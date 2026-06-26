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
DEFAULT_ROUTES = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs"
)
DEFAULT_BROW_MASK = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/"
    "brow-drawn-mask-v1.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify brow Unity contract.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--rn-app", type=Path, default=DEFAULT_RN_APP)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--mask", type=Path, default=DEFAULT_BROW_MASK)
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
    routes = read_text(resolve(repo, args.routes))
    mask_path = resolve(repo, args.mask)

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
    require_contains(
        rn_app,
        "| 'brow-drawn-mask-v1'",
        "RN mask texture ids must include brow-drawn-mask-v1.",
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
        r"case\s+\"brow\"\s*:\s*return\s+\"brow-drawn-mask-v1\"",
        "RNBridge GetDefaultMaskTextureId must return brow-drawn-mask-v1.",
    )
    require_match(
        rn_bridge,
        r"region\s*==\s*\"brow\"\s*&&\s*\w+\s*==\s*\"brow-drawn-mask-v1\"",
        "RNBridge NormalizeMaskTextureId must accept brow-drawn-mask-v1.",
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
        r"case\s+\"brow\"\s*:\s*return\s+\"brow-drawn-mask-v1\"",
        "E3RegionMaskOverlay GetDefaultMaskTextureId must return brow-drawn-mask-v1.",
    )
    require_match(
        overlay,
        r"region\s*==\s*\"brow\"\s*&&\s*\w+\s*==\s*\"brow-drawn-mask-v1\"",
        "E3RegionMaskOverlay NormalizeMaskTextureId must accept brow-drawn-mask-v1.",
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

    print("brow_unity_contract_ok")


if __name__ == "__main__":
    main()
