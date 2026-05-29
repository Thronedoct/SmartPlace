# 阶段 0 状态

## 已完成

- 已检查课程 Android Demo，并保留为 `OPAAndroidDemoSimp/`。
- 已新增根目录项目说明。
- 已新增接口约定文档。
- 已新增协作流程文档。
- 已新增测试案例模板。
- 已新增模型计划文档。
- 已在 `main` 分支初始化 Git 仓库。
- 已新增 FastAPI mock 服务。
- 已新增无额外依赖的标准库 mock 服务，并完成本地验证。

## 当前决定

先把课程 Android Demo 作为初始 App 骨架，但不把整个项目强绑定在这份 Demo 上。后端接口保持独立，这样后续即使重写 Android 页面，也不影响模型服务约定。

## 下一步

1. 成员 B 运行 mock 后端。
2. 成员 C 在 Android 端接入 `/api/place/recommend`。
3. 成员 A 跑通第一版 OPA/libcom 参考示例，并记录输入输出。
4. 小组确认 `docs/API.md` 中的响应字段是否足够支撑第一版 Android 联调。
