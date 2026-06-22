"""

沙箱 redemptionUrl 有值网点 · 主流程 E2E（网点由环境变量配置）。



与 ``test_local_offer_epass.py`` 中按 label（url/redemption_code/card_secret）参数化不同，

本模块 **一行表格 = 一条用例**，直接传入 ``LocalOfferPrebookingTarget``。



**环境变量**（见 ``env/.env.local-offer.example``）：



- ``DP_LO_EPASS_SANDBOX_VT5_RESOURCE_ID`` / ``DP_LO_EPASS_SANDBOX_VT5_OPTION_ID``（voucherType=5；vt4 场景已移除）



主链路：``RunLocalOfferEpassPrebookingMainE2EScenario``

"""

from __future__ import annotations



import os

from typing import Any, List, Tuple



import allure

import pytest



from framework.reporting import AllureHttpScenarioSteps

from scenarios.local_offer_epass_scenarios import RunLocalOfferEpassPrebookingMainE2EScenario

from services.local_offer_epass_service import LocalOfferPrebookingTarget



pytestmark = [pytest.mark.feature, pytest.mark.local_offer_epass, pytest.mark.needs_write]





def _BuildSandboxRedemptionUrlOutletParams() -> Tuple[Any, ...]:
    """从环境变量组装沙箱 redemptionUrl 有值网点参数。"""
    specs: List[Any] = []

    for voucher_type in (5,):

        resource_id = os.getenv(

            f"DP_LO_EPASS_SANDBOX_VT{voucher_type}_RESOURCE_ID",

            "",

        ).strip()

        option_id = os.getenv(

            f"DP_LO_EPASS_SANDBOX_VT{voucher_type}_OPTION_ID",

            "",

        ).strip()

        if not resource_id or not option_id:

            continue

        specs.append(

            pytest.param(

                voucher_type,

                resource_id,

                option_id,

                id=f"vt{voucher_type}-{resource_id}-{option_id}",

            )

        )

    if specs:

        return tuple(specs)

    return (

        pytest.param(

            0,

            "",

            "",

            marks=pytest.mark.skip(

                reason=(

                    "未配置沙箱 redemptionUrl 网点："

                    "DP_LO_EPASS_SANDBOX_VT5_* "

                    "（见 env/.env.local-offer.example）"

                )

            ),

            id="sandbox-outlets-not-configured",

        ),

    )





@allure.feature("Local Offer ePass")

@allure.story("E2E · 沙箱 redemptionUrl 有值网点 · 主流程")

@pytest.mark.parametrize(

    ("voucher_type", "resource_id", "option_id"),

    _BuildSandboxRedemptionUrlOutletParams(),

)

def test_LocalOfferEpass_E2E_SandboxRedemptionUrlOutlet_MainChain(

    EpassToken: str,

    ScenarioSteps: AllureHttpScenarioSteps,

    voucher_type: int,

    resource_id: str,

    option_id: str,

) -> None:

    """按环境变量指定网点跑预约主链路（下单 + 取消 + 查询）。"""

    allure.dynamic.title(

        f"主流程 · voucherType={voucher_type} · {resource_id} / {option_id}"

    )

    allure.dynamic.parameter("voucherType", voucher_type)

    allure.dynamic.parameter("resourceId", resource_id)

    allure.dynamic.parameter("optionId", option_id)



    target = LocalOfferPrebookingTarget(

        Label=f"sandbox-vt{voucher_type}-{resource_id}",

        ResourceId=resource_id,

        OptionId=option_id,

        ExpectedVoucherType=voucher_type,

        ExpectRedemptionUrlPresent=True,

    )

    RunLocalOfferEpassPrebookingMainE2EScenario(

        EpassToken,

        ScenarioSteps,

        target=target,

    )


