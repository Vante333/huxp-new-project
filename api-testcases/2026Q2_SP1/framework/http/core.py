from __future__ import annotations

import os
import time
import uuid
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

import allure
import requests
from requests import Response

from framework.config import InitializeRuntimeEnv
from framework.reporting import (
    AttachAllureRequestMeta,
    AttachAllureResponseArtifacts,
    AttachJson,
    FormatAllureHttpStepTitle,
    JsonDict,
)

AfterResponseHook = Callable[[Response], None]

_DEFAULT_BASE = "https://developer-sandbox.dragonpass.com/api"


def GetBaseUrl() -> str:
    InitializeRuntimeEnv()
    raw = os.getenv("DP_BASE_URL", _DEFAULT_BASE).strip()
    if raw.endswith("/api"):
        return raw.rstrip("/")
    if raw.rstrip("/").endswith("dragonpass.com"):
        return raw.rstrip("/") + "/api"
    return raw.rstrip("/")


def GetProgramId() -> str:
    InitializeRuntimeEnv()
    program_id = os.getenv("DP_PROGRAM_ID", "").strip()
    if not program_id:
        raise RuntimeError("缺少环境变量 DP_PROGRAM_ID")
    return program_id


def GetClientId() -> str:
    InitializeRuntimeEnv()
    client_id = os.getenv("DP_CLIENT_ID", "").strip()
    if not client_id:
        raise RuntimeError("缺少环境变量 DP_CLIENT_ID")
    return client_id


def GetClientSecret() -> str:
    InitializeRuntimeEnv()
    client_secret = os.getenv("DP_CLIENT_SECRET", "").strip()
    if not client_secret:
        raise RuntimeError("缺少环境变量 DP_CLIENT_SECRET")
    return client_secret


def GetMembershipsExtensionsHttpMethod() -> str:
    raw = os.getenv("DP_MEMBERSHIP_EXTENSIONS_METHOD", "").strip().upper()
    return raw if raw in ("POST", "PATCH") else "PATCH"


def MembershipsExtensionsHttpContextLabel() -> str:
    return f"{GetMembershipsExtensionsHttpMethod()} /v2/memberships/extensions"


def BuildNextRequestId() -> str:
    return f"{int(time.time() * 1000)}-{uuid.uuid4()}"


def MaskHeadersForLog(headers: Mapping[str, str]) -> Dict[str, str]:
    out = dict(headers)
    for key in list(out.keys()):
        if key.lower() in ("authorization", "x-api-key"):
            out[key] = "***"
    return out


def BuildCommonHeaders(token: Optional[str] = None, *, x_program_id: Optional[str] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "X-Request-ID": BuildNextRequestId(),
        "X-Program-ID": x_program_id or GetProgramId(),
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    x_version = os.getenv("DP_X_VERSION", "").strip()
    if x_version and x_version.lower() != "omit":
        headers["x-version"] = x_version
    return headers


def RequestWithAllure(
    method: str,
    path: str,
    *,
    token: Optional[str] = None,
    json_body: Optional[JsonDict] = None,
    after_response: Optional[AfterResponseHook] = None,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    timeout_sec: float = 30.0,
    x_program_id: Optional[str] = None,
) -> Response:
    url = GetBaseUrl() + path
    headers = BuildCommonHeaders(token=token, x_program_id=x_program_id)
    step_name = FormatAllureHttpStepTitle(
        method,
        path,
        step_code=step_code,
        step_title=step_title,
    )
    with allure.step(step_name):
        if step_code or step_title:
            AttachJson(
                "request_step_meta",
                {
                    "step_code": step_code,
                    "step_title": step_title,
                },
            )
        AttachAllureRequestMeta(
            url=url,
            method=method,
            headers=MaskHeadersForLog(headers),
            json_body=json_body,
        )
        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=headers,
            json=json_body,
            timeout=timeout_sec,
        )
        AttachAllureResponseArtifacts(resp)
        if after_response is not None:
            after_response(resp)
        return resp


def ParseResponseEnvelope(resp: Response) -> Tuple[int, Optional[JsonDict], Any]:
    try:
        payload = resp.json()
    except ValueError:
        return resp.status_code, None, None
    if isinstance(payload, dict):
        inner = payload.get("data")
        return resp.status_code, payload, inner
    return resp.status_code, None, payload


def ChainAfterResponse(*hooks: Optional[AfterResponseHook]) -> AfterResponseHook:
    def _Run(resp: Response) -> None:
        for hook in hooks:
            if hook is not None:
                hook(resp)

    return _Run
