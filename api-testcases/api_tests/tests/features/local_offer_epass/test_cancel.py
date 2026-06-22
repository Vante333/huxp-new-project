"""
Epass 取消订单模块 — PATCH /v2/orders。

用例来源：``testcases/2026Q2_SP3/LocalOffer订单相关-epass-测试用例-001.md`` · Epass 取消订单

usage 预订单取消及取消后 details/列表/search 已由
``RunLocalOfferEpassPrebookingMainE2EScenario``（``test_local_offer_epass.py``）覆盖，本文件仅保留会籍购买单取消。
"""
from __future__ import annotations

import allure
import pytest

from framework.reporting import AllureHttpScenarioSteps
from scenarios.local_offer_epass_scenarios import RunLocalOfferEpassCreateThenCancelPurchaseScenario
from services.local_offer_epass_service import AttachSaasManualCheckpoint

pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]


@allure.feature("Local Offer ePass")
@allure.story("Epass 取消订单 · 会籍购买单")
def test_LocalOfferEpass_CancelPurchaseOrder(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    tc-p1: 取消 ePass 会籍购买单（PATCH MS orderId）。

    接口侧：取消成功；search 侧 ``ePassStatus=3``，购买单 ``status=1`` 仍可查。
    SaaS 权益回退见 Allure 附件（不阻塞自动化）。
    """
    created = RunLocalOfferEpassCreateThenCancelPurchaseScenario(EpassToken, ScenarioSteps)
    AttachSaasManualCheckpoint(
        scenario="取消 ePass 会籍购买单 · SaaS 权益回退",
        checklist=[
            "会籍列表：ePass 已注销/权益已回退",
            "购买单 MS 状态与接口 search status=1 一致（购买单本身不取消）",
        ],
        context={
            "ePassId": created.EPassId,
            "purchaseOrderId": created.PurchaseOrderId,
            "clientUserId": created.ClientUserId,
        },
    )
