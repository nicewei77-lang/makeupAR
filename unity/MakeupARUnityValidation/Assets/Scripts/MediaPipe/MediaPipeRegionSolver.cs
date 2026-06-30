using UnityEngine;

public static class MediaPipeRegionSolver
{
    public const int LipOuterPointCount = 20;
    public const int LipInnerCutoutPointCount = 20;
    public const int BrowPointCount = 10;
    public const int CheekPointCount = 10;

    private static readonly int[] LipOuterContour =
    {
        61, 146, 91, 181, 84, 17, 314, 405, 321, 375,
        291, 409, 270, 269, 267, 0, 37, 39, 40, 185,
    };

    private static readonly int[] LipInnerCutout =
    {
        78, 95, 88, 178, 87, 14, 317, 402, 318, 324,
        308, 415, 310, 311, 312, 13, 82, 81, 80, 191,
    };

    private static readonly int[] LeftBrowContour =
    {
        70, 63, 105, 66, 107, 55, 65, 52, 53, 46,
    };

    private static readonly int[] RightBrowContour =
    {
        336, 296, 334, 293, 300, 285, 295, 282, 283, 276,
    };

    private static readonly int[] LeftCheekPolygon =
    {
        50, 117, 118, 123, 147, 177, 215, 187, 205, 101,
    };

    private static readonly int[] RightCheekPolygon =
    {
        280, 346, 347, 352, 376, 401, 435, 411, 425, 330,
    };

    public static bool TrySolveLipRegion(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeLipRegion region)
    {
        var outerPoints = new Vector2[LipOuterPointCount];
        var innerPoints = new Vector2[LipInnerCutoutPointCount];
        return TrySolveLipRegionNonAlloc(packet, outerPoints, innerPoints, out region);
    }

    public static bool TrySolveLipRegionNonAlloc(
        MediaPipeFaceLandmarkPacket packet,
        Vector2[] outerPoints,
        Vector2[] innerCutoutPoints,
        out MediaPipeLipRegion region)
    {
        region = default;
        if (!TryBuildRegion(
                packet,
                LipOuterContour,
                outerPoints,
                out Vector2 centroid,
                out Rect bounds,
                out float confidence)
            || !TryCollectPoints(packet, LipInnerCutout, innerCutoutPoints, out _))
        {
            return false;
        }

        region = new MediaPipeLipRegion(outerPoints, innerCutoutPoints, centroid, bounds, confidence);
        return true;
    }

    public static bool TrySolveBrowRegions(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeBrowRegions regions)
    {
        var leftPoints = new Vector2[BrowPointCount];
        var rightPoints = new Vector2[BrowPointCount];
        return TrySolveBrowRegionsNonAlloc(packet, leftPoints, rightPoints, out regions);
    }

    public static bool TrySolveBrowRegionsNonAlloc(
        MediaPipeFaceLandmarkPacket packet,
        Vector2[] leftPoints,
        Vector2[] rightPoints,
        out MediaPipeBrowRegions regions)
    {
        regions = default;
        if (!TrySolveBrowRegion(packet, LeftBrowContour, leftPoints, out MediaPipeBrowRegion left)
            || !TrySolveBrowRegion(packet, RightBrowContour, rightPoints, out MediaPipeBrowRegion right))
        {
            return false;
        }

        regions = new MediaPipeBrowRegions(left, right);
        return true;
    }

    public static bool TrySolveCheekRegions(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeCheekRegions regions)
    {
        var leftPoints = new Vector2[CheekPointCount];
        var rightPoints = new Vector2[CheekPointCount];
        return TrySolveCheekRegionsNonAlloc(packet, leftPoints, rightPoints, out regions);
    }

    public static bool TrySolveCheekRegionsNonAlloc(
        MediaPipeFaceLandmarkPacket packet,
        Vector2[] leftPoints,
        Vector2[] rightPoints,
        out MediaPipeCheekRegions regions)
    {
        regions = default;
        if (!TrySolveCheekRegion(packet, LeftCheekPolygon, leftPoints, out MediaPipeCheekRegion left)
            || !TrySolveCheekRegion(packet, RightCheekPolygon, rightPoints, out MediaPipeCheekRegion right))
        {
            return false;
        }

        regions = new MediaPipeCheekRegions(left, right);
        return true;
    }

    private static bool TrySolveBrowRegion(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        Vector2[] points,
        out MediaPipeBrowRegion region)
    {
        region = default;
        if (!TryBuildRegion(
                packet,
                indexes,
                points,
                out Vector2 centroid,
                out Rect bounds,
                out float confidence))
        {
            return false;
        }

        region = new MediaPipeBrowRegion(points, centroid, bounds, confidence);
        return true;
    }

    private static bool TrySolveCheekRegion(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        Vector2[] points,
        out MediaPipeCheekRegion region)
    {
        region = default;
        if (!TryBuildRegion(
                packet,
                indexes,
                points,
                out Vector2 centroid,
                out Rect bounds,
                out float confidence))
        {
            return false;
        }

        region = new MediaPipeCheekRegion(points, centroid, bounds, confidence);
        return true;
    }

    private static bool TryBuildRegion(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        out Vector2[] points,
        out Vector2 centroid,
        out Rect bounds,
        out float confidence)
    {
        points = null;
        centroid = Vector2.zero;
        bounds = default;
        confidence = 0.0f;

        if (!TryCollectPoints(packet, indexes, out points, out confidence))
        {
            return false;
        }

        centroid = ComputeCentroid(points, indexes.Length);
        bounds = ComputeBounds(points, indexes.Length);
        return bounds.width > 0.0f && bounds.height > 0.0f;
    }

    private static bool TryBuildRegion(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        Vector2[] points,
        out Vector2 centroid,
        out Rect bounds,
        out float confidence)
    {
        centroid = Vector2.zero;
        bounds = default;
        confidence = 0.0f;

        if (!TryCollectPoints(packet, indexes, points, out confidence))
        {
            return false;
        }

        centroid = ComputeCentroid(points, indexes.Length);
        bounds = ComputeBounds(points, indexes.Length);
        return bounds.width > 0.0f && bounds.height > 0.0f;
    }

    private static bool TryCollectPoints(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        out Vector2[] points,
        out float confidence)
    {
        points = null;
        confidence = 0.0f;
        if (!IsUsablePacket(packet) || indexes == null || indexes.Length == 0)
        {
            return false;
        }

        points = new Vector2[indexes.Length];
        return TryCollectPoints(packet, indexes, points, out confidence);
    }

    private static bool TryCollectPoints(
        MediaPipeFaceLandmarkPacket packet,
        int[] indexes,
        Vector2[] points,
        out float confidence)
    {
        confidence = 0.0f;
        if (!IsUsablePacket(packet)
            || indexes == null
            || indexes.Length == 0
            || points == null
            || points.Length < indexes.Length)
        {
            return false;
        }

        float presenceTotal = 0.0f;
        for (int index = 0; index < indexes.Length; index++)
        {
            int landmarkIndex = indexes[index];
            if (landmarkIndex < 0 || landmarkIndex >= packet.landmarks.Length)
            {
                return false;
            }

            MediaPipeFaceLandmark landmark = packet.landmarks[landmarkIndex];
            points[index] = new Vector2(landmark.x, landmark.y);
            presenceTotal += landmark.presence > 0.0f ? landmark.presence : 1.0f;
        }

        confidence = Mathf.Clamp01((presenceTotal / indexes.Length) * packet.faceConfidence);
        return true;
    }

    private static bool IsUsablePacket(MediaPipeFaceLandmarkPacket packet)
    {
        return packet != null && packet.HasUsableLandmarks;
    }

    private static Vector2 ComputeCentroid(Vector2[] points, int count)
    {
        Vector2 total = Vector2.zero;
        for (int index = 0; index < count; index++)
        {
            total += points[index];
        }

        return total / count;
    }

    private static Rect ComputeBounds(Vector2[] points, int count)
    {
        Vector2 first = points[0];
        float minX = first.x;
        float maxX = first.x;
        float minY = first.y;
        float maxY = first.y;

        for (int index = 1; index < count; index++)
        {
            Vector2 point = points[index];
            minX = Mathf.Min(minX, point.x);
            maxX = Mathf.Max(maxX, point.x);
            minY = Mathf.Min(minY, point.y);
            maxY = Mathf.Max(maxY, point.y);
        }

        return Rect.MinMaxRect(minX, minY, maxX, maxY);
    }
}

public readonly struct MediaPipeLipRegion
{
    public MediaPipeLipRegion(
        Vector2[] outerPoints,
        Vector2[] innerCutoutPoints,
        Vector2 centroid,
        Rect bounds,
        float confidence)
    {
        OuterPoints = outerPoints;
        InnerCutoutPoints = innerCutoutPoints;
        Centroid = centroid;
        Bounds = bounds;
        Confidence = confidence;
    }

    public Vector2[] OuterPoints { get; }
    public Vector2[] InnerCutoutPoints { get; }
    public Vector2 Centroid { get; }
    public Rect Bounds { get; }
    public float Confidence { get; }
}

public readonly struct MediaPipeBrowRegion
{
    public MediaPipeBrowRegion(
        Vector2[] points,
        Vector2 centroid,
        Rect bounds,
        float confidence)
    {
        Points = points;
        Centroid = centroid;
        Bounds = bounds;
        Confidence = confidence;
    }

    public Vector2[] Points { get; }
    public Vector2 Centroid { get; }
    public Rect Bounds { get; }
    public float Confidence { get; }
}

public readonly struct MediaPipeBrowRegions
{
    public MediaPipeBrowRegions(MediaPipeBrowRegion left, MediaPipeBrowRegion right)
    {
        Left = left;
        Right = right;
    }

    public MediaPipeBrowRegion Left { get; }
    public MediaPipeBrowRegion Right { get; }
}

public readonly struct MediaPipeCheekRegion
{
    public MediaPipeCheekRegion(
        Vector2[] polygon,
        Vector2 centroid,
        Rect bounds,
        float confidence)
    {
        Polygon = polygon;
        Centroid = centroid;
        Bounds = bounds;
        Confidence = confidence;
    }

    public Vector2[] Polygon { get; }
    public Vector2 Centroid { get; }
    public Rect Bounds { get; }
    public float Confidence { get; }
}

public readonly struct MediaPipeCheekRegions
{
    public MediaPipeCheekRegions(MediaPipeCheekRegion left, MediaPipeCheekRegion right)
    {
        Left = left;
        Right = right;
    }

    public MediaPipeCheekRegion Left { get; }
    public MediaPipeCheekRegion Right { get; }
}
