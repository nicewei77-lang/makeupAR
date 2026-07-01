#!/usr/bin/env python3
"""Verify E7 eyebrow runtime evidence after an approved iPhone run."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


EYEBROW_MASK_PATTERN = r"eyebrow-hair-atlas-[1-5]-v1"
SCENARIO_LABELS = (
    "eyebrow_off_baseline",
    "eyebrow_only",
    "lip_cheek_eyebrow",
    "yaw_pitch",
    "expression_change",
    "tracking_reacquire",
)


REQUIREMENTS: dict[str, list[str]] = {
    "eyebrow_recipe_applied": ["recipe_applied region=eyebrow", '"region":"eyebrow"'],
    "eyebrow_tracking_render": ["state=tracking_render", '"stateAction":"tracking_render"', "tracking_render"],
    "eyebrow_boundary_source": [
        "maskSource=face_local_actual_brow_boundary_with_user_texture_density",
        '"maskSource":"face_local_actual_brow_boundary_with_user_texture_density"',
        "src=face_local_actual_brow_boundary_with_user_texture_density",
    ],
    "eyebrow_boundary_renderer": [
        "boundaryRenderer=eyebrow_boundary_clipped_cleanup_tone_lift_fill_and_strand_multiply",
        '"boundaryRenderer":"eyebrow_boundary_clipped_cleanup_tone_lift_fill_and_strand_multiply"',
        "renderer=eyebrow_boundary_clipped_cleanup_tone_lift_fill_and_strand_multiply",
    ],
    "wide_feather_sampling": [
        "maskSoftSampleMode=feather_scaled_13tap_near_far",
        '"maskSoftSampleMode":"feather_scaled_13tap_near_far"',
        "soft=feather_scaled_13tap_near_far",
    ],
    "eyebrow_boundary_mesh_culling": [
        "meshCullingMode=eyebrow_boundary_threshold_sample",
        '"meshCullingMode":"eyebrow_boundary_threshold_sample"',
        "cullMode=eyebrow_boundary_threshold_sample",
    ],
    "simultaneous_regions": [
        "active=lip,cheek,eyebrow",
        "activeRegions=lip,cheek,eyebrow",
        '"activeRegions":"lip,cheek,eyebrow"',
    ],
    "focus_eyebrow": ["focus=eyebrow", "focusRegion=eyebrow", '"focusRegion":"eyebrow"'],
    "lip_still_applied": ["recipe_applied region=lip", '"region":"lip"'],
    "cheek_still_applied": ["recipe_applied region=cheek", '"region":"cheek"'],
    "tracking_face_mesh": [
        "tracking=Tracking",
        "trackingState=Tracking",
        "mesh=v=1220/i=6912/uv=1220",
        "mesh/UV counts 1220/6912/1220",
    ],
    "fps": ["fps=", "averageFps", '"fps"'],
    "frame_time": ["frame=", "frameTimeMs", '"frameTimeMs"'],
    "latency": ["latency=", "recipeLatencyMs", "latencyMs", '"recipeLatencyMs"'],
    "thermal": ["thermal=", "thermalState", '"thermalState"'],
    "memory": ["memory=", "memoryMB", "residentMemoryMB", '"memoryMB"'],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify eyebrow runtime logs and scenario notes before marking eyebrow Green.",
    )
    parser.add_argument("log", nargs="?", type=Path, help="Runtime console/log file.")
    parser.add_argument(
        "--scenario-summary",
        type=Path,
        help="Markdown/text summary containing required runtime scenario labels.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run built-in pass/fail contract checks.")
    return parser.parse_args()


def read_optional(path: Path | None) -> str:
    if path is None:
        return ""
    if not path.exists():
        raise SystemExit(f"Missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def contains_any(text: str, needles: list[str]) -> bool:
    return any(needle in text for needle in needles)


def extract_numeric_values(text: str, field_names: tuple[str, ...]) -> list[float]:
    values: list[float] = []
    for field_name in field_names:
        patterns = (
            rf"{re.escape(field_name)}[=:]\s*(-?\d+(?:\.\d+)?)",
            rf'"{re.escape(field_name)}"\s*:\s*(-?\d+(?:\.\d+)?)',
        )
        for pattern in patterns:
            values.extend(float(match) for match in re.findall(pattern, text))
    values.extend(float(match) for match in re.findall(r"frame=(-?\d+(?:\.\d+)?)ms", text))
    values.extend(float(match) for match in re.findall(r"latency=(-?\d+(?:\.\d+)?)ms", text))
    return values


def verify(text: str) -> dict[str, Any]:
    missing: list[str] = []
    results: dict[str, dict[str, Any]] = {}

    for name, patterns in REQUIREMENTS.items():
        present = contains_any(text, patterns)
        results[name] = {"present": present, "patterns": patterns}
        if not present:
            missing.append(name)

    if re.search(EYEBROW_MASK_PATTERN, text) is None:
        missing.append("eyebrow_mask_candidate_1_to_5")

    missing_scenarios = [label for label in SCENARIO_LABELS if label not in text]
    missing.extend(f"scenario:{label}" for label in missing_scenarios)

    fps_values = extract_numeric_values(text, ("fps", "averageFps"))
    frame_values = extract_numeric_values(text, ("frameTimeMs",))
    latency_values = extract_numeric_values(text, ("recipeLatencyMs", "latencyMs"))
    if fps_values and max(fps_values) < 45.0:
        missing.append("fps_too_low_for_validation")
    if frame_values and min(frame_values) > 25.0:
        missing.append("frame_time_too_high_for_validation")
    if latency_values and min(latency_values) > 80.0:
        missing.append("latency_too_high_for_validation")

    forbidden = []
    if "active=eyebrow / focus=eyebrow" in text and "recipe_applied region=eye" in text:
        forbidden.append("stale_eye_recipe_while_eyebrow_focused")
    if "active=lip,cheek,eyebrow" in text and "recipe_applied region=eyebrow" not in text:
        forbidden.append("simultaneous_ui_without_eyebrow_apply")
    missing.extend(forbidden)

    return {
        "status": "pass" if not missing else "fail",
        "scope": "E7 eyebrow runtime evidence",
        "missing": missing,
        "requirements": results,
        "metrics": {
            "lineCount": text.count("\n") + 1 if text else 0,
            "recipeAppliedCount": text.count("recipe_applied"),
            "fpsSamples": fps_values[:12],
            "frameTimeSamples": frame_values[:12],
            "latencySamples": latency_values[:12],
        },
        "notes": [
            "This verifies runtime log and scenario-summary evidence only.",
            "It does not replace visual review of eyebrow attachment, tail fit, color, or sticker drift.",
            "It intentionally requires lip+cheek+eyebrow simultaneous evidence so eyebrow cannot disable existing makeup.",
        ],
    }


def run_self_test() -> None:
    passing = "\n".join(
        [
            "scenario=eyebrow_off_baseline visual=pass",
            "scenario=eyebrow_only visual=pass",
            "scenario=lip_cheek_eyebrow visual=pass",
            "scenario=yaw_pitch visual=pass",
            "scenario=expression_change visual=pass",
            "scenario=tracking_reacquire visual=pass",
            "[E7] rn_texture_recipe_batch_post activeRegions=lip,cheek,eyebrow focusRegion=eyebrow eyebrowMaskTextureId=eyebrow-hair-atlas-5-v1",
            "[E7] recipe_applied region=lip applied=true state=tracking_render",
            "[E7] recipe_applied region=cheek applied=true state=tracking_render",
            "[E7] recipe_applied region=eyebrow applied=true state=tracking_render maskTextureId=eyebrow-hair-atlas-5-v1 maskSource=face_local_actual_brow_boundary_with_user_texture_density boundaryRenderer=eyebrow_boundary_clipped_cleanup_tone_lift_fill_and_strand_multiply maskSoftSampleMode=feather_scaled_13tap_near_far meshCullingMode=eyebrow_boundary_threshold_sample",
            "AR Status tracking=Tracking faces=1 mesh=v=1220/i=6912/uv=1220 fps=59.8 frame=16.7ms latency=22.0ms thermal=nominal memory=412MB",
        ]
    )
    failing = passing.replace("recipe_applied region=eyebrow", "recipe_applied region=eye")
    pass_result = verify(passing)
    fail_result = verify(failing)
    if pass_result["status"] != "pass":
        raise SystemExit(json.dumps(pass_result, indent=2))
    if fail_result["status"] != "fail":
        raise SystemExit("self-test expected missing eyebrow runtime evidence")
    print("eyebrow runtime verifier self-test ok")


def main() -> None:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return
    if args.log is None:
        raise SystemExit("log path is required unless --self-test is used")
    text = read_optional(args.log) + "\n" + read_optional(args.scenario_summary)
    result = verify(text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
