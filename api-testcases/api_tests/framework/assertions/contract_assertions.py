from __future__ import annotations

from typing import Any, Mapping, Sequence, Tuple


def AssertDictKeyValues(actual: Mapping[str, Any], expected: Mapping[str, Any], *, context: str = "") -> None:
    prefix = f"{context}: " if context else ""
    for key, expected_value in expected.items():
        assert key in actual, f"{prefix}缺少键 {key!r}"
        assert actual[key] == expected_value, (
            f"{prefix}键 {key!r} 期望 {expected_value!r}，实际 {actual[key]!r}"
        )


def AssertNestedStructureEqual(actual: Any, expected: Any, *, context: str = "") -> None:
    prefix = f"{context}: " if context else ""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{prefix}类型不匹配，期望 dict，实际 {type(actual).__name__}"
        assert set(actual.keys()) == set(expected.keys()), (
            f"{prefix}键集合不匹配，实际={sorted(actual.keys())!r}，期望={sorted(expected.keys())!r}"
        )
        for key, value in expected.items():
            AssertNestedStructureEqual(actual[key], value, context=f"{prefix}{key}")
        return
    if isinstance(expected, list):
        assert isinstance(actual, list), f"{prefix}类型不匹配，期望 list，实际 {type(actual).__name__}"
        assert len(actual) == len(expected), f"{prefix}长度不匹配，实际={len(actual)}，期望={len(expected)}"
        for index, value in enumerate(expected):
            AssertNestedStructureEqual(actual[index], value, context=f"{prefix}[{index}]")
        return
    assert actual == expected, f"{prefix}值不匹配，实际={actual!r}，期望={expected!r}"


def AssertSequenceContainsKeys(
    items: Sequence[Mapping[str, Any]],
    required_keys: Tuple[str, ...],
    *,
    context: str = "",
) -> None:
    prefix = f"{context}: " if context else ""
    for index, item in enumerate(items):
        for key in required_keys:
            assert key in item, f"{prefix}第 {index} 项缺少键 {key!r}"
