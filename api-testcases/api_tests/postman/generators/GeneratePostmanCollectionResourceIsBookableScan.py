"""
生成 Resource isBookable 扫描 Postman Collection v2.1 JSON（Apifox CLI · Repo-first）。

流程：

1. ``POST /v2/auth/token`` → 集合变量 ``accessToken``
2. ``GET /v2/resources?module={{scanModule}}`` 分页拉 resourceId
3. 后置脚本内 ``pm.sendRequest`` 逐条 ``GET /v2/resources/{id}?module=&language=&fallbackAllowed=true``
4. 控制台输出 ``prebookingPolicy.isBookable === true`` 的网点列表；写入集合变量
   ``scanLastBookableIds`` / ``scanLastSummary``

Environment 手填（变量供给 B）：``ProgramID`` / ``clientId`` / ``secret`` /
``baseUrl`` / ``x-version`` / ``scanModule`` / ``scanLanguage`` /
``scanPageSize`` / ``scanMaxDetails``（0=全量，>0 抽样；SyncCheck 建议先用抽样）。

用法（仓库根）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionResourceIsBookableScan.py
"""

from __future__ import annotations

import json
from typing import Dict, Final, List

from collection_builder_common import (
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionPath,
    CollectionVariable,
    EnvPath,
    Folder,
    Lines_Step,
    POSTMAN_SCHEMA,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, object]

COLLECTION_DISPLAY_NAME: Final[str] = "Resource isBookable · 扫描（prebookingPolicy）"
OUT_NAME: Final[str] = "Resource-IsBookable-Scan.postman_collection.json"
ENV_OUT_NAME: Final[str] = "Resource-IsBookable-Scan-sandbox.postman_environment.json"
SCENARIO_DISPLAY_NAME: Final[str] = "Resource isBookable Scan - CLI sync"


def BuildScenarioDescription() -> str:
    """写入集合 info.description；PushSteps 同步到 Apifox 场景说明。"""
    return (
        "由 GeneratePostmanCollectionResourceIsBookableScan.py 生成（Repo-first）。\n\n"
        "## 链路\n"
        "1. Auth：`POST /v2/auth/token` → `accessToken`\n"
        "2. 列表：`GET /v2/resources?module={{scanModule}}` 分页收集 resourceId\n"
        "3. 详情：`GET /v2/resources/{resourceId}?module=&language=&fallbackAllowed=true`\n"
        "4. 筛出 `data.prebookingPolicy.isBookable === true`，控制台打印列表\n\n"
        "## Environment / 集合变量 → 行为\n"
        "| 变量 | 用途 |\n"
        "|------|------|\n"
        "| `ProgramID` / `clientId` / `secret` | 鉴权三列（数据集或 Environment） |\n"
        "| `baseUrl` | 如 `https://developer-sandbox.dragonpass.com/api` |\n"
        "| `x-version` | 网关版本头，默认 `canary` |\n"
        "| `scanModule` | 列表/详情 module，lounge=`1` |\n"
        "| `scanLanguage` | 详情 language，默认 `en-US` |\n"
        "| `scanPageSize` | 列表分页，默认 `100`（1–100） |\n"
        "| `scanMaxDetails` | `0`=全量详情；`>0`=只扫列表返回的前 N 个（**列表顺序≠ID 排序**，`N00012` 不一定在前 N） |\n"
        "| `scanResourceIds` | 可选。如 `N00012` 或 `N00012,N00015`：**跳过列表**，只查这些 ID（定点核对推荐） |\n\n"
        "## 产出\n"
        "- 控制台：**命中即打印** `[命中 #N] resourceId\\tresourceName`，再继续扫下一条；结尾只打数量摘要\n"
        "- 集合变量：`scanLastBookableIds`（JSON 数组）、`scanLastSummary`（摘要 JSON）\n"
        "- 断言：列表/详情扫描无 fatal 错误则通过；**不**要求 bookable 数量 >0（与 Program 配置有关）\n\n"
        "## 注意\n"
        "- `isBookable` 随 Program 变化；换测请改 Environment / 数据集三列。\n"
        "- 详情必须带 `module` query，否则会报 required parameter module missing。\n"
    )


def BuildResourceIsBookableScanJsHelpersLines() -> List[str]:
    """集合级公共 JS：列表分页、详情轮询、筛 isBookable、控制台汇总。"""
    js = r"""
function rbIsCodeZero(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === '0';
}
function rbGetInnerData(root) {
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null) return d;
  return null;
}
function rbParseJsonResponse(res) {
  if (!res || typeof res !== 'object') {
    return { code: -1, msg: 'response missing' };
  }
  try {
    if (typeof res.json === 'function') {
      var j = res.json();
      if (j && typeof j === 'object') return j;
    }
  } catch (eJ) {}
  try {
    if (typeof res.text === 'function') {
      var t = String(res.text() || '').trim();
      if (!t) return { code: -1, msg: 'empty response body' };
      if (t.charAt(0) === '<') {
        return { code: -1, msg: 'response is HTML (check baseUrl): ' + t.slice(0, 120) };
      }
      var parsed = JSON.parse(t);
      if (parsed && typeof parsed === 'object') return parsed;
    }
  } catch (eT) {
    return { code: -1, msg: 'response not json: ' + String(eT) };
  }
  return { code: -1, msg: 'response not json' };
}
function rbRequestUrlToString() {
  try {
    var u = pm.request && pm.request.url;
    if (!u) return '';
    var raw = '';
    if (typeof u === 'string') raw = u;
    else if (typeof u.toString === 'function') raw = String(u.toString());
    else if (u.raw) raw = String(u.raw);
    if (raw && pm.variables && typeof pm.variables.replaceIn === 'function') {
      raw = String(pm.variables.replaceIn(raw) || raw);
    }
    return String(raw).trim();
  } catch (e) { return ''; }
}
function rbStripTrailingSlashes(s) {
  s = String(s || '');
  while (s.length > 1 && s.charAt(s.length - 1) === '/') s = s.slice(0, -1);
  return s;
}
function rbResolveBaseUrl() {
  var raw = rbRequestUrlToString();
  if (raw && raw.indexOf('{{') < 0) {
    var idx = raw.indexOf('/v2/');
    if (idx > 0) {
      var baseFromReq = rbStripTrailingSlashes(raw.slice(0, idx));
      if (baseFromReq.indexOf('http://') === 0 || baseFromReq.indexOf('https://') === 0) return baseFromReq;
    }
  }
  var base = rbVarGet('baseUrl');
  if (base && base.indexOf('{{') < 0) return rbStripTrailingSlashes(base);
  try {
    base = String(pm.variables.replaceIn('{{baseUrl}}') || '').trim();
    if (base && base.indexOf('{{') < 0) return rbStripTrailingSlashes(base);
  } catch (eB) {}
  return '';
}
function rbEnsureAbsoluteUrl(urlOrPath) {
  var url = String(urlOrPath || '').trim();
  if (!url) return url;
  if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
  if (url.indexOf('{{') >= 0) url = '';
  var base = rbResolveBaseUrl();
  if (!base) return url || '';
  if (!url) return base + '/v2/resources';
  if (url.indexOf('/v2/') >= 0) return base + url.slice(url.indexOf('/v2/'));
  return base + (url.charAt(0) === '/' ? url : '/' + url);
}
function rbVarGet(key) {
  var v;
  try {
    if (pm.variables && typeof pm.variables.get === 'function') {
      v = pm.variables.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }
  } catch (eu) {}
  try {
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {
      var rx = pm.variables.replaceIn('{{' + key + '}}');
      if (rx && String(rx).indexOf('{{') < 0 && String(rx).trim() !== '') return String(rx).trim();
    }
  } catch (er) {}
  v = pm.collectionVariables.get(key);
  if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  try {
    if (pm.environment && typeof pm.environment.get === 'function') {
      v = pm.environment.get(key);
      if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
    }
  } catch (e1) {}
  return '';
}
function rbCollectionVarGet(key) {
  try {
    var v = pm.collectionVariables && pm.collectionVariables.get(key);
    if (v !== undefined && v !== null && String(v).trim() !== '') return String(v).trim();
  } catch (e) {}
  return '';
}
function rbResolveAccessToken() {
  var t = rbCollectionVarGet('accessToken');
  if (!t) t = rbVarGet('accessToken');
  return t || '';
}
function rbResolveProgramId() {
  var pid = rbVarGet('ProgramID');
  if (!pid) pid = rbVarGet('programId');
  return pid || '';
}
function rbJsUuidV4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0;
    var v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}
function rbFreshRequestIdForSend() {
  var rid = '';
  try {
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {
      rid = String(pm.variables.replaceIn('{{$guid}}') || '');
    }
  } catch (eR) {}
  if (!rid || rid.indexOf('{{') >= 0 || rid.indexOf('}}') >= 0) {
    rid = rbJsUuidV4();
  }
  return rid;
}
function rbBuildAuthHeaders() {
  var rid = rbFreshRequestIdForSend();
  var tok = rbResolveAccessToken();
  var pid = rbResolveProgramId();
  var xver = rbVarGet('x-version');
  return [
    { key: 'Authorization', value: 'Bearer ' + tok },
    { key: 'X-Program-ID', value: String(pid) },
    { key: 'x-version', value: xver || 'canary' },
    { key: 'X-Request-ID', value: rid },
    { key: 'Content-Type', value: 'application/json' },
    { key: 'Accept', value: '*/*' }
  ];
}
function rbBuildGetRequest(fullUrlOrPath) {
  var url = String(fullUrlOrPath || '');
  if (url.indexOf('http://') !== 0 && url.indexOf('https://') !== 0) {
    var base = rbResolveBaseUrl();
    if (!base) {
      throw new Error('baseUrl missing: set environment baseUrl or ensure SCAN step URL contains /v2/');
    }
    url = base + (url.charAt(0) === '/' ? url : '/' + url);
  }
  return { url: url, method: 'GET', header: rbBuildAuthHeaders() };
}
function rbGetScanModule() {
  var raw = rbVarGet('scanModule');
  if (!raw) raw = '1';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 1 : n;
}
function rbGetScanLanguage() {
  var lang = rbVarGet('scanLanguage');
  return lang || 'en-US';
}
function rbGetPageSize() {
  var raw = rbVarGet('scanPageSize');
  if (!raw) raw = '100';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 1 ? 100 : Math.min(n, 100);
}
function rbGetMaxDetails() {
  // Environment 未配置时：默认抽样 30（勿默认 0，否则会静默全量扫 1600+ 很久）
  // 全量请显式设 scanMaxDetails=0
  var raw = rbVarGet('scanMaxDetails');
  if (!raw && raw !== 0 && raw !== '0') raw = '30';
  var n = parseInt(String(raw).trim(), 10);
  return isNaN(n) || n < 0 ? 30 : n;
}
/** 可选：Environment ``scanResourceIds=N00012,N00015`` 时跳过列表，只查这些 ID（便于定点核对）。 */
function rbGetScanResourceIdsOverride() {
  var raw = rbVarGet('scanResourceIds');
  if (!raw) return [];
  var parts = String(raw).split(/[,;\s]+/);
  var out = [];
  for (var i = 0; i < parts.length; i++) {
    var id = String(parts[i] || '').trim();
    if (id) out.push(id);
  }
  return rbUnique(out);
}
function rbResolveScanIds(module) {
  var override = rbGetScanResourceIdsOverride();
  if (override.length) {
    console.log('[isBookable Scan] 使用 scanResourceIds 定点查询: ' + override.join(','));
    return Promise.resolve(override);
  }
  return rbFetchAllResourceIds(module).then(function (ids) {
    var maxDetails = rbGetMaxDetails();
    if (maxDetails > 0) {
      console.log(
        '[isBookable Scan] 列表共拿到后将抽样前 ' + maxDetails
        + ' 个（scanMaxDetails）；列表顺序≠resourceId 排序，N00012 等可能不在前 N 个'
      );
      ids = ids.slice(0, maxDetails);
    }
    return ids;
  });
}
function rbBuildListPageUrl(module, pageNumber, pageSize) {
  var q = 'module=' + module + '&pageNumber=' + pageNumber + '&pageSize=' + pageSize;
  var raw = rbRequestUrlToString();
  if (raw && raw.indexOf('/v2/resources') >= 0 && raw.indexOf('{{') < 0) {
    var qIdx = raw.indexOf('?');
    var listUrl = qIdx >= 0 ? raw.slice(0, qIdx) + '?' + q : raw + '?' + q;
    listUrl = rbEnsureAbsoluteUrl(listUrl);
    if (listUrl && listUrl.indexOf('http') === 0) return listUrl;
  }
  var base = rbResolveBaseUrl();
  if (!base) {
    throw new Error('baseUrl missing for list page ' + pageNumber);
  }
  return base + '/v2/resources?' + q;
}
function rbMainRequestListModule() {
  var raw = rbRequestUrlToString();
  if (!raw || raw.indexOf('/v2/resources') < 0) return null;
  var m = raw.match(/[?&]module=(\d+)/);
  return m ? parseInt(m[1], 10) : null;
}
function rbTryMainResponseAsListPage(module, pageNumber) {
  if (pageNumber !== 1) return null;
  var mainMod = rbMainRequestListModule();
  if (mainMod === null || mainMod !== module) return null;
  try {
    if (typeof pm.response.json === 'function') {
      var env = pm.response.json();
      if (env && typeof env === 'object') return env;
    }
  } catch (e) {}
  try {
    if (typeof pm.response.text === 'function') {
      var t = String(pm.response.text() || '').trim();
      if (t && t.charAt(0) !== '<') return JSON.parse(t);
    }
  } catch (e2) {}
  return null;
}
function rbCollectResourceIds(data) {
  var ids = [];
  var resources = (data && data.resources) || {};
  ['transportHubResources', 'lifestyleResources'].forEach(function (key) {
    var arr = resources[key] || [];
    for (var i = 0; i < arr.length; i++) {
      var rid = arr[i] && (arr[i].resourceId || arr[i].id);
      if (rid) ids.push(String(rid));
    }
  });
  return ids;
}
function rbUnique(arr) {
  var seen = {};
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    var v = arr[i];
    if (!seen[v]) { seen[v] = true; out.push(v); }
  }
  return out;
}
function rbSendRequestAsync(req) {
  return new Promise(function (resolve, reject) {
    pm.sendRequest(req, function (err, res) {
      if (err) return reject(err);
      resolve(res);
    });
  });
}
function rbIsInvalidSecretEnv(env) {
  if (!env || typeof env !== 'object') return false;
  var code = env.errCode || '';
  var msg = env.msg || env.message || '';
  return String(code) === '201.000.001'
    || String(msg).indexOf('Authentication failed: invalid secret provided') >= 0;
}
function rbPrintFailedRequest(req, env, context) {
  console.error('[isBookable Scan failed] ' + JSON.stringify({
    context: context,
    url: (req && req.url) || '',
    code: env && env.code,
    msg: env && (env.msg || env.errCode)
  }));
}
function rbFetchListPage(module, pageNumber, pageSize) {
  var cached = rbTryMainResponseAsListPage(module, pageNumber);
  if (cached) return Promise.resolve(cached);
  var url = rbBuildListPageUrl(module, pageNumber, pageSize);
  var req = rbBuildGetRequest(url);
  return rbSendRequestAsync(req).then(function (res) {
    var env = rbParseJsonResponse(res);
    if (!rbIsCodeZero(env) && rbIsInvalidSecretEnv(env)) {
      rbPrintFailedRequest(req, env, 'list page module=' + module + ' page=' + pageNumber);
      throw new Error('list page ' + pageNumber + ' invalid secret module=' + module);
    }
    return env;
  });
}
function rbFetchDetail(module, resourceId, language) {
  var path = '/v2/resources/' + encodeURIComponent(resourceId)
    + '?module=' + module + '&language=' + encodeURIComponent(language) + '&fallbackAllowed=true';
  var url = rbEnsureAbsoluteUrl(path);
  if (!url || url.indexOf('http') !== 0) {
    throw new Error('baseUrl missing for detail ' + resourceId);
  }
  var req = rbBuildGetRequest(url);
  return rbSendRequestAsync(req).then(function (res) {
    var env = rbParseJsonResponse(res);
    if (!rbIsCodeZero(env) && rbIsInvalidSecretEnv(env)) {
      rbPrintFailedRequest(req, env, 'detail module=' + module + ' resourceId=' + resourceId);
      throw new Error('detail invalid secret resourceId=' + resourceId);
    }
    return env;
  });
}
function rbFetchAllResourceIds(module) {
  var pageSize = rbGetPageSize();
  return rbFetchListPage(module, 1, pageSize).then(function (first) {
    if (!rbIsCodeZero(first)) {
      throw new Error('list page 1 code!=0 module=' + module + ' msg=' + (first.msg || first.errCode || ''));
    }
    var data = rbGetInnerData(first) || {};
    var ids = rbCollectResourceIds(data);
    var pag = data.pagination || {};
    var total = parseInt(pag.totalNumber, 10);
    if (isNaN(total)) total = ids.length;
    var totalPages = Math.max(1, Math.ceil(total / pageSize));
    console.log('[isBookable Scan] list totalNumber=' + total + ' pageSize=' + pageSize + ' totalPages=' + totalPages);
    var chain = Promise.resolve();
    for (var p = 2; p <= totalPages; p++) {
      (function (page) {
        chain = chain.then(function () {
          return rbFetchListPage(module, page, pageSize).then(function (env) {
            if (!rbIsCodeZero(env)) {
              throw new Error('list page ' + page + ' code!=0 module=' + module);
            }
            var inner = rbGetInnerData(env) || {};
            ids = ids.concat(rbCollectResourceIds(inner));
          });
        });
      })(p);
    }
    return chain.then(function () { return rbUnique(ids); });
  });
}
function rbReadIsBookable(env) {
  var data = rbGetInnerData(env) || {};
  var name = String(data.resourceName || '');
  var pol = data.prebookingPolicy;
  if (!pol || typeof pol !== 'object') {
    return { bookable: null, name: name };
  }
  var val = pol.isBookable;
  if (val === true || val === 'true' || val === 1 || val === '1') {
    return { bookable: true, name: name };
  }
  if (val === false || val === 'false' || val === 0 || val === '0') {
    return { bookable: false, name: name };
  }
  return { bookable: null, name: name };
}
function rbFmtJsonBrief(v, maxLen) {
  maxLen = maxLen || 240;
  var s;
  try { s = JSON.stringify(v); } catch (e) { s = String(v); }
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}
function rbAssertCheck(checkpoint, expected, actual) {
  var title = checkpoint + ' | 期望=' + rbFmtJsonBrief(expected) + ' | 实际=' + rbFmtJsonBrief(actual);
  pm.test(title, function () {
    pm.expect(actual).to.eql(expected);
  });
}
function rbAssertInfo(checkpoint, expectedDesc, actualValue) {
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + rbFmtJsonBrief(actualValue);
  pm.test(title, function () {
    pm.expect(true).to.eql(true);
  });
}
function rbScanIsBookable(module, language, label) {
  return rbResolveScanIds(module).then(function (ids) {
    console.log(
      '[isBookable Scan] 开始详情轮询 count=' + ids.length
      + '；命中 isBookable=true 即写入断言面板+控制台，再继续下一条'
    );
    var bookable = [];
    var falseCount = 0;
    var missingCount = 0;
    var failures = [];
    var chain = Promise.resolve();
    // 串行：查详情 → 符合条件立刻打印/断言 → 再进入下一个 resourceId
    ids.forEach(function (rid, idx) {
      chain = chain.then(function () {
        return rbFetchDetail(module, rid, language).then(function (env) {
          if (!rbIsCodeZero(env)) {
            failures.push({
              resourceId: rid,
              code: env && env.code,
              msg: (env && (env.msg || env.errCode)) || 'code!=0'
            });
            console.error('[detail code!=0] resourceId=' + rid + ' msg=' + ((env && env.msg) || ''));
            rbAssertInfo(
              label + ': 详情失败 ' + rid,
              'code=0',
              (env && (env.msg || env.code)) || 'fail'
            );
            return;
          }
          var parsed = rbReadIsBookable(env);
          if (parsed.bookable === true) {
            bookable.push({ resourceId: rid, resourceName: parsed.name });
            var hitMsg = rid + ' | ' + parsed.name + ' | 已扫 ' + (idx + 1) + '/' + ids.length;
            // 控制台 + 断言面板双写（Apifox UI 常看不到 sendRequest 里的 console.log）
            console.log('[命中 #' + bookable.length + '] ' + hitMsg);
            rbAssertInfo(
              label + ': 命中 #' + bookable.length + ' isBookable=true',
              'resourceId+name',
              hitMsg
            );
            try {
              pm.collectionVariables.set(
                'scanLastBookableIds',
                JSON.stringify(bookable.map(function (x) { return x.resourceId; }))
              );
            } catch (eMid) {}
          } else if (parsed.bookable === false) {
            falseCount += 1;
            // 定点模式下把 false 也打到断言面板，避免「没返回」误解
            if (rbGetScanResourceIdsOverride().length) {
              rbAssertInfo(
                label + ': ' + rid + ' isBookable=false',
                '若期望 true 请换 Program / 核对详情',
                parsed.name || rid
              );
            }
          } else {
            missingCount += 1;
            if (rbGetScanResourceIdsOverride().length) {
              rbAssertInfo(
                label + ': ' + rid + ' 缺少 prebookingPolicy.isBookable',
                '字段存在且为 boolean',
                parsed.name || rid
              );
            }
          }
        });
      });
    });
    return chain.then(function () {
      return {
        label: label,
        module: module,
        language: language,
        scanned: ids.length,
        bookableCount: bookable.length,
        falseCount: falseCount,
        missingCount: missingCount,
        errorCount: failures.length,
        bookable: bookable,
        failures: failures.slice(0, 20)
      };
    });
  });
}
function rbRunScanPromise(factory, label) {
  pm.test(label + ': 扫描', function (done) {
    factory().then(function (summary) {
      try {
        pm.collectionVariables.set('scanLastSummary', JSON.stringify({
          scanned: summary.scanned,
          bookableCount: summary.bookableCount,
          falseCount: summary.falseCount,
          missingCount: summary.missingCount,
          errorCount: summary.errorCount
        }));
        pm.collectionVariables.set(
          'scanLastBookableIds',
          JSON.stringify((summary.bookable || []).map(function (x) { return x.resourceId; }))
        );
      } catch (eSet) {}
      // 命中列表已在扫描过程中逐条打印；结尾只打数量摘要，避免重复刷屏
      console.log(
        '[isBookable Scan] 结束：命中=' + summary.bookableCount
        + ' scanned=' + summary.scanned
        + ' false=' + summary.falseCount
        + ' missing=' + summary.missingCount
        + ' err=' + summary.errorCount
        + '（逐条命中见上方 [命中 #N]）'
      );
      if (!summary.bookableCount) {
        console.log('[isBookable Scan] 本轮无 isBookable=true（检查 Program / scanMaxDetails）');
      }
      if (summary.failures && summary.failures.length) {
        console.error('[isBookable Scan] sampleFailures=' + JSON.stringify(summary.failures));
      }
      rbAssertCheck(label + ': 详情扫描无 fatal 错误', 0, summary.errorCount);
      rbAssertInfo(
        label + ': isBookable=true 数量（信息项，不硬要求>0）',
        '见控制台 [命中 #N] / scanLastBookableIds',
        summary.bookableCount
      );
      rbAssertInfo(label + ': 已扫描详情数', '见 scanMaxDetails / 全量', summary.scanned);
      done();
    }).catch(function (err) {
      console.error(label + ': 扫描异常', err);
      done(err);
    });
  });
}
"""
    return [ln for ln in js.strip().split("\n")]


def _JsHelpers() -> List[str]:
    return BuildResourceIsBookableScanJsHelpersLines()


def _AuthStep() -> JsonObject:
    return RequestItem(
        js_helpers=lambda: [],
        name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
        method="POST",
        url_path="/v2/auth/token",
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        headers=AuthJsonHeaders(),
        description="写入集合变量 accessToken；Program 用 Environment / 数据集 ProgramID。",
        save_token=True,
        test_lines=Lines_Step(
            "Auth",
            ["pm.test('Auth: HTTP 200', function () { pm.response.to.have.status(200); });"],
        ),
    )


def _ScanIsBookableStep() -> JsonObject:
    run_lines = [
        "rbRunScanPromise(function () {",
        "  var module = rbGetScanModule();",
        "  var language = rbGetScanLanguage();",
        "  return rbScanIsBookable(module, language, 'SCAN-IS-BOOKABLE');",
        "}, 'SCAN-IS-BOOKABLE');",
    ]
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(
            "列表+详情筛 isBookable=true",
            "SCAN-IS-BOOKABLE",
            "GET",
            "/resources?module={{scanModule}}",
        ),
        method="GET",
        url_path="/v2/resources?module={{scanModule}}&pageNumber=1&pageSize={{scanPageSize}}",
        body=None,
        headers=BearerJsonHeaders(),
        description=(
            "分页拉列表后在后置脚本内轮询详情；筛 `prebookingPolicy.isBookable===true`。"
            "全量很慢：Environment 设 `scanMaxDetails`（0=全量，>0 抽样）。"
            "结果见控制台与集合变量 `scanLastBookableIds`。"
        ),
        test_lines=run_lines,
    )


def BuildCollection() -> JsonObject:
    return {
        "info": {
            "name": COLLECTION_DISPLAY_NAME,
            "description": BuildScenarioDescription(),
            "schema": POSTMAN_SCHEMA,
        },
        "item": [
            Folder("00 Auth", [_AuthStep()], description="先执行 Auth 写入 accessToken。"),
            Folder(
                "P1 · isBookable 扫描",
                [_ScanIsBookableStep()],
                description="按 scanModule 全量/抽样扫描详情 isBookable。",
            ),
        ],
        "variable": [
            CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
            CollectionVariable("ProgramID", ""),
            CollectionVariable("clientId", ""),
            CollectionVariable("secret", ""),
            CollectionVariable("x-version", "canary"),
            CollectionVariable("accessToken", ""),
            CollectionVariable("scanModule", "1"),
            CollectionVariable("scanLanguage", "en-US"),
            CollectionVariable("scanPageSize", "100"),
            # 有值则跳过列表、只查这些 ID；清空后才走列表+scanMaxDetails
            CollectionVariable("scanResourceIds", "N00012"),
            # 列表模式抽样；0=全量（慢）。定点模式忽略此值
            CollectionVariable("scanMaxDetails", "30"),
            CollectionVariable("scanLastBookableIds", ""),
            CollectionVariable("scanLastSummary", ""),
        ],
    }


def BuildEnvironmentJson() -> JsonObject:
    return {
        "id": "resource-is-bookable-scan-sandbox-env",
        "name": "Resource isBookable Scan sandbox（Environment 手填）",
        "values": [
            {"key": "baseUrl", "value": "https://developer-sandbox.dragonpass.com/api", "enabled": True},
            {"key": "ProgramID", "value": "", "enabled": True},
            {"key": "clientId", "value": "", "enabled": True},
            {"key": "secret", "value": "", "enabled": True},
            {"key": "x-version", "value": "canary", "enabled": True},
            {"key": "scanModule", "value": "1", "enabled": True},
            {"key": "scanLanguage", "value": "en-US", "enabled": True},
            {"key": "scanPageSize", "value": "100", "enabled": True},
            {"key": "scanResourceIds", "value": "N00012", "enabled": True},
            {"key": "scanMaxDetails", "value": "30", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
        "_postman_exported_using": "GeneratePostmanCollectionResourceIsBookableScan.py",
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
