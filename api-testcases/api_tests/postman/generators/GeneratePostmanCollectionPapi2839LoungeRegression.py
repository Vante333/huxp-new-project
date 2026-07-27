"""
生成 PAPI-2839 · Lounge 姓名正则品类隔离回归 Postman Collection v2.1 JSON。

PAPI-2839 仅收紧 **FastTrack** ``prebookingRequiredInfo`` / ``passengers[]`` 姓名为 ``^[A-Za-z ]+$``；
**Lounge** 仍沿用 ``^[A-Za-z -]+$``（连字符等 FT 非法、Lounge 合法样本在三接口应可下单）。

三条正向回归（各 1 次可用性 + 1 次下单 + 取消订单）：

- ``POST /v2/orders/lounges/ePasses/prebooking`` · lastName ``Jean-Pierre``
- ``POST /v2/orders/lounges/ePasses/bundle`` · firstName ``Mary-Jane``
- ``POST /v2/orders/lounges/memberships/prebooking`` · lastName ``Anne-Marie``

用法（仓库根目录）::

    python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionPapi2839LoungeRegression.py
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Literal, Optional, Sequence

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
from GeneratePostmanCollectionLoungeEpass import (
    AvailabilityBody,
    BuildCancelWithRetryBlock,
    BuildLoungeJsHelpersLines,
    CREATE_PAYLOAD_TEMPLATE,
    DEFAULT_LOUNGE_RESOURCE_ID,
    EPASS_MODULE_DEFAULT,
    LOUNGE_RESOURCE_ID_VAR,
    Lines_Auth,
    Prerequest_NewClientUserId,
    Prerequest_SyncPrebookingDateFromApifox,
)

JsonObject = Dict[str, Any]
OrderApiKind = Literal["epass_prebooking", "bundle", "membership_prebooking"]

OUT_NAME: Final[str] = "PAPI-2839-Lounge-NameRegex-Regression-P1.postman_collection.json"

FT_NAME_REGEX_JS: Final[str] = r"^[A-Za-z ]+$"
LOUNGE_NAME_REGEX_JS: Final[str] = r"^[A-Za-z -]+$"

CONTACT_EMAIL: Final[str] = "auto.test@dragonpass.com"
CONTACT_PHONE: Final[str] = "8081966002"
CONTACT_CALLING_CODE: Final[str] = "44"

MEMBERSHIP_REGISTER_PAYLOAD: Final[str] = json.dumps(
    {
        "clientUserId": "{{clientUserId}}",
        "firstName": "Auto",
        "lastName": "Smith",
        "phoneNumber": CONTACT_PHONE,
        "callingCode": CONTACT_CALLING_CODE,
        "email": "p2839_lounge_{{$timestamp}}@dragonpass.com",
        "expirationDate": "2027-12-31T10:10:33+00:00",
    },
    ensure_ascii=False,
    indent=2,
)


@dataclass(frozen=True)
class LoungeRegressionCase:
    """Lounge 品类隔离回归：FT 非法、Lounge 合法姓名样本。"""

    purpose: str
    step_key: str
    first_name: str
    last_name: str
    api_kind: OrderApiKind


REGRESSION_CASES: Final[Sequence[LoungeRegressionCase]] = (
    LoungeRegressionCase(
        "lastName 含连字符 Jean-Pierre（FT 拒 / Lounge 收）",
        "REG01",
        "John",
        "Jean-Pierre",
        "epass_prebooking",
    ),
    LoungeRegressionCase(
        "firstName 含连字符 Mary-Jane（FT 拒 / Lounge 收）",
        "REG02",
        "Mary-Jane",
        "Smith",
        "bundle",
    ),
    LoungeRegressionCase(
        "lastName 含连字符 Anne-Marie（FT 拒 / Lounge 收）",
        "REG03",
        "John",
        "Anne-Marie",
        "membership_prebooking",
    ),
)


def BuildLoungePrebookingExtra(*, first_name: str, last_name: str) -> JsonObject:
    return {
        "prebookingToken": "{{prebookingToken}}",
        "prebookingRequiredInfo": {
            "firstName": first_name,
            "lastName": last_name,
            "email": CONTACT_EMAIL,
            "phoneNumber": CONTACT_PHONE,
            "callingCode": CONTACT_CALLING_CODE,
        },
    }


def BuildOrderBody(case: LoungeRegressionCase) -> str:
    extra = BuildLoungePrebookingExtra(first_name=case.first_name, last_name=case.last_name)
    payload: JsonObject
    if case.api_kind == "epass_prebooking":
        payload = {
            "module": EPASS_MODULE_DEFAULT,
            "ePassId": "{{ePassId}}",
            "extra": extra,
            "async": False,
        }
    elif case.api_kind == "bundle":
        payload = {
            "module": EPASS_MODULE_DEFAULT,
            "clientUserId": "{{clientUserId}}",
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
                "toUseEntitlementCount": 1,
            },
            "async": False,
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def BuildMembershipAvailabilityBody() -> str:
    return json.dumps(
        {
            "module": EPASS_MODULE_DEFAULT,
            "resourceId": "{{loungeResourceId}}",
            "prebookingDate": "{{prebookingDate}}",
            "adultCount": 1,
            "childCount": 0,
            "membershipId": "{{membershipId}}",
        },
        ensure_ascii=False,
        indent=2,
    )


def BuildP2839LoungeJsHelpersLines() -> List[str]:
    lounge_regex_js = json.dumps(LOUNGE_NAME_REGEX_JS)
    ft_regex_js = json.dumps(FT_NAME_REGEX_JS)
    js = rf"""function p39LoungeSyncCredentialVarsFromEnv() {{
  ['baseUrl', 'ProgramID', 'clientId', 'secret', 'x-version'].forEach(function (key) {{
    var v = pm.variables.get(key);
    if (v === undefined || v === null) return;
    v = String(v).trim();
    if (v && v.indexOf('{{{{') < 0) pm.collectionVariables.set(key, v);
  }});
}}
function p39LoungeSyncLoungeResourceIdFromEnv() {{
  var rid = pm.variables.get('{LOUNGE_RESOURCE_ID_VAR}');
  if (rid === undefined || rid === null) rid = pm.variables.get('DP_HIST_EPASS_LOUNGE_RESOURCE_ID');
  if (rid === undefined || rid === null) return;
  rid = String(rid).trim();
  if (rid && rid.indexOf('{{{{') < 0) pm.collectionVariables.set('{LOUNGE_RESOURCE_ID_VAR}', rid);
}}
function p39LoungeSaveMembershipId(label) {{
  pm.test(label + ': 保存 membershipId', function () {{
    var data = lpGetInnerData(pm.response.json());
    var mid = data.membershipId || data.id;
    pm.expect(mid, 'membershipId').to.be.a('string').and.not.empty;
    pm.collectionVariables.set('membershipId', String(mid));
  }});
}}
function p39LoungeAssertMembershipPrebookingSuccess(label) {{
  lpAssertHttpBusinessOk(label);
  pm.test(label + ': usage orderId 非空', function () {{
    var data = lpGetInnerData(pm.response.json());
    pm.expect(data.orderId).to.be.a('string').and.not.empty;
    pm.collectionVariables.set('usageOrderId', String(data.orderId));
  }});
}}
function p39LoungeAssertNameIsolation(label, firstName, lastName) {{
  var loungeRe = new RegExp({lounge_regex_js});
  var ftRe = new RegExp({ft_regex_js});
  pm.test(label + ': 入参符合 Lounge 姓名正则', function () {{
    pm.expect(firstName, 'firstName').to.match(loungeRe);
    pm.expect(lastName, 'lastName').to.match(loungeRe);
  }});
  pm.test(label + ': 入参至少一处不符合 FT 正则（品类隔离样本）', function () {{
    var ftOk = ftRe.test(firstName) && ftRe.test(lastName);
    pm.expect(ftOk, 'FT ^[A-Za-z ]+$ 应拒绝本样本').to.eql(false);
  }});
}}
"""
    return js.splitlines()


def _JsHelpers() -> List[str]:
    return [
        *BuildLoungeJsHelpersLines(assert_epass_status=False),
        *BuildP2839LoungeJsHelpersLines(),
    ]


def Prerequest_Auth() -> List[str]:
    return ["p39LoungeSyncCredentialVarsFromEnv();"]


def Prerequest_SetupAvailability() -> List[str]:
    return [
        "p39LoungeSyncCredentialVarsFromEnv();",
        "p39LoungeSyncLoungeResourceIdFromEnv();",
        *Prerequest_SyncPrebookingDateFromApifox(),
    ]


def _PositiveSuccessAssert(api_kind: OrderApiKind, step_id: str) -> str:
    if api_kind == "epass_prebooking":
        return f"lpAssertPrebookingOrderSuccess('{step_id}');"
    if api_kind == "bundle":
        return f"lpAssertBundleOrderSuccess('{step_id}');"
    return f"p39LoungeAssertMembershipPrebookingSuccess('{step_id}');"


def _OrderTestLines(case: LoungeRegressionCase) -> List[str]:
    step_id = case.step_key
    return Lines_Step(
        step_id,
        [
            f"p39LoungeAssertNameIsolation('{step_id}', {json.dumps(case.first_name)}, {json.dumps(case.last_name)});",
            f"lpAssertHttpBusinessOk('{step_id}');",
            _PositiveSuccessAssert(case.api_kind, step_id),
        ],
    )


def _BuildAvailabilityItem(*, case: LoungeRegressionCase, with_epass: bool) -> JsonObject:
    avl_step_id = f"{case.step_key}-AVL"
    body = BuildMembershipAvailabilityBody() if case.api_kind == "membership_prebooking" else AvailabilityBody(
        with_epass=with_epass
    )
    prerequest = list(Prerequest_SetupAvailability())
    if case.api_kind == "bundle":
        prerequest = [*Prerequest_NewClientUserId(), *prerequest]
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(f"{case.purpose} · 可用性", avl_step_id, "POST", "/prebookings/availability"),
        method="POST",
        url_path="/v2/resources/prebookings/availability",
        body=body,
        headers=BearerJsonHeaders(),
        description="classic 可用性 · 写入 prebookingToken",
        prerequest_lines=prerequest,
        test_lines=Lines_Step(
            avl_step_id,
            [f"lpAssertHttpBusinessOk('{avl_step_id}');", f"lpAssertAvailabilitySuccess('{avl_step_id}');"],
        ),
    )


def _BuildOrderItem(case: LoungeRegressionCase) -> JsonObject:
    if case.api_kind == "epass_prebooking":
        url_path = "/v2/orders/lounges/ePasses/prebooking"
        path_hint = "prebooking"
    elif case.api_kind == "bundle":
        url_path = "/v2/orders/lounges/ePasses/bundle"
        path_hint = "bundle"
    else:
        url_path = "/v2/orders/lounges/memberships/prebooking"
        path_hint = "memberships/prebooking"
    return RequestItem(
        js_helpers=_JsHelpers,
        name=PurposeName(case.purpose, case.step_key, "POST", path_hint),
        method="POST",
        url_path=url_path,
        body=BuildOrderBody(case),
        headers=BearerJsonHeaders(),
        description=(
            f"PAPI-2839 Lounge 回归 · firstName={case.first_name!r} lastName={case.last_name!r} · "
            f"Lounge 正则 {LOUNGE_NAME_REGEX_JS} · FT 正则 {FT_NAME_REGEX_JS}"
        ),
        test_lines=_OrderTestLines(case),
    )


def _BuildCancelItemsAfterOrder(case: LoungeRegressionCase) -> List[JsonObject]:
    """下单成功后 ``PATCH /v2/orders`` 取消；Bundle 另取消 ``purchaseOrderId``。"""
    cancel_prefix = f"{case.step_key}-CAN"
    items: List[JsonObject] = list(
        BuildCancelWithRetryBlock(
            purpose="取消 usage 预订单",
            step_prefix=f"{cancel_prefix}-U",
            order_id_var="usageOrderId",
            skip_to_request_name=None,
            description="下单成功后 ``PATCH /v2/orders`` · 取消 usageOrderId",
        )
    )
    if case.api_kind == "bundle":
        items.extend(
            BuildCancelWithRetryBlock(
                purpose="取消 MS 购买单（Bundle 收尾）",
                step_prefix=f"{cancel_prefix}-MS",
                order_id_var="purchaseOrderId",
                skip_to_request_name=None,
                description="Bundle 下单后 ``PATCH /v2/orders`` · 取消 purchaseOrderId",
            )
        )
    return items


def _EpassPrebookingSetupItems() -> List[JsonObject]:
    return [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：创建 lounge ePass", "SETUP-EP-S01", "POST", "/lounges/ePasses"),
            method="POST",
            url_path="/v2/orders/lounges/ePasses",
            body=CREATE_PAYLOAD_TEMPLATE,
            headers=BearerJsonHeaders(),
            description="ePass prebooking 前置 · 写入 ePassId",
            prerequest_lines=Prerequest_NewClientUserId(),
            test_lines=Lines_Step(
                "SETUP-EP-S01",
                ["lpAssertHttpBusinessOk('SETUP-EP-S01');", "lpAssertCreateCoreFields('SETUP-EP-S01');"],
            ),
        ),
    ]


def _MembershipSetupItems() -> List[JsonObject]:
    return [
        RequestItem(
            js_helpers=_JsHelpers,
            name=PurposeName("前置：注册 membership", "SETUP-MS-S01", "POST", "/memberships"),
            method="POST",
            url_path="/v2/memberships",
            body=MEMBERSHIP_REGISTER_PAYLOAD,
            headers=BearerJsonHeaders(),
            description="membership prebooking 前置 · 写入 membershipId",
            prerequest_lines=Prerequest_NewClientUserId(),
            test_lines=Lines_Step(
                "SETUP-MS-S01",
                [
                    "lpAssertHttpBusinessOk('SETUP-MS-S01');",
                    "p39LoungeSaveMembershipId('SETUP-MS-S01');",
                ],
            ),
        ),
    ]


def _BuildTrackFolder(case: LoungeRegressionCase) -> JsonObject:
    if case.api_kind == "epass_prebooking":
        folder_name = "ePass · prebooking"
        setup_items = _EpassPrebookingSetupItems()
        with_epass = True
        setup_desc = "``POST /v2/orders/lounges/ePasses`` · 写入 ``ePassId``"
    elif case.api_kind == "bundle":
        folder_name = "ePass · bundle"
        setup_items = []
        with_epass = False
        setup_desc = "Bundle 可用性无 ePassId · Pre-request 新建 ``clientUserId``"
    else:
        folder_name = "membership · prebooking"
        setup_items = _MembershipSetupItems()
        with_epass = False
        setup_desc = "``POST /v2/memberships`` · 写入 ``membershipId``"

    items: List[JsonObject] = []
    if setup_items:
        items.append(
            Folder(
                "00 前置",
                setup_items,
                description=setup_desc,
            )
        )
    items.append(_BuildAvailabilityItem(case=case, with_epass=with_epass))
    items.append(_BuildOrderItem(case))
    items.extend(_BuildCancelItemsAfterOrder(case))

    api_label = {
        "epass_prebooking": "``POST /v2/orders/lounges/ePasses/prebooking``",
        "bundle": "``POST /v2/orders/lounges/ePasses/bundle``",
        "membership_prebooking": "``POST /v2/orders/lounges/memberships/prebooking``",
    }[case.api_kind]

    return Folder(
        folder_name,
        items,
        description=f"PAPI-2839 Lounge 回归 · {api_label} · 样本 {case.first_name!r} / {case.last_name!r}",
    )


def BuildCollection() -> JsonObject:
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

    info: JsonObject = {
        "name": "PAPI-2839 · Lounge 姓名正则品类隔离回归",
        "description": (
            "由 GeneratePostmanCollectionPapi2839LoungeRegression.py 生成。\n\n"
            "**背景**：PAPI-2839 仅收紧 **FastTrack** 三接口 "
            "（``ePasses/prebooking`` / ``ePasses/bundle`` / ``memberships/prebooking``）"
            "``prebookingRequiredInfo`` 与 ``passengers[]`` 姓名为 ``^[A-Za-z ]+$``。\n\n"
            "**本集合**：验证 **Lounge** 同路径接口 **不受 FT 修复影响**；"
            f"Lounge 姓名正则 ``{LOUNGE_NAME_REGEX_JS}``。\n\n"
            "**三条正向回归**（FT 非法、Lounge 合法样本）：\n"
            "- ePass prebooking · lastName ``Jean-Pierre``\n"
            "- ePass bundle · firstName ``Mary-Jane``\n"
            "- membership prebooking · lastName ``Anne-Marie``\n\n"
            "**收尾**：每条链路下单成功后 ``PATCH /v2/orders`` 取消 usage 单；"
            "Bundle 另取消 ``purchaseOrderId``（对齐 Lounge P0 取消语义）。\n\n"
            "**前置**：Environment 填 ``ProgramID``、``clientId``、``secret``；"
            f"``loungeResourceId`` 默认 {DEFAULT_LOUNGE_RESOURCE_ID}。"
            "membership 路径 ``cashPaymentApplied=false``。"
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
        CollectionVariable("otherModule", "11"),
        CollectionVariable(LOUNGE_RESOURCE_ID_VAR, DEFAULT_LOUNGE_RESOURCE_ID),
        CollectionVariable("prebookingDate", ""),
        CollectionVariable("accessToken", ""),
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
        "item": [
            auth_folder,
            Folder(
                "P1 · Lounge 品类隔离回归",
                [_BuildTrackFolder(case) for case in REGRESSION_CASES],
                description=(
                    "对齐 ``PAPI-2839-修复FT联系人firstName-lastName正则-测试分析-001.md`` "
                    "``FtNameRegexRegression`` · tc-p2 Lounge 同路径不受影响"
                ),
            ),
        ],
    }


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection())
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
