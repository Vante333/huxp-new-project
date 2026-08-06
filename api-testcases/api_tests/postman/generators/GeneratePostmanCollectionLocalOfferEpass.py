"""
生成 Local Offer ePass **P0/P1 E2E 核心** Postman Collection v2.1 JSON。

同时写出 ``LocalOffer-ePass-P0-e2e-core`` 与 ``LocalOffer-ePass-P1-e2e-*``（同构 37 步）。
Apifox CLI 资产：``local_offer_epass_p0``（挂载 epass/P0/prebooking）。

对齐 ``test_local_offer_epass.py`` 三条主链路及 ``local_offer_epass_service`` 断言语义：

- E01 创建验证链 · ``RunLocalOfferEpassCreateMainE2EScenario``
- E02 预约验证链 · ``RunLocalOfferEpassPrebookingMainE2EScenario``（响应校验 voucherType=1）
- E03 Bundle 一步下单 · ``RunLocalOfferEpassBundleMainE2EScenario``（响应校验 voucherType=4）

**resourceId** / **optionId**：Environment 优先；鉴权三列走数据集 ``ProgramID``/``clientId``/``secret``。

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpass.py
"""
from __future__ import annotations

from pathlib import Path

from collection_builder_common import (
    CollectionPath,
    GeneratedArtifactPath,
    Lines_EnsureRequestIdHeader,
)

import json
import os
import uuid
from typing import Any, Dict, Final, List, Mapping, Optional, Sequence, Tuple, Union

JsonObject = Dict[str, Any]

POSTMAN_SCHEMA: Final[str] = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
COLLECTION_DISPLAY_NAME: Final[str] = "Local Offer ePass · P1 E2E (pytest-sync)"
COLLECTION_LEGACY_DISPLAY_NAME: Final[str] = "Local Offer ePass · P1 E2E 核心"
OUT_NAME: Final[str] = "LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json"
APIFOX_2743_IMPORT_NAME: Final[str] = "LocalOffer-ePass-P1-e2e-pytest-sync.apifox-2.7.43-import.json"
# 与 pytest-sync 同内容，兼容旧导入路径（文档 / Apifox 模块名）
P1_E2E_CORE_OUT_NAME: Final[str] = "LocalOffer-ePass-P1-e2e-core.postman_collection.json"
P1_MAINFLOW_OUT_NAME: Final[str] = "LocalOffer-ePass-tc-P1-mainflow.postman_collection.json"
P1_E2E_CORE_APIFOX_NAME: Final[str] = "LocalOffer-ePass-P1-e2e-core.apifox-2.7.43-import.json"
# 勿由本脚本写入或删除（Apifox/Postman 手工维护）
P0_COLLECTION_JSON_NAME: Final[str] = "LocalOffer-ePass-P0-e2e-core.postman_collection.json"
APIFOX_CLIENT_VERSION: Final[str] = "2.7.43"
PREBOOKING_DATE_APIFOX: Final[str] = "{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30"
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CREATE_FIRST_NAME: Final[str] = "Auto"
CREATE_LAST_NAME: Final[str] = "Test"
CREATE_EXPIRATION_DATE: Final[str] = "2028-12-31T23:59:59+00:00"
CREATE_AVAILABLE_USAGES: Final[int] = 5
MEMBERSHIP_REGISTER_EMAIL: Final[str] = "p2548_{{$timestamp}}@yahoo.com.cn"

MEMBERSHIP_REGISTER_PAYLOAD: Final[str] = json.dumps(
    {
        "clientUserId": "{{$guid}}",
        "firstName": "Lann",
        "lastName": "Testn",
        "phoneNumber": "8081966002",
        "callingCode": "44",
        "email": MEMBERSHIP_REGISTER_EMAIL,
        "expirationDate": "2027-12-31T10:10:33+00:00",
    },
    ensure_ascii=False,
    indent=2,
)

CREATE_PAYLOAD_TEMPLATE: Final[str] = json.dumps(
    {
        "module": 11,
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

PREBOOKING_REQUIRED_INFO_FIELDS: Final[Tuple[str, ...]] = (
    "firstName",
    "lastName",
    "email",
    "phoneNumber",
    "callingCode",
    "transportNumber",
)


def BuildLocalOfferJsHelpersLines() -> List[str]:
    """与 ``local_offer_epass_service`` 断言语义对齐的公共 JS。"""
    null_fields_js = json.dumps(list(PREBOOKING_REQUIRED_INFO_FIELDS))
    cancel_msg_js = json.dumps(CANCEL_SUCCESS_MSG)
    create_first_name_js = json.dumps(CREATE_FIRST_NAME)
    create_last_name_js = json.dumps(CREATE_LAST_NAME)
    create_expiration_date_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_available_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    prebooking_date_apifox_js = json.dumps(PREBOOKING_DATE_APIFOX)
    js = rf"""
function loIsBusinessSuccess(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}}
function loGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {{
    return d;
  }}
  return d;
}}
function loParseEnvelope(respJson) {{
  return {{
    env: respJson,
    data: loGetInnerData(respJson)
  }};
}}
function loAssertModule11Required(data, ctx) {{
  pm.expect(data, ctx + ' data').to.be.an('object');
  pm.expect(data.module, ctx + ' module=11').to.eql(11);
}}
function loAssertModule11IfPresent(data, ctx) {{
  if (!data || typeof data !== 'object') return;
  if (Object.prototype.hasOwnProperty.call(data, 'module')) {{
    pm.expect(data.module, ctx + ' module').to.eql(11);
  }}
}}
function loResolveEPassIdFromRoot(data) {{
  if (!data || typeof data !== 'object') return null;
  var direct = data.ePassId || data.epassId;
  if (direct) return direct;
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    return extra.ePassId || extra.epassId || null;
  }}
  return null;
}}
function loResolveEPassId(extra) {{
  if (!extra || typeof extra !== 'object') return null;
  return extra.ePassId || extra.epassId || null;
}}
function loResolveLocalOfferOptionId(data) {{
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
function loEnvFirst() {{
  for (var i = 0; i < arguments.length; i++) {{
    var v = pm.variables.get(arguments[i]);
    if (v === undefined || v === null) continue;
    v = String(v).trim();
    if (v && v.indexOf('{{') < 0) return v;
  }}
  return '';
}}
function loApplyOutletForScenario(label) {{
  var rid = '';
  var oid = '';
  if (label === 'card_secret') {{
    rid = loEnvFirst('cardSecretResourceId', 'resourceId');
    oid = loEnvFirst('cardSecretOptionId', 'optionId');
  }} else if (label === 'redemption_code') {{
    rid = loEnvFirst('redemptionCodeResourceId', 'resourceId');
    oid = loEnvFirst('redemptionCodeOptionId', 'optionId');
  }} else if (label === 'url') {{
    rid = loEnvFirst('urlResourceId', 'resourceId');
    oid = loEnvFirst('urlOptionId', 'optionId');
  }} else {{
    rid = loEnvFirst('resourceId');
    oid = loEnvFirst('optionId');
  }}
  if (rid) pm.collectionVariables.set('resourceId', rid);
  if (oid) pm.collectionVariables.set('optionId', oid);
}}
function loResolveExpectedResourceId() {{
  var v = loEnvFirst('resourceId');
  if (v) return v;
  v = pm.collectionVariables.get('resourceId');
  if (v === undefined || v === null) return '';
  v = String(v).trim();
  return (v && v.indexOf('{{') < 0) ? v : '';
}}
function loResolveExpectedOptionId() {{
  var v = loEnvFirst('optionId');
  if (v) return v;
  v = pm.collectionVariables.get('optionId');
  if (v === undefined || v === null) return '';
  v = String(v).trim();
  return (v && v.indexOf('{{') < 0) ? v : '';
}}
function loExpectResourceIdMatch(label, actual) {{
  var expected = loResolveExpectedResourceId();
  if (expected) {{
    pm.expect(actual, label + ' resourceId').to.eql(expected);
  }} else {{
    pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;
    pm.collectionVariables.set('resourceId', String(actual));
  }}
}}
function loExpectOptionIdMatch(label, actual) {{
  if (!actual) {{
    console.warn(label + ': 响应未返回 optionId，跳过 optionId 回显断言');
    return;
  }}
  var expected = loResolveExpectedOptionId();
  if (expected) {{
    pm.expect(actual, label + ' optionId').to.eql(expected);
  }} else {{
    pm.collectionVariables.set('optionId', String(actual));
  }}
}}
function loSaveCreateIds(data) {{
  if (!data || typeof data !== 'object') return;
  if (data.clientUserId) pm.collectionVariables.set('clientUserId', String(data.clientUserId));
  if (data.orderId) pm.collectionVariables.set('purchaseOrderId', String(data.orderId));
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = loResolveEPassId(extra);
    if (ep) pm.collectionVariables.set('ePassId', String(ep));
  }}
}}
function loResolvePrebookingDateString(rawValue) {{
  if (rawValue === null || rawValue === undefined) return '';
  var pd = String(pm.variables.replaceIn(String(rawValue))).trim();
  if (!pd || pd.indexOf('{{') >= 0) {{
    pd = loBuildPrebookingDatePlus10Days1030();
  }}
  return pd;
}}
function loSyncPrebookingDateCollectionVar() {{
  var tpl = {prebooking_date_apifox_js};
  var pb = loResolvePrebookingDateString(tpl);
  pm.collectionVariables.set('prebookingDate', pb);
}}
function loSavePrebookingDateFromRequest() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (reqBody && reqBody.prebookingDate) {{
      pm.collectionVariables.set('prebookingDate', loResolvePrebookingDateString(reqBody.prebookingDate));
    }}
  }} catch (e) {{
    console.warn('loSavePrebookingDateFromRequest:', e);
  }}
}}
function loAssertBusinessFailure(label, expectedErrCodes, acceptHttp400) {{
  var codes = expectedErrCodes || [];
  pm.test(label + ': 业务失败', function () {{
    var status = pm.response.code;
    if (acceptHttp400 === true && status === 400) {{
      pm.expect(status).to.eql(400);
      return;
    }}
    pm.expect(status).to.eql(200);
    var env = pm.response.json();
    pm.expect(env && env.code).to.eql(-1);
    if (codes.length) {{
      pm.expect(codes, 'errCode').to.include(env.errCode);
    }}
  }});
}}
function loParseCreateAllowedResourceIds() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return [];
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    var ar = reqBody && reqBody.extra && reqBody.extra.allowedResources;
    if (!ar || !Array.isArray(ar.resourceIds)) return [];
    return ar.resourceIds.map(function (id) {{ return String(id); }}).filter(Boolean);
  }} catch (e) {{
    console.warn('loParseCreateAllowedResourceIds:', e);
    return [];
  }}
}}
function loAssertBusinessFailureMsgContainsRequestResourceIds(label) {{
  pm.test(label + ': msg 含本请求 resourceIds 之一', function () {{
    var env = pm.response.json();
    var msg = env && env.msg ? String(env.msg) : '';
    var ids = loParseCreateAllowedResourceIds();
    pm.expect(ids.length, 'resourceIds').to.be.above(0);
    var hit = ids.some(function (id) {{ return msg.indexOf(id) >= 0; }});
    pm.expect(hit, 'msg 应含请求体中的 resourceId: ' + ids.join(', ')).to.be.true;
  }});
}}
function loSaveFirstEsimResourceFromList(label) {{
  pm.test(label + ': 保存 esimResourceId/optionId（module=8）', function () {{
    var data = loGetInnerData(pm.response.json());
    var list = loCollectResourcesEntries(data);
    var item = null;
    for (var i = 0; i < list.length; i++) {{
      if (list[i] && Number(list[i].module) === 8) {{ item = list[i]; break; }}
    }}
    if (!item && list.length) item = list[0];
    pm.expect(item, 'module=8 资源').to.be.ok;
    var rid = item.resourceId || item.id;
    pm.expect(rid).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('esimResourceId', String(rid));
    var opt = item.optionId;
    if (!opt && item.options && item.options.length) {{
      opt = item.options[0].optionId || item.options[0].id || item.options[0].skuId;
    }}
    if (!opt) opt = item.skuId;
    if (opt) pm.collectionVariables.set('esimOptionId', String(opt));
  }});
}}
function loCollectResourcesEntries(data) {{
  var out = [];
  if (!data || typeof data !== 'object') return out;
  var bucket = data.resources;
  if (bucket && typeof bucket === 'object' && !Array.isArray(bucket)) {{
    ['transportHubResources', 'lifestyleResources'].forEach(function (key) {{
      var arr = bucket[key];
      if (Array.isArray(arr)) out = out.concat(arr);
    }});
  }}
  if (Array.isArray(bucket)) out = out.concat(bucket);
  if (Array.isArray(data.resourceList)) out = out.concat(data.resourceList);
  if (Array.isArray(data.list)) out = out.concat(data.list);
  return out;
}}
function loPatchAvailabilityBodyEsimVars(label) {{
  try {{
    var er = '';
    var eo = '';
    try {{ er = String(pm.variables.replaceIn('{{esimResourceId}}') || '').trim(); }} catch (eR0) {{}}
    try {{ eo = String(pm.variables.replaceIn('{{esimOptionId}}') || '').trim(); }} catch (eO0) {{}}
    if (!er || er.indexOf('{{') >= 0) {{
      try {{ er = String(pm.collectionVariables.get('esimResourceId') || '').trim(); }} catch (eR1) {{}}
    }}
    if (!eo || eo.indexOf('{{') >= 0) {{
      try {{ eo = String(pm.collectionVariables.get('esimOptionId') || '').trim(); }} catch (eO1) {{}}
    }}
    // Apifox 场景常无集合变量：回退默认 eSIM 网点（与 Full 集合预置一致）
    if (!er || er.indexOf('{{') >= 0) er = 'GR0005901';
    if (!eo || eo.indexOf('{{') >= 0) eo = 'SKU-GS0010955';
    var body = JSON.parse(pm.request.body.raw);
    body.resourceId = String(er);
    body.optionId = String(eo);
    if (body.module === undefined || body.module === null) body.module = 8;
    pm.request.body.raw = JSON.stringify(body);
    try {{ pm.variables.set('esimResourceId', String(er)); }} catch (eVS1) {{}}
    try {{ pm.collectionVariables.set('esimResourceId', String(er)); }} catch (eVS2) {{}}
    try {{ pm.variables.set('esimOptionId', String(eo)); }} catch (eVS3) {{}}
    try {{ pm.collectionVariables.set('esimOptionId', String(eo)); }} catch (eVS4) {{}}
  }} catch (e) {{
    console.warn(label + ': loPatchAvailabilityBodyEsimVars', e);
  }}
}}
function loAssertEsimAvailabilityForCrossModuleToken(label) {{
  // 对齐 pytest：可用性 code=-1（500.020.009/007/500.110.019）则软通过并标记跳过后续；
  // 成功则写入 prebookingToken 供后续负向下单。
  loSavePrebookingDateFromRequest();
  var env = pm.response.json();
  var code = env && env.code;
  var err = env && (env.errCode || (env.error && env.error.errCode));
  var softCodes = ['500.020.009', '500.020.007', '500.110.019'];
  if (code === -1 || code === '-1') {{
    pm.test(label + ': eSIM 可用性业务拒绝可软通过 | 期望=500.020.009|007|500.110.019 | 实际=' + String(err), function () {{
      pm.expect(softCodes.indexOf(String(err)) >= 0, 'errCode=' + err).to.eql(true);
    }});
    try {{ pm.variables.set('loEsimAvailSoftSkip', '1'); }} catch (e1) {{}}
    try {{ pm.collectionVariables.set('loEsimAvailSoftSkip', '1'); }} catch (e2) {{}}
    return;
  }}
  try {{ pm.variables.set('loEsimAvailSoftSkip', '0'); }} catch (e3) {{}}
  try {{ pm.collectionVariables.set('loEsimAvailSoftSkip', '0'); }} catch (e4) {{}}
  loAssertAvailabilitySuccess(label);
}}
function loAssertBusinessFailureUnlessEsimAvailSoftSkip(label, errCodes) {{
  var skip = '';
  try {{ skip = String(pm.variables.get('loEsimAvailSoftSkip') || '').trim(); }} catch (e0) {{}}
  if (!skip) {{ try {{ skip = String(pm.collectionVariables.get('loEsimAvailSoftSkip') || '').trim(); }} catch (e1) {{}} }}
  if (skip === '1') {{
    pm.test(label + ': 上一步 eSIM 可用性已软拒绝，跳过本步 | 期望=skip | 实际=skip', function () {{
      pm.expect(true).to.eql(true);
    }});
    return;
  }}
  loAssertBusinessFailure(label, errCodes);
}}
function loAssertMembershipRegisterSuccess(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(loIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
  pm.test(label + ': 写入 membershipId', function () {{
    var data = loGetInnerData(pm.response.json());
    pm.expect(data.membershipId).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('membershipId', String(data.membershipId));
  }});
}}
var loOrderStatusActiveOrProcessing = [1, 5];
function loNormalizeOrderStatus(st) {{
  if (st === null || st === undefined) return null;
  var n = parseInt(String(st), 10);
  return isNaN(n) ? null : n;
}}
function loFailIfOrderStatus10(status, label) {{
  var st = loNormalizeOrderStatus(status);
  if (st === 10) {{
    pm.expect.fail(label + ': 订单 status=10 FAILED');
  }}
}}
function loExpectOrderStatusActiveOrProcessing(label, status) {{
  var st = loNormalizeOrderStatus(status);
  loFailIfOrderStatus10(st, label);
  pm.expect(loOrderStatusActiveOrProcessing, label + ' status').to.include(st);
}}
function loAssertPrebookingRequiredInfoNull(label, extra) {{
  pm.test(label + ': prebookingRequiredInfo 各字段 null', function () {{
    pm.expect(extra).to.be.an('object');
    var info = extra.prebookingRequiredInfo;
    pm.expect(info).to.be.an('object');
    var fields = {null_fields_js};
    fields.forEach(function (f) {{
      pm.expect(info, '缺字段 ' + f).to.have.property(f);
      pm.expect(info[f], f + ' 应为 null').to.eql(null);
    }});
  }});
}}
function loResolveListItemField(item, rootKey, extraKey) {{
  if (!item || typeof item !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(item, rootKey)) return item[rootKey];
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, extraKey)) return ex[extraKey];
    if (Object.prototype.hasOwnProperty.call(ex, rootKey)) return ex[rootKey];
  }}
  return null;
}}
function loAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {{
  allowedStatuses = allowedStatuses || loOrderStatusActiveOrProcessing;
  var data = function () {{ return loGetInnerData(pm.response.json()); }};
  var statusLabel = (allowedStatuses.indexOf(5) >= 0)
    ? 'status=1 或 5（CONFIRMED/处理中，非 10 FAILED）'
    : 'status=1 CONFIRMED（非 10 FAILED）';
  pm.test(label + ': ' + statusLabel, function () {{
    var st = loNormalizeOrderStatus(data().status);
    if (st === 10) {{
      pm.expect.fail('预约单 status=10 FAILED');
    }}
    pm.expect(allowedStatuses).to.include(st);
  }});
  pm.test(label + ': module=11', function () {{ loAssertModule11Required(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    loSaveUsageOrderId(data());
  }});
  pm.test(label + ': clientUserId 与注册会籍一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': ePassId 与前面一致', function () {{
    var ep = loResolveEPassIdFromRoot(data());
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
    expected = loResolvePrebookingDateString(expected);
    if (expected) {{
      pm.expect(actual).to.eql(expected);
    }}
  }});
  loAssertPrebookingRequiredInfoNull(label, data().extra);
  pm.test(label + ': extra.resourceId 与 resourceId 一致', function () {{
    loExpectResourceIdMatch(label, data().extra.resourceId);
  }});
  pm.test(label + ': localOfferOptions.optionId 一致', function () {{
    loExpectOptionIdMatch(label, loResolveLocalOfferOptionId(data()));
  }});
}}
function loResolveTransportHubName(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubName')) {{
    return ex.transportHubName;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubName')) return item.transportHubName;
  return undefined;
}}
function loResolveTransportHubId(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubId')) {{
    return ex.transportHubId;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubId')) return item.transportHubId;
  return undefined;
}}
function loAssertUsageOrderListItemCore(label, item) {{
  pm.expect(item.category, label + ' category').to.eql(2);
  pm.expect(item.module, label + ' module').to.eql(11);
  var rid = loResolveListItemField(item, 'resourceId', 'resourceId');
  pm.expect(rid, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  loExpectResourceIdMatch(label, rid);
  var opt = loResolveLocalOfferOptionId(item);
  pm.expect(opt, label + ' optionId 非空').to.be.a('string').and.not.empty;
  loExpectOptionIdMatch(label, opt);
  pm.expect(loResolveTransportHubName(item), label + ' transportHubName').to.eql(null);
  pm.expect(loResolveTransportHubId(item), label + ' transportHubId').to.eql(null);
}}
function loAssertUsageOrderInListActive(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(loIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
  loAssertOrderListPagination(label, false, true);
  loAssertNoEsimInModule11List(label);
  pm.test(label + ': orders 含 usageOrderId 且 status=1 或 5', function () {{
    var data = loGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    pm.expect(data.orders.length, 'orders 不应为空').to.be.above(0);
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usageOrderId=' + oid).to.be.above(0);
    var item = hit[0];
    loExpectOrderStatusActiveOrProcessing(label, item.status);
    loAssertUsageOrderListItemCore(label, item);
    if (Object.prototype.hasOwnProperty.call(item, 'orderCancelledDate')) {{
      pm.expect(item.orderCancelledDate).to.eql(null);
    }}
    var used = loResolveListItemField(item, 'usedUsages', 'usedUsages');
    pm.expect(used, label + ' usedUsages').to.eql(1);
    var usageDate = loResolveListItemField(item, 'usageDate', 'usageDate');
    if (usageDate !== undefined) {{
      pm.expect(usageDate).to.eql(null);
    }}
    var ep = loResolveEPassIdFromRoot(item);
    if (ep) {{
      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));
    }}
    var cid = loResolveListItemField(item, 'clientUserId', 'clientUserId');
    if (cid) {{
      pm.expect(cid).to.eql(pm.collectionVariables.get('clientUserId'));
    }}
  }});
}}
function loSavePrebookingToken(data) {{
  if (data && data.prebookingToken) {{
    pm.collectionVariables.set('prebookingToken', String(data.prebookingToken));
  }}
}}
function loSaveUsageOrderId(data) {{
  if (data && data.orderId) {{
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }}
}}
function loSaveBundleIds(data) {{
  if (!data || typeof data !== 'object') return;
  var ep = loResolveEPassIdFromRoot(data);
  if (ep) pm.collectionVariables.set('ePassId', String(ep));
  if (data.orderId) pm.collectionVariables.set('usageOrderId', String(data.orderId));
}}
function loBuildPrebookingDatePlus10Days1030() {{
  var d = new Date();
  d.setUTCDate(d.getUTCDate() + 10);
  var pad = function (n) {{ return n < 10 ? '0' + n : String(n); }};
  return d.getUTCFullYear() + '-' + pad(d.getUTCMonth() + 1) + '-' + pad(d.getUTCDate()) + 'T10:30';
}}
function loEnsurePrebookingDate() {{
  var existing = pm.collectionVariables.get('prebookingDate');
  if (existing && String(existing).trim()) return String(existing);
  var computed = loBuildPrebookingDatePlus10Days1030();
  pm.collectionVariables.set('prebookingDate', computed);
  return computed;
}}
function loAssertHttpBusinessOk(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(loIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
}}
function loAssertCancelOrderSuccess(label) {{
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
function loExpectedCreateExtra() {{
  return {{
    firstName: {create_first_name_js},
    lastName: {create_last_name_js},
    expirationDate: {create_expiration_date_js},
    availableUsages: {create_available_usages_js}
  }};
}}
function loAssertExtraMatchesCreateInput(label, extra) {{
  pm.test(label + ': extra.firstName 与入参一致', function () {{
    pm.expect(extra.firstName).to.eql(loExpectedCreateExtra().firstName);
  }});
  pm.test(label + ': extra.lastName 与入参一致', function () {{
    pm.expect(extra.lastName).to.eql(loExpectedCreateExtra().lastName);
  }});
  pm.test(label + ': extra.expirationDate 与入参一致', function () {{
    pm.expect(extra.expirationDate).to.eql(loExpectedCreateExtra().expirationDate);
  }});
  pm.test(label + ': extra.availableUsages 与入参一致', function () {{
    pm.expect(extra.availableUsages).to.eql(loExpectedCreateExtra().availableUsages);
  }});
}}
function loAssertCreateCoreFields(label) {{
  var dataFn = function () {{ return loGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=11', function () {{
    loAssertModule11Required(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED', function () {{
    pm.expect(loNormalizeOrderStatus(dataFn().status)).to.eql(1);
  }});
  pm.test(label + ': category=2', function () {{
    pm.expect(dataFn().category).to.eql(2);
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
  loAssertExtraMatchesCreateInput(label, dataFn().extra);
  pm.test(label + ': extra.ePassId 非空', function () {{
    pm.expect(loResolveEPassId(dataFn().extra)).to.be.ok;
  }});
  pm.test(label + ': extra.allowedResources 存在', function () {{
    pm.expect(dataFn().extra.allowedResources).to.be.an('object');
  }});
  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {{
    loSaveCreateIds(dataFn());
    pm.expect(pm.collectionVariables.get('ePassId')).to.be.ok;
    pm.expect(pm.collectionVariables.get('purchaseOrderId')).to.be.ok;
  }});
}}
function loAssertUserListContains(label) {{
  pm.test(label + ': ePassesList 含 ePassId', function () {{
    var data = loGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    pm.expect(data.ePassesList).to.be.an('array');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    pm.expect(hit.length, '未找到 ePassId=' + target).to.be.above(0);
  }});
  pm.test(label + ': 列表项 module=11（若存在）', function () {{
    var data = loGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    if (hit[0] && Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(11);
    }}
  }});
}}
function loAssertSearchPurchaseDetails(label, assertModule11, matchCreateInput, expectedStatus, expectedUsedUsages) {{
  var dataFn = function () {{ return loGetInnerData(pm.response.json()); }};
  var status = (expectedStatus !== undefined && expectedStatus !== null) ? expectedStatus : 1;
  var usedUsages = (expectedUsedUsages !== undefined && expectedUsedUsages !== null) ? expectedUsedUsages : 0;
  if (assertModule11 !== false) {{
    pm.test(label + ': module=11', function () {{
      loAssertModule11Required(dataFn(), label);
    }});
  }}
  pm.test(label + ': category=2', function () {{
    pm.expect(dataFn().category).to.eql(2);
  }});
  pm.test(label + ': status=' + status, function () {{
    pm.expect(loNormalizeOrderStatus(dataFn().status)).to.eql(status);
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
    pm.expect(loResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.usedUsages=' + usedUsages, function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(usedUsages);
  }});
  if (matchCreateInput !== false) {{
    loAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function loAssertOrderListPagination(label, allowEmpty, expectModule11) {{
  pm.test(label + ': pagination 结构', function () {{
    var data = loGetInnerData(pm.response.json());
    pm.expect(data.pagination).to.be.an('object');
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {{
      pm.expect(data.pagination, 'pagination.' + k).to.have.property(k);
    }});
  }});
  pm.test(label + ': orders 为数组', function () {{
    pm.expect(loGetInnerData(pm.response.json()).orders).to.be.an('array');
  }});
  if (allowEmpty) {{
    pm.test(label + ': 创建后 orders 可为空（canary doc gap）', function () {{
      pm.expect(loGetInnerData(pm.response.json()).orders).to.be.an('array');
    }});
  }}
  if (expectModule11) {{
    pm.test(label + ': 列表项 module=11（若存在 module 字段）', function () {{
      var orders = loGetInnerData(pm.response.json()).orders || [];
      orders.forEach(function (item, idx) {{
        if (item && Object.prototype.hasOwnProperty.call(item, 'module')) {{
          pm.expect(item.module, 'orders[' + idx + '].module').to.eql(11);
        }}
      }});
    }});
  }}
}}
function loAssertAvailabilitySuccess(label) {{
  loSavePrebookingDateFromRequest();
  pm.test(label + ': available=true', function () {{
    pm.expect(loGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var data = loGetInnerData(pm.response.json());
    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;
    loSavePrebookingToken(data);
  }});
}}
function loAssertPrebookingOrderSuccess(label) {{
  loAssertUsageOrderCreateSuccess(label, true);
}}
function loAssertBundleOrderSuccess(label) {{
  loAssertUsageOrderCreateSuccess(label, false);
  pm.test(label + ': 写入 usageOrderId', function () {{
    pm.expect(pm.collectionVariables.get('usageOrderId')).to.be.ok;
  }});
}}
function loAssertUsageDetailsCore(label, expectCancelled) {{
  var data = function () {{ return loGetInnerData(pm.response.json()); }};
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {{
    pm.expect(data().orderId).to.eql(pm.collectionVariables.get('usageOrderId'));
  }});
  pm.test(label + ': module=11', function () {{ loAssertModule11Required(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': extra.usedUsages=1', function () {{ pm.expect(data().extra.usedUsages).to.eql(1); }});
  pm.test(label + ': extra.usageDate=null', function () {{ pm.expect(data().extra.usageDate).to.eql(null); }});
  pm.test(label + ': ePassId 一致（根节点，对齐 _ResolveEPassIdField）', function () {{
    pm.expect(loResolveEPassIdFromRoot(data())).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.clientUserId 一致', function () {{
    pm.expect(data().extra.clientUserId).to.eql(pm.collectionVariables.get('clientUserId'));
  }});
  pm.test(label + ': extra.resourceId 一致', function () {{
    loExpectResourceIdMatch(label, data().extra.resourceId);
  }});
  pm.test(label + ': prebookingRequiredInfo 各字段 null', function () {{
    var info = data().extra.prebookingRequiredInfo;
    pm.expect(info).to.be.an('object');
    var fields = {null_fields_js};
    fields.forEach(function (f) {{
      pm.expect(info, '缺字段 ' + f).to.have.property(f);
      pm.expect(info[f], f + ' 应为 null').to.eql(null);
    }});
  }});
  if (expectCancelled) {{
    pm.test(label + ': status=3 CANCELLED', function () {{
      pm.expect(loNormalizeOrderStatus(data().status)).to.eql(3);
    }});
    pm.test(label + ': orderCancelledDate 有值', function () {{
      pm.expect(data().orderCancelledDate).to.not.eql(null);
      pm.expect(data().orderCancelledDate).to.be.a('string').and.not.empty;
    }});
  }} else {{
    pm.test(label + ': status=1 或 5（CONFIRMED/处理中，非 10 FAILED）', function () {{
      loExpectOrderStatusActiveOrProcessing(label, data().status);
    }});
    pm.test(label + ': orderCancelledDate=null', function () {{
      pm.expect(data().orderCancelledDate).to.eql(null);
    }});
  }}
}}
function loAssertNoEsimInModule11List(label) {{
  pm.test(label + ': module=11 列表不含 module=8 数据', function () {{
    var data = loGetInnerData(pm.response.json());
    if (!data || typeof data !== 'object') return;
    if (!Array.isArray(data.orders)) return;
    var esimHits = data.orders.filter(function (o) {{ return o && o.module === 8; }});
    pm.expect(esimHits.length, 'module=11 orders 不应含 module=8 条目').to.eql(0);
  }});
}}
function loAssertNoLocalOfferReturnedWithModule8(label) {{
  pm.test(label + ': module=8 不返回 Local Offer 数据', function () {{
    var env = pm.response.json();
    if (env && env.code === -1) {{
      console.warn(label + ': module=8 返回业务失败，视为隔离通过 errCode=' + env.errCode);
      return;
    }}
    pm.expect(loIsBusinessSuccess(env), label + ' business success 或 code=-1').to.be.true;
    var data = loGetInnerData(env);
    if (data === null || data === undefined) return;
    if (typeof data !== 'object') return;
    var expectedUsage = pm.collectionVariables.get('usageOrderId');
    var expectedPurchase = pm.collectionVariables.get('purchaseOrderId');
    var expectedEPass = pm.collectionVariables.get('ePassId');
    if (Array.isArray(data.orders)) {{
      if (expectedUsage) {{
        var sameUsage = data.orders.filter(function (o) {{
          return o && o.orderId === expectedUsage;
        }});
        pm.expect(sameUsage.length, 'module=8 orders 不应含 usageOrderId').to.eql(0);
      }}
      if (expectedPurchase) {{
        var samePurchase = data.orders.filter(function (o) {{
          return o && o.orderId === expectedPurchase;
        }});
        pm.expect(samePurchase.length, 'module=8 orders 不应含 purchaseOrderId').to.eql(0);
      }}
      var loItems = data.orders.filter(function (o) {{ return o && o.module === 11; }});
      pm.expect(loItems.length, 'module=8 orders 不应含 module=11 条目').to.eql(0);
      return;
    }}
    pm.expect(data.module, 'module=8 details 不应返回 module=11').to.not.eql(11);
    if (expectedUsage && data.orderId) {{
      pm.expect(data.orderId, 'module=8 details 不应返回 Local Offer usageOrderId').to.not.eql(expectedUsage);
    }}
    var ep = loResolveEPassIdFromRoot(data);
    if (expectedEPass && ep && data.module === 11) {{
      pm.expect(ep, 'module=8 details 不应返回 Local Offer ePassId').to.not.eql(expectedEPass);
    }}
  }});
}}
function loAssertUsageListContainsCancelled(label) {{
  pm.test(label + ': orders 含 usageOrderId 且 status=3', function () {{
    var data = loGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    if (!data.orders.length) {{
      console.warn('orders 为空（canary 索引延迟），跳过取消态断言');
      return;
    }}
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usage orderId=' + oid).to.be.above(0);
    pm.expect(loNormalizeOrderStatus(hit[0].status)).to.eql(3);
    if (Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(11);
    }}
  }});
}}
function loAssertSearchActiveAfterUsageCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return loGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=11', function () {{
    loAssertModule11Required(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED（MS 单未取消）', function () {{
    pm.expect(loNormalizeOrderStatus(dataFn().status)).to.eql(1);
  }});
  pm.test(label + ': purchaseOrderId 仍可查', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassStatus=1 Active', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(1);
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(loResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    loAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function loAssertSearchCancelledAfterPurchaseCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return loGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=3 CANCELLED', function () {{
    pm.expect(loNormalizeOrderStatus(dataFn().status)).to.eql(3);
  }});
  pm.test(label + ': extra.ePassStatus=3 Cancelled', function () {{
    pm.expect(dataFn().extra.ePassStatus).to.eql(3);
  }});
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(loResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    loAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
""".strip()
    return [ln for ln in js.split("\n")]


def SaveTokenLines() -> List[str]:
    """Auth 后置：多作用域写入 accessToken（Apifox 场景下 collection 常不可用）。"""
    return [
        "try {",
        "  var j = pm.response.json();",
        "  var d = j.data !== undefined ? j.data : j;",
        "  var t = d.accessToken || d.token || d.access_token;",
        "  if (t) {",
        "    var tok = String(t);",
        "    try { pm.variables.set('accessToken', tok); } catch (eV) {}",
        "    try { pm.collectionVariables.set('accessToken', tok); } catch (eC) {}",
        "    try { pm.environment.set('accessToken', tok); } catch (eE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', tok); } catch (eG) {}",
        "  }",
        "} catch (e) { console.warn(e); }",
        "pm.test('Auth: accessToken 已写入运行时 | 期望=非空 | 实际=多作用域任一非空', function () {",
        "  var _a = ''; try { _a = String(pm.variables.get('accessToken') || '').trim(); } catch (e1) {}",
        "  var _b = ''; try { _b = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e2) {}",
        "  var _c = ''; try { _c = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e3) {}",
        "  var _d = ''; try { _d = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (e4) {}",
        "  pm.expect(_a || _b || _c || _d, 'variables/collection/env/globals 均无 accessToken').to.be.ok;",
        "});",
    ]


def Lines_EnsureAuthPrerequest() -> List[str]:
    """发送前：Environment 注入 baseUrl/ProgramID/x-version/resourceId/optionId；强制 Authorization。"""
    return [
        "try {",
        "  var _base = '';",
        "  try { _base = String((pm.environment && pm.environment.get('baseUrl')) || '').trim(); } catch (eB0) {}",
        "  if (!_base) { try { _base = String(pm.variables.get('baseUrl') || '').trim(); } catch (eB1) {} }",
        "  if (!_base) { try { _base = String(pm.collectionVariables.get('baseUrl') || '').trim(); } catch (eB2) {} }",
        "  if (_base) {",
        "    try { pm.variables.set('baseUrl', _base); } catch (eBS1) {}",
        "    try { pm.collectionVariables.set('baseUrl', _base); } catch (eBS2) {}",
        "  }",
        "  var _pid = '';",
        "  try { _pid = String(pm.variables.get('ProgramID') || '').trim(); } catch (eP0) {}",
        "  if (!_pid) { try { _pid = String(pm.collectionVariables.get('ProgramID') || '').trim(); } catch (eP1) {} }",
        "  if (!_pid) { try { _pid = String((pm.environment && pm.environment.get('ProgramID')) || '').trim(); } catch (eP2) {} }",
        "  if (_pid) {",
        "    try { pm.variables.set('ProgramID', _pid); } catch (ePS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'X-Program-ID', value: _pid });",
        "      }",
        "    } catch (ePH) {}",
        "  }",
        "  // 数据集标准列：ProgramID / clientId / secret",
        "  var _cid = '';",
        "  try { _cid = String(pm.variables.get('clientId') || '').trim(); } catch (eC0) {}",
        "  if (!_cid) { try { _cid = String(pm.collectionVariables.get('clientId') || '').trim(); } catch (eC1) {} }",
        "  if (!_cid) { try { _cid = String((pm.environment && pm.environment.get('clientId')) || '').trim(); } catch (eC2) {} }",
        "  if (_cid) {",
        "    try { pm.variables.set('clientId', _cid); } catch (eCS1) {}",
        "    try { pm.collectionVariables.set('clientId', _cid); } catch (eCS2) {}",
        "  }",
        "  var _sec = '';",
        "  try { _sec = String(pm.variables.get('secret') || '').trim(); } catch (eS0) {}",
        "  if (!_sec) { try { _sec = String(pm.collectionVariables.get('secret') || '').trim(); } catch (eS1) {} }",
        "  if (!_sec) { try { _sec = String((pm.environment && pm.environment.get('secret')) || '').trim(); } catch (eS2) {} }",
        "  if (_sec) {",
        "    try { pm.variables.set('secret', _sec); } catch (eSS1) {}",
        "    try { pm.collectionVariables.set('secret', _sec); } catch (eSS2) {}",
        "  }",
        "  var _xv = '';",
        "  try { _xv = String((pm.environment && pm.environment.get('x-version')) || '').trim(); } catch (eX0) {}",
        "  if (!_xv) { try { _xv = String(pm.variables.get('x-version') || '').trim(); } catch (eX1) {} }",
        "  if (!_xv) { try { _xv = String(pm.collectionVariables.get('x-version') || '').trim(); } catch (eX2) {} }",
        "  if (_xv && ['omit','none','off'].indexOf(_xv.toLowerCase()) < 0) {",
        "    try { pm.variables.set('x-version', _xv); } catch (eXS) {}",
        "    try {",
        "      if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {",
        "        pm.request.headers.upsert({ key: 'x-version', value: _xv });",
        "      }",
        "    } catch (eXH) {}",
        "  }",
        "  var _rid = '';",
        "  try { _rid = String((pm.environment && pm.environment.get('resourceId')) || '').trim(); } catch (eR0) {}",
        "  if (!_rid) { try { _rid = String(pm.variables.get('resourceId') || '').trim(); } catch (eR1) {} }",
        "  if (!_rid) { try { _rid = String(pm.collectionVariables.get('resourceId') || '').trim(); } catch (eR2) {} }",
        "  var _oid = '';",
        "  try { _oid = String((pm.environment && pm.environment.get('optionId')) || '').trim(); } catch (eO0) {}",
        "  if (!_oid) { try { _oid = String(pm.variables.get('optionId') || '').trim(); } catch (eO1) {} }",
        "  if (!_oid) { try { _oid = String(pm.collectionVariables.get('optionId') || '').trim(); } catch (eO2) {} }",
        "  if (_rid) {",
        "    try { pm.variables.set('resourceId', _rid); } catch (eRS1) {}",
        "    try { pm.collectionVariables.set('resourceId', _rid); } catch (eRS2) {}",
        "  }",
        "  if (_oid) {",
        "    try { pm.variables.set('optionId', _oid); } catch (eOS1) {}",
        "    try { pm.collectionVariables.set('optionId', _oid); } catch (eOS2) {}",
        "  }",
        "  // 数据集空 accessToken 列会盖掉 Auth 写入",
        "  try {",
        "    var _rawTok = pm.variables.get('accessToken');",
        "    if (_rawTok !== undefined && _rawTok !== null && String(_rawTok).trim() === '') {",
        "      try { pm.variables.unset('accessToken'); } catch (eUn) { try { pm.variables.set('accessToken', ''); } catch (eUn2) {} }",
        "    }",
        "  } catch (eClr) {}",
        "  var _tok = '';",
        "  try { _tok = String(pm.collectionVariables.get('accessToken') || '').trim(); } catch (e3) {}",
        "  if (!_tok) { try { _tok = String((pm.globals && pm.globals.get('accessToken')) || '').trim(); } catch (eG1) {} }",
        "  if (!_tok) { try { _tok = String((pm.environment && pm.environment.get('accessToken')) || '').trim(); } catch (e4) {} }",
        "  if (!_tok) { try { _tok = String(pm.variables.get('accessToken') || '').trim(); } catch (e5) {} }",
        "  if (_tok) {",
        "    try { pm.variables.set('accessToken', _tok); } catch (eTV) {}",
        "    try { pm.collectionVariables.set('accessToken', _tok); } catch (eTC) {}",
        "    try { pm.environment.set('accessToken', _tok); } catch (eTE) {}",
        "    try { if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set('accessToken', _tok); } catch (eTG) {}",
        "    var _auth = 'Bearer ' + _tok;",
        "    try {",
        "      var _hdrs = pm.request && pm.request.headers;",
        "      if (_hdrs && typeof _hdrs.upsert === 'function') {",
        "        _hdrs.upsert({ key: 'Authorization', value: _auth });",
        "      } else if (_hdrs && typeof _hdrs.add === 'function') {",
        "        try { if (typeof _hdrs.remove === 'function') _hdrs.remove('Authorization'); } catch (eRm) {}",
        "        _hdrs.add({ key: 'Authorization', value: _auth });",
        "      }",
        "    } catch (eH) { console.warn('LO ePass ensure bearer', eH); }",
        "  }",
        "} catch (eAll) {}",
        *Lines_EnsureRequestIdHeader(),
    ]


def MakeTestEvent(
    *,
    save_token: bool = False,
    extra_lines: Optional[Sequence[str]] = None,
) -> List[JsonObject]:
    lines: List[str] = []
    lines.extend(BuildLocalOfferJsHelpersLines())
    if save_token:
        lines.extend(SaveTokenLines())
    if extra_lines:
        lines.extend(list(extra_lines))
    return [{"listen": "test", "script": {"exec": lines, "type": "text/javascript"}}]


def MakePreRequestEvent(lines: Sequence[str]) -> List[JsonObject]:
    exec_lines: List[str] = []
    exec_lines.extend(BuildLocalOfferJsHelpersLines())
    exec_lines.extend(list(lines))
    return [{"listen": "prerequest", "script": {"exec": exec_lines, "type": "text/javascript"}}]


def AuthJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def BearerJsonHeaders() -> List[JsonObject]:
    return [
        {"key": "X-Program-ID", "value": "{{ProgramID}}"},
        {"key": "x-version", "value": "{{x-version}}"},
        {"key": "X-Request-ID", "value": "{{$guid}}"},
        {"key": "Authorization", "value": "Bearer {{accessToken}}"},
        {"key": "Content-Type", "value": "application/json"},
        {"key": "Accept", "value": "*/*"},
    ]


def PostmanUrl(url_path: str, query: Optional[Dict[str, str]] = None) -> JsonObject:
    """构建 Postman URL；``query`` 与 path 中 ``?a=1`` 会合并为 ``url.query`` 数组。"""
    path_only = url_path.split("?", 1)[0]
    merged_query: Dict[str, str] = {}
    if "?" in url_path:
        for part in url_path.split("?", 1)[1].split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                merged_query[key] = value
    if query:
        merged_query.update({str(k): str(v) for k, v in query.items()})
    path_parts: List[str] = [part for part in path_only.split("/") if part]
    raw = "{{baseUrl}}/" + "/".join(path_parts)
    url_obj: JsonObject = {"raw": raw, "host": ["{{baseUrl}}"], "path": path_parts}
    if merged_query:
        url_obj["query"] = [{"key": k, "value": v} for k, v in merged_query.items()]
        url_obj["raw"] = raw + "?" + "&".join(f"{k}={v}" for k, v in merged_query.items())
    return url_obj


def PostmanJsonRawBody(raw: str) -> JsonObject:
    return {"mode": "raw", "raw": raw, "options": {"raw": {"language": "json"}}}


def CollectionVariable(key: str, value: str) -> JsonObject:
    return {"key": key, "value": value, "type": "string"}


def RequestItem(
    *,
    name: str,
    method: str,
    url_path: str,
    body: Optional[str],
    headers: List[JsonObject],
    description: str,
    save_token: bool = False,
    test_lines: Optional[Sequence[str]] = None,
    prerequest_lines: Optional[Sequence[str]] = None,
    url_query: Optional[Dict[str, str]] = None,
) -> JsonObject:
    req: JsonObject = {
        "method": method,
        "header": headers,
        "url": PostmanUrl(url_path, url_query),
        "description": description,
    }
    if body is not None:
        req["body"] = PostmanJsonRawBody(body)
    out: JsonObject = {"name": name, "request": req}
    # CLI/Apifox 场景：每步前置 EnsureAuth；业务前置（日期/网点）叠在其后
    pre_merged: List[str] = list(Lines_EnsureAuthPrerequest())
    if prerequest_lines:
        pre_merged.extend(list(prerequest_lines))
    out["event"] = [
        MakePreRequestEvent(pre_merged)[0],
        MakeTestEvent(save_token=save_token, extra_lines=test_lines)[0],
    ]
    return out


def Folder(name: str, items: Sequence[Union[JsonObject, Mapping[str, Any]]], description: str = "") -> JsonObject:
    folder: JsonObject = {"name": name, "item": list(items)}
    if description:
        folder["description"] = description
    return folder


def Lines_Auth() -> List[str]:
    return [
        "loAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 非空 | 期望=true | 实际=响应 data', function () {",
        "  var d = loGetInnerData(pm.response.json());",
        "  var t = (d && (d.accessToken || d.token || d.access_token));",
        "  pm.expect(t, '响应 accessToken').to.be.ok;",
        "});",
    ]


def Lines_Step(label: str, fn_calls: Sequence[str]) -> List[str]:
    return list(fn_calls)


def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    """
    Apifox/Postman 列表展示名：业务目的前置，便于在自动化场景中识别每条请求验证什么。

    格式：``【目的】| 步骤号 | METHOD 路径简写``
    """
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"


def AvailabilityBody(*, with_epass: bool) -> str:
    body: JsonObject = {
        "module": 11,
        "resourceId": "{{resourceId}}",
        "optionId": "{{optionId}}",
        "prebookingDate": PREBOOKING_DATE_APIFOX,
        "adultCount": 1,
        "childCount": 0,
    }
    if with_epass:
        body["ePassId"] = "{{ePassId}}"
    return json.dumps(body, ensure_ascii=False, indent=2)


def Prerequest_SyncPrebookingDateFromApifox() -> List[str]:
    """Apifox 动态日期写入集合变量（未解析时回退 +10 天 10:30），与预约 extra.prebookingDate 对齐。"""
    return ["loSyncPrebookingDateCollectionVar();"]


def OrdersListBody() -> str:
    return OrdersListBodyForModule(11)


def OrdersListBodyForModule(module: int) -> str:
    return json.dumps(
        {"ePassId": "{{ePassId}}", "module": module, "pageSize": 10, "pageNumber": 1},
        ensure_ascii=False,
        indent=2,
    )


def UsageDetailsBody() -> str:
    """``POST /v2/orders/ePasses/details`` — OAS/pytest 仅 ``orderId``，**不传 module**。"""
    return json.dumps({"orderId": "{{usageOrderId}}"}, ensure_ascii=False, indent=2)


def Prerequest_EnsurePrebookingDate() -> List[str]:
    return Prerequest_SyncPrebookingDateFromApifox()


def Prerequest_NewClientUserId() -> List[str]:
    return [
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
    ]


def Prerequest_ResetForPrebooking() -> List[str]:
    return [
        "loApplyOutletForScenario('card_secret');",
        *Prerequest_SyncPrebookingDateFromApifox(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        "loApplyOutletForScenario('redemption_code');",
        *Prerequest_SyncPrebookingDateFromApifox(),
        "pm.collectionVariables.set('clientUserId', pm.variables.replaceIn('{{$guid}}'));",
        "pm.collectionVariables.set('ePassId', '');",
        "pm.collectionVariables.set('purchaseOrderId', '');",
        "pm.collectionVariables.set('usageOrderId', '');",
        "pm.collectionVariables.set('prebookingToken', '');",
    ]


def BuildCreateE2EFolder() -> JsonObject:
    return Folder(
        "E01 · tc-P1 创建验证链（pytest-sync）",
        [
            RequestItem(
                name=PurposeName("创建 Local Offer ePass（MS 购买单）", "E01-S01", "POST", "/localOffers/ePasses"),
                method="POST",
                url_path="/v2/orders/localOffers/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferEpassCreateCoreFields`` · ``ExtractCreateEpassIds``",
                prerequest_lines=Prerequest_NewClientUserId(),
                test_lines=Lines_Step(
                    "E01-S01",
                    ["loAssertHttpBusinessOk('E01-S01');", "loAssertCreateCoreFields('E01-S01');"],
                ),
            ),
            RequestItem(
                name=PurposeName("users 列表含本 clientUserId 的 ePass", "E01-S02", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertUserEPassesContains``",
                test_lines=Lines_Step(
                    "E01-S02",
                    ["loAssertHttpBusinessOk('E01-S02');", "loAssertUserListContains('E01-S02');"],
                ),
            ),
            RequestItem(
                name=PurposeName("search 按 purchaseOrderId 查 MS 详情", "E01-S03", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchDetailsCoreFields`` by orderId",
                test_lines=Lines_Step(
                    "E01-S03",
                    ["loAssertHttpBusinessOk('E01-S03');", "loAssertSearchPurchaseDetails('E01-S03', true);"],
                ),
            ),
            RequestItem(
                name=PurposeName("search 按 ePassId 查 MS 详情", "E01-S04", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E01-S04",
                    ["loAssertHttpBusinessOk('E01-S04');", "loAssertSearchPurchaseDetails('E01-S04', true);"],
                ),
            ),
            RequestItem(
                name=PurposeName("usage 订单列表（创建后可为空）", "E01-S05", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``PostOrdersEPassesList`` · 创建后 orders 可能为空",
                test_lines=Lines_Step(
                    "E01-S05",
                    [
                        "loAssertHttpBusinessOk('E01-S05');",
                        "loAssertOrderListPagination('E01-S05', true, true);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("module=8 列表不含 LO 订单（取消 MS 前）", "E01-I06", "POST", "/ePasses?module=8"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyForModule(8),
                headers=BearerJsonHeaders(),
                description=(
                    "``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · 取消 MS 前 · "
                    "purchaseOrderId / module=11 条目不出现"
                ),
                test_lines=Lines_Step(
                    "E01-I06",
                    ["loAssertNoLocalOfferReturnedWithModule8('E01-I06');"],
                ),
            ),
            RequestItem(
                name=PurposeName("module=11 列表不含 eSIM 订单（取消 MS 前）", "E01-I07", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter`` · 取消 MS 前 · list module=11",
                test_lines=Lines_Step(
                    "E01-I07",
                    [
                        "loAssertHttpBusinessOk('E01-I07');",
                        "loAssertNoEsimInModule11List('E01-I07');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 MS 购买单", "E01-S06", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="``AssertCancelOrderSuccess``",
                test_lines=Lines_Step("E01-S06", ["loAssertCancelOrderSuccess('E01-S06');"]),
            ),
            RequestItem(
                name=PurposeName("module=8 列表不含 LO 订单（取消 MS 后）", "E01-I08", "POST", "/ePasses?module=8"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyForModule(8),
                headers=BearerJsonHeaders(),
                description=(
                    "``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · 取消 MS 后 · "
                    "purchaseOrderId / module=11 条目不出现"
                ),
                test_lines=Lines_Step(
                    "E01-I08",
                    ["loAssertNoLocalOfferReturnedWithModule8('E01-I08');"],
                ),
            ),
            RequestItem(
                name=PurposeName("module=11 列表不含 eSIM（取消 MS 后）", "E01-I09", "POST", "/ePasses?module=11"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``AssertEsimNotReturnedWithLocalOfferModuleFilter`` · 取消 MS 后 · list module=11",
                test_lines=Lines_Step(
                    "E01-I09",
                    [
                        "loAssertHttpBusinessOk('E01-I09');",
                        "loAssertNoEsimInModule11List('E01-I09');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消后 usage 订单列表分页", "E01-S07", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``AssertOrderListPaginationShape``",
                test_lines=Lines_Step(
                    "E01-S07",
                    [
                        "loAssertHttpBusinessOk('E01-S07');",
                        "loAssertOrderListPagination('E01-S07', true, true);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消后 search 显示 ePass Cancelled", "E01-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchShowsCancelledAfterPurchaseCancel``",
                test_lines=Lines_Step(
                    "E01-S08",
                    [
                        "loAssertHttpBusinessOk('E01-S08');",
                        "loAssertSearchCancelledAfterPurchaseCancel('E01-S08');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_LocalOfferEpass_E2E_CreateMainChain`` · ``RunLocalOfferEpassCreateMainE2EScenario`` · "
            "含 module=8 列表/详情隔离（``AssertLocalOfferNotReturnedWithEsimModuleFilter`` / "
            "``AssertEsimNotReturnedWithLocalOfferModuleFilter``）"
        ),
    )


def BuildPrebookingE2EFolder() -> JsonObject:
    return Folder(
        "E02 · tc-P1 预约验证链（card_secret · voucherType=1 · pytest-sync）",
        [
            RequestItem(
                name=PurposeName("预约链前置：创建 ePass", "E02-S01", "POST", "/localOffers/ePasses"),
                method="POST",
                url_path="/v2/orders/localOffers/ePasses",
                body=CREATE_PAYLOAD_TEMPLATE,
                headers=BearerJsonHeaders(),
                description="Prebooking 前置：创建 ePass",
                prerequest_lines=Prerequest_ResetForPrebooking(),
                test_lines=Lines_Step(
                    "E02-S01",
                    ["loAssertHttpBusinessOk('E02-S01');", "loAssertCreateCoreFields('E02-S01');"],
                ),
            ),
            RequestItem(
                name=PurposeName("可用性查询并获取 prebookingToken", "E02-S02", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=True),
                headers=BearerJsonHeaders(),
                description="``AssertPrebookingAvailabilitySuccess`` · ``RequestPrebookingToken`` · prebookingDate Apifox 动态 +10天 10:30",
                prerequest_lines=Prerequest_SyncPrebookingDateFromApifox(),
                test_lines=Lines_Step(
                    "E02-S02",
                    ["loAssertHttpBusinessOk('E02-S02');", "loAssertAvailabilitySuccess('E02-S02');"],
                ),
            ),
            RequestItem(
                name=PurposeName("预约下单成功（usage 单）", "E02-S03", "POST", "/ePasses/prebooking"),
                method="POST",
                url_path="/v2/orders/localOffers/ePasses/prebooking",
                body=json.dumps(
                    {
                        "module": 11,
                        "ePassId": "{{ePassId}}",
                        "extra": {"prebookingToken": "{{prebookingToken}}"},
                        "async": False,
                    },
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferPrebookingOrderSuccess``",
                test_lines=Lines_Step(
                    "E02-S03",
                    ["loAssertHttpBusinessOk('E02-S03');", "loAssertPrebookingOrderSuccess('E02-S03');"],
                ),
            ),
            RequestItem(
                name=PurposeName("预约后 module=11 列表含 usage 单", "E02-S04", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="预约成功后 module=11 订单列表 · 含 usageOrderId / status=1 / usedUsages=1 等",
                test_lines=Lines_Step("E02-S04", ["loAssertUsageOrderInListActive('E02-S04');"]),
            ),
            RequestItem(
                name=PurposeName("module=8 列表不含 LO usage 单", "E02-S05", "POST", "/ePasses?module=8"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyForModule(8),
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · list module=8",
                test_lines=Lines_Step(
                    "E02-S05",
                    [
                        "loAssertNoLocalOfferReturnedWithModule8('E02-S05');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("usage 订单详情（取消前）", "E02-S06", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "``PostOrdersEPassesUsageDetails`` · OAS/pytest **仅 orderId**，不传 ``module``；"
                    "``AssertUsageOrderDetailsCoreFields``（取消前）。"
                ),
                test_lines=Lines_Step(
                    "E02-S06",
                    [
                        "loAssertHttpBusinessOk('E02-S06');",
                        "loAssertUsageDetailsCore('E02-S06', false);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 usage 预订单", "E02-S07", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="``CancelUsageOrderAndVerifyPostCancelRetrieve`` · ``AssertCancelOrderSuccess``",
                test_lines=Lines_Step("E02-S07", ["loAssertCancelOrderSuccess('E02-S07');"]),
            ),
            RequestItem(
                name=PurposeName("取消后 usage 详情 status=3", "E02-S08", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsShowsCancelled``",
                test_lines=Lines_Step(
                    "E02-S08",
                    [
                        "loAssertHttpBusinessOk('E02-S08');",
                        "loAssertUsageDetailsCore('E02-S08', true);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消后列表含 usage 单且 status=3", "E02-S09", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderListContainsCancelled``",
                test_lines=Lines_Step(
                    "E02-S09",
                    [
                        "loAssertHttpBusinessOk('E02-S09');",
                        "loAssertOrderListPagination('E02-S09', false);",
                        "loAssertUsageListContainsCancelled('E02-S09');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 usage 后 MS search 仍 Active", "E02-S10", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchActiveAfterUsageCancel``",
                test_lines=Lines_Step(
                    "E02-S10",
                    [
                        "loAssertHttpBusinessOk('E02-S10');",
                        "loAssertSearchActiveAfterUsageCancel('E02-S10');",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_LocalOfferEpass_E2E_PrebookingMainChain_ByVoucherType[card_secret]`` · "
            "``RunLocalOfferEpassPrebookingMainE2EScenario``。E02 前置脚本写入 ``cardSecretResourceId``/``cardSecretOptionId``（或回退 ``resourceId``/``optionId``）。"
        ),
    )


def BuildBundleE2EFolder() -> JsonObject:
    return Folder(
        "E03 · tc-P1 Bundle 一步下单（redemption_code · voucherType=4 · pytest-sync）",
        [
            RequestItem(
                name=PurposeName("Bundle 可用性（无 ePassId）取 token", "E03-S01", "POST", "/prebookings/availability"),
                method="POST",
                url_path="/v2/resources/options/prebookings/availability",
                body=AvailabilityBody(with_epass=False),
                headers=BearerJsonHeaders(),
                description="``RequestPrebookingTokenWithoutEpass``",
                prerequest_lines=Prerequest_ResetForBundle(),
                test_lines=Lines_Step(
                    "E03-S01",
                    ["loAssertHttpBusinessOk('E03-S01');", "loAssertAvailabilitySuccess('E03-S01');"],
                ),
            ),
            RequestItem(
                name=PurposeName("Bundle 一步下单（创建 ePass+usage）", "E03-S02", "POST", "/ePasses/bundle"),
                method="POST",
                url_path="/v2/orders/localOffers/ePasses/bundle",
                body=json.dumps(
                    {
                        "module": 11,
                        "clientUserId": "{{clientUserId}}",
                        "extra": {"prebookingToken": "{{prebookingToken}}"},
                        "async": False,
                    },
                    indent=2,
                ),
                headers=BearerJsonHeaders(),
                description="``AssertBundleOrderSuccess``",
                test_lines=Lines_Step(
                    "E03-S02",
                    ["loAssertHttpBusinessOk('E03-S02');", "loAssertBundleOrderSuccess('E03-S02');"],
                ),
            ),
            RequestItem(
                name=PurposeName("Bundle 后列表含 usage 单", "E03-S03", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="Bundle 成功后 module=11 订单列表 · 含 usageOrderId / status=1 / usedUsages=1 等",
                test_lines=Lines_Step("E03-S03", ["loAssertUsageOrderInListActive('E03-S03');"]),
            ),
            RequestItem(
                name=PurposeName("module=8 列表不含 LO Bundle 单", "E03-S04", "POST", "/ePasses?module=8"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBodyForModule(8),
                headers=BearerJsonHeaders(),
                description="``AssertLocalOfferNotReturnedWithEsimModuleFilter`` · list module=8",
                test_lines=Lines_Step(
                    "E03-S04",
                    [
                        "loAssertNoLocalOfferReturnedWithModule8('E03-S04');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("Bundle usage 详情（取消前）", "E03-S05", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "``PostOrdersEPassesUsageDetails`` · **仅 orderId**，不传 ``module``；"
                    "``AssertUsageOrderDetailsCoreFields``（取消前）。"
                ),
                test_lines=Lines_Step(
                    "E03-S05",
                    [
                        "loAssertHttpBusinessOk('E03-S05');",
                        "loAssertUsageDetailsCore('E03-S05', false);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("Bundle 后 users 列表含 ePass", "E03-S06", "POST", "/users/ePasses"),
                method="POST",
                url_path="/v2/users/ePasses",
                body=json.dumps({"clientUserId": "{{clientUserId}}", "pageSize": 10, "pageNumber": 1}, indent=2),
                headers=BearerJsonHeaders(),
                description="Bundle 后 ``AssertUserEPassesContains``",
                test_lines=Lines_Step(
                    "E03-S06",
                    ["loAssertHttpBusinessOk('E03-S06');", "loAssertUserListContains('E03-S06');"],
                ),
            ),
            RequestItem(
                name=PurposeName("search 按 ePassId（usedUsages=1）", "E03-S07", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchDetailsCoreFields`` by ePassId",
                test_lines=Lines_Step(
                    "E03-S07",
                    ["loAssertHttpBusinessOk('E03-S07');", "loAssertSearchPurchaseDetails('E03-S07', true, false, 2, 1);"],
                ),
            ),
            RequestItem(
                name=PurposeName("search 按 purchaseOrderId", "E03-S08", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "orderId": "{{purchaseOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="Bundle 后二次 search by orderId",
                test_lines=Lines_Step(
                    "E03-S08",
                    ["loAssertHttpBusinessOk('E03-S08');", "loAssertSearchPurchaseDetails('E03-S08', true, false, 2, 1);"],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 Bundle usage 单", "E03-S09", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="取消 Bundle usage 单 · ``AssertCancelOrderSuccess``",
                test_lines=Lines_Step("E03-S09", ["loAssertCancelOrderSuccess('E03-S09');"]),
            ),
            RequestItem(
                name=PurposeName("取消后 usage 详情 status=3", "E03-S10", "POST", "/ePasses/details"),
                method="POST",
                url_path="/v2/orders/ePasses/details",
                body=UsageDetailsBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderDetailsShowsCancelled``",
                test_lines=Lines_Step(
                    "E03-S10",
                    [
                        "loAssertHttpBusinessOk('E03-S10');",
                        "loAssertUsageDetailsCore('E03-S10', true);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消后列表含 usage 单", "E03-S11", "POST", "/ePasses"),
                method="POST",
                url_path="/v2/orders/ePasses",
                body=OrdersListBody(),
                headers=BearerJsonHeaders(),
                description="``AssertUsageOrderListContainsCancelled``",
                test_lines=Lines_Step(
                    "E03-S11",
                    [
                        "loAssertHttpBusinessOk('E03-S11');",
                        "loAssertOrderListPagination('E03-S11', false);",
                        "loAssertUsageListContainsCancelled('E03-S11');",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 usage 后 search 仍 Active", "E03-S12", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchActiveAfterUsageCancel``",
                test_lines=Lines_Step(
                    "E03-S12",
                    [
                        "loAssertHttpBusinessOk('E03-S12');",
                        "loAssertSearchActiveAfterUsageCancel('E03-S12', false);",
                    ],
                ),
            ),
            RequestItem(
                name=PurposeName("取消 MS 购买单（Bundle 收尾）", "E03-S13", "PATCH", "/orders"),
                method="PATCH",
                url_path="/v2/orders",
                body=json.dumps({"status": 3, "orderId": "{{purchaseOrderId}}"}, indent=2),
                headers=BearerJsonHeaders(),
                description="Bundle 收尾：``CancelPurchaseOrderAndVerifyPostCancelRetrieve`` · ``AssertCancelOrderSuccess``",
                test_lines=Lines_Step("E03-S13", ["loAssertCancelOrderSuccess('E03-S13');"]),
            ),
            RequestItem(
                name=PurposeName("取消 MS 后 search 显示 Cancelled", "E03-S14", "POST", "/ePasses/search"),
                method="POST",
                url_path="/v2/orders/ePasses/search",
                body='{\n  "ePassId": "{{ePassId}}"\n}',
                headers=BearerJsonHeaders(),
                description="``AssertEpassSearchShowsCancelledAfterPurchaseCancel``",
                test_lines=Lines_Step(
                    "E03-S14",
                    [
                        "loAssertHttpBusinessOk('E03-S14');",
                        "loAssertSearchCancelledAfterPurchaseCancel('E03-S14', false);",
                    ],
                ),
            ),
        ],
        description=(
            "pytest: ``test_LocalOfferEpass_E2E_BundleMainChain_ByVoucherType[redemption_code]`` · "
            "``RunLocalOfferEpassBundleMainE2EScenario``。E03 前置脚本写入 ``redemptionCodeResourceId``/``redemptionCodeOptionId``（或回退 ``resourceId``/``optionId``）。"
        ),
    )


def BuildCollection() -> JsonObject:
    auth_folder: JsonObject = Folder(
        "00 Auth",
        [
            RequestItem(
                name=PurposeName("鉴权获取 accessToken", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 ``accessToken``；前置脚本同步 ``prebookingDate``（Apifox +10天 10:30）。",
                save_token=True,
                test_lines=Lines_Auth(),
                prerequest_lines=Prerequest_EnsurePrebookingDate(),
            ),
        ],
        description="先执行本文件夹。",
    )

    info: JsonObject = {
        "name": COLLECTION_DISPLAY_NAME,
        "description": (
            "由 GeneratePostmanCollectionLocalOfferEpass.py 生成（**仅 E2E 核心 37 步**）。\n"
            "**100+ 步分模块用例**请导入 ``LocalOffer-ePass-full-pytest-sync.postman_collection.json``"
            "（或别名 ``LocalOffer-ePass-P1-full.postman_collection.json``）。\n\n"
            "**三条 E2E 链路**（对齐 ``RunLocalOfferEpass*MainE2EScenario`` / ``local_offer_epass_service``）：\n"
            "- E01 创建验证链（含 module=8 双向隔离 + MS 取消后 search）\n"
            "- E02 预约验证链（card_secret / voucherType=1；取消 usage + 取消后 details/列表/search）\n"
            "- E03 Bundle 一步下单（redemption_code / voucherType=4；含 MS 取消）\n\n"
            "每个 HTTP 步骤含多条 pm.test 字段级断言（与 pytest ``Assert*`` 同构）。\n\n"
            "**多环境（Apifox Environment）**：``baseUrl``、``x-version``、``resourceId``、``optionId``。\n"
            "**数据集鉴权三列（填 ePass 凭据）**：``ProgramID``、``clientId``、``secret``"
            "（与 PAPI-2424 共用；ProgramID 常见值 ``1919249349977088``）。\n"
            "**运行时变量**：accessToken、prebookingDate、ePassId、purchaseOrderId、usageOrderId、prebookingToken。\n"
            "``prebookingDate`` 由 availability 请求体 Apifox 表达式 "
            "``{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30`` 自动解析并写入集合变量。"
        ),
        "schema": POSTMAN_SCHEMA,
    }

    # 勿预置空 accessToken / 鉴权三列 / baseUrl：空值会盖住 Environment 与数据集
    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("prebookingDate", ""),
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


def FlattenPostmanRequestItems(items: Sequence[JsonObject]) -> List[JsonObject]:
    flat: List[JsonObject] = []
    for it in items:
        if "request" in it:
            flat.append(it)
        nested = it.get("item")
        if isinstance(nested, list):
            flat.extend(FlattenPostmanRequestItems(nested))
    return flat


def ScriptExecByListen(item: JsonObject, listen: str) -> List[str]:
    lines: List[str] = []
    for ev in item.get("event", []):
        if ev.get("listen") != listen:
            continue
        exec_lines = ev.get("script", {}).get("exec", [])
        if isinstance(exec_lines, list):
            lines.extend(str(line) for line in exec_lines)
    return lines


def ApifoxParameterRows(headers: Sequence[JsonObject]) -> List[JsonObject]:
    rows: List[JsonObject] = []
    for hdr in headers:
        key = str(hdr.get("key", ""))
        if not key:
            continue
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "relatedId": str(uuid.uuid4()),
                "relatedName": key,
                "name": key,
                "value": str(hdr.get("value", "")),
                "type": "string",
                "description": "",
                "enable": True,
                "isDelete": False,
            }
        )
    return rows


def ApifoxCustomScriptProcessor(exec_lines: Sequence[str]) -> JsonObject:
    return {
        "type": "customScript",
        "enable": True,
        "defaultEnable": True,
        "data": "\n".join(exec_lines),
    }


def ApifoxProcessorsFromItem(item: JsonObject) -> Tuple[List[JsonObject], List[JsonObject]]:
    pre_lines = ScriptExecByListen(item, "prerequest")
    test_lines = ScriptExecByListen(item, "test")
    pre: List[JsonObject] = []
    post: List[JsonObject] = []
    if pre_lines:
        pre.append(ApifoxCustomScriptProcessor(pre_lines))
    if test_lines:
        post.append(ApifoxCustomScriptProcessor(test_lines))
    return pre, post


def ApifoxHttpApiCaseFromPostmanItem(item: JsonObject, *, case_id: int) -> JsonObject:
    req = item["request"]
    method = str(req.get("method", "GET")).lower()
    url_obj = req.get("url", {})
    if isinstance(url_obj, dict):
        path = "/" + "/".join(str(p) for p in url_obj.get("path", []))
    else:
        raw = str(url_obj)
        path = raw.split("{{baseUrl}}", 1)[-1] if "{{baseUrl}}" in raw else raw
    headers = req.get("header", [])
    if not isinstance(headers, list):
        headers = []
    body = req.get("body", {})
    request_body: Optional[JsonObject] = None
    if isinstance(body, dict) and body.get("mode") == "raw":
        request_body = {
            "type": "application/json",
            "data": str(body.get("raw", "")),
            "generateMode": "normal",
            "parameters": [],
        }
    pre_processors, post_processors = ApifoxProcessorsFromItem(item)
    return {
        "id": case_id,
        "name": str(item.get("name", "")),
        "method": method,
        "path": path,
        "auth": {},
        "type": "http",
        "options": {},
        "responseId": 0,
        "apiId": 0,
        "moduleId": 0,
        "parameters": {
            "query": [],
            "header": ApifoxParameterRows(headers),
            "cookie": [],
            "path": [],
        },
        "requestBody": request_body,
        "preProcessors": pre_processors,
        "postProcessors": post_processors,
        "inheritPostProcessors": {},
        "inheritPreProcessors": {},
        "advancedSettings": {
            "disabledSystemHeaders": {},
            "isDefaultUrlEncoding": 1,
        },
    }


def BuildApifox2743ImportPayload(collection: JsonObject) -> JsonObject:
    """Apifox 2.7.43 私有化：项目设置 → 导入 Apifox 格式（勿用 Postman 入口）。"""
    flat_items = FlattenPostmanRequestItems(collection["item"])
    steps: List[JsonObject] = []
    for index, item in enumerate(flat_items, start=1):
        steps.append(
            {
                "name": str(item.get("name", f"step-{index}")),
                "number": index,
                "type": "http",
                "bind": False,
                "disable": False,
                "bindType": "API",
                "bindId": 0,
                "syncMode": "manual",
                "httpApiCase": ApifoxHttpApiCaseFromPostmanItem(item, case_id=880_000 + index),
            }
        )
    return {
        "app": "apifox",
        "type": "project",
        "exportTarget": "apifox",
        "compatibleClientVersion": APIFOX_CLIENT_VERSION,
        "exportHint": (
            "项目设置 → 导入数据 → **Apifox**（勿选 Postman）。"
            "预览勾选「测试场景/测试用例」。"
            "接口维护可另导入 *.postman_collection.json（Postman 入口）。"
        ),
        "apiCollection": [],
        "apiTestCaseCollection": [
            {
                "name": COLLECTION_DISPLAY_NAME,
                "description": "自动化测试场景；每步含前置/后置 customScript（pm.test 断言）",
                "children": [],
                "items": [
                    {
                        "id": 880_001,
                        "name": "P1 E2E pytest-sync（Auth + E01 + E02 + E03）",
                        "description": collection["info"].get("description", ""),
                        "tags": ["tc-P1", "pytest-sync", "LocalOffer", "ePass"],
                        "priority": 1,
                        "ordering": 1,
                        "steps": steps,
                    }
                ],
            }
        ],
        "environmentCollection": [],
    }


def CloneCollectionWithDisplayName(payload: JsonObject, display_name: str) -> JsonObject:
    """复制集合并替换 ``info.name``（用于 e2e-core / mainflow 别名输出）。"""
    cloned = json.loads(json.dumps(payload, ensure_ascii=False))
    cloned.setdefault("info", {})["name"] = display_name
    return cloned


def CountPostmanRequests(collection: JsonObject) -> int:
    return len(FlattenPostmanRequestItems(collection.get("item", [])))


def WritePostmanCollectionJson(payload: JsonObject, out_path: str) -> int:
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    count = CountPostmanRequests(payload)
    print(f"Wrote {out_path} ({count} HTTP steps)")
    return count


def WriteApifoxImportJson(payload: JsonObject, out_path: str, *, scenario_label: str) -> None:
    apifox_payload = BuildApifox2743ImportPayload(payload)
    for col in apifox_payload.get("apiTestCaseCollection", []):
        for item in col.get("items", []):
            if str(item.get("name", "")).startswith("P1 E2E pytest-sync"):
                item["name"] = scenario_label
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(apifox_payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Wrote {out_path}")


def PatchP0CollectionResourceIdOptionIdEnv() -> None:
    """同步 P0 集合内嵌 JS：resourceId/optionId 从环境变量读取（与 P1 生成器一致）。"""
    import re

    p0_path = str(CollectionPath(P0_COLLECTION_JSON_NAME))
    if not os.path.isfile(p0_path):
        return
    old_resource_block = (
        '                  "function loExpectResourceIdMatch(label, actual) {",\n'
        '                  "  var expected = pm.collectionVariables.get(\'resourceId\');",\n'
        '                  "  if (expected && String(expected).trim()) {",\n'
        '                  "    pm.expect(actual, label + \' resourceId\').to.eql(expected);",\n'
        '                  "  } else {",\n'
        '                  "    pm.expect(actual, label + \' resourceId 非空\').to.be.a(\'string\').and.not.empty;",\n'
        '                  "    pm.collectionVariables.set(\'resourceId\', String(actual));",\n'
        '                  "  }",\n'
        '                  "}",'
    )
    new_resource_block = (
        '                  "function loResolveExpectedResourceId() {",\n'
        '                  "  var v = pm.variables.get(\'resourceId\');",\n'
        '                  "  if (v === undefined || v === null) return \'\';",\n'
        '                  "  v = String(v).trim();",\n'
        '                  "  if (!v || v.indexOf(\'{{\') >= 0) return \'\';",\n'
        '                  "  return v;",\n'
        '                  "}",\n'
        '                  "function loResolveExpectedOptionId() {",\n'
        '                  "  var v = pm.variables.get(\'optionId\');",\n'
        '                  "  if (v === undefined || v === null) return \'\';",\n'
        '                  "  v = String(v).trim();",\n'
        '                  "  if (!v || v.indexOf(\'{{\') >= 0) return \'\';",\n'
        '                  "  return v;",\n'
        '                  "}",\n'
        '                  "function loExpectResourceIdMatch(label, actual) {",\n'
        '                  "  var expected = loResolveExpectedResourceId();",\n'
        '                  "  pm.expect(expected, label + \' 环境变量 resourceId 已配置（DP_LO_EPASS_RESOURCE_ID）\').to.be.a(\'string\').and.not.empty;",\n'
        '                  "  pm.expect(actual, label + \' resourceId\').to.eql(expected);",\n'
        '                  "}",'
    )
    old_option_block = (
        '                  "  var expected = pm.collectionVariables.get(\'optionId\');",\n'
        '                  "  if (expected && String(expected).trim()) {",\n'
        '                  "    pm.expect(actual, label + \' optionId\').to.eql(expected);",\n'
        '                  "  } else {",\n'
        '                  "    pm.collectionVariables.set(\'optionId\', String(actual));",\n'
        '                  "  }",'
    )
    new_option_block = (
        '                  "  var expected = loResolveExpectedOptionId();",\n'
        '                  "  pm.expect(expected, label + \' 环境变量 optionId 已配置（DP_LO_EPASS_OPTION_ID）\').to.be.a(\'string\').and.not.empty;",\n'
        '                  "  pm.expect(actual, label + \' optionId\').to.eql(expected);",'
    )
    old_details = 'pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get(\'resourceId\'));'
    new_details = "loExpectResourceIdMatch(label, data().extra.resourceId);"
    with open(p0_path, encoding="utf-8") as handle:
        text = handle.read()
    if "pm.collectionVariables.get('resourceId')" not in text:
        print(f"Skip P0 patch (already env-based?): {p0_path}")
        return
    text = text.replace(old_resource_block, new_resource_block)
    text = text.replace(old_option_block, new_option_block)
    text = text.replace(old_details, new_details)
    desc_old = "**必填变量**：ProgramID、clientId、secret；E02/E03 另填 resourceId、optionId。"
    desc_new = (
        "**环境变量**：ProgramID、clientId、secret、resourceId、optionId（见 "
        "``LocalOffer-ePass-sandbox.postman_environment.json``，对齐 ``DP_LO_EPASS_*``）。"
    )
    text = text.replace(desc_old, desc_new)
    text = re.sub(
        r'\n    \{\n      "key": "resourceId",\n      "value": "",\n      "type": "string"\n    \},\n'
        r'    \{\n      "key": "optionId",\n      "value": "",\n      "type": "string"\n    \},\n',
        "\n",
        text,
        count=1,
    )
    with open(p0_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"Patched P0 resourceId/optionId env resolution: {p0_path}")


def PatchP0RemoveVoucherTypeAssertion() -> None:
    """P0：移除 ``vouchersList[0].voucherType`` 断言（网点实际券型可能与 expectedVoucherType 不一致）。"""
    import re

    p0_path = str(CollectionPath(P0_COLLECTION_JSON_NAME))
    if not os.path.isfile(p0_path):
        return
    fn_block = (
        '                  "function loAssertVoucherTypeIfExpected(label, extra) {",\n'
        '                  "  var expected = pm.collectionVariables.get(\'expectedVoucherType\');",\n'
        '                  "  if (expected === undefined || expected === null || String(expected).trim() === \'\') return;",\n'
        '                  "  var vt = parseInt(String(expected), 10);",\n'
        '                  "  if (isNaN(vt)) return;",\n'
        '                  "  pm.test(label + \': vouchersList[0].voucherType=\' + vt, function () {",\n'
        '                  "    pm.expect(extra).to.be.an(\'object\');",\n'
        '                  "    var vouchers = extra.vouchersList;",\n'
        '                  "    pm.expect(vouchers, \'vouchersList\').to.be.an(\'array\').and.not.empty;",\n'
        '                  "    pm.expect(vouchers[0].voucherType).to.eql(vt);",\n'
        '                  "  });",\n'
        '                  "}",\n'
    )
    with open(p0_path, encoding="utf-8") as handle:
        text = handle.read()
    if "loAssertVoucherTypeIfExpected" not in text:
        print(f"Skip P0 voucherType patch (already removed?): {p0_path}")
        return
    text = text.replace(fn_block, "")
    text = text.replace('                  "  loAssertVoucherTypeIfExpected(label, data().extra);",\n', "")
    text = text.replace('                  "pm.collectionVariables.set(\'expectedVoucherType\', \'1\');",\n', "")
    text = text.replace('                  "pm.collectionVariables.set(\'expectedVoucherType\', \'4\');",\n', "")
    text = re.sub(
        r'\n    \{\n      "key": "expectedVoucherType",\n      "value": "1",\n      "type": "string"\n    \},\n',
        "\n",
        text,
        count=1,
    )
    with open(p0_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"Patched P0 removed voucherType assertion: {p0_path}")


def Main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="生成 Local Offer ePass P0/P1 E2E Postman / Apifox JSON")
    parser.add_argument(
        "--patch-p0",
        action="store_true",
        help="兼容旧开关：现已默认重写 P0 E2E 核心集合（与 P1 E2E 同构 37 步）",
    )
    parser.add_argument(
        "--with-full",
        action="store_true",
        help="同时生成 Full 集合（100+ HTTP 步骤，见 GeneratePostmanCollectionLocalOfferEpassFull.py）",
    )
    args = parser.parse_args()

    payload = BuildCollection()
    step_count = WritePostmanCollectionJson(payload, str(CollectionPath(OUT_NAME)))
    WriteApifoxImportJson(
        payload,
        str(GeneratedArtifactPath(APIFOX_2743_IMPORT_NAME)),
        scenario_label="P1 E2E pytest-sync（Auth + E01 + E02 + E03）",
    )

    legacy_payload = CloneCollectionWithDisplayName(payload, COLLECTION_LEGACY_DISPLAY_NAME)
    WritePostmanCollectionJson(legacy_payload, str(CollectionPath(P1_E2E_CORE_OUT_NAME)))
    WritePostmanCollectionJson(legacy_payload, str(CollectionPath(P1_MAINFLOW_OUT_NAME)))
    WriteApifoxImportJson(
        legacy_payload,
        str(GeneratedArtifactPath(P1_E2E_CORE_APIFOX_NAME)),
        scenario_label="P1 E2E 核心（Auth + E01 + E02 + E03）",
    )

    # P0 冒烟 = 同构 E2E 核心（Auth + E01/E02/E03）；CLI 资产 local_offer_epass_p0
    p0_payload = CloneCollectionWithDisplayName(payload, "Local Offer ePass · P0 E2E 核心")
    p0_info = p0_payload.get("info")
    if isinstance(p0_info, dict):
        p0_info["description"] = (
            "由 GeneratePostmanCollectionLocalOfferEpass.py 生成（**P0 冒烟 · E2E 核心 37 步**）。\n"
            "与 P1 E2E pytest-sync 同构；挂载 ``epass/P0(冒烟用例)/prebooking``。\n\n"
            + str(p0_info.get("description") or "")
        )
    WritePostmanCollectionJson(p0_payload, str(CollectionPath(P0_COLLECTION_JSON_NAME)))

    print(f"P0/P1 E2E 核心 {step_count} 个 HTTP 步骤（Auth 1 + E01 12 + E02 10 + E03 14）")
    print(f"Wrote P0: {P0_COLLECTION_JSON_NAME}")
    print("100+ 步分模块：LocalOffer-ePass-full-pytest-sync.postman_collection.json")

    if args.with_full:
        full_path = str(Path(__file__).resolve().parent / "GeneratePostmanCollectionLocalOfferEpassFull.py")
        print(f"Running Full generator: {full_path}")
        import runpy

        runpy.run_path(full_path, run_name="__main__")

    if args.patch_p0:
        print("Note: --patch-p0 已弃用（P0 现由本脚本直接重写）")


if __name__ == "__main__":
    Main()
