"""把 Postman Collection 的关键语义导出为稳定 JSON/Markdown，并支持基线比较。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

JsonObject = Dict[str, Any]


def LoadCollection(path: Path) -> JsonObject:
    """读取集合 JSON；格式或根类型错误时抛出带路径的明确异常。"""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise OSError(f"无法读取集合 {path}: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"集合 JSON 非法 {path}:{exc.lineno}:{exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"集合根节点必须是对象：{path}")
    return payload


def IterRequestSteps(
    items: Sequence[Any],
    folders: Tuple[str, ...] = (),
) -> Iterable[Tuple[Tuple[str, ...], Mapping[str, Any]]]:
    """按集合原顺序递归产出 ``(folder_path, request_item)``。"""
    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        name = str(raw_item.get("name", "")).strip()
        children = raw_item.get("item")
        if isinstance(children, list):
            yield from IterRequestSteps(children, folders + (name,))
        elif isinstance(raw_item.get("request"), dict):
            yield folders, raw_item


def ScriptText(event: Mapping[str, Any]) -> str:
    """规范化单个 event 的脚本文本。"""
    script = event.get("script")
    if not isinstance(script, dict):
        return ""
    exec_value = script.get("exec")
    if isinstance(exec_value, list):
        return "\n".join(str(line) for line in exec_value)
    if isinstance(exec_value, str):
        return exec_value
    return ""


def EventScripts(item: Mapping[str, Any]) -> Dict[str, str]:
    """合并同一请求项的 prerequest/test 脚本，保持 event 顺序。"""
    grouped: Dict[str, List[str]] = {"prerequest": [], "test": []}
    events = item.get("event")
    if not isinstance(events, list):
        return {key: "" for key in grouped}
    for raw_event in events:
        if not isinstance(raw_event, dict):
            continue
        listen = str(raw_event.get("listen", ""))
        if listen in grouped:
            grouped[listen].append(ScriptText(raw_event))
    return {key: "\n".join(parts) for key, parts in grouped.items()}


def _RequestPath(request: Mapping[str, Any]) -> str:
    url = request.get("url")
    if isinstance(url, str):
        path = url.split("?", 1)[0]
        return "/" + path.split("/", 3)[-1] if "://" in path else path
    if not isinstance(url, dict):
        return ""
    parts = url.get("path")
    if isinstance(parts, list):
        return "/" + "/".join(str(part).strip("/") for part in parts)
    raw = str(url.get("raw", ""))
    without_query = raw.split("?", 1)[0]
    marker = without_query.find("/", without_query.find("}}") + 2)
    return without_query[marker:] if marker >= 0 else without_query


def _BodyTopLevelFields(request: Mapping[str, Any]) -> List[str]:
    body = request.get("body")
    if not isinstance(body, dict) or body.get("mode") != "raw":
        return []
    raw = body.get("raw")
    if not isinstance(raw, str) or not raw.strip():
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(value, dict):
        return []
    return sorted(str(key) for key in value)


def _FirstCallArgument(text: str, start: int) -> str:
    quote = ""
    escaped = False
    depth = 0
    chars: List[str] = []
    for char in text[start:]:
        if escaped:
            chars.append(char)
            escaped = False
            continue
        if quote:
            chars.append(char)
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in ("'", '"', "`"):
            quote = char
            chars.append(char)
        elif char in "([{":
            depth += 1
            chars.append(char)
        elif char in ")]}":
            if depth == 0:
                break
            depth -= 1
            chars.append(char)
        elif char == "," and depth == 0:
            break
        else:
            chars.append(char)
    return "".join(chars).strip()


def _AssertionTitles(test_script: str) -> List[str]:
    titles: List[str] = []
    marker = "pm.test("
    offset = 0
    while True:
        found = test_script.find(marker, offset)
        if found < 0:
            break
        expression = _FirstCallArgument(test_script, found + len(marker))
        if (
            len(expression) >= 2
            and expression[0] in ("'", '"', "`")
            and expression[-1] == expression[0]
        ):
            expression = expression[1:-1]
        if expression:
            titles.append(expression)
        offset = found + len(marker)
    return list(dict.fromkeys(titles))


def BuildSemantics(payload: Mapping[str, Any]) -> JsonObject:
    """构建可稳定 diff 的集合语义摘要。"""
    info = payload.get("info")
    info_obj = info if isinstance(info, dict) else {}
    items = payload.get("item")
    item_list = items if isinstance(items, list) else []
    steps: List[JsonObject] = []
    for index, (folders, item) in enumerate(IterRequestSteps(item_list), start=1):
        request_value = item.get("request")
        request = request_value if isinstance(request_value, dict) else {}
        scripts = EventScripts(item)
        prerequest_bytes = len(scripts["prerequest"].encode("utf-8"))
        test_bytes = len(scripts["test"].encode("utf-8"))
        steps.append(
            {
                "index": index,
                "folders": list(folders),
                "name": str(item.get("name", "")),
                "method": str(request.get("method", "")).upper(),
                "path": _RequestPath(request),
                "body_top_level_fields": _BodyTopLevelFields(request),
                "assertion_titles": _AssertionTitles(scripts["test"]),
                "script_bytes": {
                    "prerequest": prerequest_bytes,
                    "test": test_bytes,
                    "total": prerequest_bytes + test_bytes,
                },
            }
        )
    return {
        "collection": {
            "name": str(info_obj.get("name", "")),
            "schema": str(info_obj.get("schema", "")),
            "step_count": len(steps),
        },
        "steps": steps,
    }


def CompareSemantics(
    baseline: Mapping[str, Any],
    current: Mapping[str, Any],
) -> JsonObject:
    """按步骤顺序比较两个语义摘要，返回稳定的字段级差异。"""
    baseline_steps = baseline.get("steps")
    current_steps = current.get("steps")
    before = baseline_steps if isinstance(baseline_steps, list) else []
    after = current_steps if isinstance(current_steps, list) else []
    changes: List[JsonObject] = []
    max_count = max(len(before), len(after))
    for offset in range(max_count):
        old = before[offset] if offset < len(before) else None
        new = after[offset] if offset < len(after) else None
        if old == new:
            continue
        if old is None:
            changes.append({"index": offset + 1, "kind": "added", "current": new})
        elif new is None:
            changes.append({"index": offset + 1, "kind": "removed", "baseline": old})
        elif isinstance(old, dict) and isinstance(new, dict):
            changed_fields = sorted(
                key for key in set(old) | set(new) if old.get(key) != new.get(key)
            )
            changes.append(
                {
                    "index": offset + 1,
                    "kind": "changed",
                    "fields": changed_fields,
                    "baseline": old,
                    "current": new,
                }
            )
        else:
            changes.append(
                {
                    "index": offset + 1,
                    "kind": "changed",
                    "baseline": old,
                    "current": new,
                }
            )
    return {
        "equal": not changes,
        "baseline_step_count": len(before),
        "current_step_count": len(after),
        "changes": changes,
    }


def RenderMarkdown(summary: Mapping[str, Any], comparison: Optional[Mapping[str, Any]]) -> str:
    """将摘要渲染为便于评审的稳定 Markdown。"""
    collection = summary.get("collection")
    collection_obj = collection if isinstance(collection, dict) else {}
    lines = [
        f"# Collection 语义摘要：{collection_obj.get('name', '')}",
        "",
        f"- Schema：`{collection_obj.get('schema', '')}`",
        f"- 请求步骤数：{collection_obj.get('step_count', 0)}",
        "",
        "## 步骤",
        "",
    ]
    steps = summary.get("steps")
    for raw_step in steps if isinstance(steps, list) else []:
        if not isinstance(raw_step, dict):
            continue
        folders = " / ".join(str(value) for value in raw_step.get("folders", []))
        scripts = raw_step.get("script_bytes")
        script_obj = scripts if isinstance(scripts, dict) else {}
        lines.extend(
            [
                f"### {raw_step.get('index')}. {raw_step.get('name', '')}",
                f"- 目录：{folders or '(根目录)'}",
                f"- 请求：`{raw_step.get('method', '')} {raw_step.get('path', '')}`",
                "- Body 顶层字段："
                + (", ".join(f"`{value}`" for value in raw_step.get("body_top_level_fields", [])) or "无/不可解析"),
                "- 断言标题："
                + ("；".join(str(value) for value in raw_step.get("assertion_titles", [])) or "无静态标题"),
                f"- 脚本字节：pre={script_obj.get('prerequest', 0)}，"
                f"test={script_obj.get('test', 0)}，total={script_obj.get('total', 0)}",
                "",
            ]
        )
    if comparison is not None:
        changes = comparison.get("changes")
        change_list = changes if isinstance(changes, list) else []
        lines.extend(
            [
                "## 基线比较",
                "",
                f"- 结果：{'一致' if comparison.get('equal') else '有差异'}",
                f"- 差异数：{len(change_list)}",
            ]
        )
        for change in change_list:
            if isinstance(change, dict):
                fields = ", ".join(str(value) for value in change.get("fields", []))
                lines.append(
                    f"- 步骤 {change.get('index')}：{change.get('kind')}"
                    + (f"（{fields}）" if fields else "")
                )
        lines.append("")
    return "\n".join(lines)


def _WriteOutput(text: str, output: str) -> None:
    if not output:
        print(text)
        return
    path = Path(output).resolve()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + ("" if text.endswith("\n") else "\n"), encoding="utf-8")
    except OSError as exc:
        raise OSError(f"无法写入摘要 {path}: {exc}") from exc


def Main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="输出或比较 Postman Collection 稳定语义")
    parser.add_argument("--input", required=True, help="当前 collection JSON")
    parser.add_argument("--baseline", default="", help="可选基线 collection JSON")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", default="", help="可选输出文件；默认 stdout")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        current = BuildSemantics(LoadCollection(Path(str(args.input)).resolve()))
        comparison: Optional[JsonObject] = None
        if str(args.baseline).strip():
            baseline = BuildSemantics(LoadCollection(Path(str(args.baseline)).resolve()))
            comparison = CompareSemantics(baseline, current)
        if args.format == "json":
            result: JsonObject = {"semantics": current}
            if comparison is not None:
                result["comparison"] = comparison
            text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        else:
            text = RenderMarkdown(current, comparison)
        _WriteOutput(text, str(args.output))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Collection 语义摘要失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
