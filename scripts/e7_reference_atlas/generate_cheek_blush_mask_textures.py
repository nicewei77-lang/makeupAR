#!/usr/bin/env python3
"""Generate Unity-ready ARFace UV cheek blush masks from face-structure anchors.

The user drawings are treated as shape templates, not fixed screen stickers.
Runtime masks regenerate that template from ARFace eye/nose anchors, face
width, and cheek bands, then store shape-specific blush density in B.
"""

from __future__ import annotations

import argparse
import json
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
    load_dark_mask,
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

ARFACE_LEFT_EYE_ANCHOR_INDICES = (1086, 1099, 1107, 1186, 1190, 1193)
ARFACE_RIGHT_EYE_ANCHOR_INDICES = (504, 1061, 1064, 1070, 1078, 1081)
ARFACE_NOSE_MIDLINE_ANCHOR_INDICES = (7, 10, 14, 15, 21, 25, 28, 38)
CHEEK_TEMPLATE_ATLAS_ID = "cheek-blush-drawing-template-atlas-v1"
CHEEK_TEMPLATE_TILE_SIZE = 128
CHEEK_TEMPLATE_ATLAS_COLUMNS = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ARFace-proportion cheek blush density masks."
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
    parser.add_argument(
        "--vision-anchor-analysis",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-vision-reference/summary.json"),
        help="Optional Apple Vision cheek reference audit evidence. It is not used as the final runtime boundary.",
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


def make_contact_sheet(images: list[tuple[str, Image.Image]], tile: int = 260) -> Image.Image:
    columns = 5
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
    safe_soft = trim_horizontal_uv_seams(variants["soft"]).filter(ImageFilter.GaussianBlur(radius=0.55))
    safe_skirt = trim_horizontal_uv_seams(variants["expanded"]).filter(ImageFilter.GaussianBlur(radius=2.40))
    soft_values = np.asarray(safe_soft, dtype=np.float32) / 255.0
    skirt_values = np.asarray(safe_skirt, dtype=np.float32) / 255.0
    return image_from_field(np.maximum(soft_values, skirt_values * 0.68))


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


def make_density_map(uv_soft: Image.Image, mask_id: str) -> Image.Image:
    alpha = np.asarray(uv_soft.convert("L"), dtype=np.float32) / 255.0
    density = np.zeros_like(alpha)
    _, width = alpha.shape
    grid_y, grid_x = np.indices(alpha.shape)

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

        if mask_id == "cheek-sunkissed-mask2-v1":
            half_width = max(box_w * 0.56, 1.0)
            alpha_gate = smoothstep_array(0.045, 0.58, alpha) * component
            side_strength = np.clip(np.abs((grid_x - cx) / half_width), 0.0, 1.0)
            ridge = 0.03 + 0.97 * np.power(side_strength, 1.55)
            vertical_core = np.exp(-((grid_y - cy) / max(box_h * 0.30, 1.0)) ** 2)
            component_density = alpha_gate * np.clip(ridge * (0.55 + 0.45 * vertical_core), 0.0, 1.0)
        else:
            direction = -1.0 if cx < width * 0.5 else 1.0
            peak_x = cx
            peak_y = cy
            sigma_x = box_w * 0.32
            sigma_y = box_h * 0.32
            base = 0.03
            cap = 1.0

            if mask_id == "cheek-daily-mask-v1":
                peak_x = cx + direction * box_w * 0.22
                peak_y = cy - box_h * 0.18
                sigma_x = box_w * 0.34
                sigma_y = box_h * 0.28
                base = 0.02
            elif mask_id == "cheek-lovely-mask-v1":
                sigma_x = box_w * 0.30
                sigma_y = box_h * 0.30
                base = 0.04
            elif mask_id == "cheek-sunkissed-mask1-v1":
                is_nose = abs(cx - width * 0.5) < width * 0.10 and box_w < width * 0.18
                sigma_x = box_w * (0.40 if is_nose else 0.32)
                sigma_y = box_h * (0.40 if is_nose else 0.30)
                base = 0.01 if is_nose else 0.04
                cap = 0.30 if is_nose else 1.0
            elif mask_id == "cheek-under-eye-mask-v1":
                peak_x = cx + direction * box_w * 0.30
                peak_y = cy - box_h * 0.24
                sigma_x = box_w * 0.30
                sigma_y = box_h * 0.24
                base = 0.015

            component_density = gaussian_density(
                alpha,
                component,
                peak_x,
                peak_y,
                sigma_x,
                sigma_y,
                base,
                cap,
            )

        density = np.maximum(density, component_density)

    density = np.clip(density, 0.0, 1.0)
    return Image.fromarray(np.rint(density * 255).astype(np.uint8), mode="L")


def make_cheek_rgba_mask(uv_soft: Image.Image, mask_id: str) -> tuple[Image.Image, Image.Image]:
    alpha = uv_soft.convert("L")
    density = make_density_map(alpha, mask_id)
    reserved = Image.new("L", alpha.size, 0)
    return Image.merge("RGBA", (alpha, reserved, density, alpha)), density


def image_from_field(field: np.ndarray) -> Image.Image:
    return Image.fromarray(np.rint(np.clip(field, 0.0, 1.0) * 255).astype(np.uint8), mode="L")


def average_screen_anchor(
    screen_vertices: np.ndarray,
    indices: tuple[int, ...],
) -> tuple[float, float] | None:
    points = []
    for index in indices:
        if 0 <= index < len(screen_vertices):
            points.append(screen_vertices[index])
    if not points:
        return None
    values = np.asarray(points, dtype=np.float32)
    return float(values[:, 0].mean()), float(values[:, 1].mean())


def face_metrics(arface: dict[str, np.ndarray], frame_size: tuple[int, int]) -> dict[str, float | str | bool]:
    screen_vertices = arface["screenVertices"]
    frame_width, frame_height = frame_size
    left, right = np.percentile(screen_vertices[:, 0], [2, 98])
    top, bottom = np.percentile(screen_vertices[:, 1], [2, 98])
    left = float(np.clip(left, 0.0, frame_width - 1))
    right = float(np.clip(right, 0.0, frame_width - 1))
    top = float(np.clip(top, 0.0, frame_height - 1))
    bottom = float(np.clip(bottom, 0.0, frame_height - 1))
    width = max(right - left, 1.0)
    height = max(bottom - top, 1.0)
    center_x = (left + right) * 0.5
    eye_line_y = top + height * 0.331
    metric_source = "p2p98_bbox_fallback"

    left_eye = average_screen_anchor(screen_vertices, ARFACE_LEFT_EYE_ANCHOR_INDICES)
    right_eye = average_screen_anchor(screen_vertices, ARFACE_RIGHT_EYE_ANCHOR_INDICES)
    if left_eye is not None and right_eye is not None:
        eye_line_y = float(
            np.clip(
                (left_eye[1] + right_eye[1]) * 0.5,
                top + height * 0.180,
                top + height * 0.450,
            )
        )
        metric_source = "arface_topology_eye_anchor_vertices"

    nose_midline = average_screen_anchor(screen_vertices, ARFACE_NOSE_MIDLINE_ANCHOR_INDICES)
    if nose_midline is not None:
        center_x = float(np.clip(nose_midline[0], left + width * 0.420, left + width * 0.580))
        metric_source += "_nose_midline_center"

    return {
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "width": width,
        "height": height,
        "centerX": center_x,
        "noseCenterX": center_x,
        "eyeLineY": eye_line_y,
        "underEyeY": eye_line_y + height * 0.117,
        "cheekboneY": eye_line_y + height * 0.155,
        "highCheekY": eye_line_y + height * 0.175,
        "appleY": eye_line_y + height * 0.195,
        "noseBridgeY": eye_line_y + height * 0.181,
        "metricSource": metric_source,
        "usedTopologyEyeAnchors": left_eye is not None and right_eye is not None,
        "usedTopologyNoseMidline": nose_midline is not None,
    }


def load_vision_anchor_analysis(path: Path | None) -> dict[str, object]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    shapes = data.get("mappedRecommendations", {}).get("shapes", {})
    anchors_by_mask: dict[str, object] = {}
    if not isinstance(shapes, dict):
        return {}

    for shape_data in shapes.values():
        if not isinstance(shape_data, dict):
            continue
        mask_id = shape_data.get("maskId")
        anchors = shape_data.get("mappedAnchorsOnCaptureFrame")
        if isinstance(mask_id, str) and isinstance(anchors, list):
            anchors_by_mask[mask_id] = anchors
    return {
        "path": str(path),
        "gateId": data.get("gateId", "unknown"),
        "appleVisionRole": data.get("appleVisionRole", ""),
        "diagnosticSheet": data.get("diagnosticSheet", ""),
        "anchorsByMaskId": anchors_by_mask,
        "usage": "landmark_anchor_audit_not_cheek_boundary_source",
    }


def make_reference_calibration(
    reference_mask: Image.Image,
    metrics: dict[str, float],
) -> dict[str, object]:
    alpha = np.asarray(reference_mask.convert("L"), dtype=np.float32) / 255.0
    components: list[dict[str, float | int]] = []
    for component in iter_components(alpha, min_pixels=180):
        ys, xs = np.nonzero(component)
        if len(xs) == 0:
            continue

        components.append(
            {
                "cx": float(xs.mean()),
                "cy": float(ys.mean()),
                "left": int(xs.min()),
                "top": int(ys.min()),
                "right": int(xs.max()),
                "bottom": int(ys.max()),
                "width": int(xs.max() - xs.min() + 1),
                "height": int(ys.max() - ys.min() + 1),
                "pixels": int(len(xs)),
            }
        )

    if not components:
        return {"components": [], "left": None, "right": None, "center": None, "global": None}

    center_x = metrics["centerX"]
    side_deadzone = metrics["width"] * 0.065
    left_components = [item for item in components if float(item["cx"]) < center_x - side_deadzone]
    right_components = [item for item in components if float(item["cx"]) > center_x + side_deadzone]
    center_components = [item for item in components if abs(float(item["cx"]) - center_x) <= side_deadzone]

    def largest(items: list[dict[str, float | int]]) -> dict[str, float | int] | None:
        if not items:
            return None
        return max(items, key=lambda item: int(item["pixels"]))

    all_left = min(int(item["left"]) for item in components)
    all_right = max(int(item["right"]) for item in components)
    all_top = min(int(item["top"]) for item in components)
    all_bottom = max(int(item["bottom"]) for item in components)
    global_box = {
        "cx": float(np.mean([float(item["cx"]) for item in components])),
        "cy": float(np.mean([float(item["cy"]) for item in components])),
        "left": all_left,
        "top": all_top,
        "right": all_right,
        "bottom": all_bottom,
        "width": all_right - all_left + 1,
        "height": all_bottom - all_top + 1,
        "pixels": int(sum(int(item["pixels"]) for item in components)),
    }
    return {
        "components": components,
        "left": largest(left_components),
        "right": largest(right_components),
        "center": largest(center_components),
        "global": global_box,
    }


def anchor(metrics: dict[str, float], side: float, x_scale: float, y_scale: float) -> tuple[float, float]:
    return (
        metrics["centerX"] + side * metrics["width"] * x_scale,
        metrics["top"] + metrics["height"] * y_scale,
    )


def ellipse_field(
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    center_x: float,
    center_y: float,
    radius_x: float,
    radius_y: float,
    angle: float = 0.0,
    exponent: float = 1.0,
    cap: float = 1.0,
) -> np.ndarray:
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    dx = grid_x - center_x
    dy = grid_y - center_y
    rotated_x = dx * cos_a + dy * sin_a
    rotated_y = -dx * sin_a + dy * cos_a
    norm = (rotated_x / max(radius_x, 1.0)) ** 2 + (rotated_y / max(radius_y, 1.0)) ** 2
    field = np.exp(-norm)
    if exponent != 1.0:
        field = np.power(field, exponent)
    return np.clip(field * cap, 0.0, 1.0)


def finalize_fields(alpha_raw: np.ndarray, density_raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    alpha = smoothstep_array(0.10, 0.52, np.clip(alpha_raw, 0.0, 1.0))
    density = np.clip(density_raw, 0.0, 1.0)
    density *= smoothstep_array(0.025, 0.36, alpha)
    return alpha, density


def silhouette_density_floor(mask_id: str) -> float:
    if mask_id == "cheek-sunkissed-mask1-v1":
        return 0.34
    if mask_id == "cheek-sunkissed-mask2-v1":
        return 0.38
    if mask_id == "cheek-under-eye-mask-v1":
        return 0.36
    return 0.24


def component_role_sequence(mask_id: str) -> tuple[str, ...]:
    if mask_id == "cheek-sunkissed-mask2-v1":
        return ("global",)
    if mask_id == "cheek-sunkissed-mask1-v1":
        return ("left", "right", "center")
    return ("left", "right")


def target_component_box(
    mask_id: str,
    role: str,
    component: dict[str, float | int],
    metrics: dict[str, float],
) -> dict[str, int | float | str]:
    source_cx = float(component["cx"])
    source_cy = float(component["cy"])
    source_width = float(component["width"])
    source_height = float(component["height"])

    if role in ("left", "right"):
        side = -1.0 if role == "left" else 1.0
        x_ratio = abs(source_cx - metrics["centerX"]) / metrics["width"]
        target_cx = metrics["centerX"] + side * metrics["width"] * x_ratio
    else:
        x_ratio = (source_cx - metrics["centerX"]) / metrics["width"]
        target_cx = metrics["centerX"] + metrics["width"] * x_ratio

    y_ratio = (source_cy - metrics["eyeLineY"]) / metrics["height"]
    width_ratio = source_width / metrics["width"]
    height_ratio = source_height / metrics["height"]

    if mask_id == "cheek-sunkissed-mask1-v1" and role == "center":
        y_ratio = min(y_ratio, 0.195)
    elif mask_id == "cheek-sunkissed-mask2-v1" and role == "global":
        y_ratio = min(y_ratio, 0.150)

    target_width = max(int(round(metrics["width"] * width_ratio)), 1)
    target_height = max(int(round(metrics["height"] * height_ratio)), 1)
    target_cy = metrics["eyeLineY"] + metrics["height"] * y_ratio
    left = int(round(target_cx - target_width * 0.5))
    top = int(round(target_cy - target_height * 0.5))
    return {
        "role": role,
        "sourceCx": round(source_cx, 3),
        "sourceCy": round(source_cy, 3),
        "targetCx": round(float(target_cx), 3),
        "targetCy": round(float(target_cy), 3),
        "targetLeft": left,
        "targetTop": top,
        "targetWidth": target_width,
        "targetHeight": target_height,
        "xRatio": round(float(x_ratio), 4),
        "yRatio": round(float(y_ratio), 4),
        "widthRatio": round(float(width_ratio), 4),
        "heightRatio": round(float(height_ratio), 4),
    }


def paste_component_template(
    output: np.ndarray,
    reference_source: Image.Image,
    component: dict[str, float | int],
    target: dict[str, int | float | str],
) -> None:
    source_box = (
        int(component["left"]),
        int(component["top"]),
        int(component["right"]) + 1,
        int(component["bottom"]) + 1,
    )
    target_width = int(target["targetWidth"])
    target_height = int(target["targetHeight"])
    if target_width <= 0 or target_height <= 0:
        return

    crop = reference_source.crop(source_box).convert("L")
    resized = crop.resize((target_width, target_height), Image.Resampling.LANCZOS)
    resized = resized.filter(ImageFilter.GaussianBlur(radius=0.55))
    patch = np.asarray(resized, dtype=np.float32) / 255.0
    left = int(target["targetLeft"])
    top = int(target["targetTop"])
    right = left + target_width
    bottom = top + target_height
    out_height, out_width = output.shape
    clip_left = max(left, 0)
    clip_top = max(top, 0)
    clip_right = min(right, out_width)
    clip_bottom = min(bottom, out_height)
    if clip_right <= clip_left or clip_bottom <= clip_top:
        return

    patch_left = clip_left - left
    patch_top = clip_top - top
    patch_right = patch_left + (clip_right - clip_left)
    patch_bottom = patch_top + (clip_bottom - clip_top)
    output[clip_top:clip_bottom, clip_left:clip_right] = np.maximum(
        output[clip_top:clip_bottom, clip_left:clip_right],
        patch[patch_top:patch_bottom, patch_left:patch_right],
    )


def make_shape_template_screen_alpha(
    reference_source: Image.Image,
    mask_id: str,
    calibration: dict[str, object],
    metrics: dict[str, float],
    frame_size: tuple[int, int],
) -> tuple[Image.Image, dict[str, object]]:
    width, height = frame_size
    output = np.zeros((height, width), dtype=np.float32)
    components: list[dict[str, int | float | str]] = []
    for role in component_role_sequence(mask_id):
        component = calibration.get(role)
        if not isinstance(component, dict):
            continue
        target = target_component_box(mask_id, role, component, metrics)
        paste_component_template(output, reference_source, component, target)
        components.append(target)

    if not components:
        return Image.new("L", frame_size, 0), {
            "source": "empty_reference_shape_template",
            "components": [],
        }

    alpha = image_from_field(output)
    return alpha, {
        "source": "user_drawing_silhouette_shape_template",
        "warp": "face_proportion_translate_scale_by_eye_line_nose_center_face_width",
        "components": components,
    }


def collect_runtime_template_tiles(
    reference_source: Image.Image,
    mask_id: str,
    calibration: dict[str, object],
    metrics: dict[str, float],
) -> list[dict[str, object]]:
    tiles: list[dict[str, object]] = []
    for role in component_role_sequence(mask_id):
        component = calibration.get(role)
        if not isinstance(component, dict):
            continue
        target = target_component_box(mask_id, role, component, metrics)
        tiles.append(
            {
                **target,
                "maskTextureId": mask_id,
                "sourceLeft": int(component["left"]),
                "sourceTop": int(component["top"]),
                "sourceRight": int(component["right"]),
                "sourceBottom": int(component["bottom"]),
                "sourceWidth": int(component["width"]),
                "sourceHeight": int(component["height"]),
                "referenceSource": reference_source,
            }
        )
    return tiles


def make_runtime_template_atlas(
    tiles: list[dict[str, object]],
) -> tuple[Image.Image, list[dict[str, object]]]:
    rows = max(1, int(np.ceil(len(tiles) / CHEEK_TEMPLATE_ATLAS_COLUMNS)))
    alpha = Image.new(
        "L",
        (CHEEK_TEMPLATE_ATLAS_COLUMNS * CHEEK_TEMPLATE_TILE_SIZE, rows * CHEEK_TEMPLATE_TILE_SIZE),
        0,
    )
    summary_tiles: list[dict[str, object]] = []
    for index, tile in enumerate(tiles):
        source = tile["referenceSource"]
        assert isinstance(source, Image.Image)
        source_box = (
            int(tile["sourceLeft"]),
            int(tile["sourceTop"]),
            int(tile["sourceRight"]) + 1,
            int(tile["sourceBottom"]) + 1,
        )
        col = index % CHEEK_TEMPLATE_ATLAS_COLUMNS
        row = index // CHEEK_TEMPLATE_ATLAS_COLUMNS
        x = col * CHEEK_TEMPLATE_TILE_SIZE
        y = row * CHEEK_TEMPLATE_TILE_SIZE
        crop = source.crop(source_box).convert("L")
        resized = crop.resize(
            (CHEEK_TEMPLATE_TILE_SIZE, CHEEK_TEMPLATE_TILE_SIZE),
            Image.Resampling.LANCZOS,
        ).filter(ImageFilter.GaussianBlur(radius=0.55))
        alpha.paste(resized, (x, y))

        summary_tile = {
            key: value
            for key, value in tile.items()
            if key != "referenceSource"
        }
        summary_tile.update(
            {
                "tileIndex": index,
                "tileColumn": col,
                "tileRow": row,
                "tileLeft": x,
                "tileTop": y,
                "tileSize": CHEEK_TEMPLATE_TILE_SIZE,
            }
        )
        summary_tiles.append(summary_tile)

    zero = Image.new("L", alpha.size, 0)
    atlas = Image.merge("RGBA", (alpha, zero, zero, alpha))
    return atlas, summary_tiles


def make_proportion_screen_fields(
    arface: dict[str, np.ndarray],
    frame_size: tuple[int, int],
    mask_id: str,
    reference_source: Image.Image,
    calibration: dict[str, object],
    vision_analysis: dict[str, object],
) -> tuple[Image.Image, Image.Image, dict[str, object]]:
    width, height = frame_size
    metrics = face_metrics(arface, frame_size)
    grid_y, grid_x = np.indices((height, width), dtype=np.float32)
    template_alpha, template_summary = make_shape_template_screen_alpha(
        reference_source,
        mask_id,
        calibration,
        metrics,
        frame_size,
    )
    alpha = np.asarray(template_alpha.convert("L"), dtype=np.float32) / 255.0
    template_alpha_available = bool(np.count_nonzero(alpha > 0.03))
    density = np.zeros((height, width), dtype=np.float32)
    anchors: list[dict[str, float | str]] = []

    def record(name: str, x: float, y: float, strength: float) -> None:
        anchors.append(
            {
                "name": name,
                "x": round(float(x), 3),
                "y": round(float(y), 3),
                "strength": round(float(strength), 3),
            }
        )

    def structural_anchor(side: float, x_ratio: float, y_from_eye_ratio: float) -> tuple[float, float]:
        return (
            metrics["centerX"] + side * metrics["width"] * x_ratio,
            metrics["eyeLineY"] + metrics["height"] * y_from_eye_ratio,
        )

    def side_anatomy_gate(center_x: float, center_y: float, side: float, radius_x: float, radius_y: float) -> np.ndarray:
        top_gate = smoothstep_array(
            metrics["eyeLineY"] + metrics["height"] * 0.058,
            metrics["eyeLineY"] + metrics["height"] * 0.092,
            grid_y,
        )
        bottom_gate = 1.0 - smoothstep_array(
            metrics["eyeLineY"] + metrics["height"] * 0.370,
            metrics["eyeLineY"] + metrics["height"] * 0.445,
            grid_y,
        )
        nose_clearance = smoothstep_array(
            metrics["width"] * 0.150,
            metrics["width"] * 0.245,
            side * (grid_x - metrics["centerX"]),
        )
        outer_limit = 1.0 - smoothstep_array(
            metrics["width"] * 0.470,
            metrics["width"] * 0.565,
            np.abs(grid_x - metrics["centerX"]),
        )
        local_x = side * (grid_x - center_x)
        cheek_lift = 1.0 - smoothstep_array(
            radius_y * 1.05,
            radius_y * 1.85,
            grid_y - center_y,
        )
        outward_softness = 1.0 - smoothstep_array(
            radius_x * 1.10,
            radius_x * 1.80,
            np.abs(local_x),
        )
        return np.clip(top_gate * bottom_gate * nose_clearance * outer_limit * cheek_lift * outward_softness, 0.0, 1.0)

    def add_side_field(
        side_name: str,
        side: float,
        x_ratio: float,
        y_from_eye_ratio: float,
        radius_x_ratio: float,
        radius_y_ratio: float,
        angle: float,
        peak_offset_x: float,
        peak_offset_y: float,
        record_name: str,
        density_cap: float = 1.0,
        write_alpha: bool = False,
    ) -> None:
        nonlocal alpha, density
        center_x, center_y = structural_anchor(side, x_ratio, y_from_eye_ratio)
        radius_x = metrics["width"] * radius_x_ratio
        radius_y = metrics["height"] * radius_y_ratio
        gate = side_anatomy_gate(center_x, center_y, side, radius_x, radius_y)
        side_alpha = ellipse_field(grid_x, grid_y, center_x, center_y, radius_x, radius_y, angle) * gate
        peak_x = center_x + side * radius_x * peak_offset_x
        peak_y = center_y + radius_y * peak_offset_y
        density_core = ellipse_field(
            grid_x,
            grid_y,
            peak_x,
            peak_y,
            radius_x * 0.66,
            radius_y * 0.70,
            angle,
            cap=density_cap,
        )
        density_wash = ellipse_field(
            grid_x,
            grid_y,
            peak_x,
            peak_y,
            radius_x * 1.08,
            radius_y * 1.04,
            angle,
            cap=density_cap * 0.50,
        )
        side_density = np.maximum(density_core, density_wash) * gate
        if write_alpha:
            alpha = np.maximum(alpha, side_alpha)
        density = np.maximum(density, side_density)
        record(f"{side_name}_{record_name}", peak_x, peak_y, density_cap)

    def add_under_eye_field(side_name: str, side: float, write_alpha: bool = False) -> None:
        nonlocal alpha, density
        center_x, center_y = structural_anchor(side, 0.345, 0.140)
        radius_x = metrics["width"] * 0.168
        radius_y = metrics["height"] * 0.106
        angle = -side * 0.12
        top_gate = smoothstep_array(
            metrics["eyeLineY"] + metrics["height"] * 0.026,
            metrics["eyeLineY"] + metrics["height"] * 0.048,
            grid_y,
        )
        bottom_gate = 1.0 - smoothstep_array(
            metrics["eyeLineY"] + metrics["height"] * 0.205,
            metrics["eyeLineY"] + metrics["height"] * 0.270,
            grid_y,
        )
        nose_clearance = smoothstep_array(
            metrics["width"] * 0.185,
            metrics["width"] * 0.290,
            side * (grid_x - metrics["centerX"]),
        )
        lower_eyelid_clearance = smoothstep_array(
            metrics["eyeLineY"] + metrics["height"] * 0.036,
            metrics["eyeLineY"] + metrics["height"] * 0.074,
            grid_y,
        )
        gate = np.clip(top_gate * bottom_gate * nose_clearance * lower_eyelid_clearance, 0.0, 1.0)
        under_alpha = ellipse_field(grid_x, grid_y, center_x, center_y, radius_x, radius_y, angle) * gate
        peak_x = center_x + side * radius_x * 0.46
        peak_y = center_y - radius_y * 0.24
        outward_gate = smoothstep_array(metrics["width"] * 0.008, metrics["width"] * 0.086, side * (grid_x - center_x))
        density_core = ellipse_field(grid_x, grid_y, peak_x, peak_y, radius_x * 0.68, radius_y * 0.72, angle)
        density_wash = ellipse_field(grid_x, grid_y, peak_x, peak_y, radius_x * 1.12, radius_y * 1.04, angle, cap=0.74)
        under_density = np.maximum(density_core * outward_gate, density_wash * (0.52 + 0.48 * outward_gate)) * gate
        if write_alpha:
            alpha = np.maximum(alpha, under_alpha)
        density = np.maximum(density, under_density)
        record(f"{side_name}_outer_undereye_high_cheek_peak", peak_x, peak_y, 1.0)

    for side_name, side in (("left", -1.0), ("right", 1.0)):
        if mask_id == "cheek-daily-mask-v1":
            add_side_field(
                side_name,
                side,
                0.300,
                0.178,
                0.145,
                0.083,
                -side * 0.20,
                0.30,
                -0.26,
                "outer_high_cheekbone_peak",
                write_alpha=not template_alpha_available,
            )
        elif mask_id == "cheek-lovely-mask-v1":
            add_side_field(
                side_name,
                side,
                0.296,
                0.190,
                0.122,
                0.102,
                0.0,
                0.0,
                0.0,
                "apple_center_peak",
                write_alpha=not template_alpha_available,
            )
        elif mask_id == "cheek-sunkissed-mask1-v1":
            add_side_field(
                side_name,
                side,
                0.400,
                0.209,
                0.118,
                0.146,
                0.0,
                0.0,
                -0.04,
                "sun_cheek_peak",
                write_alpha=not template_alpha_available,
            )
        elif mask_id == "cheek-sunkissed-mask2-v1":
            add_side_field(
                side_name,
                side,
                0.360,
                0.168,
                0.185,
                0.078,
                -side * 0.13,
                0.18,
                -0.06,
                "w_cheekbone_end_peak",
                write_alpha=not template_alpha_available,
            )
        elif mask_id == "cheek-under-eye-mask-v1":
            add_under_eye_field(side_name, side, write_alpha=not template_alpha_available)

    if mask_id == "cheek-sunkissed-mask1-v1":
        nose_x = metrics["noseCenterX"]
        nose_y = metrics["eyeLineY"] + metrics["height"] * 0.168
        nose_alpha = ellipse_field(
            grid_x,
            grid_y,
            nose_x,
            nose_y,
            metrics["width"] * 0.034,
            metrics["height"] * 0.030,
            cap=0.50,
        )
        nose_density = ellipse_field(
            grid_x,
            grid_y,
            nose_x,
            nose_y - metrics["height"] * 0.012,
            metrics["width"] * 0.021,
            metrics["height"] * 0.017,
            cap=0.16,
        )
        if not template_alpha_available:
            alpha = np.maximum(alpha, nose_alpha)
        density = np.maximum(density, nose_density)
        record("raised_low_density_nose_bridge_not_nostrils", nose_x, nose_y, 0.16)
    elif mask_id == "cheek-sunkissed-mask2-v1":
        bridge_x = metrics["noseCenterX"]
        bridge_y = metrics["eyeLineY"] + metrics["height"] * 0.148
        bridge_alpha = ellipse_field(
            grid_x,
            grid_y,
            bridge_x,
            bridge_y,
            metrics["width"] * 0.360,
            metrics["height"] * 0.052,
            cap=0.50,
        )
        bridge_density = ellipse_field(
            grid_x,
            grid_y,
            bridge_x,
            bridge_y,
            metrics["width"] * 0.205,
            metrics["height"] * 0.025,
            cap=0.20,
        )
        if not template_alpha_available:
            alpha = np.maximum(alpha, bridge_alpha)
        density = np.maximum(density, bridge_density)
        record("low_density_raised_nose_bridge_connector", bridge_x, bridge_y, 0.20)

    if template_alpha_available:
        density = np.maximum(density, np.clip(alpha, 0.0, 1.0) * silhouette_density_floor(mask_id))

    alpha, density = finalize_fields(alpha, density)
    return image_from_field(alpha), image_from_field(density), {
        "maskSource": "arface_face_proportion_anchor_density",
        "faceBBoxP2P98": {
            key: round(float(metrics[key]), 3)
            for key in ("left", "top", "right", "bottom", "width", "height", "centerX")
        },
        "metricSource": metrics["metricSource"],
        "usedTopologyEyeAnchors": bool(metrics["usedTopologyEyeAnchors"]),
        "usedTopologyNoseMidline": bool(metrics["usedTopologyNoseMidline"]),
        "anchors": anchors,
        "shapeTemplateSummary": template_summary,
        "appleVisionAnchorGateId": vision_analysis.get("gateId", "none"),
        "appleVisionAnchorRole": "landmark_anchor_audit_not_cheek_boundary_source",
    }


def back_project_field_to_uv(
    source_field: np.ndarray,
    arface: dict[str, np.ndarray],
    resolution: int,
    sample_stride: int,
    threshold: float,
) -> tuple[Image.Image, dict[str, object]]:
    field = np.clip(source_field.astype(np.float32), 0.0, 1.0)
    rows, cols = np.nonzero(field > threshold)
    if len(cols) == 0:
        raise ValueError("Cannot back-project an empty cheek field.")

    sample_stride = max(1, int(sample_stride))
    mask_left = int(cols.min())
    mask_right = int(cols.max())
    mask_top = int(rows.min())
    mask_bottom = int(rows.max())
    screen_vertices = arface["screenVertices"]
    uvs = arface["uvs"]
    triangles = arface["indices"]
    uv_values = np.zeros((resolution, resolution), dtype=np.float32)
    hit_triangle_count = 0
    hit_sample_count = 0
    skipped_degenerate_triangle_count = 0
    epsilon = 1.0e-4

    for triangle in triangles:
        screen_points = screen_vertices[triangle]
        uv_points = uvs[triangle]
        left = max(int(np.floor(float(screen_points[:, 0].min()))), mask_left)
        right = min(int(np.ceil(float(screen_points[:, 0].max()))), mask_right)
        top = max(int(np.floor(float(screen_points[:, 1].min()))), mask_top)
        bottom = min(int(np.ceil(float(screen_points[:, 1].max()))), mask_bottom)
        if right < left or bottom < top:
            continue

        x1, y1 = screen_points[0]
        x2, y2 = screen_points[1]
        x3, y3 = screen_points[2]
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(float(denominator)) < 1.0e-5:
            skipped_degenerate_triangle_count += 1
            continue

        grid_x = np.arange(left, right + 1, sample_stride, dtype=np.float32) + 0.5
        grid_y = np.arange(top, bottom + 1, sample_stride, dtype=np.float32) + 0.5
        pixel_x, pixel_y = np.meshgrid(grid_x, grid_y)
        source_x = np.clip(pixel_x.astype(np.int32), 0, field.shape[1] - 1)
        source_y = np.clip(pixel_y.astype(np.int32), 0, field.shape[0] - 1)
        samples = field[source_y, source_x]
        weight_a = (((y2 - y3) * (pixel_x - x3) + (x3 - x2) * (pixel_y - y3)) / denominator)
        weight_b = (((y3 - y1) * (pixel_x - x3) + (x1 - x3) * (pixel_y - y3)) / denominator)
        weight_c = 1.0 - weight_a - weight_b
        inside_triangle = (
            (weight_a >= -epsilon)
            & (weight_b >= -epsilon)
            & (weight_c >= -epsilon)
            & (samples > threshold)
        )
        if not inside_triangle.any():
            continue

        hit_triangle_count += 1
        hit_sample_count += int(inside_triangle.sum())
        projected_u = (
            weight_a[inside_triangle] * uv_points[0, 0]
            + weight_b[inside_triangle] * uv_points[1, 0]
            + weight_c[inside_triangle] * uv_points[2, 0]
        )
        projected_v = (
            weight_a[inside_triangle] * uv_points[0, 1]
            + weight_b[inside_triangle] * uv_points[1, 1]
            + weight_c[inside_triangle] * uv_points[2, 1]
        )
        valid_uv = (
            (projected_u >= 0.0)
            & (projected_u <= 1.0)
            & (projected_v >= 0.0)
            & (projected_v <= 1.0)
        )
        if not valid_uv.any():
            continue

        atlas_x = np.rint(projected_u[valid_uv] * (resolution - 1)).astype(np.int32)
        atlas_y = np.rint((1.0 - projected_v[valid_uv]) * (resolution - 1)).astype(np.int32)
        np.maximum.at(uv_values, (atlas_y, atlas_x), samples[inside_triangle][valid_uv])

    projected = image_from_field(uv_values)
    stats = mask_stats(np.asarray(projected, dtype=np.uint8))
    stats.update(
        {
            "hitTriangleCount": hit_triangle_count,
            "hitSampleCount": hit_sample_count,
            "rawUvPixelCount": int((uv_values > 0).sum()),
            "maxValue": round(float(uv_values.max()), 6),
            "skippedDegenerateTriangleCount": skipped_degenerate_triangle_count,
            "screenSampleStride": sample_stride,
        }
    )
    return projected, stats


def build_density_unity_mask(uv_density_hard: Image.Image, uv_alpha_soft: Image.Image) -> Image.Image:
    density = uv_density_hard.convert("L").filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(radius=0.70))
    density_values = np.asarray(density, dtype=np.float32) / 255.0
    alpha_values = np.asarray(uv_alpha_soft.convert("L"), dtype=np.float32) / 255.0
    gated = density_values * smoothstep_array(0.015, 0.48, alpha_values)
    powder_floor = alpha_values * 0.10
    gated = np.maximum(gated, powder_floor)
    return image_from_field(np.clip(gated, 0.0, 1.0))


def make_cheek_rgba_mask_from_fields(uv_alpha: Image.Image, uv_density: Image.Image) -> Image.Image:
    alpha = uv_alpha.convert("L")
    density = uv_density.convert("L")
    reserved = Image.new("L", alpha.size, 0)
    return Image.merge("RGBA", (alpha, reserved, density, alpha))


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
    vision_anchor_path = resolve_path(repo, args.vision_anchor_analysis)
    if not arface_path.exists():
        raise FileNotFoundError("ARFace export does not exist: " + str(arface_path))
    if reference_path is None or not reference_path.exists():
        raise FileNotFoundError("Reference image does not exist: " + str(reference_path))

    arface = load_arface_export(arface_path)
    reference = Image.open(reference_path).convert("RGB")
    vision_anchor_analysis = load_vision_anchor_analysis(vision_anchor_path)
    source_overlays: list[tuple[str, Image.Image]] = []
    contact_images: list[tuple[str, Image.Image]] = []
    runtime_template_tiles: list[dict[str, object]] = []
    summaries: dict[str, object] = {}
    expected_size: tuple[int, int] = (reference.height, reference.width)

    for spec in MASK_SPECS:
        source_path = resolve_path(repo, getattr(args, spec["arg"]))
        if source_path is not None and source_path.exists():
            raw = load_dark_mask(source_path, args.dark_threshold)
            clean, component_stats = keep_components(raw, args.min_component_pixels)
            reference_source = Image.fromarray(clean, mode="L")
            if reference_source.size != reference.size:
                reference_source = reference_source.resize(reference.size, Image.Resampling.NEAREST)
        else:
            component_stats = {
                "componentCount": 0,
                "keptComponentCount": 0,
                "keptPixelCount": 0,
                "removedPixelCount": 0,
            }
            reference_source = Image.new("L", reference.size, 0)

        metrics = face_metrics(arface, reference.size)
        reference_calibration = make_reference_calibration(reference_source, metrics)
        runtime_template_tiles.extend(
            collect_runtime_template_tiles(
                reference_source,
                spec["id"],
                reference_calibration,
                metrics,
            )
        )
        screen_alpha, screen_density, anchor_summary = make_proportion_screen_fields(
            arface,
            reference.size,
            spec["id"],
            reference_source,
            reference_calibration,
            vision_anchor_analysis,
        )
        screen_alpha_values = np.asarray(screen_alpha, dtype=np.float32) / 255.0
        screen_density_values = np.asarray(screen_density, dtype=np.float32) / 255.0
        uv_hard, uv_stats = back_project_field_to_uv(
            screen_alpha_values,
            arface,
            args.resolution,
            args.screen_sample_stride,
            threshold=0.018,
        )
        uv_density_hard, uv_density_stats = back_project_field_to_uv(
            screen_density_values,
            arface,
            args.resolution,
            args.screen_sample_stride,
            threshold=0.010,
        )
        uv_soft = build_soft_unity_mask(uv_hard)
        uv_density = build_density_unity_mask(uv_density_hard, uv_soft)
        uv_rgba = make_cheek_rgba_mask_from_fields(uv_soft, uv_density)
        unity_path = unity_dir / (spec["id"] + ".png")

        save(output_dir / "screen" / (spec["id"] + "-reference-drawing-clean.png"), reference_source)
        save(output_dir / "screen" / (spec["id"] + "-reference-drawing-alpha.png"), make_alpha_png(reference_source))
        save(output_dir / "screen" / (spec["id"] + "-face-anchor-alpha.png"), screen_alpha)
        save(output_dir / "screen" / (spec["id"] + "-face-anchor-density.png"), screen_density)
        save(output_dir / "uv" / (spec["id"] + "-uv-hard.png"), uv_hard)
        save(output_dir / "uv" / (spec["id"] + "-uv-soft.png"), uv_soft)
        save(output_dir / "uv" / (spec["id"] + "-uv-density-hard.png"), uv_density_hard)
        save(output_dir / "uv" / (spec["id"] + "-uv-density.png"), uv_density)
        save(unity_path, uv_rgba)
        unity_meta_path = unity_path.with_suffix(".png.meta")
        if not unity_meta_path.exists():
            write_unity_meta(unity_meta_path, "e7-" + spec["id"])

        source_overlays.append((spec["label"], reference_source))
        contact_images.extend(
            [
                (spec["label"] + " reference drawing", reference_source),
                (spec["label"] + " face alpha", screen_alpha),
                (spec["label"] + " face density", screen_density),
                (spec["label"] + " uv soft alpha", uv_soft),
                (spec["label"] + " uv density B", uv_density),
            ]
        )
        summaries[spec["id"]] = {
            "label": spec["label"],
            "sourcePath": format_path(repo, source_path) if source_path else "none",
            "drawingRole": "shape_template_for_face_proportion_warp_not_screen_sticker",
            "referenceCalibrationRole": "shape_template_calibration_not_fixed_runtime_boundary",
            "appleVisionAnchorRole": "landmark_anchor_audit_not_cheek_boundary_source",
            "appleVisionReferenceAnchorAudit": (
                vision_anchor_analysis.get("anchorsByMaskId", {}).get(spec["id"], [])
                if isinstance(vision_anchor_analysis.get("anchorsByMaskId"), dict)
                else []
            ),
            "unityMaskPath": format_path(repo, unity_path),
            "faceAnchorSummary": anchor_summary,
            "referenceCalibration": reference_calibration,
            "referenceDrawingStats": mask_stats(np.asarray(reference_source, dtype=np.uint8)),
            "componentStats": component_stats,
            "screenAlphaStats": mask_stats(np.asarray(screen_alpha, dtype=np.uint8)),
            "screenDensityStats": mask_stats(np.asarray(screen_density, dtype=np.uint8)),
            "uvAlphaStats": uv_stats,
            "uvDensityHardStats": uv_density_stats,
            "unityMaskStats": mask_stats(np.asarray(uv_soft, dtype=np.uint8)),
            "densityStats": mask_stats(np.asarray(uv_density, dtype=np.uint8)),
        }

    overlay = overlay_source_masks_for_comparison(reference, source_overlays)
    contact_sheet = make_contact_sheet(contact_images)
    template_atlas, template_atlas_tiles = make_runtime_template_atlas(runtime_template_tiles)
    template_atlas_path = unity_dir / (CHEEK_TEMPLATE_ATLAS_ID + ".png")
    save(output_dir / "screen" / "cheek_blush_region_comparison_overlay.png", overlay)
    save(output_dir / "cheek_blush_mask_contact_sheet.png", contact_sheet)
    save(output_dir / "cheek_blush_drawing_template_atlas.png", template_atlas)
    save(template_atlas_path, template_atlas)
    template_meta_path = template_atlas_path.with_suffix(".png.meta")
    if not template_meta_path.exists():
        write_unity_meta(template_meta_path, "e7-" + CHEEK_TEMPLATE_ATLAS_ID)

    summary = {
        "textureSetId": "cheek-blush-mask-textures-v1",
        "region": "cheek",
        "maskSource": "arface_face_proportion_anchor_density",
        "drawingRole": "shape_template_for_face_proportion_warp_not_screen_sticker",
        "referenceCalibrationRole": "shape_template_calibration_not_fixed_runtime_boundary",
        "appleVisionAnchorRole": "landmark_anchor_audit_not_cheek_boundary_source",
        "appleVisionAnchorAnalysisPath": (
            format_path(repo, vision_anchor_path)
            if vision_anchor_path is not None and vision_anchor_path.exists()
            else "none"
        ),
        "coordinateSpace": f"{expected_size[1]}x{expected_size[0]}",
        "uvResolution": args.resolution,
        "capturePairId": pair_dir.name,
        "arfaceExportPath": format_path(repo, arface_path),
        "referencePath": format_path(repo, reference_path),
        "outputDir": format_path(repo, output_dir),
        "unityOutputDir": format_path(repo, unity_dir),
        "runtimeTemplateAtlas": {
            "id": CHEEK_TEMPLATE_ATLAS_ID,
            "path": format_path(repo, template_atlas_path),
            "evidencePath": format_path(repo, output_dir / "cheek_blush_drawing_template_atlas.png"),
            "tileSize": CHEEK_TEMPLATE_TILE_SIZE,
            "columns": CHEEK_TEMPLATE_ATLAS_COLUMNS,
            "tiles": template_atlas_tiles,
        },
        "maskIds": [spec["id"] for spec in MASK_SPECS],
        "channelContract": {
            "r": "soft blush alpha",
            "g": "reserved; must remain zero for cheek v1",
            "b": "per-shape density map for center-strong powder pigment",
            "a": "soft blush alpha",
        },
        "faceAnchorContract": {
            "daily": "outer/high cheekbone anchor is strongest; density falls inward toward nose and lower cheek",
            "lovely": "apple cheek center is strongest; density falls out radially",
            "sun1": "both cheeks are strongest; raised nose bridge/tip connector is capped low to avoid nostril overlap",
            "sun2": "W cheekbone ends are strongest; nose bridge connector stays low density",
            "under": "outer under-eye/high cheek contact is strongest; inner lower eyelid is restrained",
        },
        "anatomyBoundaryContract": (
            "Final cheek alpha/density is regenerated from ARFace topology eye/nose anchor vertices, "
            "face-width, outer cheek/high-cheek bands, and the user's drawing-derived shape ratios; "
            "drawn masks are not pasted as fixed screen stickers and Apple Vision pink components are not cheek boundaries."
        ),
        "runtimeAttachmentContract": (
            "Masks are sampled on the ARFace mesh UVs, so scale/yaw/pitch/near-far/smile motion follows "
            "mesh tracking instead of screen-sticker placement."
        ),
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
        f"- maskSource: `{summary['maskSource']}`\n"
        f"- drawingRole: `{summary['drawingRole']}`\n"
        f"- appleVisionAnchorRole: `{summary['appleVisionAnchorRole']}`\n"
        f"- coordinateSpace: `{summary['coordinateSpace']}`\n"
        f"- uvResolution: `{summary['uvResolution']}`\n"
        f"- capturePairId: `{summary['capturePairId']}`\n"
        f"- contactSheet: `{format_path(repo, output_dir / 'cheek_blush_mask_contact_sheet.png')}`\n"
        f"- runtimeTemplateAtlas: `{summary['runtimeTemplateAtlas']['path']}`\n"
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
