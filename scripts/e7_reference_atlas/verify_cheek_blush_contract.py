#!/usr/bin/env python3
"""Verify the E7 cheek blush v1 mask/runtime contract."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MASK_ROOT = ROOT / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
SUMMARY_PATH = ROOT / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/summary.json"
EXPECTED_SUMMARY_PATH = (
    ROOT
    / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/expected_render_20260628_natural_v5/summary.json"
)
APP_PATH = ROOT / "rn/MakeupARValidation/App.tsx"
RNBRIDGE_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
OVERLAY_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
SHADER_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader"

MASK_IDS = (
    "cheek-daily-mask-v1",
    "cheek-lovely-mask-v1",
    "cheek-sunkissed-mask1-v1",
    "cheek-sunkissed-mask2-v1",
    "cheek-under-eye-mask-v1",
)
TEXTURE_NAMES = (
    "blush_daily",
    "blush_lovely",
    "blush_sunkissed1",
    "blush_sunkissed2",
    "blush_under_eye",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_text(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        require(token in text, f"{path.relative_to(ROOT)} missing token: {token}")


def verify_masks() -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for mask_id in MASK_IDS:
        path = MASK_ROOT / f"{mask_id}.png"
        require(path.exists(), f"Missing Unity cheek mask: {path}")
        rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
        require(rgba.shape == (512, 512, 4), f"{mask_id} must be 512x512 RGBA")

        r = rgba[:, :, 0]
        g = rgba[:, :, 1]
        b = rgba[:, :, 2]
        a = rgba[:, :, 3]
        active = r > 8

        require(int(g.max()) == 0, f"{mask_id} G channel must stay reserved/zero")
        require(np.array_equal(r, a), f"{mask_id} R and A alpha channels must match")
        require(int(active.sum()) > 3000, f"{mask_id} alpha coverage is unexpectedly tiny")
        require(int((b > 8).sum()) > 2500, f"{mask_id} density channel is unexpectedly tiny")
        require(float(b[active].mean()) < float(r[active].mean()), f"{mask_id} B density should not be flat alpha")
        require(int(b.max()) > 90, f"{mask_id} density peak is too weak")

        stats[mask_id] = {
            "alphaPixelsGt8": int(active.sum()),
            "densityPixelsGt8": int((b > 8).sum()),
            "densityMax": int(b.max()),
            "reservedGMax": int(g.max()),
        }
    return stats


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_SUMMARY_PATH.read_text(encoding="utf-8"))

    require(sorted(summary["maskIds"]) == sorted(MASK_IDS), "summary maskIds must match cheek v1")
    require(summary["channelContract"]["g"].startswith("reserved"), "summary must document reserved G")
    require(len(expected["rows"]) == 5, "expected render summary must contain five rows")
    require(
        expected["runtimeSelectionRule"]
        == "one cheek blush region mask is selected per cheek layer; each cheek mask encodes outer/mid/core gradient layers",
        "expected render must document single-mask runtime selection and encoded 3-stage layers",
    )
    require(
        expected["edgeContract"] == "cheek blush outer alpha stays wide for attachment, but visible pigment is density-gated inward and resolves toward unchanged camera skin",
        "expected render must document the skin-fade edge contract",
    )
    require(
        expected["layerContract"] == "outer invisible safety wash + mid veil + core pigment are blended from one selected cheek mask",
        "expected render must document the 3-stage layer contract",
    )
    require(
        expected["colorContract"] == "bright cheek colors are automatically darkened just enough for validation visibility while saturated colors keep their selected hue",
        "expected render must document color differentiation behavior",
    )
    require(
        expected["addedColor"] == "#F0CBD5",
        "expected render must document the added milk-pink color",
    )
    require(
        expected["densityContract"]["blush_daily"].startswith("expanded outer/high cheekbone"),
        "expected render must document shape-specific density behavior",
    )

    require_text(APP_PATH, MASK_IDS + TEXTURE_NAMES + ("cheek_blush_validation_v1", "cheek-blush-v1", "#F0CBD5"))
    require_text(
        RNBRIDGE_PATH,
        MASK_IDS
        + TEXTURE_NAMES
        + (
            "cheek_blush_validation_v1",
            "cheek-blush-v1",
            "GetDefaultMaskTextureId(region)",
            "maskTextureDensityPixelCountGt8",
            "maskTextureDensityMax",
        ),
    )
    require_text(
        OVERLAY_PATH,
        MASK_IDS
        + (
            "_CheekBlushMode",
            "rgba_cheek_blush_density_feather_powder",
            "MaskTextureDensityPixelCountGt8",
            "MaskTextureDensityCoverageGt8",
            "MaskTextureDensityBbox",
            "MaskTextureDensityMax",
        ),
    )
    require_text(
        SHADER_PATH,
        (
            "_CheekBlushMode",
            "cheekDensity",
            "cheekOuterLayer",
            "cheekMidLayer",
            "cheekCoreLayer",
            "cheekLightColorBoost",
            "cheekVisiblePrimary",
            "cheekSkinFade",
            "cheekSkinTint",
        ),
    )

    print(json.dumps({"status": "ok", "masks": verify_masks()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
