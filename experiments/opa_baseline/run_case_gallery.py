from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_REPORT_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "report_18.csv"
DEFAULT_RANKING_CSV = ROOT_DIR / "report" / "tables" / "candidate_ranking_v1.csv"
DEFAULT_CALIBRATION_CSV = ROOT_DIR / "report" / "tables" / "score_calibration_v1.csv"
DEFAULT_SUMMARY_CSV = ROOT_DIR / "report" / "tables" / "opa_18_case_summary.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "failure_cases.csv"
DEFAULT_SCREENSHOT_DIR = ROOT_DIR / "report" / "screenshots" / "cases"

SELECTED_CASES = {
    "opa_test_001": (
        "success_with_duplicate_cleanup",
        "Positive case: OPA label is rank 1 and IoU dedup removes near-duplicate Top 3 boxes.",
    ),
    "opa_test_002": (
        "score_saturation_boundary",
        "Positive boundary case: OPA label is high-score but rank 10 because many candidates saturate near 1.0.",
    ),
    "opa_test_006": (
        "dedup_success",
        "Positive case: raw Top 3 contains overlapping candidates; dedup keeps diverse placements.",
    ),
    "opa_test_052": (
        "negative_false_positive_risk",
        "Negative case: OPA bad placement is rejected, but one generated prior scores high and needs human review.",
    ),
    "opa_test_059": (
        "clear_negative_rejection",
        "Negative case: OPA bad placement and generated candidates are all rejected.",
    ),
}

PANEL_WIDTH = 360
PANEL_GAP = 18
TITLE_HEIGHT = 54
BOX_COLORS = ["#00b894", "#fdcb6e", "#0984e3"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build representative case panels and failure table.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--report-csv", default=str(DEFAULT_REPORT_CSV))
    parser.add_argument("--ranking-csv", default=str(DEFAULT_RANKING_CSV))
    parser.add_argument("--calibration-csv", default=str(DEFAULT_CALIBRATION_CSV))
    parser.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--screenshot-dir", default=str(DEFAULT_SCREENSHOT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    report_rows = keyed_rows(Path(args.report_csv))
    ranking_rows = group_rows(Path(args.ranking_csv))
    calibration_rows = group_rows(Path(args.calibration_csv))
    summary_rows = keyed_rows(Path(args.summary_csv))
    output_csv = Path(args.output_csv)
    screenshot_dir = Path(args.screenshot_dir)

    require_existing_dir(dataset_root, "dataset root")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    output_rows: list[dict[str, object]] = []
    for case_id, (case_type, note) in SELECTED_CASES.items():
        require_case(case_id, report_rows, ranking_rows, calibration_rows, summary_rows)
        panel_path = screenshot_dir / f"{case_id}_case_panel.png"
        build_case_panel(
            case_id=case_id,
            dataset_root=dataset_root,
            report_row=report_rows[case_id],
            ranking_rows=ranking_rows[case_id],
            calibration_rows=calibration_rows[case_id],
            summary_row=summary_rows[case_id],
            output_path=panel_path,
            case_type=case_type,
        )
        output_rows.append(
            build_output_row(
                case_id=case_id,
                case_type=case_type,
                note=note,
                summary_row=summary_rows[case_id],
                calibration_rows=calibration_rows[case_id],
                panel_path=panel_path,
            )
        )

    write_csv(output_csv, output_rows)
    print(f"cases={len(output_rows)}")
    print(f"output_csv={output_csv}")
    print(f"screenshot_dir={screenshot_dir}")


def keyed_rows(path: Path) -> dict[str, dict[str, str]]:
    require_existing_file(path, "CSV")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["case_id"]: row for row in csv.DictReader(handle)}


def group_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    require_existing_file(path, "CSV")
    grouped: dict[str, list[dict[str, str]]] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            grouped.setdefault(row["case_id"], []).append(row)
    return grouped


def require_case(
    case_id: str,
    report_rows: dict[str, dict[str, str]],
    ranking_rows: dict[str, list[dict[str, str]]],
    calibration_rows: dict[str, list[dict[str, str]]],
    summary_rows: dict[str, dict[str, str]],
) -> None:
    missing = []
    for label, rows in (
        ("report", report_rows),
        ("ranking", ranking_rows),
        ("calibration", calibration_rows),
        ("summary", summary_rows),
    ):
        if case_id not in rows:
            missing.append(label)
    if missing:
        raise KeyError(f"Missing {case_id} in: {', '.join(missing)}")


def build_case_panel(
    *,
    case_id: str,
    dataset_root: Path,
    report_row: dict[str, str],
    ranking_rows: list[dict[str, str]],
    calibration_rows: list[dict[str, str]],
    summary_row: dict[str, str],
    output_path: Path,
    case_type: str,
) -> None:
    with Image.open(ROOT_DIR / report_row["composite_path"]) as image:
        composite = image.convert("RGB").copy()
    with Image.open(
        dataset_root
        / "background"
        / summary_row["background_category"]
        / f"{summary_row['bg_id']}.jpg"
    ) as image:
        background = image.convert("RGB").copy()

    raw_top3 = sorted(
        [row for row in ranking_rows if int(row["model_rank"]) <= 3],
        key=lambda row: int(row["model_rank"]),
    )
    dedup_top3 = sorted(
        [row for row in calibration_rows if row["dedup_top3"] == "yes"],
        key=lambda row: int(row["dedup_rank"]),
    )

    panels = [
        render_image_panel(composite, "OPA composite"),
        render_box_panel(background, raw_top3, "Raw SimOPA Top 3", rank_key="model_rank", score_key="score"),
        render_box_panel(
            background,
            dedup_top3,
            "Calibrated + dedup Top 3",
            rank_key="dedup_rank",
            score_key="calibrated_score",
        ),
    ]
    title = (
        f"{case_id} | {case_type} | label={summary_row['dataset_label']} | "
        f"dataset rank={summary_row['dataset_position_rank']} score={summary_row['dataset_position_score']}"
    )
    combined = compose_panel_grid(panels, title)
    combined.save(output_path)


def render_image_panel(image: Image.Image, title: str) -> Image.Image:
    resized = resize_to_panel(image)
    return add_panel_title(resized, title)


def render_box_panel(
    image: Image.Image,
    rows: list[dict[str, str]],
    title: str,
    *,
    rank_key: str,
    score_key: str,
) -> Image.Image:
    resized = resize_to_panel(image)
    scale_x = resized.width / image.width
    scale_y = resized.height / image.height
    draw = ImageDraw.Draw(resized)
    font = ImageFont.load_default()
    for index, row in enumerate(rows[:3]):
        color = BOX_COLORS[index % len(BOX_COLORS)]
        x = float(row["x"]) * image.width * scale_x
        y = float(row["y"]) * image.height * scale_y
        w = float(row["w"]) * image.width * scale_x
        h = float(row["h"]) * image.height * scale_y
        draw.rectangle((x, y, x + w, y + h), outline=color, width=4)
        label = f"#{row[rank_key]} {float(row[score_key]):.3f}"
        draw.rectangle((x, max(0, y - 16), x + 82, max(16, y)), fill=color)
        draw.text((x + 4, max(1, y - 15)), label, fill="black", font=font)
    return add_panel_title(resized, title)


def resize_to_panel(image: Image.Image) -> Image.Image:
    ratio = PANEL_WIDTH / image.width
    height = max(1, round(image.height * ratio))
    return image.resize((PANEL_WIDTH, height), Image.Resampling.LANCZOS)


def add_panel_title(image: Image.Image, title: str) -> Image.Image:
    font = ImageFont.load_default()
    canvas = Image.new("RGB", (image.width, image.height + 24), "white")
    canvas.paste(image, (0, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((8, 7), title, fill="black", font=font)
    return canvas


def compose_panel_grid(panels: list[Image.Image], title: str) -> Image.Image:
    width = sum(panel.width for panel in panels) + PANEL_GAP * (len(panels) - 1)
    height = TITLE_HEIGHT + max(panel.height for panel in panels)
    canvas = Image.new("RGB", (width, height), "#f5f6f8")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((12, 16), title, fill="black", font=font)
    x = 0
    for panel in panels:
        canvas.paste(panel, (x, TITLE_HEIGHT))
        x += panel.width + PANEL_GAP
    return canvas


def build_output_row(
    *,
    case_id: str,
    case_type: str,
    note: str,
    summary_row: dict[str, str],
    calibration_rows: list[dict[str, str]],
    panel_path: Path,
) -> dict[str, object]:
    dataset_row = next(row for row in calibration_rows if row["candidate_source"] == "opa_position")
    removed_count = sum(1 for row in calibration_rows if row["dedup_keep"] == "no")
    return {
        "case_id": case_id,
        "case_type": case_type,
        "dataset_label": summary_row["dataset_label"],
        "fg_id": summary_row["fg_id"],
        "bg_id": summary_row["bg_id"],
        "dataset_position_score": summary_row["dataset_position_score"],
        "raw_dataset_rank": dataset_row["raw_rank"],
        "calibrated_dataset_rank": dataset_row["calibrated_rank"],
        "dedup_dataset_rank": dataset_row["dedup_rank"],
        "dedup_removed_candidates": removed_count,
        "top3_scores": summary_row["top3_scores"],
        "assessment": summary_row["assessment"],
        "note": note,
        "panel_path": project_path(panel_path),
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def project_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def require_existing_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"Missing {label}: {path}")


def require_existing_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


if __name__ == "__main__":
    main()
