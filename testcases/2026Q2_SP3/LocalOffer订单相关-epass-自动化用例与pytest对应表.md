# Local Offer ePass 路 鑷姩鍖栫敤渚嬩笌 pytest 瀵瑰簲琛?

鍔熻兘鐢ㄤ緥锛歔`LocalOffer璁㈠崟鐩稿叧-epass-娴嬭瘯鐢ㄤ緥-001.md`](./LocalOffer璁㈠崟鐩稿叧-epass-娴嬭瘯鐢ㄤ緥-001.md)

pytest 鐩綍锛?

- **涓婚摼璺?E2E**锛歔`api-testcases/api_tests/tests/features/test_local_offer_epass.py`](../../api-testcases/api_tests/tests/features/test_local_offer_epass.py)
- **鍒嗘ā鍧楃敤渚?*锛歔`api-testcases/api_tests/tests/features/local_offer_epass/`](../../api-testcases/api_tests/tests/features/local_offer_epass/)

涓婚摼璺紪鎺掞細``RunLocalOfferEpassCreateMainE2EScenario`` / ``RunLocalOfferEpassPrebookingMainE2EScenario`` / ``RunLocalOfferEpassBundleMainE2EScenario``锛堝潎鍚?**鍙栨秷 + 鍙栨秷鍚?details/鍒楄〃/search**锛?

**Postman Full 闆嗗悎**锛坄`LocalOffer-ePass-full-pytest-sync``锛夛細浠呭鍑鸿兘绋冲畾鍐欐垚 HTTP 姝ラ鐨勭敤渚嬶紱**涓?*鍖呭惈鏈〃鍏ㄩ儴琛屻€傛湭瀵煎嚭椤硅 [`api-testcases/api_tests/apifox-cli/README.md`](../../api-testcases/api_tests/apifox-cli/README.md) 涓€鑺傘€孎ull 闆嗗悎鑼冨洿銆嶏紱**鏉冨▉鎵ц浠嶄互鏈〃 + pytest 涓哄噯**銆?

**module 鏂█绛栫暐**锛氭垚鍔熷搷搴旓紙鍚?orders/ePassesList 鍒楄〃椤癸級椤?``module=11``锛屽惁鍒?``LocalOfferModuleMismatchError``锛涘彲鐢ㄦ€?``prebookingToken`` 鍝嶅簲鏃?``module`` 瀛楁锛圤AS锛変笉鏍￠獙銆?

## 鍥句緥

| 鐘舵€?| 鍚箟 |
|---|---|
| 鉁?auto | 宸插疄鐜?pytest锛孋I/鏈湴鍙窇 |
| 鈴?skip | 鐜/鏁版嵁涓嶆弧瓒虫椂 pytest.skip |
| 馃懁 api+saas | 鎺ュ彛鑷姩璺戦€氾紝Allure 杈撳嚭 SaaS 浜哄伐鏍稿妫€鏌ョ偣锛坄`needs_saas_manual_verify``锛?|
| 馃摑 manual | ``@pytest.mark.manual``锛岄粯璁や笉璺戯紙绾汉宸?鏃犳帴鍙ｆ楠わ級 |
| 鉂?鈥?| 鏆傛湭瀹炵幇 |

## CreateEpassOrder

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 涓婚摼璺垱寤?+ users/search | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateMainChain` | 鉁?auto |
| tc-p1 resourceIds 鍔ㄦ€佽幏鍙?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateWithDynamicResourceIds` | 鉁?auto |
| tc-p1 **浼犲搴?resourceId 涓嬪崟**锛堣剳鍥剧孩妗嗭級 | `test_create.py::test_LocalOfferEpass_Create_WithMatchingResourceIds` | 鉁?auto |
| tc-p1 countryOrRegion 鍔ㄦ€佽幏鍙?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateWithDynamicCountryOrRegion` | 鈴?skip |
| tc-p1 **浼犲搴?countryOrRegion 涓嬪崟**锛堣剳鍥剧孩妗嗭級 | `test_create.py::test_LocalOfferEpass_Create_WithMatchingCountryOrRegion` | 鉁?鈴?|
| tc-p1 resourceIds 涓嶄紶 | `test_create.py::test_LocalOfferEpass_Create_WithoutAllowedResources` | 鉁?auto |
| tc-p1 iata 涓嶆敮鎸?500.110.026 | `test_create.py::test_LocalOfferEpass_Create_IataRestrictionRejected` | 鉁?auto |
| tc-p1 娣峰悎 module resourceIds | `test_create.py::test_LocalOfferEpass_Create_MixedModuleResourceIdsRejected` | 鉁?auto |
| tc-p1 澶氶檺鍒舵潯浠?500.110.015 | `test_create.py::test_LocalOfferEpass_Create_MultipleRestrictionsRejected` | 鉁?auto |
| tc-p1 resourceIds >30 500.110.002 | `test_create.py::test_LocalOfferEpass_Create_ResourceIdsOverLimitRejected` | 鉁?auto |
| tc-p1 clientUserId 鐩稿悓涓斿鍚嶄笉鍚?| `test_create.py::test_LocalOfferEpass_Create_DuplicateClientUserIdRejected` | 鉁?auto锛?00.110.011锛?|
| tc-p1 esim resourceId 500.110.001 | `test_create.py::test_LocalOfferEpass_Create_EsimResourceIdRejected` | 鉁?auto |
| tc-p1 500.110.010 鍐呴儴閿欒 | 鈥?| 鉂?涓嶅彲绋冲畾鏋勯€?|

### CreateEpassOrder 路 SaaS 鏉冪泭鏍稿锛堟帴鍙ｈ嚜鍔?+ 浜哄伐 SaaS锛?

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 resourceIds 涓嶄紶 鈫?妫€鏌?SaaS 鏉冪泭 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_NoResourceIdsRestriction` | 馃懁 api+saas |
| tc-p1 浼犲搴?resourceId 鈫?妫€鏌?SaaS 鏉冪泭 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingResourceIds` | 馃懁 api+saas |
| tc-p1 countryOrRegion 涓嶄紶 鈫?妫€鏌?SaaS 鏉冪泭 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_NoCountryOrRegionRestriction` | 馃懁 api+saas |
| tc-p1 浼犲搴?countryOrRegion 鈫?妫€鏌?SaaS 鏉冪泭 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingCountryOrRegion` | 馃懁 api+saas |

## RetrieveEpassDetails / RetrieveUserEpassesList

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 orderId 鏌ヨ鎵╁睍瀛楁 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByOrderId_ExtendedFields` | 鉁?auto |
| tc-p1 ePassId 鏌ヨ鎵╁睍瀛楁 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByEPassId_ExtendedFields` | 鉁?auto |
| tc-p1 search 浼?module=8 闅旂 | 鈥?| 鉂?宸茬Щ闄わ紙``/ePasses/search`` 鏃?``module`` 鍏ュ弬锛?|
| tc-p1 search 浠?ePassId | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_ByEPassId_Only` | 鉁?auto |
| tc-p1 璁㈠崟涓嶅瓨鍦?500.080.004 | `test_retrieve.py::test_LocalOfferEpass_SearchDetails_OrderNotFound` | 鉁?auto |
| tc-p1 users/ePasses module=11 | `test_local_offer_epass.py::test_LocalOfferEpass_E2E_CreateMainChain`锛堝垱寤洪摼鍐?``AssertUserEPassesContains``锛?| 鉁?auto |
| tc-p1 ePassStatus 鍚勭姸鎬佹灇涓?| 鈥?| 鉂?闇€鐗瑰畾鐘舵€佹暟鎹?|
| tc-p1 500.080.005 璺?program | 鈥?| 鉂?闇€绗簩 program |

## Create E-pass Prebooking Order

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 涓夌被鍒稿瀷涓婚摼璺?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType` | 鉁?鈴?|
| tc-p1 **voucherType=1 脳 redemptionUrl 鏈?* | `test_prebooking.py::test_LocalOfferEpass_Prebooking_VoucherTypeAndRedemptionUrl` | 鉁?auto |
| tc-p1 **redemptionUrl 鏃?/ voucherType=4+URL 鏈?* | 鈥?| 鉂?宸茬Щ闄わ紙娌欑闅剧ǔ瀹氶€犳暟锛?|
| tc-p1 **杞鍚勭綉鐐?redemptionUrl 鏈夊€兼竻鍗?* | 鈥?| 鉂?宸茬Щ闄わ紙鎺㈡祴鐢ㄤ緥浼氭壒閲忎笅鍗曪紝鏀圭敤鎵嬪伐鑴氭湰 `tools/probe_local_offer_redemption_url.py`锛?|
| tc-p1 鍝嶅簲鏃犱腑鏂?| 鈥?| 鉂?宸茬Щ闄わ紙涓嶅啀鍋氬搷搴斾綋鏃犱腑鏂囨柇瑷€锛?|
| tc-p1 invalid token 500.110.028 | `test_prebooking.py::test_LocalOfferEpass_Prebooking_InvalidTokenRejected` | 鉁?auto |
| tc-p1 reuse token | `test_prebooking.py::test_LocalOfferEpass_Prebooking_ReuseTokenRejected` | 鉁?auto |
| tc-p1 esim token 涓?local offer | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EsimAvailabilityToken_Rejected`锛坄`test_prebooking.py`` 鍚屽悕鐢ㄤ緥宸插垹锛岄伩鍏嶉噸澶嶏級 | 鉁?auto |
| tc-p1 **鏈寚瀹?ePassId token 棰勭害** | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_WithoutEpassIdToken_Success` | 鉁?auto |
| tc-p1 **ePassId 涓€鑷?涓嶄竴鑷?* | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_EpassIdMatch_Success` / `鈥EpassIdMismatch_Rejected` | 鉁?auto |
| tc-p2 **token 涓庤姹備富浣撲竴鑷存€?*锛坮esource/ePassId/module锛?| `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_TokenResourceMismatch_Rejected` / `鈥EpassIdMismatch_Rejected` / `鈥EsimAvailabilityToken_Rejected` | 鉁?auto |
| tc-p2 **ePassId 鏉冪泭 countryOrRegion 闄愬埗澶?* | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_OutOfRange_Rejected` | 鉁?auto |
| tc-p1 **membershipId token** | `test_prebooking_token.py::test_LocalOfferEpass_Prebooking_MembershipIdToken_Rejected` | 鉁?auto锛坄`POST /v2/memberships`` 鍙?membershipId锛宔Pass token 鏃犳潈闄愭椂鍥為€€榛樿 client锛?|
| tc-p1 鏉冪泭鐐规暟=0 | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_ZeroAvailableUsages_Rejected` | 鉁?auto |
| tc-p1 浜烘暟 vs 鏉冪泭鐐规暟 | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_GuestCountVsAvailableUsages` | 鉁?auto |
| tc-p1 鏃?LO 鏉冪泭 ePass | `test_prebooking_entitlements.py::test_LocalOfferEpass_Prebooking_NoLocalOfferEntitlement_Rejected` | 鈴?闇€ `DP_LO_EPASS_NO_LO_ENTITLEMENT_EPASS_ID` |
| tc-p1 **eSIM+LO 鏉冪泭鐭╅樀 12 姝?* | `test_prebooking_entitlements.py::test_LocalOfferEpass_EsimLoEntitlementMatrix_OneScenario` | 鉁?auto锛堝惈涓嬪崟鍚?list/details module 闅旂锛?|
| tc-p1 **resourceIds 闄愬埗鍐?澶?* | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_ResourceIdsRestriction_*` | 鉁?鈴?|
| tc-p1 **countryOrRegion 闄愬埗鍐?澶?* | `test_prebooking_restrictions.py::test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_*` | 鉁?鈴?|
| tc-p1 鐩稿悓鏉′欢澶?token | 鈥?| 馃摑 md 鏍囨敞涓嶆祴 |
| tc-p1 async=true/false | 鈥?| 鉂?鏈尯鍒嗘柇瑷€ |
| tc-p1 500.110.027/029/019/020 | 閮ㄥ垎鐢?availability/prebooking 璐熷悜瑕嗙洊 | 閮ㄥ垎 |

### Prebooking 路 SaaS/渚涘簲鍟嗘牳瀵癸紙鎺ュ彛鑷姩 + 浜哄伐 SaaS锛?

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 鏃犻檺鍒?ePass 棰勭害 鈫?sass 鏍稿 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_UnrestrictedEpass` | 馃懁 api+saas |
| tc-p1 闄愬埗 resourceIds 鍚庨绾?鈫?sass 鏍稿 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithResourceIdsRestriction` | 馃懁 api+saas |
| tc-p1 闄愬埗 countryOrRegion 鍚庨绾?鈫?sass 鏍稿 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithCountryOrRegionRestriction` | 馃懁 api+saas |

## Bundle (Create E-pass with Prebooking)

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 Bundle 涓婚摼璺?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_BundleMainChain_ByVoucherType` | 鉁?鈴?|
| tc-p1 **voucherType=1 脳 redemptionUrl 鏈?* | `test_bundle.py::test_LocalOfferEpass_Bundle_VoucherTypeAndRedemptionUrl` | 鉁?auto |
| tc-p1 **redemptionUrl 鏃?/ voucherType=4+URL 鏈?* | 鈥?| 鉂?宸茬Щ闄?|
| tc-p1 鍝嶅簲鏃犱腑鏂?| 鈥?| 鉂?宸茬Щ闄わ紙涓嶅啀鍋氬搷搴斾綋鏃犱腑鏂囨柇瑷€锛?|
| tc-p1 invalid token | `test_bundle.py::test_LocalOfferEpass_Bundle_InvalidTokenRejected` | 鉁?auto |
| tc-p1 reuse token | `test_bundle.py::test_LocalOfferEpass_Bundle_ReuseTokenRejected` | 鉁?auto |
| tc-p1 **鏈寚瀹?ePassId token Bundle + retrieve 闅旂** | `test_bundle_token.py::test_LocalOfferEpass_Bundle_WithoutEpassIdToken_Success` | 鉁?auto |
| tc-p1 **鎸囧畾 ePassId 缁戝畾 token 搴旀嫆缁?* | `test_bundle_token.py::test_LocalOfferEpass_Bundle_EpassIdBoundToken_Rejected` | 鉁?auto |
| tc-p1 membershipId token | `test_bundle_token.py::test_LocalOfferEpass_Bundle_MembershipIdToken_Rejected` | 鉁?auto |
| tc-p1 esim token 涓?local offer | `test_bundle_token.py::test_LocalOfferEpass_Bundle_EsimAvailabilityToken_Rejected` | 鉁?auto |
| tc-p1 Bundle 鈫?SaaS 鏍稿 | `test_saas_manual_checkpoint.py::test_LocalOfferEpass_SaasCheckpoint_Bundle_CreateAndPrebook` | 馃懁 api+saas |
| tc-p2 琛ュ伩 disableOrder | `test_bundle.py::test_LocalOfferEpass_Bundle_CompensationAfterPrebookingFailure_Manual` | 馃摑 manual |

## Usage Details / Order List

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 usage 璇︽儏锛堝彇娑堝悗 status=3锛?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType`锛坄`CancelUsageOrderAndVerifyPostCancelRetrieve``锛?| 鉁?auto |
| tc-p1 usage 涓嶅瓨鍦?500.110.004 | `test_retrieve.py::test_LocalOfferEpass_UsageDetails_OrderNotFound` | 鉁?auto |
| tc-p1 璁㈠崟鍒楄〃鍒嗛〉锛堝彇娑堝悗锛?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType`锛堝悓涓婏級 | 鉁?auto |
| tc-p1 鍒涘缓鍚庣┖鍒楄〃 | `test_retrieve.py::test_LocalOfferEpass_OrderList_AfterCreateOnly` | 鉁?auto |
| tc-p1 status 鍏ㄦ灇涓?/ vouchersList SaaS | 鈥?| 鉂?閮ㄥ垎瀛楁 |

## Epass 鍙栨秷璁㈠崟

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 鍙栨秷鏈牳閿€ usage 棰勮鍗?| `test_local_offer_epass.py::test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType` | 鉁?auto |
| tc-p1 鍙栨秷浼氱睄璐拱鍗?| `test_cancel.py::test_LocalOfferEpass_CancelPurchaseOrder` | 鉁?auto锛堟帴鍙ｅ彇娑?+ search 渚ф晥搴旓紱SaaS 鏉冪泭 Allure 妫€鏌ョ偣锛?|

## v2_resources_options_prebookings_availability

| 鐢ㄤ緥 md 鑺傜偣 | pytest | 鐘舵€?|
|---|---|---|
| tc-p1 adult=1 child=0 | `test_availability.py::test_LocalOfferEpass_Availability_Adult1Child0_Success` | 鉁?auto |
| tc-p1 闈炴硶浜烘暟缁勫悎 | `test_availability.py::test_LocalOfferEpass_Availability_InvalidGuestCountsRejected` | 鉁?auto |
| tc-p1 杩囨湡 prebookingDate | `test_availability.py::test_LocalOfferEpass_Availability_PastDateRejected` | 鉁?auto |
| tc-p1 esim 璧勬簮 module=11 | `test_availability.py::test_LocalOfferEpass_Availability_EsimResourceOnModule11Rejected` | 鉁?auto |
| tc-p2 membership/ePass 寮傚父 | `test_availability.py::test_LocalOfferEpass_Availability_AbnormalMembershipOrEpass_Manual` | 馃摑 manual |

## 杩愯

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
$env:DP_PROFILE = "canary"
# 浠呬富閾捐矾 E2E
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py -m "local_offer_epass" -v
# 鍏ㄩ噺锛堝惈鍒嗘ā鍧楄礋鍚?杈圭晫锛屼笉鍚函 manual锛?
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py api-testcases/api_tests/tests/features/local_offer_epass -m "local_offer_epass and not manual" -v --alluredir=reports/local-offer-epass-allure-results
# 鍚?SaaS 浜哄伐鏍稿妫€鏌ョ偣锛堟帴鍙ｈ嚜鍔?+ Allure 杈撳嚭鏍稿娓呭崟锛?
pytest api-testcases/api_tests/tests/features/test_local_offer_epass.py api-testcases/api_tests/tests/features/local_offer_epass -m "local_offer_epass and not manual" -v --alluredir=reports/local-offer-epass-allure-results
# 浠?SaaS 妫€鏌ョ偣濂椾欢
pytest api-testcases/api_tests/tests/features/local_offer_epass/test_saas_manual_checkpoint.py -m "needs_saas_manual_verify" -v --alluredir=reports/local-offer-epass-allure-results
allure serve reports/local-offer-epass-allure-results
```

