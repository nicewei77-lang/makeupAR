using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public sealed class E3RegionMaskOverlay : MonoBehaviour
{
    public struct RegionApplyResult
    {
        public string Region;
        public bool Applied;
        public int FaceCount;
        public int SourceTriangleCount;
        public int MeshTriangleCount;
        public int MaskTriangleCount;
        public int CulledTriangleCount;
        public string MeshCullingMode;
        public bool UvAvailable;
        public int MeshVertexCount;
        public int MeshIndexCount;
        public int MeshUvCount;
        public string RendererMode;
        public string MaskTextureId;
        public string MaskSource;
        public string BoundaryRenderer;
        public string TrackingState;
        public string StateAction;
        public string TextureSample;
        public string TextureMode;
        public float Intensity;
        public float Feather;
        public string BlendMode;
        public string SecondaryColorHex;
        public float Coverage;
        public string Finish;
        public float Roughness;
        public float Specular;
        public float SpecularPower;
        public float GlossBoost;
        public float GradientAmount;
        public bool PreserveDetail;
        public string TopologyAuditStatus;
        public string TopologyAuditSummary;
        public float MaskThreshold;
        public float MaskFeatherUvNormalized;
        public string MaskTextureDiagnosticStatus;
        public int MaskTextureWidth;
        public int MaskTextureHeight;
        public int MaskTextureActivePixelCountGt8;
        public float MaskTextureActiveCoverageGt8;
        public string MaskTextureActiveBbox;
        public int MaskTextureThresholdPixelCount;
        public float MaskTextureThresholdCoverage;
    }

    private sealed class RegionRecipeState
    {
        public string Region = string.Empty;
        public string ColorHex = "#D94B74";
        public Color Color = new Color(0.85f, 0.29f, 0.45f, 0.65f);
        public string SecondaryColorHex = "#F29BAA";
        public Color SecondaryColor = new Color(0.95f, 0.61f, 0.67f, 1.0f);
        public float Opacity = 0.65f;
        public bool Enabled = true;
        public string TextureSample = "matte_lip";
        public string TextureMode = "sample";
        public float Intensity = 1.0f;
        public float Feather = 0.0f;
        public string BlendMode = "normal";
        public string MaskTextureId = "lip-drawn-style-atlas-v1";
        public float Coverage = 0.62f;
        public string Finish = "matte";
        public float Roughness = 0.88f;
        public float Specular = 0.04f;
        public float SpecularPower = 8.0f;
        public float GlossBoost = 0.0f;
        public float GradientAmount = 0.08f;
        public bool PreserveDetail = true;
    }

    private sealed class FaceOverlayState
    {
        public readonly Dictionary<string, RegionOverlayView> Regions =
            new Dictionary<string, RegionOverlayView>();
        public readonly Dictionary<string, string> LastLoggedStateActionByRegion =
            new Dictionary<string, string>();
        public bool WasLimitedOrLost;
    }

    private struct TrackingVisibility
    {
        public bool ShouldRender;
        public float AlphaMultiplier;
        public string Action;
    }

    private sealed class RegionOverlayView
    {
        public Mesh Mesh;
        public MeshRenderer MeshRenderer;
        public Material MaskMaterial;
    }

    private sealed class MaskDefinition
    {
        public string Region;
        public string MaskTextureId;
        public string ResourcePath;
        public float Threshold;
        public float FeatherUvNormalized;
    }

    private sealed class MaskTextureDiagnostics
    {
        public string Status = "not_run";
        public int Width;
        public int Height;
        public int ActivePixelCountGt8;
        public float ActiveCoverageGt8;
        public string ActiveBbox = "none";
        public int ThresholdPixelCount;
        public float ThresholdCoverage;
    }

    private sealed class MaskTextureSampleData
    {
        public string Status = "not_run";
        public int Width;
        public int Height;
        public int ThresholdByte;
        public Color32[] Pixels = new Color32[0];
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private bool useMeshMasks = true;

    private const string RendererMode = "smooth-region-mask";
    private const string MaskSource = "smooth_region_mask";
    private const string BoundaryRenderer = "smooth_alpha_mask";

    private readonly Dictionary<string, RegionRecipeState> recipes =
        new Dictionary<string, RegionRecipeState>();
    private readonly Dictionary<ARFace, FaceOverlayState> overlays =
        new Dictionary<ARFace, FaceOverlayState>();
    private readonly Dictionary<string, RegionApplyResult> latestRegionResults =
        new Dictionary<string, RegionApplyResult>();
    private static readonly Dictionary<string, Texture2D> MaskTextures =
        new Dictionary<string, Texture2D>();
    private static readonly Dictionary<string, MaskTextureDiagnostics> MaskTextureDiagnosticsCache =
        new Dictionary<string, MaskTextureDiagnostics>();
    private static readonly Dictionary<string, MaskTextureSampleData> MaskTextureSampleCache =
        new Dictionary<string, MaskTextureSampleData>();
    private bool overlayRenderingSuppressed;

    public void Configure(ARFaceManager manager)
    {
        if (faceManager == null)
        {
            faceManager = manager;
        }
    }

    public bool TryGetLatestRegionApplyResult(string region, out RegionApplyResult result)
    {
        return latestRegionResults.TryGetValue(NormalizeRegion(region), out result);
    }

    public void SetOverlayRenderingSuppressed(bool suppressed)
    {
        overlayRenderingSuppressed = suppressed;
        if (suppressed)
        {
            HideAllOverlayViews();
        }

        Debug.Log(
            "[E7] region_overlay_suppression"
            + " suppressed=" + overlayRenderingSuppressed.ToString().ToLowerInvariant());
    }

    public void ClearRecipesAndHideOverlays()
    {
        recipes.Clear();
        latestRegionResults.Clear();
        HideAllOverlayViews();
    }

    private void Update()
    {
        if (recipes.Count == 0)
        {
            return;
        }

        foreach (KeyValuePair<string, RegionRecipeState> entry in recipes)
        {
            if (entry.Value.Enabled)
            {
                ApplyRegionToTrackedFaces(entry.Key, false);
            }
        }
    }

    public RegionApplyResult ApplyRegionRecipe(
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
        string secondaryColorHex,
        Color secondaryColor,
        float coverage,
        string finish,
        float roughness,
        float specular,
        float specularPower,
        float glossBoost,
        float gradientAmount,
        bool preserveDetail)
    {
        region = NormalizeRegion(region);
        opacity = Mathf.Clamp01(opacity);
        recipes[region] = new RegionRecipeState
        {
            Region = region,
            ColorHex = colorHex,
            Color = new Color(color.r, color.g, color.b, opacity),
            Opacity = opacity,
            Enabled = enabled,
            TextureSample = NormalizeTextureSample(region, textureSample),
            TextureMode = NormalizeTextureMode(textureMode),
            Intensity = Mathf.Clamp01(intensity),
            Feather = Mathf.Clamp01(feather),
            BlendMode = NormalizeBlendMode(blendMode),
            MaskTextureId = NormalizeMaskTextureId(region, maskTextureId),
            SecondaryColorHex = string.IsNullOrWhiteSpace(secondaryColorHex)
                ? "#F29BAA"
                : secondaryColorHex.Trim(),
            SecondaryColor = secondaryColor,
            Coverage = Mathf.Clamp01(coverage),
            Finish = NormalizeOptional(finish),
            Roughness = Mathf.Clamp01(roughness),
            Specular = Mathf.Clamp01(specular),
            SpecularPower = Mathf.Max(1.0f, specularPower),
            GlossBoost = Mathf.Clamp01(glossBoost),
            GradientAmount = Mathf.Clamp01(gradientAmount),
            PreserveDetail = preserveDetail
        };

        return ApplyRegionToTrackedFaces(region, true);
    }

    private RegionApplyResult ApplyRegionToTrackedFaces(string region, bool emitLog)
    {
        RefreshSceneReferences();
        RegionApplyResult result = CreateResult(region);

        if (!recipes.TryGetValue(region, out RegionRecipeState recipe))
        {
            return result;
        }

        ApplyRecipeToResult(recipe, ref result);

        if (!recipe.Enabled)
        {
            result.StateAction = "disabled";
            HideRegionViews(region);
            latestRegionResults[region] = result;
            if (emitLog)
            {
                Debug.Log(
                    "[E7] region_mask_disabled"
                    + " region=" + region
                    + " rendererMode=" + RendererMode
                    + " maskTextureId=" + recipe.MaskTextureId);
            }

            return result;
        }

        if (faceManager == null)
        {
            if (emitLog)
            {
                Debug.LogWarning("[E7] region_mask_skipped region=" + region + " reason=faceManager_missing");
            }

            return result;
        }

        foreach (ARFace face in faceManager.trackables)
        {
            if (face == null)
            {
                continue;
            }

            FaceOverlayState faceState = EnsureFaceOverlayState(face);
            RegionOverlayView view = EnsureRegionOverlayView(face.transform, faceState, region);
            ApplyRecipeAppearance(view, recipe);
            TrackingVisibility visibility = ResolveTrackingVisibility(face, faceState);
            ApplyViewAlphaMultiplier(view, visibility.AlphaMultiplier);
            MaybeLogRegionMaskState(face, faceState, region, recipe, visibility);

            result.TrackingState = face.trackingState.ToString();
            result.StateAction = visibility.Action;
            result.UvAvailable = result.UvAvailable || HasUsableUv(face);
            result.MeshVertexCount = Mathf.Max(result.MeshVertexCount, GetVertexCount(face));
            result.MeshIndexCount = Mathf.Max(result.MeshIndexCount, GetIndexCount(face));
            result.MeshUvCount = Mathf.Max(result.MeshUvCount, GetUvCount(face));
            result.TopologyAuditStatus = BuildTopologyAuditStatus(face);
            result.TopologyAuditSummary = BuildTopologyAuditSummary(face);

            if (overlayRenderingSuppressed || !visibility.ShouldRender)
            {
                SetViewVisibility(view, false);
                if (overlayRenderingSuppressed)
                {
                    result.StateAction = "suppressed_for_clean_view";
                }
                continue;
            }

            result.FaceCount++;
            int triangleCount = 0;
            int sourceTriangleCount = 0;
            int culledTriangleCount = 0;
            string meshCullingMode = "none";
            bool meshApplied = useMeshMasks && TryUpdateFullFaceUvMesh(
                face,
                view,
                recipe,
                out triangleCount,
                out sourceTriangleCount,
                out culledTriangleCount,
                out meshCullingMode);
            result.SourceTriangleCount += sourceTriangleCount;
            result.MeshTriangleCount += triangleCount;
            result.MaskTriangleCount += triangleCount;
            result.CulledTriangleCount += culledTriangleCount;
            result.MeshCullingMode = meshCullingMode;

            SetViewVisibility(view, meshApplied);
            result.Applied = result.Applied || meshApplied;
        }

        latestRegionResults[region] = result;
        if (emitLog)
        {
            LogRegionApplyResult(result);
        }

        return result;
    }

    private static RegionApplyResult CreateResult(string region)
    {
        string maskTextureId = GetDefaultMaskTextureId(region);
        MaskDefinition mask = ResolveMask(region, maskTextureId);
        return new RegionApplyResult
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
            RendererMode = RendererMode,
            MaskTextureId = maskTextureId,
            MaskSource = MaskSource,
            BoundaryRenderer = BoundaryRenderer,
            TrackingState = "None",
            StateAction = "not_started",
            TextureSample = string.Empty,
            TextureMode = string.Empty,
            Intensity = 0.0f,
            Feather = 0.0f,
            BlendMode = string.Empty,
            SecondaryColorHex = string.Empty,
            Coverage = 0.0f,
            Finish = string.Empty,
            Roughness = 0.0f,
            Specular = 0.0f,
            SpecularPower = 0.0f,
            GlossBoost = 0.0f,
            GradientAmount = 0.0f,
            PreserveDetail = true,
            TopologyAuditStatus = "not_run",
            TopologyAuditSummary = "none",
            MaskThreshold = mask.Threshold,
            MaskFeatherUvNormalized = mask.FeatherUvNormalized,
            MaskTextureDiagnosticStatus = "not_run",
            MaskTextureWidth = 0,
            MaskTextureHeight = 0,
            MaskTextureActivePixelCountGt8 = 0,
            MaskTextureActiveCoverageGt8 = 0.0f,
            MaskTextureActiveBbox = "none",
            MaskTextureThresholdPixelCount = 0,
            MaskTextureThresholdCoverage = 0.0f,
        };
    }

    private static void ApplyRecipeToResult(RegionRecipeState recipe, ref RegionApplyResult result)
    {
        MaskDefinition mask = ResolveMask(recipe.Region, recipe.MaskTextureId);
        result.TextureSample = recipe.TextureSample;
        result.TextureMode = recipe.TextureMode;
        result.Intensity = recipe.Intensity;
        result.Feather = recipe.Feather;
        result.BlendMode = recipe.BlendMode;
        result.SecondaryColorHex = recipe.SecondaryColorHex;
        result.Coverage = recipe.Coverage;
        result.Finish = recipe.Finish;
        result.Roughness = recipe.Roughness;
        result.Specular = recipe.Specular;
        result.SpecularPower = recipe.SpecularPower;
        result.GlossBoost = recipe.GlossBoost;
        result.GradientAmount = recipe.GradientAmount;
        result.PreserveDetail = recipe.PreserveDetail;
        result.MaskTextureId = recipe.MaskTextureId;
        bool lipStyleAtlas = IsLipStyleAtlasMask(recipe.MaskTextureId);
        result.MaskSource = lipStyleAtlas
            ? "lip_style_atlas_v1_uv_back_projection"
            : MaskSource;
        result.BoundaryRenderer = lipStyleAtlas
            ? "rgba_style_atlas_smooth_alpha"
            : BoundaryRenderer;
        result.MaskThreshold = mask.Threshold;
        result.MaskFeatherUvNormalized = ResolveEffectiveFeather(mask, recipe);
        ApplyMaskTextureDiagnostics(mask, ref result);
    }

    private void RefreshSceneReferences()
    {
        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }
    }

    private FaceOverlayState EnsureFaceOverlayState(ARFace face)
    {
        if (overlays.TryGetValue(face, out FaceOverlayState state))
        {
            return state;
        }

        state = new FaceOverlayState();
        overlays[face] = state;
        return state;
    }

    private RegionOverlayView EnsureRegionOverlayView(
        Transform faceTransform,
        FaceOverlayState state,
        string region)
    {
        if (state.Regions.TryGetValue(region, out RegionOverlayView view))
        {
            return view;
        }

        view = CreateRegionOverlayView(faceTransform, region);
        state.Regions[region] = view;
        return view;
    }

    private RegionOverlayView CreateRegionOverlayView(Transform faceTransform, string region)
    {
        GameObject root = new GameObject("E3 Region " + region);
        root.transform.SetParent(faceTransform, false);
        root.transform.localPosition = Vector3.zero;
        root.transform.localRotation = Quaternion.identity;
        root.transform.localScale = Vector3.one;

        Mesh mesh = new Mesh
        {
            name = "E3 " + region + " smooth mask"
        };
        mesh.MarkDynamic();

        MeshFilter meshFilter = root.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = root.AddComponent<MeshRenderer>();
        meshFilter.sharedMesh = mesh;
        ConfigureRenderer(meshRenderer);

        RegionOverlayView view = new RegionOverlayView
        {
            Mesh = mesh,
            MeshRenderer = meshRenderer
        };

        SetViewVisibility(view, false);
        return view;
    }

    private static bool TryUpdateFullFaceUvMesh(
        ARFace face,
        RegionOverlayView view,
        RegionRecipeState recipe,
        out int triangleCount,
        out int sourceTriangleCount,
        out int culledTriangleCount,
        out string meshCullingMode)
    {
        triangleCount = 0;
        sourceTriangleCount = 0;
        culledTriangleCount = 0;
        meshCullingMode = "none";

        if (!HasUsableUv(face) || view.MeshRenderer == null)
        {
            view.Mesh.Clear();
            return false;
        }

        MaskDefinition mask = ResolveMask(recipe.Region, recipe.MaskTextureId);
        Texture2D maskTexture = GetMaskTexture(mask);
        if (maskTexture == null)
        {
            view.Mesh.Clear();
            return false;
        }

        if (view.MeshRenderer.sharedMaterial == null
            || !view.MeshRenderer.sharedMaterial.HasProperty("_MaskTex"))
        {
            view.Mesh.Clear();
            return false;
        }

        bool shouldCullToMask = ShouldCullMeshToMask(recipe);
        MaskTextureSampleData sampleData = null;
        if (shouldCullToMask)
        {
            sampleData = GetMaskTextureSampleData(mask);
            meshCullingMode = "lip_atlas_threshold_sample";
            if (sampleData == null || sampleData.Status != "ok")
            {
                meshCullingMode = "lip_atlas_threshold_sample_unavailable";
                view.Mesh.Clear();
                return false;
            }
        }

        List<Vector3> vertices = new List<Vector3>(face.vertices.Length);
        List<Vector2> textureCoordinates = new List<Vector2>(face.uvs.Length);
        List<int> triangles = new List<int>(face.indices.Length);

        for (int index = 0; index < face.vertices.Length; index++)
        {
            vertices.Add(face.vertices[index]);
        }

        for (int index = 0; index < face.uvs.Length; index++)
        {
            textureCoordinates.Add(face.uvs[index]);
        }

        for (int index = 0; index + 2 < face.indices.Length; index += 3)
        {
            int sourceA = face.indices[index];
            int sourceB = face.indices[index + 1];
            int sourceC = face.indices[index + 2];

            if (sourceA < 0 || sourceB < 0 || sourceC < 0
                || sourceA >= face.vertices.Length
                || sourceB >= face.vertices.Length
                || sourceC >= face.vertices.Length)
            {
                continue;
            }

            sourceTriangleCount++;
            if (shouldCullToMask
                && !TriangleIntersectsMask(
                    face.uvs[sourceA],
                    face.uvs[sourceB],
                    face.uvs[sourceC],
                    sampleData))
            {
                culledTriangleCount++;
                continue;
            }

            triangles.Add(sourceA);
            triangles.Add(sourceB);
            triangles.Add(sourceC);
        }

        triangleCount = triangles.Count / 3;
        if (triangleCount == 0)
        {
            view.Mesh.Clear();
            return false;
        }

        view.Mesh.Clear();
        view.Mesh.SetVertices(vertices);
        view.Mesh.SetUVs(0, textureCoordinates);
        view.Mesh.SetTriangles(triangles, 0);
        view.Mesh.RecalculateNormals();
        view.Mesh.RecalculateBounds();
        return true;
    }

    private static MaskDefinition ResolveMask(string region, string requestedMaskTextureId)
    {
        region = NormalizeRegion(region);
        string maskTextureId = NormalizeMaskTextureId(region, requestedMaskTextureId);
        bool lipStyleAtlas = region == "lip" && IsLipStyleAtlasMask(maskTextureId);
        return new MaskDefinition
        {
            Region = region,
            MaskTextureId = maskTextureId,
            ResourcePath = "SmoothRegionMasks/" + maskTextureId,
            Threshold = lipStyleAtlas ? 0.08f : 0.04f,
            FeatherUvNormalized = lipStyleAtlas ? 0.18f : 0.56f
        };
    }

    private static float ResolveEffectiveFeather(MaskDefinition mask, RegionRecipeState recipe)
    {
        if (mask == null)
        {
            return 0.0f;
        }

        if (recipe != null
            && recipe.Region == "lip"
            && IsLipStyleAtlasMask(recipe.MaskTextureId))
        {
            return Mathf.Clamp01(Mathf.Min(
                mask.FeatherUvNormalized,
                Mathf.Max(0.04f, recipe.Feather)));
        }

        return mask.FeatherUvNormalized;
    }

    private static string GetDefaultMaskTextureId(string region)
    {
        switch (NormalizeRegion(region))
        {
            case "lip":
                return "lip-drawn-style-atlas-v1";
            case "cheek":
                return "cheek-drawn-mask-v1";
            case "eye":
                return "eye-drawn-mask-v1";
            default:
                throw new ArgumentException("Unsupported smooth mask region: " + region);
        }
    }

    private static Texture2D GetMaskTexture(MaskDefinition mask)
    {
        if (mask == null || string.IsNullOrWhiteSpace(mask.ResourcePath))
        {
            return null;
        }

        if (MaskTextures.TryGetValue(mask.ResourcePath, out Texture2D cached))
        {
            return cached;
        }

        Texture2D texture = Resources.Load<Texture2D>(mask.ResourcePath);
        if (texture == null)
        {
            Debug.LogWarning(
                "[E7] smooth_mask_texture_missing"
                + " maskTextureId=" + mask.MaskTextureId
                + " resourcePath=" + mask.ResourcePath);
            return null;
        }

        texture.wrapMode = TextureWrapMode.Clamp;
        texture.filterMode = FilterMode.Bilinear;
        MaskTextures[mask.ResourcePath] = texture;
        return texture;
    }

    private static void ApplyMaskTextureDiagnostics(MaskDefinition mask, ref RegionApplyResult result)
    {
        MaskTextureDiagnostics diagnostics = GetMaskTextureDiagnostics(mask);
        result.MaskTextureDiagnosticStatus = diagnostics.Status;
        result.MaskTextureWidth = diagnostics.Width;
        result.MaskTextureHeight = diagnostics.Height;
        result.MaskTextureActivePixelCountGt8 = diagnostics.ActivePixelCountGt8;
        result.MaskTextureActiveCoverageGt8 = diagnostics.ActiveCoverageGt8;
        result.MaskTextureActiveBbox = diagnostics.ActiveBbox;
        result.MaskTextureThresholdPixelCount = diagnostics.ThresholdPixelCount;
        result.MaskTextureThresholdCoverage = diagnostics.ThresholdCoverage;
    }

    private static bool ShouldCullMeshToMask(RegionRecipeState recipe)
    {
        return recipe != null
            && recipe.Region == "lip"
            && IsLipStyleAtlasMask(recipe.MaskTextureId);
    }

    private static MaskTextureSampleData GetMaskTextureSampleData(MaskDefinition mask)
    {
        if (mask == null)
        {
            return null;
        }

        string cacheKey = mask.ResourcePath + "|sampleThreshold="
            + mask.Threshold.ToString("0.######", CultureInfo.InvariantCulture);
        if (MaskTextureSampleCache.TryGetValue(cacheKey, out MaskTextureSampleData cached))
        {
            return cached;
        }

        MaskTextureSampleData sampleData = new MaskTextureSampleData
        {
            ThresholdByte = Mathf.Clamp(Mathf.RoundToInt(mask.Threshold * 255.0f), 0, 255)
        };
        Texture2D texture = GetMaskTexture(mask);
        if (texture == null)
        {
            sampleData.Status = "texture_missing";
            MaskTextureSampleCache[cacheKey] = sampleData;
            return sampleData;
        }

        sampleData.Width = texture.width;
        sampleData.Height = texture.height;

        try
        {
            sampleData.Pixels = texture.GetPixels32();
            sampleData.Status = sampleData.Pixels.Length > 0 ? "ok" : "empty_pixels";
        }
        catch (Exception exception)
        {
            sampleData.Status = "error_" + SanitizeDiagnosticValue(exception.GetType().Name);
        }

        MaskTextureSampleCache[cacheKey] = sampleData;
        return sampleData;
    }

    private static bool TriangleIntersectsMask(
        Vector2 uvA,
        Vector2 uvB,
        Vector2 uvC,
        MaskTextureSampleData sampleData)
    {
        if (sampleData == null || sampleData.Status != "ok")
        {
            return false;
        }

        Vector2 centroid = (uvA + uvB + uvC) / 3.0f;
        Vector2 midAB = (uvA + uvB) * 0.5f;
        Vector2 midBC = (uvB + uvC) * 0.5f;
        Vector2 midCA = (uvC + uvA) * 0.5f;

        return SampleMaskByte(sampleData, uvA) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, uvB) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, uvC) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, centroid) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, midAB) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, midBC) > sampleData.ThresholdByte
            || SampleMaskByte(sampleData, midCA) > sampleData.ThresholdByte;
    }

    private static int SampleMaskByte(MaskTextureSampleData sampleData, Vector2 uv)
    {
        if (sampleData == null
            || sampleData.Pixels == null
            || sampleData.Pixels.Length == 0
            || sampleData.Width <= 0
            || sampleData.Height <= 0)
        {
            return 0;
        }

        int x = Mathf.Clamp(
            Mathf.RoundToInt(Mathf.Clamp01(uv.x) * (sampleData.Width - 1)),
            0,
            sampleData.Width - 1);
        int y = Mathf.Clamp(
            Mathf.RoundToInt(Mathf.Clamp01(uv.y) * (sampleData.Height - 1)),
            0,
            sampleData.Height - 1);
        int pixelIndex = y * sampleData.Width + x;
        if (pixelIndex < 0 || pixelIndex >= sampleData.Pixels.Length)
        {
            return 0;
        }

        return sampleData.Pixels[pixelIndex].r;
    }

    private static MaskTextureDiagnostics GetMaskTextureDiagnostics(MaskDefinition mask)
    {
        if (mask == null)
        {
            return new MaskTextureDiagnostics { Status = "mask_missing" };
        }

        string cacheKey = mask.ResourcePath + "|threshold=" + mask.Threshold.ToString("0.######", CultureInfo.InvariantCulture);
        if (MaskTextureDiagnosticsCache.TryGetValue(cacheKey, out MaskTextureDiagnostics cached))
        {
            return cached;
        }

        MaskTextureDiagnostics diagnostics = new MaskTextureDiagnostics();
        Texture2D texture = GetMaskTexture(mask);
        if (texture == null)
        {
            diagnostics.Status = "texture_missing";
            MaskTextureDiagnosticsCache[cacheKey] = diagnostics;
            return diagnostics;
        }

        diagnostics.Width = texture.width;
        diagnostics.Height = texture.height;

        try
        {
            Color32[] pixels = texture.GetPixels32();
            int totalPixels = Mathf.Max(1, pixels.Length);
            int thresholdByte = Mathf.Clamp(Mathf.RoundToInt(mask.Threshold * 255.0f), 0, 255);
            int minX = diagnostics.Width;
            int minY = diagnostics.Height;
            int maxX = -1;
            int maxY = -1;
            int activeCount = 0;
            int thresholdCount = 0;

            for (int y = 0; y < diagnostics.Height; y++)
            {
                for (int x = 0; x < diagnostics.Width; x++)
                {
                    int pixelIndex = y * diagnostics.Width + x;
                    if (pixelIndex < 0 || pixelIndex >= pixels.Length)
                    {
                        continue;
                    }

                    int value = pixels[pixelIndex].r;
                    if (value > thresholdByte)
                    {
                        thresholdCount++;
                    }

                    if (value <= 8)
                    {
                        continue;
                    }

                    int topLeftY = diagnostics.Height - 1 - y;
                    activeCount++;
                    minX = Mathf.Min(minX, x);
                    maxX = Mathf.Max(maxX, x);
                    minY = Mathf.Min(minY, topLeftY);
                    maxY = Mathf.Max(maxY, topLeftY);
                }
            }

            diagnostics.Status = "ok";
            diagnostics.ActivePixelCountGt8 = activeCount;
            diagnostics.ActiveCoverageGt8 = activeCount / (float)totalPixels;
            diagnostics.ThresholdPixelCount = thresholdCount;
            diagnostics.ThresholdCoverage = thresholdCount / (float)totalPixels;
            diagnostics.ActiveBbox = activeCount == 0
                ? "none"
                : "left=" + minX.ToString(CultureInfo.InvariantCulture)
                    + ",top=" + minY.ToString(CultureInfo.InvariantCulture)
                    + ",right=" + maxX.ToString(CultureInfo.InvariantCulture)
                    + ",bottom=" + maxY.ToString(CultureInfo.InvariantCulture)
                    + ",width=" + (maxX - minX + 1).ToString(CultureInfo.InvariantCulture)
                    + ",height=" + (maxY - minY + 1).ToString(CultureInfo.InvariantCulture);
        }
        catch (Exception exception)
        {
            diagnostics.Status = "error_" + SanitizeDiagnosticValue(exception.GetType().Name);
        }

        MaskTextureDiagnosticsCache[cacheKey] = diagnostics;
        return diagnostics;
    }

    private void ApplyRecipeAppearance(RegionOverlayView view, RegionRecipeState recipe)
    {
        if (view.MeshRenderer == null)
        {
            return;
        }

        Material material = GetOrCreateMaskMaterial(view, recipe.Region);
        MaskDefinition mask = ResolveMask(recipe.Region, recipe.MaskTextureId);
        Texture2D maskTexture = GetMaskTexture(mask);
        Color materialColor = BuildMaterialColor(recipe);

        if (material == null || maskTexture == null || !material.HasProperty("_MaskTex"))
        {
            view.MeshRenderer.enabled = false;
            view.Mesh.Clear();
            return;
        }

        view.MeshRenderer.sharedMaterial = material;
        material.SetTexture("_MaskTex", maskTexture);
        ApplyMaterialBlendMode(material, recipe.BlendMode);

        if (material.HasProperty("_RegionColor"))
        {
            material.SetColor("_RegionColor", new Color(materialColor.r, materialColor.g, materialColor.b, 1.0f));
        }

        if (material.HasProperty("_SecondaryColor"))
        {
            material.SetColor("_SecondaryColor", new Color(
                recipe.SecondaryColor.r,
                recipe.SecondaryColor.g,
                recipe.SecondaryColor.b,
                1.0f));
        }

        if (material.HasProperty("_Opacity"))
        {
            material.SetFloat("_Opacity", materialColor.a);
        }

        if (material.HasProperty("_Threshold"))
        {
            material.SetFloat("_Threshold", mask.Threshold);
        }

        if (material.HasProperty("_Feather"))
        {
            material.SetFloat("_Feather", ResolveEffectiveFeather(mask, recipe));
        }

        if (material.HasProperty("_VisibilityAlpha"))
        {
            material.SetFloat("_VisibilityAlpha", 1.0f);
        }

        if (material.HasProperty("_Coverage"))
        {
            material.SetFloat("_Coverage", recipe.Coverage);
        }

        if (material.HasProperty("_Roughness"))
        {
            material.SetFloat("_Roughness", recipe.Roughness);
        }

        if (material.HasProperty("_Specular"))
        {
            material.SetFloat("_Specular", recipe.Specular);
        }

        if (material.HasProperty("_SpecularPower"))
        {
            material.SetFloat("_SpecularPower", recipe.SpecularPower);
        }

        if (material.HasProperty("_GlossBoost"))
        {
            material.SetFloat("_GlossBoost", recipe.GlossBoost);
        }

        if (material.HasProperty("_GradientAmount"))
        {
            material.SetFloat("_GradientAmount", recipe.GradientAmount);
        }

        if (material.HasProperty("_PreserveDetail"))
        {
            material.SetFloat("_PreserveDetail", recipe.PreserveDetail ? 1.0f : 0.0f);
        }

        if (material.HasProperty("_LipStyleMode"))
        {
            material.SetFloat(
                "_LipStyleMode",
                IsLipStyleAtlasMask(recipe.MaskTextureId)
                    ? ResolveLipStyleMode(recipe.TextureSample)
                    : -1.0f);
        }
    }

    private static Material GetOrCreateMaskMaterial(RegionOverlayView view, string region)
    {
        if (view.MaskMaterial != null)
        {
            return view.MaskMaterial;
        }

        Material template = Resources.Load<Material>("SmoothRegionMaskMaterial");
        if (template != null)
        {
            view.MaskMaterial = new Material(template)
            {
                name = "Smooth UV Mask " + NormalizeRegion(region)
            };
            ConfigureTransparentMaterial(view.MaskMaterial);
            return view.MaskMaterial;
        }

        Shader shader = Shader.Find("MakeupAR/SmoothRegionMask");
        if (shader == null)
        {
            Debug.LogWarning(
                "[E7] smooth_mask_shader_missing"
                + " region=" + NormalizeRegion(region)
                + " action=hide_overlay");
            return null;
        }

        view.MaskMaterial = new Material(shader)
        {
            name = "Smooth UV Mask " + NormalizeRegion(region)
        };
        ConfigureTransparentMaterial(view.MaskMaterial);
        return view.MaskMaterial;
    }

    private static Color BuildMaterialColor(RegionRecipeState recipe)
    {
        float sampleAlphaScale = 1.0f;
        float brightnessScale = 1.0f;

        switch (recipe.TextureSample)
        {
            case "gloss_lip":
                sampleAlphaScale = Mathf.Lerp(0.34f, 0.52f, recipe.Intensity);
                brightnessScale = 1.02f;
                break;
            case "full_lip":
                sampleAlphaScale = Mathf.Lerp(0.44f, 0.64f, recipe.Intensity);
                brightnessScale = 0.92f;
                break;
            case "gradient_lip":
                sampleAlphaScale = Mathf.Lerp(0.32f, 0.5f, recipe.Intensity);
                brightnessScale = 0.98f;
                break;
            case "overline_lip":
                sampleAlphaScale = Mathf.Lerp(0.22f, 0.34f, recipe.Intensity);
                brightnessScale = 0.96f;
                break;
            case "soft_blush":
                sampleAlphaScale = Mathf.Lerp(0.26f, 0.42f, recipe.Intensity);
                brightnessScale = 1.02f;
                break;
            case "shimmer_eye":
                sampleAlphaScale = Mathf.Lerp(0.24f, 0.42f, recipe.Intensity);
                brightnessScale = Mathf.Lerp(1.0f, 1.08f, recipe.Intensity);
                break;
            default:
                sampleAlphaScale = Mathf.Lerp(0.34f, 0.52f, recipe.Intensity);
                brightnessScale = 0.95f;
                break;
        }

        return new Color(
            Mathf.Clamp01(recipe.Color.r * brightnessScale),
            Mathf.Clamp01(recipe.Color.g * brightnessScale),
            Mathf.Clamp01(recipe.Color.b * brightnessScale),
            Mathf.Clamp01(recipe.Opacity * sampleAlphaScale));
    }

    private static float ResolveLipStyleMode(string textureSample)
    {
        switch (textureSample)
        {
            case "gloss_lip":
                return 1.0f;
            case "full_lip":
                return 2.0f;
            case "gradient_lip":
                return 3.0f;
            case "overline_lip":
                return 4.0f;
            case "matte_lip":
                return 0.0f;
            default:
                return -1.0f;
        }
    }

    private static void ApplyMaterialBlendMode(Material material, string blendMode)
    {
        if (material == null)
        {
            return;
        }

        BlendMode sourceBlend = BlendMode.SrcAlpha;
        BlendMode destinationBlend = BlendMode.OneMinusSrcAlpha;

        switch (NormalizeBlendMode(blendMode))
        {
            case "multiply":
                sourceBlend = BlendMode.DstColor;
                destinationBlend = BlendMode.OneMinusSrcAlpha;
                break;
            case "screen":
                sourceBlend = BlendMode.SrcAlpha;
                destinationBlend = BlendMode.OneMinusSrcAlpha;
                break;
        }

        if (material.HasProperty("_SrcBlend"))
        {
            material.SetInt("_SrcBlend", (int)sourceBlend);
        }

        if (material.HasProperty("_DstBlend"))
        {
            material.SetInt("_DstBlend", (int)destinationBlend);
        }

        material.renderQueue = 5000;
    }

    private static void SetViewVisibility(RegionOverlayView view, bool showMesh)
    {
        if (view.MeshRenderer != null)
        {
            view.MeshRenderer.enabled = showMesh;
        }
    }

    private void HideAllOverlayViews()
    {
        foreach (FaceOverlayState faceState in overlays.Values)
        {
            foreach (RegionOverlayView view in faceState.Regions.Values)
            {
                SetViewVisibility(view, false);
            }
        }
    }

    private void HideRegionViews(string region)
    {
        foreach (FaceOverlayState faceState in overlays.Values)
        {
            if (faceState.Regions.TryGetValue(region, out RegionOverlayView view))
            {
                SetViewVisibility(view, false);
            }
        }
    }

    private static void ApplyViewAlphaMultiplier(RegionOverlayView view, float alphaMultiplier)
    {
        ApplyMaterialAlphaMultiplier(view.MeshRenderer != null ? view.MeshRenderer.sharedMaterial : null, alphaMultiplier);
    }

    private static void ApplyMaterialAlphaMultiplier(Material material, float alphaMultiplier)
    {
        if (material == null)
        {
            return;
        }

        if (material.HasProperty("_VisibilityAlpha"))
        {
            material.SetFloat("_VisibilityAlpha", Mathf.Clamp01(alphaMultiplier));
            return;
        }

        Color color = material.color;
        color.a = Mathf.Clamp01(color.a * Mathf.Clamp01(alphaMultiplier));
        ApplyMaterialColor(material, color);
    }

    private static void ConfigureTransparentMaterial(Material material)
    {
        ApplyMaterialColor(material, material.color);
    }

    private static void ConfigureRenderer(MeshRenderer renderer)
    {
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        renderer.receiveShadows = false;
        renderer.allowOcclusionWhenDynamic = false;
        renderer.sortingOrder = 120;
    }

    private static void ApplyMaterialColor(Material material, Color color)
    {
        if (material == null)
        {
            return;
        }

        material.color = color;

        if (material.HasProperty("_BaseColor"))
        {
            material.SetColor("_BaseColor", color);
        }

        if (material.HasProperty("_Color"))
        {
            material.SetColor("_Color", color);
        }

        if (material.HasProperty("_Surface"))
        {
            material.SetFloat("_Surface", 1.0f);
        }

        if (material.HasProperty("_SrcBlend"))
        {
            material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
        }

        if (material.HasProperty("_DstBlend"))
        {
            material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
        }

        if (material.HasProperty("_ZWrite"))
        {
            material.SetInt("_ZWrite", 0);
        }

        if (material.HasProperty("_ZTest"))
        {
            material.SetInt("_ZTest", (int)CompareFunction.Always);
        }

        material.DisableKeyword("_ALPHATEST_ON");
        material.EnableKeyword("_ALPHABLEND_ON");
        material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = 5000;
    }

    private static string NormalizeRegion(string region)
    {
        region = string.IsNullOrWhiteSpace(region) ? string.Empty : region.Trim().ToLowerInvariant();
        if (region == "lip" || region == "cheek" || region == "eye")
        {
            return region;
        }

        throw new ArgumentException("Unsupported smooth mask region: " + region);
    }

    private static string NormalizeTextureSample(string region, string textureSample)
    {
        textureSample = string.IsNullOrWhiteSpace(textureSample)
            ? string.Empty
            : textureSample.Trim().ToLowerInvariant();

        if ((region == "lip"
                && (textureSample == "matte_lip"
                    || textureSample == "gloss_lip"
                    || textureSample == "full_lip"
                    || textureSample == "gradient_lip"
                    || textureSample == "overline_lip"))
            || (region == "cheek" && textureSample == "soft_blush")
            || (region == "eye" && textureSample == "shimmer_eye"))
        {
            return textureSample;
        }

        throw new ArgumentException(
            "Unsupported smooth mask texture for region " + region + ": " + textureSample);
    }

    private static string NormalizeTextureMode(string textureMode)
    {
        textureMode = string.IsNullOrWhiteSpace(textureMode)
            ? string.Empty
            : textureMode.Trim().ToLowerInvariant();

        if (textureMode == "sample")
        {
            return textureMode;
        }

        throw new ArgumentException("Unsupported smooth mask texture mode: " + textureMode);
    }

    private static string NormalizeBlendMode(string blendMode)
    {
        blendMode = string.IsNullOrWhiteSpace(blendMode)
            ? string.Empty
            : blendMode.Trim().ToLowerInvariant();

        if (blendMode == "normal" || blendMode == "screen" || blendMode == "multiply")
        {
            return blendMode;
        }

        throw new ArgumentException("Unsupported smooth mask blend mode: " + blendMode);
    }

    private static string NormalizeMaskTextureId(string region, string maskTextureId)
    {
        maskTextureId = string.IsNullOrWhiteSpace(maskTextureId)
            ? string.Empty
            : maskTextureId.Trim();

        string expected = GetDefaultMaskTextureId(region);
        if (maskTextureId == expected
            || (region == "lip" && (maskTextureId == "lip-style-atlas-v1"
                || maskTextureId == "lip-smooth-mask-v1"
                || maskTextureId == "lip-drawn-mask-v1"))
            || (region == "cheek" && maskTextureId == "cheek-smooth-mask-v1")
            || (region == "eye" && maskTextureId == "eye-smooth-mask-v1"))
        {
            return maskTextureId;
        }

        throw new ArgumentException(
            "Unsupported smooth mask texture id for region " + region + ": " + maskTextureId);
    }

    private static bool IsLipStyleAtlasMask(string maskTextureId)
    {
        maskTextureId = string.IsNullOrWhiteSpace(maskTextureId)
            ? string.Empty
            : maskTextureId.Trim();

        return maskTextureId == "lip-drawn-style-atlas-v1"
            || maskTextureId == "lip-style-atlas-v1";
    }

    private static string NormalizeOptional(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "none" : value.Trim();
    }

    private static string SanitizeDiagnosticValue(string value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return "unknown";
        }

        return value.Trim()
            .Replace(" ", "_")
            .Replace(",", "_")
            .Replace("\"", string.Empty);
    }

    private static bool HasUsableUv(ARFace face)
    {
        return face != null
            && face.vertices.IsCreated
            && face.uvs.IsCreated
            && face.uvs.Length == face.vertices.Length
            && face.uvs.Length > 0;
    }

    private static int GetVertexCount(ARFace face)
    {
        return face != null && face.vertices.IsCreated ? face.vertices.Length : 0;
    }

    private static int GetIndexCount(ARFace face)
    {
        return face != null && face.indices.IsCreated ? face.indices.Length : 0;
    }

    private static int GetUvCount(ARFace face)
    {
        return face != null && face.uvs.IsCreated ? face.uvs.Length : 0;
    }

    private static TrackingVisibility ResolveTrackingVisibility(ARFace face, FaceOverlayState state)
    {
        if (face.trackingState == TrackingState.Tracking)
        {
            bool recovered = state.WasLimitedOrLost;
            state.WasLimitedOrLost = false;
            return new TrackingVisibility
            {
                ShouldRender = true,
                AlphaMultiplier = 1.0f,
                Action = recovered ? "recovered_restore" : "tracking_render"
            };
        }

        state.WasLimitedOrLost = true;
        string statePrefix = face.trackingState == TrackingState.Limited ? "limited" : "lost";
        return new TrackingVisibility
        {
            ShouldRender = false,
            AlphaMultiplier = 0.0f,
            Action = statePrefix + "_hide"
        };
    }

    private static void MaybeLogRegionMaskState(
        ARFace face,
        FaceOverlayState state,
        string region,
        RegionRecipeState recipe,
        TrackingVisibility visibility)
    {
        if (state.LastLoggedStateActionByRegion.TryGetValue(region, out string lastAction)
            && lastAction == visibility.Action)
        {
            return;
        }

        state.LastLoggedStateActionByRegion[region] = visibility.Action;
        Debug.Log(
            "[E7] region_mask_state"
            + " rendererMode=" + RendererMode
            + " maskTextureId=" + recipe.MaskTextureId
            + " maskSource=" + (IsLipStyleAtlasMask(recipe.MaskTextureId)
                ? "lip_style_atlas_v1_uv_back_projection"
                : MaskSource)
            + " region=" + region
            + " trackingState=" + face.trackingState
            + " stateAction=" + visibility.Action
            + " alphaMultiplier=" + visibility.AlphaMultiplier.ToString("0.##", CultureInfo.InvariantCulture)
            + " uvAvailable=" + HasUsableUv(face).ToString().ToLowerInvariant()
            + " meshVertexCount=" + GetVertexCount(face).ToString(CultureInfo.InvariantCulture)
            + " meshIndexCount=" + GetIndexCount(face).ToString(CultureInfo.InvariantCulture)
            + " meshUvCount=" + GetUvCount(face).ToString(CultureInfo.InvariantCulture)
            + " topologyAuditStatus=" + BuildTopologyAuditStatus(face));
    }

    private static void LogRegionApplyResult(RegionApplyResult result)
    {
        Debug.Log(
            "[E7] region_mask_apply"
            + " rendererMode=" + result.RendererMode
            + " maskTextureId=" + result.MaskTextureId
            + " maskSource=" + result.MaskSource
            + " boundaryRenderer=" + result.BoundaryRenderer
            + " region=" + result.Region
            + " trackingState=" + result.TrackingState
            + " stateAction=" + result.StateAction
            + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " meshVertexCount=" + result.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + " meshIndexCount=" + result.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + " meshUvCount=" + result.MeshUvCount.ToString(CultureInfo.InvariantCulture)
            + " uvAvailable=" + result.UvAvailable.ToString().ToLowerInvariant()
            + " sourceTriangles=" + result.SourceTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " appliedTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " culledTriangles=" + result.CulledTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " meshCullingMode=" + result.MeshCullingMode
            + " threshold=" + result.MaskThreshold.ToString("0.###", CultureInfo.InvariantCulture)
            + " featherUvNormalized=" + result.MaskFeatherUvNormalized.ToString("0.######", CultureInfo.InvariantCulture)
            + " maskTextureDiagnosticStatus=" + result.MaskTextureDiagnosticStatus
            + " maskTextureSize=" + result.MaskTextureWidth.ToString(CultureInfo.InvariantCulture)
            + "x" + result.MaskTextureHeight.ToString(CultureInfo.InvariantCulture)
            + " maskTextureGt8Pixels=" + result.MaskTextureActivePixelCountGt8.ToString(CultureInfo.InvariantCulture)
            + " maskTextureGt8Coverage=" + result.MaskTextureActiveCoverageGt8.ToString("0.######", CultureInfo.InvariantCulture)
            + " maskTextureGt8Bbox=" + result.MaskTextureActiveBbox
            + " maskTextureThresholdPixels=" + result.MaskTextureThresholdPixelCount.ToString(CultureInfo.InvariantCulture)
            + " maskTextureThresholdCoverage=" + result.MaskTextureThresholdCoverage.ToString("0.######", CultureInfo.InvariantCulture)
            + " coverage=" + result.Coverage.ToString("0.##", CultureInfo.InvariantCulture)
            + " finish=" + result.Finish
            + " roughness=" + result.Roughness.ToString("0.##", CultureInfo.InvariantCulture)
            + " specular=" + result.Specular.ToString("0.##", CultureInfo.InvariantCulture)
            + " specularPower=" + result.SpecularPower.ToString("0.##", CultureInfo.InvariantCulture)
            + " glossBoost=" + result.GlossBoost.ToString("0.##", CultureInfo.InvariantCulture)
            + " gradientAmount=" + result.GradientAmount.ToString("0.##", CultureInfo.InvariantCulture)
            + " topologyAuditStatus=" + result.TopologyAuditStatus
            + " regionDecision=smooth_mask_runtime"
            + " smoothing=smooth_alpha_mask"
            + " regionsInScope=lip,cheek,eye");
    }

    private static string BuildTopologyAuditStatus(ARFace face)
    {
        if (face == null)
        {
            return "face_missing";
        }

        if (!face.vertices.IsCreated || face.vertices.Length <= 0)
        {
            return "vertices_unavailable";
        }

        if (!face.indices.IsCreated || face.indices.Length < 3)
        {
            return "indices_unavailable";
        }

        if (face.indices.Length % 3 != 0)
        {
            return "indices_not_triangles";
        }

        return HasUsableUv(face) ? "pass_uv_topology_ready" : "uv_unavailable";
    }

    private static string BuildTopologyAuditSummary(ARFace face)
    {
        return "vertices=" + GetVertexCount(face).ToString(CultureInfo.InvariantCulture)
            + ";indices=" + GetIndexCount(face).ToString(CultureInfo.InvariantCulture)
            + ";uvs=" + GetUvCount(face).ToString(CultureInfo.InvariantCulture)
            + ";indexMod3=" + (GetIndexCount(face) % 3).ToString(CultureInfo.InvariantCulture)
            + ";stableUv=" + HasUsableUv(face).ToString().ToLowerInvariant();
    }
}
