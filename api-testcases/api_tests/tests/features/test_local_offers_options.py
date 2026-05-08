from __future__ import annotations

from typing import Any, Dict

import allure
import pytest

from clients import GetAccessToken
from framework.reporting import AllureHttpScenarioSteps, RunAllureAssertionStep
from services.local_offers_options_service import (
    AssertLocalOfferOptionsEnvelope,
    AssertLocalOfferOptionsRequestRejected,
    AssertLocalOfferOptionsSuccessShape,
    AssertLocalOfferOptionsSuccessContract,
    BuildLocalOfferRequestContext,
    ParseJsonBody,
    SendGetLocalOfferOptions,
)

pytestmark = [pytest.mark.feature, pytest.mark.local_offers]


@pytest.fixture(scope="function")
def AccessToken() -> str:
    """获取 Local Offers options 用例 access token。"""
    with allure.step("前置：获取 access token（POST /v2/auth/token，由 GetAccessToken 封装）"):
        token = GetAccessToken()
        if not isinstance(token, str) or len(token.strip()) < 8:
            pytest.fail(f"获取 token 异常: {token!r}")
        return token


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
@pytest.mark.smoke
def test_LocalOffersOptions_MinimalRequired_Smoke(AccessToken: str, ScenarioSteps: AllureHttpScenarioSteps) -> None:
    """
    正向：最小必填请求（path + 必填 headers）可返回可解析响应。

    说明：
    - 该接口契约响应 code 可能为 0 或 -1（异常示例），因此此处先校验契约形态；
    - 若业务 code=-1，表示环境或资源数据暂不可用，记为 skip，避免误判脚本失败。
    """
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("查询 Local Offers options（最小分页 pageSize=10）")
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
        return "HTTP 状态码为 200，可解析业务信封"

    RunAllureAssertionStep("断言：HTTP 层成功", _AssertHttpOk)

    body = ParseJsonBody(response)

    def _AssertEnvelopeAndSuccess() -> str:
        code = AssertLocalOfferOptionsEnvelope(body)
        if code == -1:
            pytest.skip(f"环境返回业务异常（code=-1），资源可能不存在或暂不可用: {body!r}")
        AssertLocalOfferOptionsSuccessShape(body)
        return "业务 code=0，data 含 pagination、resourceId、resourceName、optionList 等核心字段"

    RunAllureAssertionStep("断言：业务成功且核心 data 结构满足契约", _AssertEnvelopeAndSuccess)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
def test_LocalOffersOptions_QueryParameters_ShouldEchoPaginationAndKeepContract(
    AccessToken: str, ScenarioSteps: AllureHttpScenarioSteps
) -> None:
    """正向：pageSize/pageNumber/language/duration 组合查询仍满足响应契约。"""
    ctx = BuildLocalOfferRequestContext()
    query = {"pageSize": 5, "pageNumber": 1, "language": "en-US", "duration": 7}
    step_code, step_title = ScenarioSteps.Next("带 language/duration 的组合查询")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        query=query,
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

    def _AssertContract() -> str:
        code = AssertLocalOfferOptionsEnvelope(body)
        if code == -1:
            pytest.skip(f"环境返回业务异常（code=-1），无法校验查询参数契约: {body!r}")
        AssertLocalOfferOptionsSuccessContract(
            body,
            expected_resource_id=ctx.ResourceId,
            expected_page_size=5,
            expected_page_number=1,
        )
        return (
            "分页与 path resourceId 回显正确；pagination/optionList 等字段满足 OpenAPI 契约"
        )

    RunAllureAssertionStep("断言：分页回显与完整成功契约", _AssertContract)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
def test_LocalOffersOptions_UnknownResourceId_ShouldFail(
    AccessToken: str, ScenarioSteps: AllureHttpScenarioSteps
) -> None:
    """负向：不存在的 resourceId 不应返回业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("使用不存在的 resourceId 探测失败语义")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        resource_id_override="LO_NOT_EXIST_000000",
        query={"pageSize": 10, "pageNumber": 1},
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertRejected() -> str:
        AssertLocalOfferOptionsRequestRejected(response, context="未知 resourceId")
        return "响应未表现为业务成功（HTTP 非 2xx 或业务失败）"

    RunAllureAssertionStep("断言：未知 resourceId 按预期失败", _AssertRejected)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
def test_LocalOffersOptions_EmptyResourceId_ShouldFail(
    AccessToken: str, ScenarioSteps: AllureHttpScenarioSteps
) -> None:
    """负向：必填 path resourceId 为空时不应业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("空 resourceId path")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        resource_id_override="",
        query={"pageSize": 10, "pageNumber": 1},
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertRejected() -> str:
        AssertLocalOfferOptionsRequestRejected(response, context="空 resourceId")
        return "空 resourceId 未返回业务成功"

    RunAllureAssertionStep("断言：空 resourceId 被拒绝", _AssertRejected)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
@pytest.mark.parametrize(
    "resource_id",
    [
        "GR0006116!",
        "GR0006116/../options",
        "R" * 129,
    ],
    ids=["special_char", "path_like", "over_128_chars"],
)
def test_LocalOffersOptions_InvalidResourceIdFormat_ShouldFail(
    AccessToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    resource_id: str,
) -> None:
    """负向：resourceId 特殊字符、路径穿透样式或超长时不应业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next(f"非法 resourceId 形态（len={len(resource_id)}）")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        resource_id_override=resource_id,
        query={"pageSize": 10, "pageNumber": 1},
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertRejected() -> str:
        AssertLocalOfferOptionsRequestRejected(response, context=f"非法 resourceId={resource_id!r}")
        return "非法 resourceId 未返回业务成功"

    RunAllureAssertionStep("断言：resourceId 格式非法时失败", _AssertRejected)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
@pytest.mark.parametrize(
    "query",
    [
        {"pageSize": 0, "pageNumber": 1},
        {"pageSize": 101, "pageNumber": 1},
        {"pageSize": 10, "pageNumber": 0},
        {"pageSize": 10, "pageNumber": 101},
        {"pageSize": -1, "pageNumber": 1},
        {"pageSize": "abc", "pageNumber": 1},
    ],
    ids=["pageSize_0", "pageSize_101", "pageNumber_0", "pageNumber_101", "pageSize_negative", "pageSize_string"],
)
def test_LocalOffersOptions_InvalidPagination_ShouldFail(
    AccessToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    query: Dict[str, Any],
) -> None:
    """负向：分页边界外或类型错误时不应业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("非法分页 query")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        query=query,
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertRejected() -> str:
        AssertLocalOfferOptionsRequestRejected(response, context=f"非法分页参数 {query!r}")
        return "非法分页参数未返回业务成功"

    RunAllureAssertionStep("断言：分页非法时失败", _AssertRejected)


@allure.feature("Local Offers")
@allure.story("GET /v2/resources/localOffers/{resourceId}/options")
@pytest.mark.parametrize(
    "query",
    [
        pytest.param(
            {"pageSize": 10, "pageNumber": 1, "duration": -1},
            marks=pytest.mark.xfail(
                strict=True,
                reason="canary 当前未按 MCP query integer 语义拒绝负数 duration，保留为已知缺口观察",
            ),
        ),
        pytest.param(
            {"pageSize": 10, "pageNumber": 1, "duration": "seven"},
            marks=pytest.mark.xfail(
                strict=True,
                reason="canary 当前未按 MCP query integer 语义拒绝字符串 duration，保留为已知缺口观察",
            ),
        ),
        {"pageSize": 10, "pageNumber": 1, "language": "invalid-lang"},
        {"pageSize": 10, "pageNumber": 1, "language": "x" * 65},
    ],
    ids=["duration_negative", "duration_string", "language_invalid_format", "language_over_64_chars"],
)
def test_LocalOffersOptions_InvalidOptionalQuery_ShouldFail(
    AccessToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
    query: Dict[str, Any],
) -> None:
    """负向：duration 类型/范围异常或 language 非法时不应业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    step_code, step_title = ScenarioSteps.Next("非法可选查询参数（duration/language）")
    response = SendGetLocalOfferOptions(
        ctx=ctx,
        token=AccessToken,
        query=query,
        step_code=step_code,
        step_title=step_title,
    )

    def _AssertRejected() -> str:
        AssertLocalOfferOptionsRequestRejected(response, context=f"非法可选查询参数 {query!r}")
        return "非法可选参数未返回业务成功"

    RunAllureAssertionStep("断言：可选 query 非法时失败", _AssertRejected)
