"""
生成 fitness ePass **P0 E2E 核心** Postman Collection v2.1 JSON。

对齐 ``test_historical_epass_regression.py`` fitness 三条主链路及 ``historical_epass_service`` 断言语义（``catalog_label="fitness"``）：

- E01 创建验证链 · ``RunHistoricalEpassCreateMainE2EScenario``
- E02 预约验证链 · ``RunHistoricalEpassPrebookingMainE2EScenario``
- E03 Bundle 一步下单 · ``RunHistoricalEpassBundleMainE2EScenario``

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionFitnessEpass.py
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
    Lines_Step,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)
from epass_cli_common import (
    BuildEpassCreatePayload,
    BuildEpassRuntimeHelpersBlock,
    CREATE_EXPIRATION_DATE,
    CREATE_FIRST_NAME,
    CREATE_LAST_NAME,
    GetEpassCategoryConfig,
    OTHER_MODULE_DEFAULT,
)

JsonObject = Dict[str, Any]
FITNESS_CATEGORY = GetEpassCategoryConfig("fitness")

OUT_NAME: Final[str] = "Fitness-ePass-P0-e2e-core.postman_collection.json"
PREBOOKING_DATE_APIFOX: Final[str] = "{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30"
FITNESS_SCHEDULE_START_DATE_APIFOX: Final[str] = "{{$date.now|addDays(5)|format('yyyy-MM-dd')}}"
FITNESS_SCHEDULE_END_DATE_APIFOX: Final[str] = "{{$date.now|addDays(10)|format('yyyy-MM-dd')}}"
FITNESS_SCHEDULE_URL_PATH: Final[str] = (
    "/v2/resources/fitness/{{fitnessResourceId}}/schedule"
    f"?startDate={FITNESS_SCHEDULE_START_DATE_APIFOX}"
    f"&endDate={FITNESS_SCHEDULE_END_DATE_APIFOX}"
    "&fallbackAllowed=true"
)
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CANCEL_RETRY_MSG_NEEDLE: Final[str] = "Order cancellation failed"
CREATE_AVAILABLE_USAGES: Final[int] = FITNESS_CATEGORY.available_usages
DEFAULT_FITNESS_RESOURCE_ID: Final[str] = FITNESS_CATEGORY.default_resource_id
GENERATED_CANCEL_ATTEMPTS: Final[int] = 3
FITNESS_RESOURCE_ID_VAR: Final[str] = FITNESS_CATEGORY.resource_var
FITNESS_OPTION_ID_VAR: Final[str] = FITNESS_CATEGORY.option_var or "fitnessOptionId"
ENV_FITNESS_RESOURCE_ID: Final[str] = "DP_HIST_EPASS_FITNESS_RESOURCE_ID"
EPASS_MODULE_DEFAULT: Final[int] = FITNESS_CATEGORY.module

CREATE_PAYLOAD_TEMPLATE: Final[str] = BuildEpassCreatePayload(FITNESS_CATEGORY)


def FitnessPrebookingExtraDict() -> JsonObject:
    """fitness 预约 / Bundle ``extra``（含 prebookingRequiredInfo + optionId）。"""
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "email": "auto.test@dragonpass.com",
            "phoneNumber": "8081966002",
            "callingCode": "44",
        },
        "optionId": "{{fitnessOptionId}}",
    }


def BuildFitnessJsHelpersLines() -> List[str]:
    """与 ``historical_epass_service`` / fitness schedule+options 链断言语义对齐的公共 JS（``fp*`` 前缀）。"""
    cancel_msg_js = json.dumps(CANCEL_SUCCESS_MSG)
    cancel_retry_needle_js = json.dumps(CANCEL_RETRY_MSG_NEEDLE)
    create_first_name_js = json.dumps(CREATE_FIRST_NAME)
    create_last_name_js = json.dumps(CREATE_LAST_NAME)
    create_expiration_date_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_available_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    epass_module_default_js = json.dumps(EPASS_MODULE_DEFAULT)
    other_module_default_js = json.dumps(OTHER_MODULE_DEFAULT)
    fitness_resource_var = FITNESS_RESOURCE_ID_VAR
    fitness_option_var = FITNESS_OPTION_ID_VAR
    runtime_helpers = BuildEpassRuntimeHelpersBlock(FITNESS_CATEGORY)
    js = runtime_helpers + rf"""function fpGetPreferredOptionType() {{
  var n = parseInt(fpGetVar('fitnessPreferredOptionType') || '1', 10);
  return isNaN(n) ? 1 : n;
}}
function fpParseFitnessSchedule(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(fpIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
  var data = fpGetInnerData(pm.response.json());
  var preferred = fpGetPreferredOptionType();
  var picked = null;
  var schedules = (data && data.schedules) || [];
  pm.test(label + ': schedules 非空', function () {{
    pm.expect(schedules).to.be.an('array').that.is.not.empty;
  }});
  for (var si = 0; si < schedules.length && !picked; si++) {{
    var sched = schedules[si];
    if (!sched || !sched.date || !Array.isArray(sched.optionList)) continue;
    var dayTargets = [];
    sched.optionList.forEach(function (opt) {{
      if (!opt || !opt.optionId || !opt.startTime) return;
      dayTargets.push({{
        scheduleDate: sched.date,
        optionId: String(opt.optionId),
        startTime: String(opt.startTime),
        optionType: (typeof opt.optionType === 'number') ? opt.optionType : 0
      }});
    }});
    dayTargets.sort(function (a, b) {{
      var pa = (a.optionType === preferred) ? 0 : 1;
      var pb = (b.optionType === preferred) ? 0 : 1;
      if (pa !== pb) return pa - pb;
      return String(a.optionId).localeCompare(String(b.optionId));
    }});
    if (dayTargets.length) picked = dayTargets[0];
  }}
  pm.test(label + ': 写入 fitnessOptionId + prebookingDate', function () {{
    pm.expect(picked, 'schedule 候选').to.be.an('object');
    var slotDate = picked.scheduleDate + 'T' + picked.startTime;
    fpSetVar('fitnessOptionId', picked.optionId);
    fpSetVar('prebookingDate', slotDate);
    console.log(label + ': schedule 选槽 optionId=' + picked.optionId + ' prebookingDate=' + slotDate);
  }});
}}
function fpApplyScheduleToRequestBody() {{
  var opt = fpGetVar('fitnessOptionId');
  var pb = fpGetVar('prebookingDate');
  if (!opt) console.warn('fpApplyScheduleToRequestBody: fitnessOptionId 为空（schedule 未写入）');
  if (!pb) console.warn('fpApplyScheduleToRequestBody: prebookingDate 为空（schedule 未写入）');
  try {{
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    if (opt) {{
      if (body.optionId !== undefined) body.optionId = opt;
      if (body.extra && body.extra.optionId !== undefined) body.extra.optionId = opt;
    }}
    if (pb && body.prebookingDate !== undefined) body.prebookingDate = pb;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('fpApplyScheduleToRequestBody: optionId=' + opt + ' prebookingDate=' + pb);
  }} catch (e) {{
    console.warn('fpApplyScheduleToRequestBody:', e);
  }}
}}
function fpExpectedModule() {{
  var raw = pm.collectionVariables.get('epassModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {epass_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {epass_module_default_js} : n;
}}
function fpOtherModule() {{
  var raw = pm.collectionVariables.get('otherModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {other_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {other_module_default_js} : n;
}}
function fpIsBusinessSuccess(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}}
function fpGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {{
    return d;
  }}
  return d;
}}
function fpAssertEpassModuleRequired(data, ctx) {{
  pm.expect(data, ctx + ' data').to.be.an('object');
  pm.expect(data.module, ctx + ' module').to.eql(fpExpectedModule());
}}
function fpAssertEpassModuleIfPresent(data, ctx) {{
  if (!data || typeof data !== 'object') return;
  if (Object.prototype.hasOwnProperty.call(data, 'module')) {{
    pm.expect(data.module, ctx + ' module').to.eql(fpExpectedModule());
  }}
}}
function fpResolveEPassIdFromRoot(data) {{
  if (!data || typeof data !== 'object') return null;
  var direct = data.ePassId || data.epassId;
  if (direct) return direct;
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    return extra.ePassId || extra.epassId || null;
  }}
  return null;
}}
function fpResolveEPassId(extra) {{
  if (!extra || typeof extra !== 'object') return null;
  return extra.ePassId || extra.epassId || null;
}}
function fpResolveOptionId(data) {{
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
var fpOrderStatusActiveOrProcessing = [1, 5];
function fpFailIfOrderStatus10(status, label) {{
  if (status === 10) {{
    pm.expect.fail(label + ': 订单 status=10 FAILED');
  }}
}}
function fpExpectOrderStatusActiveOrProcessing(label, status) {{
  fpFailIfOrderStatus10(status, label);
  pm.expect(fpOrderStatusActiveOrProcessing, label + ' status').to.include(status);
}}
function fpSyncResourceIdFromOrderResponse(label, actual) {{
  pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  var fromAvail = pm.collectionVariables.get('fitnessAvailabilityResourceId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': fitness 订单 resourceId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（fitness 以响应 canonical id 为准，已回写 fitnessResourceId）'
    );
  }}
  pm.collectionVariables.set('{fitness_resource_var}', String(actual));
}}
function fpExpectResourceIdMatch(label, actual) {{
  fpSyncResourceIdFromOrderResponse(label, actual);
}}
function fpSyncOptionIdFromOrderResponse(label, actual) {{
  if (!actual) {{
    console.warn(label + ': 响应未返回 optionId，跳过 fitnessOptionId 回写');
    return;
  }}
  pm.expect(actual, label + ' optionId 非空').to.be.a('string').and.not.empty;
  var fromAvail = fpGetVar('fitnessAvailabilityOptionId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': fitness 订单 optionId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（以响应为准，已回写 fitnessOptionId）'
    );
  }}
  fpSetVar('{fitness_option_var}', String(actual));
}}
function fpExpectOptionIdMatch(label, actual) {{
  fpSyncOptionIdFromOrderResponse(label, actual);
}}
function fpSaveCreateIds(data) {{
  if (!data || typeof data !== 'object') return;
  fpCaptureClientUserIdAfterSend(data);
  if (data.orderId && !fpIsUnresolvedPlaceholder(data.orderId)) {{
    fpSetVar('purchaseOrderId', String(data.orderId));
  }}
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = fpResolveEPassId(extra);
    if (ep && !fpIsUnresolvedPlaceholder(ep)) fpSetVar('ePassId', String(ep));
  }}
}}
function fpSaveAvailabilityRequestFields() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (reqBody && reqBody.prebookingDate) {{
      fpSetVar('prebookingDate', String(reqBody.prebookingDate));
    }}
    if (reqBody && reqBody.resourceId) {{
      fpSetVar('fitnessAvailabilityResourceId', String(reqBody.resourceId));
    }}
    if (reqBody && reqBody.optionId) {{
      fpSetVar('fitnessAvailabilityOptionId', String(reqBody.optionId));
    }}
    var adultCount = parseInt(String(reqBody && reqBody.adultCount), 10);
    var childCount = parseInt(String(reqBody && reqBody.childCount), 10);
    if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
    if (isNaN(childCount) || childCount < 0) childCount = 0;
    pm.collectionVariables.set('fitnessAdultCount', String(adultCount));
    pm.collectionVariables.set('fitnessChildCount', String(childCount));
  }} catch (e) {{
    console.warn('fpSaveAvailabilityRequestFields:', e);
  }}
}}
function fpExpectedBookingCounts() {{
  var adultCount = parseInt(String(pm.collectionVariables.get('fitnessAdultCount') || '1'), 10);
  var childCount = parseInt(String(pm.collectionVariables.get('fitnessChildCount') || '0'), 10);
  if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
  if (isNaN(childCount) || childCount < 0) childCount = 0;
  if (adultCount + childCount <= 0) {{
    adultCount = 1;
    childCount = 0;
  }}
  return adultCount + childCount;
}}
function fpAssertBookingCounts(label) {{
  var env = pm.response.json();
  if (!env || env.code !== 0) {{
    return;
  }}
  var data = fpGetInnerData(env);
  var extra = (data && data.extra && typeof data.extra === 'object') ? data.extra : {{}};
  var expected = fpExpectedBookingCounts();
  var actual = extra.bookingCounts;
  pm.test(label + ': extra.bookingCounts | 期望=可用性 adultCount+childCount=' + expected + ' | 实际=' + String(actual), function () {{
    pm.expect(Object.prototype.hasOwnProperty.call(extra, 'bookingCounts'), 'extra.bookingCounts 字段存在').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.be.a('number');
    pm.expect(Number.isInteger(actual), 'extra.bookingCounts 为整数').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.eql(expected);
  }});
}}
function fpResolveListItemField(item, rootKey, extraKey) {{
  if (!item || typeof item !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(item, rootKey)) return item[rootKey];
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, extraKey)) return ex[extraKey];
    if (Object.prototype.hasOwnProperty.call(ex, rootKey)) return ex[rootKey];
  }}
  return null;
}}
function fpResolveTransportHubName(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubName')) {{
    return ex.transportHubName;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubName')) return item.transportHubName;
  return undefined;
}}
function fpResolveTransportHubId(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubId')) {{
    return ex.transportHubId;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubId')) return item.transportHubId;
  return undefined;
}}
function fpSavePrebookingToken(data) {{
  if (data && data.prebookingToken && !fpIsUnresolvedPlaceholder(data.prebookingToken)) {{
    fpSetVar('prebookingToken', String(data.prebookingToken));
  }}
}}
function fpSaveUsageOrderId(data) {{
  if (data && data.orderId && !fpIsUnresolvedPlaceholder(data.orderId)) {{
    fpSetVar('usageOrderId', String(data.orderId));
  }}
}}
function fpAssertHttpBusinessOk(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(fpIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
}}
function fpResponseHttpCode(res) {{
  if (!res) return 0;
  var raw = res.code;
  if (raw === undefined || raw === null) raw = res.status;
  if (raw === undefined || raw === null) raw = res.statusCode;
  if (raw === undefined || raw === null) raw = res.responseCode;
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? 0 : n;
}}
function fpIsCancelResponseSuccess(res, env) {{
  if (!env || typeof env !== 'object') return false;
  var httpCode = fpResponseHttpCode(res);
  if (httpCode && httpCode !== 200) return false;
  if (!fpIsBusinessSuccess(env)) return false;
  var msg = env.msg || env.message;
  return msg === {cancel_msg_js};
}}
function fpIsCancelResponseRetryable(env) {{
  if (!env || typeof env !== 'object') return false;
  var msg = String(env.msg || env.message || '');
  if (msg.indexOf({cancel_retry_needle_js}) >= 0) return true;
  if (env.errCode === '500.041.006' || env.errCode === '500.071.016') return true;
  return false;
}}
function fpCancelDoneVar(orderIdVar) {{
  return 'fpCancelDone_' + orderIdVar;
}}
function fpMarkCancelDone(orderIdVar) {{
  pm.collectionVariables.set(fpCancelDoneVar(orderIdVar), '1');
}}
function fpIsCancelAlreadyDone(orderIdVar) {{
  return pm.collectionVariables.get(fpCancelDoneVar(orderIdVar)) === '1';
}}
function fpClearCancelDone(orderIdVar) {{
  pm.collectionVariables.unset(fpCancelDoneVar(orderIdVar));
}}
function fpSetNextRequestByName(reqName) {{
  if (!reqName) return;
  var setter = (typeof postman !== 'undefined' && postman.setNextRequest)
    ? postman.setNextRequest.bind(postman)
    : (pm.execution && pm.execution.setNextRequest
      ? pm.execution.setNextRequest.bind(pm.execution)
      : null);
  if (setter) setter(reqName);
}}
function fpPrerequestSkipCancelIfDone(orderIdVar, skipToRequestName) {{
  if (fpIsCancelAlreadyDone(orderIdVar) && skipToRequestName) {{
    fpSetNextRequestByName(skipToRequestName);
  }}
}}
function fpAssertCancelEnvelope(label, env) {{
  pm.test(label + ': code=0 取消业务成功', function () {{
    pm.expect(env && env.code, 'code').to.eql(0);
  }});
  pm.test(label + ': msg=The order was cancelled successfully', function () {{
    var msg = env && (env.msg || env.message);
    pm.expect(msg, '取消响应 msg').to.eql({cancel_msg_js});
  }});
}}
function fpCancelOrderAttempt(label, orderIdVar, attemptNo, maxAttempts, skipToRequestName) {{
  if (fpIsCancelAlreadyDone(orderIdVar)) {{
    pm.test(label + ': 已成功取消（跳过）', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  var orderId = fpGetVar(orderIdVar);
  pm.test(label + ': ' + orderIdVar + ' 已设置', function () {{
    pm.expect(orderId, orderIdVar).to.be.ok;
  }});
  var env0;
  try {{
    env0 = pm.response.json();
  }} catch (e) {{
    pm.test(label + ': 响应 JSON', function () {{ pm.expect.fail(String(e)); }});
    return;
  }}
  if (fpIsCancelResponseSuccess(pm.response, env0)) {{
    fpMarkCancelDone(orderIdVar);
    fpAssertCancelEnvelope(label, env0);
    if (skipToRequestName && attemptNo < maxAttempts) {{
      fpSetNextRequestByName(skipToRequestName);
    }}
    return;
  }}
  if (fpIsCancelResponseRetryable(env0) && attemptNo < maxAttempts) {{
    pm.test(label + ': 第 ' + attemptNo + ' 次失败可重试', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  pm.test(label + ': 取消失败', function () {{
    pm.expect.fail(
      label + ': attempt ' + attemptNo + '/' + maxAttempts + ' env=' + JSON.stringify(env0)
    );
  }});
}}
function fpExpectedCreateExtra() {{
  return {{
    firstName: {create_first_name_js},
    lastName: {create_last_name_js},
    expirationDate: {create_expiration_date_js},
    availableUsages: {create_available_usages_js}
  }};
}}
function fpAssertExtraMatchesCreateInput(label, extra) {{
  pm.test(label + ': extra.firstName 与入参一致', function () {{
    pm.expect(extra.firstName).to.eql(fpExpectedCreateExtra().firstName);
  }});
  pm.test(label + ': extra.lastName 与入参一致', function () {{
    pm.expect(extra.lastName).to.eql(fpExpectedCreateExtra().lastName);
  }});
  pm.test(label + ': extra.expirationDate 与入参一致', function () {{
    pm.expect(extra.expirationDate).to.eql(fpExpectedCreateExtra().expirationDate);
  }});
  pm.test(label + ': extra.availableUsages 与入参一致', function () {{
    pm.expect(extra.availableUsages).to.eql(fpExpectedCreateExtra().availableUsages);
  }});
}}
function fpAssertCreateCoreFields(label) {{
  var dataFn = function () {{ return fpGetInnerData(pm.response.json()); }};
  fpSaveCreateIds(dataFn());
  pm.test(label + ': module=epassModule', function () {{
    fpAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': category=2 或 3', function () {{
    pm.expect([2, 3]).to.include(dataFn().category);
  }});
  pm.test(label + ': clientUserId 回显一致', function () {{
    var actual = dataFn().clientUserId;
    var saved = fpGetVar('clientUserId');
    pm.expect(actual, '响应 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(fpIsUnresolvedPlaceholder(actual), '响应不是未解析模板').to.be.false;
    pm.expect(fpIsUuid(actual), '响应 clientUserId 为 UUID').to.be.true;
    pm.expect(saved, '后置已提取 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(actual).to.eql(saved);
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
  fpAssertExtraMatchesCreateInput(label, dataFn().extra);
  pm.test(label + ': extra.ePassId 非空', function () {{
    pm.expect(fpResolveEPassId(dataFn().extra)).to.be.ok;
  }});
  pm.test(label + ': extra.allowedResources 存在', function () {{
    pm.expect(dataFn().extra.allowedResources).to.be.an('object');
  }});
  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {{
    pm.expect(fpGetVar('ePassId')).to.be.ok;
    pm.expect(fpGetVar('purchaseOrderId')).to.be.ok;
  }});
}}
function fpAssertUserListContains(label) {{
  pm.test(label + ': ePassesList 含 ePassId', function () {{
    var data = fpGetInnerData(pm.response.json());
    var target = fpGetVar('ePassId');
    pm.expect(data.ePassesList).to.be.an('array');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    pm.expect(hit.length, '未找到 ePassId=' + target).to.be.above(0);
  }});
  pm.test(label + ': 列表项 module=epassModule（若存在）', function () {{
    var data = fpGetInnerData(pm.response.json());
    var target = fpGetVar('ePassId');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    if (hit[0] && Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(fpExpectedModule());
    }}
  }});
}}
function fpAssertSearchPurchaseDetails(label, assertEpassModule, matchCreateInput, expectedStatus, expectedUsedUsages) {{
  var dataFn = function () {{ return fpGetInnerData(pm.response.json()); }};
  var status = (expectedStatus !== undefined && expectedStatus !== null) ? expectedStatus : 1;
  var usedUsages = (expectedUsedUsages !== undefined && expectedUsedUsages !== null) ? expectedUsedUsages : 0;
  if (assertEpassModule !== false) {{
    pm.test(label + ': module=epassModule', function () {{
      fpAssertEpassModuleRequired(dataFn(), label);
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
    pm.expect(dataFn().clientUserId).to.eql(fpGetVar('clientUserId'));
  }});
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    var actual = dataFn().orderId;
    var previous = fpGetVar('purchaseOrderId');
    var usage = fpGetVar('usageOrderId');
    pm.expect(actual).to.be.a('string').and.not.empty;
    if (previous && previous !== usage) {{
      pm.expect(actual).to.eql(previous);
    }} else {{
      fpSetVar('purchaseOrderId', String(actual));
    }}
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(fpResolveEPassId(dataFn().extra)).to.eql(fpGetVar('ePassId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.usedUsages=' + usedUsages, function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(usedUsages);
  }});
  if (matchCreateInput !== false) {{
    fpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function fpAssertOrderListPagination(label, allowEmpty, expectEpassModule) {{
  pm.test(label + ': pagination 结构', function () {{
    var data = fpGetInnerData(pm.response.json());
    pm.expect(data.pagination).to.be.an('object');
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {{
      pm.expect(data.pagination, 'pagination.' + k).to.have.property(k);
    }});
  }});
  pm.test(label + ': orders 为数组', function () {{
    pm.expect(fpGetInnerData(pm.response.json()).orders).to.be.an('array');
  }});
  if (allowEmpty) {{
    pm.test(label + ': 创建后 orders 可为空（canary doc gap）', function () {{
      pm.expect(fpGetInnerData(pm.response.json()).orders).to.be.an('array');
    }});
  }}
  if (expectEpassModule) {{
    pm.test(label + ': 列表项 module=epassModule（若存在 module 字段）', function () {{
      var orders = fpGetInnerData(pm.response.json()).orders || [];
      var mod = fpExpectedModule();
      orders.forEach(function (item, idx) {{
        if (item && Object.prototype.hasOwnProperty.call(item, 'module')) {{
          pm.expect(item.module, 'orders[' + idx + '].module').to.eql(mod);
        }}
      }});
    }});
  }}
}}
function fpAssertAvailabilitySuccess(label) {{
  fpSaveAvailabilityRequestFields();
  pm.test(label + ': available=true', function () {{
    pm.expect(fpGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var data = fpGetInnerData(pm.response.json());
    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;
    fpSavePrebookingToken(data);
  }});
}}
function fpAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {{
  allowedStatuses = allowedStatuses || fpOrderStatusActiveOrProcessing;
  var data = function () {{ return fpGetInnerData(pm.response.json()); }};
  if (!requireExistingEPassId) {{
    fpCaptureClientUserIdAfterSend(data());
  }}
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
  pm.test(label + ': module=epassModule', function () {{ fpAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    fpSaveUsageOrderId(data());
  }});
  pm.test(label + ': clientUserId 与注册会籍一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(fpGetVar('clientUserId'));
  }});
  pm.test(label + ': ePassId 与前面一致', function () {{
    var ep = fpResolveEPassIdFromRoot(data());
    pm.expect(ep).to.be.a('string').and.not.empty;
    if (requireExistingEPassId) {{
      pm.expect(ep).to.eql(fpGetVar('ePassId'));
    }} else {{
      fpSetVar('ePassId', String(ep));
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
    var expected = fpGetVar('prebookingDate');
    var actual = data().extra.prebookingDate;
    pm.expect(actual).to.be.a('string').and.not.empty;
    if (expected && String(expected).trim()) {{
      pm.expect(actual).to.eql(expected);
    }}
  }});
  pm.test(label + ': extra.resourceId 与 resourceId 一致', function () {{
    fpExpectResourceIdMatch(label, data().extra.resourceId);
  }});
  pm.test(label + ': optionId 一致', function () {{
    fpExpectOptionIdMatch(label, fpResolveOptionId(data()));
  }});
}}
function fpAssertUsageOrderListItemCore(label, item) {{
  pm.expect(item.category, label + ' category').to.eql(2);
  pm.expect(item.module, label + ' module').to.eql(fpExpectedModule());
  var rid = fpResolveListItemField(item, 'resourceId', 'resourceId');
  pm.expect(rid, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  fpExpectResourceIdMatch(label, rid);
  var opt = fpResolveOptionId(item);
  pm.expect(opt, label + ' optionId 非空').to.be.a('string').and.not.empty;
  fpExpectOptionIdMatch(label, opt);
  pm.expect(fpResolveTransportHubName(item), label + ' transportHubName').to.eql(null);
  pm.expect(fpResolveTransportHubId(item), label + ' transportHubId').to.eql(null);
}}
function fpAssertUsageOrderInListActive(label) {{
  fpAssertHttpBusinessOk(label);
  fpAssertOrderListPagination(label, false, true);
  fpAssertNoOtherModuleInEpassList(label);
  pm.test(label + ': orders 含 usageOrderId 且 status=1', function () {{
    var data = fpGetInnerData(pm.response.json());
    var oid = fpGetVar('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    pm.expect(data.orders.length, 'orders 不应为空').to.be.above(0);
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usageOrderId=' + oid).to.be.above(0);
    var item = hit[0];
    pm.expect(item.status).to.eql(1);
    fpAssertUsageOrderListItemCore(label, item);
    if (Object.prototype.hasOwnProperty.call(item, 'orderCancelledDate')) {{
      pm.expect(item.orderCancelledDate).to.eql(null);
    }}
    var used = fpResolveListItemField(item, 'usedUsages', 'usedUsages');
    pm.expect(used, label + ' usedUsages').to.eql(1);
    var usageDate = fpResolveListItemField(item, 'usageDate', 'usageDate');
    if (usageDate !== undefined) {{
      pm.expect(usageDate).to.eql(null);
    }}
    var ep = fpResolveEPassIdFromRoot(item);
    if (ep) {{
      pm.expect(ep).to.eql(fpGetVar('ePassId'));
    }}
    var cid = fpResolveListItemField(item, 'clientUserId', 'clientUserId');
    if (cid) {{
      pm.expect(cid).to.eql(fpGetVar('clientUserId'));
    }}
  }});
}}
function fpAssertPrebookingOrderSuccess(label) {{
  fpAssertUsageOrderCreateSuccess(label, true);
}}
function fpAssertBundleOrderSuccess(label) {{
  fpAssertUsageOrderCreateSuccess(label, false);
  pm.test(label + ': 写入 usageOrderId', function () {{
    pm.expect(fpGetVar('usageOrderId')).to.be.ok;
  }});
}}
function fpAssertUsageDetailsCore(label, expectCancelled) {{
  var data = function () {{ return fpGetInnerData(pm.response.json()); }};
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {{
    pm.expect(data().orderId).to.eql(fpGetVar('usageOrderId'));
  }});
  pm.test(label + ': module=epassModule', function () {{ fpAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': extra.usedUsages=1', function () {{ pm.expect(data().extra.usedUsages).to.eql(1); }});
  pm.test(label + ': extra.usageDate=null', function () {{ pm.expect(data().extra.usageDate).to.eql(null); }});
  pm.test(label + ': ePassId 一致', function () {{
    pm.expect(fpResolveEPassIdFromRoot(data())).to.eql(fpGetVar('ePassId'));
  }});
  pm.test(label + ': extra.clientUserId 一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(fpGetVar('clientUserId'));
  }});
  pm.test(label + ': extra.resourceId 一致', function () {{
    pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get('{fitness_resource_var}'));
  }});
  fpAssertBookingCounts(label);
  if (expectCancelled) {{
    pm.test(label + ': status=3 CANCELLED', function () {{ pm.expect(data().status).to.eql(3); }});
    pm.test(label + ': orderCancelledDate 有值', function () {{
      pm.expect(data().orderCancelledDate).to.not.eql(null);
      pm.expect(data().orderCancelledDate).to.be.a('string').and.not.empty;
    }});
  }} else {{
    pm.test(label + ': status=1 或 5（非 10 FAILED）', function () {{
      var st = data().status;
      if (st === 10) {{
        pm.expect.fail(label + ': 订单 status=10 FAILED');
      }}
      pm.expect(fpOrderStatusActiveOrProcessing, label + ' status').to.include(st);
    }});
    pm.test(label + ': orderCancelledDate=null', function () {{
      pm.expect(data().orderCancelledDate).to.eql(null);
    }});
  }}
}}
function fpAssertNoOtherModuleInEpassList(label) {{
  pm.test(label + ': module=epassModule 列表不含 otherModule 数据', function () {{
    pm.expect(fpIsBusinessSuccess(pm.response.json())).to.be.true;
    var data = fpGetInnerData(pm.response.json());
    if (!data || typeof data !== 'object') return;
    if (!Array.isArray(data.orders)) return;
    var other = fpOtherModule();
    var hits = data.orders.filter(function (o) {{ return o && o.module === other; }});
    pm.expect(hits.length, 'epassModule orders 不应含 otherModule=' + other + ' 条目').to.eql(0);
  }});
}}
function fpAssertNoFitnessReturnedWithOtherModuleFilter(label) {{
  pm.test(label + ': otherModule 不返回 fitness 数据', function () {{
    var env = pm.response.json();
    if (env && env.code === -1) {{
      console.warn(label + ': otherModule 返回业务失败，视为隔离通过 errCode=' + env.errCode);
      return;
    }}
    pm.expect(fpIsBusinessSuccess(env), label + ' business success 或 code=-1').to.be.true;
    var data = fpGetInnerData(env);
    if (data === null || data === undefined) return;
    if (typeof data !== 'object') return;
    var expectedUsage = fpGetVar('usageOrderId');
    var expectedPurchase = fpGetVar('purchaseOrderId');
    var expectedEPass = fpGetVar('ePassId');
    var fitnessMod = fpExpectedModule();
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
      var fitnessItems = data.orders.filter(function (o) {{ return o && o.module === fitnessMod; }});
      pm.expect(fitnessItems.length, 'otherModule orders 不应含 epassModule 条目').to.eql(0);
      return;
    }}
    pm.expect(data.module, 'otherModule details 不应返回 epassModule').to.not.eql(fitnessMod);
    if (expectedUsage && data.orderId) {{
      pm.expect(data.orderId, 'otherModule details 不应返回 fitness usageOrderId').to.not.eql(expectedUsage);
    }}
    var ep = fpResolveEPassIdFromRoot(data);
    if (expectedEPass && ep && data.module === fitnessMod) {{
      pm.expect(ep, 'otherModule details 不应返回 fitness ePassId').to.not.eql(expectedEPass);
    }}
  }});
}}
function fpAssertUsageListContainsCancelled(label) {{
  pm.test(label + ': orders 含 usageOrderId 且 status=3', function () {{
    var data = fpGetInnerData(pm.response.json());
    var oid = fpGetVar('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    if (!data.orders.length) {{
      console.warn('orders 为空（canary 索引延迟），跳过取消态断言');
      return;
    }}
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usage orderId=' + oid).to.be.above(0);
    pm.expect(hit[0].status).to.eql(3);
    if (Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(fpExpectedModule());
    }}
  }});
}}
function fpAssertSearchActiveAfterUsageCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return fpGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    fpAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED（MS 单未取消）', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': purchaseOrderId 仍可查', function () {{
    pm.expect(dataFn().orderId).to.eql(fpGetVar('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(fpResolveEPassId(dataFn().extra)).to.eql(fpGetVar('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    fpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function fpAssertSearchCancelledAfterPurchaseCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return fpGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=3 CANCELLED', function () {{
    pm.expect(dataFn().status).to.eql(3);
  }});
  pm.test(label + ': extra.ePassStatus=3 Cancelled', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(3);
  }});
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    pm.expect(dataFn().orderId).to.eql(fpGetVar('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(fpResolveEPassId(dataFn().extra)).to.eql(fpGetVar('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    fpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
""".strip()
    return [ln for ln in js.split("\n")]


def Lines_Auth() -> List[str]:
    return [
        "fpAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 写入集合变量', function () {",
        "  var d = fpGetInnerData(pm.response.json());",
        "  var t = (d && (d.accessToken || d.token || d.access_token));",
        "  pm.expect(t).to.be.ok;",
        "  pm.expect(pm.collectionVariables.get('accessToken')).to.be.ok;",
        "});",
    ]


def AvailabilityBody(*, with_epass: bool) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{fitnessResourceId}}",
        "optionId": "{{fitnessOptionId}}",
        "prebookingDate": "{{prebookingDate}}",
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


def FitnessRequestItem(**kwargs: Any) -> JsonObject:
    """每步前置把后置提取的 runtime id 写进 body（``{{clientUserId}}`` 等跨步常不展开）。"""
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["fpApplyRuntimeIdsToRequestBody();"]
    return RequestItem(**kwargs)


def Prerequest_ApplyScheduleSlot() -> List[str]:
    """前置：把 schedule 写入的 optionId / prebookingDate 强制写进本步 body。"""
    return ["fpApplyScheduleToRequestBody();"]


def Prerequest_SyncPrebookingDateFromApifox() -> List[str]:
    return [
        "var pb = pm.variables.replaceIn(" + json.dumps(PREBOOKING_DATE_APIFOX) + ");",
        "fpSetVar('prebookingDate', pb);",
    ]


def Prerequest_ClearCancelDoneFlags() -> List[str]:
    return [
        "pm.collectionVariables.unset('fpCancelDone_usageOrderId');",
        "pm.collectionVariables.unset('fpCancelDone_purchaseOrderId');",
    ]


def Prerequest_NewClientUserId() -> List[str]:
    return [
        *Prerequest_ClearCancelDoneFlags(),
        "fpUnsetVar('clientUserId');",
    ]


def Prerequest_ClearCancelRetryAttempts() -> List[str]:
    return list(Prerequest_ClearCancelDoneFlags())


def BuildCancelWithRetryBlock(
    *,
    purpose: str,
    step_prefix: str,
    order_id_var: str,
    skip_to_request_name: Optional[str],
    description: str,
    body: Optional[str] = None,
) -> List[JsonObject]:
    cancel_body = body if body is not None else CancelOrderBody(order_id_var)
    items: List[JsonObject] = []
    max_att = GENERATED_CANCEL_ATTEMPTS
    skip_json = json.dumps(skip_to_request_name) if skip_to_request_name else "null"
    for attempt in range(1, max_att + 1):
        step_id = step_prefix if attempt == 1 else f"{step_prefix}-R{attempt}"
        attempt_purpose = purpose if attempt == 1 else f"{purpose}（第{attempt}次）"
        prerequest: Optional[List[str]] = None
        if attempt > 1 and skip_to_request_name:
            prerequest = [
                f"fpPrerequestSkipCancelIfDone('{order_id_var}', {skip_json});",
            ]
        items.append(
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName(attempt_purpose, step_id, "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=cancel_body,
                headers=BearerJsonHeaders(),
                description=description if attempt == 1 else f"{description} · 第 {attempt} 次",
                prerequest_lines=prerequest,
                test_lines=Lines_Step(
                    step_id,
                    [
                        f"fpCancelOrderAttempt('{step_id}', '{order_id_var}', {attempt}, "
                        f"{max_att}, {skip_json});",
                    ],
                ),
            )
        )
    return items


def Prerequest_ResetForPrebooking() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        "fpUnsetVar('clientUserId');",
        "fpUnsetVar('ePassId');",
        "fpUnsetVar('purchaseOrderId');",
        "fpUnsetVar('usageOrderId');",
        "fpUnsetVar('prebookingToken');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        "fpUnsetVar('clientUserId');",
        "fpUnsetVar('ePassId');",
        "fpUnsetVar('purchaseOrderId');",
        "fpUnsetVar('usageOrderId');",
        "fpUnsetVar('prebookingToken');",
    ]


def BuildCreateE2EFolder() -> JsonObject:
    e01_i08_name = PurposeName(
        "otherModule=11 列表不含 fitness（取消 MS 后）", "E01-I08", "POST", "/ePasses?module=11"
    )
    return Folder(
        "E01 · tc-P0 创建",
        [
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("创建 fitness ePass（MS 购买单）", "E01-S01", "POST", "/fitness/ePasses"),
                method="POST",
                url_path="/v2/orders/fitness/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassCreateCoreFields`` · ``ExtractCreateEpassIds``",
                prerequest_lines=Prerequest_NewClientUserId(),
                test_lines=Lines_Step(
                    "E01-S01",
                    ["fpAssertHttpBusinessOk('E01-S01');", "fpAssertCreateCoreFields('E01-S01');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("users 列表含本 clientUserId 的 ePass", "E01-S02", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E01-S02",
                    ["fpAssertHttpBusinessOk('E01-S02');", "fpAssertUserListContains('E01-S02');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("search 按 purchaseOrderId 查 MS 详情", "E01-S03", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by orderId · status=1 usedUsages=0",
                test_lines=Lines_Step(
                    "E01-S03",
                    ["fpAssertHttpBusinessOk('E01-S03');", "fpAssertSearchPurchaseDetails('E01-S03', true);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("search 按 ePassId 查 MS 详情", "E01-S04", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E01-S04",
                    ["fpAssertHttpBusinessOk('E01-S04');", "fpAssertSearchPurchaseDetails('E01-S04', true);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("usage 订单列表（创建后可为空）", "E01-S05", "POST", "/ePasses?module=7"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``PostOrdersEPassesList`` · 创建后 orders 可能为空",
                test_lines=Lines_Step(
                    "E01-S05",
                    [
                        "fpAssertHttpBusinessOk('E01-S05');",
                        "fpAssertOrderListPagination('E01-S05', true, true);",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("otherModule=11 列表不含 fitness 订单（取消 MS 前）", "E01-I06", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertFitnessNotReturnedWithOtherModuleFilter`` · 取消 MS 前",
                test_lines=Lines_Step("E01-I06", ["fpAssertNoFitnessReturnedWithOtherModuleFilter('E01-I06');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("module=7 列表不含 otherModule 数据（取消 MS 前）", "E01-I07", "POST", "/ePasses?module=7"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 前",
                test_lines=Lines_Step(
                    "E01-I07",
                    ["fpAssertHttpBusinessOk('E01-I07');", "fpAssertNoOtherModuleInEpassList('E01-I07');"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单",
                step_prefix="E01-S06",
                order_id_var="purchaseOrderId",
                skip_to_request_name=e01_i08_name,
                description="``AssertHistoricalCancelOrderSuccess``",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=e01_i08_name,
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertFitnessNotReturnedWithOtherModuleFilter`` · 取消 MS 后",
                test_lines=Lines_Step("E01-I08", ["fpAssertNoFitnessReturnedWithOtherModuleFilter('E01-I08');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("module=7 列表不含 otherModule（取消 MS 后）", "E01-I09", "POST", "/ePasses?module=7"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 后",
                test_lines=Lines_Step(
                    "E01-I09",
                    ["fpAssertHttpBusinessOk('E01-I09');", "fpAssertNoOtherModuleInEpassList('E01-I09');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消后 usage 订单列表分页", "E01-S07", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertOrderListPaginationShape``",
                test_lines=Lines_Step(
                    "E01-S07",
                    [
                        "fpAssertHttpBusinessOk('E01-S07');",
                        "fpAssertOrderListPagination('E01-S07', true, true);",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消后 search 显示 ePass Cancelled", "E01-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E01-S08",
                    [
                        "fpAssertHttpBusinessOk('E01-S08');",
                        "fpAssertSearchCancelledAfterPurchaseCancel('E01-S08');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Fitness_E2E_CreateMainChain`` · "
            "``RunHistoricalEpassCreateMainE2EScenario(catalog_label='fitness')``"
        ),
    )


def BuildPrebookingE2EFolder() -> JsonObject:
    e02_s08_name = PurposeName("取消后 usage 详情 status=3", "E02-S08", "POST", "/ePasses/details")
    return Folder(
        "E02 · tc-P0 预约",
        [
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("预约链前置：创建 fitness ePass", "E02-S01", "POST", "/fitness/ePasses"),
                method="POST",
                url_path="/v2/orders/fitness/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="Prebooking 前置：创建 ePass",
                prerequest_lines=Prerequest_ResetForPrebooking(),
                test_lines=Lines_Step(
                    "E02-S01",
                    ["fpAssertHttpBusinessOk('E02-S01');", "fpAssertCreateCoreFields('E02-S01');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("schedule 解析 optionId 与 prebookingDate", "E02-S01a", "GET", "/fitness/.../schedule"),
                method="GET",
                url_path=FITNESS_SCHEDULE_URL_PATH,
                body=None,
                headers=BearerJsonHeaders(),
                description="``ResolveHistoricalFitnessScheduleTargets`` · Apifox 动态 startDate/endDate (+5 ~ +10 天)",
                prerequest_lines=[],
                test_lines=Lines_Step("E02-S01a", ["fpParseFitnessSchedule('E02-S01a');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("可用性查询并获取 prebookingToken（有 ePassId）", "E02-S02", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=True),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingToken`` · prebookingDate 由 schedule 写入，前置强制改写 body",
                prerequest_lines=Prerequest_ApplyScheduleSlot(),
                test_lines=Lines_Step(
                    "E02-S02",
                    ["fpAssertHttpBusinessOk('E02-S02');", "fpAssertAvailabilitySuccess('E02-S02');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("fitness 预约下单成功（usage 单）", "E02-S03", "POST", "/fitness/ePasses/prebooking"),
                method="POST",
                url_path="/v2/orders/fitness/ePasses/prebooking",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "ePassId": "{{ePassId}}",
                        "extra": FitnessPrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalPrebookingOrderSuccessForCatalog``（fitness）· extra.optionId 由 schedule 写入",
                prerequest_lines=Prerequest_ApplyScheduleSlot(),
                test_lines=Lines_Step(
                    "E02-S03",
                    [
                        "fpAssertHttpBusinessOk('E02-S03');",
                        "fpAssertPrebookingOrderSuccess('E02-S03');",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("预约后 module=7 列表含 usage 单", "E02-S04", "POST", "/ePasses?module=7"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="预约成功后 module=7 订单列表",
                test_lines=Lines_Step("E02-S04", ["fpAssertUsageOrderInListActive('E02-S04');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("otherModule=11 列表不含 fitness usage 单", "E02-S05", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertFitnessNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E02-S05", ["fpAssertNoFitnessReturnedWithOtherModuleFilter('E02-S05');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("usage 订单详情（取消前）", "E02-S06", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E02-S06",
                    ["fpAssertHttpBusinessOk('E02-S06');", "fpAssertUsageDetailsCore('E02-S06', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 usage 预订单",
                step_prefix="E02-S07",
                order_id_var="usageOrderId",
                skip_to_request_name=e02_s08_name,
                description="``CancelHistoricalUsageOrderAndVerify`` · prebooking usage 单取消",
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=e02_s08_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E02-S08",
                    ["fpAssertHttpBusinessOk('E02-S08');", "fpAssertUsageDetailsCore('E02-S08', true);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消后列表含 usage 单且 status=3", "E02-S09", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E02-S09",
                    [
                        "fpAssertHttpBusinessOk('E02-S09');",
                        "fpAssertOrderListPagination('E02-S09', false);",
                        "fpAssertUsageListContainsCancelled('E02-S09');",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消 usage 后 MS search 仍 Active", "E02-S10", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E02-S10",
                    ["fpAssertHttpBusinessOk('E02-S10');", "fpAssertSearchActiveAfterUsageCancel('E02-S10');"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（预约链收尾）",
                step_prefix="E02-S11",
                order_id_var="purchaseOrderId",
                skip_to_request_name=None,
                description="``CancelHistoricalPurchaseOrderAndVerify``",
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Fitness_E2E_PrebookingMainChain`` · "
            "``RunHistoricalEpassPrebookingMainE2EScenario(catalog_label='fitness')`` · "
            "运行前填 fitnessResourceId（``DP_HIST_EPASS_FITNESS_RESOURCE_ID``）；optionId/prebookingDate 由 schedule 步骤写入"
        ),
    )


def BuildBundleE2EFolder() -> JsonObject:
    e03_s10_name = PurposeName("取消后 usage 详情 status=3", "E03-S10", "POST", "/ePasses/details")
    e03_s14_name = PurposeName("取消 MS 后 search 显示 Cancelled", "E03-S14", "POST", "/ePasses/search")
    return Folder(
        "E03 · tc-P0 Bundle",
        [
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle 前置：schedule 解析 option 与时段", "E03-S00", "GET", "/fitness/.../schedule"),
                method="GET",
                url_path=FITNESS_SCHEDULE_URL_PATH,
                body=None,
                headers=BearerJsonHeaders(),
                description="``ResolveHistoricalFitnessScheduleTargets`` · Apifox 动态 startDate/endDate (+5 ~ +10 天)",
                prerequest_lines=[],
                test_lines=Lines_Step("E03-S00", ["fpParseFitnessSchedule('E03-S00');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle 可用性（无 ePassId）取 token", "E03-S01", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=False),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingTokenWithoutEpass`` · schedule 已写入 prebookingDate，前置强制改写 body",
                prerequest_lines=[*Prerequest_ResetForBundle(), *Prerequest_ApplyScheduleSlot()],
                test_lines=Lines_Step(
                    "E03-S01",
                    ["fpAssertHttpBusinessOk('E03-S01');", "fpAssertAvailabilitySuccess('E03-S01');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle 一步下单（创建 ePass+usage）", "E03-S02", "POST", "/fitness/ePasses/bundle"),
                method="POST",
                url_path="/v2/orders/fitness/ePasses/bundle",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "clientUserId": "{{$string.uuid}}",
                        "extra": FitnessPrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalBundleOrderSuccess``（fitness）· extra.optionId 由 schedule 写入",
                prerequest_lines=Prerequest_ApplyScheduleSlot(),
                test_lines=Lines_Step(
                    "E03-S02",
                    [
                        "fpAssertHttpBusinessOk('E03-S02');",
                        "fpAssertBundleOrderSuccess('E03-S02');",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle 后 module=7 列表含 usage 单", "E03-S03", "POST", "/ePasses?module=7"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="Bundle 成功后 module=7 订单列表",
                test_lines=Lines_Step("E03-S03", ["fpAssertUsageOrderInListActive('E03-S03');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("otherModule=11 列表不含 fitness Bundle 单", "E03-S04", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertFitnessNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E03-S04", ["fpAssertNoFitnessReturnedWithOtherModuleFilter('E03-S04');"]),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle usage 详情（取消前）", "E03-S05", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E03-S05",
                    ["fpAssertHttpBusinessOk('E03-S05');", "fpAssertUsageDetailsCore('E03-S05', false);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("Bundle 后 users 列表含 ePass", "E03-S06", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E03-S06",
                    ["fpAssertHttpBusinessOk('E03-S06');", "fpAssertUserListContains('E03-S06');"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("search 按 ePassId（usedUsages=1）", "E03-S07", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后 search by ePassId",
                test_lines=Lines_Step(
                    "E03-S07",
                    ["fpAssertHttpBusinessOk('E03-S07');", "fpAssertSearchPurchaseDetails('E03-S07', true, false, 2, 1);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("search 按 purchaseOrderId（Bundle 后）", "E03-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后二次 search by orderId",
                test_lines=Lines_Step(
                    "E03-S08",
                    ["fpAssertHttpBusinessOk('E03-S08');", "fpAssertSearchPurchaseDetails('E03-S08', true, false, 2, 1);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 Bundle usage 单",
                step_prefix="E03-S09",
                order_id_var="usageOrderId",
                skip_to_request_name=e03_s10_name,
                description="Bundle usage 单取消 · ``PatchCancelOrderWithRetry``",
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=e03_s10_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E03-S10",
                    ["fpAssertHttpBusinessOk('E03-S10');", "fpAssertUsageDetailsCore('E03-S10', true);"],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消后列表含 usage 单", "E03-S11", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E03-S11",
                    [
                        "fpAssertHttpBusinessOk('E03-S11');",
                        "fpAssertOrderListPagination('E03-S11', false);",
                        "fpAssertUsageListContainsCancelled('E03-S11');",
                    ],
                ),
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("取消 usage 后 search 仍 Active", "E03-S12", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E03-S12",
                    ["fpAssertHttpBusinessOk('E03-S12');", "fpAssertSearchActiveAfterUsageCancel('E03-S12', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（Bundle 收尾）",
                step_prefix="E03-S13",
                order_id_var="purchaseOrderId",
                skip_to_request_name=e03_s14_name,
                description="``CancelHistoricalPurchaseOrderAndVerify``",
            ),
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=e03_s14_name,
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E03-S14",
                    [
                        "fpAssertHttpBusinessOk('E03-S14');",
                        "fpAssertSearchCancelledAfterPurchaseCancel('E03-S14', false);",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Fitness_E2E_BundleMainChain`` · "
            "``RunHistoricalEpassBundleMainE2EScenario(catalog_label='fitness')`` · "
            "运行前填 fitnessResourceId（``DP_HIST_EPASS_FITNESS_RESOURCE_ID``）；optionId/prebookingDate 由 schedule 步骤写入"
        ),
    )


def BuildCollection() -> JsonObject:
    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            FitnessRequestItem(
                js_helpers=BuildFitnessJsHelpersLines,
                name=PurposeName("获取 ePass 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken（fitness 的 prebookingDate 由 schedule 步骤写入）。",
                save_token=True,
                test_lines=Lines_Auth(),
                prerequest_lines=[],
            ),
        ],
        description="先执行本文件夹。",
    )

    info: JsonObject = {
        "name": "fitness ePass · P0 E2E 核心",
        "description": (
            "由 GeneratePostmanCollectionFitnessEpass.py 生成。\n\n"
            "**三条 P0 E2E 核心链路**（对齐 ``RunHistoricalEpass*MainE2EScenario(catalog_label='fitness')``）：\n"
            "- E01 创建验证链（含 module=7 / otherModule=11 双向隔离）\n"
            "- E02 预约验证链（options 可用性 · module=7）\n"
            "- E03 Bundle 一步下单\n\n"
            "每个 HTTP 步骤含多条 pm.test 字段级断言；请求名格式 **【目的】| 步骤号 | METHOD 路径**（与 Local Offer P1 pytest-sync 一致）。\n\n"
            "**必填变量**：ProgramID、clientId、secret；E02/E03 另填 fitnessResourceId。\n"
            f"**fitness 网点**：``{FITNESS_RESOURCE_ID_VAR}`` 对齐 ``{ENV_FITNESS_RESOURCE_ID}``"
            f"（默认 {DEFAULT_FITNESS_RESOURCE_ID}）；``fitnessOptionId``/``prebookingDate`` 由 E02/E03 的 schedule 步骤写入 "
            "（``fpSetVar`` 写 variables+collection，可用性/下单前置 ``fpApplyScheduleToRequestBody`` 强制改写 body；"
            "不回写共用 Environment）。\n"
            "**clientUserId**：创建/Bundle body 仍用 ``{{$string.uuid}}`` 发出；后置 ``fpCaptureClientUserIdAfterSend`` "
            "从响应（若实际请求已解析则优先请求体）提取并 ``fpSetVar``，再断言 UUID 回显；"
            "后续步前置 ``fpApplyRuntimeIdsToRequestBody`` 把提取值写进 ``{{clientUserId}}`` / ``orderId`` 等。"
            "禁止前置 ``replaceIn('{{$string.uuid}}')``（Apifox 常不展开，会把模板拿去当期望）。\n"
            "**品类 module**：epassModule=7、otherModule=11（断言动态读取）。\n"
            "**schedule 窗口**：GET schedule 使用 Apifox 表达式 "
            "``startDate={{$date.now|addDays(5)|format('yyyy-MM-dd')}}``、"
            "``endDate={{$date.now|addDays(10)|format('yyyy-MM-dd')}}``、``fallbackAllowed=true``。\n"
            "**预约 extra**：含 ``prebookingRequiredInfo`` + ``optionId``（对齐 ``PostHistoricalEpassPrebooking``）。"
            "订单详情 ``extra.bookingCounts`` 等于可用性 ``adultCount+childCount``（默认 1+0=1；取消后不变）。\n"
            "**创建 availableUsages**：默认 2（对齐 pytest ``CreateHistoricalEpass``）。\n"
            "取消订单：线性 PATCH 最多 3 次（无 WAIT 间隔）；成功则向前 skip 剩余重试步骤；"
            "对齐 ``PatchCancelOrderWithRetry`` 可重试错误 ``Order cancellation failed``。\n"
            "**Apifox 兼容**：fp helpers 注入各 HTTP 步骤 test（及含 fp 的 pre-request）。\n"
            "**可选**：x-version（canary）。"
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
        CollectionVariable("fitnessPreferredOptionType", "1"),
        CollectionVariable(FITNESS_RESOURCE_ID_VAR, DEFAULT_FITNESS_RESOURCE_ID),
        CollectionVariable("fitnessOptionId", ""),
        CollectionVariable("fitnessAvailabilityResourceId", ""),
        CollectionVariable("fitnessAvailabilityOptionId", ""),
        CollectionVariable("fitnessCancelMaxAttempts", str(GENERATED_CANCEL_ATTEMPTS)),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("prebookingToken", ""),
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


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection())
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
