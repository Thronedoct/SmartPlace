# SmartPlace

SmartPlace 是本课程方向 A 的项目：智能物体放置与合成图质量评价。

项目目标是做一个 Web 物体放置工作台。用户在网页中选择背景图和前景物体后，系统把图片发送给后端推理服务，由后端生成候选位置、调用 OPA/libcom 或改造后的评分模型，并把推荐位置、合理性分数和可视化证据返回给网页展示。

## 当前阶段

目前处于 Phase 0 到 Phase 1 的衔接：协作环境、Web 工作台、后端服务和 OPA/SimOPA baseline 已搭建，FastAPI 推荐接口已经可以通过 `SMARTPLACE_SCORER=simopa` 返回真实模型评分后的 Top 3。

- `web/`：当前主线前端，负责图片输入、参数控制、Top 3 候选展示和演示截图。
- `server/`：后端推理服务，支持 mock scorer 和 SimOPA 真实 scorer。
- `docs/API.md`：Web 前端与后端之间的接口约定。
- `docs/HIGH_SCORE_ROUTE.md`：根据课程 PDF 整理的高分路线与交付证据清单。
- `docs/NEXT_ROUTE.md`：当前从候选排序到 RGB/mask 对比、分数校准、截图和报告的推进顺序。
- `docs/WORKFLOW.md`：小组协作、分支和合并规则。
- `docs/model_plan.md`：模型路线、参考源码、高分方案、训练和解释计划。
- `docs/PHASE0_STATUS.md`：当前阶段状态和下一步行动。
- `docs/TEST_CASES.md`：测试案例和工程验证记录。
- `OPAAndroidDemoSimp/`：课程提供的 Android 参考骨架，仅作为参考和素材来源，不作为本项目交付主线。
- `计划.md`：从阶段 0 到答辩准备的完整推进计划。

阶段 0 的核心原则是：先用 mock 数据打通 Web 到后端的链路，再把同一套接口切换到真实 OPA/SimOPA 模型推理。

课程 PDF 明确允许 Web 应用、手机 App 原型或电脑端应用软件。SmartPlace 选择 Web 应用作为交付形态，不再开发 Android 端。

## 目录结构

```text
SmartPlace/
|-- OPAAndroidDemoSimp/      # 课程 Android Demo 骨架
|-- server/                  # FastAPI 后端推理服务
|-- docs/                    # 接口、协作流程、模型计划、测试记录
|-- web/                     # Web 演示工作台
|-- assets/                  # 测试图片和共享素材
|-- report/                  # 报告、PPT、截图、录屏材料
|-- 计划.md                  # 项目推进计划
`-- README.md
```

## 阶段 0 快速运行

优先运行无额外依赖的 mock 后端：

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

运行真实 SimOPA scorer：

```powershell
$env:SMARTPLACE_SCORER='simopa'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

检查后端状态：

```bash
curl http://127.0.0.1:8000/api/health
```

运行后端单元检查：

```bash
python -m unittest server.test_recommender
python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py server/scorer.py
.\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py
```

Web 工作台访问：

```text
http://127.0.0.1:8000/
```

前端调用接口：

```text
POST http://127.0.0.1:8000/api/place/recommend
```

## 小组分工

- 成员 A：模型改造与模型实验。
- 成员 B：云端推理服务与候选推荐管线。
- 成员 C：Web 交互展示、演示视频和最终材料整合。

每个成员不仅负责实现，也负责自己模块对应的报告和 PPT 内容。
