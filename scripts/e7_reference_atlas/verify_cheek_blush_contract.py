#!/usr/bin/env python3
"""Verify the E7 cheek blush v1 mask/runtime contract."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
MASK_ROOT = ROOT / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
SUMMARY_PATH = ROOT / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/summary.json"
VISION_ANCHOR_SUMMARY_PATH = ROOT / "evidence/e7-reference-atlas/cheek-vision-reference/summary.json"
EXPECTED_SUMMARY_PATH = (
    ROOT
    / "evidence/e7-reference-atlas/cheek-blush-mask-textures-v1/expected_render_20260627/summary.json"
)
APP_PATH = ROOT / "rn/MakeupARValidation/App.tsx"
RNBRIDGE_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
OVERLAY_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
SHADER_PATH = ROOT / "unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader"
CHEEK_TEMPLATE_ATLAS_ID = "cheek-blush-drawing-template-atlas-v1"

MASK_IDS = (
    "cheek-daily-mask-v1",
    "cheek-lovely-mask-v1",
    "cheek-sunkissed-mask1-v1",
    "cheek-sunkissed-mask2-v1",
    "cheek-under-eye-mask-v1",
)
TEXTURE_NAMES = (
    "blush_daily",
    "blush_lovely",
    "blush_sunkissed1",
    "blush_sunkissed2",
    "blush_under_eye",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def require_text(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        require(token in text, f"{path.relative_to(ROOT)} missing token: {token}")


def require_no_text(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for token in tokens:
        require(token not in text, f"{path.relative_to(ROOT)} must not contain legacy token: {token}")


def verify_masks() -> dict[str, dict[str, float | int]]:
    stats: dict[str, dict[str, float | int]] = {}
    for mask_id in MASK_IDS:
        path = MASK_ROOT / f"{mask_id}.png"
        require(path.exists(), f"Missing Unity cheek mask: {path}")
        rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
        require(rgba.shape == (512, 512, 4), f"{mask_id} must be 512x512 RGBA")

        r = rgba[:, :, 0]
        g = rgba[:, :, 1]
        b = rgba[:, :, 2]
        a = rgba[:, :, 3]
        active = r > 8

        require(int(g.max()) == 0, f"{mask_id} G channel must stay reserved/zero")
        require(np.array_equal(r, a), f"{mask_id} R and A alpha channels must match")
        require(int(active.sum()) > 3000, f"{mask_id} alpha coverage is unexpectedly tiny")
        min_density_pixels = 1200 if mask_id == "cheek-under-eye-mask-v1" else 2500
        if mask_id == "cheek-sunkissed-mask2-v1":
            min_density_pixels = 2000
        density_pixels = int((b > 8).sum())
        require(
            density_pixels > min_density_pixels,
            f"{mask_id} density channel is unexpectedly tiny",
        )
        require(
            density_pixels >= int(active.sum()) * 0.68,
            f"{mask_id} density guide coverage is too small for the source-shaped alpha",
        )
        require(float(b[active].mean()) < float(r[active].mean()), f"{mask_id} B density should not be flat alpha")
        require(int(b.max()) > 90, f"{mask_id} density peak is too weak")

        stats[mask_id] = {
            "alphaPixelsGt8": int(active.sum()),
            "densityPixelsGt8": density_pixels,
            "densityMax": int(b.max()),
            "reservedGMax": int(g.max()),
        }
    return stats


def verify_shape_template_preservation(summary: dict[str, object]) -> None:
    for mask_id in MASK_IDS:
        mask_summary = summary["masks"][mask_id]
        face_summary = mask_summary["faceAnchorSummary"]
        template = face_summary["shapeTemplateSummary"]
        require(
            template["source"] == "user_drawing_silhouette_shape_template",
            f"{mask_id} must use the user drawing silhouette as the shape template",
        )
        require(
            len(template["components"]) >= 1,
            f"{mask_id} must preserve at least one drawing component",
        )

        reference = mask_summary["referenceDrawingStats"]
        converted = mask_summary["screenAlphaStats"]
        screen_density = mask_summary["screenDensityStats"]
        reference_pixels = max(int(reference["pixelCount"]), 1)
        converted_pixels = int(converted["pixelCount"])
        coverage_ratio = converted_pixels / reference_pixels
        require(
            0.90 <= coverage_ratio <= 1.12,
            f"{mask_id} converted alpha coverage {coverage_ratio:.3f} drifted from source drawing",
        )
        density_ratio = int(screen_density["pixelCount"]) / max(converted_pixels, 1)
        require(
            density_ratio >= 0.96,
            f"{mask_id} screen density coverage {density_ratio:.3f} leaves visible empty areas inside source-shaped alpha",
        )

        reference_box = reference["bbox"]
        converted_box = converted["bbox"]
        density_box = screen_density["bbox"]
        for dimension in ("width", "height"):
            reference_size = max(float(reference_box[dimension]), 1.0)
            converted_size = float(converted_box[dimension])
            size_ratio = converted_size / reference_size
            require(
                0.88 <= size_ratio <= 1.12,
                f"{mask_id} converted bbox {dimension} ratio {size_ratio:.3f} drifted from source drawing",
            )

            density_size = float(density_box[dimension])
            density_size_delta = abs(density_size - converted_size)
            require(
                density_size_delta <= 2.0,
                f"{mask_id} screen density bbox {dimension} differs from alpha by {density_size_delta:.1f}px",
            )

        max_position_shift = 26
        for edge in ("left", "right"):
            shift = abs(int(converted_box[edge]) - int(reference_box[edge]))
            require(
                shift <= max_position_shift,
                f"{mask_id} converted bbox {edge} shifted {shift}px from source drawing",
            )

        max_vertical_shift = 48 if mask_id in ("cheek-sunkissed-mask1-v1", "cheek-sunkissed-mask2-v1") else 26
        for edge in ("top", "bottom"):
            shift = abs(int(converted_box[edge]) - int(reference_box[edge]))
            require(
                shift <= max_vertical_shift,
                f"{mask_id} converted bbox {edge} shifted {shift}px from source drawing",
            )

        for edge in ("left", "right", "top", "bottom"):
            density_shift = abs(int(density_box[edge]) - int(converted_box[edge]))
            require(
                density_shift <= 2,
                f"{mask_id} screen density bbox {edge} shifted {density_shift}px from alpha bbox",
            )


def field_stats(path: Path, threshold: float = 0.03) -> tuple[int, dict[str, int]]:
    values = np.asarray(Image.open(path).convert("L"), dtype=np.float32) / 255.0
    rows, cols = np.nonzero(values > threshold)
    if len(cols) == 0:
        return 0, {"left": 0, "top": 0, "right": 0, "bottom": 0, "width": 0, "height": 0}
    return int(len(cols)), {
        "left": int(cols.min()),
        "top": int(rows.min()),
        "right": int(cols.max()),
        "bottom": int(rows.max()),
        "width": int(cols.max() - cols.min() + 1),
        "height": int(rows.max() - rows.min() + 1),
    }


def verify_projected_density_fill(expected: dict[str, object]) -> None:
    for row in expected["rows"]:
        mask_id = str(row["maskTextureId"])
        alpha_pixels, alpha_box = field_stats(ROOT / str(row["projectedAlpha"]))
        density_pixels, density_box = field_stats(ROOT / str(row["projectedDensity"]))
        require(alpha_pixels > 0, f"{mask_id} projected alpha is empty")
        ratio = density_pixels / max(alpha_pixels, 1)
        require(
            ratio >= 0.75,
            f"{mask_id} projected density guide coverage {ratio:.3f} is too small for GPU multiply shaping",
        )
        for dimension in ("width", "height"):
            alpha_size = max(int(alpha_box[dimension]), 1)
            density_size = int(density_box[dimension])
            size_ratio = density_size / alpha_size
            require(
                size_ratio >= 0.84,
                f"{mask_id} projected density bbox {dimension} ratio {size_ratio:.3f} is too small for GPU multiply shaping",
            )
        for edge in ("left", "right", "top", "bottom"):
            shift = abs(int(density_box[edge]) - int(alpha_box[edge]))
            require(
                shift <= 26,
                f"{mask_id} projected density bbox {edge} shifted {shift}px too far from alpha bbox",
            )


def main() -> None:
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    vision_summary = json.loads(VISION_ANCHOR_SUMMARY_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_SUMMARY_PATH.read_text(encoding="utf-8"))

    require(sorted(summary["maskIds"]) == sorted(MASK_IDS), "summary maskIds must match cheek v1")
    require(
        summary["maskSource"] == "arface_face_proportion_anchor_density",
        "summary must document ARFace face-proportion mask source",
    )
    require(
        summary["drawingRole"] == "shape_template_for_face_proportion_warp_not_screen_sticker",
        "summary must document that drawings are shape templates, not stickers",
    )
    require(
        summary["referenceCalibrationRole"] == "shape_template_calibration_not_fixed_runtime_boundary",
        "summary must document drawing-derived calibration without fixed runtime boundaries",
    )
    require(
        summary["appleVisionAnchorRole"] == "landmark_anchor_audit_not_cheek_boundary_source",
        "summary must document Apple Vision landmark audit role",
    )
    require(
        summary["appleVisionAnchorAnalysisPath"] == "evidence/e7-reference-atlas/cheek-vision-reference/summary.json",
        "summary must point to the Apple Vision anchor analysis evidence",
    )
    require(
        vision_summary["mappedRecommendations"]["status"] == "ok",
        "Apple Vision cheek reference analysis must produce mapped recommendations",
    )
    verify_shape_template_preservation(summary)
    for shape_name in ("daily", "lovely", "sunkissed1", "sunkissed2", "under_eye"):
        require(
            shape_name in vision_summary["mappedRecommendations"]["shapes"],
            f"Apple Vision analysis missing mapped shape: {shape_name}",
        )
    for mask_id in MASK_IDS:
        mask_summary = summary["masks"][mask_id]
        require(
            mask_summary["referenceCalibrationRole"] == "shape_template_calibration_not_fixed_runtime_boundary",
            f"{mask_id} must document reference calibration as a shape template",
        )
        require(
            mask_summary["appleVisionAnchorRole"] == "landmark_anchor_audit_not_cheek_boundary_source",
            f"{mask_id} must document Apple Vision as landmark audit only",
        )
        require(
            "appleVisionReferenceAnchorAudit" in mask_summary,
            f"{mask_id} must keep Apple Vision anchors as audit evidence",
        )
        require(
            mask_summary["faceAnchorSummary"]["appleVisionAnchorGateId"]
            == "cheek-reference-vision-anchor-analysis-v1",
            f"{mask_id} must record Apple Vision anchor gate id",
        )
        require(
            mask_summary["faceAnchorSummary"]["usedTopologyEyeAnchors"] is True,
            f"{mask_id} must use ARFace topology eye anchors for placement",
        )
        require(
            mask_summary["faceAnchorSummary"]["usedTopologyNoseMidline"] is True,
            f"{mask_id} must use ARFace topology nose midline for center placement",
        )
        require(
            "arface_topology_eye_anchor_vertices" in mask_summary["faceAnchorSummary"]["metricSource"],
            f"{mask_id} must document topology anchor metric source",
        )
    require(summary["channelContract"]["g"].startswith("reserved"), "summary must document reserved G")
    template_atlas = summary["runtimeTemplateAtlas"]
    require(
        template_atlas["id"] == CHEEK_TEMPLATE_ATLAS_ID,
        "summary must include the cheek drawing runtime template atlas id",
    )
    require(
        template_atlas["tileSize"] == 128,
        "runtime template atlas must use the expected tile size",
    )
    require(
        len(template_atlas["tiles"]) >= 10,
        "runtime template atlas must contain all source drawing components",
    )
    require(
        Path(ROOT / template_atlas["path"]).exists(),
        "runtime template atlas Unity resource must exist",
    )
    require(
        Path(ROOT / template_atlas["evidencePath"]).exists(),
        "runtime template atlas evidence preview must exist",
    )
    require(len(expected["rows"]) == 5, "expected render summary must contain five rows")
    verify_projected_density_fill(expected)
    require(
        expected["maskSource"] == "arface_face_proportion_anchor_density",
        "expected render must document ARFace face-proportion mask source",
    )
    require(
        expected["drawingRole"] == "shape_template_for_face_proportion_warp_not_screen_sticker",
        "expected render must document drawing shape-template role",
    )
    require(
        expected["referenceCalibrationRole"] == "shape_template_calibration_not_fixed_runtime_boundary",
        "expected render must document drawing-derived shape calibration",
    )
    require(
        expected["appleVisionAnchorRole"] == "landmark_anchor_audit_not_cheek_boundary_source",
        "expected render must document Apple Vision landmark audit role",
    )
    require(
        expected["appleVisionAnchorAnalysisPath"]
        == "evidence/e7-reference-atlas/cheek-vision-reference/summary.json",
        "expected render must point to Apple Vision anchor analysis evidence",
    )
    require(
        expected["runtimeSelectionRule"] == "one cheek blush region mask is selected per cheek layer",
        "expected render must document single-mask runtime selection",
    )
    require(
        expected["runtimeParityQaSheet"].endswith("cheek_blush_runtime_parity_qa_sheet.png"),
        "expected render must include a runtime-parity QA sheet",
    )
    require(
        Path(ROOT / expected["runtimeParityQaSheet"]).exists(),
        "runtime-parity QA sheet must exist",
    )
    for row in expected["rows"]:
        require(
            row["runtimeFieldAlphaActivePixelsGt003"] > 0,
            f"{row['maskTextureId']} must include runtime field alpha stats",
        )
        require(
            row["runtimeFieldDensityActivePixelsGt003"] > 0,
            f"{row['maskTextureId']} must include runtime field density stats",
        )
        require(
            row["runtimeFieldDensityActivePixelsGt003"]
            >= row["runtimeFieldAlphaActivePixelsGt003"] * 0.92,
            f"{row['maskTextureId']} runtime density area is too small compared with runtime alpha",
        )
        require(
            row["expectedRenderChangedPixelsGt006"] >= row["projectedAlphaActivePixelsGt003"] * 0.70,
            f"{row['maskTextureId']} expected render visibly changes too little of the projected alpha area",
        )
        require(
            row["centerMeanDelta"] >= 0.035,
            f"{row['maskTextureId']} center pigment became too weak",
        )
        require(
            row["outerEdgeToCenterDeltaRatio"] <= 0.62,
            f"{row['maskTextureId']} outer edge remains too close to center pigment strength",
        )
        require(
            Path(ROOT / row["qaHighVisibilityRender"]).exists(),
            f"{row['maskTextureId']} must include QA high-visibility render",
        )
    require(
        "ARFace topology eye/nose anchor vertices" in summary["anatomyBoundaryContract"],
        "summary must document ARFace topology anchor boundary generation",
    )
    require(
        "ARFace topology eye/nose anchor vertices" in expected["anatomyBoundaryContract"]
        or "ARFace face structure" in expected["anatomyBoundaryContract"],
        "expected render must document ARFace topology/anatomy boundary generation",
    )
    require(
        expected["edgeContract"]
        == "center pigment stays strong while outer blush edges return to white through GPU DstColor/Zero multiply filter strength",
        "expected render must document the GPU multiply edge fade contract",
    )
    require(
        expected["edgeFadeMetricsContract"]
        == "outer edge mean color change should stay below center mean color change, without reducing center pigment strength",
        "expected render must document the center-preserving edge fade metric contract",
    )
    require(
        expected["densityContract"]["blush_daily"].startswith("outer/high cheekbone peak"),
        "expected render must document shape-specific density behavior",
    )

    require_text(
        APP_PATH,
        MASK_IDS
        + TEXTURE_NAMES
        + (
            "cheek_blush_validation_v1",
            "cheek-blush-v1",
            "opacity: 0.8",
            "intensity: 0.82",
            "intensity: 0.84",
            "intensity: 0.78",
            "intensity: 0.74",
            "intensity: 0.76",
            "feather: 0.64",
            "attach=${formatCheekAttachmentMode",
        ),
    )
    require_text(
        RNBRIDGE_PATH,
        MASK_IDS
        + TEXTURE_NAMES
        + (
            "cheek_blush_validation_v1",
            "cheek-blush-v1",
            "GetDefaultMaskTextureId(region)",
            "maskTextureDensityPixelCountGt8",
            "maskTextureDensityMax",
        ),
    )
    require_text(
        OVERLAY_PATH,
        MASK_IDS
        + (
            "_CheekBlushMode",
            CHEEK_TEMPLATE_ATLAS_ID,
            "CheekBlushTemplateAtlasData",
            "CheekTemplateComponent",
            "SampleCheekBlushTemplateAlpha",
            "SampleCheekBlushTemplateComponent",
            "cheek_blush_v1_static_arface_uv_attached_mask",
            "static_arface_uv_gpu_dstcolor_zero_multiply_powder_fade",
            "CheekBlushDynamicProjectionEnabled = false",
            "cheek_blush_static_arface_uv_attached",
            "SideCheekAnatomyGate",
            "CheekLeftEyeAnchorVertexIndices",
            "CheekRightEyeAnchorVertexIndices",
            "CheekNoseMidlineAnchorVertexIndices",
            "TryAverageProjectedVertices",
            "eyeLineY=",
            "usedTopologyEyeAnchors=",
            "usedTopologyNoseMidline=",
            "MaskTextureDensityPixelCountGt8",
            "MaskTextureDensityCoverageGt8",
            "MaskTextureDensityBbox",
            "MaskTextureDensityMax",
            "BlendMode.DstColor",
            "BlendMode.Zero",
            "sampleAlphaScale = Mathf.Lerp(0.34f, 0.60f, recipe.Intensity)",
            "brightnessScale = 0.88f",
        ),
    )
    require_no_text(
        OVERLAY_PATH,
        (
            "cheek_blush_v1_face_proportion_uv_density",
            "rgba_cheek_blush_face_anchor_density_powder",
            "cheek_blush_v1_runtime_arface_projection_uv_density",
            "runtime_arface_projection_rgba_cheek_density_powder",
            "cheek_blush_runtime_arface_projection_uv_density",
            "cheek_blush_v1_drawing_template_arface_uv_mask",
            "drawing_template_rgba_cheek_density_powder_multiply",
            "cheek_blush_drawing_template_arface_uv_static",
            "CheekBlushDynamicProjectionEnabled = true",
        ),
    )
    require_text(
        SHADER_PATH,
        (
            "_CheekBlushMode",
            "cheekDensity",
            "cheekPowderMask",
            "cheekPowderStrength",
            "cheekCenterBoost",
            "cheekPowderStrength * coverage * 0.92",
            "cheekCenterBoost * coverage",
            "Blend [_SrcBlend] [_DstBlend]",
            "lerp(0.36, 0.57, saturate(_Coverage))",
        ),
    )
    require_no_text(
        SHADER_PATH,
        (
            "cheekSkinTint",
            "cheekSkinMelt",
            "cheekEdgeTint",
        ),
    )
    for path in (APP_PATH, RNBRIDGE_PATH, OVERLAY_PATH):
        require_no_text(path, ("soft_blush",))

    print(json.dumps({"status": "ok", "masks": verify_masks()}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
