#!/usr/bin/env python3
"""Run MediaPipe FaceLandmarker and save full-face landmarks for E7 regions."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

MEDIAPIPE_FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
    400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21,
    54, 103, 67, 109,
]
MEDIAPIPE_LEFT_EYE = [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466]
MEDIAPIPE_RIGHT_EYE = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
MEDIAPIPE_LEFT_BROW = [276, 283, 282, 295, 285, 336, 296, 334, 293, 300]
MEDIAPIPE_RIGHT_BROW = [46, 53, 52, 65, 55, 107, 66, 105, 63, 70]
MEDIAPIPE_OUTER_LIP = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146]
MEDIAPIPE_INNER_LIP = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MediaPipe full-face landmark extraction.")
    parser.add_argument("--frame", type=Path, required=True)
    parser.add_argument("--mediapipe-model", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--capture-pair-id", default=None)
    parser.add_argument("--image-source", choices=("create_from_file", "numpy_rgb"), default="numpy_rgb")
    parser.add_argument("--delegate", choices=("cpu", "default"), default="cpu")
    parser.add_argument("--threshold", type=float, default=0.3)
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def to_image_points(landmarks: list[Any], indices: list[int], width: int, height: int) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    for index in indices:
        if index < len(landmarks):
            landmark = landmarks[index]
            points.append(
                {
                    "index": index,
                    "x": float(landmark.x) * width,
                    "y": float(landmark.y) * height,
                    "z": float(landmark.z),
                }
            )
    return points


def region_payload(landmarks: list[Any], indices: list[int], width: int, height: int) -> dict[str, Any]:
    image_points = to_image_points(landmarks, indices, width, height)
    return {
        "status": "available" if image_points else "unavailable",
        "indices": indices,
        "pointCount": len(image_points),
        "imagePoints": image_points,
    }


def make_mediapipe_image(mp: Any, frame_path: Path, frame: Image.Image, image_source: str) -> Any:
    if image_source == "create_from_file":
        return mp.Image.create_from_file(str(frame_path))
    data = np.ascontiguousarray(np.asarray(frame.convert("RGB")))
    return mp.Image(image_format=mp.ImageFormat.SRGB, data=data)


def main() -> int:
    args = parse_args()
    frame = Image.open(args.frame).convert("RGB")
    width, height = frame.size

    try:
        import mediapipe as mp  # type: ignore[import-not-found]
        from mediapipe.tasks import python as mp_python  # type: ignore[import-not-found]
        from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-not-found]
    except Exception as exception:
        write_json(
            args.output_json,
            {
                "schemaVersion": "e7-mediapipe-full-face-landmarks-v0",
                "createdAt": utc_now(),
                "status": "blocked",
                "provider": "mediapipe",
                "reason": "mediapipe_import_failed",
                "exception": exception.__class__.__name__,
                "message": str(exception),
            },
        )
        return 2

    base_kwargs: dict[str, Any] = {"model_asset_path": str(args.mediapipe_model)}
    if args.delegate == "cpu":
        base_kwargs["delegate"] = mp_python.BaseOptions.Delegate.CPU

    options = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(**base_kwargs),
        running_mode=mp_vision.RunningMode.IMAGE,
        num_faces=1,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        min_face_detection_confidence=args.threshold,
        min_face_presence_confidence=args.threshold,
        min_tracking_confidence=args.threshold,
    )

    landmarker = mp_vision.FaceLandmarker.create_from_options(options)
    try:
        result = landmarker.detect(make_mediapipe_image(mp, args.frame, frame, args.image_source))
    finally:
        landmarker.close()

    if not result.face_landmarks:
        write_json(
            args.output_json,
            {
                "schemaVersion": "e7-mediapipe-full-face-landmarks-v0",
                "createdAt": utc_now(),
                "status": "blocked",
                "provider": "mediapipe",
                "reason": "no_face_detected",
                "faceCount": 0,
                "framePath": str(args.frame),
                "frameWidth": width,
                "frameHeight": height,
            },
        )
        return 3

    landmarks = result.face_landmarks[0]
    landmark_points = [
        {
            "index": index,
            "x": float(landmark.x) * width,
            "y": float(landmark.y) * height,
            "z": float(landmark.z),
        }
        for index, landmark in enumerate(landmarks)
    ]
    payload = {
        "schemaVersion": "e7-mediapipe-full-face-landmarks-v0",
        "createdAt": utc_now(),
        "status": "available",
        "provider": "mediapipe",
        "capturePairId": args.capture_pair_id,
        "framePath": str(args.frame),
        "frameWidth": width,
        "frameHeight": height,
        "coordinateSpaces": {
            "landmarks": "frame_image_pixel_top_left",
            "imagePoints": "frame_image_pixel_top_left",
        },
        "faceCount": len(result.face_landmarks),
        "landmarkCount": len(landmark_points),
        "landmarks": landmark_points,
        "namedRegions": {
            "faceOval": region_payload(landmarks, MEDIAPIPE_FACE_OVAL, width, height),
            "leftEye": region_payload(landmarks, MEDIAPIPE_LEFT_EYE, width, height),
            "rightEye": region_payload(landmarks, MEDIAPIPE_RIGHT_EYE, width, height),
            "leftEyebrow": region_payload(landmarks, MEDIAPIPE_LEFT_BROW, width, height),
            "rightEyebrow": region_payload(landmarks, MEDIAPIPE_RIGHT_BROW, width, height),
            "outerLips": region_payload(landmarks, MEDIAPIPE_OUTER_LIP, width, height),
            "innerLips": region_payload(landmarks, MEDIAPIPE_INNER_LIP, width, height),
        },
        "privacy": {
            "localOnly": True,
            "offDeviceUpload": False,
            "rawFrameStoredByThisTool": False,
        },
        "warnings": [
            "local_mediapipe_full_face_landmarks",
            "buildless_sample_artifact_not_product_quality_proof",
        ],
    }
    write_json(args.output_json, payload)
    print(args.output_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
