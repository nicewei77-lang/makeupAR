#!/usr/bin/env python3
"""Generate E7 lip inner-fill sample overlays from a generated package.

This is a buildless visual review tool. It does not claim runtime AR quality.
Use `.venv/bin/python` because the repo CV tooling owns Pillow/numpy there.
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
from PIL import Image, ImageChops, ImageDraw, ImageFilter


SCHEMA_VERSION = "e7-lip-inner-fill-samples-v0"
CHECKSUM_MOD = 2_147_483_647
DEFAULT_CANONICAL_UV_MANIFEST = Path(
    "evidence/references/arcore-canonical-face-texture-v1/manifest.json"
)


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    label: str
    inner_fill: float = 0.0
    upper_inner_fill: float = 0.0
    min_hole_ratio: float | None = None


DEFAULT_VARIANTS = (
    VariantSpec("baseline_current", "baseline"),
    VariantSpec("upper_inner_fill_020", "upper inner +0.20", upper_inner_fill=0.20),
    VariantSpec("upper_inner_fill_040", "upper inner +0.40", upper_inner_fill=0.40),
    VariantSpec("upper_inner_fill_060", "upper inner +0.60", upper_inner_fill=0.60),
    VariantSpec("inner_fill_020", "inner all +0.20", inner_fill=0.20),
    VariantSpec("inner_fill_040", "inner all +0.40", inner_fill=0.40),
    VariantSpec(
        "upper_inner_fill_050_gap_guard",
        "upper inner +0.50 gap guard",
        upper_inner_fill=0.50,
        min_hole_ratio=0.58,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate buildless E7 upper-inner-fill sample contact sheets."
    )
    parser.add_argument("--package", type=Path, default=None)
    parser.add_argument("--frame", type=Path, default=None)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("evidence/e7-lip-inner-fill-samples"),
    )
    parser.add_argument(
        "--canonical-uv-manifest",
        type=Path,
        default=DEFAULT_CANONICAL_UV_MANIFEST,
    )
    return parser.parse_args()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def resolve_existing_path(value: str | Path | None, repo_root: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    candidates = [path, repo_root / path]
    for candidate in candidates:
        if candidate.is_absolute() and candidate.exists():
            return candidate
        if candidate.exists():
            return candidate.resolve()
    return None


def latest_generated_package(repo_root: Path) -> Path:
    candidates = sorted(
        repo_root.glob("evidence/e7-lip-generate-server/**/generated_lip_package.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        try:
            package = read_json(candidate)
        except Exception:
            continue
        frame_path = resolve_existing_path(
            package.get("sourceFrameMetadata", {}).get("framePath"),
            repo_root,
        )
        boundary = package.get("lipBoundary2D") or {}
        if frame_path and boundary.get("outerPoints") and boundary.get("innerPoints"):
            return candidate
    raise FileNotFoundError("no_generated_lip_package_with_frame_and_boundary")


def points_from_package(points: list[dict[str, Any]]) -> list[tuple[float, float]]:
    return [(float(point["x"]), float(point["y"])) for point in points]


def point_bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def polygon_mask(
    size: tuple[int, int],
    outer_points: list[tuple[float, float]],
    inner_points: list[tuple[float, float]],
) -> np.ndarray:
    image = Image.new("L", size, 0)
    draw = ImageDraw.Draw(image)
    draw.polygon(outer_points, fill=255)
    if len(inner_points) >= 3:
        draw.polygon(inner_points, fill=0)
    return np.asarray(image) > 0


def inner_hole_mask(
    size: tuple[int, int],
    inner_points: list[tuple[float, float]],
) -> np.ndarray:
    image = Image.new("L", size, 0)
    if len(inner_points) >= 3:
        ImageDraw.Draw(image).polygon(inner_points, fill=255)
    return np.asarray(image) > 0


def adjust_inner_points(
    inner_points: list[tuple[float, float]],
    *,
    inner_fill: float,
    upper_inner_fill: float,
) -> list[tuple[float, float]]:
    if not inner_points:
        return []
    min_x, min_y, max_x, max_y = point_bounds(inner_points)
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    center_x = min_x + width * 0.5
    center_y = min_y + height * 0.5
    adjusted: list[tuple[float, float]] = []
    for x, y in inner_points:
        dx = x - center_x
        dy = y - center_y
        upper_weight = min(1.0, abs(dy) / (height * 0.5)) if dy < 0 else 0.0
        overall_fill = clamp(inner_fill * 0.45, -0.45, 0.65)
        upper_fill = clamp(upper_inner_fill * 0.58 * upper_weight, -0.45, 0.72)
        fill = clamp(overall_fill + upper_fill, -0.6, 0.78)
        if abs(fill) > 0.0001:
            x = center_x + dx * (1 - fill * 0.35)
            y = center_y + dy * (1 - fill)
        adjusted.append((x, y))
    return adjusted


def guarded_inner_points(
    size: tuple[int, int],
    base_inner_points: list[tuple[float, float]],
    *,
    inner_fill: float,
    upper_inner_fill: float,
    min_hole_ratio: float | None,
) -> tuple[list[tuple[float, float]], float]:
    if min_hole_ratio is None:
        return (
            adjust_inner_points(
                base_inner_points,
                inner_fill=inner_fill,
                upper_inner_fill=upper_inner_fill,
            ),
            1.0,
        )

    base_hole = inner_hole_mask(size, base_inner_points)
    base_area = max(1, int(np.count_nonzero(base_hole)))
    best_scale = 0.0
    best_points = base_inner_points
    for scale in np.linspace(1.0, 0.0, 21):
        candidate = adjust_inner_points(
            base_inner_points,
            inner_fill=inner_fill * float(scale),
            upper_inner_fill=upper_inner_fill * float(scale),
        )
        area = int(np.count_nonzero(inner_hole_mask(size, candidate)))
        if area / base_area >= min_hole_ratio:
            best_scale = float(scale)
            best_points = candidate
            break
    return best_points, best_scale


def bbox_from_mask(mask: np.ndarray) -> dict[str, Any]:
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


def crop_box(mask: np.ndarray, padding_ratio: float = 0.72) -> tuple[int, int, int, int]:
    box = bbox_from_mask(mask)
    if not box["available"]:
        return (0, 0, mask.shape[1], mask.shape[0])
    width = box["width"]
    height = box["height"]
    pad = int(round(max(width, height) * padding_ratio))
    left = max(0, box["minX"] - pad)
    top = max(0, box["minY"] - pad)
    right = min(mask.shape[1], box["maxX"] + pad + 1)
    bottom = min(mask.shape[0], box["maxY"] + pad + 1)
    return left, top, right, bottom


def edge_band_ratio(mask: np.ndarray) -> float:
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    outer = np.asarray(image.filter(ImageFilter.MaxFilter(5))) > 0
    inner = np.asarray(image.filter(ImageFilter.MinFilter(5))) > 0
    edge = outer ^ inner
    positive = max(1, int(np.count_nonzero(mask)))
    return float(np.count_nonzero(edge)) / float(positive)


def alpha_checksum(mask: np.ndarray) -> int:
    flat = mask.astype(np.uint8).reshape(-1)
    checksum = 0
    for index, value in enumerate(flat):
        if value:
            checksum = (checksum + ((index + 1) * 255)) % CHECKSUM_MOD
    return int(checksum)


def load_arface_export(
    package: dict[str, Any],
    frame_path: Path,
    repo_root: Path,
) -> dict[str, Any] | None:
    source = package.get("sourceFrameMetadata", {})
    candidates = [
        source.get("arFaceExportPath"),
        frame_path.parent / "arface_export.json",
    ]
    for candidate in candidates:
        resolved = resolve_existing_path(candidate, repo_root)
        if resolved and resolved.exists():
            return read_json(resolved)
    return None


def barycentric(
    px: float,
    py: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    cx: float,
    cy: float,
) -> tuple[float, float, float] | None:
    denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(denominator) < 1e-6:
        return None
    w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator
    w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator
    w2 = 1.0 - w0 - w1
    if w0 < -1e-5 or w1 < -1e-5 or w2 < -1e-5:
        return None
    return w0, w1, w2


def interpolate_uv(
    weights: tuple[float, float, float],
    triangle_uvs: list[list[float]],
    triangle_screen: list[list[float]],
) -> tuple[float, float]:
    clip_w = [
        vertex[3] if len(vertex) > 3 and abs(vertex[3]) >= 1e-6 else 1.0
        for vertex in triangle_screen
    ]
    inv_w = [1.0 / value for value in clip_w]
    denominator = (
        weights[0] * inv_w[0] + weights[1] * inv_w[1] + weights[2] * inv_w[2]
    )
    if abs(denominator) < 1e-6:
        denominator = 1.0
    u = (
        weights[0] * triangle_uvs[0][0] * inv_w[0]
        + weights[1] * triangle_uvs[1][0] * inv_w[1]
        + weights[2] * triangle_uvs[2][0] * inv_w[2]
    ) / denominator
    v = (
        weights[0] * triangle_uvs[0][1] * inv_w[0]
        + weights[1] * triangle_uvs[1][1] * inv_w[1]
        + weights[2] * triangle_uvs[2][1] * inv_w[2]
    ) / denominator
    return clamp(u, 0.0, 1.0), clamp(v, 0.0, 1.0)


def project_screen_point_to_uv(
    point: tuple[float, float],
    arface_export: dict[str, Any],
) -> tuple[float, float] | None:
    screen_vertices = arface_export.get("screenVertices") or []
    uvs = arface_export.get("uvs") or []
    indices = arface_export.get("indices") or []
    for index in range(0, len(indices) - 2, 3):
        triangle = [indices[index], indices[index + 1], indices[index + 2]]
        if any(
            vertex_index < 0
            or vertex_index >= len(screen_vertices)
            or vertex_index >= len(uvs)
            for vertex_index in triangle
        ):
            continue
        tri_screen = [screen_vertices[vertex_index] for vertex_index in triangle]
        weights = barycentric(
            point[0],
            point[1],
            tri_screen[0][0],
            tri_screen[0][1],
            tri_screen[1][0],
            tri_screen[1][1],
            tri_screen[2][0],
            tri_screen[2][1],
        )
        if weights is None:
            continue
        return interpolate_uv(weights, [uvs[vertex_index] for vertex_index in triangle], tri_screen)
    return None


def project_boundary_to_uv(
    points: list[tuple[float, float]],
    arface_export: dict[str, Any],
) -> list[tuple[float, float]] | None:
    uv_points: list[tuple[float, float]] = []
    for point in points:
        uv = project_screen_point_to_uv(point, arface_export)
        if uv is None:
            return None
        uv_points.append(uv)
    return uv_points if len(uv_points) >= 3 else None


def uv_mask_from_boundary(
    outer_points: list[tuple[float, float]],
    inner_points: list[tuple[float, float]],
    arface_export: dict[str, Any] | None,
    resolution: int,
) -> np.ndarray | None:
    if arface_export is None:
        return None
    outer_uv = project_boundary_to_uv(outer_points, arface_export)
    inner_uv = project_boundary_to_uv(inner_points, arface_export)
    if outer_uv is None:
        return None
    image = Image.new("L", (resolution, resolution), 0)
    draw = ImageDraw.Draw(image)
    draw.polygon(
        [(u * (resolution - 1), v * (resolution - 1)) for u, v in outer_uv],
        fill=255,
    )
    if inner_uv:
        draw.polygon(
            [(u * (resolution - 1), v * (resolution - 1)) for u, v in inner_uv],
            fill=0,
        )
    return np.asarray(image)


def mesh_round_trip_alpha_crop(
    arface_export: dict[str, Any],
    uv_alpha: np.ndarray,
    crop: tuple[int, int, int, int],
) -> np.ndarray:
    left, top, right, bottom = crop
    width = max(0, right - left)
    height = max(0, bottom - top)
    output = np.zeros((height, width), dtype=np.uint8)
    if width <= 0 or height <= 0:
        return output
    resolution = uv_alpha.shape[0]
    screen_vertices = arface_export.get("screenVertices") or []
    uvs = arface_export.get("uvs") or []
    indices = arface_export.get("indices") or []
    for index in range(0, len(indices) - 2, 3):
        triangle = [indices[index], indices[index + 1], indices[index + 2]]
        if any(
            vertex_index < 0
            or vertex_index >= len(screen_vertices)
            or vertex_index >= len(uvs)
            for vertex_index in triangle
        ):
            continue
        tri_screen = [screen_vertices[vertex_index] for vertex_index in triangle]
        min_x = max(left, int(math.floor(min(vertex[0] for vertex in tri_screen))))
        max_x = min(right - 1, int(math.ceil(max(vertex[0] for vertex in tri_screen))))
        min_y = max(top, int(math.floor(min(vertex[1] for vertex in tri_screen))))
        max_y = min(bottom - 1, int(math.ceil(max(vertex[1] for vertex in tri_screen))))
        if max_x < min_x or max_y < min_y:
            continue
        tri_uv = [uvs[vertex_index] for vertex_index in triangle]
        for y in range(min_y, max_y + 1):
            row = y - top
            for x in range(min_x, max_x + 1):
                weights = barycentric(
                    x + 0.5,
                    y + 0.5,
                    tri_screen[0][0],
                    tri_screen[0][1],
                    tri_screen[1][0],
                    tri_screen[1][1],
                    tri_screen[2][0],
                    tri_screen[2][1],
                )
                if weights is None:
                    continue
                u, v = interpolate_uv(weights, tri_uv, tri_screen)
                column = int(round(u * (resolution - 1)))
                uv_row = int(round(v * (resolution - 1)))
                alpha = int(uv_alpha[uv_row, column])
                if alpha > output[row, x - left]:
                    output[row, x - left] = alpha
    return output


def mesh_overlay_crop(
    frame: Image.Image,
    round_trip_alpha: np.ndarray,
    crop: tuple[int, int, int, int],
    inner_points: list[tuple[float, float]],
) -> Image.Image:
    left, top, right, bottom = crop
    base = np.asarray(frame.crop(crop).convert("RGB"), dtype=np.float32)
    alpha = round_trip_alpha.astype(np.float32) / 255.0
    active = alpha > 0.03
    tint = np.array([255, 45, 120], dtype=np.float32)
    base[active] = base[active] * (1 - alpha[active, None] * 0.55) + tint * (
        alpha[active, None] * 0.55
    )
    alpha_image = Image.fromarray(round_trip_alpha, mode="L")
    edge = np.asarray(
        ImageChops.subtract(
            alpha_image.filter(ImageFilter.MaxFilter(5)),
            alpha_image.filter(ImageFilter.MinFilter(5)),
        )
    ) > 0
    base[edge] = np.array([255, 220, 40], dtype=np.float32)
    output = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(output)
    if len(inner_points) >= 3:
        shifted = [(x - left, y - top) for x, y in inner_points]
        draw.line(shifted + [shifted[0]], fill=(55, 235, 255), width=3)
    return output


def lower_lip_growth_ratio(
    candidate: np.ndarray,
    baseline: np.ndarray,
    center_y: float,
) -> float:
    rows = np.arange(candidate.shape[0])[:, None]
    lower_half = rows >= center_y
    base_count = max(1, int(np.count_nonzero(baseline & lower_half)))
    candidate_count = int(np.count_nonzero(candidate & lower_half))
    return float(candidate_count) / float(base_count)


def variant_metrics(
    candidate_mask: np.ndarray,
    baseline_mask: np.ndarray,
    base_inner_hole: np.ndarray,
    candidate_inner_hole: np.ndarray,
    inner_center_y: float,
    package: dict[str, Any],
) -> dict[str, Any]:
    base_hole_area = max(1, int(np.count_nonzero(base_inner_hole)))
    candidate_hole_area = int(np.count_nonzero(candidate_inner_hole))
    upper_rows = np.arange(candidate_mask.shape[0])[:, None] < inner_center_y
    upper_fill = candidate_mask & base_inner_hole & upper_rows
    return {
        "sampleSpace": "frame_image_pixel_top_left",
        "uvResolution": package.get("uvCoverageMetadata", {}).get("uvResolution"),
        "positivePixels": int(np.count_nonzero(candidate_mask)),
        "positivePixelsDelta": int(
            np.count_nonzero(candidate_mask) - np.count_nonzero(baseline_mask)
        ),
        "alphaBoundingBoxPixels": bbox_from_mask(candidate_mask),
        "edgeBandRatio": edge_band_ratio(candidate_mask),
        "innerHoleAreaPixels": candidate_hole_area,
        "innerHoleAreaDeltaPixels": candidate_hole_area - base_hole_area,
        "mouthGapRemainingRatio": float(candidate_hole_area) / float(base_hole_area),
        "upperInnerFilledPixels": int(np.count_nonzero(upper_fill)),
        "lowerLipGrowthRatio": lower_lip_growth_ratio(
            candidate_mask,
            baseline_mask,
            inner_center_y,
        ),
        "alphaChecksum": alpha_checksum(candidate_mask),
        "previewVsUvRoundTripDelta": package.get("uvCoverageMetadata", {}).get(
            "previewVsUvRoundTripDelta"
        ),
    }


def overlay_image(
    frame: Image.Image,
    mask: np.ndarray,
    inner_points: list[tuple[float, float]],
) -> Image.Image:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    active = mask > 0
    base[active] = base[active] * 0.5 + np.array([255, 45, 120], dtype=np.float32) * 0.5
    mask_image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    outline = np.asarray(
        ImageChops.subtract(
            mask_image.filter(ImageFilter.MaxFilter(5)),
            mask_image.filter(ImageFilter.MinFilter(5)),
        )
    ) > 0
    base[outline] = np.array([255, 230, 40], dtype=np.float32)
    output = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(output)
    if len(inner_points) >= 3:
        draw.line(inner_points + [inner_points[0]], fill=(60, 240, 255), width=3)
    return output


def save_contact_sheet(items: list[dict[str, Any]], path: Path) -> None:
    thumb_w = 360
    label_h = 62
    columns = 3
    tiles: list[Image.Image] = []
    for item in items:
        image = Image.open(
            item.get("meshLipCropOverlayPath") or item["lipCropOverlayPath"]
        ).convert("RGB")
        ratio = thumb_w / float(image.width)
        thumb_h = max(1, int(round(image.height * ratio)))
        tile = Image.new("RGB", (thumb_w, thumb_h + label_h), "white")
        tile.paste(image.resize((thumb_w, thumb_h), Image.Resampling.BILINEAR), (0, label_h))
        draw = ImageDraw.Draw(tile)
        draw.text((10, 8), item["variantId"], fill=(20, 20, 20))
        draw.text((10, 30), item["label"], fill=(20, 20, 20))
        tiles.append(tile)
    rows = math.ceil(len(tiles) / columns)
    tile_h = max(tile.height for tile in tiles)
    sheet = Image.new("RGB", (columns * thumb_w, rows * tile_h), "white")
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % columns) * thumb_w, (index // columns) * tile_h))
    sheet.save(path)


def make_summary(
    *,
    output_dir: Path,
    package_path: Path,
    frame_path: Path,
    canonical_manifest: dict[str, Any] | None,
    items: list[dict[str, Any]],
) -> str:
    lines = [
        "# E7 Lip Inner Fill Samples",
        "",
        "Buildless visual samples for upper-inner lip coverage review.",
        "The contact sheet uses ARFace UV mesh round-trip crops when arface_export.json is available.",
        "",
        "## Inputs",
        "",
        f"- Package: `{package_path}`",
        f"- Frame: `{frame_path}`",
    ]
    if canonical_manifest:
        lines.extend(
            [
                "- Canonical UV reference:",
                f"  - assetId: `{canonical_manifest.get('assetId')}`",
                f"  - sha256: `{canonical_manifest.get('sha256')}`",
                f"  - size: `{canonical_manifest.get('width')}x{canonical_manifest.get('height')}`",
            ]
        )
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Contact sheet: `{output_dir / 'contact_sheet.png'}`",
            f"- Metrics: `{output_dir / 'metrics.json'}`",
            "",
            "## Review Focus",
            "",
            "- Does the upper inner lip gap look more filled?",
            "- Does the mouth/teeth gap remain believable?",
            "- Does lower lip thickness stay bounded?",
            "- Does the visible edge stay clean enough for app promotion?",
            "",
            "## Variants",
            "",
        ]
    )
    for item in items:
        metrics = item["metrics"]
        mesh = "mesh" if metrics.get("meshRoundTripAvailable") else "frame"
        lines.append(
            f"- `{item['variantId']}` ({mesh}): upperInnerFilledPixels={metrics['upperInnerFilledPixels']}, "
            f"mouthGapRemainingRatio={metrics['mouthGapRemainingRatio']:.3f}, "
            f"lowerLipGrowthRatio={metrics['lowerLipGrowthRatio']:.3f}, "
            f"positivePixelsDelta={metrics['positivePixelsDelta']}"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "These are buildless samples. Mesh round-trip crops are closer to AR runtime than raw frame-space polygons, but they are still not iPhone runtime proof.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    package_path = args.package.resolve() if args.package else latest_generated_package(repo_root)
    package = read_json(package_path)

    frame_path = args.frame or resolve_existing_path(
        package.get("sourceFrameMetadata", {}).get("framePath"),
        repo_root,
    )
    if frame_path is None or not frame_path.exists():
        raise FileNotFoundError(f"frame_not_found:{frame_path}")
    frame = Image.open(frame_path).convert("RGB")
    size = frame.size
    arface_export = load_arface_export(package, frame_path, repo_root)
    uv_resolution = int(
        package.get("uvCoverageMetadata", {}).get("uvResolution")
        or package.get("runtimeApplyPayload", {}).get("maskTextureWidth")
        or 512
    )

    boundary = package.get("lipBoundary2D") or {}
    outer_points = points_from_package(boundary.get("outerPoints") or [])
    inner_points = points_from_package(boundary.get("innerPoints") or [])
    if len(outer_points) < 3 or len(inner_points) < 3:
        raise ValueError("package_lip_boundary_missing_outer_or_inner_points")

    min_x, min_y, max_x, max_y = point_bounds(inner_points)
    inner_center_y = min_y + (max_y - min_y) * 0.5
    baseline_mask = polygon_mask(size, outer_points, inner_points)
    baseline_inner_hole = inner_hole_mask(size, inner_points)
    crop = crop_box(baseline_mask)

    provider_slug = str(package.get("provider") or "unknown").replace("/", "-")
    run_dir = args.output_root / f"{provider_slug}-inner-fill-{utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    canonical_manifest_path = args.canonical_uv_manifest
    canonical_manifest = (
        read_json(canonical_manifest_path)
        if canonical_manifest_path.exists()
        else None
    )

    items: list[dict[str, Any]] = []
    for variant in DEFAULT_VARIANTS:
        adjusted_inner_points, applied_scale = guarded_inner_points(
            size,
            inner_points,
            inner_fill=variant.inner_fill,
            upper_inner_fill=variant.upper_inner_fill,
            min_hole_ratio=variant.min_hole_ratio,
        )
        candidate_mask = polygon_mask(size, outer_points, adjusted_inner_points)
        candidate_inner_hole = inner_hole_mask(size, adjusted_inner_points)
        overlay = overlay_image(frame, candidate_mask, adjusted_inner_points)
        mask_image = Image.fromarray((candidate_mask.astype(np.uint8) * 255), mode="L")

        overlay_path = run_dir / f"{variant.variant_id}_overlay.png"
        lip_crop_overlay_path = run_dir / f"{variant.variant_id}_lip_crop_overlay.png"
        mask_crop_path = run_dir / f"{variant.variant_id}_mask_crop.png"
        overlay.save(overlay_path)
        overlay.crop(crop).save(lip_crop_overlay_path)
        mask_image.crop(crop).save(mask_crop_path)
        mesh_overlay_path: Path | None = None
        mesh_lip_crop_overlay_path: Path | None = None
        mesh_metrics: dict[str, Any] = {
            "meshRoundTripAvailable": False,
            "meshRoundTripReason": "arface_export_missing",
        }
        uv_alpha = uv_mask_from_boundary(
            outer_points,
            adjusted_inner_points,
            arface_export,
            uv_resolution,
        )
        if arface_export is not None and uv_alpha is not None:
            round_trip_alpha = mesh_round_trip_alpha_crop(
                arface_export,
                uv_alpha,
                crop,
            )
            mesh_lip_crop = mesh_overlay_crop(
                frame,
                round_trip_alpha,
                crop,
                adjusted_inner_points,
            )
            mesh_lip_crop_overlay_path = (
                run_dir / f"{variant.variant_id}_mesh_lip_crop_overlay.png"
            )
            mesh_lip_crop.save(mesh_lip_crop_overlay_path)
            full_mesh_overlay = frame.copy()
            full_mesh_overlay.paste(mesh_lip_crop, (crop[0], crop[1]))
            mesh_overlay_path = run_dir / f"{variant.variant_id}_mesh_overlay.png"
            full_mesh_overlay.save(mesh_overlay_path)
            mesh_metrics = {
                "meshRoundTripAvailable": True,
                "projectionKind": "arface_uv_mesh_round_trip",
                "uvResolution": uv_resolution,
                "uvPositiveTexels": int(np.count_nonzero(uv_alpha > 8)),
                "uvAlphaChecksum": alpha_checksum(uv_alpha > 8),
                "meshCropPositivePixels": int(np.count_nonzero(round_trip_alpha > 8)),
            }
        elif arface_export is not None:
            mesh_metrics = {
                "meshRoundTripAvailable": False,
                "meshRoundTripReason": "boundary_points_failed_to_project_to_uv",
            }

        item = {
            "variantId": variant.variant_id,
            "label": variant.label,
            "params": {
                "innerFill": variant.inner_fill,
                "upperInnerFill": variant.upper_inner_fill,
                "minHoleRatio": variant.min_hole_ratio,
                "appliedGuardScale": applied_scale,
            },
            "overlayPath": str(overlay_path),
            "lipCropOverlayPath": str(lip_crop_overlay_path),
            "maskCropPath": str(mask_crop_path),
            "meshOverlayPath": str(mesh_overlay_path) if mesh_overlay_path else None,
            "meshLipCropOverlayPath": str(mesh_lip_crop_overlay_path)
            if mesh_lip_crop_overlay_path
            else None,
            "metrics": variant_metrics(
                candidate_mask,
                baseline_mask,
                baseline_inner_hole,
                candidate_inner_hole,
                inner_center_y,
                package,
            )
            | mesh_metrics,
        }
        items.append(item)

    save_contact_sheet(items, run_dir / "contact_sheet.png")
    metrics = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "packagePath": str(package_path),
        "framePath": str(frame_path),
        "frameSize": {"width": size[0], "height": size[1]},
        "canonicalUvReference": canonical_manifest,
        "cropBox": {"left": crop[0], "top": crop[1], "right": crop[2], "bottom": crop[3]},
        "variants": items,
        "qualityBoundary": "Buildless frame-space sample. Not runtime AR proof.",
    }
    write_json(run_dir / "metrics.json", metrics)
    (run_dir / "summary.md").write_text(
        make_summary(
            output_dir=run_dir,
            package_path=package_path,
            frame_path=frame_path,
            canonical_manifest=canonical_manifest,
            items=items,
        ),
        encoding="utf-8",
    )

    print(json.dumps({"outputDir": str(run_dir), "variantCount": len(items)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
