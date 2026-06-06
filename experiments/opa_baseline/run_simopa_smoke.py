from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_PACKAGES = ROOT_DIR / ".model-packages"
OPA_REPO = ROOT_DIR / "external" / "Object-Placement-Assessment-Dataset-OPA"
DEFAULT_WEIGHT = OPA_REPO / "eval_opascore" / "checkpoints" / "simopa.pth"
DEFAULT_IMAGE = OPA_REPO / "eval_opascore" / "examples" / "composite_1.jpg"
DEFAULT_MASK = OPA_REPO / "eval_opascore" / "examples" / "mask_1.jpg"

for path in (LOCAL_PACKAGES, OPA_REPO, OPA_REPO / "eval_opascore"):
    sys.path.insert(0, str(path))

import torch  # noqa: E402
from PIL import Image  # noqa: E402
from simopa import ObjectPlacementAssessmentModel  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test SimOPA baseline scoring.")
    parser.add_argument("--image", default=str(DEFAULT_IMAGE), help="Composite image path.")
    parser.add_argument("--mask", default=str(DEFAULT_MASK), help="Foreground mask path.")
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT), help="SimOPA weight path.")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, etc.")
    return parser.parse_args()


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if requested == "cuda":
        return torch.device("cuda:0")
    return torch.device(requested)


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)

    started = time.perf_counter()
    model = ObjectPlacementAssessmentModel(device, opt)
    model.data_preprocess = lambda image, mask: preprocess_image_mask(
        image,
        mask,
        model.image_size,
        device,
    )
    score = model(args.image, args.mask)
    runtime_ms = round((time.perf_counter() - started) * 1000)

    print(f"device={device}")
    print(f"weight={args.weight}")
    print(f"image={args.image}")
    print(f"mask={args.mask}")
    print(f"score={score}")
    print(f"runtime_ms={runtime_ms}")


def preprocess_image_mask(image: str, mask: str, image_size: int, device: torch.device) -> torch.Tensor:
    img = Image.open(image).convert("RGB").resize((image_size, image_size), Image.BILINEAR)
    mask_img = Image.open(mask).convert("L").resize((image_size, image_size), Image.BILINEAR)

    rgb = torch.tensor(list(img.getdata()), dtype=torch.float32).view(image_size, image_size, 3) / 255.0
    alpha = torch.tensor(list(mask_img.getdata()), dtype=torch.float32).view(image_size, image_size, 1) / 255.0
    cat_tensor = torch.cat([rgb, alpha], dim=2).permute(2, 0, 1).unsqueeze(0)
    return cat_tensor.to(device)


if __name__ == "__main__":
    main()
