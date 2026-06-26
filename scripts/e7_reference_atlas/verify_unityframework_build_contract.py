#!/usr/bin/env python3
"""Verify UnityFramework build glue needed for ARKit/Swift linkage."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_SETUP = Path(
    "unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs"
)
DEFAULT_BUILD_SCRIPT = Path("scripts/build_m3_unityframework.sh")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify UnityFramework build contract.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, message: str) -> None:
    require(needle in text, message)


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    setup = read_text(resolve(repo, args.setup))
    build_script = read_text(resolve(repo, args.build_script))

    require_contains(
        setup,
        "EnsureArKitNativePluginLinks(pathToBuiltProject, project, targetGuid);",
        "Unity postprocess must configure native ARKit plugin links.",
    )
    for needle in (
        "UnityARKit.m",
        "libUnityARKit.a",
        "libUnityARKitFaceTracking.a",
        "CoreLocation.framework",
        "RoomPlan.framework",
        "Vision.framework",
    ):
        require_contains(
            setup,
            needle,
            f"Unity postprocess must include {needle}.",
        )

    require_contains(
        setup,
        "EnsureSwiftCompatibilityLinks(project, targetGuid);",
        "Unity postprocess must configure Swift compatibility links.",
    )
    require_contains(
        setup,
        "$(TOOLCHAIN_DIR)/usr/lib/swift/iphoneos",
        "UnityFramework target must search the Xcode iPhoneOS Swift library path.",
    )
    for flag in (
        "-lswiftCompatibility51",
        "-lswiftCompatibility56",
        "-lswiftCompatibilityConcurrency",
    ):
        require_contains(
            setup,
            flag,
            f"UnityFramework target must link {flag}.",
        )

    require_contains(
        build_script,
        'grep -q "Build Finished, Result: Failure" "$UNITY_EXPORT_LOG"',
        "Build script must detect Unity export failures even when Unity exits 0.",
    )
    for needle in (
        "Unity.XR.ARKit.cpp",
        "Unity.XR.ARKit_CodeGen.c",
        "Unity.XR.ARKit.FaceTracking.cpp",
        "Unity.XR.ARKit.FaceTracking_CodeGen.c",
        "Data/UnitySubsystems/UnityARKit/UnitySubsystemsManifest.json",
    ):
        require_contains(
            build_script,
            needle,
            f"Build script must verify generated Unity ARKit entry {needle}.",
        )
    require_contains(
        build_script,
        "Unity export failed. Full log:",
        "Build script must report the Unity export log on export failure.",
    )

    print("unityframework_build_contract_ok")


if __name__ == "__main__":
    main()
