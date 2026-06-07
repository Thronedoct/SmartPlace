# SmartPlace

SmartPlace 是课程方向 A「智能物体放置与合成图质量评价」项目。项目交付形态是一个 Web 物体放置工作台：用户选择背景图和前景物体后，FastAPI 后端生成候选位置，调用 OPA/SimOPA 评分模型，返回 Top 3 推荐位置、合理性分数、可信度提示和解释证据。

Android Demo 只作为老师提供的参考素材，不是本项目主线。

## 一键运行

启动最终演示服务：

```powershell
.\start_demo.ps1
```

默认模式是 `simopa-worker`，即最终展示主线：Web + FastAPI + 常驻 SimOPA 模型 worker。启动后打开：

```text
http://127.0.0.1:8000/
```

停止服务：

```powershell
.\stop_demo.ps1
```

常用变体：

```powershell
.\start_demo.ps1 -Scorer mock
.\start_demo.ps1 -ModelPython "D:\DevTools\Anaconda\envs\study\python.exe"
```

## 交付命令

```powershell
.\scripts\verify_core.ps1
.\scripts\capture_web_demo.ps1
.\scripts\export_handoff_package.ps1
.\scripts\export_full_project_package.ps1
```

- `verify_core.ps1`：核心验证，覆盖后端单测、Python 编译、Web/PowerShell 语法、交付资产、仓库卫生、证据汇总和旧口径扫描。
- `capture_web_demo.ps1`：重新生成桌面、演示模式和移动端 Web 截图。
- `export_handoff_package.ps1`：导出轻量材料包到 `report/exports/smartplace_handoff.zip`，不含 raw 数据和模型权重。
- `export_full_project_package.ps1`：导出项目运行包到 `report/exports/smartplace_project_no_dataset.zip`，包含源码、模型、external 和证据材料；默认不含 4.6GB OPA raw 数据集。

## 当前成果

- Web 工作台：浅色三栏界面、内置案例、Top 3 候选框、JSON/CSV 导出、可信度提示、解释图入口、演示模式。
- 后端服务：FastAPI 推荐接口，支持 `mock`、`simopa`、`simopa-lite`、`simopa-worker`、`simopa-lite-worker`。
- 模型证据：真实 SimOPA、100 组候选排序、RGB/mask ablation、分数校准、IoU 去重、鲁棒性、遮挡解释。
- 性能证据：`simopa-lite` 候选预算对比、`simopa-worker` 常驻模型加速对比。
- 轻量模型探索：LightOPA tiny/residual baseline。
- 交付材料：关键表格、日志、案例图、解释热力图、Web 最终截图和队友交接索引。

## 目录

```text
SmartPlace/
|-- start_demo.ps1          # 根目录启动入口
|-- stop_demo.ps1           # 根目录停止入口
|-- web/                    # Web 工作台
|-- server/                 # FastAPI 后端和 scorer 边界
|-- experiments/            # 模型实验和证据生成脚本
|-- report/                 # 表格、日志、截图、交接索引和导出包
|-- docs/                   # API、路线、模型计划、测试记录
|-- scripts/                # 验证、截图、导出等交付脚本
|-- assets/                 # OPA split 和数据说明，raw 数据不提交
|-- models/                 # 权重说明，权重文件不提交
|-- external/               # 外部源码说明，源码目录不提交
`-- OPAAndroidDemoSimp/     # 课程 Android 参考 Demo，归档参考
```

## 文档入口

- [report/README.md](report/README.md)：队友写报告、做 PPT、录屏时优先看这里。
- [HANDOFF_FULL_PROJECT.md](HANDOFF_FULL_PROJECT.md)：项目交付包说明，解释打包内容、未打包内容和队友到手后的操作。
- [docs/ROADMAP.md](docs/ROADMAP.md)：项目定位、完成状态和剩余材料任务。
- [docs/API.md](docs/API.md)：接口约定。
- [docs/model_plan.md](docs/model_plan.md)：模型与实验细节。
- [docs/TEST_CASES.md](docs/TEST_CASES.md)：验证记录。
- [server/README.md](server/README.md)：后端模式和接口说明。

## 分工口径

- 工程侧：维护 Web、后端、模型实验、验证脚本、截图、表格、日志和交付包。
- 材料侧：基于 `report/README.md` 写最终报告、PPT、录屏、AI 辅助说明和成员分工。
