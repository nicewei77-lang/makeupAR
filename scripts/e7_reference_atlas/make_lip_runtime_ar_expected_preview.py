#!/usr/bin/env python3
"""Render buildless AR-runtime expected lip finish previews from current code.

This script mirrors the validation runtime path closely enough for visual
review: RN default lip recipe values, E3RegionMaskOverlay material conversion,
lip atlas triangle culling, ARFace screen projection, and SmoothRegionMask
shader math. It is not a Unity/iPhone acceptance run.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_FRAME = Path(
    "evidence/e7-reference-atlas/capture_pairs/"
    "pair_face_20260622T143334Z_03/frame.png"
)
DEFAULT_ARFACE = Path(
    "evidence/e7-reference-atlas/capture_pairs/"
    "pair_face_20260622T143334Z_03/arface_export.json"
)
DEFAULT_ATLAS = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "lip-drawn-style-atlas-v1.png"
)
DEFAULT_GRADIENT_ATLAS = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "lip-drawn-gradient-density-atlas-v1.png"
)
DEFAULT_SOURCE_MASK = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/lip_gold_mask_candidate.png"
)
DEFAULT_OUT = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/"
    "ar_runtime_expected_20260626"
)
DEFAULT_LIGHTING_REFERENCE_FRAME = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/"
    "lighting_references/bright_lighting_reference_20260626.png"
)

BRIGHT_REFERENCE_BASE_SIZE = (1226, 1420)
BRIGHT_REFERENCE_UPPER_LIP = (
    (498, 934),
    (524, 928),
    (554, 918),
    (582, 905),
    (604, 916),
    (620, 924),
    (638, 916),
    (660, 905),
    (690, 918),
    (718, 928),
    (734, 934),
    (720, 938),
    (684, 940),
    (648, 938),
    (616, 938),
    (586, 938),
    (546, 940),
    (524, 938),
)
BRIGHT_REFERENCE_LOWER_LIP = (
    (498, 934),
    (514, 944),
    (552, 962),
    (588, 982),
    (620, 993),
    (654, 986),
    (692, 964),
    (724, 944),
    (734, 934),
    (720, 938),
    (684, 942),
    (648, 944),
    (616, 946),
    (580, 944),
    (542, 942),
    (524, 938),
)


@dataclass(frozen=True)
class StyleConfig:
    texture_sample: str
    secondary_color: str
    feather: float
    coverage: float
    roughness: float
    specular: float
    specular_power: float
    gloss_boost: float
    gradient_amount: float
    lip_style_mode: float
    brightness_scale: float
    alpha_scale_min: float
    alpha_scale_max: float


STYLE_CONFIGS: dict[str, StyleConfig] = {
    "matte_lip": StyleConfig(
        texture_sample="matte_lip",
        secondary_color="#F29BAA",
        feather=0.23,
        coverage=0.94,
        roughness=1.0,
        specular=0.0,
        specular_power=6.0,
        gloss_boost=0.0,
        gradient_amount=0.02,
        lip_style_mode=0.0,
        brightness_scale=0.90,
        alpha_scale_min=0.72,
        alpha_scale_max=0.92,
    ),
    "gradient_lip": StyleConfig(
        texture_sample="gradient_lip",
        secondary_color="#EC8FA0",
        feather=0.38,
        coverage=0.94,
        roughness=1.0,
        specular=0.02,
        specular_power=12.0,
        gloss_boost=0.0,
        gradient_amount=1.0,
        lip_style_mode=3.0,
        brightness_scale=0.90,
        alpha_scale_min=0.72,
        alpha_scale_max=0.92,
    ),
    "gloss_lip": StyleConfig(
        texture_sample="gloss_lip",
        secondary_color="#F29BAA",
        feather=0.23,
        coverage=0.94,
        roughness=0.26,
        specular=0.78,
        specular_power=36.0,
        gloss_boost=0.68,
        gradient_amount=0.02,
        lip_style_mode=1.0,
        brightness_scale=0.90,
        alpha_scale_min=0.72,
        alpha_scale_max=0.92,
    ),
}

DEFAULT_PRIMARY_COLOR = "#D94B74"
DEFAULT_RECIPE_OPACITY = 0.90
DEFAULT_LIP_INTENSITY = 0.84
LIP_STYLE_ATLAS_THRESHOLD = 0.025
LIP_STYLE_ATLAS_FEATHER_CAP = 0.32
GRADIENT_LIP_FEATHER_CAP = 0.38
PRESERVE_DETAIL_SCALE = 0.92


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create AR-runtime expected lip finish previews from current code.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--arface", type=Path, default=DEFAULT_ARFACE)
    parser.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    parser.add_argument("--gradient-atlas", type=Path, default=DEFAULT_GRADIENT_ATLAS)
    parser.add_argument("--source-mask", type=Path, default=DEFAULT_SOURCE_MASK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--lighting-reference-frame", type=Path, default=DEFAULT_LIGHTING_REFERENCE_FRAME)
    parser.add_argument("--lighting-reference-mask", type=Path, default=None)
    parser.add_argument("--skip-lighting-reference-preview", action="store_true")
    parser.add_argument("--primary-color", default=DEFAULT_PRIMARY_COLOR)
    parser.add_argument("--opacity", type=float, default=DEFAULT_RECIPE_OPACITY)
    parser.add_argument("--intensity", type=float, default=DEFAULT_LIP_INTENSITY)
    parser.add_argument("--changed-threshold", type=float, default=0.010)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def hex_rgb(value: str) -> np.ndarray:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, got {value!r}")
    return np.asarray(
        [int(value[index : index + 2], 16) for index in (0, 2, 4)],
        dtype=np.float32,
    ) / 255.0


def saturate(values: np.ndarray | float) -> np.ndarray | float:
    return np.clip(values, 0.0, 1.0)


def lerp(a: np.ndarray | float, b: np.ndarray | float, t: np.ndarray | float) -> np.ndarray:
    return np.asarray(a) * (1.0 - np.asarray(t)) + np.asarray(b) * np.asarray(t)


def smoothstep(edge0: np.ndarray | float, edge1: np.ndarray | float, x: np.ndarray) -> np.ndarray:
    denom = np.maximum(np.asarray(edge1) - np.asarray(edge0), 1.0e-6)
    t = np.clip((x - np.asarray(edge0)) / denom, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def luma(values: np.ndarray) -> np.ndarray:
    return values[..., 0] * 0.2126 + values[..., 1] * 0.7152 + values[..., 2] * 0.0722


def redness(values: np.ndarray) -> np.ndarray:
    return values[..., 0] - (values[..., 1] + values[..., 2]) * 0.5


def component_count(active: np.ndarray) -> int:
    seen = np.zeros_like(active, dtype=bool)
    height, width = active.shape
    count = 0
    for row, col in np.argwhere(active):
        row = int(row)
        col = int(col)
        if seen[row, col]:
            continue
        count += 1
        stack = [(row, col)]
        seen[row, col] = True
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny = y + dy
                    nx = x + dx
                    if (
                        0 <= ny < height
                        and 0 <= nx < width
                        and active[ny, nx]
                        and not seen[ny, nx]
                    ):
                        seen[ny, nx] = True
                        stack.append((ny, nx))
    return count


def bbox(mask: np.ndarray) -> dict[str, int] | None:
    rows, cols = np.nonzero(mask)
    if len(cols) == 0:
        return None
    left = int(cols.min())
    top = int(rows.min())
    right = int(cols.max())
    bottom = int(rows.max())
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left + 1,
        "height": bottom - top + 1,
    }


def expand_crop(
    box: dict[str, int],
    size: tuple[int, int],
    pad_x: int = 220,
    pad_y: int = 170,
) -> tuple[int, int, int, int]:
    width, height = size
    return (
        max(0, box["left"] - pad_x),
        max(0, box["top"] - pad_y),
        min(width, box["right"] + pad_x + 1),
        min(height, box["bottom"] + pad_y + 1),
    )


def to_image(values: np.ndarray) -> Image.Image:
    return Image.fromarray(
        np.rint(np.clip(values, 0.0, 1.0) * 255.0).astype(np.uint8),
        mode="RGB",
    )


def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0


def read_arface(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sample_nearest_r(atlas: np.ndarray, uv: np.ndarray) -> int:
    height, width = atlas.shape[:2]
    u = float(np.clip(uv[0], 0.0, 1.0))
    v = float(np.clip(uv[1], 0.0, 1.0))
    x = int(np.clip(round(u * (width - 1)), 0, width - 1))
    unity_y = int(np.clip(round(v * (height - 1)), 0, height - 1))
    row = height - 1 - unity_y
    return int(round(float(atlas[row, x, 0]) * 255.0))


def triangle_intersects_mask(atlas: np.ndarray, threshold_byte: int, uvs: np.ndarray) -> bool:
    a, b, c = uvs
    sample_points = (
        a,
        b,
        c,
        (a + b + c) / 3.0,
        (a + b) * 0.5,
        (b + c) * 0.5,
        (c + a) * 0.5,
    )
    return any(sample_nearest_r(atlas, point) > threshold_byte for point in sample_points)


def rasterize_runtime_uv_map(
    arface: dict[str, Any],
    atlas: np.ndarray,
    output_shape: tuple[int, int],
    threshold: float,
) -> tuple[np.ndarray, np.ndarray, list[list[tuple[float, float]]], dict[str, Any]]:
    screen_vertices = np.asarray(arface.get("screenVertices", []), dtype=np.float32)
    uvs = np.asarray(arface.get("uvs", []), dtype=np.float32)
    indices = np.asarray(arface.get("indices", []), dtype=np.int32)
    if screen_vertices.ndim != 2 or screen_vertices.shape[1] < 2:
        raise ValueError("ARFace export is missing screenVertices.")
    if uvs.ndim != 2 or uvs.shape[1] < 2:
        raise ValueError("ARFace export is missing uvs.")
    if len(screen_vertices) != len(uvs):
        raise ValueError("ARFace screenVertices/uvs lengths differ.")
    if indices.ndim != 1 or len(indices) < 3:
        raise ValueError("ARFace export is missing indices.")

    height, width = output_shape
    threshold_byte = int(np.clip(round(threshold * 255.0), 0, 255))
    covered = np.zeros((height, width), dtype=bool)
    uv_map = np.zeros((height, width, 2), dtype=np.float32)
    triangle_map = np.full((height, width), -1, dtype=np.int32)
    accepted_polygons: list[list[tuple[float, float]]] = []
    source_triangles = 0
    accepted_triangles = 0
    culled_triangles = 0
    invalid_triangles = 0
    rasterized_triangles = 0
    epsilon = 1.0e-4

    for triangle_index, triangle in enumerate(indices.reshape((-1, 3))):
        if int(triangle.min()) < 0 or int(triangle.max()) >= len(uvs):
            invalid_triangles += 1
            continue

        source_triangles += 1
        triangle_uvs = uvs[triangle, :2]
        if not triangle_intersects_mask(atlas, threshold_byte, triangle_uvs):
            culled_triangles += 1
            continue

        accepted_triangles += 1
        screen_points = screen_vertices[triangle, :2]
        accepted_polygons.append(
            [(float(point[0]), float(point[1])) for point in screen_points]
        )
        left = max(int(np.floor(float(screen_points[:, 0].min()))), 0)
        right = min(int(np.ceil(float(screen_points[:, 0].max()))), width - 1)
        top = max(int(np.floor(float(screen_points[:, 1].min()))), 0)
        bottom = min(int(np.ceil(float(screen_points[:, 1].max()))), height - 1)
        if right < left or bottom < top:
            continue

        x1, y1 = screen_points[0]
        x2, y2 = screen_points[1]
        x3, y3 = screen_points[2]
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(float(denominator)) < 1.0e-5:
            continue

        grid_x = np.arange(left, right + 1, dtype=np.float32) + 0.5
        grid_y = np.arange(top, bottom + 1, dtype=np.float32) + 0.5
        pixel_x, pixel_y = np.meshgrid(grid_x, grid_y)
        weight_a = (
            ((y2 - y3) * (pixel_x - x3) + (x3 - x2) * (pixel_y - y3))
            / denominator
        )
        weight_b = (
            ((y3 - y1) * (pixel_x - x3) + (x1 - x3) * (pixel_y - y3))
            / denominator
        )
        weight_c = 1.0 - weight_a - weight_b
        inside = (
            (weight_a >= -epsilon)
            & (weight_b >= -epsilon)
            & (weight_c >= -epsilon)
            & (weight_a <= 1.0 + epsilon)
            & (weight_b <= 1.0 + epsilon)
            & (weight_c <= 1.0 + epsilon)
        )
        if not inside.any():
            continue

        projected_u = (
            weight_a * triangle_uvs[0, 0]
            + weight_b * triangle_uvs[1, 0]
            + weight_c * triangle_uvs[2, 0]
        )
        projected_v = (
            weight_a * triangle_uvs[0, 1]
            + weight_b * triangle_uvs[1, 1]
            + weight_c * triangle_uvs[2, 1]
        )
        valid_uv = (
            (projected_u >= 0.0)
            & (projected_u <= 1.0)
            & (projected_v >= 0.0)
            & (projected_v <= 1.0)
        )
        active = inside & valid_uv
        if not active.any():
            continue

        patch_covered = covered[top : bottom + 1, left : right + 1]
        patch_uv = uv_map[top : bottom + 1, left : right + 1]
        patch_triangles = triangle_map[top : bottom + 1, left : right + 1]
        patch_covered[active] = True
        patch_uv[active, 0] = projected_u[active]
        patch_uv[active, 1] = projected_v[active]
        patch_triangles[active] = triangle_index
        rasterized_triangles += 1

    stats = {
        "threshold": threshold,
        "thresholdByte": threshold_byte,
        "sourceTriangles": source_triangles,
        "acceptedTriangles": accepted_triangles,
        "culledTriangles": culled_triangles,
        "cullRatio": culled_triangles / float(max(source_triangles, 1)),
        "acceptedRatio": accepted_triangles / float(max(source_triangles, 1)),
        "invalidTriangles": invalid_triangles,
        "rasterizedTriangles": rasterized_triangles,
        "coveredPixels": int(covered.sum()),
        "coveredBbox": bbox(covered),
        "meshCullingMode": "lip_atlas_threshold_sample",
    }
    return covered, uv_map, accepted_polygons, stats


def sample_texture(atlas: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    height, width = atlas.shape[:2]
    x = np.clip(u, 0.0, 1.0) * (width - 1)
    y = (1.0 - np.clip(v, 0.0, 1.0)) * (height - 1)
    x0 = np.floor(x).astype(np.int32)
    y0 = np.floor(y).astype(np.int32)
    x1 = np.clip(x0 + 1, 0, width - 1)
    y1 = np.clip(y0 + 1, 0, height - 1)
    tx = (x - x0)[..., None]
    ty = (y - y0)[..., None]
    top = atlas[y0, x0] * (1.0 - tx) + atlas[y0, x1] * tx
    bottom = atlas[y1, x0] * (1.0 - tx) + atlas[y1, x1] * tx
    return top * (1.0 - ty) + bottom * ty


def feather_texel_radius(feather: float) -> float:
    return 1.25 + (5.5 - 1.25) * float(np.clip(feather * 2.35, 0.0, 1.0))


def sample_mask_soft(atlas: np.ndarray, uv: np.ndarray, feather: float) -> np.ndarray:
    height, width = atlas.shape[:2]
    radius = feather_texel_radius(feather)
    near_x = radius / float(width)
    near_y = radius / float(height)
    far_x = near_x * 1.85
    far_y = near_y * 1.85
    u = uv[:, 0]
    v = uv[:, 1]
    center = sample_texture(atlas, u, v) * 0.24
    near_axis = (
        sample_texture(atlas, u + near_x, v)
        + sample_texture(atlas, u - near_x, v)
        + sample_texture(atlas, u, v + near_y)
        + sample_texture(atlas, u, v - near_y)
    ) * 0.085
    near_diagonal = (
        sample_texture(atlas, u + near_x, v + near_y)
        + sample_texture(atlas, u - near_x, v - near_y)
        + sample_texture(atlas, u + near_x, v - near_y)
        + sample_texture(atlas, u - near_x, v + near_y)
    ) * 0.045
    far_axis = (
        sample_texture(atlas, u + far_x, v)
        + sample_texture(atlas, u - far_x, v)
        + sample_texture(atlas, u, v + far_y)
        + sample_texture(atlas, u, v - far_y)
    ) * 0.06
    return center + near_axis + near_diagonal + far_axis


def sample_gradient_density_blur(atlas: np.ndarray, uv: np.ndarray, feather: float) -> np.ndarray:
    height, width = atlas.shape[:2]
    radius = feather_texel_radius(feather) * 2.25
    near_x = radius / float(width)
    near_y = radius / float(height)
    far_x = near_x * 1.75
    far_y = near_y * 1.75
    u = uv[:, 0]
    v = uv[:, 1]
    center = sample_texture(atlas, u, v)[:, 2] * 0.16
    near_axis = (
        sample_texture(atlas, u + near_x, v)[:, 2]
        + sample_texture(atlas, u - near_x, v)[:, 2]
        + sample_texture(atlas, u, v + near_y)[:, 2]
        + sample_texture(atlas, u, v - near_y)[:, 2]
    ) * 0.075
    near_diagonal = (
        sample_texture(atlas, u + near_x, v + near_y)[:, 2]
        + sample_texture(atlas, u - near_x, v - near_y)[:, 2]
        + sample_texture(atlas, u + near_x, v - near_y)[:, 2]
        + sample_texture(atlas, u - near_x, v + near_y)[:, 2]
    ) * 0.045
    far_axis = (
        sample_texture(atlas, u + far_x, v)[:, 2]
        + sample_texture(atlas, u - far_x, v)[:, 2]
        + sample_texture(atlas, u, v + far_y)[:, 2]
        + sample_texture(atlas, u, v - far_y)[:, 2]
    ) * 0.09
    return np.clip(center + near_axis + near_diagonal + far_axis, 0.0, 1.0)


def soft_mask_alpha(values: np.ndarray, threshold: float, feather: float) -> np.ndarray:
    soft = max(feather, 1.0e-5)
    return smoothstep(
        float(np.clip(threshold - soft * 0.46, 0.0, 1.0)),
        float(np.clip(threshold + soft, 0.0, 1.0)),
        values,
    )


def core_mask_alpha(values: np.ndarray, threshold: float, feather: float) -> np.ndarray:
    soft = max(feather, 1.0e-5)
    return smoothstep(
        float(np.clip(threshold + soft * 0.18, 0.0, 1.0)),
        float(np.clip(threshold + soft * 0.88, 0.0, 1.0)),
        values,
    )


def lip_center_density(uv: np.ndarray, mask_alpha: np.ndarray) -> np.ndarray:
    lip_uv_x = uv[:, 0] - 0.5
    lip_uv_y = uv[:, 1] - 0.5
    horizontal = 1.0 - smoothstep(0.05, 0.42, np.abs(lip_uv_x))
    mouth_proximity = 1.0 - smoothstep(0.02, 0.18, np.abs(lip_uv_y))
    lower_center = 1.0 - smoothstep(
        0.025,
        0.30,
        np.sqrt((lip_uv_x - 0.0) ** 2 + (lip_uv_y + 0.055) ** 2),
    )
    return np.clip(mask_alpha * np.maximum(horizontal * mouth_proximity, lower_center * 0.68), 0.0, 1.0)


def material_params(
    config: StyleConfig,
    primary_color: np.ndarray,
    opacity: float,
    intensity: float,
) -> dict[str, Any]:
    sample_alpha_scale = config.alpha_scale_min + (
        config.alpha_scale_max - config.alpha_scale_min
    ) * intensity
    return {
        "regionColor": np.clip(primary_color * config.brightness_scale, 0.0, 1.0),
        "secondaryColor": hex_rgb(config.secondary_color),
        "opacity": float(np.clip(opacity * sample_alpha_scale, 0.0, 1.0)),
        "feather": float(
            np.clip(
                min(
                    GRADIENT_LIP_FEATHER_CAP
                    if config.texture_sample == "gradient_lip"
                    else LIP_STYLE_ATLAS_FEATHER_CAP,
                    max(
                        0.28 if config.texture_sample == "gradient_lip" else 0.22,
                        config.feather,
                    ),
                ),
                0.0,
                1.0,
            )
        ),
        "coverage": float(np.clip(config.coverage, 0.0, 1.0)),
        "roughness": float(np.clip(config.roughness, 0.0, 1.0)),
        "specular": float(np.clip(config.specular, 0.0, 1.0)),
        "specularPower": config.specular_power,
        "glossBoost": float(np.clip(config.gloss_boost, 0.0, 1.0)),
        "glossColor": np.asarray([1.0, 0.78, 0.84], dtype=np.float32),
        "glossSharpness": float(
            np.clip(
                0.60 + (0.86 - 0.60) * np.clip(config.gloss_boost, 0.0, 1.0),
                0.0,
                1.0,
            )
        ),
        "glossHaloIntensity": float(
            np.clip(
                0.045 + (0.10 - 0.045) * np.clip(config.gloss_boost, 0.0, 1.0),
                0.0,
                1.0,
            )
        ),
        "gradientAmount": float(np.clip(config.gradient_amount, 0.0, 1.0)),
        "preserveScale": PRESERVE_DETAIL_SCALE,
        "lipStyleMode": config.lip_style_mode,
        "threshold": LIP_STYLE_ATLAS_THRESHOLD,
        "blendMode": "multiply",
        "pigmentMultiply": 1.0,
    }


def shader_first_pass(
    atlas: np.ndarray,
    uv: np.ndarray,
    config: StyleConfig,
    params: dict[str, Any],
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    threshold = params["threshold"]
    feather = params["feather"]
    coverage = max(params["coverage"], 0.001)
    mask = sample_texture(atlas, uv[:, 0], uv[:, 1])
    soft_mask = sample_mask_soft(atlas, uv, feather)
    full_soft = soft_mask_alpha(soft_mask[:, 0], threshold, feather)
    full_core = core_mask_alpha(mask[:, 0], threshold, feather)
    overline_soft = soft_mask_alpha(soft_mask[:, 1], threshold, feather)
    gradient_mask = soft_mask_alpha(np.maximum(soft_mask[:, 2], mask[:, 2]), threshold, feather)
    edge_band = np.clip(full_soft - full_core, 0.0, 1.0)
    center_density = lip_center_density(uv, full_soft)
    legacy_inner_density = np.clip(
        np.maximum(gradient_mask * full_core, center_density * full_core),
        0.0,
        1.0,
    )
    single_gradient_density = np.zeros_like(full_soft)
    base_stain = full_soft * coverage * 0.54
    inner_layer = legacy_inner_density * coverage * 0.32
    edge_layer = edge_band * coverage * 0.06
    mask_strength = base_stain + inner_layer + edge_layer
    pigment_color = params["regionColor"].copy()
    alpha_color = pigment_color.copy()
    mode = config.lip_style_mode
    matte_reference_mask_strength = np.clip(
        base_stain * 1.02 + inner_layer * 0.48 + edge_layer * 0.20,
        0.0,
        1.0,
    )
    matte_reference_pigment_color = np.clip(
        lerp(pigment_color, pigment_color * 0.82, 0.28),
        0.0,
        1.0,
    )

    if mode < 0.5:
        mask_strength = matte_reference_mask_strength
        pigment_color = matte_reference_pigment_color
        alpha_color = pigment_color
    elif mode < 1.5:
        mask_strength = matte_reference_mask_strength
        pigment_color = matte_reference_pigment_color
        alpha_color = pigment_color
    elif mode < 2.5:
        mask_strength = np.clip(
            base_stain * 0.98
            + inner_layer * 0.34
            + edge_layer * 0.30
            + overline_soft * coverage * 0.08,
            0.0,
            1.0,
        )
        pigment_color = np.clip(lerp(pigment_color, pigment_color * 0.88, 0.12), 0.0, 1.0)
        alpha_color = pigment_color
    elif mode < 3.5:
        gradient_mix = params["gradientAmount"]
        gradient_density_raw = np.maximum(mask[:, 2], soft_mask[:, 2] * 0.82)
        gradient_density_blurred = np.clip(
            sample_gradient_density_blur(atlas, uv, feather) * 1.45,
            0.0,
            1.0,
        )
        gradient_density_seed = np.clip(
            lerp(
                gradient_density_raw,
                gradient_density_blurred,
                0.42 + (0.56 - 0.42) * gradient_mix,
            ),
            0.0,
            1.0,
        )
        gradient_density_ramp = np.power(
            gradient_density_seed,
            1.02 + (0.78 - 1.02) * gradient_mix,
        )
        single_gradient_density = np.clip(
            full_soft * gradient_density_ramp,
            0.0,
            1.0,
        )
        gradient_density_curve = np.power(
            single_gradient_density,
            1.46 + (1.24 - 1.46) * gradient_mix,
        )
        gradient_strength_scale = 0.72 + (1.08 - 0.72) * gradient_density_curve
        mask_strength = np.clip(
            matte_reference_mask_strength * gradient_strength_scale,
            0.0,
            1.0,
        )
        pigment_color = matte_reference_pigment_color
        alpha_color = pigment_color
    else:
        line_alpha = np.clip(overline_soft - full_core * 0.42, 0.0, 1.0)
        mask_strength = np.maximum(base_stain * 0.54 + edge_layer * 0.2, line_alpha * coverage * 0.55)
        pigment_color = np.clip(
            params["secondaryColor"][None, :] * (1.0 - full_core[:, None])
            + params["regionColor"][None, :] * full_core[:, None],
            0.0,
            1.0,
        )
        alpha_color = pigment_color

    style_cap_boost = (
        0.18
        if mode < 0.5
        else 0.10
        if 0.5 <= mode < 1.5
        else 0.14
        if 2.5 <= mode < 3.5
        else 0.0
    )
    max_pigment_strength = float(np.clip((0.42 + (0.66 - 0.42) * coverage) + style_cap_boost, 0.0, 1.0))
    pigment_strength = np.minimum(
        np.clip(mask_strength * params["opacity"] * params["preserveScale"], 0.0, 1.0),
        max_pigment_strength,
    )
    pigment_color_values = (
        pigment_color
        if pigment_color.ndim == 2
        else np.repeat(pigment_color[None, :], len(uv), axis=0)
    )
    pigment_filter = np.clip(
        (1.0 - pigment_strength[:, None]) + pigment_color_values * pigment_strength[:, None],
        0.0,
        1.0,
    )
    layers = {
        "maskR": mask[:, 0],
        "maskA": mask[:, 3],
        "softR": soft_mask[:, 0],
        "softA": soft_mask[:, 3],
        "fullSoft": full_soft,
        "fullCore": full_core,
        "edgeBand": edge_band,
        "centerDensity": center_density,
        "legacyInnerDensity": legacy_inner_density,
        "continuousGradientDensity": single_gradient_density,
        "singleGradientDensity": single_gradient_density,
        "matteReferenceMaskStrength": matte_reference_mask_strength,
        "maskStrength": mask_strength,
        "pigmentStrength": pigment_strength,
        "pigmentColorR": pigment_color_values[:, 0],
        "pigmentColorG": pigment_color_values[:, 1],
        "pigmentColorB": pigment_color_values[:, 2],
        "alphaColor": alpha_color,
    }
    return pigment_filter, layers


def shader_gloss_additive(
    atlas: np.ndarray,
    uv: np.ndarray,
    config: StyleConfig,
    params: dict[str, Any],
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    if config.lip_style_mode < 0.5 or config.lip_style_mode >= 1.5:
        zeros = np.zeros((len(uv), 3), dtype=np.float32)
        return zeros, {
            "glossSharpMask": np.zeros((len(uv),), dtype=np.float32),
            "glossHaloMask": np.zeros((len(uv),), dtype=np.float32),
            "highlight": np.zeros((len(uv),), dtype=np.float32),
        }

    threshold = params["threshold"]
    feather = params["feather"]
    mask = sample_texture(atlas, uv[:, 0], uv[:, 1])
    soft_mask = sample_mask_soft(atlas, uv, feather)
    full_soft = soft_mask_alpha(soft_mask[:, 0], threshold, feather)
    full_core = core_mask_alpha(mask[:, 0], threshold, feather)
    coverage = max(params["coverage"], 0.001)
    gloss_sharp_mask = (
        soft_mask_alpha(
            np.clip(mask[:, 3], 0.0, 1.0),
            max(threshold * 0.96, 0.022),
            max((0.044 + (0.032 - 0.044) * params["glossSharpness"]), 0.032),
        )
        * full_soft
        * full_core
    )
    gloss_halo_mask = (
        soft_mask_alpha(
            np.clip(np.maximum(soft_mask[:, 3], mask[:, 3] * 0.52), 0.0, 1.0),
            max(threshold * 0.70, 0.018),
            max(feather * 0.26, 0.050),
        )
        * full_soft
        * full_core
    )
    gloss_halo = np.clip(gloss_halo_mask - gloss_sharp_mask * 0.56, 0.0, 1.0)
    gloss_energy = (
        coverage
        * coverage
        * params["specular"]
        * params["glossBoost"]
        * params["opacity"]
    )
    sharp_highlight = gloss_sharp_mask * gloss_energy * 0.96
    halo_highlight = gloss_halo * gloss_energy * params["glossHaloIntensity"] * 0.22
    gloss_screen_lift = np.clip(1.0 - params["regionColor"] * 0.56, 0.0, 1.0)
    sharp_color = np.clip(lerp(params["regionColor"], params["glossColor"], 0.34), 0.0, 1.0)
    halo_color = np.clip(lerp(params["regionColor"], params["glossColor"], 0.03), 0.0, 1.0)
    additive = (
        sharp_color[None, :] * gloss_screen_lift[None, :] * sharp_highlight[:, None]
        + halo_color[None, :] * gloss_screen_lift[None, :] * halo_highlight[:, None]
    )
    return additive, {
        "glossSharpMask": gloss_sharp_mask,
        "glossHaloMask": gloss_halo_mask,
        "highlight": np.maximum(sharp_highlight, halo_highlight),
    }


def render_style(
    frame: np.ndarray,
    atlas: np.ndarray,
    covered: np.ndarray,
    uv_map: np.ndarray,
    config: StyleConfig,
    params: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    output = frame.copy()
    base_output = frame.copy()
    uv = uv_map[covered]
    base_filter, first_layers = shader_first_pass(atlas, uv, config, params)
    base_pixels = np.clip(frame[covered] * base_filter, 0.0, 1.0)
    base_output[covered] = base_pixels
    output[covered] = base_pixels
    additive, gloss_layers = shader_gloss_additive(atlas, uv, config, params)
    output[covered] = np.clip(output[covered] + additive, 0.0, 1.0)

    full_layers: dict[str, np.ndarray] = {}
    covered_count = int(covered.sum())
    for name, values in first_layers.items():
        if values.ndim != 1 or values.shape[0] != covered_count:
            continue
        layer = np.zeros(covered.shape, dtype=np.float32)
        layer[covered] = values.astype(np.float32)
        full_layers[name] = layer
    for name, values in gloss_layers.items():
        layer = np.zeros(covered.shape, dtype=np.float32)
        layer[covered] = values.astype(np.float32)
        full_layers[name] = layer
    additive_luma = np.zeros(covered.shape, dtype=np.float32)
    additive_luma[covered] = luma(additive)
    full_layers["additiveLuma"] = additive_luma
    return output, base_output, full_layers


def changed_mask(original: np.ndarray, rendered: np.ndarray, threshold: float) -> np.ndarray:
    return np.max(np.abs(rendered - original), axis=2) > threshold


def dilate(mask: np.ndarray, size: int) -> np.ndarray:
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(size)), dtype=np.uint8) > 0


def mask_stats(mask: np.ndarray) -> dict[str, Any]:
    return {
        "pixelCount": int(mask.sum()),
        "coverage": float(mask.mean()),
        "bbox": bbox(mask),
    }


def style_metrics(
    original: np.ndarray,
    rendered: np.ndarray,
    base_rendered: np.ndarray,
    layers: dict[str, np.ndarray],
    source_mask: np.ndarray | None,
    threshold: float,
) -> dict[str, Any]:
    changed = changed_mask(original, rendered, threshold)
    changed_box = bbox(changed)
    active = layers["fullSoft"] > 0.12
    source_luma = luma(original)[active]
    rendered_luma = luma(rendered)[active]
    source_std = float(source_luma.std()) if len(source_luma) > 1 else 0.0
    rendered_std = float(rendered_luma.std()) if len(rendered_luma) > 1 else 0.0
    correlation = (
        0.0
        if source_std <= 1.0e-8 or rendered_std <= 1.0e-8
        else float(np.corrcoef(source_luma, rendered_luma)[0, 1])
    )
    metrics: dict[str, Any] = {
        "changed": mask_stats(changed),
        "fullSoft": mask_stats(active),
        "pigmentStrengthMean": float(layers["pigmentStrength"][active].mean()) if int(active.sum()) else 0.0,
        "pigmentStrengthP95": float(np.percentile(layers["pigmentStrength"][active], 95)) if int(active.sum()) else 0.0,
        "lumaStdRatio": rendered_std / max(source_std, 1.0e-8),
        "lumaCorrelation": correlation,
        "changedBbox": changed_box,
    }
    if source_mask is not None and int(changed.sum()) > 0:
        source_dilated = dilate(source_mask, 9)
        outside = changed & ~source_dilated
        metrics["outsideSourceDilatedPixels"] = int(outside.sum())
        metrics["outsideSourceDilatedRatio"] = float(outside.sum() / max(int(changed.sum()), 1))
    wet = layers["highlight"] > 0.012
    if int(wet.sum()) > 0:
        wet_box = bbox(wet)
        lip_box = bbox(active)
        metrics["wetHighlight"] = {
            **mask_stats(wet),
            "componentCount": component_count(wet),
            "meanAdditiveLuma": float(layers["additiveLuma"][wet].mean()),
            "maxAdditiveLuma": float(layers["additiveLuma"][wet].max()),
            "heightToLipHeight": float(
                (wet_box or {"height": 0})["height"] / max((lip_box or {"height": 1})["height"], 1)
            ),
            "widthToLipWidth": float(
                (wet_box or {"width": 0})["width"] / max((lip_box or {"width": 1})["width"], 1)
            ),
        }
    else:
        metrics["wetHighlight"] = {
            "pixelCount": 0,
            "coverage": 0.0,
            "bbox": None,
            "componentCount": 0,
            "meanAdditiveLuma": 0.0,
            "maxAdditiveLuma": 0.0,
            "heightToLipHeight": 0.0,
            "widthToLipWidth": 0.0,
        }
    metrics["baseRendered"] = {
        "meanRedness": float(redness(base_rendered)[active].mean()) if int(active.sum()) else 0.0,
        "meanLuma": float(luma(base_rendered)[active].mean()) if int(active.sum()) else 0.0,
    }
    return metrics


def gradient_metrics(layers: dict[str, np.ndarray]) -> dict[str, Any]:
    active = layers["fullSoft"] > 0.12
    density = layers["continuousGradientDensity"]
    pigment = layers["pigmentStrength"]
    pigment_color = None
    if {"pigmentColorR", "pigmentColorG", "pigmentColorB"}.issubset(layers):
        pigment_color = np.stack(
            [
                layers["pigmentColorR"],
                layers["pigmentColorG"],
                layers["pigmentColorB"],
            ],
            axis=-1,
        )
    transition = active & (density > 0.18) & (density < 0.78)
    inner = active & (density > 0.72)
    outer = active & (density >= 0.30) & (density < 0.58)
    edge = active & (density < 0.18)
    box = bbox(active)
    adjacent_p95 = 0.0
    center_jump = 0.0
    if box is not None:
        crop_density = density[box["top"] : box["bottom"] + 1, box["left"] : box["right"] + 1]
        crop_active = active[box["top"] : box["bottom"] + 1, box["left"] : box["right"] + 1]
        dy = np.abs(np.diff(crop_density, axis=0))
        dx = np.abs(np.diff(crop_density, axis=1))
        valid_y = crop_active[1:, :] & crop_active[:-1, :]
        valid_x = crop_active[:, 1:] & crop_active[:, :-1]
        adjacent = np.concatenate([dy[valid_y], dx[valid_x]])
        adjacent_p95 = float(np.percentile(adjacent, 95)) if len(adjacent) else 0.0
        center_y = int(np.clip(round(box["top"] + box["height"] * 0.58), 0, density.shape[0] - 1))
        center_line = density[center_y, box["left"] : box["right"] + 1]
        center_active = active[center_y, box["left"] : box["right"] + 1]
        center_delta = np.abs(np.diff(center_line))
        center_valid = center_active[1:] & center_active[:-1]
        center_jump = float(center_delta[center_valid].max()) if int(center_valid.sum()) else 0.0
    transition_cols = np.unique(np.nonzero(transition)[1])
    result = {
        "transitionWidthToLipWidth": float(
            len(transition_cols) / max((box or {"width": 1})["width"], 1)
        ),
        "innerOuterPigmentRatio": float(
            (pigment[inner].mean() if int(inner.sum()) else 0.0)
            / max(float(pigment[outer].mean()) if int(outer.sum()) else 0.0, 1.0e-6)
        ),
        "edgeInnerPigmentRatio": float(
            (pigment[edge].mean() if int(edge.sum()) else 0.0)
            / max(float(pigment[inner].mean()) if int(inner.sum()) else 0.0, 1.0e-6)
        ),
        "adjacentDensityDeltaP95": adjacent_p95,
        "centerLineMaxJump": center_jump,
    }
    if pigment_color is not None and int(active.sum()) > 0:
        active_colors = pigment_color[active]
        result["pigmentColorRangeMax"] = float(
            (active_colors.max(axis=0) - active_colors.min(axis=0)).max()
        )
        result["pigmentColorStdMax"] = float(active_colors.std(axis=0).max())
    return result


def overlay_diagnostic(
    frame: Image.Image,
    source_mask: np.ndarray | None,
    covered: np.ndarray,
    polygons: list[list[tuple[float, float]]],
) -> Image.Image:
    base = frame.convert("RGBA")
    if source_mask is not None:
        source_alpha = Image.fromarray((source_mask.astype(np.uint8) * 70), mode="L")
        source_tint = Image.new("RGBA", frame.size, (42, 190, 120, 0))
        source_tint.putalpha(source_alpha)
        base = Image.alpha_composite(base, source_tint)
    covered_alpha = Image.fromarray((covered.astype(np.uint8) * 60), mode="L")
    covered_tint = Image.new("RGBA", frame.size, (217, 75, 116, 0))
    covered_tint.putalpha(covered_alpha)
    base = Image.alpha_composite(base, covered_tint)
    draw = ImageDraw.Draw(base)
    for polygon in polygons:
        if len(polygon) == 3:
            draw.line([polygon[0], polygon[1], polygon[2], polygon[0]], fill=(255, 255, 255, 95), width=1)
    draw.rectangle((20, 20, 650, 90), fill=(0, 0, 0, 160))
    draw.text((38, 38), "green=source lip mask / rose=accepted ARFace triangles", fill=(255, 255, 255, 255))
    return base.convert("RGB")


def layer_diagnostic_image(layers: dict[str, np.ndarray]) -> Image.Image:
    red = np.rint(np.clip(layers["pigmentStrength"], 0.0, 1.0) * 255).astype(np.uint8)
    green = np.rint(np.clip(layers["fullSoft"], 0.0, 1.0) * 255).astype(np.uint8)
    blue = np.rint(np.clip(layers.get("highlight", np.zeros_like(layers["fullSoft"])), 0.0, 1.0) * 255).astype(np.uint8)
    return Image.merge(
        "RGB",
        (
            Image.fromarray(red, mode="L"),
            Image.fromarray(green, mode="L"),
            Image.fromarray(blue, mode="L"),
        ),
    )


def changed_overlay(frame: Image.Image, changed: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    alpha = Image.fromarray((changed.astype(np.uint8) * 132), mode="L")
    tint = Image.new("RGBA", frame.size, (*color, 0))
    tint.putalpha(alpha)
    return Image.alpha_composite(frame.convert("RGBA"), tint).convert("RGB")


def label_panel(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    output = image.convert("RGBA")
    draw = ImageDraw.Draw(output)
    height = 78 if subtitle else 54
    draw.rectangle((12, 12, min(output.width - 12, 780), 12 + height), fill=(0, 0, 0, 172))
    draw.text((28, 28), title, fill=(255, 255, 255, 255))
    if subtitle:
        draw.text((28, 54), subtitle, fill=(220, 230, 238, 255))
    return output.convert("RGB")


def make_sheet(panels: list[tuple[str, Image.Image]], crop: tuple[int, int, int, int]) -> Image.Image:
    tile_width = 390
    label_height = 34
    cropped: list[tuple[str, Image.Image]] = []
    for title, image in panels:
        view = image.crop(crop)
        view.thumbnail((tile_width, 720), Image.Resampling.LANCZOS)
        cropped.append((title, view.convert("RGB")))
    width = tile_width * len(cropped)
    height = label_height + max(image.height for _, image in cropped)
    sheet = Image.new("RGB", (width, height), (18, 18, 21))
    draw = ImageDraw.Draw(sheet)
    for index, (title, image) in enumerate(cropped):
        x = index * tile_width
        draw.rectangle((x, 0, x + tile_width, label_height), fill=(34, 34, 40))
        draw.text((x + 12, 10), title, fill=(255, 255, 255))
        sheet.paste(image, (x + (tile_width - image.width) // 2, label_height))
    return sheet


def make_mixed_crop_sheet(
    panels: list[tuple[str, Image.Image, tuple[int, int, int, int]]],
    tile_width: int = 520,
    tile_height: int = 360,
) -> Image.Image:
    label_height = 44
    cropped: list[tuple[str, Image.Image]] = []
    for title, image, crop in panels:
        view = image.crop(crop)
        view.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
        cropped.append((title, view.convert("RGB")))
    width = tile_width * len(cropped)
    height = label_height + max(image.height for _, image in cropped)
    sheet = Image.new("RGB", (width, height), (18, 18, 21))
    draw = ImageDraw.Draw(sheet)
    for index, (title, image) in enumerate(cropped):
        x = index * tile_width
        draw.rectangle((x, 0, x + tile_width, label_height), fill=(34, 34, 40))
        draw.text((x + 14, 15), title, fill=(255, 255, 255))
        sheet.paste(image, (x + (tile_width - image.width) // 2, label_height))
    return sheet


def scaled_points(
    points: tuple[tuple[int, int], ...],
    size: tuple[int, int],
) -> list[tuple[int, int]]:
    width, height = size
    base_width, base_height = BRIGHT_REFERENCE_BASE_SIZE
    scale_x = width / base_width
    scale_y = height / base_height
    return [
        (int(round(x * scale_x)), int(round(y * scale_y)))
        for x, y in points
    ]


def default_bright_reference_alpha(size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    width, height = size
    mask_image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask_image)
    draw.polygon(scaled_points(BRIGHT_REFERENCE_UPPER_LIP, size), fill=255)
    draw.polygon(scaled_points(BRIGHT_REFERENCE_LOWER_LIP, size), fill=255)
    scale = max(width / BRIGHT_REFERENCE_BASE_SIZE[0], height / BRIGHT_REFERENCE_BASE_SIZE[1])
    hard = mask_image.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    soft = hard.filter(ImageFilter.GaussianBlur(radius=max(1.6, 3.3 * scale)))
    return (
        np.asarray(soft, dtype=np.float32) / 255.0,
        np.asarray(hard, dtype=np.float32) / 255.0,
    )


def load_lighting_reference_alpha(
    repo: Path,
    frame_path: Path,
    size: tuple[int, int],
    mask_path: Path | None,
) -> tuple[np.ndarray, np.ndarray, str] | None:
    if mask_path is not None:
        resolved_mask = resolve(repo, mask_path)
        if not resolved_mask.exists():
            return None
        mask = np.asarray(Image.open(resolved_mask).convert("RGBA"), dtype=np.float32) / 255.0
        if mask.shape[:2] != (size[1], size[0]):
            mask_image = Image.fromarray(np.rint(np.max(mask[:, :, :3], axis=2) * 255).astype(np.uint8), mode="L")
            mask_image = mask_image.resize(size, Image.Resampling.BILINEAR)
            alpha = np.asarray(mask_image, dtype=np.float32) / 255.0
        else:
            alpha = np.maximum(mask[:, :, 3], np.max(mask[:, :, :3], axis=2))
        hard = (alpha > 0.2).astype(np.float32)
        return np.clip(alpha, 0.0, 1.0), hard, "explicit_lighting_reference_mask"

    default_frame = resolve(repo, DEFAULT_LIGHTING_REFERENCE_FRAME)
    if frame_path.resolve() != default_frame.resolve():
        return None
    alpha, hard = default_bright_reference_alpha(size)
    return alpha, hard, "manual_photo_aligned_outline_for_default_bright_reference"


def render_lighting_reference_preview(
    frame_image: Image.Image,
    primary: np.ndarray,
    opacity: float,
    intensity: float,
    method: str,
    alpha: np.ndarray,
) -> tuple[dict[str, Image.Image], dict[str, Any], tuple[int, int, int, int]]:
    frame = np.asarray(frame_image.convert("RGB"), dtype=np.float32) / 255.0
    active_box = bbox(alpha > 0.12)
    if active_box is None:
        raise RuntimeError("Lighting reference lip mask produced no active mask.")

    params = material_params(STYLE_CONFIGS["gradient_lip"], primary, opacity, intensity)
    height, width = alpha.shape
    yy, xx = np.indices((height, width), dtype=np.float32)
    left = float(active_box["left"])
    right = float(active_box["right"])
    top = float(active_box["top"])
    bottom = float(active_box["bottom"])
    lip_width = max(1.0, right - left)
    lip_height = max(1.0, bottom - top)
    center_x = (left + right) * 0.5
    crease_y = top + lip_height * 0.48
    lower_center_y = top + lip_height * 0.64

    inner_line = np.exp(-np.abs(yy - crease_y) / max(1.0, lip_height * 0.23))
    lower_bloom = np.exp(
        -(
            ((xx - center_x) / max(1.0, lip_width * 0.43)) ** 2
            + ((yy - lower_center_y) / max(1.0, lip_height * 0.48)) ** 2
        )
    )
    center_bloom = np.exp(
        -(
            ((xx - center_x) / max(1.0, lip_width * 0.52)) ** 2
            + ((yy - crease_y) / max(1.0, lip_height * 0.70)) ** 2
        )
    )
    density_seed = np.clip(alpha * (0.48 * inner_line + 0.34 * lower_bloom + 0.18 * center_bloom), 0.0, 1.0)
    density_image = Image.fromarray(np.rint(density_seed * 255).astype(np.uint8), mode="L")
    density = np.asarray(density_image.filter(ImageFilter.GaussianBlur(radius=3.0)), dtype=np.float32) / 255.0

    gradient_mix = params["gradientAmount"]
    render_alpha = np.clip(
        alpha
        * (
            0.10
            + 0.90
            * np.power(
                np.clip(density * 1.30, 0.0, 1.0),
                0.58,
            )
        ),
        0.0,
        1.0,
    )
    render_alpha = np.asarray(
        Image.fromarray(np.rint(render_alpha * 255).astype(np.uint8), mode="L").filter(
            ImageFilter.GaussianBlur(radius=0.7)
        ),
        dtype=np.float32,
    ) / 255.0
    single_gradient_density = np.clip(render_alpha * np.power(np.clip(density * 1.45, 0.0, 1.0), 0.78), 0.0, 1.0)
    gradient_density_curve = np.power(single_gradient_density, 1.46 + (1.24 - 1.46) * gradient_mix)
    gradient_strength_scale = 0.72 + (1.08 - 0.72) * gradient_density_curve
    matte_reference_strength = render_alpha * 0.50
    pigment_color = np.clip(lerp(params["regionColor"], params["regionColor"] * 0.82, 0.28), 0.0, 1.0)
    coverage = max(params["coverage"], 0.001)
    max_pigment_strength = float(np.clip((0.42 + (0.66 - 0.42) * coverage) + 0.14, 0.0, 1.0))
    pigment_strength = np.minimum(
        np.clip(
            matte_reference_strength
            * gradient_strength_scale
            * params["opacity"]
            * params["preserveScale"],
            0.0,
            1.0,
        ),
        max_pigment_strength,
    )
    pigment_filter = np.clip((1.0 - pigment_strength[..., None]) + pigment_color * pigment_strength[..., None], 0.0, 1.0)
    rendered = np.clip(frame * pigment_filter, 0.0, 1.0)

    empty = Image.fromarray(np.zeros((height, width), dtype=np.uint8), mode="L")
    mask_channel = Image.fromarray(np.rint(render_alpha * 255).astype(np.uint8), mode="L")
    density_channel = Image.fromarray(np.rint(single_gradient_density * 255).astype(np.uint8), mode="L")
    mask_image = Image.merge("RGB", (mask_channel, empty, empty))
    density_rgb = density_channel.convert("RGB")
    rendered_image = to_image(rendered)
    crop = expand_crop(active_box, frame_image.size, pad_x=80, pad_y=65)
    sheet = make_sheet(
        [
            ("bright source", frame_image),
            ("photo-aligned gradient", rendered_image),
            ("aligned lip mask", mask_image),
            ("continuous density", density_rgb),
        ],
        crop,
    )
    active = render_alpha > 0.12
    render_box = bbox(active) or active_box
    active_density = single_gradient_density[active]
    active_strength = pigment_strength[active]
    summary = {
        "status": "photo_aligned_lighting_reference_preview",
        "notArfaceEvidence": True,
        "method": method,
        "limitation": (
            "This preview is aligned to the lighting reference photo only; it has no same-frame "
            "ARFace screenVertices/uvs/indices and must not be used as AR attachment evidence."
        ),
        "primaryColor": "#" + "".join(f"{int(round(c * 255)):02X}" for c in primary),
        "bbox": render_box,
        "gradient": {
            "pigmentColorRangeMax": 0.0,
            "pigmentStrengthMean": float(active_strength.mean()) if len(active_strength) else 0.0,
            "pigmentStrengthP95": float(np.percentile(active_strength, 95)) if len(active_strength) else 0.0,
            "densityMean": float(active_density.mean()) if len(active_density) else 0.0,
            "densityP95": float(np.percentile(active_density, 95)) if len(active_density) else 0.0,
        },
    }
    return (
        {
            "source": frame_image.convert("RGB"),
            "preview": rendered_image,
            "mask": mask_image,
            "density": density_rgb,
            "sheet": sheet,
        },
        summary,
        crop,
    )


def save(path: Path, image: Image.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path)


def verdict(summary: dict[str, Any]) -> dict[str, Any]:
    culling = summary["meshCulling"]
    gradient = summary["metrics"]["gradient_lip"]
    gradient_ramp = summary["metrics"]["gradient_lip"]["gradientRamp"]
    gloss = summary["metrics"]["gloss_lip"]
    wet = gloss["wetHighlight"]
    red_ratio = summary["metrics"]["glossRedBasePreservationRatio"]
    checks = {
        "meshCullingTight": culling["acceptedTriangles"] <= 400 and culling["cullRatio"] >= 0.75,
        "gradientContinuous": gradient_ramp["adjacentDensityDeltaP95"] <= 0.05
        and gradient_ramp["centerLineMaxJump"] <= 0.16
        and gradient_ramp["edgeInnerPigmentRatio"] <= 0.30,
        "gradientMatchesMattePigment": summary["metrics"].get("gradientMattePigmentDeltaMax", 1.0)
        <= 1.0e-6,
        "gradientCoverageVisible": (
            gradient["changed"]["pixelCount"] / max(gradient["fullSoft"]["pixelCount"], 1)
        )
        >= 0.78,
        "gradientNotBroadLeak": gradient.get("outsideSourceDilatedRatio", 0.0) <= 0.12,
        "glossWetHighlightLocalized": wet["pixelCount"] > 0
        and wet["heightToLipHeight"] <= 0.50
        and 1 <= wet["componentCount"] <= 2,
        "glossRedBasePreserved": red_ratio >= 0.90,
        "glossNotBroadLeak": gloss.get("outsideSourceDilatedRatio", 0.0) <= 0.12,
    }
    return {
        "status": "expected_ar_preview_pass" if all(checks.values()) else "expected_ar_preview_review",
        "checks": checks,
    }


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    frame_path = resolve(repo, args.frame)
    arface_path = resolve(repo, args.arface)
    atlas_path = resolve(repo, args.atlas)
    gradient_atlas_path = resolve(repo, args.gradient_atlas)
    source_mask_path = resolve(repo, args.source_mask)
    lighting_reference_path = resolve(repo, args.lighting_reference_frame)
    out_dir = resolve(repo, args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_image = Image.open(frame_path).convert("RGB")
    frame = np.asarray(frame_image, dtype=np.float32) / 255.0
    atlas = load_rgba(atlas_path)
    gradient_atlas = load_rgba(gradient_atlas_path)
    arface = read_arface(arface_path)
    source_mask = None
    if source_mask_path.exists():
        source_mask = np.asarray(Image.open(source_mask_path).convert("L"), dtype=np.uint8) > 8

    covered, uv_map, polygons, culling = rasterize_runtime_uv_map(
        arface,
        atlas,
        output_shape=frame.shape[:2],
        threshold=LIP_STYLE_ATLAS_THRESHOLD,
    )
    primary = hex_rgb(args.primary_color)
    outputs: dict[str, str] = {}
    metrics: dict[str, Any] = {}
    rendered_images: dict[str, Image.Image] = {}
    base_rendered_by_style: dict[str, np.ndarray] = {}
    layers_by_style: dict[str, dict[str, np.ndarray]] = {}
    params_by_style: dict[str, Any] = {}

    for style_name, config in STYLE_CONFIGS.items():
        params = material_params(config, primary, args.opacity, args.intensity)
        style_atlas = gradient_atlas if style_name == "gradient_lip" else atlas
        rendered, base_rendered, layers = render_style(frame, style_atlas, covered, uv_map, config, params)
        rendered_image = to_image(rendered)
        rendered_images[style_name] = rendered_image
        base_rendered_by_style[style_name] = base_rendered
        layers_by_style[style_name] = layers
        outputs[style_name] = save(out_dir / f"expected_{style_name}.png", rendered_image)
        outputs[f"{style_name}_layer_diagnostic"] = save(
            out_dir / f"expected_{style_name}_layers.png",
            layer_diagnostic_image(layers),
        )
        style_summary = style_metrics(
            frame,
            rendered,
            base_rendered,
            layers,
            source_mask,
            args.changed_threshold,
        )
        if style_name == "gradient_lip":
            style_summary["gradientRamp"] = gradient_metrics(layers)
        metrics[style_name] = style_summary
        serializable_params = {
            key: (value.tolist() if isinstance(value, np.ndarray) else value)
            for key, value in params.items()
        }
        params_by_style[style_name] = serializable_params

    matte_active = layers_by_style["matte_lip"]["fullSoft"] > 0.12
    gloss_non_wet = matte_active & (layers_by_style["gloss_lip"]["highlight"] <= 0.006)
    if int(gloss_non_wet.sum()) > 0:
        matte_red = float(redness(base_rendered_by_style["matte_lip"])[gloss_non_wet].mean())
        gloss_red = float(redness(base_rendered_by_style["gloss_lip"])[gloss_non_wet].mean())
        metrics["glossRedBasePreservationRatio"] = gloss_red / max(matte_red, 1.0e-6)
    else:
        metrics["glossRedBasePreservationRatio"] = 0.0
    gradient_active = (
        (layers_by_style["matte_lip"]["fullSoft"] > 0.12)
        & (layers_by_style["gradient_lip"]["fullSoft"] > 0.12)
    )
    if int(gradient_active.sum()) > 0:
        matte_color = np.stack(
            [
                layers_by_style["matte_lip"]["pigmentColorR"],
                layers_by_style["matte_lip"]["pigmentColorG"],
                layers_by_style["matte_lip"]["pigmentColorB"],
            ],
            axis=-1,
        )
        gradient_color = np.stack(
            [
                layers_by_style["gradient_lip"]["pigmentColorR"],
                layers_by_style["gradient_lip"]["pigmentColorG"],
                layers_by_style["gradient_lip"]["pigmentColorB"],
            ],
            axis=-1,
        )
        metrics["gradientMattePigmentDeltaMax"] = float(
            np.abs(gradient_color[gradient_active] - matte_color[gradient_active]).max()
        )
    else:
        metrics["gradientMattePigmentDeltaMax"] = 1.0

    diagnostic = overlay_diagnostic(frame_image, source_mask, covered, polygons)
    outputs["meshCullingDiagnostic"] = save(out_dir / "mesh_culling_diagnostic.png", diagnostic)
    gradient_changed = changed_mask(frame, np.asarray(rendered_images["gradient_lip"], dtype=np.float32) / 255.0, args.changed_threshold)
    gloss_changed = changed_mask(frame, np.asarray(rendered_images["gloss_lip"], dtype=np.float32) / 255.0, args.changed_threshold)
    outputs["gradientChangedOverlay"] = save(
        out_dir / "expected_gradient_lip_changed_overlay.png",
        changed_overlay(frame_image, gradient_changed, (217, 75, 116)),
    )
    outputs["glossChangedOverlay"] = save(
        out_dir / "expected_gloss_lip_changed_overlay.png",
        changed_overlay(frame_image, gloss_changed, (248, 166, 175)),
    )

    combined_box = (
        bbox(
            covered
            | changed_mask(frame, np.asarray(rendered_images["matte_lip"], dtype=np.float32) / 255.0, args.changed_threshold)
            | gradient_changed
            | gloss_changed
        )
        or culling["coveredBbox"]
    )
    if combined_box is None:
        raise RuntimeError("No ARFace lip coverage was rendered.")
    crop = expand_crop(combined_box, frame_image.size)
    panels = [
        (
            "mesh cull",
            label_panel(
                diagnostic,
                "runtime mesh culling",
                "green source / rose accepted ARFace triangles",
            ),
        ),
        (
            "matte frozen",
            label_panel(
                rendered_images["matte_lip"],
                "matte_lip expected",
                "baseline only; runtime code unchanged",
            ),
        ),
        (
            "gradient",
            label_panel(
                rendered_images["gradient_lip"],
                "gradient_lip expected",
                "continuous ramp from weak edge to inner tint",
            ),
        ),
        (
            "gloss",
            label_panel(
                rendered_images["gloss_lip"],
                "gloss_lip expected",
                "red base + localized tinted wet line",
            ),
        ),
        (
            "gradient delta",
            label_panel(
                changed_overlay(frame_image, gradient_changed, (217, 75, 116)),
                "gradient changed pixels",
                "checks broad spill outside source lip",
            ),
        ),
        (
            "gloss layers",
            label_panel(
                layer_diagnostic_image(layers_by_style["gloss_lip"]),
                "gloss layer diagnostic",
                "R pigment / G soft mask / B wet highlight",
            ),
        ),
    ]
    sheet = make_sheet(panels, crop)
    outputs["sheet"] = save(out_dir / "ar_runtime_expected_sheet.png", sheet)

    lighting_reference_preview_summary: dict[str, Any] = {
        "status": "skipped" if args.skip_lighting_reference_preview else "missing",
        "path": str(lighting_reference_path.relative_to(repo))
        if lighting_reference_path.exists()
        else str(args.lighting_reference_frame),
        "notArfaceEvidence": True,
    }
    if not args.skip_lighting_reference_preview and lighting_reference_path.exists():
        lighting_image = Image.open(lighting_reference_path).convert("RGB")
        alpha_data = load_lighting_reference_alpha(
            repo,
            lighting_reference_path,
            lighting_image.size,
            args.lighting_reference_mask,
        )
        if alpha_data is None:
            lighting_reference_preview_summary = {
                **lighting_reference_preview_summary,
                "status": "missing_photo_aligned_mask",
                "limitation": (
                    "A lighting reference frame was found, but no explicit mask was provided and "
                    "the default hand-aligned outline only applies to the saved bright reference photo."
                ),
            }
        else:
            lighting_alpha, _lighting_hard, lighting_method = alpha_data
            lighting_images, lighting_reference_preview_summary, lighting_crop = render_lighting_reference_preview(
                lighting_image,
                primary,
                args.opacity,
                args.intensity,
                lighting_method,
                lighting_alpha,
            )
            lighting_reference_preview_summary["path"] = str(lighting_reference_path.relative_to(repo))
            outputs["lightingReferenceSource"] = save(
                out_dir / "bright_lighting_reference_source.png",
                lighting_images["source"],
            )
            outputs["lightingReferenceGradientPreview"] = save(
                out_dir / "bright_lighting_reference_gradient_lip_photo_aligned_preview.png",
                lighting_images["preview"],
            )
            outputs["lightingReferenceMask"] = save(
                out_dir / "bright_lighting_reference_photo_aligned_mask.png",
                lighting_images["mask"],
            )
            outputs["lightingReferenceDensity"] = save(
                out_dir / "bright_lighting_reference_photo_aligned_density.png",
                lighting_images["density"],
            )
            outputs["lightingReferenceSheet"] = save(
                out_dir / "bright_lighting_reference_gradient_lip_photo_aligned_sheet.png",
                lighting_images["sheet"],
            )
            outputs["twoReferenceGradientComparison"] = save(
                out_dir / "gradient_two_reference_preview.png",
                make_mixed_crop_sheet(
                    [
                        ("ARFace-based expected render", rendered_images["gradient_lip"], crop),
                        (
                            "Bright photo-aligned lighting preview",
                            lighting_images["preview"],
                            lighting_crop,
                        ),
                    ],
                ),
            )
            lighting_reference_preview_summary["outputs"] = {
                "sheet": outputs["lightingReferenceSheet"],
                "preview": outputs["lightingReferenceGradientPreview"],
                "comparison": outputs["twoReferenceGradientComparison"],
            }

    summary: dict[str, Any] = {
        "status": "offline_ar_runtime_expected_preview",
        "scope": "E7 validation-only buildless expected AR render",
        "frame": str(frame_path.relative_to(repo)),
        "arface": str(arface_path.relative_to(repo)),
        "atlas": str(atlas_path.relative_to(repo)),
        "gradientAtlas": str(gradient_atlas_path.relative_to(repo)),
        "sourceMask": str(source_mask_path.relative_to(repo)) if source_mask_path.exists() else None,
        "lightingReferencePreview": lighting_reference_preview_summary,
        "runtimeMirrors": [
            "RN default lip recipe intensity=0.84 opacity=0.90 color=#D94B74",
            "E3RegionMaskOverlay BuildMaterialColor style alpha/brightness scales",
            "lip-drawn-style-atlas-v1 R-channel triangle culling threshold=0.025",
            "gradient_lip samples lip-drawn-gradient-density-atlas-v1 B-channel distance field",
            "ARFace screenVertices/uvs/indices rasterization",
            "SmoothRegionMask first multiply pass and gloss additive pass",
        ],
        "notRuntimeAcceptance": [
            "No UnityFramework build/sync was run.",
            "No RN real-device install or iPhone visual session was run.",
            "No camera/light/depth runtime variability is modeled.",
            "Lighting reference preview is photo-aligned only, not same-frame ARFace attachment evidence.",
        ],
        "meshCulling": culling,
        "materialParams": params_by_style,
        "metrics": metrics,
        "outputs": outputs,
        "crop": {
            "left": crop[0],
            "top": crop[1],
            "right": crop[2],
            "bottom": crop[3],
            "width": crop[2] - crop[0],
            "height": crop[3] - crop[1],
        },
    }
    summary["verdict"] = verdict(summary)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_lines = [
        "# Lip AR Runtime Expected Preview",
        "",
        f"- Status: `{summary['verdict']['status']}`",
        f"- Sheet: `{outputs['sheet']}`",
        f"- Mesh culling: `{culling['acceptedTriangles']}/{culling['sourceTriangles']}` accepted",
        f"- Gradient outside-source ratio: `{metrics['gradient_lip'].get('outsideSourceDilatedRatio', 0.0):0.4f}`",
        f"- Gloss wet components: `{metrics['gloss_lip']['wetHighlight']['componentCount']}`",
        f"- Gloss red base preservation ratio: `{metrics['glossRedBasePreservationRatio']:0.4f}`",
    ]
    if outputs.get("lightingReferenceSheet"):
        summary_lines.extend(
            [
                f"- Bright lighting photo-aligned sheet: `{outputs['lightingReferenceSheet']}`",
                f"- Two-reference gradient comparison: `{outputs['twoReferenceGradientComparison']}`",
            ]
        )
    summary_lines.extend(
        [
            "",
            "This is buildless expected AR evidence based on the current code path.",
            "The lighting reference preview is photo-aligned color/lighting review only, not ARFace evidence.",
            "It is not Unity/RN real-device acceptance evidence.",
            "",
        ]
    )
    (out_dir / "summary.md").write_text("\n".join(summary_lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["verdict"]["status"],
                "sheet": outputs["sheet"],
                "lightingReferencePreview": {
                    "status": lighting_reference_preview_summary.get("status"),
                    "sheet": outputs.get("lightingReferenceSheet"),
                    "comparison": outputs.get("twoReferenceGradientComparison"),
                    "notArfaceEvidence": lighting_reference_preview_summary.get("notArfaceEvidence"),
                },
                "meshCulling": culling,
                "gradient": {
                    "outsideSourceDilatedRatio": metrics["gradient_lip"].get(
                        "outsideSourceDilatedRatio",
                        0.0,
                    ),
                    "gradientRamp": metrics["gradient_lip"]["gradientRamp"],
                },
                "gloss": {
                    "wetHighlight": metrics["gloss_lip"]["wetHighlight"],
                    "redBasePreservationRatio": metrics["glossRedBasePreservationRatio"],
                    "outsideSourceDilatedRatio": metrics["gloss_lip"].get(
                        "outsideSourceDilatedRatio",
                        0.0,
                    ),
                },
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
