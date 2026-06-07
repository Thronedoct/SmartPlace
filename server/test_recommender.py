from __future__ import annotations

import unittest

from server.demo_assets import DEMO_CASE_IDS, demo_case_available, resolve_demo_asset
from server.recommender import build_mock_recommendation, detect_image_size, select_candidates_for_scoring
from server.scorer import get_scorer_status, score_candidate_template, score_composite


class RecommenderTest(unittest.TestCase):
    def test_detects_png_size(self) -> None:
        png_header = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x02\x80"
            b"\x00\x00\x01\xe0"
        )
        self.assertEqual(detect_image_size(png_header), (640, 480))

    def test_build_recommendation_respects_count_scale_and_size(self) -> None:
        png_header = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x04\x00"
            b"\x00\x00\x03\x00"
        )

        payload = build_mock_recommendation(
            candidate_count=2,
            foreground_scale=0.22,
            background_bytes=png_header,
        )

        self.assertEqual(payload["coord_type"], "normalized_xywh")
        self.assertEqual(payload["image_width"], 1024)
        self.assertEqual(payload["image_height"], 768)
        self.assertEqual(len(payload["candidates"]), 2)
        self.assertEqual(payload["candidates"][0]["w"], 0.22)
        self.assertEqual(payload["candidates"][0]["tier"], "recommended")

    def test_build_recommendation_can_return_more_candidates(self) -> None:
        payload = build_mock_recommendation(candidate_count=8, foreground_scale=0.4)

        self.assertEqual(len(payload["candidates"]), 8)
        self.assertEqual(payload["candidates"][7]["rank"], 8)
        self.assertLessEqual(payload["candidates"][7]["w"], 0.4)

    def test_mock_scorer_boundary(self) -> None:
        candidate_score = score_candidate_template(0.86, model_version="mock-v0")
        composite_score = score_composite(b"abc", b"mask", model_version="mock-v0")

        self.assertEqual(candidate_score.mode, "mock")
        self.assertEqual(candidate_score.score, 0.86)
        self.assertEqual(composite_score.model_version, "mock-v0")
        self.assertGreaterEqual(composite_score.score, 0.0)
        self.assertLessEqual(composite_score.score, 1.0)

    def test_simopa_lite_status_and_candidate_budget(self) -> None:
        status = get_scorer_status("simopa-lite")
        worker_status = get_scorer_status("simopa-worker")
        candidates = [{"rank": rank} for rank in range(1, 13)]

        self.assertEqual(status["mode"], "simopa-lite")
        self.assertEqual(status["model_version"], "simopa-lite-candidate-budget-v1")
        self.assertEqual(worker_status["mode"], "simopa-worker")
        self.assertEqual(worker_status["model_version"], "simopa-worker-rgb-mask-v1")
        self.assertEqual(len(select_candidates_for_scoring(candidates, "simopa-lite", 3)), 6)
        self.assertEqual(len(select_candidates_for_scoring(candidates, "simopa-lite", 8)), 8)
        self.assertEqual(len(select_candidates_for_scoring(candidates, "simopa-lite-worker", 3)), 6)
        self.assertEqual(len(select_candidates_for_scoring(candidates, "simopa-worker", 3)), 12)

    def test_packaged_demo_cases_are_available_without_raw_dataset_summary(self) -> None:
        for case_id in DEMO_CASE_IDS:
            self.assertTrue(demo_case_available(case_id, {}), case_id)
            for asset_name in ("background", "foreground", "mask"):
                asset_path = resolve_demo_asset(case_id, asset_name, {})
                self.assertIsNotNone(asset_path, f"{case_id}/{asset_name}")
                self.assertTrue(asset_path.is_file(), f"{case_id}/{asset_name}")


if __name__ == "__main__":
    unittest.main()
