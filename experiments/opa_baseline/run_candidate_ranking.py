from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from server.recommender import build_candidate_pool, detect_image_size, score_to_tier  # noqa: E402
from server.scorer import score_candidate_boxes  # noqa: E402

DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_SMOKE_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "smoke_100.csv"
DEFAULT_REPORT_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "report_18.csv"
DEFAULT_RANKING_CSV = ROOT_DIR / "report" / "tables" / "candidate_ranking_v1.csv"
DEFAULT_SUMMARY_CSV = ROOT_DIR / "report" / "tables" / "opa_18_case_summary.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "candidate_ranking_v1.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build 18-case SimOPA candidate ranking evidence.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--smoke-csv", default=str(DEFAULT_SMOKE_CSV))
    parser.add_argument("--report-csv", default=str(DEFAULT_REPORT_CSV))
    parser.add_argument("--ranking-csv", default=str(DEFAULT_RANKING_CSV))
    parser.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--positive-count", type=int, default=9)
    parser.add_argument("--negative-count", type=int, default=9)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    smoke_csv = Path(args.smoke_csv)
    report_csv = Path(args.report_csv)
    ranking_csv = Path(args.ranking_csv)
    summary_csv = Path(args.summary_csv)
    log_path = Path(args.log_path)

    ranking_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    report_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    selected_cases = select_cases(smoke_csv, args.positive_count, args.negative_count)
    background_index = index_images(dataset_root / "background")
    foreground_index = index_images(dataset_root / "foreground", include_masks=True)

    started = time.perf_counter()
    ranking_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []

    for index, case in enumerate(selected_cases, start=1):
        case_id = case["case_id"]
        print(f"[{index:02d}/{len(selected_cases):02d}] scoring {case_id}")
        scored_rows, summary_row = score_case(case, background_index, foreground_index)
        ranking_rows.extend(scored_rows)
        summary_rows.append(summary_row)
        report_rows.append(case)

    write_csv(report_csv, report_rows)
    write_csv(ranking_csv, ranking_rows)
    write_csv(summary_csv, summary_rows)
    write_log(log_path, summary_rows, ranking_rows, time.perf_counter() - started)

    print(f"cases={len(summary_rows)}")
    print(f"candidate_rows={len(ranking_rows)}")
    print(f"ranking_csv={ranking_csv}")
    print(f"summary_csv={summary_csv}")
    print(f"log_path={log_path}")


def select_cases(smoke_csv: Path, positive_count: int, negative_count: int) -> list[dict[str, str]]:
    positives: list[dict[str, str]] = []
    negatives: list[dict[str, str]] = []
    with smoke_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["usable"] != "yes":
                continue
            if row["label"] == "1" and len(positives) < positive_count:
                positives.append(row)
            elif row["label"] == "0" and len(negatives) < negative_count:
                negatives.append(row)
            if len(positives) == positive_count and len(negatives) == negative_count:
                break

    if len(positives) < positive_count or len(negatives) < negative_count:
        raise RuntimeError(
            f"Not enough usable cases. positives={len(positives)}, negatives={len(negatives)}"
        )
    return positives + negatives


def index_images(root: Path, *, include_masks: bool = False) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in root.rglob("*.jpg"):
        stem = path.stem
        if stem.startswith("mask_") and not include_masks:
            continue
        index[stem] = path
    return index


def score_case(
    case: dict[str, str],
    background_index: dict[str, Path],
    foreground_index: dict[str, Path],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    fg_id = case["fg_id"]
    bg_id = case["bg_id"]
    background_path = require_indexed_path(background_index, bg_id)
    foreground_path = require_indexed_path(foreground_index, fg_id)
    foreground_mask_path = require_indexed_path(foreground_index, f"mask_{fg_id}")

    background_bytes = background_path.read_bytes()
    foreground_bytes = foreground_path.read_bytes()
    foreground_mask_bytes = foreground_mask_path.read_bytes()
    image_width, image_height = detect_image_size(background_bytes)
    x_px, y_px, w_px, h_px = parse_position(case["position"])

    annotation_candidate = {
        "rank": 1,
        "x": x_px / image_width,
        "y": y_px / image_height,
        "w": w_px / image_width,
        "h": h_px / image_height,
        "base_score": 0.5,
        "base_reason": "OPA labeled placement.",
        "candidate_source": "opa_position",
        "candidate_id": "opa_position",
    }
    prior_candidates = build_candidate_pool(
        background_size=(image_width, image_height),
        foreground_bytes=foreground_bytes,
        scale=float(case["scale"]),
        scorer_mode="simopa",
    )
    candidates = [annotation_candidate]
    for prior in prior_candidates:
        rank = len(candidates) + 1
        candidates.append(
            {
                **prior,
                "rank": rank,
                "candidate_source": "prior_pool",
                "candidate_id": f"prior_{prior['rank']:02d}",
            }
        )

    score_results = score_candidate_boxes(
        background_bytes=background_bytes,
        foreground_bytes=foreground_bytes,
        mask_bytes=foreground_mask_bytes,
        candidates=candidates,
        mode="simopa",
    )
    scored = list(zip(candidates, score_results))
    scored.sort(key=lambda item: item[1].score, reverse=True)

    dataset_position_rank = 0
    dataset_position_score = 0.0
    ranking_rows: list[dict[str, object]] = []
    for model_rank, (candidate, result) in enumerate(scored, start=1):
        tier, label = score_to_tier(result.score)
        is_dataset_position = candidate["candidate_source"] == "opa_position"
        if is_dataset_position:
            dataset_position_rank = model_rank
            dataset_position_score = result.score
        ranking_rows.append(
            {
                "case_id": case["case_id"],
                "split": case["split"],
                "dataset_label": case["label"],
                "fg_id": fg_id,
                "bg_id": bg_id,
                "foreground_category": foreground_path.parent.name,
                "background_category": background_path.parent.name,
                "candidate_source": candidate["candidate_source"],
                "candidate_id": candidate["candidate_id"],
                "model_rank": model_rank,
                "is_top3": "yes" if model_rank <= 3 else "no",
                "score": round(result.score, 4),
                "tier": tier,
                "label": label,
                "x": round(candidate["x"], 6),
                "y": round(candidate["y"], 6),
                "w": round(candidate["w"], 6),
                "h": round(candidate["h"], 6),
                "model_version": result.model_version,
                "runtime_ms": result.runtime_ms,
            }
        )

    top3 = scored[:3]
    expected = expected_case_result(case["label"], dataset_position_score, dataset_position_rank)
    summary_row = {
        "case_id": case["case_id"],
        "dataset_label": case["label"],
        "fg_id": fg_id,
        "bg_id": bg_id,
        "foreground_category": foreground_path.parent.name,
        "background_category": background_path.parent.name,
        "image_width": image_width,
        "image_height": image_height,
        "dataset_position_score": round(dataset_position_score, 4),
        "dataset_position_rank": dataset_position_rank,
        "top1_source": top3[0][0]["candidate_source"],
        "top1_score": round(top3[0][1].score, 4),
        "top3_scores": ";".join(f"{result.score:.4f}" for _, result in top3),
        "assessment": expected,
        "model_version": top3[0][1].model_version,
    }
    return ranking_rows, summary_row


def require_indexed_path(index: dict[str, Path], key: str) -> Path:
    if key not in index:
        raise FileNotFoundError(f"Could not find OPA image id: {key}")
    return index[key]


def parse_position(position: str) -> tuple[int, int, int, int]:
    parsed = ast.literal_eval(position)
    if not isinstance(parsed, list) or len(parsed) != 4:
        raise ValueError(f"Invalid OPA position: {position}")
    return tuple(int(value) for value in parsed)  # type: ignore[return-value]


def expected_case_result(dataset_label: str, score: float, rank: int) -> str:
    if dataset_label == "1":
        if score >= 0.75 and rank <= 3:
            return "pass_positive_high_rank"
        if score >= 0.45:
            return "review_positive_high_score_low_rank"
        return "fail_positive_low_score"

    if score < 0.45:
        return "pass_negative_rejected"
    return "review_negative_high_score"


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_log(
    path: Path,
    summary_rows: list[dict[str, object]],
    ranking_rows: list[dict[str, object]],
    elapsed_seconds: float,
) -> None:
    positive_rows = [row for row in summary_rows if row["dataset_label"] == "1"]
    negative_rows = [row for row in summary_rows if row["dataset_label"] == "0"]
    lines = [
        "SmartPlace candidate ranking v1",
        f"cases={len(summary_rows)}",
        f"candidate_rows={len(ranking_rows)}",
        f"positive_cases={len(positive_rows)}",
        f"negative_cases={len(negative_rows)}",
        f"elapsed_seconds={elapsed_seconds:.1f}",
        f"positive_pass={sum(1 for row in positive_rows if str(row['assessment']).startswith('pass_'))}",
        f"negative_pass={sum(1 for row in negative_rows if str(row['assessment']).startswith('pass_'))}",
    ]
    for row in summary_rows:
        lines.append(
            "case "
            f"{row['case_id']} "
            f"label={row['dataset_label']} "
            f"dataset_score={row['dataset_position_score']} "
            f"dataset_rank={row['dataset_position_rank']} "
            f"top1={row['top1_source']}:{row['top1_score']} "
            f"assessment={row['assessment']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
