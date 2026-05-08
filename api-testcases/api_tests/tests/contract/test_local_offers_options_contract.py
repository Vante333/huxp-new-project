"""
Local Offers options OpenAPI 契约用例。

依据 MCP OpenAPI：``GET /v2/resources/localOffers/{resourceId}/options``。
本文件只验证本地响应结构断言，不访问外部 canary 环境。

**Allure**：与 feature 用例同构展示「步骤 + request_step_meta + request_meta + response_body_json +
response_status」，但标注 ``contract_offline``——请求为 **对照 OpenAPI 的示例元数据**，响应体为 **本地构造的待校验
JSON**，无真实网络 I/O。
"""
from __future__ import annotations

import os
from typing import Any, Dict

import allure
import pytest

from framework.reporting import (
    AllureHttpScenarioSteps,
    AttachAllureRequestMeta,
    AttachJson,
    FormatAllureHttpStepTitle,
    RunAllureAssertionStep,
)
from services.local_offers_options_service import (
    AssertLocalOfferOptionsBusinessFailure,
    AssertLocalOfferOptionsSuccessContract,
)

pytestmark = [pytest.mark.contract, pytest.mark.local_offers]

# 与网关示例一致，仅用于报告展示（契约用例不发起真实 HTTP）。
_CONTRACT_REPORT_BASE_URL = "https://developer-sandbox.dragonpass.com/api"


def _ResolveDisplayResourceId(body: Dict[str, Any]) -> str:
    data = body.get("data")
    if isinstance(data, dict):
        rid = data.get("resourceId")
        if isinstance(rid, str) and rid:
            return rid
    return "LO00001"


def AttachLocalOffersContractHttpStep(
    steps: AllureHttpScenarioSteps,
    *,
    brief: str,
    resource_id: str,
    query: Dict[str, Any],
    response_body: Dict[str, Any],
    response_status_line: str = "HTTP 200（契约离线样例，非网关真实响应）",
) -> None:
    """
    为契约用例写入与主线 HTTP 步骤一致的 Allure 附件。

    ``request_meta.headers`` 为示例脱敏头；``response_body_json`` 为当前用例正在校验的本地 JSON。
    """
    path = f"/v2/resources/localOffers/{resource_id}/options"
    url = f"{_CONTRACT_REPORT_BASE_URL.rstrip('/')}{path}"
    step_code, step_title = steps.Next(brief)
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        AttachJson(
            "request_step_meta",
            {
                "step_code": step_code,
                "step_title": step_title,
                "method": "GET",
                "path": path,
                "scenario_kind": "contract_offline",
                "note": "本地 JSON 断言，无真实 HTTP；下列请求参数仅供报告与 OpenAPI 对照。",
            },
        )
        program_example = os.getenv("DP_PROGRAM_ID", "").strip() or "PROGRAM_EXAMPLE"
        synthetic_headers = {
            "Authorization": "Bearer ***",
            "X-Request-ID": "00000000-0000-0000-0000-000000000001",
            "X-Program-ID": program_example,
            "Content-Type": "application/json",
            "x-version": "contract-offline",
        }
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=synthetic_headers,
            json_body=None,
            params=dict(query) if query else None,
        )
        AttachJson("response_body_json", response_body)
        allure.attach(
            response_status_line + "\n",
            name="response_status",
            attachment_type=allure.attachment_type.TEXT,
        )


def BuildSuccessBodyWithValidityTypes() -> Dict[str, Any]:
    """构造覆盖 ``validity.type`` 三种 anyOf 分支的本地契约样例。"""
    return {
        "code": 0,
        "data": {
            "pagination": {"pageSize": 10, "pageNumber": 1, "totalNumber": 3},
            "resourceId": "LO00001",
            "resourceName": "DragonPass Club",
            "optionList": [
                {
                    "optionId": "LO00001-01",
                    "optionName": "5% discount",
                    "marketingTag": ["2"],
                    "validity": {
                        "type": 1,
                        "startTime": "2026-04-01T00:00:00+00:00",
                        "endTime": "2027-04-01T00:00:00+00:00",
                    },
                },
                {
                    "optionId": "LO00001-02",
                    "optionName": "free drink",
                    "marketingTag": ["1"],
                    "validity": {"type": 2, "value": 30, "unit": "DAY"},
                },
                {
                    "optionId": "LO00001-03",
                    "optionName": "dynamic offer",
                    "marketingTag": ["3", "4"],
                    "validity": {"type": 3},
                },
            ],
        },
    }


def test_LocalOffersOptions_Contract_SuccessBodySupportsAllValidityTypes(
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """契约：成功响应支持固定日期、相对时长、动态三种 validity 结构。"""
    body = BuildSuccessBodyWithValidityTypes()
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief="成功响应样例（三种 validity 分支）",
        resource_id="LO00001",
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        AssertLocalOfferOptionsSuccessContract(
            body,
            expected_resource_id="LO00001",
            expected_page_size=10,
            expected_page_number=1,
        )
        return "三种 validity（固定区间 / 相对时长 / 动态）均满足契约"

    RunAllureAssertionStep("断言：成功响应结构与 validity 分支", _Assert)


def test_LocalOffersOptions_Contract_ExceptionEnvelopeRequiresErrCodeAndMsg(
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """契约：异常示例 code=-1 时应包含 errCode 和 msg。"""
    body = {
        "code": -1,
        "msg": "Sorry, we're unable to retrieve the list at the moment. Please try again later.",
        "errCode": "500.020.016",
    }
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief="业务失败信封（code=-1）",
        resource_id="LO00001",
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
        response_status_line="HTTP 200（离线示例：网关 200 + 业务 code=-1）",
    )

    def _Assert() -> str:
        AssertLocalOfferOptionsBusinessFailure(body)
        return "code=-1 时含非空 errCode 与 msg"

    RunAllureAssertionStep("断言：失败信封 errCode/msg", _Assert)


def test_LocalOffersOptions_Contract_MarketingTagAllowsStringOrIntegerEnum(
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """兼容：MCP 写字符串枚举，canary 当前返回整数枚举。"""
    body = BuildSuccessBodyWithValidityTypes()
    body["data"]["optionList"][0]["marketingTag"] = [1, 2, 3, 4]
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief="marketingTag 整数枚举兼容",
        resource_id="LO00001",
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        AssertLocalOfferOptionsSuccessContract(body)
        return "marketingTag 允许字符串或整数形式的 1～4 枚举"

    RunAllureAssertionStep("断言：marketingTag 枚举兼容", _Assert)


@pytest.mark.parametrize(
    "path,match",
    [
        (("code",), "code"),
        (("data",), "data"),
        (("data", "pagination"), "pagination"),
        (("data", "resourceId"), "resourceId"),
        (("data", "resourceName"), "resourceName"),
        (("data", "optionList"), "optionList"),
        (("data", "optionList", 0, "optionId"), "optionId"),
        (("data", "optionList", 0, "optionName"), "optionName"),
        (("data", "optionList", 0, "marketingTag"), "marketingTag"),
        (("data", "optionList", 0, "validity"), "validity"),
        (("data", "optionList", 0, "validity", "type"), "validity.type"),
    ],
    ids=[
        "missing_code",
        "missing_data",
        "missing_pagination",
        "missing_resourceId",
        "missing_resourceName",
        "missing_optionList",
        "missing_optionId",
        "missing_optionName",
        "missing_marketingTag",
        "missing_validity",
        "missing_validity_type",
    ],
)
def test_LocalOffersOptions_Contract_MissingRequiredFieldsShouldFail(
    ScenarioSteps: AllureHttpScenarioSteps,
    path: tuple,
    match: str,
) -> None:
    """契约：OpenAPI required 字段缺失时必须失败。"""
    body = BuildSuccessBodyWithValidityTypes()
    _DeletePath(body, path)
    rid = _ResolveDisplayResourceId(body)
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief=f"缺字段回归：{match}",
        resource_id=rid,
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        with pytest.raises(AssertionError, match=match):
            AssertLocalOfferOptionsSuccessContract(body)
        return f"缺失 {match} 时 SuccessContract 抛 AssertionError"

    RunAllureAssertionStep(f"断言：缺 {match} 必失败", _Assert)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("pageSize_zero", "pageSize"),
        ("pageSize_101", "pageSize"),
        ("pageNumber_zero", "pageNumber"),
        ("pageNumber_101", "pageNumber"),
        ("totalNumber_negative", "totalNumber"),
        ("resourceId_empty", "resourceId"),
        ("resourceName_empty", "resourceName"),
        ("optionList_not_array", "optionList"),
        ("optionId_empty", "optionId"),
        ("optionName_empty", "optionName"),
    ],
)
def test_LocalOffersOptions_Contract_LengthAndRangeInvalidShouldFail(
    ScenarioSteps: AllureHttpScenarioSteps,
    mutation: str,
    match: str,
) -> None:
    """契约：分页范围、必填字符串空值和数组类型异常时必须失败。"""
    body = BuildSuccessBodyWithValidityTypes()
    data = body["data"]
    pagination = data["pagination"]
    first_item = data["optionList"][0]
    if mutation == "pageSize_zero":
        pagination["pageSize"] = 0
    elif mutation == "pageSize_101":
        pagination["pageSize"] = 101
    elif mutation == "pageNumber_zero":
        pagination["pageNumber"] = 0
    elif mutation == "pageNumber_101":
        pagination["pageNumber"] = 101
    elif mutation == "totalNumber_negative":
        pagination["totalNumber"] = -1
    elif mutation == "resourceId_empty":
        data["resourceId"] = ""
    elif mutation == "resourceName_empty":
        data["resourceName"] = ""
    elif mutation == "optionList_not_array":
        data["optionList"] = {}
    elif mutation == "optionId_empty":
        first_item["optionId"] = ""
    elif mutation == "optionName_empty":
        first_item["optionName"] = ""
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief=f"范围/长度非法：{mutation}",
        resource_id=_ResolveDisplayResourceId(body),
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        with pytest.raises(AssertionError, match=match):
            AssertLocalOfferOptionsSuccessContract(body)
        return f"mutation={mutation} 时契约断言拒绝"

    RunAllureAssertionStep(f"断言：{mutation} 必失败", _Assert)


@pytest.mark.parametrize(
    "body,match",
    [
        (
            {
                "code": 0,
                "data": {
                    "pagination": {"pageSize": 10, "pageNumber": 1, "totalNumber": 1},
                    "resourceId": "LO00001",
                    "resourceName": "DragonPass Club",
                    "optionList": [
                        {
                            "optionId": "LO00001-01",
                            "optionName": "invalid tag",
                            "marketingTag": ["9"],
                            "validity": {"type": 3},
                        }
                    ],
                },
            },
            "marketingTag",
        ),
        (
            {
                "code": 0,
                "data": {
                    "pagination": {"pageSize": 10, "pageNumber": 1, "totalNumber": 1},
                    "resourceId": "LO00001",
                    "resourceName": "DragonPass Club",
                    "optionList": [
                        {
                            "optionId": "LO00001-01",
                            "optionName": "invalid validity",
                            "marketingTag": ["1"],
                            "validity": {"type": 2, "value": 30, "unit": "WEEK"},
                        }
                    ],
                },
            },
            "unit",
        ),
    ],
)
def test_LocalOffersOptions_Contract_InvalidOptionShapeShouldFail(
    ScenarioSteps: AllureHttpScenarioSteps,
    body: Dict[str, Any],
    match: str,
) -> None:
    """契约：marketingTag / validity 枚举越界时必须失败。"""
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief=f"option 形状非法（期望命中 {match}）",
        resource_id=_ResolveDisplayResourceId(body),
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        with pytest.raises(AssertionError, match=match):
            AssertLocalOfferOptionsSuccessContract(body)
        return f"非法 option 字段（{match}）被拒绝"

    RunAllureAssertionStep(f"断言：非法 option（{match}）", _Assert)


@pytest.mark.parametrize(
    "validity,match",
    [
        ({"type": 4}, "validity.type"),
        ({"type": "2", "value": 30, "unit": "DAY"}, "validity.type"),
        ({"type": 1, "startTime": "", "endTime": "2027-04-01T00:00:00+00:00"}, "startTime"),
        ({"type": 1, "startTime": "2026-04-01T00:00:00+00:00", "endTime": ""}, "endTime"),
        ({"type": 2, "value": "30", "unit": "DAY"}, "value"),
        ({"type": 2, "value": 30, "unit": "WEEK"}, "unit"),
    ],
    ids=[
        "type_4",
        "type_string",
        "fixed_missing_startTime",
        "fixed_missing_endTime",
        "relative_value_string",
        "relative_unit_invalid",
    ],
)
def test_LocalOffersOptions_Contract_InvalidValidityShouldFail(
    ScenarioSteps: AllureHttpScenarioSteps,
    validity: Dict[str, Any],
    match: str,
) -> None:
    """契约：validity 非法枚举、缺失字段或类型错误时必须失败。"""
    body = BuildSuccessBodyWithValidityTypes()
    body["data"]["optionList"][0]["validity"] = validity
    AttachLocalOffersContractHttpStep(
        ScenarioSteps,
        brief=f"validity 非法（{match}）",
        resource_id="LO00001",
        query={"pageSize": 10, "pageNumber": 1},
        response_body=body,
    )

    def _Assert() -> str:
        with pytest.raises(AssertionError, match=match):
            AssertLocalOfferOptionsSuccessContract(body)
        return f"validity 异常时命中 {match}"

    RunAllureAssertionStep(f"断言：validity 非法（{match}）", _Assert)


def _DeletePath(obj: Dict[str, Any], path: tuple) -> None:
    """删除嵌套 dict/list 中的指定路径，用于构造缺字段契约样例。"""
    cur: Any = obj
    for key in path[:-1]:
        cur = cur[key]
    del cur[path[-1]]
