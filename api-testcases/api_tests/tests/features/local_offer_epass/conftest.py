"""Local Offer ePass 共享 fixture。"""
from __future__ import annotations

import pytest

from clients import GetAccessTokenForEpass
from services.local_offer_epass_service import RequireLocalOfferEpassEnvOrSkip


@pytest.fixture
def EpassToken() -> str:
    """ePass 三件套取 token。"""
    RequireLocalOfferEpassEnvOrSkip()
    token = GetAccessTokenForEpass()
    assert isinstance(token, str) and len(token) >= 8, "accessToken 异常"
    return token
