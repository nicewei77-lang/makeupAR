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
        public int MeshTriangleCount;
        public int MaskTriangleCount;
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
        public string TopologyAuditStatus;
        public string TopologyAuditSummary;
        public float MaskThreshold;
        public float MaskFeatherUvNormalized;
    }

    private sealed class RegionRecipeState
    {
        public string Region = string.Empty;
        public string ColorHex = "#D94B74";
        public Color Color = new Color(0.85f, 0.29f, 0.45f, 0.65f);
        public float Opacity = 0.65f;
        public bool Enabled = true;
        public string TextureSample = "matte_lip";
        public string TextureMode = "sample";
        public float Intensity = 1.0f;
        public float Feather = 0.0f;
        public string BlendMode = "normal";
        public string MaskTextureId = "lip-smooth-mask-v1";
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
        string maskTextureId)
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
            TextureMode = string.IsNullOrWhiteSpace(textureMode) ? "sample" : textureMode,
            Intensity = intensity <= 0.0f ? 1.0f : Mathf.Clamp01(intensity),
            Feather = Mathf.Clamp01(feather),
            BlendMode = string.IsNullOrWhiteSpace(blendMode) ? "normal" : blendMode,
            MaskTextureId = GetDefaultMaskTextureId(region)
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
            bool meshApplied = useMeshMasks && TryUpdateFullFaceUvMesh(face, view, recipe, out triangleCount);
            result.MeshTriangleCount += triangleCount;
            result.MaskTriangleCount += triangleCount;

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
        MaskDefinition mask = ResolveMask(region);
        return new RegionApplyResult
        {
            Region = region,
            Applied = false,
            FaceCount = 0,
            MeshTriangleCount = 0,
            MaskTriangleCount = 0,
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
            TopologyAuditStatus = "not_run",
            TopologyAuditSummary = "none",
            MaskThreshold = mask.Threshold,
            MaskFeatherUvNormalized = mask.FeatherUvNormalized,
        };
    }

    private static void ApplyRecipeToResult(RegionRecipeState recipe, ref RegionApplyResult result)
    {
        MaskDefinition mask = ResolveMask(recipe.Region);
        result.TextureSample = recipe.TextureSample;
        result.TextureMode = recipe.TextureMode;
        result.Intensity = recipe.Intensity;
        result.Feather = recipe.Feather;
        result.BlendMode = recipe.BlendMode;
        result.MaskTextureId = recipe.MaskTextureId;
        result.MaskThreshold = mask.Threshold;
        result.MaskFeatherUvNormalized = mask.FeatherUvNormalized;
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
        out int triangleCount)
    {
        triangleCount = 0;

        if (!HasUsableUv(face) || view.MeshRenderer == null)
        {
            view.Mesh.Clear();
            return false;
        }

        MaskDefinition mask = ResolveMask(recipe.Region);
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

    private static MaskDefinition ResolveMask(string region)
    {
        region = NormalizeRegion(region);
        string maskTextureId = GetDefaultMaskTextureId(region);
        return new MaskDefinition
        {
            Region = region,
            MaskTextureId = maskTextureId,
            ResourcePath = "SmoothRegionMasks/" + maskTextureId,
            Threshold = 0.04f,
            FeatherUvNormalized = 0.56f
        };
    }

    private static string GetDefaultMaskTextureId(string region)
    {
        switch (NormalizeRegion(region))
        {
            case "cheek":
                return "cheek-smooth-mask-v1";
            case "eye":
                return "eye-smooth-mask-v1";
            default:
                return "lip-smooth-mask-v1";
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

    private void ApplyRecipeAppearance(RegionOverlayView view, RegionRecipeState recipe)
    {
        if (view.MeshRenderer == null)
        {
            return;
        }

        Material material = GetOrCreateMaskMaterial(view, recipe.Region);
        MaskDefinition mask = ResolveMask(recipe.Region);
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

        if (material.HasProperty("_RegionColor"))
        {
            material.SetColor("_RegionColor", new Color(materialColor.r, materialColor.g, materialColor.b, 1.0f));
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
            material.SetFloat("_Feather", mask.FeatherUvNormalized);
        }

        if (material.HasProperty("_VisibilityAlpha"))
        {
            material.SetFloat("_VisibilityAlpha", 1.0f);
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
            case "soft_blush":
                sampleAlphaScale = Mathf.Lerp(0.18f, 0.3f, recipe.Intensity);
                brightnessScale = 0.98f;
                break;
            case "shimmer_eye":
                sampleAlphaScale = Mathf.Lerp(0.16f, 0.28f, recipe.Intensity);
                brightnessScale = Mathf.Lerp(0.92f, 1.02f, recipe.Intensity);
                break;
            default:
                sampleAlphaScale = Mathf.Lerp(0.26f, 0.42f, recipe.Intensity);
                brightnessScale = 0.9f;
                break;
        }

        return new Color(
            Mathf.Clamp01(recipe.Color.r * brightnessScale),
            Mathf.Clamp01(recipe.Color.g * brightnessScale),
            Mathf.Clamp01(recipe.Color.b * brightnessScale),
            Mathf.Clamp01(recipe.Opacity * sampleAlphaScale));
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

        return "lip";
    }

    private static string NormalizeTextureSample(string region, string textureSample)
    {
        textureSample = string.IsNullOrWhiteSpace(textureSample)
            ? string.Empty
            : textureSample.Trim().ToLowerInvariant();

        if ((region == "lip" && textureSample == "matte_lip")
            || (region == "cheek" && textureSample == "soft_blush")
            || (region == "eye" && textureSample == "shimmer_eye"))
        {
            return textureSample;
        }

        switch (region)
        {
            case "lip":
                return "matte_lip";
            case "cheek":
                return "soft_blush";
            case "eye":
                return "shimmer_eye";
            default:
                return "matte_lip";
        }
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
            + " maskSource=" + MaskSource
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
            + " appliedTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " threshold=" + result.MaskThreshold.ToString("0.###", CultureInfo.InvariantCulture)
            + " featherUvNormalized=" + result.MaskFeatherUvNormalized.ToString("0.######", CultureInfo.InvariantCulture)
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
