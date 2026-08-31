# 接口自动化覆盖索引

本索引维护「需求 / 用例 / Apifox CLI 资产 /（历史）pytest」覆盖关系。  
**正式验收单轨**：[`../api_tests/apifox-cli/`](../api_tests/apifox-cli/) + catalog；pytest 列为冻结对照。退役进度见 [`../api_tests/docs/pytest-retirement-map.md`](../api_tests/docs/pytest-retirement-map.md)。

## 维护规则

- 新需求自动化完成后，必须新增或更新本表，并登记 catalog 资产 key。
- **执行入口**以 Apifox 资产 key / SyncCheck 为准；`pytest 节点` 仅历史对照。
- Collection JSON 在 `api_tests/apifox-cli/collections/`；行为语义以生成器 Tests 为准。

## 覆盖总表

| PAPI / 能力 | 需求 | 功能用例 | pytest 节点 | 分层 / marker | 主链路入口 | Postman |
|---|---|---|---|---|---|---|
| PAPI-2548 会籍 extensions | [`requirements/2026Q2_SP1/PAPI-2548.md`](../../requirements/2026Q2_SP1/PAPI-2548.md) | [`testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2548-会籍extensions非标字段-测试用例.md) | pytest **已删**；执行入口 `papi_2548` → `membership/P1/others`（场景 365969） | CLI 单轨 | Apifox 场景 `PAPI-2548 extensions · CLI sync` | [`PAPI-2548-membership-extensions.postman_collection.json`](../api_tests/apifox-cli/collections/PAPI-2548-membership-extensions.postman_collection.json) |
| PAPI-2515 crossModuleEntitlements | [`requirements/2026Q2_SP1/PAPI-2515.md`](../../requirements/2026Q2_SP1/PAPI-2515.md) | [`testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md) | pytest **已删**；执行入口 `papi_2515`（场景 365972）；**待再调整**见 retirement-map | CLI 单轨 | Apifox 场景 `PAPI-2515 crossModule · CLI sync` | [`PAPI-2515-cross-module-entitlements.postman_collection.json`](../api_tests/apifox-cli/collections/PAPI-2515-cross-module-entitlements.postman_collection.json) |
| PAPI-2424 ePasses details MS 订单提示 | [`requirements/2026Q2_SP1/PAPI-2424.md`](../../requirements/2026Q2_SP1/PAPI-2424.md) | [`testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md`](../../testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md) | pytest **已删**；执行入口 `papi_2424`（场景 365975） | CLI 单轨 | Apifox 场景 `PAPI-2424 ePasses details MS · CLI sync` | [`PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json`](../api_tests/apifox-cli/collections/PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json) |
| Local Offers options | MCP OpenAPI：`project-0-interface_cursor-Q2 local offer` / `/v2/resources/localOffers/{resourceId}/options` | [`testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md`](../../testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md) | pytest **已删**；执行入口 `local_offers_options`（场景 365976） | CLI 单轨 | Apifox 场景 `Local Offers options · CLI sync` | [`LocalOffers-Options-P1.postman_collection.json`](../api_tests/apifox-cli/collections/LocalOffers-Options-P1.postman_collection.json) |
| Local Offer ePass 订单 | [`requirements/2026Q2_SP3/Q2-Local-Offer.md`](../../requirements/2026Q2_SP3/Q2-Local-Offer.md) | [`testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`](../../testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md)、[`LocalOffer订单相关-epass-自动化用例与pytest对应表.md`](../../testcases/2026Q2_SP3/LocalOffer订单相关-epass-自动化用例与pytest对应表.md) | [`api_tests/tests/features/local_offer_epass/`](../api_tests/tests/features/local_offer_epass/)、[`api_tests/tests/features/test_local_offer_epass.py`](../api_tests/tests/features/test_local_offer_epass.py)、[`api_tests/tests/smoke/test_local_offer_epass_smoke.py`](../api_tests/tests/smoke/test_local_offer_epass_smoke.py) | `feature`、`smoke`、`local_offer_epass`、`needs_write` | `RunLocalOfferEpassCreateMainE2EScenario` / `RunLocalOfferEpassPrebookingMainE2EScenario` / `RunLocalOfferEpassBundleMainE2EScenario` | [`LocalOffer-ePass-P1-e2e-core.postman_collection.json`](../api_tests/apifox-cli/collections/LocalOffer-ePass-P1-e2e-core.postman_collection.json)（P1 E2E 核心 E01/E02/E03） |

## 标准执行入口

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548
```

资产表：[`../../.cursor/skills/apifox-cli-repo-first/catalog.md`](../../.cursor/skills/apifox-cli-repo-first/catalog.md)。

历史 pytest（冻结，非日常验收）：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
pytest api-testcases/api_tests/tests -m "smoke or regression or contract" -v --alluredir=reports/api-tests-allure-results
```

## 待补齐项

- 按 [`pytest-retirement-map.md`](../api_tests/docs/pytest-retirement-map.md) 逐资产确认后删除对应 `tests/`。
- 后续新增 PAPI：只登记 catalog + 生成器 + `suites.yaml`，勿新增 pytest 主路径。
