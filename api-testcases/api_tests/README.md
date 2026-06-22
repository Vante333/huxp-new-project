# api-testcases/api_tests

长期维护的接口自动化框架目录，不再按迭代命名。后续新增需求优先扩展业务域、接口能力与回归分层，Jira / PAPI 编号仅作为 marker、Allure story、用例表追踪信息。

本目录是后续接口自动化的默认主线；`api-testcases/2026Q2_SP1` 仅作为历史金样例与迁移参考保留。除修复历史样例自身问题外，新需求、大改、公共断言和 Postman 生成器默认维护在本目录，避免同一接口能力出现两份真相源。

## 目录分层

| 目录 | 作用 |
|------|------|
| `framework/` | 公共配置、HTTP、Allure 报告、基础断言、CSV 数据加载 |
| `clients/` | 按接口资源封装：auth、memberships、entitlements、ePass orders |
| `services/` | 按业务能力封装：membership extensions、cross module entitlements、ePass orders |
| `scenarios/` | 主链路编排入口，主 E2E 用例只调用 `Run...MainE2EScenario` |
| `tests/contract/` | 契约、字段结构、Python 与 Postman 语义对齐 |
| `tests/features/` | 新需求或业务能力验证 |
| `tests/regression/` | 历史缺陷与关键业务回归 |
| `tests/smoke/` | 主流程冒烟入口，后续可沉淀稳定最小集 |
| `testdata/` | 按 `DP_PROFILE` 分环境的业务数据集 |
| `postman/` | Postman Collection v2.1 生成器与导出 JSON |
| `docs/` | 框架演进、命名和协作说明 |

兼容说明：`papi2548_helpers.py`、`papi2515_helpers.py`、`papi2424_helpers.py` 仍保留为重导出壳，旧调用可继续工作；新代码优先从 `clients/`、`services/`、`scenarios/` 引用。

## 命名与筛选

稳定分类 marker：

| marker | 说明 |
|--------|------|
| `contract` | 契约/字段/结构稳定性 |
| `smoke` | 主流程冒烟 |
| `regression` | 历史缺陷与关键业务回归 |
| `feature` | 新需求或业务能力验证 |
| `needs_write` | 会写入或改写沙箱数据 |

业务能力 marker：

| marker | 说明 |
|--------|------|
| `papi2548` | 会籍 extensions |
| `papi2515` | crossModuleEntitlements |
| `papi2424` | ePasses details / MS 订单提示 |
| `local_offers` | local offers options |
| `local_offer_epass` | Local Offer ePass 订单（创建/预约/查询） |

原有细粒度 marker 继续可用，例如 `needs_cross_module_write`、`needs_extensions_write`、`needs_p2424_usage_order_id`、`p2515_probe_membership`。

## 环境与数据

配置加载仍沿用成熟模式：

- `DP_PROFILE`：选择环境凭据，加载仓库根 `.env` 与 `env/.env.<profile>`。
- `DP_TEST_DATASET`：选择 `testdata/<profile>/*.csv` 中的 `datasetKey` 行。
- `DP_CREDENTIAL_ALIAS`：同一 profile 内选择多套三件套，例如 `EPASS` 映射到标准 `DP_PROGRAM_ID` / `DP_CLIENT_ID` / `DP_CLIENT_SECRET`。

语义化 CSV 文件：

| 文件 | 说明 |
|------|------|
| `membership_register.csv` | 会籍注册基础模板 |
| `cross_module_entitlements.csv` | crossModuleEntitlements 造数与断言数据 |
| `epass_orders_ms_hint.csv` | ePass orders MS 提示回归数据 |

加载器会优先读取语义化文件，并兼容回退旧文件名 `p2515_dataset.csv`、`p2424_dataset.csv`。

## 运行示例

从仓库根执行：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
$env:DP_PROFILE = "canary"
pytest api-testcases/api_tests/tests -m "contract or smoke" -v --alluredir=reports/api-tests-allure-results
```

按提测、回归、发布阶段筛选：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "feature or contract" -v --alluredir=reports/api-tests-allure-results
pytest api-testcases/api_tests/tests -m "smoke or regression or contract" -v --alluredir=reports/api-tests-allure-results
pytest api-testcases/api_tests/tests -m "not manual" -v --alluredir=reports/api-tests-allure-results
```

只跑不写沙箱数据的日常回归：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "not manual and not needs_write" -v --alluredir=reports/api-tests-allure-results
```

按业务能力筛选：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "papi2548 and feature" -v --alluredir=reports/papi2548-allure-results
```

Local Offer ePass（写沙箱，建议 ``DP_PROFILE=canary``）：

| Apifox / Postman | 环境变量（推荐） |
|------------------|------------------|
| `baseUrl` | `DP_BASE_URL` |
| `programId` | `DP_EPASS_PROGRAM_ID` |
| `clientId` | `DP_EPASS_CLIENT_ID` |
| `clientSecret` | `DP_EPASS_CLIENT_SECRET` |
| `resourceId` | `DP_LO_EPASS_RESOURCE_ID`（默认网点） |
| `optionId` | `DP_LO_EPASS_OPTION_ID` |

按券型覆盖：`DP_LO_EPASS_URL_*`、`DP_LO_EPASS_REDEMPTION_CODE_*`、`DP_LO_EPASS_CARD_SECRET_*`。  
短别名（便于 Apifox 导入）：`PROGRAM_ID`、`CLIENT_ID`、`CLIENT_SECRET`、`RESOURCE_ID`、`OPTION_ID`。  
模板文件：`env/.env.local-offer.example`；对照说明：`config/local_offer_epass_env.py`。

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
$env:DP_PROFILE = "canary"
# 将 env/.env.local-offer.example 中的键合并进 env/.env.canary 后执行：
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py -m "local_offer_epass" -v
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py api-testcases/api_tests/tests/features/local_offer_epass -m "local_offer_epass and not manual" -v --alluredir=reports/local-offer-epass-allure-results
allure serve reports/local-offer-epass-allure-results
```

写类接口建议显式筛选：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "not manual and not needs_write" -v --alluredir=reports/api-tests-readonly-allure-results
pytest api-testcases/api_tests/tests -m "needs_write" -v --alluredir=reports/api-tests-write-allure-results
```

## 新增接口能力约定

1. 优先新增或扩展 `clients/<resource>_client.py`，只放 HTTP 资源级封装。
2. 业务语义、payload 构造、断言与跳过条件放在 `services/<capability>_service.py` 或能力实现模块。
3. 产品主链路放在 `scenarios/<capability>_scenarios.py`，暴露单一 `Run...MainE2EScenario`。
4. 用例按价值放入 `tests/contract`、`tests/features`、`tests/regression`、`tests/smoke`。
5. 新增可复用 `Assert*` 时继续走 Allure 断言附件约定，保证报告可读。
6. 若需要 Postman / Apifox 导出，同步维护 `postman/Generate*.py` 与导出的 collection JSON。
7. 新增需求完成后，同步更新 [`../docs/automation-coverage-index.md`](../docs/automation-coverage-index.md) 与对应 `testcases/` 映射表，保证需求、用例、pytest 节点和报告入口可追溯。
