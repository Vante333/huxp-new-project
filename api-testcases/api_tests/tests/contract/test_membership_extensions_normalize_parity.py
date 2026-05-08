"""
金样例：NormalizeExtensionsForCompare 行为与 Postman 生成脚本中 JS 应对齐。

若修改 papi2548_helpers.NormalizeExtensionsForCompare 或 GeneratePostmanCollectionPapi2548.BuildHelpersJsLines，
请同步更新本文件中的 expected，并人工核对 Apifox/Postman Tests。
"""
from __future__ import annotations

from typing import List, Optional, Tuple

import pytest

from services.papi2548_service import NormalizeExtensionsForCompare

pytestmark = [pytest.mark.contract, pytest.mark.papi2548]


@pytest.mark.parametrize(
    ("items", "expected"),
    [
        (
            [{"type": "b", "value": "2"}, {"type": "a", "value": "1"}],
            [("a", "1"), ("b", "2")],
        ),
        (
            [{"type": "x", "value": "1"}, {"type": "x", "value": "2"}],
            [("x", "1"), ("x", "2")],
        ),
        (
            [{"type": "only"}],
            [("only", None)],
        ),
        (
            [{"type": "k", "value": None}],
            [("k", None)],
        ),
    ],
)
def test_normalize_extensions_matches_expected(
    items: List[object],
    expected: List[Tuple[str, Optional[str]]],
) -> None:
    got = NormalizeExtensionsForCompare(items)
    assert got == expected, f"got={got!r} expected={expected!r}"


def test_normalize_empty_list() -> None:
    assert NormalizeExtensionsForCompare([]) == []
