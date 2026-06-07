# SmartPlace

SmartPlace 是本课程方向 A 的项目：智能物体放置与合成图质量评价。

项目目标是做一个 Web 物体放置工作台。用户在网页中选择背景图和前景物体后，系统把图片发送给后端推理服务，由后端生成候选位置、调用 OPA/libcom 或改造后的评分模型，并把推荐位置、合理性分数和可视化证据返回给网页展示。

## 当前阶段

目前已经完成 Web 工作台、FastAPI 后端、OPA/SimOPA 真实模型接入和主要模型证据。FastAPI 推荐接口可以通过 `SMARTPLACE_SCORER=simopa` 返回真实模型评分后的 Top 3，也可以通过 `simopa-lite` 使用候选预算模式，并通过 `simopa-worker` 使用常驻模型 worker；18 组、50 组和 100 组候选排序、RGB/mask ablation、分数校准、IoU 去重、代表案例、遮挡解释、鲁棒性 ablation、full-vs-lite 对比、subprocess-vs-worker 对比、LightOPA tiny/residual 轻量模型探索、运行耗时表和模型改动说明表已经写入 `report/`。Web 工作台已支持内置案例加载、结果 JSON/CSV 导出、可信度提示、解释图入口、前端美化和课堂演示模式。最终报告、PPT 和录屏由队友基于这些证据整理。

- `web/`：当前主线前端，负责图片输入、参数控制、Top 3 候选展示和演示截图。
- `server/`：后端推理服务，支持 mock scorer、SimOPA 真实 scorer、SimOPA Lite 候选预算模式和 SimOPA Worker 常驻模型模式。
- `docs/ROADMAP.md`：路线、当前状态、分工、下一步和 GitHub 流程。
- `docs/API.md`：Web 前端与后端之间的接口约定。
- `docs/model_plan.md`：模型细节、参考源码、实验方案和解释计划。
- `docs/TEST_CASES.md`：测试案例和工程验证记录。
- `report/README.md`：给队友写报告、做 PPT、录屏用的证据交接索引。
- `OPAAndroidDemoSimp/`：课程提供的 Android 参考骨架，仅作为参考和素材来源，不作为本项目交付主线。

当前核心原则是：保持 Web + FastAPI + `simopa-worker` 的稳定闭环，在不破坏主线的前提下继续做低风险加码；随后进行前端重构级美化和项目结构深度整理，最后把脚本、表格、日志、截图、演示流程和证据索引整理成队友可直接接手的交付包。

课程 PDF 明确允许 Web 应用、手机 App 原型或电脑端应用软件。SmartPlace 选择 Web 应用作为交付形态，不再开发 Android 端。

## 目录结构

```text
SmartPlace/
|-- OPAAndroidDemoSimp/      # 课程 Android Demo 骨架
|-- server/                  # FastAPI 后端推理服务
|-- docs/                    # 路线、接口、模型计划、测试记录
|-- web/                     # Web 演示工作台
|-- scripts/                 # 交付前核心验证脚本
|-- assets/                  # 测试图片和共享素材
|-- report/                  # 报告、PPT、截图、录屏材料
`-- README.md
```

## 快速运行

仅做前端连通性调试时，可以运行无额外依赖的 mock 后端：

```bash
python server/mock_stdlib.py --host 0.0.0.0 --port 8000
```

如果已经安装 FastAPI 依赖，也可以运行正式后端入口：

```bash
python -m pip install -r server/requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Windows 本地虚拟环境可使用：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

推荐课堂演示启动方式：

```powershell
.\scripts\start_demo_server.ps1
```

生成最终 Web 截图：

```powershell
.\scripts\capture_web_demo.ps1
```

运行真实 SimOPA scorer：

```powershell
$env:SMARTPLACE_SCORER='simopa'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

运行轻量候选预算模式：

```powershell
$env:SMARTPLACE_SCORER='simopa-lite'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

运行常驻 SimOPA worker 模式：

```powershell
$env:SMARTPLACE_SCORER='simopa-worker'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

检查后端状态：

```bash
curl http://127.0.0.1:8000/api/health
```

运行交付前核心检查：

```powershell
.\scripts\verify_core.ps1
```

该脚本会覆盖后端单测、Python 编译、Web 模块语法、交付包资产检查、仓库卫生检查、证据汇总刷新、旧阶段口径扫描和 Git whitespace 检查。真实 SimOPA API smoke 仍按需单独运行，避免每次检查都启动重模型。

Web 工作台访问：

```text
http://127.0.0.1:8000/
```

前端调用接口：

```text
POST http://127.0.0.1:8000/api/place/recommend
```

## 小组分工

- 成员 A：模型改造、轻量模型探索和模型实验证据。
- 成员 B：FastAPI 推理服务、候选推荐管线和运行日志证据。
- 成员 C：Web 交互展示、前端美化、内置案例和演示验收。
- 材料负责人/队友：最终报告、PPT、演示录屏、AI 辅助说明和排版整合。

工程侧负责把脚本、表格、日志、截图和演示流程整理清楚；最终材料由材料负责人基于这些证据统一写作和排版。
