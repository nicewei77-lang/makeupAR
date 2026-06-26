#!/usr/bin/env python3
"""Evaluate the GUI Terminal MediaPipe lip result against the five core candidates.

This tool is read-only with respect to existing candidate outputs. It creates a
new evaluation folder with numeric comparisons, readable contact sheets, and
Korean review notes. It does not rerun MediaPipe, candidate generation, Unity,
Xcode, iPhone builds, uploads, or capture.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_lip_boundary_candidates import (  # noqa: E402
    CANDIDATES,
    bbox,
    boundary_distance_metrics,
    comparison_metrics,
    component_metrics,
    contour_quality,
    corner_recall_metrics,
    load_gold_reference,
    load_mask,
    mask_boundary,
    overlay_masks,
    sha256_file,
    symmetry_metrics,
    upper_lower_metrics,
    write_json,
)


SCHEMA_VERSION = "e7-mediapipe-vs-core-evaluation-v0"
DEFAULT_CORE_RUN = Path("evidence/e7-lip-candidate-generator/experiment-20260626Tmediapipe-v4")
DEFAULT_MEDIAPIPE_RUN = Path("evidence/e7-lip-candidate-generator/mediapipe-gui-terminal-20260626T154247Z")
DEFAULT_MEDIAPIPE_FAILURE_RUN = Path("evidence/e7-lip-candidate-generator/mediapipe-retry-20260626T152244Z")
DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_GOLD_RAW_DIR = Path("evidence/references/e7-user-gold-raw-20260626")
DEFAULT_FACE_PARSING_DIR = Path("evidence/e7-lip-m1-packages/m1-lip-face-parsing-20260625T2255Z")
DEFAULT_OUTPUT_ROOT = Path("evidence/e7-lip-candidate-generator")
GOLD_EXACT_MASK = Path(
    "evidence/e7-lip-mask-derivation/experiment-20260625T214159Z/gold_extracted_masks/"
    "user-gold-lip-mask-gray-20260625-163204_gold_exact_binary.png"
)

CANDIDATE_LABELS = {
    "parsing_curve_smooth": "face parsing mask를 곡선으로 다듬은 후보",
    "vision_curve_fill": "Apple Vision 입술 점을 곡선으로 채운 후보",
    "vision_color_snap": "Vision 곡선을 색/경계 쪽으로 미세 보정한 후보",
    "hybrid_curve_safe": "parsing + Vision + color를 보수적으로 섞은 후보",
    "hybrid_curve_balanced": "hybrid에서 폭과 커버리지를 조금 더 보존한 후보",
    "mediapipe_lip_curve": "MediaPipe 478 face landmark에서 lip curve를 채운 결과",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def file_info(path: Path) -> dict[str, Any]:
    absolute = resolve_path(path)
    info: dict[str, Any] = {"path": rel(absolute), "exists": absolute.exists()}
    if absolute.is_file():
        info.update(
            {
                "type": "file",
                "bytes": absolute.stat().st_size,
                "sha256": sha256_file(absolute),
            }
        )
    elif absolute.is_dir():
        files = [p for p in absolute.rglob("*") if p.is_file()]
        info.update({"type": "directory", "fileCount": len(files)})
    return info


def load_optional_mask(path: Path, size: tuple[int, int]) -> np.ndarray | None:
    absolute = resolve_path(path)
    if not absolute.exists():
        return None
    return load_mask(absolute, size)


def positive(mask: np.ndarray | None) -> int:
    if mask is None:
        return 0
    return int(np.count_nonzero(mask))


def bbox_reach(candidate: np.ndarray, reference: np.ndarray | None) -> dict[str, Any]:
    if reference is None or candidate.shape != reference.shape or not np.any(candidate) or not np.any(reference):
        return {"available": False}
    cbox = bbox(candidate)
    rbox = bbox(reference)
    if not cbox.get("available") or not rbox.get("available"):
        return {"available": False}
    width = max(1, int(rbox["width"]))
    height = max(1, int(rbox["height"]))
    return {
        "available": True,
        "leftDeltaPx": int(cbox["minX"] - rbox["minX"]),
        "rightDeltaPx": int(cbox["maxX"] - rbox["maxX"]),
        "topDeltaPx": int(cbox["minY"] - rbox["minY"]),
        "bottomDeltaPx": int(cbox["maxY"] - rbox["maxY"]),
        "widthRatio": round(float(cbox["width"]) / width, 6),
        "heightRatio": round(float(cbox["height"]) / height, 6),
    }


def split_reference_masks(reference: np.ndarray | None) -> tuple[np.ndarray | None, np.ndarray | None, int | None]:
    if reference is None or not np.any(reference):
        return None, None, None
    box = bbox(reference)
    if not box.get("available"):
        return None, None, None
    split_y = int(round((float(box["minY"]) + float(box["maxY"])) / 2.0))
    yy, _ = np.indices(reference.shape)
    return reference & (yy <= split_y), reference & (yy > split_y), split_y


def upper_lower_gold_metrics(candidate: np.ndarray, reference: np.ndarray | None) -> dict[str, Any]:
    upper_ref, lower_ref, split_y = split_reference_masks(reference)
    if upper_ref is None or lower_ref is None:
        return {"available": False}

    def recall(region: np.ndarray) -> float | None:
        count = int(np.count_nonzero(region))
        if count == 0:
            return None
        return round(float(np.count_nonzero(candidate & region) / count), 6)

    yy, _ = np.indices(candidate.shape)
    upper_candidate = candidate & (yy <= int(split_y))
    lower_candidate = candidate & (yy > int(split_y))
    upper_pixels = int(np.count_nonzero(upper_candidate))
    lower_pixels = int(np.count_nonzero(lower_candidate))
    total = upper_pixels + lower_pixels
    return {
        "available": True,
        "splitY": split_y,
        "candidateUpperPixels": upper_pixels,
        "candidateLowerPixels": lower_pixels,
        "candidateUpperShare": round(upper_pixels / total, 6) if total else None,
        "goldUpperPixels": int(np.count_nonzero(upper_ref)),
        "goldLowerPixels": int(np.count_nonzero(lower_ref)),
        "goldUpperShare": round(float(np.count_nonzero(upper_ref)) / int(np.count_nonzero(reference)), 6),
        "upperRecallVsGold": recall(upper_ref),
        "lowerRecallVsGold": recall(lower_ref),
        "upperMissPixels": int(np.count_nonzero(upper_ref & ~candidate)),
        "lowerMissPixels": int(np.count_nonzero(lower_ref & ~candidate)),
    }


def fill_ratio(mask: np.ndarray) -> float | None:
    box = bbox(mask)
    if not box.get("available"):
        return None
    area = max(1, int(box["width"]) * int(box["height"]))
    return round(float(np.count_nonzero(mask)) / area, 6)


def centroid(mask: np.ndarray) -> dict[str, Any]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return {"available": False}
    return {"available": True, "x": round(float(xs.mean()), 3), "y": round(float(ys.mean()), 3)}


def mask_metrics(
    mask: np.ndarray,
    gold: np.ndarray | None,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
    skin: np.ndarray | None,
    inner_mouth: np.ndarray | None,
) -> dict[str, Any]:
    skin_pixels = positive(skin)
    inner_pixels = positive(inner_mouth)
    rough = contour_quality(mask)
    edge_pixels = int(np.count_nonzero(mask_boundary(mask))) if np.any(mask) else 0
    return {
        "positivePixels": int(np.count_nonzero(mask)),
        "bbox": bbox(mask),
        "goldComparison": comparison_metrics(mask, gold),
        "boundaryDistanceVsGold": boundary_distance_metrics(mask, gold),
        "cornerRecallVsGold": corner_recall_metrics(mask, gold),
        "bboxReachVsGold": bbox_reach(mask, gold),
        "upperLowerVsGold": upper_lower_gold_metrics(mask, gold),
        "faceParsingUpperLower": upper_lower_metrics(mask, upper, lower),
        "contourQuality": rough,
        "edgePixels": edge_pixels,
        "edgePixelsPerArea": round(edge_pixels / max(1, int(np.count_nonzero(mask))), 6),
        "components": component_metrics(mask),
        "symmetry": symmetry_metrics(mask),
        "bboxFillRatio": fill_ratio(mask),
        "centroid": centroid(mask),
        "spillProxies": {
            "skinMaskAvailable": skin is not None,
            "innerMouthMaskAvailable": inner_mouth is not None,
            "skinOverlapPixels": int(np.count_nonzero(mask & skin)) if skin is not None else None,
            "skinOverlapShare": round(float(np.count_nonzero(mask & skin)) / max(1, skin_pixels), 6)
            if skin is not None
            else None,
            "innerMouthOverlapPixels": int(np.count_nonzero(mask & inner_mouth)) if inner_mouth is not None else None,
            "innerMouthOverlapShare": round(float(np.count_nonzero(mask & inner_mouth)) / max(1, inner_pixels), 6)
            if inner_mouth is not None
            else None,
        },
    }


def sort_rows_by_gold_iou(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: row.get("metrics", {}).get("goldComparison", {}).get("iou", -1),
        reverse=True,
    )


def fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def label_font() -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, 24)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], label: str, width: int) -> None:
    x, y = xy
    draw.rectangle((x, y, x + width, y + 60), fill=(255, 255, 255))
    draw.text((x + 12, y + 18), label[:70], fill=(20, 20, 20), font=label_font())


def make_contact_sheet(entries: list[tuple[str, Image.Image]], path: Path, thumb_w: int, thumb_h: int, cols: int) -> None:
    label_h = 62
    rows = math.ceil(len(entries) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(entries):
        col = index % cols
        row = index // cols
        x = col * thumb_w
        y = row * (thumb_h + label_h)
        thumb = ImageOps.exif_transpose(image.convert("RGB"))
        thumb.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        px = x + (thumb_w - thumb.width) // 2
        py = y + label_h + (thumb_h - thumb.height) // 2
        sheet.paste(thumb, (px, py))
        draw_label(draw, (x, y), label, thumb_w)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def crop_box_from_masks(masks: list[np.ndarray], size: tuple[int, int], padding: int = 140) -> tuple[int, int, int, int]:
    merged = np.zeros((size[1], size[0]), dtype=bool)
    for mask in masks:
        if mask is not None and mask.shape == merged.shape:
            merged |= mask
    box = bbox(merged)
    if not box.get("available"):
        return (0, 0, size[0], size[1])
    left = max(0, int(box["minX"]) - padding)
    top = max(0, int(box["minY"]) - padding)
    right = min(size[0], int(box["maxX"]) + padding + 1)
    bottom = min(size[1], int(box["maxY"]) + padding + 1)
    return (left, top, right, bottom)


def overlay_gold(frame: Image.Image, gold: np.ndarray | None) -> Image.Image:
    if gold is None:
        return frame.convert("RGB")
    return overlay_masks(frame, [(gold, (255, 212, 40), 0.55), (mask_boundary(gold), (255, 255, 255), 0.95)])


def write_metrics_markdown(path: Path, rows: list[dict[str, Any]], decision: str) -> None:
    lines = [
        "# MediaPipe vs core 후보 지표",
        "",
        f"- 생성 시각(UTC): `{utc_now()}`",
        f"- 결정: `{decision}`",
        "- 점수는 기존 core 후보와 같은 gold exact binary 기준으로 계산했다.",
        "",
        "| 순위 | 후보 | 설명 | pixels | bbox | gold IoU | precision | recall | outside | upper recall | lower recall | left corner | right corner | roughness |",
        "| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(sort_rows_by_gold_iou(rows), start=1):
        metrics = row["metrics"]
        gold = metrics.get("goldComparison", {})
        upper_lower = metrics.get("upperLowerVsGold", {})
        corner = metrics.get("cornerRecallVsGold", {})
        rough = metrics.get("contourQuality", {})
        box = metrics.get("bbox", {})
        bbox_text = (
            f'{box.get("width")}x{box.get("height")} '
            f'({box.get("minX")},{box.get("minY")}-{box.get("maxX")},{box.get("maxY")})'
            if box.get("available")
            else "n/a"
        )
        lines.append(
            "| {} | `{}` | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                rank,
                row["id"],
                row["description"],
                metrics.get("positivePixels"),
                bbox_text,
                fmt(gold.get("iou"), 6),
                fmt(gold.get("precision"), 6),
                fmt(gold.get("recall"), 6),
                fmt(gold.get("outsideReference"), 6),
                fmt(upper_lower.get("upperRecallVsGold"), 6),
                fmt(upper_lower.get("lowerRecallVsGold"), 6),
                fmt(corner.get("leftCornerRecall"), 6),
                fmt(corner.get("rightCornerRecall"), 6),
                fmt(rough.get("roughnessIndex"), 6),
            )
        )
    lines.extend(
        [
            "",
            "## 해석 메모",
            "",
            "- MediaPipe는 precision은 높지만 recall과 IoU가 core 5개보다 낮다. 즉 크게 넘치지는 않지만 gold 기준으로 덜 잡는 쪽이다.",
            "- MediaPipe는 landmark 기반 기하 형태라서 색 경계에 직접 붙는 신호가 아니다.",
            "- 이 지표만으로는 MediaPipe를 단독 6번째 후보로 승격하기 어렵다.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_visual_review(
    path: Path,
    media_row: dict[str, Any],
    best_core_row: dict[str, Any],
    contact_sheet: Path,
    crop_sheet: Path,
) -> None:
    media = media_row["metrics"]
    best = best_core_row["metrics"]
    media_gold = media.get("goldComparison", {})
    best_gold = best.get("goldComparison", {})
    media_upper = media.get("upperLowerVsGold", {})
    media_corner = media.get("cornerRecallVsGold", {})
    media_reach = media.get("bboxReachVsGold", {})
    lines = [
        "# MediaPipe 시각 리뷰",
        "",
        "## 비교 이미지",
        "",
        f"- 전체 비교: `{rel(contact_sheet)}`",
        f"- 입술 crop 비교: `{rel(crop_sheet)}`",
        "",
        "## 질문별 답",
        "",
        "1. MediaPipe가 core 5개보다 시각적으로 더 좋은가?",
        "",
        "- 단독 후보로는 더 좋다고 보기 어렵다. 입술 주변에 크게 번지지 않는 점은 좋지만, core 후보보다 recall과 IoU가 낮고 윗입술 형태가 단순해진다.",
        f"- 지표상 MediaPipe gold IoU는 `{fmt(media_gold.get('iou'), 6)}`, 최고 core 후보 `{best_core_row['id']}`는 `{fmt(best_gold.get('iou'), 6)}`다.",
        "",
        "2. 입꼬리는 더 잘 잡는가?",
        "",
        f"- 좌측 corner recall `{fmt(media_corner.get('leftCornerRecall'), 6)}`, 우측 corner recall `{fmt(media_corner.get('rightCornerRecall'), 6)}`다.",
        f"- bbox 기준 오른쪽 끝 delta는 `{fmt(media_reach.get('rightDeltaPx'))}px`다. 음수면 gold보다 오른쪽 끝을 덜 간 것이다.",
        "- 우측 corner recall 자체는 좋은 편이지만, bbox 끝단은 gold보다 짧고 좌측 corner는 core balanced보다 약하다.",
        "- 따라서 corner 보조 신호로는 쓸 수 있지만, corner coverage를 해결하는 단독 답으로 보기는 어렵다.",
        "",
        "3. 입술 모양을 과하게 단순화하는가?",
        "",
        "- 그렇다. MediaPipe는 landmark 기반이라 입술 전체를 안정적인 곡선으로 만들지만, 사진에서 보이는 비대칭과 얇은 윗입술 형태를 덜 반영한다.",
        "",
        "4. 윗입술/아랫입술을 덜 잡는가?",
        "",
        f"- gold 기준 upper recall은 `{fmt(media_upper.get('upperRecallVsGold'), 6)}`, lower recall은 `{fmt(media_upper.get('lowerRecallVsGold'), 6)}`다.",
        "- 특히 윗입술 쪽 coverage가 약하다. 아랫입술은 상대적으로 유지되지만, 전체 mask는 core 후보보다 작고 단순하다.",
        "",
        "5. edge는 parsing/gold-derived mask보다 더 부드러운가?",
        "",
        "- 육안으로는 매끈하고 안정적으로 보인다. 다만 이것은 실제 색 경계를 잘 맞춘 결과라기보다 점 기반 곡선을 채운 결과다.",
        "- 따라서 edge smoothing 보조에는 유용하지만, boundary source 자체로 보기에는 부족하다.",
        "",
        "6. 너무 geometric하고 color-boundary-aware하지 않은가?",
        "",
        "- 그렇다. MediaPipe report 자체도 face geometry landmark 신호라고 기록되어 있고, 색/그라디언트 경계 신호를 사용하지 않는다.",
        "",
        "7. 다음 후보 생성기에 어떻게 반영할까?",
        "",
        "- `use_as_helper_signal`이 맞다. standalone 후보가 아니라, hybrid 후보 안에서 shape prior / centerline / inner-mouth / gross sanity check로 쓰는 것이 적절하다.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_integration_recommendation(path: Path, rows: list[dict[str, Any]], decision: str) -> None:
    media = next(row for row in rows if row["id"] == "mediapipe_lip_curve")
    best_core = sort_rows_by_gold_iou([row for row in rows if row["id"] != "mediapipe_lip_curve"])[0]
    media_gold = media["metrics"].get("goldComparison", {})
    best_gold = best_core["metrics"].get("goldComparison", {})
    lines = [
        "# MediaPipe 통합 권고",
        "",
        f"결정: `{decision}`",
        "",
        "## 근거",
        "",
        f"- MediaPipe gold IoU `{fmt(media_gold.get('iou'), 6)}`는 core 최고 `{best_core['id']}`의 `{fmt(best_gold.get('iou'), 6)}`보다 낮다.",
        f"- MediaPipe precision `{fmt(media_gold.get('precision'), 6)}`은 높아서 크게 번지지는 않지만, recall `{fmt(media_gold.get('recall'), 6)}`이 낮아 덜 잡는 쪽이다.",
        "- 시각적으로는 깔끔한 곡선이지만, 윗입술과 좌우 세부 형태를 단순화한다.",
        "- MediaPipe는 색 경계 신호가 아니라 얼굴 landmark geometry 신호다.",
        "",
        "## 다음 후보 생성기에서의 역할",
        "",
        "- `shape_prior`: 후보 경계가 지나치게 찌그러지거나 튀는지 비교하는 기준선으로 쓴다.",
        "- `centerline_inner_mouth_hint`: inner lip landmark를 입 안쪽/중앙선 보존 힌트로 쓴다.",
        "- `curve_smoothing_hint`: parsing이나 color edge가 만든 거친 경계를 부드럽게 만들 때 참고한다.",
        "- `gross_sanity_check`: 후보 bbox/중심/폭이 MediaPipe geometry에서 크게 벗어나면 review flag를 남긴다.",
        "",
        "## 하지 말아야 할 것",
        "",
        "- MediaPipe mask를 그대로 6번째 최종 후보로 승격하지 않는다.",
        "- MediaPipe 성공만으로 M1 ready, runtime ready, E7.3 Green, Lip G/Y/R을 주장하지 않는다.",
        "- Codex shell 자동 실행을 필수 gate로 넣지 않는다.",
        "",
        "## 최소 구현 제안",
        "",
        "1. next candidate generator에서 MediaPipe가 있으면 landmark-derived geometry metrics만 읽는다.",
        "2. final mask는 parsing / Vision / color edge를 우선하고, MediaPipe는 smoothing과 sanity flag에만 사용한다.",
        "3. Codex shell에서 MediaPipe preflight가 실패하면 `manual_gui_required`로 기록하고 core 후보 생성은 계속 진행한다.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_environment_caveat(path: Path, failure_run: Path, gui_run: Path) -> None:
    lines = [
        "# MediaPipe 실행 환경 caveat",
        "",
        "## 확인된 사실",
        "",
        f"- Codex shell 실패 산출물: `{rel(resolve_path(failure_run))}`",
        f"- macOS GUI Terminal 성공 산출물: `{rel(resolve_path(gui_run))}`",
        "- 두 실행은 같은 `.venv`, 같은 MediaPipe package, 같은 frame, 같은 model을 사용했다.",
        "- Codex shell에서는 네 가지 retry variant가 `exitCode=-6`으로 실패했다.",
        "- 실패 stderr에는 `gl_context_nsgl`, `graph_service.h:139`, `DrishtiMetalHelper`가 남았다.",
        "- GUI Terminal 실행은 `faceCount=1`, `landmarkCount=478`, `positivePixels=15154`로 성공했다.",
        "",
        "## 해석",
        "",
        "- 입력 이미지, 모델 파일, Python import 문제가 아니라 실행 환경의 GL/Metal context 생성 가능 여부가 차이를 만든 것으로 본다.",
        "- 따라서 MediaPipe는 깨진 것이 아니라, 현재 Codex shell 자동 실행 경로에서 안정적으로 쓸 수 없는 상태다.",
        "",
        "## 운영 규칙",
        "",
        "- MediaPipe 결과는 수동 GUI Terminal 비교 신호로는 사용할 수 있다.",
        "- 자동 파이프라인의 필수 단계로 넣지 않는다.",
        "- 자동 실행에서 실패하면 `manual_gui_required` 또는 `mediapipe_context_unavailable`로 기록하고 core 후보 생성/평가는 계속한다.",
        "",
        "## 재현 절차",
        "",
        "macOS Terminal 앱에서 repo root로 이동한 뒤 실행한다.",
        "",
        "```sh",
        "bash scripts/e7_lip_candidate_generator/run_mediapipe_gui_terminal_retry.sh",
        "```",
        "",
        "확인할 파일:",
        "",
        "- `mediapipe_lip_report.json`",
        "- `mediapipe_lip_curve_overlay.png`",
        "- `mediapipe_lip_curve_mask.png`",
        "- `mediapipe_landmark_overlay.png`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_summary(path: Path, output_dir: Path, decision: str, rows: list[dict[str, Any]]) -> None:
    media = next(row for row in rows if row["id"] == "mediapipe_lip_curve")
    best_core = sort_rows_by_gold_iou([row for row in rows if row["id"] != "mediapipe_lip_curve"])[0]
    media_gold = media["metrics"]["goldComparison"]
    best_gold = best_core["metrics"]["goldComparison"]
    lines = [
        "# MediaPipe lip 평가 요약",
        "",
        f"- output: `{rel(output_dir)}`",
        f"- decision: `{decision}`",
        f"- MediaPipe gold IoU: `{fmt(media_gold.get('iou'), 6)}`",
        f"- core 최고: `{best_core['id']}` / gold IoU `{fmt(best_gold.get('iou'), 6)}`",
        "",
        "결론: MediaPipe는 단독 후보보다 보조 신호로 쓰는 것이 맞다. 입술 주변에 안정적으로 붙고 크게 번지지 않지만, 윗입술 coverage가 낮고 전체 형태가 단순하며 색 경계에 직접 붙는 신호가 아니다.",
        "",
        "이번 작업에서 하지 않은 것:",
        "",
        "- 기존 core 5 후보 재생성 또는 수정",
        "- Unity/Xcode/iPhone build",
        "- 새 raw frame capture",
        "- upload",
        "- M1 ready / runtime ready / E7.3 Green / Lip G/Y/R 주장",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_input_inventory(
    path: Path,
    args: argparse.Namespace,
    output_dir: Path,
    frame_size: tuple[int, int],
    gold: np.ndarray | None,
) -> None:
    inventory = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAtUtc": utc_now(),
        "outputDir": rel(output_dir),
        "frameSize": {"width": frame_size[0], "height": frame_size[1]},
        "goldReferenceLoaded": gold is not None,
        "inputs": {
            "coreRun": file_info(args.core_run),
            "mediapipeGuiRun": file_info(args.mediapipe_run),
            "mediapipeFailureRun": file_info(args.mediapipe_failure_run),
            "frame": file_info(args.frame),
            "goldRawDir": file_info(args.gold_raw_dir),
            "goldExactMask": file_info(GOLD_EXACT_MASK),
            "faceParsingDir": file_info(args.face_parsing_dir),
            "coreSummary": file_info(args.core_run / "candidate_generation_summary.json"),
            "mediapipeReport": file_info(args.mediapipe_run / "mediapipe_lip_report.json"),
            "mediapipeMask": file_info(args.mediapipe_run / "mediapipe_lip_curve_mask.png"),
            "mediapipeOverlay": file_info(args.mediapipe_run / "mediapipe_lip_curve_overlay.png"),
            "mediapipeFailureReport": file_info(args.mediapipe_failure_run / "mediapipe_lip_report.json"),
        },
        "rules": {
            "coreCandidatesRerun": False,
            "unityBuild": False,
            "xcodeBuild": False,
            "iphoneBuild": False,
            "upload": False,
            "newCapture": False,
            "readableContactSheets": True,
        },
    }
    write_json(path, inventory)


def build_rows(
    frame_size: tuple[int, int],
    args: argparse.Namespace,
    gold: np.ndarray | None,
    upper: np.ndarray | None,
    lower: np.ndarray | None,
    skin: np.ndarray | None,
    inner_mouth: np.ndarray | None,
) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    masks: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    for candidate_id in CANDIDATES:
        mask_path = resolve_path(args.core_run / "candidates" / f"{candidate_id}_mask.png")
        if not mask_path.exists():
            raise FileNotFoundError(mask_path)
        mask = load_mask(mask_path, frame_size)
        masks[candidate_id] = mask
        rows.append(
            {
                "id": candidate_id,
                "source": "core_candidate",
                "description": CANDIDATE_LABELS[candidate_id],
                "paths": {
                    "mask": rel(mask_path),
                    "overlay": rel(resolve_path(args.core_run / "candidates" / f"{candidate_id}_overlay.png")),
                    "alpha": rel(resolve_path(args.core_run / "candidates" / f"{candidate_id}_alpha.png")),
                },
                "metrics": mask_metrics(mask, gold, upper, lower, skin, inner_mouth),
            }
        )

    mediapipe_mask_path = resolve_path(args.mediapipe_run / "mediapipe_lip_curve_mask.png")
    if not mediapipe_mask_path.exists():
        raise FileNotFoundError(mediapipe_mask_path)
    mediapipe_mask = load_mask(mediapipe_mask_path, frame_size)
    masks["mediapipe_lip_curve"] = mediapipe_mask
    rows.append(
        {
            "id": "mediapipe_lip_curve",
            "source": "mediapipe_gui_terminal",
            "description": CANDIDATE_LABELS["mediapipe_lip_curve"],
            "paths": {
                "mask": rel(mediapipe_mask_path),
                "overlay": rel(resolve_path(args.mediapipe_run / "mediapipe_lip_curve_overlay.png")),
                "alpha": rel(resolve_path(args.mediapipe_run / "mediapipe_lip_curve_alpha.png")),
                "landmarkOverlay": rel(resolve_path(args.mediapipe_run / "mediapipe_landmark_overlay.png")),
                "curvePoints": rel(resolve_path(args.mediapipe_run / "mediapipe_lip_curve_points.json")),
            },
            "metrics": mask_metrics(mediapipe_mask, gold, upper, lower, skin, inner_mouth),
        }
    )
    return rows, masks


def add_pairwise_overlaps(rows: list[dict[str, Any]], masks: dict[str, np.ndarray]) -> None:
    for row in rows:
        row["overlapWithCandidates"] = {}
        for other_id, other_mask in masks.items():
            if other_id == row["id"]:
                continue
            row["overlapWithCandidates"][other_id] = comparison_metrics(masks[row["id"]], other_mask)


def make_contact_sheets(
    output_dir: Path,
    frame: Image.Image,
    args: argparse.Namespace,
    gold: np.ndarray | None,
    masks: dict[str, np.ndarray],
) -> tuple[Path, Path]:
    entries: list[tuple[str, Image.Image]] = [("original frame", frame)]
    if gold is not None:
        entries.append(("gold exact reference", overlay_gold(frame, gold)))
    for candidate_id in CANDIDATES:
        overlay_path = resolve_path(args.core_run / "candidates" / f"{candidate_id}_overlay.png")
        entries.append((candidate_id, Image.open(overlay_path).convert("RGB")))
    entries.append(("mediapipe_lip_curve", Image.open(resolve_path(args.mediapipe_run / "mediapipe_lip_curve_overlay.png"))))
    contact_sheet = output_dir / "mediapipe_vs_core_contact_sheet.png"
    make_contact_sheet(entries, contact_sheet, thumb_w=620, thumb_h=930, cols=2)

    crop_box = crop_box_from_masks([mask for mask in masks.values()] + ([gold] if gold is not None else []), frame.size)
    crop_entries: list[tuple[str, Image.Image]] = []
    for label, image in entries:
        crop_entries.append((label, image.crop(crop_box)))
    crop_sheet = output_dir / "mediapipe_lip_crop_contact_sheet.png"
    make_contact_sheet(crop_entries, crop_sheet, thumb_w=640, thumb_h=480, cols=2)
    return contact_sheet, crop_sheet


def write_metrics_json(
    path: Path,
    rows: list[dict[str, Any]],
    decision: str,
    args: argparse.Namespace,
    contact_sheet: Path,
    crop_sheet: Path,
) -> None:
    mediapipe_report = read_json(resolve_path(args.mediapipe_run / "mediapipe_lip_report.json"))
    core_summary = read_json(resolve_path(args.core_run / "candidate_generation_summary.json"))
    data = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAtUtc": utc_now(),
        "decision": decision,
        "coreRun": rel(resolve_path(args.core_run)),
        "mediapipeGuiRun": rel(resolve_path(args.mediapipe_run)),
        "mediapipeFailureRun": rel(resolve_path(args.mediapipe_failure_run)),
        "contactSheets": {
            "full": rel(contact_sheet),
            "lipCrop": rel(crop_sheet),
        },
        "mediapipeSourceReport": {
            "available": mediapipe_report.get("available"),
            "faceCount": mediapipe_report.get("faceCount"),
            "landmarkCount": mediapipe_report.get("landmarkCount"),
            "positivePixels": mediapipe_report.get("positivePixels"),
            "variantId": mediapipe_report.get("variantId"),
            "successfulVariant": mediapipe_report.get("successfulVariant"),
            "manualGuiTerminalRequired": True,
        },
        "coreSummarySource": {
            "candidateIds": list(core_summary.get("candidates", {}).keys()),
            "summaryPath": rel(resolve_path(args.core_run / "candidate_generation_summary.json")),
        },
        "rows": rows,
    }
    write_json(path, data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate GUI Terminal MediaPipe lip output against core candidates.")
    parser.add_argument("--core-run", type=Path, default=DEFAULT_CORE_RUN)
    parser.add_argument("--mediapipe-run", type=Path, default=DEFAULT_MEDIAPIPE_RUN)
    parser.add_argument("--mediapipe-failure-run", type=Path, default=DEFAULT_MEDIAPIPE_FAILURE_RUN)
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--gold-raw-dir", type=Path, default=DEFAULT_GOLD_RAW_DIR)
    parser.add_argument("--face-parsing-dir", type=Path, default=DEFAULT_FACE_PARSING_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(REPO_ROOT)
    run_id = args.run_id or f"mediapipe-evaluation-{utc_stamp()}"
    output_dir = resolve_path(args.output_root / run_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = Image.open(resolve_path(args.frame)).convert("RGB")
    frame_size = frame.size
    gold = load_gold_reference(frame_size)
    upper = load_optional_mask(args.face_parsing_dir / "face_parsing_upper_lip_mask.png", frame_size)
    lower = load_optional_mask(args.face_parsing_dir / "face_parsing_lower_lip_mask.png", frame_size)
    skin = load_optional_mask(args.face_parsing_dir / "face_parsing_skin_mask.png", frame_size)
    inner_mouth = load_optional_mask(args.face_parsing_dir / "face_parsing_inner_mouth_mask.png", frame_size)

    rows, masks = build_rows(frame_size, args, gold, upper, lower, skin, inner_mouth)
    add_pairwise_overlaps(rows, masks)
    decision = "use_as_helper_signal"
    contact_sheet, crop_sheet = make_contact_sheets(output_dir, frame, args, gold, masks)

    write_input_inventory(output_dir / "input_inventory.json", args, output_dir, frame_size, gold)
    write_metrics_json(output_dir / "mediapipe_vs_core_metrics.json", rows, decision, args, contact_sheet, crop_sheet)
    write_metrics_markdown(output_dir / "mediapipe_vs_core_metrics.md", rows, decision)

    best_core = sort_rows_by_gold_iou([row for row in rows if row["id"] != "mediapipe_lip_curve"])[0]
    media_row = next(row for row in rows if row["id"] == "mediapipe_lip_curve")
    write_visual_review(output_dir / "mediapipe_visual_review.md", media_row, best_core, contact_sheet, crop_sheet)
    write_integration_recommendation(output_dir / "mediapipe_integration_recommendation.md", rows, decision)
    write_environment_caveat(output_dir / "mediapipe_environment_caveat.md", args.mediapipe_failure_run, args.mediapipe_run)
    write_summary(output_dir / "summary.md", output_dir, decision, rows)

    print(rel(output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
