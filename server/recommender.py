from __future__ import annotations

import struct
import time
import uuid

try:
    from server.scorer import (
        DEFAULT_SCORER_MODE,
        is_simopa_lite_mode,
        is_simopa_mode,
        resolve_scorer_mode,
        score_candidate_boxes,
    )
except ModuleNotFoundError:
    from scorer import (
        DEFAULT_SCORER_MODE,
        is_simopa_lite_mode,
        is_simopa_mode,
        resolve_scorer_mode,
        score_candidate_boxes,
    )


DEFAULT_MODEL_VERSION = "mock-v0"
SIMOPA_LITE_MIN_CANDIDATE_BUDGET = 6


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
    foreground_bytes: bytes = b"",
    mask_bytes: bytes | None = None,
    model_version: str = DEFAULT_MODEL_VERSION,
    scorer_mode: str | None = None,
    started_at: float | None = None,
) -> dict:
    started = time.perf_counter() if started_at is None else started_at
    width, height = detect_image_size(background_bytes)
    scale = min(max(foreground_scale, 0.05), 0.8)
    limit = min(max(candidate_count, 1), 10)
    selected_scorer_mode = resolve_scorer_mode(scorer_mode)

    candidate_boxes = build_candidate_pool(
        background_size=(width, height),
        foreground_bytes=foreground_bytes,
        scale=scale,
        scorer_mode=selected_scorer_mode,
    )
    candidates_to_score = select_candidates_for_scoring(
        candidate_boxes,
        selected_scorer_mode,
        limit,
    )
    score_results = score_candidate_boxes(
        background_bytes=background_bytes,
        foreground_bytes=foreground_bytes,
        mask_bytes=mask_bytes,
        candidates=candidates_to_score,
        mode=selected_scorer_mode,
    )

    scored_candidates = list(zip(candidates_to_score, score_results))
    if is_simopa_mode(selected_scorer_mode):
        scored_candidates.sort(key=lambda item: item[1].score, reverse=True)

    base_candidates = []
    for display_rank, (candidate, score_result) in enumerate(scored_candidates[:limit], start=1):
        tier, label = score_to_tier(score_result.score)
        base_candidates.append(
            {
                "rank": display_rank,
                "x": candidate["x"],
                "y": candidate["y"],
                "w": candidate["w"],
                "h": candidate["h"],
                "score": score_result.score,
                "tier": tier,
                "label": label,
                "reason": build_reason(score_result.mode, score_result.score, candidate["base_reason"]),
                "preview_url": None,
                "heatmap_url": None,
            }
        )

    runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
    return {
        "request_id": f"{selected_scorer_mode}-{uuid.uuid4().hex[:12]}",
        "model_version": score_results[0].model_version if score_results else model_version,
        "coord_type": "normalized_xywh",
        "runtime_ms": runtime_ms,
        "image_width": width,
        "image_height": height,
        "best_index": 0,
        "candidates": base_candidates,
    }


def build_candidate_pool(
    *,
    background_size: tuple[int, int],
    foreground_bytes: bytes,
    scale: float,
    scorer_mode: str,
) -> list[dict]:
    if scorer_mode == "mock":
        return build_mock_candidate_templates(scale)

    box_width, box_height = estimate_candidate_box_size(
        background_size=background_size,
        foreground_bytes=foreground_bytes,
        scale=scale,
    )
    positions = [
        (0.38, 0.58, "center-lower support prior"),
        (0.42, 0.30, "dataset-like middle support prior"),
        (0.15, 0.55, "left-lower support prior"),
        (0.55, 0.55, "right-lower support prior"),
        (0.52, 0.46, "central support prior"),
        (0.25, 0.30, "left-middle support prior"),
        (0.60, 0.30, "right-middle support prior"),
        (0.72, 0.12, "upper-right rejection probe"),
        (0.08, 0.18, "upper-left context probe"),
        (0.04, 0.68, "lower-edge context probe"),
        (0.78, 0.52, "right-edge context probe"),
        (0.30, 0.20, "upper-middle rejection probe"),
    ]

    candidate_pool = []
    for rank, (x, y, reason) in enumerate(positions, start=1):
        candidate_pool.append(
            {
                "rank": rank,
                "x": clamp_float(x, 0.0, max(0.0, 1.0 - box_width)),
                "y": clamp_float(y, 0.0, max(0.0, 1.0 - box_height)),
                "w": box_width,
                "h": box_height,
                "base_score": 0.5,
                "base_tier": "acceptable",
                "base_label": "\u53ef\u63a5\u53d7",
                "base_reason": f"Candidate pool: {reason}.",
            }
        )
    return candidate_pool


def select_candidates_for_scoring(candidates: list[dict], scorer_mode: str, limit: int) -> list[dict]:
    if is_simopa_lite_mode(scorer_mode):
        budget = min(len(candidates), max(limit, SIMOPA_LITE_MIN_CANDIDATE_BUDGET))
        return candidates[:budget]
    if is_simopa_mode(scorer_mode):
        return candidates
    return candidates[:limit]


def build_mock_candidate_templates(scale: float) -> list[dict]:
    candidate_templates = [
        (0.38, 0.58, 0.32, 0.86, "recommended", "\u63a8\u8350", "Mock: object is inside a stable support region."),
        (0.15, 0.55, 0.30, 0.61, "acceptable", "\u53ef\u63a5\u53d7", "Mock: position is plausible but less centered."),
        (0.72, 0.12, 0.28, 0.28, "rejected", "\u4e0d\u63a8\u8350", "Mock: object appears unsupported or visually floating."),
        (0.52, 0.46, 0.26, 0.74, "acceptable", "\u53ef\u63a5\u53d7", "Mock: balanced placement with mild overlap risk."),
        (0.08, 0.18, 0.24, 0.52, "acceptable", "\u53ef\u63a5\u53d7", "Mock: composition is usable but visually peripheral."),
        (0.62, 0.66, 0.24, 0.43, "rejected", "\u4e0d\u63a8\u8350", "Mock: placement competes with background structure."),
        (0.30, 0.20, 0.22, 0.39, "rejected", "\u4e0d\u63a8\u8350", "Mock: object lacks a convincing support plane."),
        (0.47, 0.10, 0.20, 0.33, "rejected", "\u4e0d\u63a8\u8350", "Mock: upper image region is unlikely for this object."),
        (0.04, 0.68, 0.18, 0.31, "rejected", "\u4e0d\u63a8\u8350", "Mock: edge placement leaves weak visual context."),
        (0.78, 0.52, 0.18, 0.26, "rejected", "\u4e0d\u63a8\u8350", "Mock: object would feel cramped near the boundary."),
    ]

    candidate_boxes = []
    for rank, (x, y, max_size, score, tier, label, reason) in enumerate(candidate_templates, start=1):
        candidate_boxes.append(
            {
                "rank": rank,
                "x": x,
                "y": y,
                "w": min(max_size, scale),
                "h": min(max_size, scale),
                "base_score": score,
                "base_tier": tier,
                "base_label": label,
                "base_reason": reason,
            }
        )
    return candidate_boxes


def estimate_candidate_box_size(
    *,
    background_size: tuple[int, int],
    foreground_bytes: bytes,
    scale: float,
) -> tuple[float, float]:
    background_width, background_height = background_size
    foreground_width, foreground_height = detect_image_size(foreground_bytes)
    pixel_aspect = foreground_width / max(1, foreground_height)
    normalized_aspect = pixel_aspect * (background_height / max(1, background_width))

    if normalized_aspect >= 1.0:
        box_width = scale
        box_height = scale / normalized_aspect
    else:
        box_width = scale * normalized_aspect
        box_height = scale

    return clamp_float(box_width, 0.05, 0.8), clamp_float(box_height, 0.05, 0.8)


def clamp_float(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def score_to_tier(score: float) -> tuple[str, str]:
    if score >= 0.75:
        return "recommended", "\u63a8\u8350"
    if score >= 0.45:
        return "acceptable", "\u53ef\u63a5\u53d7"
    return "rejected", "\u4e0d\u63a8\u8350"


def build_reason(mode: str, score: float, mock_reason: str) -> str:
    if mode == "mock":
        return mock_reason
    if mode == "simopa-worker":
        return f"SimOPA Worker: candidate scored {score:.2f} by a persistent RGB+mask scorer."
    if mode == "simopa-lite":
        return f"SimOPA Lite: candidate scored {score:.2f} with a reduced candidate budget."
    if mode == "simopa-lite-worker":
        return f"SimOPA Lite Worker: candidate scored {score:.2f} with persistent reduced-budget scoring."
    return f"SimOPA: candidate scored {score:.2f} by RGB+mask placement assessment."


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
