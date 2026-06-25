#!/usr/bin/env python3
"""Audit an existing E7 M1 buildless lip package without promoting it.

The audit intentionally treats artifact existence as neutral. It classifies the
current files, records contradictions, and emits hard ready-gate failures before
any M2/runtime work can use the package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


KNOWN_FILES = (
    "m1_summary.json",
    "summary.json",
    "fusionSummary.json",
    "lip_reference_mask_meta.json",
    "lip_mesh_draft_meta.json",
    "lip_variants.json",
)
USER_ADJUSTMENT_KEYS = (
    "cornerReach",
    "upperLipTightness",
    "lowerLipTightness",
    "verticalOffset",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit an existing M1 lip package folder.")
    parser.add_argument("input_dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Folder where audit_report.json/md will be written.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def maybe_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def candidate_ready_contradictions(fusion: dict[str, Any]) -> list[str]:
    if fusion.get("phase2Status") == "ready":
        return []
    contradictions = []
    for candidate_id, candidate in fusion.get("candidateOutputs", {}).items():
        if candidate.get("status") == "ready_for_mask_derivation":
            contradictions.append(
                f"{candidate_id}:ready_for_mask_derivation_while_phase2_{fusion.get('phase2Status')}"
            )
    return contradictions


def classify_reference_meta(meta: dict[str, Any]) -> dict[str, Any]:
    if not meta:
        return {
            "classification": "missing",
            "readyUse": False,
            "reasons": ["lip_reference_mask_meta.json_missing"],
        }
    reasons = []
    if not meta.get("acceptedAsGold", False):
        reasons.append("acceptedAsGold_false")
    if meta.get("reviewStatus") == "needs_user_review_before_gold":
        reasons.append("needs_user_review_before_gold")
    has_polygon = bool(meta.get("polygonPoints") or meta.get("points"))
    has_generator = bool(meta.get("generatorCommand") or meta.get("sourceScript"))
    if not has_generator:
        reasons.append("missing_generator_command_or_source_script")
    classification = "manual-unreproducible"
    if has_polygon and not meta.get("acceptedAsGold", False):
        classification = "partial"
    if not has_polygon and not has_generator:
        classification = "manual-unreproducible"
    return {
        "classification": classification,
        "readyUse": False,
        "reasons": reasons,
        "hasPolygonPoints": has_polygon,
        "hasGeneratorProvenance": has_generator,
        "reviewedBy": meta.get("reviewedBy"),
    }


def classify_files(input_dir: Path) -> dict[str, Any]:
    m1 = maybe_json(input_dir / "m1_summary.json")
    uv = maybe_json(input_dir / "summary.json")
    fusion = maybe_json(input_dir / "fusionSummary.json")
    reference_meta = maybe_json(input_dir / "lip_reference_mask_meta.json")
    mesh_meta = maybe_json(input_dir / "lip_mesh_draft_meta.json")
    variants = maybe_json(input_dir / "lip_variants.json")

    files: dict[str, Any] = {}
    for name in KNOWN_FILES:
        path = input_dir / name
        files[name] = {
            "exists": path.exists(),
            "sha256": sha256_file(path) if path.exists() else None,
            "classification": "real" if path.exists() else "missing",
            "readyUse": False,
            "reasons": [],
        }

    if m1:
        files["m1_summary.json"]["classification"] = (
            "partial" if m1.get("m1Decision") != "ready" else "real"
        )
        files["m1_summary.json"]["reasons"] = [
            f"m1Decision={m1.get('m1Decision')}",
            f"acceptedAsGold={m1.get('referenceMask', {}).get('acceptedAsGold')}",
            f"reviewStatus={m1.get('referenceMask', {}).get('reviewStatus')}",
        ]

    if uv:
        files["summary.json"]["classification"] = (
            "invalid-for-ready" if uv.get("phase3ExecutionStatus") != "ready" else "real"
        )
        files["summary.json"]["reasons"] = [
            f"phase3ExecutionStatus={uv.get('phase3ExecutionStatus')}",
            "roundTripScore_is_same_frame_self_reconstruction_only",
        ]

    contradictions = candidate_ready_contradictions(fusion)
    if fusion:
        files["fusionSummary.json"]["classification"] = (
            "invalid-for-ready" if fusion.get("phase2Status") != "ready" else "real"
        )
        files["fusionSummary.json"]["reasons"] = [
            f"phase2Status={fusion.get('phase2Status')}",
            *contradictions,
        ]

    files["lip_reference_mask_meta.json"].update(classify_reference_meta(reference_meta))

    if mesh_meta:
        files["lip_mesh_draft_meta.json"]["classification"] = "invalid-for-ready"
        files["lip_mesh_draft_meta.json"]["reasons"] = [
            "mesh_draft_is_review_only_not_reference",
            m1.get("meshDraftReview", "mesh_draft_requires_visual_review"),
        ]

    if variants:
        variants_list = variants.get("variants", [])
        runtime_ready = [
            item.get("candidateId") for item in variants_list if item.get("runtimeReady") is True
        ]
        files["lip_variants.json"]["classification"] = "real" if not runtime_ready else "invalid-for-ready"
        files["lip_variants.json"]["readyUse"] = False
        files["lip_variants.json"]["reasons"] = [
            "runtimeReady_false_for_all_variants"
            if not runtime_ready
            else f"runtimeReady_true_unexpected:{runtime_ready}"
        ]

    return files


def ready_gate_failures(input_dir: Path, files: dict[str, Any]) -> list[str]:
    m1 = maybe_json(input_dir / "m1_summary.json")
    uv = maybe_json(input_dir / "summary.json")
    fusion = maybe_json(input_dir / "fusionSummary.json")
    reference_meta = maybe_json(input_dir / "lip_reference_mask_meta.json")

    failures = []
    if not reference_meta.get("acceptedAsGold", False):
        failures.append("acceptedAsGold_false")
    if fusion.get("phase2Status") != "ready":
        failures.append("phase2Status_not_ready")
    reference_signals = fusion.get("inputs", {}).get("referenceSignals", {})
    if not reference_signals.get("visionContourAvailable"):
        failures.append("AppleVision_required_not_available")
    if not (
        reference_signals.get("faceParsingSilver")
        or reference_signals.get("humanReviewedGold")
        or reference_signals.get("faceParsingRequiredAvailable")
    ):
        failures.append("faceParsing_required_not_available")
    readiness_warnings = set(fusion.get("readiness", {}).get("warnings", []))
    if not reference_signals.get("colorGradientComputed") or (
        "required_color_gradient_confidence_not_computed" in readiness_warnings
    ):
        failures.append("colorGradient_required_not_computed")
    if "required_user_adjustment_not_confirmed" in readiness_warnings or any(
        warning.startswith("user_adjustment_params_") for warning in readiness_warnings
    ):
        failures.append("userAdjustment_required_not_confirmed")
    user_adjustment = fusion.get("inputs", {}).get("userAdjustment", {})
    if user_adjustment.get("status") != "user_confirmed":
        failures.append("userAdjustment_required_not_confirmed")
    if user_adjustment.get("confirmedByUser") is not True:
        failures.append("userAdjustment_required_not_confirmed")
    params = user_adjustment.get("params", {})
    if not isinstance(params, dict) or any(key not in params for key in USER_ADJUSTMENT_KEYS):
        failures.append("userAdjustment_required_fields_missing")
    if user_adjustment.get("legacyKeysPresent") and (
        not isinstance(params, dict) or any(key not in params for key in USER_ADJUSTMENT_KEYS)
    ):
        failures.append("userAdjustment_legacy_only_not_accepted")
    if (
        "required_blendshape_snapshot_not_available" in readiness_warnings
        or not fusion.get("inputs", {}).get("blendshapeSnapshot")
    ):
        failures.append("blendshapeSnapshot_required_not_available")
    capture_set = fusion.get("inputs", {}).get("captureSet", {})
    if (
        "required_capture_not_accepted:pucker" in readiness_warnings
        or "missing_required_capture:pucker" in readiness_warnings
        or not any(item.get("acceptedForFusion") for item in capture_set.get("pucker", []))
    ):
        failures.append("pucker_required_not_accepted")
    if uv.get("phase3ExecutionStatus") != "ready":
        failures.append("phase3ExecutionStatus_not_ready")
    if reference_meta and not files["lip_reference_mask_meta.json"].get("readyUse", False):
        failures.append("reference_mask_not_ready_for_gold")
    warnings = set(uv.get("warnings", []))
    if "inner_mouth_exclusion_contract_only" in warnings:
        failures.append("innerMouthExclusion_contract_only")
    if "corner_falloff_contract_only" in warnings:
        failures.append("cornerFalloff_contract_only")
    if "upper_lower_split_contract_only" in warnings:
        failures.append("upperLowerSplit_contract_only")
    if "coordinate_space_validation_pending" in warnings or not uv.get("coordinateSpaceAuditStatus"):
        failures.append("coordinateSpaceAuditStatus_not_passed")
    if "triangle_visibility_unavailable_front_most_rule_contract_only" in warnings:
        failures.append("triangle_visibility_front_most_rule_contract_only")
    if m1.get("roundTripScore"):
        failures.append("same_frame_roundTripScore_not_boundary_quality_proof")
    if not (input_dir / "held_out_eval_plan.json").exists():
        failures.append("held_out_eval_plan_missing")
    return sorted(set(failures))


def build_report(input_dir: Path) -> dict[str, Any]:
    files = classify_files(input_dir)
    failures = ready_gate_failures(input_dir, files)
    fusion = maybe_json(input_dir / "fusionSummary.json")
    return {
        "schemaVersion": "e7-lip-m1-audit-report-v1",
        "createdAtUtc": utc_now(),
        "inputDir": str(input_dir),
        "auditVerdict": "partial_not_ready" if failures else "ready_candidate_needs_manual_review",
        "artifactExistenceCountsAsSuccess": False,
        "sameFrameRoundTripCountsAsBoundaryQuality": False,
        "files": files,
        "contradictions": candidate_ready_contradictions(fusion),
        "readyGateFailures": failures,
        "recommendedNextStep": (
            "run M1 repair with explicit reproducible reference mask, then keep decision partial until user review and missing gates are resolved"
            if failures
            else "record manual review and held-out/eval evidence before any M2 gate"
        ),
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# E7 Lip M1 Audit Report",
        "",
        f"- Verdict: `{report['auditVerdict']}`",
        f"- Input: `{report['inputDir']}`",
        "- Artifact existence counts as success: `false`",
        "- Same-frame round-trip counts as boundary quality: `false`",
        "",
        "## File Classification",
        "",
        "| File | Classification | Ready use | Reasons |",
        "| --- | --- | --- | --- |",
    ]
    for name, info in report["files"].items():
        reasons = ", ".join(str(item) for item in info.get("reasons", [])) or "-"
        lines.append(
            f"| `{name}` | `{info.get('classification')}` | `{str(info.get('readyUse')).lower()}` | {reasons} |"
        )
    lines.extend(["", "## Ready Gate Failures", ""])
    if report["readyGateFailures"]:
        lines.extend(f"- `{failure}`" for failure in report["readyGateFailures"])
    else:
        lines.append("- None.")
    if report["contradictions"]:
        lines.extend(["", "## Contradictions", ""])
        lines.extend(f"- `{item}`" for item in report["contradictions"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        raise FileNotFoundError(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir)
    write_json(output_dir / "audit_report.json", report)
    write_markdown(output_dir / "audit_report.md", report)
    print(json.dumps({"auditReport": str(output_dir / "audit_report.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
