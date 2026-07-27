"""
通用 Apifox 失败分流：脚本问题 vs 业务/环境问题。

规则从 ``.apifox/suites.yaml`` 资产下的 ``triage.script_name_patterns`` 读取（可选）。
未配置任何 pattern 时，全部失败视为 leftover（需人/AI 改正本）。

退出码：
- ``0``：无失败
- ``1``：存在非脚本（leftover）失败，已写 ``leftover-failures.md``
- ``10``：仅脚本类失败（匹配 pattern）——编排层可再 Generate+Push+Run 一轮；
  **不再**自动改写生成器源码（补丁应合进正本后删除对应 pattern）

用法::

    python tools/TriageApifoxRunFailures.py --report-dir apifox-reports/papi_2548 --asset papi_2548
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from ApifoxSuitesYaml import (  # noqa: E402
    LoadSuitesText,
    ParseAssetFields,
    ParseTriageScriptPatterns,
    RepoRootFromArg,
)


def LoadFailureNames(report_dir: Path, prefix: str) -> List[str]:
    names: List[str] = []
    files = sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if prefix:
        files = [p for p in files if p.name.startswith(prefix) and "fail" in p.name.lower()]
    else:
        files = [p for p in files if "fail" in p.name.lower()][:1]
    for path in files:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for item in raw.get("failures") or []:
            if not isinstance(item, dict):
                continue
            error = item.get("error") if isinstance(item.get("error"), dict) else {}
            source = item.get("source") if isinstance(item.get("source"), dict) else {}
            err_src = error.get("source") if isinstance(error.get("source"), dict) else {}
            name = str(source.get("name") or err_src.get("name") or error.get("test") or "").strip()
            if name:
                names.append(name)
    return names


def CompilePatterns(raw_patterns: Sequence[str]) -> List[re.Pattern[str]]:
    compiled: List[re.Pattern[str]] = []
    for raw in raw_patterns:
        try:
            compiled.append(re.compile(raw))
        except re.error as exc:
            raise SystemExit(f"invalid triage regex {raw!r}: {exc}") from exc
    return compiled


def Classify(
    names: Sequence[str],
    patterns: Sequence[re.Pattern[str]],
) -> Tuple[List[str], List[str]]:
    """返回 (script_issues, leftover)。无 pattern 时全部为 leftover。"""
    script: List[str] = []
    leftover: List[str] = []
    if not patterns:
        return [], list(names)
    for name in names:
        if any(p.search(name) for p in patterns):
            script.append(name)
        else:
            leftover.append(name)
    return script, leftover


def WriteLeftoverMarkdown(report_dir: Path, leftover: Sequence[str]) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    md = report_dir / "leftover-failures.md"
    lines = [
        "# 非脚本问题（请人工核对）",
        "",
        "未匹配 `suites.yaml` → `triage.script_name_patterns` 的失败均落此清单。",
        "脚本类问题应改正本生成器后 SyncCheck；修完后请删除已无用的 pattern。",
        "",
    ]
    for name in leftover:
        lines.append(f"- {name}")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def Main() -> int:
    parser = argparse.ArgumentParser(description="Triage Apifox run failures (generic)")
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--asset", required=True, help="assets key in .apifox/suites.yaml")
    parser.add_argument("--repo-root", default="")
    parser.add_argument(
        "--suites",
        default="",
        help="override path to suites.yaml (default: <repo>/.apifox/suites.yaml)",
    )
    args = parser.parse_args()

    repo = RepoRootFromArg(args.repo_root)
    report_dir = Path(args.report_dir)
    if not report_dir.is_absolute():
        report_dir = (repo / report_dir).resolve()

    text = LoadSuitesText(repo, args.suites)
    # 确认资产存在
    ParseAssetFields(text, args.asset)
    raw_patterns = ParseTriageScriptPatterns(text, args.asset)
    patterns = CompilePatterns(raw_patterns)
    names = LoadFailureNames(report_dir, args.prefix)

    if not names:
        # 成功时清掉旧 leftover，避免误读历史失败清单
        stale = report_dir / "leftover-failures.md"
        if stale.is_file():
            stale.write_text(
                "# 非脚本问题（请人工核对）\n\n"
                "本次运行无失败步骤；旧 leftover 清单已清空。\n",
                encoding="utf-8",
            )
            print(f"triage: cleared stale {stale.name}")
        print("triage: no failures")
        return 0

    script, leftover = Classify(names, patterns)
    print(
        f"triage: asset={args.asset} patterns={len(patterns)} "
        f"total_fail_steps={len(names)} script={len(script)} leftover={len(leftover)}"
    )
    for n in script:
        print(f"  [SCRIPT] {n}")
    for n in leftover:
        print(f"  [LEAVE]  {n}")

    if leftover:
        md = WriteLeftoverMarkdown(report_dir, leftover)
        print(f"triage: wrote {md}")
        return 1

    if script:
        print(
            "triage: script-like failures only — regenerate+push+rerun once "
            "(fix generator source; do not add per-asset triage .py)"
        )
        return 10

    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
