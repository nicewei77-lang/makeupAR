using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Rendering;

public sealed class MediaPipeRegionOverlayRenderer : MonoBehaviour
{
    private const string RendererMode = MakeupRegionRendererRoutes.MediaPipeRegionOverlayMode;
    private const string MaskSource = "mediapipe_full_face_landmarks";
    private const string BoundaryRenderer = "mediapipe_canonical_full_face_mesh_region_gate";
    private const string CoordinateMode = MediaPipeViewportProjection.CoordinateMode;
    private const string RuntimeTextureOverrideStatusOff = "off";
    private const string RuntimeTextureOverrideStatusUnsupported = "unsupported_in_mediapipe_overlay";
    private const float ViewportDepthMeters = 0.35f;
    private const float DefaultCoveragePivot = 0.62f;
    private const long MaxStaleHoldAgeMs = 900;
    private const int RegionPartCount = 2;

    private static readonly string[] RenderRegions = { "lip", "cheek", "brow" };

    [SerializeField] private E7MediaPipeFullFaceRuntime mediaPipeRuntime;
    [SerializeField] private Camera targetCamera;

    private readonly Dictionary<string, RegionRecipeState> recipes =
        new Dictionary<string, RegionRecipeState>();
    private readonly Dictionary<string, E3RegionMaskOverlay.RegionApplyResult> latestRegionResults =
        new Dictionary<string, E3RegionMaskOverlay.RegionApplyResult>();
    private readonly Dictionary<string, RegionOverlayPart[]> regionParts =
        new Dictionary<string, RegionOverlayPart[]>();
    private readonly List<Vector3> scratchVertices = new List<Vector3>(64);
    private readonly List<Vector2> scratchUvs = new List<Vector2>(64);
    private readonly List<int> scratchTriangles = new List<int>(192);
    private readonly List<Vector2> scratchPrimaryPolygon = new List<Vector2>(32);
    private readonly List<Vector2> scratchSecondaryPolygon = new List<Vector2>(32);
    private readonly int[] scratchCanonicalToLocal = new int[MediaPipeCanonicalFaceMesh.VertexCount];

    private bool overlaySuppressed;

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

    public void SetOverlayRenderingSuppressed(bool suppressed)
    {
        overlaySuppressed = suppressed;
        if (overlaySuppressed)
        {
            HideAllRegionViews();
        }
    }

    public void ClearRecipesAndHideOverlays()
    {
        recipes.Clear();
        latestRegionResults.Clear();
        HideAllRegionViews();
    }

    public bool TryGetLatestRegionApplyResult(
        string region,
        out E3RegionMaskOverlay.RegionApplyResult result)
    {
        region = NormalizeRegion(region);
        return latestRegionResults.TryGetValue(region, out result);
    }

    public E3RegionMaskOverlay.RegionApplyResult ApplyRegionRecipe(
        string region,
        string colorHex,
        Color color,
        float opacity,
        bool enabled,
        string textureSample,
        string textureMode,
        float intensity,
        float feather,
        string blendMode,
        string rendererMode,
        string maskTextureId,
        string runtimeTextureOverrideMode,
        string runtimeTextureOverridePath,
        string secondaryColorHex,
        Color secondaryColor,
        float coverage,
        float maskSpreadX,
        float maskOffsetY,
        float browGap,
        float browAngle,
        float browArch,
        float browArchPosition,
        bool browCleanupEnabled,
        float browCleanupStrength,
        float browReshapeStrength,
        string browCleanupSourceMode,
        string finish,
        float roughness,
        float specular,
        float specularPower,
        float glossBoost,
        float gradientAmount,
        float detailAmount,
        bool preserveDetail)
    {
        region = NormalizeRegion(region);
        string normalizedRendererMode = MakeupRegionRendererRoutes.NormalizeRendererMode(
            rendererMode,
            rendererMode,
            region);
        if (normalizedRendererMode != RendererMode)
        {
            throw new ArgumentException(
                "MediaPipe region overlay received a non-MediaPipe renderer mode for "
                + region
                + ": "
                + normalizedRendererMode);
        }

        bool isBrow = region == "brow";
        float normalizedMaskSpread = Mathf.Clamp(maskSpreadX, -0.34f, 0.34f);
        float normalizedBrowGap = isBrow
            ? Mathf.Clamp(Mathf.Abs(browGap) > 0.0001f ? browGap : normalizedMaskSpread, -0.34f, 0.34f)
            : 0.0f;

        recipes[region] = new RegionRecipeState
        {
            Region = region,
            ColorHex = NormalizeOptional(colorHex, "#D94B74"),
            Color = new Color(color.r, color.g, color.b, Mathf.Clamp01(opacity)),
            Opacity = Mathf.Clamp01(opacity),
            Enabled = enabled,
            TextureSample = NormalizeOptional(textureSample, region + "_mediapipe_region"),
            TextureMode = NormalizeOptional(textureMode, "sample"),
            Intensity = Mathf.Clamp01(intensity),
            Feather = Mathf.Clamp01(feather),
            BlendMode = NormalizeBlendMode(blendMode),
            MaskTextureId = NormalizeOptional(maskTextureId, region + "-mediapipe-region-v1"),
            RuntimeTextureOverrideMode = NormalizeOptional(runtimeTextureOverrideMode, "off"),
            RuntimeTextureOverridePath = string.IsNullOrWhiteSpace(runtimeTextureOverridePath)
                ? string.Empty
                : runtimeTextureOverridePath.Trim(),
            SecondaryColorHex = NormalizeOptional(secondaryColorHex, "#F29BAA"),
            SecondaryColor = secondaryColor,
            Coverage = Mathf.Clamp01(coverage),
            MaskSpreadX = isBrow ? normalizedBrowGap : normalizedMaskSpread,
            MaskOffsetY = Mathf.Clamp(maskOffsetY, -0.08f, 0.08f),
            BrowGap = normalizedBrowGap,
            BrowAngle = isBrow ? Mathf.Clamp(browAngle, -0.16f, 0.16f) : 0.0f,
            BrowArch = isBrow ? Mathf.Clamp(browArch, -0.05f, 0.05f) : 0.0f,
            BrowArchPosition = isBrow ? Mathf.Clamp(browArchPosition, -0.15f, 0.15f) : 0.0f,
            BrowCleanupEnabled = isBrow && browCleanupEnabled,
            BrowCleanupStrength = isBrow && browCleanupEnabled ? Mathf.Clamp01(browCleanupStrength) : 0.0f,
            BrowReshapeStrength = isBrow ? Mathf.Clamp01(browReshapeStrength) : 0.0f,
            BrowCleanupSourceMode = isBrow && browCleanupEnabled
                ? NormalizeOptional(browCleanupSourceMode, "grabpass")
                : "none",
            Finish = NormalizeOptional(finish, "natural"),
            Roughness = Mathf.Clamp01(roughness),
            Specular = Mathf.Clamp01(specular),
            SpecularPower = Mathf.Max(1.0f, specularPower),
            GlossBoost = Mathf.Clamp01(glossBoost),
            GradientAmount = Mathf.Clamp01(gradientAmount),
            DetailAmount = Mathf.Clamp01(detailAmount),
            PreserveDetail = preserveDetail,
        };

        return ApplyRegionToLatestPacket(region, true);
    }

    private void LateUpdate()
    {
        for (int index = 0; index < RenderRegions.Length; index++)
        {
            string region = RenderRegions[index];
            if (recipes.ContainsKey(region))
            {
                ApplyRegionToLatestPacket(region, false);
            }
        }
    }

    private E3RegionMaskOverlay.RegionApplyResult ApplyRegionToLatestPacket(string region, bool emitLog)
    {
        RefreshReferences();
        E3RegionMaskOverlay.RegionApplyResult result = CreateResult(region);
        if (!recipes.TryGetValue(region, out RegionRecipeState recipe))
        {
            latestRegionResults[region] = result;
            return result;
        }

        ApplyRecipeToResult(recipe, ref result);

        if (!recipe.Enabled)
        {
            result.StateAction = "disabled";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            MaybeLogApplyResult(result, emitLog);
            return result;
        }

        if (overlaySuppressed)
        {
            result.StateAction = "suppressed";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            MaybeLogApplyResult(result, emitLog);
            return result;
        }

        if (mediaPipeRuntime == null)
        {
            result.StateAction = "mediapipe_runtime_missing";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            MaybeLogApplyResult(result, emitLog);
            return result;
        }

        bool hasPacket = mediaPipeRuntime.TryGetLatestSmoothedPacket(
            out MediaPipeFaceLandmarkPacket packet,
            out MediaPipeFaceFrameSmoothingStatus status);
        ApplyPacketStatus(ref result, packet, status, hasPacket);
        if (!hasPacket)
        {
            result.StateAction = "mediapipe_waiting_for_face";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            MaybeLogApplyResult(result, emitLog);
            return result;
        }

        if (status.Stale && status.PacketAgeMs > MaxStaleHoldAgeMs)
        {
            result.FaceCount = 0;
            result.TrackingState = "StaleExpired";
            result.StateAction = "mediapipe_stale_expired_waiting_for_face";
            result.VisionBoundaryStatus = "stale_expired";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            MaybeLogApplyResult(result, emitLog);
            return result;
        }

        bool applied = false;
        if (region == "lip")
        {
            applied = MediaPipeLipRegionRenderer.TryBuildGeometry(packet, out MediaPipeRegionRenderGeometry lip)
                && ApplyLipRegion(recipe, packet, lip, ref result);
        }
        else if (region == "cheek")
        {
            applied = MediaPipeCheekRegionRenderer.TryBuildGeometry(packet, out MediaPipeRegionRenderGeometry cheeks)
                && ApplyPairedRegion(recipe, packet, cheeks, ref result);
        }
        else if (region == "brow")
        {
            applied = MediaPipeBrowRegionRenderer.TryBuildGeometry(packet, out MediaPipeRegionRenderGeometry brows)
                && ApplyPairedRegion(recipe, packet, brows, ref result);
        }

        if (!applied)
        {
            result.StateAction = "mediapipe_region_solve_failed";
            HideRegionViews(region);
        }

        result.Applied = applied;
        latestRegionResults[region] = result;
        MaybeLogApplyResult(result, emitLog);
        return result;
    }

    private bool ApplyLipRegion(
        RegionRecipeState recipe,
        MediaPipeFaceLandmarkPacket packet,
        MediaPipeRegionRenderGeometry lip,
        ref E3RegionMaskOverlay.RegionApplyResult result)
    {
        RegionOverlayPart part = EnsureRegionPart(recipe.Region, 0, "single");
        HideUnusedParts(recipe.Region, 1);
        if (!BuildLipMesh(part, recipe, packet, lip))
        {
            SetPartVisible(part, false);
            return false;
        }

        ApplyPartAppearance(part, recipe, result.TrackingState == "Stale");
        SetPartVisible(part, true);
        result.VisionBoundaryOuterPointCount = lip.PrimaryPointCount;
        result.VisionBoundaryInnerPointCount = lip.SecondaryPointCount;
        result.MeshVertexCount = part.VertexCount;
        result.MeshIndexCount = part.IndexCount;
        result.MeshUvCount = part.UvCount;
        result.MeshTriangleCount = result.MeshIndexCount / 3;
        result.MaskTriangleCount = result.MeshTriangleCount;
        result.SourceTriangleCount = MediaPipeCanonicalFaceMesh.TriangleCount;
        result.CulledTriangleCount = Mathf.Max(0, result.SourceTriangleCount - result.MeshTriangleCount);
        result.MeshCullingMode = MediaPipeCanonicalRegionMeshBuilder.MeshCullingMode;
        result.UvAvailable = true;
        result.TopologyAuditStatus = MediaPipeCanonicalFaceMesh.TopologyId;
        result.TopologyAuditSummary = MediaPipeCanonicalRegionMeshBuilder.TopologyAuditSummary;
        result.StateAction = result.TrackingState == "Stale"
            ? "mediapipe_region_stale_hold"
            : "mediapipe_region_rendered";
        return true;
    }

    private bool ApplyPairedRegion(
        RegionRecipeState recipe,
        MediaPipeFaceLandmarkPacket packet,
        MediaPipeRegionRenderGeometry geometry,
        ref E3RegionMaskOverlay.RegionApplyResult result)
    {
        bool leftApplied = ApplyPolygonPart(recipe, packet, geometry.PrimaryPoints, 0, "left", result.TrackingState == "Stale");
        bool rightApplied = ApplyPolygonPart(recipe, packet, geometry.SecondaryPoints, 1, "right", result.TrackingState == "Stale");
        ApplyPartCounts(recipe.Region, ref result);
        result.VisionBoundaryOuterPointCount = geometry.PrimaryPointCount + geometry.SecondaryPointCount;
        result.SourceTriangleCount = MediaPipeCanonicalFaceMesh.TriangleCount;
        result.CulledTriangleCount = Mathf.Max(0, result.SourceTriangleCount - result.MeshTriangleCount);
        result.MeshCullingMode = MediaPipeCanonicalRegionMeshBuilder.MeshCullingMode;
        result.UvAvailable = result.MeshTriangleCount > 0;
        result.TopologyAuditStatus = MediaPipeCanonicalFaceMesh.TopologyId;
        result.TopologyAuditSummary = MediaPipeCanonicalRegionMeshBuilder.TopologyAuditSummary;
        result.StateAction = leftApplied || rightApplied
            ? result.TrackingState == "Stale"
                ? "mediapipe_region_stale_hold"
                : "mediapipe_region_rendered"
            : "mediapipe_region_solve_failed";
        return leftApplied || rightApplied;
    }

    private bool ApplyPolygonPart(
        RegionRecipeState recipe,
        MediaPipeFaceLandmarkPacket packet,
        Vector2[] points,
        int partIndex,
        string partName,
        bool stale)
    {
        RegionOverlayPart part = EnsureRegionPart(recipe.Region, partIndex, partName);
        if (!BuildCanonicalPolygonMesh(part, recipe, packet, points))
        {
            SetPartVisible(part, false);
            return false;
        }

        ApplyPartAppearance(part, recipe, stale);
        SetPartVisible(part, true);
        return true;
    }

    private bool BuildLipMesh(
        RegionOverlayPart part,
        RegionRecipeState recipe,
        MediaPipeFaceLandmarkPacket packet,
        MediaPipeRegionRenderGeometry lip)
    {
        Vector2[] outer = lip.PrimaryPoints;
        Vector2[] inner = lip.SecondaryPoints;
        if (outer == null || inner == null || outer.Length < 3 || inner.Length < 3)
        {
            return false;
        }

        BuildTunedPolygon(outer, lip.Centroid, recipe, scratchPrimaryPolygon);
        BuildTunedPolygon(inner, lip.Centroid, recipe, scratchSecondaryPolygon);
        if (!MediaPipeCanonicalRegionMeshBuilder.TryBuildRegionMesh(
                packet,
                scratchPrimaryPolygon,
                scratchSecondaryPolygon,
                ResolveOverlayCamera(),
                ViewportDepthMeters,
                scratchVertices,
                scratchUvs,
                scratchTriangles,
                scratchCanonicalToLocal,
                out MediaPipeCanonicalRegionMeshStats stats))
        {
            return false;
        }

        ApplyMesh(part, scratchVertices, scratchUvs, scratchTriangles, stats);
        return stats.AcceptedTriangleCount > 0;
    }

    private bool BuildCanonicalPolygonMesh(
        RegionOverlayPart part,
        RegionRecipeState recipe,
        MediaPipeFaceLandmarkPacket packet,
        Vector2[] points)
    {
        if (points == null || points.Length < 3)
        {
            return false;
        }

        Vector2 centroid = ComputeCentroid(points);
        BuildTunedPolygon(points, centroid, recipe, scratchPrimaryPolygon);
        SortPolygonByAngle(scratchPrimaryPolygon, ComputeCentroid(scratchPrimaryPolygon));
        if (!MediaPipeCanonicalRegionMeshBuilder.TryBuildRegionMesh(
                packet,
                scratchPrimaryPolygon,
                null,
                ResolveOverlayCamera(),
                ViewportDepthMeters,
                scratchVertices,
                scratchUvs,
                scratchTriangles,
                scratchCanonicalToLocal,
                out MediaPipeCanonicalRegionMeshStats stats))
        {
            return false;
        }

        ApplyMesh(part, scratchVertices, scratchUvs, scratchTriangles, stats);
        return stats.AcceptedTriangleCount > 0;
    }

    private void BuildTunedPolygon(
        Vector2[] points,
        Vector2 centroid,
        RegionRecipeState recipe,
        List<Vector2> output)
    {
        output.Clear();
        for (int index = 0; index < points.Length; index++)
        {
            output.Add(ApplyCanonicalGateTuning(points[index], centroid, recipe));
        }
    }

    private void ApplyMesh(
        RegionOverlayPart part,
        List<Vector3> vertices,
        List<Vector2> uvs,
        List<int> triangles,
        MediaPipeCanonicalRegionMeshStats stats)
    {
        part.Mesh.Clear();
        part.Mesh.SetVertices(vertices);
        part.Mesh.SetUVs(0, uvs);
        part.Mesh.SetTriangles(triangles, 0);
        part.Mesh.RecalculateBounds();
        part.VertexCount = vertices.Count;
        part.UvCount = uvs.Count;
        part.IndexCount = triangles.Count;
        part.SourceTriangleCount = stats.SourceTriangleCount;
        part.CulledTriangleCount = stats.CulledTriangleCount;
    }

    private Vector2 ApplyCanonicalGateTuning(
        Vector2 point,
        Vector2 centroid,
        RegionRecipeState recipe)
    {
        float coverageScale = 1.0f + ((Mathf.Clamp01(recipe.Coverage) - DefaultCoveragePivot) * 0.24f);
        Vector2 relative = point - centroid;
        relative.x *= Mathf.Max(0.35f, coverageScale + recipe.MaskSpreadX);
        relative.y *= Mathf.Max(0.35f, coverageScale + (recipe.Region == "brow" ? recipe.BrowArch : 0.0f));

        Vector2 tuned = centroid + relative;
        tuned.y += recipe.MaskOffsetY;
        if (recipe.Region == "brow")
        {
            tuned.y -= recipe.BrowGap * 0.25f;
            tuned.x += relative.y * recipe.BrowAngle;
        }

        return ClampNormalized(tuned);
    }

    private RegionOverlayPart EnsureRegionPart(string region, int index, string partName)
    {
        if (!regionParts.TryGetValue(region, out RegionOverlayPart[] parts))
        {
            parts = new RegionOverlayPart[RegionPartCount];
            regionParts[region] = parts;
        }

        if (parts[index] != null)
        {
            ReparentPartToCamera(parts[index]);
            return parts[index];
        }

        var container = new GameObject("MediaPipe Region " + region + " " + partName);
        var meshFilter = container.AddComponent<MeshFilter>();
        var meshRenderer = container.AddComponent<MeshRenderer>();
        var mesh = new Mesh
        {
            name = "MediaPipe Region " + region + " " + partName + " Mesh"
        };
        mesh.MarkDynamic();
        meshFilter.sharedMesh = mesh;

        var part = new RegionOverlayPart
        {
            Container = container,
            Mesh = mesh,
            MeshRenderer = meshRenderer,
            Material = CreateOverlayMaterial(region, partName),
        };
        meshRenderer.sharedMaterial = part.Material;
        meshRenderer.shadowCastingMode = ShadowCastingMode.Off;
        meshRenderer.receiveShadows = false;
        meshRenderer.sortingOrder = 200;
        parts[index] = part;
        ReparentPartToCamera(part);
        SetPartVisible(part, false);
        return part;
    }

    private void ReparentPartToCamera(RegionOverlayPart part)
    {
        Camera camera = ResolveOverlayCamera();
        if (part == null || part.Container == null || camera == null)
        {
            return;
        }

        Transform parent = camera.transform;
        if (part.Container.transform.parent != parent)
        {
            part.Container.transform.SetParent(parent, false);
        }

        part.Container.transform.localPosition = Vector3.zero;
        part.Container.transform.localRotation = Quaternion.identity;
        part.Container.transform.localScale = Vector3.one;
    }

    private void ApplyPartAppearance(RegionOverlayPart part, RegionRecipeState recipe, bool stale)
    {
        if (part == null || part.Material == null)
        {
            return;
        }

        float alpha = recipe.Opacity * Mathf.Lerp(0.35f, 1.0f, recipe.Intensity);
        if (stale)
        {
            alpha *= 0.45f;
        }

        Color color = recipe.Color;
        color.a = Mathf.Clamp01(alpha);
        if (recipe.Region == "cheek")
        {
            color = Color.Lerp(color, recipe.SecondaryColor, 0.18f);
            color.a = Mathf.Clamp01(alpha * 0.7f);
        }

        SetMaterialColor(part.Material, color);
    }

    private static Material CreateOverlayMaterial(string region, string partName)
    {
        Shader shader = Shader.Find("Sprites/Default");
        if (shader == null)
        {
            shader = Shader.Find("Unlit/Transparent");
        }

        if (shader == null)
        {
            shader = Shader.Find("Unlit/Color");
        }

        Material material = new Material(shader)
        {
            name = "MediaPipe Region " + region + " " + partName + " Material",
            renderQueue = (int)RenderQueue.Transparent + 30,
        };
        SetMaterialColor(material, Color.clear);
        SetMaterialRenderState(material);
        return material;
    }

    private static void SetMaterialColor(Material material, Color color)
    {
        if (material.HasProperty("_Color"))
        {
            material.SetColor("_Color", color);
        }

        if (material.HasProperty("_BaseColor"))
        {
            material.SetColor("_BaseColor", color);
        }
    }

    private static void SetMaterialRenderState(Material material)
    {
        if (material.HasProperty("_Cull"))
        {
            material.SetInt("_Cull", (int)CullMode.Off);
        }

        if (material.HasProperty("_CullMode"))
        {
            material.SetInt("_CullMode", (int)CullMode.Off);
        }

        if (material.HasProperty("_ZWrite"))
        {
            material.SetInt("_ZWrite", 0);
        }
    }

    private void ApplyPartCounts(string region, ref E3RegionMaskOverlay.RegionApplyResult result)
    {
        result.MeshVertexCount = 0;
        result.MeshIndexCount = 0;
        result.MeshUvCount = 0;
        result.MeshTriangleCount = 0;
        result.MaskTriangleCount = 0;
        result.SourceTriangleCount = 0;

        if (!regionParts.TryGetValue(region, out RegionOverlayPart[] parts))
        {
            return;
        }

        for (int index = 0; index < parts.Length; index++)
        {
            RegionOverlayPart part = parts[index];
            if (part == null || part.MeshRenderer == null || !part.MeshRenderer.enabled || part.Mesh == null)
            {
                continue;
            }

            result.MeshVertexCount += part.VertexCount;
            result.MeshIndexCount += part.IndexCount;
            result.MeshUvCount += part.UvCount;
            result.MeshTriangleCount += part.IndexCount / 3;
        }

        result.MaskTriangleCount = result.MeshTriangleCount;
        result.SourceTriangleCount = result.MeshTriangleCount > 0
            ? MediaPipeCanonicalFaceMesh.TriangleCount
            : 0;
        result.CulledTriangleCount = result.SourceTriangleCount > 0
            ? Mathf.Max(0, result.SourceTriangleCount - result.MeshTriangleCount)
            : 0;
    }

    private void HideUnusedParts(string region, int usedPartCount)
    {
        if (!regionParts.TryGetValue(region, out RegionOverlayPart[] parts))
        {
            return;
        }

        for (int index = usedPartCount; index < parts.Length; index++)
        {
            SetPartVisible(parts[index], false);
        }
    }

    private void HideRegionViews(string region)
    {
        if (!regionParts.TryGetValue(region, out RegionOverlayPart[] parts))
        {
            return;
        }

        for (int index = 0; index < parts.Length; index++)
        {
            SetPartVisible(parts[index], false);
        }
    }

    private void HideAllRegionViews()
    {
        foreach (KeyValuePair<string, RegionOverlayPart[]> entry in regionParts)
        {
            RegionOverlayPart[] parts = entry.Value;
            for (int index = 0; index < parts.Length; index++)
            {
                SetPartVisible(parts[index], false);
            }
        }
    }

    private static void SetPartVisible(RegionOverlayPart part, bool visible)
    {
        if (part != null && part.MeshRenderer != null)
        {
            part.MeshRenderer.enabled = visible;
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

    private static E3RegionMaskOverlay.RegionApplyResult CreateResult(string region)
    {
        MakeupRegionRendererRoute route = MakeupRegionRendererRoutes.Resolve(region, RendererMode);
        return new E3RegionMaskOverlay.RegionApplyResult
        {
            Region = region,
            Applied = false,
            FaceCount = 0,
            SourceTriangleCount = 0,
            MeshTriangleCount = 0,
            MaskTriangleCount = 0,
            CulledTriangleCount = 0,
            MeshCullingMode = "none",
            UvAvailable = false,
            MeshVertexCount = 0,
            MeshIndexCount = 0,
            MeshUvCount = 0,
            RendererMode = route.RendererMode,
            RegionRendererId = route.RendererId,
            MaskTextureId = region + "-mediapipe-region-v1",
            RuntimeTextureOverrideMode = "off",
            RuntimeTextureOverridePath = string.Empty,
            RuntimeTextureOverrideStatus = RuntimeTextureOverrideStatusOff,
            MaskSource = MaskSource,
            BoundaryRenderer = BoundaryRenderer,
            TrackingState = "None",
            StateAction = "not_started",
            TextureSample = string.Empty,
            TextureMode = string.Empty,
            LipRenderLayerMode = region == "lip" ? "mediapipe_region_polygon" : "none",
            GlossHighlightMode = "none",
            Intensity = 0.0f,
            Feather = 0.0f,
            BlendMode = string.Empty,
            SecondaryColorHex = string.Empty,
            Coverage = 0.0f,
            MaskSpreadX = 0.0f,
            MaskOffsetY = 0.0f,
            BrowGap = 0.0f,
            BrowAngle = 0.0f,
            BrowArch = 0.0f,
            BrowArchPosition = 0.0f,
            BrowCleanupEnabled = false,
            BrowCleanupStrength = 0.0f,
            BrowReshapeStrength = 0.0f,
            BrowCleanupSourceMode = region == "brow" ? "grabpass" : "none",
            BrowCleanupSource = "none",
            BrowCleanupFallback = "none",
            BrowCleanupStatus = region == "brow" ? "not_required_for_mediapipe_overlay" : "not_brow",
            BrowCleanupFallbackAvailable = false,
            BrowCleanupCameraTextureWidth = 0,
            BrowCleanupCameraTextureHeight = 0,
            Finish = string.Empty,
            Roughness = 0.0f,
            Specular = 0.0f,
            SpecularPower = 0.0f,
            GlossBoost = 0.0f,
            GradientAmount = 0.0f,
            DetailAmount = 0.0f,
            PreserveDetail = true,
            TopologyAuditStatus = "mediapipe_normalized_mesh",
            TopologyAuditSummary = MediaPipeCanonicalRegionMeshBuilder.TopologyAuditSummary,
            MaskThreshold = 0.0f,
            MaskFeatherUvNormalized = 0.0f,
            MaskSoftSampleMode = "mediapipe_canonical_triangle_gate",
            MaskFeatherNearRadiusPx = 0.0f,
            MaskFeatherFarRadiusPx = 0.0f,
            MaskTextureDiagnosticStatus = "not_applicable",
            MaskTextureWidth = 0,
            MaskTextureHeight = 0,
            MaskTextureActivePixelCountGt8 = 0,
            MaskTextureActiveCoverageGt8 = 0.0f,
            MaskTextureActiveBbox = "none",
            MaskTextureThresholdPixelCount = 0,
            MaskTextureThresholdCoverage = 0.0f,
            VisionBoundaryStatus = "not_requested",
            VisionBoundarySource = MaskSource,
            VisionBoundaryCoordinateMode = CoordinateMode,
            VisionBoundaryOuterPointCount = 0,
            VisionBoundaryInnerPointCount = 0,
            VisionBoundaryImageWidth = 0,
            VisionBoundaryImageHeight = 0,
            VisionBoundaryAgeMs = 0,
            VisionBoundaryFaceMotionScore = 0.0f,
            VisionBoundaryFaceCenterShiftPx = 0.0f,
            VisionBoundaryFaceScaleDelta = 0.0f,
            VisionBoundaryFaceMotionRisk = "none",
        };
    }

    private static void ApplyRecipeToResult(
        RegionRecipeState recipe,
        ref E3RegionMaskOverlay.RegionApplyResult result)
    {
        result.TextureSample = recipe.TextureSample;
        result.TextureMode = recipe.TextureMode;
        result.Intensity = recipe.Intensity;
        result.Feather = recipe.Feather;
        result.BlendMode = recipe.BlendMode;
        result.SecondaryColorHex = recipe.SecondaryColorHex;
        result.Coverage = recipe.Coverage;
        result.MaskSpreadX = recipe.MaskSpreadX;
        result.MaskOffsetY = recipe.MaskOffsetY;
        result.BrowGap = recipe.BrowGap;
        result.BrowAngle = recipe.BrowAngle;
        result.BrowArch = recipe.BrowArch;
        result.BrowArchPosition = recipe.BrowArchPosition;
        result.BrowCleanupEnabled = recipe.BrowCleanupEnabled;
        result.BrowCleanupStrength = recipe.BrowCleanupStrength;
        result.BrowReshapeStrength = recipe.BrowReshapeStrength;
        result.BrowCleanupSourceMode = recipe.BrowCleanupSourceMode;
        result.Finish = recipe.Finish;
        result.Roughness = recipe.Roughness;
        result.Specular = recipe.Specular;
        result.SpecularPower = recipe.SpecularPower;
        result.GlossBoost = recipe.GlossBoost;
        result.GradientAmount = recipe.GradientAmount;
        result.DetailAmount = recipe.DetailAmount;
        result.PreserveDetail = recipe.PreserveDetail;
        result.MaskTextureId = recipe.MaskTextureId;
        result.RuntimeTextureOverrideMode = recipe.RuntimeTextureOverrideMode;
        result.RuntimeTextureOverridePath = recipe.RuntimeTextureOverridePath;
        result.RuntimeTextureOverrideStatus = recipe.RuntimeTextureOverrideMode == "off"
            ? RuntimeTextureOverrideStatusOff
            : RuntimeTextureOverrideStatusUnsupported;
    }

    private static void ApplyPacketStatus(
        ref E3RegionMaskOverlay.RegionApplyResult result,
        MediaPipeFaceLandmarkPacket packet,
        MediaPipeFaceFrameSmoothingStatus status,
        bool hasPacket)
    {
        result.FaceCount = hasPacket ? 1 : 0;
        result.TrackingState = hasPacket
            ? status.Stale ? "Stale" : "Tracking"
            : "None";
        result.VisionBoundaryStatus = hasPacket ? "ready" : "waiting_for_face";
        result.VisionBoundaryImageWidth = packet != null ? packet.imageWidth : 0;
        result.VisionBoundaryImageHeight = packet != null ? packet.imageHeight : 0;
        result.VisionBoundaryAgeMs = status.PacketAgeMs;
        result.VisionBoundaryFaceMotionRisk = status.Stale ? "stale_packet" : "none";
    }

    private void MaybeLogApplyResult(E3RegionMaskOverlay.RegionApplyResult result, bool emitLog)
    {
        if (!emitLog)
        {
            return;
        }

        Debug.Log(
            "[E7] mediapipe_region_overlay_apply"
            + " rendererMode=" + result.RendererMode
            + " rendererId=" + result.RegionRendererId
            + " maskSource=" + result.MaskSource
            + " boundaryRenderer=" + result.BoundaryRenderer
            + " region=" + result.Region
            + " trackingState=" + result.TrackingState
            + " stateAction=" + result.StateAction
            + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " meshVertexCount=" + result.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + " meshIndexCount=" + result.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " coordinateMode=" + result.VisionBoundaryCoordinateMode
            + " imageSize=" + result.VisionBoundaryImageWidth.ToString(CultureInfo.InvariantCulture)
            + "x" + result.VisionBoundaryImageHeight.ToString(CultureInfo.InvariantCulture)
            + " packetAgeMs=" + result.VisionBoundaryAgeMs.ToString(CultureInfo.InvariantCulture)
            + " rawFrameStored=false"
            + " offDeviceUpload=false");
    }

    private static Vector2 ComputeCentroid(IList<Vector2> points)
    {
        Vector2 sum = Vector2.zero;
        for (int index = 0; index < points.Count; index++)
        {
            sum += points[index];
        }

        return sum / points.Count;
    }

    private static void SortPolygonByAngle(List<Vector2> polygon, Vector2 centroid)
    {
        for (int i = 1; i < polygon.Count; i++)
        {
            Vector2 value = polygon[i];
            float valueAngle = Mathf.Atan2(value.y - centroid.y, value.x - centroid.x);
            int j = i - 1;
            while (j >= 0)
            {
                Vector2 current = polygon[j];
                float currentAngle = Mathf.Atan2(current.y - centroid.y, current.x - centroid.x);
                if (currentAngle <= valueAngle)
                {
                    break;
                }

                polygon[j + 1] = current;
                j--;
            }

            polygon[j + 1] = value;
        }
    }

    private static Vector2 ClampNormalized(Vector2 point)
    {
        return new Vector2(
            Mathf.Clamp01(point.x),
            Mathf.Clamp01(point.y));
    }

    private static string NormalizeRegion(string region)
    {
        region = MakeupRegionRendererRoutes.NormalizeRegion(region);
        if (region == "eye")
        {
            throw new ArgumentException("MediaPipe region overlay renderer does not own eye rendering yet.");
        }

        return region;
    }

    private static string NormalizeBlendMode(string blendMode)
    {
        if (string.IsNullOrWhiteSpace(blendMode))
        {
            return "normal";
        }

        string value = blendMode.Trim().ToLowerInvariant();
        return value == "multiply" || value == "screen" ? value : "normal";
    }

    private static string NormalizeOptional(string value, string fallback)
    {
        return string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();
    }

    private sealed class RegionRecipeState
    {
        public string Region = string.Empty;
        public string ColorHex = "#D94B74";
        public Color Color = new Color(0.85f, 0.29f, 0.45f, 0.65f);
        public float Opacity = 0.65f;
        public bool Enabled = true;
        public string TextureSample = string.Empty;
        public string TextureMode = "sample";
        public float Intensity = 1.0f;
        public float Feather;
        public string BlendMode = "normal";
        public string MaskTextureId = string.Empty;
        public string RuntimeTextureOverrideMode = "off";
        public string RuntimeTextureOverridePath = string.Empty;
        public string SecondaryColorHex = "#F29BAA";
        public Color SecondaryColor = new Color(0.95f, 0.61f, 0.67f, 1.0f);
        public float Coverage = DefaultCoveragePivot;
        public float MaskSpreadX;
        public float MaskOffsetY;
        public float BrowGap;
        public float BrowAngle;
        public float BrowArch;
        public float BrowArchPosition;
        public bool BrowCleanupEnabled;
        public float BrowCleanupStrength;
        public float BrowReshapeStrength;
        public string BrowCleanupSourceMode = "none";
        public string Finish = "natural";
        public float Roughness;
        public float Specular;
        public float SpecularPower = 1.0f;
        public float GlossBoost;
        public float GradientAmount;
        public float DetailAmount;
        public bool PreserveDetail = true;
    }

    private sealed class RegionOverlayPart
    {
        public GameObject Container;
        public Mesh Mesh;
        public MeshRenderer MeshRenderer;
        public Material Material;
        public int VertexCount;
        public int UvCount;
        public int IndexCount;
        public int SourceTriangleCount;
        public int CulledTriangleCount;
    }
}
