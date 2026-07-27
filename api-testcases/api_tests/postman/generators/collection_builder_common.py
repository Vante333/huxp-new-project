"""
Postman Collection v2.1 构建公共组件（RequestItem / Folder / Headers 等）。

供 ``generators/GeneratePostmanCollection*.py`` 复用。

目录约定（``postman/`` 按角色拆分）::

    generators/   正本（本文件与 Generate*.py）
    collections/  可审集合 JSON（提交）
    envs/         环境模板
    docs/         协作说明
    generated/    本地中间件（gitignore；勿当正本）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"


def PostmanRootDir() -> Path:
    """``api-testcases/api_tests/postman`` 根目录。"""
    here = Path(__file__).resolve().parent
    if here.name == "generators":
        return here.parent
    return here


def CollectionsDir() -> Path:
    path = PostmanRootDir() / "collections"
    path.mkdir(parents=True, exist_ok=True)
    return path


def EnvsDir() -> Path:
    path = PostmanRootDir() / "envs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def DocsDir() -> Path:
    return PostmanRootDir() / "docs"


def GeneratedDir() -> Path:
    """本地中间件（Apifox 导入包等）；默认 gitignore。"""
    path = PostmanRootDir() / "generated"
    path.mkdir(parents=True, exist_ok=True)
    return path


def CollectionPath(file_name: str) -> Path:
    return CollectionsDir() / file_name


def EnvPath(file_name: str) -> Path:
    return EnvsDir() / file_name


def GeneratedArtifactPath(file_name: str) -> Path:
    return GeneratedDir() / file_name


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


def CollectionVariable(key: str, value: str, description: str = "") -> JsonObject:
    item: JsonObject = {"key": key, "value": value, "type": "string"}
    if description:
        item["description"] = description
    return item


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


def WriteCollectionJson(out_path: Union[str, Path], payload: JsonObject) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
