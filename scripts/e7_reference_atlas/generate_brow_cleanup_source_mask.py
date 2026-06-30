#!/usr/bin/env python3
"""Generate the canonical source-brow mask used by cleanup/concealer."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
DEFAULT_OUTPUT = MASK_DIR / "brow-cleanup-source-v1.png"
SOURCE_MASK_IDS = (
    "brow-back-arch-soft-mix-v1",
    "brow-drawn-mask-v1",
    "brow-png-daily-hair-v1",
    "brow-png-dailyflat-hair-v1",
    "brow-png-dailyflat-multiply-v1",
    "brow-png-dailyflat-sharp-v1",
    "brow-png-lightbrown-hair-v1",
    "brow-png-narrow-hair-v1",
    "brow-png-natural-hair-v1",
    "brow-slim-tail-fine-hair-v1",
    "brow-soft-arch-fine-hair-v1",
)
UNITY_META_GUID = hashlib.md5(b"e7-brow-cleanup-source-v1").hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate brow-cleanup-source-v1.png.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--threshold", type=int, default=6)
    parser.add_argument("--max-filter-size", type=int, default=13)
    parser.add_argument("--blur", type=float, default=3.0)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_union_red(mask_dir: Path) -> np.ndarray:
    union: np.ndarray | None = None
    for mask_id in SOURCE_MASK_IDS:
        path = mask_dir / f"{mask_id}.png"
        require(path.exists(), f"Missing source brow mask: {path}")
        red = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)[:, :, 0]
        union = red if union is None else np.maximum(union, red)

    require(union is not None, "No source masks were loaded.")
    return union


def build_cleanup_source_mask(
    union_red: np.ndarray,
    threshold: int,
    max_filter_size: int,
    blur: float,
) -> Image.Image:
    size = max(3, max_filter_size)
    if size % 2 == 0:
        size += 1

    binary = (union_red > threshold).astype(np.uint8) * 255
    expanded = (
        Image.fromarray(binary, mode="L")
        .filter(ImageFilter.MaxFilter(size=size))
        .filter(ImageFilter.GaussianBlur(radius=max(0.0, blur)))
    )
    values = np.asarray(expanded, dtype=np.uint8)
    rgba = np.zeros((values.shape[0], values.shape[1], 4), dtype=np.uint8)
    rgba[:, :, 0] = values
    rgba[:, :, 1] = values
    rgba[:, :, 2] = values
    rgba[:, :, 3] = values
    return Image.fromarray(rgba, mode="RGBA")


def write_unity_meta(output: Path) -> None:
    template = output.parent / "brow-png-natural-hair-v1.png.meta"
    require(template.exists(), f"Missing Unity meta template: {template}")
    meta = template.read_text(encoding="utf-8")
    meta = re.sub(r"guid: [0-9a-f]+", f"guid: {UNITY_META_GUID}", meta, count=1)
    output.with_suffix(".png.meta").write_text(meta, encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output = resolve(repo, args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    union_red = load_union_red(output.parent)
    image = build_cleanup_source_mask(
        union_red,
        threshold=max(0, min(255, args.threshold)),
        max_filter_size=args.max_filter_size,
        blur=args.blur,
    )
    image.save(output)
    write_unity_meta(output)
    print(f"generated_brow_cleanup_source_mask path={output.relative_to(repo).as_posix()}")


if __name__ == "__main__":
    main()
