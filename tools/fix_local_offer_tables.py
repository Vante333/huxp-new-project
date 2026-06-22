# -*- coding: utf-8 -*-
"""将 Q2-Local-Offer.md 中 Confluence pipe 片段重建为标准 Markdown 表格。"""
from __future__ import annotations

import re
from pathlib import Path


def _ParseCell(line: str) -> str | None:
    s = line.strip()
    if not s or s == "|":
        return None
    m = re.match(r"^错误码(500\.\d+\.\d+)\s*$", s)
    if m:
        return m.group(1)
    m = re.match(r"^(500\.\d+\.\d+)\s*$", s)
    if m:
        return m.group(1)
    m = re.match(r"^\|\s*(.*?)\s*$", s)
    if m:
        val = m.group(1).strip()
        return val if val else None
    if s.startswith("/v2/"):
        return s
    return None


def _IsPipeLine(line: str) -> bool:
    return line.strip() == "" or _ParseCell(line) is not None


def _TableKind(cells: list[str]) -> str:
    if any(c.startswith("/v2/") for c in cells):
        return "api"
    if any(re.match(r"^500\.", c) for c in cells):
        return "error"
    if "买赠" in cells or "Buy X get Y" in cells:
        return "tag"
    if any(c in ("Fixed", "After Activation", "Dynamic") for c in cells):
        return "validity"
    if any("卡密" in c or "二维码" in c for c in cells):
        return "voucher"
    if "其他不符合取消政策" in cells:
        return "error"
    return "generic"


def _Headers(kind: str) -> list[str]:
    return {
        "api": ["接口", "说明", "需求"],
        "error": ["错误码", "说明", "英文描述"],
        "tag": ["原始表达", "推荐枚举值", "说明"],
        "validity": ["Type", "BOSS", ""],
        "voucher": ["voucherType", "展示方式", "BOSS 类型"],
        "generic": ["列1", "列2", "列3"],
    }[kind]


def _PrepareCells(cells: list[str], kind: str) -> list[str]:
    data = [c for c in cells if c not in ("voucherType enumenum",)]
    if kind == "api":
        while data and not data[0].startswith("/v2/"):
            data.pop(0)
    elif kind in ("tag", "validity", "voucher"):
        drop = {"原始表达", "推荐枚举值", "说明", "展示方式", "BOSS类型", "Type", "BOSS", "接口", "需求"}
        while data and data[0] in drop:
            data.pop(0)
    elif kind == "error":
        merged: list[str] = []
        i = 0
        while i < len(data):
            if re.match(r"^500\.", data[i]):
                code = data[i]
                desc = data[i + 1] if i + 1 < len(data) else ""
                eng = data[i + 2] if i + 2 < len(data) else ""
                merged.extend([code, desc, eng])
                i += 3
            else:
                merged.append(data[i])
                i += 1
        data = merged
    return data


def _Render(kind: str, cells: list[str]) -> list[str]:
    headers = _Headers(kind)
    rows = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * 3) + " |",
    ]
    for i in range(0, len(cells) - (len(cells) % 3), 3):
        row = cells[i : i + 3]
        while len(row) < 3:
            row.append("")
        rows.append("| " + " | ".join(row) + " |")
    return rows


def FixTables(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not _IsPipeLine(lines[i]) or _ParseCell(lines[i]) is None:
            out.append(lines[i])
            i += 1
            continue

        block: list[str] = []
        j = i
        while j < len(lines) and _IsPipeLine(lines[j]):
            if lines[j].strip():
                block.append(lines[j])
            j += 1

        cells = [_ParseCell(x) for x in block]
        cells = [c for c in cells if c is not None]
        if len(cells) < 3:
            out.extend(block)
            i = j
            continue

        kind = _TableKind(cells)
        prepared = _PrepareCells(cells, kind)
        if len(prepared) >= 3 and len(prepared) % 3 == 0:
            out.extend(_Render(kind, prepared))
        else:
            out.extend(block)
        i = j
    return "\n".join(out)


def MergeDuplicateTables(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in ("| 错误码 | 说明 | 英文描述 |", "| 接口 | 说明 | 需求 |"):
            header = line
            sep = "| --- | --- | --- |"
            out.append(header)
            out.append(sep)
            i += 1
            if i < len(lines) and lines[i] == sep:
                i += 1
            while i < len(lines):
                cur = lines[i]
                if cur in ("| 错误码 | 说明 | 英文描述 |", "| 接口 | 说明 | 需求 |"):
                    i += 1
                    if i < len(lines) and lines[i] == sep:
                        i += 1
                    continue
                if cur == sep:
                    i += 1
                    continue
                if cur.startswith("| ") and ("500." in cur or "/v2/" in cur or cur == "| 接口 | 说明 | 需求 |"):
                    if cur in ("| 接口 | 说明 | 需求 |", "| 错误码 | 说明 | 英文描述 |"):
                        i += 1
                        continue
                    out.append(cur)
                    i += 1
                    continue
                break
            continue
        if line.strip() in ("| 接口", "| 需求") or re.match(r"^\s*\|\s*接口\s*$", line):
            i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def CleanupMarkdown(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not re.match(r"^\s*\|\s*$", ln)]
    text = "\n".join(lines)
    return MergeDuplicateTables(text)


def Main() -> None:
    path = Path(__file__).resolve().parent.parent / "requirements" / "2026Q2_SP3" / "Q2-Local-Offer.md"
    text = path.read_text(encoding="utf-8")
    text = FixTables(text)
    text = CleanupMarkdown(text)
    path.write_text(text + "\n", encoding="utf-8")
    print(f"Tables fixed: {path}")


if __name__ == "__main__":
    Main()
