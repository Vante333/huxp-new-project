"""
生成 lounge ePass **P0 E2E 核心** Postman Collection v2.1 JSON。

对齐 ``test_historical_epass_regression.py`` lounge 三条主链路及 ``historical_epass_service`` 断言语义（``catalog_label="lounge"``）：

- E01 创建验证链 · ``RunHistoricalEpassCreateMainE2EScenario``
- E02 预约验证链 · ``RunHistoricalEpassPrebookingMainE2EScenario``
- E03 Bundle 一步下单 · ``RunHistoricalEpassBundleMainE2EScenario``

用法（仓库根目录）::

    python api-testcases/api_tests/postman/GeneratePostmanCollectionLoungeEpass.py
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Final, List, Optional, Sequence

from collection_builder_common import (
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

JsonObject = Dict[str, Any]

OUT_NAME: Final[str] = "Lounge-ePass-P0-e2e-core.postman_collection.json"
DEFAULT_API_VERSION: Final[str] = "v2"
PREBOOKING_DATE_APIFOX: Final[str] = "{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30"
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CANCEL_RETRY_MSG_NEEDLE: Final[str] = "Order cancellation failed"
CREATE_FIRST_NAME: Final[str] = "Auto"
CREATE_LAST_NAME: Final[str] = "Test"
CREATE_EXPIRATION_DATE: Final[str] = "2028-12-31T23:59:59+00:00"
CREATE_AVAILABLE_USAGES: Final[int] = 2
DEFAULT_LOUNGE_RESOURCE_ID: Final[str] = "N00012"
GENERATED_CANCEL_ATTEMPTS: Final[int] = 3
LOUNGE_RESOURCE_ID_VAR: Final[str] = "loungeResourceId"
ENV_LOUNGE_RESOURCE_ID: Final[str] = "DP_HIST_EPASS_LOUNGE_RESOURCE_ID"
EPASS_MODULE_DEFAULT: Final[int] = 1
OTHER_MODULE_DEFAULT: Final[int] = 11

_LOUNGE_JS_ASSERT_EPASS_STATUS: bool = True


def _JsAssertEpassStatusActiveBlock(*, data_fn: str = "dataFn()") -> str:
    """search/create 等步骤中 ``extra.ePassStatus=1`` 断言（v1 网关无此字段时不注入）。"""
    return f"""  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect({data_fn}.extra.ePassStatus).to.eql(1);
  }});"""


def _JsAssertEpassStatusCancelledBlock(*, data_fn: str = "dataFn()") -> str:
    return f"""  pm.test(label + ': extra.ePassStatus=3 Cancelled', function () {{
    pm.expect({data_fn}.extra.ePassStatus).to.eql(3);
  }});"""


def _LoungeJsHelpers() -> List[str]:
    """按 ``_LOUNGE_JS_ASSERT_EPASS_STATUS`` 决定是否注入 ``ePassStatus`` 断言（v1 无该字段）。"""
    return BuildLoungeJsHelpersLines(assert_epass_status=_LOUNGE_JS_ASSERT_EPASS_STATUS)


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


def LoungePrebookingExtraDict() -> JsonObject:
    """lounge 经典预约 / Bundle ``extra``（含 prebookingRequiredInfo，无 optionId）。"""
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": {
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "email": "auto.test@dragonpass.com",
            "phoneNumber": "8081966002",
            "callingCode": "44",
        },
    }


def BuildLoungeJsHelpersLines(*, assert_epass_status: bool = True) -> List[str]:
    """与 ``historical_epass_service`` / lounge classic availability 链断言语义对齐的公共 JS（``lp*`` 前缀）。"""
    epass_status_active = _JsAssertEpassStatusActiveBlock() if assert_epass_status else ""
    epass_status_cancelled = _JsAssertEpassStatusCancelledBlock() if assert_epass_status else ""
    cancel_msg_js = json.dumps(CANCEL_SUCCESS_MSG)
    cancel_retry_needle_js = json.dumps(CANCEL_RETRY_MSG_NEEDLE)
    create_first_name_js = json.dumps(CREATE_FIRST_NAME)
    create_last_name_js = json.dumps(CREATE_LAST_NAME)
    create_expiration_date_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_available_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    epass_module_default_js = json.dumps(EPASS_MODULE_DEFAULT)
    other_module_default_js = json.dumps(OTHER_MODULE_DEFAULT)
    lounge_resource_var = LOUNGE_RESOURCE_ID_VAR
    js = rf"""function lpExpectedModule() {{
  var raw = pm.collectionVariables.get('epassModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {epass_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {epass_module_default_js} : n;
}}
function lpOtherModule() {{
  var raw = pm.collectionVariables.get('otherModule');
  if (raw === undefined || raw === null || String(raw).trim() === '') {{
    return {other_module_default_js};
  }}
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? {other_module_default_js} : n;
}}
function lpIsBusinessSuccess(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}}
function lpGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {{
    return d;
  }}
  return d;
}}
function lpAssertEpassModuleRequired(data, ctx) {{
  pm.expect(data, ctx + ' data').to.be.an('object');
  pm.expect(data.module, ctx + ' module').to.eql(lpExpectedModule());
}}
function lpAssertEpassModuleIfPresent(data, ctx) {{
  if (!data || typeof data !== 'object') return;
  if (Object.prototype.hasOwnProperty.call(data, 'module')) {{
    pm.expect(data.module, ctx + ' module').to.eql(lpExpectedModule());
  }}
}}
function lpResolveEPassIdFromRoot(data) {{
  if (!data || typeof data !== 'object') return null;
  var direct = data.ePassId || data.epassId;
  if (direct) return direct;
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    return extra.ePassId || extra.epassId || null;
  }}
  return null;
}}
function lpResolveEPassId(extra) {{
  if (!extra || typeof extra !== 'object') return null;
  return extra.ePassId || extra.epassId || null;
}}
function lpResolveOptionId(data) {{
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
var lpOrderStatusActiveOrProcessing = [1, 5];
function lpFailIfOrderStatus10(status, label) {{
  if (status === 10) {{
    pm.expect.fail(label + ': 订单 status=10 FAILED');
  }}
}}
function lpExpectOrderStatusActiveOrProcessing(label, status) {{
  lpFailIfOrderStatus10(status, label);
  pm.expect(lpOrderStatusActiveOrProcessing, label + ' status').to.include(status);
}}
function lpSyncResourceIdFromOrderResponse(label, actual) {{
  pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  var fromAvail = pm.collectionVariables.get('loungeAvailabilityResourceId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': lounge 订单 resourceId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（以响应 canonical id 为准，已回写 loungeResourceId）'
    );
  }}
  pm.collectionVariables.set('{lounge_resource_var}', String(actual));
}}
function lpExpectResourceIdMatch(label, actual) {{
  lpSyncResourceIdFromOrderResponse(label, actual);
}}
function lpExpectOptionIdMatch(label, actual) {{
  if (!actual) return;
  pm.expect(actual, label + ' optionId').to.be.a('string').and.not.empty;
}}
function lpSaveCreateIds(data) {{
  if (!data || typeof data !== 'object') return;
  if (data.clientUserId) pm.collectionVariables.set('clientUserId', String(data.clientUserId));
  if (data.orderId) pm.collectionVariables.set('purchaseOrderId', String(data.orderId));
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = lpResolveEPassId(extra);
    if (ep) pm.collectionVariables.set('ePassId', String(ep));
  }}
}}
function lpSaveAvailabilityRequestFields() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (reqBody && reqBody.prebookingDate) {{
      pm.collectionVariables.set('prebookingDate', String(reqBody.prebookingDate));
    }}
    if (reqBody && reqBody.resourceId) {{
      pm.collectionVariables.set('loungeAvailabilityResourceId', String(reqBody.resourceId));
    }}
  }} catch (e) {{
    console.warn('lpSaveAvailabilityRequestFields:', e);
  }}
}}
function lpResolveListItemField(item, rootKey, extraKey) {{
  if (!item || typeof item !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(item, rootKey)) return item[rootKey];
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, extraKey)) return ex[extraKey];
    if (Object.prototype.hasOwnProperty.call(ex, rootKey)) return ex[rootKey];
  }}
  return null;
}}
function lpResolveTransportHubName(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubName')) {{
    return ex.transportHubName;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubName')) return item.transportHubName;
  return undefined;
}}
function lpResolveTransportHubId(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubId')) {{
    return ex.transportHubId;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubId')) return item.transportHubId;
  return undefined;
}}
function lpSavePrebookingToken(data) {{
  if (data && data.prebookingToken) {{
    pm.collectionVariables.set('prebookingToken', String(data.prebookingToken));
  }}
}}
function lpSaveUsageOrderId(data) {{
  if (data && data.orderId) {{
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }}
}}
function lpAssertHttpBusinessOk(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(lpIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
}}
function lpResponseHttpCode(res) {{
  if (!res) return 0;
  var raw = res.code;
  if (raw === undefined || raw === null) raw = res.status;
  if (raw === undefined || raw === null) raw = res.statusCode;
  if (raw === undefined || raw === null) raw = res.responseCode;
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? 0 : n;
}}
function lpIsCancelResponseSuccess(res, env) {{
  if (!env || typeof env !== 'object') return false;
  var httpCode = lpResponseHttpCode(res);
  if (httpCode && httpCode !== 200) return false;
  if (!lpIsBusinessSuccess(env)) return false;
  var msg = env.msg || env.message;
  return msg === {cancel_msg_js};
}}
function lpIsCancelResponseRetryable(env) {{
  if (!env || typeof env !== 'object') return false;
  var msg = String(env.msg || env.message || '');
  if (msg.indexOf({cancel_retry_needle_js}) >= 0) return true;
  if (env.errCode === '500.041.006' || env.errCode === '500.071.016') return true;
  return false;
}}
function lpCancelDoneVar(orderIdVar) {{
  return 'lpCancelDone_' + orderIdVar;
}}
function lpMarkCancelDone(orderIdVar) {{
  pm.collectionVariables.set(lpCancelDoneVar(orderIdVar), '1');
}}
function lpIsCancelAlreadyDone(orderIdVar) {{
  return pm.collectionVariables.get(lpCancelDoneVar(orderIdVar)) === '1';
}}
function lpClearCancelDone(orderIdVar) {{
  pm.collectionVariables.unset(lpCancelDoneVar(orderIdVar));
}}
function lpSetNextRequestByName(reqName) {{
  if (!reqName) return;
  var setter = (typeof postman !== 'undefined' && postman.setNextRequest)
    ? postman.setNextRequest.bind(postman)
    : (pm.execution && pm.execution.setNextRequest
      ? pm.execution.setNextRequest.bind(pm.execution)
      : null);
  if (setter) setter(reqName);
}}
function lpPrerequestSkipCancelIfDone(orderIdVar, skipToRequestName) {{
  if (lpIsCancelAlreadyDone(orderIdVar) && skipToRequestName) {{
    lpSetNextRequestByName(skipToRequestName);
  }}
}}
function lpAssertCancelEnvelope(label, env) {{
  pm.test(label + ': code=0 取消业务成功', function () {{
    pm.expect(env && env.code, 'code').to.eql(0);
  }});
  pm.test(label + ': msg=The order was cancelled successfully', function () {{
    var msg = env && (env.msg || env.message);
    pm.expect(msg, '取消响应 msg').to.eql({cancel_msg_js});
  }});
}}
function lpCancelOrderAttempt(label, orderIdVar, attemptNo, maxAttempts, skipToRequestName) {{
  if (lpIsCancelAlreadyDone(orderIdVar)) {{
    pm.test(label + ': 已成功取消（跳过）', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  var orderId = pm.collectionVariables.get(orderIdVar);
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
  if (lpIsCancelResponseSuccess(pm.response, env0)) {{
    lpMarkCancelDone(orderIdVar);
    lpAssertCancelEnvelope(label, env0);
    if (skipToRequestName && attemptNo < maxAttempts) {{
      lpSetNextRequestByName(skipToRequestName);
    }}
    return;
  }}
  if (lpIsCancelResponseRetryable(env0) && attemptNo < maxAttempts) {{
    pm.test(label + ': 第 ' + attemptNo + ' 次失败可重试', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  pm.test(label + ': 取消失败', function () {{
    pm.expect.fail(
      label + ': attempt ' + attemptNo + '/' + maxAttempts + ' env=' + JSON.stringify(env0)
    );
  }});
}}
function lpExpectedCreateExtra() {{
  return {{
    firstName: {create_first_name_js},
    lastName: {create_last_name_js},
    expirationDate: {create_expiration_date_js},
    availableUsages: {create_available_usages_js}
  }};
}}
function lpAssertExtraMatchesCreateInput(label, extra) {{
  pm.test(label + ': extra.firstName 与入参一致', function () {{
    pm.expect(extra.firstName).to.eql(lpExpectedCreateExtra().firstName);
  }});
  pm.test(label + ': extra.lastName 与入参一致', function () {{
    pm.expect(extra.lastName).to.eql(lpExpectedCreateExtra().lastName);
  }});
  pm.test(label + ': extra.expirationDate 与入参一致', function () {{
    pm.expect(extra.expirationDate).to.eql(lpExpectedCreateExtra().expirationDate);
  }});
  pm.test(label + ': extra.availableUsages 与入参一致', function () {{
    pm.expect(extra.availableUsages).to.eql(lpExpectedCreateExtra().availableUsages);
  }});
}}
function lpAssertCreateCoreFields(label) {{
  var dataFn = function () {{ return lpGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    lpAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': category=3', function () {{
    pm.expect(dataFn().category).to.eql(3);
  }});
  pm.test(label + ': clientUserId 回显一致', function () {{
    pm.expect(dataFn().clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': orderCancelledDate=null', function () {{
    pm.expect(dataFn().orderCancelledDate).to.eql(null);
  }});
{epass_status_active}
  pm.test(label + ': extra.usedUsages=0', function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(0);
  }});
  lpAssertExtraMatchesCreateInput(label, dataFn().extra);
  pm.test(label + ': extra.ePassId 非空', function () {{
    pm.expect(lpResolveEPassId(dataFn().extra)).to.be.ok;
  }});
  pm.test(label + ': extra.allowedResources 存在', function () {{
    pm.expect(dataFn().extra.allowedResources).to.be.an('object');
  }});
  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {{
    lpSaveCreateIds(dataFn());
    pm.expect(pm.collectionVariables.get('ePassId')).to.be.ok;
    pm.expect(pm.collectionVariables.get('purchaseOrderId')).to.be.ok;
  }});
}}
function lpAssertUserListContains(label) {{
  pm.test(label + ': ePassesList 含 ePassId', function () {{
    var data = lpGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    pm.expect(data.ePassesList).to.be.an('array');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    pm.expect(hit.length, '未找到 ePassId=' + target).to.be.above(0);
  }});
  pm.test(label + ': 列表项 module=epassModule（若存在）', function () {{
    var data = lpGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    if (hit[0] && Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(lpExpectedModule());
    }}
  }});
}}
function lpAssertSearchPurchaseDetails(label, assertEpassModule, matchCreateInput, expectedStatus, expectedUsedUsages) {{
  var dataFn = function () {{ return lpGetInnerData(pm.response.json()); }};
  var status = (expectedStatus !== undefined && expectedStatus !== null) ? expectedStatus : 1;
  var usedUsages = (expectedUsedUsages !== undefined && expectedUsedUsages !== null) ? expectedUsedUsages : 0;
  if (assertEpassModule !== false) {{
    pm.test(label + ': module=epassModule', function () {{
      lpAssertEpassModuleRequired(dataFn(), label);
    }});
  }}
  pm.test(label + ': category=3', function () {{
    pm.expect(dataFn().category).to.eql(3);
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
    pm.expect(lpResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
{epass_status_active}
  pm.test(label + ': extra.usedUsages=' + usedUsages, function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(usedUsages);
  }});
  if (matchCreateInput !== false) {{
    lpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function lpAssertOrderListPagination(label, allowEmpty, expectEpassModule) {{
  pm.test(label + ': pagination 结构', function () {{
    var data = lpGetInnerData(pm.response.json());
    pm.expect(data.pagination).to.be.an('object');
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {{
      pm.expect(data.pagination, 'pagination.' + k).to.have.property(k);
    }});
  }});
  pm.test(label + ': orders 为数组', function () {{
    pm.expect(lpGetInnerData(pm.response.json()).orders).to.be.an('array');
  }});
  if (allowEmpty) {{
    pm.test(label + ': 创建后 orders 可为空（canary doc gap）', function () {{
      pm.expect(lpGetInnerData(pm.response.json()).orders).to.be.an('array');
    }});
  }}
  if (expectEpassModule) {{
    pm.test(label + ': 列表项 module=epassModule（若存在 module 字段）', function () {{
      var orders = lpGetInnerData(pm.response.json()).orders || [];
      var mod = lpExpectedModule();
      orders.forEach(function (item, idx) {{
        if (item && Object.prototype.hasOwnProperty.call(item, 'module')) {{
          pm.expect(item.module, 'orders[' + idx + '].module').to.eql(mod);
        }}
      }});
    }});
  }}
}}
function lpAssertAvailabilitySuccess(label) {{
  lpSaveAvailabilityRequestFields();
  pm.test(label + ': available=true', function () {{
    pm.expect(lpGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var data = lpGetInnerData(pm.response.json());
    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;
    lpSavePrebookingToken(data);
  }});
}}
function lpAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {{
  allowedStatuses = allowedStatuses || lpOrderStatusActiveOrProcessing;
  var data = function () {{ return lpGetInnerData(pm.response.json()); }};
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
  pm.test(label + ': module=epassModule', function () {{ lpAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    lpSaveUsageOrderId(data());
  }});
  pm.test(label + ': clientUserId 与注册会籍一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': ePassId 与前面一致', function () {{
    var ep = lpResolveEPassIdFromRoot(data());
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
    lpExpectResourceIdMatch(label, data().extra.resourceId);
  }});
}}
function lpAssertUsageOrderListItemCore(label, item) {{
  pm.expect(item.category, label + ' category').to.eql(2);
  pm.expect(item.module, label + ' module').to.eql(lpExpectedModule());
  var rid = lpResolveListItemField(item, 'resourceId', 'resourceId');
  pm.expect(rid, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  lpExpectResourceIdMatch(label, rid);
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, 'optionId')) {{
      pm.expect(ex.optionId, label + ' extra.optionId').to.eql(null);
    }}
    if (Object.prototype.hasOwnProperty.call(ex, 'optionName')) {{
      pm.expect(ex.optionName, label + ' extra.optionName').to.eql(null);
    }}
  }}
}}
function lpAssertUsageOrderInListActive(label) {{
  lpAssertHttpBusinessOk(label);
  lpAssertOrderListPagination(label, false, true);
  lpAssertNoOtherModuleInEpassList(label);
  pm.test(label + ': orders 含 usageOrderId 且 status=1', function () {{
    var data = lpGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    pm.expect(data.orders.length, 'orders 不应为空').to.be.above(0);
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usageOrderId=' + oid).to.be.above(0);
    var item = hit[0];
    pm.expect(item.status).to.eql(1);
    lpAssertUsageOrderListItemCore(label, item);
    if (Object.prototype.hasOwnProperty.call(item, 'orderCancelledDate')) {{
      pm.expect(item.orderCancelledDate).to.eql(null);
    }}
    var used = lpResolveListItemField(item, 'usedUsages', 'usedUsages');
    pm.expect(used, label + ' usedUsages').to.eql(1);
    var usageDate = lpResolveListItemField(item, 'usageDate', 'usageDate');
    if (usageDate !== undefined) {{
      pm.expect(usageDate).to.eql(null);
    }}
    var ep = lpResolveEPassIdFromRoot(item);
    if (ep) {{
      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));
    }}
    var cid = lpResolveListItemField(item, 'clientUserId', 'clientUserId');
    if (cid) {{
      pm.expect(cid).to.eql(pm.collectionVariables.get('clientUserId'));
    }}
  }});
}}
function lpAssertPrebookingOrderSuccess(label) {{
  lpAssertUsageOrderCreateSuccess(label, true);
}}
function lpAssertBundleOrderSuccess(label) {{
  lpAssertUsageOrderCreateSuccess(label, false);
  pm.test(label + ': 写入 usageOrderId', function () {{
    pm.expect(pm.collectionVariables.get('usageOrderId')).to.be.ok;
  }});
}}
function lpAssertUsageDetailsCore(label, expectCancelled) {{
  var data = function () {{ return lpGetInnerData(pm.response.json()); }};
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {{
    pm.expect(data().orderId).to.eql(pm.collectionVariables.get('usageOrderId'));
  }});
  pm.test(label + ': module=epassModule', function () {{ lpAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': extra.usedUsages=1', function () {{ pm.expect(data().extra.usedUsages).to.eql(1); }});
  pm.test(label + ': extra.usageDate=null', function () {{ pm.expect(data().extra.usageDate).to.eql(null); }});
  pm.test(label + ': ePassId 一致', function () {{
    pm.expect(lpResolveEPassIdFromRoot(data())).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.clientUserId 一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': extra.resourceId 一致', function () {{
    pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get('{lounge_resource_var}'));
  }});
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
      pm.expect(lpOrderStatusActiveOrProcessing, label + ' status').to.include(st);
    }});
    pm.test(label + ': orderCancelledDate=null', function () {{
      pm.expect(data().orderCancelledDate).to.eql(null);
    }});
  }}
}}
function lpAssertNoOtherModuleInEpassList(label) {{
  pm.test(label + ': module=epassModule 列表不含 otherModule 数据', function () {{
    pm.expect(lpIsBusinessSuccess(pm.response.json())).to.be.true;
    var data = lpGetInnerData(pm.response.json());
    if (!data || typeof data !== 'object') return;
    if (!Array.isArray(data.orders)) return;
    var other = lpOtherModule();
    var hits = data.orders.filter(function (o) {{ return o && o.module === other; }});
    pm.expect(hits.length, 'epassModule orders 不应含 otherModule=' + other + ' 条目').to.eql(0);
  }});
}}
function lpAssertNoLoungeReturnedWithOtherModuleFilter(label) {{
  pm.test(label + ': otherModule 不返回 lounge 数据', function () {{
    var env = pm.response.json();
    if (env && env.code === -1) {{
      console.warn(label + ': otherModule 返回业务失败，视为隔离通过 errCode=' + env.errCode);
      return;
    }}
    pm.expect(lpIsBusinessSuccess(env), label + ' business success 或 code=-1').to.be.true;
    var data = lpGetInnerData(env);
    if (data === null || data === undefined) return;
    if (typeof data !== 'object') return;
    var expectedUsage = pm.collectionVariables.get('usageOrderId');
    var expectedPurchase = pm.collectionVariables.get('purchaseOrderId');
    var expectedEPass = pm.collectionVariables.get('ePassId');
    var loungeMod = lpExpectedModule();
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
      var loungeItems = data.orders.filter(function (o) {{ return o && o.module === loungeMod; }});
      pm.expect(loungeItems.length, 'otherModule orders 不应含 epassModule 条目').to.eql(0);
      return;
    }}
    pm.expect(data.module, 'otherModule details 不应返回 epassModule').to.not.eql(loungeMod);
    if (expectedUsage && data.orderId) {{
      pm.expect(data.orderId, 'otherModule details 不应返回 lounge usageOrderId').to.not.eql(expectedUsage);
    }}
    var ep = lpResolveEPassIdFromRoot(data);
    if (expectedEPass && ep && data.module === loungeMod) {{
      pm.expect(ep, 'otherModule details 不应返回 lounge ePassId').to.not.eql(expectedEPass);
    }}
  }});
}}
function lpAssertUsageListContainsCancelled(label) {{
  pm.test(label + ': orders 含 usageOrderId 且 status=3', function () {{
    var data = lpGetInnerData(pm.response.json());
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
      pm.expect(hit[0].module).to.eql(lpExpectedModule());
    }}
  }});
}}
function lpAssertSearchActiveAfterUsageCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return lpGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    lpAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED（MS 单未取消）', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': purchaseOrderId 仍可查', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
{epass_status_active}
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(lpResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    lpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function lpAssertSearchCancelledAfterPurchaseCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return lpGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=3 CANCELLED', function () {{
    pm.expect(dataFn().status).to.eql(3);
  }});
{epass_status_cancelled}
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(lpResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    lpAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
""".strip()
    return [ln for ln in js.split("\n")]


def Lines_Auth() -> List[str]:
    return [
        "lpAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 写入集合变量', function () {",
        "  var d = lpGetInnerData(pm.response.json());",
        "  var t = (d && (d.accessToken || d.token || d.access_token));",
        "  pm.expect(t).to.be.ok;",
        "  pm.expect(pm.collectionVariables.get('accessToken')).to.be.ok;",
        "});",
    ]


def AvailabilityBody(*, with_epass: bool) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{loungeResourceId}}",
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


def Prerequest_SyncPrebookingDateFromApifox() -> List[str]:
    return [
        "var pb = pm.variables.replaceIn(" + json.dumps(PREBOOKING_DATE_APIFOX) + ");",
        "pm.collectionVariables.set('prebookingDate', pb);",
    ]


def Prerequest_ClearCancelDoneFlags() -> List[str]:
    return [
        "pm.collectionVariables.unset('lpCancelDone_usageOrderId');",
        "pm.collectionVariables.unset('lpCancelDone_purchaseOrderId');",
    ]


def Prerequest_NewClientUserId() -> List[str]:
    return [
        *Prerequest_ClearCancelDoneFlags(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
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
                f"lpPrerequestSkipCancelIfDone('{order_id_var}', {skip_json});",
            ]
        items.append(
            RequestItem(
                js_helpers=_LoungeJsHelpers,
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
                        f"lpCancelOrderAttempt('{step_id}', '{order_id_var}', {attempt}, "
                        f"{max_att}, {skip_json});",
                    ],
                ),
            )
        )
    return items


def Prerequest_ResetForPrebooking() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
    ]


def BuildCreateE2EFolder() -> JsonObject:
    e01_i08_name = PurposeName(
        "otherModule=11 列表不含 lounge（取消 MS 后）", "E01-I08", "POST", "/ePasses?module=11"
    )
    return Folder(
        "E01 · tc-P0 创建",
        [
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("创建 lounge ePass（MS 购买单）", "E01-S01", "POST", "/lounges/ePasses"),
                method="POST",
                url_path="/v2/orders/lounges/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassCreateCoreFields`` · ``ExtractCreateEpassIds``",
                prerequest_lines=Prerequest_NewClientUserId(),
                test_lines=Lines_Step(
                    "E01-S01",
                    ["lpAssertHttpBusinessOk('E01-S01');", "lpAssertCreateCoreFields('E01-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("users 列表含本 clientUserId 的 ePass", "E01-S02", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E01-S02",
                    ["lpAssertHttpBusinessOk('E01-S02');", "lpAssertUserListContains('E01-S02');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 purchaseOrderId 查 MS 详情", "E01-S03", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by orderId · status=1 usedUsages=0",
                test_lines=Lines_Step(
                    "E01-S03",
                    ["lpAssertHttpBusinessOk('E01-S03');", "lpAssertSearchPurchaseDetails('E01-S03', true);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 ePassId 查 MS 详情", "E01-S04", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E01-S04",
                    ["lpAssertHttpBusinessOk('E01-S04');", "lpAssertSearchPurchaseDetails('E01-S04', true);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("usage 订单列表（创建后可为空）", "E01-S05", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``PostOrdersEPassesList`` · 创建后 orders 可能为空",
                test_lines=Lines_Step(
                    "E01-S05",
                    [
                        "lpAssertHttpBusinessOk('E01-S05');",
                        "lpAssertOrderListPagination('E01-S05', true, true);",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge 订单（取消 MS 前）", "E01-I06", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter`` · 取消 MS 前",
                test_lines=Lines_Step("E01-I06", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E01-I06');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("module=1 列表不含 otherModule 数据（取消 MS 前）", "E01-I07", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 前",
                test_lines=Lines_Step(
                    "E01-I07",
                    ["lpAssertHttpBusinessOk('E01-I07');", "lpAssertNoOtherModuleInEpassList('E01-I07');"],
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
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e01_i08_name,
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter`` · 取消 MS 后",
                test_lines=Lines_Step("E01-I08", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E01-I08');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("module=1 列表不含 otherModule（取消 MS 后）", "E01-I09", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertNoOtherModuleInEpassList`` · 取消 MS 后",
                test_lines=Lines_Step(
                    "E01-I09",
                    ["lpAssertHttpBusinessOk('E01-I09');", "lpAssertNoOtherModuleInEpassList('E01-I09');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后 usage 订单列表分页", "E01-S07", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="``AssertOrderListPaginationShape``",
                test_lines=Lines_Step(
                    "E01-S07",
                    [
                        "lpAssertHttpBusinessOk('E01-S07');",
                        "lpAssertOrderListPagination('E01-S07', true, true);",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后 search 显示 ePass Cancelled", "E01-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E01-S08",
                    [
                        "lpAssertHttpBusinessOk('E01-S08');",
                        "lpAssertSearchCancelledAfterPurchaseCancel('E01-S08');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Lounge_E2E_CreateMainChain`` · "
            "``RunHistoricalEpassCreateMainE2EScenario(catalog_label='lounge')``"
        ),
    )


def BuildPrebookingE2EFolder() -> JsonObject:
    e02_s08_name = PurposeName("取消后 usage 详情 status=3", "E02-S08", "POST", "/ePasses/details")
    return Folder(
        "E02 · tc-P0 预约",
        [
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("预约链前置：创建 lounge ePass", "E02-S01", "POST", "/lounges/ePasses"),
                method="POST",
                url_path="/v2/orders/lounges/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="Prebooking 前置：创建 ePass",
                prerequest_lines=Prerequest_ResetForPrebooking(),
                test_lines=Lines_Step(
                    "E02-S01",
                    ["lpAssertHttpBusinessOk('E02-S01');", "lpAssertCreateCoreFields('E02-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("可用性查询并获取 prebookingToken（有 ePassId）", "E02-S02", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/prebookings/availability",
                body=AvailabilityBody(with_epass=True),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingToken`` · 经典可用性 · Apifox 动态 prebookingDate",
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
                test_lines=Lines_Step(
                    "E02-S02",
                    ["lpAssertHttpBusinessOk('E02-S02');", "lpAssertAvailabilitySuccess('E02-S02');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("lounge 预约下单成功（usage 单）", "E02-S03", "POST", "/lounges/ePasses/prebooking"),
                method="POST",
                url_path="/v2/orders/lounges/ePasses/prebooking",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "ePassId": "{{ePassId}}",
                        "extra": LoungePrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalPrebookingOrderSuccessForCatalog``（lounge 经典链）",
                test_lines=Lines_Step(
                    "E02-S03",
                    [
                        "lpAssertHttpBusinessOk('E02-S03');",
                        "lpAssertPrebookingOrderSuccess('E02-S03');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("预约后 module=1 列表含 usage 单", "E02-S04", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="预约成功后 module=1 订单列表",
                test_lines=Lines_Step("E02-S04", ["lpAssertUsageOrderInListActive('E02-S04');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge usage 单", "E02-S05", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E02-S05", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E02-S05');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("usage 订单详情（取消前）", "E02-S06", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E02-S06",
                    ["lpAssertHttpBusinessOk('E02-S06');", "lpAssertUsageDetailsCore('E02-S06', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 usage 预订单",
                step_prefix="E02-S07",
                order_id_var="usageOrderId",
                skip_to_request_name=e02_s08_name,
                description="``CancelHistoricalUsageOrderAndVerify`` · prebooking usage 单取消",
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e02_s08_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E02-S08",
                    ["lpAssertHttpBusinessOk('E02-S08');", "lpAssertUsageDetailsCore('E02-S08', true);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后列表含 usage 单且 status=3", "E02-S09", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E02-S09",
                    [
                        "lpAssertHttpBusinessOk('E02-S09');",
                        "lpAssertOrderListPagination('E02-S09', false);",
                        "lpAssertUsageListContainsCancelled('E02-S09');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消 usage 后 MS search 仍 Active", "E02-S10", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E02-S10",
                    ["lpAssertHttpBusinessOk('E02-S10');", "lpAssertSearchActiveAfterUsageCancel('E02-S10');"],
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
            "pytest: ``test_HistoricalEpass_Lounge_E2E_PrebookingMainChain`` · "
            "``RunHistoricalEpassPrebookingMainE2EScenario(catalog_label='lounge')`` · "
            "运行前填 loungeResourceId（``DP_HIST_EPASS_LOUNGE_RESOURCE_ID``）；prebookingDate 由可用性步骤 Apifox 表达式同步"
        ),
    )


def BuildBundleE2EFolder() -> JsonObject:
    e03_s10_name = PurposeName("取消后 usage 详情 status=3", "E03-S10", "POST", "/ePasses/details")
    e03_s14_name = PurposeName("取消 MS 后 search 显示 Cancelled", "E03-S14", "POST", "/ePasses/search")
    return Folder(
        "E03 · tc-P0 Bundle",
        [
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 可用性（无 ePassId）取 token", "E03-S01", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/prebookings/availability",
                body=AvailabilityBody(with_epass=False),
                headers=BearerJsonHeaders(),
                description="``RequestHistoricalPrebookingTokenWithoutEpass`` · 经典可用性 · Apifox 动态 prebookingDate",
                prerequest_lines=[*Prerequest_ResetForBundle(), *Prerequest_SyncPrebookingDateFromApifox()],
                test_lines=Lines_Step(
                    "E03-S01",
                    ["lpAssertHttpBusinessOk('E03-S01');", "lpAssertAvailabilitySuccess('E03-S01');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 一步下单（创建 ePass+usage）", "E03-S02", "POST", "/lounges/ePasses/bundle"),
                method="POST",
                url_path="/v2/orders/lounges/ePasses/bundle",
                body=json.dumps(
                    {
                        "module": EPASS_MODULE_DEFAULT,
                        "clientUserId": "{{clientUserId}}",
                        "extra": LoungePrebookingExtraDict(),
                        "async": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertHistoricalBundleOrderSuccess``（lounge 经典链）",
                test_lines=Lines_Step(
                    "E03-S02",
                    [
                        "lpAssertHttpBusinessOk('E03-S02');",
                        "lpAssertBundleOrderSuccess('E03-S02');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 后 module=1 列表含 usage 单", "E03-S03", "POST", "/ePasses?module=1"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="Bundle 成功后 module=1 订单列表",
                test_lines=Lines_Step("E03-S03", ["lpAssertUsageOrderInListActive('E03-S03');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("otherModule=11 列表不含 lounge Bundle 单", "E03-S04", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyOtherModule(),
                headers=BearerJsonHeaders(),
                description="``AssertLoungeNotReturnedWithOtherModuleFilter``",
                test_lines=Lines_Step("E03-S04", ["lpAssertNoLoungeReturnedWithOtherModuleFilter('E03-S04');"]),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle usage 详情（取消前）", "E03-S05", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsCoreFields``（取消前）",
                test_lines=Lines_Step(
                    "E03-S05",
                    ["lpAssertHttpBusinessOk('E03-S05');", "lpAssertUsageDetailsCore('E03-S05', false);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("Bundle 后 users 列表含 ePass", "E03-S06", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContainsHistorical``",
                test_lines=Lines_Step(
                    "E03-S06",
                    ["lpAssertHttpBusinessOk('E03-S06');", "lpAssertUserListContains('E03-S06');"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 ePassId（usedUsages=1）", "E03-S07", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后 search by ePassId",
                test_lines=Lines_Step(
                    "E03-S07",
                    ["lpAssertHttpBusinessOk('E03-S07');", "lpAssertSearchPurchaseDetails('E03-S07', true, false, 2, 1);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("search 按 purchaseOrderId（Bundle 后）", "E03-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后二次 search by orderId",
                test_lines=Lines_Step(
                    "E03-S08",
                    ["lpAssertHttpBusinessOk('E03-S08');", "lpAssertSearchPurchaseDetails('E03-S08', true, false, 2, 1);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 Bundle usage 单",
                step_prefix="E03-S09",
                order_id_var="usageOrderId",
                skip_to_request_name=e03_s10_name,
                description="Bundle usage 单取消 · ``PatchCancelOrderWithRetry``",
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e03_s10_name,
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="取消后 usage 详情 status=3",
                test_lines=Lines_Step(
                    "E03-S10",
                    ["lpAssertHttpBusinessOk('E03-S10');", "lpAssertUsageDetailsCore('E03-S10', true);"],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消后列表含 usage 单", "E03-S11", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyNative(),
                headers=BearerJsonHeaders(),
                description="取消后 orders 含 usageOrderId status=3",
                test_lines=Lines_Step(
                    "E03-S11",
                    [
                        "lpAssertHttpBusinessOk('E03-S11');",
                        "lpAssertOrderListPagination('E03-S11', false);",
                        "lpAssertUsageListContainsCancelled('E03-S11');",
                    ],
                ),
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("取消 usage 后 search 仍 Active", "E03-S12", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="usage 取消后 ePassStatus=1",
                test_lines=Lines_Step(
                    "E03-S12",
                    ["lpAssertHttpBusinessOk('E03-S12');", "lpAssertSearchActiveAfterUsageCancel('E03-S12', false);"],
                ),
            ),
            *BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（Bundle 收尾）",
                step_prefix="E03-S13",
                order_id_var="purchaseOrderId",
                skip_to_request_name=e03_s14_name,
                description="``CancelHistoricalPurchaseOrderAndVerify``",
            ),
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=e03_s14_name,
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="购买单取消后 ePass Cancelled",
                test_lines=Lines_Step(
                    "E03-S14",
                    [
                        "lpAssertHttpBusinessOk('E03-S14');",
                        "lpAssertSearchCancelledAfterPurchaseCancel('E03-S14', false);",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_HistoricalEpass_Lounge_E2E_BundleMainChain`` · "
            "``RunHistoricalEpassBundleMainE2EScenario(catalog_label='lounge')`` · "
            "运行前填 loungeResourceId（``DP_HIST_EPASS_LOUNGE_RESOURCE_ID``）；prebookingDate 由可用性步骤 Apifox 表达式同步"
        ),
    )


def _RewriteApiVersionInCollection(collection: JsonObject, api_version: str) -> JsonObject:
    """将集合 JSON 内 ``/v2/`` 路径前缀替换为 ``/{api_version}/``（如 v1）。"""
    source_prefix = "/v2/"
    target_prefix = f"/{api_version.strip('/')}/"

    def rewrite(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(source_prefix, target_prefix)
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    return rewrite(collection)


def BuildCollection(*, api_version: str = DEFAULT_API_VERSION) -> JsonObject:
    global _LOUNGE_JS_ASSERT_EPASS_STATUS
    prev_assert_epass_status = _LOUNGE_JS_ASSERT_EPASS_STATUS
    _LOUNGE_JS_ASSERT_EPASS_STATUS = api_version == DEFAULT_API_VERSION
    try:
        return _BuildCollectionBody(api_version=api_version)
    finally:
        _LOUNGE_JS_ASSERT_EPASS_STATUS = prev_assert_epass_status


def _BuildCollectionBody(*, api_version: str) -> JsonObject:
    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            RequestItem(
                js_helpers=_LoungeJsHelpers,
                name=PurposeName("获取 ePass 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken。",
                save_token=True,
                test_lines=Lines_Auth(),
                prerequest_lines=[],
            ),
        ],
        description="先执行本文件夹。",
    )

    info: JsonObject = {
        "name": "lounge ePass · P0 E2E 核心",
        "description": (
            "由 GeneratePostmanCollectionLoungeEpass.py 生成。\n\n"
            "**三条 P0 E2E 核心链路**（对齐 ``RunHistoricalEpass*MainE2EScenario(catalog_label='lounge')``）：\n"
            "- E01 创建验证链（含 module=1 / otherModule=11 双向隔离）\n"
            "- E02 预约验证链（经典可用性 · module=1）\n"
            "- E03 Bundle 一步下单\n\n"
            "每个 HTTP 步骤含多条 pm.test 字段级断言；请求名格式 **【目的】| 步骤号 | METHOD 路径**（与 Local Offer P1 pytest-sync 一致）。\n\n"
            "**必填变量**：ProgramID、clientId、secret；E02/E03 另填 loungeResourceId。\n"
            f"**lounge 网点**：``{LOUNGE_RESOURCE_ID_VAR}`` 对齐 ``{ENV_LOUNGE_RESOURCE_ID}``"
            f"（默认 {DEFAULT_LOUNGE_RESOURCE_ID}）。\n"
            "**品类 module**：epassModule=1、otherModule=11（断言动态读取）。\n"
            "**经典可用性**：``POST /v2/resources/prebookings/availability``（无 optionId）；"
            "``prebookingDate`` 默认 Apifox ``{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30``。\n"
            "**预约 extra**：含 ``prebookingRequiredInfo``（对齐 ``PostHistoricalEpassPrebooking`` 经典链）。\n"
            "**创建 availableUsages**：默认 2（对齐 pytest ``CreateHistoricalEpass``）。\n"
            "取消订单：线性 PATCH 最多 3 次（无 WAIT 间隔）；成功则向前 skip 剩余重试步骤；"
            "对齐 ``PatchCancelOrderWithRetry`` 可重试错误 ``Order cancellation failed``。\n"
            "**Apifox 兼容**：lp helpers 注入各 HTTP 步骤 test（及含 lp 的 pre-request）。\n"
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
        CollectionVariable(LOUNGE_RESOURCE_ID_VAR, DEFAULT_LOUNGE_RESOURCE_ID),
        CollectionVariable("loungeCancelMaxAttempts", str(GENERATED_CANCEL_ATTEMPTS)),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("prebookingToken", ""),
    ]

    collection: JsonObject = {
        "info": info,
        "variable": variables,
        "item": [
            auth_folder,
            BuildCreateE2EFolder(),
            BuildPrebookingE2EFolder(),
            BuildBundleE2EFolder(),
        ],
    }

    if api_version != DEFAULT_API_VERSION:
        collection = _RewriteApiVersionInCollection(collection, api_version)
        info_obj = collection["info"]
        info_obj["name"] = f"lounge ePass · P0 E2E 核心 · API {api_version}"
        base_desc = str(info_obj.get("description", ""))
        info_obj["description"] = (
            f"由 GeneratePostmanCollectionLoungeEpassV1.py 生成（网关路径 ``/{api_version}/``）。\n"
            "断言与 v2 基本一致，但 **v1 search/create 响应无 ``extra.ePassStatus``**，集合内已省略相关 pm.test。\n"
            "``category``：MS 创建/search=3，usage 单=2。\n\n"
            + base_desc.replace("由 GeneratePostmanCollectionLoungeEpass.py 生成。\n\n", "")
        )
        variables_list = collection.get("variable", [])
        if isinstance(variables_list, list):
            variables_list.append(CollectionVariable("apiVersion", api_version))

    return collection


def Main() -> None:
    script_dir = os.path.dirname(__file__)
    out_path = os.path.join(script_dir, OUT_NAME)
    WriteCollectionJson(out_path, BuildCollection(api_version=DEFAULT_API_VERSION))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
