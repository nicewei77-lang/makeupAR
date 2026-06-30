using UnityEngine;

public static class MediaPipeBrowRegionRenderer
{
    public const string Region = "brow";
    public const string Source = "mediapipe_brow_landmark_region_renderer";

    private static readonly Vector2[] LeftPoints =
        new Vector2[MediaPipeRegionSolver.BrowPointCount];
    private static readonly Vector2[] RightPoints =
        new Vector2[MediaPipeRegionSolver.BrowPointCount];

    public static bool TryBuildGeometry(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeRegionRenderGeometry geometry)
    {
        geometry = default;
        if (!MediaPipeRegionSolver.TrySolveBrowRegionsNonAlloc(
                packet,
                LeftPoints,
                RightPoints,
                out MediaPipeBrowRegions brows)
            || brows.Left.Points == null
            || brows.Right.Points == null
            || brows.Left.Points.Length < 3
            || brows.Right.Points.Length < 3)
        {
            return false;
        }

        geometry = new MediaPipeRegionRenderGeometry(
            Region,
            MediaPipeRegionRenderKind.Brow,
            brows.Left.Points,
            brows.Right.Points,
            Midpoint(brows.Left.Centroid, brows.Right.Centroid),
            UnionBounds(brows.Left.Bounds, brows.Right.Bounds),
            Mathf.Min(brows.Left.Confidence, brows.Right.Confidence),
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
