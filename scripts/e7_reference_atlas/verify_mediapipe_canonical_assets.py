#!/usr/bin/env python3
"""Verify MediaPipe canonical makeup asset routing and import settings."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
RN_APP = Path("rn/MakeupARValidation/App.tsx")
ARCHITECTURE_DOC = Path(
    "docs/architecture/mediapipe-first-ar-makeup-architecture-ko.md"
)

CANONICAL_MASKS = (
    "psd-arcore-lip-style-v1.png",
    "psd-arcore-lip-mask-v1.png",
    "psd-arcore-cheek-undereye-v1.png",
    "psd-arcore-cheek-asia-z-v1.png",
    "psd-arcore-cheek-sunkissed-v1.png",
    "psd-arcore-cheek-daily-oval-v1.png",
    "psd-arcore-cheek-undereye2-v1.png",
    "psd-arcore-cheek-lovely-round-v1.png",
    "psd-arcore-cheek-lifted-diagonal-v1.png",
    "psd-arcore-brow-semi-arch-v1.png",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify MediaPipe canonical asset contract."
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    return parser.parse_args()


def read(path: Path) -> str:
    if not path.exists():
        raise AssertionError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_texture_import_settings(meta: str, filename: str) -> None:
    require("TextureImporter:" in meta, f"{filename} must be imported as a texture.")
    require("sRGBTexture: 0" in meta, f"{filename} must sample as linear mask data.")
    require("isReadable: 1" in meta, f"{filename} must remain readable for diagnostics.")
    require(
        "textureCompression: 0" in meta,
        f"{filename} must avoid compressed mask artifacts.",
    )
    require("wrapU: 1" in meta and "wrapV: 1" in meta, f"{filename} must clamp UVs.")


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    rn_app = read(repo / RN_APP)
    architecture_doc = read(repo / ARCHITECTURE_DOC)

    for filename in CANONICAL_MASKS:
        path = repo / MASK_DIR / filename
        require(path.exists(), f"Missing MediaPipe canonical mask: {path}")
        require((path.with_suffix(path.suffix + ".meta")).exists(), f"Missing meta: {path}.meta")
        require_texture_import_settings(read(path.with_suffix(path.suffix + ".meta")), filename)

    require(
        "lip: 'psd-arcore-lip-style-v1'" in rn_app,
        "RN default lip mask must be the MediaPipe/ARCore canonical lip asset.",
    )
    require(
        "cheek: 'psd-arcore-cheek-undereye-v1'" in rn_app,
        "RN default cheek mask must be a MediaPipe/ARCore canonical cheek asset.",
    )
    require(
        "brow: PSD_ARCORE_BROW_MASK_TEXTURE_ID" in rn_app,
        "RN default brow mask must be a MediaPipe/ARCore canonical brow asset.",
    )
    require(
        "MediaPipe lip" in rn_app
        and "MediaPipe flat" in rn_app
        and "Vision diagnostic" in rn_app
        and "Legacy atlas diagnostic" in rn_app
        and "Legacy mask" in rn_app
        and "Canonical lip" not in rn_app
        and "Canonical flat" not in rn_app
        and "label: 'PSD ARCore'" not in rn_app
        and "label: 'PSD flat'" not in rn_app,
        "RN product labels must separate canonical product assets from diagnostic sources.",
    )
    require(
        "MediaPipe canonical face space" in architecture_doc
        and "ARKit UV" in architecture_doc
        and "aspect-fill" in architecture_doc,
        "Architecture doc must record MediaPipe canonical ownership and projection policy.",
    )

    print("mediapipe_canonical_assets_ok")


if __name__ == "__main__":
    main()
