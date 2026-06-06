# 下一阶段路线

本文是当前推进顺序的短路线图。详细模型方案仍以 `docs/model_plan.md` 为准；评分口径和交付证据以 `docs/HIGH_SCORE_ROUTE.md` 为准；阶段事实记录以 `docs/PHASE0_STATUS.md` 为准。

## 当前基线

已经具备：

- Web 工作台 + FastAPI 后端主链路。
- OPA/SimOPA 真实 scorer，`SMARTPLACE_SCORER=simopa` 可返回真实 Top 3。
- OPA 全量数据集本地可用，`smoke_100.csv` 已审计。
- 18 组候选排序实验已完成，输出 `candidate_ranking_v1.csv`、`opa_18_case_summary.csv` 和 `candidate_ranking_v1.txt`。

当前最重要的结论：

- 正例 8/9 的 OPA 标注位置高分且进入 Top 3。
- 负例 9/9 的 OPA 标注坏位置得分为 0.0。
- `opa_test_002` 暴露了分数饱和问题：标注位置分数高，但多个候选也接近 1.0，导致排序不稳定。

## 总体优先级

下一阶段不要先追 TopNet、FOPA 或 Android。优先把已有主线做成“能解释、能对比、能展示”的高分证据链：

```text
18 组候选排序证据
-> RGB/mask 对比与 ablation
-> 分数校准和候选去重
-> Web 可视化截图与失败案例分析
-> Grad-CAM / 遮挡解释
-> 报告与 PPT 整合
```

## P1：模型对比与分数可信度

目标：回答“模型到底改了什么，为什么分数可信，为什么 Top 3 不是随便排的”。

### 1. RGB/mask 对比

输出：

```text
experiments/opa_rgb_mask/run_mask_ablation.py
report/tables/rgb_vs_mask_comparison.csv
report/logs/rgb_vs_mask_comparison.txt
```

做法：

- 在同一批 18 组候选上比较真实 mask、全 1 mask、弱化 mask 或 box mask。
- 记录每个候选的分数变化、Top 3 是否变化、负例坏位置是否仍被拒绝。
- 报告中把它解释为“mask 对前景区域定位和合理性判断的作用”。

验收：

- 至少 18 组案例都有对比结果。
- 表格中能看到 mask 改变会影响一部分候选分数或排序。
- 能指出至少 1 个 mask 有帮助的案例和 1 个 mask 不足的案例。

### 2. 分数校准与候选去重

输出：

```text
experiments/opa_baseline/run_score_calibration.py
report/tables/score_calibration_v1.csv
report/tables/candidate_dedup_v1.csv
```

做法：

- 对候选分数做简单校准：例如按验证子集统计阈值，或用 logistic/isotonic calibration。
- 对候选框做 IoU 去重，避免 `opa_test_002` 这类多个候选同时接近 1.0 的饱和排序。
- 保持 API 输出仍是 0-1 分数和三档标签。

验收：

- `opa_test_002` 这类饱和案例有解释和改进方案。
- Top 3 中高度重叠候选减少。
- 三档标签阈值能用实验表支撑，而不是拍脑袋。

## P1：Web 展示与报告案例

目标：把模型结果转成老师能一眼看懂的应用证据。

输出：

```text
report/screenshots/
report/tables/failure_cases.csv
report/tables/representative_cases.csv
```

做法：

- 从 18 组中选 3-5 组代表案例：
  - 2 个成功正例。
  - 1 个明显拒绝负例。
  - 1 个分数饱和或排序边界案例。
  - 1 个失败/局限案例。
- 用 Web 工作台截图保存 Top 3、分数、模型版本、耗时。
- 为每组写人工判断和失败原因。

验收：

- 报告里至少有 3 组带图案例。
- 每组都有 `model_version`、`runtime_ms`、候选框、分数和人工判断。
- 至少有一个失败/边界案例，而不是只展示好结果。

## P2：模型解释

目标：争取解释性加分。

输出：

```text
experiments/explainability/
report/screenshots/explainability/
report/tables/explainability_cases.csv
```

做法：

- 优先做遮挡实验：遮挡前景、支撑区域、背景其他区域，观察分数变化。
- 如果时间允许再做 Grad-CAM。
- 解释成功案例为什么高分，失败案例为什么误判或饱和。

验收：

- 至少 3 组案例有解释图或遮挡分数表。
- 能用一句话说明模型关注了什么区域。

## 暂缓事项

这些不是当前第一优先级：

- Android 接入。
- TopNet 主线接入。
- FOPAHeatMapModel 替代候选生成。
- 大规模 fine-tune。
- 云端部署到公网。

它们可以作为时间充裕时的进阶项，但不能阻塞 RGB/mask 对比、分数校准、Web 截图和报告证据。

## 最近三步

1. 合并候选排序 PR，保证 `main` 有 18 组证据。
2. 做 `rgb_vs_mask_comparison.csv`。
3. 选 3-5 组代表案例，产出 Web 截图和失败分析。
