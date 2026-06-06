# 模型计划

本文是 SmartPlace 模型相关工作的唯一权威文档，合并了课程参考源码审阅、模型路线决策、数据集方案、本地训练可行性和模型解释计划。项目路线、当前状态和短期任务见 `docs/ROADMAP.md`；后续模型细节变化优先改本文。

## 结论先行

当前模型侧已完成 SimOPA baseline、18 组和 50 组候选排序、RGB/mask ablation、分数校准、候选 IoU 去重、代表案例图、遮挡解释实验、鲁棒性 ablation、`simopa-full` vs `simopa-lite` 对比、运行耗时表和模型改动说明表。时间充裕后，下一阶段可以继续扩大到 100 组评测，或优化持久化模型服务以减少子进程加载开销。最终报告、PPT 和录屏由队友基于这些证据整理。

SmartPlace 不从零训练一个全新视觉模型。项目主线是：

> 基于课程 PDF 推荐的 BCMI OPA/libcom 参考源码，围绕智能物体放置应用做模型输入/输出适配、候选排序、分数校准、解释分析和后端服务化改造。

高分组合建议：

```text
OPA/libcom baseline
+ RGB/mask 输入与 mask ablation
+ Top 3 候选排序
+ 0-1 分数、三档标签、校准与去重
+ 遮挡解释
+ Web 交互闭环
```

不建议：

```text
从零训练新模型
第一版就在手机端做真实模型推理
把 TopNet 训练作为主线
```

## 模型改动口径

答辩和报告中不要把当前工作夸大为“重写了 SimOPA 网络结构”。更稳妥的表述是：

> 基于 OPA/SimOPA，我们完成了评分模型的应用适配：将候选合成图和 mask 输入封装为可服务化 scorer，输出 0-1 合理性分数和三档标签；通过 RGB/mask ablation 验证 mask 输入对模型判断的影响；通过候选排序、分数校准、IoU 去重和遮挡解释，使模型结果能服务于 Web 物体放置助手。

按课程分类：

| 工作 | 类型 | 当前证据 |
|---|---|---|
| SimOPA scorer 服务化 | 功能类改动 | `server/scorer.py`、`experiments/opa_baseline/score_candidates.py`、`report/tables/api_simopa_smoke.csv` |
| Top 3 候选排序 | 功能类改动 | `report/tables/candidate_ranking_v1.csv`、`report/tables/candidate_ranking_v2_50.csv` |
| RGB/mask ablation | 输入适配/本体类证据 | `report/tables/rgb_vs_mask_comparison.csv` |
| 0-1 分数与三档标签 | 输出适配 | `server/recommender.py`、API 返回字段 |
| 温度缩放与 IoU 去重 | 后处理/可信度改动 | `report/tables/score_calibration_v1.csv` |
| 遮挡热力图 | 模型解释进阶 | `report/tables/occlusion_explainability_v1.csv`、`report/screenshots/explainability/` |
| 鲁棒性 ablation | 可靠性/解释补强 | `report/tables/robustness_ablation.csv`、`report/logs/robustness_ablation.txt` |
| `simopa-lite` 候选预算模式 | 轻量推理/工程对比 | `report/tables/lite_mode_comparison.csv`、`report/logs/lite_mode_comparison.txt` |

如果老师追问“具体改了哪一层网络结构”，当前版本应如实说明：没有替换 backbone，也没有训练新权重；当前重点是参考模型的输入/输出适配、服务化、排序与解释。若后续要彻底消除这类口径风险，优先做轻量模型对比或小子集 fine-tune，但这不是当前稳定交付的必要条件。

## 高标准补强计划

升级后优先做：

1. 扩大候选排序评测：50 组已完成；如还需要更强统计证据，可继续扩展到 100 组并输出 `candidate_ranking_v2_100.csv`。
2. Web 模型证据展示：在前端显示 `request_id`、`model_version`、`runtime_ms`、scorer 状态和导出结果按钮。
3. Web 内置案例：把 3-5 个代表案例接入页面，保证现场演示稳定。
4. 鲁棒性 ablation：已在 5 个代表案例上完成 mask 膨胀/腐蚀、候选平移、尺度扰动实验，输出 `robustness_ablation.csv`。

轻量化路线：

1. **`simopa-full`**：当前真实 SimOPA scorer，作为质量优先模式。
2. **`simopa-lite`**：轻量应用模式，使用较小候选预算评估同一 SimOPA 权重，强调速度/质量取舍，不宣称是新网络。
3. **`lightopa-resnet18` 或 `lightopa-mobilenet`**：如果时间允许，训练一个 OPA 小子集轻量 scorer，做真正的轻量模型对比。输入仍围绕 composite + mask，输出 0-1 合理性分数，比较准确性、排序质量和推理耗时。
4. **FOPA/TopNet 对比**：只作为候选生成附录展示，不作为主线替换。

暂不做：

```text
大规模 fine-tune
TopNet 主线替换
FOPAHeatMapModel 主线替换
MindSpore/CANN 迁移
Android 端接入
```

## 课程参考源码

方向 A 聚焦“智能物体放置与合成图质量评价”，课程 PDF 推荐优先参考 BCMI 图像合成相关代码。

| 仓库 | 定位 | 对 SmartPlace 的用途 | 优先级 |
|---|---|---|---|
| https://github.com/bcmi/libcom | 图像合成工具箱，包含 OPAScoreModel、FOPAHeatMapModel 等模块。 | 快速跑通真实 OPA 评分，后续可尝试 FOPA 热力图候选。 | P0 |
| https://github.com/bcmi/Object-Placement-Assessment-Dataset-OPA | OPA 数据集与 SimOPA 评分模型源码。 | 模型本体改动、RGB+mask 输入、训练/测试脚本和数据集实验依据。 | P0 |
| https://github.com/bcmi/TopNet-Object-Placement | TopNet 非官方实现，面向候选位置/尺度预测。 | 进阶候选生成参考，不作为第一主线。 | P2 |

课程 PDF 还列出了图像协调、阴影生成、ControlCom 和 MindSpore 等资源。它们更适合进阶项，不作为当前方向 A 主链路的第一优先级。

## 模型路线

### V1 稳定版

- 跑通 `libcom.OPAScoreModel` 或 OPA `eval_opascore/simopa.py`。
- 后端用规则生成候选位置和尺度。
- 对每个候选合成图调用评分模型。
- 返回 Top 3、分数、标签、模型版本和耗时。

目标：确保 Web -> 后端 -> 真实模型 -> Top 3 展示的端到端链路可跑。

### V2 模型改动版

- 实现或适配 RGB baseline。
- 实现或适配 `RGB + foreground mask` 输入。
- 在同一批候选上比较 RGB 和 RGB+mask 的分数、排序和失败案例。

目标：满足“至少一项模型本体类改动”的要求。mask 显式告诉模型哪个区域是前景物体，比只看 RGB composite 更贴合物体放置评分任务。

### V3 可信度与轻量推理版

- 对 SimOPA 分数做温度缩放和三档标签映射。
- 对候选框做 IoU 去重，减少重复 Top 3。
- 在 Web 中展示可信度/失败提示。
- 已提供 `simopa-full` 与 `simopa-lite` 两种推理模式；第一版 `simopa-lite` 定义为候选预算模式，不宣称训练了新网络。

目标：让模型分数更适合交互应用展示，同时补充本地推理耗时和轻量模式对比证据。

### V4 解释版

- 对 3 个成功案例和 2 个失败案例生成 Grad-CAM 或遮挡实验图。
- 说明模型关注前景接触区域、支撑区域、悬空区域或背景语义。

目标：提升答辩说服力，解释模型不是随机打分。

### V5 轻量模型版

- 已实现 `simopa-full` 与 `simopa-lite` 对比；可选继续做 `lightopa-resnet18` / `lightopa-mobilenet`。
- `simopa-lite` 作为轻量应用模式，默认 Top 3 场景减少候选评分次数。
- 如果时间允许，训练一个 OPA 小子集轻量 scorer，使用 composite + mask 作为输入，输出 0-1 合理性分数。
- 比较准确性、Top 3 排序、失败案例和推理耗时。当前 `simopa-lite` 50 组对比显示评分调用减少 `46.15%`，Top 1 一致 `45/50`，assessment 一致 `50/50`，但端到端加速只有约 `1.02x`，说明后续更应优化常驻模型服务或 in-process scorer。

目标：让前端可以选择质量优先或速度优先模式，同时补强“轻量化”和“模型本体改动”的答辩证据。

### V6 进阶候选版

- 尝试 `FOPAHeatMapModel` 预测合理放置区域。
- 或尝试 TopNet 做候选生成对比。

目标：作为附录级冲高分项。此项依赖和时间风险较高，不应替代 V1-V5。

## 改动推荐程度

评分说明：

- 难度：1 最低，5 最高。
- 得分可能性：1 低，5 高。
- 推荐程度综合考虑课程得分、工程可落地性、答辩可解释性和时间风险。

| 方案 | 改动类型 | 内容 | 难度 | 得分可能性 | 推荐程度 |
|---|---|---|---:|---:|---|
| A. OPA/libcom 评分模型服务化 + Top 3 候选排序 | 功能类改动 | 后端生成多个候选位置，对每个候选合成图调用 OPA/libcom 评分，排序返回 Top 3。 | 2 | 4 | 强烈推荐，必须做 |
| B. RGB 与 RGB+mask 输入对比 | 本体类改动 | 保留 RGB baseline，再实现或适配 `RGB + foreground mask` 输入，比较两种模型在候选排序和分数上的差异。 | 3 | 5 | 强烈推荐，主打模型改动 |
| C. 评分输出校准与三档标签 | 输出类改动 | 将模型 softmax/logit 分数校准成 0-1 分数，并映射为推荐、可接受、不推荐。 | 2 | 3 | 推荐，配合 A/B 做 |
| D. Grad-CAM 或遮挡实验解释 | 解释类改动 | 为推荐/失败案例生成热力图或遮挡敏感性图，说明模型关注区域。 | 3 | 4 | 推荐，作为进阶亮点 |
| E. 轻量推理/候选评估模式 | 工程与模型后处理 | 提供 `simopa-full` 与 `simopa-lite` 对比，减少候选数或复用轻量后处理，并记录耗时和排序变化。 | 2 | 3 | 推荐，先做 |
| F. LightOPA 轻量 scorer | 本体类/轻量化 | 使用 ResNet18 或 MobileNetV3 适配 composite + mask 输入，在 OPA 小子集上训练或微调，并比较准确性、排序和耗时。 | 3 | 4 | 推荐，时间充裕时做 |
| G. 鲁棒性 ablation | 解释/可靠性 | 测试 mask 膨胀/腐蚀、候选平移、尺度扰动对分数和排序的影响。 | 2 | 4 | 推荐，证据丰富且风险低 |
| H. FOPAHeatMapModel 替代规则候选生成 | 功能类/进阶 | 使用 libcom 的 FOPA 热力图预测背景-前景对的合理区域，再返回 Top 3。 | 4 | 4 | 中等推荐，作为附录对比 |
| I. TopNet 接入候选生成 | 功能类/进阶 | 使用 TopNet 预测候选位置或尺度，替换规则网格候选。 | 5 | 4 | 谨慎推荐，依赖和权重风险较高 |
| J. 从零设计新网络并完整训练 | 本体类大改 | 自己定义网络结构，从数据集训练物体放置评分模型。 | 5 | 2 | 不推荐，风险远高于收益 |

## 数据集方案

主数据集选择：OPA / Object Placement Assessment Dataset。

目标不是一开始训练大模型，而是先把数据集变成 SmartPlace 可以验证的输入输出证据。

### 第 1 步：下载和整理数据

负责人：成员 A。

目录建议：

```text
assets/datasets/opa/
|-- raw/                 # 原始下载内容，不手动改
|-- samples/             # 选出的课程演示样例
|-- splits/              # train/val/test 或子集索引
`-- notes.md             # 数据来源、下载日期、字段说明
```

需要记录：

- 数据集来源链接。
- 下载日期。
- 原始目录结构。
- 是否包含 composite image、foreground mask、标签或评分。
- 数据许可证或引用信息。

大体积原始数据不要提交 GitHub，只提交 `notes.md`、小样例、索引文件或下载说明。

### 第 2 步：做最小数据审计

先抽 30 到 100 组样例，不急着训练。

检查每组是否有：

- 合成图或背景/前景图。
- foreground mask。
- 合理/不合理标签或分数。
- 可用于展示的候选位置。

输出物：

```text
assets/datasets/opa/splits/smoke_100.csv
report/tables/opa_sample_audit.csv
```

字段建议：

| 字段 | 说明 |
|---|---|
| `case_id` | 样例编号 |
| `composite_path` | 合成图路径 |
| `mask_path` | mask 路径 |
| `label` | 合理/不合理或原始标签 |
| `scene_type` | 桌面、地面、墙面、户外等 |
| `usable` | 是否可用于当前项目 |
| `note` | 问题或备注 |

### 第 3 步：跑通 baseline 推理

先不要改模型。目标是证明参考模型能在本地输出分数。

可选路径：

1. 优先路径：`libcom.OPAScoreModel`。
2. 备选路径：OPA 仓库 `eval_opascore/simopa.py`。

输入：

- composite image。
- foreground mask。

输出：

- 原始 logit 或 softmax。
- 0 到 1 的合理性分数。
- 推理耗时。

需要保存：

```text
report/logs/opa_baseline_inference.txt
report/tables/opa_baseline_scores.csv
report/screenshots/opa_baseline_run.png
```

### 第 4 步：构造 SmartPlace 候选评分数据

从真实背景图和前景图生成多个候选：

- 网格位置：例如 5x5。
- 尺度：例如 0.18、0.25、0.32。
- 过滤明显越界或过大的候选。

每个候选生成：

- composite image。
- foreground mask。
- normalized xywh。
- 模型分数。
- 人工判断。

输出表：

```text
report/tables/candidate_ranking_v1.csv
report/tables/candidate_ranking_v2_50.csv
```

字段建议：

| 字段 | 说明 |
|---|---|
| `case_id` | 案例编号 |
| `candidate_id` | 候选编号 |
| `x,y,w,h` | 归一化位置 |
| `model_version` | 模型版本 |
| `score` | 合理性分数 |
| `rank` | 系统排序 |
| `human_label` | 人工判断 |
| `match` | 排序是否符合人工判断 |

### 第 5 步：做 RGB vs RGB+mask 对比

当前已完成一版 mask ablation：`report/tables/rgb_vs_mask_comparison.csv`。同一批 234 条候选分别使用 object mask、bbox mask 和 blank mask 评分；object mask vs blank mask 的平均绝对差异为 `0.3487`，Top 3 成员变化 56 条。

做法：

1. 准备同一批候选合成图。
2. 跑 RGB baseline。
3. 跑或适配 RGB+mask 模型。
4. 对比 Top 1、Top 3 排序、分数分布和失败案例。

输出表：

```text
report/tables/rgb_vs_mask_comparison.csv
```

关键指标：

- Top 1 是否更符合人工判断。
- Top 3 中合理候选数量。
- 明显悬空/越界案例是否被压低分。
- 推理耗时变化。

### 第 6 步：运行耗时、扩展评测与轻量模式

下一步优先补充运行耗时、扩展评测和轻量模式对比。训练不做大规模主线，但可以做一个小子集轻量 scorer 作为高标准补强。

建议：

- 记录 mock、SimOPA API、候选排序、RGB/mask、校准、遮挡解释的耗时。
- 记录候选数量、设备、模型版本、平均耗时和备注。
- 将候选排序评测从 18 组扩展到 50 或 100 组。
- 第一版 `simopa-lite` 可通过减少候选数或跳过重计算实现，不宣称训练新网络。
- 第二版尝试 `lightopa-resnet18` 或 `lightopa-mobilenet`，在 OPA 小子集上训练或微调轻量 scorer。
- 增加 mask 膨胀/腐蚀、候选平移、尺度扰动等鲁棒性实验。

输出：

```text
report/tables/inference_runtime.csv
report/tables/model_change_summary.csv
report/tables/candidate_ranking_v2_50.csv
report/tables/opa_50_case_summary.csv
report/tables/robustness_ablation.csv
report/tables/lite_mode_comparison.csv
```

## 本地推理与训练可行性

当前可用硬件：

```text
study 环境已跑通 PyTorch 与 CUDA
本地 GPU: NVIDIA GeForce RTX 4070 Ti SUPER
CPU 推理也可作为兜底，但耗时更高
```

结论：

- 当前硬件已经足够 OPA/SimOPA baseline 推理、候选排序、RGB/mask ablation、校准和遮挡解释。
- 轻量模式先比较候选数量、后处理和推理耗时；时间充裕时再训练 LightOPA 级别的小模型。
- 即使 GPU 充足，也不建议从零训练新模型或把 TopNet 训练作为主线。

适合本地训练/推理：

| 任务 | CPU | RTX 4070 Ti SUPER | 建议 |
|---|---|---|---|
| OPA/SimOPA baseline 推理 | 可兜底 | 很适合 | 已完成 |
| RGB/mask ablation | 可小规模 | 很适合 | 已完成 |
| 分数校准与 IoU 去重 | 适合 | 很适合 | 已完成 |
| 遮挡解释 | 较慢 | 很适合 | 已完成 |
| 轻量推理/候选评估模式 | 适合 | 很适合 | 下一步 |
| LightOPA 小子集训练/微调 | 较慢 | 可尝试 | 高标准补强 |
| 鲁棒性 ablation | 适合 | 很适合 | 已完成 |
| FOPAHeatMapModel 推理 | 较慢 | 可尝试 | 可选 |
| TopNet 推理 | 风险较高 | 可尝试 | 可选 |
| TopNet 训练 | 不推荐 | 谨慎尝试 | 暂不做 |
| 从零训练新网络 | 不推荐 | 不推荐 | 不做 |

推荐模型实验环境单独放在：

```text
experiments/
|-- opa_baseline/
|-- opa_rgb_mask/
|-- opa_finetune/
|-- opa_lightweight/
|-- robustness/
|-- explainability/
`-- README.md
```

权重、原始数据集和训练输出不要提交 GitHub，只提交脚本、配置、少量样例和结果表。

## 本地推理与真实性证据

结论：第一版把真实模型放在本地电脑或局域网 FastAPI 服务中推理，Web 前端只负责交互和展示。这样最稳定，也最容易在课堂上证明模型真实运行。

课程强调现场处理一张全新图片，并提供目标模型实际运行证据。SmartPlace 需要准备：

- 权重来源、权重文件路径和加载日志。
- 参考模型或改造模型的推理代码位置。
- 输入张量形状，例如 RGB baseline 的 `3 x H x W` 和 RGB+mask 的 `4 x H x W`。
- 后端终端实时日志：请求 ID、候选数量、模型版本、每个候选分数和总耗时。
- Web 展示字段：`request_id`、`model_version`、`runtime_ms`、Top 3 候选和三档标签。
- 一张未出现在报告中的新图片现场推理结果。

暂不做手机端或 Android 端侧推理。若后续有充分时间，可以把 MindSpore/CANN 或轻量模型迁移作为独立进阶项，但不阻塞主线。

## 后端接口落地

后端暴露稳定函数：

```text
score_composite(composite_image, foreground_mask, model_version) -> score
```

FastAPI 做：

1. 接收 Web 上传的背景图和前景图。
2. 生成候选位置。
3. 合成每个候选。
4. 调用评分模型。
5. 返回 Top 3、分数、标签、模型版本和耗时。

Web 前端不需要关心模型细节，只按 `docs/API.md` 展示结果。

## 需要收集的证据

- 参考模型运行截图。
- 课程 PDF 参考 GitHub 源码链接和阅读记录。
- 数据集下载说明和样例审计表。
- 权重加载代码位置。
- 输入/输出适配说明。
- 一张全新图片的实时推理日志。
- 候选排序对比表。
- RGB vs RGB+mask 对比表。
- 分数校准与 IoU 去重表。
- 推理时间对比表。
- 50/100 组扩展候选排序表。
- 轻量模式或轻量 scorer 对比表。
- mask 和候选扰动鲁棒性表。
- 成功案例和失败案例。
- 遮挡实验或其他模型解释结果。
- 可选：FOPA/TopNet 候选生成对比表。

## 下一轮模型任务

| 任务 | 负责人 | 输出物 |
|---|---|---|
| 轻量模式与轻量 scorer 对比 | 成员 A、B | `lite_mode_comparison.csv` |
| 可选 100 组候选排序评测 | 成员 A、B | `candidate_ranking_v2_100.csv` |
| Web 展示模型证据与导出结果 | 成员 B、C | `request_id`、`model_version`、`runtime_ms`、JSON/CSV 导出 |
| Web 内置代表案例 | 成员 C | 成功、边界、负例、拒绝案例一键加载 |
| 可信度/失败提示 | 成员 A、B、C | 分数饱和、候选重叠、低可信等提示规则 |
| 最终材料整理 | 队友/材料负责人 | 报告、PPT、录屏、AI 辅助说明、分工说明 |

## 答辩表述

可以这样说：

> 我们没有从零发明一个视觉模型，而是基于课程推荐的 OPA/libcom 评分模型，围绕智能物体放置应用做了 RGB/mask 输入适配、候选排序、分数校准、IoU 去重和遮挡解释。Web 端负责交互和展示，真实推理由本地 FastAPI 后端完成，课堂演示时可以用全新图片展示权重加载、候选评分、Top 3 返回和运行耗时。
