"""兼容入口：测试数据加载能力已迁移至 ``framework.data``。"""
from __future__ import annotations

from framework.data import (
    CurrentDatasetKey as _CurrentDatasetKey,
    CurrentProfile as _CurrentProfile,
    LoadMembershipRegisterCsvRow,
    LoadP2424DatasetCsvRow,
    LoadP2515DatasetCsvRow,
    MembershipRegisterCsvRow,
    P2424DatasetCsvRow,
    P2515DatasetCsvRow,
    ResolveMembershipProgramIdOverride,
)

__all__ = [
    "LoadMembershipRegisterCsvRow",
    "LoadP2424DatasetCsvRow",
    "LoadP2515DatasetCsvRow",
    "MembershipRegisterCsvRow",
    "P2424DatasetCsvRow",
    "P2515DatasetCsvRow",
    "ResolveMembershipProgramIdOverride",
    "_CurrentDatasetKey",
    "_CurrentProfile",
]
