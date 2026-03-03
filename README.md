# 项目文档目录说明

本仓库采用「需求 / 技术文档 / 功能测试 / 接口测试」分离的目录结构，便于按迭代与类型管理文档。

## 目录结构

| 目录 | 说明 |
|------|------|
| **requirements/** | 需求文档。按迭代分子目录（如 `2026Q1_SP3/`） |
| **tech-docs/** | 开发技术文档（接口设计、架构、DB 变更等）。按迭代与 `shared/` 分目录 |
| **testcases/** | 功能测试用例。按迭代分目录，思维导图等放在对应迭代下的 `xmind/`，辅助文件放 `assets/` |
| **api-testcases/** | 接口用例与接口自动化。按迭代与 `shared/` 分目录 |
| **tools/** | 脚本工具（如 xmind 转 md） |
| **.cursor/** | Cursor 配置（rules、skills、commands），非业务文档 |

## 使用约定

- 新迭代：在 `requirements/`、`tech-docs/`、`testcases/`、`api-testcases/` 下各建同名迭代目录（如 `2026Q1_SP4/`）。
- 跨迭代复用：技术文档与接口用例可放在 `tech-docs/shared/`、`api-testcases/shared/`。
- 需求文档引用：编写时引用 `requirements/<迭代>/xxx.md`，便于追溯。

## 当前已整理内容

- **requirements/2026Q1_SP3/**：会籍权益分级、可用资源列表、entitlement 等需求文档已迁入。
- **testcases/2026Q1_SP3/**：迭代目录与 xmind 子目录已创建；根目录下的测试用例与 xlsx 若未被占用，可手动移至此处与 `testcases/assets/`。
- **tech-docs/**、**api-testcases/**：目录与占位 README 已创建，可按需新增文档与用例。
