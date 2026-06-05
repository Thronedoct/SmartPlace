# 模型路线决策与数据集方案

本文回答三个问题：

1. SmartPlace 是自己从零做模型，还是在课程参考源码基础上做模型改动？
2. 哪些模型改动更值得做？
3. 如果从数据集开始推进，具体怎么落地？

高分扩展方案、训练硬件和手机端推理可行性详见 `docs/HIGH_SCORE_MODEL_PLAN.md`。

## 总体结论

SmartPlace 不建议从零设计并训练一个全新模型。更合理的路线是：

- 以课程 PDF 推荐的 BCMI 方向 A 源码为基础。
- 先跑通 OPA/libcom 的物体放置评分模型。
- 在参考模型基础上做服务于应用目标的“小而实”的模型改动。
- 用数据集和自采案例证明改动前后在排序、分数、耗时或失败案例上的差异。

理由：

- 课程要求是“基于参考模型或参考代码做适度修改”，不是要求从零发明模型。
- 方向 A 的关键评分点是应用闭环、模型适配、候选排序和测试验证；从零训练模型风险高，容易牺牲 Android/后端/报告证据。
- OPA/libcom 已经覆盖“合成图位置合理性评分”这个核心任务，直接贴合 SmartPlace 的应用目标。

因此，项目定位应写成：

> 本项目基于 BCMI 的 OPA/libcom 参考源码，围绕智能物体放置应用进行模型输入、输出、候选排序和推理服务封装改造，而不是从零训练一个全新视觉模型。

## 模型改动推荐程度

评分说明：

- 难度：1 最低，5 最高。
- 得分可能性：1 低，5 高。
- 推荐程度综合考虑课程得分、工程可落地性、答辩可解释性和时间风险。

| 方案 | 改动类型 | 内容 | 难度 | 得分可能性 | 推荐程度 |
|---|---|---|---:|---:|---|
| A. OPA/libcom 评分模型服务化 + Top 3 候选排序 | 功能类改动 | 后端生成多个候选位置，对每个候选合成图调用 OPA/libcom 评分，排序返回 Top 3。 | 2 | 4 | 强烈推荐，必须做 |
| B. RGB 与 RGB+mask 输入对比 | 本体类改动 | 保留 RGB baseline，再实现或适配 `RGB + foreground mask` 输入，比较两种模型在候选排序和分数上的差异。 | 3 | 5 | 强烈推荐，主打模型改动 |
| C. 评分输出校准与三档标签 | 输出类改动 | 将模型 softmax/logit 分数校准成 0-1 分数，并映射为推荐、可接受、不推荐。 | 2 | 3 | 推荐，适合配合 A/B |
| D. Grad-CAM 或遮挡实验解释 | 解释类改动 | 为推荐/失败案例生成热力图或遮挡敏感性图，说明模型关注区域。 | 3 | 4 | 推荐，作为进阶亮点 |
| E. FOPAHeatMapModel 替代规则候选生成 | 功能类/进阶 | 使用 libcom 的 FOPA 热力图直接预测背景-前景对的合理区域，再返回 Top 3。 | 4 | 4 | 中等推荐，时间足够再做 |
| F. TopNet 接入候选生成 | 功能类/进阶 | 使用 TopNet 预测候选位置或尺度，替换规则网格候选。 | 5 | 4 | 谨慎推荐，依赖和权重风险较高 |
| G. 从零设计新网络并完整训练 | 本体类大改 | 自己定义网络结构，从数据集训练物体放置评分模型。 | 5 | 2 | 不推荐，风险远高于收益 |

## 推荐组合

### 最稳得分组合

1. A：OPA/libcom 评分模型服务化 + Top 3 候选排序。
2. B：RGB 与 RGB+mask 输入对比。
3. C：分数校准与三档标签。

这个组合最符合课程要求：有可交互应用、有真实模型调用、有至少一项本体类改动、有候选排序和测试验证。

### 高分增强组合

在最稳组合基础上增加：

4. D：Grad-CAM 或遮挡实验解释。
5. E：FOPAHeatMapModel 作为候选生成进阶。

这组适合时间充足时做。D 比 E 更适合答辩，因为解释图直观，容易展示模型不是随机打分。

### 不建议路线

不建议把主要时间投入 G：从零做模型。它需要处理数据清洗、训练收敛、调参、过拟合和指标设计；即使训练出来，也未必比参考模型表现更好。课程更看重参考代码定位、模型适配、应用闭环和结果分析。

## 从数据集开始的方案

主数据集选择：OPA / Object Placement Assessment Dataset。

目标不是一开始训练大模型，而是先把数据集变成 SmartPlace 可以验证的输入输出证据。

### 第 1 步：下载和整理数据

负责人：成员 A。

输出目录建议：

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

注意：大体积原始数据不要直接提交 GitHub。只提交 `notes.md`、小样例、索引文件或下载说明。

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

这是推荐的本体类改动证据。

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

报告里要讲清：

- mask 提供了前景位置和轮廓信息。
- 纯 RGB 合成图可能把背景纹理、物体语义和边界混在一起。
- RGB+mask 能让模型更明确地区分“被评分物体”和背景。

### 第 6 步：接入后端和 Android

后端暴露稳定函数：

```text
score_composite(composite_image, foreground_mask, model_version) -> score
```

FastAPI 做：

1. 接收 Android 上传的背景图和前景图。
2. 生成候选位置。
3. 合成每个候选。
4. 调用评分模型。
5. 返回 Top 3、分数、标签、模型版本和耗时。

Android 不需要关心模型细节，只按 `docs/API.md` 展示结果。

## 最终建议

主线选择：

> 基于 OPA/libcom 参考源码做模型适配，不从零做模型。

高分版主线选择：

> 本地显卡用于 OPA/SimOPA baseline、RGB+mask 适配和轻量微调；Android 第一版不做端侧模型推理，而是通过后端完成真实模型推理，手机端专注交互、上传、候选展示和结果保存。

优先完成：

1. OPA/libcom baseline 推理。
2. 规则候选生成 + 模型评分排序。
3. RGB vs RGB+mask 对比。
4. 分数校准和标签展示。

时间允许再做：

5. Grad-CAM/遮挡解释。
6. FOPAHeatMapModel 或 TopNet 候选生成。

最终报告中要强调：SmartPlace 的创新不在于重新发明视觉 backbone，而在于把参考评分模型改造成一个可交互、可排序、可解释、可验证的物体放置助手。
