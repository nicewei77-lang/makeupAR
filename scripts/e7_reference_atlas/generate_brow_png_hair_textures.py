#!/usr/bin/env python3
"""Convert user-authored brow PNGs into Unity-ready alpha/detail textures."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")


@dataclass(frozen=True)
class BrowTextureConfig:
    source_key: str
    mask_texture_id: str
    left_target: tuple[int, int, int, int]
    right_target: tuple[int, int, int, int]


CONFIGS = {
    "daily": BrowTextureConfig(
        "daily",
        "brow-png-daily-hair-v1",
        (100, 96, 240, 135),
        (272, 96, 412, 135),
    ),
    "natural": BrowTextureConfig(
        "natural",
        "brow-png-natural-hair-v1",
        (104, 98, 238, 134),
        (274, 98, 408, 134),
    ),
    "narrow": BrowTextureConfig(
        "narrow",
        "brow-png-narrow-hair-v1",
        (106, 101, 236, 130),
        (276, 101, 406, 130),
    ),
    "lightbrown": BrowTextureConfig(
        "lightbrown",
        "brow-png-lightbrown-hair-v1",
        (104, 100, 240, 132),
        (272, 100, 408, 132),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Unity brow PNG hair alpha/detail textures."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source mapping in key=/absolute/path.png form. Keys: "
        + ", ".join(CONFIGS.keys()),
    )
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args()


def parse_sources(values: list[str]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected --source key=/path.png, got: {value}")

        key, path = value.split("=", 1)
        key = key.strip()
        if key not in CONFIGS:
            raise ValueError(f"Unsupported source key: {key}")

        sources[key] = Path(path).expanduser()

    missing = sorted(set(CONFIGS.keys()) - set(sources.keys()))
    if missing:
        raise ValueError("Missing brow PNG sources: " + ", ".join(missing))

    return sources


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def luminance(rgb: np.ndarray) -> np.ndarray:
    return rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152 + rgb[:, :, 2] * 0.0722


def blur_array(values: np.ndarray, radius: float) -> np.ndarray:
    image = Image.fromarray(np.clip(values * 255.0, 0, 255).astype(np.uint8), "L")
    blurred = image.filter(ImageFilter.GaussianBlur(radius=radius))
    return np.asarray(blurred, dtype=np.float32) / 255.0


def bbox_for(active: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(active)
    if len(xs) == 0:
        return None

    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def expand_bbox(
    bbox: tuple[int, int, int, int],
    width: int,
    height: int,
    pad_x: int,
    pad_y: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x),
        min(height, bottom + pad_y),
    )


def normalize_score(score: np.ndarray) -> np.ndarray:
    lower = float(np.percentile(score, 82.0))
    upper = float(np.percentile(score, 99.72))
    if upper <= lower:
        upper = lower + 0.001

    return np.clip((score - lower) / (upper - lower), 0.0, 1.0)


def score_hair_pixels(crop: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    rgb = np.asarray(crop.convert("RGB"), dtype=np.float32) / 255.0
    gray = luminance(rgb)
    local = blur_array(gray, radius=16.0)
    fine = blur_array(gray, radius=1.4)
    detail = np.abs(fine - local)
    dark = np.clip(local - fine, 0.0, 1.0)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    warmth = np.clip(rgb[:, :, 0] - rgb[:, :, 2], 0.0, 1.0)
    score = dark * 1.18 + detail * 0.76 + saturation * 0.42 + warmth * 0.18
    alpha = normalize_score(score)
    return alpha, score


def extract_brow_side(source: Image.Image, side: str) -> Image.Image:
    width, height = source.size
    y0 = int(height * 0.30)
    y1 = int(height * 0.63)
    if side == "left":
        x0, x1 = 0, int(width * 0.50)
    else:
        x0, x1 = int(width * 0.50), width

    rough = source.crop((x0, y0, x1, y1))
    alpha, score = score_hair_pixels(rough)
    threshold = max(float(np.percentile(score, 98.25)), 0.018)
    active = score >= threshold
    bbox = bbox_for(active)
    if bbox is None:
        bbox = (0, 0, rough.size[0], rough.size[1])

    bbox = expand_bbox(
        bbox,
        rough.size[0],
        rough.size[1],
        pad_x=max(10, rough.size[0] // 80),
        pad_y=max(6, rough.size[1] // 30),
    )
    alpha_crop = alpha[bbox[1] : bbox[3], bbox[0] : bbox[2]]
    detail = Image.fromarray(np.clip(alpha_crop * 255.0, 0, 255).astype(np.uint8), "L")
    detail = detail.filter(ImageFilter.GaussianBlur(radius=0.28))
    shape = detail.filter(ImageFilter.MaxFilter(size=5)).filter(
        ImageFilter.GaussianBlur(radius=1.15)
    )

    detail_values = np.asarray(detail, dtype=np.uint8)
    shape_values = np.asarray(shape, dtype=np.uint8)
    rgba = np.zeros((shape_values.shape[0], shape_values.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0] = shape_values
    rgba[:, :, 1] = shape_values
    rgba[:, :, 2] = np.maximum(detail_values, (shape_values.astype(np.float32) * 0.24).astype(np.uint8))
    rgba[:, :, 3] = shape_values
    return Image.fromarray(rgba, "RGBA")


def paste_resized(
    atlas: Image.Image,
    source: Image.Image,
    target: tuple[int, int, int, int],
) -> None:
    left, top, right, bottom = target
    resized = source.resize((right - left, bottom - top), Image.Resampling.LANCZOS)
    atlas.alpha_composite(resized, dest=(left, top))


def build_texture(config: BrowTextureConfig, source_path: Path, resolution: int) -> Image.Image:
    source = Image.open(source_path).convert("RGB")
    atlas = Image.new("RGBA", (resolution, resolution), (0, 0, 0, 0))
    paste_resized(atlas, extract_brow_side(source, "left"), config.left_target)
    paste_resized(atlas, extract_brow_side(source, "right"), config.right_target)
    return atlas.filter(ImageFilter.GaussianBlur(radius=0.18))


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    sources = parse_sources(args.source)
    output_dir = resolve(repo, MASK_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, config in CONFIGS.items():
        output = output_dir / f"{config.mask_texture_id}.png"
        image = build_texture(config, sources[key], args.resolution)
        image.save(output)
        print(f"generated_brow_png_hair_texture key={key} path={output.relative_to(repo).as_posix()}")


if __name__ == "__main__":
    main()
