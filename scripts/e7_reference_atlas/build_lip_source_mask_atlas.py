#!/usr/bin/env python3
"""Pack separate lip source masks into runtime RGBA atlas textures.

Source masks are the human-reviewable truth:
R/full, G/overlip, B/gradient density, A/glossy highlight.
The generated Unity Resources atlases are runtime artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path("unity/MakeupARUnityValidation/Assets/SourceMasks/Lip")
RUNTIME_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)


def resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def load_luma(path: Path) -> Image.Image:
    return Image.open(path).convert("L")


def image_stats(image: Image.Image) -> dict[str, object]:
    histogram = image.histogram()
    active_values = [index for index, count in enumerate(histogram) if count > 0]
    return {
        "mode": image.mode,
        "size": list(image.size),
        "min": min(active_values),
        "max": max(active_values),
        "pixelsGt0": sum(histogram[1:]),
        "pixelsGt8": sum(histogram[9:]),
        "pixelsGt32": sum(histogram[33:]),
        "pixelsGt128": sum(histogram[129:]),
    }


def save_channel_preview(path: Path, channels: dict[str, Image.Image]) -> None:
    width, height = next(iter(channels.values())).size
    sheet = Image.new("RGB", (width * 2, height * 2), "white")
    positions = {
        "full": (0, 0),
        "overlip": (width, 0),
        "gradient": (0, height),
        "glossy": (width, height),
    }

    for name, image in channels.items():
        luma = image.convert("L")
        sheet.paste(Image.merge("RGB", (luma, luma, luma)), positions[name])

    sheet.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build lip runtime RGBA atlas textures from separate masks."
    )
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR)
    parser.add_argument("--runtime-dir", type=Path, default=RUNTIME_DIR)
    parser.add_argument("--gradient", default="gradient-density-pronounced.png")
    args = parser.parse_args()

    source_dir = resolve_repo_path(args.source_dir)
    runtime_dir = resolve_repo_path(args.runtime_dir)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    channels = {
        "full": load_luma(source_dir / "full.png"),
        "overlip": load_luma(source_dir / "overlip.png"),
        "gradient": load_luma(source_dir / args.gradient),
        "glossy": load_luma(source_dir / "glossy-highlight.png"),
    }
    sizes = {image.size for image in channels.values()}
    if len(sizes) != 1:
        raise ValueError(f"Source masks must share one size, got {sorted(sizes)}")

    atlas = Image.merge(
        "RGBA",
        (
            channels["full"],
            channels["overlip"],
            channels["gradient"],
            channels["glossy"],
        ),
    )

    outputs = {
        "lip-drawn-style-atlas-v1.png": atlas,
        "lip-drawn-gradient-density-atlas-v1.png": atlas,
    }
    for filename, image in outputs.items():
        image.save(runtime_dir / filename)

    preview_path = source_dir / "lip-source-masks-runtime-atlas-preview.png"
    save_channel_preview(preview_path, channels)

    summary = {
        "status": "built",
        "sourceDir": source_dir.relative_to(REPO_ROOT).as_posix(),
        "runtimeDir": runtime_dir.relative_to(REPO_ROOT).as_posix(),
        "gradientSource": args.gradient,
        "runtimeAtlases": sorted(outputs),
        "preview": preview_path.relative_to(REPO_ROOT).as_posix(),
        "channels": {name: image_stats(image) for name, image in channels.items()},
    }
    summary_path = source_dir / "runtime-atlas-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
