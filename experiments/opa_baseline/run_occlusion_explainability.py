from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_PACKAGES = ROOT_DIR / ".model-packages"
OPA_REPO = ROOT_DIR / "external" / "Object-Placement-Assessment-Dataset-OPA"
DEFAULT_WEIGHT = OPA_REPO / "eval_opascore" / "checkpoints" / "simopa.pth"
DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_FAILURE_CSV = ROOT_DIR / "report" / "tables" / "failure_cases.csv"
DEFAULT_CALIBRATION_CSV = ROOT_DIR / "report" / "tables" / "score_calibration_v1.csv"
DEFAULT_SUMMARY_CSV = ROOT_DIR / "report" / "tables" / "opa_18_case_summary.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "occlusion_explainability_v1.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "occlusion_explainability_v1.txt"
DEFAULT_SCREENSHOT_DIR = ROOT_DIR / "report" / "screenshots" / "explainability"
MODEL_VERSION = "simopa-occlusion-v1"

for path in (LOCAL_PACKAGES, OPA_REPO, OPA_REPO / "eval_opascore"):
    sys.path.insert(0, str(path))

import torch  # noqa: E402
from PIL import Image, ImageDraw, ImageFont, ImageStat  # noqa: E402
from simopa import ObjectPlacementAssessmentModel  # noqa: E402

from score_candidates import compose_candidate, preprocess_pil_pair, resolve_device  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SimOPA occlusion sensitivity evidence.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--failure-csv", default=str(DEFAULT_FAILURE_CSV))
    parser.add_argument("--calibration-csv", default=str(DEFAULT_CALIBRATION_CSV))
    parser.add_argument("--summary-csv", default=str(DEFAULT_SUMMARY_CSV))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--screenshot-dir", default=str(DEFAULT_SCREENSHOT_DIR))
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT))
    parser.add_argument("--device", default="auto")
    parser.add_argument("--grid-size", type=int, default=6)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    failure_rows = read_rows(Path(args.failure_csv))
    calibration_rows = group_rows(Path(args.calibration_csv))
    summary_rows = keyed_rows(Path(args.summary_csv))
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)
    screenshot_dir = Path(args.screenshot_dir)

    require_existing_dir(dataset_root, "dataset root")
    require_existing_file(Path(args.weight), "SimOPA weight")
    if args.grid_size < 2:
        raise ValueError(f"grid-size must be >= 2, got {args.grid_size}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)
    model = ObjectPlacementAssessmentModel(device, opt)
    model.model.eval()

    started = time.perf_counter()
    output_rows: list[dict[str, object]] = []
    for index, failure_row in enumerate(failure_rows, start=1):
        case_id = failure_row["case_id"]
        print(f"[{index:02d}/{len(failure_rows):02d}] explaining {case_id}")
        row = explain_case(
            case_id=case_id,
            case_type=failure_row["case_type"],
            dataset_root=dataset_root,
            calibration_rows=calibration_rows[case_id],
            summary_row=summary_rows[case_id],
            model=model,
            device=device,
            grid_size=args.grid_size,
            screenshot_dir=screenshot_dir,
        )
        output_rows.append(row)

    write_csv(output_csv, output_rows)
    write_log(log_path, output_rows, device, args.grid_size, time.perf_counter() - started)
    print(f"cases={len(output_rows)}")
    print(f"output_csv={output_csv}")
    print(f"log_path={log_path}")
    print(f"screenshot_dir={screenshot_dir}")


def explain_case(
    *,
    case_id: str,
    case_type: str,
    dataset_root: Path,
    calibration_rows: list[dict[str, str]],
    summary_row: dict[str, str],
    model: ObjectPlacementAssessmentModel,
    device: torch.device,
    grid_size: int,
    screenshot_dir: Path,
) -> dict[str, object]:
    candidate_row, candidate_note = select_explanation_candidate(case_type, calibration_rows)
    background, foreground, foreground_mask = load_case_images(dataset_root, summary_row)
    candidate = {
        "x": float(candidate_row["x"]),
        "y": float(candidate_row["y"]),
        "w": float(candidate_row["w"]),
        "h": float(candidate_row["h"]),
    }
    composite, composite_mask = compose_candidate(background, foreground, foreground_mask, candidate)
    baseline_score = score_pair(model, composite, composite_mask, device)
    fill_color = tuple(round(value) for value in ImageStat.Stat(composite).mean)

    cells: list[dict[str, object]] = []
    for row_index in range(grid_size):
        for col_index in range(grid_size):
            box = grid_cell_box(composite.size, grid_size, row_index, col_index)
            occluded = composite.copy()
            ImageDraw.Draw(occluded).rectangle(box, fill=fill_color)
            occluded_score = score_pair(model, occluded, composite_mask, device)
            drop = baseline_score - occluded_score
            cells.append(
                {
                    "grid_row": row_index,
                    "grid_col": col_index,
                    "box": box,
                    "occluded_score": occluded_score,
                    "score_drop": drop,
                    "abs_drop": abs(drop),
                    "candidate_iou": box_iou_pixels(box, candidate_pixel_box(composite.size, candidate)),
                }
            )

    strongest_drop = max(cells, key=lambda cell: float(cell["score_drop"]))
    strongest_abs = max(cells, key=lambda cell: float(cell["abs_drop"]))
    foreground_cells = [cell for cell in cells if float(cell["candidate_iou"]) > 0.0]
    background_cells = [cell for cell in cells if float(cell["candidate_iou"]) == 0.0]
    heatmap_path = screenshot_dir / f"{case_id}_occlusion_heatmap.png"
    render_heatmap(
        case_id=case_id,
        case_type=case_type,
        composite=composite,
        candidate=candidate,
        cells=cells,
        output_path=heatmap_path,
        baseline_score=baseline_score,
        candidate_note=candidate_note,
    )

    return {
        "case_id": case_id,
        "case_type": case_type,
        "dataset_label": summary_row["dataset_label"],
        "candidate_source": candidate_row["candidate_source"],
        "candidate_id": candidate_row["candidate_id"],
        "candidate_note": candidate_note,
        "baseline_score": round(baseline_score, 4),
        "raw_score": candidate_row["raw_score"],
        "calibrated_score": candidate_row["calibrated_score"],
        "grid_size": grid_size,
        "max_score_drop": round(float(strongest_drop["score_drop"]), 4),
        "max_drop_cell": f"r{strongest_drop['grid_row']}c{strongest_drop['grid_col']}",
        "max_abs_drop": round(float(strongest_abs["abs_drop"]), 4),
        "mean_abs_drop": round(mean(float(cell["abs_drop"]) for cell in cells), 4),
        "foreground_mean_abs_drop": round(mean(float(cell["abs_drop"]) for cell in foreground_cells), 4),
        "background_mean_abs_drop": round(mean(float(cell["abs_drop"]) for cell in background_cells), 4),
        "heatmap_path": project_path(heatmap_path),
        "model_version": MODEL_VERSION,
    }


def select_explanation_candidate(
    case_type: str,
    calibration_rows: list[dict[str, str]],
) -> tuple[dict[str, str], str]:
    if case_type == "negative_false_positive_risk":
        return min(calibration_rows, key=lambda row: int(row["raw_rank"])), "raw_top1_false_positive_risk"
    if case_type == "clear_negative_rejection":
        return require_candidate(calibration_rows, "opa_position"), "opa_rejected_position"
    return require_candidate(calibration_rows, "opa_position"), "opa_labeled_position"


def require_candidate(rows: list[dict[str, str]], candidate_id: str) -> dict[str, str]:
    for row in rows:
        if row["candidate_id"] == candidate_id:
            return row
    raise KeyError(f"Missing candidate: {candidate_id}")


def load_case_images(
    dataset_root: Path,
    summary_row: dict[str, str],
) -> tuple[Image.Image, Image.Image, Image.Image]:
    background_path = (
        dataset_root
        / "background"
        / summary_row["background_category"]
        / f"{summary_row['bg_id']}.jpg"
    )
    foreground_path = (
        dataset_root
        / "foreground"
        / summary_row["foreground_category"]
        / f"{summary_row['fg_id']}.jpg"
    )
    mask_path = (
        dataset_root
        / "foreground"
        / summary_row["foreground_category"]
        / f"mask_{summary_row['fg_id']}.jpg"
    )
    with Image.open(background_path) as image:
        background = image.convert("RGB").copy()
    with Image.open(foreground_path) as image:
        foreground = image.convert("RGB").copy()
    with Image.open(mask_path) as image:
        foreground_mask = image.convert("L").copy()
    return background, foreground, foreground_mask


def score_pair(
    model: ObjectPlacementAssessmentModel,
    composite: Image.Image,
    mask: Image.Image,
    device: torch.device,
) -> float:
    with torch.no_grad():
        inputs = preprocess_pil_pair(composite, mask, model.image_size, device)
        logits = model.model(inputs)
        return float(torch.softmax(logits, dim=-1)[0, 1].cpu().item())


def grid_cell_box(
    size: tuple[int, int],
    grid_size: int,
    row_index: int,
    col_index: int,
) -> tuple[int, int, int, int]:
    width, height = size
    left = round(col_index * width / grid_size)
    top = round(row_index * height / grid_size)
    right = round((col_index + 1) * width / grid_size)
    bottom = round((row_index + 1) * height / grid_size)
    return left, top, right, bottom


def candidate_pixel_box(size: tuple[int, int], candidate: dict[str, float]) -> tuple[int, int, int, int]:
    width, height = size
    left = round(candidate["x"] * width)
    top = round(candidate["y"] * height)
    right = round((candidate["x"] + candidate["w"]) * width)
    bottom = round((candidate["y"] + candidate["h"]) * height)
    return left, top, right, bottom


def render_heatmap(
    *,
    case_id: str,
    case_type: str,
    composite: Image.Image,
    candidate: dict[str, float],
    cells: list[dict[str, object]],
    output_path: Path,
    baseline_score: float,
    candidate_note: str,
) -> None:
    base = composite.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    max_positive_drop = max(0.0, *(max(0.0, float(cell["score_drop"])) for cell in cells))
    for cell in cells:
        drop = max(0.0, float(cell["score_drop"]))
        alpha = 0 if max_positive_drop == 0.0 else round(175 * drop / max_positive_drop)
        if alpha > 0:
            draw.rectangle(cell["box"], fill=(230, 42, 42, alpha))

    combined = Image.alpha_composite(base, overlay).convert("RGB")
    draw_rgb = ImageDraw.Draw(combined)
    draw_candidate_box(draw_rgb, combined.size, candidate)
    panel = add_title(
        combined,
        f"{case_id} | {case_type} | {candidate_note} | baseline={baseline_score:.4f}",
    )
    panel.save(output_path)


def draw_candidate_box(draw: ImageDraw.ImageDraw, size: tuple[int, int], candidate: dict[str, float]) -> None:
    box = candidate_pixel_box(size, candidate)
    draw.rectangle(box, outline="#00cec9", width=4)


def add_title(image: Image.Image, title: str) -> Image.Image:
    font = ImageFont.load_default()
    title_height = 28
    canvas = Image.new("RGB", (image.width, image.height + title_height), "white")
    canvas.paste(image, (0, title_height))
    ImageDraw.Draw(canvas).text((8, 8), title, fill="black", font=font)
    return canvas


def box_iou_pixels(
    a: tuple[int, int, int, int],
    b: tuple[int, int, int, int],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_width = max(0, min(ax2, bx2) - max(ax1, bx1))
    inter_height = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = inter_width * inter_height
    if intersection <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = area_a + area_b - intersection
    return intersection / union if union > 0 else 0.0


def read_rows(path: Path) -> list[dict[str, str]]:
    require_existing_file(path, "CSV")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def keyed_rows(path: Path) -> dict[str, dict[str, str]]:
    return {row["case_id"]: row for row in read_rows(path)}


def group_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in read_rows(path):
        grouped.setdefault(row["case_id"], []).append(row)
    return grouped


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_log(
    path: Path,
    rows: list[dict[str, object]],
    device: torch.device,
    grid_size: int,
    elapsed_seconds: float,
) -> None:
    lines = [
        "SmartPlace occlusion explainability v1",
        f"model_version={MODEL_VERSION}",
        f"device={device}",
        f"grid_size={grid_size}",
        f"cases={len(rows)}",
        f"elapsed_seconds={elapsed_seconds:.1f}",
        f"mean_max_score_drop={mean(float(row['max_score_drop']) for row in rows):.4f}",
        f"mean_abs_drop={mean(float(row['mean_abs_drop']) for row in rows):.4f}",
    ]
    for row in rows:
        lines.append(
            "case "
            f"{row['case_id']} "
            f"type={row['case_type']} "
            f"candidate={row['candidate_id']} "
            f"baseline={row['baseline_score']} "
            f"max_drop={row['max_score_drop']} "
            f"max_cell={row['max_drop_cell']} "
            f"fg_mean_abs={row['foreground_mean_abs_drop']} "
            f"bg_mean_abs={row['background_mean_abs_drop']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mean(values: object) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


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
