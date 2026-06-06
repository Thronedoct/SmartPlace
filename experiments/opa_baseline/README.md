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

To run the same API smoke through the persistent worker mode:

```powershell
$env:SMARTPLACE_API_SMOKE_MODE='simopa-worker'
$env:SMARTPLACE_API_SMOKE_PORT='8012'
.\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py
```

Outputs:

```text
report/logs/api_simopa_smoke.txt
report/tables/api_simopa_smoke.csv
report/logs/api_simopa_worker_smoke.txt
report/tables/api_simopa_worker_smoke.csv
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

## 50-Case Candidate Ranking

Run:

```powershell
.\.venv\Scripts\python.exe experiments\opa_baseline\run_candidate_ranking.py --positive-count 25 --negative-count 25 --report-csv assets\datasets\opa\splits\report_50.csv --ranking-csv report\tables\candidate_ranking_v2_50.csv --summary-csv report\tables\opa_50_case_summary.csv --log-path report\logs\candidate_ranking_v2_50.txt --run-name "SmartPlace candidate ranking v2 50-case"
```

This expands the candidate-ranking evidence to 25 positive and 25 negative OPA cases.

Outputs:

```text
assets/datasets/opa/splits/report_50.csv
report/logs/candidate_ranking_v2_50.txt
report/tables/candidate_ranking_v2_50.csv
report/tables/opa_50_case_summary.csv
```

Current result:

- 50 cases.
- 650 candidate scores.
- 22 of 25 positive cases have the OPA labeled position ranked in Top 3.
- 25 of 25 negative OPA labeled positions are rejected with score below `0.45`.
- `opa_test_002`, `opa_test_012`, and `opa_test_023` are high-score boundary cases where the labeled position is plausible but outside Top 3 because other candidates saturate near `1.0`.

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

## Robustness Ablation

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_robustness_ablation.py
```

This tests five representative cases under controlled perturbations:

- mask erosion and dilation.
- candidate left/right/up/down shifts by `0.03` normalized units.
- candidate scale down/up by `10%`.

Outputs:

```text
report/logs/robustness_ablation.txt
report/tables/robustness_ablation.csv
```

Current result:

- 5 representative cases.
- 45 SimOPA score calls.
- Mean absolute score delta: `0.0820`.
- Max absolute score delta: `0.9455`.
- 5 perturbations change the three-tier label.
- `opa_test_002` remains high under small perturbations, supporting the score-saturation boundary analysis.
- `opa_test_059` remains near `0.0`, supporting the clear rejection case.

## Lite Mode Comparison

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_lite_mode_comparison.py
```

This compares the existing 50-case `simopa-full` evidence with a real `simopa-lite` run. Lite mode uses the same SimOPA checkpoint, but scores a smaller candidate budget, so it is an application-level inference mode rather than a newly trained lightweight network.

Outputs:

```text
report/logs/lite_mode_comparison.txt
report/tables/lite_mode_comparison.csv
```

Current result:

- 50 cases.
- Full score calls: `650`; lite score calls: `350`.
- Score-call reduction: `46.15%`.
- Top 1 matches: `45/50`.
- Mean Top 3 overlap ratio: `0.8800`.
- Assessment matches: `50/50`.
- End-to-end speedup: about `1.02x`, showing that subprocess model loading dominates current runtime.

## Persistent Worker Comparison

Run:

```powershell
& 'D:\DevTools\Anaconda\envs\study\python.exe' experiments\opa_baseline\run_worker_comparison.py
```

This compares the existing 50-case subprocess SimOPA evidence with `simopa-worker`, a JSONL worker that loads the same SimOPA checkpoint once and reuses it across scoring requests.

Outputs:

```text
report/logs/persistent_worker_comparison.txt
report/tables/persistent_worker_comparison.csv
```

Current result:

- 50 cases.
- Score calls stay the same: `650` vs `650`.
- Subprocess elapsed time: `168.6s`.
- Persistent worker elapsed time: `23.4s`.
- Speedup: about `7.2x`.
- Top 1 matches: `50/50`.
- Mean Top 3 overlap ratio: `1.0000`.
- Assessment matches: `50/50`.

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

- 12 runtime rows covering mock, SimOPA smoke, FastAPI smoke, FastAPI worker smoke, 18-case ranking, RGB/mask ablation, calibration/dedup, occlusion explainability, 50-case ranking, robustness ablation, full-vs-lite comparison, and persistent worker comparison.
- 12 model-change rows: all 12 evidence items completed.
