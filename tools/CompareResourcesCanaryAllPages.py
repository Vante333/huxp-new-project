from __future__ import annotations

import json
import math
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, TextIO, Tuple
from urllib import parse, request


class _TeeOut:
    def __init__(self, *files: TextIO) -> None:
        self._files = files

    def write(self, s: str) -> int:
        for f in self._files:
            f.write(s)
        return len(s)

    def flush(self) -> None:
        for f in self._files:
            f.flush()


def _Headers(program_id: str, token: str, with_canary: bool) -> List[Tuple[str, str]]:
    h: List[Tuple[str, str]] = [
        ("X-Program-ID", program_id),
        ("X-Request-ID", str(uuid.uuid4())),
        ("Authorization", f"Bearer {token}"),
        ("Accept", "application/json"),
    ]
    if with_canary:
        return [("x-version", "canary"), *h]
    return h


def _RequestJson(
    base_url: str, page_size: int, page_number: int, program_id: str, token: str, with_canary: bool
) -> Dict[str, Any]:
    q = parse.urlencode({"pageSize": page_size, "pageNumber": page_number})
    u = f"{base_url.rstrip('/')}?{q}"
    r = request.Request(
        u,
        headers={k: v for k, v in _Headers(program_id, token, with_canary)},
        method="GET",
    )
    with request.urlopen(r, timeout=90) as resp:  # noqa: S310 — known sandbox URL
        return json.loads(resp.read().decode("utf-8"))


def _MergePageIntoTh(th: Dict[str, Any], page: Dict[str, Any]) -> None:
    d = (page.get("data") or {}).get("resources") or {}
    for it in d.get("transportHubResources") or []:
        rid = it.get("resourceId")
        if rid is not None:
            th[str(rid)] = it


def _MergePageIntoLifestyle(ls: Dict[str, Any], page: Dict[str, Any]) -> None:
    d = (page.get("data") or {}).get("resources") or {}
    for it in d.get("lifestyleResources") or []:
        rid = it.get("resourceId")
        if rid is not None:
            ls[str(rid)] = it


def _FetchAllPages(
    base_url: str, page_size: int, program_id: str, token: str, with_canary: bool, label: str
) -> Tuple[Dict[str, Any], Dict[str, Any], int, int]:
    first = _RequestJson(base_url, page_size, 1, program_id, token, with_canary)
    if first.get("code") != 0:
        raise RuntimeError(f"{label} 第1页失败: {json.dumps(first, ensure_ascii=False)[:2000]}")

    pag = ((first.get("data") or {}).get("pagination") or {})
    total = int(pag.get("totalNumber", 0))
    pages = max(1, math.ceil(total / page_size)) if page_size else 1

    th: Dict[str, Any] = {}
    ls: Dict[str, Any] = {}
    _MergePageIntoTh(th, first)
    _MergePageIntoLifestyle(ls, first)
    for pn in range(2, pages + 1):
        p = _RequestJson(base_url, page_size, pn, program_id, token, with_canary)
        if p.get("code") != 0:
            raise RuntimeError(
                f"{label} 第{pn}页失败: {json.dumps(p, ensure_ascii=False)[:2000]}"
            )
        _MergePageIntoTh(th, p)
        _MergePageIntoLifestyle(ls, p)
    return th, ls, total, pages


def _Short(x: Any, n: int = 500) -> str:
    if x is None:
        return "null"
    s = json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else str(x)
    return s if len(s) <= n else s[:n] + "..."


def _DeepDiff(a: Any, b: Any, path: str) -> List[Tuple[str, Any, Any]]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[Tuple[str, Any, Any]] = []
        for k in sorted(set(a) | set(b)):
            p = f"{path}.{k}" if path else k
            if k not in a:
                out.append((p, None, b.get(k)))
            elif k not in b:
                out.append((p, a.get(k), None))
            else:
                out.extend(_DeepDiff(a[k], b[k], p))
        return out
    if a != b:
        return [(path or "root", a, b)]
    return []


def _PrintDiffBlock(
    title: str,
    can_map: Dict[str, Any],
    no_map: Dict[str, Any],
    n_print: int,
    n_print_max: int,
) -> int:
    """按 resourceId 做集合差与共同条目的深度比较；若达 n_print_max 处差异则停。"""
    sc, sn = set(can_map), set(no_map)
    only_c = sorted(sc - sn)
    only_n = sorted(sn - sc)
    com = sc & sn
    print(title)
    print("  去重后条数: canary=", len(can_map), " 无x-version=", len(no_map), end="  ")
    if len(only_c) or len(only_n):
        print("仅 canary 多:", len(only_c), "条  仅 无x-version 多:", len(only_n), "条  共同:", len(com), "条")
    else:
        print("  id 集合差: 0（条数/集合均一致时）" if can_map or no_map else "（本桶无数据或均无 resourceId）")
    if only_c:
        print("  — 仅 canary: ", ", ".join(only_c))
    if only_n:
        print("  — 仅 无x-version: ", ", ".join(only_n))
    for rid in sorted(com):
        for p, va, vb in _DeepDiff(can_map[rid], no_map[rid], f"{rid}"):
            if n_print >= n_print_max:
                print("  …（本块已达差异输出上限，见脚本 PAPI_MAX_DIFFS_PER_BLOCK）", flush=True)
                return n_print
            print(f"  {p}")
            print(f"    canary:  {_Short(va)}")
            print(f"    nover:  {_Short(vb)}")
            n_print += 1
    return n_print


def Main() -> int:
    token = os.environ.get("PAPI_SANDBOX_BEARER", "").strip()
    if not token:
        print("请设置环境变量 PAPI_SANDBOX_BEARER 为与 sandbox 一致的 Bearer（不含「Bearer 」前缀）。", file=sys.stderr)
        return 2
    program_id = os.environ.get("PAPI_SANDBOX_PROGRAM_ID", "1919249349977088").strip()
    base = os.environ.get("PAPI_RESOURCES_URL", "https://developer-sandbox.dragonpass.com/api/v2/resources")
    page_size = int(os.environ.get("PAPI_PAGE_SIZE", "100"))

    n_max = int(os.environ.get("PAPI_MAX_DIFFS_PER_BLOCK", "200"))

    _report = Path(__file__).resolve().parent / "_last_compare_run.txt"
    _rf: TextIO = _report.open("w", encoding="utf-8", newline="")
    _old = sys.stdout
    sys.stdout = _TeeOut(_old, _rf)  # type: ignore[assignment]
    try:
        return _RunCompareBody(base, page_size, program_id, token, n_max)
    finally:
        sys.stdout = _old
        _rf.close()


def _RunCompareBody(
    base: str,
    page_size: int,
    program_id: str,
    token: str,
    n_max: int,
) -> int:
    print("拉取 canary 全量分页…", flush=True)
    can_th, can_ls, can_total, can_pages = _FetchAllPages(
        base, page_size, program_id, token, True, "canary"
    )
    print(
        f"  totalNumber={can_total} 页数={can_pages}  "
        f"transport 条数={len(can_th)}  lifestyle 条数={len(can_ls)}",
        flush=True,
    )

    print("拉取无 x-version 全量分页…", flush=True)
    no_th, no_ls, no_total, no_pages = _FetchAllPages(
        base, page_size, program_id, token, False, "无 canary"
    )
    print(
        f"  totalNumber={no_total} 页数={no_pages}  "
        f"transport 条数={len(no_th)}  lifestyle 条数={len(no_ls)}",
        flush=True,
    )

    print()
    print("========== 分页总量（接口 data.pagination，含两类资源总数）==========")
    print(f"  canary:       totalNumber={can_total}  transport+LS 分桶: {len(can_th)}+{len(can_ls)}")
    print(f"  无 x-version: totalNumber={no_total}  transport+LS 分桶: {len(no_th)}+{len(no_ls)}")
    if can_total - no_total != 0 or len(can_th) - len(no_th) or len(can_ls) - len(no_ls):
        print(f"  差: totalNumber = {can_total - no_total:+d}  transport 去重 = {len(can_th) - len(no_th):+d}  lifestyle 去重 = {len(can_ls) - len(no_ls):+d}")
    print("  注：totalNumber 为接口声明的总数；下述按 `transportHubResources` / `lifestyleResources` 分桶，仅用含 `resourceId` 的条目可对比。")
    print()

    print("========== transportHubResources（按 resourceId）==========", flush=True)
    n_print = _PrintDiffBlock("【transport 差异详情】", can_th, no_th, 0, n_max)
    if n_print == 0 and (can_th or no_th):
        print("  （本桶无叶子字段差异；id 仅在一侧有则已列于上。）", flush=True)
    print()
    print("========== lifestyleResources（按 resourceId）==========", flush=True)
    n_life = _PrintDiffBlock("【lifestyle 差异详情】", can_ls, no_ls, 0, n_max)
    if n_life == 0 and not (can_ls or no_ls):
        print("  （全量中 lifestyle 桶为 0：当前 Program/本接口在 sandbox 中未回传含 `resourceId` 的 lifestyle 项。此前合并进 transport 的对比已拆桶；若你环境中有 lifestyle 数据，此处会列出。）", flush=True)
    elif n_life == 0 and (can_ls or no_ls):
        print("  （本桶无叶子字段差异；id 仅在一侧有则已列于上。）", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
