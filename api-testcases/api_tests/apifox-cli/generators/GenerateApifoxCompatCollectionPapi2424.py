"""生成 Apifox 2.8.24 兼容的 PAPI-2424 Postman Collection。

用途：
- 基于 ``PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json`` 二次裁剪；
- 保留接口目录、请求方法、URL、Header、Body、变量；
- 去除 Apifox 2.8.24 可能拒绝的高风险字段（如 ``event``、复杂 ``url`` 对象、禁用 Header）。

说明：
- 该兼容版优先保证「可导入」；
- Postman Tests / 后置脚本不再内嵌在 JSON 中，如需断言脚本请继续参考生成器与 helpers。
"""
from __future__ import annotations

import json
from pathlib import Path

from collection_builder_common import CollectionPath
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Union, cast

JsonScalar = Union[str, int, float, bool, None]
JsonValue = Union[JsonScalar, "JsonObject", List["JsonValue"]]
JsonObject = Dict[str, JsonValue]

SOURCE_NAME = "PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json"
OUT_NAME = "PAPI-2424-ePasses-details-ms-order-hint.apifox-compat.postman_collection.json"


def _ScriptDir() -> Path:
    return Path(__file__).resolve().parent


def _LoadSourceCollection(path: Path) -> JsonObject:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"读取源 Collection 失败：{path}；{exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"源 Collection 不是合法 JSON：{path}；{exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"源 Collection 顶层必须是对象：{path}")
    return cast(JsonObject, data)


def _NormalizeUrl(value: JsonValue) -> JsonValue:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        raw = value.get("raw")
        if isinstance(raw, str) and raw.strip():
            return raw
    raise RuntimeError(f"无法识别的 request.url 结构：{value!r}")


def _NormalizeBody(value: JsonValue) -> JsonValue:
    if not isinstance(value, dict):
        return value

    mode = value.get("mode")
    if mode == "raw":
        raw = value.get("raw", "")
        if not isinstance(raw, str):
            raise RuntimeError(f"raw body 必须为字符串：{value!r}")
        return {"mode": "raw", "raw": raw}
    return value


def _NormalizeHeaders(value: JsonValue) -> JsonValue:
    if not isinstance(value, list):
        return value

    headers: List[JsonValue] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        if item.get("disabled") is True:
            continue

        normalized: JsonObject = {}
        for key in ("key", "value", "description"):
            current = item.get(key)
            if isinstance(current, str):
                normalized[key] = current
        if "key" in normalized and "value" in normalized:
            headers.append(normalized)
    return headers


def _NormalizeVariables(value: JsonValue) -> JsonValue:
    if not isinstance(value, list):
        return value

    variables: List[JsonValue] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        key = item.get("key")
        raw_value = item.get("value", "")
        if not isinstance(key, str):
            continue
        if not isinstance(raw_value, str):
            raw_value = "" if raw_value is None else str(raw_value)
        variables.append({"key": key, "value": raw_value, "type": "string"})
    return variables


def _StripUnsupportedFields(node: JsonValue) -> JsonValue:
    if isinstance(node, list):
        return [_StripUnsupportedFields(item) for item in node]

    if not isinstance(node, dict):
        return node

    result: JsonObject = {}
    for key, value in node.items():
        if key in {"event", "response", "protocolProfileBehavior", "_postman_id"}:
            continue
        if key == "url":
            result[key] = _NormalizeUrl(value)
            continue
        if key == "body":
            result[key] = _NormalizeBody(value)
            continue
        if key == "header":
            result[key] = _NormalizeHeaders(value)
            continue
        if key == "variable":
            result[key] = _NormalizeVariables(value)
            continue
        result[key] = _StripUnsupportedFields(value)
    return result


def _WriteCollection(path: Path, payload: Mapping[str, JsonValue]) -> None:
    try:
        path.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(f"写入兼容版 Collection 失败：{path}；{exc}") from exc


def Main() -> None:
    source_path = CollectionPath(SOURCE_NAME)
    out_path = CollectionPath(OUT_NAME)

    collection = _LoadSourceCollection(source_path)
    normalized = _StripUnsupportedFields(collection)
    if not isinstance(normalized, dict):
        raise RuntimeError("兼容版 Collection 顶层结构异常，预期为对象。")

    _WriteCollection(out_path, normalized)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    Main()
