using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.XR.ARSubsystems;

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
                longTermRawFrameStored: false,
                visible: true,
                strongValidationMode: true,
                colorHex: "#00E5FF",
                opacity: 0.86f,
                boundaryDebugVisible: true);
            bridge.ApplyGeneratedLipMaskJson(validPayload);

            string legacyPayload = BuildLegacyPayload(
                "e7-generated-lip-editor-smoke-legacy",
                ValidRawRgba8x8Base64,
                8,
                8);
            bridge.ApplyGeneratedLipMaskJson(legacyPayload);

            string controlsOnlyPayload = BuildControlsOnlyPayload(
                "e7-generated-lip-editor-smoke-rnbridge",
                visible: false,
                strongValidationMode: false,
                colorHex: "#FFAA00",
                opacity: 0.38f,
                boundaryDebugVisible: false);
            bridge.ApplyGeneratedLipMaskJson(controlsOnlyPayload);

            string invalidPayload = BuildPayload(
                "e7-generated-lip-editor-smoke-invalid",
                ValidRawRgba8x8Base64,
                7,
                8,
                localOnly: true,
                offDeviceUpload: false,
                longTermRawFrameStored: false,
                visible: true,
                strongValidationMode: false,
                colorHex: "#C76B74",
                opacity: 0.52f,
                boundaryDebugVisible: false);
            bridge.ApplyGeneratedLipMaskJson(invalidPayload);

            RequireLog(logs, "generated_lip_mask_texture_registered");
            RequireLog(logs, "validationStrongMode=true");
            RequireLog(logs, "validationVisible=false");
            RequireLog(logs, "validationColor=#C76B74");
            RequireLog(logs, "rawMaskProvided=false");
            RequireLog(logs, "blockedReason=no_tracked_arface_or_face_manager_missing");
            RequireLog(logs, "generated_lip_mask_apply_failed");
            ForbidLog(logs, "maskRawRgbaBase64");
            ForbidLog(logs, ValidRawRgba8x8Base64);

            VerifyTrackingGracePolicy();

            Debug.Log("[E7] generated_lip_mask_editor_smoke status=partial verified=raw_rgba_register_sanitized_failure_and_tracking_grace");
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

    private static void VerifyTrackingGracePolicy()
    {
        const float GraceSeconds = 0.25f;
        const float MinAlpha = 0.35f;
        bool wasLimitedOrLost = false;
        float trackingLossStartedAt = -1.0f;

        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult tracking =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.Tracking,
                hasCachedMesh: false,
                nowSeconds: 10.0f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(tracking.ShouldRender, "tracking should render");
        Require(!tracking.UseCachedMesh, "tracking should update live mesh");
        Require(tracking.Action == "tracking_render", "tracking action");

        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult lostStart =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.None,
                hasCachedMesh: true,
                nowSeconds: 11.0f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(lostStart.ShouldRender, "short lost gap should render");
        Require(lostStart.UseCachedMesh, "short lost gap should use cached mesh");
        Require(lostStart.Action == "lost_grace_hold", "short lost action");
        Require(Math.Abs(lostStart.AlphaMultiplier - 1.0f) < 0.001f, "lost start alpha");

        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult lostFade =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.None,
                hasCachedMesh: true,
                nowSeconds: 11.125f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(lostFade.ShouldRender, "lost fade should still render");
        Require(lostFade.AlphaMultiplier < 1.0f && lostFade.AlphaMultiplier > MinAlpha, "lost fade alpha");

        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult lostExpired =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.None,
                hasCachedMesh: true,
                nowSeconds: 11.30f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(!lostExpired.ShouldRender, "expired lost gap should hide");
        Require(!lostExpired.UseCachedMesh, "expired lost gap should stop cached mesh");
        Require(lostExpired.Action == "lost_hide", "expired lost action");

        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult recovered =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.Tracking,
                hasCachedMesh: true,
                nowSeconds: 11.31f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(recovered.ShouldRender, "recovered tracking should render");
        Require(recovered.Action == "recovered_restore", "recovered action");
        Require(!recovered.WasLimitedOrLost, "recovered should clear loss flag");
        Require(recovered.TrackingLossStartedAt < 0.0f, "recovered should reset loss timer");

        wasLimitedOrLost = false;
        trackingLossStartedAt = -1.0f;
        E3RegionMaskOverlay.TrackingVisibilityEditorSmokeResult limitedNoCache =
            E3RegionMaskOverlay.EvaluateTrackingVisibilityForEditorSmoke(
                TrackingState.Limited,
                hasCachedMesh: false,
                nowSeconds: 20.0f,
                graceSeconds: GraceSeconds,
                graceMinAlpha: MinAlpha,
                ref wasLimitedOrLost,
                ref trackingLossStartedAt);
        Require(!limitedNoCache.ShouldRender, "limited without cache should hide");
        Require(limitedNoCache.Action == "limited_hide", "limited no-cache action");
    }

    private static string BuildPayload(
        string generatedMaskId,
        string rawRgbaBase64,
        int width,
        int height,
        bool localOnly,
        bool offDeviceUpload,
        bool longTermRawFrameStored,
        bool visible,
        bool strongValidationMode,
        string colorHex,
        float opacity,
        bool boundaryDebugVisible)
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
            + "\"visible\":" + visible.ToString().ToLowerInvariant() + ","
            + "\"strongValidationMode\":" + strongValidationMode.ToString().ToLowerInvariant() + ","
            + "\"colorHex\":\"" + colorHex + "\","
            + "\"validationOpacity\":" + opacity.ToString(System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"boundaryDebugVisible\":" + boundaryDebugVisible.ToString().ToLowerInvariant() + ","
            + "\"runtimeReady\":false"
            + "}";
    }

    private static string BuildLegacyPayload(
        string generatedMaskId,
        string rawRgbaBase64,
        int width,
        int height)
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
            + "\"localOnly\":true,"
            + "\"offDeviceUpload\":false,"
            + "\"longTermRawFrameStored\":false,"
            + "\"runtimeReady\":false"
            + "}";
    }

    private static string BuildControlsOnlyPayload(
        string generatedMaskId,
        bool visible,
        bool strongValidationMode,
        string colorHex,
        float opacity,
        bool boundaryDebugVisible)
    {
        return "{"
            + "\"schemaVersion\":\"e7-generated-lip-mask-runtime-payload-v0\","
            + "\"generatedMaskId\":\"" + generatedMaskId + "\","
            + "\"provider\":\"vision\","
            + "\"expressionMode\":\"uvOnly\","
            + "\"adjustment\":{\"cornerReach\":0,\"upperLipTightness\":0,\"lowerLipTightness\":0,\"verticalOffset\":0},"
            + "\"maskTextureId\":\"" + generatedMaskId + "\","
            + "\"maskThreshold\":0.5,"
            + "\"maskFeatherUvNormalized\":0.07,"
            + "\"localOnly\":true,"
            + "\"offDeviceUpload\":false,"
            + "\"longTermRawFrameStored\":false,"
            + "\"visible\":" + visible.ToString().ToLowerInvariant() + ","
            + "\"strongValidationMode\":" + strongValidationMode.ToString().ToLowerInvariant() + ","
            + "\"colorHex\":\"" + colorHex + "\","
            + "\"validationOpacity\":" + opacity.ToString(System.Globalization.CultureInfo.InvariantCulture) + ","
            + "\"boundaryDebugVisible\":" + boundaryDebugVisible.ToString().ToLowerInvariant() + ","
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

    private static void Require(bool condition, string message)
    {
        if (!condition)
        {
            throw new InvalidOperationException("Tracking grace smoke failed: " + message);
        }
    }
}
