using System.Globalization;
using UnityEngine;

public sealed class MediaPipeFaceFrameSmoother
{
    private const long DefaultMaxStaleAgeMs = 180;
    private const float DefaultConfidenceGate = 0.5f;
    private const float DefaultAlpha = 0.65f;

    private MediaPipeFaceLandmarkPacket latestAcceptedPacket;
    private MediaPipeFaceLandmarkPacket latestSmoothedPacket;
    private string latestRejectReason = "not_started";
    private int acceptedPacketCount;
    private int rejectedPacketCount;
    private int stalePacketCount;
    private int droppedPacketCount;

    public long MaxStaleAgeMs { get; set; } = DefaultMaxStaleAgeMs;
    public float ConfidenceGate { get; set; } = DefaultConfidenceGate;
    public float Alpha { get; set; } = DefaultAlpha;
    public bool BypassSmoothing { get; set; }

    public MediaPipeFaceLandmarkPacket LatestAcceptedPacket => latestAcceptedPacket;
    public MediaPipeFaceLandmarkPacket LatestSmoothedPacket => latestSmoothedPacket;
    public string LatestRejectReason => latestRejectReason;
    public int AcceptedPacketCount => acceptedPacketCount;
    public int RejectedPacketCount => rejectedPacketCount;
    public int StalePacketCount => stalePacketCount;
    public int DroppedPacketCount => droppedPacketCount;
    public bool HasStablePacket => latestSmoothedPacket != null;

    public bool TryAcceptJson(
        string json,
        long nowMs,
        out MediaPipeFaceLandmarkPacket smoothedPacket,
        out MediaPipeFaceFrameSmoothingStatus status)
    {
        smoothedPacket = null;
        long latestTimestamp = latestAcceptedPacket != null ? latestAcceptedPacket.timestampMs : 0L;
        if (!MediaPipeFaceLandmarkPacket.TryParse(
                json,
                latestTimestamp,
                out MediaPipeFaceLandmarkPacket packet,
                out string failureReason))
        {
            rejectedPacketCount++;
            droppedPacketCount++;
            latestRejectReason = failureReason;
            status = BuildStatus(false, false, nowMs, latestRejectReason);
            return false;
        }

        long packetAgeMs = ClampNonNegativeAgeMs(nowMs, packet.timestampMs);
        if (packetAgeMs > MaxStaleAgeMs)
        {
            stalePacketCount++;
            rejectedPacketCount++;
            droppedPacketCount++;
            latestRejectReason = "stale_packet:" + packetAgeMs.ToString(CultureInfo.InvariantCulture);
            status = BuildStatus(false, true, nowMs, latestRejectReason);
            return false;
        }

        if (packet.faceConfidence < ConfidenceGate)
        {
            rejectedPacketCount++;
            droppedPacketCount++;
            latestRejectReason = "confidence_below_gate:" + packet.faceConfidence.ToString("0.###", CultureInfo.InvariantCulture);
            status = BuildStatus(false, false, nowMs, latestRejectReason);
            return false;
        }

        MediaPipeFaceLandmarkPacket nextPacket = BypassSmoothing || latestSmoothedPacket == null
            ? packet
            : packet.CloneWithLandmarks(SmoothLandmarks(latestSmoothedPacket.landmarks, packet.landmarks));

        latestAcceptedPacket = packet;
        latestSmoothedPacket = nextPacket;
        acceptedPacketCount++;
        latestRejectReason = "ok";
        smoothedPacket = nextPacket;
        status = BuildStatus(true, false, nowMs, "ok");
        return true;
    }

    public MediaPipeFaceFrameSmoothingStatus BuildCurrentStatus(long nowMs)
    {
        bool stale = false;
        if (latestAcceptedPacket != null)
        {
            stale = nowMs - latestAcceptedPacket.timestampMs > MaxStaleAgeMs;
        }

        return BuildStatus(HasStablePacket, stale, nowMs, latestRejectReason);
    }

    private MediaPipeFaceLandmark[] SmoothLandmarks(
        MediaPipeFaceLandmark[] previous,
        MediaPipeFaceLandmark[] current)
    {
        if (previous == null || current == null || previous.Length != current.Length)
        {
            return current;
        }

        float alpha = Mathf.Clamp01(Alpha);
        var smoothed = new MediaPipeFaceLandmark[current.Length];
        for (int index = 0; index < current.Length; index++)
        {
            smoothed[index] = MediaPipeFaceLandmark.Lerp(previous[index], current[index], alpha);
        }

        return smoothed;
    }

    private MediaPipeFaceFrameSmoothingStatus BuildStatus(
        bool accepted,
        bool stale,
        long nowMs,
        string reason)
    {
        long latestTimestamp = latestAcceptedPacket != null ? latestAcceptedPacket.timestampMs : 0L;
        long packetAgeMs = latestTimestamp > 0L ? ClampNonNegativeAgeMs(nowMs, latestTimestamp) : 0L;
        int landmarkCount = latestSmoothedPacket != null ? latestSmoothedPacket.landmarkCount : 0;
        float confidence = latestSmoothedPacket != null ? latestSmoothedPacket.faceConfidence : 0.0f;

        return new MediaPipeFaceFrameSmoothingStatus(
            accepted,
            stale,
            HasStablePacket,
            !BypassSmoothing,
            reason,
            packetAgeMs,
            landmarkCount,
            confidence,
            acceptedPacketCount,
            rejectedPacketCount,
            droppedPacketCount,
            stalePacketCount);
    }

    private static long ClampNonNegativeAgeMs(long nowMs, long timestampMs)
    {
        long ageMs = nowMs - timestampMs;
        return ageMs > 0L ? ageMs : 0L;
    }
}

public readonly struct MediaPipeFaceFrameSmoothingStatus
{
    public MediaPipeFaceFrameSmoothingStatus(
        bool accepted,
        bool stale,
        bool hasStablePacket,
        bool smoothingEnabled,
        string reason,
        long packetAgeMs,
        int landmarkCount,
        float confidence,
        int acceptedPacketCount,
        int rejectedPacketCount,
        int droppedPacketCount,
        int stalePacketCount)
    {
        Accepted = accepted;
        Stale = stale;
        HasStablePacket = hasStablePacket;
        SmoothingEnabled = smoothingEnabled;
        Reason = reason;
        PacketAgeMs = packetAgeMs;
        LandmarkCount = landmarkCount;
        Confidence = confidence;
        AcceptedPacketCount = acceptedPacketCount;
        RejectedPacketCount = rejectedPacketCount;
        DroppedPacketCount = droppedPacketCount;
        StalePacketCount = stalePacketCount;
    }

    public bool Accepted { get; }
    public bool Stale { get; }
    public bool HasStablePacket { get; }
    public bool SmoothingEnabled { get; }
    public string Reason { get; }
    public long PacketAgeMs { get; }
    public int LandmarkCount { get; }
    public float Confidence { get; }
    public int AcceptedPacketCount { get; }
    public int RejectedPacketCount { get; }
    public int DroppedPacketCount { get; }
    public int StalePacketCount { get; }
}
