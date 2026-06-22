"""
历史品类 ePass 回归 — 四类主链路（创建 + 预约 + Bundle）。

目的：Local Offer（module=11）大改后，验证休息室 / 快速通道 / fitness / eSIM
历史接口主链路未被破坏。

对齐 ``api-testcases/docs/api-main-call-chains.md`` · EPass 创建验证链 / Prebooking 链 / Bundle 链。
"""
from __future__ import annotations

import allure
import pytest

from config.historical_epass_env import (
    GetHistoricalEpassCoreCatalog,
    HistoricalEpassCatalogEntry,
)
from scenarios.historical_epass_scenarios import (
    RunHistoricalEpassBundleMainE2EScenario,
    RunHistoricalEpassCreateMainE2EScenario,
    RunHistoricalEpassPrebookingMainE2EScenario,
)
from services.historical_epass_service import RequireHistoricalEpassEnvOrSkip

pytestmark = [
    pytest.mark.regression,
    pytest.mark.historical_epass,
    pytest.mark.needs_write,
]


@pytest.fixture
def EpassToken() -> str:
    from clients import GetAccessTokenForEpass

    RequireHistoricalEpassEnvOrSkip()
    return GetAccessTokenForEpass()


def _CatalogIds() -> list[str]:
    return [entry.Label for entry in GetHistoricalEpassCoreCatalog()]


def _CatalogByLabel(label: str) -> HistoricalEpassCatalogEntry:
    from config.historical_epass_env import GetHistoricalEpassCatalog

    for entry in GetHistoricalEpassCatalog():
        if entry.Label == label:
            return entry
    raise KeyError(label)


@pytest.fixture(params=_CatalogIds())
def HistoricalCatalogEntry(request: pytest.FixtureRequest) -> HistoricalEpassCatalogEntry:
    entry = _CatalogByLabel(request.param)
    RequireHistoricalEpassEnvOrSkip(entry)
    return entry


@allure.feature("历史品类 ePass 回归")
@allure.story("创建验证链 · 四类品类")
def test_HistoricalEpass_Regression_CreateMainChain_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    HistoricalCatalogEntry: HistoricalEpassCatalogEntry,
) -> None:
    """``POST /v2/orders/{module}/ePasses`` → users → search → 取消 MS 单。"""
    RunHistoricalEpassCreateMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=HistoricalCatalogEntry,
    )


@allure.feature("历史品类 ePass 回归")
@allure.story("Prebooking 链 · 四类品类")
def test_HistoricalEpass_Regression_PrebookingMainChain_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    HistoricalCatalogEntry: HistoricalEpassCatalogEntry,
) -> None:
    """创建 → 可用性 → prebooking → 取消 usage + MS 单。"""
    RunHistoricalEpassPrebookingMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=HistoricalCatalogEntry,
    )


@allure.feature("历史品类 ePass 回归")
@allure.story("Bundle 链 · 四类品类")
def test_HistoricalEpass_Regression_BundleMainChain_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    HistoricalCatalogEntry: HistoricalEpassCatalogEntry,
) -> None:
    """可用性（无 ePassId）→ bundle → users → search → 取消 usage + MS 单。"""
    RunHistoricalEpassBundleMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=HistoricalCatalogEntry,
    )
