#!/usr/bin/env python3
"""Verify the user-triggered local photo/video capture contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SWIFT_FILE = ROOT / "rn/MakeupARValidation/ios/MakeupARValidation/MakeupARLocalMedia.swift"
INFO_PLIST = ROOT / "rn/MakeupARValidation/ios/MakeupARValidation/Info.plist"
PBXPROJ = ROOT / "rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj"
WORKSPACE = (
    ROOT
    / "rn/MakeupARValidation/ios/MakeupARValidation.xcworkspace/contents.xcworkspacedata"
)
APP_TSX = ROOT / "rn/MakeupARValidation/App.tsx"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, message: str) -> None:
    require(needle in text, message)


def main() -> None:
    swift = read(SWIFT_FILE)
    info = read(INFO_PLIST)
    pbxproj = read(PBXPROJ)
    workspace = read(WORKSPACE)
    app = read(APP_TSX)

    require_contains(
        swift,
        "@objc(MakeupARLocalMedia)",
        "Swift local media module must be exposed to React Native.",
    )
    require_contains(
        swift,
        "func capturePhoto(",
        "Swift local media module must expose capturePhoto.",
    )
    require_contains(
        swift,
        "UIGraphicsImageRenderer",
        "Photo capture must render the current final app view locally.",
    )
    require_contains(
        swift,
        "PHPhotoLibrary.requestAuthorization(for: .addOnly)",
        "Photo/video saving must request add-only Photos permission.",
    )
    require_contains(
        swift,
        "UIImageWriteToSavedPhotosAlbum",
        "Photo capture must save user-triggered images to the local photo library.",
    )
    require_contains(
        swift,
        "recorder.startCapture",
        "Video capture must record the local final app screen without server upload.",
    )
    require_contains(
        swift,
        "AVAssetWriter",
        "Video capture must write a local movie file before saving to Photos.",
    )
    require_contains(
        swift,
        "PHAssetChangeRequest.creationRequestForAssetFromVideo",
        "Video capture must save user-triggered videos to the local photo library.",
    )
    require(
        "URLSession" not in swift and "http://" not in swift and "https://" not in swift,
        "Local media capture module must not upload captured media.",
    )

    require_contains(
        info,
        "NSPhotoLibraryAddUsageDescription",
        "Info.plist must explain add-only Photos usage for local saves.",
    )
    require_contains(
        pbxproj,
        "MakeupARLocalMedia.swift",
        "Xcode project must include MakeupARLocalMedia.swift.",
    )
    require_contains(
        workspace,
        'location = "group:Pods/Pods.xcodeproj"',
        "Workspace must reference the repo-local Pods project.",
    )
    require(
        "/private/tmp/" not in workspace,
        "Workspace must not reference stale temporary Pods projects.",
    )
    require_contains(
        app,
        "NativeModules.MakeupARLocalMedia",
        "RN app must call the local media native module.",
    )
    require_contains(
        app,
        "Save Photo",
        "RN UI must expose user-triggered photo save.",
    )
    require_contains(
        app,
        "Record Video",
        "RN UI must expose user-triggered video recording.",
    )

    print("ios_local_media_capture_contract_ok")


if __name__ == "__main__":
    main()
