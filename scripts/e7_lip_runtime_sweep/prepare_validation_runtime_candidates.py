#!/usr/bin/env python3
"""Prepare validation-only E7 lip runtime candidate assets.

This script is buildless and local-only. It projects the current provisional
screen-space lip candidate masks into UV probability maps, installs the maps as
Unity Resources, and writes a registry for the later phone runtime sweep.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


DEFAULT_PACKAGE = Path("evidence/e7-lip-m1-packages/m1-lip-auto-selected-20260625T215327Z")
DEFAULT_CAPTURE_PAIR = Path("evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03")
DEFAULT_OUTPUT_ROOT = Path("evidence/e7-lip-runtime-sweep-prep")
UNITY_MASK_DIR = Path("unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks")
PROJECTION_SCRIPT = Path("scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py")

CANDIDATES = (
    {
        "candidateId": "lip-tight-auto-v0",
        "label": "Auto tight lip boundary draft",
        "screenMask": "lip-tight-auto-v0_mask.png",
        "unityMaskTextureId": "e7-lip-validation-tight-auto-v0",
        "threshold": 0.50,
        "coverage": 0.72,
        "feather": 0.08,
        "usesUserAdjustment": False,
    },
    {
        "candidateId": "lip-tight-user-v0",
        "label": "User-adjusted lip boundary draft",
        "screenMask": "lip-tight-user-v0_mask.png",
        "unityMaskTextureId": "e7-lip-validation-tight-user-v0",
        "threshold": 0.50,
        "coverage": 0.72,
        "feather": 0.08,
        "usesUserAdjustment": True,
    },
    {
        "candidateId": "lip-safe-v0",
        "label": "Spill-prevention lip boundary draft",
        "screenMask": "lip-safe-v0_mask.png",
        "unityMaskTextureId": "e7-lip-validation-safe-v0",
        "threshold": 0.65,
        "coverage": 0.64,
        "feather": 0.06,
        "usesUserAdjustment": True,
    },
)
DEFAULT_ADJUSTMENT_PARAMS = {
    "cornerReach": 0.0,
    "upperLipTightness": 0.0,
    "lowerLipTightness": 0.0,
    "verticalOffset": 0.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install validation-only E7 lip runtime candidate masks."
    )
    parser.add_argument("--package-dir", type=Path, default=DEFAULT_PACKAGE)
    parser.add_argument("--capture-pair", type=Path, default=DEFAULT_CAPTURE_PAIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, body: str) -> None:
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8-sig"))


def rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def guid_for_asset(asset_path: Path) -> str:
    return hashlib.md5(str(asset_path).encode("utf-8")).hexdigest()


def write_unity_png_meta(path: Path) -> None:
    path.with_suffix(path.suffix + ".meta").write_text(
        "\n".join(
            [
                "fileFormatVersion: 2",
                f"guid: {guid_for_asset(path)}",
                "TextureImporter:",
                "  internalIDToNameTable: []",
                "  externalObjects: {}",
                "  serializedVersion: 13",
                "  mipmaps:",
                "    mipMapMode: 0",
                "    enableMipMap: 0",
                "    sRGBTexture: 0",
                "    linearTexture: 0",
                "    fadeOut: 0",
                "    borderMipMap: 0",
                "    mipMapsPreserveCoverage: 0",
                "    alphaTestReferenceValue: 0.5",
                "    mipMapFadeDistanceStart: 1",
                "    mipMapFadeDistanceEnd: 3",
                "  bumpmap:",
                "    convertToNormalMap: 0",
                "    externalNormalMap: 0",
                "    heightScale: 0.25",
                "    normalMapFilter: 0",
                "    flipGreenChannel: 0",
                "  isReadable: 1",
                "  streamingMipmaps: 0",
                "  textureSettings:",
                "    serializedVersion: 2",
                "    filterMode: 1",
                "    aniso: 1",
                "    mipBias: 0",
                "    wrapU: 1",
                "    wrapV: 1",
                "    wrapW: 1",
                "  textureFormat: 1",
                "  maxTextureSize: 2048",
                "  alphaUsage: 1",
                "  alphaIsTransparency: 0",
                "  textureType: 0",
                "  textureShape: 1",
                "  platformSettings:",
                "  - serializedVersion: 4",
                "    buildTarget: DefaultTexturePlatform",
                "    maxTextureSize: 2048",
                "    textureFormat: -1",
                "    textureCompression: 0",
                "    overridden: 0",
                "  spriteSheet:",
                "    serializedVersion: 2",
                "    sprites: []",
                "    outline: []",
                "    customData: ",
                "    physicsShape: []",
                "    bones: []",
                "    spriteID: ",
                "    internalID: 0",
                "    vertices: []",
                "    indices: ",
                "    edges: []",
                "    weights: []",
                "    secondaryTextures: []",
                "    nameFileIdTable: {}",
                "  assetBundleName: ",
                "  assetBundleVariant: ",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_unity_text_meta(path: Path) -> None:
    path.with_suffix(path.suffix + ".meta").write_text(
        "\n".join(
            [
                "fileFormatVersion: 2",
                f"guid: {guid_for_asset(path)}",
                "TextScriptImporter:",
                "  externalObjects: {}",
                "  userData: ",
                "  assetBundleName: ",
                "  assetBundleVariant: ",
                "",
            ]
        ),
        encoding="utf-8",
    )


def install_probability_png(source: Path, target: Path) -> None:
    gray = Image.open(source).convert("L")
    rgba = Image.merge("RGBA", (gray, gray, gray, Image.new("L", gray.size, 255)))
    target.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(target)
    write_unity_png_meta(target)


def run_projection(
    repo_root: Path,
    package_dir: Path,
    capture_pair: Path,
    output_dir: Path,
    candidate: dict[str, Any],
    provisional_adjustment: dict[str, Any],
) -> dict[str, Any]:
    mask_path = package_dir / str(candidate["screenMask"])
    if not mask_path.exists():
        raise FileNotFoundError(mask_path)

    projection_dir = output_dir / "projections" / str(candidate["candidateId"])
    command = [
        sys.executable,
        str(PROJECTION_SCRIPT),
        str(package_dir / "fusionSummary.json"),
        "--capture-pair",
        str(capture_pair),
        "--mask",
        str(mask_path),
        "--output-dir",
        str(projection_dir),
        "--mask-source",
        "face_parsing_silver",
        "--accepted-signal-id",
        f"validation_only_{candidate['candidateId']}",
        "--candidate-id",
        str(candidate["candidateId"]),
        "--threshold",
        str(candidate["threshold"]),
        "--inner-mouth-status",
        "missing",
        "--corner-falloff-status",
        "contract_only",
        "--upper-lower-status",
        "available",
        "--rejected-signal-reason",
        "validation_only_runtime_sweep_asset_not_m1_ready",
    ]
    completed = subprocess.run(command, cwd=repo_root, check=True, text=True, capture_output=True)
    (projection_dir / "projection_command_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (projection_dir / "projection_command_stderr.txt").write_text(completed.stderr, encoding="utf-8")

    probability = projection_dir / "lip_probability.png"
    unity_asset = UNITY_MASK_DIR / f"{candidate['unityMaskTextureId']}.png"
    install_probability_png(probability, repo_root / unity_asset)
    summary_path = projection_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    selected_adjustment = provisional_adjustment.get("selectedParams", {})
    user_adjustment_params = (
        selected_adjustment
        if candidate["usesUserAdjustment"] and selected_adjustment
        else DEFAULT_ADJUSTMENT_PARAMS
    )
    return {
        **candidate,
        "userAdjustmentParams": user_adjustment_params,
        "userAdjustmentStatus": (
            "auto_provisional_not_user_confirmed"
            if candidate["usesUserAdjustment"] and selected_adjustment
            else "not_used"
        ),
        "userAdjustmentAppliedToMask": bool(
            provisional_adjustment.get("appliedToPackage", False)
            and candidate["usesUserAdjustment"]
        ),
        "userAdjustmentRuntimeShaderProbe": True,
        "userAdjustmentSelectedCandidateId": (
            provisional_adjustment.get("selectedCandidateId")
            if candidate["usesUserAdjustment"] and selected_adjustment
            else None
        ),
        "projectionDir": str(projection_dir),
        "unityResourcePath": f"SmoothRegionMasks/{candidate['unityMaskTextureId']}",
        "unityAssetPath": str(unity_asset),
        "unityAssetSha256": sha256_file(repo_root / unity_asset),
        "roundTripScore": summary.get("roundTripScore", {}),
        "phase3ExecutionStatus": summary.get("phase3ExecutionStatus"),
        "runtimeReady": False,
        "runtimeReadyReason": "validation_only_m1_m2_partial",
    }


def build_input_readiness(
    repo_root: Path,
    package_dir: Path,
    capture_pair: Path,
    provisional_adjustment: dict[str, Any],
) -> dict[str, Any]:
    required_package_files = [
        "fusionSummary.json",
        "lip-tight-auto-v0_mask.png",
        "lip-tight-user-v0_mask.png",
        "lip-safe-v0_mask.png",
    ]
    required_capture_files = ["frame.png", "arface_export.json"]
    package_checks = {
        name: (package_dir / name).exists()
        for name in required_package_files
    }
    capture_checks = {
        name: (capture_pair / name).exists()
        for name in required_capture_files
    }

    return {
        "schemaVersion": "e7-lip-runtime-sweep-input-readiness-v0",
        "sourcePackage": rel(package_dir, repo_root),
        "capturePair": rel(capture_pair, repo_root),
        "packageChecks": package_checks,
        "captureChecks": capture_checks,
        "provisionalAdjustmentAvailable": bool(provisional_adjustment),
        "provisionalAdjustmentConfirmedByUser": bool(
            provisional_adjustment.get("userConfirmed", False)
        ),
        "m1Ready": False,
        "m2Ready": False,
        "runtimeReady": False,
        "readinessState": (
            "source_staged_buildless_unproven"
            if all(package_checks.values()) and all(capture_checks.values())
            else "partial_missing_inputs"
        ),
        "buildGateRequiredFor": [
            "UnityFramework build/sync",
            "RN iPhone build/install",
            "ARFace runtime sampling",
            "visual evidence",
            "Lip G/Y/R decision",
        ],
    }


def build_adjustment_contract(provisional_adjustment: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-lip-runtime-sweep-adjustment-controls-v0",
        "fields": {
            "cornerReach": {
                "range": [-1.0, 1.0],
                "default": 0.0,
                "positive": "expand toward lip corners",
                "negative": "shrink corner spill",
            },
            "upperLipTightness": {
                "range": [-1.0, 1.0],
                "default": 0.0,
                "positive": "tighten upper lip boundary",
                "negative": "add upper-lip coverage",
            },
            "lowerLipTightness": {
                "range": [-1.0, 1.0],
                "default": 0.0,
                "positive": "tighten lower lip boundary",
                "negative": "add lower-lip coverage",
            },
            "verticalOffset": {
                "range": [-1.0, 1.0],
                "default": 0.0,
                "positive": "move image-space mask down",
                "negative": "move image-space mask up",
            },
        },
        "runtimeBehavior": (
            "RN/Unity carry these fields for sweep logging and the Unity shader applies "
            "a lightweight validation-only sampling/threshold probe; current source-staged "
            "Unity mask textures are not regenerated live by the app."
        ),
        "userAdjustmentRuntimeShaderProbe": True,
        "currentProvisionalSelection": provisional_adjustment.get("selectedCandidateId"),
        "currentProvisionalParams": provisional_adjustment.get(
            "selectedParams",
            DEFAULT_ADJUSTMENT_PARAMS,
        ),
        "confirmedByUser": bool(provisional_adjustment.get("userConfirmed", False)),
        "allowedClaim": "auto_provisional_not_user_confirmed",
        "forbiddenClaims": [
            "user_confirmed",
            "M1 ready",
            "runtime ready",
            "Lip G/Y/R",
            "E7.3 Green",
        ],
    }


def build_sweep_evidence_schema(installed: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "e7-lip-runtime-sweep-evidence-schema-v0",
        "candidateIds": [candidate["candidateId"] for candidate in installed],
        "requiredRuntimeEvents": [
            "rn_texture_recipe_batch_post",
            "recipe_applied",
            "recipe_latency",
            "region_mask_state",
            "region_mask_apply",
            "e7_metric_sample",
        ],
        "requiredFields": [
            "candidateId",
            "maskTextureId",
            "maskThreshold",
            "maskFeatherUvNormalized",
            "cornerReach",
            "upperLipTightness",
            "lowerLipTightness",
            "verticalOffset",
            "trackingState",
            "stateAction",
            "averageFps",
            "averageFrameTimeMs",
            "recipeLatencyMs",
            "meshVertexCount",
            "meshIndexCount",
            "meshUvCount",
        ],
        "requiredRegistryFields": [
            "candidateId",
            "maskTextureId",
            "userAdjustmentRuntimeShaderProbe",
            "userAdjustmentAppliedToMask",
            "runtimeReady",
        ],
        "requiredVisualEvidence": [
            "Compact HUD screenshot for each candidate",
            "At least one screenshot after non-zero adjustment probe",
            "Full console log captured with candidate switch sequence",
        ],
        "decisionOutputs": [
            "runtime_sweep_log_summary.md",
            "runtime_sweep_contact_sheet.png",
            "lip_gyr_decision.md",
        ],
        "nonGoals": [
            "Do not claim M1 ready.",
            "Do not claim runtimeReady from buildless artifacts.",
            "Do not decide Lip G/Y/R without real-device evidence.",
        ],
    }


def write_runtime_sweep_checklist(output_dir: Path, installed: list[dict[str, Any]]) -> None:
    candidate_lines = "\n".join(
        f"- `{candidate['candidateId']}` -> `{candidate['unityMaskTextureId']}` "
        f"threshold `{candidate['threshold']}` / runtimeReady `{candidate['runtimeReady']}`"
        for candidate in installed
    )
    write_text(
        output_dir / "runtime_sweep_checklist.md",
        f"""# E7 Lip Runtime Sweep Checklist

Status: build-gated / source-staged / runtime untested

## Candidates

{candidate_lines}

## Before Build

- Confirm iPhone is connected and trusted.
- Confirm Unity/Xcode platform is installed.
- Do not change M1/M2 readiness claims.
- Keep raw camera frames local-only and do not upload.

## Build Commands

```sh
TIMESTAMP=e7-lip-runtime-sweep-YYYYMMDD-HHMMSS BUILD_LOG_MODE=full bash scripts/build_m3_unityframework.sh
cd rn/MakeupARValidation
npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK
```

If RN CLI selects a simulator UDID, use the already established direct Xcode real-device destination path and record that fallback in the evidence log.

## Runtime Sweep

- Start in Compact HUD.
- Capture full console output.
- Verify default `base` candidate first.
- Switch to `auto`, `user`, and `safe`.
- For `user`, probe at least one non-zero adjustment field and return it to `0` after evidence capture.
- Record candidate ID, mask texture ID, threshold, feather, four adjustment fields, FPS, frame time, recipe latency, tracking state, and mesh/UV counts.

## Log Analysis

After the run, analyze the captured full console log:

```sh
python3 scripts/e7_lip_runtime_sweep/analyze_runtime_sweep_log.py evidence/logs/FULL_RUNTIME_LOG.log --registry {output_dir / 'runtime_candidate_registry.json'} --output-dir {output_dir}
```

The analysis result may support a `wiring_ready` claim only. It must not be used as Lip G/Y/R or E7.3 Green by itself.

## Decision Boundary

- This run may decide whether runtime wiring works.
- This run may collect early visual observations.
- This run must not mark M1 ready, M2 ready, full E7.3 Green, or Lip G/Y/R unless the required visual/runtime evidence is actually present.
""",
    )


def write_prior_evidence_summary(output_dir: Path) -> None:
    write_text(
        output_dir / "prior_evidence_summary.md",
        """# Prior Evidence Summary

- Historical smooth-mask runtime evidence showed face-attached but broad/subtle makeup.
- M1 remains partial because user-confirmed adjustment, additional captures, blendshape/face-state, coordinate/visibility audit, held-out eval, and split/exclusion/falloff acceptance are missing.
- Current registry is only a buildless source-stage for the next real-device runtime sweep.
- Use historical evidence only as context; do not reuse it as the new M3B runtime decision evidence.
""",
    )


def write_static_verification(output_dir: Path) -> None:
    write_text(
        output_dir / "static_verification.md",
        """# Static Verification

Generated by `prepare_validation_runtime_candidates.py`.

Required commands for this source-stage:

- `python3 -m py_compile scripts/e7_lip_runtime_sweep/prepare_validation_runtime_candidates.py`
- `python3 -m py_compile scripts/e7_lip_runtime_sweep/analyze_runtime_sweep_log.py`
- `npm test -- --runInBand --watchman=false`
- `./node_modules/.bin/tsc --noEmit`
- `npm run lint`
- `git diff --check`
- Unity batchmode import/compile when Unity scripts or Resources changed

Record exact command outputs in `TECH_VALIDATION_RESULT.md` or the session summary after running them.
""",
    )


def write_summary(output_dir: Path, registry: dict[str, Any]) -> None:
    write_text(
        output_dir / "summary.md",
        f"""# E7 Lip Runtime Candidate Source-Stage Summary

Run ID: `{registry['runId']}`

Status: `source_staged_buildless_unproven`

Candidates:

{chr(10).join(f"- `{candidate['candidateId']}`: runtimeReady `{candidate['runtimeReady']}`, adjustment `{candidate['userAdjustmentStatus']}`" for candidate in registry['candidates'])}

This folder prepares M3B runtime sweep inputs only. It does not prove runtime behavior, visual quality, M1 readiness, E7.3 Green, or Lip G/Y/R.
""",
    )


def write_contract_artifacts(
    repo_root: Path,
    output_dir: Path,
    package_dir: Path,
    capture_pair: Path,
    provisional_adjustment: dict[str, Any],
    installed: list[dict[str, Any]],
    registry: dict[str, Any],
) -> None:
    write_json(
        output_dir / "input_readiness.json",
        build_input_readiness(repo_root, package_dir, capture_pair, provisional_adjustment),
    )
    write_json(
        output_dir / "adjustment_controls_contract.json",
        build_adjustment_contract(provisional_adjustment),
    )
    write_json(
        output_dir / "sweep_evidence_schema.json",
        build_sweep_evidence_schema(installed),
    )
    write_runtime_sweep_checklist(output_dir, installed)
    write_prior_evidence_summary(output_dir)
    write_static_verification(output_dir)
    write_summary(output_dir, registry)


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    package_dir = (repo_root / args.package_dir).resolve()
    capture_pair = (repo_root / args.capture_pair).resolve()
    run_id = args.run_id or f"validation-candidates-{utc_stamp()}"
    output_dir = repo_root / args.output_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    provisional_adjustment = read_json_if_exists(
        package_dir / "auto_provisional_adjustment_addendum.json"
    )

    installed = [
        run_projection(
            repo_root,
            package_dir,
            capture_pair,
            output_dir,
            candidate,
            provisional_adjustment,
        )
        for candidate in CANDIDATES
    ]
    registry = {
        "schemaVersion": "e7-lip-validation-runtime-candidate-registry-v0",
        "createdAtUtc": utc_now(),
        "runId": run_id,
        "sourcePackage": str(args.package_dir),
        "capturePair": str(args.capture_pair),
        "registryStatus": "validation_only_installed_buildless",
        "m1Ready": False,
        "m2Ready": False,
        "userAdjustmentContractFields": list(DEFAULT_ADJUSTMENT_PARAMS.keys()),
        "userAdjustmentSource": str(package_dir / "auto_provisional_adjustment_addendum.json")
        if provisional_adjustment
        else "missing",
        "userAdjustmentRuntimeShaderProbe": True,
        "runtimeSweepReadyAfterBuild": True,
        "doesNotClaimM1Ready": True,
        "doesNotClaimE73Green": True,
        "candidates": installed,
    }
    write_json(output_dir / "runtime_candidate_registry.json", registry)
    write_contract_artifacts(
        repo_root,
        output_dir,
        package_dir,
        capture_pair,
        provisional_adjustment,
        installed,
        registry,
    )
    unity_registry = repo_root / UNITY_MASK_DIR / "e7-lip-validation-runtime-candidates.json"
    write_json(unity_registry, registry)
    write_unity_text_meta(unity_registry)
    print(output_dir / "runtime_candidate_registry.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
