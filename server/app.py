from __future__ import annotations

from pathlib import Path
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from server.recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
except ModuleNotFoundError:
    from recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation

MODEL_VERSION = DEFAULT_MODEL_VERSION
ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
SAMPLES_DIR = ROOT_DIR / "OPAAndroidDemoSimp" / "app" / "src" / "main" / "assets" / "samples"

app = FastAPI(
    title="SmartPlace Mock Inference Service",
    version="0.1.0",
    description="Local inference service and web workspace for SmartPlace.",
)

if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")

if SAMPLES_DIR.exists():
    app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")


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


@app.get("/")
def web_workspace() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(WEB_DIR / "favicon.svg", media_type="image/svg+xml")


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
