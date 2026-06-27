#!/usr/bin/env python3
"""Create a forced-color cheek blush diagnostic sheet."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from make_cheek_blush_expected_preview import (
    EVIDENCE_ROOT,
    FRAME_PATH,
    MASKS,
    OUTPUT_ROOT,
    ROOT,
    crop_thumb,
    source_mask_overlay,
)


def load_field(path: Path, frame_size: tuple[int, int]) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != frame_size:
        image = image.resize(frame_size, Image.Resampling.BILINEAR)
    return np.asarray(image, dtype=np.float32) / 255.0


def smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - edge0) / max(edge1 - edge0, 1.0e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def forced_overlay(frame: Image.Image, field: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    base = frame.convert("RGBA")
    forced = smoothstep(0.018, 0.22, field)
    forced = Image.fromarray(np.rint(np.clip(forced, 0.0, 1.0) * 218).astype(np.uint8), mode="L")
    forced = forced.filter(ImageFilter.GaussianBlur(radius=0.6))
    overlay = Image.new("RGBA", frame.size, (*color, 0))
    overlay.putalpha(forced)
    return Image.alpha_composite(base, overlay).convert("RGB")


def changed_pixels(frame: Image.Image, render: Image.Image) -> int:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    result = np.asarray(render.convert("RGB"), dtype=np.float32)
    diff = np.max(np.abs(result - base), axis=2) / 255.0
    return int((diff > 0.006).sum())


def main() -> None:
    frame = Image.open(FRAME_PATH).convert("RGB")
    summary_path = OUTPUT_ROOT / "summary.json"
    expected_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows_by_mask = {
        str(row["maskTextureId"]): row
        for row in expected_summary["rows"]
        if isinstance(row, dict)
    }

    columns = (
        "source drawing",
        "forced alpha region",
        "forced B-density",
        "normal render",
        "verdict",
    )
    tile_w, tile_h, label_h = 330, 260, 44
    sheet = Image.new(
        "RGB",
        (tile_w * len(columns), (tile_h + label_h) * (len(MASKS) + 1)),
        (246, 246, 246),
    )
    draw = ImageDraw.Draw(sheet)
    for col, label in enumerate(columns):
        draw.text((col * tile_w + 8, 10), label, fill=(0, 0, 0))

    diagnostics: list[dict[str, object]] = []
    for row_index, (label, sample_name, mask_id, _, _) in enumerate(MASKS, start=1):
        expected_row = rows_by_mask[mask_id]
        alpha = load_field(ROOT / expected_row["projectedAlpha"], frame.size)
        density = load_field(ROOT / expected_row["projectedDensity"], frame.size)
        normal = Image.open(ROOT / expected_row["expectedRender"]).convert("RGB")
        source = source_mask_overlay(frame, mask_id)
        forced_alpha = forced_overlay(frame, alpha, (255, 36, 92))
        forced_density = forced_overlay(frame, density, (202, 42, 150))

        alpha_pixels = int((alpha > 0.03).sum())
        density_pixels = int((density > 0.03).sum())
        normal_pixels = changed_pixels(frame, normal)
        density_ratio = density_pixels / max(alpha_pixels, 1)
        normal_ratio = normal_pixels / max(alpha_pixels, 1)
        if density_ratio < 0.75:
            verdict = "region ok / density guide too small"
        elif normal_ratio < 0.62:
            verdict = "region ok / pigment too weak"
        else:
            verdict = "gpu multiply body visible / edge guided"

        diagnostics.append(
            {
                "label": label,
                "textureSample": sample_name,
                "maskTextureId": mask_id,
                "alphaPixelsGt003": alpha_pixels,
                "densityPixelsGt003": density_pixels,
                "densityToAlphaRatio": round(density_ratio, 4),
                "normalChangedPixelsGt006": normal_pixels,
                "normalChangedToAlphaRatio": round(normal_ratio, 4),
                "verdict": verdict,
            }
        )

        y = row_index * (tile_h + label_h)
        draw.text((8, y + 8), f"{label} / {sample_name}", fill=(0, 0, 0))
        verdict_tile = Image.new("RGB", (tile_w, tile_h), (255, 255, 255))
        verdict_draw = ImageDraw.Draw(verdict_tile)
        verdict_draw.text((12, 18), verdict, fill=(0, 0, 0))
        verdict_draw.text((12, 56), f"density/alpha {density_ratio:.2f}", fill=(0, 0, 0))
        verdict_draw.text((12, 88), f"render/alpha {normal_ratio:.2f}", fill=(0, 0, 0))
        images = (source, forced_alpha, forced_density, normal, verdict_tile)
        for col, image in enumerate(images):
            tile = image if col == len(images) - 1 else crop_thumb(image, tile_w, tile_h)
            sheet.paste(tile, (col * tile_w, y + label_h))

    output_path = OUTPUT_ROOT / "cheek_blush_region_vs_pigment_diagnostic.png"
    json_path = OUTPUT_ROOT / "cheek_blush_region_vs_pigment_diagnostic.json"
    sheet.save(output_path)
    json_path.write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "sheet": str(output_path.relative_to(ROOT)),
                "diagnostics": diagnostics,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
