#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_ATLAS_MASK = Path("evidence/e7-reference-atlas/lip-style-atlas-v1/lip_atlas_roundtrip_mask.png")
DEFAULT_VISION_MASK = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/frame_vision_outer_minus_inner_mask.png")
DEFAULT_OUT = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/boundary_compare")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare current lip atlas and Apple Vision lip boundary masks.")
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--atlas-mask", type=Path, default=DEFAULT_ATLAS_MASK)
    parser.add_argument("--vision-mask", type=Path, default=DEFAULT_VISION_MASK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--crop-pad", type=int, default=220)
    return parser.parse_args()


def load_mask(path: Path, size: tuple[int, int], threshold: int) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image, dtype=np.uint8) > threshold


def bbox(mask: np.ndarray) -> dict[str, int] | None:
    ys, xs = np.where(mask)
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


def boundary(mask: np.ndarray) -> np.ndarray:
    up = np.zeros_like(mask)
    down = np.zeros_like(mask)
    left = np.zeros_like(mask)
    right = np.zeros_like(mask)
    up[1:, :] = mask[:-1, :]
    down[:-1, :] = mask[1:, :]
    left[:, 1:] = mask[:, :-1]
    right[:, :-1] = mask[:, 1:]
    return mask & ~(up & down & left & right)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    output = np.zeros_like(mask)
    padded = np.pad(mask, radius, mode="constant", constant_values=False)
    for dy in range(0, radius * 2 + 1):
        for dx in range(0, radius * 2 + 1):
            output |= padded[dy : dy + mask.shape[0], dx : dx + mask.shape[1]]
    return output


def overlay_mask(
    frame: Image.Image,
    mask: np.ndarray,
    fill_color: tuple[int, int, int],
    line_color: tuple[int, int, int],
    title: str,
) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    fill = np.array(fill_color, dtype=np.float32)
    active = mask
    base[active] = base[active] * 0.58 + fill * 0.42

    edge = dilate(boundary(mask), radius=2)
    base[edge] = np.array(line_color, dtype=np.float32)

    output = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")
    draw = ImageDraw.Draw(output)
    draw.rectangle((24, 24, 560, 92), fill=(0, 0, 0, 168))
    draw.text((42, 42), title, fill=(255, 255, 255, 255))
    return output.convert("RGB")


def difference_overlay(frame: Image.Image, atlas: np.ndarray, vision: np.ndarray) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    overlap = atlas & vision
    atlas_only = atlas & ~vision
    vision_only = vision & ~atlas
    base[overlap] = base[overlap] * 0.45 + np.array([90, 245, 120], dtype=np.float32) * 0.55
    base[atlas_only] = base[atlas_only] * 0.45 + np.array([80, 140, 255], dtype=np.float32) * 0.55
    base[vision_only] = base[vision_only] * 0.45 + np.array([255, 80, 92], dtype=np.float32) * 0.55
    output = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), mode="RGB").convert("RGBA")
    draw = ImageDraw.Draw(output)
    draw.rectangle((24, 24, 760, 116), fill=(0, 0, 0, 168))
    draw.text((42, 42), "green=overlap / blue=atlas only / red=Vision only", fill=(255, 255, 255, 255))
    draw.text((42, 72), "Boundary comparison only; not makeup acceptance", fill=(255, 255, 255, 255))
    return output.convert("RGB")


def make_sheet(images: list[tuple[str, Image.Image]], crop: tuple[int, int, int, int] | None = None) -> Image.Image:
    thumbs: list[tuple[str, Image.Image]] = []
    for title, image in images:
        view = image.crop(crop) if crop is not None else image.copy()
        view.thumbnail((420, 760), Image.Resampling.LANCZOS)
        thumbs.append((title, view.convert("RGB")))

    label_height = 34
    width = 420 * len(thumbs)
    height = label_height + max(image.height for _, image in thumbs)
    sheet = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    for index, (title, image) in enumerate(thumbs):
        x = index * 420
        draw.rectangle((x, 0, x + 420, label_height), fill=(35, 35, 39))
        draw.text((x + 14, 10), title, fill=(255, 255, 255))
        sheet.paste(image, (x + (420 - image.width) // 2, label_height))
    return sheet


def mask_stats(mask: np.ndarray) -> dict[str, Any]:
    return {
        "pixels": int(mask.sum()),
        "coverage": float(mask.sum() / max(mask.size, 1)),
        "bbox": bbox(mask),
    }


def comparison_stats(atlas: np.ndarray, vision: np.ndarray) -> dict[str, Any]:
    intersection = atlas & vision
    union = atlas | vision
    vision_only = vision & ~atlas
    atlas_only = atlas & ~vision
    return {
        "iou": float(intersection.sum() / max(union.sum(), 1)),
        "visionOutsideAtlasRatio": float(vision_only.sum() / max(vision.sum(), 1)),
        "atlasMissingInVisionRatio": float(atlas_only.sum() / max(atlas.sum(), 1)),
        "overlapPixels": int(intersection.sum()),
        "visionOnlyPixels": int(vision_only.sum()),
        "atlasOnlyPixels": int(atlas_only.sum()),
    }


def write_summary(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Lip Boundary Compare",
        "",
        f"- Status: `{summary['status']}`",
        f"- Frame: `{summary['frame']}`",
        f"- Atlas mask: `{summary['atlasMask']}`",
        f"- Vision mask: `{summary['visionMask']}`",
        f"- Full sheet: `{summary['fullSheet']}`",
        f"- Mouth crop sheet: `{summary['mouthCropSheet']}`",
        "",
        "Metrics are comparison-only because the current atlas is a baseline candidate, not a pixel-perfect gold mask.",
        "",
        f"- IoU atlas vs Vision: `{summary['comparison']['iou']:.6f}`",
        f"- Vision outside atlas ratio: `{summary['comparison']['visionOutsideAtlasRatio']:.6f}`",
        f"- Atlas missing in Vision ratio: `{summary['comparison']['atlasMissingInVisionRatio']:.6f}`",
        "",
        "Manual boundary review focus:",
        "",
        "- mouth corners included",
        "- cupid bow not inverted/displaced",
        "- lower lip not shifted onto chin skin",
        "- inner mouth/teeth excluded",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    frame_path = args.frame.resolve()
    atlas_mask_path = args.atlas_mask.resolve()
    vision_mask_path = args.vision_mask.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame = Image.open(frame_path).convert("RGB")
    atlas = load_mask(atlas_mask_path, frame.size, args.threshold)
    vision = load_mask(vision_mask_path, frame.size, args.threshold)
    union_box = bbox(atlas | vision)
    if union_box is None:
        raise SystemExit("No active pixels in atlas or Vision mask.")
    crop = expand_bbox(union_box, frame.size, args.crop_pad)

    atlas_overlay = overlay_mask(
        frame,
        atlas,
        fill_color=(217, 75, 116),
        line_color=(255, 56, 122),
        title="current atlas boundary",
    )
    vision_overlay = overlay_mask(
        frame,
        vision,
        fill_color=(0, 208, 196),
        line_color=(0, 255, 232),
        title="Apple Vision v2 boundary",
    )
    diff_overlay = difference_overlay(frame, atlas, vision)

    overlays = [
        ("current atlas", atlas_overlay),
        ("Vision v2", vision_overlay),
        ("difference", diff_overlay),
    ]
    full_sheet = out_dir / "atlas_vs_vision_boundary_full.png"
    crop_sheet = out_dir / "atlas_vs_vision_boundary_mouth_crop.png"
    make_sheet(overlays).save(full_sheet)
    make_sheet(overlays, crop=crop).save(crop_sheet)

    summary = {
        "status": "pending_manual_review",
        "frame": str(frame_path),
        "atlasMask": str(atlas_mask_path),
        "visionMask": str(vision_mask_path),
        "threshold": args.threshold,
        "crop": {
            "left": crop[0],
            "top": crop[1],
            "right": crop[2],
            "bottom": crop[3],
            "width": crop[2] - crop[0],
            "height": crop[3] - crop[1],
        },
        "fullSheet": str(full_sheet),
        "mouthCropSheet": str(crop_sheet),
        "atlas": mask_stats(atlas),
        "vision": mask_stats(vision),
        "comparison": comparison_stats(atlas, vision),
        "note": "Comparison-only boundary evidence; not runtime Vision integration and not makeup rendering acceptance.",
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_summary(out_dir / "summary.md", summary)
    print(f"lip_boundary_compare status=pending_manual_review cropSheet={crop_sheet}")


if __name__ == "__main__":
    main()
