#!/usr/bin/env python3
"""Compute buildless color/gradient confidence for E7 lip M1.

This tool does not create or expand a lip boundary. It only checks whether an
existing lip reference mask has useful color/edge evidence and records warnings
for low contrast, shadow, or specular highlights.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


MIN_SAMPLE_PIXELS = 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute E7 lip color/gradient confidence from an existing mask."
    )
    parser.add_argument("--frame", type=Path, required=True)
    parser.add_argument("--lip-mask", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--face-parsing-lip", type=Path, default=None)
    parser.add_argument("--face-parsing-skin", type=Path, default=None)
    parser.add_argument("--vision-contour", type=Path, default=None)
    parser.add_argument("--capture-pair-id", default=None)
    parser.add_argument("--low-contrast-threshold", type=float, default=18.0)
    parser.add_argument("--edge-gradient-threshold", type=float, default=0.025)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def binary_image(path: Path, size: tuple[int, int]) -> Image.Image:
    image = Image.open(path).convert("L")
    if image.size != size:
        raise ValueError(f"mask_size_mismatch:{path}:{image.size}!={size}")
    return image.point(lambda value: 255 if value > 0 else 0)


def mask_array(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L")) > 0


def count(mask: np.ndarray) -> int:
    return int(np.count_nonzero(mask))


def choose_eroded(mask: Image.Image) -> Image.Image:
    for size in (15, 11, 7, 3):
        eroded = mask.filter(ImageFilter.MinFilter(size))
        if count(mask_array(eroded)) >= MIN_SAMPLE_PIXELS:
            return eroded
    return mask


def make_bands(
    lip_mask: Image.Image,
    skin_mask: Image.Image | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    inner = mask_array(choose_eroded(lip_mask))
    dilated_near = lip_mask.filter(ImageFilter.MaxFilter(11))
    eroded_near = lip_mask.filter(ImageFilter.MinFilter(11))
    boundary = mask_array(ImageChops.subtract(dilated_near, eroded_near))

    outside_ring = mask_array(
        ImageChops.subtract(
            lip_mask.filter(ImageFilter.MaxFilter(45)),
            lip_mask.filter(ImageFilter.MaxFilter(13)),
        )
    )
    if skin_mask is not None:
        skin = mask_array(skin_mask)
        outside_skin = outside_ring & skin
        if count(outside_skin) < MIN_SAMPLE_PIXELS:
            outside_skin = outside_ring & ~mask_array(lip_mask)
    else:
        outside_skin = outside_ring & ~mask_array(lip_mask)

    if count(outside_skin) < MIN_SAMPLE_PIXELS:
        outside_skin = mask_array(lip_mask.filter(ImageFilter.MaxFilter(65))) & ~mask_array(lip_mask)
    return inner, boundary, outside_skin


def rgb_to_ycbcr(rgb: np.ndarray) -> np.ndarray:
    matrix = np.array(
        [
            [0.299, 0.587, 0.114],
            [-0.168736, -0.331264, 0.5],
            [0.5, -0.418688, -0.081312],
        ],
        dtype=np.float32,
    )
    shifted = rgb.astype(np.float32)
    ycbcr = shifted @ matrix.T
    ycbcr[:, 1:] += 128.0
    return ycbcr


def median_color(rgb: np.ndarray, mask: np.ndarray) -> list[float]:
    pixels = rgb[mask]
    if len(pixels) == 0:
        return [0.0, 0.0, 0.0]
    return [round(float(value), 3) for value in np.median(pixels, axis=0)]


def gradient_mean(rgb: np.ndarray, mask: np.ndarray) -> float:
    luma = (rgb[:, :, 0] * 0.299) + (rgb[:, :, 1] * 0.587) + (rgb[:, :, 2] * 0.114)
    grad_y, grad_x = np.gradient(luma.astype(np.float32))
    gradient = np.sqrt((grad_x * grad_x) + (grad_y * grad_y)) / 255.0
    if count(mask) == 0:
        return 0.0
    return round(float(np.mean(gradient[mask])), 6)


def highlight_fraction(rgb: np.ndarray, mask: np.ndarray) -> float:
    if count(mask) == 0:
        return 0.0
    pixels = rgb[mask].astype(np.float32)
    max_channel = pixels.max(axis=1)
    min_channel = pixels.min(axis=1)
    saturation = (max_channel - min_channel) / np.maximum(max_channel, 1.0)
    highlights = (max_channel >= 235.0) & (saturation <= 0.22)
    return round(float(np.mean(highlights)), 6)


def dark_fraction(rgb: np.ndarray, mask: np.ndarray) -> float:
    if count(mask) == 0:
        return 0.0
    pixels = rgb[mask].astype(np.float32)
    luma = (pixels[:, 0] * 0.299) + (pixels[:, 1] * 0.587) + (pixels[:, 2] * 0.114)
    return round(float(np.mean(luma < 70.0)), 6)


def draw_vision_contours(
    draw: ImageDraw.ImageDraw,
    vision: dict[str, Any] | None,
    color: tuple[int, int, int],
) -> None:
    if not vision:
        return
    contours = vision.get("contours", {})
    for contour_id in ("outerLips", "innerLips"):
        points = []
        for point in contours.get(contour_id, {}).get("imagePoints", []):
            if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(
                point.get("y"), (int, float)
            ):
                points.append((float(point["x"]), float(point["y"])))
        if len(points) >= 2:
            draw.line(points + [points[0]], fill=color, width=4, joint="curve")


def write_overlay(
    frame: Image.Image,
    inner: np.ndarray,
    boundary: np.ndarray,
    outside_skin: np.ndarray,
    vision: dict[str, Any] | None,
    output_path: Path,
) -> None:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    base[outside_skin] = (base[outside_skin] * 0.60) + (np.array([0, 190, 255]) * 0.40)
    base[inner] = (base[inner] * 0.55) + (np.array([255, 43, 118]) * 0.45)
    base[boundary] = (base[boundary] * 0.35) + (np.array([255, 215, 0]) * 0.65)
    overlay = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    draw_vision_contours(ImageDraw.Draw(overlay), vision, (80, 255, 120))
    overlay.save(output_path)


def unavailable(reason: str, args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-lip-color-gradient-confidence-v0",
        "createdAtUtc": utc_now(),
        "status": "unavailable",
        "unavailableReason": reason,
        "capturePairId": args.capture_pair_id,
        "source": "pil_numpy_boundary_band_v0",
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
        "recommendedUse": "confidence_only_never_boundary_source",
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
    }


def compute(args: argparse.Namespace) -> dict[str, Any]:
    frame = Image.open(args.frame).convert("RGB")
    lip_mask = binary_image(args.lip_mask, frame.size)
    skin_mask = binary_image(args.face_parsing_skin, frame.size) if args.face_parsing_skin else None
    face_lip_mask = binary_image(args.face_parsing_lip, frame.size) if args.face_parsing_lip else None
    inner, boundary, outside_skin = make_bands(lip_mask, skin_mask)

    rgb = np.asarray(frame, dtype=np.float32)
    lip_pixels = count(inner)
    skin_pixels = count(outside_skin)
    boundary_pixels = count(boundary)
    if lip_pixels < MIN_SAMPLE_PIXELS or skin_pixels < MIN_SAMPLE_PIXELS:
        status = "partial"
    else:
        status = "computed"

    lip_median = median_color(rgb, inner)
    skin_median = median_color(rgb, outside_skin)
    lip_rgb = np.asarray(lip_median, dtype=np.float32)
    skin_rgb = np.asarray(skin_median, dtype=np.float32)
    lip_skin_delta = round(float(np.linalg.norm(lip_rgb - skin_rgb)), 3)

    ycbcr = rgb_to_ycbcr(np.vstack([lip_rgb, skin_rgb]))
    luma_delta = round(float(abs(ycbcr[0, 0] - ycbcr[1, 0])), 3)
    chroma_delta = round(float(np.linalg.norm(ycbcr[0, 1:] - ycbcr[1, 1:])), 3)
    edge_gradient = gradient_mean(rgb, boundary)
    boundary_highlight_fraction = highlight_fraction(rgb, boundary | inner)
    skin_dark_fraction = dark_fraction(rgb, outside_skin)

    low_contrast = (
        lip_skin_delta < args.low_contrast_threshold
        or (chroma_delta < 10.0 and edge_gradient < args.edge_gradient_threshold)
    )
    shadow = skin_dark_fraction > 0.30
    specular = boundary_highlight_fraction > 0.015
    warnings = []
    if low_contrast:
        warnings.append("lowContrastWarning")
    if shadow:
        warnings.append("shadowWarning")
    if specular:
        warnings.append("specularWarning")

    overlay_path = args.output_dir / "color_gradient_overlay.png"
    vision = load_json(args.vision_contour)
    write_overlay(frame, inner, boundary, outside_skin, vision, overlay_path)

    parsing_overlap = None
    if face_lip_mask is not None and count(mask_array(face_lip_mask)) > 0:
        parsing = mask_array(face_lip_mask)
        reference = mask_array(lip_mask)
        intersection = count(parsing & reference)
        union = count(parsing | reference)
        parsing_overlap = round(float(intersection / union), 6) if union else None

    confidence_score = min(
        1.0,
        (min(lip_skin_delta / 45.0, 1.0) * 0.40)
        + (min(edge_gradient / 0.08, 1.0) * 0.40)
        + (min(chroma_delta / 24.0, 1.0) * 0.20),
    )
    if low_contrast:
        confidence_score *= 0.75
    if shadow:
        confidence_score *= 0.85
    if specular:
        confidence_score *= 0.90

    return {
        "schemaVersion": "e7-lip-color-gradient-confidence-v0",
        "createdAtUtc": utc_now(),
        "status": status,
        "source": "pil_numpy_boundary_band_v0",
        "capturePairId": args.capture_pair_id,
        "sourceFramePath": str(args.frame),
        "sourceFrameSha256": sha256_file(args.frame),
        "lipMaskPath": str(args.lip_mask),
        "lipMaskSha256": sha256_file(args.lip_mask),
        "faceParsingLipMaskPath": str(args.face_parsing_lip) if args.face_parsing_lip else None,
        "faceParsingSkinMaskPath": str(args.face_parsing_skin) if args.face_parsing_skin else None,
        "visionContourPath": str(args.vision_contour) if args.vision_contour else None,
        "overlayPath": "color_gradient_overlay.png",
        "lipInnerPixels": lip_pixels,
        "boundaryPixels": boundary_pixels,
        "outsideSkinPixels": skin_pixels,
        "lipMedianRgb": lip_median,
        "skinMedianRgb": skin_median,
        "lipSkinDelta": lip_skin_delta,
        "lumaDelta": luma_delta,
        "chromaDelta": chroma_delta,
        "edgeGradientMean": edge_gradient,
        "boundaryHighlightFraction": boundary_highlight_fraction,
        "skinDarkFraction": skin_dark_fraction,
        "faceParsingLipReferenceIoU": parsing_overlap,
        "confidenceScore": round(float(confidence_score), 6),
        "lowContrastWarning": low_contrast,
        "shadowWarning": shadow,
        "specularWarning": specular,
        "warnings": warnings,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
        "recommendedUse": "confidence_only_never_boundary_source",
        "limits": {
            "doesNotCreateBoundary": True,
            "doesNotExpandBoundary": True,
            "doesNotClaimM1Ready": True,
            "doesNotClaimE73Green": True,
        },
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
    }


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_json = args.output_dir / "color_gradient_confidence.json"
    try:
        result = compute(args)
    except Exception as exc:  # Keep M1 honest with a machine-readable artifact.
        result = unavailable(f"{type(exc).__name__}:{exc}", args)
    write_json(output_json, result)
    print(json.dumps({"colorGradientConfidence": str(output_json), "status": result["status"]}, indent=2))
    return 0 if result["status"] in {"computed", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
