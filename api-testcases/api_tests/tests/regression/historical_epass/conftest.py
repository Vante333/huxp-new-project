"""历史 ePass 回归共享 fixture（与 local_offer_epass 同构）。"""
from __future__ import annotations

import pytest

from clients import GetAccessTokenForEpass
from services.historical_epass_service import RequireHistoricalEpassEnvOrSkip


@pytest.fixture
def EpassToken() -> str:
    RequireHistoricalEpassEnvOrSkip()
    token = GetAccessTokenForEpass()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token
