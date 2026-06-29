#!/usr/bin/env python3
"""Generate E7 eyeliner v2 samples from team feedback.

This is a buildless/local-only visual sampling tool. It reuses the already
captured frame and MediaPipe landmarks, narrows the candidate families to
cat/winged/puppy, and emphasizes longer tails plus outer canthus fill.
It does not run live MediaPipe, upload data, build Xcode, or touch an iPhone.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import unicodedata
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.e7_eyeliner_candidate_experiment.run_eyeliner_candidate_experiment import (
    Candidate,
    EyeGeometry,
    bbox_for_points,
    build_eye_geometry,
    build_parametric_candidate,
    candidate_metrics,
    crop_image,
    draw_geometry_overlay,
    eye_width,
    polygon_mask,
)
from scripts.e7_region_generate.build_region_candidates import (
    alpha_to_image,
    back_project_mask,
    comparison_metrics,
    mask_to_image,
    render_atlas_to_screen,
    round_trip_overlay,
    soft_alpha,
    write_json,
    write_text,
)


DEFAULT_CAPTURE_PAIR = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06")
DEFAULT_OUTPUT_ROOT = Path("evidence/e7-eyeliner-team-feedback-samples")
DEFAULT_DOC_REPORT = Path("docs/product/e7-eyeliner-team-feedback-samples-2026-06-29")
DEFAULT_FEEDBACK_SKETCH = Path("/Users/wiseungcheol/Downloads/제목 없음 - 2026년 6월 28일 01.28.25.png")
UV_RESOLUTION = 512
FAMILIES = ("cat", "winged", "puppy")

FAMILY_COLORS = {
    "cat": (16, 14, 13),
    "winged": (18, 17, 16),
    "puppy": (62, 46, 38),
}

HIGH_CONTRAST_COLORS = {
    "cat": (0, 232, 255),
    "winged": (255, 52, 190),
    "puppy": (255, 184, 48),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run E7 eyeliner team feedback v2 sample generation.")
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--doc-report", type=Path, default=DEFAULT_DOC_REPORT)
    parser.add_argument("--feedback-sketch", type=Path, default=DEFAULT_FEEDBACK_SKETCH)
    parser.add_argument("--uv-resolution", type=int, default=UV_RESOLUTION)
    parser.add_argument("--with-uv", action="store_true", help="Also compute representative ARFace UV round-trip sanity images.")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def lerp_point(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    return (a[0] * (1.0 - t) + b[0] * t, a[1] * (1.0 - t) + b[1] * t)


def slug(value: float, scale: int = 100) -> int:
    return int(round(abs(value) * scale))


def eye_opening_mask(size: tuple[int, int], eyes: list[EyeGeometry]) -> np.ndarray:
    mask = np.zeros((size[1], size[0]), dtype=bool)
    for eye in eyes:
        mask |= polygon_mask(size, eye.eye_contour)
    return mask


def family_specs() -> list[dict[str, Any]]:
    raw: dict[str, list[dict[str, float]]] = {
        "cat": [
            {"tailLength": 0.26, "tailAngle": -24, "tailLift": -2.0, "outerCornerFill": 0.32, "lineThickness": 6.2, "innerStart": 0.20, "lineHeight": -5.4, "taper": 1.20, "softness": 2.8, "outerLift": -3.0},
            {"tailLength": 0.30, "tailAngle": -26, "tailLift": -2.5, "outerCornerFill": 0.34, "lineThickness": 6.6, "innerStart": 0.22, "lineHeight": -5.2, "taper": 1.30, "softness": 3.0, "outerLift": -3.4},
            {"tailLength": 0.34, "tailAngle": -28, "tailLift": -3.0, "outerCornerFill": 0.36, "lineThickness": 6.8, "innerStart": 0.24, "lineHeight": -5.0, "taper": 1.38, "softness": 3.0, "outerLift": -3.8},
            {"tailLength": 0.38, "tailAngle": -30, "tailLift": -3.8, "outerCornerFill": 0.38, "lineThickness": 7.2, "innerStart": 0.22, "lineHeight": -5.0, "taper": 1.48, "softness": 3.2, "outerLift": -4.2},
            {"tailLength": 0.42, "tailAngle": -32, "tailLift": -4.4, "outerCornerFill": 0.40, "lineThickness": 7.6, "innerStart": 0.24, "lineHeight": -4.8, "taper": 1.58, "softness": 3.2, "outerLift": -4.6},
            {"tailLength": 0.32, "tailAngle": -34, "tailLift": -4.0, "outerCornerFill": 0.42, "lineThickness": 7.0, "innerStart": 0.28, "lineHeight": -4.8, "taper": 1.45, "softness": 3.4, "outerLift": -4.8},
            {"tailLength": 0.36, "tailAngle": -36, "tailLift": -4.8, "outerCornerFill": 0.44, "lineThickness": 7.8, "innerStart": 0.28, "lineHeight": -4.6, "taper": 1.64, "softness": 3.5, "outerLift": -5.0},
            {"tailLength": 0.28, "tailAngle": -30, "tailLift": -3.2, "outerCornerFill": 0.46, "lineThickness": 7.4, "innerStart": 0.18, "lineHeight": -4.9, "taper": 1.34, "softness": 3.2, "outerLift": -4.2},
            {"tailLength": 0.40, "tailAngle": -28, "tailLift": -3.2, "outerCornerFill": 0.36, "lineThickness": 6.4, "innerStart": 0.26, "lineHeight": -5.4, "taper": 1.70, "softness": 2.8, "outerLift": -4.0},
            {"tailLength": 0.44, "tailAngle": -34, "tailLift": -5.0, "outerCornerFill": 0.48, "lineThickness": 8.0, "innerStart": 0.30, "lineHeight": -4.6, "taper": 1.72, "softness": 3.6, "outerLift": -5.4},
        ],
        "winged": [
            {"tailLength": 0.26, "tailAngle": -2, "tailLift": -0.4, "outerCornerFill": 0.32, "lineThickness": 6.0, "innerStart": 0.20, "lineHeight": -5.2, "taper": 1.10, "softness": 2.9, "outerLift": -2.8},
            {"tailLength": 0.30, "tailAngle": -1, "tailLift": -0.3, "outerCornerFill": 0.34, "lineThickness": 6.4, "innerStart": 0.22, "lineHeight": -5.0, "taper": 1.18, "softness": 3.0, "outerLift": -3.0},
            {"tailLength": 0.34, "tailAngle": 0, "tailLift": 0.0, "outerCornerFill": 0.36, "lineThickness": 6.8, "innerStart": 0.24, "lineHeight": -4.8, "taper": 1.28, "softness": 3.1, "outerLift": -3.2},
            {"tailLength": 0.38, "tailAngle": 1, "tailLift": 0.2, "outerCornerFill": 0.38, "lineThickness": 7.0, "innerStart": 0.22, "lineHeight": -4.8, "taper": 1.38, "softness": 3.2, "outerLift": -3.2},
            {"tailLength": 0.42, "tailAngle": 2, "tailLift": 0.4, "outerCornerFill": 0.40, "lineThickness": 7.4, "innerStart": 0.24, "lineHeight": -4.6, "taper": 1.46, "softness": 3.3, "outerLift": -3.4},
            {"tailLength": 0.32, "tailAngle": 0, "tailLift": -0.2, "outerCornerFill": 0.44, "lineThickness": 7.2, "innerStart": 0.28, "lineHeight": -4.6, "taper": 1.34, "softness": 3.4, "outerLift": -3.6},
            {"tailLength": 0.36, "tailAngle": -3, "tailLift": -0.6, "outerCornerFill": 0.42, "lineThickness": 7.8, "innerStart": 0.28, "lineHeight": -4.7, "taper": 1.52, "softness": 3.0, "outerLift": -3.6},
            {"tailLength": 0.44, "tailAngle": 0, "tailLift": 0.0, "outerCornerFill": 0.46, "lineThickness": 7.6, "innerStart": 0.26, "lineHeight": -4.8, "taper": 1.62, "softness": 3.4, "outerLift": -3.8},
            {"tailLength": 0.40, "tailAngle": 3, "tailLift": 0.5, "outerCornerFill": 0.48, "lineThickness": 8.0, "innerStart": 0.30, "lineHeight": -4.5, "taper": 1.54, "softness": 3.5, "outerLift": -3.8},
            {"tailLength": 0.46, "tailAngle": 1, "tailLift": 0.3, "outerCornerFill": 0.50, "lineThickness": 8.2, "innerStart": 0.30, "lineHeight": -4.5, "taper": 1.72, "softness": 3.7, "outerLift": -4.0},
        ],
        "puppy": [
            {"tailLength": 0.22, "tailAngle": 8, "tailLift": 1.0, "outerCornerFill": 0.28, "lineThickness": 5.8, "innerStart": 0.22, "lineHeight": -4.4, "taper": 0.90, "softness": 3.8, "outerLift": -1.2},
            {"tailLength": 0.26, "tailAngle": 10, "tailLift": 1.2, "outerCornerFill": 0.30, "lineThickness": 6.0, "innerStart": 0.24, "lineHeight": -4.2, "taper": 0.96, "softness": 4.0, "outerLift": -1.0},
            {"tailLength": 0.30, "tailAngle": 12, "tailLift": 1.5, "outerCornerFill": 0.32, "lineThickness": 6.3, "innerStart": 0.26, "lineHeight": -4.0, "taper": 1.02, "softness": 4.2, "outerLift": -0.8},
            {"tailLength": 0.34, "tailAngle": 14, "tailLift": 1.9, "outerCornerFill": 0.34, "lineThickness": 6.5, "innerStart": 0.28, "lineHeight": -3.9, "taper": 1.08, "softness": 4.4, "outerLift": -0.4},
            {"tailLength": 0.38, "tailAngle": 16, "tailLift": 2.3, "outerCornerFill": 0.36, "lineThickness": 6.8, "innerStart": 0.30, "lineHeight": -3.8, "taper": 1.14, "softness": 4.6, "outerLift": -0.2},
            {"tailLength": 0.28, "tailAngle": 18, "tailLift": 2.5, "outerCornerFill": 0.38, "lineThickness": 7.0, "innerStart": 0.24, "lineHeight": -3.7, "taper": 1.00, "softness": 4.6, "outerLift": 0.0},
            {"tailLength": 0.32, "tailAngle": 20, "tailLift": 3.0, "outerCornerFill": 0.40, "lineThickness": 7.2, "innerStart": 0.26, "lineHeight": -3.6, "taper": 1.08, "softness": 4.8, "outerLift": 0.2},
            {"tailLength": 0.36, "tailAngle": 16, "tailLift": 2.6, "outerCornerFill": 0.42, "lineThickness": 7.4, "innerStart": 0.28, "lineHeight": -3.5, "taper": 1.18, "softness": 4.8, "outerLift": 0.2},
            {"tailLength": 0.40, "tailAngle": 18, "tailLift": 3.2, "outerCornerFill": 0.44, "lineThickness": 7.6, "innerStart": 0.30, "lineHeight": -3.5, "taper": 1.24, "softness": 5.0, "outerLift": 0.4},
            {"tailLength": 0.42, "tailAngle": 20, "tailLift": 3.5, "outerCornerFill": 0.46, "lineThickness": 7.8, "innerStart": 0.32, "lineHeight": -3.4, "taper": 1.30, "softness": 5.2, "outerLift": 0.6},
        ],
    }

    specs: list[dict[str, Any]] = []
    serial = 1
    for family in FAMILIES:
        for idx, params in enumerate(raw[family], start=1):
            candidate_id = (
                f"team-v2-{family}-{idx:02d}"
                f"-tail{slug(params['tailLength']):02d}"
                f"-angle{slug(params['tailAngle'], 1):02d}"
                f"-fill{slug(params['outerCornerFill']):02d}"
            )
            specs.append(
                {
                    **params,
                    "family": family,
                    "familyIndex": idx,
                    "candidateIndex": serial,
                    "candidateId": candidate_id,
                    "outerReach": 1.0,
                    "style": {
                        "cat": "lifted_long_tail_outer_canthus_fill",
                        "winged": "horizontal_long_tail_outer_canthus_fill",
                        "puppy": "downturned_long_tail_outer_canthus_fill",
                    }[family],
                    "previewOpacity": 0.82 if family != "puppy" else 0.72,
                }
            )
            serial += 1
    return specs


def outer_canthus_allow_mask(size: tuple[int, int], eyes: list[EyeGeometry], reach: float) -> np.ndarray:
    allow = Image.new("L", size, 0)
    draw = ImageDraw.Draw(allow)
    for eye in eyes:
        contour = eye.eye_contour
        width = eye_width(eye)
        height = max(1.0, max(p[1] for p in contour) - min(p[1] for p in contour))
        outer = eye.outer_corner
        rx = width * (0.12 + reach * 0.18)
        ry = height * 0.80
        draw.ellipse((outer[0] - rx, outer[1] - ry, outer[0] + rx, outer[1] + ry), fill=255)
    return np.asarray(allow) > 0


def add_outer_canthus_fill_v2(
    candidate: Candidate,
    size: tuple[int, int],
    eyes: list[EyeGeometry],
    spec: dict[str, Any],
    opening: np.ndarray,
) -> Candidate:
    fill_img = Image.new("L", size, 0)
    draw = ImageDraw.Draw(fill_img)
    fill_strength = float(spec["outerCornerFill"])
    thickness = float(spec["lineThickness"])
    for eye in eyes:
        trace_eye = candidate.trace.get("lineTraces", {}).get(eye.side, {})
        centerline = [(float(item["x"]), float(item["y"])) for item in trace_eye.get("centerline", [])]
        if not centerline:
            continue
        tail_start = centerline[-1]
        tail_end_item = trace_eye.get("tailEnd")
        tail_end = (
            (float(tail_end_item["x"]), float(tail_end_item["y"]))
            if tail_end_item
            else tail_start
        )
        contour = eye.eye_contour
        outer = eye.outer_corner
        lower_near = contour[2] if len(contour) > 2 else lerp_point(outer, eye.inner_corner, 0.14)
        upper_near = centerline[max(0, int(len(centerline) * 0.84) - 1)]
        tail_mid = lerp_point(tail_start, tail_end, 0.38 + fill_strength * 0.20)
        lower_bridge = lerp_point(outer, lower_near, min(0.92, 0.46 + fill_strength * 0.75))
        upper_bridge = lerp_point(outer, upper_near, min(0.88, 0.36 + fill_strength * 0.70))
        tail_lower = (tail_mid[0], tail_mid[1] + thickness * (0.34 + fill_strength * 0.85))
        outer_soft_lower = (outer[0], outer[1] + thickness * (0.24 + fill_strength * 0.45))
        polygon = [upper_bridge, tail_start, tail_mid, tail_lower, lower_bridge, outer_soft_lower, outer]
        draw.polygon(polygon, fill=255)
        r_x = max(2.0, eye_width(eye) * (0.018 + fill_strength * 0.045))
        r_y = max(2.0, thickness * (0.7 + fill_strength * 1.2))
        draw.ellipse((outer[0] - r_x, outer[1] - r_y, outer[0] + r_x, outer[1] + r_y), fill=255)
        draw.line([upper_bridge, tail_mid], fill=255, width=max(1, int(round(thickness * 0.55))), joint="curve")

    fill = np.asarray(fill_img.filter(ImageFilter.GaussianBlur(radius=max(0.4, float(spec["softness"]) * 0.16)))) > 5
    protected_opening = opening & ~outer_canthus_allow_mask(size, eyes, fill_strength)
    combined = (candidate.mask | fill) & ~protected_opening
    trace = dict(candidate.trace)
    trace["outerCanthusFillV2"] = {
        "enabled": True,
        "fillStrength": fill_strength,
        "allowsOuterOpeningPatch": True,
        "protectedCentralEyeOpening": True,
        "rationale": "fill the small outer canthus V notch while preserving central eye opening",
    }
    adjustment = dict(candidate.adjustment)
    adjustment.update(
        {
            "outerCornerFill": fill_strength,
            "outerCanthusFill": fill_strength,
            "outerCanthusPatch": 1.0,
            "previewOpacity": float(spec["previewOpacity"]),
        }
    )
    warnings = [
        *candidate.warnings,
        "team feedback v2: longer tail and outer canthus fill emphasized",
        "outer canthus fill intentionally allows a small outer-eye patch; central eye opening remains protected",
    ]
    return replace(candidate, mask=combined, alpha=soft_alpha(combined, float(spec["softness"])), trace=trace, adjustment=adjustment, warnings=warnings)


def build_candidate(
    size: tuple[int, int],
    frame: Image.Image,
    eyes: list[EyeGeometry],
    opening: np.ndarray,
    spec: dict[str, Any],
) -> Candidate:
    candidate = build_parametric_candidate(
        size,
        frame,
        eyes,
        spec["candidateId"],
        f"team-feedback-v2-{spec['family']}",
        f"team_feedback_v2_{spec['family']}",
        float(spec["innerStart"]),
        float(spec["outerReach"]),
        float(spec["lineHeight"]),
        float(spec["lineThickness"]),
        float(spec["tailLength"]),
        float(spec["tailAngle"]),
        float(spec["tailLift"]),
        float(spec["taper"]),
        float(spec["softness"]),
        True,
        edge_snap=False,
        outer_lift=float(spec["outerLift"]),
        warnings=["buildless static frame only; blink/yaw iPhone test deferred"],
    )
    candidate = add_outer_canthus_fill_v2(candidate, size, eyes, spec, opening)
    trace = dict(candidate.trace)
    trace.update(
        {
            "family": spec["family"],
            "styleTaxonomy": spec["style"],
            "candidateIndex": spec["candidateIndex"],
            "familyIndex": spec["familyIndex"],
            "teamFeedback": {
                "keepFamilies": list(FAMILIES),
                "longerTail": True,
                "catDirection": "up",
                "wingedDirection": "horizontal",
                "puppyDirection": "down",
                "outerCanthusMustBeFilled": True,
            },
        }
    )
    return replace(candidate, trace=trace)


def cosmetic_overlay(frame: Image.Image, alpha: np.ndarray, color: tuple[int, int, int], opacity: float) -> Image.Image:
    base = frame.convert("RGB")
    overlay = Image.new("RGB", base.size, color)
    mask = np.rint(np.clip(alpha * opacity, 0, 1) * 255).astype(np.uint8)
    return Image.composite(overlay, base, Image.fromarray(mask, mode="L")).convert("RGB")


def high_contrast_overlay(frame: Image.Image, mask: np.ndarray, family: str) -> Image.Image:
    base = frame.convert("RGB")
    hard = mask_to_image(mask)
    halo = hard.filter(ImageFilter.MaxFilter(9))
    shadow = hard.filter(ImageFilter.MaxFilter(13))
    out = Image.composite(Image.new("RGB", base.size, (0, 0, 0)), base, shadow.point(lambda p: int(p * 0.24)))
    out = Image.composite(Image.new("RGB", base.size, (255, 255, 255)), out, halo.point(lambda p: int(p * 0.90)))
    out = Image.composite(Image.new("RGB", base.size, HIGH_CONTRAST_COLORS[family]), out, hard.point(lambda p: int(p * 0.96)))
    return out.convert("RGB")


def save_contact_sheet(
    items: list[tuple[str, Path]],
    output: Path,
    thumb_width: int = 280,
    cols: int = 5,
    label_height: int = 42,
) -> None:
    tiles: list[Image.Image] = []
    for label, path in items:
        img = Image.open(path).convert("RGB")
        ratio = thumb_width / img.width
        thumb = img.resize((thumb_width, max(1, round(img.height * ratio))), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb.width, thumb.height + label_height), "white")
        ImageDraw.Draw(tile).text((8, 5), label[:54], fill=(0, 0, 0))
        tile.paste(thumb, (0, label_height))
        tiles.append(tile)
    if not tiles:
        return
    cols = max(1, min(cols, len(tiles)))
    rows = math.ceil(len(tiles) / cols)
    cell_w = max(tile.width for tile in tiles)
    cell_h = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "white")
    for idx, tile in enumerate(tiles):
        sheet.paste(tile, ((idx % cols) * cell_w, (idx // cols) * cell_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def family_direction_ok(family: str, angle: float) -> bool:
    if family == "cat":
        return angle < -18
    if family == "winged":
        return -4 <= angle <= 4
    if family == "puppy":
        return angle > 6
    return False


def resolve_feedback_sketch(path: Path) -> Path:
    if path.exists():
        return path
    downloads = Path("/Users/wiseungcheol/Downloads")
    if not downloads.exists():
        return path
    target = unicodedata.normalize("NFC", path.name)
    for candidate in downloads.glob("*.png"):
        if unicodedata.normalize("NFC", candidate.name) == target:
            return candidate
    matches = list(downloads.glob("*2026*6*28*01.28.25*.png"))
    return matches[0] if matches else path


def build_report(
    report_dir: Path,
    output_root: Path,
    assets: dict[str, str],
    scorecard: dict[str, Any],
    shortlist: dict[str, Any],
) -> None:
    rows = "\n".join(
        f"| `{item['candidateId']}` | {item['familyKey']} | {item['adjustment']['tailLength']:.2f} | "
        f"{item['adjustment']['tailAngle']:.0f} | {item['adjustment']['outerCanthusFill']:.2f} | "
        f"{item['metrics']['eyeOpeningOverlapRatio']:.4f} |"
        for item in shortlist["reviewCandidates"]
    )
    if scorecard.get("uvRoundTripComputedCandidateIds"):
        uv_section = f"""## 5. UV round-trip sanity

상위/대표 9개만 ARFace UV round-trip sanity를 계산했다. 이 이미지는 제품 품질 증명이 아니라, UV 투영 시 큰 위치 이탈이 있는지만 보는 보조 자료다.

<figure>
  <img src="{assets['uvRoundTrip']}" width="1200" alt="UV round trip representative samples">
  <figcaption>그림 10. family별 대표 9개 UV round-trip crop.</figcaption>
</figure>
"""
    else:
        uv_section = """## 5. UV round-trip sanity

이번 빠른 v2 샘플은 shape 선택이 목적이라 기본 실행에서는 UV round-trip을 생략했다. 후보가 좁혀지면 선택 후보만 `--with-uv`로 다시 계산하는 편이 빠르고 낫다.
"""

    report = f"""# E7 아이라인 팀원 피드백 v2 샘플 보고서

상태: `pending_user_visual_pick`  
판정: buildless/local-only 샘플 생성 완료. iPhone runtime Green 또는 product-quality-ready 판정 아님.

## 1. 한 줄 결론

팀원 피드백에 맞춰 아이라인 후보를 `cat`, `winged`, `puppy` 세 family로 줄이고, 각 family마다 **10개씩 총 30개**를 새로 만들었다.

이번 v2는 기존 후보보다 아래 세 가지를 더 강하게 반영한다.

- 눈꼬리 tail을 더 길게 뺀다.
- `cat`은 위로, `winged`는 거의 수평, `puppy`는 아래로 내려가게 한다.
- 외안각의 작은 파인 V자 홈을 별도 `outerCanthusFill` polygon으로 채운다.

## 2. 입력과 원칙

| 항목 | 값 |
| --- | --- |
| Capture pair | `{scorecard['capturePairId']}` |
| Frame | `{scorecard['sourceFrame']}` |
| Landmark | `{scorecard['mediapipeLandmarks']}` |
| 후보 수 | `cat=10`, `winged=10`, `puppy=10` |
| 실험 성격 | 같은 프레임 기반 buildless/local-only visual sample |

<figure>
  <img src="{assets['feedbackSketch']}" width="900" alt="Team feedback sketch">
  <figcaption>그림 1. 팀원 피드백 스케치. v2에서는 family를 3개로 줄이고 tail 방향과 외안각 채움을 명시적으로 분리했다.</figcaption>
</figure>

## 3. 전체 샘플

아래 검은색 시트는 실제 제품색에 가까운 보기다.

<figure>
  <img src="{assets['allProduct']}" width="1500" alt="All 30 eyeliner v2 product samples">
  <figcaption>그림 2. 전체 30개 제품색 preview. family별 10개씩이며 candidate ID로 선택하면 된다.</figcaption>
</figure>

아래 고대비 시트는 shape 선택용이다. 제품색이 아니라 tail 길이, 방향, 외안각 채움 차이를 보기 위한 debug preview다.

<figure>
  <img src="{assets['allHighContrast']}" width="1500" alt="All 30 eyeliner v2 high contrast samples">
  <figcaption>그림 3. 전체 30개 고대비 preview. 속눈썹/그림자에 검은 선이 묻히는 문제를 피하기 위한 선택용 보기다.</figcaption>
</figure>

## 4. Family별 샘플

### 4.1 Cat

<figure>
  <img src="{assets['catProduct']}" width="1500" alt="Cat eyeliner v2 product samples">
  <figcaption>그림 4. Cat 10개. 눈꼬리가 위로 올라가는 방향을 강하게 반영했다.</figcaption>
</figure>

<figure>
  <img src="{assets['catHighContrast']}" width="1500" alt="Cat eyeliner v2 high contrast samples">
  <figcaption>그림 5. Cat 고대비 view. tail 상승각과 외안각 채움 정도를 우선 본다.</figcaption>
</figure>

### 4.2 Winged

<figure>
  <img src="{assets['wingedProduct']}" width="1500" alt="Winged eyeliner v2 product samples">
  <figcaption>그림 6. Winged 10개. 눈꼬리를 길게 빼되 수평에 가깝게 유지했다.</figcaption>
</figure>

<figure>
  <img src="{assets['wingedHighContrast']}" width="1500" alt="Winged eyeliner v2 high contrast samples">
  <figcaption>그림 7. Winged 고대비 view. 너무 위로 들리거나 아래로 떨어지는 후보를 걸러낸다.</figcaption>
</figure>

### 4.3 Puppy

<figure>
  <img src="{assets['puppyProduct']}" width="1500" alt="Puppy eyeliner v2 product samples">
  <figcaption>그림 8. Puppy 10개. tail이 아래로 내려가도록 만든 후보군이다.</figcaption>
</figure>

<figure>
  <img src="{assets['puppyHighContrast']}" width="1500" alt="Puppy eyeliner v2 high contrast samples">
  <figcaption>그림 9. Puppy 고대비 view. 내려가는 방향이 충분한지, 처져 보이는 정도가 과한지 확인한다.</figcaption>
</figure>

{uv_section}

## 6. 후보 표

외안각을 채우기 위해 outer eye opening 일부 overlap은 의도적으로 허용했다. 아래 overlap 값은 중앙 눈동자 침범 판정이 아니라, 외안각 patch를 포함한 참고값이다.

| 후보 ID | Family | Tail length | Tail angle | 외안각 채움 | 허용 outer overlap |
| --- | --- | ---: | ---: | ---: | ---: |
{rows}

## 7. 고르는 법

아래처럼 candidate ID로 골라주면 된다.

```txt
1순위: team-v2-winged-08-tail44-angle00-fill46
2순위: team-v2-cat-05-tail42-angle32-fill40
방향: winged는 좋은데 tail 10% 짧게, 외안각 채움은 유지
```

## 8. 한계

- 한 프레임 buildless 샘플이다.
- blink/yaw/squint, 실기기 AR attachment, FPS/latency/memory/thermal은 아직 검증하지 않았다.
- 외안각 채움은 의도적으로 outer eye opening 일부를 허용하므로, 실제 iPhone에서는 blink와 좌우 yaw에서 과한지 다시 봐야 한다.
- 최종 family/default preset은 사용자 visual pick 이후 확정한다.

## 9. 산출물 위치

| 항목 | 위치 |
| --- | --- |
| 실험 root | `{output_root}` |
| scorecard | `{output_root / 'scorecard.json'}` |
| shortlist | `{output_root / 'shortlist.json'}` |
| report artifact mirror | `{report_dir / 'artifacts'}` |
"""
    write_text(report_dir / "README.md", report)


def copy_asset(src: Path, dest_dir: Path, name: str) -> str:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name
    shutil.copyfile(src, dest)
    return f"assets/{name}"


def main() -> None:
    args = parse_args()
    feedback_sketch = resolve_feedback_sketch(args.feedback_sketch)
    run_id = f"experiment-{timestamp()}"
    output_root = args.output_root or DEFAULT_OUTPUT_ROOT / run_id
    output_root.mkdir(parents=True, exist_ok=True)
    report_assets = args.doc_report / "assets"
    report_artifacts = args.doc_report / "artifacts"
    report_assets.mkdir(parents=True, exist_ok=True)
    report_artifacts.mkdir(parents=True, exist_ok=True)

    frame_path = args.capture_pair / "frame.png"
    mediapipe_path = args.capture_pair / "mediapipe_face_landmarks.json"
    arface_path = args.capture_pair / "arface_export.json"
    frame = Image.open(frame_path).convert("RGB")
    size = frame.size
    mediapipe = load_json(mediapipe_path)
    arface_export = load_json(arface_path)
    eyes = build_eye_geometry(mediapipe)
    opening = eye_opening_mask(size, eyes)
    both_bbox = bbox_for_points([point for eye in eyes for point in eye.eye_contour], size, 118)
    left_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "left"), size, 80)
    right_bbox = bbox_for_points(next(eye.eye_contour for eye in eyes if eye.side == "right"), size, 80)

    geometry_path = output_root / "geometry" / "eyelid_and_canthus_anchor.png"
    geometry_crop = output_root / "geometry" / "eyelid_and_canthus_anchor_crop.png"
    draw_geometry_overlay(frame, eyes, geometry_path, show_opening_fill=True)
    crop_image(geometry_path, both_bbox, geometry_crop)

    specs = family_specs()
    reports: list[dict[str, Any]] = []
    product_inputs: list[tuple[str, Path]] = []
    high_inputs: list[tuple[str, Path]] = []
    product_by_family: dict[str, list[tuple[str, Path]]] = {family: [] for family in FAMILIES}
    high_by_family: dict[str, list[tuple[str, Path]]] = {family: [] for family in FAMILIES}

    for spec in specs:
        candidate = build_candidate(size, frame, eyes, opening, spec)
        family = spec["family"]
        candidate_dir = output_root / "candidates" / family
        candidate_dir.mkdir(parents=True, exist_ok=True)
        base = candidate_dir / candidate.candidate_id
        mask_path = base.with_suffix(".mask.png")
        alpha_path = base.with_suffix(".alpha.png")
        product_crop_path = candidate_dir / f"{candidate.candidate_id}.product_eye_crop.png"
        high_crop_path = candidate_dir / f"{candidate.candidate_id}.high_contrast_eye_crop.png"
        left_high_path = candidate_dir / f"{candidate.candidate_id}.left_high_contrast_crop.png"
        right_high_path = candidate_dir / f"{candidate.candidate_id}.right_high_contrast_crop.png"
        trace_path = base.with_suffix(".trace.json")

        mask_to_image(candidate.mask).save(mask_path)
        alpha_to_image(candidate.alpha).save(alpha_path)
        product = cosmetic_overlay(frame, candidate.alpha, FAMILY_COLORS[family], float(candidate.adjustment["previewOpacity"]))
        high = high_contrast_overlay(frame, candidate.mask, family)
        product.crop(both_bbox).save(product_crop_path)
        high.crop(both_bbox).save(high_crop_path)
        high.crop(left_bbox).save(left_high_path)
        high.crop(right_bbox).save(right_high_path)
        write_json(trace_path, candidate.trace)

        uv_metrics = {"status": "not_computed_for_all_candidates"}
        metrics = candidate_metrics(candidate, eyes, opening, uv_metrics)
        metrics["directionContractOk"] = family_direction_ok(family, float(spec["tailAngle"]))
        metrics["outerCanthusFillRequested"] = float(spec["outerCornerFill"])
        report = {
            "candidateId": candidate.candidate_id,
            "candidateIndex": spec["candidateIndex"],
            "familyKey": family,
            "policy": candidate.policy,
            "family": candidate.family,
            "styleTaxonomy": spec["style"],
            "sourceSignals": candidate.source_signals,
            "adjustment": candidate.adjustment,
            "warnings": candidate.warnings,
            "metrics": metrics,
            "paths": {
                "mask": str(mask_path),
                "alpha": str(alpha_path),
                "productEyeCrop": str(product_crop_path),
                "highContrastEyeCrop": str(high_crop_path),
                "leftHighContrastCrop": str(left_high_path),
                "rightHighContrastCrop": str(right_high_path),
                "trace": str(trace_path),
            },
        }
        reports.append(report)
        label = (
            f"{spec['candidateIndex']:02d} {family} "
            f"L{spec['tailLength']:.2f} A{int(spec['tailAngle'])} F{spec['outerCornerFill']:.2f}"
        )
        product_inputs.append((label, product_crop_path))
        high_inputs.append((label, high_crop_path))
        product_by_family[family].append((label, product_crop_path))
        high_by_family[family].append((label, high_crop_path))

    contact_dir = output_root / "contact_sheets"
    save_contact_sheet(product_inputs, contact_dir / "all_30_product.png", 300, 5)
    save_contact_sheet(high_inputs, contact_dir / "all_30_high_contrast.png", 300, 5)
    for family in FAMILIES:
        save_contact_sheet(product_by_family[family], contact_dir / f"{family}_10_product.png", 300, 5)
        save_contact_sheet(high_by_family[family], contact_dir / f"{family}_10_high_contrast.png", 300, 5)

    uv_inputs: list[tuple[str, Path]] = []
    uv_representatives = [reports[i] for i in [1, 4, 8, 11, 14, 18, 21, 24, 28]]
    if args.with_uv:
        for item in uv_representatives:
            candidate_mask = np.asarray(Image.open(item["paths"]["mask"]).convert("L")) > 0
            uv_path = output_root / "uv_projection" / f"{item['candidateId']}.uv_probability.png"
            round_trip_path = output_root / "uv_projection" / f"{item['candidateId']}.round_trip_overlay.png"
            round_trip_crop = output_root / "uv_projection" / f"{item['candidateId']}.round_trip_eye_crop.png"
            uv_path.parent.mkdir(parents=True, exist_ok=True)
            probability = back_project_mask(candidate_mask, arface_export, args.uv_resolution, 1)
            predicted = render_atlas_to_screen(probability, arface_export, size, 0.10, 1)
            alpha_to_image(probability).save(uv_path)
            round_trip_overlay(frame, candidate_mask, predicted).save(round_trip_path)
            crop_image(round_trip_path, both_bbox, round_trip_crop)
            item["metrics"]["uvRoundTrip"] = comparison_metrics(predicted, candidate_mask)
            item["paths"]["uvProbability"] = str(uv_path)
            item["paths"]["roundTripOverlay"] = str(round_trip_path)
            item["paths"]["roundTripEyeCrop"] = str(round_trip_crop)
            uv_inputs.append((f"{item['candidateIndex']:02d} {item['familyKey']}", round_trip_crop))
        save_contact_sheet(uv_inputs, contact_dir / "uv_round_trip_representative_9.png", 300, 3)

    family_counts = {family: sum(1 for item in reports if item["familyKey"] == family) for family in FAMILIES}
    scorecard = {
        "schemaVersion": "e7-eyeliner-team-feedback-v2-scorecard-v0",
        "createdAt": utc_now(),
        "status": "complete_buildless_local_only_pending_user_visual_pick",
        "decision": "pending_user_visual_pick",
        "capturePairId": mediapipe.get("capturePairId", args.capture_pair.name),
        "sourceFrame": str(frame_path),
        "mediapipeLandmarks": str(mediapipe_path),
        "arfaceExport": str(arface_path),
        "candidateCount": len(reports),
        "familyCounts": family_counts,
        "teamFeedbackApplied": {
            "familiesKept": list(FAMILIES),
            "samplesPerFamily": 10,
            "longerTail": True,
            "catTailDirection": "up",
            "wingedTailDirection": "horizontal",
            "puppyTailDirection": "down",
            "outerCanthusFill": True,
        },
        "directionContractPassCount": sum(1 for item in reports if item["metrics"]["directionContractOk"]),
        "uvRoundTripComputedCandidateIds": [item["candidateId"] for item in uv_representatives] if args.with_uv else [],
        "reviewCandidateIds": [item["candidateId"] for item in reports],
        "candidates": reports,
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "longTermRawFrameStored": False,
            "derivedMasksOnly": True,
            "userFeedbackSketchCopiedToDocAssets": feedback_sketch.exists(),
        },
        "productClaim": {
            "iphoneRuntimeGreen": False,
            "productQualityReady": False,
            "preXcodeBuildlessExperiment": True,
        },
    }
    shortlist = {
        "schemaVersion": "e7-eyeliner-team-feedback-v2-shortlist-v0",
        "createdAt": utc_now(),
        "status": "pending_user_visual_pick",
        "selectionInstructionKo": "cat/winged/puppy family에서 마음에 드는 candidateId를 골라주세요.",
        "reviewCandidates": reports,
        "recommendedPickShape": {
            "firstPass": "각 family에서 2개 이하로 좁힌 뒤 최종 default 1개 + fallback 1개를 고른다.",
            "candidateFormat": "team-v2-{family}-{index}-tail{tailLength}-angle{tailAngle}-fill{outerCornerFill}",
        },
    }
    write_json(output_root / "scorecard.json", scorecard)
    write_json(output_root / "shortlist.json", shortlist)
    write_text(
        output_root / "summary.md",
        f"""# E7 Eyeliner Team Feedback v2 Samples

Status: `complete_buildless_local_only_pending_user_visual_pick`

- Generated: `{len(reports)}` candidates.
- Families: `cat=10`, `winged=10`, `puppy=10`.
- Feedback applied: longer tails, family-specific tail direction, outer canthus fill.
- Product-quality/iPhone runtime Green: `false`.
- Report: `{args.doc_report / 'README.md'}`
""",
    )

    assets: dict[str, str] = {}
    if feedback_sketch.exists():
        assets["feedbackSketch"] = copy_asset(feedback_sketch, report_assets, "01-team-feedback-sketch.png")
    else:
        geometry_fallback = geometry_crop
        assets["feedbackSketch"] = copy_asset(geometry_fallback, report_assets, "01-team-feedback-sketch-missing-fallback.png")
    assets["geometry"] = copy_asset(geometry_crop, report_assets, "02-eyelid-and-canthus-anchor.png")
    assets["allProduct"] = copy_asset(contact_dir / "all_30_product.png", report_assets, "03-all-30-product.png")
    assets["allHighContrast"] = copy_asset(contact_dir / "all_30_high_contrast.png", report_assets, "04-all-30-high-contrast.png")
    assets["catProduct"] = copy_asset(contact_dir / "cat_10_product.png", report_assets, "05-cat-10-product.png")
    assets["catHighContrast"] = copy_asset(contact_dir / "cat_10_high_contrast.png", report_assets, "06-cat-10-high-contrast.png")
    assets["wingedProduct"] = copy_asset(contact_dir / "winged_10_product.png", report_assets, "07-winged-10-product.png")
    assets["wingedHighContrast"] = copy_asset(contact_dir / "winged_10_high_contrast.png", report_assets, "08-winged-10-high-contrast.png")
    assets["puppyProduct"] = copy_asset(contact_dir / "puppy_10_product.png", report_assets, "09-puppy-10-product.png")
    assets["puppyHighContrast"] = copy_asset(contact_dir / "puppy_10_high_contrast.png", report_assets, "10-puppy-10-high-contrast.png")
    if args.with_uv:
        assets["uvRoundTrip"] = copy_asset(contact_dir / "uv_round_trip_representative_9.png", report_assets, "11-uv-round-trip-representative-9.png")

    for artifact in ["scorecard.json", "shortlist.json", "summary.md"]:
        shutil.copyfile(output_root / artifact, report_artifacts / artifact)
    build_report(args.doc_report, output_root, assets, scorecard, shortlist)
    print(json.dumps({"status": "ok", "outputRoot": str(output_root), "report": str(args.doc_report / "README.md")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
