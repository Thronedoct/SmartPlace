# SmartPlace 后端

本目录是 SmartPlace 的本地/局域网推理服务。

当前 FastAPI 服务支持 mock、SimOPA、SimOPA Lite 和 SimOPA Worker：mock 用于 Web 联调，SimOPA 用于真实 OPA/SimOPA 候选评分排序，SimOPA Lite 使用较小候选预算，SimOPA Worker 使用常驻模型进程减少重复加载开销。

推荐逻辑位于 `recommender.py`，scorer 边界位于 `scorer.py`。响应字段必须保持兼容 `../docs/API.md`。

## 无额外依赖 mock 运行

用于 Web/后端连通性调试，不加载真实模型：

```bash
python mock_stdlib.py --host 0.0.0.0 --port 8000
```

## FastAPI 版本运行

```bash
python -m pip install -r server/requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

运行真实 SimOPA scorer：

```powershell
$env:SMARTPLACE_SCORER='simopa'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

运行 SimOPA Lite 候选预算模式：

```powershell
$env:SMARTPLACE_SCORER='simopa-lite'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

运行常驻 SimOPA Worker 模式：

```powershell
$env:SMARTPLACE_SCORER='simopa-worker'
$env:SMARTPLACE_MODEL_PYTHON='D:\DevTools\Anaconda\envs\study\python.exe'
$env:SMARTPLACE_SIMOPA_DEVICE='auto'
.\.venv\Scripts\python.exe -m uvicorn server.app:app --host 0.0.0.0 --port 8000
```

FastAPI 版本会读取上传图片内容，并尽量从 PNG/JPEG/GIF 背景图中解析真实宽高，写入响应的 `image_width` 和 `image_height`。

## 接口

- `GET /api/health`
- `POST /api/place/recommend`

请求和响应字段详见 `../docs/API.md`。

## Web 访问地址

- Web 工作台：`http://127.0.0.1:8000/`
- API 健康检查：`http://127.0.0.1:8000/api/health`

## 本地检查

在项目根目录运行：

```bash
python -m unittest server.test_recommender
python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py server/scorer.py
.\.venv\Scripts\python.exe experiments\opa_baseline\run_api_simopa_smoke.py
```
