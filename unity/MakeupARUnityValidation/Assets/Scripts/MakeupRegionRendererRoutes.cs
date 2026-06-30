using System;
using System.Collections.Generic;

public struct MakeupRegionRendererRoute
{
    public string Region;
    public string RendererId;
    public string RendererMode;
    public string BackendComponent;
    public string Phase;
    public string RunIdPrefix;

    public MakeupRegionRendererRoute(
        string region,
        string rendererId,
        string rendererMode,
        string backendComponent,
        string phase,
        string runIdPrefix)
    {
        Region = region;
        RendererId = rendererId;
        RendererMode = rendererMode;
        BackendComponent = backendComponent;
        Phase = phase;
        RunIdPrefix = runIdPrefix;
    }
}

public static class MakeupRegionRendererRoutes
{
    public const string SmoothRegionMaskMode = "smooth-region-mask";
    public const string SmoothRegionMaskBackend = "E3RegionMaskOverlay";
    public const string MediaPipeRegionOverlayMode = "mediapipe-region-overlay";
    public const string MediaPipeRegionOverlayBackend = "MediaPipeRegionOverlayRenderer";

    public static readonly string[] Regions = { "lip", "cheek", "eye", "brow" };

    private static readonly Dictionary<string, MakeupRegionRendererRoute> ProductRoutes =
        new Dictionary<string, MakeupRegionRendererRoute>
        {
            {
                "lip",
                new MakeupRegionRendererRoute(
                    "lip",
                    "lip-mediapipe-region-overlay-renderer",
                    MediaPipeRegionOverlayMode,
                    MediaPipeRegionOverlayBackend,
                    "mediapipe_region_lip",
                    "lip-mediapipe-v1")
            },
            {
                "cheek",
                new MakeupRegionRendererRoute(
                    "cheek",
                    "cheek-mediapipe-region-overlay-renderer",
                    MediaPipeRegionOverlayMode,
                    MediaPipeRegionOverlayBackend,
                    "mediapipe_region_cheek",
                    "cheek-mediapipe-v1")
            },
            {
                "eye",
                new MakeupRegionRendererRoute(
                    "eye",
                    "eye-smooth-region-mask-renderer",
                    SmoothRegionMaskMode,
                    SmoothRegionMaskBackend,
                    "smooth_mask_eye",
                    "eye-style-v1")
            },
            {
                "brow",
                new MakeupRegionRendererRoute(
                    "brow",
                    "brow-mediapipe-region-overlay-renderer",
                    MediaPipeRegionOverlayMode,
                    MediaPipeRegionOverlayBackend,
                    "mediapipe_region_brow",
                    "brow-mediapipe-v1")
            },
        };

    private static readonly Dictionary<string, MakeupRegionRendererRoute> SmoothRegionMaskRoutes =
        new Dictionary<string, MakeupRegionRendererRoute>
        {
            {
                "lip",
                new MakeupRegionRendererRoute(
                    "lip",
                    "lip-smooth-region-mask-renderer",
                    SmoothRegionMaskMode,
                    SmoothRegionMaskBackend,
                    "smooth_mask_lip",
                    "lip-style-v1")
            },
            {
                "cheek",
                new MakeupRegionRendererRoute(
                    "cheek",
                    "cheek-smooth-region-mask-renderer",
                    SmoothRegionMaskMode,
                    SmoothRegionMaskBackend,
                    "smooth_mask_cheek",
                    "cheek-style-v1")
            },
            {
                "eye",
                new MakeupRegionRendererRoute(
                    "eye",
                    "eye-smooth-region-mask-renderer",
                    SmoothRegionMaskMode,
                    SmoothRegionMaskBackend,
                    "smooth_mask_eye",
                    "eye-style-v1")
            },
            {
                "brow",
                new MakeupRegionRendererRoute(
                    "brow",
                    "brow-smooth-region-mask-renderer",
                    SmoothRegionMaskMode,
                    SmoothRegionMaskBackend,
                    "smooth_mask_brow",
                    "brow-style-v1")
            },
        };

    public static MakeupRegionRendererRoute Resolve(string region)
    {
        region = NormalizeRegion(region);
        return ProductRoutes[region];
    }

    public static MakeupRegionRendererRoute Resolve(string region, string rendererMode)
    {
        region = NormalizeRegion(region);
        string normalizedMode = NormalizeRendererMode(rendererMode, rendererMode, region);
        return normalizedMode == MediaPipeRegionOverlayMode
            ? ProductRoutes[region]
            : SmoothRegionMaskRoutes[region];
    }

    public static string NormalizeRegion(string region)
    {
        region = string.IsNullOrWhiteSpace(region)
            ? string.Empty
            : region.Trim().ToLowerInvariant();

        if (ProductRoutes.ContainsKey(region))
        {
            return region;
        }

        throw new ArgumentException("Unsupported makeup renderer region: " + region);
    }

    public static string NormalizeRendererMode(
        string preferred,
        string secondary,
        string region)
    {
        MakeupRegionRendererRoute route = Resolve(region);
        string value = !string.IsNullOrWhiteSpace(preferred) ? preferred : secondary;
        value = string.IsNullOrWhiteSpace(value)
            ? route.RendererMode
            : value.Trim().ToLowerInvariant();

        if (value == SmoothRegionMaskMode)
        {
            return value;
        }

        if (value == MediaPipeRegionOverlayMode)
        {
            return route.Region == "eye" ? SmoothRegionMaskMode : value;
        }

        if (value == route.RendererMode)
        {
            return value;
        }

        throw new ArgumentException(
            "Unsupported renderer mode for region " + route.Region + ": " + value);
    }
}
