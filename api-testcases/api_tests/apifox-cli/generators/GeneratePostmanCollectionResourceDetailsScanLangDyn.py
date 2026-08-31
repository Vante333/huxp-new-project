"""
生成 Resource Details · 语种 forEach 列表 + 单层资源 forEach Postman Collection v2.1。

与 ``GeneratePostmanCollectionResourceDetailsScan.py``（语种子夹静态展开）并存，互不覆盖。

编排（**不要语种子夹**；语种为 Apifox ForEach 列表，形如「ForEach 循环 ["en-US",…] 中的元素」）::

1. ``POST /auth/token``（写入 ``rdlHelpersSource``；规范化 ``scanLanguages``）
2. 顶层 **8 品类夹** → ``FOR_EACH | scanLanguages | as=scanLanguagesM{{N}}``
3. 语种循环内：Auth 续期（可选）→ LIST（**仅 page1** → ``scanResourceIdsM{{N}}``）
   → ``FOR_EACH`` 资源 → DETAIL（``fallbackAllowed=false`` / ``code=0``）

**动态选语种（B · Environment）**：改 Environment ``scanLanguages`` JSON 数组即可
（例 ``["fr-FR"]`` / ``["en-US","zh-CN"]`` / 全量 27）；Auth 仅在空时回落生成器默认，
**不会**把单语种自动扩成全量。

注意：若私有化 Apifox 嵌套 forEach 出现「轮次 (0)」，请反馈；静态版改用语种子夹可规避。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionResourceDetailsScanLangDyn.py
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
    Lines_EnsureRequestIdHeader,
    Lines_Step,
    POSTMAN_SCHEMA,
    PostmanJsonRawBody,
    PostmanUrl,
    PurposeName,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = (
    "Resource Details · forEach 语种列表 + 资源 forEach（LIST→DETAIL · code=0）"
)
OUT_NAME: Final[str] = "Resource-Details-Scan-LangDyn.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-Details-Scan-LangDyn-sandbox.postman_environment.json"

ALL_MODULES: Final[tuple[int, ...]] = (1, 2, 3, 4, 6, 7, 8, 11)
_DEFAULT_SCAN_LANGUAGES_FULL: Final[List[str]] = [
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
# 冒烟：RD_SCAN_SMOKE=1 时默认仅前两项（仍可被 Environment scanLanguages 覆盖）。
DEFAULT_SCAN_LANGUAGES: Final[List[str]] = (
    ["en-US", "ja-JP"]
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

_AUTH_REFRESH_SCOPE_RAW: Final[str] = (
    os.environ.get("RD_AUTH_REFRESH_SCOPE", "language").strip().lower() or "language"
)
AUTH_REFRESH_SCOPE: Final[str] = (
    _AUTH_REFRESH_SCOPE_RAW
    if _AUTH_REFRESH_SCOPE_RAW in ("language", "module", "none")
    else "language"
)

HELPERS_VAR: Final[str] = "rdlHelpersSource"


def _IdsVar(module: int) -> str:
    return f"scanResourceIdsM{module}"


def _LangForEachAs(module: int) -> str:
    return f"scanLanguagesM{module}"


def _LanguageForEachFolderName(module: int) -> str:
    return f"FOR_EACH | scanLanguages | as={_LangForEachAs(module)} | 语种"


def _ResourceForEachAs(module: int) -> str:
    return _IdsVar(module)


def _ResourceForEachFolderName(module: int) -> str:
    return f"FOR_EACH | {_IdsVar(module)} | as={_ResourceForEachAs(module)} | resourceId"


def BuildRdlJsHelpersSource() -> str:
    """供 Auth 写入 ``rdlHelpersSource``，下游步骤 eval 加载。"""
    default_langs_js = DEFAULT_SCAN_LANGUAGES_JSON
    return rf"""
var RDL_DEFAULT_SCAN_LANGUAGES = {default_langs_js};
function rdlIsCodeZero(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}}
function rdlGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}}
function rdlMustacheToken(key) {{
  // 勿在源码写字面量 {{{{}}}}：forEach 子步骤会被 Apifox 当 Handlebars 渲染而报 Template render error
  return String.fromCharCode(123, 123) + String(key || '') + String.fromCharCode(125, 125);
}}
function rdlLooksUnresolved(s) {{
  return String(s || '').indexOf(String.fromCharCode(123, 123)) >= 0;
}}
function rdlVarGet(key) {{
  var v;
  try {{
    if (pm.variables && typeof pm.variables.get === 'function') {{
      v = pm.variables.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (eu) {{}}
  try {{
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
      var rx = pm.variables.replaceIn(rdlMustacheToken(key));
      if (rx && !rdlLooksUnresolved(rx) && String(rx).trim() !== '') return String(rx).trim();
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
function rdlSetMulti(key, value) {{
  // 只写运行时 + collection：勿写 Environment/globals，避免 scanResourceIdsM* 等污染共用环境
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
}}
function rdlRequestUrlToString() {{
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
function rdlStripTrailingSlashes(s) {{
  s = String(s || '');
  while (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
  return s;
}}
function rdlResolveBaseUrl() {{
  var raw = rdlRequestUrlToString();
  if (raw) {{
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {{
      var base = rdlStripTrailingSlashes(raw.slice(0, idx));
      if ((base.indexOf('http://') === 0 || base.indexOf('https://') === 0) && !rdlLooksUnresolved(base)) {{
        return base;
      }}
    }}
  }}
  var b = rdlVarGet('baseUrl');
  if (b && !rdlLooksUnresolved(b)) return rdlStripTrailingSlashes(b);
  return '';
}}
function rdlGetPageSize() {{
  var raw = rdlVarGet('scanPageSize') || '100';
  if (rdlLooksUnresolved(raw)) return 100;
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : n;
}}
function rdlGetMaxDetails() {{
  var raw = rdlVarGet('scanMaxDetails') || '0';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function rdlUnique(arr) {{
  var seen = {{}};
  var out = [];
  for (var i = 0; i < (arr || []).length; i++) {{
    var s = String(arr[i] || '').trim();
    if (!s || seen[s]) continue;
    seen[s] = true;
    out.push(s);
  }}
  return out;
}}
function rdlCollectResourceIds(data) {{
  var ids = [];
  if (!data || typeof data !== 'object') return ids;
  var resources = data.resources || {{}};
  ['transportHubResources', 'lifestyleResources'].forEach(function (key) {{
    var arr = resources[key] || [];
    if (!Array.isArray(arr)) return;
    for (var i = 0; i < arr.length; i++) {{
      var rid = arr[i] && (arr[i].resourceId || arr[i].id);
      if (rid !== undefined && rid !== null && String(rid).trim() !== '') {{
        ids.push(String(rid).trim());
      }}
    }}
  }});
  var list = data.list || data.items || [];
  if (Array.isArray(data.resources)) list = data.resources;
  if (Array.isArray(list)) {{
    for (var j = 0; j < list.length; j++) {{
      var row = list[j] || {{}};
      var id = row.resourceId || row.id || row.associateCode;
      if (id !== undefined && id !== null && String(id).trim() !== '') ids.push(String(id).trim());
    }}
  }}
  return rdlUnique(ids);
}}
function rdlReadIdsVar(module) {{
  var ids = [];
  try {{ ids = JSON.parse(rdlVarGet('scanResourceIdsM' + module) || '[]'); }} catch (e0) {{ ids = []; }}
  return Array.isArray(ids) ? ids : [];
}}
function rdlParseLanguagesList(raw) {{
  var s = String(raw || '').trim();
  if (!s) return [];
  function cleanLang(x) {{
    return String(x || '').replace(/^\\[+/, '').replace(/\\]+$/, '').replace(/^["']+/, '').replace(/["']+$/, '').trim();
  }}
  try {{
    var parsed = JSON.parse(s);
    if (Array.isArray(parsed)) {{
      return parsed.map(cleanLang).filter(Boolean);
    }}
  }} catch (eJson) {{}}
  return s.split(/[,;]+/).map(cleanLang).filter(Boolean);
}}
function rdlResetLangIterCounters(reason) {{
  // UI 会把 collectionVariables 的 scanLangIterM* 留到下次；残留大下标 + Math.min 会钳死在列表末项（hu-HU）
  var mods = [1, 2, 3, 4, 6, 7, 8, 11];
  for (var mi = 0; mi < mods.length; mi++) {{
    var k = 'scanLangIterM' + mods[mi];
    try {{ pm.variables.set(k, '0'); }} catch (eV) {{}}
    try {{ pm.collectionVariables.set(k, '0'); }} catch (eC) {{}}
    try {{ if (typeof pm.collectionVariables.unset === 'function') pm.collectionVariables.unset(k); }} catch (eU) {{}}
    try {{ pm.collectionVariables.set(k, '0'); }} catch (eC2) {{}}
  }}
  try {{ pm.variables.set('scanCurrentLanguage', ''); }} catch (eL0) {{}}
  try {{ pm.collectionVariables.set('scanCurrentLanguage', ''); }} catch (eL1) {{}}
  console.log('[LANG] 已重置 scanLangIterM* = 0' + (reason ? '（' + reason + '）' : ''));
}}
function rdlEnsureScanLanguages() {{
  // B · Environment：尊重已填 scanLanguages；仅空时回落默认。不把单语种扩成全量。
  var langs = rdlParseLanguagesList(rdlVarGet('scanLanguages'));
  if (!langs.length) {{
    langs = Array.isArray(RDL_DEFAULT_SCAN_LANGUAGES) ? RDL_DEFAULT_SCAN_LANGUAGES.slice() : ['en-US'];
  }}
  rdlSetMulti('scanLanguages', JSON.stringify(langs));
  rdlResetLangIterCounters('Auth/EnsureScanLanguages');
  console.log('[scanLanguages] forEach 语种列表共 ' + langs.length + ' 个（Environment 可改，如 ["fr-FR"]）');
  for (var li = 0; li < langs.length; li++) {{
    console.log('[scanLanguages]   ' + (li + 1) + '/' + langs.length + '  ' + langs[li]);
  }}
  return langs;
}}
function rdlForEachElement(stepIdSuffix) {{
  var keys = [
    '$.foreach-' + stepIdSuffix + '.element',
    '$.' + stepIdSuffix + '.element',
    'foreach-' + stepIdSuffix + '.element',
    stepIdSuffix + '.element'
  ];
  for (var i = 0; i < keys.length; i++) {{
    try {{
      var v = pm.variables.get(keys[i]);
      if (v !== undefined && v !== null && String(v).trim() !== '') {{
        var s = String(v).trim();
        if (!rdlLooksUnresolved(s)) return s;
      }}
    }} catch (e0) {{}}
    try {{
      if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
        var rx = String(pm.variables.replaceIn(rdlMustacheToken(keys[i])) || '').trim();
        if (rx && !rdlLooksUnresolved(rx)) return rx;
      }}
    }} catch (e1) {{}}
  }}
  return '';
}}
function rdlTakeNextLanguage(module) {{
  // CLI 对语种 forEach 常读不到 $.foreach-*.element；按数组下标与轮次对齐（每 module 独立计数）
  var langs = rdlParseLanguagesList(rdlVarGet('scanLanguages'));
  if (!langs.length) {{
    langs = Array.isArray(RDL_DEFAULT_SCAN_LANGUAGES) ? RDL_DEFAULT_SCAN_LANGUAGES.slice() : ['en-US'];
  }}
  var key = 'scanLangIterM' + module;
  var i = parseInt(rdlVarGet(key) || '0', 10);
  if (isNaN(i) || i < 0) i = 0;
  // 禁止 Math.min 钳死在末项：残留大下标时回到 0，避免整轮只打 hu-HU
  if (i >= langs.length) {{
    console.warn('[LANG] module=' + module + ' ' + key + '=' + i
      + ' >= len=' + langs.length + ' → 重置为 0（疑似 collection 残留）');
    i = 0;
  }}
  var lang = langs[i] || 'en-US';
  rdlSetMulti(key, String(i + 1));
  rdlSetMulti('scanCurrentLanguage', lang);
  console.log('[LANG] module=' + module + ' forEach轮次下标=' + i + '/' + langs.length + ' → ' + lang);
  return lang;
}}
function rdlResolveLanguage(module) {{
  var lang = rdlForEachElement('scanLanguagesM' + module);
  if (!lang) lang = rdlForEachElement('scanLanguages');
  if (!lang) {{
    try {{
      if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
        var expr = rdlMustacheToken('$.foreach-scanLanguagesM' + module + '.element');
        var rx2 = String(pm.variables.replaceIn(expr) || '').trim();
        if (rx2 && !rdlLooksUnresolved(rx2)) lang = rx2;
      }}
    }} catch (eR) {{}}
  }}
  if (!lang) lang = rdlLangFromRequestUrl();
  // 勿把未解析的 {{$.foreach-...}} 或空串当有效语种；也勿沿用上次残留的 scanCurrentLanguage=hu-HU
  if (lang) {{
    // 去掉 Environment 误传入的括号残留
    lang = String(lang).replace(/^\\[+/, '').replace(/\\]+$/, '').trim();
    if (rdlLooksUnresolved(lang) || lang.indexOf('$.foreach-') >= 0) lang = '';
  }}
  if (lang) {{
    rdlSetMulti('scanCurrentLanguage', lang);
  }}
  return lang || '';
}}
function rdlLangFromRequestUrl() {{
  var raw = rdlRequestUrlToString();
  var m = /[?&]language=([^&]*)/.exec(raw);
  if (!m) return '';
  try {{
    var uLang = decodeURIComponent(String(m[1] || '').trim());
    if (!uLang || rdlLooksUnresolved(uLang)) return '';
    if (uLang.indexOf('foreach-') >= 0) return '';
    return uLang.replace(/^\\[+/, '').replace(/\\]+$/, '').trim();
  }} catch (e0) {{ return ''; }}
}}
function rdlFinalizeResourceIds(module) {{
  var ids = rdlUnique(rdlReadIdsVar(module));
  var maxDetails = rdlGetMaxDetails();
  if (maxDetails > 0) ids = ids.slice(0, maxDetails);
  rdlSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
  rdlSetMulti('scanDetailCallM' + module, '0');
  var lang = rdlVarGet('scanCurrentLanguage') || '';
  console.log('[LIST finalize] module=' + module + ' language=' + lang + ' count=' + ids.length
    + (maxDetails > 0 ? ' (scanMaxDetails=' + maxDetails + ')' : ''));
  if (ids.length) console.log('[LIST finalize] sample resourceId=' + ids[0]);
  return ids;
}}
function rdlBindListPageUrl(module, pageNumber) {{
  var page = parseInt(String(pageNumber || '1'), 10);
  if (isNaN(page) || page < 1) page = 1;
  var pageSize = rdlGetPageSize();
  var lang = rdlVarGet('scanCurrentLanguage') || 'en-US';
  var base = rdlResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[LIST bind] baseUrl missing module=' + module);
    return page;
  }}
  var url = rdlStripTrailingSlashes(base) + '/v2/resources?module=' + module
    + '&pageNumber=' + page
    + '&pageSize=' + pageSize
    + '&language=' + encodeURIComponent(lang);
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[LIST bind] rewrite url failed', eU);
  }}
  rdlSetMulti('scanCurrentListPage', String(page));
  console.log('[LIST bind] module=' + module + ' language=' + lang
    + ' page=' + page + ' pageSize=' + pageSize);
  return page;
}}
function rdlBindListSeedPage(module, label) {{
  var lang = rdlResolveLanguage(module);
  if (!lang) lang = rdlTakeNextLanguage(module);
  else rdlSetMulti('scanCurrentLanguage', lang);
  console.log('[LANG] ========== module=' + module + ' 语种=' + lang + ' (' + (label || '') + ') ==========');
  rdlBindListPageUrl(module, 1);
}}
function rdlSeedListPage1(module) {{
  var langNow = rdlVarGet('scanCurrentLanguage') || rdlLangFromRequestUrl() || '';
  if (langNow) rdlSetMulti('scanCurrentLanguage', langNow);
  var env = {{}};
  try {{ env = pm.response.json(); }} catch (eJ) {{ env = {{}}; }}
  pm.test('LIST-M' + module + ' | language=' + langNow + ' page=1 | 期望=code0 | 实际=响应', function () {{
    pm.expect(rdlIsCodeZero(env), 'list page1 code=0').to.eql(true);
  }});
  var data = rdlGetInnerData(env) || {{}};
  var ids = rdlCollectResourceIds(data);
  var pageSize = rdlGetPageSize();
  var pag = data.pagination || {{}};
  var total = parseInt(pag.totalNumber, 10);
  if (isNaN(total)) total = ids.length;
  var totalPages = Math.max(1, Math.ceil(total / pageSize));
  rdlSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
  rdlSetMulti('scanListTotalPagesM' + module, String(totalPages));
  console.log('[LIST] module=' + module + ' ★language=' + langNow
    + ' page1Ids=' + ids.length + ' totalNumber=' + total
    + ' totalPages=' + totalPages + ' (仅 page1，不翻页；详情走资源 forEach)');
  rdlFinalizeResourceIds(module);
}}
function rdlAssertDetailCodeZero(module) {{
  var lang = rdlVarGet('scanCurrentLanguage') || rdlLangFromRequestUrl() || '';
  var rid = rdlVarGet('scanCurrentResourceId') || '';
  pm.test('DETAIL-M' + module + ' | language=' + lang + ' resourceId=' + rid
    + ' | 期望=code0 fallbackAllowed=false | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(env.code, 'code').to.eql(0);
  }});
}}
function rdlBindForEachDetail(module, label, foreachAs) {{
  var lang = rdlVarGet('scanCurrentLanguage') || rdlResolveLanguage(module) || rdlLangFromRequestUrl() || 'en-US';
  rdlSetMulti('scanCurrentLanguage', lang);
  var rid = '';
  if (foreachAs) rid = rdlForEachElement(foreachAs);
  if (!rid) rid = rdlForEachElement('scanResourceIdsM' + module);
  var ids = rdlReadIdsVar(module);
  if (!rid) {{
    var callIdx = parseInt(rdlVarGet('scanDetailCallM' + module) || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (ids[callIdx] !== undefined) rid = String(ids[callIdx]);
    rdlSetMulti('scanDetailCallM' + module, String(callIdx + 1));
  }}
  rdlSetMulti('scanCurrentResourceId', rid || '');
  if (!rid) {{
    console.error('[DETAIL bind] module=' + module + ' 仍无 resourceId language=' + lang
      + ' label=' + (label || ''));
    return;
  }}
  var base = rdlResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[DETAIL bind] baseUrl missing');
    return;
  }}
  var url = rdlStripTrailingSlashes(base) + '/v2/resources/' + encodeURIComponent(rid)
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
    return BuildRdlJsHelpersSource().split("\n")


def _LoadHelpersLines() -> List[str]:
    return [
        "try {",
        "  var _src = '';",
        f"  try {{ _src = String(pm.collectionVariables.get('{HELPERS_VAR}') || ''); }} catch (e0) {{}}",
        f"  if (!_src) {{ try {{ _src = String(pm.variables.get('{HELPERS_VAR}') || ''); }} catch (e1) {{}} }}",
        "  if (_src) { eval(_src); }",
        f"  else {{ console.error('[rdlHelpers] {HELPERS_VAR} 为空：请先跑 Auth'); }}",
        "} catch (eLoad) { console.error('[rdlHelpers] load failed', eLoad); }",
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
    return [
        "try {",
        "  function _rdlCredHint(key) {",
        "    var v = '';",
        "    try { if (pm.iterationData && pm.iterationData.get) v = String(pm.iterationData.get(key) || ''); } catch (e0) {}",
        "    if (!v) { try { v = String(pm.variables.get(key) || ''); } catch (e1) {} }",
        "    if (!v) { try { v = String(pm.environment.get(key) || ''); } catch (e2) {} }",
        "    if (!v) { try { v = String(pm.collectionVariables.get(key) || ''); } catch (e3) {} }",
        "    v = String(v || '').trim();",
        "    if (!v) return key + '=EMPTY';",
        "    if (v.indexOf('{{') >= 0) return key + '=UNRESOLVED';",
        "    return key + '=ok(len=' + v.length + ')';",
        "  }",
        "  console.log('[Auth creds] ' + _rdlCredHint('ProgramID') + ' | ' + _rdlCredHint('clientId') + ' | ' + _rdlCredHint('secret'));",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = (d && (d.accessToken || d.token || d.access_token)) || '';",
        "  if (!t) {",
        "    console.error('[Auth] no accessToken in response code=' + j.code",
        "      + ' msg=' + String(j.msg || j.message || '')",
        "      + ' topKeys=' + Object.keys(j || {}).join(',')",
        "      + ' dataKeys=' + (d && typeof d === 'object' ? Object.keys(d).join(',') : typeof d));",
        "  }",
        "  if (t) {",
        "    try { pm.variables.set('accessToken', t); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', t); } catch (eC) {}",
        "    try { if (pm.environment) pm.environment.set('accessToken', t); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', t); } catch (eG) {}",
        "  }",
        "} catch (e) { console.warn('[Auth] save token failed', e); }",
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
    helpers_src = BuildRdlJsHelpersSource()
    export = (
        f"try {{ pm.collectionVariables.set('{HELPERS_VAR}', "
        + json.dumps(helpers_src, ensure_ascii=False)
        + "); } catch (eH) { console.warn(eH); }"
    )
    save_lines = [
        *_SaveAccessTokenLines(),
        export,
        "rdlEnsureScanLanguages();",
        *_AuthAssertTokenLines("Auth"),
        f"pm.test('Auth: {HELPERS_VAR} 已写入', function () {{",
        f"  var s = ''; try {{ s = String(pm.collectionVariables.get('{HELPERS_VAR}') || ''); }} catch (e0) {{}}",
        f"  pm.expect(s.length > 100, '{HELPERS_VAR}').to.eql(true);",
        "});",
    ]
    return _RdRequestItem(
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        headers=AuthJsonHeaders(),
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        description=(
            f"写入 accessToken + {HELPERS_VAR}；规范化 scanLanguages"
            "（Environment 优先，空才回落生成器默认全量；单语种不会自动扩全量）。"
        ),
        embed_full_helpers=True,
        prerequest_lines=[],
        test_lines=Lines_Step("Auth", save_lines),
    )


def _AuthRefreshStep(*, step_id: str, purpose_suffix: str = "") -> JsonObject:
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
            "续期 accessToken（四作用域写入）；不改写 helpers。"
            f"续期粒度 AUTH_REFRESH_SCOPE={AUTH_REFRESH_SCOPE}。"
        ),
        embed_full_helpers=False,
        load_helpers=False,
        prerequest_lines=[],
        test_lines=Lines_Step(step_id, save_lines),
    )


def _ListSeedStep(module: int) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    lang_expr = f"{{{{$.foreach-{_LangForEachAs(module)}.element}}}}"
    return _RdRequestItem(
        name=PurposeName(
            f"{label} 列表 page1",
            f"LIST-M{module}",
            "GET",
            f"/resources?module={module}&language={lang_expr}",
        ),
        method="GET",
        url_path=(
            f"/v2/resources?module={module}"
            f"&pageNumber=1&pageSize=100&language={lang_expr}"
        ),
        headers=BearerJsonHeaders(),
        description=(
            f"语种来自 forEach `{_LangForEachAs(module)}`（path 直绑 "
            f"`$.foreach-{_LangForEachAs(module)}.element`）；**仅 page1** 写入 "
            f"`{_IdsVar(module)}`，供下游资源 forEach。"
        ),
        prerequest_lines=[
            f"rdlBindListSeedPage({module}, {json.dumps(label, ensure_ascii=False)});"
        ],
        test_lines=[f"rdlSeedListPage1({module});"],
    )


def _DetailStep(module: int) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    foreach_as = _ResourceForEachAs(module)
    lang_expr = f"{{{{$.foreach-{_LangForEachAs(module)}.element}}}}"
    return _RdRequestItem(
        name=PurposeName(
            "详情 code=0 fallbackAllowed=false",
            f"DETAIL-M{module}",
            "GET",
            f"/resources/{{{{id}}}}?language={lang_expr}&fallbackAllowed=false",
        ),
        method="GET",
        url_path=(
            f"/v2/resources/{{{{scanCurrentResourceId}}}}"
            f"?module={module}&language={lang_expr}&fallbackAllowed=false"
        ),
        headers=BearerJsonHeaders(),
        description=(
            f"资源 forEach 详情；语种绑 `$.foreach-{_LangForEachAs(module)}.element`；"
            "fallbackAllowed=false；断言 code=0。"
        ),
        prerequest_lines=[
            "rdlBindForEachDetail("
            f"{module}, {json.dumps(label, ensure_ascii=False)}, "
            f"{json.dumps(foreach_as)});"
        ],
        test_lines=[f"rdlAssertDetailCodeZero({module});"],
    )


def _LanguageForEachFolder(module: int) -> JsonObject:
    items: List[JsonObject] = []
    if AUTH_REFRESH_SCOPE == "language":
        items.append(
            _AuthRefreshStep(
                step_id=f"Auth-Refresh-M{module}",
                purpose_suffix=f"M{module}/语种循环",
            )
        )
    items.extend(
        [
            _ListSeedStep(module),
            Folder(
                _ResourceForEachFolderName(module),
                [_DetailStep(module)],
                description=(
                    f"资源 forEach：遍历 `{_IdsVar(module)}` → DETAIL "
                    f"（as={_ResourceForEachAs(module)}）。"
                ),
            ),
        ]
    )
    return Folder(
        _LanguageForEachFolderName(module),
        items,
        description=(
            f"循环 Environment `scanLanguages`（as={_LangForEachAs(module)}）；"
            "每轮：Auth 续期（可选）→ LIST page1 → 资源 forEach DETAIL"
            + ("；轮前 Auth 续期。" if AUTH_REFRESH_SCOPE == "language" else "。")
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
    items.append(_LanguageForEachFolder(module))
    refresh_note = {
        "language": "语种 forEach 每轮前 Auth 续期；",
        "module": "品类前 Auth 续期；",
        "none": "无中途续期；",
    }.get(AUTH_REFRESH_SCOPE, "")
    return Folder(
        label,
        items,
        description=(
            f"module={module}：语种 forEach（`scanLanguages`，无语种子夹）；"
            f"{refresh_note}"
            "LIST page1 → 资源 forEach → DETAIL。"
        ),
    )


def BuildCollection() -> JsonObject:
    refresh_desc = {
        "language": "语种 forEach 每轮前 **Auth-Refresh** → ",
        "module": "各品类前 **Auth-Refresh** → ",
        "none": "",
    }.get(AUTH_REFRESH_SCOPE, "")
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": (
                "由 GeneratePostmanCollectionResourceDetailsScanLangDyn.py 生成"
                "（**不**覆盖静态语种子夹版 Resource Details Scan）。\n\n"
                "**编排**：Auth（token + rdlHelpersSource + `scanLanguages`）→ "
                "**8 品类夹** → `FOR_EACH scanLanguages`（Apifox：「ForEach 循环 […] 中的元素」）→ "
                f"{refresh_desc}"
                "LIST（**仅 page1** → `scanResourceIdsM{{N}}`）→ "
                "资源 `FOR_EACH` → DETAIL "
                "(`fallbackAllowed=false` / `code=0`)。\n\n"
                "**无语种子夹**：语种只走 Environment `scanLanguages` 列表 forEach。\n\n"
                "**变量关系（B · Environment）**：\n"
                "- `scanLanguages`：JSON 数组，改此项即动态选择语种（例 `[\"fr-FR\"]` / 全量）；\n"
                "- `scanPageSize`：列表 page1 的 pageSize；\n"
                "- `scanMaxDetails`：page1 ID 再截断详情条数（0=不截断）；\n"
                "- 鉴权：数据集选行 `ProgramID`/`clientId`/`secret` → Auth → `accessToken`；\n"
                "- `baseUrl` / `x-version`：Environment。\n\n"
                f"**默认语种（{len(DEFAULT_SCAN_LANGUAGES)}）**：生成器常量；Environment 可覆盖；"
                "改列表后无需改步骤结构，重跑即可（Auth 会规范化写入）。"
            ),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder(
                "00 Auth",
                [_AuthStep()],
                description="先执行 Auth（token + rdlHelpersSource + scanLanguages）。",
            ),
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
                description="语种 forEach 数组；运行时以 Environment 为准（B）",
            ),
            CollectionVariable("scanCurrentLanguage", "en-US"),
            CollectionVariable("scanCurrentResourceId", ""),
            CollectionVariable(HELPERS_VAR, ""),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    return {
        "id": "resource-details-scan-langdyn-sandbox-env",
        "name": "Resource Details Scan LangDyn sandbox（DP_MEMBERSHIP_*）",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
            {"key": "scanPageSize", "value": "100", "enabled": True},
            {"key": "scanMaxDetails", "value": "0", "enabled": True},
            {"key": "scanLanguage", "value": "en-US", "enabled": True},
            {
                "key": "scanLanguages",
                "value": DEFAULT_SCAN_LANGUAGES_JSON,
                "enabled": True,
            },
            {"key": "scanCurrentLanguage", "value": "en-US", "enabled": True},
            {"key": "scanCurrentResourceId", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionResourceDetailsScanLangDyn.py",
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
        f"modules={n_mod} languages_default={n_lang}(forEach scanLanguages via Environment) "
        f"auth_refresh_scope={AUTH_REFRESH_SCOPE} "
        f"http_step_defs≈{1 + n_refresh + n_mod * 2} "
        f"(LIST+DETAIL leaves; lang/resource forEach expand at runtime)"
    )


if __name__ == "__main__":
    Main()
