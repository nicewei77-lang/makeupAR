using System;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public sealed class E7MediaPipeFullFaceRuntime : MonoBehaviour
{
    private const float CaptureIntervalSeconds = 1.0f / 15.0f;
    private const double TransformationSweepIntervalSeconds = 2.0;
    private const int MaxOutputWidth = 720;
    private const string RuntimeSource = "mediapipe_face_landmarker_full_face_v1";
    private const string InputFormat = "bgra-cvpixelbuffer";
    private const string HeartbeatFilename = "e7_mediapipe_full_face_heartbeat.json";
    private const XRCpuImage.Transformation DefaultTransformation = XRCpuImage.Transformation.MirrorY;

    private RNBridge rnBridge;
    private ARCameraManager cameraManager;
    private ARFaceManager faceManager;
    private bool runtimeRequested;
    private bool captureInProgress;
    private double nextCaptureTimestamp;
    private double nextTransformationSweepTimestamp;
    private byte[] conversionBuffer = Array.Empty<byte>();
    private GCHandle conversionBufferHandle;
    private IntPtr conversionBufferPointer = IntPtr.Zero;
    private readonly XRCpuImage.Transformation[] transformationCandidates =
        new XRCpuImage.Transformation[5];
    private readonly XRCpuImage.Transformation[] attemptedTransformations =
        new XRCpuImage.Transformation[5];
    private readonly Vector2[] statusLipOuterPoints =
        new Vector2[MediaPipeRegionSolver.LipOuterPointCount];
    private readonly Vector2[] statusLipInnerCutoutPoints =
        new Vector2[MediaPipeRegionSolver.LipInnerCutoutPointCount];
    private readonly Vector2[] statusLeftBrowPoints =
        new Vector2[MediaPipeRegionSolver.BrowPointCount];
    private readonly Vector2[] statusRightBrowPoints =
        new Vector2[MediaPipeRegionSolver.BrowPointCount];
    private readonly Vector2[] statusLeftCheekPoints =
        new Vector2[MediaPipeRegionSolver.CheekPointCount];
    private readonly Vector2[] statusRightCheekPoints =
        new Vector2[MediaPipeRegionSolver.CheekPointCount];
    private XRCpuImage.Transformation? preferredTransformation;
    private string lastTransformationSweepStatus = string.Empty;
    private string lastTransformationSweepSelected = string.Empty;
    private string lastTransformationSweepAttemptNames = string.Empty;
    private int lastTransformationSweepAttemptCount;
    private readonly MediaPipeFaceFrameSmoother faceFrameSmoother =
        new MediaPipeFaceFrameSmoother();
    private MediaPipeFaceFrameSmoothingStatus latestSmoothingStatus =
        new MediaPipeFaceFrameSmoothingStatus(
            false,
            false,
            false,
            true,
            "not_started",
            0,
            0,
            0.0f,
            0,
            0,
            0,
            0);
    private int sequence;
    private int cameraFrameReceivedCount;
    private int captureAttemptCount;
    private int captureEventCount;
    private int captureSkippedBusyCount;
    private int captureSkippedThrottleCount;
    private int captureFrameUnavailableCount;
    private long lastFrameTimestampMs;
    private double lastFrameRealtimeSeconds;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern IntPtr E7MediaPipeDetectFullFaceBgra(
        IntPtr bgraBytes,
        int byteCount,
        int imageWidth,
        int imageHeight,
        long timestampMs,
        int orientationDegrees);

    [DllImport("__Internal")]
    private static extern void E7MediaPipeReleaseFullFaceCString(IntPtr pointer);
#endif

    public void Configure(RNBridge bridge)
    {
        if (rnBridge == null)
        {
            rnBridge = bridge;
        }
    }

    public void SetRuntimeRequested(bool requested)
    {
        if (runtimeRequested == requested)
        {
            return;
        }

        runtimeRequested = requested;
        nextCaptureTimestamp = 0.0;
        if (!runtimeRequested)
        {
            ReleaseConversionBuffer();
        }

        RefreshSceneReferences();
        UpdateCameraSubscription();

        Debug.Log(
            "[E7] mediapipe_full_face_runtime"
            + " requested=" + runtimeRequested.ToString().ToLowerInvariant()
            + " source=" + RuntimeSource
            + " inputFormat=" + InputFormat
            + " rawFrameStored=false"
            + " offDeviceUpload=false");
    }

    public string BuildStatusSummary()
    {
        MediaPipeFaceFrameSmoothingStatus status = faceFrameSmoother.BuildCurrentStatus(
            ResolveLatestStatusTimestampMs());
        int inferenceLatencyMs = ResolveLatestInferenceLatencyMs();
        return "mediapipe=full-face"
            + " source=direct-frame"
            + " landmarks=" + status.LandmarkCount.ToString(CultureInfo.InvariantCulture)
            + " packetAgeMs=" + status.PacketAgeMs.ToString(CultureInfo.InvariantCulture)
            + " inferenceLatencyMs=" + inferenceLatencyMs.ToString(CultureInfo.InvariantCulture)
            + " stale=" + status.Stale.ToString().ToLowerInvariant()
            + " smoothed=" + status.SmoothingEnabled.ToString().ToLowerInvariant()
            + " stable=" + status.HasStablePacket.ToString().ToLowerInvariant()
            + " accepted=" + status.AcceptedPacketCount.ToString(CultureInfo.InvariantCulture)
            + " rejected=" + status.RejectedPacketCount.ToString(CultureInfo.InvariantCulture)
            + " dropped=" + status.DroppedPacketCount.ToString(CultureInfo.InvariantCulture)
            + " stalePackets=" + status.StalePacketCount.ToString(CultureInfo.InvariantCulture)
            + " cameraFrames=" + cameraFrameReceivedCount.ToString(CultureInfo.InvariantCulture)
            + " captureAttempts=" + captureAttemptCount.ToString(CultureInfo.InvariantCulture)
            + " captureEvents=" + captureEventCount.ToString(CultureInfo.InvariantCulture)
            + " captureSkippedBusy=" + captureSkippedBusyCount.ToString(CultureInfo.InvariantCulture)
            + " captureSkippedThrottle=" + captureSkippedThrottleCount.ToString(CultureInfo.InvariantCulture)
            + " captureFrameUnavailable=" + captureFrameUnavailableCount.ToString(CultureInfo.InvariantCulture)
            + " reason=" + SanitizeStatusToken(status.Reason)
            + " rawFrameStored=false"
            + " offDeviceUpload=false";
    }

    public string BuildStatusJsonFragment()
    {
        MediaPipeFaceFrameSmoothingStatus status = faceFrameSmoother.BuildCurrentStatus(
            ResolveLatestStatusTimestampMs());
        int inferenceLatencyMs = ResolveLatestInferenceLatencyMs();

        return "\"mediapipe\":\"full-face\""
            + ",\"mediapipeSource\":\"direct-frame\""
            + ",\"mediapipeLandmarkCount\":" + status.LandmarkCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipePacketAgeMs\":" + status.PacketAgeMs.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeInferenceLatencyMs\":" + inferenceLatencyMs.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeStale\":" + status.Stale.ToString().ToLowerInvariant()
            + ",\"mediapipeSmoothingEnabled\":" + status.SmoothingEnabled.ToString().ToLowerInvariant()
            + ",\"mediapipeStable\":" + status.HasStablePacket.ToString().ToLowerInvariant()
            + ",\"mediapipeAcceptedPacketCount\":" + status.AcceptedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeRejectedPacketCount\":" + status.RejectedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeDroppedPacketCount\":" + status.DroppedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeStalePacketCount\":" + status.StalePacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipePacketRejectReason\":\"" + EscapeJsonString(status.Reason) + "\""
            + ",\"mediapipeCameraFrameCount\":" + cameraFrameReceivedCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeCaptureAttemptCount\":" + captureAttemptCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeCaptureEventCount\":" + captureEventCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeCaptureSkippedBusyCount\":" + captureSkippedBusyCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeCaptureSkippedThrottleCount\":" + captureSkippedThrottleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"mediapipeCaptureFrameUnavailableCount\":" + captureFrameUnavailableCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rawFrameStored\":false"
            + ",\"offDeviceUpload\":false";
    }

    public bool TryGetLatestSmoothedPacket(
        out MediaPipeFaceLandmarkPacket packet,
        out MediaPipeFaceFrameSmoothingStatus status)
    {
        status = faceFrameSmoother.BuildCurrentStatus(ResolveLatestStatusTimestampMs());
        packet = faceFrameSmoother.LatestSmoothedPacket;
        return packet != null && status.HasStablePacket;
    }

    public bool TryGetLatestLipRegion(
        out MediaPipeLipRegion region,
        out MediaPipeFaceFrameSmoothingStatus status)
    {
        region = default;
        return TryGetLatestSmoothedPacket(out MediaPipeFaceLandmarkPacket packet, out status)
            && MediaPipeRegionSolver.TrySolveLipRegion(packet, out region);
    }

    public bool TryGetLatestBrowRegions(
        out MediaPipeBrowRegions regions,
        out MediaPipeFaceFrameSmoothingStatus status)
    {
        regions = default;
        return TryGetLatestSmoothedPacket(out MediaPipeFaceLandmarkPacket packet, out status)
            && MediaPipeRegionSolver.TrySolveBrowRegions(packet, out regions);
    }

    public bool TryGetLatestCheekRegions(
        out MediaPipeCheekRegions regions,
        out MediaPipeFaceFrameSmoothingStatus status)
    {
        regions = default;
        return TryGetLatestSmoothedPacket(out MediaPipeFaceLandmarkPacket packet, out status)
            && MediaPipeRegionSolver.TrySolveCheekRegions(packet, out regions);
    }

    private void Awake()
    {
        RefreshSceneReferences();
        UpdateCameraSubscription();
    }

    private void OnEnable()
    {
        RefreshSceneReferences();
        UpdateCameraSubscription();
    }

    private void OnDisable()
    {
        if (cameraManager != null)
        {
            cameraManager.frameReceived -= OnCameraFrameReceived;
        }

        ReleaseConversionBuffer();
    }

    private void OnDestroy()
    {
        ReleaseConversionBuffer();
    }

    private void OnCameraFrameReceived(ARCameraFrameEventArgs args)
    {
        if (!runtimeRequested)
        {
            return;
        }

        cameraFrameReceivedCount++;
        if (captureInProgress)
        {
            captureSkippedBusyCount++;
            return;
        }

        double now = Time.realtimeSinceStartupAsDouble;
        if (now < nextCaptureTimestamp)
        {
            captureSkippedThrottleCount++;
            return;
        }

        nextCaptureTimestamp = now + CaptureIntervalSeconds;
        captureAttemptCount++;
        CaptureAndDetectLatestCpuImage();
    }

    private void CaptureAndDetectLatestCpuImage()
    {
        RefreshSceneReferences();
        if (cameraManager == null)
        {
            EmitStatusEvent(
                "camera_manager_missing",
                "ARCameraManager_not_found",
                0,
                0,
                0,
                0,
                0);
            return;
        }

        if (!cameraManager.TryAcquireLatestCpuImage(out XRCpuImage image))
        {
            captureFrameUnavailableCount++;
            EmitStatusEvent(
                "camera_frame_unavailable",
                "TryAcquireLatestCpuImage_false",
                0,
                0,
                0,
                0,
                0);
            return;
        }

        captureInProgress = true;
        long timestampMs = ResolveTimestampMs(image.timestamp);
        RecordFrameClock(timestampMs);
        FrameMetadata frameMetadata = BuildFrameMetadata(image);
        try
        {
            int outputWidth = image.width;
            int outputHeight = image.height;
            if (outputWidth > MaxOutputWidth)
            {
                float scale = MaxOutputWidth / (float)outputWidth;
                outputWidth = MaxOutputWidth;
                outputHeight = Mathf.Max(1, Mathf.RoundToInt(image.height * scale));
            }

            FullFaceDetectionResult result = DetectWithTransformationFallback(
                image,
                outputWidth,
                outputHeight,
                timestampMs,
                ResolveOrientationDegrees());
            SendFullFaceEvent(
                result.Json,
                timestampMs,
                outputWidth,
                outputHeight,
                result.ByteCount,
                result.FrameStats,
                frameMetadata);
        }
        catch (Exception exception)
        {
            EmitStatusEvent(
                "exception",
                exception.GetType().Name + ":" + exception.Message,
                timestampMs,
                image.width,
                image.height,
                0,
                0);
        }
        finally
        {
            image.Dispose();
            captureInProgress = false;
        }
    }

    private void EnsureConversionBuffer(int byteCount)
    {
        if (byteCount <= 0)
        {
            ReleaseConversionBuffer();
            return;
        }

        if (conversionBuffer.Length < byteCount)
        {
            ReleaseConversionBuffer();
            conversionBuffer = new byte[byteCount];
        }

        if (!conversionBufferHandle.IsAllocated)
        {
            conversionBufferHandle = GCHandle.Alloc(conversionBuffer, GCHandleType.Pinned);
            conversionBufferPointer = conversionBufferHandle.AddrOfPinnedObject();
        }
    }

    private void ReleaseConversionBuffer()
    {
        if (conversionBufferHandle.IsAllocated)
        {
            conversionBufferHandle.Free();
        }

        conversionBufferPointer = IntPtr.Zero;
        conversionBuffer = Array.Empty<byte>();
    }

    private FullFaceDetectionResult DetectWithTransformationFallback(
        XRCpuImage image,
        int outputWidth,
        int outputHeight,
        long timestampMs,
        int orientationDegrees)
    {
        int candidateCount = BuildTransformationCandidates(Time.realtimeSinceStartupAsDouble);
        int attemptedCount = 0;

        string lastJson = BuildFailureJson(
            "no_transformation_attempts",
            "no_frame_transformation_candidates",
            timestampMs,
            outputWidth,
            outputHeight);
        FrameStats lastFrameStats = default;
        int lastByteCount = 0;
        XRCpuImage.Transformation lastTransformation = DefaultTransformation;

        for (int index = 0; index < candidateCount; index++)
        {
            XRCpuImage.Transformation transformation = transformationCandidates[index];
            int byteCount = ConvertCpuImage(image, outputWidth, outputHeight, transformation);
            FrameStats frameStats = ComputeFrameStats(conversionBuffer, byteCount);
            string json = DetectFullFaceJson(
                conversionBufferPointer,
                byteCount,
                outputWidth,
                outputHeight,
                timestampMs,
                orientationDegrees);

            attemptedTransformations[attemptedCount] = transformation;
            attemptedCount++;
            lastJson = json;
            lastFrameStats = frameStats;
            lastByteCount = byteCount;
            lastTransformation = transformation;

            if (JsonHasDetectedFace(json))
            {
                preferredTransformation = transformation;
                if (attemptedCount > 1)
                {
                    RecordTransformationSweepDiagnostics(
                        json,
                        transformation,
                        attemptedTransformations,
                        attemptedCount);
                }

                return BuildFullFaceDetectionResult(
                    json,
                    frameStats,
                    byteCount,
                    transformation,
                    attemptedTransformations,
                    attemptedCount);
            }
        }

        if (attemptedCount > 1)
        {
            nextTransformationSweepTimestamp = Time.realtimeSinceStartupAsDouble + TransformationSweepIntervalSeconds;
            RecordTransformationSweepDiagnostics(
                lastJson,
                lastTransformation,
                attemptedTransformations,
                attemptedCount);
        }

        return BuildFullFaceDetectionResult(
            lastJson,
            lastFrameStats,
            lastByteCount,
            lastTransformation,
            attemptedTransformations,
            attemptedCount);
    }

    private int ConvertCpuImage(
        XRCpuImage image,
        int outputWidth,
        int outputHeight,
        XRCpuImage.Transformation transformation)
    {
        var conversionParams = new XRCpuImage.ConversionParams
        {
            inputRect = new RectInt(0, 0, image.width, image.height),
            outputDimensions = new Vector2Int(outputWidth, outputHeight),
            outputFormat = TextureFormat.BGRA32,
            transformation = transformation,
        };
        int byteCount = image.GetConvertedDataSize(conversionParams);
        EnsureConversionBuffer(byteCount);

        if (conversionBufferPointer == IntPtr.Zero)
        {
            throw new InvalidOperationException("MediaPipe BGRA conversion buffer is unavailable.");
        }

        image.Convert(
            conversionParams,
            conversionBufferPointer,
            byteCount);

        return byteCount;
    }

    private int BuildTransformationCandidates(double now)
    {
        XRCpuImage.Transformation preferred = preferredTransformation ?? DefaultTransformation;
        if (preferredTransformation.HasValue || now < nextTransformationSweepTimestamp)
        {
            transformationCandidates[0] = preferred;
            return 1;
        }

        return FillTransformationCandidates(
            preferred,
            XRCpuImage.Transformation.None,
            XRCpuImage.Transformation.MirrorX,
            XRCpuImage.Transformation.MirrorY,
            XRCpuImage.Transformation.MirrorX | XRCpuImage.Transformation.MirrorY);
    }

    private int FillTransformationCandidates(
        XRCpuImage.Transformation first,
        XRCpuImage.Transformation second,
        XRCpuImage.Transformation third,
        XRCpuImage.Transformation fourth,
        XRCpuImage.Transformation fifth)
    {
        int uniqueCount = 0;
        AddUniqueTransformation(first, ref uniqueCount);
        AddUniqueTransformation(second, ref uniqueCount);
        AddUniqueTransformation(third, ref uniqueCount);
        AddUniqueTransformation(fourth, ref uniqueCount);
        AddUniqueTransformation(fifth, ref uniqueCount);
        return uniqueCount;
    }

    private void AddUniqueTransformation(
        XRCpuImage.Transformation candidate,
        ref int uniqueCount)
    {
        for (int uniqueIndex = 0; uniqueIndex < uniqueCount; uniqueIndex++)
        {
            if (transformationCandidates[uniqueIndex] == candidate)
            {
                return;
            }
        }

        transformationCandidates[uniqueCount] = candidate;
        uniqueCount++;
    }

    private FullFaceDetectionResult BuildFullFaceDetectionResult(
        string json,
        FrameStats frameStats,
        int byteCount,
        XRCpuImage.Transformation selectedTransformation,
        XRCpuImage.Transformation[] attemptedTransformations,
        int attemptedCount)
    {
        bool fallbackTried = attemptedCount > 1;
        return new FullFaceDetectionResult(
            AppendFrameTransformDiagnostics(
                json,
                selectedTransformation,
                attemptedTransformations,
                attemptedCount,
                fallbackTried,
                lastTransformationSweepStatus,
                lastTransformationSweepSelected,
                lastTransformationSweepAttemptNames,
                lastTransformationSweepAttemptCount),
            frameStats,
            byteCount);
    }

    private void RecordTransformationSweepDiagnostics(
        string json,
        XRCpuImage.Transformation selectedTransformation,
        XRCpuImage.Transformation[] attemptedTransformations,
        int attemptedCount)
    {
        lastTransformationSweepStatus = ExtractJsonString(json, "status", "unknown");
        lastTransformationSweepSelected = TransformationName(selectedTransformation);
        lastTransformationSweepAttemptNames = TransformationNames(attemptedTransformations, attemptedCount);
        lastTransformationSweepAttemptCount = attemptedCount;
    }

    private static bool JsonHasDetectedFace(string json)
    {
        string status = ExtractJsonString(json, "status", string.Empty);
        if (status == "ok")
        {
            return true;
        }

        string faceCountText = ExtractJsonNumber(json, "faceCount", "0");
        return int.TryParse(faceCountText, NumberStyles.Integer, CultureInfo.InvariantCulture, out int faceCount)
            && faceCount > 0;
    }

    private static string AppendFrameTransformDiagnostics(
        string json,
        XRCpuImage.Transformation selectedTransformation,
        XRCpuImage.Transformation[] attemptedTransformations,
        int attemptedCount,
        bool fallbackTried,
        string lastSweepStatus,
        string lastSweepSelected,
        string lastSweepAttemptNames,
        int lastSweepAttemptCount)
    {
        string trimmed = string.IsNullOrWhiteSpace(json)
            ? "{}"
            : json.Trim();
        if (!trimmed.EndsWith("}", StringComparison.Ordinal))
        {
            trimmed = "{}";
        }

        string prefix = trimmed.Substring(0, trimmed.Length - 1);
        bool hasExistingFields = prefix.Length > 1;
        return prefix
            + (hasExistingFields ? "," : string.Empty)
            + "\"frameTransformation\":\"" + EscapeJsonString(TransformationName(selectedTransformation)) + "\""
            + ",\"transformationFallbackTried\":" + fallbackTried.ToString().ToLowerInvariant()
            + ",\"transformationAttemptCount\":" + attemptedCount.ToString(CultureInfo.InvariantCulture)
            + ",\"transformationAttemptNames\":\"" + EscapeJsonString(TransformationNames(attemptedTransformations, attemptedCount)) + "\""
            + ",\"lastTransformationSweepStatus\":\"" + EscapeJsonString(lastSweepStatus) + "\""
            + ",\"lastTransformationSweepSelected\":\"" + EscapeJsonString(lastSweepSelected) + "\""
            + ",\"lastTransformationSweepAttemptCount\":" + lastSweepAttemptCount.ToString(CultureInfo.InvariantCulture)
            + ",\"lastTransformationSweepAttemptNames\":\"" + EscapeJsonString(lastSweepAttemptNames) + "\""
            + "}";
    }

    private string DetectFullFaceJson(
        IntPtr bgraBytes,
        int byteCount,
        int imageWidth,
        int imageHeight,
        long timestampMs,
        int orientationDegrees)
    {
#if UNITY_IOS && !UNITY_EDITOR
        IntPtr resultPointer = E7MediaPipeDetectFullFaceBgra(
            bgraBytes,
            byteCount,
            imageWidth,
            imageHeight,
            timestampMs,
            orientationDegrees);
        if (resultPointer == IntPtr.Zero)
        {
            return BuildFailureJson(
                "native_result_null",
                "mediapipe_full_face_result_pointer_null",
                timestampMs,
                imageWidth,
                imageHeight);
        }

        try
        {
            return Marshal.PtrToStringAnsi(resultPointer) ?? string.Empty;
        }
        finally
        {
            E7MediaPipeReleaseFullFaceCString(resultPointer);
        }
#else
        return BuildFailureJson(
            "unsupported_platform",
            "requires_ios_device_runtime",
            timestampMs,
            imageWidth,
            imageHeight);
#endif
    }

    private void SendFullFaceEvent(
        string nativeJson,
        long timestampMs,
        int imageWidth,
        int imageHeight,
        int byteCount,
        FrameStats frameStats = default,
        FrameMetadata frameMetadata = default)
    {
        sequence++;
        captureEventCount++;
        string json = string.IsNullOrWhiteSpace(nativeJson)
            ? BuildFailureJson("native_result_empty", "mediapipe_full_face_json_empty", timestampMs, imageWidth, imageHeight)
            : nativeJson.Trim();
        MediaPipeFaceLandmarkPacket smoothedPacket;
        bool acceptedPacket = faceFrameSmoother.TryAcceptJson(
            json,
            timestampMs,
            out smoothedPacket,
            out latestSmoothingStatus);
        MediaPipeRegionSolveStatus regionSolveStatus = ResolveRegionSolveStatus(smoothedPacket);
        json = AppendSmoothingDiagnostics(
            json,
            latestSmoothingStatus,
            acceptedPacket,
            regionSolveStatus);

        Debug.Log(
            "[E7] mediapipe_full_face_result"
            + " sequence=" + sequence.ToString(CultureInfo.InvariantCulture)
            + " timestampMs=" + timestampMs.ToString(CultureInfo.InvariantCulture)
            + " imageSize=" + imageWidth.ToString(CultureInfo.InvariantCulture)
            + "x" + imageHeight.ToString(CultureInfo.InvariantCulture)
            + " bytes=" + byteCount.ToString(CultureInfo.InvariantCulture)
            + " source=" + RuntimeSource
            + " inputFormat=" + InputFormat
            + " smoothingAccepted=" + acceptedPacket.ToString().ToLowerInvariant()
            + " smoothedLandmarks=" + latestSmoothingStatus.LandmarkCount.ToString(CultureInfo.InvariantCulture)
            + " lipRegionReady=" + regionSolveStatus.LipReady.ToString().ToLowerInvariant()
            + " browRegionReady=" + regionSolveStatus.BrowReady.ToString().ToLowerInvariant()
            + " cheekRegionReady=" + regionSolveStatus.CheekReady.ToString().ToLowerInvariant()
            + " packetRejectReason=" + SanitizeStatusToken(latestSmoothingStatus.Reason)
            + " rawFrameStored=false"
            + " offDeviceUpload=false");

        WriteHeartbeatFile(
            json,
            timestampMs,
            imageWidth,
            imageHeight,
            byteCount,
            frameStats,
            frameMetadata);

        if (rnBridge != null)
        {
            rnBridge.SendE7MediaPipeFullFaceLandmarkEvent(EnsureUnityEventType(json));
        }
    }

    private void WriteHeartbeatFile(
        string nativeJson,
        long timestampMs,
        int imageWidth,
        int imageHeight,
        int byteCount,
        FrameStats frameStats,
        FrameMetadata frameMetadata)
    {
        try
        {
            string path = Path.Combine(Application.persistentDataPath, HeartbeatFilename);
            string heartbeatJson = BuildHeartbeatJson(
                nativeJson,
                timestampMs,
                imageWidth,
                imageHeight,
                byteCount,
                frameStats,
                frameMetadata);
            File.WriteAllText(path, heartbeatJson);
        }
        catch (Exception exception)
        {
            Debug.LogWarning("[E7] mediapipe_full_face_heartbeat_write_failed " + exception.Message);
        }
    }

    private string BuildHeartbeatJson(
        string nativeJson,
        long timestampMs,
        int imageWidth,
        int imageHeight,
        int byteCount,
        FrameStats frameStats,
        FrameMetadata frameMetadata)
    {
        string status = ExtractJsonString(nativeJson, "status", "unknown");
        string detail = ExtractJsonString(nativeJson, "detail", string.Empty);
        string source = ExtractJsonString(nativeJson, "source", RuntimeSource);
        string inputFormat = ExtractJsonString(nativeJson, "inputFormat", InputFormat);
        string faceCount = ExtractJsonNumber(nativeJson, "faceCount", "0");
        string landmarkCount = ExtractJsonNumber(nativeJson, "landmarkCount", "0");
        string latencyMs = ExtractJsonNumber(nativeJson, "latencyMs", "0");
        string faceConfidence = ExtractJsonNumber(nativeJson, "faceConfidence", "0");
        string requestedOrientationDegrees = ExtractJsonNumber(nativeJson, "requestedOrientationDegrees", "0");
        string selectedOrientationDegrees = ExtractJsonNumber(nativeJson, "selectedOrientationDegrees", "0");
        string orientationAttemptCount = ExtractJsonNumber(nativeJson, "orientationAttemptCount", "0");
        string orientationFallbackTried = ExtractJsonBoolean(nativeJson, "orientationFallbackTried", "false");
        string detectionMode = ExtractJsonString(nativeJson, "detectionMode", "video");
        string imageReacquireAttempted = ExtractJsonBoolean(nativeJson, "imageReacquireAttempted", "false");
        string imageReacquireAttemptCount = ExtractJsonNumber(nativeJson, "imageReacquireAttemptCount", "0");
        string fullFaceFrameCount = ExtractJsonNumber(nativeJson, "fullFaceFrameCount", "0");
        string videoFaceCount = ExtractJsonNumber(nativeJson, "videoFaceCount", "0");
        string videoNoFaceCount = ExtractJsonNumber(nativeJson, "videoNoFaceCount", "0");
        string imageReacquireTriggerCount = ExtractJsonNumber(nativeJson, "imageReacquireTriggerCount", "0");
        string imageReacquireTotalAttemptCount = ExtractJsonNumber(nativeJson, "imageReacquireTotalAttemptCount", "0");
        string imageReacquireSuccessCount = ExtractJsonNumber(nativeJson, "imageReacquireSuccessCount", "0");
        string imageReacquireNoFaceCount = ExtractJsonNumber(nativeJson, "imageReacquireNoFaceCount", "0");
        string uiImageReacquireTriggerCount = ExtractJsonNumber(nativeJson, "uiImageReacquireTriggerCount", "0");
        string uiImageReacquireTotalAttemptCount = ExtractJsonNumber(nativeJson, "uiImageReacquireTotalAttemptCount", "0");
        string uiImageReacquireSuccessCount = ExtractJsonNumber(nativeJson, "uiImageReacquireSuccessCount", "0");
        string uiImageReacquireNoFaceCount = ExtractJsonNumber(nativeJson, "uiImageReacquireNoFaceCount", "0");
        string frameTransformation = ExtractJsonString(nativeJson, "frameTransformation", "unknown");
        string transformationFallbackTried = ExtractJsonBoolean(nativeJson, "transformationFallbackTried", "false");
        string transformationAttemptCount = ExtractJsonNumber(nativeJson, "transformationAttemptCount", "0");
        string transformationAttemptNames = ExtractJsonString(nativeJson, "transformationAttemptNames", string.Empty);
        string lastTransformationSweepStatus = ExtractJsonString(nativeJson, "lastTransformationSweepStatus", string.Empty);
        string lastTransformationSweepSelected = ExtractJsonString(nativeJson, "lastTransformationSweepSelected", string.Empty);
        string lastTransformationSweepAttemptCount = ExtractJsonNumber(nativeJson, "lastTransformationSweepAttemptCount", "0");
        string lastTransformationSweepAttemptNames = ExtractJsonString(nativeJson, "lastTransformationSweepAttemptNames", string.Empty);
        string available = ExtractJsonBoolean(nativeJson, "available", status == "ok" ? "true" : "false");
        string smoothingAccepted = ExtractJsonBoolean(nativeJson, "smoothingAccepted", "false");
        string smoothingStale = ExtractJsonBoolean(nativeJson, "smoothingStale", "false");
        string smoothingEnabled = ExtractJsonBoolean(nativeJson, "smoothingEnabled", "true");
        string smoothingStable = ExtractJsonBoolean(nativeJson, "smoothingStable", "false");
        string smoothingPacketAgeMs = ExtractJsonNumber(nativeJson, "smoothingPacketAgeMs", "0");
        string smoothedLandmarkCount = ExtractJsonNumber(nativeJson, "smoothedLandmarkCount", "0");
        string smoothingConfidence = ExtractJsonNumber(nativeJson, "smoothingConfidence", "0");
        string acceptedPacketCount = ExtractJsonNumber(nativeJson, "acceptedPacketCount", "0");
        string rejectedPacketCount = ExtractJsonNumber(nativeJson, "rejectedPacketCount", "0");
        string droppedPacketCount = ExtractJsonNumber(nativeJson, "droppedPacketCount", "0");
        string stalePacketCount = ExtractJsonNumber(nativeJson, "stalePacketCount", "0");
        string packetRejectReason = ExtractJsonString(nativeJson, "packetRejectReason", string.Empty);
        string lipRegionReady = ExtractJsonBoolean(nativeJson, "lipRegionReady", "false");
        string lipOuterPointCount = ExtractJsonNumber(nativeJson, "lipOuterPointCount", "0");
        string lipInnerPointCount = ExtractJsonNumber(nativeJson, "lipInnerPointCount", "0");
        string lipRegionConfidence = ExtractJsonNumber(nativeJson, "lipRegionConfidence", "0");
        string browRegionReady = ExtractJsonBoolean(nativeJson, "browRegionReady", "false");
        string leftBrowPointCount = ExtractJsonNumber(nativeJson, "leftBrowPointCount", "0");
        string rightBrowPointCount = ExtractJsonNumber(nativeJson, "rightBrowPointCount", "0");
        string browRegionConfidence = ExtractJsonNumber(nativeJson, "browRegionConfidence", "0");
        string cheekRegionReady = ExtractJsonBoolean(nativeJson, "cheekRegionReady", "false");
        string leftCheekPointCount = ExtractJsonNumber(nativeJson, "leftCheekPointCount", "0");
        string rightCheekPointCount = ExtractJsonNumber(nativeJson, "rightCheekPointCount", "0");
        string cheekRegionConfidence = ExtractJsonNumber(nativeJson, "cheekRegionConfidence", "0");

        return "{\"schema\":\"e7_mediapipe_full_face_heartbeat_v1\""
            + ",\"updatedAtUtc\":\"" + EscapeJsonString(DateTimeOffset.UtcNow.ToString("O", CultureInfo.InvariantCulture)) + "\""
            + ",\"sequence\":" + sequence.ToString(CultureInfo.InvariantCulture)
            + ",\"status\":\"" + EscapeJsonString(status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(detail) + "\""
            + ",\"source\":\"" + EscapeJsonString(source) + "\""
            + ",\"inputFormat\":\"" + EscapeJsonString(inputFormat) + "\""
            + ",\"timestampMs\":" + timestampMs.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + imageWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + imageHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"byteCount\":" + byteCount.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":" + faceCount
            + ",\"landmarkCount\":" + landmarkCount
            + ",\"faceConfidence\":" + faceConfidence
            + ",\"latencyMs\":" + latencyMs
            + ",\"requestedOrientationDegrees\":" + requestedOrientationDegrees
            + ",\"selectedOrientationDegrees\":" + selectedOrientationDegrees
            + ",\"orientationFallbackTried\":" + orientationFallbackTried
            + ",\"orientationAttemptCount\":" + orientationAttemptCount
            + ",\"detectionMode\":\"" + EscapeJsonString(detectionMode) + "\""
            + ",\"imageReacquireAttempted\":" + imageReacquireAttempted
            + ",\"imageReacquireAttemptCount\":" + imageReacquireAttemptCount
            + ",\"fullFaceFrameCount\":" + fullFaceFrameCount
            + ",\"videoFaceCount\":" + videoFaceCount
            + ",\"videoNoFaceCount\":" + videoNoFaceCount
            + ",\"imageReacquireTriggerCount\":" + imageReacquireTriggerCount
            + ",\"imageReacquireTotalAttemptCount\":" + imageReacquireTotalAttemptCount
            + ",\"imageReacquireSuccessCount\":" + imageReacquireSuccessCount
            + ",\"imageReacquireNoFaceCount\":" + imageReacquireNoFaceCount
            + ",\"uiImageReacquireTriggerCount\":" + uiImageReacquireTriggerCount
            + ",\"uiImageReacquireTotalAttemptCount\":" + uiImageReacquireTotalAttemptCount
            + ",\"uiImageReacquireSuccessCount\":" + uiImageReacquireSuccessCount
            + ",\"uiImageReacquireNoFaceCount\":" + uiImageReacquireNoFaceCount
            + ",\"frameTransformation\":\"" + EscapeJsonString(frameTransformation) + "\""
            + ",\"transformationFallbackTried\":" + transformationFallbackTried
            + ",\"transformationAttemptCount\":" + transformationAttemptCount
            + ",\"transformationAttemptNames\":\"" + EscapeJsonString(transformationAttemptNames) + "\""
            + ",\"lastTransformationSweepStatus\":\"" + EscapeJsonString(lastTransformationSweepStatus) + "\""
            + ",\"lastTransformationSweepSelected\":\"" + EscapeJsonString(lastTransformationSweepSelected) + "\""
            + ",\"lastTransformationSweepAttemptCount\":" + lastTransformationSweepAttemptCount
            + ",\"lastTransformationSweepAttemptNames\":\"" + EscapeJsonString(lastTransformationSweepAttemptNames) + "\""
            + ",\"frameStatsAvailable\":" + frameStats.Available.ToString().ToLowerInvariant()
            + ",\"frameSampleCount\":" + frameStats.SampleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"frameMeanLuma\":" + FormatFloat(frameStats.MeanLuma)
            + ",\"frameMinLuma\":" + FormatFloat(frameStats.MinLuma)
            + ",\"frameMaxLuma\":" + FormatFloat(frameStats.MaxLuma)
            + ",\"frameMeanBlue\":" + FormatFloat(frameStats.MeanBlue)
            + ",\"frameMeanGreen\":" + FormatFloat(frameStats.MeanGreen)
            + ",\"frameMeanRed\":" + FormatFloat(frameStats.MeanRed)
            + ",\"frameRedBlueDelta\":" + FormatFloat(frameStats.MeanRed - frameStats.MeanBlue)
            + ",\"sourceImageAvailable\":" + frameMetadata.Available.ToString().ToLowerInvariant()
            + ",\"sourceImageWidth\":" + frameMetadata.SourceWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"sourceImageHeight\":" + frameMetadata.SourceHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"sourceImagePlaneCount\":" + frameMetadata.PlaneCount.ToString(CultureInfo.InvariantCulture)
            + ",\"sourceImageFormat\":\"" + EscapeJsonString(frameMetadata.Format) + "\""
            + ",\"screenOrientation\":\"" + EscapeJsonString(frameMetadata.ScreenOrientation) + "\""
            + ",\"cameraCurrentFacing\":\"" + EscapeJsonString(frameMetadata.CameraCurrentFacing) + "\""
            + ",\"cameraRequestedFacing\":\"" + EscapeJsonString(frameMetadata.CameraRequestedFacing) + "\""
            + ",\"arFaceCount\":" + frameMetadata.ArFaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"arTrackedFaceCount\":" + frameMetadata.ArTrackedFaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"xrTimestampSeconds\":" + frameMetadata.TimestampSeconds.ToString("0.000000", CultureInfo.InvariantCulture)
            + ",\"smoothingAccepted\":" + smoothingAccepted
            + ",\"smoothingStale\":" + smoothingStale
            + ",\"smoothingEnabled\":" + smoothingEnabled
            + ",\"smoothingStable\":" + smoothingStable
            + ",\"smoothingPacketAgeMs\":" + smoothingPacketAgeMs
            + ",\"smoothedLandmarkCount\":" + smoothedLandmarkCount
            + ",\"smoothingConfidence\":" + smoothingConfidence
            + ",\"acceptedPacketCount\":" + acceptedPacketCount
            + ",\"rejectedPacketCount\":" + rejectedPacketCount
            + ",\"droppedPacketCount\":" + droppedPacketCount
            + ",\"stalePacketCount\":" + stalePacketCount
            + ",\"packetRejectReason\":\"" + EscapeJsonString(packetRejectReason) + "\""
            + ",\"lipRegionReady\":" + lipRegionReady
            + ",\"lipOuterPointCount\":" + lipOuterPointCount
            + ",\"lipInnerPointCount\":" + lipInnerPointCount
            + ",\"lipRegionConfidence\":" + lipRegionConfidence
            + ",\"browRegionReady\":" + browRegionReady
            + ",\"leftBrowPointCount\":" + leftBrowPointCount
            + ",\"rightBrowPointCount\":" + rightBrowPointCount
            + ",\"browRegionConfidence\":" + browRegionConfidence
            + ",\"cheekRegionReady\":" + cheekRegionReady
            + ",\"leftCheekPointCount\":" + leftCheekPointCount
            + ",\"rightCheekPointCount\":" + rightCheekPointCount
            + ",\"cheekRegionConfidence\":" + cheekRegionConfidence
            + ",\"available\":" + available
            + ",\"summaryOnly\":true"
            + ",\"landmarksStored\":false"
            + ",\"bboxStored\":false"
            + ",\"rawFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
    }

    private void EmitStatusEvent(
        string status,
        string detail,
        long timestampMs,
        int imageWidth,
        int imageHeight,
        int byteCount,
        int latencyMs)
    {
        long eventTimestampMs = timestampMs > 0L ? timestampMs : ResolveCurrentRuntimeTimestampMs();
        string json =
            "{\"type\":\"e7_mediapipe_full_face_landmarks\""
            + ",\"status\":\"" + EscapeJsonString(status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(detail) + "\""
            + ",\"source\":\"" + RuntimeSource + "\""
            + ",\"inputFormat\":\"" + InputFormat + "\""
            + ",\"timestampMs\":" + eventTimestampMs.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + imageWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + imageHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"byteCount\":" + byteCount.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":0"
            + ",\"landmarkCount\":0"
            + ",\"faceConfidence\":0"
            + ",\"latencyMs\":" + latencyMs.ToString(CultureInfo.InvariantCulture)
            + ",\"available\":false"
            + ",\"rawFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
        SendFullFaceEvent(json, eventTimestampMs, imageWidth, imageHeight, byteCount);
    }

    private static FrameStats ComputeFrameStats(byte[] bgraBytes, int byteCount)
    {
        int pixelCount = Mathf.Max(0, Mathf.Min(byteCount, bgraBytes.Length) / 4);
        if (pixelCount <= 0)
        {
            return default;
        }

        const int MaxSamples = 2048;
        int stridePixels = Mathf.Max(1, pixelCount / MaxSamples);
        int sampleCount = 0;
        float minLuma = 1.0f;
        float maxLuma = 0.0f;
        double totalLuma = 0.0;
        double totalBlue = 0.0;
        double totalGreen = 0.0;
        double totalRed = 0.0;

        for (int pixelIndex = 0; pixelIndex < pixelCount; pixelIndex += stridePixels)
        {
            int byteIndex = pixelIndex * 4;
            float blue = bgraBytes[byteIndex] / 255.0f;
            float green = bgraBytes[byteIndex + 1] / 255.0f;
            float red = bgraBytes[byteIndex + 2] / 255.0f;
            float luma = (0.114f * blue) + (0.587f * green) + (0.299f * red);

            minLuma = Mathf.Min(minLuma, luma);
            maxLuma = Mathf.Max(maxLuma, luma);
            totalLuma += luma;
            totalBlue += blue;
            totalGreen += green;
            totalRed += red;
            sampleCount++;
        }

        if (sampleCount <= 0)
        {
            return default;
        }

        return new FrameStats(
            true,
            sampleCount,
            (float)(totalLuma / sampleCount),
            minLuma,
            maxLuma,
            (float)(totalBlue / sampleCount),
            (float)(totalGreen / sampleCount),
            (float)(totalRed / sampleCount));
    }

    private FrameMetadata BuildFrameMetadata(XRCpuImage image)
    {
        string currentFacing = cameraManager != null
            ? cameraManager.currentFacingDirection.ToString()
            : "unknown";
        string requestedFacing = cameraManager != null
            ? cameraManager.requestedFacingDirection.ToString()
            : "unknown";
        int arFaceCount = 0;
        int arTrackedFaceCount = 0;
        if (faceManager != null)
        {
            foreach (ARFace face in faceManager.trackables)
            {
                arFaceCount++;
                if (face != null && face.trackingState == TrackingState.Tracking)
                {
                    arTrackedFaceCount++;
                }
            }
        }

        return new FrameMetadata(
            true,
            image.width,
            image.height,
            image.planeCount,
            image.format.ToString(),
            Screen.orientation.ToString(),
            currentFacing,
            requestedFacing,
            arFaceCount,
            arTrackedFaceCount,
            image.timestamp);
    }

    private static string EnsureUnityEventType(string json)
    {
        if (json.IndexOf("\"type\"", StringComparison.Ordinal) >= 0)
        {
            return json;
        }

        return "{\"type\":\"e7_mediapipe_full_face_landmarks\","
            + json.TrimStart().TrimStart('{');
    }

    private int ResolveLatestInferenceLatencyMs()
    {
        MediaPipeFaceLandmarkPacket packet = faceFrameSmoother.LatestSmoothedPacket;
        return packet != null ? Mathf.Max(0, packet.latencyMs) : 0;
    }

    private static string AppendSmoothingDiagnostics(
        string json,
        MediaPipeFaceFrameSmoothingStatus status,
        bool acceptedPacket,
        MediaPipeRegionSolveStatus regionStatus)
    {
        string trimmed = string.IsNullOrWhiteSpace(json)
            ? "{}"
            : json.Trim();
        if (!trimmed.EndsWith("}", StringComparison.Ordinal))
        {
            trimmed = "{}";
        }

        string prefix = trimmed.Substring(0, trimmed.Length - 1);
        bool hasExistingFields = prefix.Length > 1;
        return prefix
            + (hasExistingFields ? "," : string.Empty)
            + "\"smoothingAccepted\":" + acceptedPacket.ToString().ToLowerInvariant()
            + ",\"smoothingStale\":" + status.Stale.ToString().ToLowerInvariant()
            + ",\"smoothingEnabled\":" + status.SmoothingEnabled.ToString().ToLowerInvariant()
            + ",\"smoothingStable\":" + status.HasStablePacket.ToString().ToLowerInvariant()
            + ",\"smoothingPacketAgeMs\":" + status.PacketAgeMs.ToString(CultureInfo.InvariantCulture)
            + ",\"smoothedLandmarkCount\":" + status.LandmarkCount.ToString(CultureInfo.InvariantCulture)
            + ",\"smoothingConfidence\":" + status.Confidence.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"acceptedPacketCount\":" + status.AcceptedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rejectedPacketCount\":" + status.RejectedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"droppedPacketCount\":" + status.DroppedPacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"stalePacketCount\":" + status.StalePacketCount.ToString(CultureInfo.InvariantCulture)
            + ",\"packetRejectReason\":\"" + EscapeJsonString(status.Reason) + "\""
            + ",\"lipRegionReady\":" + regionStatus.LipReady.ToString().ToLowerInvariant()
            + ",\"lipOuterPointCount\":" + regionStatus.LipOuterPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"lipInnerPointCount\":" + regionStatus.LipInnerPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"lipRegionConfidence\":" + regionStatus.LipConfidence.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"browRegionReady\":" + regionStatus.BrowReady.ToString().ToLowerInvariant()
            + ",\"leftBrowPointCount\":" + regionStatus.LeftBrowPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rightBrowPointCount\":" + regionStatus.RightBrowPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"browRegionConfidence\":" + regionStatus.BrowConfidence.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"cheekRegionReady\":" + regionStatus.CheekReady.ToString().ToLowerInvariant()
            + ",\"leftCheekPointCount\":" + regionStatus.LeftCheekPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rightCheekPointCount\":" + regionStatus.RightCheekPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"cheekRegionConfidence\":" + regionStatus.CheekConfidence.ToString("0.######", CultureInfo.InvariantCulture)
            + "}";
    }

    private MediaPipeRegionSolveStatus ResolveRegionSolveStatus(
        MediaPipeFaceLandmarkPacket packet)
    {
        var status = new MediaPipeRegionSolveStatus();
        if (packet == null)
        {
            return status;
        }

        if (MediaPipeRegionSolver.TrySolveLipRegionNonAlloc(
                packet,
                statusLipOuterPoints,
                statusLipInnerCutoutPoints,
                out MediaPipeLipRegion lipRegion))
        {
            status.LipReady = true;
            status.LipOuterPointCount = lipRegion.OuterPoints != null ? lipRegion.OuterPoints.Length : 0;
            status.LipInnerPointCount = lipRegion.InnerCutoutPoints != null ? lipRegion.InnerCutoutPoints.Length : 0;
            status.LipConfidence = lipRegion.Confidence;
        }

        if (MediaPipeRegionSolver.TrySolveBrowRegionsNonAlloc(
                packet,
                statusLeftBrowPoints,
                statusRightBrowPoints,
                out MediaPipeBrowRegions browRegions))
        {
            status.BrowReady = true;
            status.LeftBrowPointCount = browRegions.Left.Points != null ? browRegions.Left.Points.Length : 0;
            status.RightBrowPointCount = browRegions.Right.Points != null ? browRegions.Right.Points.Length : 0;
            status.BrowConfidence = Mathf.Min(browRegions.Left.Confidence, browRegions.Right.Confidence);
        }

        if (MediaPipeRegionSolver.TrySolveCheekRegionsNonAlloc(
                packet,
                statusLeftCheekPoints,
                statusRightCheekPoints,
                out MediaPipeCheekRegions cheekRegions))
        {
            status.CheekReady = true;
            status.LeftCheekPointCount = cheekRegions.Left.Polygon != null ? cheekRegions.Left.Polygon.Length : 0;
            status.RightCheekPointCount = cheekRegions.Right.Polygon != null ? cheekRegions.Right.Polygon.Length : 0;
            status.CheekConfidence = Mathf.Min(cheekRegions.Left.Confidence, cheekRegions.Right.Confidence);
        }

        return status;
    }

    private string BuildFailureJson(
        string status,
        string detail,
        long timestampMs,
        int imageWidth,
        int imageHeight)
    {
        return "{\"status\":\"" + EscapeJsonString(status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(detail) + "\""
            + ",\"source\":\"" + RuntimeSource + "\""
            + ",\"inputFormat\":\"" + InputFormat + "\""
            + ",\"timestampMs\":" + timestampMs.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + imageWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + imageHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":0"
            + ",\"landmarkCount\":0"
            + ",\"faceConfidence\":0"
            + ",\"latencyMs\":0"
            + ",\"available\":false"
            + ",\"rawFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
    }

    private void RefreshSceneReferences()
    {
        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        if (cameraManager == null)
        {
            cameraManager = FindFirstObjectByType<ARCameraManager>();
        }

        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }
    }

    private void UpdateCameraSubscription()
    {
        if (cameraManager == null)
        {
            return;
        }

        cameraManager.frameReceived -= OnCameraFrameReceived;
        if (runtimeRequested && isActiveAndEnabled)
        {
            cameraManager.frameReceived += OnCameraFrameReceived;
        }
    }

    private static long ResolveTimestampMs(double xrTimestampSeconds)
    {
        if (xrTimestampSeconds > 0.0)
        {
            return (long)Math.Round(xrTimestampSeconds * 1000.0);
        }

        return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
    }

    private static int ResolveOrientationDegrees()
    {
        switch (Screen.orientation)
        {
            case ScreenOrientation.Portrait:
                return 90;
            case ScreenOrientation.PortraitUpsideDown:
                return 270;
            case ScreenOrientation.LandscapeRight:
                return 180;
            default:
                return 0;
        }
    }

    private static string EscapeJsonString(string value)
    {
        return (value ?? string.Empty)
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r");
    }

    private long ResolveLatestStatusTimestampMs()
    {
        return ResolveCurrentRuntimeTimestampMs();
    }

    private void RecordFrameClock(long timestampMs)
    {
        if (timestampMs <= 0L)
        {
            return;
        }

        lastFrameTimestampMs = timestampMs;
        lastFrameRealtimeSeconds = Time.realtimeSinceStartupAsDouble;
    }

    private long ResolveCurrentRuntimeTimestampMs()
    {
        if (lastFrameTimestampMs > 0L)
        {
            double elapsedSeconds = Math.Max(
                0.0,
                Time.realtimeSinceStartupAsDouble - lastFrameRealtimeSeconds);
            return lastFrameTimestampMs + (long)Math.Round(elapsedSeconds * 1000.0);
        }

        MediaPipeFaceLandmarkPacket packet = faceFrameSmoother.LatestAcceptedPacket;
        return packet != null ? packet.timestampMs : 0L;
    }

    private static string SanitizeStatusToken(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "none";
        }

        return value
            .Replace(" ", "_")
            .Replace("\n", "_")
            .Replace("\r", "_");
    }

    private static string FormatFloat(float value)
    {
        return value.ToString("0.000000", CultureInfo.InvariantCulture);
    }

    private static string TransformationName(XRCpuImage.Transformation transformation)
    {
        if (transformation == XRCpuImage.Transformation.None)
        {
            return "None";
        }

        XRCpuImage.Transformation both = XRCpuImage.Transformation.MirrorX | XRCpuImage.Transformation.MirrorY;
        if (transformation == both)
        {
            return "MirrorX|MirrorY";
        }

        if (transformation == XRCpuImage.Transformation.MirrorX)
        {
            return "MirrorX";
        }

        if (transformation == XRCpuImage.Transformation.MirrorY)
        {
            return "MirrorY";
        }

        return transformation.ToString();
    }

    private static string TransformationNames(
        XRCpuImage.Transformation[] transformations,
        int count)
    {
        if (transformations == null || count <= 0)
        {
            return string.Empty;
        }

        var builder = new System.Text.StringBuilder();
        int limit = Mathf.Min(count, transformations.Length);
        for (int index = 0; index < limit; index++)
        {
            if (index > 0)
            {
                builder.Append(",");
            }

            builder.Append(TransformationName(transformations[index]));
        }

        return builder.ToString();
    }

    private static string ExtractJsonString(string json, string key, string fallback)
    {
        if (string.IsNullOrEmpty(json))
        {
            return fallback;
        }

        string needle = "\"" + key + "\":\"";
        int start = json.IndexOf(needle, StringComparison.Ordinal);
        if (start < 0)
        {
            return fallback;
        }

        start += needle.Length;
        var value = new System.Text.StringBuilder();
        bool escaping = false;
        for (int index = start; index < json.Length; index++)
        {
            char character = json[index];
            if (escaping)
            {
                value.Append(character);
                escaping = false;
                continue;
            }

            if (character == '\\')
            {
                escaping = true;
                continue;
            }

            if (character == '"')
            {
                return value.ToString();
            }

            value.Append(character);
        }

        return fallback;
    }

    private static string ExtractJsonNumber(string json, string key, string fallback)
    {
        if (string.IsNullOrEmpty(json))
        {
            return fallback;
        }

        string needle = "\"" + key + "\":";
        int start = json.IndexOf(needle, StringComparison.Ordinal);
        if (start < 0)
        {
            return fallback;
        }

        start += needle.Length;
        while (start < json.Length && char.IsWhiteSpace(json[start]))
        {
            start++;
        }

        int end = start;
        while (end < json.Length)
        {
            char character = json[end];
            if (!(char.IsDigit(character) || character == '-' || character == '+' || character == '.' || character == 'e' || character == 'E'))
            {
                break;
            }

            end++;
        }

        return end > start ? json.Substring(start, end - start) : fallback;
    }

    private static string ExtractJsonBoolean(string json, string key, string fallback)
    {
        if (string.IsNullOrEmpty(json))
        {
            return fallback;
        }

        string needle = "\"" + key + "\":";
        int start = json.IndexOf(needle, StringComparison.Ordinal);
        if (start < 0)
        {
            return fallback;
        }

        start += needle.Length;
        while (start < json.Length && char.IsWhiteSpace(json[start]))
        {
            start++;
        }

        if (json.IndexOf("true", start, StringComparison.Ordinal) == start)
        {
            return "true";
        }

        if (json.IndexOf("false", start, StringComparison.Ordinal) == start)
        {
            return "false";
        }

        return fallback;
    }

    private readonly struct FrameStats
    {
        public FrameStats(
            bool available,
            int sampleCount,
            float meanLuma,
            float minLuma,
            float maxLuma,
            float meanBlue,
            float meanGreen,
            float meanRed)
        {
            Available = available;
            SampleCount = sampleCount;
            MeanLuma = meanLuma;
            MinLuma = minLuma;
            MaxLuma = maxLuma;
            MeanBlue = meanBlue;
            MeanGreen = meanGreen;
            MeanRed = meanRed;
        }

        public bool Available { get; }
        public int SampleCount { get; }
        public float MeanLuma { get; }
        public float MinLuma { get; }
        public float MaxLuma { get; }
        public float MeanBlue { get; }
        public float MeanGreen { get; }
        public float MeanRed { get; }
    }

    private readonly struct FrameMetadata
    {
        public FrameMetadata(
            bool available,
            int sourceWidth,
            int sourceHeight,
            int planeCount,
            string format,
            string screenOrientation,
            string cameraCurrentFacing,
            string cameraRequestedFacing,
            int arFaceCount,
            int arTrackedFaceCount,
            double timestampSeconds)
        {
            Available = available;
            SourceWidth = sourceWidth;
            SourceHeight = sourceHeight;
            PlaneCount = planeCount;
            Format = format ?? string.Empty;
            ScreenOrientation = screenOrientation ?? string.Empty;
            CameraCurrentFacing = cameraCurrentFacing ?? string.Empty;
            CameraRequestedFacing = cameraRequestedFacing ?? string.Empty;
            ArFaceCount = arFaceCount;
            ArTrackedFaceCount = arTrackedFaceCount;
            TimestampSeconds = timestampSeconds;
        }

        public bool Available { get; }
        public int SourceWidth { get; }
        public int SourceHeight { get; }
        public int PlaneCount { get; }
        public string Format { get; }
        public string ScreenOrientation { get; }
        public string CameraCurrentFacing { get; }
        public string CameraRequestedFacing { get; }
        public int ArFaceCount { get; }
        public int ArTrackedFaceCount { get; }
        public double TimestampSeconds { get; }
    }

    private readonly struct FullFaceDetectionResult
    {
        public FullFaceDetectionResult(
            string json,
            FrameStats frameStats,
            int byteCount)
        {
            Json = json;
            FrameStats = frameStats;
            ByteCount = byteCount;
        }

        public string Json { get; }
        public FrameStats FrameStats { get; }
        public int ByteCount { get; }
    }

    private struct MediaPipeRegionSolveStatus
    {
        public bool LipReady;
        public int LipOuterPointCount;
        public int LipInnerPointCount;
        public float LipConfidence;
        public bool BrowReady;
        public int LeftBrowPointCount;
        public int RightBrowPointCount;
        public float BrowConfidence;
        public bool CheekReady;
        public int LeftCheekPointCount;
        public int RightCheekPointCount;
        public float CheekConfidence;
    }
}
