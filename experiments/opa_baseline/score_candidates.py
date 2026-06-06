from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time


ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_PACKAGES = ROOT_DIR / ".model-packages"
OPA_REPO = ROOT_DIR / "external" / "Object-Placement-Assessment-Dataset-OPA"
DEFAULT_WEIGHT = OPA_REPO / "eval_opascore" / "checkpoints" / "simopa.pth"
MODEL_VERSION = "simopa-rgb-mask-v1"

for path in (LOCAL_PACKAGES, OPA_REPO, OPA_REPO / "eval_opascore"):
    sys.path.insert(0, str(path))

import torch  # noqa: E402
from PIL import Image  # noqa: E402
from simopa import ObjectPlacementAssessmentModel  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score SmartPlace candidates with SimOPA.")
    parser.add_argument("--background", required=True, help="Background image path.")
    parser.add_argument("--foreground", required=True, help="Foreground image path.")
    parser.add_argument("--mask", default=None, help="Optional foreground mask path.")
    parser.add_argument("--candidates-json", required=True, help="Candidate JSON path.")
    parser.add_argument("--weight", default=str(DEFAULT_WEIGHT), help="SimOPA weight path.")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, etc.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device = resolve_device(args.device)
    opt = argparse.Namespace(weight=args.weight)
    model = ObjectPlacementAssessmentModel(device, opt)
    model.data_preprocess = lambda image, mask: preprocess_image_mask(
        image,
        mask,
        model.image_size,
        device,
    )

    background = Image.open(args.background).convert("RGB")
    foreground = Image.open(args.foreground)
    foreground_mask = Image.open(args.mask).convert("L") if args.mask else None
    candidates = json.loads(Path(args.candidates_json).read_text(encoding="utf-8"))

    scored = []
    for candidate in candidates:
        started = time.perf_counter()
        composite, composite_mask = compose_candidate(background, foreground, foreground_mask, candidate)
        with torch.no_grad():
            inputs = preprocess_pil_pair(composite, composite_mask, model.image_size, device)
            logits = model.model(inputs)
            score = torch.softmax(logits, dim=-1)[0, 1].cpu().item()
        scored.append(
            {
                "rank": candidate["rank"],
                "score": round(float(score), 4),
                "runtime_ms": max(1, round((time.perf_counter() - started) * 1000)),
            }
        )

    print(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "device": str(device),
                "scores": scored,
            },
            ensure_ascii=False,
        )
    )


def resolve_device(requested: str) -> torch.device:
    if requested == "auto":
        return torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    if requested == "cuda":
        return torch.device("cuda:0")
    return torch.device(requested)


def compose_candidate(
    background: Image.Image,
    foreground: Image.Image,
    foreground_mask: Image.Image | None,
    candidate: dict,
) -> tuple[Image.Image, Image.Image]:
    bg_width, bg_height = background.size
    box_width = max(1, round(candidate["w"] * bg_width))
    box_height = max(1, round(candidate["h"] * bg_height))
    left = clamp_int(round(candidate["x"] * bg_width), 0, max(0, bg_width - box_width))
    top = clamp_int(round(candidate["y"] * bg_height), 0, max(0, bg_height - box_height))

    fg_rgba = build_rgba_foreground(foreground, foreground_mask).resize(
        (box_width, box_height),
        Image.Resampling.LANCZOS,
    )
    alpha = fg_rgba.getchannel("A")

    composite = background.convert("RGBA")
    composite.alpha_composite(fg_rgba, (left, top))

    composite_mask = Image.new("L", background.size, 0)
    composite_mask.paste(alpha, (left, top))
    return composite.convert("RGB"), composite_mask


def build_rgba_foreground(foreground: Image.Image, foreground_mask: Image.Image | None) -> Image.Image:
    if foreground.mode == "RGBA":
        return foreground

    rgb = foreground.convert("RGB")
    if foreground_mask is None:
        alpha = Image.new("L", rgb.size, 255)
    else:
        alpha = foreground_mask.resize(rgb.size, Image.Resampling.BILINEAR)

    rgba = rgb.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba


def preprocess_image_mask(image: str, mask: str, image_size: int, device: torch.device) -> torch.Tensor:
    img = Image.open(image).convert("RGB").resize((image_size, image_size), Image.BILINEAR)
    mask_img = Image.open(mask).convert("L").resize((image_size, image_size), Image.BILINEAR)
    return preprocess_pil_pair(img, mask_img, image_size, device)


def preprocess_pil_pair(
    image: Image.Image,
    mask: Image.Image,
    image_size: int,
    device: torch.device,
) -> torch.Tensor:
    img = image.convert("RGB").resize((image_size, image_size), Image.BILINEAR)
    mask_img = mask.convert("L").resize((image_size, image_size), Image.BILINEAR)

    rgb = torch.tensor(list(img.getdata()), dtype=torch.float32).view(image_size, image_size, 3) / 255.0
    alpha = torch.tensor(list(mask_img.getdata()), dtype=torch.float32).view(image_size, image_size, 1) / 255.0
    return torch.cat([rgb, alpha], dim=2).permute(2, 0, 1).unsqueeze(0).to(device)


def clamp_int(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


if __name__ == "__main__":
    main()
