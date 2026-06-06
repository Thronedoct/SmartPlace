from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import mean, median
import time

from run_score_calibration import (
    CALIBRATION_TEMPERATURE,
    IOU_THRESHOLD,
    apply_calibration,
    apply_case_ranks,
    apply_iou_dedup,
    read_rows as read_calibration_source_rows,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
TABLE_DIR = ROOT_DIR / "report" / "tables"
LOG_DIR = ROOT_DIR / "report" / "logs"

DEFAULT_RUNTIME_CSV = TABLE_DIR / "inference_runtime.csv"
DEFAULT_CHANGE_CSV = TABLE_DIR / "model_change_summary.csv"
DEFAULT_LOG = LOG_DIR / "evidence_summary.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize SmartPlace runtime and model-change evidence."
    )
    parser.add_argument("--runtime-csv", default=str(DEFAULT_RUNTIME_CSV))
    parser.add_argument("--change-csv", default=str(DEFAULT_CHANGE_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime_csv = Path(args.runtime_csv)
    change_csv = Path(args.change_csv)
    log_path = Path(args.log_path)

    runtime_csv.parent.mkdir(parents=True, exist_ok=True)
    change_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    runtime_rows = build_runtime_rows()
    change_rows = build_change_rows()

    write_csv(runtime_csv, runtime_rows)
    write_csv(change_csv, change_rows)
    write_log(log_path, runtime_rows, change_rows)

    print(f"runtime_rows={len(runtime_rows)}")
    print(f"change_rows={len(change_rows)}")
    print(f"runtime_csv={runtime_csv}")
    print(f"change_csv={change_csv}")
    print(f"log_path={log_path}")


def build_runtime_rows() -> list[dict[str, object]]:
    ranking_rows = read_csv(TABLE_DIR / "candidate_ranking_v1.csv")
    rgb_mask_rows = read_csv(TABLE_DIR / "rgb_vs_mask_comparison.csv")
    calibration_rows = read_csv(TABLE_DIR / "score_calibration_v1.csv")
    occlusion_rows = read_csv(TABLE_DIR / "occlusion_explainability_v1.csv")

    baseline_log = parse_key_value_log(LOG_DIR / "opa_baseline_smoke.txt")
    api_log = parse_key_value_log(LOG_DIR / "api_simopa_smoke.txt")
    ranking_log = parse_key_value_log(LOG_DIR / "candidate_ranking_v1.txt")
    rgb_log = parse_key_value_log(LOG_DIR / "rgb_vs_mask_comparison.txt")
    calibration_log = parse_key_value_log(LOG_DIR / "score_calibration_v1.txt")
    occlusion_log = parse_key_value_log(LOG_DIR / "occlusion_explainability_v1.txt")

    calibration_elapsed = measure_calibration_postprocess(TABLE_DIR / "candidate_ranking_v1.csv")

    rows = [
        runtime_row(
            stage_id="R001",
            stage_name="mock recommendation",
            mode="mock",
            model_version="mock-v0",
            device="cpu",
            source_artifact="server/recommender.py",
            cases=1,
            candidate_rows=3,
            score_calls=3,
            elapsed_seconds=0.001,
            inner_runtimes_ms=[1, 1, 1],
            runtime_source="mock scorer boundary minimum runtime",
            notes="Mock baseline uses deterministic template scores; included only as an engineering baseline.",
        ),
        runtime_row(
            stage_id="R002",
            stage_name="SimOPA single composite smoke",
            mode="simopa-full",
            model_version="simopa-rgb-mask-v1",
            device=baseline_log.get("device", "cuda:0"),
            source_artifact="report/logs/opa_baseline_smoke.txt",
            cases=1,
            candidate_rows=1,
            score_calls=1,
            elapsed_seconds=float_value(baseline_log.get("runtime_ms")) / 1000.0,
            inner_runtimes_ms=[float_value(baseline_log.get("runtime_ms"))],
            runtime_source="recorded by run_simopa_smoke.py",
            notes="Direct SimOPA example scoring with released checkpoint.",
        ),
        runtime_row(
            stage_id="R003",
            stage_name="FastAPI SimOPA multipart smoke",
            mode="simopa-full",
            model_version=api_log.get("model_version", "simopa-rgb-mask-v1"),
            device="cuda:0",
            source_artifact="report/logs/api_simopa_smoke.txt",
            cases=1,
            candidate_rows=3,
            score_calls=12,
            elapsed_seconds=float_value(api_log.get("runtime_ms")) / 1000.0,
            inner_runtimes_ms=[],
            runtime_source="API response runtime_ms",
            notes="Endpoint returns Top 3 but scores the full 12-candidate SimOPA prior pool.",
        ),
        runtime_row(
            stage_id="R004",
            stage_name="18-case candidate ranking",
            mode="simopa-full",
            model_version=first_value(ranking_rows, "model_version", "simopa-rgb-mask-v1"),
            device="cuda:0",
            source_artifact="report/tables/candidate_ranking_v1.csv",
            cases=count_unique(ranking_rows, "case_id"),
            candidate_rows=len(ranking_rows),
            score_calls=len(ranking_rows),
            elapsed_seconds=float_value(ranking_log.get("elapsed_seconds")),
            inner_runtimes_ms=numeric_column(ranking_rows, "runtime_ms"),
            runtime_source="candidate_ranking_v1.txt plus per-candidate runtime_ms",
            notes="Scores OPA labeled candidate plus generated prior pool for each case.",
        ),
        runtime_row(
            stage_id="R005",
            stage_name="RGB/mask ablation",
            mode="simopa-full",
            model_version=rgb_log.get("model_version", "simopa-mask-ablation-v1"),
            device=rgb_log.get("device", "cuda:0"),
            source_artifact="report/tables/rgb_vs_mask_comparison.csv",
            cases=count_unique(rgb_mask_rows, "case_id"),
            candidate_rows=len(rgb_mask_rows),
            score_calls=len(rgb_mask_rows) * 3,
            elapsed_seconds=float_value(rgb_log.get("elapsed_seconds")),
            inner_runtimes_ms=[],
            runtime_source="rgb_vs_mask_comparison.txt",
            notes="Each candidate is scored with object mask, bbox mask, and blank mask.",
        ),
        runtime_row(
            stage_id="R006",
            stage_name="score calibration and IoU dedup",
            mode="postprocess",
            model_version=first_value(calibration_rows, "model_version", "simopa-rgb-mask-v1"),
            device="cpu",
            source_artifact="report/tables/score_calibration_v1.csv",
            cases=int_value(calibration_log.get("cases"), count_unique(calibration_rows, "case_id")),
            candidate_rows=len(calibration_rows),
            score_calls=0,
            elapsed_seconds=calibration_elapsed,
            inner_runtimes_ms=[],
            runtime_source="measured by run_evidence_summary.py",
            notes="No model inference; applies temperature scaling and IoU dedup on existing scores.",
        ),
        runtime_row(
            stage_id="R007",
            stage_name="occlusion explainability",
            mode="simopa-full",
            model_version=occlusion_log.get("model_version", "simopa-occlusion-v1"),
            device=occlusion_log.get("device", "cuda:0"),
            source_artifact="report/tables/occlusion_explainability_v1.csv",
            cases=len(occlusion_rows),
            candidate_rows=len(occlusion_rows),
            score_calls=len(occlusion_rows) * (int_value(occlusion_log.get("grid_size"), 6) ** 2 + 1),
            elapsed_seconds=float_value(occlusion_log.get("elapsed_seconds")),
            inner_runtimes_ms=[],
            runtime_source="occlusion_explainability_v1.txt",
            notes="Each representative case gets one baseline score plus grid occlusion scores.",
        ),
    ]
    return rows


def runtime_row(
    *,
    stage_id: str,
    stage_name: str,
    mode: str,
    model_version: str,
    device: str,
    source_artifact: str,
    cases: int,
    candidate_rows: int,
    score_calls: int,
    elapsed_seconds: float,
    inner_runtimes_ms: list[float],
    runtime_source: str,
    notes: str,
) -> dict[str, object]:
    batch_avg = (elapsed_seconds * 1000.0 / score_calls) if score_calls else ""
    return {
        "stage_id": stage_id,
        "stage_name": stage_name,
        "mode": mode,
        "model_version": model_version,
        "device": device,
        "source_artifact": source_artifact,
        "cases": cases,
        "candidate_rows": candidate_rows,
        "score_calls": score_calls,
        "elapsed_seconds": round(elapsed_seconds, 4),
        "batch_avg_ms_per_score_call": round(batch_avg, 2) if batch_avg != "" else "",
        "mean_inner_score_ms": round(mean(inner_runtimes_ms), 2) if inner_runtimes_ms else "",
        "median_inner_score_ms": round(median(inner_runtimes_ms), 2) if inner_runtimes_ms else "",
        "p95_inner_score_ms": round(percentile(inner_runtimes_ms, 0.95), 2) if inner_runtimes_ms else "",
        "runtime_source": runtime_source,
        "notes": notes,
    }


def build_change_rows() -> list[dict[str, str]]:
    return [
        change_row(
            "C001",
            "Real model integration",
            "functionality",
            "Expose SimOPA as a scorer mode behind the FastAPI recommendation API.",
            "server/scorer.py; server/recommender.py; experiments/opa_baseline/score_candidates.py",
            "report/tables/api_simopa_smoke.csv; report/logs/api_simopa_smoke.txt",
            "completed",
            "Proves the demo is backed by local model inference rather than mock-only output.",
            "Subprocess model loading is slower than an in-process persistent scorer.",
            "Add full/lite scorer modes and runtime comparison.",
        ),
        change_row(
            "C002",
            "Top 3 candidate ranking",
            "functionality",
            "Score OPA labeled placement and generated prior candidates, then rank Top 3.",
            "experiments/opa_baseline/run_candidate_ranking.py; server/recommender.py",
            "report/tables/candidate_ranking_v1.csv; report/tables/opa_18_case_summary.csv",
            "completed",
            "Turns a single score model into an object-placement recommendation workflow.",
            "Current evidence is 18 cases; high-standard plan expands to 50 or 100 cases.",
            "Generate candidate_ranking_v2_50.csv or candidate_ranking_v2_100.csv.",
        ),
        change_row(
            "C003",
            "RGB/mask input ablation",
            "input adaptation",
            "Compare object mask, coarse bbox mask, and blank mask for the same composite candidates.",
            "experiments/opa_baseline/run_rgb_mask_comparison.py",
            "report/tables/rgb_vs_mask_comparison.csv; report/logs/rgb_vs_mask_comparison.txt",
            "completed",
            "Shows that the mask channel materially changes scores and Top 3 membership.",
            "This is an ablation of the SimOPA input, not a backbone rewrite.",
            "Add mask dilation/erosion robustness tests.",
        ),
        change_row(
            "C004",
            "Score calibration and tier labels",
            "output adaptation",
            "Apply temperature scaling and map scores to recommended/acceptable/rejected tiers.",
            "experiments/opa_baseline/run_score_calibration.py; server/recommender.py",
            "report/tables/score_calibration_v1.csv; report/logs/score_calibration_v1.txt",
            "completed",
            "Makes saturated model scores easier to interpret in the Web app and report.",
            "Calibration is post-hoc and does not retrain the scorer.",
            "Surface confidence prompts in the Web UI.",
        ),
        change_row(
            "C005",
            "Candidate IoU dedup",
            "postprocess reliability",
            "Remove highly overlapping candidates from ranked results with an IoU threshold.",
            "experiments/opa_baseline/run_score_calibration.py",
            "report/tables/score_calibration_v1.csv",
            "completed",
            "Reduces duplicate Top 3 recommendations and clarifies boundary cases.",
            "Does not solve score saturation when multiple distinct candidates score near 1.0.",
            "Add frontend warnings for saturated or overlapping Top 3 results.",
        ),
        change_row(
            "C006",
            "Representative case gallery",
            "case analysis",
            "Render success, boundary, false-positive-risk, and clear-rejection examples.",
            "experiments/opa_baseline/run_case_gallery.py",
            "report/tables/failure_cases.csv; report/screenshots/cases/",
            "completed",
            "Provides concrete artifacts for teammate-owned report/PPT and live demo.",
            "Only five cases are visualized; not a statistical benchmark.",
            "Connect built-in Web samples to these representative cases.",
        ),
        change_row(
            "C007",
            "Occlusion explainability",
            "explainability",
            "Run a 6x6 occlusion sensitivity test and render heatmaps for representative cases.",
            "experiments/opa_baseline/run_occlusion_explainability.py",
            "report/tables/occlusion_explainability_v1.csv; report/screenshots/explainability/",
            "completed",
            "Shows which image regions affect SimOPA scores and supports model-explanation credit.",
            "Occlusion is slower than a single forward pass and currently offline.",
            "Link heatmaps from the Web case area.",
        ),
        change_row(
            "C008",
            "Runtime evidence summary",
            "measurement",
            "Aggregate end-to-end and per-candidate runtime evidence from existing experiments.",
            "experiments/opa_baseline/run_evidence_summary.py",
            "report/tables/inference_runtime.csv; report/logs/evidence_summary.txt",
            "completed",
            "Gives the project a single runtime table for local inference proof.",
            "Some rows use batch-level logs rather than per-call model timers.",
            "Use this table to compare full/lite modes after lite mode lands.",
        ),
        change_row(
            "C009",
            "Web export, samples, and confidence prompts",
            "frontend workflow",
            "Export current recommendation evidence and load stable demo cases in the Web app.",
            "web/app.js; web/index.html; web/styles.css; server/app.py; docs/API.md",
            "Web UI validation V016; /api/demo/cases; exported JSON/CSV",
            "completed",
            "Makes the app easier to demo and reduces live-presentation risk.",
            "Current validation used Playwright fallback because the in-app Browser runtime failed to start.",
            "Deepen visual polish and classroom demo mode.",
        ),
        change_row(
            "C010",
            "Lightweight inference track",
            "lightweight model/serving",
            "Compare simopa-full, simopa-lite, and optional LightOPA ResNet18/MobileNet scorer.",
            "planned: server/scorer.py; experiments/opa_lightweight/",
            "planned: report/tables/lite_mode_comparison.csv",
            "planned_next",
            "Adds a speed/quality trade-off story and reduces model-change wording risk.",
            "True lightweight scorer requires training or adaptation work.",
            "Start with simopa-lite candidate-count reduction, then train LightOPA if time allows.",
        ),
        change_row(
            "C011",
            "Robustness ablation",
            "reliability",
            "Perturb mask shape, candidate position, and candidate scale to test score stability.",
            "planned: experiments/robustness/",
            "planned: report/tables/robustness_ablation.csv",
            "planned_next",
            "Adds high-standard reliability evidence without replacing the main model.",
            "Requires careful case selection so results are interpretable.",
            "Run after runtime evidence and Web demo basics.",
        ),
    ]


def change_row(
    change_id: str,
    area: str,
    change_type: str,
    description: str,
    implementation_files: str,
    evidence_artifacts: str,
    status: str,
    high_score_value: str,
    limitation: str,
    next_upgrade: str,
) -> dict[str, str]:
    return {
        "change_id": change_id,
        "area": area,
        "change_type": change_type,
        "description": description,
        "implementation_files": implementation_files,
        "evidence_artifacts": evidence_artifacts,
        "status": status,
        "high_score_value": high_score_value,
        "limitation": limitation,
        "next_upgrade": next_upgrade,
    }


def measure_calibration_postprocess(ranking_csv: Path) -> float:
    started = time.perf_counter()
    rows = read_calibration_source_rows(ranking_csv)
    apply_calibration(rows, CALIBRATION_TEMPERATURE)
    apply_case_ranks(rows, score_key="calibrated_score", rank_key="calibrated_rank")
    apply_iou_dedup(rows, IOU_THRESHOLD)
    return time.perf_counter() - started


def read_csv(path: Path) -> list[dict[str, str]]:
    require_existing_file(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_log(
    path: Path,
    runtime_rows: list[dict[str, object]],
    change_rows: list[dict[str, str]],
) -> None:
    completed_changes = [row for row in change_rows if row["status"] == "completed"]
    planned_changes = [row for row in change_rows if row["status"] != "completed"]
    with path.open("w", encoding="utf-8") as handle:
        handle.write("SmartPlace evidence summary\n")
        handle.write(f"runtime_rows={len(runtime_rows)}\n")
        handle.write(f"change_rows={len(change_rows)}\n")
        handle.write(f"completed_changes={len(completed_changes)}\n")
        handle.write(f"planned_changes={len(planned_changes)}\n")
        for row in runtime_rows:
            handle.write(
                "runtime "
                f"{row['stage_id']} {row['stage_name']} "
                f"elapsed_seconds={row['elapsed_seconds']} "
                f"score_calls={row['score_calls']} "
                f"source={row['source_artifact']}\n"
            )


def parse_key_value_log(path: Path) -> dict[str, str]:
    require_existing_file(path)
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if " " in key:
            continue
        values[key] = value
    return values


def numeric_column(rows: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = row.get(key, "")
        if value == "":
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    return values


def first_value(rows: list[dict[str, str]], key: str, fallback: str) -> str:
    for row in rows:
        value = row.get(key)
        if value:
            return value
    return fallback


def count_unique(rows: list[dict[str, str]], key: str) -> int:
    return len({row[key] for row in rows if row.get(key)})


def float_value(value: object, fallback: float = 0.0) -> float:
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def int_value(value: object, fallback: int = 0) -> int:
    if value is None or value == "":
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = min(len(sorted_values) - 1, max(0, round((len(sorted_values) - 1) * q)))
    return sorted_values[index]


def require_existing_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


if __name__ == "__main__":
    main()
