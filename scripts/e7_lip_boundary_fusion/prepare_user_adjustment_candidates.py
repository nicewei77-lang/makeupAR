#!/usr/bin/env python3
"""Generate buildless user-adjustment candidates for E7 lip M1.

This script creates derived masks and overlays only. It does not run device
builds, upload data, store raw camera frames, or claim runtime readiness.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


SCHEMA_VERSION = "e7-lip-user-adjustment-candidates-v0"
REVIEW_SCHEMA_VERSION = "e7-lip-user-adjustment-review-v0"
PARAM_KEYS = ("cornerReach", "upperLipTightness", "lowerLipTightness", "verticalOffset")
LEGACY_PARAM_KEYS = ("tightness", "upperLowerBalance", "cornerShrink")


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    label: str
    params: dict[str, float]


DEFAULT_CANDIDATES = (
    CandidateSpec("ua-00-baseline", "baseline", dict(zip(PARAM_KEYS, (0.0, 0.0, 0.0, 0.0)))),
    CandidateSpec("ua-01-corner-plus-025", "corner +0.25", dict(zip(PARAM_KEYS, (0.25, 0.0, 0.0, 0.0)))),
    CandidateSpec("ua-02-corner-plus-045", "corner +0.45", dict(zip(PARAM_KEYS, (0.45, 0.0, 0.0, 0.0)))),
    CandidateSpec("ua-03-upper-tight-020", "upper tight +0.20", dict(zip(PARAM_KEYS, (0.0, 0.20, 0.0, 0.0)))),
    CandidateSpec("ua-04-upper-tight-035", "upper tight +0.35", dict(zip(PARAM_KEYS, (0.0, 0.35, 0.0, 0.0)))),
    CandidateSpec("ua-05-lower-tight-025", "lower tight +0.25", dict(zip(PARAM_KEYS, (0.0, 0.0, 0.25, 0.0)))),
    CandidateSpec("ua-06-lower-tight-045", "lower tight +0.45", dict(zip(PARAM_KEYS, (0.0, 0.0, 0.45, 0.0)))),
    CandidateSpec("ua-07-vertical-up-015", "vertical -0.15", dict(zip(PARAM_KEYS, (0.0, 0.0, 0.0, -0.15)))),
    CandidateSpec("ua-08-vertical-down-015", "vertical +0.15", dict(zip(PARAM_KEYS, (0.0, 0.0, 0.0, 0.15)))),
    CandidateSpec("ua-09-corner-lower", "corner + lower", dict(zip(PARAM_KEYS, (0.35, 0.0, 0.30, 0.0)))),
    CandidateSpec("ua-10-corner-upper-lower", "corner + both", dict(zip(PARAM_KEYS, (0.35, 0.20, 0.35, 0.0)))),
    CandidateSpec("ua-11-balanced-observed", "observed balanced", dict(zip(PARAM_KEYS, (0.25, 0.20, 0.45, 0.0)))),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare buildless E7 lip user-adjustment candidate masks."
    )
    parser.add_argument("package_dir", type=Path, help="Existing M1 package directory.")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--base-mask", type=Path, default=None)
    parser.add_argument("--frame", type=Path, default=None)
    parser.add_argument("--upper-lip-mask", type=Path, default=None)
    parser.add_argument("--lower-lip-mask", type=Path, default=None)
    parser.add_argument("--inner-mouth-mask", type=Path, default=None)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_path(package_dir: Path, value: str | Path | None) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute() and path.exists():
        return path
    if path.exists():
        return path
    package_relative = package_dir / path
    if package_relative.exists():
        return package_relative
    cwd_relative = Path.cwd() / path
    if cwd_relative.exists():
        return cwd_relative
    return path if path.is_absolute() else cwd_relative


def default_frame_path(package_dir: Path) -> Path | None:
    manifest = package_dir / "input_manifest.json"
    if not manifest.exists():
        return None
    frame_path = load_json(manifest).get("capturePair", {}).get("framePath")
    return resolve_path(package_dir, frame_path)


def load_binary_mask(path: Path, size: tuple[int, int] | None = None) -> np.ndarray:
    image = Image.open(path).convert("L")
    if size is not None and image.size != size:
        raise ValueError(f"mask_size_mismatch:{path}:mask={image.size}:expected={size}")
    return np.asarray(image) > 0


def save_mask(path: Path, mask: np.ndarray) -> None:
    Image.fromarray((mask.astype(np.uint8) * 255), mode="L").save(path)


def dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = max(3, radius * 2 + 1)
    if size % 2 == 0:
        size += 1
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    return np.asarray(image.filter(ImageFilter.MaxFilter(size))) > 0


def erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    size = max(3, radius * 2 + 1)
    if size % 2 == 0:
        size += 1
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    return np.asarray(image.filter(ImageFilter.MinFilter(size))) > 0


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
    }


def centroid_y(mask: np.ndarray) -> float | None:
    ys, _ = np.where(mask)
    if len(ys) == 0:
        return None
    return float(ys.mean())


def shift_mask(mask: np.ndarray, dx: int = 0, dy: int = 0) -> np.ndarray:
    out = np.zeros_like(mask)
    height, width = mask.shape
    src_x0 = max(0, -dx)
    src_x1 = min(width, width - dx)
    src_y0 = max(0, -dy)
    src_y1 = min(height, height - dy)
    dst_x0 = max(0, dx)
    dst_x1 = min(width, width + dx)
    dst_y0 = max(0, dy)
    dst_y1 = min(height, height + dy)
    if src_x0 < src_x1 and src_y0 < src_y1:
        out[dst_y0:dst_y1, dst_x0:dst_x1] = mask[src_y0:src_y1, src_x0:src_x1]
    return out


def split_y_from_support(base: np.ndarray, upper: np.ndarray | None, lower: np.ndarray | None) -> int:
    if upper is not None and np.any(upper) and lower is not None and np.any(lower):
        upper_box = bbox(upper)
        lower_box = bbox(lower)
        return int(round((upper_box["maxY"] + lower_box["minY"]) / 2.0))
    base_box = bbox(base)
    if not base_box["available"]:
        return base.shape[0] // 2
    return int(round((base_box["minY"] + base_box["maxY"]) / 2.0))


def row_mask(shape: tuple[int, int], condition: np.ndarray) -> np.ndarray:
    return np.repeat(condition[:, None], shape[1], axis=1)


def apply_corner_reach(mask: np.ndarray, amount: float, support: np.ndarray | None) -> np.ndarray:
    if amount == 0 or not np.any(mask):
        return mask.copy()
    box = bbox(mask)
    pixels = max(1, int(round(abs(amount) * max(2, box["width"]) * 0.18)))
    if amount > 0:
        expanded = mask.copy()
        for step in range(1, pixels + 1):
            expanded |= shift_mask(mask, dx=step)
            expanded |= shift_mask(mask, dx=-step)
        if support is not None and np.any(support):
            allowed = dilate(support, max(2, pixels + 2))
            expanded &= allowed
        return expanded
    shrunk = mask.copy()
    center_x = (box["minX"] + box["maxX"]) / 2.0
    xs = np.arange(mask.shape[1])
    keep_x = (xs >= box["minX"] + pixels) & (xs <= box["maxX"] - pixels)
    center_band = np.abs(xs - center_x) <= max(1, box["width"] * 0.18)
    keep = keep_x | center_band
    shrunk &= np.repeat(keep[None, :], mask.shape[0], axis=0)
    return shrunk


def apply_upper_tightness(mask: np.ndarray, amount: float, split_y: int, support: np.ndarray | None) -> np.ndarray:
    if amount == 0 or not np.any(mask):
        return mask.copy()
    box = bbox(mask)
    pixels = max(1, int(round(abs(amount) * max(2, box["height"]) * 0.22)))
    ys = np.arange(mask.shape[0])
    upper_rows = ys <= split_y
    adjusted = mask.copy()
    if amount > 0:
        remove_rows = ys < (box["minY"] + pixels)
        adjusted &= ~row_mask(mask.shape, upper_rows & remove_rows)
        return adjusted
    upper_part = mask & row_mask(mask.shape, upper_rows)
    expanded = adjusted.copy()
    for step in range(1, pixels + 1):
        expanded |= shift_mask(upper_part, dy=-step)
    if support is not None and np.any(support):
        expanded &= dilate(support, max(2, pixels + 2))
    return expanded


def apply_lower_tightness(mask: np.ndarray, amount: float, split_y: int, support: np.ndarray | None) -> np.ndarray:
    if amount == 0 or not np.any(mask):
        return mask.copy()
    box = bbox(mask)
    pixels = max(1, int(round(abs(amount) * max(2, box["height"]) * 0.22)))
    ys = np.arange(mask.shape[0])
    lower_rows = ys > split_y
    adjusted = mask.copy()
    if amount > 0:
        remove_rows = ys > (box["maxY"] - pixels)
        adjusted &= ~row_mask(mask.shape, lower_rows & remove_rows)
        return adjusted
    lower_part = mask & row_mask(mask.shape, lower_rows)
    expanded = adjusted.copy()
    for step in range(1, pixels + 1):
        expanded |= shift_mask(lower_part, dy=step)
    if support is not None and np.any(support):
        expanded &= dilate(support, max(2, pixels + 2))
    return expanded


def apply_vertical_offset(mask: np.ndarray, amount: float) -> np.ndarray:
    if amount == 0 or not np.any(mask):
        return mask.copy()
    box = bbox(mask)
    pixels = int(round(amount * max(2, box["height"]) * 0.16))
    return shift_mask(mask, dy=pixels)


def apply_user_adjustment(
    base: np.ndarray,
    params: dict[str, float],
    upper: np.ndarray | None = None,
    lower: np.ndarray | None = None,
    inner: np.ndarray | None = None,
) -> np.ndarray:
    lip_support = None
    if upper is not None and lower is not None:
        lip_support = upper | lower
    split_y = split_y_from_support(base, upper, lower)
    adjusted = apply_corner_reach(base, float(params.get("cornerReach", 0)), lip_support)
    adjusted = apply_upper_tightness(adjusted, float(params.get("upperLipTightness", 0)), split_y, upper)
    adjusted = apply_lower_tightness(adjusted, float(params.get("lowerLipTightness", 0)), split_y, lower)
    adjusted = apply_vertical_offset(adjusted, float(params.get("verticalOffset", 0)))
    if inner is not None and np.any(inner):
        adjusted &= ~inner
    return adjusted


def overlay(frame: Image.Image, mask: np.ndarray) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    active = mask > 0
    base[active] = (base[active] * 0.48) + (np.array([255, 45, 120], dtype=np.float32) * 0.52)
    mask_image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    outline = np.asarray(ImageChops.subtract(mask_image.filter(ImageFilter.MaxFilter(5)), mask_image.filter(ImageFilter.MinFilter(5)))) > 0
    base[outline] = np.array([255, 220, 0], dtype=np.float32)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def metrics(mask: np.ndarray, baseline: np.ndarray, inner: np.ndarray | None = None) -> dict[str, Any]:
    box = bbox(mask)
    base_box = bbox(baseline)
    inner_pixels = int(np.count_nonzero(mask & inner)) if inner is not None else 0
    return {
        "positivePixels": int(np.count_nonzero(mask)),
        "bbox": box,
        "bboxWidthDelta": int(box.get("width", 0) - base_box.get("width", 0)) if box["available"] and base_box["available"] else None,
        "bboxHeightDelta": int(box.get("height", 0) - base_box.get("height", 0)) if box["available"] and base_box["available"] else None,
        "centroidY": centroid_y(mask),
        "innerMouthPositivePixels": inner_pixels,
    }


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def make_contact_sheet(items: list[dict[str, Any]], columns: int = 4) -> Image.Image:
    thumbs: list[Image.Image] = [Image.open(item["overlayPath"]).convert("RGB") for item in items]
    if not thumbs:
        raise ValueError("no_candidates_for_contact_sheet")
    thumb_w = 280
    label_h = 54
    scaled = []
    for item, image in zip(items, thumbs):
        ratio = thumb_w / float(image.width)
        thumb_h = max(1, int(round(image.height * ratio)))
        tile = Image.new("RGB", (thumb_w, thumb_h + label_h), "white")
        resized = image.resize((thumb_w, thumb_h), Image.Resampling.BILINEAR)
        tile.paste(resized, (0, label_h))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 6), item["candidateId"], fill=(20, 20, 20))
        draw.text((8, 26), item["label"], fill=(20, 20, 20))
        scaled.append(tile)
    rows = int(np.ceil(len(scaled) / float(columns)))
    tile_h = max(tile.height for tile in scaled)
    sheet = Image.new("RGB", (columns * thumb_w, rows * tile_h), "white")
    for index, tile in enumerate(scaled):
        x = (index % columns) * thumb_w
        y = (index // columns) * tile_h
        sheet.paste(tile, (x, y))
    return sheet


def build_review_template(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": REVIEW_SCHEMA_VERSION,
        "status": "needs_user_selection",
        "confirmedByUser": False,
        "selectedCandidateId": None,
        "selectedMaskPath": None,
        "params": {key: 0 for key in PARAM_KEYS},
        "observedFixes": [],
        "knownWeaknesses": [],
        "candidateOptions": [
            {
                "candidateId": item["candidateId"],
                "label": item["label"],
                "params": item["params"],
                "maskPath": Path(item["maskPath"]).name,
                "overlayPath": Path(item["overlayPath"]).name,
                "metrics": item["metrics"],
            }
            for item in candidates
        ],
        "legacyParamsNotAccepted": list(LEGACY_PARAM_KEYS),
    }


def main() -> int:
    args = parse_args()
    package_dir = args.package_dir.resolve()
    output_dir = (args.output_dir or package_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    frame_path = args.frame.resolve() if args.frame else default_frame_path(package_dir)
    if frame_path is None or not frame_path.exists():
        raise FileNotFoundError("frame_not_found_use_--frame_or_input_manifest")
    frame = Image.open(frame_path).convert("RGB")
    base_path = (args.base_mask or (package_dir / "lip-tight-auto-v0_mask.png")).resolve()
    base = load_binary_mask(base_path, frame.size)

    upper_path = (args.upper_lip_mask or (package_dir / "face_parsing_upper_lip_mask.png")).resolve()
    lower_path = (args.lower_lip_mask or (package_dir / "face_parsing_lower_lip_mask.png")).resolve()
    inner_path = (args.inner_mouth_mask or (package_dir / "face_parsing_inner_mouth_mask.png")).resolve()
    upper = load_binary_mask(upper_path, frame.size) if upper_path.exists() else None
    lower = load_binary_mask(lower_path, frame.size) if lower_path.exists() else None
    inner = load_binary_mask(inner_path, frame.size) if inner_path.exists() else None

    candidates: list[dict[str, Any]] = []
    for spec in DEFAULT_CANDIDATES:
        adjusted = apply_user_adjustment(base, spec.params, upper, lower, inner)
        name = slug(spec.candidate_id)
        mask_path = output_dir / f"user_adjustment_candidate_{name}_mask.png"
        overlay_path = output_dir / f"user_adjustment_candidate_{name}_overlay.png"
        save_mask(mask_path, adjusted)
        overlay(frame, adjusted).save(overlay_path)
        candidates.append(
            {
                "candidateId": spec.candidate_id,
                "label": spec.label,
                "params": spec.params,
                "maskPath": str(mask_path),
                "overlayPath": str(overlay_path),
                "metrics": metrics(adjusted, base, inner),
            }
        )

    contact_sheet = output_dir / "user_adjustment_contact_sheet.png"
    make_contact_sheet(candidates).save(contact_sheet)
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "createdAtUtc": utc_now(),
        "packageDir": str(package_dir),
        "inputs": {
            "framePath": str(frame_path),
            "baseMaskPath": str(base_path),
            "upperLipMaskPath": str(upper_path) if upper_path.exists() else None,
            "lowerLipMaskPath": str(lower_path) if lower_path.exists() else None,
            "innerMouthMaskPath": str(inner_path) if inner_path.exists() else None,
        },
        "parameterContract": {
            "keys": list(PARAM_KEYS),
            "cornerReach": "+ expands corner reach, - shrinks corner spill",
            "upperLipTightness": "+ tightens upper lip, - adds upper coverage",
            "lowerLipTightness": "+ tightens lower lip, - adds lower coverage",
            "verticalOffset": "image-space + moves down, - moves up",
            "legacyParamsNotAcceptedForUserConfirmed": list(LEGACY_PARAM_KEYS),
        },
        "candidateCount": len(candidates),
        "candidates": candidates,
        "artifacts": {
            "user_adjustment_candidates.json": str(output_dir / "user_adjustment_candidates.json"),
            "user_adjustment_contact_sheet.png": str(contact_sheet),
            "user_adjustment_review_template.json": str(output_dir / "user_adjustment_review_template.json"),
        },
        "limits": {
            "buildlessOnly": True,
            "lipOnly": True,
            "doesNotRunLiveFaceParsingOrCoreMl": True,
            "doesNotUpload": True,
            "doesNotClaimRuntimeReady": True,
            "doesNotClaimE73Green": True,
        },
    }
    write_json(output_dir / "user_adjustment_candidates.json", payload)
    write_json(output_dir / "user_adjustment_review_template.json", build_review_template(candidates))
    print(json.dumps({"outputDir": str(output_dir), "candidateCount": len(candidates)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
