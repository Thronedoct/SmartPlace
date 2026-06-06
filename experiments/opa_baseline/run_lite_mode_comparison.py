from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from run_candidate_ranking import (  # noqa: E402
    expected_case_result,
    index_images,
    parse_position,
    require_existing_dir,
    require_indexed_path,
    write_csv,
)
from server.recommender import (  # noqa: E402
    SIMOPA_LITE_MIN_CANDIDATE_BUDGET,
    build_candidate_pool,
    detect_image_size,
)
from server.scorer import score_candidate_boxes  # noqa: E402


DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_SPLIT_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "report_50.csv"
DEFAULT_FULL_RANKING_CSV = ROOT_DIR / "report" / "tables" / "candidate_ranking_v2_50.csv"
DEFAULT_FULL_SUMMARY_CSV = ROOT_DIR / "report" / "tables" / "opa_50_case_summary.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "lite_mode_comparison.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "lite_mode_comparison.txt"
DEFAULT_FULL_LOG = ROOT_DIR / "report" / "logs" / "candidate_ranking_v2_50.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare full SimOPA candidate ranking with a lite candidate-budget mode."
    )
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--split-csv", default=str(DEFAULT_SPLIT_CSV))
    parser.add_argument("--full-ranking-csv", default=str(DEFAULT_FULL_RANKING_CSV))
    parser.add_argument("--full-summary-csv", default=str(DEFAULT_FULL_SUMMARY_CSV))
    parser.add_argument("--full-log", default=str(DEFAULT_FULL_LOG))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--lite-budget", type=int, default=SIMOPA_LITE_MIN_CANDIDATE_BUDGET)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    split_csv = Path(args.split_csv)
    full_ranking_csv = Path(args.full_ranking_csv)
    full_summary_csv = Path(args.full_summary_csv)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    require_existing_dir(dataset_root, "dataset root")
    require_existing_dir(dataset_root / "background", "OPA background directory")
    require_existing_dir(dataset_root / "foreground", "OPA foreground directory")

    cases = read_rows(split_csv)
    full_rows_by_case = group_rows(read_rows(full_ranking_csv), "case_id")
    full_summary_by_case = {row["case_id"]: row for row in read_rows(full_summary_csv)}
    background_index = index_images(dataset_root / "background")
    foreground_index = index_images(dataset_root / "foreground", include_masks=True)

    started = time.perf_counter()
    comparison_rows: list[dict[str, object]] = []
    for index, case in enumerate(cases, start=1):
        case_id = case["case_id"]
        print(f"[{index:02d}/{len(cases):02d}] lite scoring {case_id}")
        comparison_rows.append(
            compare_case(
                case=case,
                full_rows=full_rows_by_case[case_id],
                full_summary=full_summary_by_case[case_id],
                background_index=background_index,
                foreground_index=foreground_index,
                lite_budget=args.lite_budget,
            )
        )

    elapsed_seconds = time.perf_counter() - started
    write_csv(output_csv, comparison_rows)
    write_log(
        log_path,
        comparison_rows,
        elapsed_seconds,
        full_elapsed_seconds=parse_elapsed_seconds(Path(args.full_log)),
        lite_budget=args.lite_budget,
    )

    print(f"cases={len(comparison_rows)}")
    print(f"lite_candidate_rows={sum(int(row['lite_candidate_count']) for row in comparison_rows)}")
    print(f"elapsed_seconds={elapsed_seconds:.1f}")
    print(f"output_csv={output_csv}")
    print(f"log_path={log_path}")


def compare_case(
    *,
    case: dict[str, str],
    full_rows: list[dict[str, str]],
    full_summary: dict[str, str],
    background_index: dict[str, Path],
    foreground_index: dict[str, Path],
    lite_budget: int,
) -> dict[str, object]:
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
        scorer_mode="simopa-lite",
    )
    lite_candidates = [annotation_candidate]
    for prior in prior_candidates[:lite_budget]:
        lite_candidates.append(
            {
                **prior,
                "rank": len(lite_candidates) + 1,
                "candidate_source": "prior_pool",
                "candidate_id": f"prior_{prior['rank']:02d}",
            }
        )

    case_started = time.perf_counter()
    lite_results = score_candidate_boxes(
        background_bytes=background_bytes,
        foreground_bytes=foreground_bytes,
        mask_bytes=foreground_mask_bytes,
        candidates=lite_candidates,
        mode="simopa-lite",
    )
    lite_case_elapsed_ms = round((time.perf_counter() - case_started) * 1000.0, 2)

    scored_lite = list(zip(lite_candidates, lite_results))
    scored_lite.sort(key=lambda item: item[1].score, reverse=True)

    full_sorted = sorted(full_rows, key=lambda row: int(row["model_rank"]))
    full_top3 = full_sorted[:3]
    lite_top3 = scored_lite[:3]
    lite_dataset_rank, lite_dataset_score = dataset_position_rank(scored_lite)

    full_top3_ids = [row["candidate_id"] for row in full_top3]
    lite_top3_ids = [candidate["candidate_id"] for candidate, _ in lite_top3]
    overlap_count = len(set(full_top3_ids) & set(lite_top3_ids))
    lite_assessment = expected_case_result(case["label"], lite_dataset_score, lite_dataset_rank)

    return {
        "case_id": case["case_id"],
        "dataset_label": case["label"],
        "fg_id": fg_id,
        "bg_id": bg_id,
        "foreground_category": foreground_path.parent.name,
        "background_category": background_path.parent.name,
        "full_mode": "simopa-full",
        "lite_mode": "simopa-lite",
        "full_candidate_count": len(full_rows),
        "lite_candidate_budget": lite_budget,
        "lite_candidate_count": len(lite_candidates),
        "score_call_reduction_pct": round(
            (1.0 - len(lite_candidates) / max(1, len(full_rows))) * 100.0,
            2,
        ),
        "full_top1_id": full_top3[0]["candidate_id"],
        "lite_top1_id": lite_top3[0][0]["candidate_id"],
        "top1_matches": "yes" if full_top3[0]["candidate_id"] == lite_top3[0][0]["candidate_id"] else "no",
        "full_top1_score": full_top3[0]["score"],
        "lite_top1_score": round(lite_top3[0][1].score, 4),
        "full_top3_ids": ";".join(full_top3_ids),
        "lite_top3_ids": ";".join(lite_top3_ids),
        "top3_overlap_count": overlap_count,
        "top3_overlap_ratio": round(overlap_count / 3.0, 4),
        "full_dataset_position_rank": full_summary["dataset_position_rank"],
        "lite_dataset_position_rank": lite_dataset_rank,
        "full_dataset_position_score": full_summary["dataset_position_score"],
        "lite_dataset_position_score": round(lite_dataset_score, 4),
        "full_assessment": full_summary["assessment"],
        "lite_assessment": lite_assessment,
        "assessment_matches": "yes" if full_summary["assessment"] == lite_assessment else "no",
        "full_inner_runtime_ms": round(sum(float_value(row.get("runtime_ms")) for row in full_rows), 2),
        "lite_inner_runtime_ms": round(sum(result.runtime_ms for result in lite_results), 2),
        "lite_case_elapsed_ms": lite_case_elapsed_ms,
        "full_model_version": full_top3[0]["model_version"],
        "lite_model_version": lite_top3[0][1].model_version,
    }


def dataset_position_rank(scored: list[tuple[dict, object]]) -> tuple[int, float]:
    for rank, (candidate, result) in enumerate(scored, start=1):
        if candidate["candidate_id"] == "opa_position":
            return rank, float(result.score)
    return 0, 0.0


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def group_rows(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


def parse_elapsed_seconds(path: Path) -> float:
    if not path.is_file():
        return 0.0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("elapsed_seconds="):
            return float_value(line.split("=", 1)[1])
    return 0.0


def write_log(
    path: Path,
    rows: list[dict[str, object]],
    lite_elapsed_seconds: float,
    *,
    full_elapsed_seconds: float,
    lite_budget: int,
) -> None:
    full_score_calls = sum(int(row["full_candidate_count"]) for row in rows)
    lite_score_calls = sum(int(row["lite_candidate_count"]) for row in rows)
    top1_matches = sum(1 for row in rows if row["top1_matches"] == "yes")
    assessment_matches = sum(1 for row in rows if row["assessment_matches"] == "yes")
    mean_top3_overlap = sum(float(row["top3_overlap_ratio"]) for row in rows) / max(1, len(rows))
    speedup = full_elapsed_seconds / lite_elapsed_seconds if full_elapsed_seconds and lite_elapsed_seconds else 0.0
    reduction = (1.0 - lite_score_calls / max(1, full_score_calls)) * 100.0

    with path.open("w", encoding="utf-8") as handle:
        handle.write("SmartPlace SimOPA full-vs-lite comparison\n")
        handle.write("model_version=simopa-lite-candidate-budget-v1\n")
        handle.write(f"cases={len(rows)}\n")
        handle.write(f"lite_budget={lite_budget}\n")
        handle.write(f"full_score_calls={full_score_calls}\n")
        handle.write(f"lite_score_calls={lite_score_calls}\n")
        handle.write(f"score_call_reduction_pct={reduction:.2f}\n")
        handle.write(f"full_elapsed_seconds={full_elapsed_seconds:.1f}\n")
        handle.write(f"lite_elapsed_seconds={lite_elapsed_seconds:.1f}\n")
        handle.write(f"speedup_factor={speedup:.3f}\n")
        handle.write(f"top1_matches={top1_matches}\n")
        handle.write(f"top1_match_rate={top1_matches / max(1, len(rows)):.4f}\n")
        handle.write(f"mean_top3_overlap_ratio={mean_top3_overlap:.4f}\n")
        handle.write(f"assessment_matches={assessment_matches}\n")
        handle.write(f"assessment_match_rate={assessment_matches / max(1, len(rows)):.4f}\n")
        for row in rows:
            handle.write(
                f"case {row['case_id']} "
                f"top1_match={row['top1_matches']} "
                f"top3_overlap={row['top3_overlap_count']} "
                f"lite_assessment={row['lite_assessment']} "
                f"lite_elapsed_ms={row['lite_case_elapsed_ms']}\n"
            )


def float_value(value: object, fallback: float = 0.0) -> float:
    if value is None or value == "":
        return fallback
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


if __name__ == "__main__":
    main()
