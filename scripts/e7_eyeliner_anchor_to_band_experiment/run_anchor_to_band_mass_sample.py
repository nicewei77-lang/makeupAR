#!/usr/bin/env python3
"""Run the E7 eyeliner anchor-to-band mass sample experiment.

This is a buildless/local-only experiment. It reuses the already-generated
MediaPipe landmark JSON and ARFace export for pair_face_20260627T091334Z_06.
It does not run live MediaPipe, upload data, copy external reference images,
build Xcode, or touch an iPhone.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.e7_eyeliner_candidate_experiment.run_eyeliner_candidate_experiment import (
    Candidate,
    EyeGeometry,
    bbox_for_points,
    build_eye_geometry,
    build_parametric_candidate,
    candidate_metrics,
    crop_image,
    draw_geometry_overlay,
    eye_width,
    mask_components,
    polygon_mask,
)
from scripts.e7_region_generate.build_region_candidates import (
    alpha_to_image,
    back_project_mask,
    comparison_metrics,
    erode,
    load_json,
    mask_to_image,
    render_atlas_to_screen,
    round_trip_overlay,
    soft_alpha,
    write_json,
    write_text,
)


DEFAULT_CAPTURE_PAIR = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06")
DEFAULT_DOC_REPORT = Path("docs/product/e7-eyeliner-anchor-to-band-experiment-report-2026-06-27")
BEST_REFERENCE_PATH = Path(
    "/tmp/codex-remote-attachments/019f0551-bf7f-7ee1-8fbb-e023dd51f124/"
    "017A56B8-DB3B-4D83-823A-BFE9AB4928F2/1-사진-1.jpg"
)
UV_RESOLUTION = 512


FAMILY_COUNTS = {
    "cat": 24,
    "puppy": 18,
    "sexy": 24,
    "winged": 30,
    "colored": 18,
    "doll": 18,
    "balanced_reference": 6,
    "tail_only_safe": 6,
}

FAMILY_COLORS = {
    "cat": (22, 20, 18),
    "puppy": (70, 48, 38),
    "sexy": (16, 14, 16),
    "winged": (18, 17, 16),
    "colored": (115, 32, 64),
    "doll": (78, 52, 42),
    "balanced_reference": (28, 72, 155),
    "tail_only_safe": (35, 116, 80),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E7 eyeliner anchor-to-band mass sample experiment.")
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--doc-report", type=Path, default=DEFAULT_DOC_REPORT)
    parser.add_argument("--uv-resolution", type=int, default=UV_RESOLUTION)
    parser.add_argument("--target-count", type=int, default=144)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_mediapipe(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slug_number(value: float, scale: int = 100) -> int:
    return int(round(abs(value) * scale))


def family_configs() -> dict[str, dict[str, Any]]:
    return {
        "cat": {
            "style": "sharp_lifted_outer_focused",
            "lineHeight": [-5.8, -5.2, -4.8],
            "innerStart": [0.18, 0.22, 0.28],
            "lineThickness": [5.5, 6.5, 7.5],
            "outerCornerFill": [0.16, 0.22, 0.28],
            "tailLength": [0.14, 0.20, 0.26],
            "tailAngle": [-17.0, -22.0, -27.0],
            "tailLift": [-1.5, -2.5],
            "taper": [1.05, 1.25, 1.45],
            "softness": [2.2, 3.0],
            "outerLift": [-2.0, -3.2],
            "previewOpacity": [0.65, 0.82],
        },
        "puppy": {
            "style": "soft_rounded_slightly_lowered",
            "lineHeight": [-4.8, -4.2, -3.6],
            "innerStart": [0.18, 0.24, 0.32],
            "lineThickness": [4.8, 5.8, 6.5],
            "outerCornerFill": [0.10, 0.14, 0.18],
            "tailLength": [0.08, 0.12, 0.16],
            "tailAngle": [-4.0, 2.0, 6.0],
            "tailLift": [0.0, 1.0],
            "taper": [0.75, 0.95, 1.1],
            "softness": [4.0, 5.0],
            "outerLift": [-0.5, 0.4],
            "previewOpacity": [0.48, 0.62],
        },
        "sexy": {
            "style": "long_smoky_outer_third",
            "lineHeight": [-5.2, -4.6, -4.0],
            "innerStart": [0.10, 0.16, 0.22],
            "lineThickness": [6.5, 8.0, 8.8],
            "outerCornerFill": [0.18, 0.24, 0.30],
            "tailLength": [0.18, 0.24, 0.30],
            "tailAngle": [-10.0, -16.0, -22.0],
            "tailLift": [-0.5, -1.8],
            "taper": [0.9, 1.15, 1.35],
            "softness": [3.8, 5.0],
            "outerLift": [-1.6, -2.6],
            "previewOpacity": [0.58, 0.74],
        },
        "winged": {
            "style": "clean_default_wing",
            "lineHeight": [-5.6, -5.0, -4.4],
            "innerStart": [0.18, 0.22, 0.28],
            "lineThickness": [5.8, 6.8, 7.8],
            "outerCornerFill": [0.16, 0.22, 0.28],
            "tailLength": [0.14, 0.20, 0.26],
            "tailAngle": [-18.0, -24.0, -30.0],
            "tailLift": [-1.0, -2.0, -3.0],
            "taper": [1.0, 1.2, 1.45],
            "softness": [2.8, 3.6, 4.4],
            "outerLift": [-2.4, -3.4],
            "previewOpacity": [0.60, 0.78],
        },
        "colored": {
            "style": "soft_wing_tintable_shape",
            "lineHeight": [-5.2, -4.6, -4.0],
            "innerStart": [0.18, 0.24, 0.30],
            "lineThickness": [4.8, 5.8, 6.8],
            "outerCornerFill": [0.12, 0.16, 0.22],
            "tailLength": [0.10, 0.16, 0.20],
            "tailAngle": [-8.0, -14.0, -18.0],
            "tailLift": [-0.8, -1.6],
            "taper": [0.9, 1.1, 1.25],
            "softness": [4.5, 5.8],
            "outerLift": [-1.2, -2.2],
            "previewOpacity": [0.42, 0.56],
        },
        "doll": {
            "style": "round_short_soft_cute",
            "lineHeight": [-4.8, -4.2, -3.8],
            "innerStart": [0.24, 0.30, 0.35],
            "lineThickness": [4.4, 5.2, 6.0],
            "outerCornerFill": [0.06, 0.10, 0.14],
            "tailLength": [0.05, 0.08, 0.12],
            "tailAngle": [-2.0, -6.0, -10.0],
            "tailLift": [0.0, -0.8],
            "taper": [0.7, 0.9, 1.05],
            "softness": [5.0, 6.2],
            "outerLift": [-0.4, -1.0],
            "previewOpacity": [0.40, 0.55],
        },
        "balanced_reference": {
            "style": "mp_upper_balanced_reference",
            "lineHeight": [-6.0, -5.5, -5.0],
            "innerStart": [0.10, 0.16],
            "lineThickness": [5.5, 6.0],
            "outerCornerFill": [0.04, 0.08],
            "tailLength": [0.04, 0.06, 0.08],
            "tailAngle": [-8.0, -12.0],
            "tailLift": [0.0],
            "taper": [0.6, 0.75],
            "softness": [3.0, 3.6],
            "outerLift": [-1.2],
            "previewOpacity": [0.62],
        },
        "tail_only_safe": {
            "style": "outer_only_safety_fallback",
            "lineHeight": [-4.6, -4.0, -3.6],
            "innerStart": [0.52, 0.58, 0.64],
            "lineThickness": [5.8, 6.8],
            "outerCornerFill": [0.08, 0.12],
            "tailLength": [0.08, 0.12, 0.16],
            "tailAngle": [-8.0, -14.0],
            "tailLift": [0.0, -1.0],
            "taper": [0.8, 1.05],
            "softness": [3.4, 4.2],
            "outerLift": [-0.8],
            "previewOpacity": [0.66],
        },
    }


def stratified_specs(target_count: int) -> list[dict[str, Any]]:
    configs = family_configs()
    planned_total = sum(FAMILY_COUNTS.values())
    if target_count != planned_total:
        # Keep the family ratios stable while honoring a caller-provided target.
        ratio = target_count / float(planned_total)
        counts = {family: max(1, int(round(count * ratio))) for family, count in FAMILY_COUNTS.items()}
    else:
        counts = FAMILY_COUNTS.copy()

    specs: list[dict[str, Any]] = []
    serial = 1
    for family, count in counts.items():
        cfg = configs[family]
        keys = [
            "lineHeight",
            "innerStart",
            "lineThickness",
            "outerCornerFill",
            "tailLength",
            "tailAngle",
            "tailLift",
            "taper",
            "softness",
            "outerLift",
            "previewOpacity",
        ]
        lengths = [len(cfg[key]) for key in keys]
        total_combos = math.prod(lengths)
        family_seed = sum(ord(ch) for ch in family)
        step = max(1, total_combos // max(1, count))
        seen_positions: set[int] = set()
        for idx in range(count):
            position = (family_seed + idx * step + idx * idx * 97) % total_combos
            while position in seen_positions:
                position = (position + 1) % total_combos
            seen_positions.add(position)
            params: dict[str, Any] = {}
            cursor = position
            for key in reversed(keys):
                values = cfg[key]
                params[key] = values[cursor % len(values)]
                cursor //= len(values)
            params["family"] = family
            params["style"] = cfg["style"]
            params["candidateIndex"] = serial
            params["familyIndex"] = idx + 1
            params["outerReach"] = 1.0
            params["excludeEyeOpening"] = True
            params["candidateId"] = (
                f"{family.replace('_', '-')}"
                f"-i{slug_number(params['innerStart']):02d}"
                f"-t{slug_number(params['lineThickness'], 10):02d}"
                f"-o{slug_number(params['outerCornerFill']):02d}"
                f"-l{slug_number(params['tailLength']):02d}"
                f"-a{slug_number(params['tailAngle'], 1):02d}"
                f"-s{slug_number(params['softness'], 10):02d}"
                f"-u{slug_number(params['tailLift'], 10):02d}"
                f"-v{idx + 1:03d}"
            )
            specs.append(params)
            serial += 1
    return specs[:target_count]


def eye_opening_mask(size: tuple[int, int], eyes: list[EyeGeometry]) -> np.ndarray:
    mask = np.zeros((size[1], size[0]), dtype=bool)
    for eye in eyes:
        mask |= polygon_mask(size, eye.eye_contour)
    return mask


def add_outer_corner_fill(
    candidate: Candidate,
    size: tuple[int, int],
    eyes: list[EyeGeometry],
    outer_corner_fill: float,
    thickness: float,
    softness: float,
    eye_opening_safety: np.ndarray,
) -> Candidate:
    if outer_corner_fill <= 0:
        return candidate
    fill_img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(fill_img)
    for eye in eyes:
        trace_eye = candidate.trace.get("lineTraces", {}).get(eye.side, {})
        centerline = [(float(item["x"]), float(item["y"])) for item in trace_eye.get("centerline", [])]
        tail_end_item = trace_eye.get("tailEnd")
        if not centerline:
            continue
        outer_idx = max(0, int(round(len(centerline) * 0.78)) - 1)
        base_inner = centerline[outer_idx]
        tail_start = centerline[-1]
        if tail_end_item:
            tail_end = (float(tail_end_item["x"]), float(tail_end_item["y"]))
        else:
            tail_end = (
                eye.outer_corner[0] + eye.tail_direction * eye_width(eye) * max(0.06, outer_corner_fill),
                eye.outer_corner[1] - thickness,
            )
        oc = eye.outer_corner
        base_drop = thickness * (0.30 + outer_corner_fill * 1.8)
        upper_lift = thickness * (0.35 + outer_corner_fill * 0.4)
        direction = eye.tail_direction
        oc_upper = (oc[0] + direction * eye_width(eye) * 0.014, oc[1] - upper_lift)
        oc_lower = (oc[0] + direction * eye_width(eye) * 0.020, oc[1] + base_drop)
        tail_base_lower = (tail_start[0], tail_start[1] + thickness * (0.36 + outer_corner_fill))
        polygon = [base_inner, tail_start, tail_end, tail_base_lower, oc_lower, oc_upper]
        draw.polygon(polygon, fill=255)
    fill = np.asarray(fill_img.filter(ImageFilter.GaussianBlur(radius=max(0.0, softness * 0.25)))) > 10
    combined = candidate.mask | fill
    # Keep the lashline edge but prevent block/ring failures inside the eye opening.
    combined &= ~eye_opening_safety
    trace = dict(candidate.trace)
    trace["outerCornerFill"] = outer_corner_fill
    trace["eyeOpeningExcluded"] = True
    adjustment = dict(candidate.adjustment)
    adjustment["outerCornerFill"] = outer_corner_fill
    adjustment["maxLidFillHeightGuard"] = 0.18
    return replace(candidate, mask=combined, alpha=soft_alpha(combined, softness), trace=trace, adjustment=adjustment)


def build_candidate_from_spec(
    size: tuple[int, int],
    frame: Image.Image,
    eyes: list[EyeGeometry],
    spec: dict[str, Any],
    opening_safety: np.ndarray,
) -> Candidate:
    candidate = build_parametric_candidate(
        size,
        frame,
        eyes,
        spec["candidateId"],
        f"anchor-to-band-{spec['family']}",
        f"anchor_to_band_{spec['family']}",
        spec["innerStart"],
        spec["outerReach"],
        spec["lineHeight"],
        spec["lineThickness"],
        spec["tailLength"],
        spec["tailAngle"],
        spec["tailLift"],
        spec["taper"],
        spec["softness"],
        False,
        edge_snap=False,
        outer_lift=spec["outerLift"],
        warnings=[
            "buildless static frame only; blink/yaw iPhone test deferred",
            "generated from MediaPipe upper eyelid anchor; no external asset copied",
        ],
    )
    candidate = add_outer_corner_fill(
        candidate,
        size,
        eyes,
        spec["outerCornerFill"],
        spec["lineThickness"],
        spec["softness"],
        opening_safety,
    )
    trace = dict(candidate.trace)
    trace["family"] = spec["family"]
    trace["styleTaxonomy"] = spec["style"]
    trace["bestReferenceUsage"] = "shape_taxonomy_only_not_runtime_asset"
    trace["candidateIndex"] = spec["candidateIndex"]
    trace["familyIndex"] = spec["familyIndex"]
    adjustment = dict(candidate.adjustment)
    adjustment["previewOpacity"] = spec["previewOpacity"]
    return replace(candidate, trace=trace, adjustment=adjustment)


def cosmetic_overlay(frame: Image.Image, alpha: np.ndarray, color: tuple[int, int, int], opacity: float) -> Image.Image:
    base = frame.convert("RGB")
    overlay = Image.new("RGB", base.size, color)
    a = np.rint(np.clip(alpha * opacity, 0, 1) * 255).astype(np.uint8)
    return Image.composite(overlay, base, Image.fromarray(a, mode="L")).convert("RGB")


def save_contact_sheet(
    items: list[tuple[str, Path]],
    output: Path,
    thumb_width: int = 260,
    cols: int = 4,
    label_height: int = 42,
) -> None:
    tiles: list[Image.Image] = []
    for label, path in items:
        img = Image.open(path).convert("RGB")
        ratio = thumb_width / img.width
        thumb = img.resize((thumb_width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb.width, thumb.height + label_height), "white")
        tile.paste(thumb, (0, label_height))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 5), label[:48], fill=(0, 0, 0))
        tiles.append(tile)
    if not tiles:
        return
    cols = max(1, min(cols, len(tiles)))
    rows = math.ceil(len(tiles) / cols)
    cell_w = max(t.width for t in tiles)
    cell_h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
    for idx, tile in enumerate(tiles):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        sheet.paste(tile, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def area_by_eye(mask: np.ndarray, eyes: list[EyeGeometry], size: tuple[int, int]) -> list[int]:
    areas = []
    for eye in eyes:
        bbox = bbox_for_points(eye.eye_contour, size, 85)
        crop = mask[bbox[1] : bbox[3], bbox[0] : bbox[2]]
        areas.append(int(np.count_nonzero(crop)))
    return areas


def eye_height_avg(eyes: list[EyeGeometry]) -> float:
    heights = []
    for eye in eyes:
        ys = [p[1] for p in eye.eye_contour]
        heights.append(max(1.0, max(ys) - min(ys)))
    return float(np.mean(heights))


def enrich_metrics(
    base_metrics: dict[str, Any],
    candidate: Candidate,
    spec: dict[str, Any],
    eyes: list[EyeGeometry],
    size: tuple[int, int],
    opening_safety: np.ndarray,
) -> dict[str, Any]:
    avg_eye_height = eye_height_avg(eyes)
    areas = area_by_eye(candidate.mask, eyes, size)
    outer_gap = base_metrics.get("tailStartDistanceFromOuterCornerPx")
    overlap_ratio = base_metrics.get("eyeOpeningOverlapRatio") or 0.0
    lid_fill_ratio = float(spec["lineThickness"]) / max(1.0, avg_eye_height)
    lower_lid_coverage = overlap_ratio
    empty_side_penalty = 1.0 if len(areas) < 2 or min(areas) == 0 else 0.0
    return {
        **base_metrics,
        "outerCornerGapPx": outer_gap,
        "outerCornerFillScore": round(min(1.0, float(spec["outerCornerFill"]) / 0.22), 6),
        "tailTaperScore": round(min(1.0, float(spec["taper"]) / 1.35), 6),
        "tailAngleScore": round(max(0.0, 1.0 - abs(abs(float(spec["tailAngle"])) - 20.0) / 24.0), 6),
        "lidFillHeightRatio": round(lid_fill_ratio, 6),
        "lowerLidCoverageRatio": round(lower_lid_coverage, 6),
        "eyeSideAreas": areas,
        "emptySidePenalty": empty_side_penalty,
        "safetyOpeningPixels": int(np.count_nonzero(candidate.mask & opening_safety)),
    }


def score_candidate(report: dict[str, Any]) -> float:
    metrics = report["metrics"]
    adjustment = report["adjustment"]
    family = report["familyKey"]
    overlap = metrics.get("eyeOpeningOverlapRatio") or 0.0
    distance = metrics.get("upperLidMeanDistancePx") or 99.0
    continuity = metrics.get("lineContinuityScore") or 0.0
    symmetry = metrics.get("leftRight", {}).get("smallLargeRatio") or 0.0
    outer_fill = metrics.get("outerCornerFillScore") or 0.0
    taper = metrics.get("tailTaperScore") or 0.0
    lid_ratio = metrics.get("lidFillHeightRatio") or 1.0
    lower = metrics.get("lowerLidCoverageRatio") or 0.0
    tail_len = adjustment.get("tailLength", 0.0)
    wing_family_bonus = {
        "winged": 0.11,
        "cat": 0.08,
        "colored": 0.04,
        "balanced_reference": 0.03,
        "tail_only_safe": 0.02,
        "puppy": 0.02,
        "doll": 0.01,
        "sexy": 0.00,
    }.get(family, 0.0)
    score = (
        (1.0 - min(1.0, overlap * 16.0)) * 0.22
        + max(0.0, 1.0 - min(1.0, distance / 13.0)) * 0.14
        + continuity * 0.12
        + symmetry * 0.12
        + outer_fill * 0.16
        + taper * 0.08
        + max(0.0, 1.0 - abs(tail_len - 0.18) / 0.18) * 0.06
        + max(0.0, 1.0 - max(0.0, lid_ratio - 0.10) / 0.12) * 0.05
        + max(0.0, 1.0 - lower * 20.0) * 0.05
        + wing_family_bonus
    )
    return round(score, 6)


def reject_reasons(report: dict[str, Any]) -> list[str]:
    metrics = report["metrics"]
    reasons = []
    if metrics.get("maskPixels", 0) <= 0:
        reasons.append("empty_mask")
    if (metrics.get("eyeOpeningOverlapRatio") or 0.0) > 0.03:
        reasons.append("eye_opening_overlap")
    if (metrics.get("lidFillHeightRatio") or 0.0) > 0.18:
        reasons.append("full_lid_block_risk")
    if (metrics.get("lowerLidCoverageRatio") or 0.0) > 0.02:
        reasons.append("lower_lid_ring_risk")
    if metrics.get("componentCount") != 2:
        reasons.append("component_count_not_two")
    if metrics.get("leftRight", {}).get("smallLargeRatio", 0.0) < 0.78:
        reasons.append("left_right_imbalance")
    if metrics.get("emptySidePenalty"):
        reasons.append("missing_one_eye")
    if report["adjustment"].get("innerStart", 0.0) < 0.08:
        reasons.append("inner_corner_overload_risk")
    return reasons


def review_shape_key(item: dict[str, Any]) -> tuple[Any, ...]:
    axes = item["adjustment"]
    return (
        item["familyKey"],
        axes.get("innerStart"),
        axes.get("lineThickness"),
        axes.get("outerCornerFill"),
        axes.get("tailLength"),
        axes.get("tailAngle"),
        axes.get("tailLift"),
        axes.get("taper"),
        axes.get("softness"),
    )


def diverse_review_set(candidates: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_shapes: set[tuple[Any, ...]] = set()
    by_family = {family: [item for item in candidates if item["familyKey"] == family] for family in FAMILY_COUNTS}

    def add_item(item: dict[str, Any]) -> bool:
        shape = review_shape_key(item)
        if item["candidateId"] in seen_ids or shape in seen_shapes:
            return False
        selected.append(item)
        seen_ids.add(item["candidateId"])
        seen_shapes.add(shape)
        return True

    # First guarantee broad family coverage.
    for family in FAMILY_COUNTS:
        for item in by_family.get(family, []):
            if add_item(item):
                break
        if len(selected) >= limit:
            return selected

    # Then fill round-robin so one high-scoring family cannot dominate the review sheet.
    family_offsets = {family: 0 for family in FAMILY_COUNTS}
    while len(selected) < limit:
        changed = False
        for family in FAMILY_COUNTS:
            items = by_family.get(family, [])
            start = family_offsets[family]
            for idx in range(start, len(items)):
                family_offsets[family] = idx + 1
                if add_item(items[idx]):
                    changed = True
                    break
            if len(selected) >= limit:
                break
        if not changed:
            break

    # Last resort: fill by score even if shape coverage is exhausted.
    for item in candidates:
        if len(selected) >= limit:
            break
        if item["candidateId"] not in seen_ids:
            selected.append(item)
            seen_ids.add(item["candidateId"])
    return selected


def write_manifest(output_root: Path, args: argparse.Namespace, specs: list[dict[str, Any]]) -> None:
    write_json(
        output_root / "input_manifest.json",
        {
            "schemaVersion": "e7-eyeliner-anchor-to-band-input-manifest-v0",
            "createdAt": utc_now(),
            "status": "input_frozen",
            "capturePair": str(args.capture_pair),
            "frame": str(args.capture_pair / "frame.png"),
            "mediapipeLandmarks": str(args.capture_pair / "mediapipe_face_landmarks.json"),
            "arfaceExport": str(args.capture_pair / "arface_export.json"),
            "bestReference": {
                "path": str(BEST_REFERENCE_PATH),
                "usage": "shape_taxonomy_only",
                "committedAsAsset": False,
                "runtimeAssetUsage": "forbidden",
                "families": ["cat", "puppy", "sexy", "winged", "colored", "doll"],
            },
            "candidateCountTarget": len(specs),
            "familyCounts": {family: sum(1 for spec in specs if spec["family"] == family) for family in FAMILY_COUNTS},
            "privacy": {
                "localOnly": True,
                "offDeviceUpload": False,
                "externalReferenceCopied": False,
                "longTermRawCameraStorageAdded": False,
            },
        },
    )


def copy_asset(src: Path, dest_dir: Path, name: str) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copyfile(src, dest)
    return f"assets/{name}"


def copy_artifact(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest_dir / src.name)


def write_report(
    report_dir: Path,
    experiment_root: Path,
    assets: dict[str, str],
    scorecard: dict[str, Any],
    shortlist: dict[str, Any],
) -> None:
    top = shortlist["topCandidates"][:12]
    family_counts = scorecard["familyCounts"]
    generated = scorecard["candidateCount"]
    rejected = scorecard["rejectedCandidateCount"]
    accepted = scorecard["acceptedCandidateCount"]
    top_table = "\n".join(
        [
            "| 후보 ID | Family | Score | Reject | 핵심 파라미터 |",
            "| --- | --- | ---: | --- | --- |",
            *[
                (
                    f"| `{item['candidateId']}` | {item['familyKey']} | {item['selectionScore']:.3f} | "
                    f"{', '.join(item['rejectReasons']) if item['rejectReasons'] else 'pass'} | "
                    f"inner={item['adjustment']['innerStart']}, thick={item['adjustment']['lineThickness']}, "
                    f"tail={item['adjustment']['tailLength']}, angle={item['adjustment']['tailAngle']} |"
                )
                for item in top
            ],
        ]
    )
    family_rows = "\n".join(f"| {family} | {count} |" for family, count in family_counts.items())
    report = f"""# E7 아이라인 Anchor-to-Band 대량 샘플 실험 보고서

상태: `pending_user_visual_pick`  
판정: buildless/local-only 샘플 생성 완료. iPhone runtime Green 또는 product-quality-ready 판정 아님.

## 1. 한 줄 결론

MediaPipe upper eyelid anchor를 기준으로 아이라인 band 후보 **{generated}개**를 생성했다. 자동 필터 기준 pass는 **{accepted}개**, reject sheet로 보낸 후보는 **{rejected}개**다. 지금 단계의 목표는 자동 선택이 아니라, 사용자가 contact sheet에서 후보 ID를 고르는 것이다.

## 2. 왜 이 실험을 했나

직전 실험에서 `mp-upper-balanced-v0`는 가장 깔끔한 기준선으로 확인됐고, 여성 리뷰는 눈꼬리까지 채우는 wing 계열을 선호했다. 이번 실험은 그 결론을 이어서, 기준선을 그대로 칠하는 대신 두께, 눈꼬리 채움, tail 길이, angle, taper, softness를 바꾼 실제 아이라인 band 후보를 대량으로 만든 것이다.

외부 레퍼런스 이미지는 shape taxonomy로만 사용했다. repo asset, runtime texture, 학습 데이터로 복사하지 않았다.

## 3. 입력

| 항목 | 값 |
| --- | --- |
| Capture pair | `pair_face_20260627T091334Z_06` |
| Frame | `evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png` |
| Landmark | `mediapipe_face_landmarks.json` |
| ARFace export | `arface_export.json` |
| Best reference usage | `Cat / Puppy / Sexy / Winged / Colored / Doll` shape taxonomy only |

## 4. Geometry 기준

<figure>
  <img src="{assets['geometry']}" width="760" alt="MediaPipe upper eyelid anchor">
  <figcaption>그림 1. 초록색이 MediaPipe upper eyelid anchor다. 이번 후보들은 이 선을 기준으로 두께와 눈꼬리 band를 확장했다.</figcaption>
</figure>

## 5. 전체 Top 후보

<figure>
  <img src="{assets['top36']}" width="980" alt="Top 36 eyeliner anchor to band candidates">
  <figcaption>그림 2. 사용자가 고르기 좋도록 family와 shape를 섞은 review 후보 36개 eye crop이다. score는 정렬 보조일 뿐이고 최종 선택은 사람이 한다.</figcaption>
</figure>

<figure>
  <img src="{assets['leftTop36']}" width="980" alt="Left eye top 36 eyeliner candidates">
  <figcaption>그림 2-1. 왼쪽 눈만 확대한 review 후보 36개다. wide crop에서 잘 안 보이는 tail 두께와 눈꼬리 채움 차이를 여기서 본다.</figcaption>
</figure>

<figure>
  <img src="{assets['rightTop36']}" width="980" alt="Right eye top 36 eyeliner candidates">
  <figcaption>그림 2-2. 오른쪽 눈만 확대한 review 후보 36개다. 좌우 대칭과 한쪽 눈에서만 어색한 후보를 확인한다.</figcaption>
</figure>

## 6. Family별 후보

각 family는 사용자가 지정한 최고 레퍼런스의 style 이름을 shape family로만 사용했다.

| Family | 후보 수 |
| --- | ---: |
{family_rows}

<figure>
  <img src="{assets['cat']}" width="980" alt="Cat eyeliner candidates">
  <figcaption>그림 3. Cat: sharp, lifted, outer-focused.</figcaption>
</figure>

<figure>
  <img src="{assets['puppy']}" width="980" alt="Puppy eyeliner candidates">
  <figcaption>그림 4. Puppy: soft, rounded, slightly lowered.</figcaption>
</figure>

<figure>
  <img src="{assets['sexy']}" width="980" alt="Sexy eyeliner candidates">
  <figcaption>그림 5. Sexy: longer, smoky, outer third emphasized.</figcaption>
</figure>

<figure>
  <img src="{assets['winged']}" width="980" alt="Winged eyeliner candidates">
  <figcaption>그림 6. Winged: clean default wing 후보군. 기본 preset이 여기서 나올 가능성이 높다.</figcaption>
</figure>

<figure>
  <img src="{assets['colored']}" width="980" alt="Colored eyeliner candidates">
  <figcaption>그림 7. Colored: 색 자체보다 soft wing shape를 보기 위한 후보군이다.</figcaption>
</figure>

<figure>
  <img src="{assets['doll']}" width="980" alt="Doll eyeliner candidates">
  <figcaption>그림 8. Doll: rounder, shorter, softer 후보군.</figcaption>
</figure>

<figure>
  <img src="{assets['safety']}" width="980" alt="Balanced reference and tail-only safe candidates">
  <figcaption>그림 9. Balanced reference와 Tail-only safe. 기본 후보가 과하면 여기서 fallback을 고른다.</figcaption>
</figure>

## 7. Reject 후보

<figure>
  <img src="{assets['rejected']}" width="980" alt="Rejected eyeliner candidates">
  <figcaption>그림 10. 자동 reject sheet. eye opening 침범, component 불안정, 과한 lid fill risk 등을 확인하기 위한 참고용이다.</figcaption>
</figure>

## 8. UV round-trip Top 12

<figure>
  <img src="{assets['uv12']}" width="980" alt="UV round trip top eyeliner candidates">
  <figcaption>그림 11. 상위 12개 후보의 ARFace UV round-trip sanity check. 얇은 선은 IoU가 낮게 나올 수 있으므로 깨짐/위치 이탈 여부를 위주로 본다.</figcaption>
</figure>

## 9. 후보 고르는 법

아래처럼 candidate ID로 골라주면 바로 앱 구현 기본 preset으로 승격할 수 있다.

```txt
1순위: winged-i18-t58-o16-l14-a18-s28-v001
2순위: cat-i22-t65-o22-l20-a22-s30-v009
싫은 방향: sexy는 너무 진함, puppy는 꼬리가 내려감
수정 요청: 1순위에서 꼬리 10% 짧게, 두께 살짝 얇게
```

Review 후보 중 상위 12개:

{top_table}

## 10. 앱 구현 handoff

이번 산출물은 `selected_policy_pending_user.json` 상태다. 사용자가 후보를 고르면:

```txt
selected_policy_pending_user.json -> selected_policy.json
chosen candidate axes -> app default preset
nearby variants 12개 추가 생성 여부 결정
RN/Unity 구현으로 진입
```

현재 추천은 자동으로 확정하지 않는다. 다만 product 방향상 `winged` 또는 `cat` family에서 기본값이 나올 가능성이 높고, 너무 과하면 `balanced_reference` 또는 `tail_only_safe`를 fallback으로 둔다.

## 11. 산출물 위치

| 항목 | 위치 |
| --- | --- |
| 실험 root | `{experiment_root}` |
| candidate_grid | `{experiment_root / 'candidate_grid.json'}` |
| scorecard | `{experiment_root / 'scorecard.json'}` |
| shortlist | `{experiment_root / 'shortlist.json'}` |
| selected pending | `{experiment_root / 'selected_policy_pending_user.json'}` |
| adjustment axes | `{experiment_root / 'adjustment_axes_candidates.json'}` |
| app handoff | `{experiment_root / 'app_handoff_notes.md'}` |
| report artifact mirror | `{report_dir / 'artifacts'}` |

## 12. 남은 한계

- static buildless frame 기준이다.
- blink/yaw/squint 안정성은 iPhone AR에서 따로 봐야 한다.
- UV round-trip은 sanity check이며 제품 품질 증명이 아니다.
- 사용자의 visual pick이 끝나야 앱 default preset이 확정된다.
"""
    report_dir.mkdir(parents=True, exist_ok=True)
    write_text(report_dir / "README.md", report)


def main() -> int:
    args = parse_args()
    output_root = args.output_root or Path("evidence/e7-eyeliner-anchor-to-band-experiment") / f"experiment-{timestamp()}"
    frame_path = args.capture_pair / "frame.png"
    mediapipe_path = args.capture_pair / "mediapipe_face_landmarks.json"
    arface_path = args.capture_pair / "arface_export.json"

    frame = Image.open(frame_path).convert("RGB")
    size = frame.size
    mediapipe = load_mediapipe(mediapipe_path)
    arface_export = load_json(arface_path)
    eyes = build_eye_geometry(mediapipe)
    opening = eye_opening_mask(size, eyes)
    opening_safety = erode(opening, 5)
    specs = stratified_specs(args.target_count)

    for subdir in ["geometry", "candidates", "uv_projection", "contact_sheets", "assets"]:
        (output_root / subdir).mkdir(parents=True, exist_ok=True)

    write_manifest(output_root, args, specs)
    write_json(
        output_root / "candidate_grid.json",
        {
            "schemaVersion": "e7-eyeliner-anchor-to-band-candidate-grid-v0",
            "createdAt": utc_now(),
            "status": "generated_grid",
            "candidateCount": len(specs),
            "families": list(FAMILY_COUNTS.keys()),
            "sourceReferenceUsage": "shape_taxonomy_only",
            "candidates": specs,
        },
    )

    all_eye_points = [point for eye in eyes for point in eye.eye_contour]
    both_eye_bbox = bbox_for_points(all_eye_points, size, 110)
    left_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "left"), size, 78)
    right_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "right"), size, 78)
    geometry_path = output_root / "geometry" / "eyelid_landmark_overlay.png"
    geometry_crop = output_root / "geometry" / "eyelid_landmark_eye_crop.png"
    draw_geometry_overlay(frame, eyes, geometry_path, show_opening_fill=False)
    crop_image(geometry_path, both_eye_bbox, geometry_crop)

    reports: list[dict[str, Any]] = []
    family_sheet_inputs: dict[str, list[tuple[str, Path]]] = {family: [] for family in FAMILY_COUNTS}

    for spec in specs:
        candidate = build_candidate_from_spec(size, frame, eyes, spec, opening_safety)
        family = spec["family"]
        candidate_dir = output_root / "candidates" / family
        candidate_dir.mkdir(parents=True, exist_ok=True)
        mask_path = candidate_dir / f"{candidate.candidate_id}.mask.png"
        alpha_path = candidate_dir / f"{candidate.candidate_id}.alpha.png"
        overlay_path = candidate_dir / f"{candidate.candidate_id}.overlay_eye_crop.png"
        eye_crop_path = overlay_path
        left_crop_path = candidate_dir / f"{candidate.candidate_id}.left_eye_crop.png"
        right_crop_path = candidate_dir / f"{candidate.candidate_id}.right_eye_crop.png"
        trace_path = candidate_dir / f"{candidate.candidate_id}.trace.json"

        mask_to_image(candidate.mask).save(mask_path)
        alpha_to_image(candidate.alpha).save(alpha_path)
        overlay = cosmetic_overlay(
            frame,
            candidate.alpha,
            FAMILY_COLORS[family],
            float(candidate.adjustment.get("previewOpacity", 0.65)),
        )
        overlay.crop(both_eye_bbox).save(eye_crop_path)
        overlay.crop(left_bbox).save(left_crop_path)
        overlay.crop(right_bbox).save(right_crop_path)
        write_json(trace_path, candidate.trace)

        base_metrics = candidate_metrics(candidate, eyes, opening_safety, {"status": "not_computed_initial_rank"})
        metrics = enrich_metrics(base_metrics, candidate, spec, eyes, size, opening_safety)
        report = {
            "candidateId": candidate.candidate_id,
            "candidateIndex": spec["candidateIndex"],
            "familyKey": family,
            "policy": candidate.policy,
            "family": candidate.family,
            "styleTaxonomy": spec["style"],
            "sourceSignals": candidate.source_signals,
            "adjustment": candidate.adjustment,
            "warnings": candidate.warnings,
            "metrics": metrics,
            "paths": {
                "mask": str(mask_path),
                "alpha": str(alpha_path),
                "overlay": str(overlay_path),
                "eyeCrop": str(eye_crop_path),
                "leftEyeCrop": str(left_crop_path),
                "rightEyeCrop": str(right_crop_path),
                "trace": str(trace_path),
            },
        }
        report["rejectReasons"] = reject_reasons(report)
        report["selectionScore"] = score_candidate(report)
        reports.append(report)
        label = (
            f"{spec['candidateIndex']:03d} {family} "
            f"i{int(spec['innerStart'] * 100)} t{spec['lineThickness']:.1f} "
            f"l{spec['tailLength']:.2f} a{int(spec['tailAngle'])}"
        )
        family_sheet_inputs[family].append((label, eye_crop_path))

    ranked = sorted(reports, key=lambda item: item["selectionScore"], reverse=True)
    accepted = [item for item in ranked if not item["rejectReasons"]]
    rejected = [item for item in ranked if item["rejectReasons"]]
    review_candidates = diverse_review_set(accepted if accepted else ranked, 36)
    top_for_uv = review_candidates[:12] if len(review_candidates) >= 12 else ranked[:12]

    uv_sheet_inputs: list[tuple[str, Path]] = []
    for item in top_for_uv:
        candidate_mask = np.asarray(Image.open(item["paths"]["mask"]).convert("L")) > 0
        uv_path = output_root / "uv_projection" / f"{item['candidateId']}.uv_probability.png"
        round_trip_path = output_root / "uv_projection" / f"{item['candidateId']}.round_trip_overlay.png"
        round_trip_crop_path = output_root / "uv_projection" / f"{item['candidateId']}.round_trip_eye_crop.png"
        probability = back_project_mask(candidate_mask, arface_export, args.uv_resolution, 1)
        predicted = render_atlas_to_screen(probability, arface_export, size, 0.10, 1)
        alpha_to_image(probability).save(uv_path)
        round_trip_overlay(frame, candidate_mask, predicted).save(round_trip_path)
        crop_image(round_trip_path, both_eye_bbox, round_trip_crop_path)
        uv_metrics = comparison_metrics(predicted, candidate_mask)
        item["metrics"]["uvRoundTrip"] = uv_metrics
        item["paths"]["uvProbability"] = str(uv_path)
        item["paths"]["roundTripOverlay"] = str(round_trip_path)
        item["paths"]["roundTripEyeCrop"] = str(round_trip_crop_path)
        uv_sheet_inputs.append((f"{item['candidateIndex']:03d} {item['familyKey']}", round_trip_crop_path))

    # Re-rank after UV metrics are attached to top candidates. UV is still a minor review aid.
    ranked = sorted(reports, key=lambda item: item["selectionScore"], reverse=True)
    accepted = [item for item in ranked if not item["rejectReasons"]]
    rejected = [item for item in ranked if item["rejectReasons"]]
    review_candidates = diverse_review_set(accepted if accepted else ranked, 36)

    contact_dir = output_root / "contact_sheets"
    save_contact_sheet([(f"{i['candidateIndex']:03d} {i['familyKey']} {i['selectionScore']:.2f}", Path(i["paths"]["eyeCrop"])) for i in review_candidates], contact_dir / "contact_sheet_top_36.png", 270, 4)
    save_contact_sheet([(f"{i['candidateIndex']:03d} {i['familyKey']} {i['selectionScore']:.2f}", Path(i["paths"]["leftEyeCrop"])) for i in review_candidates], contact_dir / "left_eye_contact_sheet_top_36.png", 300, 4)
    save_contact_sheet([(f"{i['candidateIndex']:03d} {i['familyKey']} {i['selectionScore']:.2f}", Path(i["paths"]["rightEyeCrop"])) for i in review_candidates], contact_dir / "right_eye_contact_sheet_top_36.png", 300, 4)
    save_contact_sheet([(f"{i['candidateIndex']:03d} {i['familyKey']} {i['selectionScore']:.2f}", Path(i["paths"]["eyeCrop"])) for i in ranked], contact_dir / "contact_sheet_all_small.png", 210, 6)
    save_contact_sheet([(f"{i['candidateIndex']:03d} {i['familyKey']} {','.join(i['rejectReasons'])[:20]}", Path(i["paths"]["eyeCrop"])) for i in rejected[:36]], contact_dir / "contact_sheet_rejected.png", 270, 4)
    save_contact_sheet(uv_sheet_inputs, contact_dir / "uv_round_trip_top_12.png", 300, 3)
    for family, inputs in family_sheet_inputs.items():
        cols = 4 if len(inputs) <= 24 else 5
        save_contact_sheet(inputs, contact_dir / f"contact_sheet_family_{family}.png", 250, cols)

    family_counts = {family: sum(1 for item in ranked if item["familyKey"] == family) for family in FAMILY_COUNTS}
    scorecard = {
        "schemaVersion": "e7-eyeliner-anchor-to-band-scorecard-v0",
        "createdAt": utc_now(),
        "status": "complete_buildless_local_only_pending_user_visual_pick",
        "decision": "pending_user_visual_pick",
        "capturePairId": mediapipe.get("capturePairId"),
        "sourceFrame": str(frame_path),
        "mediapipeLandmarks": str(mediapipe_path),
        "arfaceExport": str(arface_path),
        "candidateCount": len(ranked),
        "acceptedCandidateCount": len(accepted),
        "rejectedCandidateCount": len(rejected),
        "familyCounts": family_counts,
        "topCandidateIds": [item["candidateId"] for item in ranked[:12]],
        "reviewCandidateIds": [item["candidateId"] for item in review_candidates],
        "uvRoundTripComputedCandidateIds": [item["candidateId"] for item in top_for_uv],
        "rankedCandidates": ranked,
        "rejectRules": [
            "eyeOpeningOverlapRatio > 0.03",
            "lidFillHeightRatio > 0.18",
            "lowerLidCoverageRatio > 0.02",
            "componentCount != 2",
            "leftRight smallLargeRatio < 0.78",
            "missing one eye",
            "inner corner overload risk",
        ],
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "externalReferenceCopied": False,
            "longTermRawFrameStored": False,
            "derivedMasksOnly": True,
        },
        "productClaim": {
            "iphoneRuntimeGreen": False,
            "productQualityReady": False,
            "preXcodeBuildlessExperiment": True,
        },
    }
    shortlist = {
        "schemaVersion": "e7-eyeliner-anchor-to-band-shortlist-v0",
        "createdAt": utc_now(),
        "status": "pending_user_visual_pick",
        "selectionInstructionKo": "contact sheet에서 마음에 드는 candidateId를 1순위/2순위로 골라주세요.",
        "topCandidates": review_candidates,
        "autoScoreLeaders": ranked[:12],
        "familyLeaders": [
            next(item for item in ranked if item["familyKey"] == family)
            for family in FAMILY_COUNTS
            if any(item["familyKey"] == family for item in ranked)
        ],
    }
    selected_pending = {
        "schemaVersion": "e7-eyeliner-anchor-to-band-selected-policy-pending-v0",
        "createdAt": utc_now(),
        "decision": "pending_user_visual_pick",
        "recommendedReviewSet": [item["candidateId"] for item in review_candidates],
        "defaultRecommendationBeforeUserPick": review_candidates[0]["candidateId"],
        "candidateDisplaySet": [item["candidateId"] for item in review_candidates[:12]],
        "trackingAnchorCandidateId": "mp-upper-balanced-v0",
        "primaryTracker": "MediaPipe upper eyelid landmarks",
        "shapeModel": "anchor-to-band parametric eyeliner",
        "runtimeSubstrate": "ARFace UV",
        "bestReferenceUsage": "Cat/Puppy/Sexy/Winged/Colored/Doll taxonomy only",
        "requiresHumanReview": True,
        "humanReviewStatus": "pending",
        "iphoneEvidenceRequiredForGreen": True,
    }
    adjustment_axes = {
        "schemaVersion": "e7-eyeliner-anchor-to-band-adjustment-axes-candidates-v0",
        "createdAt": utc_now(),
        "status": "pending_user_visual_pick",
        "candidateAxes": [
            {
                "candidateId": item["candidateId"],
                "family": item["familyKey"],
                "selectionScore": item["selectionScore"],
                "rejectReasons": item["rejectReasons"],
                "axes": item["adjustment"],
            }
            for item in review_candidates
        ],
        "recommendedControlStyle": "slider_plus_quick_buttons",
        "sliders": [
            "lineHeight",
            "lineThickness",
            "innerStart",
            "outerCornerFill",
            "tailLength",
            "tailAngle",
            "tailLift",
            "taper",
            "softness",
            "leftRightBalance",
        ],
        "quickButtons": [
            "얇게",
            "조금 위로",
            "조금 아래로",
            "안쪽 비우기",
            "눈꼬리 채우기",
            "꼬리 짧게",
            "꼬리 올리기",
            "바깥쪽만",
            "좌우 맞추기",
            "왼쪽만 조정",
            "오른쪽만 조정",
        ],
    }

    write_json(output_root / "scorecard.json", scorecard)
    write_json(output_root / "shortlist.json", shortlist)
    write_json(output_root / "selected_policy_pending_user.json", selected_pending)
    write_json(output_root / "adjustment_axes_candidates.json", adjustment_axes)
    write_text(
        output_root / "app_handoff_notes.md",
        f"""# E7 Eyeliner Anchor-to-Band App Handoff

Status: `pending_user_visual_pick`

Generated candidates: `{len(ranked)}`
Accepted by automatic gates: `{len(accepted)}`
Rejected into review sheet: `{len(rejected)}`

Primary tracker:

- MediaPipe upper eyelid landmarks.

Shape model:

- Anchor-to-band parametric eyeliner.
- Family taxonomy: Cat, Puppy, Sexy, Winged, Colored, Doll, Balanced reference, Tail-only safe.
- Best reference image was used only as shape taxonomy. It was not copied as a repo/runtime asset.

Implementation after user pick:

1. Promote the selected candidate from `selected_policy_pending_user.json` to `selected_policy.json`.
2. Use the selected candidate axes as the default app preset.
3. Keep top nearby candidates as style alternatives.
4. Keep Tail-only safe as fallback.
5. Keep lower-lid coverage off by default.

Do not claim product-quality-ready until iPhone runtime visual evidence exists.
""",
    )
    write_text(
        output_root / "summary.md",
        f"""# E7 Eyeliner Anchor-to-Band Mass Sample Summary

Status: `pending_user_visual_pick`

Generated candidates: `{len(ranked)}`

Accepted by automatic gates: `{len(accepted)}`

Rejected into review sheet: `{len(rejected)}`

Top candidate before user pick: `{ranked[0]['candidateId']}`

Report: `{args.doc_report / 'README.md'}`

No Xcode/iPhone build was run. No Green/product-quality-ready claim is made.
""",
    )

    report_artifacts = args.doc_report / "artifacts"
    for artifact_name in [
        "input_manifest.json",
        "candidate_grid.json",
        "scorecard.json",
        "shortlist.json",
        "selected_policy_pending_user.json",
        "adjustment_axes_candidates.json",
        "app_handoff_notes.md",
        "summary.md",
    ]:
        copy_artifact(output_root / artifact_name, report_artifacts)

    assets_dir = args.doc_report / "assets"
    assets = {
        "geometry": copy_asset(geometry_crop, assets_dir, "01-mediapipe-upper-eyelid-anchor.png"),
        "top36": copy_asset(contact_dir / "contact_sheet_top_36.png", assets_dir, "02-contact-sheet-top-36.png"),
        "leftTop36": copy_asset(contact_dir / "left_eye_contact_sheet_top_36.png", assets_dir, "02b-left-eye-top-36.png"),
        "rightTop36": copy_asset(contact_dir / "right_eye_contact_sheet_top_36.png", assets_dir, "02c-right-eye-top-36.png"),
        "cat": copy_asset(contact_dir / "contact_sheet_family_cat.png", assets_dir, "03-family-cat.png"),
        "puppy": copy_asset(contact_dir / "contact_sheet_family_puppy.png", assets_dir, "04-family-puppy.png"),
        "sexy": copy_asset(contact_dir / "contact_sheet_family_sexy.png", assets_dir, "05-family-sexy.png"),
        "winged": copy_asset(contact_dir / "contact_sheet_family_winged.png", assets_dir, "06-family-winged.png"),
        "colored": copy_asset(contact_dir / "contact_sheet_family_colored.png", assets_dir, "07-family-colored.png"),
        "doll": copy_asset(contact_dir / "contact_sheet_family_doll.png", assets_dir, "08-family-doll.png"),
        "safety": copy_asset(contact_dir / "contact_sheet_family_balanced_reference.png", assets_dir, "09-family-balanced-reference.png"),
        "tail_safe": copy_asset(contact_dir / "contact_sheet_family_tail_only_safe.png", assets_dir, "10-family-tail-only-safe.png"),
        "rejected": copy_asset(contact_dir / "contact_sheet_rejected.png", assets_dir, "11-contact-sheet-rejected.png"),
        "uv12": copy_asset(contact_dir / "uv_round_trip_top_12.png", assets_dir, "12-uv-round-trip-top-12.png"),
    }
    # Combine balanced and tail-only into one report section asset for quick review.
    save_contact_sheet(
        family_sheet_inputs["balanced_reference"] + family_sheet_inputs["tail_only_safe"],
        assets_dir / "09-family-balanced-and-tail-safe.png",
        260,
        4,
    )
    assets["safety"] = "assets/09-family-balanced-and-tail-safe.png"

    write_report(args.doc_report, output_root, assets, scorecard, shortlist)

    print(
        json.dumps(
            {
                "outputRoot": str(output_root),
                "report": str(args.doc_report / "README.md"),
                "status": "pending_user_visual_pick",
                "candidateCount": len(ranked),
                "acceptedCandidateCount": len(accepted),
                "rejectedCandidateCount": len(rejected),
                "topCandidateId": ranked[0]["candidateId"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
