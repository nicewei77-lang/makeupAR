#!/usr/bin/env python3
"""Run a local MediaPipe doctor for E7 face-region sample generation.

The doctor records the installed Python MediaPipe API surface, whether legacy
FaceMesh is available, and the result of the existing isolated Tasks retry.
It does not upload data or claim runtime/product readiness.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FRAME = REPO_ROOT / "evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png"
DEFAULT_MODEL = REPO_ROOT / ".cache/mediapipe/face_landmarker.task"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence/e7-region-detection-comparison/mediapipe-local-doctor"
RETRY_SCRIPT = REPO_ROOT / "scripts/e7_lip_candidate_generator/retry_mediapipe_lip_landmarker.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local MediaPipe doctor.")
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--mediapipe-model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def api_surface_report() -> dict[str, Any]:
    report: dict[str, Any] = {
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.replace("\n", " "),
    }
    try:
        mediapipe = importlib.import_module("mediapipe")
        report["mediapipe"] = {
            "importable": True,
            "version": getattr(mediapipe, "__version__", None),
            "file": getattr(mediapipe, "__file__", None),
            "topLevelAttrs": [attr for attr in dir(mediapipe) if not attr.startswith("_")],
            "hasSolutionsAttr": hasattr(mediapipe, "solutions"),
        }
    except Exception as exception:
        report["mediapipe"] = {
            "importable": False,
            "exception": exception.__class__.__name__,
            "message": str(exception),
        }
        return report

    try:
        legacy = importlib.import_module("mediapipe.python.solutions.face_mesh")
        report["legacyFaceMesh"] = {
            "importable": True,
            "file": getattr(legacy, "__file__", None),
        }
    except Exception as exception:
        report["legacyFaceMesh"] = {
            "importable": False,
            "exception": exception.__class__.__name__,
            "message": str(exception),
        }

    try:
        tasks_python = importlib.import_module("mediapipe.tasks.python")
        tasks_vision = importlib.import_module("mediapipe.tasks.python.vision")
        report["tasksVision"] = {
            "importable": True,
            "baseOptionsDelegates": [
                item for item in dir(tasks_python.BaseOptions.Delegate) if not item.startswith("_")
            ],
            "hasFaceLandmarker": hasattr(tasks_vision, "FaceLandmarker"),
        }
    except Exception as exception:
        report["tasksVision"] = {
            "importable": False,
            "exception": exception.__class__.__name__,
            "message": str(exception),
        }
    return report


def run_retry(args: argparse.Namespace, output_dir: Path, run_id: str) -> dict[str, Any]:
    retry_root = output_dir / "tasks_retry"
    command = [
        sys.executable,
        str(RETRY_SCRIPT),
        "--frame",
        str(args.frame),
        "--mediapipe-model",
        str(args.mediapipe_model),
        "--output-root",
        str(retry_root),
        "--run-id",
        run_id,
    ]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    stdout_path = output_dir / "mediapipe_retry_stdout.txt"
    stderr_path = output_dir / "mediapipe_retry_stderr.txt"
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    retry_dir = retry_root / run_id
    summary_path = retry_dir / "mediapipe_retry_summary.md"
    return {
        "command": command,
        "exitCode": completed.returncode,
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "retryDir": str(retry_dir),
        "summaryPath": str(summary_path) if summary_path.exists() else None,
        "summaryTail": summary_path.read_text(encoding="utf-8")[-4000:] if summary_path.exists() else None,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    api = report["apiSurface"]
    retry = report["tasksRetry"]
    lines = [
        "# MediaPipe Local Doctor",
        "",
        f"- createdAt: `{report['createdAt']}`",
        f"- frame: `{report['framePath']}`",
        f"- model: `{report['modelPath']}`",
        f"- mediapipe importable: `{api.get('mediapipe', {}).get('importable')}`",
        f"- version: `{api.get('mediapipe', {}).get('version')}`",
        f"- has top-level solutions: `{api.get('mediapipe', {}).get('hasSolutionsAttr')}`",
        f"- legacy FaceMesh importable: `{api.get('legacyFaceMesh', {}).get('importable')}`",
        f"- Tasks retry exitCode: `{retry.get('exitCode')}`",
        f"- Tasks retry summary: `{retry.get('summaryPath')}`",
        "",
        "## Interpretation",
        "",
    ]
    if not api.get("legacyFaceMesh", {}).get("importable"):
        lines.append("- Legacy `mp.solutions.face_mesh` fallback is not available in this environment.")
    if retry.get("exitCode") != 0:
        lines.append("- Tasks FaceLandmarker retry did not produce a usable result. Inspect the retry summary/stderr for the native failure.")
    lines.append("- This doctor is local-only and does not prove iPhone native MediaPipe runtime behavior.")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("mediapipe-doctor-%Y%m%dT%H%M%SZ")
    report = {
        "schemaVersion": "e7-mediapipe-local-doctor-v0",
        "createdAt": utc_now(),
        "framePath": str(args.frame),
        "modelPath": str(args.mediapipe_model),
        "apiSurface": api_surface_report(),
        "tasksRetry": run_retry(args, output_dir, run_id),
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
    }
    write_json(output_dir / "mediapipe_local_doctor.json", report)
    write_markdown(output_dir / "mediapipe_local_doctor.md", report)
    print(output_dir / "mediapipe_local_doctor.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
