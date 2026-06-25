#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


FRAME = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png")
VISION_MASK = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/frame_vision_outer_minus_inner_mask.png")
OUT_DIR = Path("evidence/e7-reference-atlas/vision-lip-boundary-v2/expected_runtime_preview")


LOOKS = [
    {
        "id": "natural_satin",
        "label": "natural satin",
        "color": "#C76B7D",
        "strength": 0.42,
        "coverage": 0.82,
        "gradient": 0.18,
        "gloss": 0.0,
    },
    {
        "id": "rose_visible",
        "label": "rose visible",
        "color": "#D94B74",
        "strength": 0.56,
        "coverage": 0.88,
        "gradient": 0.1,
        "gloss": 0.0,
    },
    {
        "id": "soft_gradient",
        "label": "soft gradient",
        "color": "#D85C78",
        "strength": 0.54,
        "coverage": 0.86,
        "gradient": 0.72,
        "gloss": 0.0,
    },
    {
        "id": "gloss_hint",
        "label": "gloss hint",
        "color": "#D06479",
        "strength": 0.48,
        "coverage": 0.84,
        "gradient": 0.18,
        "gloss": 0.22,
    },
]


def hex_rgb(value: str) -> np.ndarray:
    value = value.strip().lstrip("#")
    return np.array([int(value[index : index + 2], 16) for index in (0, 2, 4)], dtype=np.float32) / 255.0


def load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    mask = Image.open(path).convert("L")
    if mask.size != size:
        mask = mask.resize(size, Image.Resampling.NEAREST)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=3.4))
    values = np.asarray(mask, dtype=np.float32) / 255.0
    return np.where(values > 8 / 255.0, values, 0.0)


def active_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask > 0.035)
    if len(xs) == 0:
        raise SystemExit("Vision lip mask is empty.")
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def expanded_crop(box: tuple[int, int, int, int], size: tuple[int, int], pad_x: int, pad_y: int) -> tuple[int, int, int, int]:
    width, height = size
    left, top, right, bottom = box
    return (
        max(0, left - pad_x),
        max(0, top - pad_y),
        min(width, right + pad_x + 1),
        min(height, bottom + pad_y + 1),
    )


def make_gradient_mask(mask: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return mask
    left, top, right, bottom = active_bbox(mask)
    height = max(1, bottom - top + 1)
    y = np.arange(mask.shape[0], dtype=np.float32)[:, None]
    center = top + height * 0.48
    inner_band = np.exp(-np.abs(y - center) / max(1.0, height * 0.22))
    gradient_weight = 0.58 + 0.42 * inner_band
    edge_softening = 1.0 - amount * 0.22
    return np.clip(mask * ((1.0 - amount) + amount * gradient_weight) * edge_softening, 0.0, 1.0)


def pigment_multiply(frame: np.ndarray, mask: np.ndarray, color: np.ndarray, strength: float, coverage: float) -> np.ndarray:
    pigment_strength = np.clip(mask * strength * coverage, 0.0, 1.0)[..., None]
    pigment_filter = (1.0 - pigment_strength) + color * pigment_strength
    return np.clip(frame * pigment_filter, 0.0, 1.0)


def add_gloss(frame: np.ndarray, mask: np.ndarray, amount: float) -> np.ndarray:
    if amount <= 0:
        return frame
    left, top, right, bottom = active_bbox(mask)
    width = max(1, right - left + 1)
    height = max(1, bottom - top + 1)
    y = np.arange(mask.shape[0], dtype=np.float32)[:, None]
    x = np.arange(mask.shape[1], dtype=np.float32)[None, :]
    center_x = left + width * 0.5
    upper_y = top + height * 0.34
    lower_y = top + height * 0.64
    x_band = np.exp(-((x - center_x) ** 2) / max(1.0, (width * 0.34) ** 2))
    upper = np.exp(-((y - upper_y) ** 2) / max(1.0, (height * 0.055) ** 2))
    lower = np.exp(-((y - lower_y) ** 2) / max(1.0, (height * 0.06) ** 2))
    gloss = np.clip((upper * 0.65 + lower * 0.45) * x_band * mask * amount, 0.0, 0.18)
    return np.clip(frame + gloss[..., None], 0.0, 1.0)


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


def label_panel(image: Image.Image, label: str) -> Image.Image:
    output = image.convert("RGBA")
    draw = ImageDraw.Draw(output)
    draw.rectangle((12, 12, 260, 48), fill=(0, 0, 0, 150))
    draw.text((24, 24), label, fill=(255, 255, 255, 255))
    return output.convert("RGB")


def to_image(values: np.ndarray) -> Image.Image:
    return Image.fromarray(np.rint(np.clip(values, 0.0, 1.0) * 255).astype(np.uint8), mode="RGB")


def luma_std_ratio(original: np.ndarray, rendered: np.ndarray, mask: np.ndarray) -> float:
    active = mask > 0.12
    if int(active.sum()) < 2:
        return 0.0
    weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    source_luma = (original * weights).sum(axis=2)[active]
    rendered_luma = (rendered * weights).sum(axis=2)[active]
    return float(rendered_luma.std() / max(float(source_luma.std()), 1e-8))


def make_sheet(panels: list[tuple[str, Image.Image]], crop: tuple[int, int, int, int], tile_width: int = 360) -> Image.Image:
    cropped: list[tuple[str, Image.Image]] = []
    for label, image in panels:
        view = image.crop(crop)
        view.thumbnail((tile_width, 660), Image.Resampling.LANCZOS)
        cropped.append((label, label_panel(view, label)))

    height = max(image.height for _, image in cropped)
    sheet = Image.new("RGB", (tile_width * len(cropped), height), (18, 18, 20))
    for index, (_, image) in enumerate(cropped):
        x = index * tile_width + (tile_width - image.width) // 2
        sheet.paste(image, (x, 0))
    return sheet


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame_image = Image.open(FRAME).convert("RGB")
    frame = np.asarray(frame_image, dtype=np.float32) / 255.0
    mask = load_mask(VISION_MASK, frame_image.size)
    crop = expanded_crop(active_bbox(mask), frame_image.size, pad_x=210, pad_y=170)

    original_panel = boundary_overlay(frame_image, mask, (0, 255, 232))
    panels: list[tuple[str, Image.Image]] = [("original + Vision edge", original_panel)]
    natural_panels: list[tuple[str, Image.Image]] = [("original", frame_image)]
    metrics: dict[str, object] = {
        "status": "offline_expected_preview_only",
        "frame": str(FRAME),
        "visionMask": str(VISION_MASK),
        "crop": {
            "left": crop[0],
            "top": crop[1],
            "right": crop[2],
            "bottom": crop[3],
            "width": crop[2] - crop[0],
            "height": crop[3] - crop[1],
        },
        "looks": {},
    }

    for look in LOOKS:
        look_mask = make_gradient_mask(mask, float(look["gradient"]))
        rendered = pigment_multiply(
            frame,
            look_mask,
            hex_rgb(str(look["color"])),
            float(look["strength"]),
            float(look["coverage"]),
        )
        rendered = add_gloss(rendered, look_mask, float(look["gloss"]))
        plain_image = to_image(rendered)
        image = boundary_overlay(plain_image, mask, (0, 255, 232))
        path = OUT_DIR / f"{look['id']}.png"
        plain_path = OUT_DIR / f"{look['id']}_no_boundary.png"
        image.save(path)
        plain_image.save(plain_path)
        panels.append((str(look["label"]), image))
        natural_panels.append((str(look["label"]), plain_image))
        metrics["looks"][str(look["id"])] = {
            "path": str(path),
            "noBoundaryPath": str(plain_path),
            "color": look["color"],
            "strength": look["strength"],
            "coverage": look["coverage"],
            "gradient": look["gradient"],
            "gloss": look["gloss"],
            "lumaStdRatio": luma_std_ratio(frame, rendered, look_mask),
        }

    sheet = make_sheet(panels, crop)
    sheet_path = OUT_DIR / "expected_runtime_vision_lip_sheet.png"
    sheet.save(sheet_path)
    natural_sheet = make_sheet(natural_panels, crop)
    natural_sheet_path = OUT_DIR / "expected_runtime_vision_lip_sheet_no_boundary.png"
    natural_sheet.save(natural_sheet_path)

    full = Image.new("RGB", (frame_image.width * 2, frame_image.height), (18, 18, 20))
    full.paste(original_panel, (0, 0))
    full.paste(panels[1][1], (frame_image.width, 0))
    full_path = OUT_DIR / "expected_runtime_vision_lip_full_original_vs_natural.png"
    full.save(full_path)
    natural_full = Image.new("RGB", (frame_image.width * 2, frame_image.height), (18, 18, 20))
    natural_full.paste(frame_image, (0, 0))
    natural_full.paste(natural_panels[1][1], (frame_image.width, 0))
    natural_full_path = OUT_DIR / "expected_runtime_vision_lip_full_original_vs_natural_no_boundary.png"
    natural_full.save(natural_full_path)

    metrics["sheet"] = str(sheet_path)
    metrics["naturalSheet"] = str(natural_sheet_path)
    metrics["fullOriginalVsNatural"] = str(full_path)
    metrics["naturalFullOriginalVsNatural"] = str(natural_full_path)
    (OUT_DIR / "summary.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(
        "\n".join(
            [
                "# Runtime Vision Lip Expected Preview",
                "",
                "- Status: `offline_expected_preview_only`",
                f"- Sheet: `{sheet_path}`",
                f"- Natural sheet without boundary line: `{natural_sheet_path}`",
                f"- Full original vs natural: `{full_path}`",
                f"- Full original vs natural without boundary line: `{natural_full_path}`",
                "- Source: Apple Vision v2 `raw-y` lip mask on the clean reference frame.",
                "- Note: This approximates the runtime Unity result; it is not device acceptance.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"expected_runtime_preview status=offline_expected_preview_only sheet={sheet_path}")


if __name__ == "__main__":
    main()
