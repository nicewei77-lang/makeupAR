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
OUTPUT_ROOT = EVIDENCE_ROOT / "expected_render_20260628_natural_v5"

MASKS = (
    ("Daily", "blush_daily", "cheek-daily-mask-v1", 0.84, "#F2A59A"),
    ("Lovely", "blush_lovely", "cheek-lovely-mask-v1", 0.90, "#F3A1A6"),
    ("Sun 1", "blush_sunkissed1", "cheek-sunkissed-mask1-v1", 0.78, "#EFA07F"),
    ("Sun 2", "blush_sunkissed2", "cheek-sunkissed-mask2-v1", 0.72, "#EAA07A"),
    ("Under", "blush_under_eye", "cheek-under-eye-mask-v1", 0.68, "#F0A0B0"),
)
SOURCE_DRAWINGS = {
    "cheek-daily-mask-v1": Path("/Users/yeoduchi/Downloads/cheek_daily_mask.png"),
    "cheek-lovely-mask-v1": Path("/Users/yeoduchi/Downloads/cheek_lovely_mask.png"),
    "cheek-sunkissed-mask1-v1": Path("/Users/yeoduchi/Downloads/cheek_sunkissed_mask1.png"),
    "cheek-sunkissed-mask2-v1": Path("/Users/yeoduchi/Downloads/cheek_sunkissed_mask2.png"),
    "cheek-under-eye-mask-v1": Path("/Users/yeoduchi/Downloads/under_eye_mask.png"),
}

ROSE = np.array([0xD9, 0x4B, 0x74], dtype=np.float32) / 255.0
CHEEK_SKIN_TINT = np.array([1.0, 1.0, 1.0], dtype=np.float32)
CHEEK_OPACITY = 0.52
CHEEK_INTENSITY = 0.95
PRESERVE_SCALE = 0.92
MATERIAL_ALPHA = CHEEK_OPACITY * (0.24 + (0.54 - 0.24) * CHEEK_INTENSITY)
CROP_BOX = (110, 710, 1060, 1460)


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
    full_soft = smoothstep(0.025 - 0.64 * 0.46, 0.025 + 0.64, soft)
    full_core = smoothstep(0.025 + 0.64 * 0.18, 0.025 + 0.64 * 0.88, soft)
    edge_band = np.clip(full_soft - full_core, 0.0, 1.0)
    outer_ramp = smoothstep(0.12, 0.72, full_soft)
    mid_ramp = smoothstep(0.20, 0.76, density_soft)
    core_ramp = smoothstep(0.42, 0.88, density_soft)
    outer_layer = np.clip(outer_ramp * (0.018 + mid_ramp * 0.040), 0.0, 1.0)
    mid_layer = np.clip(mid_ramp * smoothstep(0.18, 0.70, full_soft), 0.0, 1.0)
    core_layer = np.clip((core_ramp * (0.62 + (1.0 - 0.62) * full_core)) ** 1.04, 0.0, 1.0)
    skin_fade = np.clip(
        outer_layer * 0.0
        + mid_layer * 0.22
        + core_layer * 0.96,
        0.0,
        1.0,
    )
    mask_strength = (
        outer_layer * coverage * 0.004
        + mid_layer * coverage * 0.18
        + core_layer * coverage * 0.56
    )
    color_luma = float(np.dot(ROSE, np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)))
    light_color_boost = float(smoothstep(0.66, 0.88, np.asarray(color_luma, dtype=np.float32)))
    max_pigment_strength = (
        0.28
        + (0.46 - 0.28) * np.clip(coverage, 0.0, 1.0)
        + light_color_boost * 0.08
    )
    pigment_strength = np.clip(
        mask_strength * MATERIAL_ALPHA * PRESERVE_SCALE,
        0.0,
        max_pigment_strength,
    )
    secondary = parse_hex_color(secondary_hex)
    visible_primary = np.clip(
        ROSE * (1.0 - 0.24 * light_color_boost)
        + np.array([0.018, 0.0, 0.012], dtype=np.float32) * light_color_boost,
        0.0,
        1.0,
    )
    blush_pigment = np.clip(visible_primary * 0.90 + secondary * 0.10, 0.0, 1.0)
    pigment_color = (
        CHEEK_SKIN_TINT.reshape((1, 1, 3)) * (1.0 - skin_fade[..., None])
        + blush_pigment.reshape((1, 1, 3)) * skin_fade[..., None]
    )
    pigment_filter = 1.0 + (pigment_color - 1.0) * pigment_strength[..., None]
    rendered = np.clip(base * pigment_filter, 0.0, 1.0)
    return Image.fromarray(np.rint(rendered * 255).astype(np.uint8), mode="RGB")


def source_mask_overlay(frame: Image.Image, mask_id: str) -> Image.Image:
    generated_path = EVIDENCE_ROOT / "screen" / f"{mask_id}-source-clean.png"
    if generated_path.exists():
        source = Image.open(generated_path).convert("L")
        if source.size != frame.size:
            source = source.resize(frame.size, Image.Resampling.BILINEAR)
        alpha = np.asarray(source, dtype=np.float32) / 255.0
        return overlay_alpha(frame, alpha, (242, 112, 126))

    source_path = SOURCE_DRAWINGS.get(mask_id)
    if source_path is None or not source_path.exists():
        return frame.convert("RGB")
    source = Image.open(source_path).convert("RGB")
    if source.size != frame.size:
        source = source.resize(frame.size, Image.Resampling.BILINEAR)
    source_rgb = np.asarray(source, dtype=np.float32)
    luminance = (
        source_rgb[..., 0] * 0.2126
        + source_rgb[..., 1] * 0.7152
        + source_rgb[..., 2] * 0.0722
    )
    alpha = np.clip((245.0 - luminance) / 135.0, 0.0, 1.0)
    alpha = np.where(luminance < 238.0, alpha, 0.0)
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
    columns = ("generated source", "projected alpha", "projected density", "expected render")
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
        "previewId": "cheek-blush-expected-render-20260628-natural-v5",
        "runtimeSelectionRule": "one cheek blush region mask is selected per cheek layer; each cheek mask encodes outer/mid/core gradient layers",
        "color": "#D94B74",
        "addedColor": "#F0CBD5",
        "opacity": CHEEK_OPACITY,
        "intensity": CHEEK_INTENSITY,
        "materialAlphaApprox": MATERIAL_ALPHA,
        "edgeContract": "cheek blush outer alpha stays wide for attachment, but visible pigment is density-gated inward and resolves toward unchanged camera skin",
        "layerContract": "outer invisible safety wash + mid veil + core pigment are blended from one selected cheek mask",
        "colorContract": "bright cheek colors are automatically darkened just enough for validation visibility while saturated colors keep their selected hue",
        "densityContract": {
            "blush_daily": "expanded outer/high cheekbone wash with mid veil and core peak",
            "blush_lovely": "expanded round apple-center wash with mid veil and core peak",
            "blush_sunkissed1": "horizontally filled round cheek blobs with visible nose blush",
            "blush_sunkissed2": "expanded W wash with cheekbone ends strongest and nose bridge low",
            "blush_under_eye": "starts directly below the lower eye area, then fades down into high cheek",
        },
        "frame": str(FRAME_PATH.relative_to(ROOT)),
        "rows": [],
    }

    for row, (label, sample_name, mask_id, coverage, secondary_hex) in enumerate(MASKS, start=1):
        mask_path = MASK_ROOT / f"{mask_id}.png"
        uv_mask = Image.open(mask_path).convert("RGBA")
        projected_alpha = project_uv_mask_to_screen(uv_mask, frame.size, "alpha")
        projected_density = project_uv_mask_to_screen(uv_mask, frame.size, "density")
        source = source_mask_overlay(frame, mask_id)
        alpha_overlay = overlay_alpha(frame, projected_alpha, (238, 111, 98))
        density_overlay = overlay_alpha(frame, projected_density, (196, 76, 110))
        expected = render_expected(frame, projected_alpha, projected_density, coverage, secondary_hex)

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
                "projectedAlphaActivePixelsGt003": int(active.sum()),
                "expectedRender": str(expected_path.relative_to(ROOT)),
                "projectedAlpha": str(alpha_path.relative_to(ROOT)),
                "projectedDensity": str(density_path.relative_to(ROOT)),
            }
        )

    sheet_path = OUTPUT_ROOT / "cheek_blush_expected_render_sheet.png"
    sheet.save(sheet_path)
    summary["sheet"] = str(sheet_path.relative_to(ROOT))
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
