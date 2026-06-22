"""
历史品类 ePass 扩展回归 — Topup / 资源只读 / module 轮询 / Simulation / Checkin 等。

对齐 MCP Q2 local offer OAS 中尚未覆盖的 ePass 相关接口。
"""
from __future__ import annotations

import allure
import pytest

from config.historical_epass_env import (
    GetConfiguredHistoricalEpassCatalog,
    GetHistoricalEpassCatalog,
    GetHistoricalEpassCoreCatalog,
    GetHistoricalSimulationPaths,
    HistoricalEpassCatalogEntry,
)
from scenarios.historical_epass_extended_scenarios import (
    RunHistoricalEpassAllModulesEventSweepScenario,
    RunHistoricalEpassModuleSweepMainE2EScenario,
    RunHistoricalEpassResourcesReadMainE2EScenario,
    RunHistoricalEsimTopupMainE2EScenario,
    RunHistoricalFitnessCheckinMainE2EScenario,
    RunHistoricalSimulationPrebookingMainE2EScenario,
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


def _CatalogIds(include_optional: bool = True) -> list[str]:
    if include_optional:
        return [entry.Label for entry in GetHistoricalEpassCatalog()]
    return [entry.Label for entry in GetHistoricalEpassCoreCatalog()]


def _CatalogByLabel(label: str) -> HistoricalEpassCatalogEntry:
    for entry in GetHistoricalEpassCatalog():
        if entry.Label == label:
            return entry
    raise KeyError(label)


@pytest.fixture(params=_CatalogIds(include_optional=True))
def HistoricalCatalogEntry(request: pytest.FixtureRequest) -> HistoricalEpassCatalogEntry:
    entry = _CatalogByLabel(request.param)
    RequireHistoricalEpassEnvOrSkip(entry)
    return entry


@pytest.fixture(params=_CatalogIds(include_optional=False))
def HistoricalCoreCatalogEntry(request: pytest.FixtureRequest) -> HistoricalEpassCatalogEntry:
    entry = _CatalogByLabel(request.param)
    RequireHistoricalEpassEnvOrSkip(entry)
    return entry


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("资源只读与价格 · 按品类 module")
def test_HistoricalEpass_Extended_ResourcesRead_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    HistoricalCatalogEntry: HistoricalEpassCatalogEntry,
) -> None:
    RunHistoricalEpassResourcesReadMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=HistoricalCatalogEntry,
    )


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("orders/internal/event · module 轮询")
def test_HistoricalEpass_Extended_ModuleSweep_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    HistoricalCatalogEntry: HistoricalEpassCatalogEntry,
) -> None:
    RunHistoricalEpassModuleSweepMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=HistoricalCatalogEntry,
    )


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("eSIM EPass Topup 链")
def test_HistoricalEpass_Extended_EsimTopupMainChain(
    EpassToken: str,
    ScenarioSteps,
) -> None:
    entry = _CatalogByLabel("esim")
    RequireHistoricalEpassEnvOrSkip(entry)
    RunHistoricalEsimTopupMainE2EScenario(EpassToken, ScenarioSteps, catalog=entry)


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("fitness Checkin")
def test_HistoricalEpass_Extended_FitnessCheckin(
    EpassToken: str,
    ScenarioSteps,
) -> None:
    entry = _CatalogByLabel("fitness")
    RequireHistoricalEpassEnvOrSkip(entry)
    RunHistoricalFitnessCheckinMainE2EScenario(EpassToken, ScenarioSteps, catalog=entry)


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("Simulation 预约核销")
@pytest.mark.parametrize(
    "catalog_label",
    [label for label in _CatalogIds(include_optional=True) if GetHistoricalSimulationPaths(label)],
)
def test_HistoricalEpass_Extended_SimulationPrebooking_ByCategory(
    EpassToken: str,
    ScenarioSteps,
    catalog_label: str,
) -> None:
    entry = _CatalogByLabel(catalog_label)
    RequireHistoricalEpassEnvOrSkip(entry)
    RunHistoricalSimulationPrebookingMainE2EScenario(
        EpassToken,
        ScenarioSteps,
        catalog=entry,
    )


@allure.feature("历史品类 ePass 扩展回归")
@allure.story("Event 恢复 · 全品类 module 轮询")
def test_HistoricalEpass_Extended_EventRecovery_AllModules(
    EpassToken: str,
    ScenarioSteps,
) -> None:
    configured = GetConfiguredHistoricalEpassCatalog()
    if not configured:
        pytest.skip("无已配置的历史 ePass 品类")
    RunHistoricalEpassAllModulesEventSweepScenario(EpassToken, ScenarioSteps)
