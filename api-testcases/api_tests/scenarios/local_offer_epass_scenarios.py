"""
Local Offer ePass 主链路编排。

对外暴露 ``RunLocalOfferEpassCreateMainE2EScenario`` 与 ``RunLocalOfferEpassPrebookingMainE2EScenario``；
主 E2E 用例仅调用上述入口。
"""
from __future__ import annotations

import uuid
from typing import Any, Mapping, Optional, Sequence

from services.local_offer_epass_service import (
    AssertBundleOrderSuccess,
    AssertEpassSearchDetailsCoreFields,
    AssertLocalOfferPrebookingOrderSuccess,
    AssertUserEPassesContains,
    CancelPurchaseOrderAndVerifyPostCancelRetrieve,
    CancelUsageOrderAndVerifyPostCancelRetrieve,
    CreateLocalOfferEpass,
    ExtractBusinessData,
    LocalOfferEpassCreateResult,
    LocalOfferEpassPrebookingResult,
    LocalOfferPrebookingTarget,
    LOCAL_OFFER_PATH_MODULE,
    PostOrdersEPassesList,
    PostOrdersEPassesSearch,
    PostOrdersLocalOffersEPassesBundle,
    PostOrdersLocalOffersEPassesPrebooking,
    PostUsersEPasses,
    RequestPrebookingToken,
    RequestPrebookingTokenWithoutEpass,
    ResolvePrebookingTargetByLabel,
    ResolvePrebookingTargetViaResourceChainOrSkip,
    _HttpStepKw,
)


def RunLocalOfferEpassCreateMainE2EScenario(
    token: str,
    steps: Any,
    *,
    allowed_resources: Optional[Mapping[str, Sequence[str]]] = None,
    client_user_id: Optional[str] = None,
) -> LocalOfferEpassCreateResult:
    """
    EPass 创建验证链（Local Offer / module=11）：

    ``POST /v2/orders/localOffers/ePasses`` → ``POST /v2/users/ePasses`` →
    ``POST /v2/orders/ePasses``（列表，创建后可能为空）→ ``POST /v2/orders/ePasses/search``
    """
    created = CreateLocalOfferEpass(
        token,
        steps,
        allowed_resources=allowed_resources,
        client_user_id=client_user_id,
    )

    kw_users = _HttpStepKw(steps, "查询用户 ePass 列表")
    resp_users = PostUsersEPasses(
        token,
        created.ClientUserId,
        step_code=kw_users["step_code"],
        step_title=kw_users["step_title"],
    )
    AssertUserEPassesContains(resp_users, e_pass_id=created.EPassId)

    kw_search_order = _HttpStepKw(steps, "ePass 购买单详情（orderId）")
    resp_search_order = PostOrdersEPassesSearch(
        token,
        order_id=created.PurchaseOrderId,
        step_code=kw_search_order["step_code"],
        step_title=kw_search_order["step_title"],
    )
    AssertEpassSearchDetailsCoreFields(
        resp_search_order,
        expected_order_id=created.PurchaseOrderId,
        expected_e_pass_id=created.EPassId,
        context="by-orderId",
    )

    kw_search_epass = _HttpStepKw(steps, "ePass 购买单详情（ePassId）")
    resp_search_epass = PostOrdersEPassesSearch(
        token,
        e_pass_id=created.EPassId,
        step_code=kw_search_epass["step_code"],
        step_title=kw_search_epass["step_title"],
    )
    AssertEpassSearchDetailsCoreFields(
        resp_search_epass,
        expected_order_id=created.PurchaseOrderId,
        expected_e_pass_id=created.EPassId,
        context="by-ePassId",
    )

    kw_list = _HttpStepKw(steps, "ePass usage 订单列表（创建后可能为空）")
    resp_list = PostOrdersEPassesList(
        token,
        created.EPassId,
        step_code=kw_list["step_code"],
        step_title=kw_list["step_title"],
    )
    ExtractBusinessData(resp_list)

    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="create-main-cancel",
    )

    return created


def RunLocalOfferEpassPrebookingMainE2EScenario(
    token: str,
    steps: Any,
    *,
    target: Optional[LocalOfferPrebookingTarget] = None,
    target_label: str = "url",
    allowed_resources: Optional[Mapping[str, Sequence[str]]] = None,
) -> LocalOfferEpassPrebookingResult:
    """
    EPass Prebooking 链（Local Offer）：

    创建 ePass → 可用性 → 预约下单 → 取消 usage 单 → 详情/列表/search 查询。
    """
    booking_target = target or ResolvePrebookingTargetViaResourceChainOrSkip(
        token, steps, label=target_label
    )

    created = CreateLocalOfferEpass(token, steps, allowed_resources=allowed_resources)

    prebooking_token, prebooking_date = RequestPrebookingToken(
        token,
        steps,
        e_pass_id=created.EPassId,
        target=booking_target,
    )

    kw_book = _HttpStepKw(steps, f"Local Offer ePass 预约下单（{booking_target.Label}）")
    resp_book = PostOrdersLocalOffersEPassesPrebooking(
        token,
        created.EPassId,
        prebooking_token,
        step_code=kw_book["step_code"],
        step_title=kw_book["step_title"],
    )
    usage_order_id = AssertLocalOfferPrebookingOrderSuccess(
        resp_book,
        e_pass_id=created.EPassId,
        resource_id=booking_target.ResourceId,
        option_id=booking_target.OptionId,
        expected_voucher_type=booking_target.ExpectedVoucherType,
        context=booking_target.Label,
    )

    CancelUsageOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        client_user_id=created.ClientUserId,
        resource_id=booking_target.ResourceId,
        option_id=booking_target.OptionId,
        context=f"prebooking-{booking_target.Label}-cancel",
    )

    return LocalOfferEpassPrebookingResult(
        ClientUserId=created.ClientUserId,
        EPassId=created.EPassId,
        PurchaseOrderId=created.PurchaseOrderId,
        UsageOrderId=usage_order_id,
        PrebookingToken=prebooking_token,
        ResourceId=booking_target.ResourceId,
        OptionId=booking_target.OptionId,
        PrebookingDate=prebooking_date,
    )


def RunLocalOfferEpassBundleMainE2EScenario(
    token: str,
    steps: Any,
    *,
    target: Optional[LocalOfferPrebookingTarget] = None,
    target_label: str = "redemption_code",
    client_user_id: Optional[str] = None,
) -> LocalOfferEpassPrebookingResult:
    """
    Bundle 主链路：可用性（无 ePassId）→ ``POST .../ePasses/bundle`` → users →
    ``POST /v2/orders/ePasses/search``（ePassId → orderId → orderId 二次查询）→ usage 详情 → 订单列表。
    """
    booking_target = target or ResolvePrebookingTargetViaResourceChainOrSkip(
        token, steps, label=target_label
    )
    cid = client_user_id or str(uuid.uuid4())
    pb_token, pb_date = RequestPrebookingTokenWithoutEpass(token, steps, target=booking_target)

    kw_bundle = _HttpStepKw(steps, f"Local Offer ePass Bundle（{booking_target.Label}）")
    resp_bundle = PostOrdersLocalOffersEPassesBundle(
        token,
        cid,
        pb_token,
        step_code=kw_bundle["step_code"],
        step_title=kw_bundle["step_title"],
    )
    e_pass_id, usage_order_id = AssertBundleOrderSuccess(
        resp_bundle,
        expected_client_user_id=cid,
        resource_id=booking_target.ResourceId,
        option_id=booking_target.OptionId,
        expected_voucher_type=booking_target.ExpectedVoucherType,
        context=booking_target.Label,
    )

    kw_users = _HttpStepKw(steps, "Bundle 后查询用户 ePass 列表")
    resp_users = PostUsersEPasses(
        token,
        cid,
        step_code=kw_users["step_code"],
        step_title=kw_users["step_title"],
    )
    AssertUserEPassesContains(resp_users, e_pass_id=e_pass_id)

    kw_search = _HttpStepKw(steps, "Bundle 后 ePass 购买单详情（ePassId）")
    resp_search = PostOrdersEPassesSearch(
        token,
        e_pass_id=e_pass_id,
        step_code=kw_search["step_code"],
        step_title=kw_search["step_title"],
    )
    AssertEpassSearchDetailsCoreFields(
        resp_search,
        expected_e_pass_id=e_pass_id,
        context="bundle-search-by-ePassId",
    )

    search_data = ExtractBusinessData(resp_search)
    purchase_order_id = search_data.get("orderId")
    if not isinstance(purchase_order_id, str):
        purchase_order_id = ""

    if purchase_order_id:
        kw_search_order = _HttpStepKw(steps, "Bundle 后 ePass 购买单详情（orderId）")
        resp_search_order = PostOrdersEPassesSearch(
            token,
            order_id=purchase_order_id,
            step_code=kw_search_order["step_code"],
            step_title=kw_search_order["step_title"],
        )
        AssertEpassSearchDetailsCoreFields(
            resp_search_order,
            expected_order_id=purchase_order_id,
            expected_e_pass_id=e_pass_id,
            context="bundle-search-by-orderId",
        )

    CancelUsageOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        usage_order_id=usage_order_id,
        e_pass_id=e_pass_id,
        purchase_order_id=purchase_order_id,
        client_user_id=cid,
        resource_id=booking_target.ResourceId,
        option_id=booking_target.OptionId,
        context=f"bundle-{booking_target.Label}-cancel",
    )
    if purchase_order_id:
        CancelPurchaseOrderAndVerifyPostCancelRetrieve(
            token,
            steps,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            context=f"bundle-{booking_target.Label}-purchase-cancel",
        )

    return LocalOfferEpassPrebookingResult(
        ClientUserId=cid,
        EPassId=e_pass_id,
        PurchaseOrderId=purchase_order_id,
        UsageOrderId=usage_order_id,
        PrebookingToken=pb_token,
        ResourceId=booking_target.ResourceId,
        OptionId=booking_target.OptionId,
        PrebookingDate=pb_date,
    )


def RunLocalOfferEpassCreateThenCancelPurchaseScenario(
    token: str,
    steps: Any,
) -> LocalOfferEpassCreateResult:
    """
    创建 Local Offer ePass 后取消会籍购买单并查询 search。

    doc：注销 ePassId（``ePassStatus=3``），购买单本身不取消；SaaS 权益回退需人工核对。
    """
    created = CreateLocalOfferEpass(token, steps)
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        e_pass_id=created.EPassId,
        purchase_order_id=created.PurchaseOrderId,
        context="create-then-cancel-purchase",
    )
    return created


__all__ = [
    "RunLocalOfferEpassCreateMainE2EScenario",
    "RunLocalOfferEpassPrebookingMainE2EScenario",
    "RunLocalOfferEpassBundleMainE2EScenario",
    "RunLocalOfferEpassCreateThenCancelPurchaseScenario",
]
