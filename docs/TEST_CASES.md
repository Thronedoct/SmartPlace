# 测试案例记录

所有验证案例统一记录在本文档中。截图、原始图片或生成结果建议放在 `assets/` 或 `report/` 目录下。

最终报告中不要只放 mock 案例。mock 案例用于工程占位，真实模型接入后需要补充 OPA/libcom 或改造模型的案例记录。

| ID | 背景类型 | 前景物体 | 候选类型 | 模型版本 | 分数 | 系统排序 | 人工判断 | 结果 | 备注 |
|---|---|---|---|---|---:|---:|---|---|---|
| T001 | 桌面 | 杯子 | 合理支撑位置 | mock-v0 | 0.86 | 1 | 合理 | 通过 | 阶段 0 占位案例。 |
| T002 | 地面 | 椅子 | 尺度偏大 | mock-v0 | 0.61 | 2 | 勉强可接受 | 待复查 | 阶段 0 占位案例。 |
| T003 | 墙面 | 植物 | 悬空或缺少支撑 | mock-v0 | 0.28 | 3 | 不合理 | 失败 | 阶段 0 占位案例。 |
| OPA001-R1 | OPA/cow | cow | 标注附近合理位置 | simopa-rgb-mask-v1 | 0.998 | 1 | 合理 | 通过 | API smoke `opa_test_001`，见 `report/tables/api_simopa_smoke.csv`。 |
| OPA001-R2 | OPA/cow | cow | 右侧可接受位置 | simopa-rgb-mask-v1 | 0.8495 | 2 | 合理/可接受 | 通过 | 同一请求候选池排序结果。 |
| OPA001-R3 | OPA/cow | cow | 上方备选位置 | simopa-rgb-mask-v1 | 0.6471 | 3 | 可接受 | 待复查 | 同一请求候选池排序结果。 |

## 最终覆盖要求

最终项目至少准备 18 组案例，覆盖：

- 桌面或台面场景。
- 地面场景。
- 墙面、架子或柜体场景。
- 户外场景。
- 明显合理的位置。
- 明显错误的位置。
- 边界越界或尺度不合理的位置。

## 每个重点案例建议保存的证据

- 原始背景图。
- 前景物体图。
- Top 3 候选展示截图。
- Web 页面截图或演示录屏片段。
- 后端模型推理日志。
- 模型评分表。
- 人工判断。
- `request_id`、`model_version`、`runtime_ms`。
- 如果结果不好，需要写清失败原因。

## 高分验证表格

真实模型接入后至少准备这些表格：

| 表格 | 位置 | 用途 |
|---|---|---|
| 候选排序表 | `report/tables/candidate_ranking_v1.csv` | 说明 Top 3 排序是否符合人工判断。 |
| RGB vs RGB+mask 对比表 | `report/tables/rgb_vs_mask_comparison.csv` | 证明本体类模型改动的效果和限制。 |
| 分数校准与去重表 | `report/tables/score_calibration_v1.csv` | 解释分数饱和和重复候选问题。 |
| 推理耗时表 | `report/tables/inference_runtime.csv` | 证明本地推理可运行，并比较不同模型版本。 |
| 模型改动说明表 | `report/tables/model_change_summary.csv` | 统一说明输入适配、输出适配、排序、校准、解释和轻量模式。 |
| 失败案例表 | `report/tables/failure_cases.csv` | 说明系统边界和失败原因。 |
| 遮挡解释表 | `report/tables/occlusion_explainability_v1.csv` | 证明模型对局部区域有可解释响应。 |

## 阶段 0 工程验证

| ID | 验证内容 | 命令或方式 | 结果 | 备注 |
|---|---|---|---|---|
| V001 | mock 推荐模块单元测试 | `python -m unittest server.test_recommender` | 通过 | 验证 PNG 尺寸解析、候选数量和尺度字段。 |
| V002 | 后端 Python 语法检查 | `python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py server/scorer.py server/test_recommender.py` | 通过 | 验证 FastAPI 入口、标准库入口、scorer 边界和推荐模块可编译。 |
| V003 | Web 前端语法检查 | `node --check web/app.js` | 通过 | 验证 Web 工作台脚本可解析。 |
| V004 | scorer 边界单元测试 | `python -m unittest server.test_recommender` | 通过 | 验证 `score_candidate_template` 和 `score_composite` mock 边界。 |
| V005 | FastAPI multipart 推荐接口冒烟 | `POST /api/place/recommend` | 通过 | 使用课程样例图返回 3 个候选，最佳分数 0.86，背景尺寸解析为 640x427。 |
| V006 | OPA SimOPA baseline 冒烟 | `python experiments/opa_baseline/run_simopa_smoke.py` | 通过 | `composite_1/mask_1` 得分 1.0，`composite_0/mask_0` 得分 0.0，CUDA 设备为 `cuda:0`。 |
| V007 | OPA 全量数据集审计 | `python experiments/opa_baseline/audit_opa_dataset.py` | 通过 | `new_OPA` 中抽取 100 条 test 样例，正负各 50，composite/mask 全部可读且尺寸匹配。 |
| V008 | OPA 数据集样例评分 | `run_simopa_smoke.py` | 通过 | 2 个正例得分 1.0，2 个负例得分 0.0，结果写入 `report/tables/opa_smoke_scores_from_dataset.csv`。 |
| V009 | FastAPI + SimOPA multipart 推荐接口冒烟 | `.\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py` | 通过 | health 返回 `scorer_mode=simopa`；`opa_test_001` Top 3 分数为 0.998、0.8495、0.6471。 |
| V010 | 18 组 OPA 候选排序实验 | `.\.venv\Scripts\python.exe experiments\opa_baseline\run_candidate_ranking.py` | 通过 | 18 组、234 条候选评分；正例 8/9 高分且进 Top 3，负例 9/9 的 OPA 标注坏位置得分 0.0。 |
| V011 | RGB/mask ablation | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_rgb_mask_comparison.py` | 通过 | 234 条候选；object mask vs blank mask 平均绝对差异 0.3487，Top 3 成员变化 56 条，见 `report/tables/rgb_vs_mask_comparison.csv`。 |
| V012 | 分数校准和 IoU 去重 | `python experiments\opa_baseline\run_score_calibration.py` | 通过 | 234 条候选；温度缩放后生成校准分数，IoU 去重移除 11 条重复候选；`opa_test_002` 保留为分数饱和边界案例。 |
| V013 | 代表案例图和失败/边界表 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_case_gallery.py` | 通过 | 生成 5 组成功/边界/负例案例图，写入 `report/tables/failure_cases.csv` 和 `report/screenshots/cases/`。 |
| V014 | 遮挡解释实验 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_occlusion_explainability.py` | 通过 | 5 组代表案例，6x6 遮挡网格；平均最大分数下降 0.5472，热力图写入 `report/screenshots/explainability/`。 |
