# SmartPlace 接口约定

本文档定义阶段 0 中 Web 前端与后端推理服务之间的稳定接口。后续接入真实模型时，应尽量保持响应结构兼容，避免前端重复改动。

## 基础地址

本机开发：

```text
http://127.0.0.1:8000
```

Web 工作台：

```text
http://127.0.0.1:8000/
```

## 健康检查

```http
GET /api/health
```

响应示例：

```json
{
  "status": "ok",
  "service": "smartplace-inference",
  "model_version": "simopa-rgb-mask-v1",
  "scorer_mode": "simopa",
  "scorer_status": "ready"
}
```

## 推荐物体放置位置

```http
POST /api/place/recommend
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 是否必填 | 说明 |
|---|---|---:|---|
| `background` | file | 是 | 用户选择的背景图。 |
| `foreground` | file | 是 | 用户选择的前景物体图，优先使用带 alpha 通道的 PNG。 |
| `mask` | file | 否 | 前景 mask。若不提供，后端后续可从 alpha 通道或分割模型中生成。 |
| `candidate_count` | integer | 否 | 返回候选数量，默认 3。 |
| `foreground_scale` | float | 否 | 前景宽度相对背景宽度的大致比例，默认 0.25。 |
| `mode` | string | 否 | `auto`、`mock` 或 `simopa`，默认 `auto`。`auto` 使用服务启动时的 `SMARTPLACE_SCORER`。 |

阶段 0 响应示例：

```json
{
  "request_id": "simopa-20260606-000001",
  "model_version": "simopa-rgb-mask-v1",
  "coord_type": "normalized_xywh",
  "runtime_ms": 3709,
  "image_width": 640,
  "image_height": 512,
  "best_index": 0,
  "candidates": [
    {
      "rank": 1,
      "x": 0.42,
      "y": 0.3,
      "w": 0.4096,
      "h": 0.49,
      "score": 0.998,
      "tier": "recommended",
      "label": "推荐",
      "reason": "SimOPA: candidate scored 1.00 by RGB+mask placement assessment.",
      "preview_url": null,
      "heatmap_url": null
    }
  ]
}
```

## 坐标规则

- `coord_type` 固定为 `normalized_xywh`。
- `x` 和 `y` 表示前景框左上角坐标。
- `w` 和 `h` 表示前景框宽度和高度。
- 所有坐标均相对于背景图显示区域归一化，范围为 `0.0` 到 `1.0`。
- `image_width` 和 `image_height` 表示后端识别到的背景图原始尺寸。阶段 0 的 FastAPI mock 会从 PNG/JPEG/GIF 上传内容中解析真实尺寸；无法识别时退回 `1`。

Web 前端展示候选框时应优先使用归一化坐标，不要依赖服务端返回的固定像素尺寸。像素尺寸主要用于调试、日志和最终报告证据。

## 分数与标签

| 分数范围 | `tier` | 中文标签 |
|---|---|---|
| `score >= 0.75` | `recommended` | 推荐 |
| `0.45 <= score < 0.75` | `acceptable` | 可接受 |
| `score < 0.45` | `rejected` | 不推荐 |

## 真实模型接入计划

阶段 0 的 mock 响应必须与真实模型响应保持兼容。当前 FastAPI 服务已经支持：

- `SMARTPLACE_SCORER=mock`：使用 deterministic mock 分数，便于前端联调。
- `SMARTPLACE_SCORER=simopa`：调用 OPA/SimOPA 权重，对候选合成图和 mask 真实评分。
- 表单 `mode=mock` 或 `mode=simopa`：覆盖服务默认 scorer，便于测试。

真实模型接入后可继续补充：

- `preview_url`：云端生成的候选合成图。
- `heatmap_url`：Grad-CAM、遮挡实验或其他解释图。
- `model_version`：例如 `opa-rgb-v1` 或 `opa-rgb-mask-v1`。
- `runtime_ms`：云端实际推理耗时。

## 错误响应

当真实 scorer 缺少权重、Python 环境不可用或模型子进程失败时，服务返回：

```json
{
  "detail": "SimOPA scorer failed: ..."
}
```

HTTP 状态码为 `502`。Web 前端应展示错误状态，不要把失败请求当成有效推荐。

## 前端实现要求

当前主线前端是 `web/` 本地工作台。课程提供的 `OPAAndroidDemoSimp/` 仅作为参考，不纳入交付主线。前端接口层必须保持：

- 使用 `multipart/form-data` 上传背景图和前景图。
- 请求成功后解析 `candidates` 数组，而不是只读取单个分数。
- 按 `best_index` 默认展示最佳候选。
- 支持展示或记录 `model_version`、`runtime_ms` 和 `request_id`，便于报告证明真实调用链路。
