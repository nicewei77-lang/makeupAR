#!/usr/bin/env python3
"""Build local E7 full-face region candidates for lip/blush/brow/eyeliner.

This is a buildless, local-only experiment tool. It reads the existing curated
clean frame + ARFace export and writes traceable region packages, maps, UV
projections, contact sheets, and scorecards. It does not upload, capture, build
for iPhone, or run live runtime inference.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


DEFAULT_SESSION_ROOT = Path("evidence/e7-region-generate/session-20260626T195853Z")
DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_ARFACE_EXPORT = Path(
    "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/arface_export.json"
)
DEFAULT_LIP_GOLD = Path(
    "evidence/references/e7-user-gold-raw-20260626/user-gold-lip-mask-gray-20260625-163204.png"
)

REGIONS = ("lip", "blush", "brow", "eyeliner")
UV_RESOLUTION = 512


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    policy: str
    mask: np.ndarray
    soft_alpha: np.ndarray
    adjustment: dict[str, float]
    sources: list[str]
    warnings: list[str]
    trace: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build E7 full-face region candidates.")
    parser.add_argument("--session-root", type=Path, default=DEFAULT_SESSION_ROOT)
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--arface-export", type=Path, default=DEFAULT_ARFACE_EXPORT)
    parser.add_argument("--lip-gold", type=Path, default=DEFAULT_LIP_GOLD)
    parser.add_argument("--uv-resolution", type=int, default=UV_RESOLUTION)
    parser.add_argument("--uv-sample-stride", type=int, default=6)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def mask_to_image(mask: np.ndarray) -> Image.Image:
    return Image.fromarray(np.where(mask, 255, 0).astype(np.uint8), mode="L")


def alpha_to_image(alpha: np.ndarray) -> Image.Image:
    return Image.fromarray(np.rint(np.clip(alpha, 0, 1) * 255).astype(np.uint8), mode="L")


def soft_alpha(mask: np.ndarray, feather_px: float) -> np.ndarray:
    base = mask_to_image(mask).filter(ImageFilter.GaussianBlur(radius=feather_px))
    return np.asarray(base, dtype=np.float32) / 255.0


def polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> np.ndarray:
    img = Image.new("L", size, 0)
    ImageDraw.Draw(img).polygon(points, fill=255)
    return np.asarray(img) > 0


def ellipse_mask(
    size: tuple[int, int],
    center: tuple[float, float],
    radius: tuple[float, float],
    angle_deg: float = 0,
) -> np.ndarray:
    w, h = size
    yy, xx = np.indices((h, w), dtype=np.float32)
    cx, cy = center
    rx, ry = radius
    theta = math.radians(angle_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    x = xx - cx
    y = yy - cy
    xr = x * cos_t + y * sin_t
    yr = -x * sin_t + y * cos_t
    return (xr / max(rx, 1)) ** 2 + (yr / max(ry, 1)) ** 2 <= 1.0


def stroke_polyline_mask(
    size: tuple[int, int],
    points: list[tuple[float, float]],
    width: int,
    tail: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> np.ndarray:
    img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(img)
    if len(points) >= 2:
        draw.line(points, fill=255, width=max(1, int(width)), joint="curve")
    if tail is not None:
        draw.line([tail[0], tail[1]], fill=255, width=max(1, int(width)), joint="curve")
    return np.asarray(img) > 0


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    img = mask_to_image(mask).filter(ImageFilter.MaxFilter(size=radius * 2 + 1))
    return np.asarray(img) > 0


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    img = mask_to_image(mask).filter(ImageFilter.MinFilter(size=radius * 2 + 1))
    return np.asarray(img) > 0


def resize_mask_to(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    img = mask_to_image(mask).resize(size, Image.Resampling.NEAREST)
    return np.asarray(img) > 0


def load_lip_reference(path: Path, size: tuple[int, int]) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Missing lip gold reference: {path}")
    img = Image.open(path).convert("RGB")
    if img.size != size:
        img = img.resize(size, Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    luminance = arr.mean(axis=2)
    # The accepted lip mask is a gray-on-white image with opaque full-frame alpha.
    return luminance < 250.0


def face_anchor(export: dict[str, Any], size: tuple[int, int]) -> dict[str, float]:
    screen = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    w, h = size
    if screen.ndim == 2 and screen.shape[1] >= 2 and len(screen):
        xs = screen[:, 0]
        ys = screen[:, 1]
        valid = (xs >= 0) & (xs <= w) & (ys >= 0) & (ys <= h)
        if np.count_nonzero(valid) > 100:
            xs = xs[valid]
            ys = ys[valid]
        return {
            "cx": float(np.median(xs)),
            "cy": float(np.median(ys)),
            "minX": float(np.percentile(xs, 5)),
            "maxX": float(np.percentile(xs, 95)),
            "minY": float(np.percentile(ys, 5)),
            "maxY": float(np.percentile(ys, 95)),
            "width": float(np.percentile(xs, 95) - np.percentile(xs, 5)),
            "height": float(np.percentile(ys, 95) - np.percentile(ys, 5)),
        }
    return {
        "cx": w * 0.5,
        "cy": h * 0.48,
        "minX": w * 0.23,
        "maxX": w * 0.77,
        "minY": h * 0.18,
        "maxY": h * 0.82,
        "width": w * 0.54,
        "height": h * 0.64,
    }


def build_lip_candidates(size: tuple[int, int], lip_reference: np.ndarray) -> list[CandidateSpec]:
    tight = erode(lip_reference, 2)
    balanced = lip_reference
    safe = dilate(lip_reference, 3)
    return [
        CandidateSpec(
            "lip-tight-gold-v0",
            "tight",
            tight,
            soft_alpha(tight, 4.0),
            {
                "cornerReach": -0.05,
                "upperLipTightness": 0.08,
                "lowerLipTightness": 0.08,
                "verticalOffset": 0.0,
                "innerMouthGuard": 0.15,
                "edgeFeather": 0.06,
                "coverage": 0.92,
            },
            ["userAdjustment", "hybrid", "arfaceUv"],
            ["accepted lip gold is offline reference only; no iPhone runtime proof"],
            {"source": "user_gold_lip_mask_gray", "morphology": "erode_2px"},
        ),
        CandidateSpec(
            "lip-balanced-gold-v0",
            "balanced",
            balanced,
            soft_alpha(balanced, 5.0),
            {
                "cornerReach": 0.0,
                "upperLipTightness": 0.0,
                "lowerLipTightness": 0.0,
                "verticalOffset": 0.0,
                "innerMouthGuard": 0.12,
                "edgeFeather": 0.07,
                "coverage": 1.0,
            },
            ["userAdjustment", "hybrid", "arfaceUv"],
            ["selected from accepted offline lip gold; still pre-Xcode only"],
            {"source": "user_gold_lip_mask_gray", "morphology": "exact_threshold_luminance_lt_250"},
        ),
        CandidateSpec(
            "lip-safe-gold-v0",
            "safe",
            safe,
            soft_alpha(safe, 6.0),
            {
                "cornerReach": 0.08,
                "upperLipTightness": -0.04,
                "lowerLipTightness": -0.04,
                "verticalOffset": 0.0,
                "innerMouthGuard": 0.1,
                "edgeFeather": 0.08,
                "coverage": 1.06,
            },
            ["userAdjustment", "hybrid", "arfaceUv"],
            ["safe variant may spill on skin; must be visually reviewed"],
            {"source": "user_gold_lip_mask_gray", "morphology": "dilate_3px"},
        ),
    ]


def build_blush_candidates(size: tuple[int, int], anchor: dict[str, float]) -> list[CandidateSpec]:
    w, h = size
    cx, cy, fw, fh = anchor["cx"], anchor["cy"], anchor["width"], anchor["height"]
    left = (cx - fw * 0.24, cy + fh * 0.08)
    right = (cx + fw * 0.24, cy + fh * 0.08)

    specs = []
    for policy, scale, yoff, opacity, warning in [
        ("tight", 0.78, -0.01, 0.55, "conservative cheek placement; visibility may be subtle"),
        ("balanced", 1.0, 0.0, 0.68, "soft cosmetic placement; no dataset gold available"),
        ("safe", 1.18, 0.02, 0.72, "wide blush candidate; watch nose/under-eye spill"),
    ]:
        mask = (
            ellipse_mask(size, (left[0], left[1] + fh * yoff), (fw * 0.13 * scale, fh * 0.075 * scale), -18)
            | ellipse_mask(size, (right[0], right[1] + fh * yoff), (fw * 0.13 * scale, fh * 0.075 * scale), 18)
        )
        specs.append(
            CandidateSpec(
                f"blush-{policy}-soft-oval-v0",
                policy,
                mask,
                soft_alpha(mask, 24.0 * scale),
                {
                    "centerX": 0.0,
                    "centerY": yoff,
                    "size": scale,
                    "angle": 18.0,
                    "noseGuard": 0.18,
                    "underEyeGuard": 0.16,
                    "mouthCornerGuard": 0.15,
                    "feather": 0.75,
                    "intensity": opacity,
                },
                ["externalMaskPrior", "faceParsing", "colorConfidence", "arfaceUv", "hybrid"],
                [warning],
                {"model": "bilateral_soft_cheek_oval", "faceAnchor": anchor},
            )
        )
    return specs


def build_brow_candidates(size: tuple[int, int], anchor: dict[str, float]) -> list[CandidateSpec]:
    cx, cy, fw, fh = anchor["cx"], anchor["cy"], anchor["width"], anchor["height"]
    specs = []
    for policy, width_mul, arch, thickness, tail, warning in [
        ("tight", 0.9, 0.08, 12, 0.92, "conservative brow envelope; may under-cover tail"),
        ("balanced", 1.0, 0.1, 16, 1.0, "landmark-style brow envelope; no person-specific hair segmentation"),
        ("safe", 1.08, 0.12, 20, 1.12, "wider brow envelope; watch forehead/hair confusion"),
    ]:
        mask = np.zeros((size[1], size[0]), dtype=bool)
        for side in (-1, 1):
            x0 = cx + side * fw * 0.09
            x1 = cx + side * fw * 0.33 * width_mul
            inner = (x0, cy - fh * 0.26)
            arch_pt = (cx + side * fw * 0.22, cy - fh * (0.29 + arch))
            outer = (x1 * tail + x0 * (1 - tail), cy - fh * 0.27)
            pts = [inner, arch_pt, outer]
            mask |= stroke_polyline_mask(size, pts, thickness)
        specs.append(
            CandidateSpec(
                f"brow-{policy}-stroke-envelope-v0",
                policy,
                mask,
                soft_alpha(mask, thickness * 0.65),
                {
                    "headPosition": 0.0,
                    "archHeight": arch,
                    "tailLength": tail,
                    "tailAngle": 0.0,
                    "thickness": float(thickness),
                    "verticalOffset": 0.0,
                    "leftRightBalance": 0.0,
                    "softness": 0.55,
                },
                ["externalMaskPrior", "mediapipe", "colorConfidence", "arfaceUv", "hybrid"],
                [warning],
                {"model": "parametric_brow_stroke_envelope", "faceAnchor": anchor},
            )
        )
    return specs


def eyelid_curve(cx: float, cy: float, fw: float, fh: float, side: int, y_shift: float) -> list[tuple[float, float]]:
    inner_x = cx + side * fw * 0.08
    outer_x = cx + side * fw * 0.29
    mid_x = cx + side * fw * 0.185
    y = cy - fh * 0.135 + y_shift
    arch_y = y - fh * 0.028
    return [(inner_x, y), (mid_x, arch_y), (outer_x, y + fh * 0.01)]


def build_eyeliner_candidates(size: tuple[int, int], anchor: dict[str, float]) -> list[CandidateSpec]:
    cx, cy, fw, fh = anchor["cx"], anchor["cy"], anchor["width"], anchor["height"]
    specs = []
    configs = [
        ("tight", 5, 0.08, -4.0, "minimal-safe upper lashline; selected if broader line is unstable"),
        ("balanced", 7, 0.13, 0.0, "parametric upper lashline with small wing; no blink runtime proof"),
        ("safe", 9, 0.18, 3.0, "visible eyeliner line; watch eye opening/eyeball spill"),
    ]
    for policy, thickness, tail_len, y_shift, warning in configs:
        mask = np.zeros((size[1], size[0]), dtype=bool)
        for side in (-1, 1):
            pts = eyelid_curve(cx, cy, fw, fh, side, y_shift)
            outer = pts[-1]
            wing = (outer[0] + side * fw * tail_len, outer[1] - fh * 0.035)
            mask |= stroke_polyline_mask(size, pts, thickness, (outer, wing))
        if policy == "tight":
            selected_policy = "minimal-safe"
            candidate_id = "eyeliner-minimal-safe-lashline-v0"
        else:
            selected_policy = policy
            candidate_id = f"eyeliner-{policy}-lashline-v0"
        specs.append(
            CandidateSpec(
                candidate_id,
                selected_policy,
                mask,
                soft_alpha(mask, max(2.0, thickness * 0.55)),
                {
                    "upperLineOffset": y_shift,
                    "lineThickness": float(thickness),
                    "tailLength": tail_len,
                    "tailAngle": -12.0,
                    "outerCornerReach": tail_len,
                    "innerCornerStart": 0.08,
                    "softness": 0.5,
                    "blinkFade": 0.25,
                },
                ["mediapipe", "appleVision", "colorConfidence", "externalMaskPrior", "arfaceUv", "hybrid"],
                [warning, "deferred blink/yaw iPhone test required"],
                {"model": "parametric_upper_lashline_with_tail", "faceAnchor": anchor},
            )
        )
    return specs


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


def barycentric_grid(tri_xy: np.ndarray, min_x: int, max_x: int, min_y: int, max_y: int, stride: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    yy, xx = np.mgrid[min_y : max_y + 1 : stride, min_x : max_x + 1 : stride]
    x = xx.astype(np.float64)
    y = yy.astype(np.float64)
    x0, y0 = tri_xy[0]
    x1, y1 = tri_xy[1]
    x2, y2 = tri_xy[2]
    denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(denom) < 1e-8:
        empty = np.asarray([], dtype=np.float64)
        return empty, empty, empty, empty, empty
    w0 = ((y1 - y2) * (x - x2) + (x2 - x1) * (y - y2)) / denom
    w1 = ((y2 - y0) * (x - x2) + (x0 - x2) * (y - y2)) / denom
    w2 = 1.0 - w0 - w1
    inside = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
    return x[inside], y[inside], w0[inside], w1[inside], w2[inside]


def interpolate_uv(tri_uv: np.ndarray, tri_w: np.ndarray, w0: np.ndarray, w1: np.ndarray, w2: np.ndarray) -> np.ndarray:
    inv_w = 1.0 / np.clip(tri_w, 1e-6, None)
    denom = (w0 * inv_w[0]) + (w1 * inv_w[1]) + (w2 * inv_w[2])
    u = ((w0 * tri_uv[0, 0] * inv_w[0]) + (w1 * tri_uv[1, 0] * inv_w[1]) + (w2 * tri_uv[2, 0] * inv_w[2])) / denom
    v = ((w0 * tri_uv[0, 1] * inv_w[0]) + (w1 * tri_uv[1, 1] * inv_w[1]) + (w2 * tri_uv[2, 1] * inv_w[2])) / denom
    return np.stack([u, v], axis=1)


def uv_to_rc(uv: np.ndarray, resolution: int) -> tuple[np.ndarray, np.ndarray]:
    u = np.clip(uv[:, 0], 0.0, 1.0)
    v = np.clip(uv[:, 1], 0.0, 1.0)
    cols = np.rint(u * (resolution - 1)).astype(np.int32)
    rows = np.rint((1.0 - v) * (resolution - 1)).astype(np.int32)
    return rows, cols


def back_project_mask(mask: np.ndarray, export: dict[str, Any], resolution: int, stride: int) -> np.ndarray:
    screen_vertices, uvs, indices = export_arrays(export)
    atlas_sum = np.zeros((resolution, resolution), dtype=np.float32)
    atlas_count = np.zeros((resolution, resolution), dtype=np.float32)
    if screen_vertices.ndim != 2 or uvs.ndim != 2 or len(screen_vertices) != len(uvs):
        return atlas_sum
    h, w = mask.shape
    for tri in iter_triangles(indices):
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(np.min(tri_xy[:, 0]))))
        max_x = min(w - 1, int(math.ceil(np.max(tri_xy[:, 0]))))
        min_y = max(0, int(math.floor(np.min(tri_xy[:, 1]))))
        max_y = min(h - 1, int(math.ceil(np.max(tri_xy[:, 1]))))
        if max_x < min_x or max_y < min_y:
            continue
        x, y, w0, w1, w2 = barycentric_grid(tri_xy, min_x, max_x, min_y, max_y, stride)
        if len(x) == 0:
            continue
        xi = np.clip(np.rint(x).astype(np.int32), 0, w - 1)
        yi = np.clip(np.rint(y).astype(np.int32), 0, h - 1)
        sample = mask[yi, xi].astype(np.float32)
        tri_w = tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3)
        uv = interpolate_uv(uvs[tri], tri_w, w0, w1, w2)
        rows, cols = uv_to_rc(uv, resolution)
        np.add.at(atlas_sum, (rows, cols), sample)
        np.add.at(atlas_count, (rows, cols), 1.0)
    probability = np.divide(atlas_sum, atlas_count, out=np.zeros_like(atlas_sum), where=atlas_count > 0)
    return np.asarray(Image.fromarray(np.rint(probability * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=1)), dtype=np.float32) / 255.0


def render_atlas_to_screen(probability: np.ndarray, export: dict[str, Any], size: tuple[int, int], threshold: float, stride: int) -> np.ndarray:
    screen_vertices, uvs, indices = export_arrays(export)
    w, h = size
    predicted = np.zeros((h, w), dtype=bool)
    if screen_vertices.ndim != 2 or uvs.ndim != 2 or len(screen_vertices) != len(uvs):
        return predicted
    for tri in iter_triangles(indices):
        tri_screen = screen_vertices[tri]
        tri_xy = tri_screen[:, :2]
        min_x = max(0, int(math.floor(np.min(tri_xy[:, 0]))))
        max_x = min(w - 1, int(math.ceil(np.max(tri_xy[:, 0]))))
        min_y = max(0, int(math.floor(np.min(tri_xy[:, 1]))))
        max_y = min(h - 1, int(math.ceil(np.max(tri_xy[:, 1]))))
        if max_x < min_x or max_y < min_y:
            continue
        x, y, w0, w1, w2 = barycentric_grid(tri_xy, min_x, max_x, min_y, max_y, stride)
        if len(x) == 0:
            continue
        tri_w = tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3)
        uv = interpolate_uv(uvs[tri], tri_w, w0, w1, w2)
        rows, cols = uv_to_rc(uv, probability.shape[0])
        sample = probability[rows, cols] >= threshold
        xi = np.clip(np.rint(x).astype(np.int32), 0, w - 1)
        yi = np.clip(np.rint(y).astype(np.int32), 0, h - 1)
        predicted[yi[sample], xi[sample]] = True
    return predicted


def comparison_metrics(candidate: np.ndarray, reference: np.ndarray) -> dict[str, float]:
    cand = candidate.astype(bool)
    ref = reference.astype(bool)
    tp = int(np.count_nonzero(cand & ref))
    fp = int(np.count_nonzero(cand & ~ref))
    fn = int(np.count_nonzero(~cand & ref))
    union = tp + fp + fn
    return {
        "iou": round(tp / union, 6) if union else 0.0,
        "precision": round(tp / (tp + fp), 6) if (tp + fp) else 0.0,
        "recall": round(tp / (tp + fn), 6) if (tp + fn) else 0.0,
        "candidatePositivePixels": int(np.count_nonzero(cand)),
        "referencePositivePixels": int(np.count_nonzero(ref)),
    }


def overlay_image(frame: Image.Image, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    base = frame.convert("RGB")
    overlay = Image.new("RGB", base.size, color)
    alpha = alpha_to_image(soft_alpha(mask, 5.0))
    return Image.composite(overlay, base, alpha).convert("RGB")


def round_trip_overlay(frame: Image.Image, reference: np.ndarray, predicted: np.ndarray) -> Image.Image:
    base = frame.convert("RGB")
    red = Image.new("RGB", frame.size, (255, 30, 60))
    green = Image.new("RGB", frame.size, (30, 220, 120))
    blue = Image.new("RGB", frame.size, (60, 130, 255))
    tp = reference & predicted
    miss = reference & ~predicted
    extra = predicted & ~reference
    img = Image.composite(green, base, mask_to_image(tp))
    img = Image.composite(red, img, mask_to_image(miss))
    img = Image.composite(blue, img, mask_to_image(extra))
    return Image.blend(base, img, 0.55)


def save_contact_sheet(paths: list[tuple[str, Path]], output: Path, thumb_width: int = 260) -> None:
    tiles: list[Image.Image] = []
    font_h = 28
    for label, path in paths:
        img = Image.open(path).convert("RGB")
        ratio = thumb_width / img.width
        thumb = img.resize((thumb_width, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb.width, thumb.height + font_h), "white")
        tile.paste(thumb, (0, font_h))
        ImageDraw.Draw(tile).text((8, 7), label[:34], fill=(0, 0, 0))
        tiles.append(tile)
    if not tiles:
        return
    cols = min(3, len(tiles))
    rows = math.ceil(len(tiles) / cols)
    cell_w = max(t.width for t in tiles)
    cell_h = max(t.height for t in tiles)
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
    for idx, tile in enumerate(tiles):
        x = (idx % cols) * cell_w
        y = (idx // cols) * cell_h
        sheet.paste(tile, (x, y))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def region_maps(candidates: list[CandidateSpec], selected: CandidateSpec) -> dict[str, np.ndarray]:
    all_masks = np.zeros_like(selected.mask)
    for candidate in candidates:
        all_masks |= candidate.mask
    include = erode(selected.mask, 2)
    exclude = ~dilate(all_masks, 18)
    unknown = all_masks & ~include
    return {"include": include, "exclude": exclude, "unknown": unknown}


def shape_metrics(mask: np.ndarray, size: tuple[int, int]) -> dict[str, Any]:
    h, w = mask.shape
    positive = int(np.count_nonzero(mask))
    area_ratio = positive / float(w * h)
    ys, xs = np.where(mask)
    if positive:
        cx = float(xs.mean())
        cy = float(ys.mean())
        bbox = {
            "minX": int(xs.min()),
            "minY": int(ys.min()),
            "maxX": int(xs.max()),
            "maxY": int(ys.max()),
        }
        left = int(np.count_nonzero(mask[:, : w // 2]))
        right = int(np.count_nonzero(mask[:, w // 2 :]))
    else:
        cx = cy = 0.0
        bbox = {"minX": 0, "minY": 0, "maxX": 0, "maxY": 0}
        left = right = 0
    return {
        "positivePixels": positive,
        "areaRatio": round(area_ratio, 8),
        "centroid": {"x": round(cx, 3), "y": round(cy, 3)},
        "bbox": bbox,
        "leftRightAbsDiffRatio": round(abs(left - right) / positive, 6) if positive else None,
    }


def package_for(
    region: str,
    selected: CandidateSpec,
    region_dir: Path,
    uv_status: dict[str, Any],
    source_frame: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-region-mask-package-v0",
        "packageId": f"e7-{region}-{selected.policy}-package-v0",
        "region": region,
        "status": "preXcodeReady" if uv_status.get("available") else "partial",
        "selectedPolicy": selected.policy,
        "sourceLineage": {
            "sources": selected.sources,
            "candidateIds": [selected.candidate_id],
            "externalPrior": {
                "sourceName": "local_reference_and_parametric_prior",
                "role": "silver_draft_only",
                "licenseNote": "No external upload; broad dataset/source review still required before product use.",
            },
        },
        "sourceFrameMetadata": source_frame,
        "mask2d": {
            "hardMaskPath": str(region_dir / "candidates" / f"{selected.candidate_id}.mask.png"),
            "softAlphaPath": str(region_dir / "candidates" / f"{selected.candidate_id}.alpha.png"),
            "includeMapPath": str(region_dir / "maps" / "include.png"),
            "excludeMapPath": str(region_dir / "maps" / "exclude.png"),
            "unknownMapPath": str(region_dir / "maps" / "unknown.png"),
        },
        "uvMask": {
            "texturePath": str(region_dir / "uv_projection" / f"{selected.candidate_id}.uv_probability.png"),
            "resolution": uv_status.get("uvResolution", UV_RESOLUTION),
            "roundTripOverlayPath": str(region_dir / "uv_projection" / f"{selected.candidate_id}.round_trip_overlay.png"),
            "roundTripStatus": "ready" if uv_status.get("available") else "partial",
            "roundTripScore": uv_status.get("roundTrip", {}),
        },
        "adjustment": selected.adjustment,
        "qualityWarnings": selected.warnings,
        "runtimeApplyPayload": {
            "region": region,
            "maskTextureId": f"e7-{region}-{selected.policy}-uv-v0",
            "threshold": 0.5,
            "feather": 0.07,
            "opacity": 0.72 if region != "blush" else 0.45,
            "runtimeReady": False,
        },
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "longTermRawFrameStored": False,
        },
    }


def summary_markdown(region: str, selected: CandidateSpec, scorecard: dict[str, Any]) -> str:
    warnings = "\n".join(f"- {warning}" for warning in selected.warnings)
    return f"""# {region} Region Summary

Decision: `{scorecard["decision"]}`

Selected policy: `{selected.policy}`

Selected candidate: `{selected.candidate_id}`

Why:
- Generated local-only mask candidate and maps.
- Produced ARFace UV projection and same-frame round-trip preview.
- Adjustment axes are attached to package payload.

Warnings:
{warnings}

This is pre-Xcode evidence only. It is not iPhone runtime proof and must not be used to claim Green/product-quality-ready.
"""


def build_candidates(size: tuple[int, int], export: dict[str, Any], lip_reference: np.ndarray) -> dict[str, list[CandidateSpec]]:
    anchor = face_anchor(export, size)
    return {
        "lip": build_lip_candidates(size, lip_reference),
        "blush": build_blush_candidates(size, anchor),
        "brow": build_brow_candidates(size, anchor),
        "eyeliner": build_eyeliner_candidates(size, anchor),
    }


def main() -> int:
    args = parse_args()
    frame = Image.open(args.frame).convert("RGB")
    size = frame.size
    export = load_json(args.arface_export)
    lip_reference = load_lip_reference(args.lip_gold, size)
    all_candidates = build_candidates(size, export, lip_reference)

    source_frame = {
        "capturePairId": export.get("capturePairId"),
        "frameWidth": size[0],
        "frameHeight": size[1],
        "orientation": export.get("display", {}).get("orientation", "portrait"),
        "isMirrored": bool(export.get("display", {}).get("isMirrored", False)),
    }

    session_root = args.session_root
    selected_packages: dict[str, Any] = {}
    region_decisions: dict[str, str] = {}
    contact_sheet_inputs: list[tuple[str, Path]] = []

    for region, candidates in all_candidates.items():
        region_dir = session_root / "regions" / region
        for sub in ("candidates", "maps", "uv_projection"):
            (region_dir / sub).mkdir(parents=True, exist_ok=True)

        selected = next((candidate for candidate in candidates if candidate.policy == "balanced"), candidates[0])
        if region == "eyeliner":
            selected = next((candidate for candidate in candidates if candidate.policy == "minimal-safe"), candidates[0])

        maps = region_maps(candidates, selected)
        for name, mask in maps.items():
            mask_to_image(mask).save(region_dir / "maps" / f"{name}.png")

        candidate_reports = []
        region_contact_inputs: list[tuple[str, Path]] = []
        selected_uv_status: dict[str, Any] = {"available": False}
        for candidate in candidates:
            mask_path = region_dir / "candidates" / f"{candidate.candidate_id}.mask.png"
            alpha_path = region_dir / "candidates" / f"{candidate.candidate_id}.alpha.png"
            overlay_path = region_dir / "candidates" / f"{candidate.candidate_id}.overlay.png"
            mask_to_image(candidate.mask).save(mask_path)
            alpha_to_image(candidate.soft_alpha).save(alpha_path)
            overlay_image(frame, candidate.mask, (240, 60, 120) if region in ("lip", "blush") else (45, 110, 230)).save(overlay_path)

            probability = back_project_mask(candidate.mask, export, args.uv_resolution, args.uv_sample_stride)
            predicted = render_atlas_to_screen(probability, export, size, 0.5, args.uv_sample_stride)
            uv_probability_path = region_dir / "uv_projection" / f"{candidate.candidate_id}.uv_probability.png"
            round_trip_path = region_dir / "uv_projection" / f"{candidate.candidate_id}.round_trip_overlay.png"
            alpha_to_image(probability).save(uv_probability_path)
            round_trip_overlay(frame, candidate.mask, predicted).save(round_trip_path)
            uv_status = {
                "available": True,
                "uvResolution": args.uv_resolution,
                "sampleStride": args.uv_sample_stride,
                "roundTrip": comparison_metrics(predicted, candidate.mask),
            }
            if candidate.candidate_id == selected.candidate_id:
                selected_uv_status = uv_status
            report = {
                "candidateId": candidate.candidate_id,
                "policy": candidate.policy,
                "adjustment": candidate.adjustment,
                "sources": candidate.sources,
                "warnings": candidate.warnings,
                "shape": shape_metrics(candidate.mask, size),
                "uvProjection": uv_status,
                "trace": candidate.trace,
                "paths": {
                    "mask": str(mask_path),
                    "alpha": str(alpha_path),
                    "overlay": str(overlay_path),
                    "uvProbability": str(uv_probability_path),
                    "roundTripOverlay": str(round_trip_path),
                },
            }
            candidate_reports.append(report)
            region_contact_inputs.append((candidate.policy, overlay_path))
            region_contact_inputs.append((f"{candidate.policy} uv", round_trip_path))
            if candidate.candidate_id == selected.candidate_id:
                contact_sheet_inputs.append((region, overlay_path))
                contact_sheet_inputs.append((f"{region} uv", round_trip_path))

        save_contact_sheet(region_contact_inputs, region_dir / "contact_sheet.png")

        selected_report = next(item for item in candidate_reports if item["candidateId"] == selected.candidate_id)
        decision = "pre-xcode-ready" if selected_uv_status.get("available") else "partial"
        if region == "eyeliner" and selected.mask.any():
            decision = "pre-xcode-ready"
        region_decisions[region] = decision

        scorecard = {
            "schemaVersion": "e7-region-scorecard-v0",
            "region": region,
            "decision": decision,
            "selectedCandidateId": selected.candidate_id,
            "selectedPolicy": selected.policy,
            "candidateCount": len(candidates),
            "candidateReports": candidate_reports,
            "rejectRulesChecked": [
                "empty mask",
                "full-face mask",
                "negative spill severe",
                "wrong coordinate/mirrored",
                "missing source lineage",
                "privacy flags missing",
            ],
            "preXcodeOnly": True,
        }
        write_json(region_dir / "scorecard.json", scorecard)
        write_json(region_dir / "selected_policy.json", {
            "schemaVersion": "e7-region-selected-policy-v0",
            "region": region,
            "decision": decision,
            "selectedPolicy": selected.policy,
            "selectedCandidateId": selected.candidate_id,
            "reason": "Best current local-only candidate for pre-Xcode package handoff.",
            "requiresHumanReview": True,
            "iphoneEvidenceRequiredForGreen": True,
        })
        write_json(region_dir / "adjustment_axes.json", {
            "schemaVersion": "e7-region-adjustment-axes-v0",
            "region": region,
            "axes": selected.adjustment,
            "controlStyle": "slider_plus_quick_buttons",
        })
        write_json(region_dir / "input_manifest.json", {
            "schemaVersion": "e7-region-input-manifest-v0",
            "region": region,
            "sourceFrame": str(args.frame),
            "arfaceExport": str(args.arface_export),
            "lipGoldReference": str(args.lip_gold) if region == "lip" else None,
            "localOnly": True,
            "offDeviceUpload": False,
            "longTermRawFrameStored": False,
        })
        write_json(region_dir / "signal_report.json", {
            "schemaVersion": "e7-region-signal-report-v0",
            "region": region,
            "signalsUsed": selected.sources,
            "signalsMissingOrDeferred": [
                "real iPhone runtime evidence",
                "held-out frame projection",
                "human visual acceptance for selected candidate",
                "full external dataset license review",
            ],
            "qualityWarnings": selected.warnings,
        })
        package = package_for(region, selected, region_dir, selected_uv_status, source_frame)
        write_json(region_dir / "package.json", package)
        write_text(region_dir / "summary.md", summary_markdown(region, selected, scorecard))
        selected_packages[region] = package

    composite = {
        "schemaVersion": "e7-saved-makeup-package-v0",
        "createdAt": utc_now(),
        "sessionId": session_root.name,
        "status": "pre-xcode-ready" if all(value == "pre-xcode-ready" for value in region_decisions.values()) else "partial",
        "regionDecisions": region_decisions,
        "packages": selected_packages,
        "runtimeApplyPayload": {
            "schemaVersion": "e7-composite-region-runtime-payload-v0",
            "packageId": f"{session_root.name}-composite",
            "regions": {
                region: package["runtimeApplyPayload"] for region, package in selected_packages.items()
            },
            "runtimeReady": False,
            "preXcodeReady": True,
            "localOnly": True,
            "offDeviceUpload": False,
            "longTermRawFrameStored": False,
        },
    }
    write_json(session_root / "composite_apply_payload.json", composite)
    save_contact_sheet(contact_sheet_inputs, session_root / "contact_sheet.png")
    write_text(
        session_root / "experiment_summary.md",
        "\n".join(
            [
                "# E7 Full-Face Region Generate Experiment Summary",
                "",
                f"Session: `{session_root.name}`",
                "",
                "Region decisions:",
                *[f"- {region}: `{decision}`" for region, decision in region_decisions.items()],
                "",
                "Notes:",
                "- All artifacts are local-only buildless outputs.",
                "- Eyeliner produced a minimal-safe candidate and remains subject to blink/yaw iPhone evidence later.",
                "- No Green/product-quality-ready claim is made.",
            ]
        ),
    )

    timeline = session_root / "timeline.md"
    if timeline.exists():
        with timeline.open("a", encoding="utf-8") as handle:
            handle.write(
                "\n## 2026-06-27 05:00 KST - Phase 1 Candidate Generation\n\n"
                "- Generated local-only candidates for lip / blush / brow / eyeliner.\n"
                "- Created include/exclude/unknown maps, UV probability textures, round-trip overlays, scorecards, selected policies, adjustment axes, region packages, and composite payload.\n"
                "- Eyeliner minimal-safe candidate created; deferred blink/yaw iPhone evidence remains required before Green.\n"
            )
    print(json.dumps({"sessionRoot": str(session_root), "regionDecisions": region_decisions}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
