"""
将 Postman Collection 的 Tests 通过 ``apifox endpoint update`` 回写到项目接口（全量 CLI 备选）。

流程：
1. 解析 Postman 每步 ``event.listen=test/prerequest`` → customScript
2. ``endpoint list`` 后按 ``METHOD + path`` 匹配（同 path 多方法取同名优先）
3. ``endpoint get`` → 合并 processors（带 id）→ ``cli-schema validate`` → ``endpoint update``

用法（仓库根，已 ``apifox auth login --api-base-url ...``）::

    python tools/SyncPostmanTestsViaCli.py ^
      --project 346275 ^
      --api-base-url https://apifox.dragonpass.com.cn ^
      --collection api-testcases/api_tests/postman/collections/PAPI-2548-membership-extensions.postman_collection.json ^
      --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

JsonObject = Dict[str, Any]

# 复用转换器里的脚本抽取逻辑
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "tools") not in sys.path:
    sys.path.insert(0, str(_REPO / "tools"))

from ConvertPostmanToApifoxScenario import (  # noqa: E402
    ApifoxCustomScriptProcessor,
    ApifoxProcessorsFromItem,
    FlattenPostmanRequestItems,
    ResolvePath,
)


def RunApifox(args: Sequence[str], *, api_base_url: str, token: str) -> JsonObject:
    cmd = [
        "apifox",
        "--api-base-url",
        api_base_url,
        "--access-token",
        token,
        *args,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    text = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    if not text:
        raise RuntimeError(f"apifox returned empty output: {' '.join(args)} exit={proc.returncode}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"apifox non-JSON output: {text[:500]}") from exc
    if proc.returncode != 0 or payload.get("success") is False:
        err = payload.get("error") or payload
        raise RuntimeError(f"apifox failed: {err}")
    return payload


def LoadCollectionSteps(collection_path: Path) -> List[JsonObject]:
    collection = json.loads(collection_path.read_text(encoding="utf-8"))
    items = collection.get("item")
    if not isinstance(items, list):
        return []
    steps: List[JsonObject] = []
    for item in FlattenPostmanRequestItems(items):
        req = item.get("request")
        if not isinstance(req, dict):
            continue
        method = str(req.get("method", "GET")).upper()
        path = ResolvePath(req)
        pre, post = ApifoxProcessorsFromItem(item)
        if not pre and not post:
            continue
        # endpoint-update 校验要求 processor 带 id
        for proc in pre + post:
            if "id" not in proc:
                proc["id"] = f"cli-{uuid.uuid4().hex[:16]}"
        steps.append(
            {
                "name": str(item.get("name") or ""),
                "method": method,
                "path": path,
                "preProcessors": pre,
                "postProcessors": post,
            }
        )
    return steps


def IndexEndpoints(list_payload: Mapping[str, Any]) -> Dict[Tuple[str, str], List[JsonObject]]:
    data = list_payload.get("data")
    rows: List[Any]
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and isinstance(data.get("items"), list):
        rows = data["items"]
    else:
        rows = []
    index: Dict[Tuple[str, str], List[JsonObject]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        method = str(row.get("method") or row.get("httpMethod") or "").upper()
        path = str(row.get("path") or "")
        if not method or not path:
            continue
        index.setdefault((method, path), []).append(row)
    return index


def PickEndpoint(
    candidates: Sequence[Mapping[str, Any]],
    step_name: str,
) -> Optional[Mapping[str, Any]]:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    for c in candidates:
        if str(c.get("name") or "") == step_name:
            return c
    # 优先名称包含 step 关键词
    for c in candidates:
        name = str(c.get("name") or "")
        if step_name and (step_name in name or name in step_name):
            return c
    return candidates[0]


def Main() -> int:
    parser = argparse.ArgumentParser(description="Sync Postman Tests → Apifox endpoints via CLI")
    parser.add_argument("--project", required=True, type=int)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--access-token", default="", help="Default: env APIFOX_ACCESS_TOKEN")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Only sync first N matched steps")
    args = parser.parse_args()

    token = (args.access_token or os.environ.get("APIFOX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise SystemExit("APIFOX_ACCESS_TOKEN missing")

    collection_path = Path(args.collection)
    steps = LoadCollectionSteps(collection_path)
    print(f"Postman steps with scripts: {len(steps)}")

    listed = RunApifox(
        ["endpoint", "list", "--project", str(args.project)],
        api_base_url=args.api_base_url,
        token=token,
    )
    index = IndexEndpoints(listed)
    print(f"Project endpoints indexed: {sum(len(v) for v in index.values())}")

    matched = 0
    updated = 0
    skipped = 0
    for step in steps:
        key = (step["method"], step["path"])
        cand = index.get(key) or []
        ep = PickEndpoint(cand, step["name"])
        if not ep:
            print(f"SKIP no endpoint: {step['method']} {step['path']} · {step['name'][:60]}")
            skipped += 1
            continue
        ep_id = ep.get("id")
        if ep_id is None:
            skipped += 1
            continue
        matched += 1
        if args.limit and matched > args.limit:
            break
        update_body: JsonObject = {}
        if step["preProcessors"]:
            update_body["preProcessors"] = step["preProcessors"]
        if step["postProcessors"]:
            update_body["postProcessors"] = step["postProcessors"]
        tmp = Path("_endpoint_update_tmp.json")
        tmp.write_text(json.dumps(update_body, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            RunApifox(
                ["cli-schema", "validate", "endpoint-update", "--file", str(tmp)],
                api_base_url=args.api_base_url,
                token=token,
            )
            if args.dry_run:
                print(f"DRY-RUN would update endpoint {ep_id}: {step['method']} {step['path']}")
            else:
                RunApifox(
                    [
                        "endpoint",
                        "update",
                        str(ep_id),
                        "--project",
                        str(args.project),
                        "--file",
                        str(tmp),
                    ],
                    api_base_url=args.api_base_url,
                    token=token,
                )
                print(f"UPDATED endpoint {ep_id}: {step['method']} {step['path']}")
                updated += 1
        finally:
            if tmp.exists():
                tmp.unlink()

    print(f"Done matched={matched} updated={updated} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
