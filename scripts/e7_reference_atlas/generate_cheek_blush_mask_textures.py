#!/usr/bin/env python3
"""Generate Unity-ready ARFace UV cheek blush masks from user drawings."""

from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from generate_user_drawn_mask_textures import (
    DEFAULT_CAPTURE_PAIR,
    back_project_mask_to_uv,
    format_path,
    keep_components,
    load_arface_export,
    make_alpha_png,
    make_region_variants,
    mask_stats,
    resolve_path,
    save,
    trim_horizontal_uv_seams,
    write_unity_meta,
)


MASK_SPECS = (
    {
        "id": "cheek-lovely-mask-v1",
        "label": "lovely round cheek",
        "arg": "lovely",
        "default": "/Users/yeoduchi/Downloads/cheek_lovely_mask.png",
    },
    {
        "id": "cheek-daily-mask-v1",
        "label": "daily diagonal cheek",
        "arg": "daily",
        "default": "/Users/yeoduchi/Downloads/cheek_daily_mask.png",
    },
    {
        "id": "cheek-default2-mask-v1",
        "label": "default2 multi-band cheek",
        "arg": "default2",
        "default": "/Users/yeoduchi/Downloads/blush_defalut2.png",
    },
    {
        "id": "cheek-sunkissed-mask1-v1",
        "label": "sunkissed cheek plus nose",
        "arg": "sunkissed1",
        "default": "/Users/yeoduchi/Downloads/cheek_sunkissed_mask1.png",
    },
    {
        "id": "cheek-sunkissed-mask2-v1",
        "label": "sunkissed bridge wash",
        "arg": "sunkissed2",
        "default": "/Users/yeoduchi/Downloads/cheek_sunkissed_mask2.png",
    },
    {
        "id": "cheek-under-eye-mask-v1",
        "label": "under-eye soft blush",
        "arg": "under_eye",
        "default": "/Users/yeoduchi/Downloads/under_eye_mask.png",
    },
)

SUNKISSED2_PLACEMENT_BBOX = (220, 906, 917, 1052)
DEFAULT2_PLACEMENT_BBOX = (160, 760, 1018, 1285)
ALPHA_MASK_THRESHOLD = 8
SUNKISSED2_ALPHA_GEOMETRY_THRESHOLD = 128
OUTER_X_EXTENSION_PX = {
    "cheek-daily-mask-v1": 26,
    "cheek-default2-mask-v1": 18,
    "cheek-lovely-mask-v1": 22,
    "cheek-sunkissed-mask1-v1": 30,
    "cheek-sunkissed-mask2-v1": 34,
    "cheek-under-eye-mask-v1": 22,
}
DENSITY_STYLE_PROFILES = {
    "cheek-daily-mask-v1": {
        "contract": "long oval daily blush; strongest at oval center, slightly outer cheek",
        "blobs": {
            "cheek": {
                "centerX": 0.08,
                "centerY": 0.02,
                "radiusX": 0.52,
                "radiusY": 0.46,
                "rotation": -6.0,
                "falloffPower": 1.02,
                "maxAlpha": 0.50,
            },
        },
    },
    "cheek-default2-mask-v1": {
        "contract": "wide default2 blush; outer skin tint, mid wash, and density-driven cheek cores",
        "blobs": {
            "leftCheek": {
                "centerXFromLeft": 0.23,
                "centerYFromTop": 0.43,
                "radiusX": 0.34,
                "radiusY": 0.42,
                "rotation": -5.0,
                "falloffPower": 0.92,
                "maxAlpha": 0.46,
            },
            "rightCheek": {
                "centerXFromRight": 0.23,
                "centerYFromTop": 0.43,
                "radiusX": 0.34,
                "radiusY": 0.42,
                "rotation": 5.0,
                "falloffPower": 0.92,
                "maxAlpha": 0.46,
            },
            "centerWash": {
                "centerX": 0.0,
                "centerYFromTop": 0.42,
                "radiusX": 0.18,
                "radiusY": 0.38,
                "rotation": 0.0,
                "falloffPower": 1.10,
                "maxAlpha": 0.14,
            },
        },
        "verticalBalance": {"centerYFromTop": 0.43, "radiusY": 0.66},
    },
    "cheek-lovely-mask-v1": {
        "contract": "apple-cheek radial blush; strongest at round front-cheek center",
        "blobs": {
            "cheek": {
                "centerX": 0.0,
                "centerY": 0.0,
                "radiusX": 0.46,
                "radiusY": 0.46,
                "rotation": 0.0,
                "falloffPower": 1.00,
                "maxAlpha": 0.48,
            },
        },
    },
    "cheek-sunkissed-mask1-v1": {
        "contract": "outer cheek sun points plus capped nose point",
        "blobs": {
            "cheek": {
                "centerX": 0.30,
                "centerY": -0.02,
                "radiusX": 0.58,
                "radiusY": 0.60,
                "rotation": -8.0,
                "falloffPower": 0.98,
                "maxAlpha": 0.50,
            },
            "nose": {
                "centerX": 0.0,
                "centerY": 0.02,
                "radiusX": 0.56,
                "radiusY": 0.46,
                "rotation": 0.0,
                "falloffPower": 1.18,
                "maxAlpha": 0.20,
            },
        },
    },
    "cheek-sunkissed-mask2-v1": {
        "contract": "horizontal shy sun wash; outer cheekbone ends strongest, bridge very light",
        "blobs": {
            "leftCheek": {
                "centerXFromLeft": 0.18,
                "centerY": -0.02,
                "radiusX": 0.38,
                "radiusY": 0.48,
                "rotation": -4.0,
                "falloffPower": 0.96,
                "maxAlpha": 0.48,
            },
            "rightCheek": {
                "centerXFromRight": 0.18,
                "centerY": -0.02,
                "radiusX": 0.38,
                "radiusY": 0.48,
                "rotation": 4.0,
                "falloffPower": 0.96,
                "maxAlpha": 0.48,
            },
            "noseBridge": {
                "centerX": 0.0,
                "centerY": -0.08,
                "radiusX": 0.16,
                "radiusY": 0.30,
                "rotation": 0.0,
                "falloffPower": 1.16,
                "maxAlpha": 0.06,
            },
        },
        "verticalBalance": {"centerY": -0.02, "radiusY": 0.58},
    },
    "cheek-under-eye-mask-v1": {
        "contract": "under-eye crescent; strongest under outer iris/eye tail and fades down",
        "blobs": {
            "underEye": {
                "centerX": 0.18,
                "centerY": -0.22,
                "radiusX": 0.62,
                "radiusY": 0.34,
                "rotation": -8.0,
                "falloffPower": 0.94,
                "maxAlpha": 0.42,
            },
        },
        "lowerFade": {"startY": -0.16, "endY": 0.72},
    },
    "default": {
        "contract": "fallback center-density blush",
        "blobs": {
            "cheek": {
                "centerX": 0.0,
                "centerY": 0.0,
                "radiusX": 0.32,
                "radiusY": 0.32,
                "rotation": 0.0,
                "falloffPower": 1.0,
                "maxAlpha": 0.60,
            },
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back-project cheek blush drawings into ARFace UV masks."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--capture-pair", type=str, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--reference", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-blush-mask-textures-v1"),
    )
    parser.add_argument(
        "--unity-output-dir",
        type=Path,
        default=Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"),
    )
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--dark-threshold", type=int, default=150)
    parser.add_argument("--min-component-pixels", type=int, default=450)
    parser.add_argument("--screen-sample-stride", type=int, default=1)
    for spec in MASK_SPECS:
        parser.add_argument(
            "--" + spec["arg"].replace("_", "-"),
            dest=spec["arg"],
            type=Path,
            default=Path(spec["default"]),
        )
    return parser.parse_args()


def make_contact_sheet(images: list[tuple[str, Image.Image]], tile: int = 300) -> Image.Image:
    columns = 3
    rows = int(np.ceil(len(images) / columns))
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 30)), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * tile
        y = row * (tile + 30)
        thumb = image.convert("RGB").copy()
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x + (tile - thumb.width) // 2, y + 24 + (tile - thumb.height) // 2))
    return sheet


def overlay_source_masks_for_comparison(
    reference: Image.Image,
    masks: list[tuple[str, Image.Image]],
) -> Image.Image:
    colors = (
        (242, 102, 124, 116),
        (236, 128, 88, 116),
        (224, 92, 76, 108),
        (236, 116, 86, 98),
        (229, 118, 146, 100),
        (220, 120, 150, 96),
    )
    output = reference.convert("RGBA")
    for index, (_, mask) in enumerate(masks):
        color = Image.new("RGBA", output.size, colors[index % len(colors)])
        alpha = mask.convert("L").filter(ImageFilter.GaussianBlur(radius=1.4))
        color.putalpha(alpha.point(lambda value: min(value, colors[index % len(colors)][3])))
        output = Image.alpha_composite(output, color)
    return output


def build_soft_unity_mask(uv_hard: Image.Image) -> Image.Image:
    variants = make_region_variants(uv_hard)
    safe = trim_horizontal_uv_seams(variants["soft"])
    return safe.filter(ImageFilter.GaussianBlur(radius=0.85))


def shift_component_x(component: np.ndarray, shift: int, direction: int) -> np.ndarray:
    shifted = np.zeros_like(component)
    if shift <= 0:
        return shifted

    if direction < 0:
        shifted[:, :-shift] = component[:, shift:]
    else:
        shifted[:, shift:] = component[:, :-shift]
    return shifted


def extend_outer_x_edges(mask: np.ndarray, mask_id: str) -> tuple[np.ndarray, dict[str, int]]:
    """Extend only the face-outer side of cheek components along x."""
    result = mask.astype(bool).copy()
    height, width = result.shape
    grid_x = np.broadcast_to(np.arange(width), (height, width))
    extension_px = OUTER_X_EXTENSION_PX.get(mask_id, 22)
    added = np.zeros_like(result)
    extended_components = 0

    for component in iter_components(result.astype(np.float32), min_pixels=450):
        ys, xs = np.nonzero(component)
        if len(xs) == 0:
            continue

        box_w = int(xs.max() - xs.min() + 1)
        center_x = float((xs.min() + xs.max()) * 0.5)
        is_center_nose = abs(center_x - width * 0.5) < width * 0.11 and box_w < width * 0.22
        if is_center_nose:
            continue

        if mask_id == "cheek-sunkissed-mask2-v1" and box_w > width * 0.36:
            left_source = component & (grid_x < center_x)
            right_source = component & (grid_x > center_x)
            sources = ((left_source, -1), (right_source, 1))
        else:
            sources = ((component, -1 if center_x < width * 0.5 else 1),)

        for source, direction in sources:
            if not source.any():
                continue
            extended_components += 1
            for shift in range(1, extension_px + 1):
                added |= shift_component_x(source, shift, direction)

    added_new = added & ~result
    result |= added
    return result, {
        "outerXExtensionPx": int(extension_px),
        "outerXAddedPixelCount": int(added_new.sum()),
        "outerXExtendedComponentCount": int(extended_components),
    }


def alpha_bbox(alpha: np.ndarray, threshold: int = ALPHA_MASK_THRESHOLD) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(alpha > threshold)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def place_alpha_strip_on_canvas(
    alpha: np.ndarray,
    canvas_shape: tuple[int, int],
    target_bbox: tuple[int, int, int, int],
) -> np.ndarray:
    source_bbox = alpha_bbox(alpha)
    if source_bbox is None:
        return np.zeros(canvas_shape, dtype=np.uint8)

    left, top, right, bottom = source_bbox
    target_left, target_top, target_right, target_bottom = target_bbox
    target_width = max(target_right - target_left + 1, 1)
    target_height = max(target_bottom - target_top + 1, 1)
    crop = Image.fromarray(alpha[top : bottom + 1, left : right + 1], mode="L")
    resized = crop.resize((target_width, target_height), Image.Resampling.LANCZOS)

    canvas = Image.new("L", (canvas_shape[1], canvas_shape[0]), 0)
    canvas.paste(resized, (target_left, target_top))
    return np.asarray(canvas, dtype=np.uint8)


def load_cheek_source_mask(
    path: Path,
    dark_threshold: int,
    mask_id: str,
    expected_shape: tuple[int, int] | None,
) -> tuple[np.ndarray, dict[str, object]]:
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    source_alpha_bbox = alpha_bbox(alpha)
    darkness = rgb.mean(axis=2)
    dark_mask = (alpha > ALPHA_MASK_THRESHOLD) & (darkness < dark_threshold)
    source_mode = "dark-rgb"

    if (
        expected_shape is not None
        and dark_mask.shape != expected_shape
        and mask_id == "cheek-default2-mask-v1"
    ):
        dark_mask = (
            place_alpha_strip_on_canvas(
                dark_mask.astype(np.uint8) * 255,
                expected_shape,
                DEFAULT2_PLACEMENT_BBOX,
            )
            > ALPHA_MASK_THRESHOLD
        )
        source_mode = "dark-rgb-fit-to-default2-canvas"

    if not dark_mask.any() and (alpha > ALPHA_MASK_THRESHOLD).any():
        source_mode = "alpha"
        alpha_threshold = ALPHA_MASK_THRESHOLD
        if (
            expected_shape is not None
            and alpha.shape != expected_shape
            and mask_id == "cheek-sunkissed-mask2-v1"
        ):
            alpha = place_alpha_strip_on_canvas(
                alpha,
                expected_shape,
                SUNKISSED2_PLACEMENT_BBOX,
            )
            alpha_threshold = SUNKISSED2_ALPHA_GEOMETRY_THRESHOLD
            source_mode = "alpha-strip-fit-to-sunkissed2-canvas"
        elif (
            expected_shape is not None
            and alpha.shape != expected_shape
            and mask_id == "cheek-default2-mask-v1"
        ):
            alpha = place_alpha_strip_on_canvas(
                alpha,
                expected_shape,
                DEFAULT2_PLACEMENT_BBOX,
            )
            source_mode = "alpha-fit-to-default2-canvas"
        dark_mask = alpha > alpha_threshold

    return dark_mask, {
        "sourceMode": source_mode,
        "sourceSize": {"width": int(rgba.shape[1]), "height": int(rgba.shape[0])},
        "sourceAlphaBbox": (
            None
            if source_alpha_bbox is None
            else {
                "left": source_alpha_bbox[0],
                "top": source_alpha_bbox[1],
                "right": source_alpha_bbox[2],
                "bottom": source_alpha_bbox[3],
            }
        ),
        "placementBbox": (
            {
                "left": SUNKISSED2_PLACEMENT_BBOX[0],
                "top": SUNKISSED2_PLACEMENT_BBOX[1],
                "right": SUNKISSED2_PLACEMENT_BBOX[2],
                "bottom": SUNKISSED2_PLACEMENT_BBOX[3],
                "alphaGeometryThreshold": SUNKISSED2_ALPHA_GEOMETRY_THRESHOLD,
            }
            if source_mode == "alpha-strip-fit-to-sunkissed2-canvas"
            else {
                "left": DEFAULT2_PLACEMENT_BBOX[0],
                "top": DEFAULT2_PLACEMENT_BBOX[1],
                "right": DEFAULT2_PLACEMENT_BBOX[2],
                "bottom": DEFAULT2_PLACEMENT_BBOX[3],
                "alphaGeometryThreshold": ALPHA_MASK_THRESHOLD,
            }
            if source_mode
            in ("dark-rgb-fit-to-default2-canvas", "alpha-fit-to-default2-canvas")
            else None
        ),
    }


def iter_components(alpha: np.ndarray, min_pixels: int = 8) -> list[np.ndarray]:
    active = alpha > 0.03
    height, width = active.shape
    visited = np.zeros(active.shape, dtype=bool)
    components: list[np.ndarray] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    ys, xs = np.nonzero(active)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue

        queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            for dy, dx in neighbors:
                ny = y + dy
                nx = x + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and active[ny, nx]
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    queue.append((ny, nx))

        if len(pixels) < min_pixels:
            continue

        rows, cols = zip(*pixels)
        component = np.zeros(active.shape, dtype=bool)
        component[np.asarray(rows), np.asarray(cols)] = True
        components.append(component)

    return components


def gaussian_density(
    alpha: np.ndarray,
    component: np.ndarray,
    peak_x: float,
    peak_y: float,
    sigma_x: float,
    sigma_y: float,
    base: float,
    cap: float = 1.0,
) -> np.ndarray:
    grid_y, grid_x = np.indices(alpha.shape)
    alpha_gate = smoothstep_array(0.045, 0.58, alpha) * component
    gaussian = np.exp(
        -(
            ((grid_x - peak_x) / max(sigma_x, 1.0)) ** 2
            + ((grid_y - peak_y) / max(sigma_y, 1.0)) ** 2
        )
    )
    return alpha_gate * np.clip((base + (1.0 - base) * gaussian) * cap, 0.0, 1.0)


def smoothstep_array(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - edge0) / max(edge1 - edge0, 1.0e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def gaussian_blob(
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    *,
    rotation_degrees: float = 0.0,
    falloff_power: float = 1.0,
    weight: float = 1.0,
) -> np.ndarray:
    angle = math.radians(rotation_degrees)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx = grid_x - center_x
    dy = grid_y - center_y
    rx = (dx * cos_a + dy * sin_a) / max(radius_x, 1.0)
    ry = (-dx * sin_a + dy * cos_a) / max(radius_y, 1.0)
    distance = rx * rx + ry * ry
    return weight * np.exp(-np.power(distance, max(falloff_power, 0.25)))


def side_direction(cx: float, width: int) -> float:
    return -1.0 if cx < width * 0.5 else 1.0


def component_bbox(component: np.ndarray) -> tuple[np.ndarray, np.ndarray, float, float, float, float]:
    ys, xs = np.nonzero(component)
    box_w = max(float(xs.max() - xs.min() + 1), 1.0)
    box_h = max(float(ys.max() - ys.min() + 1), 1.0)
    return ys, xs, float(xs.min()), float(ys.min()), box_w, box_h


def make_density_map(uv_soft: Image.Image, mask_id: str) -> Image.Image:
    alpha = np.asarray(uv_soft.convert("L"), dtype=np.float32) / 255.0
    density = np.zeros_like(alpha)
    _, width = alpha.shape
    grid_y, grid_x = np.indices(alpha.shape)
    profile = DENSITY_STYLE_PROFILES.get(mask_id, DENSITY_STYLE_PROFILES["default"])
    blobs = profile["blobs"]

    for component in iter_components(alpha):
        ys, xs = np.nonzero(component)
        if len(xs) == 0:
            continue

        weights = alpha[component]
        total_weight = float(weights.sum())
        if total_weight <= 0.0:
            continue

        cx = float((xs * weights).sum() / total_weight)
        cy = float((ys * weights).sum() / total_weight)
        box_w = max(float(xs.max() - xs.min() + 1), 1.0)
        box_h = max(float(ys.max() - ys.min() + 1), 1.0)

        alpha_gate = smoothstep_array(0.02, 0.70, alpha) * component
        direction = side_direction(cx, width)

        if mask_id == "cheek-daily-mask-v1":
            blob = blobs["cheek"]
            center_x = cx + direction * box_w * blob["centerX"]
            center_y = cy + box_h * blob["centerY"]
            density_seed = gaussian_blob(
                grid_x,
                grid_y,
                center_x,
                center_y,
                box_w * blob["radiusX"],
                box_h * blob["radiusY"],
                rotation_degrees=direction * blob["rotation"],
                falloff_power=blob["falloffPower"],
                weight=blob["maxAlpha"],
            )
        elif mask_id == "cheek-lovely-mask-v1":
            blob = blobs["cheek"]
            density_seed = gaussian_blob(
                grid_x,
                grid_y,
                cx + direction * box_w * blob["centerX"],
                cy + box_h * blob["centerY"],
                box_w * blob["radiusX"],
                box_h * blob["radiusY"],
                rotation_degrees=direction * blob["rotation"],
                falloff_power=blob["falloffPower"],
                weight=blob["maxAlpha"],
            )
        elif mask_id == "cheek-default2-mask-v1":
            left_blob = blobs["leftCheek"]
            right_blob = blobs["rightCheek"]
            wash_blob = blobs["centerWash"]
            balance = profile["verticalBalance"]
            left_peak = gaussian_blob(
                grid_x,
                grid_y,
                xs.min() + box_w * left_blob["centerXFromLeft"],
                ys.min() + box_h * left_blob["centerYFromTop"],
                box_w * left_blob["radiusX"],
                box_h * left_blob["radiusY"],
                rotation_degrees=left_blob["rotation"],
                falloff_power=left_blob["falloffPower"],
                weight=left_blob["maxAlpha"],
            )
            right_peak = gaussian_blob(
                grid_x,
                grid_y,
                xs.max() - box_w * right_blob["centerXFromRight"],
                ys.min() + box_h * right_blob["centerYFromTop"],
                box_w * right_blob["radiusX"],
                box_h * right_blob["radiusY"],
                rotation_degrees=right_blob["rotation"],
                falloff_power=right_blob["falloffPower"],
                weight=right_blob["maxAlpha"],
            )
            center_wash = gaussian_blob(
                grid_x,
                grid_y,
                cx + direction * box_w * wash_blob["centerX"],
                ys.min() + box_h * wash_blob["centerYFromTop"],
                box_w * wash_blob["radiusX"],
                box_h * wash_blob["radiusY"],
                rotation_degrees=direction * wash_blob["rotation"],
                falloff_power=wash_blob["falloffPower"],
                weight=wash_blob["maxAlpha"],
            )
            vertical_balance = gaussian_blob(
                grid_x,
                grid_y,
                cx,
                ys.min() + box_h * balance["centerYFromTop"],
                box_w * 1.8,
                box_h * balance["radiusY"],
                falloff_power=0.96,
                weight=1.0,
            )
            density_seed = np.maximum(np.maximum(left_peak, right_peak), center_wash) * vertical_balance
        elif mask_id == "cheek-sunkissed-mask1-v1":
            is_nose = abs(cx - width * 0.5) < width * 0.10 and box_w < width * 0.18
            if is_nose:
                blob = blobs["nose"]
                density_seed = gaussian_blob(
                    grid_x,
                    grid_y,
                    cx + direction * box_w * blob["centerX"],
                    cy + box_h * blob["centerY"],
                    box_w * blob["radiusX"],
                    box_h * blob["radiusY"],
                    rotation_degrees=direction * blob["rotation"],
                    falloff_power=blob["falloffPower"],
                    weight=blob["maxAlpha"],
                )
            else:
                blob = blobs["cheek"]
                density_seed = gaussian_blob(
                    grid_x,
                    grid_y,
                    cx + direction * box_w * blob["centerX"],
                    cy + box_h * blob["centerY"],
                    box_w * blob["radiusX"],
                    box_h * blob["radiusY"],
                    rotation_degrees=direction * blob["rotation"],
                    falloff_power=blob["falloffPower"],
                    weight=blob["maxAlpha"],
                )
        elif mask_id == "cheek-sunkissed-mask2-v1":
            left_blob = blobs["leftCheek"]
            right_blob = blobs["rightCheek"]
            bridge_blob = blobs["noseBridge"]
            left_peak = gaussian_blob(
                grid_x,
                grid_y,
                xs.min() + box_w * left_blob["centerXFromLeft"],
                cy + box_h * left_blob["centerY"],
                box_w * left_blob["radiusX"],
                box_h * left_blob["radiusY"],
                rotation_degrees=left_blob["rotation"],
                falloff_power=left_blob["falloffPower"],
                weight=left_blob["maxAlpha"],
            )
            right_peak = gaussian_blob(
                grid_x,
                grid_y,
                xs.max() - box_w * right_blob["centerXFromRight"],
                cy + box_h * right_blob["centerY"],
                box_w * right_blob["radiusX"],
                box_h * right_blob["radiusY"],
                rotation_degrees=right_blob["rotation"],
                falloff_power=right_blob["falloffPower"],
                weight=right_blob["maxAlpha"],
            )
            bridge_peak = gaussian_blob(
                grid_x,
                grid_y,
                cx + direction * box_w * bridge_blob["centerX"],
                cy + box_h * bridge_blob["centerY"],
                box_w * bridge_blob["radiusX"],
                box_h * bridge_blob["radiusY"],
                rotation_degrees=direction * bridge_blob["rotation"],
                falloff_power=bridge_blob["falloffPower"],
                weight=bridge_blob["maxAlpha"],
            )
            balance = profile["verticalBalance"]
            vertical_balance = gaussian_blob(
                grid_x,
                grid_y,
                cx,
                cy + box_h * balance["centerY"],
                box_w * 2.0,
                box_h * balance["radiusY"],
                falloff_power=0.95,
                weight=1.0,
            )
            density_seed = np.maximum(np.maximum(left_peak, right_peak), bridge_peak) * vertical_balance
        elif mask_id == "cheek-under-eye-mask-v1":
            blob = blobs["underEye"]
            density_seed = gaussian_blob(
                grid_x,
                grid_y,
                cx + direction * box_w * blob["centerX"],
                cy + box_h * blob["centerY"],
                box_w * blob["radiusX"],
                box_h * blob["radiusY"],
                rotation_degrees=direction * blob["rotation"],
                falloff_power=blob["falloffPower"],
                weight=blob["maxAlpha"],
            )
            fade = profile["lowerFade"]
            lower_fade = 1.0 - smoothstep_array(
                cy + box_h * fade["startY"],
                cy + box_h * fade["endY"],
                grid_y,
            )
            density_seed *= lower_fade
        else:
            blob = blobs["cheek"]
            density_seed = gaussian_blob(
                grid_x,
                grid_y,
                cx + direction * box_w * blob["centerX"],
                cy + box_h * blob["centerY"],
                box_w * blob["radiusX"],
                box_h * blob["radiusY"],
                rotation_degrees=direction * blob["rotation"],
                falloff_power=blob["falloffPower"],
                weight=blob["maxAlpha"],
            )

        component_density = alpha_gate * np.clip(density_seed, 0.0, 0.52)

        density = np.maximum(density, component_density)

    density = np.clip(density, 0.0, 1.0)
    return Image.fromarray(np.rint(density * 255).astype(np.uint8), mode="L")


def make_cheek_rgba_mask(
    coverage_soft: Image.Image,
    density_soft: Image.Image,
    mask_id: str,
) -> tuple[Image.Image, Image.Image]:
    support_alpha = np.asarray(coverage_soft.convert("L"), dtype=np.float32) / 255.0
    density = make_density_map(density_soft.convert("L"), mask_id)
    coverage_values = np.clip(support_alpha, 0.0, 1.0)
    alpha = Image.fromarray(np.rint(coverage_values * 255).astype(np.uint8), mode="L")
    reserved = Image.new("L", alpha.size, 0)
    return Image.merge("RGBA", (alpha, reserved, density, alpha)), density


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output_dir = resolve_path(repo, args.output_dir)
    unity_dir = resolve_path(repo, args.unity_output_dir)
    pair_dir = resolve_path(
        repo,
        args.capture_dir,
        Path("evidence/e7-reference-atlas/capture_pairs") / args.capture_pair,
    )
    assert output_dir is not None
    assert unity_dir is not None
    assert pair_dir is not None

    arface_path = pair_dir / "arface_export.json"
    frame_path = pair_dir / "frame.png"
    reference_path = resolve_path(repo, args.reference) if args.reference else frame_path
    if not arface_path.exists():
        raise FileNotFoundError("ARFace export does not exist: " + str(arface_path))
    if reference_path is None or not reference_path.exists():
        raise FileNotFoundError("Reference image does not exist: " + str(reference_path))

    arface = load_arface_export(arface_path)
    reference = Image.open(reference_path).convert("RGB")
    source_overlays: list[tuple[str, Image.Image]] = []
    contact_images: list[tuple[str, Image.Image]] = []
    summaries: dict[str, object] = {}
    expected_size: tuple[int, int] | None = None

    for spec in MASK_SPECS:
        source_path = resolve_path(repo, getattr(args, spec["arg"]))
        if source_path is None or not source_path.exists():
            raise FileNotFoundError("Source cheek drawing is missing: " + str(source_path))

        raw, source_load = load_cheek_source_mask(
            source_path,
            args.dark_threshold,
            spec["id"],
            expected_size,
        )
        clean, component_stats = keep_components(raw, args.min_component_pixels)
        if expected_size is None:
            expected_size = clean.shape
        elif clean.shape != expected_size:
            raise ValueError("All cheek source drawings must share the same canvas size.")

        outer_x_clean, outer_x_stats = extend_outer_x_edges(clean, spec["id"])
        screen = Image.fromarray(clean, mode="L")
        outer_x_screen = Image.fromarray(outer_x_clean.astype(np.uint8) * 255, mode="L")
        uv_hard_core, uv_core_stats = back_project_mask_to_uv(
            clean,
            arface,
            args.resolution,
            args.screen_sample_stride,
        )
        uv_hard, uv_stats = back_project_mask_to_uv(
            outer_x_clean,
            arface,
            args.resolution,
            args.screen_sample_stride,
        )
        uv_soft = build_soft_unity_mask(uv_hard)
        uv_density_soft = build_soft_unity_mask(uv_hard_core)
        uv_rgba, uv_density = make_cheek_rgba_mask(uv_soft, uv_density_soft, spec["id"])
        unity_path = unity_dir / (spec["id"] + ".png")

        save(output_dir / "screen" / (spec["id"] + "-source-clean.png"), screen)
        save(output_dir / "screen" / (spec["id"] + "-source-outer-x-extended.png"), outer_x_screen)
        save(output_dir / "screen" / (spec["id"] + "-source-alpha.png"), make_alpha_png(screen))
        save(output_dir / "uv" / (spec["id"] + "-uv-hard.png"), uv_hard)
        save(output_dir / "uv" / (spec["id"] + "-uv-density-source-hard.png"), uv_hard_core)
        save(output_dir / "uv" / (spec["id"] + "-uv-soft.png"), uv_soft)
        save(output_dir / "uv" / (spec["id"] + "-uv-density-source-soft.png"), uv_density_soft)
        save(output_dir / "uv" / (spec["id"] + "-uv-density.png"), uv_density)
        save(unity_path, uv_rgba)
        write_unity_meta(unity_path.with_suffix(".png.meta"), "e7-" + spec["id"])

        source_overlays.append((spec["label"], screen))
        contact_images.extend(
            [
                (spec["label"] + " screen", screen),
                (spec["label"] + " outer-x", outer_x_screen),
                (spec["label"] + " uv hard", uv_hard),
                (spec["label"] + " uv soft", uv_soft),
                (spec["label"] + " uv density B", uv_density),
            ]
        )
        summaries[spec["id"]] = {
            "label": spec["label"],
            "sourcePath": format_path(repo, source_path),
            "sourceLoad": source_load,
            "unityMaskPath": format_path(repo, unity_path),
            "screenStats": mask_stats(clean),
            "outerXExtensionStats": outer_x_stats,
            "outerXScreenStats": mask_stats(outer_x_clean.astype(np.uint8)),
            "componentStats": component_stats,
            "uvStats": uv_stats,
            "uvDensitySourceStats": uv_core_stats,
            "unityMaskStats": mask_stats(np.asarray(uv_soft, dtype=np.uint8)),
            "densityStats": mask_stats(np.asarray(uv_density, dtype=np.uint8)),
        }

    overlay = overlay_source_masks_for_comparison(reference, source_overlays)
    contact_sheet = make_contact_sheet(contact_images)
    save(output_dir / "screen" / "cheek_blush_region_comparison_overlay.png", overlay)
    save(output_dir / "cheek_blush_mask_contact_sheet.png", contact_sheet)

    summary = {
        "textureSetId": "cheek-blush-mask-textures-v1",
        "region": "cheek",
        "coordinateSpace": f"{expected_size[1]}x{expected_size[0]}" if expected_size else "unknown",
        "uvResolution": args.resolution,
        "capturePairId": pair_dir.name,
        "arfaceExportPath": format_path(repo, arface_path),
        "referencePath": format_path(repo, reference_path),
        "outputDir": format_path(repo, output_dir),
        "unityOutputDir": format_path(repo, unity_dir),
        "maskIds": [spec["id"] for spec in MASK_SPECS],
        "channelContract": {
            "r": "coverage alpha = softly expanded shape boundary only; density is not baked into this channel",
            "g": "reserved; must remain zero for cheek v1",
            "b": "style density map with center-specific Gaussian falloff",
            "a": "coverage alpha = same as R; runtime blends coverage and B density, with blush_default2 using outer/mid/core multi-band strength",
        },
        "densityProfiles": {
            spec["id"]: DENSITY_STYLE_PROFILES[spec["id"]] for spec in MASK_SPECS
        },
        "runtimeSelectionRule": "one cheek blush region mask is selected per cheek layer; generated masks are not stacked together",
        "masks": summaries,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        "# Cheek Blush Mask Textures v1\n\n"
        f"- region: `{summary['region']}`\n"
        f"- coordinateSpace: `{summary['coordinateSpace']}`\n"
        f"- uvResolution: `{summary['uvResolution']}`\n"
        f"- capturePairId: `{summary['capturePairId']}`\n"
        f"- contactSheet: `{format_path(repo, output_dir / 'cheek_blush_mask_contact_sheet.png')}`\n"
        f"- runtimeSelectionRule: `{summary['runtimeSelectionRule']}`\n"
        f"- comparisonOverlay: `{format_path(repo, output_dir / 'screen' / 'cheek_blush_region_comparison_overlay.png')}`\n"
        "  - comparison overlay is QA-only and must not be interpreted as runtime stacking\n\n"
        "## Unity Masks\n\n"
        + "\n".join(
            f"- `{mask_id}`: `{data['unityMaskPath']}`"
            for mask_id, data in summaries.items()
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
