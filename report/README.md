# SmartPlace Evidence Handoff

This file is the handoff index for teammates who will write the final report, slides, and demo recording. It is not a roadmap. Project direction and task status stay in `docs/ROADMAP.md`.

## Main Story

Use this as the report/PPT storyline:

```text
Web workspace
-> FastAPI local inference service
-> simopa-worker real OPA/SimOPA scorer
-> Top 3 placement candidates
-> confidence prompts, calibration, dedup, explainability, and runtime evidence
```

Primary claim:

> SmartPlace turns the OPA/SimOPA placement assessment model into an interactive object-placement recommendation workflow. The live demo uses Web + FastAPI + `simopa-worker`; LightOPA tiny/residual are supplementary lightweight-model baselines, not replacements for SimOPA.

Do not present Android as an active deliverable. `OPAAndroidDemoSimp/` is only a course-provided reference.

## Demo Script

Run the backend in the stable live-demo mode:

```powershell
$env:SMARTPLACE_SCORER='simopa-worker'
$env:SMARTPLACE_MODEL_PYTHON='<path-to-study-conda-env-python.exe>'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

To find the `study` environment Python path on a teammate machine:

```powershell
conda run -n study python -c "import sys; print(sys.executable)"
```

Open:

```text
http://127.0.0.1:8000/
```

Recommended recording flow:

1. Show `/api/health` or the Web scorer badge to prove the service is using `simopa-worker`.
2. Load `opa_test_001` from the built-in cases.
3. Click `运行本地推荐`.
4. Show Top 3 boxes, score tiers, `request_id`, `model_version`, and `runtime`.
5. Open the confidence panel links for the case panel and occlusion heatmap.
6. Export JSON and CSV results.
7. Toggle `演示模式`.
8. Repeat briefly with `opa_test_002` or `opa_test_059` to show boundary/rejection behavior.

## Key Tables

| Artifact | One-line conclusion |
|---|---|
| `report/tables/model_change_summary.csv` | Single source of truth for 14 completed engineering/model changes. |
| `report/tables/inference_runtime.csv` | Runtime evidence across 15 stages, including SimOPA, worker, LightOPA, and ablations. |
| `report/tables/candidate_ranking_v2_100.csv` | 100 OPA cases and 1300 candidate scores with `simopa-worker`. |
| `report/tables/opa_100_case_summary.csv` | 44/50 positive cases put the OPA label in Top 3; 50/50 negative cases are rejected. |
| `report/tables/rgb_vs_mask_comparison.csv` | Mask input matters: object mask vs blank mask mean absolute score difference is 0.3487. |
| `report/tables/score_calibration_v1.csv` | Temperature scaling and IoU dedup reduce duplicate/saturated Top 3 explanations. |
| `report/tables/occlusion_explainability_v1.csv` | Five representative cases have occlusion sensitivity evidence; average max score drop is 0.5472. |
| `report/tables/robustness_ablation.csv` | Five representative cases, 45 perturbation scores, average absolute score change 0.0820. |
| `report/tables/lite_mode_comparison.csv` | `simopa-lite` reduces score calls from 650 to 350 while preserving 50/50 assessment consistency. |
| `report/tables/persistent_worker_comparison.csv` | Worker mode reduces 50-case ranking from 168.6s to 23.4s with identical Top 3 overlap. |
| `report/tables/lightopa_model_comparison.csv` | Residual LightOPA improves over tiny LightOPA: accuracy 0.65 -> 0.6717, ROC-AUC 0.6761 -> 0.7084. |

## Key Logs

| Artifact | Use |
|---|---|
| `report/logs/api_simopa_worker_smoke.txt` | FastAPI smoke evidence for worker-backed inference. |
| `report/logs/candidate_ranking_v2_100.txt` | 100-case ranking summary. |
| `report/logs/persistent_worker_comparison.txt` | Full-vs-worker runtime comparison log. |
| `report/logs/evidence_summary.txt` | Confirms runtime rows and model-change rows. |
| `report/logs/lightopa_residual_training.txt` | Training log for the stronger lightweight baseline. |

## Figures

Use these for report and slides:

```text
report/screenshots/cases/
report/screenshots/explainability/
```

Suggested slide mapping:

| Slide topic | Figure source |
|---|---|
| Success case | `report/screenshots/cases/opa_test_001_case_panel.png` |
| Boundary/saturation case | `report/screenshots/cases/opa_test_002_case_panel.png` |
| Clear rejection case | `report/screenshots/cases/opa_test_059_case_panel.png` |
| Explainability | `report/screenshots/explainability/*_occlusion_heatmap.png` |

## Report Wording

Safe model wording:

> We did not claim to rewrite the SimOPA backbone. We adapted the OPA/SimOPA scorer for a Web placement assistant, added candidate ranking, score calibration, IoU dedup, mask ablation, robustness checks, occlusion explainability, persistent worker serving, and lightweight LightOPA baselines.

Avoid saying:

```text
We rebuilt SimOPA from scratch.
The Android demo is the main app.
simopa-lite is a newly trained lightweight network.
LightOPA replaces SimOPA.
```

## Teammate TODO

Materials team should still add:

```text
report/videos/
final report PDF
PPT deck
AI assistance statement
member contribution statement
```

Engineering evidence is already available in scripts, tables, logs, and screenshots. The final material work should focus on narration, formatting, and recording.
