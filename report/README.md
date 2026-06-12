# SmartPlace 交付证据索引

本文是给队友写报告、做 PPT、录屏时使用的证据索引。项目路线和当前状态只维护在 `docs/ROADMAP.md`，不要在这里再写一份路线图。

## 一句话主线

```text
Web 工作台
-> FastAPI 本地推理服务
-> simopa-worker 真实 OPA/SimOPA scorer
-> Top 3 放置候选
-> 可信度提示、校准去重、解释性、鲁棒性和运行时间证据
```

报告中的安全表述：

> SmartPlace 将 OPA/SimOPA 放置合理性评分模型封装成一个可交互的 Web 物体放置助手。最终演示使用 Web + FastAPI + `simopa-worker`；LightOPA tiny/residual 是额外的轻量模型 baseline，不替代主线 SimOPA。

不要把 Android 写成本项目主线。`OPAAndroidDemoSimp/` 只是课程提供的参考 Demo。

## 演示流程

启动最终演示服务：

```powershell
.\start_demo.ps1
```

如果队友机器上自动找不到 模型环境里的 Python：

```powershell
conda run -n <model-env> python -c "import sys; print(sys.executable)"
.\start_demo.ps1 -ModelPython "<path-to-model-python.exe>"
```

打开：

```text
http://127.0.0.1:8000/
```

推荐录屏顺序：

1. 展示页面右上角或 `/api/health`，确认 scorer 是 `simopa-worker`。
2. 加载内置案例 `opa_test_001`。
3. 点击 `运行本地推荐`。
4. 展示 Top 3 候选框、分数、标签、`request_id`、`model_version` 和 `runtime`。
5. 打开案例图和遮挡解释热力图。
6. 导出 JSON 和 CSV。
7. 切换 `演示模式`。
8. 再用 `opa_test_002` 或 `opa_test_059` 简短展示边界/拒绝案例。
9. 录屏结束后运行 `.\stop_demo.ps1`。

内置案例图片已经单独打包在 `assets/demo_cases/`，不依赖完整 OPA raw 数据集。

## 最重要的表格

模型侧答辩速查：`report/MODEL_DEFENSE_QA.md`。里面整理了模型工作、关键数字和老师可能追问的问题。

| 文件 | 报告里怎么用 |
|---|---|
| `report/tables/model_change_summary.csv` | 统一说明 14 项已完成的模型/工程改动。 |
| `report/tables/inference_runtime.csv` | 15 个阶段的运行耗时证据。 |
| `report/tables/candidate_ranking_v2_100.csv` | 100 组 OPA 案例、1300 条候选评分。 |
| `report/tables/opa_100_case_summary.csv` | 正例 44/50 标注位置进 Top 3，负例 50/50 低分拒绝。 |
| `report/tables/rgb_vs_mask_comparison.csv` | 证明 mask 输入会显著影响评分，object mask vs blank mask 平均差异 0.3487。 |
| `report/tables/score_calibration_v1.csv` | 说明温度校准和 IoU 去重如何缓解分数饱和/重复候选。 |
| `report/tables/occlusion_explainability_v1.csv` | 5 个代表案例的遮挡解释证据，平均最大分数下降 0.5472。 |
| `report/tables/robustness_ablation.csv` | mask、平移、尺度扰动下的鲁棒性证据。 |
| `report/tables/persistent_worker_comparison.csv` | worker 模式把 50 组排序从 168.6s 降到 23.4s，Top 3 保持一致。 |
| `report/tables/lightopa_model_comparison.csv` | residual LightOPA 相比 tiny LightOPA 有提升：ROC-AUC 0.6761 -> 0.7084。 |

## 最重要的日志

| 文件 | 用途 |
|---|---|
| `report/logs/api_simopa_worker_smoke.txt` | FastAPI + worker 真实推理冒烟证据。 |
| `report/logs/candidate_ranking_v2_100.txt` | 100 组候选排序摘要。 |
| `report/logs/persistent_worker_comparison.txt` | subprocess 与 worker 的耗时对比。 |
| `report/logs/evidence_summary.txt` | 运行耗时表和模型改动表的汇总确认。 |
| `report/logs/lightopa_residual_training.txt` | LightOPA residual 训练日志。 |

## 图片素材

```text
report/screenshots/web/              # 最终 Web 界面截图
report/screenshots/cases/            # 5 个代表案例图
report/screenshots/explainability/   # 5 张遮挡解释热力图
```

推荐 PPT 映射：

| 页面主题 | 图片 |
|---|---|
| Web 工作台 | `report/screenshots/web/web_demo_desktop.png` |
| 课堂演示模式 | `report/screenshots/web/web_demo_presentation.png` |
| 移动端适配 | `report/screenshots/web/web_demo_mobile.png` |
| 成功案例 | `report/screenshots/cases/opa_test_001_case_panel.png` |
| 分数饱和边界 | `report/screenshots/cases/opa_test_002_case_panel.png` |
| 清晰拒绝案例 | `report/screenshots/cases/opa_test_059_case_panel.png` |
| 模型解释 | `report/screenshots/explainability/*_occlusion_heatmap.png` |

刷新 Web 截图：

```powershell
.\scripts\capture_web_demo.ps1
```

## 报告口径

可以说：

```text
我们没有声称重写 SimOPA backbone，而是完成了 OPA/SimOPA 的应用适配：
候选排序、分数校准、IoU 去重、mask ablation、鲁棒性扰动、
遮挡解释、常驻 worker 服务化和 LightOPA 轻量 baseline。
```

不要说：

```text
我们从零重建了 SimOPA。
Android Demo 是主程序。
simopa-lite 是新训练的轻量网络。
LightOPA 已经替代 SimOPA。
```

## 材料侧剩余任务

```text
最终报告 PDF
PPT
演示录屏，放入 report/videos/
AI 辅助说明
成员分工说明
```

录屏完成后检查：

```powershell
.\scripts\verify_handoff_assets.ps1 -RequireVideos
.\scripts\export_handoff_package.ps1 -RequireVideos
```

没有录屏时，工程交付包可以先这样导出：

```powershell
.\scripts\export_handoff_package.ps1
```

导出结果位于 ignored 目录：

```text
report/exports/smartplace_handoff.zip
```

导出包故意不包含 raw 数据、模型权重、external 源码、虚拟环境和本地依赖缓存。

如果队友需要自己运行项目，而不是只写材料，使用项目运行包：

```powershell
.\scripts\export_full_project_package.ps1
```

项目运行包位于：

```text
report/exports/smartplace_project_no_dataset.zip
```

默认包包含源码、模型权重、external 参考源码、本地模型依赖缓存和 5 组内置 demo 小图，但不包含 4.6GB OPA raw 数据集。详细说明见根目录 `HANDOFF_FULL_PROJECT.md`。
