"""鉴权客户端：兼容现有 helpers，实现框架层统一入口。"""
from __future__ import annotations

from services.papi2548_memberships_extensions_impl import (
    EpassTokenCredentialsConfigured,
    GetAccessToken,
    GetAccessTokenForEpass,
    ResolveAccessTokenForP2424OrDefault,
)

__all__ = [
    "EpassTokenCredentialsConfigured",
    "GetAccessToken",
    "GetAccessTokenForEpass",
    "ResolveAccessTokenForP2424OrDefault",
]
