from __future__ import annotations

"""将 XMind 工作簿（content.json）转为与本仓库 testcases 兼容的 Markdown。

用法（PowerShell，仓库根目录）::

    python tools/xmind_workbook_to_testcase_md.py `
      --src \"d:\\fenxi\\清结算\\2026_Q2\\评审前\\升降级权益策略3测试用例.xmind\" `
      --out testcases/2026Q2_SP2/升降级权益策略3测试用例-001.md

说明：

- 仅解析 ``content.json``（XMind 为 ZIP）；不读 ``content.xml``。
- 根节点 → ``#``；一级子节点 → ``##``；以 ``tc-p1:`` / ``tc-p2:`` / ``tc-p3:`` / ``tc:`` 开头的节点 → ``###``。
- 带 ``org.xmind.ui.spreadsheet`` 扩展的节点会导出为 Markdown 表格（列来自扩展，行来自子主题）。
- 其它节点按 ``pc:``、``- 步骤`` + ``  - 预期`` 规则展开；与 ``.cursor/skills/test-case-design-with-priority`` 脑图结构一致。

路径约定：脚本位于 ``tools/xmind_workbook_to_testcase_md.py``；``--out`` 可为相对仓库根的路径。
"""

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional


def GetTopicTitle(topic: Dict[str, Any]) -> str:
    if "attributedTitle" in topic:
        return "".join(str(x.get("text", "")) for x in topic["attributedTitle"])
    return str(topic.get("title", ""))


def IsTcHeader(title: str) -> bool:
    t = title.strip()
    return bool(re.match(r"^tc-p[123]:", t, re.I)) or t.lower().startswith("tc:")


def _GetSpreadsheetColumnHeaders(topic: Dict[str, Any]) -> Optional[List[str]]:
    for ext in topic.get("extensions") or []:
        if ext.get("provider") != "org.xmind.ui.spreadsheet":
            continue
        for block in ext.get("content") or []:
            if block.get("name") != "columns":
                continue
            cols = block.get("content") or []
            headers: List[str] = []
            for col in cols:
                if isinstance(col, dict) and "content" in col:
                    headers.append(str(col.get("content", "")).strip())
            return headers if headers else None
    return None


def _SpreadsheetMarkdownTableLines(topic: Dict[str, Any]) -> Optional[List[str]]:
    headers = _GetSpreadsheetColumnHeaders(topic)
    if not headers:
        return None
    row_topics = (topic.get("children") or {}).get("attached") or []
    if not row_topics:
        return None
    body_rows: List[List[str]] = []
    for row_topic in row_topics:
        cells: List[str] = [GetTopicTitle(row_topic).strip()]
        for c in (row_topic.get("children") or {}).get("attached") or []:
            cells.append(GetTopicTitle(c).strip())
        while len(cells) < len(headers):
            cells.append("")
        body_rows.append(cells[: len(headers)])
    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    head = "| " + " | ".join(headers) + " |"
    lines = [head, sep]
    for r in body_rows:
        lines.append("| " + " | ".join(r) + " |")
    return lines


def _LastNonEmptyLineKind(lines: List[str]) -> str:
    if not lines:
        return "none"
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i]
        if not s.strip():
            continue
        if s.startswith("  - "):
            return "expect"
        if s.startswith("- "):
            return "lone"
        if s.startswith("| "):
            return "table"
        if s.startswith("pc:"):
            return "pc"
        return "other"
    return "none"


def _EmitTcBody(lines: List[str], tc_node: Dict[str, Any]) -> None:
    for child in (tc_node.get("children") or {}).get("attached") or []:
        t = GetTopicTitle(child).strip()
        if t.lower().startswith("pc:"):
            lines.append(t if t[:3].lower() == "pc:" else f"pc: {t}")
            lines.append("")
            continue
        tbl = _SpreadsheetMarkdownTableLines(child)
        if tbl is not None:
            kind = _LastNonEmptyLineKind(lines)
            if kind in ("expect", "lone"):
                lines.append("")
            lines.extend(tbl)
            lines.append("")
            continue
        sub = (child.get("children") or {}).get("attached") or []
        if not sub:
            kind = _LastNonEmptyLineKind(lines)
            if kind in ("expect", "table"):
                lines.append("")
            lines.append(f"- {t}")
            continue
        kind = _LastNonEmptyLineKind(lines)
        if kind in ("expect", "lone", "table"):
            lines.append("")
        if len(sub) == 1:
            exp = GetTopicTitle(sub[0]).strip()
            lines.append(f"- {t}")
            lines.append(f"  - {exp}")
        else:
            lines.append(f"- {t}")
            for s in sub:
                st = GetTopicTitle(s).strip()
                lines.append(f"  - {st}")
    lines.append("")


def _EmitFreeformTopic(lines: List[str], topic: Dict[str, Any], indent: int) -> None:
    t = GetTopicTitle(topic).strip()
    prefix = "  " * indent + "- "
    lines.append(f"{prefix}{t}")
    for c in (topic.get("children") or {}).get("attached") or []:
        _EmitFreeformTopic(lines, c, indent + 1)


def FormatMdFromRoot(root: Dict[str, Any]) -> str:
    lines: List[str] = []
    h1 = GetTopicTitle(root).strip()
    lines.append(f"# {h1}")
    lines.append("")
    attached = (root.get("children") or {}).get("attached") or []
    for sec in attached:
        sec_title = GetTopicTitle(sec).strip()
        lines.append(f"## {sec_title}")
        lines.append("")
        for node in (sec.get("children") or {}).get("attached") or []:
            nt = GetTopicTitle(node).strip()
            if not IsTcHeader(nt):
                lines.append(f"### {nt}")
                lines.append("")
                _EmitFreeformTopic(lines, node, indent=0)
                continue
            lines.append(f"### {nt}")
            lines.append("")
            _EmitTcBody(lines, node)
        lines.append("")
    while lines and lines[-1] == "" and len(lines) > 1 and lines[-2] == "":
        lines.pop()
    return "\n".join(lines).rstrip() + "\n"


def LoadRootTopicFromXmind(path: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(path, "r") as zf:
        raw = zf.read("content.json")
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("content.json 根应为非空数组")
    sheet = data[0]
    root = sheet.get("rootTopic")
    if not isinstance(root, dict):
        raise ValueError("缺少 rootTopic")
    return root


def ParseArgs() -> argparse.Namespace:
    repo = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="XMind content.json → testcase Markdown")
    p.add_argument(
        "--src",
        type=Path,
        required=True,
        help="源 .xmind 文件绝对或相对路径",
    )
    p.add_argument(
        "--out",
        type=Path,
        required=True,
        help="输出 .md 路径（相对当前工作目录或绝对路径）",
    )
    p.add_argument(
        "--cwd",
        type=Path,
        default=repo,
        help=f"解析相对路径时的基准目录（默认：仓库根 {repo}）",
    )
    return p.parse_args()


def Main() -> None:
    args = ParseArgs()
    src = (args.cwd / args.src).resolve() if not args.src.is_absolute() else args.src
    out = (args.cwd / args.out).resolve() if not args.out.is_absolute() else args.out
    if not src.is_file():
        raise FileNotFoundError(f"找不到 XMind 文件: {src}")
    root = LoadRootTopicFromXmind(src)
    md = FormatMdFromRoot(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md.replace("\r\n", "\n"), encoding="utf-8")


if __name__ == "__main__":
    Main()
