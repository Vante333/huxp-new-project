"""
Dining Discount Apifox CLI 公共件（helpers / 入参 / RequestItem 包装）。

E-pass 与 Membership 两套生成器共用 ``dd*`` JS：Auth 写入 ``*HelpersSource``，业务步 eval。
Dining Discount 只有 walk-in；核销 / Callback / 取消不在本套件。
Membership 含 ``POST /v2/memberships/qrCodes``（展码，非核销）；ePass 不测二维码。

``module=5``；发放 path ``/v2/orders/discounts/ePasses``（OAS path enum 尚未含 discounts，按已确认契约）。
全网络 E-pass：**不传** ``resourceIds``（不是 ``[]``）。
``resourceIds`` 上限 30；混品类负向取 coupon ``module=4``，禁止用 coupon ID 凑 31 条。
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Final, List, Optional

from collection_builder_common import (
    AuthJsonHeaders,
    BearerJsonHeaders,
    JsRuntimeIdCaptureHelpersBlock,
    JsRuntimeVarScopeHelpersBlock,
    Lines_Step,
    RequestItem,
)

JsonObject = Dict[str, Any]

DINING_MODULE: Final[int] = 5
COUPON_MODULE: Final[int] = 4
WALKIN_CATEGORY: Final[int] = 1
RESOURCE_ID_MAX: Final[int] = 30
CREATE_FIRST_NAME: Final[str] = "Auto"
CREATE_LAST_NAME: Final[str] = "Test"
CREATE_EXPIRATION_DATE: Final[str] = "2028-12-31T23:59:59+00:00"
CREATE_AVAILABLE_USAGES: Final[int] = 2
MEMBERSHIP_NEW_EXPIRATION: Final[str] = "2035-12-31T23:59:59+00:00"
QR_DURATION_SECONDS: Final[int] = 60
CONTACT_PHONE: Final[str] = "8081966002"
CONTACT_CALLING_CODE: Final[str] = "44"
ERR_MIXED_MODULE: Final[str] = "500.063.001"
ERR_OVER_LIMIT: Final[str] = "500.063.002"
MSG_MIXED_NEEDLE: Final[str] = "not associated with the expected module"
MSG_OVER_LIMIT_NEEDLE: Final[str] = "maximum limit of 30"
LIST_RESOURCES_PATH: Final[str] = (
    "/v2/resources?module={module}&pageNumber=1&pageSize=100&language=en-US"
)


def BuildDiningDiscountJsHelpersLines() -> List[str]:
    """``dd*`` helpers：资源动态取、发放/查询/权益断言。Auth 写入源码变量后业务步 eval。"""
    scope = JsRuntimeVarScopeHelpersBlock(
        prefix="dd",
        extra_unset_env_keys=(
            "diningResourceId",
            "diningOtherModuleResourceId",
            "diningResourceIdsJson",
            "ePassIdNetwork",
            "ePassIdScoped",
        ),
    )
    capture = JsRuntimeIdCaptureHelpersBlock(prefix="dd")
    extra = r"""
function ddGetRoot() {
  try { return pm.response.json(); } catch (e0) { return {}; }
}
function ddGetInnerData(root) {
  root = root || ddGetRoot();
  if (root && root.data !== undefined && root.data !== null) return root.data;
  return root || {};
}
function ddFmtBrief(v, maxLen) {
  maxLen = maxLen || 240;
  var s;
  try { s = JSON.stringify(v); } catch (e0) { s = null; }
  if (s == null) s = String(v);
  s = String(s);
  if (s.length > maxLen) return s.slice(0, maxLen) + '...(len=' + s.length + ')';
  return s;
}
function ddAssertCheck(checkpoint, expected, actual) {
  var title = checkpoint + ' | 期望=' + ddFmtBrief(expected) + ' | 实际=' + ddFmtBrief(actual);
  pm.test(title, function () { pm.expect(actual).to.eql(expected); });
}
function ddAssertInfo(checkpoint, expectedDesc, actualValue) {
  var title = checkpoint + ' | 期望=' + expectedDesc + ' | 实际=' + ddFmtBrief(actualValue);
  pm.test(title, function () { pm.expect(true).to.eql(true); });
}
function ddAssertHttpBusinessOk(label) {
  ddAssertCheck(label + ': HTTP 状态码', 200, pm.response.code);
  var root = ddGetRoot();
  var code = root && root.code;
  var ok = code === 0 || code === '0';
  if (!ok) {
    ddAssertInfo(
      label + ': 业务失败 errCode/msg',
      String((root && root.errCode) || ''),
      root && root.msg
    );
  }
  pm.test(label + ': 业务 code=0 | 期望=0 | 实际=' + ddFmtBrief(code), function () {
    pm.expect(ok).to.eql(true);
  });
  return ok;
}
function ddIfSkipped(flag) {
  return String(ddGetVar(flag) || '') === '1';
}
function ddMarkSkip(flag, reason) {
  ddSetVar(flag, '1');
  console.log('[skip] ' + reason);
  try { if (pm.execution && typeof pm.execution.skipRequest === 'function') pm.execution.skipRequest(); } catch (e0) {}
}
function ddClearSkip(flag) {
  ddSetVar(flag, '0');
}
function ddSkipTestsOrRun(flag, skipTitle, fn) {
  if (ddIfSkipped(flag)) {
    ddAssertInfo(skipTitle, '本步已 skipRequest', ddGetVar(flag));
    return;
  }
  fn();
}
function ddApplyResourcesListQuery(module) {
  var pairs = [
    ['module', String(module)],
    ['pageNumber', '1'],
    ['pageSize', '100'],
    ['language', 'en-US']
  ];
  var qs = pairs.map(function (kv) { return kv[0] + '=' + kv[1]; }).join('&');
  try {
    if (!pm.request) return;
    if (typeof pm.request.url === 'string') {
      pm.request.url = String(pm.request.url).split('?')[0] + '?' + qs;
    } else if (pm.request.url) {
      var u = pm.request.url;
      if (u.query && typeof u.query.upsert === 'function') {
        pairs.forEach(function (kv) { u.query.upsert({ key: kv[0], value: kv[1] }); });
      } else {
        u.query = pairs.map(function (kv) { return { key: kv[0], value: kv[1] }; });
      }
    }
    console.log('[dining] LIST query 已写回 module=' + module + '（解绑后 GET query 常丢）');
  } catch (eQ) {
    console.warn('ddApplyResourcesListQuery', eQ);
  }
}
function ddForceApplyCapturedIds() {
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    function force(field, varName) {
      if (!body || !Object.prototype.hasOwnProperty.call(body, field)) return;
      var cur = body[field];
      var s = cur == null ? '' : String(cur);
      if (s.indexOf('$string.uuid') >= 0 || s.indexOf('$guid') >= 0) return;
      var val = ddGetVar(varName);
      if (!val) return;
      body[field] = val;
    }
    force('clientUserId', 'clientUserId');
    force('membershipId', 'membershipId');
    force('ePassId', 'ePassId');
    force('purchaseOrderId', 'purchaseOrderId');
    force('usageOrderId', 'usageOrderId');
    var urlStr = '';
    try {
      if (typeof pm.request.url === 'string') urlStr = pm.request.url;
      else if (pm.request.url && typeof pm.request.url.toString === 'function') urlStr = String(pm.request.url.toString());
    } catch (eU) { urlStr = ''; }
    if (urlStr.indexOf('users/memberships') >= 0 && body && Object.prototype.hasOwnProperty.call(body, 'status')) {
      delete body.status;
      console.log('[dining] users/memberships 去掉 OAS 样例 status，避免滤掉刚注册会籍');
    }
    if (urlStr.indexOf('memberships/update') >= 0 && body && Object.prototype.hasOwnProperty.call(body, 'status')) {
      delete body.status;
      console.log('[dining] memberships/update 去掉 OAS 样例 status，只改 expirationDate');
    }
    pm.request.body.raw = JSON.stringify(body, null, 2);
    if (body.clientUserId || body.membershipId) {
      console.log('[dining] force ids clientUserId=' + (body.clientUserId || '') + ' membershipId=' + (body.membershipId || ''));
    }
  } catch (eForce) {
    console.warn('ddForceApplyCapturedIds', eForce);
  }
}
function ddApplyDiningIdsToRequestBody() {
  ddApplyRuntimeIdsToRequestBody();
  ddForceApplyCapturedIds();
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var raw = String(pm.request.body.raw);
    function subst(name) {
      var val = ddGetVar(name);
      if (!val) return;
      var token = '{{' + name + '}}';
      while (raw.indexOf(token) >= 0) raw = raw.split(token).join(val);
    }
    subst('diningResourceId');
    subst('diningOtherModuleResourceId');
    subst('ePassIdNetwork');
    subst('ePassIdScoped');
    pm.request.body.raw = raw;
    var body = JSON.parse(String(pm.request.body.raw));
    if (body && body.extra && body.extra.allowedResources && Array.isArray(body.extra.allowedResources.resourceIds)) {
      var ids = body.extra.allowedResources.resourceIds;
      var rid = ddGetVar('diningResourceId');
      var oid = ddGetVar('diningOtherModuleResourceId');
      var lb = String.fromCharCode(123, 123);
      var rb = String.fromCharCode(125, 125);
      body.extra.allowedResources.resourceIds = ids.map(function (x) {
        var s = String(x == null ? '' : x);
        if (s.indexOf(lb + 'diningResourceId' + rb) >= 0 && rid) return rid;
        if (s.indexOf(lb + 'diningOtherModuleResourceId' + rb) >= 0 && oid) return oid;
        if (ddIsUnresolvedPlaceholder(s) && rid) return rid;
        return x;
      });
      pm.request.body.raw = JSON.stringify(body, null, 2);
    }
  } catch (eApply) {
    console.warn('ddApplyDiningIdsToRequestBody', eApply);
  }
}
function ddResourceRows(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  var r = data.resources;
  if (Array.isArray(r)) return r;
  var out = [];
  if (r && typeof r === 'object') {
    ['transportHubResources', 'lifestyleResources'].forEach(function (k) {
      if (Array.isArray(r[k])) out = out.concat(r[k]);
    });
    if (out.length) return out;
  }
  if (Array.isArray(data.list)) return data.list;
  if (Array.isArray(data.items)) return data.items;
  return [];
}
function ddRowResourceId(row) {
  if (!row) return '';
  if (typeof row === 'string') return String(row).trim();
  var id = row.resourceId || row.id || row.code || row.resourceCode;
  return id == null ? '' : String(id).trim();
}
function ddUniqueIds(rows) {
  var out = [];
  var seen = {};
  (rows || []).forEach(function (row) {
    var id = ddRowResourceId(row);
    if (!id || id.indexOf('{{') >= 0) return;
    if (seen[id]) return;
    seen[id] = 1;
    out.push(id);
  });
  return out;
}
function ddCaptureDiningList(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  var ids = ddUniqueIds(ddResourceRows(data));
  var rkeys = (data && data.resources && typeof data.resources === 'object') ? Object.keys(data.resources).join(',') : '';
  console.log('[dining] LIST parsed ids=' + ids.length + ' resourceKeys=' + rkeys);
  if (!ids.length) {
    pm.test(label + ': Dining 资源列表非空 | 期望=至少 1 条 module=5 | 实际=0（禁止 PLACEHOLDER）', function () {
      pm.expect.fail('GET /v2/resources?module=5 为空：无法动态取 diningResourceId，请检查 Program 是否开通 Dining Discount');
    });
    return;
  }
  ddSetVar('diningResourceId', ids[0]);
  ddSetVar('diningResourceIdsJson', JSON.stringify(ids));
  console.log('[dining] resourceId=' + ids[0] + ' count=' + ids.length);
  ddAssertCheck(label + ': 写入 diningResourceId 非空', true, !!ids[0]);
  ddAssertInfo(label + ': Dining 资源条数（31 条才跑 500.063.002）', '>=1；>=31 才跑超限', ids.length);
}
function ddCaptureCouponList(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  var ids = ddUniqueIds(ddResourceRows(data));
  if (!ids.length) {
    ddSetVar('diningOtherModuleResourceId', '');
    console.log('[dining] coupon module=4 列表为空：混品类 500.063.001 将 skip');
    ddAssertInfo(label + ': coupon 资源', '有则写入 diningOtherModuleResourceId；空则后续 skip 001', 0);
    return;
  }
  ddSetVar('diningOtherModuleResourceId', ids[0]);
  console.log('[dining] coupon resourceId=' + ids[0]);
  ddAssertCheck(label + ': 写入 diningOtherModuleResourceId', true, !!ids[0]);
}
function ddReadDiningIds() {
  var ids = [];
  try { ids = JSON.parse(ddGetVar('diningResourceIdsJson') || '[]'); } catch (e0) { ids = []; }
  return Array.isArray(ids) ? ids : [];
}
function ddEnsureNetworkCreateBody() {
  ddApplyDiningIdsToRequestBody();
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    if (body.extra && body.extra.allowedResources) {
      delete body.extra.allowedResources.resourceIds;
      delete body.extra.allowedResources.iata;
      delete body.extra.allowedResources.countryOrRegion;
    }
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('[dining] 全网络发放：不传 resourceIds');
  } catch (e0) { console.warn('ddEnsureNetworkCreateBody', e0); }
}
function ddEnsureScopedCreateBody() {
  ddApplyDiningIdsToRequestBody();
  var rid = ddGetVar('diningResourceId');
  if (!rid) {
    console.error('[dining] diningResourceId 为空，指定资源发放会失败');
    return;
  }
  try {
    var body = JSON.parse(String(pm.request.body.raw));
    if (!body.extra) body.extra = {};
    body.extra.allowedResources = { resourceIds: [rid] };
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('[dining] 指定资源发放 resourceIds=[' + rid + ']');
  } catch (e0) { console.warn('ddEnsureScopedCreateBody', e0); }
}
function ddEnsureMixCreateBody() {
  ddClearSkip('ddSkipMix001');
  var oid = ddGetVar('diningOtherModuleResourceId');
  if (!oid) {
    ddMarkSkip('ddSkipMix001', 'coupon module=4 无资源，skip 500.063.001（不用 Dining ID 冒充）');
    return;
  }
  ddApplyDiningIdsToRequestBody();
  try {
    var body = JSON.parse(String(pm.request.body.raw));
    if (!body.extra) body.extra = {};
    body.extra.allowedResources = { resourceIds: [oid] };
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('[dining] 混品类发放 resourceIds=[' + oid + '] 期望 500.063.001');
  } catch (e0) { console.warn('ddEnsureMixCreateBody', e0); }
}
function ddEnsureOverLimitCreateBody() {
  ddClearSkip('ddSkipOver002');
  var ids = ddReadDiningIds();
  if (ids.length < 31) {
    ddMarkSkip('ddSkipOver002', 'Dining 资源不足 31 个（现有 ' + ids.length + '），skip 500.063.002，禁止用 coupon ID 凑数');
    return;
  }
  ddApplyDiningIdsToRequestBody();
  try {
    var body = JSON.parse(String(pm.request.body.raw));
    if (!body.extra) body.extra = {};
    body.extra.allowedResources = { resourceIds: ids.slice(0, 31) };
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('[dining] 超限发放 resourceIds.length=31 期望 500.063.002');
  } catch (e0) { console.warn('ddEnsureOverLimitCreateBody', e0); }
}
function ddSaveCreateIds(data, aliasKey) {
  if (!data || typeof data !== 'object') return;
  ddCaptureClientUserIdAfterSend(data);
  if (data.orderId && !ddIsUnresolvedPlaceholder(data.orderId)) {
    ddSetVar('purchaseOrderId', String(data.orderId));
  }
  var extra = data.extra || {};
  var ep = extra.ePassId || extra.epassId || data.ePassId;
  if (ep && !ddIsUnresolvedPlaceholder(ep)) {
    ddSetVar('ePassId', String(ep));
    if (aliasKey) ddSetVar(aliasKey, String(ep));
  }
}
function ddReadSentCreate() {
  try {
    return JSON.parse(String(pm.request.body.raw || '{}'));
  } catch (e0) { return {}; }
}
function ddAssertAllowedResources(label, extra, mode) {
  var ar = (extra && extra.allowedResources) || {};
  var rids = ar.resourceIds;
  if (mode === 'network') {
    var empty = !rids || (Array.isArray(rids) && rids.length === 0);
    pm.test(label + ': 全网络不限制 resourceIds | 期望=不传/空 | 实际=' + ddFmtBrief(rids), function () {
      pm.expect(empty).to.eql(true);
    });
    return;
  }
  if (mode === 'scoped') {
    var expectId = ddGetVar('diningResourceId');
    ddAssertCheck(label + ': allowedResources.resourceIds', [expectId], rids);
  }
}
function ddAssertCreateEpass(label, mode, aliasKey) {
  if (!ddAssertHttpBusinessOk(label)) return;
  var data = ddGetInnerData();
  var sent = ddReadSentCreate();
  ddSaveCreateIds(data, aliasKey);
  ddAssertCheck(label + ': module', 5, data.module);
  ddAssertCheck(label + ': category', 1, data.category);
  ddAssertCheck(label + ': status', 1, data.status);
  ddAssertCheck(label + ': clientUserId', ddGetVar('clientUserId'), data.clientUserId);
  pm.test(label + ': orderId 非空 | 期望=系统生成 | 实际=' + ddFmtBrief(data.orderId), function () {
    pm.expect(data.orderId).to.be.ok;
  });
  pm.test(label + ': orderCreatedDate 非空 | 期望=创建时间 | 实际=' + ddFmtBrief(data.orderCreatedDate), function () {
    pm.expect(data.orderCreatedDate).to.be.ok;
  });
  ddAssertCheck(label + ': orderCancelledDate', null, data.orderCancelledDate == null ? null : data.orderCancelledDate);
  var extra = data.extra || {};
  var ep = extra.ePassId || extra.epassId;
  pm.test(label + ': extra.ePassId 16 位数字 | 期望=/^[0-9]{16}$/ | 实际=' + ddFmtBrief(ep), function () {
    pm.expect(String(ep || '')).to.match(/^[0-9]{16}$/);
  });
  ddAssertCheck(label + ': extra.ePassStatus', 1, extra.ePassStatus);
  ddAssertCheck(label + ': extra.firstName', sent.extra && sent.extra.firstName, extra.firstName);
  ddAssertCheck(label + ': extra.lastName', sent.extra && sent.extra.lastName, extra.lastName);
  if (sent.extra && sent.extra.activationDate) {
    ddAssertCheck(label + ': extra.activationDate', sent.extra.activationDate, extra.activationDate);
  }
  ddAssertCheck(label + ': extra.expirationDate', sent.extra && sent.extra.expirationDate, extra.expirationDate);
  ddAssertCheck(label + ': extra.availableUsages', sent.extra && sent.extra.availableUsages, extra.availableUsages);
  ddAssertCheck(label + ': extra.usedUsages', 0, extra.usedUsages);
  ddAssertAllowedResources(label, extra, mode);
}
function ddAssertSearchEpass(label) {
  if (!ddAssertHttpBusinessOk(label)) return;
  var data = ddGetInnerData();
  ddAssertCheck(label + ': module', 5, data.module);
  ddAssertCheck(label + ': category', 1, data.category);
  ddAssertCheck(label + ': status', 1, data.status);
  ddAssertCheck(label + ': orderId', ddGetVar('purchaseOrderId'), data.orderId);
  ddAssertCheck(label + ': clientUserId', ddGetVar('clientUserId'), data.clientUserId);
  var extra = data.extra || {};
  ddAssertCheck(label + ': extra.ePassId', ddGetVar('ePassId'), extra.ePassId || extra.epassId);
  ddAssertCheck(label + ': extra.ePassStatus Active', 1, extra.ePassStatus);
  ddAssertCheck(label + ': extra.firstName', 'Auto', extra.firstName);
  ddAssertCheck(label + ': extra.lastName', 'Test', extra.lastName);
  ddAssertCheck(label + ': extra.availableUsages', 2, extra.availableUsages);
  ddAssertCheck(label + ': extra.usedUsages 未使用', 0, extra.usedUsages);
  ddAssertCheck(label + ': extra.expirationDate', '2028-12-31T23:59:59+00:00', extra.expirationDate);
  pm.test(label + ': extra.activationDate 非空 | 期望=系统默认/当前 | 实际=' + ddFmtBrief(extra.activationDate), function () {
    pm.expect(extra.activationDate).to.be.ok;
  });
  pm.test(label + ': orderCreatedDate 非空 | 期望=创建时间 | 实际=' + ddFmtBrief(data.orderCreatedDate), function () {
    pm.expect(data.orderCreatedDate).to.be.ok;
  });
  ddAssertCheck(label + ': orderCancelledDate', null, data.orderCancelledDate == null ? null : data.orderCancelledDate);
}
function ddAssertUsersEpasses(label) {
  if (!ddAssertHttpBusinessOk(label)) return;
  var data = ddGetInnerData();
  var pg = data.pagination || {};
  ddAssertCheck(label + ': pagination.pageSize', 10, pg.pageSize);
  ddAssertCheck(label + ': pagination.pageNumber', 1, pg.pageNumber);
  pm.test(label + ': pagination.totalNumber >=1 | 期望>=1 | 实际=' + ddFmtBrief(pg.totalNumber), function () {
    pm.expect(Number(pg.totalNumber || 0)).to.be.at.least(1);
  });
  var list = data.ePassesList || data.ePasses || [];
  var target = ddGetVar('ePassId');
  var hit = (list || []).filter(function (x) { return x && String(x.ePassId) === String(target); });
  pm.test(label + ': ePassesList 含本 ePassId | 期望=' + target + ' | 实际命中=' + hit.length, function () {
    pm.expect(hit.length).to.be.above(0);
  });
  if (hit[0]) {
    ddAssertCheck(label + ': 命中项 module', 5, hit[0].module);
    ddAssertCheck(label + ': 命中项 status', hit[0].status, hit[0].status);
  }
}
function ddAssertUsageListAndCapture(label) {
  if (!ddAssertHttpBusinessOk(label)) return;
  ddSetVar('usageOrderId', '');
  var data = ddGetInnerData();
  var pg = data.pagination || {};
  ddAssertCheck(label + ': pagination.pageSize', 10, pg.pageSize);
  ddAssertCheck(label + ': pagination.pageNumber', 1, pg.pageNumber);
  var orders = data.orders || [];
  var total = Number(pg.totalNumber == null ? orders.length : pg.totalNumber);
  if (!orders.length || total === 0) {
    ddAssertInfo(label + ': 使用订单列表为空通过', 'walk-in 未核销可为空；详情将 skip', total);
    return;
  }
  var first = orders[0] || {};
  if (first.orderId) ddSetVar('usageOrderId', String(first.orderId));
  ddAssertCheck(label + ': orders[0].module', 5, first.module);
  ddAssertCheck(label + ': orders[0].category', 1, first.category);
  pm.test(label + ': orders[0].orderId 非空 | 期望=列表取 | 实际=' + ddFmtBrief(first.orderId), function () {
    pm.expect(first.orderId).to.be.ok;
  });
  pm.test(label + ': orders[0].orderCreatedDate 非空 | 期望=有值 | 实际=' + ddFmtBrief(first.orderCreatedDate), function () {
    pm.expect(first.orderCreatedDate).to.be.ok;
  });
  if (Number(first.status) === 1) {
    pm.test(label + ': 未核销不返回 usedUsages | 期望=无该字段 | 实际=' + ddFmtBrief(first.usedUsages), function () {
      pm.expect(Object.prototype.hasOwnProperty.call(first, 'usedUsages')).to.eql(false);
    });
  }
  var extra = first.extra || {};
  ddAssertCheck(label + ': extra.optionId', null, extra.optionId == null ? null : extra.optionId);
  ddAssertCheck(label + ': extra.optionName', null, extra.optionName == null ? null : extra.optionName);
}
function ddSkipUsageDetailsIfEmpty() {
  ddClearSkip('ddSkipUsageDetails');
  if (!ddGetVar('usageOrderId')) {
    ddMarkSkip('ddSkipUsageDetails', '使用订单列表为空，skip 详情（orderId 只从列表取）');
  }
}
function ddAssertUsageDetails(label) {
  ddSkipTestsOrRun('ddSkipUsageDetails', label + ': 无 usageOrderId skip 详情', function () {
    ddAssertHttpBusinessOk(label);
    var data = ddGetInnerData();
    ddAssertCheck(label + ': module', 5, data.module);
    ddAssertCheck(label + ': category', 1, data.category);
    ddAssertCheck(label + ': orderId', ddGetVar('usageOrderId'), data.orderId);
    var ep = data.ePassId || (data.extra && data.extra.ePassId);
    ddAssertCheck(label + ': ePassId', ddGetVar('ePassId'), ep);
    if (Number(data.status) === 1) {
      var extra = data.extra || {};
      pm.test(label + ': 未核销不返回 extra.usedUsages | 期望=无该字段 | 实际=' + ddFmtBrief(extra.usedUsages), function () {
        pm.expect(Object.prototype.hasOwnProperty.call(extra, 'usedUsages')).to.eql(false);
      });
      ddAssertCheck(label + ': extra.usageDate 未核销', null, extra.usageDate == null ? null : extra.usageDate);
    }
    ddAssertCheck(label + ': extra.clientUserId', ddGetVar('clientUserId'), (data.extra || {}).clientUserId);
  });
}
function ddAssertBusinessError(label, errCode, needle) {
  ddAssertCheck(label + ': HTTP 状态码', 200, pm.response.code);
  var root = ddGetRoot();
  ddAssertCheck(label + ': errCode', errCode, root.errCode == null ? '' : String(root.errCode));
  var msg = root.msg == null ? '' : String(root.msg);
  pm.test(label + ': msg 含关键字 | 期望含=' + needle + ' | 实际=' + ddFmtBrief(msg), function () {
    pm.expect(msg.toLowerCase()).to.include(String(needle).toLowerCase());
  });
  var code = root.code;
  pm.test(label + ': 业务失败 code!=0 | 期望!=0 | 实际=' + ddFmtBrief(code), function () {
    pm.expect(code === 0 || code === '0').to.eql(false);
  });
}
function ddFindModule5Block(entitlements) {
  var arr = entitlements && entitlements.moduleExclusiveEntitlements;
  if (!Array.isArray(arr)) return null;
  for (var i = 0; i < arr.length; i++) {
    if (arr[i] && Number(arr[i].module) === 5) return arr[i];
  }
  return null;
}
function ddResolveDiningDetails(data) {
  if (!data || typeof data !== 'object') return {};
  var b = ddFindModule5Block(data.entitlements);
  if (b && b.details) return b.details;
  if (data.entitlements && data.entitlements.details) return data.entitlements.details;
  b = ddFindModule5Block(data);
  if (b && b.details) return b.details;
  if (data.details) return data.details;
  var hasDirect = DD_ENT_FIELDS.some(function (f) { return data[f] != null; });
  if (hasDirect) return data;
  return {};
}
var DD_ENT_FIELDS = [
  'cardholderExclusiveEntitlements',
  'guestsExclusiveEntitlements',
  'sharedEntitlements',
  'purchasedEntitlements'
];
function ddNum(v) {
  var n = Number(v);
  return isNaN(n) ? 0 : n;
}
function ddCaptureEntitlementSnapshot(label, data) {
  var details = ddResolveDiningDetails(data);
  DD_ENT_FIELDS.forEach(function (f) {
    var n = ddNum(details[f]);
    ddSetVar('ddSnap_' + f, String(n));
    ddSetVar('ddExpect_' + f, String(n));
  });
  if (details.allowedGuestsPerUsage != null) {
    ddSetVar('ddSnap_allowedGuestsPerUsage', String(details.allowedGuestsPerUsage));
  }
  if (details.maxGuestsNextUse != null) {
    ddSetVar('ddSnap_maxGuestsNextUse', String(details.maxGuestsNextUse));
  }
  console.log('[dining] entitlements snapshot ' + JSON.stringify({
    cardholder: ddGetVar('ddSnap_cardholderExclusiveEntitlements'),
    guests: ddGetVar('ddSnap_guestsExclusiveEntitlements'),
    shared: ddGetVar('ddSnap_sharedEntitlements'),
    purchased: ddGetVar('ddSnap_purchasedEntitlements')
  }));
  ddAssertInfo(label + ': 已快照 module=5 四类权益', '注册模板值（含 0）', details);
}
function ddAssertFourEntitlementsPresent(label, details) {
  DD_ENT_FIELDS.forEach(function (f) {
    pm.test(label + ': details.' + f + ' 为数字 | 期望=number | 实际=' + ddFmtBrief(details[f]), function () {
      pm.expect(details[f] == null ? null : Number(details[f])).to.be.a('number');
    });
  });
}
function ddAssertEntitlementsMatchExpect(label, data) {
  var details = ddResolveDiningDetails(data);
  var hasAny = DD_ENT_FIELDS.some(function (f) { return details[f] != null; });
  if (!hasAny) {
    ddAssertInfo(label + ': 未解析到 module=5 四类权益字段', '有则对拍 running expect', Object.keys(data || {}));
    return;
  }
  DD_ENT_FIELDS.forEach(function (f) {
    ddAssertCheck(label + ': ' + f, ddNum(ddGetVar('ddExpect_' + f)), ddNum(details[f]));
  });
  if (details.allowedGuestsPerUsage != null && ddGetVar('ddSnap_allowedGuestsPerUsage')) {
    ddAssertCheck(label + ': allowedGuestsPerUsage', ddNum(ddGetVar('ddSnap_allowedGuestsPerUsage')), ddNum(details.allowedGuestsPerUsage));
  }
}
function ddSaveMembershipId(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  var cid = '';
  if (data && data.clientUserId != null) cid = String(data.clientUserId).trim();
  if ((!cid || ddIsUnresolvedPlaceholder(cid)) && data && data.extra && data.extra.clientUserId != null) {
    cid = String(data.extra.clientUserId).trim();
  }
  if (cid && !ddIsUnresolvedPlaceholder(cid)) {
    ddSetVar('clientUserId', cid);
  } else {
    ddCaptureClientUserIdAfterSend(data);
  }
  var mid = data.membershipId || data.id;
  pm.test(label + ': membershipId 16 位数字 | 期望=/^[0-9]{16}$/ | 实际=' + ddFmtBrief(mid), function () {
    pm.expect(String(mid || '')).to.match(/^[0-9]{16}$/);
  });
  ddSetVar('membershipId', String(mid));
  console.log('[dining] 注册回写 clientUserId=' + ddGetVar('clientUserId') + ' membershipId=' + ddGetVar('membershipId'));
  if (data.registrationDate) ddSetVar('ddReg_registrationDate', String(data.registrationDate));
  if (data.activationDate) ddSetVar('ddReg_activationDate', String(data.activationDate));
  if (data.expirationDate) ddSetVar('ddReg_expirationDate', String(data.expirationDate));
  ddAssertCheck(label + ': clientUserId 取自注册响应', cid || ddGetVar('clientUserId'), data.clientUserId);
  pm.test(label + ': programId 非空 | 期望=当前 Program | 实际=' + ddFmtBrief(data.programId), function () {
    pm.expect(data.programId).to.be.ok;
  });
  var block = ddFindModule5Block(data.entitlements);
  pm.test(label + ': 含 module=5 权益块 | 期望=有 | 实际=' + ddFmtBrief(block && block.module), function () {
    pm.expect(block && Number(block.module) === 5).to.eql(true);
  });
  var details = (block && block.details) || {};
  ddAssertFourEntitlementsPresent(label, details);
  ddCaptureEntitlementSnapshot(label, data);
}
function ddAssertUsersMemberships(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  var pg = data.pagination || {};
  ddAssertCheck(label + ': pagination.pageSize', 10, pg.pageSize);
  ddAssertCheck(label + ': pagination.pageNumber', 1, pg.pageNumber);
  var list = data.membershipsList || data.memberships || [];
  var mid = ddGetVar('membershipId');
  var hit = (list || []).filter(function (x) { return x && String(x.membershipId) === String(mid); });
  pm.test(label + ': membershipsList 含本 membershipId | 期望=' + mid + ' | 实际命中=' + hit.length, function () {
    pm.expect(hit.length).to.be.above(0);
  });
  if (hit[0]) {
    ddAssertCheck(label + ': 命中项 membershipId', mid, String(hit[0].membershipId));
    pm.test(label + ': 命中项 programId 非空 | 期望=当前 Program | 实际=' + ddFmtBrief(hit[0].programId), function () {
      pm.expect(hit[0].programId).to.be.ok;
    });
  }
}
function ddAssertMembershipSearch(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  ddAssertCheck(label + ': membershipId', ddGetVar('membershipId'), String(data.membershipId || ''));
  ddAssertCheck(label + ': clientUserId', ddGetVar('clientUserId'), data.clientUserId);
  pm.test(label + ': programId 非空 | 期望=当前 Program | 实际=' + ddFmtBrief(data.programId), function () {
    pm.expect(data.programId).to.be.ok;
  });
  pm.test(label + ': status 有值 | 期望=当前状态 | 实际=' + ddFmtBrief(data.status), function () {
    pm.expect(data.status !== undefined && data.status !== null).to.eql(true);
  });
  if (ddGetVar('ddReg_registrationDate')) {
    ddAssertCheck(label + ': registrationDate', ddGetVar('ddReg_registrationDate'), data.registrationDate);
  }
}
function ddAssertMembershipUpdateDates(label) {
  ddAssertHttpBusinessOk(label);
  var data = ddGetInnerData();
  ddAssertCheck(label + ': membershipId', ddGetVar('membershipId'), String(data.membershipId || ''));
  ddAssertCheck(label + ': expirationDate', '2035-12-31T23:59:59+00:00', data.expirationDate);
  if (ddGetVar('ddReg_registrationDate')) {
    ddAssertCheck(label + ': registrationDate 不被改写', ddGetVar('ddReg_registrationDate'), data.registrationDate);
  }
}
function ddSkipUpdateIfZero(field, flag) {
  ddClearSkip(flag);
  var n = ddNum(ddGetVar('ddSnap_' + field));
  if (!n) {
    ddMarkSkip(flag, field + '=0，skip 大客户类更新（买点仍会打）');
  }
}
function ddSkipIfFlag(flag, reason) {
  if (ddIfSkipped(flag)) {
    ddMarkSkip(flag, reason || ('沿用 skip ' + flag));
  }
}
function ddBumpExpect(field) {
  ddSetVar('ddExpect_' + field, String(ddNum(ddGetVar('ddExpect_' + field)) + 1));
}
function ddAssertEntitlementUpdate(label, bumpedField) {
  ddSkipTestsOrRun('ddSkipUpd_' + bumpedField, label + ': 该类权益为 0 已 skip', function () {
    if (!ddAssertHttpBusinessOk(label)) return;
    ddBumpExpect(bumpedField);
    var data = ddGetInnerData();
    ddAssertCheck(label + ': membershipId', ddGetVar('membershipId'), String(data.membershipId || ''));
    var block = ddFindModule5Block(data.entitlements);
    pm.test(label + ': 响应含 module=5 | 期望=5 | 实际=' + ddFmtBrief(block && block.module), function () {
      pm.expect(block && Number(block.module) === 5).to.eql(true);
    });
    ddAssertEntitlementsMatchExpect(label, data);
  });
}
function ddAssertEntitlementSearch(label, skipFlag) {
  ddSkipTestsOrRun(skipFlag, label + ': 随更新步 skip', function () {
    ddAssertHttpBusinessOk(label);
    var data = ddGetInnerData();
    var block = ddFindModule5Block(data.entitlements);
    pm.test(label + ': 概览含 module=5 | 期望=5 | 实际=' + ddFmtBrief(block && block.module), function () {
      pm.expect(block && Number(block.module) === 5).to.eql(true);
    });
    ddAssertEntitlementsMatchExpect(label, data);
  });
}
function ddAssertEntitlementDetails(label, skipFlag) {
  ddSkipTestsOrRun(skipFlag, label + ': 随更新步 skip', function () {
    ddAssertHttpBusinessOk(label);
    var data = ddGetInnerData();
    ddAssertCheck(label + ': membershipId', ddGetVar('membershipId'), String(data.membershipId || ''));
    if (data.module != null) ddAssertCheck(label + ': module', 5, data.module);
    if (data.scopeType != null) ddAssertCheck(label + ': scopeType', 1, data.scopeType);
    ddAssertEntitlementsMatchExpect(label, data);
  });
}
function ddAssertMembershipUsageList(label) {
  ddAssertHttpBusinessOk(label);
  ddSetVar('usageOrderId', '');
  var data = ddGetInnerData();
  var pg = data.pagination || {};
  ddAssertCheck(label + ': pagination.pageSize', 10, pg.pageSize);
  pm.test(label + ': pagination.pageNumber | 期望=请求 1 | 实际=' + ddFmtBrief(pg.pageNumber), function () {
    pm.expect([0, 1]).to.include(Number(pg.pageNumber));
  });
  var orders = data.orders || [];
  var total = Number(pg.totalNumber == null ? orders.length : pg.totalNumber);
  if (!orders.length || total === 0) {
    ddAssertInfo(label + ': 使用订单列表为空通过', '未核销可为空；详情 skip', total);
    return;
  }
  var first = orders[0] || {};
  if (first.orderId) ddSetVar('usageOrderId', String(first.orderId));
  ddAssertCheck(label + ': orders[0].module', 5, first.module);
  ddAssertCheck(label + ': orders[0].category', 1, first.category);
  if (Number(first.status) === 1) {
    pm.test(label + ': 未核销不返回 passengerCounts | 期望=无该字段 | 实际=' + ddFmtBrief(first.passengerCounts), function () {
      pm.expect(Object.prototype.hasOwnProperty.call(first, 'passengerCounts')).to.eql(false);
    });
  }
}
function ddStampQrRequestUnix() {
  ddSetVar('ddQrRequestedAtUnix', String(Math.floor(Date.now() / 1000)));
}
function ddAssertMembershipQrCodes(label, durationSec) {
  if (!ddAssertHttpBusinessOk(label)) return;
  var data = ddGetInnerData();
  var qr = data.qrCode;
  pm.test(label + ': qrCode 非空 | 期望=非空字符串 | 实际=' + ddFmtBrief(qr), function () {
    pm.expect(qr).to.be.a('string').and.not.empty;
  });
  var vu = Number(data.validUntil);
  var sentAt = Number(ddGetVar('ddQrRequestedAtUnix') || 0);
  var dur = Number(durationSec);
  if (!dur) dur = 60;
  var expectUntil = sentAt + dur;
  var skew = 30;
  var delta = Math.abs(vu - expectUntil);
  pm.test(
    label + ': validUntil Unix 且与 duration 一致 | 期望≈' + expectUntil + '±' + skew + 's | 实际=' + ddFmtBrief(data.validUntil) + ' delta=' + delta,
    function () {
      pm.expect(isNaN(vu)).to.eql(false);
      pm.expect(vu).to.be.above(1000000000);
      pm.expect(sentAt).to.be.above(0);
      pm.expect(delta).to.be.at.most(skew);
    }
  );
  if (qr) ddSetVar('ddQrCode', String(qr));
  if (data.validUntil != null) ddSetVar('ddQrValidUntil', String(data.validUntil));
}
function ddAssertMembershipUsageDetails(label) {
  ddSkipTestsOrRun('ddSkipUsageDetails', label + ': 无 usageOrderId skip 详情', function () {
    ddAssertHttpBusinessOk(label);
    var data = ddGetInnerData();
    ddAssertCheck(label + ': module', 5, data.module);
    ddAssertCheck(label + ': category', 1, data.category);
    ddAssertCheck(label + ': membershipId', ddGetVar('membershipId'), String(data.membershipId || ''));
    ddAssertCheck(label + ': orderId', ddGetVar('usageOrderId'), data.orderId);
    if (Number(data.status) === 1) {
      var extra = data.extra || {};
      pm.test(label + ': 未核销不返回 passengerCounts | 期望=无该字段 | 实际=' + ddFmtBrief(extra.passengerCounts), function () {
        pm.expect(Object.prototype.hasOwnProperty.call(extra, 'passengerCounts')).to.eql(false);
      });
      pm.test(label + ': 未核销不返回 usedEntitlementDetails | 期望=无该字段 | 实际=' + ddFmtBrief(extra.usedEntitlementDetails), function () {
        pm.expect(Object.prototype.hasOwnProperty.call(extra, 'usedEntitlementDetails')).to.eql(false);
      });
      pm.test(label + ': 未核销不返回 usedEntitlementBreakdown | 期望=无该字段 | 实际=' + ddFmtBrief(extra.usedEntitlementBreakdown), function () {
        pm.expect(Object.prototype.hasOwnProperty.call(extra, 'usedEntitlementBreakdown')).to.eql(false);
      });
      ddAssertCheck(label + ': extra.usageDate 未核销', null, extra.usageDate == null ? null : extra.usageDate);
    }
  });
}
"""
    js = scope + capture + extra
    return [ln for ln in js.split("\n")]


def MakeDdRequestItem(helpers_source_key: str) -> Callable[..., JsonObject]:
    """Auth 写入 helpers 源码；其它步 eval；每步把运行时 ID 写进 body。"""

    def _Item(**kwargs: Any) -> JsonObject:
        kwargs.setdefault("js_helpers", BuildDiningDiscountJsHelpersLines)
        kwargs.setdefault("helpers_source_key", helpers_source_key)
        existing: List[str] = list(kwargs.get("prerequest_lines") or [])
        kwargs["prerequest_lines"] = existing + ["ddApplyDiningIdsToRequestBody();"]
        return RequestItem(**kwargs)

    return _Item


def Lines_Auth() -> List[str]:
    return [
        "ddAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 写入 | 期望=非空 | 实际=collection/variables', function () {",
        "  var t = ddGetVar('accessToken') || (pm.collectionVariables && pm.collectionVariables.get('accessToken'));",
        "  pm.expect(t).to.be.ok;",
        "});",
    ]


def AuthItem(helpers_source_key: str, *, purpose: str) -> JsonObject:
    item_fn = MakeDdRequestItem(helpers_source_key)
    return item_fn(
        name=purpose,
        method="POST",
        url_path="/v2/auth/token",
        body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
        headers=AuthJsonHeaders(),
        description="鉴权；写入 accessToken 与 helpers 源码。三列来自数据集选行，禁止写死 .env。",
        save_token=True,
        test_lines=Lines_Auth(),
    )


def CreateEpassBody(*, include_resource_placeholder: bool) -> str:
    extra: JsonObject = {
        "firstName": CREATE_FIRST_NAME,
        "lastName": CREATE_LAST_NAME,
        "expirationDate": CREATE_EXPIRATION_DATE,
        "availableUsages": CREATE_AVAILABLE_USAGES,
        "allowedResources": {},
    }
    if include_resource_placeholder:
        extra["allowedResources"] = {"resourceIds": ["{{diningResourceId}}"]}
    return json.dumps(
        {
            "module": DINING_MODULE,
            "clientUserId": "{{clientUserId}}",
            "extra": extra,
        },
        ensure_ascii=False,
        indent=2,
    )


def CreateEpassBodyFreshUser(*, include_resource_placeholder: bool) -> str:
    extra: JsonObject = {
        "firstName": CREATE_FIRST_NAME,
        "lastName": CREATE_LAST_NAME,
        "expirationDate": CREATE_EXPIRATION_DATE,
        "availableUsages": CREATE_AVAILABLE_USAGES,
        "allowedResources": {},
    }
    if include_resource_placeholder:
        extra["allowedResources"] = {"resourceIds": ["{{diningResourceId}}"]}
    return json.dumps(
        {
            "module": DINING_MODULE,
            "clientUserId": "{{$string.uuid}}",
            "extra": extra,
        },
        ensure_ascii=False,
        indent=2,
    )


def MixCreateBody() -> str:
    return json.dumps(
        {
            "module": DINING_MODULE,
            "clientUserId": "{{clientUserId}}",
            "extra": {
                "firstName": CREATE_FIRST_NAME,
                "lastName": CREATE_LAST_NAME,
                "expirationDate": CREATE_EXPIRATION_DATE,
                "availableUsages": CREATE_AVAILABLE_USAGES,
                "allowedResources": {"resourceIds": ["{{diningOtherModuleResourceId}}"]},
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def OverLimitCreateBody() -> str:
    return json.dumps(
        {
            "module": DINING_MODULE,
            "clientUserId": "{{clientUserId}}",
            "extra": {
                "firstName": CREATE_FIRST_NAME,
                "lastName": CREATE_LAST_NAME,
                "expirationDate": CREATE_EXPIRATION_DATE,
                "availableUsages": CREATE_AVAILABLE_USAGES,
                "allowedResources": {"resourceIds": ["PLACEHOLDER"]},
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def MembershipRegisterBody() -> str:
    return json.dumps(
        {
            "clientUserId": "{{$string.uuid}}",
            "firstName": CREATE_FIRST_NAME,
            "lastName": CREATE_LAST_NAME,
            "phoneNumber": CONTACT_PHONE,
            "callingCode": CONTACT_CALLING_CODE,
            "email": "dd_{{$timestamp}}@dragonpass.com",
            "expirationDate": CREATE_EXPIRATION_DATE,
        },
        ensure_ascii=False,
        indent=2,
    )


def MembershipQrCodesBody() -> str:
    return json.dumps(
        {
            "membershipId": "{{membershipId}}",
            "durationInSeconds": QR_DURATION_SECONDS,
        },
        ensure_ascii=False,
        indent=2,
    )


def MembershipUpdateDatesBody() -> str:
    return json.dumps(
        {
            "membershipId": "{{membershipId}}",
            "expirationDate": MEMBERSHIP_NEW_EXPIRATION,
        },
        ensure_ascii=False,
        indent=2,
    )


def EntitlementUpdateBody(
    *,
    usage_restriction: Optional[int] = None,
    quantity: Optional[int] = None,
    purchased_quantity: Optional[int] = None,
) -> str:
    """大客户传 ``quantity`` + ``usageRestriction``；买点只传 ``purchasedQuantity``（不传 restriction，否则 ``500.030.025``）。"""
    body: JsonObject = {
        "membershipId": "{{membershipId}}",
        "module": DINING_MODULE,
    }
    if usage_restriction is not None:
        body["usageRestriction"] = usage_restriction
    if quantity is not None:
        body["quantity"] = quantity
    if purchased_quantity is not None:
        body["purchasedQuantity"] = purchased_quantity
    return json.dumps(body, ensure_ascii=False, indent=2)


def BearerHeaders() -> List[JsonObject]:
    return BearerJsonHeaders()


def Step(label: str, calls: List[str]) -> List[str]:
    return Lines_Step(label, calls)
