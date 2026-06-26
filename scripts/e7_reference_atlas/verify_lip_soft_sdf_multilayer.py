#!/usr/bin/env python3
"""Guard the E7 lip soft-SDF multilayer and Vision UV-bake validation path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_SHADER = Path("unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader")
DEFAULT_OVERLAY = Path("unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs")
DEFAULT_RN_BRIDGE = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
DEFAULT_VISION_RUNTIME = Path("unity/MakeupARUnityValidation/Assets/Scripts/E7VisionLipBoundaryRuntime.cs")
DEFAULT_RN_APP = Path("rn/MakeupARValidation/App.tsx")
DEFAULT_RN_TEST = Path("rn/MakeupARValidation/__tests__/App.test.tsx")
DEFAULT_RUNTIME_VERIFIER = Path("scripts/e7_reference_atlas/verify_soft_sdf_runtime_evidence.py")
DEFAULT_PREVIEW_SUMMARY = Path(
    "evidence/e7-reference-atlas/lip-style-atlas-v1/"
    "soft_sdf_multilayer_preview_20260626/summary.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify E7 lip soft-SDF, logical multilayer, and Vision UV-bake guards.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--shader", type=Path, default=DEFAULT_SHADER)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--rn-bridge", type=Path, default=DEFAULT_RN_BRIDGE)
    parser.add_argument("--vision-runtime", type=Path, default=DEFAULT_VISION_RUNTIME)
    parser.add_argument("--rn-app", type=Path, default=DEFAULT_RN_APP)
    parser.add_argument("--rn-test", type=Path, default=DEFAULT_RN_TEST)
    parser.add_argument("--runtime-verifier", type=Path, default=DEFAULT_RUNTIME_VERIFIER)
    parser.add_argument("--preview-summary", type=Path, default=DEFAULT_PREVIEW_SUMMARY)
    parser.add_argument("--max-hard-alpha-luma-std-ratio", type=float, default=0.60)
    parser.add_argument("--min-soft-matte-luma-std-ratio", type=float, default=0.75)
    parser.add_argument("--min-soft-gradient-luma-std-ratio", type=float, default=0.80)
    parser.add_argument("--min-soft-matte-luma-correlation", type=float, default=0.85)
    parser.add_argument("--min-soft-gradient-luma-correlation", type=float, default=0.90)
    parser.add_argument("--min-thin-wet-line-luma-correlation", type=float, default=0.78)
    parser.add_argument("--min-soft-minus-hard-luma-std-ratio", type=float, default=0.30)
    parser.add_argument("--min-edge-band-mean", type=float, default=0.30)
    parser.add_argument("--max-edge-band-mean", type=float, default=0.85)
    parser.add_argument("--min-wet-line-active-pixels", type=int, default=200)
    parser.add_argument("--max-wet-line-active-pixels", type=int, default=5000)
    parser.add_argument("--min-wet-line-mean-luma-boost", type=float, default=0.03)
    parser.add_argument("--min-wet-line-aspect-ratio", type=float, default=8.0)
    parser.add_argument("--max-wet-line-height-to-lip-height", type=float, default=0.12)
    parser.add_argument("--min-wet-line-width-to-lip-width", type=float, default=0.28)
    parser.add_argument("--max-wet-line-width-to-lip-width", type=float, default=0.70)
    parser.add_argument("--max-wet-line-component-count", type=int, default=2)
    return parser.parse_args()


def resolve(repo: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo / path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_text(path: Path) -> str:
    require(path.exists(), f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def require_tokens(text: str, tokens: list[str], label: str) -> None:
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{label} is missing required token(s): {', '.join(missing)}")


def load_json(path: Path) -> dict[str, Any]:
    require(path.exists(), f"Missing JSON file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"Expected JSON object in {path}")
    return data


def verify_shader(shader_text: str) -> None:
    require_tokens(
        shader_text,
        [
            "SampleMaskSoft",
            "FeatherTexelRadius",
            "nearTexel",
            "farTexel",
            "nearAxis",
            "nearDiagonal",
            "farAxis",
            "lerp(1.25, 5.5, saturate(feather * 2.35))",
            "SoftMaskAlpha",
            "CoreMaskAlpha",
            "LipCenterDensity",
            "baseStain",
            "innerLayer",
            "edgeBand",
            "outerSoftWash",
            "innerGradientTint",
            "softEdgeFeather",
            "maxPigmentStrength",
            "glossMask",
            "thinHorizontalLine",
            "highlightColor",
            "tintedWetColor",
            "lerp(tintedWetColor, float3(1.0, 0.94, 0.92), 0.30)",
            "Blend One One",
        ],
        "SmoothRegionMask.shader",
    )
    require(
        shader_text.count("SoftMaskAlpha") >= 4,
        "SmoothRegionMask.shader should use SoftMaskAlpha in pigment and gloss paths.",
    )
    require(
        "atlasLine" not in shader_text and "fallbackLine" not in shader_text,
        "Gloss path should stay as one thin wet-line, not atlas/fallback composite highlights.",
    )
    require(
        "mask.a" in shader_text,
        "Gloss path should sample the atlas A channel as the single horizontal-line mask.",
    )


def verify_overlay(overlay_text: str) -> None:
    require_tokens(
        overlay_text,
        [
            "VisionUvMaskTexture",
            "ApplyVisionBoundaryUvMask",
            "BuildVisionUvMaskPixels",
            "TryCalculateBarycentric",
            "WriteVisionUvMaskPixel",
            "BuildRuntimeMaskDiagnosticsFromPixels",
            "VisionUvMaskSoftSplatRadius",
            "vision_arface_uv_baked_outer_minus_inner_soft_falloff",
            "softSplatRadius",
            "apple_vision_lip_landmark_arface_uv_baked",
            "vision_arface_uv_baked_outer_minus_inner",
            "vision_lip_boundary_arface_uv_bake",
            "arface-uv-bake",
            "StabilizeVisionBoundaryToCurrentFace",
            "TryCalculateCurrentFaceScreenBounds",
            "WarpBoundaryPointsToCurrentFace",
            "face_bbox_translate_scale",
            "VisionFaceMotionMediumThreshold",
            "VisionFaceMotionLargeThreshold",
            "ResolveVisionFaceMotionRisk",
            "visionBoundaryFaceMotionScore",
            "visionBoundaryFaceMotionRisk",
            "LipRenderLayerMode",
            "soft_sdf_logical_multilayer",
            "GlossHighlightMode",
            "tinted_soft_lower_wet_line",
            "WideFeatherSoftSampleMode",
            "feather_scaled_13tap_near_far",
            "FeatherNearRadiusMinPx",
            "FeatherNearRadiusMaxPx",
            "FeatherRadiusScale",
            "FeatherFarRadiusScale",
            "MaskSoftSampleMode",
            "MaskFeatherNearRadiusPx",
            "MaskFeatherFarRadiusPx",
            "ResolveShaderFeatherNearRadiusPx",
            "ResolveShaderFeatherFarRadiusPx",
            'recipe.TextureSample == "gloss_lip"',
            'material.SetFloat("_UseScreenSpaceMask", 0.0f)',
            "Threshold = lipStyleAtlas || visionLipBoundary ? 0.025f",
            "Mathf.Max(0.22f, recipe.Feather)",
        ],
        "E3RegionMaskOverlay.cs",
    )


def verify_vision_runtime(runtime_text: str) -> None:
    require_tokens(
        runtime_text,
        [
            "BoundaryTransitionDurationMs = 160",
            "CaptureIntervalSeconds = 0.20f",
            "FreshBoundaryMaxAgeMs = 300",
            "BoundarySmoothBlend",
            "BoundaryLargeMotionBlend",
            "BuildInterpolatedSnapshot",
            "PrepareBoundaryTransition",
            "ApplyFaceMotionDiagnostics",
            "ResolveFaceMotionRisk",
            "CaptureCurrentFaceBounds",
            "FaceBoundsAvailable",
            "FaceMotionScore",
            "FaceMotionRisk",
            "visionBoundaryFaceMotionScore",
            "visionBoundaryFaceMotionRisk",
            "TransitionProgress",
            "transitionDurationMs",
        ],
        "E7VisionLipBoundaryRuntime.cs",
    )


def verify_rn_bridge(rn_bridge_text: str) -> None:
    require_tokens(
        rn_bridge_text,
        [
            "LipRenderLayerMode",
            "GlossHighlightMode",
            "lipRenderLayerMode",
            "glossHighlightMode",
            "result.LipRenderLayerMode",
            "result.GlossHighlightMode",
            "VisionBoundaryFaceMotionScore",
            "VisionBoundaryFaceMotionRisk",
            "visionBoundaryFaceMotionScore",
            "visionBoundaryFaceMotionRisk",
            "MaskSoftSampleMode",
            "MaskFeatherNearRadiusPx",
            "MaskFeatherFarRadiusPx",
            "maskSoftSampleMode",
            "maskFeatherNearRadiusPx",
            "maskFeatherFarRadiusPx",
        ],
        "RNBridge.cs",
    )


def verify_rn(rn_app_text: str, rn_test_text: str) -> None:
    require_tokens(
        rn_app_text,
        [
            "visionCoord=",
            "stabilizationMode?: string",
            "transitionProgress?: number",
            "faceBoundsAvailable?: boolean",
            "visionBoundaryFaceMotionScore?: number",
            "visionBoundaryFaceMotionRisk?: string",
            "lipRenderLayerMode?: string",
            "glossHighlightMode?: string",
            "maskSoftSampleMode?: string",
            "maskFeatherNearRadiusPx?: number",
            "maskFeatherFarRadiusPx?: number",
            "focusMaskTextureId=",
            "lipMaskTextureId=",
            "soft=",
            "featherPx=",
            "layers=",
            "gloss=",
            "visionMotion=",
            "motion=",
        ],
        "App.tsx",
    )
    require_tokens(
        rn_test_text,
        [
            "apple_vision_lip_landmark_arface_uv_baked",
            "visionCoord=raw-y->flip-y->face-local-warp->arface-uv-bake",
            "layers=soft_sdf_logical_multilayer",
            "gloss=tinted_soft_lower_wet_line",
            "smooth=temporal_smooth_transition|large_face_motion_smooth",
            "t=0.42/160",
            "faceLocal=true",
            "visionMotion=0.276/medium_face_motion",
            "maskDiag=vision_arface_uv_baked_outer_minus_inner_soft_falloff",
            "motion=0.390/large_face_motion",
            "gloss=none",
            "soft=feather_scaled_13tap_near_far",
            "featherPx=3.45/6.38",
            "focusMaskTextureId=lip-drawn-style-atlas-v1",
            "lipMaskTextureId=lip-drawn-style-atlas-v1",
            "lipMaskTextureId=lip-vision-boundary-v1",
        ],
        "App.test.tsx",
    )


def verify_runtime_verifier(runtime_verifier_text: str) -> None:
    require_tokens(
        runtime_verifier_text,
        [
            "CORE_PATTERNS",
            "STYLE_PATTERNS",
            "activeLipArfaceAtlas",
            "softSdfLayerMode",
            "wideFeatherSampleMode",
            "wideFeatherRadius",
            "glowThinWetLine",
            "matteNoGloss",
            "visionSoftUvBake",
            "visionArfaceUvCoordinate",
            "visionMotionScore",
            "visionMotionRisk",
            "allow-active-vision-lip",
            "extract_first_active_lip_recipe",
            "firstActiveLipRecipeArfaceAtlas",
            "maskTextureId=lip-drawn-style-atlas-v1",
            "maskSource=lip_style_atlas_v1_uv_back_projection",
            "maskSoftSampleMode=feather_scaled_13tap_near_far",
            "maskFeatherNearRadiusPx",
            "maskFeatherFarRadiusPx",
            "soft=feather_scaled_13tap_near_far",
            "featherPx=",
            "wideFeatherNearRadiusTooNarrow",
            "wideFeatherFarRadiusTooNarrow",
            "matte,glow,gradient",
            "maskDiag=vision_arface_uv_baked_outer_minus_inner_soft_falloff",
            "glossHighlightMode=tinted_soft_lower_wet_line",
            "lipRenderLayerMode=soft_sdf_logical_multilayer",
            "visionMotion=(-?\\d+(?:\\.\\d+)?)/",
            "Vision boundary logs are allowed as explicit debug/compare evidence.",
            "This verifies log/HUD diagnostic fields only.",
            "It does not replace required runtime photos",
        ],
        "verify_soft_sdf_runtime_evidence.py",
    )


def preview_metric(summary: dict[str, Any], name: str, metric: str) -> float:
    metrics = summary.get("metrics")
    require(isinstance(metrics, dict), "Preview summary is missing metrics.")
    group = metrics.get(name)
    require(isinstance(group, dict), f"Preview summary is missing metrics.{name}.")
    value = group.get(metric)
    require(isinstance(value, (int, float)), f"Preview metric {name}.{metric} is not numeric.")
    return float(value)


def verify_preview(summary: dict[str, Any], repo: Path, args: argparse.Namespace) -> dict[str, float | int]:
    require(summary.get("status") == "offline_preview_only", "Preview summary status must be offline_preview_only.")
    feather = summary.get("feather")
    near_radius = summary.get("shaderApproxNearRadiusPx")
    far_radius = summary.get("shaderApproxFarRadiusPx")
    require(isinstance(feather, (int, float)), "Preview summary feather is missing.")
    require(isinstance(near_radius, (int, float)), "Preview summary shaderApproxNearRadiusPx is missing.")
    require(isinstance(far_radius, (int, float)), "Preview summary shaderApproxFarRadiusPx is missing.")
    require(float(feather) >= 0.20, f"Preview feather is too low for the current soft edge contract: {feather}")
    require(
        float(near_radius) >= 3.0,
        f"Shader near feather radius is too narrow for edge blur validation: {near_radius}",
    )
    require(
        float(far_radius) >= float(near_radius) * 1.7,
        f"Shader far feather radius should extend beyond near radius: near={near_radius} far={far_radius}",
    )
    outputs = summary.get("outputs")
    require(isinstance(outputs, dict), "Preview summary is missing outputs.")
    for key in ("sheet", "layerDiagnostic", "softMatte", "softGradient", "thinWetLine"):
        value = outputs.get(key)
        require(isinstance(value, str) and value, f"Preview output {key} is missing.")
        output_path = Path(value)
        if not output_path.is_absolute():
            output_path = repo / output_path
        require(output_path.exists(), f"Preview output {key} does not exist: {output_path}")

    hard = preview_metric(summary, "hardAlpha", "lumaStdRatio")
    matte = preview_metric(summary, "softMatte", "lumaStdRatio")
    gradient = preview_metric(summary, "softGradient", "lumaStdRatio")
    matte_correlation = preview_metric(summary, "softMatte", "lumaCorrelation")
    gradient_correlation = preview_metric(summary, "softGradient", "lumaCorrelation")
    wet_line_correlation = preview_metric(summary, "thinWetLine", "lumaCorrelation")
    metrics = summary["metrics"]
    edge_band = metrics.get("edgeBandMean")
    wet_line = metrics.get("wetLineActivePixels")
    wet_line_boost = metrics.get("wetLineMeanLumaBoost")
    wet_line_shape = metrics.get("wetLineShape")
    require(isinstance(edge_band, (int, float)), "Preview metric edgeBandMean is missing.")
    require(isinstance(wet_line, int), "Preview metric wetLineActivePixels is missing.")
    require(isinstance(wet_line_boost, (int, float)), "Preview metric wetLineMeanLumaBoost is missing.")
    require(isinstance(wet_line_shape, dict), "Preview metric wetLineShape is missing.")
    wet_line_aspect = wet_line_shape.get("aspectRatio")
    wet_line_height_ratio = wet_line_shape.get("heightToLipHeight")
    wet_line_width_ratio = wet_line_shape.get("widthToLipWidth")
    wet_line_components = wet_line_shape.get("componentCount")
    require(isinstance(wet_line_aspect, (int, float)), "Preview metric wetLineShape.aspectRatio is missing.")
    require(
        isinstance(wet_line_height_ratio, (int, float)),
        "Preview metric wetLineShape.heightToLipHeight is missing.",
    )
    require(
        isinstance(wet_line_width_ratio, (int, float)),
        "Preview metric wetLineShape.widthToLipWidth is missing.",
    )
    require(isinstance(wet_line_components, int), "Preview metric wetLineShape.componentCount is missing.")
    require(
        hard <= args.max_hard_alpha_luma_std_ratio,
        f"Hard alpha lumaStdRatio unexpectedly high: {hard}",
    )
    require(
        matte >= args.min_soft_matte_luma_std_ratio,
        f"Soft matte lumaStdRatio too low: {matte}",
    )
    require(
        gradient >= args.min_soft_gradient_luma_std_ratio,
        f"Soft gradient lumaStdRatio too low: {gradient}",
    )
    require(
        matte_correlation >= args.min_soft_matte_luma_correlation,
        f"Soft matte lumaCorrelation too low: {matte_correlation}",
    )
    require(
        gradient_correlation >= args.min_soft_gradient_luma_correlation,
        f"Soft gradient lumaCorrelation too low: {gradient_correlation}",
    )
    require(
        wet_line_correlation >= args.min_thin_wet_line_luma_correlation,
        f"Thin wet-line lumaCorrelation too low: {wet_line_correlation}",
    )
    require(
        matte - hard >= args.min_soft_minus_hard_luma_std_ratio,
        f"Soft matte does not preserve enough detail over hard alpha: hard={hard} matte={matte}",
    )
    require(
        args.min_edge_band_mean <= float(edge_band) <= args.max_edge_band_mean,
        f"Edge feather band mean is out of guard range: {edge_band}",
    )
    require(
        args.min_wet_line_active_pixels <= wet_line <= args.max_wet_line_active_pixels,
        f"Wet-line active pixel count is out of guard range: {wet_line}",
    )
    require(
        float(wet_line_boost) >= args.min_wet_line_mean_luma_boost,
        f"Wet-line mean luma boost too low: {wet_line_boost}",
    )
    require(
        float(wet_line_aspect) >= args.min_wet_line_aspect_ratio,
        f"Wet-line is not horizontal enough: aspectRatio={wet_line_aspect}",
    )
    require(
        float(wet_line_height_ratio) <= args.max_wet_line_height_to_lip_height,
        f"Wet-line is too vertically thick: heightToLipHeight={wet_line_height_ratio}",
    )
    require(
        float(wet_line_width_ratio) >= args.min_wet_line_width_to_lip_width,
        f"Wet-line is too short to read as a horizontal line: widthToLipWidth={wet_line_width_ratio}",
    )
    require(
        float(wet_line_width_ratio) <= args.max_wet_line_width_to_lip_width,
        f"Wet-line is too long to read as one lower-center highlight: widthToLipWidth={wet_line_width_ratio}",
    )
    require(
        wet_line_components <= args.max_wet_line_component_count,
        f"Wet-line is fragmented into too many components: componentCount={wet_line_components}",
    )
    return {
        "feather": float(feather),
        "shaderApproxNearRadiusPx": float(near_radius),
        "shaderApproxFarRadiusPx": float(far_radius),
        "hardAlphaLumaStdRatio": hard,
        "softMatteLumaStdRatio": matte,
        "softGradientLumaStdRatio": gradient,
        "softMatteLumaCorrelation": matte_correlation,
        "softGradientLumaCorrelation": gradient_correlation,
        "thinWetLineLumaCorrelation": wet_line_correlation,
        "edgeBandMean": float(edge_band),
        "wetLineActivePixels": wet_line,
        "wetLineMeanLumaBoost": float(wet_line_boost),
        "wetLineAspectRatio": float(wet_line_aspect),
        "wetLineHeightToLipHeight": float(wet_line_height_ratio),
        "wetLineWidthToLipWidth": float(wet_line_width_ratio),
        "wetLineComponentCount": wet_line_components,
    }


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    shader_text = read_text(resolve(repo, args.shader))
    overlay_text = read_text(resolve(repo, args.overlay))
    rn_bridge_text = read_text(resolve(repo, args.rn_bridge))
    runtime_text = read_text(resolve(repo, args.vision_runtime))
    rn_app_text = read_text(resolve(repo, args.rn_app))
    rn_test_text = read_text(resolve(repo, args.rn_test))
    runtime_verifier_text = read_text(resolve(repo, args.runtime_verifier))
    preview_summary = load_json(resolve(repo, args.preview_summary))

    verify_shader(shader_text)
    verify_overlay(overlay_text)
    verify_rn_bridge(rn_bridge_text)
    verify_vision_runtime(runtime_text)
    verify_rn(rn_app_text, rn_test_text)
    verify_runtime_verifier(runtime_verifier_text)
    preview_metrics = verify_preview(preview_summary, repo, args)

    print(
        json.dumps(
            {
                "status": "pass",
                "scope": "E7 lip soft-SDF logical multilayer and Vision ARFace UV-bake guard",
                "runtimeVerifier": "guarded",
                "previewMetrics": preview_metrics,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
