"""
历史品类 ePass 主链路编排。

对外暴露 ``RunHistoricalEpassCreateMainE2EScenario``、``RunHistoricalEpassPrebookingMainE2EScenario`` 与
``RunHistoricalEpassBundleMainE2EScenario``；回归用例仅调用上述入口，确保 Local Offer 改动不破坏四类历史接口。
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from config.historical_epass_env import HistoricalEpassCatalogEntry, GetHistoricalEpassCatalogByLabel
from services.historical_epass_service import (
    AssertHistoricalBundleOrderSuccess,
    AssertHistoricalEpassSearchDetailsCoreFields,
    AssertHistoricalPrebookingOrderSuccessForCatalog,
    AssertUserEPassesContainsHistorical,
    CancelHistoricalPurchaseOrderAndVerify,
    CancelHistoricalUsageOrderAndVerify,
    CreateHistoricalEpass,
    HistoricalEpassCreateResult,
    HistoricalEpassPrebookingResult,
    PostHistoricalEpassBundle,
    RequestHistoricalPrebookingToken,
    RequestHistoricalPrebookingTokenWithoutEpass,
)
from services.local_offer_epass_service import (
    ExtractBusinessData,
    PostOrdersEPassesList,
    PostOrdersEPassesSearch,
    PostUsersEPasses,
    _HttpStepKw,
)
from services.historical_epass_service import PostHistoricalEpassPrebooking


def RunHistoricalEpassCreateMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: Optional[HistoricalEpassCatalogEntry] = None,
    catalog_label: str = "lounge",
) -> HistoricalEpassCreateResult:
    """
    历史品类 EPass 创建验证链：

    ``POST /v2/orders/{module}/ePasses`` → ``POST /v2/users/ePasses`` →
    ``POST /v2/orders/ePasses`` → ``POST /v2/orders/ePasses/search``（orderId / ePassId）→
    取消 MS 购买单。
    """
    entry = catalog or GetHistoricalEpassCatalogByLabel(catalog_label)
    if entry is None:
        raise ValueError(f"未知 historical epass catalog label: {catalog_label!r}")

    created = CreateHistoricalEpass(token, steps, entry)

    kw_users = _HttpStepKw(steps, f"查询用户 ePass 列表（{entry.DisplayName}）")
    resp_users = PostUsersEPasses(
        token,
        created.ClientUserId,
        step_code=kw_users["step_code"],
        step_title=kw_users["step_title"],
    )
    AssertUserEPassesContainsHistorical(
        resp_users,
        e_pass_id=created.EPassId,
        expected_module=entry.ModuleInt,
        context=f"{entry.Label}-users",
    )

    kw_search_order = _HttpStepKw(steps, f"ePass 购买单 search（orderId · {entry.DisplayName}）")
    resp_search_order = PostOrdersEPassesSearch(
        token,
        order_id=created.PurchaseOrderId,
        step_code=kw_search_order["step_code"],
        step_title=kw_search_order["step_title"],
    )
    AssertHistoricalEpassSearchDetailsCoreFields(
        resp_search_order,
        expected_module=entry.ModuleInt,
        expected_order_id=created.PurchaseOrderId,
        expected_e_pass_id=created.EPassId,
        context=f"{entry.Label}-search-by-orderId",
    )

    kw_search_epass = _HttpStepKw(steps, f"ePass 购买单 search（ePassId · {entry.DisplayName}）")
    resp_search_epass = PostOrdersEPassesSearch(
        token,
        e_pass_id=created.EPassId,
        step_code=kw_search_epass["step_code"],
        step_title=kw_search_epass["step_title"],
    )
    AssertHistoricalEpassSearchDetailsCoreFields(
        resp_search_epass,
        expected_module=entry.ModuleInt,
        expected_order_id=created.PurchaseOrderId,
        expected_e_pass_id=created.EPassId,
        context=f"{entry.Label}-search-by-ePassId",
    )

    kw_list = _HttpStepKw(steps, f"ePass usage 订单列表（创建后可能为空 · {entry.DisplayName}）")
    resp_list = PostOrdersEPassesList(
        token,
        created.EPassId,
        module=entry.ModuleInt,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    ExtractBusinessData(resp_list)

    CancelHistoricalPurchaseOrderAndVerify(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context=f"{entry.Label}-create-cancel",
    )

    return created


def RunHistoricalEpassPrebookingMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: Optional[HistoricalEpassCatalogEntry] = None,
    catalog_label: str = "lounge",
) -> HistoricalEpassPrebookingResult:
    """
    历史品类 EPass Prebooking 链：

    创建 ePass → 可用性 → 预约下单 → 取消 usage 单 → details / 列表 / search → 取消 MS 单。
    """
    entry = catalog or GetHistoricalEpassCatalogByLabel(catalog_label)
    if entry is None:
        raise ValueError(f"未知 historical epass catalog label: {catalog_label!r}")

    created = CreateHistoricalEpass(token, steps, entry)

    pb_token, pb_date, fitness_target = RequestHistoricalPrebookingToken(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
        brief=f"{entry.DisplayName} 可用性（有 ePassId）",
    )

    kw_book = _HttpStepKw(steps, f"{entry.DisplayName} ePass 预约下单")
    resp_book = PostHistoricalEpassPrebooking(
        token,
        entry,
        e_pass_id=created.EPassId,
        prebooking_token=pb_token,
        fitness_target=fitness_target,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    usage_order_id = AssertHistoricalPrebookingOrderSuccessForCatalog(
        resp_book,
        catalog=entry,
        e_pass_id=created.EPassId,
        context=f"{entry.Label}-prebook",
        fitness_target=fitness_target,
    )

    CancelHistoricalUsageOrderAndVerify(
        token,
        steps,
        catalog=entry,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context=f"{entry.Label}-prebook-cancel",
    )

    CancelHistoricalPurchaseOrderAndVerify(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context=f"{entry.Label}-purchase-cancel",
    )

    return HistoricalEpassPrebookingResult(
        ClientUserId=created.ClientUserId,
        EPassId=created.EPassId,
        PurchaseOrderId=created.PurchaseOrderId,
        UsageOrderId=usage_order_id,
        PrebookingToken=pb_token,
        PrebookingDate=pb_date,
        Catalog=entry,
    )


def RunHistoricalEpassBundleMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: Optional[HistoricalEpassCatalogEntry] = None,
    catalog_label: str = "lounge",
    client_user_id: Optional[str] = None,
) -> HistoricalEpassPrebookingResult:
    """
    历史品类 EPass Bundle 链：

    可用性（无 ePassId）→ ``POST .../ePasses/bundle`` → users → search →
    取消 usage 单 → 取消 MS 单。
    """
    entry = catalog or GetHistoricalEpassCatalogByLabel(catalog_label)
    if entry is None:
        raise ValueError(f"未知 historical epass catalog label: {catalog_label!r}")

    cid = client_user_id or str(uuid.uuid4())
    pb_token, pb_date, fitness_target = RequestHistoricalPrebookingTokenWithoutEpass(
        token,
        steps,
        catalog=entry,
        brief=f"{entry.DisplayName} 可用性（无 ePassId · Bundle）",
    )

    kw_bundle = _HttpStepKw(steps, f"{entry.DisplayName} ePass Bundle 下单")
    resp_bundle = PostHistoricalEpassBundle(
        token,
        entry,
        client_user_id=cid,
        prebooking_token=pb_token,
        fitness_target=fitness_target,
        step_code=kw_bundle["step_code"],
        step_title=kw_bundle["step_title"],
    )
    e_pass_id, usage_order_id = AssertHistoricalBundleOrderSuccess(
        resp_bundle,
        catalog=entry,
        expected_client_user_id=cid,
        fitness_target=fitness_target,
        context=f"{entry.Label}-bundle",
    )

    kw_users = _HttpStepKw(steps, f"Bundle 后查询用户 ePass 列表（{entry.DisplayName}）")
    resp_users = PostUsersEPasses(
        token,
        cid,
        step_code=kw_users["step_code"],
        step_title=kw_users["step_title"],
    )
    AssertUserEPassesContainsHistorical(
        resp_users,
        e_pass_id=e_pass_id,
        expected_module=entry.ModuleInt,
        context=f"{entry.Label}-bundle-users",
    )

    kw_search = _HttpStepKw(steps, f"Bundle 后 ePass 购买单 search（{entry.DisplayName}）")
    resp_search = PostOrdersEPassesSearch(
        token,
        e_pass_id=e_pass_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )
    AssertHistoricalEpassSearchDetailsCoreFields(
        resp_search,
        expected_module=entry.ModuleInt,
        expected_e_pass_id=e_pass_id,
        context=f"{entry.Label}-bundle-search-by-ePassId",
    )
    search_data = ExtractBusinessData(resp_search)
    purchase_order_id_raw = search_data.get("orderId")
    purchase_order_id = (
        purchase_order_id_raw if isinstance(purchase_order_id_raw, str) else ""
    )
    if purchase_order_id:
        kw_search_order = _HttpStepKw(
            steps,
            f"Bundle 后 ePass 购买单 search（orderId · {entry.DisplayName}）",
        )
        resp_search_order = PostOrdersEPassesSearch(
            token,
            order_id=purchase_order_id,
            step_code=kw_search_order["step_code"],
            step_title=kw_search_order["step_title"],
        )
        AssertHistoricalEpassSearchDetailsCoreFields(
            resp_search_order,
            expected_module=entry.ModuleInt,
            expected_order_id=purchase_order_id,
            expected_e_pass_id=e_pass_id,
            context=f"{entry.Label}-bundle-search-by-orderId",
        )

    CancelHistoricalUsageOrderAndVerify(
        token,
        steps,
        catalog=entry,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        context=f"{entry.Label}-bundle-cancel",
    )

    if purchase_order_id:
        CancelHistoricalPurchaseOrderAndVerify(
            token,
            steps,
            catalog=entry,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            context=f"{entry.Label}-bundle-purchase-cancel",
        )

    return HistoricalEpassPrebookingResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=purchase_order_id,
        UsageOrderId=usage_order_id,
        PrebookingToken=pb_token,
        PrebookingDate=pb_date,
        Catalog=entry,
    )


__all__ = [
    "RunHistoricalEpassBundleMainE2EScenario",
    "RunHistoricalEpassCreateMainE2EScenario",
    "RunHistoricalEpassPrebookingMainE2EScenario",
]
