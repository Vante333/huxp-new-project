"""
v2_resources_options_prebookings_availability 模块。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · availability
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from services.local_offer_epass_service import (
    AssertAvailabilityBusinessFailure,
    AssertPrebookingAvailabilitySuccess,
    BuildAvailabilityBody,
    BuildPastPrebookingDate,
    CreateLocalOfferEpass,
    FinalizeCreatedLocalOfferPurchaseOnly,
    ESIM_MODULE_INT,
    FetchEsimFirstOptionIdOrSkip,
    FetchModuleResourceHintsOrSkip,
    LOCAL_OFFER_MODULE_INT,
    PostResourcesOptionsPrebookingsAvailability,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


@allure.feature("Local Offer ePass")
@allure.story("Availability · adultCount=1 childCount=0 成功")
def test_LocalOfferEpass_Availability_Adult1Child0_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: adultCount=1 childCount=0 可用性校验通过。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    body = BuildAvailabilityBody(
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        adult_count=1,
        child_count=0,
    )
    kw = _StepKw(ScenarioSteps, "可用性 adult=1 child=0")
    resp = PostResourcesOptionsPrebookingsAvailability(
        EpassToken,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertPrebookingAvailabilitySuccess(resp, context="adult1-child0")
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="availability-adult1-child0",
    )


@allure.feature("Local Offer ePass")
@allure.story("Availability · 负向人数组合")
@pytest.mark.parametrize(
    "adult_count,child_count",
    [(1, 1), (0, 1), (0, 0)],
)
def test_LocalOfferEpass_Availability_InvalidGuestCountsRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    adult_count: int,
    child_count: int,
) -> None:
    """tc-p1: 非法 adultCount/childCount 组合应业务失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    body = BuildAvailabilityBody(
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        adult_count=adult_count,
        child_count=child_count,
    )
    kw = _StepKw(ScenarioSteps, f"可用性 adult={adult_count} child={child_count}")
    resp = PostResourcesOptionsPrebookingsAvailability(
        EpassToken,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

    _st, env, _ = ParseResponseEnvelope(resp)
    if env is not None and env.get("code") == -1:
        AssertAvailabilityBusinessFailure(resp, context=f"guest-count-{adult_count}-{child_count}")
        FinalizeCreatedLocalOfferPurchaseOnly(
            EpassToken,
            ScenarioSteps,
            e_pass_id=created.EPassId,
            purchase_order_id=created.PurchaseOrderId,
            context=f"availability-guest-count-{adult_count}-{child_count}",
        )
        return
    LocalOfferFailOrRecord(f"期望 adult={adult_count} child={child_count} 失败，实际成功: {resp.text[:500]!r}")


@allure.feature("Local Offer ePass")
@allure.story("Availability · 负向过期 prebookingDate")
def test_LocalOfferEpass_Availability_PastDateRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: prebookingDate 早于当前时间应失败。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    body = BuildAvailabilityBody(
        e_pass_id=created.EPassId,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        prebooking_date=BuildPastPrebookingDate(),
    )
    kw = _StepKw(ScenarioSteps, "可用性 过期 prebookingDate")
    resp = PostResourcesOptionsPrebookingsAvailability(
        EpassToken,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertAvailabilityBusinessFailure(resp, context="past-prebooking-date")
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="availability-past-date",
    )


@allure.feature("Local Offer ePass")
@allure.story("Availability · 负向 esim resourceId+optionId")
def test_LocalOfferEpass_Availability_EsimResourceOnModule11Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: module=11 但 resourceId/optionId 为 esim 应 500.020.009。"""
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
        module=LOCAL_OFFER_MODULE_INT,
    )
    kw = _StepKw(ScenarioSteps, "可用性 esim 资源 module=11")
    resp = PostResourcesOptionsPrebookingsAvailability(
        EpassToken,
        body,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    AssertAvailabilityBusinessFailure(
        resp,
        expected_err_codes=("500.020.009", "500.020.007", "500.110.019"),
        context="esim-resource-module11",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="availability-esim-resource-module11",
    )


@allure.feature("Local Offer ePass")
@allure.story("Availability · membershipId/ePassId 异常")
@pytest.mark.manual
@pytest.mark.parametrize(
    "case_label",
    [
        "membershipId-not-exist",
        "membershipId-cancelled",
        "ePassId-not-exist",
    ],
)
def test_LocalOfferEpass_Availability_AbnormalMembershipOrEpass_Manual(case_label: str) -> None:
    """tc-p2: membershipId/ePassId 异常状态 — 需特定测试数据，默认 manual。"""
    pytest.skip(f"需构造 {case_label} 测试数据，见用例 md membershipId/ePassId 异常状态。")
