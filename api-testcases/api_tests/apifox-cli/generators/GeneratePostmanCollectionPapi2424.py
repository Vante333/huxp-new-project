"""
根据 tests/regression/test_epass_orders_ms_hint.py / services/papi2424_service.py 生成 Postman Collection v2.1 JSON。

含与 helpers 对齐的 Tests（JavaScript）；Apifox CLI Repo-first 真相源。
鉴权三列统一 ``ProgramID`` / ``clientId`` / ``secret``（填 ePass 凭据，对齐 ``GetAccessTokenForEpass``）。

NM01（真实 usage 不命中 MS 提示）前嵌 FT 造数链（复用 FastTrack-ePass P0 E02）：
创建 ePass → 可用性 → prebooking → details(NM01) → 取消 usage。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionPapi2424.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Union

from collection_builder_common import CollectionPath, Lines_EnsureRequestIdHeader
from fasttrack_prebooking_common import (
    AvailabilityBody,
    BuildCancelWithRetryBlock,
    BuildFastTrackJsHelpersLines,
    CREATE_PAYLOAD_TEMPLATE,
    DEFAULT_FASTTRACK_RESOURCE_ID,
    EPASS_MODULE_DEFAULT,
    FASTTRACK_RESOURCE_ID_VAR,
    FastTrackPrebookingExtraDict,
    Prerequest_ResetForPrebooking,
    Prerequest_SyncPrebookingDateFromApifox,
    Prerequest_SyncPrebookingPassengersBody,
)

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
OUT_NAME: Final[str] = "PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json"

# 与 papi2424_helpers 一致
P2424_MS_HINT_ERR: Final[str] = "500.000.024"
P2424_MS_HINT_MSG: Final[str] = (
    "The order ID you entered is not a usage order ID. If you want to query E-pass details, "
    "please use the /orders/ePasses/search API."
)


def BuildP2424JsHelpersLines() -> List[str]:
    """与 papi2424_helpers 中 MS 提示/非 MS/usage 回归/大小写分支语义对齐的 Postman Tests 公共脚本。"""
    err_lit = json.dumps(P2424_MS_HINT_ERR, ensure_ascii=False)
    msg_lit = json.dumps(P2424_MS_HINT_MSG, ensure_ascii=False)
    js = rf"""
var P2424_MS_HINT_ERR = {err_lit};
var P2424_MS_HINT_MSG = {msg_lit};

function p2424IsBusinessSuccess(json) {{
  if (!json || typeof json !== "object") return false;
  var c = json.code;
  return c === 0 || c === "0";
}}

function fmtJsonBrief(v, maxLen) {{
  maxLen = maxLen || 240;
  var s;
  try {{ s = JSON.stringify(v); }} catch (e) {{ s = String(v); }}
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}}

function assertCheck(checkpoint, expected, actual) {{
  var title = checkpoint + ' | 期望=' + fmtJsonBrief(expected) + ' | 实际=' + fmtJsonBrief(actual);
  pm.test(title, function () {{
    pm.expect(actual).to.eql(expected);
  }});
}}

function assertHttp(checkpoint, expectedCode) {{
  assertCheck(checkpoint, expectedCode, pm.response.code);
}}

function assertInfo(checkpoint, expectedDesc, actualValue) {{
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + fmtJsonBrief(actualValue);
  pm.test(title, function () {{
    pm.expect(true).to.eql(true);
  }});
}}

function p2424MsPrefixCaseInsensitiveFromEnv(pm) {{
  var v = String(pm.collectionVariables.get("DP_P2424_MS_PREFIX_CASE_INSENSITIVE") || "")
    .trim()
    .toLowerCase();
  return v === "1" || v === "true" || v === "yes" || v === "on";
}}

/** 对齐 ``AssertHttp200MsUsageOrderHintEnvelope`` */
function p2424AssertMsUsageOrderHintEnvelope(pm, context) {{
  context = context || "PAPI-2424";
  assertHttp(context + ': HTTP 状态码', 200);
  var root = {{}};
  try {{ root = pm.response.json(); }} catch (e) {{ root = {{}}; }}
  assertCheck(context + ': code', -1, root.code);
  assertCheck(context + ': errCode', P2424_MS_HINT_ERR, String(root.errCode));
  assertCheck(context + ': msg 全文', P2424_MS_HINT_MSG, root.msg);
}}

/** 对齐 ``AssertHttp200NotMsUsageOrderHint`` */
function p2424AssertNotMsUsageOrderHint(pm, context) {{
  context = context || "PAPI-2424";
  assertHttp(context + ': HTTP 状态码', 200);
  var root = {{}};
  try {{ root = pm.response.json(); }} catch (e) {{ root = {{}}; }}
  var errS = root.errCode === undefined || root.errCode === null ? "" : String(root.errCode);
  var title = context + ': 排除 MS 专用 errCode | 期望!=500.000.024 | 实际=' + errS;
  pm.test(title, function () {{
    pm.expect(errS).to.not.eql(P2424_MS_HINT_ERR);
  }});
  var msg = root.msg;
  if (typeof msg === "string" && msg) {{
    var t2 = context + ': 排除 MS 全文 msg | 期望!=专用文案 | 实际=' + fmtJsonBrief(msg);
    pm.test(t2, function () {{
      pm.expect(msg).to.not.eql(P2424_MS_HINT_MSG);
    }});
  }}
}}

/** 对齐 ``AssertUsageOrderRegressionNotMsHint``；无 usage 订单号时软跳过 */
function p2424AssertUsageOrderRegressionNotMsHint(pm, context) {{
  context = context || "PAPI-2424-usage";
  var oid = "";
  try {{ oid = String(pm.collectionVariables.get("p2424UsageOrderId") || "").trim(); }} catch (e0) {{}}
  if (!oid) {{
    try {{ oid = String(pm.variables.get("p2424UsageOrderId") || "").trim(); }} catch (e1) {{}}
  }}
  if (!oid) {{
    try {{ oid = String((pm.environment && pm.environment.get("p2424UsageOrderId")) || "").trim(); }} catch (e2) {{}}
  }}
  if (!oid) {{
    try {{ oid = String(pm.collectionVariables.get("usageOrderId") || "").trim(); }} catch (e3) {{}}
  }}
  if (!oid) {{
    assertInfo(context + ': 未配置 p2424UsageOrderId/usageOrderId 可跳过', '非空 usage 订单号', oid);
    return;
  }}
  assertHttp(context + ': HTTP 状态码', 200);
  var root = {{}};
  try {{ root = pm.response.json(); }} catch (e) {{ root = {{}}; }}
  var errS = root.errCode === undefined || root.errCode === null ? "" : String(root.errCode);
  var title = context + ': usage 不命中 500.000.024 | 期望!=500.000.024 | 实际=' + errS;
  pm.test(title, function () {{
    pm.expect(errS).to.not.eql(P2424_MS_HINT_ERR);
  }});
}}

/** 对齐 ``AssertLowercaseMsPrefixBehavior``（依赖集合变量 DP_P2424_MS_PREFIX_CASE_INSENSITIVE） */
function p2424AssertLowercaseMsPrefixBehavior(pm, context) {{
  context = context || "PAPI-2424-case";
  var insensitive = p2424MsPrefixCaseInsensitiveFromEnv(pm);
  if (insensitive) {{
    p2424AssertMsUsageOrderHintEnvelope(pm, context);
  }} else {{
    p2424AssertNotMsUsageOrderHint(pm, context);
  }}
}}
""".strip()
    return js.splitlines()


def P2424OnlyHelpers() -> List[str]:
    return BuildP2424JsHelpersLines()


def P2424AndFtHelpers() -> List[str]:
    """MS 断言 helpers + FT E02 造数 helpers（同脚本注入，便于 SETUP 步复用）。

    关闭 ``usedUsages=1``：本场景默认 adultCount=2，prebooking 回显 ``usedUsages=2`` 为正确行为。
    """
    return [
        *BuildP2424JsHelpersLines(),
        *BuildFastTrackJsHelpersLines(assert_usage_used_usages_one=False),
    ]


def SyncP2424UsageOrderIdLines() -> List[str]:
    """prebooking 成功后把 ``usageOrderId`` 同步到 ``p2424UsageOrderId``（多作用域）。"""
    return [
        "(function () {",
        "  var u = '';",
        "  try { u = String(pm.collectionVariables.get('usageOrderId') || '').trim(); } catch (e0) {}",
        "  if (!u) { return; }",
        "  try { pm.collectionVariables.set('p2424UsageOrderId', u); } catch (e1) {}",
        "  try { pm.variables.set('p2424UsageOrderId', u); } catch (e2) {}",
        "  pm.test('SETUP: p2424UsageOrderId 已同步', function () {",
        "    pm.expect(u).to.be.a('string').and.not.empty;",
        "  });",
        "})();",
    ]


def SaveTokenLines() -> List[str]:
    """Auth 后置：把响应令牌写入多作用域（Apifox 场景下 collection 常不可用）。"""
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    var tok = String(t);",
        "    try { pm.variables.set('accessToken', tok); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', tok); } catch (eC) {}",
        "    try { pm.environment.set('accessToken', tok); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', tok); } catch (eG) {}",
        "  }",
        "} catch (e) { console.warn(e); }",
        "pm.test('Auth: accessToken 已写入运行时', function () {",
        "  var _a = ''; try { _a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var _b = ''; try { _b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  var _c = ''; try { _c = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e3) {}",
        "  var _d = ''; try { _d = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (e4) {}",
        "  pm.expect(_a || _b || _c || _d, 'variables/collection/env/globals 均无 accessToken').to.be.ok;",
        "});",
    ]


def Lines_Auth() -> List[str]:
    return [
        "assertHttp('Auth: HTTP 状态码', 200);",
        "var _j_Auth = (function () { try { return pm.response.json(); } catch (e) { return {}; } })();",
        "var _d_Auth = _j_Auth.data !== undefined ? _j_Auth.data : _j_Auth;",
        "var _t_Auth = _d_Auth && (_d_Auth.accessToken || _d_Auth.token || _d_Auth.access_token);",
        "assertCheck('Auth: accessToken 非空', true, !!_t_Auth);",
        "assertInfo('Auth: accessToken 前缀', '非空令牌', _t_Auth ? (String(_t_Auth).slice(0, 12) + '...') : null);",
    ]


def MakeP2424TestEvent(
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
    js_helpers: Optional[Callable[[], List[str]]] = None,
) -> List[JsonObject]:
    helper_fn = js_helpers or P2424OnlyHelpers
    lines: List[str] = []
    lines.extend(helper_fn())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def AuthJsonHeaders() -> List[JsonObject]:
    """取 token：X-Program-ID 使用数据集 ``ProgramID``（填 ePass Program）。"""
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    """业务请求：Program / Bearer 与 pytest ePass 主线一致。"""
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def Lines_EnsureAuthPrerequest() -> List[str]:
    """发送前：补齐 baseUrl/ProgramID/x-version；强制注入 Authorization。"""
    return [
        "try {",
        "  var _base = '';",
        "  try { _base = String((pm.environment && pm.environment.get('baseUrl')) || '').trim(); } catch (eB0) {}",
        "  if (!_base) { try { _base = String(pm.variables.get('baseUrl') || '').trim(); } catch (eB1) {} }",
        "  if (!_base) { try { _base = String(pm.collectionVariables.get('baseUrl') || '').trim(); } catch (eB2) {} }",
        "  if (_base) {",
        "    try { pm.variables.set('baseUrl', _base); } catch (eBS1) {}",
        "    try { pm.collectionVariables.set('baseUrl', _base); } catch (eBS2) {}",
        "  }",
        "  var _pid = '';",
        "  try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {}",
        "  if (!_pid) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eP1) {} }",
        "  if (!_pid) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eP2) {} }",
        "  if (_pid) {",
        "    try { pm.variables.set('ProgramID', _pid); } catch (ePS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid });",
        "      }",
        "    } catch (ePH) {}",
        "  }",
        "  var _xv = '';",
        "  try { _xv = String((pm.environment && pm.environment.get('x-version')) || '').trim(); } catch (eX0) {}",
        "  if (!_xv) { try { _xv = String(pm.variables.get('x-version') || '').trim(); } catch (eX1) {} }",
        "  if (!_xv) { try { _xv = String(pm.collectionVariables.get('x-version') || '').trim(); } catch (eX2) {} }",
        "  if (_xv && ['omit','none','off'].indexOf(_xv.toLowerCase()) < 0) {",
        "    try { pm.variables.set('x-version', _xv); } catch (eXS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'x-version', value: _xv });",
        "      }",
        "    } catch (eXH) {}",
        "  }",
        "  try {",
        "    var _rawTok = pm.variables.get('accessToken');",
        "    if (_rawTok !== undefined && _rawTok !== null && String(_rawTok).trim() === '') {",
        "      try { pm.variables.unset('accessToken'); } catch (eUn) { try { pm.variables.set('accessToken', ''); } catch (eUn2) {} }",
        "    }",
        "  } catch (eClr) {}",
        "  var _tok = '';",
        "  try { _tok = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e3) {}",
        "  if (!_tok) { try { _tok = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (eG1) {} }",
        "  if (!_tok) { try { _tok = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e4) {} }",
        "  if (!_tok) { try { _tok = String(pm.variables.get('accessToken') || '').trim(); } catch (e5) {} }",
        "  if (_tok) {",
        "    try { pm.variables.set('accessToken', _tok); } catch (eTV) {}",
        "    try { pm.collectionVariables.set('accessToken', _tok); } catch (eTC) {}",
        "    try { pm.environment.set('accessToken', _tok); } catch (eTE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', _tok); } catch (eTG) {}",
        "    var _auth = 'Bearer ' + _tok;",
        "    try {",
        "      var _hdrs = pm.request && pm.request.headers;",
        "      if (_hdrs && typeof _hdrs.upsert === 'function') {",
        "        _hdrs.upsert({ key: 'Authorization', value: _auth });",
        "      } else if (_hdrs && typeof _hdrs.add === 'function') {",
        "        try { if (typeof _hdrs.remove === 'function') _hdrs.remove('Authorization'); } catch (eRm) {}",
        "        _hdrs.add({ key: 'Authorization', value: _auth });",
        "      }",
        "    } catch (eH) { console.warn('P2424 ensure bearer', eH); }",
        "  }",
        "} catch (eAll) {}",
        *Lines_EnsureRequestIdHeader(),
    ]


def PostmanUrl(url_path: str) -> JsonObject:
    """尽量贴近 Postman 客户端导出结构，兼容 Apifox 对 `url` 形态的严格校验。"""
    raw: str = "{{baseUrl}}" + url_path
    path_parts: List[str] = [part for part in url_path.split("/") if part]
    return {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}


def PostmanJsonRawBody(raw: str) -> JsonObject:
    """与 Postman 导出一致，便于 Apifox 识别 JSON Body。"""
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    """与 Postman/Apifox 示例一致，显式标注集合变量类型。"""
    return {"key": key, "value": value, "type": "string"}


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    """测试目的前置：``【目的】| 步骤ID | METHOD /path``。"""
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def RequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    test_lines: Optional[Sequence[str]] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
    js_helpers: Optional[Callable[[], List[str]]] = None,
) -> JsonObject:
    helper_fn = js_helpers or P2424OnlyHelpers
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)
    out: JsonObject = {"name": name, "request": req}
    # helpers 注入 prerequest：FT 步需 ftSyncPrebookingPassengersBody 等
    pre_lines: List[str] = [*helper_fn(), *Lines_EnsureAuthPrerequest()]
    if prerequest_lines:
        pre_lines.extend(list(prerequest_lines))
    out["event"] = [
        {
            "listen": "prerequest",
            "script": {"exec": pre_lines, "type": "text/javascript"},
        },
        MakeP2424TestEvent(
            save_token=save_token,
            extra_lines=test_lines,
            js_helpers=helper_fn,
        )[0],
    ]
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def DetailsBodyRaw(order_id: str) -> str:
    """``order_id`` 为字面订单号，或已含 ``{{var}}`` 的占位（仅 usage 可选变量用后者）。"""
    return json.dumps({"orderId": order_id}, ensure_ascii=False, indent=2)


def BuildCollection() -> JsonObject:
    # Apifox 场景 customHttp 下集合变量 path（如 {{p2424V2DetailsPath}}）常不解析，须写死真实路径
    details_v2: Final[str] = "/v2/orders/ePasses/details"
    details_v1: Final[str] = "/v1/orders/ePasses/details"
    auth_folder: JsonObject = Folder(
        "00 Auth（ePass）",
        [
            RequestItem(
                name=PurposeName("鉴权获取访问令牌", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps(
                    {"clientId": "{{clientId}}", "secret": "{{secret}}"},
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=AuthJsonHeaders(),
                description=(
                    "与 GetAccessTokenForEpass 一致；数据集三列 ProgramID/clientId/secret 填 **ePass** 凭据"
                    "（对应 DP_EPASS_PROGRAM_ID / DP_EPASS_CLIENT_ID / DP_EPASS_CLIENT_SECRET）。"
                ),
                save_token=True,
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行以写入 accessToken。",
    )

    ms_folder: JsonObject = Folder(
        "01 tc-P2-EPASS-001（MS 前缀 → 500.000.024）",
        [
            RequestItem(
                name=PurposeName("MS最短前缀返回search提示", "MS01", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("MS"),
                headers=BearerJsonHeaders(),
                description="参数化 orderId=MS；对齐 test_ms_prefix_returns_search_hint。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'MS01');"],
            ),
            RequestItem(
                name=PurposeName("典型MS订单号返回search提示", "MS02", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("MS00000000000001"),
                headers=BearerJsonHeaders(),
                description="参数化 orderId=MS00000000000001。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'MS02');"],
            ),
        ],
    )

    nm02_name = PurposeName("DP子串含MS但非前缀", "NM02", "POST", details_v2)
    non_ms_folder: JsonObject = Folder(
        "02 tc-P1 / tc-P3（非 MS 子串与 usage）",
        [
            RequestItem(
                name=PurposeName("造数：创建 fastTrack ePass", "SETUP-S01", "POST", "/fastTrack/ePasses"),
                method="POST",
                url_path="/v2/orders/fastTrack/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description=(
                    "NM01 前置：对齐 FT E02-S01 ``POST /v2/orders/fastTrack/ePasses``；"
                    "写入 ePassId / purchaseOrderId（MS 主单，勿给 NM01）。"
                ),
                prerequest_lines=Prerequest_ResetForPrebooking(),
                js_helpers=P2424AndFtHelpers,
                test_lines=[
                    "ftAssertHttpBusinessOk('SETUP-S01');",
                    "ftAssertCreateCoreFields('SETUP-S01');",
                ],
            ),
            RequestItem(
                name=PurposeName(
                    "造数：可用性取 prebookingToken",
                    "SETUP-S02",
                    "POST",
                    "/prebookings/availability",
                ),
                method="POST",
                url_path="/v2/resources/prebookings/availability",
                body=AvailabilityBody(with_epass=True),
                headers=BearerJsonHeaders(),
                description=(
                    "NM01 前置：对齐 FT E02-S02；须 Environment/集合已填 "
                    f"``{FASTTRACK_RESOURCE_ID_VAR}``（默认 {DEFAULT_FASTTRACK_RESOURCE_ID}）。"
                ),
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
                js_helpers=P2424AndFtHelpers,
                test_lines=[
                    "ftAssertHttpBusinessOk('SETUP-S02');",
                    "ftAssertAvailabilitySuccess('SETUP-S02');",
                ],
            ),
            RequestItem(
                name=PurposeName(
                    "造数：FT预约下单得usage单",
                    "SETUP-S03",
                    "POST",
                    "/fastTrack/ePasses/prebooking",
                ),
                method="POST",
                url_path="/v2/orders/fastTrack/ePasses/prebooking",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "ePassId": "{{ePassId}}",
                        "extra": FastTrackPrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description=(
                    "NM01 前置：对齐 FT E02-S03；写入 usageOrderId 并同步 p2424UsageOrderId。"
                ),
                prerequest_lines=Prerequest_SyncPrebookingPassengersBody(),
                js_helpers=P2424AndFtHelpers,
                test_lines=[
                    "ftAssertPrebookingPassengersShape('SETUP-S03');",
                    "ftAssertHttpBusinessOk('SETUP-S03');",
                    "ftAssertPrebookingOrderSuccess('SETUP-S03');",
                    *SyncP2424UsageOrderIdLines(),
                ],
            ),
            RequestItem(
                name=PurposeName("真实usage订单不命中MS提示", "NM01", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("{{p2424UsageOrderId}}"),
                headers=BearerJsonHeaders(),
                description=(
                    "对齐 test_usage_order_id_not_ms_hint；orderId 来自 SETUP-S03 usage 单。"
                    "若造数失败导致 p2424UsageOrderId/usageOrderId 皆空则 Tests 软跳过。"
                ),
                js_helpers=P2424AndFtHelpers,
                test_lines=["p2424AssertUsageOrderRegressionNotMsHint(pm, 'NM01');"],
            ),
            *BuildCancelWithRetryBlock(
                purpose="收尾：取消 FT usage 预订单",
                step_prefix="SETUP-S04",
                order_id_var="usageOrderId",
                skip_to_request_name=nm02_name,
                description="对齐 FT E02-S07：取消 SETUP 造出的 usage 单后再跑 NM02/NM03。",
            ),
            RequestItem(
                name=nm02_name,
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("DP000MS00000001"),
                headers=BearerJsonHeaders(),
                description="含 MS 子串但非前缀。",
                test_lines=["p2424AssertNotMsUsageOrderHint(pm, 'NM02');"],
            ),
            RequestItem(
                name=PurposeName("SL样例子串含MS但非前缀", "NM03", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("SL20260129BBMSXV9"),
                headers=BearerJsonHeaders(),
                description="SL 样例。",
                test_lines=["p2424AssertNotMsUsageOrderHint(pm, 'NM03');"],
            ),
        ],
        description=(
            "NM01 前嵌 FT 造数：创建 → 可用性 → prebooking → details → 取消 usage；"
            f"复用 FastTrack-ePass P0 E02（``{FASTTRACK_RESOURCE_ID_VAR}`` 默认 {DEFAULT_FASTTRACK_RESOURCE_ID}）。"
        ),
    )

    case_folder: JsonObject = Folder(
        "03 tc-P3-EPASS-002（MS vs ms）",
        [
            RequestItem(
                name=PurposeName("大写MS前缀恒为提示信封", "CS01", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("MS00000000000001"),
                headers=BearerJsonHeaders(),
                description="大写 MS 前缀恒为 500.000.024 信封。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'CS01');"],
            ),
            RequestItem(
                name=PurposeName("小写ms前缀按环境开关断言", "CS02", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("ms00000000000001"),
                headers=BearerJsonHeaders(),
                description=(
                    "小写 ms：集合变量 DP_P2424_MS_PREFIX_CASE_INSENSITIVE 为 1/true/yes/on 时期望与大写相同；"
                    "否则期望非 MS 专用码/全文 msg。"
                ),
                test_lines=["p2424AssertLowercaseMsPrefixBehavior(pm, 'CS02');"],
            ),
        ],
    )

    v1v2_folder: JsonObject = Folder(
        "04 tc-P2-EPASS-002（V1/V2 路径对拍）",
        [
            RequestItem(
                name=PurposeName("V1路径MS前缀同一信封", "VV01", "POST", details_v1),
                method="POST",
                url_path=details_v1,
                body=DetailsBodyRaw("MS00000000000001"),
                headers=BearerJsonHeaders(),
                description="V1 路径对拍；网关无 V1 时可能 leftover。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'VV01');"],
            ),
            RequestItem(
                name=PurposeName("V2路径MS前缀同一信封", "VV02", "POST", details_v2),
                method="POST",
                url_path=details_v2,
                body=DetailsBodyRaw("MS00000000000001"),
                headers=BearerJsonHeaders(),
                description="V2 路径对拍。",
                test_lines=["p2424AssertMsUsageOrderHintEnvelope(pm, 'VV02');"],
            ),
        ],
    )

    info: JsonObject = {
        "name": "PAPI-2424 ePasses/details MS 订单提示（对齐 tests/regression/test_epass_orders_ms_hint + services/papi2424_service）",
        "description": (
            "由 GeneratePostmanCollectionPapi2424.py 生成；Tests 内联 BuildP2424JsHelpersLines；"
            "Group 02 SETUP 复用 GeneratePostmanCollectionFastTrackEpass（E02 链）。\n"
            "请求名采用目的前置：``【测试目的】| 步骤ID | METHOD /path``。\n"
            "导入 Apifox 后位于「后置脚本」；非可视化断言组件。\n\n"
            "**链路（Group 02）**：Auth → SETUP 创建 FT ePass → 可用性 → prebooking → "
            "NM01 details(usage) → 取消 usage → NM02/NM03。\n"
            "**多环境（Apifox Environment）**：``baseUrl``、``x-version``；"
            f"``{FASTTRACK_RESOURCE_ID_VAR}``（默认 {DEFAULT_FASTTRACK_RESOURCE_ID}，"
            "对应 DP_HIST_EPASS_FASTTRACK_RESOURCE_ID）。\n"
            "**数据集鉴权三列（填 ePass 凭据）**：``ProgramID``、``clientId``、``secret``"
            "（对应 DP_EPASS_PROGRAM_ID / DP_EPASS_CLIENT_ID / DP_EPASS_CLIENT_SECRET）。\n"
            "**变量关系**：SETUP-S01 → ePassId/purchaseOrderId；SETUP-S02 → prebookingToken；"
            "SETUP-S03 → usageOrderId → 同步 p2424UsageOrderId；NM01 body.orderId={{p2424UsageOrderId}}；"
            "SETUP-S04 PATCH /v2/orders 取消 usageOrderId。\n"
            "**运行时变量**：accessToken、clientUserId、ePassId、purchaseOrderId、usageOrderId、"
            "p2424UsageOrderId、prebookingToken、prebookingDate。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        # baseUrl / x-version 留空，由 Apifox Environment 注入
        CollectionVariable("baseUrl", ""),
        CollectionVariable("x-version", ""),
        # 勿预置空 accessToken / 鉴权三列；静态 orderId 已写死在 body
        CollectionVariable("p2424UsageOrderId", ""),
        CollectionVariable("DP_P2424_MS_PREFIX_CASE_INSENSITIVE", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("prebookingToken", ""),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable(FASTTRACK_RESOURCE_ID_VAR, DEFAULT_FASTTRACK_RESOURCE_ID),
        CollectionVariable("fastTrackAdultCount", "2"),
        CollectionVariable("fastTrackChildCount", "0"),
    ]

    root: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [auth_folder, ms_folder, non_ms_folder, case_folder, v1v2_folder],
    }
    return root


def Main() -> None:
    out_path: Path = CollectionPath(OUT_NAME)
    payload: JsonObject = BuildCollection()
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
