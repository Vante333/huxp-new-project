# 接口自动化覆盖索引

本索引用于维护「需求 / 用例 / pytest / Postman」的自动化覆盖关系。长期主线为 [`../api_tests/`](../api_tests/)；历史目录 [`../2026Q2_SP1/`](../2026Q2_SP1/) 仅作为迁移参考。

## 维护规则

- 新需求自动化完成后，必须新增或更新本表。
- `pytest 节点` 使用可直接复制执行的节点或目录路径。
- `分层` 使用 `contract`、`smoke`、`regression`、`feature`、`needs_write` 等 marker 语义。
- Postman 仅作为联调和共享入口，行为语义以 pytest + helpers/services 为准。

## 覆盖总表

| PAPI / 能力 | 需求 | 功能用例 | pytest 节点 | 分层 / marker | 主链路入口 | Postman |
|---|---|---|---|---|---|---|
| PAPI-2548 会籍 extensions | [`requirements/2026Q2_SP1/PAPI-2548.md`](../../requirements/2026Q2_SP1/PAPI-2548.md) | [`testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md)、[`PAPI-2548-自动化用例与pytest对应表.md`](../../testcases/2026Q2_SP1/PAPI-2548-自动化用例与pytest对应表.md) | [`api_tests/tests/features/test_membership_extensions.py`](../api_tests/tests/features/test_membership_extensions.py)、[`api_tests/tests/contract/test_membership_extensions_normalize_parity.py`](../api_tests/tests/contract/test_membership_extensions_normalize_parity.py) | `feature`、`contract`、`papi2548`，写链路经 `needs_extensions_write` 自动补 `needs_write` | `RunPapi2548MainE2EScenario` | [`PAPI-2548-membership-extensions.postman_collection.json`](../api_tests/postman/PAPI-2548-membership-extensions.postman_collection.json) |
| PAPI-2515 crossModuleEntitlements | [`requirements/2026Q2_SP1/PAPI-2515.md`](../../requirements/2026Q2_SP1/PAPI-2515.md) | [`testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md) | [`api_tests/tests/features/test_cross_module_entitlements.py`](../api_tests/tests/features/test_cross_module_entitlements.py) | `feature`、`papi2515`、`needs_cross_module_data`、`needs_cross_module_write`、`needs_write` | `RunP2515MainE2EScenario` | [`PAPI-2515-cross-module-entitlements.postman_collection.json`](../api_tests/postman/PAPI-2515-cross-module-entitlements.postman_collection.json) |
| PAPI-2424 ePasses details MS 订单提示 | [`requirements/2026Q2_SP1/PAPI-2424.md`](../../requirements/2026Q2_SP1/PAPI-2424.md) | [`testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md) | [`api_tests/tests/regression/test_epass_orders_ms_hint.py`](../api_tests/tests/regression/test_epass_orders_ms_hint.py) | `regression`、`papi2424`、`needs_p2424_usage_order_id` | `PostOrdersEPassesDetails` 组合回归 | [`PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json`](../api_tests/postman/PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json) |
| Local Offers options | MCP OpenAPI：`project-0-interface_cursor-Q2 local offer` / `/v2/resources/localOffers/{resourceId}/options` | [`testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md`](../../testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md) | [`api_tests/tests/features/test_local_offers_options.py`](../api_tests/tests/features/test_local_offers_options.py)、[`api_tests/tests/smoke/test_local_offers_options_smoke.py`](../api_tests/tests/smoke/test_local_offers_options_smoke.py)、[`api_tests/tests/contract/test_local_offers_options_contract.py`](../api_tests/tests/contract/test_local_offers_options_contract.py) | `feature`、`smoke`、`contract`、`local_offers` | `GET /v2/resources/localOffers/{resourceId}/options` 只读查询链路 | 待补充 |

## 标准执行入口

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "feature or contract" -v --alluredir=reports/api-tests-allure-results
pytest api-testcases/api_tests/tests -m "smoke or regression or contract" -v --alluredir=reports/api-tests-allure-results
pytest api-testcases/api_tests/tests -m "not manual and not needs_write" -v --alluredir=reports/api-tests-readonly-allure-results
```

## 待补齐项

- 为 PAPI-2515、PAPI-2424 补独立的「自动化用例与 pytest 对应表」，对齐 PAPI-2548 现有模式。
- 为 Local Offers options 补正式需求文档链接和 Postman 导出。
- 后续新增 PAPI 时，同步补 `requirements`、`testcases`、pytest 节点、marker 与 Postman 链接。
