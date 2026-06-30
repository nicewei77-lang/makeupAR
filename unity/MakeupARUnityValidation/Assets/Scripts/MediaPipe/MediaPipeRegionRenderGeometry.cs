using UnityEngine;

public enum MediaPipeRegionRenderKind
{
    Lip,
    Brow,
    Cheek,
}

public readonly struct MediaPipeRegionRenderGeometry
{
    public MediaPipeRegionRenderGeometry(
        string region,
        MediaPipeRegionRenderKind kind,
        Vector2[] primaryPoints,
        Vector2[] secondaryPoints,
        Vector2 centroid,
        Rect bounds,
        float confidence,
        string source)
    {
        Region = region;
        Kind = kind;
        PrimaryPoints = primaryPoints;
        SecondaryPoints = secondaryPoints;
        Centroid = centroid;
        Bounds = bounds;
        Confidence = confidence;
        Source = source;
    }

    public string Region { get; }
    public MediaPipeRegionRenderKind Kind { get; }
    public Vector2[] PrimaryPoints { get; }
    public Vector2[] SecondaryPoints { get; }
    public Vector2 Centroid { get; }
    public Rect Bounds { get; }
    public float Confidence { get; }
    public string Source { get; }
    public int PrimaryPointCount => PrimaryPoints != null ? PrimaryPoints.Length : 0;
    public int SecondaryPointCount => SecondaryPoints != null ? SecondaryPoints.Length : 0;
    public bool HasPrimary => PrimaryPointCount >= 3;
    public bool HasSecondary => SecondaryPointCount >= 3;
}
