using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;

public sealed class E3RegionMaskOverlay : MonoBehaviour
{
    private enum RegionMaskMode
    {
        BaselineCentroid,
        E7ArFaceUvCandidate,
        E7ArFaceAuthoredAtlas,
        E7ReferenceUvAtlas,
        E7ReferenceUvAlpha
    }

    public struct RegionApplyResult
    {
        public string Region;
        public bool Applied;
        public int FaceCount;
        public int MeshTriangleCount;
        public int BaselineTriangleCount;
        public int CandidateTriangleCount;
        public bool UsedFallback;
        public bool UvAvailable;
        public int MeshVertexCount;
        public int MeshIndexCount;
        public int MeshUvCount;
        public string RendererMode;
        public string CandidateId;
        public string VariantId;
        public string MaskSource;
        public string BoundaryRenderer;
        public string TrackingState;
        public string StateAction;
        public string TextureSample;
        public string TextureMode;
        public float Intensity;
        public float Feather;
        public string BlendMode;
        public string AtlasVersion;
        public string AtlasLabelMapVersion;
        public string AtlasLabelGroup;
        public string AtlasConfigSummary;
        public string AtlasConfigHash;
        public string TopologyAuditStatus;
        public string TopologyAuditSummary;
        public string AtlasVertexLabelSummary;
        public bool AtlasDataFallback;
        public string AtlasFallbackReason;
        public int AtlasSourceFrameCount;
        public int AtlasGoldMaskCount;
        public int AtlasSilverReferenceCount;
        public int AtlasUvResolution;
        public float AtlasThreshold;
        public int AtlasFeatherUvPixels;
        public float AtlasFeatherUvNormalized;
        public string AtlasCalibrationScoreSummary;
        public string AtlasCombineMode;
        public string AtlasMorphology;
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
        public string RendererMode = "e3e4-baseline";
        public string CandidateId = "e3e4-baseline";
        public string VariantId = "baseline-v0";
        public RegionMaskMode MaskMode = RegionMaskMode.BaselineCentroid;
    }

    private sealed class FaceOverlayState
    {
        public readonly Dictionary<string, RegionOverlayView> Regions =
            new Dictionary<string, RegionOverlayView>();
        public readonly Dictionary<string, string> LastLoggedStateActionByRegion =
            new Dictionary<string, string>();
        public float LastTrackedTime = float.NegativeInfinity;
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
        public GameObject Root;
        public Mesh Mesh;
        public MeshRenderer MeshRenderer;
        public Material RegionMaterial;
        public Material ReferenceUvAlphaMaterial;
        public readonly List<MeshRenderer> FallbackRenderers = new List<MeshRenderer>();
    }

    private sealed class AtlasVariantDefinition
    {
        public string Region;
        public string VariantId;
        public string LabelGroup;
        public string ConfigSummary;
        public float CenterX;
        public float CenterY;
        public float RadiusX;
        public float RadiusY;
        public float VertexPaddingX;
        public float VertexPaddingY;
        public int MinVertexHits;
        public bool MirrorX;
        public bool IsReferenceUvAtlas;
        public string ProbabilityResourcePath;
        public int SourceFrameCount;
        public int GoldMaskCount;
        public int SilverReferenceCount;
        public int UvResolution;
        public float Threshold;
        public int FeatherUvPixels;
        public float FeatherUvNormalized;
        public string CalibrationScoreSummary;
        public string CombineMode;
        public string Morphology;
        public string PromotionReason;
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private bool useMeshMasks = true;

    private const string AtlasVersion = "arface-authored-atlas-mvp-v0.1";
    private const string AtlasLabelMapVersion = "manual-label-map-v0.1";
    private const string ReferenceAtlasVersion = "e7ref-fastgate-20260622T160307Z-v0";
    private const string ReferenceAtlasLabelMapVersion = "reference-uv-atlas-fastgate-20260622T160307Z";

    private readonly Dictionary<string, RegionRecipeState> recipes =
        new Dictionary<string, RegionRecipeState>();
    private readonly Dictionary<ARFace, FaceOverlayState> overlays =
        new Dictionary<ARFace, FaceOverlayState>();
    private readonly Dictionary<string, Texture2D> sampleTextures =
        new Dictionary<string, Texture2D>();
    private readonly Dictionary<string, RegionApplyResult> latestRegionResults =
        new Dictionary<string, RegionApplyResult>();
    private static readonly Dictionary<string, Texture2D> ReferenceAtlasTextures =
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

        foreach (string region in recipes.Keys)
        {
            ApplyRegionToTrackedFaces(region, false);
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
        string candidateId,
        string variantId)
    {
        region = NormalizeRegion(region);
        opacity = Mathf.Clamp01(opacity);
        textureSample = NormalizeTextureSample(region, textureSample);
        RegionMaskMode maskMode = NormalizeMaskMode(rendererMode);
        string normalizedRendererMode = FormatRendererMode(maskMode);
        AtlasVariantDefinition atlasVariant = IsAtlasMaskMode(maskMode)
            ? ResolveAtlasVariant(region, variantId, maskMode)
            : null;

        recipes[region] = new RegionRecipeState
        {
            Region = region,
            ColorHex = colorHex,
            Color = new Color(color.r, color.g, color.b, opacity),
            Opacity = opacity,
            Enabled = enabled,
            TextureSample = textureSample,
            TextureMode = string.IsNullOrWhiteSpace(textureMode) ? "sample" : textureMode,
            Intensity = intensity <= 0.0f ? 1.0f : Mathf.Clamp01(intensity),
            Feather = Mathf.Clamp01(feather),
            BlendMode = string.IsNullOrWhiteSpace(blendMode) ? "normal" : blendMode,
            RendererMode = normalizedRendererMode,
            CandidateId = NormalizeCandidateId(candidateId, maskMode),
            VariantId = atlasVariant != null
                ? atlasVariant.VariantId
                : NormalizeNonAtlasVariantId(variantId, maskMode),
            MaskMode = maskMode
        };

        return ApplyRegionToTrackedFaces(region, true);
    }

    private RegionApplyResult ApplyRegionToTrackedFaces(string region, bool emitLog)
    {
        RefreshSceneReferences();

        RegionApplyResult result = new RegionApplyResult
        {
            Region = region,
            Applied = false,
            FaceCount = 0,
            MeshTriangleCount = 0,
            BaselineTriangleCount = 0,
            CandidateTriangleCount = 0,
            UsedFallback = false,
            UvAvailable = false,
            MeshVertexCount = 0,
            MeshIndexCount = 0,
            MeshUvCount = 0,
            RendererMode = "e3e4-baseline",
            CandidateId = "e3e4-baseline",
            VariantId = "baseline-v0",
            MaskSource = "centroid_broad",
            BoundaryRenderer = "triangle_subset",
            TrackingState = "None",
            StateAction = "not_started",
            TextureSample = string.Empty,
            TextureMode = string.Empty,
            Intensity = 0.0f,
            Feather = 0.0f,
            BlendMode = string.Empty,
            AtlasVersion = "none",
            AtlasLabelMapVersion = "none",
            AtlasLabelGroup = "none",
            AtlasConfigSummary = "none",
            AtlasConfigHash = "none",
            TopologyAuditStatus = "not_run",
            TopologyAuditSummary = "none",
            AtlasVertexLabelSummary = "none",
            AtlasDataFallback = false,
            AtlasFallbackReason = "none",
            AtlasSourceFrameCount = 0,
            AtlasGoldMaskCount = 0,
            AtlasSilverReferenceCount = 0,
            AtlasUvResolution = 0,
            AtlasThreshold = 0.0f,
            AtlasFeatherUvPixels = 0,
            AtlasFeatherUvNormalized = 0.0f,
            AtlasCalibrationScoreSummary = "none",
            AtlasCombineMode = "none",
            AtlasMorphology = "none"
        };

        if (!recipes.TryGetValue(region, out RegionRecipeState recipe))
        {
            return result;
        }

        result.TextureSample = recipe.TextureSample;
        result.TextureMode = recipe.TextureMode;
        result.Intensity = recipe.Intensity;
        result.Feather = recipe.Feather;
        result.BlendMode = recipe.BlendMode;
        result.RendererMode = recipe.RendererMode;
        result.CandidateId = recipe.CandidateId;
        result.VariantId = recipe.VariantId;
        result.MaskSource = GetMaskSource(recipe.MaskMode);
        result.BoundaryRenderer = GetBoundaryRenderer(recipe.MaskMode);

        if (faceManager == null)
        {
            if (emitLog)
            {
                Debug.LogWarning("[E3] applied_region_skipped region=" + region + " reason=faceManager_missing");
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
            MaybeLogE7RegionPrecisionState(face, faceState, region, recipe, visibility);

            result.TrackingState = face.trackingState.ToString();
            result.StateAction = visibility.Action;
            result.UvAvailable = result.UvAvailable || HasUsableUv(face);
            result.MeshVertexCount = Mathf.Max(result.MeshVertexCount, GetVertexCount(face));
            result.MeshIndexCount = Mathf.Max(result.MeshIndexCount, GetIndexCount(face));
            result.MeshUvCount = Mathf.Max(result.MeshUvCount, GetUvCount(face));
            PopulateAtlasEvidence(face, recipe, ref result);

            if (overlayRenderingSuppressed)
            {
                SetViewVisibility(view, false, false);
                result.StateAction = "suppressed_for_clean_reference_capture";
                continue;
            }

            if (!visibility.ShouldRender || !recipe.Enabled)
            {
                SetViewVisibility(view, false, false);
                continue;
            }

            result.FaceCount++;
            int triangleCount = 0;
            int baselineTriangles = CountRegionTriangles(face, region, RegionMaskMode.BaselineCentroid);
            int candidateTriangles = CountRegionTriangles(face, region, recipe);
            bool meshApplied = useMeshMasks
                && TryUpdateMeshMask(face, view, region, recipe, out triangleCount);
            result.MeshTriangleCount += triangleCount;
            result.BaselineTriangleCount += baselineTriangles;
            result.CandidateTriangleCount += candidateTriangles;

            if (meshApplied)
            {
                SetViewVisibility(view, true, false);
            }
            else if (recipe.MaskMode == RegionMaskMode.BaselineCentroid)
            {
                SetViewVisibility(view, false, true);
                result.UsedFallback = true;
            }
            else
            {
                SetViewVisibility(view, false, false);
                result.UsedFallback = true;
            }

            result.Applied = true;
        }

        latestRegionResults[region] = result;

        if (emitLog)
        {
            Debug.Log(
                "[E3] applied_region"
                + " region=" + region
                + " color=" + recipe.ColorHex
                + " opacity=" + recipe.Opacity.ToString("0.##", CultureInfo.InvariantCulture)
                + " enabled=" + recipe.Enabled.ToString().ToLowerInvariant()
                + " applied=" + result.Applied.ToString().ToLowerInvariant()
                + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
                + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant());
            Debug.Log(
                "[E4] applied_texture"
                + " region=" + region
                + " appliedTexture=" + recipe.TextureSample
                + " textureMode=" + recipe.TextureMode
                + " intensity=" + recipe.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
                + " feather=" + recipe.Feather.ToString("0.##", CultureInfo.InvariantCulture)
                + " blendMode=" + recipe.BlendMode
                + " applied=" + result.Applied.ToString().ToLowerInvariant()
                + " appliedRegion=" + result.Region
                + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
                + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant());
            Debug.Log(
                "[E7] region_precision_compare"
                + " rendererMode=" + result.RendererMode
                + " candidateId=" + result.CandidateId
                + " variantId=" + result.VariantId
                + " maskSource=" + result.MaskSource
                + " boundaryRenderer=" + result.BoundaryRenderer
                + " region=" + region
                + " activeRegion=" + region
                + " trackingState=" + result.TrackingState
                + " stateAction=" + result.StateAction
                + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
                + " meshVertexCount=" + result.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
                + " meshIndexCount=" + result.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
                + " meshUvCount=" + result.MeshUvCount.ToString(CultureInfo.InvariantCulture)
                + " uvAvailable=" + result.UvAvailable.ToString().ToLowerInvariant()
                + " baselineTriangles=" + result.BaselineTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " candidateTriangles=" + result.CandidateTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " appliedTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant()
                + " atlasDataFallback=" + result.AtlasDataFallback.ToString().ToLowerInvariant()
                + " atlasFallbackReason=" + result.AtlasFallbackReason
                + " atlasSourceFrameCount=" + result.AtlasSourceFrameCount.ToString(CultureInfo.InvariantCulture)
                + " goldMaskCount=" + result.AtlasGoldMaskCount.ToString(CultureInfo.InvariantCulture)
                + " silverReferenceCount=" + result.AtlasSilverReferenceCount.ToString(CultureInfo.InvariantCulture)
                + " uvResolution=" + result.AtlasUvResolution.ToString(CultureInfo.InvariantCulture)
                + " threshold=" + result.AtlasThreshold.ToString("0.###", CultureInfo.InvariantCulture)
                + " featherUvPixels=" + result.AtlasFeatherUvPixels.ToString(CultureInfo.InvariantCulture)
                + " featherUvNormalized=" + result.AtlasFeatherUvNormalized.ToString("0.######", CultureInfo.InvariantCulture)
                + " calibrationScore=" + SanitizeLogValue(result.AtlasCalibrationScoreSummary)
                + " combineMode=" + result.AtlasCombineMode
                + " morphology=" + result.AtlasMorphology
                + " atlasVersion=" + result.AtlasVersion
                + " atlasLabelMapVersion=" + result.AtlasLabelMapVersion
                + " atlasLabelGroup=" + result.AtlasLabelGroup
                + " atlasConfigHash=" + result.AtlasConfigHash
                + " topologyAuditStatus=" + result.TopologyAuditStatus
                + " topologyAuditSummary=" + result.TopologyAuditSummary
                + " atlasVertexLabelSummary=" + result.AtlasVertexLabelSummary
                + " regionDecision=yellow_pending_real_device_visual_review"
                + " smoothing=visibility_hysteresis_only"
                + " regionsInScope=lip,cheek,eye");
        }

        return result;
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
            name = "E3 " + region + " mesh mask"
        };
        mesh.MarkDynamic();

        MeshFilter meshFilter = root.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = root.AddComponent<MeshRenderer>();
        meshFilter.sharedMesh = mesh;
        meshRenderer.sharedMaterial = CreateRegionMaterial(region, Color.clear);
        ConfigureRenderer(meshRenderer);

        RegionOverlayView view = new RegionOverlayView
        {
            Root = root,
            Mesh = mesh,
            MeshRenderer = meshRenderer,
            RegionMaterial = meshRenderer.sharedMaterial
        };

        CreateFallbackGeometry(root.transform, region, meshRenderer.sharedMaterial, view);
        SetViewVisibility(view, false, false);
        return view;
    }

    private static void CreateFallbackGeometry(
        Transform root,
        string region,
        Material material,
        RegionOverlayView view)
    {
        switch (region)
        {
            case "lip":
                AddFallbackEllipse(root, "lip", new Vector3(0.0f, -0.035f, 0.075f), new Vector3(0.08f, 0.026f, 0.008f), material, view);
                break;
            case "cheek":
                AddFallbackEllipse(root, "cheek-left", new Vector3(-0.072f, -0.004f, 0.07f), new Vector3(0.045f, 0.036f, 0.008f), material, view);
                AddFallbackEllipse(root, "cheek-right", new Vector3(0.072f, -0.004f, 0.07f), new Vector3(0.045f, 0.036f, 0.008f), material, view);
                break;
            case "eye":
                AddFallbackEllipse(root, "eye-left", new Vector3(-0.038f, 0.042f, 0.076f), new Vector3(0.044f, 0.018f, 0.008f), material, view);
                AddFallbackEllipse(root, "eye-right", new Vector3(0.038f, 0.042f, 0.076f), new Vector3(0.044f, 0.018f, 0.008f), material, view);
                break;
        }
    }

    private static void AddFallbackEllipse(
        Transform root,
        string name,
        Vector3 localPosition,
        Vector3 localScale,
        Material material,
        RegionOverlayView view)
    {
        GameObject primitive = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        primitive.name = "E3 " + name + " fallback";
        primitive.transform.SetParent(root, false);
        primitive.transform.localPosition = localPosition;
        primitive.transform.localRotation = Quaternion.identity;
        primitive.transform.localScale = localScale;

        Collider collider = primitive.GetComponent<Collider>();
        if (collider != null)
        {
            Destroy(collider);
        }

        MeshRenderer renderer = primitive.GetComponent<MeshRenderer>();
        if (renderer == null)
        {
            return;
        }

        renderer.sharedMaterial = material;
        ConfigureRenderer(renderer);
        view.FallbackRenderers.Add(renderer);
    }

    private static bool TryUpdateMeshMask(
        ARFace face,
        RegionOverlayView view,
        string region,
        RegionRecipeState recipe,
        out int triangleCount)
    {
        triangleCount = 0;

        if (!face.vertices.IsCreated || !face.indices.IsCreated || face.vertices.Length == 0 || face.indices.Length < 3)
        {
            view.Mesh.Clear();
            return false;
        }

        if (recipe.MaskMode == RegionMaskMode.E7ReferenceUvAlpha)
        {
            return TryUpdateFullFaceUvMesh(face, view, region, recipe, out triangleCount);
        }

        bool hasTextureCoordinates = HasUsableUv(face);
        List<Vector3> vertices = new List<Vector3>(256);
        List<Vector2> textureCoordinates = new List<Vector2>(256);
        List<int> triangles = new List<int>(384);
        Dictionary<int, int> remapped = new Dictionary<int, int>();

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

            Vector3 a = face.vertices[sourceA];
            Vector3 b = face.vertices[sourceB];
            Vector3 c = face.vertices[sourceC];
            Vector3 centroid = (a + b + c) / 3.0f;
            Vector2 uvCentroid = hasTextureCoordinates
                ? (face.uvs[sourceA] + face.uvs[sourceB] + face.uvs[sourceC]) / 3.0f
                : Vector2.zero;

            if (!IsTriangleInRegion(
                    region,
                    centroid,
                    uvCentroid,
                    hasTextureCoordinates,
                    recipe.MaskMode,
                    face,
                    sourceA,
                    sourceB,
                    sourceC,
                    recipe.VariantId))
            {
                continue;
            }

            triangles.Add(GetOrAddVertex(
                sourceA,
                a,
                hasTextureCoordinates ? face.uvs[sourceA] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
            triangles.Add(GetOrAddVertex(
                sourceB,
                b,
                hasTextureCoordinates ? face.uvs[sourceB] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
            triangles.Add(GetOrAddVertex(
                sourceC,
                c,
                hasTextureCoordinates ? face.uvs[sourceC] : Vector2.zero,
                vertices,
                textureCoordinates,
                remapped));
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

    private static bool TryUpdateFullFaceUvMesh(
        ARFace face,
        RegionOverlayView view,
        string region,
        RegionRecipeState recipe,
        out int triangleCount)
    {
        triangleCount = 0;

        if (!HasUsableUv(face))
        {
            view.Mesh.Clear();
            return false;
        }

        AtlasVariantDefinition atlasVariant = ResolveAtlasVariant(region, recipe.VariantId, recipe.MaskMode);
        Texture2D probabilityAtlas = GetReferenceAtlasTexture(atlasVariant);
        if (probabilityAtlas == null)
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

    private static int CountRegionTriangles(ARFace face, string region, RegionRecipeState recipe)
    {
        return CountRegionTriangles(face, region, recipe.MaskMode, recipe.VariantId);
    }

    private static int CountRegionTriangles(ARFace face, string region, RegionMaskMode maskMode)
    {
        return CountRegionTriangles(face, region, maskMode, string.Empty);
    }

    private static int CountRegionTriangles(
        ARFace face,
        string region,
        RegionMaskMode maskMode,
        string variantId)
    {
        if (!face.vertices.IsCreated || !face.indices.IsCreated || face.vertices.Length == 0 || face.indices.Length < 3)
        {
            return 0;
        }

        if (maskMode == RegionMaskMode.E7ReferenceUvAlpha)
        {
            return HasUsableUv(face) ? face.indices.Length / 3 : 0;
        }

        bool hasTextureCoordinates = HasUsableUv(face);
        int count = 0;
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

            Vector3 centroid = (face.vertices[sourceA] + face.vertices[sourceB] + face.vertices[sourceC]) / 3.0f;
            Vector2 uvCentroid = hasTextureCoordinates
                ? (face.uvs[sourceA] + face.uvs[sourceB] + face.uvs[sourceC]) / 3.0f
                : Vector2.zero;

            if (IsTriangleInRegion(
                    region,
                    centroid,
                    uvCentroid,
                    hasTextureCoordinates,
                    maskMode,
                    face,
                    sourceA,
                    sourceB,
                    sourceC,
                    variantId))
            {
                count++;
            }
        }

        return count;
    }

    private static int GetOrAddVertex(
        int sourceIndex,
        Vector3 value,
        Vector2 textureCoordinate,
        List<Vector3> vertices,
        List<Vector2> textureCoordinates,
        Dictionary<int, int> remapped)
    {
        if (remapped.TryGetValue(sourceIndex, out int targetIndex))
        {
            return targetIndex;
        }

        targetIndex = vertices.Count;
        vertices.Add(value);
        textureCoordinates.Add(textureCoordinate);
        remapped[sourceIndex] = targetIndex;
        return targetIndex;
    }

    private static bool IsCentroidInRegion(string region, Vector3 point)
    {
        float absX = Mathf.Abs(point.x);

        switch (region)
        {
            case "lip":
                return absX <= 0.058f && point.y >= -0.06f && point.y <= -0.012f;
            case "cheek":
                return absX >= 0.052f && absX <= 0.13f && point.y >= -0.028f && point.y <= 0.028f;
            case "eye":
                return absX >= 0.018f && absX <= 0.09f && point.y >= 0.022f && point.y <= 0.075f;
            default:
                return false;
        }
    }

    private static bool IsTriangleInRegion(
        string region,
        Vector3 centroid,
        Vector2 uvCentroid,
        bool hasTextureCoordinates,
        RegionMaskMode maskMode,
        ARFace face,
        int sourceA,
        int sourceB,
        int sourceC,
        string variantId)
    {
        if (maskMode == RegionMaskMode.BaselineCentroid)
        {
            return IsCentroidInRegion(region, centroid);
        }

        if (!hasTextureCoordinates || !IsUsableTextureCoordinate(uvCentroid))
        {
            return false;
        }

        if (maskMode == RegionMaskMode.E7ReferenceUvAtlas)
        {
            AtlasVariantDefinition atlasVariant = ResolveAtlasVariant(region, variantId, maskMode);
            return IsReferenceAtlasTriangleInRegion(atlasVariant, uvCentroid);
        }

        if (maskMode == RegionMaskMode.E7ArFaceAuthoredAtlas)
        {
            AtlasVariantDefinition atlasVariant = ResolveAtlasVariant(region, variantId, maskMode);
            return IsAuthoredAtlasTriangleInRegion(
                region,
                atlasVariant,
                face,
                sourceA,
                sourceB,
                sourceC,
                centroid);
        }

        return IsE7CandidateRegion(region, centroid);
    }

    private static bool IsE7CandidateRegion(string region, Vector3 point)
    {
        switch (region)
        {
            case "lip":
                return IsEllipse(point, 0.0f, -0.036f, 0.052f, 0.024f);
            case "cheek":
                return IsEllipse(point, -0.083f, -0.002f, 0.043f, 0.033f)
                    || IsEllipse(point, 0.083f, -0.002f, 0.043f, 0.033f);
            case "eye":
                return IsEllipse(point, -0.047f, 0.045f, 0.044f, 0.021f)
                    || IsEllipse(point, 0.047f, 0.045f, 0.044f, 0.021f);
            default:
                return false;
        }
    }

    private static bool IsEllipse(Vector3 point, float centerX, float centerY, float radiusX, float radiusY)
    {
        float dx = (point.x - centerX) / Mathf.Max(0.0001f, radiusX);
        float dy = (point.y - centerY) / Mathf.Max(0.0001f, radiusY);
        return (dx * dx) + (dy * dy) <= 1.0f;
    }

    private static bool IsAuthoredAtlasTriangleInRegion(
        string region,
        AtlasVariantDefinition atlasVariant,
        ARFace face,
        int sourceA,
        int sourceB,
        int sourceC,
        Vector3 centroid)
    {
        if (atlasVariant == null)
        {
            return false;
        }

        int labelHits = 0;
        labelHits += IsManualAtlasVertexLabel(region, atlasVariant, face.vertices[sourceA]) ? 1 : 0;
        labelHits += IsManualAtlasVertexLabel(region, atlasVariant, face.vertices[sourceB]) ? 1 : 0;
        labelHits += IsManualAtlasVertexLabel(region, atlasVariant, face.vertices[sourceC]) ? 1 : 0;

        return labelHits >= Mathf.Clamp(atlasVariant.MinVertexHits, 1, 3)
            && IsPointInsideAtlasVariant(centroid, atlasVariant);
    }

    private static bool IsManualAtlasVertexLabel(
        string region,
        AtlasVariantDefinition atlasVariant,
        Vector3 point)
    {
        if (atlasVariant == null || atlasVariant.Region != region)
        {
            return false;
        }

        AtlasVariantDefinition padded = new AtlasVariantDefinition
        {
            Region = atlasVariant.Region,
            VariantId = atlasVariant.VariantId,
            LabelGroup = atlasVariant.LabelGroup,
            ConfigSummary = atlasVariant.ConfigSummary,
            CenterX = atlasVariant.CenterX,
            CenterY = atlasVariant.CenterY,
            RadiusX = atlasVariant.RadiusX + atlasVariant.VertexPaddingX,
            RadiusY = atlasVariant.RadiusY + atlasVariant.VertexPaddingY,
            VertexPaddingX = atlasVariant.VertexPaddingX,
            VertexPaddingY = atlasVariant.VertexPaddingY,
            MinVertexHits = atlasVariant.MinVertexHits,
            MirrorX = atlasVariant.MirrorX
        };

        return IsPointInsideAtlasVariant(point, padded);
    }

    private static bool IsPointInsideAtlasVariant(Vector3 point, AtlasVariantDefinition atlasVariant)
    {
        if (atlasVariant.MirrorX)
        {
            return IsEllipse(point, -atlasVariant.CenterX, atlasVariant.CenterY, atlasVariant.RadiusX, atlasVariant.RadiusY)
                || IsEllipse(point, atlasVariant.CenterX, atlasVariant.CenterY, atlasVariant.RadiusX, atlasVariant.RadiusY);
        }

        return IsEllipse(point, atlasVariant.CenterX, atlasVariant.CenterY, atlasVariant.RadiusX, atlasVariant.RadiusY);
    }

    private static bool IsReferenceAtlasTriangleInRegion(
        AtlasVariantDefinition atlasVariant,
        Vector2 uvCentroid)
    {
        if (atlasVariant == null || !atlasVariant.IsReferenceUvAtlas)
        {
            return false;
        }

        Texture2D probabilityAtlas = GetReferenceAtlasTexture(atlasVariant);
        if (probabilityAtlas == null)
        {
            return false;
        }

        float probability = probabilityAtlas.GetPixelBilinear(
            Mathf.Clamp01(uvCentroid.x),
            Mathf.Clamp01(uvCentroid.y)).grayscale;
        return probability >= atlasVariant.Threshold;
    }

    private static Texture2D GetReferenceAtlasTexture(AtlasVariantDefinition atlasVariant)
    {
        if (atlasVariant == null || string.IsNullOrWhiteSpace(atlasVariant.ProbabilityResourcePath))
        {
            return null;
        }

        if (ReferenceAtlasTextures.TryGetValue(atlasVariant.ProbabilityResourcePath, out Texture2D cached))
        {
            return cached;
        }

        Texture2D texture = Resources.Load<Texture2D>(atlasVariant.ProbabilityResourcePath);
        if (texture == null)
        {
            Debug.LogWarning(
                "[E7] reference_uv_atlas_missing"
                + " variantId=" + atlasVariant.VariantId
                + " resourcePath=" + atlasVariant.ProbabilityResourcePath);
            return null;
        }

        texture.wrapMode = TextureWrapMode.Clamp;
        texture.filterMode = FilterMode.Bilinear;
        ReferenceAtlasTextures[atlasVariant.ProbabilityResourcePath] = texture;
        return texture;
    }

    private static bool IsUsableTextureCoordinate(Vector2 uv)
    {
        return !float.IsNaN(uv.x)
            && !float.IsNaN(uv.y)
            && !float.IsInfinity(uv.x)
            && !float.IsInfinity(uv.y);
    }

    private void ApplyRecipeAppearance(RegionOverlayView view, RegionRecipeState recipe)
    {
        if (recipe.MaskMode == RegionMaskMode.E7ReferenceUvAlpha)
        {
            ApplyReferenceUvAlphaMaterialAppearance(view, recipe);
            return;
        }

        if (view.MeshRenderer != null && view.RegionMaterial != null)
        {
            view.MeshRenderer.sharedMaterial = view.RegionMaterial;
        }

        Texture2D texture = GetOrCreateTextureSample(recipe.TextureSample, recipe.Feather);
        Color materialColor = BuildMaterialColor(recipe);

        ApplyMaterialAppearance(
            view.MeshRenderer.sharedMaterial,
            materialColor,
            texture,
            recipe.BlendMode);

        foreach (MeshRenderer renderer in view.FallbackRenderers)
        {
            ApplyMaterialAppearance(
                renderer.sharedMaterial,
                materialColor,
                texture,
                recipe.BlendMode);
        }
    }

    private static void ApplyReferenceUvAlphaMaterialAppearance(
        RegionOverlayView view,
        RegionRecipeState recipe)
    {
        if (view.MeshRenderer == null)
        {
            return;
        }

        Material material = GetOrCreateReferenceUvAlphaMaterial(view, recipe.Region);
        view.MeshRenderer.sharedMaterial = material;

        AtlasVariantDefinition atlasVariant = ResolveAtlasVariant(
            recipe.Region,
            recipe.VariantId,
            recipe.MaskMode);
        Texture2D probabilityAtlas = GetReferenceAtlasTexture(atlasVariant);
        Color materialColor = BuildMaterialColor(recipe);

        if (probabilityAtlas != null && material.HasProperty("_MaskTex"))
        {
            material.SetTexture("_MaskTex", probabilityAtlas);
        }

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
            material.SetFloat("_Threshold", atlasVariant != null ? atlasVariant.Threshold : 0.45f);
        }

        if (material.HasProperty("_Feather"))
        {
            material.SetFloat("_Feather", atlasVariant != null ? atlasVariant.FeatherUvNormalized : 2.0f / 512.0f);
        }

        if (material.HasProperty("_VisibilityAlpha"))
        {
            material.SetFloat("_VisibilityAlpha", 1.0f);
        }
    }

    private static Material GetOrCreateReferenceUvAlphaMaterial(
        RegionOverlayView view,
        string region)
    {
        if (view.ReferenceUvAlphaMaterial != null)
        {
            return view.ReferenceUvAlphaMaterial;
        }

        Material template = Resources.Load<Material>("E7ReferenceUvAlphaMaskMaterial");
        if (template != null)
        {
            view.ReferenceUvAlphaMaterial = new Material(template)
            {
                name = "E7 Reference UV Alpha " + region
            };
            ConfigureTransparentMaterial(view.ReferenceUvAlphaMaterial);
            return view.ReferenceUvAlphaMaterial;
        }

        Shader shader = Shader.Find("MakeupAR/E7ReferenceUvAlphaMask");
        if (shader == null)
        {
            shader = Shader.Find("Universal Render Pipeline/Unlit");
        }

        if (shader == null)
        {
            shader = Shader.Find("Standard");
        }

        view.ReferenceUvAlphaMaterial = new Material(shader)
        {
            name = "E7 Reference UV Alpha " + region
        };
        ConfigureTransparentMaterial(view.ReferenceUvAlphaMaterial);
        return view.ReferenceUvAlphaMaterial;
    }

    private static Color BuildMaterialColor(RegionRecipeState recipe)
    {
        float sampleAlphaScale = 1.0f;
        float brightnessScale = 1.0f;

        switch (recipe.TextureSample)
        {
            case "soft_blush":
                sampleAlphaScale = Mathf.Lerp(0.58f, 0.9f, recipe.Intensity);
                brightnessScale = 1.06f;
                break;
            case "shimmer_eye":
                sampleAlphaScale = Mathf.Lerp(0.72f, 1.0f, recipe.Intensity);
                brightnessScale = Mathf.Lerp(1.05f, 1.35f, recipe.Intensity);
                break;
            default:
                sampleAlphaScale = Mathf.Lerp(0.78f, 1.0f, recipe.Intensity);
                brightnessScale = 0.96f;
                break;
        }

        return new Color(
            Mathf.Clamp01(recipe.Color.r * brightnessScale),
            Mathf.Clamp01(recipe.Color.g * brightnessScale),
            Mathf.Clamp01(recipe.Color.b * brightnessScale),
            Mathf.Clamp01(recipe.Opacity * sampleAlphaScale));
    }

    private Texture2D GetOrCreateTextureSample(string textureSample, float feather)
    {
        string key = textureSample + ":" + Mathf.RoundToInt(Mathf.Clamp01(feather) * 100.0f).ToString(CultureInfo.InvariantCulture);
        if (sampleTextures.TryGetValue(key, out Texture2D cachedTexture))
        {
            return cachedTexture;
        }

        Texture2D texture = CreateTextureSample(textureSample, feather);
        sampleTextures[key] = texture;
        return texture;
    }

    private static Texture2D CreateTextureSample(string textureSample, float feather)
    {
        const int size = 64;
        Texture2D texture = new Texture2D(size, size, TextureFormat.RGBA32, false)
        {
            name = "E4 " + textureSample + " debug texture",
            wrapMode = TextureWrapMode.Repeat,
            filterMode = FilterMode.Bilinear
        };

        feather = Mathf.Clamp01(feather);

        for (int y = 0; y < size; y++)
        {
            for (int x = 0; x < size; x++)
            {
                texture.SetPixel(x, y, GetTextureSamplePixel(textureSample, x, y, size, feather));
            }
        }

        texture.Apply(false, true);
        return texture;
    }

    private static Color GetTextureSamplePixel(
        string textureSample,
        int x,
        int y,
        int size,
        float feather)
    {
        float u = (x + 0.5f) / size;
        float v = (y + 0.5f) / size;
        float distanceFromCenter = Vector2.Distance(new Vector2(u, v), new Vector2(0.5f, 0.5f));

        switch (textureSample)
        {
            case "soft_blush":
            {
                float softEdge = Mathf.Lerp(0.38f, 0.62f, feather);
                float alpha = Mathf.Clamp01(1.0f - distanceFromCenter / softEdge);
                float grain = 0.92f + 0.08f * Mathf.Sin((x * 0.43f) + (y * 0.31f));
                return new Color(grain, grain, grain, alpha);
            }
            case "shimmer_eye":
            {
                int hash = Mathf.Abs((x * 73856093) ^ (y * 19349663) ^ 0x5bd1e995);
                bool sparkle = hash % 17 == 0 || (x + y) % 23 == 0;
                float stripe = ((x + y) % 11) < 3 ? 0.18f : 0.0f;
                float value = sparkle ? 1.0f : 0.58f + stripe;
                float alpha = sparkle ? 1.0f : 0.62f;
                return new Color(value, Mathf.Clamp01(value * 0.92f + 0.08f), 1.0f, alpha);
            }
            default:
            {
                float stripe = (x % 10) < 2 ? 0.92f : 1.0f;
                float pore = ((x * 13 + y * 7) % 29) == 0 ? 0.95f : 1.0f;
                return new Color(stripe * pore, stripe * pore, stripe * pore, 1.0f);
            }
        }
    }

    private static void SetViewVisibility(RegionOverlayView view, bool showMesh, bool showFallback)
    {
        if (view.MeshRenderer != null)
        {
            view.MeshRenderer.enabled = showMesh;
        }

        foreach (MeshRenderer renderer in view.FallbackRenderers)
        {
            if (renderer != null)
            {
                renderer.enabled = showFallback;
            }
        }
    }

    private void HideAllOverlayViews()
    {
        foreach (FaceOverlayState faceState in overlays.Values)
        {
            foreach (RegionOverlayView view in faceState.Regions.Values)
            {
                SetViewVisibility(view, false, false);
            }
        }
    }

    private static void ApplyViewAlphaMultiplier(RegionOverlayView view, float alphaMultiplier)
    {
        ApplyMaterialAlphaMultiplier(view.MeshRenderer != null ? view.MeshRenderer.sharedMaterial : null, alphaMultiplier);

        foreach (MeshRenderer renderer in view.FallbackRenderers)
        {
            ApplyMaterialAlphaMultiplier(renderer != null ? renderer.sharedMaterial : null, alphaMultiplier);
        }
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

    private static Material CreateRegionMaterial(string region, Color color)
    {
        Shader shader = Shader.Find("Universal Render Pipeline/Unlit");
        if (shader == null)
        {
            shader = Shader.Find("Unlit/Color");
        }

        if (shader == null)
        {
            shader = Shader.Find("Standard");
        }

        Material material = new Material(shader)
        {
            name = "E3 " + region + " debug material"
        };
        ApplyMaterialColor(material, color);
        return material;
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

    private static void ApplyMaterialAppearance(
        Material material,
        Color color,
        Texture texture,
        string blendMode)
    {
        ApplyMaterialColor(material, color);

        if (texture != null)
        {
            if (material.HasProperty("_BaseMap"))
            {
                material.SetTexture("_BaseMap", texture);
            }

            if (material.HasProperty("_MainTex"))
            {
                material.SetTexture("_MainTex", texture);
            }
        }

        ApplyBlendMode(material, blendMode);
    }

    private static void ApplyBlendMode(Material material, string blendMode)
    {
        if (material == null)
        {
            return;
        }

        switch (string.IsNullOrWhiteSpace(blendMode) ? "normal" : blendMode.Trim().ToLowerInvariant())
        {
            case "multiply":
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.DstColor);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                }
                break;
            case "screen":
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.OneMinusDstColor);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.One);
                }
                break;
            default:
                if (material.HasProperty("_SrcBlend"))
                {
                    material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha);
                }

                if (material.HasProperty("_DstBlend"))
                {
                    material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha);
                }
                break;
        }
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

    private static RegionMaskMode NormalizeMaskMode(string rendererMode)
    {
        string candidate = string.IsNullOrWhiteSpace(rendererMode)
            ? "e3e4-baseline"
            : rendererMode.Trim().ToLowerInvariant();

        if (candidate == "e7-arface-authored-atlas" || candidate == "arface-authored-atlas" || candidate == "atlas")
        {
            return RegionMaskMode.E7ArFaceAuthoredAtlas;
        }

        if (candidate == "e7-reference-uv-alpha" || candidate == "arface-reference-uv-alpha" || candidate == "reference-uv-alpha" || candidate == "soft-uv")
        {
            return RegionMaskMode.E7ReferenceUvAlpha;
        }

        if (candidate == "e7-reference-uv-atlas" || candidate == "arface-reference-uv-atlas" || candidate == "reference-uv-atlas")
        {
            return RegionMaskMode.E7ReferenceUvAtlas;
        }

        if (candidate == "e7-arface-uv-candidate" || candidate == "e7-candidate" || candidate == "candidate")
        {
            return RegionMaskMode.E7ArFaceUvCandidate;
        }

        return RegionMaskMode.BaselineCentroid;
    }

    private static string FormatRendererMode(RegionMaskMode maskMode)
    {
        switch (maskMode)
        {
            case RegionMaskMode.E7ArFaceAuthoredAtlas:
                return "e7-arface-authored-atlas";
            case RegionMaskMode.E7ReferenceUvAtlas:
                return "e7-reference-uv-atlas";
            case RegionMaskMode.E7ReferenceUvAlpha:
                return "e7-reference-uv-alpha";
            case RegionMaskMode.E7ArFaceUvCandidate:
                return "e7-arface-uv-candidate";
            default:
                return "e3e4-baseline";
        }
    }

    private static string GetMaskSource(RegionMaskMode maskMode)
    {
        switch (maskMode)
        {
            case RegionMaskMode.E7ArFaceAuthoredAtlas:
                return "arface_authored_atlas_manual_vertex_labels";
            case RegionMaskMode.E7ReferenceUvAtlas:
                return "arface_reference_uv_atlas_probability";
            case RegionMaskMode.E7ReferenceUvAlpha:
                return "arface_reference_uv_atlas_shader_alpha";
            case RegionMaskMode.E7ArFaceUvCandidate:
                return "arface_mesh_uv_procedural_candidate";
            default:
                return "centroid_broad";
        }
    }

    private static string GetBoundaryRenderer(RegionMaskMode maskMode)
    {
        return maskMode == RegionMaskMode.E7ReferenceUvAlpha ? "shader_alpha" : "triangle_subset";
    }

    private static string NormalizeCandidateId(string candidateId, RegionMaskMode maskMode)
    {
        string candidate = string.IsNullOrWhiteSpace(candidateId)
            ? string.Empty
            : candidateId.Trim().ToLowerInvariant();

        if (maskMode == RegionMaskMode.E7ArFaceAuthoredAtlas)
        {
            return candidate == "arface-authored-atlas" ? candidate : "arface-authored-atlas";
        }

        if (maskMode == RegionMaskMode.E7ReferenceUvAtlas || maskMode == RegionMaskMode.E7ReferenceUvAlpha)
        {
            if (maskMode == RegionMaskMode.E7ReferenceUvAlpha)
            {
                return candidate == "arface-reference-uv-alpha" ? candidate : "arface-reference-uv-alpha";
            }

            return candidate == "arface-reference-uv-atlas" ? candidate : "arface-reference-uv-atlas";
        }

        if (maskMode == RegionMaskMode.E7ArFaceUvCandidate)
        {
            return candidate == "e7-procedural-arface-uv" ? candidate : "e7-procedural-arface-uv";
        }

        return "e3e4-baseline";
    }

    private static string NormalizeNonAtlasVariantId(string variantId, RegionMaskMode maskMode)
    {
        if (maskMode == RegionMaskMode.E7ArFaceUvCandidate)
        {
            return "procedural-v0";
        }

        return "baseline-v0";
    }

    private static bool IsAtlasMaskMode(RegionMaskMode maskMode)
    {
        return maskMode == RegionMaskMode.E7ArFaceAuthoredAtlas
            || maskMode == RegionMaskMode.E7ReferenceUvAtlas
            || maskMode == RegionMaskMode.E7ReferenceUvAlpha;
    }

    private static AtlasVariantDefinition ResolveAtlasVariant(
        string region,
        string variantId,
        RegionMaskMode maskMode)
    {
        if (maskMode == RegionMaskMode.E7ReferenceUvAtlas || maskMode == RegionMaskMode.E7ReferenceUvAlpha)
        {
            return ResolveReferenceAtlasVariant(region, variantId);
        }

        return ResolveAuthoredAtlasVariant(region, variantId);
    }

    private static AtlasVariantDefinition ResolveAuthoredAtlasVariant(string region, string variantId)
    {
        string normalizedRegion = NormalizeRegion(region);
        string normalizedVariant = string.IsNullOrWhiteSpace(variantId)
            ? string.Empty
            : variantId.Trim().ToLowerInvariant();

        switch (normalizedRegion)
        {
            case "lip":
                switch (normalizedVariant)
                {
                    case "lip-ring-v0-tight":
                        return CreateAtlasVariant("lip", "lip-ring-v0-tight", "lip_ring", 0.0f, -0.036f, 0.042f, 0.017f, 0.006f, 0.004f, 2, false);
                    case "lip-ring-v0-wide":
                        return CreateAtlasVariant("lip", "lip-ring-v0-wide", "lip_ring", 0.0f, -0.036f, 0.057f, 0.026f, 0.008f, 0.005f, 2, false);
                    default:
                        return CreateAtlasVariant("lip", "lip-ring-v0-balanced", "lip_ring", 0.0f, -0.036f, 0.050f, 0.022f, 0.007f, 0.005f, 2, false);
                }
            case "cheek":
                switch (normalizedVariant)
                {
                    case "cheek-soft-v0-high":
                        return CreateAtlasVariant("cheek", "cheek-soft-v0-high", "cheekbone_soft_cheek", 0.082f, 0.008f, 0.040f, 0.027f, 0.009f, 0.006f, 2, true);
                    case "cheek-soft-v0-wide":
                        return CreateAtlasVariant("cheek", "cheek-soft-v0-wide", "cheekbone_soft_cheek", 0.085f, -0.002f, 0.050f, 0.036f, 0.010f, 0.008f, 2, true);
                    default:
                        return CreateAtlasVariant("cheek", "cheek-soft-v0-balanced", "cheekbone_soft_cheek", 0.083f, -0.002f, 0.043f, 0.031f, 0.009f, 0.007f, 2, true);
                }
            case "eye":
                switch (normalizedVariant)
                {
                    case "eye-band-v0-tight":
                        return CreateAtlasVariant("eye", "eye-band-v0-tight", "eyelid_band", 0.047f, 0.045f, 0.034f, 0.014f, 0.006f, 0.004f, 2, true);
                    case "eye-band-v0-extended":
                        return CreateAtlasVariant("eye", "eye-band-v0-extended", "eyelid_band", 0.049f, 0.046f, 0.052f, 0.022f, 0.009f, 0.006f, 2, true);
                    default:
                        return CreateAtlasVariant("eye", "eye-band-v0-balanced", "eyelid_band", 0.047f, 0.045f, 0.043f, 0.018f, 0.008f, 0.005f, 2, true);
                }
            default:
                return ResolveAuthoredAtlasVariant("lip", "lip-ring-v0-balanced");
        }
    }

    private static AtlasVariantDefinition ResolveReferenceAtlasVariant(string region, string variantId)
    {
        string normalizedRegion = NormalizeRegion(region);
        string normalizedVariant = string.IsNullOrWhiteSpace(variantId)
            ? GetDefaultReferenceAtlasVariantId(normalizedRegion)
            : variantId.Trim().ToLowerInvariant();

        switch (normalizedRegion)
        {
            case "lip":
                switch (normalizedVariant)
                {
                    case "lip-uvref-v0-core":
                        return CreateReferenceAtlasVariant("lip", "lip-uvref-v0-core", "core", 0.55f, 1, "min", "sameFrameAtoAIou=0.9720;sameFrameBtoBIou=0.9693;crossFrameAtoBIou=0.8193;crossFrameBtoAIou=0.8325;uvCoreOverUnion=0.7046");
                    case "lip-uvref-v0-soft-wide":
                        return CreateReferenceAtlasVariant("lip", "lip-uvref-v0-soft-wide", "soft-wide", 0.35f, 4, "max", "sameFrameAtoAIou=0.9720;sameFrameBtoBIou=0.9693;crossFrameAtoBIou=0.8193;crossFrameBtoAIou=0.8325;uvCoreOverUnion=0.7046");
                    default:
                        return CreateReferenceAtlasVariant("lip", "lip-uvref-v0-balanced", "balanced", 0.45f, 2, "mean", "sameFrameAtoAIou=0.9720;sameFrameBtoBIou=0.9693;crossFrameAtoBIou=0.8193;crossFrameBtoAIou=0.8325;uvCoreOverUnion=0.7046");
                }
            case "cheek":
                switch (normalizedVariant)
                {
                    case "cheek-uvref-v0-core":
                        return CreateReferenceAtlasVariant("cheek", "cheek-uvref-v0-core", "core", 0.55f, 1, "min", "sameFrameAtoAIou=0.9912;sameFrameBtoBIou=0.9906;crossFrameAtoBIou=0.8363;crossFrameBtoAIou=0.8302;uvCoreOverUnion=0.7106");
                    case "cheek-uvref-v0-soft-wide":
                        return CreateReferenceAtlasVariant("cheek", "cheek-uvref-v0-soft-wide", "soft-wide", 0.35f, 4, "max", "sameFrameAtoAIou=0.9912;sameFrameBtoBIou=0.9906;crossFrameAtoBIou=0.8363;crossFrameBtoAIou=0.8302;uvCoreOverUnion=0.7106");
                    default:
                        return CreateReferenceAtlasVariant("cheek", "cheek-uvref-v0-balanced", "balanced", 0.45f, 2, "mean", "sameFrameAtoAIou=0.9912;sameFrameBtoBIou=0.9906;crossFrameAtoBIou=0.8363;crossFrameBtoAIou=0.8302;uvCoreOverUnion=0.7106");
                }
            case "eye":
                switch (normalizedVariant)
                {
                    case "eye-uvref-v0-core":
                        return CreateReferenceAtlasVariant("eye", "eye-uvref-v0-core", "core", 0.55f, 1, "min", "sameFrameAtoAIou=0.8604;sameFrameBtoBIou=0.8457;crossFrameAtoBIou=0.6948;crossFrameBtoAIou=0.7129;uvCoreOverUnion=0.8060");
                    case "eye-uvref-v0-soft-wide":
                        return CreateReferenceAtlasVariant("eye", "eye-uvref-v0-soft-wide", "soft-wide", 0.35f, 4, "max", "sameFrameAtoAIou=0.8604;sameFrameBtoBIou=0.8457;crossFrameAtoBIou=0.6948;crossFrameBtoAIou=0.7129;uvCoreOverUnion=0.8060");
                    default:
                        return CreateReferenceAtlasVariant("eye", "eye-uvref-v0-balanced", "balanced", 0.45f, 2, "mean", "sameFrameAtoAIou=0.8604;sameFrameBtoBIou=0.8457;crossFrameAtoBIou=0.6948;crossFrameBtoAIou=0.7129;uvCoreOverUnion=0.8060");
                }
            default:
                return ResolveReferenceAtlasVariant("lip", "lip-uvref-v0-balanced");
        }
    }

    private static string GetDefaultReferenceAtlasVariantId(string region)
    {
        switch (NormalizeRegion(region))
        {
            case "cheek":
                return "cheek-uvref-v0-balanced";
            case "eye":
                return "eye-uvref-v0-balanced";
            default:
                return "lip-uvref-v0-balanced";
        }
    }

    private static AtlasVariantDefinition CreateAtlasVariant(
        string region,
        string variantId,
        string labelGroup,
        float centerX,
        float centerY,
        float radiusX,
        float radiusY,
        float vertexPaddingX,
        float vertexPaddingY,
        int minVertexHits,
        bool mirrorX)
    {
        string configSummary = "shape=manual_ellipse"
            + ";region=" + region
            + ";labelGroup=" + labelGroup
            + ";centerX=" + centerX.ToString("0.###", CultureInfo.InvariantCulture)
            + ";centerY=" + centerY.ToString("0.###", CultureInfo.InvariantCulture)
            + ";radiusX=" + radiusX.ToString("0.###", CultureInfo.InvariantCulture)
            + ";radiusY=" + radiusY.ToString("0.###", CultureInfo.InvariantCulture)
            + ";vertexPaddingX=" + vertexPaddingX.ToString("0.###", CultureInfo.InvariantCulture)
            + ";vertexPaddingY=" + vertexPaddingY.ToString("0.###", CultureInfo.InvariantCulture)
            + ";minVertexHits=" + minVertexHits.ToString(CultureInfo.InvariantCulture)
            + ";mirrorX=" + mirrorX.ToString().ToLowerInvariant()
            + ";uvPolicy=preserve_arface_uvs";

        return new AtlasVariantDefinition
        {
            Region = region,
            VariantId = variantId,
            LabelGroup = labelGroup,
            ConfigSummary = configSummary,
            CenterX = centerX,
            CenterY = centerY,
            RadiusX = radiusX,
            RadiusY = radiusY,
            VertexPaddingX = vertexPaddingX,
            VertexPaddingY = vertexPaddingY,
            MinVertexHits = minVertexHits,
            MirrorX = mirrorX
        };
    }

    private static AtlasVariantDefinition CreateReferenceAtlasVariant(
        string region,
        string variantId,
        string labelGroup,
        float threshold,
        int featherUvPixels,
        string combineMode,
        string calibrationScoreSummary)
    {
        float featherUvNormalized = featherUvPixels / 512.0f;
        string resourcePath = "E7ReferenceAtlas/" + ReferenceAtlasVersion + "/" + variantId;
        string configSummary = "shape=reference_uv_probability"
            + ";region=" + region
            + ";labelGroup=" + labelGroup
            + ";sourceFastGate=fast-gate-20260622T160307Z"
            + ";combineMode=" + combineMode
            + ";threshold=" + threshold.ToString("0.###", CultureInfo.InvariantCulture)
            + ";featherUvPixels=" + featherUvPixels.ToString(CultureInfo.InvariantCulture)
            + ";featherUvNormalized=" + featherUvNormalized.ToString("0.######", CultureInfo.InvariantCulture)
            + ";uvResolution=512"
            + ";morphology=none"
            + ";resourcePath=" + resourcePath;

        return new AtlasVariantDefinition
        {
            Region = region,
            VariantId = variantId,
            LabelGroup = labelGroup,
            ConfigSummary = configSummary,
            IsReferenceUvAtlas = true,
            ProbabilityResourcePath = resourcePath,
            SourceFrameCount = 2,
            GoldMaskCount = 2,
            SilverReferenceCount = 0,
            UvResolution = 512,
            Threshold = threshold,
            FeatherUvPixels = featherUvPixels,
            FeatherUvNormalized = featherUvNormalized,
            CalibrationScoreSummary = calibrationScoreSummary,
            CombineMode = combineMode,
            Morphology = "none",
            PromotionReason = labelGroup == "core"
                ? "high-precision check"
                : labelGroup == "soft-wide"
                    ? "spill/coverage stress check"
                    : "default runtime candidate"
        };
    }

    private static void PopulateAtlasEvidence(
        ARFace face,
        RegionRecipeState recipe,
        ref RegionApplyResult result)
    {
        if (!IsAtlasMaskMode(recipe.MaskMode))
        {
            result.AtlasVersion = recipe.MaskMode == RegionMaskMode.E7ArFaceUvCandidate ? "procedural-v0" : "none";
            result.AtlasLabelMapVersion = "none";
            result.AtlasLabelGroup = "none";
            result.AtlasConfigSummary = "none";
            result.AtlasConfigHash = "none";
            result.TopologyAuditStatus = BuildTopologyAuditStatus(face);
            result.TopologyAuditSummary = BuildTopologyAuditSummary(face);
            result.AtlasVertexLabelSummary = "none";
            result.AtlasDataFallback = false;
            result.AtlasFallbackReason = "none";
            result.AtlasSourceFrameCount = 0;
            result.AtlasGoldMaskCount = 0;
            result.AtlasSilverReferenceCount = 0;
            result.AtlasUvResolution = 0;
            result.AtlasThreshold = 0.0f;
            result.AtlasFeatherUvPixels = 0;
            result.AtlasFeatherUvNormalized = 0.0f;
            result.AtlasCalibrationScoreSummary = "none";
            result.AtlasCombineMode = "none";
            result.AtlasMorphology = "none";
            return;
        }

        AtlasVariantDefinition atlasVariant = ResolveAtlasVariant(recipe.Region, recipe.VariantId, recipe.MaskMode);
        int labeledVertexCount = CountAtlasLabeledVertices(face, recipe.Region, atlasVariant);
        bool topologyReady = HasUsableUv(face)
            && GetVertexCount(face) > 0
            && GetIndexCount(face) >= 3
            && GetIndexCount(face) % 3 == 0;

        result.AtlasVersion = recipe.MaskMode == RegionMaskMode.E7ReferenceUvAtlas || recipe.MaskMode == RegionMaskMode.E7ReferenceUvAlpha
            ? ReferenceAtlasVersion
            : AtlasVersion;
        result.AtlasLabelMapVersion = recipe.MaskMode == RegionMaskMode.E7ReferenceUvAtlas || recipe.MaskMode == RegionMaskMode.E7ReferenceUvAlpha
            ? ReferenceAtlasLabelMapVersion
            : AtlasLabelMapVersion;
        result.AtlasLabelGroup = atlasVariant.LabelGroup;
        result.AtlasConfigSummary = atlasVariant.ConfigSummary;
        result.AtlasConfigHash = BuildStableConfigHash(result.AtlasVersion + "|" + result.AtlasLabelMapVersion + "|" + atlasVariant.VariantId + "|" + atlasVariant.ConfigSummary);
        result.TopologyAuditStatus = topologyReady ? "pass_uv_topology_ready" : BuildTopologyAuditStatus(face);
        result.TopologyAuditSummary = BuildTopologyAuditSummary(face);
        result.AtlasVertexLabelSummary = atlasVariant.IsReferenceUvAtlas
            ? "labelGroup=" + atlasVariant.LabelGroup
                + ";probabilityResourcePath=" + atlasVariant.ProbabilityResourcePath
                + ";threshold=" + atlasVariant.Threshold.ToString("0.###", CultureInfo.InvariantCulture)
            : "labelGroup=" + atlasVariant.LabelGroup
                + ";labeledVertices=" + labeledVertexCount.ToString(CultureInfo.InvariantCulture)
                + ";minVertexHits=" + atlasVariant.MinVertexHits.ToString(CultureInfo.InvariantCulture);
        result.AtlasDataFallback = string.IsNullOrWhiteSpace(recipe.VariantId)
            || recipe.VariantId != atlasVariant.VariantId
            || !topologyReady;
        result.AtlasFallbackReason = topologyReady
            ? (result.AtlasDataFallback ? "variant_defaulted" : "none")
            : "topology_or_uv_unavailable";
        result.VariantId = atlasVariant.VariantId;
        result.AtlasSourceFrameCount = atlasVariant.SourceFrameCount;
        result.AtlasGoldMaskCount = atlasVariant.GoldMaskCount;
        result.AtlasSilverReferenceCount = atlasVariant.SilverReferenceCount;
        result.AtlasUvResolution = atlasVariant.UvResolution;
        result.AtlasThreshold = atlasVariant.Threshold;
        result.AtlasFeatherUvPixels = atlasVariant.FeatherUvPixels;
        result.AtlasFeatherUvNormalized = atlasVariant.FeatherUvNormalized;
        result.AtlasCalibrationScoreSummary = string.IsNullOrWhiteSpace(atlasVariant.CalibrationScoreSummary)
            ? "none"
            : atlasVariant.CalibrationScoreSummary;
        result.AtlasCombineMode = string.IsNullOrWhiteSpace(atlasVariant.CombineMode)
            ? "none"
            : atlasVariant.CombineMode;
        result.AtlasMorphology = string.IsNullOrWhiteSpace(atlasVariant.Morphology)
            ? "none"
            : atlasVariant.Morphology;
    }

    private static int CountAtlasLabeledVertices(
        ARFace face,
        string region,
        AtlasVariantDefinition atlasVariant)
    {
        if (face == null || !face.vertices.IsCreated || atlasVariant == null)
        {
            return 0;
        }

        int count = 0;
        for (int index = 0; index < face.vertices.Length; index++)
        {
            if (IsManualAtlasVertexLabel(region, atlasVariant, face.vertices[index]))
            {
                count++;
            }
        }

        return count;
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

    private static string BuildStableConfigHash(string value)
    {
        unchecked
        {
            uint hash = 2166136261u;
            for (int index = 0; index < value.Length; index++)
            {
                hash ^= value[index];
                hash *= 16777619u;
            }

            return "fnv1a32-" + hash.ToString("x8", CultureInfo.InvariantCulture);
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
        const float limitedHoldSeconds = 0.35f;
        const float limitedFadeSeconds = 1.2f;
        float now = Time.unscaledTime;

        if (face.trackingState == TrackingState.Tracking)
        {
            bool recovered = state.WasLimitedOrLost;
            state.LastTrackedTime = now;
            state.WasLimitedOrLost = false;

            return new TrackingVisibility
            {
                ShouldRender = true,
                AlphaMultiplier = 1.0f,
                Action = recovered ? "recovered_restore" : "tracking_render"
            };
        }

        state.WasLimitedOrLost = true;
        float age = now - state.LastTrackedTime;
        string statePrefix = face.trackingState == TrackingState.Limited ? "limited" : "lost";

        if (age <= limitedHoldSeconds)
        {
            return new TrackingVisibility
            {
                ShouldRender = true,
                AlphaMultiplier = 0.72f,
                Action = statePrefix + "_short_hold"
            };
        }

        if (age <= limitedFadeSeconds)
        {
            return new TrackingVisibility
            {
                ShouldRender = true,
                AlphaMultiplier = 0.32f,
                Action = statePrefix + "_fade"
            };
        }

        return new TrackingVisibility
        {
            ShouldRender = false,
            AlphaMultiplier = 0.0f,
            Action = statePrefix + "_extended_hide"
        };
    }

    private static void MaybeLogE7RegionPrecisionState(
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
            "[E7] region_precision_state"
            + " rendererMode=" + recipe.RendererMode
            + " candidateId=" + recipe.CandidateId
            + " variantId=" + recipe.VariantId
            + " maskSource=" + GetMaskSource(recipe.MaskMode)
            + " region=" + region
            + " trackingState=" + face.trackingState
            + " stateAction=" + visibility.Action
            + " alphaMultiplier=" + visibility.AlphaMultiplier.ToString("0.##", CultureInfo.InvariantCulture)
            + " holdSeconds=0.35"
            + " fadeSeconds=1.2"
            + " uvAvailable=" + HasUsableUv(face).ToString().ToLowerInvariant()
            + " meshVertexCount=" + GetVertexCount(face).ToString(CultureInfo.InvariantCulture)
            + " meshIndexCount=" + GetIndexCount(face).ToString(CultureInfo.InvariantCulture)
            + " meshUvCount=" + GetUvCount(face).ToString(CultureInfo.InvariantCulture)
            + " topologyAuditStatus=" + BuildTopologyAuditStatus(face));
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

    private static string SanitizeLogValue(string value)
    {
        return string.IsNullOrWhiteSpace(value)
            ? "none"
            : value.Trim().Replace(" ", "_").Replace("\n", "_").Replace("\r", "_");
    }
}
