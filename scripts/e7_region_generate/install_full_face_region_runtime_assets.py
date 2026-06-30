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
from PIL import ImageFilter
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
DEFAULT_BROW_PSD = Path("/Users/wiseungcheol/Documents/ARCore_canonical_face_texture_1.psd")
REGIONS = ("lip", "blush", "brow", "eyeliner")
BROW_MASK_TEXTURE_ID = "psd-arcore-brow-semi-arch-v1"
BROW_CLEANUP_SOURCE_ID = "brow-cleanup-source-v1"
BROW_SOURCE_LAYER_NAME = "eyebrow"
BROW_LAYER_DETECTION_METHOD = "psd_metadata_string_8bim_luni"
BROW_EXTRACTION_METHOD = (
    "pil_psd_composite_rgb_threshold_upper_brow_roi_to_512_rgba_alpha"
)
BROW_ROIS_NORMALIZED = (
    (0.22, 0.25, 0.48, 0.34),
    (0.52, 0.25, 0.78, 0.34),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install E7 full-face selected region UV assets for Unity."
    )
    parser.add_argument("--composite", type=Path, default=DEFAULT_COMPOSITE)
    parser.add_argument("--resource-dir", type=Path, default=DEFAULT_RESOURCE_DIR)
    parser.add_argument("--brow-psd", type=Path, default=DEFAULT_BROW_PSD)
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


def psd_contains_ascii_layer_name(path: Path, layer_name: str) -> bool:
    if not path.exists():
        raise FileNotFoundError(path)
    needle = layer_name.lower().encode("utf-8")
    tail = b""
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            haystack = (tail + chunk).lower()
            if needle in haystack:
                return True
            tail = haystack[-max(len(needle) - 1, 0):]
    return False


def extract_brow_alpha_from_psd(psd_path: Path) -> tuple[Image.Image, dict[str, Any]]:
    if not psd_contains_ascii_layer_name(psd_path, BROW_SOURCE_LAYER_NAME):
        raise RuntimeError(
            f"PSD brow layer '{BROW_SOURCE_LAYER_NAME}' was not found in {psd_path}."
        )

    with Image.open(psd_path) as image:
        composite = image.convert("RGB")

    width, height = composite.size
    rgb = np.asarray(composite, dtype=np.uint8)
    roi_mask = np.zeros((height, width), dtype=bool)
    roi_pixels: list[dict[str, int]] = []
    for x0n, y0n, x1n, y1n in BROW_ROIS_NORMALIZED:
        x0 = int(round(width * x0n))
        y0 = int(round(height * y0n))
        x1 = int(round(width * x1n))
        y1 = int(round(height * y1n))
        roi_mask[y0:y1, x0:x1] = True
        roi_pixels.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1})

    channel_min = rgb.min(axis=2)
    channel_max = rgb.max(axis=2)
    channel_mean = rgb.mean(axis=2)
    white_brow = (
        roi_mask
        & (channel_min >= 210)
        & (channel_mean >= 228)
        & ((channel_max - channel_min) <= 42)
    )

    alpha = np.zeros((height, width), dtype=np.uint8)
    alpha[white_brow] = 255
    alpha_image = Image.fromarray(alpha, mode="L")
    alpha_image = alpha_image.filter(ImageFilter.GaussianBlur(radius=2.0))
    alpha_512 = alpha_image.resize((512, 512), Image.Resampling.LANCZOS)
    alpha_arr = np.asarray(alpha_512, dtype=np.uint8)
    alpha_count = int(np.count_nonzero(alpha_arr))
    if alpha_count == 0:
        raise RuntimeError("PSD brow extraction produced an empty alpha mask.")

    bbox = alpha_512.getbbox()
    rgba_arr = np.zeros((512, 512, 4), dtype=np.uint8)
    rgba_arr[:, :, 0:3] = 255
    rgba_arr[:, :, 3] = alpha_arr
    rgba = Image.fromarray(rgba_arr, mode="RGBA")
    return rgba, {
        "sourceWidth": width,
        "sourceHeight": height,
        "sourceLayerName": BROW_SOURCE_LAYER_NAME,
        "sourceLayerDetectionMethod": BROW_LAYER_DETECTION_METHOD,
        "extractionMethod": BROW_EXTRACTION_METHOD,
        "roiPixels": roi_pixels,
        "alphaPixelCount512": alpha_count,
        "bbox512": list(bbox) if bbox else None,
    }


def install_psd_brow_assets(
    psd_path: Path,
    resource_dir: Path,
    template_meta: Path,
) -> dict[str, Any]:
    brow_target = resource_dir / f"{BROW_MASK_TEXTURE_ID}.png"
    cleanup_target = resource_dir / f"{BROW_CLEANUP_SOURCE_ID}.png"
    rgba, extraction = extract_brow_alpha_from_psd(psd_path)
    brow_target.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(brow_target)

    alpha = rgba.getchannel("A")
    cleanup_alpha = alpha.filter(ImageFilter.MaxFilter(size=31)).filter(
        ImageFilter.GaussianBlur(radius=8.0)
    )
    cleanup_arr = np.zeros((512, 512, 4), dtype=np.uint8)
    cleanup_arr[:, :, 0:3] = 255
    cleanup_arr[:, :, 3] = np.asarray(cleanup_alpha, dtype=np.uint8)
    Image.fromarray(cleanup_arr, mode="RGBA").save(cleanup_target)

    for target in (brow_target, cleanup_target):
        meta_path = Path(str(target) + ".meta")
        if not meta_path.exists():
            meta_path.write_text(meta_from_template(template_meta), encoding="utf-8")

    extraction.update(
        {
            "target": str(brow_target),
            "targetMeta": str(brow_target) + ".meta",
            "targetSha256": sha256_file(brow_target),
            "cleanupSourceTextureId": BROW_CLEANUP_SOURCE_ID,
            "cleanupSourceTarget": str(cleanup_target),
            "cleanupSourceTargetMeta": str(cleanup_target) + ".meta",
            "cleanupSourceSha256": sha256_file(cleanup_target),
            "width": 512,
            "height": 512,
            "encoding": "psd_arcore_canonical_eyebrow_layer_rgba_alpha",
            "source": str(psd_path),
            "sourcePsdSha256": sha256_file(psd_path),
        }
    )
    return extraction


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
        color = "#4A342B"
        opacity = 0.75
        blend_mode = "multiply"
        coverage = 0.66
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
        "maskSpreadX": package["adjustment"].get("maskSpreadX", 0.0) if region == "brow" else 0.0,
        "maskOffsetY": package["adjustment"].get("maskOffsetY", 0.0) if region == "brow" else 0.0,
        "browGap": package["adjustment"].get("browGap", 0.0) if region == "brow" else 0.0,
        "browAngle": package["adjustment"].get("browAngle", 0.0) if region == "brow" else 0.0,
        "browArch": package["adjustment"].get("browArch", 0.0) if region == "brow" else 0.0,
        "browArchPosition": package["adjustment"].get("browArchPosition", 0.0) if region == "brow" else 0.0,
        "finish": "validation-placeholder",
        "textureAmount": 0.64 if region == "brow" else 0.0,
        "roughness": 0.0,
        "specular": 0.0,
        "specularPower": 0.0,
        "glossBoost": 0.0,
        "detailAmount": 0.64 if region == "brow" else 0.0,
        "browCleanupEnabled": False,
        "browCleanupStrength": 0.0,
        "browReshapeStrength": 0.16 if region == "brow" else 0.0,
        "browCleanupSourceMode": "none",
        "shimmer": 0.0,
        "shimmerColor": "#FFFFFF",
        "skinAdaptive": region == "lip",
        "preserveDetail": True,
        "materialId": f"e7-full-face-{region}-material-v0",
        "shaderMode": "smooth-lip-finish-v0",
        "passCount": 1,
        "candidateId": "brow-psd-semi-arch-v1" if region == "brow" else package["sourceLineage"]["candidateIds"][0],
        "maskTextureId": BROW_MASK_TEXTURE_ID if region == "brow" else payload["maskTextureId"],
        "maskThreshold": 0.035 if region == "brow" else payload["threshold"],
        "maskFeatherUvNormalized": 0.42 if region == "brow" else payload.get("feather", 0.07),
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
        if region == "brow":
            texture_id = BROW_MASK_TEXTURE_ID
            brow_install = install_psd_brow_assets(
                args.brow_psd,
                args.resource_dir,
                template_meta,
            )
            installed[region] = {
                **brow_install,
                "region": region,
                "selectedPolicy": "psd-semi-arch",
                "candidateId": "brow-psd-semi-arch-v1",
                "maskTextureId": texture_id,
                "runtimeReady": False,
            }
            layers.append(runtime_layer_for(region, package))
            continue
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
