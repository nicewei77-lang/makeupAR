using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

public sealed class MediaPipeFullFaceMeshRenderer : MonoBehaviour
{
    public const string RendererId = "mediapipe-full-face-mesh-renderer";
    public const string TopologyStatus = MediaPipeCanonicalFaceMesh.TopologyId;
    private const float ViewportDepthMeters = 0.35f;

    [SerializeField] private E7MediaPipeFullFaceRuntime mediaPipeRuntime;
    [SerializeField] private Camera targetCamera;
    [SerializeField] private bool renderVisible;

    private readonly List<Vector3> vertices = new List<Vector3>(MediaPipeFaceLandmarkPacket.MinimumLandmarkCount);
    private readonly List<Vector2> uvs = new List<Vector2>(MediaPipeFaceLandmarkPacket.MinimumLandmarkCount);
    private readonly List<int> triangleIndices = new List<int>(MediaPipeCanonicalFaceMesh.TriangleCount * 3);
    private Mesh mesh;
    private MeshRenderer meshRenderer;
    private MeshFilter meshFilter;
    private Material material;
    private MediaPipeFullFaceMeshStatus latestStatus;

    public void Configure(E7MediaPipeFullFaceRuntime runtime, Camera overlayCamera)
    {
        if (mediaPipeRuntime == null)
        {
            mediaPipeRuntime = runtime;
        }

        if (targetCamera == null)
        {
            targetCamera = overlayCamera != null ? overlayCamera : Camera.main;
        }
    }

    public bool TryUpdateFromLatestPacket(out MediaPipeFullFaceMeshStatus status)
    {
        RefreshReferences();
        if (mediaPipeRuntime == null
            || !mediaPipeRuntime.TryGetLatestSmoothedPacket(
                out MediaPipeFaceLandmarkPacket packet,
                out MediaPipeFaceFrameSmoothingStatus smoothingStatus))
        {
            status = new MediaPipeFullFaceMeshStatus(
                false,
                false,
                0,
                0,
                0,
                0,
                "None",
                TopologyStatus,
                0);
            latestStatus = status;
            SetVisible(false);
            return false;
        }

        if (!CanBuildCanonicalMesh(packet))
        {
            status = BuildUnavailableStatus(packet.landmarkCount, "InsufficientLandmarks");
            latestStatus = status;
            SetVisible(false);
            return false;
        }

        EnsureMeshObjects();
        BuildCanonicalTopologyMesh(packet);
        SetVisible(renderVisible);
        status = new MediaPipeFullFaceMeshStatus(
            true,
            true,
            packet.landmarkCount,
            vertices.Count,
            triangleIndices.Count,
            MediaPipeCanonicalFaceMesh.TriangleCount,
            smoothingStatus.Stale ? "Stale" : "Tracking",
            TopologyStatus,
            smoothingStatus.PacketAgeMs);
        latestStatus = status;
        return true;
    }

    public bool TryRefreshStatusFromLatestPacket(out MediaPipeFullFaceMeshStatus status)
    {
        RefreshReferences();
        if (mediaPipeRuntime == null
            || !mediaPipeRuntime.TryGetLatestSmoothedPacket(
                out MediaPipeFaceLandmarkPacket packet,
                out MediaPipeFaceFrameSmoothingStatus smoothingStatus))
        {
            status = new MediaPipeFullFaceMeshStatus(
                false,
                false,
                0,
                0,
                0,
                0,
                "None",
                TopologyStatus,
                0);
            latestStatus = status;
            SetVisible(false);
            return false;
        }

        bool canBuildMesh = CanBuildCanonicalMesh(packet);
        int vertexCount = canBuildMesh ? MediaPipeCanonicalFaceMesh.VertexCount : 0;
        int indexCount = vertexCount > 0 ? MediaPipeCanonicalFaceMesh.TriangleIndices.Length : 0;
        int triangleCount = vertexCount > 0 ? MediaPipeCanonicalFaceMesh.TriangleCount : 0;
        bool applied = false;
        if (renderVisible && canBuildMesh)
        {
            EnsureMeshObjects();
            BuildCanonicalTopologyMesh(packet);
            SetVisible(true);
            vertexCount = vertices.Count;
            indexCount = triangleIndices.Count;
            triangleCount = indexCount / 3;
            applied = true;
        }
        else
        {
            SetVisible(false);
        }

        status = new MediaPipeFullFaceMeshStatus(
            true,
            applied,
            packet.landmarkCount,
            vertexCount,
            indexCount,
            triangleCount,
            smoothingStatus.Stale ? "Stale" : "Tracking",
            TopologyStatus,
            smoothingStatus.PacketAgeMs);
        latestStatus = status;
        return true;
    }

    private static bool CanBuildCanonicalMesh(MediaPipeFaceLandmarkPacket packet)
    {
        return packet != null
            && MediaPipeCanonicalFaceMesh.CanBuildFromLandmarkCount(packet.landmarkCount)
            && packet.landmarks != null
            && packet.landmarks.Length >= MediaPipeCanonicalFaceMesh.VertexCount;
    }

    private static MediaPipeFullFaceMeshStatus BuildUnavailableStatus(
        int landmarkCount,
        string trackingState)
    {
        return new MediaPipeFullFaceMeshStatus(
            false,
            false,
            landmarkCount,
            0,
            0,
            0,
            trackingState,
            TopologyStatus,
            0);
    }

    public bool TryGetLatestStatus(out MediaPipeFullFaceMeshStatus status)
    {
        status = latestStatus;
        return latestStatus.HasPacket;
    }

    public void SetRenderVisible(bool visible)
    {
        renderVisible = visible;
        SetVisible(visible);
    }

    private void BuildCanonicalTopologyMesh(MediaPipeFaceLandmarkPacket packet)
    {
        vertices.Clear();
        uvs.Clear();
        triangleIndices.Clear();

        int count = Mathf.Min(
            MediaPipeCanonicalFaceMesh.VertexCount,
            Mathf.Min(packet.landmarks.Length, packet.landmarkCount));
        for (int index = 0; index < count; index++)
        {
            MediaPipeFaceLandmark landmark = packet.landmarks[index];
            Vector2 normalizedPoint = new Vector2(landmark.x, landmark.y);
            vertices.Add(
                MediaPipeViewportProjection.ProjectNormalizedImagePointToCameraLocal(
                    normalizedPoint,
                    packet,
                    ResolveOverlayCamera(),
                    ViewportDepthMeters));
            uvs.Add(MediaPipeCanonicalFaceMesh.Uvs[index]);
        }

        triangleIndices.AddRange(MediaPipeCanonicalFaceMesh.TriangleIndices);

        mesh.Clear();
        mesh.SetVertices(vertices);
        mesh.SetUVs(0, uvs);
        mesh.SetTriangles(triangleIndices, 0);
        mesh.RecalculateBounds();
    }

    private void EnsureMeshObjects()
    {
        if (mesh != null)
        {
            ReparentToCamera();
            return;
        }

        mesh = new Mesh
        {
            name = "MediaPipe Canonical Full Face Mesh",
        };
        mesh.MarkDynamic();
        meshFilter = gameObject.AddComponent<MeshFilter>();
        meshRenderer = gameObject.AddComponent<MeshRenderer>();
        meshFilter.sharedMesh = mesh;
        material = CreateMaterial();
        meshRenderer.sharedMaterial = material;
        meshRenderer.shadowCastingMode = ShadowCastingMode.Off;
        meshRenderer.receiveShadows = false;
        meshRenderer.sortingOrder = 190;
        ReparentToCamera();
        SetVisible(renderVisible);
    }

    private void ReparentToCamera()
    {
        Camera camera = ResolveOverlayCamera();
        if (camera == null)
        {
            return;
        }

        Transform parent = camera.transform;
        if (transform.parent != parent)
        {
            transform.SetParent(parent, false);
        }

        transform.localPosition = Vector3.zero;
        transform.localRotation = Quaternion.identity;
        transform.localScale = Vector3.one;
    }

    private void SetVisible(bool visible)
    {
        if (meshRenderer != null)
        {
            meshRenderer.enabled = visible;
        }
    }

    private void RefreshReferences()
    {
        if (mediaPipeRuntime == null)
        {
            mediaPipeRuntime = FindFirstObjectByType<E7MediaPipeFullFaceRuntime>();
        }

        ResolveOverlayCamera();
    }

    private Camera ResolveOverlayCamera()
    {
        if (targetCamera == null)
        {
            targetCamera = Camera.main;
        }

        return targetCamera;
    }

    private static Material CreateMaterial()
    {
        Shader shader = Shader.Find("Sprites/Default");
        if (shader == null)
        {
            shader = Shader.Find("Unlit/Color");
        }

        Material meshMaterial = new Material(shader)
        {
            name = "MediaPipe Canonical Full Face Mesh Material",
            renderQueue = (int)RenderQueue.Transparent + 20,
        };
        if (meshMaterial.HasProperty("_Color"))
        {
            meshMaterial.SetColor("_Color", new Color(0.25f, 0.9f, 0.6f, 0.35f));
        }

        return meshMaterial;
    }
}

public readonly struct MediaPipeFullFaceMeshStatus
{
    public MediaPipeFullFaceMeshStatus(
        bool hasPacket,
        bool applied,
        int landmarkCount,
        int vertexCount,
        int indexCount,
        int triangleCount,
        string trackingState,
        string topologyStatus,
        long packetAgeMs)
    {
        HasPacket = hasPacket;
        Applied = applied;
        LandmarkCount = landmarkCount;
        VertexCount = vertexCount;
        IndexCount = indexCount;
        TriangleCount = triangleCount;
        TrackingState = trackingState;
        TopologyStatus = topologyStatus;
        PacketAgeMs = packetAgeMs;
    }

    public bool HasPacket { get; }
    public bool Applied { get; }
    public int LandmarkCount { get; }
    public int VertexCount { get; }
    public int IndexCount { get; }
    public int TriangleCount { get; }
    public string TrackingState { get; }
    public string TopologyStatus { get; }
    public long PacketAgeMs { get; }
}
