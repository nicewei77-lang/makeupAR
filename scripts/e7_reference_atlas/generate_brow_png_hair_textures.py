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
    detail_blur: float = 0.28
    shape_filter_size: int = 5
    shape_blur: float = 1.15
    shape_detail_floor: float = 0.24
    final_blur: float = 0.18
    left_source_region: tuple[float, float, float, float] | None = None
    right_source_region: tuple[float, float, float, float] | None = None
    fill_vertical_gaps: bool = False
    vertical_fill_strength: float = 0.72


CONFIGS = {
    "dailyflat": BrowTextureConfig(
        "dailyflat",
        "brow-png-dailyflat-hair-v1",
        (80, 96, 224, 135),
        (288, 96, 432, 135),
        left_source_region=(0.055, 0.405, 0.390, 0.545),
        right_source_region=(0.600, 0.405, 0.925, 0.545),
    ),
    "dailyflatsharp": BrowTextureConfig(
        "dailyflat",
        "brow-png-dailyflat-sharp-v1",
        (84, 98, 226, 132),
        (286, 98, 428, 132),
        left_source_region=(0.055, 0.405, 0.390, 0.545),
        right_source_region=(0.600, 0.405, 0.925, 0.545),
    ),
    "dailyflatmultiply": BrowTextureConfig(
        "dailyflat",
        "brow-png-dailyflat-multiply-v1",
        (84, 98, 226, 132),
        (286, 98, 428, 132),
        left_source_region=(0.055, 0.405, 0.390, 0.545),
        right_source_region=(0.600, 0.405, 0.925, 0.545),
    ),
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
        + ", ".join(sorted({config.source_key for config in CONFIGS.values()})),
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Optional output config key to generate. Repeat for multiple keys.",
    )
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args()


def parse_sources(values: list[str], selected_configs: dict[str, BrowTextureConfig]) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected --source key=/path.png, got: {value}")

        key, path = value.split("=", 1)
        key = key.strip()
        valid_source_keys = {config.source_key for config in CONFIGS.values()}
        if key not in valid_source_keys:
            raise ValueError(f"Unsupported source key: {key}")

        sources[key] = Path(path).expanduser()

    required_source_keys = {config.source_key for config in selected_configs.values()}
    missing = sorted(required_source_keys - set(sources.keys()))
    if missing:
        raise ValueError("Missing brow PNG sources: " + ", ".join(missing))

    return sources


def select_configs(keys: list[str]) -> dict[str, BrowTextureConfig]:
    if not keys:
        return CONFIGS

    selected: dict[str, BrowTextureConfig] = {}
    for key in keys:
        if key not in CONFIGS:
            raise ValueError(f"Unsupported output config key: {key}")

        selected[key] = CONFIGS[key]

    return selected


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


def largest_component_bbox(active: np.ndarray) -> tuple[int, int, int, int] | None:
    height, width = active.shape
    visited = np.zeros(active.shape, dtype=bool)
    best_pixels: list[tuple[int, int]] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    rows, cols = np.nonzero(active)

    for start_y, start_x in zip(rows.tolist(), cols.tolist()):
        if visited[start_y, start_x]:
            continue

        stack = [(start_y, start_x)]
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []

        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for dy, dx in neighbors:
                next_y = y + dy
                next_x = x + dx
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and active[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))

        if len(pixels) > len(best_pixels):
            best_pixels = pixels

    if not best_pixels:
        return None

    ys, xs = zip(*best_pixels)
    return int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1


def component_bboxes(active: np.ndarray) -> list[tuple[int, tuple[int, int, int, int]]]:
    height, width = active.shape
    visited = np.zeros(active.shape, dtype=bool)
    components: list[tuple[int, tuple[int, int, int, int]]] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    rows, cols = np.nonzero(active)

    for start_y, start_x in zip(rows.tolist(), cols.tolist()):
        if visited[start_y, start_x]:
            continue

        stack = [(start_y, start_x)]
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []

        while stack:
            y, x = stack.pop()
            pixels.append((y, x))
            for dy, dx in neighbors:
                next_y = y + dy
                next_x = x + dx
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and active[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    stack.append((next_y, next_x))

        ys, xs = zip(*pixels)
        components.append(
            (
                len(pixels),
                (int(min(xs)), int(min(ys)), int(max(xs)) + 1, int(max(ys)) + 1),
            )
        )

    return components


def brow_component_bbox(active: np.ndarray) -> tuple[int, int, int, int] | None:
    components = component_bboxes(active)
    strong: list[tuple[int, tuple[int, int, int, int]]] = []
    for pixels, bbox in components:
        left, top, right, bottom = bbox
        width = right - left
        height = max(1, bottom - top)
        aspect = width / height
        if pixels >= 80 and width >= 45 and aspect >= 1.25:
            strong.append((pixels, bbox))

    if not strong:
        return largest_component_bbox(active)

    union_left = min(bbox[0] for _, bbox in strong)
    union_top = min(bbox[1] for _, bbox in strong)
    union_right = max(bbox[2] for _, bbox in strong)
    union_bottom = max(bbox[3] for _, bbox in strong)

    for pixels, bbox in components:
        if (pixels, bbox) in strong or pixels < 10:
            continue

        left, top, right, bottom = bbox
        center_y = (top + bottom) * 0.5
        vertical_match = union_top - 42 <= center_y <= union_bottom + 42
        horizontal_gap = max(union_left - right, left - union_right, 0)
        if vertical_match and horizontal_gap <= 90:
            union_left = min(union_left, left)
            union_top = min(union_top, top)
            union_right = max(union_right, right)
            union_bottom = max(union_bottom, bottom)

    return union_left, union_top, union_right, union_bottom


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
    light = np.clip(fine - local, 0.0, 1.0)
    foreground = np.clip(fine - np.percentile(gray, 12.0), 0.0, 1.0)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    warmth = np.clip(rgb[:, :, 0] - rgb[:, :, 2], 0.0, 1.0)
    score = (
        dark * 1.10
        + light * 1.18
        + detail * 0.82
        + foreground * 0.28
        + saturation * 0.42
        + warmth * 0.18
    )
    alpha = normalize_score(score)
    return alpha, score


def fill_vertical_gaps(alpha_crop: np.ndarray, fill_strength: float) -> np.ndarray:
    filled = np.zeros_like(alpha_crop, dtype=np.float32)
    height, width = alpha_crop.shape

    for x in range(width):
        column = alpha_crop[:, x]
        peak = float(column.max())
        if peak < 0.08:
            continue

        active_rows = np.flatnonzero(column >= max(0.05, peak * 0.20))
        if len(active_rows) < 2:
            continue

        top = int(active_rows.min())
        bottom = int(active_rows.max()) + 1
        if bottom - top < 2:
            continue

        filled[top:bottom, x] = max(filled[top:bottom, x].max(), peak * fill_strength)

    if width > 2:
        for x in range(1, width - 1):
            if filled[:, x].max() > 0:
                continue

            neighbor = np.maximum(filled[:, x - 1], filled[:, x + 1]) * 0.55
            filled[:, x] = np.maximum(filled[:, x], neighbor)

    return np.clip(filled, 0.0, 1.0)


def extract_brow_side(source: Image.Image, side: str, config: BrowTextureConfig) -> Image.Image:
    width, height = source.size
    source_region = config.left_source_region if side == "left" else config.right_source_region
    if source_region is not None:
        x0 = int(width * source_region[0])
        y0 = int(height * source_region[1])
        x1 = int(width * source_region[2])
        y1 = int(height * source_region[3])
    elif side == "left":
        y0 = int(height * 0.30)
        y1 = int(height * 0.63)
        x0, x1 = 0, int(width * 0.50)
    else:
        y0 = int(height * 0.30)
        y1 = int(height * 0.63)
        x0, x1 = int(width * 0.50), width

    rough = source.crop((x0, y0, x1, y1))
    alpha, score = score_hair_pixels(rough)
    threshold = max(float(np.percentile(score, 98.25)), 0.018)
    active = score >= threshold
    bbox = brow_component_bbox(active)
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
    if config.detail_blur > 0:
        detail = detail.filter(ImageFilter.GaussianBlur(radius=config.detail_blur))

    shape_seed = detail
    if config.fill_vertical_gaps:
        filled_alpha = fill_vertical_gaps(alpha_crop, config.vertical_fill_strength)
        filled_detail = Image.fromarray(
            np.clip(filled_alpha * 255.0, 0, 255).astype(np.uint8),
            "L",
        ).filter(ImageFilter.GaussianBlur(radius=2.35))
        shape_seed = filled_detail

    shape = shape_seed.filter(ImageFilter.MaxFilter(size=config.shape_filter_size))
    if config.shape_blur > 0:
        shape = shape.filter(ImageFilter.GaussianBlur(radius=config.shape_blur))

    detail_values = np.asarray(detail, dtype=np.uint8)
    shape_values = np.asarray(shape, dtype=np.uint8)
    rgba = np.zeros((shape_values.shape[0], shape_values.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0] = shape_values
    rgba[:, :, 1] = shape_values
    rgba[:, :, 2] = np.maximum(
        detail_values,
        (shape_values.astype(np.float32) * config.shape_detail_floor).astype(np.uint8),
    )
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
    paste_resized(atlas, extract_brow_side(source, "left", config), config.left_target)
    paste_resized(atlas, extract_brow_side(source, "right", config), config.right_target)
    if config.final_blur > 0:
        return atlas.filter(ImageFilter.GaussianBlur(radius=config.final_blur))

    return atlas


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    selected_configs = select_configs(args.only)
    sources = parse_sources(args.source, selected_configs)
    output_dir = resolve(repo, MASK_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    for key, config in selected_configs.items():
        output = output_dir / f"{config.mask_texture_id}.png"
        image = build_texture(config, sources[config.source_key], args.resolution)
        image.save(output)
        print(f"generated_brow_png_hair_texture key={key} path={output.relative_to(repo).as_posix()}")


if __name__ == "__main__":
    main()
