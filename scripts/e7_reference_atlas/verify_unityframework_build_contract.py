#!/usr/bin/env python3
"""Verify UnityFramework build glue needed for ARKit/Swift linkage."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_SETUP = Path(
    "unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs"
)
DEFAULT_BUILD_SCRIPT = Path("scripts/build_m3_unityframework.sh")
DEFAULT_PBXPROJ = Path(
    "rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj"
)
DEFAULT_PODFILE = Path("rn/MakeupARValidation/ios/Podfile")
DEFAULT_ROADMAP = Path("docs/roadmaps/active/mediapipe-first-ar-makeup-goal-plan-ko.md")
DEFAULT_RUNBOOK = Path("docs/runbooks/mediapipe-first-real-device-qa-ko.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify UnityFramework build contract.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--setup", type=Path, default=DEFAULT_SETUP)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("--pbxproj", type=Path, default=DEFAULT_PBXPROJ)
    parser.add_argument("--podfile", type=Path, default=DEFAULT_PODFILE)
    parser.add_argument("--roadmap", type=Path, default=DEFAULT_ROADMAP)
    parser.add_argument("--runbook", type=Path, default=DEFAULT_RUNBOOK)
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
    pbxproj = read_text(resolve(repo, args.pbxproj))
    podfile = read_text(resolve(repo, args.podfile))
    roadmap = read_text(resolve(repo, args.roadmap))
    runbook = read_text(resolve(repo, args.runbook))

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
    for needle in (
        "CODE_SIGNING_ALLOWED=NO",
        'ditto "$EXPORT_PATH/Data" "$PRODUCT_FRAMEWORK/Data"',
        'ditto "$PRODUCT_FRAMEWORK" "$RN_FRAMEWORK"',
        'ditto "$PRODUCT_FRAMEWORK" "$PACKAGE_FRAMEWORK"',
        'grep -n "BUILD SUCCEEDED" "$XCODE_BUILD_LOG"',
        "m3-repro-artifact-verification",
    ):
        require_contains(
            build_script,
            needle,
            f"Build script must preserve UnityFramework sync/artifact proof step: {needle}.",
        )
    require(
        "DEVELOPMENT_TEAM =" not in pbxproj
        and "PROVISIONING_PROFILE_SPECIFIER" not in pbxproj
        and "TARGETED_DEVICE_IDENTIFIER" not in pbxproj
        and "UDID" not in pbxproj,
        "RN iOS project must not hard-code a signing team, provisioning profile, or device id.",
    )
    for needle in (
        "MakeupARMediaPipeFaceLandmarker.swift in Sources",
        "MakeupARMediaPipeFrameSource.swift in Sources",
        "face_landmarker.task in Resources",
        "SWIFT_OBJC_BRIDGING_HEADER",
    ):
        require_contains(
            pbxproj,
            needle,
            f"RN iOS project must include MediaPipe native build item: {needle}.",
        )
    require_contains(
        podfile,
        "pod 'MediaPipeTasksVision', '0.10.14'",
        "Podfile must pin the approved MediaPipeTasksVision dependency.",
    )
    require_contains(
        roadmap,
        "Before building, report:",
        "Roadmap must preserve the explicit real-device build approval gate.",
    )
    require_contains(
        runbook,
        "Before a real-device build, stop and ask for approval.",
        "Runbook must preserve the explicit real-device build approval gate.",
    )
    require(
        "Do not add a default UDID or `DEVELOPMENT_TEAM` to the repo." in runbook
        and "Do not hard-code a new UDID or `DEVELOPMENT_TEAM` as repo defaults." in roadmap,
        "Build docs must forbid repo-default signing team or device ids.",
    )

    print("unityframework_build_contract_ok")


if __name__ == "__main__":
    main()
