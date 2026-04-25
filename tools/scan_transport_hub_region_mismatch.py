"""
多语种 transportHubId / countryOrRegion 扫描与 POST /v2/search 探测（独立脚本）。

**环境**：与 ``api-testcases/2026Q2_SP1`` 一致——仓库根 ``.env`` + ``DP_PROFILE`` + ``env/.env.<profile>``；
需 ``DP_BASE_URL``、``DP_PROGRAM_ID``、``DP_CLIENT_ID``、``DP_CLIENT_SECRET``；可选 ``DP_X_VERSION`` 等（同 ``papi2548_helpers.BuildCommonHeaders``）。

**OpenAPI 契约**：列表类 GET 默认使用 Query ``pageNumber``、``pageSize``、``language``；若与线网不一致，可用环境变量覆盖（见下方 ``DP_SCAN_*``）。
也可用 Cursor Apifox MCP 服务器 **「API Q1SP4+5」** 的 ``read_project_oas_7dyfjf`` / ``read_project_oas_ref_resources_7dyfjf`` 拉取 OpenAPI 复核。

**依赖**：``httpx``（``pip install httpx``）。

用法示例::

    cd d:\\interface\\interface_cursor
    python tools/scan_transport_hub_region_mismatch.py --mode resources-only --output-json scan.json
    python tools/scan_transport_hub_region_mismatch.py --mode combined --output-json scan.json --max-concurrency 48
    python tools/scan_transport_hub_region_mismatch.py --mode combined --languages en-US,ko-KR,zh-CN --skip-languages ko-KR --output-anomaly-table summary.json
    python tools/scan_transport_hub_region_mismatch.py --mode detail-only --seen-hub-ids-json scan.json --include-anomaly-breakdown --output-json detail.json
    python tools/scan_transport_hub_region_mismatch.py --mode search --scan-json scan.json --output-json search.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote
from typing import Any, DefaultDict, Dict, Final, List, Mapping, Optional, Sequence, Set, Tuple, Union, cast

try:
    import httpx
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("请先安装 httpx：pip install httpx") from exc

JsonDict = Dict[str, Any]

_PROFILE_SAFE = re.compile(r"^[a-zA-Z0-9_-]+$")
_DEFAULT_BASE: Final[str] = "https://developer-sandbox.dragonpass.com/api"

DEFAULT_LANGUAGES: Final[Tuple[str, ...]] = (
    "en-US",
    "ja-JP",
    "de-DE",
    "es-ES",
    "fr-FR",
    "it-IT",
    "pl-PL",
    "pt-PT",
    "ru-RU",
    "th-TH",
    "uk-UA",
    "vi-VN",
)


def _RepoRoot() -> Path:
    return Path(__file__).resolve().parent.parent


def _ParseDotenvLine(line: str) -> Optional[Tuple[str, str]]:
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    key, _, val = s.partition("=")
    key = key.strip()
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    if not key:
        return None
    return (key, val)


def _ApplyDotenvFile(
    path: Path,
    *,
    overwrite: bool,
    skip_empty_overwrites: bool = False,
) -> None:
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        tup = _ParseDotenvLine(line)
        if tup is None:
            continue
        key, val = tup
        if overwrite:
            if skip_empty_overwrites and not val.strip():
                continue
            os.environ[key] = val
        elif key not in os.environ:
            os.environ[key] = val


def _ProfileSegmentSafe(segment: str) -> bool:
    return bool(segment) and _PROFILE_SAFE.match(segment) is not None


def _ApplyProfileNameFromLocalProfileFile(root: Path) -> None:
    if os.environ.get("DP_PROFILE", "").strip():
        return
    path = root / "env" / ".local_profile"
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        seg = line.strip()
        if not seg or seg.startswith("#"):
            continue
        if _ProfileSegmentSafe(seg):
            os.environ["DP_PROFILE"] = seg
        return


def LoadAllDotenvLayers() -> None:
    """与 ``api-testcases/2026Q2_SP1/conftest.py`` 分层加载逻辑一致。"""
    root = _RepoRoot()
    _ApplyDotenvFile(root / ".env", overwrite=False)
    _ApplyProfileNameFromLocalProfileFile(root)
    profile = os.environ.get("DP_PROFILE", "").strip()
    if _ProfileSegmentSafe(profile):
        prof_path = root / "env" / f".env.{profile}"
        _ApplyDotenvFile(prof_path, overwrite=True, skip_empty_overwrites=True)
    if profile.lower() == "canary" and not os.environ.get("DP_X_VERSION", "").strip():
        os.environ["DP_X_VERSION"] = "canary"


def GetBaseUrl() -> str:
    raw = os.getenv("DP_BASE_URL", _DEFAULT_BASE).strip()
    if raw.endswith("/api"):
        return raw.rstrip("/")
    if raw.rstrip("/").endswith("dragonpass.com"):
        return raw.rstrip("/") + "/api"
    return raw.rstrip("/")


def _EnvFlagTrue(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def BuildNextRequestId() -> str:
    explicit = os.getenv("DP_X_REQUEST_ID", "").strip()
    if explicit:
        return explicit
    mode = os.getenv("DP_X_REQUEST_ID_MODE", "uuid").strip().lower()
    if mode == "numeric":
        tail = random.randint(100_000_000, 999_999_999)
        return str(int(time.time() * 1_000_000)) + str(tail)
    return str(uuid.uuid4())


def BuildAuthHeaders(token: str) -> Dict[str, str]:
    prog = os.getenv("DP_PROGRAM_ID", "").strip()
    if not prog:
        raise RuntimeError("缺少环境变量 DP_PROGRAM_ID")
    headers: Dict[str, str] = {
        "X-Program-ID": prog,
        "X-Request-ID": BuildNextRequestId(),
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "scan-transport-hub-region-mismatch/1.0",
        "Authorization": "Bearer " + token.strip(),
    }
    xv = os.getenv("DP_X_VERSION", "").strip()
    if xv and xv.lower() not in ("omit", "none", "off"):
        headers["x-version"] = xv
    return headers


async def PostAccessTokenAsync(client: httpx.AsyncClient) -> str:
    base = GetBaseUrl().rstrip("/")
    url = base + "/v2/auth/token"
    client_id = os.getenv("DP_CLIENT_ID", "").strip()
    client_secret = os.getenv("DP_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("缺少 DP_CLIENT_ID 或 DP_CLIENT_SECRET")
    token_headers: Dict[str, str] = {
        "X-Request-ID": BuildNextRequestId(),
        "Content-Type": "application/json",
        "Accept": "*/*",
        "User-Agent": "scan-transport-hub-region-mismatch/1.0",
    }
    if not _EnvFlagTrue("DP_TOKEN_OMIT_PROGRAM_ID"):
        pid = os.getenv("DP_PROGRAM_ID", "").strip()
        if pid:
            token_headers["X-Program-ID"] = pid
    br = os.getenv("DP_TOKEN_REQUEST_BEARER", "").strip()
    if br:
        token_headers["Authorization"] = br if br.lower().startswith("bearer ") else "Bearer " + br
    resp = await client.post(
        url,
        json={"clientId": client_id, "secret": client_secret},
        headers=token_headers,
        timeout=60.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"取 token HTTP 失败: {resp.status_code} {resp.text[:800]}")
    data = resp.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"token 响应非对象: {data!r}")
    root = cast(JsonDict, data)
    if "code" in root and root["code"] not in (0, "0"):
        raise RuntimeError(f"取 token 业务失败: {root!r}")
    container = root.get("data") if "data" in root else root
    if not isinstance(container, dict):
        raise RuntimeError(f"token 载荷格式异常: {container!r}")
    cdict = cast(JsonDict, container)
    tok = cdict.get("accessToken") or cdict.get("token") or cdict.get("access_token")
    if not tok or not isinstance(tok, str):
        raise RuntimeError(f"token 响应中无 accessToken: {root!r}")
    return tok


def UnwrapDataPayload(root: JsonDict) -> Tuple[Optional[JsonDict], Any]:
    """解析 {code, data} 信封；返回 (data 为 dict 时, 内层或原始 data)。"""
    if "data" not in root:
        return None, None
    data = root["data"]
    if isinstance(data, dict):
        return cast(JsonDict, data), data
    return None, data


def ExtractListFromDataInner(inner: JsonDict) -> List[Any]:
    for key in ("list", "items", "resources", "transportHubs", "results", "records"):
        v = inner.get(key)
        if isinstance(v, list):
            return v
    return []


def ExtractPagination(inner: JsonDict) -> Optional[JsonDict]:
    p = inner.get("pagination")
    return cast(JsonDict, p) if isinstance(p, dict) else None


def IsBusinessOk(root: JsonDict) -> bool:
    if "code" not in root:
        return True
    return root["code"] in (0, "0")


def ExtractIataFromHubDict(d: JsonDict) -> Optional[str]:
    """
    从含 ``transportHubId`` 的同一对象上解析 IATA：常见扁平字段与 ``airport`` 嵌套对象。
    返回大写 3 字码（若原值非空）；无法解析则 ``None``。
    """
    for key in (
        "iataCode",
        "iata",
        "airportIata",
        "airportIATACode",
        "iataAirportCode",
        "primaryIata",
        "hubIata",
        "transportHubIata",
    ):
        v = d.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip().upper()
    airport = d.get("airport")
    if isinstance(airport, dict):
        ad = cast(JsonDict, airport)
        for key in ("iataCode", "iata", "code"):
            v = ad.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip().upper()
    return None


def ExtractRegionCodeFromHubDict(d: JsonDict) -> Optional[str]:
    """
    从单条枢纽/资源节点取地区码：优先 ``countryOrRegion``，其次常见别名（与多环境 JSON 字段差异对齐）。
    仅接受非空字符串；不做大小写改写，避免误合并业务含义不同的取值。
    """
    for key in (
        "countryOrRegion",
        "iso2",
        "countryCode",
        "country",
        "regionCode",
    ):
        v = d.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def WalkHubRegionPairs(
    obj: Any,
    out: List[Tuple[str, Optional[str], Optional[str], Optional[str]]],
) -> None:
    """
    收集 (transportHubId, region_code, transportHubName, iata_code)。
    对 dict 递归；同 dict 含 transportHubId 时，地区码由 ``ExtractRegionCodeFromHubDict``、IATA 由 ``ExtractIataFromHubDict`` 解析。
    """
    if isinstance(obj, dict):
        d = cast(JsonDict, obj)
        hid = d.get("transportHubId")
        if isinstance(hid, str) and hid.strip():
            rstr = ExtractRegionCodeFromHubDict(d)
            name = d.get("transportHubName")
            nstr: Optional[str] = name.strip() if isinstance(name, str) and name.strip() else None
            iata = ExtractIataFromHubDict(d)
            out.append((hid.strip(), rstr, nstr, iata))
        for v in d.values():
            WalkHubRegionPairs(v, out)
    elif isinstance(obj, list):
        for it in obj:
            WalkHubRegionPairs(it, out)


def _NestedLangRegionDefault() -> DefaultDict[str, Set[str]]:
    return defaultdict(set)


def PickCommonIataFromCounter(counter: Counter[str]) -> Optional[str]:
    """在出现次数最多的 IATA 中，按字典序取一个，保证稳定输出。"""
    if not counter:
        return None
    top = max(counter.values())
    return min(k for k, v in counter.items() if v == top)


@dataclass
class ScanState:
    hub_to_regions: DefaultDict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    """同一 transportHubId 下，跨全部语种与全部请求合并后的地区码集合（≥2 即为异常）。"""
    hub_regions_by_language: DefaultDict[str, DefaultDict[str, Set[str]]] = field(
        default_factory=lambda: defaultdict(_NestedLangRegionDefault)
    )
    """hub_id -> language -> 该语种响应中出现过的地区码集合（用于看出「差异分布在哪些语种」）。"""
    hub_names_by_lang: DefaultDict[str, Dict[str, str]] = field(default_factory=lambda: defaultdict(dict))
    hub_iata_counts: DefaultDict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    """hub_id -> 各 IATA 在全部扫描请求中出现的次数（用于「常见 IATA」）。"""
    missing_region_events: int = 0
    seen_hub_ids: Set[str] = field(default_factory=set)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def IngestFromPayload(self, language: str, payload: JsonDict) -> None:
        pairs: List[Tuple[str, Optional[str], Optional[str], Optional[str]]] = []
        WalkHubRegionPairs(payload, pairs)
        async with self._lock:
            for hid, reg, name, iata in pairs:
                self.seen_hub_ids.add(hid)
                if reg:
                    self.hub_to_regions[hid].add(reg)
                    self.hub_regions_by_language[hid][language].add(reg)
                else:
                    self.missing_region_events += 1
                if iata:
                    self.hub_iata_counts[hid][iata] += 1
                if name:
                    prev = self.hub_names_by_lang[hid].get(language)
                    if not prev:
                        self.hub_names_by_lang[hid][language] = name


def ResolveListQueryParamNames() -> Tuple[str, str, str]:
    """
    返回 (page_number_key, page_size_key, language_key)。
    可通过环境变量覆盖：DP_SCAN_QUERY_PAGE_NUMBER、DP_SCAN_QUERY_PAGE_SIZE、DP_SCAN_QUERY_LANGUAGE。
    """
    pn = os.getenv("DP_SCAN_QUERY_PAGE_NUMBER", "pageNumber").strip() or "pageNumber"
    ps = os.getenv("DP_SCAN_QUERY_PAGE_SIZE", "pageSize").strip() or "pageSize"
    lg = os.getenv("DP_SCAN_QUERY_LANGUAGE", "language").strip() or "language"
    return pn, ps, lg


def MergeExtraQuery() -> Dict[str, str]:
    raw = os.getenv("DP_SCAN_LIST_EXTRA_QUERY", "").strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DP_SCAN_LIST_EXTRA_QUERY 须为 JSON 对象字符串") from exc
    if not isinstance(obj, dict):
        raise RuntimeError("DP_SCAN_LIST_EXTRA_QUERY 须为 JSON 对象")
    out: Dict[str, str] = {}
    for k, v in obj.items():
        out[str(k)] = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
    return out


async def RequestWithRetries(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str],
    params: Optional[Mapping[str, Union[str, int]]] = None,
    json_body: Optional[JsonDict] = None,
    max_retries: int = 4,
) -> httpx.Response:
    delay = 1.0
    last_exc: Optional[BaseException] = None
    for _ in range(max_retries):
        req_headers = dict(headers)
        req_headers["X-Request-ID"] = BuildNextRequestId()
        async with semaphore:
            try:
                if method.upper() == "GET":
                    resp = await client.get(url, headers=req_headers, params=params, timeout=120.0)
                else:
                    resp = await client.post(
                        url,
                        headers=req_headers,
                        json=json_body,
                        timeout=120.0,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 30.0)
                continue
        if resp.status_code == 429:
            await asyncio.sleep(delay)
            delay = min(delay * 2.0, 30.0)
            continue
        return resp
    if last_exc is not None:
        raise RuntimeError(f"请求重试耗尽: {url}") from last_exc
    raise RuntimeError(f"请求重试耗尽: {url}")


async def PaginateListEndpoint(
    *,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    headers: Mapping[str, str],
    path: str,
    language: str,
    page_size: int,
    state: ScanState,
) -> None:
    base = GetBaseUrl().rstrip("/")
    url = base + path
    pn_key, ps_key, lg_key = ResolveListQueryParamNames()
    extra = MergeExtraQuery()
    mode = os.getenv("DP_SCAN_LANGUAGE_MODE", "query").strip().lower()
    page = 1
    while True:
        params: Dict[str, Union[str, int]] = {
            pn_key: page,
            ps_key: page_size,
            **{k: v for k, v in extra.items()},
        }
        req_headers = dict(headers)
        if mode == "header":
            req_headers["Accept-Language"] = language
        else:
            params[lg_key] = language

        resp = await RequestWithRetries(client, semaphore, "GET", url, headers=req_headers, params=params)
        if resp.status_code != 200:
            raise RuntimeError(
                f"GET {path} HTTP {resp.status_code} lang={language} page={page}: {resp.text[:1200]}"
            )
        try:
            root = resp.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GET {path} 非 JSON: {resp.text[:500]}") from exc
        if not isinstance(root, dict):
            raise RuntimeError(f"GET {path} 根非对象: {root!r}")
        root_dict = cast(JsonDict, root)
        if not IsBusinessOk(root_dict):
            raise RuntimeError(f"GET {path} 业务 code 失败: {root_dict!r}"[:2000])
        inner_dict, _ = UnwrapDataPayload(root_dict)
        if inner_dict is None:
            break
        items = ExtractListFromDataInner(inner_dict)
        if items:
            for it in items:
                if isinstance(it, dict):
                    await state.IngestFromPayload(language, cast(JsonDict, it))
        else:
            await state.IngestFromPayload(language, inner_dict)

        pag = ExtractPagination(inner_dict)
        if not items:
            break
        total = None
        if pag:
            tn = pag.get("totalNumber")
            if isinstance(tn, int):
                total = tn
            elif isinstance(tn, str) and tn.isdigit():
                total = int(tn)
        if total is not None and page * page_size >= total:
            break
        if len(items) < page_size:
            break
        page += 1


async def FetchHubDetailsForLanguage(
    *,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    headers: Mapping[str, str],
    hub_ids: Sequence[str],
    language: str,
    state: ScanState,
) -> None:
    base = GetBaseUrl().rstrip("/")
    _, _, lg_key = ResolveListQueryParamNames()
    mode = os.getenv("DP_SCAN_LANGUAGE_MODE", "query").strip().lower()
    for hid in hub_ids:
        seg = quote(hid, safe="")
        path = f"/v2/transportHubs/{seg}"
        url = base + path
        params: Optional[Dict[str, Union[str, int]]] = None
        req_headers = dict(headers)
        if mode == "header":
            req_headers["Accept-Language"] = language
        else:
            params = {lg_key: language}

        resp = await RequestWithRetries(client, semaphore, "GET", url, headers=req_headers, params=params)
        if resp.status_code != 200:
            raise RuntimeError(
                f"GET {path} HTTP {resp.status_code} lang={language}: {resp.text[:800]}"
            )
        try:
            root = resp.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"GET {path} 非 JSON: {resp.text[:400]}") from exc
        if not isinstance(root, dict):
            continue
        root_dict = cast(JsonDict, root)
        if not IsBusinessOk(root_dict):
            continue
        inner_dict, _ = UnwrapDataPayload(root_dict)
        if inner_dict is not None:
            await state.IngestFromPayload(language, inner_dict)
        else:
            await state.IngestFromPayload(language, root_dict)


def PickKeywordForHub(
    hub_id: str,
    names_by_lang: Mapping[str, Mapping[str, str]],
    name_priority: Sequence[str],
) -> Optional[str]:
    per_lang = names_by_lang.get(hub_id, {})
    for lang in name_priority:
        n = per_lang.get(lang)
        if n:
            return n
    for _lg, n in per_lang.items():
        if n:
            return n
    return None


def BuildAnomalyReport(
    state: ScanState,
    *,
    dump_all_hub_regions: bool,
    include_seen_hub_ids: bool,
    include_anomaly_breakdown: bool,
) -> JsonDict:
    anomalies = sorted(hid for hid, regs in state.hub_to_regions.items() if len(regs) >= 2)
    hub_regions_serial = {h: sorted(state.hub_to_regions[h]) for h in anomalies}
    names_for_anomalies = {
        h: dict(state.hub_names_by_lang[h]) for h in anomalies if h in state.hub_names_by_lang
    }
    out: JsonDict = {
        "anomaly_transport_hub_ids": anomalies,
        "anomaly_count": len(anomalies),
        "hub_to_regions": hub_regions_serial,
        "hub_names_by_lang": names_for_anomalies,
        "missing_region_events": state.missing_region_events,
        "seen_transport_hub_count": len(state.seen_hub_ids),
        "criteria": "Same transportHubId: union of region codes across all languages and API calls has size>=2; codes from countryOrRegion, iso2, etc.",
    }
    if include_anomaly_breakdown:
        breakdown: JsonDict = {}
        for h in anomalies:
            by_lang_raw = state.hub_regions_by_language.get(h, {})
            by_lang = {
                lang: sorted(regs)
                for lang, regs in sorted(by_lang_raw.items(), key=lambda x: x[0])
                if regs
            }
            breakdown[h] = {
                "regions_union": sorted(state.hub_to_regions[h]),
                "by_language": by_lang,
            }
        out["anomaly_breakdown"] = breakdown
    if dump_all_hub_regions:
        out["all_hub_to_regions"] = {k: sorted(v) for k, v in state.hub_to_regions.items()}
    if include_seen_hub_ids:
        out["seen_transport_hub_ids"] = sorted(state.seen_hub_ids)
    return out


def BuildAnomalySummaryTable(state: ScanState) -> List[JsonDict]:
    """
    仅异常 hub：``transportHubId``、跨请求出现次数最多的 ``commonIata``、地区码并集 ``regions``（排序列表）。
    """
    anomalies = sorted(hid for hid, regs in state.hub_to_regions.items() if len(regs) >= 2)
    rows: List[JsonDict] = []
    for hid in anomalies:
        rows.append(
            {
                "transportHubId": hid,
                "commonIata": PickCommonIataFromCounter(state.hub_iata_counts[hid]),
                "regions": sorted(state.hub_to_regions[hid]),
            }
        )
    return rows


async def RunScanPhase(
    *,
    mode: str,
    languages: Sequence[str],
    page_size: int,
    max_concurrency: int,
    skip_detail: bool,
    max_hubs_detail: Optional[int],
    detail_only_hub_ids: Optional[Sequence[str]],
) -> ScanState:
    limits = httpx.Limits(max_connections=max_concurrency + 5, max_keepalive_connections=max_concurrency + 5)
    async with httpx.AsyncClient(limits=limits) as client:
        token = await PostAccessTokenAsync(client)
        semaphore = asyncio.Semaphore(max_concurrency)
        state = ScanState()
        base_headers = BuildAuthHeaders(token)

        if mode == "detail-only":
            if not detail_only_hub_ids:
                raise RuntimeError("detail-only 模式须传入非空 detail_only_hub_ids")
            hub_list = sorted({str(x).strip() for x in detail_only_hub_ids if str(x).strip()})
            if not hub_list:
                raise RuntimeError("detail-only: 去重后 transportHubId 为空")
            if max_hubs_detail is not None:
                hub_list = hub_list[:max_hubs_detail]
            for hid in hub_list:
                state.seen_hub_ids.add(hid)
            await asyncio.gather(
                *[
                    FetchHubDetailsForLanguage(
                        client=client,
                        semaphore=semaphore,
                        headers=base_headers,
                        hub_ids=hub_list,
                        language=lang,
                        state=state,
                    )
                    for lang in languages
                ]
            )
            return state

        async def RunForAllLangs(path: str) -> None:
            await asyncio.gather(
                *[
                    PaginateListEndpoint(
                        client=client,
                        semaphore=semaphore,
                        headers=base_headers,
                        path=path,
                        language=lang,
                        page_size=page_size,
                        state=state,
                    )
                    for lang in languages
                ]
            )

        if mode in ("resources-only", "combined"):
            await RunForAllLangs("/v2/resources")
        if mode == "combined":
            await RunForAllLangs("/v2/transportHubs")
            if not skip_detail:
                hub_list = sorted(state.seen_hub_ids)
                if max_hubs_detail is not None:
                    hub_list = hub_list[:max_hubs_detail]
                await asyncio.gather(
                    *[
                        FetchHubDetailsForLanguage(
                            client=client,
                            semaphore=semaphore,
                            headers=base_headers,
                            hub_ids=hub_list,
                            language=lang,
                            state=state,
                        )
                        for lang in languages
                    ]
                )
        return state


def FindSearchHitForHub(results: Sequence[Any], hub_id: str) -> Optional[JsonDict]:
    for it in results:
        if not isinstance(it, dict):
            continue
        d = cast(JsonDict, it)
        if d.get("type") != 1:
            continue
        hid = d.get("transportHubId")
        if isinstance(hid, str) and hid == hub_id:
            return d
    return None


async def RunSearchProbe(
    *,
    languages: Sequence[str],
    anomaly_hub_ids: Sequence[str],
    hub_names_by_lang: Mapping[str, Mapping[str, str]],
    name_priority: Sequence[str],
    page_size: int,
    max_concurrency: int,
    enable_fuzzy: bool,
) -> JsonDict:
    limits = httpx.Limits(max_connections=max_concurrency + 5, max_keepalive_connections=max_concurrency + 5)
    async with httpx.AsyncClient(limits=limits) as client:
        token = await PostAccessTokenAsync(client)
        semaphore = asyncio.Semaphore(max_concurrency)
        base_headers = BuildAuthHeaders(token)
        base = GetBaseUrl().rstrip("/")
        search_url = base + "/v2/search"

        async def OneSearch(hub_id: str, keyword: str, language: str) -> JsonDict:
            body: JsonDict = {
                "keyword": keyword,
                "language": language,
                "pageSize": page_size,
                "pageNumber": 1,
                "searchFields": [1, 2, 3, 4, 5, 6],
                "enableFuzzy": enable_fuzzy,
                "sortBy": [1],
            }
            resp = await RequestWithRetries(
                client, semaphore, "POST", search_url, headers=base_headers, json_body=body
            )
            row: JsonDict = {
                "transportHubId": hub_id,
                "keyword": keyword,
                "language": language,
                "http_status": resp.status_code,
            }
            if resp.status_code != 200:
                row["error_text"] = resp.text[:1200]
                return row
            try:
                root = resp.json()
            except json.JSONDecodeError as exc:
                row["error"] = f"非 JSON: {exc}"
                return row
            if not isinstance(root, dict):
                row["error"] = "根非对象"
                return row
            rd = cast(JsonDict, root)
            row["business_ok"] = IsBusinessOk(rd)
            inner, _ = UnwrapDataPayload(rd)
            results: List[Any] = []
            if isinstance(inner, dict):
                r = inner.get("results")
                if isinstance(r, list):
                    results = r
            hit = FindSearchHitForHub(results, hub_id)
            if hit is None:
                row["hit_found"] = False
                row["results_type1_count"] = sum(
                    1 for x in results if isinstance(x, dict) and x.get("type") == 1
                )
            else:
                row["hit_found"] = True
                row["hit_countryOrRegion"] = hit.get("countryOrRegion")
                row["hit_transportHubName"] = hit.get("transportHubName")
            return row

        async def SkipNoKeyword(hub_id: str) -> JsonDict:
            return {"transportHubId": hub_id, "skipped": True, "reason": "no_keyword"}

        tasks: List[asyncio.Task[JsonDict]] = []
        for hid in anomaly_hub_ids:
            kw = PickKeywordForHub(hid, hub_names_by_lang, name_priority)
            if not kw:
                tasks.append(asyncio.create_task(SkipNoKeyword(hid)))
                continue
            for lang in languages:
                tasks.append(asyncio.create_task(OneSearch(hid, kw, lang)))

        rows = await asyncio.gather(*tasks)
        return {"search_rows": list(rows)}


def ParseLanguagesArg(raw: Optional[str]) -> Tuple[str, ...]:
    if not raw or not raw.strip():
        return DEFAULT_LANGUAGES
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts)


def ParseSkipLanguagesArg(raw: Optional[str]) -> Set[str]:
    if not raw or not raw.strip():
        return set()
    return {p.strip() for p in raw.split(",") if p.strip()}


def ApplyLanguageSkips(languages: Sequence[str], skip: Set[str]) -> Tuple[str, ...]:
    """按原顺序保留不在 ``skip`` 中的语种（大小写敏感，须与 ``--languages`` 写法一致）。"""
    if not skip:
        return tuple(languages)
    return tuple(lang for lang in languages if lang not in skip)


def ParseNamePriorityArg(raw: Optional[str]) -> Tuple[str, ...]:
    if not raw or not raw.strip():
        return ("en-US", "ja-JP")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts)


def LoadScanJson(path: Path) -> JsonDict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"无法读取 JSON 文件: {path}") from exc
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"非合法 JSON: {path}") from exc
    if not isinstance(obj, dict):
        raise RuntimeError("JSON 根须为对象")
    return cast(JsonDict, obj)


def LoadSeenHubIdsFromScanJson(path: Path) -> List[str]:
    """
    从上一轮扫描输出中读取 ``seen_transport_hub_ids``（与 ``--include-seen-hub-ids`` 写入的字段一致）。
    """
    root = LoadScanJson(path)
    ids_raw = root.get("seen_transport_hub_ids")
    if not isinstance(ids_raw, list):
        raise RuntimeError(
            f"{path} 缺少 seen_transport_hub_ids 数组；请先对 combined/resources-only 使用 --include-seen-hub-ids 输出"
        )
    out = [str(x).strip() for x in ids_raw if str(x).strip()]
    if not out:
        raise RuntimeError(f"{path} 中 seen_transport_hub_ids 为空")
    return out


async def Amain() -> int:
    parser = argparse.ArgumentParser(
        description="多语种 transportHubId/countryOrRegion 扫描与 /v2/search 探测",
    )
    parser.add_argument(
        "--mode",
        choices=("combined", "resources-only", "detail-only", "search"),
        required=True,
        help="combined=resources+transportHubs+详情；resources-only=仅 resources；detail-only=仅 GET /v2/transportHubs/{id}（需 --seen-hub-ids-json）；search=仅探测（需 --scan-json）",
    )
    parser.add_argument(
        "--languages",
        default=None,
        help="逗号分隔 BCP47，默认 12 语种",
    )
    parser.add_argument(
        "--skip-languages",
        default=None,
        help="逗号分隔，从生效语种列表中移除（如 pre 不支持 ko-KR：--skip-languages ko-KR）",
    )
    parser.add_argument("--page-size", type=int, default=100, help="列表与 search 分页大小")
    parser.add_argument("--max-concurrency", type=int, default=48, help="全局并发上限（信号量）")
    parser.add_argument("--skip-detail", action="store_true", help="combined 模式下跳过 GET /v2/transportHubs/{id}")
    parser.add_argument(
        "--max-hubs-detail",
        type=int,
        default=None,
        help="详情接口最多处理的 hub 数（截断，用于超大目录）",
    )
    parser.add_argument("--output-json", type=Path, default=None, help="写入完整结果 JSON")
    parser.add_argument(
        "--scan-json",
        type=Path,
        default=None,
        help="search 模式：上一轮扫描输出的 JSON（含 anomaly_transport_hub_ids 与 hub_names_by_lang）",
    )
    parser.add_argument(
        "--seen-hub-ids-json",
        type=Path,
        default=None,
        help="detail-only：含 seen_transport_hub_ids 的 JSON（通常由 combined/resources-only + --include-seen-hub-ids 生成）",
    )
    parser.add_argument(
        "--name-lang-priority",
        default=None,
        help="keyword 取名顺序，逗号分隔，默认 en-US,ja-JP",
    )
    parser.add_argument(
        "--search-fuzzy",
        action="store_true",
        help="search 请求 enableFuzzy=true",
    )
    parser.add_argument(
        "--run-search-after-scan",
        action="store_true",
        help="combined/resources-only 完成后立即对异常 hub 跑 search（写入同一 output-json）",
    )
    parser.add_argument(
        "--dump-all-hub-regions",
        action="store_true",
        help="在结果 JSON 中额外输出 all_hub_to_regions（全量 hub→regions，体积可能很大）",
    )
    parser.add_argument(
        "--include-seen-hub-ids",
        action="store_true",
        help="在结果 JSON 中输出 seen_transport_hub_ids（resources/transportHubs 等扫描中去重排序后的 ID 列表）",
    )
    parser.add_argument(
        "--include-anomaly-breakdown",
        action="store_true",
        help="输出 anomaly_breakdown：每个异常 hub 的 regions_union 与按语种拆分的 by_language",
    )
    parser.add_argument(
        "--output-anomaly-table",
        type=Path,
        default=None,
        help="另存异常清单 JSON 数组（transportHubId、commonIata、regions）；完整报告内亦含键 anomaly_summary_table",
    )
    args = parser.parse_args()
    LoadAllDotenvLayers()

    skip_langs = ParseSkipLanguagesArg(args.skip_languages)
    languages = ApplyLanguageSkips(ParseLanguagesArg(args.languages), skip_langs)
    if not languages:
        print("剔除 --skip-languages 后语种列表为空", file=sys.stderr)
        return 2
    name_priority = ParseNamePriorityArg(args.name_lang_priority)
    t0 = time.perf_counter()

    report: JsonDict = {"mode": args.mode, "languages": list(languages)}
    if skip_langs:
        report["skipped_languages"] = sorted(skip_langs)

    if args.mode == "detail-only":
        if args.seen_hub_ids_json is None:
            print("detail-only 模式必须提供 --seen-hub-ids-json", file=sys.stderr)
            return 2
        try:
            detail_hub_ids = LoadSeenHubIdsFromScanJson(args.seen_hub_ids_json)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    else:
        detail_hub_ids = None

    if args.mode == "search":
        if args.scan_json is None:
            print("search 模式必须提供 --scan-json", file=sys.stderr)
            return 2
        scan_obj = LoadScanJson(args.scan_json)
        ids_raw = scan_obj.get("anomaly_transport_hub_ids")
        if not isinstance(ids_raw, list):
            print("scan-json 缺少 anomaly_transport_hub_ids 数组", file=sys.stderr)
            return 2
        hub_ids = [str(x) for x in ids_raw if str(x).strip()]
        names_root = scan_obj.get("hub_names_by_lang")
        if not isinstance(names_root, dict):
            print("scan-json 缺少 hub_names_by_lang 对象", file=sys.stderr)
            return 2
        hub_names: Dict[str, Dict[str, str]] = {}
        for hid, langs in names_root.items():
            if not isinstance(langs, dict):
                continue
            hub_names[str(hid)] = {str(k): str(v) for k, v in langs.items() if isinstance(v, str)}
        search_part = await RunSearchProbe(
            languages=languages,
            anomaly_hub_ids=hub_ids,
            hub_names_by_lang=hub_names,
            name_priority=name_priority,
            page_size=args.page_size,
            max_concurrency=args.max_concurrency,
            enable_fuzzy=args.search_fuzzy,
        )
        report.update(search_part)
    else:
        state = await RunScanPhase(
            mode=args.mode,
            languages=languages,
            page_size=args.page_size,
            max_concurrency=args.max_concurrency,
            skip_detail=args.skip_detail,
            max_hubs_detail=args.max_hubs_detail,
            detail_only_hub_ids=detail_hub_ids,
        )
        scan_report = BuildAnomalyReport(
            state,
            dump_all_hub_regions=args.dump_all_hub_regions,
            include_seen_hub_ids=args.include_seen_hub_ids,
            include_anomaly_breakdown=args.include_anomaly_breakdown,
        )
        report.update(scan_report)
        summary_table = BuildAnomalySummaryTable(state)
        report["anomaly_summary_table"] = summary_table
        if args.output_anomaly_table is not None:
            table_text = json.dumps(summary_table, ensure_ascii=False, indent=2) + "\n"
            args.output_anomaly_table.write_text(table_text, encoding="utf-8")
        if args.run_search_after_scan:
            anomalies = cast(List[str], scan_report.get("anomaly_transport_hub_ids", []))
            search_part = await RunSearchProbe(
                languages=languages,
                anomaly_hub_ids=anomalies,
                hub_names_by_lang=state.hub_names_by_lang,
                name_priority=name_priority,
                page_size=args.page_size,
                max_concurrency=args.max_concurrency,
                enable_fuzzy=args.search_fuzzy,
            )
            report["search"] = search_part

    report["elapsed_seconds"] = round(time.perf_counter() - t0, 3)
    text_out = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output_json is not None:
        args.output_json.write_text(text_out, encoding="utf-8")
    try:
        reconf = getattr(sys.stdout, "reconfigure", None)
        if callable(reconf):
            reconf(encoding="utf-8", errors="replace")
    except (OSError, TypeError, ValueError):
        pass
    try:
        sys.stdout.write(text_out)
    except UnicodeEncodeError:
        sys.stdout.write(json.dumps(report, ensure_ascii=True, indent=2) + "\n")
    return 0


def Main() -> None:
    raise SystemExit(asyncio.run(Amain()))


if __name__ == "__main__":
    Main()
