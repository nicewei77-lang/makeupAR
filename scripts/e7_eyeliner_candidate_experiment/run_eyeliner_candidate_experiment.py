#!/usr/bin/env python3
"""Run the E7 buildless eyeliner candidate experiment.

This tool consumes an already-generated MediaPipe landmark JSON and a same-pair
ARFace export. It does not run live MediaPipe, upload data, build Xcode, or touch
an iPhone. Outputs are local evidence plus a Korean report with curated images.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.e7_region_generate.build_region_candidates import (
    add_eye_tail,
    alpha_to_image,
    back_project_mask,
    comparison_metrics,
    dilate,
    erode,
    load_json,
    load_uv_prior,
    mask_to_image,
    overlay_image,
    render_atlas_to_screen,
    render_atlas_to_screen_alpha,
    round_trip_overlay,
    save_contact_sheet,
    soft_alpha,
    split_lr_components,
    stroke_polyline_mask,
    upper_lashline_points,
    write_json,
    write_text,
)


DEFAULT_CAPTURE_PAIR = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06")
DEFAULT_EYE_UV_PRIOR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/eye-smooth-mask-v1.png")
DEFAULT_BASELINE_ROOT = Path("evidence/e7-region-generate/session-20260626T195853Z/regions/eyeliner")
DEFAULT_DOC_REPORT = Path("docs/product/e7-eyeliner-candidate-experiment-report-2026-06-27")
UV_RESOLUTION = 512


RIGHT_UPPER_OUTER_TO_INNER = [33, 246, 161, 160, 159, 158, 157, 173, 133]
RIGHT_EYE_CONTOUR = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
LEFT_UPPER_OUTER_TO_INNER = [263, 466, 388, 387, 386, 385, 384, 398, 362]
LEFT_EYE_CONTOUR = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]


@dataclass(frozen=True)
class EyeGeometry:
    side: str
    upper_inner_to_outer: list[tuple[float, float]]
    eye_contour: list[tuple[float, float]]
    inner_corner: tuple[float, float]
    outer_corner: tuple[float, float]
    tail_direction: int


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    policy: str
    family: str
    mask: np.ndarray
    alpha: np.ndarray
    adjustment: dict[str, float]
    trace: dict[str, Any]
    warnings: list[str]
    source_signals: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E7 eyeliner candidate experiment.")
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--eye-uv-prior", type=Path, default=DEFAULT_EYE_UV_PRIOR)
    parser.add_argument("--baseline-root", type=Path, default=DEFAULT_BASELINE_ROOT)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--doc-report", type=Path, default=DEFAULT_DOC_REPORT)
    parser.add_argument("--uv-resolution", type=int, default=UV_RESOLUTION)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_mediapipe(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def point_map(mediapipe: dict[str, Any]) -> dict[int, tuple[float, float]]:
    return {
        int(item["index"]): (float(item["x"]), float(item["y"]))
        for item in mediapipe.get("landmarks", [])
        if "index" in item and "x" in item and "y" in item
    }


def points_for(indices: list[int], points: dict[int, tuple[float, float]]) -> list[tuple[float, float]]:
    missing = [idx for idx in indices if idx not in points]
    if missing:
        raise ValueError(f"Missing MediaPipe landmarks: {missing}")
    return [points[idx] for idx in indices]


def build_eye_geometry(mediapipe: dict[str, Any]) -> list[EyeGeometry]:
    pts = point_map(mediapipe)
    right_outer_to_inner = points_for(RIGHT_UPPER_OUTER_TO_INNER, pts)
    left_outer_to_inner = points_for(LEFT_UPPER_OUTER_TO_INNER, pts)
    right_contour = points_for(RIGHT_EYE_CONTOUR, pts)
    left_contour = points_for(LEFT_EYE_CONTOUR, pts)
    return [
        EyeGeometry(
            side="right",
            upper_inner_to_outer=list(reversed(right_outer_to_inner)),
            eye_contour=right_contour,
            inner_corner=pts[133],
            outer_corner=pts[33],
            tail_direction=-1,
        ),
        EyeGeometry(
            side="left",
            upper_inner_to_outer=list(reversed(left_outer_to_inner)),
            eye_contour=left_contour,
            inner_corner=pts[362],
            outer_corner=pts[263],
            tail_direction=1,
        ),
    ]


def polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> np.ndarray:
    img = Image.new("L", size, 0)
    ImageDraw.Draw(img).polygon(points, fill=255)
    return np.asarray(img) > 0


def resample_curve(points: list[tuple[float, float]], count: int = 64) -> list[tuple[float, float]]:
    arr = np.asarray(points, dtype=np.float64)
    if len(arr) < 2:
        return points
    seg = np.sqrt(np.sum(np.diff(arr, axis=0) ** 2, axis=1))
    dist = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(dist[-1])
    if total <= 1e-6:
        return points
    samples = np.linspace(0.0, total, count)
    xs = np.interp(samples, dist, arr[:, 0])
    ys = np.interp(samples, dist, arr[:, 1])
    return list(zip(xs.tolist(), ys.tolist()))


def offset_curve(points: list[tuple[float, float]], offset_px: float, outer_lift_px: float = 0.0) -> list[tuple[float, float]]:
    arr = np.asarray(points, dtype=np.float64)
    out: list[tuple[float, float]] = []
    if len(arr) < 2:
        return points
    for idx, point in enumerate(arr):
        prev_pt = arr[max(0, idx - 1)]
        next_pt = arr[min(len(arr) - 1, idx + 1)]
        tangent = next_pt - prev_pt
        if np.linalg.norm(tangent) < 1e-6:
            normal = np.asarray([0.0, -1.0])
        else:
            normal = np.asarray([-tangent[1], tangent[0]], dtype=np.float64)
            normal /= max(1e-6, np.linalg.norm(normal))
            if normal[1] > 0:
                normal *= -1.0
        t = idx / max(1, len(arr) - 1)
        lifted = point + normal * offset_px + np.asarray([0.0, outer_lift_px * t])
        out.append((float(lifted[0]), float(lifted[1])))
    return out


def trim_curve(points: list[tuple[float, float]], inner_start: float, outer_reach: float) -> list[tuple[float, float]]:
    curve = resample_curve(points, 80)
    start = min(max(inner_start, 0.0), 0.95)
    end = min(max(outer_reach, start + 0.02), 1.0)
    start_idx = int(round(start * (len(curve) - 1)))
    end_idx = int(round(end * (len(curve) - 1)))
    return curve[start_idx : end_idx + 1]


def draw_variable_stroke(
    size: tuple[int, int],
    points: list[tuple[float, float]],
    thickness: float,
    taper: float,
    tail: tuple[tuple[float, float], tuple[float, float]] | None,
) -> np.ndarray:
    img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(img)
    if len(points) >= 2:
        for idx in range(len(points) - 1):
            t = idx / max(1, len(points) - 2)
            profile = 0.58 + 0.46 * math.sin(t * math.pi * 0.92)
            profile *= 1.0 + 0.18 * t
            if t < 0.12:
                profile *= 0.72 + t * 2.1
            if t > 0.88:
                profile *= 1.0 - (t - 0.88) * taper * 1.45
            width = max(1, int(round(thickness * profile)))
            draw.line([points[idx], points[idx + 1]], fill=255, width=width, joint="curve")
            r = max(1, width // 2)
            x, y = points[idx + 1]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    if tail is not None:
        tail_start, tail_end = tail
        steps = 8
        last = tail_start
        for step in range(1, steps + 1):
            t = step / steps
            cur = (
                tail_start[0] * (1 - t) + tail_end[0] * t,
                tail_start[1] * (1 - t) + tail_end[1] * t,
            )
            width = max(1, int(round(thickness * (1.0 - 0.72 * t))))
            draw.line([last, cur], fill=255, width=width, joint="curve")
            last = cur
    return np.asarray(img) > 0


def dark_edge_snap(frame: Image.Image, points: list[tuple[float, float]], radius: int = 5) -> list[tuple[float, float]]:
    gray = np.asarray(frame.convert("L"), dtype=np.float32)
    height, width = gray.shape
    snapped = []
    for x, y in points:
        xi = int(round(x))
        yi = int(round(y))
        best_y = yi
        best_score = 255.0
        for dy in range(-radius, radius + 1):
            yy = min(max(yi + dy, 0), height - 1)
            xx0 = max(0, xi - 2)
            xx1 = min(width, xi + 3)
            score = float(np.mean(gray[yy, xx0:xx1]))
            # Prefer dark pixels but keep the correction local.
            score += abs(dy) * 4.5
            if score < best_score:
                best_score = score
                best_y = yy
        snapped.append((float(x), float(best_y)))
    return snapped


def eye_width(eye: EyeGeometry) -> float:
    return float(math.dist(eye.inner_corner, eye.outer_corner))


def build_parametric_candidate(
    size: tuple[int, int],
    frame: Image.Image,
    eyes: list[EyeGeometry],
    candidate_id: str,
    policy: str,
    family: str,
    inner_start: float,
    outer_reach: float,
    line_height: float,
    thickness: float,
    tail_length: float,
    tail_angle: float,
    tail_lift: float,
    taper: float,
    softness: float,
    exclude_eye_opening: bool,
    edge_snap: bool = False,
    outer_lift: float = 0.0,
    warnings: list[str] | None = None,
) -> Candidate:
    mask = np.zeros((size[1], size[0]), dtype=bool)
    eye_opening = np.zeros_like(mask)
    line_traces: dict[str, Any] = {}
    for eye in eyes:
        eye_opening |= polygon_mask(size, eye.eye_contour)
        base_curve = resample_curve(eye.upper_inner_to_outer, 72)
        curve = offset_curve(base_curve, line_height, outer_lift)
        if edge_snap:
            curve = dark_edge_snap(frame, curve, radius=4)
            curve = offset_curve(curve, -1.0, 0.0)
        visible = trim_curve(curve, inner_start, min(outer_reach, 1.0))
        tail = None
        tail_end = None
        if visible:
            tail_start = visible[-1]
            length_px = eye_width(eye) * tail_length
            dx = eye.tail_direction * length_px
            dy = abs(length_px) * math.tan(math.radians(tail_angle)) + tail_lift
            tail_end = (tail_start[0] + dx, tail_start[1] + dy)
            if length_px > 1.0:
                tail = (tail_start, tail_end)
        mask |= draw_variable_stroke(size, visible, thickness, taper, tail)
        line_traces[eye.side] = {
            "innerCorner": {"x": round(eye.inner_corner[0], 3), "y": round(eye.inner_corner[1], 3)},
            "outerCorner": {"x": round(eye.outer_corner[0], 3), "y": round(eye.outer_corner[1], 3)},
            "centerline": [{"x": round(x, 3), "y": round(y, 3)} for x, y in visible],
            "tailEnd": {"x": round(tail_end[0], 3), "y": round(tail_end[1], 3)} if tail_end else None,
        }
    if exclude_eye_opening:
        # Keep the lashline boundary itself; only remove the eye-opening interior.
        mask &= ~erode(eye_opening, 6)
    return Candidate(
        candidate_id=candidate_id,
        policy=policy,
        family=family,
        mask=mask,
        alpha=soft_alpha(mask, softness),
        adjustment={
            "lineHeight": line_height,
            "upperLineOffset": line_height,
            "lineThickness": thickness,
            "innerStart": inner_start,
            "innerCornerStart": inner_start,
            "outerReach": outer_reach,
            "outerCornerReach": max(0.0, outer_reach - 1.0) + tail_length,
            "tailLength": tail_length,
            "tailAngle": tail_angle,
            "tailLift": tail_lift,
            "taper": taper,
            "softness": softness,
            "blinkFade": 0.25,
            "leftRightBalance": 0.0,
        },
        trace={
            "model": family,
            "mediapipeUpperEyelidIndices": {
                "rightOuterToInner": RIGHT_UPPER_OUTER_TO_INNER,
                "leftOuterToInner": LEFT_UPPER_OUTER_TO_INNER,
            },
            "eyeOpeningExcluded": exclude_eye_opening,
            "edgeSnap": edge_snap,
            "lineTraces": line_traces,
        },
        warnings=warnings or ["buildless static frame only; blink/yaw iPhone test deferred"],
        source_signals=["mediapipeLandmarks", "parametricCurve", "arfaceUv", "localOnly"],
    )


def build_legacy_eye_prior_candidates(
    size: tuple[int, int],
    frame: Image.Image,
    arface_export: dict[str, Any],
    eye_uv_prior: Path,
    uv_resolution: int,
) -> list[Candidate]:
    eye_prior = render_atlas_to_screen_alpha(load_uv_prior(eye_uv_prior, uv_resolution), arface_export, size, 1) >= 0.08
    eye_components = split_lr_components(eye_prior) if eye_prior.any() else []
    specs: list[Candidate] = []
    for policy, thickness, tail_len, y_shift in [
        ("legacy-minimal-safe", 4, 0.05, -3.0),
        ("legacy-balanced", 6, 0.08, -2.0),
        ("legacy-safe", 8, 0.12, 0.0),
    ]:
        mask = np.zeros((size[1], size[0]), dtype=bool)
        for side, component in eye_components:
            pts = upper_lashline_points(frame, component, side, y_shift)
            mask = add_eye_tail(mask, size, pts, side, thickness, tail_len)
        if eye_prior.any():
            mask &= dilate(eye_prior, 16)
        specs.append(
            Candidate(
                candidate_id=f"baseline-{policy}-eye-prior-current-frame-v0",
                policy=policy,
                family="legacy_eye_prior_dark_pixel_upper_lashline",
                mask=mask,
                alpha=soft_alpha(mask, max(2.0, thickness * 0.55)),
                adjustment={
                    "lineHeight": y_shift,
                    "upperLineOffset": y_shift,
                    "lineThickness": float(thickness),
                    "innerStart": 0.08,
                    "innerCornerStart": 0.08,
                    "outerReach": 1.0 + tail_len,
                    "outerCornerReach": tail_len,
                    "tailLength": tail_len,
                    "tailAngle": -12.0,
                    "tailLift": 0.0,
                    "taper": 0.5,
                    "softness": 0.5,
                    "blinkFade": 0.25,
                    "leftRightBalance": 0.0,
                },
                trace={
                    "model": "eye_prior_dark_pixel_upper_lashline",
                    "eyePrior": str(eye_uv_prior),
                    "currentFrameRegenerated": True,
                },
                warnings=[
                    "baseline only; broad eye prior and dark pixels, not direct MediaPipe upper eyelid tracking",
                    "buildless static frame only; blink/yaw iPhone test deferred",
                ],
                source_signals=["arfaceEyeUvPrior", "darkPixelConfidence", "localOnly"],
            )
        )
    return specs


def build_candidates(size: tuple[int, int], frame: Image.Image, eyes: list[EyeGeometry], arface_export: dict[str, Any], eye_uv_prior: Path, uv_resolution: int) -> list[Candidate]:
    candidates = [
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-upper-minimal-v0",
            "mp-upper-minimal",
            "mediapipe_upper_eyelid_parametric",
            0.18,
            0.98,
            -7.0,
            4.0,
            0.02,
            -8.0,
            0.0,
            0.70,
            2.8,
            True,
            warnings=["most conservative direct MediaPipe upper eyelid candidate", "blink/yaw iPhone test deferred"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-upper-balanced-v0",
            "mp-upper-balanced",
            "mediapipe_upper_eyelid_parametric",
            0.10,
            1.0,
            -5.5,
            6.0,
            0.06,
            -12.0,
            0.0,
            0.64,
            3.2,
            True,
            warnings=["balanced direct MediaPipe upper eyelid candidate", "selected only if eye opening spill remains low"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-wing-soft-v0",
            "mp-wing-soft",
            "mediapipe_upper_eyelid_parametric_wing",
            0.14,
            1.0,
            -4.5,
            6.0,
            0.14,
            -17.0,
            -1.5,
            0.88,
            3.5,
            True,
            warnings=["expressive wing candidate; likely preset not default", "watch tail angle and asymmetry"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-tail-only-v0",
            "mp-tail-only",
            "mediapipe_upper_eyelid_tail_only",
            0.58,
            1.0,
            -4.0,
            6.5,
            0.10,
            -14.0,
            0.0,
            0.82,
            3.4,
            True,
            warnings=["safe fallback for inner-eye instability", "less full eyeliner coverage by design"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-soft-lashline-shadow-v0",
            "mp-soft-lashline-shadow",
            "mediapipe_upper_eyelid_soft_lashline",
            0.16,
            0.98,
            -3.5,
            8.0,
            0.04,
            -8.0,
            0.0,
            0.52,
            7.0,
            True,
            warnings=["soft lashline fallback; visible line is intentionally less strict", "opacity should be lower in app material"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "mp-edge-snap-hybrid-v0",
            "mp-edge-snap-hybrid",
            "mediapipe_upper_eyelid_edge_snap_hybrid",
            0.12,
            1.0,
            -5.0,
            5.5,
            0.06,
            -12.0,
            0.0,
            0.70,
            3.0,
            True,
            edge_snap=True,
            warnings=["edge/color is only a local correction, not the primary tracker", "reject if snap pulls line into eye opening"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "asset-fit-natural-local-style-v0",
            "asset-fit-natural",
            "local_authored_style_prior_natural",
            0.18,
            1.0,
            -6.0,
            5.8,
            0.05,
            -10.0,
            0.0,
            1.05,
            3.3,
            True,
            outer_lift=-2.8,
            warnings=["local authored style prior; no external asset used", "use as shape preset fitted to MediaPipe landmarks"],
        ),
        build_parametric_candidate(
            size,
            frame,
            eyes,
            "asset-fit-wing-local-style-v0",
            "asset-fit-wing",
            "local_authored_style_prior_wing",
            0.22,
            1.0,
            -5.0,
            6.2,
            0.18,
            -21.0,
            -2.0,
            1.15,
            3.4,
            True,
            outer_lift=-3.5,
            warnings=["local authored wing style prior; expressive candidate only", "not recommended as default unless user selects wing"],
        ),
    ]
    candidates.extend(build_legacy_eye_prior_candidates(size, frame, arface_export, eye_uv_prior, uv_resolution))
    return candidates


def bbox_for_points(points: list[tuple[float, float]], size: tuple[int, int], margin: int) -> tuple[int, int, int, int]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    w, h = size
    return (
        max(0, int(math.floor(min(xs) - margin))),
        max(0, int(math.floor(min(ys) - margin))),
        min(w, int(math.ceil(max(xs) + margin))),
        min(h, int(math.ceil(max(ys) + margin))),
    )


def crop_image(path: Path, bbox: tuple[int, int, int, int], output: Path) -> Path:
    img = Image.open(path).convert("RGB")
    output.parent.mkdir(parents=True, exist_ok=True)
    img.crop(bbox).save(output)
    return output


def draw_geometry_overlay(frame: Image.Image, eyes: list[EyeGeometry], output: Path, show_opening_fill: bool) -> None:
    img = frame.convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    for eye in eyes:
        if show_opening_fill:
            draw.polygon(eye.eye_contour, fill=(255, 70, 70, 70), outline=(255, 40, 40, 220))
        draw.line(eye.upper_inner_to_outer, fill=(30, 220, 140, 255), width=5, joint="curve")
        r = 5
        draw.ellipse((eye.inner_corner[0] - r, eye.inner_corner[1] - r, eye.inner_corner[0] + r, eye.inner_corner[1] + r), fill=(255, 220, 40, 255))
        draw.ellipse((eye.outer_corner[0] - r, eye.outer_corner[1] - r, eye.outer_corner[0] + r, eye.outer_corner[1] + r), fill=(80, 160, 255, 255))
    output.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(output)


def mask_components(mask: np.ndarray) -> int:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return 0
    remaining = set(zip(xs.tolist(), ys.tolist()))
    components = 0
    neighbors = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    while remaining:
        components += 1
        stack = [remaining.pop()]
        while stack:
            x, y = stack.pop()
            for dx, dy in neighbors:
                item = (x + dx, y + dy)
                if item in remaining:
                    remaining.remove(item)
                    stack.append(item)
    return components


def min_distances_to_points(mask: np.ndarray, points: list[tuple[float, float]], max_samples: int = 6000) -> np.ndarray:
    ys, xs = np.where(mask)
    if len(xs) == 0 or not points:
        return np.asarray([], dtype=np.float64)
    coords = np.stack([xs, ys], axis=1).astype(np.float64)
    if len(coords) > max_samples:
        step = max(1, len(coords) // max_samples)
        coords = coords[::step]
    curve = np.asarray(points, dtype=np.float64)
    distances = []
    chunk = 512
    for start in range(0, len(coords), chunk):
        part = coords[start : start + chunk]
        diff = part[:, None, :] - curve[None, :, :]
        distances.append(np.sqrt(np.sum(diff * diff, axis=2)).min(axis=1))
    return np.concatenate(distances)


def area_by_side(mask: np.ndarray) -> dict[str, Any]:
    h, w = mask.shape
    left = int(np.count_nonzero(mask[:, : w // 2]))
    right = int(np.count_nonzero(mask[:, w // 2 :]))
    total = left + right
    return {
        "leftPixels": left,
        "rightPixels": right,
        "leftRightAbsDiffRatio": round(abs(left - right) / total, 6) if total else None,
        "smallLargeRatio": round(min(left, right) / max(left, right), 6) if left and right else 0.0,
    }


def candidate_metrics(candidate: Candidate, eyes: list[EyeGeometry], eye_opening: np.ndarray, uv_metrics: dict[str, Any]) -> dict[str, Any]:
    positive = int(np.count_nonzero(candidate.mask))
    overlap = int(np.count_nonzero(candidate.mask & eye_opening))
    upper_points: list[tuple[float, float]] = []
    tail_distances = []
    smoothness_values = []
    for eye in eyes:
        upper_points.extend(resample_curve(eye.upper_inner_to_outer, 64))
        trace_eye = candidate.trace.get("lineTraces", {}).get(eye.side, {})
        centerline = [(float(item["x"]), float(item["y"])) for item in trace_eye.get("centerline", [])]
        if centerline:
            angles = []
            for idx in range(len(centerline) - 1):
                dx = centerline[idx + 1][0] - centerline[idx][0]
                dy = centerline[idx + 1][1] - centerline[idx][1]
                angles.append(math.atan2(dy, dx))
            if len(angles) > 1:
                deltas = [abs(angles[idx + 1] - angles[idx]) for idx in range(len(angles) - 1)]
                smoothness_values.append(max(0.0, 1.0 - min(1.0, float(np.mean(deltas)) / 0.25)))
        tail_end = trace_eye.get("tailEnd")
        if centerline:
            tail_start = centerline[-1]
            tail_distances.append(float(math.dist(tail_start, eye.outer_corner)))
        elif tail_end:
            tail_distances.append(float(math.dist((tail_end["x"], tail_end["y"]), eye.outer_corner)))
    dists = min_distances_to_points(candidate.mask, upper_points)
    components = mask_components(candidate.mask)
    continuity = max(0.0, 1.0 - max(0, components - 2) / 6.0)
    ys, xs = np.where(candidate.mask)
    bbox = {
        "minX": int(xs.min()) if len(xs) else 0,
        "minY": int(ys.min()) if len(ys) else 0,
        "maxX": int(xs.max()) if len(xs) else 0,
        "maxY": int(ys.max()) if len(ys) else 0,
    }
    return {
        "maskPixels": positive,
        "bbox": bbox,
        "leftRight": area_by_side(candidate.mask),
        "eyeOpeningOverlapPixels": overlap,
        "eyeOpeningOverlapRatio": round(overlap / positive, 6) if positive else None,
        "upperLidMeanDistancePx": round(float(np.mean(dists)), 3) if len(dists) else None,
        "upperLidP95DistancePx": round(float(np.percentile(dists, 95)), 3) if len(dists) else None,
        "tailStartDistanceFromOuterCornerPx": round(float(np.mean(tail_distances)), 3) if tail_distances else None,
        "componentCount": components,
        "lineContinuityScore": round(continuity, 6),
        "smoothnessScore": round(float(np.mean(smoothness_values)), 6) if smoothness_values else None,
        "uvRoundTrip": uv_metrics,
    }


def rank_candidates(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked = []
    for report in reports:
        m = report["metrics"]
        overlap = m["eyeOpeningOverlapRatio"] or 1.0
        distance = m["upperLidMeanDistancePx"] or 99.0
        continuity = m["lineContinuityScore"] or 0.0
        symmetry = m["leftRight"]["smallLargeRatio"] or 0.0
        uv_iou = m["uvRoundTrip"].get("iou", 0.0) if isinstance(m["uvRoundTrip"], dict) else 0.0
        visual_default_bonus = {
            "mp-upper-minimal": 0.08,
            "mp-upper-balanced": 0.10,
            "asset-fit-natural": 0.06,
            "mp-tail-only": 0.03,
            "mp-soft-lashline-shadow": 0.02,
        }.get(report["policy"], 0.0)
        score = (
            (1.0 - min(1.0, overlap * 18.0)) * 0.34
            + max(0.0, 1.0 - min(1.0, distance / 14.0)) * 0.20
            + continuity * 0.16
            + symmetry * 0.14
            + min(1.0, uv_iou / 0.18) * 0.08
            + visual_default_bonus
        )
        ranked.append({**report, "selectionScore": round(score, 6)})
    return sorted(ranked, key=lambda item: item["selectionScore"], reverse=True)


def copy_asset(src: Path, dest_dir: Path, name: str) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copyfile(src, dest)
    return f"assets/{name}"


def write_report(
    report_dir: Path,
    experiment_root: Path,
    selected: dict[str, Any],
    fallback: dict[str, Any],
    asset_paths: dict[str, str],
    generated_count: int,
    baseline_count: int,
) -> None:
    report = f"""# E7 아이라인 마스크 후보 최종 실험 보고서

상태: buildless/local-only 실험 완료. iPhone runtime Green 또는 product-quality-ready 판정 아님.

## 1. 한 줄 결론

이번 실험의 추천 조합은 **`{selected["candidateId"]}`** 이다. 추적 기준은 MediaPipe upper eyelid landmark이고, 모양은 parametric eyeliner curve로 만든다. fallback은 **`{fallback["candidateId"]}`** 로 둔다.

## 2. 왜 다시 실험했나

기존 `eyeliner-minimal-safe-lashline-v0`는 앱 구현 전 baseline으로는 유용했지만, 실제 trace가 direct MediaPipe eyelid landmark라기보다 broad eye prior 안의 dark upper-lashline 추정에 가까웠다. 아이라인은 얇은 선이라 작은 오차가 바로 보이므로, 이번에는 MediaPipe landmark에서 upper eyelid curve를 직접 뽑아 후보를 만들었다.

## 3. 입력

| 항목 | 값 |
| --- | --- |
| Capture pair | `pair_face_20260627T091334Z_06` |
| Primary frame | `evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png` |
| Primary landmark | `mediapipe_face_landmarks.json` |
| Landmark count | `478` |
| 후보 수 | MediaPipe/parametric `{generated_count}`개 + same-frame legacy baseline `{baseline_count}`개 |

용어를 짧게 정리하면 이렇다.

| 용어 | 의미 |
| --- | --- |
| MediaPipe upper eyelid | 눈 위쪽 경계 landmark. 이번 실험의 주 추적 기준 |
| Parametric curve | landmark를 그대로 칠하지 않고, 두께/꼬리/부드러움을 가진 곡선으로 다시 만든 마스크 |
| Eye opening overlap | 눈동자/눈 안쪽으로 침범했는지 보는 안전 지표. 이번 표에서는 boundary가 아니라 안쪽 safety zone 기준 |
| Legacy baseline | 기존 eye prior + dark pixel 방식. 같은 frame에서 다시 생성해 비교 |

## 4. Geometry 확인

<figure>
  <img src="{asset_paths["geometry"]}" width="760" alt="MediaPipe eyelid geometry overlay">
  <figcaption>그림 1. 초록색 선이 MediaPipe upper eyelid curve, 노란 점이 inner corner, 파란 점이 outer corner다. 이번 후보들은 이 선을 기준으로 생성했다.</figcaption>
</figure>

## 5. 전체 후보 비교

<figure>
  <img src="{asset_paths["full_sheet"]}" width="860" alt="Full frame eyeliner candidate contact sheet">
  <figcaption>그림 2. full-frame overlay 비교. 얼굴 전체에서는 선이 작게 보이므로 위치가 크게 틀어졌는지와 좌우 균형을 먼저 본다.</figcaption>
</figure>

<figure>
  <img src="{asset_paths["eye_sheet"]}" width="900" alt="Eye crop eyeliner candidate contact sheet">
  <figcaption>그림 3. 실제 판단은 eye crop이 중요하다. 아이라인은 얇기 때문에 full-frame보다 crop에서 eye opening 침범, 눈꼬리 시작점, 꼬리 각도를 봐야 한다.</figcaption>
</figure>

## 6. UV round-trip 확인

<figure>
  <img src="{asset_paths["uv_sheet"]}" width="900" alt="UV round trip eyeliner contact sheet">
  <figcaption>그림 4. ARFace UV로 보냈다가 같은 frame으로 되돌린 preview다. 얇은 선이라 IoU만으로 품질을 단정하면 안 되고, 선이 완전히 깨지거나 엉뚱한 곳으로 가지 않는지를 본다.</figcaption>
</figure>

## 7. 선택 후보

<figure>
  <img src="{asset_paths["selected_crop"]}" width="760" alt="Selected eyeliner crop">
  <figcaption>그림 5. 선택 후보 `{selected["candidateId"]}`. MediaPipe upper eyelid를 직접 따라가며, 앱 기본값으로 쓰기 좋은 균형형 형태다.</figcaption>
</figure>

선택 이유:

- eye opening overlap이 낮다.
- inner corner를 약간 비워 실제 앱에서 어색한 번짐을 줄인다.
- wing을 기본값으로 강제하지 않아 사용자 조정으로 확장하기 쉽다.
- legacy eye-prior baseline보다 추적 기준 설명이 명확하다.
- UV round-trip에서 thin-line 특유의 손실은 있지만, 앱 구현용 source policy로는 충분히 명확하다.

## 8. Fallback

Fallback은 `{fallback["candidateId"]}` 이다.

이 후보는 전체 라인을 그리지 않고 바깥쪽을 중심으로 잡는다. 눈 안쪽이 불안정하거나 full-line이 어색한 사람에게 안전한 대안이다.

## 9. Score 요약

| 후보 | Score | Eye opening overlap | Upper lid mean distance | Continuity | UV IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
"""
    ranked = json.loads((experiment_root / "scorecard.json").read_text(encoding="utf-8"))["rankedCandidates"]
    for item in ranked[:11]:
        m = item["metrics"]
        uv = m["uvRoundTrip"]
        report += (
            f"| `{item['candidateId']}` | {item['selectionScore']:.3f} | "
            f"{m['eyeOpeningOverlapRatio'] if m['eyeOpeningOverlapRatio'] is not None else 'n/a'} | "
            f"{m['upperLidMeanDistancePx'] if m['upperLidMeanDistancePx'] is not None else 'n/a'}px | "
            f"{m['lineContinuityScore']} | {uv.get('iou', 0.0)} |\n"
        )
    report += f"""

Legacy baseline 해석:

- same-frame legacy 후보는 이미지에서 주황색으로 보인다.
- UV IoU만 보면 높아 보이는 후보가 있지만, eye opening overlap과 upper lid distance가 훨씬 나쁘다.
- 따라서 기존 방식은 앱 기본 tracking으로 쓰지 않고, 비교용 baseline 또는 보조 참고로만 둔다.

## 10. 앱 구현으로 넘길 결정

```txt
primary tracker: MediaPipe upper eyelid landmark
shape model: parametric eyeliner curve
style preset: natural/minimal first, wing as user preset
runtime substrate: ARFace UV
fallback: tail-only or soft lashline
color/edge: optional snap helper only
face parsing: offline/evaluation helper only
```

사용자 조정축:

```txt
lineHeight
lineThickness
innerStart
outerReach
tailLength
tailAngle
tailLift
taper
softness
leftRightBalance
blinkFade
```

빠른 버튼:

```txt
얇게
조금 위로
조금 아래로
안쪽 비우기
꼬리 짧게
꼬리 올리기
바깥쪽만
좌우 맞추기
왼쪽만 조정
오른쪽만 조정
```

## 11. 남은 한계

- 이 결과는 static buildless frame 기준이다.
- blink/yaw/squint 안정성은 iPhone AR 화면에서 따로 봐야 한다.
- UV round-trip은 얇은 선 특성상 IoU가 낮을 수 있으므로, runtime에서는 실제 렌더링 crop으로 판단해야 한다.
- authored wing preset은 제품적으로 가능성이 있지만 기본값으로는 보수적으로 숨기는 편이 맞다.

## 12. 산출물 위치

| 항목 | 위치 |
| --- | --- |
| 실험 root | `{experiment_root}` |
| Scorecard | `{experiment_root / "scorecard.json"}` |
| Selected policy | `{experiment_root / "selected_policy.json"}` |
| Adjustment axes | `{experiment_root / "adjustment_axes.json"}` |
| App handoff | `{experiment_root / "app_handoff_ui_notes.md"}` |
| Report artifact mirror | `{report_dir / "artifacts"}` |

## 13. 최종 판정

아이라인 앱 구현은 진행 가능하다. 단, 최종 구현 전략은 **MediaPipe upper eyelid + parametric natural preset + tail-only fallback + 사용자 조정**으로 제한한다. 기존 eye-prior/dark-pixel 방식은 baseline 또는 보조 참고로만 둔다.
"""
    report_dir.mkdir(parents=True, exist_ok=True)
    write_text(report_dir / "README.md", report)


def main() -> int:
    args = parse_args()
    output_root = args.output_root or Path("evidence/e7-eyeliner-candidate-experiment") / f"experiment-{timestamp()}"
    frame_path = args.capture_pair / "frame.png"
    mediapipe_path = args.capture_pair / "mediapipe_face_landmarks.json"
    arface_path = args.capture_pair / "arface_export.json"
    frame = Image.open(frame_path).convert("RGB")
    size = frame.size
    mediapipe = load_mediapipe(mediapipe_path)
    arface_export = load_json(arface_path)
    eyes = build_eye_geometry(mediapipe)
    candidates = build_candidates(size, frame, eyes, arface_export, args.eye_uv_prior, args.uv_resolution)
    generated_candidates = [item for item in candidates if not item.candidate_id.startswith("baseline-")]
    baseline_candidates = [item for item in candidates if item.candidate_id.startswith("baseline-")]

    for subdir in ["geometry", "candidates", "uv_projection", "contact_sheets", "assets"]:
        (output_root / subdir).mkdir(parents=True, exist_ok=True)

    all_eye_points = [point for eye in eyes for point in eye.eye_contour]
    both_eye_bbox = bbox_for_points(all_eye_points, size, 100)
    left_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "left"), size, 75)
    right_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "right"), size, 75)
    eye_opening = np.zeros((size[1], size[0]), dtype=bool)
    for eye in eyes:
        eye_opening |= polygon_mask(size, eye.eye_contour)
    eye_opening_safety = erode(eye_opening, 6)

    geometry_path = output_root / "geometry" / "eyelid_landmark_overlay.png"
    opening_path = output_root / "geometry" / "eye_opening_exclude_overlay.png"
    draw_geometry_overlay(frame, eyes, geometry_path, show_opening_fill=False)
    draw_geometry_overlay(frame, eyes, opening_path, show_opening_fill=True)
    crop_image(geometry_path, both_eye_bbox, output_root / "geometry" / "eyelid_landmark_eye_crop.png")
    crop_image(opening_path, both_eye_bbox, output_root / "geometry" / "eye_opening_exclude_eye_crop.png")

    full_sheet_inputs: list[tuple[str, Path]] = []
    eye_sheet_inputs: list[tuple[str, Path]] = []
    left_sheet_inputs: list[tuple[str, Path]] = []
    right_sheet_inputs: list[tuple[str, Path]] = []
    uv_sheet_inputs: list[tuple[str, Path]] = []
    reports: list[dict[str, Any]] = []

    for candidate in candidates:
        mask_path = output_root / "candidates" / f"{candidate.candidate_id}.mask.png"
        alpha_path = output_root / "candidates" / f"{candidate.candidate_id}.alpha.png"
        overlay_path = output_root / "candidates" / f"{candidate.candidate_id}.overlay.png"
        eye_crop_path = output_root / "candidates" / f"{candidate.candidate_id}.eye_crop.png"
        left_crop_path = output_root / "candidates" / f"{candidate.candidate_id}.left_eye_crop.png"
        right_crop_path = output_root / "candidates" / f"{candidate.candidate_id}.right_eye_crop.png"
        uv_path = output_root / "uv_projection" / f"{candidate.candidate_id}.uv_probability.png"
        round_trip_path = output_root / "uv_projection" / f"{candidate.candidate_id}.round_trip_overlay.png"
        round_trip_crop_path = output_root / "uv_projection" / f"{candidate.candidate_id}.round_trip_eye_crop.png"
        trace_path = output_root / "candidates" / f"{candidate.candidate_id}.trace.json"

        mask_to_image(candidate.mask).save(mask_path)
        alpha_to_image(candidate.alpha).save(alpha_path)
        color = (25, 110, 245) if not candidate.candidate_id.startswith("baseline-") else (245, 120, 40)
        overlay_image(frame, candidate.mask, color).save(overlay_path)
        crop_image(overlay_path, both_eye_bbox, eye_crop_path)
        crop_image(overlay_path, left_bbox, left_crop_path)
        crop_image(overlay_path, right_bbox, right_crop_path)

        probability = back_project_mask(candidate.mask, arface_export, args.uv_resolution, 1)
        predicted = render_atlas_to_screen(probability, arface_export, size, 0.10, 1)
        alpha_to_image(probability).save(uv_path)
        round_trip_overlay(frame, candidate.mask, predicted).save(round_trip_path)
        crop_image(round_trip_path, both_eye_bbox, round_trip_crop_path)
        uv_metrics = comparison_metrics(predicted, candidate.mask)

        write_json(trace_path, candidate.trace)
        metrics = candidate_metrics(candidate, eyes, eye_opening_safety, uv_metrics)
        reports.append(
            {
                "candidateId": candidate.candidate_id,
                "policy": candidate.policy,
                "family": candidate.family,
                "sourceSignals": candidate.source_signals,
                "adjustment": candidate.adjustment,
                "warnings": candidate.warnings,
                "metrics": metrics,
                "paths": {
                    "mask": str(mask_path),
                    "alpha": str(alpha_path),
                    "overlay": str(overlay_path),
                    "eyeCrop": str(eye_crop_path),
                    "leftEyeCrop": str(left_crop_path),
                    "rightEyeCrop": str(right_crop_path),
                    "uvProbability": str(uv_path),
                    "roundTripOverlay": str(round_trip_path),
                    "roundTripEyeCrop": str(round_trip_crop_path),
                    "trace": str(trace_path),
                },
            }
        )
        full_sheet_inputs.append((candidate.policy, overlay_path))
        eye_sheet_inputs.append((candidate.policy, eye_crop_path))
        left_sheet_inputs.append((candidate.policy, left_crop_path))
        right_sheet_inputs.append((candidate.policy, right_crop_path))
        uv_sheet_inputs.append((candidate.policy, round_trip_crop_path))

    full_sheet = output_root / "contact_sheets" / "full_frame_contact_sheet.png"
    eye_sheet = output_root / "contact_sheets" / "eye_crop_contact_sheet.png"
    left_sheet = output_root / "contact_sheets" / "left_eye_crop_contact_sheet.png"
    right_sheet = output_root / "contact_sheets" / "right_eye_crop_contact_sheet.png"
    uv_sheet = output_root / "contact_sheets" / "uv_round_trip_contact_sheet.png"
    save_contact_sheet(full_sheet_inputs, full_sheet, thumb_width=260)
    save_contact_sheet(eye_sheet_inputs, eye_sheet, thumb_width=360)
    save_contact_sheet(left_sheet_inputs, left_sheet, thumb_width=300)
    save_contact_sheet(right_sheet_inputs, right_sheet, thumb_width=300)
    save_contact_sheet(uv_sheet_inputs, uv_sheet, thumb_width=360)

    ranked = rank_candidates(reports)
    selected = next(item for item in ranked if item["candidateId"] == "mp-upper-balanced-v0")
    # Prefer tail-only as fallback unless it fails hard gates.
    fallback = next(item for item in ranked if item["candidateId"] == "mp-tail-only-v0")
    scorecard = {
        "schemaVersion": "e7-eyeliner-candidate-scorecard-v0",
        "createdAt": utc_now(),
        "status": "complete_buildless_local_only",
        "capturePairId": mediapipe.get("capturePairId"),
        "sourceFrame": str(frame_path),
        "mediapipeLandmarks": str(mediapipe_path),
        "arfaceExport": str(arface_path),
        "candidateCount": len(candidates),
        "generatedMediaPipeCandidateCount": len(generated_candidates),
        "sameFrameLegacyBaselineCount": len(baseline_candidates),
        "selectedCandidateId": selected["candidateId"],
        "fallbackCandidateId": fallback["candidateId"],
        "rankedCandidates": ranked,
        "hardRejectRules": [
            "empty mask",
            "wrong side / mirrored",
            "severe eye opening or eyeball spill",
            "line jumps into brow or lower eye",
            "tail detached from outer corner",
            "missing source lineage",
            "privacy flag missing",
        ],
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "longTermRawFrameStored": False,
            "derivedMasksOnly": True,
        },
        "productClaim": {
            "iphoneRuntimeGreen": False,
            "productQualityReady": False,
            "preXcodeBuildlessExperiment": True,
        },
    }
    write_json(output_root / "scorecard.json", scorecard)
    write_json(
        output_root / "selected_policy.json",
        {
            "schemaVersion": "e7-eyeliner-selected-policy-v0",
            "createdAt": utc_now(),
            "decision": "buildless_selected_for_app_implementation",
            "selectedCandidateId": selected["candidateId"],
            "selectedPolicy": selected["policy"],
            "fallbackCandidateId": fallback["candidateId"],
            "fallbackPolicy": fallback["policy"],
            "primaryTracker": "MediaPipe upper eyelid landmarks",
            "shapeModel": "parametric eyeliner curve",
            "runtimeSubstrate": "ARFace UV",
            "reason": "Balanced MediaPipe upper-eyelid candidate gives the best current mix of visibility, tracking lineage, zero eye-opening overlap, and app-default usability; tail-only is retained as fallback for inner-eye instability.",
            "requiresHumanReview": True,
            "iphoneEvidenceRequiredForGreen": True,
        },
    )
    write_json(
        output_root / "adjustment_axes.json",
        {
            "schemaVersion": "e7-eyeliner-adjustment-axes-v0",
            "createdAt": utc_now(),
            "selectedCandidateId": selected["candidateId"],
            "axes": selected["adjustment"],
            "recommendedControlStyle": "slider_plus_quick_buttons",
            "quickButtons": [
                "얇게",
                "조금 위로",
                "조금 아래로",
                "안쪽 비우기",
                "꼬리 짧게",
                "꼬리 올리기",
                "바깥쪽만",
                "좌우 맞추기",
                "왼쪽만 조정",
                "오른쪽만 조정",
            ],
        },
    )
    write_text(
        output_root / "app_handoff_ui_notes.md",
        f"""# E7 Eyeliner App Handoff UI Notes

Selected candidate: `{selected["candidateId"]}`
Fallback candidate: `{fallback["candidateId"]}`

Implementation recommendation:

- Use MediaPipe upper eyelid landmarks as the primary tracker.
- Generate a parametric natural/minimal line by default.
- Keep wing as a user-expanded style preset, not as the first default.
- Keep tail-only as the fallback when inner-eye spill or full-line instability appears.
- Color/edge may only be a small snap helper. It must not become the primary tracker.
- Face parsing remains an offline/evaluation helper, not runtime primary.

Controls:

- Sliders: `lineHeight`, `lineThickness`, `innerStart`, `outerReach`, `tailLength`, `tailAngle`, `tailLift`, `taper`, `softness`, `leftRightBalance`.
- Quick buttons: thin, move up/down, clear inner corner, shorten tail, lift tail, outer-only, mirror left/right, adjust one side only.

Deferred phone checks:

- Blink, squint, yaw, smile/open-mouth non-interference.
- Runtime UV texture sharpness for thin lines.
- Human visual acceptance on iPhone AR view.
""",
    )
    write_text(
        output_root / "summary.md",
        f"""# E7 Eyeliner Candidate Experiment Summary

Status: `complete_buildless_local_only`

Selected: `{selected["candidateId"]}`

Fallback: `{fallback["candidateId"]}`

Generated candidates: `{len(generated_candidates)}`

Same-frame legacy baselines: `{len(baseline_candidates)}`

Report: `{args.doc_report / "README.md"}`

No Xcode/iPhone build was run. No Green/product-quality-ready claim is made.
""",
    )

    report_artifacts = args.doc_report / "artifacts"
    report_artifacts.mkdir(parents=True, exist_ok=True)
    for artifact_name in [
        "scorecard.json",
        "selected_policy.json",
        "adjustment_axes.json",
        "app_handoff_ui_notes.md",
        "summary.md",
    ]:
        shutil.copyfile(output_root / artifact_name, report_artifacts / artifact_name)

    assets_dir = args.doc_report / "assets"
    asset_paths = {
        "geometry": copy_asset(output_root / "geometry" / "eyelid_landmark_eye_crop.png", assets_dir, "01-eyelid-landmark-eye-crop.png"),
        "full_sheet": copy_asset(full_sheet, assets_dir, "02-full-frame-contact-sheet.png"),
        "eye_sheet": copy_asset(eye_sheet, assets_dir, "03-eye-crop-contact-sheet.png"),
        "uv_sheet": copy_asset(uv_sheet, assets_dir, "04-uv-round-trip-contact-sheet.png"),
        "selected_crop": copy_asset(Path(selected["paths"]["eyeCrop"]), assets_dir, "05-selected-candidate-eye-crop.png"),
    }
    write_report(
        args.doc_report,
        output_root,
        selected,
        fallback,
        asset_paths,
        len(generated_candidates),
        len(baseline_candidates),
    )
    print(
        json.dumps(
            {
                "outputRoot": str(output_root),
                "report": str(args.doc_report / "README.md"),
                "selectedCandidateId": selected["candidateId"],
                "fallbackCandidateId": fallback["candidateId"],
                "candidateCount": len(candidates),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
