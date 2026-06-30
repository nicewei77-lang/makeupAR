using System.Collections.Generic;
using UnityEngine;

public static class MediaPipeCanonicalRegionMeshBuilder
{
    public const string MeshCullingMode = "mediapipe_canonical_full_face_triangle_gate";
    public const string TopologyAuditSummary =
        "mediapipe_canonical_face_model_v1_region_triangles_from_smoothed_landmarks";

    public static bool TryBuildRegionMesh(
        MediaPipeFaceLandmarkPacket packet,
        IList<Vector2> includePolygon,
        IList<Vector2> excludePolygon,
        Camera camera,
        float viewportDepthMeters,
        List<Vector3> vertices,
        List<Vector2> uvs,
        List<int> triangles,
        int[] canonicalToLocal,
        out MediaPipeCanonicalRegionMeshStats stats)
    {
        stats = default;
        if (!CanBuild(packet)
            || includePolygon == null
            || includePolygon.Count < 3
            || vertices == null
            || uvs == null
            || triangles == null
            || canonicalToLocal == null
            || canonicalToLocal.Length < MediaPipeCanonicalFaceMesh.VertexCount)
        {
            return false;
        }

        vertices.Clear();
        uvs.Clear();
        triangles.Clear();
        for (int index = 0; index < MediaPipeCanonicalFaceMesh.VertexCount; index++)
        {
            canonicalToLocal[index] = -1;
        }

        int[] sourceTriangles = MediaPipeCanonicalFaceMesh.TriangleIndices;
        int acceptedTriangleCount = 0;
        for (int index = 0; index < sourceTriangles.Length; index += 3)
        {
            int a = sourceTriangles[index];
            int b = sourceTriangles[index + 1];
            int c = sourceTriangles[index + 2];
            Vector2 centroid = (LandmarkPoint(packet, a)
                + LandmarkPoint(packet, b)
                + LandmarkPoint(packet, c)) / 3.0f;

            if (!ContainsPoint(includePolygon, centroid))
            {
                continue;
            }

            if (excludePolygon != null
                && excludePolygon.Count >= 3
                && ContainsPoint(excludePolygon, centroid))
            {
                continue;
            }

            triangles.Add(AddVertex(packet, a, camera, viewportDepthMeters, vertices, uvs, canonicalToLocal));
            triangles.Add(AddVertex(packet, b, camera, viewportDepthMeters, vertices, uvs, canonicalToLocal));
            triangles.Add(AddVertex(packet, c, camera, viewportDepthMeters, vertices, uvs, canonicalToLocal));
            acceptedTriangleCount++;
        }

        stats = new MediaPipeCanonicalRegionMeshStats(
            MediaPipeCanonicalFaceMesh.TriangleCount,
            acceptedTriangleCount,
            MediaPipeCanonicalFaceMesh.TriangleCount - acceptedTriangleCount,
            vertices.Count,
            triangles.Count,
            MeshCullingMode,
            TopologyAuditSummary);
        return acceptedTriangleCount > 0;
    }

    private static bool CanBuild(MediaPipeFaceLandmarkPacket packet)
    {
        return packet != null
            && MediaPipeCanonicalFaceMesh.CanBuildFromLandmarkCount(packet.landmarkCount)
            && packet.landmarks != null
            && packet.landmarks.Length >= MediaPipeCanonicalFaceMesh.VertexCount;
    }

    private static int AddVertex(
        MediaPipeFaceLandmarkPacket packet,
        int canonicalIndex,
        Camera camera,
        float viewportDepthMeters,
        List<Vector3> vertices,
        List<Vector2> uvs,
        int[] canonicalToLocal)
    {
        int localIndex = canonicalToLocal[canonicalIndex];
        if (localIndex >= 0)
        {
            return localIndex;
        }

        Vector2 normalizedPoint = LandmarkPoint(packet, canonicalIndex);
        vertices.Add(
            MediaPipeViewportProjection.ProjectNormalizedImagePointToCameraLocal(
                normalizedPoint,
                packet,
                camera,
                viewportDepthMeters));
        uvs.Add(MediaPipeCanonicalFaceMesh.Uvs[canonicalIndex]);
        localIndex = vertices.Count - 1;
        canonicalToLocal[canonicalIndex] = localIndex;
        return localIndex;
    }

    private static Vector2 LandmarkPoint(MediaPipeFaceLandmarkPacket packet, int canonicalIndex)
    {
        MediaPipeFaceLandmark landmark = packet.landmarks[canonicalIndex];
        return new Vector2(landmark.x, landmark.y);
    }

    private static bool ContainsPoint(IList<Vector2> polygon, Vector2 point)
    {
        bool inside = false;
        int previous = polygon.Count - 1;
        for (int current = 0; current < polygon.Count; current++)
        {
            Vector2 a = polygon[current];
            Vector2 b = polygon[previous];
            bool crosses = (a.y > point.y) != (b.y > point.y);
            if (crosses)
            {
                float denominator = b.y - a.y;
                if (Mathf.Abs(denominator) > 0.000001f)
                {
                    float xAtY = ((b.x - a.x) * (point.y - a.y) / denominator) + a.x;
                    if (point.x < xAtY)
                    {
                        inside = !inside;
                    }
                }
            }

            previous = current;
        }

        return inside;
    }
}

public readonly struct MediaPipeCanonicalRegionMeshStats
{
    public MediaPipeCanonicalRegionMeshStats(
        int sourceTriangleCount,
        int acceptedTriangleCount,
        int culledTriangleCount,
        int vertexCount,
        int indexCount,
        string meshCullingMode,
        string topologyAuditSummary)
    {
        SourceTriangleCount = sourceTriangleCount;
        AcceptedTriangleCount = acceptedTriangleCount;
        CulledTriangleCount = culledTriangleCount;
        VertexCount = vertexCount;
        IndexCount = indexCount;
        MeshCullingMode = meshCullingMode;
        TopologyAuditSummary = topologyAuditSummary;
    }

    public int SourceTriangleCount { get; }
    public int AcceptedTriangleCount { get; }
    public int CulledTriangleCount { get; }
    public int VertexCount { get; }
    public int IndexCount { get; }
    public string MeshCullingMode { get; }
    public string TopologyAuditSummary { get; }
}
