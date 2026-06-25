#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_ATLAS_MASK = Path("evidence/e7-reference-atlas/lip-style-atlas-v1/lip_atlas_roundtrip_mask.png")
DEFAULT_VISION_MASK = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/frame_vision_outer_minus_inner_mask.png")
DEFAULT_OUT = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/blend_preview")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create alpha overlay vs pigment multiply lip previews.")
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--atlas-mask", type=Path, default=DEFAULT_ATLAS_MASK)
    parser.add_argument("--vision-mask", type=Path, default=DEFAULT_VISION_MASK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--color", default="#D94B74")
    parser.add_argument("--alpha-opacity", type=float, default=0.62)
    parser.add_argument("--multiply-strength", type=float, default=0.76)
    parser.add_argument("--feather", type=float, default=3.0)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--crop-pad", type=int, default=220)
    return parser.parse_args()


def hex_to_rgb(value: str) -> np.ndarray:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB color, got {value!r}")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32) / 255.0


def load_mask(path: Path, size: tuple[int, int], threshold: int, feather: float) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    if feather > 0:
        image = image.filter(ImageFilter.GaussianBlur(radius=feather))
    values = np.asarray(image, dtype=np.float32) / 255.0
    return np.where(values > threshold / 255.0, values, 0.0)


def bbox(mask: np.ndarray) -> dict[str, int] | None:
    ys, xs = np.where(mask > 0.03)
    if len(xs) == 0:
        return None
    left = int(xs.min())
    top = int(ys.min())
    right = int(xs.max())
    bottom = int(ys.max())
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left + 1,
        "height": bottom - top + 1,
    }


def expand_bbox(box: dict[str, int], size: tuple[int, int], pad: int) -> tuple[int, int, int, int]:
    width, height = size
    left = max(0, box["left"] - pad)
    top = max(0, box["top"] - pad)
    right = min(width - 1, box["right"] + pad)
    bottom = min(height - 1, box["bottom"] + pad)
    return left, top, right + 1, bottom + 1


def alpha_overlay(frame: np.ndarray, mask: np.ndarray, color: np.ndarray, opacity: float) -> np.ndarray:
    alpha = np.clip(mask * opacity, 0.0, 1.0)[..., None]
    return frame * (1.0 - alpha) + color * alpha


def pigment_multiply(frame: np.ndarray, mask: np.ndarray, color: np.ndarray, strength: float) -> np.ndarray:
    pigment_strength = np.clip(mask * strength, 0.0, 1.0)[..., None]
    pigment_filter = 1.0 * (1.0 - pigment_strength) + color * pigment_strength
    return np.clip(frame * pigment_filter, 0.0, 1.0)


def add_boundary(image: Image.Image, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    hard = mask > 0.04
    edge = np.zeros_like(hard)
    edge[1:, :] |= hard[1:, :] != hard[:-1, :]
    edge[:-1, :] |= hard[:-1, :] != hard[1:, :]
    edge[:, 1:] |= hard[:, 1:] != hard[:, :-1]
    edge[:, :-1] |= hard[:, :-1] != hard[:, 1:]
    edge_image = Image.fromarray((edge.astype(np.uint8) * 255), mode="L").filter(ImageFilter.MaxFilter(5))
    output = image.convert("RGBA")
    line = Image.new("RGBA", output.size, (*color, 0))
    line.putalpha(edge_image)
    return Image.alpha_composite(output, line).convert("RGB")


def luminance(values: np.ndarray) -> np.ndarray:
    return values[..., 0] * 0.2126 + values[..., 1] * 0.7152 + values[..., 2] * 0.0722


def detail_metrics(original: np.ndarray, rendered: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    active = mask > 0.12
    if int(active.sum()) < 2:
        return {"lumaStdRatio": 0.0, "lumaCorrelation": 0.0}
    original_luma = luminance(original)[active]
    rendered_luma = luminance(rendered)[active]
    original_std = float(original_luma.std())
    rendered_std = float(rendered_luma.std())
    if original_std <= 1e-8 or rendered_std <= 1e-8:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(original_luma, rendered_luma)[0, 1])
    return {
        "lumaStdRatio": rendered_std / max(original_std, 1e-8),
        "lumaCorrelation": correlation,
    }


def label(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    output = image.convert("RGBA")
    draw = ImageDraw.Draw(output)
    height = 92 if subtitle else 64
    draw.rectangle((24, 24, 720, 24 + height), fill=(0, 0, 0, 168))
    draw.text((42, 42), title, fill=(255, 255, 255, 255))
    if subtitle:
        draw.text((42, 70), subtitle, fill=(255, 255, 255, 255))
    return output.convert("RGB")


def make_sheet(images: list[tuple[str, Image.Image]], crop: tuple[int, int, int, int]) -> Image.Image:
    thumbs: list[tuple[str, Image.Image]] = []
    for title, image in images:
        view = image.crop(crop)
        view.thumbnail((360, 640), Image.Resampling.LANCZOS)
        thumbs.append((title, view.convert("RGB")))

    label_height = 34
    width = 360 * len(thumbs)
    height = label_height + max(image.height for _, image in thumbs)
    sheet = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    for index, (title, image) in enumerate(thumbs):
        x = index * 360
        draw.rectangle((x, 0, x + 360, label_height), fill=(35, 35, 39))
        draw.text((x + 12, 10), title, fill=(255, 255, 255))
        sheet.paste(image, (x + (360 - image.width) // 2, label_height))
    return sheet


def save_preview(path: Path, values: np.ndarray, mask: np.ndarray, line_color: tuple[int, int, int], title: str, subtitle: str) -> Image.Image:
    image = Image.fromarray(np.rint(np.clip(values, 0.0, 1.0) * 255).astype(np.uint8), mode="RGB")
    image = add_boundary(image, mask, line_color)
    image = label(image, title, subtitle)
    image.save(path)
    return image


def main() -> None:
    args = parse_args()
    frame_path = args.frame.resolve()
    atlas_mask_path = args.atlas_mask.resolve()
    vision_mask_path = args.vision_mask.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_image = Image.open(frame_path).convert("RGB")
    frame = np.asarray(frame_image, dtype=np.float32) / 255.0
    color = hex_to_rgb(args.color)
    atlas_mask = load_mask(atlas_mask_path, frame_image.size, args.threshold, args.feather)
    vision_mask = load_mask(vision_mask_path, frame_image.size, args.threshold, args.feather)

    union_box = bbox(np.maximum(atlas_mask, vision_mask))
    if union_box is None:
        raise SystemExit("No active lip pixels in atlas or Vision mask.")
    crop = expand_bbox(union_box, frame_image.size, args.crop_pad)

    atlas_alpha = alpha_overlay(frame, atlas_mask, color, args.alpha_opacity)
    atlas_multiply = pigment_multiply(frame, atlas_mask, color, args.multiply_strength)
    vision_multiply = pigment_multiply(frame, vision_mask, color, args.multiply_strength)

    original_path = out_dir / "original_crop_context.png"
    alpha_path = out_dir / "current_alpha_overlay_atlas.png"
    multiply_atlas_path = out_dir / "pigment_multiply_atlas.png"
    multiply_vision_path = out_dir / "pigment_multiply_vision_v2.png"

    original = label(frame_image, "original clean frame", "no makeup preview")
    original.save(original_path)
    alpha_image = save_preview(
        alpha_path,
        atlas_alpha,
        atlas_mask,
        (255, 74, 132),
        "current alpha overlay / atlas",
        "baseline sticker-risk preview",
    )
    multiply_atlas_image = save_preview(
        multiply_atlas_path,
        atlas_multiply,
        atlas_mask,
        (255, 74, 132),
        "pigment multiply / atlas",
        "same mask; texture should remain visible",
    )
    multiply_vision_image = save_preview(
        multiply_vision_path,
        vision_multiply,
        vision_mask,
        (0, 255, 232),
        "pigment multiply / Vision v2",
        "boundary candidate; not runtime approval",
    )

    sheet_path = out_dir / "alpha_vs_pigment_multiply_sheet.png"
    sheet = make_sheet(
        [
            ("original", original),
            ("alpha atlas", alpha_image),
            ("multiply atlas", multiply_atlas_image),
            ("multiply Vision", multiply_vision_image),
        ],
        crop,
    )
    sheet.save(sheet_path)

    summary: dict[str, Any] = {
        "status": "offline_preview_only",
        "frame": str(frame_path),
        "atlasMask": str(atlas_mask_path),
        "visionMask": str(vision_mask_path),
        "color": args.color,
        "alphaOpacity": args.alpha_opacity,
        "multiplyStrength": args.multiply_strength,
        "feather": args.feather,
        "crop": {
            "left": crop[0],
            "top": crop[1],
            "right": crop[2],
            "bottom": crop[3],
            "width": crop[2] - crop[0],
            "height": crop[3] - crop[1],
        },
        "sheet": str(sheet_path),
        "previews": {
            "original": str(original_path),
            "alphaAtlas": str(alpha_path),
            "multiplyAtlas": str(multiply_atlas_path),
            "multiplyVision": str(multiply_vision_path),
        },
        "detailMetrics": {
            "alphaAtlas": detail_metrics(frame, atlas_alpha, atlas_mask),
            "multiplyAtlas": detail_metrics(frame, atlas_multiply, atlas_mask),
            "multiplyVision": detail_metrics(frame, vision_multiply, vision_mask),
        },
        "note": "Offline visual approximation only. It does not replace Unity runtime rendering or real-device acceptance.",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Lip Blend Preview",
        "",
        "- Status: `offline_preview_only`",
        f"- Sheet: `{sheet_path}`",
        f"- Color: `{args.color}`",
        f"- Alpha opacity: `{args.alpha_opacity:.2f}`",
        f"- Multiply strength: `{args.multiply_strength:.2f}`",
        "",
        "Detail metrics are measured over the active lip mask on the clean frame.",
        "",
        f"- Alpha atlas luma std ratio: `{summary['detailMetrics']['alphaAtlas']['lumaStdRatio']:.6f}`",
        f"- Multiply atlas luma std ratio: `{summary['detailMetrics']['multiplyAtlas']['lumaStdRatio']:.6f}`",
        f"- Multiply Vision luma std ratio: `{summary['detailMetrics']['multiplyVision']['lumaStdRatio']:.6f}`",
        "",
        "This is buildless preview evidence only; runtime Unity acceptance is still required.",
    ]
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"lip_blend_preview status=offline_preview_only sheet={sheet_path}")


if __name__ == "__main__":
    main()
