"""
解析 ``apifox run -r json`` / JUnit 报告，汇总失败步骤名与断言。

用法::

    python tools/apifox-cli/SummarizeApifoxRunFailures.py --report-dir apifox-reports
    python tools/apifox-cli/SummarizeApifoxRunFailures.py --json path/to/report.json --fail-on-error
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


JsonObject = Dict[str, Any]


@dataclass
class FailureItem:
    step_name: str
    detail: str = ""
    assertion: str = ""
    status_code: str = ""
    url: str = ""


@dataclass
class RunSummary:
    source: str
    total: int = 0
    failed: int = 0
    passed: int = 0
    failures: List[FailureItem] = field(default_factory=list)


def _AsList(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _PickStr(*candidates: Any) -> str:
    for item in candidates:
        if item is None:
            continue
        text = str(item).strip()
        if text:
            return text
    return ""


def _ExtractApifoxFailure(item: Mapping[str, Any]) -> FailureItem:
    """Apifox ``*-failures.json`` / ``run.failures[]`` 条目。"""
    error = item.get("error") if isinstance(item.get("error"), dict) else {}
    source = item.get("source") if isinstance(item.get("source"), dict) else {}
    err_source = error.get("source") if isinstance(error.get("source"), dict) else {}
    request = source.get("request") if isinstance(source.get("request"), dict) else {}
    url_obj = request.get("url") if isinstance(request.get("url"), dict) else {}
    path_parts = url_obj.get("path") if isinstance(url_obj.get("path"), list) else []
    path = "/" + "/".join(str(p) for p in path_parts) if path_parts else ""
    method = _PickStr(request.get("method"))
    step = _PickStr(source.get("name"), err_source.get("name"), item.get("name"))
    assertion = _PickStr(error.get("test"), item.get("test"), error.get("name"))
    detail = _PickStr(error.get("message"), item.get("message"), error.get("stack"))
    return FailureItem(
        step_name=step or "(unnamed)",
        detail=detail[:500],
        assertion=assertion,
        status_code="",
        url=(f"{method} {path}".strip() if method or path else ""),
    )


def ParseJsonReport(path: Path) -> RunSummary:
    raw = json.loads(path.read_text(encoding="utf-8"))
    summary = RunSummary(source=str(path))
    if not isinstance(raw, dict):
        return summary

    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    run = raw.get("run") if isinstance(raw.get("run"), dict) else {}
    stats_candidates = [
        raw.get("stats") if isinstance(raw.get("stats"), dict) else {},
        result.get("stats") if isinstance(result.get("stats"), dict) else {},
        run.get("stats") if isinstance(run.get("stats"), dict) else {},
    ]
    for blob in stats_candidates:
        if not blob:
            continue
        # Apifox: stats.steps / stats.requests / stats.assertions
        for key in ("steps", "requests", "assertions"):
            node = blob.get(key)
            if isinstance(node, dict) and (node.get("total") is not None or node.get("failed") is not None):
                total = int(node.get("total") or 0)
                failed = int(node.get("failed") or 0)
                passed = int(node.get("passed") or max(total - failed, 0))
                if key == "steps" or summary.total == 0:
                    summary.total = total
                    summary.failed = failed
                    summary.passed = passed
                break

    failures_raw: List[Any] = []
    for key in ("failures", "failed", "failedCases", "failedSteps"):
        for root in (raw, result, run):
            if isinstance(root.get(key), list):
                failures_raw.extend(root[key])

    for item in failures_raw:
        if not isinstance(item, dict):
            summary.failures.append(FailureItem(step_name=str(item)[:200]))
            continue
        # Apifox 形态优先
        if isinstance(item.get("error"), dict) or isinstance(item.get("source"), dict):
            summary.failures.append(_ExtractApifoxFailure(item))
            continue
        parent = item.get("parent") if isinstance(item.get("parent"), dict) else {}
        source = item.get("source") if isinstance(item.get("source"), dict) else {}
        error = item.get("error") if isinstance(item.get("error"), dict) else {}
        name = _PickStr(
            item.get("name"),
            item.get("stepName"),
            parent.get("name"),
            source.get("name"),
            item.get("at"),
        )
        summary.failures.append(
            FailureItem(
                step_name=name or "(unnamed)",
                detail=_PickStr(item.get("message"), error.get("message"), item.get("error"), item.get("stack"))[:500],
                assertion=_PickStr(item.get("assertion"), item.get("test"), error.get("name")),
                status_code=_PickStr(item.get("statusCode"), item.get("code")),
                url=_PickStr(item.get("url")),
            )
        )

    # 去重（同名保留首条）
    seen: set = set()
    uniq: List[FailureItem] = []
    for f in summary.failures:
        key = f"{f.step_name}|{f.assertion}|{f.detail[:80]}"
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    summary.failures = uniq
    if summary.failed == 0 and summary.failures:
        summary.failed = len(summary.failures)
    # 勿用失败条数伪造 total（failures 分离文件通常无 stats）
    return summary


def ParseJunitReport(path: Path) -> RunSummary:
    summary = RunSummary(source=str(path))
    root = ET.parse(path).getroot()
    suites = [root] if root.tag.endswith("testsuite") else list(root)
    for suite in suites:
        if not suite.tag.endswith("testsuite"):
            continue
        summary.total += int(suite.attrib.get("tests") or 0)
        summary.failed += int(suite.attrib.get("failures") or 0) + int(suite.attrib.get("errors") or 0)
        for case in suite.findall("testcase"):
            fail = case.find("failure")
            err = case.find("error")
            node = fail if fail is not None else err
            if node is None:
                continue
            summary.failures.append(
                FailureItem(
                    step_name=_PickStr(case.attrib.get("name"), case.attrib.get("classname")),
                    detail=_PickStr(node.attrib.get("message"), node.text)[:500],
                    assertion=_PickStr(node.attrib.get("type")),
                )
            )
    summary.passed = max(summary.total - summary.failed, 0)
    return summary


def FindLatestReports(report_dir: Path, *, prefix: str = "") -> List[Path]:
    if not report_dir.is_dir():
        return []
    json_files = sorted(report_dir.glob("**/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    junit_files = sorted(report_dir.glob("**/*.xml"), key=lambda p: p.stat().st_mtime, reverse=True)
    if prefix.strip():
        pref = prefix.strip()
        json_files = [p for p in json_files if p.name.startswith(pref)]
        junit_files = [p for p in junit_files if p.name.startswith(pref)]
    else:
        # 无 prefix 时只取最新一批（同 stem 前缀）
        if json_files:
            newest = json_files[0].name
            # <asset>-YYYYMMDD-HHMMSS[-failures].json
            base = newest.replace("-failures.json", "").replace(".json", "")
            json_files = [p for p in json_files if p.name.startswith(base)]
            junit_files = [p for p in junit_files if p.name.startswith(base)]
    preferred = [p for p in json_files if "fail" in p.name.lower()] + [
        p for p in json_files if "fail" not in p.name.lower()
    ]
    out: List[Path] = []
    for p in preferred:
        if p not in out:
            out.append(p)
    for p in junit_files:
        if p not in out:
            out.append(p)
    return out


def MergeSummaries(items: Sequence[RunSummary]) -> RunSummary:
    if not items:
        return RunSummary(source="(none)")
    # 优先 Apifox failures 分离 JSON（步骤名最完整）
    ranked = sorted(
        items,
        key=lambda s: (
            1 if "failures" in Path(s.source).name.lower() else 0,
            len(s.failures),
            s.failed,
            s.total,
        ),
        reverse=True,
    )
    best = ranked[0]
    # *-failures.json 已解析到空列表 = 本轮无失败；勿被同批 junit/主 JSON 的脏 failed 计数抬高
    failures_separated = "failures" in Path(best.source).name.lower()
    if failures_separated and not best.failures:
        best.failed = 0
    # 从任一含 stats 的报告补全 total/passed
    for other in ranked:
        if other.total > best.total:
            best.total = other.total
            best.passed = other.passed
        if (
            not failures_separated
            and other.failed > best.failed
            and not best.failures
        ):
            best.failed = other.failed
    if best.failures and best.failed == 0:
        best.failed = len(best.failures)
    if best.total > 0 and best.failed >= 0:
        best.passed = max(best.total - best.failed, 0)
    return best


def FormatMarkdown(summary: RunSummary) -> str:
    lines = [
        "# Apifox 运行失败汇总",
        "",
        f"- 来源: `{summary.source}`",
        f"- 总计: {summary.total}  通过: {summary.passed}  失败: {summary.failed}",
        "",
    ]
    if not summary.failures:
        lines.append("无失败步骤（或报告未解析到 failures 节点）。")
        return "\n".join(lines) + "\n"
    lines.append("## 失败步骤")
    lines.append("")
    for index, item in enumerate(summary.failures, start=1):
        lines.append(f"### {index}. {item.step_name}")
        if item.status_code:
            lines.append(f"- HTTP: `{item.status_code}`")
        if item.url:
            lines.append(f"- URL: `{item.url}`")
        if item.assertion:
            lines.append(f"- 断言: {item.assertion}")
        if item.detail:
            lines.append(f"- 详情: {item.detail}")
        lines.append("")
    return "\n".join(lines)


def PrintConsole(summary: RunSummary) -> None:
    def SafePrint(text: str) -> None:
        try:
            print(text)
        except UnicodeEncodeError:
            sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))

    SafePrint("=== Apifox run check ===")
    SafePrint(f"source: {summary.source}")
    SafePrint(f"total={summary.total} passed={summary.passed} failed={summary.failed}")
    if not summary.failures:
        SafePrint("failures: (none parsed)")
        return
    SafePrint(f"failures ({len(summary.failures)}):")
    for index, item in enumerate(summary.failures, start=1):
        SafePrint(f"  [{index}] {item.step_name}")
        if item.assertion:
            SafePrint(f"       assert: {item.assertion}")
        if item.detail:
            SafePrint(f"       detail: {item.detail[:240]}")
        if item.status_code or item.url:
            SafePrint(f"       http: {item.status_code} {item.url}".rstrip())


def Main() -> int:
    parser = argparse.ArgumentParser(description="Summarize Apifox run failures")
    parser.add_argument("--report-dir", default="", help="扫描目录内最新报告")
    parser.add_argument("--prefix", default="", help="只解析此前缀的报告（避免读到历史失败）")
    parser.add_argument("--json", default="", help="指定 JSON 报告路径")
    parser.add_argument("--junit", default="", help="指定 JUnit XML 路径")
    parser.add_argument("--write-md", default="", help="写出 Markdown 汇总路径")
    parser.add_argument("--fail-on-error", action="store_true", help="存在失败则 exit 1")
    args = parser.parse_args()

    summaries: List[RunSummary] = []
    if args.json:
        summaries.append(ParseJsonReport(Path(args.json)))
    if args.junit:
        summaries.append(ParseJunitReport(Path(args.junit)))
    if args.report_dir:
        for path in FindLatestReports(Path(args.report_dir), prefix=args.prefix):
            try:
                if path.suffix.lower() == ".json":
                    summaries.append(ParseJsonReport(path))
                elif path.suffix.lower() == ".xml":
                    summaries.append(ParseJunitReport(path))
            except (OSError, json.JSONDecodeError, ET.ParseError) as exc:
                print(f"skip {path}: {exc}", file=sys.stderr)

    if not summaries:
        print("未找到可解析报告。请先 apifox run -r json,junit --out-dir <dir>", file=sys.stderr)
        return 2

    summary = MergeSummaries(summaries)
    PrintConsole(summary)
    md_path = Path(args.write_md) if args.write_md else None
    if md_path is None and args.report_dir:
        md_path = Path(args.report_dir) / "last-failures.md"
    if md_path is not None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(FormatMarkdown(summary), encoding="utf-8")
        print(f"wrote: {md_path}")

    if args.fail_on_error and (summary.failed > 0 or summary.failures):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
