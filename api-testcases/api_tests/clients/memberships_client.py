"""会籍相关接口客户端。"""
from __future__ import annotations

from services.papi2548_memberships_extensions_impl import (
    PatchMembershipsExtensions,
    PostMemberships,
    PostMembershipsSearch,
)

__all__ = [
    "PatchMembershipsExtensions",
    "PostMemberships",
    "PostMembershipsSearch",
]
