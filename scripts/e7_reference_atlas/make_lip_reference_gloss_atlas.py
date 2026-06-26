#!/usr/bin/env python3
"""Build a candidate gloss A-channel from a provided glossy lip reference.

The extracted white pixels are used as a gloss mask guide, not as a literal
white sticker. The output atlas keeps the existing RGB lip channels and writes
the reference-derived highlight into alpha for buildless expected-render review.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_ATLAS = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "lip-drawn-style-atlas-v1.png"
)
DEFAULT_OUT_DIR = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/"
    "reference_gloss_extract_20260626"
)
DEFAULT_CROP = (78, 270, 572, 425)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract reference gloss and warp it to the lip atlas A-channel.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--atlas", type=Path, default=DEFAULT_ATLAS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--crop", type=str, default=",".join(str(v) for v in DEFAULT_CROP))
    parser.add_argument("--target-x0", type=float, default=0.15)
    parser.add_argument("--target-x1", type=float, default=0.88)
    parser.add_argument("--target-y0", type=float, default=0.56)
    parser.add_argument("--target-y1", type=float, default=0.84)
    parser.add_argument("--right-glint-strength", type=float, default=0.0)
    parser.add_argument("--right-glint-x", type=float, default=0.72)
    parser.add_argument("--right-glint-y", type=float, default=0.79)
    parser.add_argument("--right-glint-width", type=float, default=0.030)
    parser.add_argument("--right-glint-height", type=float, default=0.016)
    parser.add_argument(
        "--extra-glint",
        action="append",
        default=[],
        metavar="X,Y,W,H,STRENGTH",
        help="Additional atlas-relative lower-lip glint. Can be passed more than once.",
    )
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def parse_crop(value: str) -> tuple[int, int, int, int]:
    parts = [int(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("--crop must be left,top,right,bottom")
    left, top, right, bottom = parts
    if left >= right or top >= bottom:
        raise ValueError(f"Invalid crop: {value}")
    return left, top, right, bottom


def active_bbox(active: np.ndarray) -> dict[str, int] | None:
    ys, xs = np.where(active)
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


def component_boxes(active: np.ndarray) -> list[dict[str, Any]]:
    seen = np.zeros_like(active, dtype=bool)
    boxes: list[dict[str, Any]] = []
    height, width = active.shape
    for start_y, start_x in np.argwhere(active):
        y = int(start_y)
        x = int(start_x)
        if seen[y, x]:
            continue
        points: list[tuple[int, int]] = []
        queue: deque[tuple[int, int]] = deque([(y, x)])
        seen[y, x] = True
        while queue:
            cy, cx = queue.popleft()
            points.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny = cy + dy
                    nx = cx + dx
                    if 0 <= ny < height and 0 <= nx < width and active[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        ys = np.asarray([point[0] for point in points])
        xs = np.asarray([point[1] for point in points])
        boxes.append(
            {
                "area": int(len(points)),
                "bbox": {
                    "left": int(xs.min()),
                    "top": int(ys.min()),
                    "right": int(xs.max()),
                    "bottom": int(ys.max()),
                    "width": int(xs.max() - xs.min() + 1),
                    "height": int(ys.max() - ys.min() + 1),
                },
                "center": [float((xs.min() + xs.max()) * 0.5), float((ys.min() + ys.max()) * 0.5)],
            }
        )
    return boxes


def extract_reference_mask(reference: Image.Image, crop_box: tuple[int, int, int, int]) -> tuple[Image.Image, Image.Image, Image.Image, list[dict[str, Any]]]:
    crop = reference.convert("RGB").crop(crop_box)
    values = np.asarray(crop, dtype=np.float32)
    max_channel = values.max(axis=2)
    min_channel = values.min(axis=2)
    luma = values[:, :, 0] * 0.2126 + values[:, :, 1] * 0.7152 + values[:, :, 2] * 0.0722
    saturation = (max_channel - min_channel) / np.maximum(max_channel, 1.0)

    white = np.clip((luma - 188.0) / 52.0, 0.0, 1.0) * np.clip((0.42 - saturation) / 0.28, 0.0, 1.0)
    height, width = white.shape
    y = np.arange(height, dtype=np.float32)[:, None]
    x = np.arange(width, dtype=np.float32)[None, :]
    lower_lip_band = np.exp(-(((y - height * 0.50) / max(height * 0.28, 1.0)) ** 4))
    horizontal_band = np.exp(-(((x - width * 0.52) / max(width * 0.47, 1.0)) ** 8))
    mask = white * lower_lip_band * horizontal_band

    active = mask > 0.18
    kept = np.zeros_like(active, dtype=bool)
    kept_boxes: list[dict[str, Any]] = []
    for box in component_boxes(active):
        cx, cy = box["center"]
        area = box["area"]
        keep = area >= 4 and height * 0.22 <= cy <= height * 0.72 and width * 0.25 <= cx <= width * 0.88
        if not keep:
            continue
        bbox = box["bbox"]
        kept[bbox["top"] : bbox["bottom"] + 1, bbox["left"] : bbox["right"] + 1] |= active[
            bbox["top"] : bbox["bottom"] + 1, bbox["left"] : bbox["right"] + 1
        ]
        kept_boxes.append(box)

    mask = np.where(kept, mask, 0.0)
    hard = Image.fromarray(np.rint(np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8), mode="L")
    soft = hard.filter(ImageFilter.GaussianBlur(radius=0.8))

    overlay = crop.convert("RGBA")
    alpha = np.asarray(soft, dtype=np.uint8)
    tint = np.zeros((height, width, 4), dtype=np.uint8)
    tint[:, :, :3] = 255
    tint[:, :, 3] = alpha
    overlay.alpha_composite(Image.fromarray(tint, mode="RGBA"))
    draw = ImageDraw.Draw(overlay)
    for box in kept_boxes:
        bbox = box["bbox"]
        draw.rectangle((bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]), outline=(80, 255, 120, 255), width=1)
    return crop, hard, soft, overlay, kept_boxes


def warp_mask_to_atlas(
    atlas: Image.Image,
    source_mask: Image.Image,
    target_x0: float,
    target_x1: float,
    target_y0: float,
    target_y1: float,
    right_glint_strength: float,
    right_glint_x: float,
    right_glint_y: float,
    right_glint_width: float,
    right_glint_height: float,
    extra_glints: list[tuple[float, float, float, float, float]],
) -> tuple[Image.Image, dict[str, Any]]:
    rgba = np.asarray(atlas.convert("RGBA"), dtype=np.uint8)
    full = rgba[:, :, 0] > 8
    lip_box = active_bbox(full)
    if lip_box is None:
        raise ValueError("Atlas R channel has no active lip pixels.")

    source_values = np.asarray(source_mask.convert("L"), dtype=np.uint8)
    source_box = active_bbox(source_values > 8)
    if source_box is None:
        raise ValueError("Reference gloss extraction produced an empty mask.")

    source_crop = source_mask.crop(
        (
            source_box["left"],
            source_box["top"],
            source_box["right"] + 1,
            source_box["bottom"] + 1,
        )
    )

    target_left = int(round(lip_box["left"] + lip_box["width"] * target_x0))
    target_right = int(round(lip_box["left"] + lip_box["width"] * target_x1))
    target_top = int(round(lip_box["top"] + lip_box["height"] * target_y0))
    target_bottom = int(round(lip_box["top"] + lip_box["height"] * target_y1))
    target_width = max(1, target_right - target_left + 1)
    target_height = max(1, target_bottom - target_top + 1)

    resized = source_crop.resize((target_width, target_height), Image.Resampling.BICUBIC)
    resized_values = np.asarray(resized, dtype=np.float32) / 255.0
    target = np.zeros(rgba.shape[:2], dtype=np.float32)
    target[target_top : target_top + target_height, target_left : target_left + target_width] = resized_values

    glint_summary: list[dict[str, Any]] = []

    def add_glint(
        strength: float,
        rel_x: float,
        rel_y: float,
        rel_width: float,
        rel_height: float,
    ) -> None:
        nonlocal target
        if strength <= 0.0:
            return
        y_grid, x_grid = np.indices(target.shape, dtype=np.float32)
        center_x = lip_box["left"] + lip_box["width"] * rel_x
        center_y = lip_box["top"] + lip_box["height"] * rel_y
        sigma_x = max(0.8, lip_box["width"] * rel_width)
        sigma_y = max(0.45, lip_box["height"] * rel_height)
        glint = np.exp(-(((x_grid - center_x) / sigma_x) ** 4 + ((y_grid - center_y) / sigma_y) ** 2))
        target = np.maximum(target, glint * np.clip(strength, 0.0, 1.0))
        glint_summary.append(
            {
                "center": [float(center_x), float(center_y)],
                "sigma": [float(sigma_x), float(sigma_y)],
                "strength": float(np.clip(strength, 0.0, 1.0)),
            }
        )

    add_glint(
        right_glint_strength,
        right_glint_x,
        right_glint_y,
        right_glint_width,
        right_glint_height,
    )
    for rel_x, rel_y, rel_width, rel_height, strength in extra_glints:
        add_glint(strength, rel_x, rel_y, rel_width, rel_height)

    full_strength = rgba[:, :, 0].astype(np.float32) / 255.0
    target = np.clip(target * full_strength, 0.0, 1.0)
    target = np.asarray(
        Image.fromarray(np.rint(target * 255).astype(np.uint8), mode="L").filter(ImageFilter.GaussianBlur(radius=0.25)),
        dtype=np.float32,
    )
    target = np.clip((target / 255.0) ** 0.82, 0.0, 1.0)

    out = rgba.copy()
    out[:, :, 3] = np.rint(target * 255).astype(np.uint8)
    atlas_alpha = Image.fromarray(out[:, :, 3], mode="L")
    return Image.fromarray(out, mode="RGBA"), {
        "lipBbox": lip_box,
        "sourceGlossBbox": source_box,
        "targetBbox": {
            "left": target_left,
            "top": target_top,
            "right": target_left + target_width - 1,
            "bottom": target_top + target_height - 1,
            "width": target_width,
            "height": target_height,
        },
        "atlasGlossBboxGt8": active_bbox(np.asarray(atlas_alpha) > 8),
        "atlasGlossPixelsGt8": int((np.asarray(atlas_alpha) > 8).sum()),
        "atlasGlossPixelsGt48": int((np.asarray(atlas_alpha) > 48).sum()),
        "atlasGlossPixelsGt96": int((np.asarray(atlas_alpha) > 96).sum()),
        "atlasGlossMaxAlpha": int(np.asarray(atlas_alpha).max()),
        "glints": glint_summary,
    }


def channel_preview(atlas: Image.Image) -> Image.Image:
    rgba = atlas.convert("RGBA")
    channels = rgba.split()
    tile = rgba.size[0]
    preview = Image.new("RGB", (tile * 2, tile * 2), (0, 0, 0))
    labels = [
        ("R full", channels[0], 0, 0),
        ("G overline", channels[1], tile, 0),
        ("B gradient", channels[2], 0, tile),
        ("A reference gloss", channels[3], tile, tile),
    ]
    draw = ImageDraw.Draw(preview)
    for label, channel, x, y in labels:
        preview.paste(Image.merge("RGB", (channel, channel, channel)), (x, y))
        draw.rectangle((x + 8, y + 8, x + 168, y + 31), fill=(255, 255, 255))
        draw.text((x + 15, y + 13), label, fill=(0, 0, 0))
    return preview


def save(path: Path, image: Image.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path)


def parse_extra_glints(values: list[str]) -> list[tuple[float, float, float, float, float]]:
    glints: list[tuple[float, float, float, float, float]] = []
    for value in values:
        parts = [float(part.strip()) for part in value.split(",")]
        if len(parts) != 5:
            raise ValueError("--extra-glint must be X,Y,W,H,STRENGTH")
        glints.append((parts[0], parts[1], parts[2], parts[3], parts[4]))
    return glints


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    reference_path = resolve(repo, args.reference)
    atlas_path = resolve(repo, args.atlas)
    out_dir = resolve(repo, args.out_dir)
    crop_box = parse_crop(args.crop)
    extra_glints = parse_extra_glints(args.extra_glint)

    reference = Image.open(reference_path)
    atlas = Image.open(atlas_path).convert("RGBA")
    crop, hard, soft, overlay, boxes = extract_reference_mask(reference, crop_box)
    candidate_atlas, warp_summary = warp_mask_to_atlas(
        atlas,
        soft,
        args.target_x0,
        args.target_x1,
        args.target_y0,
        args.target_y1,
        args.right_glint_strength,
        args.right_glint_x,
        args.right_glint_y,
        args.right_glint_width,
        args.right_glint_height,
        extra_glints,
    )

    outputs = {
        "sourceReferenceCopy": save(out_dir / "source_reference_gloss_lip.png", reference.convert("RGB")),
        "referenceLowerLipCrop": save(out_dir / "reference_lower_lip_crop.png", crop),
        "referenceGlossMaskHard": save(out_dir / "reference_gloss_mask_hard.png", hard),
        "referenceGlossMaskSoft": save(out_dir / "reference_gloss_mask_soft.png", soft),
        "referenceGlossExtractOverlay": save(out_dir / "reference_gloss_extract_overlay.png", overlay),
        "candidateAtlas": save(out_dir / "lip-drawn-style-atlas-v1-reference-gloss.png", candidate_atlas),
        "candidateAtlasChannels": save(out_dir / "reference_gloss_atlas_channels.png", channel_preview(candidate_atlas)),
    }
    summary = {
        "status": "reference_gloss_mask_candidate",
        "method": "white-highlight extraction from user-provided glossy lip reference, warped into existing atlas alpha",
        "reference": str(reference_path),
        "sourceCrop": {
            "left": crop_box[0],
            "top": crop_box[1],
            "right": crop_box[2],
            "bottom": crop_box[3],
            "width": crop_box[2] - crop_box[0],
            "height": crop_box[3] - crop_box[1],
        },
        "componentBoxes": boxes,
        "warp": warp_summary,
        "outputs": outputs,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "candidateAtlas": outputs["candidateAtlas"], "summary": str(out_dir / "summary.json"), "warp": warp_summary}, ensure_ascii=False))


if __name__ == "__main__":
    main()
