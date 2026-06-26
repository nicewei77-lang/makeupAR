#!/usr/bin/env python3
"""Generate the E7 validation lip style atlas from a synchronized lip marking.

The source marking is screen-space evidence. The preferred runtime texture is a
single-frame ARFace UV back-projection from that marking, with the existing
smooth lip mask kept as a fallback scaffold when projection evidence is missing.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ATLAS_ID = "lip-style-atlas-v1"
DEFAULT_CAPTURE_PAIR = "pair_face_20260622T143334Z_03"
UNITY_META_GUID = "e703b90e3e9b4d729e7a4a8cf4d00137"
CHANNEL_DESCRIPTIONS = {
    "r": "full lip surface from projected ARFace UV lip candidate",
    "g": "subtle overline safe zone from projected lip candidate",
    "b": "inner center gradient density",
    "a": "lower-lip gloss highlight weight",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E7 lip style atlas v1.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--source-marking",
        type=Path,
        required=True,
        help="1179x2556 lip-only user marking in the capture frame coordinate space.",
    )
    parser.add_argument(
        "--capture-pair",
        type=str,
        default=DEFAULT_CAPTURE_PAIR,
        help="Capture-pair id under evidence/e7-reference-atlas/capture_pairs.",
    )
    parser.add_argument(
        "--capture-dir",
        type=Path,
        default=None,
        help="Explicit capture-pair directory. Overrides --capture-pair when provided.",
    )
    parser.add_argument(
        "--output-atlas",
        type=Path,
        default=None,
        help="Runtime RGBA atlas output. Defaults to Unity Resources/SmoothRegionMasks.",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Evidence output directory for candidate masks, previews, and summaries.",
    )
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument(
        "--projection-mode",
        choices=("auto", "back-project", "scaffold"),
        default="auto",
        help="Use screen-marking to ARFace UV back-projection, fallback scaffold, or auto fallback.",
    )
    parser.add_argument(
        "--screen-sample-stride",
        type=int,
        default=1,
        help="Pixel stride while sampling the source marking inside projected ARFace triangles.",
    )
    return parser.parse_args()


def resolve_path(repo: Path, path: Path | None, fallback: Path) -> Path:
    selected = fallback if path is None else path
    return selected if selected.is_absolute() else repo / selected


def format_repo_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return str(path.resolve())


def dark_mask(path: Path) -> np.ndarray:
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    darkness = rgb.mean(axis=2)
    return (alpha > 8) & (darkness < 96)


def largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    best_pixels: list[tuple[int, int]] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    ys, xs = np.nonzero(mask)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue

        queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []

        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            for dy, dx in neighbors:
                ny = y + dy
                nx = x + dx
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and mask[ny, nx]
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    queue.append((ny, nx))

        if len(pixels) > len(best_pixels):
            best_pixels = pixels

    output = np.zeros(mask.shape, dtype=np.uint8)
    if best_pixels:
        rows, cols = zip(*best_pixels)
        output[np.asarray(rows), np.asarray(cols)] = 255
    return output


def mask_stats(mask: np.ndarray) -> dict[str, object]:
    height, width = mask.shape
    ys, xs = np.nonzero(mask > 0)
    pixel_count = int(len(xs))
    coverage = pixel_count / float(max(width * height, 1))

    if pixel_count == 0:
        bbox = None
    else:
        bbox = {
            "left": int(xs.min()),
            "top": int(ys.min()),
            "right": int(xs.max()),
            "bottom": int(ys.max()),
            "width": int(xs.max() - xs.min() + 1),
            "height": int(ys.max() - ys.min() + 1),
        }

    return {
        "width": width,
        "height": height,
        "pixelCount": pixel_count,
        "coverage": coverage,
        "bbox": bbox,
    }


def validate_lip_candidate(stats: dict[str, object]) -> None:
    bbox = stats["bbox"]
    width = int(stats["width"])
    height = int(stats["height"])
    coverage = float(stats["coverage"])

    if bbox is None:
        raise ValueError("Source marking did not contain a dark lip candidate.")

    bbox_width = int(bbox["width"])
    bbox_height = int(bbox["height"])
    if coverage > 0.025 or bbox_width / float(width) > 0.36 or bbox_height / float(height) > 0.13:
        raise ValueError(
            "Source marking is too broad for lip-only validation; "
            "stop before treating it as a gold mask candidate."
        )


def load_arface_export(path: Path) -> dict[str, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    screen_vertices = np.asarray(data.get("screenVertices", []), dtype=np.float32)
    uvs = np.asarray(data.get("uvs", []), dtype=np.float32)
    indices = np.asarray(data.get("indices", []), dtype=np.int32)

    if screen_vertices.ndim != 2 or screen_vertices.shape[1] < 2:
        raise ValueError("ARFace export is missing screenVertices.")
    if uvs.ndim != 2 or uvs.shape[1] < 2:
        raise ValueError("ARFace export is missing uvs.")
    if len(screen_vertices) != len(uvs):
        raise ValueError(
            "ARFace export screenVertices/uvs length mismatch: "
            f"{len(screen_vertices)} != {len(uvs)}"
        )
    if len(indices) < 3 or len(indices) % 3 != 0:
        raise ValueError("ARFace export indices are missing or not triangle aligned.")

    return {
        "screenVertices": screen_vertices[:, :2],
        "uvs": uvs[:, :2],
        "indices": indices.reshape((-1, 3)),
    }


def normalize_density(values: np.ndarray) -> Image.Image:
    if not np.any(values > 0):
        return Image.fromarray(np.zeros(values.shape, dtype=np.uint8), mode="L")

    positive = values[values > 0]
    scale = float(np.percentile(positive, 95))
    if scale <= 0:
        scale = float(positive.max())
    if scale <= 0:
        scale = 1.0

    normalized = np.clip(values / scale, 0.0, 1.0)
    return Image.fromarray(np.rint(normalized * 255).astype(np.uint8), mode="L")


def back_project_mask_to_uv(
    source_mask: np.ndarray,
    arface: dict[str, np.ndarray],
    resolution: int,
    sample_stride: int,
) -> tuple[Image.Image, dict[str, object]]:
    mask = source_mask > 0
    rows, cols = np.nonzero(mask)
    if len(cols) == 0:
        raise ValueError("Cannot back-project an empty source mask.")

    sample_stride = max(1, int(sample_stride))
    mask_left = int(cols.min())
    mask_right = int(cols.max())
    mask_top = int(rows.min())
    mask_bottom = int(rows.max())
    screen_vertices = arface["screenVertices"]
    uvs = arface["uvs"]
    triangles = arface["indices"]
    density = np.zeros((resolution, resolution), dtype=np.float32)
    hit_triangle_count = 0
    hit_sample_count = 0
    skipped_degenerate_triangle_count = 0
    epsilon = 1.0e-4

    for triangle in triangles:
        screen_points = screen_vertices[triangle]
        uv_points = uvs[triangle]
        left = max(int(np.floor(float(screen_points[:, 0].min()))), mask_left)
        right = min(int(np.ceil(float(screen_points[:, 0].max()))), mask_right)
        top = max(int(np.floor(float(screen_points[:, 1].min()))), mask_top)
        bottom = min(int(np.ceil(float(screen_points[:, 1].max()))), mask_bottom)

        if right < left or bottom < top:
            continue

        x1, y1 = screen_points[0]
        x2, y2 = screen_points[1]
        x3, y3 = screen_points[2]
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(float(denominator)) < 1.0e-5:
            skipped_degenerate_triangle_count += 1
            continue

        grid_x = np.arange(left, right + 1, sample_stride, dtype=np.float32) + 0.5
        grid_y = np.arange(top, bottom + 1, sample_stride, dtype=np.float32) + 0.5
        pixel_x, pixel_y = np.meshgrid(grid_x, grid_y)
        source_x = np.clip(pixel_x.astype(np.int32), 0, mask.shape[1] - 1)
        source_y = np.clip(pixel_y.astype(np.int32), 0, mask.shape[0] - 1)
        mask_samples = mask[source_y, source_x]

        if not mask_samples.any():
            continue

        weight_a = (
            ((y2 - y3) * (pixel_x - x3) + (x3 - x2) * (pixel_y - y3))
            / denominator
        )
        weight_b = (
            ((y3 - y1) * (pixel_x - x3) + (x1 - x3) * (pixel_y - y3))
            / denominator
        )
        weight_c = 1.0 - weight_a - weight_b
        inside_triangle = (
            (weight_a >= -epsilon)
            & (weight_b >= -epsilon)
            & (weight_c >= -epsilon)
            & mask_samples
        )

        if not inside_triangle.any():
            continue

        hit_triangle_count += 1
        hit_sample_count += int(inside_triangle.sum())
        projected_u = (
            weight_a[inside_triangle] * uv_points[0, 0]
            + weight_b[inside_triangle] * uv_points[1, 0]
            + weight_c[inside_triangle] * uv_points[2, 0]
        )
        projected_v = (
            weight_a[inside_triangle] * uv_points[0, 1]
            + weight_b[inside_triangle] * uv_points[1, 1]
            + weight_c[inside_triangle] * uv_points[2, 1]
        )
        valid_uv = (
            (projected_u >= 0.0)
            & (projected_u <= 1.0)
            & (projected_v >= 0.0)
            & (projected_v <= 1.0)
        )

        if not valid_uv.any():
            continue

        atlas_x = np.rint(projected_u[valid_uv] * (resolution - 1)).astype(np.int32)
        atlas_y = np.rint((1.0 - projected_v[valid_uv]) * (resolution - 1)).astype(np.int32)
        np.add.at(density, (atlas_y, atlas_x), 1.0)

    raw_mask = normalize_density(density)
    projected_mask = raw_mask.filter(ImageFilter.MaxFilter(3)).filter(
        ImageFilter.GaussianBlur(radius=0.65)
    )
    projected_values = np.asarray(projected_mask, dtype=np.uint8)
    projected_stats = mask_stats(projected_values)
    projected_stats.update(
        {
            "hitTriangleCount": hit_triangle_count,
            "hitSampleCount": hit_sample_count,
            "rawUvPixelCount": int((density > 0).sum()),
            "skippedDegenerateTriangleCount": skipped_degenerate_triangle_count,
            "screenSampleStride": sample_stride,
        }
    )
    return projected_mask, projected_stats


def is_projection_usable(stats: dict[str, object]) -> bool:
    coverage = float(stats["coverage"])
    return (
        int(stats.get("hitSampleCount", 0)) >= 1000
        and int(stats.get("rawUvPixelCount", 0)) >= 500
        and 0.002 <= coverage <= 0.028
        and stats["bbox"] is not None
    )


def normalize_channel(channel: Image.Image, resolution: int) -> Image.Image:
    return channel.convert("L").resize((resolution, resolution), Image.Resampling.LANCZOS)


def blur(channel: Image.Image, radius: float) -> Image.Image:
    return channel.filter(ImageFilter.GaussianBlur(radius=radius))


def expand(channel: Image.Image, size: int) -> Image.Image:
    return channel.filter(ImageFilter.MaxFilter(size=size))


def multiply_channel(channel: Image.Image, amount: float) -> Image.Image:
    values = np.asarray(channel.convert("L"), dtype=np.float32)
    values = np.clip(values * amount, 0, 255).astype(np.uint8)
    return Image.fromarray(values, mode="L")


def center_gradient(full: Image.Image) -> Image.Image:
    alpha = np.asarray(full.convert("L"), dtype=np.float32) / 255.0
    ys, xs = np.nonzero(alpha > 0.05)
    if len(xs) == 0:
        return Image.new("L", full.size, 0)

    center_x = float(xs.mean())
    center_y = float(ys.mean())
    width = max(float(xs.max() - xs.min()), 1.0)
    height = max(float(ys.max() - ys.min()), 1.0)
    grid_y, grid_x = np.indices(alpha.shape)
    norm = ((grid_x - center_x) / (width * 0.52)) ** 2 + (
        (grid_y - center_y) / (height * 0.38)
    ) ** 2
    gradient = np.clip(1.0 - norm, 0.0, 1.0) * alpha
    return Image.fromarray(np.rint(gradient * 255).astype(np.uint8), mode="L")


def gloss_weight(full: Image.Image) -> Image.Image:
    alpha = np.asarray(full.convert("L"), dtype=np.float32) / 255.0
    ys, xs = np.nonzero(alpha > 0.05)
    if len(xs) == 0:
        return Image.new("L", full.size, 0)

    center_x = float(xs.mean())
    width = max(float(xs.max() - xs.min()), 1.0)
    height = max(float(ys.max() - ys.min()), 1.0)
    grid_y, grid_x = np.indices(alpha.shape)
    line_y = float(ys.min()) + height * 0.68
    line_sigma = max(0.85, height * 0.018)
    line = np.exp(-(((grid_y - line_y) / line_sigma) ** 2))
    horizontal = np.exp(-(((grid_x - center_x) / max(1.0, width * 0.24)) ** 4))
    gloss = alpha * line * horizontal
    return Image.fromarray(np.rint(np.clip(gloss, 0.0, 1.0) * 255).astype(np.uint8), mode="L")


def channel_preview(channels: dict[str, Image.Image]) -> Image.Image:
    tile_size = next(iter(channels.values())).size[0]
    preview = Image.new("RGB", (tile_size * 2, tile_size * 2), (255, 255, 255))
    draw = ImageDraw.Draw(preview)
    placements = {
        "R full": (0, 0, channels["r"]),
        "G overline": (tile_size, 0, channels["g"]),
        "B gradient": (0, tile_size, channels["b"]),
        "A gloss": (tile_size, tile_size, channels["a"]),
    }

    for label, (x, y, channel) in placements.items():
        rgb = Image.merge("RGB", (channel, channel, channel))
        preview.paste(rgb, (x, y))
        draw.rectangle((x, y, x + 118, y + 22), fill=(255, 255, 255))
        draw.text((x + 6, y + 5), label, fill=(0, 0, 0))

    return preview


def write_summary_md(path: Path, summary: dict[str, object]) -> None:
    channels = summary["channels"]
    stats = summary["sourceMarkingStats"]
    bbox = stats["bbox"]
    lines = [
        "# E7 Lip Style Atlas v1 Summary",
        "",
        "## Inputs",
        "",
        f"- atlasId: `{summary['atlasId']}`",
        f"- capturePairId: `{summary['capturePairId']}`",
        f"- sourceMarkingPath: `{summary['sourceMarkingPath']}`",
        f"- sourceFramePath: `{summary['sourceFramePath']}`",
        f"- arfaceExportPath: `{summary['arfaceExportPath']}`",
        f"- runtimeAtlasPath: `{summary['runtimeAtlasPath']}`",
        f"- projectionMode: `{summary['projectionMode']}`",
        f"- runtimeMaskSource: `{summary['runtimeMaskSource']}`",
        f"- projectionUsed: `{summary['projectionUsed']}`",
        f"- projectionFallbackReason: `{summary['projectionFallbackReason']}`",
        "",
        "## Source Candidate",
        "",
        f"- coordinateSpace: `{summary['coordinateSpace']}`",
        f"- retainedPixelCount: `{stats['pixelCount']}`",
        f"- retainedCoverage: `{float(stats['coverage']):0.6f}`",
        f"- retainedBBox: `{bbox}`",
        f"- removedDarkPixelCount: `{summary['removedDarkPixelCount']}`",
        "",
        "## UV Back Projection",
        "",
        f"- trueUvBackProjection: `{summary['trueUvBackProjection']}`",
        f"- uvBackProjectionStats: `{summary['uvBackProjectionStats']}`",
        "",
        "## Runtime Channels",
        "",
    ]

    for channel, description in channels.items():
        lines.append(f"- `{channel.upper()}`: {description}")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "- This is a validation v1 style atlas, not product-grade segmentation.",
            "- It is not eligible as E7.3 Green evidence without real-device runtime visual evidence.",
            "- The source marking passed lip-only size/coverage guards, but semantic teeth/inner-mouth spill still requires visual review.",
            "",
        ]
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def write_meta(path: Path, guid: str) -> None:
    path.write_text(
        f"""fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 13
  mipmaps:
    mipMapMode: 0
    enableMipMap: 0
    sRGBTexture: 0
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 1
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 1
  lightmap: 0
  compressionQuality: 50
  spriteMode: 0
  spriteExtrude: 1
  spriteMeshType: 1
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 1
  alphaUsage: 1
  alphaIsTransparency: 0
  spriteTessellationDetail: -1
  textureType: 0
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 4
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 0
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  - serializedVersion: 4
    buildTarget: Standalone
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  - serializedVersion: 4
    buildTarget: iOS
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 1
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    customData: 
    physicsShape: []
    bones: []
    spriteID: 
    internalID: 0
    vertices: []
    indices: 
    edges: []
    weights: []
    secondaryTextures: []
    nameFileIdTable: {{}}
  mipmapLimitGroupName: 
  pSDRemoveMatte: 0
  userData: 
  assetBundleName: 
  assetBundleVariant: 
""",
        encoding="utf-8",
    )


def save_images(images: Iterable[tuple[Path, Image.Image]]) -> None:
    for path, image in images:
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    pair_dir = resolve_path(
        repo,
        args.capture_dir,
        Path("evidence/e7-reference-atlas/capture_pairs") / args.capture_pair,
    )
    frame_path = pair_dir / "frame.png"
    arface_export_path = pair_dir / "arface_export.json"
    existing_lip_mask_path = (
        repo
        / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-smooth-mask-v1.png"
    )
    atlas_path = resolve_path(
        repo,
        args.output_atlas,
        Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
        / f"{ATLAS_ID}.png",
    )
    evidence_dir = resolve_path(
        repo,
        args.evidence_dir,
        Path("evidence/e7-reference-atlas") / ATLAS_ID,
    )

    source_marking = resolve_path(repo, args.source_marking, args.source_marking)
    if not source_marking.exists():
        raise FileNotFoundError("Source marking does not exist: " + str(source_marking))
    if not frame_path.exists():
        raise FileNotFoundError("Capture frame does not exist: " + str(frame_path))
    if not arface_export_path.exists() and args.projection_mode != "scaffold":
        raise FileNotFoundError("ARFace export does not exist: " + str(arface_export_path))
    if not existing_lip_mask_path.exists():
        raise FileNotFoundError("Smooth lip mask does not exist: " + str(existing_lip_mask_path))

    frame = Image.open(frame_path).convert("RGB")
    raw_dark = dark_mask(source_marking)
    if raw_dark.shape != (frame.height, frame.width):
        raise ValueError(
            "Source marking size must match capture frame size. "
            f"source={raw_dark.shape[1]}x{raw_dark.shape[0]} "
            f"frame={frame.width}x{frame.height}"
        )

    source_mask = largest_component(raw_dark)
    retained_stats = mask_stats(source_mask)
    validate_lip_candidate(retained_stats)
    gold_mask = Image.fromarray(source_mask, mode="L")

    overlay = frame.copy().convert("RGBA")
    red = Image.new("RGBA", overlay.size, (217, 75, 116, 0))
    red.putalpha(blur(gold_mask, 2.2))
    overlay = Image.alpha_composite(overlay, red)

    scaffold_base = normalize_channel(Image.open(existing_lip_mask_path), args.resolution)
    projection_stats: dict[str, object] | None = None
    projection_used = False
    projection_fallback_reason = "projection_mode_scaffold"

    if args.projection_mode != "scaffold":
        arface = load_arface_export(arface_export_path)
        projected_base, projection_stats = back_project_mask_to_uv(
            source_mask,
            arface,
            args.resolution,
            args.screen_sample_stride,
        )
        if is_projection_usable(projection_stats):
            base = projected_base
            projection_used = True
            projection_fallback_reason = "none"
        elif args.projection_mode == "back-project":
            raise ValueError(
                "ARFace UV back-projection was not usable: "
                + json.dumps(projection_stats, ensure_ascii=False)
            )
        else:
            base = scaffold_base
            projection_fallback_reason = "projection_quality_guard_failed"
    else:
        base = scaffold_base

    full = blur(base, 0.7 if projection_used else 1.0)
    overline = multiply_channel(
        blur(expand(base, 5 if projection_used else 7), 1.1 if projection_used else 1.5),
        0.58 if projection_used else 0.78,
    )
    gradient = center_gradient(full)
    gloss = multiply_channel(blur(gloss_weight(full), 0.35), 0.96)
    atlas = Image.merge("RGBA", (full, overline, gradient, gloss))
    preview = channel_preview({"r": full, "g": overline, "b": gradient, "a": gloss})

    output_images = [
        (evidence_dir / "lip_gold_mask_candidate.png", gold_mask),
        (evidence_dir / "lip_gold_mask_overlay.png", overlay.convert("RGB")),
        (evidence_dir / "lip_style_atlas_v1_preview.png", atlas),
        (evidence_dir / "lip_style_atlas_v1_channels.png", preview),
        (atlas_path, atlas),
    ]
    if projection_stats is not None:
        output_images.append((evidence_dir / "lip_uv_backprojected_mask.png", base))
    save_images(output_images)
    write_meta(atlas_path.with_suffix(".png.meta"), UNITY_META_GUID)

    summary = {
        "atlasId": ATLAS_ID,
        "capturePairId": pair_dir.name,
        "sourceMarkingPath": format_repo_path(repo, source_marking),
        "sourceFramePath": format_repo_path(repo, frame_path),
        "arfaceExportPath": format_repo_path(repo, arface_export_path),
        "runtimeAtlasPath": format_repo_path(repo, atlas_path),
        "evidenceDirectory": format_repo_path(repo, evidence_dir),
        "coordinateSpace": f"{frame.width}x{frame.height}",
        "resolution": args.resolution,
        "projectionMode": args.projection_mode,
        "runtimeMaskSource": "arface_uv_back_projection" if projection_used else "smooth_mask_scaffold",
        "projectionUsed": projection_used,
        "projectionFallbackReason": projection_fallback_reason,
        "uvBackProjectionStats": projection_stats,
        "channels": CHANNEL_DESCRIPTIONS,
        "sourceMarkingStats": retained_stats,
        "rawDarkPixelCount": int(raw_dark.sum()),
        "removedDarkPixelCount": int(raw_dark.sum()) - int(retained_stats["pixelCount"]),
        "trueUvBackProjection": projection_used,
        "greenEvidenceEligible": False,
        "notes": [
            "Validation v1 atlas; not product-grade segmentation.",
            "Largest dark component was retained from the user marking to remove stray dots.",
            "Runtime atlas uses single-frame screen marking to ARFace UV back-projection when projection quality guards pass.",
            "This is not E7.3 Green evidence without real-device runtime visual review.",
        ],
    }
    (evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_summary_md(evidence_dir / "summary.md", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
