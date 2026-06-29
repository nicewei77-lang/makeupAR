#!/usr/bin/env python3
"""Verify the E7 cheek blush v1 mask/runtime contract."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MASK_ROOT = ROOT / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
SUMMARY_PATH = ROOT / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/summary.json"
EXPECTED_SUMMARY_PATH = (
    ROOT
    / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/expected_render_20260629_current_session_png/summary.json"
)
APP_PATH = ROOT / "rn/MakeupARValidation/App.tsx"
RNBRIDGE_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
OVERLAY_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
SHADER_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader"

MASK_IDS = (
    "cheek-session-mask-1-v1",
    "cheek-session-mask-2-v1",
    "cheek-session-mask-3-v1",
    "cheek-session-mask-4-v1",
    "cheek-session-mask-5-v1",
)
TEXTURE_NAMES = (
    "blush_session_1",
    "blush_session_2",
    "blush_session_3",
    "blush_session_4",
    "blush_session_5",
)
REMOVED_CHEEK_RESOURCE_IDS = (
    "cheek-default2-mask-v1",
    "cheek-drawn-mask-v1",
    "cheek-smooth-mask-v1",
    "cheek-daily-mask-v1",
    "cheek-lovely-mask-v1",
    "cheek-sunkissed-mask1-v1",
    "cheek-sunkissed-mask2-v1",
    "cheek-under-eye-mask-v1",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_text(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        require(token in text, f"{path.relative_to(ROOT)} missing token: {token}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_masks() -> dict[str, dict[str, float | int | str]]:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    stats: dict[str, dict[str, float | int | str]] = {}
    for removed_id in REMOVED_CHEEK_RESOURCE_IDS:
        require(
            not (MASK_ROOT / f"{removed_id}.png").exists(),
            f"Old cheek mask resource must be deleted: {removed_id}.png",
        )
        require(
            not (MASK_ROOT / f"{removed_id}.png.meta").exists(),
            f"Old cheek mask meta must be deleted: {removed_id}.png.meta",
        )
    for mask_id in MASK_IDS:
        path = MASK_ROOT / f"{mask_id}.png"
        require(path.exists(), f"Missing Unity cheek mask: {path}")
        rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
        mask_summary = summary["masks"][mask_id]
        source_size = summary["masks"][mask_id]["sourceSize"]
        require(
            rgb.shape == (int(source_size["height"]), int(source_size["width"]), 3),
            f"{mask_id} must preserve the supplied UV atlas source size",
        )
        require(
            sha256(path) == mask_summary["sourceSha256"] == mask_summary["unitySha256"],
            f"{mask_id} Unity Resource PNG must be byte-identical to the supplied source",
        )
        rgb_float = rgb.astype(np.float32) / 255.0
        luminance = (
            rgb_float[:, :, 0] * 0.2126
            + rgb_float[:, :, 1] * 0.7152
            + rgb_float[:, :, 2] * 0.0722
        )
        gray_strength = np.clip((0.965 - luminance) / 0.412, 0.0, 1.0)
        active = gray_strength > 0.03
        density = np.clip(gray_strength**1.16, 0.0, 1.0)
        density_active = density > 0.03

        require(float(active.sum()) / float(gray_strength.size) > 0.030, f"{mask_id} gray mask coverage is unexpectedly tiny")
        require(float(density_active.sum()) / float(density.size) > 0.025, f"{mask_id} gray density is unexpectedly tiny")
        require(float(gray_strength.max()) > 0.35, f"{mask_id} gray coverage peak should be visible")
        require(float(density[density_active].std()) > 0.045, f"{mask_id} density should have visible falloff")
        require(float(gray_strength[active].std()) > 0.050, f"{mask_id} gray coverage should not be flat")

        stats[mask_id] = {
            "sourceMode": str(mask_summary["sourceMode"]),
            "sha256": sha256(path),
            "grayPixelsGt003": int(active.sum()),
            "grayMax": float(gray_strength.max()),
            "grayStdActive": float(gray_strength[active].std()) if int(active.sum()) > 0 else 0.0,
            "densityPixelsGt003": int(density_active.sum()),
            "densityMax": float(density.max()),
            "densityStdActive": float(density[density_active].std()) if int(density_active.sum()) > 0 else 0.0,
        }
    return stats


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_SUMMARY_PATH.read_text(encoding="utf-8"))

    require(sorted(summary["maskIds"]) == sorted(MASK_IDS), "summary maskIds must match session cheek v1")
    require(
        summary["atlasSourceRule"].startswith("the five user-provided 2D PNGs are copied byte-for-byte"),
        "summary must document byte-identical user 2D source",
    )
    require(
        summary["shaderSamplingContract"]["rgb"].startswith("source RGB is preserved exactly"),
        "summary must document exact RGB preservation",
    )
    require(
        summary["shaderSamplingContract"]["coverage"].startswith("computed at runtime from source RGB luminance"),
        "summary must document runtime luminance coverage",
    )
    require(
        summary["shaderSamplingContract"]["density"].startswith("computed at runtime from source RGB luminance"),
        "summary must document runtime luminance density",
    )
    for mask_id in MASK_IDS:
        mask_summary = summary["masks"][mask_id]
        require(
            mask_summary["sourceMode"] == "byte_identical_user_supplied_2d_png",
            f"{mask_id} must copy the supplied 2D PNG directly",
        )
        require(
            mask_summary["sourceSha256"] == mask_summary["unitySha256"],
            f"{mask_id} Unity resource hash must match source hash",
        )
    require(len(expected["rows"]) == 5, "expected render summary must contain five blush rows")
    for row in expected["rows"]:
        require(
            row["outerStrengthCurve"] == "lerp(0.035,0.095,smoothstep(intensity))",
            "expected render must use the skin-close outer intensity curve",
        )
        require(
            row["midStrengthCurve"] == "lerp(0.065,0.620,pow(intensity,1.05))",
            "expected render must use the edge-protected mid intensity curve",
        )
        require(
            row["coreStrengthCurve"] == "lerp(0.015,1.200,pow(intensity,1.18))",
            "expected render must use the center-strong core intensity curve",
        )
    require(
        expected["runtimeSelectionRule"] == "one user-supplied cheek blush 2D texture is selected per cheek layer",
        "expected render must document single-mask runtime selection",
    )
    require(
        "source RGB luminance" in expected["atlasSourceRule"],
        "expected render must document source RGB luminance sampling",
    )
    require(
        "outer band stays skin-close" in expected["edgeContract"],
        "expected render must document the skin-close outer edge contract",
    )
    require(
        "face-local x/y UVs" in expected["projectionNote"],
        "expected render must document face-local cheek mesh sampling",
    )
    require(
        "cheek mesh UVs are rebuilt from face-local x/y coordinates" in expected["placementCalibrationRule"],
        "expected render must document cheek face-local UV reconstruction",
    )
    require(
        expected["blendContract"] == "cheek blush uses a three-band skin-aware multiply filter, not simple source-over alpha color",
        "expected render must document the non-alpha-overlay blend contract",
    )
    require(
        "outer, mid, and core bands" in expected["coreEdgeContract"],
        "expected render must document smooth multi-band blush falloff",
    )
    require(
        expected["densityContract"]["blush_session_1"].startswith("direct session image-1 gray atlas"),
        "expected render must document session image-1 density behavior",
    )
    require(
        "darker gray pixels" in expected["densityContract"]["blush_session_2"],
        "expected render must document session image-2 density behavior",
    )
    require(
        "darker gray pixels" in expected["densityContract"]["blush_session_3"],
        "expected render must document session image-3 density behavior",
    )
    require(
        "darker gray pixels" in expected["densityContract"]["blush_session_4"],
        "expected render must document session image-4 density behavior",
    )
    require(
        expected["materialAlphaRule"].startswith("opacity stays independent"),
        "expected render must document opacity/intensity separation",
    )
    require(
        "darker gray pixels" in expected["densityContract"]["blush_session_5"],
        "expected render must document session image-5 density behavior",
    )
    calibration_by_mask = {
        row["maskTextureId"]: row
        for row in expected["rows"]
    }
    require(calibration_by_mask["cheek-session-mask-1-v1"]["densityGain"] == 0.94, "daily/session-1 must normalize density for same-slider comparison")
    require(calibration_by_mask["cheek-session-mask-1-v1"]["coverage"] == 0.78, "daily/session-1 must use shared default coverage")
    require(calibration_by_mask["cheek-session-mask-1-v1"]["intensity"] == 0.76, "daily/session-1 must use shared default intensity")
    require(calibration_by_mask["cheek-session-mask-2-v1"]["coverage"] == 0.78, "lovely/session-2 must use shared default coverage")
    require(calibration_by_mask["cheek-session-mask-2-v1"]["intensity"] == 0.76, "lovely/session-2 must use shared default intensity")
    require(calibration_by_mask["cheek-session-mask-2-v1"]["uvTransform"] == [1.02, 0.84, 0.0, 0.0], "lovely/session-2 must sit farther from the nose while keeping its soft cheek height")
    require(calibration_by_mask["cheek-session-mask-2-v1"]["densityGain"] == 0.98, "lovely/session-2 must stay close to shared density strength")
    require(calibration_by_mask["cheek-session-mask-3-v1"]["coverage"] == 0.78, "under-eye/session-3 must use shared default coverage")
    require(calibration_by_mask["cheek-session-mask-3-v1"]["intensity"] == 0.76, "under-eye/session-3 must use shared default intensity")
    require(calibration_by_mask["cheek-session-mask-3-v1"]["uvTransform"] == [1.02, 1.32, 0.0, 0.02], "under-eye/session-3 must cover below-eye to upper-cheek rather than only the tear-triangle")
    require(calibration_by_mask["cheek-session-mask-3-v1"]["densityGain"] == 1.2, "under-eye/session-3 must stay visible under the shared slider strength")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["coverage"] == 0.78, "sunkissed1/session-4 must use shared default coverage")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["intensity"] == 0.76, "sunkissed1/session-4 must use shared default intensity")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["uvTransform"] == [1.12, 1.02, 0.0, -0.015], "sunkissed1/session-4 must read from outer cheekbone near the face line toward cheek rather than cheek center")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["partUvTransform"] == [1.12, 1.12, 0.0, -0.01], "sunkissed1/session-4 must enlarge the central nose component and place it closer to the nostril/alar area")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["partBlend"] == 0.9, "sunkissed1/session-4 must use stronger component-aware resampling for the nose component")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["densityGain"] == 0.86, "sunkissed1/session-4 must not over-darken the cheek while the nose component is strengthened")
    require(calibration_by_mask["cheek-session-mask-4-v1"]["centerGain"] == 0.95, "sunkissed1/session-4 must make central nose density visible")
    require(calibration_by_mask["cheek-session-mask-5-v1"]["coverage"] == 0.78, "sunkissed2/session-5 must use shared default coverage")
    require(calibration_by_mask["cheek-session-mask-5-v1"]["intensity"] == 0.76, "sunkissed2/session-5 must use shared default intensity")
    require(calibration_by_mask["cheek-session-mask-5-v1"]["uvTransform"] == [1.02, 0.96, 0.0, -0.018], "sunkissed2/session-5 must keep the supplied band crossing the nose with a slightly wider x-axis")
    require(calibration_by_mask["cheek-session-mask-5-v1"]["densityGain"] == 0.94, "sunkissed2/session-5 must stay balanced with the shared slider strength")
    require(calibration_by_mask["cheek-session-mask-5-v1"]["centerGain"] == 0.36, "sunkissed2/session-5 must keep central nose density visible but not harsh")

    require_text(
        APP_PATH,
        MASK_IDS
        + TEXTURE_NAMES
        + (
            "cheek_blush_validation_v1",
            "cheek-blush-v1",
            "Opacity",
            "const INTENSITY_STEP = 0.01",
            "cheek-blush-multiband-skin-aware-validation",
        ),
    )
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
            "_BlushIntensity",
            "_CheekUvTransform",
            "_CheekPartUvTransform",
            "_CheekPartBlend",
            "_CheekDensityGain",
            "_CheekCenterGain",
            "BuildCheekFaceLocalUvCoordinates",
            "ResolveCheekBlushUvTransform",
            "ResolveCheekBlushPartUvTransform",
            "ResolveCheekBlushPartBlend",
            "ResolveCheekBlushDensityGain",
            "ResolveCheekBlushCenterGain",
            "return CheekSessionMask1Id;",
            "user_session_2d_png_face_local_luminance_multiband",
            "face_local_skin_aware_cheek_blush_multiband_filter",
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
            "_BlushIntensity",
            "_CheekUvTransform",
            "_CheekPartUvTransform",
            "_CheekPartBlend",
            "_CheekDensityGain",
            "_CheekCenterGain",
            "cheekMaskUv",
            "cheekPartUv",
            "cheekPartGate",
            "cheekCenterGate",
            "cheekOuterBand",
            "cheekMidBand",
            "cheekCoreBand",
            "cheekDensity",
            "outerStrength",
            "midStrength",
            "coreStrength",
            "skinAwareFilter",
            "cheekBlushPigment",
            "CheekSourceGrayStrength",
            "CheekSourceGrayBlur",
            "lerp(1.00, 1.65, sliderCurve)",
            "lerp(0.035, 0.095, sliderCurve)",
            "lerp(0.065, 0.620, sliderMidCurve)",
            "lerp(0.015, 1.200, sliderCoreCurve)",
            "lerp(1.55, 1.15, saturate(_DensityPower))",
            "lerp(2.60, 1.70, saturate(_DensityPower))",
        ),
    )
    require(
        "CheekDailyMaskId" not in OVERLAY_PATH.read_text(encoding="utf-8"),
        "old cheek daily fallback constant must not remain in E3RegionMaskOverlay",
    )

    print(json.dumps({"status": "ok", "masks": verify_masks()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
