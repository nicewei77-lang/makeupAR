using UnityEngine;

public static class MediaPipeCheekRegionRenderer
{
    public const string Region = "cheek";
    public const string Source = "mediapipe_cheek_landmark_region_renderer";

    private static readonly Vector2[] LeftPoints =
        new Vector2[MediaPipeRegionSolver.CheekPointCount];
    private static readonly Vector2[] RightPoints =
        new Vector2[MediaPipeRegionSolver.CheekPointCount];

    public static bool TryBuildGeometry(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeRegionRenderGeometry geometry)
    {
        geometry = default;
        if (!MediaPipeRegionSolver.TrySolveCheekRegionsNonAlloc(
                packet,
                LeftPoints,
                RightPoints,
                out MediaPipeCheekRegions cheeks)
            || cheeks.Left.Polygon == null
            || cheeks.Right.Polygon == null
            || cheeks.Left.Polygon.Length < 3
            || cheeks.Right.Polygon.Length < 3)
        {
            return false;
        }

        geometry = new MediaPipeRegionRenderGeometry(
            Region,
            MediaPipeRegionRenderKind.Cheek,
            cheeks.Left.Polygon,
            cheeks.Right.Polygon,
            Midpoint(cheeks.Left.Centroid, cheeks.Right.Centroid),
            UnionBounds(cheeks.Left.Bounds, cheeks.Right.Bounds),
            Mathf.Min(cheeks.Left.Confidence, cheeks.Right.Confidence),
            Source);
        return true;
    }

    private static Vector2 Midpoint(Vector2 left, Vector2 right)
    {
        return (left + right) * 0.5f;
    }

    private static Rect UnionBounds(Rect left, Rect right)
    {
        return Rect.MinMaxRect(
            Mathf.Min(left.xMin, right.xMin),
            Mathf.Min(left.yMin, right.yMin),
            Mathf.Max(left.xMax, right.xMax),
            Mathf.Max(left.yMax, right.yMax));
    }
}
