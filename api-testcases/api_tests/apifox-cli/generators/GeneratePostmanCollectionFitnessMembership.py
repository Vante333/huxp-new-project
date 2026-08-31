"""
生成 fitness Membership **P0 预约冒烟** Postman Collection v2.1 JSON。

对齐 ``api-main-call-chains.md`` Membership Prebooking（fitness）：
注册会籍 → schedule 选槽 → options 可用性 → ``/fitness/memberships/prebooking`` → 详情/列表 → 取消。

鉴权走 membership 数据集（``ProgramID`` / ``clientId`` / ``secret``）。
``prebookingDate`` / ``optionId`` 由 schedule 写入，可用性前置强制改写 body。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionFitnessMembership.py
"""
from __future__ import annotations

import json
from typing import Any, Dict, Final, List

from collection_builder_common import (
    POSTMAN_SCHEMA,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionPath,
    CollectionVariable,
    Folder,
    JsRuntimeIdCaptureHelpersBlock,
    Lines_SeedAuthFromDataset,
    Lines_Step,
    PurposeName,
    RequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, Any]

OUT_NAME: Final[str] = "Fitness-Membership-P0-e2e-core.postman_collection.json"
HELPERS_SOURCE_KEY: Final[str] = "fmHelpersSource"
FITNESS_MODULE: Final[int] = 7
DEFAULT_FITNESS_RESOURCE_ID: Final[str] = "GR0000308"
FITNESS_RESOURCE_ID_VAR: Final[str] = "fitnessResourceId"
FITNESS_SCHEDULE_URL_PATH: Final[str] = (
    "/v2/resources/fitness/{{fitnessResourceId}}/schedule"
    "?startDate={{$date.now|addDays(5)|format('yyyy-MM-dd')}}"
    "&endDate={{$date.now|addDays(10)|format('yyyy-MM-dd')}}"
    "&fallbackAllowed=true"
)
CONTACT_EMAIL: Final[str] = "auto.test@dragonpass.com"
CONTACT_PHONE: Final[str] = "8081966002"
CONTACT_CALLING_CODE: Final[str] = "44"

MEMBERSHIP_REGISTER_PAYLOAD: Final[str] = json.dumps(
    {
        "clientUserId": "{{$string.uuid}}",
        "firstName": "Auto",
        "lastName": "Smith",
        "phoneNumber": CONTACT_PHONE,
        "callingCode": CONTACT_CALLING_CODE,
        "email": "fm_{{$timestamp}}@dragonpass.com",
        "expirationDate": "2028-12-31T23:59:59+00:00",
    },
    ensure_ascii=False,
    indent=2,
)


def _Item(**kwargs: Any) -> JsonObject:
    kwargs.setdefault("js_helpers", BuildFitnessMembershipJsHelpersLines)
    kwargs.setdefault("helpers_source_key", HELPERS_SOURCE_KEY)
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["fmApplyRuntimeIdsToRequestBody();"]
    return RequestItem(**kwargs)


def BuildFitnessMembershipJsHelpersLines() -> List[str]:
    """fitness membership P0 helpers（``fm*``）。Auth 写入 ``fmHelpersSource``，业务步 eval。"""
    runtime_capture = JsRuntimeIdCaptureHelpersBlock(prefix="fm")
    js = runtime_capture + r"""function fmSetVar(key, value) {
  var v = String(value);
  try { pm.variables.set(key, v); } catch (e0) {}
  try { pm.collectionVariables.set(key, v); } catch (e1) {}
  var unsetEnv = {
    fitnessOptionId: 1, prebookingDate: 1, clientUserId: 1,
    membershipId: 1, usageOrderId: 1, prebookingToken: 1
  };
  if (unsetEnv[key]) {
    try { if (pm.environment && typeof pm.environment.unset === 'function') pm.environment.unset(key); } catch (e2) {}
    try { if (pm.globals && typeof pm.globals.unset === 'function') pm.globals.unset(key); } catch (e3) {}
  }
}
function fmUnsetVar(key) {
  try { pm.variables.unset(key); } catch (e0) {}
  try { pm.collectionVariables.unset(key); } catch (e1) {}
}
function fmGetVar(key) {
  var v = '';
  try { if (pm.iterationData) v = String(pm.iterationData.get(key) || '').trim(); } catch (eId) {}
  if (!v || v.indexOf('{{') >= 0) { try { v = String(pm.variables.get(key) || '').trim(); } catch (e0) {} }
  if (!v || v.indexOf('{{') >= 0) { try { v = String(pm.collectionVariables.get(key) || '').trim(); } catch (e1) {} }
  if (!v || v.indexOf('{{') >= 0) return '';
  return v;
}
function fmEnsureResourceId() {
  var v = fmGetVar('fitnessResourceId');
  if (!v) {
    try { v = String((pm.environment && pm.environment.get('fitnessResourceId')) || '').trim(); } catch (eE) {}
  }
  if (v && v.indexOf('{{') < 0) fmSetVar('fitnessResourceId', v);
}
function fmYmdAddDays(days) {
  var d = new Date();
  d.setDate(d.getDate() + days);
  var y = d.getFullYear();
  var m = String(d.getMonth() + 1);
  if (m.length < 2) m = '0' + m;
  var day = String(d.getDate());
  if (day.length < 2) day = '0' + day;
  return y + '-' + m + '-' + day;
}
function fmSlotIsFuture(scheduleDate, startTime) {
  var raw = String(scheduleDate || '') + 'T' + String(startTime || '00:00');
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw)) raw = raw + ':00';
  var t = Date.parse(raw);
  if (isNaN(t)) return true;
  return t > Date.now();
}
function fmApplyScheduleQuery() {
  fmEnsureResourceId();
  var start = fmYmdAddDays(5);
  var end = fmYmdAddDays(10);
  try {
    if (!pm.request || !pm.request.url) return;
    var u = pm.request.url;
    if (u.query && typeof u.query.upsert === 'function') {
      u.query.upsert({ key: 'startDate', value: start });
      u.query.upsert({ key: 'endDate', value: end });
      u.query.upsert({ key: 'fallbackAllowed', value: 'true' });
    } else {
      u.query = [
        { key: 'startDate', value: start },
        { key: 'endDate', value: end },
        { key: 'fallbackAllowed', value: 'true' }
      ];
    }
    console.log('fmApplyScheduleQuery: startDate=' + start + ' endDate=' + end);
  } catch (e) {
    console.warn('fmApplyScheduleQuery:', e);
  }
}
function fmIsBusinessSuccess(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}
function fmGetInnerData(root) {
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) return d;
  return d;
}
function fmAssertHttpBusinessOk(label) {
  pm.test(label + ': 业务成功', function () {
    var root = pm.response.json();
    var ok = fmIsBusinessSuccess(root);
    if (!ok) {
      console.log(label + ': business fail code=' + (root && root.code) + ' errCode=' + (root && root.errCode) + ' msg=' + (root && root.msg));
    }
    pm.expect(ok, (root && (root.errCode || root.msg)) || 'business').to.be.true;
  });
}
function fmParseFitnessSchedule(label) {
  fmAssertHttpBusinessOk(label);
  var data = fmGetInnerData(pm.response.json());
  var picked = null;
  var schedules = (data && data.schedules) || [];
  pm.test(label + ': schedules 非空', function () {
    pm.expect(schedules).to.be.an('array').that.is.not.empty;
  });
  for (var si = 0; si < schedules.length && !picked; si++) {
    var sched = schedules[si];
    if (!sched || !sched.date || !Array.isArray(sched.optionList)) continue;
    var dayTargets = [];
    sched.optionList.forEach(function (opt) {
      if (!opt || !opt.optionId || !opt.startTime) return;
      if (!fmSlotIsFuture(sched.date, opt.startTime)) return;
      dayTargets.push({
        scheduleDate: sched.date,
        optionId: String(opt.optionId),
        startTime: String(opt.startTime),
        optionType: (typeof opt.optionType === 'number') ? opt.optionType : 0
      });
    });
    dayTargets.sort(function (a, b) {
      var pa = (a.optionType === 1) ? 0 : 1;
      var pb = (b.optionType === 1) ? 0 : 1;
      if (pa !== pb) return pa - pb;
      return String(a.optionId).localeCompare(String(b.optionId));
    });
    if (dayTargets.length) picked = dayTargets[0];
  }
  pm.test(label + ': 写入 fitnessOptionId + prebookingDate', function () {
    pm.expect(picked, 'schedule 候选').to.be.an('object');
    var slotDate = picked.scheduleDate + 'T' + picked.startTime;
    fmSetVar('fitnessOptionId', picked.optionId);
    fmSetVar('prebookingDate', slotDate);
    console.log(label + ': schedule 选槽 optionId=' + picked.optionId + ' prebookingDate=' + slotDate);
  });
}
function fmApplyScheduleToRequestBody() {
  fmEnsureResourceId();
  var opt = fmGetVar('fitnessOptionId');
  var pb = fmGetVar('prebookingDate');
  if (!opt) console.warn('fmApplyScheduleToRequestBody: fitnessOptionId 为空（schedule 未写入）');
  if (!pb) console.warn('fmApplyScheduleToRequestBody: prebookingDate 为空（schedule 未写入）');
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    if (opt && body.optionId !== undefined) body.optionId = opt;
    if (pb && body.prebookingDate !== undefined) body.prebookingDate = pb;
    var rid = fmGetVar('fitnessResourceId');
    if (rid && body.resourceId !== undefined) body.resourceId = rid;
    var mid = fmGetVar('membershipId');
    if (mid && body.membershipId !== undefined) body.membershipId = mid;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('fmApplyScheduleToRequestBody: optionId=' + opt + ' prebookingDate=' + pb);
  } catch (e) {
    console.warn('fmApplyScheduleToRequestBody:', e);
  }
}
function fmSaveMembershipId(label) {
  pm.test(label + ': 保存 membershipId + clientUserId', function () {
    var data = fmGetInnerData(pm.response.json());
    fmCaptureClientUserIdAfterSend(data);
    var mid = data && (data.membershipId || data.id);
    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;
    fmSetVar('membershipId', String(mid));
    if (data && data.clientUserId) {
      var saved = fmGetVar('clientUserId');
      pm.expect(saved, '后置已提取 clientUserId').to.be.a('string').and.not.empty;
      pm.expect(fmIsUuid(String(data.clientUserId)), '响应 clientUserId 为 UUID').to.be.true;
      pm.expect(String(data.clientUserId)).to.eql(saved);
    }
  });
}
function fmSaveAvailabilityRequestFields() {
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var reqBody = JSON.parse(String(pm.request.body.raw));
    var adultCount = parseInt(String(reqBody && reqBody.adultCount), 10);
    var childCount = parseInt(String(reqBody && reqBody.childCount), 10);
    if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
    if (isNaN(childCount) || childCount < 0) childCount = 0;
    fmSetVar('fitnessAdultCount', String(adultCount));
    fmSetVar('fitnessChildCount', String(childCount));
  } catch (e) {
    console.warn('fmSaveAvailabilityRequestFields:', e);
  }
}
function fmExpectedBookingCounts() {
  var adultCount = parseInt(String(fmGetVar('fitnessAdultCount') || '1'), 10);
  var childCount = parseInt(String(fmGetVar('fitnessChildCount') || '0'), 10);
  if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
  if (isNaN(childCount) || childCount < 0) childCount = 0;
  if (adultCount + childCount <= 0) {
    adultCount = 1;
    childCount = 0;
  }
  return adultCount + childCount;
}
function fmAssertBookingCounts(label) {
  var env = pm.response.json();
  if (!env || !fmIsBusinessSuccess(env)) return;
  var data = fmGetInnerData(env);
  var extra = (data && data.extra && typeof data.extra === 'object') ? data.extra : {};
  var expected = fmExpectedBookingCounts();
  var actual = extra.bookingCounts;
  pm.test(label + ': extra.bookingCounts | 期望=可用性 adultCount+childCount=' + expected + ' | 实际=' + String(actual), function () {
    pm.expect(Object.prototype.hasOwnProperty.call(extra, 'bookingCounts'), 'extra.bookingCounts 字段存在').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.be.a('number');
    pm.expect(Number.isInteger(actual), 'extra.bookingCounts 为整数').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.eql(expected);
  });
}
function fmAssertAvailabilitySuccess(label) {
  fmSaveAvailabilityRequestFields();
  fmAssertHttpBusinessOk(label);
  pm.test(label + ': 写入 prebookingToken', function () {
    var data = fmGetInnerData(pm.response.json());
    var tok = data && data.prebookingToken;
    pm.expect(tok, 'prebookingToken').to.be.a('string').and.not.empty;
    fmSetVar('prebookingToken', String(tok));
  });
}
function fmApplyPrebookingBody() {
  fmEnsureResourceId();
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    var mid = fmGetVar('membershipId');
    var tok = fmGetVar('prebookingToken');
    if (mid && body.membershipId !== undefined) body.membershipId = mid;
    if (body.extra && typeof body.extra === 'object' && tok) body.extra.prebookingToken = tok;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('fmApplyPrebookingBody: membershipId=' + mid);
  } catch (e) {
    console.warn('fmApplyPrebookingBody:', e);
  }
}
function fmAssertPrebookingSuccess(label) {
  fmAssertHttpBusinessOk(label);
  pm.test(label + ': usage orderId 非空', function () {
    var data = fmGetInnerData(pm.response.json());
    pm.expect(data && data.orderId, 'orderId').to.be.a('string').and.not.empty;
    fmSetVar('usageOrderId', String(data.orderId));
  });
}
function fmAssertDetailsCore(label, cancelled) {
  fmAssertHttpBusinessOk(label);
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {
    var data = fmGetInnerData(pm.response.json());
    pm.expect(data.orderId).to.eql(fmGetVar('usageOrderId'));
  });
  pm.test(label + ': status=' + (cancelled ? '3 CANCELLED' : '1/5 有效'), function () {
    var data = fmGetInnerData(pm.response.json());
    if (cancelled) {
      pm.expect(data.status).to.eql(3);
    } else {
      pm.expect([1, 5], 'status').to.include(data.status);
    }
  });
  fmAssertBookingCounts(label);
}
function fmAssertListContains(label) {
  fmAssertHttpBusinessOk(label);
  pm.test(label + ': 列表含 usageOrderId', function () {
    var data = fmGetInnerData(pm.response.json());
    var items = (data && (data.orders || data.items || data.list || data.records)) || [];
    if (!items.length && data && Array.isArray(data.content)) items = data.content;
    var want = fmGetVar('usageOrderId');
    var hit = items.some(function (it) { return it && String(it.orderId) === want; });
    pm.expect(hit, '列表含 ' + want).to.eql(true);
  });
}
function fmApplyOrderIdBody() {
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    var oid = fmGetVar('usageOrderId');
    var mid = fmGetVar('membershipId');
    if (oid && body.orderId !== undefined) body.orderId = oid;
    if (mid && body.membershipId !== undefined) body.membershipId = mid;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('fmApplyOrderIdBody: orderId=' + oid + ' membershipId=' + mid);
  } catch (e) {
    console.warn('fmApplyOrderIdBody:', e);
  }
}
""".strip()
    return js.split("\n")


def AvailabilityBody() -> str:
    return json.dumps(
        {
            "module": FITNESS_MODULE,
            "resourceId": "{{fitnessResourceId}}",
            "optionId": "{{fitnessOptionId}}",
            "prebookingDate": "{{prebookingDate}}",
            "adultCount": 1,
            "childCount": 0,
            "membershipId": "{{membershipId}}",
        },
        ensure_ascii=False,
        indent=2,
    )


def PrebookingBody() -> str:
    return json.dumps(
        {
            "module": FITNESS_MODULE,
            "membershipId": "{{membershipId}}",
            "extra": {
                "prebookingToken": "{{prebookingToken}}",
                "cashPaymentApplied": False,
                "toUseEntitlementCount": 1,
                "prebookingRequiredInfo": {
                    "firstName": "Auto",
                    "lastName": "Smith",
                    "email": CONTACT_EMAIL,
                    "phoneNumber": CONTACT_PHONE,
                    "callingCode": CONTACT_CALLING_CODE,
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildScenarioDescription() -> str:
    return (
        "由 GeneratePostmanCollectionFitnessMembership.py 生成。\n\n"
        "**范围**：fitness **Membership** P0 预约冒烟（账户轴 membership，品类 fitness）。"
        "ePass 轨见 ``fitness ePass P0 · CLI sync``。\n\n"
        "**链路**：``POST /v2/memberships`` → ``GET …/fitness/{resourceId}/schedule`` → "
        "``POST /v2/resources/options/prebookings/availability`` → "
        "``POST /v2/orders/fitness/memberships/prebooking`` → 详情/列表 → ``PATCH /v2/orders`` 取消。\n\n"
        "**变量**：\n"
        "- 鉴权三列 ``ProgramID`` / ``clientId`` / ``secret``：场景数据集 "
        "「membership数据集合」（``use_data_set_id=3475754``）选行；Auth 种子 "
        "iterationData → Environment → variables，写回四作用域。\n"
        "- ``fitnessResourceId``：Environment（默认 GR0000308）。\n"
        "- ``membershipId``：注册会籍后写入 variables+collection。\n"
        "- ``fitnessOptionId`` / ``prebookingDate``：schedule 选槽写入（variables+collection），"
        "可用性前置 ``fmApplyScheduleToRequestBody`` 强制改写 body；**不**套今天+10 天 T10:00。"
        "GET schedule 前置 ``fmApplyScheduleQuery`` 写本机今天+5～+10（解绑后 query 常丢）；选槽跳过已过点。\n"
        "- ``prebookingToken`` / ``usageOrderId``：可用性 / 下单响应写入。\n"
        "- ``extra.bookingCounts``：仅详情 ``/memberships/details`` 断言，等于可用性 "
        "``adultCount+childCount``（默认 1+0=1；取消后不变）。\n"
        "- 下单 ``extra.cashPaymentApplied=false``、``toUseEntitlementCount=1``；"
        "OAS extra **无** optionId（槽位已绑在可用性 token）。\n\n"
        "**Helpers**：Auth 写入 ``fmHelpersSource``；其它步 eval loader。须先跑 00 Auth。\n"
        "**取消**：``PATCH /v2/orders`` status=3；取消后再查详情 status=3。"
    )


def BuildCollection() -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            _Item(
                name=PurposeName("获取 membership 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken + fmHelpersSource。数据集选 membership 行。",
                save_token=True,
                prerequest_lines=Lines_SeedAuthFromDataset(),
                test_lines=Lines_Step(
                    "Auth",
                    [
                        "fmAssertHttpBusinessOk('Auth');",
                        "pm.test('Auth: accessToken 已写入', function () {",
                        "  pm.expect(fmGetVar('accessToken') || pm.variables.get('accessToken')).to.be.ok;",
                        "});",
                    ],
                ),
            ),
        ],
        description="先执行。鉴权三列来自 membership 数据集选行。",
    )
    prebooking_folder = Folder(
        "P0 · membership 预约",
        [
            Folder(
                "00 前置",
                [
                    _Item(
                        name=PurposeName("注册 membership", "SETUP-MS-S01", "POST", "/memberships"),
                        method="POST",
                        url_path="/v2/memberships",
                        body=MEMBERSHIP_REGISTER_PAYLOAD,
                        headers=BearerJsonHeaders(),
                        description="``POST /v2/memberships`` · 写入 membershipId",
                        prerequest_lines=[
                            "fmUnsetVar('clientUserId');",
                            "fmUnsetVar('membershipId');",
                            "fmUnsetVar('usageOrderId');",
                            "fmUnsetVar('prebookingToken');",
                        ],
                        test_lines=Lines_Step(
                            "SETUP-MS-S01",
                            [
                                "fmAssertHttpBusinessOk('SETUP-MS-S01');",
                                "fmSaveMembershipId('SETUP-MS-S01');",
                            ],
                        ),
                    ),
                ],
                description="注册会籍，后续预约必跑。",
            ),
            Folder(
                "prebooking",
                [
                    _Item(
                        name=PurposeName(
                            "schedule 解析 optionId 与 prebookingDate",
                            "E02-S01",
                            "GET",
                            "/fitness/.../schedule",
                        ),
                        method="GET",
                        url_path=FITNESS_SCHEDULE_URL_PATH,
                        body=None,
                        headers=BearerJsonHeaders(),
                        description="schedule 选槽写入 fitnessOptionId + prebookingDate；前置补 startDate/endDate（解绑后 query 常丢）",
                        prerequest_lines=["fmEnsureResourceId();", "fmApplyScheduleQuery();"],
                        test_lines=Lines_Step("E02-S01", ["fmParseFitnessSchedule('E02-S01');"]),
                    ),
                    _Item(
                        name=PurposeName(
                            "可用性查询并获取 prebookingToken",
                            "E02-S02",
                            "POST",
                            "/options/prebookings/availability",
                        ),
                        method="POST",
                        url_path="/v2/resources/options/prebookings/availability",
                        body=AvailabilityBody(),
                        headers=BearerJsonHeaders(),
                        description="options 可用性 · membershipId + schedule 槽位",
                        prerequest_lines=["fmApplyScheduleToRequestBody();"],
                        test_lines=Lines_Step(
                            "E02-S02",
                            [
                                "fmAssertHttpBusinessOk('E02-S02');",
                                "fmAssertAvailabilitySuccess('E02-S02');",
                            ],
                        ),
                    ),
                    _Item(
                        name=PurposeName(
                            "fitness membership 预约下单",
                            "E02-S03",
                            "POST",
                            "/fitness/memberships/prebooking",
                        ),
                        method="POST",
                        url_path="/v2/orders/fitness/memberships/prebooking",
                        body=PrebookingBody(),
                        headers=BearerJsonHeaders(),
                        description="``cashPaymentApplied=false`` · extra 无 optionId（OAS）",
                        prerequest_lines=["fmApplyPrebookingBody();"],
                        test_lines=Lines_Step(
                            "E02-S03",
                            [
                                "fmAssertHttpBusinessOk('E02-S03');",
                                "fmAssertPrebookingSuccess('E02-S03');",
                            ],
                        ),
                    ),
                    _Item(
                        name=PurposeName("预约后 usage 详情", "E02-S04", "POST", "/memberships/details"),
                        method="POST",
                        url_path="/v2/orders/memberships/details",
                        body=json.dumps({"orderId": "{{usageOrderId}}"}, indent=2),
                        headers=BearerJsonHeaders(),
                        description="取消前详情 status=1/5",
                        prerequest_lines=["fmApplyOrderIdBody();"],
                        test_lines=Lines_Step("E02-S04", ["fmAssertDetailsCore('E02-S04', false);"]),
                    ),
                    _Item(
                        name=PurposeName("预约后订单列表含 usage 单", "E02-S05", "POST", "/memberships"),
                        method="POST",
                        url_path="/v2/orders/memberships",
                        body=json.dumps(
                            {
                                "membershipId": "{{membershipId}}",
                                "module": FITNESS_MODULE,
                                "pageSize": 10,
                                "pageNumber": 1,
                            },
                            indent=2,
                        ),
                        headers=BearerJsonHeaders(),
                        description="列表含 usageOrderId",
                        prerequest_lines=["fmApplyOrderIdBody();"],
                        test_lines=Lines_Step("E02-S05", ["fmAssertListContains('E02-S05');"]),
                    ),
                    _Item(
                        name=PurposeName("取消 usage 单", "E02-S06", "PATCH", "/orders"),
                        method="PATCH",
                        url_path="/v2/orders",
                        body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
                        headers=BearerJsonHeaders(),
                        description="``PATCH /v2/orders`` status=3",
                        prerequest_lines=["fmApplyOrderIdBody();"],
                        test_lines=Lines_Step("E02-S06", ["fmAssertHttpBusinessOk('E02-S06');"]),
                    ),
                    _Item(
                        name=PurposeName("取消后 usage 详情 status=3", "E02-S07", "POST", "/memberships/details"),
                        method="POST",
                        url_path="/v2/orders/memberships/details",
                        body=json.dumps({"orderId": "{{usageOrderId}}"}, indent=2),
                        headers=BearerJsonHeaders(),
                        description="取消后详情 status=3",
                        prerequest_lines=["fmApplyOrderIdBody();"],
                        test_lines=Lines_Step("E02-S07", ["fmAssertDetailsCore('E02-S07', true);"]),
                    ),
                ],
                description="schedule 选槽 → 可用性 → 下单 → 查询 → 取消",
            ),
        ],
        description="P0 冒烟一条预约链。换测：数据集选 membership 行；Environment 填 fitnessResourceId。",
    )
    info: JsonObject = {
        "name": "fitness Membership · P0 预约冒烟",
        "description": BuildScenarioDescription(),
        "schema": POSTMAN_SCHEMA,
    }
    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable(FITNESS_RESOURCE_ID_VAR, DEFAULT_FITNESS_RESOURCE_ID),
        CollectionVariable("fitnessOptionId", ""),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable(
            HELPERS_SOURCE_KEY,
            "",
            "Auth 写入的 helpers 源码；其它步骤 eval。单独跑业务步须先跑 00 Auth。",
        ),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("membershipId", ""),
        CollectionVariable("prebookingToken", ""),
        CollectionVariable("usageOrderId", ""),
    ]
    return {
        "info": info,
        "variable": variables,
        "item": [auth_folder, prebooking_folder],
    }


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection())
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
