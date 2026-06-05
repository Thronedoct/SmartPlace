from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from server.recommender import build_mock_recommendation
except ModuleNotFoundError:
    from recommender import build_mock_recommendation

MODEL_VERSION = "mock-stdlib-v0"


def build_recommendation() -> dict:
    return build_mock_recommendation(model_version=MODEL_VERSION)


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
