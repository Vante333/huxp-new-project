# 接口自动化套件：附录（模板与命令）

## 建议目录结构（新需求/迭代）

将 `{TICKET}` 换为如 `PAPI-2548`，`{SPRINT}` 换为如 `2026Q2_SP1`：

```
api-testcases/{SPRINT}/
  README.md
  pytest.ini
  conftest.py
  {ticket}_helpers.py          # 或小写前缀，与套件内 import 一致
  test_{ticket}_*.py
  postman/
    README.md
    GeneratePostmanCollection{TICKET}.py
    {TICKET}-*.postman_collection.json
    {TICKET}-*.postman_environment.json   # 可选
testcases/{SPRINT}/
  {TICKET}-自动化用例与pytest对应表.md    # 可选但推荐
```

## 环境：分层加载（与金样例一致）

1. 仓库根目录 `.env`：不覆盖已在进程环境中的键。
2. 若设置 `DP_PROFILE`（仅 `a-zA-Z0-9_-`），加载 `env/.env.<profile>` 并**覆盖**同名键。

PowerShell 示例（在仓库根执行）：

```powershell
$env:DP_PROFILE = "sandbox"
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1 -m "not manual" --alluredir=reports/papi2548-allure-results
```

将路径中的 `2026Q2_SP1`、`papi2548` 换成当前套件对应目录与报告名。

## pytest + Allure

在本套件目录内：

```powershell
cd api-testcases\2026Q2_SP1
pytest . -v --alluredir=..\..\reports\papi2548-allure-results
```

安装 Allure CLI 后查看报告：

```powershell
allure serve ..\..\reports\papi2548-allure-results
```

`pytest.ini` 中应包含 `addopts = --clean-alluredir`，以便每次带 `--alluredir` 运行时先清空目录，避免多次运行合并导致用例数翻倍。

## Postman 生成器（最小结构提示）

- **Schema**：`https://schema.getpostman.com/json/collection/v2.1.0/collection.json`
- **事件**：请求的 `event` 中 `listen: "test"`，`script.exec` 为 JavaScript 字符串数组（与 Python helpers 行为对齐）。
- **变量**：集合/环境中定义 `baseUrl`、`programId`、`clientId`、`clientSecret` 等，与 README 中 `DP_*` 对照表一致。
- 生成后：在 Postman 或 Apifox 中 **Import** 写出的 JSON；团队流程见金样例 [`postman/README.md`](../../../api-testcases/2026Q2_SP1/postman/README.md)。

## 依赖

金样例依赖见仓库 [`tools/requirements.txt`](../../../tools/requirements.txt)（在套件 README 中引用 `pip install -r ...`）。
