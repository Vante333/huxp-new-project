"""
将 ``*.apifox-2.7.43-import.json`` 中的步骤（含 postProcessors）CLI 写入已有场景。

背景：私有化 ``import --format apifox`` 可能只创建场景元数据而 ``steps=[]``；
本工具用 ``test-scenario update --file`` 补全步骤，实现后置 Tests 全量 CLI 化。

用法::

    python tools/apifox-cli/PushApifoxScenarioSteps.py ^
      --project 346275 ^
      --scenario-id 365969 ^
      --api-base-url https://apifox.dragonpass.com.cn ^
      --package apifox-reports/papi_2548/generated/PAPI-2548-membership-extensions.apifox-2.7.43-import.json
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

JsonObject = Dict[str, Any]


def FindApifoxCmd() -> str:
    candidates = [
        Path(os.environ.get("APPDATA", "")) / "npm" / "apifox.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "apifox",
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    return "apifox"


def ParseApifoxCliJson(text: str) -> JsonObject:
    """CLI 常在 JSON 前打印 emoji 提示，取第一段 JSON 对象。"""
    raw = (text or "").strip()
    if not raw:
        raise RuntimeError("apifox empty output")
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    if start < 0:
        raise RuntimeError(f"apifox non-JSON: {raw[:800]}")
    decoder = json.JSONDecoder()
    try:
        payload, _ = decoder.raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"apifox non-JSON: {raw[:800]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"apifox JSON is not an object: {type(payload)}")
    return payload


def RunApifoxJson(args: Sequence[str], *, api_base_url: str, token: str) -> JsonObject:
    cmd = [
        FindApifoxCmd(),
        "--api-base-url",
        api_base_url,
        "--access-token",
        token,
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "").strip()
    if not text:
        text = (proc.stderr or "").strip()
    try:
        payload = ParseApifoxCliJson(text)
    except RuntimeError as exc:
        raise RuntimeError(f"apifox non-JSON (exit={proc.returncode}): {text[:800]}") from exc
    if proc.returncode != 0 or payload.get("success") is False:
        raise RuntimeError(f"apifox failed: {payload.get('error') or payload}")
    return payload


def ExtractImportScenarioItem(package: Mapping[str, Any]) -> JsonObject:
    collections = package.get("apiTestCaseCollection")
    if not isinstance(collections, list):
        raise ValueError("package missing apiTestCaseCollection")
    for col in collections:
        if not isinstance(col, dict):
            continue
        for item in col.get("items") or []:
            if not isinstance(item, dict):
                continue
            steps = item.get("steps")
            if isinstance(steps, list) and steps:
                return dict(item)
    raise ValueError("no steps found in package")


def ExtractImportSteps(package: Mapping[str, Any]) -> List[JsonObject]:
    item = ExtractImportScenarioItem(package)
    steps = item.get("steps")
    if not isinstance(steps, list):
        raise ValueError("scenario item steps is not a list")
    return [dict(s) for s in steps if isinstance(s, dict)]


def NormalizeCustomHttpBody(request_body: Any) -> JsonObject:
    """客户端导入形 body → customHttpRequest.requestBody。"""
    if not isinstance(request_body, dict):
        return {"type": "none", "data": ""}
    raw_type = str(request_body.get("type") or "none")
    data = request_body.get("data")
    data_s = "" if data is None else str(data)
    if raw_type in ("application/json", "json"):
        return {"type": "json", "data": data_s}
    if raw_type in ("raw", "text/plain"):
        return {"type": "raw", "data": data_s}
    if data_s.strip():
        return {"type": "json", "data": data_s}
    return {"type": "none", "data": ""}


def NormalizeRelPath(raw_path: str) -> str:
    """``{{baseUrl}}/v2/...`` 或完整 URL → ``/v2/...``。"""
    text = str(raw_path or "").strip()
    if "{{baseUrl}}" in text:
        text = text.split("{{baseUrl}}", 1)[-1]
    if "://" in text:
        text = "/" + "/".join(text.split("://", 1)[-1].split("/")[1:])
    if not text.startswith("/"):
        text = "/" + text
    return text.split("?")[0] or "/"


def EndpointMapKey(method: str, path: str) -> str:
    return f"{str(method or '').upper()} {NormalizeRelPath(path)}"


def CaseMethodPath(step: Mapping[str, Any]) -> Optional[Tuple[str, str]]:
    case = step.get("httpApiCase")
    if not isinstance(case, dict):
        return None
    method = str(case.get("method") or "get").lower()
    rel_path = NormalizeRelPath(str(case.get("path") or "/"))
    return method, rel_path


def CollectHttpMethodPaths(steps: Sequence[Mapping[str, Any]]) -> List[Tuple[str, str]]:
    """展开 group/forEach，收集唯一 METHOD+path。"""
    seen: Dict[str, Tuple[str, str]] = {}

    def Walk(items: Sequence[Mapping[str, Any]]) -> None:
        for step in items:
            if not isinstance(step, dict):
                continue
            children = step.get("children")
            if str(step.get("type") or "").strip().lower() in ("group", "foreach") and isinstance(children, list):
                Walk(children)
                continue
            pair = CaseMethodPath(step)
            if pair is None:
                continue
            seen[EndpointMapKey(pair[0], pair[1])] = pair

    Walk(steps)
    return list(seen.values())


def IsAuthTokenPath(path: str) -> bool:
    return NormalizeRelPath(path).rstrip("/") == "/v2/auth/token"


def StandardDocHeaders(*, with_auth: bool) -> List[JsonObject]:
    """写入接口文档的 Header 示例，绑定后「接口运行」才能显示参数值。"""
    rows: List[JsonObject] = [
        {"name": "X-Program-ID", "required": True, "enable": True, "example": "{{ProgramID}}", "type": "string"},
        {"name": "x-version", "required": False, "enable": True, "example": "{{x-version}}", "type": "string"},
        {"name": "X-Request-ID", "required": True, "enable": True, "example": "{{$string.uuid}}", "type": "string"},
    ]
    if with_auth:
        rows.append(
            {
                "name": "Authorization",
                "required": True,
                "enable": True,
                "example": "Bearer {{accessToken}}",
                "type": "string",
            }
        )
    rows.append(
        {"name": "Content-Type", "required": False, "enable": True, "example": "application/json", "type": "string"}
    )
    return rows


def ListEndpointMap(
    *,
    project_id: int,
    branch: str,
    api_base_url: str,
    token: str,
) -> Dict[str, int]:
    cmd = ["endpoint", "list", "--project", str(project_id)]
    if branch:
        cmd.extend(["--branch", branch])
    payload = RunApifoxJson(cmd, api_base_url=api_base_url, token=token)
    data = payload.get("data")
    items: Sequence[Any]
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        raw_items = data.get("items") or data.get("list") or data.get("endpoints") or []
        items = raw_items if isinstance(raw_items, list) else []
    else:
        items = []
    out: Dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        endpoint_id = item.get("id")
        if not isinstance(endpoint_id, int) or endpoint_id <= 0:
            continue
        method = str(item.get("method") or "")
        path = str(item.get("path") or "")
        out[EndpointMapKey(method, path)] = endpoint_id
    return out


def CreateEndpoint(
    *,
    project_id: int,
    branch: str,
    method: str,
    path: str,
    api_base_url: str,
    token: str,
) -> int:
    """在当前工作分支创建最小接口文档（含 Header 示例），供场景 bind。"""
    payload: JsonObject = {
        "name": f"{method.upper()} {path}",
        "type": "http",
        "method": method.lower(),
        "path": path,
        "status": "testing",
        "description": "Repo-first 绑定用接口文档；场景步骤 syncMode=MANUAL，可解绑。",
        "parameters": {
            "header": StandardDocHeaders(with_auth=not IsAuthTokenPath(path)),
        },
        "requestBody": {"type": "none"} if method.lower() in ("get", "head") else {"type": "application/json"},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False)
        tmp_path = handle.name
    try:
        created = RunApifoxJson(
            [
                "endpoint",
                "create",
                "--project",
                str(project_id),
                "--branch",
                branch,
                "--file",
                tmp_path,
            ],
            api_base_url=api_base_url,
            token=token,
        )
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
    data = created.get("data")
    endpoint_id = data.get("id") if isinstance(data, dict) else None
    if not isinstance(endpoint_id, int) or endpoint_id <= 0:
        raise RuntimeError(f"endpoint create 未返回 id: {created}")
    print(f"created endpoint {endpoint_id} {method.upper()} {path} on {branch}")
    return endpoint_id


def EnsureEndpointIds(
    needed: Sequence[Tuple[str, str]],
    *,
    project_id: int,
    branch: str,
    api_base_url: str,
    token: str,
) -> Dict[str, int]:
    """按 METHOD+path 解析真实 apiDetailId；当前分支没有则创建。禁止回落 0。"""
    mapping = ListEndpointMap(project_id=project_id, branch=branch, api_base_url=api_base_url, token=token)
    for method, path in needed:
        key = EndpointMapKey(method, path)
        if mapping.get(key, 0) > 0:
            continue
        mapping[key] = CreateEndpoint(
            project_id=project_id,
            branch=branch,
            method=method,
            path=path,
            api_base_url=api_base_url,
            token=token,
        )
    missing = [EndpointMapKey(m, p) for m, p in needed if mapping.get(EndpointMapKey(m, p), 0) <= 0]
    if missing:
        raise RuntimeError("无法绑定：缺少真实接口 ID（禁止 apiDetailId=0）: " + ", ".join(missing))
    return mapping


def HeaderRowValue(row: Mapping[str, Any]) -> str:
    """取运行表可用的 header 值：优先 ``value``，再 ``sampleValue`` / ``example``。"""
    raw = row.get("value")
    text = "" if raw is None else str(raw)
    if text.strip():
        return text
    sample = row.get("sampleValue")
    if sample is not None and str(sample).strip():
        return str(sample)
    example = row.get("example")
    if example is None:
        schema = row.get("schema")
        if isinstance(schema, dict):
            example = schema.get("example")
            if example is None:
                example = schema.get("default")
    return "" if example is None else str(example)


def UiUnbindHeaderRows(case: Mapping[str, Any]) -> List[JsonObject]:
    """对齐 Apifox UI「解绑」写出的 header：``name`` + ``value`` + ``sampleValue``。"""
    rows: List[JsonObject] = []
    for item in CaseHeaderRows(case):
        name = str(item.get("name") or item.get("key") or "").strip()
        if not name:
            continue
        value = str(item.get("value") or "")
        row: JsonObject = {
            "name": name,
            "value": value,
            "sampleValue": value,
            "enable": True,
        }
        if item.get("disabled") is True or item.get("enable") is False:
            row["enable"] = False
        rows.append(row)
    return rows


def CaseHeaderRows(case: Mapping[str, Any]) -> List[JsonObject]:
    parameters = case.get("parameters") if isinstance(case.get("parameters"), dict) else {}
    header = parameters.get("header") if isinstance(parameters.get("header"), list) else []
    rows: List[JsonObject] = []
    for row in header:
        if not isinstance(row, dict):
            continue
        key = str(row.get("key") or row.get("name") or "").strip()
        if not key:
            continue
        item: JsonObject = {"key": key, "name": key, "value": HeaderRowValue(row), "enable": True}
        if row.get("disabled") is True or row.get("enable") is False:
            item["enable"] = False
            item["disabled"] = True
        rows.append(item)
    return rows


def StepDisplayName(step: Mapping[str, Any]) -> str:
    """读取步骤展示名（customHttp / httpApiCase / group 兼容）。"""
    step_type = str(step.get("type") or "").strip().lower()
    if step_type == "group":
        params = step.get("parameters")
        if isinstance(params, dict):
            gname = str(params.get("name") or "").strip()
            if gname:
                return gname
    name = str(step.get("name") or "").strip()
    if name:
        return name
    case = step.get("httpApiCase")
    if isinstance(case, dict):
        return str(case.get("name") or "").strip()
    custom = step.get("customHttpRequest")
    if isinstance(custom, dict):
        return str(custom.get("name") or "").strip()
    return ""


def FlattenHttpStepNames(steps: Sequence[Mapping[str, Any]]) -> List[str]:
    """递归展开 group/forEach/loop.children，仅收集 HTTP/customHttp 叶节点名（目的前置校验用）。"""
    names: List[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_type = str(step.get("type") or "").strip().lower()
        children = step.get("children")
        if step_type in ("group", "foreach", "loop") and isinstance(children, list):
            names.extend(FlattenHttpStepNames(children))
            continue
        if step_type in ("http", "customhttp", "") or step.get("httpApiCase") or step.get(
            "customHttpRequest"
        ):
            name = StepDisplayName(step)
            if name:
                names.append(name)
    return names


def AssertPurposeFirstNames(names: Sequence[str], *, context: str) -> None:
    """校验目的前置：``【中文目的】| 步骤ID | METHOD ...``。"""
    if not names:
        raise RuntimeError(f"{context}: 步骤名为空")
    bad: List[str] = []
    for index, name in enumerate(names, start=1):
        if not name.startswith("【"):
            bad.append(f"#{index} 未以【开头: {name}")
            continue
        if "】| " not in name:
            bad.append(f"#{index} 缺少 】| 分隔: {name}")
            continue
        purpose = name.split("】| ", 1)[0].lstrip("【").strip()
        if not purpose:
            bad.append(f"#{index} 目的为空: {name}")
            continue
        # 目的段不应再出现旧式 pytest 函数名
        if "test_" in purpose or purpose.startswith("R0") or purpose.startswith("POST /"):
            bad.append(f"#{index} 目的仍像旧命名: {name}")
    if bad:
        preview = "\n".join(bad[:12])
        raise RuntimeError(f"{context}: 目的前置命名校验失败 ({len(bad)}):\n{preview}")


def VerifyRemoteMatchesExpected(
    *,
    expected_names: Sequence[str],
    remote_steps: Sequence[Mapping[str, Any]],
) -> None:
    """推送后：叶 HTTP 条数一致 + 远程名目的前置 + 与包内期望名一致。"""
    remote_names = FlattenHttpStepNames(remote_steps)
    print(f"verify steps_len={len(remote_names)} expected={len(expected_names)}")
    AssertPurposeFirstNames(expected_names, context="package")
    AssertPurposeFirstNames(remote_names, context="remote")
    if len(remote_names) != len(expected_names):
        raise RuntimeError(
            f"步骤条数不一致: remote={len(remote_names)} expected={len(expected_names)}"
        )
    mismatches: List[str] = []
    for index, (exp, got) in enumerate(zip(expected_names, remote_names), start=1):
        if exp != got:
            mismatches.append(f"#{index}\n  expect: {exp}\n  remote: {got}")
    if mismatches:
        preview = "\n".join(mismatches[:8])
        raise RuntimeError(f"远程步骤名未刷新为最新 ({len(mismatches)}):\n{preview}")
    print("verify purpose-first names: OK")
    for index, name in enumerate(remote_names[:5], start=1):
        print(f"  sample[{index}] {name}")
    if len(remote_names) > 5:
        print(f"  ... +{len(remote_names) - 5} more")


def ToCliHttpStep(step: Mapping[str, Any], *, project_id: int, index: int) -> Optional[JsonObject]:
    """单条 HTTP 导入步 → customHttp。"""
    case = step.get("httpApiCase")
    if not isinstance(case, dict):
        return None
    method = str(case.get("method") or "get").lower()
    rel_path = str(case.get("path") or "/")
    if not rel_path.startswith("/"):
        rel_path = "/" + rel_path
    # customHttp 的 path 用带 baseUrl 的完整形态，便于环境切换
    path = "{{baseUrl}}" + rel_path
    name = str(step.get("name") or case.get("name") or f"step-{index}")
    pre = case.get("preProcessors") if isinstance(case.get("preProcessors"), list) else []
    post = case.get("postProcessors") if isinstance(case.get("postProcessors"), list) else []
    for proc in list(pre) + list(post):
        if isinstance(proc, dict) and "id" not in proc:
            proc["id"] = f"step{index}-{proc.get('type', 'script')}"

    parameters = case.get("parameters") if isinstance(case.get("parameters"), dict) else {}
    query = parameters.get("query") if isinstance(parameters.get("query"), list) else []
    cookie = parameters.get("cookie") if isinstance(parameters.get("cookie"), list) else []
    path_params = parameters.get("path") if isinstance(parameters.get("path"), list) else []

    # 私有化 customHttp 偶发不带 parameters.query：把启用中的 query 拼进 path，保证运行时生效
    if query and "?" not in path:
        pairs: List[str] = []
        for row in query:
            if not isinstance(row, dict):
                continue
            if row.get("enable") is False or row.get("isDelete") is True:
                continue
            qname = str(row.get("name") or row.get("key") or "").strip()
            if not qname:
                continue
            qval = str(row.get("value", ""))
            pairs.append(f"{qname}={qval}")
        if pairs:
            path = path + "?" + "&".join(pairs)

    postman_header: List[JsonObject] = []
    run_headers = CaseHeaderRows(case)
    for row in run_headers:
        item: JsonObject = {"key": str(row.get("key") or ""), "value": str(row.get("value", ""))}
        if row.get("disabled") is True or row.get("enable") is False:
            item["disabled"] = True
        postman_header.append(item)

    custom_req: JsonObject = {
        "id": 0,
        "name": name,
        "path": path,
        "method": method,
        "folderId": 0,
        # 与可显示的 Apifox CLI 导出一致：顶层 header 用 Postman key/value
        "header": postman_header,
        "parameters": {
            "path": path_params,
            "query": query,
            "header": run_headers,
            "cookie": cookie,
        },
        "requestBody": NormalizeCustomHttpBody(case.get("requestBody")),
        "preProcessors": pre,
        "postProcessors": post,
        "auth": {},
        "advancedSettings": {},
        "commonParameters": {},
        "projectId": project_id,
    }
    return {
        "id": f"step-{index}",
        "name": name,
        "type": "customHttp",
        "disable": False,
        "ordering": index,
        "customHttpRequest": custom_req,
    }


def IsBoundHttpLeaf(step: Mapping[str, Any]) -> bool:
    """UI「已关联接口文档」：``type=http`` 且 ``bindType=API`` 或 ``bindId>0``。"""
    if str(step.get("type") or "").strip().lower() != "http":
        return False
    try:
        bind_id = int(step.get("bindId") or 0)
    except (TypeError, ValueError):
        bind_id = 0
    return str(step.get("bindType") or "") == "API" or bind_id > 0


def HttpCaseToUnboundCustomHttpStep(
    step: Mapping[str, Any],
    case: Mapping[str, Any],
    *,
    project_id: int,
    index: int,
) -> JsonObject:
    """绑定 http 步 → 独立 customHttp，对齐 UI「解绑」：相对 path + sampleValue。"""
    method = str(case.get("method") or "get").strip().lower()
    path = NormalizeRelPath(str(case.get("path") or "/"))
    name = str(step.get("name") or case.get("name") or f"step-{index}")
    parameters = case.get("parameters") if isinstance(case.get("parameters"), dict) else {}
    query = parameters.get("query") if isinstance(parameters.get("query"), list) else []
    cookie = parameters.get("cookie") if isinstance(parameters.get("cookie"), list) else []
    path_params = parameters.get("path") if isinstance(parameters.get("path"), list) else []
    header_rows = UiUnbindHeaderRows(case)
    if query and "?" not in path:
        pairs: List[str] = []
        for row in query:
            if not isinstance(row, dict):
                continue
            if row.get("enable") is False or row.get("isDelete") is True:
                continue
            qname = str(row.get("name") or row.get("key") or "").strip()
            if not qname:
                continue
            pairs.append(f"{qname}={row.get('value', '')}")
        if pairs:
            path = path + "?" + "&".join(pairs)
    try:
        case_project = int(case.get("projectId") or 0)
    except (TypeError, ValueError):
        case_project = 0
    custom_req: JsonObject = {
        "id": 0,
        "name": name,
        "path": path,
        "method": method,
        "folderId": 0,
        "parameters": {
            "path": path_params,
            "query": query,
            "header": header_rows,
            "cookie": cookie,
        },
        "requestBody": NormalizeCustomHttpBody(case.get("requestBody")),
        "preProcessors": case.get("preProcessors") if isinstance(case.get("preProcessors"), list) else [],
        "postProcessors": case.get("postProcessors") if isinstance(case.get("postProcessors"), list) else [],
        "auth": case.get("auth") if isinstance(case.get("auth"), dict) else {},
        "advancedSettings": {},
        "commonParameters": {},
        "projectId": case_project if case_project > 0 else project_id,
    }
    out: JsonObject = {
        "id": str(step.get("id") or f"step-{index}"),
        "name": name,
        "type": "customHttp",
        "disable": bool(step.get("disable")),
        "ordering": int(step.get("ordering") or index),
        "parameters": {},
        "customHttpRequest": custom_req,
    }
    if "number" in step:
        out["number"] = step.get("number")
    return out


def UnbindHttpStepsToCustomHttp(steps: List[Any], *, project_id: int) -> int:
    """递归把绑定 ``type=http`` 解绑为独立 ``customHttp``，Headers 用运行表字段。"""
    unbound = 0

    def Walk(items: List[Any]) -> None:
        nonlocal unbound
        for index, step in enumerate(items, start=1):
            if not isinstance(step, dict):
                continue
            children = step.get("children")
            if isinstance(children, list):
                Walk(children)
            if not IsBoundHttpLeaf(step):
                continue
            case = step.get("httpApiCase")
            if not isinstance(case, dict):
                raise RuntimeError("解绑失败：http 步缺少 httpApiCase")
            converted = HttpCaseToUnboundCustomHttpStep(
                step, case, project_id=project_id, index=index
            )
            step.clear()
            step.update(converted)
            unbound += 1

    Walk(steps)
    return unbound


def CountCustomHttpLeaves(steps: Sequence[Mapping[str, Any]]) -> int:
    count = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        children = step.get("children")
        step_type = str(step.get("type") or "").strip().lower()
        if step_type in ("group", "foreach", "loop") and isinstance(children, list):
            count += CountCustomHttpLeaves(children)
            continue
        if step_type == "customhttp":
            count += 1
    return count


def CountEmptyHeaderValueLeaves(steps: Sequence[Mapping[str, Any]]) -> int:
    empty = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        children = step.get("children")
        step_type = str(step.get("type") or "").strip().lower()
        if step_type in ("group", "foreach", "loop") and isinstance(children, list):
            empty += CountEmptyHeaderValueLeaves(children)
            continue
        case = step.get("httpApiCase")
        if not isinstance(case, dict):
            custom = step.get("customHttpRequest")
            case = custom if isinstance(custom, dict) else {}
        rows = CaseHeaderRows(case)
        if not rows:
            top_header = case.get("header") if isinstance(case.get("header"), list) else []
            rows = CaseHeaderRows({"parameters": {"header": top_header}})
        if not rows:
            continue
        if all(not str(row.get("value") or "").strip() for row in rows):
            empty += 1
    return empty


def CountBoundHttpLeaves(steps: Sequence[Mapping[str, Any]]) -> int:
    bound = 0
    for step in steps:
        if not isinstance(step, dict):
            continue
        children = step.get("children")
        if str(step.get("type") or "").strip().lower() in ("group", "foreach", "loop") and isinstance(children, list):
            bound += CountBoundHttpLeaves(children)
            continue
        if IsBoundHttpLeaf(step):
            bound += 1
    return bound


def WriteScenarioUpdateFile(body: Mapping[str, Any]) -> str:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump(body, handle, ensure_ascii=False, separators=(",", ":"))
        return handle.name


def GetScenarioDetail(
    *,
    scenario_id: int,
    project_id: int,
    branch: str,
    api_base_url: str,
    token: str,
) -> JsonObject:
    get_args = [
        "test-scenario",
        "get",
        str(scenario_id),
        "--project",
        str(project_id),
        "--with-case-detail",
    ]
    if branch:
        get_args.extend(["--branch", branch])
    detail = RunApifoxJson(get_args, api_base_url=api_base_url, token=token)
    data = detail.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("test-scenario get: data 非对象")
    return data


def UpdateScenarioFromFile(
    *,
    scenario_id: int,
    project_id: int,
    branch: str,
    api_base_url: str,
    token: str,
    file_path: str,
) -> None:
    update_args = [
        "test-scenario",
        "update",
        str(scenario_id),
        "--project",
        str(project_id),
        "--file",
        file_path,
    ]
    if branch:
        update_args.extend(["--branch", branch])
    RunApifoxJson(update_args, api_base_url=api_base_url, token=token)


def ToCliBoundHttpStep(
    step: Mapping[str, Any],
    *,
    project_id: int,
    index: int,
    endpoint_ids: Mapping[str, int],
) -> Optional[JsonObject]:
    """绑定真实接口：``type=http`` + ``bindType=API`` + ``syncMode=MANUAL``（可解绑）。"""
    case = step.get("httpApiCase")
    if not isinstance(case, dict):
        return None
    pair = CaseMethodPath(step)
    if pair is None:
        return None
    method, rel_path = pair
    api_id = int(endpoint_ids.get(EndpointMapKey(method, rel_path), 0))
    if api_id <= 0:
        raise RuntimeError(f"禁止 apiDetailId=0：未找到接口 {method.upper()} {rel_path}")
    name = str(step.get("name") or case.get("name") or f"step-{index}")
    pre = case.get("preProcessors") if isinstance(case.get("preProcessors"), list) else []
    post = case.get("postProcessors") if isinstance(case.get("postProcessors"), list) else []
    for proc in list(pre) + list(post):
        if isinstance(proc, dict) and "id" not in proc:
            proc["id"] = f"step{index}-{proc.get('type', 'script')}"
    parameters = case.get("parameters") if isinstance(case.get("parameters"), dict) else {}
    query = parameters.get("query") if isinstance(parameters.get("query"), list) else []
    cookie = parameters.get("cookie") if isinstance(parameters.get("cookie"), list) else []
    path_params = parameters.get("path") if isinstance(parameters.get("path"), list) else []
    header_rows = CaseHeaderRows(case)
    return {
        "id": f"step-{index}",
        "name": name,
        "type": "http",
        "disable": False,
        "ordering": index,
        "bindType": "API",
        "bindId": api_id,
        "syncMode": "MANUAL",
        "httpApiCase": {
            "id": 0,
            "name": name,
            "type": "DEBUG_CASE",
            "method": method,
            "path": rel_path,
            "apiDetailId": api_id,
            "projectId": project_id,
            "parameters": {
                "path": path_params,
                "query": query,
                "header": header_rows,
                "cookie": cookie,
            },
            "requestBody": NormalizeCustomHttpBody(case.get("requestBody")),
            "preProcessors": pre,
            "postProcessors": post,
            "auth": {},
            "commonParameters": {},
        },
    }


def ToCliScenarioSteps(
    import_steps: Sequence[Mapping[str, Any]],
    *,
    project_id: int,
    endpoint_ids: Optional[Mapping[str, int]] = None,
) -> List[JsonObject]:
    """转为场景步骤。默认 customHttp；传入 ``endpoint_ids`` 则绑定真实接口。"""
    counter = {"http": 0, "group": 0, "foreach": 0}

    def ConvertList(steps: Sequence[Mapping[str, Any]]) -> List[JsonObject]:
        out: List[JsonObject] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_type = str(step.get("type") or "").strip().lower()
            children = step.get("children")
            if step_type == "foreach" and isinstance(children, list):
                counter["foreach"] += 1
                params = step.get("parameters") if isinstance(step.get("parameters"), dict) else {}
                array_expr = str(params.get("array") or "").strip()
                if not array_expr:
                    raise RuntimeError(f"forEach step missing parameters.array: {step.get('id') or step.get('name')}")
                foreach_id = str(step.get("id") or f"foreach-{counter['foreach']}").strip()
                foreach_name = str(step.get("name") or foreach_id).strip()
                out.append(
                    {
                        "id": foreach_id,
                        "name": foreach_name,
                        "type": "forEach",
                        "disable": False,
                        "isOpen": True,
                        "parameters": {
                            "array": array_expr,
                            "onError": str(params.get("onError") or "continue"),
                        },
                        "children": ConvertList(children),
                    }
                )
                continue
            if step_type == "group" and isinstance(children, list):
                counter["group"] += 1
                group_name = StepDisplayName(step) or f"group-{counter['group']}"
                out.append(
                    {
                        "id": f"group-{counter['group']}",
                        "type": "group",
                        "disable": False,
                        "isOpen": True,
                        "parameters": {"name": group_name},
                        "children": ConvertList(children),
                    }
                )
                continue
            counter["http"] += 1
            if endpoint_ids:
                converted = ToCliBoundHttpStep(
                    step,
                    project_id=project_id,
                    index=counter["http"],
                    endpoint_ids=endpoint_ids,
                )
            else:
                converted = ToCliHttpStep(step, project_id=project_id, index=counter["http"])
            if converted is not None:
                out.append(converted)
        return out

    return ConvertList(import_steps)


def Main() -> int:
    parser = argparse.ArgumentParser(description="Push Apifox package steps into a scenario via CLI")
    parser.add_argument("--project", type=int, required=True)
    parser.add_argument("--scenario-id", type=int, required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--access-token", default="")
    parser.add_argument("--branch", default="main", help="Required by private deploy for automation writes")
    parser.add_argument(
        "--scenario-name",
        default="",
        help="写入 test-scenario update 的 name；默认取 package 内场景名",
    )
    parser.add_argument(
        "--use-data-set-id",
        type=int,
        default=0,
        help="写入 options.useDataSetId（与 2548 共用数据集时必填，否则鉴权 secret 为空）",
    )
    parser.add_argument(
        "--environment-id",
        type=int,
        default=0,
        help="写入 options.environmentId（可选，与 suites.yaml environment_id 对齐）",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("customHttp", "http", "raw"),
        default="customHttp",
        help="customHttp=不关联接口文档；http=绑定真实接口(MANUAL 可解绑)；raw=原样。"
        " RepoFirst 漏写 yaml 时默认 http+unbind（见 reference「场景 Headers 参数值为空」）",
    )
    parser.add_argument(
        "--unbind-after",
        action="store_true",
        help="仅 --mode http：绑定展开后按 UI 解绑形态转 customHttp（header 含 sampleValue）",
    )
    args = parser.parse_args()

    token = (args.access_token or os.environ.get("APIFOX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise SystemExit("APIFOX_ACCESS_TOKEN missing")

    package = json.loads(Path(args.package).read_text(encoding="utf-8"))
    scenario_item = ExtractImportScenarioItem(package)
    package_scenario_name = str(scenario_item.get("name") or "").strip()
    scenario_name = (args.scenario_name or "").strip() or package_scenario_name
    if not scenario_name:
        raise SystemExit("scenario name missing: pass --scenario-name or set name in package")
    scenario_desc = str(scenario_item.get("description") or "").strip()
    if not scenario_desc:
        scenario_desc = "Repo-first CLI sync; steps include postProcessors/customScript from Postman Tests."
    import_steps = ExtractImportSteps(package)
    if args.mode == "raw":
        steps = list(import_steps)
        for index, step in enumerate(steps, start=1):
            if "id" not in step:
                step["id"] = f"step-{index}"
            case = step.get("httpApiCase")
            if isinstance(case, dict):
                for proc in list(case.get("preProcessors") or []) + list(case.get("postProcessors") or []):
                    if isinstance(proc, dict) and "id" not in proc:
                        proc["id"] = f"step{index}-{proc.get('type', 'script')}"
                if "projectId" not in case:
                    case["projectId"] = args.project
    elif args.mode == "http":
        needed = CollectHttpMethodPaths(import_steps)
        endpoint_ids = EnsureEndpointIds(
            needed,
            project_id=args.project,
            branch=args.branch,
            api_base_url=args.api_base_url,
            token=token,
        )
        print(
            "bound endpoints: "
            + ", ".join(f"{EndpointMapKey(m, p)}={endpoint_ids[EndpointMapKey(m, p)]}" for m, p in needed)
        )
        steps = ToCliScenarioSteps(import_steps, project_id=args.project, endpoint_ids=endpoint_ids)
    else:
        steps = ToCliScenarioSteps(import_steps, project_id=args.project)

    update_body: JsonObject = {
        "name": scenario_name,
        "description": scenario_desc,
        "steps": steps,
    }
    # 数据集承载 clientId/secret/ProgramID；仅 steps 更新时勿丢掉 options
    if args.use_data_set_id > 0 or args.environment_id > 0:
        options: JsonObject = {
            "iterationCount": 1,
            "threadCount": 1,
            "runnerId": 0,
            "onError": "ignore",
            "delayItem": 0,
            "saveReportDetail": "all",
            "saveVariables": True,
            "readGlobalCookie": False,
            "saveGlobalCookie": False,
        }
        if args.environment_id > 0:
            options["environmentId"] = int(args.environment_id)
        if args.use_data_set_id > 0:
            options["useDataSetId"] = int(args.use_data_set_id)
        update_body["options"] = options

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        delete=False,
    ) as handle:
        # 紧凑 JSON：P1 大场景可避免私有化 update 422001（体积上限）
        json.dump(update_body, handle, ensure_ascii=False, separators=(",", ":"))
        tmp_path = handle.name

    expected_names = FlattenHttpStepNames(steps)
    AssertPurposeFirstNames(expected_names, context="push-payload")

    try:
        print(
            f"top_level_steps={len(steps)} http_leaves={len(expected_names)} "
            f"scenario_name={scenario_name!r} package={args.package}"
        )
        RunApifoxJson(
            ["cli-schema", "validate", "test-scenario-update", "--file", tmp_path],
            api_base_url=args.api_base_url,
            token=token,
        )
        print("cli-schema validate: OK")
        if args.dry_run:
            print(f"DRY-RUN skip update scenario {args.scenario_id}")
            print("DRY-RUN package names sample:")
            for index, name in enumerate(expected_names[:5], start=1):
                print(f"  sample[{index}] {name}")
            if args.unbind_after:
                print("DRY-RUN would unbind bound http steps to customHttp after push")
            return 0
        update_args = [
            "test-scenario",
            "update",
            str(args.scenario_id),
            "--project",
            str(args.project),
            "--file",
            tmp_path,
        ]
        if args.branch:
            update_args.extend(["--branch", args.branch])
        RunApifoxJson(update_args, api_base_url=args.api_base_url, token=token)
        print(f"UPDATED scenario {args.scenario_id} branch={args.branch or 'main'}")
        data = GetScenarioDetail(
            scenario_id=args.scenario_id,
            project_id=args.project,
            branch=args.branch,
            api_base_url=args.api_base_url,
            token=token,
        )
        got = data.get("steps") or []
        if not isinstance(got, list):
            raise RuntimeError("test-scenario get: steps 非列表")
        VerifyRemoteMatchesExpected(expected_names=expected_names, remote_steps=got)
        if args.unbind_after:
            if args.mode != "http":
                raise SystemExit("--unbind-after 仅在 --mode http 时有效")
            unbound = UnbindHttpStepsToCustomHttp(got, project_id=args.project)
            print(f"unbind http→customHttp: {unbound} steps")
            unbind_body: JsonObject = {
                "name": str(data.get("name") or scenario_name),
                "description": str(data.get("description") or scenario_desc),
                "steps": got,
            }
            remote_options = data.get("options")
            if isinstance(remote_options, dict) and remote_options:
                unbind_body["options"] = remote_options
            elif isinstance(update_body.get("options"), dict):
                unbind_body["options"] = update_body["options"]
            unbind_path = WriteScenarioUpdateFile(unbind_body)
            try:
                RunApifoxJson(
                    ["cli-schema", "validate", "test-scenario-update", "--file", unbind_path],
                    api_base_url=args.api_base_url,
                    token=token,
                )
                UpdateScenarioFromFile(
                    scenario_id=args.scenario_id,
                    project_id=args.project,
                    branch=args.branch,
                    api_base_url=args.api_base_url,
                    token=token,
                    file_path=unbind_path,
                )
            finally:
                Path(unbind_path).unlink(missing_ok=True)
            unbound_data = GetScenarioDetail(
                scenario_id=args.scenario_id,
                project_id=args.project,
                branch=args.branch,
                api_base_url=args.api_base_url,
                token=token,
            )
            unbound_steps = unbound_data.get("steps") or []
            if not isinstance(unbound_steps, list):
                raise RuntimeError("test-scenario get after unbind: steps 非列表")
            leftover = CountBoundHttpLeaves(unbound_steps)
            custom_left = CountCustomHttpLeaves(unbound_steps)
            empty_headers = CountEmptyHeaderValueLeaves(unbound_steps)
            if leftover > 0:
                raise RuntimeError(f"解绑后仍有 {leftover} 个绑定 http 步（UI 会显示已关联接口文档）")
            if custom_left != len(expected_names):
                raise RuntimeError(
                    f"解绑后 customHttp={custom_left} 期望={len(expected_names)}"
                )
            if empty_headers > 0:
                raise RuntimeError(
                    f"解绑后仍有 {empty_headers} 个步骤 header value 全空"
                )
            VerifyRemoteMatchesExpected(expected_names=expected_names, remote_steps=unbound_steps)
            print(
                f"UNBOUND scenario {args.scenario_id} leftover_bind=0 "
                f"customHttp={custom_left} empty_header_leaves=0"
            )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
