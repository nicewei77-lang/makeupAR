#!/usr/bin/env python3
"""Pull one iOS capture pair from app Documents and rebuild region overlays.

This helper is intentionally local-only. It reads the app data container from a
paired iPhone with devicectl, copies the selected capture pair into repo
evidence, then runs the existing eye/skin/brow comparison builder.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEVICE = "6F504EE9-BABC-5F6F-A186-C734E04CA625"
DEFAULT_BUNDLE_ID = "com.makeupar.rnvalidation"
DEFAULT_CAPTURE_PAIR = "pair_face_20260627T091334Z_06"
DEFAULT_CAPTURE_ROOT = REPO_ROOT / "evidence/e7-reference-atlas/capture_pairs"
DEFAULT_OUTPUT_BASE = REPO_ROOT / "evidence/e7-region-detection-comparison"
BUILDER = REPO_ROOT / "scripts/e7_region_detection_compare/build_capture_pair_region_masks.py"
NATIVE_ARTIFACTS = ("vision_face_landmarks.json", "mediapipe_face_landmarks.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pull one iOS capture pair and rebuild E7 region comparison overlays."
    )
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--bundle-id", default=DEFAULT_BUNDLE_ID)
    parser.add_argument("--capture-pair-id", default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--capture-root", type=Path, default=DEFAULT_CAPTURE_ROOT)
    parser.add_argument("--output-base", type=Path, default=DEFAULT_OUTPUT_BASE)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument(
        "--require-native-artifacts",
        action="store_true",
        help="Exit non-zero if Vision/MediaPipe native full-face JSON files are missing after pull.",
    )
    parser.add_argument(
        "--skip-rebuild",
        action="store_true",
        help="Only pull the capture pair; do not rebuild masks/contact sheet.",
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


def copy_tree_contents(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def pull_capture_pair(args: argparse.Namespace) -> Path:
    pair_id = args.capture_pair_id
    tmp_root = Path("/private/tmp/makeupar-ios-capture-pair-pull") / pair_id
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.parent.mkdir(parents=True, exist_ok=True)

    json_output = tmp_root.parent / f"{pair_id}.devicectl.json"
    source = f"Documents/e7-reference-atlas/capture_pairs/{pair_id}"
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
        str(tmp_root),
        "--timeout",
        str(args.timeout),
        "--json-output",
        str(json_output),
    ]
    completed = run(command)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)

    source_root = tmp_root / pair_id if (tmp_root / pair_id).exists() else tmp_root
    if not source_root.exists():
        raise SystemExit(f"Pulled path does not exist: {source_root}")

    local_pair = args.capture_root.resolve() / pair_id
    copy_tree_contents(source_root, local_pair)
    return local_pair


def inspect_pair(local_pair: Path) -> dict[str, Any]:
    files = {path.name for path in local_pair.iterdir()} if local_pair.exists() else set()
    return {
        "localPairPath": str(local_pair),
        "requiredCaptureFilesPresent": all(
            name in files for name in ("frame.png", "arface_export.json", "capture_summary.json")
        ),
        "nativeArtifacts": {
            name: {
                "present": name in files,
                "path": str(local_pair / name),
            }
            for name in NATIVE_ARTIFACTS
        },
    }


def rebuild(args: argparse.Namespace, local_pair: Path) -> Path:
    output_root = args.output_base.resolve() / args.capture_pair_id
    command = [
        sys.executable,
        str(BUILDER),
        "--capture-pair",
        str(local_pair),
        "--output-root",
        str(output_root),
    ]
    completed = run(command)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return output_root / "contact_sheet_eye_skin_brow.png"


def main() -> int:
    args = parse_args()
    local_pair = pull_capture_pair(args)
    inspection = inspect_pair(local_pair)
    print(json.dumps(inspection, ensure_ascii=False, indent=2))

    missing = [
        name
        for name, payload in inspection["nativeArtifacts"].items()
        if not payload["present"]
    ]
    if args.require_native_artifacts and missing:
        print(f"Missing native artifacts: {', '.join(missing)}", file=sys.stderr)
        return 3

    if not args.skip_rebuild:
        contact_sheet = rebuild(args, local_pair)
        print(f"contactSheet={contact_sheet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
