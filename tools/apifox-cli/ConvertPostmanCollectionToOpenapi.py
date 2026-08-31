"""
将 Postman Collection v2.1 转为 OpenAPI 3.0.3（供私有化 Apifox CLI ``import --format openapi``）。

说明：当前私有化 ``import --format postman`` 返回 Invalid Parameter；OpenAPI 导入可用。
本转换只保留 method/path/summary（请求名），不迁移 Tests 脚本——自动化断言仍以仓库生成器为准，
需在 Apifox 客户端导入 Postman 或整理为场景用例后才能 ``apifox run``。

用法（仓库根）::

    python tools/apifox-cli/ConvertPostmanCollectionToOpenapi.py ^
      --input api-testcases/api_tests/apifox-cli/collections/PAPI-2548-membership-extensions.postman_collection.json ^
      --output apifox-reports/papi_2548/generated/PAPI-2548-membership-extensions.openapi.json
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


def ParsePostmanUrl(url: Any) -> Tuple[str, List[str]]:
    """返回 (path, path_segments)。"""
    if isinstance(url, str):
        # 去掉 host / {{baseUrl}}
        path = url
        path = re.sub(r"^https?://[^/]+", "", path)
        path = re.sub(r"^\{\{[^}]+\}\}", "", path)
        if not path.startswith("/"):
            path = "/" + path.lstrip("/")
        segs = [s for s in path.split("/") if s]
        return path.split("?")[0] or "/", segs
    if isinstance(url, dict):
        raw_path = url.get("path")
        if isinstance(raw_path, list):
            segs = [str(x).strip("/") for x in raw_path if str(x).strip("/")]
            path = "/" + "/".join(segs) if segs else "/"
            return path, segs
        raw = url.get("raw")
        if isinstance(raw, str):
            return ParsePostmanUrl(raw)
    return "/", []


def WalkRequests(items: Sequence[Mapping[str, Any]], folder_prefix: str = "") -> Iterable[Dict[str, Any]]:
    for it in items:
        name = str(it.get("name") or "")
        children = it.get("item")
        if isinstance(children, list):
            next_prefix = f"{folder_prefix}{name}/" if name else folder_prefix
            yield from WalkRequests(children, next_prefix)
            continue
        req = it.get("request")
        if not isinstance(req, dict):
            continue
        method = str(req.get("method") or "GET").upper()
        path, _ = ParsePostmanUrl(req.get("url"))
        # OpenAPI path 参数 {{id}} -> {id}
        oas_path = re.sub(r"\{\{([^}]+)\}\}", r"{\1}", path)
        yield {
            "folder": folder_prefix.rstrip("/"),
            "name": name,
            "method": method,
            "path": oas_path if oas_path.startswith("/") else "/" + oas_path,
            "description": str(it.get("description") or req.get("description") or ""),
        }


def BuildOpenApi(
    collection: Mapping[str, Any],
    *,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    info = collection.get("info") if isinstance(collection.get("info"), dict) else {}
    coll_title = title or str(info.get("name") or "Imported Postman Collection")
    paths: MutableMapping[str, Any] = {}
    seen: set[Tuple[str, str]] = set()
    items = collection.get("item")
    if not isinstance(items, list):
        items = []
    for req in WalkRequests(items):
        key = (req["method"], req["path"])
        if key in seen:
            continue
        seen.add(key)
        method_l = req["method"].lower()
        op: Dict[str, Any] = {
            "summary": req["name"][:120] or f"{req['method']} {req['path']}",
            "description": (
                f"folder: {req['folder']}\n\n{req['description']}".strip()
                if req["folder"] or req["description"]
                else ""
            ),
            "responses": {"200": {"description": "OK"}},
            "tags": [req["folder"]] if req["folder"] else ["imported"],
        }
        # path params
        params = re.findall(r"\{([^}]+)\}", req["path"])
        if params:
            op["parameters"] = [
                {
                    "name": p,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
                for p in params
            ]
        paths.setdefault(req["path"], {})[method_l] = op

    return {
        "openapi": "3.0.3",
        "info": {
            "title": coll_title,
            "version": "1.0.0",
            "description": (
                "Generated from Postman Collection for Apifox CLI openapi import "
                "(private deploy postman import workaround). Scripts/tests not included."
            ),
        },
        "paths": dict(sorted(paths.items(), key=lambda kv: kv[0])),
    }


def Main() -> int:
    parser = argparse.ArgumentParser(description="Postman Collection v2.1 → OpenAPI 3.0.3")
    parser.add_argument("--input", required=True, help="Postman collection JSON path")
    parser.add_argument("--output", required=True, help="OpenAPI JSON output path")
    parser.add_argument("--title", default="", help="Override OpenAPI info.title")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.output)
    if not in_path.is_file():
        raise FileNotFoundError(f"input not found: {in_path}")

    collection = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(collection, dict):
        raise ValueError("collection root must be object")

    oas = BuildOpenApi(collection, title=args.title or None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(oas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path_count = len(oas.get("paths") or {})
    op_count = sum(len(v) for v in (oas.get("paths") or {}).values())
    print(f"OK: {out_path} paths={path_count} operations={op_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
