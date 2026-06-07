# SmartPlace 实验索引

本目录只放可复现实验脚本和轻量说明。大数据、模型权重、checkpoint、本地依赖缓存和生成媒体都放在 ignored 目录或 `report/` 中，不提交 Git。

长期路线见 `docs/ROADMAP.md`，模型细节见 `docs/model_plan.md`。本文只作为实验目录索引。

## 当前实验轨道

| 目录 | 状态 | 用途 |
|---|---|---|
| `opa_baseline/` | 主线 | SimOPA 冒烟、API 冒烟、候选排序、RGB/mask ablation、校准、案例图、解释性、鲁棒性、lite 模式、worker 对比和证据汇总。 |
| `lightopa/` | 探索 | tiny/residual 两个 4 通道 CNN 轻量模型 baseline。它们是模型侧补强证据，不替代 `simopa-worker`。 |

## 主要输出

```text
report/tables/candidate_ranking_v2_100.csv
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
report/tables/persistent_worker_comparison.csv
report/tables/lightopa_tiny_metrics.csv
report/tables/lightopa_residual_metrics.csv
report/tables/lightopa_model_comparison.csv
report/screenshots/cases/
report/screenshots/explainability/
```

## 最终验证

交付前优先运行：

```powershell
.\scripts\verify_core.ps1
```

GPU-heavy 实验已经有对应表格和日志。只有在更新实验结果时，才需要按 `experiments/opa_baseline/README.md` 或 `experiments/lightopa/README.md` 重新跑完整实验。
