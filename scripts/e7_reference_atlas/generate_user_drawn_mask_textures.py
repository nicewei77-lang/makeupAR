#!/usr/bin/env python3
"""Generate Unity-ready mask textures from user-drawn makeup region images."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_CAPTURE_PAIR = "pair_face_20260622T143334Z_03"
REGIONS = ("lip", "cheek", "eye")
REGION_COLORS = {
    "lip": (232, 58, 100, 190),
    "cheek": (255, 116, 88, 150),
    "eye": (103, 70, 255, 180),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract screen-space and ARFace-UV mask textures from user drawings."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--lip", type=Path, required=True)
    parser.add_argument("--cheek", type=Path, required=True)
    parser.add_argument("--eye", type=Path, required=True)
    parser.add_argument("--reference", type=Path, default=None)
    parser.add_argument("--capture-pair", type=str, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--unity-output-dir", type=Path, default=None)
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--dark-threshold", type=int, default=128)
    parser.add_argument("--min-component-pixels", type=int, default=450)
    parser.add_argument("--screen-sample-stride", type=int, default=1)
    return parser.parse_args()


def resolve_path(repo: Path, value: Path | None, fallback: Path | None = None) -> Path | None:
    selected = fallback if value is None else value
    if selected is None:
        return None
    return selected if selected.is_absolute() else repo / selected


def format_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo).as_posix()
    except ValueError:
        return str(path.resolve())


def load_dark_mask(path: Path, dark_threshold: int) -> np.ndarray:
    rgba = np.asarray(Image.open(path).convert("RGBA"))
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    darkness = rgb.mean(axis=2)
    return (alpha > 8) & (darkness < dark_threshold)


def keep_components(mask: np.ndarray, min_component_pixels: int) -> tuple[np.ndarray, dict[str, int]]:
    height, width = mask.shape
    visited = np.zeros(mask.shape, dtype=bool)
    output = np.zeros(mask.shape, dtype=np.uint8)
    component_count = 0
    kept_count = 0
    kept_pixels = 0
    removed_pixels = 0
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))

    ys, xs = np.nonzero(mask)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue

        component_count += 1
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

        if len(pixels) >= min_component_pixels:
            kept_count += 1
            kept_pixels += len(pixels)
            rows, cols = zip(*pixels)
            output[np.asarray(rows), np.asarray(cols)] = 255
        else:
            removed_pixels += len(pixels)

    return output, {
        "componentCount": component_count,
        "keptComponentCount": kept_count,
        "keptPixelCount": kept_pixels,
        "removedPixelCount": removed_pixels,
    }


def mask_stats(mask: np.ndarray) -> dict[str, object]:
    height, width = mask.shape
    ys, xs = np.nonzero(mask > 0)
    count = int(len(xs))
    bbox = None
    if count > 0:
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
        "pixelCount": count,
        "coverage": count / float(max(width * height, 1)),
        "bbox": bbox,
    }


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
        raise ValueError("ARFace export screenVertices/uvs length mismatch.")
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
        scale = max(float(positive.max()), 1.0)
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

        weight_a = (((y2 - y3) * (pixel_x - x3) + (x3 - x2) * (pixel_y - y3)) / denominator)
        weight_b = (((y3 - y1) * (pixel_x - x3) + (x1 - x3) * (pixel_y - y3)) / denominator)
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

    hard = normalize_density(density)
    stats = mask_stats(np.asarray(hard, dtype=np.uint8))
    stats.update(
        {
            "hitTriangleCount": hit_triangle_count,
            "hitSampleCount": hit_sample_count,
            "rawUvPixelCount": int((density > 0).sum()),
            "skippedDegenerateTriangleCount": skipped_degenerate_triangle_count,
            "screenSampleStride": sample_stride,
        }
    )
    return hard, stats


def expand(channel: Image.Image, size: int) -> Image.Image:
    return channel.filter(ImageFilter.MaxFilter(size))


def multiply(channel: Image.Image, amount: float) -> Image.Image:
    values = np.asarray(channel.convert("L"), dtype=np.float32)
    return Image.fromarray(np.rint(np.clip(values * amount, 0, 255)).astype(np.uint8), mode="L")


def make_alpha_png(mask: Image.Image) -> Image.Image:
    alpha = mask.convert("L")
    white = Image.new("L", alpha.size, 255)
    return Image.merge("RGBA", (white, white, white, alpha))


def make_rgba_mask(mask: Image.Image) -> Image.Image:
    channel = mask.convert("L")
    return Image.merge("RGBA", (channel, channel, channel, channel))


def center_density(mask: Image.Image) -> Image.Image:
    alpha = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    ys, xs = np.nonzero(alpha > 0.05)
    if len(xs) == 0:
        return Image.new("L", mask.size, 0)

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


def lip_gloss(mask: Image.Image) -> Image.Image:
    alpha = np.asarray(mask.convert("L"), dtype=np.float32) / 255.0
    ys, xs = np.nonzero(alpha > 0.05)
    if len(xs) == 0:
        return Image.new("L", mask.size, 0)

    center_x = float(xs.mean())
    width = max(float(xs.max() - xs.min()), 1.0)
    height = max(float(ys.max() - ys.min()), 1.0)
    grid_y, grid_x = np.indices(alpha.shape)
    line_y = float(round(float(ys.min()) + height * 0.76))
    line_sigma = max(0.25, height * 0.006)
    line = np.exp(-(((grid_y - line_y) / line_sigma) ** 2))
    horizontal = np.exp(-(((grid_x - center_x) / max(1.0, width * 0.13)) ** 4))
    gloss = alpha * line * horizontal
    return Image.fromarray(np.rint(np.clip(gloss, 0.0, 1.0) * 255).astype(np.uint8), mode="L")


def make_region_variants(hard: Image.Image) -> dict[str, Image.Image]:
    hard = hard.convert("L")
    return {
        "hard": hard,
        "soft": hard.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(radius=1.25)),
        "expanded": hard.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(radius=1.8)),
    }


def trim_horizontal_uv_seams(channel: Image.Image, margin: int = 42) -> Image.Image:
    values = np.asarray(channel.convert("L"), dtype=np.uint8).copy()
    values[:, :margin] = 0
    values[:, values.shape[1] - margin :] = 0
    return Image.fromarray(values, mode="L")


def make_lip_style_atlas(variants: dict[str, Image.Image]) -> Image.Image:
    full = variants["soft"]
    overline = multiply(variants["expanded"], 0.66)
    gradient = center_density(full)
    gloss = multiply(lip_gloss(full).filter(ImageFilter.GaussianBlur(radius=0.35)), 0.96)
    return Image.merge("RGBA", (full, overline, gradient, gloss))


def overlay_masks(base: Image.Image, masks: dict[str, Image.Image]) -> Image.Image:
    output = base.convert("RGBA")
    for region, mask in masks.items():
        color = Image.new("RGBA", output.size, REGION_COLORS[region])
        alpha = mask.convert("L").filter(ImageFilter.GaussianBlur(radius=1.2))
        color.putalpha(alpha.point(lambda value: min(value, REGION_COLORS[region][3])))
        output = Image.alpha_composite(output, color)
    return output


def make_contact_sheet(images: list[tuple[str, Image.Image]], tile: int = 320) -> Image.Image:
    columns = 3
    rows = int(np.ceil(len(images) / columns))
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 30)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * tile
        y = row * (tile + 30)
        thumb = image.convert("RGB").copy()
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        paste_x = x + (tile - thumb.width) // 2
        paste_y = y + 24 + (tile - thumb.height) // 2
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0))
        sheet.paste(thumb, (paste_x, paste_y))
    return sheet


def write_unity_meta(path: Path, guid_seed: str) -> None:
    guid = hashlib.md5(guid_seed.encode("utf-8")).hexdigest()
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
    buildTarget: iOS
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


def save(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output_dir = resolve_path(
        repo,
        args.output_dir,
        Path("evidence/e7-reference-atlas/user-drawn-mask-textures-v1"),
    )
    unity_dir = resolve_path(
        repo,
        args.unity_output_dir,
        Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"),
    )
    pair_dir = resolve_path(
        repo,
        args.capture_dir,
        Path("evidence/e7-reference-atlas/capture_pairs") / args.capture_pair,
    )
    assert output_dir is not None
    assert unity_dir is not None
    assert pair_dir is not None
    arface_path = pair_dir / "arface_export.json"
    frame_path = pair_dir / "frame.png"
    reference_path = resolve_path(repo, args.reference) if args.reference else frame_path

    source_paths = {
        "lip": resolve_path(repo, args.lip),
        "cheek": resolve_path(repo, args.cheek),
        "eye": resolve_path(repo, args.eye),
    }
    if any(path is None or not path.exists() for path in source_paths.values()):
        raise FileNotFoundError("One or more source drawing files are missing.")
    if not arface_path.exists():
        raise FileNotFoundError("ARFace export does not exist: " + str(arface_path))
    if reference_path is None or not reference_path.exists():
        raise FileNotFoundError("Reference image does not exist.")

    arface = load_arface_export(arface_path)
    screen_masks: dict[str, Image.Image] = {}
    uv_variants: dict[str, dict[str, Image.Image]] = {}
    summaries: dict[str, object] = {}
    contact_images: list[tuple[str, Image.Image]] = []

    expected_size = None
    for region in REGIONS:
        source_path = source_paths[region]
        assert source_path is not None
        raw = load_dark_mask(source_path, args.dark_threshold)
        clean, component_stats = keep_components(raw, args.min_component_pixels)
        if expected_size is None:
            expected_size = clean.shape
        elif clean.shape != expected_size:
            raise ValueError("All source drawings must share the same canvas size.")

        screen = Image.fromarray(clean, mode="L")
        screen_masks[region] = screen
        uv_hard, uv_stats = back_project_mask_to_uv(
            clean,
            arface,
            args.resolution,
            args.screen_sample_stride,
        )
        variants = make_region_variants(uv_hard)
        if region == "cheek":
            variants["safe"] = trim_horizontal_uv_seams(variants["soft"])
        uv_variants[region] = variants

        save(output_dir / "screen" / f"{region}_source_clean_1179x2556.png", screen)
        save(output_dir / "screen" / f"{region}_source_alpha_1179x2556.png", make_alpha_png(screen))
        for name, image in variants.items():
            save(output_dir / "uv" / f"{region}_uv_{name}_{args.resolution}.png", image)
        save(
            output_dir / "uv" / f"{region}_uv_rgba_variants_{args.resolution}.png",
            Image.merge(
                "RGBA",
                (variants["hard"], variants["soft"], variants["expanded"], variants["soft"]),
            ),
        )

        unity_variant = "safe" if "safe" in variants else "soft"
        unity_name = f"{region}-drawn-mask-v1.png"
        unity_path = unity_dir / unity_name
        save(unity_path, make_rgba_mask(variants[unity_variant]))
        write_unity_meta(unity_path.with_suffix(".png.meta"), f"e7-user-drawn-{unity_name}")

        summaries[region] = {
            "sourcePath": format_path(repo, source_path),
            "sourceStats": mask_stats(clean),
            "componentStats": component_stats,
            "uvStats": uv_stats,
            "unityMaskPath": format_path(repo, unity_path),
            "unityMaskVariant": unity_variant,
            "evidenceUvSoftPath": format_path(
                repo, output_dir / "uv" / f"{region}_uv_soft_{args.resolution}.png"
            ),
        }
        contact_images.extend(
            [
                (f"{region} screen", screen),
                (f"{region} uv hard", variants["hard"]),
                (f"{region} uv soft", variants["soft"]),
            ]
        )

    lip_style = make_lip_style_atlas(uv_variants["lip"])
    lip_style_path = unity_dir / "lip-drawn-style-atlas-v1.png"
    save(lip_style_path, lip_style)
    write_unity_meta(lip_style_path.with_suffix(".png.meta"), "e7-user-drawn-lip-style-atlas-v1")
    save(output_dir / "uv" / "lip_drawn_style_atlas_v1.png", lip_style)

    composite_alpha = Image.fromarray(
        np.maximum.reduce(
            [
                np.asarray(
                    uv_variants[region].get("safe", uv_variants[region]["soft"]),
                    dtype=np.uint8,
                )
                for region in REGIONS
            ]
        ),
        mode="L",
    )
    composite = Image.merge(
        "RGBA",
        (
            uv_variants["lip"].get("safe", uv_variants["lip"]["soft"]),
            uv_variants["cheek"].get("safe", uv_variants["cheek"]["soft"]),
            uv_variants["eye"].get("safe", uv_variants["eye"]["soft"]),
            composite_alpha,
        ),
    )
    composite_path = unity_dir / "drawn-makeup-composite-atlas-v1.png"
    save(composite_path, composite)
    write_unity_meta(composite_path.with_suffix(".png.meta"), "e7-user-drawn-composite-atlas-v1")
    save(output_dir / "uv" / "drawn_makeup_composite_rgba_v1.png", composite)

    reference = Image.open(reference_path).convert("RGB")
    if reference.size == screen_masks["lip"].size:
        screen_overlay = overlay_masks(reference, screen_masks)
        save(output_dir / "screen" / "drawn_makeup_screen_overlay.png", screen_overlay)
        contact_images.insert(0, ("screen overlay", screen_overlay))

    contact_sheet = make_contact_sheet(contact_images)
    save(output_dir / "mask_texture_contact_sheet.png", contact_sheet)

    summary = {
        "textureSetId": "user-drawn-mask-textures-v1",
        "coordinateSpace": f"{screen_masks['lip'].size[0]}x{screen_masks['lip'].size[1]}",
        "uvResolution": args.resolution,
        "capturePairId": pair_dir.name,
        "arfaceExportPath": format_path(repo, arface_path),
        "referencePath": format_path(repo, reference_path),
        "outputDir": format_path(repo, output_dir),
        "unityOutputDir": format_path(repo, unity_dir),
        "unityTextures": {
            "lipDrawnMask": format_path(repo, unity_dir / "lip-drawn-mask-v1.png"),
            "cheekDrawnMask": format_path(repo, unity_dir / "cheek-drawn-mask-v1.png"),
            "eyeDrawnMask": format_path(repo, unity_dir / "eye-drawn-mask-v1.png"),
            "lipDrawnStyleAtlas": format_path(repo, lip_style_path),
            "drawnMakeupCompositeAtlas": format_path(repo, composite_path),
        },
        "regions": summaries,
    }
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "summary.md").write_text(
        "# User Drawn Mask Textures v1\n\n"
        f"- coordinateSpace: `{summary['coordinateSpace']}`\n"
        f"- uvResolution: `{summary['uvResolution']}`\n"
        f"- capturePairId: `{summary['capturePairId']}`\n"
        f"- unityOutputDir: `{summary['unityOutputDir']}`\n"
        f"- contactSheet: `{format_path(repo, output_dir / 'mask_texture_contact_sheet.png')}`\n"
        f"- zip: `{format_path(repo, output_dir / 'user-drawn-mask-textures-v1.zip')}`\n\n"
        "## Unity Textures\n\n"
        + "\n".join(f"- `{name}`: `{path}`" for name, path in summary["unityTextures"].items())
        + "\n",
        encoding="utf-8",
    )

    zip_path = output_dir / "user-drawn-mask-textures-v1.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            archive.write(path, path.relative_to(output_dir))
        for path in sorted(unity_dir.glob("*drawn*mask-v1.png")) + sorted(
            unity_dir.glob("*drawn*atlas-v1.png")
        ):
            archive.write(path, Path("unity") / path.name)

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
