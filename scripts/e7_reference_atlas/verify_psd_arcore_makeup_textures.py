#!/usr/bin/env python3
"""Verify experimental PSD-derived ARCore makeup masks."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_MASK_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)
DEFAULT_EVIDENCE_DIR = Path(
    "evidence/asset-inputs/ARCore_canonical_face_texture_1_runtime"
)
DEFAULT_RN_APP = Path("rn/MakeupARValidation/App.tsx")
DEFAULT_RN_BRIDGE = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
DEFAULT_SHADER = Path(
    "unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader"
)
DEFAULT_GENERATOR = Path(
    "scripts/e7_reference_atlas/generate_psd_arcore_makeup_textures.py"
)
DEFAULT_EXTRACTOR = Path(
    "scripts/e7_reference_atlas/extract_arcore_psd_layers.py"
)
EXPECTED = {
    "psd-arcore-lip-style-v1.png": {
        "bbox": (195, 333, 315, 378),
        "active": (3300, 5200),
    },
    "psd-arcore-lip-mask-v1.png": {
        "bbox": (195, 333, 315, 378),
        "active": (3300, 5200),
    },
    "psd-arcore-cheek-undereye-v1.png": {
        "bbox": (74, 135, 436, 310),
        "active": (36000, 56000),
    },
    "psd-arcore-cheek-asia-z-v1.png": {
        "bbox": (40, 147, 470, 319),
        "active": (43000, 59000),
    },
    "psd-arcore-cheek-sunkissed-v1.png": {
        "bbox": (64, 158, 448, 304),
        "active": (38000, 52000),
    },
    "psd-arcore-cheek-daily-oval-v1.png": {
        "bbox": (75, 203, 429, 304),
        "active": (22000, 31000),
    },
    "psd-arcore-cheek-undereye2-v1.png": {
        "bbox": (59, 158, 452, 330),
        "active": (38000, 53000),
    },
    "psd-arcore-cheek-lovely-round-v1.png": {
        "bbox": (89, 161, 422, 333),
        "active": (38000, 53000),
    },
    "psd-arcore-cheek-lifted-diagonal-v1.png": {
        "bbox": (40, 131, 471, 271),
        "active": (28000, 40000),
    },
    "psd-arcore-brow-semi-arch-v1.png": {
        "bbox": (139, 144, 372, 163),
        "active": (900, 1900),
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify PSD ARCore makeup masks.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mask-dir", type=Path, default=DEFAULT_MASK_DIR)
    parser.add_argument("--evidence-dir", type=Path, default=DEFAULT_EVIDENCE_DIR)
    parser.add_argument("--rn-app", type=Path, default=DEFAULT_RN_APP)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--shader", type=Path, default=DEFAULT_SHADER)
    parser.add_argument("--generator", type=Path, default=DEFAULT_GENERATOR)
    parser.add_argument("--extractor", type=Path, default=DEFAULT_EXTRACTOR)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def bbox_for(values: np.ndarray, threshold: int = 8) -> tuple[int, int, int, int]:
    rows, cols = np.nonzero(values > threshold)
    require(len(cols) > 0, "Mask has no active pixels.")
    return int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())


def require_bbox_close(
    actual: tuple[int, int, int, int],
    expected: tuple[int, int, int, int],
    tolerance: int,
    name: str,
) -> None:
    for index, (actual_value, expected_value) in enumerate(zip(actual, expected)):
        require(
            abs(actual_value - expected_value) <= tolerance,
            f"{name} bbox component {index} is off: actual={actual} expected={expected}.",
        )


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    mask_dir = resolve(repo, args.mask_dir)
    evidence_dir = resolve(repo, args.evidence_dir)
    rn_app = read_text(resolve(repo, args.rn_app))
    rn_bridge = read_text(resolve(repo, args.rn_bridge))
    shader = read_text(resolve(repo, args.shader))
    generator = read_text(resolve(repo, args.generator))
    extractor = read_text(resolve(repo, args.extractor))
    summary = read_text(evidence_dir / "summary.json")
    require(
        "RUNTIME_LAYER_PATHS_NORMALIZED" in extractor
        and "Root/blush/Undereye/all" in extractor
        and "Root/blush/Asia-Z/all" in extractor
        and "Root/blush/Sunkissed/all" in extractor
        and "Root/blush/Daily-Oval/all" in extractor
        and "Root/blush/Undereye2/all" in extractor
        and "Root/blush/Lovely_Round/all" in extractor
        and "Root/blush/Lifted-Diagonal/all" in extractor
        and "path.casefold()" in extractor,
        "PSD extractor must accept updated PSD runtime layer names case-insensitively, including all cheek style layers.",
    )
    require(
        "root_blush_undereye_all.png" in generator
        and "root_blush_asia-z_all.png" in generator
        and "root_blush_sunkissed_all.png" in generator
        and "root_blush_daily-oval_all.png" in generator
        and "root_blush_undereye2_all.png" in generator
        and "root_blush_lovely_round_all.png" in generator
        and "root_blush_lifted-diagonal_all.png" in generator,
        "PSD generator must accept all updated cheek layer exports.",
    )
    require(
        "tintable coverage masks" in summary,
        "PSD ARCore summary must document white/gray PSD pixels as tint masks, not baked color.",
    )
    require(
        "R=full target/protect core, G=soft gradient powder, B=left/right hair detail" in summary,
        "PSD ARCore summary must document PSD brow channel semantics.",
    )
    require(
        "tintable coverage mask, not baked makeup color" in generator,
        "PSD generator must treat white/gray PSD artwork as tintable mask data.",
    )
    require(
        "R=target full/protect core" in generator
        and "G=very light powder" in generator
        and "B=left/right hair detail" in generator,
        "PSD generator must keep brow full, gradient, and hair layers in separate channels.",
    )
    require(
        "fit_full_canvas_to_resolution(" in generator
        and "MediaPipe/ARCore canonical full-canvas" in generator
        and "MediaPipe FaceMesh canonical eyebrow landmarks" in generator
        and "fit_brow_sides_to_target_contain(" not in generator
        and "lip_target = target_bbox" not in generator
        and "cheek_target = target_bbox" not in generator
        and "brow_left_target, brow_right_target" not in generator
        and "arkit_calibrated_brow_side_bboxes" not in generator
        and "browArkitCalibrated" not in generator
        and "brow_left_hair_source.filter(ImageFilter.MaxFilter" not in generator
        and "brow_right_hair_source.filter(ImageFilter.MaxFilter" not in generator
        and "image.resize((RESOLUTION, RESOLUTION)" not in generator,
        "PSD generator must keep PSD layers in the MediaPipe/ARCore canonical full-canvas coordinate system; runtime placement belongs in the detector bridge.",
    )
    require(
        "float3 pigmentColor = saturate(_RegionColor.rgb);" in shader,
        "Unity shader path must derive makeup pigment from recipe _RegionColor, not PSD white pixels.",
    )
    require(
        "psd-arcore-lip-style-v1" in rn_app
        and "psd-arcore-cheek-undereye-v1" in rn_app
        and "psd-arcore-cheek-asia-z-v1" in rn_app
        and "psd-arcore-cheek-sunkissed-v1" in rn_app
        and "psd-arcore-cheek-daily-oval-v1" in rn_app
        and "psd-arcore-cheek-undereye2-v1" in rn_app
        and "psd-arcore-cheek-lovely-round-v1" in rn_app
        and "psd-arcore-cheek-lifted-diagonal-v1" in rn_app
        and "psd-arcore-brow-semi-arch-v1" in rn_app,
        "RN must expose PSD-derived masks as selectable tintable mask ids.",
    )
    require(
        "psd-arcore-cheek-undereye-v1" in rn_bridge
        and "psd-arcore-cheek-asia-z-v1" in rn_bridge
        and "psd-arcore-cheek-sunkissed-v1" in rn_bridge
        and "psd-arcore-cheek-daily-oval-v1" in rn_bridge
        and "psd-arcore-cheek-undereye2-v1" in rn_bridge
        and "psd-arcore-cheek-lovely-round-v1" in rn_bridge
        and "psd-arcore-cheek-lifted-diagonal-v1" in rn_bridge,
        "Unity RNBridge must accept all PSD cheek texture ids for the cheek region.",
    )
    require(
        "PSD_BROW_PLACEMENT_BASELINE" in rn_app
        and "PSD_BROW_BASELINE_OFFSET_Y = 0" in rn_app,
        "RN must keep PSD semi-arch brows at the source-brow placement baseline.",
    )
    require(
        "PSD_BROW_DEFAULT_DETAIL_AMOUNT = 0.64" in rn_app
        and "PSD_BROW_DEFAULT_CLEANUP_STRENGTH = 0.52" in rn_app,
        "RN must start PSD semi-arch brows with thin hair detail and source-brow cleanup.",
    )
    summaries: list[str] = []
    for filename, expected in EXPECTED.items():
        path = mask_dir / filename
        require(path.exists(), f"Missing PSD ARCore mask: {path}")
        image = Image.open(path).convert("RGBA")
        require(image.size == (512, 512), f"{filename} must be 512x512, got {image.size}.")
        red = np.asarray(image, dtype=np.uint8)[:, :, 0]
        blue = np.asarray(image, dtype=np.uint8)[:, :, 2]
        alpha = np.asarray(image, dtype=np.uint8)[:, :, 3]
        active = int((red > 8).sum())
        actual_bbox = bbox_for(red)
        low, high = expected["active"]
        require(low <= active <= high, f"{filename} active pixels off: {active}.")
        require_bbox_close(actual_bbox, expected["bbox"], tolerance=7, name=filename)
        require(int(alpha.max()) > 120, f"{filename} alpha appears empty or too weak.")
        if filename == "psd-arcore-brow-semi-arch-v1.png":
            green = np.asarray(image, dtype=np.uint8)[:, :, 1]
            green_active = int((green > 8).sum())
            blue_active = int((blue > 8).sum())
            green_mean = float(green[green > 8].mean()) if green_active else 0.0
            blue_mean = float(blue[blue > 8].mean()) if blue_active else 0.0
            green_ratio = green_active / max(1, active)
            blue_ratio = blue_active / max(1, active)
            red_height = actual_bbox[3] - actual_bbox[1] + 1
            channel_union = (red > 8) | (green > 8) | (blue > 8)
            red_green_delta = float(
                np.mean(
                    np.abs(
                        red[channel_union].astype(np.int16)
                        - green[channel_union].astype(np.int16)
                    )
                )
            )
            red_blue_delta = float(
                np.mean(
                    np.abs(
                        red[channel_union].astype(np.int16)
                        - blue[channel_union].astype(np.int16)
                    )
                )
            )
            require(
                18 <= red_height <= 26,
                f"{filename} red full channel height is off: height={red_height}.",
            )
            require(
                0.70 <= green_ratio <= 1.65,
                f"{filename} green powder channel coverage is off: ratio={green_ratio:.3f}.",
            )
            require(
                0.62 <= blue_ratio <= 1.10,
                f"{filename} blue hair-detail channel coverage is off: ratio={blue_ratio:.3f}.",
            )
            require(
                green_mean <= 125.0,
                f"{filename} green powder channel is too strong: mean={green_mean:.3f}.",
            )
            require(
                blue_mean <= 105.0,
                f"{filename} blue hair-detail channel is too broad/solid: mean={blue_mean:.3f}.",
            )
            require(
                red_green_delta > 8.0 and red_blue_delta > 8.0,
                f"{filename} brow channels collapsed together: red/green={red_green_delta:.3f} red/blue={red_blue_delta:.3f}.",
            )
        summaries.append(f"{filename}:bbox={actual_bbox}:active={active}")

    print("psd_arcore_makeup_textures_ok " + " ".join(summaries))


if __name__ == "__main__":
    main()
