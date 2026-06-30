using System;
using System.Globalization;
using UnityEngine;

[Serializable]
public sealed class MediaPipeFaceLandmarkPacket
{
    public const string ExpectedSource = "mediapipe_face_landmarker_full_face_v1";
    public const int MinimumLandmarkCount = 468;

    public string source;
    public string coordinateMode;
    public string inputFormat;
    public long frameId;
    public long timestampMs;
    public int imageWidth;
    public int imageHeight;
    public int faceCount;
    public int landmarkCount;
    public bool hasBlendshapes;
    public bool hasFacialTransformMatrix;
    public int facialTransformMatrixCount;
    public float faceConfidence;
    public int latencyMs;
    public int requestedOrientationDegrees;
    public int selectedOrientationDegrees;
    public bool orientationFallbackTried;
    public int orientationAttemptCount;
    public bool rawFrameStored;
    public bool offDeviceUpload;
    public MediaPipeFaceLandmark[] landmarks;
    public float[] facialTransformMatrix;

    public bool IsPrivacySafe => !rawFrameStored && !offDeviceUpload;
    public bool HasUsableLandmarks =>
        source == ExpectedSource
        && IsPrivacySafe
        && faceCount > 0
        && landmarkCount >= MinimumLandmarkCount
        && landmarks != null
        && landmarks.Length >= MinimumLandmarkCount;

    public static bool TryParse(
        string json,
        long latestAcceptedTimestampMs,
        out MediaPipeFaceLandmarkPacket packet,
        out string failureReason)
    {
        packet = null;
        failureReason = string.Empty;

        if (string.IsNullOrWhiteSpace(json))
        {
            failureReason = "empty_json";
            return false;
        }

        try
        {
            packet = JsonUtility.FromJson<MediaPipeFaceLandmarkPacket>(json);
        }
        catch (Exception exception)
        {
            failureReason = "json_parse_failed:" + exception.GetType().Name;
            return false;
        }

        if (packet == null)
        {
            failureReason = "json_parse_null";
            return false;
        }

        if (packet.source != ExpectedSource)
        {
            failureReason = "unexpected_source:" + Safe(packet.source);
            return false;
        }

        if (packet.rawFrameStored)
        {
            failureReason = "raw_frame_storage_not_allowed";
            return false;
        }

        if (packet.offDeviceUpload)
        {
            failureReason = "off_device_upload_not_allowed";
            return false;
        }

        if (packet.landmarkCount < MinimumLandmarkCount)
        {
            failureReason = "landmark_count_below_min:" + packet.landmarkCount.ToString(CultureInfo.InvariantCulture);
            return false;
        }

        if (packet.landmarks == null || packet.landmarks.Length < MinimumLandmarkCount)
        {
            int parsedCount = packet.landmarks != null ? packet.landmarks.Length : 0;
            failureReason = "landmarks_array_below_min:" + parsedCount.ToString(CultureInfo.InvariantCulture);
            return false;
        }

        if (packet.timestampMs <= latestAcceptedTimestampMs)
        {
            failureReason = "non_monotonic_timestamp";
            return false;
        }

        failureReason = "ok";
        return true;
    }

    public MediaPipeFaceLandmarkPacket CloneWithLandmarks(MediaPipeFaceLandmark[] nextLandmarks)
    {
        return new MediaPipeFaceLandmarkPacket
        {
            source = source,
            coordinateMode = coordinateMode,
            inputFormat = inputFormat,
            frameId = frameId,
            timestampMs = timestampMs,
            imageWidth = imageWidth,
            imageHeight = imageHeight,
            faceCount = faceCount,
            landmarkCount = landmarkCount,
            hasBlendshapes = hasBlendshapes,
            hasFacialTransformMatrix = hasFacialTransformMatrix,
            facialTransformMatrixCount = facialTransformMatrixCount,
            faceConfidence = faceConfidence,
            latencyMs = latencyMs,
            requestedOrientationDegrees = requestedOrientationDegrees,
            selectedOrientationDegrees = selectedOrientationDegrees,
            orientationFallbackTried = orientationFallbackTried,
            orientationAttemptCount = orientationAttemptCount,
            rawFrameStored = rawFrameStored,
            offDeviceUpload = offDeviceUpload,
            landmarks = nextLandmarks,
            facialTransformMatrix = facialTransformMatrix,
        };
    }

    private static string Safe(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "none" : value;
    }
}

[Serializable]
public struct MediaPipeFaceLandmark
{
    public int i;
    public float x;
    public float y;
    public float z;
    public float presence;

    public MediaPipeFaceLandmark(int index, float xValue, float yValue, float zValue, float presenceValue)
    {
        i = index;
        x = xValue;
        y = yValue;
        z = zValue;
        presence = presenceValue;
    }

    public static MediaPipeFaceLandmark Lerp(
        MediaPipeFaceLandmark previous,
        MediaPipeFaceLandmark current,
        float alpha)
    {
        return new MediaPipeFaceLandmark(
            current.i,
            Mathf.Lerp(previous.x, current.x, alpha),
            Mathf.Lerp(previous.y, current.y, alpha),
            Mathf.Lerp(previous.z, current.z, alpha),
            Mathf.Lerp(previous.presence, current.presence, alpha));
    }
}
