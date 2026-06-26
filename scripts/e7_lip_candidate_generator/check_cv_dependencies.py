#!/usr/bin/env python3
"""Smoke-check local OpenCV/scikit-image tooling without reading evidence files."""

from __future__ import annotations

import json
import platform
import sys
from importlib import metadata as importlib_metadata
from typing import Any


def package_version(distribution_name: str) -> str | None:
    try:
        return importlib_metadata.version(distribution_name)
    except importlib_metadata.PackageNotFoundError:
        return None


def main() -> int:
    report: dict[str, Any] = {
        "schemaVersion": "e7-local-cv-tooling-smoke-v0",
        "pythonExecutable": sys.executable,
        "pythonVersion": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": {},
        "operations": {},
    }

    try:
        import cv2  # type: ignore[import-not-found]
        import numpy as np
        from skimage import measure, morphology  # type: ignore[import-not-found]
    except Exception as exception:
        report["available"] = False
        report["error"] = f"{exception.__class__.__name__}: {exception}"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    report["packages"] = {
        "opencv-python-headless": {
            "distributionVersion": package_version("opencv-python-headless"),
            "moduleVersion": getattr(cv2, "__version__", None),
            "importName": "cv2",
        },
        "scikit-image": {
            "distributionVersion": package_version("scikit-image"),
            "moduleVersion": package_version("scikit-image"),
            "importName": "skimage",
        },
        "numpy": {
            "distributionVersion": package_version("numpy"),
            "moduleVersion": getattr(np, "__version__", None),
            "importName": "numpy",
        },
    }

    mask = np.zeros((80, 80), dtype=np.uint8)
    cv2.ellipse(mask, center=(40, 40), axes=(24, 10), angle=0, startAngle=0, endAngle=360, color=255, thickness=-1)
    kernel = np.ones((3, 3), dtype=np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    closed = morphology.closing(opened > 0, morphology.disk(2))
    sk_contours = measure.find_contours(closed.astype(float), 0.5)

    report["operations"] = {
        "opencvFindContours": {
            "ok": len(contours) == 1,
            "contourCount": len(contours),
            "positivePixels": int(np.count_nonzero(opened)),
        },
        "skimageMorphologyAndContours": {
            "ok": len(sk_contours) >= 1,
            "contourCount": len(sk_contours),
            "positivePixels": int(np.count_nonzero(closed)),
        },
    }
    report["available"] = all(item["ok"] for item in report["operations"].values())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
