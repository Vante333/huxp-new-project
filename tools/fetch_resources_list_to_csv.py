"""分页调用 GET /api/v2/resources，导出为 CSV（countryOrRegion,resourceIds,iata,transportHubId）。

必填请求头：Authorization（Bearer）、X-Program-ID、X-Request-ID（每请求自动生成 UUID）、Content-Type。

凭据请通过环境变量或命令行传入，勿将真实 Token 写入仓库。

用法（PowerShell）::

    $env:RESOURCES_BEARER_TOKEN = \"eyJ...\"
    python tools/fetch_resources_list_to_csv.py --program-id 1919249349977088 --module 1 --output resources.csv

也可使用 ``--bearer-token``（注意 shell 历史记录风险）。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import uuid
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

JsonDict = Dict[str, Any]


class ResourcesExportError(RuntimeError):
    """导出失败时抛出，附带可读原因。"""


def _AsStr(value: Optional[Union[str, int, float]]) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _GetLocationInfo(item: Mapping[str, Any]) -> Mapping[str, Any]:
    raw = item.get("locationInfo")
    if isinstance(raw, dict):
        return cast(Mapping[str, Any], raw)
    return {}


def ExtractCsvRowsFromResourceItem(item: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    """从单条资源记录提取 CSV 四列（空值转为空字符串）。"""
    loc = _GetLocationInfo(item)
    country = _AsStr(loc.get("countryOrRegion"))
    rid = _AsStr(item.get("resourceId") or item.get("resourceIds"))
    iata = _AsStr(loc.get("iata"))
    hub = _AsStr(loc.get("transportHubId"))
    return country, rid, iata, hub


def IterateResourceArrays(resources_obj: Any) -> Iterable[Mapping[str, Any]]:
    """遍历 ``data.resources`` 下各数组中的资源条目。"""
    if not isinstance(resources_obj, dict):
        return
    res = cast(Dict[str, Any], resources_obj)
    for key in ("transportHubResources", "lifestyleResources"):
        arr = res.get(key)
        if not isinstance(arr, list):
            continue
        for elem in arr:
            if isinstance(elem, dict):
                yield cast(Mapping[str, Any], elem)


def FetchResourcesPage(
    *,
    base_url: str,
    module: str,
    page_number: int,
    page_size: int,
    language: str,
    program_id: str,
    bearer_token: str,
    timeout_sec: float,
) -> JsonDict:
    """请求单页资源列表并解析 JSON。"""
    q: Dict[str, Union[str, int]] = {
        "module": module,
        "pageNumber": page_number,
        "pageSize": page_size,
        "language": language,
    }
    path = "/api/v2/resources"
    full_url = f"{base_url.rstrip('/')}{path}?{urlencode(q)}"
    req_id = str(uuid.uuid4())
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Program-ID": program_id,
        "X-Request-ID": req_id,
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    req = Request(full_url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ResourcesExportError(
            f"HTTP {exc.code} 请求失败: {full_url}\n响应体（截断）: {body[:2000]}"
        ) from exc
    except URLError as exc:
        raise ResourcesExportError(f"网络错误，无法请求 {full_url}: {exc!r}") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ResourcesExportError(f"响应非合法 JSON（前 500 字符）: {raw[:500]!r}") from exc
    if not isinstance(parsed, dict):
        raise ResourcesExportError(f"响应根节点必须为 JSON 对象，实际: {type(parsed).__name__}")
    return cast(JsonDict, parsed)


def _ParsePagination(body: JsonDict) -> Tuple[int, int, int]:
    data = body.get("data")
    if not isinstance(data, dict):
        raise ResourcesExportError(f"成功响应缺少 data 对象: {body!r}")
    pag = data.get("pagination")
    if not isinstance(pag, dict):
        raise ResourcesExportError(f"data 缺少 pagination: {data!r}")
    try:
        page_size = int(pag["pageSize"])
        page_number = int(pag["pageNumber"])
        total_number = int(pag["totalNumber"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ResourcesExportError(f"pagination 字段异常: {pag!r}") from exc
    if page_size < 1:
        raise ResourcesExportError(f"非法 pageSize: {page_size}")
    return page_size, page_number, total_number


def ComputeTotalPages(total_number: int, page_size: int) -> int:
    if total_number <= 0:
        return 1
    return (total_number + page_size - 1) // page_size


def RunExportResourcesToCsv(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 入口：分页拉取并写入 CSV。"""
    parser = argparse.ArgumentParser(description="分页导出 GET /api/v2/resources 为 CSV")
    parser.add_argument(
        "--base-url",
        default="https://developer-sandbox.dragonpass.com",
        help="API 网关根 URL（不含路径）",
    )
    parser.add_argument("--module", default="1", help="query module，如 lounge=1")
    parser.add_argument("--language", default="en-US", help="query language")
    parser.add_argument("--page-size", type=int, default=100, help="每页条数 1–100")
    parser.add_argument("--program-id", required=True, help="请求头 X-Program-ID")
    parser.add_argument(
        "--output",
        "-o",
        default="resources_export.csv",
        help="输出 CSV 路径",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="单次 HTTP 超时（秒）",
    )
    parser.add_argument(
        "--bearer-token",
        default=os.environ.get("RESOURCES_BEARER_TOKEN", "").strip(),
        help="Bearer Token（不含前缀）；也可设置环境变量 RESOURCES_BEARER_TOKEN",
    )
    parser.add_argument(
        "--module-filter",
        type=int,
        default=None,
        help="仅导出 module 等于该整数的行；未指定且 --module 为纯数字时自动使用该数字",
    )
    parser.add_argument(
        "--no-module-row-filter",
        action="store_true",
        help="关闭按 module 过滤行（默认在 --module 为纯数字时会只保留该 module 的行）",
    )
    parser.add_argument(
        "--utf8-bom",
        action="store_true",
        help="使用带 BOM 的 UTF-8，便于 Excel 直接打开",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    module_filter: Optional[int] = args.module_filter
    if not args.no_module_row_filter:
        if module_filter is None:
            ms = str(args.module).strip()
            if ms.isdigit():
                module_filter = int(ms)

    token = (args.bearer_token or "").strip()
    if not token:
        print(
            "错误：未提供 Bearer Token。请设置环境变量 RESOURCES_BEARER_TOKEN 或使用 --bearer-token。",
            file=sys.stderr,
        )
        return 2

    if not (1 <= int(args.page_size) <= 100):
        print("错误：--page-size 必须在 1–100 之间。", file=sys.stderr)
        return 2

    rows_buffer: List[Tuple[str, str, str, str]] = []
    page_size_used: Optional[int] = None
    total_pages: Optional[int] = None

    page_num = 1
    while True:
        body = FetchResourcesPage(
            base_url=args.base_url,
            module=str(args.module),
            page_number=page_num,
            page_size=int(args.page_size),
            language=str(args.language),
            program_id=str(args.program_id),
            bearer_token=token,
            timeout_sec=float(args.timeout),
        )
        code = body.get("code")
        if code != 0:
            msg = body.get("msg") or body.get("message") or body
            raise ResourcesExportError(f"业务失败 code={code!r}: {msg!r}")

        ps, _pn, total_number = _ParsePagination(body)
        if page_size_used is None:
            page_size_used = ps
            total_pages = ComputeTotalPages(total_number, ps)
        data = body.get("data")
        if not isinstance(data, dict):
            raise ResourcesExportError(f"缺少 data: {body!r}")
        resources_obj = data.get("resources")

        for item in IterateResourceArrays(resources_obj):
            mod = item.get("module")
            if module_filter is not None:
                try:
                    if int(mod) != int(module_filter):
                        continue
                except (TypeError, ValueError):
                    continue
            rows_buffer.append(ExtractCsvRowsFromResourceItem(item))

        if total_pages is not None and page_num >= total_pages:
            break
        page_num += 1
        if page_num > 5000:
            raise ResourcesExportError("分页超过 5000 页，中止以防死循环；请检查 totalNumber / pageSize。")

    encoding = "utf-8-sig" if args.utf8_bom else "utf-8"
    out_path = os.path.abspath(str(args.output))
    try:
        with open(out_path, "w", newline="", encoding=encoding) as fp:
            w = csv.writer(fp)
            w.writerow(["countryOrRegion", "resourceIds", "iata", "transportHubId"])
            for row in rows_buffer:
                w.writerow(list(row))
    except OSError as exc:
        raise ResourcesExportError(f"无法写入文件 {out_path}: {exc!r}") from exc

    print(f"已写入 {len(rows_buffer)} 行 -> {out_path}")
    return 0


def main() -> None:
    try:
        code = RunExportResourcesToCsv()
    except ResourcesExportError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
