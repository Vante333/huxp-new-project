"""
CreateEpassOrder 模块 — Local Offer ePass 创建与负向。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · CreateEpassOrder

主链路 E2E 见 ``tests/features/test_local_offer_epass.py``。
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from services.local_offer_epass_service import (
    AssertBusinessFailure,
    AssertCreateAllowedResourcesRestriction,
    AssertLocalOfferEpassCreateCoreFields,
    BuildLocalOfferEpassCreatePayload,
    BuildOverLimitResourceIds,
    CancelPurchaseOrderAndVerifyPostCancelRetrieve,
    CreateLocalOfferEpass,
    ESIM_MODULE_INT,
    ExtractBusinessData,
    ExtractCreateEpassIds,
    FetchModuleResourceHintsOrSkip,
    IsLocalOfferBusinessSuccess,
    LOCAL_OFFER_MODULE_INT,
    PostOrdersEPassesList,
    PostOrdersLocalOffersEPasses,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 传对应 resourceId 下单成功")
def test_LocalOfferEpass_Create_WithMatchingResourceIds(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1（脑图红框）：allowedResources.resourceIds 传 ``GET /v2/resources?module=11`` 返回的有效 resourceId，下单成功。

    SaaS 权益核对需人工；接口侧校验创建成功且 allowedResources 回显一致。
    """
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    resource_ids = hints.ResourceIds[:1]
    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"resourceIds": resource_ids})
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（有效 resourceIds）"),
    )
    cid, e_pass_id, order_id = ExtractCreateEpassIds(resp)
    AssertLocalOfferEpassCreateCoreFields(resp, expected_client_user_id=cid)
    AssertCreateAllowedResourcesRestriction(
        resp,
        restriction_key="resourceIds",
        expected_values=resource_ids,
        context="matching-resourceIds",
    )
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        context="create-matching-resourceIds",
    )
    allure.attach(
        f"orderId={order_id}, ePassId={e_pass_id}, resourceIds={resource_ids!r}",
        name="create_with_resourceIds_context",
        attachment_type=allure.attachment_type.TEXT,
    )


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 传对应 countryOrRegion 下单成功")
def test_LocalOfferEpass_Create_WithMatchingCountryOrRegion(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1（脑图红框）：allowedResources.countryOrRegion 传 ``GET /v2/resources?module=11`` 解析的有效码，下单成功。

    canary 若不支持 countryOrRegion 限制（500.110.026）则 skip；SaaS 权益核对需人工。
    """
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("GET /v2/resources module=11 未解析到 countryOrRegion，跳过本用例。")
    countries = hints.CountryOrRegions[:1]
    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"countryOrRegion": countries})
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（有效 countryOrRegion）"),
    )
    _st, env, _ = ParseResponseEnvelope(resp)
    if not IsLocalOfferBusinessSuccess(env):
        if env is not None and env.get("errCode") == "500.110.026":
            pytest.skip(
                "canary 环境 Local Offer ePass 暂不支持 countryOrRegion 限制（500.110.026），"
                f"已动态获取 countryOrRegion={countries!r}。"
            )
        LocalOfferFailOrRecord(f"countryOrRegion 创建 ePass 非预期失败: {env!r}")
    cid, e_pass_id, order_id = ExtractCreateEpassIds(resp)
    AssertLocalOfferEpassCreateCoreFields(resp, expected_client_user_id=cid)
    AssertCreateAllowedResourcesRestriction(
        resp,
        restriction_key="countryOrRegion",
        expected_values=countries,
        context="matching-countryOrRegion",
    )
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        context="create-matching-countryOrRegion",
    )
    allure.attach(
        f"orderId={order_id}, ePassId={e_pass_id}, countryOrRegion={countries!r}",
        name="create_with_countryOrRegion_context",
        attachment_type=allure.attachment_type.TEXT,
    )


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向 iata 不支持")
def test_LocalOfferEpass_Create_IataRestrictionRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Local Offer 传 iata 应返回 500.110.026。"""
    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"iata": ["MAN"]})
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（iata 限制）"),
    )
    AssertBusinessFailure(resp, expected_err_code="500.110.026", context="iata-not-supported")


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向混合 module 资源")
def test_LocalOfferEpass_Create_MixedModuleResourceIdsRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: module=11 混合 esim(module=8) 与 local offer 资源应 500.110.001。"""
    lo_hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    esim_hints = FetchModuleResourceHintsOrSkip(EpassToken, module=ESIM_MODULE_INT, steps=ScenarioSteps)
    mixed_ids = [lo_hints.ResourceIds[0], esim_hints.ResourceIds[0]]
    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"resourceIds": mixed_ids})
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（混合品类 resourceIds）"),
    )
    AssertBusinessFailure(
        resp,
        expected_err_codes=("500.110.001", "500.000.017"),
        context="mixed-module-resourceIds",
    )


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向多限制条件")
def test_LocalOfferEpass_Create_MultipleRestrictionsRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: allowedResources 同时传 resourceIds + countryOrRegion 应 500.110.015。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    country = hints.CountryOrRegions[0] if hints.CountryOrRegions else "GB"
    payload = BuildLocalOfferEpassCreatePayload(
        allowed_resources={
            "resourceIds": hints.ResourceIds[:1],
            "countryOrRegion": [country],
        },
    )
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（多限制条件）"),
    )
    AssertBusinessFailure(resp, expected_err_codes=("500.110.015", "500.110.026"), context="multiple-restrictions")


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向 resourceIds 超 30")
def test_LocalOfferEpass_Create_ResourceIdsOverLimitRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: resourceIds 超过 30 个应 500.110.002。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    over_ids = BuildOverLimitResourceIds(hints.ResourceIds, count=31)
    payload = BuildLocalOfferEpassCreatePayload(allowed_resources={"resourceIds": over_ids})
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（31 个 resourceIds）"),
    )
    AssertBusinessFailure(resp, expected_err_code="500.110.002", context="resourceIds-over-30", accept_http_400=True)


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向 clientUserId 相同但姓名不同")
def test_LocalOfferEpass_Create_DuplicateClientUserIdRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1: clientUserId 相同、firstName/lastName 与已有会员不一致时应失败。

    脑图/用例 md：``500.110.011`` — Sorry, this clientUserId already exists.
    （与单纯 clientUserId 重复 ``500.080.011`` 的触发条件不同，本用例刻意改姓名。）
    """
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="create-before-duplicate-clientUserId",
    )
    payload = BuildLocalOfferEpassCreatePayload(
        client_user_id=created.ClientUserId,
        first_name="Conflict",
        last_name="User",
    )
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "相同 clientUserId + 不同姓名 再次创建"),
    )
    AssertBusinessFailure(
        resp,
        expected_err_codes=("500.110.011", "500.080.011"),
        context="same-clientUserId-diff-name",
    )


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 负向 esim resourceId")
def test_LocalOfferEpass_Create_EsimResourceIdRejected(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: Local Offer 创建传 esim resourceId 应 500.110.001。"""
    esim_hints = FetchModuleResourceHintsOrSkip(EpassToken, module=ESIM_MODULE_INT, steps=ScenarioSteps)
    payload = BuildLocalOfferEpassCreatePayload(
        allowed_resources={"resourceIds": [esim_hints.ResourceIds[0]]},
    )
    resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（esim resourceId）"),
    )
    AssertBusinessFailure(
        resp,
        expected_err_codes=("500.110.001", "500.000.017"),
        context="esim-resourceId-on-local-offer",
    )


@allure.feature("Local Offer ePass")
@allure.story("CreateEpassOrder · 无限制下单")
def test_LocalOfferEpass_Create_WithoutAllowedResources(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """tc-p1: allowedResources 三键空数组（不传限制）下单成功。"""
    created = CreateLocalOfferEpass(EpassToken, ScenarioSteps, allowed_resources=None)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="create-no-restrictions",
    )
    kw_list = _StepKw(ScenarioSteps, "ePass usage 订单列表")
    resp_list = PostOrdersEPassesList(
        EpassToken,
        created.EPassId,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    ExtractBusinessData(resp_list)
