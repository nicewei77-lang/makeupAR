#!/usr/bin/env python3
"""Buildless contract stub for E7 lip Boundary Fusion.

The script reads a local lip-calib-* package and emits a fusionSummary contract.
It does not process images, run face parsing, call Core ML, upload data, or
produce runtime-ready masks. Its job is to make Phase 2 input readiness and
Phase 3 handoff shape explicit before the UV projection pass.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_STEPS = ("neutral", "open_close", "smile", "yaw", "pucker")
REQUIRED_ARFACE_FIELDS = ("screenVertices", "uvs", "indices", "clipW")
CANDIDATE_IDS = ("lip-tight-auto-v0", "lip-tight-user-v0", "lip-safe-v0")
FUSION_PRIORITY = (
    "human_reviewed_gold_mask",
    "face_parsing_lip_labels_silver_until_reviewed",
    "apple_vision_lip_contour",
    "arface_topology_projection",
    "color_gradient_confidence_required_confidence_only",
    "user_adjustment_params",
    "failure_mode_type_preset",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a buildless E7 lip Boundary Fusion summary contract."
    )
    parser.add_argument(
        "package",
        type=Path,
        help="Path to a lip-calib-* JSON file or directory containing one.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for fusionSummary.json/md. Defaults to stdout only.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_package_file(package_path: Path) -> Path:
    if package_path.is_file():
        return package_path
    if not package_path.is_dir():
        raise FileNotFoundError(package_path)

    candidates = [
        package_path / "package.json",
        package_path / "calibration.json",
        package_path / "lip-calib.json",
    ]
    candidates.extend(sorted(package_path.glob("lip-calib*.json")))
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(f"No lip-calib JSON package found in {package_path}")


def normalize_step(capture: dict[str, Any]) -> str:
    raw = str(capture.get("step", "")).strip().lower().replace("-", "_")
    capture_id = str(capture.get("capturePairId", "")).strip().lower()
    if raw in {"openclose", "open_close"}:
        return "open_close"
    if raw.startswith("yaw") or "lip_yaw" in capture_id:
        return "yaw"
    if raw in {"neutral", "smile", "pucker"}:
        return raw
    return raw or "unknown"


def is_available(value: Any) -> bool:
    if isinstance(value, str):
        return value == "available"
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    return value is not None


def arface_status(capture: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    arface = capture.get("arFace", {})
    fields: dict[str, str] = {}
    rejected: list[str] = []
    for field in REQUIRED_ARFACE_FIELDS:
        status = "available" if is_available(arface.get(field)) else "missing"
        fields[field] = status
        if status != "available":
            rejected.append(f"missing_arface_{field}")
    mesh_counts = arface.get("meshCounts") or capture.get("tracking", {}).get("meshCounts")
    if isinstance(mesh_counts, dict):
        fields["meshCounts"] = "available"
    else:
        fields["meshCounts"] = "missing"
        rejected.append("missing_mesh_counts")
    return fields, rejected


def tracking_status(capture: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    tracking = capture.get("tracking", {})
    state = tracking.get("state")
    face_count = tracking.get("faceCount")
    rejected: list[str] = []
    if state != "Tracking":
        rejected.append(f"tracking_not_ready:{state or 'missing'}")
    if face_count != 1:
        rejected.append(f"face_count_not_one:{face_count!r}")
    return {"state": state, "faceCount": face_count}, rejected


def summarize_capture_set(package: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    captures_by_step: dict[str, list[dict[str, Any]]] = {}
    rejected: list[str] = []
    warnings: list[str] = []

    for capture in package.get("captureSet", []):
        step = normalize_step(capture)
        captures_by_step.setdefault(step, []).append(capture)

    summary: dict[str, Any] = {}
    for step in REQUIRED_STEPS:
        captures = captures_by_step.get(step, [])
        accepted = []
        for capture in captures:
            capture_status = capture.get("captureStatus", "captured")
            arface, arface_rejected = arface_status(capture)
            tracking, tracking_rejected = tracking_status(capture)
            clean_frame = capture.get("cleanFrame", {})
            long_term_stored = bool(clean_frame.get("longTermStored"))
            capture_rejected = list(arface_rejected) + list(tracking_rejected)
            if long_term_stored:
                capture_rejected.append("raw_frame_long_term_stored")
            accepted.append(
                {
                    "capturePairId": capture.get("capturePairId"),
                    "captureStatus": capture_status,
                    "arFace": arface,
                    "tracking": tracking,
                    "acceptedForFusion": capture_status == "captured" and not capture_rejected,
                    "rejectedSignalReasons": capture_rejected,
                }
            )
        if step in REQUIRED_STEPS and not captures:
            rejected.append(f"missing_required_capture:{step}")
        if step in REQUIRED_STEPS and captures and not any(item["acceptedForFusion"] for item in accepted):
            warnings.append(f"required_capture_not_accepted:{step}")
        summary[step] = accepted
    return summary, rejected, warnings


def summarize_reference_signals(package: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    signals = {
        "humanReviewedGold": 0,
        "faceParsingSilver": 0,
        "faceParsingRequiredAvailable": 0,
        "faceParsingRequiredMissing": 0,
        "manualReferenceMask": 0,
        "meshStructuralDraftReference": 0,
        "visionContourAvailable": 0,
        "visionContourRequiredMissing": 0,
        "visionContourLowConfidence": 0,
        "visionContours": [],
        "colorGradientComputed": 0,
        "colorGradientRequiredMissing": 0,
        "colorGradientWarnings": [],
        "screenLipReferenceMask": None,
    }
    rejected: list[str] = []
    warnings: list[str] = []

    reference_mask = package.get("screenLipReferenceMask")
    if isinstance(reference_mask, dict):
        signals["screenLipReferenceMask"] = {
            "status": reference_mask.get("status"),
            "path": reference_mask.get("maskPath"),
            "capturePairId": reference_mask.get("capturePairId"),
            "source": reference_mask.get("source"),
            "reviewStatus": reference_mask.get("reviewStatus"),
            "acceptedAsGold": bool(reference_mask.get("acceptedAsGold")),
            "acceptedSignalIds": reference_mask.get("acceptedSignalIds", []),
        }
        source = str(reference_mask.get("source", ""))
        status = str(reference_mask.get("status", ""))
        if status in {"available", "reference_ready", "accepted_reference"}:
            if "mesh" in source or "lip_ring" in source:
                signals["meshStructuralDraftReference"] += 1
            else:
                signals["manualReferenceMask"] += 1
            if not reference_mask.get("acceptedAsGold"):
                warnings.append("screen_lip_reference_mask_not_human_reviewed_gold")

    for capture in package.get("captureSet", []):
        capture_id = capture.get("capturePairId", "unknown_capture")
        face_parsing_status = capture.get("faceParsing", {}).get("status")
        if face_parsing_status == "human_reviewed_gold":
            signals["humanReviewedGold"] += 1
        elif face_parsing_status == "silver":
            signals["faceParsingSilver"] += 1
        if face_parsing_status in {"human_reviewed_gold", "silver"}:
            signals["faceParsingRequiredAvailable"] += 1
        else:
            signals["faceParsingRequiredMissing"] += 1

        vision = capture.get("visionLipContour", {})
        vision_status = vision.get("status")
        if vision_status == "available":
            signals["visionContourAvailable"] += 1
            signals["visionContours"].append(
                {
                    "capturePairId": capture_id,
                    "source": vision.get("source"),
                    "confidence": vision.get("confidence"),
                    "coordinateSpace": vision.get("coordinateSpace"),
                    "contourJsonPath": vision.get("contourJsonPath"),
                    "overlayPath": vision.get("overlayPath"),
                    "outerLipPointCount": vision.get("outerLipPointCount", 0),
                    "innerLipPointCount": vision.get("innerLipPointCount", 0),
                    "outerLipImageBounds": vision.get("outerLipImageBounds"),
                    "innerLipImageBounds": vision.get("innerLipImageBounds"),
                    "runtimePrimaryTracker": bool(vision.get("runtimePrimaryTracker", False)),
                    "recommendedUse": "tighten_or_audit_outer_lip_boundary_against_arface_uv_mask",
                }
            )
            confidence = vision.get("confidence")
            if isinstance(confidence, (int, float)) and confidence < 0.45:
                signals["visionContourAvailable"] -= 1
                signals["visionContourLowConfidence"] += 1
                rejected.append(f"{capture_id}:vision_contour_low_confidence")
        elif vision_status == "low_confidence":
            signals["visionContourLowConfidence"] += 1
            rejected.append(f"{capture_id}:vision_contour_low_confidence")
            signals["visionContourRequiredMissing"] += 1
        else:
            signals["visionContourRequiredMissing"] += 1

        color = capture.get("colorGradientConfidence", {})
        if color.get("status") == "computed":
            signals["colorGradientComputed"] += 1
            for key in ("lowContrastWarning", "shadowWarning", "specularWarning"):
                if color.get(key):
                    warning = f"{capture_id}:{key}"
                    signals["colorGradientWarnings"].append(warning)
                    warnings.append(warning)
        else:
            signals["colorGradientRequiredMissing"] += 1

    if not (
        signals["humanReviewedGold"]
        or signals["faceParsingSilver"]
        or signals["manualReferenceMask"]
        or signals["meshStructuralDraftReference"]
        or signals["visionContourAvailable"]
    ):
        warnings.append("no_reference_signal_available_yet")
    if signals["visionContourAvailable"] == 0:
        warnings.append("required_apple_vision_lip_contour_not_available")
    if signals["faceParsingRequiredAvailable"] == 0:
        warnings.append("required_face_parsing_lip_labels_not_available")
    if signals["colorGradientComputed"] == 0:
        warnings.append("required_color_gradient_confidence_not_computed")
    return signals, rejected, warnings


def summarize_privacy(package: dict[str, Any]) -> tuple[dict[str, bool], list[str]]:
    privacy = package.get("privacy", {})
    expected = {
        "localOnly": True,
        "rawFrameStored": False,
        "longTermRawFrameStored": False,
        "offDeviceUpload": False,
        "backendUpload": False,
        "userProfileSync": False,
    }
    rejected = []
    observed = {}
    for key, expected_value in expected.items():
        observed[key] = bool(privacy.get(key))
        if observed[key] != expected_value:
            rejected.append(f"privacy_violation:{key}")
    return observed, rejected


def user_adjustment_status(package: dict[str, Any]) -> dict[str, Any]:
    correction = package.get("correction", {})
    params = correction.get("userAdjustmentParams")
    declared_status = correction.get("userAdjustmentStatus")
    if not isinstance(params, dict):
        return {
            "status": declared_status or "default_zero_assumed",
            "params": {
                "tightness": 0,
                "upperLowerBalance": 0,
                "cornerShrink": 0,
                "verticalOffset": 0,
            },
        }
    expected_keys = ("tightness", "upperLowerBalance", "cornerShrink", "verticalOffset")
    missing = [key for key in expected_keys if key not in params]
    if missing:
        status = "partial"
    else:
        status = declared_status or "available"
    return {"status": status, "params": params, "missing": missing}


def decide_candidates(
    blockers: list[str],
    warnings: list[str],
    reference_signals: dict[str, Any],
    user_adjustment: dict[str, Any],
) -> dict[str, Any]:
    has_reference = bool(
        reference_signals["humanReviewedGold"]
        or reference_signals["faceParsingSilver"]
        or reference_signals.get("manualReferenceMask")
        or reference_signals.get("meshStructuralDraftReference")
        or reference_signals["visionContourAvailable"]
    )
    blocking_warnings = list(warnings)
    if blockers:
        base_status = "blocked"
    elif has_reference and not blocking_warnings:
        base_status = "ready_for_mask_derivation"
    else:
        base_status = "partial_contract_only"

    auto_reasons = []
    if not has_reference:
        auto_reasons.append("needs_gold_silver_or_vision_reference")
    if blocking_warnings:
        auto_reasons.extend(f"phase2_not_ready:{warning}" for warning in blocking_warnings)
    if reference_signals["colorGradientWarnings"]:
        auto_reasons.append("color_gradient_warning_lowers_confidence")

    user_status = base_status
    user_reasons = list(auto_reasons)
    if user_adjustment["status"] != "user_confirmed":
        user_status = "partial_contract_only" if not blockers else "blocked"
        user_reasons.append(f"user_adjustment_status:{user_adjustment['status']}")

    safe_reasons = list(auto_reasons)
    if any("missing_required_capture:open_close" in item for item in blockers + warnings):
        safe_reasons.append("inner_mouth_seed_missing")

    return {
        "lip-tight-auto-v0": {
            "status": base_status,
            "primaryInputs": ["neutral", "smile", "yaw", "referenceSignals"],
            "rule": "tighten to accepted lip reference; reject color-only boundaries",
            "rejectedSignalReasons": auto_reasons,
        },
        "lip-tight-user-v0": {
            "status": user_status,
            "primaryInputs": ["lip-tight-auto-v0", "userAdjustmentParams"],
            "rule": "apply tightness, upper/lower balance, corner shrink, and vertical offset after auto fusion",
            "rejectedSignalReasons": user_reasons,
        },
        "lip-safe-v0": {
            "status": base_status,
            "primaryInputs": ["open_close", "innerMouthExclusion", "cornerFalloff"],
            "rule": "prefer spill prevention over recall; shrink teeth, inner mouth, and lower-face skin risk",
            "rejectedSignalReasons": safe_reasons,
        },
    }


def phase2_status(blockers: list[str], warnings: list[str]) -> str:
    if blockers:
        return "blocked"
    blocking_warnings = list(warnings)
    if blocking_warnings:
        return "partial"
    return "ready"


def build_summary(package_file: Path, package: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []

    if package.get("schemaVersion") != "e7-lip-boundary-calibration-v0":
        blockers.append("unsupported_schema_version")
    if package.get("region") != "lip":
        blockers.append("non_lip_region_not_in_scope")
    if not str(package.get("calibrationId", "")).startswith("lip-calib-"):
        blockers.append("calibration_id_must_start_with_lip-calib")

    capture_summary, capture_blockers, capture_warnings = summarize_capture_set(package)
    blockers.extend(capture_blockers)
    warnings.extend(capture_warnings)

    reference_signals, signal_rejections, signal_warnings = summarize_reference_signals(package)
    warnings.extend(signal_rejections)
    warnings.extend(signal_warnings)

    privacy, privacy_blockers = summarize_privacy(package)
    blockers.extend(privacy_blockers)

    user_adjustment = user_adjustment_status(package)
    if user_adjustment["status"] != "user_confirmed":
        warnings.append(f"user_adjustment_params_{user_adjustment['status']}")
        warnings.append("required_user_adjustment_not_confirmed")

    failure_mode = package.get("failureModeType") or package.get("failureMode")
    if not isinstance(failure_mode, dict) or failure_mode.get("status") not in {
        "classified",
        "available",
        "user_confirmed",
    }:
        warnings.append("required_failure_mode_type_not_classified")

    if not any(
        capture.get("blendshapeSnapshot", {}).get("status") == "available"
        for capture in package.get("captureSet", [])
    ):
        warnings.append("required_blendshape_snapshot_not_available")

    candidate_outputs = decide_candidates(blockers, warnings, reference_signals, user_adjustment)
    status = phase2_status(blockers, warnings)
    rejected_signal_reasons = sorted(set(blockers + warnings))

    return {
        "schemaVersion": "e7-lip-boundary-fusion-summary-v0",
        "fusionId": f"fusion-{package.get('calibrationId', 'lip-calib-unknown')}",
        "createdAtUtc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sourcePackage": str(package_file),
        "calibrationId": package.get("calibrationId"),
        "region": "lip",
        "phase2Status": status,
        "inputs": {
            "captureSet": capture_summary,
            "referenceSignals": reference_signals,
            "userAdjustment": user_adjustment,
            "privacy": privacy,
        },
        "fusionPolicy": {
            "priority": list(FUSION_PRIORITY),
            "colorGradientRule": "required_confidence_signal_never_wins_alone",
            "faceParsingRule": "offline_silver_until_human_reviewed",
            "requiredM1Signals": [
                "pucker",
                "appleVisionLipContour",
                "faceParsingLipLabels",
                "colorGradientConfidence",
                "userConfirmedAdjustment",
                "failureModeType",
                "blendshapeSnapshot",
            ],
            "runtimeRule": "no_live_face_parsing_or_core_ml_runtime",
        },
        "candidateOutputs": candidate_outputs,
        "readiness": {
            "status": status,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "deferredRequiredCaptures": sorted(
                reason.split(":", 1)[1]
                for reason in warnings + blockers
                if reason.startswith("missing_required_capture:")
                or reason.startswith("required_capture_not_accepted:")
            ),
            "artifactExistenceIsSuccess": False,
        },
        "phase3OutputContract": {
            "screenSpaceLipReferenceMask": {
                "status": (
                    "available_reference"
                    if reference_signals.get("manualReferenceMask")
                    or reference_signals.get("meshStructuralDraftReference")
                    or reference_signals.get("humanReviewedGold")
                    else ("ready_for_generation" if status == "ready" else status)
                ),
                "current": reference_signals.get("screenLipReferenceMask"),
                "requiredFields": ["maskPath", "capturePairId", "coordinateSpace", "acceptedSignalIds"],
            },
            "innerMouthExclusion": {
                "source": "open_close plus required faceParsing/vision, user review if ambiguous"
            },
            "cornerFalloff": {
                "source": "smile and yaw corner stretch/spill review"
            },
            "upperLowerSplit": {
                "source": "required faceParsing labels first, required Vision contour second, geometric split fallback only with low confidence"
            },
            "confidenceSummary": {
                "source": "per-capture signal confidence plus global phase2Status"
            },
            "rejectedSignalReasons": rejected_signal_reasons,
        },
        "limits": {
            "lipOnly": True,
            "cheekEyeExtensionSlotsOnly": True,
            "doesNotClaimE73Green": True,
            "doesNotStartE74E75E76": True,
            "doesNotStoreRawFramesLongTerm": True,
            "doesNotUpload": True,
        },
    }


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E7 Lip Boundary Fusion Summary",
        "",
        f"- Fusion id: `{summary['fusionId']}`",
        f"- Calibration id: `{summary.get('calibrationId')}`",
        f"- Phase 2 status: `{summary['phase2Status']}`",
        "- Scope: lip only; cheek/eye are extension slots only.",
        "- Runtime limits: no live face parsing/Core ML, no upload, no long-term raw frame storage.",
        "",
        "## Candidate Outputs",
        "",
        "| Candidate | Status | Rule |",
        "| --- | --- | --- |",
    ]
    for candidate_id in CANDIDATE_IDS:
        candidate = summary["candidateOutputs"][candidate_id]
        lines.append(
            f"| `{candidate_id}` | `{candidate['status']}` | {candidate['rule']} |"
        )
    lines.extend(
        [
            "",
            "## Phase 3 Handoff",
            "",
            "- screen-space lip reference mask",
            "- inner-mouth exclusion",
            "- corner falloff",
            "- upper/lower split",
            "- confidence summary",
            "- rejected-signal reasons",
            "",
            "## Rejected Or Deferred Signals",
            "",
        ]
    )
    reasons = summary["phase3OutputContract"]["rejectedSignalReasons"]
    if reasons:
        lines.extend(f"- `{reason}`" for reason in reasons)
    else:
        lines.append("- None.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    package_file = find_package_file(args.package.resolve())
    package = load_json(package_file)
    summary = build_summary(package_file, package)

    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = args.output_dir / "fusionSummary.json"
        md_path = args.output_dir / "fusionSummary.md"
        json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_summary_md(md_path, summary)
        print(json.dumps({"fusionSummary": str(json_path), "markdown": str(md_path)}, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
