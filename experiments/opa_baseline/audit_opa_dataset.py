from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_SPLIT = "test"
DEFAULT_SMOKE_CSV = ROOT_DIR / "assets" / "datasets" / "opa" / "splits" / "smoke_100.csv"
DEFAULT_AUDIT_CSV = ROOT_DIR / "report" / "tables" / "opa_sample_audit.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local OPA dataset samples.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--split", choices=["train", "test"], default=DEFAULT_SPLIT)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--smoke-csv", default=str(DEFAULT_SMOKE_CSV))
    parser.add_argument("--audit-csv", default=str(DEFAULT_AUDIT_CSV))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    split_csv = dataset_root / f"{args.split}_set.csv"
    smoke_csv = Path(args.smoke_csv)
    audit_csv = Path(args.audit_csv)
    smoke_csv.parent.mkdir(parents=True, exist_ok=True)
    audit_csv.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    with split_csv.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        positives = []
        negatives = []
        for row in reader:
            if row["label"] == "1" and len(positives) < args.limit // 2:
                positives.append(row)
            elif row["label"] == "0" and len(negatives) < args.limit - args.limit // 2:
                negatives.append(row)
            if len(positives) + len(negatives) >= args.limit:
                break
        rows = positives + negatives

    audit_rows = []
    for index, row in enumerate(rows, start=1):
        image_path = resolve_opa_path(dataset_root, row["img_name"])
        mask_path = resolve_opa_path(dataset_root, row["mask_name"])
        image_ok, width, height = inspect_image(image_path)
        mask_ok, mask_width, mask_height = inspect_image(mask_path)
        usable = image_ok and mask_ok and width == mask_width and height == mask_height
        audit_rows.append(
            {
                "case_id": f"opa_{args.split}_{index:03d}",
                "split": args.split,
                "fg_id": row["fg_id"],
                "bg_id": row["bg_id"],
                "position": row["position"],
                "scale": row["scale"],
                "label": row["label"],
                "composite_path": to_project_path(image_path),
                "mask_path": to_project_path(mask_path),
                "width": width,
                "height": height,
                "mask_width": mask_width,
                "mask_height": mask_height,
                "usable": "yes" if usable else "no",
                "note": "" if usable else "missing or mismatched image/mask",
            }
        )

    write_csv(smoke_csv, audit_rows)
    write_csv(audit_csv, audit_rows)
    print(f"dataset_root={dataset_root}")
    print(f"split={args.split}")
    print(f"rows={len(audit_rows)}")
    print(f"smoke_csv={smoke_csv}")
    print(f"audit_csv={audit_csv}")
    print(f"usable={sum(1 for row in audit_rows if row['usable'] == 'yes')}")
    print(f"positive={sum(1 for row in audit_rows if row['label'] == '1')}")
    print(f"negative={sum(1 for row in audit_rows if row['label'] == '0')}")


def resolve_opa_path(dataset_root: Path, raw_path: str) -> Path:
    normalized = raw_path.replace("\\", "/")
    if normalized.startswith("dataset/"):
        normalized = normalized.removeprefix("dataset/")
    return dataset_root / normalized


def inspect_image(path: Path) -> tuple[bool, int, int]:
    if not path.exists():
        return False, 0, 0
    try:
        with Image.open(path) as image:
            return True, image.width, image.height
    except OSError:
        return False, 0, 0


def to_project_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
