#!/usr/bin/env python3
"""Build experimental Unity tint masks from the ARCore canonical-face PSD layers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_INPUT_DIR = Path(
    "evidence/asset-inputs/ARCore_canonical_face_texture_1_extracted/full-canvas"
)
DEFAULT_OUTPUT_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)
DEFAULT_EVIDENCE_DIR = Path(
    "evidence/asset-inputs/ARCore_canonical_face_texture_1_runtime"
)
RESOLUTION = 512

PSD_ARCORE_LIP_STYLE_ID = "psd-arcore-lip-style-v1"
PSD_ARCORE_LIP_MASK_ID = "psd-arcore-lip-mask-v1"
PSD_ARCORE_CHEEK_ID = "psd-arcore-cheek-undereye-v1"
PSD_ARCORE_CHEEK_TEXTURE_IDS = {
    "cheek_undereye": "psd-arcore-cheek-undereye-v1",
    "cheek_asia_z": "psd-arcore-cheek-asia-z-v1",
    "cheek_sunkissed": "psd-arcore-cheek-sunkissed-v1",
    "cheek_daily_oval": "psd-arcore-cheek-daily-oval-v1",
    "cheek_undereye2": "psd-arcore-cheek-undereye2-v1",
    "cheek_lovely_round": "psd-arcore-cheek-lovely-round-v1",
    "cheek_lifted_diagonal": "psd-arcore-cheek-lifted-diagonal-v1",
}
PSD_ARCORE_BROW_ID = "psd-arcore-brow-semi-arch-v1"

SOURCE_LAYER_FILES = {
    "lip_full": ("root_lip_full_color_or_mask.png",),
    "lip_gradient": ("root_lip_gradient_density.png",),
    "lip_gloss": ("root_lip_gloss_highlight_gloss_highlight.png",),
    "cheek_left": ("root_blush_undereye_left.png",),
    "cheek_right": ("root_blush_undereye_right.png",),
    "cheek_single": (
        "root_blush_undereye_all.png",
        "root_blush_undereye_undereye.png",
        "root_blush_sunkissed_레이어_5.png",
    ),
    "cheek_undereye": ("root_blush_undereye_all.png",),
    "cheek_asia_z": ("root_blush_asia-z_all.png",),
    "cheek_sunkissed": ("root_blush_sunkissed_all.png",),
    "cheek_daily_oval": ("root_blush_daily-oval_all.png",),
    "cheek_undereye2": ("root_blush_undereye2_all.png",),
    "cheek_lovely_round": ("root_blush_lovely_round_all.png",),
    "cheek_lifted_diagonal": ("root_blush_lifted-diagonal_all.png",),
    "brow_left": ("root_eyebrow_semi-arch_left.png",),
    "brow_right": ("root_eyebrow_semi-arch_right.png",),
    "brow_left_full": ("root_eyebrow_semi-arch_left-full.png",),
    "brow_right_full": ("root_eyebrow_semi-arch_right-full.png",),
    "brow_left_gradient": (
        "root_eyebrow_semi-arch_left-gradient.png",
        "root_eyebrow_semi-arch_right-gradient_복사.png",
    ),
    "brow_right_gradient": ("root_eyebrow_semi-arch_right-gradient.png",),
}

# MediaPipe FaceMesh canonical eyebrow landmarks, mapped through canonical
# face-model vertex UVs into this 512x512 top-left-origin texture canvas.
MEDIAPIPE_TEXTURE_LEFT_BROW_LANDMARKS = (
    (70, 0.229625, 0.299585),
    (63, 0.277177, 0.271927),
    (105, 0.327564, 0.256441),
    (66, 0.382472, 0.255138),
    (107, 0.441869, 0.261727),
    (46, 0.257040, 0.314377),
    (53, 0.296716, 0.293245),
    (52, 0.337929, 0.282769),
    (65, 0.385428, 0.281379),
    (55, 0.447580, 0.302467),
)
MEDIAPIPE_TEXTURE_RIGHT_BROW_LANDMARKS = (
    (296, 0.617528, 0.255138),
    (334, 0.672436, 0.256538),
    (293, 0.722823, 0.271927),
    (300, 0.770375, 0.299585),
    (336, 0.558131, 0.261727),
    (285, 0.552420, 0.302467),
    (295, 0.614572, 0.281379),
    (282, 0.662137, 0.282919),
    (283, 0.703284, 0.293245),
    (276, 0.742960, 0.314377),
)
MEDIAPIPE_BROW_TARGET_PAD_X = 18
MEDIAPIPE_BROW_TARGET_PAD_Y = 8


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PSD ARCore makeup masks.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def tint_mask_from_png(path: Path) -> Image.Image:
    require(path.exists(), f"Missing PSD extracted layer: {path}")
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.uint8)
    alpha = rgba[:, :, 3]
    luminance = (
        rgba[:, :, 0].astype(np.float32) * 0.299
        + rgba[:, :, 1].astype(np.float32) * 0.587
        + rgba[:, :, 2].astype(np.float32) * 0.114
    ).astype(np.uint8)
    # PSD white/gray artwork is a tintable coverage mask, not baked makeup color.
    return array_to_channel(np.minimum(alpha, luminance))


def channel_to_array(channel: Image.Image) -> np.ndarray:
    return np.asarray(channel, dtype=np.uint8)


def array_to_channel(values: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(values, 0, 255).astype(np.uint8), mode="L")


def max_channels(*channels: Image.Image) -> Image.Image:
    arrays = [channel_to_array(channel) for channel in channels]
    return array_to_channel(np.maximum.reduce(arrays))


def scale_channel(channel: Image.Image, amount: float) -> Image.Image:
    values = channel_to_array(channel).astype(np.float32) * amount
    return array_to_channel(values)


def bbox_for(channel: Image.Image, threshold: int = 8) -> tuple[int, int, int, int]:
    values = channel_to_array(channel)
    rows, cols = np.nonzero(values > threshold)
    require(len(cols) > 0, "Channel has no active pixels.")
    return int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())


def target_bbox(mask_dir: Path, reference_name: str) -> tuple[int, int, int, int]:
    reference = Image.open(mask_dir / reference_name).convert("RGBA")
    return bbox_for(reference.getchannel("R"))


def side_bboxes(channel: Image.Image) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    values = channel_to_array(channel)
    left = array_to_channel(values[:, : RESOLUTION // 2])
    right = array_to_channel(values[:, RESOLUTION // 2 :])
    lx0, ly0, lx1, ly1 = bbox_for(left)
    rx0, ry0, rx1, ry1 = bbox_for(right)
    return (
        (lx0, ly0, lx1, ly1),
        (rx0 + RESOLUTION // 2, ry0, rx1 + RESOLUTION // 2, ry1),
    )


def target_side_bboxes(
    mask_dir: Path,
    reference_name: str,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    reference = Image.open(mask_dir / reference_name).convert("RGBA")
    return side_bboxes(reference.getchannel("R"))


def fit_channel_to_bbox(
    channel: Image.Image,
    source_bbox: tuple[int, int, int, int],
    target: tuple[int, int, int, int],
    extra_filter: ImageFilter.Filter | None = None,
) -> Image.Image:
    sx0, sy0, sx1, sy1 = source_bbox
    tx0, ty0, tx1, ty1 = target
    cropped = channel.crop((sx0, sy0, sx1 + 1, sy1 + 1))
    resized = cropped.resize((tx1 - tx0 + 1, ty1 - ty0 + 1), Image.Resampling.LANCZOS)
    if extra_filter is not None:
        resized = resized.filter(extra_filter)
    output = Image.new("L", (RESOLUTION, RESOLUTION), 0)
    output.paste(resized, (tx0, ty0))
    return output


def fit_full_canvas_to_resolution(
    channel: Image.Image,
    extra_filter: ImageFilter.Filter | None = None,
) -> Image.Image:
    # MediaPipe/ARCore canonical full-canvas source of truth: keep the PSD
    # layer's authored UV position and only reduce the square canvas resolution.
    resized = channel.resize((RESOLUTION, RESOLUTION), Image.Resampling.LANCZOS)
    if extra_filter is not None:
        resized = resized.filter(extra_filter)
    return resized


def fit_brow_sides_to_target(
    left_channel: Image.Image,
    right_channel: Image.Image,
    left_source_bbox: tuple[int, int, int, int],
    right_source_bbox: tuple[int, int, int, int],
    left_target_bbox: tuple[int, int, int, int],
    right_target_bbox: tuple[int, int, int, int],
    extra_filter: ImageFilter.Filter | None = None,
) -> Image.Image:
    return max_channels(
        fit_channel_to_bbox(
            left_channel,
            left_source_bbox,
            left_target_bbox,
            extra_filter=extra_filter,
        ),
        fit_channel_to_bbox(
            right_channel,
            right_source_bbox,
            right_target_bbox,
            extra_filter=extra_filter,
        ),
    )


def mediapipe_landmark_bbox(
    landmarks: tuple[tuple[int, float, float], ...],
) -> tuple[int, int, int, int]:
    xs = [int(round(u * (RESOLUTION - 1))) for _, u, _ in landmarks]
    ys = [int(round(v * (RESOLUTION - 1))) for _, _, v in landmarks]
    return (
        max(0, min(xs) - MEDIAPIPE_BROW_TARGET_PAD_X),
        max(0, min(ys) - MEDIAPIPE_BROW_TARGET_PAD_Y),
        min(RESOLUTION - 1, max(xs) + MEDIAPIPE_BROW_TARGET_PAD_X),
        min(RESOLUTION - 1, max(ys) + MEDIAPIPE_BROW_TARGET_PAD_Y),
    )


def mediapipe_brow_side_bboxes() -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    return (
        mediapipe_landmark_bbox(MEDIAPIPE_TEXTURE_LEFT_BROW_LANDMARKS),
        mediapipe_landmark_bbox(MEDIAPIPE_TEXTURE_RIGHT_BROW_LANDMARKS),
    )


def make_rgba_mask(red: Image.Image, green: Image.Image | None = None, blue: Image.Image | None = None, alpha: Image.Image | None = None) -> Image.Image:
    green = red if green is None else green
    blue = red if blue is None else blue
    alpha = red if alpha is None else alpha
    return Image.merge("RGBA", (red, green, blue, alpha))


def make_brow_fiber_detail(shape: Image.Image, source_detail: Image.Image) -> Image.Image:
    shape_values = channel_to_array(shape).astype(np.float32) / 255.0
    detail_values = channel_to_array(source_detail).astype(np.float32) / 255.0
    near_detail = (
        channel_to_array(source_detail.filter(ImageFilter.GaussianBlur(radius=0.65))).astype(
            np.float32
        )
        / 255.0
    )
    broad_detail = (
        channel_to_array(source_detail.filter(ImageFilter.GaussianBlur(radius=1.8))).astype(
            np.float32
        )
        / 255.0
    )
    local_lines = np.clip((detail_values - broad_detail * 0.86) * 5.8, 0.0, 1.0)
    needle_lines = np.clip((detail_values - near_detail * 0.58) * 3.8, 0.0, 1.0)
    active_detail = detail_values[detail_values > 0.025]
    if active_detail.size:
        low = np.percentile(active_detail, 42)
        high = np.percentile(active_detail, 88)
        tonal_gate = np.clip((detail_values - low) / max(high - low, 0.0001), 0.0, 1.0)
    else:
        tonal_gate = detail_values
    line_centers = np.maximum(local_lines, needle_lines) * np.power(tonal_gate, 0.8)
    # PSD left/right brow layers are already user-drawn white hair strokes.
    # Preserve that direct stroke coverage instead of extracting only center ridges.
    direct_strokes = np.power(np.clip(detail_values * 1.18, 0.0, 1.0), 0.86)
    antialias_support = np.clip((near_detail - broad_detail * 0.52) * 1.65, 0.0, 1.0)
    stroke_lines = np.maximum.reduce(
        [
            line_centers * 0.92,
            direct_strokes * 0.84,
            antialias_support * 0.34,
        ]
    )
    shape_gate = np.power(np.clip(shape_values, 0.0, 1.0), 0.52)
    fiber = stroke_lines * shape_gate
    return array_to_channel(fiber * 255.0)


def save_with_meta(image: Image.Image, output: Path, template_meta: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    require(template_meta.exists(), f"Missing Unity meta template: {template_meta}")
    guid = hashlib.md5(f"e7-{output.stem}".encode("utf-8")).hexdigest()
    meta = template_meta.read_text(encoding="utf-8")
    meta = re.sub(r"guid: [0-9a-f]+", f"guid: {guid}", meta, count=1)
    output.with_suffix(".png.meta").write_text(meta, encoding="utf-8")


def layer_path(input_dir: Path, key: str) -> Path:
    candidates = [input_dir / filename for filename in SOURCE_LAYER_FILES[key]]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    tried = ", ".join(path.name for path in candidates)
    raise AssertionError(f"Missing PSD extracted layer for {key}; tried: {tried}")


def layer_paths(input_dir: Path, key: str) -> list[Path]:
    return [
        input_dir / filename
        for filename in SOURCE_LAYER_FILES[key]
        if (input_dir / filename).exists()
    ]


def cheek_source_for(input_dir: Path, key: str) -> Image.Image:
    paths = layer_paths(input_dir, key)
    if key == "cheek_undereye" and not paths:
        paths = [
            *layer_paths(input_dir, "cheek_left"),
            *layer_paths(input_dir, "cheek_right"),
        ]
        if not paths:
            paths = [layer_path(input_dir, "cheek_single")]
    require(paths, f"Missing PSD cheek layer for {key}.")
    return max_channels(*(tint_mask_from_png(path) for path in paths))


def make_contact_sheet(items: list[tuple[str, Image.Image]]) -> Image.Image:
    tile = 180
    label_h = 46
    cols = 4
    rows = max(1, (len(items) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(items):
        x = (index % cols) * tile
        y = (index // cols) * (tile + label_h)
        rgba = image.convert("RGBA")
        values = np.maximum.reduce(
            [
                np.asarray(rgba.getchannel(channel), dtype=np.uint8)
                for channel in ("R", "G", "B", "A")
            ]
        )
        preview = Image.new("RGBA", rgba.size, (224, 68, 126, 0))
        preview.putalpha(array_to_channel(values))
        preview.thumbnail((tile - 16, tile - 16), Image.Resampling.LANCZOS)
        checker = Image.new("RGB", (tile, tile), (255, 255, 255))
        checker.paste(
            preview,
            ((tile - preview.width) // 2, (tile - preview.height) // 2),
            preview.getchannel("A"),
        )
        sheet.paste(checker, (x, y))
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=(34, 34, 40))
        draw.text((x + 8, y + tile + 9), label[:28], fill=(255, 255, 255))
    return sheet


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    input_dir = resolve(repo, args.input_dir)
    output_dir = resolve(repo, args.output_dir)
    evidence_dir = resolve(repo, args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    lip_full_source = tint_mask_from_png(layer_path(input_dir, "lip_full"))
    lip_gradient_source = tint_mask_from_png(layer_path(input_dir, "lip_gradient"))
    lip_gloss_source = tint_mask_from_png(layer_path(input_dir, "lip_gloss"))
    lip_source_bbox = bbox_for(lip_full_source)
    lip_full = fit_full_canvas_to_resolution(lip_full_source)
    lip_gradient = fit_full_canvas_to_resolution(lip_gradient_source)
    lip_gloss = fit_full_canvas_to_resolution(lip_gloss_source)
    lip_overline = lip_full.filter(ImageFilter.MaxFilter(size=3)).filter(
        ImageFilter.GaussianBlur(radius=0.55)
    )
    lip_style = make_rgba_mask(lip_full, lip_overline, lip_gradient, lip_gloss)
    lip_mask = make_rgba_mask(lip_full)

    cheek_sources = {
        key: cheek_source_for(input_dir, key)
        for key in PSD_ARCORE_CHEEK_TEXTURE_IDS
    }
    cheek_masks = {}
    for key, texture_id in PSD_ARCORE_CHEEK_TEXTURE_IDS.items():
        cheek = fit_full_canvas_to_resolution(
            cheek_sources[key],
            extra_filter=ImageFilter.GaussianBlur(radius=0.45),
        )
        cheek_masks[texture_id] = make_rgba_mask(cheek)

    brow_left_full_source = tint_mask_from_png(layer_path(input_dir, "brow_left_full"))
    brow_right_full_source = tint_mask_from_png(layer_path(input_dir, "brow_right_full"))
    brow_left_hair_source = tint_mask_from_png(layer_path(input_dir, "brow_left"))
    brow_right_hair_source = tint_mask_from_png(layer_path(input_dir, "brow_right"))
    brow_left_gradient_source = tint_mask_from_png(layer_path(input_dir, "brow_left_gradient"))
    brow_right_gradient_source = tint_mask_from_png(layer_path(input_dir, "brow_right_gradient"))
    brow_left_source_bbox = bbox_for(
        max_channels(
            brow_left_full_source,
            brow_left_hair_source,
            brow_left_gradient_source,
        )
    )
    brow_right_source_bbox = bbox_for(
        max_channels(
            brow_right_full_source,
            brow_right_hair_source,
            brow_right_gradient_source,
        )
    )
    brow_full = max_channels(
        fit_full_canvas_to_resolution(brow_left_full_source),
        fit_full_canvas_to_resolution(brow_right_full_source),
    )
    brow_full = brow_full.filter(ImageFilter.MinFilter(size=3)).filter(
        ImageFilter.GaussianBlur(radius=0.25)
    )
    brow_powder = max_channels(
        fit_full_canvas_to_resolution(brow_left_gradient_source),
        fit_full_canvas_to_resolution(brow_right_gradient_source),
    ).filter(ImageFilter.GaussianBlur(radius=0.55))
    brow_powder = scale_channel(brow_powder, 0.56)
    brow_hair = max_channels(
        fit_full_canvas_to_resolution(brow_left_hair_source),
        fit_full_canvas_to_resolution(brow_right_hair_source),
    )
    brow_detail = make_brow_fiber_detail(brow_full, brow_hair)
    brow_alpha = max_channels(brow_full, brow_powder, brow_detail)
    # PSD brow channels are semantic: R=target full/protect core,
    # G=very light powder, B=left/right hair detail, A=diagnostic union.
    brow_mask = make_rgba_mask(brow_full, brow_powder, brow_detail, brow_alpha)

    outputs = {
        PSD_ARCORE_LIP_STYLE_ID: lip_style,
        PSD_ARCORE_LIP_MASK_ID: lip_mask,
        **cheek_masks,
        PSD_ARCORE_BROW_ID: brow_mask,
    }
    templates = {
        PSD_ARCORE_LIP_STYLE_ID: output_dir / "lip-drawn-style-atlas-v1.png.meta",
        PSD_ARCORE_LIP_MASK_ID: output_dir / "lip-drawn-mask-v1.png.meta",
        **{
            texture_id: output_dir / "cheek-drawn-mask-v1.png.meta"
            for texture_id in PSD_ARCORE_CHEEK_TEXTURE_IDS.values()
        },
        PSD_ARCORE_BROW_ID: output_dir / "brow-png-natural-hair-v1.png.meta",
    }

    summary = {
        "sourceInputDir": input_dir.relative_to(repo).as_posix(),
        "coordinateNote": "MediaPipe/ARCore canonical full-canvas source of truth: PSD layers are downsampled from their authored full-canvas UV positions into a 512x512 runtime mask. Runtime placement belongs in the MediaPipe detector bridge, not in ARKit bbox fitting.",
        "colorSemantics": "PSD white/gray pixels are tintable coverage masks; runtime makeup color comes from the RN/Unity recipe color.",
        "browChannelSemantics": "PSD brow R=full target/protect core, G=soft gradient powder, B=left/right hair detail, A=diagnostic union.",
        "sourceBboxes": {
            "lip": lip_source_bbox,
            "cheeks": {
                PSD_ARCORE_CHEEK_TEXTURE_IDS[key]: bbox_for(source)
                for key, source in cheek_sources.items()
            },
            "browLeft": brow_left_source_bbox,
            "browRight": brow_right_source_bbox,
        },
        "outputs": {},
    }
    contact_items: list[tuple[str, Image.Image]] = []
    for texture_id, image in outputs.items():
        output_path = output_dir / f"{texture_id}.png"
        save_with_meta(image, output_path, templates[texture_id])
        evidence_path = evidence_dir / f"{texture_id}.png"
        image.save(evidence_path)
        red_bbox = bbox_for(image.getchannel("R"))
        summary["outputs"][texture_id] = {
            "unityPath": output_path.relative_to(repo).as_posix(),
            "evidencePath": evidence_path.relative_to(repo).as_posix(),
            "tintableMask": True,
            "redBbox": red_bbox,
            "activePixelsGt8": int((channel_to_array(image.getchannel("R")) > 8).sum()),
        }
        contact_items.append((texture_id, image))

    sheet = make_contact_sheet(contact_items)
    sheet.save(evidence_dir / "psd_arcore_runtime_contact_sheet.png")
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("generated_psd_arcore_makeup_textures")
    for texture_id, record in summary["outputs"].items():
        print(
            f"{texture_id} path={record['unityPath']} "
            f"bbox={record['redBbox']} activePixelsGt8={record['activePixelsGt8']}"
        )


if __name__ == "__main__":
    main()
