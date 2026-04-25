from __future__ import annotations

import json
import math
import os
import sys
import uuid
import ssl
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union


def _HttpGetJson(url: str, headers: Mapping[str, str], timeout_s: float = 120.0) -> Tuple[int, Dict[str, Any]]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, method="GET")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_s) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            code = int(getattr(resp, "status", 200))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        code = int(e.code)
    try:
        parsed: Dict[str, Any] = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError as ex:
        raise RuntimeError(f"非 JSON 响应 (HTTP {code}): {body[:500]}") from ex
    return code, parsed


def _BuildResourcesUrl(page_number: int, page_size: int) -> str:
    q = urllib.parse.urlencode(
        {
            "pageSize": str(page_size),
            "pageNumber": str(page_number),
        }
    )
    return f"https://developer-sandbox.dragonpass.com/api/v2/resources?{q}"


def _CollectResourceItems(resources_obj: object) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(resources_obj, dict):
        return out
    for _k, v in resources_obj.items():
        if not isinstance(v, list):
            continue
        for item in v:
            if isinstance(item, dict):
                out.append(item)
    return out


def _RequestIdHeader() -> str:
    return str(uuid.uuid4())


def _FetchOne(
    name: str,
    base_headers: Dict[str, str],
    page_number: int,
    page_size: int,
) -> Tuple[str, int, int, List[Dict[str, Any]]]:
    h = dict(base_headers)
    h["X-Request-ID"] = _RequestIdHeader()
    url = _BuildResourcesUrl(page_number, page_size)
    status, j = _HttpGetJson(url, h)
    if status != 200:
        raise RuntimeError(f"{name} HTTP {status} @ pageNumber={page_number}: {str(j)[:1000]}")
    biz: Union[int, str, None] = j.get("code", None)
    if biz is not None and int(str(biz)) != 0:
        raise RuntimeError(
            f"{name} 业务 code!=0 @ pageNumber={page_number}: {json.dumps(j, ensure_ascii=False)[:1200]}"
        )
    data = j.get("data")
    total_num: int = -1
    if isinstance(data, dict):
        pag = data.get("pagination")
        if isinstance(pag, dict) and isinstance(pag.get("totalNumber"), int):
            total_num = int(pag["totalNumber"])
        res = data.get("resources")
        items = _CollectResourceItems(res)
    else:
        items = []
    return name, total_num, page_number, items


def _DiffDicts(
    a: Dict[str, Any], b: Dict[str, Any], path: str
) -> List[Tuple[str, Any, Any]]:
    diffs: List[Tuple[str, Any, Any]] = []
    keys = set(a.keys()) | set(b.keys())
    for k in sorted(keys, key=lambda x: str(x)):
        pa = f"{path}.{k}" if path else str(k)
        if k not in a:
            diffs.append((pa, None, b.get(k)))
            continue
        if k not in b:
            diffs.append((pa, a.get(k), None))
            continue
        va, vb = a[k], b[k]
        if type(va) is not type(vb) and not (
            isinstance(va, (int, float)) and isinstance(vb, (int, float))
        ):
            if va != vb:
                diffs.append((pa, va, vb))
            continue
        if isinstance(va, dict) and isinstance(vb, dict):
            diffs.extend(_DiffDicts(va, vb, pa))
        elif isinstance(va, list) and isinstance(vb, list):
            if va != vb:
                diffs.append((pa, va, vb))
        else:
            if va != vb:
                diffs.append((pa, va, vb))
    return diffs


def _IndexByResourceId(items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for it in items:
        rid = it.get("resourceId")
        if rid is not None:
            by_id[str(rid)] = it
    return by_id


def Main() -> int:
    page_size = 100
    token_a = os.environ.get("DP_RESOURCES_TOKEN_A", "").strip()
    token_b = os.environ.get("DP_RESOURCES_TOKEN_B", "").strip()
    if not token_a or not token_b:
        print(
            "请设置环境变量 DP_RESOURCES_TOKEN_A、DP_RESOURCES_TOKEN_B 为两段 Bearer token（不含 Bearer 前缀也可，本脚本会补全）。",
            file=sys.stderr,
        )
        return 2
    if not token_a.lower().startswith("bearer "):
        token_a = "Bearer " + token_a
    if not token_b.lower().startswith("bearer "):
        token_b = "Bearer " + token_b
    h_a: Dict[str, str] = {
        "X-Program-ID": "1919249349977088",
        "Authorization": token_a,
        "Accept": "application/json",
    }
    h_b: Dict[str, str] = {
        "x-version": "canary",
        "X-Program-ID": "1919249349977088",
        "Authorization": token_b,
        "Accept": "application/json",
    }

    # 第 1 页：并行
    a_total: int = -1
    b_total: int = -1
    all_a: List[Dict[str, Any]] = []
    all_b: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = {
            ex.submit(_FetchOne, "A(无x-version,token1)", h_a, 1, page_size),
            ex.submit(_FetchOne, "B(x-version=canary,token2)", h_b, 1, page_size),
        }
        for fut in as_completed(futs):
            name, tnum, _pn, items = fut.result()
            if name.startswith("A"):
                a_total = tnum
                all_a.extend(items)
            else:
                b_total = tnum
                all_b.extend(items)
    if a_total < 0 or b_total < 0:
        raise RuntimeError("无法从第 1 页读取 pagination.totalNumber")

    print(
        f"第1页完成: A totalNumber={a_total} 本页条数={len(all_a)} | "
        f"B totalNumber={b_total} 本页条数={len(all_b)}",
        flush=True,
    )

    max_page = max(int(math.ceil(a_total / float(page_size))), int(math.ceil(b_total / float(page_size))))
    print(f"预计总页数(两环境较大值): {max_page}  pageSize={page_size}", flush=True)

    for pn in range(2, max_page + 1):
        with ThreadPoolExecutor(max_workers=2) as ex:
            futs = {
                ex.submit(_FetchOne, "A", h_a, pn, page_size),
                ex.submit(_FetchOne, "B", h_b, pn, page_size),
            }
            for fut in as_completed(futs):
                _name, _t, _p, items = fut.result()
                if _name == "A":
                    all_a.extend(items)
                else:
                    all_b.extend(items)
        print(f"第{pn}/{max_page}页 已拉取  A累加={len(all_a)} B累加={len(all_b)}", flush=True)

    # 若有重复 resourceId 仅保留最后一条
    a_by = _IndexByResourceId(all_a)
    b_by = _IndexByResourceId(all_b)

    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.platform == "win32" and hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    print("== 总数 data.pagination.totalNumber ==")
    print("A:", a_total, "  B:", b_total, "  差值:", b_total - a_total)
    print("== 累加条数（去重前列表长度） ==")
    print("A:", len(all_a), "  B:", len(all_b))
    print("== 以 resourceId 去重后条数 ==")
    print("A:", len(a_by), "  B:", len(b_by))
    print()

    only_a = sorted(set(a_by) - set(b_by))
    only_b = sorted(set(b_by) - set(a_by))
    both = sorted(set(a_by) & set(b_by), key=str)

    print("== 仅一边存在的 resourceId ==")
    print("仅 A:", only_a)
    print("仅 B:", only_b)
    print("两边都有:", len(both))
    print()

    max_ids = 30
    max_field_show = 6
    n_diff = 0
    shown: List[str] = []
    for rid in both:
        da, db = a_by[rid], b_by[rid]
        if da == db:
            continue
        n_diff += 1
        diffs = _DiffDicts(da, db, "")
        if len(shown) < max_ids:
            shown.append(rid)
            print("---- resourceId=" + rid + f" 字段差异(最多{max_field_show}处) ----")
            for i, (p, va, vb) in enumerate(diffs):
                if i >= max_field_show:
                    break
                print(" ", p)
                print("   A:", (json.dumps(va, ensure_ascii=False)[:500]))
                print("   B:", (json.dumps(vb, ensure_ascii=False)[:500]))
    print()
    print("== 同 resourceId 但 JSON 对象不完全相等的条数:", n_diff, "==")
    if n_diff > max_ids:
        print("（仅以上展示前 " + str(max_ids) + " 个有差异的 resourceId:", ", ".join(shown), "）")
    return 0


if __name__ == "__main__":
    sys.exit(Main())
