from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import BinaryIO
import urllib.request


ROOT_DIR = Path(__file__).resolve().parents[2]
MODEL_PYTHON = Path(
    os.getenv(
        "SMARTPLACE_MODEL_PYTHON",
        r"D:\DevTools\Anaconda\envs\study\python.exe",
    )
)
PORT = int(os.getenv("SMARTPLACE_API_SMOKE_PORT", "8011"))
MODE = os.getenv("SMARTPLACE_API_SMOKE_MODE", "simopa").strip().lower() or "simopa"
CASE_ID = "opa_test_001"
BACKGROUND = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA" / "background" / "cow" / "442445.jpg"
FOREGROUND = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA" / "foreground" / "cow" / "69931.jpg"
MASK = ROOT_DIR / "assets" / "datasets" / "opa" / "raw" / "new_OPA" / "foreground" / "cow" / "mask_69931.jpg"
SAFE_MODE = MODE.replace("-", "_")
LOG_PATH = ROOT_DIR / "report" / "logs" / (
    "api_simopa_smoke.txt" if MODE == "simopa" else f"api_{SAFE_MODE}_smoke.txt"
)
TABLE_PATH = ROOT_DIR / "report" / "tables" / (
    "api_simopa_smoke.csv" if MODE == "simopa" else f"api_{SAFE_MODE}_smoke.csv"
)


def main() -> None:
    ensure_inputs()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)

    output_log = ROOT_DIR / "server.api-smoke.out.log"
    error_log = ROOT_DIR / "server.api-smoke.err.log"
    process, stdout, stderr = start_server(output_log, error_log)
    try:
        health = wait_for_health()
        payload = post_recommendation()
        write_outputs(health, payload, output_log, error_log)
    finally:
        stop_server(process)
        stdout.close()
        stderr.close()


def ensure_inputs() -> None:
    missing = [path for path in (MODEL_PYTHON, BACKGROUND, FOREGROUND, MASK) if not path.exists()]
    if missing:
        formatted = "\n".join(str(path) for path in missing)
        raise FileNotFoundError(f"Missing required smoke input:\n{formatted}")


def start_server(output_log: Path, error_log: Path) -> tuple[subprocess.Popen, BinaryIO, BinaryIO]:
    env = normalized_environment()
    stdout = output_log.open("wb")
    stderr = error_log.open("wb")
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(PORT),
            ],
            cwd=ROOT_DIR,
            env=env,
            stdout=stdout,
            stderr=stderr,
        )
    except Exception:
        stdout.close()
        stderr.close()
        raise
    return process, stdout, stderr


def stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def normalized_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key.upper() != "PATH"}
    env["Path"] = os.environ.get("Path") or os.environ.get("PATH", "")
    env["SMARTPLACE_SCORER"] = MODE
    env["SMARTPLACE_MODEL_PYTHON"] = str(MODEL_PYTHON)
    env["SMARTPLACE_SIMOPA_DEVICE"] = os.getenv("SMARTPLACE_SIMOPA_DEVICE", "auto")
    return env


def wait_for_health() -> dict:
    deadline = time.time() + 20
    url = f"http://127.0.0.1:{PORT}/api/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("API smoke server did not become ready.")


def post_recommendation() -> dict:
    boundary = "smartplace-api-smoke"
    body = build_multipart_body(
        boundary=boundary,
        fields={
            "candidate_count": "3",
            "foreground_scale": "0.49",
            "mode": MODE,
        },
        files={
            "background": ("442445.jpg", BACKGROUND, "image/jpeg"),
            "foreground": ("69931.jpg", FOREGROUND, "image/jpeg"),
            "mask": ("mask_69931.jpg", MASK, "image/jpeg"),
        },
    )
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/api/place/recommend",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def build_multipart_body(
    *,
    boundary: str,
    fields: dict[str, str],
    files: dict[str, tuple[str, Path, str]],
) -> bytes:
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    for name, (filename, path, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.extend(path.read_bytes())
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body)


def write_outputs(health: dict, payload: dict, output_log: Path, error_log: Path) -> None:
    with TABLE_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "rank",
                "score",
                "tier",
                "x",
                "y",
                "w",
                "h",
                "model_version",
                "runtime_ms",
                "image_width",
                "image_height",
            ],
        )
        writer.writeheader()
        for candidate in payload["candidates"]:
            writer.writerow(
                {
                    "case_id": CASE_ID,
                    "rank": candidate["rank"],
                    "score": candidate["score"],
                    "tier": candidate["tier"],
                    "x": candidate["x"],
                    "y": candidate["y"],
                    "w": candidate["w"],
                    "h": candidate["h"],
                    "model_version": payload["model_version"],
                    "runtime_ms": payload["runtime_ms"],
                    "image_width": payload["image_width"],
                    "image_height": payload["image_height"],
                }
            )

    lines = [
        f"SmartPlace {MODE} API smoke",
        f"health={json.dumps(health, ensure_ascii=False)}",
        f"model_version={payload['model_version']}",
        f"runtime_ms={payload['runtime_ms']}",
        f"image_size={payload['image_width']}x{payload['image_height']}",
        f"server_stdout={output_log}",
        f"server_stderr={error_log}",
    ]
    for candidate in payload["candidates"]:
        lines.append(
            "candidate "
            f"rank={candidate['rank']} "
            f"score={candidate['score']} "
            f"tier={candidate['tier']} "
            f"xywh=({candidate['x']:.4f},{candidate['y']:.4f},{candidate['w']:.4f},{candidate['h']:.4f})"
        )
    LOG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
