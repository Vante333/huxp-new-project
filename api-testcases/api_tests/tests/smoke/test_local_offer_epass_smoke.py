"""Local Offer ePass 冒烟入口。"""
from __future__ import annotations

import allure
import pytest

from clients import GetAccessTokenForEpass
from scenarios.local_offer_epass_scenarios import RunLocalOfferEpassCreateMainE2EScenario
from services.local_offer_epass_service import RequireLocalOfferEpassEnvOrSkip

pytestmark = [pytest.mark.smoke, pytest.mark.local_offer_epass, pytest.mark.needs_write]


@pytest.fixture
def EpassToken() -> str:
    RequireLocalOfferEpassEnvOrSkip()
    return GetAccessTokenForEpass()


@allure.feature("Local Offer ePass")
@allure.story("smoke · 创建验证链")
def test_LocalOfferEpass_Smoke_CreateChain(EpassToken: str, ScenarioSteps) -> None:
    RunLocalOfferEpassCreateMainE2EScenario(EpassToken, ScenarioSteps)
