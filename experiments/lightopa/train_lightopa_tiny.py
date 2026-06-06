from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import random
import time
from pathlib import Path

from PIL import Image
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA"
DEFAULT_OUTPUT_CSV = ROOT_DIR / "report" / "tables" / "lightopa_tiny_metrics.csv"
DEFAULT_LOG = ROOT_DIR / "report" / "logs" / "lightopa_tiny_training.txt"
DEFAULT_CHECKPOINT = ROOT_DIR / "models" / "lightopa" / "tiny_lightopa_smoke.pth"


class OpaCompositeDataset(Dataset):
    def __init__(self, rows: list[dict[str, str]], dataset_root: Path, image_size: int) -> None:
        self.rows = rows
        self.dataset_root = dataset_root
        self.image_size = image_size

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        image = Image.open(resolve_opa_path(self.dataset_root, row["img_name"])).convert("RGB")
        mask = Image.open(resolve_opa_path(self.dataset_root, row["mask_name"])).convert("L")
        image = image.resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)
        mask = mask.resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)

        rgb = torch.tensor(list(image.getdata()), dtype=torch.float32).view(
            self.image_size,
            self.image_size,
            3,
        )
        alpha = torch.tensor(list(mask.getdata()), dtype=torch.float32).view(
            self.image_size,
            self.image_size,
            1,
        )
        inputs = torch.cat([rgb, alpha], dim=2).permute(2, 0, 1) / 255.0
        label = torch.tensor(float(row["label"]), dtype=torch.float32)
        return inputs, label


class TinyLightOPA(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            conv_block(4, 16),
            conv_block(16, 32),
            conv_block(32, 64),
            conv_block(64, 96),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.15),
            nn.Linear(96, 1),
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(inputs)).squeeze(1)


def conv_block(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=2, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a tiny 4-channel LightOPA baseline.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET))
    parser.add_argument("--train-count", type=int, default=2000)
    parser.add_argument("--val-count", type=int, default=500)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=20260606)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--log-path", default=str(DEFAULT_LOG))
    parser.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
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

    model = TinyLightOPA().to(device)
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
    checkpoint_payload = {
        "model_state_dict": best_state_dict,
        "image_size": args.image_size,
        "model_name": "tiny-lightopa-cnn-v1",
        "param_count": param_count,
        "train_count": len(train_rows),
        "val_count": len(val_rows),
        "best_epoch": best_epoch,
        "best_metrics": best_metrics,
    }
    torch.save(checkpoint_payload, checkpoint)

    write_metrics_csv(
        output_csv,
        {
            "model_name": "tiny-lightopa-cnn-v1",
            "model_type": "4-channel tiny CNN",
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
        },
    )
    write_log(log_path, args, device, param_count, elapsed_seconds, epoch_rows, checkpoint, best_epoch)

    print(f"metrics_csv={output_csv}")
    print(f"log_path={log_path}")
    print(f"checkpoint={checkpoint}")


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    total_items = 0
    for inputs, labels in loader:
        inputs = inputs.to(device)
        labels = labels.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(inputs)
        loss = criterion(logits, labels)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item()) * labels.numel()
        total_items += labels.numel()
    return total_loss / max(1, total_items)


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict[str, float]:
    model.eval()
    total_loss = 0.0
    labels_all: list[int] = []
    scores_all: list[float] = []
    started = time.perf_counter()
    with torch.no_grad():
        for inputs, labels in loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            logits = model(inputs)
            loss = criterion(logits, labels)
            scores = torch.sigmoid(logits)
            total_loss += float(loss.item()) * labels.numel()
            labels_all.extend(int(value) for value in labels.cpu().tolist())
            scores_all.extend(float(value) for value in scores.cpu().tolist())

    elapsed = time.perf_counter() - started
    predictions = [1 if score >= 0.5 else 0 for score in scores_all]
    best_threshold, best_balanced = best_balanced_threshold(labels_all, scores_all)
    tuned_predictions = [1 if score >= best_threshold else 0 for score in scores_all]
    return {
        "val_loss": total_loss / max(1, len(labels_all)),
        "accuracy": accuracy(labels_all, predictions),
        "balanced_accuracy": balanced_accuracy(labels_all, predictions),
        "precision": precision(labels_all, predictions),
        "recall": recall(labels_all, predictions),
        "f1": f1_score(labels_all, predictions),
        "roc_auc": roc_auc(labels_all, scores_all),
        "best_threshold": best_threshold,
        "best_balanced_accuracy": best_balanced,
        "best_threshold_f1": f1_score(labels_all, tuned_predictions),
        "avg_inference_ms_per_sample": elapsed * 1000.0 / max(1, len(labels_all)),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def balanced_sample(rows: list[dict[str, str]], count: int, seed: int) -> list[dict[str, str]]:
    positives = [row for row in rows if row["label"] == "1"]
    negatives = [row for row in rows if row["label"] == "0"]
    half = count // 2
    rng = random.Random(seed)
    rng.shuffle(positives)
    rng.shuffle(negatives)
    sampled = positives[:half] + negatives[: count - half]
    rng.shuffle(sampled)
    return sampled


def resolve_opa_path(dataset_root: Path, value: str) -> Path:
    normalized = value.replace("\\", "/")
    if normalized.startswith("dataset/"):
        normalized = normalized[len("dataset/") :]
    path = dataset_root / normalized
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if requested == "cuda":
        return torch.device("cuda:0")
    return torch.device(requested)


def accuracy(labels: list[int], predictions: list[int]) -> float:
    return sum(1 for label, pred in zip(labels, predictions) if label == pred) / max(1, len(labels))


def balanced_accuracy(labels: list[int], predictions: list[int]) -> float:
    positives = [pred for label, pred in zip(labels, predictions) if label == 1]
    negatives = [pred for label, pred in zip(labels, predictions) if label == 0]
    tpr = sum(1 for pred in positives if pred == 1) / max(1, len(positives))
    tnr = sum(1 for pred in negatives if pred == 0) / max(1, len(negatives))
    return (tpr + tnr) / 2.0


def precision(labels: list[int], predictions: list[int]) -> float:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    return tp / max(1, tp + fp)


def recall(labels: list[int], predictions: list[int]) -> float:
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    return tp / max(1, tp + fn)


def f1_score(labels: list[int], predictions: list[int]) -> float:
    p = precision(labels, predictions)
    r = recall(labels, predictions)
    return 2.0 * p * r / max(1e-8, p + r)


def roc_auc(labels: list[int], scores: list[float]) -> float:
    pairs = sorted(zip(scores, labels), key=lambda item: item[0])
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if positive_count == 0 or negative_count == 0:
        return 0.5

    rank_sum = 0.0
    index = 0
    while index < len(pairs):
        next_index = index + 1
        while next_index < len(pairs) and pairs[next_index][0] == pairs[index][0]:
            next_index += 1
        average_rank = (index + 1 + next_index) / 2.0
        rank_sum += sum(average_rank for _, label in pairs[index:next_index] if label == 1)
        index = next_index

    return (rank_sum - positive_count * (positive_count + 1) / 2.0) / (
        positive_count * negative_count
    )


def best_balanced_threshold(labels: list[int], scores: list[float]) -> tuple[float, float]:
    thresholds = sorted(set(scores))
    if not thresholds:
        return 0.5, 0.5

    best_threshold = 0.5
    best_score = -1.0
    for threshold in thresholds:
        predictions = [1 if score >= threshold else 0 for score in scores]
        score = balanced_accuracy(labels, predictions)
        if score > best_score:
            best_score = score
            best_threshold = threshold
    return best_threshold, best_score


def round_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 6) for key, value in metrics.items()}


def write_metrics_csv(path: Path, row: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)


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
        "SmartPlace Tiny LightOPA training",
        "model_name=tiny-lightopa-cnn-v1",
        "model_type=4-channel tiny CNN",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    main()
