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

暂缓：

- Android 接入。
- TopNet 主线接入。
- FOPAHeatMapModel 替代候选生成。
- 大规模 fine-tune。
- 公网部署。

## 下一步

最近三步：

1. 选 3-5 组代表案例，做 Web 截图和失败/边界分析。
2. 做遮挡实验或 Grad-CAM，补解释性证据。
3. 汇总报告、PPT、演示录屏和分工说明。

随后做：

4. 如果时间允许，再做轻量 fine-tune 或 FOPA 候选生成对比。

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
```

还需要补：

```text
report/tables/failure_cases.csv
report/screenshots/
report/videos/
```

## 分工

- 成员 A：模型改造、模型实验、RGB/mask 对比、解释实验。
- 成员 B：FastAPI 后端、候选排序管线、模型调用证据。
- 成员 C：Web 展示、截图录屏、报告和 PPT 材料整合。

每个成员负责自己模块对应的报告和 PPT 内容，最终由成员 C 统一排版。

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
