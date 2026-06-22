"""
Create E-pass with Prebooking Order (Bundle) 模块。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · Bundle

主链路 E2E 见 ``tests/features/test_local_offer_epass.py``。
Token 一致性场景见 ``test_bundle_token.py``。
"""
from __future__ import annotations

import uuid
from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from services.local_offer_epass_service import (
    AssertBundleOrderSuccess,
    AssertBusinessFailure,
    AssertPrebookingStepRejected,
    LOCAL_OFFER_MODULE_INT,
    LOCAL_OFFER_PATH_MODULE,
    PostOrdersLocalOffersEPassesBundle,
    RequestPrebookingTokenWithoutEpass,
    ResolvePrebookingTargetByLabel,
    ResolvePrebookingTargetForVoucherRedemptionScenario,
    FinalizeSuccessfulBundleOrder,
    _HttpStepKw,
)

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


_BUNDLE_REUSE_TOKEN_REJECT_ERR_CODES = (
    "500.110.028",
    "500.110.027",
)


@allure.feature("Local Offer ePass")
@allure.story("Bundle · 负向 invalid token")
def test_LocalOfferEpass_Bundle_InvalidTokenRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Bundle 无效 prebookingToken 应 500.110.028。"""
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, "Bundle 无效 token")
    resp = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid,
        "00000000-0000-0000-0000-000000000000",
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertBusinessFailure(resp, expected_err_code="500.110.028", context="bundle-invalid-token")


@allure.feature("Local Offer ePass")
@allure.story("Bundle · 负向 reuse token")
def test_LocalOfferEpass_Bundle_ReuseTokenRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 已消费 prebookingToken 再次 Bundle 应失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    pb_token, _ = RequestPrebookingTokenWithoutEpass(EpassToken, ScenarioSteps, target=target)
    cid_first = str(uuid.uuid4())
    kw_first = _StepKw(ScenarioSteps, "首次 Bundle 下单")
    resp_first = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid_first,
        pb_token,
        step_code=kw_first["step_code"],
        step_title=kw_first["step_title"],
    )
    e_pass_id, usage_order_id = AssertBundleOrderSuccess(
        resp_first,
        expected_client_user_id=cid_first,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context="first-bundle",
    )
    FinalizeSuccessfulBundleOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        client_user_id=cid_first,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context="first-bundle-cancel",
    )
    cid_second = str(uuid.uuid4())
    kw_second = _StepKw(ScenarioSteps, "复用 prebookingToken 再次 Bundle")
    resp_second = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid_second,
        pb_token,
        step_code=kw_second["step_code"],
        step_title=kw_second["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_second,
        expected_err_codes=_BUNDLE_REUSE_TOKEN_REJECT_ERR_CODES,
        context="reuse-prebooking-token-bundle",
    )


@allure.feature("Local Offer ePass")
@allure.story("Bundle · voucherType 与 redemptionUrl")
def test_LocalOfferEpass_Bundle_VoucherTypeAndRedemptionUrl(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1：资源链造数后 Bundle 一步下单 — voucherType=1 且 redemptionUrl 有值。

    已移除自动化：redemptionUrl 无；voucherType=4 + redemptionUrl 有。

    造数顺序（与 prebooking 一致）：
    ``GET /v2/resources?module=11`` →
    ``GET /v2/resources/localOffers/{resourceId}/options`` →
    ``GET /v2/resources/localOffers/{resourceId}/options/{optionId}`` →
    ``POST /v2/resources/options/prebookings/availability``（无 ePassId）→
    ``POST /v2/orders/localOffers/ePasses/bundle``
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
    pb_token, _ = RequestPrebookingTokenWithoutEpass(EpassToken, ScenarioSteps, target=target)
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, f"Bundle 下单（voucherType={voucher_type} · redemptionUrl）")
    resp = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    e_pass_id, usage_order_id = AssertBundleOrderSuccess(
        resp,
        expected_client_user_id=cid,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        expected_voucher_type=target.ExpectedVoucherType,
        expect_redemption_url_present=target.ExpectRedemptionUrlPresent,
        context=f"voucherType{voucher_type}-redemptionUrl-{expect_redemption_url}",
    )
    FinalizeSuccessfulBundleOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        client_user_id=cid,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context=f"bundle-voucherType{voucher_type}-cancel",
    )


@allure.feature("Local Offer ePass")
@allure.story("Bundle · 补偿链路")
@pytest.mark.manual
def test_LocalOfferEpass_Bundle_CompensationAfterPrebookingFailure_Manual() -> None:
    """tc-p2: Bundle 预约失败补偿注销 ePass — 需 SaaS/轮询，默认 manual 不跑。"""
    pytest.skip("需人工构造预约失败并轮询会籍/订单状态，见用例 md Bundle补偿链路。")
