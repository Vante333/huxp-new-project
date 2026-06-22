"""
Local Offer ePass 主链路 E2E 入口（2026Q2_SP3）。

与拆分模块用例并存：本文件仅保留 **主调用链** 冒烟/E2E，便于 ``-m smoke`` 或 ``local_offer_epass`` 快速回归。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md``
主链路：``api-testcases/docs/api-main-call-chains.md`` · EPass
"""
from __future__ import annotations

from typing import Dict

import allure
import pytest

from clients import GetAccessTokenForEpass
from framework.reporting import AllureHttpScenarioSteps
from framework.soft_assert import LocalOfferFailOrRecord
from scenarios.local_offer_epass_scenarios import (
    RunLocalOfferEpassBundleMainE2EScenario,
    RunLocalOfferEpassCreateMainE2EScenario,
    RunLocalOfferEpassPrebookingMainE2EScenario,
)
from services.local_offer_epass_service import (
    AssertEpassSearchDetailsCoreFields,
    CancelPurchaseOrderAndVerifyPostCancelRetrieve,
    AssertLocalOfferEpassCreateCoreFields,
    AssertUserEPassesContains,
    BuildLocalOfferEpassCreatePayload,
    ExtractBusinessData,
    ExtractCreateEpassIds,
    FetchModuleResourceHintsOrSkip,
    IsLocalOfferBusinessSuccess,
    LOCAL_OFFER_MODULE_INT,
    PostOrdersEPassesList,
    PostOrdersEPassesSearch,
    PostOrdersLocalOffersEPasses,
    PostUsersEPasses,
    RequireLocalOfferEpassEnvOrSkip,
    ResolvePrebookingTargetByLabel,
    _HttpStepKw,
)
from services.papi2548_memberships_extensions_impl import ParseResponseEnvelope

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


@pytest.fixture
def EpassToken() -> str:
    """ePass 三件套取 token。"""
    RequireLocalOfferEpassEnvOrSkip()
    token = GetAccessTokenForEpass()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    return _HttpStepKw(steps, brief)


@allure.feature("Local Offer ePass")
@allure.story("E2E · 创建验证链")
@pytest.mark.smoke
def test_LocalOfferEpass_E2E_CreateMainChain(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    主链路 1：``POST /v2/orders/localOffers/ePasses`` → ``POST /v2/users/ePasses`` →
    ``POST /v2/orders/ePasses`` → ``POST /v2/orders/ePasses/search``（orderId + ePassId）
    """
    RunLocalOfferEpassCreateMainE2EScenario(EpassToken, ScenarioSteps)


@allure.feature("Local Offer ePass")
@allure.story("E2E · 创建链 + 动态 resourceIds")
def test_LocalOfferEpass_E2E_CreateWithDynamicResourceIds(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """主链路 1 变体：allowedResources.resourceIds 从 ``GET /v2/resources?module=11`` 动态获取。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    RunLocalOfferEpassCreateMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        allowed_resources={"resourceIds": hints.ResourceIds[:1]},
    )


@allure.feature("Local Offer ePass")
@allure.story("E2E · 创建链 + 动态 countryOrRegion")
def test_LocalOfferEpass_E2E_CreateWithDynamicCountryOrRegion(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """主链路 1 变体：allowedResources.countryOrRegion 从 ``GET /v2/resources?module=11`` 动态获取。"""
    hints = FetchModuleResourceHintsOrSkip(EpassToken, module=LOCAL_OFFER_MODULE_INT, steps=ScenarioSteps)
    if not hints.CountryOrRegions:
        pytest.skip("GET /v2/resources module=11 未解析到 countryOrRegion，跳过本用例。")
    payload = BuildLocalOfferEpassCreatePayload(
        allowed_resources={"countryOrRegion": hints.CountryOrRegions[:1]},
    )
    create_resp = PostOrdersLocalOffersEPasses(
        EpassToken,
        payload,
        **_StepKw(ScenarioSteps, "创建 ePass（countryOrRegion 限制）"),
    )
    _st, create_env, _ = ParseResponseEnvelope(create_resp)
    if not IsLocalOfferBusinessSuccess(create_env):
        if create_env is not None and create_env.get("errCode") == "500.110.026":
            pytest.skip(
                "canary 环境 Local Offer ePass 暂不支持 countryOrRegion 限制（500.110.026），"
                f"已动态获取 countryOrRegion={hints.CountryOrRegions[:1]!r}。"
            )
        LocalOfferFailOrRecord(f"countryOrRegion 创建 ePass 非预期失败: {create_env!r}")
    cid, e_pass_id, order_id = ExtractCreateEpassIds(create_resp)
    AssertLocalOfferEpassCreateCoreFields(create_resp, expected_client_user_id=cid)

    kw_users = _StepKw(ScenarioSteps, "查询用户 ePass 列表")
    resp_users = PostUsersEPasses(
        EpassToken, cid, step_code=kw_users["step_code"], step_title=kw_users["step_title"]
    )
    AssertUserEPassesContains(resp_users, e_pass_id=e_pass_id)

    kw_search = _StepKw(ScenarioSteps, "ePass 购买单详情（orderId）")
    resp_search = PostOrdersEPassesSearch(
        EpassToken,
        order_id=order_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )
    AssertEpassSearchDetailsCoreFields(
        resp_search,
        expected_order_id=order_id,
        expected_e_pass_id=e_pass_id,
        context="e2e-countryOrRegion-by-orderId",
    )

    kw_list = _StepKw(ScenarioSteps, "ePass usage 订单列表")
    resp_list = PostOrdersEPassesList(
        EpassToken,
        e_pass_id,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    ExtractBusinessData(resp_list)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        EpassToken,
        ScenarioSteps,
        e_pass_id=e_pass_id,
        purchase_order_id=order_id,
        context="e2e-countryOrRegion-cancel",
    )


@allure.feature("Local Offer ePass")
@allure.story("E2E · Prebooking 验证链")
@pytest.mark.parametrize("label", ["url", "redemption_code", "card_secret"])
def test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    label: str,
) -> None:
    """
    主链路 2：创建 ePass → 可用性 → 预约下单 → 取消 usage 单 → 取消后 details/列表/search。

    默认网点：
    网点由环境变量配置（见 ``env/.env.local-offer.example``）：
    - url: ``DP_LO_EPASS_URL_RESOURCE_ID`` / ``DP_LO_EPASS_URL_OPTION_ID``
    - redemption_code: ``DP_LO_EPASS_REDEMPTION_CODE_*`` 或默认 ``DP_LO_EPASS_RESOURCE_ID`` / ``OPTION_ID``
    - card_secret: ``DP_LO_EPASS_CARD_SECRET_*``
    """
    target = ResolvePrebookingTargetByLabel(label)
    allure.dynamic.parameter("resourceId", target.ResourceId)
    allure.dynamic.parameter("optionId", target.OptionId)
    RunLocalOfferEpassPrebookingMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        target=target,
    )


@allure.feature("Local Offer ePass")
@allure.story("E2E · Bundle 一步下单链")
@pytest.mark.parametrize("label", ["redemption_code", "card_secret"])
def test_LocalOfferEpass_E2E_BundleMainChain_ByVoucherType(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    label: str,
) -> None:
    """
    主链路 3（Bundle）：可用性（无 ePassId）→ ``POST .../ePasses/bundle`` →
    users → search（ePassId → orderId 二次查询）→ usage 详情 → 订单列表。
    """
    target = ResolvePrebookingTargetByLabel(label)
    allure.dynamic.parameter("resourceId", target.ResourceId)
    allure.dynamic.parameter("optionId", target.OptionId)
    RunLocalOfferEpassBundleMainE2EScenario(EpassToken, ScenarioSteps, target=target)
