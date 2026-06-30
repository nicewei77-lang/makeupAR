#!/usr/bin/env python3
"""Verify the MediaPipe-first product runtime contract."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify MediaPipe-first product runtime guardrails."
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


def count_csharp_int_array_entries(source: str, array_name: str) -> int:
    match = re.search(rf"{array_name}\s*=\s*\{{(?P<body>.*?)\}};", source, re.S)
    if not match:
        raise AssertionError(f"Missing C# int array: {array_name}")
    return len(re.findall(r"\b\d+\b", match.group("body")))


def section_between(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    if start_index < 0:
        raise AssertionError(f"Missing section start: {start}")
    end_index = source.find(end, start_index + len(start))
    if end_index < 0:
        raise AssertionError(f"Missing section end after {start}: {end}")
    return source[start_index:end_index]


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    swift_runtime = read(
        repo
        / "rn/MakeupARValidation/ios/MakeupARValidation/MakeupARMediaPipeFaceLandmarker.swift"
    )
    swift_frame_source = read(
        repo
        / "rn/MakeupARValidation/ios/MakeupARValidation/MakeupARMediaPipeFrameSource.swift"
    )
    xcode_project = read(
        repo
        / "rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj"
    )
    unity_runtime_path = (
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/E7MediaPipeFullFaceRuntime.cs"
    )
    unity_runtime = read(unity_runtime_path)
    packet_dto = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeFaceLandmarkPacket.cs"
    )
    frame_smoother = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeFaceFrameSmoother.cs"
    )
    region_solver = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeRegionSolver.cs"
    )
    region_overlay_renderer = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeRegionOverlayRenderer.cs"
    )
    canonical_region_mesh_builder = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeCanonicalRegionMeshBuilder.cs"
    )
    lip_region_renderer = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeLipRegionRenderer.cs"
    )
    brow_region_renderer = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeBrowRegionRenderer.cs"
    )
    cheek_region_renderer = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeCheekRegionRenderer.cs"
    )
    full_face_mesh_renderer = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeFullFaceMeshRenderer.cs"
    )
    canonical_face_mesh = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeCanonicalFaceMesh.cs"
    )
    viewport_projection = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Scripts/MediaPipe/MediaPipeViewportProjection.cs"
    )
    renderer_routes = read(
        repo / "unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs"
    )
    ios_bridge = read(
        repo
        / "unity/MakeupARUnityValidation/Assets/Plugins/iOS/E7MediaPipeFullFaceBridge.mm"
    )
    rn_bridge = read(repo / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
    face_status_reporter = read(
        repo / "unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs"
    )
    rn_app = read(repo / "rn/MakeupARValidation/App.tsx")
    swift_full_face_runtime = section_between(
        swift_runtime,
        "private enum MakeupARMediaPipeFullFaceRuntime",
        "private enum MakeupARMediaPipeBrowRuntime",
    )
    swift_brow_runtime = section_between(
        swift_runtime,
        "private enum MakeupARMediaPipeBrowRuntime",
        '@_cdecl("E7MediaPipeAppDetectFullFaceBgra")',
    )

    require(
        "import MediaPipeTasksVision" in swift_runtime,
        "Swift runtime must import MediaPipeTasksVision.",
    )
    require(
        "MPImage(" in swift_full_face_runtime
        and "pixelBuffer:" in swift_full_face_runtime,
        "Product MediaPipe runtime must use MPImage(pixelBuffer:) instead of PNG decode.",
    )
    require(
        "options.runningMode = .video" in swift_full_face_runtime,
        "Product MediaPipe runtime must use video mode for timestamped frames.",
    )
    require(
        '@_cdecl("E7MediaPipeAppDetectFullFaceBgra")' in swift_runtime,
        "Swift runtime must expose the full-face BGRA app symbol.",
    )
    require(
        "detectFullFaceFrame" in swift_full_face_runtime
        and "MakeupARMediaPipeFrameSource.Frame" in swift_full_face_runtime
        and '@_cdecl("E7MediaPipeAppDetectFullFaceFromNativeFrame")'
        in swift_runtime,
        "Swift runtime must expose a native CVPixelBuffer frame entry point shape.",
    )
    require(
        "Data(bytes:" not in swift_full_face_runtime
        and "UIImage(data:" not in swift_full_face_runtime
        and "pngBytes" not in swift_full_face_runtime
        and "DetectBrowLandmarksPng" not in swift_full_face_runtime,
        "Full-face product runtime section must not decode PNG bytes or call the legacy brow PNG diagnostic path.",
    )
    require(
        "detectBrowLandmarksPng" in swift_brow_runtime
        and "diagnostic-only legacy path" in swift_brow_runtime,
        "Legacy PNG brow detection must remain explicitly diagnostic-only.",
    )
    require(
        '"mediapipe_face_landmarker_full_face_v1"' in swift_runtime,
        "Swift runtime must label the full-face packet with a stable source.",
    )
    require(
        '"rawFrameStored":false' in swift_runtime
        and '"offDeviceUpload":false' in swift_runtime,
        "Swift full-face packet must explicitly report no raw frame storage/upload.",
    )
    require(
        "detectWithOrientationFallback" in swift_runtime
        and "orientationCandidates" in swift_runtime
        and "selectedOrientationDegrees" in swift_runtime
        and "orientationFallbackTried" in swift_runtime,
        "Swift full-face runtime must try/carry orientation fallback diagnostics.",
    )
    require(
        "shouldAttemptImageReacquire" in swift_runtime
        and "image_reacquire" in swift_runtime
        and "imageReacquireAttempted" in swift_runtime,
        "Swift full-face runtime must carry image reacquire diagnostics for no-face triage.",
    )
    require(
        "diagnosticCounterJsonFields" in swift_runtime
        and "fullFaceFrameCount" in swift_runtime
        and "imageReacquireTriggerCount" in swift_runtime
        and "imageReacquireTotalAttemptCount" in swift_runtime
        and "imageReacquireNoFaceCount" in swift_runtime,
        "Swift full-face runtime must carry cumulative no-face/reacquire diagnostics.",
    )
    require(
        "tryDetectUiImageReacquire" in swift_runtime
        and "CIImage(cvPixelBuffer:" in swift_runtime
        and "uiimage_reacquire" in swift_runtime
        and "uiImageReacquireTotalAttemptCount" in swift_runtime,
        "Swift full-face runtime must carry a throttled UIImage reacquire diagnostic path.",
    )
    require(
        "final class MakeupARMediaPipeFrameSource" in swift_frame_source
        and "CVPixelBuffer" in swift_frame_source
        and "CGImagePropertyOrientation" in swift_frame_source
        and "timestampMs" in swift_frame_source,
        "Swift runtime must define a native frame source abstraction around CVPixelBuffer frames.",
    )
    require(
        "MakeupARMediaPipeFrameSource.swift in Sources" in xcode_project
        and "MakeupARMediaPipeFrameSource.swift" in xcode_project,
        "Xcode project must compile the MediaPipe frame source abstraction.",
    )

    forbidden_product_tokens = ("ReadPixels", "EncodeToPNG", "Png", "PNG", "Texture2D")
    for token in forbidden_product_tokens:
        require(
            token not in unity_runtime,
            f"Product MediaPipe runtime must not use {token}.",
        )

    require(
        "TryAcquireLatestCpuImage" in unity_runtime,
        "Unity product runtime must consume ARCameraManager CPU camera frames.",
    )
    require(
        "CaptureIntervalSeconds = 1.0f / 15.0f" in unity_runtime
        and "MaxOutputWidth = 720" in unity_runtime
        and "nextCaptureTimestamp = now + CaptureIntervalSeconds" in unity_runtime,
        "Unity product runtime must throttle direct camera-frame MediaPipe capture for realtime performance.",
    )
    require(
        "XRCpuImage.ConversionParams" in unity_runtime
        and "outputFormat = TextureFormat.BGRA32" in unity_runtime
        and "image.Convert(" in unity_runtime,
        "Unity product runtime must convert ARCameraManager CPU images to BGRA for MediaPipe without ReadPixels/PNG.",
    )
    require(
        "private GCHandle conversionBufferHandle" in unity_runtime
        and "private IntPtr conversionBufferPointer = IntPtr.Zero" in unity_runtime
        and "ReleaseConversionBuffer()" in unity_runtime
        and "conversionBufferHandle.Free()" in unity_runtime,
        "Unity product runtime must reuse a persistent pinned BGRA conversion buffer and release it when inactive.",
    )
    require(
        "private static extern IntPtr E7MediaPipeDetectFullFaceBgra(\n        IntPtr bgraBytes," in unity_runtime
        and "image.Convert(\n            conversionParams,\n            conversionBufferPointer,\n            byteCount)" in unity_runtime
        and "DetectFullFaceJson(\n                conversionBufferPointer," in unity_runtime,
        "Unity product runtime must pass the pinned BGRA pointer through Convert and the native bridge instead of remarshal/pinning per capture.",
    )
    require(
        "transformationCandidates =\n        new XRCpuImage.Transformation[5]" in unity_runtime
        and "attemptedTransformations =\n        new XRCpuImage.Transformation[5]" in unity_runtime
        and "FillTransformationCandidates(" in unity_runtime
        and "AddUniqueTransformation(" in unity_runtime
        and "new[] { preferred }" not in unity_runtime
        and "new XRCpuImage.Transformation[candidates.Length]" not in unity_runtime
        and "params XRCpuImage.Transformation" not in unity_runtime,
        "Unity product runtime must reuse transformation fallback buffers instead of allocating arrays per capture.",
    )
    require(
        "E7MediaPipeDetectFullFaceBgra" in unity_runtime,
        "Unity product runtime must call the full-face BGRA native bridge.",
    )
    require(
        "e7_mediapipe_full_face_landmarks" in unity_runtime,
        "Unity product runtime must emit the full-face landmark event.",
    )
    require(
        "rawFrameStored" in unity_runtime
        and "offDeviceUpload" in unity_runtime
        and "false" in unity_runtime,
        "Unity product runtime must explicitly report no raw frame storage/upload.",
    )
    require(
        "e7_mediapipe_full_face_heartbeat.json" in unity_runtime
        and "summaryOnly" in unity_runtime
        and "landmarksStored" in unity_runtime
        and "bboxStored" in unity_runtime,
        "Unity runtime must write only summary heartbeat diagnostics, not landmarks or bbox.",
    )
    require(
        "selectedOrientationDegrees" in unity_runtime
        and "orientationFallbackTried" in unity_runtime
        and "orientationAttemptCount" in unity_runtime,
        "Unity heartbeat must preserve orientation fallback summary diagnostics.",
    )
    require(
        "detectionMode" in unity_runtime
        and "imageReacquireAttempted" in unity_runtime
        and "imageReacquireAttemptCount" in unity_runtime,
        "Unity heartbeat must preserve MediaPipe detection mode/reacquire diagnostics.",
    )
    require(
        "fullFaceFrameCount" in unity_runtime
        and "videoNoFaceCount" in unity_runtime
        and "imageReacquireTriggerCount" in unity_runtime
        and "imageReacquireTotalAttemptCount" in unity_runtime
        and "imageReacquireNoFaceCount" in unity_runtime,
        "Unity heartbeat must preserve cumulative no-face/reacquire diagnostics.",
    )
    require(
        "BuildStatusJsonFragment" in unity_runtime
        and "mediapipePacketAgeMs" in unity_runtime
        and "mediapipeInferenceLatencyMs" in unity_runtime
        and "mediapipeDroppedPacketCount" in unity_runtime
        and "mediapipeStalePacketCount" in unity_runtime
        and "mediapipeCaptureSkippedBusyCount" in unity_runtime
        and "mediapipeCaptureSkippedThrottleCount" in unity_runtime
        and "mediapipeCaptureFrameUnavailableCount" in unity_runtime
        and "captureSkippedBusyCount++" in unity_runtime
        and "captureSkippedThrottleCount++" in unity_runtime
        and "captureFrameUnavailableCount++" in unity_runtime,
        "Unity full-face runtime must expose packet latency/drop and capture cadence diagnostics for performance triage.",
    )
    require(
        "uiImageReacquireTriggerCount" in unity_runtime
        and "uiImageReacquireTotalAttemptCount" in unity_runtime
        and "uiImageReacquireSuccessCount" in unity_runtime,
        "Unity heartbeat must preserve UIImage reacquire diagnostics.",
    )
    require(
        "ComputeFrameStats" in unity_runtime
        and "frameMeanLuma" in unity_runtime
        and "frameStatsAvailable" in unity_runtime
        and "rawFrameStored" in unity_runtime,
        "Unity heartbeat must include privacy-safe aggregate frame stats without storing frames.",
    )
    require(
        "frameMeanBlue" in unity_runtime
        and "frameMeanGreen" in unity_runtime
        and "frameMeanRed" in unity_runtime
        and "sourceImageFormat" in unity_runtime
        and "cameraCurrentFacing" in unity_runtime,
        "Unity heartbeat must include privacy-safe channel and camera source diagnostics.",
    )
    require(
        "ARFaceManager" in unity_runtime
        and "arFaceCount" in unity_runtime
        and "arTrackedFaceCount" in unity_runtime,
        "Unity heartbeat must include ARKit face-trackable counts for no-face triage.",
    )
    require(
        "DetectWithTransformationFallback" in unity_runtime
        and "BuildTransformationCandidates" in unity_runtime
        and "frameTransformation" in unity_runtime
        and "transformationFallbackTried" in unity_runtime,
        "Unity runtime must auto-probe and report CPU-image frame transformation fallback.",
    )
    require(
        "lastTransformationSweepStatus" in unity_runtime
        and "lastTransformationSweepAttemptNames" in unity_runtime,
        "Unity heartbeat must preserve the latest full transformation sweep result.",
    )
    require(
        "MediaPipeFaceLandmarkPacket.TryParse" in unity_runtime
        or "faceFrameSmoother.TryAcceptJson" in unity_runtime,
        "Unity runtime must parse/smooth full-face packets before rendering diagnostics.",
    )
    require(
        "class MediaPipeFaceLandmarkPacket" in packet_dto
        and "ExpectedSource" in packet_dto
        and "rawFrameStored" in packet_dto
        and "offDeviceUpload" in packet_dto
        and "MinimumLandmarkCount = 468" in packet_dto
        and "non_monotonic_timestamp" in packet_dto,
        "Unity packet DTO must enforce source, privacy flags, landmark count, and monotonic timestamps.",
    )
    require(
        "class MediaPipeFaceFrameSmoother" in frame_smoother
        and "MaxStaleAgeMs" in frame_smoother
        and "ConfidenceGate" in frame_smoother
        and "DefaultAlpha = 0.65f" in frame_smoother
        and "SmoothLandmarks" in frame_smoother,
        "Unity frame smoother must implement stale, confidence, and per-landmark smoothing gates.",
    )
    require(
        "RecordFrameClock" in unity_runtime
        and "ResolveCurrentRuntimeTimestampMs" in unity_runtime
        and "lastFrameTimestampMs" in unity_runtime
        and "lastFrameRealtimeSeconds" in unity_runtime
        and "timestampMs > 0L ? timestampMs : ResolveCurrentRuntimeTimestampMs()" in unity_runtime,
        "Unity full-face runtime must age stale packets using the same runtime clock as MediaPipe frame timestamps.",
    )
    require(
        "TrySolveLipRegion" in region_solver
        and "TrySolveLipRegionNonAlloc" in region_solver
        and "LipOuterPointCount" in region_solver
        and "LipInnerCutoutPointCount" in region_solver
        and "LipOuterContour" in region_solver
        and "LipInnerCutout" in region_solver
        and "MediaPipeLipRegion" in region_solver,
        "Unity region solver must expose MediaPipe lip contour geometry.",
    )
    require(
        "TrySolveBrowRegions" in region_solver
        and "TrySolveBrowRegionsNonAlloc" in region_solver
        and "BrowPointCount" in region_solver
        and "LeftBrowContour" in region_solver
        and "RightBrowContour" in region_solver
        and "MediaPipeBrowRegions" in region_solver,
        "Unity region solver must expose independent left/right MediaPipe brow geometry.",
    )
    require(
        "TrySolveCheekRegions" in region_solver
        and "TrySolveCheekRegionsNonAlloc" in region_solver
        and "CheekPointCount" in region_solver
        and "LeftCheekPolygon" in region_solver
        and "RightCheekPolygon" in region_solver
        and "MediaPipeCheekRegions" in region_solver,
        "Unity region solver must expose independent left/right MediaPipe cheek geometry.",
    )
    require(
        "statusLipOuterPoints" in unity_runtime
        and "statusLipInnerCutoutPoints" in unity_runtime
        and "statusLeftBrowPoints" in unity_runtime
        and "statusRightBrowPoints" in unity_runtime
        and "statusLeftCheekPoints" in unity_runtime
        and "statusRightCheekPoints" in unity_runtime
        and "TrySolveLipRegionNonAlloc(" in unity_runtime
        and "TrySolveBrowRegionsNonAlloc(" in unity_runtime
        and "TrySolveCheekRegionsNonAlloc(" in unity_runtime,
        "Unity full-face runtime must use preallocated MediaPipe region status buffers.",
    )
    require(
        "ResolveRegionSolveStatus" in unity_runtime
        and "lipRegionReady" in unity_runtime
        and "browRegionReady" in unity_runtime
        and "cheekRegionReady" in unity_runtime,
        "Unity full-face runtime must report MediaPipe region solve readiness.",
    )
    require(
        "TryGetLatestSmoothedPacket" in unity_runtime
        and "TryGetLatestLipRegion" in unity_runtime
        and "TryGetLatestBrowRegions" in unity_runtime
        and "TryGetLatestCheekRegions" in unity_runtime,
        "Unity full-face runtime must expose smoothed packet and region accessors for renderers.",
    )
    require(
        "class MediaPipeRegionOverlayRenderer" in region_overlay_renderer
        and "TryGetLatestSmoothedPacket" in region_overlay_renderer
        and "MediaPipeLipRegionRenderer.TryBuildGeometry" in region_overlay_renderer
        and "MediaPipeCheekRegionRenderer.TryBuildGeometry" in region_overlay_renderer
        and "MediaPipeBrowRegionRenderer.TryBuildGeometry" in region_overlay_renderer
        and "MediaPipeCanonicalRegionMeshBuilder.TryBuildRegionMesh" in region_overlay_renderer
        and "ApplyCanonicalGateTuning" in region_overlay_renderer
        and "SortPolygonByAngle" in region_overlay_renderer
        and "SetMaterialRenderState" in region_overlay_renderer
        and "MediaPipeCanonicalFaceMesh.TriangleCount" in region_overlay_renderer
        and "mediapipe_canonical_triangle_gate" in region_overlay_renderer,
        "Unity must render lip/cheek/brow by gating the smoothed MediaPipe canonical full-face mesh, with stable region polygons and transparent two-sided material state.",
    )
    require(
        "class MediaPipeCanonicalRegionMeshBuilder" in canonical_region_mesh_builder
        and "TryBuildRegionMesh" in canonical_region_mesh_builder
        and "MediaPipeCanonicalFaceMesh.TriangleIndices" in canonical_region_mesh_builder
        and "MediaPipeCanonicalFaceMesh.Uvs" in canonical_region_mesh_builder
        and "ContainsPoint" in canonical_region_mesh_builder
        and "ProjectNormalizedImagePointToCameraLocal" in canonical_region_mesh_builder
        and "mediapipe_canonical_full_face_triangle_gate" in canonical_region_mesh_builder
        and "mediapipe_canonical_face_model_v1_region_triangles_from_smoothed_landmarks"
        in canonical_region_mesh_builder,
        "Unity must include a canonical full-face triangle gate builder for MediaPipe lip/cheek/brow region meshes.",
    )
    require(
        "class MediaPipeLipRegionRenderer" in lip_region_renderer
        and "TryBuildGeometry" in lip_region_renderer
        and "MediaPipeRegionSolver.TrySolveLipRegionNonAlloc" in lip_region_renderer
        and "new Vector2[MediaPipeRegionSolver.LipOuterPointCount]" in lip_region_renderer
        and "MediaPipeRegionRenderGeometry" in lip_region_renderer,
        "Unity must expose a named MediaPipe lip region renderer artifact backed by lip landmarks.",
    )
    require(
        "class MediaPipeBrowRegionRenderer" in brow_region_renderer
        and "TryBuildGeometry" in brow_region_renderer
        and "MediaPipeRegionSolver.TrySolveBrowRegionsNonAlloc" in brow_region_renderer
        and "new Vector2[MediaPipeRegionSolver.BrowPointCount]" in brow_region_renderer
        and "MediaPipeRegionRenderGeometry" in brow_region_renderer,
        "Unity must expose a named MediaPipe brow region renderer artifact backed by brow landmarks.",
    )
    require(
        "class MediaPipeCheekRegionRenderer" in cheek_region_renderer
        and "TryBuildGeometry" in cheek_region_renderer
        and "MediaPipeRegionSolver.TrySolveCheekRegionsNonAlloc" in cheek_region_renderer
        and "new Vector2[MediaPipeRegionSolver.CheekPointCount]" in cheek_region_renderer
        and "MediaPipeRegionRenderGeometry" in cheek_region_renderer,
        "Unity must expose a named MediaPipe cheek region renderer artifact backed by cheek landmarks.",
    )
    require(
        "class MediaPipeFullFaceMeshRenderer" in full_face_mesh_renderer
        and "TryUpdateFromLatestPacket" in full_face_mesh_renderer
        and "TryRefreshStatusFromLatestPacket" in full_face_mesh_renderer
        and "TryGetLatestSmoothedPacket" in full_face_mesh_renderer
        and "MediaPipeCanonicalFaceMesh" in full_face_mesh_renderer
        and "SetTriangles" in full_face_mesh_renderer
        and "BuildCanonicalTopologyMesh" in full_face_mesh_renderer,
        "Unity must include a MediaPipe full-face topology mesh renderer with a lightweight status path over smoothed full-face packets.",
    )
    require(
        "class MediaPipeCanonicalFaceMesh" in canonical_face_mesh
        and 'TopologyId = "mediapipe_canonical_face_model_v1"' in canonical_face_mesh
        and 'SourceLicense = "Apache-2.0"' in canonical_face_mesh
        and "canonical_face_model.obj" in canonical_face_mesh
        and "VertexCount = 468" in canonical_face_mesh
        and "UvCount = 468" in canonical_face_mesh
        and "TriangleCount = 898" in canonical_face_mesh
        and "TriangleIndices" in canonical_face_mesh
        and "CanBuildFromLandmarkCount" in canonical_face_mesh,
        "Unity must carry the MediaPipe canonical face topology/UV table with source/license attribution.",
    )
    require(
        canonical_face_mesh.count("new Vector2(") == 468,
        "MediaPipe canonical face mesh must contain exactly 468 UV entries.",
    )
    require(
        count_csharp_int_array_entries(canonical_face_mesh, "TriangleIndices") == 898 * 3,
        "MediaPipe canonical face mesh must contain exactly 898 triangle faces.",
    )
    require(
        "class MediaPipeViewportProjection" in viewport_projection
        and "MapNormalizedImagePointToViewport" in viewport_projection
        and "ResolveOrientedImageSize" in viewport_projection
        and "selectedOrientationDegrees" in viewport_projection
        and "aspect_fill" in viewport_projection
        and "MediaPipeViewportProjection" in region_overlay_renderer
        and "MediaPipeViewportProjection" in full_face_mesh_renderer,
        "MediaPipe region overlay must map oriented camera-frame landmarks through aspect-fill viewport projection.",
    )
    require(
        "MaxStaleHoldAgeMs" in region_overlay_renderer
        and "mediapipe_region_stale_hold" in region_overlay_renderer
        and "mediapipe_stale_expired_waiting_for_face" in region_overlay_renderer
        and "stale_expired" in region_overlay_renderer,
        "MediaPipe region overlay must hold/fade short stale packets before hiding expired makeup.",
    )
    for token in forbidden_product_tokens:
        for name, source in (
            ("region overlay renderer", region_overlay_renderer),
            ("lip region renderer", lip_region_renderer),
            ("brow region renderer", brow_region_renderer),
            ("cheek region renderer", cheek_region_renderer),
            ("full-face mesh renderer", full_face_mesh_renderer),
            ("canonical face mesh", canonical_face_mesh),
            ("canonical region mesh builder", canonical_region_mesh_builder),
            ("viewport projection helper", viewport_projection),
        ):
            require(
                token not in source,
                f"MediaPipe product {name} must not use {token}.",
            )
    forbidden_coordinate_owner_tokens = (
        "ARFace",
        "ARKit",
        "ARFoundation",
        "XRFace",
        "faceManager",
        "regionMaskOverlay",
    )
    for token in forbidden_coordinate_owner_tokens:
        for name, source in (
            ("region overlay renderer", region_overlay_renderer),
            ("lip region renderer", lip_region_renderer),
            ("brow region renderer", brow_region_renderer),
            ("cheek region renderer", cheek_region_renderer),
            ("full-face mesh renderer", full_face_mesh_renderer),
            ("canonical region mesh builder", canonical_region_mesh_builder),
            ("viewport projection helper", viewport_projection),
        ):
            require(
                token not in source,
                f"MediaPipe product {name} must not depend on ARKit/ARFace coordinate ownership token {token}.",
            )
    require(
        "MediaPipeRegionOverlayMode" in renderer_routes
        and "mediapipe-region-overlay" in renderer_routes
        and "MediaPipeRegionOverlayRenderer" in renderer_routes
        and "lip-mediapipe-region-overlay-renderer" in renderer_routes
        and "cheek-mediapipe-region-overlay-renderer" in renderer_routes
        and "brow-mediapipe-region-overlay-renderer" in renderer_routes,
        "Renderer routes must make MediaPipe region overlay the product route for lip/cheek/brow.",
    )
    require(
        "BuildMediaPipeFullFaceStatusSummary" in rn_bridge
        and "mediapipe=full-face" in rn_bridge
        and "rawFrameStored=false" in rn_bridge
        and "offDeviceUpload=false" in rn_bridge,
        "RNBridge status must expose MediaPipe-first packet/smoothing privacy diagnostics.",
    )
    require(
        "MediaPipeFullFaceMeshRenderer" in rn_bridge
        and "EnsureMediaPipeFullFaceMeshRenderer" in rn_bridge
        and "TryRefreshStatusFromLatestPacket" in rn_bridge
        and "fullFaceMesh=" in rn_bridge
        and "fullFaceVertices=" in rn_bridge,
        "RNBridge must wire and report the MediaPipe full-face mesh scaffold through the lightweight status path.",
    )
    require(
        "coordinates=mediapipe" in rn_bridge
        and "assist=arkit-session,arkit-camera,optional-depth" in rn_bridge
        and "fullFaceTriangles=" in rn_bridge,
        "RNBridge status must expose MediaPipe coordinate ownership, ARKit assist role, and full-face triangle counts.",
    )
    require(
        "BuildMediaPipeFullFaceStatusJsonFragment" in rn_bridge
        and "mediapipePacketAgeMs" in rn_bridge
        and "mediapipeInferenceLatencyMs" in rn_bridge
        and "mediapipeDroppedPacketCount" in rn_bridge
        and "mediapipeCaptureSkippedThrottleCount" in rn_bridge
        and "activeRegionCount" in rn_bridge,
        "RNBridge metric samples must carry MediaPipe packet/capture performance diagnostics and active region count.",
    )
    require(
        'ProductCoordinateSystem = "mediapipe_canonical_face_space"' in rn_bridge
        and 'ProductPlacementOwner = "mediapipe_full_face_landmarks"' in rn_bridge
        and 'ArKitAssistRole = "arkit_session_camera_optional_depth"' in rn_bridge
        and "productCoordinateSystem=" in rn_bridge
        and "placementOwner=" in rn_bridge
        and "arkitAssistRole=" in rn_bridge
        and "productCoordinateSystem" in rn_bridge
        and "placementOwner" in rn_bridge
        and "arkitAssistRole" in rn_bridge,
        "RNBridge diagnostics must identify MediaPipe as product coordinate owner and ARKit as assist.",
    )
    require(
        "mediapipe_region_overlay_product" in rn_bridge
        and "legacy_arface_uv_compat" in rn_bridge
        and "legacy_smooth_region_mask" in rn_bridge,
        "Region snapshots must distinguish MediaPipe product routes from legacy ARFace UV compatibility routes.",
    )
    require(
        "if (layer.RendererMode == MakeupRegionRendererRoutes.MediaPipeRegionOverlayMode)"
        in rn_bridge
        and "return mediaPipeRegionOverlayRenderer.ApplyRegionRecipe" in rn_bridge
        and "return regionMaskOverlay.ApplyRegionRecipe" in rn_bridge
        and rn_bridge.find("return mediaPipeRegionOverlayRenderer.ApplyRegionRecipe")
        < rn_bridge.find("return regionMaskOverlay.ApplyRegionRecipe"),
        "RNBridge must dispatch MediaPipe product layers to MediaPipeRegionOverlayRenderer before the legacy ARFace UV overlay fallback.",
    )
    require(
        "mediapipe_waiting_for_face" in region_overlay_renderer
        and "HideRegionViews(region)" in region_overlay_renderer
        and "mediaPipeRuntime.TryGetLatestSmoothedPacket" in region_overlay_renderer
        and "FaceCount = hasPacket ? 1 : 0" in region_overlay_renderer,
        "MediaPipe product overlay must hide makeup while waiting for a MediaPipe face packet even if ARKit diagnostics still exist.",
    )
    require(
        "normalizedRendererMode != RendererMode" in region_overlay_renderer
        and "non-MediaPipe renderer mode" in region_overlay_renderer,
        "MediaPipe product overlay must reject legacy renderer modes instead of silently mixing coordinate systems.",
    )
    require(
        "mediapipe_stale_expired_waiting_for_face" in region_overlay_renderer
        and "result.FaceCount = 0" in region_overlay_renderer
        and "result.TrackingState = \"StaleExpired\"" in region_overlay_renderer,
        "MediaPipe product overlay must expire long-stale packets into waiting-for-face instead of falling back to ARKit placement.",
    )
    require(
        "productCoordinateSystem" in face_status_reporter
        and "mediapipe_canonical_face_space" in face_status_reporter
        and "placementOwner" in face_status_reporter
        and "mediapipe_full_face_landmarks" in face_status_reporter
        and "arkitAssistRole" in face_status_reporter
        and "arkit_session_camera_optional_depth" in face_status_reporter
        and "productCoordinateSystem=mediapipe_canonical_face_space" in face_status_reporter,
        "Face feature snapshots must carry MediaPipe-first coordinate ownership diagnostics.",
    )
    require(
        "MediaPipeRegionOverlayRenderer" in rn_bridge
        and "EnsureMediaPipeRegionOverlayRenderer" in rn_bridge
        and "ApplyRegionRecipe" in rn_bridge
        and "MakeupRegionRendererRoutes.MediaPipeRegionOverlayMode" in rn_bridge,
        "RNBridge must dispatch MediaPipe renderer-mode layers to the MediaPipe region overlay renderer.",
    )

    require(
        "E7MediaPipeDetectFullFaceBgra" in ios_bridge
        and "E7MediaPipeAppDetectFullFaceBgra" in ios_bridge
        and "dlsym(RTLD_DEFAULT" in ios_bridge,
        "UnityFramework bridge must forward full-face BGRA calls to the app target.",
    )
    require(
        "E7MediaPipeDetectFullFaceFromNativeFrame" in ios_bridge
        and "E7MediaPipeAppDetectFullFaceFromNativeFrame" in ios_bridge
        and "native_frame_handle_not_connected" in ios_bridge,
        "UnityFramework bridge must reserve the native-frame full-face ABI.",
    )
    require(
        "E7MediaPipeReleaseFullFaceCString" in ios_bridge,
        "UnityFramework bridge must expose a full-face release symbol.",
    )
    require(
        "EnsureMediaPipeFullFaceRuntime" in rn_bridge
        and "SetRuntimeRequested(true)" in rn_bridge,
        "RNBridge must create and start the MediaPipe full-face product runtime.",
    )
    require(
        "SendE7MediaPipeFullFaceLandmarkEvent" in rn_bridge,
        "RNBridge must forward MediaPipe full-face events to React Native.",
    )
    require(
        "e7_mediapipe_full_face_landmarks" in rn_app
        and "formatE7MediaPipeFullFaceLandmarkSummary" in rn_app,
        "RN HUD must recognize and summarize full-face MediaPipe diagnostics.",
    )
    require(
        "mediapipe-region-overlay" in rn_app
        and "DEFAULT_RENDERER_MODE: RendererMode = 'mediapipe-region-overlay'" in rn_app,
        "React Native recipe payloads must default product layers to the MediaPipe region overlay renderer.",
    )
    require(
        "formatRendererDisplayLabel" in rn_app
        and "Renderer ${rendererLabel}" in rn_app
        and "MediaPipe lip" in rn_app
        and "Vision diagnostic" in rn_app
        and "Legacy mask" in rn_app
        and "Legacy atlas diagnostic" in rn_app,
        "React Native product UI must present MediaPipe as the product route and label alternate sources as diagnostics.",
    )
    require(
        "mediapipePacketAgeMs" in rn_app
        and "mediapipeInferenceLatencyMs" in rn_app
        and "mediapipeDroppedPacketCount" in rn_app
        and "mediapipeCaptureSkippedThrottleCount" in rn_app
        and "activeRegionCount" in rn_app,
        "React Native HUD must surface MediaPipe packet/capture performance diagnostics and active region count.",
    )

    print("mediapipe_first_runtime_contract_ok")


if __name__ == "__main__":
    main()
