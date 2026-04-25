# 功能测试用例目录

按迭代组织，每个迭代一个子目录。

## 当前结构

- **2026Q1_SP3/**：本迭代功能测试用例与 xmind 源文件（`xmind/`）
- **2026Q2_SP2/**：含 Aero Blue 本地需求（`requirements/Aero Blue/`）对应 Markdown 用例，如 `PAPI-2636-*`、`PAPI-2657-*`、`PAPI-2644-*`、`PAPI-2204-*`、`PAPI-2576-*` 等
- **assets/**：辅助文件（如 Excel 矩阵表、配置表等）

## 迁移说明

若你看到本目录下还有以下文件：

- `2026Q1_SP3-测试用例.md`
- `会籍权益分级需求文档测试用例.md`
- `会籍权益分级-场景配置与权益总览.xlsx`
- `my_xmind/` 目录

请关闭相关文件后，将上述 **.md** 与 **.xmind** 移至 `testcases/2026Q1_SP3/`（xmind 文件可放入 `testcases/2026Q1_SP3/xmind/`），将 **.xlsx** 移至 `testcases/assets/`，以符合推荐目录结构。
