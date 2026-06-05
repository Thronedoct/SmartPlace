# SmartPlace

SmartPlace 是本课程方向 A 的项目：智能物体放置与合成图质量评价。

项目目标是做一个 Android 物体放置助手。用户在 App 中选择背景图和前景物体后，系统把图片发送给云端推理服务，由后端生成候选位置、调用模型评分，并把推荐位置、合理性分数和可视化证据返回给 App 展示。

## 当前阶段

目前处于阶段 0 到阶段 1 的衔接：协作环境和 mock Demo 已搭建，下一步是 Android 联调与真实 OPA/libcom 评分模型验证。

- `OPAAndroidDemoSimp/`：课程提供的 Android 前端参考骨架。
- `server/`：云端推理服务，阶段 0 先返回 mock 推荐结果。
- `docs/API.md`：Android 与后端之间的接口约定。
- `docs/WORKFLOW.md`：小组协作、分支和合并规则。
- `docs/model_plan.md`：模型选择、模型改造和验证计划。
- `docs/SOURCE_REVIEW.md`：课程 PDF 中参考 GitHub 源码的审阅记录和落地路线。
- `计划.md`：从阶段 0 到答辩准备的完整推进计划。

阶段 0 的核心原则是：先用 mock 数据打通 Android 到后端的链路，再逐步替换为真实 OPA/libcom 模型推理。

Android 端可以继续使用课程 Demo，也可以重新搭建；项目边界以 `docs/API.md` 为准。

## 目录结构

```text
SmartPlace/
|-- OPAAndroidDemoSimp/      # 课程 Android Demo 骨架
|-- server/                  # FastAPI / mock 云端推理服务
|-- docs/                    # 接口、协作流程、模型计划、测试记录
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
cd server
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

检查后端状态：

```bash
curl http://127.0.0.1:8000/api/health
```

运行后端单元检查：

```bash
python -m unittest server.test_recommender
python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py
```

Android 端后续调用：

```text
POST http://<server-ip>:8000/api/place/recommend
```

模拟器使用 `http://10.0.2.2:8000`。真机使用电脑的局域网 IP。

## 小组分工

- 成员 A：模型改造与模型实验。
- 成员 B：云端推理服务与候选推荐管线。
- 成员 C：Android App、交互展示、演示视频和最终材料整合。

每个成员不仅负责实现，也负责自己模块对应的报告和 PPT 内容。
