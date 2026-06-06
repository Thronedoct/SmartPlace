# SmartPlace Experiments

This directory contains reproducible experiment scripts and lightweight notes.
Large datasets, model weights, checkpoints, and generated media stay in ignored
data/model folders or in `report/`.

Long-term project direction lives in `docs/ROADMAP.md`; model-side rationale lives
in `docs/model_plan.md`. Keep this file as a concise experiment index.

## Current Tracks

| Directory | Status | Purpose |
|---|---|---|
| `opa_baseline/` | active, mainline | SimOPA smoke tests, API smoke tests, candidate ranking, RGB/mask ablation, calibration, case gallery, explainability, robustness, lite mode, worker comparison, and evidence summary. |
| `lightopa/` | active, exploratory | Tiny LightOPA 4-channel CNN baseline trained on a small OPA subset. It is model-level lightweight evidence, not a replacement for `simopa-worker`. |

## Main Evidence Outputs

```text
report/tables/candidate_ranking_v2_100.csv
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
report/tables/persistent_worker_comparison.csv
report/tables/lightopa_tiny_metrics.csv
report/screenshots/cases/
report/screenshots/explainability/
```

## Re-run Order

For final verification, use this order instead of rerunning every historical
experiment:

```powershell
python experiments\opa_baseline\run_evidence_summary.py
python -m unittest server.test_recommender
python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py server/scorer.py
node --check web/app.js
```

GPU-heavy experiments are documented in `experiments/opa_baseline/README.md` and
`experiments/lightopa/README.md`. Re-run them only when updating the corresponding
tables or logs.
