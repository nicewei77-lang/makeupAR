#!/usr/bin/env python3
"""Pull and inspect E7 in-app Generate evidence from an iPhone app container.

This helper is local-only. It copies only the app Documents subtrees needed to
diagnose the personalized Generate flow, then writes a compact summary that is
safe to use for build-gate decisions.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEVICE = "6F504EE9-BABC-5F6F-A186-C734E04CA625"
DEFAULT_BUNDLE_ID = "com.makeupar.rnvalidation"
DEFAULT_OUTPUT_BASE = REPO_ROOT / "evidence/logs"
PULL_SOURCES = (
    "Documents/e7-generated-lip-packages",
    "Documents/e7-runtime-events",
    "Documents/e7-reference-atlas/capture_pairs",
)


def source_output_path(output_root: Path, source: str) -> Path:
    return output_root / "pulled" / source.removeprefix("Documents/")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull latest E7 generated lip package/apply evidence from iPhone Documents."
    )
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--output-base", type=Path, default=DEFAULT_OUTPUT_BASE)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--timestamp",
        default=datetime.now().strftime("%Y%m%d-%H%M%S"),
        help="Stable timestamp used for the output folder name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print devicectl commands without copying device files.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Continue when one of the optional app Documents subtrees is missing.",
    )
    return parser.parse_args()


def run(command: list[str], cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    return completed


def read_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    return payload if isinstance(payload, dict) else {"value": payload}


def latest_file(root: Path, name: str) -> Path | None:
    if not root.exists():
        return None
    matches = [path for path in root.rglob(name) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: (path.stat().st_mtime, str(path)))


def summarize_package(payload: dict[str, Any] | None, path: Path | None) -> dict[str, Any]:
    if not payload:
        return {"present": False, "path": str(path) if path else None}
    runtime_payload = payload.get("runtimeApplyPayload")
    return {
        "present": True,
        "path": str(path),
        "schemaVersion": payload.get("schemaVersion"),
        "generatedMaskId": payload.get("generatedMaskId"),
        "captureSetId": payload.get("captureSetId"),
        "provider": payload.get("provider"),
        "expressionMode": payload.get("expressionMode"),
        "adjustment": payload.get("adjustment"),
        "qualityWarnings": payload.get("qualityWarnings"),
        "runtimeReady": runtime_payload.get("runtimeReady")
        if isinstance(runtime_payload, dict)
        else None,
        "uvCoverageMetadata": payload.get("uvCoverageMetadata"),
    }


def summarize_saved_record(payload: dict[str, Any] | None, path: Path | None) -> dict[str, Any]:
    if not payload:
        return {"present": False, "path": str(path) if path else None}
    return {
        "present": True,
        "path": str(path),
        "status": payload.get("status"),
        "generatedMaskId": payload.get("generatedMaskId"),
        "packagePath": payload.get("packagePath"),
        "runtimeReady": payload.get("runtimeReady"),
        "createdAt": payload.get("createdAt"),
    }


def summarize_ack(payload: dict[str, Any] | None, path: Path | None) -> dict[str, Any]:
    if not payload:
        return {"present": False, "path": str(path) if path else None}
    return {
        "present": True,
        "path": str(path),
        "type": payload.get("type"),
        "status": payload.get("status"),
        "applied": payload.get("applied"),
        "uvAvailable": payload.get("uvAvailable"),
        "maskTriangles": payload.get("maskTriangles"),
        "generatedMaskId": payload.get("generatedMaskId"),
        "provider": payload.get("provider"),
        "expressionMode": payload.get("expressionMode"),
        "blockedReason": payload.get("blockedReason"),
        "validationVisible": payload.get("validationVisible"),
        "validationStrongMode": payload.get("validationStrongMode"),
        "validationColor": payload.get("validationColor"),
        "validationOpacity": payload.get("validationOpacity"),
    }


def summarize_capture(payload: dict[str, Any] | None, path: Path | None) -> dict[str, Any]:
    if not payload:
        return {"present": False, "path": str(path) if path else None}
    return {
        "present": True,
        "path": str(path),
        "capturePairId": payload.get("capturePairId"),
        "captureSetId": payload.get("captureSetId"),
        "shotKind": payload.get("shotKind") or payload.get("captureShotKind"),
        "framePath": payload.get("framePath"),
        "arFaceExportPath": payload.get("arFaceExportPath"),
        "meshVertexCount": payload.get("meshVertexCount"),
        "meshIndexCount": payload.get("meshIndexCount"),
        "meshUvCount": payload.get("meshUvCount"),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    package = summary["generatedPackage"]
    saved = summary["savedRecord"]
    ack = summary["generatedApplyAck"]
    capture = summary["captureSummary"]
    lines = [
        "# E7 In-App Generate Device Evidence Pull",
        "",
        f"- timestamp: `{summary['timestamp']}`",
        f"- device: `{summary['device']}`",
        f"- bundle: `{summary['bundleId']}`",
        f"- status: `{summary['status']}`",
        "",
        "## Copy Results",
        "",
        *[
            f"- `{result.get('source')}` -> `{result.get('status')}`"
            for result in summary.get("copyResults", [])
        ],
        "",
        "## Latest Artifacts",
        "",
        f"- generated package: `{package.get('path')}`",
        f"- saved record: `{saved.get('path')}`",
        f"- generated apply ack: `{ack.get('path')}`",
        f"- capture summary: `{capture.get('path')}`",
        "",
        "## Apply Diagnosis",
        "",
        f"- package generatedMaskId: `{package.get('generatedMaskId')}`",
        f"- saved status/runtimeReady: `{saved.get('status')}` / `{saved.get('runtimeReady')}`",
        f"- ack present/applied: `{ack.get('present')}` / `{ack.get('applied')}`",
        f"- ack uvAvailable/maskTriangles: `{ack.get('uvAvailable')}` / `{ack.get('maskTriangles')}`",
        f"- ack blockedReason: `{ack.get('blockedReason')}`",
        f"- ack validation controls: visible=`{ack.get('validationVisible')}` strong=`{ack.get('validationStrongMode')}` color=`{ack.get('validationColor')}` opacity=`{ack.get('validationOpacity')}`",
        "",
        "## Capture",
        "",
        f"- capturePairId: `{capture.get('capturePairId')}`",
        f"- shotKind: `{capture.get('shotKind')}`",
        f"- mesh v/i/uv: `{capture.get('meshVertexCount')}` / `{capture.get('meshIndexCount')}` / `{capture.get('meshUvCount')}`",
        "",
        "## Notes",
        "",
        "- This is local-only diagnostic evidence. A saved package is not runtime proof.",
        "- Runtime success still requires matching generated_lip_mask_applied ack and user-visible AR validation.",
        "",
    ]
    return "\n".join(lines)


def copy_device_source(args: argparse.Namespace, output_root: Path, source: str) -> dict[str, Any]:
    destination = source_output_path(output_root, source)
    json_output = output_root / f"{source.replace('/', '_')}.devicectl.json"
    command = [
        "xcrun",
        "devicectl",
        "device",
        "copy",
        "from",
        "--device",
        args.device,
        "--domain-type",
        "appDataContainer",
        "--domain-identifier",
        args.bundle_id,
        "--source",
        source,
        "--destination",
        str(destination),
        "--timeout",
        str(args.timeout),
        "--json-output",
        str(json_output),
    ]
    if args.dry_run:
        print(" ".join(command))
        return {
            "source": source,
            "destination": str(destination),
            "status": "dry-run",
        }
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    completed = run(command)
    if completed.returncode == 0:
        return {
            "source": source,
            "destination": str(destination),
            "status": "copied",
        }
    if args.allow_missing:
        print(f"[e7-device-pull] missing-or-unavailable source tolerated: {source}")
        return {
            "source": source,
            "destination": str(destination),
            "status": "missing",
            "returnCode": completed.returncode,
        }
    raise SystemExit(completed.returncode)


def build_summary(
    args: argparse.Namespace,
    output_root: Path,
    copy_results: list[dict[str, Any]],
) -> dict[str, Any]:
    pulled_root = output_root / "pulled"
    package_path = latest_file(pulled_root / "e7-generated-lip-packages", "generated_lip_package.json")
    saved_path = latest_file(pulled_root / "e7-generated-lip-packages", "saved_record.json")
    ack_path = latest_file(pulled_root / "e7-runtime-events", "generated_lip_mask_applied.latest.json")
    capture_path = latest_file(pulled_root / "e7-reference-atlas" / "capture_pairs", "capture_summary.json")
    status = "pulled"
    if any(result.get("status") == "missing" for result in copy_results):
        status = "partial"
    return {
        "timestamp": args.timestamp,
        "device": args.device,
        "bundleId": args.bundle_id,
        "status": status,
        "outputRoot": str(output_root),
        "copyResults": copy_results,
        "generatedPackage": summarize_package(read_json_if_present(package_path), package_path),
        "savedRecord": summarize_saved_record(read_json_if_present(saved_path), saved_path),
        "generatedApplyAck": summarize_ack(read_json_if_present(ack_path), ack_path),
        "captureSummary": summarize_capture(read_json_if_present(capture_path), capture_path),
    }


def main() -> int:
    args = parse_args()
    output_root = args.output_base.resolve() / f"e7-device-generated-pull-{args.timestamp}"

    copy_results = []
    for source in PULL_SOURCES:
        copy_results.append(copy_device_source(args, output_root, source))

    if args.dry_run:
        return 0

    output_root.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, output_root, copy_results)
    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path = output_root / "summary.md"
    report_path.write_text(render_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"summary={summary_path}")
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
