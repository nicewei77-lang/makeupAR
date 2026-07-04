#!/usr/bin/env python3
"""Verify eyebrow boundary-first atlas evidence before Unity/RN builds."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


EXPECTED_FACE_SOURCE = "/Users/yeoduchi/Downloads/사용자 첨부 파일.png"
EXPECTED_MASK_ID = "eyebrow-hair-atlas-v1"
EXPECTED_UNITY_MASK_IDS = [
    "eyebrow-hair-atlas-1-v1",
    "eyebrow-hair-atlas-2-v1",
    "eyebrow-hair-atlas-3-v1",
    "eyebrow-hair-atlas-4-v1",
    "eyebrow-hair-atlas-5-v1",
]
EXPECTED_SELECTED_CANDIDATE = 5
EXPECTED_BOUNDARY_MASK_ID = "eyebrow-boundary-mask-v1"
APP_PATH = Path("rn/MakeupARValidation/App.tsx")
RN_TEST_PATH = Path("rn/MakeupARValidation/__tests__/App.test.tsx")
RN_BRIDGE_PATH = Path("unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs")
OVERLAY_PATH = Path("unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs")
SHADER_PATH = Path("unity/MakeupARUnityValidation/Assets/Shaders/EyebrowRegionMask.shader")
MATERIAL_PATH = Path("unity/MakeupARUnityValidation/Assets/Resources/EyebrowRegionMaskMaterial.mat")
RUNTIME_CONTRACT_VERIFIER_PATH = Path(
    "scripts/e7_reference_atlas/verify_eyebrow_runtime_contract.py"
)
EYEBROW_SHADER_GUID = "58f9507dc56340cb9f2f6945e55e99a0"
EXPECTED_EYEBROW_COLORS = {
    "black": "#171412",
    "dark_brown": "#3B2A22",
    "brown": "#6B4A34",
    "light_brown": "#8B6447",
    "wine": "#6A243B",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("evidence/e7-reference-atlas/eyebrow-validation-v1/summary.json"),
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def resolve(repo: Path, path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else repo / path


def verify_boundary_side(side_name: str, side: dict[str, object]) -> None:
    polygon = side.get("polygon", [])
    tight = side["tightBbox"]
    tight_width = int(tight["width"])
    tight_height = int(tight["height"])
    require(len(polygon) >= 80, f"{side_name} polygon should be a smoothed brow boundary")
    require(315 <= tight_width <= 355, f"{side_name} tight width out of v10 range: {tight_width}")
    require(58 <= tight_height <= 78, f"{side_name} tight height out of v10 range: {tight_height}")
    require(
        side.get("fallbackReason") == "approved_manual_boundary_v10_runtime_y_aligned_tail_extended",
        f"{side_name} must use approved v10 runtime-y-aligned boundary",
    )


def verify_mirrored_pair(boundary: dict[str, object]) -> None:
    left = boundary["screenLeft"]["tightBbox"]
    right = boundary["screenRight"]["tightBbox"]
    width_delta = abs(int(left["width"]) - int(right["width"]))
    height_delta = abs(int(left["height"]) - int(right["height"]))
    require(width_delta <= 22, f"mirrored boundary width mismatch: {width_delta}")
    require(height_delta <= 8, f"mirrored boundary height mismatch: {height_delta}")


def verify_runtime_spline_contract(repo: Path, overlay_text: str) -> str:
    verifier_path = repo / RUNTIME_CONTRACT_VERIFIER_PATH
    require(verifier_path.exists(), "missing eyebrow runtime spline contract verifier")
    spec = importlib.util.spec_from_file_location(
        "verify_eyebrow_runtime_contract",
        verifier_path,
    )
    require(spec is not None and spec.loader is not None, "could not load runtime contract verifier")
    module = importlib.util.module_from_spec(spec)
    previous_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous_write_bytecode
    result = module.verify_overlay_contract(overlay_text)
    require(
        "styled spline envelope drives UV mask" in result,
        "runtime contract verifier did not confirm styled spline UV mask",
    )
    return result


def main() -> None:
    args = parse_args()
    repo = args.repo_root.resolve()
    summary_path = resolve(repo, str(args.summary))
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    require(summary["unityMaskId"] == EXPECTED_MASK_ID, "unexpected unity mask id")
    require(summary["selectedCandidate"] == EXPECTED_SELECTED_CANDIDATE, "unexpected selected candidate")
    require(summary["greenEvidenceEligible"] is True, "face source must be Green-eligible")
    require(
        summary["sourceAssets"]["face"]["sourcePath"] == EXPECTED_FACE_SOURCE,
        "preview face source is not the requested eyebrow-visible image",
    )
    require(
        EXPECTED_FACE_SOURCE in summary["previewTargetRule"],
        "preview target rule does not name the eyebrow-visible source",
    )
    require(
        "blush screenshot" in summary["wrongTargetGuard"],
        "wrong-target guard is missing",
    )

    boundary = summary["eyebrowBoundary"]
    require(boundary["id"] == "eyebrow-boundary-v1", "boundary id mismatch")
    require(
        boundary["version"] == "actual_boundary_v10_runtime_y_aligned_tail_extended_candidate_shape",
        "boundary version mismatch",
    )
    verify_boundary_side("screenLeft", boundary["screenLeft"])
    verify_boundary_side("screenRight", boundary["screenRight"])
    verify_mirrored_pair(boundary)

    for key in (
        "eyebrowBoundaryOverlayPath",
        "eyebrowBoundaryMaskPath",
        "eyebrowBoundarySummaryPath",
        "contactSheetPath",
        "previewSheetPath",
        "selectedColorVariantSheetPath",
        "allMaskColorVariantSheetPath",
        "unityResourcePath",
    ):
        require(resolve(repo, summary[key]).exists(), f"missing artifact: {key}")
    require(
        resolve(
            repo,
            "evidence/e7-reference-atlas/eyebrow-validation-v1/eyebrow_boundary_face_local_v10_runtime_y_aligned_cleanup_rgba.png",
        ).exists(),
        "missing v10 face-local eyebrow boundary diagnostic texture",
    )
    require(
        resolve(
            repo,
            "evidence/e7-reference-atlas/eyebrow-validation-v1/eyebrow_boundary_face_local_v10_runtime_y_aligned_cleanup_preview.png",
        ).exists(),
        "missing v10 face-local eyebrow boundary diagnostic preview",
    )
    source_manifest_path = resolve(
        repo,
        "evidence/e7-reference-atlas/eyebrow-validation-v1/source/source_manifest.sha256",
    )
    require(source_manifest_path.exists(), "missing source manifest")
    source_manifest_text = source_manifest_path.read_text(encoding="utf-8")
    for source_name in ("face.png", "candidate-1.png", "candidate-5.png"):
        require(source_name in source_manifest_text, f"source manifest missing {source_name}")

    selected = next(
        candidate
        for candidate in summary["candidateSummaries"]
        if candidate["index"] == EXPECTED_SELECTED_CANDIDATE
    )
    unity_path = resolve(repo, summary["unityResourcePath"])
    require(
        sha256(unity_path) == selected["atlasSha256"] == summary["unityResourceSha256"],
        "Unity resource sha does not match selected candidate atlas",
    )
    boundary_resource = summary.get("unityBoundaryResource", {})
    require(boundary_resource.get("maskId") == EXPECTED_BOUNDARY_MASK_ID, "missing eyebrow boundary resource id")
    boundary_path = resolve(repo, boundary_resource["path"])
    require(boundary_path.exists(), "missing Unity eyebrow boundary texture")
    require(
        sha256(boundary_path) == boundary_resource["sha256"],
        "Unity eyebrow boundary sha mismatch",
    )
    channel_packing = summary.get("boundaryChannelPacking", {})
    require(channel_packing.get("b", "").startswith("wider cleanup band"), "cleanup channel is missing")
    app_text = (repo / APP_PATH).read_text(encoding="utf-8")
    rn_test_text = (repo / RN_TEST_PATH).read_text(encoding="utf-8")
    rn_bridge_text = (repo / RN_BRIDGE_PATH).read_text(encoding="utf-8")
    overlay_text = (repo / OVERLAY_PATH).read_text(encoding="utf-8")
    shader_text = (repo / SHADER_PATH).read_text(encoding="utf-8")
    runtime_contract_result = verify_runtime_spline_contract(repo, overlay_text)
    runtime_contract_label = (
        "styled-spline-uv"
        if "styled spline envelope drives UV mask" in runtime_contract_result
        else "unknown"
    )
    runtime_verifier_text = (
        repo / "scripts/e7_reference_atlas/verify_eyebrow_runtime_evidence.py"
    ).read_text(encoding="utf-8")
    buildgate_text = (
        repo / "evidence/logs/e7-eyebrow-v9-runtime-buildgate-20260701.md"
    ).read_text(encoding="utf-8")
    material_path = repo / MATERIAL_PATH
    require(material_path.exists(), "missing Unity eyebrow Resources material")
    material_text = material_path.read_text(encoding="utf-8")
    require(
        EYEBROW_SHADER_GUID in material_text,
        "Unity eyebrow Resources material is not bound to EyebrowRegionMask shader",
    )
    for color_name, color_value in EXPECTED_EYEBROW_COLORS.items():
        require(color_name in app_text and color_value in app_text, f"eyebrow color option missing: {color_name}")
    require("CORE_RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye']" in app_text, "legacy core 3-region list is missing")
    require("eyebrow: false" in app_text, "eyebrow must be disabled by default")
    require("shouldIncludeEyebrowLayer" in app_text, "RN payload must keep eyebrow optional")
    require("eyebrow-boundary-tone-lift-validation" in app_text, "RN eyebrow tone-lift shader mode missing")
    require(
        "focusedRegion === 'eyebrow' ? undefined : unityEventStatus.recipe_applied" in app_text,
        "RN eyebrow HUD must not fall back to stale non-eyebrow recipe events",
    )
    require(
        "const shouldDisable = isActive && focusedRegion === region" in app_text,
        "RN region focus must preserve already-active lip/cheek layers",
    )
    require(
        "active=lip,cheek,eyebrow" in rn_test_text,
        "RN tests must cover lip+cheek+eyebrow simultaneous activation",
    )
    require(
        "activeRegions=lip,cheek,eyebrow" in rn_test_text
        and "enabledLayerCount=3" in rn_test_text
        and "focusRegion=eyebrow" in rn_test_text,
        "RN tests must verify simultaneous lip+cheek+eyebrow payload posts",
    )
    require(
        "recipe_applied region=eye texture=shimmer_eye" in rn_test_text
        and "recipe_applied waiting" in rn_test_text,
        "RN tests must cover stale eye recipe suppression for eyebrow focus",
    )
    require(
        'FeatureSnapshotRegions = { "lip", "cheek", "eye" }' in rn_bridge_text,
        "Unity feature snapshot must remain limited to lip/cheek/eye",
    )
    require(
        'RecipeLayerRegions = { "lip", "cheek", "eye", "eyebrow" }' in rn_bridge_text,
        "Unity bridge must include optional eyebrow layer region",
    )
    require(
        "recipe.layers.Length != FeatureSnapshotRegions.Length" in rn_bridge_text
        and "recipe.layers.Length != RecipeLayerRegions.Length" in rn_bridge_text,
        "Unity bridge must accept both 3-layer and 4-layer payloads",
    )
    require("IsEyebrowHairMaskTextureId" in rn_bridge_text, "Unity bridge eyebrow mask normalization missing")
    require("BoundaryToneLift" in shader_text and "_ToneLiftStrength" in shader_text, "eyebrow tone-lift shader pass missing")
    for pass_name in ("OuterSkinCleanup", "BoundaryToneLift", "BoundaryTintFill", "BoundaryStrandMultiply"):
        require(pass_name in shader_text, f"eyebrow shader pass missing: {pass_name}")
    require("BrowEndTaper" in shader_text, "eyebrow end taper guard missing")
    require(
        'Resources.Load<Material>("EyebrowRegionMaskMaterial")' in overlay_text,
        "Unity eyebrow renderer must load the Resources material before Shader.Find",
    )
    require("GetEyebrowBoundaryTexture" in overlay_text, "Unity eyebrow boundary texture loader missing")
    require('material.SetTexture("_BoundaryTex", boundaryTexture)' in overlay_text, "Unity eyebrow boundary texture is not bound")
    require("ResolveEyebrowToneLiftStrength" in overlay_text, "Unity eyebrow tone-lift strength resolver missing")
    require(
        "mediapipe_face_landmarker_eyebrow_arface_uv_baked_eye_exclusion_tone_lift_fill_and_strand_multiply" in overlay_text,
        "Unity eyebrow renderer diagnostic does not include tone lift",
    )
    require(
        "BuildEyebrowCalibrationKey" in overlay_text
        and 'return "eyebrow:"' in overlay_text
        and "SanitizeDiagnosticValue(recipe.MaskTextureId)" in overlay_text
        and "shapeIntensity" not in overlay_text,
        "eyebrow UV calibration key must be style-only so opacity/intensity/color changes do not rebake placement",
    )
    require(
        "ApplyEyebrowStyleShape(\n                        screenEyebrowBoundary,\n                        recipe.MaskTextureId)" in overlay_text
        and "private const float EyebrowStyleShapeAmount" in overlay_text,
        "eyebrow style shaping must be independent from runtime intensity sliders",
    )
    require(
        "return Mathf.Max(pixel.r, pixel.g);" in overlay_text,
        "eyebrow mesh culling must use hard/soft brow channels only, not cleanup channels",
    )
    require(
        "lip_cheek_eyebrow" in runtime_verifier_text
        and "mediapipe_face_landmarker_runtime_eyebrow_boundary" in runtime_verifier_text
        and "mediapipe_face_landmarker_eyebrow_arface_uv_baked_eye_exclusion_tone_lift_fill_and_strand_multiply" in runtime_verifier_text,
        "eyebrow runtime verifier does not guard simultaneous lip+cheek+eyebrow evidence",
    )
    require(
        "actual_boundary_v10_runtime_y_aligned_tail_extended_candidate_shape" in buildgate_text
        and "verify_eyebrow_runtime_evidence.py" in buildgate_text,
        "eyebrow runtime Build Gate packet is missing v10/verifier contract",
    )
    unity_candidates = summary.get("unityResourceCandidates", [])
    require(
        len(unity_candidates) >= len(EXPECTED_UNITY_MASK_IDS),
        "not all eyebrow candidate Unity resources are listed",
    )
    candidates_by_id = {
        candidate.get("maskId"): candidate for candidate in unity_candidates
    }
    for expected_index, mask_id in enumerate(EXPECTED_UNITY_MASK_IDS, start=1):
        candidate = candidates_by_id.get(mask_id)
        require(candidate is not None, f"missing Unity eyebrow resource listing: {mask_id}")
        resource_path = resolve(repo, candidate["path"])
        require(resource_path.exists(), f"missing Unity eyebrow resource file: {mask_id}")
        source_candidate = next(
            item for item in summary["candidateSummaries"] if item["index"] == expected_index
        )
        require(
            sha256(resource_path) == source_candidate["atlasSha256"] == candidate["sha256"],
            f"Unity eyebrow resource sha mismatch: {mask_id}",
        )
    profile_morphs = {
        int(candidate["index"]): int(candidate["candidateChannelProfile"]["morph"])
        for candidate in summary["candidateSummaries"]
    }
    require(
        profile_morphs == {1: -1, 2: 0, 3: 1, 4: 2, 5: 1},
        f"eyebrow candidate profiles are not distinct enough: {profile_morphs}",
    )
    require(
        "ShouldCullMeshToMask" in overlay_text
        and "ResolveMeshCullMask" in overlay_text
        and "EyebrowBoundaryMaskId" in overlay_text
        and "eyebrow_boundary_threshold_sample" in overlay_text,
        "Unity eyebrow mesh must be culled by boundary mask, not by candidate hair atlas",
    )
    require(
        "eyebrow_atlas_threshold_sample" not in overlay_text,
        "stale eyebrow atlas-based mesh culling diagnostic remains",
    )

    print(
        "eyebrow atlas ok:",
        "candidate=5",
        "unityCandidates=5",
        "boundary=eyebrow-boundary-v1/v10-y-align-tail",
        "cleanup=outer-skin",
        "runtimeContract=" + runtime_contract_label,
        "unity=" + str(unity_path),
    )


if __name__ == "__main__":
    main()
