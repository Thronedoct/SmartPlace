from __future__ import annotations

import struct
import time
import uuid


DEFAULT_MODEL_VERSION = "mock-v0"


def detect_image_size(data: bytes) -> tuple[int, int]:
    """Return image dimensions for common upload formats, or 1x1 if unknown."""
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        width, height = struct.unpack(">II", data[16:24])
        return max(1, width), max(1, height)

    if len(data) >= 10 and data[:6] in {b"GIF87a", b"GIF89a"}:
        width, height = struct.unpack("<HH", data[6:10])
        return max(1, width), max(1, height)

    jpeg_size = _detect_jpeg_size(data)
    if jpeg_size is not None:
        return jpeg_size

    return 1, 1


def build_mock_recommendation(
    *,
    candidate_count: int = 3,
    foreground_scale: float = 0.25,
    background_bytes: bytes = b"",
    model_version: str = DEFAULT_MODEL_VERSION,
    started_at: float | None = None,
) -> dict:
    started = time.perf_counter() if started_at is None else started_at
    width, height = detect_image_size(background_bytes)
    scale = min(max(foreground_scale, 0.05), 0.8)
    limit = min(max(candidate_count, 1), 10)

    candidate_templates = [
        (0.38, 0.58, 0.32, 0.86, "recommended", "推荐", "Mock: object is inside a stable support region."),
        (0.15, 0.55, 0.30, 0.61, "acceptable", "可接受", "Mock: position is plausible but less centered."),
        (0.72, 0.12, 0.28, 0.28, "rejected", "不推荐", "Mock: object appears unsupported or visually floating."),
        (0.52, 0.46, 0.26, 0.74, "acceptable", "可接受", "Mock: balanced placement with mild overlap risk."),
        (0.08, 0.18, 0.24, 0.52, "acceptable", "可接受", "Mock: composition is usable but visually peripheral."),
        (0.62, 0.66, 0.24, 0.43, "rejected", "不推荐", "Mock: placement competes with background structure."),
        (0.30, 0.20, 0.22, 0.39, "rejected", "不推荐", "Mock: object lacks a convincing support plane."),
        (0.47, 0.10, 0.20, 0.33, "rejected", "不推荐", "Mock: upper image region is unlikely for this object."),
        (0.04, 0.68, 0.18, 0.31, "rejected", "不推荐", "Mock: edge placement leaves weak visual context."),
        (0.78, 0.52, 0.18, 0.26, "rejected", "不推荐", "Mock: object would feel cramped near the boundary."),
    ]

    base_candidates = [
        {
            "rank": rank,
            "x": x,
            "y": y,
            "w": min(max_size, scale),
            "h": min(max_size, scale),
            "score": score,
            "tier": tier,
            "label": label,
            "reason": reason,
            "preview_url": None,
            "heatmap_url": None,
        }
        for rank, (x, y, max_size, score, tier, label, reason) in enumerate(candidate_templates, start=1)
    ]

    runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
    return {
        "request_id": f"mock-{uuid.uuid4().hex[:12]}",
        "model_version": model_version,
        "coord_type": "normalized_xywh",
        "runtime_ms": runtime_ms,
        "image_width": width,
        "image_height": height,
        "best_index": 0,
        "candidates": base_candidates[: min(limit, len(base_candidates))],
    }


def _detect_jpeg_size(data: bytes) -> tuple[int, int] | None:
    if len(data) < 4 or not data.startswith(b"\xff\xd8"):
        return None

    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue

        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            return None

        marker = data[offset]
        offset += 1
        if marker in {0xD8, 0xD9}:
            continue
        if offset + 2 > len(data):
            return None

        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            return None

        if 0xC0 <= marker <= 0xCF and marker not in {0xC4, 0xC8, 0xCC}:
            if offset + 7 > len(data):
                return None
            height = struct.unpack(">H", data[offset + 3 : offset + 5])[0]
            width = struct.unpack(">H", data[offset + 5 : offset + 7])[0]
            return max(1, width), max(1, height)

        offset += segment_length

    return None
