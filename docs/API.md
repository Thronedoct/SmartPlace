# SmartPlace 接口约定

本文档定义 Web 前端与 FastAPI 推理服务之间的当前稳定接口。后端已经支持 mock、SimOPA、SimOPA Lite 和 SimOPA Worker 多种 scorer 模式；后续重构前端或模型时应保持响应结构兼容，避免重复改动接口层。

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
| `mode` | string | 否 | `auto`、`mock`、`simopa`、`simopa-lite`、`simopa-worker` 或 `simopa-lite-worker`，默认 `auto`。`auto` 使用服务启动时的 `SMARTPLACE_SCORER`。 |

响应示例：

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
- `image_width` 和 `image_height` 表示后端识别到的背景图原始尺寸。FastAPI 服务会从 PNG/JPEG/GIF 上传内容中解析真实尺寸；无法识别时退回 `1`。

Web 前端展示候选框时应优先使用归一化坐标，不要依赖服务端返回的固定像素尺寸。像素尺寸主要用于调试、日志和最终报告证据。

## 分数与标签

| 分数范围 | `tier` | 中文标签 |
|---|---|---|
| `score >= 0.75` | `recommended` | 推荐 |
| `0.45 <= score < 0.75` | `acceptable` | 可接受 |
| `score < 0.45` | `rejected` | 不推荐 |

## Scorer 模式

mock、SimOPA 和 worker 模式共用同一响应结构。当前 FastAPI 服务支持：

- `SMARTPLACE_SCORER=mock`：使用 deterministic mock 分数，便于前端联调。
- `SMARTPLACE_SCORER=simopa`：调用 OPA/SimOPA 权重，对候选合成图和 mask 真实评分。
- `SMARTPLACE_SCORER=simopa-lite`：仍调用同一 SimOPA 权重，但只评估较小候选预算，作为速度优先的应用模式。
- `SMARTPLACE_SCORER=simopa-worker`：启动常驻 SimOPA JSONL worker，模型只加载一次，适合现场演示和批量评测。
- `SMARTPLACE_SCORER=simopa-lite-worker`：常驻 worker + 较小候选预算。
- 表单 `mode=mock`、`mode=simopa`、`mode=simopa-lite`、`mode=simopa-worker` 或 `mode=simopa-lite-worker`：覆盖服务默认 scorer，便于测试。

当前保留的可选展示字段：

- `preview_url`：后端生成的候选合成图。
- `heatmap_url`：Grad-CAM、遮挡实验或其他解释图。

## 错误响应

当真实 scorer 缺少权重、Python 环境不可用或模型子进程失败时，服务返回：

```json
{
  "detail": "SimOPA scorer failed: ..."
}
```

HTTP 状态码为 `502`。Web 前端应展示错误状态，不要把失败请求当成有效推荐。

## 内置演示案例

```http
GET /api/demo/cases
```

返回 Web 工作台可一键加载的代表案例。案例元数据来自 `report/tables/failure_cases.csv` 和 `report/tables/opa_18_case_summary.csv`；图片优先来自 `assets/demo_cases/` 中的小型打包案例，缺失时才回退到本地 OPA raw 数据集。

响应字段：

| 字段 | 说明 |
|---|---|
| `case_id` | 案例编号，例如 `opa_test_001`。 |
| `title` | 页面展示标题，例如“成功案例”“分数饱和边界”。 |
| `case_type` | 案例类型，用于报告和可信度提示。 |
| `dataset_label` | OPA 原始正负标签。 |
| `note` | 案例说明。 |
| `foreground_scale` | 推荐前景比例。 |
| `candidate_count` | 推荐候选数量。 |
| `recommended_mode` | 推荐 scorer 模式，当前为 `simopa`。 |
| `available` | 本地图片、前景和 mask 是否可用。 |
| `background_url`、`foreground_url`、`mask_url` | 可由 Web 拉取并转成 multipart 文件的图片资源。 |
| `heatmap_url`、`panel_url` | 可选解释热力图和案例图。 |

图片资源：

```http
GET /api/demo/cases/{case_id}/background
GET /api/demo/cases/{case_id}/foreground
GET /api/demo/cases/{case_id}/mask
GET /api/demo/cases/{case_id}/heatmap
GET /api/demo/cases/{case_id}/panel
```

当打包 demo asset、OPA raw 数据和截图都缺失时，对应资源返回 `404`，`available=false` 的案例按钮会在前端禁用。

## 前端实现要求

当前主线前端是 `web/` 本地工作台。课程提供的 `OPAAndroidDemoSimp/` 仅作为参考，不纳入交付主线。前端接口层必须保持：

- 使用 `multipart/form-data` 上传背景图和前景图。
- 请求成功后解析 `candidates` 数组，而不是只读取单个分数。
- 按 `best_index` 默认展示最佳候选。
- 支持展示或记录 `model_version`、`runtime_ms` 和 `request_id`，便于报告证明真实调用链路。
- 支持导出当前推荐结果 JSON/CSV，导出内容包括 Top 3、坐标、模型版本、运行耗时和可信度提示。
- 支持一键加载内置代表案例，确保课堂现场演示稳定。
