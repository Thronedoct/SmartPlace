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
DEFAULT_RANKING_CSV = ROOT_DIR / "report" / "tables" / "candidate_ranking_v1.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "rgb_vs_mask_comparison.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "rgb_vs_mask_comparison.txt"
MODEL_VERSION = "simopa-mask-ablation-v1"

for path in (LOCAL_PACKAGES, OPA_REPO, OPA_REPO / "eval_opascore"):
    sys.path.insert(0, str(path))

import torch  # noqa: E402
from PIL import Image  # noqa: E402
from simopa import ObjectPlacementAssessmentModel  # noqa: E402

from score_candidates import compose_candidate, preprocess_pil_pair  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare RGB+mask, bbox-mask, and blank-mask SimOPA scores.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--ranking-csv", default=str(DEFAULT_RANKING_CSV))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT))
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    ranking_csv = Path(args.ranking_csv)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)

    require_existing_dir(dataset_root, "dataset root")
    require_existing_file(ranking_csv, "candidate ranking CSV")
    require_existing_file(Path(args.weight), "SimOPA weight")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)
    model = ObjectPlacementAssessmentModel(device, opt)
    model.model.eval()

    rows = read_candidate_rows(ranking_csv)
    started = time.perf_counter()
    output_rows = score_rows(rows, dataset_root, model, device)
    write_csv(output_csv, output_rows)
    write_log(log_path, output_rows, device, time.perf_counter() - started)

    print(f"rows={len(output_rows)}")
    print(f"output_csv={output_csv}")
    print(f"log_path={log_path}")


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if requested == "cuda":
        return torch.device("cuda:0")
    return torch.device(requested)


def read_candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def score_rows(
    rows: list[dict[str, str]],
    dataset_root: Path,
    model: ObjectPlacementAssessmentModel,
    device: torch.device,
) -> list[dict[str, object]]:
    image_cache: dict[str, Image.Image] = {}
    scored_rows: list[dict[str, object]] = []

    for index, row in enumerate(rows, start=1):
        if index % 25 == 1:
            print(f"[{index:03d}/{len(rows):03d}] scoring {row['case_id']}")

        background = load_image(
            image_cache,
            dataset_root
            / "background"
            / row["background_category"]
            / f"{row['bg_id']}.jpg",
            "RGB",
        )
        foreground = load_image(
            image_cache,
            dataset_root
            / "foreground"
            / row["foreground_category"]
            / f"{row['fg_id']}.jpg",
            "RGB",
        )
        foreground_mask = load_image(
            image_cache,
            dataset_root
            / "foreground"
            / row["foreground_category"]
            / f"mask_{row['fg_id']}.jpg",
            "L",
        )
        candidate = {
            "x": float(row["x"]),
            "y": float(row["y"]),
            "w": float(row["w"]),
            "h": float(row["h"]),
        }
        composite, shape_mask = compose_candidate(background, foreground, foreground_mask, candidate)
        bbox_mask = build_bbox_mask(background.size, candidate)
        blank_mask = Image.new("L", background.size, 0)

        score_rgb_mask = score_pair(model, composite, shape_mask, device)
        score_bbox_mask = score_pair(model, composite, bbox_mask, device)
        score_blank_mask = score_pair(model, composite, blank_mask, device)

        scored_rows.append(
            {
                "case_id": row["case_id"],
                "dataset_label": row["dataset_label"],
                "fg_id": row["fg_id"],
                "bg_id": row["bg_id"],
                "candidate_source": row["candidate_source"],
                "candidate_id": row["candidate_id"],
                "x": row["x"],
                "y": row["y"],
                "w": row["w"],
                "h": row["h"],
                "score_rgb_mask": round(score_rgb_mask, 4),
                "score_bbox_mask": round(score_bbox_mask, 4),
                "score_blank_mask": round(score_blank_mask, 4),
                "delta_shape_vs_bbox": round(score_rgb_mask - score_bbox_mask, 4),
                "delta_shape_vs_blank": round(score_rgb_mask - score_blank_mask, 4),
                "abs_delta_shape_vs_bbox": round(abs(score_rgb_mask - score_bbox_mask), 4),
                "abs_delta_shape_vs_blank": round(abs(score_rgb_mask - score_blank_mask), 4),
                "model_version": MODEL_VERSION,
            }
        )

    add_mode_ranks(scored_rows, "score_rgb_mask", "rank_rgb_mask")
    add_mode_ranks(scored_rows, "score_bbox_mask", "rank_bbox_mask")
    add_mode_ranks(scored_rows, "score_blank_mask", "rank_blank_mask")
    for row in scored_rows:
        row["top3_rgb_mask"] = "yes" if int(row["rank_rgb_mask"]) <= 3 else "no"
        row["top3_bbox_mask"] = "yes" if int(row["rank_bbox_mask"]) <= 3 else "no"
        row["top3_blank_mask"] = "yes" if int(row["rank_blank_mask"]) <= 3 else "no"
    return scored_rows


def load_image(cache: dict[str, Image.Image], path: Path, mode: str) -> Image.Image:
    key = f"{path}:{mode}"
    if key not in cache:
        require_existing_file(path, "OPA image")
        cache[key] = Image.open(path).convert(mode)
    return cache[key]


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


def build_bbox_mask(size: tuple[int, int], candidate: dict[str, float]) -> Image.Image:
    width, height = size
    box_width = max(1, round(candidate["w"] * width))
    box_height = max(1, round(candidate["h"] * height))
    left = clamp_int(round(candidate["x"] * width), 0, max(0, width - box_width))
    top = clamp_int(round(candidate["y"] * height), 0, max(0, height - box_height))

    mask = Image.new("L", size, 0)
    mask.paste(255, (left, top, left + box_width, top + box_height))
    return mask


def clamp_int(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def add_mode_ranks(rows: list[dict[str, object]], score_key: str, rank_key: str) -> None:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["case_id"]), []).append(row)

    for case_rows in grouped.values():
        sorted_rows = sorted(case_rows, key=lambda row: float(row[score_key]), reverse=True)
        for rank, row in enumerate(sorted_rows, start=1):
            row[rank_key] = rank


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
    elapsed_seconds: float,
) -> None:
    changed_shape = [row for row in rows if float(row["abs_delta_shape_vs_bbox"]) >= 0.05]
    changed_blank = [row for row in rows if float(row["abs_delta_shape_vs_blank"]) >= 0.05]
    top3_changed_bbox = [
        row
        for row in rows
        if row["top3_rgb_mask"] != row["top3_bbox_mask"]
    ]
    top3_changed_blank = [
        row
        for row in rows
        if row["top3_rgb_mask"] != row["top3_blank_mask"]
    ]

    lines = [
        "SmartPlace RGB/mask ablation",
        f"model_version={MODEL_VERSION}",
        f"device={device}",
        f"candidate_rows={len(rows)}",
        f"elapsed_seconds={elapsed_seconds:.1f}",
        f"mean_abs_delta_shape_vs_bbox={mean(float(row['abs_delta_shape_vs_bbox']) for row in rows):.4f}",
        f"mean_abs_delta_shape_vs_blank={mean(float(row['abs_delta_shape_vs_blank']) for row in rows):.4f}",
        f"changed_shape_vs_bbox_ge_0.05={len(changed_shape)}",
        f"changed_shape_vs_blank_ge_0.05={len(changed_blank)}",
        f"top3_membership_changed_bbox={len(top3_changed_bbox)}",
        f"top3_membership_changed_blank={len(top3_changed_blank)}",
    ]
    for row in sorted(rows, key=lambda item: float(item["abs_delta_shape_vs_blank"]), reverse=True)[:8]:
        lines.append(
            "case "
            f"{row['case_id']} "
            f"{row['candidate_id']} "
            f"label={row['dataset_label']} "
            f"rgb_mask={row['score_rgb_mask']} "
            f"bbox={row['score_bbox_mask']} "
            f"blank={row['score_blank_mask']} "
            f"delta_blank={row['delta_shape_vs_blank']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mean(values: object) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


def require_existing_dir(path: Path, label: str) -> None:
    if not path.is_dir():
        raise FileNotFoundError(f"Missing {label}: {path}")


def require_existing_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label}: {path}")


if __name__ == "__main__":
    main()
