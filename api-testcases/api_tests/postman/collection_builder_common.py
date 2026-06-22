"""
Postman Collection v2.1 构建公共组件（RequestItem / Folder / Headers 等）。

供 ``GeneratePostmanCollection*Epass.py`` 生成器复用。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def SaveTokenLines() -> List[str]:
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) { pm.collectionVariables.set('accessToken', t); }",
        "} catch (e) { console.warn(e); }",
    ]


def MakeTestEvent(
    js_helpers: Callable[[], List[str]],
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(js_helpers())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def MakePreRequestEvent(
    js_helpers: Callable[[], List[str]],
    lines: Sequence[str],
) -> List[JsonObject]:
    exec_lines: List[str] = []
    exec_lines.extend(js_helpers())
    exec_lines.extend(list(lines))
    return [{"listen": "prerequest", "script": {"exec": exec_lines, "type": "text/javascript"}}]


def AuthJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def PostmanUrl(url_path: str, query: Optional[Dict[str, str]] = None) -> JsonObject:
    """构建 Postman URL；支持 ``url.query``（Apifox/Postman 才会带上 module 等参数）。"""
    path_only = url_path.split("?", 1)[0]
    merged_query: Dict[str, str] = {}
    if "?" in url_path:
        for part in url_path.split("?", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                merged_query[key] = value
    if query:
        merged_query.update({str(k): str(v) for k, v in query.items()})
    path_parts: List[str] = [part for part in path_only.split("/") if part]
    raw = "{{baseUrl}}/" + "/".join(path_parts)
    url_obj: JsonObject = {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}
    if merged_query:
        url_obj["query"] = [{"key": k, "value": v} for k, v in merged_query.items()]
        url_obj["raw"] = raw + "?" + "&".join(f"{k}={v}" for k, v in merged_query.items())
    return url_obj


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    return {"key": key, "value": value, "type": "string"}


def RequestItem(
    *,
    js_helpers: Callable[[], List[str]],
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    test_lines: Optional[Sequence[str]] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)
    out: JsonObject = {"name": name, "request": req}
    events: List[JsonObject] = []
    if prerequest_lines:
        events.extend(MakePreRequestEvent(js_helpers, prerequest_lines))
    events.extend(MakeTestEvent(js_helpers, save_token=save_token, extra_lines=test_lines))
    if events:
        out["event"] = events
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def Lines_Step(_label: str, fn_calls: Sequence[str]) -> List[str]:
    return list(fn_calls)


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    """
    Apifox/Postman 列表展示名：业务目的前置，便于在自动化场景中识别每条请求验证什么。

    格式：``【目的】| 步骤号 | METHOD 路径简写``
    """
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def WriteCollectionJson(out_path: str, payload: JsonObject) -> None:
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
