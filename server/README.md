# SmartPlace Mock 后端

本目录是阶段 0 的云端推理 mock 服务。

当前服务返回 mock Top 3 放置推荐结果，响应结构与后续真实 OPA/libcom 模型计划保持一致。

推荐逻辑位于 `recommender.py`，FastAPI 入口和标准库入口共用同一套响应构造函数。后续接入真实模型时，优先替换 scorer/候选排序逻辑，不要破坏 `../docs/API.md` 中已经约定的响应字段。

## 无额外依赖运行

用于阶段 0 的 Android 连通性 Demo：

```bash
python mock_stdlib.py --host 0.0.0.0 --port 8000
```

## FastAPI 版本运行

```bash
cd server
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

FastAPI 版本会读取上传图片内容，并尽量从 PNG/JPEG/GIF 背景图中解析真实宽高，写入响应的 `image_width` 和 `image_height`。

## 接口

- `GET /api/health`
- `POST /api/place/recommend`

请求和响应字段详见 `../docs/API.md`。

## Android 访问地址

- 模拟器：`http://10.0.2.2:8000`
- 真机：`http://<电脑局域网IP>:8000`

## 本地检查

在项目根目录运行：

```bash
python -m unittest server.test_recommender
python -m py_compile server/app.py server/mock_stdlib.py server/recommender.py
```
