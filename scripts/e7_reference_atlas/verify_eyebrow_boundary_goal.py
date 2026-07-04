#!/usr/bin/env python3
"""Verify the current eyebrow spline boundary approval preview contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUMMARY_GLOB = "evidence/e7-reference-atlas/eyebrow-boundary-goal-*/summary.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--summary",
        type=Path,
        help="Boundary-goal summary.json. Defaults to the newest generated summary.",
    )
    parser.add_argument(
        "--require-reference",
        action="store_true",
        help="Fail unless the optional user red-reference compare gate is present and passing.",
    )
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_summary(repo: Path, explicit_summary: Path | None) -> tuple[Path, dict[str, Any]]:
    if explicit_summary is not None:
        summary_path = explicit_summary if explicit_summary.is_absolute() else repo / explicit_summary
    else:
        summaries = sorted(
            repo.glob(SUMMARY_GLOB),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        require(bool(summaries), f"no eyebrow boundary goal summaries found: {SUMMARY_GLOB}")
        summary_path = summaries[0]

    require(summary_path.exists(), f"missing summary: {summary_path}")
    return summary_path, json.loads(summary_path.read_text(encoding="utf-8"))


def resolve_path(repo: Path, value: Any) -> Path:
    require(isinstance(value, str) and value, f"expected path string, got {value!r}")
    path = Path(value)
    return path if path.is_absolute() else repo / path


def require_existing_path(repo: Path, summary: dict[str, Any], key: str) -> Path:
    path = resolve_path(repo, summary.get(key))
    require(path.exists(), f"missing {key}: {path}")
    return path


def require_number_close(value: Any, expected: float, name: str, tolerance: float = 0.0001) -> None:
    require(isinstance(value, (int, float)), f"{name} must be numeric")
    require(abs(float(value) - expected) <= tolerance, f"{name} mismatch: {value} != {expected}")


def verify_reference_gate(
    repo: Path,
    summary: dict[str, Any],
    preview_gate: dict[str, Any],
    require_reference: bool,
) -> str:
    compare_gate = preview_gate.get("referenceCompareGate")
    require(isinstance(compare_gate, dict), "missing previewGate.referenceCompareGate")
    status = compare_gate.get("status")

    if require_reference:
        require(status == "pass", f"reference gate must pass, got {status!r}")
    else:
        require(
            status in {"pass", "check", "missing_optional_reference"},
            f"unexpected reference gate status: {status!r}",
        )

    if status in {"pass", "check"}:
        threshold = compare_gate.get("threshold")
        max_delta = compare_gate.get("maxDeltaNorm")
        require(isinstance(threshold, (int, float)), "reference threshold must be numeric")
        require(isinstance(max_delta, (int, float)), "reference maxDeltaNorm must be numeric")
        if require_reference:
            require(float(max_delta) <= float(threshold), "reference maxDeltaNorm exceeds threshold")

        reference_boundary = preview_gate.get("referenceBoundary")
        require(resolve_path(repo, reference_boundary).exists(), "reference boundary image missing")

        reference_compare = summary.get("referenceCompare")
        require(isinstance(reference_compare, dict), "missing referenceCompare details")
        reference_overlay = resolve_path(repo, reference_compare.get("path"))
        require(reference_overlay.exists(), f"reference compare overlay missing: {reference_overlay}")
        return f"{status} maxDelta={float(max_delta):.4f}"

    return "missing_optional_reference"


def verify(summary_path: Path, repo: Path, require_reference: bool) -> str:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    primary = require_existing_path(repo, summary, "primaryApprovalSheet")
    boundary = require_existing_path(repo, summary, "boundaryOnlySheet")
    require(primary == boundary, "primary approval sheet must be the boundary-only sheet")
    require_existing_path(repo, summary, "curveDebugSheet")

    preview_gate = summary.get("previewGate")
    require(isinstance(preview_gate, dict), "missing previewGate")
    require(preview_gate.get("status") == "line_only_first", "preview gate must be line_only_first")
    require(
        preview_gate.get("fillTextureBuildBlockedUntilBoundaryApproval") is True,
        "fill/texture/build must stay blocked until boundary approval",
    )
    reference_status = verify_reference_gate(repo, summary, preview_gate, require_reference)

    constants = summary.get("constants")
    require(isinstance(constants, dict), "missing constants")
    require_number_close(constants.get("H"), 0.0, "H")
    require_number_close(constants.get("T"), 1.0, "T")
    require_number_close(constants.get("A"), constants.get("S"), "A/S")

    curve = summary.get("curve")
    require(isinstance(curve, dict), "missing curve")
    control_mode = str(curve.get("controlPointMode", ""))
    require("spline" in control_mode and "linear" in control_mode, "curve mode must name spline and linear tail")
    require("hair boundary is used only for position" in str(curve.get("sourceUsage", "")), "wrong source usage")

    profile_validation = curve.get("profileValidation")
    require(isinstance(profile_validation, dict), "missing profileValidation")
    require(profile_validation.get("passed") is True, "profileValidation did not pass")

    unity_sync = curve.get("unityProfileSync")
    require(isinstance(unity_sync, dict), "missing unityProfileSync")
    require(unity_sync.get("passed") is True, "unityProfileSync did not pass")

    styles = summary.get("styles")
    require(isinstance(styles, list) and len(styles) >= 3, "expected three eyebrow styles")
    for style in styles[:3]:
        gate = style.get("commercialShapeGate") if isinstance(style, dict) else None
        require(isinstance(gate, dict), f"missing commercial shape gate: {style!r}")
        require(gate.get("passed") is True, f"commercial shape gate failed: {style!r}")

    return (
        "eyebrow boundary goal ok: "
        f"summary={summary_path} "
        f"primary={primary} "
        f"reference={reference_status}"
    )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    summary_path, _ = load_summary(repo, args.summary)
    print(verify(summary_path, repo, args.require_reference))


if __name__ == "__main__":
    main()
