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
- FastAPI 后端支持 `SMARTPLACE_SCORER=mock` 和 `SMARTPLACE_SCORER=simopa`。
- OPA/SimOPA 权重已本地跑通，`model_version=simopa-rgb-mask-v1`。
- OPA 全量数据集位于 `assets/datasets/opa/raw/new_OPA`，raw 数据不提交 Git。
- `smoke_100.csv` 已审计：100 条 test 样例可读，正负各 50。
- API smoke 已跑通：`opa_test_001` Top 3 分数为 `0.998 / 0.8495 / 0.6471`。
- 18 组候选排序实验已完成：9 正例、9 负例、234 条候选评分。
- RGB/mask ablation 已完成：234 条候选中，object mask 与 blank mask 的平均绝对差异为 `0.3487`，Top 3 成员变化 56 条。
- 分数校准和 IoU 去重已完成：温度缩放后生成 `score_calibration_v1.csv`，IoU 去重移除 11 条重复候选；`opa_test_002` 保留为分数饱和边界案例。
- 代表案例图已完成：5 组成功/边界/负例案例写入 `failure_cases.csv`，案例图位于 `report/screenshots/cases/`。
- 遮挡解释实验已完成：5 组代表案例生成 `occlusion_explainability_v1.csv` 和热力图，平均最大分数下降为 `0.5472`。

当前候选排序结论：

- 正例 8/9 的 OPA 标注位置高分且进入 Top 3。
- 负例 9/9 的 OPA 标注坏位置得分为 `0.0`。
- `opa_test_002` 是边界案例：标注位置得分 `0.9987`，但多个候选也接近 `1.0`，说明 SimOPA 分数有饱和问题，需要做校准或候选去重。

## 高分路线

优先级从高到低：

1. **真实模型闭环**：Web -> FastAPI -> SimOPA -> Top 3。
2. **候选排序证据**：18 组案例、候选池评分、Top 3 排序表。
3. **模型本体类改动**：RGB/mask 对比或 mask ablation，证明 mask 对评分有影响。
4. **分数可信度**：分数校准、候选去重、三档标签阈值说明。
5. **案例展示**：3-5 组 Web 截图，包含成功、拒绝、失败/边界案例。
6. **解释性加分**：遮挡实验或 Grad-CAM。

不作为当前主线：

- Android 接入。
- TopNet 主线接入，但可做附录级对比。
- FOPAHeatMapModel 替代候选生成，但可做附录级对比。
- 大规模 fine-tune。
- 公网部署。

## 下一步

下一阶段目标从“稳交付”升级为“高标准完整应用”：继续丰富项目本体，让 Web 应用、后端推理、模型对比、运行证据和解释性材料形成一套可以现场演示、可以量化对比、可以回答追问的闭环。

工程侧优先顺序：

1. **运行证据补齐**：生成 `report/tables/inference_runtime.csv` 和 `report/tables/model_change_summary.csv`，记录真实模型、本地推理、候选排序、RGB/mask、校准、解释实验的耗时和改动类型。
2. **Web 结果导出**：在 Web 工作台增加导出当前推荐结果 JSON/CSV 的按钮，导出 `request_id`、`model_version`、`runtime_ms`、Top 3 分数、坐标和可信度提示。
3. **Web 内置样例加载**：提供成功、边界、负例误报、清晰拒绝等稳定演示案例，一键加载背景、前景、mask 和推荐参数。
4. **可信度/失败提示**：根据分数饱和、Top 3 分数差、候选重叠和低分情况显示“高可信推荐 / 需要人工复查 / 分数饱和 / 候选过于重叠”等提示。
5. **前端美化与易用性增强**：把 Web 工作台升级成更像完整产品的界面，优化桌面/移动布局、图像画布、候选框视觉层级、模型状态 badge、Top 3 面板、按钮反馈、空状态、加载态和错误态。
6. **前端演示增强**：增加课堂演示模式，突出模型状态、运行耗时、Top 3、解释热力图入口、导出证据和现场推理信息。

模型侧升级顺序：

7. **扩大验证规模**：从 18 组代表案例扩展到 50 或 100 组候选排序评测，输出 `candidate_ranking_v2_50.csv` 或 `candidate_ranking_v2_100.csv`，让结果不只依赖少量案例。
8. **轻量推理对比**：增加 `simopa-full` 与轻量模式对比。轻量模式第一版可减少候选数或复用轻量后处理；如果时间允许，再训练或适配一个 ResNet18/MobileNetV3 级别的轻量 scorer，输出耗时、排序和失败案例对比。
9. **鲁棒性 ablation**：在已有 object/bbox/blank mask 对比基础上，增加 mask 膨胀/腐蚀、尺度扰动、候选平移扰动等实验，输出 `robustness_ablation.csv`。
10. **解释性集成**：把离线遮挡热力图接入 Web 案例区，答辩时可以在应用内直接看到模型关注区域。

交付材料分工：

11. 最终报告、PPT、演示录屏、AI 辅助说明和小组分工说明交给队友整理。工程侧先把脚本、表格、日志、截图和 Web 演示入口准备好，队友基于这些证据做最终排版和讲稿。
12. FOPA/TopNet 只做附录级对比，不替代当前主线；大规模 fine-tune、Android 和公网部署仍不作为当前主线。

## 证据清单

当前已有：

```text
report/logs/api_simopa_smoke.txt
report/logs/candidate_ranking_v1.txt
report/logs/rgb_vs_mask_comparison.txt
report/logs/score_calibration_v1.txt
report/tables/api_simopa_smoke.csv
report/tables/candidate_ranking_v1.csv
report/tables/opa_18_case_summary.csv
report/tables/opa_sample_audit.csv
report/tables/opa_smoke_scores_from_dataset.csv
report/tables/rgb_vs_mask_comparison.csv
report/tables/score_calibration_v1.csv
report/logs/occlusion_explainability_v1.txt
report/tables/failure_cases.csv
report/tables/occlusion_explainability_v1.csv
report/screenshots/cases/
report/screenshots/explainability/
```

还需要补：

```text
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
report/tables/candidate_ranking_v2_50.csv
report/tables/lite_mode_comparison.csv
report/tables/robustness_ablation.csv
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

合并前至少检查：

```powershell
python -m unittest server.test_recommender
python -m py_compile server/app.py server/recommender.py server/scorer.py
node --check web/app.js
```

模型实验 PR 还要附对应脚本命令和 `report/` 输出表。
