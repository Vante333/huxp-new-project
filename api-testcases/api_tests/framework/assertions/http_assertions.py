from __future__ import annotations

from typing import Any, Optional

from requests import Response

from framework.reporting import JsonDict


def IsHttpOk(resp: Response) -> bool:
    return 200 <= resp.status_code < 300


def IsBusinessSuccess(envelope: Optional[JsonDict]) -> bool:
    if envelope is None:
        return False
    if "code" not in envelope:
        return True
    code = envelope.get("code")
    return code == 0 or code == "0"


def AssertHttpAndBusinessOk(
    resp: Response,
    envelope: Optional[JsonDict],
    *,
    context: str = "HTTP",
) -> None:
    assert IsHttpOk(resp), f"{context}: HTTP 失败，status={resp.status_code}, body={resp.text[:4000]}"
    assert IsBusinessSuccess(envelope), f"{context}: 业务失败，body={envelope!r}"


def AssertJsonResponse(resp: Response) -> JsonDict:
    try:
        payload: Any = resp.json()
    except ValueError as exc:
        raise AssertionError(f"响应不是合法 JSON: {resp.text[:4000]}") from exc
    assert isinstance(payload, dict), f"响应根类型应为 dict，实际={type(payload).__name__}"
    return payload
