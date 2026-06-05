from __future__ import annotations

import time
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from pydantic import BaseModel, Field

try:
    from server.recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
except ModuleNotFoundError:
    from recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation

MODEL_VERSION = DEFAULT_MODEL_VERSION

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

    return RecommendResponse(
        **build_mock_recommendation(
            candidate_count=candidate_count,
            foreground_scale=foreground_scale,
            background_bytes=background_bytes,
            model_version=MODEL_VERSION,
            started_at=started,
        )
    )
