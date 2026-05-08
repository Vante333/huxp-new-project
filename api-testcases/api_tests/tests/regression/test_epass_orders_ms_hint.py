"""
PAPI-2424：ePasses **usage** details 对 MS 主单订单号的提示（``500.000.024``）。

手工用例见 ``testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md``；OpenAPI 见 MCP Default module
``POST /v2/orders/ePasses/details``。
"""
from __future__ import annotations

import os
from typing import Dict

import allure
import pytest
from test_data_loader import LoadP2424DatasetCsvRow

from clients import GetAccessTokenForEpass, PostOrdersEPassesDetails
from framework.reporting import AllureHttpScenarioSteps
from services.papi2424_service import (
    AssertHttp200MsUsageOrderHintEnvelope,
    AssertHttp200NotMsUsageOrderHint,
    AssertLowercaseMsPrefixBehavior,
    AssertUsageOrderRegressionNotMsHint,
    AttachP2424ResponseSummary,
    GetV2OrdersEPassesDetailsPath,
    RequireP2424EpassTokenEnvOrSkip,
    ResolveV1OrdersEPassesDetailsPathOrEmpty,
)

pytestmark = [pytest.mark.regression, pytest.mark.papi2424]


def _StepKw(steps: AllureHttpScenarioSteps, brief: str) -> Dict[str, str]:
    code, title = steps.Next(brief)
    return {"step_code": code, "step_title": title}


@pytest.fixture
def Token() -> str:
    """
    固定 ePass 三件套：``DP_EPASS_PROGRAM_ID``、``DP_EPASS_CLIENT_ID``、``DP_EPASS_CLIENT_SECRET`` → ``GetAccessTokenForEpass``。
    取 token 若需父级 Bearer，另配 ``DP_EPASS_TOKEN_REQUEST_BEARER`` 或 ``DP_TOKEN_REQUEST_BEARER``。
    """
    RequireP2424EpassTokenEnvOrSkip()
    token = GetAccessTokenForEpass()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token


@allure.feature("PAPI-2424")
@allure.story("v2_orders_ePasses_details_ms_prefix")
class TestP2424MsPrefixErrorEnvelope:
    """tc-P2-EPASS-001：MS 前缀 ``orderId`` 统一返回 ``500.000.024`` 与 ePasses/search 引导文案。"""

    @allure.title("MS 前缀 orderId 返回 500.000.024 与固定英文 msg（参数化）")
    @pytest.mark.parametrize(
        "order_id,case_note",
        [
            ("MS", "最短前缀边界"),
            ("MS00000000000001", "典型 MS 订单号形态"),
        ],
    )
    def test_ms_prefix_returns_search_hint(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
        order_id: str,
        case_note: str,
    ) -> None:
        allure.dynamic.parameter("orderId", order_id)
        allure.dynamic.parameter("说明", case_note)
        path = GetV2OrdersEPassesDetailsPath()
        resp = PostOrdersEPassesDetails(
            Token,
            path,
            order_id,
            **_StepKw(ScenarioSteps, f"ePasses/details（{case_note}）"),
        )
        AssertHttp200MsUsageOrderHintEnvelope(resp)


@allure.feature("PAPI-2424")
@allure.story("v2_orders_ePasses_details_non_ms")
class TestP2424NonMsSubstringAndUsage:
    """tc-P1 / tc-P3：非 MS 前缀与子串边界。"""

    @allure.title("tc-P1：非 MS 前缀 usage 订单不因本需求单独出现 500.000.024")
    @pytest.mark.needs_p2424_usage_order_id
    def test_usage_order_id_not_ms_hint(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        oid = os.environ.get("DP_P2424_USAGE_ORDER_ID", "").strip()
        if not oid:
            oid = LoadP2424DatasetCsvRow().usage_order_id.strip()
        if not oid:
            pytest.skip("未设置 DP_P2424_USAGE_ORDER_ID（须为环境已知的非 MS 开头 usage 订单号）")
        if oid.upper().startswith("MS"):
            pytest.skip("DP_P2424_USAGE_ORDER_ID 不得以 MS 开头")
        path = GetV2OrdersEPassesDetailsPath()
        resp = PostOrdersEPassesDetails(
            Token,
            path,
            oid,
            **_StepKw(ScenarioSteps, "ePasses/details（usage 回归）"),
        )
        AssertUsageOrderRegressionNotMsHint(resp)

    @allure.title("tc-P3：orderId 含 MS 子串但非 MS 前缀（DP000MS00000001）")
    def test_substring_ms_not_prefix_dp_style(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        path = GetV2OrdersEPassesDetailsPath()
        resp = PostOrdersEPassesDetails(
            Token,
            path,
            "DP000MS00000001",
            **_StepKw(ScenarioSteps, "ePasses/details（子串非前缀）"),
        )
        AssertHttp200NotMsUsageOrderHint(resp)

    @allure.title("tc-P3：orderId 含 MS 子串但非 MS 前缀（SL20260129BBMSXV9）")
    def test_substring_ms_not_prefix_sl_style(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        path = GetV2OrdersEPassesDetailsPath()
        resp = PostOrdersEPassesDetails(
            Token,
            path,
            "SL20260129BBMSXV9",
            **_StepKw(ScenarioSteps, "ePasses/details（SL 样例）"),
        )
        AssertHttp200NotMsUsageOrderHint(resp)


@allure.feature("PAPI-2424")
@allure.story("v2_orders_ePasses_details_case_sensitivity")
class TestP2424MsPrefixCaseSensitivity:
    """tc-P3-EPASS-002：大小写策略由 ``DP_P2424_MS_PREFIX_CASE_INSENSITIVE`` 声明期望。"""

    @allure.title("MS vs ms 前缀：与环境变量声明的评审结论一致")
    def test_uppercase_ms_always_hint_lowercase_depends_on_env(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        path = GetV2OrdersEPassesDetailsPath()
        upper_id = "MS00000000000001"
        lower_id = "ms00000000000001"

        resp_upper = PostOrdersEPassesDetails(
            Token,
            path,
            upper_id,
            **_StepKw(ScenarioSteps, "ePasses/details（大写 MS 前缀）"),
        )
        AssertHttp200MsUsageOrderHintEnvelope(resp_upper)

        resp_lower = PostOrdersEPassesDetails(
            Token,
            path,
            lower_id,
            **_StepKw(ScenarioSteps, "ePasses/details（小写 ms 前缀）"),
        )
        AssertLowercaseMsPrefixBehavior(resp_lower)


@allure.feature("PAPI-2424")
@allure.story("v1_v2_orders_ePasses_details")
class TestP2424V1V2Consistency:
    """tc-P2-EPASS-002：V1 与 V2 对 MS 前缀返回一致（V1 路径未配置则跳过）。"""

    @allure.title("V1/V2 ePasses details 对 MS 前缀均返回 500.000.024（需配置 V1 路径）")
    def test_v1_v2_ms_prefix_same_envelope(
        self,
        Token: str,
        ScenarioSteps: AllureHttpScenarioSteps,
    ) -> None:
        path_v1 = ResolveV1OrdersEPassesDetailsPathOrEmpty()
        if not path_v1:
            pytest.skip(
                "未配置 DP_P2424_V1_ORDERS_EPASSES_DETAILS_PATH；仅 V2 上线时请跳过或后续补 V1 路径"
            )
        path_v2 = GetV2OrdersEPassesDetailsPath()
        order_id = "MS00000000000001"

        resp_v1 = PostOrdersEPassesDetails(
            Token,
            path_v1,
            order_id,
            **_StepKw(ScenarioSteps, "V1 ePasses/details（MS）"),
        )
        AttachP2424ResponseSummary(resp_v1, label="v1")
        AssertHttp200MsUsageOrderHintEnvelope(resp_v1, context="PAPI-2424-V1")

        resp_v2 = PostOrdersEPassesDetails(
            Token,
            path_v2,
            order_id,
            **_StepKw(ScenarioSteps, "V2 ePasses/details（MS）"),
        )
        AttachP2424ResponseSummary(resp_v2, label="v2")
        AssertHttp200MsUsageOrderHintEnvelope(resp_v2, context="PAPI-2424-V2")
