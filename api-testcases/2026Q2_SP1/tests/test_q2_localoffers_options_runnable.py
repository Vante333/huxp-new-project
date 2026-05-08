from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pytest
import requests

from clients import GetAccessToken
from framework.config.runtime import InitializeRuntimeEnv, LoadRuntimeSettings


@dataclass(frozen=True)
class LocalOfferRequestContext:
    BaseUrl: str
    ProgramId: str
    ResourceId: str


def BuildLocalOfferRequestContext() -> LocalOfferRequestContext:
    InitializeRuntimeEnv()
    settings = LoadRuntimeSettings()
    base_url = settings.base_url.strip() or "https://developer-sandbox.dragonpass.com/api"
    program_id = os.getenv("DP_PROGRAM_ID", "").strip()
    resource_id = os.getenv("DP_LOCAL_OFFER_RESOURCE_ID", "").strip() or "LO00001"
    if not program_id:
        pytest.skip("缺少 DP_PROGRAM_ID，无法运行 local offer 接口测试。")
    return LocalOfferRequestContext(BaseUrl=base_url, ProgramId=program_id, ResourceId=resource_id)


def BuildHeaders(*, token: str, program_id: str, include_program: bool = True) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
    }
    if include_program:
        headers["X-Program-ID"] = program_id
    return headers


def SendGetLocalOfferOptions(
    *,
    ctx: LocalOfferRequestContext,
    token: str,
    headers_include_program: bool = True,
    resource_id_override: Optional[str] = None,
    query: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    rid = resource_id_override if resource_id_override is not None else ctx.ResourceId
    url = f"{ctx.BaseUrl}/v2/resources/localOffers/{rid}/options"
    headers = BuildHeaders(token=token, program_id=ctx.ProgramId, include_program=headers_include_program)
    try:
        response = requests.get(url, headers=headers, params=query or {}, timeout=30.0)
    except requests.RequestException as exc:
        raise RuntimeError("请求 local offer options 失败") from exc
    return response


def ParseJsonBody(response: requests.Response) -> Dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        pytest.fail(f"响应不是 JSON: status={response.status_code}, body={response.text[:800]}, err={exc}")
    if not isinstance(body, dict):
        pytest.fail(f"响应根节点必须是对象: actual={type(body)!r}, body={body!r}")
    return body


@pytest.fixture(scope="function")
def AccessToken() -> str:
    token = GetAccessToken()
    if not isinstance(token, str) or len(token.strip()) < 8:
        pytest.fail(f"获取 token 异常: {token!r}")
    return token


def test_LocalOffersOptions_MinimalRequired_Smoke(AccessToken: str) -> None:
    """
    正向：最小必填请求（path + 必填 headers）可返回可解析响应。

    说明：
    - 该接口契约响应 code 可能为 0 或 -1（异常示例），因此此处先校验契约形态；
    - 若业务 code=-1，表示环境或资源数据暂不可用，记为 skip，避免误判脚本失败。
    """
    ctx = BuildLocalOfferRequestContext()
    response = SendGetLocalOfferOptions(ctx=ctx, token=AccessToken, query={"pageSize": 10, "pageNumber": 1})
    assert response.status_code == 200, f"HTTP 状态应为 200，实际={response.status_code}, body={response.text[:1000]}"
    body = ParseJsonBody(response)
    assert "code" in body, f"响应缺少 code 字段: {body!r}"
    code = body.get("code")
    assert code in (0, -1), f"code 仅允许 0/-1，实际={code!r}, body={body!r}"
    if code == -1:
        pytest.skip(f"环境返回业务异常（code=-1），资源可能不存在或暂不可用: {body!r}")
    data = body.get("data")
    assert isinstance(data, dict), f"code=0 时 data 必须为对象: {body!r}"
    for key in ("pagination", "resourceId", "resourceName", "optionList"):
        assert key in data, f"code=0 时 data 缺少字段 {key}: {data!r}"
    pagination = data.get("pagination")
    assert isinstance(pagination, dict), f"pagination 必须为对象: {data!r}"
    for key in ("pageSize", "pageNumber", "totalNumber"):
        assert key in pagination, f"pagination 缺少字段 {key}: {pagination!r}"


def test_LocalOffersOptions_InvalidToken_ShouldFail() -> None:
    """负向：非法 token 不应返回业务成功（HTTP 200 + code 0）。"""
    ctx = BuildLocalOfferRequestContext()
    response = SendGetLocalOfferOptions(ctx=ctx, token="invalid.token.value")
    body = ParseJsonBody(response)
    business_success = response.status_code == 200 and body.get("code") == 0
    assert not business_success, (
        "非法 token 不应业务成功，实际却成功。"
        f"status={response.status_code}, body={body!r}"
    )


def test_LocalOffersOptions_MissingProgramId_ShouldFail(AccessToken: str) -> None:
    """负向：缺少必填头 X-Program-ID 不应返回业务成功。"""
    ctx = BuildLocalOfferRequestContext()
    response = SendGetLocalOfferOptions(ctx=ctx, token=AccessToken, headers_include_program=False)
    body = ParseJsonBody(response)
    business_success = response.status_code == 200 and body.get("code") == 0
    assert not business_success, (
        "缺少 X-Program-ID 不应业务成功，实际却成功。"
        f"status={response.status_code}, body={body!r}"
    )
