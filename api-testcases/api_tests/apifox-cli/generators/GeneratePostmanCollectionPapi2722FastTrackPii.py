"""
生成 PAPI-2722 · FT PII（全部使用人·无航班号）Postman Collection v2.1 JSON。

对齐 ``testcases/2026Q2SP4/PAPI-2722-预订单PII信息收集改读BOSS-测试分析-001.md`` 中
``FtPrebookingE2E`` · ``tc-p1: FT场景-邮箱姓名电话 不需要航班号``（全部使用人）：

- 【步骤2·资源详情】``GET /v2/resources/{resourceId}?module=2`` → ``prebookingRequiredInfo=[1,2,3,4,5]`` 不含 ``6``
- 【步骤3·下单校验】三接口各 6 条负向（``prebookingRequiredInfo`` 每次少 1 个字段；``transportNumber`` 不传应成功）
- 【步骤3·下单校验】三接口正向：全部使用人 PII 完整、不传 ``transportNumber``

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionPapi2722FastTrackPii.py

一次写出 ePass / membership 两套 Collection（便于分别挂 ``epass`` / ``membership`` P1-prebooking）。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Final, List, Literal, Optional, Sequence, Tuple

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
    CREATE_PAYLOAD_TEMPLATE,
    DEFAULT_FASTTRACK_RESOURCE_ID,
    EPASS_MODULE_DEFAULT,
    OTHER_MODULE_DEFAULT,
    BuildCancelWithRetryBlock,
    BuildFastTrackBundleBody,
    BuildFastTrackEpassPrebookingBody,
    BuildFastTrackJsHelpersLines,
    BuildFastTrackMembershipPrebookingBody,
    DEFAULT_FASTTRACK_ADULT_COUNT,
    DEFAULT_FASTTRACK_CHILD_COUNT,
    Lines_Auth as FtLines_Auth,
    Prerequest_InitFastTrackPassengerCounts,
    Prerequest_NewClientUserId,
    Prerequest_ResetForBundle,
    Prerequest_ResetForPrebooking,
    Prerequest_SyncPrebookingDateFromApifox,
    Prerequest_SyncPrebookingPassengersBody,
)

JsonObject = Dict[str, Any]
HELPERS_SOURCE_KEY: Final[str] = "p2722HelpersSource"


def RequestItem(**kwargs: Any) -> JsonObject:
    """PAPI-2722：Auth 写入 ``p2722HelpersSource``，其它步 eval loader。"""
    kwargs.setdefault("helpers_source_key", HELPERS_SOURCE_KEY)
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["ftApplyRuntimeIdsToRequestBody();"]
    return CommonRequestItem(**kwargs)

TrackKind = Literal["epass", "membership"]

OUT_NAME_EPASS: Final[str] = "PAPI-2722-FastTrack-PII-P1.postman_collection.json"
OUT_NAME_MEMBERSHIP: Final[str] = "PAPI-2722-FastTrack-PII-P1-Membership.postman_collection.json"
EXPECTED_PII_ENUMS: Final[List[int]] = [1, 2, 3, 4, 5]
ADULT_COUNT: Final[int] = DEFAULT_FASTTRACK_ADULT_COUNT
CHILD_COUNT: Final[int] = DEFAULT_FASTTRACK_CHILD_COUNT

MEMBERSHIP_REGISTER_PAYLOAD: Final[str] = json.dumps(
    {
        "clientUserId": "{{$string.uuid}}",
        "firstName": "Auto",
        "lastName": "Smith",
        "phoneNumber": "8081966002",
        "callingCode": "44",
        "email": "p2722_{{$timestamp}}@dragonpass.com",
        "expirationDate": "2027-12-31T10:10:33+00:00",
    },
    ensure_ascii=False,
    indent=2,
)


@dataclass(frozen=True)
class OmitFieldSpec:
    field_name: str
    purpose: str
    expect_reject: bool


OrderApiKind = str  # ``epass_prebooking`` | ``bundle`` | ``membership_prebooking``

NEGATIVE_OMIT_SPECS: Final[Tuple[OmitFieldSpec, ...]] = (
    OmitFieldSpec("firstName", "缺 prebookingRequiredInfo.firstName", True),
    OmitFieldSpec("lastName", "缺 prebookingRequiredInfo.lastName", True),
    OmitFieldSpec("email", "缺 prebookingRequiredInfo.email", True),
    OmitFieldSpec("phoneNumber", "缺 prebookingRequiredInfo.phoneNumber", True),
    OmitFieldSpec("callingCode", "缺 prebookingRequiredInfo.callingCode", True),
    OmitFieldSpec("transportNumber", "不传 transportNumber（BOSS 未收集航班号）", False),
)

# 与 P0 ``FastTrackPrebookingExtraDict`` 同构（含 ``transportNumber: BA123``）；P2722 N06 专项删 ``transportNumber``。
P2722_INCLUDE_TRANSPORT_NUMBER: Final[bool] = True


def BuildEpassPrebookingBody(omit_field: Optional[str] = None) -> str:
    return BuildFastTrackEpassPrebookingBody(
        omit_prebooking_required_info_field=omit_field,
        include_transport_number=P2722_INCLUDE_TRANSPORT_NUMBER,
    )


def BuildBundleBody(omit_field: Optional[str] = None) -> str:
    return BuildFastTrackBundleBody(
        omit_prebooking_required_info_field=omit_field,
        include_transport_number=P2722_INCLUDE_TRANSPORT_NUMBER,
    )


def BuildMembershipPrebookingBody(omit_field: Optional[str] = None) -> str:
    return BuildFastTrackMembershipPrebookingBody(
        omit_prebooking_required_info_field=omit_field,
        include_transport_number=P2722_INCLUDE_TRANSPORT_NUMBER,
        adult_count=ADULT_COUNT,
    )


def BuildClassicAvailabilityBody(
    *,
    with_epass: bool,
    with_membership: bool,
    add_days: int = PREBOOKING_ADD_DAYS_START,
) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{fastTrackResourceId}}",
        "prebookingDate": PrebookingDateApifoxExpr(add_days),
        "adultCount": ADULT_COUNT,
        "childCount": CHILD_COUNT,
    }
    if with_epass:
        body["ePassId"] = "{{ePassId}}"
    if with_membership:
        body["membershipId"] = "{{membershipId}}"
    return json.dumps(body, ensure_ascii=False, indent=2)


def BuildP2722JsHelpersLines() -> List[str]:
    expected_enums_js = json.dumps(EXPECTED_PII_ENUMS)
    js = rf"""function p27SyncPrebookingPassengersOnly() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var body = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (!body.extra || typeof body.extra !== 'object') body.extra = {{}};
    var counts = ftResolveFastTrackPassengerCounts();
    body.extra.passengers = ftBuildFastTrackPassengers(counts.adultCount, counts.childCount);
    pm.request.body.raw = JSON.stringify(body, null, 2);
  }} catch (e) {{
    console.warn('p27SyncPrebookingPassengersOnly:', e);
    throw e;
  }}
}}
function p27AssertBusinessRejected(label) {{
  pm.test(label + ': 业务拒绝 code=-1', function () {{
    var env = pm.response.json();
    pm.expect(env.code).to.eql(-1);
    pm.expect(env.msg, 'msg 非空').to.be.a('string').and.not.empty;
  }});
}}
function p27AssertResourcePiiEnums(label) {{
  ftAssertHttpBusinessOk(label);
  pm.test(label + ': prebookingRequiredInfo=[1,2,3,4,5] 不含 6', function () {{
    var data = ftGetInnerData(pm.response.json());
    pm.expect(data, label + ' data').to.be.an('object');
    var policy = data.prebookingPolicy || {{}};
    var info = policy.prebookingRequiredInfo;
    if (info === undefined) {{ info = data.prebookingRequiredInfo; }}
    pm.expect(info, 'prebookingPolicy.prebookingRequiredInfo').to.be.an('array');
    var sorted = info.slice().sort(function (a, b) {{ return a - b; }});
    pm.expect(sorted).to.eql({expected_enums_js});
    pm.expect(info).to.not.include(6);
  }});
}}
function p27SaveMembershipId(label) {{
  pm.test(label + ': 保存 membershipId', function () {{
    var data = ftGetInnerData(pm.response.json());
    ftCaptureClientUserIdAfterSend(data);
    var mid = data.membershipId || data.id;
    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;
    pm.collectionVariables.set('membershipId', String(mid));
  }});
}}
function p27SaveUsageOrderId(label) {{
  pm.test(label + ': usage orderId 非空', function () {{
    var data = ftGetInnerData(pm.response.json());
    pm.expect(data.orderId).to.be.a('string').and.not.empty;
    ftSaveUsageOrderId(data);
  }});
}}
"""
    return js.splitlines()


def _JsHelpers() -> List[str]:
    """关闭 ``usedUsages=1``：本场景 ``adultCount=2``，prebooking/bundle 回显 ``usedUsages=2``。"""
    return BuildFastTrackJsHelpersLines(
        assert_epass_status=False,
        assert_usage_used_usages_one=False,
        assert_booking_counts=False,
    ) + BuildP2722JsHelpersLines()


def Lines_Auth() -> List[str]:
    return FtLines_Auth()


def Prerequest_ResetForMembership() -> List[str]:
    return [
        *Prerequest_InitFastTrackPassengerCounts(),
        *Prerequest_NewClientUserId(),
        "ftUnsetVar('membershipId');",
        "ftUnsetVar('prebookingToken');",
        "ftUnsetVar('usageOrderId');",
    ]


def Prerequest_SyncPrebookingPassengersBodyForOmit(omit_field: Optional[str]) -> List[str]:
    """负向缺 ``firstName``/``lastName`` 时仅同步 ``passengers``，避免 ``ftSync`` 写回姓名。"""
    if omit_field in ("firstName", "lastName"):
        return ["p27SyncPrebookingPassengersOnly();"]
    return Prerequest_SyncPrebookingPassengersBody()


def _OrderSuccessTestLines(step_id: str, api_kind: OrderApiKind) -> List[str]:
    lines: List[str] = [
        f"ftAssertPrebookingPassengersShape('{step_id}');",
        f"ftAssertHttpBusinessOk('{step_id}');",
    ]
    if api_kind == "epass_prebooking":
        lines.append(f"ftAssertPrebookingOrderSuccess('{step_id}');")
    elif api_kind == "bundle":
        lines.append(f"ftAssertBundleOrderSuccess('{step_id}');")
    else:
        lines.append(f"p27SaveUsageOrderId('{step_id}');")
    return lines


def _CancelRetryKw() -> Dict[str, Any]:
    """FT 预订单刚创建时常 ``500.051.029``；单步 HTTP + ``sendRequest`` 轮询取消。"""
    return {
        "helpers_source_key": HELPERS_SOURCE_KEY,
        "max_attempts": 3,
        "cancel_fn": "ftCancelOrderAttemptWithPoll",
    }


def _BuildCancelItemsAfterSuccessOrder(*, step_id: str, api_kind: OrderApiKind) -> List[JsonObject]:
    """正向下单成功后 ``PATCH /v2/orders`` 取消 usage。

    Bundle 响应 ``orderId`` 即 usage，``purchaseOrderId`` 未写入（P0 靠 search-by-ePassId 才补）；
    本 PII 场景不另开 search，故不发空 ``purchaseOrderId`` 取消。
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


def _NegativeOrderTests(
    step_id: str,
    *,
    expect_reject: bool,
    omit_field: Optional[str],
    api_kind: OrderApiKind,
) -> List[str]:
    if expect_reject:
        shape_line: List[str] = []
        if omit_field not in ("firstName", "lastName"):
            shape_line = [f"ftAssertPrebookingPassengersShape('{step_id}');"]
        return Lines_Step(step_id, [*shape_line, f"p27AssertBusinessRejected('{step_id}');"])
    return Lines_Step(step_id, _OrderSuccessTestLines(step_id, api_kind))


def _BuildNegativeOrderRequests(
    *,
    api_label: str,
    step_prefix: str,
    url_path: str,
    body_builder: Callable[[Optional[str]], str],
    start_index: int,
    api_kind: OrderApiKind,
) -> List[JsonObject]:
    items: List[JsonObject] = []
    idx = start_index
    for spec in NEGATIVE_OMIT_SPECS:
        step_id = f"{step_prefix}-N{idx:02d}"
        omit_field: Optional[str] = spec.field_name if spec.expect_reject else None
        items.append(
            RequestItem(
                js_helpers=_JsHelpers,
                name=PurposeName(f"{api_label} · {spec.purpose}", step_id, "POST", url_path.split("/")[-1]),
                method="POST",
                url_path=url_path,
                body=body_builder(omit_field),
                headers=BearerJsonHeaders(),
                description=f"PAPI-2722 负向 · omit={spec.field_name} · expect_reject={spec.expect_reject}",
                prerequest_lines=Prerequest_SyncPrebookingPassengersBodyForOmit(omit_field),
                test_lines=_NegativeOrderTests(
                    step_id,
                    expect_reject=spec.expect_reject,
                    omit_field=omit_field,
                    api_kind=api_kind,
                ),
            )
        )
        if not spec.expect_reject:
            items.extend(_BuildCancelItemsAfterSuccessOrder(step_id=step_id, api_kind=api_kind))
        idx += 1
    return items


def _BuildSuccessOrderRequest(
    *,
    purpose: str,
    step_id: str,
    url_path: str,
    body: str,
    api_kind: OrderApiKind,
) -> JsonObject:
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "POST", url_path.split("/")[-1]),
        method="POST",
        url_path=url_path,
        body=body,
        headers=BearerJsonHeaders(),
        description="PAPI-2722 正向 · 全部使用人 PII 完整 · 与 P0 同构含 transportNumber",
        prerequest_lines=Prerequest_SyncPrebookingPassengersBody(),
        test_lines=Lines_Step(step_id, _OrderSuccessTestLines(step_id, api_kind)),
    )


def _AppendSuccessOrderWithCancel(
    items: List[JsonObject],
    *,
    purpose: str,
    step_id: str,
    url_path: str,
    body: str,
    api_kind: OrderApiKind,
) -> None:
    items.append(
        _BuildSuccessOrderRequest(
            purpose=purpose,
            step_id=step_id,
            url_path=url_path,
            body=body,
            api_kind=api_kind,
        )
    )
    items.extend(_BuildCancelItemsAfterSuccessOrder(step_id=step_id, api_kind=api_kind))


def Prerequest_EnsureResourceDetailQuery() -> List[str]:
    """绑定真实 ``GET /v2/resources/{id}`` 后 query 常被丢掉；运行时强制补回 ``module=2``。"""
    return [
        "(function () {",
        "  var raw = '';",
        "  try {",
        "    raw = String((pm.request && pm.request.url && pm.request.url.toString && pm.request.url.toString()) || '');",
        "  } catch (e0) { raw = ''; }",
        "  raw = pm.variables.replaceIn(raw);",
        "  var base = String(raw || '').split('?')[0];",
        "  if (!base) { return; }",
        "  var next = base + '?module=2&language=en-US&fallbackAllowed=true';",
        "  try { pm.request.url = next; } catch (e1) {}",
        "})();",
    ]


def _BuildResourceDetailRequest() -> JsonObject:
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(
            "资源详情 prebookingRequiredInfo 枚举",
            "P1-S01",
            "GET",
            "/resources/{resourceId}",
        ),
        method="GET",
        url_path="/v2/resources/{{fastTrackResourceId}}?module=2&language=en-US&fallbackAllowed=true",
        body=None,
        headers=BearerJsonHeaders(),
        description="``GET /v2/resources/{resourceId}?module=2`` · 断言 ``[1,2,3,4,5]`` 不含 ``6``",
        prerequest_lines=Prerequest_EnsureResourceDetailQuery(),
        test_lines=Lines_Step("P1-S01", ["p27AssertResourcePiiEnums('P1-S01');"]),
    )


def _BuildAvailabilityRequest(
    *,
    purpose: str,
    step_id: str,
    body: str,
    prerequest_lines: Optional[List[str]] = None,
    add_days: int = PREBOOKING_ADD_DAYS_START,
) -> JsonObject:
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(purpose, step_id, "POST", "/prebookings/availability"),
        method="POST",
        url_path="/v2/resources/prebookings/availability",
        body=body,
        headers=BearerJsonHeaders(),
        description="经典可用性 · 本机今天+N 天 T10:00 · 写入 prebookingToken",
        prerequest_lines=prerequest_lines
        or Prerequest_SyncPrebookingDateFromApifox(add_days),
        test_lines=Lines_Step(
            step_id,
            [f"ftAssertHttpBusinessOk('{step_id}');", f"ftAssertAvailabilitySuccess('{step_id}');"],
        ),
    )


def _BuildEpassPrebookingTrackItems() -> List[JsonObject]:
    items: List[JsonObject] = [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：创建 fastTrack ePass", "P1-S02", "POST", "/fastTrack/ePasses"),
            method="POST",
            url_path="/v2/orders/fastTrack/ePasses",
            body=CREATE_PAYLOAD_TEMPLATE,
            headers=BearerJsonHeaders(),
            description="ePass prebooking 前置 · ``POST /v2/orders/fastTrack/ePasses`` · 写入 ePassId",
            prerequest_lines=Prerequest_ResetForPrebooking(),
            test_lines=Lines_Step(
                "P1-S02",
                ["ftAssertHttpBusinessOk('P1-S02');", "ftAssertCreateCoreFields('P1-S02');"],
            ),
        ),
        _BuildAvailabilityRequest(
            purpose="ePass 可用性取 token（2 成人）",
            step_id="P1-S03",
            body=BuildClassicAvailabilityBody(
                with_epass=True,
                with_membership=False,
                add_days=PREBOOKING_ADD_DAYS_START,
            ),
            add_days=PREBOOKING_ADD_DAYS_START,
        ),
    ]
    items.extend(
        _BuildNegativeOrderRequests(
            api_label="ePass prebooking",
            step_prefix="P1-S04",
            url_path="/v2/orders/fastTrack/ePasses/prebooking",
            body_builder=BuildEpassPrebookingBody,
            start_index=1,
            api_kind="epass_prebooking",
        )
    )
    items.append(
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName(
                "前置：重建 fastTrack ePass（正向下单，N06 已用尽次数）",
                "P1-S04-OK-EP",
                "POST",
                "/fastTrack/ePasses",
            ),
            method="POST",
            url_path="/v2/orders/fastTrack/ePasses",
            body=CREATE_PAYLOAD_TEMPLATE,
            headers=BearerJsonHeaders(),
            description="N06 已用尽 ``availableUsages`` · 再建一张 ePass 供正向下单",
            prerequest_lines=Prerequest_ResetForPrebooking(),
            test_lines=Lines_Step(
                "P1-S04-OK-EP",
                ["ftAssertHttpBusinessOk('P1-S04-OK-EP');", "ftAssertCreateCoreFields('P1-S04-OK-EP');"],
            ),
        )
    )
    items.append(
        _BuildAvailabilityRequest(
            purpose="ePass 可用性取 token（正向下单，N06 已消耗上一枚）",
            step_id="P1-S04-OK-AVL",
            body=BuildClassicAvailabilityBody(
                with_epass=True,
                with_membership=False,
                add_days=PREBOOKING_ADD_DAYS_START,
            ),
            add_days=PREBOOKING_ADD_DAYS_START,
        )
    )
    _AppendSuccessOrderWithCancel(
        items,
        purpose="ePass prebooking 全部使用人 PII 成功",
        step_id="P1-S04-OK",
        url_path="/v2/orders/fastTrack/ePasses/prebooking",
        body=BuildEpassPrebookingBody(),
        api_kind="epass_prebooking",
    )
    return items


def _BuildEpassBundleTrackItems() -> List[JsonObject]:
    items: List[JsonObject] = [
        _BuildAvailabilityRequest(
            purpose="Bundle 可用性取 token（无 ePassId）",
            step_id="P1-S05",
            body=BuildClassicAvailabilityBody(
                with_epass=False,
                with_membership=False,
                add_days=PREBOOKING_ADD_DAYS_START + 1,
            ),
            prerequest_lines=[
                *Prerequest_ResetForBundle(),
                *Prerequest_SyncPrebookingDateFromApifox(PREBOOKING_ADD_DAYS_START + 1),
            ],
            add_days=PREBOOKING_ADD_DAYS_START + 1,
        ),
    ]
    items.extend(
        _BuildNegativeOrderRequests(
            api_label="ePass bundle",
            step_prefix="P1-S06",
            url_path="/v2/orders/fastTrack/ePasses/bundle",
            body_builder=BuildBundleBody,
            start_index=1,
            api_kind="bundle",
        )
    )
    items.append(
        _BuildAvailabilityRequest(
            purpose="Bundle 可用性取 token（正向下单，N06 已消耗上一枚）",
            step_id="P1-S06-OK-AVL",
            body=BuildClassicAvailabilityBody(
                with_epass=False,
                with_membership=False,
                add_days=PREBOOKING_ADD_DAYS_START + 1,
            ),
            add_days=PREBOOKING_ADD_DAYS_START + 1,
        )
    )
    _AppendSuccessOrderWithCancel(
        items,
        purpose="ePass bundle 全部使用人 PII 成功",
        step_id="P1-S06-OK",
        url_path="/v2/orders/fastTrack/ePasses/bundle",
        body=BuildBundleBody(),
        api_kind="bundle",
    )
    return items


def _BuildMembershipPrebookingTrackItems() -> List[JsonObject]:
    items: List[JsonObject] = [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：注册 membership", "P1-S07", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=MEMBERSHIP_REGISTER_PAYLOAD,
            headers=BearerJsonHeaders(),
            description="membership prebooking 前置 · ``POST /v2/memberships`` · 写入 membershipId",
            prerequest_lines=Prerequest_ResetForMembership(),
            test_lines=Lines_Step(
                "P1-S07",
                ["ftAssertHttpBusinessOk('P1-S07');", "p27SaveMembershipId('P1-S07');"],
            ),
        ),
        _BuildAvailabilityRequest(
            purpose="membership 可用性取 token",
            step_id="P1-S08",
            body=BuildClassicAvailabilityBody(
                with_epass=False,
                with_membership=True,
                add_days=PREBOOKING_ADD_DAYS_START + 2,
            ),
            add_days=PREBOOKING_ADD_DAYS_START + 2,
        ),
    ]
    items.extend(
        _BuildNegativeOrderRequests(
            api_label="membership prebooking",
            step_prefix="P1-S09",
            url_path="/v2/orders/fastTrack/memberships/prebooking",
            body_builder=BuildMembershipPrebookingBody,
            start_index=1,
            api_kind="membership_prebooking",
        )
    )
    items.append(
        _BuildAvailabilityRequest(
            purpose="membership 可用性取 token（正向下单，N06 已消耗上一枚）",
            step_id="P1-S09-OK-AVL",
            body=BuildClassicAvailabilityBody(
                with_epass=False,
                with_membership=True,
                add_days=PREBOOKING_ADD_DAYS_START + 2,
            ),
            add_days=PREBOOKING_ADD_DAYS_START + 2,
        )
    )
    _AppendSuccessOrderWithCancel(
        items,
        purpose="membership prebooking 全部使用人 PII 成功",
        step_id="P1-S09-OK",
        url_path="/v2/orders/fastTrack/memberships/prebooking",
        body=BuildMembershipPrebookingBody(),
        api_kind="membership_prebooking",
    )
    return items


def BuildStep2ResourceFolder() -> JsonObject:
    return Folder(
        "【步骤2·资源详情】",
        [_BuildResourceDetailRequest()],
        description=(
            "``GET /v2/resources/{{fastTrackResourceId}}?module=2`` · "
            "断言 ``prebookingRequiredInfo=[1,2,3,4,5]`` 不含 ``6``"
        ),
    )


def BuildStep3OrderFolder(track: TrackKind) -> JsonObject:
    children: List[JsonObject]
    if track == "epass":
        children = [
            Folder(
                "ePass · prebooking",
                _BuildEpassPrebookingTrackItems(),
                description=(
                    "``POST /v2/orders/fastTrack/ePasses/prebooking`` · "
                    "前置 ``POST /v2/orders/fastTrack/ePasses`` → 可用性 → 6 负向 + 1 正向"
                ),
            ),
            Folder(
                "ePass · bundle",
                _BuildEpassBundleTrackItems(),
                description=(
                    "``POST /v2/orders/fastTrack/ePasses/bundle`` · "
                    "可用性（无 ePassId）→ 6 负向 + 1 正向"
                ),
            ),
        ]
        desc = (
            "ePass prebooking / bundle 各 6 条负向（每次仅缺 ``prebookingRequiredInfo`` 一个字段；"
            "``transportNumber`` 不传应成功）+ 各 1 条正向"
        )
    else:
        children = [
            Folder(
                "membership · prebooking",
                _BuildMembershipPrebookingTrackItems(),
                description=(
                    "``POST /v2/orders/fastTrack/memberships/prebooking`` · "
                    "前置 ``POST /v2/memberships`` → 可用性 → 6 负向 + 1 正向 · "
                    "``cashPaymentApplied=false``"
                ),
            ),
        ]
        desc = (
            "membership prebooking 6 条负向（每次仅缺 ``prebookingRequiredInfo`` 一个字段；"
            "``transportNumber`` 不传应成功）+ 1 条正向"
        )
    return Folder("【步骤3·下单校验】", children, description=desc)


def BuildMainScenarioFolder(track: TrackKind) -> JsonObject:
    track_label = "ePass" if track == "epass" else "membership"
    return Folder(
        f"P1 · FtPrebookingE2E · {track_label}（全部使用人·无航班号）",
        [BuildStep2ResourceFolder(), BuildStep3OrderFolder(track)],
        description=(
            "对齐 ``PAPI-2722-预订单PII信息收集改读BOSS-测试分析-001.md`` · "
            "``tc-p1: FT场景-邮箱姓名电话 不需要航班号``。"
            "步骤1（BOSS 配置）为人工前置，不在本集合内。"
        ),
    )


def BuildScenarioDescription(track: TrackKind) -> str:
    if track == "epass":
        return (
            "由 GeneratePostmanCollectionPapi2722FastTrackPii.py 生成（ePass 轨）。\n\n"
            "对齐 ``PAPI-2722-预订单PII信息收集改读BOSS-测试分析-001.md`` · "
            "``FtPrebookingE2E`` · ``tc-p1: FT场景-邮箱姓名电话 不需要航班号``（全部使用人）。\n\n"
            "**本集合只含 ePass**：``ePasses/prebooking`` + ``ePasses/bundle``。"
            "membership 轨见 ``PAPI-2722-FastTrack-PII-P1-Membership.postman_collection.json``。\n\n"
            "**前置**：Environment/集合填 ``ProgramID``、``clientId``、``secret``；"
            f"``fastTrackResourceId`` 默认 {DEFAULT_FASTTRACK_RESOURCE_ID}（BOSS 已配置全部使用人+无航班号）。\n\n"
            "**步骤2**：``GET /v2/resources/{{fastTrackResourceId}}?module=2`` → "
            "``prebookingRequiredInfo=[1,2,3,4,5]`` 不含 ``6``。\n\n"
            "**步骤3 负向**：``ePasses/prebooking``、``ePasses/bundle`` 各 6 步，"
            "每次仅缺 ``prebookingRequiredInfo`` 一个字段（``transportNumber`` 不传应成功）。\n\n"
            "**步骤3 正向**：两接口各 1 步 — body 与 P0 E02-S03 同构（``prebookingRequiredInfo`` + ``passengers[]`` + ``transportNumber: BA123``）；"
            "Pre-request ``ftSyncPrebookingPassengersBody()``；Tests ``ftAssertPrebookingPassengersShape``。\n\n"
            "**步骤3 N06**：专项验证不传 ``transportNumber`` 仍可成功（C10826 无航班号 BOSS）。\n\n"
            "**目录**：``P1 · FtPrebookingE2E · ePass`` → ``【步骤2·资源详情】`` → "
            "``【步骤3·下单校验】``（``ePass·prebooking`` / ``ePass·bundle``）。\n\n"
            "**前置链路**：ePass prebooking 先 ``POST /v2/orders/fastTrack/ePasses``；再可用性 → 下单。\n\n"
            "``prebookingDate``：ePass=+10天、Bundle=+11天，时刻 T10:00；"
            "前置每次重算写入请求体，禁止沿用 Environment 旧值。\n\n"
            "**勿与 P0 混淆**：``FastTrack-ePass-P0-e2e-core`` 为 E01/E02/E03 全链路回归；"
            "本集合仅覆盖 P2722 PII 场景。\n\n"
            "**负向断言**：仅以 ``p27AssertBusinessRejected`` 业务 ``code=-1`` 为准（不校验 HTTP 200）。\n\n"
            "**收尾**：每条**正向**下单成功后 ``PATCH /v2/orders`` 取消 usage 单"
            "（含 N06 不传 ``transportNumber`` 成功步）。"
            "Bundle 响应 ``orderId`` 即 usage，本场景不另取消空的 ``purchaseOrderId``。\n\n"
            "**Apifox**：负向步骤请关闭「校验响应 HTTP 200 = 成功」，避免与 HTTP 400 响应冲突。"
        )
    return (
        "由 GeneratePostmanCollectionPapi2722FastTrackPii.py 生成（membership 轨）。\n\n"
        "对齐 ``PAPI-2722-预订单PII信息收集改读BOSS-测试分析-001.md`` · "
        "``FtPrebookingE2E`` · ``tc-p1: FT场景-邮箱姓名电话 不需要航班号``（全部使用人）。\n\n"
        "**本集合只含 membership**：``memberships/prebooking``。"
        "ePass 轨见 ``PAPI-2722-FastTrack-PII-P1.postman_collection.json``。\n\n"
        "**前置**：Environment/集合填 ``ProgramID``、``clientId``、``secret``；"
        f"``fastTrackResourceId`` 默认 {DEFAULT_FASTTRACK_RESOURCE_ID}（BOSS 已配置全部使用人+无航班号）。\n\n"
        "**步骤2**：``GET /v2/resources/{{fastTrackResourceId}}?module=2`` → "
        "``prebookingRequiredInfo=[1,2,3,4,5]`` 不含 ``6``。\n\n"
        "**步骤3 负向**：``memberships/prebooking`` 6 步，"
        "每次仅缺 ``prebookingRequiredInfo`` 一个字段（``transportNumber`` 不传应成功）。\n\n"
        "**步骤3 正向**：1 步 — body 与 P0 同构（``prebookingRequiredInfo`` + ``passengers[]`` + ``transportNumber: BA123``）；"
        "Pre-request ``ftSyncPrebookingPassengersBody()``；Tests ``ftAssertPrebookingPassengersShape``。\n\n"
        "**步骤3 N06**：专项验证不传 ``transportNumber`` 仍可成功（C10826 无航班号 BOSS）。\n\n"
        "**目录**：``P1 · FtPrebookingE2E · membership`` → ``【步骤2·资源详情】`` → "
        "``【步骤3·下单校验】``（``membership·prebooking``）。\n\n"
        "**前置链路**：先 ``POST /v2/memberships``；再可用性 → 下单。"
        "``cashPaymentApplied=false``。\n\n"
        "``prebookingDate``：membership=+12天，时刻 T10:00；"
        "前置每次重算写入请求体，禁止沿用 Environment 旧值。\n\n"
        "**负向断言**：仅以 ``p27AssertBusinessRejected`` 业务 ``code=-1`` 为准（不校验 HTTP 200）。\n\n"
        "**收尾**：正向下单成功后 ``PATCH /v2/orders`` 取消 usage 单。\n\n"
        "**Apifox**：负向步骤请关闭「校验响应 HTTP 200 = 成功」，避免与 HTTP 400 响应冲突。"
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
                test_lines=Lines_Auth(),
            ),
        ],
        description="先执行本文件夹。",
    )

    track_label = "ePass" if track == "epass" else "Membership"
    info: JsonObject = {
        "name": f"PAPI-2722 · FT PII {track_label}（全部使用人·无航班号）",
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
        CollectionVariable("otherModule", str(OTHER_MODULE_DEFAULT)),
        CollectionVariable("fastTrackResourceId", DEFAULT_FASTTRACK_RESOURCE_ID),
        CollectionVariable("fastTrackAdultCount", str(ADULT_COUNT)),
        CollectionVariable("fastTrackChildCount", str(CHILD_COUNT)),
        CollectionVariable("prebookingDate", ""),
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
        "item": [auth_folder, BuildMainScenarioFolder(track)],
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
