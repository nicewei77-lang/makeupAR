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
OUTPUT_ROOT = EVIDENCE_ROOT / "expected_render_20260627"

MASKS = (
    ("Daily", "blush_daily", "cheek-daily-mask-v1", 0.72, "#EA8F82", 0.54),
    ("Lovely", "blush_lovely", "cheek-lovely-mask-v1", 0.70, "#E98694", 0.52),
    ("Sun 1", "blush_sunkissed1", "cheek-sunkissed-mask1-v1", 0.68, "#E58965", 0.54),
    ("Sun 2", "blush_sunkissed2", "cheek-sunkissed-mask2-v1", 0.66, "#E9805C", 0.50),
    ("Under", "blush_under_eye", "cheek-under-eye-mask-v1", 0.62, "#E98EA2", 0.46),
)
SOURCE_DRAWINGS = {
    "cheek-daily-mask-v1": Path("/Users/yeoduchi/Downloads/cheek_daily_mask.png"),
    "cheek-lovely-mask-v1": Path("/Users/yeoduchi/Downloads/cheek_lovely_mask.png"),
    "cheek-sunkissed-mask1-v1": Path("/Users/yeoduchi/Downloads/cheek_sunkissed_mask1.png"),
    "cheek-sunkissed-mask2-v1": Path("/Users/yeoduchi/Downloads/cheek_sunkissed_mask2.png"),
    "cheek-under-eye-mask-v1": Path("/Users/yeoduchi/Downloads/under_eye_mask.png"),
}

ROSE = np.array([0xD9, 0x4B, 0x74], dtype=np.float32) / 255.0
CHEEK_OPACITY = 0.54
PRESERVE_SCALE = 0.92
SKIN_PRESERVE = 0.70
SATURATION_BOOST = 0.34
WARMTH = 0.28
CROP_BOX = (110, 710, 1060, 1460)
SUNKISSED2_PLACEMENT_BBOX = (220, 906, 917, 1052)


def load_arface(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    screen_vertices = np.asarray(data["screenVertices"], dtype=np.float32)[:, :2]
    uvs = np.asarray(data["uvs"], dtype=np.float32)[:, :2]
    indices = np.asarray(data["indices"], dtype=np.int32).reshape((-1, 3))
    return screen_vertices, uvs, indices


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
) -> np.ndarray:
    screen_vertices, uvs, indices = load_arface(ARFACE_PATH)
    width, height = frame_size
    rgba = np.asarray(mask.convert("RGBA"), dtype=np.float32) / 255.0
    if channel == "density":
        mask_values = rgba[:, :, 2]
    else:
        mask_values = np.maximum(rgba[:, :, 0], rgba[:, :, 3])
    mask_height, mask_width = mask_values.shape
    alpha = np.zeros((height, width), dtype=np.float32)

    for triangle in indices:
        points = screen_vertices[triangle]
        uv_points = uvs[triangle]
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
        valid = (
            inside
            & (projected_uv[..., 0] >= 0.0)
            & (projected_uv[..., 0] <= 1.0)
            & (projected_uv[..., 1] >= 0.0)
            & (projected_uv[..., 1] <= 1.0)
        )
        if not valid.any():
            continue

        sample_x = np.rint(projected_uv[..., 0][valid] * (mask_width - 1)).astype(np.int32)
        sample_y = np.rint((1.0 - projected_uv[..., 1][valid]) * (mask_height - 1)).astype(np.int32)
        sampled = mask_values[sample_y, sample_x]
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
) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32) / 255.0
    alpha_image = Image.fromarray(np.rint(np.clip(alpha, 0.0, 1.0) * 255).astype(np.uint8), mode="L")
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(radius=4.0))
    density_image = Image.fromarray(
        np.rint(np.clip(density, 0.0, 1.0) * 255).astype(np.uint8),
        mode="L",
    )
    density_image = density_image.filter(ImageFilter.GaussianBlur(radius=3.0))
    soft = np.asarray(alpha_image, dtype=np.float32) / 255.0
    density_soft = np.asarray(density_image, dtype=np.float32) / 255.0
    coverage_soft = smoothstep(0.025 - 0.76 * 0.46, 0.025 + 0.76, soft)
    density_mix = np.clip(density * (1.0 - 0.42) + density_soft * 0.42, 0.0, 1.0)
    density_curve = smoothstep(0.006, 0.62, density_mix)
    density_ramp = np.clip(density_curve ** 0.912, 0.0, 1.0)
    edge_melt = smoothstep(0.0, 0.22, coverage_soft) * smoothstep(0.015, 0.18, density_mix)
    shape_fade = np.clip(coverage_soft ** 1.436, 0.0, 1.0)
    tone_curve = np.clip(0.24 + (1.0 - 0.24) * density_ramp, 0.0, 1.0)
    continuous_field = np.clip(shape_fade * tone_curve * edge_melt, 0.0, 1.0)
    watercolor_field = np.clip(continuous_field ** 0.9304, 0.0, 1.0)
    mask_strength = watercolor_field * coverage * 0.92
    intensity_curve = intensity * intensity * (3.0 - 2.0 * intensity)
    material_alpha = CHEEK_OPACITY * (0.06 + (1.24 - 0.06) * intensity_curve)
    cheek_cap = 0.12 + (0.52 - 0.12) * np.clip(coverage, 0.0, 1.0)
    pigment_strength = np.minimum(
        np.clip(mask_strength * material_alpha * PRESERVE_SCALE, 0.0, 1.0),
        cheek_cap,
    )
    pigment_strength = np.clip(pigment_strength ** (1.08 + (0.88 - 1.08) * SATURATION_BOOST), 0.0, 1.0)
    pigment_strength *= 1.0 + (0.84 - 1.0) * SKIN_PRESERVE
    secondary = parse_hex_color(secondary_hex)
    blush_pigment = np.clip(ROSE * (1.0 - 0.04) + secondary * 0.04, 0.0, 1.0)
    pigment_warmth = np.clip(
        (blush_pigment[0] - max(blush_pigment[1], blush_pigment[2])) * 2.25
        + SATURATION_BOOST * 0.18,
        0.0,
        1.0,
    )
    filter_target = np.array(
        [
            1.0,
            (0.94 + (0.72 - 0.94) * pigment_warmth) - WARMTH * 0.020,
            (0.96 + (0.78 - 0.96) * pigment_warmth) - WARMTH * 0.024,
        ],
        dtype=np.float32,
    )
    filter_target = np.clip(np.maximum(filter_target, np.array([0.88, 0.72, 0.75])), 0.0, 1.0)
    skin_filter = 1.0 + (filter_target.reshape((1, 1, 3)) - 1.0) * pigment_strength[..., None]
    rendered = np.clip(
        base * skin_filter,
        0.0,
        1.0,
    )
    return Image.fromarray(np.rint(rendered * 255).astype(np.uint8), mode="RGB")


def source_mask_overlay(frame: Image.Image, mask_id: str) -> Image.Image:
    source_path = SOURCE_DRAWINGS.get(mask_id)
    if source_path is None or not source_path.exists():
        return frame.convert("RGB")
    source_rgba = Image.open(source_path).convert("RGBA")
    if mask_id == "cheek-sunkissed-mask2-v1" and source_rgba.size != frame.size:
        source_alpha = source_rgba.getchannel("A")
        alpha_values = np.asarray(source_alpha, dtype=np.float32)
        ys, xs = np.nonzero(alpha_values > 8.0)
        if len(xs) > 0:
            left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
            crop = source_alpha.crop((left, top, right + 1, bottom + 1))
            target_left, target_top, target_right, target_bottom = SUNKISSED2_PLACEMENT_BBOX
            crop = crop.resize(
                (target_right - target_left + 1, target_bottom - target_top + 1),
                Image.Resampling.LANCZOS,
            )
            placed = Image.new("L", frame.size, 0)
            placed.paste(crop, (target_left, target_top))
            return overlay_alpha(
                frame,
                np.asarray(placed, dtype=np.float32) / 255.0,
                (242, 112, 126),
            )

    source = source_rgba.convert("RGB")
    if source.size != frame.size:
        source_rgba = source_rgba.resize(frame.size, Image.Resampling.BILINEAR)
        source = source_rgba.convert("RGB")
    source_rgb = np.asarray(source, dtype=np.float32)
    source_alpha = np.asarray(source_rgba.getchannel("A"), dtype=np.float32) / 255.0
    luminance = (
        source_rgb[..., 0] * 0.2126
        + source_rgb[..., 1] * 0.7152
        + source_rgb[..., 2] * 0.0722
    )
    alpha = np.clip((245.0 - luminance) / 135.0, 0.0, 1.0)
    alpha = np.where(luminance < 238.0, alpha, 0.0)
    if float(alpha.max()) <= 0.0 and float(source_alpha.max()) > 0.0:
        alpha = source_alpha
    return overlay_alpha(frame, alpha, (242, 112, 126))


def crop_thumb(image: Image.Image, width: int = 320, height: int = 260) -> Image.Image:
    crop = image.crop(CROP_BOX)
    crop.thumbnail((width, height), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (width, height), (246, 246, 246))
    tile.paste(crop, ((width - crop.width) // 2, (height - crop.height) // 2))
    return tile


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    frame = Image.open(FRAME_PATH).convert("RGB")
    columns = ("source drawing", "projected alpha", "projected density", "expected render")
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
        "previewId": "cheek-blush-expected-render-20260627-skin-aware",
        "runtimeSelectionRule": "one cheek blush region mask is selected per cheek layer",
        "color": "#D94B74",
        "opacity": CHEEK_OPACITY,
        "materialAlphaRule": "opacity * lerp(0.06, 1.24, smoothstep(intensity))",
        "edgeContract": "coverage alpha stays wide/soft while density and coverage form one continuous watercolor field; cheek color is applied through skin-aware multiply tint",
        "blendContract": "cheek blush uses a density-gated multiply filter, not simple source-over alpha color",
        "coreEdgeContract": "visible blush uses one continuous density curve, avoiding separate strong and weak color layers",
        "densityContract": {
            "blush_daily": "outer/high cheekbone peak; fades inward toward nose and lower cheek",
            "blush_lovely": "round apple-center radial peak; fades outward evenly",
            "blush_sunkissed1": "outer cheek strongest; fades inward toward the nose; nose stays medium-light",
            "blush_sunkissed2": "outer cheekbone shy blush strongest; fades horizontally inward; nose bridge stays very light",
            "blush_under_eye": "under-eye band strongest near lower eyelid; fades gradually downward into cheek",
        },
        "frame": str(FRAME_PATH.relative_to(ROOT)),
        "rows": [],
    }

    for row, (label, sample_name, mask_id, coverage, secondary_hex, intensity) in enumerate(MASKS, start=1):
        mask_path = MASK_ROOT / f"{mask_id}.png"
        uv_mask = Image.open(mask_path).convert("RGBA")
        projected_alpha = project_uv_mask_to_screen(uv_mask, frame.size, "alpha")
        projected_density = project_uv_mask_to_screen(uv_mask, frame.size, "density")
        source = source_mask_overlay(frame, mask_id)
        alpha_overlay = overlay_alpha(frame, projected_alpha, (238, 111, 98))
        density_overlay = overlay_alpha(frame, projected_density, (196, 76, 110))
        expected = render_expected(
            frame,
            projected_alpha,
            projected_density,
            coverage,
            secondary_hex,
            intensity,
        )

        expected_path = OUTPUT_ROOT / f"expected_{mask_id}.png"
        alpha_path = OUTPUT_ROOT / f"projected_alpha_{mask_id}.png"
        density_path = OUTPUT_ROOT / f"projected_density_{mask_id}.png"
        expected.save(expected_path)
        Image.fromarray(np.rint(np.clip(projected_alpha, 0.0, 1.0) * 255).astype(np.uint8), mode="L").save(alpha_path)
        Image.fromarray(np.rint(np.clip(projected_density, 0.0, 1.0) * 255).astype(np.uint8), mode="L").save(density_path)

        y = row * (tile_h + label_h)
        draw.text((8, y + 8), f"{label} / {sample_name}", fill=(0, 0, 0))
        for col, image in enumerate((source, alpha_overlay, density_overlay, expected)):
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
                "materialAlphaApprox": CHEEK_OPACITY
                * (0.06 + (1.24 - 0.06) * (intensity * intensity * (3.0 - 2.0 * intensity))),
                "projectedAlphaActivePixelsGt003": int(active.sum()),
                "expectedRender": str(expected_path.relative_to(ROOT)),
                "projectedAlpha": str(alpha_path.relative_to(ROOT)),
                "projectedDensity": str(density_path.relative_to(ROOT)),
            }
        )

    sheet_path = OUTPUT_ROOT / "cheek_blush_expected_render_sheet.png"
    sheet.save(sheet_path)
    summary["sheet"] = str(sheet_path.relative_to(ROOT))

    ramp_levels = (0.15, 0.55, 1.0)
    ramp_sheet = Image.new(
        "RGB",
        (tile_w * len(ramp_levels), (tile_h + label_h) * (len(MASKS) + 1)),
        (245, 245, 245),
    )
    ramp_draw = ImageDraw.Draw(ramp_sheet)
    for col, level in enumerate(ramp_levels):
        ramp_draw.text((col * tile_w + 8, 9), f"intensity {level:.2f}", fill=(0, 0, 0))

    for row, (label, sample_name, mask_id, coverage, secondary_hex, _intensity) in enumerate(MASKS, start=1):
        mask_path = MASK_ROOT / f"{mask_id}.png"
        uv_mask = Image.open(mask_path).convert("RGBA")
        projected_alpha = project_uv_mask_to_screen(uv_mask, frame.size, "alpha")
        projected_density = project_uv_mask_to_screen(uv_mask, frame.size, "density")
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
