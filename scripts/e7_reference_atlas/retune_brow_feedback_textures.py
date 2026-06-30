#!/usr/bin/env python3
"""Retune existing Unity-ready brow textures from device QA feedback."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")


FLAT_TARGETS = {
    "brow-png-dailyflat-hair-v1": ((96, 98, 212, 132), (300, 98, 416, 132), 0.58),
    "brow-png-dailyflat-sharp-v1": ((99, 100, 209, 129), (303, 100, 413, 129), 0.54),
    "brow-png-dailyflat-multiply-v1": ((99, 100, 209, 129), (303, 100, 413, 129), 0.54),
}

FLAT_SOURCE_TEXTURES = {
    "brow-png-dailyflat-hair-v1": "brow-png-daily-hair-v1",
    "brow-png-dailyflat-sharp-v1": "brow-png-narrow-hair-v1",
    "brow-png-dailyflat-multiply-v1": "brow-png-narrow-hair-v1",
}

HAIR_TEXTURES = (
    "brow-png-daily-hair-v1",
    "brow-png-natural-hair-v1",
    "brow-png-narrow-hair-v1",
    "brow-png-lightbrown-hair-v1",
)

PROCEDURAL_VISIBILITY_BOOSTS = {
    "brow-back-arch-soft-mix-v1": (1.7, 8),
    "brow-slim-tail-fine-hair-v1": (1.08, 4),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retune Unity-ready brow textures.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--scope",
        choices=("flat", "all"),
        default="flat",
        help="Default flat scope avoids cumulative retuning of already-softened hair textures.",
    )
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def bbox_for(active: np.ndarray) -> tuple[int, int, int, int] | None:
    rows, cols = np.nonzero(active)
    if len(cols) == 0:
        return None

    return int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1


def side_crop(image: Image.Image, side: str) -> Image.Image:
    rgba = np.asarray(image.convert("RGBA"))
    red = rgba[:, :, 0]
    if side == "left":
        active = red[:, :256] > 8
        x_offset = 0
    else:
        active = red[:, 256:] > 8
        x_offset = 256

    bbox = bbox_for(active)
    if bbox is None:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

    left, top, right, bottom = bbox
    pad_x = 3
    pad_y = 2
    left = max(0, left + x_offset - pad_x)
    right = min(image.width, right + x_offset + pad_x)
    top = max(0, top - pad_y)
    bottom = min(image.height, bottom + pad_y)
    return image.crop((left, top, right, bottom))


def blur_luma(values: np.ndarray, radius: float) -> np.ndarray:
    source = Image.fromarray(np.clip(values, 0, 255).astype(np.uint8), "L")
    return np.asarray(source.filter(ImageFilter.GaussianBlur(radius=radius)), dtype=np.float32)


def retune_flat_crop(crop: Image.Image, size: tuple[int, int], detail_scale: float) -> Image.Image:
    resized = crop.resize(size, Image.Resampling.LANCZOS)
    rgba = np.asarray(resized.convert("RGBA"), dtype=np.float32)
    red = rgba[:, :, 0]
    blue = rgba[:, :, 2]
    shape_seed = Image.fromarray(np.clip(red, 0, 255).astype(np.uint8), "L")
    shape = np.asarray(
        shape_seed.filter(ImageFilter.MaxFilter(size=5)).filter(ImageFilter.GaussianBlur(radius=1.05)),
        dtype=np.float32,
    )
    shape = np.maximum(shape * 0.88, red * 0.72)
    detail = blur_luma(blue, 0.70) * detail_scale + shape * 0.22

    output = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    output[:, :, 0] = np.clip(shape, 0, 255).astype(np.uint8)
    output[:, :, 1] = output[:, :, 0]
    output[:, :, 2] = np.clip(detail, 0, 255).astype(np.uint8)
    output[:, :, 3] = output[:, :, 0]
    return Image.fromarray(output, "RGBA")


def retune_flat(path: Path, left_target: tuple[int, int, int, int], right_target: tuple[int, int, int, int], detail_scale: float) -> None:
    source = Image.open(path).convert("RGBA")
    output = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for side, target in (("left", left_target), ("right", right_target)):
        left, top, right, bottom = target
        crop = side_crop(source, side)
        tuned = retune_flat_crop(crop, (right - left, bottom - top), detail_scale)
        output.alpha_composite(tuned, dest=(left, top))

    output.save(path)


def remap_flat_to_hair_response(path: Path) -> None:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.float32)
    red = rgba[:, :, 0]
    blue = rgba[:, :, 2]
    soft_detail = blur_luma(blue, 1.15)

    alpha = np.clip(blue * 2.2 + soft_detail * 0.18 + red * 0.10, 0, 255)
    detail = np.clip(blue * 1.25 + soft_detail * 0.32, 0, 255)
    active = red > 0
    rgba[:, :, 0] = np.where(active, alpha, 0)
    rgba[:, :, 1] = rgba[:, :, 0]
    rgba[:, :, 2] = np.where(active, detail, 0)
    rgba[:, :, 3] = rgba[:, :, 0]
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(path)


def retune_flat_from_hair_crop(crop: Image.Image, size: tuple[int, int]) -> Image.Image:
    resized = crop.resize(size, Image.Resampling.LANCZOS)
    rgba = np.asarray(resized.convert("RGBA"), dtype=np.float32)
    red = rgba[:, :, 0]
    blue = rgba[:, :, 2]
    height = max(1, red.shape[0])
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    bottom_edge = np.clip((y - 0.68) / 0.32, 0.0, 1.0)
    edge_trim = 1.0 - bottom_edge * 0.40

    alpha = np.clip(red * 0.94 * edge_trim + blue * 0.10, 0, 255)
    detail = np.clip(blue * 0.98 * edge_trim + red * 0.08, 0, 255)

    output = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    output[:, :, 0] = alpha.astype(np.uint8)
    output[:, :, 1] = output[:, :, 0]
    output[:, :, 2] = detail.astype(np.uint8)
    output[:, :, 3] = output[:, :, 0]
    return Image.fromarray(output, "RGBA")


def retune_flat_from_hair_texture(
    path: Path,
    source_path: Path,
    left_target: tuple[int, int, int, int],
    right_target: tuple[int, int, int, int],
) -> None:
    source = Image.open(source_path).convert("RGBA")
    output = Image.new("RGBA", source.size, (0, 0, 0, 0))
    for side, target in (("left", left_target), ("right", right_target)):
        left, top, right, bottom = target
        crop = side_crop(source, side)
        tuned = retune_flat_from_hair_crop(crop, (right - left, bottom - top))
        output.alpha_composite(tuned, dest=(left, top))

    output.save(path)


def soften_hair_detail(path: Path) -> None:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.float32)
    red = rgba[:, :, 0]
    blue = rgba[:, :, 2]
    softened_blue = blur_luma(blue, 0.75) * 0.56 + blur_luma(red, 0.45) * 0.22
    rgba[:, :, 2] = np.clip(softened_blue, 0, 255)
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(path)


def boost_procedural(path: Path, scale: float, lift: int) -> None:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.float32)
    active = rgba[:, :, 0] > 0
    for channel in (0, 1, 2, 3):
        values = rgba[:, :, channel]
        values[active] = np.clip(values[active] * scale + lift, 0, 255)
        rgba[:, :, channel] = values

    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)


def soften_soft_flat_top_edge(path: Path) -> None:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image, dtype=np.float32)
    red = rgba[:, :, 0]
    strong_threshold = 32

    for x_start, x_end in ((0, 256), (256, image.width)):
        active = red[:, x_start:x_end] > strong_threshold
        bbox = bbox_for(active)
        if bbox is None:
            continue

        left, _top, right, _bottom = bbox
        columns = [
            x_start + x
            for x in range(left, right)
            if np.any(red[:, x_start + x] > strong_threshold)
        ]
        if not columns:
            continue

        center_start = (len(columns) * 2) // 5
        center_end = max(center_start + 1, (len(columns) * 3) // 5)
        for x in columns[center_start:center_end]:
            rows = np.nonzero(red[:, x] > strong_threshold)[0]
            if len(rows) == 0:
                continue

            y = rows[0]
            rgba[y, x, :] = np.minimum(rgba[y, x, :], 30)

    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(path)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    mask_dir = resolve(repo, MASK_DIR)

    for texture_id, (left_target, right_target, _detail_scale) in FLAT_TARGETS.items():
        path = mask_dir / f"{texture_id}.png"
        source_path = mask_dir / f"{FLAT_SOURCE_TEXTURES[texture_id]}.png"
        retune_flat_from_hair_texture(path, source_path, left_target, right_target)
        print(f"retuned_flat_brow path={path.relative_to(repo).as_posix()}")

    if args.scope != "all":
        return

    for texture_id in HAIR_TEXTURES:
        soften_hair_detail(mask_dir / f"{texture_id}.png")
        print(f"softened_brow_hair_detail path={(mask_dir / f'{texture_id}.png').relative_to(repo).as_posix()}")

    for texture_id, (scale, lift) in PROCEDURAL_VISIBILITY_BOOSTS.items():
        path = mask_dir / f"{texture_id}.png"
        boost_procedural(path, scale, lift)
        if texture_id == "brow-back-arch-soft-mix-v1":
            soften_soft_flat_top_edge(path)
        print(f"boosted_procedural_brow path={path.relative_to(repo).as_posix()}")


if __name__ == "__main__":
    main()
