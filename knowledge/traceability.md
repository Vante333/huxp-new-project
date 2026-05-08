# 业务接口追溯表

本表按业务能力维护需求、用例、自动化与报告入口，服务于跨迭代影响分析和历史回归选择。需求原文仍以 `requirements/` 为准，自动化主线为 `api-testcases/api_tests/`。

## 追溯矩阵

| 业务能力 | 需求来源 | 功能用例 | 自动化入口 | 回归分层 | 维护说明 |
|---|---|---|---|---|---|
| 会籍 extensions | [`requirements/2026Q2_SP1/PAPI-2548.md`](../requirements/2026Q2_SP1/PAPI-2548.md) | [`testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md) | [`api-testcases/api_tests/tests/features/test_membership_extensions.py`](../api-testcases/api_tests/tests/features/test_membership_extensions.py)、[`api-testcases/api_tests/tests/contract/test_membership_extensions_normalize_parity.py`](../api-testcases/api_tests/tests/contract/test_membership_extensions_normalize_parity.py) | `feature`、`contract`、`papi2548` | 新增字段或校验规则时，优先扩展 `services/papi2548_service.py` 与 PAPI-2548 对应表。 |
| crossModuleEntitlements | [`requirements/2026Q2_SP1/PAPI-2515.md`](../requirements/2026Q2_SP1/PAPI-2515.md) | [`testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md) | [`api-testcases/api_tests/tests/features/test_cross_module_entitlements.py`](../api-testcases/api_tests/tests/features/test_cross_module_entitlements.py) | `feature`、`papi2515`、`needs_cross_module_data`、`needs_write` | 主链路通过 `RunP2515MainE2EScenario` 维护；写链路默认视为沙箱改写用例。 |
| ePasses details MS 订单提示 | [`requirements/2026Q2_SP1/PAPI-2424.md`](../requirements/2026Q2_SP1/PAPI-2424.md) | [`testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md) | [`api-testcases/api_tests/tests/regression/test_epass_orders_ms_hint.py`](../api-testcases/api_tests/tests/regression/test_epass_orders_ms_hint.py) | `regression`、`papi2424` | 作为历史兼容回归保留，避免 ePasses details 对 MS 前缀提示退化。 |
| Local Offers options | MCP OpenAPI：`project-0-interface_cursor-Q2 local offer` / `/v2/resources/localOffers/{resourceId}/options` | [`testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md`](../testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md) | [`api-testcases/api_tests/tests/features/test_local_offers_options.py`](../api-testcases/api_tests/tests/features/test_local_offers_options.py)、[`api-testcases/api_tests/tests/smoke/test_local_offers_options_smoke.py`](../api-testcases/api_tests/tests/smoke/test_local_offers_options_smoke.py)、[`api-testcases/api_tests/tests/contract/test_local_offers_options_contract.py`](../api-testcases/api_tests/tests/contract/test_local_offers_options_contract.py) | `feature`、`smoke`、`contract`、`local_offers` | 当前已按 MCP OpenAPI 沉淀只读接口契约、正向查询、负向鉴权和 canary 冒烟；需补正式需求来源后完善追溯。 |

## 使用方式

- 需求评审时：先按业务能力查本表，确认是否影响已有 `contract`、`smoke` 或 `regression`。
- 新增自动化时：同步更新 [`api-testcases/docs/automation-coverage-index.md`](../api-testcases/docs/automation-coverage-index.md) 与本表。
- 发布回归时：优先选择同业务能力下的 `smoke + regression + contract`，再按新需求补 `feature`。
