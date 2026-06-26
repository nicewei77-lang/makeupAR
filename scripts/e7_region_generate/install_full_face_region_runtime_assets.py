#!/usr/bin/env python3
"""Install selected E7 full-face region UV masks into Unity Resources.

This is a pre-Xcode handoff step. It copies the selected local buildless UV
probability textures for lip/blush/brow/eyeliner into
Assets/Resources/SmoothRegionMasks so RN/Unity can reference stable
maskTextureId values before a later approved iPhone build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


DEFAULT_COMPOSITE = Path(
    "evidence/e7-region-generate/session-20260626T195853Z/composite_apply_payload.json"
)
DEFAULT_RESOURCE_DIR = Path(
    "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks"
)
REGIONS = ("lip", "blush", "brow", "eyeliner")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install E7 full-face selected region UV assets for Unity."
    )
    parser.add_argument("--composite", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--resource-dir", type=Path, default=DEFAULT_RESOURCE_DIR)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def meta_from_template(template_path: Path) -> str:
    guid = uuid.uuid4().hex
    if template_path.exists():
        lines = template_path.read_text(encoding="utf-8").splitlines()
        return "\n".join(
            f"guid: {guid}" if line.startswith("guid: ") else line.rstrip()
            for line in lines
        ) + "\n"
    return f"fileFormatVersion: 2\nguid: {guid}\n"


def install_probability_png(source: Path, target: Path) -> dict[str, Any]:
    if not source.exists():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("L")
    if image.size != (512, 512):
        image = image.resize((512, 512), Image.Resampling.BILINEAR)
    arr = np.asarray(image, dtype=np.uint8)
    rgba = np.dstack([arr, arr, arr, np.full_like(arr, 255)])
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(target)
    return {
        "target": str(target),
        "targetSha256": sha256_file(target),
        "width": 512,
        "height": 512,
        "encoding": "rgba_from_luminance_probability",
    }


def runtime_layer_for(region: str, package: dict[str, Any]) -> dict[str, Any]:
    payload = package["runtimeApplyPayload"]
    if region == "lip":
        texture = "matte_lip"
        color = "#C76B74"
        opacity = 0.62
        blend_mode = "multiply"
        coverage = 1.0
    elif region == "blush":
        texture = "soft_blush"
        color = "#E67B5F"
        opacity = 0.45
        blend_mode = "normal"
        coverage = 0.68
    elif region == "brow":
        texture = "shimmer_eye"
        color = "#5F4A42"
        opacity = 0.48
        blend_mode = "multiply"
        coverage = 0.72
    else:
        texture = "shimmer_eye"
        color = "#2F2730"
        opacity = 0.66
        blend_mode = "multiply"
        coverage = 0.72
    return {
        "id": f"{region}-{package['selectedPolicy']}",
        "region": region,
        "layer": region,
        "enabled": True,
        "color": color,
        "opacity": opacity,
        "texture": texture,
        "sample": texture,
        "textureMode": "sample",
        "intensity": payload.get("opacity", opacity),
        "feather": payload.get("feather", 0.07),
        "blendMode": blend_mode,
        "coverage": package["adjustment"].get("coverage", coverage),
        "finish": "validation-placeholder",
        "textureAmount": 0.0,
        "roughness": 0.0,
        "specular": 0.0,
        "specularPower": 0.0,
        "glossBoost": 0.0,
        "shimmer": 0.0,
        "shimmerColor": "#FFFFFF",
        "skinAdaptive": region == "lip",
        "preserveDetail": True,
        "materialId": f"e7-full-face-{region}-material-v0",
        "shaderMode": "smooth-lip-finish-v0",
        "passCount": 1,
        "candidateId": package["sourceLineage"]["candidateIds"][0],
        "maskTextureId": payload["maskTextureId"],
        "maskThreshold": payload["threshold"],
        "maskFeatherUvNormalized": payload.get("feather", 0.07),
        "cornerReach": package["adjustment"].get("cornerReach", 0.0),
        "upperLipTightness": package["adjustment"].get("upperLipTightness", 0.0),
        "lowerLipTightness": package["adjustment"].get("lowerLipTightness", 0.0),
        "verticalOffset": package["adjustment"].get("verticalOffset", 0.0),
        "cameraBackdropAvailable": False,
        "lightEstimateAvailable": False,
    }


def main() -> int:
    args = parse_args()
    composite = load_json(args.composite)
    args.resource_dir.mkdir(parents=True, exist_ok=True)
    template_meta = args.resource_dir / "lip-smooth-mask-v1.png.meta"

    installed: dict[str, Any] = {}
    layers = []
    for region in REGIONS:
        package = composite["packages"][region]
        texture_id = package["runtimeApplyPayload"]["maskTextureId"]
        source = Path(package["uvMask"]["texturePath"])
        target = args.resource_dir / f"{texture_id}.png"
        install = install_probability_png(source, target)
        meta_path = Path(str(target) + ".meta")
        if not meta_path.exists():
            meta_path.write_text(meta_from_template(template_meta), encoding="utf-8")
        install.update(
            {
                "region": region,
                "selectedPolicy": package["selectedPolicy"],
                "candidateId": package["sourceLineage"]["candidateIds"][0],
                "maskTextureId": texture_id,
                "source": str(source),
                "targetMeta": str(meta_path),
                "runtimeReady": False,
            }
        )
        installed[region] = install
        layers.append(runtime_layer_for(region, package))

    registry = {
        "schemaVersion": "e7-full-face-region-runtime-assets-v0",
        "createdAtUtc": utc_now(),
        "sourceComposite": str(args.composite),
        "sessionId": composite.get("sessionId"),
        "status": "pre-xcode-ready",
        "runtimeReady": False,
        "runtimeReadyReason": "iPhone build and visual evidence are intentionally deferred",
        "regions": installed,
        "rnRecipeBatchDraft": {
            "version": 2,
            "recipeBatchId": f"{composite.get('sessionId')}-full-face-region-pre-xcode",
            "recipeId": f"{composite.get('sessionId')}-full-face-region-pre-xcode",
            "lookId": "e7_full_face_region_generate_v0",
            "rendererMode": "smooth-region-mask",
            "activeRegions": "lip,blush,brow,eyeliner",
            "region": "lip",
            "layerCount": len(layers),
            "enabledLayerCount": len(layers),
            "texture": "matte_lip",
            "sample": "matte_lip",
            "textureMode": "sample",
            "coverage": 0.72,
            "finish": "validation-placeholder",
            "textureAmount": 0.0,
            "roughness": 0.0,
            "specular": 0.0,
            "specularPower": 0.0,
            "glossBoost": 0.0,
            "shimmer": 0.0,
            "shimmerColor": "#FFFFFF",
            "skinAdaptive": True,
            "preserveDetail": True,
            "materialId": "e7-full-face-region-batch-material-v0",
            "shaderMode": "smooth-lip-finish-v0",
            "passCount": 1,
            "cameraBackdropAvailable": False,
            "lightEstimateAvailable": False,
            "layers": layers,
        },
    }
    registry_path = args.resource_dir / "e7-full-face-region-runtime-assets.json"
    write_json(registry_path, registry)
    meta_path = Path(str(registry_path) + ".meta")
    if not meta_path.exists():
        meta_path.write_text(meta_from_template(args.resource_dir / "e7-lip-validation-runtime-candidates.json.meta"), encoding="utf-8")

    print(json.dumps({"registry": str(registry_path), "regions": list(installed)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
