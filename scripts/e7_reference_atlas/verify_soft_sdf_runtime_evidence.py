#!/usr/bin/env python3
"""Verify post-build E7.3 soft-SDF runtime diagnostics from a captured log."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CORE_PATTERNS = {
    "activeLipArfaceAtlas": [
        "maskTextureId=lip-drawn-style-atlas-v1",
        '"maskTextureId":"lip-drawn-style-atlas-v1"',
        "maskTex=lip-drawn-style-atlas-v1",
        "maskSource=lip_style_atlas_v1_uv_back_projection",
        '"maskSource":"lip_style_atlas_v1_uv_back_projection"',
        "src=lip_style_atlas_v1_uv_back_projection",
    ],
    "softSdfLayerMode": [
        "lipRenderLayerMode=soft_sdf_logical_multilayer",
        '"lipRenderLayerMode":"soft_sdf_logical_multilayer"',
        "layers=soft_sdf_logical_multilayer",
    ],
    "wideFeatherSampleMode": [
        "maskSoftSampleMode=feather_scaled_13tap_near_far",
        '"maskSoftSampleMode":"feather_scaled_13tap_near_far"',
        "soft=feather_scaled_13tap_near_far",
    ],
    "wideFeatherRadius": [
        "maskFeatherNearRadiusPx",
        "maskFeatherFarRadiusPx",
        "featherPx=",
    ],
    "glowGlossSheen": [
        "glossHighlightMode=matte_base_wet_sheen",
        '"glossHighlightMode":"matte_base_wet_sheen"',
        "gloss=matte_base_wet_sheen",
    ],
    "matteNoGloss": [
        "glossHighlightMode=none",
        '"glossHighlightMode":"none"',
        "gloss=none",
    ],
    "visionSoftUvBake": [
        "maskDiag=vision_arface_uv_baked_outer_minus_inner_soft_falloff",
        "maskTextureDiagnosticStatus=vision_arface_uv_baked_outer_minus_inner_soft_falloff",
        '"maskTextureDiagnosticStatus":"vision_arface_uv_baked_outer_minus_inner_soft_falloff"',
    ],
    "visionArfaceUvCoordinate": [
        "->arface-uv-bake",
        '"visionBoundaryCoordinateMode":"raw-y->flip-y->face-local-warp->arface-uv-bake"',
        "visionCoord=raw-y->flip-y->face-local-warp->arface-uv-bake",
    ],
    "visionMotionScore": [
        "visionBoundaryFaceMotionScore",
        "visionMotion=",
    ],
    "visionMotionRisk": [
        "visionBoundaryFaceMotionRisk",
        "medium_face_motion",
        "large_face_motion",
    ],
}

STYLE_PATTERNS = {
    "matte": ["matte_lip", "finish matte_lip"],
    "glow": ["gloss_lip", "finish gloss_lip"],
    "gradient": ["gradient_lip", "finish gradient_lip"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify E7.3 soft-SDF runtime log diagnostics after an approved iPhone run.",
    )
    parser.add_argument("log", type=Path, help="Runtime console/log file to verify.")
    parser.add_argument(
        "--no-require-vision-compare",
        action="store_true",
        help="Do not require Vision debug/compare ARFace UV bake diagnostics.",
    )
    parser.add_argument(
        "--no-require-motion-diagnostics",
        action="store_true",
        help="Do not require Vision face-motion diagnostic fields.",
    )
    parser.add_argument(
        "--require-styles",
        default="matte,glow,gradient",
        help="Comma-separated style markers to require. Default: matte,glow,gradient.",
    )
    parser.add_argument(
        "--allow-active-vision-lip",
        action="store_true",
        help=(
            "Allow the first active lip recipe in the log to use lip-vision-boundary-v1. "
            "Default requires the active lip path to start on ARFace-attached lip-drawn-style-atlas-v1; "
            "Vision may still appear later as an explicit debug/compare path."
        ),
    )
    return parser.parse_args()


def read_log(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"Missing runtime log: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def count_any(text: str, needles: list[str]) -> int:
    return sum(text.count(needle) for needle in needles)


def extract_numeric_values(text: str, field: str) -> list[float]:
    values: list[float] = []
    patterns = [
        rf"{re.escape(field)}[=:]\s*(-?\d+(?:\.\d+)?)",
        rf'"{re.escape(field)}"\s*:\s*(-?\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        values.extend(float(match) for match in re.findall(pattern, text))
    return values


def extract_first_active_lip_recipe(text: str) -> dict[str, Any]:
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "recipe_applied" not in line:
            continue
        if "region=lip" not in line and '"region":"lip"' not in line:
            continue
        if (
            "applied=true" not in line
            and '"applied":true' not in line
            and " applied True" not in line
        ):
            continue

        mask_texture_id = "unknown"
        for pattern in (
            r"maskTextureId=([^\s]+)",
            r"maskTex=([^\s]+)",
            r'"maskTextureId"\s*:\s*"([^"]+)"',
        ):
            match = re.search(pattern, line)
            if match:
                mask_texture_id = match.group(1)
                break

        return {
            "lineNumber": line_number,
            "maskTextureId": mask_texture_id,
            "line": line.strip()[:360],
        }

    return {
        "lineNumber": None,
        "maskTextureId": None,
        "line": None,
    }


def extract_lip_recipe_mask_ids(text: str) -> list[str]:
    mask_ids: list[str] = []
    for line in text.splitlines():
        if "recipe_applied" not in line:
            continue
        if "region=lip" not in line and '"region":"lip"' not in line:
            continue
        for pattern in (
            r"maskTextureId=([^\s]+)",
            r"maskTex=([^\s]+)",
            r'"maskTextureId"\s*:\s*"([^"]+)"',
        ):
            match = re.search(pattern, line)
            if match:
                mask_ids.append(match.group(1))
                break
    return mask_ids


def build_requirements(args: argparse.Namespace) -> dict[str, list[str]]:
    requirements = {
        "activeLipArfaceAtlas": CORE_PATTERNS["activeLipArfaceAtlas"],
        "softSdfLayerMode": CORE_PATTERNS["softSdfLayerMode"],
        "wideFeatherSampleMode": CORE_PATTERNS["wideFeatherSampleMode"],
        "wideFeatherRadius": CORE_PATTERNS["wideFeatherRadius"],
        "glowGlossSheen": CORE_PATTERNS["glowGlossSheen"],
        "matteNoGloss": CORE_PATTERNS["matteNoGloss"],
    }

    styles = [style.strip() for style in args.require_styles.split(",") if style.strip()]
    for style in styles:
        if style not in STYLE_PATTERNS:
            raise SystemExit(f"Unsupported style marker in --require-styles: {style}")
        requirements[f"style:{style}"] = STYLE_PATTERNS[style]

    if not args.no_require_vision_compare:
        requirements["visionSoftUvBake"] = CORE_PATTERNS["visionSoftUvBake"]
        requirements["visionArfaceUvCoordinate"] = CORE_PATTERNS["visionArfaceUvCoordinate"]

    if not args.no_require_motion_diagnostics:
        requirements["visionMotionScore"] = CORE_PATTERNS["visionMotionScore"]
        requirements["visionMotionRisk"] = CORE_PATTERNS["visionMotionRisk"]

    return requirements


def verify(text: str, args: argparse.Namespace) -> dict[str, Any]:
    requirements = build_requirements(args)
    results: dict[str, dict[str, Any]] = {}
    missing: list[str] = []

    for name, patterns in requirements.items():
        present = contains_any(text, patterns)
        results[name] = {
            "present": present,
            "count": count_any(text, patterns),
            "patterns": patterns,
        }
        if not present:
            missing.append(name)

    first_active_lip_recipe = extract_first_active_lip_recipe(text)
    first_active_lip_mask_id = first_active_lip_recipe["maskTextureId"]
    if first_active_lip_mask_id is None:
        missing.append("firstActiveLipRecipe")
    elif (
        not args.allow_active_vision_lip
        and first_active_lip_mask_id != "lip-drawn-style-atlas-v1"
    ):
        missing.append("firstActiveLipRecipeArfaceAtlas")

    lip_recipe_mask_ids = extract_lip_recipe_mask_ids(text)
    motion_scores = extract_numeric_values(text, "visionBoundaryFaceMotionScore")
    compact_motion_scores = re.findall(r"visionMotion=(-?\d+(?:\.\d+)?)/", text)
    motion_scores.extend(float(value) for value in compact_motion_scores)
    near_feather_radius = extract_numeric_values(text, "maskFeatherNearRadiusPx")
    far_feather_radius = extract_numeric_values(text, "maskFeatherFarRadiusPx")
    compact_feather_radius = re.findall(r"featherPx=(-?\d+(?:\.\d+)?)/(-?\d+(?:\.\d+)?)", text)
    near_feather_radius.extend(float(value[0]) for value in compact_feather_radius)
    far_feather_radius.extend(float(value[1]) for value in compact_feather_radius)
    if not near_feather_radius:
        missing.append("wideFeatherNearRadiusNumeric")
    elif max(near_feather_radius) < 3.0:
        missing.append("wideFeatherNearRadiusTooNarrow")
    if not far_feather_radius:
        missing.append("wideFeatherFarRadiusNumeric")
    elif max(far_feather_radius) < 6.0:
        missing.append("wideFeatherFarRadiusTooNarrow")

    return {
        "status": "pass" if not missing else "fail",
        "scope": "E7.3 soft-SDF runtime acceptance diagnostics",
        "requirements": results,
        "missing": missing,
        "metrics": {
            "lineCount": text.count("\n") + 1 if text else 0,
            "recipeAppliedCount": text.count("recipe_applied"),
            "regionMaskApplyCount": text.count("region_mask_apply"),
            "firstActiveLipRecipe": first_active_lip_recipe,
            "lipRecipeMaskIds": lip_recipe_mask_ids[:12],
            "nearFeatherRadiusSamples": near_feather_radius,
            "farFeatherRadiusSamples": far_feather_radius,
            "minNearFeatherRadius": min(near_feather_radius) if near_feather_radius else None,
            "maxFarFeatherRadius": max(far_feather_radius) if far_feather_radius else None,
            "motionScoreSamples": motion_scores,
            "maxMotionScore": max(motion_scores) if motion_scores else None,
        },
        "notes": [
            "This verifies log/HUD diagnostic fields only.",
            "By default it requires the first active lip recipe to use the ARFace-attached lip-drawn-style-atlas-v1 path; Vision boundary logs are allowed as explicit debug/compare evidence.",
            "It does not replace required runtime photos for visual boundary/gloss acceptance.",
        ],
    }


def main() -> None:
    args = parse_args()
    text = read_log(args.log)
    result = verify(text, args)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
