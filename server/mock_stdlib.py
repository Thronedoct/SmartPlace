from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


MODEL_VERSION = "mock-stdlib-v0"


def build_recommendation() -> dict:
    started = time.perf_counter()
    runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
    return {
        "request_id": f"mock-{uuid.uuid4().hex[:12]}",
        "model_version": MODEL_VERSION,
        "coord_type": "normalized_xywh",
        "runtime_ms": runtime_ms,
        "image_width": 1,
        "image_height": 1,
        "best_index": 0,
        "candidates": [
            {
                "rank": 1,
                "x": 0.38,
                "y": 0.58,
                "w": 0.25,
                "h": 0.25,
                "score": 0.86,
                "tier": "recommended",
                "label": "推荐",
                "reason": "Mock: object is inside a stable support region.",
                "preview_url": None,
                "heatmap_url": None,
            },
            {
                "rank": 2,
                "x": 0.15,
                "y": 0.55,
                "w": 0.25,
                "h": 0.25,
                "score": 0.61,
                "tier": "acceptable",
                "label": "可接受",
                "reason": "Mock: position is plausible but less centered.",
                "preview_url": None,
                "heatmap_url": None,
            },
            {
                "rank": 3,
                "x": 0.72,
                "y": 0.12,
                "w": 0.25,
                "h": 0.25,
                "score": 0.28,
                "tier": "rejected",
                "label": "不推荐",
                "reason": "Mock: object appears unsupported or visually floating.",
                "preview_url": None,
                "heatmap_url": None,
            },
        ],
    }


class MockHandler(BaseHTTPRequestHandler):
    server_version = "SmartPlaceMock/0.1"

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self.write_json(
                {
                    "status": "ok",
                    "service": "smartplace-mock-stdlib",
                    "model_version": MODEL_VERSION,
                }
            )
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:
        if self.path != "/api/place/recommend":
            self.send_error(404, "Not found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        print(
            "mock recommendation",
            {
                "content_type": self.headers.get("Content-Type"),
                "body_bytes": len(body),
            },
        )
        self.write_json(build_recommendation())

    def write_json(self, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SmartPlace phase-0 mock API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockHandler)
    print(f"SmartPlace mock API running at http://{args.host}:{args.port}")
    print("Endpoints: GET /api/health, POST /api/place/recommend")
    server.serve_forever()


if __name__ == "__main__":
    main()
