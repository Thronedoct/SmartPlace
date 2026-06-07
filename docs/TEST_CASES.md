# 测试案例记录

所有验证案例统一记录在本文档中。截图、原始图片或生成结果建议放在 `assets/` 或 `report/` 目录下。

最终报告中不要只放 mock 案例。mock 案例仅用于说明早期接口形态，主报告应使用 OPA/SimOPA、LightOPA 和 Web 演示证据。

| ID | 背景类型 | 前景物体 | 候选类型 | 模型版本 | 分数 | 系统排序 | 人工判断 | 结果 | 备注 |
|---|---|---|---|---|---:|---:|---|---|---|
| T001 | 桌面 | 杯子 | 合理支撑位置 | mock-v0 | 0.86 | 1 | 合理 | 通过 | 历史 mock 占位案例，仅用于说明早期接口形态。 |
| T002 | 地面 | 椅子 | 尺度偏大 | mock-v0 | 0.61 | 2 | 勉强可接受 | 待复查 | 历史 mock 占位案例，仅用于说明早期接口形态。 |
| T003 | 墙面 | 植物 | 悬空或缺少支撑 | mock-v0 | 0.28 | 3 | 不合理 | 失败 | 历史 mock 占位案例，仅用于说明早期接口形态。 |
| OPA001-R1 | OPA/cow | cow | 标注附近合理位置 | simopa-rgb-mask-v1 | 0.998 | 1 | 合理 | 通过 | API smoke `opa_test_001`，见 `report/tables/api_simopa_smoke.csv`。 |
| OPA001-R2 | OPA/cow | cow | 右侧可接受位置 | simopa-rgb-mask-v1 | 0.8495 | 2 | 合理/可接受 | 通过 | 同一请求候选池排序结果。 |
| OPA001-R3 | OPA/cow | cow | 上方备选位置 | simopa-rgb-mask-v1 | 0.6471 | 3 | 可接受 | 待复查 | 同一请求候选池排序结果。 |

## 最终覆盖要求

当前项目已经完成 18/50/100 组候选排序评测，超过最低覆盖要求。最终报告选例时仍应覆盖：

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

当前已有这些高分验证表格：

| 表格 | 位置 | 用途 |
|---|---|---|
| 候选排序表 | `report/tables/candidate_ranking_v1.csv` | 说明 Top 3 排序是否符合人工判断。 |
| 扩展候选排序表 | `report/tables/candidate_ranking_v2_50.csv` 和 `candidate_ranking_v2_100.csv` | 用更多案例验证排序稳定性。 |
| RGB vs RGB+mask 对比表 | `report/tables/rgb_vs_mask_comparison.csv` | 证明本体类模型改动的效果和限制。 |
| 分数校准与去重表 | `report/tables/score_calibration_v1.csv` | 解释分数饱和和重复候选问题。 |
| 推理耗时表 | `report/tables/inference_runtime.csv` | 证明本地推理可运行，并比较不同模型版本。 |
| 轻量模式对比表 | `report/tables/lite_mode_comparison.csv` | 比较 `simopa-full` 和 `simopa-lite` 候选预算模式的耗时、Top 1 一致性、Top 3 重合度和 assessment 一致性。 |
| 常驻 worker 对比表 | `report/tables/persistent_worker_comparison.csv` | 比较 subprocess SimOPA 和常驻 worker SimOPA 的耗时、Top 1 一致性、Top 3 重合度和 assessment 一致性。 |
| LightOPA tiny 指标表 | `report/tables/lightopa_tiny_metrics.csv` | 记录 4 通道 tiny CNN 轻量模型的训练规模、验证准确率、AUC、参数量和单样本推理耗时。 |
| LightOPA residual 指标表 | `report/tables/lightopa_residual_metrics.csv` | 记录 residual 4 通道 CNN 轻量模型的训练规模、验证准确率、AUC、参数量和单样本推理耗时。 |
| LightOPA 模型对比表 | `report/tables/lightopa_model_comparison.csv` | 对比 tiny 与 residual LightOPA 的参数量、准确率、AUC、F1 和推理耗时。 |
| 鲁棒性 ablation 表 | `report/tables/robustness_ablation.csv` | 比较 mask 扰动、候选平移、尺度变化对评分的影响。 |
| 模型改动说明表 | `report/tables/model_change_summary.csv` | 统一说明输入适配、输出适配、排序、校准、解释和轻量模式。 |
| 失败案例表 | `report/tables/failure_cases.csv` | 说明系统边界和失败原因。 |
| 遮挡解释表 | `report/tables/occlusion_explainability_v1.csv` | 证明模型对局部区域有可解释响应。 |

## 完整工程验证

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
| V015 | 运行耗时与模型改动说明汇总 | `python experiments\opa_baseline\run_evidence_summary.py` | 通过 | 生成 15 行运行耗时证据和 14 行模型改动说明，写入 `report/tables/inference_runtime.csv`、`report/tables/model_change_summary.csv` 和 `report/logs/evidence_summary.txt`。 |
| V016 | Web 内置样例、可信度提示和导出验证 | Playwright fallback，URL `http://127.0.0.1:8000/` | 通过 | 桌面视口加载 5 个内置案例；加载 `opa_test_001` 后运行推荐得到 3 个候选、可信度为“高可信”、JSON/CSV 导出按钮启用，JSON 下载成功；移动视口中样例区、可信度区和画布可见。 |
| V017 | Web 前端美化与演示模式验证 | Playwright fallback，URL `http://127.0.0.1:8000/` | 通过 | 页面中文无乱码；演示模式切换成功；当前案例有选中态；Top 3 候选框按分级着色；JSON/CSV 导出可用；移动视口无横向溢出；控制台无相关错误。 |
| V018 | 50 组 OPA 候选排序扩展评测 | `.\.venv\Scripts\python.exe experiments\opa_baseline\run_candidate_ranking.py --positive-count 25 --negative-count 25 ...` | 通过 | 50 组、650 条候选；正例 22/25 的 OPA 标注位置进入 Top 3，负例 25/25 低分拒绝；边界案例为 `opa_test_002`、`opa_test_012`、`opa_test_023`。 |
| V019 | 代表案例鲁棒性 ablation | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_robustness_ablation.py` | 通过 | 5 个代表案例、45 次真实 SimOPA 扰动评分；平均绝对分数变化 0.0820，最大变化 0.9455，5 条扰动造成三档标签变化。 |
| V020 | SimOPA full-vs-lite 对比 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_lite_mode_comparison.py` | 通过 | 50 组；`simopa-lite` 将评分调用从 650 降到 350，Top 1 一致 45/50，assessment 一致 50/50；端到端加速约 1.02x，说明子进程模型加载是主要瓶颈。 |
| V021 | SimOPA subprocess-vs-worker 对比 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_worker_comparison.py` | 通过 | 50 组、650 次评分调用；subprocess 耗时 168.6s，常驻 worker 耗时 23.4s，约 7.2x 加速；Top 1、Top 3 和 assessment 全一致。 |
| V022 | FastAPI + SimOPA worker 推荐接口冒烟 | `SMARTPLACE_API_SMOKE_MODE=simopa-worker .\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py` | 通过 | health 返回 `scorer_mode=simopa-worker`；`opa_test_001` Top 3 分数为 0.998、0.8495、0.6471，结果写入 `api_simopa_worker_smoke.*`。 |
| V023 | 100 组 OPA worker 候选排序扩展评测 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\opa_baseline\run_candidate_ranking.py --positive-count 50 --negative-count 50 --scorer-mode simopa-worker ...` | 通过 | 100 组、1300 条候选；正例 44/50 的 OPA 标注位置进入 Top 3，负例 50/50 低分拒绝；耗时 42.1s。 |
| V024 | LightOPA tiny 轻量模型训练 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\lightopa\train_lightopa_tiny.py` | 通过 | 4 通道 tiny CNN，参数量 79,425；2,000 条 train、500 条 val；最佳 epoch=3，验证 accuracy=0.65，ROC-AUC=0.6761，平均验证推理 12.36ms/sample。 |
| V025 | LightOPA residual 轻量模型训练 | `D:\DevTools\Anaconda\envs\study\python.exe experiments\lightopa\train_lightopa_residual.py` | 通过 | 4 通道 residual CNN，参数量 1,113,377；3,000 条 train、600 条 val；最佳 epoch=2，验证 accuracy=0.6717，ROC-AUC=0.7084，平均验证推理 11.50ms/sample。 |
