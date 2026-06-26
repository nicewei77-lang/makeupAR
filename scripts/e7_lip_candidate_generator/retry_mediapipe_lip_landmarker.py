#!/usr/bin/env python3
"""Retry only the MediaPipe lip landmark comparison.

This script intentionally does not rebuild the five core candidates. It runs
MediaPipe FaceLandmarker in isolated child processes, so native aborts are
captured as evidence instead of killing the parent process.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from build_lip_boundary_candidates import (
    DEFAULT_FRAME,
    DEFAULT_MEDIAPIPE_MODEL,
    MEDIAPIPE_INNER_LIP,
    MEDIAPIPE_OUTER_LIP,
    bbox,
    chaikin,
    classify_mediapipe_failure,
    close_mask,
    fill_polygon,
    keep_largest_component,
    make_soft_alpha,
    mediapipe_point,
    save_alpha,
    save_mask,
    sha256_file,
    utc_now,
    write_curve_overlay,
    write_json,
)


DEFAULT_OUTPUT_ROOT = Path("evidence/e7-lip-candidate-generator")


@dataclass(frozen=True)
class Variant:
    variant_id: str
    delegate: str
    image_source: str
    thresholds: float


VARIANTS = (
    Variant("current_cpu_create_from_file", "cpu", "create_from_file", 0.3),
    Variant("cpu_numpy_rgb", "cpu", "numpy_rgb", 0.3),
    Variant("default_delegate_numpy_rgb", "default", "numpy_rgb", 0.3),
    Variant("cpu_numpy_rgb_default_thresholds", "cpu", "numpy_rgb", 0.5),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retry MediaPipe lip landmark comparison only.")
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--mediapipe-model", type=Path, default=DEFAULT_MEDIAPIPE_MODEL)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--variant-id", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--delegate", choices=("cpu", "default"), default="cpu", help=argparse.SUPPRESS)
    parser.add_argument(
        "--image-source",
        choices=("create_from_file", "numpy_rgb"),
        default="create_from_file",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--thresholds", type=float, default=0.3, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=Path, default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_text_tail(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")[-limit:]


def environment_report(frame_path: Path, model_path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schemaVersion": "e7-mediapipe-retry-environment-v0",
        "createdAtUtc": utc_now(),
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.replace("\n", " "),
        "frame": {
            "path": str(frame_path),
            "exists": frame_path.exists(),
        },
        "model": {
            "path": str(model_path),
            "exists": model_path.exists(),
        },
    }
    if frame_path.exists():
        frame = Image.open(frame_path)
        report["frame"].update(
            {
                "size": list(frame.size),
                "mode": frame.mode,
                "sha256": sha256_file(frame_path),
                "bytes": frame_path.stat().st_size,
            }
        )
    if model_path.exists():
        report["model"].update(
            {
                "bytes": model_path.stat().st_size,
                "sha256": sha256_file(model_path),
            }
        )
    try:
        mediapipe = importlib.import_module("mediapipe")
        from mediapipe.tasks import python as mp_python  # type: ignore[import-not-found]
        from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-not-found]

        report["mediapipe"] = {
            "importable": True,
            "version": getattr(mediapipe, "__version__", None),
            "file": getattr(mediapipe, "__file__", None),
            "baseOptionsDelegates": [
                item for item in dir(mp_python.BaseOptions.Delegate) if not item.startswith("_")
            ],
            "faceLandmarkerOptionsSignature": str(inspect.signature(mp_vision.FaceLandmarkerOptions)),
            "runningModes": [item for item in dir(mp_vision.RunningMode) if not item.startswith("_")],
        }
    except Exception as exception:
        report["mediapipe"] = {
            "importable": False,
            "exception": exception.__class__.__name__,
            "message": str(exception),
        }
    return report


def make_mediapipe_image(mp: Any, frame_path: Path, frame: Image.Image, image_source: str) -> Any:
    if image_source == "create_from_file":
        return mp.Image.create_from_file(str(frame_path))
    data = np.ascontiguousarray(np.asarray(frame.convert("RGB")))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=data)


def run_child(args: argparse.Namespace) -> int:
    if args.output_dir is None:
        return 2
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import mediapipe as mp  # type: ignore[import-not-found]
        from mediapipe.tasks import python as mp_python  # type: ignore[import-not-found]
        from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-not-found]
    except Exception as exception:
        write_json(
            output_dir / "mediapipe_lip_report.json",
            {
                "schemaVersion": "e7-mediapipe-lip-comparison-v0",
                "createdAtUtc": utc_now(),
                "available": False,
                "reason": "mediapipe_import_failed",
                "exception": exception.__class__.__name__,
                "message": str(exception),
            },
        )
        return 3

    frame = Image.open(args.frame).convert("RGB")
    base_kwargs: dict[str, Any] = {"model_asset_path": str(args.mediapipe_model)}
    if args.delegate == "cpu":
        base_kwargs["delegate"] = mp_python.BaseOptions.Delegate.CPU
    base_options = mp_python.BaseOptions(**base_kwargs)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        min_face_detection_confidence=args.thresholds,
        min_face_presence_confidence=args.thresholds,
        min_tracking_confidence=args.thresholds,
    )

    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    try:
        image = make_mediapipe_image(mp, args.frame, frame, args.image_source)
        result = landmarker.detect(image)
    finally:
        landmarker.close()

    face_count = len(result.face_landmarks)
    if face_count == 0:
        write_json(
            output_dir / "mediapipe_lip_report.json",
            {
                "schemaVersion": "e7-mediapipe-lip-comparison-v0",
                "createdAtUtc": utc_now(),
                "available": False,
                "reason": "no_face_detected",
                "faceCount": 0,
            },
        )
        return 5

    landmarks = result.face_landmarks[0]
    required_index = max(max(MEDIAPIPE_OUTER_LIP), max(MEDIAPIPE_INNER_LIP))
    if len(landmarks) <= required_index:
        write_json(
            output_dir / "mediapipe_lip_report.json",
            {
                "schemaVersion": "e7-mediapipe-lip-comparison-v0",
                "createdAtUtc": utc_now(),
                "available": False,
                "reason": "landmark_count_too_small",
                "landmarkCount": len(landmarks),
                "requiredIndex": required_index,
            },
        )
        return 6

    size = frame.size
    outer_points = [mediapipe_point(landmarks, index, size) for index in MEDIAPIPE_OUTER_LIP]
    inner_points = [mediapipe_point(landmarks, index, size) for index in MEDIAPIPE_INNER_LIP]
    outer_curve = chaikin(outer_points, 4)
    inner_curve = chaikin(inner_points, 3)
    mask = keep_largest_component(close_mask(fill_polygon(outer_curve, size, [inner_curve]), 1))
    alpha = make_soft_alpha(mask, 2.1)

    mask_path = output_dir / "mediapipe_lip_curve_mask.png"
    alpha_path = output_dir / "mediapipe_lip_curve_alpha.png"
    overlay_path = output_dir / "mediapipe_lip_curve_overlay.png"
    landmark_overlay_path = output_dir / "mediapipe_landmark_overlay.png"
    curve_points_path = output_dir / "mediapipe_lip_curve_points.json"

    save_mask(mask_path, mask)
    save_alpha(alpha_path, alpha)
    write_curve_overlay(frame, mask, outer_curve, overlay_path, "mediapipe_lip_curve")

    landmark_image = frame.convert("RGB")
    draw = ImageDraw.Draw(landmark_image, "RGBA")
    for left, right in zip(outer_points, outer_points[1:] + outer_points[:1]):
        draw.line([left, right], fill=(80, 255, 120, 230), width=3)
    for left, right in zip(inner_points, inner_points[1:] + inner_points[:1]):
        draw.line([left, right], fill=(255, 230, 80, 230), width=2)
    for index, point in zip(MEDIAPIPE_OUTER_LIP, outer_points):
        x, y = point
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(80, 255, 120, 240))
        draw.text((x + 4, y - 4), str(index), fill=(255, 255, 255, 220))
    landmark_image.save(landmark_overlay_path)

    write_json(
        curve_points_path,
        {
            "outerIndices": list(MEDIAPIPE_OUTER_LIP),
            "innerIndices": list(MEDIAPIPE_INNER_LIP),
            "outerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in outer_points],
            "innerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in inner_points],
            "outerCurvePointCount": len(outer_curve),
            "innerCurvePointCount": len(inner_curve),
        },
    )

    write_json(
        output_dir / "mediapipe_lip_report.json",
        {
            "schemaVersion": "e7-mediapipe-lip-comparison-v0",
            "createdAtUtc": utc_now(),
            "available": True,
            "variantId": args.variant_id,
            "role": "additional_comparison_signal_not_replacement",
            "api": "mediapipe.tasks.python.vision.FaceLandmarker",
            "options": {
                "delegate": args.delegate,
                "imageSource": args.image_source,
                "runningMode": "IMAGE",
                "numFaces": 1,
                "outputFaceBlendshapes": False,
                "outputFacialTransformationMatrixes": False,
                "thresholds": args.thresholds,
            },
            "modelPath": str(args.mediapipe_model),
            "framePath": str(args.frame),
            "faceCount": face_count,
            "landmarkCount": len(landmarks),
            "outerPointCount": len(outer_points),
            "innerPointCount": len(inner_points),
            "positivePixels": int(np.count_nonzero(mask)),
            "bbox": bbox(mask),
            "outputs": {
                "landmarkOverlay": str(landmark_overlay_path),
                "mask": str(mask_path),
                "alpha": str(alpha_path),
                "curveOverlay": str(overlay_path),
                "curvePoints": str(curve_points_path),
            },
            "limitations": [
                "MediaPipe landmarks describe face geometry, not makeup color boundary.",
                "This is one clean female sample only.",
                "This result still needs visual review and real camera comparison.",
            ],
        },
    )
    return 0


def run_variant(args: argparse.Namespace, output_dir: Path, variant: Variant) -> dict[str, Any]:
    variant_dir = output_dir / "attempts" / variant.variant_id
    variant_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child",
        "--variant-id",
        variant.variant_id,
        "--frame",
        str(args.frame.resolve()),
        "--mediapipe-model",
        str(args.mediapipe_model.resolve()),
        "--delegate",
        variant.delegate,
        "--image-source",
        variant.image_source,
        "--thresholds",
        str(variant.thresholds),
        "--output-dir",
        str(variant_dir.resolve()),
    ]
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=45, env=env, check=False)
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exception:
        exit_code = 124
        stdout = exception.stdout or ""
        stderr = exception.stderr or ""

    stdout_path = variant_dir / "mediapipe_process_stdout.txt"
    stderr_path = variant_dir / "mediapipe_process_stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")

    report_path = variant_dir / "mediapipe_lip_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else None
    available = bool(report and report.get("available")) and exit_code == 0
    diagnosis = None if available else classify_mediapipe_failure(stderr[-12000:], exit_code)
    attempt = {
        "variantId": variant.variant_id,
        "command": command,
        "commandString": shlex.join(command),
        "exitCode": exit_code,
        "available": available,
        "stdoutPath": str(stdout_path),
        "stderrPath": str(stderr_path),
        "reportPath": str(report_path) if report_path.exists() else None,
        "stdoutTail": stdout[-4000:],
        "stderrTail": stderr[-8000:],
        "options": {
            "delegate": variant.delegate,
            "imageSource": variant.image_source,
            "thresholds": variant.thresholds,
        },
    }
    if diagnosis:
        attempt["failureDiagnosis"] = diagnosis
    if report:
        attempt["childReport"] = report
    write_json(variant_dir / "attempt_summary.json", attempt)
    return attempt


def make_text_panel(size: tuple[int, int], title: str, lines: list[str]) -> Image.Image:
    panel = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(80, 80, 80), width=3)
    draw.text((36, 36), title, fill=(20, 20, 20))
    y = 90
    for line in lines:
        words = line.split()
        wrapped: list[str] = []
        current = ""
        for word in words:
            if len(word) > 58:
                if current:
                    wrapped.append(current)
                    current = ""
                wrapped.extend(word[index : index + 58] for index in range(0, len(word), 58))
                continue
            trial = f"{current} {word}".strip()
            if len(trial) > 58 and current:
                wrapped.append(current)
                current = word
            else:
                current = trial
        wrapped.append(current)
        for wrapped_line in wrapped[:4]:
            draw.text((36, y), wrapped_line, fill=(30, 30, 30))
            y += 28
        y += 8
    return panel


def write_review_sheet(output_dir: Path, frame_path: Path, final_report: dict[str, Any]) -> None:
    frame = Image.open(frame_path).convert("RGB")
    cell_w = 420
    cell_h = int(cell_w * frame.height / frame.width)
    cells: list[Image.Image] = []
    labels: list[str] = []
    cells.append(frame.resize((cell_w, cell_h), Image.Resampling.LANCZOS))
    labels.append("input_frame")
    if final_report.get("available"):
        outputs = final_report.get("outputs", {})
        for label, key in (
            ("landmark_overlay", "landmarkOverlay"),
            ("curve_overlay", "curveOverlay"),
            ("mask", "mask"),
        ):
            path = Path(outputs.get(key, ""))
            if path.exists():
                cells.append(Image.open(path).convert("RGB").resize((cell_w, cell_h), Image.Resampling.LANCZOS))
                labels.append(label)
    else:
        attempts = final_report.get("attempts", [])
        for attempt in attempts:
            diagnosis = attempt.get("failureDiagnosis", {})
            panel = make_text_panel(
                (cell_w, cell_h),
                attempt["variantId"],
                [
                    f"exitCode: {attempt.get('exitCode')}",
                    diagnosis.get("mostLikelyRootCause", "see stderr"),
                    f"stderr: {attempt.get('stderrPath')}",
                ],
            )
            cells.append(panel)
            labels.append("failed")

    columns = min(3, len(cells))
    rows = (len(cells) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + 36)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, cell in enumerate(cells):
        col = index % columns
        row = index // columns
        x = col * cell_w
        y = row * (cell_h + 36)
        sheet.paste(cell, (x, y))
        draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(220, 220, 220), width=2)
        draw.text((x + 8, y + cell_h + 8), labels[index], fill=(20, 20, 20))
    sheet.save(output_dir / "mediapipe_only_review_sheet.png")


def promote_success_outputs(output_dir: Path, attempt: dict[str, Any]) -> dict[str, str]:
    child = attempt.get("childReport", {})
    outputs = child.get("outputs", {})
    promoted: dict[str, str] = {}
    mapping = {
        "landmarkOverlay": "mediapipe_landmark_overlay.png",
        "curveOverlay": "mediapipe_lip_curve_overlay.png",
        "mask": "mediapipe_lip_curve_mask.png",
        "alpha": "mediapipe_lip_curve_alpha.png",
        "curvePoints": "mediapipe_lip_curve_points.json",
    }
    for key, filename in mapping.items():
        source = Path(outputs.get(key, ""))
        if source.exists():
            destination = output_dir / filename
            shutil.copyfile(source, destination)
            promoted[key] = str(destination)
    return promoted


def write_retry_summary(output_dir: Path, report: dict[str, Any]) -> None:
    lines = [
        "# MediaPipe lip landmark retry result",
        "",
        f"- createdAtUtc: `{report.get('createdAtUtc')}`",
        f"- available: `{report.get('available')}`",
        f"- frame: `{report.get('framePath')}`",
        f"- model: `{report.get('modelPath')}`",
        "",
    ]
    if report.get("available"):
        lines.extend(
            [
                f"- successfulVariant: `{report.get('successfulVariant')}`",
                f"- landmarkOverlay: `{report.get('outputs', {}).get('landmarkOverlay')}`",
                f"- curveOverlay: `{report.get('outputs', {}).get('curveOverlay')}`",
                f"- mask: `{report.get('outputs', {}).get('mask')}`",
            ]
        )
    else:
        lines.extend(
            [
                f"- reason: `{report.get('reason')}`",
                f"- rootCause: {report.get('failureDiagnosis', {}).get('mostLikelyRootCause')}",
                f"- smallestNextUnblock: {report.get('failureDiagnosis', {}).get('smallestNextUnblock')}",
                "",
                "## Attempts",
                "",
            ]
        )
        for attempt in report.get("attempts", []):
            lines.extend(
                [
                    f"### {attempt.get('variantId')}",
                    "",
                    f"- exitCode: `{attempt.get('exitCode')}`",
                    f"- command: `{attempt.get('commandString')}`",
                    f"- stdout: `{attempt.get('stdoutPath')}`",
                    f"- stderr: `{attempt.get('stderrPath')}`",
                    "",
                ]
            )
    (output_dir / "mediapipe_retry_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.child:
        return run_child(args)

    run_id = args.run_id or f"mediapipe-retry-{utc_stamp()}"
    output_dir = args.output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "input_environment_report.json", environment_report(args.frame, args.mediapipe_model))

    attempts = [run_variant(args, output_dir, variant) for variant in VARIANTS]
    first_success = next((attempt for attempt in attempts if attempt.get("available")), None)
    primary = attempts[0] if attempts else {}
    (output_dir / "mediapipe_process_stdout.txt").write_text(
        read_text_tail(Path(primary.get("stdoutPath", "")), 12000),
        encoding="utf-8",
    )
    (output_dir / "mediapipe_process_stderr.txt").write_text(
        read_text_tail(Path(primary.get("stderrPath", "")), 12000),
        encoding="utf-8",
    )

    if first_success:
        promoted = promote_success_outputs(output_dir, first_success)
        child = first_success.get("childReport", {})
        report = {
            **child,
            "createdAtUtc": utc_now(),
            "retryRunId": run_id,
            "outputDir": str(output_dir),
            "successfulVariant": first_success["variantId"],
            "attempts": attempts,
            "outputs": promoted,
            "inputEnvironmentReport": str(output_dir / "input_environment_report.json"),
            "reviewSheet": str(output_dir / "mediapipe_only_review_sheet.png"),
        }
    else:
        diagnosis = classify_mediapipe_failure(str(primary.get("stderrTail", "")), int(primary.get("exitCode", -1)))
        report = {
            "schemaVersion": "e7-mediapipe-lip-comparison-v0",
            "createdAtUtc": utc_now(),
            "available": False,
            "reason": "all_mediapipe_retry_variants_failed",
            "role": "additional_comparison_signal_not_replacement",
            "pythonExecutable": sys.executable,
            "framePath": str(args.frame),
            "modelPath": str(args.mediapipe_model),
            "outputDir": str(output_dir),
            "attempts": attempts,
            "failureDiagnosis": {
                **diagnosis,
                "smallestNextUnblock": (
                    "Try the same script in a GUI-capable macOS Python session or a different Python/MediaPipe "
                    "environment where MediaPipe FaceLandmarker can create its native Metal/GL service; otherwise "
                    "leave MediaPipe as a documented failed comparison signal."
                ),
            },
            "inputEnvironmentReport": str(output_dir / "input_environment_report.json"),
            "reviewSheet": str(output_dir / "mediapipe_only_review_sheet.png"),
            "outputs": {},
        }

    write_json(output_dir / "mediapipe_lip_report.json", report)
    write_retry_summary(output_dir, report)
    write_review_sheet(output_dir, args.frame, report)
    print(json.dumps({"outputDir": str(output_dir), "available": report.get("available")}, ensure_ascii=False))
    return 0 if report.get("available") else 1


if __name__ == "__main__":
    raise SystemExit(main())
