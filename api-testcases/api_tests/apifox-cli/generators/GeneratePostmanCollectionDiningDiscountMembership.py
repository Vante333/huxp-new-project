"""
生成 Dining Discount **Membership walk-in** Postman Collection v2.1 JSON。

P0：注册 → 用户会籍列表 → search → 生成动态二维码 → 只改 expirationDate →
按注册结果依次更新四类权益（大客户类为 0 则 skip；买点无论是否为 0 都打一次）→
每次更新后概览+明细 → 使用订单列表（空则过）。

不测核销 / 取消。变量供给 B：Environment 手填。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionDiningDiscountMembership.py
"""
from __future__ import annotations

from typing import Any, Dict, Final, List

from collection_builder_common import (
    BearerJsonHeaders,
    CollectionPath,
    CollectionVariable,
    Folder,
    POSTMAN_SCHEMA,
    PurposeName,
    WriteCollectionJson,
)
from dining_discount_cli_common import (
    AuthItem,
    DINING_MODULE,
    EntitlementUpdateBody,
    MakeDdRequestItem,
    MembershipQrCodesBody,
    MembershipRegisterBody,
    MembershipUpdateDatesBody,
    QR_DURATION_SECONDS,
    Step,
)

JsonObject = Dict[str, Any]

OUT_NAME: Final[str] = "Dining-Discount-Membership-P0-e2e-core.postman_collection.json"
HELPERS_SOURCE_KEY: Final[str] = "ddMbrHelpersSource"

_Item = MakeDdRequestItem(HELPERS_SOURCE_KEY)

_ENT_STEPS: Final[List[Dict[str, Any]]] = [
    {
        "field": "cardholderExclusiveEntitlements",
        "flag": "ddSkipUpd_cardholderExclusiveEntitlements",
        "ur": 1,
        "qty": 1,
        "pq": None,
        "always": False,
        "purpose": "更新持卡人专属 +1",
        "prefix": "M03",
    },
    {
        "field": "sharedEntitlements",
        "flag": "ddSkipUpd_sharedEntitlements",
        "ur": 3,
        "qty": 1,
        "pq": None,
        "always": False,
        "purpose": "更新共享权益 +1",
        "prefix": "M04",
    },
    {
        "field": "guestsExclusiveEntitlements",
        "flag": "ddSkipUpd_guestsExclusiveEntitlements",
        "ur": 2,
        "qty": 1,
        "pq": None,
        "always": False,
        "purpose": "更新携客专属 +1",
        "prefix": "M05",
    },
    {
        "field": "purchasedEntitlements",
        "flag": "ddSkipUpd_purchasedEntitlements",
        "ur": None,
        "qty": None,
        "pq": 1,
        "always": True,
        "purpose": "更新买点 purchasedQuantity +1",
        "prefix": "M06",
    },
]


def BuildScenarioDescription() -> str:
    return (
        "由 GeneratePostmanCollectionDiningDiscountMembership.py 生成。\n\n"
        "**范围**：Dining Discount **Membership** walk-in 注册 / 查询 / 展码 / 改期 / 权益更新。"
        "没有预约下单；核销由其他团队负责，不测 Callback / 取消。\n\n"
        "**链路**：Auth → ``POST /v2/memberships`` 注册（快照 module=5 四类权益）→ "
        "``POST /v2/users/memberships`` → ``POST /v2/memberships/search`` → "
        "``POST /v2/memberships/qrCodes`` 展码（``durationInSeconds="
        + str(QR_DURATION_SECONDS)
        + "``）→ "
        "``POST /v2/memberships/update`` **只改** ``expirationDate``（权益不被清零）→ "
        "按注册快照依次更新：持卡人 ``usageRestriction=1`` + ``quantity``、"
        "共享 ``=3``、携客 ``guestsExclusiveEntitlements`` ``=2``（为 0 则 skip 该步）、"
        "**无论 purchased 是否为 0 再打一次买点** ``purchasedQuantity`` → "
        "每次更新后 ``/entitlements/search`` + ``/entitlements/details``（目标类变、其余不变）→ "
        "``POST /v2/orders/memberships`` 使用列表（空则通过，详情 skip）。\n\n"
        "**变量**：\n"
        "- 鉴权三列 ``ProgramID`` / ``clientId`` / ``secret``：membership 数据集选行"
        "（``use_data_set_id=3475754``）；业务 body **不**注入 clientId/secret。\n"
        "- ``membershipId`` / ``clientUserId``：取 **M01-S01 注册响应**，写入 variables+collection；"
        "后续步前置 **强制回填**（覆盖 Environment 旧值 / OAS 样例）。"
        "``POST /users/memberships`` **不传** ``status``（OAS example 的 ``status=1`` 会过滤列表）。\n"
        "- 动态二维码：``membershipId`` + ``durationInSeconds="
        + str(QR_DURATION_SECONDS)
        + "``（合法范围 60–7200）；"
        "``qrCode`` 非空；``validUntil`` Unix 秒 ≈ 请求时刻+"
        + str(QR_DURATION_SECONDS)
        + "（容差 30s）。\n"
        "- 四类权益：持卡人 ``cardholderExclusiveEntitlements``、"
        "携客 ``guestsExclusiveEntitlements``（restriction=2）、"
        "共享 ``sharedEntitlements``、充值/买点 ``purchasedEntitlements``。\n"
        "- 权益更新（用户确认，对齐 ``500.030.025``）：大客户（持卡人/共享/携客）**只传** ``quantity``，"
        "买点 **只传** ``purchasedQuantity``。OAS 两字段都 required，同传会被产品拒绝。\n"
        "- 未核销使用订单 **不返回** ``passengerCounts`` / ``usedEntitlementDetails`` / "
        "``usedEntitlementBreakdown``。已核销才要求 ``usedEntitlementDetails`` 含 ``purchasedEntitlements``"
        "（本场景不造核销）。\n\n"
        "**Helpers**：Auth 写入 ``ddMbrHelpersSource``；其它步 eval loader。须先跑 00 Auth。\n"
        "**OAS 已知冲突**：``entitlements/details`` schema 为空，本场景仍传 ``membershipId`` + ``module=5``；"
        "权益更新 schema 两数量字段都 required，本场景按 ``500.030.025`` **不同时传**。"
    )


def _EntitlementTriplet(spec: Dict[str, Any]) -> List[JsonObject]:
    field = str(spec["field"])
    flag = str(spec["flag"])
    prefix = str(spec["prefix"])
    always = bool(spec["always"])
    pre_update = (
        []
        if always
        else [f"ddSkipUpdateIfZero('{field}', '{flag}');"]
    )
    pre_follow = [] if always else [f"ddSkipIfFlag('{flag}', '{field} 为 0 skip 概览/明细');"]
    skip_arg = "''" if always else f"'{flag}'"
    return [
        _Item(
            name=PurposeName(str(spec["purpose"]), f"{prefix}-S01", "POST", "/entitlements/update"),
            method="POST",
            url_path="/v2/entitlements/update",
            body=EntitlementUpdateBody(
                usage_restriction=spec.get("ur"),
                quantity=spec.get("qty"),
                purchased_quantity=spec.get("pq"),
            ),
            headers=BearerJsonHeaders(),
            description=(
                f"module=5；目标字段 {field}；"
                "大客户传 quantity+usageRestriction；买点只传 purchasedQuantity（不传 restriction）。"
            ),
            prerequest_lines=pre_update,
            test_lines=Step(
                f"{prefix}-S01",
                [f"ddAssertEntitlementUpdate('{prefix}-S01', '{field}');"],
            ),
        ),
        _Item(
            name=PurposeName("更新后权益概览", f"{prefix}-S02", "POST", "/entitlements/search"),
            method="POST",
            url_path="/v2/entitlements/search",
            body='{\n  "membershipId": "{{membershipId}}"\n}',
            headers=BearerJsonHeaders(),
            description="与明细对拍：目标类 +1，其余等于 running expect。",
            prerequest_lines=pre_follow,
            test_lines=Step(
                f"{prefix}-S02",
                [f"ddAssertEntitlementSearch('{prefix}-S02', {skip_arg});"],
            ),
        ),
        _Item(
            name=PurposeName("更新后权益明细", f"{prefix}-S03", "POST", "/entitlements/details"),
            method="POST",
            url_path="/v2/entitlements/details",
            body='{\n  "membershipId": "{{membershipId}}",\n  "module": ' + str(DINING_MODULE) + "\n}",
            headers=BearerJsonHeaders(),
            description="scopeType=1；四类余额与概览一致。",
            prerequest_lines=pre_follow,
            test_lines=Step(
                f"{prefix}-S03",
                [f"ddAssertEntitlementDetails('{prefix}-S03', {skip_arg});"],
            ),
        ),
    ]


def BuildCollection() -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            AuthItem(
                HELPERS_SOURCE_KEY,
                purpose=PurposeName("获取 membership 鉴权 token", "Auth", "POST", "/auth/token"),
            ),
        ],
        description="先执行。鉴权三列来自 membership 数据集选行。",
    )
    setup_folder = Folder(
        "M01 · 注册与查询",
        [
            _Item(
                name=PurposeName("注册 Dining Discount 会籍", "M01-S01", "POST", "/memberships"),
                method="POST",
                url_path="/v2/memberships",
                body=MembershipRegisterBody(),
                headers=BearerJsonHeaders(),
                description="快照 module=5 四类权益（含 0）；写入 membershipId。",
                prerequest_lines=[
                    "ddUnsetVar('clientUserId');",
                    "ddUnsetVar('membershipId');",
                    "ddUnsetVar('usageOrderId');",
                ],
                test_lines=Step("M01-S01", ["ddSaveMembershipId('M01-S01');"]),
            ),
            _Item(
                name=PurposeName("用户会籍列表含本会籍", "M01-S02", "POST", "/users/memberships"),
                method="POST",
                url_path="/v2/users/memberships",
                body=(
                    '{\n  "clientUserId": "{{clientUserId}}",\n'
                    '  "pageSize": 10,\n  "pageNumber": 1\n}'
                ),
                headers=BearerJsonHeaders(),
                description="clientUserId / pageSize / pageNumber 必传。",
                test_lines=Step("M01-S02", ["ddAssertUsersMemberships('M01-S02');"]),
            ),
            _Item(
                name=PurposeName("search 查询会籍", "M01-S03", "POST", "/memberships/search"),
                method="POST",
                url_path="/v2/memberships/search",
                body='{\n  "membershipId": "{{membershipId}}"\n}',
                headers=BearerJsonHeaders(),
                description="membershipId 必传。",
                test_lines=Step("M01-S03", ["ddAssertMembershipSearch('M01-S03');"]),
            ),
            _Item(
                name=PurposeName("生成会籍动态二维码", "M01-S04", "POST", "/memberships/qrCodes"),
                method="POST",
                url_path="/v2/memberships/qrCodes",
                body=MembershipQrCodesBody(),
                headers=BearerJsonHeaders(),
                description=(
                    "membershipId 必传；durationInSeconds="
                    + str(QR_DURATION_SECONDS)
                    + "（合法范围 60–7200）。qrCode 非空；validUntil≈请求时刻+duration。"
                ),
                prerequest_lines=["ddStampQrRequestUnix();"],
                test_lines=Step(
                    "M01-S04",
                    [f"ddAssertMembershipQrCodes('M01-S04', {QR_DURATION_SECONDS});"],
                ),
            ),
        ],
        description="注册发放 Dining Discount 预设权益；随后展码。不硬断言模板绝对值。",
    )
    date_folder = Folder(
        "M02 · 更新有效期（权益不清零）",
        [
            _Item(
                name=PurposeName("只改 expirationDate", "M02-S01", "POST", "/memberships/update"),
                method="POST",
                url_path="/v2/memberships/update",
                body=MembershipUpdateDatesBody(),
                headers=BearerJsonHeaders(),
                description="不改 status；registrationDate 不被改写。",
                test_lines=Step("M02-S01", ["ddAssertMembershipUpdateDates('M02-S01');"]),
            ),
            _Item(
                name=PurposeName("改期后权益概览仍等于注册快照", "M02-S02", "POST", "/entitlements/search"),
                method="POST",
                url_path="/v2/entitlements/search",
                body='{\n  "membershipId": "{{membershipId}}"\n}',
                headers=BearerJsonHeaders(),
                description="四类权益不被错误重置。",
                test_lines=Step(
                    "M02-S02",
                    ["ddAssertEntitlementSearch('M02-S02', '');"],
                ),
            ),
        ],
        description="改期后 running expect 仍等于注册快照。",
    )
    ent_items: List[JsonObject] = []
    for spec in _ENT_STEPS:
        ent_items.extend(_EntitlementTriplet(spec))
    ent_folder = Folder(
        "M03–M06 · 分别更新四类权益",
        ent_items,
        description="持卡人=1 / 共享=3 / 携客=2；买点始终打 purchasedQuantity。为 0 的大客户类 skip。",
    )
    usage_folder = Folder(
        "M07 · 使用订单（空则过）",
        [
            _Item(
                name=PurposeName("membership 使用订单列表", "M07-S01", "POST", "/orders/memberships"),
                method="POST",
                url_path="/v2/orders/memberships",
                body=(
                    '{\n  "membershipId": "{{membershipId}}",\n  "module": '
                    + str(DINING_MODULE)
                    + ',\n  "pageSize": 10,\n  "pageNumber": 1\n}'
                ),
                headers=BearerJsonHeaders(),
                description="空列表通过；未核销不返回 passengerCounts。",
                test_lines=Step("M07-S01", ["ddAssertMembershipUsageList('M07-S01');"]),
            ),
            _Item(
                name=PurposeName("membership 使用订单详情（无单 skip）", "M07-S02", "POST", "/memberships/details"),
                method="POST",
                url_path="/v2/orders/memberships/details",
                body='{\n  "orderId": "{{usageOrderId}}"\n}',
                headers=BearerJsonHeaders(),
                description="无 usageOrderId 则 skip；未核销不返回 usedEntitlementDetails。",
                prerequest_lines=["ddSkipUsageDetailsIfEmpty();"],
                test_lines=Step("M07-S02", ["ddAssertMembershipUsageDetails('M07-S02');"]),
            ),
        ],
        description="不造核销；有单才查详情。",
    )
    info: JsonObject = {
        "name": "Dining Discount Membership · P0 walk-in",
        "description": BuildScenarioDescription(),
        "schema": POSTMAN_SCHEMA,
    }
    variables: List[JsonObject] = [
        CollectionVariable("baseUrl", "https://developer-sandbox.dragonpass.com/api"),
        CollectionVariable("ProgramID", ""),
        CollectionVariable("clientId", ""),
        CollectionVariable("secret", ""),
        CollectionVariable("x-version", ""),
        CollectionVariable(
            HELPERS_SOURCE_KEY,
            "",
            "Auth 写入的 helpers 源码；其它步骤 eval。单独跑业务步须先跑 00 Auth。",
        ),
        CollectionVariable("accessToken", ""),
        CollectionVariable("clientUserId", ""),
        CollectionVariable("membershipId", ""),
        CollectionVariable("usageOrderId", ""),
    ]
    return {
        "info": info,
        "variable": variables,
        "item": [auth_folder, setup_folder, date_folder, ent_folder, usage_folder],
    }


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection())
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
