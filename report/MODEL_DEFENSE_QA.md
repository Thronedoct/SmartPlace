# SmartPlace 模型侧答辩说明与问答

本文用于答辩前快速统一模型侧口径。建议先读“一分钟讲法”，再根据老师提问跳到后面的问答。

## 一分钟讲法

SmartPlace 的模型侧主线是把 OPA/SimOPA 放置合理性评分模型封装成一个可交互的物体放置推荐器。输入是背景图、前景图、前景 mask 和候选位置；后端把每个候选位置合成图像，再调用 SimOPA 输出 0-1 合理性分数，最后排序返回 Top 3。

我们不只是调用模型，还围绕模型做了完整验证和工程化：

```text
真实 SimOPA 推理
-> 多候选 Top 3 排序
-> RGB/mask 消融
-> 分数校准与 IoU 去重
-> 遮挡解释与鲁棒性扰动
-> simopa-worker 常驻模型加速
-> LightOPA tiny/residual 轻量模型 baseline
```

报告中最稳的表述是：我们完成了 OPA/SimOPA 的应用适配、候选排序服务化、输入/输出分析、结果后处理、可解释性、鲁棒性、推理加速和轻量模型探索。不要说“我们重写了 SimOPA backbone”。

## 模型侧做了什么

### 1. 真实 SimOPA 接入

我们使用 OPA 项目中的 SimOPA 评分模型。这个模型的任务与项目目标一致：判断一个前景物体放在背景中的某个位置是否合理。

项目里把 SimOPA 封装成统一 scorer：

```text
background + foreground + mask + candidates
-> candidate composites
-> SimOPA score
-> Top 3 placement recommendation
```

相关证据：

| 内容 | 文件 |
|---|---|
| 后端 scorer | `server/scorer.py` |
| 候选排序逻辑 | `server/recommender.py` |
| SimOPA 调用脚本 | `experiments/opa_baseline/score_candidates.py` |
| Worker 调用脚本 | `experiments/opa_baseline/score_candidates_worker.py` |
| API 冒烟结果 | `report/logs/api_simopa_worker_smoke.txt` |

### 2. Top 3 候选排序

SimOPA 原本更像“给单张合成图打分”。我们把它变成放置助手：先生成多个候选位置，再逐个评分、排序、返回 Top 3。

100 组验证结果：

```text
100 组案例：50 正例、50 负例
1300 条候选评分
正例：44/50 的 OPA 标注位置进入 Top 3
负例：50/50 被低分拒绝
耗时：42.1s，使用 simopa-worker
```

相关证据：

| 内容 | 文件 |
|---|---|
| 100 组排序表 | `report/tables/candidate_ranking_v2_100.csv` |
| 100 组汇总表 | `report/tables/opa_100_case_summary.csv` |
| 100 组日志 | `report/logs/candidate_ranking_v2_100.txt` |

### 3. RGB/mask 消融

为了证明 mask 信息确实有用，我们比较了三种输入：

```text
object mask：真实前景形状
bbox mask：只保留粗框
blank mask：不提供有效 mask
```

结果：

```text
候选数：234
object mask vs bbox mask 平均绝对差异：0.0839
object mask vs blank mask 平均绝对差异：0.3487
Top 3 成员变化：bbox 16 条，blank 56 条
```

这个实验说明 mask 通道会显著影响模型判断，模型不是只看整张 RGB 图。

相关证据：

| 内容 | 文件 |
|---|---|
| 消融表 | `report/tables/rgb_vs_mask_comparison.csv` |
| 消融日志 | `report/logs/rgb_vs_mask_comparison.txt` |

### 4. 分数校准与 IoU 去重

SimOPA 输出会有分数饱和问题：有些候选都接近 1.0。我们做了两个后处理：

```text
分数校准：把原始置信度整理成更容易解释的推荐分数
IoU 去重：避免 Top 3 候选框高度重叠
```

Web 端最终展示三档标签：

```text
推荐 / 可接受 / 不推荐
```

答辩时可以说：原始模型输出是分类置信度，我们把它整理成适合推荐系统展示的分数、标签和可信度提示。

相关证据：

| 内容 | 文件 |
|---|---|
| 校准与去重表 | `report/tables/score_calibration_v1.csv` |
| 校准日志 | `report/logs/score_calibration_v1.txt` |

### 5. 可解释性：遮挡实验

我们做了 6x6 网格遮挡实验：每次遮挡图像中的一个区域，观察 SimOPA 分数下降多少。下降越大，说明该区域对模型判断越重要。

结果：

```text
代表案例：5 个
平均最大分数下降：0.5472
部分案例出现明显敏感区域
```

相关证据：

| 内容 | 文件 |
|---|---|
| 遮挡解释表 | `report/tables/occlusion_explainability_v1.csv` |
| 遮挡解释日志 | `report/logs/occlusion_explainability_v1.txt` |
| 热力图 | `report/screenshots/explainability/` |

### 6. 鲁棒性扰动

我们测试了模型对小扰动是否稳定：

```text
mask 腐蚀/膨胀
候选位置平移
候选尺度缩放
```

结果：

```text
5 个代表案例
45 次扰动评分
平均绝对分数变化：0.0820
最大变化：0.9455
5 次扰动导致三档标签变化
```

这说明多数轻微扰动下模型比较稳定，但个别边界案例对位置变化很敏感。

相关证据：

| 内容 | 文件 |
|---|---|
| 鲁棒性表 | `report/tables/robustness_ablation.csv` |
| 鲁棒性日志 | `report/logs/robustness_ablation.txt` |

### 7. 推理加速：simopa-worker

最开始每次评分都启动子进程并加载模型，速度慢。我们做了常驻 worker：模型只加载一次，之后多次请求复用。

结果：

```text
50 组案例，650 次评分调用
subprocess 模式：168.6s
persistent worker：23.4s
加速：约 7.2x
Top 1 一致：50/50
Top 3 overlap：1.0000
assessment 一致：50/50
```

这说明 worker 加速没有改变模型结论，适合作为最终演示模式。

相关证据：

| 内容 | 文件 |
|---|---|
| Worker 对比表 | `report/tables/persistent_worker_comparison.csv` |
| Worker 对比日志 | `report/logs/persistent_worker_comparison.txt` |
| 运行时间汇总 | `report/tables/inference_runtime.csv` |

### 8. LightOPA 轻量模型探索

除了 SimOPA 主线，我们还训练了自己的轻量评分 baseline，输入为 4 通道：

```text
RGB + mask
```

结果：

| 模型 | 参数量 | accuracy | ROC-AUC | 平均推理 |
|---|---:|---:|---:|---:|
| tiny-lightopa-cnn-v1 | 79,425 | 0.6500 | 0.6761 | 12.36 ms/sample |
| residual-lightopa-cnn-v1 | 1,113,377 | 0.6717 | 0.7084 | 11.50 ms/sample |

答辩口径：LightOPA 是轻量模型探索，不替代最终演示的 SimOPA worker。它的价值是证明我们做了模型本体层面的训练尝试，并且 residual 版本相对 tiny 有提升。

相关证据：

| 内容 | 文件 |
|---|---|
| LightOPA 对比表 | `report/tables/lightopa_model_comparison.csv` |
| Tiny 训练日志 | `report/logs/lightopa_tiny_training.txt` |
| Residual 训练日志 | `report/logs/lightopa_residual_training.txt` |

## 答辩高频问题

### Q1：你们到底用了什么模型？

A：主线使用 OPA 项目的 SimOPA 模型，它是物体放置合理性评分模型，输入合成图和前景 mask，输出放置是否合理的分数。我们把它封装进 FastAPI 后端，用于多个候选位置的 Top 3 排序。

### Q2：你们是不是只是调用现成模型？

A：不是只调用。现成 SimOPA 只负责对合成图评分，我们做了应用层和模型实验层的扩展：候选池生成与 Top 3 排序、RGB/mask 消融、分数校准、IoU 去重、鲁棒性扰动、遮挡解释、常驻 worker 加速，以及 LightOPA tiny/residual 轻量 baseline。

### Q3：你们有没有改模型结构？

A：对 SimOPA 主干网络没有硬改 backbone，这样可以保证主线稳定。我们的模型侧改动主要是应用适配和实验分析：输入 mask 消融、输出校准、候选排序、去重、解释和服务化。除此之外，我们训练了 LightOPA tiny/residual 两个 4 通道轻量 CNN baseline，属于模型本体层面的补充探索。

### Q4：为什么不用自己训练的 LightOPA 作为最终模型？

A：LightOPA 是轻量 baseline，用来探索小模型可行性。它的准确率和 ROC-AUC 低于成熟的 SimOPA，因此最终演示仍使用更可靠的 SimOPA worker。LightOPA 的价值是补充模型本体实验，而不是替代主线。

### Q5：你们怎么证明 mask 有用？

A：我们做了 RGB/mask 消融，同一批 234 个候选分别用真实 object mask、bbox mask 和 blank mask 评分。object mask 与 blank mask 的平均绝对差异是 0.3487，Top 3 成员变化 56 条，说明 mask 明显影响模型判断。

### Q6：为什么正例不是 50/50 都进 Top 3？

A：100 组里正例 44/50 进入 Top 3，剩下 6 个大多是高分但排名低的边界情况。原因是 SimOPA 对一些相近候选都会给接近 1.0 的高分，也就是分数饱和。我们没有回避这个问题，而是通过分数校准、IoU 去重和边界案例分析解释它。

### Q7：负例 50/50 低分拒绝是什么意思？

A：这表示 OPA 标注为不合理的位置，SimOPA 对原始标注位置都给了低分。它证明模型对明显不合理放置有较稳定的拒绝能力。不过个别负例中，候选池里的其他位置可能会高分，这并不矛盾，因为其他位置可能比原始坏位置更合理。

### Q8：模型输出的 0-1 分数能直接当概率吗？

A：不能严格当概率。它更接近模型置信度或合理性分数。我们通过分数校准和三档标签，把它转换成推荐系统更易解释的结果：推荐、可接受、不推荐。

### Q9：为什么需要 IoU 去重？

A：如果只按分数排序，Top 3 可能是非常接近甚至重叠的位置，用户看起来没有选择空间。IoU 去重可以让推荐位置更分散，提升 Web 交互的实用性。

### Q10：你们的可解释性怎么做？

A：我们用遮挡敏感性分析。把图像分成 6x6 网格，每次遮挡一个区域，观察分数变化。分数下降大的区域就是模型比较依赖的区域。5 个代表案例平均最大分数下降 0.5472，并生成了热力图。

### Q11：鲁棒性实验说明什么？

A：我们对 mask、位置和尺度做小扰动，观察分数是否剧烈变化。平均绝对变化是 0.0820，说明多数轻微扰动下结果比较稳定；但最大变化达到 0.9455，说明部分边界案例对位置变化敏感，这也是后续可以改进的方向。

### Q12：为什么要做 simopa-worker？

A：因为如果每次评分都重新启动子进程并加载模型，速度很慢。worker 模式让模型常驻内存，50 组排序从 168.6s 降到 23.4s，约 7.2 倍加速，而且 Top 1、Top 3 和 assessment 都保持一致。

### Q13：你们的最终演示用哪个模式？

A：最终演示推荐使用 `simopa-worker`。它是真实 SimOPA 模型推理，同时速度比普通 subprocess 模式快很多。没有模型环境时可以用 `mock` 模式先验证 Web 页面。

### Q14：项目有哪些局限？

A：主要有三点。第一，SimOPA 分数有饱和现象，多个候选可能都接近 1.0。第二，候选生成目前是规则候选池，不是学习式生成。第三，LightOPA 只是轻量 baseline，效果还不足以替代 SimOPA。我们已经用校准、去重、边界案例和鲁棒性实验把这些局限讲清楚。

### Q15：如果继续做，下一步模型侧怎么升级？

A：可以做三个方向：第一，用更多数据训练更强的轻量模型，比如 ResNet18 或 MobileNet；第二，用学习式候选生成替代规则候选池；第三，把解释性从离线遮挡实验升级为更高效的 Grad-CAM 或 Web 实时解释。

## 老师追问时的安全口径

可以说：

```text
我们没有声称从零训练或重写 SimOPA，而是基于 OPA/SimOPA 做了完整应用适配和高标准实验验证。
主线贡献是把评分模型变成可交互的 Top 3 物体放置推荐系统，并补充了消融、校准、去重、解释、鲁棒性、性能优化和轻量模型 baseline。
```

不要说：

```text
我们重写了 SimOPA。
LightOPA 已经超过 SimOPA。
模型输出就是严格概率。
Android 是我们的主线。
```

