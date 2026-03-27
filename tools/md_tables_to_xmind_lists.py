#!/usr/bin/env python3
"""
将 Markdown 中的管道表格转为无序列表，便于 XMind「从 Markdown 导入」时在主图展开子主题。

规则：
- 识别连续的 | ... | 行（含表头分隔行 | --- | --- |）
- 两列表格：输出为「- 左列：右列」；跳过表头分隔行；表头若为（字段路径/预期）、（项/约定）、（Body 变体/说明）、（前置状态/目标 status）则跳过首行
- 非表格行原样输出

用法：
  python tools/md_tables_to_xmind_lists.py <输入.md> [-o 输出.md]
  默认输出：<输入文件名>-xmind.md（同目录）
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and len(s) > 2


def parse_table_row(line: str) -> list[str]:
    # 去掉首尾 | 再按 | 分割
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.match(r"^:?-{3,}:?$", c.strip()) is not None for c in cells if c.strip()) and any(
        "-" in c for c in cells
    )


SKIP_HEADER_PAIRS = {
    ("字段路径", "预期"),
    ("项", "约定"),
    ("Body 变体", "说明"),
    ("前置状态", "目标 status"),
    ("字段路径", "预期 "),
}


def table_to_bullets(rows: list[str]) -> list[str]:
    parsed: list[list[str]] = []
    for row in rows:
        cells = parse_table_row(row)
        parsed.append(cells)

    # 去掉分隔行
    data_rows: list[list[str]] = []
    for cells in parsed:
        if not cells:
            continue
        if is_separator_row(cells):
            continue
        data_rows.append(cells)

    if not data_rows:
        return []

    # 跳过已知表头
    if len(data_rows[0]) >= 2:
        key = (data_rows[0][0].strip(), data_rows[0][1].strip())
        if key in SKIP_HEADER_PAIRS or (
            data_rows[0][0].strip() == "字段路径" and "预期" in data_rows[0][1].strip()
        ):
            data_rows = data_rows[1:]

    out: list[str] = []
    for cells in data_rows:
        if not cells or not any(c.strip() for c in cells):
            continue
        if len(cells) == 1:
            out.append(f"- {cells[0]}")
        elif len(cells) == 2:
            left, right = cells[0], cells[1]
            out.append(f"- {left}：{right}")
        else:
            out.append(f"- {' | '.join(cells)}")
    return out


def insert_xmind_banner(text: str, source_name: str) -> str:
    """在首个一级标题后插入导入说明（blockquote），便于与源文件区分。"""
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].lstrip().startswith("#"):
        return text
    i = 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    banner = (
        "\n> **XMind 导入专用**：本文件由脚本将 `{src}` 中的 **Markdown 表格** 转为 **无序列表**，"
        "便于 XMind 24「从 Markdown 导入」时在主图展开子主题。**维护与评审以源文件为准**；"
        "修改源文件后请重新运行本脚本生成。\n\n"
    ).format(src=source_name)
    return "".join(lines[:i]) + banner + "".join(lines[i:])


def convert(text: str) -> str:
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        stripped = line.rstrip("\n\r")

        if is_table_row(stripped):
            block: list[str] = []
            start = i
            while i < n and is_table_row(lines[i].rstrip("\n\r")):
                block.append(lines[i].rstrip("\n\r"))
                i += 1
            bullets = table_to_bullets(block)
            if bullets:
                for b in bullets:
                    result.append(b + "\n")
            else:
                # 无法解析则保留原表格
                for j in range(start, i):
                    result.append(lines[j])
            continue

        result.append(line)
        i += 1

    return "".join(result)


def main() -> int:
    ap = argparse.ArgumentParser(description="Markdown 表格转列表（XMind 导入）")
    ap.add_argument("input", type=Path, help="输入 .md 路径")
    ap.add_argument("-o", "--output", type=Path, default=None, help="输出路径（默认 输入-xmind.md）")
    args = ap.parse_args()
    inp: Path = args.input
    if not inp.is_file():
        print(f"文件不存在: {inp}", file=sys.stderr)
        return 1
    out = args.output
    if out is None:
        out = inp.with_name(inp.stem + "-xmind" + inp.suffix)

    text = inp.read_text(encoding="utf-8")
    text = insert_xmind_banner(text, inp.name)
    converted = convert(text)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(converted)
    print(f"已写入: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
