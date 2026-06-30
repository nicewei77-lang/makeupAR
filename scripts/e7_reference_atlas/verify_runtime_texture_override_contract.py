#!/usr/bin/env python3
"""Verify the RN-to-Unity runtime PNG texture override contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_TSX = ROOT / "rn/MakeupARValidation/App.tsx"
MANIFEST = ROOT / "unity/MakeupARUnityValidation/Packages/manifest.json"
RN_BRIDGE = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
OVERLAY = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, message: str) -> None:
    require(needle in text, message)


def main() -> None:
    app = read(APP_TSX)
    manifest = read(MANIFEST)
    rn_bridge = read(RN_BRIDGE)
    overlay = read(OVERLAY)

    require_contains(
        app,
        "export type RuntimeTextureOverrideMode",
        "RN must define a typed runtime texture override mode.",
    )
    require_contains(
        app,
        "runtimeTextureOverrideMode: RuntimeTextureOverrideMode",
        "RN region tuning must carry the override mode.",
    )
    require_contains(
        app,
        "runtimeTextureOverridePath: string",
        "RN region tuning must carry the override PNG path.",
    )
    require_contains(
        app,
        "runtimeTextureOverrideMode",
        "RN payload must send the override mode.",
    )
    require_contains(
        app,
        "runtimeTextureOverridePath",
        "RN payload must send the override PNG path.",
    )

    for source in (rn_bridge, overlay):
        require_contains(
            source,
            "runtimeTextureOverrideMode",
            "Unity C# payload classes must receive runtimeTextureOverrideMode.",
        )
        require_contains(
            source,
            "runtimeTextureOverridePath",
            "Unity C# payload classes must receive runtimeTextureOverridePath.",
        )

    require_contains(
        rn_bridge,
        "RuntimeTextureOverrideMode = NormalizeRuntimeTextureOverrideMode",
        "RNBridge must normalize and pass the override mode into parsed recipe layers.",
    )
    require_contains(
        rn_bridge,
        "RuntimeTextureOverridePath = NormalizeRuntimeTextureOverridePath",
        "RNBridge must normalize and pass the override path into parsed recipe layers.",
    )
    require_contains(
        rn_bridge,
        "layer.RuntimeTextureOverrideMode",
        "RNBridge must pass the override mode into E3RegionMaskOverlay.",
    )
    require_contains(
        rn_bridge,
        "layer.RuntimeTextureOverridePath",
        "RNBridge must pass the override path into E3RegionMaskOverlay.",
    )

    require_contains(
        overlay,
        "Application.persistentDataPath",
        "Unity override loader must resolve Documents PNGs under persistentDataPath.",
    )
    require_contains(
        overlay,
        "Path.GetFullPath",
        "Unity override loader must normalize paths before loading.",
    )
    require_contains(
        overlay,
        "File.ReadAllBytes",
        "Unity override loader must read PNG bytes from disk.",
    )
    require_contains(
        overlay,
        ".LoadImage(",
        "Unity override loader must replace textures using Texture2D.LoadImage().",
    )
    require_contains(
        manifest,
        '"com.unity.modules.imageconversion": "1.0.0"',
        "Unity manifest must include the built-in ImageConversion module for PNG LoadImage.",
    )
    require_contains(
        overlay,
        "RuntimeMaskTextures",
        "Unity override loader must cache runtime PNG textures.",
    )
    require_contains(
        overlay,
        "LastWriteTimeUtc",
        "Unity override loader must invalidate cache entries when PNG files change.",
    )
    require_contains(
        overlay,
        "RuntimeTextureOverrideStatus",
        "Unity apply diagnostics must report runtime override load status.",
    )
    require_contains(
        overlay,
        "runtime_texture_override_loaded",
        "Unity override loader must log successful runtime PNG loads.",
    )

    print("runtime_texture_override_contract_ok")


if __name__ == "__main__":
    main()
