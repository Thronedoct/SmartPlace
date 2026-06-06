from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
import traceback

import torch
from PIL import Image

from score_candidates import (
    DEFAULT_WEIGHT,
    MODEL_VERSION,
    compose_candidate,
    preprocess_pil_pair,
    resolve_device,
)
from simopa import ObjectPlacementAssessmentModel


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Persistent JSONL worker for SimOPA candidate scoring.")
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT), help="SimOPA weight path.")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, etc.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)
    model = ObjectPlacementAssessmentModel(device, opt)
    model.model.eval()

    write_message(
        {
            "type": "ready",
            "model_version": MODEL_VERSION,
            "device": str(device),
        }
    )

    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue

        request = None
        try:
            request = json.loads(stripped)
            if request.get("command") == "shutdown":
                write_message({"type": "shutdown"})
                return
            write_message(score_request(request, model, device))
        except Exception as exc:  # noqa: BLE001 - worker must keep protocol errors explicit.
            write_message(
                {
                    "type": "error",
                    "request_id": request.get("request_id") if request else None,
                    "error": str(exc),
                    "traceback": traceback.format_exc(limit=5),
                }
            )


def score_request(
    request: dict,
    model: ObjectPlacementAssessmentModel,
    device: torch.device,
) -> dict:
    background = Image.open(require_path(request, "background")).convert("RGB")
    foreground = Image.open(require_path(request, "foreground"))
    mask_path = request.get("mask")
    foreground_mask = Image.open(mask_path).convert("L") if mask_path else None

    scored = []
    for candidate in request["candidates"]:
        started = time.perf_counter()
        composite, composite_mask = compose_candidate(background, foreground, foreground_mask, candidate)
        with torch.no_grad():
            inputs = preprocess_pil_pair(composite, composite_mask, model.image_size, device)
            logits = model.model(inputs)
            score = torch.softmax(logits, dim=-1)[0, 1].cpu().item()
        scored.append(
            {
                "rank": candidate["rank"],
                "score": round(float(score), 4),
                "runtime_ms": max(1, round((time.perf_counter() - started) * 1000)),
            }
        )

    return {
        "type": "result",
        "request_id": request["request_id"],
        "model_version": MODEL_VERSION,
        "device": str(device),
        "scores": scored,
    }


def require_path(request: dict, key: str) -> Path:
    value = request.get(key)
    if not value:
        raise ValueError(f"Missing request path: {key}")
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def write_message(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
