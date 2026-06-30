#!/usr/bin/env python3
"""Extract named runtime makeup layers from the ARCore canonical-face PSD."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

try:
    from psd_tools import PSDImage
except ModuleNotFoundError as error:  # pragma: no cover - exercised by CLI setup.
    raise SystemExit(
        "psd_tools is required. In this repo use: "
        "PYTHONPATH=.codex_deps/psd-tools /opt/anaconda3/bin/python3.12 "
        "scripts/e7_reference_atlas/extract_arcore_psd_layers.py"
    ) from error


DEFAULT_SOURCE_PSD = Path("evidence/asset-inputs/ARCore_canonical_face_texture_1.psd")
DEFAULT_OUTPUT_DIR = Path(
    "evidence/asset-inputs/ARCore_canonical_face_texture_1_extracted"
)

RUNTIME_LAYER_PATHS = {
    "Root/eyebrow/semi-arch/left",
    "Root/eyebrow/semi-arch/right",
    "Root/eyebrow/semi-arch/left-full",
    "Root/eyebrow/semi-arch/right-full",
    "Root/eyebrow/semi-arch/left-gradient",
    "Root/eyebrow/semi-arch/right-gradient",
    "Root/eyebrow/semi-arch/right-gradient 복사",
    "Root/blush/Undereye/all",
    "Root/blush/Asia-Z/all",
    "Root/blush/Sunkissed/all",
    "Root/blush/Daily-Oval/all",
    "Root/blush/Undereye2/all",
    "Root/blush/Lovely_Round/all",
    "Root/blush/Lifted-Diagonal/all",
    "Root/blush/undereye/left",
    "Root/blush/undereye/right",
    "Root/blush/undereye/undereye",
    "Root/blush/Sunkissed/레이어 5",
    "Root/lip/full_color_or_mask",
    "Root/lip/gradient_density",
    "Root/lip/gloss_highlight/gloss_highlight",
}
RUNTIME_LAYER_PATHS_NORMALIZED = {
    path.casefold() for path in RUNTIME_LAYER_PATHS
}

SKIP_NAME_FRAGMENTS = {
    "archive",
    "archieve",
    "background",
    "lines",
    "mask",
    "preview",
    "uv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract ARCore PSD runtime layers.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-psd", type=Path, default=DEFAULT_SOURCE_PSD)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def relative_or_absolute(repo: Path, path: Path) -> str:
    try:
        return path.relative_to(repo).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_path(path: str) -> str:
    value = path.strip().lower().replace("/", "_")
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^0-9a-z가-힣._-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value


def inherited_visible(path: list[object]) -> bool:
    return all(bool(getattr(layer, "visible", False)) for layer in path)


def skip_reason(path: str) -> str | None:
    lowered_parts = [part.lower() for part in path.split("/")]
    if path.casefold() in RUNTIME_LAYER_PATHS_NORMALIZED:
        return None
    for part in lowered_parts:
        if any(fragment in part for fragment in SKIP_NAME_FRAGMENTS):
            return "guide_or_archive"
    return "not_runtime_makeup_layer"


def alpha_bbox(values: np.ndarray) -> tuple[int, int, int, int] | None:
    rows, cols = np.nonzero(values > 0)
    if len(cols) == 0:
        return None
    return int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1


def paste_on_canvas(crop: Image.Image, bbox: tuple[int, int, int, int], size: tuple[int, int]) -> Image.Image:
    x0, y0, x1, y1 = bbox
    canvas_w, canvas_h = size
    source_x0 = max(0, -x0)
    source_y0 = max(0, -y0)
    source_x1 = crop.width - max(0, x1 - canvas_w)
    source_y1 = crop.height - max(0, y1 - canvas_h)
    target_x = max(0, x0)
    target_y = max(0, y0)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    if source_x1 > source_x0 and source_y1 > source_y0:
        canvas.paste(crop.crop((source_x0, source_y0, source_x1, source_y1)), (target_x, target_y))
    return canvas


def make_contact_sheet(items: list[tuple[str, Image.Image]]) -> Image.Image:
    tile = 180
    label_h = 48
    cols = 4
    rows = max(1, (len(items) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(items):
        x = (index % cols) * tile
        y = (index // cols) * (tile + label_h)
        thumb = image.convert("RGBA")
        alpha = thumb.getchannel("A")
        preview = Image.new("RGBA", thumb.size, (218, 66, 122, 0))
        preview.putalpha(alpha)
        preview.thumbnail((tile - 16, tile - 16), Image.Resampling.LANCZOS)
        sheet.paste(
            Image.new("RGB", (tile, tile), (255, 255, 255)),
            (x, y),
        )
        sheet.paste(
            preview,
            (x + (tile - preview.width) // 2, y + (tile - preview.height) // 2),
            preview.getchannel("A"),
        )
        draw.rectangle((x, y + tile, x + tile, y + tile + label_h), fill=(35, 35, 42))
        draw.text((x + 8, y + tile + 9), label[:28], fill=(255, 255, 255))
    return sheet


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    source_psd = resolve(repo, args.source_psd)
    output_dir = resolve(repo, args.output_dir)
    cropped_dir = output_dir / "cropped"
    full_canvas_dir = output_dir / "full-canvas"
    cropped_dir.mkdir(parents=True, exist_ok=True)
    full_canvas_dir.mkdir(parents=True, exist_ok=True)
    for directory in (cropped_dir, full_canvas_dir):
        for stale_png in directory.glob("*.png"):
            stale_png.unlink()

    psd = PSDImage.open(source_psd)
    canvas_size = (psd.width, psd.height)
    records: list[dict[str, object]] = []
    contact_items: list[tuple[str, Image.Image]] = []

    def walk(layer: object, parent_path: str, lineage: list[object]) -> None:
        name = str(getattr(layer, "name", "") or "<unnamed>")
        path = f"{parent_path}/{name}" if parent_path else f"Root/{name}"
        path_lineage = [*lineage, layer]
        bbox = tuple(getattr(layer, "bbox", (0, 0, 0, 0)))

        if bool(layer.is_group()):
            for child in layer:
                walk(child, path, path_lineage)
            return

        record: dict[str, object] = {
            "path": path,
            "bbox": list(bbox),
            "visible": bool(getattr(layer, "visible", False)),
            "inheritedVisible": inherited_visible(path_lineage),
        }
        reason = skip_reason(path)
        if reason is not None:
            record.update({"skip": True, "reason": reason})
            records.append(record)
            return

        x0, y0, x1, y1 = bbox
        if x1 <= x0 or y1 <= y0:
            record.update({"skip": True, "reason": "empty_bbox"})
            records.append(record)
            return

        force_visible = not inherited_visible(path_lineage)
        crop = layer.composite(layer_filter=lambda _layer: True).convert("RGBA")
        full_canvas = paste_on_canvas(crop, bbox, canvas_size)
        filename = f"{sanitize_path(path)}.png"
        cropped_path = cropped_dir / filename
        full_canvas_path = full_canvas_dir / filename
        crop.save(cropped_path)
        full_canvas.save(full_canvas_path)
        alpha_box = alpha_bbox(np.asarray(crop.getchannel("A"), dtype=np.uint8))
        record.update(
            {
                "skip": False,
                "forceVisibleComposite": force_visible,
                "cropped": relative_or_absolute(repo, cropped_path),
                "fullCanvas": relative_or_absolute(repo, full_canvas_path),
                "cropSize": [crop.width, crop.height],
                "alphaBboxInCrop": list(alpha_box) if alpha_box is not None else None,
                "alphaPixelsGt8": int((np.asarray(crop.getchannel("A"), dtype=np.uint8) > 8).sum()),
            }
        )
        records.append(record)
        contact_items.append((filename.removesuffix(".png"), full_canvas))

    for top_layer in psd:
        walk(top_layer, "", [])

    manifest = {
        "source": relative_or_absolute(repo, source_psd),
        "canvasSize": [psd.width, psd.height],
        "extractionPolicy": (
            "Runtime makeup layers are selected by canonical layer path. Hidden "
            "runtime layers are force-composited so Photoshop visibility does not "
            "erase full, gradient, or lip mask sources."
        ),
        "runtimeLayerPaths": sorted(RUNTIME_LAYER_PATHS),
        "records": records,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    make_contact_sheet(contact_items).save(output_dir / "contact_sheet.png")

    exported = [record for record in records if not record.get("skip")]
    print(f"extracted_arcore_psd_layers source={relative_or_absolute(repo, source_psd)}")
    for record in exported:
        print(
            f"{record['path']} fullCanvas={record['fullCanvas']} "
            f"forceVisibleComposite={record['forceVisibleComposite']} "
            f"alphaPixelsGt8={record['alphaPixelsGt8']}"
        )


if __name__ == "__main__":
    main()
