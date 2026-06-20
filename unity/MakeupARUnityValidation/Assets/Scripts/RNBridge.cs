using System;
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
        public string layer;
        public string color;
        public float opacity;
    }

    [SerializeField] private ARFaceManager faceManager;
    [SerializeField] private Material overlayMaterial;

    private string currentLayer = "lip";
    private string currentColorHex = "#D94B74";
    private Color currentColor = new Color(0.85f, 0.29f, 0.45f, 0.65f);
    private bool hasRecipe;

#if UNITY_IOS && !UNITY_EDITOR
    [DllImport("__Internal")]
    private static extern void sendMessageToMobileApp(string message);
#endif

    private void Awake()
    {
        RefreshSceneReferences();

        if (overlayMaterial != null)
        {
            currentColor = ReadMaterialColor(overlayMaterial);
        }

        ApplyCurrentRecipeToOverlay();
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

            if (string.IsNullOrWhiteSpace(recipe.color))
            {
                throw new ArgumentException("Recipe color is missing.");
            }

            if (!ColorUtility.TryParseHtmlString(recipe.color, out Color parsedColor))
            {
                throw new ArgumentException("Recipe color is not a valid HTML color: " + recipe.color);
            }

            float opacity = Mathf.Clamp01(recipe.opacity);
            currentLayer = recipe.layer;
            currentColorHex = recipe.color;
            currentColor = new Color(parsedColor.r, parsedColor.g, parsedColor.b, opacity);
            hasRecipe = true;

            if (ApplyCurrentRecipeToOverlay())
            {
                LogRecipeApplied("message");
                SendRecipeAppliedEvent();
            }
            else
            {
                Debug.Log(
                    "[M5] recipe_queued overlay_not_ready"
                    + " layer=" + currentLayer
                    + " color=" + currentColorHex
                    + " opacity=" + currentColor.a.ToString("0.##", CultureInfo.InvariantCulture));
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("[M5] recipe_parse_failed raw=" + json + " error=" + exception.Message);
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

    private bool ApplyCurrentRecipeToOverlay()
    {
        RefreshSceneReferences();
        bool applied = false;

        if (overlayMaterial != null)
        {
            ApplyMaterialColor(overlayMaterial, currentColor);
            applied = true;
        }

        if (faceManager == null)
        {
            return applied;
        }

        foreach (ARFace face in faceManager.trackables)
        {
            MeshRenderer faceRenderer = face.GetComponent<MeshRenderer>();
            if (faceRenderer != null && faceRenderer.sharedMaterial != null)
            {
                ApplyMaterialColor(faceRenderer.sharedMaterial, currentColor);
                applied = true;
            }
        }

        return applied;
    }

    private void LogRecipeApplied(string source)
    {
        Debug.Log(
            "[M5] recipe_applied"
            + " source=" + source
            + " layer=" + currentLayer
            + " color=" + currentColorHex
            + " opacity=" + currentColor.a.ToString("0.##", CultureInfo.InvariantCulture));
    }

    private void SendRecipeAppliedEvent()
    {
        SendUnityEvent(
            "{\"type\":\"recipe_applied\",\"layer\":\""
            + EscapeJsonString(currentLayer)
            + "\",\"color\":\""
            + EscapeJsonString(currentColorHex)
            + "\",\"opacity\":"
            + currentColor.a.ToString("0.##", CultureInfo.InvariantCulture)
            + "}");
    }

    private static void SendUnityEvent(string message)
    {
        Debug.Log("[M6] unity_to_rn_send " + message);

#if UNITY_IOS && !UNITY_EDITOR
        try
        {
            sendMessageToMobileApp(message);
        }
        catch (Exception exception)
        {
            Debug.LogError("[M6] unity_to_rn_send_failed error=" + exception.Message + " message=" + message);
        }
#else
        Debug.Log("[M6] unity_to_rn_editor_fallback " + message);
#endif
    }

    private static string EscapeJsonString(string value)
    {
        return (value ?? string.Empty)
            .Replace("\\", "\\\\")
            .Replace("\"", "\\\"");
    }

    private static Color ReadMaterialColor(Material material)
    {
        if (material.HasProperty("_BaseColor"))
        {
            return material.GetColor("_BaseColor");
        }

        if (material.HasProperty("_Color"))
        {
            return material.GetColor("_Color");
        }

        return material.color;
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
