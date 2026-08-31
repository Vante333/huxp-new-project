"""
Lounge E-pass 域公共构建能力。

P0 入口与 PAPI-2839 Lounge 回归依赖本模块；本模块不反向依赖任何
``GeneratePostmanCollection*.py``。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Final, List, Optional, Sequence

from collection_builder_common import (
    BearerJsonHeaders,
    Lines_Step,
    Lines_SyncPrebookingDate,
    PREBOOKING_ADD_DAYS_START,
    PrebookingDateApifoxExpr,
    PurposeName,
    RequestItem,
)
from epass_cli_common import (
    BuildEpassCreatePayload,
    BuildEpassExpectedModuleHelpersBlock,
    BuildEpassMainChainRequestSpecs,
    BuildEpassRuntimeHelpersBlock,
    CREATE_EXPIRATION_DATE,
    CREATE_FIRST_NAME,
    CREATE_LAST_NAME,
    GetEpassCategoryConfig,
    JsAssertRuntimeClientUserIdEquals,
    OTHER_MODULE_DEFAULT,
)

JsonObject = Dict[str, Any]
LOUNGE_CATEGORY = GetEpassCategoryConfig("lounge")
EPASS_MAIN_CHAIN_SPECS = BuildEpassMainChainRequestSpecs(LOUNGE_CATEGORY)

OUT_NAME: Final[str] = "Lounge-ePass-P0-e2e-core.postman_collection.json"
DEFAULT_API_VERSION: Final[str] = "v2"
PREBOOKING_DATE_APIFOX: Final[str] = PrebookingDateApifoxExpr(PREBOOKING_ADD_DAYS_START)
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CANCEL_RETRY_MSG_NEEDLE: Final[str] = "Order cancellation failed"
CREATE_AVAILABLE_USAGES: Final[int] = LOUNGE_CATEGORY.available_usages
DEFAULT_LOUNGE_RESOURCE_ID: Final[str] = LOUNGE_CATEGORY.default_resource_id
GENERATED_CANCEL_ATTEMPTS: Final[int] = 3
LOUNGE_RESOURCE_ID_VAR: Final[str] = LOUNGE_CATEGORY.resource_var
ENV_LOUNGE_RESOURCE_ID: Final[str] = "DP_HIST_EPASS_LOUNGE_RESOURCE_ID"
EPASS_MODULE_DEFAULT: Final[int] = LOUNGE_CATEGORY.module

_LOUNGE_JS_ASSERT_EPASS_STATUS: bool = True


def SetLoungeAssertEpassStatus(enabled: bool) -> bool:
    """设置 v1/v2 兼容断言开关并返回旧值，供入口在 ``finally`` 中恢复。"""
    global _LOUNGE_JS_ASSERT_EPASS_STATUS
    previous = _LOUNGE_JS_ASSERT_EPASS_STATUS
    _LOUNGE_JS_ASSERT_EPASS_STATUS = bool(enabled)
    return previous


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


CREATE_PAYLOAD_TEMPLATE: Final[str] = BuildEpassCreatePayload(LOUNGE_CATEGORY)


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
    lounge_resource_var = LOUNGE_RESOURCE_ID_VAR
    runtime_helpers = BuildEpassRuntimeHelpersBlock(
        LOUNGE_CATEGORY,
        extra_unset_env_keys=("loungeAvailabilityResourceId",),
    )
    module_helpers = BuildEpassExpectedModuleHelpersBlock(LOUNGE_CATEGORY)
    assert_data_fn_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="lp",
        actual_expression="dataFn().clientUserId",
    )
    assert_data_extra_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="lp",
        actual_expression="data().extra.clientUserId",
    )
    assert_list_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="lp",
        actual_expression="cid",
        indent="      ",
    )
    js = runtime_helpers + module_helpers + rf"""function lpIsBusinessSuccess(env) {{
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
  lpCaptureClientUserIdAfterSend(data);
  if (data.orderId && !lpIsUnresolvedPlaceholder(data.orderId)) {{
    lpSetVar('purchaseOrderId', String(data.orderId));
  }}
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = lpResolveEPassId(extra);
    if (ep && !lpIsUnresolvedPlaceholder(ep)) lpSetVar('ePassId', String(ep));
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
    var adultCount = parseInt(String(reqBody && reqBody.adultCount), 10);
    var childCount = parseInt(String(reqBody && reqBody.childCount), 10);
    if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
    if (isNaN(childCount) || childCount < 0) childCount = 0;
    pm.collectionVariables.set('loungeAdultCount', String(adultCount));
    pm.collectionVariables.set('loungeChildCount', String(childCount));
  }} catch (e) {{
    console.warn('lpSaveAvailabilityRequestFields:', e);
  }}
}}
function lpExpectedBookingCounts() {{
  var adultCount = parseInt(String(pm.collectionVariables.get('loungeAdultCount') || '1'), 10);
  var childCount = parseInt(String(pm.collectionVariables.get('loungeChildCount') || '0'), 10);
  if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
  if (isNaN(childCount) || childCount < 0) childCount = 0;
  if (adultCount + childCount <= 0) {{
    adultCount = 1;
    childCount = 0;
  }}
  return adultCount + childCount;
}}
function lpAssertBookingCounts(label) {{
  var env = pm.response.json();
  if (!env || env.code !== 0) {{
    return;
  }}
  var data = lpGetInnerData(env);
  var extra = (data && data.extra && typeof data.extra === 'object') ? data.extra : {{}};
  var expected = lpExpectedBookingCounts();
  var actual = extra.bookingCounts;
  pm.test(label + ': extra.bookingCounts | 期望=可用性 adultCount+childCount=' + expected + ' | 实际=' + String(actual), function () {{
    pm.expect(Object.prototype.hasOwnProperty.call(extra, 'bookingCounts'), 'extra.bookingCounts 字段存在').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.be.a('number');
    pm.expect(Number.isInteger(actual), 'extra.bookingCounts 为整数').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.eql(expected);
  }});
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
  lpSaveCreateIds(dataFn());
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
    var actual = dataFn().clientUserId;
    var saved = lpGetVar('clientUserId');
    pm.expect(actual, '响应 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(lpIsUnresolvedPlaceholder(actual), '响应不是未解析模板').to.be.false;
    pm.expect(lpIsUuid(actual), '响应 clientUserId 为 UUID').to.be.true;
    pm.expect(saved, '后置已提取 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(actual).to.eql(saved);
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
    pm.expect(lpGetVar('ePassId')).to.be.ok;
    pm.expect(lpGetVar('purchaseOrderId')).to.be.ok;
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
{assert_data_fn_client_user}
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
{assert_data_extra_client_user}
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
{assert_list_client_user}
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
{assert_data_extra_client_user}
  }});
  pm.test(label + ': extra.resourceId 一致', function () {{
    pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get('{lounge_resource_var}'));
  }});
  lpAssertBookingCounts(label);
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


def AvailabilityBody(*, with_epass: bool, add_days: int = PREBOOKING_ADD_DAYS_START) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{loungeResourceId}}",
        "prebookingDate": PrebookingDateApifoxExpr(add_days),
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


def Prerequest_SyncPrebookingDateFromApifox(
    add_days: int = PREBOOKING_ADD_DAYS_START,
) -> List[str]:
    return Lines_SyncPrebookingDate(add_days)


def LoungeRequestItem(**kwargs: Any) -> JsonObject:
    """每步前置把后置提取的 runtime id 写进 body（``{{clientUserId}}`` 等跨步常不展开）。"""
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["lpApplyRuntimeIdsToRequestBody();"]
    return RequestItem(**kwargs)


def Prerequest_ClearCancelDoneFlags() -> List[str]:
    return [
        "pm.collectionVariables.unset('lpCancelDone_usageOrderId');",
        "pm.collectionVariables.unset('lpCancelDone_purchaseOrderId');",
    ]


def Prerequest_NewClientUserId() -> List[str]:
    return [
        *Prerequest_ClearCancelDoneFlags(),
        "lpUnsetVar('clientUserId');",
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
            LoungeRequestItem(
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
        "lpUnsetVar('clientUserId');",
        "lpUnsetVar('ePassId');",
        "lpUnsetVar('purchaseOrderId');",
        "lpUnsetVar('usageOrderId');",
        "lpUnsetVar('prebookingToken');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        "lpUnsetVar('clientUserId');",
        "lpUnsetVar('ePassId');",
        "lpUnsetVar('purchaseOrderId');",
        "lpUnsetVar('usageOrderId');",
        "lpUnsetVar('prebookingToken');",
    ]


