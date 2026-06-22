"""
SaaS 人工核对检查点 — 仅跑接口链路，不查 SaaS 库。

接口自动化负责：下单/预约成功 + 核心字段断言。
Allure 附件 ``saas_manual_checkpoint`` 输出核对清单与 orderId/ePassId 等上下文，供测试工程师人工查 SaaS。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` 中含「sass/SaaS 核对」的节点。
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from scenarios.local_offer_epass_scenarios import (
    RunLocalOfferEpassBundleMainE2EScenario,
    RunLocalOfferEpassPrebookingMainE2EScenario,
)
from services.local_offer_epass_service import (
    AttachSaasManualCheckpoint,
    AssertUsageOrderDetailsShowsCancelled,
    CancelPurchaseOrderAndVerifyPostCancelRetrieve,
    CreateLocalOfferEpass,
    ExtractBusinessData,
    FetchLocalOfferResourceOptionReference,
    FetchModuleResourceHintsOrSkip,
    IsLocalOfferBusinessSuccess,
    LOCAL_OFFER_MODULE_INT,
    LocalOfferEpassCreateResult,
    LocalOfferEpassPrebookingResult,
    LocalOfferPrebookingTarget,
    PostOrdersEPassesUsageDetails,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [
    pytest.mark.feature,
    pytest.mark.local_offer_epass,
    pytest.mark.needs_write,
    pytest.mark.needs_saas_manual_verify,
]

_CREATE_MEMBERSHIP_CHECKLIST: List[str] = [
    "SaaS 会籍列表：Local Offer 权益类型与模板一致（休息室/Local Offer 品类）",
    "SaaS 会籍点数：availableUsages 与接口下单入参一致",
    "SaaS 会籍状态：Active/可用",
    "SaaS 购买订单（MS 开头）：状态可用，与 purchaseOrderId 一致",
]

_PREBOOKING_CHECKLIST: List[str] = [
    "SaaS 会籍列表：扣减权益点数与 usedUsages 一致",
    "SaaS 预定订单：商品信息、权益扣减、交易信息与 usageOrderId 一致",
    "SaaS 券记录 ord_order_common_voucher_esim_record（sub_type=OFFER）：voucher 与接口 vouchersList 一致",
    "供应商侧：是否真实下单（视网点/商品配置）",
]


def _CreateContext(created: LocalOfferEpassCreateResult, *, restriction_note: str) -> Dict[str, Any]:
    data = ExtractBusinessData(created.CreateResponse)
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    allowed = extra.get("allowedResources") if isinstance(extra.get("allowedResources"), dict) else {}
    return {
        "clientUserId": created.ClientUserId,
        "ePassId": created.EPassId,
        "purchaseOrderId": created.PurchaseOrderId,
        "availableUsages": extra.get("availableUsages"),
        "allowedResources": allowed,
        "restrictionNote": restriction_note,
    }


def _PrebookingContext(
    result: LocalOfferEpassPrebookingResult,
    *,
    target: LocalOfferPrebookingTarget,
    restriction_note: str,
) -> Dict[str, Any]:
    return {
        "clientUserId": result.ClientUserId,
        "ePassId": result.EPassId,
        "purchaseOrderId": result.PurchaseOrderId,
        "usageOrderId": result.UsageOrderId,
        "resourceId": result.ResourceId,
        "optionId": result.OptionId,
        "prebookingDate": result.PrebookingDate,
        "voucherTypeExpected": target.ExpectedVoucherType,
        "restrictionNote": restriction_note,
    }


def _RunPrebookingSaasCheckpointOrSkip(
    token: str,
    steps: AllureHttpScenarioSteps,
    *,
    target: LocalOfferPrebookingTarget,
    allowed_resources: Optional[Mapping[str, Sequence[str]]],
    restriction_note: str,
    scenario: str,
    extra_checklist: Optional[List[str]] = None,
) -> None:
    """创建（带限制）→ 预约主链路；创建失败时按 errCode skip。"""
    from services.local_offer_epass_service import (
        BuildLocalOfferEpassCreatePayload,
        ExtractCreateEpassIds,
        PostOrdersLocalOffersEPasses,
    )

    payload = BuildLocalOfferEpassCreatePayload(allowed_resources=allowed_resources)
    kw = _HttpStepKw(steps, f"创建 ePass（{restriction_note}）")
    create_resp = PostOrdersLocalOffersEPasses(
        token,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(create_resp)
    if not IsLocalOfferBusinessSuccess(env):
        err = env.get("errCode") if env else None
        if err in ("500.110.026", "500.110.010"):
            pytest.skip(f"canary 创建 ePass 失败（{err}），跳过 SaaS 预约检查点: {env!r}")
        LocalOfferFailOrRecord(f"创建 ePass 非预期失败: {env!r}")
    cid, e_pass_id, order_id = ExtractCreateEpassIds(create_resp)
    from services.local_offer_epass_service import (
        AssertLocalOfferPrebookingOrderSuccess,
        FinalizeCreatedLocalOfferPurchaseOnly,
        FinalizeSuccessfulLocalOfferUsageOrder,
        PostOrdersLocalOffersEPassesPrebooking,
        RegisterPendingLocalOfferEPassId,
        RegisterPendingLocalOfferOrder,
        RequestPrebookingToken,
    )

    RegisterPendingLocalOfferOrder(order_id)
    RegisterPendingLocalOfferEPassId(e_pass_id)

    pb_token, pb_date = RequestPrebookingToken(
        token, steps, e_pass_id=e_pass_id, target=target
    )
    kw_book = _HttpStepKw(steps, f"预约（{scenario}）")
    book_resp = PostOrdersLocalOffersEPassesPrebooking(
        token,
        e_pass_id,
        pb_token,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    _st_book, env_book, _ = ParseResponseEnvelope(book_resp)
    if env_book is not None and env_book.get("code") == -1:
        err_book = env_book.get("errCode")
        if err_book in ("500.110.010", "500.110.019", "500.020.009"):
            pytest.skip(f"canary 预约失败（{err_book}），跳过 SaaS 检查点: {env_book!r}")
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        book_resp,
        e_pass_id=e_pass_id,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        expected_voucher_type=target.ExpectedVoucherType,
        context=scenario,
    )
    FinalizeSuccessfulLocalOfferUsageOrder(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        client_user_id=cid,
        resource_id=target.ResourceId,
        option_id=target.OptionId,
        context=f"{scenario}-cancel",
    )
    FinalizeCreatedLocalOfferPurchaseOnly(
        token,
        steps,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        context=f"{scenario}-purchase-cancel",
    )
    result = LocalOfferEpassPrebookingResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=order_id,
        UsageOrderId=usage_order_id,
        PrebookingToken=pb_token,
        ResourceId=target.ResourceId,
        OptionId=target.OptionId,
        PrebookingDate=pb_date,
    )
    ctx = _PrebookingContext(result, target=target, restriction_note=restriction_note)
    _AttachUsageVoucherSnapshot(token, steps, result, target, ctx)
    checklist = _PREBOOKING_CHECKLIST + (extra_checklist or [])
    AttachSaasManualCheckpoint(
        scenario=scenario,
        checklist=checklist,
        context=ctx,
        sql_hints=[
            "SELECT * FROM `business-saas`.ord_order WHERE order_no='<usageOrderId>';",
        ],
    )


def _AttachUsageVoucherSnapshot(
    token: str,
    steps: AllureHttpScenarioSteps,
    result: LocalOfferEpassPrebookingResult,
    target: LocalOfferPrebookingTarget,
    context: Dict[str, Any],
) -> None:
    """拉 usage 详情，断言核心字段并把 vouchersList 快照并入 context（仍不查 SaaS）。"""
    kw = _HttpStepKw(steps, "usage 详情（SaaS 核对上下文）")
    resp = PostOrdersEPassesUsageDetails(
        token,
        result.UsageOrderId,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    option_ref = FetchLocalOfferResourceOptionReference(
        token,
        result.ResourceId,
        result.OptionId,
        steps=steps,
    )
    AssertUsageOrderDetailsShowsCancelled(
        resp,
        expected_order_id=result.UsageOrderId,
        expected_e_pass_id=result.EPassId,
        expected_client_user_id=result.ClientUserId,
        expected_resource_id=result.ResourceId,
        option_reference=option_ref,
        context="saas-checkpoint-usage-details-cancelled",
    )
    data = ExtractBusinessData(resp)
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    context["usageOrderStatus"] = data.get("status")
    context["vouchersList"] = extra.get("vouchersList")
    context["localOfferOptions"] = extra.get("localOfferOptions")


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("CreateEpassOrder · resourceIds 不传")
def test_LocalOfferEpass_SaasCheckpoint_Create_NoResourceIdsRestriction(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: resourceIds 不传 — 接口下单成功后输出 SaaS 权益核对清单。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps, allowed_resources=None)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="saas-create-no-resourceIds-cancel",
    )
    AttachSaasManualCheckpoint(
        scenario="CreateEpassOrder · resourceIds 不传",
        checklist=_CREATE_MEMBERSHIP_CHECKLIST
        + ["allowedResources.resourceIds 为空：SaaS 权益不限网点 resourceId"],
        context=_CreateContext(created, restriction_note="resourceIds 不传（三键空数组）"),
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("CreateEpassOrder · 传对应 resourceId")
def test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingResourceIds(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 传有效 resourceId — 接口成功后输出 SaaS 权益范围核对清单。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    resource_ids = hints.ResourceIds[:1]
    created = CreateLocalOfferEpass(
        EpassToken,
        ScenarioSteps,
        allowed_resources={"resourceIds": resource_ids},
    )
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="saas-create-resourceIds-cancel",
    )
    ctx = _CreateContext(created, restriction_note=f"resourceIds={resource_ids!r}")
    ctx["expectedResourceIds"] = resource_ids
    AttachSaasManualCheckpoint(
        scenario="CreateEpassOrder · 传对应 resourceId",
        checklist=_CREATE_MEMBERSHIP_CHECKLIST
        + ["SaaS 限制网点：仅 resourceIds 列表内资源可预约"],
        context=ctx,
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("CreateEpassOrder · countryOrRegion 不传")
def test_LocalOfferEpass_SaasCheckpoint_Create_NoCountryOrRegionRestriction(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: countryOrRegion 不传 — 接口下单成功后输出 SaaS 核对清单。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps, allowed_resources=None)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="saas-create-no-country-cancel",
    )
    AttachSaasManualCheckpoint(
        scenario="CreateEpassOrder · countryOrRegion 不传",
        checklist=_CREATE_MEMBERSHIP_CHECKLIST
        + ["allowedResources.countryOrRegion 为空：SaaS 权益不限国家/地区"],
        context=_CreateContext(created, restriction_note="countryOrRegion 不传（三键空数组）"),
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("CreateEpassOrder · 传对应 countryOrRegion")
def test_LocalOfferEpass_SaasCheckpoint_Create_WithMatchingCountryOrRegion(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 传有效 countryOrRegion — 接口成功后输出 SaaS 核对清单。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("GET /v2/resources module=11 未解析到 countryOrRegion。")
    countries = hints.CountryOrRegions[:1]
    from services.local_offer_epass_service import (
        AssertLocalOfferEpassCreateCoreFields,
        BuildLocalOfferEpassCreatePayload,
        ExtractCreateEpassIds,
        PostOrdersLocalOffersEPasses,
    )

    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"countryOrRegion": countries})
    kw = _HttpStepKw(ScenarioSteps, "创建 ePass（countryOrRegion · SaaS 检查点）")
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        step_code=kw["step_code"],
        step_title=kw["step_title"],
    )
    _st, env, _ = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env):
        if env is not None and env.get("errCode") == "500.110.026":
            pytest.skip(f"canary 不支持 countryOrRegion 限制: {env!r}")
        LocalOfferFailOrRecord(f"创建失败: {env!r}")
    cid, e_pass_id, order_id = ExtractCreateEpassIds(resp)
    AssertLocalOfferEpassCreateCoreFields(resp, expected_client_user_id=cid)
    created = LocalOfferEpassCreateResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=order_id,
        CreateResponse=resp,
    )
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        context="saas-create-country-cancel",
    )
    ctx = _CreateContext(created, restriction_note=f"countryOrRegion={countries!r}")
    ctx["expectedCountryOrRegion"] = countries
    AttachSaasManualCheckpoint(
        scenario="CreateEpassOrder · 传对应 countryOrRegion",
        checklist=_CREATE_MEMBERSHIP_CHECKLIST
        + ["SaaS 限制范围：countryOrRegion 与入参一致"],
        context=ctx,
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("Prebooking · 无网点限制 ePass")
@pytest.mark.parametrize("label", ["redemption_code", "card_secret"])
def test_LocalOfferEpass_SaasCheckpoint_Prebooking_UnrestrictedEpass(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    label: str,
) -> None:
    """tc-p1: epass 无网点限制 — 预约成功后输出 SaaS 会籍/订单/券核对清单。"""
    target = ResolvePrebookingTargetByLabel(label)
    result = RunLocalOfferEpassPrebookingMainE2EScenario(EpassToken, ScenarioSteps, target=target)
    ctx = _PrebookingContext(result, target=target, restriction_note="ePass 未限制 allowedResources")
    _AttachUsageVoucherSnapshot(EpassToken, ScenarioSteps, result, target, ctx)
    AttachSaasManualCheckpoint(
        scenario=f"Prebooking · 无限制 ePass · {label}",
        checklist=_PREBOOKING_CHECKLIST,
        context=ctx,
        sql_hints=[
            "SELECT * FROM `business-saas`.ord_order WHERE order_no='<usageOrderId>';",
            "SELECT assignment_id, card_coupon_type, use_url, end_time "
            "FROM `business-saas`.ord_order_common_voucher_esim_record "
            "WHERE sub_type='OFFER' AND /* assignment_id 或订单关联 */;",
        ],
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("Prebooking · ePass 限制 resourceIds")
def test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithResourceIdsRestriction(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 创建时限制 resourceIds — 预约后核对 SaaS 扣点与限制网点。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    target = ResolvePrebookingTargetByLabel("redemption_code")
    if target.ResourceId not in hints.ResourceIds:
        pytest.skip(
            f"默认预约网点 {target.ResourceId!r} 不在 module=11 资源列表中，"
            "请配置 DP_LO_EPASS_REDEMPTION_CODE_RESOURCE_ID 为列表内 resourceId。"
        )
    _RunPrebookingSaasCheckpointOrSkip(
        EpassToken,
        ScenarioSteps,
        target=target,
        allowed_resources={"resourceIds": [target.ResourceId]},
        restriction_note=f"ePass allowedResources.resourceIds=[{target.ResourceId!r}]",
        scenario="Prebooking · ePass 限制 resourceIds",
        extra_checklist=["SaaS：预约网点在 ePass resourceIds 限制范围内"],
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("Prebooking · ePass 限制 countryOrRegion")
def test_LocalOfferEpass_SaasCheckpoint_Prebooking_EpassWithCountryOrRegionRestriction(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: 创建时限制 countryOrRegion — 预约后核对 SaaS。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("未解析到 countryOrRegion。")
    countries = hints.CountryOrRegions[:1]
    target = ResolvePrebookingTargetByLabel("redemption_code")
    _RunPrebookingSaasCheckpointOrSkip(
        EpassToken,
        ScenarioSteps,
        target=target,
        allowed_resources={"countryOrRegion": countries},
        restriction_note=f"ePass allowedResources.countryOrRegion={countries!r}",
        scenario="Prebooking · ePass 限制 countryOrRegion",
        extra_checklist=["SaaS：预约资源 countryOrRegion 在 ePass 限制范围内"],
    )


@allure.feature("Local Offer ePass · SaaS 人工核对")
@allure.story("Bundle · 一步下单")
def test_LocalOfferEpass_SaasCheckpoint_Bundle_CreateAndPrebook(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Bundle 创建 ePass + 预约 — 输出 SaaS 会籍与预约订单核对清单。"""
    target = ResolvePrebookingTargetByLabel("redemption_code")
    result = RunLocalOfferEpassBundleMainE2EScenario(EpassToken, ScenarioSteps, target=target)
    ctx = _PrebookingContext(result, target=target, restriction_note="Bundle 一步下单")
    ctx["flow"] = "POST /v2/orders/localOffers/ePasses/bundle"
    _AttachUsageVoucherSnapshot(EpassToken, ScenarioSteps, result, target, ctx)
    AttachSaasManualCheckpoint(
        scenario="Bundle · 创建 ePass + 预约",
        checklist=_CREATE_MEMBERSHIP_CHECKLIST + _PREBOOKING_CHECKLIST,
        context=ctx,
        sql_hints=[
            "SELECT * FROM `business-saas`.ord_order WHERE order_no IN ('<purchaseOrderId>','<usageOrderId>');",
        ],
    )
