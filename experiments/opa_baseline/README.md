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

## 18-Case Candidate Ranking

Run:

```powershell
.\.venv\Scripts\python.exe experiments\opa_baseline\run_candidate_ranking.py
```

This selects 9 positive and 9 negative cases from `assets/datasets/opa/splits/smoke_100.csv`. For each case, it scores the OPA labeled position plus 12 generated prior candidates with the SimOPA scorer and writes model-ranked evidence tables.

Outputs:

```text
assets/datasets/opa/splits/report_18.csv
report/logs/candidate_ranking_v1.txt
report/tables/candidate_ranking_v1.csv
report/tables/opa_18_case_summary.csv
```

Current result:

- 18 cases.
- 234 candidate scores.
- 8 of 9 positive cases have the OPA labeled position scored high and ranked in Top 3.
- 9 of 9 negative OPA labeled positions are rejected with score `0.0`.
- `opa_test_002` is a useful discussion case: the labeled position scores `0.9987`, but several generated candidates also saturate near `1.0`, so the labeled position ranks lower despite a high absolute score.

## RGB/Mask Ablation

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_rgb_mask_comparison.py
```

This reuses the 234 candidates from `candidate_ranking_v1.csv` and compares three scoring inputs:

- `score_rgb_mask`: normal SimOPA composite RGB plus object-shape mask.
- `score_bbox_mask`: same composite RGB plus only a coarse bounding-box mask.
- `score_blank_mask`: same composite RGB plus a blank mask channel as an RGB-only proxy.

Outputs:

```text
report/logs/rgb_vs_mask_comparison.txt
report/tables/rgb_vs_mask_comparison.csv
```

Current result:

- 234 candidate rows.
- Mean absolute delta between object mask and bbox mask: `0.0839`.
- Mean absolute delta between object mask and blank mask: `0.3487`.
- 29 candidates change by at least `0.05` against bbox mask.
- 136 candidates change by at least `0.05` against blank mask.
- Top 3 membership changes for 16 candidates against bbox mask and 56 against blank mask.

## Score Calibration and IoU Dedup

Run:

```powershell
python experiments\opa_baseline\run_score_calibration.py
```

This post-processes `candidate_ranking_v1.csv` with temperature scaling and IoU-NMS. It is meant as a reportable reliability analysis, not as a replacement for SimOPA training.

Outputs:

```text
report/logs/score_calibration_v1.txt
report/tables/score_calibration_v1.csv
```

Current result:

- 234 candidate rows.
- 97 high-saturated rows and 118 low-saturated rows.
- 11 candidates removed by IoU dedup.
- Raw Top 3 has duplicate boxes in 2 cases; dedup Top 3 has 0 duplicate cases.
- `opa_test_002` remains rank 10 after calibration and dedup, which makes it a useful score-saturation boundary case rather than a simple duplicate-candidate problem.

## Representative Case Gallery

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_case_gallery.py
```

This selects five report cases and renders three-panel images: OPA composite, raw SimOPA Top 3, and calibrated + dedup Top 3.

Outputs:

```text
report/tables/failure_cases.csv
report/screenshots/cases/
```

Current cases:

- `opa_test_001`: success with duplicate cleanup.
- `opa_test_002`: score-saturation boundary.
- `opa_test_006`: dedup success.
- `opa_test_052`: negative false-positive risk.
- `opa_test_059`: clear negative rejection.

## Occlusion Explainability

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_occlusion_explainability.py
```

This runs a 6x6 RGB occlusion sensitivity test on the five representative cases. The foreground mask is kept fixed while image cells are occluded, so the output explains which visual regions most affect the SimOPA score.

Outputs:

```text
report/logs/occlusion_explainability_v1.txt
report/tables/occlusion_explainability_v1.csv
report/screenshots/explainability/
```

Current result:

- 5 representative cases.
- Mean max score drop: `0.5472`.
- `opa_test_001`, `opa_test_002`, and `opa_test_052` show strong localized sensitivity.
- `opa_test_059` stays at score `0.0`, supporting the clear rejection case.

## Evidence Summary

Run:

```powershell
python experiments\opa_baseline\run_evidence_summary.py
```

This reads the existing experiment logs and tables, then writes one runtime table and one model-change summary table for report/PPT reuse. It does not rerun the heavy GPU experiments.

Outputs:

```text
report/logs/evidence_summary.txt
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
```

Current result:

- 7 runtime rows covering mock, SimOPA smoke, FastAPI smoke, candidate ranking, RGB/mask ablation, calibration/dedup, and occlusion explainability.
- 11 model-change rows: 8 completed evidence items and 3 planned high-standard upgrades.
