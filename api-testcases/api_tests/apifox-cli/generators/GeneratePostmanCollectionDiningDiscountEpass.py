"""
生成 Dining Discount **ePass walk-in** Postman Collection v2.1 JSON。

P0：LIST module=5/4 → 发放全网络（不传 resourceIds）→ search / users / 使用列表（空则过）
→ 再发放指定资源 → 同样查询链。
P1 挂在同一场景末尾：混品类 ``500.063.001``、超 30 ``500.063.002``（ Dining 不足 31 则 skip）。

不测核销 / Callback / 取消 / 二维码。变量供给 B：Environment 手填（资源 ID 运行时 LIST 取）。

用法（仓库根目录）::

    python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionDiningDiscountEpass.py
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
    COUPON_MODULE,
    CreateEpassBody,
    CreateEpassBodyFreshUser,
    DINING_MODULE,
    ERR_MIXED_MODULE,
    ERR_OVER_LIMIT,
    LIST_RESOURCES_PATH,
    MSG_MIXED_NEEDLE,
    MSG_OVER_LIMIT_NEEDLE,
    MakeDdRequestItem,
    MixCreateBody,
    OverLimitCreateBody,
    Step,
)

JsonObject = Dict[str, Any]

OUT_NAME: Final[str] = "Dining-Discount-ePass-P0-e2e-core.postman_collection.json"
HELPERS_SOURCE_KEY: Final[str] = "ddEpassHelpersSource"

_Item = MakeDdRequestItem(HELPERS_SOURCE_KEY)


def BuildScenarioDescription() -> str:
    return (
        "由 GeneratePostmanCollectionDiningDiscountEpass.py 生成。\n\n"
        "**范围**：Dining Discount **ePass** walk-in 发放与查询（P0 正向 + 同场景 P1 负向）。"
        "没有预约下单；核销由其他团队负责，本场景不测 Callback / Simulation / 取消 / 二维码。\n\n"
        "**链路**：Auth → ``GET /v2/resources?module=5`` 动态取 ``diningResourceId`` "
        "→ ``GET /v2/resources?module=4``（coupon）取混品类 ID → "
        "发放①全网络（``POST /v2/orders/discounts/ePasses``，**不传** ``resourceIds``）→ "
        "search / users/ePasses / 使用订单列表（空则通过，详情 skip）→ "
        "发放② ``resourceIds=[diningResourceId]`` → 再查一遍 → "
        "P1 混品类 ``500.063.001``、超 30（31 个）``500.063.002``。\n\n"
        "**变量**：\n"
        "- 鉴权三列 ``ProgramID`` / ``clientId`` / ``secret``：ePass 数据集选行"
        "（``use_data_set_id=3475756``）；Auth 种子 iterationData → Environment → variables，写回四作用域。"
        "业务 body **不**注入 clientId/secret。\n"
        "- ``diningResourceId`` / ``diningResourceIdsJson``：LIST module=5 写入 variables+collection；"
        "**不要** Environment 手填。列表空则失败（禁止 PLACEHOLDER）。"
        "解绑后 GET query 常丢，前置 ``ddApplyResourcesListQuery`` 写回 ``module/pageSize/language``。\n"
        "- ``diningOtherModuleResourceId``：LIST coupon module=4 第一条；空则 skip ``500.063.001``。\n"
        "- 超 30：Dining 去重 ID **不足 31** 则 skip ``500.063.002``，禁止用 coupon ID 凑数。\n"
        "- 全网络 = ``allowedResources`` 对象仍传，但 **不传** ``resourceIds`` 键（不是 ``[]``）。\n"
        "- ``module=5``、walk-in ``category=1``；``clientUserId`` / ``ePassId`` / ``purchaseOrderId`` "
        "由发放响应写入；使用 ``orderId`` **只从列表取**。\n"
        "- 未核销使用订单 **不返回** ``usedUsages``。\n\n"
        "**Helpers**：Auth 写入 ``ddEpassHelpersSource``；其它步 eval loader。须先跑 00 Auth。\n"
        "**OAS 已知冲突**：path enum 无 ``discounts``；本场景仍打 ``/v2/orders/discounts/ePasses``。"
    )


def _QueryChain(*, prefix: str, purpose_tag: str) -> List[JsonObject]:
    return [
        _Item(
            name=PurposeName(f"{purpose_tag} search 按 ePassId 查主订单", f"{prefix}-S02", "POST", "/ePasses/search"),
            method="POST",
            url_path="/v2/orders/ePasses/search",
            body='{\n  "ePassId": "{{ePassId}}"\n}',
            headers=BearerJsonHeaders(),
            description="按发放写入的 ePassId 查主订单；module=5、category=1、未使用 usedUsages=0。",
            test_lines=Step(f"{prefix}-S02", [f"ddAssertSearchEpass('{prefix}-S02');"]),
        ),
        _Item(
            name=PurposeName(f"{purpose_tag} 用户 ePass 列表含本券", f"{prefix}-S03", "POST", "/users/ePasses"),
            method="POST",
            url_path="/v2/users/ePasses",
            body=(
                '{\n  "clientUserId": "{{clientUserId}}",\n'
                '  "pageSize": 10,\n  "pageNumber": 1\n}'
            ),
            headers=BearerJsonHeaders(),
            description="clientUserId 必传；命中项 module=5。",
            test_lines=Step(f"{prefix}-S03", [f"ddAssertUsersEpasses('{prefix}-S03');"]),
        ),
        _Item(
            name=PurposeName(f"{purpose_tag} 使用订单列表（空则过）", f"{prefix}-S04", "POST", "/orders/ePasses"),
            method="POST",
            url_path="/v2/orders/ePasses",
            body=(
                '{\n  "ePassId": "{{ePassId}}",\n  "module": '
                + str(DINING_MODULE)
                + ',\n  "pageSize": 10,\n  "pageNumber": 1\n}'
            ),
            headers=BearerJsonHeaders(),
            description="orderId 只从列表取；空列表通过；未核销不返回 usedUsages。",
            test_lines=Step(f"{prefix}-S04", [f"ddAssertUsageListAndCapture('{prefix}-S04');"]),
        ),
        _Item(
            name=PurposeName(f"{purpose_tag} 使用订单详情（无单 skip）", f"{prefix}-S05", "POST", "/ePasses/details"),
            method="POST",
            url_path="/v2/orders/ePasses/details",
            body='{\n  "orderId": "{{usageOrderId}}"\n}',
            headers=BearerJsonHeaders(),
            description="无 usageOrderId 时 skipRequest；未核销不返回 extra.usedUsages。",
            prerequest_lines=["ddSkipUsageDetailsIfEmpty();"],
            test_lines=Step(f"{prefix}-S05", [f"ddAssertUsageDetails('{prefix}-S05');"]),
        ),
    ]


def BuildCollection() -> JsonObject:
    auth_folder = Folder(
        "00 Auth",
        [
            AuthItem(
                HELPERS_SOURCE_KEY,
                purpose=PurposeName("获取 ePass 鉴权 token", "Auth", "POST", "/auth/token"),
            ),
        ],
        description="先执行。鉴权三列来自 ePass 数据集选行。",
    )
    list_folder = Folder(
        "E00 · 动态取资源",
        [
            _Item(
                name=PurposeName("LIST Dining 资源取 diningResourceId", "E00-S01", "GET", "/resources?module=5"),
                method="GET",
                url_path=LIST_RESOURCES_PATH.format(module=DINING_MODULE),
                body=None,
                headers=BearerJsonHeaders(),
                description="第一条写入 diningResourceId；全部 ID 供凑 31 个。空列表失败。解绑后 GET query 常丢，前置强制写回。",
                prerequest_lines=["ddApplyResourcesListQuery(5);"],
                test_lines=Step("E00-S01", ["ddCaptureDiningList('E00-S01');"]),
            ),
            _Item(
                name=PurposeName("LIST coupon 资源取混品类 ID", "E00-S02", "GET", "/resources?module=4"),
                method="GET",
                url_path=LIST_RESOURCES_PATH.format(module=COUPON_MODULE),
                body=None,
                headers=BearerJsonHeaders(),
                description="module=4 coupon（不是 lounge）。空则后续 skip 500.063.001。解绑后 GET query 常丢，前置强制写回。",
                prerequest_lines=["ddApplyResourcesListQuery(4);"],
                test_lines=Step("E00-S02", ["ddCaptureCouponList('E00-S02');"]),
            ),
        ],
        description="资源 ID 运行时取，禁止 Environment 手填 diningResourceId。",
    )
    network_folder = Folder(
        "E01 · P0 全网络发放",
        [
            _Item(
                name=PurposeName("发放全网络 Dining Discount ePass", "E01-S01", "POST", "/discounts/ePasses"),
                method="POST",
                url_path="/v2/orders/discounts/ePasses",
                body=CreateEpassBodyFreshUser(include_resource_placeholder=False),
                headers=BearerJsonHeaders(),
                description="allowedResources 仍传对象；不传 resourceIds 键。module=5。",
                prerequest_lines=[
                    "ddUnsetVar('clientUserId');",
                    "ddUnsetVar('ePassId');",
                    "ddUnsetVar('purchaseOrderId');",
                    "ddUnsetVar('usageOrderId');",
                    "ddEnsureNetworkCreateBody();",
                ],
                test_lines=Step(
                    "E01-S01",
                    ["ddAssertCreateEpass('E01-S01', 'network', 'ePassIdNetwork');"],
                ),
            ),
            *_QueryChain(prefix="E01", purpose_tag="全网络"),
        ],
        description="全网络 = 不传 resourceIds（不是空数组）。",
    )
    scoped_folder = Folder(
        "E02 · P0 指定资源发放",
        [
            _Item(
                name=PurposeName("发放指定餐厅 Dining Discount ePass", "E02-S01", "POST", "/discounts/ePasses"),
                method="POST",
                url_path="/v2/orders/discounts/ePasses",
                body=CreateEpassBody(include_resource_placeholder=True),
                headers=BearerJsonHeaders(),
                description="同一 clientUserId；resourceIds 仅 diningResourceId。",
                prerequest_lines=[
                    "ddUnsetVar('ePassId');",
                    "ddUnsetVar('purchaseOrderId');",
                    "ddUnsetVar('usageOrderId');",
                    "ddEnsureScopedCreateBody();",
                ],
                test_lines=Step(
                    "E02-S01",
                    ["ddAssertCreateEpass('E02-S01', 'scoped', 'ePassIdScoped');"],
                ),
            ),
            *_QueryChain(prefix="E02", purpose_tag="指定资源"),
        ],
        description="allowedResources.resourceIds 仅含 LIST 第一条 Dining ID。",
    )
    p1_folder = Folder(
        "E03 · P1 负向（同场景）",
        [
            _Item(
                name=PurposeName("混品类 resourceIds 期望 500.063.001", "E03-S01", "POST", "/discounts/ePasses"),
                method="POST",
                url_path="/v2/orders/discounts/ePasses",
                body=MixCreateBody(),
                headers=BearerJsonHeaders(),
                description="resourceIds 带 coupon module=4 ID；无 coupon 则 skip。",
                prerequest_lines=["ddEnsureMixCreateBody();"],
                test_lines=Step(
                    "E03-S01",
                    [
                        "ddSkipTestsOrRun('ddSkipMix001', 'E03-S01: 无 coupon 资源 skip 001', function () {",
                        f"  ddAssertBusinessError('E03-S01', '{ERR_MIXED_MODULE}', {MSG_MIXED_NEEDLE!r});",
                        "});",
                    ],
                ),
            ),
            _Item(
                name=PurposeName("resourceIds 31 个期望 500.063.002", "E03-S02", "POST", "/discounts/ePasses"),
                method="POST",
                url_path="/v2/orders/discounts/ePasses",
                body=OverLimitCreateBody(),
                headers=BearerJsonHeaders(),
                description="Dining 去重 ID 不足 31 则 skip，禁止用 coupon 凑数。",
                prerequest_lines=["ddEnsureOverLimitCreateBody();"],
                test_lines=Step(
                    "E03-S02",
                    [
                        "ddSkipTestsOrRun('ddSkipOver002', 'E03-S02: Dining 不足 31 skip 002', function () {",
                        f"  ddAssertBusinessError('E03-S02', '{ERR_OVER_LIMIT}', {MSG_OVER_LIMIT_NEEDLE!r});",
                        "});",
                    ],
                ),
            ),
        ],
        description="P1 不另开场景；skip 不算失败。",
    )
    info: JsonObject = {
        "name": "Dining Discount ePass · P0 walk-in（含 P1 负向）",
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
        CollectionVariable("ePassId", ""),
        CollectionVariable("ePassIdNetwork", ""),
        CollectionVariable("ePassIdScoped", ""),
        CollectionVariable("purchaseOrderId", ""),
        CollectionVariable("usageOrderId", ""),
        CollectionVariable("diningResourceId", ""),
        CollectionVariable("diningOtherModuleResourceId", ""),
        CollectionVariable("diningResourceIdsJson", ""),
    ]
    return {
        "info": info,
        "variable": variables,
        "item": [auth_folder, list_folder, network_folder, scoped_folder, p1_folder],
    }


def Main() -> None:
    out_path = str(CollectionPath(OUT_NAME))
    WriteCollectionJson(out_path, BuildCollection())
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
