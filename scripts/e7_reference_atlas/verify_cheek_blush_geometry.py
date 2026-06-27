#!/usr/bin/env python3
"""Verify E7 cheek blush placement geometry before real-device builds."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = ROOT / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/summary.json"
EXPECTED_SUMMARY_PATH = (
    ROOT
    / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/expected_render_20260627/summary.json"
)

LEFT_EYE_ANCHORS = (1086, 1099, 1107, 1186, 1190, 1193)
RIGHT_EYE_ANCHORS = (504, 1061, 1064, 1070, 1078, 1081)
NOSE_MIDLINE_ANCHORS = (7, 10, 14, 15, 21, 25, 28, 38)

MASK_BY_SHAPE = {
    "daily": "cheek-daily-mask-v1",
    "lovely": "cheek-lovely-mask-v1",
    "sun1": "cheek-sunkissed-mask1-v1",
    "sun2": "cheek-sunkissed-mask2-v1",
    "under": "cheek-under-eye-mask-v1",
}

ANCHOR_EXPECTATIONS = {
    "daily": {
        "anchor_suffix": "outer_high_cheekbone_peak",
        "x_range": (0.300, 0.370),
        "y_range": (0.140, 0.190),
        "description": "outer/high cheekbone peak",
    },
    "lovely": {
        "anchor_suffix": "apple_center_peak",
        "x_range": (0.275, 0.325),
        "y_range": (0.170, 0.220),
        "description": "apple cheek center peak",
    },
    "sun1": {
        "anchor_suffix": "sun_cheek_peak",
        "x_range": (0.365, 0.435),
        "y_range": (0.175, 0.225),
        "description": "cheek peak stronger than nose",
    },
    "sun2": {
        "anchor_suffix": "w_cheekbone_end_peak",
        "x_range": (0.360, 0.430),
        "y_range": (0.130, 0.185),
        "description": "W cheekbone end peak",
    },
    "under": {
        "anchor_suffix": "outer_undereye_high_cheek_peak",
        "x_range": (0.385, 0.455),
        "y_range": (0.090, 0.145),
        "description": "outer under-eye/high cheek peak",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, object]:
    require(path.exists(), f"Missing required JSON: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def percentile(values: list[float], percent: float) -> float:
    require(bool(values), "Cannot calculate percentile of empty values")
    sorted_values = sorted(values)
    scaled = clamp(percent, 0.0, 1.0) * (len(sorted_values) - 1)
    lower = int(scaled)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = scaled - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def average_points(vertices: list[list[float]], indices: tuple[int, ...]) -> tuple[float, float]:
    points = [vertices[index] for index in indices if 0 <= index < len(vertices)]
    require(bool(points), "ARFace topology anchors did not resolve")
    return (
        sum(float(point[0]) for point in points) / len(points),
        sum(float(point[1]) for point in points) / len(points),
    )


def calculate_metrics(summary: dict[str, object]) -> dict[str, float]:
    arface_path = ROOT / str(summary["arfaceExportPath"])
    arface = load_json(arface_path)
    vertices = arface["screenVertices"]
    require(isinstance(vertices, list) and len(vertices) >= 32, "ARFace screen vertices missing or too small")
    xs = [float(point[0]) for point in vertices]
    ys = [float(point[1]) for point in vertices]
    left = percentile(xs, 0.02)
    right = percentile(xs, 0.98)
    top = percentile(ys, 0.02)
    bottom = percentile(ys, 0.98)
    width = max(float(right - left), 1.0)
    height = max(float(bottom - top), 1.0)
    center_x = (float(left) + float(right)) * 0.5
    eye_line_y = float(top) + height * 0.331

    left_eye = average_points(vertices, LEFT_EYE_ANCHORS)
    right_eye = average_points(vertices, RIGHT_EYE_ANCHORS)
    eye_line_y = clamp((left_eye[1] + right_eye[1]) * 0.5, top + height * 0.180, top + height * 0.450)

    nose_midline = average_points(vertices, NOSE_MIDLINE_ANCHORS)
    center_x = clamp(nose_midline[0], left + width * 0.420, left + width * 0.580)
    return {
        "left": float(left),
        "right": float(right),
        "top": float(top),
        "bottom": float(bottom),
        "width": width,
        "height": height,
        "centerX": center_x,
        "eyeLineY": eye_line_y,
    }


def ratio_from_anchor(anchor: dict[str, object], metrics: dict[str, float], side: float) -> tuple[float, float]:
    x_ratio = side * (float(anchor["x"]) - metrics["centerX"]) / metrics["width"]
    y_ratio = (float(anchor["y"]) - metrics["eyeLineY"]) / metrics["height"]
    return x_ratio, y_ratio


def anchors_for(mask_summary: dict[str, object], suffix: str) -> dict[str, dict[str, object]]:
    anchors = mask_summary["faceAnchorSummary"]["anchors"]
    require(isinstance(anchors, list), "faceAnchorSummary.anchors must be a list")
    matched: dict[str, dict[str, object]] = {}
    for anchor in anchors:
        require(isinstance(anchor, dict), "anchor entries must be objects")
        name = str(anchor["name"])
        if not name.endswith(suffix):
            continue
        if name.startswith("left_"):
            matched["left"] = anchor
        elif name.startswith("right_"):
            matched["right"] = anchor
    require(set(matched) == {"left", "right"}, f"Missing left/right anchors for {suffix}")
    return matched


def verify_shape_anchor(
    shape: str,
    mask_summary: dict[str, object],
    metrics: dict[str, float],
) -> dict[str, object]:
    expectation = ANCHOR_EXPECTATIONS[shape]
    anchors = anchors_for(mask_summary, str(expectation["anchor_suffix"]))
    x_min, x_max = expectation["x_range"]
    y_min, y_max = expectation["y_range"]
    results: dict[str, object] = {}
    ratios: list[tuple[float, float]] = []
    for side_name, side in (("left", -1.0), ("right", 1.0)):
        x_ratio, y_ratio = ratio_from_anchor(anchors[side_name], metrics, side)
        require(
            x_min <= x_ratio <= x_max,
            f"{shape} {side_name} x ratio {x_ratio:.3f} outside {x_min:.3f}-{x_max:.3f}",
        )
        require(
            y_min <= y_ratio <= y_max,
            f"{shape} {side_name} y ratio {y_ratio:.3f} outside {y_min:.3f}-{y_max:.3f}",
        )
        ratios.append((x_ratio, y_ratio))
        results[side_name] = {
            "xRatioFromFaceCenter": round(x_ratio, 4),
            "yRatioFromEyeLine": round(y_ratio, 4),
        }

    require(
        abs(ratios[0][0] - ratios[1][0]) <= 0.045,
        f"{shape} left/right x symmetry drift is too large",
    )
    require(
        abs(ratios[0][1] - ratios[1][1]) <= 0.030,
        f"{shape} left/right y symmetry drift is too large",
    )
    return results


def verify_nose_connectors(summary: dict[str, object], metrics: dict[str, float]) -> dict[str, object]:
    results: dict[str, object] = {}
    for shape, name, y_range, max_strength in (
        ("sun1", "raised_low_density_nose_bridge_not_nostrils", (0.130, 0.185), 0.18),
        ("sun2", "low_density_raised_nose_bridge_connector", (0.120, 0.175), 0.22),
    ):
        mask_id = MASK_BY_SHAPE[shape]
        anchors = summary["masks"][mask_id]["faceAnchorSummary"]["anchors"]
        nose_anchor = next((item for item in anchors if item["name"] == name), None)
        require(nose_anchor is not None, f"{shape} missing nose connector anchor")
        center_offset = abs(float(nose_anchor["x"]) - metrics["centerX"]) / metrics["width"]
        y_ratio = (float(nose_anchor["y"]) - metrics["eyeLineY"]) / metrics["height"]
        strength = float(nose_anchor["strength"])
        require(center_offset <= 0.030, f"{shape} nose connector is off center: {center_offset:.3f}")
        require(y_range[0] <= y_ratio <= y_range[1], f"{shape} nose connector y ratio {y_ratio:.3f} outside range")
        require(strength <= max_strength, f"{shape} nose connector density cap too strong: {strength:.3f}")
        results[shape] = {
            "centerOffsetRatio": round(center_offset, 4),
            "yRatioFromEyeLine": round(y_ratio, 4),
            "densityCap": round(strength, 4),
        }
    return results


def verify_preview_rows(expected_summary: dict[str, object]) -> dict[str, int]:
    rows = expected_summary["rows"]
    require(isinstance(rows, list) and len(rows) == 5, "Expected render must include exactly five rows")
    pixels = {str(row["textureSample"]): int(row["projectedAlphaActivePixelsGt003"]) for row in rows}
    require(
        pixels["blush_sunkissed2"] > pixels["blush_daily"] * 0.75,
        "Sun2 projected alpha should preserve the broad W template",
    )
    require(
        pixels["blush_sunkissed1"] > pixels["blush_lovely"],
        "Sun1 should include cheek spots plus a low-density nose connector",
    )
    require(
        pixels["blush_under_eye"] < pixels["blush_sunkissed1"],
        "Under-eye should not be broader than sun-kissed cheek+nose",
    )
    return pixels


def main() -> None:
    summary = load_json(SUMMARY_PATH)
    expected_summary = load_json(EXPECTED_SUMMARY_PATH)
    metrics = calculate_metrics(summary)
    shape_results: dict[str, object] = {}
    for shape, mask_id in MASK_BY_SHAPE.items():
        mask_summary = summary["masks"][mask_id]
        face_summary = mask_summary["faceAnchorSummary"]
        require(face_summary["usedTopologyEyeAnchors"] is True, f"{mask_id} must use topology eye anchors")
        require(face_summary["usedTopologyNoseMidline"] is True, f"{mask_id} must use topology nose anchors")
        shape_results[shape] = verify_shape_anchor(shape, mask_summary, metrics)

    output = {
        "status": "ok",
        "metrics": {key: round(value, 4) for key, value in metrics.items()},
        "shapeAnchors": shape_results,
        "noseConnectors": verify_nose_connectors(summary, metrics),
        "projectedAlphaPixels": verify_preview_rows(expected_summary),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
