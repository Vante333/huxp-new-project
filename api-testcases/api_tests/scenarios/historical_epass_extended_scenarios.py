"""
历史品类 ePass 扩展主链路编排。

覆盖资源只读/价格、module 轮询、Topup、Checkin、Simulation、Event、Internal 等 MCP 补充接口。
"""
from __future__ import annotations

from typing import Any, Optional

from config.historical_epass_env import (
    GetConfiguredHistoricalEpassCatalog,
    HistoricalEpassCatalogEntry,
    GetHistoricalEpassCatalogByLabel,
)
from services.historical_epass_service import CreateHistoricalEpass
from services.historical_epass_extended_service import (
    RunHistoricalEsimTopupMainE2EScenario,
    RunHistoricalEventRecoveryModuleSweep,
    RunHistoricalFitnessCheckinMainE2EScenario,
    RunHistoricalInternalOrdersListOrSkip,
    RunHistoricalOrdersListModuleSweep,
    RunHistoricalResourcesReadForCatalog,
    RunHistoricalSimulationPrebookingMainE2EScenario,
)


def RunHistoricalEpassResourcesReadMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: Optional[HistoricalEpassCatalogEntry] = None,
    catalog_label: str = "lounge",
) -> None:
    """创建 ePass 后按品类 module 拉资源/价格只读链。"""
    entry = catalog or GetHistoricalEpassCatalogByLabel(catalog_label)
    if entry is None:
        raise ValueError(f"未知 historical epass catalog label: {catalog_label!r}")
    created = CreateHistoricalEpass(token, steps, entry)
    RunHistoricalResourcesReadForCatalog(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
    )


def RunHistoricalEpassModuleSweepMainE2EScenario(
    token: str,
    steps: Any,
    *,
    catalog: Optional[HistoricalEpassCatalogEntry] = None,
    catalog_label: str = "lounge",
) -> None:
    """创建 ePass 后 orders 列表 / internal 列表 / event 按 module 轮询。"""
    entry = catalog or GetHistoricalEpassCatalogByLabel(catalog_label)
    if entry is None:
        raise ValueError(f"未知 historical epass catalog label: {catalog_label!r}")
    created = CreateHistoricalEpass(token, steps, entry)
    RunHistoricalOrdersListModuleSweep(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
    )
    RunHistoricalInternalOrdersListOrSkip(
        token,
        steps,
        catalog=entry,
        e_pass_id=created.EPassId,
    )


def RunHistoricalEpassAllModulesEventSweepScenario(
    token: str,
    steps: Any,
) -> None:
    """对已配置的全部品类轮询 ``GET /v2/event?module=``。"""
    for entry in GetConfiguredHistoricalEpassCatalog():
        RunHistoricalEventRecoveryModuleSweep(token, steps, catalog=entry)


__all__ = [
    "RunHistoricalEpassAllModulesEventSweepScenario",
    "RunHistoricalEpassModuleSweepMainE2EScenario",
    "RunHistoricalEpassResourcesReadMainE2EScenario",
    "RunHistoricalEsimTopupMainE2EScenario",
    "RunHistoricalFitnessCheckinMainE2EScenario",
    "RunHistoricalSimulationPrebookingMainE2EScenario",
]
