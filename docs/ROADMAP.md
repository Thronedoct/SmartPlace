# SmartPlace 路线图

本文是项目路线、当前状态、分工和短期任务的唯一维护入口。不要再新增单独的阶段状态、高分路线或下一步文档。

保留的长期文档只有：

| 文档 | 用途 |
|---|---|
| `README.md` | 项目简介、运行方式、文档入口 |
| `docs/ROADMAP.md` | 路线、状态、分工、下一步 |
| `docs/API.md` | Web 与 FastAPI 后端接口 |
| `docs/model_plan.md` | 模型细节、参考源码、实验方案 |
| `docs/TEST_CASES.md` | 测试案例、验证记录、证据表 |

## 项目定位

SmartPlace 选择课程方向 A：智能物体放置与合成图质量评价。

交付形态是 Web 工作台 + FastAPI 本地推理服务，不做 Android 端。`OPAAndroidDemoSimp/` 只作为老师提供的参考 Demo 和素材来源。

主线目标：

```text
背景图 + 前景图 + mask
-> 后端生成候选位置
-> SimOPA / 改造模型逐候选评分
-> 返回 Top 3、分数、标签、模型版本和耗时
-> Web 展示候选框与运行证据
```

## 当前状态

已经完成：

- Web 工作台可上传背景图、前景图和可选 mask。
- FastAPI 后端支持 `SMARTPLACE_SCORER=mock`、`SMARTPLACE_SCORER=simopa`、`SMARTPLACE_SCORER=simopa-lite` 和 `SMARTPLACE_SCORER=simopa-worker`。
- OPA/SimOPA 权重已本地跑通，`model_version=simopa-rgb-mask-v1`。
- OPA 全量数据集位于 `assets/datasets/opa/raw/new_OPA`，raw 数据不提交 Git。
- `smoke_100.csv` 已审计：100 条 test 样例可读，正负各 50。
- API smoke 已跑通：`opa_test_001` Top 3 分数为 `0.998 / 0.8495 / 0.6471`。
- 18 组候选排序实验已完成：9 正例、9 负例、234 条候选评分。
- 50 组扩展候选排序实验已完成：25 正例、25 负例、650 条候选评分；正例 22/25 的 OPA 标注位置进 Top 3，负例 25/25 被低分拒绝。
- 100 组 worker 候选排序实验已完成：50 正例、50 负例、1300 条候选评分；正例 44/50 的 OPA 标注位置进 Top 3，负例 50/50 被低分拒绝。
- RGB/mask ablation 已完成：234 条候选中，object mask 与 blank mask 的平均绝对差异为 `0.3487`，Top 3 成员变化 56 条。
- 分数校准和 IoU 去重已完成：温度缩放后生成 `score_calibration_v1.csv`，IoU 去重移除 11 条重复候选；`opa_test_002` 保留为分数饱和边界案例。
- 代表案例图已完成：5 组成功/边界/负例案例写入 `failure_cases.csv`，案例图位于 `report/screenshots/cases/`。
- 遮挡解释实验已完成：5 组代表案例生成 `occlusion_explainability_v1.csv` 和热力图，平均最大分数下降为 `0.5472`。
- 鲁棒性 ablation 已完成：5 个代表案例、45 次扰动评分；平均绝对分数变化 `0.0820`，5 条扰动造成三档标签变化。
- 轻量推理对比已完成：`simopa-lite` 将 50 组评测的评分调用从 650 次降到 350 次，Top 1 一致 45/50，assessment 一致 50/50；端到端加速约 `1.02x`，说明当前主要瓶颈是每个 case 的子进程模型加载。
- 常驻 SimOPA worker 已完成：同样 50 组、650 次评分调用，subprocess 模式耗时 `168.6s`，worker 模式耗时 `23.4s`，Top 1、Top 3 和 assessment 全部一致。
- LightOPA tiny 轻量模型探索已完成：4 通道小 CNN 使用 2,000 条 OPA train 样例训练、500 条 test 样例验证；最佳 epoch 验证准确率 `0.65`，ROC-AUC `0.6761`，平均验证推理 `12.36ms/sample`。该模型作为轻量 baseline，不替代主线 `simopa-worker`。
- 运行耗时表和模型改动说明表已完成：`inference_runtime.csv` 汇总 14 个运行阶段，`model_change_summary.csv` 汇总 13 个已完成改动。
- Web 工作台已支持内置案例加载、当前结果 JSON/CSV 导出、可信度/失败提示、解释热力图入口、前端美化和课堂演示模式。

当前候选排序结论：

- 正例 8/9 的 OPA 标注位置高分且进入 Top 3。
- 负例 9/9 的 OPA 标注坏位置得分为 `0.0`。
- 扩展到 100 组后，正例 44/50 进 Top 3，负例 50/50 低分拒绝。
- `opa_test_002`、`opa_test_012`、`opa_test_023` 是边界案例：标注位置高分，但多个候选也接近 `1.0`，说明 SimOPA 分数有饱和问题，需要做校准或候选去重。

## 高分路线

优先级从高到低：

1. **真实模型闭环**：Web -> FastAPI -> SimOPA -> Top 3。
2. **候选排序证据**：18 组案例、候选池评分、Top 3 排序表。
3. **模型本体类改动**：RGB/mask 对比或 mask ablation，证明 mask 对评分有影响。
4. **分数可信度**：分数校准、候选去重、三档标签阈值说明。
5. **案例展示**：3-5 组 Web 截图，包含成功、拒绝、失败/边界案例。
6. **解释性和可靠性加分**：遮挡实验、热力图和鲁棒性扰动分析。

不作为当前主线：

- Android 接入。
- TopNet 主线接入，但可做附录级对比。
- FOPAHeatMapModel 替代候选生成，但可做附录级对比。
- 大规模 fine-tune。
- 公网部署。

## 下一步

下一阶段目标从“稳交付”升级为“高标准完整应用”：继续丰富项目本体，让 Web 应用、后端推理、模型对比、运行证据和解释性材料形成一套可以现场演示、可以量化对比、可以回答追问的闭环。

工程侧优先顺序：

1. **Web 演示验收**：用桌面和移动视口验证内置案例、演示模式、Top 3 面板、可信度提示、解释热力图入口和 JSON/CSV 导出。
2. **证据材料交接**：把 Web 截图、导出样例、runtime 表和模型改动说明表交给负责报告/PPT 的队友。

模型侧升级顺序：

3. **LightOPA 后续增强**：tiny LightOPA baseline 已完成，证明可以训练真实轻量 scorer。若继续卷模型本体，可以升级到 ResNet18/MobileNetV3 级别 LightOPA scorer，与 `simopa-worker` 比较速度、排序质量和失败案例。
4. **可选更大规模验证**：100 组候选排序已经完成；如还需要更强统计证据，可以继续扩大到全量测试子集，但这不再是当前主线必需项。

交付材料分工：

6. 最终报告、PPT、演示录屏、AI 辅助说明和小组分工说明交给队友整理。工程侧先把脚本、表格、日志、截图和 Web 演示入口准备好，队友基于这些证据做最终排版和讲稿。
7. FOPA/TopNet 只做附录级对比，不替代当前主线；大规模 fine-tune、Android 和公网部署仍不作为当前主线。

## 证据清单

当前已有：

```text
report/logs/api_simopa_smoke.txt
report/logs/api_simopa_worker_smoke.txt
report/logs/candidate_ranking_v1.txt
report/logs/candidate_ranking_v2_50.txt
report/logs/candidate_ranking_v2_100.txt
report/logs/rgb_vs_mask_comparison.txt
report/logs/score_calibration_v1.txt
report/tables/api_simopa_smoke.csv
report/tables/api_simopa_worker_smoke.csv
report/tables/candidate_ranking_v1.csv
report/tables/candidate_ranking_v2_50.csv
report/tables/candidate_ranking_v2_100.csv
report/tables/opa_18_case_summary.csv
report/tables/opa_50_case_summary.csv
report/tables/opa_100_case_summary.csv
report/tables/opa_sample_audit.csv
report/tables/opa_smoke_scores_from_dataset.csv
report/tables/rgb_vs_mask_comparison.csv
report/tables/score_calibration_v1.csv
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
report/logs/occlusion_explainability_v1.txt
report/logs/evidence_summary.txt
report/tables/failure_cases.csv
report/tables/occlusion_explainability_v1.csv
report/logs/robustness_ablation.txt
report/logs/lite_mode_comparison.txt
report/logs/persistent_worker_comparison.txt
report/logs/lightopa_tiny_training.txt
report/tables/robustness_ablation.csv
report/tables/lite_mode_comparison.csv
report/tables/persistent_worker_comparison.csv
report/tables/lightopa_tiny_metrics.csv
report/screenshots/cases/
report/screenshots/explainability/
```

还需要补：

```text
report/videos/
```

## 分工

- 成员 A：模型改造、模型实验、RGB/mask 对比、轻量模型/轻量推理、鲁棒性 ablation、解释实验。
- 成员 B：FastAPI 后端、候选排序管线、模型调用证据、运行耗时统计、导出接口。
- 成员 C：Web 展示、前端美化、内置样例、可信度提示、解释热力图入口。
- 队友/材料负责人：最终报告、PPT、演示录屏、AI 辅助说明、小组分工说明和最终排版。

工程侧每完成一块，都要留下可复用证据：脚本命令、输出表、日志、截图和一句话结论。最终材料负责人直接基于这些证据写报告和 PPT，工程侧不把主要时间花在排版上。

## GitHub 流程

- `main`：稳定可展示版本。
- `codex/*` 或 `feature/*`：功能分支。
- 每块工作开 PR，先保持 Draft，验证通过后再合并。
- 权重、raw 数据、external 源码和 `.model-packages/` 不提交。
- GitHub CLI 优先使用沙箱外 `gh`。沙箱内 `gh` 的 token 容易失效，日常开 PR、查 review、合并 PR 走沙箱外授权好的 `gh`；不要把 GitHub PAT 或 API key 发到聊天里。

推荐本机登录方式：

```powershell
gh auth login -h github.com --web --git-protocol https
gh auth setup-git
gh auth status
```

如果必须使用 PAT，先在 GitHub 创建只授权 `Thronedoct/SmartPlace` 的 fine-grained token，然后在本机 PowerShell 中通过 `Read-Host` 输入，不要写进文档、脚本、日志或对话记录：

```powershell
$token = Read-Host "Paste GitHub token"
$token | gh auth login -h github.com --with-token
Remove-Variable token
gh auth setup-git
gh auth status
```

合并前至少检查：

```powershell
python -m unittest server.test_recommender
python -m py_compile server/app.py server/recommender.py server/scorer.py
node --check web/app.js
```

模型实验 PR 还要附对应脚本命令和 `report/` 输出表。
