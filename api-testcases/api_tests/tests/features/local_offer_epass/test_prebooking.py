"""
Create E-pass Prebooking Order 模块 — 预约下单与负向。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · Create E-pass Prebooking Order

主链路 E2E 见 ``tests/features/test_local_offer_epass.py``。
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from services.local_offer_epass_service import (
    AssertBusinessFailure,
    AssertLocalOfferPrebookingOrderSuccess,
    CreateLocalOfferEpass,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulLocalOfferUsageOrder,
    PostOrdersLocalOffersEPassesPrebookingWithToken,
    RequestPrebookingToken,
    ResolvePrebookingTargetByLabel,
    ResolvePrebookingTargetForVoucherRedemptionScenario,
    _HttpStepKw,
)

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


@allure.feature("Local Offer ePass")
@allure.story("Create E-pass Prebooking Order · 负向 invalid token")
def test_LocalOfferEpass_Prebooking_InvalidTokenRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 无效 prebookingToken 应 500.110.028。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    kw = _StepKw(ScenarioSteps, "无效 prebookingToken 预约")
    resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        "00000000-0000-0000-0000-000000000000",
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertBusinessFailure(resp, expected_err_code="500.110.028", context="invalid-prebooking-token")
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="invalid-prebooking-token",
    )


@allure.feature("Local Offer ePass")
@allure.story("Create E-pass Prebooking Order · 负向 reuse token")
def test_LocalOfferEpass_Prebooking_ReuseTokenRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 已消费 prebookingToken 再次下单应失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        target=target,
    )
    kw_first = _StepKw(ScenarioSteps, "首次预约下单")
    resp_first = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        pb_token,
        step_code=kw_first["step_code"],
        step_title=kw_first["step_title"],
    )
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        resp_first,
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context="first-booking",
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        client_user_id=created.ClientUserId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context="first-booking-cancel",
    )
    kw_second = _StepKw(ScenarioSteps, "复用 prebookingToken 再次预约")
    resp_second = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        pb_token,
        step_code=kw_second["step_code"],
        step_title=kw_second["step_title"],
    )
    AssertBusinessFailure(
        resp_second,
        expected_err_codes=("500.110.028", "500.110.027"),
        context="reuse-prebooking-token",
    )


@allure.feature("Local Offer ePass")
@allure.story("Create E-pass Prebooking Order · voucherType 与 redemptionUrl")
def test_LocalOfferEpass_Prebooking_VoucherTypeAndRedemptionUrl(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1：Create E-pass Prebooking Order — voucherType=1 且 redemptionUrl 有值。

    已移除自动化：redemptionUrl 无；voucherType=4 + redemptionUrl 有（沙箱数据难稳定造数）。

    造数顺序（与用例步骤一致）：
    ``GET /v2/resources?module=11`` →
    ``GET /v2/resources/localOffers/{resourceId}/options`` →
    ``GET /v2/resources/localOffers/{resourceId}/options/{optionId}`` →
    ``POST /v2/resources/options/prebookings/availability`` →
    ``POST /v2/orders/localOffers/ePasses/prebooking``
    """
    voucher_type = 1
    expect_redemption_url = True
    target = ResolvePrebookingTargetForVoucherRedemptionScenario(
        EpassToken,
        ScenarioSteps,
        voucher_type=voucher_type,
        expect_redemption_url_present=expect_redemption_url,
    )
    allure.dynamic.parameter("resourceId", target.ResourceId)
    allure.dynamic.parameter("optionId", target.OptionId)
    allure.dynamic.parameter("voucherTypeExpected", target.ExpectedVoucherType)
    allure.dynamic.parameter("redemptionUrlExpected", expect_redemption_url)
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        target=target,
    )
    kw = _StepKw(ScenarioSteps, f"预约下单（voucherType={voucher_type} · redemptionUrl）")
    resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        resp,
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        expected_voucher_type=target.ExpectedVoucherType,
        expect_redemption_url_present=target.ExpectRedemptionUrlPresent,
        context=f"voucherType{voucher_type}-redemptionUrl-{expect_redemption_url}",
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        client_user_id=created.ClientUserId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context=f"voucherType{voucher_type}-cancel",
    )
