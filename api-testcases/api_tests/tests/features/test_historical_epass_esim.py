"""
eSIM ePass 主链路 E2E 入口（历史品类 · module=8）。

与 ``test_historical_epass_regression.py`` 四类 parametrize 并存：本文件仅保留 **eSIM** 三条 P0 冒烟/E2E，
便于 ``-m smoke`` 或 ``historical_epass`` 快速回归。

主链路：``RunHistoricalEpass*MainE2EScenario(catalog_label='esim')`` · ``config/historical_epass_env.py``
"""
from __future__ import annotations

import allure
import pytest

from clients import GetAccessTokenForEpass
from config.historical_epass_env import GetHistoricalEpassCatalogByLabel
from framework.reporting import AllureHttpScenarioSteps
from scenarios.historical_epass_scenarios import (
    RunHistoricalEpassBundleMainE2EScenario,
    RunHistoricalEpassCreateMainE2EScenario,
    RunHistoricalEpassPrebookingMainE2EScenario,
)
from services.historical_epass_service import RequireHistoricalEpassEnvOrSkip

pytestmark = [
    pytest.mark.feature,
    pytest.mark.historical_epass,
    pytest.mark.needs_write,
]


@pytest.fixture
def EpassToken() -> str:
    """ePass 三件套取 token（eSIM catalog 配置校验）。"""
    entry = GetHistoricalEpassCatalogByLabel("esim")
    assert entry is not None
    RequireHistoricalEpassEnvOrSkip(entry)
    token = GetAccessTokenForEpass()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token


@allure.feature("eSIM ePass")
@allure.story("E2E · 创建验证链")
@pytest.mark.smoke
def test_HistoricalEpassEsim_E2E_CreateMainChain(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    主链路 1：``POST /v2/orders/esims/ePasses`` → ``POST /v2/users/ePasses`` →
    ``POST /v2/orders/ePasses/search``（orderId + ePassId）→ 取消 MS 购买单。
    """
    RunHistoricalEpassCreateMainE2EScenario(EpassToken, ScenarioSteps, catalog_label="esim")


@allure.feature("eSIM ePass")
@allure.story("E2E · Prebooking 验证链")
@pytest.mark.smoke
def test_HistoricalEpassEsim_E2E_PrebookingMainChain(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    主链路 2：创建 ePass → options 可用性（module=8）→ 预约下单 →
    取消 usage 单 → 取消 MS 购买单。
    """
    RunHistoricalEpassPrebookingMainE2EScenario(EpassToken, ScenarioSteps, catalog_label="esim")


@allure.feature("eSIM ePass")
@allure.story("E2E · Bundle 一步下单链")
@pytest.mark.smoke
def test_HistoricalEpassEsim_E2E_BundleMainChain(
    EpassToken: str,
    ScenarioSteps: AllureHttpScenarioSteps,
) -> None:
    """
    主链路 3（Bundle）：可用性（无 ePassId）→ ``POST .../esims/ePasses/bundle`` →
    users → search → 取消 usage 单 → 取消 MS 购买单。
    """
    RunHistoricalEpassBundleMainE2EScenario(EpassToken, ScenarioSteps, catalog_label="esim")
