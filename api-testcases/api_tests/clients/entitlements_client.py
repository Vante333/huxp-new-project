"""权益相关接口客户端。"""
from __future__ import annotations

from services.papi2515_cross_module_impl import (
    PostEntitlementsSearch,
    PostEntitlementsUpdate,
    PostEntitlementsUpdateByPoolId,
)

__all__ = [
    "PostEntitlementsSearch",
    "PostEntitlementsUpdate",
    "PostEntitlementsUpdateByPoolId",
]
