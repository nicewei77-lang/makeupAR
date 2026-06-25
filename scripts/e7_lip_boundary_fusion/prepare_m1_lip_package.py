#!/usr/bin/env python3
"""Build or block an M1 buildless personalized lip package.

M1 is allowed to generate a mesh-derived draft from the current ARFace export,
but it must not silently promote that draft into a reference/gold mask. A
screen-space reference mask must come from an explicit reproducible input:
either a mask file plus metadata or a polygon JSON file. Without that input the
script stops with blocked_review_needed after writing draft/audit artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


SCRIPT_VERSION = "m1-lip-package-repair-v1"
DEFAULT_CAPTURE_PAIR = Path(
    "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03"
)
EXPECTED_CANDIDATES = ("lip-tight-auto-v0", "lip-tight-user-v0", "lip-safe-v0")


@dataclass(frozen=True)
class LipRingConfig:
    variant_id: str = "lip-ring-v0-balanced"
    label_group: str = "lip_ring"
    center_x: float = 0.0
    center_y: float = -0.036
    radius_x: float = 0.050
    radius_y: float = 0.022
    vertex_padding_x: float = 0.007
    vertex_padding_y: float = 0.005
    min_vertex_hits: int = 2
    source: str = "historical_e7_arface_authored_atlas_config"
    source_commit: str = "089c210"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare M1 buildless personalized lip package v0 artifacts."
    )
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output folder. Defaults to evidence/e7-lip-m1-packages/m1-lip-repair-<UTC>.",
    )
    parser.add_argument(
        "--reference-mask",
        type=Path,
        default=None,
        help="Existing screen-space lip reference mask to consume.",
    )
    parser.add_argument(
        "--reference-mask-meta",
        type=Path,
        default=None,
        help="Metadata JSON for --reference-mask.",
    )
    parser.add_argument(
        "--reference-polygon-json",
        type=Path,
        default=None,
        help="Polygon JSON containing polygonPoints/points to rasterize as lip_reference_mask.png.",
    )
    parser.add_argument(
        "--run-apple-vision",
        action="store_true",
        help="Run the local Apple Vision lip contour extractor for the same frame.",
    )
    parser.add_argument(
        "--apple-vision-contour-json",
        type=Path,
        default=None,
        help="Existing apple_vision_lip_contour.json to copy into the package instead of running Vision.",
    )
    parser.add_argument(
        "--apple-vision-script",
        type=Path,
        default=Path("scripts/e7_lip_boundary_fusion/extract_apple_vision_lip_contour.swift"),
        help="Swift Apple Vision extractor script path.",
    )
    parser.add_argument("--apple-vision-min-confidence", type=float, default=0.35)
    parser.add_argument(
        "--run-face-parsing",
        action="store_true",
        help="Run the local/offline face parsing runner for the same frame.",
    )
    parser.add_argument(
        "--face-parsing-dir",
        type=Path,
        default=None,
        help="Existing directory containing real face_parsing_* artifacts to consume.",
    )
    parser.add_argument(
        "--face-parsing-script",
        type=Path,
        default=Path("scripts/e7_lip_boundary_fusion/run_face_parsing.py"),
        help="Local/offline face parsing runner script path.",
    )
    parser.add_argument(
        "--face-parsing-checkpoint",
        type=Path,
        default=Path("evidence/e7-lip-m1-models/face-parsing-pytorch/79999_iter.pth"),
        help="Pretrained face parsing checkpoint path.",
    )
    parser.add_argument("--face-parsing-min-lip-pixels", type=int, default=64)
    parser.add_argument(
        "--color-gradient-script",
        type=Path,
        default=Path("scripts/e7_lip_boundary_fusion/compute_color_gradient_confidence.py"),
        help="Buildless color/gradient confidence script path.",
    )
    parser.add_argument(
        "--skip-color-gradient",
        action="store_true",
        help="Leave colorGradientConfidence as required_not_run.",
    )
    parser.add_argument(
        "--inner-mouth-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument(
        "--corner-falloff-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument(
        "--upper-lower-status",
        choices=("available", "contract_only", "missing"),
        default="contract_only",
    )
    parser.add_argument("--uv-resolution", type=int, default=512)
    parser.add_argument("--sample-stride", type=int, default=1)
    parser.add_argument("--render-stride", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--skip-round-trip", action="store_true")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path | None, base: Path) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)


def export_arrays(export: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    local_vertices = np.asarray(export.get("localVertices", []), dtype=np.float64)
    screen_vertices = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    uvs = np.asarray(export.get("uvs", []), dtype=np.float64)
    indices = np.asarray(export.get("indices", []), dtype=np.int32)
    if indices.ndim != 1:
        indices = indices.reshape(-1)
    return local_vertices, screen_vertices, uvs, indices


def inside_ellipse(points: np.ndarray, cx: float, cy: float, rx: float, ry: float) -> np.ndarray:
    safe_rx = max(rx, 0.0001)
    safe_ry = max(ry, 0.0001)
    return (((points[:, 0] - cx) / safe_rx) ** 2) + (((points[:, 1] - cy) / safe_ry) ** 2) <= 1.0


def select_lip_triangles(
    local_vertices: np.ndarray, indices: np.ndarray, config: LipRingConfig
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    usable = (len(indices) // 3) * 3
    triangles = indices[:usable].reshape(-1, 3)
    valid = np.all((triangles >= 0) & (triangles < len(local_vertices)), axis=1)
    triangles = triangles[valid]
    padded_inside = inside_ellipse(
        local_vertices,
        config.center_x,
        config.center_y,
        config.radius_x + config.vertex_padding_x,
        config.radius_y + config.vertex_padding_y,
    )
    centroids = local_vertices[triangles].mean(axis=1)
    centroid_inside = inside_ellipse(
        centroids,
        config.center_x,
        config.center_y,
        config.radius_x,
        config.radius_y,
    )
    label_hits = padded_inside[triangles].sum(axis=1)
    selected = centroid_inside & (label_hits >= config.min_vertex_hits)
    return triangles, selected, padded_inside


def rasterize_triangles(
    frame_size: tuple[int, int],
    screen_vertices: np.ndarray,
    triangles: np.ndarray,
    selected: np.ndarray,
) -> Image.Image:
    mask = Image.new("L", frame_size, 0)
    draw = ImageDraw.Draw(mask)
    for tri in triangles[selected]:
        draw.polygon(
            [(float(screen_vertices[index, 0]), float(screen_vertices[index, 1])) for index in tri],
            fill=255,
        )
    return mask


def mask_overlay(frame: Image.Image, mask: Image.Image, outline_width: int = 5) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    mask_array = np.asarray(mask) > 0
    base[mask_array] = (base[mask_array] * 0.50) + (np.array([255, 43, 118]) * 0.50)
    dilated = mask.filter(ImageFilter.MaxFilter(outline_width))
    eroded = mask.filter(ImageFilter.MinFilter(outline_width))
    outline = np.asarray(ImageChops.subtract(dilated, eroded)) > 0
    base[outline] = np.array([255, 215, 0], dtype=np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def projected_bbox(screen_vertices: np.ndarray, triangles: np.ndarray, selected: np.ndarray) -> dict[str, Any]:
    if not np.any(selected):
        return {"available": False}
    vertex_ids = np.unique(triangles[selected].reshape(-1))
    points = screen_vertices[vertex_ids, :2]
    return {
        "available": True,
        "minX": round(float(points[:, 0].min()), 3),
        "minY": round(float(points[:, 1].min()), 3),
        "maxX": round(float(points[:, 0].max()), 3),
        "maxY": round(float(points[:, 1].max()), 3),
        "width": round(float(points[:, 0].max() - points[:, 0].min()), 3),
        "height": round(float(points[:, 1].max() - points[:, 1].min()), 3),
        "projectedVertexCount": int(len(vertex_ids)),
    }


def normalize_points(raw: Any) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    if not isinstance(raw, list):
        return points
    for item in raw:
        if isinstance(item, dict):
            x = item.get("x")
            y = item.get("y")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            x, y = item[0], item[1]
        else:
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            points.append((int(round(x)), int(round(y))))
    return points


def build_reference_from_polygon(
    polygon_path: Path,
    frame: Image.Image,
    output_dir: Path,
) -> tuple[Path, dict[str, Any], list[str]]:
    blockers: list[str] = []
    polygon = load_json(polygon_path)
    points = normalize_points(polygon.get("polygonPoints") or polygon.get("points"))
    if len(points) < 3:
        blockers.append("reference_polygon_needs_at_least_three_points")
    mask = Image.new("L", frame.size, 0)
    if not blockers:
        draw = ImageDraw.Draw(mask)
        draw.polygon(points, fill=255)
        mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    mask_path = output_dir / "lip_reference_mask.png"
    mask.save(mask_path)
    positive = int(np.count_nonzero(np.asarray(mask)))
    accepted = bool(polygon.get("acceptedAsGold", False))
    source = str(polygon.get("maskSource") or polygon.get("source") or "reference_polygon_json")
    review_status = str(
        polygon.get("reviewStatus")
        or ("human_reviewed_gold" if accepted else "needs_user_review_before_gold")
    )
    reviewed_by = str(polygon.get("reviewedBy") or "unknown_reviewer")
    accepted_signal_ids = polygon.get("acceptedSignalIds") or ["reference_polygon_json"]
    meta = {
        "schemaVersion": "e7-lip-reference-mask-meta-v0",
        "capturePairId": polygon.get("capturePairId"),
        "maskPath": "lip_reference_mask.png",
        "coordinateSpace": polygon.get("coordinateSpace", "frame_image_pixel_top_left"),
        "maskSource": source,
        "sourceType": "reference_polygon_json",
        "sourcePath": str(polygon_path),
        "sourceSha256": sha256_file(polygon_path),
        "acceptedSignalIds": accepted_signal_ids,
        "reviewedBy": reviewed_by,
        "acceptedAsGold": accepted,
        "reviewStatus": review_status,
        "imageWidth": frame.width,
        "imageHeight": frame.height,
        "positivePixels": positive,
        "coverageRatio": round(positive / float(frame.width * frame.height), 6),
        "polygonPoints": points,
        "knownWeaknesses": polygon.get("knownWeaknesses", []),
        "reproducible": True,
    }
    return mask_path, meta, blockers


def build_reference_from_mask(
    mask_path: Path,
    meta_path: Path | None,
    frame: Image.Image,
    output_dir: Path,
) -> tuple[Path, dict[str, Any], list[str]]:
    blockers: list[str] = []
    source_meta = load_json(meta_path) if meta_path and meta_path.exists() else {}
    image = Image.open(mask_path).convert("L")
    if image.size != frame.size:
        blockers.append(f"reference_mask_size_mismatch:mask={image.size},frame={frame.size}")
    output_mask = output_dir / "lip_reference_mask.png"
    image.save(output_mask)
    positive = int(np.count_nonzero(np.asarray(image) > 0))
    if positive == 0:
        blockers.append("reference_mask_empty")
    accepted = bool(source_meta.get("acceptedAsGold", False))
    review_status = str(
        source_meta.get("reviewStatus")
        or ("human_reviewed_gold" if accepted else "needs_user_review_before_gold")
    )
    meta = {
        "schemaVersion": "e7-lip-reference-mask-meta-v0",
        "capturePairId": source_meta.get("capturePairId"),
        "maskPath": "lip_reference_mask.png",
        "coordinateSpace": source_meta.get("coordinateSpace", "frame_image_pixel_top_left"),
        "maskSource": source_meta.get("maskSource", "external_reference_mask"),
        "sourceType": "reference_mask_file",
        "sourcePath": str(mask_path),
        "sourceSha256": sha256_file(mask_path),
        "sourceMetaPath": str(meta_path) if meta_path else None,
        "sourceMetaSha256": sha256_file(meta_path) if meta_path and meta_path.exists() else None,
        "acceptedSignalIds": source_meta.get("acceptedSignalIds", ["reference_mask_file"]),
        "reviewedBy": source_meta.get("reviewedBy", "unknown_reviewer"),
        "acceptedAsGold": accepted,
        "reviewStatus": review_status,
        "imageWidth": frame.width,
        "imageHeight": frame.height,
        "positivePixels": positive,
        "coverageRatio": round(positive / float(frame.width * frame.height), 6),
        "knownWeaknesses": source_meta.get("knownWeaknesses", []),
        "reproducible": True,
    }
    return output_mask, meta, blockers


def contour_points(vision: dict[str, Any], contour_id: str) -> list[tuple[float, float]]:
    contour = vision.get("contours", {}).get(contour_id, {})
    points = []
    for point in contour.get("imagePoints", []):
        if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(
            point.get("y"), (int, float)
        ):
            points.append((float(point["x"]), float(point["y"])))
    return points


def draw_polyline(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], width: int) -> None:
    if len(points) < 2:
        return
    draw.line(points + [points[0]], fill=color, width=width, joint="curve")


def write_vision_overlay(frame: Image.Image, vision: dict[str, Any], output_dir: Path) -> str | None:
    outer = contour_points(vision, "outerLips")
    inner = contour_points(vision, "innerLips")
    if not outer and not inner:
        return None
    overlay = frame.copy()
    draw = ImageDraw.Draw(overlay)
    draw_polyline(draw, outer, (255, 43, 118), 6)
    draw_polyline(draw, inner, (255, 214, 80), 5)
    path = output_dir / "apple_vision_lip_contour_overlay.png"
    overlay.save(path)
    return path.name


def unavailable_vision(reason: str, frame_path: Path, capture_pair_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-apple-vision-lip-contour-v0",
        "createdAtUtc": utc_now(),
        "status": "unavailable",
        "unavailableReason": reason,
        "capturePairId": capture_pair_id,
        "sourceFramePath": str(frame_path),
        "sourceFrameSha256": sha256_file(frame_path) if frame_path.exists() else None,
        "requiredForM1Ready": True,
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
    }


def prepare_apple_vision_contour(
    args: argparse.Namespace,
    repo_root: Path,
    frame_path: Path,
    frame: Image.Image,
    output_dir: Path,
    capture_pair_id: str,
) -> dict[str, Any] | None:
    output_json = output_dir / "apple_vision_lip_contour.json"
    run_log = output_dir / "apple_vision_lip_contour_run.json"

    if args.apple_vision_contour_json:
        source = args.apple_vision_contour_json.resolve()
        if not source.exists():
            vision = unavailable_vision(f"provided_contour_json_missing:{source}", frame_path, capture_pair_id)
            write_json(output_json, vision)
        else:
            vision = load_json(source)
            if source != output_json.resolve():
                write_json(output_json, vision)
    elif args.run_apple_vision:
        script = args.apple_vision_script.resolve()
        if not script.exists():
            vision = unavailable_vision(f"apple_vision_script_missing:{script}", frame_path, capture_pair_id)
            write_json(output_json, vision)
        else:
            command = [
                "xcrun",
                "swift",
                str(script),
                "--image",
                str(frame_path),
                "--output-json",
                str(output_json),
                "--capture-pair-id",
                capture_pair_id,
                "--min-confidence",
                str(args.apple_vision_min_confidence),
            ]
            cache_dir = output_dir / ".swift-module-cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["CLANG_MODULE_CACHE_PATH"] = str(cache_dir)
            env["SWIFT_MODULE_CACHE_PATH"] = str(cache_dir)
            completed = subprocess.run(
                command,
                cwd=str(repo_root),
                text=True,
                capture_output=True,
                env=env,
            )
            write_json(
                run_log,
                {
                    "schemaVersion": "e7-apple-vision-run-log-v0",
                    "createdAtUtc": utc_now(),
                    "command": command,
                    "returnCode": completed.returncode,
                    "moduleCachePath": str(cache_dir),
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                    "localOnly": True,
                },
            )
            if output_json.exists():
                vision = load_json(output_json)
            else:
                vision = unavailable_vision(
                    f"apple_vision_extractor_failed:{completed.returncode}",
                    frame_path,
                    capture_pair_id,
                )
                write_json(output_json, vision)
    else:
        return None

    overlay = write_vision_overlay(frame, vision, output_dir)
    if overlay:
        vision["overlayPath"] = overlay
        write_json(output_json, vision)
    return vision


def vision_capture_payload(vision: dict[str, Any] | None) -> dict[str, Any]:
    if not vision:
        return {
            "status": "required_not_run",
            "confidence": None,
            "requiredForM1Ready": True,
        }
    contours = vision.get("contours", {})
    outer = contours.get("outerLips", {})
    inner = contours.get("innerLips", {})
    return {
        "status": vision.get("status", "unavailable"),
        "source": "apple_vision_vndetectfacelandmarksrequest",
        "coordinateSpace": "frame_image_pixel_top_left",
        "visionCoordinateSpace": "face_bbox_normalized_bottom_left",
        "confidence": vision.get("confidence"),
        "contourJsonPath": "apple_vision_lip_contour.json",
        "overlayPath": vision.get("overlayPath"),
        "outerLipPointCount": outer.get("pointCount", 0),
        "innerLipPointCount": inner.get("pointCount", 0),
        "outerLipImageBounds": outer.get("imageBounds"),
        "innerLipImageBounds": inner.get("imageBounds"),
        "unavailableReason": vision.get("unavailableReason"),
        "requiredForM1Ready": True,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
    }


def unavailable_face_parsing(reason: str, frame_path: Path, capture_pair_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-face-parsing-labels-v0",
        "createdAtUtc": utc_now(),
        "status": "unavailable",
        "unavailableReason": reason,
        "capturePairId": capture_pair_id,
        "sourceFramePath": str(frame_path),
        "sourceFrameSha256": sha256_file(frame_path) if frame_path.exists() else None,
        "requiredForM1Ready": True,
        "localOnly": True,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
    }


def required_face_parsing_artifacts() -> tuple[str, ...]:
    return (
        "face_parsing_labels.json",
        "face_parsing_lip_mask.png",
        "face_parsing_upper_lip_mask.png",
        "face_parsing_lower_lip_mask.png",
        "face_parsing_inner_mouth_mask.png",
        "face_parsing_overlay.png",
        "face_parsing_confidence.json",
    )


def copy_face_parsing_artifacts(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    missing = []
    for name in required_face_parsing_artifacts():
        source = source_dir / name
        if not source.exists():
            missing.append(name)
            continue
        destination = output_dir / name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
    if missing:
        return unavailable_face_parsing(
            "provided_face_parsing_dir_missing_artifacts:" + ",".join(missing),
            output_dir / "frame.png",
            "unknown_capture",
        )
    return load_json(output_dir / "face_parsing_labels.json")


def prepare_face_parsing_artifacts(
    args: argparse.Namespace,
    repo_root: Path,
    frame_path: Path,
    export_path: Path,
    output_dir: Path,
    capture_pair_id: str,
) -> dict[str, Any] | None:
    output_json = output_dir / "face_parsing_labels.json"
    run_log = output_dir / "face_parsing_run.json"

    if args.face_parsing_dir:
        face_parsing = copy_face_parsing_artifacts(args.face_parsing_dir.resolve(), output_dir)
        if face_parsing.get("capturePairId") in {None, "unknown_capture"}:
            face_parsing["capturePairId"] = capture_pair_id
            write_json(output_json, face_parsing)
        return face_parsing

    if not args.run_face_parsing:
        return None

    script = args.face_parsing_script.resolve()
    checkpoint = args.face_parsing_checkpoint.resolve()
    if not script.exists():
        face_parsing = unavailable_face_parsing(
            f"face_parsing_script_missing:{script}", frame_path, capture_pair_id
        )
        write_json(output_json, face_parsing)
        return face_parsing
    if not checkpoint.exists():
        face_parsing = unavailable_face_parsing(
            f"face_parsing_checkpoint_missing:{checkpoint}", frame_path, capture_pair_id
        )
        write_json(output_json, face_parsing)
        return face_parsing

    command = [
        sys.executable,
        str(script),
        "--image",
        str(frame_path),
        "--checkpoint",
        str(checkpoint),
        "--output-dir",
        str(output_dir),
        "--capture-pair-id",
        capture_pair_id,
        "--arface-export",
        str(export_path),
        "--min-lip-pixels",
        str(args.face_parsing_min_lip_pixels),
    ]
    completed = subprocess.run(command, cwd=str(repo_root), text=True, capture_output=True)
    write_json(
        run_log,
        {
            "schemaVersion": "e7-face-parsing-run-log-v0",
            "createdAtUtc": utc_now(),
            "command": command,
            "returnCode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "localOnly": True,
        },
    )
    if output_json.exists():
        return load_json(output_json)
    face_parsing = unavailable_face_parsing(
        f"face_parsing_runner_failed:{completed.returncode}", frame_path, capture_pair_id
    )
    write_json(output_json, face_parsing)
    return face_parsing


def face_parsing_capture_payload(face_parsing: dict[str, Any] | None) -> dict[str, Any]:
    if not face_parsing:
        return {
            "status": "required_not_run",
            "labels": [],
            "localOnly": True,
            "requiredForM1Ready": True,
        }
    labels = face_parsing.get("requiredLabels", {})
    pixel_counts = {
        name: detail.get("pixelCount")
        for name, detail in labels.items()
        if isinstance(detail, dict)
    }
    present_labels = [
        name
        for name, detail in labels.items()
        if isinstance(detail, dict) and int(detail.get("pixelCount", 0)) > 0
    ]
    artifacts = face_parsing.get("artifacts", {})
    return {
        "status": face_parsing.get("status", "unavailable"),
        "labels": present_labels,
        "labelSet": face_parsing.get("labelSet"),
        "localOnly": bool(face_parsing.get("localOnly", True)),
        "requiredForM1Ready": True,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
        "lipMaskPath": artifacts.get("lipMask", "face_parsing_lip_mask.png"),
        "upperLipMaskPath": artifacts.get("upperLipMask", "face_parsing_upper_lip_mask.png"),
        "lowerLipMaskPath": artifacts.get("lowerLipMask", "face_parsing_lower_lip_mask.png"),
        "innerMouthMaskPath": artifacts.get("innerMouthMask", "face_parsing_inner_mouth_mask.png"),
        "overlayPath": artifacts.get("overlay", "face_parsing_overlay.png"),
        "confidencePath": "face_parsing_confidence.json",
        "requiredLabels": labels,
        "pixelCounts": pixel_counts,
        "meanLipConfidence": None,
        "unavailableReason": face_parsing.get("unavailableReason"),
        "failureReasons": face_parsing.get("failureReasons", []),
    }


def unavailable_color_gradient(reason: str, frame_path: Path, capture_pair_id: str) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-lip-color-gradient-confidence-v0",
        "createdAtUtc": utc_now(),
        "status": "unavailable",
        "unavailableReason": reason,
        "capturePairId": capture_pair_id,
        "sourceFramePath": str(frame_path),
        "sourceFrameSha256": sha256_file(frame_path) if frame_path.exists() else None,
        "requiredForM1Ready": True,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
        "recommendedUse": "confidence_only_never_boundary_source",
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
    }


def prepare_color_gradient_confidence(
    args: argparse.Namespace,
    repo_root: Path,
    frame_path: Path,
    output_dir: Path,
    capture_pair_id: str,
) -> dict[str, Any] | None:
    output_json = output_dir / "color_gradient_confidence.json"
    run_log = output_dir / "color_gradient_run.json"
    if args.skip_color_gradient:
        return None

    script = args.color_gradient_script.resolve()
    lip_mask = output_dir / "lip_reference_mask.png"
    if not script.exists():
        color = unavailable_color_gradient(f"color_gradient_script_missing:{script}", frame_path, capture_pair_id)
        write_json(output_json, color)
        return color
    if not lip_mask.exists():
        color = unavailable_color_gradient("lip_reference_mask_missing", frame_path, capture_pair_id)
        write_json(output_json, color)
        return color

    command = [
        sys.executable,
        str(script),
        "--frame",
        str(frame_path),
        "--lip-mask",
        str(lip_mask),
        "--output-dir",
        str(output_dir),
        "--capture-pair-id",
        capture_pair_id,
    ]
    optional_inputs = [
        ("--face-parsing-lip", output_dir / "face_parsing_lip_mask.png"),
        ("--face-parsing-skin", output_dir / "face_parsing_skin_mask.png"),
        ("--vision-contour", output_dir / "apple_vision_lip_contour.json"),
    ]
    for flag, path in optional_inputs:
        if path.exists():
            command.extend([flag, str(path)])

    completed = subprocess.run(command, cwd=str(repo_root), text=True, capture_output=True)
    write_json(
        run_log,
        {
            "schemaVersion": "e7-color-gradient-run-log-v0",
            "createdAtUtc": utc_now(),
            "command": command,
            "returnCode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "localOnly": True,
        },
    )
    if output_json.exists():
        return load_json(output_json)
    color = unavailable_color_gradient(f"color_gradient_runner_failed:{completed.returncode}", frame_path, capture_pair_id)
    write_json(output_json, color)
    return color


def color_gradient_capture_payload(color_gradient: dict[str, Any] | None) -> dict[str, Any]:
    if not color_gradient:
        return {
            "status": "required_not_run",
            "summary": "required_for_m1_ready",
        }
    return {
        "status": color_gradient.get("status", "unavailable"),
        "source": color_gradient.get("source"),
        "requiredForM1Ready": True,
        "runtimePrimaryTracker": bool(color_gradient.get("runtimePrimaryTracker", False)),
        "derivedEvidenceOnly": bool(color_gradient.get("derivedEvidenceOnly", True)),
        "recommendedUse": color_gradient.get(
            "recommendedUse", "confidence_only_never_boundary_source"
        ),
        "confidenceScore": color_gradient.get("confidenceScore"),
        "lipSkinDelta": color_gradient.get("lipSkinDelta"),
        "lumaDelta": color_gradient.get("lumaDelta"),
        "chromaDelta": color_gradient.get("chromaDelta"),
        "edgeGradientMean": color_gradient.get("edgeGradientMean"),
        "boundaryHighlightFraction": color_gradient.get("boundaryHighlightFraction"),
        "skinDarkFraction": color_gradient.get("skinDarkFraction"),
        "faceParsingLipReferenceIoU": color_gradient.get("faceParsingLipReferenceIoU"),
        "lowContrastWarning": bool(color_gradient.get("lowContrastWarning", False)),
        "shadowWarning": bool(color_gradient.get("shadowWarning", False)),
        "specularWarning": bool(color_gradient.get("specularWarning", False)),
        "warnings": color_gradient.get("warnings", []),
        "jsonPath": "color_gradient_confidence.json",
        "overlayPath": color_gradient.get("overlayPath", "color_gradient_overlay.png"),
        "unavailableReason": color_gradient.get("unavailableReason"),
    }


def count_mask_pixels(path: Path) -> int:
    if not path.exists():
        return 0
    return int(np.count_nonzero(np.asarray(Image.open(path).convert("L")) > 0))


def effective_region_statuses(
    args: argparse.Namespace, face_parsing: dict[str, Any] | None, output_dir: Path
) -> None:
    if not face_parsing or face_parsing.get("status") != "silver":
        return
    if count_mask_pixels(output_dir / "face_parsing_inner_mouth_mask.png") > 0:
        args.inner_mouth_status = "available"
    if (
        count_mask_pixels(output_dir / "face_parsing_upper_lip_mask.png") > 0
        and count_mask_pixels(output_dir / "face_parsing_lower_lip_mask.png") > 0
    ):
        args.upper_lower_status = "available"


def binary_mask(path: Path) -> Image.Image:
    image = Image.open(path).convert("L")
    return image.point(lambda value: 255 if value > 0 else 0)


def write_candidate_mask(path: Path, image: Image.Image) -> int:
    image.save(path)
    return int(np.count_nonzero(np.asarray(image) > 0))


def apply_face_parsing_to_reference(
    output_dir: Path,
    frame: Image.Image,
    reference_meta: dict[str, Any],
    face_parsing: dict[str, Any] | None,
) -> dict[str, Any]:
    if not face_parsing or face_parsing.get("status") != "silver":
        return reference_meta
    reference_path = output_dir / "lip_reference_mask.png"
    lip_path = output_dir / "face_parsing_lip_mask.png"
    inner_path = output_dir / "face_parsing_inner_mouth_mask.png"
    if not reference_path.exists() or not lip_path.exists():
        return reference_meta

    before_path = output_dir / "lip_reference_mask_before_face_parsing.png"
    shutil.copy2(reference_path, before_path)
    reference = binary_mask(reference_path)
    parsing_lip = binary_mask(lip_path)
    parsing_lip_expanded = parsing_lip.filter(ImageFilter.MaxFilter(17))
    fused = ImageChops.multiply(reference, parsing_lip_expanded)
    inner_pixels = 0
    if inner_path.exists():
        parsing_inner = binary_mask(inner_path).filter(ImageFilter.MaxFilter(9))
        inner_pixels = int(np.count_nonzero(np.asarray(parsing_inner) > 0))
        fused = ImageChops.subtract(fused, parsing_inner)
    fused = fused.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    before_pixels = int(np.count_nonzero(np.asarray(reference) > 0))
    parsing_pixels = int(np.count_nonzero(np.asarray(parsing_lip) > 0))
    fused_pixels = int(np.count_nonzero(np.asarray(fused) > 0))
    if fused_pixels < max(64, int(before_pixels * 0.10)):
        # Keep the reference mask if intersection is implausibly tiny, but record
        # the failure so parsing cannot silently claim to have improved fusion.
        fused = reference
        fusion_status = "not_applied_intersection_too_small"
    else:
        fusion_status = "applied"
    write_candidate_mask(reference_path, fused)
    mask_overlay(frame, fused).save(output_dir / "lip_reference_mask_overlay.png")
    auto_pixels = write_candidate_mask(output_dir / "lip-tight-auto-v0_mask.png", fused)
    user_pixels = write_candidate_mask(output_dir / "lip-tight-user-v0_mask.png", fused)
    safe = fused.filter(ImageFilter.MinFilter(5))
    if inner_path.exists():
        safe = ImageChops.subtract(safe, binary_mask(inner_path).filter(ImageFilter.MaxFilter(13)))
    safe_pixels = write_candidate_mask(output_dir / "lip-safe-v0_mask.png", safe)

    accepted_signal_ids = list(reference_meta.get("acceptedSignalIds", []))
    if "face_parsing_lip_labels_silver" not in accepted_signal_ids:
        accepted_signal_ids.append("face_parsing_lip_labels_silver")
    known_weaknesses = list(reference_meta.get("knownWeaknesses", []))
    if "face parsing is silver, not human-reviewed gold" not in known_weaknesses:
        known_weaknesses.append("face parsing is silver, not human-reviewed gold")
    reference_meta = dict(reference_meta)
    reference_meta.update(
        {
            "maskSource": f"{reference_meta.get('maskSource', 'reference_mask')}+face_parsing_silver_fusion",
            "acceptedSignalIds": accepted_signal_ids,
            "knownWeaknesses": known_weaknesses,
            "positivePixelsBeforeFaceParsing": before_pixels,
            "positivePixels": fused_pixels,
            "coverageRatio": round(fused_pixels / float(frame.width * frame.height), 6),
            "faceParsingFusion": {
                "status": fusion_status,
                "operation": "reference_mask_intersect_dilated_face_parsing_lip_minus_inner_mouth",
                "parsingLipPixels": parsing_pixels,
                "innerMouthPixels": inner_pixels,
                "referencePixelsBefore": before_pixels,
                "referencePixelsAfter": fused_pixels,
                "referenceBeforePath": before_path.name,
                "candidateMasks": {
                    "lip-tight-auto-v0": "lip-tight-auto-v0_mask.png",
                    "lip-tight-user-v0": "lip-tight-user-v0_mask.png",
                    "lip-safe-v0": "lip-safe-v0_mask.png",
                },
            },
        }
    )
    write_json(
        output_dir / "lip_candidate_generation.json",
        {
            "schemaVersion": "e7-lip-candidate-generation-v0",
            "createdAtUtc": utc_now(),
            "faceParsingAffectedReferenceMask": fusion_status == "applied",
            "sourceReferenceBefore": before_path.name,
            "sourceFaceParsingMask": "face_parsing_lip_mask.png",
            "innerMouthExclusionMask": "face_parsing_inner_mouth_mask.png",
            "candidatePixels": {
                "lip-tight-auto-v0": auto_pixels,
                "lip-tight-user-v0": user_pixels,
                "lip-safe-v0": safe_pixels,
            },
            "fusion": reference_meta["faceParsingFusion"],
            "limits": {
                "faceParsingIsSilverNotGold": True,
                "doesNotClaimE73Green": True,
                "runtimeReady": False,
            },
        },
    )
    write_json(output_dir / "lip_reference_mask_meta.json", reference_meta)
    return reference_meta


def make_capture_entry(
    capture_pair_id: str,
    step: str,
    required: bool,
    status: str,
    frame: Image.Image,
    export: dict[str, Any],
    frame_digest: str | None,
    vision_lip_contour: dict[str, Any] | None = None,
    face_parsing: dict[str, Any] | None = None,
    color_gradient: dict[str, Any] | None = None,
) -> dict[str, Any]:
    face = export.get("face", {})
    display = export.get("display", {})
    if status != "captured":
        return {
            "capturePairId": f"{capture_pair_id}_{step}_deferred",
            "step": step,
            "required": required,
            "captureStatus": "deferred",
            "deferredReason": "m1_one_frame_existing_pair_only",
            "tracking": {"state": "unavailable", "faceCount": 0, "meshCountStatus": "deferred"},
        }
    return {
        "capturePairId": capture_pair_id,
        "step": step,
        "required": required,
        "captureStatus": "captured",
        "timestamp": {
            "arFrameTimestamp": export.get("capturedAtUtc"),
            "frameImageTimestamp": export.get("capturedAtUtc"),
            "maxDeltaMs": 0,
        },
        "frame": {
            "path": "frame.png",
            "width": frame.width,
            "height": frame.height,
            "orientation": display.get("orientation", "Portrait"),
            "mirrored": bool(display.get("isMirrored", False)),
            "colorSpace": "sRGB",
        },
        "viewport": {
            "width": frame.width,
            "height": frame.height,
            "contentMode": "unity_world_to_screen_top_left",
            "safeAreaApplied": True,
        },
        "coordinateSpaces": {
            "frameImage": "image_pixel_top_left",
            "visionLandmarks": "face_bbox_normalized_bottom_left",
            "screenVertices": "frame_image_pixel_top_left",
            "referenceMask": "frame_image_pixel_top_left",
        },
        "cleanFrame": {
            "localProcessingInput": True,
            "longTermStored": False,
            "derivedEvidenceOnly": True,
            "frameDigestSha256": frame_digest,
        },
        "arFace": {
            "screenVertices": "available",
            "uvs": "available",
            "indices": "available",
            "clipW": "available",
            "screenVerticesPath": "arface_export.json#screenVertices",
            "uvsPath": "arface_export.json#uvs",
            "indicesPath": "arface_export.json#indices",
            "clipWPath": "arface_export.json#screenVertices[][3]",
            "meshCounts": {
                "vertices": face.get("meshVertexCount"),
                "indices": face.get("meshIndexCount"),
                "uvs": face.get("meshUvCount"),
            },
        },
        "tracking": {
            "state": face.get("trackingState"),
            "faceCount": 1 if face.get("trackingState") == "Tracking" else 0,
            "meshCountStatus": "valid",
        },
        "blendshapeSnapshot": {
            "status": "unavailable",
            "source": export.get("blendShapes", {}).get(
                "source", "not_exposed_in_current_capture_export"
            ),
        },
        "visionLipContour": vision_capture_payload(vision_lip_contour),
        "faceParsing": face_parsing_capture_payload(face_parsing),
        "colorGradientConfidence": color_gradient_capture_payload(color_gradient),
    }


def build_calibration_package(
    output_dir: Path,
    frame: Image.Image,
    export: dict[str, Any],
    draft_meta: dict[str, Any],
    reference_meta: dict[str, Any],
    frame_digest: str,
    vision_lip_contour: dict[str, Any] | None,
    face_parsing: dict[str, Any] | None,
    color_gradient: dict[str, Any] | None,
) -> dict[str, Any]:
    capture_pair_id = export.get("capturePairId") or output_dir.name
    calibration_id = "lip-calib-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-m1-v0"
    capture_set = [
        make_capture_entry(
            capture_pair_id,
            "neutral",
            True,
            "captured",
            frame,
            export,
            frame_digest,
            vision_lip_contour,
            face_parsing,
            color_gradient,
        ),
        make_capture_entry(capture_pair_id, "open_close", True, "deferred", frame, export, None),
        make_capture_entry(capture_pair_id, "smile", True, "deferred", frame, export, None),
        make_capture_entry(capture_pair_id, "yaw", True, "deferred", frame, export, None),
        make_capture_entry(capture_pair_id, "pucker", True, "deferred", frame, export, None),
    ]
    return {
        "schemaVersion": "e7-lip-boundary-calibration-v0",
        "calibrationId": calibration_id,
        "region": "lip",
        "status": "ready_for_uv_projection_partial_m1_one_frame_reference",
        "createdAtUtc": utc_now(),
        "sourceCapturePairIds": [capture_pair_id],
        "captureSet": capture_set,
        "m1OneFrameProof": {
            "status": "partial",
            "reason": "one existing same-moment neutral-ish capture pair only; expression calibration captures are deferred",
            "outputDir": str(output_dir),
            "doesNotClaimE73Green": True,
        },
        "meshStructuralDraft": {
            "status": "generated",
            "source": "arface_lip_ring_mesh_structural_draft_v0",
            "draftMaskPath": "lip_mesh_draft.png",
            "overlayPath": "lip_mesh_draft_overlay.png",
            "metaPath": "lip_mesh_draft_meta.json",
            "acceptedAsReference": False,
            "meta": draft_meta,
        },
        "screenLipReferenceMask": {
            "status": "reference_ready",
            "maskPath": "lip_reference_mask.png",
            "metaPath": "lip_reference_mask_meta.json",
            "capturePairId": capture_pair_id,
            "coordinateSpace": reference_meta.get("coordinateSpace", "frame_image_pixel_top_left"),
            "source": reference_meta.get("maskSource"),
            "acceptedSignalIds": reference_meta.get("acceptedSignalIds", []),
            "acceptedAsGold": bool(reference_meta.get("acceptedAsGold", False)),
            "reviewStatus": reference_meta.get("reviewStatus", "needs_user_review_before_gold"),
            "reviewedBy": reference_meta.get("reviewedBy"),
            "reproducible": bool(reference_meta.get("reproducible", False)),
            "derivedEvidenceOnly": True,
            "knownWeaknesses": reference_meta.get("knownWeaknesses", []),
            "path": str(output_dir / "lip_reference_mask.png"),
        },
        "preFilterSignals": {
            "appleVisionLipContour": vision_capture_payload(vision_lip_contour),
            "faceParsing": face_parsing_capture_payload(face_parsing),
            "colorGradientConfidence": color_gradient_capture_payload(color_gradient),
        },
        "offlineCandidateConfigs": {
            candidate_id: {"status": "uv_projection_artifact_only", "runtimeReady": False}
            for candidate_id in EXPECTED_CANDIDATES
        },
        "correction": {
            "userAdjustmentParams": {
                "tightness": 0,
                "upperLowerBalance": 0,
                "cornerShrink": 0,
                "verticalOffset": 0,
            },
            "userAdjustmentStatus": "default_zero_assumed_not_user_confirmed",
        },
        "failureModeType": {
            "status": "required_not_classified",
            "requiredForM1Ready": True,
        },
        "extensions": {"cheek": {"status": "reserved_only"}, "eye": {"status": "reserved_only"}},
        "privacy": {
            "localOnly": True,
            "rawFrameStored": False,
            "longTermRawFrameStored": False,
            "offDeviceUpload": False,
            "backendUpload": False,
            "userProfileSync": False,
        },
        "limits": {
            "buildlessOnly": True,
            "lipOnly": True,
            "doesNotRunLiveFaceParsingOrCoreMl": True,
            "doesNotUpload": True,
            "doesNotImplementUnityRuntimeCandidate": True,
            "doesNotClaimE73Green": True,
        },
    }


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def status_value(path: Path, key: str) -> str | None:
    if not path.exists():
        return None
    return load_json(path).get(key)


def build_gate_failures(
    reference_meta: dict[str, Any] | None,
    fusion_path: Path,
    uv_path: Path,
    inner_mouth_status: str,
    corner_falloff_status: str,
    upper_lower_status: str,
    blockers: list[str],
) -> list[str]:
    failures: list[str] = []
    if blockers:
        failures.extend(blockers)
    if not reference_meta:
        failures.append("missing_reproducible_reference_mask")
    elif not reference_meta.get("acceptedAsGold", False):
        failures.append("acceptedAsGold_false")
    elif not reference_meta.get("reproducible", False):
        failures.append("reference_mask_not_reproducible")
    if status_value(fusion_path, "phase2Status") != "ready":
        failures.append("phase2Status_not_ready")
    fusion_summary = load_json(fusion_path) if fusion_path.exists() else {}
    fusion_warnings = fusion_summary.get("readiness", {}).get("warnings", [])
    if "required_apple_vision_lip_contour_not_available" in fusion_warnings:
        failures.append("AppleVision_required_not_available")
    if "required_face_parsing_lip_labels_not_available" in fusion_warnings:
        failures.append("faceParsing_required_not_available")
    if "required_color_gradient_confidence_not_computed" in fusion_warnings:
        failures.append("colorGradient_required_not_computed")
    if "required_user_adjustment_not_confirmed" in fusion_warnings:
        failures.append("userAdjustment_required_not_confirmed")
    if "required_failure_mode_type_not_classified" in fusion_warnings:
        failures.append("failureModeType_required_not_classified")
    if "required_blendshape_snapshot_not_available" in fusion_warnings:
        failures.append("blendshapeSnapshot_required_not_available")
    if "required_capture_not_accepted:pucker" in fusion_warnings:
        failures.append("pucker_required_not_accepted")
    if status_value(uv_path, "phase3ExecutionStatus") != "ready":
        failures.append("phase3ExecutionStatus_not_ready")
    uv_summary = load_json(uv_path) if uv_path.exists() else {}
    if uv_summary.get("coordinateSpaceAuditStatus") != "passed":
        failures.append("coordinateSpaceAuditStatus_not_passed")
    if inner_mouth_status == "contract_only":
        failures.append("innerMouthExclusion_contract_only")
    if corner_falloff_status == "contract_only":
        failures.append("cornerFalloff_contract_only")
    if upper_lower_status == "contract_only":
        failures.append("upperLowerSplit_contract_only")
    if uv_summary.get("visibilityConfidence") != "ready":
        failures.append("visibilityConfidence_not_ready")
    if uv_summary.get("heldOutEvalPlanStatus") not in {"available", "recorded", "ready"}:
        failures.append("heldOutEvalPlan_not_recorded")
    return sorted(set(failures))


def write_m1_summary(
    output_dir: Path,
    reference_meta: dict[str, Any] | None,
    blockers: list[str],
    args: argparse.Namespace,
) -> None:
    fusion_path = output_dir / "fusionSummary.json"
    uv_path = output_dir / "summary.json"
    gate_failures = build_gate_failures(
        reference_meta,
        fusion_path,
        uv_path,
        args.inner_mouth_status,
        args.corner_falloff_status,
        args.upper_lower_status,
        blockers,
    )
    decision = "ready" if not gate_failures else ("blocked" if blockers or not reference_meta else "partial")
    fusion_summary = load_json(fusion_path) if fusion_path.exists() else {}
    reference_signals = fusion_summary.get("inputs", {}).get("referenceSignals", {})
    uv_summary = load_json(uv_path) if uv_path.exists() else {}
    draft_meta = load_json(output_dir / "lip_mesh_draft_meta.json") if (output_dir / "lip_mesh_draft_meta.json").exists() else {}
    summary = {
        "schemaVersion": "e7-lip-m1-buildless-package-summary-v1",
        "createdAtUtc": utc_now(),
        "m1Decision": decision,
        "meshDraftGenerated": (output_dir / "lip_mesh_draft.png").exists(),
        "meshDraftReview": draft_meta.get("review"),
        "referenceMask": {
            "path": str(output_dir / "lip_reference_mask.png") if reference_meta else None,
            "source": reference_meta.get("maskSource") if reference_meta else None,
            "acceptedAsGold": bool(reference_meta.get("acceptedAsGold", False)) if reference_meta else False,
            "reviewStatus": reference_meta.get("reviewStatus") if reference_meta else "missing",
            "reproducible": bool(reference_meta.get("reproducible", False)) if reference_meta else False,
        },
        "appleVisionLipContour": {
            "availableCount": reference_signals.get("visionContourAvailable", 0),
            "lowConfidenceCount": reference_signals.get("visionContourLowConfidence", 0),
            "requiredMissingCount": reference_signals.get("visionContourRequiredMissing", 0),
            "jsonPath": str(output_dir / "apple_vision_lip_contour.json")
            if (output_dir / "apple_vision_lip_contour.json").exists()
            else None,
            "overlayPath": str(output_dir / "apple_vision_lip_contour_overlay.png")
            if (output_dir / "apple_vision_lip_contour_overlay.png").exists()
            else None,
        },
        "faceParsing": {
            "silverCount": reference_signals.get("faceParsingSilver", 0),
            "requiredAvailableCount": reference_signals.get("faceParsingRequiredAvailable", 0),
            "requiredMissingCount": reference_signals.get("faceParsingRequiredMissing", 0),
            "labelsPath": str(output_dir / "face_parsing_labels.json")
            if (output_dir / "face_parsing_labels.json").exists()
            else None,
            "overlayPath": str(output_dir / "face_parsing_overlay.png")
            if (output_dir / "face_parsing_overlay.png").exists()
            else None,
            "candidateGenerationPath": str(output_dir / "lip_candidate_generation.json")
            if (output_dir / "lip_candidate_generation.json").exists()
            else None,
        },
        "colorGradient": {
            "computedCount": reference_signals.get("colorGradientComputed", 0),
            "requiredMissingCount": reference_signals.get("colorGradientRequiredMissing", 0),
            "warnings": reference_signals.get("colorGradientWarnings", []),
            "jsonPath": str(output_dir / "color_gradient_confidence.json")
            if (output_dir / "color_gradient_confidence.json").exists()
            else None,
            "overlayPath": str(output_dir / "color_gradient_overlay.png")
            if (output_dir / "color_gradient_overlay.png").exists()
            else None,
        },
        "uvRoundTripRan": uv_summary.get("artifacts", {}).get("round_trip_overlay.png") not in {None, "pending"},
        "phase2Status": status_value(fusion_path, "phase2Status"),
        "phase3ExecutionStatus": status_value(uv_path, "phase3ExecutionStatus"),
        "roundTripKind": uv_summary.get("roundTripKind"),
        "boundaryQualityProof": bool(uv_summary.get("boundaryQualityProof", False)),
        "coordinateSpaceAuditStatus": uv_summary.get("coordinateSpaceAuditStatus"),
        "visibilityConfidence": uv_summary.get("visibilityConfidence"),
        "heldOutEvalPlanStatus": uv_summary.get("heldOutEvalPlanStatus"),
        "roundTripScore": uv_summary.get("roundTripScore"),
        "gateFailures": gate_failures,
        "nextStep": "user approve/draw mask" if decision == "partial" else (
            "provide reproducible reference mask" if decision == "blocked" else "record M1 ready boundary"
        ),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(uv_summary.get("warnings", []))),
        "limits": {
            "artifactExistenceIsSuccess": False,
            "sameFrameRoundTripIsBoundaryQualityProof": False,
            "doesNotClaimRuntimeReady": True,
            "doesNotClaimE73Green": True,
        },
    }
    write_json(output_dir / "m1_summary.json", summary)
    lines = [
        "# E7 Lip M1 Buildless Package Summary",
        "",
        f"- M1 decision: `{decision}`",
        f"- Phase 2 status: `{summary['phase2Status']}`",
        f"- Phase 3 status: `{summary['phase3ExecutionStatus']}`",
        f"- Mesh draft review: `{(summary['meshDraftReview'] or {}).get('status')}`",
        f"- Reference accepted as gold: `{str(summary['referenceMask']['acceptedAsGold']).lower()}`",
        f"- Apple Vision contour available count: `{summary['appleVisionLipContour']['availableCount']}`",
        f"- Face parsing silver count: `{summary['faceParsing']['silverCount']}`",
        f"- Color/gradient computed count: `{summary['colorGradient']['computedCount']}`",
        f"- Boundary quality proof: `{str(summary['boundaryQualityProof']).lower()}`",
        f"- Next step: {summary['nextStep']}.",
        "",
        "## Gate Failures",
        "",
    ]
    lines.extend(f"- `{failure}`" for failure in gate_failures) if gate_failures else lines.append("- None.")
    (output_dir / "m1_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_input_manifest(
    output_dir: Path,
    repo_root: Path,
    args: argparse.Namespace,
    frame_path: Path,
    export_path: Path,
    reference_meta: dict[str, Any] | None,
    vision_lip_contour: dict[str, Any] | None,
    face_parsing: dict[str, Any] | None,
    color_gradient: dict[str, Any] | None,
) -> None:
    manifest = {
        "schemaVersion": "e7-lip-m1-input-manifest-v1",
        "createdAtUtc": utc_now(),
        "scriptVersion": SCRIPT_VERSION,
        "command": sys.argv,
        "capturePair": {
            "path": rel(args.capture_pair, repo_root),
            "framePath": rel(frame_path, repo_root),
            "frameSha256": sha256_file(frame_path),
            "arFaceExportPath": rel(export_path, repo_root),
            "arFaceExportSha256": sha256_file(export_path),
        },
        "referenceInput": {
            "referenceMaskArg": rel(args.reference_mask, repo_root),
            "referenceMaskMetaArg": rel(args.reference_mask_meta, repo_root),
            "referencePolygonJsonArg": rel(args.reference_polygon_json, repo_root),
            "referenceSource": reference_meta.get("maskSource") if reference_meta else None,
            "acceptedAsGold": bool(reference_meta.get("acceptedAsGold", False)) if reference_meta else False,
            "reviewStatus": reference_meta.get("reviewStatus") if reference_meta else None,
            "reproducible": bool(reference_meta.get("reproducible", False)) if reference_meta else False,
        },
        "appleVisionInput": {
            "runRequested": bool(args.run_apple_vision),
            "contourJsonArg": rel(args.apple_vision_contour_json, repo_root),
            "script": rel(args.apple_vision_script, repo_root),
            "minConfidence": args.apple_vision_min_confidence,
            "status": vision_lip_contour.get("status") if vision_lip_contour else "required_not_run",
            "artifact": "apple_vision_lip_contour.json"
            if (output_dir / "apple_vision_lip_contour.json").exists()
            else None,
            "overlay": "apple_vision_lip_contour_overlay.png"
            if (output_dir / "apple_vision_lip_contour_overlay.png").exists()
            else None,
        },
        "faceParsingInput": {
            "runRequested": bool(args.run_face_parsing),
            "artifactDirArg": rel(args.face_parsing_dir, repo_root),
            "script": rel(args.face_parsing_script, repo_root),
            "checkpoint": rel(args.face_parsing_checkpoint, repo_root),
            "status": face_parsing.get("status") if face_parsing else "required_not_run",
            "artifact": "face_parsing_labels.json"
            if (output_dir / "face_parsing_labels.json").exists()
            else None,
            "overlay": "face_parsing_overlay.png"
            if (output_dir / "face_parsing_overlay.png").exists()
            else None,
        },
        "colorGradientInput": {
            "runRequested": not bool(args.skip_color_gradient),
            "script": rel(args.color_gradient_script, repo_root),
            "status": color_gradient.get("status") if color_gradient else "required_not_run",
            "artifact": "color_gradient_confidence.json"
            if (output_dir / "color_gradient_confidence.json").exists()
            else None,
            "overlay": "color_gradient_overlay.png"
            if (output_dir / "color_gradient_overlay.png").exists()
            else None,
        },
        "limits": {
            "artifactExistenceIsSuccess": False,
            "sameFrameRoundTripIsBoundaryQualityProof": False,
        },
    }
    write_json(output_dir / "input_manifest.json", manifest)


def write_blocked_review_needed(output_dir: Path, draft_meta: dict[str, Any], blockers: list[str]) -> None:
    report = {
        "schemaVersion": "e7-lip-m1-blocked-review-needed-v1",
        "createdAtUtc": utc_now(),
        "status": "blocked_review_needed",
        "m1Decision": "blocked",
        "reason": "No explicit reproducible reference mask was provided; mesh draft is review-only.",
        "meshDraft": draft_meta,
        "blockers": sorted(set(blockers + ["missing_reproducible_reference_mask"])),
        "nextStep": "provide --reference-mask with metadata or --reference-polygon-json",
    }
    write_json(output_dir / "blocked_review_needed.json", report)


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    capture_pair = args.capture_pair.resolve()
    frame_path = capture_pair / "frame.png"
    export_path = capture_pair / "arface_export.json"
    output_dir = (
        args.output_dir
        or (
            repo_root
            / "evidence/e7-lip-m1-packages"
            / f"m1-lip-repair-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
    ).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []
    if not frame_path.exists():
        blockers.append(f"missing_capture_frame:{frame_path}")
    if not export_path.exists():
        blockers.append(f"missing_arface_export:{export_path}")
    if blockers:
        write_m1_summary(output_dir, None, blockers, args)
        return 2

    frame = Image.open(frame_path).convert("RGB")
    export = load_json(export_path)
    capture_pair_id = str(export.get("capturePairId") or capture_pair.name)
    vision_lip_contour = prepare_apple_vision_contour(
        args,
        repo_root,
        frame_path,
        frame,
        output_dir,
        capture_pair_id,
    )
    face_parsing = prepare_face_parsing_artifacts(
        args,
        repo_root,
        frame_path,
        export_path,
        output_dir,
        capture_pair_id,
    )
    effective_region_statuses(args, face_parsing, output_dir)
    local_vertices, screen_vertices, uvs, indices = export_arrays(export)
    if not len(local_vertices):
        blockers.append("missing_arface_localVertices")
    if not len(screen_vertices):
        blockers.append("missing_arface_screenVertices")
    if not len(uvs):
        blockers.append("missing_arface_uvs")
    if not len(indices):
        blockers.append("missing_arface_indices")
    if screen_vertices.ndim != 2 or screen_vertices.shape[1] < 4:
        blockers.append("missing_arface_clipW")
    if len(screen_vertices) and len(uvs) and len(screen_vertices) != len(uvs):
        blockers.append("screen_vertices_uv_count_mismatch")

    config = LipRingConfig()
    triangles, selected, padded_inside = select_lip_triangles(local_vertices, indices, config)
    if not np.any(selected):
        blockers.append("lip_ring_mesh_draft_selected_no_triangles")

    draft_mask = rasterize_triangles(frame.size, screen_vertices, triangles, selected)
    draft_mask.save(output_dir / "lip_mesh_draft.png")
    mask_overlay(frame, draft_mask).save(output_dir / "lip_mesh_draft_overlay.png")
    positive_pixels = int(np.count_nonzero(np.asarray(draft_mask)))
    draft_meta = {
        "schemaVersion": "e7-lip-mesh-draft-meta-v1",
        "createdAtUtc": utc_now(),
        "capturePairId": export.get("capturePairId"),
        "sourceFieldsUsed": ["localVertices", "screenVertices", "uvs", "indices", "screenVertices[][3] as clipW"],
        "sourceFieldsNotUsed": [
            "normals",
            "curvature",
            "reliable_triangle_visibility",
            "front_most_triangle_marking",
            "blendshape_values",
        ],
        "labelGroup": config.__dict__,
        "meshCounts": {
            "localVertices": int(len(local_vertices)),
            "screenVertices": int(len(screen_vertices)),
            "uvs": int(len(uvs)),
            "indices": int(len(indices)),
            "triangles": int(len(triangles)),
            "selectedTriangles": int(np.count_nonzero(selected)),
            "paddedLabelVertices": int(np.count_nonzero(padded_inside)),
        },
        "projectedBBox": projected_bbox(screen_vertices, triangles, selected),
        "draftMask": {
            "path": "lip_mesh_draft.png",
            "positivePixels": positive_pixels,
            "coverageRatio": round(positive_pixels / float(frame.width * frame.height), 6),
        },
        "review": {
            "status": "review_only_too_broad_for_reference",
            "reason": "mesh draft covers surrounding lip skin and must not be promoted without explicit reference input",
            "reviewedBy": "codex_visual_audit",
        },
        "coordinateSpaceValidated": bool(export.get("coordinateSpaceValidated", False)),
        "coordinateSpaceValidationStatus": export.get("coordinateSpaceValidationStatus"),
    }
    write_json(output_dir / "lip_mesh_draft_meta.json", draft_meta)

    reference_meta: dict[str, Any] | None = None
    if args.reference_polygon_json:
        reference_mask_path, reference_meta, reference_blockers = build_reference_from_polygon(
            args.reference_polygon_json.resolve(), frame, output_dir
        )
        blockers.extend(reference_blockers)
    elif args.reference_mask:
        reference_mask_path, reference_meta, reference_blockers = build_reference_from_mask(
            args.reference_mask.resolve(),
            args.reference_mask_meta.resolve() if args.reference_mask_meta else None,
            frame,
            output_dir,
        )
        blockers.extend(reference_blockers)
    else:
        write_input_manifest(
            output_dir,
            repo_root,
            args,
            frame_path,
            export_path,
            None,
            vision_lip_contour,
            face_parsing,
            None,
        )
        write_blocked_review_needed(output_dir, draft_meta, blockers)
        write_m1_summary(output_dir, None, blockers + ["missing_reproducible_reference_mask"], args)
        print(json.dumps({"outputDir": str(output_dir), "m1Decision": "blocked"}, indent=2))
        return 2

    if reference_meta:
        reference_meta = apply_face_parsing_to_reference(output_dir, frame, reference_meta, face_parsing)
        mask_overlay(frame, Image.open(output_dir / "lip_reference_mask.png").convert("L")).save(
            output_dir / "lip_reference_mask_overlay.png"
        )
        write_json(output_dir / "lip_reference_mask_meta.json", reference_meta)
    color_gradient = prepare_color_gradient_confidence(
        args,
        repo_root,
        frame_path,
        output_dir,
        capture_pair_id,
    )
    write_input_manifest(
        output_dir,
        repo_root,
        args,
        frame_path,
        export_path,
        reference_meta,
        vision_lip_contour,
        face_parsing,
        color_gradient,
    )

    if blockers:
        write_m1_summary(output_dir, reference_meta, blockers, args)
        print(json.dumps({"outputDir": str(output_dir), "m1Decision": "blocked"}, indent=2))
        return 2

    package = build_calibration_package(
        output_dir,
        frame,
        export,
        draft_meta,
        reference_meta or {},
        sha256_file(frame_path),
        vision_lip_contour,
        face_parsing,
        color_gradient,
    )
    package_path = output_dir / f"{package['calibrationId']}.json"
    write_json(package_path, package)
    run_command(
        [
            sys.executable,
            "scripts/e7_lip_boundary_fusion/prepare_fusion_summary.py",
            str(package_path),
            "--output-dir",
            str(output_dir),
        ],
        repo_root,
    )

    if not args.skip_round_trip:
        face_parsing_fusion = reference_meta.get("faceParsingFusion", {})
        parsing_fused = face_parsing_fusion.get("status") == "applied"
        mask_source = "face_parsing_silver" if parsing_fused else "manual_reference"
        accepted_signal_id = (
            "face_parsing_lip_labels_silver"
            if parsing_fused
            else "reproducible_reference_mask"
        )
        rejected_reason = (
            "face_parsing_silver_not_user_approved_gold"
            if parsing_fused and not reference_meta.get("acceptedAsGold", False)
            else (
                "reference_mask_not_user_approved_gold"
                if not reference_meta.get("acceptedAsGold", False)
                else "reference_mask_user_approved_gold"
            )
        )
        run_command(
            [
                sys.executable,
                "scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py",
                str(output_dir / "fusionSummary.json"),
                "--capture-pair",
                str(capture_pair),
                "--mask",
                str(output_dir / "lip_reference_mask.png"),
                "--mask-source",
                mask_source,
                "--accepted-signal-id",
                accepted_signal_id,
                "--inner-mouth-status",
                args.inner_mouth_status,
                "--corner-falloff-status",
                args.corner_falloff_status,
                "--upper-lower-status",
                args.upper_lower_status,
                "--rejected-signal-reason",
                rejected_reason,
                "--output-dir",
                str(output_dir),
                "--uv-resolution",
                str(args.uv_resolution),
                "--sample-stride",
                str(args.sample_stride),
                "--render-stride",
                str(args.render_stride),
                "--threshold",
                str(args.threshold),
            ],
            repo_root,
        )

    write_m1_summary(output_dir, reference_meta, blockers, args)
    print(
        json.dumps(
            {
                "outputDir": str(output_dir),
                "m1Summary": str(output_dir / "m1_summary.json"),
                "m1Decision": load_json(output_dir / "m1_summary.json").get("m1Decision"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
