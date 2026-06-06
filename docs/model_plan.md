# 模型计划

本文是 SmartPlace 模型相关工作的唯一权威文档，合并了课程参考源码审阅、模型路线决策、数据集方案、本地训练可行性和模型解释计划。项目路线、当前状态和短期任务见 `docs/ROADMAP.md`；后续模型细节变化优先改本文。

## 结论先行

当前模型侧已完成 SimOPA baseline、18 组候选排序、RGB/mask ablation、分数校准、候选 IoU 去重、代表案例图和遮挡解释实验。下一阶段优先级是：报告/PPT/演示材料整合；轻量 fine-tune 和 FOPA/TopNet 作为后续进阶项。

SmartPlace 不从零训练一个全新视觉模型。项目主线是：

> 基于课程 PDF 推荐的 BCMI OPA/libcom 参考源码，围绕智能物体放置应用做模型输入、输出、候选排序、轻量微调、解释分析和后端服务化改造。

高分组合建议：

```text
OPA/libcom baseline
+ RGB vs RGB+mask 本体改动
+ Top 3 候选排序
+ OPA 小子集 fine-tune
+ Grad-CAM 或遮挡解释
+ Web 交互闭环
```

不建议：

```text
从零训练新模型
第一版就在手机端做真实模型推理
把 TopNet 训练作为主线
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

### V3 训练版

- 从 OPA 数据集抽取小训练子集和验证子集。
- 冻结 ResNet backbone 前几层，只微调分类头或最后一个 block。
- 对比微调前后候选排序、分数分布和推理耗时。

目标：证明项目不只是调用现成模型，也做了数据集驱动的训练适配。

### V4 解释版

- 对 3 个成功案例和 2 个失败案例生成 Grad-CAM 或遮挡实验图。
- 说明模型关注前景接触区域、支撑区域、悬空区域或背景语义。

目标：提升答辩说服力，解释模型不是随机打分。

### V5 进阶候选版

- 尝试 `FOPAHeatMapModel` 预测合理放置区域。
- 或尝试 TopNet 做候选生成对比。

目标：作为冲高分项。此项依赖和时间风险较高，不应阻塞 V1-V4。

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
| E. OPA 小子集轻量 fine-tune | 训练适配 | 冻结大部分 backbone，只微调分类头或最后一个 block，并记录改动前后差异。 | 3 | 4 | 推荐，16GB 显卡可支撑 |
| F. FOPAHeatMapModel 替代规则候选生成 | 功能类/进阶 | 使用 libcom 的 FOPA 热力图预测背景-前景对的合理区域，再返回 Top 3。 | 4 | 4 | 中等推荐，时间足够再做 |
| G. TopNet 接入候选生成 | 功能类/进阶 | 使用 TopNet 预测候选位置或尺度，替换规则网格候选。 | 5 | 4 | 谨慎推荐，依赖和权重风险较高 |
| H. 从零设计新网络并完整训练 | 本体类大改 | 自己定义网络结构，从数据集训练物体放置评分模型。 | 5 | 2 | 不推荐，风险远高于收益 |

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

### 第 6 步：轻量 fine-tune

训练目标不是刷榜，而是得到可展示的对比证据。

建议：

- OPA 子集 100 到 500 组起步。
- 图像尺寸 256。
- batch size 16 起步，16GB 显存可尝试 32。
- 冻结 backbone，先只训练分类头。
- 稳定后解冻最后一个 block。
- epoch 3 到 10。
- 使用 fp16 或 mixed precision。

输出：

```text
report/tables/finetune_comparison.csv
report/logs/opa_finetune_log.txt
```

## 本地训练可行性

当前可用硬件：

```text
本机已检测到: NVIDIA GeForce RTX 5070 Laptop GPU, 约 8GB 显存
额外可用: 16GB 显存的 RTX 4070 TiS
当前普通 Python 环境: 尚未安装 PyTorch
```

结论：

- 8GB 显存已经足够 OPA/SimOPA baseline 推理、RGB+mask 推理、小 batch 微调。
- 16GB RTX 4070 TiS 更适合做稳定 fine-tune，可用更大 batch size、更快跑完对比实验，也更适合尝试 FOPAHeatMapModel 推理。
- 即使有 16GB 显存，也不建议从零训练新模型或把 TopNet 训练作为主线。

适合本地训练/推理：

| 任务 | 8GB Laptop GPU | 16GB 4070 TiS | 建议 |
|---|---|---|---|
| OPA/SimOPA baseline 推理 | 适合 | 很适合 | P0 |
| RGB+mask 4 通道模型推理 | 适合 | 很适合 | P0 |
| 冻结 backbone 微调分类头 | 适合 | 很适合 | P1 |
| 微调 ResNet 最后一两个 block | 基本适合 | 适合 | P1 |
| Grad-CAM/遮挡解释 | 适合 | 很适合 | P1 |
| FOPAHeatMapModel 推理 | 可能可行 | 更适合 | P2 |
| TopNet 推理 | 风险较高 | 可尝试 | P2 |
| TopNet 训练 | 不推荐 | 谨慎尝试 | P3 |
| 从零训练新网络 | 不推荐 | 不推荐 | 不做 |

推荐模型实验环境单独放在：

```text
experiments/
|-- opa_baseline/
|-- opa_rgb_mask/
|-- opa_finetune/
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
- 改造前后的输入张量形状。
- 一张全新图片的实时推理日志。
- 候选排序对比表。
- RGB vs RGB+mask 对比表。
- fine-tune 前后对比表。
- 推理时间对比表。
- 成功案例和失败案例。
- Grad-CAM、遮挡实验或其他模型解释结果。

## 下一轮模型任务

| 任务 | 负责人 | 输出物 |
|---|---|---|
| 下载并审计 OPA 小子集 | 成员 A | `assets/datasets/opa/notes.md`、`opa_sample_audit.csv` |
| 跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py` | 成员 A | 终端日志、输入图片、分数截图、依赖记录 |
| 定义 scorer 函数签名 | 成员 A、B | `score_composite(composite, mask) -> score` |
| 后端接入 mock/真实模型开关 | 成员 B | `model_version`、耗时日志、错误处理 |
| 生成候选评分表 | 成员 A、B | `candidate_ranking_v1.csv` |
| Web 展示模型字段 | 成员 C | Top 3、分数、标签、耗时、模型版本 |

## 答辩表述

可以这样说：

> 我们没有从零发明一个视觉模型，而是基于课程推荐的 OPA/libcom 评分模型，围绕智能物体放置应用做了 RGB+mask 输入适配、候选排序、轻量微调和解释分析。Web 端负责交互和展示，真实推理由本地 FastAPI 后端完成，课堂演示时可以用全新图片展示权重加载、张量推理、候选评分和 Top 3 返回过程。
