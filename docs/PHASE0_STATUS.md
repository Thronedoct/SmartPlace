# 阶段 0 状态

## 已完成

- 已从 `课程项目.pdf` 提取方向 A 相关 GitHub 仓库，并新增 `docs/SOURCE_REVIEW.md`。
- 已检查课程 Android Demo，并保留为 `OPAAndroidDemoSimp/`。
- 已新增根目录项目说明。
- 已新增接口约定文档。
- 已新增协作流程文档。
- 已新增测试案例模板。
- 已新增模型计划文档。
- 已在 `main` 分支初始化 Git 仓库。
- 已新增 FastAPI mock 服务。
- 已新增无额外依赖的标准库 mock 服务，并完成本地验证。
- 已将 mock 推荐逻辑抽到 `server/recommender.py`，便于后续替换真实 OPA/libcom scorer。
- FastAPI mock 已开始根据上传背景图解析 PNG/JPEG/GIF 尺寸，并在响应中返回 `image_width`、`image_height`。

## 当前决定

先把课程 Android Demo 作为参考 App 骨架，但不把整个项目强绑定在这份 Demo 上。成员 C 可以重写 Android 端；无论是否重写，前端必须遵守 `docs/API.md`，并完成 Top 3 推荐展示。

模型路线选择为：先用 OPA/libcom 评分模型跑通真实分数，再用规则候选生成排序；TopNet 或 FOPA 热力图作为后续进阶路线。

## 下一步

1. 成员 A 跑通 `libcom.OPAScoreModel` 或 OPA `simopa.py`，记录输入输出、权重路径和日志。
2. 成员 B 将后端 scorer 接口整理成 `score_composite(composite, mask) -> score`，保留 mock/真实模型开关。
3. 成员 C 决定继续使用 Demo 还是重建 Android 项目，并优先接入 `/api/place/recommend`。
4. 小组用一张新背景图和一张新前景图完成 Android -> 后端 mock 的端到端演示。
5. 每次推进后同步更新 `docs/API.md`、`docs/TEST_CASES.md` 和阶段状态文档。
