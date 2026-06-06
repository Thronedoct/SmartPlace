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
DEFAULT_FAILURE_CSV = ROOT_DIR / "report" / "tables" / "failure_cases.csv"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "robustness_ablation.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "robustness_ablation.txt"
MODEL_VERSION = "simopa-robustness-v1"
SHIFT_DELTA = 0.03
SCALE_DELTA = 0.10
MASK_FILTER_SIZE = 7

for path in (LOCAL_PACKAGES, OPA_REPO, OPA_REPO / "eval_opascore"):
    sys.path.insert(0, str(path))

import torch  # noqa: E402
from PIL import Image, ImageFilter  # noqa: E402
from simopa import ObjectPlacementAssessmentModel  # noqa: E402

from score_candidates import compose_candidate, preprocess_pil_pair  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test SimOPA score robustness under mask, position, and scale perturbations."
    )
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--ranking-csv", default=str(DEFAULT_RANKING_CSV))
    parser.add_argument("--failure-csv", default=str(DEFAULT_FAILURE_CSV))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT))
    parser.add_argument("--device", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    ranking_csv = Path(args.ranking_csv)
    failure_csv = Path(args.failure_csv)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)

    require_existing_dir(dataset_root, "dataset root")
    require_existing_file(ranking_csv, "candidate ranking CSV")
    require_existing_file(failure_csv, "failure cases CSV")
    require_existing_file(Path(args.weight), "SimOPA weight")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)
    model = ObjectPlacementAssessmentModel(device, opt)
    model.model.eval()

    failure_rows = read_rows(failure_csv)
    ranking_rows = read_rows(ranking_csv)
    selected_rows = select_representative_candidates(failure_rows, ranking_rows)

    started = time.perf_counter()
    output_rows = score_perturbations(selected_rows, dataset_root, model, device)
    elapsed_seconds = time.perf_counter() - started
    write_csv(output_csv, output_rows)
    write_log(log_path, output_rows, selected_rows, device, elapsed_seconds)

    print(f"cases={len(selected_rows)}")
    print(f"rows={len(output_rows)}")
    print(f"score_calls={len(output_rows)}")
    print(f"output_csv={output_csv}")
    print(f"log_path={log_path}")


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if requested == "cuda":
        return torch.device("cuda:0")
    return torch.device(requested)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def select_representative_candidates(
    failure_rows: list[dict[str, str]],
    ranking_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    ranking_by_case: dict[str, list[dict[str, str]]] = {}
    for row in ranking_rows:
        ranking_by_case.setdefault(row["case_id"], []).append(row)

    selected: list[dict[str, str]] = []
    for failure in failure_rows:
        case_rows = ranking_by_case.get(failure["case_id"], [])
        if not case_rows:
            raise RuntimeError(f"Missing ranking rows for {failure['case_id']}")

        if failure["case_type"] == "negative_false_positive_risk":
            chosen = min(case_rows, key=lambda row: int(row["model_rank"]))
        else:
            chosen = next(
                (row for row in case_rows if row["candidate_source"] == "opa_position"),
                None,
            )
            if chosen is None:
                raise RuntimeError(f"Missing OPA position for {failure['case_id']}")

        selected.append({**chosen, "case_type": failure["case_type"], "case_note": failure["note"]})
    return selected


def score_perturbations(
    rows: list[dict[str, str]],
    dataset_root: Path,
    model: ObjectPlacementAssessmentModel,
    device: torch.device,
) -> list[dict[str, object]]:
    image_cache: dict[str, Image.Image] = {}
    output_rows: list[dict[str, object]] = []

    for index, row in enumerate(rows, start=1):
        print(f"[{index:02d}/{len(rows):02d}] robustness {row['case_id']} {row['candidate_id']}")
        background = load_image(
            image_cache,
            dataset_root / "background" / row["background_category"] / f"{row['bg_id']}.jpg",
            "RGB",
        )
        foreground = load_image(
            image_cache,
            dataset_root / "foreground" / row["foreground_category"] / f"{row['fg_id']}.jpg",
            "RGB",
        )
        foreground_mask = load_image(
            image_cache,
            dataset_root / "foreground" / row["foreground_category"] / f"mask_{row['fg_id']}.jpg",
            "L",
        )
        base_candidate = candidate_from_row(row)
        base_composite, base_mask = compose_candidate(
            background,
            foreground,
            foreground_mask,
            base_candidate,
        )
        baseline_score = score_pair(model, base_composite, base_mask, device)
        variants = build_variants(base_candidate)

        for variant in variants:
            if variant["group"] == "baseline":
                score = baseline_score
                candidate = base_candidate
            elif variant["group"] == "mask":
                candidate = base_candidate
                score = score_pair(
                    model,
                    base_composite,
                    perturb_mask(base_mask, variant["name"]),
                    device,
                )
            else:
                candidate = variant["candidate"]
                composite, mask = compose_candidate(background, foreground, foreground_mask, candidate)
                score = score_pair(model, composite, mask, device)

            delta = score - baseline_score
            output_rows.append(
                {
                    "case_id": row["case_id"],
                    "case_type": row["case_type"],
                    "dataset_label": row["dataset_label"],
                    "fg_id": row["fg_id"],
                    "bg_id": row["bg_id"],
                    "candidate_source": row["candidate_source"],
                    "candidate_id": row["candidate_id"],
                    "baseline_rank": row["model_rank"],
                    "baseline_score": round(baseline_score, 4),
                    "baseline_tier": score_to_tier(baseline_score),
                    "perturbation_group": variant["group"],
                    "perturbation": variant["name"],
                    "perturbed_score": round(score, 4),
                    "perturbed_tier": score_to_tier(score),
                    "delta_score": round(delta, 4),
                    "abs_delta_score": round(abs(delta), 4),
                    "tier_changed": "yes"
                    if score_to_tier(score) != score_to_tier(baseline_score)
                    else "no",
                    "x": round(candidate["x"], 6),
                    "y": round(candidate["y"], 6),
                    "w": round(candidate["w"], 6),
                    "h": round(candidate["h"], 6),
                    "model_version": MODEL_VERSION,
                }
            )
    return output_rows


def load_image(cache: dict[str, Image.Image], path: Path, mode: str) -> Image.Image:
    key = f"{path}:{mode}"
    if key not in cache:
        require_existing_file(path, "OPA image")
        with Image.open(path) as image:
            cache[key] = image.convert(mode).copy()
    return cache[key]


def candidate_from_row(row: dict[str, str]) -> dict[str, float]:
    return {
        "x": float(row["x"]),
        "y": float(row["y"]),
        "w": float(row["w"]),
        "h": float(row["h"]),
    }


def build_variants(candidate: dict[str, float]) -> list[dict[str, object]]:
    return [
        {"group": "baseline", "name": "baseline", "candidate": candidate},
        {"group": "mask", "name": "mask_erode_7", "candidate": candidate},
        {"group": "mask", "name": "mask_dilate_7", "candidate": candidate},
        {
            "group": "shift",
            "name": "shift_left_0.03",
            "candidate": shift_candidate(candidate, dx=-SHIFT_DELTA, dy=0.0),
        },
        {
            "group": "shift",
            "name": "shift_right_0.03",
            "candidate": shift_candidate(candidate, dx=SHIFT_DELTA, dy=0.0),
        },
        {
            "group": "shift",
            "name": "shift_up_0.03",
            "candidate": shift_candidate(candidate, dx=0.0, dy=-SHIFT_DELTA),
        },
        {
            "group": "shift",
            "name": "shift_down_0.03",
            "candidate": shift_candidate(candidate, dx=0.0, dy=SHIFT_DELTA),
        },
        {
            "group": "scale",
            "name": "scale_down_0.10",
            "candidate": scale_candidate(candidate, factor=1.0 - SCALE_DELTA),
        },
        {
            "group": "scale",
            "name": "scale_up_0.10",
            "candidate": scale_candidate(candidate, factor=1.0 + SCALE_DELTA),
        },
    ]


def perturb_mask(mask: Image.Image, name: str) -> Image.Image:
    if name == "mask_erode_7":
        return mask.filter(ImageFilter.MinFilter(MASK_FILTER_SIZE))
    if name == "mask_dilate_7":
        return mask.filter(ImageFilter.MaxFilter(MASK_FILTER_SIZE))
    raise ValueError(f"Unknown mask perturbation: {name}")


def shift_candidate(candidate: dict[str, float], *, dx: float, dy: float) -> dict[str, float]:
    return {
        **candidate,
        "x": clamp(candidate["x"] + dx, 0.0, 1.0 - candidate["w"]),
        "y": clamp(candidate["y"] + dy, 0.0, 1.0 - candidate["h"]),
    }


def scale_candidate(candidate: dict[str, float], *, factor: float) -> dict[str, float]:
    center_x = candidate["x"] + candidate["w"] / 2.0
    center_y = candidate["y"] + candidate["h"] / 2.0
    width = clamp(candidate["w"] * factor, 0.01, 1.0)
    height = clamp(candidate["h"] * factor, 0.01, 1.0)
    return {
        "x": clamp(center_x - width / 2.0, 0.0, 1.0 - width),
        "y": clamp(center_y - height / 2.0, 0.0, 1.0 - height),
        "w": width,
        "h": height,
    }


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


def score_to_tier(score: float) -> str:
    if score >= 0.7:
        return "recommended"
    if score >= 0.4:
        return "acceptable"
    return "rejected"


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


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
    selected_rows: list[dict[str, str]],
    device: torch.device,
    elapsed_seconds: float,
) -> None:
    variant_rows = [row for row in rows if row["perturbation_group"] != "baseline"]
    changed_tier_rows = [row for row in variant_rows if row["tier_changed"] == "yes"]
    high_delta_rows = [row for row in variant_rows if float(row["abs_delta_score"]) >= 0.2]

    lines = [
        "SmartPlace robustness ablation",
        f"model_version={MODEL_VERSION}",
        f"device={device}",
        f"cases={len(selected_rows)}",
        f"rows={len(rows)}",
        f"score_calls={len(rows)}",
        f"elapsed_seconds={elapsed_seconds:.1f}",
        f"mean_abs_delta={mean(float(row['abs_delta_score']) for row in variant_rows):.4f}",
        f"max_abs_delta={max(float(row['abs_delta_score']) for row in variant_rows):.4f}",
        f"tier_changed_rows={len(changed_tier_rows)}",
        f"high_delta_ge_0.20_rows={len(high_delta_rows)}",
    ]
    for group in ("mask", "shift", "scale"):
        group_rows = [row for row in variant_rows if row["perturbation_group"] == group]
        lines.append(
            f"group_{group}_mean_abs_delta="
            f"{mean(float(row['abs_delta_score']) for row in group_rows):.4f}"
        )

    for case_id, case_rows in group_by_case(rows).items():
        variants = [row for row in case_rows if row["perturbation_group"] != "baseline"]
        strongest = max(variants, key=lambda row: float(row["abs_delta_score"]))
        baseline = next(row for row in case_rows if row["perturbation_group"] == "baseline")
        lines.append(
            "case "
            f"{case_id} "
            f"type={baseline['case_type']} "
            f"candidate={baseline['candidate_id']} "
            f"baseline={baseline['baseline_score']} "
            f"max_variant={strongest['perturbation']} "
            f"max_abs_delta={strongest['abs_delta_score']} "
            f"variant_score={strongest['perturbed_score']} "
            f"tier_changes={sum(1 for row in variants if row['tier_changed'] == 'yes')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def group_by_case(rows: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["case_id"]), []).append(row)
    return grouped


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
