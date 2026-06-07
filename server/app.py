from __future__ import annotations

import csv
from pathlib import Path
import time
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    from server.demo_assets import (
        DEMO_CASE_IDS,
        DEMO_CASE_TITLES,
        demo_case_available,
        optional_demo_url,
        resolve_demo_asset,
    )
    from server.recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
    from server.scorer import DEFAULT_SCORER_MODE, get_scorer_status
except ModuleNotFoundError:
    from demo_assets import (
        DEMO_CASE_IDS,
        DEMO_CASE_TITLES,
        demo_case_available,
        optional_demo_url,
        resolve_demo_asset,
    )
    from recommender import DEFAULT_MODEL_VERSION, build_mock_recommendation
    from scorer import DEFAULT_SCORER_MODE, get_scorer_status

MODEL_VERSION = DEFAULT_MODEL_VERSION
ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT_DIR / "web"
SAMPLES_DIR = ROOT_DIR / "OPAAndroidDemoSimp" / "app" / "src" / "main" / "assets" / "samples"
REPORT_TABLE_DIR = ROOT_DIR / "report" / "tables"
REPORT_SPLIT_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "report_18.csv"

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


class DemoCase(BaseModel):
    case_id: str
    title: str
    case_type: str
    dataset_label: int
    note: str
    foreground_scale: float
    candidate_count: int
    recommended_mode: str
    available: bool
    background_url: str
    foreground_url: str
    mask_url: str
    heatmap_url: str | None = None
    panel_url: str | None = None


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


@app.get("/api/demo/cases", response_model=list[DemoCase])
def demo_cases() -> list[DemoCase]:
    failure_rows = read_csv_by_key(REPORT_TABLE_DIR / "failure_cases.csv", "case_id")
    summary_rows = read_csv_by_key(REPORT_TABLE_DIR / "opa_18_case_summary.csv", "case_id")
    split_rows = read_csv_by_key(REPORT_SPLIT_CSV, "case_id")

    cases = []
    for case_id in DEMO_CASE_IDS:
        failure = failure_rows.get(case_id, {})
        summary = summary_rows.get(case_id, {})
        split = split_rows.get(case_id, {})
        case_type = failure.get("case_type", "demo_case")
        cases.append(
            DemoCase(
                case_id=case_id,
                title=DEMO_CASE_TITLES.get(case_type, case_id),
                case_type=case_type,
                dataset_label=safe_int(
                    failure.get("dataset_label") or summary.get("dataset_label"),
                    0,
                ),
                note=failure.get("note", ""),
                foreground_scale=safe_float(split.get("scale"), 0.35),
                candidate_count=3,
                recommended_mode="simopa",
                available=demo_case_available(case_id, summary),
                background_url=f"/api/demo/cases/{case_id}/background",
                foreground_url=f"/api/demo/cases/{case_id}/foreground",
                mask_url=f"/api/demo/cases/{case_id}/mask",
                heatmap_url=optional_demo_url(case_id, "heatmap"),
                panel_url=optional_demo_url(case_id, "panel"),
            )
        )
    return cases


@app.get("/api/demo/cases/{case_id}/{asset_name}")
def demo_case_asset(case_id: str, asset_name: str) -> FileResponse:
    if case_id not in DEMO_CASE_IDS:
        raise HTTPException(status_code=404, detail=f"Unknown demo case: {case_id}")

    summary_rows = read_csv_by_key(REPORT_TABLE_DIR / "opa_18_case_summary.csv", "case_id")
    asset_path = resolve_demo_asset(case_id, asset_name, summary_rows.get(case_id, {}))
    if asset_path is None or not asset_path.is_file():
        raise HTTPException(status_code=404, detail=f"Missing demo asset: {case_id}/{asset_name}")
    return FileResponse(asset_path)


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


def read_csv_by_key(path: Path, key: str) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row[key]: row for row in csv.DictReader(handle) if row.get(key)}


def safe_int(value: object, default: int) -> int:
    try:
        text = str(value).strip()
        return int(float(text)) if text else default
    except (TypeError, ValueError):
        return default


def safe_float(value: object, default: float) -> float:
    try:
        text = str(value).strip()
        return float(text) if text else default
    except (TypeError, ValueError):
        return default
