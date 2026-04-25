"""测试数据构造层：保留 CSV 选择器，同时提供常用请求体构造入口。"""
from __future__ import annotations

from services.papi2515_cross_module_impl import (
    BuildP2515ModuleExclusiveUpdateBody,
    BuildP2515PoolUpdatePlan,
    BuildP2515RegisterPayload,
)
from services.papi2548_memberships_extensions_impl import BuildMinimalMembershipPayload

__all__ = [
    "BuildMinimalMembershipPayload",
    "BuildP2515ModuleExclusiveUpdateBody",
    "BuildP2515PoolUpdatePlan",
    "BuildP2515RegisterPayload",
]
