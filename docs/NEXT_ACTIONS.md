# 下一阶段行动清单

本文用于承接“先规划再行动”的执行节奏。每轮开发前先更新目标与验收标准；每轮开发后同步状态、测试和证据。

## 当前阶段目标

从 Phase 0 进入 Phase 1，目标不是一次性完成真实模型，而是先完成两条可证明的链路：

1. Android 或重建前端能够请求 mock 后端并展示 Top 3。
2. 模型侧能够独立跑通 OPA/libcom 评分，形成真实模型调用证据。

## 本轮已确定路线

| 方向 | 当前决定 | 验收标准 |
|---|---|---|
| 参考源码 | 优先使用课程 PDF 中方向 A 的 BCMI 仓库，详见 `docs/SOURCE_REVIEW.md`。 | 文档中记录仓库定位、用途和落地优先级。 |
| 后端 | 保留 FastAPI + 标准库 mock；推荐逻辑抽到 `server/recommender.py`。 | 单元测试通过，API 字段保持兼容。 |
| 前端 | Android 可继续改 Demo，也可重建；必须遵守 `docs/API.md`。 | 能上传背景/前景，解析 `candidates`，展示 Top 3。 |
| 模型 | 先跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py`，再接入后端。 | 有日志、输入输出、权重路径和分数截图。 |

## 立即任务

| 优先级 | 任务 | 负责人 | 输出物 |
|---:|---|---|---|
| P0 | 决定 Android 是否重建，并给出项目目录名。 | 成员 C | 前端路线说明、最小页面或 Demo 改造分支 |
| P0 | Android 调用 `/api/place/recommend` mock 接口。 | 成员 C | 请求日志、Top 3 展示截图 |
| P0 | 跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py`。 | 成员 A | 运行命令、截图、分数输出 |
| P1 | 后端定义 scorer 接口和 mock/真实模型开关。 | 成员 B | `score_composite` 函数、配置说明 |
| P1 | 将联调案例写入 `docs/TEST_CASES.md`。 | A、B、C | 至少 3 组 mock 联调案例 |

## 下一次同步需要回答

1. Android 是否继续使用 `OPAAndroidDemoSimp/`？
2. 模型权重是否已经能下载并加载？
3. 后端真实 scorer 的输入格式是否确定为 composite image + foreground mask？
4. `docs/API.md` 是否需要增加错误响应或候选预览图字段？
5. 哪些截图、日志或录屏已经可以放入 `report/`？
