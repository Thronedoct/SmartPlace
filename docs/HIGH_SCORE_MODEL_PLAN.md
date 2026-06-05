# 高分模型方案与训练/端侧推理可行性

本文在 `docs/MODEL_DECISION.md` 的基础上，设计一个更高分、但仍可落地的模型方案，并分析它是否适合本地显卡训练、是否适合手机端推理。

## 高分目标

高分方案要同时满足四件事：

1. 有真实参考模型调用，不停留在 mock。
2. 有至少一项模型本体类改动，而不是只改接口。
3. 有应用闭环：Android/前端上传图片，后端返回 Top 3 推荐。
4. 有实验证据：数据集样例、自采案例、对比表、失败分析和可解释图。

本项目不追求“大而全”的新模型。更好的高分策略是：

> 用 OPA/libcom 做主评分模型，用数据集证明模型改动有效，用后端候选排序形成应用价值，用解释图和少量微调提高答辩说服力。

## 推荐高分组合

### 主线：OPA 评分模型 + 候选排序

必须完成：

- 使用 OPA/libcom 跑通真实评分。
- 后端生成候选位置和尺度。
- 对每个候选合成图调用评分模型。
- 返回 Top 3、分数、标签、模型版本和耗时。

这是系统主链路，直接支撑 Android 展示。

### 本体改动：RGB baseline vs RGB+mask

必须完成：

- 实现或适配 RGB baseline。
- 实现或适配 `RGB + foreground mask` 输入。
- 对同一批候选比较分数和排序。

这项是最推荐的模型本体改动，因为它和“物体放置”任务强相关，答辩时也好解释：mask 显式告诉模型哪个区域是前景物体。

### 训练/微调：轻量 fine-tune 而不是从零训练

建议完成：

- 用 OPA 数据集抽取一个小训练子集和验证子集。
- 冻结 ResNet backbone 前几层，只微调最后分类层或最后一个 block。
- 对比微调前后在候选排序上的变化。

这比从零训练风险低很多，但能体现“我们不只是调用模型，还做了训练适配”。

### 解释增强：Grad-CAM 或遮挡实验

建议完成：

- 对 3 个成功案例和 2 个失败案例生成解释图。
- 说明模型关注前景接触区域、支撑区域、悬空区域或背景语义。

如果 Grad-CAM 时间不够，可以做遮挡实验：用滑窗遮挡前景附近区域，看分数变化。遮挡实验工程量小，也足够说明模型解释。

### 候选生成增强：FOPAHeatMapModel

时间允许再做：

- 用 libcom 的 FOPA 热力图模型预测合理放置区域。
- 将规则网格候选与 FOPA 热力图候选做对比。

这项作为加分项，不建议放在主链路第一优先级。主链路先用规则候选，保证稳定。

## 高分版本分层

| 版本 | 内容 | 目标 |
|---|---|---|
| V1 稳定版 | OPA/libcom 评分 + 规则候选 + Top 3 返回 | 确保端到端演示可跑 |
| V2 模型改动版 | RGB vs RGB+mask 对比 + 分数校准 | 满足模型本体改动要求 |
| V3 训练版 | OPA 小子集轻量 fine-tune + 对比表 | 证明有训练和数据集工作 |
| V4 解释版 | Grad-CAM/遮挡实验 + 成功失败分析 | 提升答辩说服力 |
| V5 进阶版 | FOPAHeatMapModel 或 TopNet 候选生成对比 | 时间充足时冲高分 |

建议至少完成 V1-V4。V5 可根据时间和依赖情况决定。

## 本地显卡训练可行性

当前本机检测结果：

```text
GPU: NVIDIA GeForce RTX 5070 Laptop GPU
显存: 约 8GB
CUDA driver: 可用，nvidia-smi 正常
Python: 当前项目环境尚未安装 PyTorch
```

结论：适合做 OPA/SimOPA 的轻量训练或微调，不建议从零训练大模型，也不建议把 TopNet 训练作为主任务。

### 适合本机训练的内容

| 任务 | 是否适合 | 原因 |
|---|---|---|
| OPA/SimOPA baseline 推理 | 适合 | ResNet 级别模型，输入通常是 256 图像，显存压力小。 |
| RGB+mask 4 通道模型推理 | 适合 | 只比 RGB 多一个 mask 通道，显存增加有限。 |
| 冻结 backbone 微调分类头 | 适合 | batch size 可以设小，8GB 显存够用。 |
| 微调 ResNet 最后一两个 block | 基本适合 | 需要控制 batch size、图像尺寸和 dataloader worker。 |
| 从零训练 ResNet/SimOPA | 不推荐 | 需要更多时间、数据和调参，收益不稳定。 |
| 训练 TopNet | 不推荐 | 依赖、数据和权重更复杂，8GB 显存可能吃紧。 |
| 训练扩散/生成式模型 | 不推荐 | 与方向 A 主目标不匹配，硬件和时间成本都高。 |

### 推荐训练设置

先从保守设置开始：

```text
image_size: 256
batch_size: 8 或 16
optimizer: AdamW
learning_rate: 1e-4 到 3e-4
epochs: 3 到 10
precision: fp16 或 mixed precision
strategy: 先冻结 backbone，只训分类头；稳定后再解冻最后一个 block
```

训练目标不是刷榜，而是得到可展示的对比证据：

- baseline 分数表。
- 微调后分数表。
- 排序变化。
- 成功/失败案例。
- 推理耗时。

### 本地环境建议

建议单独建模型实验环境，不要污染后端运行环境：

```text
experiments/
|-- opa_baseline/
|-- opa_rgb_mask/
|-- logs/
`-- README.md
```

大模型权重、原始数据集和训练输出不要提交 GitHub，只提交脚本、配置、少量样例和结果表。

## 手机端推理可行性

结论：不建议把第一版真实模型放在手机端推理。推荐主线是云端/电脑端 FastAPI 推理，Android 只做交互和展示。

### 为什么不建议第一版手机端推理

OPA/SimOPA 这类模型虽然不是超大模型，但手机端仍有几个风险：

- Android 端要转换模型格式，例如 ONNX、TFLite 或 MindSpore Lite。
- 4 通道输入 `RGB + mask` 在移动端预处理更麻烦。
- 端侧推理需要处理模型包体、内存、耗时和兼容性。
- 课程演示最重要的是稳定闭环；云端推理更容易展示日志和模型真实性。

### 手机端可以做什么

推荐手机端负责：

- 选择背景图和前景图。
- 简单前景裁剪或 mask 生成。
- 上传图片到后端。
- 展示 Top 3 候选框和分数。
- 支持候选切换、手动微调、保存结果。

这些交互本身就是课程项目高分点。

### 如果一定要做端侧推理

端侧推理适合作为加分项，不作为主线。

可选路线：

| 路线 | 可行性 | 说明 |
|---|---|---|
| ONNX Runtime Mobile | 中等 | PyTorch -> ONNX 较自然，但 Android 集成和 4 通道输入预处理要额外做。 |
| TFLite | 中等偏低 | 需要 PyTorch -> ONNX -> TensorFlow/TFLite，转换链更长。 |
| MindSpore Lite | 中等偏低 | 如果课程强调华为生态可作为亮点，但迁移成本较高。 |
| 只在手机做轻量规则候选，模型仍在后端 | 高 | 最稳，交互体验好，模型证据也清楚。 |

如果做端侧推理，建议只转换 V1/V2 的小模型，不要转 TopNet 或 FOPAHeatMapModel。

## 高分实验设计

### 数据集实验

至少准备：

- OPA 数据集子集 100 到 500 组。
- 自采/自制案例 18 组。
- 每组生成 5 到 25 个候选。

表格：

```text
report/tables/opa_sample_audit.csv
report/tables/baseline_scores.csv
report/tables/rgb_vs_mask_comparison.csv
report/tables/finetune_comparison.csv
report/tables/failure_cases.csv
```

### 模型对比

至少比较三种版本：

| 版本 | 说明 |
|---|---|
| `opa-rgb-baseline` | 只输入 RGB composite 的 baseline。 |
| `opa-rgb-mask-v1` | 输入 RGB composite + foreground mask。 |
| `opa-rgb-mask-ft-v1` | 在 OPA 子集或自构造候选上轻量微调后的版本。 |

可选加入：

| 版本 | 说明 |
|---|---|
| `fopa-heatmap-v1` | 使用 FOPAHeatMapModel 产生候选热力图。 |
| `topnet-candidate-v1` | 使用 TopNet 候选生成，仅做进阶对比。 |

### 指标

不需要复杂学术指标，课程项目应优先使用可解释指标：

- Top 1 是否符合人工判断。
- Top 3 中合理候选数量。
- 不合理候选平均分是否低于合理候选。
- 推理耗时。
- 网络端到端耗时。
- 失败案例类型：悬空、尺度错误、语义不匹配、透视不一致、遮挡不自然。

## 最终推荐

主线：

1. 云端/电脑端推理，不做第一版手机端推理。
2. 本地 RTX 5070 Laptop GPU 用于 OPA/SimOPA baseline、RGB+mask 适配和轻量微调。
3. Android 端专注交互、上传、展示和结果保存。
4. 数据集从 OPA 子集开始，配合 18 组自采案例做结果分析。

高分组合：

```text
OPA/libcom baseline
+ RGB vs RGB+mask 本体改动
+ Top 3 候选排序
+ 小子集 fine-tune
+ Grad-CAM/遮挡解释
+ Android 交互闭环
```

不建议：

```text
从零训练新模型
第一版就做手机端真实模型推理
把 TopNet 训练作为主线
```

答辩表述可以这样说：

> 我们没有从零发明一个视觉模型，而是基于课程推荐的 OPA/libcom 评分模型，围绕智能物体放置应用做了 RGB+mask 输入适配、候选排序、轻量微调和解释分析。模型训练在本地 RTX 显卡上完成，Android 端负责交互和展示，真实推理由后端完成，以保证稳定性和可验证性。
