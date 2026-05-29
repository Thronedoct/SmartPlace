# SmartPlace 接口约定

本文档定义阶段 0 中 Android App 与云端推理服务之间的稳定接口。后续接入真实模型时，应尽量保持响应结构兼容，避免 Android 端重复改动。

## 基础地址

本机开发：

```text
http://127.0.0.1:8000
```

Android 模拟器：

```text
http://10.0.2.2:8000
```

Android 真机：

```text
http://<电脑局域网IP>:8000
```

## 健康检查

```http
GET /api/health
```

响应示例：

```json
{
  "status": "ok",
  "service": "smartplace-mock",
  "model_version": "mock-v0"
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
| `mode` | string | 否 | `auto` 或 `manual`，默认 `auto`。 |

阶段 0 响应示例：

```json
{
  "request_id": "mock-20260529-000001",
  "model_version": "mock-v0",
  "coord_type": "normalized_xywh",
  "runtime_ms": 42,
  "image_width": 1,
  "image_height": 1,
  "best_index": 0,
  "candidates": [
    {
      "rank": 1,
      "x": 0.38,
      "y": 0.58,
      "w": 0.22,
      "h": 0.22,
      "score": 0.86,
      "tier": "recommended",
      "label": "推荐",
      "reason": "候选位置位于较稳定的支撑区域内。",
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

## 分数与标签

| 分数范围 | `tier` | 中文标签 |
|---|---|---|
| `score >= 0.75` | `recommended` | 推荐 |
| `0.45 <= score < 0.75` | `acceptable` | 可接受 |
| `score < 0.45` | `rejected` | 不推荐 |

## 真实模型接入计划

阶段 0 的 mock 响应必须与后续真实模型响应保持兼容。真实模型接入后可补充：

- `preview_url`：云端生成的候选合成图。
- `heatmap_url`：Grad-CAM、遮挡实验或其他解释图。
- `model_version`：例如 `opa-rgb-v1` 或 `opa-rgb-mask-v1`。
- `runtime_ms`：云端实际推理耗时。
