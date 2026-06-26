using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

public static class E7GeneratedLipMaskSmoke
{
    private const string ValidRawRgba8x8Base64 =
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////////////////////wAAAAAAAAAAAAAAAP////8AAAAAAAAAAAAAAAAAAAAA/////wAAAAAAAAAA////////////////////////////////AAAAAAAAAAAAAAAA/////////////////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";

    [MenuItem("Makeup AR Validation/Run E7 Generated Lip Mask Smoke")]
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

        GameObject root = new GameObject("E7GeneratedLipMaskSmoke");
        try
        {
            E3RegionMaskOverlay overlay = root.AddComponent<E3RegionMaskOverlay>();
            bool registered = overlay.RegisterGeneratedLipMaskTexture(
                "e7-generated-lip-editor-smoke",
                ValidRawRgba8x8Base64,
                8,
                8);
            if (!registered)
            {
                throw new InvalidOperationException("RegisterGeneratedLipMaskTexture returned false.");
            }

            RNBridge bridge = root.AddComponent<RNBridge>();
            string validPayload = BuildPayload(
                "e7-generated-lip-editor-smoke-rnbridge",
                ValidRawRgba8x8Base64,
                8,
                8,
                localOnly: true,
                offDeviceUpload: false,
                longTermRawFrameStored: false);
            bridge.ApplyGeneratedLipMaskJson(validPayload);

            string invalidPayload = BuildPayload(
                "e7-generated-lip-editor-smoke-invalid",
                ValidRawRgba8x8Base64,
                7,
                8,
                localOnly: true,
                offDeviceUpload: false,
                longTermRawFrameStored: false);
            bridge.ApplyGeneratedLipMaskJson(invalidPayload);

            RequireLog(logs, "generated_lip_mask_texture_registered");
            RequireLog(logs, "generated_lip_mask_apply_failed");
            ForbidLog(logs, "maskRawRgbaBase64");
            ForbidLog(logs, ValidRawRgba8x8Base64);

            Debug.Log("[E7] generated_lip_mask_editor_smoke status=partial verified=raw_rgba_register_and_sanitized_failure");
            if (exitEditor)
            {
                EditorApplication.Exit(0);
            }
        }
        catch (Exception exception)
        {
            Debug.LogError("[E7] generated_lip_mask_editor_smoke_failed error=" + exception.Message);
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

    private static string BuildPayload(
        string generatedMaskId,
        string rawRgbaBase64,
        int width,
        int height,
        bool localOnly,
        bool offDeviceUpload,
        bool longTermRawFrameStored)
    {
        return "{"
            + "\"schemaVersion\":\"e7-generated-lip-mask-runtime-payload-v0\","
            + "\"generatedMaskId\":\"" + generatedMaskId + "\","
            + "\"provider\":\"vision\","
            + "\"expressionMode\":\"uvOnly\","
            + "\"adjustment\":{\"cornerReach\":0,\"upperLipTightness\":0,\"lowerLipTightness\":0,\"verticalOffset\":0},"
            + "\"maskTextureId\":\"" + generatedMaskId + "\","
            + "\"maskTextureEncoding\":\"raw_rgba_base64\","
            + "\"maskRawRgbaBase64\":\"" + rawRgbaBase64 + "\","
            + "\"maskTextureWidth\":" + width.ToString(System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"maskTextureHeight\":" + height.ToString(System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"maskThreshold\":0.5,"
            + "\"maskFeatherUvNormalized\":0.07,"
            + "\"localOnly\":" + localOnly.ToString().ToLowerInvariant() + ","
            + "\"offDeviceUpload\":" + offDeviceUpload.ToString().ToLowerInvariant() + ","
            + "\"longTermRawFrameStored\":" + longTermRawFrameStored.ToString().ToLowerInvariant() + ","
            + "\"runtimeReady\":false"
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
