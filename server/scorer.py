from __future__ import annotations

import atexit
from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import uuid


DEFAULT_SCORER_MODE = os.getenv("SMARTPLACE_SCORER", "mock").strip().lower() or "mock"
SUPPORTED_SCORER_MODES = {
    "mock",
    "simopa",
    "simopa-lite",
    "simopa-worker",
    "simopa-lite-worker",
}
ROOT_DIR = Path(__file__).resolve().parents[1]
SIMOPA_MODEL_VERSION = "simopa-rgb-mask-v1"
SIMOPA_LITE_MODEL_VERSION = "simopa-lite-candidate-budget-v1"
SIMOPA_WORKER_MODEL_VERSION = "simopa-worker-rgb-mask-v1"
SIMOPA_LITE_WORKER_MODEL_VERSION = "simopa-lite-worker-candidate-budget-v1"
SIMOPA_SCRIPT = ROOT_DIR / "experiments" / "opa_baseline" / "score_candidates.py"
SIMOPA_WORKER_SCRIPT = ROOT_DIR / "experiments" / "opa_baseline" / "score_candidates_worker.py"
SIMOPA_WEIGHT = (
    ROOT_DIR
    / "external"
    / "Object-Placement-Assessment-Dataset-OPA"
    / "eval_opascore"
    / "checkpoints"
    / "simopa.pth"
)
MODEL_PYTHON_TEXT = os.getenv("SMARTPLACE_MODEL_PYTHON", "").strip()
MODEL_PYTHON = Path(MODEL_PYTHON_TEXT) if MODEL_PYTHON_TEXT else None
SIMOPA_DEVICE = os.getenv("SMARTPLACE_SIMOPA_DEVICE", "auto")
_SIMOPA_WORKER: SimopaWorker | None = None
_SIMOPA_WORKER_GUARD = threading.Lock()


@dataclass(frozen=True)
class ScoreResult:
    score: float
    model_version: str
    runtime_ms: int
    mode: str


def get_scorer_status(mode: str | None = None) -> dict[str, str]:
    selected_mode = resolve_scorer_mode(mode)
    if is_simopa_mode(selected_mode):
        script = SIMOPA_WORKER_SCRIPT if is_simopa_worker_mode(selected_mode) else SIMOPA_SCRIPT
        ready = MODEL_PYTHON is not None and MODEL_PYTHON.exists() and script.exists() and SIMOPA_WEIGHT.exists()
        return {
            "mode": selected_mode,
            "status": "ready" if ready else "unavailable",
            "model_version": simopa_model_version(selected_mode),
        }

    return {
        "mode": selected_mode,
        "status": "ready",
        "model_version": "mock-v0",
    }


def score_candidate_template(
    base_score: float,
    *,
    model_version: str,
    mode: str | None = None,
) -> ScoreResult:
    """Score a generated candidate placeholder.

    Mock mode uses predefined candidate scores while preserving the same scorer
    boundary used by the SimOPA modes.
    """
    started = time.perf_counter()
    selected_mode = resolve_scorer_mode(mode)
    if selected_mode != "mock":
        raise RuntimeError(f"Unsupported scorer mode: {selected_mode}")

    return ScoreResult(
        score=clamp_score(base_score),
        model_version=model_version,
        runtime_ms=max(1, round((time.perf_counter() - started) * 1000)),
        mode=selected_mode,
    )


def score_candidate_boxes(
    *,
    background_bytes: bytes,
    foreground_bytes: bytes,
    mask_bytes: bytes | None,
    candidates: list[dict],
    mode: str | None = None,
) -> list[ScoreResult]:
    selected_mode = resolve_scorer_mode(mode)
    if selected_mode == "mock":
        return [
            score_candidate_template(
                candidate["base_score"],
                model_version="mock-v0",
                mode=selected_mode,
            )
            for candidate in candidates
        ]

    return score_candidates_with_simopa(
        background_bytes=background_bytes,
        foreground_bytes=foreground_bytes,
        mask_bytes=mask_bytes,
        candidates=candidates,
        mode=selected_mode,
    )


def score_composite(
    composite_image: bytes,
    foreground_mask: bytes | None = None,
    *,
    model_version: str,
    mode: str | None = None,
) -> ScoreResult:
    """Stable future entrypoint for real composite-image scoring."""
    started = time.perf_counter()
    selected_mode = resolve_scorer_mode(mode)
    if selected_mode != "mock":
        raise RuntimeError("Use score_candidate_boxes for SimOPA scoring.")

    # Deterministic placeholder for smoke tests. Real OPA/libcom scoring should
    # replace this branch while preserving the function signature.
    size_signal = min(len(composite_image), 500_000) / 500_000
    mask_bonus = 0.05 if foreground_mask else 0.0
    score = 0.45 + size_signal * 0.1 + mask_bonus

    return ScoreResult(
        score=clamp_score(score),
        model_version=model_version,
        runtime_ms=max(1, round((time.perf_counter() - started) * 1000)),
        mode=selected_mode,
    )


def resolve_scorer_mode(mode: str | None = None) -> str:
    selected_mode = (mode or DEFAULT_SCORER_MODE).strip().lower()
    if selected_mode not in SUPPORTED_SCORER_MODES:
        raise RuntimeError(
            f"Unsupported scorer mode: {selected_mode}. "
            f"Supported modes: {', '.join(sorted(SUPPORTED_SCORER_MODES))}"
        )
    return selected_mode


def is_simopa_mode(mode: str) -> bool:
    return mode.startswith("simopa")


def is_simopa_worker_mode(mode: str) -> bool:
    return mode in {"simopa-worker", "simopa-lite-worker"}


def is_simopa_lite_mode(mode: str) -> bool:
    return mode in {"simopa-lite", "simopa-lite-worker"}


def simopa_model_version(mode: str) -> str:
    if mode == "simopa-worker":
        return SIMOPA_WORKER_MODEL_VERSION
    if mode == "simopa-lite-worker":
        return SIMOPA_LITE_WORKER_MODEL_VERSION
    if mode == "simopa-lite":
        return SIMOPA_LITE_MODEL_VERSION
    return SIMOPA_MODEL_VERSION


def clamp_score(value: float) -> float:
    return min(1.0, max(0.0, float(value)))


def score_candidates_with_simopa(
    *,
    background_bytes: bytes,
    foreground_bytes: bytes,
    mask_bytes: bytes | None,
    candidates: list[dict],
    mode: str = "simopa",
) -> list[ScoreResult]:
    selected_mode = resolve_scorer_mode(mode)
    status = get_scorer_status(selected_mode)
    if status["status"] != "ready":
        raise RuntimeError(
            "SimOPA scorer is not ready. Set SMARTPLACE_MODEL_PYTHON or pass -ModelPython, "
            "and ensure the score script and simopa.pth weight exist."
        )
    if is_simopa_worker_mode(selected_mode):
        return score_candidates_with_simopa_worker(
            background_bytes=background_bytes,
            foreground_bytes=foreground_bytes,
            mask_bytes=mask_bytes,
            candidates=candidates,
            mode=selected_mode,
        )

    with tempfile.TemporaryDirectory(prefix="smartplace-simopa-") as temp_name:
        temp_dir = Path(temp_name)
        background_path = temp_dir / "background.img"
        foreground_path = temp_dir / "foreground.img"
        mask_path = temp_dir / "mask.img"
        candidates_path = temp_dir / "candidates.json"

        background_path.write_bytes(background_bytes)
        foreground_path.write_bytes(foreground_bytes)
        if mask_bytes:
            mask_path.write_bytes(mask_bytes)

        candidate_payload = [
            {
                "rank": candidate["rank"],
                "x": candidate["x"],
                "y": candidate["y"],
                "w": candidate["w"],
                "h": candidate["h"],
            }
            for candidate in candidates
        ]
        candidates_path.write_text(json.dumps(candidate_payload), encoding="utf-8")

        command = [
            str(MODEL_PYTHON),
            str(SIMOPA_SCRIPT),
            "--background",
            str(background_path),
            "--foreground",
            str(foreground_path),
            "--candidates-json",
            str(candidates_path),
            "--weight",
            str(SIMOPA_WEIGHT),
            "--device",
            SIMOPA_DEVICE,
        ]
        if mask_bytes:
            command.extend(["--mask", str(mask_path)])

        started = time.perf_counter()
        completed = subprocess.run(
            command,
            cwd=ROOT_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"SimOPA scorer failed: {completed.stderr or completed.stdout}")

        payload = parse_simopa_output(completed.stdout)
        total_runtime_ms = max(1, round((time.perf_counter() - started) * 1000))
        scores_by_rank = {item["rank"]: item for item in payload["scores"]}

        results = []
        for candidate in candidates:
            score_payload = scores_by_rank[candidate["rank"]]
            results.append(
                ScoreResult(
                    score=clamp_score(score_payload["score"]),
                    model_version=simopa_model_version(selected_mode),
                    runtime_ms=score_payload.get("runtime_ms", total_runtime_ms),
                    mode=selected_mode,
                )
            )
        return results


def score_candidates_with_simopa_worker(
    *,
    background_bytes: bytes,
    foreground_bytes: bytes,
    mask_bytes: bytes | None,
    candidates: list[dict],
    mode: str,
) -> list[ScoreResult]:
    selected_mode = resolve_scorer_mode(mode)
    worker = get_simopa_worker()

    with tempfile.TemporaryDirectory(prefix="smartplace-simopa-worker-") as temp_name:
        temp_dir = Path(temp_name)
        background_path = temp_dir / "background.img"
        foreground_path = temp_dir / "foreground.img"
        mask_path = temp_dir / "mask.img"

        background_path.write_bytes(background_bytes)
        foreground_path.write_bytes(foreground_bytes)
        if mask_bytes:
            mask_path.write_bytes(mask_bytes)

        candidate_payload = [
            {
                "rank": candidate["rank"],
                "x": candidate["x"],
                "y": candidate["y"],
                "w": candidate["w"],
                "h": candidate["h"],
            }
            for candidate in candidates
        ]
        request_id = uuid.uuid4().hex
        payload = worker.score(
            {
                "request_id": request_id,
                "background": str(background_path),
                "foreground": str(foreground_path),
                "mask": str(mask_path) if mask_bytes else None,
                "candidates": candidate_payload,
            }
        )
        scores_by_rank = {item["rank"]: item for item in payload["scores"]}

        results = []
        for candidate in candidates:
            score_payload = scores_by_rank[candidate["rank"]]
            results.append(
                ScoreResult(
                    score=clamp_score(score_payload["score"]),
                    model_version=simopa_model_version(selected_mode),
                    runtime_ms=score_payload.get("runtime_ms", 1),
                    mode=selected_mode,
                )
            )
        return results


class SimopaWorker:
    def __init__(self) -> None:
        command = [
            str(MODEL_PYTHON),
            str(SIMOPA_WORKER_SCRIPT),
            "--weight",
            str(SIMOPA_WEIGHT),
            "--device",
            SIMOPA_DEVICE,
        ]
        self._process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        self._lock = threading.Lock()
        self._read_ready()

    def score(self, request: dict) -> dict:
        with self._lock:
            if self._process.poll() is not None:
                raise RuntimeError("SimOPA worker is not running.")
            if self._process.stdin is None:
                raise RuntimeError("SimOPA worker stdin is unavailable.")

            self._process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            self._process.stdin.flush()
            while True:
                message = self._read_message()
                if message.get("type") == "result" and message.get("request_id") == request["request_id"]:
                    return message
                if message.get("type") == "error" and message.get("request_id") == request["request_id"]:
                    raise RuntimeError(message.get("error", "SimOPA worker error"))

    def stop(self) -> None:
        if self._process.poll() is not None:
            return
        try:
            if self._process.stdin is not None:
                self._process.stdin.write(json.dumps({"command": "shutdown"}) + "\n")
                self._process.stdin.flush()
        except OSError:
            pass
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.terminate()

    def _read_ready(self) -> None:
        while True:
            message = self._read_message()
            if message.get("type") == "ready":
                return

    def _read_message(self) -> dict:
        if self._process.stdout is None:
            raise RuntimeError("SimOPA worker stdout is unavailable.")
        while True:
            line = self._process.stdout.readline()
            if not line:
                raise RuntimeError("SimOPA worker stopped before returning a JSON message.")
            stripped = line.strip()
            if not stripped.startswith("{"):
                continue
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                continue


def get_simopa_worker() -> SimopaWorker:
    global _SIMOPA_WORKER
    with _SIMOPA_WORKER_GUARD:
        if _SIMOPA_WORKER is None or _SIMOPA_WORKER._process.poll() is not None:
            _SIMOPA_WORKER = SimopaWorker()
        return _SIMOPA_WORKER


def stop_simopa_worker() -> None:
    global _SIMOPA_WORKER
    with _SIMOPA_WORKER_GUARD:
        if _SIMOPA_WORKER is not None:
            _SIMOPA_WORKER.stop()
            _SIMOPA_WORKER = None


def parse_simopa_output(stdout: str) -> dict:
    for line in reversed(stdout.splitlines()):
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)
    raise RuntimeError(f"SimOPA scorer produced no JSON output: {stdout}")


atexit.register(stop_simopa_worker)
