"""
Prebooking 网点/国家限制 — 限定范围内成功、范围外失败。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` ·
epassid 限定 resourceIds / countryOrRegion 预约。
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest
from requests import Response

from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from services.local_offer_epass_service import (
    AssertLocalOfferPrebookingOrderSuccess,
    AssertPrebookingAvailabilitySuccess,
    AssertPrebookingStepRejected,
    BuildAvailabilityBody,
    CreateLocalOfferEpass,
    FetchLocalOfferResourceOptionReference,
    FetchModuleResourceHintsOrSkip,
    LOCAL_OFFER_MODULE_INT,
    LOCAL_OFFER_PATH_MODULE,
    LocalOfferEpassCreateResult,
    LocalOfferPrebookingTarget,
    PickAlternatePrebookingTarget,
    PostOrdersLocalOffersEPassesPrebookingWithToken,
    PostPrebookingAvailability,
    FinalizeCreatedLocalOfferPurchaseOnly,
    FinalizeSuccessfulLocalOfferUsageOrder,
    RegisterPendingLocalOfferEPassId,
    RegisterPendingLocalOfferOrder,
    RequestPrebookingToken,
    RequestPrebookingTokenWithoutEpass,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


_AVAILABILITY_REJECT_ERR_CODES = (
    "500.110.019",
    "500.071.019",
    "500.110.031",
    "500.020.009",
    "500.020.007",
)
_PREBOOKING_REJECT_ERR_CODES = (
    "500.110.019",
    "500.071.019",
    "500.110.031",
    "500.110.028",
)


def _AvailabilityModeLabel(with_e_pass_id: bool) -> str:
    return "有 ePassId" if with_e_pass_id else "无 ePassId"


def _SkipIfPrebookInternalError(resp: Response, *, context: str) -> None:
    _st, env, _ = ParseResponseEnvelope(resp)
    if env is not None and env.get("code") == -1 and env.get("errCode") == "500.110.010":
        pytest.skip(f"canary 预约内部错误 500.110.010（{context}）: {env.get('msg')!r}")


def _PrebookAtTargetBothAvailabilityModes(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    created: LocalOfferEpassCreateResult,
    target: LocalOfferPrebookingTarget,
    context: str,
) -> None:
    """可用性分别带/不带 ePassId 拿 token，再各调一次预约下单；成功后取消并查询详情/列表/会籍卡。"""
    e_pass_id = created.EPassId
    for with_e_pass_id in (True, False):
        mode = _AvailabilityModeLabel(with_e_pass_id)
        sub_context = f"{context}-{'with' if with_e_pass_id else 'without'}-epass-avail"
        if with_e_pass_id:
            pb_token, _ = RequestPrebookingToken(
                token,
                steps,
                e_pass_id=e_pass_id,
                target=target,
            )
        else:
            pb_token, _ = RequestPrebookingTokenWithoutEpass(
                token,
                steps,
                target=target,
            )
        kw = _StepKw(steps, f"预约 {target.Label}（{context} · {mode}）")
        resp = PostOrdersLocalOffersEPassesPrebookingWithToken(
            token,
            e_pass_id,
            pb_token,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        _SkipIfPrebookInternalError(resp, context=sub_context)
        usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
            resp,
            e_pass_id=e_pass_id,
            resource_id=target.ResourceId,
            option_id=target.OptionId,
            expected_voucher_type=target.ExpectedVoucherType,
            context=sub_context,
        )
        FinalizeSuccessfulLocalOfferUsageOrder(
            token,
            steps,
            usage_order_id=usage_order_id,
            e_pass_id=e_pass_id,
            purchase_order_id=created.PurchaseOrderId,
            client_user_id=created.ClientUserId,
            resource_id=target.ResourceId,
            option_id=target.OptionId,
            context=f"{sub_context}-cancel",
        )


def _AssertOutOfRangeBothAvailabilityModes(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    e_pass_id: str,
    target: LocalOfferPrebookingTarget,
    context: str,
) -> None:
    """限制外网点：可用性带/不带 ePassId 各测一次，若拿到 token 再分别调预约下单。"""
    for with_e_pass_id in (True, False):
        mode = _AvailabilityModeLabel(with_e_pass_id)
        sub_context = f"{context}-{'with' if with_e_pass_id else 'without'}-epass-avail"
        body = BuildAvailabilityBody(
            e_pass_id=e_pass_id if with_e_pass_id else None,
            resource_id=target.ResourceId,
            option_id=target.OptionId,
        )
        resp_avail = PostPrebookingAvailability(
            token,
            steps,
            body=body,
            brief=f"可用性 限制外网点 {target.ResourceId}（{context} · {mode}）",
        )
        _st, env, _ = ParseResponseEnvelope(resp_avail)
        if env is not None and env.get("code") == -1:
            AssertPrebookingStepRejected(
                resp_avail,
                expected_err_codes=_AVAILABILITY_REJECT_ERR_CODES,
                context=f"{sub_context}-availability",
            )
            continue
        pb_token = AssertPrebookingAvailabilitySuccess(
            resp_avail,
            context=f"{sub_context}-unexpected-avail",
        )
        kw = _StepKw(steps, f"限制外网点预约（{context} · {mode}）")
        resp_book = PostOrdersLocalOffersEPassesPrebookingWithToken(
            token,
            e_pass_id,
            pb_token,
            step_code=kw["step_code"],
            step_title=kw["step_title"],
        )
        AssertPrebookingStepRejected(
            resp_book,
            expected_err_codes=_PREBOOKING_REJECT_ERR_CODES,
            context=f"{sub_context}-prebooking",
        )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · ePass 限制 resourceIds · 范围内")
def test_LocalOfferEpass_Prebooking_ResourceIdsRestriction_InRange_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ePass 限定 resourceIds，预约列表内网点应成功。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    target = ResolvePrebookingTargetByLabel("redemption_code")
    if target.ResourceId not in hints.ResourceIds:
        pytest.skip(
            f"默认网点 {target.ResourceId!r} 不在 module=11 资源列表，"
            "请配置 DP_LO_EPASS_REDEMPTION_CODE_RESOURCE_ID 为列表内 ID。"
        )
    created = CreateLocalOfferEpass(
        EpassToken,
        ScenarioSteps,
        allowed_resources={"resourceIds": [target.ResourceId]},
    )
    _PrebookAtTargetBothAvailabilityModes(
        EpassToken,
        ScenarioSteps,
        created=created,
        target=target,
        context="resourceIds-in-range",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="resourceIds-in-range-purchase",
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · ePass 限制 resourceIds · 范围外")
def test_LocalOfferEpass_Prebooking_ResourceIdsRestriction_OutOfRange_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ePass 限定 resourceIds，预约列表外网点应失败（可用性或预约层）。"""
    hints = FetchModuleResourceHintsOrSkip(
        EpassToken,
        module=LOCAL_OFFER_MODULE_INT,
        steps=ScenarioSteps,
        min_resource_ids=1,
    )
    allowed_id = hints.ResourceIds[0]
    try:
        out_target = PickAlternatePrebookingTarget(exclude_resource_ids=[allowed_id])
    except LookupError as exc:
        pytest.skip(str(exc))
    created = CreateLocalOfferEpass(
        EpassToken,
        ScenarioSteps,
        allowed_resources={"resourceIds": [allowed_id]},
    )
    _AssertOutOfRangeBothAvailabilityModes(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        target=out_target,
        context="resourceIds-out-of-range",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="resourceIds-out-of-range",
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · ePass 限制 countryOrRegion · 范围内")
def test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_InRange_Success(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ePass 限定 countryOrRegion，预约对应国家网点应成功。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("GET /v2/resources 未解析到 countryOrRegion。")
    target = ResolvePrebookingTargetByLabel("redemption_code")
    ref = FetchLocalOfferResourceOptionReference(
        EpassToken,
        target.ResourceId,
        target.OptionId,
        steps=ScenarioSteps,
    )
    if not ref.CountryOrRegion:
        pytest.skip(f"默认网点 {target.ResourceId!r} 无 countryOrRegion 详情。")
    if ref.CountryOrRegion not in hints.CountryOrRegions:
        pytest.skip(
            f"默认网点 country={ref.CountryOrRegion!r} 不在 resources 列表 countries 中，无法构造正向。"
        )
    countries = [ref.CountryOrRegion]
    from services.local_offer_epass_service import (
        AssertLocalOfferEpassCreateCoreFields,
        BuildLocalOfferEpassCreatePayload,
        ExtractCreateEpassIds,
        IsLocalOfferBusinessSuccess,
        PostOrdersLocalOffersEPasses,
    )

    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"countryOrRegion": countries})
    kw = _StepKw(ScenarioSteps, "创建 ePass（countryOrRegion 限制）")
    create_resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(create_resp)
    if not IsLocalOfferBusinessSuccess(env):
        if env is not None and env.get("errCode") == "500.110.026":
            pytest.skip(f"canary 不支持 countryOrRegion 限制: {env!r}")
        LocalOfferFailOrRecord(f"创建 countryOrRegion 限制 ePass 失败: {env!r}")
    cid, e_pass_id, order_id = ExtractCreateEpassIds(create_resp)
    AssertLocalOfferEpassCreateCoreFields(create_resp, expected_client_user_id=cid)
    created = LocalOfferEpassCreateResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=order_id,
        CreateResponse=create_resp,
    )
    RegisterPendingLocalOfferOrder(order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    _PrebookAtTargetBothAvailabilityModes(
        EpassToken,
        ScenarioSteps,
        created=created,
        target=target,
        context="countryOrRegion-in-range",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="countryOrRegion-in-range-purchase",
    )


@allure.feature("Local Offer ePass")
@allure.story("Prebooking · ePass 限制 countryOrRegion · 范围外")
def test_LocalOfferEpass_Prebooking_CountryOrRegionRestriction_OutOfRange_Rejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: ePass 限定 countryOrRegion A，预约 A 外国家网点应失败。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("GET /v2/resources 未解析到 countryOrRegion。")
    allowed_countries = hints.CountryOrRegions[:1]
    target = ResolvePrebookingTargetByLabel("redemption_code")
    ref = FetchLocalOfferResourceOptionReference(
        EpassToken,
        target.ResourceId,
        target.OptionId,
        steps=ScenarioSteps,
    )
    if not ref.CountryOrRegion:
        pytest.skip(f"默认网点 {target.ResourceId!r} 无 countryOrRegion。")
    if ref.CountryOrRegion in allowed_countries:
        pytest.skip(
            f"默认网点 country={ref.CountryOrRegion!r} 落在 allowed={allowed_countries!r} 内，"
            "无法构造 countryOrRegion 限制外负向；请换 DP_LO_EPASS_REDEMPTION_CODE_RESOURCE_ID。"
        )
    from services.local_offer_epass_service import (
        BuildLocalOfferEpassCreatePayload,
        ExtractCreateEpassIds,
        IsLocalOfferBusinessSuccess,
        PostOrdersLocalOffersEPasses,
    )

    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"countryOrRegion": allowed_countries})
    kw = _StepKw(ScenarioSteps, "创建 ePass（countryOrRegion 限制 · 负向）")
    create_resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(create_resp)
    if not IsLocalOfferBusinessSuccess(env):
        if env is not None and env.get("errCode") == "500.110.026":
            pytest.skip(f"canary 不支持 countryOrRegion 限制: {env!r}")
        LocalOfferFailOrRecord(f"创建失败: {env!r}")
    _cid, e_pass_id, purchase_order_id = ExtractCreateEpassIds(create_resp)
    RegisterPendingLocalOfferOrder(purchase_order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)
    _AssertOutOfRangeBothAvailabilityModes(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        target=target,
        context="countryOrRegion-out-of-range",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        context="countryOrRegion-out-of-range",
    )
