#!/usr/bin/env python3
"""Generate Unity-ready ARFace UV cheek blush masks from user drawings."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from generate_user_drawn_mask_textures import (
    DEFAULT_CAPTURE_PAIR,
    back_project_mask_to_uv,
    format_path,
    keep_components,
    load_arface_export,
    load_dark_mask,
    make_alpha_png,
    make_region_variants,
    mask_stats,
    resolve_path,
    save,
    trim_horizontal_uv_seams,
    write_unity_meta,
)


MASK_SPECS = (
    {
        "id": "cheek-lovely-mask-v1",
        "label": "lovely round cheek",
        "arg": "lovely",
        "default": "/Users/yeoduchi/Downloads/cheek_lovely_mask.png",
    },
    {
        "id": "cheek-daily-mask-v1",
        "label": "daily diagonal cheek",
        "arg": "daily",
        "default": "/Users/yeoduchi/Downloads/cheek_daily_mask.png",
    },
    {
        "id": "cheek-sunkissed-mask1-v1",
        "label": "sunkissed cheek plus nose",
        "arg": "sunkissed1",
        "default": "/Users/yeoduchi/Downloads/cheek_sunkissed_mask1.png",
    },
    {
        "id": "cheek-sunkissed-mask2-v1",
        "label": "sunkissed bridge wash",
        "arg": "sunkissed2",
        "default": "/Users/yeoduchi/Downloads/cheek_sunkissed_mask2.png",
    },
    {
        "id": "cheek-under-eye-mask-v1",
        "label": "under-eye soft blush",
        "arg": "under_eye",
        "default": "/Users/yeoduchi/Downloads/under_eye_mask.png",
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Back-project cheek blush drawings into ARFace UV masks."
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--capture-pair", type=str, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--capture-dir", type=Path, default=None)
    parser.add_argument("--reference", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("evidence/e7-reference-atlas/cheek-blush-mask-textures-v1"),
    )
    parser.add_argument(
        "--unity-output-dir",
        type=Path,
        default=Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"),
    )
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--dark-threshold", type=int, default=150)
    parser.add_argument("--min-component-pixels", type=int, default=450)
    parser.add_argument("--screen-sample-stride", type=int, default=1)
    for spec in MASK_SPECS:
        parser.add_argument(
            "--" + spec["arg"].replace("_", "-"),
            dest=spec["arg"],
            type=Path,
            default=Path(spec["default"]),
        )
    return parser.parse_args()


def make_contact_sheet(images: list[tuple[str, Image.Image]], tile: int = 300) -> Image.Image:
    columns = 3
    rows = int(np.ceil(len(images) / columns))
    sheet = Image.new("RGB", (columns * tile, rows * (tile + 30)), (246, 246, 246))
    draw = ImageDraw.Draw(sheet)
    for index, (label, image) in enumerate(images):
        col = index % columns
        row = index // columns
        x = col * tile
        y = row * (tile + 30)
        thumb = image.convert("RGB").copy()
        thumb.thumbnail((tile, tile), Image.Resampling.LANCZOS)
        draw.text((x + 8, y + 6), label, fill=(0, 0, 0))
        sheet.paste(thumb, (x + (tile - thumb.width) // 2, y + 24 + (tile - thumb.height) // 2))
    return sheet


def overlay_source_masks_for_comparison(
    reference: Image.Image,
    masks: list[tuple[str, Image.Image]],
) -> Image.Image:
    colors = (
        (242, 102, 124, 116),
        (236, 128, 88, 116),
        (224, 92, 76, 108),
        (236, 116, 86, 98),
        (229, 118, 146, 100),
    )
    output = reference.convert("RGBA")
    for index, (_, mask) in enumerate(masks):
        color = Image.new("RGBA", output.size, colors[index % len(colors)])
        alpha = mask.convert("L").filter(ImageFilter.GaussianBlur(radius=1.4))
        color.putalpha(alpha.point(lambda value: min(value, colors[index % len(colors)][3])))
        output = Image.alpha_composite(output, color)
    return output


def build_soft_unity_mask(uv_hard: Image.Image) -> Image.Image:
    variants = make_region_variants(uv_hard)
    safe = trim_horizontal_uv_seams(variants["soft"])
    return safe.filter(ImageFilter.GaussianBlur(radius=0.55))


def expand_component_ellipse(
    expanded: np.ndarray,
    component: np.ndarray,
    *,
    scale_x: float,
    scale_y: float,
    shift_x: float,
    shift_y: float,
) -> None:
    ys, xs = np.nonzero(component)
    if len(xs) == 0:
        return

    height, width = expanded.shape
    box_w = max(float(xs.max() - xs.min() + 1), 1.0)
    box_h = max(float(ys.max() - ys.min() + 1), 1.0)
    cx = float(xs.mean()) + shift_x * box_w
    cy = float(ys.mean()) + shift_y * box_h
    radius_x = max(box_w * scale_x * 0.5, 1.0)
    radius_y = max(box_h * scale_y * 0.5, 1.0)

    left = max(int(np.floor(cx - radius_x)), 0)
    right = min(int(np.ceil(cx + radius_x)), width - 1)
    top = max(int(np.floor(cy - radius_y)), 0)
    bottom = min(int(np.ceil(cy + radius_y)), height - 1)
    if right < left or bottom < top:
        return

    grid_y, grid_x = np.mgrid[top : bottom + 1, left : right + 1]
    ellipse = (
        ((grid_x - cx) / radius_x) ** 2
        + ((grid_y - cy) / radius_y) ** 2
    ) <= 1.0
    expanded[top : bottom + 1, left : right + 1] = np.maximum(
        expanded[top : bottom + 1, left : right + 1],
        ellipse.astype(np.uint8) * 255,
    )


def expand_screen_mask_for_runtime(clean: np.ndarray, mask_id: str) -> np.ndarray:
    expanded = np.asarray(clean, dtype=np.uint8).copy()
    alpha = expanded.astype(np.float32) / 255.0
    _, width = expanded.shape

    if mask_id == "cheek-under-eye-mask-v1":
        for component in iter_components(alpha, min_pixels=24):
            ys, xs = np.nonzero(component)
            if len(xs) == 0:
                continue

            direction = -1.0 if float(xs.mean()) < width * 0.5 else 1.0
            expand_component_ellipse(
                expanded,
                component,
                scale_x=1.64,
                scale_y=2.18,
                shift_x=direction * 0.05,
                shift_y=0.34,
            )
            expand_component_ellipse(
                expanded,
                component,
                scale_x=1.32,
                scale_y=1.24,
                shift_x=direction * 0.02,
                shift_y=-0.18,
            )
        return expanded

    growth_by_mask = {
        "cheek-lovely-mask-v1": (1.52, 1.50, 0.0, 0.04),
        "cheek-daily-mask-v1": (1.44, 1.42, 0.08, 0.02),
        "cheek-sunkissed-mask1-v1": (1.34, 1.38, 0.04, 0.02),
        "cheek-sunkissed-mask2-v1": (1.18, 1.68, 0.0, 0.10),
    }
    scale_x, scale_y, outward_shift, shift_y = growth_by_mask.get(
        mask_id,
        (1.28, 1.28, 0.0, 0.0),
    )
    for component in iter_components(alpha, min_pixels=24):
        ys, xs = np.nonzero(component)
        if len(xs) == 0:
            continue

        direction = -1.0 if float(xs.mean()) < width * 0.5 else 1.0
        expand_component_ellipse(
            expanded,
            component,
            scale_x=scale_x,
            scale_y=scale_y,
            shift_x=direction * outward_shift,
            shift_y=shift_y,
        )

    return expanded


def iter_components(alpha: np.ndarray, min_pixels: int = 8) -> list[np.ndarray]:
    active = alpha > 0.03
    height, width = active.shape
    visited = np.zeros(active.shape, dtype=bool)
    components: list[np.ndarray] = []
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
                if (
                    0 <= ny < height
                    and 0 <= nx < width
                    and active[ny, nx]
                    and not visited[ny, nx]
                ):
                    visited[ny, nx] = True
                    queue.append((ny, nx))

        if len(pixels) < min_pixels:
            continue

        rows, cols = zip(*pixels)
        component = np.zeros(active.shape, dtype=bool)
        component[np.asarray(rows), np.asarray(cols)] = True
        components.append(component)

    return components


def gaussian_density(
    alpha: np.ndarray,
    component: np.ndarray,
    peak_x: float,
    peak_y: float,
    sigma_x: float,
    sigma_y: float,
    base: float,
    cap: float = 1.0,
) -> np.ndarray:
    grid_y, grid_x = np.indices(alpha.shape)
    alpha_gate = smoothstep_array(0.045, 0.58, alpha) * component
    gaussian = np.exp(
        -(
            ((grid_x - peak_x) / max(sigma_x, 1.0)) ** 2
            + ((grid_y - peak_y) / max(sigma_y, 1.0)) ** 2
        )
    )
    return alpha_gate * np.clip((base + (1.0 - base) * gaussian) * cap, 0.0, 1.0)


def three_stage_density(
    alpha: np.ndarray,
    component: np.ndarray,
    peak_x: float,
    peak_y: float,
    sigma_x: float,
    sigma_y: float,
    base: float,
    cap: float = 1.0,
) -> np.ndarray:
    grid_y, grid_x = np.indices(alpha.shape)
    alpha_gate = smoothstep_array(0.035, 0.62, alpha) * component
    distance = np.sqrt(
        ((grid_x - peak_x) / max(sigma_x, 1.0)) ** 2
        + ((grid_y - peak_y) / max(sigma_y, 1.0)) ** 2
    )
    outer = smoothstep_array(1.92, 0.70, distance) * 0.28
    mid = smoothstep_array(1.24, 0.38, distance) * 0.36
    core = np.exp(-(distance**2)) * 0.48
    layered = np.clip(base + outer + mid + core, 0.0, 1.0)
    return alpha_gate * np.clip(layered * cap, 0.0, 1.0)


def smoothstep_array(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    denominator = edge1 - edge0
    if abs(denominator) < 1.0e-6:
        denominator = 1.0e-6 if denominator >= 0 else -1.0e-6
    t = np.clip((values - edge0) / denominator, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def make_density_map(uv_soft: Image.Image, mask_id: str) -> Image.Image:
    alpha = np.asarray(uv_soft.convert("L"), dtype=np.float32) / 255.0
    density = np.zeros_like(alpha)
    _, width = alpha.shape
    grid_y, grid_x = np.indices(alpha.shape)

    for component in iter_components(alpha):
        ys, xs = np.nonzero(component)
        if len(xs) == 0:
            continue

        weights = alpha[component]
        total_weight = float(weights.sum())
        if total_weight <= 0.0:
            continue

        cx = float((xs * weights).sum() / total_weight)
        cy = float((ys * weights).sum() / total_weight)
        box_w = max(float(xs.max() - xs.min() + 1), 1.0)
        box_h = max(float(ys.max() - ys.min() + 1), 1.0)

        if mask_id == "cheek-sunkissed-mask2-v1":
            half_width = max(box_w * 0.56, 1.0)
            alpha_gate = smoothstep_array(0.035, 0.62, alpha) * component
            side_strength = np.clip(np.abs((grid_x - cx) / half_width), 0.0, 1.0)
            outer = 0.16 * smoothstep_array(0.02, 0.48, alpha)
            mid = 0.32 * smoothstep_array(0.15, 0.76, alpha)
            ridge = 0.10 + 0.90 * np.power(side_strength, 1.35)
            vertical_core = np.exp(-((grid_y - (cy + box_h * 0.08)) / max(box_h * 0.42, 1.0)) ** 2)
            core = 0.46 * ridge * vertical_core
            component_density = alpha_gate * np.clip(outer + mid + core, 0.0, 1.0)
        else:
            direction = -1.0 if cx < width * 0.5 else 1.0
            peak_x = cx
            peak_y = cy
            sigma_x = box_w * 0.32
            sigma_y = box_h * 0.32
            base = 0.03
            cap = 1.0

            if mask_id == "cheek-daily-mask-v1":
                peak_x = cx + direction * box_w * 0.22
                peak_y = cy - box_h * 0.10
                sigma_x = box_w * 0.42
                sigma_y = box_h * 0.36
                base = 0.08
            elif mask_id == "cheek-lovely-mask-v1":
                sigma_x = box_w * 0.40
                sigma_y = box_h * 0.40
                base = 0.10
            elif mask_id == "cheek-sunkissed-mask1-v1":
                is_nose = abs(cx - width * 0.5) < width * 0.10 and box_w < width * 0.18
                sigma_x = box_w * (0.44 if is_nose else 0.40)
                sigma_y = box_h * (0.44 if is_nose else 0.38)
                base = 0.02 if is_nose else 0.09
                cap = 0.28 if is_nose else 1.0
            elif mask_id == "cheek-under-eye-mask-v1":
                peak_x = cx + direction * box_w * 0.24
                peak_y = cy - box_h * 0.02
                sigma_x = box_w * 0.46
                sigma_y = box_h * 0.48
                base = 0.06

            component_density = three_stage_density(
                alpha,
                component,
                peak_x,
                peak_y,
                sigma_x,
                sigma_y,
                base,
                cap,
            )

        density = np.maximum(density, component_density)

    density = np.clip(density, 0.0, 1.0)
    return Image.fromarray(np.rint(density * 255).astype(np.uint8), mode="L")


def make_cheek_rgba_mask(uv_soft: Image.Image, mask_id: str) -> tuple[Image.Image, Image.Image]:
    alpha = uv_soft.convert("L")
    density = make_density_map(alpha, mask_id)
    reserved = Image.new("L", alpha.size, 0)
    return Image.merge("RGBA", (alpha, reserved, density, alpha)), density


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    output_dir = resolve_path(repo, args.output_dir)
    unity_dir = resolve_path(repo, args.unity_output_dir)
    pair_dir = resolve_path(
        repo,
        args.capture_dir,
        Path("evidence/e7-reference-atlas/capture_pairs") / args.capture_pair,
    )
    assert output_dir is not None
    assert unity_dir is not None
    assert pair_dir is not None

    arface_path = pair_dir / "arface_export.json"
    frame_path = pair_dir / "frame.png"
    reference_path = resolve_path(repo, args.reference) if args.reference else frame_path
    if not arface_path.exists():
        raise FileNotFoundError("ARFace export does not exist: " + str(arface_path))
    if reference_path is None or not reference_path.exists():
        raise FileNotFoundError("Reference image does not exist: " + str(reference_path))

    arface = load_arface_export(arface_path)
    reference = Image.open(reference_path).convert("RGB")
    source_overlays: list[tuple[str, Image.Image]] = []
    contact_images: list[tuple[str, Image.Image]] = []
    summaries: dict[str, object] = {}
    expected_size: tuple[int, int] | None = None

    for spec in MASK_SPECS:
        source_path = resolve_path(repo, getattr(args, spec["arg"]))
        if source_path is None or not source_path.exists():
            raise FileNotFoundError("Source cheek drawing is missing: " + str(source_path))

        raw = load_dark_mask(source_path, args.dark_threshold)
        clean, component_stats = keep_components(raw, args.min_component_pixels)
        clean = expand_screen_mask_for_runtime(clean, spec["id"])
        if expected_size is None:
            expected_size = clean.shape
        elif clean.shape != expected_size:
            raise ValueError("All cheek source drawings must share the same canvas size.")

        screen = Image.fromarray(clean, mode="L")
        uv_hard, uv_stats = back_project_mask_to_uv(
            clean,
            arface,
            args.resolution,
            args.screen_sample_stride,
        )
        uv_soft = build_soft_unity_mask(uv_hard)
        uv_rgba, uv_density = make_cheek_rgba_mask(uv_soft, spec["id"])
        unity_path = unity_dir / (spec["id"] + ".png")

        save(output_dir / "screen" / (spec["id"] + "-source-clean.png"), screen)
        save(output_dir / "screen" / (spec["id"] + "-source-alpha.png"), make_alpha_png(screen))
        save(output_dir / "uv" / (spec["id"] + "-uv-hard.png"), uv_hard)
        save(output_dir / "uv" / (spec["id"] + "-uv-soft.png"), uv_soft)
        save(output_dir / "uv" / (spec["id"] + "-uv-density.png"), uv_density)
        save(unity_path, uv_rgba)
        write_unity_meta(unity_path.with_suffix(".png.meta"), "e7-" + spec["id"])

        source_overlays.append((spec["label"], screen))
        contact_images.extend(
            [
                (spec["label"] + " screen", screen),
                (spec["label"] + " uv hard", uv_hard),
                (spec["label"] + " uv soft", uv_soft),
                (spec["label"] + " uv density B", uv_density),
            ]
        )
        summaries[spec["id"]] = {
            "label": spec["label"],
            "sourcePath": format_path(repo, source_path),
            "unityMaskPath": format_path(repo, unity_path),
            "screenStats": mask_stats(clean),
            "componentStats": component_stats,
            "uvStats": uv_stats,
            "unityMaskStats": mask_stats(np.asarray(uv_soft, dtype=np.uint8)),
            "densityStats": mask_stats(np.asarray(uv_density, dtype=np.uint8)),
        }

    overlay = overlay_source_masks_for_comparison(reference, source_overlays)
    contact_sheet = make_contact_sheet(contact_images)
    save(output_dir / "screen" / "cheek_blush_region_comparison_overlay.png", overlay)
    save(output_dir / "cheek_blush_mask_contact_sheet.png", contact_sheet)

    summary = {
        "textureSetId": "cheek-blush-mask-textures-v1",
        "region": "cheek",
        "coordinateSpace": f"{expected_size[1]}x{expected_size[0]}" if expected_size else "unknown",
        "uvResolution": args.resolution,
        "capturePairId": pair_dir.name,
        "arfaceExportPath": format_path(repo, arface_path),
        "referencePath": format_path(repo, reference_path),
        "outputDir": format_path(repo, output_dir),
        "unityOutputDir": format_path(repo, unity_dir),
        "maskIds": [spec["id"] for spec in MASK_SPECS],
        "channelContract": {
            "r": "expanded soft blush outer alpha",
            "g": "reserved; must remain zero for cheek v1",
            "b": "per-shape three-stage density map for outer/mid/core powder pigment",
            "a": "expanded soft blush outer alpha",
        },
        "runtimeSelectionRule": "one cheek blush region mask is selected per cheek layer; generated masks are not stacked together; each mask encodes outer/mid/core gradient layers",
        "masks": summaries,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        "# Cheek Blush Mask Textures v1\n\n"
        f"- region: `{summary['region']}`\n"
        f"- coordinateSpace: `{summary['coordinateSpace']}`\n"
        f"- uvResolution: `{summary['uvResolution']}`\n"
        f"- capturePairId: `{summary['capturePairId']}`\n"
        f"- contactSheet: `{format_path(repo, output_dir / 'cheek_blush_mask_contact_sheet.png')}`\n"
        f"- runtimeSelectionRule: `{summary['runtimeSelectionRule']}`\n"
        f"- comparisonOverlay: `{format_path(repo, output_dir / 'screen' / 'cheek_blush_region_comparison_overlay.png')}`\n"
        "  - comparison overlay is QA-only and must not be interpreted as runtime stacking\n\n"
        "## Unity Masks\n\n"
        + "\n".join(
            f"- `{mask_id}`: `{data['unityMaskPath']}`"
            for mask_id, data in summaries.items()
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
