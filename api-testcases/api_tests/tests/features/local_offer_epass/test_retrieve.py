"""
RetrieveEpassDetails / RetrieveUserEpassesList / Usage Details / Order List 模块。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md``
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from scenarios.local_offer_epass_scenarios import RunLocalOfferEpassCreateMainE2EScenario
from services.local_offer_epass_service import (
    AssertBusinessFailure,
    AssertEpassSearchDetailsCoreFields,
    AssertLocalOfferNotReturnedWithEsimModuleFilter,
    AssertLocalOfferPrebookingOrderSuccess,
    AssertOrderListPaginationShape,
    AssertSearchDetailsExtendedFields,
    BuildFakeOrderId,
    CreateLocalOfferEpass,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulLocalOfferUsageOrder,
    ESIM_MODULE_INT,
    LOCAL_OFFER_MODULE_INT,
    LocalOfferEpassPrebookingResult,
    PostOrdersEPassesList,
    PostOrdersEPassesSearch,
    PostOrdersEPassesUsageDetails,
    PostOrdersLocalOffersEPassesPrebookingWithToken,
    RequestPrebookingToken,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


def _CreateLocalOfferUsageOrderMinimal(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    target_label: str = "redemption_code",
) -> LocalOfferEpassPrebookingResult:
    """创建 Local Offer ePass 并完成预约（不含 options 对拍，供 module 隔离负向用）。"""
    target = ResolvePrebookingTargetByLabel(target_label)
    created = CreateLocalOfferEpass(token, steps)
    pb_token, pb_date = RequestPrebookingToken(
        token,
        steps,
        e_pass_id=created.EPassId,
        target=target,
    )
    kw = _StepKw(steps, f"预约下单（module8 前置 · {target.Label}）")
    resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
        token,
        created.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        resp_book,
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        expected_voucher_type=target.ExpectedVoucherType,
        context=f"module8-setup-{target.Label}",
    )
    return LocalOfferEpassPrebookingResult(
        ClientUserId=created.ClientUserId,
        EPassId=created.EPassId,
        PurchaseOrderId=created.PurchaseOrderId,
        UsageOrderId=usage_order_id,
        PrebookingToken=pb_token,
        ResourceId=target.ResourceId,
        OptionId=target.OptionId,
        PrebookingDate=pb_date,
    )


@allure.feature("Local Offer ePass")
@allure.story("RetrieveEpassDetails · orderId 查询扩展字段")
def test_LocalOfferEpass_SearchDetails_ByOrderId_ExtendedFields(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 通过 orderId 查询购买单详情，校验 module/category/extra 等。"""
    created = RunLocalOfferEpassCreateMainE2EScenario(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "购买单详情扩展字段（orderId）")
    resp = PostOrdersEPassesSearch(
        EpassToken,
        order_id=created.PurchaseOrderId,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertSearchDetailsExtendedFields(
        resp,
        expected_client_user_id=created.ClientUserId,
        context="by-orderId-extended",
    )


@allure.feature("Local Offer ePass")
@allure.story("RetrieveEpassDetails · ePassId 查询扩展字段")
def test_LocalOfferEpass_SearchDetails_ByEPassId_ExtendedFields(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 通过 ePassId 查询购买单详情。"""
    created = RunLocalOfferEpassCreateMainE2EScenario(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "购买单详情扩展字段（ePassId）")
    resp = PostOrdersEPassesSearch(
        EpassToken,
        e_pass_id=created.EPassId,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertSearchDetailsExtendedFields(
        resp,
        expected_client_user_id=created.ClientUserId,
        context="by-ePassId-extended",
    )


@allure.feature("Local Offer ePass")
@allure.story("RetrieveEpassDetails · 负向订单不存在")
def test_LocalOfferEpass_SearchDetails_OrderNotFound(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 不存在的 orderId 应 500.080.004。"""
    fake_id = BuildFakeOrderId()
    kw = _StepKw(ScenarioSteps, "查询不存在 orderId")
    resp = PostOrdersEPassesSearch(
        EpassToken,
        order_id=fake_id,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertBusinessFailure(
        resp,
        expected_err_codes=("500.080.004", "500.000.004"),
        context="search-order-not-found",
    )


@allure.feature("Local Offer ePass")
@allure.story("Retrieve E-pass Usage Order Details · 负向订单不存在")
def test_LocalOfferEpass_UsageDetails_OrderNotFound(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 不存在的 usage orderId 应 500.110.004。"""
    fake_id = BuildFakeOrderId()
    kw = _StepKw(ScenarioSteps, "查询不存在 usage orderId")
    resp = PostOrdersEPassesUsageDetails(
        EpassToken,
        fake_id,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertBusinessFailure(
        resp,
        expected_err_codes=("500.110.004", "500.000.004"),
        context="usage-order-not-found",
    )


@allure.feature("Local Offer ePass")
@allure.story("Retrieve E-pass Order List · 创建后空列表可接受")
def test_LocalOfferEpass_OrderList_AfterCreateOnly(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 仅创建 ePass 后列表结构合法（orders 可为空）。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "创建后 usage 订单列表")
    resp = PostOrdersEPassesList(
        EpassToken,
        created.EPassId,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertOrderListPaginationShape(resp, context="create-only")
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="order-list-create-only",
    )


@allure.feature("Local Offer ePass")
@allure.story("Retrieve E-pass Order List · module=8 不返回 Local Offer 数据")
def test_LocalOfferEpass_OrderList_Module8_NoLocalOfferData(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Local Offer usage 订单存在时，``POST /v2/orders/ePasses`` 传 ``module=8`` 不应返回该订单。"""
    result = _CreateLocalOfferUsageOrderMinimal(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "ePass usage 订单列表（module=8）")
    resp = PostOrdersEPassesList(
        EpassToken,
        result.EPassId,
        module=ESIM_MODULE_INT,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertLocalOfferNotReturnedWithEsimModuleFilter(
        resp,
        expected_order_id=result.UsageOrderId,
        context="order-list-module8",
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=result.UsageOrderId,
        e_pass_id=result.EPassId,
        purchase_order_id=result.PurchaseOrderId,
        client_user_id=result.ClientUserId,
        resource_id=result.ResourceId,
        option_id=result.OptionId,
        context="order-list-module8-cancel",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=result.EPassId,
        purchase_order_id=result.PurchaseOrderId,
        context="order-list-module8-purchase",
    )


@allure.feature("Local Offer ePass")
@allure.story("RetrieveEpassDetails · search 仅 ePassId")
def test_LocalOfferEpass_SearchDetails_ByEPassId_Only(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ``POST /v2/orders/ePasses/search`` 仅 ``ePassId`` 可查购买单详情（接口无 ``module`` 入参）。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "购买单详情（仅 ePassId）")
    resp = PostOrdersEPassesSearch(
        EpassToken,
        e_pass_id=created.EPassId,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertEpassSearchDetailsCoreFields(
        resp,
        expected_order_id=created.PurchaseOrderId,
        expected_e_pass_id=created.EPassId,
        context="search-by-ePassId-only",
        assert_module_11=False,
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="search-ePassId-only",
    )


@allure.feature("Local Offer ePass")
@allure.story("Retrieve E-pass Usage Order Details · module=8 不返回 Local Offer 数据")
def test_LocalOfferEpass_UsageDetails_Module8_NoData(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Local Offer usage 订单存在时，``POST /v2/orders/ePasses/details`` 传 ``module=8`` 不应返回详情。"""
    result = _CreateLocalOfferUsageOrderMinimal(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "usage 订单详情（module=8）")
    resp = PostOrdersEPassesUsageDetails(
        EpassToken,
        result.UsageOrderId,
        module=ESIM_MODULE_INT,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertLocalOfferNotReturnedWithEsimModuleFilter(
        resp,
        expected_order_id=result.UsageOrderId,
        expected_e_pass_id=result.EPassId,
        context="usage-details-module8",
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=result.UsageOrderId,
        e_pass_id=result.EPassId,
        purchase_order_id=result.PurchaseOrderId,
        client_user_id=result.ClientUserId,
        resource_id=result.ResourceId,
        option_id=result.OptionId,
        context="usage-details-module8-cancel",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=result.EPassId,
        purchase_order_id=result.PurchaseOrderId,
        context="usage-details-module8-purchase",
    )
