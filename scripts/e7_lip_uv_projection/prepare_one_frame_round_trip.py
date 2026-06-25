#!/usr/bin/env python3
"""Buildless Phase 3 lip UV projection preparation and one-frame round trip.

The script consumes the Phase 2 fusionSummary contract plus, when available,
one same-moment capture pair and a screen-space lip reference mask. It can either
write a readiness summary that names missing inputs, or produce the first
buildless lip mask -> ARFace UV -> screen overlay artifact set.

It does not run live face parsing, Core ML, Unity, Xcode, iPhone builds, upload
data, or claim E7.3 Green.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


EXPECTED_ARTIFACTS = (
    "lip_probability.png",
    "lip_coverage.png",
    "lip_unknown.png",
    "lip_debug_votes.png",
    "lip_variants.json",
    "round_trip_overlay.png",
    "summary.json",
    "summary.md",
)
REQUIRED_ARFACE_FIELDS = ("screenVertices", "uvs", "indices", "clipW")
CANDIDATE_IDS = ("lip-tight-auto-v0", "lip-tight-user-v0", "lip-safe-v0")


@dataclass
class CaptureFiles:
    capture_pair_id: str
    root: Path
    frame_path: Path
    export_path: Path


@dataclass
class BackProjection:
    probability: np.ndarray
    coverage: np.ndarray
    positive_votes: np.ndarray
    total_votes: np.ndarray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare or run the E7 lip Phase 3 one-frame UV round trip."
    )
    parser.add_argument(
        "fusion_summary",
        type=Path,
        help="Path to fusionSummary.json, or a directory containing it.",
    )
    parser.add_argument(
        "--capture-pair",
        type=Path,
        default=None,
        help="Directory containing same-moment frame.png and arface_export.json.",
    )
    parser.add_argument(
        "--mask",
        type=Path,
        default=None,
        help="Screen-space lip reference mask on the same frame.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for Phase 3 artifacts. Without this, summary prints to stdout.",
    )
    parser.add_argument("--uv-resolution", type=int, default=512)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--render-stride", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--mask-coordinate-space",
        choices=("image_pixel", "image_normalized"),
        default="image_pixel",
    )
    parser.add_argument(
        "--mask-source",
        choices=(
            "human_reviewed_gold",
            "face_parsing_silver",
            "vision_reference",
            "manual_reference",
            "contract_only",
        ),
        default="contract_only",
    )
    parser.add_argument(
        "--accepted-signal-id",
        action="append",
        default=[],
        help="Signal id accepted by Phase 2 for this mask. May be repeated.",
    )
    parser.add_argument(
        "--inner-mouth-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument(
        "--corner-falloff-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument(
        "--upper-lower-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument(
        "--rejected-signal-reason",
        action="append",
        default=[],
        help="Extra Phase 2/3 rejected signal reason. May be repeated.",
    )
    parser.add_argument(
        "--candidate-id",
        choices=CANDIDATE_IDS,
        default="lip-tight-user-v0",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when Phase 3 execution status is blocked.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_fusion_summary(path: Path) -> Path:
    if path.is_file():
        return path
    if not path.is_dir():
        raise FileNotFoundError(path)
    for candidate in (path / "fusionSummary.json", path / "summary.json"):
        if candidate.exists():
            return candidate
    matches = sorted(path.glob("*fusion*Summary*.json")) + sorted(path.glob("fusion*.json"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"No fusionSummary JSON found in {path}")


def rel(path: Path | None, base: Path | None) -> str | None:
    if path is None:
        return None
    if base is None:
        return str(path)
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def resolve_capture_pair(path: Path | None) -> tuple[CaptureFiles | None, list[str]]:
    if path is None:
        return None, ["missing_same_moment_capture_pair"]
    root = path.resolve()
    if not root.exists():
        return None, [f"capture_pair_path_not_found:{root}"]
    frame_path = root / "frame.png"
    export_path = root / "arface_export.json"
    missing = []
    if not frame_path.exists():
        missing.append("missing_capture_frame:frame.png")
    if not export_path.exists():
        missing.append("missing_arface_export:arface_export.json")
    if missing:
        return None, missing
    return CaptureFiles(root.name, root, frame_path, export_path), []


def load_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def load_mask(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    rgba = np.asarray(image)
    alpha = rgba[:, :, 3]
    alpha_ratio = float(np.count_nonzero(alpha > 8)) / float(alpha.size)
    if 0.0 < alpha_ratio < 0.90:
        return alpha > 8

    rgb = rgba[:, :, :3].astype(np.int16)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    gray = np.asarray(image.convert("L"))
    return (alpha > 8) & ((gray > 16) | (spread > 12))


def export_arrays(export: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    screen_vertices = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    uvs = np.asarray(export.get("uvs", []), dtype=np.float64)
    indices = np.asarray(export.get("indices", []), dtype=np.int32)
    if indices.ndim != 1:
        indices = indices.reshape(-1)
    return screen_vertices, uvs, indices


def arface_field_status(export: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    screen_vertices, uvs, indices = export_arrays(export)
    fields = {
        "screenVertices": "available" if len(screen_vertices) else "missing",
        "uvs": "available" if len(uvs) else "missing",
        "indices": "available" if len(indices) else "missing",
        "clipW": "available"
        if screen_vertices.ndim == 2 and screen_vertices.shape[1] >= 4
        else "missing",
    }
    blockers = [f"missing_arface_{key}" for key, status in fields.items() if status != "available"]
    if len(screen_vertices) and len(uvs) and len(screen_vertices) != len(uvs):
        blockers.append("screen_vertices_uv_count_mismatch")
    return fields, blockers


def iter_triangles(indices: np.ndarray) -> np.ndarray:
    usable = (len(indices) // 3) * 3
    return indices[:usable].reshape(-1, 3)


def barycentric_grid(
    xs: np.ndarray, ys: np.ndarray, tri_xy: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x0, y0 = tri_xy[0]
    x1, y1 = tri_xy[1]
    x2, y2 = tri_xy[2]
    denom = ((y1 - y2) * (x0 - x2)) + ((x2 - x1) * (y0 - y2))
    if abs(float(denom)) < 1e-6:
        empty = np.zeros(xs.shape, dtype=bool)
        return empty, xs, xs, xs
    w0 = (((y1 - y2) * (xs - x2)) + ((x2 - x1) * (ys - y2))) / denom
    w1 = (((y2 - y0) * (xs - x2)) + ((x0 - x2) * (ys - y2))) / denom
    w2 = 1.0 - w0 - w1
    inside = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
    return inside, w0, w1, w2


def interpolate_uv(
    tri_uv: np.ndarray, tri_w: np.ndarray, w0: np.ndarray, w1: np.ndarray, w2: np.ndarray
) -> np.ndarray:
    clip_w = np.where(np.abs(tri_w) < 1e-6, 1.0, tri_w)
    inv_w = 1.0 / clip_w
    denom = (w0 * inv_w[0]) + (w1 * inv_w[1]) + (w2 * inv_w[2])
    denom = np.where(np.abs(denom) < 1e-6, 1.0, denom)
    u = (
        (w0 * tri_uv[0, 0] * inv_w[0])
        + (w1 * tri_uv[1, 0] * inv_w[1])
        + (w2 * tri_uv[2, 0] * inv_w[2])
    ) / denom
    v = (
        (w0 * tri_uv[0, 1] * inv_w[0])
        + (w1 * tri_uv[1, 1] * inv_w[1])
        + (w2 * tri_uv[2, 1] * inv_w[2])
    ) / denom
    return np.column_stack((u, v))


def uv_to_rc(uv: np.ndarray, resolution: int) -> tuple[np.ndarray, np.ndarray]:
    u = np.clip(uv[:, 0], 0.0, 1.0)
    v = np.clip(uv[:, 1], 0.0, 1.0)
    cols = np.rint(u * (resolution - 1)).astype(np.int32)
    rows = np.rint((1.0 - v) * (resolution - 1)).astype(np.int32)
    return rows, cols


def back_project_mask(
    mask: np.ndarray,
    export: dict[str, Any],
    resolution: int,
    sample_stride: int,
) -> BackProjection:
    screen_vertices, uvs, indices = export_arrays(export)
    height, width = mask.shape
    positive_votes = np.zeros((resolution, resolution), dtype=np.uint32)
    total_votes = np.zeros((resolution, resolution), dtype=np.uint32)

    for tri in iter_triangles(indices):
        if np.any(tri < 0) or np.any(tri >= len(screen_vertices)):
            continue
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(float(np.min(tri_xy[:, 0])))))
        max_x = min(width - 1, int(math.ceil(float(np.max(tri_xy[:, 0])))))
        min_y = max(0, int(math.floor(float(np.min(tri_xy[:, 1])))))
        max_y = min(height - 1, int(math.ceil(float(np.max(tri_xy[:, 1])))))
        if max_x < min_x or max_y < min_y:
            continue

        x_values = np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64)
        y_values = np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64)
        if x_values.size == 0 or y_values.size == 0:
            continue
        xs, ys = np.meshgrid(x_values, y_values)
        inside, w0, w1, w2 = barycentric_grid(xs, ys, tri_xy)
        if not np.any(inside):
            continue

        inside_x = xs[inside].astype(np.int32)
        inside_y = ys[inside].astype(np.int32)
        uv = interpolate_uv(
            uvs[tri],
            tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3),
            w0[inside],
            w1[inside],
            w2[inside],
        )
        rows, cols = uv_to_rc(uv, resolution)
        positive = mask[inside_y, inside_x]
        np.add.at(total_votes, (rows, cols), 1)
        np.add.at(positive_votes, (rows[positive], cols[positive]), 1)

    with np.errstate(divide="ignore", invalid="ignore"):
        probability = np.divide(
            positive_votes,
            total_votes,
            out=np.zeros_like(positive_votes, dtype=np.float32),
            where=total_votes > 0,
        )
    return BackProjection(probability, total_votes > 0, positive_votes, total_votes)


def render_atlas_to_screen(
    probability: np.ndarray,
    export: dict[str, Any],
    frame_size: tuple[int, int],
    threshold: float,
    sample_stride: int,
) -> np.ndarray:
    width, height = frame_size
    screen_vertices, uvs, indices = export_arrays(export)
    predicted = np.zeros((height, width), dtype=bool)

    for tri in iter_triangles(indices):
        if np.any(tri < 0) or np.any(tri >= len(screen_vertices)):
            continue
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(float(np.min(tri_xy[:, 0])))))
        max_x = min(width - 1, int(math.ceil(float(np.max(tri_xy[:, 0])))))
        min_y = max(0, int(math.floor(float(np.min(tri_xy[:, 1])))))
        max_y = min(height - 1, int(math.ceil(float(np.max(tri_xy[:, 1])))))
        if max_x < min_x or max_y < min_y:
            continue

        x_values = np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64)
        y_values = np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64)
        xs, ys = np.meshgrid(x_values, y_values)
        inside, w0, w1, w2 = barycentric_grid(xs, ys, tri_xy)
        if not np.any(inside):
            continue

        uv = interpolate_uv(
            uvs[tri],
            tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3),
            w0[inside],
            w1[inside],
            w2[inside],
        )
        rows, cols = uv_to_rc(uv, probability.shape[0])
        selected = probability[rows, cols] >= threshold
        inside_x = xs[inside].astype(np.int32)
        inside_y = ys[inside].astype(np.int32)
        predicted[inside_y[selected], inside_x[selected]] = True

    return predicted


def save_probability(path: Path, probability: np.ndarray) -> None:
    Image.fromarray(np.rint(np.clip(probability, 0.0, 1.0) * 255).astype(np.uint8)).save(path)


def save_coverage(path: Path, coverage: np.ndarray) -> None:
    Image.fromarray((coverage.astype(np.uint8) * 255)).save(path)


def save_debug_votes(path: Path, positive_votes: np.ndarray, total_votes: np.ndarray) -> None:
    max_positive = max(1, int(positive_votes.max()))
    max_total = max(1, int(total_votes.max()))
    image = np.zeros((*positive_votes.shape, 3), dtype=np.uint8)
    image[:, :, 0] = np.rint(np.clip(positive_votes / max_positive, 0, 1) * 255).astype(np.uint8)
    image[:, :, 1] = np.rint(np.clip(total_votes / max_total, 0, 1) * 255).astype(np.uint8)
    image[:, :, 2] = np.where(total_votes > 0, 80, 0).astype(np.uint8)
    Image.fromarray(image).save(path)


def metrics(predicted: np.ndarray, reference: np.ndarray) -> dict[str, Any]:
    tp = int(np.count_nonzero(predicted & reference))
    fp = int(np.count_nonzero(predicted & ~reference))
    fn = int(np.count_nonzero(~predicted & reference))
    candidate_positive = int(np.count_nonzero(predicted))
    reference_positive = int(np.count_nonzero(reference))
    union = tp + fp + fn
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "candidatePositive": candidate_positive,
        "referencePositive": reference_positive,
        "precision": round(tp / (tp + fp), 4) if (tp + fp) else 0.0,
        "recall": round(tp / (tp + fn), 4) if (tp + fn) else 0.0,
        "iou": round(tp / union, 4) if union else 0.0,
        "leakage": round(fp / candidate_positive, 4) if candidate_positive else 0.0,
        "miss": round(fn / reference_positive, 4) if reference_positive else 0.0,
    }


def save_round_trip_overlay(
    path: Path, frame: Image.Image, reference: np.ndarray, predicted: np.ndarray
) -> None:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    overlay = np.zeros_like(base)
    tp = predicted & reference
    fp = predicted & ~reference
    fn = ~predicted & reference
    overlay[tp] = [80, 255, 80]
    overlay[fp] = [255, 70, 70]
    overlay[fn] = [70, 130, 255]
    active = tp | fp | fn
    base[active] = (base[active] * 0.45) + (overlay[active] * 0.55)
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(path)


def status_from(blockers: list[str], warnings: list[str]) -> str:
    if blockers:
        return "blocked"
    if warnings:
        return "partial"
    return "ready"


def build_lip_variants(
    path: Path,
    summary: dict[str, Any],
    candidate_id: str,
    threshold: float,
) -> None:
    variants = {
        "schemaVersion": "e7-lip-uv-projection-variants-v0",
        "region": "lip",
        "primaryCandidateId": candidate_id,
        "variants": [
            {
                "candidateId": "lip-tight-auto-v0",
                "threshold": threshold,
                "maskTexture": "lip_probability.png",
                "useUserAdjustment": False,
            },
            {
                "candidateId": "lip-tight-user-v0",
                "threshold": threshold,
                "maskTexture": "lip_probability.png",
                "useUserAdjustment": True,
            },
            {
                "candidateId": "lip-safe-v0",
                "threshold": max(0.65, threshold),
                "maskTexture": "lip_probability.png",
                "useUserAdjustment": True,
                "rule": "prefer spill prevention before recall",
            },
        ],
        "sourceFusionId": summary.get("fusionId"),
        "doesNotImplementRuntime": True,
        "doesNotClaimE73Green": True,
    }
    path.write_text(json.dumps(variants, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E7 Lip Phase 3 UV Projection Summary",
        "",
        f"- Phase 3 execution status: `{summary['phase3ExecutionStatus']}`",
        f"- Fusion id: `{summary['fusion'].get('fusionId')}`",
        f"- Calibration id: `{summary['fusion'].get('calibrationId')}`",
        f"- Capture pair: `{summary['inputs']['capturePair'].get('capturePairId')}`",
        f"- Mask source: `{summary['inputs']['screenSpaceLipReferenceMask']['source']}`",
        "- Scope: lip only; cheek/eye remain extension slots only.",
        "- Limits: buildless, local-only, no live face parsing/Core ML runtime, no upload, no E7.3 Green claim.",
        "",
        "## Artifacts",
        "",
    ]
    for name, value in summary["artifacts"].items():
        lines.append(f"- `{name}`: {value}")
    lines.extend(["", "## Blockers / Warnings", ""])
    reasons = summary["blockers"] + summary["warnings"]
    if reasons:
        lines.extend(f"- `{reason}`" for reason in reasons)
    else:
        lines.append("- None.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_base_summary(
    args: argparse.Namespace,
    fusion_path: Path,
    fusion: dict[str, Any],
    capture_files: CaptureFiles | None,
    blockers: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-lip-uv-projection-summary-v0",
        "createdAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "phase3ExecutionStatus": status_from(blockers, warnings),
        "fusion": {
            "path": str(fusion_path),
            "schemaVersion": fusion.get("schemaVersion"),
            "fusionId": fusion.get("fusionId"),
            "calibrationId": fusion.get("calibrationId"),
            "phase2Status": fusion.get("phase2Status"),
            "region": fusion.get("region"),
        },
        "inputs": {
            "screenSpaceLipReferenceMask": {
                "status": "available" if args.mask else "missing",
                "path": str(args.mask.resolve()) if args.mask else None,
                "coordinateSpace": args.mask_coordinate_space,
                "source": args.mask_source,
                "acceptedSignalIds": args.accepted_signal_id,
                "derivedEvidenceOnly": True,
            },
            "capturePair": {
                "status": "available" if capture_files else "missing",
                "capturePairId": capture_files.capture_pair_id if capture_files else None,
                "path": str(capture_files.root) if capture_files else None,
                "framePath": str(capture_files.frame_path) if capture_files else None,
                "arFaceExportPath": str(capture_files.export_path) if capture_files else None,
            },
            "innerMouthExclusion": {"status": args.inner_mouth_status},
            "cornerFalloff": {"status": args.corner_falloff_status},
            "upperLowerSplit": {"status": args.upper_lower_status},
            "confidenceSummary": {
                "phase2Status": fusion.get("phase2Status"),
                "maskSource": args.mask_source,
                "referenceOnlyUntilRuntimeEvidence": True,
            },
            "rejectedSignalReasons": args.rejected_signal_reason,
        },
        "projectionRules": {
            "perspectiveCorrectUv": True,
            "frontMostVisibleTriangleOnly": "required_by_contract; depends_on_exported_visibility_or_depth",
            "grazingAngleDownweight": "contract_only_in_this_stub",
            "unknownNotNegative": True,
            "oneFrameRoundTripOnly": True,
        },
        "artifacts": {name: "pending" for name in EXPECTED_ARTIFACTS},
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": {
            "lipOnly": True,
            "cheekEyeExtensionSlotsOnly": True,
            "buildlessOnly": True,
            "doesNotClaimE73Green": True,
            "doesNotStartE74E75E76": True,
            "doesNotRunLiveFaceParsingOrCoreMl": True,
            "doesNotUpload": True,
            "doesNotStoreRawFramesLongTerm": True,
            "doesNotImplementUnityRuntimeCandidate": True,
        },
    }


def validate_contract(
    args: argparse.Namespace,
    fusion: dict[str, Any],
    capture_files: CaptureFiles | None,
) -> tuple[list[str], list[str], dict[str, Any] | None, Image.Image | None, np.ndarray | None]:
    blockers: list[str] = []
    warnings: list[str] = []
    export: dict[str, Any] | None = None
    frame: Image.Image | None = None
    mask: np.ndarray | None = None

    if fusion.get("schemaVersion") != "e7-lip-boundary-fusion-summary-v0":
        blockers.append("unsupported_fusion_summary_schema")
    if fusion.get("region") != "lip":
        blockers.append("non_lip_fusion_summary_not_in_scope")
    phase2_status = fusion.get("phase2Status")
    if phase2_status == "blocked":
        blockers.append("phase2_boundary_fusion_blocked")
    elif phase2_status != "ready":
        warnings.append(f"phase2_boundary_fusion_not_ready:{phase2_status}")

    if args.mask is None:
        blockers.append("missing_screen_space_lip_reference_mask")
    elif not args.mask.exists():
        blockers.append(f"screen_space_lip_reference_mask_not_found:{args.mask}")
    if args.mask_source == "contract_only":
        warnings.append("mask_source_contract_only_not_gold_or_silver")
    if not args.accepted_signal_id:
        warnings.append("accepted_signal_ids_missing")
    if args.inner_mouth_status != "available":
        warnings.append(f"inner_mouth_exclusion_{args.inner_mouth_status}")
    if args.corner_falloff_status != "available":
        warnings.append(f"corner_falloff_{args.corner_falloff_status}")
    if args.upper_lower_status != "available":
        warnings.append(f"upper_lower_split_{args.upper_lower_status}")
    warnings.extend(args.rejected_signal_reason)

    if capture_files is None:
        blockers.append("missing_same_moment_capture_pair")
        return blockers, warnings, export, frame, mask

    frame = load_rgb(capture_files.frame_path)
    export = load_json(capture_files.export_path)
    if export.get("capturePairId") and export.get("capturePairId") != capture_files.capture_pair_id:
        warnings.append("capture_pair_id_mismatch_between_path_and_export")
    if not export.get("annotationFrameClean", False):
        blockers.append("annotation_frame_not_clean")
    if not export.get("coordinateSpaceValidated", False):
        warnings.append("coordinate_space_validation_pending")

    arface_fields, arface_blockers = arface_field_status(export)
    blockers.extend(arface_blockers)
    if export.get("triangleVisibility"):
        warnings.append("triangle_visibility_available_but_not_consumed_by_prepare_stub")
    else:
        warnings.append("triangle_visibility_unavailable_front_most_rule_contract_only")

    if args.mask and args.mask.exists():
        mask = load_mask(args.mask)
        if args.mask_coordinate_space != "image_pixel":
            blockers.append("image_normalized_mask_not_supported_by_this_one_frame_stub")
        elif mask.shape != (frame.height, frame.width):
            blockers.append(
                f"mask_frame_size_mismatch:mask={mask.shape},frame={(frame.height, frame.width)}"
            )
        positive = int(np.count_nonzero(mask)) if mask is not None else 0
        if positive == 0:
            blockers.append("screen_space_lip_reference_mask_empty")

    if arface_fields:
        warnings.extend(
            f"arface_field_{field}_{status}"
            for field, status in arface_fields.items()
            if status != "available"
        )
    return blockers, warnings, export, frame, mask


def run_projection(
    args: argparse.Namespace,
    output_dir: Path,
    summary: dict[str, Any],
    export: dict[str, Any],
    frame: Image.Image,
    mask: np.ndarray,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    projection = back_project_mask(mask, export, args.uv_resolution, args.sample_stride)
    predicted = render_atlas_to_screen(
        projection.probability,
        export,
        frame.size,
        threshold=args.threshold,
        sample_stride=args.render_stride,
    )

    paths = {
        "lip_probability.png": output_dir / "lip_probability.png",
        "lip_coverage.png": output_dir / "lip_coverage.png",
        "lip_unknown.png": output_dir / "lip_unknown.png",
        "lip_debug_votes.png": output_dir / "lip_debug_votes.png",
        "lip_variants.json": output_dir / "lip_variants.json",
        "round_trip_overlay.png": output_dir / "round_trip_overlay.png",
    }
    save_probability(paths["lip_probability.png"], projection.probability)
    save_coverage(paths["lip_coverage.png"], projection.coverage)
    save_coverage(paths["lip_unknown.png"], ~projection.coverage)
    save_debug_votes(paths["lip_debug_votes.png"], projection.positive_votes, projection.total_votes)
    build_lip_variants(paths["lip_variants.json"], summary["fusion"], args.candidate_id, args.threshold)
    save_round_trip_overlay(paths["round_trip_overlay.png"], frame, mask, predicted)

    summary["roundTripScore"] = metrics(predicted, mask)
    summary["projectionStats"] = {
        "uvResolution": args.uv_resolution,
        "sampleStride": args.sample_stride,
        "renderStride": args.render_stride,
        "threshold": args.threshold,
        "positiveVotes": int(projection.positive_votes.sum()),
        "totalVotes": int(projection.total_votes.sum()),
        "coverageTexels": int(np.count_nonzero(projection.coverage)),
        "unknownTexels": int(np.count_nonzero(~projection.coverage)),
        "calibrationScore": "not_scored_in_phase3_prepare_stub",
        "futureEvalScore": "requires_held_out_frames",
    }
    for name, path in paths.items():
        summary["artifacts"][name] = str(path)
    return summary


def write_outputs(output_dir: Path | None, summary: dict[str, Any]) -> None:
    if output_dir is None:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_json = output_dir / "summary.json"
    summary_md = output_dir / "summary.md"
    summary["artifacts"]["summary.json"] = str(summary_json)
    summary["artifacts"]["summary.md"] = str(summary_md)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary_md(summary_md, summary)
    print(json.dumps({"summary": str(summary_json), "markdown": str(summary_md)}, indent=2))


def main() -> int:
    args = parse_args()
    fusion_path = find_fusion_summary(args.fusion_summary.resolve())
    fusion = load_json(fusion_path)
    capture_files, capture_path_blockers = resolve_capture_pair(args.capture_pair)
    blockers, warnings, export, frame, mask = validate_contract(args, fusion, capture_files)
    blockers.extend(capture_path_blockers)
    summary = build_base_summary(args, fusion_path, fusion, capture_files, blockers, warnings)

    can_project = (
        summary["phase3ExecutionStatus"] != "blocked"
        and args.output_dir is not None
        and export is not None
        and frame is not None
        and mask is not None
    )
    if can_project:
        try:
            summary = run_projection(args, args.output_dir.resolve(), summary, export, frame, mask)
        except Exception as exc:  # pragma: no cover - keeps the prep stub diagnostic.
            summary["blockers"] = sorted(set(summary["blockers"] + [f"projection_error:{exc}"]))
            summary["phase3ExecutionStatus"] = "blocked"

    write_outputs(args.output_dir.resolve() if args.output_dir else None, summary)
    if args.strict and summary["phase3ExecutionStatus"] == "blocked":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
