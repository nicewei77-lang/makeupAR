using System;
using System.Collections.Generic;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Collections;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.XR.ARFoundation;

public sealed class RNBridge : MonoBehaviour
{
    private static readonly string[] FeatureSnapshotRegions = { "lip", "cheek", "eye" };

    [Serializable]
    private sealed class RecipePayload
    {
        public int version;
        public string recipeId;
        public string lookId;
        public double sentAtMs;
        public string region;
        public string layer;
        public string color;
        public float opacity;
        public string texture;
        public string sample;
        public string textureMode;
        public float intensity;
        public float feather;
        public string blendMode;
        public string rendererMode;
        public string candidateId;
        public string variantId;
        public RecipeLayerPayload[] layers;
    }

    [Serializable]
    private sealed class RecipeLayerPayload
    {
        public string id;
        public string recipeId;
        public string lookId;
        public double sentAtMs;
        public string region;
        public string layer;
        public string color;
        public float opacity;
        public string texture;
        public string sample;
        public string textureMode;
        public float intensity;
        public float feather;
        public string blendMode;
        public string rendererMode;
        public string candidateId;
        public string variantId;
        public bool enabled;
    }

    [Serializable]
    private sealed class RecipeAckPayload
    {
        public string type;
        public string runId;
        public string phase;
        public string rendererMode;
        public string candidateId;
        public string variantId;
        public string lookId;
        public string recipeId;
        public string region;
        public string texture;
        public double sentAtMs;
        public double appliedAtMs;
        public int appliedFrame;
        public double receivedAtMs;
        public bool visualLatencyConfirmedByRecording;
        public string visualLatencyObservation;
    }

    [Serializable]
    private sealed class RegionOverlayVisibilityPayload
    {
        public bool visible = true;
        public string validationViewMode;
        public string reason;
    }

    private struct ParsedRecipeLayer
    {
        public string Id;
        public string Region;
        public string LegacyLayer;
        public string ColorHex;
        public Color Color;
        public float Opacity;
        public string RecipeId;
        public string LookId;
        public double SentAtMs;
        public string TextureSample;
        public string TextureMode;
        public float Intensity;
        public float Feather;
        public string BlendMode;
        public string RendererMode;
        public string CandidateId;
        public string VariantId;
        public bool Enabled;
    }

    private sealed class RegionFeatureState
    {
        public string Region = string.Empty;
        public bool Enabled;
        public bool Applied;
        public string ColorHex = string.Empty;
        public float Opacity;
        public string TextureSample = string.Empty;
        public string TextureMode = string.Empty;
        public string BlendMode = string.Empty;
        public float Intensity;
        public float Feather;
        public string RendererMode = "e3e4-baseline";
        public string CandidateId = "e3e4-baseline";
        public string VariantId = "baseline-v0";
        public string MaskSource = "centroid_broad";
        public string TrackingState = "None";
        public string StateAction = "not_started";
        public int BaselineTriangleCount;
        public int CandidateTriangleCount;
        public bool UvAvailable;
        public int MeshVertexCount;
        public int MeshIndexCount;
        public int MeshUvCount;
        public int FaceCount;
        public int MeshTriangleCount;
        public bool UsedFallback;
        public string AtlasVersion = "none";
        public string AtlasLabelMapVersion = "none";
        public string AtlasLabelGroup = "none";
        public string AtlasConfigSummary = "none";
        public string AtlasConfigHash = "none";
        public string TopologyAuditStatus = "not_run";
        public string TopologyAuditSummary = "none";
        public string AtlasVertexLabelSummary = "none";
        public bool AtlasDataFallback;
        public string AtlasFallbackReason = "none";
        public long LastUpdatedMs;
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private Material overlayMaterial;
    [SerializeField] private E7SynchronizedCaptureExporter referenceCaptureExporter;
    [SerializeField] private FaceTrackingStatusReporter statusReporter;

    private E3RegionMaskOverlay regionMaskOverlay;
    private readonly Dictionary<Renderer, bool> suppressedFaceRendererStates =
        new Dictionary<Renderer, bool>();
    private readonly Dictionary<string, RegionFeatureState> latestRegionFeatureStates =
        new Dictionary<string, RegionFeatureState>();
    private bool faceRenderersSuppressed;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern void sendMessageToMobileApp(string message);
#endif

    private void Awake()
    {
        RefreshSceneReferences();
        EnsureRegionMaskOverlay();
        EnsureReferenceCaptureExporter();

        if (overlayMaterial != null)
        {
            ApplyMaterialColor(overlayMaterial, new Color(1.0f, 1.0f, 1.0f, 0.06f));
        }
    }

    private IEnumerator Start()
    {
        yield return null;
        yield return new WaitForSeconds(0.25f);
        SendUnityEvent("{\"type\":\"unity_initialized\"}");
    }

    private void LateUpdate()
    {
        if (faceRenderersSuppressed)
        {
            ApplyFaceRendererSuppression();
        }
    }

    public void ApplyRecipeJson(string json)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                throw new ArgumentException("Recipe JSON is empty.");
            }

            RecipePayload recipe = JsonUtility.FromJson<RecipePayload>(json);
            if (recipe == null)
            {
                throw new ArgumentException("Recipe JSON did not parse into a payload.");
            }

            List<ParsedRecipeLayer> layers = ParseRecipeLayers(recipe);
            Debug.Log(
                "[E4] recipe_parse"
                + " version=" + recipe.version.ToString(CultureInfo.InvariantCulture)
                + " layerCount=" + layers.Count.ToString(CultureInfo.InvariantCulture)
                + " region=" + NormalizeOptional(recipe.region)
                + " texture=" + NormalizeOptional(recipe.texture)
                + " sample=" + NormalizeOptional(recipe.sample)
                + " textureMode=" + NormalizeOptional(recipe.textureMode)
                + " candidateId=" + NormalizeOptional(recipe.candidateId)
                + " variantId=" + NormalizeOptional(recipe.variantId)
                + " raw=" + json);

            foreach (ParsedRecipeLayer layer in layers)
            {
                Debug.Log(
                    "[E4] region_dispatch"
                    + " region=" + layer.Region
                    + " legacyLayer=" + layer.LegacyLayer
                    + " id=" + layer.Id
                    + " color=" + layer.ColorHex
                    + " opacity=" + layer.Opacity.ToString("0.##", CultureInfo.InvariantCulture)
                    + " texture=" + layer.TextureSample
                    + " textureMode=" + layer.TextureMode
                    + " blendMode=" + layer.BlendMode
                    + " rendererMode=" + layer.RendererMode
                    + " candidateId=" + layer.CandidateId
                    + " variantId=" + layer.VariantId
                    + " enabled=" + layer.Enabled.ToString().ToLowerInvariant());

                Debug.Log(
                    "[E4] texture_dispatch"
                    + " region=" + layer.Region
                    + " texture=" + layer.TextureSample
                    + " sample=" + layer.TextureSample
                    + " mode=" + layer.TextureMode
                    + " intensity=" + layer.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
                    + " feather=" + layer.Feather.ToString("0.##", CultureInfo.InvariantCulture)
                    + " blendMode=" + layer.BlendMode);

                E3RegionMaskOverlay.RegionApplyResult result = ApplyRegionLayer(layer);
                long appliedAtMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
                int appliedFrame = Time.frameCount;
                RememberRegionFeatureState(layer, result);
                LogRecipeApplied("message", layer, result, appliedAtMs, appliedFrame);
                SendRecipeAppliedEvent(layer, result, appliedAtMs, appliedFrame);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("[E4] recipe_parse_failed raw=" + json + " error=" + exception.Message);
        }
    }

    public void SendFaceDetectedEvent(
        bool tracked,
        int faceCount,
        int totalTrackables,
        string trackingStates)
    {
        SendUnityEvent(
            "{\"type\":\"face_detected\",\"tracked\":"
            + tracked.ToString().ToLowerInvariant()
            + ",\"faceCount\":"
            + faceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"totalTrackables\":"
            + totalTrackables.ToString(CultureInfo.InvariantCulture)
            + ",\"trackingStates\":\""
            + EscapeJsonString(trackingStates)
            + "\""
            + "}");
    }

    public void SendFaceLifecycleEvent(string json)
    {
        SendUnityEvent(json, "[E2]");
    }

    public void SendFaceFeatureSnapshotEvent(string json)
    {
        SendUnityEvent(json, "[E5]");
    }

    public void SendE7MetricSampleEvent(string json)
    {
        SendUnityEvent(json, "[E7]");
    }

    public void SendE7ReferenceCaptureEvent(string json)
    {
        SendUnityEvent(json, "[E7]");
    }

    public void SetE7RegionOverlayVisibleJson(string json)
    {
        try
        {
            RegionOverlayVisibilityPayload payload =
                JsonUtility.FromJson<RegionOverlayVisibilityPayload>(json);
            bool visible = payload == null || payload.visible;
            string validationViewMode = payload != null ? NormalizeOptional(payload.validationViewMode) : "unknown";
            bool unityDebugVisible = visible && validationViewMode == "full";

            EnsureRegionMaskOverlay();
            if (regionMaskOverlay == null)
            {
                throw new InvalidOperationException("E3 region mask overlay is unavailable.");
            }

            regionMaskOverlay.SetOverlayRenderingSuppressed(!visible);
            SetFaceRenderersSuppressed(!visible);

            if (statusReporter != null)
            {
                statusReporter.SetDebugOverlayVisible(unityDebugVisible);
            }

            Debug.Log(
                "[E7] region_overlay_visibility"
                + " visible=" + visible.ToString().ToLowerInvariant()
                + " faceRenderersSuppressed=" + (!visible).ToString().ToLowerInvariant()
                + " unityDebugVisible=" + unityDebugVisible.ToString().ToLowerInvariant()
                + " validationViewMode=" + validationViewMode
                + " reason=" + NormalizeOptional(payload != null ? payload.reason : string.Empty));
        }
        catch (Exception exception)
        {
            Debug.LogError("[E7] region_overlay_visibility_failed raw=" + json + " error=" + exception.Message);
        }
    }

    public void CaptureE7ReferenceFrameJson(string json)
    {
        try
        {
            EnsureReferenceCaptureExporter();

            if (referenceCaptureExporter == null)
            {
                throw new InvalidOperationException("E7 reference capture exporter is unavailable.");
            }

            referenceCaptureExporter.CaptureReferenceFrameJson(json);
        }
        catch (Exception exception)
        {
            Debug.LogError("[E7] reference_capture_request_failed raw=" + json + " error=" + exception.Message);
            SendE7ReferenceCaptureEvent(
                "{\"type\":\"e7_reference_capture\""
                + ",\"status\":\"failed\""
                + ",\"capturePairId\":\"pair_face_0001\""
                + ",\"regions\":[\"lip\",\"eye\",\"cheek\"]"
                + ",\"relativeDirectory\":\"\""
                + ",\"detail\":\""
                + EscapeJsonString(exception.Message)
                + "\""
                + ",\"meshVertexCount\":0"
                + ",\"meshIndexCount\":0"
                + ",\"meshUvCount\":0"
                + ",\"frameWidth\":0"
                + ",\"coordinateSpaceValidated\":false"
                + ",\"coordinateSpaceValidationStatus\":\"request_failed\""
                + "}");
        }
    }

    public void LogRecipeAck(string json)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(json))
            {
                throw new ArgumentException("Recipe ack JSON is empty.");
            }

            RecipeAckPayload ack = JsonUtility.FromJson<RecipeAckPayload>(json);
            if (ack == null)
            {
                throw new ArgumentException("Recipe ack JSON did not parse into a payload.");
            }

            double sendToAckLatencyMs = CalculateLatencyMs(ack.sentAtMs, ack.receivedAtMs);
            double unityApplyLatencyMs = CalculateLatencyMs(ack.sentAtMs, ack.appliedAtMs);
            double unityToRnReceiveLatencyMs = CalculateLatencyMs(ack.appliedAtMs, ack.receivedAtMs);

            Debug.Log(
                "[E7] recipe_latency"
                + " source=rn_ack"
                + " runId=" + NormalizeOptional(ack.runId)
                + " phase=" + NormalizeOptional(ack.phase)
                + " timestampMs=" + ack.receivedAtMs.ToString("0", CultureInfo.InvariantCulture)
                + " rendererMode=" + NormalizeOptional(ack.rendererMode)
                + " candidateId=" + NormalizeOptional(ack.candidateId)
                + " variantId=" + NormalizeOptional(ack.variantId)
                + " lookId=" + NormalizeOptional(ack.lookId)
                + " recipeId=" + NormalizeOptional(ack.recipeId)
                + " region=" + NormalizeOptional(ack.region)
                + " texture=" + NormalizeOptional(ack.texture)
                + " sentAtMs=" + ack.sentAtMs.ToString("0", CultureInfo.InvariantCulture)
                + " appliedAtMs=" + ack.appliedAtMs.ToString("0", CultureInfo.InvariantCulture)
                + " appliedFrame=" + ack.appliedFrame.ToString(CultureInfo.InvariantCulture)
                + " receivedAtMs=" + ack.receivedAtMs.ToString("0", CultureInfo.InvariantCulture)
                + " sendToAckLatencyMs=" + sendToAckLatencyMs.ToString("0", CultureInfo.InvariantCulture)
                + " unityApplyLatencyMs=" + unityApplyLatencyMs.ToString("0", CultureInfo.InvariantCulture)
                + " unityToRnReceiveLatencyMs=" + unityToRnReceiveLatencyMs.ToString("0", CultureInfo.InvariantCulture)
                + " visualLatencyConfirmedByRecording="
                + ack.visualLatencyConfirmedByRecording.ToString().ToLowerInvariant()
                + " visualLatencyObservation="
                + NormalizeOptional(ack.visualLatencyObservation));
        }
        catch (Exception exception)
        {
            Debug.LogError("[E7] recipe_latency_ack_failed raw=" + json + " error=" + exception.Message);
        }
    }

    public string BuildFaceFeatureRegionSnapshotJsonFragment()
    {
        string activeRegionSummary = BuildActiveRegionSummary();
        string appliedTextureSampleSummary = BuildAppliedTextureSampleSummary();

        return "\"activeRegions\":" + BuildActiveRegionsJson()
            + ",\"appliedTextureSamples\":" + BuildAppliedTextureSamplesJson()
            + ",\"activeRegionSummary\":\"" + EscapeJsonString(activeRegionSummary) + "\""
            + ",\"appliedTextureSampleSummary\":\"" + EscapeJsonString(appliedTextureSampleSummary) + "\""
            + ",\"regions\":" + BuildRegionsJson();
    }

    private void RefreshSceneReferences()
    {
        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
        }

        if (statusReporter == null)
        {
            statusReporter = FindFirstObjectByType<FaceTrackingStatusReporter>();
        }

        if (overlayMaterial == null && faceManager != null && faceManager.facePrefab != null)
        {
            MeshRenderer prefabRenderer = faceManager.facePrefab.GetComponentInChildren<MeshRenderer>(true);
            if (prefabRenderer != null)
            {
                overlayMaterial = prefabRenderer.sharedMaterial;
            }
        }
    }

    private void EnsureRegionMaskOverlay()
    {
        RefreshSceneReferences();

        if (regionMaskOverlay == null)
        {
            regionMaskOverlay = FindFirstObjectByType<E3RegionMaskOverlay>();
        }

        if (regionMaskOverlay == null)
        {
            regionMaskOverlay = gameObject.AddComponent<E3RegionMaskOverlay>();
        }

        regionMaskOverlay.Configure(faceManager);
    }

    private void EnsureReferenceCaptureExporter()
    {
        RefreshSceneReferences();

        if (referenceCaptureExporter == null)
        {
            referenceCaptureExporter = FindFirstObjectByType<E7SynchronizedCaptureExporter>();
        }

        if (referenceCaptureExporter == null)
        {
            referenceCaptureExporter = gameObject.AddComponent<E7SynchronizedCaptureExporter>();
        }

        referenceCaptureExporter.Configure(
            faceManager,
            Camera.main,
            statusReporter,
            this);
    }

    private void SetFaceRenderersSuppressed(bool suppressed)
    {
        RefreshSceneReferences();
        faceRenderersSuppressed = suppressed;

        if (suppressed)
        {
            ApplyFaceRendererSuppression();
            return;
        }

        foreach (KeyValuePair<Renderer, bool> entry in suppressedFaceRendererStates)
        {
            if (entry.Key != null)
            {
                entry.Key.enabled = entry.Value;
            }
        }

        suppressedFaceRendererStates.Clear();
    }

    private void ApplyFaceRendererSuppression()
    {
        if (faceManager == null)
        {
            return;
        }

        foreach (ARFace face in faceManager.trackables)
        {
            if (face == null)
            {
                continue;
            }

            Renderer[] renderers = face.GetComponentsInChildren<Renderer>(true);
            foreach (Renderer renderer in renderers)
            {
                if (renderer == null)
                {
                    continue;
                }

                if (!suppressedFaceRendererStates.ContainsKey(renderer))
                {
                    suppressedFaceRendererStates[renderer] = renderer.enabled;
                }

                renderer.enabled = false;
            }
        }
    }

    private E3RegionMaskOverlay.RegionApplyResult ApplyRegionLayer(ParsedRecipeLayer layer)
    {
        EnsureRegionMaskOverlay();

        return regionMaskOverlay.ApplyRegionRecipe(
            layer.Region,
            layer.ColorHex,
            layer.Color,
            layer.Opacity,
            layer.Enabled,
            layer.TextureSample,
            layer.TextureMode,
            layer.Intensity,
            layer.Feather,
            layer.BlendMode,
            layer.RendererMode,
            layer.CandidateId,
            layer.VariantId);
    }

    private void RememberRegionFeatureState(
        ParsedRecipeLayer layer,
        E3RegionMaskOverlay.RegionApplyResult result)
    {
        latestRegionFeatureStates[layer.Region] = new RegionFeatureState
        {
            Region = layer.Region,
            Enabled = layer.Enabled,
            Applied = result.Applied,
            ColorHex = layer.ColorHex,
            Opacity = layer.Opacity,
            TextureSample = result.TextureSample,
            TextureMode = result.TextureMode,
            BlendMode = result.BlendMode,
            Intensity = result.Intensity,
            Feather = result.Feather,
            RendererMode = result.RendererMode,
            CandidateId = result.CandidateId,
            VariantId = result.VariantId,
            MaskSource = result.MaskSource,
            TrackingState = result.TrackingState,
            StateAction = result.StateAction,
            BaselineTriangleCount = result.BaselineTriangleCount,
            CandidateTriangleCount = result.CandidateTriangleCount,
            UvAvailable = result.UvAvailable,
            MeshVertexCount = result.MeshVertexCount,
            MeshIndexCount = result.MeshIndexCount,
            MeshUvCount = result.MeshUvCount,
            FaceCount = result.FaceCount,
            MeshTriangleCount = result.MeshTriangleCount,
            UsedFallback = result.UsedFallback,
            AtlasVersion = result.AtlasVersion,
            AtlasLabelMapVersion = result.AtlasLabelMapVersion,
            AtlasLabelGroup = result.AtlasLabelGroup,
            AtlasConfigSummary = result.AtlasConfigSummary,
            AtlasConfigHash = result.AtlasConfigHash,
            TopologyAuditStatus = result.TopologyAuditStatus,
            TopologyAuditSummary = result.TopologyAuditSummary,
            AtlasVertexLabelSummary = result.AtlasVertexLabelSummary,
            AtlasDataFallback = result.AtlasDataFallback,
            AtlasFallbackReason = result.AtlasFallbackReason,
            LastUpdatedMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()
        };
    }

    private void RefreshLatestOverlayRegionResults()
    {
        if (regionMaskOverlay == null)
        {
            return;
        }

        foreach (string region in FeatureSnapshotRegions)
        {
            if (!latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                || !state.Enabled
                || !regionMaskOverlay.TryGetLatestRegionApplyResult(region, out E3RegionMaskOverlay.RegionApplyResult result))
            {
                continue;
            }

            state.Applied = result.Applied;
            state.TextureSample = result.TextureSample;
            state.TextureMode = result.TextureMode;
            state.BlendMode = result.BlendMode;
            state.Intensity = result.Intensity;
            state.Feather = result.Feather;
            state.RendererMode = result.RendererMode;
            state.CandidateId = result.CandidateId;
            state.VariantId = result.VariantId;
            state.MaskSource = result.MaskSource;
            state.TrackingState = result.TrackingState;
            state.StateAction = result.StateAction;
            state.BaselineTriangleCount = result.BaselineTriangleCount;
            state.CandidateTriangleCount = result.CandidateTriangleCount;
            state.UvAvailable = result.UvAvailable;
            state.MeshVertexCount = result.MeshVertexCount;
            state.MeshIndexCount = result.MeshIndexCount;
            state.MeshUvCount = result.MeshUvCount;
            state.FaceCount = result.FaceCount;
            state.MeshTriangleCount = result.MeshTriangleCount;
            state.UsedFallback = result.UsedFallback;
            state.AtlasVersion = result.AtlasVersion;
            state.AtlasLabelMapVersion = result.AtlasLabelMapVersion;
            state.AtlasLabelGroup = result.AtlasLabelGroup;
            state.AtlasConfigSummary = result.AtlasConfigSummary;
            state.AtlasConfigHash = result.AtlasConfigHash;
            state.TopologyAuditStatus = result.TopologyAuditStatus;
            state.TopologyAuditSummary = result.TopologyAuditSummary;
            state.AtlasVertexLabelSummary = result.AtlasVertexLabelSummary;
            state.AtlasDataFallback = result.AtlasDataFallback;
            state.AtlasFallbackReason = result.AtlasFallbackReason;
        }
    }

    private string BuildActiveRegionSummary()
    {
        RefreshLatestOverlayRegionResults();

        List<string> activeRegions = new List<string>();
        foreach (string region in FeatureSnapshotRegions)
        {
            if (latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                && state.Enabled)
            {
                activeRegions.Add(region);
            }
        }

        return activeRegions.Count == 0 ? "none" : string.Join(",", activeRegions);
    }

    private string BuildAppliedTextureSampleSummary()
    {
        RefreshLatestOverlayRegionResults();

        List<string> appliedSamples = new List<string>();
        foreach (string region in FeatureSnapshotRegions)
        {
            if (latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                && state.Enabled)
            {
                appliedSamples.Add(region + ":" + state.TextureSample + ":applied=" + state.Applied.ToString().ToLowerInvariant());
            }
        }

        return appliedSamples.Count == 0 ? "none" : string.Join(",", appliedSamples);
    }

    private string BuildActiveRegionsJson()
    {
        RefreshLatestOverlayRegionResults();

        List<string> activeRegions = new List<string>();
        foreach (string region in FeatureSnapshotRegions)
        {
            if (latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                && state.Enabled)
            {
                activeRegions.Add("\"" + EscapeJsonString(region) + "\"");
            }
        }

        return "[" + string.Join(",", activeRegions) + "]";
    }

    private string BuildAppliedTextureSamplesJson()
    {
        RefreshLatestOverlayRegionResults();

        List<string> samples = new List<string>();
        foreach (string region in FeatureSnapshotRegions)
        {
            if (!latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                || !state.Enabled)
            {
                continue;
            }

            samples.Add("{"
                + "\"region\":\"" + EscapeJsonString(region) + "\""
                + ",\"texture\":\"" + EscapeJsonString(state.TextureSample) + "\""
                + ",\"sample\":\"" + EscapeJsonString(state.TextureSample) + "\""
                + ",\"textureMode\":\"" + EscapeJsonString(state.TextureMode) + "\""
                + ",\"blendMode\":\"" + EscapeJsonString(state.BlendMode) + "\""
                + ",\"rendererMode\":\"" + EscapeJsonString(state.RendererMode) + "\""
                + ",\"candidateId\":\"" + EscapeJsonString(state.CandidateId) + "\""
                + ",\"variantId\":\"" + EscapeJsonString(state.VariantId) + "\""
                + ",\"maskSource\":\"" + EscapeJsonString(state.MaskSource) + "\""
                + ",\"trackingState\":\"" + EscapeJsonString(state.TrackingState) + "\""
                + ",\"stateAction\":\"" + EscapeJsonString(state.StateAction) + "\""
                + ",\"intensity\":" + state.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
                + ",\"feather\":" + state.Feather.ToString("0.##", CultureInfo.InvariantCulture)
                + ",\"applied\":" + state.Applied.ToString().ToLowerInvariant()
                + ",\"faceCount\":" + state.FaceCount.ToString(CultureInfo.InvariantCulture)
                + ",\"meshTriangles\":" + state.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
                + ",\"baselineTriangles\":" + state.BaselineTriangleCount.ToString(CultureInfo.InvariantCulture)
                + ",\"candidateTriangles\":" + state.CandidateTriangleCount.ToString(CultureInfo.InvariantCulture)
                + ",\"uvAvailable\":" + state.UvAvailable.ToString().ToLowerInvariant()
                + ",\"meshVertexCount\":" + state.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
                + ",\"meshIndexCount\":" + state.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
                + ",\"meshUvCount\":" + state.MeshUvCount.ToString(CultureInfo.InvariantCulture)
                + ",\"usedFallback\":" + state.UsedFallback.ToString().ToLowerInvariant()
                + ",\"atlasVersion\":\"" + EscapeJsonString(state.AtlasVersion) + "\""
                + ",\"atlasLabelMapVersion\":\"" + EscapeJsonString(state.AtlasLabelMapVersion) + "\""
                + ",\"atlasLabelGroup\":\"" + EscapeJsonString(state.AtlasLabelGroup) + "\""
                + ",\"atlasConfigSummary\":\"" + EscapeJsonString(state.AtlasConfigSummary) + "\""
                + ",\"atlasConfigHash\":\"" + EscapeJsonString(state.AtlasConfigHash) + "\""
                + ",\"topologyAuditStatus\":\"" + EscapeJsonString(state.TopologyAuditStatus) + "\""
                + ",\"topologyAuditSummary\":\"" + EscapeJsonString(state.TopologyAuditSummary) + "\""
                + ",\"atlasVertexLabelSummary\":\"" + EscapeJsonString(state.AtlasVertexLabelSummary) + "\""
                + ",\"atlasDataFallback\":" + state.AtlasDataFallback.ToString().ToLowerInvariant()
                + ",\"atlasFallbackReason\":\"" + EscapeJsonString(state.AtlasFallbackReason) + "\""
                + "}");
        }

        return "[" + string.Join(",", samples) + "]";
    }

    private string BuildRegionsJson()
    {
        RefreshLatestOverlayRegionResults();

        List<string> regions = new List<string>();
        foreach (string region in FeatureSnapshotRegions)
        {
            latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state);
            bool active = state != null && state.Enabled;
            string textureSample = state != null && !string.IsNullOrWhiteSpace(state.TextureSample)
                ? state.TextureSample
                : GetDefaultTextureSample(region);
            string textureMode = state != null && !string.IsNullOrWhiteSpace(state.TextureMode)
                ? state.TextureMode
                : "sample";
            string rendererMode = state != null && !string.IsNullOrWhiteSpace(state.RendererMode)
                ? state.RendererMode
                : "e3e4-baseline";
            string candidateId = state != null && !string.IsNullOrWhiteSpace(state.CandidateId)
                ? state.CandidateId
                : GetCandidateIdForRenderer(rendererMode);
            string variantId = state != null && !string.IsNullOrWhiteSpace(state.VariantId)
                ? state.VariantId
                : GetDefaultVariantId(region, rendererMode);
            string maskSource = state != null && !string.IsNullOrWhiteSpace(state.MaskSource)
                ? state.MaskSource
                : "centroid_broad";
            string qaStatus = IsRegionPrecisionRenderer(rendererMode)
                ? "yellow_pending_real_device_visual_review"
                : "green_validation_baseline";

            regions.Add("\"" + EscapeJsonString(region) + "\":{"
                + "\"available\":true"
                + ",\"active\":" + active.ToString().ToLowerInvariant()
                + ",\"lastApplied\":" + (state != null && state.Applied).ToString().ToLowerInvariant()
                + ",\"rendererMode\":\"" + EscapeJsonString(rendererMode) + "\""
                + ",\"candidateId\":\"" + EscapeJsonString(candidateId) + "\""
                + ",\"variantId\":\"" + EscapeJsonString(variantId) + "\""
                + ",\"maskSource\":\"" + EscapeJsonString(maskSource) + "\""
                + ",\"qaStatus\":\"" + EscapeJsonString(qaStatus) + "\""
                + ",\"validationScope\":\"debug\""
                + ",\"texture\":\"" + EscapeJsonString(textureSample) + "\""
                + ",\"sample\":\"" + EscapeJsonString(textureSample) + "\""
                + ",\"textureMode\":\"" + EscapeJsonString(textureMode) + "\""
                + ",\"meshTriangles\":" + (state != null ? state.MeshTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
                + ",\"baselineTriangles\":" + (state != null ? state.BaselineTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
                + ",\"candidateTriangles\":" + (state != null ? state.CandidateTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
                + ",\"uvAvailable\":" + (state != null && state.UvAvailable).ToString().ToLowerInvariant()
                + ",\"usedFallback\":" + (state != null && state.UsedFallback).ToString().ToLowerInvariant()
                + ",\"atlasVersion\":\"" + EscapeJsonString(state != null ? state.AtlasVersion : "none") + "\""
                + ",\"atlasLabelMapVersion\":\"" + EscapeJsonString(state != null ? state.AtlasLabelMapVersion : "none") + "\""
                + ",\"atlasLabelGroup\":\"" + EscapeJsonString(state != null ? state.AtlasLabelGroup : "none") + "\""
                + ",\"atlasConfigHash\":\"" + EscapeJsonString(state != null ? state.AtlasConfigHash : "none") + "\""
                + ",\"topologyAuditStatus\":\"" + EscapeJsonString(state != null ? state.TopologyAuditStatus : "not_run") + "\""
                + ",\"atlasVertexLabelSummary\":\"" + EscapeJsonString(state != null ? state.AtlasVertexLabelSummary : "none") + "\""
                + ",\"atlasDataFallback\":" + (state != null && state.AtlasDataFallback).ToString().ToLowerInvariant()
                + ",\"atlasFallbackReason\":\"" + EscapeJsonString(state != null ? state.AtlasFallbackReason : "none") + "\""
                + ",\"lastUpdatedMs\":" + (state != null ? state.LastUpdatedMs : 0L).ToString(CultureInfo.InvariantCulture)
                + "}");
        }

        return "{" + string.Join(",", regions) + "}";
    }

    public string BuildE7BaselineStateLogFields()
    {
        RefreshLatestOverlayRegionResults();

        RegionFeatureState state = GetLatestActiveRegionFeatureState();
        string region = state != null ? state.Region : "none";
        string activeRegions = BuildActiveRegionSummary();
        string textureSample = state != null && !string.IsNullOrWhiteSpace(state.TextureSample)
            ? state.TextureSample
            : "none";
        string colorHex = state != null && !string.IsNullOrWhiteSpace(state.ColorHex)
            ? state.ColorHex
            : "none";
        float opacity = state != null ? state.Opacity : 0.0f;
        string rendererMode = state != null && !string.IsNullOrWhiteSpace(state.RendererMode)
            ? state.RendererMode
            : "e3e4-baseline";
        string candidateId = state != null && !string.IsNullOrWhiteSpace(state.CandidateId)
            ? state.CandidateId
            : GetCandidateIdForRenderer(rendererMode);
        string variantId = state != null && !string.IsNullOrWhiteSpace(state.VariantId)
            ? state.VariantId
            : GetDefaultVariantId(region, rendererMode);
        string lookId = IsRegionPrecisionRenderer(rendererMode)
            ? "e7_region_precision_debug"
            : "baseline_debug_mask";

        return " rendererMode=" + rendererMode
            + " candidateId=" + candidateId
            + " variantId=" + variantId
            + " lookId=" + lookId
            + " region=" + region
            + " activeRegions=" + activeRegions
            + " texture=" + textureSample
            + " sample=" + textureSample
            + " color=" + colorHex
            + " opacity=" + opacity.ToString("0.##", CultureInfo.InvariantCulture)
            + " maskSource=" + (state != null ? state.MaskSource : "centroid_broad")
            + " regionPrecisionStatus=" + (IsRegionPrecisionRenderer(rendererMode) ? "yellow_pending_real_device_visual_review" : "baseline_preserved")
            + " regionTrackingState=" + (state != null ? state.TrackingState : "None")
            + " regionStateAction=" + (state != null ? state.StateAction : "not_started")
            + " regionUvAvailable=" + (state != null && state.UvAvailable).ToString().ToLowerInvariant()
            + " regionBaselineTriangles=" + (state != null ? state.BaselineTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + " regionCandidateTriangles=" + (state != null ? state.CandidateTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + " regionAppliedTriangles=" + (state != null ? state.MeshTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + " atlasVersion=" + (state != null ? state.AtlasVersion : "none")
            + " atlasLabelMapVersion=" + (state != null ? state.AtlasLabelMapVersion : "none")
            + " atlasLabelGroup=" + (state != null ? state.AtlasLabelGroup : "none")
            + " atlasConfigHash=" + (state != null ? state.AtlasConfigHash : "none")
            + " topologyAuditStatus=" + (state != null ? state.TopologyAuditStatus : "not_run")
            + " topologyAuditSummary=" + SanitizeLogValue(state != null ? state.TopologyAuditSummary : "none")
            + " atlasVertexLabelSummary=" + SanitizeLogValue(state != null ? state.AtlasVertexLabelSummary : "none")
            + " atlasDataFallback=" + (state != null && state.AtlasDataFallback).ToString().ToLowerInvariant()
            + " atlasFallbackReason=" + (state != null ? state.AtlasFallbackReason : "none");
    }

    public string BuildE7BaselineStateJsonFragment()
    {
        RefreshLatestOverlayRegionResults();

        RegionFeatureState state = GetLatestActiveRegionFeatureState();
        string region = state != null ? state.Region : "none";
        string activeRegions = BuildActiveRegionSummary();
        string textureSample = state != null && !string.IsNullOrWhiteSpace(state.TextureSample)
            ? state.TextureSample
            : "none";
        string colorHex = state != null && !string.IsNullOrWhiteSpace(state.ColorHex)
            ? state.ColorHex
            : "none";
        float opacity = state != null ? state.Opacity : 0.0f;
        string rendererMode = state != null && !string.IsNullOrWhiteSpace(state.RendererMode)
            ? state.RendererMode
            : "e3e4-baseline";
        string candidateId = state != null && !string.IsNullOrWhiteSpace(state.CandidateId)
            ? state.CandidateId
            : GetCandidateIdForRenderer(rendererMode);
        string variantId = state != null && !string.IsNullOrWhiteSpace(state.VariantId)
            ? state.VariantId
            : GetDefaultVariantId(region, rendererMode);
        string lookId = IsRegionPrecisionRenderer(rendererMode)
            ? "e7_region_precision_debug"
            : "baseline_debug_mask";

        return "\"rendererMode\":\"" + EscapeJsonString(rendererMode) + "\""
            + ",\"candidateId\":\"" + EscapeJsonString(candidateId) + "\""
            + ",\"variantId\":\"" + EscapeJsonString(variantId) + "\""
            + ",\"lookId\":\"" + EscapeJsonString(lookId) + "\""
            + ",\"region\":\"" + EscapeJsonString(region) + "\""
            + ",\"activeRegions\":\"" + EscapeJsonString(activeRegions) + "\""
            + ",\"texture\":\"" + EscapeJsonString(textureSample) + "\""
            + ",\"sample\":\"" + EscapeJsonString(textureSample) + "\""
            + ",\"color\":\"" + EscapeJsonString(colorHex) + "\""
            + ",\"opacity\":" + opacity.ToString("0.##", CultureInfo.InvariantCulture)
            + ",\"maskSource\":\"" + EscapeJsonString(state != null ? state.MaskSource : "centroid_broad") + "\""
            + ",\"regionPrecisionStatus\":\"" + EscapeJsonString(IsRegionPrecisionRenderer(rendererMode) ? "yellow_pending_real_device_visual_review" : "baseline_preserved") + "\""
            + ",\"regionTrackingState\":\"" + EscapeJsonString(state != null ? state.TrackingState : "None") + "\""
            + ",\"regionStateAction\":\"" + EscapeJsonString(state != null ? state.StateAction : "not_started") + "\""
            + ",\"regionUvAvailable\":" + (state != null && state.UvAvailable).ToString().ToLowerInvariant()
            + ",\"regionBaselineTriangles\":" + (state != null ? state.BaselineTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"regionCandidateTriangles\":" + (state != null ? state.CandidateTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"regionAppliedTriangles\":" + (state != null ? state.MeshTriangleCount : 0).ToString(CultureInfo.InvariantCulture)
            + ",\"atlasVersion\":\"" + EscapeJsonString(state != null ? state.AtlasVersion : "none") + "\""
            + ",\"atlasLabelMapVersion\":\"" + EscapeJsonString(state != null ? state.AtlasLabelMapVersion : "none") + "\""
            + ",\"atlasLabelGroup\":\"" + EscapeJsonString(state != null ? state.AtlasLabelGroup : "none") + "\""
            + ",\"atlasConfigSummary\":\"" + EscapeJsonString(state != null ? state.AtlasConfigSummary : "none") + "\""
            + ",\"atlasConfigHash\":\"" + EscapeJsonString(state != null ? state.AtlasConfigHash : "none") + "\""
            + ",\"topologyAuditStatus\":\"" + EscapeJsonString(state != null ? state.TopologyAuditStatus : "not_run") + "\""
            + ",\"topologyAuditSummary\":\"" + EscapeJsonString(state != null ? state.TopologyAuditSummary : "none") + "\""
            + ",\"atlasVertexLabelSummary\":\"" + EscapeJsonString(state != null ? state.AtlasVertexLabelSummary : "none") + "\""
            + ",\"atlasDataFallback\":" + (state != null && state.AtlasDataFallback).ToString().ToLowerInvariant()
            + ",\"atlasFallbackReason\":\"" + EscapeJsonString(state != null ? state.AtlasFallbackReason : "none") + "\"";
    }

    public string GetE7MetricPhase()
    {
        RefreshLatestOverlayRegionResults();

        RegionFeatureState state = GetLatestActiveRegionFeatureState();
        if (state != null && state.RendererMode == "e7-arface-authored-atlas")
        {
            return "region_precision_atlas";
        }

        return state != null && state.RendererMode == "e7-arface-uv-candidate"
            ? "region_precision"
            : "baseline";
    }

    private RegionFeatureState GetLatestActiveRegionFeatureState()
    {
        RegionFeatureState latest = null;
        foreach (string region in FeatureSnapshotRegions)
        {
            if (!latestRegionFeatureStates.TryGetValue(region, out RegionFeatureState state)
                || !state.Enabled)
            {
                continue;
            }

            if (latest == null || state.LastUpdatedMs > latest.LastUpdatedMs)
            {
                latest = state;
            }
        }

        return latest;
    }

    private void LogRecipeApplied(
        string source,
        ParsedRecipeLayer layer,
        E3RegionMaskOverlay.RegionApplyResult result,
        long appliedAtMs,
        int appliedFrame)
    {
        string applied = result.Applied ? "true" : "false";
        string phase = GetPhaseForRenderer(layer.RendererMode);
        string runId = GetRunIdForRenderer(layer.RendererMode);
        string visualLatencyObservation = IsRegionPrecisionRenderer(layer.RendererMode)
            ? "pending_region_precision_visual_review"
            : "pending_recording_review";
        Debug.Log(
            "[E4] recipe_applied"
            + " source=" + source
            + " region=" + layer.Region
            + " legacyLayer=" + layer.LegacyLayer
            + " texture=" + layer.TextureSample
            + " appliedTexture=" + result.TextureSample
            + " textureMode=" + layer.TextureMode
            + " intensity=" + layer.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
            + " feather=" + layer.Feather.ToString("0.##", CultureInfo.InvariantCulture)
            + " blendMode=" + layer.BlendMode
            + " color=" + layer.ColorHex
            + " opacity=" + layer.Opacity.ToString("0.##", CultureInfo.InvariantCulture)
            + " applied=" + applied
            + " appliedRegion=" + result.Region
            + " rendererMode=" + result.RendererMode
            + " candidateId=" + result.CandidateId
            + " variantId=" + result.VariantId
            + " maskSource=" + result.MaskSource
            + " trackingState=" + result.TrackingState
            + " stateAction=" + result.StateAction
            + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " baselineTriangles=" + result.BaselineTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " candidateTriangles=" + result.CandidateTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " uvAvailable=" + result.UvAvailable.ToString().ToLowerInvariant()
            + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant()
            + " atlasVersion=" + result.AtlasVersion
            + " atlasLabelMapVersion=" + result.AtlasLabelMapVersion
            + " atlasLabelGroup=" + result.AtlasLabelGroup
            + " atlasConfigHash=" + result.AtlasConfigHash
            + " topologyAuditStatus=" + result.TopologyAuditStatus
            + " topologyAuditSummary=" + SanitizeLogValue(result.TopologyAuditSummary)
            + " atlasVertexLabelSummary=" + SanitizeLogValue(result.AtlasVertexLabelSummary)
            + " atlasDataFallback=" + result.AtlasDataFallback.ToString().ToLowerInvariant()
            + " atlasFallbackReason=" + result.AtlasFallbackReason);

        Debug.Log(
            "[E7] recipe_latency"
            + " source=unity_applied"
            + " runId=" + runId
            + " phase=" + phase
            + " timestampMs=" + appliedAtMs.ToString(CultureInfo.InvariantCulture)
            + " rendererMode=" + result.RendererMode
            + " candidateId=" + result.CandidateId
            + " variantId=" + result.VariantId
            + " lookId=" + layer.LookId
            + " recipeId=" + layer.RecipeId
            + " region=" + layer.Region
            + " texture=" + layer.TextureSample
            + " sentAtMs=" + layer.SentAtMs.ToString("0", CultureInfo.InvariantCulture)
            + " appliedAtMs=" + appliedAtMs.ToString(CultureInfo.InvariantCulture)
            + " appliedFrame=" + appliedFrame.ToString(CultureInfo.InvariantCulture)
            + " receivedAtMs=0"
            + " sendToAckLatencyMs=0"
            + " visualLatencyConfirmedByRecording=false"
            + " visualLatencyObservation=" + visualLatencyObservation
            + " atlasConfigHash=" + result.AtlasConfigHash
            + " topologyAuditStatus=" + result.TopologyAuditStatus);
    }

    private void SendRecipeAppliedEvent(
        ParsedRecipeLayer layer,
        E3RegionMaskOverlay.RegionApplyResult result,
        long appliedAtMs,
        int appliedFrame)
    {
        SendUnityEvent(
            "{\"type\":\"recipe_applied\",\"region\":\""
            + EscapeJsonString(layer.Region)
            + "\",\"layer\":\""
            + EscapeJsonString(layer.LegacyLayer)
            + "\",\"appliedRegion\":\""
            + EscapeJsonString(result.Region)
            + "\",\"texture\":\""
            + EscapeJsonString(layer.TextureSample)
            + "\",\"sample\":\""
            + EscapeJsonString(layer.TextureSample)
            + "\",\"appliedTexture\":\""
            + EscapeJsonString(result.TextureSample)
            + "\",\"textureMode\":\""
            + EscapeJsonString(layer.TextureMode)
            + "\",\"blendMode\":\""
            + EscapeJsonString(layer.BlendMode)
            + "\",\"applied\":"
            + result.Applied.ToString().ToLowerInvariant()
            + ",\"rendererMode\":\""
            + EscapeJsonString(result.RendererMode)
            + "\",\"candidateId\":\""
            + EscapeJsonString(result.CandidateId)
            + "\",\"variantId\":\""
            + EscapeJsonString(result.VariantId)
            + "\",\"runId\":\""
            + EscapeJsonString(GetRunIdForRenderer(layer.RendererMode))
            + "\",\"phase\":\""
            + EscapeJsonString(GetPhaseForRenderer(layer.RendererMode))
            + "\",\"maskSource\":\""
            + EscapeJsonString(result.MaskSource)
            + "\",\"trackingState\":\""
            + EscapeJsonString(result.TrackingState)
            + "\",\"stateAction\":\""
            + EscapeJsonString(result.StateAction)
            + "\",\"lookId\":\""
            + EscapeJsonString(layer.LookId)
            + "\",\"recipeId\":\""
            + EscapeJsonString(layer.RecipeId)
            + "\",\"sentAtMs\":"
            + layer.SentAtMs.ToString("0", CultureInfo.InvariantCulture)
            + ",\"appliedAtMs\":"
            + appliedAtMs.ToString(CultureInfo.InvariantCulture)
            + ",\"appliedFrame\":"
            + appliedFrame.ToString(CultureInfo.InvariantCulture)
            + ",\"visualLatencyConfirmedByRecording\":false"
            + ",\"visualLatencyObservation\":\""
            + EscapeJsonString(IsRegionPrecisionRenderer(result.RendererMode)
                ? "pending_region_precision_visual_review"
                : "pending_recording_review")
            + "\""
            + ",\"faceCount\":"
            + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"meshTriangles\":"
            + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"baselineTriangles\":"
            + result.BaselineTriangleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"candidateTriangles\":"
            + result.CandidateTriangleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"uvAvailable\":"
            + result.UvAvailable.ToString().ToLowerInvariant()
            + ",\"meshVertexCount\":"
            + result.MeshVertexCount.ToString(CultureInfo.InvariantCulture)
            + ",\"meshIndexCount\":"
            + result.MeshIndexCount.ToString(CultureInfo.InvariantCulture)
            + ",\"meshUvCount\":"
            + result.MeshUvCount.ToString(CultureInfo.InvariantCulture)
            + ",\"usedFallback\":"
            + result.UsedFallback.ToString().ToLowerInvariant()
            + ",\"atlasVersion\":\""
            + EscapeJsonString(result.AtlasVersion)
            + "\",\"atlasLabelMapVersion\":\""
            + EscapeJsonString(result.AtlasLabelMapVersion)
            + "\",\"atlasLabelGroup\":\""
            + EscapeJsonString(result.AtlasLabelGroup)
            + "\",\"atlasConfigSummary\":\""
            + EscapeJsonString(result.AtlasConfigSummary)
            + "\",\"atlasConfigHash\":\""
            + EscapeJsonString(result.AtlasConfigHash)
            + "\",\"topologyAuditStatus\":\""
            + EscapeJsonString(result.TopologyAuditStatus)
            + "\",\"topologyAuditSummary\":\""
            + EscapeJsonString(result.TopologyAuditSummary)
            + "\",\"atlasVertexLabelSummary\":\""
            + EscapeJsonString(result.AtlasVertexLabelSummary)
            + "\",\"atlasDataFallback\":"
            + result.AtlasDataFallback.ToString().ToLowerInvariant()
            + ",\"atlasFallbackReason\":\""
            + EscapeJsonString(result.AtlasFallbackReason)
            + "\""
            + ",\"color\":\""
            + EscapeJsonString(layer.ColorHex)
            + "\",\"opacity\":"
            + layer.Opacity.ToString("0.##", CultureInfo.InvariantCulture)
            + ",\"intensity\":"
            + layer.Intensity.ToString("0.##", CultureInfo.InvariantCulture)
            + ",\"feather\":"
            + layer.Feather.ToString("0.##", CultureInfo.InvariantCulture)
            + "}");
    }

    private static List<ParsedRecipeLayer> ParseRecipeLayers(RecipePayload recipe)
    {
        List<ParsedRecipeLayer> layers = new List<ParsedRecipeLayer>();

        if (recipe.layers != null && recipe.layers.Length > 0)
        {
            for (int index = 0; index < recipe.layers.Length; index++)
            {
                layers.Add(ParseRecipeLayer(recipe.layers[index], recipe, index));
            }
        }
        else
        {
            layers.Add(ParseLegacyRecipeLayer(recipe));
        }

        return layers;
    }

    private static ParsedRecipeLayer ParseRecipeLayer(RecipeLayerPayload layer, RecipePayload recipe, int index)
    {
        if (layer == null)
        {
            throw new ArgumentException("Recipe layer " + index.ToString(CultureInfo.InvariantCulture) + " is null.");
        }

        string region = NormalizeRegion(layer.region, layer.layer);
        string colorHex = NormalizeColor(layer.color);
        float opacity = Mathf.Clamp01(layer.opacity);
        string textureSample = NormalizeTextureSample(region, layer.texture, layer.sample);

        if (!ColorUtility.TryParseHtmlString(colorHex, out Color parsedColor))
        {
            throw new ArgumentException("Recipe color is not a valid HTML color: " + colorHex);
        }

        return new ParsedRecipeLayer
        {
            Id = string.IsNullOrWhiteSpace(layer.id) ? region + "-e3" : layer.id,
            Region = region,
            LegacyLayer = string.IsNullOrWhiteSpace(layer.layer) ? region : layer.layer,
            ColorHex = colorHex,
            Color = parsedColor,
            Opacity = opacity,
            RecipeId = NormalizeRecipeId(layer.recipeId, recipe.recipeId, region, index),
            LookId = NormalizeLookId(layer.lookId, recipe.lookId),
            SentAtMs = NormalizeSentAtMs(layer.sentAtMs, recipe.sentAtMs),
            TextureSample = textureSample,
            TextureMode = NormalizeTextureMode(layer.textureMode),
            Intensity = NormalizeIntensity(layer.intensity),
            Feather = NormalizeFeather(layer.feather),
            BlendMode = NormalizeBlendMode(layer.blendMode, textureSample),
            RendererMode = NormalizeRendererMode(layer.rendererMode, recipe.rendererMode),
            CandidateId = NormalizeCandidateId(layer.candidateId, recipe.candidateId, NormalizeRendererMode(layer.rendererMode, recipe.rendererMode)),
            VariantId = NormalizeVariantId(layer.variantId, recipe.variantId, region, NormalizeRendererMode(layer.rendererMode, recipe.rendererMode)),
            Enabled = layer.enabled
        };
    }

    private static ParsedRecipeLayer ParseLegacyRecipeLayer(RecipePayload recipe)
    {
        string region = NormalizeRegion(recipe.region, recipe.layer);
        string colorHex = NormalizeColor(recipe.color);
        float opacity = Mathf.Clamp01(recipe.opacity);
        string textureSample = NormalizeTextureSample(region, recipe.texture, recipe.sample);

        if (!ColorUtility.TryParseHtmlString(colorHex, out Color parsedColor))
        {
            throw new ArgumentException("Recipe color is not a valid HTML color: " + colorHex);
        }

        return new ParsedRecipeLayer
        {
            Id = region + "-legacy",
            Region = region,
            LegacyLayer = string.IsNullOrWhiteSpace(recipe.layer) ? region : recipe.layer,
            ColorHex = colorHex,
            Color = parsedColor,
            Opacity = opacity,
            RecipeId = NormalizeRecipeId(recipe.recipeId, string.Empty, region, 0),
            LookId = NormalizeLookId(recipe.lookId, string.Empty),
            SentAtMs = NormalizeSentAtMs(recipe.sentAtMs, 0.0),
            TextureSample = textureSample,
            TextureMode = NormalizeTextureMode(recipe.textureMode),
            Intensity = NormalizeIntensity(recipe.intensity),
            Feather = NormalizeFeather(recipe.feather),
            BlendMode = NormalizeBlendMode(recipe.blendMode, textureSample),
            RendererMode = NormalizeRendererMode(recipe.rendererMode, string.Empty),
            CandidateId = NormalizeCandidateId(recipe.candidateId, string.Empty, NormalizeRendererMode(recipe.rendererMode, string.Empty)),
            VariantId = NormalizeVariantId(recipe.variantId, string.Empty, region, NormalizeRendererMode(recipe.rendererMode, string.Empty)),
            Enabled = true
        };
    }

    private static string NormalizeRegion(string region, string legacyLayer)
    {
        string candidate = !string.IsNullOrWhiteSpace(region) ? region : legacyLayer;
        candidate = string.IsNullOrWhiteSpace(candidate)
            ? string.Empty
            : candidate.Trim().ToLowerInvariant();

        if (candidate == "lip" || candidate == "cheek" || candidate == "eye")
        {
            return candidate;
        }

        throw new ArgumentException("Unsupported E4 region: " + candidate);
    }

    private static string NormalizeColor(string color)
    {
        if (string.IsNullOrWhiteSpace(color))
        {
            throw new ArgumentException("Recipe color is missing.");
        }

        return color.Trim();
    }

    private static string NormalizeRecipeId(string preferred, string fallback, string region, int index)
    {
        if (!string.IsNullOrWhiteSpace(preferred))
        {
            return preferred.Trim();
        }

        if (!string.IsNullOrWhiteSpace(fallback))
        {
            return fallback.Trim();
        }

        return "e7-baseline-" + region + "-" + index.ToString(CultureInfo.InvariantCulture);
    }

    private static string NormalizeLookId(string preferred, string fallback)
    {
        if (!string.IsNullOrWhiteSpace(preferred))
        {
            return preferred.Trim();
        }

        if (!string.IsNullOrWhiteSpace(fallback))
        {
            return fallback.Trim();
        }

        return "baseline_debug_mask";
    }

    private static double NormalizeSentAtMs(double preferred, double fallback)
    {
        if (preferred > 0.0)
        {
            return preferred;
        }

        return fallback > 0.0 ? fallback : 0.0;
    }

    private static string NormalizeTextureSample(string region, string texture, string sample)
    {
        string candidate = !string.IsNullOrWhiteSpace(texture) ? texture : sample;
        candidate = string.IsNullOrWhiteSpace(candidate)
            ? GetDefaultTextureSample(region)
            : candidate.Trim().ToLowerInvariant();

        if ((region == "lip" && candidate == "matte_lip")
            || (region == "cheek" && candidate == "soft_blush")
            || (region == "eye" && candidate == "shimmer_eye"))
        {
            return candidate;
        }

        throw new ArgumentException("Unsupported E4 texture sample for region " + region + ": " + candidate);
    }

    private static string GetDefaultTextureSample(string region)
    {
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

    private static string NormalizeTextureMode(string textureMode)
    {
        string candidate = string.IsNullOrWhiteSpace(textureMode)
            ? "sample"
            : textureMode.Trim().ToLowerInvariant();

        if (candidate == "sample")
        {
            return candidate;
        }

        throw new ArgumentException("Unsupported E4 texture mode: " + candidate);
    }

    private static float NormalizeIntensity(float intensity)
    {
        if (intensity <= 0.0f)
        {
            return 1.0f;
        }

        return Mathf.Clamp01(intensity);
    }

    private static float NormalizeFeather(float feather)
    {
        return Mathf.Clamp01(feather);
    }

    private static string NormalizeBlendMode(string blendMode, string textureSample)
    {
        string fallback = textureSample == "shimmer_eye" ? "screen" : "normal";
        string candidate = string.IsNullOrWhiteSpace(blendMode)
            ? fallback
            : blendMode.Trim().ToLowerInvariant();

        if (candidate == "normal" || candidate == "multiply" || candidate == "screen")
        {
            return candidate;
        }

        throw new ArgumentException("Unsupported E4 blend mode: " + candidate);
    }

    private static string NormalizeRendererMode(string preferred, string fallback)
    {
        string candidate = !string.IsNullOrWhiteSpace(preferred) ? preferred : fallback;
        candidate = string.IsNullOrWhiteSpace(candidate)
            ? "e3e4-baseline"
            : candidate.Trim().ToLowerInvariant();

        if (candidate == "e3e4-baseline" || candidate == "baseline")
        {
            return "e3e4-baseline";
        }

        if (candidate == "e7-arface-authored-atlas" || candidate == "arface-authored-atlas" || candidate == "atlas")
        {
            return "e7-arface-authored-atlas";
        }

        if (candidate == "e7-reference-uv-atlas" || candidate == "arface-reference-uv-atlas" || candidate == "reference-uv-atlas")
        {
            return "e7-reference-uv-atlas";
        }

        if (candidate == "e7-arface-uv-candidate" || candidate == "e7-candidate" || candidate == "candidate")
        {
            return "e7-arface-uv-candidate";
        }

        throw new ArgumentException("Unsupported E7 renderer mode: " + candidate);
    }

    private static string GetPhaseForRenderer(string rendererMode)
    {
        if (rendererMode == "e7-arface-authored-atlas" || rendererMode == "e7-reference-uv-atlas")
        {
            return "region_precision_atlas";
        }

        return rendererMode == "e7-arface-uv-candidate" ? "region_precision" : "baseline";
    }

    private static string GetRunIdForRenderer(string rendererMode)
    {
        string date = DateTimeOffset.Now.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
        if (rendererMode == "e7-reference-uv-atlas")
        {
            return "e7-reference-uv-atlas-" + date;
        }

        if (rendererMode == "e7-arface-authored-atlas")
        {
            return "e7-region-precision-atlas-" + date;
        }

        return rendererMode == "e7-arface-uv-candidate"
            ? "e7-region-precision-" + date
            : "e7-baseline-" + date;
    }

    private static bool IsRegionPrecisionRenderer(string rendererMode)
    {
        return rendererMode == "e7-arface-uv-candidate"
            || rendererMode == "e7-arface-authored-atlas"
            || rendererMode == "e7-reference-uv-atlas";
    }

    private static string GetCandidateIdForRenderer(string rendererMode)
    {
        if (rendererMode == "e7-reference-uv-atlas")
        {
            return "arface-reference-uv-atlas";
        }

        if (rendererMode == "e7-arface-authored-atlas")
        {
            return "arface-authored-atlas";
        }

        if (rendererMode == "e7-arface-uv-candidate")
        {
            return "e7-procedural-arface-uv";
        }

        return "e3e4-baseline";
    }

    private static string NormalizeCandidateId(string preferred, string fallback, string rendererMode)
    {
        string candidate = !string.IsNullOrWhiteSpace(preferred) ? preferred : fallback;
        candidate = string.IsNullOrWhiteSpace(candidate)
            ? GetCandidateIdForRenderer(rendererMode)
            : candidate.Trim().ToLowerInvariant();

        if (rendererMode == "e7-arface-authored-atlas")
        {
            return candidate == "arface-authored-atlas" ? candidate : "arface-authored-atlas";
        }

        if (rendererMode == "e7-reference-uv-atlas")
        {
            return candidate == "arface-reference-uv-atlas" ? candidate : "arface-reference-uv-atlas";
        }

        if (rendererMode == "e7-arface-uv-candidate")
        {
            return candidate == "e7-procedural-arface-uv" ? candidate : "e7-procedural-arface-uv";
        }

        return "e3e4-baseline";
    }

    private static string NormalizeVariantId(string preferred, string fallback, string region, string rendererMode)
    {
        string candidate = !string.IsNullOrWhiteSpace(preferred) ? preferred : fallback;
        candidate = string.IsNullOrWhiteSpace(candidate)
            ? GetDefaultVariantId(region, rendererMode)
            : candidate.Trim().ToLowerInvariant();

        if (rendererMode == "e7-reference-uv-atlas")
        {
            switch (region)
            {
                case "lip":
                    if (candidate == "lip-uvref-v0-core" || candidate == "lip-uvref-v0-balanced" || candidate == "lip-uvref-v0-soft-wide")
                    {
                        return candidate;
                    }
                    return "lip-uvref-v0-balanced";
                case "cheek":
                    if (candidate == "cheek-uvref-v0-core" || candidate == "cheek-uvref-v0-balanced" || candidate == "cheek-uvref-v0-soft-wide")
                    {
                        return candidate;
                    }
                    return "cheek-uvref-v0-balanced";
                case "eye":
                    if (candidate == "eye-uvref-v0-core" || candidate == "eye-uvref-v0-balanced" || candidate == "eye-uvref-v0-soft-wide")
                    {
                        return candidate;
                    }
                    return "eye-uvref-v0-balanced";
                default:
                    return "lip-uvref-v0-balanced";
            }
        }

        if (rendererMode != "e7-arface-authored-atlas")
        {
            return GetDefaultVariantId(region, rendererMode);
        }

        switch (region)
        {
            case "lip":
                if (candidate == "lip-ring-v0-tight" || candidate == "lip-ring-v0-balanced" || candidate == "lip-ring-v0-wide")
                {
                    return candidate;
                }
                return "lip-ring-v0-balanced";
            case "cheek":
                if (candidate == "cheek-soft-v0-balanced" || candidate == "cheek-soft-v0-high" || candidate == "cheek-soft-v0-wide")
                {
                    return candidate;
                }
                return "cheek-soft-v0-balanced";
            case "eye":
                if (candidate == "eye-band-v0-tight" || candidate == "eye-band-v0-balanced" || candidate == "eye-band-v0-extended")
                {
                    return candidate;
                }
                return "eye-band-v0-balanced";
            default:
                return "lip-ring-v0-balanced";
        }
    }

    private static string GetDefaultVariantId(string region, string rendererMode)
    {
        if (rendererMode == "e7-arface-authored-atlas")
        {
            switch (region)
            {
                case "cheek":
                    return "cheek-soft-v0-balanced";
                case "eye":
                    return "eye-band-v0-balanced";
                default:
                    return "lip-ring-v0-balanced";
            }
        }

        if (rendererMode == "e7-reference-uv-atlas")
        {
            switch (region)
            {
                case "cheek":
                    return "cheek-uvref-v0-balanced";
                case "eye":
                    return "eye-uvref-v0-balanced";
                default:
                    return "lip-uvref-v0-balanced";
            }
        }

        return rendererMode == "e7-arface-uv-candidate" ? "procedural-v0" : "baseline-v0";
    }

    private static double CalculateLatencyMs(double startMs, double endMs)
    {
        if (startMs <= 0.0 || endMs <= 0.0)
        {
            return 0.0;
        }

        return Math.Max(0.0, endMs - startMs);
    }

    private static string NormalizeOptional(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "none" : value.Trim();
    }

    private static string SanitizeLogValue(string value)
    {
        return NormalizeOptional(value).Replace(" ", "_").Replace("\n", "_").Replace("\r", "_");
    }

    private static void SendUnityEvent(string message)
    {
        SendUnityEvent(message, "[M6]");
    }

    private static void SendUnityEvent(string message, string logPrefix)
    {
        Debug.Log(logPrefix + " unity_to_rn_send " + message);

#if UNITY_IOS && !UNITY_EDITOR
        try
        {
            sendMessageToMobileApp(message);
        }
        catch (Exception exception)
        {
            Debug.LogError(logPrefix + " unity_to_rn_send_failed error=" + exception.Message + " message=" + message);
        }
#else
        Debug.Log(logPrefix + " unity_to_rn_editor_fallback " + message);
#endif
    }

    private static string EscapeJsonString(string value)
    {
        return (value ?? string.Empty)
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"");
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

        material.DisableKeyword("_ALPHATEST_ON");
        material.EnableKeyword("_ALPHABLEND_ON");
        material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)RenderQueue.Transparent;
    }
}
