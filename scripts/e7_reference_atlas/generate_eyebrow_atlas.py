#!/usr/bin/env python3
"""Generate Unity-ready eyebrow texture atlases and preview evidence."""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from generate_user_drawn_mask_textures import format_path, resolve_path, save, write_unity_meta

EYEBROW_COLOR_PRESETS: tuple[tuple[str, tuple[int, int, int], float], ...] = (
    ("black", (23, 20, 18), 0.06),
    ("dark brown", (59, 42, 34), 0.14),
    ("brown", (107, 74, 52), 0.25),
    ("light brown", (139, 100, 71), 0.38),
    ("wine", (106, 36, 59), 0.30),
)

CANDIDATE_CHANNEL_PROFILES: dict[int, dict[str, float | int]] = {
    1: {"morph": -1, "coverage": 0.72, "strand": 0.24, "fill": 0.08, "neutral": 0.34},
    2: {"morph": 0, "coverage": 0.86, "strand": 0.30, "fill": 0.11, "neutral": 0.40},
    3: {"morph": 1, "coverage": 1.00, "strand": 0.36, "fill": 0.15, "neutral": 0.46},
    4: {"morph": 2, "coverage": 1.12, "strand": 0.42, "fill": 0.19, "neutral": 0.52},
    5: {"morph": 1, "coverage": 0.94, "strand": 0.34, "fill": 0.13, "neutral": 0.44},
}


ATTACHMENT_STRIP = Path(
    "/Users/yeoduchi/.codex/attachments/5b4c9792-6760-4d4c-af08-3e2323e46728/image-1.png"
)
CANDIDATE_DEFAULTS = [
    Path("/Users/yeoduchi/Documents/ChatGPT Image 2026년 7월 1일 오전 12_09_27 (1).png"),
    Path("/Users/yeoduchi/Documents/ChatGPT Image 2026년 7월 1일 오전 12_09_27 (2).png"),
    Path("/Users/yeoduchi/Documents/ChatGPT Image 2026년 7월 1일 오전 12_09_27 (3).png"),
    Path("/Users/yeoduchi/Documents/ChatGPT Image 2026년 7월 1일 오전 12_09_27 (4).png"),
    Path("/Users/yeoduchi/Documents/ChatGPT Image 2026년 7월 1일 오전 12_09_27 (5).png"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate eyebrow RGBA atlases, Unity Resource texture, and preview sheets."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--face",
        type=Path,
        default=Path("/Users/yeoduchi/Downloads/사용자 첨부 파일.png"),
    )
    parser.add_argument("--psd", type=Path, default=Path("/Users/yeoduchi/Downloads/cenonical.PSD"))
    parser.add_argument("--fallback-attachment-strip", type=Path, default=ATTACHMENT_STRIP)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/e7-reference-atlas/eyebrow-validation-v1"),
    )
    parser.add_argument(
        "--unity-output-dir",
        type=Path,
        default=Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"),
    )
    parser.add_argument("--unity-mask-id", default="eyebrow-hair-atlas-v1")
    parser.add_argument("--selected-candidate", type=int, default=5)
    for index, default_path in enumerate(CANDIDATE_DEFAULTS, start=1):
        parser.add_argument(f"--candidate-{index}", type=Path, default=default_path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_if_exists(repo: Path, source: Path | None, destination: Path) -> dict[str, object]:
    if source is None or not source.exists():
        return {
            "status": "missing",
            "sourcePath": str(source) if source is not None else "none",
        }

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {
        "status": "copied",
        "sourcePath": format_path(repo, source),
        "storedPath": format_path(repo, destination),
        "sha256": sha256(destination),
    }


def load_or_recover_face(repo: Path, face_path: Path, fallback_strip: Path, source_dir: Path) -> tuple[Image.Image | None, dict[str, object]]:
    if face_path.exists():
        stored = source_dir / "face.png"
        shutil.copyfile(face_path, stored)
        return Image.open(stored).convert("RGB"), {
            "status": "copied_full_face",
            "sourcePath": format_path(repo, face_path),
            "storedPath": format_path(repo, stored),
            "sha256": sha256(stored),
        }

    if fallback_strip.exists():
        strip = Image.open(fallback_strip).convert("RGBA")
        # The only available fallback in this thread is a horizontal attachment strip.
        # Crop the first thumbnail so preview generation remains possible, but mark it
        # explicitly as weaker evidence than the missing full face source.
        crop_box = (128, 54, min(strip.width, 310), min(strip.height, 232))
        face = strip.crop(crop_box).convert("RGB")
        stored = source_dir / "face-fallback-thumbnail.png"
        save(stored, face)
        return face, {
            "status": "fallback_thumbnail_from_attachment_strip",
            "missingPreferredSource": str(face_path),
            "sourcePath": format_path(repo, fallback_strip),
            "storedPath": format_path(repo, stored),
            "cropBox": list(crop_box),
            "sha256": sha256(stored),
            "greenEvidenceEligible": False,
        }

    return None, {
        "status": "missing",
        "missingPreferredSource": str(face_path),
        "greenEvidenceEligible": False,
    }


def eyebrow_alpha_from_rgb(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB")).astype(np.float32)
    luminance = rgb.mean(axis=2)
    # The supplied images have a baked checkerboard background around 238-255.
    # Hair strokes sit much darker. This extracts strands without preserving the board.
    alpha = np.clip((226.0 - luminance) / 96.0, 0.0, 1.0)
    alpha[luminance > 224.0] = 0.0
    alpha = np.where(alpha > 0.035, alpha, 0.0)
    return alpha


def apply_candidate_profile(hair_img: Image.Image, candidate_index: int) -> Image.Image:
    profile = CANDIDATE_CHANNEL_PROFILES.get(candidate_index, CANDIDATE_CHANNEL_PROFILES[5])
    morph = int(profile["morph"])
    if morph < 0:
        return hair_img.filter(ImageFilter.MinFilter(3))
    if morph >= 2:
        return hair_img.filter(ImageFilter.MaxFilter(5))
    if morph == 1:
        return hair_img.filter(ImageFilter.MaxFilter(3))
    return hair_img


def make_channel_atlas(
    image: Image.Image,
    candidate_index: int = 5,
) -> tuple[Image.Image, dict[str, object], np.ndarray]:
    alpha = eyebrow_alpha_from_rgb(image)
    hair = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    hair_img = Image.fromarray(hair, mode="L")
    hair_img = apply_candidate_profile(hair_img, candidate_index)
    hair = np.asarray(hair_img).astype(np.uint8)
    profile = CANDIDATE_CHANNEL_PROFILES.get(candidate_index, CANDIDATE_CHANNEL_PROFILES[5])
    coverage = hair_img.filter(ImageFilter.GaussianBlur(radius=2.4))
    fill = hair_img.filter(ImageFilter.GaussianBlur(radius=5.0))
    neutralizer = hair_img.filter(ImageFilter.GaussianBlur(radius=8.0))

    coverage_np = np.asarray(coverage).astype(np.float32)
    fill_np = np.asarray(fill).astype(np.float32)
    neutral_np = np.asarray(neutralizer).astype(np.float32)
    rgba = np.stack(
        [
            np.clip(
                np.maximum(
                    coverage_np * float(profile["coverage"]),
                    hair.astype(np.float32) * float(profile["coverage"]) * 0.84,
                ),
                0,
                255,
            ),
            np.clip(hair.astype(np.float32) * float(profile["strand"]), 0, 255),
            np.clip(fill_np * float(profile["fill"]), 0, 255),
            np.clip(neutral_np * float(profile["neutral"]), 0, 255),
        ],
        axis=2,
    ).astype(np.uint8)

    atlas = Image.fromarray(rgba, mode="RGBA")
    ys, xs = np.nonzero(hair > 8)
    bbox = "none"
    if len(xs) > 0:
        bbox = (
            f"left={int(xs.min())},top={int(ys.min())},right={int(xs.max())},"
            f"bottom={int(ys.max())},width={int(xs.max() - xs.min() + 1)},"
            f"height={int(ys.max() - ys.min() + 1)}"
        )
    stats = {
        "size": {"width": image.width, "height": image.height},
        "activePixelCountGt8": int((hair > 8).sum()),
        "activeCoverageGt8": float((hair > 8).sum() / max(1, hair.size)),
        "activeBbox": bbox,
        "maxHairValue": int(hair.max()) if hair.size else 0,
        "candidateChannelProfile": profile,
    }
    return atlas, stats, hair


def make_channel_sheet(atlas: Image.Image) -> Image.Image:
    channels = atlas.split()
    labels = ("R coverage", "G strands", "B tint fill", "A neutralizer")
    tile = 300
    sheet = Image.new("RGB", (tile * 4, tile + 32), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, channel) in enumerate(zip(labels, channels)):
        thumb = channel.convert("RGB")
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        x = index * tile + (tile - thumb.width) // 2
        y = 28 + (tile - thumb.height) // 2
        draw.text((index * tile + 8, 8), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x, y))
    return sheet


def split_brow_crops(atlas: Image.Image, hair: np.ndarray) -> list[tuple[Image.Image, Image.Image]]:
    width = atlas.width
    crops: list[tuple[Image.Image, Image.Image]] = []
    for left, right in ((0, width // 2), (width // 2, width)):
        region = hair[:, left:right]
        ys, xs = np.nonzero(region > 8)
        if len(xs) == 0:
            continue
        pad = 18
        crop_left = max(left + int(xs.min()) - pad, 0)
        crop_right = min(left + int(xs.max()) + pad, atlas.width - 1)
        crop_top = max(int(ys.min()) - pad, 0)
        crop_bottom = min(int(ys.max()) + pad, atlas.height - 1)
        box = (crop_left, crop_top, crop_right + 1, crop_bottom + 1)
        crop = atlas.crop(box)
        mask = Image.fromarray(hair, mode="L").crop(box)
        crops.append((crop, mask))
    return crops


def sample_skin_color(face: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int]:
    left, top, right, bottom = box
    height = max(1, bottom - top)
    sample_box = (
        max(0, left),
        min(face.height - 1, bottom + height // 5),
        min(face.width, right),
        min(face.height, bottom + height),
    )
    if sample_box[2] <= sample_box[0] or sample_box[3] <= sample_box[1]:
        return (205, 164, 140)
    pixels = np.asarray(face.crop(sample_box).convert("RGB")).reshape(-1, 3)
    if pixels.size == 0:
        return (205, 164, 140)
    median = np.median(pixels, axis=0)
    return tuple(int(np.clip(v, 0, 255)) for v in median)


def connected_components(mask: np.ndarray) -> list[tuple[int, int, int, int, int]]:
    height, width = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    components: list[tuple[int, int, int, int, int]] = []
    for start_y in range(height):
        for start_x in range(width):
            if visited[start_y, start_x] or not mask[start_y, start_x]:
                continue

            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            visited[start_y, start_x] = True
            min_x = max_x = start_x
            min_y = max_y = start_y
            count = 0
            while queue:
                x, y = queue.popleft()
                count += 1
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = x + dx
                        ny = y + dy
                        if (
                            nx < 0
                            or ny < 0
                            or nx >= width
                            or ny >= height
                            or visited[ny, nx]
                            or not mask[ny, nx]
                        ):
                            continue
                        visited[ny, nx] = True
                        queue.append((nx, ny))
            components.append((min_x, min_y, max_x, max_y, count))
    return components


def expand_box(
    box: tuple[int, int, int, int],
    image_size: tuple[int, int],
    x_pad_ratio: float,
    y_pad_ratio: float,
) -> tuple[int, int, int, int]:
    width, height = image_size
    left, top, right, bottom = box
    box_w = max(1, right - left)
    box_h = max(1, bottom - top)
    x_pad = int(round(box_w * x_pad_ratio))
    y_pad = int(round(box_h * y_pad_ratio))
    return (
        max(0, left - x_pad),
        max(0, top - y_pad),
        min(width, right + x_pad),
        min(height, bottom + y_pad),
    )


def prior_tight_brow_box(face: Image.Image, side: str) -> tuple[int, int, int, int]:
    width, height = face.size
    if side == "screenLeft":
        return (
            int(width * 0.150),
            int(height * 0.252),
            int(width * 0.466),
            int(height * 0.292),
        )

    return (
        int(width * 0.534),
        int(height * 0.252),
        int(width * 0.850),
        int(height * 0.292),
    )


def estimate_single_brow_boundary(
    face: Image.Image,
    side: str,
) -> dict[str, object]:
    width, height = face.size
    if side == "screenLeft":
        roi = (
            int(width * 0.165),
            int(height * 0.232),
            int(width * 0.485),
            int(height * 0.320),
        )
    else:
        roi = (
            int(width * 0.515),
            int(height * 0.232),
            int(width * 0.895),
            int(height * 0.320),
        )

    crop = face.crop(roi).convert("RGB")
    rgb = np.asarray(crop).astype(np.float32)
    luminance = rgb.mean(axis=2)
    threshold = float(min(158.0, max(104.0, np.percentile(luminance, 32.0) - 3.0)))
    dark = luminance < threshold
    dark_img = Image.fromarray((dark.astype(np.uint8) * 255), mode="L")
    dark_img = dark_img.filter(ImageFilter.MaxFilter(5))
    dark_img = dark_img.filter(ImageFilter.MinFilter(3))
    dark_img = dark_img.filter(ImageFilter.GaussianBlur(radius=0.8))
    mask = np.asarray(dark_img) > 28

    prior = prior_tight_brow_box(face, side)
    best: tuple[int, int, int, int, int] | None = None
    best_score = -1.0
    target_y = (roi[3] - roi[1]) * 0.52
    for component in connected_components(mask):
        min_x, min_y, max_x, max_y, count = component
        comp_w = max_x - min_x + 1
        comp_h = max_y - min_y + 1
        if count < 42 or comp_w < 36 or comp_h < 4:
            continue
        if comp_w < 72 or comp_w / max(1, comp_h) < 1.25:
            continue
        if comp_h > mask.shape[0] * 0.68:
            continue
        touches_edge_penalty = 250.0 if min_x <= 1 or max_x >= mask.shape[1] - 2 else 0.0
        shape_penalty = max(0, comp_h - 72) * 18.0
        y_penalty = abs(((min_y + max_y) * 0.5) - target_y) * 3.5
        score = count + comp_w * 4.0 - shape_penalty - y_penalty - touches_edge_penalty
        if score > best_score:
            best = component
            best_score = score

    fallback = best is None
    fallback_reason = "none"
    if best is None:
        tight = prior
        count = 0
        fallback_reason = "no_component_passed_shape_gate"
    else:
        min_x, min_y, max_x, max_y, count = best
        tight = (roi[0] + min_x, roi[1] + min_y, roi[0] + max_x + 1, roi[1] + max_y + 1)
        comp_width = tight[2] - tight[0]
        comp_height = tight[3] - tight[1]
        comp_center_y = (tight[1] + tight[3]) * 0.5
        prior_center_y = (prior[1] + prior[3]) * 0.5
        if (
            comp_width < (prior[2] - prior[0]) * 0.62
            or comp_height < 18
            or abs(comp_center_y - prior_center_y) > height * 0.028
        ):
            fallback = True
            fallback_reason = "component_failed_face_prior_gate"
            tight = prior
            count = 0

    render_box = expand_box(tight, face.size, 0.05, 0.20)
    left, top, right, bottom = render_box
    if side == "screenLeft":
        inner_x = right
        tail_x = left
        arch_x = int(left + (right - left) * 0.62)
    else:
        inner_x = left
        tail_x = right
        arch_x = int(left + (right - left) * 0.38)
    mid_y = int(top + (bottom - top) * 0.54)
    arch_y = int(top + (bottom - top) * 0.20)

    return {
        "side": side,
        "method": "local_dark_component_with_face_prior_v1",
        "fallbackUsed": fallback,
        "fallbackReason": fallback_reason,
        "roi": {"left": roi[0], "top": roi[1], "right": roi[2], "bottom": roi[3]},
        "darkThreshold": threshold,
        "componentPixelCount": int(count),
        "componentScore": float(best_score),
        "tightBbox": {
            "left": tight[0],
            "top": tight[1],
            "right": tight[2],
            "bottom": tight[3],
            "width": tight[2] - tight[0],
            "height": tight[3] - tight[1],
        },
        "renderBbox": {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
        },
        "anchors": {
            "inner": {"x": inner_x, "y": mid_y},
            "arch": {"x": arch_x, "y": arch_y},
            "tail": {"x": tail_x, "y": mid_y},
        },
    }


def estimate_eyebrow_boundary(face: Image.Image) -> dict[str, object]:
    left = estimate_single_brow_boundary(face, "screenLeft")
    right = estimate_single_brow_boundary(face, "screenRight")
    return {
        "id": "eyebrow-boundary-v1",
        "imageSize": {"width": face.width, "height": face.height},
        "screenLeft": left,
        "screenRight": right,
        "exclusionPolicy": {
            "eyelidLowerGuard": "renderBbox must stay above upper eyelid region",
            "glabellaGuard": "inner anchors may not cross the center pimple/glabella area",
            "hairlineGuard": "ROI avoids top hairline; side hair contact lowers component score",
        },
    }


def boundary_render_boxes(boundary: dict[str, object], face: Image.Image) -> list[tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    for key in ("screenLeft", "screenRight"):
        side = boundary.get(key)
        if not isinstance(side, dict):
            continue
        bbox = side.get("renderBbox")
        if not isinstance(bbox, dict):
            continue
        boxes.append(
            (
                int(bbox["left"]),
                int(bbox["top"]),
                int(bbox["right"]),
                int(bbox["bottom"]),
            )
        )
    if len(boxes) == 2:
        return boxes
    width, height = face.size
    return [
        (int(width * 0.125), int(height * 0.282), int(width * 0.440), int(height * 0.352)),
        (int(width * 0.555), int(height * 0.282), int(width * 0.875), int(height * 0.352)),
    ]


def make_boundary_overlay(face: Image.Image, boundary: dict[str, object]) -> Image.Image:
    output = face.convert("RGBA")
    draw = ImageDraw.Draw(output)
    for key, color in (("screenLeft", (0, 190, 255, 210)), ("screenRight", (0, 190, 255, 210))):
        side = boundary[key]
        tight = side["tightBbox"]
        render = side["renderBbox"]
        anchors = side["anchors"]
        draw.rectangle(
            (tight["left"], tight["top"], tight["right"], tight["bottom"]),
            outline=(255, 220, 0, 220),
            width=3,
        )
        draw.rectangle(
            (render["left"], render["top"], render["right"], render["bottom"]),
            outline=color,
            width=3,
        )
        for anchor_name, anchor in anchors.items():
            x = anchor["x"]
            y = anchor["y"]
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(255, 70, 70, 230))
            draw.text((x + 7, y - 7), anchor_name, fill=(20, 20, 20, 255))
    return output.convert("RGB")


def make_boundary_mask(face: Image.Image, boundary: dict[str, object]) -> Image.Image:
    mask = Image.new("L", face.size, 0)
    draw = ImageDraw.Draw(mask)
    for box in boundary_render_boxes(boundary, face):
        draw.rounded_rectangle(box, radius=max(6, (box[3] - box[1]) // 2), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=7.0))
    return mask


def overlay_candidate(
    face: Image.Image,
    atlas: Image.Image,
    hair: np.ndarray,
    boundary: dict[str, object] | None,
    brow_color: tuple[int, int, int] = (59, 42, 34),
    tone_lift: float = 0.14,
) -> Image.Image:
    output = face.convert("RGBA")
    boxes = boundary_render_boxes(boundary, output) if boundary is not None else boundary_render_boxes({}, output)
    crops = split_brow_crops(atlas, hair)
    if len(crops) < 2:
        return output.convert("RGB")

    for (crop, _mask), box in zip(crops[:2], boxes):
        box_w = max(1, box[2] - box[0])
        box_h = max(1, box[3] - box[1])
        target_w = box_w
        target_h = max(28, min(44, int(round(box_h * 0.36))))
        y_offset = max(0, int(round((box_h - target_h) * 0.44)))
        resized = crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
        channels = resized.split()
        coverage, strands, tint_fill, neutralizer = channels
        skin = sample_skin_color(output.convert("RGB"), box)

        neutral_alpha = neutralizer.point(lambda value: int(value * 0.08))
        neutral_layer = Image.new("RGBA", (target_w, target_h), (*skin, 0))
        neutral_layer.putalpha(neutral_alpha)
        output.alpha_composite(neutral_layer, (box[0], box[1] + y_offset))

        strand_alpha = Image.eval(strands, lambda value: min(54, int(value * 0.22)))
        tint_alpha = Image.eval(tint_fill, lambda value: min(14, int(value * 0.07)))
        tint_layer = Image.new("RGBA", (target_w, target_h), (89, 65, 54, 0))
        tint_layer.putalpha(tint_alpha)
        output.alpha_composite(tint_layer, (box[0], box[1] + y_offset))
        strand_layer = Image.new("RGBA", (target_w, target_h), (42, 34, 30, 0))
        strand_layer.putalpha(strand_alpha)
        output.alpha_composite(strand_layer, (box[0], box[1] + y_offset))

    return output.convert("RGB")


def make_candidate_contact_sheet(images: list[tuple[str, Image.Image]], columns: int = 2) -> Image.Image:
    tile_w = 360
    tile_h = 330
    rows = int((len(images) + columns - 1) / columns)
    sheet = Image.new("RGB", (columns * tile_w, rows * tile_h), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * tile_w
        y = row * tile_h
        thumb = image.convert("RGB")
        thumb.thumbnail((tile_w - 20, tile_h - 48), Image.Resampling.LANCZOS)
        draw.text((x + 10, y + 10), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, y + 38))
    return sheet


def make_preview_sheet(previews: list[tuple[str, Image.Image]]) -> Image.Image:
    tile_w = 360
    tile_h = 620
    sheet = Image.new("RGB", (tile_w * len(previews), tile_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(previews):
        x = index * tile_w
        thumb = image.convert("RGB")
        thumb.thumbnail((tile_w - 16, tile_h - 44), Image.Resampling.LANCZOS)
        draw.text((x + 8, 8), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x + (tile_w - thumb.width) // 2, 36))
    return sheet


def make_brow_crop_sheet(previews: list[tuple[str, Image.Image]], columns: int = 5) -> Image.Image:
    crop_box = (55, 390, 830, 635)
    tile_w = 300
    label_h = 28
    pad = 10
    rows = int((len(previews) + columns - 1) / columns)
    crop_w = crop_box[2] - crop_box[0]
    crop_h = crop_box[3] - crop_box[1]
    tile_h = int(round(crop_h * tile_w / crop_w)) + label_h
    sheet = Image.new(
        "RGB",
        (columns * tile_w + (columns + 1) * pad, rows * tile_h + (rows + 1) * pad),
        (235, 235, 235),
    )
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(previews):
        x = pad + (index % columns) * (tile_w + pad)
        y = pad + (index // columns) * (tile_h + pad)
        tile = Image.new("RGB", (tile_w, tile_h), (246, 246, 246))
        crop = image.convert("RGB").crop(crop_box)
        crop = crop.resize((tile_w, tile_h - label_h), Image.Resampling.LANCZOS)
        tile.paste(crop, (0, label_h))
        ImageDraw.Draw(tile).text((6, 8), label, fill=(0, 0, 0))
        sheet.paste(tile, (x, y))
    return sheet


APPROVED_LEFT_TOP_V10 = [(96, 508), (146, 493), (216, 477), (288, 467), (362, 476), (421, 493)]
APPROVED_LEFT_BOTTOM_V10 = [(96, 508), (178, 508), (262, 510), (348, 520), (421, 536)]
APPROVED_RIGHT_INNER_X_V10 = 486
APPROVED_RIGHT_TAIL_X_V10 = 830
FACE_LOCAL_SOURCE_Y_TOP = 464.0
FACE_LOCAL_SOURCE_Y_BOTTOM = 532.0
FACE_LOCAL_UV_TOP = 0.772
FACE_LOCAL_UV_BOTTOM = 0.684


def mirror_left_brow_points(points: list[tuple[int, int]]) -> list[tuple[int, int]]:
    left_min_x = APPROVED_LEFT_TOP_V10[0][0]
    left_max_x = APPROVED_LEFT_TOP_V10[-1][0]
    mirrored: list[tuple[int, int]] = []
    for x, y in reversed(points):
        t = (left_max_x - x) / max(1, left_max_x - left_min_x)
        mirrored_x = APPROVED_RIGHT_INNER_X_V10 + t * (APPROVED_RIGHT_TAIL_X_V10 - APPROVED_RIGHT_INNER_X_V10)
        mirrored.append((int(round(mirrored_x)), y))
    return mirrored


def smooth_brow_points(points: list[tuple[int, int]], steps: int = 30) -> list[tuple[float, float]]:
    padded = [points[0]] + points + [points[-1]]
    smoothed: list[tuple[float, float]] = []
    for index in range(1, len(padded) - 2):
        p0, p1, p2, p3 = padded[index - 1], padded[index], padded[index + 1], padded[index + 2]
        for step in range(steps):
            t = step / float(steps)
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            y = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            smoothed.append((x, y))
    smoothed.append(points[-1])
    return smoothed


def approved_brow_polygons_v10() -> dict[str, dict[str, object]]:
    right_top = mirror_left_brow_points(APPROVED_LEFT_TOP_V10)
    right_bottom = mirror_left_brow_points(APPROVED_LEFT_BOTTOM_V10)
    return {
        "screenLeft": {
            "top": APPROVED_LEFT_TOP_V10,
            "bottom": APPROVED_LEFT_BOTTOM_V10,
            "polygon": smooth_brow_points(APPROVED_LEFT_TOP_V10)
            + list(reversed(smooth_brow_points(APPROVED_LEFT_BOTTOM_V10))),
        },
        "screenRight": {
            "top": right_top,
            "bottom": right_bottom,
            "polygon": smooth_brow_points(right_top) + list(reversed(smooth_brow_points(right_bottom))),
        },
    }


def polygon_bbox(points: list[tuple[float, float]]) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return (
        int(np.floor(min(xs))),
        int(np.floor(min(ys))),
        int(np.ceil(max(xs))),
        int(np.ceil(max(ys))),
    )


def bbox_record(box: tuple[int, int, int, int]) -> dict[str, int]:
    left, top, right, bottom = box
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": bottom - top,
    }


def expand_approved_box(box: tuple[int, int, int, int], image_size: tuple[int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    width, height = image_size
    return (
        max(0, left - 12),
        max(0, top - 15),
        min(width, right + 12),
        min(height, bottom + 15),
    )


def estimate_eyebrow_boundary(face: Image.Image) -> dict[str, object]:
    polygons = approved_brow_polygons_v10()
    result: dict[str, object] = {
        "id": "eyebrow-boundary-v1",
        "version": "actual_boundary_v10_runtime_y_aligned_tail_extended_candidate_shape",
        "imageSize": {"width": face.width, "height": face.height},
        "method": "approved_actual_brow_body_boundary_left_shape_mirrored_to_right",
        "commercialCleanupModel": "skin-color cleanup outside final boundary, tint and strand layers inside boundary",
        "exclusionPolicy": {
            "strayHairPolicy": "external sparse brow hairs are intentionally excluded",
            "hairlineGuard": "side hair and top hairline are not part of the brow boundary",
            "rightShapePolicy": "screen-right shape mirrors screen-left silhouette per user request",
        },
    }
    for side_name, side in polygons.items():
        polygon = [(int(round(x)), int(round(y))) for x, y in side["polygon"]]
        tight = polygon_bbox(side["polygon"])
        render = expand_approved_box(tight, face.size)
        result[side_name] = {
            "side": side_name,
            "fallbackUsed": True,
            "fallbackReason": "approved_manual_boundary_v10_runtime_y_aligned_tail_extended",
            "top": side["top"],
            "bottom": side["bottom"],
            "polygon": polygon,
            "tightBbox": bbox_record(tight),
            "renderBbox": bbox_record(render),
            "anchors": {
                "tail": {"x": tight[0] if side_name == "screenLeft" else tight[2], "y": int((tight[1] + tight[3]) * 0.5)},
                "arch": {"x": int((tight[0] + tight[2]) * 0.5), "y": tight[1]},
                "inner": {"x": tight[2] if side_name == "screenLeft" else tight[0], "y": int((tight[1] + tight[3]) * 0.5)},
            },
        }
    return result


def boundary_render_boxes(boundary: dict[str, object], face: Image.Image) -> list[tuple[int, int, int, int]]:
    boxes: list[tuple[int, int, int, int]] = []
    for key in ("screenLeft", "screenRight"):
        side = boundary.get(key)
        if not isinstance(side, dict):
            continue
        bbox = side.get("renderBbox")
        if not isinstance(bbox, dict):
            continue
        boxes.append((int(bbox["left"]), int(bbox["top"]), int(bbox["right"]), int(bbox["bottom"])))
    return boxes


def make_boundary_overlay(face: Image.Image, boundary: dict[str, object]) -> Image.Image:
    output = face.convert("RGBA")
    fill = Image.new("RGBA", face.size, (0, 170, 255, 0))
    alpha = make_boundary_mask(face, boundary).point(lambda value: int(value * 0.26))
    fill.putalpha(alpha)
    output = Image.alpha_composite(output, fill)
    draw = ImageDraw.Draw(output)
    for key, color in (("screenLeft", (0, 150, 255, 255)), ("screenRight", (255, 132, 0, 255))):
        side = boundary[key]
        polygon = [tuple(point) for point in side["polygon"]]
        draw.line(polygon + [polygon[0]], fill=color, width=3)
    return output.convert("RGB")


def make_boundary_mask(face: Image.Image, boundary: dict[str, object]) -> Image.Image:
    mask = Image.new("L", face.size, 0)
    draw = ImageDraw.Draw(mask)
    for key in ("screenLeft", "screenRight"):
        side = boundary[key]
        draw.polygon([tuple(point) for point in side["polygon"]], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=5.5))


def photo_to_face_local_uv(x: float, y: float, image_width: int) -> tuple[float, float]:
    u = x / max(1.0, float(image_width))
    v = FACE_LOCAL_UV_TOP + (y - FACE_LOCAL_SOURCE_Y_TOP) * (
        FACE_LOCAL_UV_BOTTOM - FACE_LOCAL_UV_TOP
    ) / (FACE_LOCAL_SOURCE_Y_BOTTOM - FACE_LOCAL_SOURCE_Y_TOP)
    return float(np.clip(u, 0.0, 1.0)), float(np.clip(v, 0.0, 1.0))


def make_face_local_boundary_texture(face: Image.Image, boundary: dict[str, object], size: int = 512) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    for key in ("screenLeft", "screenRight"):
        side = boundary[key]
        points: list[tuple[int, int]] = []
        for x, y in side["polygon"]:
            u, v = photo_to_face_local_uv(float(x), float(y), face.width)
            points.append((int(round(u * (size - 1))), int(round((1.0 - v) * (size - 1)))))
        draw.polygon(points, fill=255)
    hard = mask.filter(ImageFilter.GaussianBlur(0.8)).point(lambda value: 255 if value >= 88 else 0)
    edge = hard.filter(ImageFilter.GaussianBlur(5.0))
    cleanup = hard.filter(ImageFilter.GaussianBlur(15.0))
    return Image.merge("RGBA", (hard, edge, cleanup, cleanup))


def side_polygon_mask(face: Image.Image, side: dict[str, object]) -> Image.Image:
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).polygon([tuple(point) for point in side["polygon"]], fill=255)
    return mask


def subtract_masks(outer: Image.Image, inner: Image.Image, scale: float = 1.0) -> Image.Image:
    outer_np = np.asarray(outer).astype(np.float32)
    inner_np = np.asarray(inner).astype(np.float32)
    result = np.clip((outer_np - inner_np) * scale, 0, 255).astype(np.uint8)
    return Image.fromarray(result, mode="L")


def overlay_candidate(
    face: Image.Image,
    atlas: Image.Image,
    hair: np.ndarray,
    boundary: dict[str, object] | None,
    brow_color: tuple[int, int, int] = (59, 42, 34),
    tone_lift: float = 0.14,
) -> Image.Image:
    if boundary is None:
        return face.convert("RGB")

    output = face.convert("RGBA")
    crops = split_brow_crops(atlas, hair)
    if len(crops) < 2:
        return output.convert("RGB")

    for side_key, crop_pair in zip(("screenLeft", "screenRight"), crops[:2]):
        side = boundary[side_key]
        tight = side["tightBbox"]
        render = side["renderBbox"]
        hard_mask = side_polygon_mask(face, side)
        edge_mask = hard_mask.filter(ImageFilter.GaussianBlur(radius=2.0))
        cleanup_mask = subtract_masks(
            hard_mask.filter(ImageFilter.GaussianBlur(radius=14.0)),
            hard_mask.filter(ImageFilter.GaussianBlur(radius=1.2)),
            scale=1.25,
        )
        cleanup_alpha = cleanup_mask.point(lambda value: min(58, int(value * 0.32)))
        skin = sample_skin_color(face, (render["left"], render["top"], render["right"], render["bottom"]))
        cleanup_layer = Image.new("RGBA", face.size, (*skin, 0))
        cleanup_layer.putalpha(cleanup_alpha)
        output = Image.alpha_composite(output, cleanup_layer)

        crop, _mask = crop_pair
        target_box = (tight["left"], tight["top"], tight["right"], tight["bottom"])
        target_w = max(1, target_box[2] - target_box[0])
        target_h = max(1, target_box[3] - target_box[1])
        resized = crop.resize((target_w, target_h), Image.Resampling.LANCZOS)
        coverage, strands, tint_fill, _neutralizer = resized.split()

        local_edge = edge_mask.crop(target_box)
        local_hard = hard_mask.crop(target_box)
        x_axis = np.linspace(0.0, 1.0, target_w, dtype=np.float32)
        left_taper = np.clip((x_axis - 0.02) / 0.12, 0.0, 1.0)
        right_taper = np.clip((0.98 - x_axis) / 0.12, 0.0, 1.0)
        horizontal_taper = (left_taper * left_taper * (3.0 - 2.0 * left_taper))
        horizontal_taper *= (right_taper * right_taper * (3.0 - 2.0 * right_taper))
        horizontal_taper = horizontal_taper.reshape(1, target_w)
        tone_lift_np = (
            np.asarray(local_hard).astype(np.float32)
            * horizontal_taper
            * np.clip(tone_lift, 0.0, 1.0)
            * 0.78
        )
        tone_lift_alpha = Image.fromarray(np.clip(tone_lift_np, 0, 92).astype(np.uint8), mode="L")
        tone_lift_color = tuple(
            int(round(skin[channel] * 0.72 + brow_color[channel] * 0.28))
            for channel in range(3)
        )
        tone_lift_layer = Image.new("RGBA", (target_w, target_h), (*tone_lift_color, 0))
        tone_lift_layer.putalpha(tone_lift_alpha)
        output.alpha_composite(tone_lift_layer, (target_box[0], target_box[1]))

        tint_np = np.maximum(
            np.asarray(local_edge).astype(np.float32) * 0.22,
            np.asarray(tint_fill).astype(np.float32) * 0.28,
        )
        tint_np *= horizontal_taper
        tint_np = np.maximum(
            tint_np,
            np.asarray(local_hard).astype(np.float32) * horizontal_taper * 0.095,
        )
        tint_alpha = Image.fromarray(np.clip(tint_np, 0, 96).astype(np.uint8), mode="L")
        tint_layer = Image.new("RGBA", (target_w, target_h), (*brow_color, 0))
        tint_layer.putalpha(tint_alpha)
        output.alpha_composite(tint_layer, (target_box[0], target_box[1]))

        strand_np = np.minimum(
            np.asarray(strands).astype(np.float32) * 0.52,
            np.asarray(local_hard).astype(np.float32) * 0.58,
        )
        strand_np *= np.sqrt(horizontal_taper)
        strand_alpha = Image.fromarray(np.clip(strand_np, 0, 126).astype(np.uint8), mode="L")
        strand_color = tuple(max(10, int(round(channel * 0.42))) for channel in brow_color)
        strand_layer = Image.new("RGBA", (target_w, target_h), (*strand_color, 0))
        strand_layer.putalpha(strand_alpha)
        output.alpha_composite(strand_layer, (target_box[0], target_box[1]))

    return output.convert("RGB")


def write_summary_md(path: Path, summary: dict[str, object]) -> None:
    selected = summary["selectedCandidate"]
    face = summary["sourceAssets"]["face"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Eyebrow Atlas Generation Summary",
                "",
                f"- Texture set: `{summary['textureSetId']}`",
                f"- Unity mask id: `{summary['unityMaskId']}`",
                f"- Selected candidate: `{selected}`",
                f"- Face source status: `{face['status']}`",
                f"- Boundary summary: `{summary['eyebrowBoundarySummaryPath']}`",
                f"- Boundary overlay: `{summary['eyebrowBoundaryOverlayPath']}`",
                f"- Unity resource: `{summary['unityResourcePath']}`",
                f"- Green evidence eligible: `{summary['greenEvidenceEligible']}`",
                "",
                "This output is buildless asset evidence. Runtime Green still requires iPhone AR evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output_dir = resolve_path(repo, args.output_dir)
    unity_dir = resolve_path(repo, args.unity_output_dir)
    face_path = resolve_path(repo, args.face)
    psd_path = resolve_path(repo, args.psd)
    fallback_strip = resolve_path(repo, args.fallback_attachment_strip)
    assert output_dir is not None
    assert unity_dir is not None
    assert face_path is not None
    assert fallback_strip is not None

    source_dir = output_dir / "source"
    atlas_dir = output_dir / "atlas_candidates"
    preview_dir = output_dir / "photo_aligned_candidates"
    diagnostics_dir = output_dir / "diagnostics"
    source_dir.mkdir(parents=True, exist_ok=True)
    atlas_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    unity_dir.mkdir(parents=True, exist_ok=True)

    face_image, face_summary = load_or_recover_face(repo, face_path, fallback_strip, source_dir)
    psd_summary = copy_if_exists(repo, psd_path, source_dir / "cenonical.PSD")
    fallback_summary = copy_if_exists(repo, fallback_strip, source_dir / "attachment-strip.png")
    boundary_summary: dict[str, object] | None = None
    boundary_overlay_path = output_dir / "eyebrow_boundary_v1_overlay.png"
    boundary_mask_path = output_dir / "eyebrow_boundary_v1_mask.png"
    boundary_summary_path = output_dir / "eyebrow_boundary_v1.json"
    if face_image is not None:
        boundary_summary = estimate_eyebrow_boundary(face_image)
        save(boundary_overlay_path, make_boundary_overlay(face_image, boundary_summary))
        save(boundary_mask_path, make_boundary_mask(face_image, boundary_summary))
        boundary_summary_path.write_text(
            json.dumps(boundary_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    candidate_summaries: list[dict[str, object]] = []
    contact_images: list[tuple[str, Image.Image]] = []
    preview_images: list[tuple[str, Image.Image]] = []
    candidate_artifacts: list[tuple[int, Image.Image, np.ndarray]] = []
    selected_atlas: Image.Image | None = None
    selected_path: Path | None = None
    unity_resource_summaries: list[dict[str, object]] = []

    for index in range(1, 6):
        candidate_path = resolve_path(repo, getattr(args, f"candidate_{index}"))
        if candidate_path is None or not candidate_path.exists():
            raise FileNotFoundError(f"Missing eyebrow candidate {index}: {candidate_path}")

        stored_source = source_dir / f"candidate-{index}.png"
        shutil.copyfile(candidate_path, stored_source)
        source_image = Image.open(stored_source).convert("RGB")
        atlas, stats, hair = make_channel_atlas(source_image, index)
        atlas_path = atlas_dir / f"eyebrow-candidate-{index}-atlas.png"
        channel_path = diagnostics_dir / f"eyebrow-candidate-{index}-channels.png"
        save(atlas_path, atlas)
        save(channel_path, make_channel_sheet(atlas))
        candidate_artifacts.append((index, atlas, hair))
        unity_mask_id = f"eyebrow-hair-atlas-{index}-v1"
        unity_candidate_path = unity_dir / (unity_mask_id + ".png")
        save(unity_candidate_path, atlas)
        write_unity_meta(
            unity_candidate_path.with_suffix(".png.meta"),
            "e7-" + unity_mask_id,
        )
        unity_resource_summaries.append(
            {
                "index": index,
                "maskId": unity_mask_id,
                "path": format_path(repo, unity_candidate_path),
                "sha256": sha256(unity_candidate_path),
            }
        )
        contact_images.append((f"candidate {index} atlas", atlas))
        if face_image is not None:
            preview = overlay_candidate(face_image, atlas, hair, boundary_summary)
            preview_path = preview_dir / f"eyebrow-candidate-{index}-preview.png"
            save(preview_path, preview)
            preview_images.append((f"candidate {index}", preview))

        if index == args.selected_candidate:
            selected_atlas = atlas
            selected_path = atlas_path

        candidate_summaries.append(
            {
                "index": index,
                "sourcePath": format_path(repo, candidate_path),
                "storedSourcePath": format_path(repo, stored_source),
                "atlasPath": format_path(repo, atlas_path),
                "channelDiagnosticPath": format_path(repo, channel_path),
                "sourceSha256": sha256(stored_source),
                "atlasSha256": sha256(atlas_path),
                **stats,
            }
        )

    if selected_atlas is None or selected_path is None:
        raise ValueError("Selected eyebrow candidate did not produce an atlas.")

    unity_path = unity_dir / (args.unity_mask_id + ".png")
    save(unity_path, selected_atlas)
    write_unity_meta(unity_path.with_suffix(".png.meta"), "e7-" + args.unity_mask_id)
    unity_resource_summaries.append(
        {
            "index": args.selected_candidate,
            "maskId": args.unity_mask_id,
            "path": format_path(repo, unity_path),
            "sha256": sha256(unity_path),
            "aliasOf": f"eyebrow-hair-atlas-{args.selected_candidate}-v1",
        }
    )
    unity_boundary_path = unity_dir / "eyebrow-boundary-mask-v1.png"
    unity_boundary_summary: dict[str, object] = {
        "maskId": "eyebrow-boundary-mask-v1",
        "path": "not_generated",
        "sha256": "not_generated",
        "channelPacking": {
            "r": "hard final eyebrow fill boundary",
            "g": "soft feather for color and strands",
            "b": "wider cleanup band for skin-color outer brow cleanup",
            "a": "same wider cleanup band",
        },
    }
    if face_image is not None and boundary_summary is not None:
        boundary_texture = make_face_local_boundary_texture(face_image, boundary_summary)
        save(unity_boundary_path, boundary_texture)
        write_unity_meta(unity_boundary_path.with_suffix(".png.meta"), "e7-eyebrow-boundary-mask-v1")
        save(output_dir / "eyebrow_boundary_face_local_v10_runtime_y_aligned_cleanup_rgba.png", boundary_texture)
        preview_r, preview_g, preview_b, _ = boundary_texture.split()
        save(
            output_dir / "eyebrow_boundary_face_local_v10_runtime_y_aligned_cleanup_preview.png",
            Image.merge("RGB", (preview_r, preview_g, preview_b)),
        )
        unity_boundary_summary["path"] = format_path(repo, unity_boundary_path)
        unity_boundary_summary["sha256"] = sha256(unity_boundary_path)

    contact_sheet_path = output_dir / "eyebrow_candidate_atlas_contact_sheet.png"
    save(contact_sheet_path, make_candidate_contact_sheet(contact_images))
    preview_sheet_path = preview_dir / "eyebrow_candidate_preview_sheet.png"
    if preview_images:
        save(preview_sheet_path, make_preview_sheet(preview_images))
    selected_color_sheet_path = preview_dir / "eyebrow_selected_mask_color_variants_review_sheet.png"
    all_color_sheet_path = preview_dir / "eyebrow_all_masks_color_variants_review_sheet.png"
    selected_color_images: list[tuple[str, Image.Image]] = []
    color_variant_images: list[tuple[str, Image.Image]] = []
    if face_image is not None and boundary_summary is not None:
        for candidate_index, atlas, hair in candidate_artifacts:
            for color_name, color_rgb, tone_lift in EYEBROW_COLOR_PRESETS:
                rendered = overlay_candidate(
                    face_image,
                    atlas,
                    hair,
                    boundary_summary,
                    brow_color=color_rgb,
                    tone_lift=tone_lift,
                )
                label = f"Brow {candidate_index} / {color_name}"
                color_variant_images.append((label, rendered))
                if candidate_index == args.selected_candidate:
                    selected_color_images.append((label, rendered))
        if selected_color_images:
            save(selected_color_sheet_path, make_brow_crop_sheet(selected_color_images, columns=5))
        if color_variant_images:
            save(all_color_sheet_path, make_brow_crop_sheet(color_variant_images, columns=5))

    green_evidence_eligible = face_summary.get("status") == "copied_full_face"
    summary: dict[str, object] = {
        "textureSetId": "eyebrow-validation-v1",
        "unityMaskId": args.unity_mask_id,
        "selectedCandidate": args.selected_candidate,
        "selectionPolicy": "selected_candidate_5_after_boundary_preview_for_softer_natural_density",
        "sourceAssets": {
            "face": face_summary,
            "canonicalPsd": psd_summary,
            "fallbackAttachmentStrip": fallback_summary,
        },
        "eyebrowBoundary": boundary_summary
        if boundary_summary is not None
        else {
            "id": "eyebrow-boundary-v1",
            "status": "not_generated",
            "reason": "face source missing",
        },
        "eyebrowBoundaryOverlayPath": format_path(repo, boundary_overlay_path)
        if face_image is not None
        else "not_generated",
        "eyebrowBoundaryMaskPath": format_path(repo, boundary_mask_path)
        if face_image is not None
        else "not_generated",
        "eyebrowBoundarySummaryPath": format_path(repo, boundary_summary_path)
        if face_image is not None
        else "not_generated",
        "candidateSummaries": candidate_summaries,
        "unityResourceCandidates": unity_resource_summaries,
        "unityResourcePath": format_path(repo, unity_path),
        "unityResourceSha256": sha256(unity_path),
        "unityBoundaryResource": unity_boundary_summary,
        "contactSheetPath": format_path(repo, contact_sheet_path),
        "previewSheetPath": format_path(repo, preview_sheet_path) if preview_images else "not_generated",
        "selectedColorVariantSheetPath": format_path(repo, selected_color_sheet_path)
        if selected_color_images
        else "not_generated",
        "allMaskColorVariantSheetPath": format_path(repo, all_color_sheet_path)
        if color_variant_images
        else "not_generated",
        "previewTargetRule": (
            "Prefer "
            + str(face_path)
            + "; fallback thumbnail is not Green-eligible."
        ),
        "wrongTargetGuard": "No preview output is generated from the blush screenshot.",
        "atlasChannels": {
            "r": "shape coverage",
            "g": "hair strand density",
            "b": "tint fill density",
            "a": "soft neutralizer edge guide",
        },
        "boundaryChannelPacking": unity_boundary_summary["channelPacking"],
        "commercialCleanupModel": (
            "Skin-color cleanup is applied only around the outside of the final brow boundary; "
            "tint and strand layers are clipped inside eyebrow-boundary-mask-v1."
        ),
        "greenEvidenceEligible": green_evidence_eligible,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_summary_md(output_dir / "summary.md", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
