"""
Local Offer ePass 环境变量（多 profile / Apifox 导入对照）。

**鉴权三件套（必填，与 PAPI-2424 ePass 共用）**

| Apifox / Postman 变量名 | 环境变量（推荐） | 说明 |
|-------------------------|------------------|------|
| ``baseUrl`` | ``DP_BASE_URL`` | 网关根路径，如 ``https://developer-sandbox.dragonpass.com/api`` |
| ``programId`` | ``DP_EPASS_PROGRAM_ID`` | 请求头 ``X-Program-ID``；别名 ``DP_PROGRAM_ID``、``PROGRAM_ID`` |
| ``clientId`` | ``DP_EPASS_CLIENT_ID`` | ``POST /v2/auth/token`` body；别名 ``DP_CLIENT_ID``、``CLIENT_ID`` |
| ``clientSecret`` | ``DP_EPASS_CLIENT_SECRET`` | token body ``secret``；别名 ``DP_CLIENT_SECRET``、``CLIENT_SECRET`` |

**默认预约网点（多数用例 ``redemption_code`` 及未单独配置的 label 回退）**

| Apifox / Postman | 环境变量（推荐） | 说明 |
|------------------|------------------|------|
| ``resourceId`` | ``DP_LO_EPASS_RESOURCE_ID`` | 默认网点；别名 ``RESOURCE_ID`` |
| ``optionId`` | ``DP_LO_EPASS_OPTION_ID`` | 默认 option；别名 ``OPTION_ID`` |

**按券型/场景覆盖（可选，优先于默认网点）**

| label | resourceId | optionId |
|-------|------------|----------|
| ``url`` | ``DP_LO_EPASS_URL_RESOURCE_ID`` | ``DP_LO_EPASS_URL_OPTION_ID`` |
| ``redemption_code`` | ``DP_LO_EPASS_REDEMPTION_CODE_RESOURCE_ID`` | ``DP_LO_EPASS_REDEMPTION_CODE_OPTION_ID`` |
| ``card_secret`` | ``DP_LO_EPASS_CARD_SECRET_RESOURCE_ID`` | ``DP_LO_EPASS_CARD_SECRET_OPTION_ID`` |

复制模板：仓库 ``env/.env.local-offer.example`` → 合并进 ``env/.env.<profile>``。
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

# catalog 元数据（不含硬编码网点 ID）
_PREBOOKING_CATALOG_META: Tuple[Dict[str, str], ...] = (
    {"label": "url", "voucherType": "5"},
    {"label": "redemption_code", "voucherType": "4"},
    {"label": "card_secret", "voucherType": "1"},
)

_VOUCHER_REDEMPTION_CATALOG_META: Tuple[Dict[str, str], ...] = (
    {
        "label": "card_secret_with_url",
        "voucherType": "1",
        "redemptionUrlExpect": "present",
        "fallbackLabel": "card_secret",
    },
)


def _EnvFirst(*names: str) -> str:
    """按顺序读取第一个非空环境变量。"""
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def GetLocalOfferBaseUrl() -> str:
    """网关 ``DP_BASE_URL``（Apifox ``baseUrl``）。"""
    return _EnvFirst("DP_BASE_URL", "BASE_URL")


def GetEpassProgramId() -> str:
    """``X-Program-ID``（Apifox ``programId``）。"""
    return _EnvFirst("DP_EPASS_PROGRAM_ID", "DP_PROGRAM_ID", "PROGRAM_ID")


def GetEpassClientId() -> str:
    """token body ``clientId``（Apifox ``clientId``）。"""
    return _EnvFirst("DP_EPASS_CLIENT_ID", "DP_CLIENT_ID", "CLIENT_ID")


def GetEpassClientSecret() -> str:
    """token body ``secret``（Apifox ``clientSecret``）。"""
    return _EnvFirst("DP_EPASS_CLIENT_SECRET", "DP_CLIENT_SECRET", "CLIENT_SECRET")


def GetDefaultOutletResourceId() -> str:
    """默认 ``resourceId``（Apifox 通用 ``resourceId``）。"""
    return _EnvFirst("DP_LO_EPASS_RESOURCE_ID", "RESOURCE_ID")


def GetDefaultOutletOptionId() -> str:
    """默认 ``optionId``（Apifox 通用 ``optionId``）。"""
    return _EnvFirst("DP_LO_EPASS_OPTION_ID", "OPTION_ID")


def _LabelEnvPrefix(label: str) -> str:
    return f"DP_LO_EPASS_{label.upper().replace('-', '_')}"


def GetOutletResourceIdForLabel(label: str) -> str:
    """
    按 label 解析 ``resourceId``。

    顺序：``DP_LO_EPASS_<LABEL>_RESOURCE_ID`` → ``DP_LO_EPASS_RESOURCE_ID`` → ``RESOURCE_ID``。
    """
    prefix = _LabelEnvPrefix(label)
    return _EnvFirst(
        f"{prefix}_RESOURCE_ID",
        "DP_LO_EPASS_RESOURCE_ID",
        "RESOURCE_ID",
    )


def GetOutletOptionIdForLabel(label: str) -> str:
    """
    按 label 解析 ``optionId``。

    顺序：``DP_LO_EPASS_<LABEL>_OPTION_ID`` → ``DP_LO_EPASS_OPTION_ID`` → ``OPTION_ID``。
    """
    prefix = _LabelEnvPrefix(label)
    return _EnvFirst(
        f"{prefix}_OPTION_ID",
        "DP_LO_EPASS_OPTION_ID",
        "OPTION_ID",
    )


def GetOutletPairForLabel(label: str) -> Tuple[str, str]:
    """返回 ``(resourceId, optionId)``。"""
    return GetOutletResourceIdForLabel(label), GetOutletOptionIdForLabel(label)


def BuildPrebookingCatalogItem(meta: Mapping[str, str]) -> Dict[str, str]:
    """由 catalog 元数据 + 环境变量生成带 ``resourceId``/``optionId`` 的条目。"""
    label = meta["label"]
    resource_id = meta.get("resourceId", "").strip()
    option_id = meta.get("optionId", "").strip()
    if not resource_id:
        resource_id = GetOutletResourceIdForLabel(label)
    if not option_id:
        fallback = meta.get("fallbackLabel", "").strip()
        if fallback:
            option_id = GetOutletOptionIdForLabel(fallback)
            if not resource_id:
                resource_id = GetOutletResourceIdForLabel(fallback)
        else:
            option_id = GetOutletOptionIdForLabel(label)
    item: Dict[str, str] = {
        "label": label,
        "resourceId": resource_id,
        "optionId": option_id,
        "voucherType": meta["voucherType"],
    }
    for key in ("redemptionUrlExpect", "fallbackLabel"):
        if key in meta and meta[key]:
            item[key] = meta[key]
    return item


def GetDefaultPrebookingResources() -> Tuple[Dict[str, str], ...]:
    """三类券型默认网点（值来自环境变量）。"""
    return tuple(BuildPrebookingCatalogItem(m) for m in _PREBOOKING_CATALOG_META)


def GetDefaultVoucherRedemptionScenarios() -> Tuple[Dict[str, str], ...]:
    """voucherType=1 且 redemptionUrl 有值场景（网点由 label / fallbackLabel 环境变量解析）。"""
    return tuple(BuildPrebookingCatalogItem(m) for m in _VOUCHER_REDEMPTION_CATALOG_META)


def ListMissingRequiredLocalOfferEpassEnv() -> List[str]:
    """返回缺失的必填环境变量名（canonical ``DP_*`` 名）。"""
    missing: List[str] = []
    if not GetEpassProgramId():
        missing.append("DP_EPASS_PROGRAM_ID")
    if not GetEpassClientId():
        missing.append("DP_EPASS_CLIENT_ID")
    if not GetEpassClientSecret():
        missing.append("DP_EPASS_CLIENT_SECRET")
    return missing


def GetLocalOfferPrebookingDateOverride() -> str:
    """固定预约时间（Apifox 可映射 ``prebookingDate``）；未配置则走候选列表。"""
    return _EnvFirst("DP_LO_EPASS_PREBOOKING_DATE", "PREBOOKING_DATE")


def IterLocalOfferPrebookingDateCandidates() -> Tuple[str, ...]:
    """
    可用性/预约造数用的 ``prebookingDate`` 候选（按序尝试）。

    未配置 ``DP_LO_EPASS_PREBOOKING_DATE`` 时：UTC **+10 天 10:30** 为首项，
    并保留 +11/+12 天 10:30 作为 ``500.020.009``（时段不可用）时的回退。
    """
    override = GetLocalOfferPrebookingDateOverride()
    if override:
        return (override,)
    now = datetime.now(timezone.utc)
    return (
        (now + timedelta(days=10)).strftime("%Y-%m-%dT10:30"),
        (now + timedelta(days=11)).strftime("%Y-%m-%dT10:30"),
        (now + timedelta(days=12)).strftime("%Y-%m-%dT10:30"),
    )


def BuildLocalOfferPrebookingDate() -> str:
    """默认预约时间（候选列表首项）。"""
    return IterLocalOfferPrebookingDateCandidates()[0]


def RequireDefaultOutletEnvOrSkipMessage() -> Optional[str]:
    """默认网点未配置时返回 skip 说明，否则 ``None``。"""
    if GetDefaultOutletResourceId() and GetDefaultOutletOptionId():
        return None
    return (
        "未配置默认网点：请设置 DP_LO_EPASS_RESOURCE_ID 与 DP_LO_EPASS_OPTION_ID "
        "（Apifox 可映射 resourceId / optionId）。"
    )


__all__ = [
    "BuildLocalOfferPrebookingDate",
    "BuildPrebookingCatalogItem",
    "GetLocalOfferPrebookingDateOverride",
    "IterLocalOfferPrebookingDateCandidates",
    "GetDefaultOutletOptionId",
    "GetDefaultOutletResourceId",
    "GetDefaultPrebookingResources",
    "GetDefaultVoucherRedemptionScenarios",
    "GetEpassClientId",
    "GetEpassClientSecret",
    "GetEpassProgramId",
    "GetLocalOfferBaseUrl",
    "GetOutletOptionIdForLabel",
    "GetOutletPairForLabel",
    "GetOutletResourceIdForLabel",
    "ListMissingRequiredLocalOfferEpassEnv",
    "RequireDefaultOutletEnvOrSkipMessage",
]
