"""
生成 lounge ePass **P0 E2E 核心** Postman Collection v2.1 JSON。

对齐 ``test_historical_epass_regression.py`` lounge 三条主链路及 ``historical_epass_service`` 断言语义（``catalog_label="lounge"``）：

- E01 创建验证链 · ``RunHistoricalEpassCreateMainE2EScenario``
- E02 预约验证链 · ``RunHistoricalEpassPrebookingMainE2EScenario``
- E03 Bundle 一步下单 · ``RunHistoricalEpassBundleMainE2EScenario``

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionLoungeEpass.py
"""
from __future__ import annotations

import json
import os
from typing import Any, List

from collection_builder_common import (
    CollectionPath,
    POSTMAN_SCHEMA,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    Lines_EnsureEnvKeysIfMissing,
    Lines_Step,
    PREBOOKING_ADD_DAYS_START,
    PurposeName,
    WriteCollectionJson,
)

from lounge_epass_common import (
    AvailabilityBody,
    BuildCancelWithRetryBlock,
    CREATE_PAYLOAD_TEMPLATE,
    DEFAULT_API_VERSION,
    DEFAULT_LOUNGE_RESOURCE_ID,
    ENV_LOUNGE_RESOURCE_ID,
    EPASS_MODULE_DEFAULT,
    EPASS_MAIN_CHAIN_SPECS,
    GENERATED_CANCEL_ATTEMPTS,
    JsonObject,
    LOUNGE_RESOURCE_ID_VAR,
    Lines_Auth,
    LoungePrebookingExtraDict,
    LoungeRequestItem,
    OTHER_MODULE_DEFAULT,
    OUT_NAME,
    OrdersListBodyNative,
    OrdersListBodyOtherModule,
    Prerequest_NewClientUserId,
    Prerequest_ResetForBundle,
    Prerequest_ResetForPrebooking,
    Prerequest_SyncPrebookingDateFromApifox,
    SetLoungeAssertEpassStatus,
    UsageDetailsBody,
    _LoungeJsHelpers,
)


def BuildCreateE2EFolder() -> JsonObject:
    e01_i08_name = PurposeName(
        "otherModule=11 列表不含 lounge（取消 MS 后）", "E01-I08", "POST", "/ePasses?module=11"
    )
    return Folder(
        "E01 · tc-P0 创建",
        [
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("创建 lounge ePass（MS 购买单）", "E01-S01", "POST", "/lounges/ePasses"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["create"].path,
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassCreateCoreFields`` · ``ExtractCreateEpassIds``",
                prerequest_lines=Prerequest_NewClientUserId(),
                test_lines=Lines_Step(
                    "E01-S01",
                    ["lpAssertHttpBusinessOk('E01-S01');", "lpAssertCreateCoreFields('E01-S01');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("users 列表含本 clientUserId 的 ePass", "E01-S02", "POST", "/users/ePasses"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["users"].path,
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E01-S02",
                    ["lpAssertHttpBusinessOk('E01-S02');", "lpAssertUserListContains('E01-S02');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 purchaseOrderId 查 MS 详情", "E01-S03", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by orderId · status=1 usedUsages=0",
                test_lines=Lines_Step(
                    "E01-S03",
                    ["lpAssertHttpBusinessOk('E01-S03');", "lpAssertSearchPurchaseDetails('E01-S03', true);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 ePassId 查 MS 详情", "E01-S04", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E01-S04",
                    ["lpAssertHttpBusinessOk('E01-S04');", "lpAssertSearchPurchaseDetails('E01-S04', true);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("usage 订单列表（创建后可为空）", "E01-S05", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``PostOrdersEPassesList`` · 创建后 orders 可能为空",
                test_lines=Lines_Step(
                    "E01-S05",
                    [
                        "lpAssertHttpBusinessOk('E01-S05');",
                        "lpAssertOrderListPagination('E01-S05', true, true);",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge 订单（取消 MS 前）", "E01-I06", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter`` · 取消 MS 前",
                test_lines=Lines_Step("E01-I06", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E01-I06');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("module=1 列表不含 otherModule 数据（取消 MS 前）", "E01-I07", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 前",
                test_lines=Lines_Step(
                    "E01-I07",
                    ["lpAssertHttpBusinessOk('E01-I07');", "lpAssertNoOtherModuleInEpassList('E01-I07');"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单",
                step_prefix="E01-S06",
                order_id_var="purchaseOrderId",
                skip_to_request_name=e01_i08_name,
                description="``AssertHistoricalCancelOrderSuccess``",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e01_i08_name,
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter`` · 取消 MS 后",
                test_lines=Lines_Step("E01-I08", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E01-I08');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("module=1 列表不含 otherModule（取消 MS 后）", "E01-I09", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 后",
                test_lines=Lines_Step(
                    "E01-I09",
                    ["lpAssertHttpBusinessOk('E01-I09');", "lpAssertNoOtherModuleInEpassList('E01-I09');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后 usage 订单列表分页", "E01-S07", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertOrderListPaginationShape``",
                test_lines=Lines_Step(
                    "E01-S07",
                    [
                        "lpAssertHttpBusinessOk('E01-S07');",
                        "lpAssertOrderListPagination('E01-S07', true, true);",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后 search 显示 ePass Cancelled", "E01-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E01-S08",
                    [
                        "lpAssertHttpBusinessOk('E01-S08');",
                        "lpAssertSearchCancelledAfterPurchaseCancel('E01-S08');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Lounge_E2E_CreateMainChain`` · "
            "``RunHistoricalEpassCreateMainE2EScenario(catalog_label='lounge')``"
        ),
    )


def BuildPrebookingE2EFolder() -> JsonObject:
    e02_s08_name = PurposeName("取消后 usage 详情 status=3", "E02-S08", "POST", "/ePasses/details")
    return Folder(
        "E02 · tc-P0 预约",
        [
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("预约链前置：创建 lounge ePass", "E02-S01", "POST", "/lounges/ePasses"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["create"].path,
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="Prebooking 前置：创建 ePass",
                prerequest_lines=Prerequest_ResetForPrebooking(),
                test_lines=Lines_Step(
                    "E02-S01",
                    ["lpAssertHttpBusinessOk('E02-S01');", "lpAssertCreateCoreFields('E02-S01');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("可用性查询并获取 prebookingToken（有 ePassId）", "E02-S02", "POST", "/prebookings/availability"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["availability"].path,
                body=AvailabilityBody(with_epass=True, add_days=PREBOOKING_ADD_DAYS_START),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingToken`` · 运行日+10天 T10:00",
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(PREBOOKING_ADD_DAYS_START),
                test_lines=Lines_Step(
                    "E02-S02",
                    ["lpAssertHttpBusinessOk('E02-S02');", "lpAssertAvailabilitySuccess('E02-S02');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("lounge 预约下单成功（usage 单）", "E02-S03", "POST", "/lounges/ePasses/prebooking"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["prebooking"].path,
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "ePassId": "{{ePassId}}",
                        "extra": LoungePrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalPrebookingOrderSuccessForCatalog``（lounge 经典链）",
                test_lines=Lines_Step(
                    "E02-S03",
                    [
                        "lpAssertHttpBusinessOk('E02-S03');",
                        "lpAssertPrebookingOrderSuccess('E02-S03');",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("预约后 module=1 列表含 usage 单", "E02-S04", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="预约成功后 module=1 订单列表",
                test_lines=Lines_Step("E02-S04", ["lpAssertUsageOrderInListActive('E02-S04');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge usage 单", "E02-S05", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E02-S05", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E02-S05');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("usage 订单详情（取消前）", "E02-S06", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E02-S06",
                    ["lpAssertHttpBusinessOk('E02-S06');", "lpAssertUsageDetailsCore('E02-S06', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 usage 预订单",
                step_prefix="E02-S07",
                order_id_var="usageOrderId",
                skip_to_request_name=e02_s08_name,
                description="``CancelHistoricalUsageOrderAndVerify`` · prebooking usage 单取消",
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e02_s08_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E02-S08",
                    ["lpAssertHttpBusinessOk('E02-S08');", "lpAssertUsageDetailsCore('E02-S08', true);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后列表含 usage 单且 status=3", "E02-S09", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E02-S09",
                    [
                        "lpAssertHttpBusinessOk('E02-S09');",
                        "lpAssertOrderListPagination('E02-S09', false);",
                        "lpAssertUsageListContainsCancelled('E02-S09');",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消 usage 后 MS search 仍 Active", "E02-S10", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E02-S10",
                    ["lpAssertHttpBusinessOk('E02-S10');", "lpAssertSearchActiveAfterUsageCancel('E02-S10');"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（预约链收尾）",
                step_prefix="E02-S11",
                order_id_var="purchaseOrderId",
                skip_to_request_name=None,
                description="``CancelHistoricalPurchaseOrderAndVerify``",
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Lounge_E2E_PrebookingMainChain`` · "
            "``RunHistoricalEpassPrebookingMainE2EScenario(catalog_label='lounge')`` · "
            "运行前填 loungeResourceId（``DP_HIST_EPASS_LOUNGE_RESOURCE_ID``）；prebookingDate 由可用性步骤 Apifox 表达式同步"
        ),
    )


def BuildBundleE2EFolder() -> JsonObject:
    e03_s10_name = PurposeName("取消后 usage 详情 status=3", "E03-S10", "POST", "/ePasses/details")
    e03_s14_name = PurposeName("取消 MS 后 search 显示 Cancelled", "E03-S14", "POST", "/ePasses/search")
    return Folder(
        "E03 · tc-P0 Bundle",
        [
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 可用性（无 ePassId）取 token", "E03-S01", "POST", "/prebookings/availability"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["availability"].path,
                body=AvailabilityBody(with_epass=False, add_days=PREBOOKING_ADD_DAYS_START + 1),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingTokenWithoutEpass`` · 运行日+11天 T10:00",
                prerequest_lines=[
                    *Prerequest_ResetForBundle(),
                    *Prerequest_SyncPrebookingDateFromApifox(PREBOOKING_ADD_DAYS_START + 1),
                ],
                test_lines=Lines_Step(
                    "E03-S01",
                    ["lpAssertHttpBusinessOk('E03-S01');", "lpAssertAvailabilitySuccess('E03-S01');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 一步下单（创建 ePass+usage）", "E03-S02", "POST", "/lounges/ePasses/bundle"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["bundle"].path,
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "clientUserId": "{{$string.uuid}}",
                        "extra": LoungePrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalBundleOrderSuccess``（lounge 经典链）",
                test_lines=Lines_Step(
                    "E03-S02",
                    [
                        "lpAssertHttpBusinessOk('E03-S02');",
                        "lpAssertBundleOrderSuccess('E03-S02');",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 后 module=1 列表含 usage 单", "E03-S03", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="Bundle 成功后 module=1 订单列表",
                test_lines=Lines_Step("E03-S03", ["lpAssertUsageOrderInListActive('E03-S03');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge Bundle 单", "E03-S04", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E03-S04", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E03-S04');"]),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle usage 详情（取消前）", "E03-S05", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E03-S05",
                    ["lpAssertHttpBusinessOk('E03-S05');", "lpAssertUsageDetailsCore('E03-S05', false);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 后 users 列表含 ePass", "E03-S06", "POST", "/users/ePasses"),
                method="POST",
                url_path=EPASS_MAIN_CHAIN_SPECS["users"].path,
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E03-S06",
                    ["lpAssertHttpBusinessOk('E03-S06');", "lpAssertUserListContains('E03-S06');"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 ePassId（usedUsages=1）", "E03-S07", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后 search by ePassId",
                test_lines=Lines_Step(
                    "E03-S07",
                    ["lpAssertHttpBusinessOk('E03-S07');", "lpAssertSearchPurchaseDetails('E03-S07', true, false, 2, 1);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 purchaseOrderId（Bundle 后）", "E03-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后二次 search by orderId",
                test_lines=Lines_Step(
                    "E03-S08",
                    ["lpAssertHttpBusinessOk('E03-S08');", "lpAssertSearchPurchaseDetails('E03-S08', true, false, 2, 1);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 Bundle usage 单",
                step_prefix="E03-S09",
                order_id_var="usageOrderId",
                skip_to_request_name=e03_s10_name,
                description="Bundle usage 单取消 · ``PatchCancelOrderWithRetry``",
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e03_s10_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E03-S10",
                    ["lpAssertHttpBusinessOk('E03-S10');", "lpAssertUsageDetailsCore('E03-S10', true);"],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后列表含 usage 单", "E03-S11", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E03-S11",
                    [
                        "lpAssertHttpBusinessOk('E03-S11');",
                        "lpAssertOrderListPagination('E03-S11', false);",
                        "lpAssertUsageListContainsCancelled('E03-S11');",
                    ],
                ),
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消 usage 后 search 仍 Active", "E03-S12", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E03-S12",
                    ["lpAssertHttpBusinessOk('E03-S12');", "lpAssertSearchActiveAfterUsageCancel('E03-S12', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（Bundle 收尾）",
                step_prefix="E03-S13",
                order_id_var="purchaseOrderId",
                skip_to_request_name=e03_s14_name,
                description="``CancelHistoricalPurchaseOrderAndVerify``",
            ),
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e03_s14_name,
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E03-S14",
                    [
                        "lpAssertHttpBusinessOk('E03-S14');",
                        "lpAssertSearchCancelledAfterPurchaseCancel('E03-S14', false);",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Lounge_E2E_BundleMainChain`` · "
            "``RunHistoricalEpassBundleMainE2EScenario(catalog_label='lounge')`` · "
            "运行前填 loungeResourceId（``DP_HIST_EPASS_LOUNGE_RESOURCE_ID``）；prebookingDate 由可用性步骤 Apifox 表达式同步"
        ),
    )


def _RewriteApiVersionInCollection(collection: JsonObject, api_version: str) -> JsonObject:
    """将集合 JSON 内 ``/v2/`` 路径前缀替换为 ``/{api_version}/``（如 v1）。"""
    source_prefix = "/v2/"
    target_prefix = f"/{api_version.strip('/')}/"

    def rewrite(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(source_prefix, target_prefix)
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    return rewrite(collection)


def BuildCollection(*, api_version: str = DEFAULT_API_VERSION) -> JsonObject:
    prev_assert_epass_status = SetLoungeAssertEpassStatus(
        api_version == DEFAULT_API_VERSION
    )
    try:
        return _BuildCollectionBody(api_version=api_version)
    finally:
        SetLoungeAssertEpassStatus(prev_assert_epass_status)


def _BuildCollectionBody(*, api_version: str) -> JsonObject:
    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            LoungeRequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("获取 ePass 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken。",
                save_token=True,
                test_lines=Lines_Auth(),
                prerequest_lines=Lines_EnsureEnvKeysIfMissing(
                    [(LOUNGE_RESOURCE_ID_VAR, DEFAULT_LOUNGE_RESOURCE_ID)]
                ),
            ),
        ],
        description="先执行本文件夹。",
    )

    info: JsonObject = {
        "name": "lounge ePass · P0 E2E 核心",
        "description": (
            "由 GeneratePostmanCollectionLoungeEpass.py 生成。\n\n"
            "**三条 P0 E2E 核心链路**（对齐 ``RunHistoricalEpass*MainE2EScenario(catalog_label='lounge')``）：\n"
            "- E01 创建验证链（含 module=1 / otherModule=11 双向隔离）\n"
            "- E02 预约验证链（经典可用性 · module=1）\n"
            "- E03 Bundle 一步下单\n\n"
            "每个 HTTP 步骤含多条 pm.test 字段级断言；请求名格式 **【目的】| 步骤号 | METHOD 路径**（与 Local Offer P1 pytest-sync 一致）。\n\n"
            "**必填变量**：ProgramID、clientId、secret；E02/E03 另填 loungeResourceId。\n"
            f"**lounge 网点**：``{LOUNGE_RESOURCE_ID_VAR}`` 对齐 ``{ENV_LOUNGE_RESOURCE_ID}``"
            f"（默认 {DEFAULT_LOUNGE_RESOURCE_ID}）。\n"
            "**品类 module**：epassModule=1、otherModule=11（断言动态读取）。\n"
            "**经典可用性**：``POST /v2/resources/prebookings/availability``（无 optionId）；"
            "``prebookingDate``：E02=运行日+10天 T10:00，E03=+11天；前置每次重算。\n"
            "**预约 extra**：含 ``prebookingRequiredInfo``（对齐 ``PostHistoricalEpassPrebooking`` 经典链）。"
            "订单详情 ``extra.bookingCounts`` 等于可用性 ``adultCount+childCount``（默认 1+0=1；取消后不变）。\n"
            "**创建 availableUsages**：默认 2（对齐 pytest ``CreateHistoricalEpass``）。\n"
            "取消订单：线性 PATCH 最多 3 次（无 WAIT 间隔）；成功则向前 skip 剩余重试步骤；"
            "对齐 ``PatchCancelOrderWithRetry`` 可重试错误 ``Order cancellation failed``。\n"
            "**Apifox 兼容**：lp helpers 注入各 HTTP 步骤 test（及含 lp 的 pre-request）。\n"
            "**可选**：x-version（canary）。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("epassModule", str(EPASS_MODULE_DEFAULT)),
        CollectionVariable("otherModule", str(OTHER_MODULE_DEFAULT)),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable(LOUNGE_RESOURCE_ID_VAR, DEFAULT_LOUNGE_RESOURCE_ID),
        CollectionVariable("loungeCancelMaxAttempts", str(GENERATED_CANCEL_ATTEMPTS)),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("prebookingToken", ""),
    ]

    collection: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [
            auth_folder,
            BuildCreateE2EFolder(),
            BuildPrebookingE2EFolder(),
            BuildBundleE2EFolder(),
        ],
    }

    if api_version != DEFAULT_API_VERSION:
        collection = _RewriteApiVersionInCollection(collection, api_version)
        info_obj = collection["info"]
        info_obj["name"] = f"lounge ePass · P0 E2E 核心 · API {api_version}"
        base_desc = str(info_obj.get("description", ""))
        info_obj["description"] = (
            f"由 GeneratePostmanCollectionLoungeEpassV1.py 生成（网关路径 ``/{api_version}/``）。\n"
            "断言与 v2 基本一致，但 **v1 search/create 响应无 ``extra.ePassStatus``**，集合内已省略相关 pm.test。\n"
            "``category``：MS 创建/search=3，usage 单=2。\n\n"
            + base_desc.replace("由 GeneratePostmanCollectionLoungeEpass.py 生成。\n\n", "")
        )
        variables_list = collection.get("variable", [])
        if isinstance(variables_list, list):
            variables_list.append(CollectionVariable("apiVersion", api_version))

    return collection


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection(api_version=DEFAULT_API_VERSION))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
