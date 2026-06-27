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
DEFAULT_BROW_MASK_ID = "brow-soft-arch-fine-hair-v1"
LEGACY_BROW_MASK_ID = "brow-drawn-mask-v1"
SELECTED_BROW_MASK_IDS = (
    DEFAULT_BROW_MASK_ID,
    "brow-back-arch-soft-mix-v1",
    "brow-slim-tail-fine-hair-v1",
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
        for mask_id in (*SELECTED_BROW_MASK_IDS, LEGACY_BROW_MASK_ID)
    ]
    mask_paths.extend(resolve(repo, mask) for mask in args.mask)

    for mask_path in mask_paths:
        require(mask_path.exists(), f"Missing brow mask asset: {mask_path}")

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
    for mask_id in SELECTED_BROW_MASK_IDS:
        require_contains(
            rn_app,
            f"| '{mask_id}'",
            f"RN mask texture ids must include {mask_id}.",
        )
        require_contains(
            rn_app,
            f"id: '{mask_id}'",
            f"RN brow HUD options must include {mask_id}.",
        )

    require_contains(
        rn_app,
        f"brow: '{DEFAULT_BROW_MASK_ID}'",
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
    for mask_id in (*SELECTED_BROW_MASK_IDS, LEGACY_BROW_MASK_ID):
        require_contains(
            rn_bridge,
            f'"{mask_id}"',
            f"RNBridge NormalizeMaskTextureId must accept {mask_id}.",
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
        "MaskSpreadX = NormalizeMaskSpread(layer.maskSpreadX)",
        "RNBridge must normalize layer maskSpreadX into parsed layers.",
    )
    require_contains(
        rn_bridge,
        "MaskOffsetY = NormalizeMaskOffset(layer.maskOffsetY)",
        "RNBridge must normalize layer maskOffsetY into parsed layers.",
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
    for mask_id in (*SELECTED_BROW_MASK_IDS, LEGACY_BROW_MASK_ID):
        require_contains(
            overlay,
            f'"{mask_id}"',
            f"E3RegionMaskOverlay NormalizeMaskTextureId must accept {mask_id}.",
        )
    require_contains(
        overlay,
        'case "natural_brow":',
        "E3RegionMaskOverlay BuildMaterialColor must tune natural_brow.",
    )
    require_contains(
        overlay,
        'case "soft_brow":',
        "E3RegionMaskOverlay BuildMaterialColor must tune soft_brow.",
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
        "MaskSpreadX = Mathf.Clamp(maskSpreadX, -0.16f, 0.16f)",
        "E3RegionMaskOverlay must clamp mask spread X.",
    )
    require_contains(
        overlay,
        "MaskOffsetY = Mathf.Clamp(maskOffsetY, -0.08f, 0.08f)",
        "E3RegionMaskOverlay must clamp mask offset Y.",
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
        "maskUv.x = saturate(0.5 + (maskUv.x - 0.5) / max(1.0 + _MaskSpreadX, 0.001));",
        "SmoothRegionMask shader must spread eyebrow mask sampling around the centerline.",
    )
    require_contains(
        shader,
        "maskUv.y = saturate(maskUv.y - _MaskOffset.y);",
        "SmoothRegionMask shader must still apply vertical mask offset before sampling.",
    )

    print("brow_unity_contract_ok")


if __name__ == "__main__":
    main()
