#!/usr/bin/env python3
"""Verify the RN-to-Unity eyebrow smooth-region contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_RN_APP = Path("rn/MakeupARValidation/App.tsx")
DEFAULT_RN_BRIDGE = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
DEFAULT_OVERLAY = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
)
DEFAULT_SHADER = Path(
    "unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader"
)
DEFAULT_ROUTES = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs"
)
DEFAULT_BROW_MASK_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)
DEFAULT_BROW_MASK_ID = "psd-arcore-brow-semi-arch-v1"
LEGACY_BROW_MASK_ID = "brow-drawn-mask-v1"
BROW_CLEANUP_SOURCE_MASK_ID = "brow-cleanup-source-v1"
PSD_ARCORE_MASK_IDS = (
    "psd-arcore-lip-style-v1",
    "psd-arcore-lip-mask-v1",
    "psd-arcore-cheek-undereye-v1",
    "psd-arcore-brow-semi-arch-v1",
)
SELECTED_BROW_MASK_IDS = (
    DEFAULT_BROW_MASK_ID,
    "brow-png-dailyflat-hair-v1",
    "brow-png-dailyflat-sharp-v1",
    "brow-png-dailyflat-multiply-v1",
    "brow-back-arch-soft-mix-v1",
    "brow-slim-tail-fine-hair-v1",
    "brow-png-daily-hair-v1",
    "brow-png-natural-hair-v1",
    "brow-png-narrow-hair-v1",
    "brow-png-lightbrown-hair-v1",
)
SUPPORTED_BROW_MASK_IDS = (
    *SELECTED_BROW_MASK_IDS,
    "brow-soft-arch-fine-hair-v1",
    LEGACY_BROW_MASK_ID,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify brow Unity contract.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--rn-app", type=Path, default=DEFAULT_RN_APP)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--shader", type=Path, default=DEFAULT_SHADER)
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--mask-dir", type=Path, default=DEFAULT_BROW_MASK_DIR)
    parser.add_argument("--mask", type=Path, action="append", default=[])
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_match(text: str, pattern: str, message: str) -> None:
    require(re.search(pattern, text, re.DOTALL) is not None, message)


def require_contains(text: str, needle: str, message: str) -> None:
    require(needle in text, message)


def require_not_contains(text: str, needle: str, message: str) -> None:
    require(needle not in text, message)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    rn_app = read_text(resolve(repo, args.rn_app))
    rn_bridge = read_text(resolve(repo, args.rn_bridge))
    overlay = read_text(resolve(repo, args.overlay))
    shader = read_text(resolve(repo, args.shader))
    routes = read_text(resolve(repo, args.routes))
    mask_dir = resolve(repo, args.mask_dir)
    mask_paths = [
        mask_dir / f"{mask_id}.png"
        for mask_id in (
            *SELECTED_BROW_MASK_IDS,
            LEGACY_BROW_MASK_ID,
            BROW_CLEANUP_SOURCE_MASK_ID,
        )
    ]
    mask_paths.extend(mask_dir / f"{mask_id}.png" for mask_id in PSD_ARCORE_MASK_IDS)
    mask_paths.extend(resolve(repo, mask) for mask in args.mask)

    for mask_path in mask_paths:
        require(mask_path.exists(), f"Missing smooth-region mask asset: {mask_path}")

    require_contains(
        rn_app,
        "const RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye', 'brow'] as const;",
        "RN recipe region options must include brow as the fourth region.",
    )
    require_contains(
        rn_app,
        "| 'natural_brow'",
        "RN recipe sample names must include natural_brow.",
    )
    require_contains(
        rn_app,
        "| 'soft_brow'",
        "RN recipe sample names must include soft_brow.",
    )
    for mask_id in SUPPORTED_BROW_MASK_IDS:
        require_contains(
            rn_app,
            f"| '{mask_id}'",
            f"RN mask texture ids must include {mask_id}.",
        )
    for mask_id in PSD_ARCORE_MASK_IDS:
        require_contains(
            rn_app,
            f"| '{mask_id}'",
            f"RN mask texture ids must include PSD-derived mask {mask_id}.",
        )
    for mask_id in SELECTED_BROW_MASK_IDS:
        require_contains(
            rn_app,
            f"id: '{mask_id}'",
            f"RN brow HUD options must include {mask_id}.",
        )
    for mask_id in PSD_ARCORE_MASK_IDS:
        require_contains(
            rn_app,
            f"id: '{mask_id}'",
            f"RN HUD mask options must expose PSD-derived mask {mask_id}.",
        )
    require_contains(
        rn_app,
        "psd-arcore-brow-semi-arch-v1",
        "RN must expose the PSD brow as a separate tintable mask id, not replace an existing brow asset.",
    )

    require(
        f"brow: '{DEFAULT_BROW_MASK_ID}'" in rn_app
        or "brow: PSD_ARCORE_BROW_MASK_TEXTURE_ID" in rn_app,
        f"RN default brow mask must be {DEFAULT_BROW_MASK_ID}.",
    )

    require_match(
        routes,
        r"Regions\s*=\s*\{\s*\"lip\",\s*\"cheek\",\s*\"eye\",\s*\"brow\"\s*\}",
        "Renderer route table must include brow as the fourth layer.",
    )
    require_contains(
        rn_bridge,
        "FeatureSnapshotRegions = MakeupRegionRendererRoutes.Regions",
        "RNBridge FeatureSnapshotRegions must use the renderer route table.",
    )
    require_match(
        rn_bridge,
        r"region\s*==\s*\"brow\".*natural_brow.*soft_brow",
        "RNBridge NormalizeTextureSample must accept natural_brow and soft_brow for brow.",
    )
    require_match(
        rn_bridge,
        rf"case\s+\"brow\"\s*:\s*return\s+\"{DEFAULT_BROW_MASK_ID}\"",
        f"RNBridge GetDefaultMaskTextureId must return {DEFAULT_BROW_MASK_ID}.",
    )
    for mask_id in SUPPORTED_BROW_MASK_IDS:
        require_contains(
            rn_bridge,
            f'"{mask_id}"',
            f"RNBridge NormalizeMaskTextureId must accept {mask_id}.",
        )
    for mask_id in PSD_ARCORE_MASK_IDS:
        require_contains(
            rn_bridge,
            f'"{mask_id}"',
            f"RNBridge NormalizeMaskTextureId must accept PSD-derived mask {mask_id}.",
        )
    require_contains(
        rn_bridge,
        "public float maskSpreadX;",
        "RNBridge recipe layer payload must accept maskSpreadX.",
    )
    require_contains(
        rn_bridge,
        "public float maskOffsetY;",
        "RNBridge recipe layer payload must accept maskOffsetY.",
    )
    require_contains(
        rn_bridge,
        "public float detailAmount;",
        "RNBridge recipe payloads must accept PNG brow hair detailAmount.",
    )
    require_contains(
        rn_bridge,
        "public float browCleanupStrength;",
        "RNBridge recipe payloads must accept brow cleanup strength.",
    )
    require_contains(
        rn_bridge,
        "public bool browCleanupEnabled",
        "RNBridge recipe payloads must accept brow cleanup enabled toggle.",
    )
    require_contains(
        rn_bridge,
        "public string browCleanupSourceMode;",
        "RNBridge recipe payloads must accept brow cleanup source mode.",
    )
    require_contains(
        rn_bridge,
        "public float browReshapeStrength;",
        "RNBridge recipe payloads must accept brow reshape strength.",
    )
    require_contains(
        rn_bridge,
        "public float browGap;",
        "RNBridge recipe payloads must accept browGap.",
    )
    require_contains(
        rn_bridge,
        "public float browAngle;",
        "RNBridge recipe payloads must accept browAngle.",
    )
    require_contains(
        rn_bridge,
        "public float browArch;",
        "RNBridge recipe payloads must accept browArch.",
    )
    require_contains(
        rn_bridge,
        "public float browArchPosition;",
        "RNBridge recipe payloads must accept browArchPosition.",
    )
    require_contains(
        rn_bridge,
        "float maskSpread = NormalizeMaskSpread(layer.maskSpreadX);",
        "RNBridge must normalize layer maskSpreadX into parsed layers.",
    )
    require_contains(
        rn_bridge,
        'MaskSpreadX = region == "brow" ? browGap : maskSpread',
        "RNBridge must use browGap as the brow-facing gap placement value.",
    )
    require_contains(
        rn_bridge,
        "return Mathf.Clamp(maskSpread, -0.34f, 0.34f);",
        "RNBridge must preserve the wider brow spread tuning range.",
    )
    require_contains(
        rn_bridge,
        "return region == \"brow\" ? Mathf.Clamp(browAngle, -0.16f, 0.16f) : 0.0f;",
        "RNBridge must clamp browAngle to the conservative brow warp range.",
    )
    require_contains(
        rn_bridge,
        "return region == \"brow\" ? Mathf.Clamp(browArch, -0.05f, 0.05f) : 0.0f;",
        "RNBridge must clamp browArch to the conservative brow warp range.",
    )
    require_contains(
        rn_bridge,
        "return region == \"brow\" ? Mathf.Clamp(browArchPosition, -0.15f, 0.15f) : 0.0f;",
        "RNBridge must clamp browArchPosition to the conservative brow warp range.",
    )
    require_contains(
        rn_bridge,
        "SetFaceMeshOverlayVisible(faceMeshVisible);",
        "RNBridge overlay visibility must preserve the requested wire mesh visibility state.",
    )
    require_contains(
        rn_bridge,
        "faceMeshOverlayVisible = visible;",
        "RNBridge SetFaceMeshOverlayVisible must preserve the requested wire overlay state.",
    )
    require_contains(
        rn_bridge,
        "statusReporter.SetMeshOverlayVisible(faceMeshVisible);",
        "RNBridge must route meshOverlayVisible to the wireframe status reporter.",
    )
    require_contains(
        rn_bridge,
        "SetFaceRenderersSuppressed(true);",
        "RNBridge must keep the filled ARFace debug surface suppressed while mesh wireframe is visible.",
    )
    require_not_contains(
        rn_bridge,
        "ApplyFaceMeshOverlay();\n            return;",
        "RNBridge SetFaceMeshOverlayVisible must not enable the filled yellow ARFace surface.",
    )
    require_contains(
        rn_bridge,
        "MaskOffsetY = NormalizeMaskOffset(layer.maskOffsetY)",
        "RNBridge must normalize layer maskOffsetY into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "DetailAmount = Mathf.Clamp01(layer.detailAmount > 0.0f",
        "RNBridge must normalize PNG brow detailAmount into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "BrowCleanupStrength = NormalizeBrowCleanupStrength(",
        "RNBridge must normalize brow cleanup strength into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "BrowCleanupEnabled = NormalizeBrowCleanupEnabled(",
        "RNBridge must normalize brow cleanup enabled into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "BrowCleanupSourceMode = NormalizeBrowCleanupSourceMode(",
        "RNBridge must normalize brow cleanup source mode into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "BrowReshapeStrength = NormalizeBrowReshapeStrength(",
        "RNBridge must normalize brow reshape strength into parsed layers.",
    )
    require_contains(
        rn_bridge,
        '",\\\"maskSpreadX\\\":"',
        "RNBridge recipe_applied event must emit applied maskSpreadX for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"maskOffsetY\\\":"',
        "RNBridge recipe_applied event must emit applied maskOffsetY for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browGap\\\":"',
        "RNBridge recipe_applied event must emit applied browGap for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browAngle\\\":"',
        "RNBridge recipe_applied event must emit applied browAngle for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browArch\\\":"',
        "RNBridge recipe_applied event must emit applied browArch for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browArchPosition\\\":"',
        "RNBridge recipe_applied event must emit applied browArchPosition for QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupSource\\\":\\\"',
        "RNBridge recipe_applied event must emit browCleanupSource for device QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupEnabled\\\":',
        "RNBridge recipe_applied event must emit browCleanupEnabled for device QA diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupFallback\\\":\\\"',
        "RNBridge recipe_applied event must emit browCleanupFallback for fallback decisions.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupStatus\\\":\\\"',
        "RNBridge recipe_applied event must emit browCleanupStatus for GrabPass acceptance.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupSourceMode\\\":\\\"',
        "RNBridge recipe_applied event must emit browCleanupSourceMode for source switching QA.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupFallbackAvailable\\\":',
        "RNBridge recipe_applied event must emit browCleanupFallbackAvailable for AR BG fallback readiness.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupCameraTextureWidth\\\":',
        "RNBridge recipe_applied event must emit browCleanupCameraTextureWidth for fallback RT diagnostics.",
    )
    require_contains(
        rn_bridge,
        '",\\\"browCleanupCameraTextureHeight\\\":',
        "RNBridge recipe_applied event must emit browCleanupCameraTextureHeight for fallback RT diagnostics.",
    )
    require_contains(
        rn_bridge,
        ' + " maskSpreadX=" + result.MaskSpreadX.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied maskSpreadX.",
    )
    require_contains(
        rn_bridge,
        ' + " maskOffsetY=" + result.MaskOffsetY.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied maskOffsetY.",
    )
    require_contains(
        rn_bridge,
        ' + " browGap=" + result.BrowGap.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied browGap.",
    )
    require_contains(
        rn_bridge,
        ' + " browAngle=" + result.BrowAngle.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied browAngle.",
    )
    require_contains(
        rn_bridge,
        ' + " browArch=" + result.BrowArch.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied browArch.",
    )
    require_contains(
        rn_bridge,
        ' + " browArchPosition=" + result.BrowArchPosition.ToString("0.###", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include applied browArchPosition.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupSource=" + result.BrowCleanupSource',
        "RNBridge recipe_applied log must include browCleanupSource.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupFallback=" + result.BrowCleanupFallback',
        "RNBridge recipe_applied log must include browCleanupFallback.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupStatus=" + result.BrowCleanupStatus',
        "RNBridge recipe_applied log must include browCleanupStatus.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupSourceMode=" + result.BrowCleanupSourceMode',
        "RNBridge recipe_applied log must include browCleanupSourceMode.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupFallbackAvailable=" + result.BrowCleanupFallbackAvailable.ToString().ToLowerInvariant()',
        "RNBridge recipe_applied log must include browCleanupFallbackAvailable.",
    )
    require_contains(
        rn_bridge,
        ' + " browCleanupCameraTextureSize=" + result.BrowCleanupCameraTextureWidth.ToString(CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include fallback RT size.",
    )
    require_contains(
        rn_bridge,
        ' + " detailAmount=" + layer.DetailAmount.ToString("0.##", CultureInfo.InvariantCulture)',
        "RNBridge recipe_applied log must include detailAmount.",
    )

    require_match(
        overlay,
        r"NormalizeRegion\(string region\).*MakeupRegionRendererRoutes\.NormalizeRegion\(region\)",
        "E3RegionMaskOverlay NormalizeRegion must use the renderer route table.",
    )
    require_match(
        overlay,
        r"region\s*==\s*\"brow\".*natural_brow.*soft_brow",
        "E3RegionMaskOverlay NormalizeTextureSample must accept brow samples.",
    )
    require_match(
        overlay,
        rf"case\s+\"brow\"\s*:\s*return\s+\"{DEFAULT_BROW_MASK_ID}\"",
        f"E3RegionMaskOverlay GetDefaultMaskTextureId must return {DEFAULT_BROW_MASK_ID}.",
    )
    for mask_id in SUPPORTED_BROW_MASK_IDS:
        require_contains(
            overlay,
            f'"{mask_id}"',
            f"E3RegionMaskOverlay NormalizeMaskTextureId must accept {mask_id}.",
        )
    for mask_id in PSD_ARCORE_MASK_IDS:
        require_contains(
            overlay,
            f'"{mask_id}"',
            f"E3RegionMaskOverlay NormalizeMaskTextureId must accept PSD-derived mask {mask_id}.",
        )
    require_contains(
        overlay,
        "public string BrowCleanupSource;",
        "Region apply result must expose brow cleanup source.",
    )
    require_contains(
        overlay,
        "public string BrowCleanupFallback;",
        "Region apply result must expose brow cleanup fallback.",
    )
    require_contains(
        overlay,
        "public string BrowCleanupStatus;",
        "Region apply result must expose brow cleanup status.",
    )
    require_contains(
        overlay,
        "public string BrowCleanupSourceMode;",
        "Region apply result must expose brow cleanup source mode.",
    )
    require_contains(
        overlay,
        "public bool BrowCleanupEnabled;",
        "Region apply result must expose brow cleanup enabled state.",
    )
    require_contains(
        overlay,
        "public bool BrowCleanupFallbackAvailable;",
        "Region apply result must expose whether the ARCameraBackground fallback texture is ready.",
    )
    require_contains(
        overlay,
        "public int BrowCleanupCameraTextureWidth;",
        "Region apply result must expose fallback texture width.",
    )
    require_contains(
        overlay,
        "public int BrowCleanupCameraTextureHeight;",
        "Region apply result must expose fallback texture height.",
    )
    require_contains(
        overlay,
        "grabpass_live_frame_skin_sample",
        "Brow cleanup source must identify the GrabPass live-frame path.",
    )
    require_contains(
        overlay,
        "ar_camera_background_texture",
        "Brow cleanup fallback must identify the ARCameraBackground texture path.",
    )
    require_contains(
        overlay,
        "[SerializeField] private ARCameraBackground arCameraBackground;",
        "E3RegionMaskOverlay must hold ARCameraBackground for the fallback source.",
    )
    require_contains(
        overlay,
        "private RenderTexture browCleanupCameraTexture;",
        "E3RegionMaskOverlay must keep a GPU-only brow cleanup camera texture.",
    )
    require_contains(
        overlay,
        "Graphics.Blit(sourceTexture, browCleanupCameraTexture, backgroundMaterial);",
        "E3RegionMaskOverlay must render ARCameraBackground material into the fallback texture.",
    )
    require_contains(
        overlay,
        'material.SetTexture("_BrowCleanupCameraTex", browCleanupCameraTexture);',
        "E3RegionMaskOverlay must bind the fallback texture to the cleanup shader.",
    )
    require_contains(
        overlay,
        f'private const string BrowCleanupSourceMaskId = "{BROW_CLEANUP_SOURCE_MASK_ID}";',
        "E3RegionMaskOverlay must define a canonical source-brow cleanup mask.",
    )
    require_contains(
        overlay,
        'material.SetTexture("_BrowCleanupSourceTex", GetBrowCleanupSourceMaskTexture(recipe));',
        "E3RegionMaskOverlay must bind the source-brow cleanup mask independently of the target brow asset.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_BrowCleanupFrameSource",',
        "E3RegionMaskOverlay must switch the cleanup shader source without changing the default path.",
    )
    require_contains(
        overlay,
        "ApplyBrowCleanupFallbackDiagnostics(ref result, recipe, browCleanupDiagnostics);",
        "E3RegionMaskOverlay must update recipe results with actual fallback texture readiness.",
    )
    require_contains(
        overlay,
        'case "natural_brow":',
        "E3RegionMaskOverlay BuildMaterialColor must tune natural_brow.",
    )
    require_contains(
        overlay,
        "sampleAlphaScale = Mathf.Lerp(0.58f, 0.96f, recipe.Intensity);",
        "E3RegionMaskOverlay must make natural_brow visible enough at 75% intensity.",
    )
    require_contains(
        overlay,
        'case "soft_brow":',
        "E3RegionMaskOverlay BuildMaterialColor must tune soft_brow.",
    )
    require_contains(
        overlay,
        "sampleAlphaScale = Mathf.Lerp(0.58f, 0.94f, recipe.Intensity);",
        "E3RegionMaskOverlay must keep soft_brow visible enough at 75% intensity.",
    )
    require_contains(
        overlay,
        "regionsInScope=lip,cheek,eye,brow",
        "E3RegionMaskOverlay diagnostics must report brow in regionsInScope.",
    )
    require_contains(
        overlay,
        "private const float BrowMaskThreshold = 0.035f;",
        "E3RegionMaskOverlay must define a brow-specific mask threshold.",
    )
    require_contains(
        overlay,
        "private const float BrowMaskFeatherUvNormalized = 0.42f;",
        "E3RegionMaskOverlay must define a brow-specific mask feather.",
    )
    require_contains(
        overlay,
        "private const float BrowMaskRecipeFeatherMin = 0.34f;",
        "E3RegionMaskOverlay must define a brow recipe feather minimum.",
    )
    require_contains(
        overlay,
        "private const float BrowMaskRecipeFeatherMax = 0.48f;",
        "E3RegionMaskOverlay must define a brow recipe feather maximum.",
    )
    require_contains(
        overlay,
        "IsPngBrowHairMask(recipe.MaskTextureId) ? 1.0f : 0.0f",
        "E3RegionMaskOverlay must enable photo-detail rendering for PNG brow hair masks.",
    )
    require_contains(
        overlay,
        "IsPsdArcoreBrowMask(recipe.MaskTextureId) ? 1.0f : 0.0f",
        "E3RegionMaskOverlay must enable PSD brow powder fill only for the PSD semi-arch mask.",
    )
    require_contains(
        overlay,
        'return maskTextureId == "psd-arcore-brow-semi-arch-v1";',
        "E3RegionMaskOverlay must identify the PSD semi-arch brow mask separately from PNG hair masks.",
    )
    require_contains(
        overlay,
        "private const float BrowMeshVertexSmoothing = 0.58f;",
        "E3RegionMaskOverlay must define brow mesh vertex smoothing.",
    )
    require_contains(
        overlay,
        "BuildOverlayVertices(face, view, recipe)",
        "E3RegionMaskOverlay must build stable brow overlay vertices before rendering.",
    )
    require_contains(
        overlay,
        "recipe.Region == \"brow\" ? BrowMeshVertexSmoothing : 0.0f",
        "E3RegionMaskOverlay must apply vertex smoothing only to brow overlays.",
    )
    require_match(
        overlay,
        r"bool\s+browMask\s*=\s*region\s*==\s*\"brow\".*"
        r"Threshold\s*=\s*browMask\s*\?\s*BrowMaskThreshold.*"
        r"FeatherUvNormalized\s*=\s*browMask\s*\?\s*BrowMaskFeatherUvNormalized",
        "E3RegionMaskOverlay ResolveMask must route brow to its own threshold/feather.",
    )
    require_match(
        overlay,
        r"recipe\.Region\s*==\s*\"brow\".*"
        r"BrowMaskRecipeFeatherMax.*BrowMaskRecipeFeatherMin.*recipe\.Feather",
        "E3RegionMaskOverlay ResolveEffectiveFeather must clamp brow recipe feather.",
    )
    require_contains(
        overlay,
        "public float MaskSpreadX;",
        "E3RegionMaskOverlay result must expose mask spread X.",
    )
    require_contains(
        overlay,
        "public float MaskOffsetY;",
        "E3RegionMaskOverlay result must expose mask offset Y.",
    )
    require_contains(
        overlay,
        "public float DetailAmount;",
        "E3RegionMaskOverlay result must expose PNG brow detail amount.",
    )
    require_contains(
        overlay,
        "public float BrowCleanupStrength;",
        "E3RegionMaskOverlay result/state must expose brow cleanup strength.",
    )
    require_contains(
        overlay,
        "public float BrowReshapeStrength;",
        "E3RegionMaskOverlay result/state must expose brow reshape strength.",
    )
    require_contains(
        overlay,
        "public float BrowGap;",
        "E3RegionMaskOverlay result must expose browGap.",
    )
    require_contains(
        overlay,
        "public float BrowAngle;",
        "E3RegionMaskOverlay result must expose browAngle.",
    )
    require_contains(
        overlay,
        "public float BrowArch;",
        "E3RegionMaskOverlay result must expose browArch.",
    )
    require_contains(
        overlay,
        "public float BrowArchPosition;",
        "E3RegionMaskOverlay result must expose browArchPosition.",
    )
    require_contains(
        overlay,
        "float normalizedMaskSpread = Mathf.Clamp(maskSpreadX, -0.34f, 0.34f);",
        "E3RegionMaskOverlay must clamp mask spread X.",
    )
    require_contains(
        overlay,
        "MaskOffsetY = Mathf.Clamp(maskOffsetY, -0.08f, 0.08f)",
        "E3RegionMaskOverlay must clamp mask offset Y.",
    )
    require_contains(
        overlay,
        "BrowAngle = isBrow ? Mathf.Clamp(browAngle, -0.16f, 0.16f) : 0.0f",
        "E3RegionMaskOverlay must clamp browAngle.",
    )
    require_contains(
        overlay,
        "BrowArch = isBrow ? Mathf.Clamp(browArch, -0.05f, 0.05f) : 0.0f",
        "E3RegionMaskOverlay must clamp browArch.",
    )
    require_contains(
        overlay,
        "BrowArchPosition = isBrow ? Mathf.Clamp(browArchPosition, -0.15f, 0.15f) : 0.0f",
        "E3RegionMaskOverlay must clamp browArchPosition.",
    )
    require_contains(
        overlay,
        'material.SetVector("_MaskOffset"',
        "E3RegionMaskOverlay must pass mask offset to the shader.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_MaskSpreadX", recipe.MaskSpreadX)',
        "E3RegionMaskOverlay must pass symmetric mask spread to the shader.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_BrowAngle", recipe.Region == "brow" ? recipe.BrowAngle : 0.0f)',
        "E3RegionMaskOverlay must pass browAngle to the shader for brow only.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_BrowArch", recipe.Region == "brow" ? recipe.BrowArch : 0.0f)',
        "E3RegionMaskOverlay must pass browArch to the shader for brow only.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_BrowArchPosition", recipe.Region == "brow" ? recipe.BrowArchPosition : 0.0f)',
        "E3RegionMaskOverlay must pass browArchPosition to the shader for brow only.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_DetailAmount", recipe.DetailAmount)',
        "E3RegionMaskOverlay must pass PNG brow detail amount to the shader.",
    )
    require_contains(
        overlay,
        'recipe.Region == "brow" && recipe.BrowCleanupEnabled',
        "E3RegionMaskOverlay must pass brow cleanup strength only when brow cleanup is enabled.",
    )
    require_contains(
        overlay,
        'material.SetFloat("_BrowReshapeStrength", recipe.Region == "brow" ? recipe.BrowReshapeStrength : 0.0f)',
        "E3RegionMaskOverlay must pass brow reshape strength to the shader for brow only.",
    )
    require_contains(
        shader,
        '_MaskOffset ("Mask UV Offset", Vector) = (0, 0, 0, 0)',
        "SmoothRegionMask shader must define a mask UV offset property.",
    )
    require_contains(
        shader,
        "float4 _MaskOffset;",
        "SmoothRegionMask shader must expose _MaskOffset to shader code.",
    )
    require_contains(
        shader,
        '_MaskSpreadX ("Mask Spread X", Float) = 0',
        "SmoothRegionMask shader must define a symmetric mask spread property.",
    )
    require_contains(
        shader,
        "float _MaskSpreadX;",
        "SmoothRegionMask shader must expose _MaskSpreadX to shader code.",
    )
    require_contains(
        shader,
        '_BrowAngle ("Brow Angle", Float) = 0',
        "SmoothRegionMask shader must define a brow angle property.",
    )
    require_contains(
        shader,
        '_BrowArch ("Brow Arch", Float) = 0',
        "SmoothRegionMask shader must define a brow arch property.",
    )
    require_contains(
        shader,
        "float _BrowAngle;",
        "SmoothRegionMask shader must expose _BrowAngle to shader code.",
    )
    require_contains(
        shader,
        "float _BrowArch;",
        "SmoothRegionMask shader must expose _BrowArch to shader code.",
    )
    require_contains(
        shader,
        '_BrowPhotoDetailMode ("Brow Photo Detail Mode", Float) = 0',
        "SmoothRegionMask shader must define a PNG brow photo-detail mode property.",
    )
    require_contains(
        shader,
        '_BrowPowderFill ("Brow Powder Fill", Range(0, 1)) = 0',
        "SmoothRegionMask shader must define a PSD brow powder fill property.",
    )
    require_contains(
        shader,
        "float _BrowPhotoDetailMode;",
        "SmoothRegionMask shader must expose _BrowPhotoDetailMode to shader code.",
    )
    require_contains(
        shader,
        "float _BrowPowderFill;",
        "SmoothRegionMask shader must expose _BrowPowderFill to shader code.",
    )
    require_contains(
        shader,
        '_DetailAmount ("Detail Amount", Range(0, 1)) = 0',
        "SmoothRegionMask shader must define a PNG brow detail amount property.",
    )
    require_contains(
        shader,
        '_BrowCleanupStrength ("Brow Cleanup Strength", Range(0, 1)) = 0',
        "SmoothRegionMask shader must define a brow cleanup strength property.",
    )
    require_contains(
        shader,
        '_BrowReshapeStrength ("Brow Reshape Strength", Range(0, 1)) = 0',
        "SmoothRegionMask shader must define a brow reshape strength property.",
    )
    require_contains(
        shader,
        "float _DetailAmount;",
        "SmoothRegionMask shader must expose _DetailAmount to shader code.",
    )
    require_contains(
        shader,
        "float _BrowCleanupStrength;",
        "SmoothRegionMask shader must expose _BrowCleanupStrength to shader code.",
    )
    require_contains(
        shader,
        "float _BrowReshapeStrength;",
        "SmoothRegionMask shader must expose _BrowReshapeStrength to shader code.",
    )
    require_contains(
        shader,
        "maskUv.x = saturate(0.5 + (maskUv.x - 0.5) / max(1.0 + _MaskSpreadX, 0.001));",
        "SmoothRegionMask shader must spread eyebrow mask sampling around the centerline.",
    )
    require_contains(
        shader,
        "maskUv.y = saturate(maskUv.y - _MaskOffset.y);",
        "SmoothRegionMask shader must still apply vertical mask offset before sampling.",
    )
    require_contains(
        shader,
        "float2 ApplyBrowWarp(float2 uv)",
        "SmoothRegionMask shader must define the brow placement warp.",
    )
    require_contains(
        shader,
        "maskUv = ApplyBrowWarp(maskUv);",
        "SmoothRegionMask shader must apply brow angle/arch warp before sampling.",
    )
    require_not_contains(
        shader,
        "ApplyPsdBrowCanonicalMap",
        "SmoothRegionMask shader must not use hand-tuned PSD brow canonical UV correction constants.",
    )
    require_not_contains(
        shader,
        "uv.y = saturate(uv.y * 1.342857 - 0.01875);",
        "SmoothRegionMask shader must not vertically place PSD brows with a manual correction constant.",
    )
    require_contains(
        shader,
        "if (_BrowPhotoDetailMode > 0.5 && _LipStyleMode < -0.5 && (detailAmount > 0.001 || _BrowPowderFill > 0.001))",
        "SmoothRegionMask shader must route PNG brow masks through a photo-detail branch.",
    )
    require_contains(
        shader,
        "float BrowFiberAlpha(float2 uv, float shapeRaw, float detailAmount, float powderFill)",
        "SmoothRegionMask shader must use a brow-specific fiber alpha extractor instead of broad region fill.",
    )
    require_contains(
        shader,
        "float psdStrokePreserve = saturate(powderFill);",
        "SmoothRegionMask shader must preserve PSD-drawn hair strokes instead of treating them as broad fill.",
    )
    require_contains(
        shader,
        "softDetail * lerp(0.72, 0.52, psdStrokePreserve)",
        "SmoothRegionMask shader must relax high-pass suppression for PSD semi-arch hair strokes.",
    )
    require_contains(
        shader,
        "directStroke * psdStrokePreserve",
        "SmoothRegionMask shader must keep direct PSD hair stroke coverage visible.",
    )
    require_contains(
        shader,
        "float detailNeedle = saturate((",
        "SmoothRegionMask shader must high-pass brow detail so broad density does not clump into a block.",
    )
    require_contains(
        shader,
        "float powderRaw = saturate(max(mask.g, softMask.g * 0.82));",
        "SmoothRegionMask shader must read PSD semi-arch powder from the green gradient channel.",
    )
    require_contains(
        shader,
        "pow(powderRaw, 1.36) * coverage * 0.075",
        "SmoothRegionMask shader must keep PSD semi-arch powder very light.",
    )
    require_contains(
        shader,
        "float fiberCoverage = detailAmount > 0.001",
        "SmoothRegionMask shader must let the Texture Detail slider control the fiber contribution.",
    )
    require_contains(
        shader,
        "maskStrength = saturate(shapeVeil + fiberAlpha * fiberCoverage);",
        "SmoothRegionMask shader must make extracted brow fibers drive opacity.",
    )
    require_contains(
        shader,
        "float psdBrowMask = saturate(_BrowPowderFill);",
        "SmoothRegionMask shader must carry the PSD brow flag into later full-shape suppression logic.",
    )
    require_contains(
        shader,
        "powderRaw * powderFill * 0.32",
        "SmoothRegionMask raw debug mask must show PSD gradient powder rather than full-shape fill.",
    )
    require_not_contains(
        shader,
        "shapeRaw * powderFill * 0.32",
        "SmoothRegionMask shader must not make the PSD full/protect channel visible as a filled raw mask.",
    )
    require_not_contains(
        shader,
        "maskStrength = saturate(shapeVeil + hairLine * coverage * lerp(0.58, 1.10, detailAmount));",
        "SmoothRegionMask shader must not use the older broad hairLine fill formula for photo brow masks.",
    )
    require_contains(
        shader,
        "float cleanupHalo = saturate(browCleanup * (softMask.r - fullCore * 0.82));",
        "SmoothRegionMask shader must compute a target-mask cleanup halo for brow reshape mode.",
    )
    require_contains(
        shader,
        "float reshapeBoost = saturate(browReshape * fullSoft * (1.0 - fullCore) * (1.0 - psdBrowMask));",
        "SmoothRegionMask shader must not turn the PSD full/protect channel into visible reshape makeup.",
    )
    require_contains(
        shader,
        'GrabPass\n        {\n            "_BrowCleanupFrameTex"\n        }',
        "SmoothRegionMask shader must grab the live camera frame before brow cleanup passes.",
    )
    require_contains(
        shader,
        "sampler2D _BrowCleanupFrameTex;",
        "Brow cleanup pass must sample the grabbed camera frame texture.",
    )
    require_contains(
        shader,
        '_BrowCleanupCameraTex ("Brow Cleanup Camera Texture", 2D) = "black" {}',
        "SmoothRegionMask shader must define the ARCameraBackground fallback texture.",
    )
    require_contains(
        shader,
        '_BrowCleanupSourceTex ("Brow Cleanup Source Mask", 2D) = "black" {}',
        "SmoothRegionMask shader must define a source-brow cleanup mask texture.",
    )
    require_contains(
        shader,
        '_BrowCleanupFrameSource ("Brow Cleanup Frame Source", Float) = 0',
        "SmoothRegionMask shader must define a cleanup frame source switch.",
    )
    require_contains(
        shader,
        "sampler2D _BrowCleanupCameraTex;",
        "Brow cleanup pass must sample the ARCameraBackground fallback texture.",
    )
    require_contains(
        shader,
        "sampler2D _BrowCleanupSourceTex;",
        "Brow cleanup pass must sample the canonical source-brow mask.",
    )
    require_contains(
        shader,
        "float _BrowCleanupFrameSource;",
        "Brow cleanup pass must expose the cleanup frame source switch.",
    )
    require_contains(
        shader,
        "float4 _BrowCleanupFrameTex_TexelSize;",
        "Brow cleanup pass must know grabbed frame texel size for nearby skin sampling.",
    )
    require_contains(
        shader,
        "float4 _BrowCleanupSourceTex_TexelSize;",
        "Brow cleanup pass must know source-brow mask texel size for soft expansion.",
    )
    require_contains(
        shader,
        "output.grabPos = ComputeGrabScreenPos(output.vertex);",
        "Brow cleanup pass must compute screen-space coordinates for frame sampling.",
    )
    require_contains(
        shader,
        "float3 SampleGrabbedFrameSkin(float4 grabPos)",
        "Brow cleanup pass must restore color from neighboring grabbed-frame skin samples.",
    )
    require_contains(
        shader,
        "float SkinSampleWeight(float3 color)",
        "Brow cleanup pass must reject dark brow-hair samples when estimating skin color.",
    )
    require_contains(
        shader,
        "AccumulateGrabbedSkinSample(",
        "Brow cleanup pass must use weighted grabbed-frame skin samples instead of a raw local average.",
    )
    require_contains(
        shader,
        "AccumulateCameraBackgroundSkinSample(",
        "Brow cleanup pass must use weighted ARCameraBackground skin samples instead of a raw local average.",
    )
    require_not_contains(
        shader,
        "float3 cleanupTint = float3(0.76, 0.61, 0.50);",
        "Brow cleanup must not bake a fixed beige tint before live skin restoration.",
    )
    require_not_contains(
        shader,
        "lerp(pigmentColor, cleanupTint",
        "Brow cleanup pigment pass must not tint cleanup with a fixed skin color.",
    )
    require_contains(
        shader,
        "float3 SampleCameraBackgroundSkin(float4 grabPos)",
        "Brow cleanup pass must restore color from neighboring ARCameraBackground samples.",
    )
    require_contains(
        shader,
        "float3 SampleBrowCleanupFrameSkin(float4 grabPos)",
        "Brow cleanup pass must route skin sampling through the selected frame source.",
    )
    require_contains(
        shader,
        "if (_BrowCleanupFrameSource > 0.5)",
        "Brow cleanup pass must use ARCameraBackground only when the source switch requests it.",
    )
    require_contains(
        shader,
        "tex2Dproj(_BrowCleanupFrameTex, UNITY_PROJ_COORD(samplePos))",
        "Brow cleanup pass must directly sample the grabbed live camera frame.",
    )
    require_contains(
        shader,
        "float cleanupWide = BrowCleanupWideAlpha(maskUv);",
        "Brow cleanup pass must use a widened target-mask zone for original brow peeking.",
    )
    require_contains(
        shader,
        "float BrowCleanupSourceAlpha(float2 baseUv)",
        "Brow cleanup pass must compute source-brow cleanup alpha from unshifted face UVs.",
    )
    require_contains(
        shader,
        "float cleanupSourceRaw = BrowCleanupSourceAlpha(input.uv);",
        "Brow cleanup pass must sample the source-brow mask using original face UVs, not moved target UVs.",
    )
    require_contains(
        shader,
        "float cleanupSource = saturate(cleanupSourceRaw * (1.0 - fullCore * 0.72));",
        "Brow cleanup pass must protect the newly drawn target full/core from source cleanup overpaint.",
    )
    require_contains(
        shader,
        "float cleanupTarget = saturate(cleanupWide + softMask.r - fullCore * 0.82);",
        "Brow cleanup pass must keep a target-mask cleanup zone for near-target peeking.",
    )
    require_contains(
        shader,
        "float cleanupHalo = saturate(browCleanup * max(cleanupSource, cleanupTarget));",
        "Brow cleanup pass must cover the union of original brow and moved target cleanup zones.",
    )
    require_not_contains(
        shader,
        "float cleanupHalo = saturate(browCleanup * (cleanupWide + softMask.r - fullCore * 0.82));",
        "Brow cleanup pass must not rely only on moved target-mask cleanup alpha.",
    )
    require_contains(
        shader,
        "float3 restoredSkin = SampleBrowCleanupFrameSkin(input.grabPos);",
        "Brow cleanup pass must use sampled skin color as the restoration color.",
    )
    require_contains(
        shader,
        "return fixed4(restoredSkin, saturate(alpha));",
        "Brow cleanup pass must alpha-blend sampled skin color back over the original brow.",
    )
    require_contains(
        shader,
        "pigmentColor * 0.42",
        "SmoothRegionMask shader must keep extracted brow fibers dark enough for multiply-like rendering.",
    )
    require_contains(
        shader,
        "float3 pigmentColor = saturate(_RegionColor.rgb);",
        "SmoothRegionMask shader must derive makeup color from recipe _RegionColor rather than baked white PSD pixels.",
    )

    print("brow_unity_contract_ok")


if __name__ == "__main__":
    main()
