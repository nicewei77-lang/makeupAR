#!/usr/bin/env python3
"""Analyze user cheek reference art against Apple Vision landmarks.

This helper keeps the Apple Vision call in Swift, then uses the dumped JSON to
measure where the reference blush sits relative to eyes, nose, lips, and face
width. The measurements are buildless evidence for the cheek generator.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


SHAPE_ORDER = (
    ("daily", "cheek-daily-mask-v1"),
    ("lovely", "cheek-lovely-mask-v1"),
    ("sunkissed1", "cheek-sunkissed-mask1-v1"),
    ("sunkissed2", "cheek-sunkissed-mask2-v1"),
    ("under_eye", "cheek-under-eye-mask-v1"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract cheek reference panels and summarize Apple Vision anchor ratios."
    )
    parser.add_argument("--reference-composite", type=Path, required=True)
    parser.add_argument(
        "--capture-frame",
        type=Path,
        default=Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png"),
    )
    parser.add_argument(
        "--vision-json",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-vision-reference/landmarks.json"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-vision-reference"),
    )
    return parser.parse_args()


def pink_mask(image: Image.Image) -> np.ndarray:
    rgba = np.asarray(image.convert("RGBA"), dtype=np.int16)
    r = rgba[..., 0]
    g = rgba[..., 1]
    b = rgba[..., 2]
    a = rgba[..., 3]
    return (
        (a > 180)
        & (r > 185)
        & (g >= 55)
        & (g <= 175)
        & (b >= 75)
        & (b <= 190)
        & (r > g + 38)
        & (r > b + 18)
    )


def iter_components(active: np.ndarray, min_pixels: int = 80) -> list[dict[str, Any]]:
    height, width = active.shape
    visited = np.zeros(active.shape, dtype=bool)
    components: list[dict[str, Any]] = []
    neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
    ys, xs = np.nonzero(active)
    for start_y, start_x in zip(ys.tolist(), xs.tolist()):
        if visited[start_y, start_x]:
            continue
        queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
        visited[start_y, start_x] = True
        pixels: list[tuple[int, int]] = []
        while queue:
            y, x = queue.popleft()
            pixels.append((y, x))
            for dy, dx in neighbors:
                ny = y + dy
                nx = x + dx
                if 0 <= ny < height and 0 <= nx < width and active[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
        if len(pixels) < min_pixels:
            continue
        rows, cols = zip(*pixels)
        rows_np = np.asarray(rows)
        cols_np = np.asarray(cols)
        components.append(
            {
                "cx": float(cols_np.mean()),
                "cy": float(rows_np.mean()),
                "left": int(cols_np.min()),
                "top": int(rows_np.min()),
                "right": int(cols_np.max()),
                "bottom": int(rows_np.max()),
                "width": int(cols_np.max() - cols_np.min() + 1),
                "height": int(rows_np.max() - rows_np.min() + 1),
                "pixels": int(len(pixels)),
            }
        )
    return components


def group_components_by_row(components: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    sorted_components = sorted(components, key=lambda item: float(item["cy"]))
    rows: list[list[dict[str, Any]]] = []
    for component in sorted_components:
        if not rows:
            rows.append([component])
            continue
        row_cy = float(np.mean([float(item["cy"]) for item in rows[-1]]))
        if abs(float(component["cy"]) - row_cy) > 95:
            rows.append([component])
        else:
            rows[-1].append(component)
    return rows


def bbox_union(components: list[dict[str, Any]]) -> dict[str, Any]:
    left = min(int(item["left"]) for item in components)
    top = min(int(item["top"]) for item in components)
    right = max(int(item["right"]) for item in components)
    bottom = max(int(item["bottom"]) for item in components)
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left + 1,
        "height": bottom - top + 1,
        "cx": float(np.mean([float(item["cx"]) for item in components])),
        "cy": float(np.mean([float(item["cy"]) for item in components])),
        "pixels": int(sum(int(item["pixels"]) for item in components)),
    }


def select_shape_components(
    shape_name: str,
    components: list[dict[str, Any]],
    image_width: int,
) -> list[dict[str, Any]]:
    center_x = image_width * 0.5
    side_components = [
        item
        for item in components
        if int(item["pixels"]) >= 1100
        and int(item["width"]) >= 32
        and abs(float(item["cx"]) - center_x) >= image_width * 0.095
    ]
    if shape_name in ("daily", "lovely", "under_eye"):
        return sorted(side_components, key=lambda item: float(item["cx"]))[:2]

    if shape_name == "sunkissed1":
        center_components = [
            item
            for item in components
            if int(item["pixels"]) >= 850
            and int(item["width"]) >= 28
            and abs(float(item["cx"]) - center_x) < image_width * 0.095
        ]
        selected = sorted(side_components, key=lambda item: int(item["pixels"]), reverse=True)[:2]
        selected.extend(sorted(center_components, key=lambda item: int(item["pixels"]), reverse=True)[:1])
        return sorted(selected, key=lambda item: float(item["cx"]))

    if shape_name == "sunkissed2":
        wide_components = [
            item
            for item in components
            if int(item["pixels"]) >= 1800 and int(item["width"]) >= image_width * 0.28
        ]
        if wide_components:
            return [max(wide_components, key=lambda item: int(item["pixels"]))]

    return sorted(components, key=lambda item: int(item["pixels"]), reverse=True)[:2]


def crop_panels(reference: Image.Image, output_dir: Path) -> list[dict[str, Any]]:
    mask = pink_mask(reference)
    components = iter_components(mask)
    rows = group_components_by_row(components)
    if len(rows) < len(SHAPE_ORDER):
        raise RuntimeError(f"Expected at least {len(SHAPE_ORDER)} pink rows, got {len(rows)}")

    panel_dir = output_dir / "panels"
    panel_dir.mkdir(parents=True, exist_ok=True)
    panels: list[dict[str, Any]] = []
    width, height = reference.size
    for (shape_name, mask_id), row in zip(SHAPE_ORDER, rows[: len(SHAPE_ORDER)]):
        row = select_shape_components(shape_name, row, width)
        row_box = bbox_union(row)
        crop_left = max(0, int(row_box["left"]) - 42)
        crop_right = min(width, int(row_box["right"]) + 42)
        crop_top = max(0, int(row_box["top"]) - 70)
        crop_bottom = min(height, int(row_box["bottom"]) + 100)
        crop_box = (crop_left, crop_top, crop_right + 1, crop_bottom + 1)
        crop = reference.crop(crop_box).convert("RGB")
        crop_path = panel_dir / f"{shape_name}_reference_crop.png"
        crop.save(crop_path)

        selected_mask = np.zeros_like(mask)
        for component in row:
            selected_mask[
                int(component["top"]) : int(component["bottom"]) + 1,
                int(component["left"]) : int(component["right"]) + 1,
            ] = mask[
                int(component["top"]) : int(component["bottom"]) + 1,
                int(component["left"]) : int(component["right"]) + 1,
            ]
        local_mask = Image.fromarray(
            (selected_mask[crop_top : crop_bottom + 1, crop_left : crop_right + 1] * 255).astype(np.uint8),
            mode="L",
        )
        local_mask = local_mask.filter(ImageFilter.GaussianBlur(radius=0.65))
        mask_path = panel_dir / f"{shape_name}_pink_mask.png"
        local_mask.save(mask_path)

        local_components = []
        for component in row:
            local = dict(component)
            for x_key in ("left", "right", "cx"):
                local[x_key] = float(local[x_key]) - crop_left
            for y_key in ("top", "bottom", "cy"):
                local[y_key] = float(local[y_key]) - crop_top
            local_components.append(local)

        panels.append(
            {
                "shape": shape_name,
                "maskId": mask_id,
                "cropPath": str(crop_path),
                "pinkMaskPath": str(mask_path),
                "cropBoxInComposite": {
                    "left": crop_left,
                    "top": crop_top,
                    "right": crop_right,
                    "bottom": crop_bottom,
                    "width": crop_right - crop_left + 1,
                    "height": crop_bottom - crop_top + 1,
                },
                "pinkComponents": local_components,
                "pinkGlobalBox": row_box,
            }
        )
    return panels


def load_vision_faces(vision_json_path: Path) -> dict[str, dict[str, Any]]:
    if not vision_json_path.exists():
        return {}
    data = json.loads(vision_json_path.read_text(encoding="utf-8"))
    records: dict[str, dict[str, Any]] = {}
    for image_record in data.get("images", []):
        if image_record.get("status") != "ok":
            continue
        faces = image_record.get("faces", [])
        if not faces:
            continue
        face = max(faces, key=lambda item: float(item.get("confidence", 0.0)))
        records[str(image_record.get("inputPath"))] = {
            "image": image_record,
            "face": face,
        }
    return records


def points_top_left(region: dict[str, Any], height: float) -> list[dict[str, float]]:
    points = region.get("points", [])
    if not points:
        return []
    raw = [(float(point["x"]), float(point["y"])) for point in points]
    ys = [item[1] for item in raw]
    return [{"x": x, "y": height - y} for x, y in raw]


def bbox_from_points(points: list[dict[str, float]]) -> dict[str, float]:
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    return {
        "left": min(xs),
        "top": min(ys),
        "right": max(xs),
        "bottom": max(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
        "centerX": (min(xs) + max(xs)) * 0.5,
        "centerY": (min(ys) + max(ys)) * 0.5,
    }


def face_geometry(face_record: dict[str, Any], image_height: float) -> dict[str, Any] | None:
    face = face_record["face"]
    landmarks = face.get("landmarks", {})
    required = ["leftEye", "rightEye", "nose", "outerLips"]
    if not all(name in landmarks for name in required):
        return None

    converted: dict[str, dict[str, Any]] = {}
    all_points: list[dict[str, float]] = []
    for name, region in landmarks.items():
        points = points_top_left(region, image_height)
        if points:
            converted[name] = {
                "points": points,
                "bbox": bbox_from_points(points),
                "pointCount": int(region.get("pointCount", len(points))),
            }
            all_points.extend(points)

    if not all_points:
        return None

    eyes = converted["leftEye"]["points"] + converted["rightEye"]["points"]
    face_box = bbox_from_points(all_points)
    eye_box = bbox_from_points(eyes)
    nose_box = converted["nose"]["bbox"]
    lip_box = converted["outerLips"]["bbox"]
    face_width = max(face_box["width"], 1.0)
    face_height = max(face_box["height"], 1.0)
    return {
        "faceBox": face_box,
        "eyeBox": eye_box,
        "noseBox": nose_box,
        "lipBox": lip_box,
        "faceCenterX": face_box["centerX"],
        "eyeCenterY": eye_box["centerY"],
        "noseCenterX": nose_box["centerX"],
        "noseCenterY": nose_box["centerY"],
        "lipCenterY": lip_box["centerY"],
        "faceWidth": face_width,
        "faceHeight": face_height,
        "landmarks": converted,
    }


def component_side(component: dict[str, Any], geometry: dict[str, Any]) -> str:
    cx = float(component["cx"])
    center_x = float(geometry["faceCenterX"])
    deadzone = float(geometry["faceWidth"]) * 0.09
    if cx < center_x - deadzone:
        return "left"
    if cx > center_x + deadzone:
        return "right"
    return "center"


def summarize_panel(panel: dict[str, Any], face_record: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(panel)
    if face_record is None:
        result["visionStatus"] = "missing"
        return result
    image_height = float(face_record["image"]["height"])
    geometry = face_geometry(face_record, image_height)
    if geometry is None:
        result["visionStatus"] = "landmarks_missing"
        return result

    return apply_geometry_to_panel(result, geometry, "ok")


def apply_geometry_to_panel(
    result: dict[str, Any],
    geometry: dict[str, Any],
    vision_status: str,
) -> dict[str, Any]:

    components = []
    for component in result["pinkComponents"]:
        side = component_side(component, geometry)
        cx = float(component["cx"])
        cy = float(component["cy"])
        face_width = float(geometry["faceWidth"])
        face_height = float(geometry["faceHeight"])
        eye_to_nose = max(float(geometry["noseCenterY"]) - float(geometry["eyeCenterY"]), 1.0)
        components.append(
            {
                **component,
                "side": side,
                "xFromFaceCenterPerFaceWidth": round((cx - float(geometry["faceCenterX"])) / face_width, 4),
                "yFromEyeCenterPerFaceHeight": round((cy - float(geometry["eyeCenterY"])) / face_height, 4),
                "yFromEyeToNose": round((cy - float(geometry["eyeCenterY"])) / eye_to_nose, 4),
                "widthPerFaceWidth": round(float(component["width"]) / face_width, 4),
                "heightPerFaceHeight": round(float(component["height"]) / face_height, 4),
            }
        )

    result["visionStatus"] = vision_status
    result["visionGeometry"] = {
        key: round_dict_values(value) if isinstance(value, dict) else round(float(value), 4)
        for key, value in geometry.items()
        if key != "landmarks"
    }
    result["pinkComponents"] = components
    return result


def offset_geometry(geometry: dict[str, Any], dx: float, dy: float) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in geometry.items():
        if key == "landmarks":
            continue
        if isinstance(value, dict):
            adjusted = dict(value)
            for x_key in ("left", "right", "centerX"):
                if x_key in adjusted:
                    adjusted[x_key] = float(adjusted[x_key]) + dx
            for y_key in ("top", "bottom", "centerY"):
                if y_key in adjusted:
                    adjusted[y_key] = float(adjusted[y_key]) + dy
            output[key] = adjusted
        else:
            output[key] = value
    for x_key in ("faceCenterX", "noseCenterX"):
        if x_key in output:
            output[x_key] = float(output[x_key]) + dx
    for y_key in ("eyeCenterY", "noseCenterY", "lipCenterY"):
        if y_key in output:
            output[y_key] = float(output[y_key]) + dy
    return output


def median_local_geometry(panel_summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    geometries: list[dict[str, Any]] = []
    for panel in panel_summaries:
        if panel.get("visionStatus") != "ok" or "visionGeometry" not in panel:
            continue
        geometries.append(panel["visionGeometry"])
    if not geometries:
        return None

    def median_value(path: tuple[str, ...]) -> float:
        values: list[float] = []
        for geometry in geometries:
            value: Any = geometry
            for item in path:
                value = value[item]
            values.append(float(value))
        return float(np.median(values))

    output: dict[str, Any] = {}
    for key, value in geometries[0].items():
        if isinstance(value, dict):
            output[key] = {child_key: median_value((key, child_key)) for child_key in value.keys()}
        else:
            output[key] = median_value((key,))
    return output


def fill_missing_panels_from_composite_geometry(panel_summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    local_geometry = median_local_geometry(panel_summaries)
    if local_geometry is None:
        return panel_summaries

    filled: list[dict[str, Any]] = []
    for panel in panel_summaries:
        if str(panel.get("visionStatus", "")).startswith("ok"):
            filled.append(panel)
            continue
        filled.append(
            apply_geometry_to_panel(
                dict(panel),
                local_geometry,
                "ok_from_composite_panel_median",
            )
        )
    return filled


def round_dict_values(value: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, float):
            output[key] = round(item, 3)
        else:
            output[key] = item
    return output


def build_mapped_recommendations(
    panel_summaries: list[dict[str, Any]],
    capture_record: dict[str, Any] | None,
) -> dict[str, Any]:
    if capture_record is None:
        return {"status": "missing_capture_vision"}
    geometry = face_geometry(capture_record, float(capture_record["image"]["height"]))
    if geometry is None:
        return {"status": "capture_landmarks_missing"}

    shape_recommendations: dict[str, Any] = {}
    for panel in panel_summaries:
        if not str(panel.get("visionStatus", "")).startswith("ok"):
            continue
        anchors = []
        for component in panel["pinkComponents"]:
            side = component["side"]
            x = float(geometry["faceCenterX"]) + float(component["xFromFaceCenterPerFaceWidth"]) * float(geometry["faceWidth"])
            y = float(geometry["eyeCenterY"]) + float(component["yFromEyeCenterPerFaceHeight"]) * float(geometry["faceHeight"])
            anchors.append(
                {
                    "side": side,
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "width": round(float(component["widthPerFaceWidth"]) * float(geometry["faceWidth"]), 3),
                    "height": round(float(component["heightPerFaceHeight"]) * float(geometry["faceHeight"]), 3),
                    "sourceRatios": {
                        "xFromFaceCenterPerFaceWidth": component["xFromFaceCenterPerFaceWidth"],
                        "yFromEyeCenterPerFaceHeight": component["yFromEyeCenterPerFaceHeight"],
                        "yFromEyeToNose": component["yFromEyeToNose"],
                    },
                }
            )
        shape_recommendations[panel["shape"]] = {
            "maskId": panel["maskId"],
            "mappedAnchorsOnCaptureFrame": anchors,
        }
    return {
        "status": "ok",
        "captureGeometry": {
            key: round_dict_values(value) if isinstance(value, dict) else round(float(value), 4)
            for key, value in geometry.items()
            if key != "landmarks"
        },
        "shapes": shape_recommendations,
    }


def make_diagnostic_sheet(reference: Image.Image, panel_summaries: list[dict[str, Any]], output_dir: Path) -> str:
    tiles: list[tuple[str, Image.Image]] = []
    for panel in panel_summaries:
        crop = Image.open(panel["cropPath"]).convert("RGB")
        mask = Image.open(panel["pinkMaskPath"]).convert("L")
        if mask.size != crop.size:
            mask = mask.resize(crop.size, Image.Resampling.NEAREST)
        overlay = crop.convert("RGBA")
        color = Image.new("RGBA", crop.size, (226, 88, 118, 126))
        color.putalpha(mask.point(lambda value: min(int(value), 126)))
        overlay = Image.alpha_composite(overlay, color).convert("RGB")
        draw = ImageDraw.Draw(overlay)
        if panel.get("visionStatus") == "ok":
            geometry = panel["visionGeometry"]
            eye_y = float(geometry["eyeCenterY"])
            nose_y = float(geometry["noseCenterY"])
            draw.line((0, eye_y, overlay.width, eye_y), fill=(55, 180, 255), width=2)
            draw.line((0, nose_y, overlay.width, nose_y), fill=(255, 210, 60), width=2)
            for component in panel["pinkComponents"]:
                x = float(component["cx"])
                y = float(component["cy"])
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=(255, 255, 255), width=2)
        tiles.append((panel["shape"], overlay))

    tile_w = 360
    tile_h = 280
    sheet = Image.new("RGB", (tile_w, tile_h * len(tiles)), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(tiles):
        thumb = image.copy()
        thumb.thumbnail((tile_w, tile_h - 28), Image.Resampling.LANCZOS)
        y = index * tile_h
        draw.text((8, y + 6), label, fill=(0, 0, 0))
        sheet.paste(thumb, ((tile_w - thumb.width) // 2, y + 24))
    path = output_dir / "cheek_reference_vision_diagnostic_sheet.png"
    sheet.save(path)
    return str(path)


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    reference = Image.open(args.reference_composite).convert("RGBA")
    panels = crop_panels(reference, output_dir)
    panel_paths = [panel["cropPath"] for panel in panels]

    vision_records = load_vision_faces(args.vision_json)
    summaries = [
        summarize_panel(panel, vision_records.get(panel["cropPath"]))
        for panel in panels
    ]
    summaries = fill_missing_panels_from_composite_geometry(summaries)
    capture_key = str(args.capture_frame)
    mapped = build_mapped_recommendations(summaries, vision_records.get(capture_key))
    diagnostic_sheet = make_diagnostic_sheet(reference, summaries, output_dir)

    summary = {
        "gateId": "cheek-reference-vision-anchor-analysis-v1",
        "referenceComposite": str(args.reference_composite),
        "captureFrame": str(args.capture_frame),
        "visionJson": str(args.vision_json),
        "panelCropPaths": panel_paths,
        "pinkSegmentation": {
            "role": "measure user reference placement only; not used as final runtime mask boundary",
            "shapeOrder": [shape for shape, _ in SHAPE_ORDER],
        },
        "appleVisionRole": (
            "offline face landmark measurement for cheek anchor ratios; runtime cheek masks still attach through ARFace mesh UVs"
        ),
        "diagnosticSheet": diagnostic_sheet,
        "panels": summaries,
        "mappedRecommendations": mapped,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        "# Cheek Reference Vision Anchor Analysis v1\n\n"
        f"- referenceComposite: `{args.reference_composite}`\n"
        f"- captureFrame: `{args.capture_frame}`\n"
        f"- appleVisionRole: `{summary['appleVisionRole']}`\n"
        f"- diagnosticSheet: `{diagnostic_sheet}`\n"
        f"- mappedStatus: `{mapped['status']}`\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
