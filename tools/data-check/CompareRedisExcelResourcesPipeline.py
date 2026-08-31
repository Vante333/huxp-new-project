"""核对流水线：Redis 新旧 JSON → Excel 交集 → 资源列表 → 基线 vs canary → diningOptions 对拍。

用法（PowerShell）::

    $env:DP_CLIENT_ID = \"...\"
    $env:DP_CLIENT_SECRET = \"...\"
    python tools/data-check/CompareRedisExcelResourcesPipeline.py `
      --old-json \"C:\\path\\旧json.txt\" `
      --new-json \"C:\\path\\新json.txt\" `
      --excel \"D:\\path\\单一价格.xlsx\" `
      --dining-json \"D:\\path\\discount_promo.json\" `
      --program-id 2036766110032896 `
      --language ja-JP

无旧 JSON / 无单一价表时省略 ``--old-json`` / ``--excel``：Step1 只统计新侧；
Step2 不与 Excel 求交，Final=新侧 ``hasLgNetworkData=true`` 集合。
``--dining-json`` 为 Step5：按 ``FD_PCODE`` 对拍列表/详情 ``diningOptions``
（入参分别 ``module=5`` 与 ``module=6``；对拍取 ``diningOptions`` 中 ``module=5``
的 ``optionName``/``description``，对应 ``FD_DISCOUNT``/``FD_NOTE``，备注为空则回退优惠值；
接口返回值与源 JSON 逐字对比，``\\r\\n`` 保留为原值、不折叠成空格）；省略则跳过 Step5。

``--language`` 会传给 Step3 列表、Step4 详情与 Step5。凭据勿写入仓库；
Token 也可 ``--bearer-token`` 或环境变量 ``RESOURCES_BEARER_TOKEN``。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openpyxl import load_workbook

JsonDict = Dict[str, Any]
DiffItem = Dict[str, Any]


class PipelineError(RuntimeError):
    """流水线失败。"""


def _AsStr(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def LoadJsonFile(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise PipelineError(f"无法读取 JSON: {path}: {exc}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise PipelineError(f"JSON 解析失败: {path}: {exc}") from exc


def ResolveRedisCacheKey(root: Any, *, module: int, redis_key: Optional[str] = None) -> Optional[str]:
    """选定 Redis 顶层键：优先 ``--redis-key``，否则 ``str(module)``，再否则单 list 键。"""
    if not isinstance(root, dict):
        return None
    if redis_key:
        key = str(redis_key).strip()
        if key not in root or not isinstance(root.get(key), list):
            raise PipelineError(f"Redis JSON 缺少列表键 {key!r}，现有键: {list(root.keys())}")
        return key
    preferred = str(module)
    if preferred in root and isinstance(root.get(preferred), list):
        return preferred
    list_keys = [str(k) for k, v in root.items() if isinstance(v, list)]
    if len(list_keys) == 1:
        return list_keys[0]
    if not list_keys:
        raise PipelineError(f"Redis JSON 无列表键，现有键: {list(root.keys())}")
    # 多键并存（如 setmeal 的 3/6）时必须用 module 对齐，避免重复计数
    raise PipelineError(
        f"Redis JSON 存在多个列表键 {list_keys}，请用 --module 对应键（如 setmeal=3）"
        " 或显式 --redis-key"
    )


def IterRedisCacheItems(
    root: Any,
    *,
    redis_key: Optional[str] = None,
) -> List[Mapping[str, Any]]:
    """展开 Redis 缓存资源对象列表；``redis_key`` 指定时只读该顶层键。"""
    items: List[Mapping[str, Any]] = []
    if isinstance(root, list):
        raw_lists: List[Any] = [root]
    elif isinstance(root, dict):
        if redis_key is not None:
            arr = root.get(redis_key)
            raw_lists = [arr] if isinstance(arr, list) else []
        else:
            raw_lists = [v for v in root.values() if isinstance(v, list)]
    else:
        raise PipelineError(f"Redis JSON 根节点类型不支持: {type(root).__name__}")
    for arr in raw_lists:
        for elem in arr:
            if isinstance(elem, dict):
                items.append(cast(Mapping[str, Any], elem))
    return items


def _AssociateOrResourceId(item: Mapping[str, Any]) -> str:
    """接口侧 ID：优先 ``resourceId``（列表/详情 path 用），否则 ``associateCode``。

    setmeal 场景下二者常同为 R 码；lounge 若 ``associateCode`` 为 P 码而列表仍用 N 码，
    必须以 ``resourceId`` 为准，避免 Step3/4 对错 ID。
    """
    return _AsStr(item.get("resourceId") or item.get("resourceIds") or item.get("associateCode"))


def AnalyzeRedisLgCodes(
    root: Any,
    *,
    redis_key: Optional[str] = None,
) -> Tuple[Set[str], Dict[str, int], Dict[str, str]]:
    """提取 ``hasLgNetworkData is True`` 的 ``networkCode``，并返回诊断计数与 N→R 映射。

    映射：``networkCode -> associateCode|resourceId``（餐食体验厅如图：N04043→R05084）。
    """
    items = IterRedisCacheItems(root, redis_key=redis_key)
    true_rows = 0
    codes: Set[str] = set()
    net_to_assoc: Dict[str, str] = {}
    for item in items:
        if item.get("hasLgNetworkData") is not True:
            continue
        true_rows += 1
        code = _AsStr(item.get("networkCode"))
        if not code:
            continue
        codes.add(code)
        assoc = _AssociateOrResourceId(item)
        if assoc:
            # 新侧优先覆盖（调用方先旧后新合并时可覆盖）
            net_to_assoc[code] = assoc
    stats = {
        "arrayLen": len(items),
        "hasLgTrueRows": true_rows,
        "uniqueNetworkCodes": len(codes),
    }
    return codes, stats, net_to_assoc


def ExtractLgNetworkCodes(root: Any, *, redis_key: Optional[str] = None) -> Set[str]:
    """从 Redis 缓存根节点提取 ``hasLgNetworkData is True`` 的 ``networkCode`` 集合。"""
    codes, _stats, _map = AnalyzeRedisLgCodes(root, redis_key=redis_key)
    return codes


def MapNetworkCodesToApiIds(
    network_codes: Sequence[str],
    net_to_assoc: Mapping[str, str],
) -> Tuple[List[str], List[str], Dict[str, str]]:
    """Final networkCode → API resourceId（associateCode）；返回 (apiIds, 缺映射N码, 映射表)。"""
    mapping: Dict[str, str] = {}
    missing: List[str] = []
    api_ids: List[str] = []
    for net in network_codes:
        assoc = _AsStr(net_to_assoc.get(net))
        if not assoc:
            missing.append(net)
            continue
        mapping[net] = assoc
        api_ids.append(assoc)
    # 去重且保序
    seen: Set[str] = set()
    uniq: List[str] = []
    for rid in api_ids:
        if rid in seen:
            continue
        seen.add(rid)
        uniq.append(rid)
    return uniq, missing, mapping


_EXCEL_CODE_HEADER_ALIASES: Set[str] = {
    "编码",
    "网点编码",
    "network code",
    "networkcode",
    "resourceid",
    "resource id",
}


def _ExcelHeaderAlias(value: Any) -> str:
    return _AsStr(value).lower().replace("／", "/").replace(" ", "")


def LoadExcelNetworkCodes(path: Path) -> Set[str]:
    """读 Excel 网点编码。

    自动识别表头列：
    - 网络清单：第 1 行 ``编码`` 列，第 2 行起
    - 单一价：第 4 行 ``Network Code`` / ``网点编码``，第 5 行起首列
    - 未识别到表头时回退：第 5 行起取第 1 列
    """
    try:
        wb = load_workbook(str(path), read_only=True, data_only=True)
    except OSError as exc:
        raise PipelineError(f"无法读取 Excel: {path}: {exc}") from exc
    sheet_name = wb.sheetnames[0]
    ws = wb[sheet_name]
    buffered: List[List[Any]] = []
    rest_iter = ws.iter_rows(min_row=1, values_only=True)
    for i, row in enumerate(rest_iter, start=1):
        buffered.append(list(row) if row else [])
        if i >= 6:
            break

    header_row_idx = 0
    code_col_idx = 0
    found = False
    for row_i, cells in enumerate(buffered, start=1):
        for col_i, cell in enumerate(cells):
            alias = _ExcelHeaderAlias(cell)
            if alias in ("模板id", "moduleid"):
                continue
            if (
                alias in _EXCEL_CODE_HEADER_ALIASES
                or "networkcode" in alias
                or alias.endswith("编码")
            ):
                header_row_idx = row_i
                code_col_idx = col_i
                found = True
                break
        if found:
            break

    data_start = header_row_idx + 1 if found else 5

    def _Collect(rows: Iterable[Sequence[Any]], start_row: int) -> Set[str]:
        out: Set[str] = set()
        for row_i, row in enumerate(rows, start=start_row):
            if row_i < data_start or not row or code_col_idx >= len(row):
                continue
            code = _AsStr(row[code_col_idx])
            if code and code.lower() != "none":
                out.add(code)
        return out

    codes = _Collect(buffered, 1)
    codes.update(_Collect(rest_iter, 7))
    wb.close()
    if found:
        print(
            f"Excel 编码列: sheet={sheet_name!r} 表头行={header_row_idx} "
            f"列索引={code_col_idx} 数据起始行={data_start}"
        )
    else:
        print("Excel 未识别到编码表头，回退第 5 行起第 1 列")
    return codes


def _HttpJson(
    *,
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: Optional[bytes] = None,
    timeout_sec: float,
) -> JsonDict:
    req = Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read()
    except HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise PipelineError(
            f"HTTP {exc.code} {method} {url}\n响应体（截断）: {err_body[:2000]}"
        ) from exc
    except URLError as exc:
        raise PipelineError(f"网络错误 {method} {url}: {exc!r}") from exc
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineError(f"响应非 JSON: {raw[:500]!r}") from exc
    if not isinstance(parsed, dict):
        raise PipelineError(f"响应根须为对象: {type(parsed).__name__}")
    return cast(JsonDict, parsed)


def FetchAccessToken(
    *,
    base_url: str,
    program_id: str,
    client_id: str,
    secret: str,
    timeout_sec: float,
    x_version: Optional[str] = None,
) -> str:
    url = f"{base_url.rstrip('/')}/api/v2/auth/token"
    headers = {
        "X-Program-ID": program_id,
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    if x_version:
        headers["x-version"] = x_version
    payload = json.dumps({"clientId": client_id, "secret": secret}).encode("utf-8")
    body = _HttpJson(method="POST", url=url, headers=headers, body=payload, timeout_sec=timeout_sec)
    if body.get("code") not in (0, "0", None):
        # 部分网关成功时 code=0；若直接返回 token 字段也兼容
        if "accessToken" not in str(body) and "token" not in str(body):
            raise PipelineError(f"取 Token 业务失败: {body!r}")
    data = body.get("data")
    token: Optional[str] = None
    if isinstance(data, dict):
        token = _AsStr(data.get("accessToken") or data.get("token") or data.get("access_token"))
    if not token:
        token = _AsStr(body.get("accessToken") or body.get("token"))
    if not token:
        raise PipelineError(f"响应中未找到 accessToken: {body!r}")
    return token


def _AuthHeaders(
    *,
    program_id: str,
    bearer_token: str,
    x_version: Optional[str] = None,
) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Program-ID": program_id,
        "X-Request-ID": str(uuid.uuid4()),
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    if x_version:
        headers["x-version"] = x_version
    return headers


def IterateResourceArrays(resources_obj: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(resources_obj, dict):
        return
    for key in ("transportHubResources", "lifestyleResources"):
        arr = resources_obj.get(key)
        if not isinstance(arr, list):
            continue
        for elem in arr:
            if isinstance(elem, dict):
                yield cast(Mapping[str, Any], elem)


def FetchAllResourcesList(
    *,
    base_url: str,
    module: int,
    page_size: int,
    language: Optional[str],
    program_id: str,
    bearer_token: str,
    timeout_sec: float,
    x_version: Optional[str] = None,
) -> Tuple[int, Dict[str, JsonDict]]:
    """分页拉取列表，返回 ``(totalNumber, {resourceId: item})``。"""
    by_id: Dict[str, JsonDict] = {}
    total_number = 0
    page_num = 1
    total_pages = 1
    while page_num <= total_pages:
        q: Dict[str, Union[str, int]] = {
            "module": module,
            "pageNumber": page_num,
            "pageSize": page_size,
        }
        if language:
            q["language"] = language
        url = f"{base_url.rstrip('/')}/api/v2/resources?{urlencode(q)}"
        body = _HttpJson(
            method="GET",
            url=url,
            headers=_AuthHeaders(program_id=program_id, bearer_token=bearer_token, x_version=x_version),
            timeout_sec=timeout_sec,
        )
        if body.get("code") != 0:
            raise PipelineError(f"资源列表业务失败 page={page_num}: {body.get('msg') or body!r}")
        data = body.get("data")
        if not isinstance(data, dict):
            raise PipelineError(f"列表缺少 data: {body!r}")
        pag = data.get("pagination")
        if not isinstance(pag, dict):
            raise PipelineError(f"列表缺少 pagination: {data!r}")
        try:
            ps = int(pag["pageSize"])
            total_number = int(pag["totalNumber"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PipelineError(f"pagination 异常: {pag!r}") from exc
        if page_num == 1:
            total_pages = 1 if total_number <= 0 else (total_number + ps - 1) // ps
        for item in IterateResourceArrays(data.get("resources")):
            rid = _AsStr(item.get("resourceId") or item.get("resourceIds"))
            if rid:
                by_id[rid] = dict(item)
        page_num += 1
        if page_num > 5000:
            raise PipelineError("分页超过 5000，中止")
    return total_number, by_id


def FetchResourceDetail(
    *,
    base_url: str,
    resource_id: str,
    module: int,
    language: Optional[str],
    program_id: str,
    bearer_token: str,
    timeout_sec: float,
    x_version: Optional[str] = None,
) -> JsonDict:
    q: Dict[str, Union[str, int]] = {"module": module}
    if language:
        q["language"] = language
    url = f"{base_url.rstrip('/')}/api/v2/resources/{resource_id}?{urlencode(q)}"
    body = _HttpJson(
        method="GET",
        url=url,
        headers=_AuthHeaders(program_id=program_id, bearer_token=bearer_token, x_version=x_version),
        timeout_sec=timeout_sec,
    )
    if body.get("code") != 0:
        raise PipelineError(
            f"详情失败 resourceId={resource_id} x-version={x_version!r}: {body.get('msg') or body!r}"
        )
    data = body.get("data")
    if not isinstance(data, dict):
        raise PipelineError(f"详情缺少 data: resourceId={resource_id}")
    return cast(JsonDict, data)


_BLANK_NOTE_TOKENS: Set[str] = {"", "(null)", "null", "none", "n/a", "-"}
_DINING_NULL_TOKENS: Set[str] = {"", "(null)", "null"}


def DiningRawText(value: Any) -> str:
    """dining 字段转字符串：接口/源 JSON 原值，不转义、不折叠。"""
    if value is None:
        return ""
    return str(value)


def CollapseDiningWhitespace(value: Any) -> str:
    """把换行与连续空白折成单空格，仅用于给差异分组打标。"""
    return " ".join(DiningRawText(value).split())


def IsBlankDiningNote(value: Any) -> bool:
    """``FD_NOTE`` 是否视为空（含 Oracle 导出的 ``(null)``）。"""
    if value is None:
        return True
    return DiningRawText(value).lower() in _BLANK_NOTE_TOKENS


def IsDiningNullLike(value: Any) -> bool:
    """JSON ``null``、空串、字面量 ``(null)`` / ``null`` 视为同一空值；纯换行不算空。"""
    if value is None:
        return True
    return DiningRawText(value).lower() in _DINING_NULL_TOKENS


def DiningFieldEquals(left: Any, right: Any) -> bool:
    """两侧都空视为相等；有值则与源 JSON / 接口返回值逐字相同（保留 ``\\r\\n`` / ``\\n``）。"""
    if IsDiningNullLike(left) and IsDiningNullLike(right):
        return True
    return DiningRawText(left) == DiningRawText(right)


def IsDiningNewlineOnlyDiff(left: Any, right: Any) -> bool:
    """原文不等，但折叠空白后文案相同（空格 vs ``\\r\\n`` / ``\\n``）。"""
    if DiningFieldEquals(left, right):
        return False
    if IsDiningNullLike(left) or IsDiningNullLike(right):
        return False
    return CollapseDiningWhitespace(left) == CollapseDiningWhitespace(right)


def ExpectedDiningDescription(discount: str, note: Any) -> str:
    """``description`` 期望值：备注为空则回退优惠值；非空备注保持原文。"""
    if IsBlankDiningNote(note):
        return discount
    return DiningRawText(note)


def _DiningRawDisplay(value: Any) -> str:
    """按 JSON 字符串写法展示接口/源原值，保留 ``\\r\\n``，不再二次加工。"""
    if value is None:
        return "(null)"
    return json.dumps(value, ensure_ascii=False)


_STEP5_STRUCTURAL_ISSUES: Set[str] = {
    "not_in_list",
    "missing_module5_diningOptions",
    "missing_module6_diningOptions",
    "optionName_not_found",
}


def ExtractDiningOptions(payload: Any) -> List[JsonDict]:
    """从列表项或详情中收集 ``diningOptions``（去重）。"""
    found: List[JsonDict] = []

    def Walk(node: Any) -> None:
        if isinstance(node, dict):
            opts = node.get("diningOptions")
            if isinstance(opts, list):
                for item in opts:
                    if isinstance(item, dict):
                        found.append(dict(item))
            for child in node.values():
                Walk(child)
        elif isinstance(node, list):
            for elem in node:
                Walk(elem)

    Walk(payload)
    uniq: List[JsonDict] = []
    seen: Set[str] = set()
    for item in found:
        key = json.dumps(item, ensure_ascii=False, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def DiningOptionsByModule(
    options: Sequence[Mapping[str, Any]], option_module: int
) -> List[JsonDict]:
    """筛指定 ``module`` 的 diningOptions（入参 6 时仍可能混有 coupon 与 discount）。"""
    out: List[JsonDict] = []
    want = {option_module, str(option_module)}
    for item in options:
        if item.get("module") in want:
            out.append(dict(item))
    return out


def Module5DiningOptions(options: Sequence[Mapping[str, Any]]) -> List[JsonDict]:
    """筛 ``module=5`` 的 diningOptions。"""
    return DiningOptionsByModule(options, 5)


def LoadDiningDiscountExpected(path: Path) -> Dict[str, JsonDict]:
    """读 Step5 JSON：``data[].FD_PCODE / FD_DISCOUNT / FD_NOTE / FD_MODE_TYPE``。"""
    root = LoadJsonFile(path)
    rows: List[Any]
    if isinstance(root, dict):
        data = root.get("data")
        if not isinstance(data, list):
            raise PipelineError(f"dining JSON 缺少 data 数组: {path}")
        rows = data
    elif isinstance(root, list):
        rows = root
    else:
        raise PipelineError(f"dining JSON 根节点类型不支持: {type(root).__name__}")
    expected: Dict[str, JsonDict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = _AsStr(row.get("FD_PCODE") or row.get("resourceId") or row.get("networkCode"))
        if not code:
            continue
        discount = DiningRawText(row.get("FD_DISCOUNT"))
        note = row.get("FD_NOTE")
        expected[code] = {
            "mode": DiningRawText(row.get("FD_MODE_TYPE")),
            "discount": discount,
            "noteRaw": DiningRawText(note),
            "noteBlank": IsBlankDiningNote(note),
            "expectedOptionName": discount,
            "expectedDescription": ExpectedDiningDescription(discount, note),
        }
    if not expected:
        raise PipelineError(f"dining JSON 未解析到 FD_PCODE: {path}")
    return expected


def ClassifyDiningDiff(
    *,
    expected_name: Any,
    expected_desc: Any,
    actual_name: Any,
    actual_desc: Any,
) -> str:
    """给 Step5 差异打可读类型。有值时接口返回与源 JSON 逐字对比。"""
    name_ok = DiningFieldEquals(expected_name, actual_name)
    desc_ok = DiningFieldEquals(expected_desc, actual_desc)
    if name_ok and desc_ok:
        return "matched"
    name_nl = (not name_ok) and IsDiningNewlineOnlyDiff(expected_name, actual_name)
    desc_nl = (not desc_ok) and IsDiningNewlineOnlyDiff(expected_desc, actual_desc)
    if name_ok and desc_nl:
        return "description_newline_mismatch"
    if name_nl and desc_ok:
        return "optionName_newline_mismatch"
    if name_nl and desc_nl:
        return "optionName+description_newline_mismatch"
    issues: List[str] = []
    if not name_ok:
        issues.append("optionName")
    if not desc_ok:
        issues.append("description")
    return "+".join(issues) + "_mismatch" if issues else "mismatch"


def IsStructuralDiningIssue(issue: Any) -> bool:
    """缺项 / 未找到 option 等结构问题，不是文本内容差异。"""
    key = str(issue or "")
    if key in _STEP5_STRUCTURAL_ISSUES:
        return True
    return key.startswith("missing_")


def DiningStoredDiffStillOpen(row: Mapping[str, Any]) -> bool:
    """已落盘的差异行在逐字规则下是否仍算不一致。"""
    if IsStructuralDiningIssue(row.get("issue")):
        return True
    return not (
        DiningFieldEquals(row.get("expectedOptionName"), row.get("actualOptionName"))
        and DiningFieldEquals(row.get("expectedDescription"), row.get("actualDescription"))
    )


def ReclassifyDiningDiffRow(row: Mapping[str, Any]) -> JsonDict:
    """按接口返回 vs 源 JSON 逐字规则重打 issue；结构问题保持原 issue。"""
    out = dict(row)
    if IsStructuralDiningIssue(out.get("issue")):
        return out
    out["issue"] = ClassifyDiningDiff(
        expected_name=out.get("expectedOptionName"),
        expected_desc=out.get("expectedDescription"),
        actual_name=out.get("actualOptionName"),
        actual_desc=out.get("actualDescription"),
    )
    return out


def FilterOpenDiningDiffs(rows: Sequence[Mapping[str, Any]]) -> List[JsonDict]:
    """丢掉逐字已一致的旧差异，剩余行按新规则重分类。"""
    opened: List[JsonDict] = []
    for row in rows:
        if not DiningStoredDiffStillOpen(row):
            continue
        refreshed = ReclassifyDiningDiffRow(row)
        if refreshed.get("issue") == "matched":
            continue
        opened.append(refreshed)
    return opened


def CompareDiningOptionRow(
    *,
    resource_id: str,
    expected_name: str,
    expected_desc: str,
    actual_options: Sequence[Mapping[str, Any]],
    option_module: int = 5,
) -> Optional[JsonDict]:
    """单条编码对拍；一致返回 None。只匹配 ``diningOptions.module=option_module``（默认 5）。"""
    opts = DiningOptionsByModule(actual_options, option_module)
    missing_issue = f"missing_module{option_module}_diningOptions"
    if not opts:
        return {
            "resourceId": resource_id,
            "issue": missing_issue,
            "optionModule": option_module,
            "expectedOptionName": expected_name,
            "expectedDescription": expected_desc,
            "actualOptionName": None,
            "actualDescription": None,
            "actual": [],
        }
    matched: Optional[Mapping[str, Any]] = None
    for item in opts:
        if DiningFieldEquals(item.get("optionName"), expected_name):
            matched = item
            break
    if matched is None and len(opts) == 1:
        matched = opts[0]
    if matched is None:
        return {
            "resourceId": resource_id,
            "issue": "optionName_not_found",
            "optionModule": option_module,
            "expectedOptionName": expected_name,
            "expectedDescription": expected_desc,
            "actualOptionName": None,
            "actualDescription": None,
            "actual": [
                {
                    "optionName": item.get("optionName"),
                    "description": item.get("description"),
                    "module": item.get("module"),
                }
                for item in opts
            ],
        }
    actual_name = matched.get("optionName")
    actual_desc = matched.get("description")
    if DiningFieldEquals(actual_name, expected_name) and DiningFieldEquals(
        actual_desc, expected_desc
    ):
        return None
    issue = ClassifyDiningDiff(
        expected_name=expected_name,
        expected_desc=expected_desc,
        actual_name=actual_name,
        actual_desc=actual_desc,
    )
    return {
        "resourceId": resource_id,
        "issue": issue,
        "optionModule": option_module,
        "expectedOptionName": expected_name,
        "expectedDescription": expected_desc,
        "actualOptionName": actual_name,
        "actualDescription": actual_desc,
        "optionCount": len(opts),
        "module5OptionCount": len(opts),
    }


def RunStep5DiningOptions(
    *,
    expected: Mapping[str, JsonDict],
    list_by_id: Mapping[str, JsonDict],
    list_total: int,
    base_url: str,
    module: int,
    language: Optional[str],
    program_id: str,
    bearer_token: str,
    x_version: Optional[str],
    workers: int,
    timeout_sec: float,
    option_module: int = 5,
) -> JsonDict:
    """Step5：源 JSON vs 指定入参 ``module`` 的列表+详情；对拍 ``diningOptions.module=option_module``。"""
    list_diffs: List[JsonDict] = []
    list_missing: List[str] = []
    for code, exp in sorted(expected.items()):
        expected_name = str(exp["expectedOptionName"])
        expected_desc = str(exp["expectedDescription"])
        item = list_by_id.get(code)
        if item is None:
            list_missing.append(code)
            list_diffs.append(
                {
                    "resourceId": code,
                    "issue": "not_in_list",
                    "queryModule": module,
                    "optionModule": option_module,
                    "expectedOptionName": expected_name,
                    "expectedDescription": expected_desc,
                    "actualOptionName": None,
                    "actualDescription": None,
                }
            )
            continue
        diff = CompareDiningOptionRow(
            resource_id=code,
            expected_name=expected_name,
            expected_desc=expected_desc,
            actual_options=ExtractDiningOptions(item),
            option_module=option_module,
        )
        if diff is not None:
            diff["queryModule"] = module
            list_diffs.append(diff)

    codes = sorted(expected.keys())
    detail_diffs: List[JsonDict] = []
    detail_errors: List[JsonDict] = []

    def FetchOne(rid: str) -> Tuple[str, Optional[JsonDict], Optional[str]]:
        try:
            data = FetchResourceDetail(
                base_url=base_url,
                resource_id=rid,
                module=module,
                language=language,
                program_id=program_id,
                bearer_token=bearer_token,
                timeout_sec=timeout_sec,
                x_version=x_version,
            )
            return rid, data, None
        except Exception as exc:  # noqa: BLE001
            return rid, None, str(exc)

    print(
        f"Step5 入参 module={module} 并发拉详情 workers={workers}，共 {len(codes)} 个 ..."
    )
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(FetchOne, rid) for rid in codes]
        for fut in as_completed(futures):
            rid, data, err = fut.result()
            done += 1
            if done % 50 == 0 or done == len(codes):
                print(f"  Step5 module={module} 详情进度 {done}/{len(codes)}")
            exp = expected[rid]
            if err:
                detail_errors.append(
                    {"resourceId": rid, "error": err, "queryModule": module}
                )
                continue
            assert data is not None
            diff = CompareDiningOptionRow(
                resource_id=rid,
                expected_name=str(exp["expectedOptionName"]),
                expected_desc=str(exp["expectedDescription"]),
                actual_options=ExtractDiningOptions(data),
                option_module=option_module,
            )
            if diff is not None:
                diff["queryModule"] = module
                detail_diffs.append(diff)

    blank_note = sum(1 for exp in expected.values() if bool(exp.get("noteBlank")))
    return {
        "skipped": False,
        "queryModule": module,
        "optionModule": option_module,
        "expectedCount": len(expected),
        "blankNoteFallbackCount": blank_note,
        "listTotalNumber": list_total,
        "listDiffCount": len(list_diffs),
        "detailDiffCount": len(detail_diffs),
        "detailErrorCount": len(detail_errors),
        "listMissingCount": len(list_missing),
        "listMissing": list_missing,
        "listDiffs": sorted(list_diffs, key=lambda x: str(x.get("resourceId") or "")),
        "detailDiffs": sorted(detail_diffs, key=lambda x: str(x.get("resourceId") or "")),
        "detailErrors": detail_errors,
        "xVersion": x_version,
    }


STEP5_QUERY_MODULES: Tuple[int, ...] = (5, 6)


# Step4 默认忽略的字段路径（不参与基线 vs canary 对拍）
DEFAULT_IGNORE_DIFF_PATHS: Tuple[str, ...] = ("$.lastUpdatedTime",)


def DeepDiff(
    left: Any,
    right: Any,
    path: str = "$",
    *,
    ignore_paths: Optional[Sequence[str]] = None,
) -> List[DiffItem]:
    """字段全集深比对，返回差异列表；``ignore_paths`` 中的路径整段跳过。"""
    ignored = set(ignore_paths if ignore_paths is not None else DEFAULT_IGNORE_DIFF_PATHS)
    if path in ignored:
        return []
    diffs: List[DiffItem] = []
    if type(left) is not type(right) and not (
        isinstance(left, (int, float)) and isinstance(right, (int, float))
    ):
        # None vs 缺省等仍记差异
        if left != right:
            diffs.append({"path": path, "baseline": left, "canary": right})
        return diffs
    if isinstance(left, dict) and isinstance(right, dict):
        keys = set(left.keys()) | set(right.keys())
        for key in sorted(keys, key=lambda x: str(x)):
            child = f"{path}.{key}"
            if child in ignored:
                continue
            if key not in left:
                diffs.append({"path": child, "baseline": None, "canary": right[key]})
            elif key not in right:
                diffs.append({"path": child, "baseline": left[key], "canary": None})
            else:
                diffs.extend(DeepDiff(left[key], right[key], child, ignore_paths=ignore_paths))
        return diffs
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            diffs.append(
                {
                    "path": f"{path}.length",
                    "baseline": len(left),
                    "canary": len(right),
                }
            )
        for idx in range(max(len(left), len(right))):
            child = f"{path}[{idx}]"
            if child in ignored:
                continue
            if idx >= len(left):
                diffs.append({"path": child, "baseline": None, "canary": right[idx]})
            elif idx >= len(right):
                diffs.append({"path": child, "baseline": left[idx], "canary": None})
            else:
                diffs.extend(DeepDiff(left[idx], right[idx], child, ignore_paths=ignore_paths))
        return diffs
    if left != right:
        diffs.append({"path": path, "baseline": left, "canary": right})
    return diffs


def RunPipeline(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Redis/Excel/资源列表/canary/diningOptions 核对")
    parser.add_argument(
        "--old-json",
        default="",
        help="旧 Redis JSON 路径；省略则跳过新旧对比，仅用新 JSON",
    )
    parser.add_argument("--new-json", required=True, help="新 Redis JSON 路径")
    parser.add_argument(
        "--excel",
        default="",
        help="单一价 Excel 路径；省略则 Step2 不求交，Final=新侧 lg 集合",
    )
    parser.add_argument(
        "--base-url",
        default="https://developer-sandbox.dragonpass.com",
        help="API 网关根 URL",
    )
    parser.add_argument("--program-id", required=True, help="X-Program-ID")
    parser.add_argument("--module", type=int, default=1, help="资源 module，默认 1；亦用于选定 Redis 顶层键")
    parser.add_argument(
        "--redis-key",
        default="",
        help="Redis JSON 顶层列表键（如 setmeal 的 3）；默认取 str(--module)",
    )
    parser.add_argument("--page-size", type=int, default=100, help="列表 pageSize")
    parser.add_argument(
        "--language",
        default="",
        help="Step3 列表 / Step4 详情共用的 language 入参，如 de-DE、ja-JP；默认不传",
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("DP_CLIENT_ID", "").strip(),
        help="鉴权 clientId，或环境变量 DP_CLIENT_ID",
    )
    parser.add_argument(
        "--secret",
        default=os.environ.get("DP_CLIENT_SECRET", "").strip(),
        help="鉴权 secret，或环境变量 DP_CLIENT_SECRET",
    )
    parser.add_argument(
        "--bearer-token",
        default=os.environ.get("RESOURCES_BEARER_TOKEN", "").strip(),
        help="基线侧 Bearer Token（跳过取 token）；也作对比侧默认 Token",
    )
    parser.add_argument(
        "--compare-bearer-token",
        default=os.environ.get("RESOURCES_COMPARE_BEARER_TOKEN", "").strip(),
        help="对比侧 Bearer Token（如 gray）；默认与 --bearer-token 相同",
    )
    parser.add_argument(
        "--baseline-x-version",
        default="",
        help="基线侧 x-version；指定后才做 Step4 版本对拍。默认留空：不对比，Step3 只跑 --compare-x-version（canary）",
    )
    parser.add_argument(
        "--compare-x-version",
        default="canary",
        help="对比侧 x-version，如 canary / gray（默认 canary）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Step4 详情并发数",
    )
    parser.add_argument(
        "--max-detail",
        type=int,
        default=0,
        help="Step4 最多比对多少个 resourceId（0=全部）",
    )
    parser.add_argument(
        "--skip-step4",
        action="store_true",
        help="跳过基线 vs 对比版本字段对拍（未指定 --baseline-x-version 时本来就会跳过）",
    )
    parser.add_argument(
        "--dining-json",
        default="",
        help="Step5 优惠源 JSON（含 FD_PCODE/FD_DISCOUNT/FD_NOTE）；省略则跳过",
    )
    parser.add_argument(
        "--report-dir",
        default="",
        help="报告目录；默认 apifox-reports/redis_excel_resources_pipeline/",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)

    old_json_arg = str(args.old_json or "").strip()
    excel_arg = str(args.excel or "").strip()
    old_path = Path(old_json_arg) if old_json_arg else None
    new_path = Path(args.new_json)
    excel_path = Path(excel_arg) if excel_arg else None
    skip_old = old_path is None
    skip_excel = excel_path is None
    language = str(args.language).strip() or None

    report_dir = Path(args.report_dir) if args.report_dir else Path(
        "apifox-reports/redis_excel_resources_pipeline"
    )
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    # 固定最新文件名，避免每次 pipeline-<stamp> 堆积；JSON 内仍带 generatedAt
    report_path = report_dir / "pipeline-latest.json"
    summary_path = report_dir / "pipeline-latest-summary.md"

    # --- Step1 ---
    new_root = LoadJsonFile(new_path)
    redis_key_arg = str(args.redis_key).strip() or None
    empty_stats: Dict[str, int] = {
        "arrayLen": 0,
        "hasLgTrueRows": 0,
        "uniqueNetworkCodes": 0,
    }
    old_root: Any = None
    if not skip_old:
        assert old_path is not None
        old_root = LoadJsonFile(old_path)
    redis_key = ResolveRedisCacheKey(
        old_root if isinstance(old_root, dict) else new_root,
        module=int(args.module),
        redis_key=redis_key_arg,
    )
    # 若旧文件键集不同，再按新文件解析一次（允许仅一侧有该键时失败更早）
    if isinstance(new_root, dict):
        redis_key = ResolveRedisCacheKey(
            new_root, module=int(args.module), redis_key=redis_key_arg or redis_key
        )
    if skip_old:
        old_codes: Set[str] = set()
        old_stats = dict(empty_stats)
        old_net_to_assoc: Dict[str, str] = {}
    else:
        old_codes, old_stats, old_net_to_assoc = AnalyzeRedisLgCodes(
            old_root, redis_key=redis_key
        )
    new_codes, new_stats, new_net_to_assoc = AnalyzeRedisLgCodes(
        new_root, redis_key=redis_key
    )
    # 映射合并：新覆盖旧
    net_to_assoc: Dict[str, str] = dict(old_net_to_assoc)
    net_to_assoc.update(new_net_to_assoc)
    only_old = sorted(old_codes - new_codes)
    only_new = sorted(new_codes - old_codes)
    step1_common = old_codes & new_codes
    print("========== Step1 Redis hasLgNetworkData=true ==========")
    print(f"Redis 顶层键: {redis_key!r}（module={int(args.module)}）")
    if skip_old:
        print("未提供 --old-json，跳过新旧对比，仅统计新 JSON")
    else:
        print(
            f"旧: 数组条数={old_stats['arrayLen']}  "
            f"hasLgTrue行数={old_stats['hasLgTrueRows']}  "
            f"去重networkCode={old_stats['uniqueNetworkCodes']}"
        )
    print(
        f"新: 数组条数={new_stats['arrayLen']}  "
        f"hasLgTrue行数={new_stats['hasLgTrueRows']}  "
        f"去重networkCode={new_stats['uniqueNetworkCodes']}"
    )
    print(f"新数量(去重): {len(new_codes)}")
    if not skip_old:
        print(f"旧数量(去重): {len(old_codes)}")
        print(f"数量相等: {len(old_codes) == len(new_codes)}")
        print(f"集合相等: {old_codes == new_codes}")
        print(f"仅旧有: {len(only_old)}")
        print(f"仅新有: {len(only_new)}")
        if only_old:
            preview = only_old[:30]
            print(f"仅旧有预览({len(preview)}/{len(only_old)}): {preview}")
        if only_new:
            preview = only_new[:30]
            print(f"仅新有预览({len(preview)}/{len(only_new)}): {preview}")
        if (
            new_stats["arrayLen"] == new_stats["hasLgTrueRows"]
            and new_stats["arrayLen"] < old_stats["arrayLen"]
        ):
            print(
                "提示: 新 JSON 文件内数组本身就只有 "
                f"{new_stats['arrayLen']} 条（且全部 hasLgNetworkData=true），"
                "并非脚本少算；请确认导出是否为完整缓存。"
            )

    # Step2 与「步骤一」交集：有旧 JSON 时用两边共有；否则用新侧全集
    if skip_old:
        step1_for_intersect = new_codes
    else:
        step1_for_intersect = step1_common if step1_common else (new_codes or old_codes)

    # --- Step2 ---
    if skip_excel:
        excel_codes: Set[str] = set()
        final_network_codes = sorted(step1_for_intersect)
        only_excel: List[str] = []
        only_step1_vs_excel: List[str] = []
    else:
        assert excel_path is not None
        excel_codes = LoadExcelNetworkCodes(excel_path)
        final_network_codes = sorted(step1_for_intersect & excel_codes)
        only_excel = sorted(excel_codes - step1_for_intersect)
        only_step1_vs_excel = sorted(step1_for_intersect - excel_codes)
    final_api_ids, missing_assoc, final_mapping = MapNetworkCodesToApiIds(
        final_network_codes, net_to_assoc
    )
    print("\n========== Step2 Excel ∩ Step1 ==========")
    if skip_excel:
        print("未提供 --excel，跳过单一价求交，Final=Step1 集合")
    else:
        print(f"Excel Network Code 数量: {len(excel_codes)}")
        print(f"Step1 用于交集的集合大小: {len(step1_for_intersect)}")
        print(f"仅 Excel 有: {len(only_excel)}")
        print(f"仅 Step1 有: {len(only_step1_vs_excel)}")
        if only_excel:
            print(f"仅 Excel 有预览: {only_excel[:30]}")
        if only_step1_vs_excel:
            print(f"仅 Step1 有预览: {only_step1_vs_excel[:30]}")
    print(f"Final networkCode 数量: {len(final_network_codes)}")
    print(f"Final networkCode 列表: {final_network_codes}")
    print(f"关联映射 networkCode→associateCode/resourceId: {final_mapping}")
    print(f"Final API resourceId 数量: {len(final_api_ids)}")
    print(f"Final API resourceId 列表: {final_api_ids}")
    if missing_assoc:
        print(f"警告: 以下 networkCode 缺少 associateCode/resourceId 映射: {missing_assoc}")

    # --- Auth ---
    baseline_x_version = str(args.baseline_x_version or "").strip() or None
    compare_x_version = str(args.compare_x_version or "").strip() or None
    token = str(args.bearer_token or "").strip()
    if not token:
        client_id = str(args.client_id or "").strip()
        secret = str(args.secret or "").strip()
        if not client_id or not secret:
            raise PipelineError("未提供 --bearer-token，且缺少 --client-id/--secret（或环境变量）")
        print("\n正在获取 accessToken ...")
        token = FetchAccessToken(
            base_url=str(args.base_url),
            program_id=str(args.program_id),
            client_id=client_id,
            secret=secret,
            timeout_sec=float(args.timeout),
        )
        print("Token 获取成功")
    compare_token = str(args.compare_bearer_token or "").strip() or token

    # --- Step3（默认只跑 canary / --compare-x-version）---
    print("\n========== Step3 GET /api/v2/resources ==========")
    print(
        f"language={language!r}  module={int(args.module)}  "
        f"x-version={compare_x_version!r}（只跑对比侧，不做 baseline 对拍）"
    )
    total_number, list_by_id = FetchAllResourcesList(
        base_url=str(args.base_url),
        module=int(args.module),
        page_size=int(args.page_size),
        language=language,
        program_id=str(args.program_id),
        bearer_token=compare_token,
        timeout_sec=float(args.timeout),
        x_version=compare_x_version,
    )
    list_ids = set(list_by_id.keys())
    # Step3/4 与接口对拍用 associateCode（R 码）；无映射时回退 networkCode
    final_api_set = set(final_api_ids)
    only_in_final = sorted(final_api_set - list_ids)
    only_in_list = sorted(list_ids - final_api_set)
    print(f"module={args.module}")
    print(f"响应 totalNumber: {total_number}")
    print(f"列表实际 resourceId 数: {len(list_ids)}")
    print(f"Final API(resourceId/associateCode) 数量: {len(final_api_set)}")
    print(f"totalNumber == Final API: {total_number == len(final_api_set)}")
    print(f"列表集合 == Final API: {list_ids == final_api_set}")
    print(f"仅 Final API 有: {len(only_in_final)}")
    print(f"仅列表有: {len(only_in_list)}")
    if only_in_final:
        print(f"仅 Final API 有预览: {only_in_final[:30]}")
    if only_in_list:
        print(f"仅列表有预览: {only_in_list[:30]}")

    # --- Step4 ---
    list_diffs: List[DiffItem] = []
    detail_diffs: List[DiffItem] = []
    detail_errors: List[Dict[str, str]] = []
    compared_ids: List[str] = []
    canary_list_by_id: Dict[str, JsonDict] = dict(list_by_id)
    canary_total = int(total_number)
    skip_step4 = bool(args.skip_step4) or not baseline_x_version

    if not skip_step4:
        print(
            f"\n========== Step4 基线({baseline_x_version!r}) vs "
            f"对比({compare_x_version!r})（列表+详情全集） =========="
        )
        print(f"language={language!r}（列表与详情均带此 query）")
        print(f"拉取对比侧全量列表 x-version={compare_x_version!r} ...")
        _canary_total, canary_list_by_id = FetchAllResourcesList(
            base_url=str(args.base_url),
            module=int(args.module),
            page_size=int(args.page_size),
            language=language,
            program_id=str(args.program_id),
            bearer_token=compare_token,
            timeout_sec=float(args.timeout),
            x_version=compare_x_version,
        )
        print(
            f"对比侧 totalNumber={_canary_total}, resourceId数={len(canary_list_by_id)}"
        )
        canary_total = int(_canary_total)

        target_ids = list(final_api_ids)
        if int(args.max_detail) > 0:
            target_ids = target_ids[: int(args.max_detail)]
            print(f"注意: --max-detail={args.max_detail}，仅比对前 {len(target_ids)} 个")
        print(f"Step4 比对 API resourceId(=associateCode) 数: {len(target_ids)}")

        for rid in target_ids:
            base_item = list_by_id.get(rid)
            can_item = canary_list_by_id.get(rid)
            if base_item is None and can_item is None:
                list_diffs.append(
                    {
                        "resourceId": rid,
                        "api": "list",
                        "path": "$",
                        "baseline": None,
                        "canary": None,
                        "note": "两侧列表均无此 resourceId",
                    }
                )
                continue
            if base_item is None or can_item is None:
                list_diffs.append(
                    {
                        "resourceId": rid,
                        "api": "list",
                        "path": "$",
                        "baseline": base_item,
                        "canary": can_item,
                        "note": "一侧列表缺失",
                    }
                )
                continue
            for d in DeepDiff(base_item, can_item):
                list_diffs.append({"resourceId": rid, "api": "list", **d})

        def _FetchPair(rid: str) -> Tuple[str, Optional[JsonDict], Optional[JsonDict], Optional[str]]:
            try:
                base = FetchResourceDetail(
                    base_url=str(args.base_url),
                    resource_id=rid,
                    module=int(args.module),
                    language=language,
                    program_id=str(args.program_id),
                    bearer_token=token,
                    timeout_sec=float(args.timeout),
                    x_version=baseline_x_version,
                )
                can = FetchResourceDetail(
                    base_url=str(args.base_url),
                    resource_id=rid,
                    module=int(args.module),
                    language=language,
                    program_id=str(args.program_id),
                    bearer_token=compare_token,
                    timeout_sec=float(args.timeout),
                    x_version=compare_x_version,
                )
                return rid, base, can, None
            except Exception as exc:  # noqa: BLE001 - 汇总单条失败继续
                return rid, None, None, str(exc)

        print(f"并发拉取详情 workers={args.workers}，共 {len(target_ids)} 个 ...")
        done = 0
        with ThreadPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
            futures = [pool.submit(_FetchPair, rid) for rid in target_ids]
            for fut in as_completed(futures):
                rid, base, can, err = fut.result()
                compared_ids.append(rid)
                done += 1
                if done % 50 == 0 or done == len(target_ids):
                    print(f"  详情进度 {done}/{len(target_ids)}")
                if err:
                    detail_errors.append({"resourceId": rid, "error": err})
                    continue
                assert base is not None and can is not None
                for d in DeepDiff(base, can):
                    detail_diffs.append({"resourceId": rid, "api": "detail", **d})

        print(f"列表字段差异条数: {len(list_diffs)}")
        print(f"详情字段差异条数: {len(detail_diffs)}")
        print(f"详情请求失败数: {len(detail_errors)}")
        # 预览
        for label, rows in (("列表", list_diffs[:20]), ("详情", detail_diffs[:20])):
            if rows:
                print(f"--- {label}差异预览（最多20）---")
                for row in rows:
                    print(
                        f"  {row.get('resourceId')} | {row.get('path')} | "
                        f"baseline={row.get('baseline')!r} | canary={row.get('canary')!r}"
                    )
    else:
        if args.skip_step4:
            print("\n========== Step4 已跳过 (--skip-step4) ==========")
        else:
            print(
                "\n========== Step4 已跳过（未指定 --baseline-x-version，"
                f"仅跑 x-version={compare_x_version!r}） =========="
            )

    # --- Step5 ---
    dining_json_arg = str(getattr(args, "dining_json", "") or "").strip()
    skip_step5 = not dining_json_arg
    step5: JsonDict = {"skipped": True}
    if skip_step5:
        print("\n========== Step5 已跳过（未提供 --dining-json） ==========")
    else:
        dining_path = Path(dining_json_arg)
        print("\n========== Step5 diningOptions vs FD_DISCOUNT/FD_NOTE ==========")
        print(f"源 JSON: {dining_path}")
        expected_dining = LoadDiningDiscountExpected(dining_path)
        print(
            f"期望编码: {len(expected_dining)}  "
            f"FD_NOTE空回退优惠值: "
            f"{sum(1 for v in expected_dining.values() if bool(v.get('noteBlank')))}"
        )
        print(
            "入参 module="
            + ",".join(str(m) for m in STEP5_QUERY_MODULES)
            + "；对拍 diningOptions.module=5 的 optionName/description"
            + "（module=6 响应里可能另有 Coupon，不对优惠源）"
        )
        by_query: Dict[str, JsonDict] = {}
        for query_module in STEP5_QUERY_MODULES:
            print(f"\n----- Step5 入参 module={query_module} -----")
            if query_module == int(args.module) and canary_list_by_id:
                list_by_id = canary_list_by_id
                list_total = int(canary_total) if canary_total else len(canary_list_by_id)
                print(
                    f"复用对比侧列表 totalNumber={list_total}, "
                    f"resourceId数={len(list_by_id)}"
                )
            else:
                print(f"拉取对比侧列表 module={query_module} x-version={compare_x_version!r} ...")
                list_total, list_by_id = FetchAllResourcesList(
                    base_url=str(args.base_url),
                    module=query_module,
                    page_size=int(args.page_size),
                    language=language,
                    program_id=str(args.program_id),
                    bearer_token=compare_token,
                    timeout_sec=float(args.timeout),
                    x_version=compare_x_version,
                )
                print(
                    f"对比侧 module={query_module} totalNumber={list_total}, "
                    f"resourceId数={len(list_by_id)}"
                )
            one = RunStep5DiningOptions(
                expected=expected_dining,
                list_by_id=list_by_id,
                list_total=int(list_total),
                base_url=str(args.base_url),
                module=query_module,
                language=language,
                program_id=str(args.program_id),
                bearer_token=compare_token,
                x_version=compare_x_version,
                workers=int(args.workers),
                timeout_sec=float(args.timeout),
                option_module=5,
            )
            by_query[str(query_module)] = one
            print(
                f"Step5 module={query_module} 列表不一致={one['listDiffCount']}  "
                f"详情不一致={one['detailDiffCount']}  "
                f"详情失败={one['detailErrorCount']}"
            )
        step5 = {
            "skipped": False,
            "diningJson": str(dining_path),
            "optionModule": 5,
            "queryModules": list(STEP5_QUERY_MODULES),
            "byQueryModule": by_query,
        }
        primary = by_query.get("5") or next(iter(by_query.values()), {})
        for key in (
            "expectedCount",
            "blankNoteFallbackCount",
            "listTotalNumber",
            "listDiffCount",
            "detailDiffCount",
            "detailErrorCount",
            "listMissingCount",
            "listMissing",
            "listDiffs",
            "detailDiffs",
            "detailErrors",
            "xVersion",
        ):
            if key in primary:
                step5[key] = primary[key]

    report = {
        "generatedAt": stamp,
        "inputs": {
            "oldJson": str(old_path) if old_path else None,
            "newJson": str(new_path),
            "excel": str(excel_path) if excel_path else None,
            "diningJson": dining_json_arg or None,
            "skipOldJson": skip_old,
            "skipExcel": skip_excel,
            "skipStep5": skip_step5,
            "module": int(args.module),
            "redisKey": redis_key,
            "language": language,
            "baseUrl": str(args.base_url),
            "programId": str(args.program_id),
            "baselineXVersion": baseline_x_version,
            "compareXVersion": compare_x_version,
        },
        "step1": {
            "redisKey": redis_key,
            "oldStats": old_stats,
            "newStats": new_stats,
            "skipOldJson": skip_old,
            "oldCount": len(old_codes),
            "newCount": len(new_codes),
            "countEqual": len(old_codes) == len(new_codes),
            "setEqual": old_codes == new_codes,
            "onlyOldCount": len(only_old),
            "onlyNewCount": len(only_new),
            "onlyOld": only_old,
            "onlyNew": only_new,
            "commonCount": len(step1_common),
            "newCodes": sorted(new_codes),
            "oldCodes": sorted(old_codes),
            "networkToAssociate": {k: net_to_assoc[k] for k in sorted(net_to_assoc)},
        },
        "step2": {
            "skippedExcel": skip_excel,
            "excelCount": len(excel_codes),
            "onlyExcel": only_excel,
            "onlyStep1VsExcel": only_step1_vs_excel,
            "step1IntersectBaseCount": len(step1_for_intersect),
            "finalNetworkCount": len(final_network_codes),
            "finalCodes": final_network_codes,
            "finalApiIds": final_api_ids,
            "finalMapping": final_mapping,
            "missingAssociate": missing_assoc,
        },
        "step3": {
            "totalNumber": total_number,
            "listResourceIdCount": len(list_ids),
            "finalCount": len(final_api_set),
            "finalApiIds": final_api_ids,
            "totalEqualsFinal": total_number == len(final_api_set),
            "setEqualsFinal": list_ids == final_api_set,
            "onlyInFinal": only_in_final,
            "onlyInList": only_in_list,
            "xVersion": compare_x_version,
        },
        "step4": {
            "skipped": skip_step4,
            "comparedCount": len(compared_ids),
            "listDiffCount": len(list_diffs),
            "detailDiffCount": len(detail_diffs),
            "detailErrorCount": len(detail_errors),
            "listDiffs": list_diffs,
            "detailDiffs": detail_diffs,
            "detailErrors": detail_errors,
        },
        "step5": step5,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = BuildSummaryMarkdown(
        stamp=stamp,
        old_stats=old_stats,
        new_stats=new_stats,
        old_count=len(old_codes),
        new_count=len(new_codes),
        only_old=only_old,
        only_new=only_new,
        new_codes_sorted=sorted(new_codes),
        excel_count=len(excel_codes),
        only_excel=only_excel,
        only_step1_vs_excel=only_step1_vs_excel,
        final_codes=final_network_codes,
        final_api_ids=final_api_ids,
        final_mapping=final_mapping,
        redis_key=redis_key,
        language=language,
        skip_old=skip_old,
        skip_excel=skip_excel,
        module=int(args.module),
        total_number=total_number,
        list_id_count=len(list_ids),
        only_in_final=only_in_final,
        only_in_list=only_in_list,
        skip_step4=skip_step4,
        list_x_version=compare_x_version,
        list_diffs=list_diffs,
        detail_diffs=detail_diffs,
        detail_errors=detail_errors,
        step5=step5,
        report_path=report_path,
    )
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    # 清理历史 pipeline-<stamp>.*（保留 pipeline-latest*）
    pruned = 0
    for old in report_dir.glob("pipeline-*"):
        if old.name.startswith("pipeline-latest"):
            continue
        try:
            old.unlink()
            pruned += 1
        except OSError:
            pass
    print(f"\n报告已写入:\n  {report_path}\n  {summary_path}")
    if pruned:
        print(f"已清理旧报告 {pruned} 个")
    return 0


def _FmtJsonVal(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except TypeError:
        return repr(value)


def BuildSummaryMarkdown(
    *,
    stamp: str,
    old_stats: Mapping[str, int],
    new_stats: Mapping[str, int],
    old_count: int,
    new_count: int,
    only_old: Sequence[str],
    only_new: Sequence[str],
    new_codes_sorted: Sequence[str],
    excel_count: int,
    only_excel: Sequence[str],
    only_step1_vs_excel: Sequence[str],
    final_codes: Sequence[str],
    final_api_ids: Sequence[str],
    final_mapping: Mapping[str, str],
    redis_key: Optional[str],
    language: Optional[str],
    skip_old: bool,
    skip_excel: bool,
    module: int,
    total_number: int,
    list_id_count: int,
    only_in_final: Sequence[str],
    only_in_list: Sequence[str],
    skip_step4: bool,
    list_diffs: Sequence[Mapping[str, Any]],
    detail_diffs: Sequence[Mapping[str, Any]],
    detail_errors: Sequence[Mapping[str, Any]],
    step5: Mapping[str, Any],
    report_path: Path,
    list_x_version: Optional[str] = None,
) -> List[str]:
    """组装摘要 Markdown（含 Step1 新侧列表、Step3 差异、Step4 差异明细）。"""
    old_line = (
        "- 未提供旧 JSON，跳过新旧对比"
        if skip_old
        else (
            f"- 旧: 数组={old_stats['arrayLen']} / hasLgTrue行={old_stats['hasLgTrueRows']} / "
            f"去重={old_stats['uniqueNetworkCodes']}"
        )
    )
    step2_excel_line = (
        f"- 未提供 Excel，Final=Step1 新侧集合: {len(final_codes)}"
        if skip_excel
        else f"- Excel: {excel_count}  Final networkCode(Step1∩Excel): {len(final_codes)}"
    )
    step2_diff_line = (
        ""
        if skip_excel
        else f"- 仅Excel有: {len(only_excel)}  仅Step1有: {len(only_step1_vs_excel)}"
    )
    lines: List[str] = [
        f"# Redis / Excel / Resources 核对摘要 ({stamp})",
        "",
        "## Step1",
        f"- Redis 顶层键: {redis_key!r}",
        old_line,
        (
            f"- 新: 数组={new_stats['arrayLen']} / hasLgTrue行={new_stats['hasLgTrueRows']} / "
            f"去重={new_stats['uniqueNetworkCodes']}"
        ),
        (
            f"- 新侧去重: {new_count}"
            if skip_old
            else (
                f"- 数量相等: {old_count == new_count}  "
                f"集合相等: {not only_old and not only_new}"
            )
        ),
        (
            ""
            if skip_old
            else f"- 仅旧有: {len(only_old)}  仅新有: {len(only_new)}"
        ),
        "",
        f"### Step1 新侧 networkCode 列表（共 {len(new_codes_sorted)}）",
        json.dumps(list(new_codes_sorted), ensure_ascii=False),
        "",
        "## Step2",
        step2_excel_line,
        step2_diff_line,
        (
            ""
            if skip_excel or not only_excel
            else f"- 仅Excel: {json.dumps(list(only_excel), ensure_ascii=False)}"
        ),
        (
            ""
            if skip_excel or not only_step1_vs_excel
            else f"- 仅Step1: {json.dumps(list(only_step1_vs_excel), ensure_ascii=False)}"
        ),
        f"- Final API resourceId(=associateCode): {len(final_api_ids)}",
        "",
        f"### Step2 Final networkCode 列表（共 {len(final_codes)}）",
        json.dumps(list(final_codes), ensure_ascii=False),
        "",
        "### Step2 关联映射 networkCode → associateCode/resourceId",
        json.dumps(dict(final_mapping), ensure_ascii=False),
        "",
        f"### Step2 Final API resourceId 列表（共 {len(final_api_ids)}）",
        json.dumps(list(final_api_ids), ensure_ascii=False),
        "",
        "## Step3",
        f"- language={language!r}  module={module}  x-version={list_x_version!r}",
        (
            f"- totalNumber={total_number}  列表ID数={list_id_count}  "
            f"Final API={len(final_api_ids)}"
        ),
        f"- totalNumber==Final API: {total_number == len(final_api_ids)}",
        (
            f"- 集合==Final API: "
            f"{list_id_count == len(final_api_ids) and not only_in_final and not only_in_list}"
        ),
        f"- 仅Final API有: {len(only_in_final)}  仅列表有: {len(only_in_list)}",
        "",
        f"### Step3 差异 · 仅 Final API 有（列表无，共 {len(only_in_final)}）",
        json.dumps(list(only_in_final), ensure_ascii=False),
        "",
        f"### Step3 差异 · 仅列表有（Final API 无，共 {len(only_in_list)}）",
        json.dumps(list(only_in_list), ensure_ascii=False),
    ]

    lines.extend(
        [
            "",
            "## Step4",
            f"- language={language!r}",
            f"- 跳过: {skip_step4}（未指定 --baseline-x-version 时默认跳过，只跑 canary）",
            f"- 忽略对比字段: {list(DEFAULT_IGNORE_DIFF_PATHS)}",
            f"- 列表差异条数: {len(list_diffs)}",
            f"- 详情差异条数: {len(detail_diffs)}",
            f"- 详情失败: {len(detail_errors)}",
        ]
    )
    lines.extend(_FormatDiffsGroupedByPath("Step4 列表差异（按字段类型分组）", list_diffs))
    lines.extend(_FormatDiffsGroupedByPath("Step4 详情差异（按字段类型分组）", detail_diffs))

    if detail_errors:
        lines.extend(["", f"### Step4 详情失败（共 {len(detail_errors)}）"])
        for err in detail_errors:
            lines.append(f"- `{err.get('resourceId')}` | {err.get('error')}")

    lines.extend(BuildStep5SummaryMarkdown(step5))
    lines.extend(["", f"完整 JSON 报告: `{report_path.as_posix()}`"])
    return lines


def _MdCell(value: Any) -> str:
    """Markdown 表格单元格：空显示为（空），换行改为空格。"""
    text = "" if value is None else str(value)
    if text == "":
        return "（空）"
    return text.replace("\r\n", " ").replace("\n", " ").replace("|", "\\|")


def _MdDiningCell(value: Any) -> str:
    """diningOptions 表格单元格：空值显示 ``(null)``；不转义 ``\\r\\n``，表格内换行折成空格。"""
    if IsDiningNullLike(value):
        if value is None or DiningRawText(value).strip().lower() in {"(null)", "null"}:
            return "`(null)`"
        return "（空）"
    text = CollapseDiningWhitespace(value)
    return text.replace("|", "\\|")


def _IssueGroupLabel(issue: str) -> str:
    mapping = {
        "not_in_list": "列表中无此编码",
        "missing_module5_diningOptions": "缺少 module=5 的 diningOptions",
        "missing_module6_diningOptions": "缺少 module=6 的 diningOptions",
        "optionName_not_found": "未找到匹配的 optionName",
        "optionName_mismatch": "optionName 不一致",
        "optionName_newline_mismatch": "optionName 不一致（空格 vs \\r\\n / \\n）",
        "description_mismatch": "description 不一致",
        "description_newline_mismatch": "description 不一致（空格 vs \\r\\n / \\n）",
        "optionName+description_mismatch": "optionName 与 description 均不一致",
        "optionName+description_newline_mismatch": "optionName 与 description 均不一致（空格 vs \\r\\n / \\n）",
    }
    return mapping.get(issue, issue)


def _BuildStep5DiffSections(block: Mapping[str, Any]) -> List[str]:
    """单次入参 module 的 Step5 统计表 + 一条典型例子。"""
    list_diffs = FilterOpenDiningDiffs(list(block.get("listDiffs") or []))
    detail_diffs = FilterOpenDiningDiffs(list(block.get("detailDiffs") or []))
    detail_errors = list(block.get("detailErrors") or [])
    list_missing = list(block.get("listMissing") or [])
    expected_count = int(block.get("expectedCount") or 0)
    blank_note = int(block.get("blankNoteFallbackCount") or 0)
    x_version = block.get("xVersion")
    query_module = block.get("queryModule")
    option_module = block.get("optionModule", 5)
    lines: List[str] = [
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 入参 module | `{query_module}` |",
        f"| 对拍 diningOptions.module | `{option_module}` |",
        f"| 对比侧 x-version | `{x_version}` |",
        f"| 期望编码 | {expected_count}（其中 {blank_note} 条 `FD_NOTE` 为空，已按优惠值回退） |",
        f"| 对比侧列表 totalNumber | {block.get('listTotalNumber')} |",
        f"| 列表不一致 | **{len(list_diffs)}** |",
        f"| 详情不一致 | **{len(detail_diffs)}** |",
        f"| 详情失败 | {len(detail_errors)} |",
        f"| 列表缺失 | {len(list_missing)} |",
    ]

    def GroupRows(rows: Sequence[Mapping[str, Any]]) -> List[Tuple[str, List[Mapping[str, Any]]]]:
        grouped: Dict[str, List[Mapping[str, Any]]] = {}
        for row in rows:
            key = str(row.get("issue") or "unknown")
            grouped.setdefault(key, []).append(row)
        ordered = sorted(grouped.keys(), key=lambda k: (-len(grouped[k]), k))
        return [(k, grouped[k]) for k in ordered]

    def OverviewTable(rows: Sequence[Mapping[str, Any]]) -> List[str]:
        if not rows:
            return ["", "（无）"]
        out = ["", "| 类型 | 数量 | 编码 |", "|---|---|---|"]
        for issue, group in GroupRows(rows):
            rids = "、".join(
                f"`{r.get('resourceId')}`"
                for r in sorted(group, key=lambda x: str(x.get("resourceId") or ""))
            )
            out.append(f"| {_IssueGroupLabel(issue)} | {len(group)} | {rids} |")
        return out

    def RenderTypicalExample(row: Mapping[str, Any], issue: str, total: int) -> List[str]:
        """只展开 1 条典型例子；接口值原样输出，不做转义。"""
        rid = row.get("resourceId")
        return [
            "",
            f"##### {_IssueGroupLabel(issue)}（共 {total}，下为 1 条典型例子）",
            "",
            f"代表编码：`{rid}`",
            "",
            "**源 optionName**",
            "",
            "```text",
            _DiningRawDisplay(row.get("expectedOptionName")),
            "```",
            "",
            "**接口 optionName**",
            "",
            "```text",
            _DiningRawDisplay(row.get("actualOptionName")),
            "```",
            "",
            "**源 description**",
            "",
            "```text",
            _DiningRawDisplay(row.get("expectedDescription")),
            "```",
            "",
            "**接口 description**",
            "",
            "```text",
            _DiningRawDisplay(row.get("actualDescription")),
            "```",
        ]

    same_ids = {str(r.get("resourceId")) for r in list_diffs} == {
        str(r.get("resourceId")) for r in detail_diffs
    }
    lines.extend(["", "#### 列表差异总览"])
    lines.extend(OverviewTable(list_diffs))
    lines.extend(["", "#### 详情差异总览"])
    if same_ids and list_diffs and detail_diffs:
        lines.append("与列表为同一批编码，明细见下列表。")
    else:
        lines.extend(OverviewTable(detail_diffs))

    display_rows = detail_diffs if detail_diffs else list_diffs
    if display_rows:
        lines.extend(["", "#### 典型例子（每类 1 条，接口 JSON 原值 vs 源 JSON 原值）"])
        for issue, group in GroupRows(display_rows):
            by_id = {str(r.get("resourceId") or ""): r for r in group}
            sample = by_id.get("R03166")
            if sample is None:
                sample = sorted(group, key=lambda r: str(r.get("resourceId") or ""))[0]
            lines.extend(RenderTypicalExample(sample, issue, len(group)))

    if list_missing:
        lines.extend(
            [
                "",
                f"#### 列表中无此编码（共 {len(list_missing)}）",
                json.dumps(list_missing, ensure_ascii=False),
            ]
        )
    if detail_errors:
        lines.extend(["", f"#### Step5 详情失败（共 {len(detail_errors)}）"])
        for err in detail_errors:
            lines.append(f"- `{err.get('resourceId')}` | {err.get('error')}")

    matched = expected_count - len(detail_diffs) - len(detail_errors)
    if expected_count:
        lines.extend(
            [
                "",
                f"其余 **{max(0, matched)}** 条：该入参下列表、详情的 `diningOptions`（module={option_module}）与源 JSON 逐字一致。",
            ]
        )
    return lines


def BuildStep5SummaryMarkdown(step5: Mapping[str, Any]) -> List[str]:
    """Step5 表格摘要：入参 module=5 与 module=6 各一份。"""
    lines: List[str] = ["", "## Step5 diningOptions 对拍"]
    if bool(step5.get("skipped", True)):
        lines.append("- 未提供 `--dining-json`，已跳过")
        return lines

    dining_json = step5.get("diningJson")
    lines.extend(
        [
            "",
            "对照规则：`optionName` ← `FD_DISCOUNT`；`description` ← `FD_NOTE`（空 / `(null)` 时回退为 `FD_DISCOUNT`）。接口 JSON `null` 与源 `(null)`、空串视为同一空值。有值时直接取接口返回值与源 JSON 逐字对比（接口里的 `\\r\\n` 原样参与比较，不折叠成空格）。`optionName` 同样按此规则。",
            "",
            "分别用入参 `module=5`、`module=6` 拉资源列表与详情。对拍只取 `diningOptions` 里 **module=5** 的 `optionName`/`description`；`module=6` 响应里可能同时有 Coupon（如 `15.0 EUR Coupon`），不拿去对优惠源。",
            "",
            f"- 源 JSON：`{dining_json}`" if dining_json else "- 源 JSON：（已加载）",
        ]
    )

    by_query = step5.get("byQueryModule")
    blocks: List[Tuple[str, Mapping[str, Any]]] = []
    if isinstance(by_query, dict) and by_query:
        ordered = list(step5.get("queryModules") or [])
        if not ordered:
            ordered = sorted((int(k) for k in by_query.keys()))
        for qmod in ordered:
            block = by_query.get(str(qmod))
            if isinstance(block, dict):
                blocks.append((f"入参 module={qmod}", block))
    else:
        blocks.append(("入参 module（单次）", step5))

    for title, block in blocks:
        lines.extend(["", f"### {title}"])
        lines.extend(_BuildStep5DiffSections(block))
    return lines


def _DiffGroupLabel(path: Any, note: Any) -> str:
    """差异分组标题：优先字段路径，缺失两侧时用 note。"""
    p = str(path or "").strip() or "$"
    if note and p in ("$", ""):
        return f"{p}（{note}）"
    return p


def _FormatDiffsGroupedByPath(title: str, diffs: Sequence[Mapping[str, Any]]) -> List[str]:
    """按 path 分组输出差异明细。"""
    lines: List[str] = ["", f"### {title}（共 {len(diffs)}）"]
    if not diffs:
        lines.append("- （无）")
        return lines

    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for d in diffs:
        key = _DiffGroupLabel(d.get("path"), d.get("note"))
        grouped.setdefault(key, []).append(d)

    # 组内按 resourceId 排序；组顺序按条数降序，同数按 path 字典序
    ordered_keys = sorted(
        grouped.keys(),
        key=lambda k: (-len(grouped[k]), k),
    )
    lines.append("")
    lines.append("#### 类型汇总")
    for key in ordered_keys:
        lines.append(f"- `{key}`: {len(grouped[key])} 条")

    for key in ordered_keys:
        rows = sorted(grouped[key], key=lambda x: str(x.get("resourceId") or ""))
        lines.extend(["", f"#### `{key}`（{len(rows)}）"])
        # 同组若取值模式简单，额外给出 resourceId 数组便于复制
        rids = [str(d.get("resourceId") or "") for d in rows]
        lines.append(f"- resourceIds: {json.dumps(rids, ensure_ascii=False)}")
        for d in rows:
            rid = d.get("resourceId", "")
            note = d.get("note")
            note_s = f" | note={note}" if note else ""
            lines.append(
                f"- `{rid}` | baseline={_FmtJsonVal(d.get('baseline'))} | "
                f"canary={_FmtJsonVal(d.get('canary'))}{note_s}"
            )
    return lines


def main() -> None:
    try:
        raise SystemExit(RunPipeline())
    except PipelineError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
