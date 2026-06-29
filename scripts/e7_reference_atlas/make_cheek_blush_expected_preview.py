#!/usr/bin/env python3
"""Create a no-build expected cheek blush render from current RN/Unity settings."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
FRAME_PATH = ROOT / "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png"
ARFACE_PATH = ROOT / "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/arface_export.json"
MASK_ROOT = ROOT / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
EVIDENCE_ROOT = ROOT / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1"
OUTPUT_ROOT = EVIDENCE_ROOT / "expected_render_20260629_current_session_png"

MASKS = (
    ("Mask 1", "blush_session_1", "cheek-session-mask-1-v1", 0.78, "#F2A59A", 0.76, (1.00, 1.00, 0.000, 0.000), (1.00, 1.00, 0.000, 0.000), 0.00, 0.94, 0.00),
    ("Mask 2", "blush_session_2", "cheek-session-mask-2-v1", 0.78, "#F3A1A6", 0.76, (1.02, 0.84, 0.000, 0.000), (1.00, 1.00, 0.000, 0.000), 0.00, 0.98, 0.00),
    ("Mask 3", "blush_session_3", "cheek-session-mask-3-v1", 0.78, "#F0A0B0", 0.76, (1.28, 1.72, 0.000, -0.015), (1.00, 1.00, 0.000, 0.000), 0.00, 2.05, 0.00),
    ("Mask 4", "blush_session_4", "cheek-session-mask-4-v1", 0.78, "#EFA07F", 0.76, (1.14, 1.20, 0.000, 0.018), (2.038, 0.981, 0.000, -0.037), 1.00, 1.70, 0.36),
    ("Mask 5", "blush_session_5", "cheek-session-mask-5-v1", 0.78, "#EAA07A", 0.76, (1.02, 0.96, 0.000, -0.018), (1.00, 1.00, 0.000, 0.000), 0.00, 0.94, 0.36),
)
SOURCE_DRAWINGS = {
    "cheek-session-mask-1-v1": Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4/image-1.png"),
    "cheek-session-mask-2-v1": Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4/image-2.png"),
    "cheek-session-mask-3-v1": Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4/image-3.png"),
    "cheek-session-mask-4-v1": Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4/image-4.png"),
    "cheek-session-mask-5-v1": Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4/image-5.png"),
}

ROSE = np.array([0xD9, 0x4B, 0x74], dtype=np.float32) / 255.0
CHEEK_OPACITY = 0.58
PRESERVE_SCALE = 0.92
SKIN_PRESERVE = 0.74
SATURATION_BOOST = 0.30
WARMTH = 0.24
EDGE_SOFTNESS = 0.94
DENSITY_POWER = 0.74
CROP_BOX = (110, 710, 1060, 1460)


def load_arface(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    local_vertices = np.asarray(data["localVertices"], dtype=np.float32)[:, :2]
    screen_vertices = np.asarray(data["screenVertices"], dtype=np.float32)[:, :2]
    uvs = np.asarray(data["uvs"], dtype=np.float32)[:, :2]
    indices = np.asarray(data["indices"], dtype=np.int32).reshape((-1, 3))
    return local_vertices, screen_vertices, uvs, indices


def build_cheek_face_local_uvs(local_vertices: np.ndarray) -> np.ndarray:
    min_xy = np.percentile(local_vertices, 1.0, axis=0)
    max_xy = np.percentile(local_vertices, 99.0, axis=0)
    span = np.maximum(max_xy - min_xy, 1.0e-6)
    min_xy = min_xy - span * np.array([0.10, 0.08], dtype=np.float32)
    max_xy = max_xy + span * np.array([0.10, 0.08], dtype=np.float32)
    span = np.maximum(max_xy - min_xy, 1.0e-6)
    return np.clip((local_vertices - min_xy) / span, 0.0, 1.0)


def smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - edge0) / max(edge1 - edge0, 1.0e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def parse_hex_color(value: str) -> np.ndarray:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}")
    return np.array(
        [int(value[index : index + 2], 16) for index in (0, 2, 4)],
        dtype=np.float32,
    ) / 255.0


def project_uv_mask_to_screen(
    mask: Image.Image,
    frame_size: tuple[int, int],
    channel: str,
    uv_transform: tuple[float, float, float, float],
    part_uv_transform: tuple[float, float, float, float],
    part_blend: float,
    density_gain: float,
    center_gain: float,
) -> np.ndarray:
    local_vertices, screen_vertices, _uvs, indices = load_arface(ARFACE_PATH)
    face_local_uvs = build_cheek_face_local_uvs(local_vertices)
    width, height = frame_size
    rgb = np.asarray(mask.convert("RGB"), dtype=np.float32) / 255.0
    luminance = (
        rgb[..., 0] * 0.2126
        + rgb[..., 1] * 0.7152
        + rgb[..., 2] * 0.0722
    )
    gray_strength = np.clip((0.965 - luminance) / 0.412, 0.0, 1.0)
    mask_height, mask_width = gray_strength.shape
    alpha = np.zeros((height, width), dtype=np.float32)
    scale_x, scale_y, offset_x, offset_y = uv_transform

    for triangle in indices:
        points = screen_vertices[triangle]
        uv_points = face_local_uvs[triangle]
        left = max(int(np.floor(float(points[:, 0].min()))), 0)
        right = min(int(np.ceil(float(points[:, 0].max()))), width - 1)
        top = max(int(np.floor(float(points[:, 1].min()))), 0)
        bottom = min(int(np.ceil(float(points[:, 1].max()))), height - 1)
        if right < left or bottom < top:
            continue

        grid_y, grid_x = np.mgrid[top : bottom + 1, left : right + 1]
        x1, y1 = points[0]
        x2, y2 = points[1]
        x3, y3 = points[2]
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(float(denominator)) < 1.0e-5:
            continue

        w1 = ((y2 - y3) * (grid_x - x3) + (x3 - x2) * (grid_y - y3)) / denominator
        w2 = ((y3 - y1) * (grid_x - x3) + (x1 - x3) * (grid_y - y3)) / denominator
        w3 = 1.0 - w1 - w2
        inside = (w1 >= -1.0e-4) & (w2 >= -1.0e-4) & (w3 >= -1.0e-4)
        if not inside.any():
            continue

        projected_uv = (
            uv_points[0] * w1[..., None]
            + uv_points[1] * w2[..., None]
            + uv_points[2] * w3[..., None]
        )
        cheek_uv = np.clip(
            (projected_uv - 0.5)
            / np.array(
                [max(abs(scale_x), 1.0e-6), max(abs(scale_y), 1.0e-6)],
                dtype=np.float32,
            )
            + 0.5
            + np.array([offset_x, offset_y], dtype=np.float32),
            0.0,
            1.0,
        )
        valid = (
            inside
            & (cheek_uv[..., 0] >= 0.0)
            & (cheek_uv[..., 0] <= 1.0)
            & (cheek_uv[..., 1] >= 0.0)
            & (cheek_uv[..., 1] <= 1.0)
        )
        if not valid.any():
            continue

        valid_uv = cheek_uv[valid]
        sample_x = np.rint(valid_uv[..., 0] * (mask_width - 1)).astype(np.int32)
        sample_y = np.rint((1.0 - valid_uv[..., 1]) * (mask_height - 1)).astype(np.int32)
        center_uv = valid_uv - np.array([0.5, 0.5], dtype=np.float32)
        center_gate = (
            1.0 - smoothstep(0.025, 0.255, np.abs(center_uv[..., 0]))
        ) * (
            1.0 - smoothstep(0.020, 0.245, np.abs(center_uv[..., 1]))
        )
        sampled_gray = gray_strength[sample_y, sample_x]
        boost_gate = center_gate
        part_strength = float(np.clip(part_blend, 0.0, 1.0))
        if part_strength > 0.001:
            part_scale_x, part_scale_y, part_offset_x, part_offset_y = part_uv_transform
            part_uv = np.clip(
                (valid_uv - 0.5)
                / np.array(
                    [max(abs(part_scale_x), 1.0e-6), max(abs(part_scale_y), 1.0e-6)],
                    dtype=np.float32,
                )
                + 0.5
                + np.array([part_offset_x, part_offset_y], dtype=np.float32),
                0.0,
                1.0,
            )
            part_sample_x = np.rint(part_uv[..., 0] * (mask_width - 1)).astype(np.int32)
            part_sample_y = np.rint((1.0 - part_uv[..., 1]) * (mask_height - 1)).astype(np.int32)
            part_center_uv = part_uv - np.array([0.5, 0.5], dtype=np.float32)
            part_ellipse = np.sqrt(
                (part_center_uv[..., 0] / 0.220) ** 2
                + (part_center_uv[..., 1] / 0.170) ** 2
            )
            part_gate = 1.0 - smoothstep(0.74, 1.04, part_ellipse)
            side_gate = smoothstep(0.19, 0.32, np.abs(valid_uv[..., 0] - 0.5))
            upper_gate = 1.0 - smoothstep(0.74, 0.91, valid_uv[..., 1])
            outer_patch_gate = np.clip(np.maximum(side_gate * upper_gate, 0.18), 0.0, 1.0)
            sampled_gray *= 1.0 - part_strength * 0.58 + part_strength * 0.58 * outer_patch_gate
            original_center_suppress = center_gate * part_strength
            sampled_gray = np.maximum(
                sampled_gray * (1.0 - original_center_suppress * 0.90),
                gray_strength[part_sample_y, part_sample_x] * part_gate * part_strength,
            )
            boost_gate = np.maximum(
                center_gate * (1.0 - original_center_suppress * 0.82),
                part_gate * part_strength,
            )
        sampled_gray = np.clip(
            sampled_gray
            * density_gain
            * (1.0 + center_gain * boost_gate),
            0.0,
            1.0,
        )
        sampled = np.clip(sampled_gray**1.16, 0.0, 1.0) if channel == "density" else sampled_gray
        target = alpha[grid_y[valid], grid_x[valid]]
        alpha[grid_y[valid], grid_x[valid]] = np.maximum(target, sampled)

    return alpha


def overlay_alpha(frame: Image.Image, alpha: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    base = frame.convert("RGBA")
    alpha_image = Image.fromarray(np.rint(np.clip(alpha, 0.0, 1.0) * 155).astype(np.uint8), mode="L")
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(radius=1.2))
    overlay = Image.new("RGBA", frame.size, (*color, 0))
    overlay.putalpha(alpha_image)
    return Image.alpha_composite(base, overlay).convert("RGB")


def render_expected(
    frame: Image.Image,
    alpha: np.ndarray,
    density: np.ndarray,
    coverage: float,
    secondary_hex: str,
    intensity: float,
    sample_name: str,
) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32) / 255.0
    alpha_image = Image.fromarray(
        np.rint(np.clip(alpha, 0.0, 1.0) * 255).astype(np.uint8),
        mode="L",
    )
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(radius=4.0))
    density_image = Image.fromarray(
        np.rint(np.clip(density, 0.0, 1.0) * 255).astype(np.uint8),
        mode="L",
    )
    density_image = density_image.filter(ImageFilter.GaussianBlur(radius=3.0))
    soft = np.asarray(alpha_image, dtype=np.float32) / 255.0
    density_blurred = np.asarray(density_image, dtype=np.float32) / 255.0
    cheek_feather = max(0.86, 0.68) * (1.02 + (1.20 - 1.02) * EDGE_SOFTNESS)
    coverage_soft = smoothstep(0.025 * 0.72 - cheek_feather * 0.46, 0.025 * 0.72 + cheek_feather, soft)
    coverage_wide = np.clip(
        coverage_soft ** (0.74 + (0.56 - 0.74) * EDGE_SOFTNESS),
        0.0,
        1.0,
    )
    density_soft = np.clip(density * (1.0 - 0.62) + density_blurred * 0.62, 0.0, 1.0)
    density_field = np.maximum(density, density_blurred * 0.82)
    secondary = parse_hex_color(secondary_hex)
    blush_pigment = np.clip(ROSE * (1.0 - 0.04) + secondary * 0.04, 0.0, 1.0)
    pigment_warmth = np.clip(
        (blush_pigment[0] - max(blush_pigment[1], blush_pigment[2])) * 2.25
        + SATURATION_BOOST * 0.18,
        0.0,
        1.0,
    )

    outer_band = np.clip(coverage_wide * smoothstep(0.004, 0.18, soft), 0.0, 1.0)
    mid_band = np.clip(
        coverage_wide
        * np.clip(density_soft + density_blurred * 0.08, 0.0, 1.0)
        ** (1.55 + (1.15 - 1.55) * DENSITY_POWER),
        0.0,
        1.0,
    )
    core_band = np.clip(
        coverage_wide * np.clip(density_field, 0.0, 1.0) ** (2.60 + (1.70 - 2.60) * DENSITY_POWER),
        0.0,
        1.0,
    )
    mid_band = np.clip(mid_band ** (1.24 + (0.98 - 1.24) * DENSITY_POWER), 0.0, 1.0)
    core_band = np.clip(core_band ** (1.50 + (0.98 - 1.50) * DENSITY_POWER), 0.0, 1.0)
    slider_curve = intensity * intensity * (3.0 - 2.0 * intensity)
    slider_mid_curve = intensity**1.05
    slider_core_curve = intensity**1.18
    opacity_scale = np.clip(CHEEK_OPACITY * PRESERVE_SCALE * (1.00 + (1.65 - 1.00) * slider_curve), 0.0, 1.0)
    outer_strength = np.clip(outer_band * opacity_scale * (0.035 + (0.095 - 0.035) * slider_curve), 0.0, 1.0)
    mid_strength = np.clip(mid_band * opacity_scale * (0.065 + (0.620 - 0.065) * slider_mid_curve), 0.0, 1.0)
    core_strength = np.clip(core_band * opacity_scale * (0.015 + (1.200 - 0.015) * slider_core_curve), 0.0, 1.0)

    outer_target = np.array(
        [
            1.0,
            (0.995 + (0.965 - 0.995) * pigment_warmth) - WARMTH * 0.003,
            (0.995 + (0.970 - 0.995) * pigment_warmth) - WARMTH * 0.004,
        ],
        dtype=np.float32,
    )
    mid_target = np.array(
        [
            1.0,
            (0.955 + (0.70 - 0.955) * pigment_warmth) - WARMTH * 0.020,
            (0.970 + (0.78 - 0.970) * pigment_warmth) - WARMTH * 0.022,
        ],
        dtype=np.float32,
    )
    core_target = np.array(
        [
            1.0,
            (0.920 + (0.44 - 0.920) * pigment_warmth) - WARMTH * 0.024,
            (0.940 + (0.58 - 0.940) * pigment_warmth) - WARMTH * 0.030,
        ],
        dtype=np.float32,
    )
    outer_target = np.clip(np.maximum(outer_target, np.array([0.97, 0.94, 0.945])), 0.0, 1.0)
    mid_target = np.clip(np.maximum(mid_target, np.array([0.86, 0.66, 0.70])), 0.0, 1.0)
    core_target = np.clip(np.maximum(core_target, np.array([0.80, 0.42, 0.52])), 0.0, 1.0)
    outer_filter = 1.0 + (outer_target.reshape((1, 1, 3)) - 1.0) * outer_strength[..., None]
    mid_filter = 1.0 + (mid_target.reshape((1, 1, 3)) - 1.0) * mid_strength[..., None]
    core_filter = 1.0 + (core_target.reshape((1, 1, 3)) - 1.0) * core_strength[..., None]
    rendered = np.clip(base * outer_filter * mid_filter * core_filter, 0.0, 1.0)
    return Image.fromarray(np.rint(rendered * 255).astype(np.uint8), mode="RGB")


def source_mask_preview(mask_id: str) -> Image.Image:
    atlas_path = EVIDENCE_ROOT / "atlas" / f"{mask_id}-source-original.png"
    if atlas_path.exists():
        return Image.open(atlas_path).convert("RGB")
    source_path = SOURCE_DRAWINGS.get(mask_id)
    if source_path is None or not source_path.exists():
        return Image.new("RGB", (320, 320), (246, 246, 246))
    return Image.open(source_path).convert("RGB")


def crop_thumb(image: Image.Image, width: int = 320, height: int = 260) -> Image.Image:
    crop = image.crop(CROP_BOX)
    crop.thumbnail((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height), (246, 246, 246))
    tile.paste(crop, ((width - crop.width) // 2, (height - crop.height) // 2))
    return tile


def fit_thumb(image: Image.Image, width: int = 320, height: int = 260) -> Image.Image:
    thumb = image.convert("RGB").copy()
    thumb.thumbnail((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height), (246, 246, 246))
    tile.paste(thumb, ((width - thumb.width) // 2, (height - thumb.height) // 2))
    return tile


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    frame = Image.open(FRAME_PATH).convert("RGB")
    columns = ("source 2D PNG", "face-local alpha", "face-local density", "expected render")
    tile_w, tile_h, label_h = 320, 260, 32
    sheet = Image.new(
        "RGB",
        (tile_w * len(columns), (tile_h + label_h) * (len(MASKS) + 1)),
        (245, 245, 245),
    )
    draw = ImageDraw.Draw(sheet)
    for col, label in enumerate(columns):
        draw.text((col * tile_w + 8, 9), label, fill=(0, 0, 0))

    summary: dict[str, object] = {
        "previewId": "cheek-blush-expected-render-20260629-multiband-skin-aware",
        "runtimeSelectionRule": "one user-supplied cheek blush 2D texture is selected per cheek layer",
        "atlasSourceRule": "the user-provided 2D PNG is sampled directly; source RGB luminance defines where blush is applied and darker gray defines stronger density",
        "color": "#D94B74",
        "opacity": CHEEK_OPACITY,
        "materialAlphaRule": "opacity stays independent from intensity; intensity curves outer, mid, and core bands separately",
        "edgeContract": "coverage alpha keeps a wide soft support while the outer band stays skin-close so bright colors do not reveal a hard edge",
        "blendContract": "cheek blush uses a three-band skin-aware multiply filter, not simple source-over alpha color",
        "coreEdgeContract": "visible blush fades through outer, mid, and core bands with smoothstep/gaussian falloff and no hard thresholds",
        "projectionNote": "source 2D PNGs are copied exactly; face-local alpha/density columns show the same texture sampled through cheek mesh face-local x/y UVs, so the flat drawing position is preserved on the face instead of being warped by the default ARFace UV layout",
        "placementCalibrationRule": "cheek mesh UVs are rebuilt from face-local x/y coordinates; per-mask scale, component-aware part offset, and density gain are runtime shader parameters and do not replace or redraw the supplied 2D PNG atlases",
        "densityContract": {
            "blush_session_1": "direct session image-1 gray atlas; darker gray pixels become stronger density",
            "blush_session_2": "direct session image-2 gray atlas; darker gray pixels become stronger density",
            "blush_session_3": "direct session image-3 gray atlas; darker gray pixels become stronger density",
            "blush_session_4": "direct session image-4 gray atlas; darker gray pixels become stronger density",
            "blush_session_5": "direct session image-5 gray atlas; darker gray pixels become stronger density",
        },
        "frame": str(FRAME_PATH.relative_to(ROOT)),
        "rows": [],
    }

    for row, (
        label,
        sample_name,
        mask_id,
        coverage,
        secondary_hex,
        intensity,
        uv_transform,
        part_uv_transform,
        part_blend,
        density_gain,
        center_gain,
    ) in enumerate(MASKS, start=1):
        mask_path = MASK_ROOT / f"{mask_id}.png"
        uv_mask = Image.open(mask_path).convert("RGBA")
        projected_alpha = project_uv_mask_to_screen(
            uv_mask,
            frame.size,
            "alpha",
            uv_transform,
            part_uv_transform,
            part_blend,
            density_gain,
            center_gain,
        )
        projected_density = project_uv_mask_to_screen(
            uv_mask,
            frame.size,
            "density",
            uv_transform,
            part_uv_transform,
            part_blend,
            density_gain,
            center_gain,
        )
        source = source_mask_preview(mask_id)
        alpha_overlay = overlay_alpha(frame, projected_alpha, (238, 111, 98))
        density_overlay = overlay_alpha(frame, projected_density, (196, 76, 110))
        expected = render_expected(
            frame,
            projected_alpha,
            projected_density,
            coverage,
            secondary_hex,
            intensity,
            sample_name,
        )

        expected_path = OUTPUT_ROOT / f"expected_{mask_id}.png"
        alpha_path = OUTPUT_ROOT / f"projected_alpha_{mask_id}.png"
        density_path = OUTPUT_ROOT / f"projected_density_{mask_id}.png"
        expected.save(expected_path)
        Image.fromarray(np.rint(np.clip(projected_alpha, 0.0, 1.0) * 255).astype(np.uint8), mode="L").save(alpha_path)
        Image.fromarray(np.rint(np.clip(projected_density, 0.0, 1.0) * 255).astype(np.uint8), mode="L").save(density_path)

        y = row * (tile_h + label_h)
        draw.text((8, y + 8), f"{label} / {sample_name}", fill=(0, 0, 0))
        sheet.paste(fit_thumb(source, tile_w, tile_h), (0, y + label_h))
        for col, image in enumerate((alpha_overlay, density_overlay, expected), start=1):
            sheet.paste(crop_thumb(image, tile_w, tile_h), (col * tile_w, y + label_h))

        active = projected_alpha > 0.03
        rows = summary["rows"]
        assert isinstance(rows, list)
        rows.append(
            {
                "label": label,
                "textureSample": sample_name,
                "maskTextureId": mask_id,
                "coverage": coverage,
                "secondaryColor": secondary_hex,
                "intensity": intensity,
                "opacity": CHEEK_OPACITY,
                "uvTransform": uv_transform,
                "partUvTransform": part_uv_transform,
                "partBlend": part_blend,
                "densityGain": density_gain,
                "centerGain": center_gain,
                "outerStrengthCurve": "lerp(0.035,0.095,smoothstep(intensity))",
                "midStrengthCurve": "lerp(0.065,0.620,pow(intensity,1.05))",
                "coreStrengthCurve": "lerp(0.015,1.200,pow(intensity,1.18))",
                "projectedAlphaActivePixelsGt003": int(active.sum()),
                "expectedRender": str(expected_path.relative_to(ROOT)),
                "projectedAlpha": str(alpha_path.relative_to(ROOT)),
                "projectedDensity": str(density_path.relative_to(ROOT)),
            }
        )

    sheet_path = OUTPUT_ROOT / "cheek_blush_expected_render_sheet.png"
    sheet.save(sheet_path)
    summary["sheet"] = str(sheet_path.relative_to(ROOT))

    ramp_levels = (0.08, 0.35, 0.70, 1.0)
    ramp_sheet = Image.new(
        "RGB",
        (tile_w * len(ramp_levels), (tile_h + label_h) * (len(MASKS) + 1)),
        (245, 245, 245),
    )
    ramp_draw = ImageDraw.Draw(ramp_sheet)
    for col, level in enumerate(ramp_levels):
        ramp_draw.text((col * tile_w + 8, 9), f"intensity {level:.2f}", fill=(0, 0, 0))

    for row, (
        label,
        sample_name,
        mask_id,
        coverage,
        secondary_hex,
        _intensity,
        uv_transform,
        part_uv_transform,
        part_blend,
        density_gain,
        center_gain,
    ) in enumerate(MASKS, start=1):
        mask_path = MASK_ROOT / f"{mask_id}.png"
        uv_mask = Image.open(mask_path).convert("RGBA")
        projected_alpha = project_uv_mask_to_screen(
            uv_mask,
            frame.size,
            "alpha",
            uv_transform,
            part_uv_transform,
            part_blend,
            density_gain,
            center_gain,
        )
        projected_density = project_uv_mask_to_screen(
            uv_mask,
            frame.size,
            "density",
            uv_transform,
            part_uv_transform,
            part_blend,
            density_gain,
            center_gain,
        )
        y = row * (tile_h + label_h)
        ramp_draw.text((8, y + 8), f"{label} / {sample_name}", fill=(0, 0, 0))
        for col, level in enumerate(ramp_levels):
            rendered = render_expected(
                frame,
                projected_alpha,
                projected_density,
                coverage,
                secondary_hex,
                level,
                sample_name,
            )
            ramp_sheet.paste(crop_thumb(rendered, tile_w, tile_h), (col * tile_w, y + label_h))

    ramp_path = OUTPUT_ROOT / "cheek_blush_intensity_ramp_sheet.png"
    ramp_sheet.save(ramp_path)
    summary["intensityRampSheet"] = str(ramp_path.relative_to(ROOT))
    summary["intensityRampLevels"] = ramp_levels
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
