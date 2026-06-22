# Local Offer ePass · 自动化用例与 pytest 对应表

功能用例：[`LocalOffer订单相关-epass-测试用例-001.md`](./LocalOffer订单相关-epass-测试用例-001.md)

pytest 目录：

- **主链路 E2E**：[`api-testcases/api_tests/tests/features/test_local_offer_epass.py`](../../api-testcases/api_tests/tests/features/test_local_offer_epass.py)
- **分模块用例**：[`api-testcases/api_tests/tests/features/local_offer_epass/`](../../api-testcases/api_tests/tests/features/local_offer_epass/)

主链路编排：``RunLocalOfferEpassCreateMainE2EScenario`` / ``RunLocalOfferEpassPrebookingMainE2EScenario`` / ``RunLocalOfferEpassBundleMainE2EScenario``（均含 **取消 + 取消后 details/列表/search**）

**Postman Full 集合**（``LocalOffer-ePass-full-pytest-sync``）：仅导出能稳定写成 HTTP 步骤的用例；**不**包含本表全部行。未导出项见 [`api-testcases/api_tests/postman/README.md`](../../api-testcases/api_tests/postman/README.md) 一节「Full 集合范围」；**权威执行仍以本表 + pytest 为准**。

**module 断言策略**：成功响应（含 orders/ePassesList 列表项）须 ``module=11``，否则 ``LocalOfferModuleMismatchError``；可用性 ``prebookingToken`` 响应无 ``module`` 字段（OAS）不校验。

## 图例

| 状态 | 含义 |
|---|---|
| ✅ auto | 已实现 pytest，CI/本地可跑 |
| ⏭ skip | 环境/数据不满足时 pytest.skip |
| 👤 api+saas | 接口自动跑通，Allure 输出 SaaS 人工核对检查点（``needs_saas_manual_verify``） |
| 📝 manual | ``@pytest.mark.manual``，默认不跑（纯人工/无接口步骤） |
| ❌ — | 暂未实现 |

## CreateEpassOrder

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 主链路创建 + users/search | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateMainChain` | ✅ auto |
| tc-p1 resourceIds 动态获取 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateWithDynamicResourceIds` | ✅ auto |
| tc-p1 **传对应 resourceId 下单**（脑图红框） | `test_create.py::test_LocalOfferEpass_Create_WithMatchingResourceIds` | ✅ auto |
| tc-p1 countryOrRegion 动态获取 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateWithDynamicCountryOrRegion` | ⏭ skip |
| tc-p1 **传对应 countryOrRegion 下单**（脑图红框） | `test_create.py::test_LocalOfferEpass_Create_WithMatchingCountryOrRegion` | ✅/⏭ |
| tc-p1 resourceIds 不传 | `test_create.py::test_LocalOfferEpass_Create_WithoutAllowedResources` | ✅ auto |
| tc-p1 iata 不支持 500.110.026 | `test_create.py::test_LocalOfferEpass_Create_IataRestrictionRejected` | ✅ auto |
| tc-p1 混合 module resourceIds | `test_create.py::test_LocalOfferEpass_Create_MixedModuleResourceIdsRejected` | ✅ auto |
| tc-p1 多限制条件 500.110.015 | `test_create.py::test_LocalOfferEpass_Create_MultipleRestrictionsRejected` | ✅ auto |
| tc-p1 resourceIds >30 500.110.002 | `test_create.py::test_LocalOfferEpass_Create_ResourceIdsOverLimitRejected` | ✅ auto |
| tc-p1 clientUserId 相同且姓名不同 | `test_create.py::test_LocalOfferEpass_Create_DuplicateClientUserIdRejected` | ✅ auto（500.110.011） |
| tc-p1 esim resourceId 500.110.001 | `test_create.py::test_LocalOfferEpass_Create_EsimResourceIdRejected` | ✅ auto |
| tc-p1 500.110.010 内部错误 | — | ❌ 不可稳定构造 |

### CreateEpassOrder · SaaS 权益核对（接口自动 + 人工 SaaS）

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 resourceIds 不传 → 检查 SaaS 权益 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_NoResourceIdsRestriction` | 👤 api+saas |
| tc-p1 传对应 resourceId → 检查 SaaS 权益 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingResourceIds` | 👤 api+saas |
| tc-p1 countryOrRegion 不传 → 检查 SaaS 权益 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_NoCountryOrRegionRestriction` | 👤 api+saas |
| tc-p1 传对应 countryOrRegion → 检查 SaaS 权益 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingCountryOrRegion` | 👤 api+saas |

## RetrieveEpassDetails / RetrieveUserEpassesList

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 orderId 查询扩展字段 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByOrderId_ExtendedFields` | ✅ auto |
| tc-p1 ePassId 查询扩展字段 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByEPassId_ExtendedFields` | ✅ auto |
| tc-p1 search 传 module=8 隔离 | — | ❌ 已移除（``/ePasses/search`` 无 ``module`` 入参） |
| tc-p1 search 仅 ePassId | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByEPassId_Only` | ✅ auto |
| tc-p1 订单不存在 500.080.004 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_OrderNotFound` | ✅ auto |
| tc-p1 users/ePasses module=11 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateMainChain`（创建链内 ``AssertUserEPassesContains``） | ✅ auto |
| tc-p1 ePassStatus 各状态枚举 | — | ❌ 需特定状态数据 |
| tc-p1 500.080.005 跨 program | — | ❌ 需第二 program |

## Create E-pass Prebooking Order

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 三类券型主链路 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType` | ✅/⏭ |
| tc-p1 **voucherType=1 × redemptionUrl 有** | `test_prebooking.py::test_LocalOfferEpass_Prebooking_VoucherTypeAndRedemptionUrl` | ✅ auto |
| tc-p1 **redemptionUrl 无 / voucherType=4+URL 有** | — | ❌ 已移除（沙箱难稳定造数） |
| tc-p1 **轮询各网点 redemptionUrl 有值清单** | — | ❌ 已移除（探测用例会批量下单，改用手工脚本 `tools/probe_local_offer_redemption_url.py`） |
| tc-p1 响应无中文 | — | ❌ 已移除（不再做响应体无中文断言） |
| tc-p1 invalid token 500.110.028 | `test_prebooking.py::test_LocalOfferEpass_Prebooking_InvalidTokenRejected` | ✅ auto |
| tc-p1 reuse token | `test_prebooking.py::test_LocalOfferEpass_Prebooking_ReuseTokenRejected` | ✅ auto |
| tc-p1 esim token 下 local offer | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EsimAvailabilityToken_Rejected`（``test_prebooking.py`` 同名用例已删，避免重复） | ✅ auto |
| tc-p1 **未指定 ePassId token 预约** | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_WithoutEpassIdToken_Success` | ✅ auto |
| tc-p1 **ePassId 一致/不一致** | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EpassIdMatch_Success` / `…_EpassIdMismatch_Rejected` | ✅ auto |
| tc-p2 **token 与请求主体一致性**（resource/ePassId/module） | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_TokenResourceMismatch_Rejected` / `…_EpassIdMismatch_Rejected` / `…_EsimAvailabilityToken_Rejected` | ✅ auto |
| tc-p2 **ePassId 权益 countryOrRegion 限制外** | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_OutOfRange_Rejected` | ✅ auto |
| tc-p1 **membershipId token** | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_MembershipIdToken_Rejected` | ✅ auto（``POST /v2/memberships`` 取 membershipId，ePass token 无权限时回退默认 client） |
| tc-p1 权益点数=0 | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_ZeroAvailableUsages_Rejected` | ✅ auto |
| tc-p1 人数 vs 权益点数 | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_GuestCountVsAvailableUsages` | ✅ auto |
| tc-p1 无 LO 权益 ePass | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_NoLocalOfferEntitlement_Rejected` | ⏭ 需 `DP_LO_EPASS_NO_LO_ENTITLEMENT_EPASS_ID` |
| tc-p1 **eSIM+LO 权益矩阵 12 步** | `test_prebooking_entitlements.py::test_LocalOfferEpass_EsimLoEntitlementMatrix_OneScenario` | ✅ auto（含下单后 list/details module 隔离） |
| tc-p1 **resourceIds 限制内/外** | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_ResourceIdsRestriction_*` | ✅/⏭ |
| tc-p1 **countryOrRegion 限制内/外** | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_*` | ✅/⏭ |
| tc-p1 相同条件多 token | — | 📝 md 标注不测 |
| tc-p1 async=true/false | — | ❌ 未区分断言 |
| tc-p1 500.110.027/029/019/020 | 部分由 availability/prebooking 负向覆盖 | 部分 |

### Prebooking · SaaS/供应商核对（接口自动 + 人工 SaaS）

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 无限制 ePass 预约 → sass 核对 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_UnrestrictedEpass` | 👤 api+saas |
| tc-p1 限制 resourceIds 后预约 → sass 核对 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithResourceIdsRestriction` | 👤 api+saas |
| tc-p1 限制 countryOrRegion 后预约 → sass 核对 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithCountryOrRegionRestriction` | 👤 api+saas |

## Bundle (Create E-pass with Prebooking)

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 Bundle 主链路 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_BundleMainChain_ByVoucherType` | ✅/⏭ |
| tc-p1 **voucherType=1 × redemptionUrl 有** | `test_bundle.py::test_LocalOfferEpass_Bundle_VoucherTypeAndRedemptionUrl` | ✅ auto |
| tc-p1 **redemptionUrl 无 / voucherType=4+URL 有** | — | ❌ 已移除 |
| tc-p1 响应无中文 | — | ❌ 已移除（不再做响应体无中文断言） |
| tc-p1 invalid token | `test_bundle.py::test_LocalOfferEpass_Bundle_InvalidTokenRejected` | ✅ auto |
| tc-p1 reuse token | `test_bundle.py::test_LocalOfferEpass_Bundle_ReuseTokenRejected` | ✅ auto |
| tc-p1 **未指定 ePassId token Bundle + retrieve 隔离** | `test_bundle_token.py::test_LocalOfferEpass_Bundle_WithoutEpassIdToken_Success` | ✅ auto |
| tc-p1 **指定 ePassId 绑定 token 应拒绝** | `test_bundle_token.py::test_LocalOfferEpass_Bundle_EpassIdBoundToken_Rejected` | ✅ auto |
| tc-p1 membershipId token | `test_bundle_token.py::test_LocalOfferEpass_Bundle_MembershipIdToken_Rejected` | ✅ auto |
| tc-p1 esim token 下 local offer | `test_bundle_token.py::test_LocalOfferEpass_Bundle_EsimAvailabilityToken_Rejected` | ✅ auto |
| tc-p1 Bundle → SaaS 核对 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Bundle_CreateAndPrebook` | 👤 api+saas |
| tc-p2 补偿 disableOrder | `test_bundle.py::test_LocalOfferEpass_Bundle_CompensationAfterPrebookingFailure_Manual` | 📝 manual |

## Usage Details / Order List

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 usage 详情（取消后 status=3） | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType`（``CancelUsageOrderAndVerifyPostCancelRetrieve``） | ✅ auto |
| tc-p1 usage 不存在 500.110.004 | `test_retrieve.py::test_LocalOfferEpass_UsageDetails_OrderNotFound` | ✅ auto |
| tc-p1 订单列表分页（取消后） | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType`（同上） | ✅ auto |
| tc-p1 创建后空列表 | `test_retrieve.py::test_LocalOfferEpass_OrderList_AfterCreateOnly` | ✅ auto |
| tc-p1 status 全枚举 / vouchersList SaaS | — | ❌ 部分字段 |

## Epass 取消订单

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 取消未核销 usage 预订单 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType` | ✅ auto |
| tc-p1 取消会籍购买单 | `test_cancel.py::test_LocalOfferEpass_CancelPurchaseOrder` | ✅ auto（接口取消 + search 侧效应；SaaS 权益 Allure 检查点） |

## v2_resources_options_prebookings_availability

| 用例 md 节点 | pytest | 状态 |
|---|---|---|
| tc-p1 adult=1 child=0 | `test_availability.py::test_LocalOfferEpass_Availability_Adult1Child0_Success` | ✅ auto |
| tc-p1 非法人数组合 | `test_availability.py::test_LocalOfferEpass_Availability_InvalidGuestCountsRejected` | ✅ auto |
| tc-p1 过期 prebookingDate | `test_availability.py::test_LocalOfferEpass_Availability_PastDateRejected` | ✅ auto |
| tc-p1 esim 资源 module=11 | `test_availability.py::test_LocalOfferEpass_Availability_EsimResourceOnModule11Rejected` | ✅ auto |
| tc-p2 membership/ePass 异常 | `test_availability.py::test_LocalOfferEpass_Availability_AbnormalMembershipOrEpass_Manual` | 📝 manual |

## 运行

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
$env:DP_PROFILE = "canary"
# 仅主链路 E2E
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py -m "local_offer_epass" -v
# 全量（含分模块负向/边界，不含纯 manual）
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py api-testcases/api_tests/tests/features/local_offer_epass -m "local_offer_epass and not manual" -v --alluredir=reports/local-offer-epass-allure-results
# 含 SaaS 人工核对检查点（接口自动 + Allure 输出核对清单）
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py api-testcases/api_tests/tests/features/local_offer_epass -m "local_offer_epass and not manual" -v --alluredir=reports/local-offer-epass-allure-results
# 仅 SaaS 检查点套件
pytest api-testcases/api_tests/tests/features/local_offer_epass/test_saas_manual_checkpoint.py -m "needs_saas_manual_verify" -v --alluredir=reports/local-offer-epass-allure-results
allure serve reports/local-offer-epass-allure-results
```
