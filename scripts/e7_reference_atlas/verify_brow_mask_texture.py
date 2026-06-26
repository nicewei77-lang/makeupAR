#!/usr/bin/env python3
"""Verify the Unity-ready procedural eyebrow smooth-region mask."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


DEFAULT_BROW_MASK = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "brow-drawn-mask-v1.png"
)
DEFAULT_MASK_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)
REGION_SEPARATION_MASKS = {
    "eye-drawn": ("eye-drawn-mask-v1.png", 1200),
    "eye-smooth": ("eye-smooth-mask-v1.png", 4200),
    "cheek-drawn": ("cheek-drawn-mask-v1.png", 50),
    "lip-drawn": ("lip-drawn-mask-v1.png", 0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify brow-drawn-mask-v1.png.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mask", type=Path, default=DEFAULT_BROW_MASK)
    parser.add_argument("--mask-dir", type=Path, default=DEFAULT_MASK_DIR)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--component-threshold", type=int, default=32)
    parser.add_argument("--min-component-pixels", type=int, default=800)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def bbox_for(mask: np.ndarray) -> dict[str, int] | None:
    rows, cols = np.nonzero(mask)
    if len(cols) == 0:
        return None

    return {
        "left": int(cols.min()),
        "top": int(rows.min()),
        "right": int(cols.max()),
        "bottom": int(rows.max()),
        "width": int(cols.max() - cols.min() + 1),
        "height": int(rows.max() - rows.min() + 1),
    }


def connected_components(mask: np.ndarray, min_pixels: int) -> list[dict[str, Any]]:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[dict[str, Any]] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    rows, cols = np.nonzero(mask)
    for start_y, start_x in zip(rows.tolist(), cols.tolist()):
        if visited[start_y, start_x]:
            continue

        queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []

        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            for dy, dx in neighbors:
                next_y = y + dy
                next_x = x + dx
                if (
                    0 <= next_y < height
                    and 0 <= next_x < width
                    and mask[next_y, next_x]
                    and not visited[next_y, next_x]
                ):
                    visited[next_y, next_x] = True
                    queue.append((next_y, next_x))

        if len(pixels) < min_pixels:
            continue

        ys, xs = zip(*pixels)
        components.append(
            {
                "pixelCount": len(pixels),
                "bbox": {
                    "left": int(min(xs)),
                    "top": int(min(ys)),
                    "right": int(max(xs)),
                    "bottom": int(max(ys)),
                    "width": int(max(xs) - min(xs) + 1),
                    "height": int(max(ys) - min(ys) + 1),
                },
                "centerX": float(sum(xs) / len(xs)),
                "centerY": float(sum(ys) / len(ys)),
            }
        )

    return sorted(components, key=lambda component: component["centerX"])


def load_red_mask(path: Path, threshold: int) -> np.ndarray:
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    return rgba[:, :, 0] > threshold


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    mask_path = resolve(repo, args.mask)
    mask_dir = resolve(repo, args.mask_dir)

    require(mask_path.exists(), f"Missing brow mask texture: {mask_path}")

    image = Image.open(mask_path).convert("RGBA")
    require(
        image.size == (args.resolution, args.resolution),
        f"Expected {args.resolution}x{args.resolution}, got {image.size}.",
    )

    rgba = np.asarray(image)
    red = rgba[:, :, 0]
    active = red > args.threshold
    active_count = int(active.sum())
    coverage = active_count / float(args.resolution * args.resolution)
    bounds = bbox_for(active)

    require(bounds is not None, "Brow mask has no active red-channel pixels.")
    require(2500 <= active_count <= 13000, f"Unexpected active pixels: {active_count}.")
    require(0.008 <= coverage <= 0.05, f"Unexpected active coverage: {coverage:.6f}.")
    require(95 <= bounds["left"] <= 170, f"Brow bbox left is off: {bounds}.")
    require(340 <= bounds["right"] <= 430, f"Brow bbox right is off: {bounds}.")
    require(70 <= bounds["top"] <= 135, f"Brow bbox top is off: {bounds}.")
    require(120 <= bounds["bottom"] <= 175, f"Brow bbox bottom is off: {bounds}.")
    require(220 <= bounds["width"] <= 340, f"Brow bbox width is off: {bounds}.")
    require(35 <= bounds["height"] <= 95, f"Brow bbox height is off: {bounds}.")

    components = connected_components(
        red > args.component_threshold,
        args.min_component_pixels,
    )
    require(len(components) == 2, f"Expected two brow components, got {components}.")

    left, right = components
    require(120 <= left["centerX"] <= 220, f"Left brow center is off: {left}.")
    require(292 <= right["centerX"] <= 392, f"Right brow center is off: {right}.")
    require(left["bbox"]["right"] < 245, f"Left brow crosses center gap: {left}.")
    require(right["bbox"]["left"] > 267, f"Right brow crosses center gap: {right}.")

    center_gap_pixels = int((red[:, 245:267] > args.component_threshold).sum())
    require(center_gap_pixels <= 30, f"Center gap is too filled: {center_gap_pixels}.")

    overlap_summaries: list[str] = []
    for label, (filename, max_overlap_pixels) in REGION_SEPARATION_MASKS.items():
        region_path = mask_dir / filename
        require(region_path.exists(), f"Missing region separation mask: {region_path}")
        region_mask = load_red_mask(region_path, args.threshold)
        overlap_pixels = int((active & region_mask).sum())
        overlap_summaries.append(f"{label}={overlap_pixels}/{max_overlap_pixels}")
        require(
            overlap_pixels <= max_overlap_pixels,
            f"Brow mask overlaps {label}: {overlap_pixels} > {max_overlap_pixels}.",
        )

    print(
        "brow_mask_texture_ok "
        f"path={mask_path.relative_to(repo).as_posix()} "
        f"activePixels={active_count} coverage={coverage:.6f} bbox={bounds} "
        f"components={components} overlaps={','.join(overlap_summaries)}"
    )


if __name__ == "__main__":
    main()
