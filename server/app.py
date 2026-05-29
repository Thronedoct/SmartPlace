from __future__ import annotations

import time
import uuid
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field


MODEL_VERSION = "mock-v0"

app = FastAPI(
    title="SmartPlace Mock Inference Service",
    version="0.1.0",
    description="Phase-0 mock service for Android/backend integration.",
)


class Candidate(BaseModel):
    rank: int
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)
    score: float = Field(ge=0.0, le=1.0)
    tier: str
    label: str
    reason: str
    preview_url: str | None = None
    heatmap_url: str | None = None


class RecommendResponse(BaseModel):
    request_id: str
    model_version: str
    coord_type: str
    runtime_ms: int
    image_width: int
    image_height: int
    best_index: int
    candidates: list[Candidate]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "smartplace-mock",
        "model_version": MODEL_VERSION,
    }


@app.post("/api/place/recommend", response_model=RecommendResponse)
async def recommend_place(
    background: Annotated[UploadFile, File(description="Background image")],
    foreground: Annotated[UploadFile, File(description="Foreground object image")],
    mask: Annotated[UploadFile | None, File(description="Optional foreground mask")] = None,
    candidate_count: Annotated[int, Form(ge=1, le=10)] = 3,
    foreground_scale: Annotated[float, Form(gt=0.05, le=0.8)] = 0.25,
    mode: Annotated[str, Form()] = "auto",
) -> RecommendResponse:
    started = time.perf_counter()

    # Phase 0 deliberately avoids real image/model work. These reads prove that
    # the multipart upload path works and make later validation easier.
    background_bytes = await background.read()
    foreground_bytes = await foreground.read()
    if mask is not None:
        await mask.read()

    print(
        "mock recommendation",
        {
            "background": background.filename,
            "background_bytes": len(background_bytes),
            "foreground": foreground.filename,
            "foreground_bytes": len(foreground_bytes),
            "candidate_count": candidate_count,
            "foreground_scale": foreground_scale,
            "mode": mode,
        },
    )

    base_candidates = [
        Candidate(
            rank=1,
            x=0.38,
            y=0.58,
            w=min(0.32, foreground_scale),
            h=min(0.32, foreground_scale),
            score=0.86,
            tier="recommended",
            label="推荐",
            reason="Mock: object is inside a stable support region.",
        ),
        Candidate(
            rank=2,
            x=0.15,
            y=0.55,
            w=min(0.30, foreground_scale),
            h=min(0.30, foreground_scale),
            score=0.61,
            tier="acceptable",
            label="可接受",
            reason="Mock: position is plausible but less centered.",
        ),
        Candidate(
            rank=3,
            x=0.72,
            y=0.12,
            w=min(0.28, foreground_scale),
            h=min(0.28, foreground_scale),
            score=0.28,
            tier="rejected",
            label="不推荐",
            reason="Mock: object appears unsupported or visually floating.",
        ),
    ]
    candidates = base_candidates[:candidate_count]

    runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
    return RecommendResponse(
        request_id=f"mock-{uuid.uuid4().hex[:12]}",
        model_version=MODEL_VERSION,
        coord_type="normalized_xywh",
        runtime_ms=runtime_ms,
        image_width=1,
        image_height=1,
        best_index=0,
        candidates=candidates,
    )
