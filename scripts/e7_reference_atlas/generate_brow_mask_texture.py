#!/usr/bin/env python3
"""Generate the in-house procedural eyebrow smooth-region mask."""

from __future__ import annotations

import argparse
import math
import random
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


def offset_curve(
    curve: list[tuple[float, float]],
    offset: float,
    vertical_jitter: float,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    last_index = len(curve) - 1
    for index, (x, y) in enumerate(curve):
        if index == 0:
            x0, y0 = curve[index]
            x1, y1 = curve[index + 1]
        elif index == last_index:
            x0, y0 = curve[index - 1]
            x1, y1 = curve[index]
        else:
            x0, y0 = curve[index - 1]
            x1, y1 = curve[index + 1]

        dx = x1 - x0
        dy = y1 - y0
        length = math.hypot(dx, dy) or 1.0
        normal_x = -dy / length
        normal_y = dx / length
        points.append(
            (x + normal_x * offset, y + normal_y * offset + vertical_jitter)
        )

    return points


def draw_brow(
    layer: Image.Image,
    curve: list[tuple[float, float]],
    scale: int,
    seed: int,
) -> None:
    draw = ImageDraw.Draw(layer)
    points = scaled_points(curve, scale)
    draw_round_line(draw, points, width=round(20 * scale), fill=42)
    draw_round_line(draw, points, width=round(13 * scale), fill=92)
    draw_round_line(draw, points, width=round(6 * scale), fill=145)

    rng = random.Random(seed)
    for _ in range(18):
        start = rng.randint(5, max(5, len(curve) - 32))
        end = min(len(curve) - 5, start + rng.randint(13, 26))
        segment = offset_curve(
            curve[start:end],
            rng.uniform(-4.2, 4.2),
            rng.uniform(-1.5, 1.5),
        )
        draw_round_line(
            draw,
            scaled_points(segment, scale),
            width=max(1, round(rng.uniform(1.0, 1.9) * scale)),
            fill=rng.randint(150, 225),
        )


def apply_longitudinal_density_variation(values: np.ndarray) -> np.ndarray:
    adjusted = values.astype(np.float32, copy=True)
    brow_ranges = ((112, 235, 11), (276, 400, 13))

    for x0, x1, seed in brow_ranges:
        rng = random.Random(seed)
        width = x1 - x0 + 1
        controls = [rng.uniform(0.82, 1.08) for _ in range(13)]
        modifiers: list[float] = []
        for index in range(width):
            position = index / float(max(width - 1, 1)) * (len(controls) - 1)
            lower = int(position)
            upper = min(lower + 1, len(controls) - 1)
            t = position - lower
            smooth_t = t * t * (3.0 - 2.0 * t)
            modifiers.append(
                controls[lower] * (1.0 - smooth_t) + controls[upper] * smooth_t
            )

        for offset_x, x in enumerate(range(x0, x1 + 1)):
            column = adjusted[:, x]
            strength = np.clip((column - 36.0) / 120.0, 0.0, 1.0) * 0.55
            adjusted[:, x] = column * (1.0 - strength + strength * modifiers[offset_x])

    return np.clip(adjusted, 0, 255).astype(np.uint8)


def build_mask(resolution: int, scale: int) -> Image.Image:
    high_resolution = resolution * scale
    mask = Image.new("L", (high_resolution, high_resolution), 0)

    left_curve = cubic_bezier(
        (124, 119),
        (152, 112),
        (192, 109),
        (222, 116),
        samples=80,
    )
    right_curve = cubic_bezier(
        (290, 116),
        (320, 109),
        (360, 112),
        (388, 119),
        samples=80,
    )

    draw_brow(mask, left_curve, scale, seed=1701)
    draw_brow(mask, right_curve, scale, seed=2701)

    mask = mask.filter(ImageFilter.GaussianBlur(radius=1.05 * scale))
    mask = mask.resize((resolution, resolution), Image.Resampling.LANCZOS)

    values = apply_longitudinal_density_variation(np.asarray(mask, dtype=np.uint8))
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
