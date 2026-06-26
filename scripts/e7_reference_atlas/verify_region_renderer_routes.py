#!/usr/bin/env python3
"""Verify explicit per-region Unity makeup renderer routes."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_ROUTES = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs"
)
DEFAULT_RN_BRIDGE = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
DEFAULT_OVERLAY = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
)

EXPECTED_RENDERERS = {
    "lip": "lip-smooth-region-mask-renderer",
    "cheek": "cheek-smooth-region-mask-renderer",
    "eye": "eye-smooth-region-mask-renderer",
    "brow": "brow-smooth-region-mask-renderer",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify per-region renderer routes.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
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


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    routes_path = resolve(repo, args.routes)
    rn_bridge_path = resolve(repo, args.rn_bridge)
    overlay_path = resolve(repo, args.overlay)

    routes = read_text(routes_path)
    rn_bridge = read_text(rn_bridge_path)
    overlay = read_text(overlay_path)

    require('SmoothRegionMaskMode = "smooth-region-mask"' in routes,
            "Routes must define the smooth-region-mask renderer mode constant.")
    require('SmoothRegionMaskBackend = "E3RegionMaskOverlay"' in routes,
            "Routes must define E3RegionMaskOverlay as the current smooth mask backend.")

    for region, renderer_id in EXPECTED_RENDERERS.items():
        require_match(
            routes,
            rf"\"{region}\".*\"{renderer_id}\".*SmoothRegionMaskMode.*SmoothRegionMaskBackend",
            f"Route for {region} must map to {renderer_id} through E3RegionMaskOverlay.",
        )

    require("MakeupRegionRendererRoutes.Regions" in rn_bridge,
            "RNBridge must derive region order from the renderer route table.")
    require("MakeupRegionRendererRoutes.NormalizeRegion" in rn_bridge,
            "RNBridge must normalize regions through the route table.")
    require_match(
        rn_bridge,
        r"RegionRendererId\s*=\s*MakeupRegionRendererRoutes\.Resolve\(region\)\.RendererId",
        "RNBridge parsed layers must store the resolved region renderer id.",
    )
    require("rendererId=" in rn_bridge,
            "RNBridge logs/events must include rendererId for region dispatch/result tracing.")

    require("RegionRendererId" in overlay,
            "E3RegionMaskOverlay results must expose RegionRendererId.")
    require("MakeupRegionRendererRoutes.Resolve" in overlay,
            "E3RegionMaskOverlay must resolve the route for applied regions.")
    require("rendererId=" in overlay,
            "E3RegionMaskOverlay logs must include rendererId.")

    print("region_renderer_routes_ok")


if __name__ == "__main__":
    main()
