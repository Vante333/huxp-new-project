"""
生成 PAPI-2839 · FT 联系人/乘客姓名正则 Postman Collection v2.1 JSON。

对齐 ``testcases/2026Q2SP4/PAPI-2839-修复FT联系人firstName-lastName正则-测试分析-001.md`` 与
``.cursor/rules/fasttrack-epass-prebooking-patterns.mdc``：

- 可用性 ``ftSaveAvailabilityRequestFields`` → ``fastTrackAdultCount`` / ``fastTrackChildCount``
- 下单 body **按用例静态生成场景数据**；Pre-request 仅 ``p39SyncPrebookingPassengersOnly`` + ``p39ApplyNameOverrides``（不覆盖 ``prebookingRequiredInfo`` 到默认 Auto）
- 正向 Tests ``ftAssertPrebookingPassengersShape``；不断言 ``extra.lastName``/``availableUsages`` 与入参一致、``usedUsages=1``
- ``prebookingRequiredInfo`` / ``passengers[]`` 姓名正则 ``^[A-Za-z ]+$``

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionPapi2839.py

一次写出 ePass / membership 两套 Collection（便于分别挂 ``epass`` / ``membership`` P1-prebooking）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Literal, Optional, Sequence, Tuple

from collection_builder_common import (
    CollectionPath,
    POSTMAN_SCHEMA,
    AuthJsonHeaders,
    BearerJsonHeaders,
    CollectionVariable,
    Folder,
    Lines_Step,
    PREBOOKING_ADD_DAYS_START,
    PrebookingDateApifoxExpr,
    PurposeName,
    RequestItem as CommonRequestItem,
    WriteCollectionJson,
)
from fasttrack_prebooking_common import (
    AvailabilityBody,
    BuildCancelWithRetryBlock,
    BuildFastTrackJsHelpersLines,
    CREATE_AVAILABLE_USAGES,
    CREATE_EXPIRATION_DATE,
    DEFAULT_FASTTRACK_ADULT_COUNT,
    DEFAULT_FASTTRACK_CHILD_COUNT,
    DEFAULT_FASTTRACK_RESOURCE_ID,
    EPASS_MODULE_DEFAULT,
    FASTTRACK_RESOURCE_ID_VAR,
    FastTrackPrebookingExtraDict,
    Lines_Auth,
    Prerequest_InitFastTrackPassengerCounts,
    Prerequest_NewClientUserId,
    Prerequest_SyncPrebookingDateFromApifox,
)

JsonObject = Dict[str, Any]
HELPERS_SOURCE_KEY: Final[str] = "p2839HelpersSource"


def RequestItem(**kwargs: Any) -> JsonObject:
    """PAPI-2839：Auth 写入 ``p2839HelpersSource``，其它步 eval loader。"""
    kwargs.setdefault("helpers_source_key", HELPERS_SOURCE_KEY)
    return CommonRequestItem(**kwargs)
CaseKind = Literal["prebooking_info", "passengers"]
OrderApiKind = Literal["epass_prebooking", "bundle", "membership_prebooking"]

TrackKind = Literal["epass", "membership"]

OUT_NAME_EPASS: Final[str] = "PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json"
OUT_NAME_MEMBERSHIP: Final[str] = "PAPI-2839-FastTrack-NameRegex-P1-Membership.postman_collection.json"
PREBOOKING_DATE_APIFOX: Final[str] = PrebookingDateApifoxExpr(PREBOOKING_ADD_DAYS_START)

CONTACT_EMAIL: Final[str] = "auto.test@dragonpass.com"
CONTACT_PHONE: Final[str] = "8081966002"
CONTACT_CALLING_CODE: Final[str] = "44"

NAME_REGEX_JS: Final[str] = r"^[A-Za-z ]+$"

MEMBERSHIP_REGISTER_PAYLOAD: Final[str] = json.dumps(
    {
        "clientUserId": "{{$string.uuid}}",
        "firstName": "Auto",
        "lastName": "Smith",
        "phoneNumber": CONTACT_PHONE,
        "callingCode": CONTACT_CALLING_CODE,
        "email": "p2839_{{$timestamp}}@dragonpass.com",
        "expirationDate": "2027-12-31T10:10:33+00:00",
    },
    ensure_ascii=False,
    indent=2,
)

CREATE_EPASS_PAYLOAD: Final[str] = json.dumps(
    {
        "module": EPASS_MODULE_DEFAULT,
        "clientUserId": "{{$string.uuid}}",
        "extra": {
            "firstName": "Auto",
            "lastName": "Smith",
            "expirationDate": CREATE_EXPIRATION_DATE,
            "availableUsages": CREATE_AVAILABLE_USAGES,
            "allowedResources": {"resourceIds": [], "iata": [], "countryOrRegion": []},
        },
    },
    ensure_ascii=False,
    indent=2,
)


@dataclass(frozen=True)
class NameFieldSpec:
    """姓名正则用例；下单 body 在 Python 侧按场景写入，Pre-request 仅同步 passengers 人数。"""

    purpose: str
    step_key: str
    expect_reject: bool
    case_kind: CaseKind
    prebooking_first_name: str = "DragonPass"
    prebooking_last_name: str = "DragonPass"
    passenger_overrides: Tuple[Tuple[int, str, str], ...] = ()


PREBOOKING_INFO_CASES: Final[Tuple[NameFieldSpec, ...]] = (
    NameFieldSpec("合法纯字母 DragonPass", "OK01", False, "prebooking_info"),
    NameFieldSpec(
        "合法含内部空格",
        "OK02",
        False,
        "prebooking_info",
        "John Smith",
        "Mary Jane",
    ),
    NameFieldSpec("firstName 含数字 John123", "NG01", True, "prebooking_info", "John123", "Smith"),
    NameFieldSpec("lastName 含连字符 Jean-Pierre", "NG02", True, "prebooking_info", "John", "Jean-Pierre"),
    NameFieldSpec("lastName 含撇号 O'Brien", "NG03", True, "prebooking_info", "John", "O'Brien"),
    NameFieldSpec("firstName 含中文 李明", "NG04", True, "prebooking_info", "李明", "Smith"),
    NameFieldSpec("lastName 含特殊符号 Test@", "NG05", True, "prebooking_info", "John", "Test@"),
)

PASSENGERS_CASES: Final[Tuple[NameFieldSpec, ...]] = (
    NameFieldSpec("passengers 合法纯字母", "OK01", False, "passengers"),
    NameFieldSpec(
        "passengers 含内部空格",
        "OK02",
        False,
        "passengers",
        passenger_overrides=((0, "John Smith", "Mary Jane"),),
    ),
    NameFieldSpec(
        "passengers[0].firstName 含数字 Bad123",
        "NG01",
        True,
        "passengers",
        passenger_overrides=((0, "Bad123", "Smith"),),
    ),
    NameFieldSpec(
        "passengers[0].lastName 含连字符 Jean-Pierre",
        "NG02",
        True,
        "passengers",
        passenger_overrides=((0, "John", "Jean-Pierre"),),
    ),
    NameFieldSpec(
        "passengers[1].firstName 含数字 Bad123",
        "NG03",
        True,
        "passengers",
        passenger_overrides=((1, "Bad123", "Jones"),),
    ),
)


def NameSpecToJsLiteral(spec: NameFieldSpec) -> str:
    payload: JsonObject = {
        "caseKind": spec.case_kind,
        "expectReject": spec.expect_reject,
        "prebookingFirstName": spec.prebooking_first_name,
        "prebookingLastName": spec.prebooking_last_name,
        "passengerOverrides": [
            {"index": index, "firstName": first_name, "lastName": last_name}
            for index, first_name, last_name in spec.passenger_overrides
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def ApplyNameSpecToExtra(spec: NameFieldSpec, extra: JsonObject) -> JsonObject:
    """按用例写入 ``prebookingRequiredInfo`` / ``passengers``；合法 prebooking_info 同步 lead 姓名（``500.051.017``）。"""
    info_obj = extra.get("prebookingRequiredInfo")
    passengers_obj = extra.get("passengers")
    if not isinstance(info_obj, dict) or not isinstance(passengers_obj, list) or not passengers_obj:
        return extra

    if spec.case_kind == "prebooking_info":
        info_obj["firstName"] = spec.prebooking_first_name
        info_obj["lastName"] = spec.prebooking_last_name
        if not spec.expect_reject:
            lead = passengers_obj[0]
            if isinstance(lead, dict):
                lead["firstName"] = spec.prebooking_first_name
                lead["lastName"] = spec.prebooking_last_name
    elif spec.case_kind == "passengers":
        for index, first_name, last_name in spec.passenger_overrides:
            if 0 <= index < len(passengers_obj):
                passenger = passengers_obj[index]
                if isinstance(passenger, dict):
                    passenger["firstName"] = first_name
                    passenger["lastName"] = last_name
        lead_passenger: Optional[JsonObject] = None
        for passenger in passengers_obj:
            if isinstance(passenger, dict) and passenger.get("leadPassenger") is True:
                lead_passenger = passenger
                break
        if lead_passenger is None and isinstance(passengers_obj[0], dict):
            lead_passenger = passengers_obj[0]
        if lead_passenger is not None:
            info_obj["firstName"] = str(lead_passenger["firstName"])
            info_obj["lastName"] = str(lead_passenger["lastName"])
    return extra


def BuildOrderBodyForSpec(spec: NameFieldSpec, *, api_kind: str) -> str:
    """与 P0 同构；``extra`` 按 ``NameFieldSpec`` 写入场景姓名。"""
    extra = ApplyNameSpecToExtra(
        spec,
        FastTrackPrebookingExtraDict(
            adult_count=DEFAULT_FASTTRACK_ADULT_COUNT,
            child_count=DEFAULT_FASTTRACK_CHILD_COUNT,
            include_transport_number=True,
        ),
    )
    payload: JsonObject
    if api_kind == "epass_prebooking":
        payload = {
            "module": EPASS_MODULE_DEFAULT,
            "ePassId": "{{ePassId}}",
            "extra": extra,
            "async": False,
        }
    elif api_kind == "bundle":
        payload = {
            "module": EPASS_MODULE_DEFAULT,
            "clientUserId": "{{$string.uuid}}",
            "extra": extra,
            "async": False,
        }
    else:
        payload = {
            "module": EPASS_MODULE_DEFAULT,
            "membershipId": "{{membershipId}}",
            "extra": {
                **extra,
                "cashPaymentApplied": False,
                "toUseEntitlementCount": DEFAULT_FASTTRACK_ADULT_COUNT,
                "toUseEntitlementDetail": {"cardholder": 1, "guest": 1},
            },
            "async": False,
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def BuildP2839ExtraJsHelpersLines() -> List[str]:
    js = rf"""function p39EnvFirst() {{
  for (var i = 0; i < arguments.length; i++) {{
    var v = pm.variables.get(arguments[i]);
    if (v === undefined || v === null) continue;
    v = String(v).trim();
    if (v && v.indexOf('{{{{') < 0) return v;
  }}
  return '';
}}
function p39SyncCredentialVarsFromEnv() {{
  ['baseUrl', 'ProgramID', 'clientId', 'secret', 'x-version'].forEach(function (key) {{
    var _id = ''; try {{ if (pm.iterationData) _id = String(pm.iterationData.get(key) || '').trim(); }} catch (eI) {{}}
    var _e = ''; try {{ _e = String((pm.environment && pm.environment.get(key)) || '').trim(); }} catch (eE) {{}}
    var _v = p39EnvFirst(key);
    var _c = ''; try {{ _c = String(pm.collectionVariables.get(key) || '').trim(); }} catch (eC) {{}}
    var v = _id || _e || _v || _c;
    if (!v || v.indexOf('{{') >= 0) return;
    try {{ pm.variables.set(key, v); }} catch (e1) {{}}
    try {{ pm.collectionVariables.set(key, v); }} catch (e2) {{}}
    try {{ if (pm.environment) pm.environment.set(key, v); }} catch (e3) {{}}
    try {{ if (pm.globals && typeof pm.globals.set === 'function') pm.globals.set(key, v); }} catch (e4) {{}}
  }});
}}
function p39SyncFastTrackResourceIdFromEnv() {{
  var rid = p39EnvFirst('fastTrackResourceId');
  if (rid) pm.collectionVariables.set('fastTrackResourceId', rid);
}}
function p39SyncPrebookingPassengersOnly() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var body = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (!body.extra || typeof body.extra !== 'object') body.extra = {{}};
    var counts = ftResolveFastTrackPassengerCounts();
    body.extra.passengers = ftBuildFastTrackPassengers(counts.adultCount, counts.childCount);
    pm.request.body.raw = JSON.stringify(body, null, 2);
  }} catch (e) {{
    console.warn('p39SyncPrebookingPassengersOnly:', e);
    throw e;
  }}
}}
function p39ApplyNameOverrides(cfg) {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var body = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (!body.extra || typeof body.extra !== 'object') body.extra = {{}};
    var extra = body.extra;
    if (!extra.prebookingRequiredInfo || typeof extra.prebookingRequiredInfo !== 'object') {{
      extra.prebookingRequiredInfo = {{}};
    }}
    var info = extra.prebookingRequiredInfo;
    if (cfg.caseKind === 'prebooking_info') {{
      info.firstName = cfg.prebookingFirstName;
      info.lastName = cfg.prebookingLastName;
      if (!cfg.expectReject && extra.passengers && extra.passengers.length) {{
        extra.passengers[0].firstName = cfg.prebookingFirstName;
        extra.passengers[0].lastName = cfg.prebookingLastName;
      }}
    }} else if (cfg.caseKind === 'passengers') {{
      (cfg.passengerOverrides || []).forEach(function (o) {{
        if (extra.passengers && extra.passengers[o.index]) {{
          if (o.firstName) extra.passengers[o.index].firstName = o.firstName;
          if (o.lastName) extra.passengers[o.index].lastName = o.lastName;
        }}
      }});
      var lead = ftResolveLeadPassenger(extra.passengers || []);
      if (lead) {{
        info.firstName = lead.firstName;
        info.lastName = lead.lastName;
      }}
    }}
    pm.request.body.raw = JSON.stringify(body, null, 2);
  }} catch (e) {{
    console.warn('p39ApplyNameOverrides:', e);
    throw e;
  }}
}}
function p39AssertNameRegexRejected(label) {{
  pm.test(label + ': 姓名正则拒绝 code=-1', function () {{
    var env = pm.response.json();
    pm.expect(env.code).to.eql(-1);
    pm.expect(env.msg, 'msg 非空').to.be.a('string').and.not.empty;
  }});
}}
function p39SaveMembershipId(label) {{
  pm.test(label + ': 保存 membershipId', function () {{
    var data = ftGetInnerData(pm.response.json());
    var mid = data.membershipId || data.id;
    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;
    pm.collectionVariables.set('membershipId', String(mid));
  }});
}}
function p39AssertMembershipPrebookingSuccess(label) {{
  ftAssertHttpBusinessOk(label);
  pm.test(label + ': usage orderId 非空', function () {{
    var data = ftGetInnerData(pm.response.json());
    pm.expect(data.orderId).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }});
}}
"""
    return js.splitlines()


def _JsHelpers() -> List[str]:
    return [
        *BuildFastTrackJsHelpersLines(
            assert_epass_status=False,
            assert_create_extra_last_name=False,
            assert_create_extra_available_usages=False,
            assert_usage_used_usages_one=False,
            assert_booking_counts=False,
        ),
        *BuildP2839ExtraJsHelpersLines(),
    ]


def Prerequest_Auth() -> List[str]:
    return ["p39SyncCredentialVarsFromEnv();"]


def Prerequest_SetupAvailability(*, add_days: int = PREBOOKING_ADD_DAYS_START) -> List[str]:
    return [
        "p39SyncCredentialVarsFromEnv();",
        "p39SyncFastTrackResourceIdFromEnv();",
        *Prerequest_SyncPrebookingDateFromApifox(add_days),
    ]


def Prerequest_OrderNameSpec(spec: NameFieldSpec) -> List[str]:
    cfg = NameSpecToJsLiteral(spec)
    return [
        "p39SyncPrebookingPassengersOnly();",
        f"p39ApplyNameOverrides({cfg});",
    ]


def _PositiveSuccessAssert(api_kind: str, step_id: str) -> str:
    if api_kind == "epass_prebooking":
        return f"ftAssertPrebookingOrderSuccess('{step_id}');"
    if api_kind == "bundle":
        return f"ftAssertBundleOrderSuccess('{step_id}');"
    return f"p39AssertMembershipPrebookingSuccess('{step_id}');"


def _OrderTestLines(step_id: str, *, expect_reject: bool, api_kind: str) -> List[str]:
    if expect_reject:
        return Lines_Step(step_id, [f"p39AssertNameRegexRejected('{step_id}');"])
    return Lines_Step(
        step_id,
        [
            f"ftAssertPrebookingPassengersShape('{step_id}');",
            f"ftAssertHttpBusinessOk('{step_id}');",
            _PositiveSuccessAssert(api_kind, step_id),
        ],
    )


def _CancelRetryKw() -> Dict[str, Any]:
    """FT 预订单刚创建时常 ``500.051.029``；单步 HTTP + ``sendRequest`` 轮询取消。"""
    return {
        "helpers_source_key": HELPERS_SOURCE_KEY,
        "max_attempts": 3,
        "cancel_fn": "ftCancelOrderAttemptWithPoll",
    }


def _BuildCancelItemsAfterSuccessOrder(*, step_id: str, api_kind: str) -> List[JsonObject]:
    """正向下单成功后 ``PATCH /v2/orders`` 取消 usage。

    Bundle 响应 ``orderId`` 即 usage，``purchaseOrderId`` 未写入（P0 靠 search-by-ePassId 才补）；
    本正则场景不另开 search，故不发空 ``purchaseOrderId`` 取消。
    """
    del api_kind
    return list(
        BuildCancelWithRetryBlock(
            purpose="取消 usage 预订单",
            step_prefix=f"{step_id}-CAN-U",
            order_id_var="usageOrderId",
            skip_to_request_name=None,
            description="下单成功后 ``PATCH /v2/orders`` · 取消 usageOrderId",
            **_CancelRetryKw(),
        )
    )


def _PrebookingAddDaysForApiKind(api_kind: str) -> int:
    if api_kind == "bundle":
        return PREBOOKING_ADD_DAYS_START + 1
    if api_kind == "membership_prebooking":
        return PREBOOKING_ADD_DAYS_START + 2
    return PREBOOKING_ADD_DAYS_START


def _BuildAvailabilityRequestItem(
    *,
    purpose: str,
    step_id: str,
    body: str,
    prerequest_lines: Optional[List[str]] = None,
    add_days: int = PREBOOKING_ADD_DAYS_START,
) -> JsonObject:
    merged_prerequest = list(prerequest_lines or [])
    merged_prerequest.extend(Prerequest_SetupAvailability(add_days=add_days))
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "POST", "/prebookings/availability"),
        method="POST",
        url_path="/v2/resources/prebookings/availability",
        body=body,
        headers=BearerJsonHeaders(),
        description="classic 可用性 · 写入 prebookingToken 与 fastTrackAdultCount/ChildCount",
        prerequest_lines=merged_prerequest,
        test_lines=Lines_Step(
            step_id,
            [f"ftAssertHttpBusinessOk('{step_id}');", f"ftAssertAvailabilitySuccess('{step_id}');"],
        ),
    )


def _BuildOrderRequestItem(
    *,
    api_label: str,
    step_id: str,
    url_path: str,
    spec: NameFieldSpec,
    api_kind: str,
) -> JsonObject:
    path_hint = url_path.rstrip("/").split("/")[-1]
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(f"{api_label} · {spec.purpose}", step_id, "POST", path_hint),
        method="POST",
        url_path=url_path,
        body=BuildOrderBodyForSpec(spec, api_kind=api_kind),
        headers=BearerJsonHeaders(),
        description=(
            f"PAPI-2839 · case_kind={spec.case_kind} · expect_reject={spec.expect_reject} · "
            f"prebooking=({spec.prebooking_first_name!r},{spec.prebooking_last_name!r}) · "
            f"passenger_overrides={spec.passenger_overrides!r}"
        ),
        prerequest_lines=Prerequest_OrderNameSpec(spec),
        test_lines=_OrderTestLines(step_id, expect_reject=spec.expect_reject, api_kind=api_kind),
    )


def _BuildApiTrackFolderItems(
    *,
    api_label: str,
    step_prefix: str,
    url_path: str,
    cases: Sequence[NameFieldSpec],
    api_kind: str,
    setup_items: Sequence[JsonObject],
    availability_body: str,
    ok_availability_prerequest: Optional[List[str]] = None,
    ng_availability_prerequest: Optional[List[str]] = None,
) -> List[JsonObject]:
    """同一 API 链路：前置 → 每条合法用例各 1 次可用性+下单 → 非法用例共用 1 次可用性。"""
    items: List[JsonObject] = list(setup_items)
    ok_cases = [spec for spec in cases if not spec.expect_reject]
    ng_cases = [spec for spec in cases if spec.expect_reject]

    for spec in ok_cases:
        if api_kind == "epass_prebooking":
            items.extend(
                _EpassPrebookingSetupItems(step_id=f"{step_prefix}-{spec.step_key}-EP")
            )
        avl_step_id = f"{step_prefix}-{spec.step_key}-AVL"
        items.append(
            _BuildAvailabilityRequestItem(
                purpose=f"{api_label} · 可用性（{spec.purpose}）",
                step_id=avl_step_id,
                body=availability_body,
                prerequest_lines=ok_availability_prerequest,
                add_days=_PrebookingAddDaysForApiKind(api_kind),
            )
        )
        order_step_id = f"{step_prefix}-{spec.step_key}"
        items.append(
            _BuildOrderRequestItem(
                api_label=api_label,
                step_id=order_step_id,
                url_path=url_path,
                spec=spec,
                api_kind=api_kind,
            )
        )
        items.extend(_BuildCancelItemsAfterSuccessOrder(step_id=order_step_id, api_kind=api_kind))

    if ng_cases:
        ng_avl_step_id = f"{step_prefix}-NG-AVL"
        items.append(
            _BuildAvailabilityRequestItem(
                purpose=f"{api_label} · 可用性（非法用例共用）",
                step_id=ng_avl_step_id,
                body=availability_body,
                prerequest_lines=ng_availability_prerequest,
                add_days=_PrebookingAddDaysForApiKind(api_kind),
            )
        )
        for spec in ng_cases:
            items.append(
                _BuildOrderRequestItem(
                    api_label=api_label,
                    step_id=f"{step_prefix}-{spec.step_key}",
                    url_path=url_path,
                    spec=spec,
                    api_kind=api_kind,
                )
            )

    return items


def _MembershipAvailabilityBody(*, add_days: int = PREBOOKING_ADD_DAYS_START) -> str:
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "resourceId": "{{fastTrackResourceId}}",
            "prebookingDate": PrebookingDateApifoxExpr(add_days),
            "adultCount": DEFAULT_FASTTRACK_ADULT_COUNT,
            "childCount": DEFAULT_FASTTRACK_CHILD_COUNT,
            "membershipId": "{{membershipId}}",
        },
        ensure_ascii=False,
        indent=2,
    )


_BUNDLE_AVAILABILITY_PREREQUEST: Final[List[str]] = [
    *Prerequest_InitFastTrackPassengerCounts(),
    *Prerequest_NewClientUserId(),
]


def _BuildApiTrackFolder(
    *,
    folder_name: str,
    step_prefix: str,
    url_path: str,
    cases: Sequence[NameFieldSpec],
    api_label: str,
    api_kind: str,
    setup_items: Sequence[JsonObject],
    availability_body: str,
    ok_availability_prerequest: Optional[List[str]] = None,
    ng_availability_prerequest: Optional[List[str]] = None,
) -> JsonObject:
    return Folder(
        folder_name,
        _BuildApiTrackFolderItems(
            api_label=api_label,
            step_prefix=step_prefix,
            url_path=url_path,
            cases=cases,
            api_kind=api_kind,
            setup_items=setup_items,
            availability_body=availability_body,
            ok_availability_prerequest=ok_availability_prerequest,
            ng_availability_prerequest=ng_availability_prerequest,
        ),
        description=(
            f"PAPI-2839 · {api_label} · 正则 {NAME_REGEX_JS} · "
            "合法用例各调可用性；非法用例共用一次可用性。"
        ),
    )


def _EpassPrebookingSetupItems(*, step_id: str = "SETUP-EP-S01") -> List[JsonObject]:
    return [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：创建 fastTrack ePass", step_id, "POST", "/fastTrack/ePasses"),
            method="POST",
            url_path="/v2/orders/fastTrack/ePasses",
            body=CREATE_EPASS_PAYLOAD,
            headers=BearerJsonHeaders(),
            description="ePass prebooking 前置 · ``POST /v2/orders/fastTrack/ePasses`` · 写入 ePassId",
            prerequest_lines=[*Prerequest_InitFastTrackPassengerCounts(), *Prerequest_NewClientUserId()],
            test_lines=Lines_Step(
                step_id,
                [f"ftAssertHttpBusinessOk('{step_id}');", f"ftAssertCreateCoreFields('{step_id}');"],
            ),
        ),
    ]


def _MembershipSetupItems(*, step_id: str = "SETUP-MS-S01") -> List[JsonObject]:
    return [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：注册 membership", step_id, "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=MEMBERSHIP_REGISTER_PAYLOAD,
            headers=BearerJsonHeaders(),
            description="membership prebooking 前置 · ``POST /v2/memberships`` · 写入 membershipId",
            prerequest_lines=Prerequest_NewClientUserId(),
            test_lines=Lines_Step(
                step_id,
                [f"ftAssertHttpBusinessOk('{step_id}');", f"p39SaveMembershipId('{step_id}');"],
            ),
        ),
    ]


def _BuildCaseKindTrackFolder(
    *,
    folder_name: str,
    step_prefix: str,
    url_path: str,
    cases: Sequence[NameFieldSpec],
    api_label: str,
    api_kind: str,
    availability_body: str,
    ok_availability_prerequest: Optional[List[str]] = None,
    ng_availability_prerequest: Optional[List[str]] = None,
    setup_items: Optional[Sequence[JsonObject]] = None,
) -> JsonObject:
    """仅用例步骤（无前置造数）；供 ePass / membership 子文件夹复用。"""
    return _BuildApiTrackFolder(
        folder_name=folder_name,
        step_prefix=step_prefix,
        url_path=url_path,
        cases=cases,
        api_label=api_label,
        api_kind=api_kind,
        setup_items=list(setup_items or []),
        availability_body=availability_body,
        ok_availability_prerequest=ok_availability_prerequest,
        ng_availability_prerequest=ng_availability_prerequest,
    )


def BuildEpassFolder() -> JsonObject:
    return Folder(
        "P1 · ePass",
        [
            Folder(
                "00 前置",
                _EpassPrebookingSetupItems(),
                description="``POST /v2/orders/fastTrack/ePasses`` · 写入 ``ePassId``（``prebooking`` 必跑）",
            ),
            Folder(
                "prebooking",
                [
                    _BuildCaseKindTrackFolder(
                        folder_name="prebookingRequiredInfo",
                        step_prefix="P1-EP",
                        url_path="/v2/orders/fastTrack/ePasses/prebooking",
                        cases=PREBOOKING_INFO_CASES,
                        api_label="ePass prebooking",
                        api_kind="epass_prebooking",
                        availability_body=AvailabilityBody(
                            with_epass=True, add_days=PREBOOKING_ADD_DAYS_START
                        ),
                    ),
                    _BuildCaseKindTrackFolder(
                        folder_name="passengers",
                        step_prefix="P1-PX-EP",
                        url_path="/v2/orders/fastTrack/ePasses/prebooking",
                        cases=PASSENGERS_CASES,
                        api_label="ePass prebooking",
                        api_kind="epass_prebooking",
                        availability_body=AvailabilityBody(
                            with_epass=True, add_days=PREBOOKING_ADD_DAYS_START
                        ),
                    ),
                ],
                description="``POST /v2/orders/fastTrack/ePasses/prebooking`` · 前置 ``POST /v2/orders/fastTrack/ePasses`` → 可用性 → 下单",
            ),
            Folder(
                "bundle",
                [
                    _BuildCaseKindTrackFolder(
                        folder_name="prebookingRequiredInfo",
                        step_prefix="P1-BU",
                        url_path="/v2/orders/fastTrack/ePasses/bundle",
                        cases=PREBOOKING_INFO_CASES,
                        api_label="ePass bundle",
                        api_kind="bundle",
                        availability_body=AvailabilityBody(
                            with_epass=False, add_days=PREBOOKING_ADD_DAYS_START + 1
                        ),
                        ok_availability_prerequest=_BUNDLE_AVAILABILITY_PREREQUEST,
                        ng_availability_prerequest=_BUNDLE_AVAILABILITY_PREREQUEST,
                    ),
                    _BuildCaseKindTrackFolder(
                        folder_name="passengers",
                        step_prefix="P1-PX-BU",
                        url_path="/v2/orders/fastTrack/ePasses/bundle",
                        cases=PASSENGERS_CASES,
                        api_label="ePass bundle",
                        api_kind="bundle",
                        availability_body=AvailabilityBody(
                            with_epass=False, add_days=PREBOOKING_ADD_DAYS_START + 1
                        ),
                        ok_availability_prerequest=_BUNDLE_AVAILABILITY_PREREQUEST,
                        ng_availability_prerequest=_BUNDLE_AVAILABILITY_PREREQUEST,
                    ),
                ],
                description="``POST /v2/orders/fastTrack/ePasses/bundle``",
            ),
        ],
        description="ePass prebooking + bundle · 正则 ``^[A-Za-z ]+$``",
    )


def BuildMembershipFolder() -> JsonObject:
    return Folder(
        "P1 · membership",
        [
            Folder(
                "00 前置",
                _MembershipSetupItems(),
                description="``POST /v2/memberships`` · 写入 ``membershipId``（``prebooking`` 必跑）",
            ),
            Folder(
                "prebooking",
                [
                    _BuildCaseKindTrackFolder(
                        folder_name="prebookingRequiredInfo",
                        step_prefix="P1-MS",
                        url_path="/v2/orders/fastTrack/memberships/prebooking",
                        cases=PREBOOKING_INFO_CASES,
                        api_label="membership prebooking",
                        api_kind="membership_prebooking",
                        availability_body=_MembershipAvailabilityBody(
                            add_days=PREBOOKING_ADD_DAYS_START + 2
                        ),
                    ),
                    _BuildCaseKindTrackFolder(
                        folder_name="passengers",
                        step_prefix="P1-PX-MS",
                        url_path="/v2/orders/fastTrack/memberships/prebooking",
                        cases=PASSENGERS_CASES,
                        api_label="membership prebooking",
                        api_kind="membership_prebooking",
                        availability_body=_MembershipAvailabilityBody(
                            add_days=PREBOOKING_ADD_DAYS_START + 2
                        ),
                        setup_items=_MembershipSetupItems(step_id="SETUP-MS-S02"),
                    ),
                ],
                description=(
                    "``POST /v2/orders/fastTrack/memberships/prebooking`` · "
                    "``cashPaymentApplied=false`` · 前置 ``POST /v2/memberships`` → 可用性 → 下单"
                ),
            ),
        ],
        description="membership prebooking · 正则 ``^[A-Za-z ]+$``",
    )


def BuildScenarioDescription(track: TrackKind) -> str:
    if track == "epass":
        return (
            "由 GeneratePostmanCollectionPapi2839.py 生成（ePass 轨）。\n\n"
            "**范围**：仅 **FastTrack ePass**（``ePasses/prebooking`` + ``ePasses/bundle``）；"
            "membership 轨见 ``PAPI-2839-FastTrack-NameRegex-P1-Membership.postman_collection.json``；"
            "Lounge 品类隔离回归见 ``PAPI-2839-Lounge-NameRegex-Regression-P1*.postman_collection.json``。\n\n"
            "对齐 ``PAPI-2839-修复FT联系人firstName-lastName正则-测试分析-001.md`` 与 "
            "``.cursor/rules/fasttrack-epass-prebooking-patterns.mdc``。\n\n"
            "**FT 正则**：``prebookingRequiredInfo`` 与 ``passengers[]`` 的 ``firstName`` / ``lastName`` "
            "均为 ``^[A-Za-z ]+$``（**不含** Lounge 的 ``^[A-Za-z -]+$``）。\n\n"
            "**人数流转**：合法用例各调一次可用性取新 ``prebookingToken``；"
            "非法用例共用一次可用性后连续下单。"
            "下单 body 按用例静态写入场景姓名；Pre-request 仅同步 ``passengers`` 人数并回放场景字段。\n\n"
            "**正向断言**：``ftAssertPrebookingPassengersShape`` + ``ftAssert*OrderSuccess``；"
            "不校验 ``extra.lastName``/``availableUsages`` 与入参一致、``usedUsages=1``。\n\n"
            "**前置**：Environment / 数据集填 ``ProgramID``、``clientId``、``secret``；"
            f"``fastTrackResourceId`` 默认 {DEFAULT_FASTTRACK_RESOURCE_ID}（P2722 全部使用人·无航班号）。\n\n"
            "**前置链路**：ePass prebooking 先 ``POST /v2/orders/fastTrack/ePasses``；再可用性 → 下单。\n\n"
            "``prebookingDate``：ePass=+10天、Bundle=+11天，时刻 T10:00；"
            "前置每次重算写入请求体。\n\n"
            "**负向断言**：仅以 ``p39AssertNameRegexRejected`` 业务 ``code=-1`` 为准（不校验 HTTP 200）。\n\n"
            "**收尾**：每条**正向**下单成功后 ``PATCH /v2/orders`` 取消 usage 单。"
            "Bundle 响应 ``orderId`` 即 usage，本场景不另取消空的 ``purchaseOrderId``。"
        )
    return (
        "由 GeneratePostmanCollectionPapi2839.py 生成（membership 轨）。\n\n"
        "**范围**：仅 **FastTrack membership**（``memberships/prebooking``）；"
        "ePass 轨见 ``PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json``；"
        "Lounge 品类隔离回归见 ``PAPI-2839-Lounge-NameRegex-Regression-P1*.postman_collection.json``。\n\n"
        "对齐 ``PAPI-2839-修复FT联系人firstName-lastName正则-测试分析-001.md`` 与 "
        "``.cursor/rules/fasttrack-epass-prebooking-patterns.mdc``。\n\n"
        "**FT 正则**：``prebookingRequiredInfo`` 与 ``passengers[]`` 的 ``firstName`` / ``lastName`` "
        "均为 ``^[A-Za-z ]+$``（**不含** Lounge 的 ``^[A-Za-z -]+$``）。\n\n"
        "**人数流转**：合法用例各调一次可用性取新 ``prebookingToken``；"
        "非法用例共用一次可用性后连续下单。"
        "下单 body 按用例静态写入场景姓名；Pre-request 仅同步 ``passengers`` 人数并回放场景字段。\n\n"
        "**正向断言**：``ftAssertPrebookingPassengersShape`` + ``p39AssertMembershipPrebookingSuccess``；"
        "不校验 ``extra.lastName``/``availableUsages`` 与入参一致、``usedUsages=1``。\n\n"
        "**前置**：Environment / 数据集填 ``ProgramID``、``clientId``、``secret``；"
        f"``fastTrackResourceId`` 默认 {DEFAULT_FASTTRACK_RESOURCE_ID}（P2722 全部使用人·无航班号）。\n\n"
        "**前置链路**：先 ``POST /v2/memberships``；再可用性 → 下单。"
        "``cashPaymentApplied=false``。\n\n"
        "``prebookingDate``：membership=+12天，时刻 T10:00；前置每次重算写入请求体。\n\n"
        "**负向断言**：仅以 ``p39AssertNameRegexRejected`` 业务 ``code=-1`` 为准（不校验 HTTP 200）。\n\n"
        "**收尾**：每条**正向**下单成功后 ``PATCH /v2/orders`` 取消 usage 单。"
    )


def BuildCollection(track: TrackKind) -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            RequestItem(
                js_helpers=_JsHelpers,
                name=PurposeName("获取 ePass 鉴权 token", "Auth", "POST", "/auth/token"),
                method="POST",
                url_path="/v2/auth/token",
                body=json.dumps({"clientId": "{{clientId}}", "secret": "{{secret}}"}, indent=2),
                headers=AuthJsonHeaders(),
                description="鉴权；写入 accessToken。",
                save_token=True,
                prerequest_lines=Prerequest_Auth(),
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行本文件夹。",
    )

    track_label = "ePass" if track == "epass" else "Membership"
    info: JsonObject = {
        "name": f"PAPI-2839 · FT 姓名正则 {track_label}（prebookingRequiredInfo + passengers）",
        "description": BuildScenarioDescription(track),
        "schema": POSTMAN_SCHEMA,
    }

    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable("epassModule", str(EPASS_MODULE_DEFAULT)),
        CollectionVariable("otherModule", "11"),
        CollectionVariable(FASTTRACK_RESOURCE_ID_VAR, DEFAULT_FASTTRACK_RESOURCE_ID),
        CollectionVariable("fastTrackAdultCount", str(DEFAULT_FASTTRACK_ADULT_COUNT)),
        CollectionVariable("fastTrackChildCount", str(DEFAULT_FASTTRACK_CHILD_COUNT)),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable("fastTrackAvailabilityResourceId", ""),
        CollectionVariable("accessToken", ""),
        CollectionVariable(
            HELPERS_SOURCE_KEY,
            "",
            "Auth 写入的 helpers 源码；其它步骤 eval。单独跑业务步须先跑 00 Auth。",
        ),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("ePassId", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("membershipId", ""),
        CollectionVariable("prebookingToken", ""),
        CollectionVariable("usageOrderId", ""),
    ]

    return {
        "info": info,
        "variable": variables,
        "item": [auth_folder, BuildEpassFolder() if track == "epass" else BuildMembershipFolder()],
    }


def Main() -> None:
    for track, out_name in (
        ("epass", OUT_NAME_EPASS),
        ("membership", OUT_NAME_MEMBERSHIP),
    ):
        out_path = str(CollectionPath(out_name))
        WriteCollectionJson(out_path, BuildCollection(track))
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
