using UnityEngine;

public static class MediaPipeLipRegionRenderer
{
    public const string Region = "lip";
    public const string Source = "mediapipe_lip_landmark_region_renderer";

    private static readonly Vector2[] OuterPoints =
        new Vector2[MediaPipeRegionSolver.LipOuterPointCount];
    private static readonly Vector2[] InnerCutoutPoints =
        new Vector2[MediaPipeRegionSolver.LipInnerCutoutPointCount];

    public static bool TryBuildGeometry(
        MediaPipeFaceLandmarkPacket packet,
        out MediaPipeRegionRenderGeometry geometry)
    {
        geometry = default;
        if (!MediaPipeRegionSolver.TrySolveLipRegionNonAlloc(
                packet,
                OuterPoints,
                InnerCutoutPoints,
                out MediaPipeLipRegion lip)
            || lip.OuterPoints == null
            || lip.InnerCutoutPoints == null
            || lip.OuterPoints.Length < 3
            || lip.InnerCutoutPoints.Length < 3)
        {
            return false;
        }

        geometry = new MediaPipeRegionRenderGeometry(
            Region,
            MediaPipeRegionRenderKind.Lip,
            lip.OuterPoints,
            lip.InnerCutoutPoints,
            lip.Centroid,
            lip.Bounds,
            lip.Confidence,
            Source);
        return true;
    }
}
