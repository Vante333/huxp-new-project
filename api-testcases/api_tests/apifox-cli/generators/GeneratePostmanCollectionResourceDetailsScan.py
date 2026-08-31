"""
生成 Resource Details 全量扫描 Postman Collection v2.1 JSON（Apifox CLI · Repo-first）。

编排（品类 → 语种子夹）::

1. ``POST /auth/token``（写入 helpers 到 ``rdHelpersSource``）
2. 顶层 **8 品类夹** → 语种子夹（名=``en-US`` 等字面量）
3. 语种内：Auth 续期（可选）→ LIST（page1 + sendRequest 余页）→
   资源 forEach → DETAIL（``fallbackAllowed=false`` / ``code=0``）

下游步骤 ``eval(rdHelpersSource)``，避免 helpers 撑爆包体。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionResourceDetailsScan.py
"""
from __future__ import annotations

import json
import os
from typing import Dict, Final, List, Optional, Sequence

from collection_builder_common import (
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionPath,
    CollectionVariable,
    EnvPath,
    Folder,
    JsExpr_FreshRequestId,
    Lines_EnsureRequestIdHeader,
    Lines_Step,
    POSTMAN_SCHEMA,
    PostmanJsonRawBody,
    PostmanUrl,
    PurposeName,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = "Resource Details · 全量扫描（语种×列表×详情 code=0）"
OUT_NAME: Final[str] = "Resource-Details-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-Details-Scan-sandbox.postman_environment.json"

ALL_MODULES: Final[tuple[int, ...]] = (1, 2, 3, 4, 6, 7, 8, 11)
_DEFAULT_SCAN_LANGUAGES_FULL: Final[List[str]] = [
    "en-US",
    "zh-CN",
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
    "ko-KR",
    "es-419",
    "fr-CA",
    "ar-SA",
    "ro-RO",
    "bs-BA",
    "sr-SP",
    "sr-ME",
    "hr-HR",
    "nl-NL",
    "el-GR",
    "si-SI",
    "he-IL",
    "hu-HU",
]
# 冒烟：RD_SCAN_SMOKE=1 时仅展开 en-US + zh-CN，跑完须无该变量再 Generate+Push 恢复全量。
DEFAULT_SCAN_LANGUAGES: Final[List[str]] = (
    ["en-US", "zh-CN"]
    if os.environ.get("RD_SCAN_SMOKE", "").strip() == "1"
    else list(_DEFAULT_SCAN_LANGUAGES_FULL)
)
DEFAULT_SCAN_LANGUAGES_JSON: Final[str] = json.dumps(
    DEFAULT_SCAN_LANGUAGES, ensure_ascii=False, separators=(",", ":")
)

MODULE_LABEL: Final[Dict[int, str]] = {
    1: "Lounge",
    2: "FastTrack",
    3: "Set Meal",
    4: "Dining",
    6: "Fitness",
    7: "eSIM",
    8: "Fitness/eSIM 变体",
    11: "Local Offer",
}

# Auth 续期粒度：language（全量推荐）| module | none
_AUTH_REFRESH_SCOPE_RAW: Final[str] = (
    os.environ.get("RD_AUTH_REFRESH_SCOPE", "language").strip().lower() or "language"
)
AUTH_REFRESH_SCOPE: Final[str] = (
    _AUTH_REFRESH_SCOPE_RAW
    if _AUTH_REFRESH_SCOPE_RAW in ("language", "module", "none")
    else "language"
)


def _IdsVar(module: int) -> str:
    return f"scanResourceIdsM{module}"


def _LangSafe(lang: str) -> str:
    return lang.replace("-", "_").replace(".", "_")


def _ResourceForEachFolderName(module: int, lang: str) -> str:
    safe = _LangSafe(lang)
    return f"FOR_EACH | {_IdsVar(module)} | as={_IdsVar(module)}_{safe} | {lang} resourceId"


def _ResourceForEachAs(module: int, lang: str) -> str:
    return f"{_IdsVar(module)}_{_LangSafe(lang)}"


def BuildResourceDetailsScanJsHelpersSource() -> str:
    """供 Auth 写入 ``rdHelpersSource``，下游步骤 eval 加载。"""
    default_langs_js = DEFAULT_SCAN_LANGUAGES_JSON
    fresh_rid = JsExpr_FreshRequestId()
    return rf"""
var RD_DEFAULT_SCAN_LANGUAGES = {default_langs_js};
function rdIsCodeZero(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}}
function rdGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}}
function rdVarGet(key) {{
  var v;
  try {{
    if (pm.variables && typeof pm.variables.get === 'function') {{
      v = pm.variables.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (eu) {{}}
  try {{
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
      var rx = pm.variables.replaceIn('{{{{' + key + '}}}}');
      if (rx && String(rx).indexOf('{{{{') < 0 && String(rx).trim() !== '') return String(rx).trim();
    }}
  }} catch (er) {{}}
  try {{
    v = pm.collectionVariables.get(key);
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  }} catch (ec) {{}}
  try {{
    if (pm.environment && typeof pm.environment.get === 'function') {{
      v = pm.environment.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (e1) {{}}
  return '';
}}
function rdSetMulti(key, value) {{
  // 只写运行时 + collection：勿写 Environment/globals，避免 scanResourceIdsM* / scanListPagesM* 污染共用环境
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
}}
function rdRequestUrlToString() {{
  try {{
    var u = pm.request && pm.request.url;
    if (!u) return '';
    var raw = '';
    if (typeof u === 'string') raw = u;
    else if (typeof u.toString === 'function') raw = String(u.toString());
    else if (u.raw) raw = String(u.raw);
    if (raw && pm.variables && typeof pm.variables.replaceIn === 'function') {{
      raw = String(pm.variables.replaceIn(raw) || raw);
    }}
    return String(raw).trim();
  }} catch (e) {{ return ''; }}
}}
function rdStripTrailingSlashes(s) {{
  s = String(s || '');
  while (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
  return s;
}}
function rdResolveBaseUrl() {{
  var raw = rdRequestUrlToString();
  if (raw) {{
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {{
      var base = rdStripTrailingSlashes(raw.slice(0, idx));
      if ((base.indexOf('http://') === 0 || base.indexOf('https://') === 0) && base.indexOf('{{{{') < 0) {{
        return base;
      }}
    }}
  }}
  var b = rdVarGet('baseUrl');
  if (b && b.indexOf('{{{{') < 0) return rdStripTrailingSlashes(b);
  return '';
}}
function rdGetPageSize() {{
  var raw = rdVarGet('scanPageSize') || '100';
  if (String(raw).indexOf('{{{{') >= 0) return 100;
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : n;
}}
function rdGetMaxDetails() {{
  var raw = rdVarGet('scanMaxDetails') || '0';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function rdCollectResourceIds(data) {{
  var ids = [];
  var resources = (data && data.resources) || {{}};
  ['transportHubResources', 'lifestyleResources'].forEach(function (key) {{
    var arr = resources[key] || [];
    for (var i = 0; i < arr.length; i++) {{
      var rid = arr[i] && (arr[i].resourceId || arr[i].id);
      if (rid) ids.push(String(rid));
    }}
  }});
  return ids;
}}
function rdUnique(arr) {{
  var seen = {{}};
  var out = [];
  for (var i = 0; i < arr.length; i++) {{
    if (!seen[arr[i]]) {{ seen[arr[i]] = true; out.push(arr[i]); }}
  }}
  return out;
}}
function rdReadIdsVar(module) {{
  var ids = [];
  try {{ ids = JSON.parse(rdVarGet('scanResourceIdsM' + module) || '[]'); }} catch (e0) {{ ids = []; }}
  return Array.isArray(ids) ? ids : [];
}}
function rdParseLanguagesList(raw) {{
  var s = String(raw || '').trim();
  if (!s) return [];
  try {{
    var parsed = JSON.parse(s);
    if (Array.isArray(parsed)) {{
      return parsed.map(function (x) {{ return String(x || '').trim(); }}).filter(Boolean);
    }}
  }} catch (eJson) {{}}
  return s.split(/[,;\\s]+/).map(function (x) {{ return String(x || '').trim(); }}).filter(Boolean);
}}
function rdEnsureScanLanguages() {{
  var langs = rdParseLanguagesList(rdVarGet('scanLanguages'));
  var legacySingleEn = langs.length === 1 && String(langs[0]).toLowerCase() === 'en-us';
  if (!langs.length || legacySingleEn) {{
    langs = Array.isArray(RD_DEFAULT_SCAN_LANGUAGES) ? RD_DEFAULT_SCAN_LANGUAGES.slice() : ['en-US'];
  }}
  var json = JSON.stringify(langs);
  rdSetMulti('scanLanguages', json);
  console.log('[scanLanguages] 套件语种共 ' + langs.length + ' 个（语种子夹名=字面量）');
  for (var li = 0; li < langs.length; li++) {{
    console.log('[scanLanguages]   ' + (li + 1) + '/' + langs.length + '  ' + langs[li]);
  }}
  return langs;
}}
function rdForEachElement(stepIdSuffix) {{
  var keys = [
    '$.foreach-' + stepIdSuffix + '.element',
    '$.' + stepIdSuffix + '.element'
  ];
  for (var i = 0; i < keys.length; i++) {{
    try {{
      var v = pm.variables.get(keys[i]);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }} catch (e0) {{}}
    try {{
      if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
        var rx = String(pm.variables.replaceIn('{{{{' + keys[i] + '}}}}') || '').trim();
        if (rx && rx.indexOf('{{{{') < 0) return rx;
      }}
    }} catch (e1) {{}}
  }}
  return '';
}}
function rdFinalizeResourceIds(module) {{
  var ids = rdUnique(rdReadIdsVar(module));
  var maxDetails = rdGetMaxDetails();
  if (maxDetails > 0) ids = ids.slice(0, maxDetails);
  rdSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
  rdSetMulti('scanDetailCallM' + module, '0');
  var lang = rdVarGet('scanCurrentLanguage') || '';
  console.log('[LIST finalize] module=' + module + ' language=' + lang + ' count=' + ids.length
    + (maxDetails > 0 ? ' (scanMaxDetails=' + maxDetails + ')' : ''));
  if (ids.length) console.log('[LIST finalize] sample resourceId=' + ids[0]);
  return ids;
}}
function rdBindListPageUrl(module, pageNumber) {{
  var page = parseInt(String(pageNumber || '1'), 10);
  if (isNaN(page) || page < 1) page = 1;
  var pageSize = rdGetPageSize();
  var lang = rdVarGet('scanCurrentLanguage') || 'en-US';
  var base = rdResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[LIST bind] baseUrl missing module=' + module);
    return page;
  }}
  var url = rdStripTrailingSlashes(base) + '/v2/resources?module=' + module
    + '&pageNumber=' + page
    + '&pageSize=' + pageSize
    + '&language=' + encodeURIComponent(lang);
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[LIST bind] rewrite url failed', eU);
  }}
  rdSetMulti('scanCurrentListPage', String(page));
  console.log('[LIST bind] module=' + module + ' language=' + lang
    + ' page=' + page + ' pageSize=' + pageSize);
  return page;
}}
function rdBindListSeedPage(module, label, lang) {{
  lang = String(lang || 'en-US');
  rdSetMulti('scanCurrentLanguage', lang);
  console.log('[LANG] ========== module=' + module + ' 语种=' + lang + ' (' + (label || '') + ') ==========');
  rdBindListPageUrl(module, 1);
}}
function rdParseSendJson(res) {{
  try {{
    if (res && typeof res.json === 'function') {{
      var j = res.json();
      if (j && typeof j === 'object') return j;
    }}
  }} catch (e0) {{}}
  try {{
    var t = '';
    if (res && typeof res.text === 'function') t = String(res.text() || '');
    else if (res && res.body !== undefined) t = String(res.body || '');
    if (t) return JSON.parse(t);
  }} catch (e1) {{}}
  return null;
}}
function rdListSendHeaders() {{
  try {{
    var headers = pm.request && pm.request.headers;
    if (headers) {{
      var list = [];
      if (typeof headers.each === 'function') {{
        headers.each(function (h) {{
          if (!h || !h.key) return;
          var k = String(h.key);
          if (k.toLowerCase() === 'content-length') return;
          list.push({{ key: k, value: String(h.value || '') }});
        }});
      }}
      var hasAuth = false;
      for (var i = 0; i < list.length; i++) {{
        if (String(list[i].key || '').toLowerCase() === 'authorization'
            && String(list[i].value || '').length > 20) {{
          hasAuth = true;
          break;
        }}
      }}
      if (hasAuth && list.length) {{
        var rid = {fresh_rid};
        var replaced = false;
        for (var j = 0; j < list.length; j++) {{
          if (String(list[j].key || '').toLowerCase() === 'x-request-id') {{
            list[j].value = rid;
            replaced = true;
          }}
        }}
        if (!replaced) list.push({{ key: 'X-Request-ID', value: rid }});
        return list;
      }}
    }}
  }} catch (eClone) {{}}
  var tok = rdVarGet('accessToken') || '';
  var pid = rdVarGet('ProgramID') || '';
  var xv = rdVarGet('x-version') || '';
  var out = [
    {{ key: 'Authorization', value: 'Bearer ' + tok }},
    {{ key: 'X-Program-ID', value: String(pid) }},
    {{ key: 'X-Request-ID', value: {fresh_rid} }},
    {{ key: 'Content-Type', value: 'application/json' }},
    {{ key: 'Accept', value: '*/*' }}
  ];
  if (xv && String(xv).toLowerCase() !== 'omit' && String(xv).toLowerCase() !== 'none') {{
    out.splice(2, 0, {{ key: 'x-version', value: String(xv) }});
  }}
  return out;
}}
function rdBuildListPageUrl(module, page) {{
  var pageSize = rdGetPageSize();
  var lang = rdVarGet('scanCurrentLanguage') || 'en-US';
  var base = rdResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  return rdStripTrailingSlashes(base) + '/v2/resources?module=' + module
    + '&pageNumber=' + page
    + '&pageSize=' + pageSize
    + '&language=' + encodeURIComponent(lang);
}}
function rdSeedListPage1(module) {{
  var langNow = rdVarGet('scanCurrentLanguage') || '';
  var env = {{}};
  try {{ env = pm.response.json(); }} catch (eJ) {{ env = {{}}; }}
  pm.test('LIST-M' + module + ' | language=' + langNow + ' page=1 | 期望=code0 | 实际=响应', function () {{
    pm.expect(rdIsCodeZero(env), 'list page1 code=0').to.eql(true);
  }});
  var data = rdGetInnerData(env) || {{}};
  var ids = rdCollectResourceIds(data);
  var pageSize = rdGetPageSize();
  var pag = data.pagination || {{}};
  var total = parseInt(pag.totalNumber, 10);
  if (isNaN(total)) total = ids.length;
  var totalPages = Math.max(1, Math.ceil(total / pageSize));
  rdSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
  rdSetMulti('scanListTotalPagesM' + module, String(totalPages));
  console.log('[LIST] module=' + module + ' ★language=' + langNow
    + ' page1Ids=' + ids.length + ' totalNumber=' + total
    + ' totalPages=' + totalPages);
  if (totalPages <= 1) {{
    rdFinalizeResourceIds(module);
    return;
  }}
  // page2..N：pm.sendRequest 串行；setInterval 保活避免 Runner 提前进下一步（同 P2515）
  var hold = setInterval(function () {{}}, 5000);
  var page = 2;
  function fetchNext() {{
    if (page > totalPages) {{
      clearInterval(hold);
      rdFinalizeResourceIds(module);
      return;
    }}
    var curPage = page;
    var url = rdBuildListPageUrl(module, curPage);
    pm.sendRequest({{ url: url, method: 'GET', header: rdListSendHeaders() }}, function (err, res) {{
      pm.test('LIST-M' + module + ' | language=' + langNow + ' page=' + curPage
        + ' | 期望=code0+追加ID | 实际=响应', function () {{
        pm.expect(err, 'sendRequest err').to.eql(null);
        var env2 = rdParseSendJson(res) || {{}};
        pm.expect(rdIsCodeZero(env2), 'list page code=0').to.eql(true);
        var more = rdCollectResourceIds(rdGetInnerData(env2) || {{}});
        var cur = rdReadIdsVar(module).concat(more);
        rdSetMulti('scanResourceIdsM' + module, JSON.stringify(cur));
        console.log('[LIST] module=' + module + ' language=' + langNow
          + ' page=' + curPage + ' +' + more.length + ' idsNow=' + cur.length);
      }});
      page = curPage + 1;
      fetchNext();
    }});
  }}
  fetchNext();
}}
function rdAssertDetailCodeZero(module) {{
  var lang = rdVarGet('scanCurrentLanguage') || '';
  var rid = rdVarGet('scanCurrentResourceId') || '';
  pm.test('DETAIL-M' + module + ' | language=' + lang + ' resourceId=' + rid
    + ' | 期望=code0 fallbackAllowed=false | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(env.code, 'code').to.eql(0);
  }});
}}
function rdBindForEachDetail(module, label, lang, foreachAs) {{
  lang = String(lang || 'en-US');
  rdSetMulti('scanCurrentLanguage', lang);
  var rid = '';
  if (foreachAs) rid = rdForEachElement(foreachAs);
  if (!rid) rid = rdForEachElement('scanResourceIdsM' + module);
  var ids = rdReadIdsVar(module);
  if (!rid) {{
    var callIdx = parseInt(rdVarGet('scanDetailCallM' + module) || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (ids[callIdx] !== undefined) rid = String(ids[callIdx]);
    rdSetMulti('scanDetailCallM' + module, String(callIdx + 1));
  }}
  rdSetMulti('scanCurrentResourceId', rid || '');
  if (!rid) {{
    console.error('[DETAIL bind] module=' + module + ' 仍无 resourceId language=' + lang);
    return;
  }}
  var base = rdResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[DETAIL bind] baseUrl missing');
    return;
  }}
  var url = rdStripTrailingSlashes(base) + '/v2/resources/' + encodeURIComponent(rid)
    + '?module=' + module
    + '&language=' + encodeURIComponent(lang)
    + '&fallbackAllowed=false';
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[DETAIL bind] rewrite url failed', eU);
  }}
  console.log('[DETAIL] module=' + module + ' ★language=' + lang + ' resourceId=' + rid);
}}
""".strip()


def _HelpersLines() -> List[str]:
    return BuildResourceDetailsScanJsHelpersSource().split("\n")


def _LoadHelpersLines() -> List[str]:
    return [
        "try {",
        "  var _src = '';",
        "  try { _src = String(pm.collectionVariables.get('rdHelpersSource') || ''); } catch (e0) {}",
        "  if (!_src) { try { _src = String(pm.variables.get('rdHelpersSource') || ''); } catch (e1) {} }",
        "  if (_src) { eval(_src); }",
        "  else { console.error('[rdHelpers] rdHelpersSource 为空：请先跑 Auth'); }",
        "} catch (eLoad) { console.error('[rdHelpers] load failed', eLoad); }",
    ]


def _RdRequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    headers: List[JsonObject],
    description: str,
    body: Optional[str] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
    test_lines: Optional[Sequence[str]] = None,
    embed_full_helpers: bool = False,
    load_helpers: bool = True,
) -> JsonObject:
    """业务步骤默认只 loader+调用；首次 Auth 嵌入完整 helpers；续期可不加载 helpers。"""
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

    pre: List[str] = []
    if embed_full_helpers:
        pre.extend(_HelpersLines())
    elif load_helpers:
        pre.extend(_LoadHelpersLines())
    pre.extend(Lines_EnsureRequestIdHeader())
    if prerequest_lines:
        pre.extend(list(prerequest_lines))
    events.append({"listen": "prerequest", "script": {"exec": pre, "type": "text/javascript"}})

    post: List[str] = []
    if embed_full_helpers:
        post.extend(_HelpersLines())
    elif load_helpers:
        post.extend(_LoadHelpersLines())
    if test_lines:
        post.extend(list(test_lines))
    events.append({"listen": "test", "script": {"exec": post, "type": "text/javascript"}})
    out["event"] = events
    return out


def _SaveAccessTokenLines() -> List[str]:
    """Auth / Auth-Refresh 共用：四作用域写入 accessToken。"""
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    try { pm.variables.set('accessToken', t); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', t); } catch (eC) {}",
        "    try { if (pm.environment) pm.environment.set('accessToken', t); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', t); } catch (eG) {}",
        "  }",
        "} catch (e) { console.warn(e); }",
    ]


def _AuthAssertTokenLines(label: str) -> List[str]:
    return [
        f"pm.test('{label}: HTTP 200', function () {{ pm.response.to.have.status(200); }});",
        f"pm.test('{label}: accessToken 已写入运行时', function () {{",
        "  var a = ''; try { a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var b = ''; try { b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  pm.expect(a || b, 'accessToken').to.be.ok;",
        "});",
    ]


def _AuthStep() -> JsonObject:
    helpers_src = BuildResourceDetailsScanJsHelpersSource()
    export = (
        "try { pm.collectionVariables.set('rdHelpersSource', "
        + json.dumps(helpers_src, ensure_ascii=False)
        + "); } catch (eH) { console.warn(eH); }"
    )
    save_lines = [
        *_SaveAccessTokenLines(),
        export,
        "rdEnsureScanLanguages();",
        *_AuthAssertTokenLines("Auth"),
        "pm.test('Auth: rdHelpersSource 已写入', function () {",
        "  var s = ''; try { s = String(pm.collectionVariables.get('rdHelpersSource') || ''); } catch (e0) {}",
        "  pm.expect(s.length > 100, 'rdHelpersSource').to.eql(true);",
        "});",
    ]
    return _RdRequestItem(
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        headers=AuthJsonHeaders(),
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        description="写入 accessToken + rdHelpersSource；语种子夹名含语种字面量。",
        embed_full_helpers=True,
        prerequest_lines=[],
        test_lines=Lines_Step("Auth", save_lines),
    )


def _AuthRefreshStep(*, step_id: str, purpose_suffix: str = "") -> JsonObject:
    """仅续期 accessToken（不重写 rdHelpersSource），避免长跑 token 约 55 分钟过期。"""
    purpose = "鉴权续期 accessToken" + (f"（{purpose_suffix}）" if purpose_suffix else "")
    save_lines = [
        *_SaveAccessTokenLines(),
        *_AuthAssertTokenLines(step_id),
    ]
    return _RdRequestItem(
        name=PurposeName(purpose, step_id, "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        headers=AuthJsonHeaders(),
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        description=(
            "续期 accessToken（四作用域写入）；不改写 rdHelpersSource。"
            f"续期粒度 AUTH_REFRESH_SCOPE={AUTH_REFRESH_SCOPE}。"
        ),
        embed_full_helpers=False,
        load_helpers=False,
        prerequest_lines=[],
        test_lines=Lines_Step(step_id, save_lines),
    )


def _ListSeedStep(module: int, lang: str) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    return _RdRequestItem(
        name=PurposeName(
            f"{label} {lang} 列表全量",
            f"LIST-M{module}-{lang}",
            "GET",
            f"/resources?module={module}&language={lang}",
        ),
        method="GET",
        url_path=f"/v2/resources?module={module}&pageNumber=1&pageSize=100&language={lang}",
        headers=BearerJsonHeaders(),
        description=(
            f"语种 {lang}：page1 + sendRequest 余页 → `{_IdsVar(module)}`。"
        ),
        prerequest_lines=[
            f"rdBindListSeedPage({module}, {json.dumps(label, ensure_ascii=False)}, {json.dumps(lang)});"
        ],
        test_lines=[f"rdSeedListPage1({module});"],
    )


def _DetailStep(module: int, lang: str) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    foreach_as = _ResourceForEachAs(module, lang)
    return _RdRequestItem(
        name=PurposeName(
            f"详情 {lang} code=0 fallbackAllowed=false",
            f"DETAIL-M{module}-{lang}",
            "GET",
            f"/resources/{{id}}?language={lang}&fallbackAllowed=false",
        ),
        method="GET",
        url_path=(
            f"/v2/resources/{{{{scanCurrentResourceId}}}}"
            f"?module={module}&language={lang}&fallbackAllowed=false"
        ),
        headers=BearerJsonHeaders(),
        description=f"语种 {lang} 详情；fallbackAllowed=false；断言 code=0。",
        prerequest_lines=[
            "rdBindForEachDetail("
            f"{module}, {json.dumps(label, ensure_ascii=False)}, {json.dumps(lang)}, "
            f"{json.dumps(foreach_as)});"
        ],
        test_lines=[f"rdAssertDetailCodeZero({module});"],
    )


def _LanguageFolder(module: int, lang: str) -> JsonObject:
    """品类下语种子夹（名=语种字面量）。"""
    items: List[JsonObject] = []
    if AUTH_REFRESH_SCOPE == "language":
        items.append(
            _AuthRefreshStep(
                step_id=f"Auth-Refresh-M{module}-{lang}",
                purpose_suffix=f"M{module}/{lang}",
            )
        )
    items.extend(
        [
            _ListSeedStep(module, lang),
            Folder(
                _ResourceForEachFolderName(module, lang),
                [_DetailStep(module, lang)],
                description=f"{lang} 资源详情 forEach；fallbackAllowed=false。",
            ),
        ]
    )
    return Folder(
        lang,
        items,
        description=(
            f"module={module} / language={lang}：列表全量 → 详情"
            + ("；语种前 Auth 续期。" if AUTH_REFRESH_SCOPE == "language" else "。")
        ),
    )


def _ModuleGroup(module: int) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    items: List[JsonObject] = []
    if AUTH_REFRESH_SCOPE == "module":
        items.append(
            _AuthRefreshStep(
                step_id=f"Auth-Refresh-M{module}",
                purpose_suffix=f"M{module}/{label}",
            )
        )
    items.extend([_LanguageFolder(module, lang) for lang in DEFAULT_SCAN_LANGUAGES])
    refresh_note = {
        "language": "每语种前 Auth 续期；",
        "module": "品类前 Auth 续期；",
        "none": "无中途续期；",
    }.get(AUTH_REFRESH_SCOPE, "")
    return Folder(
        label,
        items,
        description=(
            f"module={module}：语种子夹（名=字面量）；"
            f"{refresh_note}"
            "LIST 内联翻页 + 资源详情 forEach。"
        ),
    )


def BuildCollection() -> JsonObject:
    refresh_desc = {
        "language": "各语种子夹前 **Auth-Refresh** → ",
        "module": "各品类前 **Auth-Refresh** → ",
        "none": "",
    }.get(AUTH_REFRESH_SCOPE, "")
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": (
                "由 GeneratePostmanCollectionResourceDetailsScan.py 生成。\n\n"
                "**编排**：Auth → **8 品类夹** → 语种子夹（en-US 等）→ "
                f"{refresh_desc}"
                "LIST（page1 + sendRequest 余页）→ 资源 forEach → DETAIL "
                "(`fallbackAllowed=false` / `code=0`)。\n\n"
                "**Auth 续期**：`RD_AUTH_REFRESH_SCOPE=language|module|none`（默认 language）。\n"
                "**Environment**：`scanPageSize`、`scanMaxDetails`（0=全量）。\n"
                f"**语种（{len(DEFAULT_SCAN_LANGUAGES)}）**：改生成器常量后重新 Generate+Push。"
            ),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth（token + rdHelpersSource）。"),
            *[_ModuleGroup(m) for m in ALL_MODULES],
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("scanPageSize", "100"),
            CollectionVariable("scanMaxDetails", "0"),
            CollectionVariable("scanLanguage", "en-US"),
            CollectionVariable(
                "scanLanguages",
                DEFAULT_SCAN_LANGUAGES_JSON,
                description="文档用；场景按生成器常量展开语种子夹",
            ),
            CollectionVariable("scanCurrentLanguage", "en-US"),
            CollectionVariable("rdHelpersSource", ""),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    return {
        "id": "resource-details-scan-sandbox-env",
        "name": "Resource Details Scan sandbox（DP_MEMBERSHIP_*）",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
            {"key": "scanPageSize", "value": "100", "enabled": True},
            {"key": "scanMaxDetails", "value": "0", "enabled": True},
            {"key": "scanLanguage", "value": "en-US", "enabled": True},
            {"key": "scanLanguages", "value": DEFAULT_SCAN_LANGUAGES_JSON, "enabled": True},
            {"key": "scanCurrentLanguage", "value": "en-US", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionResourceDetailsScan.py",
    }


def Main() -> None:
    collection = BuildCollection()
    out_path = CollectionPath(OUT_NAME)
    env_path = EnvPath(ENV_OUT_NAME)
    WriteCollectionJson(out_path, collection)
    WriteCollectionJson(env_path, BuildEnvironmentJson())
    print("Wrote", out_path)
    print("Wrote", env_path)
    n_lang = len(DEFAULT_SCAN_LANGUAGES)
    n_mod = len(ALL_MODULES)
    n_refresh = (
        n_mod * n_lang
        if AUTH_REFRESH_SCOPE == "language"
        else (n_mod if AUTH_REFRESH_SCOPE == "module" else 0)
    )
    print(
        f"modules={n_mod} languages={n_lang}(language folders) "
        f"auth_refresh_scope={AUTH_REFRESH_SCOPE} "
        f"http_leaves≈{1 + n_refresh + n_mod * n_lang * 2} (LIST+DETAIL; pages via sendRequest)"
    )


if __name__ == "__main__":
    Main()
