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
    / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/expected_render_20260627/summary.json"
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
        density_active = b > 8

        require(int(g.max()) == 0, f"{mask_id} G channel must stay reserved/zero")
        require(np.array_equal(r, a), f"{mask_id} R and A alpha channels must match")
        require(int(active.sum()) > 1200, f"{mask_id} final alpha coverage is unexpectedly tiny")
        require(int(density_active.sum()) > 2500, f"{mask_id} density channel is unexpectedly tiny")
        require(170 <= int(r.max()) <= 255, f"{mask_id} coverage alpha peak must preserve the full soft shape")
        require(55 <= int(b.max()) <= 140, f"{mask_id} density peak must stay in natural blush range")
        require(float(b[density_active].std()) > 18.0, f"{mask_id} density should have visible falloff")
        require(float(r[active].std()) > 12.0, f"{mask_id} alpha should not be flat across the shape")

        stats[mask_id] = {
            "alphaPixelsGt8": int(active.sum()),
            "alphaMax": int(r.max()),
            "alphaStdActive": float(r[active].std()) if int(active.sum()) > 0 else 0.0,
            "densityPixelsGt8": int(density_active.sum()),
            "densityMax": int(b.max()),
            "densityStdActive": float(b[density_active].std()) if int(density_active.sum()) > 0 else 0.0,
            "reservedGMax": int(g.max()),
        }
    return stats


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_SUMMARY_PATH.read_text(encoding="utf-8"))

    require(sorted(summary["maskIds"]) == sorted(MASK_IDS), "summary maskIds must match cheek v1")
    require(
        summary["channelContract"]["r"].startswith("coverage alpha = softly expanded shape boundary only"),
        "summary must document coverage alpha separately from density",
    )
    require(summary["channelContract"]["g"].startswith("reserved"), "summary must document reserved G")
    profiles = summary.get("densityProfiles", {})
    require(sorted(profiles.keys()) == sorted(MASK_IDS), "summary must define a density profile per cheek style")
    require(
        profiles["cheek-daily-mask-v1"]["blobs"]["cheek"]["centerX"] > 0.0,
        "daily profile must push core slightly outward",
    )
    require(
        profiles["cheek-lovely-mask-v1"]["blobs"]["cheek"]["radiusX"]
        < profiles["cheek-daily-mask-v1"]["blobs"]["cheek"]["radiusX"],
        "lovely profile must stay rounder/tighter than daily",
    )
    require(
        profiles["cheek-sunkissed-mask1-v1"]["blobs"]["nose"]["maxAlpha"]
        < profiles["cheek-sunkissed-mask1-v1"]["blobs"]["cheek"]["maxAlpha"],
        "sunkissed1 nose core must stay weaker than cheek core",
    )
    require(
        profiles["cheek-sunkissed-mask2-v1"]["blobs"]["noseBridge"]["maxAlpha"]
        < profiles["cheek-sunkissed-mask2-v1"]["blobs"]["leftCheek"]["maxAlpha"],
        "sunkissed2 nose bridge must stay weaker than cheekbone cores",
    )
    require(
        "verticalBalance" in profiles["cheek-sunkissed-mask2-v1"]
        and "lowerFade" not in profiles["cheek-sunkissed-mask2-v1"],
        "sunkissed2 must use horizontal cheek-to-nose density, not top-to-bottom lowerFade",
    )
    require(
        profiles["cheek-under-eye-mask-v1"]["blobs"]["underEye"]["centerY"] < 0.0,
        "under-eye profile must keep the core high under the eye",
    )
    require(
        profiles["cheek-under-eye-mask-v1"]["lowerFade"]["endY"]
        > profiles["cheek-under-eye-mask-v1"]["lowerFade"]["startY"],
        "under-eye profile must fade down into the cheek",
    )
    require(len(expected["rows"]) == 5, "expected render summary must contain five rows")
    require(
        expected["runtimeSelectionRule"] == "one cheek blush region mask is selected per cheek layer",
        "expected render must document single-mask runtime selection",
    )
    require(
        expected["edgeContract"] == "coverage alpha stays wide/soft while density and coverage form one continuous watercolor field; cheek color is applied through skin-aware multiply tint",
        "expected render must document the skin-aware edge contract",
    )
    require(
        expected["blendContract"] == "cheek blush uses a density-gated multiply filter, not simple source-over alpha color",
        "expected render must document the non-alpha-overlay blend contract",
    )
    require(
        expected["coreEdgeContract"].startswith("visible blush uses one continuous density curve"),
        "expected render must document the continuous blush density curve",
    )
    require(
        expected["densityContract"]["blush_daily"].startswith("outer/high cheekbone peak"),
        "expected render must document shape-specific density behavior",
    )
    require(
        "fades horizontally inward" in expected["densityContract"]["blush_sunkissed2"],
        "expected render must document sunkissed2 horizontal fade",
    )
    require(
        "fades gradually downward" in expected["densityContract"]["blush_under_eye"],
        "expected render must document under-eye downward fade",
    )

    require_text(APP_PATH, MASK_IDS + TEXTURE_NAMES + ("cheek_blush_validation_v1", "cheek-blush-v1"))
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
            "skin_aware_cheek_blush_density_filter",
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
            "cheekContinuousField",
            "cheekWatercolorField",
            "skinAwareFilter",
            "cheekBlushPigment",
        ),
    )

    print(json.dumps({"status": "ok", "masks": verify_masks()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
