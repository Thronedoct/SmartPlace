from __future__ import annotations

import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TABLE_DIR = ROOT_DIR / "report" / "tables"
LOG_DIR = ROOT_DIR / "report" / "logs"

DEFAULT_OUTPUT_CSV = TABLE_DIR / "lightopa_model_comparison.csv"
DEFAULT_LOG = LOG_DIR / "lightopa_model_comparison.txt"


def main() -> None:
    tiny = read_one(TABLE_DIR / "lightopa_tiny_metrics.csv")
    residual = read_one(TABLE_DIR / "lightopa_residual_metrics.csv")
    rows = [comparison_row(tiny), comparison_row(residual)]

    DEFAULT_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    tiny_auc = float(tiny["roc_auc"])
    residual_auc = float(residual["roc_auc"])
    tiny_acc = float(tiny["accuracy"])
    residual_acc = float(residual["accuracy"])
    lines = [
        "SmartPlace LightOPA model comparison",
        f"models={tiny['model_name']},{residual['model_name']}",
        f"accuracy_delta={residual_acc - tiny_acc:.6f}",
        f"roc_auc_delta={residual_auc - tiny_auc:.6f}",
        f"tiny_param_count={tiny['param_count']}",
        f"residual_param_count={residual['param_count']}",
        f"output_csv={DEFAULT_OUTPUT_CSV.relative_to(ROOT_DIR)}",
    ]
    DEFAULT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"comparison_csv={DEFAULT_OUTPUT_CSV}")
    print(f"log_path={DEFAULT_LOG}")


def read_one(path: Path) -> dict[str, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 1:
        raise ValueError(f"Expected one row in {path}, found {len(rows)}")
    return rows[0]


def comparison_row(row: dict[str, str]) -> dict[str, object]:
    return {
        "model_name": row["model_name"],
        "model_type": row["model_type"],
        "train_count": row["train_count"],
        "val_count": row["val_count"],
        "param_count": row["param_count"],
        "best_epoch": row["epoch"],
        "accuracy": row["accuracy"],
        "best_balanced_accuracy": row["best_balanced_accuracy"],
        "f1": row["f1"],
        "roc_auc": row["roc_auc"],
        "avg_inference_ms_per_sample": row["avg_inference_ms_per_sample"],
        "elapsed_seconds": row["elapsed_seconds"],
        "metrics_source": metrics_source(row["model_name"]),
    }


def metrics_source(model_name: str) -> str:
    if model_name.startswith("tiny"):
        return "report/tables/lightopa_tiny_metrics.csv"
    if model_name.startswith("residual"):
        return "report/tables/lightopa_residual_metrics.csv"
    return ""


if __name__ == "__main__":
    main()
