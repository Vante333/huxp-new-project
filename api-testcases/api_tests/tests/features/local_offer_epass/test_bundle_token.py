"""
Bundle · PrebookingToken 场景 — 无/有 ePassId 绑定、membershipId/esim token 负向。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` ·
Bundle · invalid prebookingToken 校验 / 指定 ePassId 的 prebookingToken。

与 ``test_prebooking_token.py`` 同构，调用 ``POST .../ePasses/bundle`` 而非 prebooking。
"""
from __future__ import annotations

import uuid
from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from services.local_offer_epass_service import (
    AssertBundleOrderSuccess,
    AssertPrebookingAvailabilitySuccess,
    AssertPrebookingStepRejected,
    BuildAvailabilityBody,
    CreateLocalOfferEpass,
    ESIM_MODULE_INT,
    FetchEsimFirstOptionIdOrSkip,
    FetchModuleResourceHintsOrSkip,
    LOCAL_OFFER_MODULE_INT,
    LOCAL_OFFER_PATH_MODULE,
    PostOrdersLocalOffersEPassesBundle,
    PostPrebookingAvailability,
    RequestPrebookingToken,
    RequestPrebookingTokenWithoutEpass,
    ResolveMembershipIdForAvailabilityOrSkip,
    ResolvePrebookingTargetByLabel,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulBundleOrder,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


_BUNDLE_TOKEN_REJECT_ERR_CODES = (
    "500.110.028",
    "500.110.027",
    "500.110.019",
    "500.110.031",
    "500.020.009",
)


@allure.feature("Local Offer ePass")
@allure.story("Bundle · PrebookingToken · 指定 ePassId 绑定应拒绝")
def test_LocalOfferEpass_Bundle_EpassIdBoundToken_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 容量查询绑定 ePassId 的 token 用于 Bundle（新建 ePass）应失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    pb_token, _ = RequestPrebookingToken(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        target=target,
    )
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, "ePassId 绑定 token + Bundle 新建 ePass")
    resp = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp,
        expected_err_codes=_BUNDLE_TOKEN_REJECT_ERR_CODES + ("500.110.020",),
        context="bundle-epass-id-bound-token",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="bundle-epass-id-bound-token",
    )


@allure.feature("Local Offer ePass")
@allure.story("Bundle · PrebookingToken · invalid · membershipId token")
def test_LocalOfferEpass_Bundle_MembershipIdToken_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: membershipId 可用性 token 下 Bundle 应失败。"""
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
            context="bundle-membershipId-availability-fail",
        )
        return
    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context="membershipId-token")
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, "membershipId token Bundle")
    resp_bundle = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_bundle,
        expected_err_codes=("500.110.028", "500.110.027", "500.110.019"),
        context="membershipId-token-on-bundle",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="bundle-membershipId-token-on-bundle",
    )


@allure.feature("Local Offer ePass")
@allure.story("Bundle · PrebookingToken · invalid · esim token")
def test_LocalOfferEpass_Bundle_EsimAvailabilityToken_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: esim module≠11 网点 token 下 Bundle 应失败。"""
    esim_hints = FetchModuleResourceHintsOrSkip(EpassToken, module=ESIM_MODULE_INT, steps=ScenarioSteps)
    esim_resource_id = esim_hints.ResourceIds[0]
    option_id = FetchEsimFirstOptionIdOrSkip(
        EpassToken,
        esim_resource_id,
        steps=ScenarioSteps,
    )
    body = BuildAvailabilityBody(
        resource_id=esim_resource_id,
        option_id=option_id,
        module=ESIM_MODULE_INT,
    )
    resp_avail = PostPrebookingAvailability(
        EpassToken,
        ScenarioSteps,
        body=body,
        brief="esim 资源可用性 module=8（无 ePassId）",
    )
    _st, env, _ = ParseResponseEnvelope(resp_avail)
    if env is not None and env.get("code") == -1:
        AssertPrebookingStepRejected(
            resp_avail,
            expected_err_codes=("500.020.009", "500.020.007", "500.110.019"),
            context="esim-availability-on-local-offer",
        )
        return
    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context="esim-token")
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, "esim token Bundle")
    resp_bundle = PostOrdersLocalOffersEPassesBundle(
        EpassToken,
        cid,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_bundle,
        expected_err_codes=("500.110.028", "500.110.019", "500.020.009"),
        context="esim-token-bundle",
    )


@allure.feature("Local Offer ePass")
@allure.story("Bundle · PrebookingToken · 无 ePassId token 成功")
def test_LocalOfferEpass_Bundle_WithoutEpassIdToken_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 可用性不传 ePassId 取 token，Bundle 应成功（与主链路一致）。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    pb_token, _ = RequestPrebookingTokenWithoutEpass(EpassToken, ScenarioSteps, target=target)
    cid = str(uuid.uuid4())
    kw = _StepKw(ScenarioSteps, "无 ePassId token Bundle")
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
        context="bundle-no-epass-id-token",
    )
    FinalizeSuccessfulBundleOrder(
        EpassToken,
        ScenarioSteps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        client_user_id=cid,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context="bundle-no-epass-id-token-cancel",
    )
