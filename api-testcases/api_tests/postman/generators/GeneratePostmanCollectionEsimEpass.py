"""
生成 eSIM ePass **P0 E2E 核心** Postman Collection v2.1 JSON。

对齐 ``test_historical_epass_esim.py`` 三条主链路及 ``historical_epass_service`` 断言语义（``catalog_label="esim"``）：

- E01 创建验证链 · ``RunHistoricalEpassCreateMainE2EScenario``
- E02 预约验证链 · ``RunHistoricalEpassPrebookingMainE2EScenario``
- E03 Bundle 一步下单 · ``RunHistoricalEpassBundleMainE2EScenario``

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionEsimEpass.py
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Final, List, Optional, Sequence

from collection_builder_common import (
    CollectionPath,
    POSTMAN_SCHEMA,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    JsExpr_FreshRequestId,
    Lines_Step,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, Any]

OUT_NAME: Final[str] = "Esim-ePass-P0-e2e-core.postman_collection.json"
PREBOOKING_DATE_APIFOX: Final[str] = "{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30"
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CANCEL_RETRY_MSG_NEEDLE: Final[str] = "Order cancellation failed"
CREATE_FIRST_NAME: Final[str] = "Auto"
CREATE_LAST_NAME: Final[str] = "Test"
CREATE_EXPIRATION_DATE: Final[str] = "2028-12-31T23:59:59+00:00"
CREATE_AVAILABLE_USAGES: Final[int] = 1
DEFAULT_ESIM_RESOURCE_ID: Final[str] = "GR0005901"
DEFAULT_ESIM_OPTION_ID: Final[str] = "SKU-GS0010955"
ESIM_RESOURCE_ID_VAR: Final[str] = "esimResourceId"
ESIM_OPTION_ID_VAR: Final[str] = "esimOptionId"
ENV_ESIM_RESOURCE_ID: Final[str] = "DP_HIST_EPASS_ESIM_RESOURCE_ID"
ENV_ESIM_OPTION_ID: Final[str] = "DP_HIST_EPASS_ESIM_OPTION_ID"
EPASS_MODULE_DEFAULT: Final[int] = 8
OTHER_MODULE_DEFAULT: Final[int] = 11

CREATE_PAYLOAD_TEMPLATE: Final[str] = json.dumps(
    {
        "module": EPASS_MODULE_DEFAULT,
        "clientUserId": "{{clientUserId}}",
        "extra": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "expirationDate": CREATE_EXPIRATION_DATE,
            "availableUsages": CREATE_AVAILABLE_USAGES,
            "allowedResources": {
                "resourceIds": [],
                "iata": [],
                "countryOrRegion": [],
            },
        },
    },
    ensure_ascii=False,
    indent=2,
)


def BuildEsimJsHelpersLines() -> List[str]:
    """与 ``historical_epass_service`` / eSIM options 链断言语义对齐的公共 JS（``ep*`` 前缀）。"""
    cancel_msg_js = json.dumps(CANCEL_SUCCESS_MSG)
    cancel_retry_needle_js = json.dumps(CANCEL_RETRY_MSG_NEEDLE)
    create_first_name_js = json.dumps(CREATE_FIRST_NAME)
    create_last_name_js = json.dumps(CREATE_LAST_NAME)
    create_expiration_date_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_available_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    epass_module_default_js = json.dumps(EPASS_MODULE_DEFAULT)
    other_module_default_js = json.dumps(OTHER_MODULE_DEFAULT)
    esim_resource_var = ESIM_RESOURCE_ID_VAR
    esim_option_var = ESIM_OPTION_ID_VAR
    js = rf"""
function epExpectedModule() {{
  var raw = pm.collectionVariables.get('epassModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {epass_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {epass_module_default_js} : n;
}}
function epOtherModule() {{
  var raw = pm.collectionVariables.get('otherModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {other_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {other_module_default_js} : n;
}}
function epIsBusinessSuccess(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}}
function epGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {{
    return d;
  }}
  return d;
}}
function epAssertEpassModuleRequired(data, ctx) {{
  pm.expect(data, ctx + ' data').to.be.an('object');
  pm.expect(data.module, ctx + ' module').to.eql(epExpectedModule());
}}
function epAssertEpassModuleIfPresent(data, ctx) {{
  if (!data || typeof data !== 'object') return;
  if (Object.prototype.hasOwnProperty.call(data, 'module')) {{
    pm.expect(data.module, ctx + ' module').to.eql(epExpectedModule());
  }}
}}
function epResolveEPassIdFromRoot(data) {{
  if (!data || typeof data !== 'object') return null;
  var direct = data.ePassId || data.epassId;
  if (direct) return direct;
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    return extra.ePassId || extra.epassId || null;
  }}
  return null;
}}
function epResolveEPassId(extra) {{
  if (!extra || typeof extra !== 'object') return null;
  return extra.ePassId || extra.epassId || null;
}}
function epResolveOptionId(data) {{
  if (!data || typeof data !== 'object') return null;
  var extra = data.extra;
  if (!extra || typeof extra !== 'object') return null;
  if (extra.localOfferOptions && typeof extra.localOfferOptions === 'object') {{
    return extra.localOfferOptions.optionId || null;
  }}
  if (Array.isArray(extra.localOfferOptions) && extra.localOfferOptions.length) {{
    return extra.localOfferOptions[0] && extra.localOfferOptions[0].optionId;
  }}
  if (extra.optionId) return extra.optionId;
  return null;
}}
var epOrderStatusActiveOrProcessing = [1, 5];
function epFailIfOrderStatus10(status, label) {{
  if (status === 10) {{
    pm.expect.fail(label + ': 订单 status=10 FAILED');
  }}
}}
function epExpectOrderStatusActiveOrProcessing(label, status) {{
  epFailIfOrderStatus10(status, label);
  pm.expect(epOrderStatusActiveOrProcessing, label + ' status').to.include(status);
}}
function epSyncResourceIdFromOrderResponse(label, actual) {{
  pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  var fromAvail = pm.collectionVariables.get('esimAvailabilityResourceId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': eSIM 订单 resourceId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（eSIM 以响应 canonical id 为准，已回写 esimResourceId）'
    );
  }}
  pm.collectionVariables.set('{esim_resource_var}', String(actual));
}}
function epExpectResourceIdMatch(label, actual) {{
  epSyncResourceIdFromOrderResponse(label, actual);
}}
function epSyncOptionIdFromOrderResponse(label, actual) {{
  if (!actual) {{
    console.warn(label + ': 响应未返回 optionId，跳过 esimOptionId 回写');
    return;
  }}
  pm.expect(actual, label + ' optionId 非空').to.be.a('string').and.not.empty;
  var fromAvail = pm.collectionVariables.get('esimAvailabilityOptionId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': eSIM 订单 optionId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（以响应为准，已回写 esimOptionId）'
    );
  }}
  pm.collectionVariables.set('{esim_option_var}', String(actual));
}}
function epExpectOptionIdMatch(label, actual) {{
  epSyncOptionIdFromOrderResponse(label, actual);
}}
function epSaveCreateIds(data) {{
  if (!data || typeof data !== 'object') return;
  if (data.clientUserId) pm.collectionVariables.set('clientUserId', String(data.clientUserId));
  if (data.orderId) pm.collectionVariables.set('purchaseOrderId', String(data.orderId));
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = epResolveEPassId(extra);
    if (ep) pm.collectionVariables.set('ePassId', String(ep));
  }}
}}
function epSaveAvailabilityRequestFields() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (reqBody && reqBody.prebookingDate) {{
      pm.collectionVariables.set('prebookingDate', String(reqBody.prebookingDate));
    }}
    if (reqBody && reqBody.resourceId) {{
      pm.collectionVariables.set('esimAvailabilityResourceId', String(reqBody.resourceId));
    }}
    if (reqBody && reqBody.optionId) {{
      pm.collectionVariables.set('esimAvailabilityOptionId', String(reqBody.optionId));
    }}
  }} catch (e) {{
    console.warn('epSaveAvailabilityRequestFields:', e);
  }}
}}
function epGetPollConfig() {{
  var maxAttempts = parseInt(pm.collectionVariables.get('esimPollMaxAttempts') || '40', 10);
  var intervalMs = parseInt(pm.collectionVariables.get('esimPollIntervalMs') || '3000', 10);
  return {{
    maxAttempts: isNaN(maxAttempts) ? 40 : maxAttempts,
    intervalMs: isNaN(intervalMs) ? 3000 : intervalMs
  }};
}}
function epPollAttemptVarName(orderIdVar) {{
  return 'esimPollAttempt_' + orderIdVar;
}}
function epGetPollAttempt(orderIdVar) {{
  var n = parseInt(pm.collectionVariables.get(epPollAttemptVarName(orderIdVar)) || '1', 10);
  return isNaN(n) || n < 1 ? 1 : n;
}}
function epClearPollAttempt(orderIdVar) {{
  pm.collectionVariables.unset(epPollAttemptVarName(orderIdVar));
}}
function epParseResponseJson(res) {{
  if (!res) return null;
  try {{
    if (typeof res.json === 'function') {{
      var parsed = res.json();
      if (parsed && typeof parsed === 'object') return parsed;
    }}
  }} catch (e1) {{}}
  try {{
    if (typeof res.text === 'function') {{
      var txt = res.text();
      if (txt && String(txt).trim()) return JSON.parse(String(txt));
    }}
  }} catch (e2) {{}}
  try {{
    if (typeof res.responseText === 'string' && res.responseText.trim()) {{
      return JSON.parse(res.responseText);
    }}
  }} catch (e3) {{}}
  return null;
}}
function epResolveOrderDataFromEnv(env) {{
  var data = epGetInnerData(env);
  if (!data || typeof data !== 'object' || Array.isArray(data)) return data;
  if (Object.prototype.hasOwnProperty.call(data, 'status')) return data;
  if (data.order && typeof data.order === 'object' && !Array.isArray(data.order)) {{
    return data.order;
  }}
  if (data.orderDetails && typeof data.orderDetails === 'object' && !Array.isArray(data.orderDetails)) {{
    return data.orderDetails;
  }}
  return data;
}}
function epDeepFindIccid(node, depth) {{
  depth = depth || 0;
  if (!node || typeof node !== 'object' || depth > 8) return null;
  if (Array.isArray(node)) {{
    for (var i = 0; i < node.length; i++) {{
      var hitArr = epDeepFindIccid(node[i], depth + 1);
      if (hitArr) return hitArr;
    }}
    return null;
  }}
  var keys = Object.keys(node);
  for (var j = 0; j < keys.length; j++) {{
    if (String(keys[j]).toLowerCase() === 'iccid') {{
      var val = node[keys[j]];
      if (val && String(val).trim()) return String(val).trim();
    }}
  }}
  for (var k = 0; k < keys.length; k++) {{
    var hitObj = epDeepFindIccid(node[keys[k]], depth + 1);
    if (hitObj) return hitObj;
  }}
  return null;
}}
function epGetPollRequestName(label) {{
  var cached = pm.collectionVariables.get('esimPollCurrentRequestName');
  if (cached && String(cached).trim()) return String(cached).trim();
  if (pm.info && pm.info.requestName) return pm.info.requestName;
  console.warn(label + ': 无法解析当前请求名（需前置脚本写入 esimPollCurrentRequestName）');
  return null;
}}
function epSetNextRequestSelf(label, delayMs) {{
  var reqName = epGetPollRequestName(label);
  if (!reqName) return false;
  var setter = (typeof postman !== 'undefined' && postman.setNextRequest)
    ? postman.setNextRequest.bind(postman)
    : (pm.execution && pm.execution.setNextRequest
      ? pm.execution.setNextRequest.bind(pm.execution)
      : null);
  if (!setter) return false;
  setTimeout(function () {{ setter(reqName); }}, delayMs);
  return true;
}}
function epBuildDetailsPollRequest(orderIdVar) {{
  var headers = {{}};
  if (pm.request && pm.request.headers && pm.request.headers.each) {{
    pm.request.headers.each(function (h) {{
      if (h && h.key && h.disabled !== true) {{
        headers[h.key] = pm.variables.replaceIn(String(h.value));
      }}
    }});
  }} else {{
    var token = pm.collectionVariables.get('accessToken');
    var programId = pm.collectionVariables.get('ProgramID');
    headers = {{
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'X-Program-ID': programId,
      'X-Request-ID': pm.variables.replaceIn('{{{{$guid}}}}')
    }};
    var xVersion = pm.collectionVariables.get('x-version');
    if (xVersion && String(xVersion).trim()) {{
      headers['x-version'] = String(xVersion);
    }}
  }}
  var url = '';
  if (pm.request && pm.request.url && pm.request.url.toString) {{
    url = pm.variables.replaceIn(pm.request.url.toString());
  }} else {{
    var baseUrl = pm.variables.replaceIn(String(pm.collectionVariables.get('baseUrl') || ''));
    url = baseUrl.replace(/[/]+$/, '') + '/v2/orders/ePasses/details';
  }}
  var orderId = pm.collectionVariables.get(orderIdVar);
  var rawBody = JSON.stringify({{ orderId: orderId }});
  var headerArr = [];
  Object.keys(headers).forEach(function (k) {{
    headerArr.push({{ key: k, value: headers[k] }});
  }});
  return {{
    url: url,
    method: 'POST',
    header: headerArr.length ? headerArr : headers,
    body: {{ mode: 'raw', raw: rawBody }}
  }};
}}
function epBuildUsageDetailsPollRequestFromCurrent() {{
  return epBuildDetailsPollRequest('usageOrderId');
}}
function epNormalizeOrderStatus(st) {{
  if (st === null || st === undefined) return null;
  var n = parseInt(String(st), 10);
  return isNaN(n) ? null : n;
}}
function epResponseHttpCode(res) {{
  if (!res) return 0;
  var raw = res.code;
  if (raw === undefined || raw === null) raw = res.status;
  if (raw === undefined || raw === null) raw = res.statusCode;
  if (raw === undefined || raw === null) raw = res.responseCode;
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? 0 : n;
}}
function epResponseOkForPoll(res, env) {{
  if (!env || typeof env !== 'object') return false;
  var httpCode = epResponseHttpCode(res);
  if (httpCode === 200) return epIsBusinessSuccess(env);
  // Apifox 等环境 pm.response.code 可能缺失，业务体成功则视为 HTTP 200
  if ((!httpCode || httpCode === 0) && epIsBusinessSuccess(env)) return true;
  // 详情接口已返回可解析订单体时也视为成功
  var data = epResolveOrderDataFromEnv(env);
  if ((!httpCode || httpCode === 0) && data && typeof data === 'object' && !Array.isArray(data)
      && Object.prototype.hasOwnProperty.call(data, 'status')) {{
    return true;
  }}
  return false;
}}
function epSoftSyncPollFields(data, orderIdVar) {{
  if (!data || typeof data !== 'object') return;
  if (data.orderId && orderIdVar) {{
    pm.collectionVariables.set(orderIdVar, String(data.orderId));
  }}
  if (data.extra && data.extra.resourceId) {{
    pm.collectionVariables.set('{esim_resource_var}', String(data.extra.resourceId));
  }}
  var opt = epResolveOptionId(data);
  if (opt) pm.collectionVariables.set('{esim_option_var}', String(opt));
  var iccid = epExtractIccidFromData(data);
  if (iccid) pm.collectionVariables.set('esimIccid', iccid);
}}
function epEvaluatePollBody(res, env, requireIccid) {{
  if (!env) {{
    return {{ action: 'retry', reason: '响应非 JSON' }};
  }}
  if (!epResponseOkForPoll(res, env)) {{
    return {{
      action: 'retry',
      reason: 'HTTP/业务未成功 http=' + epResponseHttpCode(res) + ' code=' + env.code
    }};
  }}
  var data = epResolveOrderDataFromEnv(env);
  if (!data || typeof data !== 'object' || Array.isArray(data)) {{
    return {{ action: 'retry', reason: 'data 非对象' }};
  }}
  var st = epNormalizeOrderStatus(data.status);
  if (st === 10) {{
    return {{ action: 'fail', reason: 'status=10 FAILED', data: data, st: st }};
  }}
  if (st === 1) {{
    if (requireIccid) {{
      var iccidReady = epIccidReadyFromDataOrCache(data);
      if (!iccidReady) {{
        return {{ action: 'retry', reason: 'status=1 但 iccid 未解析', data: data, st: st }};
      }}
    }}
    return {{ action: 'ok', data: data, st: st }};
  }}
  if (st === 5 || st === null) {{
    return {{ action: 'retry', reason: 'status=' + data.status + ' 处理中', data: data, st: st }};
  }}
  return {{ action: 'retry', reason: '未知 status=' + data.status, data: data, st: st }};
}}
function epPollOrderDetailsSendRequestFallback(label, orderIdVar, requireIccid, orderKind, startAttempt) {{
  pm.test(
    label + ': sendRequest 轮询 ' + orderKind + ' 详情（Apifox 无 setNextRequest 时）',
    function (done) {{
      var cfg = epGetPollConfig();
      function loop(attempt) {{
        setTimeout(function () {{
          pm.sendRequest(epBuildDetailsPollRequest(orderIdVar), function (err, res) {{
            if (err) {{
              if (attempt >= cfg.maxAttempts) {{ done(err); return; }}
              loop(attempt + 1);
              return;
            }}
            var env = epParseResponseJson(res);
            var verdict = epEvaluatePollBody(res, env, requireIccid);
            if (verdict.action === 'ok') {{
              epClearPollAttempt(orderIdVar);
              epSoftSyncPollFields(verdict.data, orderIdVar);
              console.log(label + ': sendRequest 第 ' + attempt + ' 次命中 status=1');
              done();
              return;
            }}
            if (verdict.action === 'fail') {{
              epClearPollAttempt(orderIdVar);
              done(new Error(label + ': ' + verdict.reason));
              return;
            }}
            if (attempt >= cfg.maxAttempts) {{
              epClearPollAttempt(orderIdVar);
              done(new Error(
                label + ': sendRequest ' + cfg.maxAttempts + ' 次内未达 status=1（'
                + verdict.reason + '）'
              ));
              return;
            }}
            console.log(label + ': sendRequest 第 ' + attempt + ' 次未满足（' + verdict.reason + '）');
            loop(attempt + 1);
          }});
        }}, cfg.intervalMs);
      }}
      loop(startAttempt);
    }}
  );
}}
function epExtractIccidFromData(data) {{
  if (!data || typeof data !== 'object') return null;
  function pickIccid(val) {{
    if (val && String(val).trim()) return String(val).trim();
    return null;
  }}
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var fromExtra = pickIccid(extra.iccid);
    if (fromExtra) return fromExtra;
    if (extra.esim && typeof extra.esim === 'object') {{
      var fromExtraEsim = pickIccid(extra.esim.iccid);
      if (fromExtraEsim) return fromExtraEsim;
    }}
  }}
  var fromRoot = pickIccid(data.iccid);
  if (fromRoot) return fromRoot;
  if (data.esim && typeof data.esim === 'object') {{
    var fromEsim = pickIccid(data.esim.iccid);
    if (fromEsim) return fromEsim;
  }}
  return epDeepFindIccid(data, 0);
}}
function epSaveIccidFromData(label, data) {{
  var iccid = epExtractIccidFromData(data);
  pm.expect(iccid, label + ' iccid 非空（Topup 前置）').to.be.a('string').and.not.empty;
  pm.collectionVariables.set('esimIccid', iccid);
}}
function epIccidReadyFromDataOrCache(data) {{
  var iccid = epExtractIccidFromData(data);
  if (iccid) return iccid;
  var cached = pm.collectionVariables.get('esimIccid');
  if (cached && String(cached).trim()) return String(cached).trim();
  return null;
}}
function epSyncPollSuccessFields(label, data, usageOrderId, ePassId) {{
  pm.expect(data.orderId).to.eql(usageOrderId);
  pm.expect(epResolveEPassIdFromRoot(data)).to.eql(ePassId);
  if (data.extra && data.extra.resourceId) {{
    pm.collectionVariables.set('{esim_resource_var}', String(data.extra.resourceId));
  }}
  var opt = epResolveOptionId(data);
  if (opt) {{
    pm.collectionVariables.set('{esim_option_var}', String(opt));
  }}
  var iccid = epExtractIccidFromData(data);
  if (iccid) {{
    pm.collectionVariables.set('esimIccid', iccid);
  }}
}}
function epSaveTopupToken(data) {{
  if (data && data.prebookingToken) {{
    pm.collectionVariables.set('topupToken', String(data.prebookingToken));
  }}
}}
function epAssertUsageDetailsReadyForTopup(label) {{
  var env = epParseResponseJson(pm.response);
  var data = epResolveOrderDataFromEnv(env);
  pm.test(label + ': status=1 CONFIRMED（Topup 前置）', function () {{
    pm.expect(data, 'details data').to.be.an('object');
    pm.expect(epNormalizeOrderStatus(data.status)).to.eql(1);
  }});
  pm.test(label + ': iccid 已就绪（Topup 前置）', function () {{
    var iccid = epExtractIccidFromData(data);
    if (iccid) {{
      pm.collectionVariables.set('esimIccid', iccid);
      return;
    }}
    var cached = pm.collectionVariables.get('esimIccid');
    if (cached && String(cached).trim()) {{
      console.warn(label + ': 本步响应 iccid 为空，沿用缓存 esimIccid');
      pm.expect(String(cached).trim()).to.not.be.empty;
      return;
    }}
    pm.expect.fail(label + ': iccid 仍为空；请检查 details 响应 extra.esim.iccid 等字段');
  }});
}}
function epAssertTopupAvailabilitySuccess(label) {{
  pm.test(label + ': available=true', function () {{
    pm.expect(epGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var respData = epGetInnerData(pm.response.json());
    pm.expect(respData.prebookingToken).to.be.a('string').and.not.empty;
    epSaveTopupToken(respData);
  }});
}}
function epAssertTopupOrderSuccess(label) {{
  var data = function () {{ return epGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=1 或 5（Topup 非 10 FAILED）', function () {{
    var st = epNormalizeOrderStatus(data().status);
    if (st === 10) {{
      pm.expect.fail('topup 单 status=10 FAILED');
    }}
    pm.expect(epOrderStatusActiveOrProcessing, label + ' status').to.include(st);
  }});
  pm.test(label + ': module=epassModule', function () {{ epAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('topupOrderId', String(data().orderId));
  }});
  pm.test(label + ': ePassId 一致', function () {{
    pm.expect(epResolveEPassIdFromRoot(data())).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': iccid 与 esimIccid 一致', function () {{
    pm.expect(epExtractIccidFromData(data())).to.eql(pm.collectionVariables.get('esimIccid'));
  }});
}}
function epPollOrderDetailsUntilStatus1(label, orderIdVar, requireIccid, orderKind) {{
  orderKind = orderKind || '订单';
  var cfg = epGetPollConfig();
  var attempt = epGetPollAttempt(orderIdVar);
  var expectedOrderId = pm.collectionVariables.get(orderIdVar);
  var env = epParseResponseJson(pm.response);
  var verdict = epEvaluatePollBody(pm.response, env, requireIccid);
  var data = verdict.data || epResolveOrderDataFromEnv(env);
  var httpCode = epResponseHttpCode(pm.response);

  function failPoll(msg) {{
    epClearPollAttempt(orderIdVar);
    pm.test(label + ': 轮询失败', function () {{
      pm.expect.fail(msg);
    }});
  }}

  function finishPollOk(stValue, pollData) {{
    epClearPollAttempt(orderIdVar);
    if (pollData) epSoftSyncPollFields(pollData, orderIdVar);
    pm.test(
      label + ': ' + orderKind + ' status=1 已确认'
      + (requireIccid ? ' 且 iccid 就绪' : '')
      + '（第 ' + attempt + ' 次）',
      function () {{
        pm.expect(stValue).to.eql(1);
        if (requireIccid && pollData) {{
          var iccidReady = epIccidReadyFromDataOrCache(pollData);
          pm.expect(iccidReady, 'iccid').to.be.a('string').and.not.empty;
          pm.collectionVariables.set('esimIccid', iccidReady);
        }}
      }}
    );
    console.log(label + ': 第 ' + attempt + ' 次命中 status=1');
  }}

  function retryPoll(reason) {{
    if (attempt >= cfg.maxAttempts) {{
      failPoll(
        label + ': ' + cfg.maxAttempts + ' 次轮询内未达 status=1'
        + '（' + reason + '；末次 status=' + (data && data.status) + ' http=' + httpCode + '）'
      );
      return;
    }}
    console.log(
      label + ': 第 ' + attempt + ' 次未满足（' + reason + '），'
      + cfg.intervalMs + 'ms 后重试'
    );
    pm.collectionVariables.set(epPollAttemptVarName(orderIdVar), String(attempt + 1));
    if (epSetNextRequestSelf(label, cfg.intervalMs)) {{
      pm.test(label + ': 轮询继续（第 ' + attempt + ' 次 · ' + reason + '）', function () {{
        pm.expect(true, 'setNextRequest 重试').to.be.true;
      }});
      return;
    }}
    console.warn(label + ': setNextRequest 不可用，改用 sendRequest 轮询（Apifox 兼容）');
    epPollOrderDetailsSendRequestFallback(
      label, orderIdVar, requireIccid, orderKind, attempt + 1
    );
  }}

  pm.test(label + ': ' + orderIdVar + ' 已设置', function () {{
    pm.expect(expectedOrderId, orderIdVar).to.be.ok;
  }});

  if (verdict.action === 'ok') {{
    finishPollOk(verdict.st, verdict.data);
    return;
  }}
  if (verdict.action === 'fail') {{
    failPoll(label + ': ' + orderKind + ' ' + verdict.reason);
    return;
  }}
  retryPoll(verdict.reason || '未达 status=1');
}}
function epPollEsimUsageOrderUntilConfirmed(label) {{
  // 对齐 pytest WaitForHistoricalEsimUsageOrderConfirmed：仅轮询 status=1；iccid 在 S03c 取
  epPollOrderDetailsUntilStatus1(label, 'usageOrderId', false, 'usage 预订单');
}}
function epPollTopupOrderUntilStatus1(label) {{
  epPollOrderDetailsUntilStatus1(label, 'topupOrderId', false, 'topup 单');
}}
function epGetCancelRetryConfig() {{
  var maxAttempts = parseInt(pm.collectionVariables.get('esimCancelMaxAttempts') || '5', 10);
  var intervalMs = parseInt(pm.collectionVariables.get('esimCancelRetryIntervalMs') || '2000', 10);
  return {{
    maxAttempts: isNaN(maxAttempts) ? 5 : maxAttempts,
    intervalMs: isNaN(intervalMs) ? 2000 : intervalMs
  }};
}}
function epIsCancelResponseSuccess(res, env) {{
  if (!res) return false;
  var httpCode = epResponseHttpCode(res);
  if (httpCode && httpCode !== 200) return false;
  if (!epIsBusinessSuccess(env)) return false;
  var msg = env && (env.msg || env.message);
  return msg === {cancel_msg_js};
}}
function epIsCancelResponseRetryable(env) {{
  if (!env || typeof env !== 'object') return false;
  var msg = String(env.msg || env.message || '');
  if (msg.indexOf({cancel_retry_needle_js}) >= 0) return true;
  if (env.errCode === '500.041.006' || env.errCode === '500.071.016') return true;
  return false;
}}
function epBuildCancelOrderRequest(orderId) {{
  var headers = {{}};
  if (pm.request && pm.request.headers && pm.request.headers.each) {{
    pm.request.headers.each(function (h) {{
      if (h && h.key && h.disabled !== true) {{
        headers[h.key] = pm.variables.replaceIn(String(h.value));
      }}
    }});
  }} else {{
    var token = pm.collectionVariables.get('accessToken');
    var programId = pm.collectionVariables.get('ProgramID');
    headers = {{
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token,
      'X-Program-ID': programId,
      'X-Request-ID': pm.variables.replaceIn('{{{{$guid}}}}')
    }};
    var xVersion = pm.collectionVariables.get('x-version');
    if (xVersion && String(xVersion).trim()) {{
      headers['x-version'] = String(xVersion);
    }}
  }}
  var url = '';
  if (pm.request && pm.request.url && pm.request.url.toString) {{
    url = pm.variables.replaceIn(pm.request.url.toString());
  }} else {{
    var baseUrl = pm.variables.replaceIn(String(pm.collectionVariables.get('baseUrl') || ''));
    url = baseUrl.replace(/[/]+$/, '') + '/v2/orders';
  }}
  return {{
    url: url,
    method: 'PATCH',
    header: (function () {{
      var headerArr = [];
      Object.keys(headers).forEach(function (k) {{
        headerArr.push({{ key: k, value: headers[k] }});
      }});
      return headerArr.length ? headerArr : headers;
    }})(),
    body: {{ mode: 'raw', raw: JSON.stringify({{ status: 3, orderId: orderId }}) }}
  }};
}}
function epCancelOrderWithRetry(label, orderIdVar) {{
  pm.test(label + ': 取消订单（Order cancellation failed 自动重试）', function (done) {{
    var orderId = pm.collectionVariables.get(orderIdVar);
    pm.expect(orderId, orderIdVar).to.be.ok;
    var cfg = epGetCancelRetryConfig();
    function finishSuccess(res, env) {{
      pm.expect(epResponseHttpCode(res)).to.eql(200);
      pm.expect(env.code).to.eql(0);
      pm.expect(env.msg || env.message).to.eql({cancel_msg_js});
      done();
    }}
    function sendCancel(attempt) {{
      setTimeout(function () {{
        pm.sendRequest(epBuildCancelOrderRequest(orderId), function (err, res) {{
          if (err) {{
            if (attempt >= cfg.maxAttempts) {{ done(err); return; }}
            sendCancel(attempt + 1);
            return;
          }}
          var env = epParseResponseJson(res);
          if (epIsCancelResponseSuccess(res, env)) {{
            finishSuccess(res, env);
            return;
          }}
          if (epIsCancelResponseRetryable(env) && attempt < cfg.maxAttempts) {{
            console.warn(label + ': 第 ' + attempt + ' 次取消失败，' + cfg.intervalMs + 'ms 后重试: ' + JSON.stringify(env));
            sendCancel(attempt + 1);
            return;
          }}
          done(new Error(
            label + ': 取消失败 http=' + epResponseHttpCode(res) + ' env=' + JSON.stringify(env)
          ));
        }});
      }}, cfg.intervalMs);
    }}
    var env0 = epParseResponseJson(pm.response);
    if (epIsCancelResponseSuccess(pm.response, env0)) {{
      finishSuccess(pm.response, env0);
      return;
    }}
    if (epIsCancelResponseRetryable(env0)) {{
      console.warn(label + ': 本步取消可重试: ' + JSON.stringify(env0));
      sendCancel(2);
      return;
    }}
    done(new Error(label + ': 取消失败 env=' + JSON.stringify(env0)));
  }});
}}
function epResolveListItemField(item, rootKey, extraKey) {{
  if (!item || typeof item !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(item, rootKey)) return item[rootKey];
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, extraKey)) return ex[extraKey];
    if (Object.prototype.hasOwnProperty.call(ex, rootKey)) return ex[rootKey];
  }}
  return null;
}}
function epResolveTransportHubName(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubName')) {{
    return ex.transportHubName;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubName')) return item.transportHubName;
  return undefined;
}}
function epResolveTransportHubId(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubId')) {{
    return ex.transportHubId;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubId')) return item.transportHubId;
  return undefined;
}}
function epSavePrebookingToken(data) {{
  if (data && data.prebookingToken) {{
    pm.collectionVariables.set('prebookingToken', String(data.prebookingToken));
  }}
}}
function epSaveUsageOrderId(data) {{
  if (data && data.orderId) {{
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }}
}}
function epAssertHttpBusinessOk(label) {{
  pm.test(label + ': HTTP 200 且业务成功', function () {{
    pm.response.to.have.status(200);
    pm.expect(epIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
}}
function epAssertCancelOrderSuccess(label) {{
  pm.test(label + ': HTTP 200', function () {{
    pm.response.to.have.status(200);
  }});
  pm.test(label + ': code=0 取消业务成功', function () {{
    var env = pm.response.json();
    pm.expect(env && env.code, 'code').to.eql(0);
  }});
  pm.test(label + ': msg=The order was cancelled successfully', function () {{
    var env = pm.response.json();
    var msg = env && (env.msg || env.message);
    pm.expect(msg, '取消响应 msg').to.eql({cancel_msg_js});
  }});
}}
function epExpectedCreateExtra() {{
  return {{
    firstName: {create_first_name_js},
    lastName: {create_last_name_js},
    expirationDate: {create_expiration_date_js},
    availableUsages: {create_available_usages_js}
  }};
}}
function epAssertExtraMatchesCreateInput(label, extra) {{
  pm.test(label + ': extra.firstName 与入参一致', function () {{
    pm.expect(extra.firstName).to.eql(epExpectedCreateExtra().firstName);
  }});
  pm.test(label + ': extra.lastName 与入参一致', function () {{
    pm.expect(extra.lastName).to.eql(epExpectedCreateExtra().lastName);
  }});
  pm.test(label + ': extra.expirationDate 与入参一致', function () {{
    pm.expect(extra.expirationDate).to.eql(epExpectedCreateExtra().expirationDate);
  }});
  pm.test(label + ': extra.availableUsages 与入参一致', function () {{
    pm.expect(extra.availableUsages).to.eql(epExpectedCreateExtra().availableUsages);
  }});
}}
function epAssertCreateCoreFields(label) {{
  var dataFn = function () {{ return epGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    epAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': category=2 或 3', function () {{
    pm.expect([2, 3]).to.include(dataFn().category);
  }});
  pm.test(label + ': clientUserId 回显一致', function () {{
    pm.expect(dataFn().clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': orderCancelledDate=null', function () {{
    pm.expect(dataFn().orderCancelledDate).to.eql(null);
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.usedUsages=0', function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(0);
  }});
  epAssertExtraMatchesCreateInput(label, dataFn().extra);
  pm.test(label + ': extra.ePassId 非空', function () {{
    pm.expect(epResolveEPassId(dataFn().extra)).to.be.ok;
  }});
  pm.test(label + ': extra.allowedResources 存在', function () {{
    pm.expect(dataFn().extra.allowedResources).to.be.an('object');
  }});
  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {{
    epSaveCreateIds(dataFn());
    pm.expect(pm.collectionVariables.get('ePassId')).to.be.ok;
    pm.expect(pm.collectionVariables.get('purchaseOrderId')).to.be.ok;
  }});
}}
function epAssertUserListContains(label) {{
  pm.test(label + ': ePassesList 含 ePassId', function () {{
    var data = epGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    pm.expect(data.ePassesList).to.be.an('array');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    pm.expect(hit.length, '未找到 ePassId=' + target).to.be.above(0);
  }});
  pm.test(label + ': 列表项 module=epassModule（若存在）', function () {{
    var data = epGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    if (hit[0] && Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(epExpectedModule());
    }}
  }});
}}
function epAssertSearchPurchaseDetails(label, assertEpassModule, matchCreateInput, expectedStatus, expectedUsedUsages) {{
  var dataFn = function () {{ return epGetInnerData(pm.response.json()); }};
  var status = (expectedStatus !== undefined && expectedStatus !== null) ? expectedStatus : 1;
  var usedUsages = (expectedUsedUsages !== undefined && expectedUsedUsages !== null) ? expectedUsedUsages : 0;
  if (assertEpassModule !== false) {{
    pm.test(label + ': module=epassModule', function () {{
      epAssertEpassModuleRequired(dataFn(), label);
    }});
  }}
  pm.test(label + ': category=2', function () {{
    pm.expect(dataFn().category).to.eql(2);
  }});
  pm.test(label + ': status=' + status, function () {{
    pm.expect(dataFn().status).to.eql(status);
  }});
  pm.test(label + ': orderCancelledDate=null', function () {{
    pm.expect(dataFn().orderCancelledDate).to.eql(null);
  }});
  pm.test(label + ': clientUserId 与注册一致', function () {{
    pm.expect(dataFn().clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    var actual = dataFn().orderId;
    var previous = pm.collectionVariables.get('purchaseOrderId');
    var usage = pm.collectionVariables.get('usageOrderId');
    pm.expect(actual).to.be.a('string').and.not.empty;
    if (previous && previous !== usage) {{
      pm.expect(actual).to.eql(previous);
    }} else {{
      pm.collectionVariables.set('purchaseOrderId', String(actual));
    }}
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(epResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.usedUsages=' + usedUsages, function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(usedUsages);
  }});
  if (matchCreateInput !== false) {{
    epAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function epAssertOrderListPagination(label, allowEmpty, expectEpassModule) {{
  pm.test(label + ': pagination 结构', function () {{
    var data = epGetInnerData(pm.response.json());
    pm.expect(data.pagination).to.be.an('object');
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {{
      pm.expect(data.pagination, 'pagination.' + k).to.have.property(k);
    }});
  }});
  pm.test(label + ': orders 为数组', function () {{
    pm.expect(epGetInnerData(pm.response.json()).orders).to.be.an('array');
  }});
  if (allowEmpty) {{
    pm.test(label + ': 创建后 orders 可为空（canary doc gap）', function () {{
      pm.expect(epGetInnerData(pm.response.json()).orders).to.be.an('array');
    }});
  }}
  if (expectEpassModule) {{
    pm.test(label + ': 列表项 module=epassModule（若存在 module 字段）', function () {{
      var orders = epGetInnerData(pm.response.json()).orders || [];
      var mod = epExpectedModule();
      orders.forEach(function (item, idx) {{
        if (item && Object.prototype.hasOwnProperty.call(item, 'module')) {{
          pm.expect(item.module, 'orders[' + idx + '].module').to.eql(mod);
        }}
      }});
    }});
  }}
}}
function epAssertAvailabilitySuccess(label) {{
  epSaveAvailabilityRequestFields();
  pm.test(label + ': available=true', function () {{
    pm.expect(epGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var data = epGetInnerData(pm.response.json());
    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;
    epSavePrebookingToken(data);
  }});
}}
function epAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {{
  allowedStatuses = allowedStatuses || epOrderStatusActiveOrProcessing;
  var data = function () {{ return epGetInnerData(pm.response.json()); }};
  var statusLabel = (allowedStatuses.indexOf(5) >= 0)
    ? 'status=1 或 5（CONFIRMED/处理中，非 10 FAILED）'
    : 'status=1 CONFIRMED（非 10 FAILED）';
  pm.test(label + ': ' + statusLabel, function () {{
    var st = data().status;
    if (st === 10) {{
      pm.expect.fail('预约单 status=10 FAILED');
    }}
    pm.expect(allowedStatuses).to.include(st);
  }});
  pm.test(label + ': module=epassModule', function () {{ epAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    epSaveUsageOrderId(data());
  }});
  pm.test(label + ': clientUserId 与注册会籍一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': ePassId 与前面一致', function () {{
    var ep = epResolveEPassIdFromRoot(data());
    pm.expect(ep).to.be.a('string').and.not.empty;
    if (requireExistingEPassId) {{
      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));
    }} else {{
      pm.collectionVariables.set('ePassId', String(ep));
    }}
  }});
  pm.test(label + ': orderCancelledDate=null', function () {{
    pm.expect(data().orderCancelledDate).to.eql(null);
  }});
  pm.test(label + ': extra.usageDate=null', function () {{
    pm.expect(data().extra.usageDate).to.eql(null);
  }});
  pm.test(label + ': extra.usedUsages=1', function () {{
    pm.expect(data().extra.usedUsages).to.eql(1);
  }});
  pm.test(label + ': extra.prebookingDate 与可用性入参一致', function () {{
    var expected = pm.collectionVariables.get('prebookingDate');
    var actual = data().extra.prebookingDate;
    pm.expect(actual).to.be.a('string').and.not.empty;
    if (expected && String(expected).trim()) {{
      pm.expect(actual).to.eql(expected);
    }}
  }});
  pm.test(label + ': extra.resourceId 与 resourceId 一致', function () {{
    epExpectResourceIdMatch(label, data().extra.resourceId);
  }});
  pm.test(label + ': optionId 一致', function () {{
    epExpectOptionIdMatch(label, epResolveOptionId(data()));
  }});
}}
function epAssertUsageOrderListItemCore(label, item) {{
  pm.expect(item.category, label + ' category').to.eql(2);
  pm.expect(item.module, label + ' module').to.eql(epExpectedModule());
  var rid = epResolveListItemField(item, 'resourceId', 'resourceId');
  pm.expect(rid, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  epExpectResourceIdMatch(label, rid);
  var opt = epResolveOptionId(item);
  pm.expect(opt, label + ' optionId 非空').to.be.a('string').and.not.empty;
  epExpectOptionIdMatch(label, opt);
  pm.expect(epResolveTransportHubName(item), label + ' transportHubName').to.eql(null);
  pm.expect(epResolveTransportHubId(item), label + ' transportHubId').to.eql(null);
}}
function epAssertUsageOrderInListActive(label) {{
  pm.test(label + ': HTTP 200 且业务成功', function () {{
    pm.response.to.have.status(200);
    pm.expect(epIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
  epAssertOrderListPagination(label, false, true);
  epAssertNoOtherModuleInEpassList(label);
  pm.test(label + ': orders 含 usageOrderId 且 status=1', function () {{
    var data = epGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    pm.expect(data.orders.length, 'orders 不应为空').to.be.above(0);
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usageOrderId=' + oid).to.be.above(0);
    var item = hit[0];
    pm.expect(item.status).to.eql(1);
    epAssertUsageOrderListItemCore(label, item);
    if (Object.prototype.hasOwnProperty.call(item, 'orderCancelledDate')) {{
      pm.expect(item.orderCancelledDate).to.eql(null);
    }}
    var used = epResolveListItemField(item, 'usedUsages', 'usedUsages');
    pm.expect(used, label + ' usedUsages').to.eql(1);
    var usageDate = epResolveListItemField(item, 'usageDate', 'usageDate');
    if (usageDate !== undefined) {{
      pm.expect(usageDate).to.eql(null);
    }}
    var ep = epResolveEPassIdFromRoot(item);
    if (ep) {{
      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));
    }}
    var cid = epResolveListItemField(item, 'clientUserId', 'clientUserId');
    if (cid) {{
      pm.expect(cid).to.eql(pm.collectionVariables.get('clientUserId'));
    }}
  }});
}}
function epAssertPrebookingOrderSuccess(label) {{
  epAssertUsageOrderCreateSuccess(label, true);
}}
function epAssertBundleOrderSuccess(label) {{
  epAssertUsageOrderCreateSuccess(label, false);
  pm.test(label + ': 写入 usageOrderId', function () {{
    pm.expect(pm.collectionVariables.get('usageOrderId')).to.be.ok;
  }});
}}
function epAssertUsageDetailsCore(label, expectCancelled) {{
  var data = function () {{ return epGetInnerData(pm.response.json()); }};
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {{
    pm.expect(data().orderId).to.eql(pm.collectionVariables.get('usageOrderId'));
  }});
  pm.test(label + ': module=epassModule', function () {{ epAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': extra.usedUsages=1', function () {{ pm.expect(data().extra.usedUsages).to.eql(1); }});
  pm.test(label + ': extra.usageDate=null', function () {{ pm.expect(data().extra.usageDate).to.eql(null); }});
  pm.test(label + ': ePassId 一致', function () {{
    pm.expect(epResolveEPassIdFromRoot(data())).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.clientUserId 一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': extra.resourceId 一致', function () {{
    pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get('{esim_resource_var}'));
  }});
  if (expectCancelled) {{
    pm.test(label + ': status=3 CANCELLED', function () {{ pm.expect(data().status).to.eql(3); }});
    pm.test(label + ': orderCancelledDate 有值', function () {{
      pm.expect(data().orderCancelledDate).to.not.eql(null);
      pm.expect(data().orderCancelledDate).to.be.a('string').and.not.empty;
    }});
  }} else {{
    pm.test(label + ': status=1 CONFIRMED（轮询后）', function () {{
      pm.expect(data().status).to.eql(1);
    }});
    pm.test(label + ': orderCancelledDate=null', function () {{
      pm.expect(data().orderCancelledDate).to.eql(null);
    }});
  }}
}}
function epAssertNoOtherModuleInEpassList(label) {{
  pm.test(label + ': module=epassModule 列表不含 otherModule 数据', function () {{
    pm.response.to.have.status(200);
    var data = epGetInnerData(pm.response.json());
    if (!data || typeof data !== 'object') return;
    if (!Array.isArray(data.orders)) return;
    var other = epOtherModule();
    var hits = data.orders.filter(function (o) {{ return o && o.module === other; }});
    pm.expect(hits.length, 'epassModule orders 不应含 otherModule=' + other + ' 条目').to.eql(0);
  }});
}}
function epAssertNoEsimReturnedWithOtherModuleFilter(label) {{
  pm.test(label + ': otherModule 不返回 eSIM 数据', function () {{
    pm.response.to.have.status(200);
    var env = pm.response.json();
    if (env && env.code === -1) {{
      console.warn(label + ': otherModule 返回业务失败，视为隔离通过 errCode=' + env.errCode);
      return;
    }}
    pm.expect(epIsBusinessSuccess(env), label + ' business success 或 code=-1').to.be.true;
    var data = epGetInnerData(env);
    if (data === null || data === undefined) return;
    if (typeof data !== 'object') return;
    var expectedUsage = pm.collectionVariables.get('usageOrderId');
    var expectedPurchase = pm.collectionVariables.get('purchaseOrderId');
    var expectedEPass = pm.collectionVariables.get('ePassId');
    var esimMod = epExpectedModule();
    if (Array.isArray(data.orders)) {{
      if (expectedUsage) {{
        var sameUsage = data.orders.filter(function (o) {{
          return o && o.orderId === expectedUsage;
        }});
        pm.expect(sameUsage.length, 'otherModule orders 不应含 usageOrderId').to.eql(0);
      }}
      if (expectedPurchase) {{
        var samePurchase = data.orders.filter(function (o) {{
          return o && o.orderId === expectedPurchase;
        }});
        pm.expect(samePurchase.length, 'otherModule orders 不应含 purchaseOrderId').to.eql(0);
      }}
      var esimItems = data.orders.filter(function (o) {{ return o && o.module === esimMod; }});
      pm.expect(esimItems.length, 'otherModule orders 不应含 epassModule 条目').to.eql(0);
      return;
    }}
    pm.expect(data.module, 'otherModule details 不应返回 epassModule').to.not.eql(esimMod);
    if (expectedUsage && data.orderId) {{
      pm.expect(data.orderId, 'otherModule details 不应返回 eSIM usageOrderId').to.not.eql(expectedUsage);
    }}
    var ep = epResolveEPassIdFromRoot(data);
    if (expectedEPass && ep && data.module === esimMod) {{
      pm.expect(ep, 'otherModule details 不应返回 eSIM ePassId').to.not.eql(expectedEPass);
    }}
  }});
}}
function epAssertUsageListContainsCancelled(label) {{
  pm.test(label + ': orders 含 usageOrderId 且 status=3', function () {{
    var data = epGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    if (!data.orders.length) {{
      console.warn('orders 为空（canary 索引延迟），跳过取消态断言');
      return;
    }}
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usage orderId=' + oid).to.be.above(0);
    pm.expect(hit[0].status).to.eql(3);
    if (Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(epExpectedModule());
    }}
  }});
}}
function epAssertSearchActiveAfterUsageCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return epGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    epAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED（MS 单未取消）', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': purchaseOrderId 仍可查', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(epResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    epAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function epAssertSearchCancelledAfterPurchaseCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return epGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=3 CANCELLED', function () {{
    pm.expect(dataFn().status).to.eql(3);
  }});
  pm.test(label + ': extra.ePassStatus=3 Cancelled', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(3);
  }});
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(epResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    epAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
""".strip()
    # Apifox 内 {{$guid}} 常未展开 → 空 X-Request-ID → 301.000.001；sendRequest 回退头改用本地 UUID
    js = js.replace("pm.variables.replaceIn('{{$guid}}')", JsExpr_FreshRequestId())
    return [ln for ln in js.split("\n")]


def Lines_Auth() -> List[str]:
    return [
        "epAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 写入集合变量', function () {",
        "  var d = epGetInnerData(pm.response.json());",
        "  var t = (d && (d.accessToken || d.token || d.access_token));",
        "  pm.expect(t).to.be.ok;",
        "  pm.expect(pm.collectionVariables.get('accessToken')).to.be.ok;",
        "});",
    ]


def AvailabilityBody(*, with_epass: bool) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{esimResourceId}}",
        "optionId": "{{esimOptionId}}",
        "prebookingDate": PREBOOKING_DATE_APIFOX,
        "adultCount": 1,
        "childCount": 0,
    }
    if with_epass:
        body["ePassId"] = "{{ePassId}}"
    return json.dumps(body, ensure_ascii=False, indent=2)


def OrdersListBodyNative() -> str:
    return json.dumps(
        {"ePassId": "{{ePassId}}", "module": EPASS_MODULE_DEFAULT, "pageSize": 10, "pageNumber": 1},
        ensure_ascii=False,
        indent=2,
    )


def OrdersListBodyOtherModule() -> str:
    return json.dumps(
        {"ePassId": "{{ePassId}}", "module": OTHER_MODULE_DEFAULT, "pageSize": 10, "pageNumber": 1},
        ensure_ascii=False,
        indent=2,
    )


def UsageDetailsBody() -> str:
    return OrderDetailsBody("usageOrderId")


def OrderDetailsBody(order_id_var: str) -> str:
    return json.dumps({"orderId": "{{" + order_id_var + "}}"}, ensure_ascii=False, indent=2)


def CancelOrderBody(order_id_var: str) -> str:
    return json.dumps(
        {"status": 3, "orderId": "{{" + order_id_var + "}}"},
        ensure_ascii=False,
        indent=2,
    )


def TopupAvailabilityBody() -> str:
    return json.dumps(
        {
            "ePassId": "{{ePassId}}",
            "module": EPASS_MODULE_DEFAULT,
            "resourceId": "{{esimResourceId}}",
            "optionId": "{{esimOptionId}}",
            "prebookingDate": PREBOOKING_DATE_APIFOX,
            "iccid": "{{esimIccid}}",
            "adultCount": 1,
            "childCount": 0,
        },
        ensure_ascii=False,
        indent=2,
    )


def TopupOrderBody() -> str:
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "ePassId": "{{ePassId}}",
            "extra": {
                "prebookingToken": "{{topupToken}}",
                "iccid": "{{esimIccid}}",
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def Prerequest_SavePollRequestName() -> List[str]:
    """轮询步骤前置：缓存完整请求名，供 setNextRequest 精确重跑（勿用 step_code 短名）。"""
    return [
        "if (pm.info && pm.info.requestName) {",
        "  pm.collectionVariables.set('esimPollCurrentRequestName', pm.info.requestName);",
        "}",
    ]


def BuildPollBeforeCancelUsageStep(js: Callable[[], List[str]], step_code: str) -> RequestItem:
    """prebooking/bundle usage 单取消前轮询 status=1。"""
    return RequestItem(
        js_helpers=js,
        name=f"{step_code} 轮询 usage 详情 status=1（取消前置）",
        method="POST",
        url_path="/v2/orders/ePasses/details",
        body=UsageDetailsBody(),
        headers=BearerJsonHeaders(),
        description="取消 usage 预订单前确认 status=1（eSIM 异步落单）。",
        prerequest_lines=Prerequest_SavePollRequestName(),
        test_lines=Lines_Step(
            step_code,
            [f"epPollOrderDetailsUntilStatus1('{step_code}', 'usageOrderId', false, 'usage 预订单');"],
        ),
    )


def BuildTopupStepsAfterPoll(
    js: Callable[[], List[str]],
    *,
    step_prefix: str,
) -> List[RequestItem]:
    """prebooking/bundle 轮询 status=1 后：取 iccid → topup → 轮询 topup status=1 → 取消 topup。"""
    c, d, e, f, g = (
        f"{step_prefix}c",
        f"{step_prefix}d",
        f"{step_prefix}e",
        f"{step_prefix}f",
        f"{step_prefix}g",
    )
    return [
        RequestItem(
            js_helpers=js,
            name=f"{step_prefix}c POST /v2/orders/ePasses/details（status=1 后取 iccid · Topup 前置）",
            method="POST",
            url_path="/v2/orders/ePasses/details",
            body=UsageDetailsBody(),
            headers=BearerJsonHeaders(),
            description="``RunHistoricalEsimTopupMainE2EScenario`` · 从 usage 详情解析 iccid。",
            test_lines=Lines_Step(
                c,
                [
                    f"epAssertHttpBusinessOk('{c}');",
                    f"epAssertUsageDetailsReadyForTopup('{c}');",
                ],
            ),
        ),
        RequestItem(
            js_helpers=js,
            name=f"{step_prefix}d POST /v2/orders/esims/topup/availability",
            method="POST",
            url_path="/v2/orders/esims/topup/availability",
            body=TopupAvailabilityBody(),
            headers=BearerJsonHeaders(),
            description="``PostEsimTopupAvailability`` · prebookingDate Apifox +10天 10:30",
            prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
            test_lines=Lines_Step(
                d,
                [f"epAssertHttpBusinessOk('{d}');", f"epAssertTopupAvailabilitySuccess('{d}');"],
            ),
        ),
        RequestItem(
            js_helpers=js,
            name=f"{step_prefix}e POST /v2/orders/esims/ePasses/topup",
            method="POST",
            url_path="/v2/orders/esims/ePasses/topup",
            body=TopupOrderBody(),
            headers=BearerJsonHeaders(),
            description="``PostEsimEpassTopup`` · status=1 或 5",
            test_lines=Lines_Step(
                e,
                [
                    f"epClearPollAttempt('topupOrderId');",
                    f"epAssertHttpBusinessOk('{e}');",
                    f"epAssertTopupOrderSuccess('{e}');",
                ],
            ),
        ),
        RequestItem(
            js_helpers=js,
            name=f"{f} 轮询 topup 详情 status=1（取消前置）",
            method="POST",
            url_path="/v2/orders/ePasses/details",
            body=OrderDetailsBody("topupOrderId"),
            headers=BearerJsonHeaders(),
            description="Topup 下单后轮询 status=1，再 PATCH 取消（对齐 usage 预订单轮询）。",
            prerequest_lines=Prerequest_SavePollRequestName(),
            test_lines=Lines_Step(f, [f"epPollTopupOrderUntilStatus1('{f}');"]),
        ),
        RequestItem(
            js_helpers=js,
            name=f"{g} PATCH /v2/orders（取消 topup 单 · 失败重试）",
            method="PATCH",
            url_path="/v2/orders",
            body=CancelOrderBody("topupOrderId"),
            headers=BearerJsonHeaders(),
            description="``PatchCancelOrderWithRetry`` · msg 含 Order cancellation failed 时自动重试。",
            test_lines=Lines_Step(g, [f"epCancelOrderWithRetry('{g}', 'topupOrderId');"]),
        ),
    ]


def Prerequest_SyncPrebookingDateFromApifox() -> List[str]:
    return [
        "var pb = pm.variables.replaceIn(" + json.dumps(PREBOOKING_DATE_APIFOX) + ");",
        "pm.collectionVariables.set('prebookingDate', pb);",
    ]


def Prerequest_NewClientUserId() -> List[str]:
    return [
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
    ]


def Prerequest_ResetForPrebooking() -> List[str]:
    return [
        *Prerequest_SyncPrebookingDateFromApifox(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
        "pm.collectionVariables.set('esimIccid', '');",
        "pm.collectionVariables.set('topupToken', '');",
        "pm.collectionVariables.set('topupOrderId', '');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        *Prerequest_SyncPrebookingDateFromApifox(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
        "pm.collectionVariables.set('esimIccid', '');",
        "pm.collectionVariables.set('topupToken', '');",
        "pm.collectionVariables.set('topupOrderId', '');",
    ]


def BuildCreateE2EFolder() -> JsonObject:
    js = BuildEsimJsHelpersLines
    return Folder(
        "E01 · tc-P0 创建",
        [
            RequestItem(
                js_helpers=js,
                name="E01-S01 POST /v2/orders/esims/ePasses",
                method="POST",
                url_path="/v2/orders/esims/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassCreateCoreFields`` · ``ExtractCreateEpassIds``",
                prerequest_lines=Prerequest_NewClientUserId(),
                test_lines=Lines_Step(
                    "E01-S01",
                    ["epAssertHttpBusinessOk('E01-S01');", "epAssertCreateCoreFields('E01-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S02 POST /v2/users/ePasses",
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E01-S02",
                    ["epAssertHttpBusinessOk('E01-S02');", "epAssertUserListContains('E01-S02');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S03 POST /v2/orders/ePasses/search（orderId）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by orderId · status=1 usedUsages=0",
                test_lines=Lines_Step(
                    "E01-S03",
                    ["epAssertHttpBusinessOk('E01-S03');", "epAssertSearchPurchaseDetails('E01-S03', true);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S04 POST /v2/orders/ePasses/search（ePassId）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E01-S04",
                    ["epAssertHttpBusinessOk('E01-S04');", "epAssertSearchPurchaseDetails('E01-S04', true);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S05 POST /v2/orders/ePasses（module=8 · usage 列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``PostOrdersEPassesList`` · 创建后 orders 可能为空",
                test_lines=Lines_Step(
                    "E01-S05",
                    [
                        "epAssertHttpBusinessOk('E01-S05');",
                        "epAssertOrderListPagination('E01-S05', true, true);",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-I06 POST /v2/orders/ePasses（otherModule=11 隔离 · 取消前）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter`` · 取消 MS 前",
                test_lines=Lines_Step("E01-I06", ["epAssertNoEsimReturnedWithOtherModuleFilter('E01-I06');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-I07 POST /v2/orders/ePasses（module=8 原生 · 取消前）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · 取消 MS 前",
                test_lines=Lines_Step(
                    "E01-I07",
                    ["epAssertHttpBusinessOk('E01-I07');", "epAssertNoOtherModuleInEpassList('E01-I07');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S06 PATCH /v2/orders（取消 MS 购买单）",
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalCancelOrderSuccess``",
                test_lines=Lines_Step("E01-S06", ["epCancelOrderWithRetry('E01-S06', 'purchaseOrderId');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-I08 POST /v2/orders/ePasses（otherModule=11 隔离 · 取消后）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter`` · 取消 MS 后",
                test_lines=Lines_Step("E01-I08", ["epAssertNoEsimReturnedWithOtherModuleFilter('E01-I08');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-I09 POST /v2/orders/ePasses（module=8 原生 · 取消后）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · 取消 MS 后",
                test_lines=Lines_Step(
                    "E01-I09",
                    ["epAssertHttpBusinessOk('E01-I09');", "epAssertNoOtherModuleInEpassList('E01-I09');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S07 POST /v2/orders/ePasses（取消后列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertOrderListPaginationShape``",
                test_lines=Lines_Step(
                    "E01-S07",
                    [
                        "epAssertHttpBusinessOk('E01-S07');",
                        "epAssertOrderListPagination('E01-S07', true, true);",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E01-S08 POST /v2/orders/ePasses/search（取消后 ePassId）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E01-S08",
                    [
                        "epAssertHttpBusinessOk('E01-S08');",
                        "epAssertSearchCancelledAfterPurchaseCancel('E01-S08');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpassEsim_E2E_CreateMainChain`` · "
            "``RunHistoricalEpassCreateMainE2EScenario(catalog_label='esim')``"
        ),
    )


def BuildPrebookingE2EFolder() -> JsonObject:
    js = BuildEsimJsHelpersLines
    return Folder(
        "E02 · tc-P0 预约",
        [
            RequestItem(
                js_helpers=js,
                name="E02-S01 POST /v2/orders/esims/ePasses",
                method="POST",
                url_path="/v2/orders/esims/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="Prebooking 前置：创建 ePass",
                prerequest_lines=Prerequest_ResetForPrebooking(),
                test_lines=Lines_Step(
                    "E02-S01",
                    ["epAssertHttpBusinessOk('E02-S01');", "epAssertCreateCoreFields('E02-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S02 POST /v2/resources/options/prebookings/availability（有 ePassId · module=8）",
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=True),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingToken`` · prebookingDate Apifox +10天 10:30",
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
                test_lines=Lines_Step(
                    "E02-S02",
                    ["epAssertHttpBusinessOk('E02-S02');", "epAssertAvailabilitySuccess('E02-S02');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S03 POST /v2/orders/esims/ePasses/prebooking",
                method="POST",
                url_path="/v2/orders/esims/ePasses/prebooking",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "ePassId": "{{ePassId}}",
                        "extra": {"prebookingToken": "{{prebookingToken}}"},
                        "async": False,
                    },
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertEsimPrebookingOrderSuccess``",
                test_lines=Lines_Step(
                    "E02-S03",
                    [
                        "epClearPollAttempt('usageOrderId');",
                        "epAssertHttpBusinessOk('E02-S03');",
                        "epAssertPrebookingOrderSuccess('E02-S03');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S03b 轮询 usage 详情 status=1（eSIM · status=5 继续 / 10 失败）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "``WaitForHistoricalEsimUsageOrderConfirmed`` · 用本步 HTTP 响应判定；"
                    "status=5 时 setNextRequest 重跑本步；status=1 进入 S03c 取 iccid。"
                ),
                prerequest_lines=Prerequest_SavePollRequestName(),
                test_lines=Lines_Step(
                    "E02-S03b",
                    ["epPollEsimUsageOrderUntilConfirmed('E02-S03b');"],
                ),
            ),
            *BuildTopupStepsAfterPoll(js, step_prefix="E02-S03"),
            RequestItem(
                js_helpers=js,
                name="E02-S04 POST /v2/orders/ePasses（module=8 · 预约后 usage 列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="预约成功后 module=8 订单列表",
                test_lines=Lines_Step("E02-S04", ["epAssertUsageOrderInListActive('E02-S04');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S05 POST /v2/orders/ePasses（otherModule=11 隔离）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter``",
                test_lines=Lines_Step("E02-S05", ["epAssertNoEsimReturnedWithOtherModuleFilter('E02-S05');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S06 POST /v2/orders/ePasses/details（仅 orderId · usage 详情）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E02-S06",
                    ["epAssertHttpBusinessOk('E02-S06');", "epAssertUsageDetailsCore('E02-S06', false);"],
                ),
            ),
            BuildPollBeforeCancelUsageStep(js, "E02-S06b"),
            RequestItem(
                js_helpers=js,
                name="E02-S07 PATCH /v2/orders（取消 usage 预订单 · 失败重试）",
                method="PATCH",
                url_path="/v2/orders",
                body=CancelOrderBody("usageOrderId"),
                headers=BearerJsonHeaders(),
                description="``CancelHistoricalUsageOrderAndVerify`` · prebooking usage 单取消",
                test_lines=Lines_Step("E02-S07", ["epCancelOrderWithRetry('E02-S07', 'usageOrderId');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S08 POST /v2/orders/ePasses/details（取消后 usage 详情）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E02-S08",
                    ["epAssertHttpBusinessOk('E02-S08');", "epAssertUsageDetailsCore('E02-S08', true);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S09 POST /v2/orders/ePasses（取消后 usage 列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E02-S09",
                    [
                        "epAssertHttpBusinessOk('E02-S09');",
                        "epAssertOrderListPagination('E02-S09', false);",
                        "epAssertUsageListContainsCancelled('E02-S09');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S10 POST /v2/orders/ePasses/search（usage 取消后 ePass 仍 Active）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E02-S10",
                    ["epAssertHttpBusinessOk('E02-S10');", "epAssertSearchActiveAfterUsageCancel('E02-S10');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E02-S11 PATCH /v2/orders（取消 MS 购买单 · 失败重试）",
                method="PATCH",
                url_path="/v2/orders",
                body=CancelOrderBody("purchaseOrderId"),
                headers=BearerJsonHeaders(),
                description="``CancelHistoricalPurchaseOrderAndVerify``",
                test_lines=Lines_Step("E02-S11", ["epCancelOrderWithRetry('E02-S11', 'purchaseOrderId');"]),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpassEsim_E2E_PrebookingMainChain`` · "
            "``RunHistoricalEpassPrebookingMainE2EScenario(catalog_label='esim')`` · "
            "运行前填 esimResourceId/esimOptionId（``DP_HIST_EPASS_ESIM_RESOURCE_ID`` / ``DP_HIST_EPASS_ESIM_OPTION_ID``）"
        ),
    )


def BuildBundleE2EFolder() -> JsonObject:
    js = BuildEsimJsHelpersLines
    return Folder(
        "E03 · tc-P0 Bundle",
        [
            RequestItem(
                js_helpers=js,
                name="E03-S01 POST /v2/resources/options/prebookings/availability（无 ePassId · module=8）",
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=False),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingTokenWithoutEpass``",
                prerequest_lines=Prerequest_ResetForBundle(),
                test_lines=Lines_Step(
                    "E03-S01",
                    ["epAssertHttpBusinessOk('E03-S01');", "epAssertAvailabilitySuccess('E03-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S02 POST /v2/orders/esims/ePasses/bundle",
                method="POST",
                url_path="/v2/orders/esims/ePasses/bundle",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "clientUserId": "{{clientUserId}}",
                        "extra": {"prebookingToken": "{{prebookingToken}}"},
                        "async": False,
                    },
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalBundleOrderSuccess``",
                test_lines=Lines_Step(
                    "E03-S02",
                    [
                        "epClearPollAttempt('usageOrderId');",
                        "epAssertHttpBusinessOk('E03-S02');",
                        "epAssertBundleOrderSuccess('E03-S02');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S02b 轮询 usage 详情 status=1（eSIM · status=5 继续 / 10 失败）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="Bundle 后轮询 usage 单 status=1（同 E02-S03b · setNextRequest 自循环）。",
                prerequest_lines=Prerequest_SavePollRequestName(),
                test_lines=Lines_Step(
                    "E03-S02b",
                    ["epPollEsimUsageOrderUntilConfirmed('E03-S02b');"],
                ),
            ),
            *BuildTopupStepsAfterPoll(js, step_prefix="E03-S02"),
            RequestItem(
                js_helpers=js,
                name="E03-S03 POST /v2/orders/ePasses（module=8 · Bundle 后 usage 列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="Bundle 成功后 module=8 订单列表",
                test_lines=Lines_Step("E03-S03", ["epAssertUsageOrderInListActive('E03-S03');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S04 POST /v2/orders/ePasses（otherModule=11 隔离）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter``",
                test_lines=Lines_Step("E03-S04", ["epAssertNoEsimReturnedWithOtherModuleFilter('E03-S04');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S05 POST /v2/orders/ePasses/details（仅 orderId · usage 详情）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E03-S05",
                    ["epAssertHttpBusinessOk('E03-S05');", "epAssertUsageDetailsCore('E03-S05', false);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S06 POST /v2/users/ePasses",
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E03-S06",
                    ["epAssertHttpBusinessOk('E03-S06');", "epAssertUserListContains('E03-S06');"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S07 POST /v2/orders/ePasses/search（ePassId · status=2 usedUsages=1）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后 search by ePassId",
                test_lines=Lines_Step(
                    "E03-S07",
                    ["epAssertHttpBusinessOk('E03-S07');", "epAssertSearchPurchaseDetails('E03-S07', true, false, 2, 1);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S08 POST /v2/orders/ePasses/search（orderId · status=2 usedUsages=1）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后二次 search by orderId",
                test_lines=Lines_Step(
                    "E03-S08",
                    ["epAssertHttpBusinessOk('E03-S08');", "epAssertSearchPurchaseDetails('E03-S08', true, false, 2, 1);"],
                ),
            ),
            BuildPollBeforeCancelUsageStep(js, "E03-S08b"),
            RequestItem(
                js_helpers=js,
                name="E03-S09 PATCH /v2/orders（取消 usage 预订单 · 失败重试）",
                method="PATCH",
                url_path="/v2/orders",
                body=CancelOrderBody("usageOrderId"),
                headers=BearerJsonHeaders(),
                description="Bundle usage 单取消 · ``PatchCancelOrderWithRetry``",
                test_lines=Lines_Step("E03-S09", ["epCancelOrderWithRetry('E03-S09', 'usageOrderId');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S10 POST /v2/orders/ePasses/details（取消后 usage 详情）",
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E03-S10",
                    ["epAssertHttpBusinessOk('E03-S10');", "epAssertUsageDetailsCore('E03-S10', true);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S11 POST /v2/orders/ePasses（取消后 usage 列表）",
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E03-S11",
                    [
                        "epAssertHttpBusinessOk('E03-S11');",
                        "epAssertOrderListPagination('E03-S11', false);",
                        "epAssertUsageListContainsCancelled('E03-S11');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S12 POST /v2/orders/ePasses/search（usage 取消后 ePass Active）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E03-S12",
                    ["epAssertHttpBusinessOk('E03-S12');", "epAssertSearchActiveAfterUsageCancel('E03-S12', false);"],
                ),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S13 PATCH /v2/orders（取消 MS 购买单 · 失败重试）",
                method="PATCH",
                url_path="/v2/orders",
                body=CancelOrderBody("purchaseOrderId"),
                headers=BearerJsonHeaders(),
                description="``CancelHistoricalPurchaseOrderAndVerify``",
                test_lines=Lines_Step("E03-S13", ["epCancelOrderWithRetry('E03-S13', 'purchaseOrderId');"]),
            ),
            RequestItem(
                js_helpers=js,
                name="E03-S14 POST /v2/orders/ePasses/search（购买单取消后 ePass Cancelled）",
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E03-S14",
                    [
                        "epAssertHttpBusinessOk('E03-S14');",
                        "epAssertSearchCancelledAfterPurchaseCancel('E03-S14', false);",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpassEsim_E2E_BundleMainChain`` · "
            "``RunHistoricalEpassBundleMainE2EScenario(catalog_label='esim')`` · "
            "运行前填 esimResourceId/esimOptionId（``DP_HIST_EPASS_ESIM_RESOURCE_ID`` / ``DP_HIST_EPASS_ESIM_OPTION_ID``）"
        ),
    )


def BuildCollection() -> JsonObject:
    js = BuildEsimJsHelpersLines
    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            RequestItem(
                js_helpers=js,
                name="POST /v2/auth/token（GetAccessTokenForEpass）",
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken；前置脚本同步 prebookingDate（Apifox +10天 10:30）。",
                save_token=True,
                test_lines=Lines_Auth(),
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
            ),
        ],
        description="先执行本文件夹。",
    )

    info: JsonObject = {
        "name": "eSIM ePass · P0 E2E 核心",
        "description": (
            "由 GeneratePostmanCollectionEsimEpass.py 生成。\n\n"
            "**三条 P0 E2E 核心链路**（对齐 ``RunHistoricalEpass*MainE2EScenario(catalog_label='esim')``）：\n"
            "- E01 创建验证链（含 module=8 / otherModule=11 双向隔离）\n"
            "- E02 预约验证链（options 可用性 · module=8）\n"
            "- E03 Bundle 一步下单\n\n"
            "每个 HTTP 步骤含多条 pm.test 字段级断言（**无** prebookingRequiredInfo null 断言）。\n\n"
            "**必填变量**：ProgramID、clientId、secret；E02/E03 另填 esimResourceId、esimOptionId。\n"
            f"**eSIM 网点变量**：集合 ``{ESIM_RESOURCE_ID_VAR}`` / ``{ESIM_OPTION_ID_VAR}`` 对齐 "
            f"``{ENV_ESIM_RESOURCE_ID}`` / ``{ENV_ESIM_OPTION_ID}``（默认 {DEFAULT_ESIM_RESOURCE_ID} / {DEFAULT_ESIM_OPTION_ID}）。\n"
            "**品类 module**：epassModule=8、otherModule=11（断言动态读取）。\n"
            "**eSIM 异步落单**：prebooking/bundle 后轮询 status=1，Topup 后轮询 status=1 再取消；"
            "usage/topup/MS 取消遇 ``Order cancellation failed. Please try again later.`` 自动重试。\n"
            "**创建 availableUsages**：默认 1（E01/E02/E03 创建 ePass）。\n"
            "**eSIM 异步落单轮询**：``esimPollIntervalMs`` / ``esimPollMaxAttempts`` 对齐 "
            "``DP_HIST_EPASS_ESIM_STATUS_POLL_*``；Postman 用 setNextRequest 重跑本步，"
            "Apifox 无 setNextRequest 时自动降级 sendRequest 轮询。\n"
            "**eSIM resourceId**：订单回显可能与可用性请求不一致，以响应 canonical id 为准并回写 ``esimResourceId``。\n"
            "**可选**：x-version（canary）。prebookingDate 由 Apifox 表达式 "
            "``{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30`` 自动解析。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("epassModule", str(EPASS_MODULE_DEFAULT)),
        CollectionVariable("otherModule", str(OTHER_MODULE_DEFAULT)),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable(
            ESIM_RESOURCE_ID_VAR,
            DEFAULT_ESIM_RESOURCE_ID,
        ),
        CollectionVariable(
            ESIM_OPTION_ID_VAR,
            DEFAULT_ESIM_OPTION_ID,
        ),
        CollectionVariable("esimAvailabilityResourceId", ""),
        CollectionVariable("esimAvailabilityOptionId", ""),
        CollectionVariable("esimPollIntervalMs", "3000"),
        CollectionVariable("esimPollMaxAttempts", "40"),
        CollectionVariable("esimCancelMaxAttempts", "5"),
        CollectionVariable("esimCancelRetryIntervalMs", "2000"),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("prebookingToken", ""),
        CollectionVariable("esimIccid", ""),
        CollectionVariable("topupToken", ""),
        CollectionVariable("topupOrderId", ""),
    ]

    return {
        "info": info,
        "variable": variables,
        "item": [
            auth_folder,
            BuildCreateE2EFolder(),
            BuildPrebookingE2EFolder(),
            BuildBundleE2EFolder(),
        ],
    }


def RewritePurposeFirstNames(node: Any) -> None:
    """将历史「步骤码 METHOD /path」命名改写为 PurposeName（PushSteps 硬约束）。"""
    import re

    if isinstance(node, list):
        for child in node:
            RewritePurposeFirstNames(child)
        return
    if not isinstance(node, dict):
        return
    name = node.get("name")
    req = node.get("request")
    if isinstance(name, str) and isinstance(req, dict) and not name.startswith("【"):
        method = str(req.get("method") or "POST").upper()
        url = req.get("url")
        path_hint = ""
        if isinstance(url, dict):
            raw_path = url.get("path")
            if isinstance(raw_path, list):
                path_hint = "/" + "/".join(str(p) for p in raw_path if str(p))
            elif isinstance(url.get("raw"), str):
                raw = str(url.get("raw") or "")
                path_hint = raw.split("?", 1)[0]
                if "://" in path_hint:
                    path_hint = "/" + "/".join(path_hint.split("/", 3)[3:])
        if path_hint.startswith("/v2/"):
            path_hint = path_hint[3:]
        elif path_hint.startswith("/v1/"):
            path_hint = path_hint[3:]
        m = re.match(r"^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\s+(.*)$", name.strip())
        if m:
            step_id, rest = m.group(1), m.group(2).strip()
        elif name.strip().upper().startswith(("POST ", "GET ", "PATCH ", "PUT ", "DELETE ")):
            step_id, rest = "Auth" if "auth/token" in name else "STEP", name.strip()
        else:
            step_id, rest = "STEP", name.strip()
        purpose = re.sub(
            r"^(GET|POST|PATCH|PUT|DELETE)\s+/[^\s（(]*\s*",
            "",
            rest,
            flags=re.IGNORECASE,
        ).strip()
        purpose = purpose.strip("（）() ·")
        if not purpose or purpose.upper().startswith(("POST ", "GET ", "PATCH ", "PUT ", "DELETE ")):
            purpose = f"{step_id} 步骤"
        if "GetAccessToken" in name or "auth/token" in name:
            purpose = "获取 ePass 鉴权 token"
            step_id = "Auth"
            path_hint = path_hint or "/auth/token"
        node["name"] = PurposeName(purpose, step_id, method, path_hint or "/")
    for key in ("item", "response"):
        child = node.get(key)
        if child is not None:
            RewritePurposeFirstNames(child)


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    collection = BuildCollection()
    RewritePurposeFirstNames(collection)
    WriteCollectionJson(out_path, collection)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
