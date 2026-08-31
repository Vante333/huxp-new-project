"""
生成 Resource isBookable 扫描 Postman Collection v2.1 JSON（Apifox CLI · Repo-first）。

编排（对齐 Resource Details Scan · forEach；仅 en-US）::

1. ``POST /v2/auth/token`` → ``accessToken`` + ``rbHelpersSource``
2. module ∈ {1,2,7,8,11} × 语种 ``en-US`` 静态分组
3. 组内：LIST-SEED → 列表页 forEach → 资源 forEach → DETAIL
   （``fallbackAllowed=false``；筛 ``prebookingPolicy.isBookable===true``）
4. 命中写入集合变量 ``scanLastBookableIds``（JSON 数组）

变量供给 **A · 数据集选行**：业务键 ``scanPageSize`` / ``scanMaxDetails`` /
``scanResourceIds`` 走 ``postman/datasets/resource_is_bookable_scan/``；
鉴权三列仍用独立鉴权数据集 / Environment。

用法（仓库根）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionResourceIsBookableScan.py
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
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
    PostmanRootDir,
    PostmanUrl,
    PurposeName,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = "Resource isBookable · 扫描（prebookingPolicy · forEach）"
OUT_NAME: Final[str] = "Resource-IsBookable-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-IsBookable-Scan-sandbox.postman_environment.json"
SCENARIO_DISPLAY_NAME: Final[str] = "Resource isBookable Scan - CLI sync"
ASSET_KEY: Final[str] = "resource_is_bookable_scan"

SCAN_MODULES: Final[tuple[int, ...]] = (1, 2, 7, 8, 11)
SCAN_LANGUAGE: Final[str] = "en-US"

MODULE_LABEL: Final[Dict[int, str]] = {
    1: "Lounge",
    2: "FastTrack",
    7: "eSIM",
    8: "Fitness/eSIM 变体",
    11: "Local Offer",
}

# 业务键默认（数据集 / collection）；不含鉴权
DEFAULT_BIZ: Final[Dict[str, str]] = {
    "scanPageSize": "100",
    "scanMaxDetails": "30",
    "scanResourceIds": "",
    "scanLanguage": SCAN_LANGUAGE,
}


@dataclass(frozen=True)
class ScenarioEnvSpec:
    scenario_key: str
    group_name: str
    polarity: str
    module: int
    env_keys: Sequence[str]


def DatasetDir() -> Path:
    path = PostmanRootDir() / "datasets" / ASSET_KEY
    path.mkdir(parents=True, exist_ok=True)
    return path


def _IdsVar(module: int) -> str:
    return f"scanResourceIdsM{module}"


def _PagesVar(module: int) -> str:
    return f"scanListPagesM{module}"


def _LangSafe(lang: str) -> str:
    return lang.replace("-", "_").replace(".", "_")


def _PageForEachFolderName(module: int, lang: str) -> str:
    safe = _LangSafe(lang)
    return f"FOR_EACH | {_PagesVar(module)} | as={_PagesVar(module)}_{safe} | {lang} 列表页"


def _ResourceForEachFolderName(module: int, lang: str) -> str:
    safe = _LangSafe(lang)
    return f"FOR_EACH | {_IdsVar(module)} | as={_IdsVar(module)}_{safe} | {lang} resourceId"


def _ResourceForEachAs(module: int, lang: str) -> str:
    return f"{_IdsVar(module)}_{_LangSafe(lang)}"


def BuildScenarioEnvCatalog() -> List[ScenarioEnvSpec]:
    biz_keys = tuple(DEFAULT_BIZ.keys())
    specs: List[ScenarioEnvSpec] = []
    for module in SCAN_MODULES:
        label = MODULE_LABEL.get(module, f"module={module}")
        specs.append(
            ScenarioEnvSpec(
                scenario_key=f"M{module}_{_LangSafe(SCAN_LANGUAGE)}",
                group_name=f"P1 · module={module} {label} · {SCAN_LANGUAGE} isBookable",
                polarity="positive",
                module=module,
                env_keys=biz_keys,
            )
        )
    return specs


def BuildScenarioDescription() -> str:
    mods = ", ".join(str(m) for m in SCAN_MODULES)
    return (
        "由 GeneratePostmanCollectionResourceIsBookableScan.py 生成（Repo-first）。\n\n"
        "## 链路\n"
        "1. Auth：`POST /v2/auth/token` → `accessToken` + `rbHelpersSource`\n"
        f"2. module ∈ {{{mods}}} × 语种 `{SCAN_LANGUAGE}`（静态分组，步骤名含字面量）\n"
        "3. 组内：LIST-SEED → 列表页 forEach → 资源 forEach → DETAIL\n"
        "4. 筛 `data.prebookingPolicy.isBookable === true`；命中写入 `scanLastBookableIds`\n\n"
        "## 变量供给 A · 数据集选行\n"
        "- 业务数据集：`postman/datasets/resource_is_bookable_scan/apifox-dataset-business-ascii.csv`\n"
        "- 中文 Group↔name：`scenario-group-map.md`\n"
        "- 鉴权三列（`ProgramID`/`clientId`/`secret`）**不进**业务数据集；用鉴权数据集或 Environment\n"
        "- `baseUrl` / `x-version` 留 Environment（共用 351893）\n\n"
        "## 业务键 → 行为\n"
        "| 键 | 用途 |\n"
        "|------|------|\n"
        "| `scanPageSize` | 列表分页，默认 `100`（1–100） |\n"
        "| `scanMaxDetails` | `0`=全量详情；`>0`=只扫列表前 N 个 |\n"
        "| `scanResourceIds` | 可选。如 `N00012` 或 `N00012,N00015`：**跳过列表**，只查这些 ID |\n"
        "| `scanLanguage` | 固定 `en-US`（步骤已字面量展开） |\n\n"
        "## 产出\n"
        "- 控制台 / 断言面板：命中即打印 `[命中 #N] module=… resourceId …`\n"
        "- 集合变量：`scanLastBookableIds`（JSON 数组）、`scanLastSummary`（摘要 JSON）\n"
        "- **不**硬要求 bookable 数量 >0（与 Program 配置有关）\n"
    )


def BuildResourceIsBookableScanJsHelpersSource() -> str:
    """供 Auth 写入 ``rbHelpersSource``，下游步骤 eval 加载。"""
    lang_lit = json.dumps(SCAN_LANGUAGE, ensure_ascii=False)
    return rf"""
var RB_SCAN_LANGUAGE = {lang_lit};
var RB_BIZ_KEYS = ['scanPageSize','scanMaxDetails','scanResourceIds','scanLanguage'];
function rbIsPlaceholder(v) {{
  var s = String(v || '').trim();
  if (!s) return true;
  return s.indexOf('PLACEHOLDER') === 0 || s.indexOf('FILL_') === 0;
}}
function rbIsCodeZero(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}}
function rbGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}}
function rbVarGet(key) {{
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
  // 业务键禁止读 Environment（数据集选行）；infra 才读
  if (RB_BIZ_KEYS.indexOf(String(key)) >= 0) return '';
  try {{
    if (pm.environment && typeof pm.environment.get === 'function') {{
      v = pm.environment.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (e1) {{}}
  return '';
}}
function rbSetMulti(key, value) {{
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
  try {{ if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(key, v); }} catch (e3) {{}}
}}
function rbSetBizOnly(key, value) {{
  // 业务真值只写 variables/collection，禁止回写 Environment（污染共用 351893）
  var v = String(value);
  try {{ pm.variables.set(key, v); }} catch (e0) {{}}
  try {{ pm.collectionVariables.set(key, v); }} catch (e1) {{}}
}}
function rbSeedBusinessFromDataset() {{
  var defaults = {{
    scanPageSize: '100',
    scanMaxDetails: '30',
    scanResourceIds: '',
    scanLanguage: RB_SCAN_LANGUAGE
  }};
  for (var i = 0; i < RB_BIZ_KEYS.length; i++) {{
    var k = RB_BIZ_KEYS[i];
    var idV = '';
    try {{ if (pm.iterationData) idV = String(pm.iterationData.get(k) || '').trim(); }} catch (eI) {{}}
    var v = '';
    try {{ v = String(pm.variables.get(k) || '').trim(); }} catch (e0) {{}}
    var envV = '';
    try {{ envV = String((pm.environment && pm.environment.get(k)) || '').trim(); }} catch (e1) {{}}
    var pick = '';
    if (idV && !rbIsPlaceholder(idV)) pick = idV;
    else if (v && !rbIsPlaceholder(v)) pick = v;
    else if (envV && !rbIsPlaceholder(envV)) pick = envV;
    else if (idV) pick = idV;
    else if (v) pick = v;
    else if (envV) pick = envV;
    else pick = String(defaults[k] || '');
    rbSetBizOnly(k, pick);
  }}
}}
function rbRequestUrlToString() {{
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
function rbStripTrailingSlashes(s) {{
  s = String(s || '');
  while (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
  return s;
}}
function rbResolveBaseUrl() {{
  var raw = rbRequestUrlToString();
  if (raw) {{
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {{
      var base = rbStripTrailingSlashes(raw.slice(0, idx));
      if ((base.indexOf('http://') === 0 || base.indexOf('https://') === 0) && base.indexOf('{{{{') < 0) {{
        return base;
      }}
    }}
  }}
  var b = rbVarGet('baseUrl');
  if (b && b.indexOf('{{{{') < 0) return rbStripTrailingSlashes(b);
  try {{
    b = String((pm.environment && pm.environment.get('baseUrl')) || '').trim();
    if (b && b.indexOf('{{{{') < 0) return rbStripTrailingSlashes(b);
  }} catch (eB) {{}}
  return '';
}}
function rbGetPageSize() {{
  var raw = rbVarGet('scanPageSize') || '100';
  if (String(raw).indexOf('{{{{') >= 0) return 100;
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : Math.min(n, 100);
}}
function rbGetMaxDetails() {{
  var raw = rbVarGet('scanMaxDetails') || '0';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function rbGetScanResourceIdsOverride() {{
  var raw = rbVarGet('scanResourceIds') || '';
  if (!raw || raw.indexOf('{{{{') >= 0) return [];
  return raw.split(/[,;\\s]+/).map(function (x) {{ return String(x || '').trim(); }}).filter(Boolean);
}}
function rbCollectResourceIds(data) {{
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
function rbUnique(arr) {{
  var seen = {{}};
  var out = [];
  for (var i = 0; i < arr.length; i++) {{
    if (!seen[arr[i]]) {{ seen[arr[i]] = true; out.push(arr[i]); }}
  }}
  return out;
}}
function rbReadIdsVar(module) {{
  var ids = [];
  try {{ ids = JSON.parse(rbVarGet('scanResourceIdsM' + module) || '[]'); }} catch (e0) {{ ids = []; }}
  return Array.isArray(ids) ? ids : [];
}}
function rbForEachElement(stepIdSuffix) {{
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
function rbFinalizeResourceIds(module) {{
  var ids = rbUnique(rbReadIdsVar(module));
  var maxDetails = rbGetMaxDetails();
  if (maxDetails > 0) ids = ids.slice(0, maxDetails);
  rbSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
  rbSetMulti('scanDetailCallM' + module, '0');
  var lang = rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE;
  console.log('[LIST finalize] module=' + module + ' language=' + lang + ' count=' + ids.length
    + (maxDetails > 0 ? ' (scanMaxDetails=' + maxDetails + ')' : ''));
  if (ids.length) console.log('[LIST finalize] sample resourceId=' + ids[0]);
  return ids;
}}
function rbBindListPageUrl(module, pageNumber) {{
  var page = parseInt(String(pageNumber || '1'), 10);
  if (isNaN(page) || page < 1) page = 1;
  var pageSize = rbGetPageSize();
  var lang = rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE;
  var base = rbResolveBaseUrl();
  if (!base) {{
    console.error('[LIST bind] baseUrl missing module=' + module);
    return page;
  }}
  var url = rbStripTrailingSlashes(base) + '/v2/resources?module=' + module
    + '&pageNumber=' + page
    + '&pageSize=' + pageSize
    + '&language=' + encodeURIComponent(lang);
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[LIST bind] rewrite url failed', eU);
  }}
  rbSetMulti('scanCurrentListPage', String(page));
  console.log('[LIST bind] module=' + module + ' language=' + lang
    + ' page=' + page + ' pageSize=' + pageSize);
  return page;
}}
function rbBindListSeedPage(module, label, lang) {{
  lang = String(lang || RB_SCAN_LANGUAGE);
  rbSeedBusinessFromDataset();
  rbSetMulti('scanCurrentLanguage', lang);
  console.log('[LANG] ========== module=' + module + ' 语种=' + lang + ' (' + (label || '') + ') ==========');
  var override = rbGetScanResourceIdsOverride();
  if (override.length) {{
    console.log('[LIST seed] 使用 scanResourceIds 定点：' + override.join(','));
    rbSetMulti('scanResourceIdsM' + module, JSON.stringify(override));
    rbSetMulti('scanListPagesM' + module, '[]');
    rbSetMulti('scanListPageCallM' + module, '0');
    rbSetMulti('scanListTotalPagesM' + module, '1');
    rbFinalizeResourceIds(module);
    return;
  }}
  rbBindListPageUrl(module, 1);
}}
function rbBindListForEachPage(module, label, lang) {{
  lang = String(lang || rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE);
  rbSeedBusinessFromDataset();
  rbSetMulti('scanCurrentLanguage', lang);
  var safe = String(lang).replace(/-/g, '_').replace(/\\./g, '_');
  var pageStr = rbForEachElement('scanListPagesM' + module + '_' + safe);
  if (!pageStr) pageStr = rbForEachElement('scanListPagesM' + module);
  if (!pageStr) {{
    var pages = [];
    try {{ pages = JSON.parse(rbVarGet('scanListPagesM' + module) || '[]'); }} catch (eP) {{ pages = []; }}
    if (!Array.isArray(pages)) pages = [];
    var callIdx = parseInt(rbVarGet('scanListPageCallM' + module) || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (pages[callIdx] !== undefined) pageStr = String(pages[callIdx]);
    rbSetMulti('scanListPageCallM' + module, String(callIdx + 1));
  }}
  var page = parseInt(String(pageStr || ''), 10);
  if (isNaN(page) || page < 1) page = 1;
  rbBindListPageUrl(module, page);
}}
function rbSeedListPage1(module) {{
  var langNow = rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE;
  var override = rbGetScanResourceIdsOverride();
  if (override.length) {{
    pm.test('LIST-SEED-M' + module + ' | language=' + langNow + ' | 期望=定点ID已写入 | 实际=跳过列表', function () {{
      var ids = rbReadIdsVar(module);
      pm.expect(ids.length > 0, '定点 resourceIds').to.eql(true);
    }});
    return;
  }}
  pm.test('LIST-SEED-M' + module + ' | language=' + langNow + ' | 期望=code0+建页数组 | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(rbIsCodeZero(env), 'list page1 code=0').to.eql(true);
    var data = rbGetInnerData(env) || {{}};
    var ids = rbCollectResourceIds(data);
    var pageSize = rbGetPageSize();
    var pag = data.pagination || {{}};
    var total = parseInt(pag.totalNumber, 10);
    if (isNaN(total)) total = ids.length;
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    var rest = [];
    for (var p = 2; p <= totalPages; p++) rest.push(p);
    rbSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
    rbSetMulti('scanListPagesM' + module, JSON.stringify(rest));
    rbSetMulti('scanListPageCallM' + module, '0');
    rbSetMulti('scanListTotalPagesM' + module, String(totalPages));
    console.log('[LIST seed] module=' + module + ' ★language=' + langNow
      + ' page1Ids=' + ids.length + ' totalNumber=' + total
      + ' totalPages=' + totalPages + ' restPages=' + rest.length);
    if (totalPages <= 1) rbFinalizeResourceIds(module);
  }});
}}
function rbAppendListPage(module) {{
  var langNow = rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE;
  var pageNow = rbVarGet('scanCurrentListPage') || '';
  pm.test('LIST-PAGE-M' + module + ' | language=' + langNow + ' page=' + pageNow
    + ' | 期望=code0+追加ID | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(rbIsCodeZero(env), 'list page code=0').to.eql(true);
    var data = rbGetInnerData(env) || {{}};
    var more = rbCollectResourceIds(data);
    var ids = rbReadIdsVar(module).concat(more);
    rbSetMulti('scanResourceIdsM' + module, JSON.stringify(ids));
    var page = parseInt(rbVarGet('scanCurrentListPage') || '0', 10);
    var pages = [];
    try {{ pages = JSON.parse(rbVarGet('scanListPagesM' + module) || '[]'); }} catch (e2) {{ pages = []; }}
    if (!Array.isArray(pages)) pages = [];
    console.log('[LIST page] module=' + module + ' language=' + langNow
      + ' page=' + page + ' +' + more.length + ' idsNow=' + ids.length);
    if (pages.length > 0 && page === pages[pages.length - 1]) rbFinalizeResourceIds(module);
  }});
}}
function rbReadIsBookable(env) {{
  var data = rbGetInnerData(env) || {{}};
  var name = String(data.resourceName || '');
  var pol = data.prebookingPolicy;
  if (!pol || typeof pol !== 'object') {{
    return {{ bookable: null, name: name }};
  }}
  var val = pol.isBookable;
  if (val === true || val === 'true' || val === 1 || val === '1') {{
    return {{ bookable: true, name: name }};
  }}
  if (val === false || val === 'false' || val === 0 || val === '0') {{
    return {{ bookable: false, name: name }};
  }}
  return {{ bookable: null, name: name }};
}}
function rbFmtJsonBrief(v, maxLen) {{
  maxLen = maxLen || 240;
  var s;
  try {{ s = JSON.stringify(v); }} catch (e) {{ s = String(v); }}
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}}
function rbAssertInfo(checkpoint, expectedDesc, actualValue) {{
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + rbFmtJsonBrief(actualValue);
  pm.test(title, function () {{
    pm.expect(true).to.eql(true);
  }});
}}
function rbReadBookableIds() {{
  var arr = [];
  try {{ arr = JSON.parse(rbVarGet('scanLastBookableIds') || '[]'); }} catch (e0) {{ arr = []; }}
  return Array.isArray(arr) ? arr : [];
}}
function rbAppendBookable(module, rid, name) {{
  var ids = rbReadBookableIds();
  if (ids.indexOf(rid) < 0) ids.push(rid);
  rbSetMulti('scanLastBookableIds', JSON.stringify(ids));
  var hits = [];
  try {{ hits = JSON.parse(rbVarGet('scanLastBookableHits') || '[]'); }} catch (e1) {{ hits = []; }}
  if (!Array.isArray(hits)) hits = [];
  hits.push({{ module: module, resourceId: rid, resourceName: name || '' }});
  rbSetMulti('scanLastBookableHits', JSON.stringify(hits));
  rbSetMulti('scanLastSummary', JSON.stringify({{
    bookableCount: ids.length,
    lastHit: {{ module: module, resourceId: rid, resourceName: name || '' }}
  }}));
  return ids.length;
}}
function rbBindForEachDetail(module, label, lang, foreachAs) {{
  lang = String(lang || RB_SCAN_LANGUAGE);
  rbSeedBusinessFromDataset();
  rbSetMulti('scanCurrentLanguage', lang);
  var rid = '';
  if (foreachAs) rid = rbForEachElement(foreachAs);
  if (!rid) rid = rbForEachElement('scanResourceIdsM' + module);
  var ids = rbReadIdsVar(module);
  if (!rid) {{
    var callIdx = parseInt(rbVarGet('scanDetailCallM' + module) || '0', 10);
    if (isNaN(callIdx) || callIdx < 0) callIdx = 0;
    if (ids[callIdx] !== undefined) rid = String(ids[callIdx]);
    rbSetMulti('scanDetailCallM' + module, String(callIdx + 1));
  }}
  rbSetMulti('scanCurrentResourceId', rid || '');
  if (!rid) {{
    console.error('[DETAIL bind] module=' + module + ' 仍无 resourceId language=' + lang);
    return;
  }}
  var base = rbResolveBaseUrl();
  if (!base) {{
    console.error('[DETAIL bind] baseUrl missing');
    return;
  }}
  var url = rbStripTrailingSlashes(base) + '/v2/resources/' + encodeURIComponent(rid)
    + '?module=' + module
    + '&language=' + encodeURIComponent(lang)
    + '&fallbackAllowed=false';
  try {{ if (pm.request) pm.request.url = url; }} catch (eU) {{
    console.warn('[DETAIL bind] rewrite url failed', eU);
  }}
  console.log('[DETAIL] module=' + module + ' ★language=' + lang + ' resourceId=' + rid);
}}
function rbAssertDetailAndCollectBookable(module) {{
  var lang = rbVarGet('scanCurrentLanguage') || RB_SCAN_LANGUAGE;
  var rid = rbVarGet('scanCurrentResourceId') || '';
  pm.test('DETAIL-M' + module + ' | language=' + lang + ' resourceId=' + rid
    + ' | 期望=code0 fallbackAllowed=false | 实际=响应', function () {{
    var env = pm.response.json();
    pm.expect(env.code, 'code').to.eql(0);
  }});
  try {{
    var env2 = pm.response.json();
    if (!rbIsCodeZero(env2)) {{
      rbAssertInfo(
        'DETAIL-M' + module + ': 详情失败 ' + rid,
        'code=0',
        (env2 && (env2.msg || env2.code)) || 'fail'
      );
      return;
    }}
    var parsed = rbReadIsBookable(env2);
    if (parsed.bookable === true) {{
      var n = rbAppendBookable(module, rid, parsed.name);
      var hitMsg = 'module=' + module + ' | ' + rid + ' | ' + parsed.name;
      console.log('[命中 #' + n + '] ' + hitMsg);
      rbAssertInfo(
        'DETAIL-M' + module + ': 命中 #' + n + ' isBookable=true',
        'resourceId+name → scanLastBookableIds',
        hitMsg
      );
    }} else if (parsed.bookable === false) {{
      if (rbGetScanResourceIdsOverride().length) {{
        rbAssertInfo(
          'DETAIL-M' + module + ': ' + rid + ' isBookable=false',
          '若期望 true 请换 Program / 核对详情',
          parsed.name || rid
        );
      }}
    }} else if (rbGetScanResourceIdsOverride().length) {{
      rbAssertInfo(
        'DETAIL-M' + module + ': ' + rid + ' 缺少 prebookingPolicy.isBookable',
        '字段存在且为 boolean',
        parsed.name || rid
      );
    }}
  }} catch (eCollect) {{
    console.warn('[isBookable collect]', eCollect);
  }}
}}
function rbResetBookableAccumulators() {{
  rbSetMulti('scanLastBookableIds', '[]');
  rbSetMulti('scanLastBookableHits', '[]');
  rbSetMulti('scanLastSummary', '{{}}');
  console.log('[isBookable Scan] 已清空 scanLastBookableIds / Hits');
}}
""".strip()


def _HelpersLines() -> List[str]:
    return BuildResourceIsBookableScanJsHelpersSource().split("\n")


def _LoadHelpersLines() -> List[str]:
    return [
        "try {",
        "  var _src = '';",
        "  try { _src = String(pm.collectionVariables.get('rbHelpersSource') || ''); } catch (e0) {}",
        "  if (!_src) { try { _src = String(pm.variables.get('rbHelpersSource') || ''); } catch (e1) {} }",
        "  if (_src) { eval(_src); }",
        "  else { console.error('[rbHelpers] rbHelpersSource 为空：请先跑 Auth'); }",
        "} catch (eLoad) { console.error('[rbHelpers] load failed', eLoad); }",
    ]


def _SeedAuthLines() -> List[str]:
    """鉴权三列：iterationData → Environment → variables → collection → globals（无 .env 字面量回落）。"""
    lines: List[str] = ["try {"]
    for key in ("ProgramID", "clientId", "secret"):
        k_lit = json.dumps(key, ensure_ascii=False)
        lines.extend(
            [
                "  (function () {",
                f"    var _k = {k_lit};",
                "    var _id = ''; try { if (pm.iterationData) _id = String(pm.iterationData.get(_k) || '').trim(); } catch (eI) {}",
                "    var _e = ''; try { _e = String((pm.environment && pm.environment.get(_k)) || '').trim(); } catch (eE0) {}",
                "    var _v = ''; try { _v = String(pm.variables.get(_k) || '').trim(); } catch (eV0) {}",
                "    var _c = ''; try { _c = String(pm.collectionVariables.get(_k) || '').trim(); } catch (eC0) {}",
                "    var _g = ''; try { _g = String((pm.globals && pm.globals.get(_k)) || '').trim(); } catch (eG0) {}",
                "    var _pick = _id || _e || _v || _c || _g;",
                "    if (_pick) {",
                "      try { pm.variables.set(_k, _pick); } catch (e1) {}",
                "      try { pm.collectionVariables.set(_k, _pick); } catch (e2) {}",
                "      try { if (pm.environment) pm.environment.set(_k, _pick); } catch (e3) {}",
                "      try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(_k, _pick); } catch (e4) {}",
                "    }",
                "  })();",
            ]
        )
    lines.extend(
        [
            "  var _pid = '';",
            "  try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP) {}",
            "  if (_pid && pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
            "    try { pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid }); } catch (ePH) {}",
            "  }",
            "} catch (eSeed) { console.warn('seed auth', eSeed); }",
        ]
    )
    return lines


def _RbRequestItem(
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
    else:
        pre.extend(_LoadHelpersLines())
    pre.extend(_SeedAuthLines())
    pre.extend(Lines_EnsureRequestIdHeader())
    if prerequest_lines:
        pre.extend(list(prerequest_lines))
    events.append({"listen": "prerequest", "script": {"exec": pre, "type": "text/javascript"}})

    post: List[str] = []
    if embed_full_helpers:
        post.extend(_HelpersLines())
    else:
        post.extend(_LoadHelpersLines())
    if test_lines:
        post.extend(list(test_lines))
    events.append({"listen": "test", "script": {"exec": post, "type": "text/javascript"}})
    out["event"] = events
    return out


def _AuthStep() -> JsonObject:
    helpers_src = BuildResourceIsBookableScanJsHelpersSource()
    export = (
        "try { pm.collectionVariables.set('rbHelpersSource', "
        + json.dumps(helpers_src, ensure_ascii=False)
        + "); } catch (eH) { console.warn(eH); }"
    )
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
        export,
        "rbResetBookableAccumulators();",
        "rbSeedBusinessFromDataset();",
        "pm.test('Auth: HTTP 200', function () { pm.response.to.have.status(200); });",
        "pm.test('Auth: accessToken 已写入运行时', function () {",
        "  var a = ''; try { a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var b = ''; try { b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  pm.expect(a || b, 'accessToken').to.be.ok;",
        "});",
        "pm.test('Auth: rbHelpersSource 已写入', function () {",
        "  var s = ''; try { s = String(pm.collectionVariables.get('rbHelpersSource') || ''); } catch (e0) {}",
        "  pm.expect(s.length > 100, 'rbHelpersSource').to.eql(true);",
        "});",
    ]
    return _RbRequestItem(
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        headers=AuthJsonHeaders(),
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        description="写入 accessToken + rbHelpersSource；清空 scanLastBookableIds。",
        embed_full_helpers=True,
        prerequest_lines=[],
        test_lines=Lines_Step("Auth", save_lines),
    )


def _ListSeedStep(module: int, lang: str) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    return _RbRequestItem(
        name=PurposeName(
            f"{label} {lang} 列表 page1",
            f"LIST-SEED-M{module}-{lang}",
            "GET",
            f"/resources?module={module}&language={lang}&page=1",
        ),
        method="GET",
        url_path=f"/v2/resources?module={module}&pageNumber=1&pageSize=100&language={lang}",
        headers=BearerJsonHeaders(),
        description=(
            f"语种 {lang} 列表 page1 → `{_IdsVar(module)}` + `{_PagesVar(module)}`；"
            "若数据集 `scanResourceIds` 非空则定点跳过列表。"
        ),
        prerequest_lines=[
            f"rbBindListSeedPage({module}, {json.dumps(label, ensure_ascii=False)}, {json.dumps(lang)});"
        ],
        test_lines=[f"rbSeedListPage1({module});"],
    )


def _ListPageStep(module: int, lang: str) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    return _RbRequestItem(
        name=PurposeName(
            f"{label} {lang} 列表翻页",
            f"LIST-PAGE-M{module}-{lang}",
            "GET",
            f"/resources?module={module}&language={lang}&page={{n}}",
        ),
        method="GET",
        url_path=(
            f"/v2/resources?module={module}"
            f"&pageNumber={{{{scanCurrentListPage}}}}&pageSize=100&language={lang}"
        ),
        headers=BearerJsonHeaders(),
        description=f"语种 {lang} 列表翻页，追加 resourceId。",
        prerequest_lines=[
            f"rbBindListForEachPage({module}, {json.dumps(label, ensure_ascii=False)}, {json.dumps(lang)});"
        ],
        test_lines=[f"rbAppendListPage({module});"],
    )


def _DetailStep(module: int, lang: str) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    foreach_as = _ResourceForEachAs(module, lang)
    return _RbRequestItem(
        name=PurposeName(
            f"详情 {lang} 筛 isBookable=true",
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
        description=(
            f"语种 {lang} 详情；`fallbackAllowed=false`；"
            "命中 `isBookable===true` 追加到 `scanLastBookableIds`。"
        ),
        prerequest_lines=[
            "rbBindForEachDetail("
            f"{module}, {json.dumps(label, ensure_ascii=False)}, {json.dumps(lang)}, "
            f"{json.dumps(foreach_as)});"
        ],
        test_lines=[f"rbAssertDetailAndCollectBookable({module});"],
    )


def _LanguageFolder(module: int, lang: str) -> JsonObject:
    return Folder(
        f"语种 {lang}",
        [
            _ListSeedStep(module, lang),
            Folder(
                _PageForEachFolderName(module, lang),
                [_ListPageStep(module, lang)],
                description=f"{lang} 列表页 forEach（page2..N）。",
            ),
            Folder(
                _ResourceForEachFolderName(module, lang),
                [_DetailStep(module, lang)],
                description=f"{lang} 资源详情 forEach；筛 isBookable。",
            ),
        ],
        description=f"module={module} / language={lang}：列表 → 详情筛 isBookable。",
    )


def _ModuleGroup(module: int) -> JsonObject:
    label = MODULE_LABEL.get(module, f"module={module}")
    return Folder(
        f"P1 · module={module} {label} · {SCAN_LANGUAGE} isBookable",
        [_LanguageFolder(module, SCAN_LANGUAGE)],
        description=(
            f"module={module}（{label}）：语种 {SCAN_LANGUAGE}；"
            "LIST-SEED → 列表翻页 forEach → 资源详情 forEach → 筛 isBookable。"
        ),
    )


def BuildCollection() -> JsonObject:
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": BuildScenarioDescription(),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth（token + rbHelpersSource）。"),
            *[_ModuleGroup(m) for m in SCAN_MODULES],
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("accessToken", ""),
            CollectionVariable("scanPageSize", DEFAULT_BIZ["scanPageSize"]),
            CollectionVariable("scanMaxDetails", DEFAULT_BIZ["scanMaxDetails"]),
            CollectionVariable("scanResourceIds", DEFAULT_BIZ["scanResourceIds"]),
            CollectionVariable("scanLanguage", SCAN_LANGUAGE),
            CollectionVariable("scanCurrentLanguage", SCAN_LANGUAGE),
            CollectionVariable("scanLastBookableIds", "[]"),
            CollectionVariable("scanLastBookableHits", "[]"),
            CollectionVariable("scanLastSummary", "{}"),
            CollectionVariable("rbHelpersSource", ""),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    """Environment 只留网关 + 鉴权占位；业务键走数据集（勿在此填真值）。"""
    return {
        "id": "resource-is-bookable-scan-sandbox-env",
        "name": "Resource isBookable Scan sandbox（网关+鉴权；业务看数据集）",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionResourceIsBookableScan.py",
    }


def WriteApifoxBusinessDatasetCsvs() -> List[Path]:
    catalog = BuildScenarioEnvCatalog()
    biz_keys = list(DEFAULT_BIZ.keys())
    out_dir = DatasetDir()
    fieldnames = ["name", "scenario_key", "title", "polarity", "notes"] + biz_keys

    full_zh = "全量并集（填齐后勾选本行跑整场景）"
    zh_rows: List[Dict[str, str]] = [
        {
            "name": full_zh,
            "scenario_key": "_FULL_SUITE",
            "title": full_zh,
            "polarity": "full",
            "notes": "填齐业务列后勾选；鉴权仍用鉴权数据集三列；scanMaxDetails=0 全量",
            **{**DEFAULT_BIZ, "scanMaxDetails": "0"},
        }
    ]
    ascii_rows: List[Dict[str, str]] = [
        {
            "name": "_FULL_SUITE",
            "scenario_key": "_FULL_SUITE",
            "title": "full_suite",
            "polarity": "full",
            "notes": "fill_biz_cols; auth=auth_dataset; scanMaxDetails=0_full",
            **{**DEFAULT_BIZ, "scanMaxDetails": "0"},
        }
    ]
    for spec in catalog:
        base = dict(DEFAULT_BIZ)
        zh_rows.append(
            {
                "name": spec.group_name,
                "scenario_key": spec.scenario_key,
                "title": spec.group_name,
                "polarity": spec.polarity,
                "notes": f"module={spec.module} language={SCAN_LANGUAGE}",
                **base,
            }
        )
        ascii_rows.append(
            {
                "name": spec.scenario_key,
                "scenario_key": spec.scenario_key,
                "title": spec.scenario_key,
                "polarity": spec.polarity,
                "notes": f"module={spec.module}",
                **base,
            }
        )

    utf8_path = out_dir / "apifox-dataset-business.csv"
    ascii_path = out_dir / "apifox-dataset-business-ascii.csv"
    with utf8_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(zh_rows)
    with ascii_path.open("w", encoding="ascii", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ascii_rows)
    return [utf8_path, ascii_path]


def WriteScenarioGroupMapMd() -> Path:
    catalog = BuildScenarioEnvCatalog()
    out = DatasetDir() / "scenario-group-map.md"
    lines = [
        "# 数据集 name（中文）↔ scenario_key",
        "",
        f"场景：`{SCENARIO_DISPLAY_NAME}` · 资产 `{ASSET_KEY}`",
        "",
        "Apifox 全量数据 **name** 列用中文 Group 名；`scenario_key` 为稳定英文键。",
        "",
        "| name（中文 Group） | scenario_key | module |",
        "|---|---|---|",
        "| 全量并集（填齐后勾选本行跑整场景） | `_FULL_SUITE` | all |",
    ]
    for spec in catalog:
        lines.append(
            f"| {spec.group_name} | `{spec.scenario_key}` | {spec.module} |"
        )
    lines.extend(
        [
            "",
            "## 业务列",
            "",
            "| 列 | 说明 |",
            "|----|------|",
            "| `scanPageSize` | 列表分页（默认 100） |",
            "| `scanMaxDetails` | 0=全量；>0=前 N 个（SyncCheck 建议 30） |",
            "| `scanResourceIds` | 定点 ID，逗号分隔；非空则跳过列表 |",
            "| `scanLanguage` | 固定 en-US |",
            "",
            "鉴权三列 **不要** 放进本业务数据集。",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def WriteDatasetReadme() -> Path:
    out = DatasetDir() / "README.md"
    out.write_text(
        "\n".join(
            [
                "# Resource isBookable Scan · Apifox 全量数据导入",
                "",
                "## 推荐导入（name = 中文 Group）",
                "",
                "文件：`apifox-dataset-business.csv`（UTF-8 BOM）",
                "",
                "| 列 | 含义 |",
                "|----|------|",
                "| **name** | 中文 Group 名（与场景目录一致，勾选用） |",
                "| **scenario_key** | 英文稳定键 |",
                "| 业务列 | `scanPageSize` / `scanMaxDetails` / `scanResourceIds` / `scanLanguage` |",
                "",
                "1. 导入本文件，编码选 **UTF-8**",
                "2. 勾选对应 `name` 行再跑场景 Group（选行只换变量，不会自动只跑某一 Group）",
                "3. 鉴权仍勾「自动化-鉴权」数据集三列；先跑 `00 Auth`",
                "",
                "若中文乱码：改用 `apifox-dataset-business-ascii.csv`。",
                "",
                "对照表：`scenario-group-map.md`。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return out


def Main() -> None:
    collection = BuildCollection()
    out_path = CollectionPath(OUT_NAME)
    env_path = EnvPath(ENV_OUT_NAME)
    WriteCollectionJson(out_path, collection)
    WriteCollectionJson(env_path, BuildEnvironmentJson())
    print("Wrote", out_path)
    print("Wrote", env_path)
    for path in WriteApifoxBusinessDatasetCsvs():
        print("Wrote", path)
    print("Wrote", WriteScenarioGroupMapMd())
    print("Wrote", WriteDatasetReadme())
    n_mod = len(SCAN_MODULES)
    print(f"modules={n_mod} language={SCAN_LANGUAGE} http_leaves≈{1 + n_mod * 3}")


if __name__ == "__main__":
    Main()
