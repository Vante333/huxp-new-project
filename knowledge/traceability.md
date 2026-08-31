# 业务接口追溯表

本表按业务能力维护需求、用例、自动化与报告入口，服务于跨迭代影响分析和历史回归选择。需求原文仍以 `requirements/` 为准，自动化主线为 `api-testcases/api_tests/`。

## 追溯矩阵

| 业务能力 | 需求来源 | 功能用例 | 自动化入口 | 回归分层 | 维护说明 |
|---|---|---|---|---|---|
| 会籍 extensions | [`requirements/2026Q2_SP1/PAPI-2548.md`](../requirements/2026Q2_SP1/PAPI-2548.md) | [`testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md) | [`api-testcases/api_tests/tests/features/test_membership_extensions.py`](../api-testcases/api_tests/tests/features/test_membership_extensions.py)、[`api-testcases/api_tests/tests/contract/test_membership_extensions_normalize_parity.py`](../api-testcases/api_tests/tests/contract/test_membership_extensions_normalize_parity.py) | `feature`、`contract`、`papi2548` | 新增字段或校验规则时，优先扩展 `services/papi2548_service.py` 与 PAPI-2548 对应表。 |
| crossModuleEntitlements | [`requirements/2026Q2_SP1/PAPI-2515.md`](../requirements/2026Q2_SP1/PAPI-2515.md) | [`testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md) | Apifox CLI `papi_2515`（场景 365972）；pytest 已删 | CLI 单轨 | 主链路以生成器 + SyncCheck 为准；**待再调整**见 `api_tests/docs/pytest-retirement-map.md`。 |
| ePasses details MS 订单提示 | [`requirements/2026Q2_SP1/PAPI-2424.md`](../requirements/2026Q2_SP1/PAPI-2424.md) | [`testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md`](../testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md) | Apifox CLI `papi_2424`（场景 365975）；pytest 已删 | CLI 单轨 | 以生成器 + SyncCheck 回归 MS 前缀提示，避免退化。 |
| Local Offers options | MCP OpenAPI：`project-0-interface_cursor-Q2 local offer` / `/v2/resources/localOffers/{resourceId}/options` | [`testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md`](../testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md) | Apifox CLI `local_offers_options`（场景 365976）；pytest 已删 | CLI 单轨 | 只读契约/正向/负向鉴权以生成器 + SyncCheck 为准。 |

## 使用方式

- 需求评审时：先按业务能力查本表，确认是否影响已有 `contract`、`smoke` 或 `regression`。
- 新增自动化时：同步更新 [`api-testcases/docs/automation-coverage-index.md`](../api-testcases/docs/automation-coverage-index.md) 与本表。
- 发布回归时：优先选择同业务能力下的 `smoke + regression + contract`，再按新需求补 `feature`。
