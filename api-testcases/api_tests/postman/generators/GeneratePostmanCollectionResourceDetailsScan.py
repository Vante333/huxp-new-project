"""
生成 Resource Details 全量扫描 Postman Collection v2.1 JSON。

对齐手工 sandbox 核对场景：

- **module=1**：分页拉列表 → 详情 ``prebookingPolicy.prebookingRequiredInfo === [1, 2]``
  （可选 26 语种 i18n 扫描）
- **module=2/3/4/6/7/8/11**：分页拉列表 → 详情 ``code === 0``（en-US）

扫描在后置脚本内用 ``pm.sendRequest`` 串行完成（非逐条静态 HTTP 步骤）。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionResourceDetailsScan.py

环境变量对齐 ``env/.env.canary`` 中 ``DP_MEMBERSHIP_*``（Program 1919256841868288）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Final, List, Sequence

from collection_builder_common import (
    CollectionPath,
    EnvPath,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    Lines_Step,
    POSTMAN_SCHEMA,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = "Resource Details · 全量扫描（prebookingRequiredInfo / code=0）"
OUT_NAME: Final[str] = "Resource-Details-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-Details-Scan-sandbox.postman_environment.json"

I18N_LANGUAGES: Final[tuple[str, ...]] = (
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
)

CODE0_MODULES: Final[tuple[int, ...]] = (2, 3, 4, 6, 7, 8, 11)
EXPECTED_PREBOOKING_REQUIRED_INFO: Final[List[int]] = [1, 2]


def BuildResourceDetailsScanJsHelpersLines() -> List[str]:
    """集合级公共 JS：列表分页、详情扫描、断言汇总。"""
    langs_json = json.dumps(list(I18N_LANGUAGES))
    modules_json = json.dumps(list(CODE0_MODULES))
    expected_json = json.dumps(EXPECTED_PREBOOKING_REQUIRED_INFO)
    js = rf"""
var RD_I18N_LANGUAGES = {langs_json};
var RD_CODE0_MODULES = {modules_json};
var RD_EXPECTED_PREBOOKING_REQUIRED_INFO = {expected_json};

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
function rdParseJsonResponse(res) {{
  if (!res || typeof res !== 'object') {{
    return {{ code: -1, msg: 'response missing' }};
  }}
  try {{
    if (typeof res.json === 'function') {{
      var j = res.json();
      if (j && typeof j === 'object') return j;
    }}
  }} catch (eJ) {{}}
  try {{
    if (typeof res.text === 'function') {{
      var t = String(res.text() || '').trim();
      if (!t) return {{ code: -1, msg: 'empty response body' }};
      if (t.charAt(0) === '<') {{
        return {{ code: -1, msg: 'response is HTML (check baseUrl): ' + t.slice(0, 120) }};
      }}
      var parsed = JSON.parse(t);
      if (parsed && typeof parsed === 'object') return parsed;
    }}
  }} catch (eT) {{
    return {{ code: -1, msg: 'response not json: ' + String(eT) }};
  }}
  return {{ code: -1, msg: 'response not json' }};
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
  if (raw && raw.indexOf('{{{{') < 0) {{
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {{
      base = rdStripTrailingSlashes(raw.slice(0, idx));
      if (base.indexOf('http://') === 0 || base.indexOf('https://') === 0) return base;
    }}
  }}
  var base = rdVarGet('baseUrl');
  if (base && base.indexOf('{{{{') < 0) return rdStripTrailingSlashes(base);
  try {{
    base = String(pm.variables.replaceIn('{{{{baseUrl}}}}') || '').trim();
    if (base && base.indexOf('{{{{') < 0) return rdStripTrailingSlashes(base);
  }} catch (eB) {{}}
  return '';
}}
function rdEnsureAbsoluteUrl(urlOrPath) {{
  var url = String(urlOrPath || '').trim();
  if (!url) return url;
  if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
  if (url.indexOf('{{{{') >= 0) url = '';
  if (!url) {{
    var base = rdResolveBaseUrl();
    if (!base) return '';
    return base + '/v2/resources';
  }}
  var base = rdResolveBaseUrl();
  if (!base) return url;
  if (url.indexOf('/v2/') >= 0) return base + url.slice(url.indexOf('/v2/'));
  return base + (url.charAt(0) === '/' ? url : '/' + url);
}}
function rdBuildListPageUrl(module, pageNumber, pageSize) {{
  var q = 'module=' + module + '&pageNumber=' + pageNumber + '&pageSize=' + pageSize;
  var raw = rdRequestUrlToString();
  if (raw && raw.indexOf('/v2/resources') >= 0 && raw.indexOf('{{{{') < 0) {{
    var qIdx = raw.indexOf('?');
    var listUrl = qIdx >= 0 ? raw.slice(0, qIdx) + '?' + q : raw + '?' + q;
    listUrl = rdEnsureAbsoluteUrl(listUrl);
    if (listUrl && listUrl.indexOf('http') === 0) return listUrl;
  }}
  var base = rdResolveBaseUrl();
  if (!base) {{
    throw new Error('baseUrl missing for list page ' + pageNumber + ': set environment baseUrl');
  }}
  return base + '/v2/resources?' + q;
}}
function rdMainRequestListModule() {{
  var raw = rdRequestUrlToString();
  if (!raw || raw.indexOf('/v2/resources') < 0) return null;
  var m = raw.match(/[?&]module=(\\d+)/);
  return m ? parseInt(m[1], 10) : null;
}}
/** page 1 与当前 SCAN 主请求同 module 时，直接复用 ``pm.response``（避免 sendRequest baseUrl 未解析收 HTML）。 */
function rdTryMainResponseAsListPage(module, pageNumber) {{
  if (pageNumber !== 1) return null;
  var mainMod = rdMainRequestListModule();
  if (mainMod === null || mainMod !== module) return null;
  try {{
    if (typeof pm.response.json === 'function') {{
      var env = pm.response.json();
      if (env && typeof env === 'object') return env;
    }}
  }} catch (e) {{}}
  try {{
    if (typeof pm.response.text === 'function') {{
      var t = String(pm.response.text() || '').trim();
      if (t && t.charAt(0) !== '<') return JSON.parse(t);
    }}
  }} catch (e2) {{}}
  return null;
}}
/** ``pm.sendRequest`` 变量解析：跳过空串，回退 collectionVariables（缓解环境空 accessToken 盖掉 Auth 写入）。 */
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
  v = pm.collectionVariables.get(key);
  if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  try {{
    if (pm.environment && typeof pm.environment.get === 'function') {{
      v = pm.environment.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (e1) {{}}
  try {{
    if (pm.globals && typeof pm.globals.get === 'function') {{
      v = pm.globals.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }}
  }} catch (e2) {{}}
  return '';
}}
function rdCollectionVarGet(key) {{
  try {{
    var v = pm.collectionVariables && pm.collectionVariables.get(key);
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  }} catch (e) {{}}
  return '';
}}
function rdResolveAccessToken() {{
  var t = rdCollectionVarGet('accessToken');
  if (!t) t = rdCollectionVarGet('access_token');
  if (!t) t = rdCollectionVarGet('token');
  if (!t) t = rdVarGet('accessToken');
  if (!t) t = rdVarGet('access_token');
  if (!t) t = rdVarGet('token');
  if (t) return t;
  try {{
    var h = pm.request && pm.request.headers;
    if (!h) return '';
    var auth = null;
    if (typeof h.get === 'function') auth = h.get('Authorization');
    if (!auth && typeof h === 'object') {{
      var hk = h.Authorization;
      if (hk) auth = hk;
    }}
    if (!auth && Array.isArray(h)) {{
      for (var i = 0; i < h.length; i++) {{
        var hi = h[i];
        if (hi && String(hi.key || '').toLowerCase() === 'authorization') {{
          auth = hi.value;
          break;
        }}
      }}
    }}
    auth = auth ? String(auth) : '';
    var up = auth.toLowerCase().indexOf('bearer ');
    if (up === 0) return auth.slice(7).trim();
  }} catch (e3) {{}}
  return '';
}}
function rdResolveProgramId() {{
  var pid = rdVarGet('ProgramID');
  if (!pid) pid = rdVarGet('programId');
  if (!pid) pid = rdVarGet('X-Program-ID');
  return pid;
}}
function rdJsUuidV4() {{
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {{
    var r = (Math.random() * 16) | 0;
    var v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  }});
}}
function rdFreshRequestIdForSend() {{
  var rid = '';
  try {{
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {{
      rid = String(pm.variables.replaceIn('{{{{$guid}}}}') || '');
    }}
  }} catch (eR) {{}}
  if (!rid || rid.indexOf('{{{{') >= 0 || rid.indexOf('}}}}') >= 0) {{
    rid = rdJsUuidV4();
  }}
  return rid;
}}
function rdApplyFreshRequestIdToHeaderList(list) {{
  var rid = rdFreshRequestIdForSend();
  var out = [];
  var seen = false;
  list.forEach(function (x) {{
    if (String(x.key || '').toLowerCase() === 'x-request-id') {{
      if (!seen) {{
        out.push({{ key: 'X-Request-ID', value: rid }});
        seen = true;
      }}
    }} else {{
      out.push(x);
    }}
  }});
  if (!seen) out.push({{ key: 'X-Request-ID', value: rid }});
  return out;
}}
/**
 * ``pm.sendRequest`` 请求头：强制使用 Auth 步骤写入的集合变量 ``accessToken`` 重新拼 Bearer。
 *
 * Apifox 在运行器里可能把 ``pm.request.headers`` 暴露成旧环境/旧 token 的已解析值，
 * 主请求可成功但内联详情请求会统一 ``201.000.001 invalid secret``；因此这里不再克隆当前请求头。
 */
function rdBuildAuthHeaders() {{
  var rid = rdFreshRequestIdForSend();
  var tok = rdResolveAccessToken();
  var pid = rdResolveProgramId();
  var xver = rdVarGet('x-version');
  return [
    {{ key: 'Authorization', value: 'Bearer ' + tok }},
    {{ key: 'X-Program-ID', value: String(pid) }},
    {{ key: 'x-version', value: xver || 'canary' }},
    {{ key: 'X-Request-ID', value: rid }},
    {{ key: 'Content-Type', value: 'application/json' }},
    {{ key: 'Accept', value: '*/*' }}
  ];
}}
function rdBuildGetRequest(fullUrlOrPath) {{
  var url = String(fullUrlOrPath || '');
  if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0) {{
    var base = rdResolveBaseUrl();
    if (!base) {{
      throw new Error('baseUrl missing: set environment baseUrl or ensure SCAN step URL contains /v2/');
    }}
    url = base + (url.charAt(0) === '/' ? url : '/' + url);
  }}
  return {{ url: url, method: 'GET', header: rdBuildAuthHeaders() }};
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
    var v = arr[i];
    if (!seen[v]) {{ seen[v] = true; out.push(v); }}
  }}
  return out;
}}
function rdGetPageSize() {{
  var raw = rdVarGet('scanPageSize');
  if (!raw) raw = '100';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : n;
}}
function rdGetMaxDetails() {{
  var raw = rdVarGet('scanMaxDetails');
  if (!raw) raw = '0';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 0 : n;
}}
function rdSendRequestAsync(req) {{
  return new Promise(function (resolve, reject) {{
    pm.sendRequest(req, function (err, res) {{
      if (err) return reject(err);
      resolve(res);
    }});
  }});
}}
function rdFetchListPage(module, pageNumber, pageSize) {{
  var cached = rdTryMainResponseAsListPage(module, pageNumber);
  if (cached) return Promise.resolve(cached);
  var url = rdBuildListPageUrl(module, pageNumber, pageSize);
  var req = rdBuildGetRequest(url);
  return rdSendRequestAsync(req).then(function (res) {{
    var env = rdParseJsonResponse(res);
    if (!rdIsCodeZero(env) && rdIsInvalidSecretEnv(env)) {{
      rdPrintFailedRequest(req, env, 'list page module=' + module + ' page=' + pageNumber);
      throw new Error('list page ' + pageNumber + ' invalid secret module=' + module);
    }}
    return env;
  }});
}}
function rdFetchDetail(module, resourceId, language) {{
  var path = '/v2/resources/' + encodeURIComponent(resourceId)
    + '?module=' + module + '&language=' + encodeURIComponent(language) + '&fallbackAllowed=true';
  var url = rdEnsureAbsoluteUrl(path);
  if (!url || url.indexOf('http') !== 0) {{
    throw new Error('baseUrl missing for detail ' + resourceId);
  }}
  var req = rdBuildGetRequest(url);
  return rdSendRequestAsync(req).then(function (res) {{
    var env = rdParseJsonResponse(res);
    if (!rdIsCodeZero(env) && rdIsInvalidSecretEnv(env)) {{
      rdPrintFailedRequest(req, env, 'detail module=' + module + ' resourceId=' + resourceId + ' language=' + language);
      throw new Error('detail invalid secret module=' + module + ' resourceId=' + resourceId + ' language=' + language);
    }}
    return env;
  }});
}}
function rdProbeFirstDetail(module, language) {{
  var pageSize = rdGetPageSize();
  return rdFetchListPage(module, 1, pageSize).then(function (first) {{
    if (!rdIsCodeZero(first)) {{
      throw new Error('probe list page 1 code!=0 module=' + module + ' msg=' + (first.msg || first.errCode || ''));
    }}
    var ids = rdUnique(rdCollectResourceIds(rdGetInnerData(first) || {{}}));
    if (!ids.length) return null;
    return rdFetchDetail(module, ids[0], language).then(function () {{
      return ids[0];
    }});
  }});
}}
function rdFetchAllResourceIds(module) {{
  var pageSize = rdGetPageSize();
  return rdFetchListPage(module, 1, pageSize).then(function (first) {{
    if (!rdIsCodeZero(first)) {{
      throw new Error('list page 1 code!=0 module=' + module + ' msg=' + (first.msg || first.errCode || ''));
    }}
    var data = rdGetInnerData(first) || {{}};
    var ids = rdCollectResourceIds(data);
    var pag = data.pagination || {{}};
    var total = parseInt(pag.totalNumber, 10);
    if (isNaN(total)) total = ids.length;
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    var chain = Promise.resolve();
    for (var p = 2; p <= totalPages; p++) {{
      (function (page) {{
        chain = chain.then(function () {{
          return rdFetchListPage(module, page, pageSize).then(function (env) {{
            if (!rdIsCodeZero(env)) {{
              throw new Error('list page ' + page + ' code!=0 module=' + module);
            }}
            var inner = rdGetInnerData(env) || {{}};
            ids = ids.concat(rdCollectResourceIds(inner));
          }});
        }});
      }})(p);
    }}
    return chain.then(function () {{ return rdUnique(ids); }});
  }});
}}
function rdFormatFailureDetail(failure) {{
  return JSON.stringify(failure, null, 2);
}}
function rdIsInvalidSecretEnv(env) {{
  if (!env || typeof env !== 'object') return false;
  var code = env.errCode || '';
  var msg = env.msg || env.message || '';
  return String(code) === '201.000.001'
    || String(msg).indexOf('Authentication failed: invalid secret provided') >= 0;
}}
function rdRedactHeaderForLog(header) {{
  var k = String((header && header.key) || '');
  var v = String((header && header.value) || '');
  if (k.toLowerCase() === 'authorization') {{
    if (v.toLowerCase().indexOf('bearer ') === 0) {{
      var token = v.slice(7).trim();
      v = 'Bearer *** len=' + token.length;
    }} else if (v) {{
      v = '***';
    }}
  }}
  return {{ key: k, value: v }};
}}
function rdPrintFailedRequest(req, env, context) {{
  var header = (req && req.header) || [];
  var safeHeaders = [];
  if (Array.isArray(header)) {{
    for (var i = 0; i < header.length; i++) {{
      safeHeaders.push(rdRedactHeaderForLog(header[i]));
    }}
  }}
  console.error('[Resource Details Scan failed request] ' + JSON.stringify({{
    context: context,
    request: {{
      method: (req && req.method) || 'GET',
      url: (req && req.url) || '',
      header: safeHeaders
    }},
    response: env
  }}, null, 2));
}}
function rdIsInvalidSecretFailure(failure) {{
  if (!failure || typeof failure !== 'object') return false;
  var code = failure.errCode || (failure.response && failure.response.errCode) || '';
  var msg = failure.msg || failure.reason || (failure.response && failure.response.msg) || '';
  return String(code) === '201.000.001'
    || String(msg).indexOf('Authentication failed: invalid secret provided') >= 0;
}}
function rdPrintInvalidSecretHint(summary) {{
  if (!summary || !summary.failures || !summary.failures.length) return;
  if (summary.failures.length !== summary.totalIds) return;
  var allInvalidSecret = true;
  for (var i = 0; i < summary.failures.length; i++) {{
    if (!rdIsInvalidSecretFailure(summary.failures[i])) {{
      allInvalidSecret = false;
      break;
    }}
  }}
  if (!allInvalidSecret) return;
  console.error(
    '[Resource Details Scan 诊断] 列表分页已成功拿到 ' + summary.totalIds
      + ' 个 resourceId，但所有详情请求均返回 201.000.001 invalid secret。'
      + ' 请检查该 Program 权限组是否开通 GET /v2/resources/{{resourceId}}（详情）权限；'
      + ' 仅开 GET /v2/resources（列表）会出现当前现象。'
  );
}}
function rdPrintCodeNonZeroDetail(module, language, resourceId, env) {{
  var detail = {{
    resourceId: resourceId,
    module: module,
    language: language,
    code: env && env.code,
    msg: (env && (env.msg || env.errCode)) || '',
    response: env
  }};
  console.error('[code!=0] ' + rdFormatFailureDetail(detail));
  return detail;
}}
function rdPrintPrebookingFailureDetail(module, language, resourceId, env, reason) {{
  var detail = {{
    resourceId: resourceId,
    module: module,
    language: language,
    reason: reason,
    code: env && env.code,
    msg: (env && (env.msg || env.errCode)) || '',
    response: env
  }};
  console.error('[prebookingRequiredInfo!=expected] ' + rdFormatFailureDetail(detail));
  return detail;
}}
function rdAssertPrebookingRequiredInfo(env, resourceId, language) {{
  if (!rdIsCodeZero(env)) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, env.msg || env.errCode || 'code!=0');
    return {{ ok: false, resourceId: resourceId, language: language, reason: env.msg || env.errCode || 'code!=0' }};
  }}
  var body = rdGetInnerData(env) || {{}};
  var pol = body.prebookingPolicy;
  var val = pol && pol.prebookingRequiredInfo;
  if (!Array.isArray(val)) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'missing prebookingPolicy.prebookingRequiredInfo');
    return {{ ok: false, resourceId: resourceId, language: language, reason: 'missing prebookingPolicy.prebookingRequiredInfo' }};
  }}
  var expected = RD_EXPECTED_PREBOOKING_REQUIRED_INFO;
  if (val.length !== expected.length) {{
    rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'prebookingRequiredInfo=' + JSON.stringify(val));
    return {{ ok: false, resourceId: resourceId, language: language, reason: 'prebookingRequiredInfo=' + JSON.stringify(val) }};
  }}
  for (var i = 0; i < expected.length; i++) {{
    if (val[i] !== expected[i]) {{
      rdPrintPrebookingFailureDetail(1, language, resourceId, env, 'prebookingRequiredInfo=' + JSON.stringify(val));
      return {{ ok: false, resourceId: resourceId, language: language, reason: 'prebookingRequiredInfo=' + JSON.stringify(val) }};
    }}
  }}
  return {{ ok: true }};
}}
function rdScanModulePrebooking(module, languages, label) {{
  var probeLanguage = languages && languages.length ? languages[0] : 'en-US';
  return rdProbeFirstDetail(module, probeLanguage).then(function () {{
    return rdFetchAllResourceIds(module);
  }}).then(function (ids) {{
    var maxDetails = rdGetMaxDetails();
    if (maxDetails > 0) ids = ids.slice(0, maxDetails);
    var failures = [];
    var okCount = 0;
    var chain = Promise.resolve();
    languages.forEach(function (lang) {{
      chain = chain.then(function () {{
        var langChain = Promise.resolve();
        ids.forEach(function (rid) {{
          langChain = langChain.then(function () {{
            return rdFetchDetail(module, rid, lang).then(function (env) {{
              var verdict = rdAssertPrebookingRequiredInfo(env, rid, lang);
              if (verdict.ok) okCount += 1;
              else failures.push(verdict);
            }});
          }});
        }});
        return langChain;
      }});
    }});
    return chain.then(function () {{
      return {{ label: label, module: module, languages: languages, totalIds: ids.length, okCount: okCount, failures: failures }};
    }});
  }});
}}
function rdScanModuleCodeZero(module, language, label) {{
  return rdProbeFirstDetail(module, language).then(function () {{
    return rdFetchAllResourceIds(module);
  }}).then(function (ids) {{
    var maxDetails = rdGetMaxDetails();
    if (maxDetails > 0) ids = ids.slice(0, maxDetails);
    var failures = [];
    var okCount = 0;
    var chain = Promise.resolve();
    ids.forEach(function (rid) {{
      chain = chain.then(function () {{
        return rdFetchDetail(module, rid, language).then(function (env) {{
          if (rdIsCodeZero(env)) {{
            okCount += 1;
          }} else {{
            failures.push(rdPrintCodeNonZeroDetail(module, language, rid, env));
          }}
        }});
      }});
    }});
    return chain.then(function () {{
      return {{ label: label, module: module, language: language, totalIds: ids.length, okCount: okCount, failures: failures }};
    }});
  }});
}}
function rdRunScanPromise(runScanFn, label) {{
  pm.test(label + ': 扫描', function (done) {{
    runScanFn().then(function (summary) {{
      pm.collectionVariables.set('scanLastSummary', JSON.stringify(summary));
      rdPrintInvalidSecretHint(summary);
      pm.expect(summary.failures.length, 'failure count').to.eql(0);
      if (summary.failures.length) {{
        console.error(label + ': 非预期共 ' + summary.failures.length + ' 条（资源详情见上方 [code!=0] / [prebookingRequiredInfo!=expected] 输出）');
      }} else {{
        console.log(label + ': 全部通过，共 ' + summary.okCount + ' 条（code=0 / 断言符合，无逐条输出）');
      }}
      done();
    }}).catch(function (err) {{
      console.error(label + ': 扫描异常', err);
      done(err);
    }});
  }});
}}
"""
    return [ln for ln in js.strip().split("\n")]


def _JsHelpers() -> List[str]:
    return BuildResourceDetailsScanJsHelpersLines()


def _AuthStep() -> JsonObject:
    return RequestItem(
        js_helpers=lambda: [],
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        headers=AuthJsonHeaders(),
        description="写入集合变量 accessToken；Program 对齐 DP_MEMBERSHIP_PROGRAM_ID。",
        save_token=True,
        test_lines=Lines_Step("Auth", ["pm.test('Auth: HTTP 200', function () { pm.response.to.have.status(200); });"]),
    )


def _ScanPrebookingStep(step_id: str, purpose: str, *, i18n: bool) -> JsonObject:
    if i18n:
        run_lines = [
            "rdRunScanPromise(function () {",
            "  return rdScanModulePrebooking(1, RD_I18N_LANGUAGES.slice(), '" + step_id + "');",
            "}, '" + step_id + "');",
        ]
        desc = (
            "module=1 全量列表 + 26 语种详情；断言 "
            "`prebookingPolicy.prebookingRequiredInfo === [1,2]`。"
            "全量扫描耗时较长，可设 scanMaxDetails 抽样。"
        )
    else:
        run_lines = [
            "rdRunScanPromise(function () {",
            "  return rdScanModulePrebooking(1, ['en-US'], '" + step_id + "');",
            "}, '" + step_id + "');",
        ]
        desc = "module=1 全量列表 + en-US 详情；断言 prebookingPolicy.prebookingRequiredInfo === [1,2]。"

    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "GET", "/resources scan"),
        method="GET",
        url_path="/v2/resources?module=1&pageNumber=1&pageSize={{scanPageSize}}",
        body=None,
        headers=BearerJsonHeaders(),
        description=desc,
        test_lines=run_lines,
    )


def _ScanCodeZeroStep(step_id: str, purpose: str, module: int) -> JsonObject:
    run_lines = [
        "rdRunScanPromise(function () {",
        "  return rdScanModuleCodeZero(" + str(module) + ", 'en-US', '" + step_id + "');",
        "}, '" + step_id + "');",
    ]
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "GET", "/resources?module=" + str(module)),
        method="GET",
        url_path="/v2/resources?module=" + str(module) + "&pageNumber=1&pageSize={{scanPageSize}}",
        body=None,
        headers=BearerJsonHeaders(),
        description=(
            f"module={module} 全量列表 + en-US 详情；断言 code=0。"
        ),
        test_lines=run_lines,
    )


def BuildCollection() -> JsonObject:
    code0_items: List[JsonObject] = []
    module_purpose: Dict[int, str] = {
        2: "FastTrack 详情 code=0",
        3: "Set Meal 详情 code=0",
        4: "Dining 详情 code=0",
        6: "Fitness 详情 code=0",
        7: "eSIM 详情 code=0",
        8: "Fitness/eSIM 变体 详情 code=0",
        11: "Local Offer 详情 code=0",
    }
    for mod in CODE0_MODULES:
        step_id = "SCAN-M" + str(mod)
        code0_items.append(_ScanCodeZeroStep(step_id, module_purpose.get(mod, "详情 code=0"), mod))

    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": (
                "由 GeneratePostmanCollectionResourceDetailsScan.py 生成。\n\n"
                "**扫描方式**：每条「SCAN-*」步骤在后置脚本内用 pm.sendRequest 分页拉列表并逐条查详情。\n"
                "**pm.sendRequest 鉴权**：优先克隆当前步骤 pm.request 已解析请求头；回退 rdVarGet + Bearer；"
                "X-Request-ID 自生成（避免 Apifox 内 {{{{$guid}}}} 未展开）。\n"
                "**列表 page 1**：与 SCAN 主请求同 module 时复用 pm.response，不重复 sendRequest。\n"
                "**sendRequest URL**：从 pm.request.url 解析 baseUrl；page 2+ 基于主请求 URL 改 query。\n"
                "**变量**：ProgramID / clientId / secret / x-version / scanPageSize(默认100) / "
                "scanMaxDetails(0=全量，>0 抽样)。\n"
                "**对齐 sandbox 手工核对**：module=1 prebookingRequiredInfo [1,2]；"
                "module 2/3/4/6/7/8/11 详情 code=0。"
            ),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth 写入 accessToken。"),
            Folder(
                "P1 · module=1 · prebookingRequiredInfo",
                [
                    _ScanPrebookingStep(
                        "SCAN-M1-EN",
                        "module=1 全量 prebookingRequiredInfo [1,2]（en-US）",
                        i18n=False,
                    ),
                    _ScanPrebookingStep(
                        "SCAN-M1-I18N",
                        "module=1 全量 prebookingRequiredInfo [1,2]（26 语种）",
                        i18n=True,
                    ),
                ],
                description="Lounge module=1；断言 prebookingPolicy.prebookingRequiredInfo。",
            ),
            Folder(
                "P1 · modules · detail code=0（en-US）",
                code0_items,
                description="各 module 独立 SCAN 步骤；详情 language=en-US。",
            ),
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("accessToken", ""),
            CollectionVariable("scanPageSize", "100"),
            CollectionVariable("scanMaxDetails", "0"),
            CollectionVariable("scanLastSummary", ""),
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


if __name__ == "__main__":
    Main()
