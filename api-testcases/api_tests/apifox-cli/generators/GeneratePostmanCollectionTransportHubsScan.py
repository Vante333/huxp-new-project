"""
生成 Transport Hubs（站点）全量扫描 Postman Collection v2.1（Apifox CLI · Repo-first）。

编排（对齐 Resource Details Scan；语种字面量进步骤名）::

1. ``POST /auth/token``
2. **每个语种一个静态分组**（步骤名含 ``en-US`` 等字面量）
3. 分组内：
   - LIST-SEED ``GET /v2/transportHubs?language={lang}&page=1``（不传 type）
   - ``FOR_EACH`` 列表翻页 → 汇总 ``transportHubId``
   - ``FOR_EACH`` 站点详情 ``GET /v2/transportHubs/{id}?language={lang}&fallbackAllowed=false``
     断言 ``code === 0``

说明：helpers 内嵌每步（勿写入含 ``{{`` 的 collection 变量，Apifox 会模板解析失败）。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionTransportHubsScan.py
"""
from __future__ import annotations

import json
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

COLLECTION_DISPLAY_NAME: Final[str] = "Transport Hubs · 站点全量扫描（语种×列表×详情 code=0）"
OUT_NAME: Final[str] = "Transport-Hubs-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Transport-Hubs-Scan-sandbox.postman_environment.json"

DEFAULT_SCAN_LANGUAGES: Final[List[str]] = [
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
DEFAULT_SCAN_LANGUAGES_JSON: Final[str] = json.dumps(
    DEFAULT_SCAN_LANGUAGES, ensure_ascii=False, separators=(",", ":")
)

IDS_VAR: Final[str] = "scanHubIds"
PAGES_VAR: Final[str] = "scanHubPages"


def _LangSafe(lang: str) -> str:
    return lang.replace("-", "_").replace(".", "_")


def _PageForEachFolderName(lang: str) -> str:
    safe = _LangSafe(lang)
    return f"FOR_EACH | {PAGES_VAR} | as={PAGES_VAR}_{safe} | {lang} 列表页"


def _HubForEachFolderName(lang: str) -> str:
    safe = _LangSafe(lang)
    return f"FOR_EACH | {IDS_VAR} | as={IDS_VAR}_{safe} | {lang} transportHubId"


def _HubForEachAs(lang: str) -> str:
    return f"{IDS_VAR}_{_LangSafe(lang)}"


def BuildTransportHubsScanJsHelpersSource() -> str:
    default_langs_js = DEFAULT_SCAN_LANGUAGES_JSON
    ids_var = IDS_VAR
    pages_var = PAGES_VAR
    return rf"""
var TH_DEFAULT_SCAN_LANGUAGES = {default_langs_js};
var TH_IDS_VAR = '{ids_var}';
var TH_PAGES_VAR = '{pages_var}';
function thIsCodeZero(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}}
function thGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}}
function thVarGet(key) {{
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
function thSetMulti(key, value) {{
  // 只写运行时 + collection：勿写 Environment，避免 scanCurrent* 污染共用环境
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
}}
function thRequestUrlToString() {{
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
function thStripTrailingSlashes(s) {{
  s = String(s || '');
  while (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
  return s;
}}
function thResolveBaseUrl() {{
  var raw = thRequestUrlToString();
  if (raw) {{
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {{
      var base = thStripTrailingSlashes(raw.slice(0, idx));
      if ((base.indexOf('http://') === 0 || base.indexOf('https://') === 0) && base.indexOf('{{{{') < 0) {{
        return base;
      }}
    }}
  }}
  var b = thVarGet('baseUrl');
  if (b && b.indexOf('{{{{') < 0) return thStripTrailingSlashes(b);
  return '';
}}
function thGetPageSize() {{
  var raw = thVarGet('scanPageSize') || '100';
  if (String(raw).indexOf('{{{{') >= 0) return 100;
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : Math.min(n, 100);
}}
function thGetMaxDetails() {{
  var raw = thVarGet('scanMaxDetails') || '0';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function thCollectHubIds(data) {{
  var ids = [];
  var arr = (data && data.transportHubs) || [];
  for (var i = 0; i < arr.length; i++) {{
    var hid = arr[i] && (arr[i].transportHubId || arr[i].id);
    if (hid) ids.push(String(hid));
  }}
  return ids;
}}
function thUnique(arr) {{
  var seen = {{}};
  var out = [];
  for (var i = 0; i < arr.length; i++) {{
    if (!seen[arr[i]]) {{ seen[arr[i]] = true; out.push(arr[i]); }}
  }}
  return out;
}}
function thReadIdsVar() {{
  var ids = [];
  try {{ ids = JSON.parse(thVarGet(TH_IDS_VAR) || '[]'); }} catch (e0) {{ ids = []; }}
  return Array.isArray(ids) ? ids : [];
}}
function thParseLanguagesList(raw) {{
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
function thEnsureScanLanguages() {{
  var langs = thParseLanguagesList(thVarGet('scanLanguages'));
  var legacySingleEn = langs.length === 1 && String(langs[0]).toLowerCase() === 'en-us';
  if (!langs.length || legacySingleEn) {{
    langs = Array.isArray(TH_DEFAULT_SCAN_LANGUAGES) ? TH_DEFAULT_SCAN_LANGUAGES.slice() : ['en-US'];
  }}
  var json = JSON.stringify(langs);
  thSetMulti('scanLanguages', json);
  console.log('[scanLanguages] 站点扫描语种分组共 ' + langs.length + ' 个');
  return langs;
}}
function thForEachElement(stepIdSuffix) {{
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
function thFinalizeHubIds() {{
  var ids = thUnique(thReadIdsVar());
  var maxDetails = thGetMaxDetails();
  if (maxDetails > 0) ids = ids.slice(0, maxDetails);
  thSetMulti(TH_IDS_VAR, JSON.stringify(ids));
  thSetMulti('scanHubDetailCall', '0');
  var lang = thVarGet('scanCurrentLanguage') || '';
  console.log('[LIST finalize] language=' + lang + ' count=' + ids.length
    + (maxDetails > 0 ? ' (scanMaxDetails=' + maxDetails + ')' : ''));
  if (ids.length) console.log('[LIST finalize] sample transportHubId=' + ids[0]);
  return ids;
}}
function thBindListPageUrl(pageNumber) {{
  var page = parseInt(String(pageNumber || '1'), 10);
  if (isNaN(page) || page < 1) page = 1;
  var pageSize = thGetPageSize();
  var lang = thVarGet('scanCurrentLanguage') || 'en-US';
  var base = thResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[LIST bind] baseUrl missing');
    return page;
  }}
  // 不传 type：全量站点
  var url = thStripTrailingSlashes(base) + '/v2/transportHubs'
    + '?pageNumber=' + page
    + '&pageSize=' + pageSize
    + '&language=' + encodeURIComponent(lang);
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[LIST bind] rewrite url failed', eU);
  }}
  thSetMulti('scanCurrentListPage', String(page));
  console.log('[LIST bind] language=' + lang + ' page=' + page + ' pageSize=' + pageSize);
  return page;
}}
function thBindListSeedPage(lang) {{
  lang = String(lang || 'en-US');
  thSetMulti('scanCurrentLanguage', lang);
  console.log('[LANG] ========== 站点语种=' + lang + ' ==========');
  thBindListPageUrl(1);
}}
function thBindListForEachPage(lang) {{
  lang = String(lang || thVarGet('scanCurrentLanguage') || 'en-US');
  thSetMulti('scanCurrentLanguage', lang);
  var safe = String(lang).replace(/-/g, '_').replace(/\\./g, '_');
  var pageStr = thForEachElement(TH_PAGES_VAR + '_' + safe);
  if (!pageStr) pageStr = thForEachElement(TH_PAGES_VAR);
  if (!pageStr) {{
    var pages = [];
    try {{ pages = JSON.parse(thVarGet(TH_PAGES_VAR) || '[]'); }} catch (eP) {{ pages = []; }}
    if (!Array.isArray(pages)) pages = [];
    var callIdx = parseInt(thVarGet('scanHubPageCall') || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (pages[callIdx] !== undefined) pageStr = String(pages[callIdx]);
    thSetMulti('scanHubPageCall', String(callIdx + 1));
  }}
  var page = parseInt(String(pageStr || ''), 10);
  if (isNaN(page) || page < 1) page = 1;
  thBindListPageUrl(page);
}}
function thSeedListPage1() {{
  var langNow = thVarGet('scanCurrentLanguage') || '';
  pm.test('LIST-SEED | language=' + langNow + ' | 期望=code0+建页数组 | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(thIsCodeZero(env), 'list page1 code=0').to.eql(true);
    var data = thGetInnerData(env) || {{}};
    var ids = thCollectHubIds(data);
    var pageSize = thGetPageSize();
    var pag = data.pagination || {{}};
    var total = parseInt(pag.totalNumber, 10);
    if (isNaN(total)) total = ids.length;
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    var rest = [];
    for (var p = 2; p <= totalPages; p++) rest.push(p);
    thSetMulti(TH_IDS_VAR, JSON.stringify(ids));
    thSetMulti(TH_PAGES_VAR, JSON.stringify(rest));
    thSetMulti('scanHubPageCall', '0');
    thSetMulti('scanHubTotalPages', String(totalPages));
    console.log('[LIST seed] ★language=' + langNow
      + ' page1Ids=' + ids.length + ' totalNumber=' + total
      + ' totalPages=' + totalPages + ' restPages=' + rest.length);
    if (totalPages <= 1) thFinalizeHubIds();
  }});
}}
function thAppendListPage() {{
  var langNow = thVarGet('scanCurrentLanguage') || '';
  var pageNow = thVarGet('scanCurrentListPage') || '';
  pm.test('LIST-PAGE | language=' + langNow + ' page=' + pageNow
    + ' | 期望=code0+追加ID | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(thIsCodeZero(env), 'list page code=0').to.eql(true);
    var data = thGetInnerData(env) || {{}};
    var more = thCollectHubIds(data);
    var ids = thReadIdsVar().concat(more);
    thSetMulti(TH_IDS_VAR, JSON.stringify(ids));
    var page = parseInt(thVarGet('scanCurrentListPage') || '0', 10);
    var pages = [];
    try {{ pages = JSON.parse(thVarGet(TH_PAGES_VAR) || '[]'); }} catch (e2) {{ pages = []; }}
    if (!Array.isArray(pages)) pages = [];
    console.log('[LIST page] language=' + langNow + ' page=' + page
      + ' +' + more.length + ' idsNow=' + ids.length);
    if (pages.length > 0 && page === pages[pages.length - 1]) thFinalizeHubIds();
  }});
}}
function thAssertDetailCodeZero() {{
  var lang = thVarGet('scanCurrentLanguage') || '';
  var hid = thVarGet('scanCurrentHubId') || '';
  pm.test('DETAIL | language=' + lang + ' transportHubId=' + hid
    + ' | 期望=code0 fallbackAllowed=false | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(env.code, 'code').to.eql(0);
  }});
}}
function thBindForEachDetail(lang, foreachAs) {{
  lang = String(lang || 'en-US');
  thSetMulti('scanCurrentLanguage', lang);
  var hid = '';
  if (foreachAs) hid = thForEachElement(foreachAs);
  if (!hid) hid = thForEachElement(TH_IDS_VAR);
  var ids = thReadIdsVar();
  if (!hid) {{
    var callIdx = parseInt(thVarGet('scanHubDetailCall') || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (ids[callIdx] !== undefined) hid = String(ids[callIdx]);
    thSetMulti('scanHubDetailCall', String(callIdx + 1));
  }}
  thSetMulti('scanCurrentHubId', hid || '');
  if (!hid) {{
    console.error('[DETAIL bind] 仍无 transportHubId language=' + lang);
    return;
  }}
  var base = thResolveBaseUrl();
  if (!base) {{
    try {{ base = String(pm.environment.get('baseUrl') || '').trim(); }} catch (eB) {{}}
  }}
  if (!base) {{
    console.error('[DETAIL bind] baseUrl missing');
    return;
  }}
  var url = thStripTrailingSlashes(base) + '/v2/transportHubs/' + encodeURIComponent(hid)
    + '?language=' + encodeURIComponent(lang)
    + '&fallbackAllowed=false';
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[DETAIL bind] rewrite url failed', eU);
  }}
  console.log('[DETAIL] ★language=' + lang + ' transportHubId=' + hid);
}}
""".strip()


def _HelpersLines() -> List[str]:
    return BuildTransportHubsScanJsHelpersSource().split("\n")


def _ThRequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    headers: List[JsonObject],
    description: str,
    body: Optional[str] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
    test_lines: Optional[Sequence[str]] = None,
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

    pre: List[str] = list(_HelpersLines())
    pre.extend(Lines_EnsureRequestIdHeader())
    if prerequest_lines:
        pre.extend(list(prerequest_lines))
    events.append({"listen": "prerequest", "script": {"exec": pre, "type": "text/javascript"}})

    post: List[str] = list(_HelpersLines())
    if test_lines:
        post.extend(list(test_lines))
    events.append({"listen": "test", "script": {"exec": post, "type": "text/javascript"}})
    out["event"] = events
    return out


def _AuthStep() -> JsonObject:
    save_lines = [
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
        "thEnsureScanLanguages();",
        "pm.test('Auth: HTTP 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Auth: accessToken 已写入运行时', function () {",
        "  var a = ''; try { a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var b = ''; try { b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  pm.expect(a || b, 'accessToken').to.be.ok;",
        "});",
    ]
    return _ThRequestItem(
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        headers=AuthJsonHeaders(),
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        description="写入 accessToken；helpers 内嵌各步骤（避免 collection 变量含 {{ 触发模板错误）。",
        test_lines=Lines_Step("Auth", save_lines),
    )


def _ListSeedStep(lang: str) -> JsonObject:
    return _ThRequestItem(
        name=PurposeName(
            f"站点 {lang} 列表 page1",
            f"LIST-SEED-{lang}",
            "GET",
            f"/transportHubs?language={lang}&page=1",
        ),
        method="GET",
        url_path=f"/v2/transportHubs?pageNumber=1&pageSize=100&language={lang}",
        headers=BearerJsonHeaders(),
        description=f"语种 {lang} 站点列表 page1（不传 type）；写入 `{IDS_VAR}` + `{PAGES_VAR}`。",
        prerequest_lines=[f"thBindListSeedPage({json.dumps(lang)});"],
        test_lines=["thSeedListPage1();"],
    )


def _ListPageStep(lang: str) -> JsonObject:
    return _ThRequestItem(
        name=PurposeName(
            f"站点 {lang} 列表翻页",
            f"LIST-PAGE-{lang}",
            "GET",
            f"/transportHubs?language={lang}&page={{n}}",
        ),
        method="GET",
        url_path=(
            f"/v2/transportHubs?pageNumber={{{{scanCurrentListPage}}}}"
            f"&pageSize=100&language={lang}"
        ),
        headers=BearerJsonHeaders(),
        description=f"语种 {lang} 站点列表翻页，追加 transportHubId。",
        prerequest_lines=[f"thBindListForEachPage({json.dumps(lang)});"],
        test_lines=["thAppendListPage();"],
    )


def _DetailStep(lang: str) -> JsonObject:
    foreach_as = _HubForEachAs(lang)
    return _ThRequestItem(
        name=PurposeName(
            f"站点详情 {lang} code=0 fallbackAllowed=false",
            f"DETAIL-{lang}",
            "GET",
            f"/transportHubs/{{id}}?language={lang}&fallbackAllowed=false",
        ),
        method="GET",
        url_path=(
            f"/v2/transportHubs/{{{{scanCurrentHubId}}}}"
            f"?language={lang}&fallbackAllowed=false"
        ),
        headers=BearerJsonHeaders(),
        description=f"语种 {lang} 站点详情；fallbackAllowed=false；断言 code=0。",
        prerequest_lines=[
            f"thBindForEachDetail({json.dumps(lang)}, {json.dumps(foreach_as)});"
        ],
        test_lines=["thAssertDetailCodeZero();"],
    )


def _LanguageFolder(lang: str) -> JsonObject:
    return Folder(
        f"语种 {lang}",
        [
            _ListSeedStep(lang),
            Folder(
                _PageForEachFolderName(lang),
                [_ListPageStep(lang)],
                description=f"{lang} 站点列表页 forEach（page2..N）。",
            ),
            Folder(
                _HubForEachFolderName(lang),
                [_DetailStep(lang)],
                description=f"{lang} 站点详情 forEach；fallbackAllowed=false。",
            ),
        ],
        description=f"language={lang}：站点列表 → 详情。",
    )


def BuildCollection() -> JsonObject:
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": (
                "由 GeneratePostmanCollectionTransportHubsScan.py 生成。\n\n"
                "**编排**：Auth → 语种静态分组 → LIST-SEED → 列表页 forEach → "
                "站点 forEach → DETAIL (`fallbackAllowed=false` / `code=0`)。\n"
                "**列表**：`GET /v2/transportHubs`（不传 `type`=全量）。\n"
                "**详情**：`GET /v2/transportHubs/{transportHubId}`。\n"
                "**Environment**：`scanPageSize`（≤100）、`scanMaxDetails`（0=全量）。\n"
                f"**语种（{len(DEFAULT_SCAN_LANGUAGES)}）**：改生成器常量后重新 Generate+Push。\n"
                "**鉴权**：数据集选行 `ProgramID` / `clientId` / `secret` → Auth → `accessToken`。"
            ),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth（写入 accessToken）。"),
            Folder(
                "P1 · Transport Hubs 站点扫描",
                [_LanguageFolder(lang) for lang in DEFAULT_SCAN_LANGUAGES],
                description="26 语种静态分组；步骤名含语种字面量。",
            ),
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("scanPageSize", "100"),
            CollectionVariable("scanMaxDetails", "0"),
            CollectionVariable("scanLanguages", DEFAULT_SCAN_LANGUAGES_JSON),
            CollectionVariable("scanCurrentLanguage", "en-US"),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    return {
        "id": "transport-hubs-scan-sandbox-env",
        "name": "Transport Hubs Scan sandbox",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
            {"key": "scanPageSize", "value": "100", "enabled": True},
            {"key": "scanMaxDetails", "value": "0", "enabled": True},
            {"key": "scanLanguages", "value": DEFAULT_SCAN_LANGUAGES_JSON, "enabled": True},
            {"key": "scanCurrentLanguage", "value": "en-US", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionTransportHubsScan.py",
    }


def Main() -> None:
    collection = BuildCollection()
    out_path = CollectionPath(OUT_NAME)
    env_path = EnvPath(ENV_OUT_NAME)
    WriteCollectionJson(out_path, collection)
    WriteCollectionJson(env_path, BuildEnvironmentJson())
    print("Wrote", out_path)
    print("Wrote", env_path)
    print(f"languages={len(DEFAULT_SCAN_LANGUAGES)} http_leaves≈{1 + len(DEFAULT_SCAN_LANGUAGES) * 3}")


if __name__ == "__main__":
    Main()
