using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class E7FullFaceRegionPackageSmoke
{
    [MenuItem("Makeup AR Validation/Run E7 Full Face Region Package Smoke")]
    public static void RunFromMenu()
    {
        RunSmoke(exitEditor: false);
    }

    public static void RunFromCommandLine()
    {
        RunSmoke(exitEditor: true);
    }

    private static void RunSmoke(bool exitEditor)
    {
        List<string> logs = new List<string>();
        Application.LogCallback logCallback = (condition, stackTrace, type) =>
        {
            logs.Add(type + ":" + condition);
        };
        Application.logMessageReceived += logCallback;

        GameObject root = new GameObject("E7FullFaceRegionPackageSmoke");
        try
        {
            RNBridge bridge = root.AddComponent<RNBridge>();
            bridge.ApplyRecipeJson(BuildPayload());

            RequireLog(logs, "[E4] recipe_parse");
            RequireLog(logs, "layerCount=4");
            RequireLog(logs, "region=lip");
            RequireLog(logs, "region=blush");
            RequireLog(logs, "region=brow");
            RequireLog(logs, "region=eyeliner");
            RequireLog(logs, "maskTextureId=e7-lip-balanced-uv-v0");
            RequireLog(logs, "maskTextureId=e7-blush-balanced-uv-v0");
            RequireLog(logs, "maskTextureId=e7-brow-balanced-uv-v0");
            RequireLog(logs, "maskTextureId=e7-eyeliner-minimal-safe-uv-v0");
            ForbidLog(logs, "recipe_parse_failed");
            ForbidLog(logs, "Unsupported");

            Debug.Log("[E7] full_face_region_package_editor_smoke status=pre_xcode_ready verified=recipe_parse_and_region_dispatch");
            if (exitEditor)
            {
                EditorApplication.Exit(0);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("[E7] full_face_region_package_editor_smoke_failed error=" + exception.Message);
            if (exitEditor)
            {
                EditorApplication.Exit(1);
            }
        }
        finally
        {
            Application.logMessageReceived -= logCallback;
            UnityEngine.Object.DestroyImmediate(root);
        }
    }

    private static string BuildPayload()
    {
        return "{"
            + "\"version\":2,"
            + "\"recipeBatchId\":\"e7-full-face-region-editor-smoke\","
            + "\"recipeId\":\"e7-full-face-region-editor-smoke\","
            + "\"lookId\":\"e7_full_face_region_generate_v0\","
            + "\"rendererMode\":\"smooth-region-mask\","
            + "\"activeRegions\":\"lip,blush,brow,eyeliner\","
            + "\"region\":\"lip\","
            + "\"layerCount\":4,"
            + "\"enabledLayerCount\":4,"
            + "\"texture\":\"matte_lip\","
            + "\"sample\":\"matte_lip\","
            + "\"textureMode\":\"sample\","
            + "\"coverage\":0.72,"
            + "\"finish\":\"validation-placeholder\","
            + "\"layers\":["
            + Layer("lip", "lip-balanced-gold-v0", "e7-lip-balanced-uv-v0", "matte_lip", "#C76B74", 0.62f, 1.0f, 0.35f, "multiply")
            + ","
            + Layer("blush", "blush-balanced-soft-oval-v0", "e7-blush-balanced-uv-v0", "soft_blush", "#E67B5F", 0.45f, 0.68f, 0.18f, "normal")
            + ","
            + Layer("brow", "brow-balanced-stroke-envelope-v0", "e7-brow-balanced-uv-v0", "shimmer_eye", "#5F4A42", 0.48f, 0.72f, 0.14f, "multiply")
            + ","
            + Layer("eyeliner", "eyeliner-minimal-safe-lashline-v0", "e7-eyeliner-minimal-safe-uv-v0", "shimmer_eye", "#2F2730", 0.66f, 0.72f, 0.12f, "multiply")
            + "]"
            + "}";
    }

    private static string Layer(
        string region,
        string candidateId,
        string maskTextureId,
        string texture,
        string color,
        float opacity,
        float coverage,
        float threshold,
        string blendMode)
    {
        return "{"
            + "\"id\":\"" + region + "-" + candidateId + "\","
            + "\"region\":\"" + region + "\","
            + "\"layer\":\"" + region + "\","
            + "\"enabled\":true,"
            + "\"color\":\"" + color + "\","
            + "\"opacity\":" + opacity.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"texture\":\"" + texture + "\","
            + "\"sample\":\"" + texture + "\","
            + "\"textureMode\":\"sample\","
            + "\"intensity\":" + opacity.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"feather\":0.07,"
            + "\"blendMode\":\"" + blendMode + "\","
            + "\"rendererMode\":\"smooth-region-mask\","
            + "\"coverage\":" + coverage.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"finish\":\"validation-placeholder\","
            + "\"textureAmount\":0,"
            + "\"roughness\":0,"
            + "\"specular\":0,"
            + "\"specularPower\":0,"
            + "\"glossBoost\":0,"
            + "\"shimmer\":0,"
            + "\"shimmerColor\":\"#FFFFFF\","
            + "\"skinAdaptive\":" + (region == "lip").ToString().ToLowerInvariant() + ","
            + "\"preserveDetail\":true,"
            + "\"materialId\":\"e7-full-face-" + region + "-material-v0\","
            + "\"shaderMode\":\"smooth-lip-finish-v0\","
            + "\"passCount\":1,"
            + "\"candidateId\":\"" + candidateId + "\","
            + "\"maskTextureId\":\"" + maskTextureId + "\","
            + "\"maskThreshold\":" + threshold.ToString("0.##", System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"maskFeatherUvNormalized\":0.07,"
            + "\"cornerReach\":0,"
            + "\"upperLipTightness\":0,"
            + "\"lowerLipTightness\":0,"
            + "\"verticalOffset\":0,"
            + "\"cameraBackdropAvailable\":false,"
            + "\"lightEstimateAvailable\":false"
            + "}";
    }

    private static void RequireLog(IEnumerable<string> logs, string token)
    {
        foreach (string log in logs)
        {
            if (log.Contains(token, StringComparison.Ordinal))
            {
                return;
            }
        }

        throw new InvalidOperationException("Expected log token missing: " + token);
    }

    private static void ForbidLog(IEnumerable<string> logs, string token)
    {
        foreach (string log in logs)
        {
            if (log.Contains(token, StringComparison.Ordinal))
            {
                throw new InvalidOperationException("Forbidden log token present: " + token);
            }
        }
    }
}
