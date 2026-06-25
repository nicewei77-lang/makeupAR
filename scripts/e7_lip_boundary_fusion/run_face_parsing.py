#!/usr/bin/env python3
"""Run local/offline face parsing for E7 M1 lip calibration.

This runner is intentionally buildless and local-only. It consumes a still
frame, optionally crops around the synchronized ARFace projection, runs a
pretrained BiSeNet face parsing checkpoint, and writes only derived masks and
metadata that the M1 package builder can consume.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image, ImageChops, ImageDraw, ImageFilter


SCRIPT_VERSION = "e7-face-parsing-runner-v0"
INPUT_SIZE = 512
LABELS = {
    0: "background",
    1: "skin",
    2: "left_brow",
    3: "right_brow",
    4: "left_eye",
    5: "right_eye",
    6: "eyeglass",
    7: "left_ear",
    8: "right_ear",
    9: "earring",
    10: "nose",
    11: "inner_mouth",
    12: "upper_lip",
    13: "lower_lip",
    14: "neck",
    15: "necklace",
    16: "cloth",
    17: "hair",
    18: "hat",
}
REQUIRED_LABELS = {
    "upper_lip": 12,
    "lower_lip": 13,
    "inner_mouth": 11,
    "skin": 1,
}


class ConvBNReLU(nn.Module):
    def __init__(self, in_chan: int, out_chan: int, ks: int = 3, stride: int = 1, padding: int = 1):
        super().__init__()
        self.conv = nn.Conv2d(in_chan, out_chan, kernel_size=ks, stride=stride, padding=padding, bias=False)
        self.bn = nn.BatchNorm2d(out_chan)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.relu(self.bn(self.conv(x)))


class BiSeNetOutput(nn.Module):
    def __init__(self, in_chan: int, mid_chan: int, n_classes: int):
        super().__init__()
        self.conv = ConvBNReLU(in_chan, mid_chan, ks=3, stride=1, padding=1)
        self.conv_out = nn.Conv2d(mid_chan, n_classes, kernel_size=1, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv_out(self.conv(x))


def conv3x3(in_planes: int, out_planes: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride, padding=1, bias=False)


class BasicBlock(nn.Module):
    def __init__(self, in_chan: int, out_chan: int, stride: int = 1):
        super().__init__()
        self.conv1 = conv3x3(in_chan, out_chan, stride)
        self.bn1 = nn.BatchNorm2d(out_chan)
        self.conv2 = conv3x3(out_chan, out_chan)
        self.bn2 = nn.BatchNorm2d(out_chan)
        self.relu = nn.ReLU(inplace=True)
        self.downsample = None
        if in_chan != out_chan or stride != 1:
            self.downsample = nn.Sequential(
                nn.Conv2d(in_chan, out_chan, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_chan),
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.conv1(x)
        residual = F.relu(self.bn1(residual))
        residual = self.conv2(residual)
        residual = self.bn2(residual)
        shortcut = x if self.downsample is None else self.downsample(x)
        return self.relu(shortcut + residual)


def create_layer_basic(in_chan: int, out_chan: int, bnum: int, stride: int = 1) -> nn.Sequential:
    layers: list[nn.Module] = [BasicBlock(in_chan, out_chan, stride=stride)]
    for _ in range(bnum - 1):
        layers.append(BasicBlock(out_chan, out_chan, stride=1))
    return nn.Sequential(*layers)


class Resnet18(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = nn.BatchNorm2d(64)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = create_layer_basic(64, 64, bnum=2, stride=1)
        self.layer2 = create_layer_basic(64, 128, bnum=2, stride=2)
        self.layer3 = create_layer_basic(128, 256, bnum=2, stride=2)
        self.layer4 = create_layer_basic(256, 512, bnum=2, stride=2)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = self.conv1(x)
        x = F.relu(self.bn1(x))
        x = self.maxpool(x)
        x = self.layer1(x)
        feat8 = self.layer2(x)
        feat16 = self.layer3(feat8)
        feat32 = self.layer4(feat16)
        return feat8, feat16, feat32


class AttentionRefinementModule(nn.Module):
    def __init__(self, in_chan: int, out_chan: int):
        super().__init__()
        self.conv = ConvBNReLU(in_chan, out_chan, ks=3, stride=1, padding=1)
        self.conv_atten = nn.Conv2d(out_chan, out_chan, kernel_size=1, bias=False)
        self.bn_atten = nn.BatchNorm2d(out_chan)
        self.sigmoid_atten = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.conv(x)
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.conv_atten(atten)
        atten = self.bn_atten(atten)
        atten = self.sigmoid_atten(atten)
        return torch.mul(feat, atten)


class ContextPath(nn.Module):
    def __init__(self):
        super().__init__()
        self.resnet = Resnet18()
        self.arm16 = AttentionRefinementModule(256, 128)
        self.arm32 = AttentionRefinementModule(512, 128)
        self.conv_head32 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
        self.conv_head16 = ConvBNReLU(128, 128, ks=3, stride=1, padding=1)
        self.conv_avg = ConvBNReLU(512, 128, ks=1, stride=1, padding=0)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        _, _, feat32_size = None, None, None
        feat8, feat16, feat32 = self.resnet(x)
        h16, w16 = feat16.size()[2:]
        h32, w32 = feat32.size()[2:]
        avg = F.avg_pool2d(feat32, feat32.size()[2:])
        avg = self.conv_avg(avg)
        avg_up = F.interpolate(avg, (h32, w32), mode="nearest")
        feat32_arm = self.arm32(feat32)
        feat32_sum = feat32_arm + avg_up
        feat32_up = F.interpolate(feat32_sum, (h16, w16), mode="nearest")
        feat32_up = self.conv_head32(feat32_up)
        feat16_arm = self.arm16(feat16)
        feat16_sum = feat16_arm + feat32_up
        h8, w8 = feat8.size()[2:]
        feat16_up = F.interpolate(feat16_sum, (h8, w8), mode="nearest")
        feat16_up = self.conv_head16(feat16_up)
        return feat8, feat16_up, feat32_up


class FeatureFusionModule(nn.Module):
    def __init__(self, in_chan: int, out_chan: int):
        super().__init__()
        self.convblk = ConvBNReLU(in_chan, out_chan, ks=1, stride=1, padding=0)
        self.conv1 = nn.Conv2d(out_chan, out_chan // 4, kernel_size=1, stride=1, padding=0, bias=False)
        self.conv2 = nn.Conv2d(out_chan // 4, out_chan, kernel_size=1, stride=1, padding=0, bias=False)
        self.relu = nn.ReLU(inplace=True)
        self.sigmoid = nn.Sigmoid()

    def forward(self, fsp: torch.Tensor, fcp: torch.Tensor) -> torch.Tensor:
        feat = self.convblk(torch.cat([fsp, fcp], dim=1))
        atten = F.avg_pool2d(feat, feat.size()[2:])
        atten = self.conv1(atten)
        atten = self.relu(atten)
        atten = self.conv2(atten)
        atten = self.sigmoid(atten)
        return torch.mul(feat, atten) + feat


class BiSeNet(nn.Module):
    def __init__(self, n_classes: int):
        super().__init__()
        self.cp = ContextPath()
        self.ffm = FeatureFusionModule(256, 256)
        self.conv_out = BiSeNetOutput(256, 256, n_classes)
        self.conv_out16 = BiSeNetOutput(128, 64, n_classes)
        self.conv_out32 = BiSeNetOutput(128, 64, n_classes)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        height, width = x.size()[2:]
        feat_res8, feat_cp8, feat_cp16 = self.cp(x)
        feat_fuse = self.ffm(feat_res8, feat_cp8)
        feat_out = self.conv_out(feat_fuse)
        feat_out16 = self.conv_out16(feat_cp8)
        feat_out32 = self.conv_out32(feat_cp16)
        feat_out = F.interpolate(feat_out, (height, width), mode="bilinear", align_corners=True)
        feat_out16 = F.interpolate(feat_out16, (height, width), mode="bilinear", align_corners=True)
        feat_out32 = F.interpolate(feat_out32, (height, width), mode="bilinear", align_corners=True)
        return feat_out, feat_out16, feat_out32


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local/offline face parsing for one E7 capture frame.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--capture-pair-id", default=None)
    parser.add_argument("--arface-export", type=Path, default=None)
    parser.add_argument("--crop-expansion", type=float, default=0.35)
    parser.add_argument("--min-lip-pixels", type=int, default=64)
    parser.add_argument("--device", choices=("auto", "cpu", "mps"), default="auto")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def choose_device(requested: str) -> torch.device:
    if requested == "cpu":
        return torch.device("cpu")
    if requested == "mps":
        return torch.device("mps")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def crop_box_from_arface(arface_export: Path | None, frame_size: tuple[int, int], expansion: float) -> dict[str, Any]:
    width, height = frame_size
    if not arface_export or not arface_export.exists():
        return {
            "source": "full_frame_no_arface_export",
            "box": [0, 0, width, height],
            "faceVertexCount": 0,
        }
    export = load_json(arface_export)
    points = np.asarray(export.get("screenVertices", []), dtype=np.float64)
    if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 2:
        return {
            "source": "full_frame_missing_screen_vertices",
            "box": [0, 0, width, height],
            "faceVertexCount": 0,
        }
    xy = points[:, :2]
    valid = (
        np.isfinite(xy[:, 0])
        & np.isfinite(xy[:, 1])
        & (xy[:, 0] >= -width)
        & (xy[:, 0] <= width * 2)
        & (xy[:, 1] >= -height)
        & (xy[:, 1] <= height * 2)
    )
    xy = xy[valid]
    if len(xy) == 0:
        return {"source": "full_frame_no_valid_vertices", "box": [0, 0, width, height], "faceVertexCount": 0}
    min_x, min_y = xy.min(axis=0)
    max_x, max_y = xy.max(axis=0)
    face_w = max_x - min_x
    face_h = max_y - min_y
    pad = max(face_w, face_h) * expansion
    x0 = max(0, int(np.floor(min_x - pad)))
    y0 = max(0, int(np.floor(min_y - pad)))
    x1 = min(width, int(np.ceil(max_x + pad)))
    y1 = min(height, int(np.ceil(max_y + pad)))
    side = max(x1 - x0, y1 - y0)
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    x0 = max(0, int(round(cx - side / 2.0)))
    y0 = max(0, int(round(cy - side / 2.0)))
    x1 = min(width, x0 + side)
    y1 = min(height, y0 + side)
    x0 = max(0, x1 - side)
    y0 = max(0, y1 - side)
    return {
        "source": "arface_screen_vertices_square_crop",
        "box": [int(x0), int(y0), int(x1), int(y1)],
        "faceVertexCount": int(len(xy)),
        "rawBounds": {
            "minX": round(float(min_x), 3),
            "minY": round(float(min_y), 3),
            "maxX": round(float(max_x), 3),
            "maxY": round(float(max_y), 3),
        },
    }


def image_to_tensor(image: Image.Image, device: torch.device) -> torch.Tensor:
    array = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    mean = np.asarray([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.asarray([0.229, 0.224, 0.225], dtype=np.float32)
    array = (array - mean) / std
    tensor = torch.from_numpy(array.transpose(2, 0, 1)).unsqueeze(0)
    return tensor.to(device)


def load_model(checkpoint: Path, device: torch.device) -> BiSeNet:
    state = torch.load(str(checkpoint), map_location="cpu")
    if isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    cleaned = {}
    for key, value in state.items():
        cleaned[key[7:] if key.startswith("module.") else key] = value
    model = BiSeNet(n_classes=19)
    missing, unexpected = model.load_state_dict(cleaned, strict=False)
    critical_missing = [key for key in missing if not key.endswith("num_batches_tracked")]
    if critical_missing or unexpected:
        raise RuntimeError(
            "checkpoint_state_mismatch "
            + json.dumps({"missing": critical_missing[:20], "unexpected": unexpected[:20]})
        )
    model.to(device)
    model.eval()
    return model


def paste_crop_label_map(
    crop_label_map: np.ndarray,
    crop_box: list[int],
    frame_size: tuple[int, int],
) -> np.ndarray:
    x0, y0, x1, y1 = crop_box
    crop_w = max(1, x1 - x0)
    crop_h = max(1, y1 - y0)
    crop_image = Image.fromarray(crop_label_map.astype(np.uint8), mode="L").resize(
        (crop_w, crop_h), Image.Resampling.NEAREST
    )
    full = Image.new("L", frame_size, 0)
    full.paste(crop_image, (x0, y0))
    return np.asarray(full, dtype=np.uint8)


def save_mask(path: Path, mask: np.ndarray) -> int:
    binary = (mask > 0).astype(np.uint8) * 255
    Image.fromarray(binary, mode="L").save(path)
    return int(np.count_nonzero(binary))


def make_overlay(frame: Image.Image, label_map: np.ndarray, output_path: Path) -> None:
    base = np.asarray(frame.convert("RGB"), dtype=np.float32)
    colors = {
        11: np.array([40, 180, 255], dtype=np.float32),
        12: np.array([255, 42, 116], dtype=np.float32),
        13: np.array([255, 126, 36], dtype=np.float32),
    }
    lip_area = np.isin(label_map, [11, 12, 13])
    for label, color in colors.items():
        index = label_map == label
        base[index] = base[index] * 0.45 + color * 0.55
    outline_mask = Image.fromarray((lip_area.astype(np.uint8) * 255), mode="L")
    outline = ImageChops.subtract(
        outline_mask.filter(ImageFilter.MaxFilter(7)),
        outline_mask.filter(ImageFilter.MinFilter(7)),
    )
    outline_index = np.asarray(outline) > 0
    base[outline_index] = np.array([255, 230, 60], dtype=np.float32)
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).save(output_path)


def bounds_for_mask(mask: np.ndarray) -> dict[str, Any] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return {
        "minX": int(xs.min()),
        "minY": int(ys.min()),
        "maxX": int(xs.max()),
        "maxY": int(ys.max()),
        "width": int(xs.max() - xs.min() + 1),
        "height": int(ys.max() - ys.min() + 1),
    }


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = Image.open(args.image).convert("RGB")
    crop = crop_box_from_arface(args.arface_export, frame.size, args.crop_expansion)
    x0, y0, x1, y1 = crop["box"]
    crop_frame = frame.crop((x0, y0, x1, y1)).resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    device = choose_device(args.device)
    model = load_model(args.checkpoint, device)
    with torch.no_grad():
        logits = model(image_to_tensor(crop_frame, device))[0]
        probs = torch.softmax(logits, dim=1)
        confidence, parsing = torch.max(probs, dim=1)
    crop_label_map = parsing.squeeze(0).detach().cpu().numpy().astype(np.uint8)
    crop_confidence = confidence.squeeze(0).detach().cpu().numpy().astype(np.float32)
    label_map = paste_crop_label_map(crop_label_map, crop["box"], frame.size)
    confidence_map = Image.fromarray(np.uint8(np.clip(crop_confidence * 255.0, 0, 255)), mode="L").resize(
        (max(1, x1 - x0), max(1, y1 - y0)), Image.Resampling.BILINEAR
    )
    full_conf = Image.new("L", frame.size, 0)
    full_conf.paste(confidence_map, (x0, y0))
    full_conf_array = np.asarray(full_conf, dtype=np.uint8)

    Image.fromarray(label_map, mode="L").save(args.output_dir / "face_parsing_label_map.png")
    Image.fromarray(full_conf_array, mode="L").save(args.output_dir / "face_parsing_confidence_map.png")
    lip_mask = np.isin(label_map, [12, 13])
    upper_mask = label_map == 12
    lower_mask = label_map == 13
    inner_mask = label_map == 11
    skin_mask = label_map == 1
    counts = {
        "lip": save_mask(args.output_dir / "face_parsing_lip_mask.png", lip_mask),
        "upper_lip": save_mask(args.output_dir / "face_parsing_upper_lip_mask.png", upper_mask),
        "lower_lip": save_mask(args.output_dir / "face_parsing_lower_lip_mask.png", lower_mask),
        "inner_mouth": save_mask(args.output_dir / "face_parsing_inner_mouth_mask.png", inner_mask),
        "skin": save_mask(args.output_dir / "face_parsing_skin_mask.png", skin_mask),
    }
    make_overlay(frame, label_map, args.output_dir / "face_parsing_overlay.png")

    labels_found = {
        name: {
            "classId": class_id,
            "label": LABELS[class_id],
            "pixelCount": int(np.count_nonzero(label_map == class_id)),
            "bounds": bounds_for_mask(label_map == class_id),
        }
        for name, class_id in REQUIRED_LABELS.items()
    }
    lip_pixels = counts["lip"]
    required_available = (
        counts["upper_lip"] >= args.min_lip_pixels
        and counts["lower_lip"] >= args.min_lip_pixels
        and counts["inner_mouth"] >= 0
    )
    confidence_values = full_conf_array[lip_mask]
    mean_lip_conf = float(np.mean(confidence_values) / 255.0) if len(confidence_values) else 0.0
    status = "silver" if required_available and lip_pixels >= args.min_lip_pixels else "low_confidence"
    failure_reasons = []
    if counts["upper_lip"] < args.min_lip_pixels:
        failure_reasons.append("upper_lip_pixels_below_threshold")
    if counts["lower_lip"] < args.min_lip_pixels:
        failure_reasons.append("lower_lip_pixels_below_threshold")
    if lip_pixels < args.min_lip_pixels:
        failure_reasons.append("combined_lip_pixels_below_threshold")

    labels_payload = {
        "schemaVersion": "e7-face-parsing-labels-v0",
        "createdAtUtc": utc_now(),
        "scriptVersion": SCRIPT_VERSION,
        "modelFamily": "BiSeNet",
        "checkpointPath": str(args.checkpoint),
        "checkpointSha256": sha256_file(args.checkpoint),
        "sourceFramePath": str(args.image),
        "sourceFrameSha256": sha256_file(args.image),
        "capturePairId": args.capture_pair_id,
        "status": status,
        "labelSet": "CelebAMask-HQ-19",
        "labels": {str(key): value for key, value in LABELS.items()},
        "requiredLabels": labels_found,
        "crop": crop,
        "artifacts": {
            "labelMap": "face_parsing_label_map.png",
            "confidenceMap": "face_parsing_confidence_map.png",
            "lipMask": "face_parsing_lip_mask.png",
            "upperLipMask": "face_parsing_upper_lip_mask.png",
            "lowerLipMask": "face_parsing_lower_lip_mask.png",
            "innerMouthMask": "face_parsing_inner_mouth_mask.png",
            "skinMask": "face_parsing_skin_mask.png",
            "overlay": "face_parsing_overlay.png",
        },
        "localOnly": True,
        "runtimePrimaryTracker": False,
        "derivedEvidenceOnly": True,
        "doesNotClaimGold": True,
        "failureReasons": failure_reasons,
    }
    confidence_payload = {
        "schemaVersion": "e7-face-parsing-confidence-v0",
        "createdAtUtc": utc_now(),
        "status": status,
        "meanLipConfidence": round(mean_lip_conf, 4),
        "pixelCounts": counts,
        "lipCoverageRatio": round(lip_pixels / float(frame.width * frame.height), 6),
        "source": "local_offline_bisenet_face_parsing",
        "warnings": failure_reasons,
        "fusionUse": {
            "silverSignalWhenStatusSilver": True,
            "shrinkBroadMeshDraftTowardLipLabels": True,
            "innerMouthExclusionFromLabel": counts["inner_mouth"] > 0,
            "upperLowerSplitFromLabels": counts["upper_lip"] > 0 and counts["lower_lip"] > 0,
        },
    }
    write_json(args.output_dir / "face_parsing_labels.json", labels_payload)
    write_json(args.output_dir / "face_parsing_confidence.json", confidence_payload)
    print(json.dumps({"status": status, "outputDir": str(args.output_dir), "pixelCounts": counts}, indent=2))
    return 0 if status == "silver" else 4


if __name__ == "__main__":
    raise SystemExit(main())
