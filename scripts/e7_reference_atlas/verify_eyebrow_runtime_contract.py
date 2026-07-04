#!/usr/bin/env python3
"""Verify the Unity eyebrow runtime uses styled spline envelope masks."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


UNITY_OVERLAY = Path(
    "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--overlay", type=Path, default=UNITY_OVERLAY)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_overlay(repo_root: Path, overlay: Path) -> str:
    path = overlay if overlay.is_absolute() else repo_root / overlay
    require(path.exists(), f"missing Unity overlay script: {path}")
    return path.read_text(encoding="utf-8")


def extract_method(source: str, name: str) -> str:
    match = re.search(
        rf"\n\s+private(?: static)? [^;\n]+ {re.escape(name)}\([^)]*\)\s*\{{",
        source,
        re.MULTILINE,
    )
    require(match is not None, f"missing method: {name}")
    start = match.end()
    depth = 1
    index = start
    while index < len(source) and depth > 0:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    require(depth == 0, f"could not parse method body: {name}")
    return source[start : index - 1]


def verify_overlay_contract(source: str) -> str:
    render_path = extract_method(source, "TryUpdateFullFaceUvMesh")
    style_method = extract_method(source, "ApplyEyebrowStyleShape")
    bake_method = extract_method(source, "ApplyEyebrowBoundaryUvMask")
    build_mask_method = extract_method(source, "BuildEyebrowUvMaskPixels")
    inside_method = extract_method(source, "IsPointInsideEyebrowBoundary")
    cleanup_method = extract_method(source, "IsPointInsideEyebrowCleanupBoundary")

    style_pos = render_path.find("ApplyEyebrowStyleShape(")
    bake_pos = render_path.find("ApplyEyebrowBoundaryUvMask(")
    require(style_pos >= 0, "eyebrow render path must apply styled spline shape")
    require(bake_pos >= 0, "eyebrow render path must bake ARFace UV mask")
    require(style_pos < bake_pos, "styled spline shape must be applied before UV bake")

    require(
        "ShapeEyebrowBoundaryPoints(" in style_method,
        "ApplyEyebrowStyleShape must rebuild brow boundary points",
    )
    require(
        "head_body_arch_bodySpline_AS_tailLinear_styled" in style_method,
        "styled control point mode is missing",
    )
    require(
        "raw_boundary_position_width_scale_only" in style_method,
        "raw boundary usage must stay position/width/scale only",
    )
    require(
        "BuildEyebrowControlPoints(" in style_method
        and "SampleEyebrowBoundaryCenter(" in style_method,
        "styled H/B/A/S/T diagnostics must be rebuilt from styled points",
    )

    require(
        "BuildEyebrowUvMaskPixels(" in bake_method,
        "ApplyEyebrowBoundaryUvMask must build runtime UV mask pixels",
    )
    require(
        "styled_spline_envelope_boundary" in bake_method
        or "styled_spline_envelope_boundary" in source,
        "UV mask source diagnostic must name styled spline envelope",
    )
    require(
        "eyebrow_arface_uv_baked_styled_spline_envelope_minus_eye_exclusion"
        in build_mask_method,
        "runtime mask diagnostics must name styled spline envelope bake",
    )

    require(
        "IsPointInsideEyebrowBoundary(point, boundary)" in build_mask_method,
        "UV mask hard coverage must test styled boundary",
    )
    require(
        "IsPointInsideEyebrowCleanupBoundary(point, boundary)" in build_mask_method,
        "UV mask cleanup coverage must test styled boundary",
    )
    require(
        "IsPointInsideEyebrowBoundary(point, sourceBoundary)" not in build_mask_method,
        "sourceBoundary must not drive hard brow mask coverage",
    )
    require(
        "IsPointInsideEyebrowCleanupBoundary(point, sourceBoundary)" not in build_mask_method,
        "sourceBoundary must not drive cleanup coverage",
    )
    require(
        "CalculateEyebrowBoundaryBbox(\n            boundary," in build_mask_method,
        "UV bake bounds must be calculated from styled boundary",
    )

    require(
        "IsPointInPolygon(point, boundary.LeftOuterPoints)" in inside_method
        and "IsPointInPolygon(point, boundary.RightOuterPoints)" in inside_method,
        "inside test must use styled left/right outer points",
    )
    require(
        "IsPointInsideEyebrowEyeExclusion(" in inside_method,
        "inside test must subtract eye exclusion",
    )
    require(
        "IsPointInScaledPolygon(point, boundary.LeftOuterPoints" in cleanup_method
        and "IsPointInScaledPolygon(point, boundary.RightOuterPoints" in cleanup_method,
        "cleanup neutralizer must expand styled brow envelope",
    )

    return "eyebrow runtime contract ok: styled spline envelope drives UV mask"


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    print(verify_overlay_contract(read_overlay(repo_root, args.overlay)))


if __name__ == "__main__":
    main()
