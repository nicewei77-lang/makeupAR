#!/usr/bin/env python3
"""Verify Unity-ready PNG-derived eyebrow hair textures."""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
MASK_TEXTURE_IDS = (
    "brow-png-dailyflat-hair-v1",
    "brow-png-dailyflat-sharp-v1",
    "brow-png-dailyflat-multiply-v1",
    "brow-png-daily-hair-v1",
    "brow-png-natural-hair-v1",
    "brow-png-narrow-hair-v1",
    "brow-png-lightbrown-hair-v1",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify PNG brow hair textures.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mask-dir", type=Path, default=MASK_DIR)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--threshold", type=int, default=8)
    parser.add_argument("--component-threshold", type=int, default=26)
    parser.add_argument("--min-component-pixels", type=int, default=320)
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


def component_fill_metrics(active: np.ndarray, component: dict[str, Any]) -> dict[str, float]:
    bbox = component["bbox"]
    left = bbox["left"]
    right = bbox["right"] + 1
    top = bbox["top"]
    bottom = bbox["bottom"] + 1
    width = max(1, right - left)
    height = max(1, bottom - top)
    crop = active[top:bottom, left:right]
    inner_left = left + int(width * 0.20)
    inner_right = right - int(width * 0.20)
    inner_top = top + int(height * 0.25)
    inner_bottom = bottom - int(height * 0.25)
    inner = active[inner_top:inner_bottom, inner_left:inner_right]

    return {
        "bboxFill": float(crop.sum() / max(1, crop.size)),
        "innerFill": float(inner.sum() / max(1, inner.size)),
    }


def verify_texture(path: Path, resolution: int, threshold: int, component_threshold: int, min_component_pixels: int) -> str:
    require(path.exists(), f"Missing PNG brow hair texture: {path}")
    image = Image.open(path).convert("RGBA")
    require(image.size == (resolution, resolution), f"Unexpected size for {path}: {image.size}")
    rgba = np.asarray(image)
    red = rgba[:, :, 0]
    blue = rgba[:, :, 2]
    alpha = rgba[:, :, 3]
    active = red > threshold
    bounds = bbox_for(active)
    require(bounds is not None, f"{path.name} has no active brow pixels.")

    active_count = int(active.sum())
    coverage = active_count / float(resolution * resolution)
    require(1600 <= active_count <= 12500, f"{path.name} active pixels off: {active_count}")
    require(0.006 <= coverage <= 0.048, f"{path.name} coverage off: {coverage:.6f}")
    require(84 <= bounds["left"] <= 112, f"{path.name} left bbox off: {bounds}")
    require(398 <= bounds["right"] <= 430, f"{path.name} right bbox off: {bounds}")
    require(92 <= bounds["top"] <= 104, f"{path.name} top bbox off: {bounds}")
    require(126 <= bounds["bottom"] <= 138, f"{path.name} bottom bbox off: {bounds}")
    require(24 <= bounds["height"] <= 48, f"{path.name} height off: {bounds}")
    if "dailyflat-sharp" in path.name or "dailyflat-multiply" in path.name:
        require(bounds["height"] <= 38, f"{path.name} should stay thin: {bounds}")

    components = connected_components(red > component_threshold, min_component_pixels)
    require(len(components) == 2, f"{path.name} should have two brows, got: {components}")
    left, right = components
    require(left["bbox"]["right"] < 246, f"{path.name} left brow crosses center: {left}")
    require(right["bbox"]["left"] > 266, f"{path.name} right brow crosses center: {right}")
    center_gap = right["bbox"]["left"] - left["bbox"]["right"] - 1
    min_center_gap = 44 if "dailyflat" in path.name else 30
    require(
        center_gap >= min_center_gap,
        f"{path.name} center gap too narrow: {center_gap}px components={components}",
    )
    if "dailyflat" in path.name:
        require(
            bounds["left"] >= left["bbox"]["left"] - 8,
            f"{path.name} has stray low-alpha pixels before the left brow: bounds={bounds} left={left}",
        )
        require(
            bounds["right"] <= right["bbox"]["right"] + 8,
            f"{path.name} has stray low-alpha pixels after the right brow: bounds={bounds} right={right}",
        )
        left_fill = component_fill_metrics(active, left)
        right_fill = component_fill_metrics(active, right)
        require(
            left_fill["innerFill"] >= 0.72,
            f"{path.name} left brow interior is hollow: {left_fill}",
        )
        require(
            right_fill["innerFill"] >= 0.72,
            f"{path.name} right brow interior is hollow: {right_fill}",
        )

    corner_alpha = int(
        alpha[:32, :32].max()
        + alpha[:32, -32:].max()
        + alpha[-32:, :32].max()
        + alpha[-32:, -32:].max()
    )
    require(corner_alpha == 0, f"{path.name} has residual background alpha in corners.")

    detail_values = blue[active]
    red_values = red[active]
    min_detail_std = 11.0 if "dailyflat-sharp" in path.name or "dailyflat-multiply" in path.name else 8.0
    require(float(detail_values.std()) >= min_detail_std, f"{path.name} detail channel too flat.")
    require(float(red_values.std()) >= 7.0, f"{path.name} alpha shape too flat.")
    require(int(blue[active].max()) > int(red[active].mean()), f"{path.name} detail channel lacks hair peaks.")

    return (
        f"{path.name}:active={active_count} coverage={coverage:.6f} "
        f"bbox={bounds} components={components} detailStd={float(detail_values.std()):.2f}"
    )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    mask_dir = resolve(repo, args.mask_dir)
    summaries = [
        verify_texture(
            mask_dir / f"{mask_texture_id}.png",
            args.resolution,
            args.threshold,
            args.component_threshold,
            args.min_component_pixels,
        )
        for mask_texture_id in MASK_TEXTURE_IDS
    ]

    print("brow_png_hair_textures_ok " + " | ".join(summaries))


if __name__ == "__main__":
    main()
