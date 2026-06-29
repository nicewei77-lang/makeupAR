#!/usr/bin/env python3
"""Copy user-supplied cheek blush 2D mask PNGs directly into Unity Resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

from generate_user_drawn_mask_textures import (
    DEFAULT_CAPTURE_PAIR,
    format_path,
    resolve_path,
    save,
    write_unity_meta,
)


ATTACHMENT_ROOT = Path("/Users/yeoduchi/.codex/attachments/7a2d9f53-98bf-404c-a9bb-e3104515a6f4")

MASK_SPECS = (
    {
        "id": "cheek-session-mask-1-v1",
        "label": "session mask 1",
        "arg": "mask_1",
        "default": str(ATTACHMENT_ROOT / "image-1.png"),
    },
    {
        "id": "cheek-session-mask-2-v1",
        "label": "session mask 2",
        "arg": "mask_2",
        "default": str(ATTACHMENT_ROOT / "image-2.png"),
    },
    {
        "id": "cheek-session-mask-3-v1",
        "label": "session mask 3",
        "arg": "mask_3",
        "default": str(ATTACHMENT_ROOT / "image-3.png"),
    },
    {
        "id": "cheek-session-mask-4-v1",
        "label": "session mask 4",
        "arg": "mask_4",
        "default": str(ATTACHMENT_ROOT / "image-4.png"),
    },
    {
        "id": "cheek-session-mask-5-v1",
        "label": "session mask 5",
        "arg": "mask_5",
        "default": str(ATTACHMENT_ROOT / "image-5.png"),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy the supplied cheek blush 2D PNG masks directly into Unity Resources."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--capture-pair", type=str, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--reference", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-blush-mask-textures-v1"),
    )
    parser.add_argument(
        "--unity-output-dir",
        type=Path,
        default=Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"),
    )
    for spec in MASK_SPECS:
        parser.add_argument(
            "--" + spec["arg"].replace("_", "-"),
            dest=spec["arg"],
            type=Path,
            default=Path(spec["default"]),
        )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_contact_sheet(images: list[tuple[str, Image.Image]], tile: int = 360) -> Image.Image:
    columns = 2
    rows = int((len(images) + columns - 1) / columns)
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 30)), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * tile
        y = row * (tile + 30)
        thumb = image.convert("RGB").copy()
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x + (tile - thumb.width) // 2, y + 24 + (tile - thumb.height) // 2))
    return sheet


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output_dir = resolve_path(repo, args.output_dir)
    unity_dir = resolve_path(repo, args.unity_output_dir)
    pair_dir = resolve_path(
        repo,
        args.capture_dir,
        Path("evidence/e7-reference-atlas/capture_pairs") / args.capture_pair,
    )
    assert output_dir is not None
    assert unity_dir is not None
    assert pair_dir is not None

    frame_path = pair_dir / "frame.png"
    reference_path = resolve_path(repo, args.reference) if args.reference else frame_path
    if reference_path is None or not reference_path.exists():
        raise FileNotFoundError("Reference image does not exist: " + str(reference_path))

    contact_images: list[tuple[str, Image.Image]] = []
    summaries: dict[str, object] = {}
    expected_size: tuple[int, int] | None = None

    for spec in MASK_SPECS:
        source_path = resolve_path(repo, getattr(args, spec["arg"]))
        if source_path is None or not source_path.exists():
            raise FileNotFoundError("Source cheek 2D mask is missing: " + str(source_path))

        source = Image.open(source_path).convert("RGB")
        if expected_size is None:
            expected_size = source.size
        elif source.size != expected_size:
            raise ValueError("All cheek 2D masks must share the same pixel size.")

        unity_path = unity_dir / (spec["id"] + ".png")
        unity_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, unity_path)
        write_unity_meta(unity_path.with_suffix(".png.meta"), "e7-" + spec["id"])

        source_hash = sha256(source_path)
        unity_hash = sha256(unity_path)
        if source_hash != unity_hash:
            raise RuntimeError(f"Unity resource copy is not byte-identical for {spec['id']}")

        save(output_dir / "atlas" / (spec["id"] + "-source-original.png"), source)
        contact_images.append((spec["label"] + " exact 2D source", source))
        summaries[spec["id"]] = {
            "label": spec["label"],
            "sourcePath": format_path(repo, source_path),
            "unityMaskPath": format_path(repo, unity_path),
            "sourceMode": "byte_identical_user_supplied_2d_png",
            "sourceSize": {"width": int(source.width), "height": int(source.height)},
            "sourceSha256": source_hash,
            "unitySha256": unity_hash,
            "runtimeSamplingRule": "shader samples source RGB luminance directly; no generated R/A/B atlas is baked",
        }

    contact_sheet = make_contact_sheet(contact_images)
    save(output_dir / "cheek_blush_mask_contact_sheet.png", contact_sheet)

    summary = {
        "textureSetId": "cheek-blush-mask-textures-v1",
        "region": "cheek",
        "coordinateSpace": f"{expected_size[0]}x{expected_size[1]} user-supplied 2D texture" if expected_size else "unknown",
        "uvResolution": f"{expected_size[0]}x{expected_size[1]}" if expected_size else "unknown",
        "capturePairId": pair_dir.name,
        "referencePath": format_path(repo, reference_path),
        "outputDir": format_path(repo, output_dir),
        "unityOutputDir": format_path(repo, unity_dir),
        "maskIds": [spec["id"] for spec in MASK_SPECS],
        "atlasSourceRule": "the five user-provided 2D PNGs are copied byte-for-byte into Unity Resources; pixel positions are not reprojected, enlarged, redrawn, or converted into baked mask channels",
        "runtimeSelectionRule": "one user-supplied cheek blush 2D texture is selected per cheek layer; masks are not stacked together",
        "shaderSamplingContract": {
            "rgb": "source RGB is preserved exactly in the Unity Resource PNG",
            "coverage": "computed at runtime from source RGB luminance",
            "density": "computed at runtime from source RGB luminance; darker gray source pixels become stronger blush density",
            "alpha": "source alpha is not used for cheek blush coverage",
        },
        "masks": summaries,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        "# Cheek Blush Mask Textures v1\n\n"
        f"- region: `{summary['region']}`\n"
        f"- coordinateSpace: `{summary['coordinateSpace']}`\n"
        f"- uvResolution: `{summary['uvResolution']}`\n"
        f"- capturePairId: `{summary['capturePairId']}`\n"
        f"- contactSheet: `{format_path(repo, output_dir / 'cheek_blush_mask_contact_sheet.png')}`\n"
        f"- atlasSourceRule: `{summary['atlasSourceRule']}`\n"
        f"- runtimeSelectionRule: `{summary['runtimeSelectionRule']}`\n\n"
        "## Unity Masks\n\n"
        + "\n".join(
            f"- `{mask_id}`: `{data['unityMaskPath']}` sha256 `{data['unitySha256']}`"
            for mask_id, data in summaries.items()
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
