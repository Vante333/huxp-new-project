"""
Fast Track E-pass 域公共构建能力。

仅依赖通用 Collection runtime 与 E-pass 域配置；payment、PAPI 与具体 FT P0
生成器均依赖本模块，禁止本模块反向导入 ``GeneratePostmanCollection*.py``。
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
    RequestItem as CommonRequestItem,
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
FASTTRACK_CATEGORY = GetEpassCategoryConfig("fastTrack")
EPASS_MAIN_CHAIN_SPECS = BuildEpassMainChainRequestSpecs(FASTTRACK_CATEGORY)
HELPERS_SOURCE_KEY: Final[str] = "ftEpassHelpersSource"


def RequestItem(**kwargs: Any) -> JsonObject:
    """FastTrack 集合：Auth 写入 ``ftEpassHelpersSource``，其它步 eval loader。"""
    kwargs.setdefault("helpers_source_key", HELPERS_SOURCE_KEY)
    existing: List[str] = list(kwargs.get("prerequest_lines") or [])
    kwargs["prerequest_lines"] = existing + ["ftApplyRuntimeIdsToRequestBody();"]
    return CommonRequestItem(**kwargs)

OUT_NAME: Final[str] = "FastTrack-ePass-P0-e2e-core.postman_collection.json"
DEFAULT_API_VERSION: Final[str] = "v2"
PREBOOKING_DATE_APIFOX: Final[str] = PrebookingDateApifoxExpr(PREBOOKING_ADD_DAYS_START)
CANCEL_SUCCESS_MSG: Final[str] = "The order was cancelled successfully"
CANCEL_RETRY_MSG_NEEDLE: Final[str] = "Order cancellation failed"
CREATE_AVAILABLE_USAGES: Final[int] = FASTTRACK_CATEGORY.available_usages
DEFAULT_FASTTRACK_ADULT_COUNT: Final[int] = 2
DEFAULT_FASTTRACK_CHILD_COUNT: Final[int] = 0
FASTTRACK_ADULT_PASSENGER_NAMES: Final[List[tuple[str, str]]] = [
    ("Auto", "Smith"),
    ("Alex", "Jones"),
    ("Anna", "Brown"),
    ("Alan", "Davis"),
]
FASTTRACK_CHILD_PASSENGER_NAMES: Final[List[tuple[str, str]]] = [
    ("Amy", "White"),
    ("Ben", "Green"),
    ("Cyra", "Black"),
    ("Dora", "Gray"),
]
DEFAULT_FASTTRACK_RESOURCE_ID: Final[str] = FASTTRACK_CATEGORY.default_resource_id
GENERATED_CANCEL_ATTEMPTS: Final[int] = 3
FASTTRACK_RESOURCE_ID_VAR: Final[str] = FASTTRACK_CATEGORY.resource_var
ENV_FASTTRACK_RESOURCE_ID: Final[str] = "DP_HIST_EPASS_FASTTRACK_RESOURCE_ID"
EPASS_MODULE_DEFAULT: Final[int] = FASTTRACK_CATEGORY.module

_LOUNGE_JS_ASSERT_EPASS_STATUS: bool = True


def SetFastTrackAssertEpassStatus(enabled: bool) -> bool:
    """设置 v1/v2 兼容断言开关并返回旧值，供生成入口在 ``finally`` 中恢复。"""
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


def _JsAssertCreateExtraLastNameBlock() -> str:
    return """  pm.test(label + ': extra.lastName 与入参一致', function () {{
    pm.expect(extra.lastName).to.eql(ftExpectedCreateExtra().lastName);
  }});"""


def _JsAssertCreateExtraAvailableUsagesBlock() -> str:
    return """  pm.test(label + ': extra.availableUsages 与入参一致', function () {{
    pm.expect(extra.availableUsages).to.eql(ftExpectedCreateExtra().availableUsages);
  }});"""


def _JsAssertUsageUsedUsagesOneBlock(*, data_fn: str = "data()") -> str:
    return f"""  pm.test(label + ': extra.usedUsages=1', function () {{
    pm.expect({data_fn}.extra.usedUsages).to.eql(1);
  }});"""


def _LoungeJsHelpers() -> List[str]:
    """按 ``_LOUNGE_JS_ASSERT_EPASS_STATUS`` 决定是否注入 ``ePassStatus`` 断言（v1 无该字段）。"""
    return BuildFastTrackJsHelpersLines(assert_epass_status=_LOUNGE_JS_ASSERT_EPASS_STATUS)


CREATE_PAYLOAD_TEMPLATE: Final[str] = BuildEpassCreatePayload(FASTTRACK_CATEGORY)


def BuildFastTrackPassengers(*, adult_count: int, child_count: int) -> List[JsonObject]:
    """按预约人数生成 fastTrack ``passengers``；仅首位为 leadPassenger，姓名唯一且仅拉丁字母（无数字）。"""
    if adult_count < 0 or child_count < 0:
        raise ValueError("adult_count and child_count must be non-negative")
    if adult_count > len(FASTTRACK_ADULT_PASSENGER_NAMES):
        raise ValueError(
            f"adult_count={adult_count} exceeds configured names ({len(FASTTRACK_ADULT_PASSENGER_NAMES)})"
        )
    if child_count > len(FASTTRACK_CHILD_PASSENGER_NAMES):
        raise ValueError(
            f"child_count={child_count} exceeds configured names ({len(FASTTRACK_CHILD_PASSENGER_NAMES)})"
        )
    passenger_count = adult_count + child_count
    if passenger_count <= 0:
        raise ValueError("fastTrack passengers require at least one adult or child")

    passengers: List[JsonObject] = []
    for adult_index in range(adult_count):
        first_name, last_name = FASTTRACK_ADULT_PASSENGER_NAMES[adult_index]
        passengers.append(
            {
                "firstName": first_name,
                "lastName": last_name,
                "passengersType": 1,
                "leadPassenger": len(passengers) == 0,
            }
        )
    for child_index in range(child_count):
        first_name, last_name = FASTTRACK_CHILD_PASSENGER_NAMES[child_index]
        passengers.append(
            {
                "firstName": first_name,
                "lastName": last_name,
                "passengersType": 2,
                "leadPassenger": False,
            }
        )
    return passengers


def FastTrackPrebookingExtraDict(
    *,
    adult_count: int = DEFAULT_FASTTRACK_ADULT_COUNT,
    child_count: int = DEFAULT_FASTTRACK_CHILD_COUNT,
    include_transport_number: bool = True,
) -> JsonObject:
    """fastTrack 经典预约 / Bundle ``extra``（含 prebookingRequiredInfo、passengers；可选 ``transportNumber``，无 optionId）。"""
    passengers = BuildFastTrackPassengers(adult_count=adult_count, child_count=child_count)
    lead_passenger = passengers[0]
    prebooking_required_info: JsonObject = {
        "firstName": str(lead_passenger["firstName"]),
        "lastName": str(lead_passenger["lastName"]),
        "email": "auto.test@dragonpass.com",
        "phoneNumber": "8081966002",
        "callingCode": "44",
    }
    if include_transport_number:
        prebooking_required_info["transportNumber"] = "BA123"
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": prebooking_required_info,
        "passengers": passengers,
    }


def BuildFastTrackPrebookingExtra(
    *,
    omit_prebooking_required_info_field: Optional[str] = None,
    include_transport_number: bool = True,
    adult_count: int = DEFAULT_FASTTRACK_ADULT_COUNT,
    child_count: int = DEFAULT_FASTTRACK_CHILD_COUNT,
) -> JsonObject:
    """fastTrack 预约 / Bundle / membership 下单 ``extra``；可删 ``prebookingRequiredInfo`` 单字段（负向）。"""
    extra = FastTrackPrebookingExtraDict(
        adult_count=adult_count,
        child_count=child_count,
        include_transport_number=include_transport_number,
    )
    if omit_prebooking_required_info_field:
        info = extra.get("prebookingRequiredInfo")
        if isinstance(info, dict) and omit_prebooking_required_info_field in info:
            del info[omit_prebooking_required_info_field]
    return extra


def BuildFastTrackEpassPrebookingBody(
    *,
    omit_prebooking_required_info_field: Optional[str] = None,
    include_transport_number: bool = True,
) -> str:
    """``POST /v2/orders/fastTrack/ePasses/prebooking`` 请求体（与 P0 E02-S03 同构）。"""
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "ePassId": "{{ePassId}}",
            "extra": BuildFastTrackPrebookingExtra(
                omit_prebooking_required_info_field=omit_prebooking_required_info_field,
                include_transport_number=include_transport_number,
            ),
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildFastTrackBundleBody(
    *,
    omit_prebooking_required_info_field: Optional[str] = None,
    include_transport_number: bool = True,
) -> str:
    """``POST /v2/orders/fastTrack/ePasses/bundle`` 请求体（与 P0 E03-S02 同构）。"""
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "clientUserId": "{{$string.uuid}}",
            "extra": BuildFastTrackPrebookingExtra(
                omit_prebooking_required_info_field=omit_prebooking_required_info_field,
                include_transport_number=include_transport_number,
            ),
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildFastTrackMembershipPrebookingBody(
    *,
    omit_prebooking_required_info_field: Optional[str] = None,
    include_transport_number: bool = True,
    adult_count: int = DEFAULT_FASTTRACK_ADULT_COUNT,
) -> str:
    """``POST /v2/orders/fastTrack/memberships/prebooking`` 请求体。"""
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "membershipId": "{{membershipId}}",
            "extra": {
                **BuildFastTrackPrebookingExtra(
                    omit_prebooking_required_info_field=omit_prebooking_required_info_field,
                    include_transport_number=include_transport_number,
                    adult_count=adult_count,
                ),
                "cashPaymentApplied": False,
                "toUseEntitlementCount": adult_count,
                "toUseEntitlementDetail": {"cardholder": 1, "guest": 1},
            },
            "async": False,
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildFastTrackJsHelpersLines(
    *,
    assert_epass_status: bool = True,
    assert_create_extra_last_name: bool = True,
    assert_create_extra_available_usages: bool = True,
    assert_usage_used_usages_one: bool = True,
    assert_booking_counts: bool = True,
) -> List[str]:
    """与 ``historical_epass_service`` / lounge classic availability 链断言语义对齐的公共 JS（``ft*`` 前缀）。"""
    epass_status_active = _JsAssertEpassStatusActiveBlock() if assert_epass_status else ""
    epass_status_cancelled = _JsAssertEpassStatusCancelledBlock() if assert_epass_status else ""
    create_extra_last_name = _JsAssertCreateExtraLastNameBlock() if assert_create_extra_last_name else ""
    create_extra_available_usages = (
        _JsAssertCreateExtraAvailableUsagesBlock() if assert_create_extra_available_usages else ""
    )
    usage_used_usages_one = _JsAssertUsageUsedUsagesOneBlock() if assert_usage_used_usages_one else ""
    assert_booking_counts_js = "true" if assert_booking_counts else "false"
    cancel_msg_js = json.dumps(CANCEL_SUCCESS_MSG)
    cancel_retry_needle_js = json.dumps(CANCEL_RETRY_MSG_NEEDLE)
    create_first_name_js = json.dumps(CREATE_FIRST_NAME)
    create_last_name_js = json.dumps(CREATE_LAST_NAME)
    create_expiration_date_js = json.dumps(CREATE_EXPIRATION_DATE)
    create_available_usages_js = json.dumps(CREATE_AVAILABLE_USAGES)
    default_adult_count_js = json.dumps(DEFAULT_FASTTRACK_ADULT_COUNT)
    default_child_count_js = json.dumps(DEFAULT_FASTTRACK_CHILD_COUNT)
    adult_passenger_names_js = json.dumps(
        [{"firstName": first, "lastName": last} for first, last in FASTTRACK_ADULT_PASSENGER_NAMES]
    )
    child_passenger_names_js = json.dumps(
        [{"firstName": first, "lastName": last} for first, last in FASTTRACK_CHILD_PASSENGER_NAMES]
    )
    fast_track_resource_var = FASTTRACK_RESOURCE_ID_VAR
    runtime_helpers = BuildEpassRuntimeHelpersBlock(
        FASTTRACK_CATEGORY,
        extra_unset_env_keys=("fastTrackAvailabilityResourceId",),
    )
    module_helpers = BuildEpassExpectedModuleHelpersBlock(FASTTRACK_CATEGORY)
    assert_data_fn_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="ft",
        actual_expression="dataFn().clientUserId",
    )
    assert_data_extra_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="ft",
        actual_expression="data().extra.clientUserId",
    )
    assert_list_client_user = JsAssertRuntimeClientUserIdEquals(
        prefix="ft",
        actual_expression="cid",
        indent="      ",
    )
    js = runtime_helpers + module_helpers + rf"""function ftParseNonNegativeInt(value, fallbackValue) {{
  var n = parseInt(String(value), 10);
  if (isNaN(n) || n < 0) return fallbackValue;
  return n;
}}
var ftAdultPassengerNames = {adult_passenger_names_js};
var ftChildPassengerNames = {child_passenger_names_js};
function ftResolveFastTrackPassengerCounts() {{
  var adultCount = ftParseNonNegativeInt(pm.collectionVariables.get('fastTrackAdultCount'), {default_adult_count_js});
  var childCount = ftParseNonNegativeInt(pm.collectionVariables.get('fastTrackChildCount'), {default_child_count_js});
  if (adultCount + childCount <= 0) {{
    adultCount = {default_adult_count_js};
    childCount = {default_child_count_js};
  }}
  return {{ adultCount: adultCount, childCount: childCount }};
}}
function ftExpectedBookingCounts() {{
  var counts = ftResolveFastTrackPassengerCounts();
  return counts.adultCount + counts.childCount;
}}
function ftAssertBookingCounts(label) {{
  if (!{assert_booking_counts_js}) {{
    return;
  }}
  var env = pm.response.json();
  if (!env || env.code !== 0) {{
    return;
  }}
  var data = ftGetInnerData(env);
  var extra = (data && data.extra && typeof data.extra === 'object') ? data.extra : {{}};
  var expected = ftExpectedBookingCounts();
  var actual = extra.bookingCounts;
  pm.test(label + ': extra.bookingCounts | 期望=可用性 adultCount+childCount=' + expected + ' | 实际=' + String(actual), function () {{
    pm.expect(Object.prototype.hasOwnProperty.call(extra, 'bookingCounts'), 'extra.bookingCounts 字段存在').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.be.a('number');
    pm.expect(Number.isInteger(actual), 'extra.bookingCounts 为整数').to.eql(true);
    pm.expect(actual, 'extra.bookingCounts').to.eql(expected);
  }});
}}
function ftBuildFastTrackPassengers(adultCount, childCount) {{
  var passengers = [];
  var idx;
  if (adultCount > ftAdultPassengerNames.length) {{
    throw new Error('adultCount exceeds configured passenger names: ' + adultCount);
  }}
  if (childCount > ftChildPassengerNames.length) {{
    throw new Error('childCount exceeds configured passenger names: ' + childCount);
  }}
  for (idx = 0; idx < adultCount; idx++) {{
    passengers.push({{
      firstName: ftAdultPassengerNames[idx].firstName,
      lastName: ftAdultPassengerNames[idx].lastName,
      passengersType: 1,
      leadPassenger: passengers.length === 0
    }});
  }}
  for (idx = 0; idx < childCount; idx++) {{
    passengers.push({{
      firstName: ftChildPassengerNames[idx].firstName,
      lastName: ftChildPassengerNames[idx].lastName,
      passengersType: 2,
      leadPassenger: false
    }});
  }}
  return passengers;
}}
function ftResolveLeadPassenger(passengers) {{
  if (!passengers || !passengers.length) return null;
  var lead = passengers.filter(function (p) {{ return p && p.leadPassenger === true; }});
  return lead.length ? lead[0] : passengers[0];
}}
function ftSyncPrebookingPassengersBody() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var body = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (!body.extra || typeof body.extra !== 'object') body.extra = {{}};
    var counts = ftResolveFastTrackPassengerCounts();
    body.extra.passengers = ftBuildFastTrackPassengers(counts.adultCount, counts.childCount);
    var lead = ftResolveLeadPassenger(body.extra.passengers);
    if (lead) {{
      if (!body.extra.prebookingRequiredInfo || typeof body.extra.prebookingRequiredInfo !== 'object') {{
        body.extra.prebookingRequiredInfo = {{}};
      }}
      body.extra.prebookingRequiredInfo.firstName = lead.firstName;
      body.extra.prebookingRequiredInfo.lastName = lead.lastName;
    }}
    pm.request.body.raw = JSON.stringify(body, null, 2);
  }} catch (e) {{
    console.warn('ftSyncPrebookingPassengersBody:', e);
    throw e;
  }}
}}
function ftAssertPrebookingPassengersShape(label) {{
  pm.test(label + ': passengers 数量与可用性 adultCount+childCount 一致', function () {{
    var counts = ftResolveFastTrackPassengerCounts();
    var raw = pm.request.body && pm.request.body.raw;
    pm.expect(raw, label + ' request body').to.be.a('string').and.not.empty;
    var body = JSON.parse(pm.variables.replaceIn(String(raw)));
    pm.expect(body.extra.passengers).to.be.an('array');
    pm.expect(body.extra.passengers.length).to.eql(counts.adultCount + counts.childCount);
    var leadCount = body.extra.passengers.filter(function (p) {{ return p && p.leadPassenger === true; }}).length;
    pm.expect(leadCount, label + ' leadPassenger=true 仅 1 个').to.eql(1);
    var lead = ftResolveLeadPassenger(body.extra.passengers);
    pm.expect(body.extra.prebookingRequiredInfo, label + ' prebookingRequiredInfo').to.be.an('object');
    pm.expect(body.extra.prebookingRequiredInfo.firstName).to.eql(lead.firstName);
    pm.expect(body.extra.prebookingRequiredInfo.lastName).to.eql(lead.lastName);
    var seen = {{}};
    body.extra.passengers.forEach(function (p, idx) {{
      pm.expect(p.firstName, 'passengers[' + idx + '].firstName').to.match(/^[A-Za-z ]+$/);
      pm.expect(p.lastName, 'passengers[' + idx + '].lastName').to.match(/^[A-Za-z ]+$/);
      var key = String(p.firstName) + '|' + String(p.lastName);
      pm.expect(seen[key], 'passengers 姓名重复: ' + key).to.be.undefined;
      seen[key] = true;
    }});
  }});
}}
function ftIsBusinessSuccess(env) {{
  if (!env || typeof env !== 'object') return false;
  if (!Object.prototype.hasOwnProperty.call(env, 'code')) return true;
  var c = env.code;
  return c === 0 || c === 1 || c === '0' || c === '1';
}}
function ftGetInnerData(root) {{
  if (!root || typeof root !== 'object') return null;
  var d = root.data;
  if (d !== undefined && d !== null && typeof d === 'object' && !Array.isArray(d)) {{
    return d;
  }}
  return d;
}}
function ftAssertEpassModuleRequired(data, ctx) {{
  pm.expect(data, ctx + ' data').to.be.an('object');
  pm.expect(data.module, ctx + ' module').to.eql(ftExpectedModule());
}}
function ftAssertEpassModuleIfPresent(data, ctx) {{
  if (!data || typeof data !== 'object') return;
  if (Object.prototype.hasOwnProperty.call(data, 'module')) {{
    pm.expect(data.module, ctx + ' module').to.eql(ftExpectedModule());
  }}
}}
function ftResolveEPassIdFromRoot(data) {{
  if (!data || typeof data !== 'object') return null;
  var direct = data.ePassId || data.epassId;
  if (direct) return direct;
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    return extra.ePassId || extra.epassId || null;
  }}
  return null;
}}
function ftResolveEPassId(extra) {{
  if (!extra || typeof extra !== 'object') return null;
  return extra.ePassId || extra.epassId || null;
}}
function ftResolveOptionId(data) {{
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
var ftOrderStatusActiveOrProcessing = [1, 5];
function ftFailIfOrderStatus10(status, label) {{
  if (status === 10) {{
    pm.expect.fail(label + ': 订单 status=10 FAILED');
  }}
}}
function ftExpectOrderStatusActiveOrProcessing(label, status) {{
  ftFailIfOrderStatus10(status, label);
  pm.expect(ftOrderStatusActiveOrProcessing, label + ' status').to.include(status);
}}
function ftSyncResourceIdFromOrderResponse(label, actual) {{
  pm.expect(actual, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  var fromAvail = pm.collectionVariables.get('fastTrackAvailabilityResourceId');
  if (fromAvail && String(fromAvail).trim() && actual !== fromAvail) {{
    console.warn(
      label + ': fastTrack 订单 resourceId=' + actual + ' 与可用性请求 ' + fromAvail
      + ' 不一致（以响应 canonical id 为准，已回写 fastTrackResourceId）'
    );
  }}
  pm.collectionVariables.set('{fast_track_resource_var}', String(actual));
}}
function ftExpectResourceIdMatch(label, actual) {{
  ftSyncResourceIdFromOrderResponse(label, actual);
}}
function ftExpectOptionIdMatch(label, actual) {{
  if (!actual) return;
  pm.expect(actual, label + ' optionId').to.be.a('string').and.not.empty;
}}
function ftSaveCreateIds(data) {{
  if (!data || typeof data !== 'object') return;
  ftCaptureClientUserIdAfterSend(data);
  if (data.orderId && !ftIsUnresolvedPlaceholder(data.orderId)) {{
    ftSetVar('purchaseOrderId', String(data.orderId));
  }}
  var extra = data.extra;
  if (extra && typeof extra === 'object') {{
    var ep = ftResolveEPassId(extra);
    if (ep && !ftIsUnresolvedPlaceholder(ep)) ftSetVar('ePassId', String(ep));
  }}
}}
function ftSaveAvailabilityRequestFields() {{
  try {{
    var raw = pm.request.body && pm.request.body.raw;
    if (!raw) return;
    var reqBody = JSON.parse(pm.variables.replaceIn(String(raw)));
    if (reqBody && reqBody.prebookingDate) {{
      pm.collectionVariables.set('prebookingDate', String(reqBody.prebookingDate));
    }}
    if (reqBody && reqBody.resourceId) {{
      pm.collectionVariables.set('fastTrackAvailabilityResourceId', String(reqBody.resourceId));
    }}
    var adultCount = ftParseNonNegativeInt(reqBody && reqBody.adultCount, {default_adult_count_js});
    var childCount = ftParseNonNegativeInt(reqBody && reqBody.childCount, {default_child_count_js});
    pm.collectionVariables.set('fastTrackAdultCount', String(adultCount));
    pm.collectionVariables.set('fastTrackChildCount', String(childCount));
  }} catch (e) {{
    console.warn('ftSaveAvailabilityRequestFields:', e);
  }}
}}
function ftResolveListItemField(item, rootKey, extraKey) {{
  if (!item || typeof item !== 'object') return null;
  if (Object.prototype.hasOwnProperty.call(item, rootKey)) return item[rootKey];
  var ex = item.extra;
  if (ex && typeof ex === 'object') {{
    if (Object.prototype.hasOwnProperty.call(ex, extraKey)) return ex[extraKey];
    if (Object.prototype.hasOwnProperty.call(ex, rootKey)) return ex[rootKey];
  }}
  return null;
}}
function ftResolveTransportHubName(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubName')) {{
    return ex.transportHubName;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubName')) return item.transportHubName;
  return undefined;
}}
function ftResolveTransportHubId(item) {{
  if (!item || typeof item !== 'object') return undefined;
  var ex = item.extra;
  if (ex && typeof ex === 'object' && Object.prototype.hasOwnProperty.call(ex, 'transportHubId')) {{
    return ex.transportHubId;
  }}
  if (Object.prototype.hasOwnProperty.call(item, 'transportHubId')) return item.transportHubId;
  return undefined;
}}
function ftSavePrebookingToken(data) {{
  if (data && data.prebookingToken) {{
    pm.collectionVariables.set('prebookingToken', String(data.prebookingToken));
  }}
}}
function ftSaveUsageOrderId(data) {{
  if (data && data.orderId) {{
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }}
}}
function ftAssertHttpBusinessOk(label) {{
  pm.test(label + ': 业务成功', function () {{
    pm.expect(ftIsBusinessSuccess(pm.response.json())).to.be.true;
  }});
}}
function ftResponseHttpCode(res) {{
  if (!res) return 0;
  var raw = res.code;
  if (raw === undefined || raw === null) raw = res.status;
  if (raw === undefined || raw === null) raw = res.statusCode;
  if (raw === undefined || raw === null) raw = res.responseCode;
  var n = parseInt(String(raw), 10);
  return isNaN(n) ? 0 : n;
}}
function ftIsCancelResponseSuccess(res, env) {{
  if (!env || typeof env !== 'object') return false;
  var httpCode = ftResponseHttpCode(res);
  if (httpCode && httpCode !== 200) return false;
  if (!ftIsBusinessSuccess(env)) return false;
  var msg = env.msg || env.message;
  return msg === {cancel_msg_js};
}}
function ftIsCancelResponseRetryable(env) {{
  if (!env || typeof env !== 'object') return false;
  var msg = String(env.msg || env.message || '');
  if (msg.indexOf({cancel_retry_needle_js}) >= 0) return true;
  if (msg.indexOf('does not allow cancellation') >= 0) return true;
  if (env.errCode === '500.041.006' || env.errCode === '500.071.016' || env.errCode === '500.051.029') return true;
  return false;
}}
function ftCancelDoneVar(orderIdVar) {{
  return 'ftCancelDone_' + orderIdVar;
}}
function ftMarkCancelDone(orderIdVar) {{
  pm.collectionVariables.set(ftCancelDoneVar(orderIdVar), '1');
}}
function ftIsCancelAlreadyDone(orderIdVar) {{
  return pm.collectionVariables.get(ftCancelDoneVar(orderIdVar)) === '1';
}}
function ftClearCancelDone(orderIdVar) {{
  pm.collectionVariables.unset(ftCancelDoneVar(orderIdVar));
}}
function ftSetNextRequestByName(reqName) {{
  if (!reqName) return;
  var setter = (typeof postman !== 'undefined' && postman.setNextRequest)
    ? postman.setNextRequest.bind(postman)
    : (pm.execution && pm.execution.setNextRequest
      ? pm.execution.setNextRequest.bind(pm.execution)
      : null);
  if (setter) setter(reqName);
}}
function ftPrerequestSkipCancelIfDone(orderIdVar, skipToRequestName) {{
  if (ftIsCancelAlreadyDone(orderIdVar) && skipToRequestName) {{
    ftSetNextRequestByName(skipToRequestName);
  }}
}}
function ftAssertCancelEnvelope(label, env) {{
  pm.test(label + ': code=0 取消业务成功', function () {{
    pm.expect(env && env.code, 'code').to.eql(0);
  }});
  pm.test(label + ': msg=The order was cancelled successfully', function () {{
    var msg = env && (env.msg || env.message);
    pm.expect(msg, '取消响应 msg').to.eql({cancel_msg_js});
  }});
}}
function ftCancelOrderAttempt(label, orderIdVar, attemptNo, maxAttempts, skipToRequestName) {{
  if (ftIsCancelAlreadyDone(orderIdVar)) {{
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
  if (ftIsCancelResponseSuccess(pm.response, env0)) {{
    ftMarkCancelDone(orderIdVar);
    ftAssertCancelEnvelope(label, env0);
    if (skipToRequestName && attemptNo < maxAttempts) {{
      ftSetNextRequestByName(skipToRequestName);
    }}
    return;
  }}
  if (ftIsCancelResponseRetryable(env0) && attemptNo < maxAttempts) {{
    pm.test(label + ': 第 ' + attemptNo + ' 次失败可重试', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  pm.test(label + ': 取消失败', function () {{
    pm.expect.fail(
      label + ': attempt ' + attemptNo + '/' + maxAttempts + ' env=' + JSON.stringify(env0)
    );
  }});
}}
function ftCancelOrderAttemptWithPoll(label, orderIdVar, attemptNo, maxAttempts, skipToRequestName) {{
  if (ftIsCancelAlreadyDone(orderIdVar)) {{
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
  if (ftIsCancelResponseSuccess(pm.response, env0)) {{
    ftMarkCancelDone(orderIdVar);
    ftAssertCancelEnvelope(label, env0);
    return;
  }}
  if (ftIsCancelResponseRetryable(env0) && attemptNo < maxAttempts) {{
    pm.test(label + ': 第 ' + attemptNo + ' 次失败可重试', function () {{ pm.expect(true).to.be.true; }});
    return;
  }}
  if (ftIsCancelResponseRetryable(env0)) {{
    pm.test(label + ': 取消未就绪（收尾警告，不阻断 PII 主路径）', function () {{
      console.warn(label + ': last cancel env=' + JSON.stringify(env0));
      pm.expect(true).to.be.true;
    }});
    return;
  }}
  pm.test(label + ': 取消失败', function () {{
    pm.expect.fail(
      label + ': attempt ' + attemptNo + '/' + maxAttempts + ' env=' + JSON.stringify(env0)
    );
  }});
}}
function ftExpectedCreateExtra() {{
  return {{
    firstName: {create_first_name_js},
    lastName: {create_last_name_js},
    expirationDate: {create_expiration_date_js},
    availableUsages: {create_available_usages_js}
  }};
}}
function ftAssertExtraMatchesCreateInput(label, extra) {{
  pm.test(label + ': extra.firstName 与入参一致', function () {{
    pm.expect(extra.firstName).to.eql(ftExpectedCreateExtra().firstName);
  }});
{create_extra_last_name}
  pm.test(label + ': extra.expirationDate 与入参一致', function () {{
    pm.expect(extra.expirationDate).to.eql(ftExpectedCreateExtra().expirationDate);
  }});
{create_extra_available_usages}
}}
function ftAssertCreateCoreFields(label) {{
  var dataFn = function () {{ return ftGetInnerData(pm.response.json()); }};
  ftSaveCreateIds(dataFn());
  pm.test(label + ': module=epassModule', function () {{
    ftAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': category=2', function () {{
    pm.expect(dataFn().category).to.eql(2);
  }});
  pm.test(label + ': clientUserId 回显一致', function () {{
    var actual = dataFn().clientUserId;
    var saved = ftGetVar('clientUserId');
    pm.expect(actual, '响应 clientUserId').to.be.a('string').and.not.empty;
    pm.expect(ftIsUnresolvedPlaceholder(actual), '响应不是未解析模板').to.be.false;
    pm.expect(ftIsUuid(actual), '响应 clientUserId 为 UUID').to.be.true;
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
  ftAssertExtraMatchesCreateInput(label, dataFn().extra);
  pm.test(label + ': extra.ePassId 非空', function () {{
    pm.expect(ftResolveEPassId(dataFn().extra)).to.be.ok;
  }});
  pm.test(label + ': extra.allowedResources 存在', function () {{
    pm.expect(dataFn().extra.allowedResources).to.be.an('object');
  }});
  pm.test(label + ': 写入 ePassId/purchaseOrderId', function () {{
    pm.expect(ftGetVar('ePassId')).to.be.ok;
    pm.expect(ftGetVar('purchaseOrderId')).to.be.ok;
  }});
}}
function ftAssertUserListContains(label) {{
  pm.test(label + ': ePassesList 含 ePassId', function () {{
    var data = ftGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    pm.expect(data.ePassesList).to.be.an('array');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    pm.expect(hit.length, '未找到 ePassId=' + target).to.be.above(0);
  }});
  pm.test(label + ': 列表项 module=epassModule（若存在）', function () {{
    var data = ftGetInnerData(pm.response.json());
    var target = pm.collectionVariables.get('ePassId');
    var hit = data.ePassesList.filter(function (x) {{ return x && x.ePassId === target; }});
    if (hit[0] && Object.prototype.hasOwnProperty.call(hit[0], 'module')) {{
      pm.expect(hit[0].module).to.eql(ftExpectedModule());
    }}
  }});
}}
function ftAssertSearchPurchaseDetails(label, assertEpassModule, matchCreateInput, expectedStatus, expectedUsedUsages) {{
  var dataFn = function () {{ return ftGetInnerData(pm.response.json()); }};
  var status = (expectedStatus !== undefined && expectedStatus !== null) ? expectedStatus : 1;
  var usedUsages = (expectedUsedUsages !== undefined && expectedUsedUsages !== null) ? expectedUsedUsages : 0;
  if (assertEpassModule !== false) {{
    pm.test(label + ': module=epassModule', function () {{
      ftAssertEpassModuleRequired(dataFn(), label);
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
    pm.expect(ftResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
{epass_status_active}
  pm.test(label + ': extra.usedUsages=' + usedUsages, function () {{
    pm.expect(dataFn().extra.usedUsages).to.eql(usedUsages);
  }});
  if (matchCreateInput !== false) {{
    ftAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function ftAssertOrderListPagination(label, allowEmpty, expectEpassModule) {{
  pm.test(label + ': pagination 结构', function () {{
    var data = ftGetInnerData(pm.response.json());
    pm.expect(data.pagination).to.be.an('object');
    ['pageSize', 'pageNumber', 'totalNumber'].forEach(function (k) {{
      pm.expect(data.pagination, 'pagination.' + k).to.have.property(k);
    }});
  }});
  pm.test(label + ': orders 为数组', function () {{
    pm.expect(ftGetInnerData(pm.response.json()).orders).to.be.an('array');
  }});
  if (allowEmpty) {{
    pm.test(label + ': 创建后 orders 可为空（canary doc gap）', function () {{
      pm.expect(ftGetInnerData(pm.response.json()).orders).to.be.an('array');
    }});
  }}
  if (expectEpassModule) {{
    pm.test(label + ': 列表项 module=epassModule（若存在 module 字段）', function () {{
      var orders = ftGetInnerData(pm.response.json()).orders || [];
      var mod = ftExpectedModule();
      orders.forEach(function (item, idx) {{
        if (item && Object.prototype.hasOwnProperty.call(item, 'module')) {{
          pm.expect(item.module, 'orders[' + idx + '].module').to.eql(mod);
        }}
      }});
    }});
  }}
}}
function ftAssertAvailabilitySuccess(label) {{
  ftSaveAvailabilityRequestFields();
  pm.test(label + ': available=true', function () {{
    pm.expect(ftGetInnerData(pm.response.json()).available).to.eql(true);
  }});
  pm.test(label + ': prebookingToken 非空', function () {{
    var data = ftGetInnerData(pm.response.json());
    pm.expect(data.prebookingToken).to.be.a('string').and.not.empty;
    ftSavePrebookingToken(data);
  }});
}}
function ftAssertUsageOrderCreateSuccess(label, requireExistingEPassId, allowedStatuses) {{
  allowedStatuses = allowedStatuses || ftOrderStatusActiveOrProcessing;
  var data = function () {{ return ftGetInnerData(pm.response.json()); }};
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
  pm.test(label + ': module=epassModule', function () {{ ftAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': orderId 非空', function () {{
    pm.expect(data().orderId).to.be.a('string').and.not.empty;
    ftSaveUsageOrderId(data());
  }});
  pm.test(label + ': clientUserId 与注册会籍一致', function () {{
{assert_data_extra_client_user}
  }});
  pm.test(label + ': ePassId 与前面一致', function () {{
    var ep = ftResolveEPassIdFromRoot(data());
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
{usage_used_usages_one}
  pm.test(label + ': extra.prebookingDate 与可用性入参一致', function () {{
    var expected = pm.collectionVariables.get('prebookingDate');
    var actual = data().extra.prebookingDate;
    pm.expect(actual).to.be.a('string').and.not.empty;
    if (expected && String(expected).trim()) {{
      pm.expect(actual).to.eql(expected);
    }}
  }});
  pm.test(label + ': extra.resourceId 与 resourceId 一致', function () {{
    ftExpectResourceIdMatch(label, data().extra.resourceId);
  }});
}}
function ftAssertUsageOrderListItemCore(label, item) {{
  pm.expect(item.category, label + ' category').to.eql(2);
  pm.expect(item.module, label + ' module').to.eql(ftExpectedModule());
  var rid = ftResolveListItemField(item, 'resourceId', 'resourceId');
  pm.expect(rid, label + ' resourceId 非空').to.be.a('string').and.not.empty;
  ftExpectResourceIdMatch(label, rid);
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
function ftAssertUsageOrderInListActive(label) {{
  ftAssertHttpBusinessOk(label);
  ftAssertOrderListPagination(label, false, true);
  ftAssertNoOtherModuleInEpassList(label);
  pm.test(label + ': orders 含 usageOrderId 且 status=1', function () {{
    var data = ftGetInnerData(pm.response.json());
    var oid = pm.collectionVariables.get('usageOrderId');
    pm.expect(data.orders).to.be.an('array');
    pm.expect(data.orders.length, 'orders 不应为空').to.be.above(0);
    var hit = data.orders.filter(function (o) {{ return o && o.orderId === oid; }});
    pm.expect(hit.length, '未找到 usageOrderId=' + oid).to.be.above(0);
    var item = hit[0];
    pm.expect(item.status).to.eql(1);
    ftAssertUsageOrderListItemCore(label, item);
    if (Object.prototype.hasOwnProperty.call(item, 'orderCancelledDate')) {{
      pm.expect(item.orderCancelledDate).to.eql(null);
    }}
    var used = ftResolveListItemField(item, 'usedUsages', 'usedUsages');
    pm.expect(used, label + ' usedUsages').to.eql(1);
    var usageDate = ftResolveListItemField(item, 'usageDate', 'usageDate');
    if (usageDate !== undefined) {{
      pm.expect(usageDate).to.eql(null);
    }}
    var ep = ftResolveEPassIdFromRoot(item);
    if (ep) {{
      pm.expect(ep).to.eql(pm.collectionVariables.get('ePassId'));
    }}
    var cid = ftResolveListItemField(item, 'clientUserId', 'clientUserId');
    if (cid) {{
{assert_list_client_user}
    }}
  }});
}}
function ftAssertPrebookingOrderSuccess(label) {{
  ftAssertUsageOrderCreateSuccess(label, true);
}}
function ftAssertBundleOrderSuccess(label) {{
  ftAssertUsageOrderCreateSuccess(label, false);
  pm.test(label + ': 写入 usageOrderId', function () {{
    pm.expect(pm.collectionVariables.get('usageOrderId')).to.be.ok;
  }});
}}
function ftAssertUsageDetailsCore(label, expectCancelled) {{
  var data = function () {{ return ftGetInnerData(pm.response.json()); }};
  pm.test(label + ': orderId 与 usageOrderId 一致', function () {{
    pm.expect(data().orderId).to.eql(pm.collectionVariables.get('usageOrderId'));
  }});
  pm.test(label + ': module=epassModule', function () {{ ftAssertEpassModuleRequired(data(), label); }});
  pm.test(label + ': category=2', function () {{ pm.expect(data().category).to.eql(2); }});
  pm.test(label + ': extra.usedUsages=1', function () {{
    pm.expect(data().extra.usedUsages).to.eql(1);
  }});
  pm.test(label + ': extra.usageDate=null', function () {{ pm.expect(data().extra.usageDate).to.eql(null); }});
  pm.test(label + ': ePassId 一致', function () {{
    pm.expect(ftResolveEPassIdFromRoot(data())).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  pm.test(label + ': extra.clientUserId 一致', function () {{
{assert_data_extra_client_user}
  }});
    pm.test(label + ': extra.resourceId 一致', function () {{
    pm.expect(data().extra.resourceId).to.eql(pm.collectionVariables.get('{fast_track_resource_var}'));
  }});
  ftAssertBookingCounts(label);
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
      pm.expect(ftOrderStatusActiveOrProcessing, label + ' status').to.include(st);
    }});
    pm.test(label + ': orderCancelledDate=null', function () {{
      pm.expect(data().orderCancelledDate).to.eql(null);
    }});
  }}
}}
function ftAssertNoOtherModuleInEpassList(label) {{
  pm.test(label + ': module=epassModule 列表不含 otherModule 数据', function () {{
    pm.expect(ftIsBusinessSuccess(pm.response.json())).to.be.true;
    var data = ftGetInnerData(pm.response.json());
    if (!data || typeof data !== 'object') return;
    if (!Array.isArray(data.orders)) return;
    var other = ftOtherModule();
    var hits = data.orders.filter(function (o) {{ return o && o.module === other; }});
    pm.expect(hits.length, 'epassModule orders 不应含 otherModule=' + other + ' 条目').to.eql(0);
  }});
}}
function ftAssertNoFastTrackReturnedWithOtherModuleFilter(label) {{
  pm.test(label + ': otherModule 不返回 fastTrack 数据', function () {{
    var env = pm.response.json();
    if (env && env.code === -1) {{
      console.warn(label + ': otherModule 返回业务失败，视为隔离通过 errCode=' + env.errCode);
      return;
    }}
    pm.expect(ftIsBusinessSuccess(env), label + ' business success 或 code=-1').to.be.true;
    var data = ftGetInnerData(env);
    if (data === null || data === undefined) return;
    if (typeof data !== 'object') return;
    var expectedUsage = pm.collectionVariables.get('usageOrderId');
    var expectedPurchase = pm.collectionVariables.get('purchaseOrderId');
    var expectedEPass = pm.collectionVariables.get('ePassId');
    var fastTrackMod = ftExpectedModule();
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
      var loungeItems = data.orders.filter(function (o) {{ return o && o.module === fastTrackMod; }});
      pm.expect(loungeItems.length, 'otherModule orders 不应含 epassModule 条目').to.eql(0);
      return;
    }}
    pm.expect(data.module, 'otherModule details 不应返回 epassModule').to.not.eql(fastTrackMod);
    if (expectedUsage && data.orderId) {{
      pm.expect(data.orderId, 'otherModule details 不应返回 lounge usageOrderId').to.not.eql(expectedUsage);
    }}
    var ep = ftResolveEPassIdFromRoot(data);
    if (expectedEPass && ep && data.module === fastTrackMod) {{
      pm.expect(ep, 'otherModule details 不应返回 fastTrack ePassId').to.not.eql(expectedEPass);
    }}
  }});
}}
function ftAssertUsageListContainsCancelled(label) {{
  pm.test(label + ': orders 含 usageOrderId 且 status=3', function () {{
    var data = ftGetInnerData(pm.response.json());
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
      pm.expect(hit[0].module).to.eql(ftExpectedModule());
    }}
  }});
}}
function ftAssertSearchActiveAfterUsageCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return ftGetInnerData(pm.response.json()); }};
  pm.test(label + ': module=epassModule', function () {{
    ftAssertEpassModuleRequired(dataFn(), label);
  }});
  pm.test(label + ': status=1 CONFIRMED（MS 单未取消）', function () {{
    pm.expect(dataFn().status).to.eql(1);
  }});
  pm.test(label + ': purchaseOrderId 仍可查', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
{epass_status_active}
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(ftResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    ftAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
function ftAssertSearchCancelledAfterPurchaseCancel(label, matchCreateInput) {{
  var dataFn = function () {{ return ftGetInnerData(pm.response.json()); }};
  pm.test(label + ': status=3 CANCELLED', function () {{
    pm.expect(dataFn().status).to.eql(3);
  }});
{epass_status_cancelled}
  pm.test(label + ': orderId 与 purchaseOrderId 一致', function () {{
    pm.expect(dataFn().orderId).to.eql(pm.collectionVariables.get('purchaseOrderId'));
  }});
  pm.test(label + ': extra.ePassId 一致', function () {{
    pm.expect(ftResolveEPassId(dataFn().extra)).to.eql(pm.collectionVariables.get('ePassId'));
  }});
  if (matchCreateInput !== false) {{
    ftAssertExtraMatchesCreateInput(label, dataFn().extra);
  }}
}}
""".strip()
    return [ln for ln in js.split("\n")]


def Lines_Auth() -> List[str]:
    return [
        "ftAssertHttpBusinessOk('Auth');",
        "pm.test('Auth: accessToken 写入集合变量', function () {",
        "  var d = ftGetInnerData(pm.response.json());",
        "  var t = (d && (d.accessToken || d.token || d.access_token));",
        "  pm.expect(t).to.be.ok;",
        "  pm.expect(pm.collectionVariables.get('accessToken')).to.be.ok;",
        "});",
    ]


def AvailabilityBody(*, with_epass: bool, add_days: int = PREBOOKING_ADD_DAYS_START) -> str:
    body: JsonObject = {
        "module": EPASS_MODULE_DEFAULT,
        "resourceId": "{{fastTrackResourceId}}",
        "prebookingDate": PrebookingDateApifoxExpr(add_days),
        "adultCount": DEFAULT_FASTTRACK_ADULT_COUNT,
        "childCount": DEFAULT_FASTTRACK_CHILD_COUNT,
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


def Prerequest_InitFastTrackPassengerCounts() -> List[str]:
    return [
        f"pm.collectionVariables.set('fastTrackAdultCount', '{DEFAULT_FASTTRACK_ADULT_COUNT}');",
        f"pm.collectionVariables.set('fastTrackChildCount', '{DEFAULT_FASTTRACK_CHILD_COUNT}');",
    ]


def Prerequest_SyncPrebookingPassengersBody() -> List[str]:
    return ["ftSyncPrebookingPassengersBody();"]


def Prerequest_ClearCancelDoneFlags() -> List[str]:
    return [
        "pm.collectionVariables.unset('ftCancelDone_usageOrderId');",
        "pm.collectionVariables.unset('ftCancelDone_purchaseOrderId');",
    ]


def Prerequest_NewClientUserId() -> List[str]:
    return [
        *Prerequest_ClearCancelDoneFlags(),
        "ftUnsetVar('clientUserId');",
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
    helpers_source_key: Optional[str] = None,
    max_attempts: Optional[int] = None,
    cancel_fn: str = "ftCancelOrderAttempt",
) -> List[JsonObject]:
    cancel_body = body if body is not None else CancelOrderBody(order_id_var)
    items: List[JsonObject] = []
    max_att = int(max_attempts or GENERATED_CANCEL_ATTEMPTS)
    if max_att < 1:
        raise ValueError(f"cancel max_attempts 须 >= 1，实际={max_att}")
    skip_json = json.dumps(skip_to_request_name) if skip_to_request_name else "null"
    source_key = str(helpers_source_key or HELPERS_SOURCE_KEY).strip() or HELPERS_SOURCE_KEY
    fn_name = str(cancel_fn or "ftCancelOrderAttempt").strip() or "ftCancelOrderAttempt"
    for attempt in range(1, max_att + 1):
        step_id = step_prefix if attempt == 1 else f"{step_prefix}-R{attempt}"
        attempt_purpose = purpose if attempt == 1 else f"{purpose}（第{attempt}次）"
        prerequest: Optional[List[str]] = None
        if attempt > 1 and skip_to_request_name:
            prerequest = [
                f"ftPrerequestSkipCancelIfDone('{order_id_var}', {skip_json});",
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
                helpers_source_key=source_key,
                test_lines=Lines_Step(
                    step_id,
                    [
                        f"{fn_name}('{step_id}', '{order_id_var}', {attempt}, "
                        f"{max_att}, {skip_json});",
                    ],
                ),
            )
        )
    return items


def Prerequest_ResetForPrebooking() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        *Prerequest_InitFastTrackPassengerCounts(),
        "ftUnsetVar('clientUserId');",
        "ftUnsetVar('ePassId');",
        "ftUnsetVar('purchaseOrderId');",
        "ftUnsetVar('usageOrderId');",
        "ftUnsetVar('prebookingToken');",
    ]


def Prerequest_ResetForBundle() -> List[str]:
    return [
        *Prerequest_ClearCancelRetryAttempts(),
        *Prerequest_InitFastTrackPassengerCounts(),
        "ftUnsetVar('clientUserId');",
        "ftUnsetVar('ePassId');",
        "ftUnsetVar('purchaseOrderId');",
        "ftUnsetVar('usageOrderId');",
        "ftUnsetVar('prebookingToken');",
    ]


