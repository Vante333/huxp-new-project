"""
Postman Collection v2.1 构建公共组件（RequestItem / Folder / Headers 等）。

供 ``generators/GeneratePostmanCollection*.py`` 复用。

目录约定（``apifox-cli/`` 按角色拆分）::

    generators/   正本（本文件与 Generate*.py）
    collections/  可审集合 JSON（提交）
    envs/         环境模板
    docs/         协作说明
    generated/    本地中间件（gitignore；勿当正本）
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Final, List, Mapping, Optional, Sequence, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

PREBOOKING_ADD_DAYS_START: Final[int] = 10
PREBOOKING_TIME_SUFFIX: Final[str] = "T10:00"


def PrebookingDateApifoxExpr(add_days: int = PREBOOKING_ADD_DAYS_START) -> str:
    """可用性 ``prebookingDate``：本机今天 + ``add_days`` 天，时刻固定 ``T10:00``。"""
    days = int(add_days)
    if days < 1 or days > 366:
        raise ValueError(f"prebooking addDays 超出范围: {days}")
    return (
        "{{$date.now|addDays("
        + str(days)
        + ")|format('yyyy-MM-dd')}}"
        + PREBOOKING_TIME_SUFFIX
    )


def Lines_SyncPrebookingDate(add_days: int = PREBOOKING_ADD_DAYS_START) -> List[str]:
    """
    前置：每次按今天+N 重算 ``prebookingDate`` 写入请求体。

    禁止沿用 Environment / Collection 旧值（否则实际请求会变成过期字面量）。
    """
    days = int(add_days)
    expr = PrebookingDateApifoxExpr(days)
    return [
        "var pb = '';",
        "try { pb = String(pm.variables.replaceIn("
        + json.dumps(expr)
        + ") || '').trim(); } catch (eR) {}",
        "if (!/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}/.test(pb)) {",
        "  var d = new Date(); d.setDate(d.getDate() + " + str(days) + ");",
        "  var y = d.getFullYear();",
        "  var m = String(d.getMonth() + 1); if (m.length < 2) m = '0' + m;",
        "  var day = String(d.getDate()); if (day.length < 2) day = '0' + day;",
        "  pb = y + '-' + m + '-' + day + "
        + json.dumps(PREBOOKING_TIME_SUFFIX)
        + ";",
        "}",
        "try { pm.variables.set('prebookingDate', pb); } catch (e0) {}",
        "try { pm.collectionVariables.set('prebookingDate', pb); } catch (e1) {}",
        "try { if (pm.environment && typeof pm.environment.unset === 'function') pm.environment.unset('prebookingDate'); } catch (e2) {}",
        "try { if (pm.globals && typeof pm.globals.unset === 'function') pm.globals.unset('prebookingDate'); } catch (e3) {}",
        "try {",
        "  if (pm.request && pm.request.body && pm.request.body.raw) {",
        "    var _bd = JSON.parse(String(pm.request.body.raw));",
        "    if (_bd && _bd.prebookingDate !== undefined) {",
        "      _bd.prebookingDate = pb;",
        "      pm.request.body.raw = JSON.stringify(_bd, null, 2);",
        "    }",
        "  }",
        "} catch (eB) {}",
    ]


def PostmanRootDir() -> Path:
    """``api-testcases/api_tests/apifox-cli`` 根目录。"""
    here = Path(__file__).resolve().parent
    if here.name == "generators":
        return here.parent
    return here


def CollectionsDir() -> Path:
    path = PostmanRootDir() / "collections"
    path.mkdir(parents=True, exist_ok=True)
    return path


def EnvsDir() -> Path:
    path = PostmanRootDir() / "envs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def DocsDir() -> Path:
    return PostmanRootDir() / "docs"


def GeneratedDir() -> Path:
    """本地中间件（Apifox 导入包等）；默认 gitignore。"""
    path = PostmanRootDir() / "generated"
    path.mkdir(parents=True, exist_ok=True)
    return path


def CollectionPath(file_name: str) -> Path:
    return CollectionsDir() / file_name


def EnvPath(file_name: str) -> Path:
    return EnvsDir() / file_name


def GeneratedArtifactPath(file_name: str) -> Path:
    return GeneratedDir() / file_name


def Lines_EnsureEnvKeysIfMissing(pairs: Sequence[tuple]) -> List[str]:
    """Environment 缺 key 或值为空时插入默认值，已有值不覆盖。"""
    items = [(str(k), str(v)) for k, v in list(pairs or []) if str(k).strip()]
    lines: List[str] = [
        "// --- 换测键：Environment 缺 key 则插入默认值（不覆盖已有）---",
        "try {",
        "  function _ensureEnvKey(key, seed) {",
        "    var cur = '';",
        "    try { cur = String((pm.environment && pm.environment.get(key)) || '').trim(); } catch (e0) {}",
        "    if (cur && cur.indexOf('{{') < 0) return;",
        "    try { if (pm.environment) pm.environment.set(key, String(seed)); } catch (e1) {}",
        "    console.log('[env] 插入缺失键 ' + key + '=' + seed);",
        "  }",
    ]
    for key, value in items:
        lines.append(
            "  _ensureEnvKey("
            + json.dumps(key, ensure_ascii=False)
            + ", "
            + json.dumps(value, ensure_ascii=False)
            + ");"
        )
    lines.append("} catch (eEns) { console.warn('[env] ensure keys', eEns); }")
    return lines


def Lines_LoadHelpersSource(key: str) -> List[str]:
    """业务步：eval Auth 写入的 helpers 源码变量。"""
    name = str(key or "").strip()
    if not name:
        raise ValueError("helpers source key 为空")
    return [
        f"// --- 加载 Auth 写入的 {name}（请先跑 00 Auth）---",
        "try {",
        "  var _src = '';",
        f"  try {{ _src = String(pm.collectionVariables.get('{name}') || ''); }} catch (e0) {{}}",
        f"  if (!_src) {{ try {{ _src = String(pm.variables.get('{name}') || ''); }} catch (e2) {{}} }}",
        f"  if (!_src) {{ try {{ _src = String((pm.globals && pm.globals.get('{name}')) || ''); }} catch (e3) {{}} }}",
        "  if (_src) { eval(_src); }",
        f"  else {{ console.error('[{name}] 为空：请先跑 00 Auth'); }}",
        "} catch (eLoad) { console.error('[" + name + "] load helpers failed', eLoad); }",
    ]


def Lines_ExportHelpersSource(key: str, source: str) -> List[str]:
    """Auth 后置：把 helpers 源码写入 collection/variables 并 eval（不写 Environment）。"""
    name = str(key or "").strip()
    if not name:
        raise ValueError("helpers source key 为空")
    dumped = json.dumps(str(source or ""), ensure_ascii=False)
    return [
        f"// --- 写入 {name}（后续步骤 eval）---",
        "try {",
        f"  var _hs = {dumped};",
        f"  try {{ pm.variables.set('{name}', _hs); }} catch (eV) {{}}",
        f"  try {{ pm.collectionVariables.set('{name}', _hs); }} catch (eC) {{}}",
        f"  console.log('[auth] {name} 已写入，len=' + String(_hs).length);",
        "  eval(_hs);",
        "} catch (eH) { console.warn('[auth] 写入 helpers 源码失败', eH); }",
        f"pm.test('Auth: {name} 已写入 | 期望=长度>100 | 实际=collection/variables', function () {{",
        "  var s = '';",
        f"  try {{ s = String(pm.collectionVariables.get('{name}') || ''); }} catch (e0) {{}}",
        f"  if (!s) {{ try {{ s = String(pm.variables.get('{name}') || ''); }} catch (e1) {{}} }}",
        f"  pm.expect(s.length > 100, '{name}').to.eql(true);",
        "});",
    ]


def SaveTokenLines() -> List[str]:
    """Auth 后置：把 ``accessToken`` 写入四作用域，供后续 ``Bearer {{accessToken}}``。"""
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    var tok = String(t);",
        "    try { pm.variables.set('accessToken', tok); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', tok); } catch (eC) {}",
        "    try { if (pm.environment) pm.environment.set('accessToken', tok); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', tok); } catch (eG) {}",
        "    console.log('[auth] accessToken 已写入 variables/collection/environment/globals');",
        "  }",
        "} catch (e) { console.warn('[auth] 解析 token 失败', e); }",
    ]


def Lines_SeedAuthFromDataset() -> List[str]:
    """鉴权三列：iterationData → Environment → variables → collection → globals，写回四作用域。"""
    lines: List[str] = [
        "try {",
    ]
    for key in ("ProgramID", "clientId", "secret"):
        lines.extend(
            [
                "  (function () {",
                f"    var _k = '{key}';",
                "    var _id = ''; try { if (pm.iterationData) _id = String(pm.iterationData.get(_k) || '').trim(); } catch (eI) {}",
                "    var _e = ''; try { _e = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (eE) {}",
                "    var _v = ''; try { _v = String(pm.variables.get(_k) || '').trim(); } catch (eV) {}",
                "    var _c = ''; try { _c = String(pm.collectionVariables.get(_k) || '').trim(); } catch (eC) {}",
                "    var _g = ''; try { _g = String((pm.globals && pm.globals.get(_k)) || '').trim(); } catch (eG) {}",
                "    var _pick = _id || _e || _v || _c || _g;",
                "    var _src = _id ? 'iterationData' : (_e ? 'environment' : (_v ? 'variables' : (_c ? 'collection' : (_g ? 'globals' : ''))));",
                "    if (_pick && _pick.indexOf('{{') < 0) {",
                "      try { pm.variables.set(_k, _pick); } catch (e1) {}",
                "      try { pm.collectionVariables.set(_k, _pick); } catch (e2) {}",
                "      try { if (pm.environment) pm.environment.set(_k, _pick); } catch (e3) {}",
                "      try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(_k, _pick); } catch (e4) {}",
                "      if (_k === 'ProgramID') {",
                "        console.log('[auth-seed] ProgramID=' + _pick + ' source=' + _src);",
                "      }",
                "    } else if (_k === 'ProgramID') {",
                "      console.warn('[auth-seed] 未取到 ProgramID：请勾选场景数据集行（列名 ProgramID/clientId/secret）');",
                "    }",
                "  })();",
            ]
        )
    lines.append("} catch (eSeed) { console.warn('[auth-seed] 失败', eSeed); }")
    return lines


def Lines_EnsureBearerAndProgramId() -> List[str]:
    """业务步：把已持久化的 ProgramID / accessToken 写回头，避免 ``{{}}`` 未展开或 Environment 旧值。"""
    return [
        "try {",
        "  var _pid = '';",
        "  try { if (pm.iterationData) _pid = String(pm.iterationData.get('ProgramID') || '').trim(); } catch (eI) {}",
        "  if (!_pid || _pid.indexOf('{{') >= 0) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eE) {} }",
        "  if (!_pid || _pid.indexOf('{{') >= 0) { try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eV) {} }",
        "  if (!_pid || _pid.indexOf('{{') >= 0) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eC) {} }",
        "  var _tok = '';",
        "  try { _tok = String(pm.variables.get('accessToken') || '').trim(); } catch (e0) {}",
        "  if (!_tok || _tok.indexOf('{{') >= 0) { try { _tok = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e1) {} }",
        "  if (!_tok || _tok.indexOf('{{') >= 0) { try { _tok = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e2) {} }",
        "  if (!_tok || _tok.indexOf('{{') >= 0) { try { _tok = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (e3) {} }",
        "  if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "    if (_pid && _pid.indexOf('{{') < 0) {",
        "      pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid });",
        "    }",
        "    if (_tok && _tok.indexOf('{{') < 0) {",
        "      pm.request.headers.upsert({ key: 'Authorization', value: 'Bearer ' + _tok });",
        "    }",
        "  }",
        "  if (!_tok || _tok.indexOf('{{') >= 0) {",
        "    console.warn('[auth-header] accessToken 为空：请先跑 00 Auth');",
        "  }",
        "} catch (eAuthH) { console.warn('[auth-header]', eAuthH); }",
    ]


def MakeTestEvent(
    js_helpers: Callable[[], List[str]],
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(js_helpers())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def MakePreRequestEvent(
    js_helpers: Callable[[], List[str]],
    lines: Sequence[str],
) -> List[JsonObject]:
    exec_lines: List[str] = []
    exec_lines.extend(js_helpers())
    exec_lines.extend(list(lines))
    return [{"listen": "prerequest", "script": {"exec": exec_lines, "type": "text/javascript"}}]


def Lines_EnsureRequestIdHeader() -> List[str]:
    """发送前写入合法 ``X-Request-ID``（兼补 ``Accept``）。

    Apifox 单步调试 / CLI 场景常不展开头里的 ``{{$guid}}``，发出空头会触发
    ``301.000.001``（The field X-Request-ID contains invalid characters or format is incorrect）。
    策略与 PAPI-2515 ``p2515FreshRequestIdForSend`` 一致：先试 ``replaceIn``，失败则本地 UUID。
    """
    return [
        "try {",
        "  var _rid = '';",
        "  try {",
        "    if (pm.variables && typeof pm.variables.replaceIn === 'function') {",
        "      _rid = String(pm.variables.replaceIn('{{$guid}}') || '');",
        "    }",
        "  } catch (eR0) {}",
        "  if (!_rid || _rid.indexOf('{{') >= 0 || _rid.indexOf('}}') >= 0) {",
        "    _rid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {",
        "      var r = (Math.random() * 16) | 0;",
        "      var v = c === 'x' ? r : (r & 0x3) | 0x8;",
        "      return v.toString(16);",
        "    });",
        "  }",
        "  if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "    pm.request.headers.upsert({ key: 'X-Request-ID', value: _rid });",
        "    pm.request.headers.upsert({ key: 'Accept', value: '*/*' });",
        "  }",
        "} catch (eRid) {}",
    ]


def JsExpr_FreshRequestId() -> str:
    """可嵌入 helpers / ``pm.sendRequest`` 头的 IIFE：返回合法 UUID（不依赖 ``{{$guid}}`` 展开）。"""
    return (
        "(function () {"
        "  var r = '';"
        "  try {"
        "    if (pm.variables && typeof pm.variables.replaceIn === 'function') {"
        "      r = String(pm.variables.replaceIn('{{$guid}}') || '');"
        "    }"
        "  } catch (e) {}"
        "  if (!r || r.indexOf('{{') >= 0 || r.indexOf('}}') >= 0) {"
        "    r = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {"
        "      var n = (Math.random() * 16) | 0;"
        "      var v = c === 'x' ? n : (n & 0x3) | 0x8;"
        "      return v.toString(16);"
        "    });"
        "  }"
        "  return r;"
        "})()"
    )


def AuthJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def PostmanUrl(url_path: str, query: Optional[Dict[str, str]] = None) -> JsonObject:
    """构建 Postman URL；支持 ``url.query``（Apifox/Postman 才会带上 module 等参数）。"""
    path_only = url_path.split("?", 1)[0]
    merged_query: Dict[str, str] = {}
    if "?" in url_path:
        for part in url_path.split("?", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                merged_query[key] = value
    if query:
        merged_query.update({str(k): str(v) for k, v in query.items()})
    path_parts: List[str] = [part for part in path_only.split("/") if part]
    raw = "{{baseUrl}}/" + "/".join(path_parts)
    url_obj: JsonObject = {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}
    if merged_query:
        url_obj["query"] = [{"key": k, "value": v} for k, v in merged_query.items()]
        url_obj["raw"] = raw + "?" + "&".join(f"{k}={v}" for k, v in merged_query.items())
    return url_obj


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str, description: str = "") -> JsonObject:
    item: JsonObject = {"key": key, "value": value, "type": "string"}
    if description:
        item["description"] = description
    return item


def RequestItem(
    *,
    js_helpers: Callable[[], List[str]],
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    test_lines: Optional[Sequence[str]] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
    helpers_source_key: str = "",
) -> JsonObject:
    """构建一步 HTTP。``helpers_source_key`` 非空时：Auth 内联并写入该变量，其它步 eval loader。"""
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)
    out: JsonObject = {"name": name, "request": req}
    events: List[JsonObject] = []
    source_key = str(helpers_source_key or "").strip()
    helper_src = "\n".join(js_helpers())
    if source_key:
        if save_token:
            helper_pre = list(js_helpers())
            helper_post = Lines_ExportHelpersSource(source_key, helper_src)
        else:
            helper_pre = Lines_LoadHelpersSource(source_key)
            helper_post = Lines_LoadHelpersSource(source_key)
    else:
        helper_pre = list(js_helpers())
        helper_post = list(js_helpers())
    # 每步必跑：空 X-Request-ID → 301.000.001；后续步不跟选行 → 201.000.001
    pre_merged: List[str] = list(helper_pre)
    pre_merged.extend(Lines_EnsureRequestIdHeader())
    pre_merged.extend(Lines_SeedAuthFromDataset())
    if not save_token:
        pre_merged.extend(Lines_EnsureBearerAndProgramId())
    if prerequest_lines:
        pre_merged.extend(list(prerequest_lines))
    events.append(
        {"listen": "prerequest", "script": {"exec": pre_merged, "type": "text/javascript"}}
    )
    test_exec: List[str] = list(helper_post)
    if save_token:
        test_exec.extend(SaveTokenLines())
    if test_lines:
        test_exec.extend(list(test_lines))
    events.append({"listen": "test", "script": {"exec": test_exec, "type": "text/javascript"}})
    out["event"] = events
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def Lines_Step(_label: str, fn_calls: Sequence[str]) -> List[str]:
    return list(fn_calls)


_DEFAULT_RUNTIME_UNSET_ENV_KEYS: Final[tuple[str, ...]] = (
    "clientUserId",
    "ePassId",
    "purchaseOrderId",
    "usageOrderId",
    "prebookingToken",
    "membershipId",
    "prebookingDate",
)


def JsRuntimeVarScopeHelpersBlock(
    *,
    prefix: str,
    extra_unset_env_keys: Sequence[str] = (),
) -> str:
    """``{prefix}SetVar`` / ``UnsetVar`` / ``GetVar``：运行时 ID 写 variables+collection，并 ``unset`` 共用 Environment。"""
    keys = list(_DEFAULT_RUNTIME_UNSET_ENV_KEYS) + list(extra_unset_env_keys)
    unset_entries = ",\n    ".join(f"{k}: 1" for k in keys)
    p = prefix
    return rf"""function {p}SetVar(key, value) {{
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
  var unsetEnv = {{
    {unset_entries}
  }};
  if (unsetEnv[key]) {{
    try {{ if (pm.environment && typeof pm.environment.unset === 'function') pm.environment.unset(key); }} catch (e2) {{}}
    try {{ if (pm.globals && typeof pm.globals.unset === 'function') pm.globals.unset(key); }} catch (e3) {{}}
  }}
}}
function {p}UnsetVar(key) {{
  try {{ pm.variables.unset(key); }} catch (e0) {{}}
  try {{ pm.collectionVariables.unset(key); }} catch (e1) {{}}
}}
function {p}GetVar(key) {{
  var v = '';
  try {{ if (pm.iterationData) v = String(pm.iterationData.get(key) || '').trim(); }} catch (eId) {{}}
  if (!v || v.indexOf('{{{{') >= 0) {{ try {{ v = String(pm.variables.get(key) || '').trim(); }} catch (e0) {{}} }}
  if (!v || v.indexOf('{{{{') >= 0) {{ try {{ v = String(pm.collectionVariables.get(key) || '').trim(); }} catch (e1) {{}} }}
  if (!v || v.indexOf('{{{{') >= 0) return '';
  return v;
}}
"""


def JsRuntimeClientUserIdCaptureHelpersBlock(
    *,
    prefix: str,
    variable_prefix: Optional[str] = None,
) -> str:
    """仅生成 ``clientUserId`` 捕获函数；函数名前缀与变量作用域函数前缀可解耦。

    捕获优先 **响应**（``fromResp || fromReq``）：后续步必须用注册/创建接口返回值，
    不能用请求体或 Environment 里的旧 UUID。
    """
    p = prefix
    variable_p = variable_prefix or prefix
    return rf"""function {p}IsUnresolvedPlaceholder(s) {{
  var t = String(s == null ? '' : s).trim();
  return !t || t.indexOf('{{{{') >= 0 || t.indexOf('}}}}') >= 0;
}}
function {p}IsUuid(s) {{
  return /^[0-9a-fA-F]{{8}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{4}}-[0-9a-fA-F]{{12}}$/.test(String(s || ''));
}}
function {p}ReadSentClientUserId() {{
  try {{
    var raw = pm.request && pm.request.body && pm.request.body.raw;
    if (!raw) return '';
    var body = JSON.parse(String(raw));
    var cid = '';
    if (body && body.clientUserId != null) cid = String(body.clientUserId).trim();
    else if (body && body.profile && body.profile.clientUserId != null) {{
      cid = String(body.profile.clientUserId).trim();
    }}
    if ({p}IsUnresolvedPlaceholder(cid)) return '';
    return cid;
  }} catch (eSent) {{
    return '';
  }}
}}
function {p}CaptureClientUserIdAfterSend(data) {{
  var fromResp = '';
  if (data && data.clientUserId != null) fromResp = String(data.clientUserId).trim();
  if ({p}IsUnresolvedPlaceholder(fromResp) && data && data.extra && data.extra.clientUserId != null) {{
    fromResp = String(data.extra.clientUserId).trim();
  }}
  if ({p}IsUnresolvedPlaceholder(fromResp)) fromResp = '';
  var fromReq = {p}ReadSentClientUserId();
  var captured = fromResp || fromReq;
  if (captured) {variable_p}SetVar('clientUserId', captured);
  return captured;
}}
"""


def JsRuntimeIdCaptureHelpersBlock(
    *,
    prefix: str,
    variable_prefix: Optional[str] = None,
) -> str:
    """生成 runtime ID 捕获与请求体回填；默认变量作用域函数与公开函数同前缀。

    后续步必须 **强制** 用上一步捕获的 ``membershipId`` / ``clientUserId`` / ``ePassId``
    （覆盖 Environment 旧值、OAS 样例字面量）。``{{$string.uuid}}`` 注册步不覆盖。
    负向「伪造 ID」须在本函数 **之后** 再写回假值。
    """
    p = prefix
    variable_p = variable_prefix or prefix
    capture_helpers = JsRuntimeClientUserIdCaptureHelpersBlock(
        prefix=p,
        variable_prefix=variable_p,
    )
    apply_helpers = rf"""function {p}ApplyRuntimeIdsToRequestBody() {{
  try {{
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var raw = String(pm.request.body.raw);
    function subst(name) {{
      var val = {variable_p}GetVar(name);
      if (!val) return;
      var token = '{{{{' + name + '}}}}';
      while (raw.indexOf(token) >= 0) {{
        raw = raw.split(token).join(val);
      }}
    }}
    subst('clientUserId');
    subst('ePassId');
    subst('purchaseOrderId');
    subst('usageOrderId');
    subst('prebookingToken');
    subst('membershipId');
    var body = JSON.parse(raw);
    function forceCaptured(field, varName) {{
      if (!body || !Object.prototype.hasOwnProperty.call(body, field)) return;
      var cur = body[field];
      var s = cur == null ? '' : String(cur);
      if (s.indexOf('$string.uuid') >= 0 || s.indexOf('$guid') >= 0) return;
      var val = {variable_p}GetVar(varName);
      if (val) body[field] = val;
    }}
    forceCaptured('clientUserId', 'clientUserId');
    forceCaptured('ePassId', 'ePassId');
    forceCaptured('prebookingToken', 'prebookingToken');
    forceCaptured('membershipId', 'membershipId');
    if (body && Object.prototype.hasOwnProperty.call(body, 'orderId')) {{
      var oid = body.orderId;
      if ({p}IsUnresolvedPlaceholder(oid) || !String(oid || '').trim()) {{
        var filledOid = '';
        if (String(pm.request.body.raw).indexOf('usageOrderId') >= 0) filledOid = {variable_p}GetVar('usageOrderId');
        else if (String(pm.request.body.raw).indexOf('purchaseOrderId') >= 0) filledOid = {variable_p}GetVar('purchaseOrderId');
        if (filledOid) body.orderId = filledOid;
      }}
    }}
    pm.request.body.raw = JSON.stringify(body, null, 2);
  }} catch (eApplyIds) {{
    console.warn('{p}ApplyRuntimeIdsToRequestBody:', eApplyIds);
  }}
}}
"""
    return capture_helpers + apply_helpers


def JsAssertClientUserIdEchoBlock(*, prefix: str) -> str:
    """创建 ePass 后置：先提取 ``clientUserId``，再断言 UUID 回显。"""
    p = prefix
    return rf"""  {p}SaveCreateIds(dataFn());
  pm.test(label + ': clientUserId 回显一致', function () {{
    var actual = dataFn().clientUserId;
    var saved = {p}GetVar('clientUserId');
    pm.expect(actual, '响应 clientUserId').to.be.a('string').and.not.empty;
    pm.expect({p}IsUnresolvedPlaceholder(actual), '响应不是未解析模板').to.be.false;
    pm.expect({p}IsUuid(actual), '响应 clientUserId 为 UUID').to.be.true;
    pm.expect(saved, '后置已提取 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(actual).to.eql(saved);
  }});"""


def Prerequest_ApplyRuntimeIds(prefix: str) -> List[str]:
    return [f"{prefix}ApplyRuntimeIdsToRequestBody();"]


def Prerequest_UnsetClientUserId(prefix: str) -> List[str]:
    return [f"{prefix}UnsetVar('clientUserId');"]


def WrapRequestItemWithRuntimeIds(
    *,
    prefix: str,
    base_request_item: Callable[..., JsonObject],
) -> Callable[..., JsonObject]:
    """每步前置把后置提取的 runtime id 写进 body（``{{clientUserId}}`` 等跨步常不展开）。"""

    def Wrapped(**kwargs: Any) -> JsonObject:
        existing: List[str] = list(kwargs.get("prerequest_lines") or [])
        kwargs["prerequest_lines"] = existing + Prerequest_ApplyRuntimeIds(prefix)
        return base_request_item(**kwargs)

    return Wrapped


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    """
    Apifox/Postman 列表展示名：业务目的前置，便于在自动化场景中识别每条请求验证什么。

    格式：``【目的】| 步骤号 | METHOD 路径简写``
    """
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def WriteCollectionJson(out_path: Union[str, Path], payload: JsonObject) -> None:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
