#!/usr/bin/env python3
"""Verify the canonical source-brow cleanup mask."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


DEFAULT_MASK = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "brow-cleanup-source-v1.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify brow cleanup source mask.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mask", type=Path, default=DEFAULT_MASK)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--active-threshold", type=int, default=8)
    parser.add_argument("--component-threshold", type=int, default=32)
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


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    mask_path = resolve(repo, args.mask)
    require(mask_path.exists(), f"Missing brow cleanup source mask: {mask_path}")

    image = Image.open(mask_path).convert("RGBA")
    require(
        image.size == (args.resolution, args.resolution),
        f"Expected {args.resolution}x{args.resolution}, got {image.size}.",
    )

    red = np.asarray(image, dtype=np.uint8)[:, :, 0]
    active = red > args.active_threshold
    active_count = int(active.sum())
    coverage = active_count / float(args.resolution * args.resolution)
    bounds = bbox_for(active)
    require(bounds is not None, "Source cleanup mask has no active pixels.")
    require(16000 <= active_count <= 24000, f"Unexpected active pixels: {active_count}.")
    require(0.060 <= coverage <= 0.092, f"Unexpected coverage: {coverage:.6f}.")
    require(80 <= bounds["left"] <= 92, f"Source cleanup bbox left is off: {bounds}.")
    require(420 <= bounds["right"] <= 432, f"Source cleanup bbox right is off: {bounds}.")
    require(76 <= bounds["top"] <= 86, f"Source cleanup bbox top is off: {bounds}.")
    require(140 <= bounds["bottom"] <= 150, f"Source cleanup bbox bottom is off: {bounds}.")
    require(330 <= bounds["width"] <= 346, f"Source cleanup bbox width is off: {bounds}.")
    require(58 <= bounds["height"] <= 68, f"Source cleanup bbox height is off: {bounds}.")

    components = connected_components(red > args.component_threshold, min_pixels=5000)
    require(len(components) == 2, f"Expected two source cleanup components, got {components}.")
    left, right = components
    require(160 <= left["centerX"] <= 178, f"Left source cleanup center is off: {left}.")
    require(334 <= right["centerX"] <= 352, f"Right source cleanup center is off: {right}.")
    require(left["bbox"]["right"] < 255, f"Left source cleanup crosses too far inward: {left}.")
    require(right["bbox"]["left"] > 255, f"Right source cleanup crosses too far inward: {right}.")

    center_gap_pixels = int((red[:, 245:267] > 80).sum())
    require(center_gap_pixels <= 220, f"Source cleanup fills too much center gap: {center_gap_pixels}.")

    print(
        "brow_cleanup_source_mask_ok "
        f"path={mask_path.relative_to(repo).as_posix()} "
        f"activePixels={active_count} coverage={coverage:.6f} bbox={bounds} "
        f"components={components} centerGapPixels={center_gap_pixels}"
    )


if __name__ == "__main__":
    main()
