#!/usr/bin/env python3
"""Build fast E7 lip boundary candidates from local calibration evidence.

This is a local-only experiment tool. It reads existing E7 frame, Apple Vision,
face parsing, color/gradient, and ARFace export artifacts, then writes derived
candidate masks and review images. It does not run uploads, device builds, or
live runtime inference.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


SCHEMA_VERSION = "e7-lip-candidate-generator-fast-v0"
DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_ARFACE_EXPORT = Path(
    "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/arface_export.json"
)
DEFAULT_VISION = Path(
    "evidence/e7-lip-m1-packages/m1-lip-apple-vision-20260625T132216Z/apple_vision_lip_contour.json"
)
DEFAULT_FACE_PARSING_DIR = Path("evidence/e7-lip-m1-packages/m1-lip-face-parsing-20260625T2255Z")
DEFAULT_COLOR_CONFIDENCE = Path(
    "evidence/e7-lip-m1-packages/m1-lip-color-gradient-20260625T000000Z/color_gradient_confidence.json"
)
DEFAULT_MEDIAPIPE_MODEL = Path(".cache/mediapipe/face_landmarker.task")
DEFAULT_OUTPUT_ROOT = Path("evidence/e7-lip-candidate-generator")
DEFAULT_UNITY_RESOURCE_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
CANDIDATES = (
    "parsing_curve_smooth",
    "vision_curve_fill",
    "vision_color_snap",
    "hybrid_curve_safe",
    "hybrid_curve_balanced",
)
CANDIDATE_RUNTIME = {
    "parsing_curve_smooth": {
        "candidateId": "cv-parsing-smooth-v1",
        "unityMaskTextureId": "e7-lip-validation-cv-parsing-smooth-v1",
        "label": "parsing",
        "status": "cv-smooth",
        "threshold": 0.50,
        "coverage": 0.70,
        "feather": 0.075,
    },
    "vision_curve_fill": {
        "candidateId": "cv-vision-fill-v1",
        "unityMaskTextureId": "e7-lip-validation-cv-vision-fill-v1",
        "label": "vision",
        "status": "curve-fill",
        "threshold": 0.50,
        "coverage": 0.69,
        "feather": 0.07,
    },
    "vision_color_snap": {
        "candidateId": "cv-vision-color-v1",
        "unityMaskTextureId": "e7-lip-validation-cv-vision-color-v1",
        "label": "color",
        "status": "edge-snap",
        "threshold": 0.50,
        "coverage": 0.69,
        "feather": 0.07,
    },
    "hybrid_curve_safe": {
        "candidateId": "cv-hybrid-safe-v1",
        "unityMaskTextureId": "e7-lip-validation-cv-hybrid-safe-v1",
        "label": "safe2",
        "status": "low-spill",
        "threshold": 0.54,
        "coverage": 0.66,
        "feather": 0.065,
    },
    "hybrid_curve_balanced": {
        "candidateId": "cv-hybrid-balanced-v1",
        "unityMaskTextureId": "e7-lip-validation-cv-hybrid-balanced-v1",
        "label": "bal2",
        "status": "coverage",
        "threshold": 0.52,
        "coverage": 0.70,
        "feather": 0.07,
    },
}
ADJUSTMENT_FIELDS = ("cornerReach", "upperLipTightness", "lowerLipTightness", "verticalOffset")
MEDIAPIPE_OUTER_LIP = (61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185)
MEDIAPIPE_INNER_LIP = (78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191)


@dataclass
class Candidate:
    candidate_id: str
    mask: np.ndarray
    alpha: np.ndarray
    curve_points: list[tuple[float, float]]
    trace: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build fast E7 lip boundary candidates.")
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--arface-export", type=Path, default=DEFAULT_ARFACE_EXPORT)
    parser.add_argument("--vision", type=Path, default=DEFAULT_VISION)
    parser.add_argument("--face-parsing-dir", type=Path, default=DEFAULT_FACE_PARSING_DIR)
    parser.add_argument("--color-confidence", type=Path, default=DEFAULT_COLOR_CONFIDENCE)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--uv-resolution", type=int, default=512)
    parser.add_argument("--uv-sample-stride", type=int, default=5)
    parser.add_argument("--curve-samples", type=int, default=180)
    parser.add_argument("--mediapipe-model", type=Path, default=DEFAULT_MEDIAPIPE_MODEL)
    parser.add_argument("--skip-mediapipe", action="store_true")
    parser.add_argument("--install-unity-assets", action="store_true")
    parser.add_argument("--unity-resource-dir", type=Path, default=DEFAULT_UNITY_RESOURCE_DIR)
    parser.add_argument("--mediapipe-child", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--mediapipe-output-dir", type=Path, default=None, help=argparse.SUPPRESS)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "inputs": output_dir / "inputs",
        "candidates": output_dir / "candidates",
        "debug": output_dir / "debug",
        "evaluation": output_dir / "evaluation",
        "report": output_dir / "report",
        "review": output_dir / "review",
        "mediapipe": output_dir / "mediapipe",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def package_status() -> dict[str, Any]:
    packages = {
        "opencv": ("cv2", "opencv-python-headless"),
        "scipy": ("scipy", "scipy"),
        "scikit-image": ("skimage", "scikit-image"),
        "mediapipe": ("mediapipe", "mediapipe"),
        "numpy": ("numpy", "numpy"),
        "pillow": ("PIL", "pillow"),
    }
    status: dict[str, Any] = {}
    for label, (import_name, distribution_name) in packages.items():
        available = importlib.util.find_spec(import_name) is not None
        item: dict[str, Any] = {
            "importName": import_name,
            "distributionName": distribution_name,
            "available": available,
        }
        try:
            item["distributionVersion"] = importlib_metadata.version(distribution_name)
        except importlib_metadata.PackageNotFoundError:
            item["distributionVersion"] = None
        if available and import_name != "mediapipe":
            try:
                module = importlib.import_module(import_name)
                item["moduleVersion"] = getattr(module, "__version__", None)
            except Exception as exception:
                item["moduleImportError"] = f"{exception.__class__.__name__}: {exception}"
        elif available:
            item["moduleVersion"] = item["distributionVersion"]
            item["moduleImportSkipped"] = "Skipped during package status collection; MediaPipe is tested in its child process."
        status[label] = item
    return status


def optional_import(import_name: str) -> Any | None:
    if importlib.util.find_spec(import_name) is None:
        return None
    try:
        return importlib.import_module(import_name)
    except Exception:
        return None


def cv2_module() -> Any | None:
    return optional_import("cv2")


def scipy_ndimage_module() -> Any | None:
    if importlib.util.find_spec("scipy.ndimage") is None:
        return None
    try:
        from scipy import ndimage as ndi  # type: ignore[import-not-found]

        return ndi
    except Exception:
        return None


def skimage_measure_module() -> Any | None:
    if importlib.util.find_spec("skimage.measure") is None:
        return None
    try:
        from skimage import measure  # type: ignore[import-not-found]

        return measure
    except Exception:
        return None


def skimage_morphology_module() -> Any | None:
    if importlib.util.find_spec("skimage.morphology") is None:
        return None
    try:
        from skimage import morphology  # type: ignore[import-not-found]

        return morphology
    except Exception:
        return None


def load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    image = Image.open(path).convert("L")
    if image.size != size:
        image = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(image) > 0


def save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def save_alpha(path: Path, alpha: np.ndarray) -> None:
    Image.fromarray(np.clip(alpha, 0, 255).astype(np.uint8), mode="L").save(path)


def bbox(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {"available": False}
    return {
        "available": True,
        "minX": int(xs.min()),
        "minY": int(ys.min()),
        "maxX": int(xs.max()),
        "maxY": int(ys.max()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
        "positivePixels": int(len(xs)),
    }


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = radius * 2 + 1
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255, mode="L").filter(ImageFilter.MaxFilter(size))) > 0


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = radius * 2 + 1
    return np.asarray(Image.fromarray(mask.astype(np.uint8) * 255, mode="L").filter(ImageFilter.MinFilter(size))) > 0


def close_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    return erode(dilate(mask, radius), radius)


def open_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    return dilate(erode(mask, radius), radius)


def keep_largest_component(mask: np.ndarray) -> np.ndarray:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return mask.copy()
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    best: list[tuple[int, int]] = []
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        component: list[tuple[int, int]] = []
        while stack:
            y, x = stack.pop()
            component.append((y, x))
            for ny in (y - 1, y, y + 1):
                for nx in (x - 1, x, x + 1):
                    if ny == y and nx == x:
                        continue
                    if 0 <= ny < height and 0 <= nx < width and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        if len(component) > len(best):
            best = component
    out = np.zeros_like(mask, dtype=bool)
    if best:
        by, bx = zip(*best)
        out[np.asarray(by), np.asarray(bx)] = True
    return out


def cv_find_largest_contour(mask: np.ndarray) -> Any | None:
    cv2 = cv2_module()
    if cv2 is None or not np.any(mask):
        return None
    contours, _ = cv2.findContours(
        (mask.astype(np.uint8) * 255),
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_NONE,
    )
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def smooth_mask_cv_skimage(mask: np.ndarray, close_radius: int = 3, blur_sigma: float = 1.2) -> np.ndarray:
    """Use available CV libraries to remove jagged bits without changing the source signal role."""
    if not np.any(mask):
        return mask.copy()
    refined = mask.copy()
    morphology = skimage_morphology_module()
    if morphology is not None:
        refined = morphology.remove_small_objects(refined.astype(bool), max_size=48)
        refined = morphology.remove_small_holes(refined.astype(bool), max_size=48)
    cv2 = cv2_module()
    if cv2 is not None:
        source = (refined.astype(np.uint8) * 255)
        kernel_size = max(1, close_radius * 2 + 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        source = cv2.morphologyEx(source, cv2.MORPH_CLOSE, kernel)
        source = cv2.morphologyEx(source, cv2.MORPH_OPEN, kernel)
        if blur_sigma > 0:
            source = cv2.GaussianBlur(source, (0, 0), blur_sigma)
            source = (source >= 128).astype(np.uint8) * 255
        refined = source > 0
    return keep_largest_component(refined.astype(bool))


def mask_boundary(mask: np.ndarray) -> np.ndarray:
    cv2 = cv2_module()
    if cv2 is not None:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edge = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_GRADIENT, kernel)
        return edge > 0
    return mask & ~erode(mask, 1)


def contour_quality(mask: np.ndarray) -> dict[str, Any]:
    area = int(np.count_nonzero(mask))
    contour = cv_find_largest_contour(mask)
    if area == 0 or contour is None:
        return {
            "available": False,
            "perimeterPx": 0.0,
            "roughnessIndex": None,
            "solidity": None,
        }
    cv2 = cv2_module()
    perimeter = float(cv2.arcLength(contour, True)) if cv2 is not None else float(np.count_nonzero(mask_boundary(mask)))
    hull = cv2.convexHull(contour) if cv2 is not None else None
    hull_area = float(cv2.contourArea(hull)) if cv2 is not None and hull is not None else 0.0
    circle_perimeter = 2.0 * math.pi * math.sqrt(max(area, 1) / math.pi)
    return {
        "available": True,
        "perimeterPx": round(perimeter, 3),
        "roughnessIndex": round(perimeter / circle_perimeter, 6) if circle_perimeter else None,
        "solidity": round(area / hull_area, 6) if hull_area > 0 else None,
    }


def boundary_points_from_mask(mask: np.ndarray, samples: int = 180) -> list[tuple[float, float]]:
    mask = keep_largest_component(mask)
    ys, xs = np.where(mask)
    if len(xs) < 16:
        return []
    cx = float(xs.mean())
    cy = float(ys.mean())
    edge = mask & ~erode(mask, 1)
    eys, exs = np.where(edge)
    if len(exs) < 16:
        return []
    angles = np.arctan2(eys.astype(np.float64) - cy, exs.astype(np.float64) - cx)
    radii = np.sqrt(((exs.astype(np.float64) - cx) ** 2) + ((eys.astype(np.float64) - cy) ** 2))
    bins: list[tuple[float, float]] = []
    for index in range(samples):
        start = -math.pi + (2.0 * math.pi * index / samples)
        end = -math.pi + (2.0 * math.pi * (index + 1) / samples)
        if index == samples - 1:
            selected = (angles >= start) & (angles <= end)
        else:
            selected = (angles >= start) & (angles < end)
        if not np.any(selected):
            continue
        local = np.where(selected)[0]
        best = local[int(np.argmax(radii[local]))]
        bins.append((float(exs[best]), float(eys[best])))
    return bins


def chaikin(points: list[tuple[float, float]], iterations: int = 3, closed: bool = True) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points
    current = points[:]
    for _ in range(iterations):
        next_points: list[tuple[float, float]] = []
        count = len(current)
        pairs = count if closed else count - 1
        for i in range(pairs):
            p0 = current[i]
            p1 = current[(i + 1) % count]
            q = (0.75 * p0[0] + 0.25 * p1[0], 0.75 * p0[1] + 0.25 * p1[1])
            r = (0.25 * p0[0] + 0.75 * p1[0], 0.25 * p0[1] + 0.75 * p1[1])
            next_points.extend([q, r])
        if not closed:
            next_points.insert(0, current[0])
            next_points.append(current[-1])
        current = next_points
    return current


def resample_polyline(points: list[tuple[float, float]], max_points: int = 240) -> list[tuple[float, float]]:
    if len(points) <= max_points:
        return points
    step = max(1, len(points) // max_points)
    return points[::step]


def fill_polygon(
    points: list[tuple[float, float]],
    size: tuple[int, int],
    holes: list[list[tuple[float, float]]] | None = None,
) -> np.ndarray:
    image = Image.new("L", size, 0)
    draw = ImageDraw.Draw(image)
    if len(points) >= 3:
        draw.polygon([(float(x), float(y)) for x, y in points], fill=255)
    for hole in holes or []:
        if len(hole) >= 3:
            draw.polygon([(float(x), float(y)) for x, y in hole], fill=0)
    return np.asarray(image) > 0


def make_soft_alpha(mask: np.ndarray, blur_radius: float = 2.2) -> np.ndarray:
    base = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    blurred = base.filter(ImageFilter.GaussianBlur(blur_radius))
    return np.asarray(blurred, dtype=np.uint8)


def contour_from_vision(vision: dict[str, Any], key: str) -> list[tuple[float, float]]:
    contour = vision.get("contours", {}).get(key, {})
    points: list[tuple[float, float]] = []
    for point in contour.get("imagePoints", []):
        if isinstance(point, dict) and isinstance(point.get("x"), (int, float)) and isinstance(
            point.get("y"), (int, float)
        ):
            points.append((float(point["x"]), float(point["y"])))
    return points


def curve_center(points: list[tuple[float, float]], fallback: tuple[float, float]) -> tuple[float, float]:
    if not points:
        return fallback
    arr = np.asarray(points, dtype=np.float64)
    return float(arr[:, 0].mean()), float(arr[:, 1].mean())


def snap_curve_to_color_edge(
    points: list[tuple[float, float]],
    frame: Image.Image,
    max_offset: int = 8,
) -> tuple[list[tuple[float, float]], dict[str, Any], np.ndarray]:
    if len(points) < 3:
        empty = np.zeros((frame.height, frame.width), dtype=bool)
        return points, {"status": "skipped_insufficient_points"}, empty
    rgb = np.asarray(frame.convert("RGB"), dtype=np.float32)
    cv2 = cv2_module()
    if cv2 is not None:
        lab = cv2.cvtColor(np.asarray(frame.convert("RGB"), dtype=np.uint8), cv2.COLOR_RGB2LAB).astype(np.float32)
        gradient = np.zeros((frame.height, frame.width), dtype=np.float32)
        for channel_index, weight in ((0, 0.45), (1, 0.35), (2, 0.20)):
            gx = cv2.Sobel(lab[:, :, channel_index], cv2.CV_32F, 1, 0, ksize=3)
            gy = cv2.Sobel(lab[:, :, channel_index], cv2.CV_32F, 0, 1, ksize=3)
            gradient += weight * np.sqrt((gx * gx) + (gy * gy))
        gradient_source = "opencv_lab_sobel"
    else:
        luma = (rgb[:, :, 0] * 0.299) + (rgb[:, :, 1] * 0.587) + (rgb[:, :, 2] * 0.114)
        grad_y, grad_x = np.gradient(luma)
        gradient = np.sqrt((grad_x * grad_x) + (grad_y * grad_y))
        gradient_source = "numpy_luma_gradient"
    cx, cy = curve_center(points, (frame.width / 2.0, frame.height / 2.0))
    snapped: list[tuple[float, float]] = []
    band = np.zeros((frame.height, frame.width), dtype=bool)
    movements: list[float] = []
    for x, y in points:
        vx = x - cx
        vy = y - cy
        length = math.sqrt((vx * vx) + (vy * vy))
        if length < 1e-6:
            snapped.append((x, y))
            continue
        nx = vx / length
        ny = vy / length
        best_score = -1.0
        best_point = (x, y)
        for offset in range(-max_offset, max_offset + 1):
            sx = int(round(x + nx * offset))
            sy = int(round(y + ny * offset))
            if not (1 <= sx < frame.width - 1 and 1 <= sy < frame.height - 1):
                continue
            band[sy, sx] = True
            score = float(gradient[sy, sx]) - (abs(offset) * 1.5)
            if score > best_score:
                best_score = score
                best_point = (float(sx), float(sy))
        snapped.append(best_point)
        movements.append(math.sqrt(((best_point[0] - x) ** 2) + ((best_point[1] - y) ** 2)))
    return snapped, {
        "status": "applied",
        "gradientSource": gradient_source,
        "maxOffsetPx": max_offset,
        "meanMovementPx": round(float(np.mean(movements)), 3) if movements else 0.0,
        "maxMovementPx": round(float(np.max(movements)), 3) if movements else 0.0,
    }, dilate(band, 2)


def draw_points(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], color: tuple[int, int, int], width: int) -> None:
    if len(points) >= 2:
        draw.line(points + [points[0]], fill=color, width=width, joint="curve")
    for x, y in points:
        r = max(2, width)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def overlay_masks(frame: Image.Image, masks: list[tuple[np.ndarray, tuple[int, int, int], float]]) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    for mask, color, alpha in masks:
        if mask is None:
            continue
        index = mask.astype(bool)
        base[index] = (base[index] * (1.0 - alpha)) + (np.asarray(color, dtype=np.float32) * alpha)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def write_curve_overlay(
    frame: Image.Image,
    mask: np.ndarray,
    points: list[tuple[float, float]],
    output_path: Path,
    title: str,
) -> None:
    image = overlay_masks(frame, [(mask, (255, 42, 96), 0.42)]).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw_points(draw, points, (70, 255, 110), 3)
    draw.rectangle((0, 0, min(image.width - 1, 780), 42), fill=(0, 0, 0))
    draw.text((12, 12), title, fill=(255, 255, 255))
    image.save(output_path)


def write_input_overlays(
    dirs: dict[str, Path],
    frame: Image.Image,
    vision: dict[str, Any] | None,
    parsing_lip: np.ndarray | None,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
    skin: np.ndarray | None,
    color_band: np.ndarray,
    arface_export: dict[str, Any] | None,
) -> None:
    overview = frame.convert("RGB")
    overview.save(dirs["inputs"] / "input_overview.png")

    vision_img = frame.convert("RGB")
    draw = ImageDraw.Draw(vision_img)
    if vision:
        draw_points(draw, contour_from_vision(vision, "outerLips"), (80, 255, 120), 4)
        draw_points(draw, contour_from_vision(vision, "innerLips"), (255, 230, 60), 3)
    vision_img.save(dirs["inputs"] / "vision_points_overlay.png")

    masks: list[tuple[np.ndarray, tuple[int, int, int], float]] = []
    if skin is not None:
        masks.append((skin, (0, 170, 255), 0.18))
    if upper is not None:
        masks.append((upper, (255, 42, 116), 0.55))
    if lower is not None:
        masks.append((lower, (255, 128, 40), 0.55))
    if parsing_lip is not None:
        edge = parsing_lip & ~erode(parsing_lip, 1)
        masks.append((edge, (255, 255, 80), 0.90))
    overlay_masks(frame, masks).save(dirs["inputs"] / "parsing_masks_overlay.png")

    overlay_masks(frame, [(color_band, (80, 255, 120), 0.70)]).save(dirs["inputs"] / "color_edge_band_overlay.png")

    mesh_img = frame.convert("RGB")
    mesh_draw = ImageDraw.Draw(mesh_img)
    if arface_export:
        screen_vertices = np.asarray(arface_export.get("screenVertices", []), dtype=np.float64)
        indices = np.asarray(arface_export.get("indices", []), dtype=np.int32).reshape(-1)
        if screen_vertices.ndim == 2 and screen_vertices.shape[1] >= 2 and len(indices) >= 3:
            for tri in indices[: min(len(indices), 1400 * 3)].reshape(-1, 3):
                if np.any(tri < 0) or np.any(tri >= len(screen_vertices)):
                    continue
                pts = [(float(screen_vertices[i, 0]), float(screen_vertices[i, 1])) for i in tri]
                mesh_draw.line(pts + [pts[0]], fill=(0, 255, 255), width=1)
    mesh_img.save(dirs["inputs"] / "arface_mesh_overlay.png")


def subtract_optional(mask: np.ndarray, subtract_mask: np.ndarray | None) -> np.ndarray:
    return mask & ~subtract_mask if subtract_mask is not None else mask


def build_candidates(
    frame: Image.Image,
    vision: dict[str, Any] | None,
    parsing_lip: np.ndarray,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
    inner: np.ndarray | None,
    skin: np.ndarray | None,
    samples: int,
) -> tuple[dict[str, Candidate], dict[str, Any], np.ndarray]:
    size = frame.size
    candidates: dict[str, Candidate] = {}
    warnings: dict[str, Any] = {}

    parsing_source = close_mask(open_mask(parsing_lip, 1), 2)
    parsing_points = chaikin(resample_polyline(boundary_points_from_mask(parsing_source, samples=samples)), 3)
    parsing_mask = keep_largest_component(close_mask(fill_polygon(parsing_points, size), 1))
    parsing_mask = smooth_mask_cv_skimage(parsing_mask, close_radius=2, blur_sigma=0.9)
    parsing_mask = subtract_optional(parsing_mask, inner)
    candidates["parsing_curve_smooth"] = Candidate(
        "parsing_curve_smooth",
        parsing_mask,
        make_soft_alpha(parsing_mask),
        parsing_points,
        {
            "sourceSignals": ["face_parsing_lip_mask", "face_parsing_upper_lower_if_available"],
            "steps": [
                "extract parsing lip boundary",
                "reduce and smooth boundary points",
                "fill smoothed curve",
                "clean boundary with OpenCV/scikit-image when available",
                "subtract inner mouth if available",
            ],
            "inputPixels": int(np.count_nonzero(parsing_lip)),
            "outputPixels": int(np.count_nonzero(parsing_mask)),
        },
    )

    outer = contour_from_vision(vision or {}, "outerLips")
    inner_points = contour_from_vision(vision or {}, "innerLips")
    if len(outer) < 3:
        warnings["vision"] = "outer_lips_points_missing_or_insufficient"
        outer = parsing_points
        inner_points = []
    vision_curve = chaikin(outer, 4)
    inner_curve = chaikin(inner_points, 3) if len(inner_points) >= 3 else []
    vision_mask = keep_largest_component(close_mask(fill_polygon(vision_curve, size, [inner_curve] if inner_curve else None), 1))
    vision_mask = smooth_mask_cv_skimage(vision_mask, close_radius=1, blur_sigma=0.7)
    vision_mask = subtract_optional(vision_mask, inner)
    candidates["vision_curve_fill"] = Candidate(
        "vision_curve_fill",
        vision_mask,
        make_soft_alpha(vision_mask),
        vision_curve,
        {
            "sourceSignals": ["apple_vision_outer_lips", "apple_vision_inner_lips"],
            "steps": [
                "read Vision points",
                "smooth closed curve",
                "fill outer curve",
                "clean boundary with OpenCV/scikit-image when available",
                "subtract inner curve when usable",
            ],
            "outerPointCount": len(outer),
            "innerPointCount": len(inner_points),
            "outputPixels": int(np.count_nonzero(vision_mask)),
        },
    )

    snapped_curve, snap_report, color_band = snap_curve_to_color_edge(vision_curve, frame, max_offset=8)
    snap_mask = keep_largest_component(close_mask(fill_polygon(snapped_curve, size, [inner_curve] if inner_curve else None), 1))
    snap_mask = smooth_mask_cv_skimage(snap_mask, close_radius=1, blur_sigma=0.7)
    snap_mask = subtract_optional(snap_mask, inner)
    candidates["vision_color_snap"] = Candidate(
        "vision_color_snap",
        snap_mask,
        make_soft_alpha(snap_mask),
        snapped_curve,
        {
            "sourceSignals": ["apple_vision_outer_lips", "frame_luma_gradient", "limited_color_edge_band"],
            "steps": [
                "start from Vision curve",
                "scan local normal band",
                "move points to strong LAB/luma gradient",
                "fill curve",
                "clean boundary with OpenCV/scikit-image when available",
            ],
            "snapReport": snap_report,
            "outputPixels": int(np.count_nonzero(snap_mask)),
        },
    )

    near_parsing = dilate(parsing_mask, 7)
    near_snap = dilate(snap_mask, 7)
    safe = (parsing_mask & near_snap) | (snap_mask & dilate(parsing_mask, 3))
    safe = keep_largest_component(erode(close_mask(safe, 2), 1))
    if skin is not None:
        skin_guard = skin & ~dilate(parsing_mask | snap_mask, 4)
        safe &= ~skin_guard
    safe = subtract_optional(safe, inner)
    safe_points = chaikin(resample_polyline(boundary_points_from_mask(safe, samples=samples)), 3)
    safe = keep_largest_component(fill_polygon(safe_points, size)) if len(safe_points) >= 3 else safe
    safe = smooth_mask_cv_skimage(safe, close_radius=2, blur_sigma=0.9)
    safe = subtract_optional(safe, inner)
    candidates["hybrid_curve_safe"] = Candidate(
        "hybrid_curve_safe",
        safe,
        make_soft_alpha(safe, 2.0),
        safe_points,
        {
            "sourceSignals": ["face_parsing_curve", "vision_color_snap", "skin_mask_guard", "inner_mouth_mask_if_available"],
            "steps": [
                "intersect/near-overlap parsing and color-snapped Vision masks",
                "erode once for spill prevention",
                "remove confident skin guard",
                "smooth final boundary",
                "clean boundary with OpenCV/scikit-image when available",
            ],
            "outputPixels": int(np.count_nonzero(safe)),
        },
    )

    balanced = safe | ((snap_mask | vision_mask) & dilate(parsing_mask, 11)) | (parsing_mask & dilate(vision_mask, 8))
    if upper is not None and np.any(upper):
        balanced |= upper & dilate(snap_mask | vision_mask | parsing_mask, 8)
    if lower is not None and np.any(lower):
        balanced |= lower & dilate(safe | snap_mask | parsing_mask, 5)
    balanced = keep_largest_component(close_mask(balanced, 2))
    if skin is not None:
        balanced &= ~(skin & ~dilate(safe | parsing_mask | snap_mask, 6))
    balanced = subtract_optional(balanced, inner)
    balanced_points = chaikin(resample_polyline(boundary_points_from_mask(balanced, samples=samples)), 3)
    balanced = keep_largest_component(fill_polygon(balanced_points, size)) if len(balanced_points) >= 3 else balanced
    balanced = smooth_mask_cv_skimage(balanced, close_radius=2, blur_sigma=0.9)
    balanced = subtract_optional(balanced, inner)
    candidates["hybrid_curve_balanced"] = Candidate(
        "hybrid_curve_balanced",
        balanced,
        make_soft_alpha(balanced, 2.3),
        balanced_points,
        {
            "sourceSignals": [
                "hybrid_curve_safe",
                "vision_curve_fill",
                "vision_color_snap",
                "face_parsing_upper_lower",
            ],
            "steps": [
                "start from safe mask",
                "restore Vision-supported corners/coverage near parsing",
                "preserve upper/lower parsing support",
                "skin guard rollback",
                "smooth final boundary",
                "clean boundary with OpenCV/scikit-image when available",
            ],
            "outputPixels": int(np.count_nonzero(balanced)),
        },
    )
    return candidates, warnings, color_band


def export_arrays(export: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    screen_vertices = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    uvs = np.asarray(export.get("uvs", []), dtype=np.float64)
    indices = np.asarray(export.get("indices", []), dtype=np.int32)
    if indices.ndim != 1:
        indices = indices.reshape(-1)
    return screen_vertices, uvs, indices


def iter_triangles(indices: np.ndarray) -> np.ndarray:
    usable = (len(indices) // 3) * 3
    return indices[:usable].reshape(-1, 3)


def barycentric_grid(
    xs: np.ndarray, ys: np.ndarray, tri_xy: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x0, y0 = tri_xy[0]
    x1, y1 = tri_xy[1]
    x2, y2 = tri_xy[2]
    denom = ((y1 - y2) * (x0 - x2)) + ((x2 - x1) * (y0 - y2))
    if abs(float(denom)) < 1e-6:
        empty = np.zeros(xs.shape, dtype=bool)
        return empty, xs, xs, xs
    w0 = (((y1 - y2) * (xs - x2)) + ((x2 - x1) * (ys - y2))) / denom
    w1 = (((y2 - y0) * (xs - x2)) + ((x0 - x2) * (ys - y2))) / denom
    w2 = 1.0 - w0 - w1
    inside = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
    return inside, w0, w1, w2


def interpolate_uv(
    tri_uv: np.ndarray, tri_w: np.ndarray, w0: np.ndarray, w1: np.ndarray, w2: np.ndarray
) -> np.ndarray:
    clip_w = np.where(np.abs(tri_w) < 1e-6, 1.0, tri_w)
    inv_w = 1.0 / clip_w
    denom = (w0 * inv_w[0]) + (w1 * inv_w[1]) + (w2 * inv_w[2])
    denom = np.where(np.abs(denom) < 1e-6, 1.0, denom)
    u = ((w0 * tri_uv[0, 0] * inv_w[0]) + (w1 * tri_uv[1, 0] * inv_w[1]) + (w2 * tri_uv[2, 0] * inv_w[2])) / denom
    v = ((w0 * tri_uv[0, 1] * inv_w[0]) + (w1 * tri_uv[1, 1] * inv_w[1]) + (w2 * tri_uv[2, 1] * inv_w[2])) / denom
    return np.column_stack((u, v))


def uv_to_rc(uv: np.ndarray, resolution: int) -> tuple[np.ndarray, np.ndarray]:
    u = np.clip(uv[:, 0], 0.0, 1.0)
    v = np.clip(uv[:, 1], 0.0, 1.0)
    cols = np.rint(u * (resolution - 1)).astype(np.int32)
    rows = np.rint((1.0 - v) * (resolution - 1)).astype(np.int32)
    return rows, cols


def back_project_mask(mask: np.ndarray, export: dict[str, Any], resolution: int, sample_stride: int) -> np.ndarray:
    screen_vertices, uvs, indices = export_arrays(export)
    positive_votes = np.zeros((resolution, resolution), dtype=np.uint32)
    total_votes = np.zeros((resolution, resolution), dtype=np.uint32)
    height, width = mask.shape
    if screen_vertices.ndim != 2 or uvs.ndim != 2 or len(screen_vertices) != len(uvs):
        return np.zeros((resolution, resolution), dtype=np.float32)
    for tri in iter_triangles(indices):
        if np.any(tri < 0) or np.any(tri >= len(screen_vertices)):
            continue
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(float(np.min(tri_xy[:, 0])))))
        max_x = min(width - 1, int(math.ceil(float(np.max(tri_xy[:, 0])))))
        min_y = max(0, int(math.floor(float(np.min(tri_xy[:, 1])))))
        max_y = min(height - 1, int(math.ceil(float(np.max(tri_xy[:, 1])))))
        if max_x < min_x or max_y < min_y:
            continue
        xs, ys = np.meshgrid(
            np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64),
            np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64),
        )
        inside, w0, w1, w2 = barycentric_grid(xs, ys, tri_xy)
        if not np.any(inside):
            continue
        uv = interpolate_uv(
            uvs[tri],
            tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3),
            w0[inside],
            w1[inside],
            w2[inside],
        )
        rows, cols = uv_to_rc(uv, resolution)
        inside_x = xs[inside].astype(np.int32)
        inside_y = ys[inside].astype(np.int32)
        positive = mask[inside_y, inside_x]
        np.add.at(total_votes, (rows, cols), 1)
        np.add.at(positive_votes, (rows[positive], cols[positive]), 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.divide(positive_votes, total_votes, out=np.zeros_like(positive_votes, dtype=np.float32), where=total_votes > 0)


def render_atlas_to_screen(
    probability: np.ndarray, export: dict[str, Any], frame_size: tuple[int, int], threshold: float, sample_stride: int
) -> np.ndarray:
    screen_vertices, uvs, indices = export_arrays(export)
    width, height = frame_size
    predicted = np.zeros((height, width), dtype=bool)
    if screen_vertices.ndim != 2 or uvs.ndim != 2 or len(screen_vertices) != len(uvs):
        return predicted
    for tri in iter_triangles(indices):
        if np.any(tri < 0) or np.any(tri >= len(screen_vertices)):
            continue
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(float(np.min(tri_xy[:, 0])))))
        max_x = min(width - 1, int(math.ceil(float(np.max(tri_xy[:, 0])))))
        min_y = max(0, int(math.floor(float(np.min(tri_xy[:, 1])))))
        max_y = min(height - 1, int(math.ceil(float(np.max(tri_xy[:, 1])))))
        if max_x < min_x or max_y < min_y:
            continue
        xs, ys = np.meshgrid(
            np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64),
            np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64),
        )
        inside, w0, w1, w2 = barycentric_grid(xs, ys, tri_xy)
        if not np.any(inside):
            continue
        uv = interpolate_uv(
            uvs[tri],
            tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3),
            w0[inside],
            w1[inside],
            w2[inside],
        )
        rows, cols = uv_to_rc(uv, probability.shape[0])
        selected = probability[rows, cols] >= threshold
        inside_x = xs[inside].astype(np.int32)
        inside_y = ys[inside].astype(np.int32)
        predicted[inside_y[selected], inside_x[selected]] = True
    return predicted


def round_trip_overlay(frame: Image.Image, reference: np.ndarray, predicted: np.ndarray) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    tp = reference & predicted
    ref_only = reference & ~predicted
    pred_only = predicted & ~reference
    base[tp] = base[tp] * 0.45 + np.asarray([255, 40, 120], dtype=np.float32) * 0.55
    base[ref_only] = base[ref_only] * 0.35 + np.asarray([255, 230, 40], dtype=np.float32) * 0.65
    base[pred_only] = base[pred_only] * 0.35 + np.asarray([40, 180, 255], dtype=np.float32) * 0.65
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def comparison_metrics(candidate: np.ndarray, reference: np.ndarray | None) -> dict[str, Any]:
    if reference is None or candidate.shape != reference.shape or not np.any(reference):
        return {"available": False}
    tp = int(np.count_nonzero(candidate & reference))
    fp = int(np.count_nonzero(candidate & ~reference))
    fn = int(np.count_nonzero(~candidate & reference))
    union = tp + fp + fn
    cand = int(np.count_nonzero(candidate))
    ref = int(np.count_nonzero(reference))
    return {
        "available": True,
        "iou": round(tp / union, 6) if union else 0.0,
        "dice": round((2 * tp) / ((2 * tp) + fp + fn), 6) if ((2 * tp) + fp + fn) else 0.0,
        "precision": round(tp / (tp + fp), 6) if (tp + fp) else 0.0,
        "recall": round(tp / (tp + fn), 6) if (tp + fn) else 0.0,
        "outsideReference": round(fp / cand, 6) if cand else 0.0,
        "missReference": round(fn / ref, 6) if ref else 0.0,
    }


def boundary_distance_metrics(candidate: np.ndarray, reference: np.ndarray | None) -> dict[str, Any]:
    if reference is None or candidate.shape != reference.shape or not np.any(candidate) or not np.any(reference):
        return {"available": False}
    ndi = scipy_ndimage_module()
    if ndi is None:
        return {"available": False, "reason": "scipy_ndimage_unavailable"}
    candidate_edge = mask_boundary(candidate)
    reference_edge = mask_boundary(reference)
    if not np.any(candidate_edge) or not np.any(reference_edge):
        return {"available": False, "reason": "edge_missing"}
    dist_to_reference = ndi.distance_transform_edt(~reference_edge)
    dist_to_candidate = ndi.distance_transform_edt(~candidate_edge)
    candidate_to_reference = dist_to_reference[candidate_edge]
    reference_to_candidate = dist_to_candidate[reference_edge]
    symmetric = np.concatenate([candidate_to_reference, reference_to_candidate])
    return {
        "available": True,
        "candidateToReferenceMeanPx": round(float(np.mean(candidate_to_reference)), 4),
        "candidateToReferenceP95Px": round(float(np.percentile(candidate_to_reference, 95)), 4),
        "candidateToReferenceMaxPx": round(float(np.max(candidate_to_reference)), 4),
        "referenceToCandidateMeanPx": round(float(np.mean(reference_to_candidate)), 4),
        "referenceToCandidateP95Px": round(float(np.percentile(reference_to_candidate, 95)), 4),
        "referenceToCandidateMaxPx": round(float(np.max(reference_to_candidate)), 4),
        "symmetricMeanPx": round(float(np.mean(symmetric)), 4),
        "symmetricP95Px": round(float(np.percentile(symmetric, 95)), 4),
    }


def component_metrics(mask: np.ndarray) -> dict[str, Any]:
    measure = skimage_measure_module()
    ndi = scipy_ndimage_module()
    if measure is not None:
        labels = measure.label(mask.astype(bool), connectivity=2)
        component_count = int(labels.max())
    else:
        cv2 = cv2_module()
        if cv2 is not None:
            component_count = int(cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)[0] - 1)
        else:
            component_count = 1 if np.any(mask) else 0
    hole_pixels = 0
    hole_component_count = 0
    if ndi is not None and np.any(mask):
        filled = ndi.binary_fill_holes(mask)
        holes = filled & ~mask
        hole_pixels = int(np.count_nonzero(holes))
        if measure is not None:
            hole_component_count = int(measure.label(holes.astype(bool), connectivity=2).max())
    return {
        "componentCount": component_count,
        "holePixels": hole_pixels,
        "holeComponentCount": hole_component_count,
    }


def corner_recall_metrics(candidate: np.ndarray, reference: np.ndarray | None) -> dict[str, Any]:
    if reference is None or candidate.shape != reference.shape or not np.any(reference):
        return {"available": False}
    box = bbox(reference)
    if not box.get("available"):
        return {"available": False}
    width = max(1, int(box["width"]))
    left_limit = int(box["minX"] + max(2, round(width * 0.18)))
    right_limit = int(box["maxX"] - max(2, round(width * 0.18)))
    yy, xx = np.indices(reference.shape)
    left_ref = reference & (xx <= left_limit)
    right_ref = reference & (xx >= right_limit)

    def recall(region: np.ndarray) -> float | None:
        total = int(np.count_nonzero(region))
        if total == 0:
            return None
        return round(float(np.count_nonzero(candidate & region) / total), 6)

    left_total = int(np.count_nonzero(left_ref))
    right_total = int(np.count_nonzero(right_ref))
    return {
        "available": True,
        "leftCornerRecall": recall(left_ref),
        "rightCornerRecall": recall(right_ref),
        "leftCornerMissPixels": int(np.count_nonzero(left_ref & ~candidate)),
        "rightCornerMissPixels": int(np.count_nonzero(right_ref & ~candidate)),
        "leftCornerReferencePixels": left_total,
        "rightCornerReferencePixels": right_total,
    }


def symmetry_metrics(mask: np.ndarray) -> dict[str, Any]:
    box = bbox(mask)
    if not box.get("available"):
        return {"available": False}
    center_x = (float(box["minX"]) + float(box["maxX"])) / 2.0
    yy, xx = np.indices(mask.shape)
    left = int(np.count_nonzero(mask & (xx < center_x)))
    right = int(np.count_nonzero(mask & (xx >= center_x)))
    total = left + right
    return {
        "available": True,
        "leftPixels": left,
        "rightPixels": right,
        "leftRightAbsDiffRatio": round(abs(left - right) / total, 6) if total else None,
    }


def upper_lower_metrics(mask: np.ndarray, upper: np.ndarray | None, lower: np.ndarray | None) -> dict[str, Any]:
    if not np.any(mask):
        return {"available": False}
    if upper is not None and lower is not None and np.any(upper | lower):
        upper_pixels = int(np.count_nonzero(mask & upper))
        lower_pixels = int(np.count_nonzero(mask & lower))
        source = "face_parsing_upper_lower"
    else:
        box = bbox(mask)
        if not box.get("available"):
            return {"available": False}
        split_y = int(round((float(box["minY"]) + float(box["maxY"])) / 2.0))
        yy, _ = np.indices(mask.shape)
        upper_pixels = int(np.count_nonzero(mask & (yy <= split_y)))
        lower_pixels = int(np.count_nonzero(mask & (yy > split_y)))
        source = "bbox_midline"
    total = upper_pixels + lower_pixels
    return {
        "available": True,
        "source": source,
        "upperPixels": upper_pixels,
        "lowerPixels": lower_pixels,
        "upperLowerRatio": round(upper_pixels / total, 6) if total else None,
    }


def advanced_candidate_metrics(
    candidate: np.ndarray,
    reference: np.ndarray | None,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
) -> dict[str, Any]:
    positive = int(np.count_nonzero(candidate))
    reference_positive = int(np.count_nonzero(reference)) if reference is not None and reference.shape == candidate.shape else None
    area_change = None
    if reference_positive:
        area_change = round((positive - reference_positive) / reference_positive, 6)
    return {
        "schemaVersion": "e7-lip-candidate-evaluation-v1",
        "positivePixels": positive,
        "referencePixels": reference_positive,
        "areaChangeVsGold": area_change,
        "bbox": bbox(candidate),
        "goldOverlap": comparison_metrics(candidate, reference),
        "boundaryDistance": boundary_distance_metrics(candidate, reference),
        "cornerRecall": corner_recall_metrics(candidate, reference),
        "contourQuality": contour_quality(candidate),
        "components": component_metrics(candidate),
        "symmetry": symmetry_metrics(candidate),
        "upperLower": upper_lower_metrics(candidate, upper, lower),
    }


def write_failure_overlay(
    frame: Image.Image,
    candidate: np.ndarray,
    reference: np.ndarray | None,
    output_path: Path,
    title: str,
) -> None:
    if reference is None or reference.shape != candidate.shape:
        edge = mask_boundary(candidate)
        image = overlay_masks(frame, [(candidate, (255, 42, 96), 0.34), (edge, (80, 255, 120), 0.90)]).convert("RGB")
    else:
        tp = candidate & reference
        ref_only = reference & ~candidate
        candidate_only = candidate & ~reference
        candidate_edge = mask_boundary(candidate)
        reference_edge = mask_boundary(reference)
        image = overlay_masks(
            frame,
            [
                (tp, (255, 42, 96), 0.40),
                (ref_only, (255, 220, 40), 0.75),
                (candidate_only, (40, 180, 255), 0.70),
                (candidate_edge, (70, 255, 110), 0.90),
                (reference_edge, (255, 255, 255), 0.75),
            ],
        ).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, min(image.width - 1, 920), 52), fill=(0, 0, 0))
    draw.text((12, 16), title, fill=(255, 255, 255))
    image.save(output_path)


def load_gold_reference(size: tuple[int, int]) -> np.ndarray | None:
    path = Path(
        "evidence/e7-lip-mask-derivation/experiment-20260625T214159Z/gold_extracted_masks/"
        "user-gold-lip-mask-gray-20260625-163204_gold_exact_binary.png"
    )
    if not path.exists():
        return None
    return load_mask(path, size)


def write_contact_sheet(entries: list[tuple[str, Image.Image]], path: Path, thumb_w: int, thumb_h: int) -> None:
    label_h = 34
    cols = 2 if thumb_w >= 480 else 3
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, (label, image) in enumerate(entries):
        col = idx % cols
        row = idx // cols
        thumb = ImageOps.exif_transpose(image.convert("RGB"))
        thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = col * thumb_w + (thumb_w - thumb.width) // 2
        y = row * (thumb_h + label_h)
        sheet.paste(thumb, (x, y))
        draw.rectangle((col * thumb_w, y + thumb_h, (col + 1) * thumb_w - 1, y + thumb_h + label_h), fill=(245, 245, 245))
        draw.text((col * thumb_w + 8, y + thumb_h + 9), label[:64], fill=(0, 0, 0))
    sheet.save(path)


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = word if not current else f"{current} {word}"
        if len(next_line) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    return lines or [""]


def make_text_panel(size: tuple[int, int], title: str, lines: list[str]) -> Image.Image:
    image = Image.new("RGB", size, (248, 248, 248))
    draw = ImageDraw.Draw(image)
    margin = max(24, min(size) // 18)
    y = margin
    draw.text((margin, y), title, fill=(20, 20, 20))
    y += 44
    for line in lines:
        for chunk in wrap_text(line, max(28, size[0] // 26)):
            draw.text((margin, y), chunk, fill=(45, 45, 45))
            y += 30
        y += 12
    return image


def write_candidate_artifacts(
    dirs: dict[str, Path],
    frame: Image.Image,
    candidates: dict[str, Candidate],
    arface_export: dict[str, Any] | None,
    gold_reference: np.ndarray | None,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[tuple[str, Image.Image]]]:
    metrics_by_candidate: dict[str, Any] = {}
    contact_entries: list[tuple[str, Image.Image]] = []
    for candidate_id in CANDIDATES:
        candidate = candidates[candidate_id]
        mask_path = dirs["candidates"] / f"{candidate_id}_mask.png"
        alpha_path = dirs["candidates"] / f"{candidate_id}_alpha.png"
        overlay_path = dirs["candidates"] / f"{candidate_id}_overlay.png"
        save_mask(mask_path, candidate.mask)
        save_alpha(alpha_path, candidate.alpha)
        write_curve_overlay(frame, candidate.mask, candidate.curve_points, overlay_path, candidate_id)
        write_json(
            dirs["debug"] / f"{candidate_id}_curve_points.json",
            {
                "candidateId": candidate_id,
                "pointCount": len(candidate.curve_points),
                "points": [{"x": round(x, 3), "y": round(y, 3)} for x, y in candidate.curve_points],
            },
        )
        write_json(dirs["debug"] / f"{candidate_id}_generation_trace.json", candidate.trace)
        edge_band = dilate(candidate.mask, 4) & ~erode(candidate.mask, 4)
        overlay_masks(frame, [(edge_band, (80, 255, 120), 0.75)]).save(dirs["debug"] / f"{candidate_id}_edge_band.png")
        curve_overlay = dirs["debug"] / f"{candidate_id}_curve_overlay.png"
        write_curve_overlay(frame, candidate.mask, candidate.curve_points, curve_overlay, f"{candidate_id} curve")
        failure_overlay_path = dirs["evaluation"] / f"{candidate_id}_gold_difference_overlay.png"
        write_failure_overlay(frame, candidate.mask, gold_reference, failure_overlay_path, f"{candidate_id} difference vs gold")

        uv_status: dict[str, Any] = {"available": False}
        if arface_export:
            probability = back_project_mask(candidate.mask, arface_export, args.uv_resolution, args.uv_sample_stride)
            predicted = render_atlas_to_screen(probability, arface_export, frame.size, 0.5, args.uv_sample_stride)
            round_trip_overlay(frame, candidate.mask, predicted).save(dirs["debug"] / f"{candidate_id}_uv_round_trip_overlay.png")
            save_alpha(dirs["debug"] / f"{candidate_id}_uv_probability.png", np.rint(np.clip(probability, 0, 1) * 255).astype(np.uint8))
            uv_status = {
                "available": True,
                "uvResolution": args.uv_resolution,
                "sampleStride": args.uv_sample_stride,
                "roundTrip": comparison_metrics(predicted, candidate.mask),
            }
        else:
            Image.new("RGB", frame.size, "white").save(dirs["debug"] / f"{candidate_id}_uv_round_trip_overlay.png")

        advanced_metrics = advanced_candidate_metrics(candidate.mask, gold_reference, upper, lower)
        evaluation_path = dirs["evaluation"] / f"{candidate_id}_evaluation.json"
        write_json(evaluation_path, advanced_metrics)
        candidate_metrics = {
            "maskPath": str(mask_path),
            "alphaPath": str(alpha_path),
            "overlayPath": str(overlay_path),
            "failureOverlayPath": str(failure_overlay_path),
            "positivePixels": int(np.count_nonzero(candidate.mask)),
            "bbox": bbox(candidate.mask),
            "goldComparison": comparison_metrics(candidate.mask, gold_reference),
            "advancedEvaluation": advanced_metrics,
            "evaluationPath": str(evaluation_path),
            "uvProjection": uv_status,
            "tracePath": str(dirs["debug"] / f"{candidate_id}_generation_trace.json"),
            "runtime": CANDIDATE_RUNTIME[candidate_id],
        }
        metrics_by_candidate[candidate_id] = candidate_metrics
        contact_entries.append((candidate_id, Image.open(overlay_path).copy()))
    return metrics_by_candidate, contact_entries


def mediapipe_point(landmarks: list[Any], index: int, size: tuple[int, int]) -> tuple[float, float]:
    width, height = size
    landmark = landmarks[index]
    return (float(landmark.x) * width, float(landmark.y) * height)


def write_mediapipe_failure_report(output_dir: Path, reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    report = {
        "schemaVersion": "e7-mediapipe-lip-comparison-v0",
        "createdAtUtc": utc_now(),
        "available": False,
        "reason": reason,
        "role": "additional_comparison_signal_not_replacement",
        "outputs": {},
        "limitations": [
            "MediaPipe is an additional comparison signal, not a replacement for Vision, parsing, color, or ARFace.",
            "No MediaPipe mask should be promoted without visual review on the clean sample and real camera check.",
        ],
    }
    if extra:
        report.update(extra)
    write_json(output_dir / "mediapipe_lip_report.json", report)
    return report


def classify_mediapipe_failure(stderr: str, exit_code: int) -> dict[str, Any]:
    lower = stderr.lower()
    if "graph_service.h:139" in stderr and "drishtimetalhelper" in lower:
        return {
            "mostLikelyRootCause": "FaceLandmarker native graph failed while opening the macOS GL/Metal helper service.",
            "evidence": [
                "MediaPipe import succeeded before the child process ran.",
                "Face Landmarker model file exists.",
                "Input frame path and dimensions were valid.",
                "stderr contains gl_context_nsgl pixel format failure.",
                "stderr contains graph_service.h:139 service unavailable.",
                "stderr stack includes DrishtiMetalHelper.",
                f"process exit code was {exit_code}.",
            ],
            "smallestSafeUnblock": "Treat MediaPipe as a documented failed comparison signal for this buildless run and continue reviewing the 5 core candidates.",
            "coreCandidatesCanContinue": True,
        }
    if "no module named" in lower or "import" in lower:
        return {
            "mostLikelyRootCause": "MediaPipe package import failed in the selected Python environment.",
            "evidence": [f"process exit code was {exit_code}.", "stderr mentions import/module failure."],
            "smallestSafeUnblock": "Record MediaPipe unavailable and continue with the 5 core candidates.",
            "coreCandidatesCanContinue": True,
        }
    return {
        "mostLikelyRootCause": "MediaPipe child process failed before producing a usable lip landmark report.",
        "evidence": [f"process exit code was {exit_code}.", "See mediapipe_process_stderr.txt for the raw failure."],
        "smallestSafeUnblock": "Record the failure and continue with the 5 core candidates.",
        "coreCandidatesCanContinue": True,
    }


def run_mediapipe_child(args: argparse.Namespace) -> int:
    if args.mediapipe_output_dir is None:
        return 2
    output_dir = args.mediapipe_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import mediapipe as mp  # type: ignore[import-not-found]
        from mediapipe.tasks import python as mp_python  # type: ignore[import-not-found]
        from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-not-found]
    except Exception as exception:
        write_mediapipe_failure_report(
            output_dir,
            "mediapipe_import_failed",
            {"exception": exception.__class__.__name__, "message": str(exception)},
        )
        return 3

    if not args.mediapipe_model.exists():
        write_mediapipe_failure_report(
            output_dir,
            "face_landmarker_model_missing",
            {"modelPath": str(args.mediapipe_model)},
        )
        return 4

    frame = Image.open(args.frame).convert("RGB")
    size = frame.size
    base_options = mp_python.BaseOptions(
        model_asset_path=str(args.mediapipe_model),
        delegate=mp_python.BaseOptions.Delegate.CPU,
    )
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=False,
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3,
        min_tracking_confidence=0.3,
    )

    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    try:
        result = landmarker.detect(mp.Image.create_from_file(str(args.frame)))
    finally:
        landmarker.close()

    face_count = len(result.face_landmarks)
    if face_count == 0:
        write_mediapipe_failure_report(output_dir, "no_face_detected", {"faceCount": 0})
        return 5

    landmarks = result.face_landmarks[0]
    required_index = max(max(MEDIAPIPE_OUTER_LIP), max(MEDIAPIPE_INNER_LIP))
    if len(landmarks) <= required_index:
        write_mediapipe_failure_report(
            output_dir,
            "landmark_count_too_small",
            {"landmarkCount": len(landmarks), "requiredIndex": required_index},
        )
        return 6

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
    for index, point in zip(MEDIAPIPE_INNER_LIP, inner_points):
        x, y = point
        draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(255, 230, 80, 220))
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

    report = {
        "schemaVersion": "e7-mediapipe-lip-comparison-v0",
        "createdAtUtc": utc_now(),
        "available": True,
        "role": "additional_comparison_signal_not_replacement",
        "api": "mediapipe.tasks.python.vision.FaceLandmarker",
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
        "observationsToReview": [
            "입꼬리가 Apple Vision보다 더 잘 잡히는지",
            "윗입술 산 모양이 더 자연스러운지",
            "가장자리가 face parsing보다 매끈한지",
            "입술 실제 색 경계와 어긋나는 곳이 있는지",
        ],
        "limitations": [
            "MediaPipe landmarks describe face geometry, not makeup color boundary.",
            "This is one clean female sample only.",
            "This result still needs visual review and real camera comparison.",
        ],
    }
    write_json(output_dir / "mediapipe_lip_report.json", report)
    return 0


def run_mediapipe_test(
    args: argparse.Namespace,
    dirs: dict[str, Path],
    frame: Image.Image,
    arface_export: dict[str, Any] | None,
    gold_reference: np.ndarray | None,
) -> tuple[dict[str, Any], tuple[str, Image.Image] | None]:
    output_dir = dirs["mediapipe"]
    if args.skip_mediapipe:
        report = write_mediapipe_failure_report(output_dir, "skipped_by_flag")
        return report, None

    package_available = importlib.util.find_spec("mediapipe") is not None
    if not package_available:
        report = write_mediapipe_failure_report(
            output_dir,
            "mediapipe_package_missing_in_current_python",
            {
                "pythonExecutable": sys.executable,
                "modelPath": str(args.mediapipe_model),
                "modelExists": args.mediapipe_model.exists(),
            },
        )
        return report, None

    if not args.mediapipe_model.exists():
        report = write_mediapipe_failure_report(
            output_dir,
            "face_landmarker_model_missing",
            {
                "pythonExecutable": sys.executable,
                "modelPath": str(args.mediapipe_model),
                "modelExists": False,
            },
        )
        return report, None

    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", str(Path(".cache/matplotlib").resolve()))
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--mediapipe-child",
        "--frame",
        str(args.frame.resolve()),
        "--mediapipe-model",
        str(args.mediapipe_model.resolve()),
        "--mediapipe-output-dir",
        str(output_dir.resolve()),
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=45, env=env, check=False)
    except subprocess.TimeoutExpired as exception:
        report = write_mediapipe_failure_report(
            output_dir,
            "mediapipe_child_timeout",
            {
                "pythonExecutable": sys.executable,
                "modelPath": str(args.mediapipe_model),
                "stdout": (exception.stdout or "")[-8000:],
                "stderr": (exception.stderr or "")[-8000:],
            },
        )
        return report, None

    (output_dir / "mediapipe_process_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
    (output_dir / "mediapipe_process_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")
    report_path = output_dir / "mediapipe_lip_report.json"
    if completed.returncode != 0 or not report_path.exists():
        stderr_tail = (completed.stderr or "")[-12000:]
        report = write_mediapipe_failure_report(
            output_dir,
            "mediapipe_child_failed",
            {
                "pythonExecutable": sys.executable,
                "modelPath": str(args.mediapipe_model),
                "modelExists": args.mediapipe_model.exists(),
                "exitCode": completed.returncode,
                "stdoutTail": (completed.stdout or "")[-8000:],
                "stderrTail": stderr_tail,
                "failureDiagnosis": classify_mediapipe_failure(stderr_tail, completed.returncode),
            },
        )
        return report, None

    report = load_json(report_path)
    if not report.get("available"):
        return report, None

    mask_path = Path(report["outputs"]["mask"])
    overlay_path = Path(report["outputs"]["curveOverlay"])
    mask = load_mask(mask_path, frame.size)
    report["goldComparison"] = comparison_metrics(mask, gold_reference)
    uv_status: dict[str, Any] = {"available": False}
    if arface_export:
        probability = back_project_mask(mask, arface_export, args.uv_resolution, args.uv_sample_stride)
        predicted = render_atlas_to_screen(probability, arface_export, frame.size, 0.5, args.uv_sample_stride)
        round_trip_path = output_dir / "mediapipe_uv_round_trip_overlay.png"
        round_trip_overlay(frame, mask, predicted).save(round_trip_path)
        uv_status = {
            "available": True,
            "roundTrip": comparison_metrics(predicted, mask),
            "roundTripOverlayPath": str(round_trip_path),
            "note": "UV preview only; not real camera evidence.",
        }
    report["uvProjection"] = uv_status
    write_json(report_path, report)
    return report, ("mediapipe_lip_curve", Image.open(overlay_path).copy())


def write_review_docs(
    output_dir: Path,
    dirs: dict[str, Path],
    metrics: dict[str, Any],
    contact_entries: list[tuple[str, Image.Image]],
    mediapipe_report: dict[str, Any] | None = None,
) -> None:
    write_contact_sheet(contact_entries, dirs["review"] / "full_size_contact_sheet.png", 560, 820)
    write_contact_sheet(contact_entries, dirs["review"] / "compact_contact_sheet.png", 260, 380)
    rows = [
        "# E7 입술 후보 생성기 비교표",
        "",
        "| 후보 | 픽셀 수 | gold IoU | Dice | 경계 평균 거리(px) | 왼쪽 입꼬리 | 오른쪽 입꼬리 | 면적 변화 | 거칠기 | UV 미리보기 IoU | 현재 해석 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    interpretation = {
        "parsing_curve_smooth": "face parsing 면적을 매끈하게 정리한 후보",
        "vision_curve_fill": "Vision 점을 곡선으로 이어 만든 후보",
        "vision_color_snap": "Vision 곡선을 색 경계 쪽으로 미세 이동한 후보",
        "hybrid_curve_safe": "번짐을 줄이기 위해 보수적으로 합친 후보",
        "hybrid_curve_balanced": "입꼬리/윗입술 보존을 더 시도한 후보",
    }
    for candidate_id in CANDIDATES:
        item = metrics[candidate_id]
        gold = item["goldComparison"]
        advanced = item.get("advancedEvaluation", {})
        distance = advanced.get("boundaryDistance", {})
        corner = advanced.get("cornerRecall", {})
        contour = advanced.get("contourQuality", {})
        uv = item["uvProjection"].get("roundTrip", {})
        rows.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                candidate_id,
                item["positivePixels"],
                gold.get("iou", "n/a") if gold.get("available") else "n/a",
                gold.get("dice", "n/a") if gold.get("available") else "n/a",
                distance.get("symmetricMeanPx", "n/a") if distance.get("available") else "n/a",
                corner.get("leftCornerRecall", "n/a") if corner.get("available") else "n/a",
                corner.get("rightCornerRecall", "n/a") if corner.get("available") else "n/a",
                advanced.get("areaChangeVsGold", "n/a"),
                contour.get("roughnessIndex", "n/a") if contour.get("available") else "n/a",
                uv.get("iou", "n/a") if uv.get("available") else "n/a",
                interpretation[candidate_id],
            )
        )
    if mediapipe_report is not None:
        rows.extend(["", "## MediaPipe 비교", ""])
        if mediapipe_report.get("available"):
            gold = mediapipe_report.get("goldComparison", {})
            uv = mediapipe_report.get("uvProjection", {}).get("roundTrip", {})
            rows.extend(
                [
                    "| 항목 | 값 |",
                    "| --- | --- |",
                    f"| 상태 | 사용 가능 |",
                    f"| landmark 수 | {mediapipe_report.get('landmarkCount')} |",
                    f"| lip mask 픽셀 수 | {mediapipe_report.get('positivePixels')} |",
                    f"| gold IoU | {gold.get('iou', 'n/a') if gold.get('available') else 'n/a'} |",
                    f"| UV round-trip IoU | {uv.get('iou', 'n/a') if uv.get('available') else 'n/a'} |",
                    f"| overlay | `{mediapipe_report.get('outputs', {}).get('curveOverlay')}` |",
                ]
            )
        else:
            rows.extend(
                [
                    "| 항목 | 값 |",
                    "| --- | --- |",
                    "| 상태 | 실패 또는 사용 불가 |",
                    f"| 이유 | `{mediapipe_report.get('reason')}` |",
                    f"| exitCode | `{mediapipe_report.get('exitCode', 'n/a')}` |",
                    f"| report | `{dirs['mediapipe'] / 'mediapipe_lip_report.json'}` |",
                ]
            )
    (dirs["review"] / "candidate_comparison_table.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    notes = [
        "# E7 입술 후보 리뷰 노트",
        "",
        "각 후보를 full-size overlay와 UV round-trip overlay로 확인한다.",
        "",
    ]
    for candidate_id in CANDIDATES:
        notes.extend(
            [
                f"## {candidate_id}",
                "",
                "- 범위:",
                "- 입꼬리:",
                "- 윗입술:",
                "- 아랫입술:",
                "- 입 안쪽/치아:",
                "- 가장자리:",
                "- 실제 카메라에서 확인할 점:",
                "",
            ]
        )
    notes.extend(
        [
            "## MediaPipe 비교",
            "",
            "- 입꼬리:",
            "- 윗입술 산:",
            "- 가장자리:",
            "- Apple Vision 대비 나은 점:",
            "- face parsing 대비 나은 점:",
            "- 한계:",
            "",
        ]
    )
    (dirs["review"] / "review_notes_template.md").write_text("\n".join(notes), encoding="utf-8")
    checklist = [
        "# 다음 실제 카메라 확인 체크리스트",
        "",
        "- 후보 5개를 같은 조명/같은 표정에서 차례로 확인한다.",
        "- 입꼬리가 비는지, 피부까지 번지는지, 윗입술 산이 무너지는지 후보별로 기록한다.",
        "- `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset` 조정 전/후를 분리해서 본다.",
        "- 실제 카메라에서는 숫자 점수보다 얼굴에 붙어 보이는지, 표정 변화에서 선이 흔들리는지를 우선 본다.",
        "- MediaPipe가 이번 로컬 실행에서 실패했으면, 기기/다른 Python 환경에서 다시 실행 가능할 때만 보조 비교로 다시 본다.",
        "- 이 확인 전에는 M1 ready, runtime ready, E7.3 Green으로 부르지 않는다.",
        "",
        "## 후보별 확인",
        "",
    ]
    for candidate_id in CANDIDATES:
        checklist.extend(
            [
                f"### {candidate_id}",
                "",
                "- 입꼬리:",
                "- 윗입술:",
                "- 아랫입술:",
                "- 피부 번짐:",
                "- 입 안쪽/치아:",
                "- 표정 변화:",
                "",
            ]
        )
    (dirs["review"] / "next_camera_checklist.md").write_text("\n".join(checklist), encoding="utf-8")
    loop_notes = [
        "# 구현 루프 노트",
        "",
        "## 1차 구현",
        "",
        "- 기존 clean female sample, Apple Vision, face parsing, color/gradient, ARFace export를 읽어 core 후보 5개를 생성했다.",
        "- 후보별 hard mask, soft alpha, overlay, curve points, edge band, UV 미리보기를 저장했다.",
        "",
        "## 리뷰",
        "",
        "- compact/full contact sheet에서 5개 후보가 모두 표시되는지 확인한다.",
        "- 후보 간 차이는 주로 면적, 입꼬리 보존, 윗입술/아랫입술 coverage에서 난다.",
        "- UV 미리보기 수치는 낮으므로 제품 품질 판단이 아니라 좌표 확인용으로만 본다.",
        "",
        "## 개선",
        "",
        "- MediaPipe를 core 후보 생성 뒤 별도 child process로 실행하게 했다.",
        "- MediaPipe 실패가 core 5개 생성을 막지 않도록 실패 이유, exit code, stderr를 report와 summary에 남겼다.",
        "- MediaPipe 실패도 contact sheet에서 보이도록 실패 패널을 추가했다.",
        "- 다음 실제 카메라 확인 checklist를 추가했다.",
        "",
        "## 남은 실패",
        "",
    ]
    if mediapipe_report is not None and not mediapipe_report.get("available"):
        diagnosis = mediapipe_report.get("failureDiagnosis", {})
        loop_notes.extend(
            [
                f"- MediaPipe: `{mediapipe_report.get('reason')}`.",
                f"- exitCode: `{mediapipe_report.get('exitCode', 'n/a')}`.",
                f"- 추정 원인: {diagnosis.get('mostLikelyRootCause', 'raw log 확인 필요')}",
                f"- 최소 해소 경로: {diagnosis.get('smallestSafeUnblock', '실패를 문서화하고 core 후보 리뷰 계속')}",
                "- 원문 로그는 `mediapipe/mediapipe_process_stderr.txt`와 `mediapipe/mediapipe_lip_report.json`에 있다.",
            ]
        )
    else:
        loop_notes.append("- MediaPipe: 사용 가능. overlay/mask/report를 리뷰한다.")
    loop_notes.extend(
        [
            "",
            "## 다음 루프 필요 여부",
            "",
            "- core 5개 후보와 필수 리뷰 산출물은 존재한다.",
            "- MediaPipe는 보조 비교 신호이므로 현재 실패가 core 후보 생성 전체를 막지는 않는다.",
            "- 다음 루프는 실제 카메라 후보 선택/사용자 조정 화면으로 연결할 때 필요하다.",
        ]
    )
    (dirs["review"] / "loop_notes.md").write_text("\n".join(loop_notes), encoding="utf-8")


def review_priority_score(item: dict[str, Any]) -> float:
    gold = item.get("goldComparison", {})
    advanced = item.get("advancedEvaluation", {})
    distance = advanced.get("boundaryDistance", {})
    corner = advanced.get("cornerRecall", {})
    area_change = advanced.get("areaChangeVsGold")
    contour = advanced.get("contourQuality", {})
    iou = float(gold.get("iou", 0.0)) if gold.get("available") else 0.0
    mean_distance = float(distance.get("symmetricMeanPx", 20.0)) if distance.get("available") else 20.0
    left_corner = corner.get("leftCornerRecall")
    right_corner = corner.get("rightCornerRecall")
    corner_min = min(
        float(left_corner) if isinstance(left_corner, (int, float)) else 0.0,
        float(right_corner) if isinstance(right_corner, (int, float)) else 0.0,
    )
    area_penalty = abs(float(area_change)) if isinstance(area_change, (int, float)) else 0.2
    roughness = contour.get("roughnessIndex")
    roughness_penalty = max(0.0, float(roughness) - 1.4) if isinstance(roughness, (int, float)) else 0.2
    return round(iou + (corner_min * 0.04) - (mean_distance * 0.01) - (area_penalty * 0.12) - (roughness_penalty * 0.03), 6)


def sorted_candidate_ids_by_priority(metrics: dict[str, Any]) -> list[str]:
    return sorted(CANDIDATES, key=lambda candidate_id: review_priority_score(metrics[candidate_id]), reverse=True)


def meta_from_template(template_path: Path) -> str:
    guid = uuid.uuid4().hex
    if template_path.exists():
        lines = template_path.read_text(encoding="utf-8").splitlines()
        return "\n".join([f"guid: {guid}" if line.startswith("guid: ") else line for line in lines]) + "\n"
    return f"fileFormatVersion: 2\nguid: {guid}\n"


def install_unity_assets(
    dirs: dict[str, Path],
    metrics: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    install_report: dict[str, Any] = {
        "installed": False,
        "resourceDir": str(args.unity_resource_dir),
        "assets": {},
    }
    if not args.install_unity_assets:
        install_report["reason"] = "install_unity_assets_flag_not_set"
        write_json(dirs["review"] / "unity_asset_install_report.json", install_report)
        return install_report

    args.unity_resource_dir.mkdir(parents=True, exist_ok=True)
    template_meta = args.unity_resource_dir / "e7-lip-validation-tight-auto-v0.png.meta"
    for candidate_id in CANDIDATES:
        runtime = CANDIDATE_RUNTIME[candidate_id]
        source = dirs["debug"] / f"{candidate_id}_uv_probability.png"
        target = args.unity_resource_dir / f"{runtime['unityMaskTextureId']}.png"
        if not source.exists():
            install_report["assets"][candidate_id] = {
                "installed": False,
                "reason": "uv_probability_missing",
                "source": str(source),
            }
            continue
        source_image = Image.open(source).convert("L")
        if source_image.size != (512, 512):
            source_image = source_image.resize((512, 512), Image.Resampling.BILINEAR)
        arr = np.asarray(source_image, dtype=np.uint8)
        rgba = np.dstack([arr, arr, arr, np.full_like(arr, 255)])
        Image.fromarray(rgba, mode="RGBA").save(target)
        meta_path = Path(str(target) + ".meta")
        if not meta_path.exists():
            meta_path.write_text(meta_from_template(template_meta), encoding="utf-8")
        install_report["assets"][candidate_id] = {
            "installed": True,
            "candidateId": runtime["candidateId"],
            "unityMaskTextureId": runtime["unityMaskTextureId"],
            "source": str(source),
            "target": str(target),
            "targetMeta": str(meta_path),
            "targetSha256": sha256_file(target),
            "metricsPath": metrics[candidate_id].get("evaluationPath"),
        }
    install_report["installed"] = any(item.get("installed") for item in install_report["assets"].values())
    write_json(dirs["review"] / "unity_asset_install_report.json", install_report)
    return install_report


def write_runtime_registry(
    output_dir: Path,
    metrics: dict[str, Any],
    unity_install: dict[str, Any],
) -> dict[str, Any]:
    registry = {
        "schemaVersion": "e7-lip-cv-runtime-candidate-registry-v1",
        "createdAtUtc": utc_now(),
        "runtimeReady": False,
        "candidateIds": [CANDIDATE_RUNTIME[candidate_id]["candidateId"] for candidate_id in CANDIDATES],
        "userAdjustmentFields": list(ADJUSTMENT_FIELDS),
        "unityAssetsInstalled": bool(unity_install.get("installed")),
        "candidates": [],
    }
    for candidate_id in CANDIDATES:
        runtime = CANDIDATE_RUNTIME[candidate_id]
        item = metrics[candidate_id]
        install_item = unity_install.get("assets", {}).get(candidate_id, {})
        registry["candidates"].append(
            {
                "sourceCandidateId": candidate_id,
                "candidateId": runtime["candidateId"],
                "label": runtime["label"],
                "status": runtime["status"],
                "unityMaskTextureId": runtime["unityMaskTextureId"],
                "threshold": runtime["threshold"],
                "coverage": runtime["coverage"],
                "feather": runtime["feather"],
                "screenMask": item["maskPath"],
                "overlay": item["overlayPath"],
                "evaluation": item["evaluationPath"],
                "unityAssetPath": install_item.get("target"),
                "runtimeReady": False,
                "runtimeReadyReason": "installed_for_validation_selection_not_user_confirmed",
            }
        )
    write_json(output_dir / "candidate_registry_cv_runtime.json", registry)
    return registry


def write_korean_report(
    output_dir: Path,
    dirs: dict[str, Path],
    metrics: dict[str, Any],
    unity_install: dict[str, Any],
    mediapipe_report: dict[str, Any] | None,
) -> Path:
    ranked = sorted_candidate_ids_by_priority(metrics)
    best = ranked[0] if ranked else CANDIDATES[0]
    lines = [
        "# E7 입술 경계 후보 생성 실험 보고서",
        "",
        f"- 실행 폴더: `{output_dir}`",
        "- 목적: 기존 신호를 조합해 실제 AR 화면에서 비교할 입술 경계 후보 5개를 만든다.",
        "- 판단 범위: 현재 clean female sample 기준의 buildless 결과다. 실제 카메라 최종 판정은 아니다.",
        "",
        "## 입력 신호",
        "",
        "| 신호 | 이번 실험에서의 역할 | 한계 |",
        "| --- | --- | --- |",
        "| gold 기준 마스크 | 비교 기준과 누락/넘침 확인 | 사람이 그린 기준이라 같은 사진에는 강하지만 일반화 근거는 약함 |",
        "| face parsing | 입술 면적과 피부/입 안쪽 제외 힌트 | 가장자리가 거칠고 입꼬리를 짧게 잡을 수 있음 |",
        "| Apple Vision | 입술 형태와 좌표 안정성 힌트 | 점이 적으면 실제 곡선을 덜 따라갈 수 있음 |",
        "| color/gradient | Vision 선을 실제 색 경계 쪽으로 조금 옮기는 보정 | 조명, 그림자, 기존 립 컬러에 영향을 받음 |",
        "| ARFace UV | 실제 카메라에서 얼굴 mesh에 붙일 좌표계 | 색 경계 자체를 알려주지는 않음 |",
        "| OpenCV/scikit-image | 경계 정리, 부드럽게 만들기, 거리/거칠기 평가 | 새 입술 인식 모델은 아니며 입력 신호가 틀리면 함께 틀릴 수 있음 |",
        "",
        "## 후보 요약",
        "",
        "| 후보 | 설명 | gold IoU | Dice | 경계 평균 거리(px) | 입꼬리 최소 recall | 면적 변화 | 리뷰 우선값 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    description = {
        "parsing_curve_smooth": "face parsing 결과를 매끈한 곡선 mask로 다시 그린 후보",
        "vision_curve_fill": "Apple Vision 입술 점을 곡선으로 이어 채운 후보",
        "vision_color_snap": "Vision 곡선을 사진의 색/밝기 경계 쪽으로 조금 이동한 후보",
        "hybrid_curve_safe": "parsing, Vision, 색 경계를 합치되 번짐을 줄인 후보",
        "hybrid_curve_balanced": "safe보다 입꼬리와 얇은 윗입술 보존을 더 시도한 후보",
    }
    for candidate_id in CANDIDATES:
        item = metrics[candidate_id]
        gold = item["goldComparison"]
        advanced = item["advancedEvaluation"]
        distance = advanced["boundaryDistance"]
        corner = advanced["cornerRecall"]
        corner_values = [
            value for value in (corner.get("leftCornerRecall"), corner.get("rightCornerRecall")) if isinstance(value, (int, float))
        ]
        corner_min = min(corner_values) if corner_values else "n/a"
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} | {} | {} |".format(
                candidate_id,
                description[candidate_id],
                gold.get("iou", "n/a") if gold.get("available") else "n/a",
                gold.get("dice", "n/a") if gold.get("available") else "n/a",
                distance.get("symmetricMeanPx", "n/a") if distance.get("available") else "n/a",
                corner_min,
                advanced.get("areaChangeVsGold", "n/a"),
                review_priority_score(item),
            )
        )
    lines.extend(
        [
            "",
            "## 후보별 이미지",
            "",
            "아래 이미지는 작게 삽입했다. 원본 비교는 각 이미지 경로를 직접 열어 확인하면 된다.",
            "",
        ]
    )
    for candidate_id in CANDIDATES:
        item = metrics[candidate_id]
        lines.extend(
            [
                f"### {candidate_id}",
                "",
                f"- 최종 overlay: `{item['overlayPath']}`",
                f"- 기준 대비 차이 overlay: `{item['failureOverlayPath']}`",
                f"- 중간/디버그: `{dirs['debug'] / (candidate_id + '_curve_overlay.png')}` / `{dirs['debug'] / (candidate_id + '_edge_band.png')}`",
                "",
                f'<img src="../candidates/{candidate_id}_overlay.png" width="320" />',
                "",
                f'<img src="../evaluation/{candidate_id}_gold_difference_overlay.png" width="320" />',
                "",
            ]
        )
    lines.extend(
        [
            "## 현재 추천",
            "",
            f"- buildless 리뷰 우선 후보: `{best}`",
            "- 이 추천은 자동 확정이 아니라 실제 카메라에서 먼저 볼 후보 순서다.",
            "- 이유: gold와의 겹침, 경계 거리, 입꼬리 누락, 면적 증가를 함께 본 보조값이 가장 높다.",
            "",
            "## 앱 연결 상태",
            "",
        ]
    )
    if unity_install.get("installed"):
        lines.append("- 새 후보 UV texture를 Unity Resources에 설치했다. RN 후보 버튼과 Unity mask id를 연결하면 실제 카메라 화면에서 전환 가능하다.")
    else:
        lines.append("- 이번 실행에서는 Unity Resources 설치 플래그가 꺼져 있었다. `--install-unity-assets`로 다시 실행하면 후보 texture를 설치한다.")
    lines.extend(
        [
            f"- Unity 설치 리포트: `{dirs['review'] / 'unity_asset_install_report.json'}`",
            f"- 런타임 후보 registry: `{output_dir / 'candidate_registry_cv_runtime.json'}`",
            "",
            "## MediaPipe",
            "",
        ]
    )
    if mediapipe_report is not None and mediapipe_report.get("available"):
        lines.append("- MediaPipe 비교 신호도 생성됐다. 단, 이번 5개 core 후보를 대체하는 신호로 보지 않는다.")
    else:
        reason = mediapipe_report.get("reason") if mediapipe_report else "not_run"
        lines.append(f"- MediaPipe는 이번 로컬 실행에서 사용 불가로 기록했다: `{reason}`.")
    lines.extend(
        [
            "",
            "## 실제 카메라에서 볼 점",
            "",
            "- 피부 쪽으로 번지는지",
            "- 입꼬리가 비는지",
            "- 윗입술 산과 얇은 윗입술이 무너지는지",
            "- 입을 조금 열거나 표정을 바꿀 때 경계가 얼굴에 붙어 보이는지",
            "- 사용자 조정값으로 충분히 보정 가능한지",
            "",
            "## 남은 위험",
            "",
            "- clean female sample 하나에서 만든 결과다.",
            "- gold 기준 점수는 실제 AR 적용감을 대신하지 않는다.",
            "- ARFace UV 미리보기는 실제 카메라 runtime 증거가 아니다.",
            "- 후보 선택 UI는 검증용이며 최종 사용자 흐름은 별도 정리가 필요하다.",
        ]
    )
    path = dirs["report"] / "E7_LIP_CANDIDATE_GENERATOR_REPORT_KO.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main() -> int:
    args = parse_args()
    if args.mediapipe_child:
        return run_mediapipe_child(args)

    run_id = args.run_id or f"experiment-{utc_stamp()}"
    output_dir = args.output_root / run_id
    dirs = ensure_dirs(output_dir)

    frame = Image.open(args.frame).convert("RGB")
    size = frame.size
    vision = load_json(args.vision) if args.vision.exists() else None
    arface_export = load_json(args.arface_export) if args.arface_export.exists() else None
    color_confidence = load_json(args.color_confidence) if args.color_confidence.exists() else None

    parsing_lip = load_mask(args.face_parsing_dir / "face_parsing_lip_mask.png", size)
    upper = load_mask(args.face_parsing_dir / "face_parsing_upper_lip_mask.png", size) if (args.face_parsing_dir / "face_parsing_upper_lip_mask.png").exists() else None
    lower = load_mask(args.face_parsing_dir / "face_parsing_lower_lip_mask.png", size) if (args.face_parsing_dir / "face_parsing_lower_lip_mask.png").exists() else None
    inner = load_mask(args.face_parsing_dir / "face_parsing_inner_mouth_mask.png", size) if (args.face_parsing_dir / "face_parsing_inner_mouth_mask.png").exists() else None
    skin = load_mask(args.face_parsing_dir / "face_parsing_skin_mask.png", size) if (args.face_parsing_dir / "face_parsing_skin_mask.png").exists() else None

    candidates, warnings, color_band = build_candidates(frame, vision, parsing_lip, upper, lower, inner, skin, args.curve_samples)
    write_input_overlays(dirs, frame, vision, parsing_lip, upper, lower, skin, color_band, arface_export)
    gold_reference = load_gold_reference(size)
    metrics, contact_entries = write_candidate_artifacts(dirs, frame, candidates, arface_export, gold_reference, upper, lower, args)
    mediapipe_report, mediapipe_contact_entry = run_mediapipe_test(args, dirs, frame, arface_export, gold_reference)
    if mediapipe_contact_entry is not None:
        contact_entries.append(mediapipe_contact_entry)
    elif mediapipe_report is not None:
        contact_entries.append(
            (
                "mediapipe_failed",
                make_text_panel(
                    frame.size,
                    "MediaPipe failed",
                    [
                        f"reason: {mediapipe_report.get('reason', 'unknown')}",
                        f"exitCode: {mediapipe_report.get('exitCode', 'n/a')}",
                        "model exists: " + str(mediapipe_report.get("modelExists", "n/a")),
                        "details: mediapipe/mediapipe_lip_report.json",
                    ],
                ),
            )
        )
    write_review_docs(output_dir, dirs, metrics, contact_entries, mediapipe_report)
    unity_install = install_unity_assets(dirs, metrics, args)
    runtime_registry = write_runtime_registry(output_dir, metrics, unity_install)
    report_path = write_korean_report(output_dir, dirs, metrics, unity_install, mediapipe_report)

    input_report = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAtUtc": utc_now(),
        "runId": run_id,
        "inputs": {
            "frame": {"path": str(args.frame), "exists": args.frame.exists(), "sha256": sha256_file(args.frame)},
            "arfaceExport": {
                "path": str(args.arface_export),
                "exists": args.arface_export.exists(),
                "sha256": sha256_file(args.arface_export) if args.arface_export.exists() else None,
                "blendShapesAvailable": bool((arface_export or {}).get("blendShapes", {}).get("available", False)),
            },
            "appleVision": {
                "path": str(args.vision),
                "exists": args.vision.exists(),
                "outerPointCount": len(contour_from_vision(vision or {}, "outerLips")),
                "innerPointCount": len(contour_from_vision(vision or {}, "innerLips")),
            },
            "faceParsing": {
                "dir": str(args.face_parsing_dir),
                "lipPixels": int(np.count_nonzero(parsing_lip)),
                "upperPixels": int(np.count_nonzero(upper)) if upper is not None else None,
                "lowerPixels": int(np.count_nonzero(lower)) if lower is not None else None,
                "innerPixels": int(np.count_nonzero(inner)) if inner is not None else None,
            },
            "colorGradient": {
                "path": str(args.color_confidence),
                "exists": args.color_confidence.exists(),
                "status": (color_confidence or {}).get("status"),
                "lowContrastWarning": (color_confidence or {}).get("lowContrastWarning"),
            },
            "availablePackages": package_status(),
            "mediapipe": {
                "modelPath": str(args.mediapipe_model),
                "modelExists": args.mediapipe_model.exists(),
                "reportPath": str(dirs["mediapipe"] / "mediapipe_lip_report.json"),
                "available": bool(mediapipe_report.get("available")),
                "reason": mediapipe_report.get("reason"),
            },
        },
        "warnings": warnings,
        "privacy": {
            "localOnly": True,
            "uploadAllowed": False,
            "rawFrameStoredByThisTool": False,
            "deviceBuildRun": False,
            "liveRuntimeInference": False,
        },
    }
    write_json(dirs["inputs"] / "input_signal_report.json", input_report)

    registry = {
        "schemaVersion": "e7-lip-candidate-registry-draft-v0",
        "createdAtUtc": utc_now(),
        "runId": run_id,
        "runtimeReady": False,
        "candidateIds": list(CANDIDATES),
        "userAdjustmentFields": list(ADJUSTMENT_FIELDS),
        "candidates": {
            candidate_id: {
                "candidateId": candidate_id,
                "maskPath": metrics[candidate_id]["maskPath"],
                "alphaPath": metrics[candidate_id]["alphaPath"],
                "overlayPath": metrics[candidate_id]["overlayPath"],
                "runtimeReady": False,
                "source": candidates[candidate_id].trace.get("sourceSignals", []),
            }
            for candidate_id in CANDIDATES
        },
        "comparisonSignals": {
            "mediapipe": {
                "available": bool(mediapipe_report.get("available")),
                "reportPath": str(dirs["mediapipe"] / "mediapipe_lip_report.json"),
                "overlayPath": mediapipe_report.get("outputs", {}).get("curveOverlay"),
                "note": "additional comparison signal; not a replacement candidate",
            }
        },
    }
    write_json(output_dir / "candidate_registry_draft.json", registry)

    summary = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAtUtc": utc_now(),
        "runId": run_id,
        "decision": "generated_for_review_not_runtime_ready",
        "outputDir": str(output_dir),
        "candidateCount": len(CANDIDATES),
        "candidates": metrics,
        "reviewPriority": [
            {
                "candidateId": candidate_id,
                "score": review_priority_score(metrics[candidate_id]),
            }
            for candidate_id in sorted_candidate_ids_by_priority(metrics)
        ],
        "mediapipeComparison": mediapipe_report,
        "unityInstall": unity_install,
        "runtimeRegistry": runtime_registry,
        "reviewArtifacts": {
            "fullSizeContactSheet": str(dirs["review"] / "full_size_contact_sheet.png"),
            "compactContactSheet": str(dirs["review"] / "compact_contact_sheet.png"),
            "comparisonTable": str(dirs["review"] / "candidate_comparison_table.md"),
            "reviewNotesTemplate": str(dirs["review"] / "review_notes_template.md"),
            "nextCameraChecklist": str(dirs["review"] / "next_camera_checklist.md"),
            "loopNotes": str(dirs["review"] / "loop_notes.md"),
            "koreanReport": str(report_path),
            "unityInstallReport": str(dirs["review"] / "unity_asset_install_report.json"),
        },
        "knownLimits": [
            "single clean neutral frame only",
            "blendshape values are only consumed if already present in arface_export",
            "inner mouth is empty in the current closed-mouth face parsing signal",
            "MediaPipe is only an additional comparison signal and may fail on this headless macOS session",
            "not a runtime or E7.3 Green decision",
        ],
    }
    write_json(output_dir / "candidate_generation_summary.json", summary)
    lines = [
        "# E7 입술 후보 생성기 결과",
        "",
        f"- Run: `{run_id}`",
        f"- Output: `{output_dir}`",
        "- Decision: `generated_for_review_not_runtime_ready`",
        "",
        "## 후보",
        "",
    ]
    for candidate_id in CANDIDATES:
        item = metrics[candidate_id]
        gold = item["goldComparison"]
        uv = item["uvProjection"].get("roundTrip", {})
        lines.append(
            "- `{}`: pixels `{}`, goldIoU `{}`, boundaryMeanPx `{}`, reviewPriority `{}`, uvPreviewIoU `{}`".format(
                candidate_id,
                item["positivePixels"],
                gold.get("iou", "n/a") if gold.get("available") else "n/a",
                item["advancedEvaluation"]["boundaryDistance"].get("symmetricMeanPx", "n/a")
                if item["advancedEvaluation"]["boundaryDistance"].get("available")
                else "n/a",
                review_priority_score(item),
                uv.get("iou", "n/a") if uv.get("available") else "n/a",
            )
        )
    lines.extend(["", "## MediaPipe 비교", ""])
    if mediapipe_report.get("available"):
        lines.extend(
            [
                "- 상태: 사용 가능",
                f"- landmark 수: `{mediapipe_report.get('landmarkCount')}`",
                f"- overlay: `{mediapipe_report.get('outputs', {}).get('curveOverlay')}`",
                f"- report: `{dirs['mediapipe'] / 'mediapipe_lip_report.json'}`",
            ]
        )
    else:
        diagnosis = mediapipe_report.get("failureDiagnosis", {})
        lines.extend(
            [
                "- 상태: 실패 또는 사용 불가",
                f"- 이유: `{mediapipe_report.get('reason')}`",
                f"- exitCode: `{mediapipe_report.get('exitCode', 'n/a')}`",
                f"- 추정 원인: {diagnosis.get('mostLikelyRootCause', 'raw log 확인 필요')}",
                f"- 최소 해소 경로: {diagnosis.get('smallestSafeUnblock', '실패를 문서화하고 core 후보 리뷰 계속')}",
                f"- report: `{dirs['mediapipe'] / 'mediapipe_lip_report.json'}`",
            ]
        )
    lines.extend(
        [
            "",
            "## 리뷰 파일",
            "",
            f"- Full-size contact sheet: `{dirs['review'] / 'full_size_contact_sheet.png'}`",
            f"- Compact contact sheet: `{dirs['review'] / 'compact_contact_sheet.png'}`",
            f"- Comparison table: `{dirs['review'] / 'candidate_comparison_table.md'}`",
            f"- Next camera checklist: `{dirs['review'] / 'next_camera_checklist.md'}`",
            f"- Loop notes: `{dirs['review'] / 'loop_notes.md'}`",
            f"- Candidate registry draft: `{output_dir / 'candidate_registry_draft.json'}`",
            f"- CV runtime registry: `{output_dir / 'candidate_registry_cv_runtime.json'}`",
            f"- Korean report: `{report_path}`",
            f"- Unity asset install report: `{dirs['review'] / 'unity_asset_install_report.json'}`",
            "",
            "## 제한",
            "",
            "- 기존 local evidence만 사용했다.",
            "- 새 capture, iPhone build, 실제 카메라 runtime evidence는 없다.",
            "- 이 결과는 후보 리뷰용이며 M1 ready / runtime ready / E7.3 Green 증거가 아니다.",
        ]
    )
    (output_dir / "candidate_generation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
