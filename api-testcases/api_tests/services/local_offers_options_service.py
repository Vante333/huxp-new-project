"""
Local Offers options 业务服务层。

封装 ``GET /v2/resources/localOffers/{resourceId}/options`` 的请求上下文、HTTP 发送与基础响应结构断言，
供 feature 与 smoke 用例复用，避免同一接口能力在多个测试文件中重复维护。

**Allure**：HTTP 步骤标题为 ``[Sxx] 步骤x · … · GET /v2/resources/localOffers/{resourceId}/options``，
同屏附件含 ``request_step_meta``、``request_meta``（headers 脱敏、query 写入 ``params``）、
``response_body_json`` / ``response_status``；断言请在用例侧配合 ``RunAllureAssertionStep``。
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

import allure
import pytest
import requests

from framework.config.runtime import InitializeRuntimeEnv, LoadRuntimeSettings
from framework.http.core import MaskHeadersForLog
from framework.reporting import (
    AttachAllureRequestMeta,
    AttachAllureResponseArtifacts,
    AttachJson,
    FormatAllureHttpStepTitle,
)


@dataclass(frozen=True)
class LocalOfferRequestContext:
    """Local Offers options 请求上下文。"""

    BaseUrl: str
    ProgramId: str
    ResourceId: str


def BuildLocalOfferRequestContext() -> LocalOfferRequestContext:
    """从分层环境变量构造 Local Offers options 请求上下文。"""
    InitializeRuntimeEnv()
    settings = LoadRuntimeSettings()
    base_url = settings.base_url.strip() or "https://developer-sandbox.dragonpass.com/api"
    program_id = os.getenv("DP_PROGRAM_ID", "").strip()
    resource_id = os.getenv("DP_LOCAL_OFFER_RESOURCE_ID", "").strip() or "LO00001"
    if not program_id:
        pytest.skip("缺少 DP_PROGRAM_ID，无法运行 Local Offers options 接口测试。")
    return LocalOfferRequestContext(BaseUrl=base_url, ProgramId=program_id, ResourceId=resource_id)


def BuildLocalOfferOptionsHeaders(
    *,
    token: str,
    program_id: str,
    include_program: bool = True,
    include_request_id: bool = True,
    include_content_type: bool = True,
) -> Dict[str, str]:
    """构造 Local Offers options 请求头。"""
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
    }
    if include_request_id:
        headers["X-Request-ID"] = str(uuid.uuid4())
    if include_program:
        headers["X-Program-ID"] = program_id
    if include_content_type:
        headers["Content-Type"] = "application/json"
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() != "omit":
        headers["x-version"] = x_version
    return headers


def SendGetLocalOfferOptions(
    *,
    ctx: LocalOfferRequestContext,
    token: str,
    headers_include_program: bool = True,
    headers_include_request_id: bool = True,
    headers_include_content_type: bool = True,
    resource_id_override: Optional[str] = None,
    query: Optional[Dict[str, Any]] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
) -> requests.Response:
    """
    发送 Local Offers options 请求。

    当提供 ``step_code`` / ``step_title``（通常来自 ``AllureHttpScenarioSteps.Next``）时，
    在 Allure 中输出与主线一致的步骤标题、``request_step_meta``、``request_meta``（含 query ``params``）、
    ``response_body_json`` / ``response_status``。
    """
    resource_id = resource_id_override if resource_id_override is not None else ctx.ResourceId
    path = f"/v2/resources/localOffers/{resource_id}/options"
    url = f"{ctx.BaseUrl.rstrip('/')}{path}"
    headers = BuildLocalOfferOptionsHeaders(
        token=token,
        program_id=ctx.ProgramId,
        include_program=headers_include_program,
        include_request_id=headers_include_request_id,
        include_content_type=headers_include_content_type,
    )
    params = dict(query or {})
    step_name = FormatAllureHttpStepTitle("GET", path, step_code=step_code, step_title=step_title)
    with allure.step(step_name):
        if step_code or step_title:
            AttachJson(
                "request_step_meta",
                {
                    "step_code": step_code,
                    "step_title": step_title,
                    "method": "GET",
                    "path": path,
                },
            )
        AttachAllureRequestMeta(
            url=url,
            method="GET",
            headers=MaskHeadersForLog(headers),
            json_body=None,
            params=params if params else None,
        )
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30.0)
        except requests.RequestException as exc:
            raise RuntimeError("请求 Local Offers options 失败") from exc
        AttachAllureResponseArtifacts(resp)
        return resp


def ParseJsonBody(response: requests.Response) -> Dict[str, Any]:
    """解析 JSON 响应，失败时给出可定位的 pytest 失败信息。"""
    try:
        body = response.json()
    except ValueError as exc:
        pytest.fail(f"响应不是 JSON: status={response.status_code}, body={response.text[:800]}, err={exc}")
    if not isinstance(body, dict):
        pytest.fail(f"响应根节点必须是对象: actual={type(body)!r}, body={body!r}")
    return body


def AssertLocalOfferOptionsSuccessShape(body: Dict[str, Any]) -> None:
    """断言 Local Offers options 业务成功响应的核心结构。"""
    AssertLocalOfferOptionsSuccessContract(body)


def AssertLocalOfferOptionsEnvelope(body: Mapping[str, Any]) -> int:
    """断言响应信封符合 OpenAPI ``code`` 契约，并返回业务 code。"""
    assert "code" in body, f"响应缺少 code 字段: {body!r}"
    code = body.get("code")
    assert code in (0, -1), f"code 仅允许 0/-1，实际={code!r}, body={body!r}"
    return int(code)


def AssertLocalOfferOptionsBusinessFailure(body: Mapping[str, Any]) -> None:
    """断言响应不是业务成功，并在 ``code=-1`` 时校验错误字段形态。"""
    code = AssertLocalOfferOptionsEnvelope(body)
    assert code != 0, f"预期业务失败，实际成功: {body!r}"
    if code == -1:
        assert isinstance(body.get("errCode"), str) and body.get("errCode"), f"失败响应应包含 errCode: {body!r}"
        assert isinstance(body.get("msg"), str) and body.get("msg"), f"失败响应应包含 msg: {body!r}"


def AssertLocalOfferOptionsRequestRejected(
    response: requests.Response,
    *,
    context: str,
) -> None:
    """断言异常请求未业务成功；兼容 HTTP 非 200 或 HTTP 200 + 业务失败两类网关行为。"""
    try:
        body = response.json()
    except ValueError:
        assert response.status_code >= 400, (
            f"{context} 应失败；非 JSON 响应只接受 HTTP 4xx/5xx，"
            f"实际 status={response.status_code}, body={response.text[:800]}"
        )
        return
    assert isinstance(body, dict), f"{context} 响应根节点必须为对象: status={response.status_code}, body={body!r}"
    if response.status_code == 200:
        AssertLocalOfferOptionsBusinessFailure(body)
        return
    assert response.status_code >= 400, f"{context} 应失败，实际 status={response.status_code}, body={body!r}"


def AssertLocalOfferOptionsSuccessContract(
    body: Mapping[str, Any],
    *,
    expected_resource_id: Optional[str] = None,
    expected_page_size: Optional[int] = None,
    expected_page_number: Optional[int] = None,
) -> None:
    """按 MCP OpenAPI 契约断言业务成功响应核心结构。"""
    code = AssertLocalOfferOptionsEnvelope(body)
    assert code == 0, f"预期业务成功 code=0，实际响应: {body!r}"
    data = body.get("data")
    assert isinstance(data, dict), f"code=0 时 data 必须为对象: {body!r}"
    for key in ("pagination", "resourceId", "resourceName", "optionList"):
        assert key in data, f"code=0 时 data 缺少字段 {key}: {data!r}"
    pagination = data.get("pagination")
    assert isinstance(pagination, dict), f"pagination 必须为对象: {data!r}"
    for key in ("pageSize", "pageNumber", "totalNumber"):
        assert key in pagination, f"pagination 缺少字段 {key}: {pagination!r}"
        assert isinstance(pagination.get(key), int), f"pagination.{key} 必须为整数: {pagination!r}"
    assert 1 <= pagination["pageSize"] <= 100, f"pageSize 超出契约范围: {pagination!r}"
    assert 1 <= pagination["pageNumber"] <= 100, f"pageNumber 超出契约范围: {pagination!r}"
    assert pagination["totalNumber"] >= 0, f"totalNumber 不应为负数: {pagination!r}"
    if expected_page_size is not None:
        assert pagination["pageSize"] == expected_page_size, f"pageSize 未按请求回显: {pagination!r}"
    if expected_page_number is not None:
        assert pagination["pageNumber"] == expected_page_number, f"pageNumber 未按请求回显: {pagination!r}"

    resource_id = data.get("resourceId")
    assert isinstance(resource_id, str) and resource_id, f"resourceId 必须为非空字符串: {data!r}"
    if expected_resource_id is not None:
        assert resource_id == expected_resource_id, f"resourceId 未按 path 回显: expected={expected_resource_id!r}, data={data!r}"
    assert isinstance(data.get("resourceName"), str) and data.get("resourceName"), f"resourceName 必须为非空字符串: {data!r}"
    option_list = data.get("optionList")
    assert isinstance(option_list, list), f"optionList 必须为数组: {data!r}"
    for idx, item in enumerate(option_list):
        AssertLocalOfferOptionItemContract(item, index=idx)


def AssertLocalOfferOptionItemContract(item: Any, *, index: int) -> None:
    """断言 ``optionList`` 单项符合 OpenAPI 契约。"""
    assert isinstance(item, dict), f"optionList[{index}] 必须为对象: {item!r}"
    assert isinstance(item.get("optionId"), str) and item.get("optionId"), f"optionList[{index}].optionId 异常: {item!r}"
    assert isinstance(item.get("optionName"), str) and item.get("optionName"), f"optionList[{index}].optionName 异常: {item!r}"
    marketing_tag = item.get("marketingTag")
    assert isinstance(marketing_tag, list), f"optionList[{index}].marketingTag 必须为数组: {item!r}"
    for tag in marketing_tag:
        assert str(tag) in ("1", "2", "3", "4"), f"optionList[{index}].marketingTag 枚举异常: {item!r}"
    AssertLocalOfferValidityContract(item.get("validity"), index=index)


def AssertLocalOfferValidityContract(validity: Any, *, index: int) -> None:
    """断言 ``validity`` 的三种 anyOf 结构。"""
    assert isinstance(validity, dict), f"optionList[{index}].validity 必须为对象: {validity!r}"
    type_value = validity.get("type")
    assert type_value in (1, 2, 3), f"optionList[{index}].validity.type 枚举异常: {validity!r}"
    if type_value == 1:
        assert isinstance(validity.get("startTime"), str) and validity.get("startTime"), f"type=1 缺 startTime: {validity!r}"
        assert isinstance(validity.get("endTime"), str) and validity.get("endTime"), f"type=1 缺 endTime: {validity!r}"
        return
    if type_value == 2:
        assert isinstance(validity.get("value"), int), f"type=2 缺整数 value: {validity!r}"
        assert validity.get("unit") in ("DAY", "MONTH", "YEAR"), f"type=2 unit 枚举异常: {validity!r}"
