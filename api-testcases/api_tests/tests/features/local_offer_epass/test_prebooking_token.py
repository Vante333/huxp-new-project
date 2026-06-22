"""
PrebookingToken 场景 — 无/有 ePassId 绑定、一致性、invalid token。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` ·
未指定/指定 ePassId 的 prebookingToken、invalid prebookingToken 校验。
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from services.local_offer_epass_service import (
    AssertLocalOfferPrebookingOrderSuccess,
    FinalizeCreatedLocalOfferEpassResults,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulLocalOfferUsageOrder,
    AssertPrebookingStepRejected,
    BuildAvailabilityBody,
    CreateLocalOfferEpass,
    ESIM_MODULE_INT,
    FetchEsimFirstOptionIdOrSkip,
    FetchModuleResourceHintsOrSkip,
    PickAlternatePrebookingTarget,
    PostOrdersLocalOffersEPassesPrebookingWithToken,
    PostPrebookingAvailability,
    RequestPrebookingToken,
    RequestPrebookingTokenWithoutEpass,
    ResolveMembershipIdForAvailabilityOrSkip,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


_TOKEN_CONSISTENCY_REJECT_ERR_CODES = (
    "500.110.028",
    "500.110.027",
    "500.110.019",
    "500.110.031",
    "500.020.009",
)


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · 未指定 ePassId/memberId")
def test_LocalOfferEpass_Prebooking_WithoutEpassIdToken_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 可用性不传 ePassId 取 token，预约时传入 ePassId 应成功。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingTokenWithoutEpass(EpassToken, ScenarioSteps, target=target)
    kw = _StepKw(ScenarioSteps, "无 ePassId token + 指定 ePassId 预约")
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
        context="no-epass-id-token",
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
        context="no-epass-id-token-cancel",
    )


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · 指定 ePassId 一致性")
def test_LocalOfferEpass_Prebooking_EpassIdMatch_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 容量查询与预约传入相同 ePassId 应成功。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        target=target,
    )
    kw = _StepKw(ScenarioSteps, "ePassId 一致预约")
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
        context="epass-id-match",
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
        context="epass-id-match-cancel",
    )


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · 指定 ePassId 一致性")
def test_LocalOfferEpass_Prebooking_EpassIdMismatch_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p2: token 绑定 ePassId A，预约传入 ePassId B 应失败（500.110.028）。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    epass_a = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    epass_b = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=epass_a.EPassId,
        target=target,
    )
    kw = _StepKw(ScenarioSteps, "ePassId 不一致预约")
    resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        epass_b.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp,
        expected_err_codes=_TOKEN_CONSISTENCY_REJECT_ERR_CODES + ("500.110.020",),
        context="epass-id-mismatch",
    )
    FinalizeCreatedLocalOfferEpassResults(
        EpassToken,
        ScenarioSteps,
        epass_a,
        epass_b,
        context_prefix="epass-id-mismatch",
    )


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · tc-p2 与请求主体一致性")
def test_LocalOfferEpass_Prebooking_TokenResourceMismatch_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p2: token 由 resourceA 生成，下单 ePass 仅含 resourceB 权益上下文应失败。"""
    target_a = ResolvePrebookingTargetByLabel("redemption_code")
    try:
        target_b = PickAlternatePrebookingTarget(exclude_resource_ids=[target_a.ResourceId])
    except LookupError as exc:
        pytest.skip(str(exc))
    epass_for_token = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=epass_for_token.EPassId,
        target=target_a,
    )
    epass_b_ctx = CreateLocalOfferEpass(
        EpassToken,
        ScenarioSteps,
        allowed_resources={"resourceIds": [target_b.ResourceId]},
    )
    kw = _StepKw(ScenarioSteps, "resourceA token + resourceB 权益 ePass 预约")
    resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        epass_b_ctx.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp,
        expected_err_codes=_TOKEN_CONSISTENCY_REJECT_ERR_CODES,
        context="token-resource-mismatch",
    )
    FinalizeCreatedLocalOfferEpassResults(
        EpassToken,
        ScenarioSteps,
        epass_for_token,
        epass_b_ctx,
        context_prefix="token-resource-mismatch",
    )


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · invalid · membershipId token")
def test_LocalOfferEpass_Prebooking_MembershipIdToken_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ``POST /v2/memberships`` 取 membershipId → 可用性仅绑 membershipId → ePass 预约应失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    membership_id = ResolveMembershipIdForAvailabilityOrSkip(
        EpassToken,
        ScenarioSteps,
        created=created,
    )
    body = BuildAvailabilityBody(
        membership_id=membership_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
    )
    resp_avail = PostPrebookingAvailability(
        EpassToken,
        ScenarioSteps,
        body=body,
        brief=f"可用性 membershipId={membership_id[:6]}…",
    )
    _st, env, _ = ParseResponseEnvelope(resp_avail)
    if env is not None and env.get("code") == -1:
        AssertPrebookingStepRejected(
            resp_avail,
            expected_err_codes=("500.110.021", "500.020.009", "500.020.007", "500.110.019"),
            context="membershipId-availability-fail",
        )
        FinalizeCreatedLocalOfferPurchaseOnly(
            EpassToken,
            ScenarioSteps,
            e_pass_id=created.EPassId,
            purchase_order_id=created.PurchaseOrderId,
            context="membershipId-availability-fail",
        )
        return
    from services.local_offer_epass_service import AssertPrebookingAvailabilitySuccess

    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context="membershipId-token")
    kw = _StepKw(ScenarioSteps, "membershipId token 预约 ePass")
    resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_book,
        expected_err_codes=("500.110.028", "500.110.027", "500.110.019"),
        context="membershipId-token-on-epass-prebooking",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="membershipId-token-on-epass-prebooking",
    )


@allure.feature("Local Offer ePass")
@allure.story("PrebookingToken · invalid · esim token")
def test_LocalOfferEpass_Prebooking_EsimAvailabilityToken_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p2: esim module≠11 网点 token 下 local offer 预订单应失败（Invalid prebookingToken）。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    esim_hints = FetchModuleResourceHintsOrSkip(EpassToken, module=ESIM_MODULE_INT, steps=ScenarioSteps)
    esim_resource_id = esim_hints.ResourceIds[0]
    option_id = FetchEsimFirstOptionIdOrSkip(
        EpassToken,
        esim_resource_id,
        steps=ScenarioSteps,
    )
    body = BuildAvailabilityBody(
        e_pass_id=created.EPassId,
        resource_id=esim_resource_id,
        option_id=option_id,
        module=ESIM_MODULE_INT,
    )
    resp_avail = PostPrebookingAvailability(
        EpassToken,
        ScenarioSteps,
        body=body,
        brief="esim 资源可用性 module=8",
    )
    _st, env, _ = ParseResponseEnvelope(resp_avail)
    if env is not None and env.get("code") == -1:
        AssertPrebookingStepRejected(
            resp_avail,
            expected_err_codes=("500.020.009", "500.020.007", "500.110.019"),
            context="esim-availability-on-local-offer",
        )
        FinalizeCreatedLocalOfferPurchaseOnly(
            EpassToken,
            ScenarioSteps,
            e_pass_id=created.EPassId,
            purchase_order_id=created.PurchaseOrderId,
            context="esim-availability-on-local-offer",
        )
        return
    from services.local_offer_epass_service import AssertPrebookingAvailabilitySuccess

    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context="esim-token")
    kw = _StepKw(ScenarioSteps, "esim token local offer 预约")
    resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        created.EPassId,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_book,
        expected_err_codes=("500.110.028", "500.110.019", "500.020.009"),
        context="esim-token-prebooking",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="esim-token-prebooking",
    )
