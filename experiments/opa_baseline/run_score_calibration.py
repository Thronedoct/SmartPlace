from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import mean


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_RANKING_CSV = ROOT_DIR / "report" / "tables" / "candidate_ranking_v1.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "score_calibration_v1.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "score_calibration_v1.txt"
CALIBRATION_TEMPERATURE = 2.5
SCORE_EPSILON = 1e-3
IOU_THRESHOLD = 0.75
HIGH_SATURATION_THRESHOLD = 0.995
LOW_SATURATION_THRESHOLD = 0.005


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate SimOPA scores and apply candidate IoU dedup.")
    parser.add_argument("--ranking-csv", default=str(DEFAULT_RANKING_CSV))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--temperature", type=float, default=CALIBRATION_TEMPERATURE)
    parser.add_argument("--iou-threshold", type=float, default=IOU_THRESHOLD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ranking_csv = Path(args.ranking_csv)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)

    require_existing_file(ranking_csv, "candidate ranking CSV")
    if args.temperature <= 0:
        raise ValueError(f"Temperature must be positive, got {args.temperature}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    rows = read_rows(ranking_csv)
    apply_calibration(rows, args.temperature)
    apply_case_ranks(rows, score_key="calibrated_score", rank_key="calibrated_rank")
    apply_iou_dedup(rows, args.iou_threshold)
    write_csv(output_csv, rows)
    write_log(log_path, rows, args.temperature, args.iou_threshold)

    print(f"rows={len(rows)}")
    print(f"output_csv={output_csv}")
    print(f"log_path={log_path}")


def read_rows(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        source_rows = list(csv.DictReader(handle))

    rows: list[dict[str, object]] = []
    for row in source_rows:
        score = float(row["score"])
        row["raw_score"] = score
        row["raw_rank"] = int(row["model_rank"])
        row["raw_top3"] = row["is_top3"]
        row["x"] = float(row["x"])
        row["y"] = float(row["y"])
        row["w"] = float(row["w"])
        row["h"] = float(row["h"])
        rows.append(row)
    return rows


def apply_calibration(rows: list[dict[str, object]], temperature: float) -> None:
    for row in rows:
        raw_score = float(row["raw_score"])
        clipped = min(1.0 - SCORE_EPSILON, max(SCORE_EPSILON, raw_score))
        calibrated = sigmoid(logit(clipped) / temperature)
        row["calibrated_score"] = round(calibrated, 4)
        row["calibrated_tier"] = score_to_tier(calibrated)
        row["saturation_flag"] = saturation_flag(raw_score)


def apply_case_ranks(rows: list[dict[str, object]], *, score_key: str, rank_key: str) -> None:
    for case_rows in group_by_case(rows).values():
        sorted_rows = sorted(
            case_rows,
            key=lambda row: (-float(row[score_key]), int(row["raw_rank"])),
        )
        for rank, row in enumerate(sorted_rows, start=1):
            row[rank_key] = rank
            row[f"{rank_key}_top3"] = "yes" if rank <= 3 else "no"


def apply_iou_dedup(rows: list[dict[str, object]], iou_threshold: float) -> None:
    for case_rows in group_by_case(rows).values():
        sorted_rows = sorted(
            case_rows,
            key=lambda row: (-float(row["calibrated_score"]), int(row["raw_rank"])),
        )
        kept: list[dict[str, object]] = []
        for row in sorted_rows:
            duplicate = first_duplicate(row, kept, iou_threshold)
            if duplicate is None:
                kept.append(row)
                row["dedup_keep"] = "yes"
                row["dedup_removed_by"] = ""
                row["dedup_iou"] = 0.0
            else:
                row["dedup_keep"] = "no"
                row["dedup_removed_by"] = duplicate["candidate_id"]
                row["dedup_iou"] = round(box_iou(row, duplicate), 4)

        for rank, row in enumerate(kept, start=1):
            row["dedup_rank"] = rank
            row["dedup_top3"] = "yes" if rank <= 3 else "no"

        for row in case_rows:
            if row.get("dedup_keep") != "yes":
                row["dedup_rank"] = ""
                row["dedup_top3"] = "no"


def first_duplicate(
    row: dict[str, object],
    kept: list[dict[str, object]],
    iou_threshold: float,
) -> dict[str, object] | None:
    for kept_row in kept:
        if box_iou(row, kept_row) >= iou_threshold:
            return kept_row
    return None


def box_iou(a: dict[str, object], b: dict[str, object]) -> float:
    ax1, ay1, ax2, ay2 = box_edges(a)
    bx1, by1, bx2, by2 = box_edges(b)
    inter_width = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_height = max(0.0, min(ay2, by2) - max(ay1, by1))
    intersection = inter_width * inter_height
    if intersection <= 0.0:
        return 0.0

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0.0 else 0.0


def box_edges(row: dict[str, object]) -> tuple[float, float, float, float]:
    x = float(row["x"])
    y = float(row["y"])
    w = float(row["w"])
    h = float(row["h"])
    return x, y, x + w, y + h


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "case_id",
        "dataset_label",
        "fg_id",
        "bg_id",
        "candidate_source",
        "candidate_id",
        "x",
        "y",
        "w",
        "h",
        "raw_score",
        "raw_rank",
        "raw_top3",
        "calibrated_score",
        "calibrated_tier",
        "calibrated_rank",
        "calibrated_rank_top3",
        "saturation_flag",
        "dedup_keep",
        "dedup_rank",
        "dedup_top3",
        "dedup_removed_by",
        "dedup_iou",
        "model_version",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_log(
    path: Path,
    rows: list[dict[str, object]],
    temperature: float,
    iou_threshold: float,
) -> None:
    case_groups = group_by_case(rows)
    saturated_high = [row for row in rows if row["saturation_flag"] == "high_saturated"]
    saturated_low = [row for row in rows if row["saturation_flag"] == "low_saturated"]
    removed = [row for row in rows if row["dedup_keep"] == "no"]
    raw_dup_cases = [
        case_id
        for case_id, case_rows in case_groups.items()
        if top3_max_iou(case_rows, "raw_rank") >= iou_threshold
    ]
    dedup_dup_cases = [
        case_id
        for case_id, case_rows in case_groups.items()
        if dedup_top3_max_iou(case_rows) >= iou_threshold
    ]
    dataset_rows = [row for row in rows if row["candidate_source"] == "opa_position"]
    positive_dataset_rows = [row for row in dataset_rows if row["dataset_label"] == "1"]
    negative_dataset_rows = [row for row in dataset_rows if row["dataset_label"] == "0"]
    case_002 = next((row for row in dataset_rows if row["case_id"] == "opa_test_002"), None)

    lines = [
        "SmartPlace score calibration v1",
        "method=temperature-scaling-plus-iou-dedup",
        f"temperature={temperature}",
        f"score_epsilon={SCORE_EPSILON}",
        f"high_saturation_threshold={HIGH_SATURATION_THRESHOLD}",
        f"low_saturation_threshold={LOW_SATURATION_THRESHOLD}",
        f"iou_threshold={iou_threshold}",
        f"candidate_rows={len(rows)}",
        f"cases={len(case_groups)}",
        f"high_saturated_rows={len(saturated_high)}",
        f"low_saturated_rows={len(saturated_low)}",
        f"dedup_removed_rows={len(removed)}",
        f"raw_top3_duplicate_cases={len(raw_dup_cases)}",
        f"dedup_top3_duplicate_cases={len(dedup_dup_cases)}",
        f"positive_dataset_mean_calibrated={mean_score(positive_dataset_rows):.4f}",
        f"negative_dataset_mean_calibrated={mean_score(negative_dataset_rows):.4f}",
    ]
    if case_002 is not None:
        lines.append(
            "opa_test_002 "
            f"raw_score={case_002['raw_score']} "
            f"calibrated_score={case_002['calibrated_score']} "
            f"raw_rank={case_002['raw_rank']} "
            f"calibrated_rank={case_002['calibrated_rank']} "
            f"dedup_rank={case_002['dedup_rank'] or 'removed'} "
            f"saturation={case_002['saturation_flag']}"
        )

    for case_id, case_rows in sorted(case_groups.items()):
        removed_in_case = [row for row in case_rows if row["dedup_keep"] == "no"]
        if removed_in_case or case_id == "opa_test_002":
            dataset_row = next(
                (row for row in case_rows if row["candidate_source"] == "opa_position"),
                None,
            )
            lines.append(
                "case "
                f"{case_id} "
                f"label={dataset_row['dataset_label'] if dataset_row else 'unknown'} "
                f"dataset_raw_rank={dataset_row['raw_rank'] if dataset_row else 'missing'} "
                f"dataset_calibrated_rank={dataset_row['calibrated_rank'] if dataset_row else 'missing'} "
                f"dataset_dedup_rank={dataset_row['dedup_rank'] if dataset_row and dataset_row['dedup_rank'] else 'removed'} "
                f"removed={len(removed_in_case)} "
                f"raw_top3_max_iou={top3_max_iou(case_rows, 'raw_rank'):.4f} "
                f"dedup_top3_max_iou={dedup_top3_max_iou(case_rows):.4f}"
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def top3_max_iou(rows: list[dict[str, object]], rank_key: str) -> float:
    top_rows = [row for row in rows if row.get(rank_key) and int(row[rank_key]) <= 3]
    return max_pairwise_iou(top_rows)


def dedup_top3_max_iou(rows: list[dict[str, object]]) -> float:
    top_rows = [
        row
        for row in rows
        if row.get("dedup_keep") == "yes" and row.get("dedup_rank") and int(row["dedup_rank"]) <= 3
    ]
    return max_pairwise_iou(top_rows)


def max_pairwise_iou(rows: list[dict[str, object]]) -> float:
    max_iou = 0.0
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            max_iou = max(max_iou, box_iou(left, right))
    return max_iou


def mean_score(rows: list[dict[str, object]]) -> float:
    return mean(float(row["calibrated_score"]) for row in rows) if rows else 0.0


def group_by_case(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["case_id"]), []).append(row)
    return grouped


def logit(value: float) -> float:
    return math.log(value / (1.0 - value))


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def score_to_tier(score: float) -> str:
    if score >= 0.7:
        return "recommended"
    if score >= 0.4:
        return "acceptable"
    return "rejected"


def saturation_flag(score: float) -> str:
    if score >= HIGH_SATURATION_THRESHOLD:
        return "high_saturated"
    if score <= LOW_SATURATION_THRESHOLD:
        return "low_saturated"
    return "continuous"


def require_existing_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


if __name__ == "__main__":
    main()
