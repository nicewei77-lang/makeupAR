using System;
using System.Collections;
using System.Globalization;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using UnityEngine;

public sealed class E7VisionLipBoundaryRuntime : MonoBehaviour
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
        public int OuterPointCount;
        public int InnerPointCount;
        public int Sequence;
        public long DetectedAtMs;
        public long AgeMs;
        public Vector2[] OuterPoints;
        public Vector2[] InnerPoints;
    }

    [Serializable]
    private sealed class VisionPointPayload
    {
        public float x;
        public float y;
    }

    [Serializable]
    private sealed class VisionBoundaryPayload
    {
        public string status;
        public string detail;
        public string source;
        public string coordinateMode;
        public int imageWidth;
        public int imageHeight;
        public int faceCount;
        public int outerPointCount;
        public int innerPointCount;
        public VisionPointPayload[] outer;
        public VisionPointPayload[] inner;
    }

    private const float CaptureIntervalSeconds = 0.20f;
    private const long FreshBoundaryMaxAgeMs = 300;
    private const string RuntimeSource = "apple_vision_runtime_lip_landmarks";
    private const string CoordinateMode = "raw-y";

    private bool runtimeRequested;
    private bool captureInProgress;
    private float nextCaptureAt;
    private int sequence;
    private BoundarySnapshot latestSnapshot;
    private RNBridge rnBridge;
    private E3RegionMaskOverlay regionMaskOverlay;
    private FaceTrackingStatusReporter statusReporter;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern IntPtr E7VisionDetectLipBoundaryPng(
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
            "[E7] vision_lip_boundary_runtime"
            + " requested=" + runtimeRequested.ToString().ToLowerInvariant()
            + " source=" + RuntimeSource
            + " coordinateMode=" + CoordinateMode);
    }

    public bool TryGetLatestBoundary(
        int targetWidth,
        int targetHeight,
        out BoundarySnapshot snapshot)
    {
        snapshot = latestSnapshot;
        snapshot.AgeMs = latestSnapshot.DetectedAtMs > 0
            ? DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() - latestSnapshot.DetectedAtMs
            : 0;

        if (!latestSnapshot.Available
            || latestSnapshot.OuterPoints == null
            || latestSnapshot.InnerPoints == null
            || latestSnapshot.OuterPoints.Length < 3
            || latestSnapshot.InnerPoints.Length < 3
            || snapshot.AgeMs > FreshBoundaryMaxAgeMs)
        {
            return false;
        }

        if (targetWidth <= 0
            || targetHeight <= 0
            || latestSnapshot.ImageWidth <= 0
            || latestSnapshot.ImageHeight <= 0)
        {
            return true;
        }

        if (targetWidth == latestSnapshot.ImageWidth && targetHeight == latestSnapshot.ImageHeight)
        {
            return true;
        }

        float scaleX = targetWidth / (float)latestSnapshot.ImageWidth;
        float scaleY = targetHeight / (float)latestSnapshot.ImageHeight;
        snapshot.OuterPoints = ScalePoints(latestSnapshot.OuterPoints, scaleX, scaleY);
        snapshot.InnerPoints = ScalePoints(latestSnapshot.InnerPoints, scaleX, scaleY);
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
            regionMaskOverlay.SetVisionCaptureSuppressed(true);
        }

        if (statusReporter != null)
        {
            statusReporter.SetDebugOverlayVisible(false);
        }

        yield return new WaitForEndOfFrame();

        int width = Screen.width;
        int height = Screen.height;
        string status = "unknown";
        string detail = "none";
        Texture2D frameTexture = null;

        try
        {
            if (width <= 0 || height <= 0)
            {
                status = "invalid_screen_size";
                detail = "screen_width_or_height_zero";
                ApplyBoundaryPayload(BuildFailurePayload(status, detail, width, height));
                yield break;
            }

            frameTexture = new Texture2D(width, height, TextureFormat.RGB24, false);
            frameTexture.ReadPixels(new Rect(0, 0, width, height), 0, 0, false);
            frameTexture.Apply(false, false);
            byte[] pngBytes = EncodeRgbPngTopLeft(frameTexture);

            string json = DetectLipBoundaryJson(pngBytes, width, height);
            VisionBoundaryPayload payload = JsonUtility.FromJson<VisionBoundaryPayload>(json);
            if (payload == null)
            {
                ApplyBoundaryPayload(BuildFailurePayload(
                    "parse_failed",
                    "native_vision_json_empty",
                    width,
                    height));
            }
            else
            {
                ApplyBoundaryPayload(payload);
            }
        }
        catch (Exception exception)
        {
            status = "exception";
            detail = exception.GetType().Name + ":" + exception.Message;
            ApplyBoundaryPayload(BuildFailurePayload(status, detail, width, height));
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

    private string DetectLipBoundaryJson(byte[] pngBytes, int width, int height)
    {
#if UNITY_IOS && !UNITY_EDITOR
        IntPtr resultPointer = E7VisionDetectLipBoundaryPng(
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
            + ",\"faceCount\":0,\"outerPointCount\":0,\"innerPointCount\":0,\"outer\":[],\"inner\":[]}";
#endif
    }

    private void ApplyBoundaryPayload(VisionBoundaryPayload payload)
    {
        sequence++;
        long detectedAtMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string status = NormalizeOptional(payload.status, "unknown");
        Vector2[] outerPoints = ConvertPoints(payload.outer);
        Vector2[] innerPoints = ConvertPoints(payload.inner);
        bool available = status == "ok"
            && outerPoints.Length >= 3
            && innerPoints.Length >= 3;

        latestSnapshot = new BoundarySnapshot
        {
            Available = available,
            Status = status,
            Detail = NormalizeOptional(payload.detail, "none"),
            Source = NormalizeOptional(payload.source, RuntimeSource),
            CoordinateMode = NormalizeOptional(payload.coordinateMode, CoordinateMode),
            ImageWidth = payload.imageWidth,
            ImageHeight = payload.imageHeight,
            FaceCount = payload.faceCount,
            OuterPointCount = payload.outerPointCount > 0 ? payload.outerPointCount : outerPoints.Length,
            InnerPointCount = payload.innerPointCount > 0 ? payload.innerPointCount : innerPoints.Length,
            Sequence = sequence,
            DetectedAtMs = detectedAtMs,
            AgeMs = 0,
            OuterPoints = outerPoints,
            InnerPoints = innerPoints
        };

        Debug.Log(
            "[E7] vision_lip_boundary_result"
            + " status=" + latestSnapshot.Status
            + " source=" + latestSnapshot.Source
            + " coordinateMode=" + latestSnapshot.CoordinateMode
            + " sequence=" + latestSnapshot.Sequence.ToString(CultureInfo.InvariantCulture)
            + " imageSize=" + latestSnapshot.ImageWidth.ToString(CultureInfo.InvariantCulture)
            + "x" + latestSnapshot.ImageHeight.ToString(CultureInfo.InvariantCulture)
            + " faceCount=" + latestSnapshot.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " outerPoints=" + latestSnapshot.OuterPointCount.ToString(CultureInfo.InvariantCulture)
            + " innerPoints=" + latestSnapshot.InnerPointCount.ToString(CultureInfo.InvariantCulture)
            + " available=" + latestSnapshot.Available.ToString().ToLowerInvariant()
            + " rawCameraFrameStored=false"
            + " offDeviceUpload=false"
            + " detail=" + SanitizeLogValue(latestSnapshot.Detail));

        if (rnBridge != null)
        {
            rnBridge.SendE7VisionLipBoundaryEvent(BuildBoundaryEventJson(latestSnapshot));
        }
    }

    private static VisionBoundaryPayload BuildFailurePayload(
        string status,
        string detail,
        int width,
        int height)
    {
        return new VisionBoundaryPayload
        {
            status = status,
            detail = detail,
            source = RuntimeSource,
            coordinateMode = CoordinateMode,
            imageWidth = width,
            imageHeight = height,
            faceCount = 0,
            outerPointCount = 0,
            innerPointCount = 0,
            outer = new VisionPointPayload[0],
            inner = new VisionPointPayload[0]
        };
    }

    private static Vector2[] ConvertPoints(VisionPointPayload[] points)
    {
        if (points == null || points.Length == 0)
        {
            return Array.Empty<Vector2>();
        }

        Vector2[] converted = new Vector2[points.Length];
        for (int index = 0; index < points.Length; index++)
        {
            VisionPointPayload point = points[index];
            converted[index] = new Vector2(point != null ? point.x : 0.0f, point != null ? point.y : 0.0f);
        }

        return converted;
    }

    private static Vector2[] ScalePoints(Vector2[] points, float scaleX, float scaleY)
    {
        Vector2[] scaled = new Vector2[points.Length];
        for (int index = 0; index < points.Length; index++)
        {
            scaled[index] = new Vector2(points[index].x * scaleX, points[index].y * scaleY);
        }

        return scaled;
    }

    private static string BuildBoundaryEventJson(BoundarySnapshot snapshot)
    {
        return "{\"type\":\"e7_vision_lip_boundary\""
            + ",\"status\":\"" + EscapeJsonString(snapshot.Status) + "\""
            + ",\"source\":\"" + EscapeJsonString(snapshot.Source) + "\""
            + ",\"coordinateMode\":\"" + EscapeJsonString(snapshot.CoordinateMode) + "\""
            + ",\"sequence\":" + snapshot.Sequence.ToString(CultureInfo.InvariantCulture)
            + ",\"imageWidth\":" + snapshot.ImageWidth.ToString(CultureInfo.InvariantCulture)
            + ",\"imageHeight\":" + snapshot.ImageHeight.ToString(CultureInfo.InvariantCulture)
            + ",\"faceCount\":" + snapshot.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"outerPointCount\":" + snapshot.OuterPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"innerPointCount\":" + snapshot.InnerPointCount.ToString(CultureInfo.InvariantCulture)
            + ",\"available\":" + snapshot.Available.ToString().ToLowerInvariant()
            + ",\"rawCameraFrameStored\":false"
            + ",\"offDeviceUpload\":false"
            + ",\"detail\":\"" + EscapeJsonString(snapshot.Detail) + "\""
            + "}";
    }

    private static string NormalizeOptional(string value, string fallback)
    {
        return string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
    }

    private static string SanitizeLogValue(string value)
    {
        return string.IsNullOrWhiteSpace(value)
            ? "none"
            : value.Trim().Replace(" ", "_").Replace(",", "_").Replace("\"", string.Empty);
    }

    private static string EscapeJsonString(string value)
    {
        return string.IsNullOrEmpty(value)
            ? string.Empty
            : value.Replace("\\", "\\\\").Replace("\"", "\\\"");
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
}
