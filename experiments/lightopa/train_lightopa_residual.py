from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from train_lightopa_tiny import (
    DEFAULT_DATASET,
    ROOT_DIR,
    OpaCompositeDataset,
    balanced_sample,
    evaluate,
    read_csv,
    resolve_device,
    round_metrics,
    sha256_file,
    train_epoch,
    write_metrics_csv,
)


DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "lightopa_residual_metrics.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "lightopa_residual_training.txt"
DEFAULT_CHECKPOINT = ROOT_DIR / "models" / "lightopa" / "residual_lightopa_smoke.pth"
MODEL_NAME = "residual-lightopa-cnn-v1"
MODEL_TYPE = "4-channel residual CNN"


class ResidualBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, stride: int = 1) -> None:
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                stride=stride,
                padding=1,
                bias=False,
            ),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
        )
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels),
            )
        else:
            self.shortcut = nn.Identity()
        self.activation = nn.ReLU(inplace=True)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.activation(self.body(inputs) + self.shortcut(inputs))


class ResidualLightOPA(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            ResidualBlock(32, 32),
            ResidualBlock(32, 64, stride=2),
            ResidualBlock(64, 64),
            ResidualBlock(64, 128, stride=2),
            ResidualBlock(128, 128),
            ResidualBlock(128, 160, stride=2),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.25),
            nn.Linear(160, 1),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(inputs)).squeeze(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a stronger residual LightOPA baseline.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--train-count", type=int, default=3000)
    parser.add_argument("--val-count", type=int, default=600)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=5e-4)
    parser.add_argument("--seed", type=int, default=20260607)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)
    device = resolve_device(args.device)
    dataset_root = Path(args.dataset_root)
    output_csv = Path(args.output_csv)
    log_path = Path(args.log_path)
    checkpoint = Path(args.checkpoint)

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)

    train_rows = balanced_sample(read_csv(dataset_root / "train_set.csv"), args.train_count, args.seed)
    val_rows = balanced_sample(read_csv(dataset_root / "test_set.csv"), args.val_count, args.seed + 1)

    train_loader = DataLoader(
        OpaCompositeDataset(train_rows, dataset_root, args.image_size),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        OpaCompositeDataset(val_rows, dataset_root, args.image_size),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )

    model = ResidualLightOPA().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    criterion = nn.BCEWithLogitsLoss()

    started = time.perf_counter()
    epoch_rows: list[dict[str, object]] = []
    best_epoch = 0
    best_score = -1.0
    best_state_dict = copy.deepcopy(model.state_dict())
    for epoch in range(1, args.epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        metrics = evaluate(model, val_loader, criterion, device)
        epoch_row = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            **round_metrics(metrics),
        }
        epoch_rows.append(epoch_row)
        if metrics["best_balanced_accuracy"] > best_score:
            best_score = metrics["best_balanced_accuracy"]
            best_epoch = epoch
            best_state_dict = copy.deepcopy(model.state_dict())
        print(
            f"epoch={epoch} train_loss={train_loss:.4f} "
            f"val_accuracy={metrics['accuracy']:.4f} "
            f"best_balanced_accuracy={metrics['best_balanced_accuracy']:.4f} "
            f"val_auc={metrics['roc_auc']:.4f}"
        )

    elapsed_seconds = time.perf_counter() - started
    best_metrics = next(row for row in epoch_rows if int(row["epoch"]) == best_epoch)
    param_count = sum(parameter.numel() for parameter in model.parameters())
    torch.save(
        {
            "model_state_dict": best_state_dict,
            "image_size": args.image_size,
            "model_name": MODEL_NAME,
            "param_count": param_count,
            "train_count": len(train_rows),
            "val_count": len(val_rows),
            "best_epoch": best_epoch,
            "best_metrics": best_metrics,
        },
        checkpoint,
    )

    row = {
        "model_name": MODEL_NAME,
        "model_type": MODEL_TYPE,
        "device": str(device),
        "image_size": args.image_size,
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "param_count": param_count,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "checkpoint_path": str(checkpoint.relative_to(ROOT_DIR)),
        "checkpoint_sha256": sha256_file(checkpoint),
        **best_metrics,
    }
    write_metrics_csv(output_csv, row)
    write_log(log_path, args, device, param_count, elapsed_seconds, epoch_rows, checkpoint, best_epoch)

    print(f"metrics_csv={output_csv}")
    print(f"log_path={log_path}")
    print(f"checkpoint={checkpoint}")


def write_log(
    path: Path,
    args: argparse.Namespace,
    device: torch.device,
    param_count: int,
    elapsed_seconds: float,
    epoch_rows: list[dict[str, object]],
    checkpoint: Path,
    best_epoch: int,
) -> None:
    best = next(row for row in epoch_rows if int(row["epoch"]) == best_epoch)
    lines = [
        "SmartPlace Residual LightOPA training",
        f"model_name={MODEL_NAME}",
        f"model_type={MODEL_TYPE}",
        f"device={device}",
        f"image_size={args.image_size}",
        f"train_count={args.train_count}",
        f"val_count={args.val_count}",
        f"epochs={args.epochs}",
        f"batch_size={args.batch_size}",
        f"learning_rate={args.learning_rate}",
        f"param_count={param_count}",
        f"elapsed_seconds={elapsed_seconds:.2f}",
        f"best_epoch={best_epoch}",
        f"checkpoint_path={checkpoint.relative_to(ROOT_DIR)}",
        f"checkpoint_sha256={sha256_file(checkpoint)}",
        f"best_epoch_accuracy={best['accuracy']}",
        f"best_epoch_balanced_accuracy={best['balanced_accuracy']}",
        f"best_epoch_f1={best['f1']}",
        f"best_epoch_roc_auc={best['roc_auc']}",
        f"best_threshold={best['best_threshold']}",
        f"best_balanced_accuracy={best['best_balanced_accuracy']}",
        f"best_threshold_f1={best['best_threshold_f1']}",
        f"avg_inference_ms_per_sample={best['avg_inference_ms_per_sample']}",
    ]
    for row in epoch_rows:
        lines.append(
            "epoch "
            f"{row['epoch']} "
            f"train_loss={row['train_loss']} "
            f"val_loss={row['val_loss']} "
            f"accuracy={row['accuracy']} "
            f"roc_auc={row['roc_auc']}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
