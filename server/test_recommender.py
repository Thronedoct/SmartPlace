from __future__ import annotations

import unittest

from server.recommender import build_mock_recommendation, detect_image_size


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


if __name__ == "__main__":
    unittest.main()
