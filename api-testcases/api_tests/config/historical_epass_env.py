"""
历史品类 ePass 回归 — 环境变量与网点 catalog。

与 ``api-testcases/docs/api-main-call-chains.md`` · EPass 主链路对齐；用于 Local Offer 上线后
验证休息室 / 快速通道 / fitness / eSIM / setMeals / coupons 历史接口未被破坏。

| 品类 | path module | module int | 环境变量（resourceId / optionId） |
|------|-------------|------------|-----------------------------------|
| 休息室 | lounges | 1 | ``DP_HIST_EPASS_LOUNGE_RESOURCE_ID``（默认 N00012） |
| 快速通道 | fastTrack | 2 | ``DP_HIST_EPASS_FASTTRACK_RESOURCE_ID``（默认 C10826） |
| fitness | fitness | 7 | ``DP_HIST_EPASS_FITNESS_RESOURCE_ID``；``optionId``/时段由 ``GET .../fitness/{resourceId}/schedule`` 动态解析 |
| eSIM | esims | 8 | ``DP_HIST_EPASS_ESIM_RESOURCE_ID`` / ``_OPTION_ID`` |
| setMeals | setMeals | 3 | ``DP_HIST_EPASS_SETMEALS_RESOURCE_ID``（可选，未配则 skip） |
| coupons | coupons | 4 | ``DP_HIST_EPASS_COUPONS_RESOURCE_ID``（可选，未配则 skip） |

复制模板：``env/.env.historical-epass.example`` → 合并进 ``env/.env.<profile>``。
鉴权三件套与 Local Offer 共用 ``DP_EPASS_*``（见 ``config/local_offer_epass_env.py``）。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from config.local_offer_epass_env import (
    BuildLocalOfferPrebookingDate,
    GetEpassClientId,
    GetEpassClientSecret,
    GetEpassProgramId,
    IterLocalOfferPrebookingDateCandidates,
    ListMissingRequiredLocalOfferEpassEnv,
)


class HistoricalAvailabilityMode(str, Enum):
    """可用性接口路径：经典 ``/prebookings/availability`` 或 options 链。"""

    Classic = "classic"
    Options = "options"


@dataclass(frozen=True)
class HistoricalEpassCatalogEntry:
    """单品类 ePass 回归配置。"""

    Label: str
    DisplayName: str
    PathModule: str
    ModuleInt: int
    ResourceId: str
    OptionId: str
    AvailabilityMode: HistoricalAvailabilityMode
    Optional: bool = False


_SIMULATION_PATH_BY_LABEL: dict = {
    "lounge": (
        "/v2/simulations/lounges/prebookings/redemptions",
        "/v2/simulations/lounges/cancellation",
    ),
    "fastTrack": (
        "/v2/simulations/fastTrack/prebookings/redemptions",
        "/v2/simulations/fastTrack/cancellation",
    ),
    "setMeals": (
        "/v2/simulations/setMeals/redemptions",
        "/v2/simulations/setMeals/cancellation",
    ),
    "coupons": (
        "/v2/simulations/coupons/redemptions",
        "/v2/simulations/coupons/cancellation",
    ),
}


_CATALOG_META: Tuple[dict, ...] = (
    {
        "label": "lounge",
        "displayName": "休息室",
        "pathModule": "lounges",
        "moduleInt": 1,
        "envPrefix": "LOUNGE",
        "defaultResourceId": "N00012",
        "availabilityMode": HistoricalAvailabilityMode.Classic,
    },
    {
        "label": "fastTrack",
        "displayName": "快速通道",
        "pathModule": "fastTrack",
        "moduleInt": 2,
        "envPrefix": "FASTTRACK",
        "defaultResourceId": "C10826",
        "availabilityMode": HistoricalAvailabilityMode.Classic,
    },
    {
        "label": "fitness",
        "displayName": "fitness",
        "pathModule": "fitness",
        "moduleInt": 7,
        "envPrefix": "FITNESS",
        "defaultResourceId": "GR0000308",
        "defaultOptionId": "",
        "availabilityMode": HistoricalAvailabilityMode.Options,
    },
    {
        "label": "esim",
        "displayName": "eSIM",
        "pathModule": "esims",
        "moduleInt": 8,
        "envPrefix": "ESIM",
        "defaultResourceId": "GR0005901",
        "defaultOptionId": "SKU-GS0010955",
        "availabilityMode": HistoricalAvailabilityMode.Options,
    },
    {
        "label": "setMeals",
        "displayName": "setMeals",
        "pathModule": "setMeals",
        "moduleInt": 3,
        "envPrefix": "SETMEALS",
        "defaultResourceId": "",
        "availabilityMode": HistoricalAvailabilityMode.Classic,
        "optional": True,
    },
    {
        "label": "coupons",
        "displayName": "coupons",
        "pathModule": "coupons",
        "moduleInt": 4,
        "envPrefix": "COUPONS",
        "defaultResourceId": "",
        "availabilityMode": HistoricalAvailabilityMode.Classic,
        "optional": True,
    },
)


def _EnvFirst(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def GetHistoricalEpassResourceId(env_prefix: str, default: str) -> str:
    """``DP_HIST_EPASS_<PREFIX>_RESOURCE_ID`` → default。"""
    key = f"DP_HIST_EPASS_{env_prefix}_RESOURCE_ID"
    return _EnvFirst(key) or default


def GetHistoricalEpassOptionId(env_prefix: str, default: str = "") -> str:
    """``DP_HIST_EPASS_<PREFIX>_OPTION_ID`` → default（classic 品类可为空）。"""
    key = f"DP_HIST_EPASS_{env_prefix}_OPTION_ID"
    return _EnvFirst(key) or default


def BuildHistoricalEpassCatalogEntry(meta: dict) -> HistoricalEpassCatalogEntry:
    """由元数据 + 环境变量生成 catalog 条目。"""
    prefix = meta["envPrefix"]
    resource_id = GetHistoricalEpassResourceId(prefix, meta["defaultResourceId"])
    option_id = GetHistoricalEpassOptionId(prefix, meta.get("defaultOptionId", ""))
    return HistoricalEpassCatalogEntry(
        Label=meta["label"],
        DisplayName=meta["displayName"],
        PathModule=meta["pathModule"],
        ModuleInt=meta["moduleInt"],
        ResourceId=resource_id,
        OptionId=option_id,
        AvailabilityMode=meta["availabilityMode"],
        Optional=bool(meta.get("optional", False)),
    )


def GetHistoricalSimulationPaths(label: str) -> Optional[Tuple[str, str]]:
    """返回 ``(redemptionPath, cancellationPath)``；不支持 simulation 的品类为 ``None``。"""
    paths = _SIMULATION_PATH_BY_LABEL.get(label.strip())
    if paths is None:
        return None
    return paths


def GetHistoricalEpassCatalog(include_optional: bool = True) -> Tuple[HistoricalEpassCatalogEntry, ...]:
    """历史品类 catalog；``optional`` 条目在未配置 resourceId 时自动剔除。"""
    entries = tuple(BuildHistoricalEpassCatalogEntry(m) for m in _CATALOG_META)
    if include_optional:
        return entries
    return tuple(e for e in entries if not e.Optional)


def GetConfiguredHistoricalEpassCatalog() -> Tuple[HistoricalEpassCatalogEntry, ...]:
    """仅返回当前环境可跑的品类（optional 未配 resourceId 则 skip 列表不含）。"""
    configured: List[HistoricalEpassCatalogEntry] = []
    for entry in GetHistoricalEpassCatalog():
        if entry.Optional and not entry.ResourceId:
            continue
        if RequireHistoricalEpassCatalogOrSkipMessage(entry) is None:
            configured.append(entry)
    return tuple(configured)


def GetHistoricalEpassCoreCatalog() -> Tuple[HistoricalEpassCatalogEntry, ...]:
    """四类主链路品类（lounge / fastTrack / fitness / esim）。"""
    core_labels = frozenset({"lounge", "fastTrack", "fitness", "esim"})
    return tuple(e for e in GetHistoricalEpassCatalog() if e.Label in core_labels)


def GetHistoricalEpassCatalogByLabel(label: str) -> Optional[HistoricalEpassCatalogEntry]:
    """按 label 查找 catalog 条目。"""
    normalized = label.strip()
    for entry in GetHistoricalEpassCatalog():
        if entry.Label == normalized:
            return entry
    return None


def GetHistoricalPrebookingDateOverride() -> str:
    """固定预约时间；未配置则走候选列表首项。"""
    return _EnvFirst("DP_HIST_EPASS_PREBOOKING_DATE", "DP_LO_EPASS_PREBOOKING_DATE")


def IterHistoricalPrebookingDateCandidates() -> Tuple[str, ...]:
    override = GetHistoricalPrebookingDateOverride()
    if override:
        return (override,)
    return IterLocalOfferPrebookingDateCandidates()


def BuildHistoricalPrebookingDate() -> str:
    return IterHistoricalPrebookingDateCandidates()[0]


@dataclass(frozen=True)
class HistoricalFitnessScheduleTarget:
    """fitness 预约目标：由 schedule 接口解析的 option 与时段。"""

    ResourceId: str
    OptionId: str
    ScheduleDate: str
    StartTime: str
    EndTime: str
    OptionType: int
    OptionName: str

    @property
    def PrebookingDate(self) -> str:
        """可用性/预约 ``prebookingDate``（``YYYY-MM-DDTHH:mm``）。"""
        return f"{self.ScheduleDate}T{self.StartTime}"


def GetFitnessScheduleStartOffsetDays() -> int:
    """schedule ``startDate`` 相对 UTC 今天偏移（默认 +5 天）。"""
    raw = _EnvFirst("DP_HIST_EPASS_FITNESS_SCHEDULE_START_OFFSET_DAYS")
    if raw:
        try:
            return max(0, int(raw))
        except ValueError:
            pass
    return 5


def GetFitnessScheduleEndOffsetDays() -> int:
    """schedule ``endDate`` 相对 UTC 今天偏移（默认 +10 天）。"""
    raw = _EnvFirst("DP_HIST_EPASS_FITNESS_SCHEDULE_END_OFFSET_DAYS")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return 10


def GetFitnessPreferredOptionType() -> int:
    """优先选用的 ``optionType``（默认 1 = Day Pass）。"""
    raw = _EnvFirst("DP_HIST_EPASS_FITNESS_PREFERRED_OPTION_TYPE")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return 1


def BuildFitnessScheduleQueryDateRange() -> Tuple[str, str]:
    """
    返回 ``(startDate, endDate)``，格式 ``YYYY-MM-DD``。

    默认与 Apifox 一致：today+5 ～ today+10（跨度不超过 5 天需满足 OAS 约束时由 end 自动截断）。
    """
    today = datetime.now(timezone.utc).date()
    start = today + timedelta(days=GetFitnessScheduleStartOffsetDays())
    end = today + timedelta(days=GetFitnessScheduleEndOffsetDays())
    if end < start:
        end = start
    max_end = start + timedelta(days=5)
    if end > max_end:
        end = max_end
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def ListMissingHistoricalEpassEnvForEntry(entry: HistoricalEpassCatalogEntry) -> List[str]:
    """返回该品类缺失的必填配置（鉴权 + resourceId；options 模式另需 optionId）。"""
    missing = list(ListMissingRequiredLocalOfferEpassEnv())
    if entry.Optional and not entry.ResourceId:
        missing.append(f"DP_HIST_EPASS_{entry.Label.upper()}_RESOURCE_ID（optional 品类未配置）")
    if not entry.ResourceId and not entry.Optional:
        missing.append(f"DP_HIST_EPASS_{entry.Label.upper()}_RESOURCE_ID")
    if entry.AvailabilityMode == HistoricalAvailabilityMode.Options and not entry.OptionId:
        if entry.Label == "fitness":
            pass
        elif entry.Label == "fastTrack":
            prefix = "FASTTRACK"
            missing.append(f"DP_HIST_EPASS_{prefix}_OPTION_ID")
        elif entry.Label == "esim":
            prefix = "ESIM"
            missing.append(f"DP_HIST_EPASS_{prefix}_OPTION_ID")
    return missing


def RequireHistoricalEpassCatalogOrSkipMessage(
    entry: HistoricalEpassCatalogEntry,
) -> Optional[str]:
    missing = ListMissingHistoricalEpassEnvForEntry(entry)
    if not missing:
        return None
    return (
        f"历史 ePass 回归（{entry.DisplayName}/{entry.Label}）缺少配置: "
        + ", ".join(missing)
        + "。见 config/historical_epass_env.py 与 env/.env.historical-epass.example。"
    )


def GetHistoricalEsimStatusPollIntervalSec() -> float:
    """eSIM usage 单 status 轮询间隔（秒）。"""
    raw = _EnvFirst("DP_HIST_EPASS_ESIM_STATUS_POLL_INTERVAL_SEC")
    if raw:
        try:
            return max(1.0, float(raw))
        except ValueError:
            pass
    return 3.0


def GetHistoricalEsimStatusPollMaxAttempts() -> int:
    """eSIM usage 单 status 轮询最大次数（默认 40 次 × 3s ≈ 2 分钟）。"""
    raw = _EnvFirst("DP_HIST_EPASS_ESIM_STATUS_POLL_MAX_ATTEMPTS")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return 40


__all__ = [
    "BuildFitnessScheduleQueryDateRange",
    "BuildHistoricalPrebookingDate",
    "GetEpassClientId",
    "GetEpassClientSecret",
    "GetEpassProgramId",
    "GetFitnessPreferredOptionType",
    "GetFitnessScheduleEndOffsetDays",
    "GetFitnessScheduleStartOffsetDays",
    "GetConfiguredHistoricalEpassCatalog",
    "GetHistoricalEpassCoreCatalog",
    "GetHistoricalSimulationPaths",
    "GetHistoricalEpassCatalog",
    "GetHistoricalEpassCatalogByLabel",
    "GetHistoricalEsimStatusPollIntervalSec",
    "GetHistoricalEsimStatusPollMaxAttempts",
    "HistoricalAvailabilityMode",
    "HistoricalEpassCatalogEntry",
    "HistoricalFitnessScheduleTarget",
    "IterHistoricalPrebookingDateCandidates",
    "ListMissingHistoricalEpassEnvForEntry",
    "RequireHistoricalEpassCatalogOrSkipMessage",
]
