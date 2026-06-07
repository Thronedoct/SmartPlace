# SmartPlace 路线与状态

本文是项目路线和当前状态的唯一入口。不要再新增单独的阶段状态、高分路线或下一步文档。

## 项目定位

SmartPlace 选择课程方向 A：智能物体放置与合成图质量评价。

主线是：

```text
Web 工作台
-> FastAPI 本地推理服务
-> simopa-worker 真实 OPA/SimOPA scorer
-> Top 3 物体放置候选
-> 可信度、校准、去重、解释性和运行时间证据
```

不做 Android 端。`OPAAndroidDemoSimp/` 只是课程参考 Demo 和素材来源。

## 当前完成度

### 应用闭环

- Web 工作台已完成：上传/内置案例、候选框、Top 3、JSON/CSV 导出、可信度提示、解释图入口、演示模式。
- 5 组内置案例已抽到 `assets/demo_cases/`，项目运行包无需携带完整 OPA raw 数据集也能加载案例。
- FastAPI 后端已完成：`/api/health`、`/api/place/recommend`、`/api/demo/cases`。
- Scorer 模式已完成：`mock`、`simopa`、`simopa-lite`、`simopa-worker`、`simopa-lite-worker`。
- 最终演示模式：`.\start_demo.ps1` 启动 `simopa-worker`，访问 `http://127.0.0.1:8000/`。

### 模型和实验

- OPA/SimOPA 真实权重已本地推理。
- 18 / 50 / 100 组候选排序实验已完成。
- 100 组 worker 排序：50 正例、50 负例、1300 条候选评分；正例 44/50 的 OPA 标注位置进入 Top 3，负例 50/50 低分拒绝。
- RGB/mask ablation 已完成，object mask 与 blank mask 平均绝对差异为 `0.3487`。
- 分数校准和 IoU 去重已完成，`opa_test_002` 保留为分数饱和边界案例。
- 遮挡解释和鲁棒性 ablation 已完成。
- `simopa-worker` 将 50 组 full ranking 从 `168.6s` 降到 `23.4s`，Top 1、Top 3 和 assessment 保持一致。
- LightOPA tiny/residual baseline 已完成，residual ROC-AUC 从 `0.6761` 提升到 `0.7084`。

### 交付证据

- 表格：`report/tables/`
- 日志：`report/logs/`
- 案例图：`report/screenshots/cases/`
- 解释热力图：`report/screenshots/explainability/`
- Web 最终截图：`report/screenshots/web/`
- 队友交接索引：`report/README.md`
- 轻量材料包导出：`.\scripts\export_handoff_package.ps1`
- 完整项目包导出：`.\scripts\export_full_project_package.ps1`

## 当前不做

- Android 主线开发。
- TopNet/FOPA 主线替换。
- 大规模 fine-tune。
- 公网部署。
- 提交 raw 数据、模型权重、external 源码、本地虚拟环境或本地依赖缓存。

## 最后剩余

工程侧已经整理到可交付状态。材料侧还需要：

```text
最终报告 PDF
PPT
演示录屏，放入 report/videos/
AI 辅助说明
成员分工说明
```

录屏完成后运行：

```powershell
.\scripts\verify_handoff_assets.ps1 -RequireVideos
.\scripts\export_handoff_package.ps1 -RequireVideos
```

如果队友需要自己运行完整项目，导出完整项目包：

```powershell
.\scripts\export_full_project_package.ps1
```

默认包会包含源码、模型权重、external 参考源码和本地模型依赖缓存，但不包含 4.6GB OPA raw 数据集；说明见 `HANDOFF_FULL_PROJECT.md`。

## 验证与 GitHub 流程

合并前运行：

```powershell
.\scripts\verify_core.ps1
```

日常流程：

```text
codex/* 分支
-> Draft PR
-> 本地验证
-> 检查 bot review
-> squash merge 到 main
```

`main` 只保留稳定、可展示、可交付版本。GitHub CLI 优先使用沙箱外已授权的 `gh`；不要把 GitHub PAT 或 API key 发到聊天、文档、脚本或日志里。
