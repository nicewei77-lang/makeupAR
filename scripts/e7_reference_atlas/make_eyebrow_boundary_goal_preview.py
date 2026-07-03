#!/usr/bin/env python3
"""Render a static eyebrow boundary preview that mirrors the Unity brow envelope.

This is visual evidence only. Runtime proof still needs device AR validation.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


POINT_COUNT = 72
INNER_GAP_RIGHT_BIAS = 0.70
SCREEN_LEFT_HEAD_RESTORE = 0.86
SCREEN_RIGHT_HEAD_EXTRA_TRIM = -0.18
HEAD_BODY = 0.20
BODY_END = 0.62
ARCH = 0.64
TAIL_START = ARCH
TAIL_ROOT = 0.985
CONTROL_BODY = 0.42
PROFILE_KNOTS = (0.0, 0.08, 0.16, 0.24, 0.42, 0.62, 0.64, 0.78, 0.90, 0.985, 1.0)
SEMI_ARCH_TOP_PROFILE = (0.42, 0.30, 0.22, 0.16, 0.10, 0.08, 0.04, 0.12, 0.24, 0.34, 0.40)
SEMI_ARCH_BOTTOM_PROFILE = (0.86, 0.80, 0.75, 0.72, 0.70, 0.69, 0.67, 0.63, 0.57, 0.51, 0.50)
SPLINE_KNOTS = (0.0, CONTROL_BODY, ARCH, 1.0)
SPLINE_TOPS = {
    1: (0.40, 0.14, 0.05, 0.44),
    2: (0.41, 0.28, 0.26, 0.43),
    3: (0.40, 0.11, -0.02, 0.46),
}
SPLINE_BOTTOMS = {
    1: (0.92, 0.71, 0.66, 0.55),
    2: (0.90, 0.71, 0.66, 0.55),
    3: (0.94, 0.71, 0.66, 0.57),
}

COMMERCIAL_SHAPE_TARGETS = {
    "semi arch": {"h_over_w": (0.145, 0.225), "tail_t": (0.10, 0.36)},
    "straight": {"h_over_w": (0.105, 0.165), "tail_t": (0.10, 0.36)},
    "arch": {"h_over_w": (0.155, 0.220), "tail_t": (0.10, 0.36)},
}

STYLES = {
    1: (
        "semi arch",
        (0.90, 0.165, 0.004, 0.202, 0.015),
        (0.83, 0.70, 0.62, 0.45, 0.52, 0.58, 0.76),
        (0.18, 0.76, 0.70, 0.52, 0.29, 0.16, 0.040),
        (0.38, 0.30, 0.18, 0.16, 0.30, 0.42, 0.52),
        (0.89, 0.76, 0.68, 0.66, 0.66, 0.64, 0.62),
    ),
    2: (
        "straight",
        (0.88, 0.150, 0.000, 0.198, 0.020),
        (0.80, 0.72, 0.70, 0.68, 0.70, 0.72, 0.77),
        (0.18, 0.76, 0.70, 0.54, 0.30, 0.16, 0.040),
        (0.50, 0.27, 0.24, 0.22, 0.32, 0.44, 0.50),
        (0.86, 0.73, 0.72, 0.71, 0.68, 0.62, 0.63),
    ),
    3: (
        "arch",
        (0.92, 0.180, 0.008, 0.204, 0.000),
        (0.85, 0.70, 0.56, 0.36, 0.44, 0.50, 0.76),
        (0.18, 0.76, 0.70, 0.50, 0.28, 0.15, 0.040),
        (0.40, 0.13, 0.04, -0.04, 0.10, 0.32, 0.50),
        (0.90, 0.74, 0.71, 0.69, 0.65, 0.60, 0.62),
    ),
}


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def lerp(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount


def evaluate_curve(progress: float, values: tuple[float, ...]) -> float:
    head, body_start, body_end, arch, tail_start, tail_root, tail = values
    progress = max(0.0, min(1.0, progress))
    if progress <= HEAD_BODY:
        return lerp(head, body_start, smoothstep(progress / HEAD_BODY))
    if progress <= BODY_END:
        return lerp(
            body_start,
            body_end,
            smoothstep((progress - HEAD_BODY) / (BODY_END - HEAD_BODY)),
        )
    if progress <= ARCH:
        return lerp(
            body_end,
            arch,
            smoothstep((progress - BODY_END) / (ARCH - BODY_END)),
        )
    if progress <= TAIL_START:
        return lerp(
            arch,
            tail_start,
            smoothstep((progress - ARCH) / (TAIL_START - ARCH)),
        )
    if progress <= TAIL_ROOT:
        return lerp(
            tail_start,
            tail_root,
            smoothstep((progress - TAIL_START) / (TAIL_ROOT - TAIL_START)),
        )
    return lerp(
        tail_root,
        tail,
        smoothstep((progress - TAIL_ROOT) / (1.0 - TAIL_ROOT)),
    )


def evaluate_profile_curve(
    progress: float,
    knots: tuple[float, ...],
    values: tuple[float, ...],
) -> float:
    progress = max(0.0, min(1.0, progress))
    if progress <= knots[0]:
        return values[0]
    for index in range(1, len(knots)):
        if progress <= knots[index]:
            start = knots[index - 1]
            end = knots[index]
            amount = 0.0 if end <= start else smoothstep((progress - start) / (end - start))
            return lerp(values[index - 1], values[index], amount)
    return values[-1]


def evaluate_cubic_spline(
    progress: float,
    knots: tuple[float, ...],
    values: tuple[float, ...],
) -> float:
    progress = max(0.0, min(1.0, progress))
    if progress <= knots[0]:
        return values[0]
    if progress >= knots[-1]:
        return values[-1]
    index = 1
    while index < len(knots) and progress > knots[index]:
        index += 1
    start = knots[index - 1]
    end = knots[index]
    t = 0.0 if end <= start else (progress - start) / (end - start)

    def slope(point_index: int) -> float:
        if point_index <= 0:
            dx = knots[1] - knots[0]
            return 0.0 if dx <= 0.0 else (values[1] - values[0]) / dx
        if point_index >= len(knots) - 1:
            dx = knots[-1] - knots[-2]
            return 0.0 if dx <= 0.0 else (values[-1] - values[-2]) / dx
        dx = knots[point_index + 1] - knots[point_index - 1]
        return 0.0 if dx <= 0.0 else (values[point_index + 1] - values[point_index - 1]) / dx

    m0 = slope(index - 1) * (end - start) * 0.55
    m1 = slope(index) * (end - start) * 0.55
    t2 = t * t
    t3 = t2 * t
    h00 = 2.0 * t3 - 3.0 * t2 + 1.0
    h10 = t3 - 2.0 * t2 + t
    h01 = -2.0 * t3 + 3.0 * t2
    h11 = t3 - t2
    return h00 * values[index - 1] + h10 * m0 + h01 * values[index] + h11 * m1


def evaluate_style_top(progress: float, style_index: int, values: tuple[float, ...]) -> float:
    return evaluate_cubic_spline(progress, SPLINE_KNOTS, SPLINE_TOPS.get(style_index, SPLINE_TOPS[1]))


def evaluate_style_bottom(progress: float, style_index: int, values: tuple[float, ...]) -> float:
    return evaluate_cubic_spline(progress, SPLINE_KNOTS, SPLINE_BOTTOMS.get(style_index, SPLINE_BOTTOMS[1]))


def bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def smooth_boundary(
    points: list[tuple[float, float]],
    iterations: int = 2,
) -> list[tuple[float, float]]:
    current = list(points)
    half = len(current) // 2
    for _ in range(iterations):
        next_points = list(current)
        for start, direction in ((0, 1), (len(current) - 1, -1)):
            for offset in range(1, half - 1):
                index = start + offset * direction
                previous = start + (offset - 1) * direction
                following = start + (offset + 1) * direction
                next_points[index] = (
                    current[previous][0] * 0.18
                    + current[index][0] * 0.64
                    + current[following][0] * 0.18,
                    current[previous][1] * 0.22
                    + current[index][1] * 0.56
                    + current[following][1] * 0.22,
                )
        current = next_points
    return current


def shape_boundary(
    source_points: list[tuple[float, float]],
    screen_left: bool,
    style_index: int,
    eye_top: float = 600.0,
) -> list[tuple[float, float]]:
    left, top, right, bottom = bounds(source_points)
    width = max(1.0, right - left)
    source_height = max(1.0, bottom - top)
    _, profile, center_values, thickness_values, top_values, bottom_values = STYLES[style_index]
    width_scale, height_ratio, tail_extend_ratio, head_trim_ratio, bottom_lift = profile

    adjusted_width = width * width_scale
    center_x = (left + right) * 0.5
    shaped_left = center_x - adjusted_width * 0.5
    shaped_right = center_x + adjusted_width * 0.5
    tail_extend = max(0.0, min(width * tail_extend_ratio, 28.0))
    head_trim = max(12.0, min(width * head_trim_ratio, 54.0))
    if screen_left:
        shaped_left -= tail_extend
        shaped_right -= head_trim
        shaped_right += head_trim * SCREEN_LEFT_HEAD_RESTORE
    else:
        shaped_left += head_trim
        shaped_left += head_trim * SCREEN_RIGHT_HEAD_EXTRA_TRIM
        shaped_right += tail_extend

    shape_width = shaped_right - shaped_left
    height = max(source_height * 0.84, shape_width * height_ratio)
    min_height = max(16.0, min(shape_width * 0.135, 34.0))
    max_height = max(40.0, min(shape_width * 0.275, 70.0))
    height = max(min_height, min(height, max_height))
    max_bottom = eye_top - 12.0
    bottom_anchor = min(max(bottom + source_height * 0.05, top + source_height * 0.78), max_bottom)
    bottom_anchor -= height * bottom_lift
    top_anchor = bottom_anchor - height

    top_points: list[tuple[float, float]] = []
    bottom_points: list[tuple[float, float]] = []
    for index in range(POINT_COUNT):
        ratio = index / (POINT_COUNT - 1)
        x = lerp(shaped_left, shaped_right, ratio)
        progress = 1.0 - ratio if screen_left else ratio
        top_y = top_anchor + height * evaluate_style_top(progress, style_index, top_values)
        bottom_y = top_anchor + height * evaluate_style_bottom(progress, style_index, bottom_values)
        direction_to_tail_x = -1.0 if screen_left else 1.0
        head_influence = 1.0 - smoothstep(progress / 0.18)
        tail_influence = smoothstep((progress - TAIL_START) / (1.0 - TAIL_START))
        top_x = (
            x
            + direction_to_tail_x * shape_width * 0.028 * head_influence
            - direction_to_tail_x * shape_width * 0.015 * tail_influence
        )
        bottom_x = (
            x
            + direction_to_tail_x * shape_width * 0.006 * head_influence
            + direction_to_tail_x * shape_width * 0.018 * tail_influence
        )
        tail_tip_influence = smoothstep((progress - TAIL_START) / (1.0 - TAIL_START))
        tail_tip_x = x + direction_to_tail_x * shape_width * 0.004
        tail_tip_blend = tail_tip_influence * 0.72
        top_x = lerp(top_x, tail_tip_x, tail_tip_blend)
        bottom_x = lerp(bottom_x, tail_tip_x, tail_tip_blend)
        min_thickness = height * lerp(0.060, 0.145, 1.0 - tail_influence)
        if bottom_y < top_y + min_thickness:
            bottom_y = top_y + min_thickness
        if bottom_y > max_bottom:
            shift = bottom_y - max_bottom
            top_y -= shift
            bottom_y -= shift
        top_points.append((top_x, top_y))
        bottom_points.append((bottom_x, bottom_y))
    return smooth_boundary(top_points + list(reversed(bottom_points)), 3)


def sample_center(
    polygon: list[tuple[float, float]],
    screen_left: bool,
    progress: float,
) -> tuple[float, float]:
    half = len(polygon) // 2
    position = (1.0 - progress if screen_left else progress) * (half - 1)
    lower = max(0, min(half - 1, math.floor(position)))
    upper = max(0, min(half - 1, math.ceil(position)))
    fraction = position - lower
    top = (
        polygon[lower][0] * (1.0 - fraction) + polygon[upper][0] * fraction,
        polygon[lower][1] * (1.0 - fraction) + polygon[upper][1] * fraction,
    )
    bottom_lower = polygon[len(polygon) - 1 - lower]
    bottom_upper = polygon[len(polygon) - 1 - upper]
    bottom = (
        bottom_lower[0] * (1.0 - fraction) + bottom_upper[0] * fraction,
        bottom_lower[1] * (1.0 - fraction) + bottom_upper[1] * fraction,
    )
    return (top[0] + bottom[0]) * 0.5, (top[1] + bottom[1]) * 0.5


def sample_boundary_pair(
    polygon: list[tuple[float, float]],
    screen_left: bool,
    progress: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    half = len(polygon) // 2
    position = (1.0 - progress if screen_left else progress) * (half - 1)
    lower = max(0, min(half - 1, math.floor(position)))
    upper = max(0, min(half - 1, math.ceil(position)))
    fraction = position - lower
    top = (
        polygon[lower][0] * (1.0 - fraction) + polygon[upper][0] * fraction,
        polygon[lower][1] * (1.0 - fraction) + polygon[upper][1] * fraction,
    )
    bottom_lower = polygon[len(polygon) - 1 - lower]
    bottom_upper = polygon[len(polygon) - 1 - upper]
    bottom = (
        bottom_lower[0] * (1.0 - fraction) + bottom_upper[0] * fraction,
        bottom_lower[1] * (1.0 - fraction) + bottom_upper[1] * fraction,
    )
    return top, bottom


def sample_boundary_pair_by_screen_ratio(
    polygon: list[tuple[float, float]],
    ratio: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    half = len(polygon) // 2
    position = max(0.0, min(1.0, ratio)) * (half - 1)
    lower = max(0, min(half - 1, math.floor(position)))
    upper = max(0, min(half - 1, math.ceil(position)))
    fraction = position - lower
    top = (
        polygon[lower][0] * (1.0 - fraction) + polygon[upper][0] * fraction,
        polygon[lower][1] * (1.0 - fraction) + polygon[upper][1] * fraction,
    )
    bottom_lower = polygon[len(polygon) - 1 - lower]
    bottom_upper = polygon[len(polygon) - 1 - upper]
    bottom = (
        bottom_lower[0] * (1.0 - fraction) + bottom_upper[0] * fraction,
        bottom_lower[1] * (1.0 - fraction) + bottom_upper[1] * fraction,
    )
    return top, bottom


def boundary_shape_metrics(
    polygon: list[tuple[float, float]],
    screen_left: bool,
) -> dict[str, float]:
    min_x, min_y, max_x, max_y = bounds(polygon)
    width = max(1.0, max_x - min_x)
    height = max(1.0, max_y - min_y)
    metrics = {
        "hOverW": height / width,
        "widthPx": width,
        "heightPx": height,
    }
    for name, progress in (
        ("head", 0.0),
        ("body", CONTROL_BODY),
        ("tailStart", TAIL_START),
        ("arch", ARCH),
        ("tail", 1.0),
    ):
        top, bottom = sample_boundary_pair(polygon, screen_left, progress)
        metrics[f"{name}Thickness"] = max(0.0, min(1.0, abs(bottom[1] - top[1]) / height))
    return metrics


def evaluate_commercial_shape_gate(
    style_name: str,
    left_metrics: dict[str, float],
    right_metrics: dict[str, float],
) -> dict[str, object]:
    target = COMMERCIAL_SHAPE_TARGETS[style_name]
    h_min, h_max = target["h_over_w"]
    tail_min, tail_max = target["tail_t"]
    checks = {
        "leftHOverW": h_min <= left_metrics["hOverW"] <= h_max,
        "rightHOverW": h_min <= right_metrics["hOverW"] <= h_max,
        "leftTailThickness": tail_min <= left_metrics["tailThickness"] <= tail_max,
        "rightTailThickness": tail_min <= right_metrics["tailThickness"] <= tail_max,
        "bodyTailSeparation": (
            left_metrics["tailStartThickness"] > left_metrics["tailThickness"] * 2.2
            and right_metrics["tailStartThickness"] > right_metrics["tailThickness"] * 2.2
        ),
        "leftRightHeightSymmetry": abs(left_metrics["hOverW"] - right_metrics["hOverW"]) <= 0.045,
    }
    return {
        "target": {
            "hOverW": [h_min, h_max],
            "tailThickness": [tail_min, tail_max],
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def enforce_inner_gap(
    left_polygon: list[tuple[float, float]],
    right_polygon: list[tuple[float, float]],
) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    left_min, _, left_max, _ = bounds(left_polygon)
    right_min, _, right_max, _ = bounds(right_polygon)
    average_width = ((left_max - left_min) + (right_max - right_min)) * 0.5
    minimum_gap = max(80.0, min(average_width * 0.42, 148.0))
    current_gap = right_min - left_max
    if current_gap >= minimum_gap:
        return left_polygon, right_polygon
    trim_needed = minimum_gap - current_gap
    right_trim = trim_needed * INNER_GAP_RIGHT_BIAS
    left_trim = trim_needed - right_trim

    def trim_inner(
        polygon: list[tuple[float, float]],
        screen_left: bool,
        trim_px: float,
    ) -> list[tuple[float, float]]:
        min_x, _, max_x, _ = bounds(polygon)
        width = max(1.0, max_x - min_x)
        out: list[tuple[float, float]] = []
        for x, y in polygon:
            distance_from_inner = (max_x - x) / width if screen_left else (x - min_x) / width
            influence = 1.0 - smoothstep(distance_from_inner / 0.30)
            shift = trim_px * influence
            out.append((x - shift if screen_left else x + shift, y))
        return out

    return (
        trim_inner(left_polygon, True, left_trim),
        trim_inner(right_polygon, False, right_trim),
    )


def brow_end_taper(local_x: float) -> float:
    head_taper = lerp(0.46, 1.0, smoothstep(local_x / 0.20))
    tail_taper = lerp(1.0, 0.38, smoothstep((local_x - TAIL_START) / (1.0 - TAIL_START)))
    return max(0.0, min(1.0, head_taper * tail_taper))


def brow_shape_density(local_x: float, style_index: int) -> float:
    semi_mode = 1.0 if style_index == 1 else 0.0
    straight_mode = 1.0 if style_index == 2 else 0.0
    arch_mode = 1.0 if style_index == 3 else 0.0
    arch_center = semi_mode * 0.64 + straight_mode * 0.64 + arch_mode * 0.64
    arch_strength = semi_mode * 0.18 + straight_mode * 0.05 + arch_mode * 0.32
    head_soft = (1.0 - smoothstep(local_x / 0.24)) * 0.28
    body = smoothstep((local_x - 0.05) / 0.29) * (1.0 - smoothstep((local_x - TAIL_START) / (1.0 - TAIL_START))) * 0.78
    arch = (1.0 - smoothstep(abs(local_x - arch_center) / 0.24)) * arch_strength
    tail_fade = (1.0 - smoothstep((local_x - TAIL_START) / (1.0 - TAIL_START))) * 0.16
    return max(0.0, min(1.0, head_soft + body + arch + tail_fade))


def make_shader_like_fill(
    size: tuple[int, int],
    left_polygon: list[tuple[float, float]],
    right_polygon: list[tuple[float, float]],
    style_index: int,
    color: tuple[int, int, int],
    max_alpha: int,
    blur: float,
) -> Image.Image:
    alpha = Image.new("L", size, 0)
    alpha_draw = ImageDraw.Draw(alpha)
    alpha_draw.polygon(left_polygon, fill=max_alpha)
    alpha_draw.polygon(right_polygon, fill=max_alpha)
    alpha = alpha.filter(ImageFilter.GaussianBlur(blur))
    alpha_pixels = alpha.load()

    fill = Image.new("RGBA", size, color + (0,))
    fill_pixels = fill.load()

    for polygon, screen_left in ((left_polygon, True), (right_polygon, False)):
        min_x, min_y, max_x, max_y = bounds(polygon)
        width = max(1.0, max_x - min_x)
        x0 = max(0, int(math.floor(min_x)) - 4)
        x1 = min(size[0] - 1, int(math.ceil(max_x)) + 4)
        y0 = max(0, int(math.floor(min_y)) - 4)
        y1 = min(size[1] - 1, int(math.ceil(max_y)) + 4)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                source_alpha = alpha_pixels[x, y]
                if source_alpha <= 0:
                    continue
                local_x = (max_x - x) / width if screen_left else (x - min_x) / width
                local_x = max(0.0, min(1.0, local_x))
                density = 0.22 + brow_shape_density(local_x, style_index) * 0.72
                tapered = brow_end_taper(local_x)
                fill_pixels[x, y] = color + (int(source_alpha * density * tapered),)

    return fill


def draw_boundary_only(
    face: Image.Image,
    left_polygon: list[tuple[float, float]],
    right_polygon: list[tuple[float, float]],
    crop_box: tuple[int, int, int, int],
) -> Image.Image:
    canvas = face.copy()
    draw = ImageDraw.Draw(canvas)
    for polygon in (left_polygon, right_polygon):
        draw.line(
            polygon + [polygon[0]],
            fill=(255, 0, 0, 255),
            width=3,
            joint="curve",
        )
    return canvas.crop(crop_box)


def extract_reference_red_points(
    reference_image: Image.Image,
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    pixels = reference_image.convert("RGBA").load()
    width, height = reference_image.size
    left_points: list[tuple[int, int]] = []
    right_points: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a > 80 and r > 180 and g < 90 and b < 90:
                if x < width * 0.5:
                    left_points.append((x, y))
                else:
                    right_points.append((x, y))
    return left_points, right_points


def red_profile(
    points: list[tuple[int, int]],
    bins: int = 96,
) -> tuple[tuple[float, float, float, float], list[tuple[float, float, float]]]:
    if not points:
        return (0.0, 0.0, 1.0, 1.0), []
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max(1.0, float(max_x - min_x))
    buckets: list[list[int]] = [[] for _ in range(bins)]
    for x, y in points:
        index = max(0, min(bins - 1, round((x - min_x) / width * (bins - 1))))
        buckets[index].append(y)
    samples: list[tuple[float, float, float]] = []
    for index, values in enumerate(buckets):
        if not values:
            continue
        ratio = index / (bins - 1)
        samples.append((ratio, float(min(values)), float(max(values))))
    return (float(min_x), float(min_y), float(max_x), float(max_y)), samples


def map_polygon_to_reference_box(
    polygon: list[tuple[float, float]],
    target_box: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = bounds(polygon)
    source_width = max(1.0, max_x - min_x)
    source_height = max(1.0, max_y - min_y)
    target_min_x, target_min_y, target_max_x, target_max_y = target_box
    target_width = max(1.0, target_max_x - target_min_x)
    target_height = max(1.0, target_max_y - target_min_y)
    return [
        (
            target_min_x + ((x - min_x) / source_width) * target_width,
            target_min_y + ((y - min_y) / source_height) * target_height,
        )
        for x, y in polygon
    ]


def compare_polygon_to_red_profile(
    polygon: list[tuple[float, float]],
    red_box: tuple[float, float, float, float],
    red_samples: list[tuple[float, float, float]],
) -> dict[str, float]:
    if not red_samples:
        return {"topMeanDeltaNorm": 1.0, "bottomMeanDeltaNorm": 1.0}
    min_x, min_y, max_x, max_y = bounds(polygon)
    height = max(1.0, max_y - min_y)
    red_min_y = red_box[1]
    red_height = max(1.0, red_box[3] - red_box[1])
    top_deltas: list[float] = []
    bottom_deltas: list[float] = []
    for ratio, red_top_y, red_bottom_y in red_samples:
        generated_top, generated_bottom = sample_boundary_pair_by_screen_ratio(
            polygon,
            ratio,
        )
        generated_top_norm = (generated_top[1] - min_y) / height
        generated_bottom_norm = (generated_bottom[1] - min_y) / height
        red_top_norm = (red_top_y - red_min_y) / red_height
        red_bottom_norm = (red_bottom_y - red_min_y) / red_height
        top_deltas.append(abs(generated_top_norm - red_top_norm))
        bottom_deltas.append(abs(generated_bottom_norm - red_bottom_norm))
    return {
        "topMeanDeltaNorm": sum(top_deltas) / len(top_deltas),
        "bottomMeanDeltaNorm": sum(bottom_deltas) / len(bottom_deltas),
    }


def write_reference_compare(
    out_dir: Path,
    reference_path: Path,
    left_polygon: list[tuple[float, float]],
    right_polygon: list[tuple[float, float]],
) -> dict[str, object] | None:
    if not reference_path.exists():
        return None
    reference = Image.open(reference_path).convert("RGBA")
    left_red, right_red = extract_reference_red_points(reference)
    left_box, left_samples = red_profile(left_red)
    right_box, right_samples = red_profile(right_red)
    left_mapped = map_polygon_to_reference_box(left_polygon, left_box)
    right_mapped = map_polygon_to_reference_box(right_polygon, right_box)
    overlay = reference.copy()
    draw = ImageDraw.Draw(overlay)
    for polygon in (left_mapped, right_mapped):
        draw.line(
            polygon + [polygon[0]],
            fill=(0, 220, 255, 255),
            width=3,
            joint="curve",
        )
    path = out_dir / "reference_scaled_compare_style1.png"
    overlay.save(path)
    return {
        "path": str(path),
        "left": compare_polygon_to_red_profile(left_polygon, left_box, left_samples),
        "right": compare_polygon_to_red_profile(right_polygon, right_box, right_samples),
    }


def render(args: argparse.Namespace) -> None:
    root = Path(args.root)
    source = root / "evidence/e7-reference-atlas/eyebrow-validation-v1/source/face.png"
    summary_path = root / "evidence/e7-reference-atlas/eyebrow-validation-v1/summary.json"
    summary = json.loads(summary_path.read_text())
    out_dir = root / f"evidence/e7-reference-atlas/eyebrow-boundary-goal-{args.version}"
    out_dir.mkdir(parents=True, exist_ok=True)

    face = Image.open(source).convert("RGBA")
    left_source = [tuple(point) for point in summary["eyebrowBoundary"]["screenLeft"]["top"]]
    left_source += [tuple(point) for point in summary["eyebrowBoundary"]["screenLeft"]["bottom"]]
    right_source = [tuple(point) for point in summary["eyebrowBoundary"]["screenRight"]["top"]]
    right_source += [tuple(point) for point in summary["eyebrowBoundary"]["screenRight"]["bottom"]]
    crop_box = (40, 390, 825, 650)
    debug_rows = []
    clean_rows = []
    boundary_rows = []
    style_summaries = []
    reference_compare = None

    for style_index in (1, 2, 3):
        style_name = STYLES[style_index][0]
        left_polygon = shape_boundary(left_source, True, style_index)
        right_polygon = shape_boundary(right_source, False, style_index)
        left_polygon, right_polygon = enforce_inner_gap(left_polygon, right_polygon)
        left_metrics = boundary_shape_metrics(left_polygon, True)
        right_metrics = boundary_shape_metrics(right_polygon, False)
        gate = evaluate_commercial_shape_gate(style_name, left_metrics, right_metrics)
        if style_index == 1 and args.reference_boundary:
            reference_compare = write_reference_compare(
                out_dir,
                Path(args.reference_boundary),
                left_polygon,
                right_polygon,
            )
        style_summaries.append(
            {
                "styleIndex": style_index,
                "styleName": style_name,
                "leftMetrics": left_metrics,
                "rightMetrics": right_metrics,
                "commercialShapeGate": gate,
            }
        )

        boundary_crop = draw_boundary_only(face, left_polygon, right_polygon, crop_box)
        boundary_rows.append(boundary_crop)
        boundary_crop.save(
            out_dir / f"boundary_only_{style_index}_{style_name.replace(' ', '_')}_{args.version}.png"
        )

        for debug in (False, True):
            canvas = face.copy()
            fill = make_shader_like_fill(
                face.size,
                left_polygon,
                right_polygon,
                style_index,
                tuple(args.color),
                args.alpha,
                args.blur,
            )
            canvas = Image.alpha_composite(canvas, fill)
            draw = ImageDraw.Draw(canvas)
            if debug:
                for polygon in (left_polygon, right_polygon):
                    draw.line(polygon + [polygon[0]], fill=(255, 0, 0, 255), width=3, joint="curve")
                controls = [
                    ("H", 0.0, (0, 210, 255)),
                    ("B", CONTROL_BODY, (0, 210, 255)),
                    ("A/S", ARCH, (0, 230, 60)),
                    ("R", TAIL_ROOT, (255, 220, 0)),
                    ("T", 1.0, (255, 95, 0)),
                ]
                for polygon, screen_left in ((left_polygon, True), (right_polygon, False)):
                    for label, progress, color in controls:
                        x, y = sample_center(polygon, screen_left, progress)
                        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color + (255,), outline=(255, 255, 255, 255), width=2)
                        draw.text((x + 5, y - 13), label, fill=color + (255,))
                draw.text(
                    (crop_box[0] + 5, crop_box[1] + 5),
                    (
                        f"{style_name} H=0 B={CONTROL_BODY * 100:.0f} "
                        f"A={ARCH * 100:.0f} S={TAIL_START * 100:.0f} "
                        f"R={TAIL_ROOT * 100:.1f} T=100 "
                        f"gate={'pass' if gate['passed'] else 'check'}"
                    ),
                    fill=(255, 0, 0, 255),
                )
            crop = canvas.crop(crop_box)
            stem = style_name.replace(" ", "_")
            if debug:
                debug_rows.append(crop)
                crop.save(out_dir / f"debug_boundary_fill_{style_index}_{stem}_{args.version}.png")
            else:
                clean_rows.append(crop)
                crop.save(out_dir / f"clean_boundary_fill_{style_index}_{stem}_{args.version}.png")

    def save_sheet(rows: list[Image.Image], filename: str) -> Path:
        sheet = Image.new("RGBA", (crop_box[2] - crop_box[0], (crop_box[3] - crop_box[1]) * 3 + 40), (245, 245, 245, 255))
        y = 0
        for row in rows:
            sheet.alpha_composite(row, (0, y))
            y += row.height + 20
        path = out_dir / filename
        sheet.save(path)
        return path

    debug_sheet = save_sheet(debug_rows, f"debug_boundary_fill_3style_{args.version}_makeup_envelope.png")
    clean_sheet = save_sheet(clean_rows, f"clean_boundary_fill_3style_{args.version}_makeup_envelope.png")
    boundary_sheet = save_sheet(boundary_rows, f"boundary_only_3style_{args.version}_spline_envelope.png")
    (out_dir / "summary.json").write_text(
        json.dumps(
            {
                "version": args.version,
                "debugSheet": str(debug_sheet),
                "cleanSheet": str(clean_sheet),
                "boundaryOnlySheet": str(boundary_sheet),
                "constants": {
                    "H": 0.0,
                    "B": CONTROL_BODY,
                    "S": TAIL_START,
                    "A": ARCH,
                    "tailRoot": TAIL_ROOT,
                    "T": 1.0,
                    "bodyEnd": BODY_END,
                },
                "spline": {
                    "controlPointMode": "head_body_arch_tail_cubic_spline",
                    "sourceUsage": "hair boundary is used only for position, width, and scale; final makeup envelope comes from spline controls",
                    "knots": list(SPLINE_KNOTS),
                    "topControls": {str(key): list(value) for key, value in SPLINE_TOPS.items()},
                    "bottomControls": {str(key): list(value) for key, value in SPLINE_BOTTOMS.items()},
                    "anchors": {
                        "H": 0.0,
                        "B": CONTROL_BODY,
                        "A/S": ARCH,
                        "R": TAIL_ROOT,
                        "T": 1.0,
                    },
                },
                "styles": style_summaries,
                "referenceCompare": reference_compare,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(debug_sheet)
    print(clean_sheet)
    print(boundary_sheet)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/Users/yeoduchi/Documents/makeupAR")
    parser.add_argument("--version", default="v37")
    parser.add_argument("--alpha", type=int, default=150)
    parser.add_argument("--blur", type=float, default=1.45)
    parser.add_argument("--color", type=int, nargs=3, default=(62, 43, 34))
    parser.add_argument("--reference-boundary", default="")
    render(parser.parse_args())


if __name__ == "__main__":
    main()
