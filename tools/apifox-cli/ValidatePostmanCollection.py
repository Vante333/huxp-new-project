"""离线校验 Postman Collection v2.1、命名、说明、脚本体积与最终脚本反模式。"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Counter as CounterType
from typing import List, Mapping, Optional, Sequence, Tuple

from SummarizeCollectionSemantics import IterRequestSteps, LoadCollection, ScriptText

_POSTMAN_V21_SCHEMA = (
    "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
)
_DEFAULT_WARNING_BYTES = 40 * 1024
_DEFAULT_ERROR_BYTES = 50 * 1024
_PURPOSE_NAME_PATTERN = re.compile(
    r"^【[^】\r\n]+】\s*\|\s*[^|\r\n]+\s*\|\s*"
    r"(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/\S+"
)


@dataclass(frozen=True)
class ValidationFinding:
    Level: str
    Location: str
    RuleId: str
    Message: str


@dataclass(frozen=True)
class ScriptAntiPattern:
    RuleId: str
    Pattern: re.Pattern[str]
    Level: str
    Message: str


_SCRIPT_ANTI_PATTERNS: Tuple[ScriptAntiPattern, ...] = (
    ScriptAntiPattern(
        RuleId="replace_in_uuid",
        Pattern=re.compile(r"""replaceIn\(\s*['"]\{\{\$string\.uuid\}\}['"]\s*\)"""),
        Level="error",
        Message="最终脚本仍依赖 CLI 常不展开的 {{$string.uuid}}",
    ),
    ScriptAntiPattern(
        RuleId="legacy_client_user_id_get",
        Pattern=re.compile(
            r"""pm\.collectionVariables\.get\(\s*['"]clientUserId['"]\s*\)"""
        ),
        Level="warning",
        Message="最终脚本直接读取 collectionVariables.clientUserId，建议使用统一 GetVar",
    ),
    ScriptAntiPattern(
        RuleId="inline_capture",
        Pattern=re.compile(r"function\s+\w+CaptureClientUserIdAfterSend\s*\("),
        Level="warning",
        Message="最终脚本内联 CaptureClientUserIdAfterSend，注意避免逐步复制公共 helper",
    ),
)

# 现存集合债按「文件名 + 规则 + 精确数量」登记，仅对默认 40/50 KiB 阈值生效。
# 数量增加阻断新债，数量减少也阻断并要求同步收紧本表。
_KNOWN_COLLECTION_DEBT: Mapping[str, Mapping[str, int]] = {
    "PAPI-2424-ePasses-details-ms-order-hint.postman_collection.json": {
        "replace_in_uuid": 1,
    },
    "FT-Membership-Prebooking-Payment-P0.postman_collection.json": {"script_size": 2},
    "FT-Membership-Prebooking-Payment-P1.postman_collection.json": {"script_size": 2},
    "FT-Epass-Prebooking-Payment-P0.postman_collection.json": {"script_size": 2},
    "FT-Epass-Prebooking-Payment-P1.postman_collection.json": {"script_size": 2},
    "Lounge-Membership-Prebooking-Payment-P0.postman_collection.json": {
        "script_size": 2,
    },
    "Lounge-Membership-Prebooking-Payment-P1.postman_collection.json": {
        "script_size": 2,
    },
    "Lounge-Epass-Prebooking-Payment-P0.postman_collection.json": {"script_size": 2},
    "Lounge-Epass-Prebooking-Payment-P1.postman_collection.json": {"script_size": 2},
    "Membership-Purchase-P0.postman_collection.json": {"replace_in_uuid": 3},
    "Membership-Purchase-P1.postman_collection.json": {"replace_in_uuid": 56},
    "Esim-ePass-P0-e2e-core.postman_collection.json": {"script_size": 104},
    "PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json": {
        "purpose_name": 24,
        "replace_in_uuid": 11,
    },
    "PAPI-2839-FastTrack-NameRegex-P1-Membership.postman_collection.json": {
        "purpose_name": 12,
        "replace_in_uuid": 2,
    },
    "PAPI-2839-Lounge-NameRegex-Regression-P1.postman_collection.json": {
        "purpose_name": 2,
    },
    "PAPI-2839-Lounge-NameRegex-Regression-P1-Membership.postman_collection.json": {
        "purpose_name": 1,
    },
    "PAPI-2722-FastTrack-PII-P1.postman_collection.json": {
        "purpose_name": 14,
        "replace_in_uuid": 3,
    },
    "PAPI-2722-FastTrack-PII-P1-Membership.postman_collection.json": {
        "purpose_name": 7,
        "replace_in_uuid": 1,
    },
}


def _Add(
    findings: List[ValidationFinding],
    level: str,
    location: str,
    rule_id: str,
    message: str,
) -> None:
    findings.append(
        ValidationFinding(
            Level=level,
            Location=location,
            RuleId=rule_id,
            Message=message,
        )
    )


def _ValidateInfo(
    payload: Mapping[str, Any],
    findings: List[ValidationFinding],
) -> None:
    info = payload.get("info")
    if not isinstance(info, dict):
        _Add(findings, "error", "info", "schema", "info 必须是对象")
        return
    if not isinstance(info.get("name"), str) or not str(info.get("name", "")).strip():
        _Add(findings, "error", "info.name", "schema", "集合名称不能为空")
    description = info.get("description")
    if not isinstance(description, str) or not description.strip():
        _Add(
            findings,
            "error",
            "info.description",
            "description",
            "场景说明不能为空，须描述生成源、链路与变量关系",
        )
    schema = info.get("schema")
    if schema != _POSTMAN_V21_SCHEMA:
        _Add(
            findings,
            "error",
            "info.schema",
            "schema",
            f"必须为 Postman v2.1 schema：{_POSTMAN_V21_SCHEMA}",
        )


def _ValidateRequest(
    item: Mapping[str, Any],
    location: str,
    findings: List[ValidationFinding],
) -> None:
    name = item.get("name")
    if not isinstance(name, str) or not _PURPOSE_NAME_PATTERN.match(name):
        _Add(
            findings,
            "error",
            location,
            "purpose_name",
            "请求名必须为「【中文目的】| 步骤ID | METHOD /path」",
        )
    request = item.get("request")
    if not isinstance(request, dict):
        _Add(findings, "error", location, "schema", "request 必须是对象")
        return
    method = request.get("method")
    if not isinstance(method, str) or not method.strip():
        _Add(findings, "error", f"{location}.request.method", "schema", "method 不能为空")
    url = request.get("url")
    if not isinstance(url, (str, dict)):
        _Add(
            findings,
            "error",
            f"{location}.request.url",
            "schema",
            "url 必须是字符串或对象",
        )


def _ValidateEvents(
    item: Mapping[str, Any],
    location: str,
    warning_bytes: int,
    error_bytes: int,
    findings: List[ValidationFinding],
) -> None:
    events = item.get("event")
    if events is None:
        return
    if not isinstance(events, list):
        _Add(findings, "error", f"{location}.event", "schema", "event 必须是数组")
        return
    for event_index, raw_event in enumerate(events, start=1):
        event_location = f"{location}.event[{event_index}]"
        if not isinstance(raw_event, dict):
            _Add(findings, "error", event_location, "schema", "event 项必须是对象")
            continue
        listen = raw_event.get("listen")
        if listen not in ("prerequest", "test"):
            _Add(
                findings,
                "warning",
                f"{event_location}.listen",
                "schema",
                f"未知事件类型：{listen!r}",
            )
        script = raw_event.get("script")
        if not isinstance(script, dict):
            _Add(findings, "error", f"{event_location}.script", "schema", "script 必须是对象")
            continue
        exec_value = script.get("exec")
        if not isinstance(exec_value, (list, str)):
            _Add(
                findings,
                "error",
                f"{event_location}.script.exec",
                "schema",
                "exec 必须是字符串或字符串数组",
            )
            continue
        if isinstance(exec_value, list) and any(
            not isinstance(line, str) for line in exec_value
        ):
            _Add(
                findings,
                "error",
                f"{event_location}.script.exec",
                "schema",
                "exec 数组只能包含字符串",
            )
            continue

        text = ScriptText(raw_event)
        size = len(text.encode("utf-8"))
        if size >= error_bytes:
            _Add(
                findings,
                "error",
                event_location,
                "script_size",
                f"单步 {listen} 脚本 {size} bytes，达到错误阈值 {error_bytes}",
            )
        elif size >= warning_bytes:
            _Add(
                findings,
                "warning",
                event_location,
                "script_size",
                f"单步 {listen} 脚本 {size} bytes，达到警告阈值 {warning_bytes}",
            )

        for anti_pattern in _SCRIPT_ANTI_PATTERNS:
            for match in anti_pattern.Pattern.finditer(text):
                line_no = text.count("\n", 0, match.start()) + 1
                _Add(
                    findings,
                    anti_pattern.Level,
                    f"{event_location}.script.exec:L{line_no}",
                    anti_pattern.RuleId,
                    anti_pattern.Message,
                )


def ValidateCollection(
    payload: Mapping[str, Any],
    warning_bytes: int,
    error_bytes: int,
) -> List[ValidationFinding]:
    """执行全部离线检查并返回稳定顺序的发现列表。"""
    findings: List[ValidationFinding] = []
    _ValidateInfo(payload, findings)
    items = payload.get("item")
    if not isinstance(items, list) or not items:
        _Add(findings, "error", "item", "schema", "item 必须是非空数组")
        return findings
    request_count = 0
    for request_count, (folders, item) in enumerate(
        IterRequestSteps(items),
        start=1,
    ):
        display_path = " / ".join(folders + (str(item.get("name", "")),))
        location = f"item.request[{request_count}] ({display_path})"
        _ValidateRequest(item, location, findings)
        _ValidateEvents(
            item,
            location,
            warning_bytes,
            error_bytes,
            findings,
        )
    if request_count == 0:
        _Add(findings, "error", "item", "schema", "集合中没有请求步骤")
    return findings


def ApplyKnownDebt(
    input_path: Path,
    findings: Sequence[ValidationFinding],
    warning_bytes: int,
    error_bytes: int,
) -> List[ValidationFinding]:
    """按精确数量降级已登记集合债，数量漂移时阻断并提示收紧清单。"""
    expected = (
        _KNOWN_COLLECTION_DEBT.get(input_path.name, {})
        if warning_bytes == _DEFAULT_WARNING_BYTES
        and error_bytes == _DEFAULT_ERROR_BYTES
        else {}
    )
    actual: CounterType[str] = Counter(
        item.RuleId for item in findings if item.Level == "error"
    )
    normalized: List[ValidationFinding] = []
    for item in findings:
        if item.Level == "error" and item.RuleId in expected:
            continue
        normalized.append(item)
    for rule_id in sorted(set(expected) | set(actual)):
        expected_count = expected.get(rule_id, 0)
        actual_count = actual.get(rule_id, 0)
        if expected_count == actual_count and expected_count > 0:
            normalized.append(
                ValidationFinding(
                    Level="warning",
                    Location=input_path.name,
                    RuleId=f"known_debt:{rule_id}",
                    Message=f"已登记技术债命中 {actual_count} 次（精确数量一致）",
                )
            )
        elif expected_count != actual_count:
            direction = "新增技术债" if actual_count > expected_count else "债清理后清单未收紧"
            normalized.append(
                ValidationFinding(
                    Level="error",
                    Location=input_path.name,
                    RuleId=f"known_debt:{rule_id}",
                    Message=(
                        f"登记数量={expected_count}，实际错误命中={actual_count}"
                        f"（{direction}）"
                    ),
                )
            )
    return normalized


def RunValidation(
    input_path: Path,
    warning_bytes: int,
    error_bytes: int,
    warnings_as_errors: bool = False,
) -> int:
    """读取并校验集合；错误（或指定时警告）返回 1。"""
    if warning_bytes <= 0 or error_bytes <= 0:
        print("Collection 校验失败：脚本阈值必须为正整数。", file=sys.stderr)
        return 1
    if warning_bytes >= error_bytes:
        print("Collection 校验失败：warning 阈值必须小于 error 阈值。", file=sys.stderr)
        return 1
    try:
        payload = LoadCollection(input_path)
        raw_findings = ValidateCollection(payload, warning_bytes, error_bytes)
        findings = ApplyKnownDebt(
            input_path,
            raw_findings,
            warning_bytes,
            error_bytes,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Collection 校验无法完成：{exc}", file=sys.stderr)
        return 1

    errors = [item for item in findings if item.Level == "error"]
    warnings = [item for item in findings if item.Level == "warning"]
    for item in errors:
        print(
            f"  - [错误] {item.Location} [{item.RuleId}] {item.Message}",
            file=sys.stderr,
        )
    visible_warnings = warnings[:100]
    for item in visible_warnings:
        print(f"  - [警告] {item.Location} [{item.RuleId}] {item.Message}")
    if len(warnings) > len(visible_warnings):
        print(f"  - [警告] 其余 {len(warnings) - len(visible_warnings)} 条已省略")
    if errors:
        print(
            f"Collection 校验失败：{len(errors)} 个错误，{len(warnings)} 个警告。",
            file=sys.stderr,
        )
        return 1
    if warnings_as_errors and warnings:
        print(
            f"Collection 校验失败：--warnings-as-errors 将 {len(warnings)} 个警告视为错误。",
            file=sys.stderr,
        )
        return 1
    print(f"Collection 校验通过：0 个错误，{len(warnings)} 个警告。")
    return 0


def Main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="离线校验 Postman Collection")
    parser.add_argument("--input", required=True, help="collection JSON 路径")
    parser.add_argument(
        "--warning-kb",
        type=int,
        default=40,
        help="单个 pre/test 脚本警告阈值，单位 KiB（默认 40）",
    )
    parser.add_argument(
        "--error-kb",
        type=int,
        default=50,
        help="单个 pre/test 脚本错误阈值，单位 KiB（默认 50）",
    )
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    return RunValidation(
        Path(str(args.input)).resolve(),
        int(args.warning_kb) * 1024,
        int(args.error_kb) * 1024,
        bool(args.warnings_as_errors),
    )


if __name__ == "__main__":
    raise SystemExit(Main())
