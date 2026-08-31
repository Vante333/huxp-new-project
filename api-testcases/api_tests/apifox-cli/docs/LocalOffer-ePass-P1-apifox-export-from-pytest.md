# Local Offer ePass · P1 E2E：pytest → Postman Collection 导出

**权威执行**仍以 **pytest + Allure + `local_offer_epass_service`** 为准；本集合为 **Postman Collection v2.1**，Tests 脚本与 Python `Assert*` **字段级对齐**（每条 HTTP 对应多条 `pm.test`）。

## 1. 导入文件（Postman 格式 · 主入口）

| 文件 | 导入方式 | 说明 |
|------|----------|------|
| [**`LocalOffer-ePass-P1-e2e-core.postman_collection.json`**](../collections/LocalOffer-ePass-P1-e2e-core.postman_collection.json) | **Postman** 或 Apifox **导入 → Postman** | **主文件**：35 步 Tests，E01 取消前/后各一组 module 隔离（`I06`–`I09`） |
| [`LocalOffer-ePass-tc-P1-mainflow.postman_collection.json`](../collections/LocalOffer-ePass-tc-P1-mainflow.postman_collection.json) | 同上 | 与 e2e-core 相同（兼容旧名） |
| [`GeneratePostmanCollectionLocalOfferEpass.py`](../generators/GeneratePostmanCollectionLocalOfferEpass.py) | — | 生成器（同时写出 Postman + 可选 Apifox 场景包到 `generated/`） |
| [`LocalOffer-ePass-P1-e2e-core.apifox-2.7.43-import.json`](../generated/LocalOffer-ePass-P1-e2e-core.apifox-2.7.43-import.json) | 仅 Apifox **导入 → Apifox** | 可选；本地生成（gitignore） |

导入步骤：**[`LocalOffer-ePass-P1-apifox-2.7.43-导入说明.md`](LocalOffer-ePass-P1-apifox-2.7.43-导入说明.md)**（第一节为 Postman 格式）

## 2. 三条 P1 E2E ↔ pytest

| 文件夹 | pytest | 编排入口 |
|--------|--------|----------|
| **E01 · 创建验证链** | `test_LocalOfferEpass_E2E_CreateMainChain` | `RunLocalOfferEpassCreateMainE2EScenario` |
| **E02 · 预约验证链** | `test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType[card_secret]` | `RunLocalOfferEpassPrebookingMainE2EScenario` |
| **E03 · Bundle 一步下单** | `test_LocalOfferEpass_E2E_BundleMainChain_ByVoucherType[redemption_code]` | `RunLocalOfferEpassBundleMainE2EScenario` |

## 3. 集合变量

| 集合变量 | 环境变量 | 说明 |
|----------|----------|------|
| `ProgramID` | `DP_EPASS_PROGRAM_ID` | `X-Program-ID` |
| `clientId` | `DP_EPASS_CLIENT_ID` | token body |
| `secret` | `DP_EPASS_CLIENT_SECRET` | token body |
| `x-version` | `DP_X_VERSION` | canary 填 `canary` |
| `prebookingDate` | `DP_LO_EPASS_PREBOOKING_DATE` | 未填则 Auth 前置脚本 **UTC+10天 10:30** |
| `resourceId` / `optionId` | `DP_LO_EPASS_*` | E02 用 `CARD_SECRET_*`；E03 用 `REDEMPTION_CODE_*` |
| `expectedVoucherType` | — | E02 自动设 `1`；E03 自动设 `4` |
| `clientUserId` / `ePassId` / `purchaseOrderId` / `usageOrderId` / `prebookingToken` | — | 步骤间自动写入 |

## 4. 断言 ↔ Python 对照（按链路）

### E01 创建验证链

| 步骤 | Python 断言 |
|------|-------------|
| E01-S01 创建 | `AssertLocalOfferEpassCreateCoreFields` · `ExtractCreateEpassIds` |
| E01-S02 users | `AssertUserEPassesContains` |
| E01-S03/S04 search | `AssertEpassSearchDetailsCoreFields`（search 无 module 入参） |
| E01-S05 列表 | `AssertOrderListPaginationShape` · orders 可为空 |
| E01-I06/I07 module 隔离 | `AssertLocalOfferNotReturnedWithEsimModuleFilter` / `AssertEsimNotReturnedWithLocalOfferModuleFilter` · **取消前** |
| E01-S06 取消 MS | `AssertCancelOrderSuccess` |
| E01-I08/I09 module 隔离 | 同上 · **取消后** |
| E01-S07 取消后列表 | `AssertOrderListPaginationShape` |
| E01-S08 取消后 search | `AssertEpassSearchShowsCancelledAfterPurchaseCancel` |

### E02 预约验证链

| 步骤 | Python 断言 |
|------|-------------|
| E02-S01 创建 | 同 E01-S01 |
| E02-S02 可用性（有 ePassId） | `AssertPrebookingAvailabilitySuccess` |
| E02-S03 prebooking | `AssertLocalOfferPrebookingOrderSuccess` |
| E02-S04/S05 module=8 隔离 | `AssertLocalOfferNotReturnedWithEsimModuleFilter` |
| E02-S06 取消 usage | `AssertCancelOrderSuccess` |
| E02-S07 details | `AssertUsageOrderDetailsShowsCancelled` |
| E02-S08 列表 | `AssertOrderListPaginationShape` · `AssertUsageOrderListContainsCancelled` |
| E02-S09 search | `AssertEpassSearchActiveAfterUsageCancel` |

### E03 Bundle

| 步骤 | Python 断言 |
|------|-------------|
| E03-S01 可用性（无 ePassId） | `RequestPrebookingTokenWithoutEpass` |
| E03-S02 bundle | `AssertBundleOrderSuccess` |
| E03-S03/S04 module=8 隔离 | `AssertLocalOfferNotReturnedWithEsimModuleFilter` |
| E03-S05 users | `AssertUserEPassesContains` |
| E03-S06/S07 search | `AssertEpassSearchDetailsCoreFields` |
| E03-S08～S11 | 同 E02 取消 usage 收尾 |
| E03-S12/S13 | `CancelPurchaseOrderAndVerifyPostCancelRetrieve` |

## 5. 公共脚本

将生成器 **`BuildLocalOfferJsHelpersLines()`** 内 `js = r"""..."""` 复制到 Apifox **项目公共后置脚本**（或集合父级），与 PAPI-2515 导出方式一致。

## 6. 运行顺序

1. 填环境变量 → 跑 **00 Auth**
2. 按需选 **E01 / E02 / E03** 文件夹，**从上到下**执行（各文件夹独立，E02/E03 前置脚本会重置 `clientUserId` 等）
3. E02/E03 运行前务必填好对应 `resourceId`、`optionId`
