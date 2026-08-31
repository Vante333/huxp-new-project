"""
生成 Local Offer Membership **P0 冒烟 / P1 全量** Postman Collection v2.1 JSON。

对齐 ``api-main-call-chains.md`` Membership Prebooking（localOffers）：
注册会籍 → options 可用性 → ``/localOffers/memberships/prebooking`` → 详情/列表 → 取消。

P0：一条可用性（**含** ``membershipId``）正向链。
P1：另加可用性 **不含** ``membershipId`` 的第二条链（与 ePass 双路径约定对齐）。

鉴权走 membership 数据集（``ProgramID`` / ``clientId`` / ``secret``）。
``resourceId`` / ``optionId`` 从 Environment 读取（与 Local Offer ePass 同键）。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionLocalOfferMembership.py
"""
from __future__ import annotations

import json
from typing import Any, Dict, Final, List, Literal

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
    Lines_SyncPrebookingDate,
    PREBOOKING_ADD_DAYS_START,
    PrebookingDateApifoxExpr,
    PurposeName,
    RequestItem as CommonRequestItem,
    WriteCollectionJson,
)

JsonObject = Dict[str, Any]
PriorityKind = Literal["p0", "p1"]

OUT_NAME_P0: Final[str] = "LocalOffer-Membership-P0-e2e-core.postman_collection.json"
OUT_NAME_P1: Final[str] = "LocalOffer-Membership-P1-e2e-core.postman_collection.json"
HELPERS_SOURCE_KEY: Final[str] = "lomHelpersSource"
LOCAL_OFFER_MODULE: Final[int] = 11
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
        "email": "lom_{{$timestamp}}@dragonpass.com",
        "expirationDate": "2028-12-31T23:59:59+00:00",
    },
    ensure_ascii=False,
    indent=2,
)


def _Item(**kwargs: Any) -> JsonObject:
    kwargs.setdefault("js_helpers", BuildLocalOfferMembershipJsHelpersLines)
    kwargs.setdefault("helpers_source_key", HELPERS_SOURCE_KEY)
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["lomApplyRuntimeIdsToRequestBody();"]
    return CommonRequestItem(**kwargs)


def BuildLocalOfferMembershipJsHelpersLines() -> List[str]:
    """Local Offer membership helpers（``lom*``）。Auth 写入 ``lomHelpersSource``，业务步 eval。"""
    runtime_capture = JsRuntimeIdCaptureHelpersBlock(prefix="lom")
    js = runtime_capture + r"""function lomSetVar(key, value) {
  var v = String(value);
  try { pm.variables.set(key, v); } catch (e0) {}
  try { pm.collectionVariables.set(key, v); } catch (e1) {}
  if (key === 'clientUserId' || key === 'membershipId' || key === 'prebookingToken' || key === 'usageOrderId') {
    try { if (pm.environment && typeof pm.environment.unset === 'function') pm.environment.unset(key); } catch (e2) {}
    try { if (pm.globals && typeof pm.globals.unset === 'function') pm.globals.unset(key); } catch (e3) {}
  }
}
function lomUnsetVar(key) {
  try { pm.variables.unset(key); } catch (e0) {}
  try { pm.collectionVariables.unset(key); } catch (e1) {}
}
function lomGetVar(key) {
  var v = '';
  try { if (pm.iterationData) v = String(pm.iterationData.get(key) || '').trim(); } catch (eId) {}
  if (!v || v.indexOf('{{') >= 0) { try { v = String(pm.variables.get(key) || '').trim(); } catch (e0) {} }
  if (!v || v.indexOf('{{') >= 0) { try { v = String(pm.collectionVariables.get(key) || '').trim(); } catch (e1) {} }
  if (!v || v.indexOf('{{') >= 0) { try { v = String((pm.environment && pm.environment.get(key)) || '').trim(); } catch (e2) {} }
  if (!v || v.indexOf('{{') >= 0) return '';
  return v;
}
function lomEnsureOutletIds() {
  var rid = lomGetVar('resourceId');
  var oid = lomGetVar('optionId');
  if (rid && rid.indexOf('{{') < 0) lomSetVar('resourceId', rid);
  if (oid && oid.indexOf('{{') < 0) lomSetVar('optionId', oid);
  if (!rid) console.warn('[lom] resourceId 为空：请在 Environment 填写与 Local Offer ePass 相同的网点');
  if (!oid) console.warn('[lom] optionId 为空：请在 Environment 填写与 Local Offer ePass 相同的 option');
}
function lomIsBusinessSuccess(env) {
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}
function lomGetInnerData(root) {
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) return d;
  return d;
}
function lomAssertHttpBusinessOk(label) {
  pm.test(label + ': 业务成功 | 期望=code 0/1 | 实际=' + (function () {
    try { return String((pm.response.json() || {}).code); } catch (e) { return 'parse-error'; }
  })(), function () {
    var root = pm.response.json();
    var ok = lomIsBusinessSuccess(root);
    if (!ok) {
      console.log(label + ': business fail code=' + (root && root.code) + ' errCode=' + (root && root.errCode) + ' msg=' + (root && root.msg));
    }
    pm.expect(ok, (root && (root.errCode || root.msg)) || 'business').to.be.true;
  });
}
function lomSaveMembershipId(label) {
  pm.test(label + ': 保存 membershipId + clientUserId | 期望=非空 | 实际=响应 data', function () {
    var data = lomGetInnerData(pm.response.json());
    lomCaptureClientUserIdAfterSend(data);
    var mid = data && (data.membershipId || data.id);
    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;
    lomSetVar('membershipId', String(mid));
    if (data && data.clientUserId) {
      var saved = lomGetVar('clientUserId');
      pm.expect(saved, '后置已提取 clientUserId').to.be.a('string').and.not.empty;
      pm.expect(lomIsUuid(String(data.clientUserId)), '响应 clientUserId 为 UUID').to.be.true;
      pm.expect(String(data.clientUserId)).to.eql(saved);
    }
  });
}
function lomSaveAvailabilityRequestFields() {
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var reqBody = JSON.parse(String(pm.request.body.raw));
    var adultCount = parseInt(String(reqBody && reqBody.adultCount), 10);
    var childCount = parseInt(String(reqBody && reqBody.childCount), 10);
    if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
    if (isNaN(childCount) || childCount < 0) childCount = 0;
    lomSetVar('lomAdultCount', String(adultCount));
    lomSetVar('lomChildCount', String(childCount));
  } catch (e) {
    console.warn('lomSaveAvailabilityRequestFields:', e);
  }
}
function lomExpectedBookingCounts() {
  var adultCount = parseInt(String(lomGetVar('lomAdultCount') || '1'), 10);
  var childCount = parseInt(String(lomGetVar('lomChildCount') || '0'), 10);
  if (isNaN(adultCount) || adultCount < 0) adultCount = 1;
  if (isNaN(childCount) || childCount < 0) childCount = 0;
  if (adultCount + childCount <= 0) {
    adultCount = 1;
    childCount = 0;
  }
  return adultCount + childCount;
}
function lomAssertBookingCounts(label) {
  var env = pm.response.json();
  if (!env || !lomIsBusinessSuccess(env)) return;
  var data = lomGetInnerData(env);
  var extra = (data && data.extra && typeof data.extra === 'object') ? data.extra : {};
  var expected = lomExpectedBookingCounts();
  var actual = extra.bookingCounts;
  pm.test(label + ': extra.bookingCounts | 期望=可用性 adultCount+childCount=' + expected + ' | 实际=' + String(actual), function () {
    pm.expect(Object.prototype.hasOwnProperty.call(extra, 'bookingCounts'), 'extra.bookingCounts 字段存在').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.be.a('number');
    pm.expect(Number.isInteger(actual), 'extra.bookingCounts 为整数').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.eql(expected);
  });
}
function lomApplyAvailabilityBody(withMembership) {
  lomEnsureOutletIds();
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    var rid = lomGetVar('resourceId');
    var oid = lomGetVar('optionId');
    var mid = lomGetVar('membershipId');
    if (rid) body.resourceId = rid;
    if (oid) body.optionId = oid;
    if (withMembership) {
      if (mid) body.membershipId = mid;
    } else if (body.membershipId !== undefined) {
      delete body.membershipId;
    }
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('lomApplyAvailabilityBody: resourceId=' + rid + ' optionId=' + oid + ' membershipId=' + (withMembership ? mid : '(omit)'));
  } catch (e) {
    console.warn('lomApplyAvailabilityBody:', e);
  }
}
function lomAssertAvailabilitySuccess(label) {
  lomSaveAvailabilityRequestFields();
  lomAssertHttpBusinessOk(label);
  pm.test(label + ': 写入 prebookingToken | 期望=非空 | 实际=响应 data', function () {
    var data = lomGetInnerData(pm.response.json());
    var tok = data && data.prebookingToken;
    pm.expect(tok, 'prebookingToken').to.be.a('string').and.not.empty;
    lomSetVar('prebookingToken', String(tok));
  });
}
function lomApplyPrebookingBody() {
  lomEnsureOutletIds();
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    var mid = lomGetVar('membershipId');
    var tok = lomGetVar('prebookingToken');
    if (mid && body.membershipId !== undefined) body.membershipId = mid;
    if (body.extra && typeof body.extra === 'object' && tok) body.extra.prebookingToken = tok;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('lomApplyPrebookingBody: membershipId=' + mid);
  } catch (e) {
    console.warn('lomApplyPrebookingBody:', e);
  }
}
function lomAssertPrebookingSuccess(label) {
  lomAssertHttpBusinessOk(label);
  pm.test(label + ': usage orderId 非空 | 期望=非空 | 实际=响应 data.orderId', function () {
    var data = lomGetInnerData(pm.response.json());
    pm.expect(data && data.orderId, 'orderId').to.be.a('string').and.not.empty;
    lomSetVar('usageOrderId', String(data.orderId));
  });
  pm.test(label + ': module=11 | 期望=11 | 实际=响应 data.module', function () {
    var data = lomGetInnerData(pm.response.json());
    pm.expect(data && data.module, 'module').to.eql(11);
  });
}
function lomAssertDetailsCore(label, cancelled) {
  lomAssertHttpBusinessOk(label);
  pm.test(label + ': orderId 与 usageOrderId 一致 | 期望=' + lomGetVar('usageOrderId') + ' | 实际=响应', function () {
    var data = lomGetInnerData(pm.response.json());
    pm.expect(data.orderId).to.eql(lomGetVar('usageOrderId'));
  });
  pm.test(label + ': status | 期望=' + (cancelled ? '3' : '1/5') + ' | 实际=响应 data.status', function () {
    var data = lomGetInnerData(pm.response.json());
    if (cancelled) {
      pm.expect(data.status).to.eql(3);
    } else {
      pm.expect([1, 5], 'status').to.include(data.status);
    }
  });
  lomAssertBookingCounts(label);
}
function lomAssertListContains(label) {
  lomAssertHttpBusinessOk(label);
  pm.test(label + ': 列表含 usageOrderId | 期望=' + lomGetVar('usageOrderId') + ' | 实际=data.orders', function () {
    var data = lomGetInnerData(pm.response.json());
    var items = (data && (data.orders || data.items || data.list || data.records)) || [];
    if (!items.length && data && Array.isArray(data.content)) items = data.content;
    var want = lomGetVar('usageOrderId');
    var hit = items.some(function (it) { return it && String(it.orderId) === want; });
    pm.expect(hit, '列表含 ' + want).to.eql(true);
  });
}
function lomApplyOrderIdBody() {
  try {
    if (!pm.request || !pm.request.body || !pm.request.body.raw) return;
    var body = JSON.parse(String(pm.request.body.raw));
    var oid = lomGetVar('usageOrderId');
    var mid = lomGetVar('membershipId');
    if (oid && body.orderId !== undefined) body.orderId = oid;
    if (mid && body.membershipId !== undefined) body.membershipId = mid;
    pm.request.body.raw = JSON.stringify(body, null, 2);
    console.log('lomApplyOrderIdBody: orderId=' + oid + ' membershipId=' + mid);
  } catch (e) {
    console.warn('lomApplyOrderIdBody:', e);
  }
}
""".strip()
    return js.split("\n")


def AvailabilityBody(*, with_membership: bool, add_days: int) -> str:
    body: JsonObject = {
        "module": LOCAL_OFFER_MODULE,
        "resourceId": "{{resourceId}}",
        "optionId": "{{optionId}}",
        "prebookingDate": PrebookingDateApifoxExpr(add_days),
        "adultCount": 1,
        "childCount": 0,
    }
    if with_membership:
        body["membershipId"] = "{{membershipId}}"
    return json.dumps(body, ensure_ascii=False, indent=2)


def PrebookingBody() -> str:
    return json.dumps(
        {
            "module": LOCAL_OFFER_MODULE,
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
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def OrdersListBody() -> str:
    return json.dumps(
        {
            "membershipId": "{{membershipId}}",
            "module": LOCAL_OFFER_MODULE,
            "pageSize": 10,
            "pageNumber": 1,
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildRegisterStep(step_id: str) -> JsonObject:
    return _Item(
        name=PurposeName("注册 membership", step_id, "POST", "/memberships"),
        method="POST",
        url_path="/v2/memberships",
        body=MEMBERSHIP_REGISTER_PAYLOAD,
        headers=BearerJsonHeaders(),
        description="``POST /v2/memberships`` · 写入 membershipId。每条预约链前重注册，避免权益耗尽。",
        prerequest_lines=[
            "lomUnsetVar('clientUserId');",
            "lomUnsetVar('membershipId');",
            "lomUnsetVar('usageOrderId');",
            "lomUnsetVar('prebookingToken');",
        ],
        test_lines=Lines_Step(
            step_id,
            [
                "lomAssertHttpBusinessOk('" + step_id + "');",
                "lomSaveMembershipId('" + step_id + "');",
            ],
        ),
    )


def BuildPrebookingChain(
    *,
    prefix: str,
    with_membership: bool,
    add_days: int,
) -> List[JsonObject]:
    """一条可用性 → 下单 → 详情/列表 → 取消链。"""
    avail_label = prefix + "-S01"
    book_label = prefix + "-S02"
    detail_label = prefix + "-S03"
    list_label = prefix + "-S04"
    cancel_label = prefix + "-S05"
    after_label = prefix + "-S06"
    avail_purpose = (
        "可用性查询（含 membershipId）" if with_membership else "可用性查询（不含 membershipId）"
    )
    return [
        _Item(
            name=PurposeName(avail_purpose, avail_label, "POST", "/options/prebookings/availability"),
            method="POST",
            url_path="/v2/resources/options/prebookings/availability",
            body=AvailabilityBody(with_membership=with_membership, add_days=add_days),
            headers=BearerJsonHeaders(),
            description="options 可用性 · Local Offer module=11；"
            + ("body 含 membershipId" if with_membership else "body 不含 membershipId"),
            prerequest_lines=[
                *Lines_SyncPrebookingDate(add_days),
                "lomApplyAvailabilityBody(" + ("true" if with_membership else "false") + ");",
            ],
            test_lines=Lines_Step(
                avail_label,
                ["lomAssertAvailabilitySuccess('" + avail_label + "');"],
            ),
        ),
        _Item(
            name=PurposeName(
                "Local Offer membership 预约下单",
                book_label,
                "POST",
                "/localOffers/memberships/prebooking",
            ),
            method="POST",
            url_path="/v2/orders/localOffers/memberships/prebooking",
            body=PrebookingBody(),
            headers=BearerJsonHeaders(),
            description="``cashPaymentApplied=false`` · ``toUseEntitlementCount=1`` · 业务 body 不含 clientId/secret",
            prerequest_lines=["lomApplyPrebookingBody();"],
            test_lines=Lines_Step(
                book_label,
                ["lomAssertPrebookingSuccess('" + book_label + "');"],
            ),
        ),
        _Item(
            name=PurposeName("预约后 usage 详情", detail_label, "POST", "/memberships/details"),
            method="POST",
            url_path="/v2/orders/memberships/details",
            body=json.dumps({"orderId": "{{usageOrderId}}"}, indent=2),
            headers=BearerJsonHeaders(),
            description="取消前详情 status=1/5；``extra.bookingCounts`` = 可用性 adult+child",
            prerequest_lines=["lomApplyOrderIdBody();"],
            test_lines=Lines_Step(detail_label, ["lomAssertDetailsCore('" + detail_label + "', false);"]),
        ),
        _Item(
            name=PurposeName("预约后订单列表含 usage 单", list_label, "POST", "/memberships"),
            method="POST",
            url_path="/v2/orders/memberships",
            body=OrdersListBody(),
            headers=BearerJsonHeaders(),
            description="列表看 ``data.orders``（不是 items）",
            prerequest_lines=["lomApplyOrderIdBody();"],
            test_lines=Lines_Step(list_label, ["lomAssertListContains('" + list_label + "');"]),
        ),
        _Item(
            name=PurposeName("取消 usage 单", cancel_label, "PATCH", "/orders"),
            method="PATCH",
            url_path="/v2/orders",
            body=json.dumps({"status": 3, "orderId": "{{usageOrderId}}"}, indent=2),
            headers=BearerJsonHeaders(),
            description="``PATCH /v2/orders`` status=3",
            prerequest_lines=["lomApplyOrderIdBody();"],
            test_lines=Lines_Step(cancel_label, ["lomAssertHttpBusinessOk('" + cancel_label + "');"]),
        ),
        _Item(
            name=PurposeName("取消后 usage 详情 status=3", after_label, "POST", "/memberships/details"),
            method="POST",
            url_path="/v2/orders/memberships/details",
            body=json.dumps({"orderId": "{{usageOrderId}}"}, indent=2),
            headers=BearerJsonHeaders(),
            description="取消后详情 status=3；bookingCounts 仍为原始人数",
            prerequest_lines=["lomApplyOrderIdBody();"],
            test_lines=Lines_Step(after_label, ["lomAssertDetailsCore('" + after_label + "', true);"]),
        ),
    ]


def BuildScenarioDescription(priority: PriorityKind) -> str:
    title = "P0 冒烟" if priority == "p0" else "P1 全量（双可用性路径）"
    extra_p1 = ""
    if priority == "p1":
        extra_p1 = (
            "P1 另含路径 B：可用性 **不含** ``membershipId``，再用同一会籍下单"
            "（``prebookingDate`` +11 天 T10:00）。每条链前重注册会籍。\n\n"
        )
    return (
        "由 GeneratePostmanCollectionLocalOfferMembership.py 生成。\n\n"
        "**范围**：Local Offer **Membership** "
        + title
        + "（账户轴 membership，品类 localOffers / module=11）。"
        "ePass 轨见 ``Local Offer ePass P0/P1 · CLI sync``。\n\n"
        "**链路**：``POST /v2/memberships`` → "
        "``POST /v2/resources/options/prebookings/availability`` → "
        "``POST /v2/orders/localOffers/memberships/prebooking`` → "
        "``POST /v2/orders/memberships/details`` → ``POST /v2/orders/memberships`` → "
        "``PATCH /v2/orders`` 取消 → 再查详情。\n\n"
        + extra_p1
        + "**变量**：\n"
        "- 鉴权三列 ``ProgramID`` / ``clientId`` / ``secret``：场景数据集 "
        "「membership数据集合」（``use_data_set_id=3475754``）选行；Auth 种子 "
        "iterationData → Environment → variables，写回四作用域。\n"
        "- ``resourceId`` / ``optionId``：Environment（与 Local Offer ePass 同键，集合不预置字面量）。\n"
        "- ``membershipId``：注册会籍后写入 variables+collection。\n"
        "- ``prebookingToken`` / ``usageOrderId``：可用性 / 下单响应写入。\n"
        "- ``prebookingDate``：每次本机今天+"
        + str(PREBOOKING_ADD_DAYS_START)
        + " 天 T10:00（路径 B +11）；前置 ``Lines_SyncPrebookingDate`` 强制改写 body，禁止沿用 Environment 旧值。\n"
        "- ``extra.bookingCounts``：详情/取消后详情等于可用性 ``adultCount+childCount``"
        "（默认 1+0=1；取消后不变）。下单响应常无此字段，不硬断言。\n"
        "- 下单 ``extra.cashPaymentApplied=false``、``toUseEntitlementCount=1``；"
        "业务 body **不传** clientId/secret。\n\n"
        "**Helpers**：Auth 写入 ``lomHelpersSource``；其它步 eval loader。须先跑 00 Auth。\n"
        "**取消**：``PATCH /v2/orders`` status=3；取消后再查详情 status=3。"
    )


def BuildCollection(priority: PriorityKind) -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            _Item(
                name=PurposeName("获取 membership 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken + lomHelpersSource。数据集选 membership 行。",
                save_token=True,
                prerequest_lines=Lines_SeedAuthFromDataset(),
                test_lines=Lines_Step(
                    "Auth",
                    [
                        "lomAssertHttpBusinessOk('Auth');",
                        "pm.test('Auth: accessToken 已写入 | 期望=非空 | 实际=四作用域', function () {",
                        "  pm.expect(lomGetVar('accessToken') || pm.variables.get('accessToken')).to.be.ok;",
                        "});",
                    ],
                ),
            ),
        ],
        description="先执行。鉴权三列来自 membership 数据集选行。",
    )
    path_a = Folder(
        "prebooking · 有 membershipId",
        [
            BuildRegisterStep("SETUP-MS-S01"),
            *BuildPrebookingChain(
                prefix="E02A",
                with_membership=True,
                add_days=PREBOOKING_ADD_DAYS_START,
            ),
        ],
        description="路径 A：可用性 body 含 membershipId。",
    )
    folders: List[JsonObject] = [
        auth_folder,
        Folder(
            "P0 · membership 预约" if priority == "p0" else "P1 · membership 预约",
            [path_a]
            if priority == "p0"
            else [
                path_a,
                Folder(
                    "prebooking · 无 membershipId",
                    [
                        BuildRegisterStep("SETUP-MS-S02"),
                        *BuildPrebookingChain(
                            prefix="E02B",
                            with_membership=False,
                            add_days=PREBOOKING_ADD_DAYS_START + 1,
                        ),
                    ],
                    description="路径 B：可用性 body 不含 membershipId，下单仍绑 membershipId。",
                ),
            ],
            description="换测：数据集选 membership 行；Environment 填 resourceId / optionId。",
        ),
    ]
    display = (
        "Local Offer Membership · P0 预约冒烟"
        if priority == "p0"
        else "Local Offer Membership · P1 预约全量"
    )
    info: JsonObject = {
        "name": display,
        "description": BuildScenarioDescription(priority),
        "schema": POSTMAN_SCHEMA,
    }
    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", ""),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("resourceId", ""),
        CollectionVariable("optionId", ""),
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
        "item": folders,
    }


def Main() -> None:
    p0_path = str(CollectionPath(OUT_NAME_P0))
    p1_path = str(CollectionPath(OUT_NAME_P1))
    WriteCollectionJson(p0_path, BuildCollection("p0"))
    WriteCollectionJson(p1_path, BuildCollection("p1"))
    print(f"Wrote {p0_path}")
    print(f"Wrote {p1_path}")


if __name__ == "__main__":
    Main()
