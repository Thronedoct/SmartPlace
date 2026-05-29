# SmartPlace Mock 后端

本目录是阶段 0 的云端推理 mock 服务。

当前服务返回固定 Top 3 放置推荐结果，响应结构与后续真实 OPA/libcom 模型计划保持一致。

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

## 接口

- `GET /api/health`
- `POST /api/place/recommend`

请求和响应字段详见 `../docs/API.md`。

## Android 访问地址

- 模拟器：`http://10.0.2.2:8000`
- 真机：`http://<电脑局域网IP>:8000`
