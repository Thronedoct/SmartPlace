# 阶段状态与下一步行动

本文是当前阶段状态和短期行动清单的唯一维护入口。每次阶段推进后更新本文；接口变化更新 `docs/API.md`；模型路线变化更新 `docs/model_plan.md`；案例和验证结果更新 `docs/TEST_CASES.md`。

## 当前阶段

项目处于 Phase 0 到 Phase 1 的衔接阶段：

- 协作环境、基础文档和 mock 后端已经建立。
- 后端推荐逻辑已抽到 `server/recommender.py`，便于后续替换真实 OPA/libcom scorer。
- FastAPI mock 已能从上传背景图中解析 PNG/JPEG/GIF 尺寸，并返回 `image_width`、`image_height`。
- 模型路线已明确：基于 OPA/libcom 源码做适配和轻量微调，不从零训练新模型。
- Android 端可以继续使用课程 Demo，也可以重建；无论哪种方式都必须遵守 `docs/API.md`。

## 已完成

- 已检查课程 Android Demo，并保留为 `OPAAndroidDemoSimp/` 参考骨架。
- 已新增根目录项目说明。
- 已新增接口约定文档。
- 已新增协作流程文档。
- 已新增测试案例模板。
- 已新增模型计划文档，并合并课程参考源码审阅、高分模型方案、训练/端侧推理分析。
- 已在 `main` 分支初始化 Git 仓库。
- 已新增 FastAPI mock 服务。
- 已新增无额外依赖的标准库 mock 服务，并完成本地验证。
- 已将前期拆分文档合并，当前 docs 维护入口收敛为：
  - `docs/API.md`
  - `docs/WORKFLOW.md`
  - `docs/model_plan.md`
  - `docs/PHASE0_STATUS.md`
  - `docs/TEST_CASES.md`

## 当前决定

### 模型

- 主线：OPA/libcom baseline + RGB vs RGB+mask 本体改动 + Top 3 候选排序 + OPA 小子集 fine-tune + Grad-CAM/遮挡解释。
- 本地训练：8GB RTX 5070 Laptop GPU 可跑 baseline 和小 batch 微调；16GB RTX 4070 TiS 更适合稳定 fine-tune 和解释实验。
- 手机端推理：第一版不做真实模型端侧推理，Android 负责交互、上传、展示、手动调整和保存；真实模型推理由后端完成。
- TopNet/FOPA：作为进阶候选生成路线，不阻塞主链路。

### 前端

- Android 端可继续使用 `OPAAndroidDemoSimp/`，也可重建项目。
- 如果重建 Android，需要先写清目录名、技术栈和仍然遵守的 API 字段。
- 第一目标是接入 `/api/place/recommend`，解析 `candidates`，展示 Top 3。

### 后端

- API 字段以 `docs/API.md` 为准。
- 后端 scorer 目标签名：

```text
score_composite(composite_image, foreground_mask, model_version) -> score
```

## 立即任务

| 优先级 | 任务 | 负责人 | 输出物 |
|---:|---|---|---|
| P0 | 决定 Android 是否重建，并给出项目目录名。 | 成员 C | 前端路线说明、最小页面或 Demo 改造分支 |
| P0 | Android 调用 `/api/place/recommend` mock 接口。 | 成员 C | 请求日志、Top 3 展示截图 |
| P0 | 下载并审计 OPA 小子集。 | 成员 A | `assets/datasets/opa/notes.md`、`opa_sample_audit.csv` |
| P0 | 跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py`。 | 成员 A | 运行命令、截图、分数输出 |
| P1 | 后端定义 scorer 接口和 mock/真实模型开关。 | 成员 B | `score_composite` 函数、配置说明 |
| P1 | 生成候选评分表。 | 成员 A、B | `candidate_ranking_v1.csv` |
| P1 | 将联调案例写入 `docs/TEST_CASES.md`。 | A、B、C | 至少 3 组 mock 联调案例 |

## 下一次同步需要回答

1. Android 是否继续使用 `OPAAndroidDemoSimp/`？
2. 模型权重是否已经能下载并加载？
3. OPA 数据集小子集是否已经审计完成？
4. 后端真实 scorer 的输入格式是否确定为 composite image + foreground mask？
5. `docs/API.md` 是否需要增加错误响应或候选预览图字段？
6. 哪些截图、日志或录屏已经可以放入 `report/`？

