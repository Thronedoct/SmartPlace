# SmartPlace 后端

本目录是 SmartPlace 的 FastAPI 本地推理服务。推荐从仓库根目录启动：

```powershell
.\start_demo.ps1
```

默认模式是 `simopa-worker`，用于最终演示。停止服务：

```powershell
.\stop_demo.ps1
```

## 环境

App 环境安装 FastAPI 依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

真实模型推理使用单独的 model 环境。先按机器情况安装 PyTorch/torchvision，再安装：

```powershell
conda run -n <model-env> python -m pip install -r requirements-model.txt
```

Web 内置案例图片位于 `assets/demo_cases/`，不依赖完整 OPA raw 数据集。

## Scorer 模式

| 模式 | 用途 |
|---|---|
| `mock` | 无模型联调和快速页面验证。 |
| `simopa` | 每次请求通过子进程调用真实 SimOPA。 |
| `simopa-lite` | 候选预算更小的速度优先模式。 |
| `simopa-worker` | 常驻模型 worker，最终演示推荐模式。 |
| `simopa-lite-worker` | worker + 较小候选预算。 |

示例：

```powershell
.\start_demo.ps1 -Scorer mock
.\start_demo.ps1 -Scorer simopa-worker
.\start_demo.ps1 -ModelPython "<model-python>"
```

## 接口

- `GET /api/health`
- `GET /api/demo/cases`
- `GET /api/demo/cases/{case_id}/{asset}`
- `POST /api/place/recommend`

字段约定见 [docs/API.md](../docs/API.md)。

## 代码边界

- [app.py](app.py)：FastAPI 路由、静态页面、demo case 资产。
- [recommender.py](recommender.py)：候选生成、排序和响应封装。
- [scorer.py](scorer.py)：mock / SimOPA / worker scorer 边界。
- [test_recommender.py](test_recommender.py)：后端核心单测。

## 本地检查

在仓库根目录运行：

```powershell
.\scripts\verify_core.ps1
```
