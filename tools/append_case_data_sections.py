"""为测试分析 Markdown 中每个 tc 用例追加「数据」列表节点（与 XMind 平级子主题一致）。"""
from __future__ import annotations

import re

_TC_HEADER_RE = re.compile(r"^#{3,4} tc(?:-p\d+)?:", re.M)
_DATA_BLOCK = """- 数据
  - apifox链接 ——（待补充）
  - boss配置 ——（待补充）
  - saas截图 ——（待补充）
  - saas价格返回 ——（待补充）"""
_OLD_HEADING_DATA_RE = re.compile(
    r"\n#### 数据\n\n(?:- [^\n]+\n){4}\n*",
    re.M,
)
_HAS_DATA_NODE_RE = re.compile(r"^- 数据\s*$", re.M)


def _IsTcHeader(line: str) -> bool:
    return bool(_TC_HEADER_RE.match(line))


def _HeaderLevel(line: str) -> int:
    return len(line) - len(line.lstrip("#"))


def _IsCaseBoundary(line: str, case_level: int) -> bool:
    if not line.startswith("#"):
        return False
    if _IsTcHeader(line):
        return True
    level = _HeaderLevel(line)
    if level < case_level:
        return True
    if case_level == 4 and level == 3 and not _IsTcHeader(line):
        return True
    return False


def _HasDataNode(body: str) -> bool:
    return "#### 数据" in body or bool(_HAS_DATA_NODE_RE.search(body))


def _NormalizeCaseBody(body: str) -> str:
    """去掉旧版 ``#### 数据`` 标题块；**不**改动步骤原文。"""
    return _OLD_HEADING_DATA_RE.sub("\n", body).strip("\n")


def AppendCaseDataSections(text: str) -> str:
    """在步骤列表末尾追加 ``- 数据`` 子节点；不修改既有步骤与章节编排。"""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _IsTcHeader(line):
            out.append(line)
            i += 1
            continue
        case_level = _HeaderLevel(line)
        case_lines: list[str] = [line.rstrip("\n")]
        i += 1
        while i < len(lines) and not _IsCaseBoundary(lines[i], case_level):
            case_lines.append(lines[i].rstrip("\n"))
            i += 1
        body = _NormalizeCaseBody("\n".join(case_lines))
        if not _HasDataNode(body):
            body = body.rstrip() + "\n" + _DATA_BLOCK
        out.append(body + "\n\n")
    return "".join(out)
