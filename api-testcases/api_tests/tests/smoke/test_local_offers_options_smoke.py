"""
Local Offers options 只读冒烟用例。

主链路：获取 token → GET /v2/resources/localOffers/{resourceId}/options → 校验响应信封与核心 data 结构。
必填环境变量：``DP_PROGRAM_ID``、``DP_CLIENT_ID``、``DP_CLIENT_SECRET``；可选 ``DP_LOCAL_OFFER_RESOURCE_ID``。
"""
from __future__ import annotations

import allure
import pytest

from clients import GetAccessToken
from framework.reporting import AllureHttpScenarioSteps, RunAllureAssertionStep
from services.local_offers_options_service import (
    AssertLocalOfferOptionsEnvelope,
    AssertLocalOfferOptionsSuccessShape,
    BuildLocalOfferRequestContext,
    ParseJsonBody,
    SendGetLocalOfferOptions,
)

pytestmark = [pytest.mark.smoke, pytest.mark.local_offers]


@pytest.fixture(scope="function")
def AccessToken() -> str:
    """获取 Local Offers options 冒烟用例 access token。"""
    with allure.step("前置：获取 access token（POST /v2/auth/token，由 GetAccessToken 封装）"):
        token = GetAccessToken()
        if not isinstance(token, str) or len(token.strip()) < 8:
            pytest.fail(f"获取 token 异常: {token!r}")
        return token


def test_LocalOffersOptions_MinimalReadonly_Smoke(
    AccessToken: str, ScenarioSteps: AllureHttpScenarioSteps
) -> None:
    """只读冒烟：最小分页查询返回可解析信封，业务成功时包含核心 data 字段。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("只读冒烟：最小分页查询")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        query={"pageSize": 10, "pageNumber": 1},
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertHttpOk() -> str:
        assert response.status_code == 200, (
            f"HTTP 状态应为 200，实际={response.status_code}, body={response.text[:1000]}"
        )
        return "HTTP 200"

    RunAllureAssertionStep("断言：HTTP 层成功", _AssertHttpOk)

    body = ParseJsonBody(response)

    def _AssertEnvelopeAndShape() -> str:
        code = AssertLocalOfferOptionsEnvelope(body)
        if code == -1:
            pytest.skip(f"环境返回业务异常（code=-1），资源可能不存在或暂不可用: {body!r}")
        AssertLocalOfferOptionsSuccessShape(body)
        return "业务成功时 data 结构满足核心字段契约"

    RunAllureAssertionStep("断言：业务信封与 data 核心结构", _AssertEnvelopeAndShape)
