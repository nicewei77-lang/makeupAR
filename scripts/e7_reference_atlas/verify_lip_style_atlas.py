#!/usr/bin/env python3
"""Verify that the E7 lip style atlas is the tight UV back-projected variant."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


DEFAULT_ATLAS_DIR = Path("evidence/e7-reference-atlas/lip-style-atlas-v1")
DEFAULT_OLD_MASK = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-smooth-mask-v1.png"
)
DEFAULT_NEW_ATLAS = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-style-atlas-v1.png"
)
DEFAULT_OVERLAY_SCRIPT = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
)
DEFAULT_RN_BRIDGE = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
DEFAULT_RN_APP = Path("rn/MakeupARValidation/App.tsx")
DEFAULT_CAPTURE_EXPORT = Path(
    "evidence/e7-reference-atlas/capture_pairs/"
    "pair_face_20260622T143334Z_03/arface_export.json"
)
DEFAULT_CAPTURE_FRAME = Path(
    "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify E7 lip style atlas v1.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--atlas-dir", type=Path, default=DEFAULT_ATLAS_DIR)
    parser.add_argument("--old-mask", type=Path, default=DEFAULT_OLD_MASK)
    parser.add_argument("--new-atlas", type=Path, default=DEFAULT_NEW_ATLAS)
    parser.add_argument("--overlay-script", type=Path, default=DEFAULT_OVERLAY_SCRIPT)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--rn-app", type=Path, default=DEFAULT_RN_APP)
    parser.add_argument("--capture-export", type=Path, default=DEFAULT_CAPTURE_EXPORT)
    parser.add_argument("--capture-frame", type=Path, default=DEFAULT_CAPTURE_FRAME)
    parser.add_argument("--source-screen-mask", type=Path, default=None)
    parser.add_argument("--roundtrip-mask-output", type=Path, default=None)
    parser.add_argument("--roundtrip-preview-output", type=Path, default=None)
    parser.add_argument("--roundtrip-json-output", type=Path, default=None)
    parser.add_argument("--max-new-gt8-pixels", type=int, default=4500)
    parser.add_argument("--min-old-to-new-gt8-ratio", type=float, default=2.0)
    parser.add_argument("--min-hit-samples", type=int, default=10000)
    parser.add_argument("--max-new-bbox-height", type=int, default=64)
    parser.add_argument("--max-threshold", type=float, default=0.12)
    parser.add_argument("--max-feather", type=float, default=0.34)
    parser.add_argument("--max-accepted-triangles", type=int, default=400)
    parser.add_argument("--min-cull-ratio", type=float, default=0.75)
    parser.add_argument("--min-roundtrip-iou", type=float, default=0.75)
    parser.add_argument("--max-roundtrip-outside-ratio", type=float, default=0.22)
    parser.add_argument("--max-roundtrip-missing-ratio", type=float, default=0.08)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def mask_stats(channel: np.ndarray, threshold: int) -> dict[str, Any]:
    active = channel > threshold
    rows, cols = np.nonzero(active)
    stats: dict[str, Any] = {
        "threshold": threshold,
        "pixelCount": int(active.sum()),
        "coverage": float(active.mean()),
        "bbox": None,
    }

    if len(cols) > 0:
        stats["bbox"] = {
            "left": int(cols.min()),
            "top": int(rows.min()),
            "right": int(cols.max()),
            "bottom": int(rows.max()),
            "width": int(cols.max() - cols.min() + 1),
            "height": int(rows.max() - rows.min() + 1),
        }

    return stats


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_lip_atlas_shader_params(path: Path) -> tuple[float, float]:
    text = path.read_text(encoding="utf-8")
    threshold_match = re.search(
        r"Threshold\s*=\s*lipStyleAtlas(?:\s*\|\|\s*visionLipBoundary)?\s*\?\s*([0-9.]+)f",
        text,
    )
    feather_match = re.search(
        r"FeatherUvNormalized\s*=\s*lipStyleAtlas\s*\?\s*([0-9.]+)f",
        text,
    )
    require(threshold_match is not None, "Missing lipStyleAtlas threshold in overlay script.")
    require(feather_match is not None, "Missing lipStyleAtlas feather in overlay script.")
    return float(threshold_match.group(1)), float(feather_match.group(1))


def sample_unity_texture_byte(channel: np.ndarray, uv: np.ndarray) -> int:
    height, width = channel.shape
    u = float(np.clip(uv[0], 0.0, 1.0))
    v = float(np.clip(uv[1], 0.0, 1.0))
    x = int(round(u * (width - 1)))
    unity_y = int(round(v * (height - 1)))
    row = height - 1 - unity_y
    return int(channel[row, x])


def triangle_intersects_mask(channel: np.ndarray, threshold: int, triangle_uvs: np.ndarray) -> bool:
    uv_a = triangle_uvs[0]
    uv_b = triangle_uvs[1]
    uv_c = triangle_uvs[2]
    sample_points = (
        uv_a,
        uv_b,
        uv_c,
        (uv_a + uv_b + uv_c) / 3.0,
        (uv_a + uv_b) * 0.5,
        (uv_b + uv_c) * 0.5,
        (uv_c + uv_a) * 0.5,
    )
    return any(sample_unity_texture_byte(channel, point) > threshold for point in sample_points)


def mesh_culling_stats(capture_export_path: Path, channel: np.ndarray, threshold: float) -> dict[str, Any]:
    arface = json.loads(capture_export_path.read_text(encoding="utf-8-sig"))
    uvs = np.asarray(arface.get("uvs", []), dtype=np.float32)
    indices = np.asarray(arface.get("indices", []), dtype=np.int32)
    threshold_byte = int(np.clip(round(threshold * 255.0), 0, 255))
    source_triangles = 0
    accepted_triangles = 0
    skipped_invalid_triangles = 0

    require(uvs.ndim == 2 and uvs.shape[1] >= 2, "capture export is missing UVs.")
    require(indices.ndim == 1 and len(indices) >= 3, "capture export is missing indices.")

    for index in range(0, len(indices) - 2, 3):
        triangle = indices[index : index + 3]
        if int(triangle.min()) < 0 or int(triangle.max()) >= len(uvs):
            skipped_invalid_triangles += 1
            continue

        source_triangles += 1
        if triangle_intersects_mask(channel, threshold_byte, uvs[triangle, :2]):
            accepted_triangles += 1

    culled_triangles = source_triangles - accepted_triangles
    return {
        "thresholdByte": threshold_byte,
        "sourceTriangles": source_triangles,
        "acceptedTriangles": accepted_triangles,
        "culledTriangles": culled_triangles,
        "cullRatio": culled_triangles / float(max(source_triangles, 1)),
        "acceptedRatio": accepted_triangles / float(max(source_triangles, 1)),
        "skippedInvalidTriangles": skipped_invalid_triangles,
    }


def screen_mask_stats(mask: np.ndarray) -> dict[str, Any]:
    rows, cols = np.nonzero(mask)
    stats: dict[str, Any] = {
        "pixelCount": int(mask.sum()),
        "coverage": float(mask.mean()),
        "bbox": None,
    }

    if len(cols) > 0:
        stats["bbox"] = {
            "left": int(cols.min()),
            "top": int(rows.min()),
            "right": int(cols.max()),
            "bottom": int(rows.max()),
            "width": int(cols.max() - cols.min() + 1),
            "height": int(rows.max() - rows.min() + 1),
        }

    return stats


def project_atlas_to_screen(
    capture_export_path: Path,
    channel: np.ndarray,
    threshold: float,
    output_shape: tuple[int, int],
) -> tuple[np.ndarray, int]:
    arface = json.loads(capture_export_path.read_text(encoding="utf-8-sig"))
    screen_vertices = np.asarray(arface.get("screenVertices", []), dtype=np.float32)
    uvs = np.asarray(arface.get("uvs", []), dtype=np.float32)
    indices = np.asarray(arface.get("indices", []), dtype=np.int32)
    require(
        screen_vertices.ndim == 2 and screen_vertices.shape[1] >= 2,
        "capture export is missing screen vertices.",
    )
    require(uvs.ndim == 2 and uvs.shape[1] >= 2, "capture export is missing UVs.")
    require(len(screen_vertices) == len(uvs), "capture export screen/UV lengths differ.")
    require(indices.ndim == 1 and len(indices) >= 3, "capture export is missing indices.")

    height, width = output_shape
    atlas_height, atlas_width = channel.shape
    threshold_byte = int(np.clip(round(threshold * 255.0), 0, 255))
    projected = np.zeros((height, width), dtype=bool)
    touched_triangles = 0
    triangles = indices.reshape((-1, 3))
    epsilon = 1.0e-4

    for triangle in triangles:
        if int(triangle.min()) < 0 or int(triangle.max()) >= len(uvs):
            continue

        screen_points = screen_vertices[triangle, :2]
        uv_points = uvs[triangle, :2]
        left = max(int(np.floor(float(screen_points[:, 0].min()))), 0)
        right = min(int(np.ceil(float(screen_points[:, 0].max()))), width - 1)
        top = max(int(np.floor(float(screen_points[:, 1].min()))), 0)
        bottom = min(int(np.ceil(float(screen_points[:, 1].max()))), height - 1)
        if right < left or bottom < top:
            continue

        x1, y1 = screen_points[0]
        x2, y2 = screen_points[1]
        x3, y3 = screen_points[2]
        denominator = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)
        if abs(float(denominator)) < 1.0e-5:
            continue

        grid_x = np.arange(left, right + 1, dtype=np.float32) + 0.5
        grid_y = np.arange(top, bottom + 1, dtype=np.float32) + 0.5
        pixel_x, pixel_y = np.meshgrid(grid_x, grid_y)
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
        )
        if not inside_triangle.any():
            continue

        projected_u = (
            weight_a * uv_points[0, 0]
            + weight_b * uv_points[1, 0]
            + weight_c * uv_points[2, 0]
        )
        projected_v = (
            weight_a * uv_points[0, 1]
            + weight_b * uv_points[1, 1]
            + weight_c * uv_points[2, 1]
        )
        valid_uv = (
            (projected_u >= 0.0)
            & (projected_u <= 1.0)
            & (projected_v >= 0.0)
            & (projected_v <= 1.0)
        )
        active_domain = inside_triangle & valid_uv
        if not active_domain.any():
            continue

        atlas_x = np.clip(
            np.rint(projected_u * (atlas_width - 1)).astype(np.int32),
            0,
            atlas_width - 1,
        )
        unity_y = np.clip(
            np.rint(projected_v * (atlas_height - 1)).astype(np.int32),
            0,
            atlas_height - 1,
        )
        atlas_row = atlas_height - 1 - unity_y
        active = active_domain & (channel[atlas_row, atlas_x] > threshold_byte)
        if active.any():
            projected[top : bottom + 1, left : right + 1] |= active
            touched_triangles += 1

    return projected, touched_triangles


def roundtrip_stats(source_mask: np.ndarray, roundtrip_mask: np.ndarray, touched_triangles: int) -> dict[str, Any]:
    intersection = source_mask & roundtrip_mask
    union = source_mask | roundtrip_mask
    outside = roundtrip_mask & ~source_mask
    missing = source_mask & ~roundtrip_mask
    roundtrip_pixels = int(roundtrip_mask.sum())
    source_pixels = int(source_mask.sum())
    return {
        "source": screen_mask_stats(source_mask),
        "roundTrip": screen_mask_stats(roundtrip_mask),
        "intersectionPixelCount": int(intersection.sum()),
        "unionPixelCount": int(union.sum()),
        "iou": int(intersection.sum()) / float(max(int(union.sum()), 1)),
        "outsideSourcePixelCount": int(outside.sum()),
        "outsideSourceRatio": int(outside.sum()) / float(max(roundtrip_pixels, 1)),
        "missingSourcePixelCount": int(missing.sum()),
        "missingSourceRatio": int(missing.sum()) / float(max(source_pixels, 1)),
        "touchedTriangles": touched_triangles,
    }


def write_roundtrip_preview(
    frame_path: Path,
    source_mask: np.ndarray,
    roundtrip_mask: np.ndarray,
    preview_path: Path,
) -> None:
    frame = Image.open(frame_path).convert("RGBA")
    source_overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    source_overlay.putalpha(Image.fromarray((source_mask.astype(np.uint8) * 72), mode="L"))
    source_tint = Image.new("RGBA", frame.size, (58, 190, 112, 0))
    source_tint.putalpha(source_overlay.getchannel("A"))
    roundtrip_tint = Image.new("RGBA", frame.size, (217, 75, 116, 0))
    roundtrip_tint.putalpha(Image.fromarray((roundtrip_mask.astype(np.uint8) * 116), mode="L"))
    preview = Image.alpha_composite(Image.alpha_composite(frame, source_tint), roundtrip_tint)
    draw = ImageDraw.Draw(preview)
    draw.rectangle((24, 24, 520, 94), fill=(0, 0, 0, 150))
    draw.text((42, 40), "green=source marking / rose=atlas round-trip", fill=(255, 255, 255, 255))
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview.convert("RGB").save(preview_path)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    atlas_dir = resolve(repo, args.atlas_dir)
    summary_path = atlas_dir / "summary.json"
    old_mask_path = resolve(repo, args.old_mask)
    new_atlas_path = resolve(repo, args.new_atlas)
    overlay_script_path = resolve(repo, args.overlay_script)
    rn_bridge_path = resolve(repo, args.rn_bridge)
    rn_app_path = resolve(repo, args.rn_app)
    capture_export_path = resolve(repo, args.capture_export)
    capture_frame_path = resolve(repo, args.capture_frame)
    source_mask_path = (
        resolve(repo, args.source_screen_mask)
        if args.source_screen_mask is not None
        else atlas_dir / "lip_gold_mask_candidate.png"
    )
    roundtrip_mask_output = (
        resolve(repo, args.roundtrip_mask_output)
        if args.roundtrip_mask_output is not None
        else atlas_dir / "lip_atlas_roundtrip_mask.png"
    )
    roundtrip_preview_output = (
        resolve(repo, args.roundtrip_preview_output)
        if args.roundtrip_preview_output is not None
        else atlas_dir / "lip_atlas_roundtrip_overlay.png"
    )
    roundtrip_json_output = (
        resolve(repo, args.roundtrip_json_output)
        if args.roundtrip_json_output is not None
        else atlas_dir / "lip_atlas_roundtrip_metrics.json"
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    old_mask = np.asarray(Image.open(old_mask_path).convert("L"), dtype=np.uint8)
    new_atlas = np.asarray(Image.open(new_atlas_path).convert("RGBA"), dtype=np.uint8)
    new_full_channel = new_atlas[:, :, 0]
    source_screen_mask = (
        np.asarray(Image.open(source_mask_path).convert("L"), dtype=np.uint8) > 8
    )

    old_gt8 = mask_stats(old_mask, 8)
    new_gt8 = mask_stats(new_full_channel, 8)
    new_gt26 = mask_stats(new_full_channel, 26)
    old_pixels = int(old_gt8["pixelCount"])
    new_pixels = int(new_gt8["pixelCount"])
    ratio = old_pixels / float(max(new_pixels, 1))
    threshold, feather = read_lip_atlas_shader_params(overlay_script_path)
    overlay_text = overlay_script_path.read_text(encoding="utf-8")
    rn_bridge_text = rn_bridge_path.read_text(encoding="utf-8")
    rn_app_text = rn_app_path.read_text(encoding="utf-8")
    uv_stats = summary.get("uvBackProjectionStats") or {}
    new_bbox = new_gt8["bbox"] or {}
    old_bbox = old_gt8["bbox"] or {}
    culling = mesh_culling_stats(capture_export_path, new_full_channel, threshold)
    roundtrip_mask, touched_triangles = project_atlas_to_screen(
        capture_export_path,
        new_full_channel,
        threshold,
        source_screen_mask.shape,
    )
    roundtrip = roundtrip_stats(source_screen_mask, roundtrip_mask, touched_triangles)
    roundtrip_mask_output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((roundtrip_mask.astype(np.uint8) * 255), mode="L").save(
        roundtrip_mask_output
    )
    write_roundtrip_preview(
        capture_frame_path,
        source_screen_mask,
        roundtrip_mask,
        roundtrip_preview_output,
    )
    roundtrip_json_output.write_text(
        json.dumps(roundtrip, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    require(summary.get("projectionUsed") is True, "summary projectionUsed must be true.")
    require(
        summary.get("runtimeMaskSource") == "arface_uv_back_projection",
        "runtimeMaskSource must be arface_uv_back_projection.",
    )
    require(summary.get("trueUvBackProjection") is True, "trueUvBackProjection must be true.")
    require(
        summary.get("greenEvidenceEligible") is False,
        "greenEvidenceEligible must stay false until runtime visual evidence exists.",
    )
    require(
        int(uv_stats.get("hitSampleCount", 0)) >= args.min_hit_samples,
        f"hitSampleCount below guard: {uv_stats.get('hitSampleCount')}",
    )
    require(
        new_pixels <= args.max_new_gt8_pixels,
        f"new projected atlas is too broad: {new_pixels} > {args.max_new_gt8_pixels}",
    )
    require(
        ratio >= args.min_old_to_new_gt8_ratio,
        f"old/new pixel ratio too low: {ratio:0.3f}",
    )
    require(
        int(new_bbox.get("height", 9999)) <= args.max_new_bbox_height,
        f"new projected bbox too tall: {new_bbox}",
    )
    require(
        int(new_bbox.get("bottom", 9999)) <= int(old_bbox.get("bottom", 0)) - 20,
        f"new projected bbox bottom did not shrink enough: old={old_bbox} new={new_bbox}",
    )
    require(
        threshold <= args.max_threshold,
        f"lip atlas threshold too high for projected atlas: {threshold}",
    )
    require(feather <= args.max_feather, f"lip atlas feather too high: {feather}")
    require(
        "lip_style_atlas_v1_uv_back_projection" in overlay_text,
        "Unity maskSource metadata must identify the UV back-projected lip atlas.",
    )
    require(
        "lip_style_atlas_v1_scaffold" not in overlay_text,
        "Unity maskSource metadata still references the old scaffold name.",
    )
    require(
        "MaskTextureActivePixelCountGt8" in overlay_text
        and "maskTextureGt8Pixels" in overlay_text,
        "Unity overlay result is missing runtime mask texture diagnostics.",
    )
    require(
        "lip_atlas_threshold_sample" in overlay_text
        and "TriangleIntersectsMask" in overlay_text,
        "Unity overlay is missing lip atlas mesh culling.",
    )
    require(
        "sourceTriangles" in rn_bridge_text
        and "culledTriangles" in rn_bridge_text
        and "meshCullingMode" in rn_bridge_text,
        "RNBridge recipe event is missing lip atlas mesh culling diagnostics.",
    )
    require(
        "cull=${String" in rn_app_text and "meshCullingMode" in rn_app_text,
        "RN HUD summary is missing lip atlas mesh culling diagnostics.",
    )
    require(
        int(culling["acceptedTriangles"]) <= args.max_accepted_triangles,
        f"lip atlas culling leaves too many triangles: {culling}",
    )
    require(
        float(culling["cullRatio"]) >= args.min_cull_ratio,
        f"lip atlas culling ratio too low: {culling}",
    )
    require(
        float(roundtrip["iou"]) >= args.min_roundtrip_iou,
        f"lip atlas screen round-trip IoU too low: {roundtrip}",
    )
    require(
        float(roundtrip["outsideSourceRatio"]) <= args.max_roundtrip_outside_ratio,
        f"lip atlas screen round-trip outside-source ratio too high: {roundtrip}",
    )
    require(
        float(roundtrip["missingSourceRatio"]) <= args.max_roundtrip_missing_ratio,
        f"lip atlas screen round-trip missing-source ratio too high: {roundtrip}",
    )

    print(
        json.dumps(
            {
                "status": "pass",
                "projectionUsed": summary.get("projectionUsed"),
                "runtimeMaskSource": summary.get("runtimeMaskSource"),
                "oldGt8": old_gt8,
                "newGt8": new_gt8,
                "newGt26": new_gt26,
                "oldToNewGt8Ratio": ratio,
                "lipAtlasThreshold": threshold,
                "lipAtlasFeather": feather,
                "uvBackProjectionStats": uv_stats,
                "meshCulling": culling,
                "screenRoundTrip": roundtrip,
                "roundtripMaskOutput": str(roundtrip_mask_output.relative_to(repo)),
                "roundtripPreviewOutput": str(roundtrip_preview_output.relative_to(repo)),
                "roundtripJsonOutput": str(roundtrip_json_output.relative_to(repo)),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
