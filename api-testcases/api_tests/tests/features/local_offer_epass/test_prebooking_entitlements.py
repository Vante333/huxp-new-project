"""
Prebooking 权益校验 — 可用点数、预约人数与 remaining usages。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · 权益校验。
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from services.local_offer_epass_service import (
    AssertLocalOfferPrebookingOrderSuccess,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulLocalOfferUsageOrder,
    RegisterPendingLocalOfferEPassId,
    RegisterPendingLocalOfferOrder,
    AssertPrebookingAvailabilitySuccess,
    AssertPrebookingStepRejected,
    BuildAvailabilityBody,
    BuildLocalOfferEpassCreatePayload,
    CreateLocalOfferEpass,
    ExtractCreateEpassIds,
    IsLocalOfferBusinessSuccess,
    PostOrdersLocalOffersEPasses,
    PostOrdersLocalOffersEPassesPrebookingWithToken,
    PostPrebookingAvailability,
    RequestPrebookingToken,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


def _CreateEpassWithUsagesOrSkip(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    available_usages: int,
) -> Tuple[str, str, str]:
    """创建指定 ``availableUsages`` 的 ePass；返回 ``(ePassId, purchaseOrderId, clientUserId)``。"""
    payload = BuildLocalOfferEpassCreatePayload(available_usages=available_usages)
    kw = _StepKw(steps, f"创建 ePass availableUsages={available_usages}")
    resp = PostOrdersLocalOffersEPasses(
        token,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(resp)
    if resp.status_code == 400:
        if available_usages == 0:
            pytest.skip("创建 availableUsages=0 返回 HTTP 400，权益为 0 在参数层已拒绝。")
        LocalOfferFailOrRecord(f"创建 ePass HTTP 400: {resp.text[:500]!r}")
        return "", "", ""
    if not IsLocalOfferBusinessSuccess(env):
        if available_usages == 0:
            AssertPrebookingStepRejected(
                resp,
                expected_err_codes=("500.110.029", "500.110.001", "500.110.010"),
                context="create-zero-usages",
            )
            pytest.skip("创建 availableUsages=0 已被接口拒绝，权益为 0 负向在创建层已覆盖。")
        LocalOfferFailOrRecord(f"创建 ePass availableUsages={available_usages} 失败: {env!r}")
        return "", "", ""
    cid, e_pass_id, order_id = ExtractCreateEpassIds(resp)
    RegisterPendingLocalOfferOrder(order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    return e_pass_id, order_id, cid


def _TryAvailabilityThenPrebook(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    e_pass_id: str,
    purchase_order_id: str,
    client_user_id: str,
    target: object,
    adult_count: int,
    child_count: int,
    expect_failure: bool,
    expected_err_codes: Sequence[str],
    context: str,
) -> None:
    from services.local_offer_epass_service import LocalOfferPrebookingTarget

    assert isinstance(target, LocalOfferPrebookingTarget)
    body = BuildAvailabilityBody(
        e_pass_id=e_pass_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        adult_count=adult_count,
        child_count=child_count,
    )
    resp_avail = PostPrebookingAvailability(
        token,
        steps,
        body=body,
        brief=f"可用性 adult={adult_count} child={child_count}（{context}）",
    )
    _st, env, _ = ParseResponseEnvelope(resp_avail)
    if env is not None and env.get("code") == -1:
        if expect_failure:
            AssertPrebookingStepRejected(
                resp_avail,
                expected_err_codes=expected_err_codes,
                context=f"{context}-availability",
            )
            FinalizeCreatedLocalOfferPurchaseOnly(
                token,
                steps,
                e_pass_id=e_pass_id,
                purchase_order_id=purchase_order_id,
                context=f"{context}-availability-fail",
            )
            return
        LocalOfferFailOrRecord(f"期望可用性成功，实际失败: {env!r}")
        return
    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context=context)
    kw = _StepKw(steps, f"预约 adult={adult_count}（{context}）")
    resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
        token,
        e_pass_id,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    if expect_failure:
        AssertPrebookingStepRejected(
            resp_book,
            expected_err_codes=expected_err_codes,
            context=f"{context}-prebooking",
        )
        FinalizeCreatedLocalOfferPurchaseOnly(
            token,
            steps,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            context=f"{context}-prebooking-fail",
        )
        return
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        resp_book,
        e_pass_id=e_pass_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context=context,
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=client_user_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context=f"{context}-cancel",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        token,
        steps,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        context=f"{context}-purchase-cancel",
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · 权益点数为 0")
def test_LocalOfferEpass_Prebooking_ZeroAvailableUsages_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: local offer 权益点数为 0 时不可预约（创建或预约层拒绝）。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    e_pass_id, purchase_order_id, client_user_id = _CreateEpassWithUsagesOrSkip(
        EpassToken, ScenarioSteps, available_usages=0
    )
    _TryAvailabilityThenPrebook(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=client_user_id,
        target=target,
        adult_count=1,
        child_count=0,
        expect_failure=True,
        expected_err_codes=("500.110.029", "500.110.019", "500.020.009"),
        context="zero-usages",
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · 人数与权益点数")
@pytest.mark.parametrize(
    "available_usages,adult_count,expect_failure,case_label",
    [
        (1, 2, True, "guests-exceed-usages"),
        (1, 1, False, "guests-equals-usages"),
        (3, 1, False, "guests-less-than-usages"),
    ],
)
def test_LocalOfferEpass_Prebooking_GuestCountVsAvailableUsages(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    available_usages: int,
    adult_count: int,
    expect_failure: bool,
    case_label: str,
) -> None:
    """tc-p1: 预约人数与 ePass 剩余权益点数比较（> 失败，=/< 成功）。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    e_pass_id, purchase_order_id, client_user_id = _CreateEpassWithUsagesOrSkip(
        EpassToken,
        ScenarioSteps,
        available_usages=available_usages,
    )
    _TryAvailabilityThenPrebook(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=client_user_id,
        target=target,
        adult_count=adult_count,
        child_count=0,
        expect_failure=expect_failure,
        expected_err_codes=("500.110.029", "500.020.007", "500.020.029", "500.110.019"),
        context=case_label,
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · eSIM+LO 权益矩阵（12 步单场景）")
def test_LocalOfferEpass_EsimLoEntitlementMatrix_OneScenario(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1 合并场景（脑图权益校验整块）：

    仅 eSIM 权益 → LO 预约失败；补 LO 权益后成功；2 点用尽后失败；eSIM 权益仍可预约。
    """
    from scenarios.local_offer_epass_entitlement_scenarios import (
        RunLocalOfferEsimLoEntitlementMatrixScenario,
    )

    RunLocalOfferEsimLoEntitlementMatrixScenario(EpassToken, ScenarioSteps)


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · 无 Local Offer 权益 ePass")
def test_LocalOfferEpass_Prebooking_NoLocalOfferEntitlement_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1: ePassId 无 local offer 权益时预约失败。

    需预置 ``DP_LO_EPASS_NO_LO_ENTITLEMENT_EPASS_ID``（仅 eSIM 等无 LO 权益的 ePass）。
    """
    import os

    e_pass_id = os.getenv("DP_LO_EPASS_NO_LO_ENTITLEMENT_EPASS_ID", "").strip()
    if not e_pass_id:
        pytest.skip(
            "未配置 DP_LO_EPASS_NO_LO_ENTITLEMENT_EPASS_ID（无 Local Offer 权益的 ePass），跳过。"
        )
    target = ResolvePrebookingTargetByLabel("redemption_code")
    body = BuildAvailabilityBody(
        e_pass_id=e_pass_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
    )
    resp_avail = PostPrebookingAvailability(
        EpassToken,
        ScenarioSteps,
        body=body,
        brief="无 LO 权益 ePass 可用性",
    )
    _st, env, _ = ParseResponseEnvelope(resp_avail)
    if env is not None and env.get("code") == -1:
        AssertPrebookingStepRejected(
            resp_avail,
            expected_err_codes=("500.110.029", "500.110.019", "500.020.009", "500.110.020"),
            context="no-lo-entitlement-availability",
        )
        return
    pb_token = AssertPrebookingAvailabilitySuccess(resp_avail, context="no-lo-maybe-pass")
    kw = _StepKw(ScenarioSteps, "无 LO 权益 ePass 预约")
    resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
        EpassToken,
        e_pass_id,
        pb_token,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_book,
        expected_err_codes=("500.110.029", "500.110.019", "500.110.028"),
        context="no-lo-entitlement-prebooking",
    )
