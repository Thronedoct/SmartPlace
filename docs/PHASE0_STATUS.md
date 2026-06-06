# 阶段状态与下一步行动

本文是当前阶段状态和短期行动清单的唯一维护入口。每次阶段推进后更新本文；接口变化更新 `docs/API.md`；模型路线变化更新 `docs/model_plan.md`；案例和验证结果更新 `docs/TEST_CASES.md`；高分路线变化更新 `docs/HIGH_SCORE_ROUTE.md`。

## 当前阶段

项目处于 Phase 0 到 Phase 1 的衔接阶段：

- 协作环境、基础文档、Web mock 工作台和 mock 后端已经建立。
- 后端推荐逻辑已抽到 `server/recommender.py`，便于后续替换真实 OPA/libcom scorer。
- FastAPI mock 已能从上传背景图中解析 PNG/JPEG/GIF 尺寸，并返回 `image_width`、`image_height`。
- Web 前端已能通过 `/api/place/recommend` 上传背景图和前景图，并展示 Top 3 候选框、分数、模型版本和耗时。
- 课程 PDF 已重新阅读并确认：Web 应用是允许的交付形态，`OPAAndroidDemoSimp/` 仅作为课程参考骨架，不纳入项目主线。
- 模型路线已明确：基于 OPA/libcom 源码做适配和轻量微调，不从零训练新模型。

## 已完成

- 已检查课程 Android Demo，并保留为 `OPAAndroidDemoSimp/` 参考骨架和素材来源。
- 已新增根目录项目说明。
- 已新增接口约定文档。
- 已新增协作流程文档。
- 已新增测试案例模板。
- 已新增模型计划文档，并合并课程参考源码审阅、高分模型方案、训练和解释计划。
- 已新增高分路线文档 `docs/HIGH_SCORE_ROUTE.md`。
- 已在 `main` 分支初始化 Git 仓库。
- 已新增 FastAPI mock 服务。
- 已新增无额外依赖的标准库 mock 服务，并完成本地验证。
- 已修复 `.venv`，当前虚拟环境指向 Python 3.12，并可导入 FastAPI。
- 已新增 `server/scorer.py`，提供 `score_composite(...)` scorer 边界和 mock/真实模型替换入口。
- 已克隆模型参考仓库到 `external/`：`libcom`、OPA、TopNet。
- 已在 `study` 环境配合 `.model-packages/` 准备 OPA baseline 依赖。
- 已下载并解压 OPA score 权重 `OPA_checkpoints.zip`，`simopa.pth` 与 `simopa_ext.pth` 已放到本地。
- 已通过 `experiments/opa_baseline/run_simopa_smoke.py` 跑通 SimOPA baseline，CUDA 设备为 `cuda:0`。
- 已确认用户下载的 OPA 全量数据位于 `assets/datasets/opa/raw/new_OPA`。
- 已生成 `smoke_100.csv` 和 `opa_sample_audit.csv`，100 条 test 样例全部可读。
- 已将文档维护入口收敛为：
  - `docs/API.md`
  - `docs/HIGH_SCORE_ROUTE.md`
  - `docs/WORKFLOW.md`
  - `docs/model_plan.md`
  - `docs/PHASE0_STATUS.md`
  - `docs/TEST_CASES.md`

## 当前决定

### 应用

- 主线交付形态：Web 物体放置工作台。
- 不做 Android 端。课程 Android Demo 只作为参考，不参与最终主流程验收。
- 第一目标是 Web + 后端 + 真实模型的端到端主链路：
  - 上传背景图和前景图。
  - 后端生成候选位置。
  - 真实模型评分。
  - 前端展示 Top 3、分数、标签、耗时和模型版本。

### 模型

- 主线：OPA/libcom baseline + RGB vs RGB+mask 本体改动 + Top 3 候选排序 + 0-1 分数/三档标签 + OPA 小子集 fine-tune + Grad-CAM/遮挡解释。
- 本地训练：8GB RTX 5070 Laptop GPU 可跑 baseline 和小 batch 微调；16GB RTX 4070 TiS 更适合稳定 fine-tune 和解释实验。
- 本地/局域网推理：第一版把真实模型放在本地电脑或 FastAPI 服务中，便于展示日志、权重加载和张量推理证据。
- TopNet/FOPA：作为进阶候选生成路线，不阻塞主链路。

### 后端

- API 字段以 `docs/API.md` 为准。
- 后端 scorer 目标签名：

```text
score_composite(composite_image, foreground_mask, model_version) -> score
```

- 后端需要支持 mock/真实模型开关，保证 Web 前端不用因为模型替换而改接口。

## 立即任务

| 优先级 | 任务 | 负责人 | 输出物 |
|---:|---|---|---|
| P0 | 跑通并记录 FastAPI 服务启动、健康检查和 Web 首页访问。 | B | `.tmp-uvicorn.latest.err.log`、健康检查输出 |
| P0 | 将 OPA SimOPA baseline 封装进 `server/scorer.py`。 | A、B | 真实 `score_composite`、`model_version=simopa-*`、接口日志 |
| P0 | 将 `score_composite` 从 mock 占位替换为真实 OPA/libcom scorer。 | A、B | scorer 函数、模型版本字段、耗时日志 |
| P0 | Web 工作台稳定展示 Top 3，补充候选切换、错误提示和运行证据字段。 | C | Web 截图、演示录屏 |
| P0 | 从 OPA smoke 样例中挑选 18 组报告案例。 | A、C | 18 组案例截图、人工判断、失败原因 |
| P1 | 生成候选评分表。 | A、B | `report/tables/candidate_ranking_v1.csv` |
| P1 | 做 RGB vs RGB+mask 对比。 | A | `report/tables/rgb_vs_mask_comparison.csv` |
| P1 | 将真实联调案例写入 `docs/TEST_CASES.md`。 | A、B、C | 至少 6 组真实模型案例 |
| P2 | 生成 Grad-CAM 或遮挡实验解释图。 | A | 成功/失败案例解释图和分析 |

## 下一次同步需要回答

1. FastAPI 环境是否已经能稳定启动？
2. 模型权重是否已经能下载、加载并对样例输出分数？
3. scorer 的输入格式是否确定为 composite image + foreground mask？
4. Web 是否已经能展示真实模型返回的 Top 3？
5. `docs/API.md` 是否需要增加错误响应、候选预览图或导出字段？
6. 哪些截图、日志、表格或录屏已经可以放入 `report/`？

## 2026-06-06 推进记录

- 已将 OPA/SimOPA scorer 接入 `server/scorer.py`，支持 `SMARTPLACE_SCORER=mock` 和 `SMARTPLACE_SCORER=simopa`。
- 已新增候选池评分排序逻辑：SimOPA 模式下先生成候选池，再按真实模型分数返回 Top N。
- 已新增 `experiments/opa_baseline/score_candidates.py`，用于把 background/foreground/mask 和候选框合成为 SimOPA 输入。
- 已新增 `experiments/opa_baseline/run_api_simopa_smoke.py`，可临时启动 FastAPI 并发起真实 multipart 推荐请求。
- 已生成 `report/tables/api_simopa_smoke.csv` 和 `report/logs/api_simopa_smoke.txt`。
- 当前 API smoke 结果：`model_version=simopa-rgb-mask-v1`，Top 3 分数为 `0.998`、`0.8495`、`0.6471`，接口耗时约 `3.7s`。
- FastAPI health 在 SimOPA 模式下返回 `service=smartplace-inference`、`scorer_mode=simopa`、`scorer_status=ready`。

## 下一步重点

1. Web 工作台接收真实 SimOPA 分数时补充错误状态、mode 显示和运行证据字段。
2. 从 `smoke_100.csv` 中筛选 18 组报告案例，覆盖合理、悬空、边缘、尺度错误和失败案例。
3. 生成 `candidate_ranking_v1.csv`，记录每个案例的候选池分数、Top 3 和人工判断。
4. 开始 RGB vs RGB+mask 对比实验，形成模型本体类改动证据。
