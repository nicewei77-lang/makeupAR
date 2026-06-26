#!/usr/bin/env python3
"""Generate the in-house procedural eyebrow smooth-region mask."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_OUTPUT = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "brow-drawn-mask-v1.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate brow-drawn-mask-v1.png.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--scale", type=int, default=4)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(samples):
        t = index / float(max(samples - 1, 1))
        mt = 1.0 - t
        x = (
            mt * mt * mt * p0[0]
            + 3.0 * mt * mt * t * p1[0]
            + 3.0 * mt * t * t * p2[0]
            + t * t * t * p3[0]
        )
        y = (
            mt * mt * mt * p0[1]
            + 3.0 * mt * mt * t * p1[1]
            + 3.0 * mt * t * t * p2[1]
            + t * t * t * p3[1]
        )
        points.append((x, y))
    return points


def scaled_points(
    points: list[tuple[float, float]],
    scale: int,
) -> list[tuple[int, int]]:
    return [(round(x * scale), round(y * scale)) for x, y in points]


def draw_round_line(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    width: int,
    fill: int,
) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")
    radius = width // 2
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)


def draw_brow(
    layer: Image.Image,
    curve: list[tuple[float, float]],
    scale: int,
) -> None:
    draw = ImageDraw.Draw(layer)
    points = scaled_points(curve, scale)
    draw_round_line(draw, points, width=round(34 * scale), fill=72)
    draw_round_line(draw, points, width=round(24 * scale), fill=148)
    draw_round_line(draw, points, width=round(13 * scale), fill=245)

    upper_points = scaled_points([(x, y - 4.0) for x, y in curve[8:-8]], scale)
    draw_round_line(draw, upper_points, width=round(6 * scale), fill=255)


def build_mask(resolution: int, scale: int) -> Image.Image:
    high_resolution = resolution * scale
    mask = Image.new("L", (high_resolution, high_resolution), 0)

    left_curve = cubic_bezier(
        (118, 124),
        (144, 96),
        (195, 89),
        (224, 114),
        samples=52,
    )
    right_curve = cubic_bezier(
        (288, 114),
        (317, 89),
        (368, 96),
        (394, 124),
        samples=52,
    )

    draw_brow(mask, left_curve, scale)
    draw_brow(mask, right_curve, scale)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.7 * scale))
    mask = mask.resize((resolution, resolution), Image.Resampling.LANCZOS)

    values = np.asarray(mask, dtype=np.uint8)
    rgba = np.zeros((resolution, resolution, 4), dtype=np.uint8)
    rgba[:, :, 0] = values
    rgba[:, :, 1] = values
    rgba[:, :, 2] = values
    rgba[:, :, 3] = values
    return Image.fromarray(rgba, mode="RGBA")


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output = resolve(repo, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    image = build_mask(args.resolution, max(1, args.scale))
    image.save(output)
    print(f"generated_brow_mask_texture path={output.relative_to(repo).as_posix()}")


if __name__ == "__main__":
    main()
