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
    [Serializable]
    private sealed class RecipePayload
    {
        public int version;
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
        public RecipeLayerPayload[] layers;
    }

    [Serializable]
    private sealed class RecipeLayerPayload
    {
        public string id;
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
        public bool enabled;
    }

    private struct ParsedRecipeLayer
    {
        public string Id;
        public string Region;
        public string LegacyLayer;
        public string ColorHex;
        public Color Color;
        public float Opacity;
        public string TextureSample;
        public string TextureMode;
        public float Intensity;
        public float Feather;
        public string BlendMode;
        public bool Enabled;
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private Material overlayMaterial;

    private E3RegionMaskOverlay regionMaskOverlay;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern void sendMessageToMobileApp(string message);
#endif

    private void Awake()
    {
        RefreshSceneReferences();
        EnsureRegionMaskOverlay();

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
                LogRecipeApplied("message", layer, result);
                SendRecipeAppliedEvent(layer, result);
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

    private void RefreshSceneReferences()
    {
        if (faceManager == null)
        {
            faceManager = FindFirstObjectByType<ARFaceManager>();
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
            layer.BlendMode);
    }

    private void LogRecipeApplied(
        string source,
        ParsedRecipeLayer layer,
        E3RegionMaskOverlay.RegionApplyResult result)
    {
        string applied = result.Applied ? "true" : "false";
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
            + " faceCount=" + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + " meshTriangles=" + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + " usedFallback=" + result.UsedFallback.ToString().ToLowerInvariant());
    }

    private void SendRecipeAppliedEvent(
        ParsedRecipeLayer layer,
        E3RegionMaskOverlay.RegionApplyResult result)
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
            + ",\"faceCount\":"
            + result.FaceCount.ToString(CultureInfo.InvariantCulture)
            + ",\"meshTriangles\":"
            + result.MeshTriangleCount.ToString(CultureInfo.InvariantCulture)
            + ",\"usedFallback\":"
            + result.UsedFallback.ToString().ToLowerInvariant()
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
                layers.Add(ParseRecipeLayer(recipe.layers[index], index));
            }
        }
        else
        {
            layers.Add(ParseLegacyRecipeLayer(recipe));
        }

        return layers;
    }

    private static ParsedRecipeLayer ParseRecipeLayer(RecipeLayerPayload layer, int index)
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
            TextureSample = textureSample,
            TextureMode = NormalizeTextureMode(layer.textureMode),
            Intensity = NormalizeIntensity(layer.intensity),
            Feather = NormalizeFeather(layer.feather),
            BlendMode = NormalizeBlendMode(layer.blendMode, textureSample),
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
            TextureSample = textureSample,
            TextureMode = NormalizeTextureMode(recipe.textureMode),
            Intensity = NormalizeIntensity(recipe.intensity),
            Feather = NormalizeFeather(recipe.feather),
            BlendMode = NormalizeBlendMode(recipe.blendMode, textureSample),
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

    private static string NormalizeOptional(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? "none" : value.Trim();
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
