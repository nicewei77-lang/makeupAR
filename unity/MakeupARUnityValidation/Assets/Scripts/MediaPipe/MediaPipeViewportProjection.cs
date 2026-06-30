using UnityEngine;

public static class MediaPipeViewportProjection
{
    public const string CoordinateMode = "mediapipe_oriented_aspect_fill_to_camera_viewport";

    public static Vector2 MapNormalizedImagePointToViewport(
        Vector2 normalizedPoint,
        MediaPipeFaceLandmarkPacket packet,
        Camera camera)
    {
        Vector2 viewportPoint = new Vector2(
            Mathf.Clamp01(normalizedPoint.x),
            Mathf.Clamp01(1.0f - normalizedPoint.y));
        if (packet == null || camera == null)
        {
            return viewportPoint;
        }

        ResolveOrientedImageSize(packet, out float imageWidth, out float imageHeight);
        if (imageWidth <= 0.0f || imageHeight <= 0.0f || camera.pixelHeight <= 0)
        {
            return viewportPoint;
        }

        float imageAspect = imageWidth / imageHeight;
        float viewportAspect = camera.pixelWidth / (float)camera.pixelHeight;
        if (imageAspect > viewportAspect)
        {
            float scaleX = imageAspect / viewportAspect;
            viewportPoint.x = ((viewportPoint.x - 0.5f) * scaleX) + 0.5f;
        }
        else if (imageAspect < viewportAspect)
        {
            float scaleY = viewportAspect / imageAspect;
            viewportPoint.y = ((viewportPoint.y - 0.5f) * scaleY) + 0.5f;
        }

        return ClampNormalized(viewportPoint);
    }

    public static Vector3 ProjectNormalizedImagePointToCameraLocal(
        Vector2 normalizedPoint,
        MediaPipeFaceLandmarkPacket packet,
        Camera camera,
        float depthMeters)
    {
        Vector2 viewportPoint = MapNormalizedImagePointToViewport(normalizedPoint, packet, camera);
        if (camera == null)
        {
            return new Vector3(viewportPoint.x - 0.5f, viewportPoint.y - 0.5f, 0.0f);
        }

        Vector3 worldPoint = camera.ViewportToWorldPoint(
            new Vector3(viewportPoint.x, viewportPoint.y, depthMeters));
        return camera.transform.InverseTransformPoint(worldPoint);
    }

    public static void ResolveOrientedImageSize(
        MediaPipeFaceLandmarkPacket packet,
        out float imageWidth,
        out float imageHeight)
    {
        imageWidth = packet != null ? packet.imageWidth : 0.0f;
        imageHeight = packet != null ? packet.imageHeight : 0.0f;
        int orientation = packet != null ? NormalizeDegrees(packet.selectedOrientationDegrees) : 0;
        if (orientation == 90 || orientation == 270)
        {
            float swappedWidth = imageHeight;
            imageHeight = imageWidth;
            imageWidth = swappedWidth;
        }
    }

    private static Vector2 ClampNormalized(Vector2 point)
    {
        return new Vector2(
            Mathf.Clamp01(point.x),
            Mathf.Clamp01(point.y));
    }

    private static int NormalizeDegrees(int degrees)
    {
        int normalized = degrees % 360;
        return normalized >= 0 ? normalized : normalized + 360;
    }
}
