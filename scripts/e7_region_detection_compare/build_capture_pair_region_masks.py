#!/usr/bin/env python3
"""Compare eye / skin / eyebrow masks from local detector candidates.

This buildless tool reads one E7 capture pair, runs local-only provider probes
where available, and writes reviewable overlays plus a contact sheet. It is
evidence for visual comparison only, not product-quality runtime proof.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "e7_region_generate"))

from build_region_candidates import (  # noqa: E402
    DEFAULT_CHEEK_UV_PRIOR,
    DEFAULT_EYE_UV_PRIOR,
    bbox_for,
    dilate,
    face_anchor,
    load_json,
    load_uv_prior,
    mask_to_image,
    render_atlas_to_screen_alpha,
    split_lr_components,
    stroke_polyline_mask,
)

DEFAULT_CAPTURE_PAIR = REPO_ROOT / "evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06"
DEFAULT_MEDIAPIPE_MODEL = REPO_ROOT / ".cache/mediapipe/face_landmarker.task"
VISION_SCRIPT = REPO_ROOT / "scripts/e7_region_detection_compare/extract_apple_vision_face_landmarks.swift"
FACE_PARSING_SCRIPT = REPO_ROOT / "scripts/e7_lip_boundary_fusion/run_face_parsing.py"
FACE_PARSING_CHECKPOINT = REPO_ROOT / "evidence/e7-lip-m1-models/face-parsing-pytorch/79999_iter.pth"

REGIONS = ("eye", "skin", "brow")
PROVIDERS = ("arface", "vision", "parsing", "color", "mediapipe")

MEDIAPIPE_FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
    400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
    54, 103, 67, 109,
]
MEDIAPIPE_LEFT_EYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
MEDIAPIPE_RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
MEDIAPIPE_LEFT_BROW = [276, 283, 282, 295, 285, 336, 296, 334, 293, 300]
MEDIAPIPE_RIGHT_BROW = [46, 53, 52, 65, 55, 107, 66, 105, 63, 70]


@dataclass(frozen=True)
class MaskResult:
    provider: str
    region: str
    status: str
    mask: np.ndarray | None
    method: str
    warnings: list[str]
    details: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build region mask comparison from one capture pair.")
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--mediapipe-model", type=Path, default=DEFAULT_MEDIAPIPE_MODEL)
    parser.add_argument("--uv-resolution", type=int, default=512)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def binary_from_image(path: Path, size: tuple[int, int]) -> np.ndarray:
    img = Image.open(path).convert("L")
    if img.size != size:
        img = img.resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 0


def alpha_image(mask: np.ndarray | None, feather: float = 4.0) -> Image.Image:
    if mask is None:
        return Image.new("L", (1, 1), 0)
    return mask_to_image(mask).filter(ImageFilter.GaussianBlur(radius=feather))


def draw_status_panel(size: tuple[int, int], title: str, lines: list[str]) -> Image.Image:
    panel = Image.new("RGB", size, (246, 246, 246))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(80, 80, 80), width=3)
    title_font = load_font(72)
    body_font = load_font(42)
    badge_font = load_font(64)
    draw.rectangle((0, 0, size[0], 160), fill=(28, 28, 28))
    draw.text((52, 50), title[:42], fill=(255, 255, 255), font=title_font)
    badge = "BLOCKED" if "blocked" in title else "UNAVAILABLE"
    badge_width = text_width(draw, badge, badge_font)
    draw.rounded_rectangle(
        (52, 220, 52 + badge_width + 64, 330),
        radius=16,
        fill=(210, 54, 82),
    )
    draw.text((84, 244), badge, fill=(255, 255, 255), font=badge_font)
    y = 390
    for line in lines:
        chunks = wrap_line(line, 38)
        for chunk in chunks[:5]:
            draw.text((52, y), chunk, fill=(35, 35, 35), font=body_font)
            y += 58
        y += 18
    return panel


def load_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return int(bbox[2] - bbox[0])


def wrap_line(line: str, width: int) -> list[str]:
    words = line.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > width:
            if current:
                lines.append(current)
                current = ""
            lines.extend(word[index : index + width] for index in range(0, len(word), width))
            continue
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def overlay(frame: Image.Image, result: MaskResult, color: tuple[int, int, int]) -> Image.Image:
    if result.mask is None or result.status not in {"available", "approximate"}:
        return draw_status_panel(
            frame.size,
            f"{result.provider}/{result.region}: {result.status}",
            [result.method, *result.warnings[:4]],
        )
    base = frame.convert("RGB")
    tint = Image.new("RGB", frame.size, color)
    alpha = alpha_image(result.mask, 5.0)
    out = Image.composite(tint, base, alpha).convert("RGB")
    draw = ImageDraw.Draw(out)
    label = f"{result.provider} {result.region} | {result.status}"
    draw.rectangle((18, 18, min(frame.width - 18, 18 + 16 * len(label)), 62), fill=(0, 0, 0))
    draw.text((30, 32), label, fill=(255, 255, 255))
    return out


def polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> np.ndarray:
    img = Image.new("L", size, 0)
    if len(points) >= 3:
        ImageDraw.Draw(img).polygon(points, fill=255)
    return np.asarray(img) > 0


def line_mask(size: tuple[int, int], points: list[tuple[float, float]], width: int) -> np.ndarray:
    if not points:
        return np.zeros((size[1], size[0]), dtype=bool)
    return stroke_polyline_mask(size, points, max(1, width))


def arface_face_surface_mask(size: tuple[int, int], export: dict[str, Any]) -> np.ndarray:
    screen_vertices = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    indices = np.asarray(export.get("indices", []), dtype=np.int32)
    if screen_vertices.ndim != 2 or len(indices) < 3:
        return np.zeros((size[1], size[0]), dtype=bool)
    img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(img)
    usable = (len(indices) // 3) * 3
    for tri in indices[:usable].reshape(-1, 3):
        pts = [(float(screen_vertices[idx][0]), float(screen_vertices[idx][1])) for idx in tri]
        draw.polygon(pts, fill=255)
    return np.asarray(img) > 0


def build_arface_results(frame: Image.Image, export: dict[str, Any], uv_resolution: int) -> list[MaskResult]:
    size = frame.size
    eye_uv = load_uv_prior(DEFAULT_EYE_UV_PRIOR, uv_resolution)
    eye_prior_alpha = render_atlas_to_screen_alpha(eye_uv, export, size, 1)
    eye_mask = eye_prior_alpha >= 0.08
    face_mask = arface_face_surface_mask(size, export)

    brow_mask = np.zeros((size[1], size[0]), dtype=bool)
    for side, component in split_lr_components(eye_mask):
        bbox = bbox_for(component)
        if bbox is None:
            continue
        comp_w = float(bbox["width"])
        y_base = bbox["minY"] - 58.0
        if side == "left":
            pts = [
                (bbox["minX"] + comp_w * 0.03, y_base + 9),
                (bbox["minX"] + comp_w * 0.42, y_base - 21),
                (bbox["maxX"] - comp_w * 0.08, y_base + 5),
            ]
        else:
            pts = [
                (bbox["minX"] + comp_w * 0.08, y_base + 5),
                (bbox["minX"] + comp_w * 0.58, y_base - 21),
                (bbox["maxX"] - comp_w * 0.03, y_base + 9),
            ]
        brow_mask |= line_mask(size, pts, 16)

    return [
        MaskResult("arface", "eye", "approximate", eye_mask, "Projected local eye UV prior through current ARFace mesh.", ["ARFace has no semantic eye mask; this is UV-prior projection."], {}),
        MaskResult("arface", "skin", "approximate", face_mask, "Filled current ARFace mesh triangles as face/skin surface.", ["Includes lips/eyes/brows; ARFace mesh is geometry, not skin semantic segmentation."], {}),
        MaskResult("arface", "brow", "approximate", brow_mask, "Parametric brow arc anchored to ARFace-projected eye prior.", ["ARFace has no eyebrow hair recognition; brow is inferred above eyes."], {}),
    ]


def run_vision(frame_path: Path, output_json: Path, capture_pair_id: str) -> dict[str, Any]:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "xcrun",
        "swift",
        str(VISION_SCRIPT),
        "--image",
        str(frame_path),
        "--output-json",
        str(output_json),
        "--capture-pair-id",
        capture_pair_id,
    ]
    env = os.environ.copy()
    swift_cache = Path("/private/tmp/makeupar-swift-module-cache")
    swift_cache.mkdir(parents=True, exist_ok=True)
    env.setdefault("CLANG_MODULE_CACHE_PATH", str(swift_cache / "clang"))
    env.setdefault("SWIFT_MODULE_CACHE_PATH", str(swift_cache / "swift"))
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=60,
        env=env,
        check=False,
    )
    (output_json.parent / "apple_vision_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_json.parent / "apple_vision_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if output_json.exists():
        data = json.loads(output_json.read_text(encoding="utf-8"))
    else:
        data = {"status": "unavailable", "unavailableReason": f"swift_exit_{completed.returncode}"}
    data["_process"] = {"exitCode": completed.returncode}
    return data


def load_native_provider_artifact(capture_pair: Path, provider: str) -> dict[str, Any] | None:
    path = capture_pair / f"{provider}_face_landmarks.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["_source"] = {
        "kind": "ios_native_provider_artifact",
        "path": str(path),
    }
    return data


def contour_points(vision: dict[str, Any], name: str) -> list[tuple[float, float]]:
    contour = vision.get("contours", {}).get(name, {})
    points = contour.get("imagePoints", [])
    out: list[tuple[float, float]] = []
    for point in points:
        if "x" in point and "y" in point:
            out.append((float(point["x"]), float(point["y"])))
    return out


def build_vision_results(frame: Image.Image, vision: dict[str, Any], arface_skin: np.ndarray) -> list[MaskResult]:
    size = frame.size
    if vision.get("status") not in {"available", "low_confidence"}:
        reason = vision.get("unavailableReason", "vision_unavailable")
        return [
            MaskResult("vision", region, "blocked", None, "Apple Vision landmark extraction did not produce usable contours.", [str(reason)], {})
            for region in REGIONS
        ]

    eye_mask = np.zeros((size[1], size[0]), dtype=bool)
    for name in ("leftEye", "rightEye"):
        points = contour_points(vision, name)
        eye_mask |= dilate(polygon_mask(size, points), 2)

    face_points = contour_points(vision, "faceContour")
    skin_mask = polygon_mask(size, face_points)
    if skin_mask.any():
        skin_mask = dilate(skin_mask, 18) & arface_skin
    else:
        skin_mask = arface_skin

    brow_mask = np.zeros((size[1], size[0]), dtype=bool)
    for name in ("leftEyebrow", "rightEyebrow"):
        points = contour_points(vision, name)
        brow_mask |= line_mask(size, points, 18)

    status = "available" if vision.get("status") == "available" else "approximate"
    return [
        MaskResult("vision", "eye", status, eye_mask, "Apple Vision leftEye/rightEye landmarks filled as eye masks.", [], {"confidence": vision.get("confidence")}),
        MaskResult("vision", "skin", "approximate", skin_mask, "Apple Vision faceContour clipped by ARFace mesh used as skin/face area.", ["Vision does not provide a true skin label."], {"confidence": vision.get("confidence")}),
        MaskResult("vision", "brow", status, brow_mask, "Apple Vision leftEyebrow/rightEyebrow landmarks stroked as eyebrow masks.", [], {"confidence": vision.get("confidence")}),
    ]


def build_color_results(frame: Image.Image, arface_eye: np.ndarray, arface_skin: np.ndarray, arface_brow: np.ndarray) -> list[MaskResult]:
    arr = np.asarray(frame.convert("RGB"), dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = arr.max(axis=2)
    minc = arr.min(axis=2)
    sat = (maxc - minc) / np.maximum(maxc, 1.0)
    gray = (0.299 * r + 0.587 * g + 0.114 * b)

    face_pixels = arface_skin & (gray > 35)
    if np.count_nonzero(face_pixels) > 0:
        median_rgb = np.median(arr[face_pixels], axis=0)
        dist = np.linalg.norm((arr - median_rgb) / np.array([42.0, 34.0, 32.0]), axis=2)
        skin_mask = face_pixels & (dist < 2.15) & (sat < 0.55)
        skin_mask = dilate(skin_mask, 5) & arface_skin
    else:
        skin_mask = arface_skin

    eye_zone = dilate(arface_eye, 8)
    white_eye = eye_zone & (gray > np.percentile(gray[eye_zone], 66) if np.any(eye_zone) else False) & (sat < 0.42)
    dark_eye = eye_zone & (gray < np.percentile(gray[eye_zone], 38) if np.any(eye_zone) else False)
    eye_mask = dilate(white_eye | dark_eye, 2) & eye_zone

    brow_zone = dilate(arface_brow, 18)
    if np.any(brow_zone):
        dark_threshold = min(95.0, float(np.percentile(gray[brow_zone], 42)))
        brow_mask = brow_zone & (gray <= dark_threshold) & (sat < 0.8)
        brow_mask = dilate(brow_mask, 3)
    else:
        brow_mask = arface_brow

    return [
        MaskResult("color", "eye", "approximate", eye_mask, "Brightness/saturation split inside ARFace eye prior.", ["Color alone cannot know eye anatomy; it is a helper signal."], {}),
        MaskResult("color", "skin", "approximate", skin_mask, "Median skin-color threshold inside ARFace face surface.", ["Sensitive to lighting, shadows, clothing, hair, and existing makeup."], {}),
        MaskResult("color", "brow", "approximate", brow_mask, "Dark-pixel extraction in ARFace brow band.", ["Works only when brow hair is darker than nearby skin."], {}),
    ]


def run_face_parsing(frame_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        import torch  # type: ignore[import-not-found]  # noqa: F401
    except Exception as exception:
        data = {
            "status": "blocked",
            "reason": "torch_not_available_in_current_python_env",
            "exception": exception.__class__.__name__,
            "message": str(exception),
            "script": str(FACE_PARSING_SCRIPT),
            "checkpoint": str(FACE_PARSING_CHECKPOINT),
        }
        write_json(output_dir / "face_parsing_blocked.json", data)
        return data

    command = [
        sys.executable,
        str(FACE_PARSING_SCRIPT),
        "--image",
        str(frame_path),
        "--output-dir",
        str(output_dir),
        "--checkpoint",
        str(FACE_PARSING_CHECKPOINT),
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=180, check=False)
    (output_dir / "face_parsing_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "face_parsing_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    labels_path = output_dir / "face_parsing_labels.json"
    if completed.returncode == 0 and labels_path.exists():
        data = json.loads(labels_path.read_text(encoding="utf-8"))
        data["_process"] = {"exitCode": completed.returncode}
        return data
    data = {"status": "blocked", "reason": f"face_parsing_runner_failed_{completed.returncode}"}
    write_json(output_dir / "face_parsing_blocked.json", data)
    return data


def build_parsing_results(frame: Image.Image, parsing_dir: Path, parsing: dict[str, Any]) -> list[MaskResult]:
    size = frame.size
    if parsing.get("status") != "silver":
        reason = parsing.get("reason") or parsing.get("unavailableReason") or "face_parsing_unavailable"
        return [
            MaskResult("parsing", region, "blocked", None, "Local BiSeNet face parsing did not run for this capture.", [str(reason)], parsing)
            for region in REGIONS
        ]

    skin_path = parsing_dir / "face_parsing_skin_mask.png"
    label_path = parsing_dir / "face_parsing_label_map.png"
    skin_mask = binary_from_image(skin_path, size) if skin_path.exists() else None
    label_map = np.asarray(Image.open(label_path).convert("L").resize(size, Image.Resampling.NEAREST)) if label_path.exists() else None

    eye_mask = None
    brow_mask = None
    if label_map is not None:
        # CelebAMask-HQ/BiSeNet common labels: brows 2/3, eyes 4/5, skin 1.
        brow_mask = np.isin(label_map, [2, 3])
        eye_mask = np.isin(label_map, [4, 5])
        if skin_mask is None:
            skin_mask = label_map == 1

    return [
        MaskResult("parsing", "eye", "available" if eye_mask is not None and eye_mask.any() else "blocked", eye_mask, "Face parsing eye labels 4/5 from local BiSeNet.", [], parsing),
        MaskResult("parsing", "skin", "available" if skin_mask is not None and skin_mask.any() else "blocked", skin_mask, "Face parsing skin label from local BiSeNet.", [], parsing),
        MaskResult("parsing", "brow", "available" if brow_mask is not None and brow_mask.any() else "blocked", brow_mask, "Face parsing brow labels 2/3 from local BiSeNet.", [], parsing),
    ]


def run_mediapipe_child(frame_path: Path, model_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    child_script = output_dir / "mediapipe_child.py"
    child_script.write_text(
        """
import json
import sys
from pathlib import Path
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

frame_path = Path(sys.argv[1])
model_path = Path(sys.argv[2])
output_json = Path(sys.argv[3])
frame = Image.open(frame_path).convert("RGB")
base_options = mp_python.BaseOptions(model_asset_path=str(model_path), delegate=mp_python.BaseOptions.Delegate.CPU)
options = mp_vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=mp_vision.RunningMode.IMAGE,
    num_faces=1,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    min_face_detection_confidence=0.3,
    min_face_presence_confidence=0.3,
    min_tracking_confidence=0.3,
)
landmarker = mp_vision.FaceLandmarker.create_from_options(options)
try:
    image = mp.Image.create_from_file(str(frame_path))
    result = landmarker.detect(image)
finally:
    landmarker.close()
payload = {
    "status": "available" if result.face_landmarks else "blocked",
    "faceCount": len(result.face_landmarks),
    "imageSize": list(frame.size),
    "landmarks": []
}
if result.face_landmarks:
    payload["landmarks"] = [
        {"x": round(float(point.x) * frame.width, 3), "y": round(float(point.y) * frame.height, 3), "z": round(float(point.z), 6)}
        for point in result.face_landmarks[0]
    ]
output_json.write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")
""".lstrip(),
        encoding="utf-8",
    )
    output_json = output_dir / "mediapipe_landmarks.json"
    command = [sys.executable, str(child_script), str(frame_path), str(model_path), str(output_json)]
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", str((REPO_ROOT / ".cache/matplotlib").resolve()))
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    completed = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, timeout=60, env=env, check=False)
    (output_dir / "mediapipe_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "mediapipe_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if output_json.exists():
        data = json.loads(output_json.read_text(encoding="utf-8"))
    else:
        data = {
            "status": "blocked",
            "reason": f"mediapipe_child_failed_{completed.returncode}",
            "stderrTail": completed.stderr[-2000:],
        }
    data["_process"] = {"exitCode": completed.returncode}
    return data


def points_from_landmarks(landmarks: list[dict[str, Any]], indices: list[int]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for idx in indices:
        if idx < len(landmarks):
            point = landmarks[idx]
            out.append((float(point["x"]), float(point["y"])))
    return out


def build_mediapipe_results(frame: Image.Image, mediapipe: dict[str, Any]) -> list[MaskResult]:
    size = frame.size
    if mediapipe.get("status") != "available":
        reason = mediapipe.get("reason", "mediapipe_unavailable")
        return [
            MaskResult("mediapipe", region, "blocked", None, "MediaPipe FaceLandmarker did not produce landmarks.", [str(reason)], mediapipe)
            for region in REGIONS
        ]
    landmarks = mediapipe.get("landmarks", [])
    face_mask = polygon_mask(size, points_from_landmarks(landmarks, MEDIAPIPE_FACE_OVAL))
    eye_mask = polygon_mask(size, points_from_landmarks(landmarks, MEDIAPIPE_LEFT_EYE)) | polygon_mask(size, points_from_landmarks(landmarks, MEDIAPIPE_RIGHT_EYE))
    brow_mask = line_mask(size, points_from_landmarks(landmarks, MEDIAPIPE_LEFT_BROW), 18) | line_mask(size, points_from_landmarks(landmarks, MEDIAPIPE_RIGHT_BROW), 18)
    return [
        MaskResult("mediapipe", "eye", "available", dilate(eye_mask, 2), "MediaPipe FaceLandmarker eye landmark polygons.", [], {"landmarkCount": len(landmarks)}),
        MaskResult("mediapipe", "skin", "approximate", face_mask, "MediaPipe face-oval polygon used as face/skin area.", ["MediaPipe has no semantic skin class."], {"landmarkCount": len(landmarks)}),
        MaskResult("mediapipe", "brow", "available", brow_mask, "MediaPipe eyebrow landmark strokes.", [], {"landmarkCount": len(landmarks)}),
    ]


def result_record(result: MaskResult, overlay_path: Path, mask_path: Path | None) -> dict[str, Any]:
    pixels = int(np.count_nonzero(result.mask)) if result.mask is not None else 0
    bbox = bbox_for(result.mask) if result.mask is not None and pixels > 0 else None
    return {
        "provider": result.provider,
        "region": result.region,
        "status": result.status,
        "method": result.method,
        "warnings": result.warnings,
        "positivePixels": pixels,
        "bbox": bbox,
        "maskPath": str(mask_path) if mask_path else None,
        "overlayPath": str(overlay_path),
        "details": result.details,
    }


def save_results(frame: Image.Image, results: list[MaskResult], output_root: Path) -> dict[str, Any]:
    colors = {
        "eye": (60, 150, 255),
        "skin": (255, 176, 118),
        "brow": (60, 230, 140),
    }
    records: list[dict[str, Any]] = []
    by_key = {(result.provider, result.region): result for result in results}
    for provider in PROVIDERS:
        for region in REGIONS:
            result = by_key.get((provider, region))
            if result is None:
                result = MaskResult(provider, region, "blocked", None, "Provider result missing.", ["missing_result"], {})
            provider_dir = output_root / provider
            provider_dir.mkdir(parents=True, exist_ok=True)
            mask_path: Path | None = None
            if result.mask is not None:
                mask_path = provider_dir / f"{region}_mask.png"
                mask_to_image(result.mask).save(mask_path)
            overlay_path = provider_dir / f"{region}_overlay.png"
            overlay(frame, result, colors[region]).save(overlay_path)
            records.append(result_record(result, overlay_path, mask_path))
    return {"records": records}


def make_contact_sheet(output_root: Path, summary: dict[str, Any]) -> Path:
    cell_w = 300
    first = Image.open(summary["sourceFramePath"]).convert("RGB")
    cell_h = int(cell_w * first.height / first.width)
    header_h = 34
    sheet = Image.new("RGB", (len(REGIONS) * cell_w, len(PROVIDERS) * (cell_h + header_h)), "white")
    draw = ImageDraw.Draw(sheet)
    lookup = {(r["provider"], r["region"]): r for r in summary["records"]}
    for row, provider in enumerate(PROVIDERS):
        for col, region in enumerate(REGIONS):
            rec = lookup[(provider, region)]
            img = Image.open(rec["overlayPath"]).convert("RGB").resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            x = col * cell_w
            y = row * (cell_h + header_h)
            sheet.paste(img, (x, y + header_h))
            label = f"{provider} / {region} / {rec['status']}"
            draw.rectangle((x, y, x + cell_w - 1, y + header_h - 1), fill=(30, 30, 30))
            draw.text((x + 8, y + 10), label, fill=(255, 255, 255))
            draw.rectangle((x, y + header_h, x + cell_w - 1, y + header_h + cell_h - 1), outline=(220, 220, 220), width=2)
    path = output_root / "contact_sheet_eye_skin_brow.png"
    sheet.save(path)
    return path


def write_markdown(output_root: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Eye / Skin / Brow Detector Comparison",
        "",
        f"- capturePairId: `{summary['capturePairId']}`",
        f"- sourceFrame: `{summary['sourceFramePath']}`",
        f"- contactSheet: `{summary['contactSheetPath']}`",
        "",
        "| provider | eye | skin | brow | notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    lookup = {(r["provider"], r["region"]): r for r in summary["records"]}
    for provider in PROVIDERS:
        statuses = [lookup[(provider, region)]["status"] for region in REGIONS]
        notes = []
        for region in REGIONS:
            rec = lookup[(provider, region)]
            if rec["warnings"]:
                notes.append(f"{region}: {rec['warnings'][0]}")
        lines.append(f"| {provider} | {statuses[0]} | {statuses[1]} | {statuses[2]} | {'; '.join(notes) or '-'} |")
    lines.extend(
        [
            "",
            "## Interpretation Rules",
            "",
            "- `available`: provider produced a direct landmark/label for that region in this local run.",
            "- `approximate`: provider does not directly recognize the region, so the mask is inferred from geometry, prior, or color.",
            "- `blocked`: the provider could not run in the current local environment or did not expose that signal.",
            "- This is buildless visual comparison only. It is not iPhone runtime proof or product-quality acceptance.",
        ]
    )
    write_text(output_root / "summary.md", "\n".join(lines))


def main() -> int:
    args = parse_args()
    capture_pair = args.capture_pair.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    frame_path = capture_pair / "frame.png"
    export_path = capture_pair / "arface_export.json"
    frame = Image.open(frame_path).convert("RGB")
    export = load_json(export_path)
    capture_pair_id = export.get("capturePairId") or capture_pair.name

    arface_results = build_arface_results(frame, export, args.uv_resolution)
    arface_by_region = {result.region: result for result in arface_results}

    vision_json = output_root / "vision" / "apple_vision_face_landmarks.json"
    vision = load_native_provider_artifact(capture_pair, "vision")
    if vision is None:
        vision = run_vision(frame_path, vision_json, capture_pair_id)
    vision_results = build_vision_results(frame, vision, arface_by_region["skin"].mask)  # type: ignore[arg-type]

    color_results = build_color_results(
        frame,
        arface_by_region["eye"].mask,  # type: ignore[arg-type]
        arface_by_region["skin"].mask,  # type: ignore[arg-type]
        arface_by_region["brow"].mask,  # type: ignore[arg-type]
    )

    parsing_dir = output_root / "parsing" / "raw"
    parsing = run_face_parsing(frame_path, parsing_dir)
    parsing_results = build_parsing_results(frame, parsing_dir, parsing)

    mediapipe_dir = output_root / "mediapipe" / "raw"
    mediapipe = load_native_provider_artifact(capture_pair, "mediapipe")
    if mediapipe is None:
        mediapipe = run_mediapipe_child(frame_path, args.mediapipe_model.resolve(), mediapipe_dir)
    mediapipe_results = build_mediapipe_results(frame, mediapipe)

    all_results = arface_results + vision_results + parsing_results + color_results + mediapipe_results
    saved = save_results(frame, all_results, output_root)
    summary = {
        "schemaVersion": "e7-region-detector-comparison-v0",
        "createdAtUtc": utc_now(),
        "capturePairId": capture_pair_id,
        "capturePairPath": str(capture_pair),
        "sourceFramePath": str(frame_path),
        "arfaceExportPath": str(export_path),
        "frameSize": list(frame.size),
        "records": saved["records"],
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
        "limits": [
            "single captured frame only",
            "not iPhone runtime provider proof",
            "not product-quality acceptance",
            "visual human review still required",
        ],
    }
    contact_sheet = make_contact_sheet(output_root, summary)
    summary["contactSheetPath"] = str(contact_sheet)
    write_json(output_root / "summary.json", summary)
    write_markdown(output_root, summary)
    print(str(contact_sheet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
