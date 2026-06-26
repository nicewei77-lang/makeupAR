#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


DEFAULT_FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
DEFAULT_MASK = Path("evidence/e7-reference-atlas/lip-style-atlas-v1/lip_atlas_roundtrip_mask.png")
DEFAULT_OUT = Path("evidence/e7-reference-atlas/lip-style-atlas-v1/soft_sdf_multilayer_preview_20260626")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a buildless lip soft-SDF logical multilayer preview.",
    )
    parser.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--mask", type=Path, default=DEFAULT_MASK)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--color", default="#D94B74")
    parser.add_argument("--secondary-color", default="#F29BAA")
    parser.add_argument("--threshold", type=float, default=0.025)
    parser.add_argument("--feather", type=float, default=0.22)
    parser.add_argument("--soft-radius", type=float, default=4.0)
    parser.add_argument("--crop-pad-x", type=int, default=220)
    parser.add_argument("--crop-pad-y", type=int, default=170)
    return parser.parse_args()


def hex_rgb(value: str) -> np.ndarray:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Expected #RRGGBB, got {value!r}")
    return np.array([int(value[index : index + 2], 16) for index in (0, 2, 4)], dtype=np.float32) / 255.0


def smoothstep(edge0: float, edge1: float, values: np.ndarray) -> np.ndarray:
    t = np.clip((values - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def shader_feather_texel_radius(feather: float) -> float:
    return 1.25 + (5.5 - 1.25) * float(np.clip(feather * 2.35, 0.0, 1.0))


def load_mask(path: Path, size: tuple[int, int], radius: float) -> tuple[np.ndarray, np.ndarray]:
    hard_image = Image.open(path).convert("L")
    if hard_image.size != size:
        hard_image = hard_image.resize(size, Image.Resampling.NEAREST)
    soft_image = hard_image.filter(ImageFilter.GaussianBlur(radius=radius))
    hard = np.asarray(hard_image, dtype=np.float32) / 255.0
    soft = np.asarray(soft_image, dtype=np.float32) / 255.0
    return hard, soft


def bbox(mask: np.ndarray) -> dict[str, int]:
    ys, xs = np.where(mask > 0.03)
    if len(xs) == 0:
        raise SystemExit("Lip mask has no active pixels.")
    left = int(xs.min())
    top = int(ys.min())
    right = int(xs.max())
    bottom = int(ys.max())
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left + 1,
        "height": bottom - top + 1,
    }


def connected_component_count(active: np.ndarray) -> int:
    seen = np.zeros_like(active, dtype=bool)
    count = 0
    height, width = active.shape
    for y, x in np.argwhere(active):
        y = int(y)
        x = int(x)
        if seen[y, x]:
            continue
        count += 1
        stack = [(y, x)]
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    ny = cy + dy
                    nx = cx + dx
                    if 0 <= ny < height and 0 <= nx < width and active[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
    return count


def line_shape_metrics(mask: np.ndarray, threshold: float, reference_box: dict[str, int]) -> dict[str, Any]:
    active = mask > threshold
    ys, xs = np.where(active)
    active_pixels = int(active.sum())
    if active_pixels == 0:
        return {
            "threshold": threshold,
            "activePixels": 0,
            "bbox": {"left": 0, "top": 0, "right": -1, "bottom": -1, "width": 0, "height": 0},
            "aspectRatio": 0.0,
            "heightToLipHeight": 0.0,
            "widthToLipWidth": 0.0,
            "componentCount": 0,
        }

    left = int(xs.min())
    top = int(ys.min())
    right = int(xs.max())
    bottom = int(ys.max())
    width = right - left + 1
    height = bottom - top + 1
    return {
        "threshold": threshold,
        "activePixels": active_pixels,
        "bbox": {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": width,
            "height": height,
        },
        "aspectRatio": float(width / max(height, 1)),
        "heightToLipHeight": float(height / max(reference_box["height"], 1)),
        "widthToLipWidth": float(width / max(reference_box["width"], 1)),
        "componentCount": connected_component_count(active),
    }


def crop_from_bbox(box: dict[str, int], size: tuple[int, int], pad_x: int, pad_y: int) -> tuple[int, int, int, int]:
    width, height = size
    left = max(0, box["left"] - pad_x)
    top = max(0, box["top"] - pad_y)
    right = min(width, box["right"] + pad_x + 1)
    bottom = min(height, box["bottom"] + pad_y + 1)
    return left, top, right, bottom


def lip_density(mask: np.ndarray, box: dict[str, int], gradient_amount: float) -> np.ndarray:
    height, width = mask.shape
    y = np.arange(height, dtype=np.float32)[:, None]
    x = np.arange(width, dtype=np.float32)[None, :]
    center_x = box["left"] + box["width"] * 0.5
    center_y = box["top"] + box["height"] * 0.58
    x_width = max(1.0, box["width"] * 0.50)
    y_width = max(1.0, box["height"] * 0.40)
    radial = np.exp(-(((x - center_x) / x_width) ** 2 + ((y - center_y) / y_width) ** 2))
    inner_line = np.exp(-np.abs(y - center_y) / max(1.0, box["height"] * 0.22))
    density = np.clip((0.54 * radial + 0.46 * inner_line) * mask, 0.0, 1.0)
    return mask * (1.0 - gradient_amount) + density * gradient_amount


def hard_alpha_sticker(frame: np.ndarray, hard_mask: np.ndarray, color: np.ndarray) -> np.ndarray:
    alpha = (hard_mask > 0.025).astype(np.float32) * 0.72
    return frame * (1.0 - alpha[..., None]) + color * alpha[..., None]


def soft_sdf_layers(
    frame: np.ndarray,
    hard_mask: np.ndarray,
    soft_mask: np.ndarray,
    color: np.ndarray,
    secondary_color: np.ndarray,
    threshold: float,
    gradient_amount: float,
    gloss_amount: float,
    style: str,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    box = bbox(soft_mask)
    full_soft = smoothstep(threshold, threshold + 0.30, soft_mask)
    full_core = smoothstep(threshold + 0.36, threshold + 0.58, hard_mask)
    edge_band = np.clip(full_soft - full_core, 0.0, 1.0)
    inner_density = lip_density(full_soft, box, gradient_amount)

    if style == "gradient":
        base_layer = full_soft * 0.20
        inner_layer = inner_density * 0.82
        edge_layer = edge_band * 0.035
        inner_mix = np.clip(inner_density * 1.25 + 0.08, 0.0, 1.0)
        pixel_color = secondary_color * (1.0 - inner_mix[..., None]) + (color * 0.92) * inner_mix[..., None]
        pigment_cap = 0.78
    elif style == "gloss":
        base_layer = full_soft * 0.45
        inner_layer = inner_density * 0.10
        edge_layer = edge_band * 0.04
        pixel_color = color * 0.965 + secondary_color * 0.035
        pigment_cap = 0.62
    else:
        base_layer = full_soft * 0.55
        inner_layer = inner_density * 0.18
        edge_layer = edge_band * 0.035
        pixel_color = color * 0.92
        pigment_cap = 0.80

    pigment_strength = np.clip(base_layer + inner_layer + edge_layer, 0.0, pigment_cap)
    pigment_filter = (1.0 - pigment_strength[..., None]) + pixel_color * pigment_strength[..., None]
    rendered = np.clip(frame * pigment_filter, 0.0, 1.0)

    if gloss_amount > 0.0:
        height, width = full_soft.shape
        y = np.arange(height, dtype=np.float32)[:, None]
        x = np.arange(width, dtype=np.float32)[None, :]
        line_y = box["top"] + box["height"] * 0.68
        center_x = box["left"] + box["width"] * 0.5
        line_sigma = max(0.65, min(1.1, box["height"] * 0.010))
        lower_line = np.exp(-(((y - line_y) / line_sigma) ** 2))
        center_width = np.exp(-(((x - center_x) / max(1.0, box["width"] * 0.18)) ** 4))
        wet_line = lower_line * center_width * full_core
        tinted_wet = color * 0.62 + secondary_color * 0.38
        highlight_color = np.clip(tinted_wet * 0.70 + np.array([1.0, 0.94, 0.92], dtype=np.float32) * 0.30, 0.0, 1.0)
        rendered = np.clip(rendered + wet_line[..., None] * highlight_color * gloss_amount, 0.0, 1.0)
    else:
        wet_line = np.zeros_like(full_soft)

    layers = {
        "fullSoft": full_soft,
        "fullCore": full_core,
        "edgeBand": edge_band,
        "innerDensity": inner_density,
        "wetLine": wet_line,
        "pigmentStrength": pigment_strength,
    }
    return rendered, layers


def luma(values: np.ndarray) -> np.ndarray:
    return values[..., 0] * 0.2126 + values[..., 1] * 0.7152 + values[..., 2] * 0.0722


def metrics(original: np.ndarray, rendered: np.ndarray, soft_mask: np.ndarray, hard_mask: np.ndarray) -> dict[str, float]:
    active = soft_mask > 0.12
    edge = (soft_mask > 0.08) & (hard_mask < 0.5)
    if int(active.sum()) < 2:
        return {
            "lumaStdRatio": 0.0,
            "lumaCorrelation": 0.0,
            "edgeAlphaMean": 0.0,
        }
    source_luma = luma(original)[active]
    rendered_luma = luma(rendered)[active]
    source_std = float(source_luma.std())
    rendered_std = float(rendered_luma.std())
    correlation = 0.0 if source_std <= 1e-8 or rendered_std <= 1e-8 else float(np.corrcoef(source_luma, rendered_luma)[0, 1])
    return {
        "lumaStdRatio": rendered_std / max(source_std, 1e-8),
        "lumaCorrelation": correlation,
        "edgeAlphaMean": float(soft_mask[edge].mean()) if int(edge.sum()) > 0 else 0.0,
    }


def to_image(values: np.ndarray) -> Image.Image:
    return Image.fromarray(np.rint(np.clip(values, 0.0, 1.0) * 255).astype(np.uint8), mode="RGB")


def mask_to_rgb(mask: np.ndarray) -> Image.Image:
    values = np.rint(np.clip(mask, 0.0, 1.0) * 255).astype(np.uint8)
    return Image.fromarray(values, mode="L").convert("RGB")


def label(image: Image.Image, title: str, subtitle: str = "") -> Image.Image:
    output = image.convert("RGBA")
    draw = ImageDraw.Draw(output)
    panel_height = 86 if subtitle else 58
    draw.rectangle((12, 12, min(output.width - 12, 700), 12 + panel_height), fill=(0, 0, 0, 172))
    draw.text((28, 28), title, fill=(255, 255, 255, 255))
    if subtitle:
        draw.text((28, 54), subtitle, fill=(220, 230, 238, 255))
    return output.convert("RGB")


def boundary_overlay(image: Image.Image, mask: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    hard = mask > 0.04
    edge = np.zeros_like(hard)
    edge[1:, :] |= hard[1:, :] != hard[:-1, :]
    edge[:-1, :] |= hard[:-1, :] != hard[1:, :]
    edge[:, 1:] |= hard[:, 1:] != hard[:, :-1]
    edge[:, :-1] |= hard[:, :-1] != hard[:, 1:]
    alpha = Image.fromarray((edge.astype(np.uint8) * 255), mode="L").filter(ImageFilter.MaxFilter(3))
    line = Image.new("RGBA", image.size, (*color, 0))
    line.putalpha(alpha)
    return Image.alpha_composite(image.convert("RGBA"), line).convert("RGB")


def make_sheet(panels: list[tuple[str, Image.Image]], crop: tuple[int, int, int, int]) -> Image.Image:
    tile_width = 360
    label_height = 34
    cropped: list[tuple[str, Image.Image]] = []
    for title, image in panels:
        view = image.crop(crop)
        view.thumbnail((tile_width, 660), Image.Resampling.LANCZOS)
        cropped.append((title, view.convert("RGB")))

    width = tile_width * len(cropped)
    height = label_height + max(image.height for _, image in cropped)
    sheet = Image.new("RGB", (width, height), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    for index, (title, image) in enumerate(cropped):
        x = index * tile_width
        draw.rectangle((x, 0, x + tile_width, label_height), fill=(36, 36, 42))
        draw.text((x + 12, 10), title, fill=(255, 255, 255))
        sheet.paste(image, (x + (tile_width - image.width) // 2, label_height))
    return sheet


def save(path: Path, image: Image.Image) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return str(path)


def main() -> None:
    args = parse_args()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    frame_path = args.frame.resolve()
    mask_path = args.mask.resolve()
    frame_image = Image.open(frame_path).convert("RGB")
    frame = np.asarray(frame_image, dtype=np.float32) / 255.0
    hard_mask, blurred_mask = load_mask(mask_path, frame_image.size, args.soft_radius)
    color = hex_rgb(args.color)
    secondary = hex_rgb(args.secondary_color)
    shader_near_radius = shader_feather_texel_radius(args.feather)
    shader_far_radius = shader_near_radius * 1.85
    soft_alpha = smoothstep(args.threshold, args.threshold + 0.30, blurred_mask)
    box = bbox(soft_alpha)
    crop = crop_from_bbox(box, frame_image.size, args.crop_pad_x, args.crop_pad_y)

    sticker = hard_alpha_sticker(frame, hard_mask, color)
    matte, matte_layers = soft_sdf_layers(
        frame,
        hard_mask,
        blurred_mask,
        color,
        secondary,
        args.threshold,
        gradient_amount=0.10,
        gloss_amount=0.0,
        style="matte",
    )
    gradient, gradient_layers = soft_sdf_layers(
        frame,
        hard_mask,
        blurred_mask,
        color,
        secondary,
        args.threshold,
        gradient_amount=1.0,
        gloss_amount=0.0,
        style="gradient",
    )
    glow_base, _ = soft_sdf_layers(
        frame,
        hard_mask,
        blurred_mask,
        color,
        secondary,
        args.threshold,
        gradient_amount=0.20,
        gloss_amount=0.0,
        style="gloss",
    )
    glow, glow_layers = soft_sdf_layers(
        frame,
        hard_mask,
        blurred_mask,
        color,
        secondary,
        args.threshold,
        gradient_amount=0.20,
        gloss_amount=0.18,
        style="gloss",
    )
    wet_line_pixels = glow_layers["wetLine"] > 0.08
    wet_line_luma_boost = luma(glow) - luma(glow_base)

    panels = [
        ("original", label(boundary_overlay(frame_image, hard_mask, (255, 255, 255)), "original + hard edge")),
        ("hard alpha", label(boundary_overlay(to_image(sticker), hard_mask, (255, 74, 132)), "hard alpha baseline", "sticker-risk comparison")),
        ("soft matte", label(to_image(matte), "soft-SDF matte", "base + inner + edge")),
        ("soft gradient", label(to_image(gradient), "soft-SDF gradient", "soft outer wash + stronger inner tint")),
        ("tinted wet-line", label(to_image(glow), "tinted lower wet-line", "narrow gloss only")),
        ("mask layers", label(
            Image.merge(
                "RGB",
                (
                    mask_to_rgb(matte_layers["fullSoft"]).convert("L"),
                    mask_to_rgb(matte_layers["edgeBand"]).convert("L"),
                    mask_to_rgb(glow_layers["wetLine"]).convert("L"),
                ),
            ),
            "layer diagnostic",
            "R soft / G edge / B wet-line",
        )),
    ]
    sheet = make_sheet(panels, crop)

    outputs = {
        "sheet": save(out_dir / "soft_sdf_multilayer_sheet.png", sheet),
        "hardAlpha": save(out_dir / "hard_alpha_baseline.png", to_image(sticker)),
        "softMatte": save(out_dir / "soft_sdf_matte.png", to_image(matte)),
        "softGradient": save(out_dir / "soft_sdf_gradient.png", to_image(gradient)),
        "thinWetLine": save(out_dir / "soft_sdf_thin_wet_line.png", to_image(glow)),
        "layerDiagnostic": save(out_dir / "soft_sdf_layer_diagnostic.png", panels[-1][1]),
    }
    summary: dict[str, Any] = {
        "status": "offline_preview_only",
        "scope": "E7.3 validation-only soft-SDF logical multilayer preview",
        "frame": str(frame_path),
        "mask": str(mask_path),
        "color": args.color,
        "secondaryColor": args.secondary_color,
        "threshold": args.threshold,
        "feather": args.feather,
        "softRadiusPx": args.soft_radius,
        "shaderApproxNearRadiusPx": shader_near_radius,
        "shaderApproxFarRadiusPx": shader_far_radius,
        "crop": {
            "left": crop[0],
            "top": crop[1],
            "right": crop[2],
            "bottom": crop[3],
            "width": crop[2] - crop[0],
            "height": crop[3] - crop[1],
        },
        "activeBbox": box,
        "outputs": outputs,
        "metrics": {
            "hardAlpha": metrics(frame, sticker, soft_alpha, hard_mask),
            "softMatte": metrics(frame, matte, matte_layers["fullSoft"], hard_mask),
            "softGradient": metrics(frame, gradient, gradient_layers["fullSoft"], hard_mask),
            "thinWetLine": metrics(frame, glow, glow_layers["fullSoft"], hard_mask),
            "edgeBandMean": float(matte_layers["edgeBand"][matte_layers["edgeBand"] > 0.01].mean()),
            "wetLineActivePixels": int((glow_layers["wetLine"] > 0.02).sum()),
            "wetLineShape": line_shape_metrics(glow_layers["wetLine"], 0.02, box),
            "wetLineMeanLumaBoost": float(wet_line_luma_boost[wet_line_pixels].mean())
            if int(wet_line_pixels.sum()) > 0
            else 0.0,
            "wetLineMaxLumaBoost": float(wet_line_luma_boost[wet_line_pixels].max())
            if int(wet_line_pixels.sum()) > 0
            else 0.0,
        },
        "notes": [
            "This approximates the Unity shader intent for buildless review only.",
            "It is not runtime acceptance and does not mark E7.3 Green.",
            "The production path remains validation-only; no product-quality rendering claim is made.",
        ],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out_dir / "summary.md").write_text(
        "\n".join(
            [
                "# Lip Soft-SDF Multilayer Preview",
                "",
                "- Status: `offline_preview_only`",
                "- Scope: `E7.3 validation-only`",
                f"- Sheet: `{outputs['sheet']}`",
                f"- Layer diagnostic: `{outputs['layerDiagnostic']}`",
                "- Guard shape: wet-line must stay one thin tinted lower-center line.",
                "- Gradient shape: weak full-lip base with a stronger inner tint, fading through the soft outer edge.",
                "",
                "This preview approximates the current shader intent from the same reference frame and lip atlas round-trip mask.",
                "It is not Unity runtime or iPhone visual acceptance evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"lip_soft_sdf_multilayer_preview status=offline_preview_only sheet={outputs['sheet']}")


if __name__ == "__main__":
    main()
