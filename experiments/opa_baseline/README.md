# OPA Baseline Smoke Test

This experiment verifies that the released SimOPA model can load locally and score example composite/mask pairs.

Environment:

```text
Python: D:\DevTools\Anaconda\envs\study\python.exe
Local packages: .model-packages
Torch: 2.8.0+cu129
CUDA: available
GPU: NVIDIA GeForce RTX 4070 Ti SUPER
```

Required local files:

```text
external/Object-Placement-Assessment-Dataset-OPA/
external/Object-Placement-Assessment-Dataset-OPA/eval_opascore/checkpoints/simopa.pth
.model-packages/
```

Install local packages if `.model-packages/` is missing:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' -m pip install --target .model-packages --no-deps -r experiments\requirements-model-min.txt
```

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_simopa_smoke.py
```

Known issue:

- The upstream `eval_opascore/simopa.py` main block hardcodes `cuda:1`; this project wrapper uses `cuda:0` or CPU explicitly.
- The current torch/numpy binding in `study` rejects `torch.from_numpy(...)`, so the wrapper builds tensors from Pillow pixel lists without numpy.

Outputs:

```text
report/logs/opa_baseline_smoke.txt
report/logs/opa_baseline_smoke_case0.txt
report/tables/opa_baseline_scores.csv
```

## Dataset Audit

After downloading the full OPA dataset to `assets/datasets/opa/raw/new_OPA`, run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\audit_opa_dataset.py
```

Outputs:

```text
assets/datasets/opa/splits/smoke_100.csv
report/tables/opa_sample_audit.csv
report/tables/opa_smoke_scores_from_dataset.csv
```

Current audit result:

- 100 usable test samples.
- 50 positive and 50 negative.
- Composite/mask pairs are readable and have matching dimensions.

## API Smoke

After the FastAPI dependencies are installed in `.venv`, run:

```powershell
.\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py
```

This starts a temporary FastAPI server, posts one real multipart request, routes candidate scoring through `server/scorer.py`, and then shuts the server down.

Outputs:

```text
report/logs/api_simopa_smoke.txt
report/tables/api_simopa_smoke.csv
```

Current result on `opa_test_001`:

- `model_version=simopa-rgb-mask-v1`
- Top 3 scores: `0.998`, `0.8495`, `0.6471`
- API runtime: about 3.7 seconds with subprocess model loading.
