#!/usr/bin/env python3
"""Fast offline gate for the E7 reference-driven UV atlas path.

This script intentionally stays smaller than the full E7 atlas pipeline. It
uses the two user-authored A/B mask sets and existing synchronized ARFace
exports to answer one question: does screen mask -> UV -> screen projection look
viable enough to justify a later runtime atlas sweep?
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
from PIL import Image, ImageDraw


REGIONS = ("lip", "cheek", "eye")
REGION_MASKS = {
    "lip": {"A": "A_lips.png", "B": "B_lips.png"},
    "cheek": {"A": "A_cheeks.png", "B": "B_cheeks.png"},
    "eye": {"A": "A_eyes.png", "B": "B_eyes.png"},
}


@dataclass(frozen=True)
class CaptureInput:
    label: str
    capture_pair_id: str
    path: Path
    frame_path: Path
    export_path: Path


@dataclass
class BackProjection:
    probability: np.ndarray
    coverage: np.ndarray
    positive_votes: int
    total_votes: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the E7 A/B UV atlas fast decision gate."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to current working directory.",
    )
    parser.add_argument(
        "--uv-resolution",
        type=int,
        default=512,
        help="Square UV atlas resolution for the fast gate.",
    )
    parser.add_argument(
        "--sample-stride",
        type=int,
        default=2,
        help="Screen-space pixel stride used while rasterizing triangles.",
    )
    parser.add_argument(
        "--render-stride",
        type=int,
        default=1,
        help="Screen-space pixel stride used while rendering atlas masks back to frames.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to evidence fast-gate timestamp.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def load_mask(path: Path) -> np.ndarray:
    rgba = np.array(Image.open(path).convert("RGBA"))
    alpha = rgba[:, :, 3]
    alpha_ratio = float(np.count_nonzero(alpha > 8)) / float(alpha.size)
    if 0.0 < alpha_ratio < 0.90:
        return alpha > 8

    rgb = rgba[:, :, :3].astype(np.int16)
    spread = rgb.max(axis=2) - rgb.min(axis=2)
    return (alpha > 8) & (spread > 12)


def export_arrays(data: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    screen_vertices = np.asarray(data.get("screenVertices", []), dtype=np.float64)
    uvs = np.asarray(data.get("uvs", []), dtype=np.float64)
    indices = np.asarray(data.get("indices", []), dtype=np.int32)
    if indices.ndim != 1:
        indices = indices.reshape(-1)
    return screen_vertices, uvs, indices


def uv_to_rc(uv: np.ndarray, resolution: int) -> tuple[np.ndarray, np.ndarray]:
    u = np.clip(uv[:, 0], 0.0, 1.0)
    v = np.clip(uv[:, 1], 0.0, 1.0)
    cols = np.rint(u * (resolution - 1)).astype(np.int32)
    rows = np.rint((1.0 - v) * (resolution - 1)).astype(np.int32)
    return rows, cols


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
    u = (
        (w0 * tri_uv[0, 0] * inv_w[0])
        + (w1 * tri_uv[1, 0] * inv_w[1])
        + (w2 * tri_uv[2, 0] * inv_w[2])
    ) / denom
    v = (
        (w0 * tri_uv[0, 1] * inv_w[0])
        + (w1 * tri_uv[1, 1] * inv_w[1])
        + (w2 * tri_uv[2, 1] * inv_w[2])
    ) / denom
    return np.column_stack((u, v))


def iter_triangles(indices: np.ndarray) -> np.ndarray:
    usable = (len(indices) // 3) * 3
    return indices[:usable].reshape(-1, 3)


def back_project_mask(
    mask: np.ndarray,
    export: dict[str, Any],
    resolution: int,
    sample_stride: int,
) -> BackProjection:
    screen_vertices, uvs, indices = export_arrays(export)
    if len(screen_vertices) != len(uvs):
        raise ValueError("screenVertices and uvs length mismatch")

    height, width = mask.shape
    pos_votes = np.zeros((resolution, resolution), dtype=np.uint32)
    total_votes = np.zeros((resolution, resolution), dtype=np.uint32)

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

        x_values = np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64)
        y_values = np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64)
        if x_values.size == 0 or y_values.size == 0:
            continue
        xs, ys = np.meshgrid(x_values, y_values)
        inside, w0, w1, w2 = barycentric_grid(xs, ys, tri_xy)
        if not np.any(inside):
            continue

        inside_x = xs[inside].astype(np.int32)
        inside_y = ys[inside].astype(np.int32)
        uv = interpolate_uv(
            uvs[tri],
            tri_screen[:, 3] if tri_screen.shape[1] >= 4 else np.ones(3),
            w0[inside],
            w1[inside],
            w2[inside],
        )
        rows, cols = uv_to_rc(uv, resolution)
        positive = mask[inside_y, inside_x]
        np.add.at(total_votes, (rows, cols), 1)
        np.add.at(pos_votes, (rows[positive], cols[positive]), 1)

    with np.errstate(divide="ignore", invalid="ignore"):
        probability = np.divide(
            pos_votes,
            total_votes,
            out=np.zeros_like(pos_votes, dtype=np.float32),
            where=total_votes > 0,
        )
    return BackProjection(
        probability=probability,
        coverage=total_votes > 0,
        positive_votes=int(pos_votes.sum()),
        total_votes=int(total_votes.sum()),
    )


def render_atlas_to_screen(
    probability: np.ndarray,
    export: dict[str, Any],
    frame_size: tuple[int, int],
    threshold: float,
    sample_stride: int,
) -> np.ndarray:
    width, height = frame_size
    screen_vertices, uvs, indices = export_arrays(export)
    predicted = np.zeros((height, width), dtype=bool)

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

        x_values = np.arange(min_x, max_x + 1, sample_stride, dtype=np.float64)
        y_values = np.arange(min_y, max_y + 1, sample_stride, dtype=np.float64)
        xs, ys = np.meshgrid(x_values, y_values)
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


def metrics(predicted: np.ndarray, gold: np.ndarray) -> dict[str, Any]:
    tp = int(np.count_nonzero(predicted & gold))
    fp = int(np.count_nonzero(predicted & ~gold))
    fn = int(np.count_nonzero(~predicted & gold))
    candidate_positive = int(np.count_nonzero(predicted))
    reference_positive = int(np.count_nonzero(gold))
    union = tp + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    iou = tp / union if union else 0.0
    leakage = fp / candidate_positive if candidate_positive else 0.0
    miss = fn / reference_positive if reference_positive else 0.0
    centroid_shift = None
    if candidate_positive and reference_positive:
        pred_yx = np.argwhere(predicted)
        gold_yx = np.argwhere(gold)
        pred_centroid = pred_yx.mean(axis=0)
        gold_centroid = gold_yx.mean(axis=0)
        centroid_shift = float(np.linalg.norm(pred_centroid - gold_centroid))
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "candidatePositive": candidate_positive,
        "referencePositive": reference_positive,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "iou": round(iou, 4),
        "leakage": round(leakage, 4),
        "miss": round(miss, 4),
        "centroidShiftPx": round(centroid_shift, 2) if centroid_shift is not None else None,
    }


def save_probability(path: Path, probability: np.ndarray) -> None:
    image = Image.fromarray(np.rint(np.clip(probability, 0.0, 1.0) * 255).astype(np.uint8))
    image.save(path)


def save_coverage(path: Path, coverage: np.ndarray) -> None:
    Image.fromarray((coverage.astype(np.uint8) * 255)).save(path)


def save_uv_overlap(
    path: Path, a_probability: np.ndarray, b_probability: np.ndarray, threshold: float
) -> dict[str, Any]:
    a_bin = a_probability >= threshold
    b_bin = b_probability >= threshold
    core = a_bin & b_bin
    a_only = a_bin & ~b_bin
    b_only = b_bin & ~a_bin
    union = a_bin | b_bin
    image = np.zeros((*a_bin.shape, 3), dtype=np.uint8)
    image[core] = [255, 255, 255]
    image[a_only] = [255, 80, 80]
    image[b_only] = [80, 150, 255]
    Image.fromarray(image).save(path)
    union_count = int(np.count_nonzero(union))
    core_count = int(np.count_nonzero(core))
    soft_count = int(np.count_nonzero(a_only | b_only))
    return {
        "coreTexels": core_count,
        "softBoundaryTexels": soft_count,
        "unionTexels": union_count,
        "coreOverUnion": round(core_count / union_count, 4) if union_count else 0.0,
        "conflictOverUnion": round(soft_count / union_count, 4) if union_count else 0.0,
    }


def compare_overlay(frame: Image.Image, gold: np.ndarray, predicted: np.ndarray) -> Image.Image:
    base = np.array(frame.convert("RGB"), dtype=np.float32)
    overlay = np.zeros_like(base)
    tp = predicted & gold
    fp = predicted & ~gold
    fn = ~predicted & gold
    overlay[tp] = [80, 255, 80]
    overlay[fp] = [255, 70, 70]
    overlay[fn] = [70, 130, 255]
    active = tp | fp | fn
    base[active] = (base[active] * 0.45) + (overlay[active] * 0.55)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def make_preview_grid(paths: list[Path], output_path: Path) -> None:
    images = [Image.open(path).convert("RGB") for path in paths if path.exists()]
    if not images:
        return
    thumb_width = 360
    thumbs = []
    for image in images:
        ratio = thumb_width / image.width
        thumb = image.resize((thumb_width, int(image.height * ratio)))
        thumbs.append(thumb)
    cols = 2
    rows = math.ceil(len(thumbs) / cols)
    cell_height = max(thumb.height for thumb in thumbs)
    grid = Image.new("RGB", (cols * thumb_width, rows * cell_height), (20, 20, 20))
    for index, thumb in enumerate(thumbs):
        x = (index % cols) * thumb_width
        y = (index // cols) * cell_height
        grid.paste(thumb, (x, y))
    grid.save(output_path)


def validate_inputs(captures: dict[str, CaptureInput], repo_root: Path) -> dict[str, Any]:
    validation: dict[str, Any] = {}
    for label, capture in captures.items():
        frame = load_rgb(capture.frame_path)
        export = load_json(capture.export_path)
        screen_vertices, uvs, indices = export_arrays(export)
        has_clip_w = bool(screen_vertices.ndim == 2 and screen_vertices.shape[1] >= 4)
        display = export.get("display", {})
        face = export.get("face", {})
        label_validation = {
            "capturePairId": capture.capture_pair_id,
            "frameSize": list(frame.size),
            "screenVertices": int(len(screen_vertices)),
            "uvs": int(len(uvs)),
            "indices": int(len(indices)),
            "hasClipW": has_clip_w,
            "triangleVisibilityAvailable": bool(export.get("triangleVisibility")),
            "blendShapesAvailable": bool(export.get("blendShapes", {}).get("available")),
            "annotationFrameClean": bool(export.get("annotationFrameClean")),
            "coordinateSpaceValidated": bool(export.get("coordinateSpaceValidated")),
            "display": display,
            "face": face,
            "masks": {},
        }
        if frame.size != (1179, 2556):
            raise ValueError(f"{label} frame size is {frame.size}, expected 1179x2556")
        if len(screen_vertices) != 1220 or len(uvs) != 1220 or len(indices) != 6912:
            raise ValueError(f"{label} export counts do not match expected ARFace sample counts")
        if not has_clip_w:
            raise ValueError(f"{label} screenVertices do not include clipW/depth field")
        for region in REGIONS:
            mask_path = capture.path / REGION_MASKS[region][label]
            if not mask_path.exists():
                raise FileNotFoundError(mask_path)
            mask = load_mask(mask_path)
            if mask.shape != (frame.height, frame.width):
                raise ValueError(f"{mask_path} shape {mask.shape} does not match frame")
            positive = int(np.count_nonzero(mask))
            ratio = positive / float(mask.size)
            if ratio <= 0.0001 or ratio >= 0.5:
                raise ValueError(f"{mask_path} has suspicious coverage ratio {ratio:.6f}")
            label_validation["masks"][region] = {
                "path": str(mask_path.relative_to(repo_root)),
                "positivePixels": positive,
                "coverageRatio": round(ratio, 6),
            }
        validation[label] = label_validation
    return validation


def decide_region(region: str, same: dict[str, Any], cross: dict[str, Any], overlap: dict[str, Any]) -> str:
    same_iou_ok = same["A_to_A"]["iou"] >= 0.70 and same["B_to_B"]["iou"] >= 0.70
    if region == "cheek":
        cross_signal = (
            cross["A_to_B"]["precision"] >= 0.35
            or cross["B_to_A"]["precision"] >= 0.35
            or overlap["coreOverUnion"] >= 0.20
        )
    else:
        cross_signal = (
            cross["A_to_B"]["precision"] >= 0.45
            or cross["B_to_A"]["precision"] >= 0.45
            or overlap["coreOverUnion"] >= 0.25
        )
    if not same_iou_ok:
        return "fix_projection_first"
    if overlap["unionTexels"] == 0:
        return "mask_or_uv_empty"
    if cross_signal:
        return "continue_signal"
    return "need_more_gold_or_rescope"


def overall_decision(region_decisions: dict[str, str]) -> str:
    if any(value == "fix_projection_first" for value in region_decisions.values()):
        return "fix_projection_first"
    has_cheek = region_decisions.get("cheek") == "continue_signal"
    has_lip_or_eye = (
        region_decisions.get("lip") == "continue_signal"
        or region_decisions.get("eye") == "continue_signal"
    )
    if has_cheek and has_lip_or_eye:
        return "continue"
    if all(value == "need_more_gold_or_rescope" for value in region_decisions.values()):
        return "stop_or_rescope"
    return "need_more_gold"


def write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# E7 Reference UV Atlas Fast Gate",
        "",
        f"- Created: {summary['createdAtUtc']}",
        f"- Overall decision: `{summary['overallDecision']}`",
        f"- UV resolution: `{summary['uvResolution']}`",
        f"- Sample stride: `{summary['sampleStride']}`",
        f"- Render stride: `{summary['renderStride']}`",
        "",
        "## Region Results",
        "",
        "| Region | Decision | A->A IoU | B->B IoU | A->B IoU | B->A IoU | Core/Union |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for region, data in summary["regions"].items():
        lines.append(
            "| {region} | `{decision}` | {aa:.4f} | {bb:.4f} | {ab:.4f} | {ba:.4f} | {core:.4f} |".format(
                region=region,
                decision=data["decision"],
                aa=data["sameFrame"]["A_to_A"]["iou"],
                bb=data["sameFrame"]["B_to_B"]["iou"],
                ab=data["crossFrame"]["A_to_B"]["iou"],
                ba=data["crossFrame"]["B_to_A"]["iou"],
                core=data["uvOverlap"]["coreOverUnion"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This is a fast offline calibration gate, not E7.03 Green evidence.",
            "- `triangleVisibility` and blendshape correction were not available in the current export and were intentionally excluded.",
            "- Runtime sweep should only be proposed if the overall decision is `continue`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    atlas_root = repo_root / "evidence/e7-reference-atlas"
    captures = {
        "A": CaptureInput(
            label="A",
            capture_pair_id="pair_face_20260622T143300Z_01",
            path=atlas_root / "capture_pairs/pair_face_20260622T143300Z_01",
            frame_path=atlas_root / "capture_pairs/pair_face_20260622T143300Z_01/frame.png",
            export_path=atlas_root / "capture_pairs/pair_face_20260622T143300Z_01/arface_export.json",
        ),
        "B": CaptureInput(
            label="B",
            capture_pair_id="pair_face_20260622T143334Z_03",
            path=atlas_root / "capture_pairs/pair_face_20260622T143334Z_03",
            frame_path=atlas_root / "capture_pairs/pair_face_20260622T143334Z_03/frame.png",
            export_path=atlas_root / "capture_pairs/pair_face_20260622T143334Z_03/arface_export.json",
        ),
    }

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_root = args.output or (atlas_root / f"fast-gate-{timestamp}")
    output_root.mkdir(parents=True, exist_ok=True)
    for dirname in ("round_trip", "cross_frame", "uv_overlap", "candidate_preview", "atlases"):
        (output_root / dirname).mkdir(exist_ok=True)

    validation = validate_inputs(captures, repo_root)
    frames = {label: load_rgb(capture.frame_path) for label, capture in captures.items()}
    exports = {label: load_json(capture.export_path) for label, capture in captures.items()}

    summary: dict[str, Any] = {
        "schemaVersion": "e7-fast-uv-atlas-gate-v1",
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "outputRoot": str(output_root.relative_to(repo_root)),
        "uvResolution": args.uv_resolution,
        "sampleStride": args.sample_stride,
        "renderStride": args.render_stride,
        "inputs": validation,
        "regions": {},
        "skipped": {
            "newDeviceCapture": True,
            "unityRnBuild": True,
            "mediaPipeOrFaceParsing": True,
            "runtimeSweep": True,
            "e703GreenDecision": True,
        },
    }

    region_decisions: dict[str, str] = {}

    for region in REGIONS:
        masks = {
            label: load_mask(captures[label].path / REGION_MASKS[region][label])
            for label in captures
        }
        back = {
            label: back_project_mask(
                masks[label],
                exports[label],
                args.uv_resolution,
                args.sample_stride,
            )
            for label in captures
        }
        for label, projection in back.items():
            save_probability(
                output_root / "atlases" / f"{region}_{label}_probability.png",
                projection.probability,
            )
            save_coverage(
                output_root / "atlases" / f"{region}_{label}_coverage.png",
                projection.coverage,
            )

        predictions = {
            "A_to_A": render_atlas_to_screen(
                back["A"].probability,
                exports["A"],
                frames["A"].size,
                threshold=0.5,
                sample_stride=args.render_stride,
            ),
            "B_to_B": render_atlas_to_screen(
                back["B"].probability,
                exports["B"],
                frames["B"].size,
                threshold=0.5,
                sample_stride=args.render_stride,
            ),
            "A_to_B": render_atlas_to_screen(
                back["A"].probability,
                exports["B"],
                frames["B"].size,
                threshold=0.5,
                sample_stride=args.render_stride,
            ),
            "B_to_A": render_atlas_to_screen(
                back["B"].probability,
                exports["A"],
                frames["A"].size,
                threshold=0.5,
                sample_stride=args.render_stride,
            ),
        }

        same_frame = {
            "A_to_A": metrics(predictions["A_to_A"], masks["A"]),
            "B_to_B": metrics(predictions["B_to_B"], masks["B"]),
        }
        cross_frame = {
            "A_to_B": metrics(predictions["A_to_B"], masks["B"]),
            "B_to_A": metrics(predictions["B_to_A"], masks["A"]),
        }

        overlay_paths = [
            output_root / "round_trip" / f"{region}_A_to_A.png",
            output_root / "round_trip" / f"{region}_B_to_B.png",
            output_root / "cross_frame" / f"{region}_A_to_B.png",
            output_root / "cross_frame" / f"{region}_B_to_A.png",
        ]
        compare_overlay(frames["A"], masks["A"], predictions["A_to_A"]).save(overlay_paths[0])
        compare_overlay(frames["B"], masks["B"], predictions["B_to_B"]).save(overlay_paths[1])
        compare_overlay(frames["B"], masks["B"], predictions["A_to_B"]).save(overlay_paths[2])
        compare_overlay(frames["A"], masks["A"], predictions["B_to_A"]).save(overlay_paths[3])

        overlap = save_uv_overlap(
            output_root / "uv_overlap" / f"{region}_uv_overlap.png",
            back["A"].probability,
            back["B"].probability,
            threshold=0.5,
        )
        make_preview_grid(
            overlay_paths,
            output_root / "candidate_preview" / f"{region}_candidate_preview.png",
        )

        region_decision = decide_region(region, same_frame, cross_frame, overlap)
        region_decisions[region] = region_decision
        summary["regions"][region] = {
            "decision": region_decision,
            "sameFrame": same_frame,
            "crossFrame": cross_frame,
            "uvOverlap": overlap,
            "atlasVotes": {
                "A": {
                    "positiveVotes": back["A"].positive_votes,
                    "totalVotes": back["A"].total_votes,
                },
                "B": {
                    "positiveVotes": back["B"].positive_votes,
                    "totalVotes": back["B"].total_votes,
                },
            },
            "artifacts": {
                "roundTrip": [str(path.relative_to(repo_root)) for path in overlay_paths[:2]],
                "crossFrame": [str(path.relative_to(repo_root)) for path in overlay_paths[2:]],
                "uvOverlap": str(
                    (output_root / "uv_overlap" / f"{region}_uv_overlap.png").relative_to(repo_root)
                ),
                "candidatePreview": str(
                    (output_root / "candidate_preview" / f"{region}_candidate_preview.png").relative_to(repo_root)
                ),
            },
        }

    summary["overallDecision"] = overall_decision(region_decisions)
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_summary_md(output_root / "summary.md", summary)
    print(json.dumps({"overallDecision": summary["overallDecision"], "outputRoot": str(output_root)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
