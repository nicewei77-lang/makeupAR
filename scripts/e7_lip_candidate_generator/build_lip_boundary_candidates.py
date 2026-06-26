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
import importlib.util
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
CANDIDATES = (
    "parsing_curve_smooth",
    "vision_curve_fill",
    "vision_color_snap",
    "hybrid_curve_safe",
    "hybrid_curve_balanced",
)
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
    parser.add_argument("--uv-resolution", type=int, default=256)
    parser.add_argument("--uv-sample-stride", type=int, default=5)
    parser.add_argument("--curve-samples", type=int, default=180)
    parser.add_argument("--mediapipe-model", type=Path, default=DEFAULT_MEDIAPIPE_MODEL)
    parser.add_argument("--skip-mediapipe", action="store_true")
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
        "review": output_dir / "review",
        "mediapipe": output_dir / "mediapipe",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def package_status() -> dict[str, Any]:
    packages = {
        "cv2": "opencv",
        "scipy": "scipy",
        "skimage": "scikit-image",
        "mediapipe": "mediapipe",
        "numpy": "numpy",
        "PIL": "pillow",
    }
    return {
        label: {
            "importName": name,
            "available": importlib.util.find_spec(name) is not None,
        }
        for name, label in packages.items()
    }


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
    luma = (rgb[:, :, 0] * 0.299) + (rgb[:, :, 1] * 0.587) + (rgb[:, :, 2] * 0.114)
    grad_y, grad_x = np.gradient(luma)
    gradient = np.sqrt((grad_x * grad_x) + (grad_y * grad_y))
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
    vision_mask = subtract_optional(vision_mask, inner)
    candidates["vision_curve_fill"] = Candidate(
        "vision_curve_fill",
        vision_mask,
        make_soft_alpha(vision_mask),
        vision_curve,
        {
            "sourceSignals": ["apple_vision_outer_lips", "apple_vision_inner_lips"],
            "steps": ["read Vision points", "smooth closed curve", "fill outer curve", "subtract inner curve when usable"],
            "outerPointCount": len(outer),
            "innerPointCount": len(inner_points),
            "outputPixels": int(np.count_nonzero(vision_mask)),
        },
    )

    snapped_curve, snap_report, color_band = snap_curve_to_color_edge(vision_curve, frame, max_offset=8)
    snap_mask = keep_largest_component(close_mask(fill_polygon(snapped_curve, size, [inner_curve] if inner_curve else None), 1))
    snap_mask = subtract_optional(snap_mask, inner)
    candidates["vision_color_snap"] = Candidate(
        "vision_color_snap",
        snap_mask,
        make_soft_alpha(snap_mask),
        snapped_curve,
        {
            "sourceSignals": ["apple_vision_outer_lips", "frame_luma_gradient", "limited_color_edge_band"],
            "steps": ["start from Vision curve", "scan local normal band", "move points to strong gradient", "fill curve"],
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
        "precision": round(tp / (tp + fp), 6) if (tp + fp) else 0.0,
        "recall": round(tp / (tp + fn), 6) if (tp + fn) else 0.0,
        "outsideReference": round(fp / cand, 6) if cand else 0.0,
        "missReference": round(fn / ref, 6) if ref else 0.0,
    }


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


def write_candidate_artifacts(
    dirs: dict[str, Path],
    frame: Image.Image,
    candidates: dict[str, Candidate],
    arface_export: dict[str, Any] | None,
    gold_reference: np.ndarray | None,
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

        candidate_metrics = {
            "maskPath": str(mask_path),
            "alphaPath": str(alpha_path),
            "overlayPath": str(overlay_path),
            "positivePixels": int(np.count_nonzero(candidate.mask)),
            "bbox": bbox(candidate.mask),
            "goldComparison": comparison_metrics(candidate.mask, gold_reference),
            "uvProjection": uv_status,
            "tracePath": str(dirs["debug"] / f"{candidate_id}_generation_trace.json"),
        }
        metrics_by_candidate[candidate_id] = candidate_metrics
        contact_entries.append((candidate_id, Image.open(overlay_path).copy()))
    return metrics_by_candidate, contact_entries


def write_review_docs(output_dir: Path, dirs: dict[str, Path], metrics: dict[str, Any], contact_entries: list[tuple[str, Image.Image]]) -> None:
    write_contact_sheet(contact_entries, dirs["review"] / "full_size_contact_sheet.png", 560, 820)
    write_contact_sheet(contact_entries, dirs["review"] / "compact_contact_sheet.png", 260, 380)
    rows = [
        "# E7 입술 후보 생성기 비교표",
        "",
        "| 후보 | 픽셀 수 | gold IoU | gold precision | gold recall | UV round-trip IoU | 현재 해석 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
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
        uv = item["uvProjection"].get("roundTrip", {})
        rows.append(
            "| `{}` | {} | {} | {} | {} | {} | {} |".format(
                candidate_id,
                item["positivePixels"],
                gold.get("iou", "n/a") if gold.get("available") else "n/a",
                gold.get("precision", "n/a") if gold.get("available") else "n/a",
                gold.get("recall", "n/a") if gold.get("available") else "n/a",
                uv.get("iou", "n/a") if uv.get("available") else "n/a",
                interpretation[candidate_id],
            )
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
    (dirs["review"] / "review_notes_template.md").write_text("\n".join(notes), encoding="utf-8")


def main() -> int:
    args = parse_args()
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
    metrics, contact_entries = write_candidate_artifacts(dirs, frame, candidates, arface_export, gold_reference, args)
    write_review_docs(output_dir, dirs, metrics, contact_entries)

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
        "reviewArtifacts": {
            "fullSizeContactSheet": str(dirs["review"] / "full_size_contact_sheet.png"),
            "compactContactSheet": str(dirs["review"] / "compact_contact_sheet.png"),
            "comparisonTable": str(dirs["review"] / "candidate_comparison_table.md"),
            "reviewNotesTemplate": str(dirs["review"] / "review_notes_template.md"),
        },
        "knownLimits": [
            "single clean neutral frame only",
            "blendshape values are only consumed if already present in arface_export",
            "inner mouth is empty in the current closed-mouth face parsing signal",
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
            "- `{}`: pixels `{}`, goldIoU `{}`, uvRoundTripIoU `{}`".format(
                candidate_id,
                item["positivePixels"],
                gold.get("iou", "n/a") if gold.get("available") else "n/a",
                uv.get("iou", "n/a") if uv.get("available") else "n/a",
            )
        )
    lines.extend(
        [
            "",
            "## 리뷰 파일",
            "",
            f"- Full-size contact sheet: `{dirs['review'] / 'full_size_contact_sheet.png'}`",
            f"- Compact contact sheet: `{dirs['review'] / 'compact_contact_sheet.png'}`",
            f"- Comparison table: `{dirs['review'] / 'candidate_comparison_table.md'}`",
            f"- Candidate registry draft: `{output_dir / 'candidate_registry_draft.json'}`",
            "",
            "## 제한",
            "",
            "- 기존 local evidence만 사용했다.",
            "- 새 capture, iPhone build, runtime evidence는 없다.",
            "- 이 결과는 후보 리뷰용이며 M1 ready / runtime ready / E7.3 Green 증거가 아니다.",
        ]
    )
    (output_dir / "candidate_generation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
