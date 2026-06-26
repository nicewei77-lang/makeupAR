#!/usr/bin/env python3
"""Generate a gradient-only lip atlas with a distance-field B channel.

The default lip atlas remains untouched so frozen matte/gloss paths keep using
the same resource. This script copies R/G/A from lip-drawn-style-atlas-v1 and
replaces B with a continuous density field for gradient_lip only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_SOURCE = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "lip-drawn-style-atlas-v1.png"
)
DEFAULT_OUTPUT = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "lip-drawn-gradient-density-atlas-v1.png"
)
DEFAULT_EVIDENCE = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/"
    "gradient_density_atlas_20260626"
)
UNITY_META_GUID = "d2dff6903519403cb8d768a2a98888e7"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the gradient_lip distance-field atlas.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - edge0) / max(edge1 - edge0, 1.0e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def edt_1d(values: np.ndarray) -> np.ndarray:
    n = len(values)
    v = np.zeros(n, dtype=np.int32)
    z = np.zeros(n + 1, dtype=np.float64)
    d = np.zeros(n, dtype=np.float64)
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf

    for q in range(1, n):
        while True:
            r = v[k]
            numerator = (values[q] + q * q) - (values[r] + r * r)
            denominator = 2.0 * (q - r)
            s = numerator / denominator
            if s > z[k]:
                break
            k -= 1
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf

    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        r = v[k]
        d[q] = (q - r) * (q - r) + values[r]

    return d


def distance_to_features(features: np.ndarray) -> np.ndarray:
    height, width = features.shape
    inf = float(height * height + width * width + 1)
    field = np.where(features, 0.0, inf).astype(np.float64)
    tmp = np.empty_like(field)
    dist2 = np.empty_like(field)

    for x in range(width):
        tmp[:, x] = edt_1d(field[:, x])
    for y in range(height):
        dist2[y, :] = edt_1d(tmp[y, :])

    return np.sqrt(np.maximum(dist2, 0.0)).astype(np.float32)


def bbox(mask: np.ndarray) -> dict[str, int]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        raise ValueError("No active lip pixels in source atlas R channel.")
    return {
        "left": int(xs.min()),
        "top": int(ys.min()),
        "right": int(xs.max()),
        "bottom": int(ys.max()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }


def make_gradient_density(full_channel: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    alpha = full_channel.astype(np.float32) / 255.0
    active = alpha > 0.035
    box = bbox(active)
    height, width = active.shape
    grid_y, grid_x = np.indices(active.shape, dtype=np.float32)

    center_x = box["left"] + box["width"] * 0.5
    crease_y = box["top"] + box["height"] * 0.56
    seed_half_width = max(2.0, box["width"] * 0.36)
    seed_half_height = max(2.0, box["height"] * 0.115)
    seed = (
        active
        & (np.abs(grid_x - center_x) <= seed_half_width)
        & (np.abs(grid_y - crease_y) <= seed_half_height)
    )
    if int(seed.sum()) == 0:
        seed = active

    distance_from_seed = distance_to_features(seed)
    distance_to_edge = distance_to_features(~active)
    max_edge_distance = max(float(np.percentile(distance_to_edge[active], 96)), 1.0)
    attraction_radius = max(box["width"] * 0.48, box["height"] * 0.68, 1.0)

    inner_attraction = np.exp(-np.power(distance_from_seed / attraction_radius, 1.22))
    outer_falloff = smoothstep(0.00, 0.50, distance_to_edge / max_edge_distance)
    center_bias = np.exp(-np.power(np.abs(grid_x - center_x) / max(box["width"] * 0.56, 1.0), 3.0))
    vertical_bias = np.exp(-np.power(np.abs(grid_y - crease_y) / max(box["height"] * 0.72, 1.0), 2.0))

    broad_inner_field = inner_attraction * (0.78 + 0.22 * center_bias * vertical_bias)
    density = alpha * outer_falloff * (0.18 + 0.82 * broad_inner_field)
    active_values = density[active]
    scale = max(float(np.percentile(active_values, 99.2)), 1.0e-6)
    density = np.clip(density / scale, 0.0, 1.0)
    density = np.power(density, 0.92) * alpha

    stats = {
        "activeBbox": box,
        "activePixels": int(active.sum()),
        "seedPixels": int(seed.sum()),
        "maxEdgeDistanceP96": max_edge_distance,
        "attractionRadiusPx": attraction_radius,
        "densityMinActive": float(density[active].min()),
        "densityMeanActive": float(density[active].mean()),
        "densityP50Active": float(np.percentile(density[active], 50)),
        "densityP95Active": float(np.percentile(density[active], 95)),
        "densityMaxActive": float(density[active].max()),
    }
    return np.rint(np.clip(density, 0.0, 1.0) * 255).astype(np.uint8), stats


def channel_preview(channels: dict[str, Image.Image]) -> Image.Image:
    tile = 512
    sheet = Image.new("RGB", (tile * 2, tile * 2 + 60), (20, 20, 24))
    draw = ImageDraw.Draw(sheet)
    positions = {
        "R full": (0, 0, channels["r"]),
        "G overline": (tile, 0, channels["g"]),
        "B density": (0, tile + 30, channels["b"]),
        "A gloss": (tile, tile + 30, channels["a"]),
    }
    for label, (x, y, image) in positions.items():
        sheet.paste(image.convert("RGB"), (x, y + 30))
        draw.rectangle((x, y, x + tile, y + 30), fill=(35, 35, 42))
        draw.text((x + 12, y + 9), label, fill=(255, 255, 255))
    return sheet


def write_meta(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "fileFormatVersion: 2",
                f"guid: {UNITY_META_GUID}",
                "TextureImporter:",
                "  internalIDToNameTable: []",
                "  externalObjects: {}",
                "  serializedVersion: 13",
                "  mipmaps:",
                "    mipMapMode: 0",
                "    enableMipMap: 0",
                "    sRGBTexture: 0",
                "    linearTexture: 0",
                "    fadeOut: 0",
                "    borderMipMap: 0",
                "    mipMapsPreserveCoverage: 0",
                "    alphaTestReferenceValue: 0.5",
                "    mipMapFadeDistanceStart: 1",
                "    mipMapFadeDistanceEnd: 3",
                "  bumpmap:",
                "    convertToNormalMap: 0",
                "    externalNormalMap: 0",
                "    heightScale: 0.25",
                "    normalMapFilter: 0",
                "    flipGreenChannel: 0",
                "  isReadable: 1",
                "  streamingMipmaps: 0",
                "  streamingMipmapsPriority: 0",
                "  vTOnly: 0",
                "  ignoreMipmapLimit: 0",
                "  grayScaleToAlpha: 0",
                "  generateCubemap: 6",
                "  cubemapConvolution: 0",
                "  seamlessCubemap: 0",
                "  textureFormat: 1",
                "  maxTextureSize: 2048",
                "  textureSettings:",
                "    serializedVersion: 2",
                "    filterMode: 1",
                "    aniso: 1",
                "    mipBias: 0",
                "    wrapU: 1",
                "    wrapV: 1",
                "    wrapW: 1",
                "  nPOTScale: 1",
                "  lightmap: 0",
                "  compressionQuality: 50",
                "  spriteMode: 0",
                "  spriteExtrude: 1",
                "  spriteMeshType: 1",
                "  alignment: 0",
                "  spritePivot: {x: 0.5, y: 0.5}",
                "  spritePixelsToUnits: 100",
                "  spriteBorder: {x: 0, y: 0, z: 0, w: 0}",
                "  spriteGenerateFallbackPhysicsShape: 1",
                "  alphaUsage: 1",
                "  alphaIsTransparency: 0",
                "  spriteTessellationDetail: -1",
                "  textureType: 0",
                "  textureShape: 1",
                "  singleChannelComponent: 0",
                "  flipbookRows: 1",
                "  flipbookColumns: 1",
                "  maxTextureSizeSet: 0",
                "  compressionQualitySet: 0",
                "  textureFormatSet: 0",
                "  ignorePngGamma: 0",
                "  applyGammaDecoding: 0",
                "  swizzle: 50462976",
                "  cookieLightType: 0",
                "  platformSettings:",
                "  - serializedVersion: 4",
                "    buildTarget: DefaultTexturePlatform",
                "    maxTextureSize: 2048",
                "    resizeAlgorithm: 0",
                "    textureFormat: -1",
                "    textureCompression: 0",
                "    compressionQuality: 50",
                "    crunchedCompression: 0",
                "    allowsAlphaSplitting: 0",
                "    overridden: 0",
                "    ignorePlatformSupport: 0",
                "  assetBundleName: ",
                "  assetBundleVariant: ",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    source_path = resolve(repo, args.source)
    output_path = resolve(repo, args.output)
    evidence_dir = resolve(repo, args.evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source = np.asarray(Image.open(source_path).convert("RGBA"), dtype=np.uint8)
    density_b, stats = make_gradient_density(source[:, :, 0])
    output = source.copy()
    output[:, :, 2] = density_b
    output_image = Image.fromarray(output, mode="RGBA")
    output_image.save(output_path)
    write_meta(output_path.with_suffix(".png.meta"))

    channel_images = {
        "r": Image.fromarray(output[:, :, 0], mode="L"),
        "g": Image.fromarray(output[:, :, 1], mode="L"),
        "b": Image.fromarray(output[:, :, 2], mode="L"),
        "a": Image.fromarray(output[:, :, 3], mode="L"),
    }
    channel_preview(channel_images).save(evidence_dir / "lip_gradient_density_channels.png")
    output_image.save(evidence_dir / output_path.name)

    summary = {
        "status": "generated",
        "atlasId": "lip-drawn-gradient-density-atlas-v1",
        "sourceAtlas": source_path.relative_to(repo).as_posix(),
        "outputAtlas": output_path.relative_to(repo).as_posix(),
        "evidenceDir": evidence_dir.relative_to(repo).as_posix(),
        "channelContract": {
            "r": "copied full lip soft mask",
            "g": "copied overline channel",
            "b": "distance-transform continuous gradient density seed",
            "a": "copied gloss line channel",
        },
        "matteFreeze": "default lip-drawn-style-atlas-v1 is not overwritten",
        "densityStats": stats,
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (evidence_dir / "summary.md").write_text(
        "\n".join(
            [
                "# Lip Gradient Density Atlas",
                "",
                "- Status: `generated`",
                "- Atlas: `lip-drawn-gradient-density-atlas-v1`",
                "- B channel: distance-transform continuous density seed",
                "- Matte freeze: default `lip-drawn-style-atlas-v1` was not overwritten.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": "generated", **summary["densityStats"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
