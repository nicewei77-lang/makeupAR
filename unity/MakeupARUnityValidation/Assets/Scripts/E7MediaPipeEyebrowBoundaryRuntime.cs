using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public sealed class E7MediaPipeEyebrowBoundaryRuntime : MonoBehaviour
{
    public struct BoundarySnapshot
    {
        public bool Available;
        public string Status;
        public string Detail;
        public string Source;
        public string CoordinateMode;
        public int ImageWidth;
        public int ImageHeight;
        public int FaceCount;
        public int LeftOuterPointCount;
        public int RightOuterPointCount;
        public int LeftEyePointCount;
        public int RightEyePointCount;
        public int Sequence;
        public long DetectedAtMs;
        public long AgeMs;
        public Vector2[] LeftOuterPoints;
        public Vector2[] RightOuterPoints;
        public Vector2[] LeftEyePoints;
        public Vector2[] RightEyePoints;
        public Vector2[] LeftControlPoints;
        public Vector2[] RightControlPoints;
        public string ControlPointMode;
        public bool FaceBoundsAvailable;
        public Vector2 FaceBoundsCenter;
        public Vector2 FaceBoundsSize;
        public string StabilizationMode;
        public float FaceMotionScore;
        public float FaceMotionCenterShiftPx;
        public float FaceMotionScaleDelta;
        public string FaceMotionRisk;
        public string HairRefinementStatus;
        public int LeftHairPixelCount;
        public int RightHairPixelCount;
        public float LeftBrowEyeGapPx;
        public float RightBrowEyeGapPx;
    }

    [Serializable]
    private sealed class MediaPipePointPayload
    {
        public float x;
        public float y;
    }

    [Serializable]
    private sealed class MediaPipeEyebrowPayload
    {
        public string status;
        public string detail;
        public string source;
        public string coordinateMode;
        public int imageWidth;
        public int imageHeight;
        public int faceCount;
        public int leftOuterPointCount;
        public int rightOuterPointCount;
        public int leftEyePointCount;
        public int rightEyePointCount;
        public MediaPipePointPayload[] leftOuter;
        public MediaPipePointPayload[] rightOuter;
        public MediaPipePointPayload[] leftEye;
        public MediaPipePointPayload[] rightEye;
    }

    private struct FaceScreenBounds
    {
        public bool Available;
        public Vector2 Center;
        public Vector2 Size;
    }

    private struct BrowRefinementStats
    {
        public string Status;
        public int LeftHairPixelCount;
        public int RightHairPixelCount;
        public float LeftBrowEyeGapPx;
        public float RightBrowEyeGapPx;
    }

    private const float CaptureIntervalSeconds = 0.14f;
    private const long FreshBoundaryMaxAgeMs = 320;
    private const float BoundarySmoothBlend = 0.82f;
    private const float BoundaryLargeMotionBlend = 1.0f;
    private const float FaceMotionMediumThreshold = 0.18f;
    private const float FaceMotionLargeThreshold = 0.32f;
    private const int BrowRefinementSampleStepPx = 2;
    private const float BrowMinimumEyeGapPx = 14.0f;
    private const int BrowEnvelopeColumnCount = 24;
    private const int BrowMakeupShapePointCount = 36;
    private const int BrowEnvelopeMinValidColumns = 5;
    private const int BrowDenseCorePaddingColumns = 0;
    private const string RuntimeSource = "mediapipe_face_landmarker_runtime_eyebrow_boundary";
    private const string CoordinateMode = "mediapipe-image-top-left";

    private bool runtimeRequested;
    private bool captureInProgress;
    private float nextCaptureAt;
    private int sequence;
    private BoundarySnapshot latestSnapshot;
    private RNBridge rnBridge;
    private E3RegionMaskOverlay regionMaskOverlay;
    private FaceTrackingStatusReporter statusReporter;
    private ARFaceManager faceManager;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern IntPtr E7MediaPipeDetectEyebrowBoundaryPng(
        byte[] pngBytes,
        int byteCount,
        int imageWidth,
        int imageHeight);

    [DllImport("__Internal")]
    private static extern void E7VisionReleaseCString(IntPtr pointer);
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
            "[E7] mediapipe_eyebrow_boundary_runtime"
            + " requested=" + runtimeRequested.ToString().ToLowerInvariant()
            + " source=" + RuntimeSource
            + " coordinateMode=" + CoordinateMode);
    }

    public bool TryGetLatestBoundary(
        int targetWidth,
        int targetHeight,
        out BoundarySnapshot snapshot)
    {
        long nowMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        snapshot = latestSnapshot;
        snapshot.AgeMs = snapshot.DetectedAtMs > 0
            ? nowMs - snapshot.DetectedAtMs
            : 0;

        if (!snapshot.Available
            || snapshot.LeftOuterPoints == null
            || snapshot.RightOuterPoints == null
            || snapshot.LeftOuterPoints.Length < 3
            || snapshot.RightOuterPoints.Length < 3
            || snapshot.AgeMs > FreshBoundaryMaxAgeMs)
        {
            return false;
        }

        if (targetWidth <= 0
            || targetHeight <= 0
            || snapshot.ImageWidth <= 0
            || snapshot.ImageHeight <= 0
            || (targetWidth == snapshot.ImageWidth && targetHeight == snapshot.ImageHeight))
        {
            return true;
        }

        float scaleX = targetWidth / (float)snapshot.ImageWidth;
        float scaleY = targetHeight / (float)snapshot.ImageHeight;
        snapshot.LeftOuterPoints = ScalePoints(snapshot.LeftOuterPoints, scaleX, scaleY);
        snapshot.RightOuterPoints = ScalePoints(snapshot.RightOuterPoints, scaleX, scaleY);
        snapshot.LeftEyePoints = ScalePoints(snapshot.LeftEyePoints, scaleX, scaleY);
        snapshot.RightEyePoints = ScalePoints(snapshot.RightEyePoints, scaleX, scaleY);
        if (snapshot.FaceBoundsAvailable)
        {
            snapshot.FaceBoundsCenter = new Vector2(
                snapshot.FaceBoundsCenter.x * scaleX,
                snapshot.FaceBoundsCenter.y * scaleY);
            snapshot.FaceBoundsSize = new Vector2(
                snapshot.FaceBoundsSize.x * scaleX,
                snapshot.FaceBoundsSize.y * scaleY);
        }

        snapshot.ImageWidth = targetWidth;
        snapshot.ImageHeight = targetHeight;
        return true;
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
            regionMaskOverlay.SetRegionCaptureSuppressed("eyebrow", true);
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
                ApplyBoundaryPayload(BuildFailurePayload("invalid_screen_size", "screen_width_or_height_zero", width, height), default);
                yield break;
            }

            FaceScreenBounds faceBounds = CaptureCurrentFaceBounds();
            frameTexture = new Texture2D(width, height, TextureFormat.RGB24, false);
            frameTexture.ReadPixels(new Rect(0, 0, width, height), 0, 0, false);
            frameTexture.Apply(false, false);
            Color32[] framePixels = frameTexture.GetPixels32();
            byte[] pngBytes = EncodeRgbPngTopLeft(frameTexture);

            string json = DetectEyebrowBoundaryJson(pngBytes, width, height);
            MediaPipeEyebrowPayload payload = JsonUtility.FromJson<MediaPipeEyebrowPayload>(json);
            ApplyBoundaryPayload(
                payload ?? BuildFailurePayload("parse_failed", "native_mediapipe_json_empty", width, height),
                faceBounds,
                framePixels,
                width,
                height);
        }
        catch (Exception exception)
        {
            ApplyBoundaryPayload(
                BuildFailurePayload("exception", exception.GetType().Name + ":" + exception.Message, width, height),
                default);
        }
        finally
        {
            if (frameTexture != null)
            {
                Destroy(frameTexture);
            }

            if (regionMaskOverlay != null)
            {
                regionMaskOverlay.SetRegionCaptureSuppressed("eyebrow", false);
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

        if (statusReporter == null)
        {
            statusReporter = FindFirstObjectByType<FaceTrackingStatusReporter>();
        }

        if (regionMaskOverlay == null)
        {
            regionMaskOverlay = FindFirstObjectByType<E3RegionMaskOverlay>();
        }

        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }
    }

    private string DetectEyebrowBoundaryJson(byte[] pngBytes, int width, int height)
    {
#if UNITY_IOS && !UNITY_EDITOR
        IntPtr resultPointer = E7MediaPipeDetectEyebrowBoundaryPng(
            pngBytes,
            pngBytes != null ? pngBytes.Length : 0,
            width,
            height);
        if (resultPointer == IntPtr.Zero)
        {
            return "{\"status\":\"native_result_null\",\"source\":\""
                + RuntimeSource
                + "\",\"coordinateMode\":\""
                + CoordinateMode
                + "\"}";
        }

        try
        {
            return Marshal.PtrToStringAnsi(resultPointer) ?? string.Empty;
        }
        finally
        {
            E7VisionReleaseCString(resultPointer);
        }
#else
        return "{\"status\":\"unsupported_platform\",\"detail\":\"requires_ios_device_runtime\",\"source\":\""
            + RuntimeSource
            + "\",\"coordinateMode\":\""
            + CoordinateMode
            + "\",\"imageWidth\":"
            + width.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":"
            + height.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":0,\"leftOuterPointCount\":0,\"rightOuterPointCount\":0,\"leftEyePointCount\":0,\"rightEyePointCount\":0,\"leftOuter\":[],\"rightOuter\":[],\"leftEye\":[],\"rightEye\":[]}";
#endif
    }

    private void ApplyBoundaryPayload(MediaPipeEyebrowPayload payload, FaceScreenBounds faceBounds)
    {
        ApplyBoundaryPayload(payload, faceBounds, null, 0, 0);
    }

    private void ApplyBoundaryPayload(
        MediaPipeEyebrowPayload payload,
        FaceScreenBounds faceBounds,
        Color32[] framePixels,
        int frameWidth,
        int frameHeight)
    {
        sequence++;
        long detectedAtMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string status = NormalizeOptional(payload.status, "unknown");
        string detail = NormalizeOptional(payload.detail, "none");
        Vector2[] leftOuter = ConvertPoints(payload.leftOuter);
        Vector2[] rightOuter = ConvertPoints(payload.rightOuter);
        Vector2[] leftEye = ConvertPoints(payload.leftEye);
        Vector2[] rightEye = ConvertPoints(payload.rightEye);
        BrowRefinementStats refinementStats = RefineEyebrowBoundaries(
            framePixels,
            frameWidth,
            frameHeight,
            ref leftOuter,
            ref rightOuter,
            leftEye,
            rightEye,
            status == "ok");
        if (!string.IsNullOrWhiteSpace(refinementStats.Status))
        {
            detail = detail + "|" + refinementStats.Status;
        }

        bool available = status == "ok"
            && leftOuter.Length >= 3
            && rightOuter.Length >= 3
            && EyebrowBoundaryClearsEye(leftOuter, leftEye, out refinementStats.LeftBrowEyeGapPx)
            && EyebrowBoundaryClearsEye(rightOuter, rightEye, out refinementStats.RightBrowEyeGapPx);

        BoundarySnapshot rawSnapshot = new BoundarySnapshot
        {
            Available = available,
            Status = status,
            Detail = detail,
            Source = NormalizeOptional(payload.source, RuntimeSource),
            CoordinateMode = NormalizeOptional(payload.coordinateMode, CoordinateMode),
            ImageWidth = payload.imageWidth,
            ImageHeight = payload.imageHeight,
            FaceCount = payload.faceCount,
            LeftOuterPointCount = leftOuter.Length,
            RightOuterPointCount = rightOuter.Length,
            LeftEyePointCount = payload.leftEyePointCount > 0 ? payload.leftEyePointCount : leftEye.Length,
            RightEyePointCount = payload.rightEyePointCount > 0 ? payload.rightEyePointCount : rightEye.Length,
            Sequence = sequence,
            DetectedAtMs = detectedAtMs,
            AgeMs = 0,
            LeftOuterPoints = leftOuter,
            RightOuterPoints = rightOuter,
            LeftEyePoints = leftEye,
            RightEyePoints = rightEye,
            FaceBoundsAvailable = faceBounds.Available,
            FaceBoundsCenter = faceBounds.Center,
            FaceBoundsSize = faceBounds.Size,
            StabilizationMode = available ? "temporal_smooth" : "unavailable",
            FaceMotionScore = 0.0f,
            FaceMotionCenterShiftPx = 0.0f,
            FaceMotionScaleDelta = 0.0f,
            FaceMotionRisk = faceBounds.Available
                ? "initial_face_motion_reference"
                : "face_motion_unavailable",
            HairRefinementStatus = NormalizeOptional(refinementStats.Status, "unavailable"),
            LeftHairPixelCount = refinementStats.LeftHairPixelCount,
            RightHairPixelCount = refinementStats.RightHairPixelCount,
            LeftBrowEyeGapPx = refinementStats.LeftBrowEyeGapPx,
            RightBrowEyeGapPx = refinementStats.RightBrowEyeGapPx
        };

        if (latestSnapshot.Available && rawSnapshot.Available)
        {
            ApplyFaceMotionDiagnostics(latestSnapshot, ref rawSnapshot);
            float blend = ResolveTemporalBlend(latestSnapshot, rawSnapshot);
            rawSnapshot.LeftOuterPoints = LerpPoints(latestSnapshot.LeftOuterPoints, rawSnapshot.LeftOuterPoints, blend);
            rawSnapshot.RightOuterPoints = LerpPoints(latestSnapshot.RightOuterPoints, rawSnapshot.RightOuterPoints, blend);
            rawSnapshot.LeftEyePoints = LerpPoints(latestSnapshot.LeftEyePoints, rawSnapshot.LeftEyePoints, blend);
            rawSnapshot.RightEyePoints = LerpPoints(latestSnapshot.RightEyePoints, rawSnapshot.RightEyePoints, blend);
            rawSnapshot.StabilizationMode = rawSnapshot.FaceMotionRisk == "large_face_motion"
                ? "temporal_smooth|large_face_motion_smooth"
                : "temporal_smooth";
        }

        latestSnapshot = rawSnapshot;

        Debug.Log(
            "[E7] mediapipe_eyebrow_boundary_result"
            + " status=" + rawSnapshot.Status
            + " source=" + rawSnapshot.Source
            + " coordinateMode=" + rawSnapshot.CoordinateMode
            + " sequence=" + rawSnapshot.Sequence.ToString(CultureInfo.InvariantCulture)
            + " imageSize=" + rawSnapshot.ImageWidth.ToString(CultureInfo.InvariantCulture)
            + "x" + rawSnapshot.ImageHeight.ToString(CultureInfo.InvariantCulture)
            + " faceCount=" + rawSnapshot.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " leftOuterPoints=" + rawSnapshot.LeftOuterPointCount.ToString(CultureInfo.InvariantCulture)
            + " rightOuterPoints=" + rawSnapshot.RightOuterPointCount.ToString(CultureInfo.InvariantCulture)
            + " leftEyePoints=" + rawSnapshot.LeftEyePointCount.ToString(CultureInfo.InvariantCulture)
            + " rightEyePoints=" + rawSnapshot.RightEyePointCount.ToString(CultureInfo.InvariantCulture)
            + " available=" + rawSnapshot.Available.ToString().ToLowerInvariant()
            + " stabilization=" + rawSnapshot.StabilizationMode
            + " faceBoundsAvailable=" + rawSnapshot.FaceBoundsAvailable.ToString().ToLowerInvariant()
            + " faceMotionScore=" + rawSnapshot.FaceMotionScore.ToString("0.###", CultureInfo.InvariantCulture)
            + " faceMotionRisk=" + rawSnapshot.FaceMotionRisk
            + " hairRefinement=" + rawSnapshot.HairRefinementStatus
            + " leftHairPixels=" + rawSnapshot.LeftHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + " rightHairPixels=" + rawSnapshot.RightHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + " leftBrowEyeGapPx=" + rawSnapshot.LeftBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture)
            + " rightBrowEyeGapPx=" + rawSnapshot.RightBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture)
            + " rawCameraFrameStored=false"
            + " offDeviceUpload=false"
            + " detail=" + SanitizeLogValue(rawSnapshot.Detail));

        if (rnBridge != null)
        {
            rnBridge.SendE7MediaPipeEyebrowBoundaryEvent(BuildBoundaryEventJson(rawSnapshot));
        }
    }

    private static MediaPipeEyebrowPayload BuildFailurePayload(
        string status,
        string detail,
        int width,
        int height)
    {
        return new MediaPipeEyebrowPayload
        {
            status = status,
            detail = detail,
            source = RuntimeSource,
            coordinateMode = CoordinateMode,
            imageWidth = width,
            imageHeight = height,
            faceCount = 0,
            leftOuterPointCount = 0,
            rightOuterPointCount = 0,
            leftEyePointCount = 0,
            rightEyePointCount = 0,
            leftOuter = new MediaPipePointPayload[0],
            rightOuter = new MediaPipePointPayload[0],
            leftEye = new MediaPipePointPayload[0],
            rightEye = new MediaPipePointPayload[0]
        };
    }

    private static string BuildBoundaryEventJson(BoundarySnapshot snapshot)
    {
        return "{"
            + "\"type\":\"e7_mediapipe_eyebrow_boundary\""
            + ",\"status\":\"" + EscapeJsonString(snapshot.Status) + "\""
            + ",\"detail\":\"" + EscapeJsonString(snapshot.Detail) + "\""
            + ",\"source\":\"" + EscapeJsonString(snapshot.Source) + "\""
            + ",\"coordinateMode\":\"" + EscapeJsonString(snapshot.CoordinateMode) + "\""
            + ",\"sequence\":" + snapshot.Sequence.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + snapshot.ImageWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + snapshot.ImageHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":" + snapshot.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"leftOuterPointCount\":" + snapshot.LeftOuterPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rightOuterPointCount\":" + snapshot.RightOuterPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"leftEyePointCount\":" + snapshot.LeftEyePointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rightEyePointCount\":" + snapshot.RightEyePointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"available\":" + snapshot.Available.ToString().ToLowerInvariant()
            + ",\"stabilizationMode\":\"" + EscapeJsonString(snapshot.StabilizationMode) + "\""
            + ",\"faceBoundsAvailable\":" + snapshot.FaceBoundsAvailable.ToString().ToLowerInvariant()
            + ",\"faceMotionScore\":" + snapshot.FaceMotionScore.ToString("0.###", CultureInfo.InvariantCulture)
            + ",\"faceMotionCenterShiftPx\":" + snapshot.FaceMotionCenterShiftPx.ToString("0.#", CultureInfo.InvariantCulture)
            + ",\"faceMotionScaleDelta\":" + snapshot.FaceMotionScaleDelta.ToString("0.###", CultureInfo.InvariantCulture)
            + ",\"faceMotionRisk\":\"" + EscapeJsonString(snapshot.FaceMotionRisk) + "\""
            + ",\"hairRefinement\":\"" + EscapeJsonString(snapshot.HairRefinementStatus) + "\""
            + ",\"leftHairPixels\":" + snapshot.LeftHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + ",\"rightHairPixels\":" + snapshot.RightHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + ",\"leftBrowEyeGapPx\":" + snapshot.LeftBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture)
            + ",\"rightBrowEyeGapPx\":" + snapshot.RightBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture)
            + ",\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + "}";
    }

    private static string EscapeJsonString(string value)
    {
        if (string.IsNullOrEmpty(value))
        {
            return string.Empty;
        }

        return value
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"")
            .Replace("\n", "\\n")
            .Replace("\r", "\\r");
    }

    private FaceScreenBounds CaptureCurrentFaceBounds()
    {
        if (faceManager == null)
        {
            RefreshSceneReferences();
        }

        Camera camera = Camera.main;
        if (faceManager == null || camera == null)
        {
            return default;
        }

        foreach (ARFace face in faceManager.trackables)
        {
            if (face == null || face.trackingState != TrackingState.Tracking)
            {
                continue;
            }

            if (TryProjectFaceBounds(face, camera, out FaceScreenBounds bounds))
            {
                return bounds;
            }
        }

        return default;
    }

    private static bool TryProjectFaceBounds(ARFace face, Camera camera, out FaceScreenBounds bounds)
    {
        bounds = default;
        if (face == null
            || camera == null
            || !face.vertices.IsCreated
            || face.vertices.Length == 0)
        {
            return false;
        }

        float minX = float.MaxValue;
        float minY = float.MaxValue;
        float maxX = float.MinValue;
        float maxY = float.MinValue;
        int count = 0;
        for (int index = 0; index < face.vertices.Length; index++)
        {
            Vector3 screen = camera.WorldToScreenPoint(face.transform.TransformPoint(face.vertices[index]));
            if (screen.z <= 0.0f)
            {
                continue;
            }

            float topLeftY = Screen.height - screen.y;
            minX = Mathf.Min(minX, screen.x);
            maxX = Mathf.Max(maxX, screen.x);
            minY = Mathf.Min(minY, topLeftY);
            maxY = Mathf.Max(maxY, topLeftY);
            count++;
        }

        if (count <= 0 || maxX <= minX || maxY <= minY)
        {
            return false;
        }

        bounds = new FaceScreenBounds
        {
            Available = true,
            Center = new Vector2((minX + maxX) * 0.5f, (minY + maxY) * 0.5f),
            Size = new Vector2(maxX - minX, maxY - minY)
        };
        return true;
    }

    private static byte[] EncodeRgbPngTopLeft(Texture2D texture)
    {
        int width = texture.width;
        int height = texture.height;
        Color32[] pixels = texture.GetPixels32();
        byte[] raw = new byte[(width * 3 + 1) * height];
        int offset = 0;

        for (int y = height - 1; y >= 0; y--)
        {
            raw[offset++] = 0;
            int rowStart = y * width;
            for (int x = 0; x < width; x++)
            {
                Color32 pixel = pixels[rowStart + x];
                raw[offset++] = pixel.r;
                raw[offset++] = pixel.g;
                raw[offset++] = pixel.b;
            }
        }

        using (MemoryStream stream = new MemoryStream())
        {
            stream.Write(new byte[] { 137, 80, 78, 71, 13, 10, 26, 10 }, 0, 8);

            using (MemoryStream ihdr = new MemoryStream())
            {
                WriteBigEndianUInt32(ihdr, (uint)width);
                WriteBigEndianUInt32(ihdr, (uint)height);
                ihdr.WriteByte(8);
                ihdr.WriteByte(2);
                ihdr.WriteByte(0);
                ihdr.WriteByte(0);
                ihdr.WriteByte(0);
                WritePngChunk(stream, "IHDR", ihdr.ToArray());
            }

            WritePngChunk(stream, "IDAT", BuildStoredZlibPayload(raw));
            WritePngChunk(stream, "IEND", Array.Empty<byte>());
            return stream.ToArray();
        }
    }

    private static byte[] BuildStoredZlibPayload(byte[] raw)
    {
        using (MemoryStream stream = new MemoryStream())
        {
            stream.WriteByte(0x78);
            stream.WriteByte(0x01);

            int offset = 0;
            while (offset < raw.Length)
            {
                int blockLength = Math.Min(65535, raw.Length - offset);
                bool isFinal = offset + blockLength >= raw.Length;
                stream.WriteByte(isFinal ? (byte)0x01 : (byte)0x00);
                WriteLittleEndianUInt16(stream, (ushort)blockLength);
                WriteLittleEndianUInt16(stream, (ushort)~blockLength);
                stream.Write(raw, offset, blockLength);
                offset += blockLength;
            }

            WriteBigEndianUInt32(stream, CalculateAdler32(raw));
            return stream.ToArray();
        }
    }

    private static void WritePngChunk(Stream stream, string type, byte[] data)
    {
        byte[] typeBytes = Encoding.ASCII.GetBytes(type);
        WriteBigEndianUInt32(stream, (uint)data.Length);
        stream.Write(typeBytes, 0, typeBytes.Length);
        stream.Write(data, 0, data.Length);

        byte[] crcInput = new byte[typeBytes.Length + data.Length];
        Buffer.BlockCopy(typeBytes, 0, crcInput, 0, typeBytes.Length);
        Buffer.BlockCopy(data, 0, crcInput, typeBytes.Length, data.Length);
        WriteBigEndianUInt32(stream, CalculateCrc32(crcInput));
    }

    private static uint CalculateAdler32(byte[] data)
    {
        const uint modulus = 65521;
        uint a = 1;
        uint b = 0;
        for (int index = 0; index < data.Length; index++)
        {
            a = (a + data[index]) % modulus;
            b = (b + a) % modulus;
        }

        return (b << 16) | a;
    }

    private static uint CalculateCrc32(byte[] data)
    {
        uint crc = 0xffffffff;
        for (int index = 0; index < data.Length; index++)
        {
            crc ^= data[index];
            for (int bit = 0; bit < 8; bit++)
            {
                bool lsb = (crc & 1) != 0;
                crc >>= 1;
                if (lsb)
                {
                    crc ^= 0xedb88320;
                }
            }
        }

        return ~crc;
    }

    private static void WriteBigEndianUInt32(Stream stream, uint value)
    {
        stream.WriteByte((byte)((value >> 24) & 0xff));
        stream.WriteByte((byte)((value >> 16) & 0xff));
        stream.WriteByte((byte)((value >> 8) & 0xff));
        stream.WriteByte((byte)(value & 0xff));
    }

    private static void WriteLittleEndianUInt16(Stream stream, ushort value)
    {
        stream.WriteByte((byte)(value & 0xff));
        stream.WriteByte((byte)((value >> 8) & 0xff));
    }

    private static BrowRefinementStats RefineEyebrowBoundaries(
        Color32[] framePixels,
        int frameWidth,
        int frameHeight,
        ref Vector2[] leftOuter,
        ref Vector2[] rightOuter,
        Vector2[] leftEye,
        Vector2[] rightEye,
        bool canRefine)
    {
        BrowRefinementStats stats = new BrowRefinementStats
        {
            Status = "pixel_refine_unavailable",
            LeftBrowEyeGapPx = 0.0f,
            RightBrowEyeGapPx = 0.0f
        };

        if (!canRefine
            || framePixels == null
            || frameWidth <= 0
            || frameHeight <= 0
            || framePixels.Length != frameWidth * frameHeight)
        {
            return stats;
        }

        leftOuter = RefineSingleBrowBoundary(
            framePixels,
            frameWidth,
            frameHeight,
            leftOuter,
            leftEye,
            true,
            out stats.LeftHairPixelCount,
            out stats.LeftBrowEyeGapPx);
        rightOuter = RefineSingleBrowBoundary(
            framePixels,
            frameWidth,
            frameHeight,
            rightOuter,
            rightEye,
            false,
            out stats.RightHairPixelCount,
            out stats.RightBrowEyeGapPx);

        stats.Status = "pixel_refined_makeup_body_column_boundary_first"
            + ":leftHair=" + stats.LeftHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + ",rightHair=" + stats.RightHairPixelCount.ToString(CultureInfo.InvariantCulture)
            + ",leftGap=" + stats.LeftBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture)
            + ",rightGap=" + stats.RightBrowEyeGapPx.ToString("0.###", CultureInfo.InvariantCulture);
        return stats;
    }

    private static Vector2[] RefineSingleBrowBoundary(
        Color32[] framePixels,
        int frameWidth,
        int frameHeight,
        Vector2[] seedBoundary,
        Vector2[] eyeBoundary,
        bool screenLeftBrow,
        out int hairPixelCount,
        out float browEyeGapPx)
    {
        hairPixelCount = 0;
        browEyeGapPx = 0.0f;
        if (!TryCalculatePointBounds(seedBoundary, out float seedLeft, out float seedTop, out float seedRight, out float seedBottom))
        {
            return seedBoundary ?? Array.Empty<Vector2>();
        }

        float seedWidth = Mathf.Max(8.0f, seedRight - seedLeft);
        float seedHeight = Mathf.Max(6.0f, seedBottom - seedTop);
        float eyeTop = TryCalculatePointBounds(eyeBoundary, out _, out float detectedEyeTop, out _, out _)
            ? detectedEyeTop
            : seedBottom + seedHeight * 2.0f;
        float browSearchHeight = Mathf.Clamp(seedWidth * 0.30f, 22.0f, 72.0f);
        float browSearchTop = Mathf.Max(
            seedTop - Mathf.Clamp(seedHeight * 0.28f, 4.0f, 12.0f),
            eyeTop - browSearchHeight);
        float browSearchBottom = Mathf.Min(
            seedBottom + Mathf.Clamp(seedHeight * 0.24f, 3.0f, 10.0f),
            eyeTop - BrowMinimumEyeGapPx);
        int roiLeft = Mathf.Clamp(Mathf.FloorToInt(seedLeft - seedWidth * 0.18f - 8.0f), 0, frameWidth - 1);
        int roiRight = Mathf.Clamp(Mathf.CeilToInt(seedRight + seedWidth * 0.18f + 8.0f), 0, frameWidth - 1);
        int roiTop = Mathf.Clamp(Mathf.FloorToInt(browSearchTop), 0, frameHeight - 1);
        int roiBottom = Mathf.Clamp(
            Mathf.CeilToInt(browSearchBottom),
            0,
            frameHeight - 1);
        if (roiRight <= roiLeft || roiBottom <= roiTop)
        {
            Vector2[] fallback = BuildDesiredBrowPolygonFromBox(
                seedLeft,
                seedTop,
                seedRight,
                Mathf.Min(seedBottom, eyeTop - BrowMinimumEyeGapPx),
                screenLeftBrow);
            EyebrowBoundaryClearsEye(fallback, eyeBoundary, out browEyeGapPx);
            return fallback;
        }

        List<int>[] columnYs = CreateBrowColumnBuckets();
        float roiWidth = Mathf.Max(1.0f, roiRight - roiLeft + 1.0f);
        for (int y = roiTop; y <= roiBottom; y += BrowRefinementSampleStepPx)
        {
            for (int x = roiLeft; x <= roiRight; x += BrowRefinementSampleStepPx)
            {
                Vector2 samplePoint = new Vector2(x + 0.5f, y + 0.5f);
                if (IsPointInsideEyeRejectZone(samplePoint, eyeBoundary, BrowMinimumEyeGapPx))
                {
                    continue;
                }

                if (!IsPointInScaledBoundary(samplePoint, seedBoundary, 1.20f, 1.70f))
                {
                    continue;
                }

                Color32 pixel = ReadTopLeftPixel(framePixels, frameWidth, frameHeight, x, y);
                if (!LooksLikeBrowHair(framePixels, frameWidth, frameHeight, x, y, pixel))
                {
                    continue;
                }

                int columnIndex = Mathf.Clamp(
                    Mathf.FloorToInt(((x - roiLeft) / roiWidth) * BrowEnvelopeColumnCount),
                    0,
                    BrowEnvelopeColumnCount - 1);
                columnYs[columnIndex].Add(y);
                hairPixelCount++;
            }
        }

        Vector2[] refined = null;
        int minimumHairPixels = Mathf.Max(18, Mathf.RoundToInt(seedWidth * 0.09f));
        if (hairPixelCount >= minimumHairPixels)
        {
            refined = BuildBrowEnvelopePolygonFromColumns(
                columnYs,
                roiLeft,
                roiRight,
                seedLeft,
                seedTop,
                seedRight,
                seedBottom,
                eyeTop,
                screenLeftBrow);
        }

        if (refined == null || refined.Length < 3)
        {
            float desiredBottom = Mathf.Min(seedBottom + seedHeight * 0.05f, eyeTop - BrowMinimumEyeGapPx);
            refined = BuildDesiredBrowPolygonFromBox(
                seedLeft - seedWidth * 0.035f,
                desiredBottom - Mathf.Clamp(seedHeight * 0.82f, seedWidth * 0.080f, seedWidth * 0.155f),
                seedRight + seedWidth * 0.035f,
                desiredBottom,
                screenLeftBrow);
        }

        ClampPointsToFrame(refined, frameWidth, frameHeight);
        EyebrowBoundaryClearsEye(refined, eyeBoundary, out browEyeGapPx);
        return refined;
    }

    private static List<int>[] CreateBrowColumnBuckets()
    {
        List<int>[] buckets = new List<int>[BrowEnvelopeColumnCount];
        for (int index = 0; index < buckets.Length; index++)
        {
            buckets[index] = new List<int>();
        }

        return buckets;
    }

    private static Vector2[] BuildBrowEnvelopePolygonFromColumns(
        List<int>[] columnYs,
        int roiLeft,
        int roiRight,
        float seedLeft,
        float seedTop,
        float seedRight,
        float seedBottom,
        float eyeTop,
        bool screenLeftBrow)
    {
        if (columnYs == null || columnYs.Length == 0)
        {
            return null;
        }

        int columnCount = columnYs.Length;
        bool[] valid = new bool[columnCount];
        float[] top = new float[columnCount];
        float[] bottom = new float[columnCount];
        int[] columnCounts = new int[columnCount];
        int firstValid = -1;
        int lastValid = -1;
        int validCount = 0;

        for (int column = 0; column < columnCount; column++)
        {
            List<int> values = columnYs[column];
            if (values == null || values.Count < 2)
            {
                continue;
            }

            values.Sort();
            valid[column] = true;
            columnCounts[column] = values.Count;
            top[column] = Percentile(values, 0.24f);
            bottom[column] = Percentile(values, 0.76f);
            if (bottom[column] < top[column] + 1.0f)
            {
                bottom[column] = top[column] + 1.0f;
            }

            if (firstValid < 0)
            {
                firstValid = column;
            }

            lastValid = column;
            validCount++;
        }

        if (validCount < BrowEnvelopeMinValidColumns || firstValid < 0 || lastValid <= firstValid)
        {
            return null;
        }

        if (TryResolveDenseBrowCoreRange(
                valid,
                columnCounts,
                out int denseFirst,
                out int denseLast))
        {
            firstValid = Mathf.Max(0, denseFirst - BrowDenseCorePaddingColumns);
            lastValid = Mathf.Min(columnCount - 1, denseLast + BrowDenseCorePaddingColumns);
        }

        float seedWidth = Mathf.Max(8.0f, seedRight - seedLeft);
        float seedHeight = Mathf.Max(4.0f, seedBottom - seedTop);
        float measuredTop = float.MaxValue;
        float measuredBottom = float.MinValue;
        float measuredCenterSum = 0.0f;
        int measuredCenterCount = 0;
        for (int column = firstValid; column <= lastValid; column++)
        {
            if (!valid[column])
            {
                continue;
            }

            measuredTop = Mathf.Min(measuredTop, top[column]);
            measuredBottom = Mathf.Max(measuredBottom, bottom[column]);
            measuredCenterSum += (top[column] + bottom[column]) * 0.5f;
            measuredCenterCount++;
        }

        float measuredCenterY = measuredCenterCount > 0
            ? measuredCenterSum / measuredCenterCount
            : (seedTop + seedBottom) * 0.5f;
        float measuredHeight = measuredBottom > measuredTop
            ? measuredBottom - measuredTop
            : seedHeight;

        FillMissingBrowColumns(top, bottom, valid, seedTop, seedBottom, seedWidth);
        SmoothBrowEnvelope(top, 3);
        SmoothBrowEnvelope(bottom, 3);

        float roiWidth = Mathf.Max(1.0f, roiRight - roiLeft + 1.0f);
        float columnWidth = roiWidth / Mathf.Max(1, columnCount);
        float hairLeft = roiLeft + firstValid * columnWidth;
        float hairRight = roiLeft + (lastValid + 1) * columnWidth;
        float hairWidth = Mathf.Max(8.0f, hairRight - hairLeft);
        float hairCenterX = (hairLeft + hairRight) * 0.5f;
        float seedCenterX = (seedLeft + seedRight) * 0.5f;
        float centerShift = Mathf.Clamp(
            hairCenterX - seedCenterX,
            -seedWidth * 0.060f,
            seedWidth * 0.060f);
        float seedTailInset = Mathf.Clamp(seedWidth * 0.040f, 3.0f, 12.0f);
        float seedHeadInset = Mathf.Clamp(
            seedWidth * (screenLeftBrow ? 0.118f : 0.178f),
            screenLeftBrow ? 10.0f : 18.0f,
            screenLeftBrow ? 34.0f : 52.0f);
        float hairTailInset = Mathf.Clamp(hairWidth * 0.025f, 2.0f, 7.0f);
        float hairHeadInset = Mathf.Clamp(
            hairWidth * (screenLeftBrow ? 0.090f : 0.168f),
            screenLeftBrow ? 5.0f : 10.0f,
            screenLeftBrow ? 22.0f : 36.0f);
        float seedTargetLeft = screenLeftBrow
            ? seedLeft + seedTailInset
            : seedLeft + seedHeadInset;
        float seedTargetRight = screenLeftBrow
            ? seedRight - seedHeadInset
            : seedRight - seedTailInset;
        float hairTargetLeft = screenLeftBrow
            ? hairLeft + hairTailInset
            : hairLeft + hairHeadInset;
        float hairTargetRight = screenLeftBrow
            ? hairRight - hairHeadInset
            : hairRight - hairTailInset;
        float left = Mathf.Lerp(seedTargetLeft, hairTargetLeft, 0.72f)
            + centerShift * 0.24f;
        float right = Mathf.Lerp(seedTargetRight, hairTargetRight, 0.72f)
            + centerShift * 0.24f;

        if (right <= left + 4.0f)
        {
            return null;
        }

        Vector2[] polygon = new Vector2[BrowMakeupShapePointCount * 2];
        float maxBottom = eyeTop - BrowMinimumEyeGapPx;
        float makeupShapeHeight = Mathf.Clamp(
            Mathf.Max(measuredHeight * 1.90f, seedWidth * 0.225f, seedHeight * 1.66f),
            Mathf.Clamp(seedWidth * 0.165f, 14.0f, 32.0f),
            Mathf.Clamp(seedWidth * 0.295f, 34.0f, 64.0f));
        float seedCenterY = (seedTop + seedBottom) * 0.5f;
        float baseCenterY = Mathf.Lerp(seedCenterY, measuredCenterY, 0.58f);
        float bodyBottomAnchor = Mathf.Min(
            Mathf.Max(
                seedBottom + seedHeight * 0.12f,
                baseCenterY + makeupShapeHeight * 0.36f),
            maxBottom);
        float shapeTopY = bodyBottomAnchor - makeupShapeHeight;
        for (int index = 0; index < BrowMakeupShapePointCount; index++)
        {
            float t = index / (float)(BrowMakeupShapePointCount - 1);
            float x = Mathf.Lerp(left, right, t);
            float columnPosition = Mathf.Clamp01((x - roiLeft) / roiWidth) * (columnCount - 1);
            float sampledTop = SampleFloatArray(top, columnPosition);
            float sampledBottom = SampleFloatArray(bottom, columnPosition);
            float bodyT = 1.0f - Mathf.Abs(t - 0.5f) * 2.0f;
            float progressFromTail = screenLeftBrow ? t : 1.0f - t;
            float sampledCenterY = sampledTop * 0.46f + sampledBottom * 0.54f;
            float localCenterY = Mathf.Lerp(
                baseCenterY,
                sampledCenterY,
                0.18f);
            float localTopY = Mathf.Lerp(
                shapeTopY,
                localCenterY - makeupShapeHeight * 0.48f,
                0.16f);
            localTopY -= Mathf.Clamp(seedWidth * 0.004f, 0.5f, 1.8f)
                * Smooth01(Mathf.InverseLerp(0.05f, 0.82f, bodyT));

            float topY = localTopY + makeupShapeHeight * EvaluateBrowFillTop(progressFromTail);
            float bottomY = localTopY + makeupShapeHeight * EvaluateBrowFillBottom(progressFromTail);
            if (bottomY > maxBottom)
            {
                float shift = bottomY - maxBottom;
                topY -= shift;
                bottomY -= shift;
            }

            polygon[index] = new Vector2(x, topY);
            polygon[polygon.Length - 1 - index] = new Vector2(x, bottomY);
        }

        return polygon;
    }

    private static float EvaluateBrowFillTop(float progressFromTail)
    {
        return EvaluateBrowFillCurve(
            progressFromTail,
            0.60f,
            0.38f,
            0.04f,
            0.15f,
            0.38f);
    }

    private static float EvaluateBrowFillBottom(float progressFromTail)
    {
        return EvaluateBrowFillCurve(
            progressFromTail,
            0.60f,
            0.59f,
            0.74f,
            0.82f,
            0.92f);
    }

    private static float EvaluateBrowFillCurve(
        float progress,
        float tail,
        float outerBody,
        float archBody,
        float innerBody,
        float head)
    {
        progress = Mathf.Clamp01(progress);
        if (progress <= 0.20f)
        {
            return Mathf.Lerp(tail, outerBody, Smooth01(progress / 0.20f));
        }

        if (progress <= 0.52f)
        {
            return Mathf.Lerp(outerBody, archBody, Smooth01((progress - 0.20f) / 0.32f));
        }

        if (progress <= 0.82f)
        {
            return Mathf.Lerp(archBody, innerBody, Smooth01((progress - 0.52f) / 0.30f));
        }

        return Mathf.Lerp(innerBody, head, Smooth01((progress - 0.82f) / 0.18f));
    }

    private static bool TryResolveDenseBrowCoreRange(
        bool[] valid,
        int[] columnCounts,
        out int first,
        out int last)
    {
        first = -1;
        last = -1;
        if (valid == null
            || columnCounts == null
            || valid.Length == 0
            || columnCounts.Length != valid.Length)
        {
            return false;
        }

        List<int> nonZeroCounts = new List<int>();
        for (int index = 0; index < valid.Length; index++)
        {
            if (valid[index] && columnCounts[index] > 0)
            {
                nonZeroCounts.Add(columnCounts[index]);
            }
        }

        if (nonZeroCounts.Count < BrowEnvelopeMinValidColumns)
        {
            return false;
        }

        nonZeroCounts.Sort();
        float medianCount = Percentile(nonZeroCounts, 0.50f);
        int denseThreshold = Mathf.Max(2, Mathf.RoundToInt(medianCount * 0.38f));
        int denseStart = -1;
        int denseEnd = -1;

        for (int index = 0; index < valid.Length; index++)
        {
            bool dense = valid[index] && columnCounts[index] >= denseThreshold;
            if (!dense)
            {
                continue;
            }

            if (denseStart < 0)
            {
                denseStart = index;
            }

            denseEnd = index;
        }

        if (denseStart < 0
            || denseEnd <= denseStart
            || denseEnd - denseStart + 1 < BrowEnvelopeMinValidColumns)
        {
            return false;
        }

        first = denseStart;
        last = denseEnd;
        return true;
    }

    private static void FillMissingBrowColumns(
        float[] top,
        float[] bottom,
        bool[] valid,
        float seedTop,
        float seedBottom,
        float seedWidth)
    {
        float seedCenter = (seedTop + seedBottom) * 0.5f;
        float fallbackHalf = Mathf.Clamp(seedWidth * 0.030f, 2.0f, 8.0f);
        for (int index = 0; index < valid.Length; index++)
        {
            if (valid[index])
            {
                continue;
            }

            int previous = FindPreviousValid(valid, index);
            int next = FindNextValid(valid, index);
            if (previous >= 0 && next >= 0)
            {
                float t = (index - previous) / (float)Mathf.Max(1, next - previous);
                top[index] = Mathf.Lerp(top[previous], top[next], t);
                bottom[index] = Mathf.Lerp(bottom[previous], bottom[next], t);
            }
            else if (previous >= 0)
            {
                top[index] = top[previous];
                bottom[index] = bottom[previous];
            }
            else if (next >= 0)
            {
                top[index] = top[next];
                bottom[index] = bottom[next];
            }
            else
            {
                top[index] = seedCenter - fallbackHalf;
                bottom[index] = seedCenter + fallbackHalf;
            }
        }
    }

    private static int FindPreviousValid(bool[] valid, int start)
    {
        for (int index = start - 1; index >= 0; index--)
        {
            if (valid[index])
            {
                return index;
            }
        }

        return -1;
    }

    private static int FindNextValid(bool[] valid, int start)
    {
        for (int index = start + 1; index < valid.Length; index++)
        {
            if (valid[index])
            {
                return index;
            }
        }

        return -1;
    }

    private static void SmoothBrowEnvelope(float[] values, int passes)
    {
        if (values == null || values.Length < 3)
        {
            return;
        }

        float[] scratch = new float[values.Length];
        for (int pass = 0; pass < passes; pass++)
        {
            Array.Copy(values, scratch, values.Length);
            for (int index = 1; index < values.Length - 1; index++)
            {
                values[index] = scratch[index - 1] * 0.24f
                    + scratch[index] * 0.52f
                    + scratch[index + 1] * 0.24f;
            }
        }
    }

    private static float SampleFloatArray(float[] values, float position)
    {
        if (values == null || values.Length == 0)
        {
            return 0.0f;
        }

        position = Mathf.Clamp(position, 0.0f, values.Length - 1);
        int lower = Mathf.FloorToInt(position);
        int upper = Mathf.CeilToInt(position);
        if (lower == upper)
        {
            return values[lower];
        }

        return Mathf.Lerp(values[lower], values[upper], position - lower);
    }

    private static float Smooth01(float value)
    {
        value = Mathf.Clamp01(value);
        return value * value * (3.0f - 2.0f * value);
    }

    private static Vector2[] BuildDesiredBrowPolygonFromBox(
        float left,
        float top,
        float right,
        float bottom,
        bool screenLeftBrow)
    {
        const int sampleCount = BrowMakeupShapePointCount;
        Vector2[] polygon = new Vector2[sampleCount * 2];
        float height = Mathf.Max(5.0f, bottom - top);

        for (int index = 0; index < sampleCount; index++)
        {
            float t = index / (float)(sampleCount - 1);
            float x = Mathf.Lerp(left, right, t);
            float progressFromTail = screenLeftBrow ? t : 1.0f - t;
            polygon[index] = new Vector2(
                x,
                top + height * EvaluateBrowFillTop(progressFromTail));
            polygon[polygon.Length - 1 - index] = new Vector2(
                x,
                top + height * EvaluateBrowFillBottom(progressFromTail));
        }

        return polygon;
    }

    private static bool EyebrowBoundaryClearsEye(Vector2[] browBoundary, Vector2[] eyeBoundary, out float browEyeGapPx)
    {
        browEyeGapPx = 0.0f;
        if (!TryCalculatePointBounds(browBoundary, out _, out _, out _, out float browBottom))
        {
            return false;
        }

        if (!TryCalculatePointBounds(eyeBoundary, out _, out float eyeTop, out _, out _))
        {
            browEyeGapPx = BrowMinimumEyeGapPx;
            return true;
        }

        browEyeGapPx = eyeTop - browBottom;
        return browEyeGapPx >= BrowMinimumEyeGapPx;
    }

    private static bool IsPointInScaledBoundary(
        Vector2 point,
        Vector2[] polygon,
        float scaleX,
        float scaleY)
    {
        if (!TryCalculatePointBounds(polygon, out float left, out float top, out float right, out float bottom))
        {
            return false;
        }

        Vector2 center = new Vector2((left + right) * 0.5f, (top + bottom) * 0.5f);
        Vector2 projected = new Vector2(
            center.x + (point.x - center.x) / Mathf.Max(0.001f, scaleX),
            center.y + (point.y - center.y) / Mathf.Max(0.001f, scaleY));
        return IsPointInPolygon(projected, polygon);
    }

    private static bool IsPointInsideEyeRejectZone(
        Vector2 point,
        Vector2[] eyeBoundary,
        float topPaddingPx)
    {
        if (!TryCalculatePointBounds(eyeBoundary, out float left, out float top, out float right, out _))
        {
            return false;
        }

        float horizontalPadding = Mathf.Max(8.0f, (right - left) * 0.18f);
        return point.x >= left - horizontalPadding
            && point.x <= right + horizontalPadding
            && point.y >= top - topPaddingPx;
    }

    private static bool IsPointInPolygon(Vector2 point, Vector2[] polygon)
    {
        bool inside = false;
        int count = polygon != null ? polygon.Length : 0;
        if (count < 3)
        {
            return false;
        }

        for (int current = 0, previous = count - 1; current < count; previous = current++)
        {
            Vector2 a = polygon[current];
            Vector2 b = polygon[previous];
            bool crossesY = (a.y > point.y) != (b.y > point.y);
            if (!crossesY)
            {
                continue;
            }

            float denominator = b.y - a.y;
            if (Mathf.Abs(denominator) < 0.00001f)
            {
                continue;
            }

            float crossingX = (b.x - a.x) * (point.y - a.y) / denominator + a.x;
            if (point.x < crossingX)
            {
                inside = !inside;
            }
        }

        return inside;
    }

    private static bool TryCalculatePointBounds(
        Vector2[] points,
        out float left,
        out float top,
        out float right,
        out float bottom)
    {
        left = float.MaxValue;
        top = float.MaxValue;
        right = float.MinValue;
        bottom = float.MinValue;
        if (points == null || points.Length == 0)
        {
            return false;
        }

        int validCount = 0;
        for (int index = 0; index < points.Length; index++)
        {
            Vector2 point = points[index];
            if (float.IsNaN(point.x)
                || float.IsNaN(point.y)
                || float.IsInfinity(point.x)
                || float.IsInfinity(point.y))
            {
                continue;
            }

            left = Mathf.Min(left, point.x);
            right = Mathf.Max(right, point.x);
            top = Mathf.Min(top, point.y);
            bottom = Mathf.Max(bottom, point.y);
            validCount++;
        }

        return validCount > 0 && right > left && bottom > top;
    }

    private static Color32 ReadTopLeftPixel(Color32[] pixels, int width, int height, int x, int topLeftY)
    {
        x = Mathf.Clamp(x, 0, width - 1);
        topLeftY = Mathf.Clamp(topLeftY, 0, height - 1);
        int textureY = height - 1 - topLeftY;
        return pixels[textureY * width + x];
    }

    private static bool LooksLikeBrowHair(
        Color32[] pixels,
        int width,
        int height,
        int x,
        int topLeftY,
        Color32 pixel)
    {
        float luma = CalculateLuma(pixel);
        int maxChannel = Mathf.Max(pixel.r, Mathf.Max(pixel.g, pixel.b));
        int minChannel = Mathf.Min(pixel.r, Mathf.Min(pixel.g, pixel.b));
        int chromaSpread = maxChannel - minChannel;
        float localContrast = CalculateLocalDarkContrast(pixels, width, height, x, topLeftY, luma);

        return luma < 72.0f
            || (luma < 118.0f && maxChannel < 156 && chromaSpread < 64 && localContrast > 4.0f)
            || (luma < 146.0f && maxChannel < 178 && chromaSpread < 58 && localContrast > 9.0f);
    }

    private static float CalculateLuma(Color32 pixel)
    {
        return pixel.r * 0.299f + pixel.g * 0.587f + pixel.b * 0.114f;
    }

    private static float CalculateLocalDarkContrast(
        Color32[] pixels,
        int width,
        int height,
        int x,
        int topLeftY,
        float centerLuma)
    {
        const int radius = 4;
        int count = 0;
        float sum = 0.0f;
        for (int dy = -radius; dy <= radius; dy += radius)
        {
            for (int dx = -radius; dx <= radius; dx += radius)
            {
                if (dx == 0 && dy == 0)
                {
                    continue;
                }

                Color32 sample = ReadTopLeftPixel(pixels, width, height, x + dx, topLeftY + dy);
                sum += CalculateLuma(sample);
                count++;
            }
        }

        if (count <= 0)
        {
            return 0.0f;
        }

        return (sum / count) - centerLuma;
    }

    private static float Percentile(List<int> sortedValues, float percentile)
    {
        if (sortedValues == null || sortedValues.Count == 0)
        {
            return 0.0f;
        }

        float position = Mathf.Clamp01(percentile) * (sortedValues.Count - 1);
        int lowerIndex = Mathf.FloorToInt(position);
        int upperIndex = Mathf.CeilToInt(position);
        if (lowerIndex == upperIndex)
        {
            return sortedValues[lowerIndex];
        }

        return Mathf.Lerp(sortedValues[lowerIndex], sortedValues[upperIndex], position - lowerIndex);
    }

    private static void ClampPointsToFrame(Vector2[] points, int width, int height)
    {
        if (points == null)
        {
            return;
        }

        for (int index = 0; index < points.Length; index++)
        {
            points[index] = new Vector2(
                Mathf.Clamp(points[index].x, 0.0f, Mathf.Max(0, width - 1)),
                Mathf.Clamp(points[index].y, 0.0f, Mathf.Max(0, height - 1)));
        }
    }

    private static Vector2[] ConvertPoints(MediaPipePointPayload[] points)
    {
        if (points == null || points.Length == 0)
        {
            return Array.Empty<Vector2>();
        }

        Vector2[] converted = new Vector2[points.Length];
        for (int index = 0; index < points.Length; index++)
        {
            MediaPipePointPayload point = points[index];
            converted[index] = new Vector2(point != null ? point.x : 0.0f, point != null ? point.y : 0.0f);
        }

        return converted;
    }

    private static Vector2[] ScalePoints(Vector2[] points, float scaleX, float scaleY)
    {
        if (points == null || points.Length == 0)
        {
            return Array.Empty<Vector2>();
        }

        Vector2[] scaled = new Vector2[points.Length];
        for (int index = 0; index < points.Length; index++)
        {
            scaled[index] = new Vector2(points[index].x * scaleX, points[index].y * scaleY);
        }

        return scaled;
    }

    private static Vector2[] LerpPoints(Vector2[] from, Vector2[] to, float blend)
    {
        if (from == null || to == null || from.Length != to.Length)
        {
            return to ?? Array.Empty<Vector2>();
        }

        Vector2[] points = new Vector2[to.Length];
        for (int index = 0; index < to.Length; index++)
        {
            points[index] = Vector2.Lerp(from[index], to[index], Mathf.Clamp01(blend));
        }

        return points;
    }

    private static float ResolveTemporalBlend(BoundarySnapshot previous, BoundarySnapshot current)
    {
        if (!previous.Available || !current.Available)
        {
            return 1.0f;
        }

        return current.FaceMotionRisk == "large_face_motion"
            ? BoundaryLargeMotionBlend
            : BoundarySmoothBlend;
    }

    private static void ApplyFaceMotionDiagnostics(BoundarySnapshot previous, ref BoundarySnapshot current)
    {
        if (!previous.FaceBoundsAvailable
            || !current.FaceBoundsAvailable
            || previous.FaceBoundsSize.x <= 1.0f
            || previous.FaceBoundsSize.y <= 1.0f
            || current.FaceBoundsSize.x <= 1.0f
            || current.FaceBoundsSize.y <= 1.0f)
        {
            current.FaceMotionRisk = "face_motion_unavailable";
            return;
        }

        float centerShiftPx = Vector2.Distance(previous.FaceBoundsCenter, current.FaceBoundsCenter);
        float referenceSize = Mathf.Max(1.0f, Mathf.Max(previous.FaceBoundsSize.x, previous.FaceBoundsSize.y));
        float centerShiftNormalized = centerShiftPx / referenceSize;
        float scaleDelta = Mathf.Max(
            Mathf.Abs(current.FaceBoundsSize.x / previous.FaceBoundsSize.x - 1.0f),
            Mathf.Abs(current.FaceBoundsSize.y / previous.FaceBoundsSize.y - 1.0f));
        float motionScore = centerShiftNormalized + scaleDelta * 0.5f;
        current.FaceMotionCenterShiftPx = centerShiftPx;
        current.FaceMotionScaleDelta = scaleDelta;
        current.FaceMotionScore = motionScore;
        current.FaceMotionRisk = ResolveMediaPipeFaceMotionRisk(motionScore);
    }

    private static string ResolveMediaPipeFaceMotionRisk(float motionScore)
    {
        if (motionScore >= FaceMotionLargeThreshold)
        {
            return "large_face_motion";
        }

        if (motionScore >= FaceMotionMediumThreshold)
        {
            return "medium_face_motion";
        }

        return "low_face_motion";
    }

    private static string NormalizeOptional(string value, string fallback)
    {
        return string.IsNullOrWhiteSpace(value)
            ? fallback
            : value.Trim();
    }

    private static string SanitizeLogValue(string value)
    {
        return string.IsNullOrWhiteSpace(value)
            ? "none"
            : value.Replace(' ', '_').Replace('\n', '_').Replace('\r', '_');
    }
}
