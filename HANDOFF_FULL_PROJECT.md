# SmartPlace 完整项目交付说明书

本文说明“项目交付包”里有什么、没有什么，以及队友收到后应该怎么运行和继续做材料。

## 这个包是什么

项目交付包面向需要自己打开源码、运行 Web 演示、录屏或继续改材料的队友。它不是只包含报告素材的小包，而是把当前本机项目中可复用的代码、模型、外部参考源码和证据放在一起。

默认包**不包含 OPA raw 数据集**，因为 `new_OPA/` 约 4.6GB 且包含十几万张小图，复制和压缩会很慢。队友只写报告/PPT/录屏时，默认包已经够用；如果确实要重跑 OPA 内置案例或大规模实验，再单独复制数据集。

默认导出位置：

```text
report/exports/smartplace_project_no_dataset.zip
```

生成命令：

```powershell
.\scripts\export_full_project_package.ps1
```

如果确实要把 raw 数据也放进包里，再显式运行：

```powershell
.\scripts\export_full_project_package.ps1 -IncludeRawDataset -PackageName smartplace_project_with_dataset
```

这个命令会很慢，也会生成一个 5GB 以上的大包。

打包前只看预估文件数和大小，不真正写 zip：

```powershell
.\scripts\export_full_project_package.ps1 -ListOnly
```

## 包里包含什么

| 内容 | 路径 | 用途 |
|---|---|---|
| 项目源码 | `web/`、`server/`、`experiments/`、`scripts/` | 运行 Web、后端、实验和验证脚本。 |
| 根目录启动脚本 | `start_demo.ps1`、`stop_demo.ps1` | 一键启动/停止演示服务。 |
| 项目文档 | `README.md`、`docs/`、`server/README.md`、`experiments/README.md` | 查看项目定位、接口、模型路线和验证记录。 |
| 交付证据 | `report/` | 报告/PPT/录屏所需的表格、日志、截图和交接索引。 |
| 数据 split 和说明 | `assets/datasets/opa/splits/`、`assets/datasets/opa/notes.md` | 18/50/100 组案例和数据审计记录。 |
| SimOPA 权重 | `models/opa/`、`models/libcom/pretrained_models/` | 真实 OPA/SimOPA scorer 运行所需权重。 |
| LightOPA 权重 | `models/lightopa/` | tiny/residual 轻量 baseline 的训练结果。 |
| 外部参考源码 | `external/` | OPA/libcom/TopNet 参考源码和 SimOPA 调用依赖。 |
| 本地模型依赖缓存 | `.model-packages/` | SimOPA 脚本使用的轻量 Python 包缓存。 |
| 课程 PDF | `课程项目.pdf` | 课程要求参考。 |

## 包里没有什么

这些内容故意不打包：

| 不包含 | 原因 |
|---|---|
| `.git/` | 队友只需要交付包；完整 Git 历史在 GitHub。 |
| `.venv/`、`venv/` | 虚拟环境路径和机器绑定，不便携。 |
| `__pycache__/`、`.pytest_cache/` | 缓存文件，没必要交付。 |
| `report/exports/` | 防止把旧包套进新包；脚本会在进入该目录前跳过。 |
| `assets/datasets/opa/raw/` | 默认不包含，避免 4.6GB 小文件数据集导致打包很慢。 |
| `assets/datasets/opa/downloads/` | 下载压缩包会和已解压 raw 数据重复。 |
| `server/uploads/`、`server/generated/` | 本地临时运行产物。 |
| IDE/系统临时文件 | 与课程交付无关。 |

## 队友收到后怎么做

1. 解压到一个短路径，例如：

```text
D:\SmartPlace\
```

2. 先看两个入口：

```text
README.md
report/README.md
```

`README.md` 负责运行项目；`report/README.md` 负责报告、PPT 和录屏怎么取证。

3. 快速确认 Web 可以打开：

```powershell
.\start_demo.ps1 -Scorer mock
```

打开：

```text
http://127.0.0.1:8000/
```

结束后：

```powershell
.\stop_demo.ps1
```

4. 跑最终真实模型演示：

```powershell
.\start_demo.ps1
```

默认 scorer 是 `simopa-worker`。如果没有 OPA raw 数据集，Web 仍可启动，真实模型也可对用户手动上传的图片评分；但内置 OPA demo case 会因为缺少图片而不可用。若要使用内置案例，请把数据集复制到：

```text
assets/datasets/opa/raw/new_OPA/
```

如果脚本找不到 `study` conda 环境里的 Python，先查询：

```powershell
conda run -n study python -c "import sys; print(sys.executable)"
```

再显式传入：

```powershell
.\start_demo.ps1 -ModelPython "<path-to-study-conda-env-python.exe>"
```

5. 录屏流程按 `report/README.md` 走。录屏文件放到：

```text
report/videos/
```

6. 录屏后检查材料是否齐：

```powershell
.\scripts\verify_handoff_assets.ps1 -RequireVideos
```

## 队友要干什么

材料侧主要负责：

```text
最终报告 PDF
PPT
演示录屏
AI 辅助说明
成员分工说明
```

工程侧证据已经放在：

```text
report/tables/
report/logs/
report/screenshots/
report/README.md
```

## 常见问题

### 真实模型启动失败

先用 mock 确认 Web 和后端没问题：

```powershell
.\start_demo.ps1 -Scorer mock
```

如果 mock 正常但 `simopa-worker` 失败，重点检查：

```text
models/opa/OPA_checkpoints/checkpoints/simopa.pth
external/Object-Placement-Assessment-Dataset-OPA/
.model-packages/
```

以及 `study` 环境是否有 PyTorch、torchvision、Pillow 等依赖。

### 内置案例不可用

默认交付包不含 OPA raw 数据，所以内置案例按钮可能不可用。这不是代码坏了。要恢复内置案例，把数据集单独放回：

```text
assets/datasets/opa/raw/new_OPA/
```

如果只是写报告/PPT，直接使用 `report/screenshots/` 和 `report/tables/` 即可。

### 要不要重新跑全部实验

不需要。报告和 PPT 优先使用现有表格、日志和截图。只在修改实验结论时重新跑 GPU-heavy 脚本。

交付前轻量验证：

```powershell
.\scripts\verify_core.ps1
```

## GitHub 说明

完整源码仍在 GitHub：

```text
https://github.com/Thronedoct/SmartPlace
```

完整项目包用于队友本地运行和材料整理；GitHub 用于查看提交历史和代码版本。
