"""
eSIM + Local Offer 权益矩阵 — 单场景 12 步编排。

覆盖脑图 tc-p1：仅 eSIM 权益 / 无 LO 权益 / LO 权益点数边界 / 无 ePassId token 等。

**链路概要**（与手工用例步骤 1–12 对齐；步骤 8/10 的 token 取**紧前可用性** 7/9 的
``prebookingToken``，因步骤 4 的 token 绑定 esim-only ePassId，不可用于 LO ePass 成功预约）：

1. ``POST /v2/orders/esims/ePasses`` module=8，2 点 → esimEpassId
2–3. module=8 可用性 + ``/v2/orders/esims/ePasses/prebooking`` → 成功
4–5. module=11 可用性（同 esim 资源，esim ePassId）→ token；LO 预约 → **失败**
6. ``POST /v2/orders/localOffers/ePasses`` 同 clientUserId，2 点 → loEpassId
7–8. module=11 可用性（lo ePassId）→ token；LO 预约 → **成功**
9–10. module=11 可用性（不传 ePassId）→ token；LO 预约 → **成功**
11. 重复 9–10 → **失败**（权益不足或 token/点数限制）
12. 重复 2–3 esim 预约 → **成功**（eSIM 权益独立）
"""
from __future__ import annotations

import json
from typing import Any

import allure

from framework.soft_assert import LocalOfferFailOrRecord

from services.local_offer_epass_service import (
    AssertEsimPrebookingOrderSuccess,
    AssertLocalOfferPrebookingOrderSuccess,
    AssertPrebookingStepRejected,
    BuildEntitlementMatrixPrebookingDate1030,
    CreateModuleEpassOrFail,
    ESIM_MODULE_INT,
    ESIM_PATH_MODULE,
    LOCAL_OFFER_MODULE_INT,
    LOCAL_OFFER_PATH_MODULE,
    PostOrdersPathModuleEPassesPrebooking,
    RequestLocalOfferAvailabilityTokenPreferEsimResource,
    RequestModulePrebookingTokenOrFail,
    ResolveEsimPrebookingTargetOrSkip,
    ResolvePrebookingTargetByLabel,
    CancelPurchaseOrderAndVerifyPostCancelRetrieve,
    CancelUsageOrderAndVerifyPostCancelRetrieve,
    _HttpStepKw,
)


def RunLocalOfferEsimLoEntitlementMatrixScenario(token: str, steps: Any) -> None:
    """eSIM-only → LO 补权益 → 点数边界，单条 pytest 跑完 12 步。"""
    pb_date = BuildEntitlementMatrixPrebookingDate1030()
    esim_target = ResolveEsimPrebookingTargetOrSkip(token, steps)
    lo_fallback = ResolvePrebookingTargetByLabel("redemption_code")

    with allure.step("权益矩阵场景上下文"):
        allure.attach(
            json.dumps(
                {
                    "prebookingDate": pb_date,
                    "esimResourceId": esim_target.ResourceId,
                    "esimOptionId": esim_target.OptionId,
                    "availableUsagesPerEpass": 2,
                },
                ensure_ascii=False,
                indent=2,
            ),
            name="entitlement_matrix_context",
            attachment_type=allure.attachment_type.JSON,
        )

    def _CancelAndVerify(
        *,
        e_pass_id: str,
        purchase_order_id: str,
        usage_order_id: str,
        native_module: int,
        client_user_id: str,
        resource_id: str,
        option_id: str,
        context: str,
    ) -> None:
        CancelUsageOrderAndVerifyPostCancelRetrieve(
            token,
            steps,
            usage_order_id=usage_order_id,
            e_pass_id=e_pass_id,
            purchase_order_id=purchase_order_id,
            client_user_id=client_user_id,
            resource_id=resource_id,
            option_id=option_id,
            native_module=native_module,
            context=context,
        )

    # 1 — 注册 eSIM ePass（2 点）
    esim_cid, esim_e_pass_id, esim_purchase = CreateModuleEpassOrFail(
        token,
        steps,
        path_module=ESIM_PATH_MODULE,
        module=ESIM_MODULE_INT,
        available_usages=2,
        step_brief="步骤1 · 注册 eSIM ePass（module=8，2 点）",
    )

    # 2–3 — eSIM module=8 可用性 + 预约成功
    token_esim_m8 = RequestModulePrebookingTokenOrFail(
        token,
        steps,
        module=ESIM_MODULE_INT,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        prebooking_date=pb_date,
        e_pass_id=esim_e_pass_id,
        brief="步骤2 · eSIM 可用性 module=8",
    )
    kw_esim_book = _HttpStepKw(steps, "步骤3 · eSIM 预约 module=8")
    resp_esim_book = PostOrdersPathModuleEPassesPrebooking(
        token,
        ESIM_PATH_MODULE,
        module=ESIM_MODULE_INT,
        e_pass_id=esim_e_pass_id,
        prebooking_token=token_esim_m8,
        step_code=kw_esim_book["step_code"],
        step_title=kw_esim_book["step_title"],
    )
    esim_usage_order_1 = AssertEsimPrebookingOrderSuccess(
        resp_esim_book,
        e_pass_id=esim_e_pass_id,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        context="step3-esim-prebook",
    )
    _CancelAndVerify(
        e_pass_id=esim_e_pass_id,
        purchase_order_id=esim_purchase,
        usage_order_id=esim_usage_order_1,
        native_module=ESIM_MODULE_INT,
        client_user_id=esim_cid,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        context="step3-esim-cancel",
    )

    # 4–5 — module=11 可用性（esim ePassId）可拿 token；LO 预约失败（无 LO 权益）
    token_lo_on_esim_epass, lo_res_4, lo_opt_4 = RequestLocalOfferAvailabilityTokenPreferEsimResource(
        token,
        steps,
        prebooking_date=pb_date,
        e_pass_id=esim_e_pass_id,
        esim_target=esim_target,
        lo_fallback_target=lo_fallback,
        brief="步骤4 · LO 可用性 module=11（esim ePassId）",
    )
    kw_lo_fail = _HttpStepKw(steps, "步骤5 · LO 预约 module=11（esim ePass 无 LO 权益）")
    resp_lo_fail = PostOrdersPathModuleEPassesPrebooking(
        token,
        LOCAL_OFFER_PATH_MODULE,
        module=LOCAL_OFFER_MODULE_INT,
        e_pass_id=esim_e_pass_id,
        prebooking_token=token_lo_on_esim_epass,
        step_code=kw_lo_fail["step_code"],
        step_title=kw_lo_fail["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_lo_fail,
        expected_err_codes=("500.110.029", "500.110.019", "500.110.028", "500.110.001"),
        context="step5-esim-epass-lo-prebook",
    )

    # 6 — 同 clientUserId 注册 LO ePass（2 点）
    _lo_cid, lo_e_pass_id, lo_purchase = CreateModuleEpassOrFail(
        token,
        steps,
        path_module=LOCAL_OFFER_PATH_MODULE,
        module=LOCAL_OFFER_MODULE_INT,
        client_user_id=esim_cid,
        available_usages=2,
        step_brief="步骤6 · 注册 LO ePass（module=11，同 clientUserId，2 点）",
    )

    # 7–8 — LO ePass + module=11 可用性 → 预约成功
    token_lo_with_epass, lo_res_7, lo_opt_7 = RequestLocalOfferAvailabilityTokenPreferEsimResource(
        token,
        steps,
        prebooking_date=pb_date,
        e_pass_id=lo_e_pass_id,
        esim_target=esim_target,
        lo_fallback_target=lo_fallback,
        brief="步骤7 · LO 可用性 module=11（LO ePassId）",
    )
    kw_lo_ok1 = _HttpStepKw(steps, "步骤8 · LO 预约（token 来自步骤7）")
    resp_lo_ok1 = PostOrdersPathModuleEPassesPrebooking(
        token,
        LOCAL_OFFER_PATH_MODULE,
        module=LOCAL_OFFER_MODULE_INT,
        e_pass_id=lo_e_pass_id,
        prebooking_token=token_lo_with_epass,
        step_code=kw_lo_ok1["step_code"],
        step_title=kw_lo_ok1["step_title"],
    )
    lo_usage_order_1 = AssertLocalOfferPrebookingOrderSuccess(
        resp_lo_ok1,
        e_pass_id=lo_e_pass_id,
        resource_id=lo_res_7,
        option_id=lo_opt_7,
        context="step8-lo-prebook-with-epass-token",
    )
    _CancelAndVerify(
        e_pass_id=lo_e_pass_id,
        purchase_order_id=lo_purchase,
        usage_order_id=lo_usage_order_1,
        native_module=LOCAL_OFFER_MODULE_INT,
        client_user_id=esim_cid,
        resource_id=lo_res_7,
        option_id=lo_opt_7,
        context="step8-lo-cancel",
    )

    # 9–10 — 不传 ePassId 可用性 → LO 预约成功
    token_lo_no_epass, lo_res_9, lo_opt_9 = RequestLocalOfferAvailabilityTokenPreferEsimResource(
        token,
        steps,
        prebooking_date=pb_date,
        e_pass_id=None,
        esim_target=esim_target,
        lo_fallback_target=lo_fallback,
        brief="步骤9 · LO 可用性 module=11（不传 ePassId）",
    )
    kw_lo_ok2 = _HttpStepKw(steps, "步骤10 · LO 预约（token 来自步骤9）")
    resp_lo_ok2 = PostOrdersPathModuleEPassesPrebooking(
        token,
        LOCAL_OFFER_PATH_MODULE,
        module=LOCAL_OFFER_MODULE_INT,
        e_pass_id=lo_e_pass_id,
        prebooking_token=token_lo_no_epass,
        step_code=kw_lo_ok2["step_code"],
        step_title=kw_lo_ok2["step_title"],
    )
    lo_usage_order_2 = AssertLocalOfferPrebookingOrderSuccess(
        resp_lo_ok2,
        e_pass_id=lo_e_pass_id,
        resource_id=lo_res_9,
        option_id=lo_opt_9,
        context="step10-lo-prebook-no-epass-token",
    )
    _CancelAndVerify(
        e_pass_id=lo_e_pass_id,
        purchase_order_id=lo_purchase,
        usage_order_id=lo_usage_order_2,
        native_module=LOCAL_OFFER_MODULE_INT,
        client_user_id=esim_cid,
        resource_id=lo_res_9,
        option_id=lo_opt_9,
        context="step10-lo-cancel",
    )

    # 11 — 重复 9–10，预期失败（2 点已用尽或 token/权益限制）
    token_lo_no_epass_2, _lo_res_11, _lo_opt_11 = RequestLocalOfferAvailabilityTokenPreferEsimResource(
        token,
        steps,
        prebooking_date=pb_date,
        e_pass_id=None,
        esim_target=esim_target,
        lo_fallback_target=lo_fallback,
        brief="步骤11a · 重复 LO 可用性（不传 ePassId）",
    )
    kw_lo_fail2 = _HttpStepKw(steps, "步骤11b · 重复 LO 预约（预期失败）")
    resp_lo_fail2 = PostOrdersPathModuleEPassesPrebooking(
        token,
        LOCAL_OFFER_PATH_MODULE,
        module=LOCAL_OFFER_MODULE_INT,
        e_pass_id=lo_e_pass_id,
        prebooking_token=token_lo_no_epass_2,
        step_code=kw_lo_fail2["step_code"],
        step_title=kw_lo_fail2["step_title"],
    )
    AssertPrebookingStepRejected(
        resp_lo_fail2,
        expected_err_codes=("500.110.029", "500.110.028", "500.110.027", "500.110.019"),
        context="step11-lo-prebook-exhausted",
    )

    # 12 — 重复 esim module=8 预约，仍应成功（eSIM 权益与 LO 独立）
    token_esim_m8_2 = RequestModulePrebookingTokenOrFail(
        token,
        steps,
        module=ESIM_MODULE_INT,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        prebooking_date=pb_date,
        e_pass_id=esim_e_pass_id,
        brief="步骤12a · 重复 eSIM 可用性 module=8",
    )
    kw_esim_book2 = _HttpStepKw(steps, "步骤12b · 重复 eSIM 预约 module=8")
    resp_esim_book2 = PostOrdersPathModuleEPassesPrebooking(
        token,
        ESIM_PATH_MODULE,
        module=ESIM_MODULE_INT,
        e_pass_id=esim_e_pass_id,
        prebooking_token=token_esim_m8_2,
        step_code=kw_esim_book2["step_code"],
        step_title=kw_esim_book2["step_title"],
    )
    esim_usage_order_2 = AssertEsimPrebookingOrderSuccess(
        resp_esim_book2,
        e_pass_id=esim_e_pass_id,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        context="step12-esim-prebook-again",
    )
    _CancelAndVerify(
        e_pass_id=esim_e_pass_id,
        purchase_order_id=esim_purchase,
        usage_order_id=esim_usage_order_2,
        native_module=ESIM_MODULE_INT,
        client_user_id=esim_cid,
        resource_id=esim_target.ResourceId,
        option_id=esim_target.OptionId,
        context="step12-esim-cancel",
    )

    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        e_pass_id=esim_e_pass_id,
        purchase_order_id=esim_purchase,
        context="entitlement-matrix-esim-purchase-cancel",
    )
    CancelPurchaseOrderAndVerifyPostCancelRetrieve(
        token,
        steps,
        e_pass_id=lo_e_pass_id,
        purchase_order_id=lo_purchase,
        context="entitlement-matrix-lo-purchase-cancel",
    )


__all__ = ["RunLocalOfferEsimLoEntitlementMatrixScenario"]
