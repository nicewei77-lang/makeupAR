import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.e7_lip_boundary_fusion.prepare_m1_lip_package import (
    validate_user_adjustment_review,
)
from scripts.e7_lip_boundary_fusion.prepare_user_adjustment_candidates import (
    PARAM_KEYS,
    apply_user_adjustment,
    bbox,
    centroid_y,
    save_mask,
    write_json,
)


def rect(shape, x0, y0, x1, y1):
    mask = np.zeros(shape, dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


class UserAdjustmentCandidateTests(unittest.TestCase):
    def setUp(self):
        self.shape = (100, 100)
        self.base = rect(self.shape, 42, 44, 59, 63)
        self.upper = rect(self.shape, 30, 38, 70, 52)
        self.lower = rect(self.shape, 30, 52, 70, 72)
        self.inner = rect(self.shape, 47, 52, 54, 58)

    def test_positive_corner_reach_increases_horizontal_bbox(self):
        adjusted = apply_user_adjustment(
            self.base,
            {"cornerReach": 0.6, "upperLipTightness": 0, "lowerLipTightness": 0, "verticalOffset": 0},
            self.upper,
            self.lower,
            None,
        )
        self.assertGreater(bbox(adjusted)["width"], bbox(self.base)["width"])

    def test_positive_lower_tightness_reduces_lower_edge(self):
        adjusted = apply_user_adjustment(
            self.base,
            {"cornerReach": 0, "upperLipTightness": 0, "lowerLipTightness": 0.8, "verticalOffset": 0},
            self.upper,
            self.lower,
            None,
        )
        self.assertLess(bbox(adjusted)["maxY"], bbox(self.base)["maxY"])

    def test_positive_upper_tightness_reduces_upper_edge(self):
        adjusted = apply_user_adjustment(
            self.base,
            {"cornerReach": 0, "upperLipTightness": 0.8, "lowerLipTightness": 0, "verticalOffset": 0},
            self.upper,
            self.lower,
            None,
        )
        self.assertGreater(bbox(adjusted)["minY"], bbox(self.base)["minY"])

    def test_vertical_offset_moves_centroid_down_for_positive_value(self):
        adjusted = apply_user_adjustment(
            self.base,
            {"cornerReach": 0, "upperLipTightness": 0, "lowerLipTightness": 0, "verticalOffset": 0.8},
            self.upper,
            self.lower,
            None,
        )
        self.assertGreater(centroid_y(adjusted), centroid_y(self.base))

    def test_inner_mouth_is_always_excluded(self):
        adjusted = apply_user_adjustment(
            self.base | self.inner,
            {"cornerReach": 0.6, "upperLipTightness": 0, "lowerLipTightness": 0, "verticalOffset": 0},
            self.upper,
            self.lower,
            self.inner,
        )
        self.assertEqual(int(np.count_nonzero(adjusted & self.inner)), 0)


class UserAdjustmentReviewTests(unittest.TestCase):
    def test_legacy_only_params_do_not_confirm_user_adjustment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "pkg"
            package.mkdir()
            review = package / "user_adjustment_review.json"
            write_json(
                review,
                {
                    "schemaVersion": "e7-lip-user-adjustment-review-v0",
                    "status": "user_confirmed",
                    "confirmedByUser": True,
                    "selectedCandidateId": "ua-00-baseline",
                    "params": {
                        "tightness": 0,
                        "upperLowerBalance": 0,
                        "cornerShrink": 0,
                        "verticalOffset": 0,
                    },
                },
            )

            adjustment, selected_mask, blockers = validate_user_adjustment_review(review, root, package)

            self.assertEqual(blockers, [])
            self.assertIsNone(selected_mask)
            self.assertNotEqual(adjustment["status"], "user_confirmed")
            self.assertIn("cornerReach", adjustment["missing"])

    def test_valid_review_selects_candidate_mask(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "pkg"
            package.mkdir()
            mask_path = package / "candidate_mask.png"
            save_mask(mask_path, rect((12, 12), 3, 3, 8, 8))
            params = {
                "cornerReach": 0.25,
                "upperLipTightness": 0.2,
                "lowerLipTightness": 0.45,
                "verticalOffset": 0,
            }
            write_json(
                package / "user_adjustment_candidates.json",
                {
                    "schemaVersion": "e7-lip-user-adjustment-candidates-v0",
                    "candidates": [
                        {
                            "candidateId": "ua-11-balanced-observed",
                            "params": params,
                            "maskPath": str(mask_path),
                            "metrics": {},
                        }
                    ],
                },
            )
            review = package / "user_adjustment_review.json"
            write_json(
                review,
                {
                    "schemaVersion": "e7-lip-user-adjustment-review-v0",
                    "status": "user_confirmed",
                    "confirmedByUser": True,
                    "selectedCandidateId": "ua-11-balanced-observed",
                    "params": {key: params[key] for key in PARAM_KEYS},
                },
            )

            adjustment, selected_mask, blockers = validate_user_adjustment_review(review, root, package)

            self.assertEqual(blockers, [])
            self.assertEqual(selected_mask, mask_path)
            self.assertEqual(adjustment["status"], "user_confirmed")
            self.assertEqual(adjustment["params"], params)


if __name__ == "__main__":
    unittest.main()
