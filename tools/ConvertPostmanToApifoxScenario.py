"""
Postman Collection v2.1 → Apifox 2.7.43 导入包（含前后置 customScript）。

用于私有化 CLI：``apifox import --format apifox``（``postman`` 格式在私有化常失败）。
每步 HTTP 的 Postman ``event.listen=test/prerequest`` 转为 ``httpApiCase.postProcessors/preProcessors``。

用法（仓库根）::

    python tools/ConvertPostmanToApifoxScenario.py ^
      --input api-testcases/api_tests/postman/collections/PAPI-2548-membership-extensions.postman_collection.json ^
      --output apifox-reports/papi_2548/generated/PAPI-2548-membership-extensions.apifox-2.7.43-import.json ^
      --scenario-name "PAPI-2548 extensions · CLI sync" ^
      --collection-name "PAPI-2548 membership extensions"
"""
from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

JsonObject = Dict[str, Any]

APIFOX_CLIENT_VERSION = "2.7.43"


def FlattenPostmanRequestItems(items: Sequence[Mapping[str, Any]]) -> List[JsonObject]:
    flat: List[JsonObject] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if "request" in it:
            flat.append(dict(it))
        nested = it.get("item")
        if isinstance(nested, list):
            flat.extend(FlattenPostmanRequestItems(nested))
    return flat


def BuildApifoxStepsFromPostmanItems(
    items: Sequence[Mapping[str, Any]],
    *,
    case_id_base: int,
    counters: Optional[Dict[str, int]] = None,
) -> Tuple[List[JsonObject], int]:
    """
    保留 Postman 文件夹嵌套：文件夹 → ``type=group``，请求 → HTTP 步。

    返回 ``(steps, scripted_count)``。group 的展示名放在 ``parameters.name``（Apifox CLI schema）。
    """
    if counters is None:
        counters = {"http": 0, "group": 0, "scripted": 0}
    steps: List[JsonObject] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        nested = it.get("item")
        if isinstance(nested, list) and "request" not in it:
            counters["group"] += 1
            group_name = str(it.get("name") or f"group-{counters['group']}").strip()
            children, _ = BuildApifoxStepsFromPostmanItems(
                nested, case_id_base=case_id_base, counters=counters
            )
            steps.append(
                {
                    "id": f"group-{counters['group']}",
                    "type": "group",
                    "disable": False,
                    "isOpen": True,
                    "parameters": {"name": group_name},
                    "children": children,
                }
            )
            continue
        if "request" not in it:
            continue
        counters["http"] += 1
        index = counters["http"]
        case = ApifoxHttpApiCaseFromPostmanItem(it, case_id=case_id_base + index)
        if case.get("postProcessors") or case.get("preProcessors"):
            counters["scripted"] += 1
        steps.append(
            {
                "name": str(it.get("name", f"step-{index}")),
                "number": index,
                "type": "http",
                "bind": False,
                "disable": False,
                "bindType": "API",
                "bindId": 0,
                "syncMode": "manual",
                "httpApiCase": case,
            }
        )
    return steps, int(counters["scripted"])


def ScriptExecByListen(item: Mapping[str, Any], listen: str) -> List[str]:
    lines: List[str] = []
    for ev in item.get("event", []) or []:
        if not isinstance(ev, dict) or ev.get("listen") != listen:
            continue
        script = ev.get("script") or {}
        if not isinstance(script, dict):
            continue
        exec_lines = script.get("exec", [])
        if isinstance(exec_lines, list):
            lines.extend(str(line) for line in exec_lines)
        elif isinstance(exec_lines, str):
            lines.extend(exec_lines.splitlines())
    return lines


def ApifoxParameterRows(headers: Sequence[Mapping[str, Any]]) -> List[JsonObject]:
    rows: List[JsonObject] = []
    for hdr in headers:
        if not isinstance(hdr, dict):
            continue
        key = str(hdr.get("key", ""))
        if not key:
            continue
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "relatedId": str(uuid.uuid4()),
                "relatedName": key,
                "name": key,
                "value": str(hdr.get("value", "")),
                "type": "string",
                "description": "",
                "enable": True,
                "isDelete": False,
            }
        )
    return rows


def ApifoxCustomScriptProcessor(exec_lines: Sequence[str]) -> JsonObject:
    return {
        "type": "customScript",
        "enable": True,
        "defaultEnable": True,
        "data": "\n".join(exec_lines),
    }


def ApifoxProcessorsFromItem(item: Mapping[str, Any]) -> Tuple[List[JsonObject], List[JsonObject]]:
    pre_lines = ScriptExecByListen(item, "prerequest")
    test_lines = ScriptExecByListen(item, "test")
    pre: List[JsonObject] = []
    post: List[JsonObject] = []
    if pre_lines:
        pre.append(ApifoxCustomScriptProcessor(pre_lines))
    if test_lines:
        post.append(ApifoxCustomScriptProcessor(test_lines))
    return pre, post


def ResolvePath(req: Mapping[str, Any]) -> str:
    url_obj = req.get("url", {})
    if isinstance(url_obj, dict):
        path_parts = url_obj.get("path", [])
        if isinstance(path_parts, list) and path_parts:
            # 保留空 path 段（如空 resourceId → /localOffers//options）；勿用 truthy 过滤
            cleaned: List[str] = []
            for part in path_parts:
                s = str(part)
                if s == "":
                    cleaned.append("")
                else:
                    cleaned.append(s.strip("/"))
            while cleaned and cleaned[0] == "":
                cleaned.pop(0)
            return "/" + "/".join(cleaned) if cleaned else "/"
        raw = url_obj.get("raw")
        if isinstance(raw, str):
            return ResolvePath({"url": raw})
        return "/"
    raw = str(url_obj)
    if "{{baseUrl}}" in raw:
        raw = raw.split("{{baseUrl}}", 1)[-1]
    if "://" in raw:
        raw = "/" + "/".join(raw.split("://", 1)[-1].split("/")[1:])
    if not raw.startswith("/"):
        raw = "/" + raw.lstrip("/")
    return raw.split("?")[0] or "/"


def ExtractPostmanQueryRows(req: Mapping[str, Any]) -> List[JsonObject]:
    """从 Postman ``url.query``（或 ``url.raw`` 的 querystring）提取 query，供 Apifox parameters.query。"""
    url_obj = req.get("url", {})
    rows_src: List[Mapping[str, Any]] = []
    if isinstance(url_obj, dict):
        query = url_obj.get("query")
        if isinstance(query, list):
            for item in query:
                if isinstance(item, dict):
                    rows_src.append(item)
        if not rows_src:
            raw = url_obj.get("raw")
            if isinstance(raw, str) and "?" in raw:
                qs = raw.split("?", 1)[1]
                for part in qs.split("&"):
                    if not part:
                        continue
                    if "=" in part:
                        key, value = part.split("=", 1)
                    else:
                        key, value = part, ""
                    rows_src.append({"key": key, "value": value})
    elif isinstance(url_obj, str) and "?" in url_obj:
        qs = url_obj.split("?", 1)[1]
        for part in qs.split("&"):
            if not part:
                continue
            if "=" in part:
                key, value = part.split("=", 1)
            else:
                key, value = part, ""
            rows_src.append({"key": key, "value": value})
    # 复用 header 行结构：Postman query 项多为 key/value
    return ApifoxParameterRows(rows_src)


def ApifoxHttpApiCaseFromPostmanItem(item: Mapping[str, Any], *, case_id: int) -> JsonObject:
    req = item.get("request")
    if not isinstance(req, dict):
        raise ValueError(f"item missing request: {item.get('name')}")
    method = str(req.get("method", "GET")).lower()
    path = ResolvePath(req)
    headers = req.get("header", [])
    if not isinstance(headers, list):
        headers = []
    body = req.get("body", {})
    request_body: Optional[JsonObject] = None
    if isinstance(body, dict) and body.get("mode") == "raw":
        request_body = {
            "type": "application/json",
            "data": str(body.get("raw", "")),
            "generateMode": "normal",
            "parameters": [],
        }
    pre_processors, post_processors = ApifoxProcessorsFromItem(item)
    return {
        "id": case_id,
        "name": str(item.get("name", "")),
        "method": method,
        "path": path,
        "auth": {},
        "type": "http",
        "options": {},
        "responseId": 0,
        "apiId": 0,
        "moduleId": 0,
        "parameters": {
            "query": ExtractPostmanQueryRows(req),
            "header": ApifoxParameterRows(headers),
            "cookie": [],
            "path": [],
        },
        "requestBody": request_body,
        "preProcessors": pre_processors,
        "postProcessors": post_processors,
        "inheritPostProcessors": {},
        "inheritPreProcessors": {},
        "advancedSettings": {
            "disabledSystemHeaders": {},
            "isDefaultUrlEncoding": 1,
        },
    }


def BuildApifox2743ImportPayload(
    collection: Mapping[str, Any],
    *,
    collection_name: str,
    scenario_name: str,
    tags: Optional[Sequence[str]] = None,
    case_id_base: int = 890_000,
) -> JsonObject:
    info = collection.get("info") if isinstance(collection.get("info"), dict) else {}
    items = collection.get("item")
    if not isinstance(items, list):
        items = []
    steps, scripted = BuildApifoxStepsFromPostmanItems(items, case_id_base=case_id_base)
    http_count = len(FlattenPostmanRequestItems(items))
    tag_list = list(tags) if tags else ["cli-sync", "repo-first"]
    return {
        "app": "apifox",
        "type": "project",
        "exportTarget": "apifox",
        "compatibleClientVersion": APIFOX_CLIENT_VERSION,
        "exportHint": (
            "CLI: apifox import --format apifox --file <this> --project <id> "
            "[--module-map \"name=moduleId\"]. "
            "客户端：项目设置 → 导入数据 → Apifox（勾选测试场景）。"
        ),
        "apiCollection": [],
        "apiTestCaseCollection": [
            {
                "name": collection_name,
                "description": (
                    f"由 ConvertPostmanToApifoxScenario.py 生成；"
                    f"{http_count} HTTP 步（含文件夹→group 嵌套），其中 {scripted} 步含前/后置脚本。"
                ),
                "children": [],
                "items": [
                    {
                        "id": case_id_base + 1,
                        "name": scenario_name,
                        "description": str(info.get("description") or ""),
                        "tags": tag_list,
                        "priority": 1,
                        "ordering": 1,
                        "steps": steps,
                    }
                ],
            }
        ],
        "environmentCollection": [],
        "_meta": {
            "stepCount": http_count,
            "topLevelStepCount": len(steps),
            "scriptedStepCount": scripted,
            "sourceCollectionName": str(info.get("name") or ""),
        },
    }


def Main() -> int:
    parser = argparse.ArgumentParser(description="Postman → Apifox 2.7.43 scenario package (with Tests)")
    parser.add_argument("--input", required=True, help="Postman collection JSON")
    parser.add_argument("--output", required=True, help="Apifox import JSON output")
    parser.add_argument("--scenario-name", default="", help="Scenario item name")
    parser.add_argument("--collection-name", default="", help="apiTestCaseCollection name")
    parser.add_argument(
        "--tags",
        default="cli-sync,repo-first",
        help="Comma-separated tags（业务 tag 由调用方传入，如 suites.yaml convert_tags）",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.is_file():
        raise FileNotFoundError(f"input not found: {in_path}")

    collection = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(collection, dict):
        raise ValueError("collection root must be object")

    info = collection.get("info") if isinstance(collection.get("info"), dict) else {}
    default_name = str(info.get("name") or "Imported collection")
    collection_name = args.collection_name.strip() or default_name
    scenario_name = args.scenario_name.strip() or f"{collection_name} · CLI sync"
    tags = [t.strip() for t in str(args.tags).split(",") if t.strip()]

    payload = BuildApifox2743ImportPayload(
        collection,
        collection_name=collection_name,
        scenario_name=scenario_name,
        tags=tags,
    )
    meta = payload.pop("_meta", {})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {out_path} steps={meta.get('stepCount')} "
        f"scripted={meta.get('scriptedStepCount')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
