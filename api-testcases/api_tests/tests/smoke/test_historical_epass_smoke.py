"""历史品类 ePass 冒烟 — 休息室创建链最小回归。"""
from __future__ import annotations

import allure
import pytest

from clients import GetAccessTokenForEpass
from config.historical_epass_env import GetHistoricalEpassCatalogByLabel
from scenarios.historical_epass_scenarios import RunHistoricalEpassCreateMainE2EScenario
from services.historical_epass_service import RequireHistoricalEpassEnvOrSkip

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.regression,
    pytest.mark.historical_epass,
    pytest.mark.needs_write,
]


@pytest.fixture
def EpassToken() -> str:
    entry = GetHistoricalEpassCatalogByLabel("lounge")
    assert entry is not None
    RequireHistoricalEpassEnvOrSkip(entry)
    return GetAccessTokenForEpass()


@allure.feature("历史品类 ePass")
@allure.story("smoke · 休息室创建验证链")
def test_HistoricalEpass_Smoke_LoungeCreateChain(EpassToken: str, ScenarioSteps) -> None:
    RunHistoricalEpassCreateMainE2EScenario(EpassToken, ScenarioSteps, catalog_label="lounge")
