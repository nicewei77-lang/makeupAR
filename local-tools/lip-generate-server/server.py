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
import shutil
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


def make_polygon_mask(
    frame_size: tuple[int, int],
    outer_points: list[tuple[float, float]],
    inner_points: list[tuple[float, float]],
) -> Image.Image:
    mask = Image.new("L", frame_size, 0)
    draw = ImageDraw.Draw(mask)
    if outer_points:
        draw.polygon(outer_points, fill=255)
    if inner_points:
        draw.polygon(inner_points, fill=0)
    return mask


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


def generate_vision_mask(fixture: dict[str, Any], run_dir: Path) -> tuple[dict[str, Any], list[str]]:
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
    make_polygon_mask(frame.size, outer_points, inner_points).save(mask_path)
    save_alpha(mask_path, alpha_path)
    save_overlay(frame_path, mask_path, overlay_path, "vision")
    boundary = {
        "coordinateSpace": "frame_image_pixel_top_left",
        "outerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in outer_points],
        "innerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in inner_points],
        "source": "vision",
    }
    write_json(boundary_path, boundary)
    outputs = {
        "mask": rel(mask_path),
        "alpha": rel(alpha_path),
        "overlay": rel(overlay_path),
        "boundary": rel(boundary_path),
        "contour": rel(contour_path),
    }
    return outputs, provider.get("warnings", [])


def generate_mediapipe_mask(fixture: dict[str, Any], run_dir: Path) -> tuple[dict[str, Any], list[str]]:
    provider = fixture["providers"]["mediapipe"]
    frame_path = repo_path(fixture["framePath"])
    source_mask_path = repo_path(provider["maskPath"])
    points_path = repo_path(provider["pointsPath"])
    points = read_json(points_path)
    outer_points, inner_points = points_from_mediapipe(points)

    mask_path = run_dir / "mediapipe_lip_mask.png"
    alpha_path = run_dir / "mediapipe_lip_alpha.png"
    overlay_path = run_dir / "mediapipe_lip_overlay.png"
    boundary_path = run_dir / "mediapipe_lip_boundary_2d.json"
    shutil.copyfile(source_mask_path, mask_path)
    save_alpha(mask_path, alpha_path)
    save_overlay(frame_path, mask_path, overlay_path, "mediapipe")
    write_json(
        boundary_path,
        {
            "coordinateSpace": "frame_image_pixel_top_left",
            "outerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in outer_points],
            "innerPoints": [{"x": round(x, 3), "y": round(y, 3)} for x, y in inner_points],
            "source": "mediapipe",
        },
    )
    outputs = {
        "mask": rel(mask_path),
        "alpha": rel(alpha_path),
        "overlay": rel(overlay_path),
        "boundary": rel(boundary_path),
        "points": rel(points_path),
    }
    return outputs, provider.get("warnings", [])


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
        "provider": provider,
        "expressionMode": expression_mode,
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

    if provider == "vision":
        mask_outputs, provider_warnings = generate_vision_mask(fixture, run_dir)
    else:
        mask_outputs, provider_warnings = generate_mediapipe_mask(fixture, run_dir)

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
    try:
        for provider in ("vision", "mediapipe"):
            payload = {
                "requestId": f"smoke-{utc_stamp()}",
                "provider": provider,
                "expressionMode": "uvOnly",
                "adjustment": {
                    "cornerReach": 0,
                    "upperLipTightness": 0,
                    "lowerLipTightness": 0,
                    "verticalOffset": 0,
                },
                "frameSource": "fixture",
                "fixtureId": "pair_face_20260622T143334Z_03",
                "privacy": DEFAULT_PRIVACY,
            }
            request = urllib.request.Request(
                f"{base_url}/api/lip-mask/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
            summary["providers"][provider] = {
                "status": data.get("status"),
                "uvMaskReady": data.get("uvMaskReady"),
                "roundTripReady": data.get("roundTripReady"),
                "runDirectory": data.get("runDirectory"),
                "warningCount": len(data.get("warnings", [])),
            }
    finally:
        server.shutdown()
        thread.join(timeout=5)

    summary["status"] = (
        "partial"
        if all(item.get("uvMaskReady") and item.get("roundTripReady") for item in summary["providers"].values())
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
