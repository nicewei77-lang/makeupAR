using System;
using System.Collections;
using System.Globalization;
using System.Runtime.InteropServices;
using UnityEngine;

public sealed class E7MediaPipeBrowLandmarkRuntime : MonoBehaviour
{
    // Privacy contract: raw camera frames are memory-only. Detector diagnostics
    // are limited to landmark, bbox, confidence, timing, and status numbers.
    // Event JSON includes "rawCameraFrameStored":false and "offDeviceUpload":false.
    [Serializable]
    private sealed class BrowPointPayload
    {
        public int index;
        public float x;
        public float y;
        public float z;
        public float presence;
    }

    [Serializable]
    private sealed class BrowBboxPayload
    {
        public float left;
        public float top;
        public float right;
        public float bottom;
        public float width;
        public float height;
    }

    [Serializable]
    private sealed class BrowLandmarkPayload
    {
        public string status;
        public string detail;
        public string source;
        public string coordinateMode;
        public int imageWidth;
        public int imageHeight;
        public int faceCount;
        public int landmarkCount;
        public int leftPointCount;
        public int rightPointCount;
        public float confidence;
        public int latencyMs;
        public BrowBboxPayload bbox;
        public BrowPointPayload[] leftEyebrow;
        public BrowPointPayload[] rightEyebrow;
        public bool rawCameraFrameStored;
        public bool offDeviceUpload;
    }

    private const float CaptureIntervalSeconds = 0.20f;
    private const string RuntimeSource = "mediapipe_face_landmarker_runtime_brow_landmarks";
    private const string CoordinateMode = "normalized-image";

    private RNBridge rnBridge;
    private E3RegionMaskOverlay regionMaskOverlay;
    private FaceTrackingStatusReporter statusReporter;
    private bool runtimeRequested;
    private bool captureInProgress;
    private float nextCaptureAt;
    private int sequence;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern IntPtr E7MediaPipeDetectBrowLandmarksPng(
        byte[] pngBytes,
        int byteCount,
        int imageWidth,
        int imageHeight);

    [DllImport("__Internal")]
    private static extern void E7MediaPipeReleaseCString(IntPtr pointer);
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
        if (runtimeRequested)
        {
            nextCaptureAt = 0.0f;
        }

        Debug.Log(
            "[E7] mediapipe_brow_landmark_runtime"
            + " requested=" + runtimeRequested.ToString().ToLowerInvariant()
            + " source=" + RuntimeSource
            + " coordinateMode=" + CoordinateMode
            + " rawCameraFrameStored=false"
            + " offDeviceUpload=false");
    }

    private void Awake()
    {
        RefreshSceneReferences();
    }

    private void Update()
    {
        if (!runtimeRequested || captureInProgress || Time.realtimeSinceStartup < nextCaptureAt)
        {
            return;
        }

        StartCoroutine(CaptureAndDetectRoutine());
    }

    private IEnumerator CaptureAndDetectRoutine()
    {
        captureInProgress = true;
        RefreshSceneReferences();
        bool originalDebugOverlayVisible = statusReporter != null && statusReporter.DebugOverlayVisible;

        if (regionMaskOverlay != null)
        {
            regionMaskOverlay.SetVisionCaptureSuppressed(true);
        }

        if (statusReporter != null)
        {
            statusReporter.SetDebugOverlayVisible(false);
        }

        yield return new WaitForEndOfFrame();

        int width = Screen.width;
        int height = Screen.height;
        Texture2D frameTexture = null;

        try
        {
            if (width <= 0 || height <= 0)
            {
                ApplyBrowLandmarkPayload(BuildFailurePayload(
                    "invalid_screen_size",
                    "screen_width_or_height_zero",
                    width,
                    height));
                yield break;
            }

            frameTexture = new Texture2D(width, height, TextureFormat.RGBA32, false);
            frameTexture.ReadPixels(new Rect(0, 0, width, height), 0, 0, false);
            frameTexture.Apply(false, false);
            byte[] pngBytes = frameTexture.EncodeToPNG();

            string json = DetectBrowLandmarksJson(pngBytes, width, height);
            BrowLandmarkPayload payload = JsonUtility.FromJson<BrowLandmarkPayload>(json);
            ApplyBrowLandmarkPayload(payload ?? BuildFailurePayload(
                "parse_failed",
                "native_mediapipe_json_empty",
                width,
                height));
        }
        catch (Exception exception)
        {
            ApplyBrowLandmarkPayload(BuildFailurePayload(
                "exception",
                exception.GetType().Name + ":" + exception.Message,
                width,
                height));
        }
        finally
        {
            if (frameTexture != null)
            {
                Destroy(frameTexture);
            }

            if (regionMaskOverlay != null)
            {
                regionMaskOverlay.SetVisionCaptureSuppressed(false);
            }

            if (statusReporter != null)
            {
                statusReporter.SetDebugOverlayVisible(originalDebugOverlayVisible);
            }

            nextCaptureAt = Time.realtimeSinceStartup + CaptureIntervalSeconds;
            captureInProgress = false;
        }
    }

    private void RefreshSceneReferences()
    {
        if (rnBridge == null)
        {
            rnBridge = FindFirstObjectByType<RNBridge>();
        }

        if (regionMaskOverlay == null)
        {
            regionMaskOverlay = FindFirstObjectByType<E3RegionMaskOverlay>();
        }

        if (statusReporter == null)
        {
            statusReporter = FindFirstObjectByType<FaceTrackingStatusReporter>();
        }
    }

    private string DetectBrowLandmarksJson(byte[] pngBytes, int width, int height)
    {
#if UNITY_IOS && !UNITY_EDITOR
        IntPtr resultPointer = E7MediaPipeDetectBrowLandmarksPng(
            pngBytes,
            pngBytes != null ? pngBytes.Length : 0,
            width,
            height);
        if (resultPointer == IntPtr.Zero)
        {
            return BuildFailureJson("native_result_null", "mediapipe_result_pointer_null", width, height);
        }

        try
        {
            return Marshal.PtrToStringAnsi(resultPointer) ?? string.Empty;
        }
        finally
        {
            E7MediaPipeReleaseCString(resultPointer);
        }
#else
        return BuildFailureJson("unsupported_platform", "requires_ios_device_runtime", width, height);
#endif
    }

    private void ApplyBrowLandmarkPayload(BrowLandmarkPayload payload)
    {
        sequence++;
        long detectedAtMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string status = NormalizeOptional(payload != null ? payload.status : string.Empty, "unknown");
        string detail = NormalizeOptional(payload != null ? payload.detail : string.Empty, "none");
        string source = NormalizeOptional(payload != null ? payload.source : string.Empty, RuntimeSource);
        string coordinateMode = NormalizeOptional(
            payload != null ? payload.coordinateMode : string.Empty,
            CoordinateMode);
        bool available = status == "ok"
            && payload != null
            && payload.leftPointCount >= 2
            && payload.rightPointCount >= 2;

        Debug.Log(
            "[E7] mediapipe_brow_landmark_result"
            + " status=" + status
            + " source=" + source
            + " coordinateMode=" + coordinateMode
            + " sequence=" + sequence.ToString(CultureInfo.InvariantCulture)
            + " imageSize=" + (payload != null ? payload.imageWidth : 0).ToString(CultureInfo.InvariantCulture)
            + "x" + (payload != null ? payload.imageHeight : 0).ToString(CultureInfo.InvariantCulture)
            + " faceCount=" + (payload != null ? payload.faceCount : 0).ToString(CultureInfo.InvariantCulture)
            + " landmarkCount=" + (payload != null ? payload.landmarkCount : 0).ToString(CultureInfo.InvariantCulture)
            + " leftPoints=" + (payload != null ? payload.leftPointCount : 0).ToString(CultureInfo.InvariantCulture)
            + " rightPoints=" + (payload != null ? payload.rightPointCount : 0).ToString(CultureInfo.InvariantCulture)
            + " confidence=" + (payload != null ? payload.confidence : 0.0f).ToString("0.###", CultureInfo.InvariantCulture)
            + " latencyMs=" + (payload != null ? payload.latencyMs : 0).ToString(CultureInfo.InvariantCulture)
            + " available=" + available.ToString().ToLowerInvariant()
            + " rawCameraFrameStored=false"
            + " offDeviceUpload=false"
            + " detail=" + SanitizeLogValue(detail));

        if (rnBridge != null)
        {
            rnBridge.SendE7MediaPipeBrowLandmarkEvent(BuildBrowLandmarkEventJson(
                payload,
                sequence,
                detectedAtMs,
                available,
                status,
                detail,
                source,
                coordinateMode));
        }
    }

    private static BrowLandmarkPayload BuildFailurePayload(
        string status,
        string detail,
        int width,
        int height)
    {
        return new BrowLandmarkPayload
        {
            status = status,
            detail = detail,
            source = RuntimeSource,
            coordinateMode = CoordinateMode,
            imageWidth = width,
            imageHeight = height,
            faceCount = 0,
            landmarkCount = 0,
            leftPointCount = 0,
            rightPointCount = 0,
            confidence = 0.0f,
            latencyMs = 0,
            bbox = new BrowBboxPayload(),
            leftEyebrow = Array.Empty<BrowPointPayload>(),
            rightEyebrow = Array.Empty<BrowPointPayload>(),
            rawCameraFrameStored = false,
            offDeviceUpload = false
        };
    }

    private static string BuildFailureJson(string status, string detail, int width, int height)
    {
        return "{\"status\":\"" + EscapeJsonString(status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(detail) + "\""
            + ",\"source\":\"" + RuntimeSource + "\""
            + ",\"coordinateMode\":\"" + CoordinateMode + "\""
            + ",\"imageWidth\":" + width.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + height.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":0"
            + ",\"landmarkCount\":0"
            + ",\"leftPointCount\":0"
            + ",\"rightPointCount\":0"
            + ",\"confidence\":0"
            + ",\"latencyMs\":0"
            + ",\"bbox\":{\"left\":0,\"top\":0,\"right\":0,\"bottom\":0,\"width\":0,\"height\":0}"
            + ",\"leftEyebrow\":[]"
            + ",\"rightEyebrow\":[]"
            + ",\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
    }

    private static string BuildBrowLandmarkEventJson(
        BrowLandmarkPayload payload,
        int sequence,
        long detectedAtMs,
        bool available,
        string status,
        string detail,
        string source,
        string coordinateMode)
    {
        BrowBboxPayload bbox = payload != null && payload.bbox != null
            ? payload.bbox
            : new BrowBboxPayload();

        return "{\"type\":\"e7_mediapipe_brow_landmarks\""
            + ",\"status\":\"" + EscapeJsonString(status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(detail) + "\""
            + ",\"source\":\"" + EscapeJsonString(source) + "\""
            + ",\"coordinateMode\":\"" + EscapeJsonString(coordinateMode) + "\""
            + ",\"sequence\":" + sequence.ToString(CultureInfo.InvariantCulture)
            + ",\"detectedAtMs\":" + detectedAtMs.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + (payload != null ? payload.imageWidth : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + (payload != null ? payload.imageHeight : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":" + (payload != null ? payload.faceCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"landmarkCount\":" + (payload != null ? payload.landmarkCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"leftPointCount\":" + (payload != null ? payload.leftPointCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"rightPointCount\":" + (payload != null ? payload.rightPointCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"confidence\":" + (payload != null ? payload.confidence : 0.0f).ToString("0.###", CultureInfo.InvariantCulture)
            + ",\"latencyMs\":" + (payload != null ? payload.latencyMs : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"available\":" + available.ToString().ToLowerInvariant()
            + ",\"bboxLeft\":" + bbox.left.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"bboxTop\":" + bbox.top.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"bboxRight\":" + bbox.right.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"bboxBottom\":" + bbox.bottom.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"bboxWidth\":" + bbox.width.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"bboxHeight\":" + bbox.height.ToString("0.######", CultureInfo.InvariantCulture)
            + ",\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
    }

    private static string NormalizeOptional(string value, string defaultValue)
    {
        return string.IsNullOrWhiteSpace(value) ? defaultValue : value.Trim();
    }

    private static string SanitizeLogValue(string value)
    {
        return NormalizeOptional(value, "none").Replace(" ", "_").Replace("\n", "_").Replace("\r", "_");
    }

    private static string EscapeJsonString(string value)
    {
        return (value ?? string.Empty)
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r");
    }
}
