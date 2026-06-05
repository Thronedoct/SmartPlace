# 课程参考源码审阅

本文记录从 `课程项目.pdf` 中提取并浏览过的方向 A 相关 GitHub 源码，以及 SmartPlace 的落地选择。后续模型、后端和 Android 改动都应优先回到本文确认依据。

## 课程文档中的相关仓库

方向 A 聚焦“智能物体放置与合成图质量评价”，优先参考以下 BCMI 代码：

| 仓库 | 定位 | 对 SmartPlace 的用途 |
|---|---|---|
| https://github.com/bcmi/libcom | 图像合成工具箱，集成 OPAScoreModel、FOPAHeatMapModel 等任务模块。 | Phase 1 优先用于快速跑通 OPA 评分接口，减少从源码组装模型的成本。 |
| https://github.com/bcmi/Object-Placement-Assessment-Dataset-OPA | OPA 数据集与 SimOPA 评分模型源码。 | 本项目模型本体改动的主要依据，重点关注 `RGB + mask` 输入、评分输出和训练/测试脚本。 |
| https://github.com/bcmi/TopNet-Object-Placement | TopNet 非官方实现，面向候选位置/尺度预测。 | 可作为 Phase 3 之后的候选生成参考；Phase 1-2 暂不把它作为主链路依赖。 |

课程 PDF 还列出了图像协调、阴影生成、ControlCom 和 MindSpore 等资源。它们更适合进阶项，不作为当前方向 A 主链路的第一优先级。

## 关键源码结论

### libcom

- README 将 `OPAScoreModel` 定位为合成图中前景物体放置合理性评分模块。
- README 将 `FOPAHeatMapModel` 定位为给定背景-前景对后，预测多位置/多尺度合理性分数并输出最佳放置结果的模块。
- 当前 `libcom` 主分支要求较新的 Python/PyTorch 环境，适合先在独立实验目录中验证，再封装到本仓库后端。

结论：`libcom` 是最快形成“真实模型调用证据”的路径。成员 A 应先跑通 `OPAScoreModel`，成员 B 再把它包成后端 scorer。

### Object-Placement-Assessment-Dataset-OPA

- 仓库 README 明确 OPA 任务是判断合成图中物体位置是否合理，关注位置、大小、遮挡、语义和透视等因素。
- `eval_opascore/simopa.py` 的推理流程是读取 composite image 和 foreground mask，将 RGB 图与灰度 mask 拼成 4 通道输入，输出二分类 softmax 中“合理”类别的分数。
- `resnet_4ch.py` 中包含将 ResNet 第一层从 3 通道扩展到 4 通道的实现思路，并用 RGB 权重加权初始化新增 mask 通道。

结论：课程要求的“模型本体类改动”可以落在 `RGB -> RGB + mask` 这条线上。虽然 OPA 原始代码已有 4 通道版本，本项目仍需要在报告中说明自己如何适配输入、封装推理、对比原 RGB 和 RGB+mask 的结果。

### TopNet

- README 将 TopNet 定位为 CVPR 2023 “Transformer-based Object Placement Network for Image Compositing”的非官方实现。
- 它用于根据背景和前景预测合理位置/尺度，比单纯网格枚举更接近真实候选生成模型。
- 仓库需要额外数据、SOPA encoder 和预训练权重，接入成本高于 OPA 评分。

结论：TopNet 暂定为进阶候选生成路线。当前先用规则候选生成 + OPA/libcom 评分，确保端到端演示稳定。

## SmartPlace 当前落地路线

1. Phase 0：保留 mock 后端，先让 API、文档、测试和 Android 联调稳定。
2. Phase 1：成员 A 在独立实验环境跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py`，记录输入输出、权重路径和日志。
3. Phase 2：成员 B 将评分函数接入 FastAPI，后端生成候选框并逐个评分，返回 Top 3。
4. Phase 3：成员 A 完成 `RGB` 与 `RGB+mask` 模式对比；成员 B 在接口中返回 `model_version`；成员 C 在 Android 展示模型版本、耗时和 Top 3。
5. Phase 4：如时间允许，再参考 `FOPAHeatMapModel` 或 TopNet 替换规则候选生成。

## Android 决策

课程 Demo 可以继续作为参考，但 SmartPlace 不再强制基于 `OPAAndroidDemoSimp/` 开发。成员 C 可以：

- 继续在原生 Android Demo 上接入 HTTP multipart 和 Top 3 展示。
- 重新搭建一个更干净的原生 Android 项目。
- 在小组确认后改用 Flutter、Web 或其他可交互原型。

无论选择哪种前端，必须遵守 `docs/API.md`，并保证演示中能完成“选择背景/前景 -> 请求后端 -> 展示 Top 3 -> 保存或截图结果”的主流程。
