#!/usr/bin/env python3
"""Verify the approved brow landmark runtime privacy contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCH_DOC = ROOT / "docs/architecture/eyebrow-ar-rendering-design.md"
PRODUCT_DOC = ROOT / "docs/product/eyebrow-makeup-feature.md"
QA_RUNBOOK = ROOT / "docs/runbooks/eyebrow-makeup-qa-runbook.md"
DEV_LOG = ROOT / "docs/roadmaps/active/eyebrow-makeup-development-log.md"
IOS_PODFILE = ROOT / "rn/MakeupARValidation/ios/Podfile"
IOS_PODFILE_LOCK = ROOT / "rn/MakeupARValidation/ios/Podfile.lock"
IOS_XCODE_PROJECT = (
    ROOT / "rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj"
)
LOCAL_MEDIA_SWIFT = (
    ROOT / "rn/MakeupARValidation/ios/MakeupARValidation/MakeupARLocalMedia.swift"
)
MEDIAPIPE_SWIFT = (
    ROOT
    / "rn/MakeupARValidation/ios/MakeupARValidation/MakeupARMediaPipeFaceLandmarker.swift"
)
MEDIAPIPE_MODEL = (
    ROOT / "rn/MakeupARValidation/ios/MakeupARValidation/face_landmarker.task"
)
RN_APP = ROOT / "rn/MakeupARValidation/App.tsx"
UNITY_MEDIAPIPE_RUNTIME = (
    ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E7MediaPipeBrowLandmarkRuntime.cs"
)
UNITY_MEDIAPIPE_IOS_BRIDGE = (
    ROOT
    / "unity/MakeupARUnityValidation/Assets/Plugins/iOS/E7MediaPipeBrowLandmarkBridge.mm"
)
UNITY_RN_BRIDGE = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
UNITY_SCRIPTS = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts"
UNITY_IOS_PLUGINS = ROOT / "unity/MakeupARUnityValidation/Assets/Plugins/iOS"

FORBIDDEN_RAW_FRAME_STORAGE_TOKENS = (
    "WriteAllBytes",
    "FileStream",
    "UIImageWriteToSavedPhotosAlbum",
    "PHAssetChangeRequest",
    "AVAssetWriter",
    "URLSession",
    "http://",
    "https://",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read(path: Path) -> str:
    require(path.exists(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def require_contains(text: str, needle: str, message: str) -> None:
    require(needle in text, message)


def iter_mediapipe_runtime_files() -> list[Path]:
    return sorted(
        path
        for path in (UNITY_MEDIAPIPE_RUNTIME, UNITY_MEDIAPIPE_IOS_BRIDGE)
        if path.exists()
    )


def main() -> None:
    arch = read(ARCH_DOC)
    product = read(PRODUCT_DOC)
    qa = read(QA_RUNBOOK)
    log = read(DEV_LOG)
    podfile = read(IOS_PODFILE)
    podfile_lock = read(IOS_PODFILE_LOCK)
    xcode_project = read(IOS_XCODE_PROJECT)
    local_media = read(LOCAL_MEDIA_SWIFT)
    mediapipe_swift = read(MEDIAPIPE_SWIFT)
    rn_app = read(RN_APP)
    unity_mediapipe_runtime = read(UNITY_MEDIAPIPE_RUNTIME)
    unity_mediapipe_ios_bridge = read(UNITY_MEDIAPIPE_IOS_BRIDGE)
    unity_rn_bridge = read(UNITY_RN_BRIDGE)

    require_contains(
        arch,
        "## Brow Landmark Runtime Privacy Contract",
        "Architecture doc must include the approved brow landmark privacy contract.",
    )
    require_contains(
        arch,
        "User approval recorded on 2026-06-30",
        "Architecture doc must record the explicit user approval date.",
    )
    require_contains(
        arch,
        "MediaPipe Face Landmarker",
        "Architecture doc must name the approved on-device detector.",
    )
    require_contains(
        arch,
        "face_landmarker.task",
        "Architecture doc must identify the expected app-bundled model file.",
    )
    require_contains(
        arch,
        "raw camera frames are memory-only",
        "Architecture doc must forbid persistent raw frame retention.",
    )
    require_contains(
        arch,
        "landmark, bbox, confidence, timing, and status numbers",
        "Architecture doc must restrict detector diagnostics to numeric metadata.",
    )
    require_contains(
        arch,
        "user-triggered product capture exception",
        "Architecture doc must separate user-triggered photo/video saves from detector frames.",
    )

    require_contains(
        product,
        "MediaPipe Face Landmarker is an approved brow-runtime exception",
        "Product doc must record MediaPipe as an approved exception to the original no-AI scope.",
    )
    require_contains(
        product,
        "no raw frame storage or upload",
        "Product doc must preserve the no raw frame storage/upload condition.",
    )
    require_contains(
        qa,
        "verify_brow_landmark_privacy_contract.py",
        "QA runbook must include the privacy-contract verifier.",
    )
    require_contains(
        log,
        "2026-06-30 MediaPipe brow runtime privacy approval",
        "Development log must record the approval checkpoint.",
    )

    require_contains(
        podfile,
        "MediaPipeTasksVision",
        "iOS Podfile must install the approved MediaPipe Tasks Vision dependency.",
    )
    require_contains(
        podfile_lock,
        "MediaPipeTasksVision",
        "iOS Podfile.lock must be refreshed with MediaPipeTasksVision.",
    )
    require(
        MEDIAPIPE_MODEL.exists() and MEDIAPIPE_MODEL.stat().st_size > 1_000_000,
        "App bundle must include the downloaded face_landmarker.task model.",
    )
    require_contains(
        xcode_project,
        "face_landmarker.task",
        "Xcode project must copy face_landmarker.task into the app bundle.",
    )
    require_contains(
        xcode_project,
        "MakeupARMediaPipeFaceLandmarker.swift",
        "Xcode project must compile the MediaPipe dependency sentinel.",
    )
    require_contains(
        mediapipe_swift,
        "import MediaPipeTasksVision",
        "MediaPipe Swift sentinel must import MediaPipeTasksVision to prove linkage.",
    )
    require_contains(
        mediapipe_swift,
        "Bundle.main.path(forResource: \"face_landmarker\", ofType: \"task\")",
        "MediaPipe Swift sentinel must resolve the bundled face_landmarker.task model.",
    )
    require_contains(
        mediapipe_swift,
        '@_cdecl("E7MediaPipeAppDetectBrowLandmarksPng")',
        "Swift MediaPipe runtime must expose an app-target C symbol callable through the UnityFramework bridge.",
    )
    require_contains(
        mediapipe_swift,
        '@_cdecl("E7MediaPipeAppReleaseCString")',
        "Swift MediaPipe runtime must expose an app-target release function for bridge-owned C strings.",
    )
    require_contains(
        mediapipe_swift,
        "FaceLandmarkerOptions",
        "Swift MediaPipe runtime must configure FaceLandmarkerOptions.",
    )
    require_contains(
        mediapipe_swift,
        "FaceLandmarker",
        "Swift MediaPipe runtime must instantiate the on-device Face Landmarker.",
    )
    require_contains(
        mediapipe_swift,
        "leftEyebrowConnections",
        "Swift MediaPipe runtime must extract left eyebrow landmarks from canonical indices.",
    )
    require_contains(
        mediapipe_swift,
        "rightEyebrowConnections",
        "Swift MediaPipe runtime must extract right eyebrow landmarks from canonical indices.",
    )
    require_contains(
        mediapipe_swift,
        '"mediapipe_face_landmarker_runtime_brow_landmarks"',
        "Swift MediaPipe runtime must label numeric brow landmark output with a stable source.",
    )

    require_contains(
        unity_mediapipe_runtime,
        "raw camera frames are memory-only",
        "Unity MediaPipe runtime must carry the raw-frame retention policy.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "landmark, bbox, confidence",
        "Unity MediaPipe runtime must carry the numeric-diagnostics policy.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "E7MediaPipeDetectBrowLandmarksPng",
        "Unity MediaPipe runtime must call the native detector symbol.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "E7MediaPipeReleaseCString",
        "Unity MediaPipe runtime must release native detector result strings.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "e7_mediapipe_brow_landmarks",
        "Unity MediaPipe runtime must emit a brow landmark event for RN diagnostics.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "rawCameraFrameStored\":false",
        "Unity MediaPipe runtime event must explicitly report no raw frame storage.",
    )
    require_contains(
        unity_mediapipe_runtime,
        "offDeviceUpload\":false",
        "Unity MediaPipe runtime event must explicitly report no off-device upload.",
    )
    for forbidden in FORBIDDEN_RAW_FRAME_STORAGE_TOKENS:
        require(
            forbidden not in unity_mediapipe_runtime,
            f"Unity MediaPipe runtime must not use {forbidden}.",
        )

    require_contains(
        unity_mediapipe_ios_bridge,
        "E7MediaPipeDetectBrowLandmarksPng",
        "UnityFramework iOS bridge must define the Unity-facing detector symbol so UnityFramework links standalone.",
    )
    require_contains(
        unity_mediapipe_ios_bridge,
        "E7MediaPipeReleaseCString",
        "UnityFramework iOS bridge must define the Unity-facing release symbol so UnityFramework links standalone.",
    )
    require_contains(
        unity_mediapipe_ios_bridge,
        "E7MediaPipeAppDetectBrowLandmarksPng",
        "UnityFramework iOS bridge must forward to the app-target Swift MediaPipe detector.",
    )
    require_contains(
        unity_mediapipe_ios_bridge,
        "E7MediaPipeAppReleaseCString",
        "UnityFramework iOS bridge must forward releases to the app-target Swift release function.",
    )
    require_contains(
        unity_mediapipe_ios_bridge,
        "dlsym(RTLD_DEFAULT",
        "UnityFramework iOS bridge must use runtime symbol lookup for app-target MediaPipe functions.",
    )

    require_contains(
        unity_rn_bridge,
        "EnsureMediaPipeBrowLandmarkRuntime",
        "RNBridge must create/configure the Unity MediaPipe brow landmark runtime.",
    )
    require_contains(
        unity_rn_bridge,
        "SendE7MediaPipeBrowLandmarkEvent",
        "RNBridge must expose a dedicated MediaPipe brow landmark event sender.",
    )
    require_contains(
        unity_rn_bridge,
        "SetRuntimeRequested",
        "RNBridge must keep MediaPipe brow detection request control for opt-in diagnostics.",
    )
    require_contains(
        rn_app,
        "e7_mediapipe_brow_landmarks",
        "RN HUD must recognize MediaPipe brow landmark events.",
    )
    require_contains(
        rn_app,
        "formatE7MediaPipeBrowLandmarkSummary",
        "RN HUD must summarize MediaPipe brow landmark diagnostics.",
    )

    require_contains(
        local_media,
        "PHPhotoLibrary.requestAuthorization(for: .addOnly)",
        "User-triggered product capture must use add-only Photos permission.",
    )
    require(
        "URLSession" not in local_media
        and "http://" not in local_media
        and "https://" not in local_media,
        "Local product capture module must not upload saved media.",
    )

    for runtime_file in iter_mediapipe_runtime_files():
        text = read(runtime_file)
        relative = runtime_file.relative_to(ROOT)
        require_contains(
            text,
            "raw camera frames are memory-only",
            f"{relative} must carry the raw-frame retention policy.",
        )
        require_contains(
            text,
            "landmark, bbox, confidence",
            f"{relative} must carry the numeric-diagnostics policy.",
        )
        for forbidden in FORBIDDEN_RAW_FRAME_STORAGE_TOKENS:
            require(
                forbidden not in text,
                f"{relative} must not use {forbidden} in MediaPipe runtime code.",
            )

    print("brow_landmark_privacy_contract_ok")


if __name__ == "__main__":
    main()
