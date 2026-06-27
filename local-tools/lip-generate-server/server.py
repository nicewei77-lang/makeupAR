#!/usr/bin/env python3
"""Local-only E7 personalized lip Generate server.

This server is a development facade for the web beta. It binds to 127.0.0.1,
uses existing local fixtures/scripts, writes derived artifacts only, and does
not upload or persist new raw camera frames.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = ROOT / "fixtures/lip-generate/fixture_inventory.json"
RUN_ROOT = ROOT / "evidence/e7-lip-generate-server"
SAVE_ROOT = RUN_ROOT / "saved"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8791
ALLOWED_ORIGINS = {
    "http://127.0.0.1:8789",
    "http://localhost:8789",
}
DEFAULT_PRIVACY = {
    "localOnly": True,
    "offDeviceUpload": False,
    "longTermRawFrameStored": False,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())[:80]
    return cleaned.strip(".-") or f"run-{utc_stamp()}"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def repo_path(repo_relative_path: str) -> Path:
    if not repo_relative_path or Path(repo_relative_path).is_absolute():
        raise ValueError(f"expected repo-relative path: {repo_relative_path}")
    resolved = (ROOT / repo_relative_path).resolve()
    if ROOT.resolve() not in [resolved, *resolved.parents]:
        raise ValueError(f"path escapes repo root: {repo_relative_path}")
    return resolved


def artifact_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        resolved = path.resolve()
        if ROOT.resolve() not in [resolved, *resolved.parents]:
            raise ValueError(f"artifact path escapes repo root: {value}")
        return resolved
    return repo_path(value)


def is_allowed_artifact(path: Path) -> bool:
    resolved = path.resolve()
    allowed_roots = [
        RUN_ROOT.resolve(),
        (ROOT / "fixtures/lip-generate").resolve(),
        (ROOT / "evidence/references").resolve(),
        (ROOT / "evidence/e7-reference-atlas/capture_pairs").resolve(),
    ]
    return any(root in [resolved, *resolved.parents] for root in allowed_roots)


def normalize_artifact_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    resolved = path.resolve()
    if ROOT.resolve() in [resolved, *resolved.parents]:
        return rel(resolved)
    return value


def normalize_projection_summary(summary: dict[str, Any]) -> dict[str, Any]:
    artifacts = summary.get("artifacts")
    if isinstance(artifacts, dict):
        summary["artifacts"] = {
            key: normalize_artifact_value(value) for key, value in artifacts.items()
        }
    inputs = summary.get("inputs")
    if isinstance(inputs, dict):
        capture = inputs.get("capturePair")
        if isinstance(capture, dict):
            for key in ("path", "framePath", "arFaceExportPath"):
                capture[key] = normalize_artifact_value(capture.get(key))
        mask = inputs.get("screenSpaceLipReferenceMask")
        if isinstance(mask, dict):
            mask["path"] = normalize_artifact_value(mask.get("path"))
    return summary


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def redact_request_for_storage(value: Any) -> Any:
    if isinstance(value, list):
        return [redact_request_for_storage(item) for item in value]
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, entry in value.items():
            normalized_key = key.lower()
            if any(
                token in normalized_key
                for token in ("base64", "imagebytes", "rawframe", "cameraframe")
            ):
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_request_for_storage(entry)
        return redacted
    return value


def encode_texture_base64(
    repo_relative_path: str | None,
) -> tuple[str | None, str | None, int | None, int | None]:
    if not repo_relative_path:
        return None, None, None, None
    path = repo_path(repo_relative_path)
    if not path.exists() or not path.is_file():
        return None, None, None, None
    with Image.open(path) as image:
        width, height = image.size
        raw_rgba_base64 = base64.b64encode(image.convert("RGBA").tobytes()).decode(
            "ascii"
        )
    return base64.b64encode(path.read_bytes()).decode("ascii"), raw_rgba_base64, width, height


def load_inventory() -> dict[str, Any]:
    return read_json(INVENTORY_PATH)


def find_fixture(fixture_id: str | None) -> dict[str, Any]:
    inventory = load_inventory()
    requested = fixture_id or inventory["defaultFixtureId"]
    for fixture in inventory.get("fixtures", []):
        if fixture.get("fixtureId") == requested:
            return fixture
    raise KeyError(f"unknown fixtureId: {requested}")


def validate_privacy(payload: dict[str, Any]) -> list[str]:
    privacy = payload.get("privacy") or {}
    blockers: list[str] = []
    if privacy.get("localOnly") is not True:
        blockers.append("privacy.localOnly_must_be_true")
    if privacy.get("offDeviceUpload") is not False:
        blockers.append("privacy.offDeviceUpload_must_be_false")
    if privacy.get("longTermRawFrameStored") is not False:
        blockers.append("privacy.longTermRawFrameStored_must_be_false")
    return blockers


def make_run_dir(request_id: str, provider: str, expression_mode: str) -> Path:
    run_id = safe_id(f"{request_id}-{provider}-{expression_mode}")
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_run_artifact(path_value: str, expected_name: str) -> Path:
    path = artifact_path(path_value)
    resolved = path.resolve()
    if not is_allowed_artifact(resolved):
        raise ValueError(f"artifact_not_allowed:{path_value}")
    if RUN_ROOT.resolve() not in [resolved, *resolved.parents]:
        raise ValueError(f"artifact_not_in_generate_run_root:{path_value}")
    if resolved.name != expected_name:
        raise ValueError(f"unexpected_artifact_name:{resolved.name}")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def points_from_vision(contour: dict[str, Any]) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    contours = contour.get("contours", {})
    outer = contours.get("outerLips", {}).get("imagePoints", [])
    inner = contours.get("innerLips", {}).get("imagePoints", [])
    outer_points = [(float(point["x"]), float(point["y"])) for point in outer]
    inner_points = [(float(point["x"]), float(point["y"])) for point in inner]
    return outer_points, inner_points


def points_from_mediapipe(points: dict[str, Any]) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    outer = points.get("outerPoints", [])
    inner = points.get("innerPoints", [])
    outer_points = [(float(point["x"]), float(point["y"])) for point in outer]
    inner_points = [(float(point["x"]), float(point["y"])) for point in inner]
    return outer_points, inner_points


def normalized_adjustment(payload: dict[str, Any]) -> dict[str, float]:
    adjustment = payload.get("adjustment") or {}
    return {
        key: max(-1.0, min(1.0, float(adjustment.get(key, 0.0))))
        for key in (
            "cornerReach",
            "upperLipTightness",
            "lowerLipTightness",
            "verticalOffset",
        )
    }


def bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def apply_lip_adjustment(
    points: list[tuple[float, float]],
    adjustment: dict[str, float],
    reference_bounds: tuple[float, float, float, float],
    frame_size: tuple[int, int],
    *,
    inner: bool = False,
) -> list[tuple[float, float]]:
    if not points:
        return []

    min_x, min_y, max_x, max_y = reference_bounds
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    center_x = min_x + width * 0.5
    center_y = min_y + height * 0.5
    corner_scale = 0.45 if inner else 1.0
    tightness_scale = 0.35 if inner else 1.0
    adjusted: list[tuple[float, float]] = []

    for x, y in points:
        dx = x - center_x
        dy = y - center_y
        corner_weight = min(1.0, abs(dx) / (width * 0.5))
        vertical_weight = min(1.0, abs(dy) / (height * 0.5))

        x = center_x + dx * (
            1.0 + adjustment["cornerReach"] * 0.22 * corner_weight * corner_scale
        )
        y += adjustment["verticalOffset"] * height * 0.38

        if dy < 0:
            y += adjustment["upperLipTightness"] * height * 0.24 * vertical_weight * tightness_scale
        elif dy > 0:
            y -= adjustment["lowerLipTightness"] * height * 0.24 * vertical_weight * tightness_scale

        adjusted.append(
            (
                max(0.0, min(float(frame_size[0] - 1), x)),
                max(0.0, min(float(frame_size[1] - 1), y)),
            )
        )

    return adjusted


def chaikin_closed(
    points: list[tuple[float, float]], iterations: int
) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    curve = points
    for _ in range(iterations):
        next_curve: list[tuple[float, float]] = []
        for index, point in enumerate(curve):
            next_point = curve[(index + 1) % len(curve)]
            next_curve.append(
                (
                    point[0] * 0.75 + next_point[0] * 0.25,
                    point[1] * 0.75 + next_point[1] * 0.25,
                )
            )
            next_curve.append(
                (
                    point[0] * 0.25 + next_point[0] * 0.75,
                    point[1] * 0.25 + next_point[1] * 0.75,
                )
            )
        curve = next_curve
    return curve


def make_smooth_curve_mask(
    frame_size: tuple[int, int],
    outer_points: list[tuple[float, float]],
    inner_points: list[tuple[float, float]],
    adjustment: dict[str, float],
    *,
    smooth_iterations: int,
) -> tuple[Image.Image, list[tuple[float, float]], list[tuple[float, float]]]:
    reference_bounds = bounds(outer_points)
    adjusted_outer = apply_lip_adjustment(
        outer_points, adjustment, reference_bounds, frame_size
    )
    adjusted_inner = apply_lip_adjustment(
        inner_points, adjustment, reference_bounds, frame_size, inner=True
    )
    outer_curve = chaikin_closed(adjusted_outer, smooth_iterations)
    inner_curve = chaikin_closed(adjusted_inner, max(1, smooth_iterations - 1))
    scale = 4
    scaled_size = (frame_size[0] * scale, frame_size[1] * scale)
    mask = Image.new("L", scaled_size, 0)
    draw = ImageDraw.Draw(mask)
    if outer_curve:
        draw.polygon([(x * scale, y * scale) for x, y in outer_curve], fill=255)
    if len(inner_curve) >= 3:
        draw.polygon([(x * scale, y * scale) for x, y in inner_curve], fill=0)
    return (
        mask.resize(frame_size, Image.Resampling.LANCZOS),
        outer_curve,
        inner_curve,
    )


def save_alpha(mask_path: Path, alpha_path: Path) -> None:
    mask = Image.open(mask_path).convert("L")
    alpha = mask.filter(ImageFilter.GaussianBlur(radius=2.2))
    alpha.save(alpha_path)


def save_overlay(frame_path: Path, mask_path: Path, overlay_path: Path, label: str) -> None:
    frame = Image.open(frame_path).convert("RGB")
    mask = Image.open(mask_path).convert("L")
    frame_array = np.asarray(frame, dtype=np.float32)
    mask_array = np.asarray(mask) > 0
    color = np.zeros_like(frame_array)
    color[:, :, 0] = 225
    color[:, :, 1] = 60 if label == "vision" else 190
    color[:, :, 2] = 130 if label == "vision" else 80
    frame_array[mask_array] = (frame_array[mask_array] * 0.45) + (color[mask_array] * 0.55)
    Image.fromarray(np.clip(frame_array, 0, 255).astype(np.uint8)).save(overlay_path)


def generate_vision_mask(
    fixture: dict[str, Any],
    run_dir: Path,
    adjustment: dict[str, float],
) -> tuple[dict[str, Any], list[str]]:
    provider = fixture["providers"]["vision"]
    contour_path = repo_path(provider["contourPath"])
    frame_path = repo_path(fixture["framePath"])
    contour = read_json(contour_path)
    outer_points, inner_points = points_from_vision(contour)
    frame = Image.open(frame_path)
    if not outer_points:
        raise RuntimeError("vision_outer_lip_points_missing")

    mask_path = run_dir / "vision_lip_mask.png"
    alpha_path = run_dir / "vision_lip_alpha.png"
    overlay_path = run_dir / "vision_lip_overlay.png"
    boundary_path = run_dir / "vision_lip_boundary_2d.json"
    mask, outer_curve, inner_curve = make_smooth_curve_mask(
        frame.size, outer_points, inner_points, adjustment, smooth_iterations=4
    )
    mask.save(mask_path)
    save_alpha(mask_path, alpha_path)
    save_overlay(frame_path, mask_path, overlay_path, "vision")
    boundary = {
        "coordinateSpace": "frame_image_pixel_top_left",
        "outerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in outer_curve],
        "innerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in inner_curve],
        "source": "vision",
        "generationMethod": "vision_curve_fill",
        "adjustmentApplied": adjustment,
    }
    write_json(boundary_path, boundary)
    outputs = {
        "mask": rel(mask_path),
        "alpha": rel(alpha_path),
        "overlay": rel(overlay_path),
        "boundary": rel(boundary_path),
        "contour": rel(contour_path),
    }
    warnings = list(provider.get("warnings", []))
    warnings.append("vision_curve_fill_smooth_boundary_no_cv_skimage")
    return outputs, warnings


def generate_mediapipe_mask(
    fixture: dict[str, Any],
    run_dir: Path,
    adjustment: dict[str, float],
) -> tuple[dict[str, Any], list[str]]:
    provider = fixture["providers"]["mediapipe"]
    frame_path = repo_path(fixture["framePath"])
    points_path = repo_path(provider["pointsPath"])
    points = read_json(points_path)
    outer_points, inner_points = points_from_mediapipe(points)
    frame = Image.open(frame_path)

    mask_path = run_dir / "mediapipe_lip_mask.png"
    alpha_path = run_dir / "mediapipe_lip_alpha.png"
    overlay_path = run_dir / "mediapipe_lip_overlay.png"
    boundary_path = run_dir / "mediapipe_lip_boundary_2d.json"
    mask, outer_curve, inner_curve = make_smooth_curve_mask(
        frame.size, outer_points, inner_points, adjustment, smooth_iterations=2
    )
    mask.save(mask_path)
    save_alpha(mask_path, alpha_path)
    save_overlay(frame_path, mask_path, overlay_path, "mediapipe")
    write_json(
        boundary_path,
        {
            "coordinateSpace": "frame_image_pixel_top_left",
            "outerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in outer_curve],
            "innerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in inner_curve],
            "source": "mediapipe",
            "generationMethod": "mediapipe_curve_fill",
            "adjustmentApplied": adjustment,
        },
    )
    outputs = {
        "mask": rel(mask_path),
        "alpha": rel(alpha_path),
        "overlay": rel(overlay_path),
        "boundary": rel(boundary_path),
        "points": rel(points_path),
    }
    warnings = list(provider.get("warnings", []))
    warnings.append("mediapipe_curve_fill_adjusted_from_landmarks")
    return outputs, warnings


def run_projection(
    fixture: dict[str, Any],
    provider: str,
    mask_path: str,
    run_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    output_dir = run_dir / f"{provider}_projection"
    script = ROOT / "scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py"
    mask_source = "vision_reference" if provider == "vision" else "contract_only"
    command = [
        sys.executable,
        str(script),
        str(repo_path(fixture["fusionSummaryPath"])),
        "--capture-pair",
        str(repo_path(fixture["framePath"]).parent),
        "--mask",
        str(repo_path(mask_path)),
        "--mask-source",
        mask_source,
        "--accepted-signal-id",
        f"{provider}_fixture_boundary",
        "--output-dir",
        str(output_dir),
        "--candidate-id",
        "lip-tight-auto-v0",
    ]
    if provider == "mediapipe":
        command.extend(
            [
                "--rejected-signal-reason",
                "mediapipe_fixture_not_gold_or_runtime_provider",
            ]
        )

    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    (run_dir / f"{provider}_projection_stdout.txt").write_text(
        completed.stdout or "", encoding="utf-8"
    )
    (run_dir / f"{provider}_projection_stderr.txt").write_text(
        completed.stderr or "", encoding="utf-8"
    )
    if completed.returncode != 0:
        return (
            {
                "status": "blocked",
                "command": command,
                "exitCode": completed.returncode,
                "stdoutPath": rel(run_dir / f"{provider}_projection_stdout.txt"),
                "stderrPath": rel(run_dir / f"{provider}_projection_stderr.txt"),
            },
            [f"projection_process_failed:{completed.returncode}"],
        )

    summary_path = output_dir / "summary.json"
    summary = normalize_projection_summary(read_json(summary_path))
    warnings = list(summary.get("warnings", []))
    warnings.extend(summary.get("blockers", []))
    return summary, warnings


def build_package(
    payload: dict[str, Any],
    fixture: dict[str, Any],
    run_dir: Path,
    provider: str,
    expression_mode: str,
    mask_outputs: dict[str, str],
    projection_summary: dict[str, Any],
    warnings: list[str],
) -> dict[str, Any]:
    generated_mask_id = safe_id(f"e7-generated-lip-{run_dir.name}-mask")
    frame_path = repo_path(fixture["framePath"])
    frame = Image.open(frame_path)
    uv_texture = projection_summary.get("artifacts", {}).get("lip_probability.png")
    round_trip = projection_summary.get("artifacts", {}).get("round_trip_overlay.png")
    mask_png_base64, mask_raw_rgba_base64, mask_width, mask_height = encode_texture_base64(
        uv_texture
    )
    runtime_payload = {
        "schemaVersion": "e7-generated-lip-mask-runtime-payload-v0",
        "generatedMaskId": generated_mask_id,
        "captureSetId": payload.get("captureSetId") or fixture["capturePairId"],
        "provider": provider,
        "expressionMode": expression_mode,
        "adjustment": payload["adjustment"],
        "maskTexturePath": uv_texture,
        "maskTextureId": generated_mask_id,
        "maskTextureEncoding": "raw_rgba_base64"
        if mask_raw_rgba_base64
        else "png_base64"
        if mask_png_base64
        else None,
        "maskPngBase64": mask_png_base64,
        "maskRawRgbaBase64": mask_raw_rgba_base64,
        "maskTextureWidth": mask_width,
        "maskTextureHeight": mask_height,
        "maskThreshold": 0.5,
        "maskFeatherUvNormalized": 0.07,
        "localOnly": True,
        "offDeviceUpload": False,
        "longTermRawFrameStored": False,
        "runtimeReady": False,
    }
    generated_package = {
        "schemaVersion": "e7-personalized-lip-generate-package-v0",
        "generatedMaskId": generated_mask_id,
        "captureSetId": payload.get("captureSetId") or fixture["capturePairId"],
        "provider": provider,
        "providerResults": {
            provider: {
                "status": "partial",
                "provider": provider,
                "capturePairId": fixture["capturePairId"],
                "captureShotKind": "fixture",
                "frameWidth": frame.width,
                "frameHeight": frame.height,
                "outerPointCount": len(read_json(repo_path(mask_outputs["boundary"])).get("outerPoints", [])),
                "innerPointCount": len(read_json(repo_path(mask_outputs["boundary"])).get("innerPoints", [])),
                "generationMethod": read_json(repo_path(mask_outputs["boundary"])).get("generationMethod"),
                "warnings": sorted(set(warnings)),
            }
        },
        "expressionMode": expression_mode,
        "blendshapeAssist": {
            "mode": expression_mode,
            "enabled": expression_mode == "blendshapeAssist",
            "source": "arface-blendshapes",
            "materialFeatherUvNormalized": 0.09
            if expression_mode == "blendshapeAssist"
            else 0.07,
            "warning": "fixture_blendshape_values_unavailable",
        },
        "adjustment": payload["adjustment"],
        "sourceFrameMetadata": {
            "capturePairId": fixture["capturePairId"],
            "framePath": fixture["framePath"],
            "frameWidth": frame.width,
            "frameHeight": frame.height,
            "orientation": "fixture_cgImagePropertyOrientationUp",
            "isMirrored": False,
        },
        "sourceFaceState": {
            "blendshapeAvailable": False,
            "warning": "fixture_blendshape_values_unavailable",
        },
        "lipBoundary2D": read_json(repo_path(mask_outputs["boundary"])),
        "uvMaskTexture": uv_texture,
        "uvCoverageMetadata": {
            "uvResolution": projection_summary.get("projectionStats", {}).get("uvResolution"),
            "coverageTexels": projection_summary.get("projectionStats", {}).get("coverageTexels"),
            "unknownTexels": projection_summary.get("projectionStats", {}).get("unknownTexels"),
            "roundTripKind": projection_summary.get("roundTripKind"),
            "roundTripScore": projection_summary.get("roundTripScore"),
        },
        "roundTripPreview": round_trip,
        "runtimeApplyPayload": runtime_payload,
        "qualityWarnings": sorted(set(warnings)),
        "createdAt": utc_now(),
        "privacyFlags": DEFAULT_PRIVACY,
        "buildlessOnly": True,
    }
    write_json(run_dir / "generated_lip_package.json", generated_package)
    return generated_package


def generate(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    blockers = validate_privacy(payload)
    if blockers:
        return 400, {"status": "blocked", "blockers": blockers}

    provider = payload.get("provider")
    if provider not in ("vision", "mediapipe"):
        return 400, {"status": "blocked", "blockers": ["unsupported_provider"]}
    expression_mode = payload.get("expressionMode") or "uvOnly"
    if expression_mode not in ("uvOnly", "blendshapeAssist"):
        return 400, {"status": "blocked", "blockers": ["unsupported_expressionMode"]}
    adjustment = payload.get("adjustment") or {}
    for key in ("cornerReach", "upperLipTightness", "lowerLipTightness", "verticalOffset"):
        if not isinstance(adjustment.get(key), (int, float)):
            return 400, {"status": "blocked", "blockers": [f"invalid_adjustment:{key}"]}

    fixture = find_fixture(payload.get("fixtureId"))
    run_dir = make_run_dir(payload.get("requestId") or f"generate-{utc_stamp()}", provider, expression_mode)
    write_json(run_dir / "request.json", redact_request_for_storage(payload))

    normalized = normalized_adjustment(payload)
    if provider == "vision":
        mask_outputs, provider_warnings = generate_vision_mask(fixture, run_dir, normalized)
    else:
        mask_outputs, provider_warnings = generate_mediapipe_mask(
            fixture, run_dir, normalized
        )

    projection_summary, projection_warnings = run_projection(
        fixture, provider, mask_outputs["mask"], run_dir
    )
    warnings = list(fixture.get("expectedWarnings", []))
    warnings.extend(provider_warnings)
    warnings.extend(projection_warnings)
    warnings.append("runtimeReady_false_until_Unity_iPhone_evidence")
    if expression_mode == "blendshapeAssist":
        warnings.append("blendshapeAssist_payload_only_until_runtime_values_available")

    generated_package = build_package(
        payload,
        fixture,
        run_dir,
        provider,
        expression_mode,
        mask_outputs,
        projection_summary,
        warnings,
    )
    uv_ready = bool(generated_package.get("uvMaskTexture")) and repo_path(
        generated_package["uvMaskTexture"]
    ).exists()
    round_trip_ready = bool(generated_package.get("roundTripPreview")) and repo_path(
        generated_package["roundTripPreview"]
    ).exists()
    projection_status = projection_summary.get("phase3ExecutionStatus")
    status = "blocked" if projection_status == "blocked" else "partial"
    result = {
        "status": status,
        "generatedMaskId": generated_package["generatedMaskId"],
        "provider": provider,
        "expressionMode": expression_mode,
        "uvMaskReady": uv_ready,
        "roundTripReady": round_trip_ready,
        "runtimeApplyReady": False,
        "warnings": sorted(set(warnings)),
        "runId": run_dir.name,
        "runDirectory": rel(run_dir),
        "maskOutputs": mask_outputs,
        "projectionSummary": projection_summary,
        "package": generated_package,
    }
    write_json(run_dir / "result.json", result)
    return 200, result


def compact_saved_record(package: dict[str, Any], save_dir: Path) -> dict[str, Any]:
    metadata_path = save_dir / "saved_record.json"
    preview = package.get("roundTripPreview")
    uv_texture = package.get("uvMaskTexture")
    return {
        "schemaVersion": "e7-lip-generate-saved-record-v0",
        "savedAt": utc_now(),
        "generatedMaskId": package.get("generatedMaskId"),
        "provider": package.get("provider"),
        "expressionMode": package.get("expressionMode"),
        "adjustment": package.get("adjustment"),
        "status": "saved_local_only",
        "packagePath": rel(save_dir / "generated_lip_package.json"),
        "metadataPath": rel(metadata_path),
        "roundTripPreview": preview,
        "uvMaskTexture": uv_texture,
        "privacyFlags": DEFAULT_PRIVACY,
        "runtimeReady": bool(
            package.get("runtimeApplyPayload", {}).get("runtimeReady", False)
        ),
    }


def save_generated_package(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    package_path_value = payload.get("packagePath")
    if not isinstance(package_path_value, str):
        return 400, {"status": "blocked", "blockers": ["missing_packagePath"]}

    try:
        package_path = ensure_run_artifact(package_path_value, "generated_lip_package.json")
    except (FileNotFoundError, ValueError) as exc:
        return 400, {"status": "blocked", "blockers": [str(exc)]}

    package = read_json(package_path)
    generated_mask_id = safe_id(str(package.get("generatedMaskId") or package_path.parent.name))
    requested_id = payload.get("generatedMaskId")
    if requested_id and requested_id != package.get("generatedMaskId"):
        return 400, {"status": "blocked", "blockers": ["generatedMaskId_mismatch"]}
    if package.get("privacyFlags") != DEFAULT_PRIVACY:
        return 400, {"status": "blocked", "blockers": ["privacyFlags_not_local_only"]}

    save_dir = SAVE_ROOT / generated_mask_id
    save_dir.mkdir(parents=True, exist_ok=True)
    target_package = save_dir / "generated_lip_package.json"
    shutil_copy(package_path, target_package)

    source_result_path = package_path.parent / "result.json"
    if source_result_path.exists():
        shutil_copy(source_result_path, save_dir / "result.json")

    record = compact_saved_record(package, save_dir)
    write_json(save_dir / "saved_record.json", record)
    return 200, {"status": "saved", "record": record}


def list_saved_packages() -> tuple[int, dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if SAVE_ROOT.exists():
        for record_path in sorted(SAVE_ROOT.glob("*/saved_record.json")):
            try:
                records.append(read_json(record_path))
            except json.JSONDecodeError:
                continue
    records.sort(key=lambda item: str(item.get("savedAt", "")), reverse=True)
    return 200, {
        "schemaVersion": "e7-lip-generate-saved-list-v0",
        "status": "ready",
        "records": records,
    }


def shutil_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


class LipGenerateHandler(BaseHTTPRequestHandler):
    server_version = "E7LipGenerateLocal/0.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def send_cors_headers(self) -> None:
        origin = self.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8789")

    def send_json(self, status_code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json(
                200,
                {
                    "status": "ok",
                    "localOnly": True,
                    "offDeviceUpload": False,
                    "longTermRawFrameStored": False,
                },
            )
            return
        if parsed.path == "/api/lip-mask/fixtures":
            self.send_json(200, load_inventory())
            return
        if parsed.path == "/api/lip-mask/saved":
            status_code, result = list_saved_packages()
            self.send_json(status_code, result)
            return
        if parsed.path.startswith("/api/lip-mask/runs/"):
            run_id = safe_id(parsed.path.rsplit("/", 1)[-1])
            result_path = RUN_ROOT / run_id / "result.json"
            if not result_path.exists():
                self.send_json(404, {"status": "blocked", "reason": "run_not_found"})
                return
            self.send_json(200, read_json(result_path))
            return
        if parsed.path == "/api/lip-mask/artifact":
            query = urllib.parse.parse_qs(parsed.query)
            artifact_path = query.get("path", [""])[0]
            try:
                path = repo_path(artifact_path)
            except ValueError as exc:
                self.send_json(400, {"status": "blocked", "reason": str(exc)})
                return
            if not is_allowed_artifact(path):
                self.send_json(
                    403,
                    {"status": "blocked", "reason": "artifact_path_not_allowed"},
                )
                return
            if not path.exists() or not path.is_file():
                self.send_json(404, {"status": "blocked", "reason": "artifact_not_found"})
                return
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_json(404, {"status": "blocked", "reason": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError as exc:
            self.send_json(400, {"status": "blocked", "reason": f"invalid_json:{exc}"})
            return
        if parsed.path in {
            "/api/lip-mask/generate",
            "/api/lip-mask/project-uv",
            "/api/lip-mask/round-trip",
        }:
            try:
                status_code, result = generate(payload)
            except Exception as exc:  # pragma: no cover - local diagnostic path.
                self.send_json(
                    500,
                    {
                        "status": "blocked",
                        "reason": f"{exc.__class__.__name__}:{exc}",
                    },
                )
                return
            self.send_json(status_code, result)
            return
        if parsed.path == "/api/lip-mask/save":
            status_code, result = save_generated_package(payload)
            self.send_json(status_code, result)
            return
        self.send_json(404, {"status": "blocked", "reason": "not_found"})


def smoke(host: str) -> int:
    server = ThreadingHTTPServer((host, 0), LipGenerateHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base_url = f"http://{host}:{port}"
    summary = {
        "schemaVersion": "e7-lip-generate-server-smoke-v0",
        "createdAtUtc": utc_now(),
        "baseUrl": base_url,
        "providers": {},
    }

    def post_json(path: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def generate_smoke(provider: str, label: str, adjustment: dict[str, float]) -> dict[str, Any]:
        payload = {
            "requestId": f"smoke-{label}-{provider}-{utc_stamp()}",
            "provider": provider,
            "expressionMode": "uvOnly",
            "adjustment": adjustment,
            "frameSource": "fixture",
            "fixtureId": "pair_face_20260622T143334Z_03",
            "privacy": DEFAULT_PRIVACY,
        }
        return post_json("/api/lip-mask/generate", payload)

    def mask_delta(a_path: str, b_path: str) -> int:
        a = np.asarray(Image.open(repo_path(a_path)).convert("L"), dtype=np.int16)
        b = np.asarray(Image.open(repo_path(b_path)).convert("L"), dtype=np.int16)
        if a.shape != b.shape:
            return -1
        return int(np.count_nonzero(np.abs(a - b) > 8))

    try:
        for provider in ("vision", "mediapipe"):
            baseline = generate_smoke(
                provider,
                "baseline",
                {
                    "cornerReach": 0,
                    "upperLipTightness": 0,
                    "lowerLipTightness": 0,
                    "verticalOffset": 0,
                },
            )
            adjusted = generate_smoke(
                provider,
                "adjusted",
                {
                    "cornerReach": 0.35,
                    "upperLipTightness": -0.25,
                    "lowerLipTightness": 0.25,
                    "verticalOffset": -0.2,
                },
            )
            delta = mask_delta(
                baseline.get("maskOutputs", {}).get("mask", ""),
                adjusted.get("maskOutputs", {}).get("mask", ""),
            )
            save_result = post_json(
                "/api/lip-mask/save",
                {
                    "generatedMaskId": adjusted.get("generatedMaskId"),
                    "packagePath": f"{adjusted.get('runDirectory')}/generated_lip_package.json",
                },
            )
            summary["providers"][provider] = {
                "status": adjusted.get("status"),
                "uvMaskReady": adjusted.get("uvMaskReady"),
                "roundTripReady": adjusted.get("roundTripReady"),
                "runDirectory": adjusted.get("runDirectory"),
                "baselineRunDirectory": baseline.get("runDirectory"),
                "adjustedMaskDeltaPixels": delta,
                "generationMethod": adjusted.get("package", {})
                .get("lipBoundary2D", {})
                .get("generationMethod"),
                "saveStatus": save_result.get("status"),
                "savedPackagePath": save_result.get("record", {}).get("packagePath"),
                "warningCount": len(adjusted.get("warnings", [])),
            }
    finally:
        server.shutdown()
        thread.join(timeout=5)

    summary["status"] = (
        "partial"
        if all(
            item.get("uvMaskReady")
            and item.get("roundTripReady")
            and item.get("adjustedMaskDeltaPixels", 0) > 0
            and item.get("saveStatus") == "saved"
            for item in summary["providers"].values()
        )
        else "blocked"
    )
    output_dir = RUN_ROOT / f"smoke-{int(time.time())}"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "smoke_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "partial" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local E7 lip Generate server.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.host not in ("127.0.0.1", "localhost"):
        raise SystemExit("This local-only server must bind to 127.0.0.1 or localhost.")
    if args.smoke:
        return smoke("127.0.0.1")

    server = ThreadingHTTPServer((args.host, args.port), LipGenerateHandler)
    print(f"E7 lip Generate local server listening on http://{args.host}:{args.port}")
    print("localOnly=true offDeviceUpload=false longTermRawFrameStored=false")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
