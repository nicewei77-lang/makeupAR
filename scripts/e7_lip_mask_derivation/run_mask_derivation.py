#!/usr/bin/env python3
"""Run E7 Section 14B buildless lip mask derivation.

This is local-only, lip-only evidence generation. It reads the user-approved
gold raw manifest, writes derived masks into a timestamped experiment folder,
and does not run device builds, live face parsing, Core ML, upload, or runtime
candidate installation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SCHEMA_VERSION = "e7-lip-mask-derivation-v0"
POLICY_SCHEMA_VERSION = "e7-lip-mask-derivation-selected-policy-v0"
DEFAULT_MANIFEST = Path("evidence/references/e7-user-gold-raw-20260626/manifest.json")
DEFAULT_OUTPUT_ROOT = Path("evidence/e7-lip-mask-derivation")
DEFAULT_APPLE_VISION_CONTOUR = Path(
    "evidence/e7-lip-m1-packages/m1-lip-apple-vision-20260625T132216Z/apple_vision_lip_contour.json"
)
DEFAULT_FACE_PARSING_DIR = Path("evidence/e7-lip-m1-packages/m1-lip-face-parsing-20260625T2255Z")
DEFAULT_COLOR_GRADIENT_CONFIDENCE = Path(
    "evidence/e7-lip-m1-packages/m1-lip-color-gradient-20260625T000000Z/color_gradient_confidence.json"
)
DEFAULT_ARFACE_EXPORT = Path(
    "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/arface_export.json"
)
REJECTED_LINEAGE = "manual_polygon_codex_visual_reference_v0"
MIN_CANDIDATES = (
    "gold_exact_binary",
    "gold_alpha_soft",
    "gold_clean_morphology",
    "gold_conservative_erode",
    "gold_coverage_dilate",
)
CANDIDATE_FAMILIES = MIN_CANDIDATES + (
    "face_parsing_raw",
    "face_parsing_clean",
    "vision_contour_fill",
    "vision_expanded",
    "arface_lip_ring_envelope",
    "parsing_clamped_by_vision",
    "parsing_clamped_by_arface",
    "hybrid_conservative",
    "hybrid_balanced",
    "hybrid_coverage",
    "lip_smooth_mask_v1_baseline",
)


@dataclass(frozen=True)
class GoldSource:
    source_id: str
    path: Path
    role: str
    width: int
    height: int
    mode: str
    sha256: str
    context_path: Path | None


@dataclass
class OptionalSignals:
    reports: list[dict[str, Any]]
    skipped_reasons: dict[str, str]
    face_parsing_raw: np.ndarray | None = None
    face_parsing_clean: np.ndarray | None = None
    face_parsing_inner_mouth: np.ndarray | None = None
    vision_contour_fill: np.ndarray | None = None
    vision_expanded: np.ndarray | None = None
    color_gradient_confidence: dict[str, Any] | None = None
    arface_coordinate_metadata: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E7 14B gold mask derivation.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--apple-vision-contour", type=Path, default=DEFAULT_APPLE_VISION_CONTOUR)
    parser.add_argument("--face-parsing-dir", type=Path, default=DEFAULT_FACE_PARSING_DIR)
    parser.add_argument("--color-gradient-confidence", type=Path, default=DEFAULT_COLOR_GRADIENT_CONFIDENCE)
    parser.add_argument("--arface-export", type=Path, default=DEFAULT_ARFACE_EXPORT)
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-").lower()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_dirs(output_dir: Path) -> None:
    for child in (
        "gold_extracted_masks",
        "candidates",
        "overlays",
    ):
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def border_rgb(rgb: np.ndarray, pad: int = 8) -> np.ndarray:
    top = rgb[:pad, :, :]
    bottom = rgb[-pad:, :, :]
    left = rgb[:, :pad, :]
    right = rgb[:, -pad:, :]
    border = np.concatenate(
        [top.reshape(-1, 3), bottom.reshape(-1, 3), left.reshape(-1, 3), right.reshape(-1, 3)],
        axis=0,
    )
    return np.median(border, axis=0)


def extract_mask_and_alpha(image: Image.Image) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    rgba = image.convert("RGBA")
    arr = np.asarray(rgba).astype(np.int16)
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    info: dict[str, Any] = {
        "method": "alpha_or_border_color_distance",
        "alphaMin": int(alpha.min()),
        "alphaMax": int(alpha.max()),
    }
    if int(alpha.min()) < 250:
        soft = np.clip(alpha, 0, 255).astype(np.uint8)
        mask = soft > 16
        info["selectedSignal"] = "alpha"
        return mask, soft, info

    bg = border_rgb(rgb.astype(np.uint8))
    dist = np.sqrt(np.sum((rgb.astype(np.float32) - bg.astype(np.float32)) ** 2, axis=2))
    soft = np.clip((dist - 8.0) * 5.0, 0, 255).astype(np.uint8)
    mask = dist > 18.0
    info["selectedSignal"] = "border_color_distance"
    info["backgroundRgbMedian"] = [float(x) for x in bg]
    info["distanceThreshold"] = 18.0
    return mask, soft, info


def mask_to_image(mask: np.ndarray) -> Image.Image:
    return Image.fromarray((mask.astype(np.uint8) * 255), mode="L")


def load_binary_mask(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("L")) > 127


def mask_iou(a: np.ndarray, b: np.ndarray) -> float | None:
    if a.shape != b.shape or not np.any(b):
        return None
    union = int(np.count_nonzero(a | b))
    if union == 0:
        return None
    return int(np.count_nonzero(a & b)) / union


def contains_rejected_lineage(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_rejected_lineage(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_rejected_lineage(v) for v in value)
    if isinstance(value, str):
        return REJECTED_LINEAGE in value
    return False


def soft_to_mask(soft: np.ndarray) -> np.ndarray:
    return soft > 127


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = radius * 2 + 1
    image = mask_to_image(mask)
    return np.asarray(image.filter(ImageFilter.MaxFilter(size))) > 0


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = radius * 2 + 1
    image = mask_to_image(mask)
    return np.asarray(image.filter(ImageFilter.MinFilter(size))) > 0


def close_mask(mask: np.ndarray, radius: int = 2) -> np.ndarray:
    return erode(dilate(mask, radius), radius)


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        component: list[tuple[int, int]] = []
        queue: deque[tuple[int, int]] = deque([(y0, x0)])
        seen[y0, x0] = True
        while queue:
            y, x = queue.popleft()
            component.append((y, x))
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    if ny == y and nx == x:
                        continue
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        components.append(component)
    components.sort(key=len, reverse=True)
    return components


def keep_main_components(mask: np.ndarray, max_components: int = 1, min_pixels: int = 64) -> np.ndarray:
    out = np.zeros_like(mask, dtype=bool)
    for component in connected_components(mask)[:max_components]:
        if len(component) < min_pixels:
            continue
        ys, xs = zip(*component)
        out[np.asarray(ys), np.asarray(xs)] = True
    return out


def keep_plausible_components(mask: np.ndarray, max_components: int = 2) -> np.ndarray:
    return keep_main_components(mask, max_components=max_components, min_pixels=64)


def bbox(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {"available": False}
    return {
        "available": True,
        "minX": int(xs.min()),
        "minY": int(ys.min()),
        "maxX": int(xs.max()),
        "maxY": int(ys.max()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }


def perimeter_pixels(mask: np.ndarray) -> int:
    if not np.any(mask):
        return 0
    eroded = erode(mask, 1)
    return int(np.count_nonzero(mask & ~eroded))


def component_count(mask: np.ndarray) -> int:
    return len([component for component in connected_components(mask) if len(component) >= 64])


def approximate_hole_count(mask: np.ndarray) -> int:
    box = bbox(mask)
    if not box["available"]:
        return 0
    crop = mask[box["minY"] : box["maxY"] + 1, box["minX"] : box["maxX"] + 1]
    inv = ~crop
    components = connected_components(inv)
    holes = 0
    height, width = crop.shape
    for component in components:
        touches_edge = any(y in (0, height - 1) or x in (0, width - 1) for y, x in component)
        if not touches_edge and len(component) >= 16:
            holes += 1
    return holes


def overlay_mask(context: Image.Image, mask: np.ndarray, label: str) -> Image.Image:
    base = ImageOps.exif_transpose(context).convert("RGBA")
    if base.size != (mask.shape[1], mask.shape[0]):
        base = base.resize((mask.shape[1], mask.shape[0]), Image.Resampling.BILINEAR)
    tint = Image.new("RGBA", base.size, (255, 42, 96, 0))
    alpha = Image.fromarray((mask.astype(np.uint8) * 150), mode="L")
    tint.putalpha(alpha)
    out = Image.alpha_composite(base, tint)
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, min(out.width - 1, 620), 34), fill=(0, 0, 0, 145))
    draw.text((10, 8), label, fill=(255, 255, 255, 255))
    return out.convert("RGB")


def rasterize_vision_contour(path: Path) -> tuple[np.ndarray | None, dict[str, Any]]:
    report: dict[str, Any] = {
        "signal": "appleVision",
        "path": str(path),
        "exists": path.exists(),
        "status": "missing",
    }
    if not path.exists():
        return None, report
    data = load_json(path)
    report["sha256"] = sha256_file(path)
    report["containsRejectedLineage"] = contains_rejected_lineage(data)
    if report["containsRejectedLineage"]:
        report["status"] = "rejected_lineage_detected"
        return None, report
    image_info = data.get("image", {})
    width = int(image_info.get("width", 0) or 0)
    height = int(image_info.get("height", 0) or 0)
    outer = data.get("contours", {}).get("outerLips", {})
    inner = data.get("contours", {}).get("innerLips", {})
    outer_points = [(float(p["x"]), float(p["y"])) for p in outer.get("imagePoints", []) if "x" in p and "y" in p]
    inner_points = [(float(p["x"]), float(p["y"])) for p in inner.get("imagePoints", []) if "x" in p and "y" in p]
    report.update(
        {
            "width": width,
            "height": height,
            "confidence": data.get("confidence"),
            "outerLipPointCount": len(outer_points),
            "innerLipPointCount": len(inner_points),
            "sourceUse": "silver_auxiliary_only",
        }
    )
    if width <= 0 or height <= 0 or len(outer_points) < 3:
        report["status"] = "insufficient_contour_points"
        return None, report
    image = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(image)
    draw.polygon(outer_points, fill=255)
    if len(inner_points) >= 3:
        draw.polygon(inner_points, fill=0)
    mask = np.asarray(image) > 0
    report["status"] = "available" if np.any(mask) else "empty_after_rasterize"
    report["positivePixels"] = int(np.count_nonzero(mask))
    report["bbox"] = bbox(mask)
    return mask, report


def load_optional_signals(args: argparse.Namespace) -> OptionalSignals:
    reports: list[dict[str, Any]] = []
    skipped = {
        "arface_lip_ring_envelope": "arface_export_available_for_coordinate_metadata_only_not_verified_for_mask_generation",
        "parsing_clamped_by_arface": "arface_coordinate_pairing_not_verified",
        "lip_smooth_mask_v1_baseline": "existing_broad_baseline_mask_not_available_as_standalone_same_dimension_artifact",
    }

    vision_mask, vision_report = rasterize_vision_contour(args.apple_vision_contour)
    reports.append(vision_report)
    if vision_mask is None:
        skipped["vision_contour_fill"] = vision_report["status"]
        skipped["vision_expanded"] = vision_report["status"]
        skipped["parsing_clamped_by_vision"] = "apple_vision_contour_unavailable"

    face_report: dict[str, Any] = {
        "signal": "faceParsing",
        "dir": str(args.face_parsing_dir),
        "exists": args.face_parsing_dir.exists(),
        "status": "missing",
        "sourceUse": "silver_auxiliary_only",
    }
    face_raw = face_clean = face_inner = None
    if args.face_parsing_dir.exists():
        lip_path = args.face_parsing_dir / "face_parsing_lip_mask.png"
        upper_path = args.face_parsing_dir / "face_parsing_upper_lip_mask.png"
        lower_path = args.face_parsing_dir / "face_parsing_lower_lip_mask.png"
        inner_path = args.face_parsing_dir / "face_parsing_inner_mouth_mask.png"
        confidence_path = args.face_parsing_dir / "face_parsing_confidence.json"
        required = [lip_path, upper_path, lower_path, inner_path, confidence_path]
        missing = [str(path) for path in required if not path.exists()]
        face_report["missing"] = missing
        if missing:
            face_report["status"] = "required_artifact_missing"
        else:
            confidence = load_json(confidence_path)
            face_report["confidenceSha256"] = sha256_file(confidence_path)
            face_report["containsRejectedLineage"] = contains_rejected_lineage(confidence)
            if face_report["containsRejectedLineage"]:
                face_report["status"] = "rejected_lineage_detected"
            else:
                face_raw = load_binary_mask(lip_path)
                upper = load_binary_mask(upper_path)
                lower = load_binary_mask(lower_path)
                face_inner = load_binary_mask(inner_path)
                face_clean = keep_plausible_components(close_mask((face_raw | upper | lower) & ~face_inner, 1), 2)
                face_report.update(
                    {
                        "status": confidence.get("status", "available"),
                        "meanLipConfidence": confidence.get("meanLipConfidence"),
                        "pixelCounts": confidence.get("pixelCounts", {}),
                        "width": int(face_raw.shape[1]),
                        "height": int(face_raw.shape[0]),
                        "rawPositivePixels": int(np.count_nonzero(face_raw)),
                        "cleanPositivePixels": int(np.count_nonzero(face_clean)),
                        "innerMouthPositivePixels": int(np.count_nonzero(face_inner)),
                    }
                )
    reports.append(face_report)
    if face_raw is None or face_clean is None:
        skipped["face_parsing_raw"] = face_report["status"]
        skipped["face_parsing_clean"] = face_report["status"]
        skipped["parsing_clamped_by_vision"] = "face_parsing_unavailable"
        skipped["hybrid_conservative"] = "face_parsing_unavailable"
        skipped["hybrid_balanced"] = "face_parsing_unavailable"
        skipped["hybrid_coverage"] = "face_parsing_unavailable"

    color_report: dict[str, Any] = {
        "signal": "colorGradient",
        "path": str(args.color_gradient_confidence),
        "exists": args.color_gradient_confidence.exists(),
        "status": "missing",
        "sourceUse": "confidence_gate_only_not_boundary_source",
    }
    color_confidence = None
    if args.color_gradient_confidence.exists():
        color_confidence = load_json(args.color_gradient_confidence)
        color_report.update(
            {
                "status": color_confidence.get("status"),
                "sha256": sha256_file(args.color_gradient_confidence),
                "containsRejectedLineage": contains_rejected_lineage(color_confidence),
                "lowContrastWarning": color_confidence.get("lowContrastWarning"),
                "shadowWarning": color_confidence.get("shadowWarning"),
                "specularWarning": color_confidence.get("specularWarning"),
            }
        )
    reports.append(color_report)

    arface_report: dict[str, Any] = {
        "signal": "arfaceCoordinateMetadata",
        "path": str(args.arface_export),
        "exists": args.arface_export.exists(),
        "status": "metadata_only_not_coordinate_pair_validated",
        "sourceUse": "coordinate_feasibility_metadata_only",
    }
    arface_metadata = None
    if args.arface_export.exists():
        arface_data = load_json(args.arface_export)
        arface_metadata = {
            "sha256": sha256_file(args.arface_export),
            "containsRejectedLineage": contains_rejected_lineage(arface_data),
            "keys": sorted(arface_data.keys()),
        }
        arface_report.update(arface_metadata)
    reports.append(arface_report)

    if face_clean is not None and vision_mask is not None:
        skipped.pop("parsing_clamped_by_vision", None)
        skipped.pop("hybrid_conservative", None)
        skipped.pop("hybrid_balanced", None)
        skipped.pop("hybrid_coverage", None)

    return OptionalSignals(
        reports=reports,
        skipped_reasons=skipped,
        face_parsing_raw=face_raw,
        face_parsing_clean=face_clean,
        face_parsing_inner_mouth=face_inner,
        vision_contour_fill=vision_mask,
        vision_expanded=dilate(vision_mask, 3) if vision_mask is not None else None,
        color_gradient_confidence=color_confidence,
        arface_coordinate_metadata=arface_metadata,
    )


def source_context_path(manifest_dir: Path, file_path: str, files: list[dict[str, Any]]) -> Path | None:
    if file_path.startswith("user-gold-lip-mask-gray"):
        return manifest_dir / "user-gold-lip-render-20260625-163240.png"
    if file_path == "A_1.png":
        return manifest_dir / "A_0.png"
    for entry in files:
        if entry.get("role") in {"combined_face_region_gold_reference_visual", "full_face_region_gold_reference_visual"}:
            path = manifest_dir / entry["path"]
            if path.exists():
                return path
    return None


def load_gold_sources(manifest_path: Path, manifest: dict[str, Any]) -> tuple[list[GoldSource], list[dict[str, Any]], list[str]]:
    manifest_dir = manifest_path.parent
    sources: list[GoldSource] = []
    file_reports: list[dict[str, Any]] = []
    blockers: list[str] = []
    files = manifest.get("files", [])
    if not isinstance(files, list) or not files:
        return sources, file_reports, ["manifest_files_missing_or_invalid"]

    for entry in files:
        rel_path = entry.get("path")
        role = entry.get("role", "")
        if not rel_path:
            blockers.append("manifest_file_entry_missing_path")
            continue
        path = manifest_dir / rel_path
        report: dict[str, Any] = {
            "path": rel_path,
            "role": role,
            "exists": path.exists(),
            "expectedSha256": entry.get("sha256"),
            "extractableLipMask": role == "lip_mask_only_gold_reference",
        }
        if not path.exists():
            blockers.append(f"missing_gold_file:{rel_path}")
            file_reports.append(report)
            continue
        actual_sha = sha256_file(path)
        report["actualSha256"] = actual_sha
        report["sha256Matches"] = actual_sha == entry.get("sha256")
        if not report["sha256Matches"]:
            blockers.append(f"hash_mismatch:{rel_path}")
        with Image.open(path) as image:
            report["actualMode"] = image.mode
            report["actualWidth"] = image.width
            report["actualHeight"] = image.height
            report["dimensionMatches"] = image.width == entry.get("width") and image.height == entry.get("height")
            report["modeMatchesManifest"] = image.mode == entry.get("mode")
        file_reports.append(report)
        if role == "lip_mask_only_gold_reference" and report["sha256Matches"] and report["dimensionMatches"]:
            sources.append(
                GoldSource(
                    source_id=slug(Path(rel_path).stem),
                    path=path,
                    role=role,
                    width=int(entry["width"]),
                    height=int(entry["height"]),
                    mode=str(entry["mode"]),
                    sha256=actual_sha,
                    context_path=source_context_path(manifest_dir, rel_path, files),
                )
            )
    return sources, file_reports, blockers


def shape_compatible(mask: np.ndarray | None, shape: tuple[int, int]) -> bool:
    return mask is not None and mask.shape == shape


def candidate_masks(
    binary: np.ndarray,
    soft: np.ndarray,
    optional: OptionalSignals,
) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    clean = keep_main_components(close_mask(binary, 2), max_components=1)
    masks = {
        "gold_exact_binary": binary,
        "gold_alpha_soft": soft_to_mask(soft),
        "gold_clean_morphology": clean,
        "gold_conservative_erode": keep_main_components(erode(clean, 2), max_components=1),
        "gold_coverage_dilate": keep_main_components(dilate(clean, 3), max_components=1),
    }
    skips: dict[str, str] = {}
    shape = binary.shape
    parsing = optional.face_parsing_clean if shape_compatible(optional.face_parsing_clean, shape) else None
    parsing_raw = optional.face_parsing_raw if shape_compatible(optional.face_parsing_raw, shape) else None
    vision = optional.vision_contour_fill if shape_compatible(optional.vision_contour_fill, shape) else None
    vision_expanded = optional.vision_expanded if shape_compatible(optional.vision_expanded, shape) else None

    if optional.face_parsing_raw is not None and parsing_raw is None:
        skips["face_parsing_raw"] = "face_parsing_dimension_mismatch"
    elif parsing_raw is not None:
        masks["face_parsing_raw"] = parsing_raw

    if optional.face_parsing_clean is not None and parsing is None:
        skips["face_parsing_clean"] = "face_parsing_dimension_mismatch"
    elif parsing is not None:
        masks["face_parsing_clean"] = parsing

    if optional.vision_contour_fill is not None and vision is None:
        skips["vision_contour_fill"] = "apple_vision_dimension_mismatch"
    elif vision is not None:
        masks["vision_contour_fill"] = vision

    if optional.vision_expanded is not None and vision_expanded is None:
        skips["vision_expanded"] = "apple_vision_dimension_mismatch"
    elif vision_expanded is not None:
        masks["vision_expanded"] = vision_expanded

    if parsing is not None and vision_expanded is not None:
        masks["parsing_clamped_by_vision"] = keep_plausible_components(close_mask(parsing & vision_expanded, 1), 2)
    elif "parsing_clamped_by_vision" not in optional.skipped_reasons:
        skips["parsing_clamped_by_vision"] = "requires_face_parsing_and_apple_vision_same_dimensions"

    available_aux = [mask for mask in (parsing, vision_expanded) if mask is not None]
    if len(available_aux) >= 2:
        aux_union = np.zeros_like(clean, dtype=bool)
        aux_vote = clean.astype(np.uint8)
        for mask in available_aux:
            aux_union |= mask
            aux_vote += mask.astype(np.uint8)
        near_gold = dilate(clean, 12)
        masks["hybrid_conservative"] = keep_plausible_components(close_mask(erode(clean, 1) & dilate(aux_union, 4), 1), 2)
        masks["hybrid_balanced"] = keep_plausible_components(close_mask(aux_vote >= 2, 1), 2)
        masks["hybrid_coverage"] = keep_plausible_components(close_mask(clean | ((aux_union & near_gold)), 2), 2)
    elif any(key not in optional.skipped_reasons for key in ("hybrid_conservative", "hybrid_balanced", "hybrid_coverage")):
        reason = "requires_at_least_two_auxiliary_silver_signals_same_dimensions"
        skips["hybrid_conservative"] = reason
        skips["hybrid_balanced"] = reason
        skips["hybrid_coverage"] = reason

    for candidate_id, reason in optional.skipped_reasons.items():
        skips.setdefault(candidate_id, reason)
    return masks, skips


def score_candidate(candidate: np.ndarray, gold: np.ndarray, optional: OptionalSignals) -> dict[str, Any]:
    candidate_positive = int(np.count_nonzero(candidate))
    gold_positive = int(np.count_nonzero(gold))
    intersection = int(np.count_nonzero(candidate & gold))
    union = int(np.count_nonzero(candidate | gold))
    false_positive = candidate_positive - intersection
    false_negative = gold_positive - intersection
    precision = intersection / candidate_positive if candidate_positive else 0.0
    recall = intersection / gold_positive if gold_positive else 0.0
    iou = intersection / union if union else 0.0
    outside_spill = false_positive / candidate_positive if candidate_positive else 1.0
    inner_mouth = optional.face_parsing_inner_mouth if shape_compatible(optional.face_parsing_inner_mouth, candidate.shape) else None
    inner_mouth_spill = (
        int(np.count_nonzero(candidate & inner_mouth)) / candidate_positive
        if candidate_positive and inner_mouth is not None and np.any(inner_mouth)
        else None
    )
    skin_band = dilate(gold, 12) & ~gold
    skin_band_spill = int(np.count_nonzero(candidate & skin_band)) / candidate_positive if candidate_positive else 1.0
    comp_count = component_count(candidate)
    holes = approximate_hole_count(candidate)
    area_ratio = candidate_positive / candidate.size
    perimeter = perimeter_pixels(candidate)
    edge_roughness = perimeter / math.sqrt(candidate_positive) if candidate_positive else None
    boundary_cleanliness = 0.0 if edge_roughness is None else max(0.0, min(1.0, 1.0 - max(edge_roughness - 4.0, 0.0) / 18.0))
    bbox_info = bbox(candidate)
    bbox_score = 0.0
    if bbox_info["available"]:
        width_ratio = bbox_info["width"] / candidate.shape[1]
        height_ratio = bbox_info["height"] / candidate.shape[0]
        bbox_score = 1.0 if 0.10 <= width_ratio <= 0.70 and 0.01 <= height_ratio <= 0.22 else 0.5

    hard_rejects: list[str] = []
    if candidate_positive == 0:
        hard_rejects.append("candidate_empty")
    if area_ratio > 0.06:
        hard_rejects.append("candidate_area_ratio_above_0_06")
    if comp_count > 3:
        hard_rejects.append("component_count_above_3")
    if outside_spill > 0.45:
        hard_rejects.append("outside_gold_spill_above_0_45")
    if recall < 0.55:
        hard_rejects.append("lip_coverage_recall_below_0_55")
    if precision < 0.55:
        hard_rejects.append("lip_precision_below_0_55")
    if inner_mouth_spill is not None and inner_mouth_spill > 0.08:
        hard_rejects.append("inner_mouth_spill_above_0_08")

    vision_agreement = (
        mask_iou(candidate, optional.vision_contour_fill)
        if shape_compatible(optional.vision_contour_fill, candidate.shape)
        else None
    )
    parsing_agreement = (
        mask_iou(candidate, optional.face_parsing_clean)
        if shape_compatible(optional.face_parsing_clean, candidate.shape)
        else None
    )
    aux_values = [value for value in (vision_agreement, parsing_agreement) if value is not None]
    auxiliary_agreement = float(sum(aux_values) / len(aux_values)) if aux_values else None
    auxiliary_score = auxiliary_agreement if auxiliary_agreement is not None else 0.0

    base_score = (
        0.35 * iou
        + 0.25 * precision
        + 0.20 * recall
        + 0.10 * boundary_cleanliness
        + 0.05 * auxiliary_score
        + 0.05 * bbox_score
    )
    penalties = min(0.20, outside_spill * 0.20) + min(0.10, skin_band_spill * 0.10)
    if comp_count > 1:
        penalties += min(0.15, 0.05 * (comp_count - 1))
    final_score = max(0.0, min(1.0, base_score - penalties))

    metric_unavailable_reasons: list[str] = []
    if inner_mouth_spill is None:
        metric_unavailable_reasons.append("inner_mouth_signal_unavailable_or_empty")
    if vision_agreement is None:
        metric_unavailable_reasons.append("vision_signal_unavailable_or_dimension_mismatch")
    if parsing_agreement is None:
        metric_unavailable_reasons.append("face_parsing_signal_unavailable_or_dimension_mismatch")
    metric_unavailable_reasons.append("arface_coordinate_pairing_not_requested")

    return {
        "goldIoU": iou,
        "lipCoverageRecall": recall,
        "lipPrecision": precision,
        "outsideGoldSpill": outside_spill,
        "innerMouthSpill": inner_mouth_spill,
        "skinBandSpill": skin_band_spill,
        "componentCount": comp_count,
        "holeCount": holes,
        "edgeRoughness": edge_roughness,
        "bboxPlausibility": bbox_score,
        "visionAgreement": vision_agreement,
        "faceParsingAgreement": parsing_agreement,
        "arfaceEnvelopeAgreement": None,
        "positivePixels": candidate_positive,
        "goldPositivePixels": gold_positive,
        "intersectionPixels": intersection,
        "falsePositivePixels": false_positive,
        "falseNegativePixels": false_negative,
        "areaRatio": area_ratio,
        "boundaryCleanliness": boundary_cleanliness,
        "auxiliarySignalAgreement": auxiliary_agreement,
        "hardRejects": hard_rejects,
        "metricUnavailableReasons": metric_unavailable_reasons,
        "finalScore": final_score,
    }


def make_contact_sheet(entries: list[tuple[str, Image.Image]], output_path: Path) -> None:
    thumb_w, thumb_h = 260, 170
    label_h = 28
    cols = 3
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, (label, image) in enumerate(entries):
        col = idx % cols
        row = idx // cols
        thumb = ImageOps.exif_transpose(image.convert("RGB"))
        thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = col * thumb_w + (thumb_w - thumb.width) // 2
        y = row * (thumb_h + label_h)
        sheet.paste(thumb, (x, y))
        draw.rectangle((col * thumb_w, y + thumb_h, (col + 1) * thumb_w - 1, y + thumb_h + label_h), fill=(245, 245, 245))
        draw.text((col * thumb_w + 6, y + thumb_h + 7), label[:42], fill=(0, 0, 0))
    sheet.save(output_path)


def aggregate_scores(per_candidate: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for candidate_id, scores in per_candidate.items():
        valid = [score for score in scores if not score["hardRejects"]]
        score_basis = valid if valid else scores
        final_scores = [float(score["finalScore"]) for score in score_basis]
        hard_rejects = sorted({reason for score in scores for reason in score["hardRejects"]})
        aggregated[candidate_id] = {
            "candidateId": candidate_id,
            "averageFinalScore": float(sum(final_scores) / len(final_scores)) if final_scores else 0.0,
            "minFinalScore": float(min(final_scores)) if final_scores else 0.0,
            "maxFinalScore": float(max(final_scores)) if final_scores else 0.0,
            "compatibleGoldReferenceCount": len(scores),
            "validGoldReferenceCount": len(valid),
            "hardRejects": hard_rejects,
            "metricUnavailableReasons": sorted(
                {reason for score in scores for reason in score["metricUnavailableReasons"]}
            ),
        }
    return aggregated


def choose_policy(aggregated: dict[str, dict[str, Any]], source_count: int) -> dict[str, Any]:
    preferred_order = {
        "hybrid_balanced": 0,
        "gold_clean_morphology": 1,
        "hybrid_conservative": 2,
        "gold_exact_binary": 3,
        "gold_alpha_soft": 4,
        "hybrid_coverage": 5,
        "gold_conservative_erode": 6,
        "gold_coverage_dilate": 7,
        "parsing_clamped_by_vision": 8,
        "face_parsing_clean": 9,
        "vision_contour_fill": 10,
        "vision_expanded": 11,
        "face_parsing_raw": 12,
    }
    ranked = sorted(
        aggregated.values(),
        key=lambda item: (
            item["averageFinalScore"],
            item["validGoldReferenceCount"],
            -preferred_order.get(item["candidateId"], 99),
        ),
        reverse=True,
    )
    if not ranked:
        return {
            "schemaVersion": POLICY_SCHEMA_VERSION,
            "experimentDecision": "blocked",
            "selectedCandidateId": None,
            "selectedPolicyFamily": None,
            "finalScore": 0.0,
            "scoreMargin": 0.0,
            "acceptedGoldSourceIds": [],
            "hardRejects": ["no_candidates_scored"],
            "metricUnavailableReasons": [],
            "requiresHumanReview": True,
            "nextAction": "fix_inputs",
        }
    top = ranked[0]
    second_score = ranked[1]["averageFinalScore"] if len(ranked) > 1 else 0.0
    margin = float(top["averageFinalScore"] - second_score)
    optional_missing = sorted(
        set(top.get("metricUnavailableReasons", []))
        | {
            "coordinate_pairing_not_performed",
            "same_moment_arface_export_not_matched",
            "human_review_required_before_m1_ready",
        }
    )
    decision = "partial_needs_review"
    next_action = "human_review_candidates"
    if (
        top["averageFinalScore"] >= 0.75
        and margin >= 0.05
        and top["validGoldReferenceCount"] >= min(2, source_count)
        and not top["hardRejects"]
        and not optional_missing
    ):
        decision = "ready_for_coordinate_pairing"
        next_action = "coordinate_pair_selected_gold"

    family = "gold_clean"
    if top["candidateId"].startswith("vision_"):
        family = "vision"
    elif top["candidateId"].startswith("face_parsing"):
        family = "parsing"
    elif top["candidateId"].startswith("hybrid"):
        family = "hybrid"
    elif "clamped_by_vision" in top["candidateId"]:
        family = "hybrid"

    return {
        "schemaVersion": POLICY_SCHEMA_VERSION,
        "experimentDecision": decision,
        "selectedCandidateId": top["candidateId"],
        "selectedPolicyFamily": family,
        "finalScore": top["averageFinalScore"],
        "scoreMargin": margin,
        "selectedCandidateValidGoldReferenceCount": top["validGoldReferenceCount"],
        "selectedCandidateCompatibleGoldReferenceCount": top["compatibleGoldReferenceCount"],
        "acceptedGoldSourceIds": [],
        "hardRejects": top["hardRejects"],
        "metricUnavailableReasons": optional_missing,
        "requiresHumanReview": True,
        "nextAction": next_action,
    }


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest
    run_id = args.run_id or f"experiment-{utc_stamp()}"
    output_dir = args.output_root / run_id
    ensure_dirs(output_dir)

    manifest = load_json(manifest_path)
    manifest_sha = sha256_file(manifest_path)
    optional = load_optional_signals(args)
    manifest_blockers: list[str] = []
    if manifest.get("acceptedAsGold") is not True:
        manifest_blockers.append("manifest_acceptedAsGold_not_true")
    if manifest.get("localOnly") is not True:
        manifest_blockers.append("manifest_localOnly_not_true")
    if manifest.get("uploadAllowed") is not False:
        manifest_blockers.append("manifest_uploadAllowed_not_false")
    if manifest.get("sourceLineage") == REJECTED_LINEAGE:
        manifest_blockers.append("manifest_uses_rejected_lineage")
    if manifest.get("rejectedLineageExcluded") != REJECTED_LINEAGE:
        manifest_blockers.append("rejected_lineage_exclusion_not_recorded")

    sources, file_reports, file_blockers = load_gold_sources(manifest_path, manifest)
    blockers = manifest_blockers + file_blockers

    input_manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAt": utc_now(),
        "sourceManifestPath": str(manifest_path),
        "sourceManifestSha256": manifest_sha,
        "privacy": {
            "localOnly": True,
            "uploadAllowed": False,
            "rawGoldOverwritten": False,
            "liveFaceParsingRuntime": False,
            "coreMlRuntime": False,
            "unityFrameworkBuild": False,
            "xcodeBuild": False,
            "iphoneBuild": False,
        },
        "lineageRules": {
            "goldAllowlist": "e7-user-gold-raw-20260626_manifest_only",
            "rejectedLineageExcluded": REJECTED_LINEAGE,
            "manualPolygonLineageUsed": False,
        },
        "files": file_reports,
        "extractableGoldSources": [source.source_id for source in sources],
        "optionalSignals": {
            "reports": optional.reports,
            "skippedReasons": optional.skipped_reasons,
            "appleVision": "silver_auxiliary_loaded"
            if optional.vision_contour_fill is not None
            else "unavailable_or_rejected",
            "faceParsing": "silver_auxiliary_loaded"
            if optional.face_parsing_clean is not None
            else "unavailable_or_rejected",
            "arfaceCoordinatePair": "metadata_only_not_coordinate_paired",
            "colorGradient": "confidence_gate_loaded"
            if optional.color_gradient_confidence is not None
            else "unavailable",
            "userAdjustmentReview": "not_used_in_14b_dev_run",
        },
        "blockers": blockers,
    }
    write_json(output_dir / "input_manifest.json", input_manifest)

    extraction_reports: list[dict[str, Any]] = []
    per_candidate_scores: dict[str, list[dict[str, Any]]] = {candidate_id: [] for candidate_id in CANDIDATE_FAMILIES}
    skipped_reasons: dict[str, set[str]] = {candidate_id: set() for candidate_id in CANDIDATE_FAMILIES}
    contact_entries: list[tuple[str, Image.Image]] = []

    if blockers:
        scores: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "status": "blocked",
            "blockers": blockers,
            "perCandidate": {},
            "skippedCandidates": [],
        }
        write_json(output_dir / "gold_extraction_report.json", {"schemaVersion": SCHEMA_VERSION, "sources": extraction_reports})
        write_json(output_dir / "mask_derivation_scores.json", scores)
        policy = {
            "schemaVersion": POLICY_SCHEMA_VERSION,
            "experimentDecision": "blocked",
            "selectedCandidateId": None,
            "selectedPolicyFamily": None,
            "finalScore": 0.0,
            "scoreMargin": 0.0,
            "acceptedGoldSourceIds": [],
            "hardRejects": blockers,
            "metricUnavailableReasons": [],
            "requiresHumanReview": True,
            "nextAction": "fix_inputs",
        }
        write_json(output_dir / "selected_policy.json", policy)
    else:
        for source in sources:
            image = Image.open(source.path)
            binary, soft, info = extract_mask_and_alpha(image)
            cleaned_gold = keep_main_components(binary, max_components=1)
            if np.any(cleaned_gold):
                binary = cleaned_gold
            gold_path = output_dir / "gold_extracted_masks" / f"{source.source_id}_gold_exact_binary.png"
            alpha_path = output_dir / "gold_extracted_masks" / f"{source.source_id}_gold_alpha_soft.png"
            mask_to_image(binary).save(gold_path)
            Image.fromarray(soft, mode="L").save(alpha_path)
            report = {
                "sourceId": source.source_id,
                "sourcePath": str(source.path),
                "role": source.role,
                "width": source.width,
                "height": source.height,
                "mode": source.mode,
                "sha256": source.sha256,
                "extraction": info,
                "positivePixels": int(np.count_nonzero(binary)),
                "areaRatio": float(np.count_nonzero(binary) / binary.size),
                "bbox": bbox(binary),
                "warnings": [],
                "goldMaskPath": str(gold_path),
                "goldAlphaPath": str(alpha_path),
                "contextPath": str(source.context_path) if source.context_path else None,
            }
            if report["positivePixels"] == 0:
                report["warnings"].append("empty_extracted_lip_mask")
            extraction_reports.append(report)

            context = Image.open(source.context_path) if source.context_path and source.context_path.exists() else image
            contact_entries.append((f"{source.source_id} gold", mask_to_image(binary).convert("RGB")))
            masks, source_skips = candidate_masks(binary, soft, optional)
            for candidate_id, reason in source_skips.items():
                skipped_reasons.setdefault(candidate_id, set()).add(reason)
            for candidate_id, candidate in masks.items():
                candidate_dir = output_dir / "candidates" / candidate_id
                candidate_dir.mkdir(parents=True, exist_ok=True)
                candidate_path = candidate_dir / f"{source.source_id}.png"
                mask_to_image(candidate).save(candidate_path)
                overlay = overlay_mask(context, candidate, f"{candidate_id} / {source.source_id}")
                overlay_path = output_dir / "overlays" / f"{candidate_id}_{source.source_id}_overlay.png"
                overlay.save(overlay_path)
                contact_entries.append((f"{candidate_id} {source.source_id}", overlay))
                score = score_candidate(candidate, binary, optional)
                score["sourceId"] = source.source_id
                score["candidatePath"] = str(candidate_path)
                score["overlayPath"] = str(overlay_path)
                per_candidate_scores.setdefault(candidate_id, []).append(score)

        write_json(
            output_dir / "gold_extraction_report.json",
            {
                "schemaVersion": SCHEMA_VERSION,
                "createdAt": utc_now(),
                "sourceManifestSha256": manifest_sha,
                "sources": extraction_reports,
            },
        )
        make_contact_sheet(contact_entries, output_dir / "contact_sheet.png")
        generated_scores = {candidate_id: scores for candidate_id, scores in per_candidate_scores.items() if scores}
        aggregated = aggregate_scores(generated_scores)
        skipped = [
            {
                "candidateId": candidate_id,
                "status": "skipped",
                "reason": ";".join(sorted(skipped_reasons.get(candidate_id, set()))) or "no_compatible_input_generated",
            }
            for candidate_id in CANDIDATE_FAMILIES
            if not per_candidate_scores.get(candidate_id)
        ]
        scores = {
            "schemaVersion": SCHEMA_VERSION,
            "createdAt": utc_now(),
            "status": "scored",
            "scoringMode": "gold_with_optional_silver_auxiliary_buildless",
            "perCandidate": generated_scores,
            "aggregatedCandidates": aggregated,
            "skippedCandidates": skipped,
            "hardRejectRules": {
                "candidateAreaRatioMax": 0.06,
                "componentCountMax": 3,
                "outsideGoldSpillMax": 0.45,
                "lipCoverageRecallMin": 0.55,
                "lipPrecisionMin": 0.55,
            },
        }
        write_json(output_dir / "mask_derivation_scores.json", scores)
        policy = choose_policy(aggregated, len(sources))
        policy["acceptedGoldSourceIds"] = [source.source_id for source in sources]
        policy["optionalSignalPolicy"] = {
            "appleVision": "silver_auxiliary_only",
            "faceParsing": "silver_auxiliary_only",
            "colorGradient": "confidence_gate_only_not_boundary_source",
            "arface": "metadata_only_not_coordinate_paired",
        }
        write_json(output_dir / "selected_policy.json", policy)

    if not contact_entries:
        Image.new("RGB", (640, 220), "white").save(output_dir / "contact_sheet.png")
    summary_policy = load_json(output_dir / "selected_policy.json")
    summary = [
        "# E7 Section 14B Mask Derivation Summary",
        "",
        f"- Run: `{run_id}`",
        f"- Decision: `{summary_policy['experimentDecision']}`",
        f"- Selected candidate: `{summary_policy.get('selectedCandidateId')}`",
        f"- Final score: `{summary_policy.get('finalScore')}`",
        f"- Score margin: `{summary_policy.get('scoreMargin')}`",
        f"- Next action: `{summary_policy.get('nextAction')}`",
        "",
        "## Scope Guard",
        "",
        "- Lip-only, local-only buildless derivation.",
        "- Raw gold files were not overwritten.",
        "- Rejected manual polygon lineage was not used.",
        "- No upload, live face parsing/Core ML runtime, UnityFramework build, Xcode build, or iPhone build was run.",
        "- This is not M1 ready, runtime ready, E7.3 Green, or Lip G/Y/R evidence.",
        "",
        "## Inputs",
        "",
        f"- Source manifest: `{manifest_path}`",
        f"- Source manifest sha256: `{manifest_sha}`",
        f"- Extractable lip gold sources: `{', '.join(source.source_id for source in sources) or 'none'}`",
        "",
        "## Required Candidate Families",
        "",
    ]
    for candidate_id in MIN_CANDIDATES:
        summary.append(f"- `{candidate_id}`: generated" if not blockers else f"- `{candidate_id}`: blocked")
    summary.extend(
        [
            "",
            "## Optional / Silver Candidate Families",
            "",
        ]
    )
    scores_for_summary = load_json(output_dir / "mask_derivation_scores.json")
    generated_candidate_ids = set(scores_for_summary.get("perCandidate", {}).keys())
    skipped_by_id = {
        item.get("candidateId"): item.get("reason")
        for item in scores_for_summary.get("skippedCandidates", [])
    }
    for candidate_id in CANDIDATE_FAMILIES:
        if candidate_id in MIN_CANDIDATES:
            continue
        if candidate_id in generated_candidate_ids:
            summary.append(f"- `{candidate_id}`: generated")
        else:
            summary.append(f"- `{candidate_id}`: skipped - `{skipped_by_id.get(candidate_id, 'not_generated')}`")
    summary.extend(
        [
            "",
            "## M1 Gate Impact",
            "",
            "- Satisfies buildless optional-signal integration for available Apple Vision and local/offline face parsing artifacts.",
            "- Fails M1 readiness because coordinate-paired selected gold/reference mask, human review, user-confirmed adjustment evidence, pucker/expression coverage, blendshape/face-state, visibility/front-most handling, held-out/eval plan, corner falloff, and accepted upper/lower/inner-mouth behavior remain unresolved or partial.",
            "- Does not claim M1 ready, runtime ready, E7.3 Green, or Lip G/Y/R.",
            "",
            "## Score Notes",
            "",
        ]
    )
    aggregated_for_summary = scores_for_summary.get("aggregatedCandidates", {})
    ranked_for_summary = sorted(
        aggregated_for_summary.values(),
        key=lambda item: item.get("averageFinalScore", 0.0),
        reverse=True,
    )[:5]
    for item in ranked_for_summary:
        summary.append(
            "- `{candidateId}`: score `{score:.6f}`, valid `{valid}/{compatible}`, hardRejects `{rejects}`".format(
                candidateId=item.get("candidateId"),
                score=float(item.get("averageFinalScore", 0.0)),
                valid=item.get("validGoldReferenceCount"),
                compatible=item.get("compatibleGoldReferenceCount"),
                rejects=",".join(item.get("hardRejects", [])) or "none",
            )
        )
    summary.append(
        "- Selection remains `partial_needs_review` because the top hybrid is not valid across both gold references and the margin over gold-only candidates is too small."
    )
    summary.extend(
        [
            "",
            "## Blockers / Review Reasons",
            "",
        ]
    )
    reasons = summary_policy.get("hardRejects", []) + summary_policy.get("metricUnavailableReasons", [])
    if reasons:
        for reason in reasons:
            summary.append(f"- `{reason}`")
    else:
        summary.append("- none")
    summary.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `input_manifest.json`",
            "- `gold_extracted_masks/`",
            "- `gold_extraction_report.json`",
            "- `candidates/`",
            "- `overlays/`",
            "- `contact_sheet.png`",
            "- `mask_derivation_scores.json`",
            "- `selected_policy.json`",
        ]
    )
    (output_dir / "mask_derivation_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(output_dir)
    print(summary_policy["experimentDecision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
