from __future__ import annotations

from pathlib import Path
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from server.recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
    from server.scorer import DEFAULT_SCORER_MODE, get_scorer_status
except ModuleNotFoundError:
    from recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
    from scorer import DEFAULT_SCORER_MODE, get_scorer_status

MODEL_VERSION = DEFAULT_MODEL_VERSION
ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
SAMPLES_DIR = ROOT_DIR / "OPAAndroidDemoSimp" / "app" / "src" / "main" / "assets" / "samples"

app = FastAPI(
    title="SmartPlace Inference Service",
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
    scorer_status = get_scorer_status()
    return {
        "status": "ok",
        "service": "smartplace-inference",
        "model_version": scorer_status["model_version"],
        "scorer_mode": scorer_status["mode"],
        "scorer_status": scorer_status["status"],
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

    background_bytes = await background.read()
    foreground_bytes = await foreground.read()
    mask_bytes = await mask.read() if mask is not None else None
    scorer_mode = DEFAULT_SCORER_MODE if mode == "auto" else mode

    print(
        "place recommendation",
        {
            "background": background.filename,
            "background_bytes": len(background_bytes),
            "foreground": foreground.filename,
            "foreground_bytes": len(foreground_bytes),
            "mask_bytes": len(mask_bytes) if mask_bytes else 0,
            "candidate_count": candidate_count,
            "foreground_scale": foreground_scale,
            "mode": scorer_mode,
        },
    )

    try:
        recommendation = build_mock_recommendation(
            candidate_count=candidate_count,
            foreground_scale=foreground_scale,
            background_bytes=background_bytes,
            foreground_bytes=foreground_bytes,
            mask_bytes=mask_bytes,
            model_version=MODEL_VERSION,
            scorer_mode=scorer_mode,
            started_at=started,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return RecommendResponse(**recommendation)
