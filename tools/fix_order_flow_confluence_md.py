# -*- coding: utf-8 -*-
"""修复「订单流支持【真现金支付】【第三方权益】」Confluence 拉取 Markdown 的格式问题。"""
from __future__ import annotations

import re
from pathlib import Path


def ReplaceHtmlEntities(text: str) -> str:
    replacements = {
        "&mdash;": "——",
        "&rsquo;": "'",
        "&ldquo;": '"',
        "&rdquo;": '"',
        "&rarr;": "->",
        "&nbsp;": " ",
        "&ndash;": "–",
        "&ge;": ">=",
        "&lt;": "<",
        "&gt;": ">",
        "&Ita&uacute;": "Itaú",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def SplitMergedHeadings(text: str) -> str:
    """拆分 html2text 将标题与正文粘连的行。"""
    lines = text.splitlines()
    out: list[str] = []

    heading_content_splits: list[tuple[str, str]] = [
        ("### 1.2 主要改动内容", "商品选择部分："),
        ("### 1.3 参考资料", "saas的需求："),
        ("### 2.1.1 初始化", "saas新增兑换类型的需求："),
        ("### 2.1.2 动态选择商品", "PAPI-2667"),
        ("### 2.2 预览订单接口", "预览订单这步，"),
        ("### 2.2.1 payment object 返回内容", "payment object 与 extra 同级"),
        ("### 2.2.2 Membership", "https://developer-sandbox.dragonpass.com/api/v2/orders/{modules}/memberships/prebooking/preview"),
        ("### 2.2.3 E-pass", "新增预览接口（先不支持bundle单收款）"),
        ("### 2.2.4 错误提示语（预览+创建订单）", "休息室"),
        ("### 2.3 拉起DP收银台", "2.3.1 是否要拉起收银台"),
        ("### 2.3.1 是否要拉起收银台", "与2.1.2逻辑是一样的"),
        ("### 2.3.2 创单后返回", "对于需要拉起收银台的订单"),
        ("### 2.3.3 获取支付链接接口", "POST /v2/orders/payments"),
        ("### 2.3.4 错误提示语", "500.000.801"),
        ("### 2.4 支付状态Callback", "2.5 订单详情见2.2 payment下几个大模块的返回逻辑"),
    ]

    for line in lines:
        replaced = False
        for prefix, content_start in heading_content_splits:
            if line.startswith(prefix) and not line.strip() == prefix:
                rest = line[len(prefix) :]
                if rest.startswith(content_start) or content_start in rest:
                    out.append(prefix)
                    out.append("")
                    out.append(rest.lstrip())
                    replaced = True
                    break
        if not replaced:
            out.append(line)

    text = "\n".join(out)

    text = re.sub(
        r"^## 一、概述(\d+\.\d+ .+)$",
        r"## 一、概述\n\n### \1",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^## 二、需求(\d+\.\d+ .+)$",
        r"## 二、需求\n\n### \1",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^### 2\.3 拉起DP收银台2\.3\.1",
        "### 2.3 拉起DP收银台\n\n#### 2.3.1",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^### 2\.4 支付状态Callback2\.5",
        "### 2.4 支付状态Callback\n\n### 2.5",
        text,
        flags=re.MULTILINE,
    )
    return text


def _IsPipeLine(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|")


def _ParsePipeLine(line: str) -> str:
    return line.strip().lstrip("|").strip()


def _TryParseBrokenTable(lines: list[str], start: int) -> tuple[list[list[str]], int] | None:
    """尝试从 start 位置解析断裂表格，失败返回 None。"""
    if start + 2 >= len(lines):
        return None
    if not lines[start].strip():
        return None
    if not _IsPipeLine(lines[start + 1]) and not (
        lines[start + 1].strip() == "" and start + 2 < len(lines) and _IsPipeLine(lines[start + 2])
    ):
        return None

    rows: list[list[str]] = []
    cell1_parts: list[str] = []
    cell2_parts: list[str] = []
    in_cell2 = False
    i = start

    def _FlushRow() -> None:
        nonlocal cell1_parts, cell2_parts
        c1 = "\n".join(cell1_parts).strip()
        c2 = "\n".join(cell2_parts).strip()
        if c1 or c2:
            rows.append([c1, c2] if not rows or len(rows[-1]) != 2 else [c1, c2])
        cell1_parts = []
        cell2_parts = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if _IsPipeLine(line):
            payload = _ParsePipeLine(line)
            if not in_cell2:
                if cell1_parts:
                    in_cell2 = True
                    if payload:
                        cell2_parts.append(payload)
                elif payload:
                    cell1_parts.append(payload)
            else:
                if payload:
                    cell2_parts.append(payload)
                else:
                    rows.append(
                        [
                            "\n".join(cell1_parts).strip(),
                            "\n".join(cell2_parts).strip(),
                        ]
                    )
                    cell1_parts = []
                    cell2_parts = []
                    in_cell2 = False
            i += 1
            continue

        if stripped == "":
            if in_cell2 and cell1_parts:
                rows.append(
                    [
                        "\n".join(cell1_parts).strip(),
                        "\n".join(cell2_parts).strip(),
                    ]
                )
                cell1_parts = []
                cell2_parts = []
                in_cell2 = False
                i += 1
                if rows and i < len(lines) and not _IsPipeLine(lines[i]) and lines[i].strip():
                    if not (i + 1 < len(lines) and (lines[i + 1].strip() == "" and i + 2 < len(lines) and _IsPipeLine(lines[i + 2]))):
                        break
                continue
            i += 1
            if rows:
                break
            continue

        if not in_cell2:
            cell1_parts.append(stripped)
        else:
            cell2_parts.append(stripped)
        i += 1

    if in_cell2 and (cell1_parts or cell2_parts):
        rows.append(
            [
                "\n".join(cell1_parts).strip(),
                "\n".join(cell2_parts).strip(),
            ]
        )

    if len(rows) < 2:
        return None
    return rows, i


def _TryParseMultiColumnTable(lines: list[str], start: int) -> tuple[list[list[str]], int] | None:
    """解析多列断裂表格（错误码、枚举等）。"""
    chunk: list[str] = []
    i = start
    while i < len(lines):
        s = lines[i].strip()
        if s == "" and chunk and i + 1 < len(lines):
            nxt = lines[i + 1].strip()
            if not _IsPipeLine(lines[i + 1]) and not re.match(r"^#{1,4}\s", nxt) and not nxt.startswith("```"):
                break
        if re.match(r"^#{1,4}\s", s) or s.startswith("```"):
            break
        chunk.append(lines[i])
        i += 1

    if len(chunk) < 4:
        return None

    rows: list[list[str]] = []
    current_row: list[str] = []
    current_cell: list[str] = []

    for line in chunk:
        if _IsPipeLine(line):
            payload = _ParsePipeLine(line)
            if current_cell:
                current_row.append("\n".join(current_cell).strip())
                current_cell = []
            if payload:
                current_row.append(payload)
            if line.strip() in {"|", "| "}:
                if current_row:
                    rows.append(current_row)
                    current_row = []
        else:
            stripped = line.strip()
            if stripped:
                current_cell.append(stripped)

    if current_cell:
        current_row.append("\n".join(current_cell).strip())
    if current_row:
        rows.append(current_row)

    if len(rows) < 2:
        return None

    col_counts = {len(r) for r in rows}
    if len(col_counts) != 1:
        return None
    if max(col_counts) < 2:
        return None

    return rows, i


def _FormatMarkdownTable(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    normalized = [r + [""] * (col_count - len(r)) for r in rows]
    header = normalized[0]
    sep = ["---"] * col_count
    body = normalized[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(sep) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def RebuildBrokenTables(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() and (
            (i + 1 < len(lines) and _IsPipeLine(lines[i + 1]))
            or (
                i + 2 < len(lines)
                and lines[i + 1].strip() == ""
                and _IsPipeLine(lines[i + 2])
            )
        ):
            parsed = _TryParseMultiColumnTable(lines, i)
            if parsed is None:
                parsed = _TryParseBrokenTable(lines, i)
            if parsed is not None:
                rows, end = parsed
                table_md = _FormatMarkdownTable(rows)
                if out and out[-1].strip():
                    out.append("")
                out.append(table_md)
                out.append("")
                i = end
                continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def FixSummaryList(text: str) -> str:
    """将「总结」后的商品类型列表整理为列表项。"""
    replacements = [
        (
            "| 总结： | 商品类型 | DP收款 | 客户预收款 | 纯权益支付 |",
            "总结：\n\n| 商品类型 | DP收款 | 客户预收款 | 纯权益支付 |",
        ),
        (
            "总结：每个品类都需要初始化3个商品：\n\n客户预售费\n\n权益支付\n\n现金（支持权益抵扣）",
            "总结：每个品类都需要初始化3个商品：\n\n- 客户预售费\n- 权益支付\n- 现金（支持权益抵扣）",
        ),
        (
            "CLIENT_COLLECT不传+cashPaymentApplied=true\n\n | ✅ cashPaymentApplied=false",
            "CLIENT_COLLECT 不传 + cashPaymentApplied=true | ✅ cashPaymentApplied=false",
        ),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def CompressListBlankLines(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for idx, line in enumerate(lines):
        if line.strip() == "" and out and re.match(r"^-\s", out[-1]):
            if idx + 1 < len(lines) and re.match(r"^-\s", lines[idx + 1]):
                continue
        out.append(line)
    return "\n".join(out)


def NormalizeCodeFenceLanguage(text: str) -> str:
    text = re.sub(
        r"(?m)^(POST /v2/[^\n]+)$",
        r"```text\n\1\n```",
        text,
    )
    return text


def FixOrderFlowMarkdown(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    steps = [
        ReplaceHtmlEntities,
        SplitMergedHeadings,
        FixSummaryList,
        NormalizeCodeFenceLanguage,
        CompressListBlankLines,
    ]
    result = raw
    for fn in steps:
        result = fn(result)
    if not result.endswith("\n"):
        result += "\n"
    path.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    target = (
        Path(__file__).resolve().parent.parent
        / "requirements"
        / "2026Q2SP4"
        / "Confluence-1906049058.md"
    )
    FixOrderFlowMarkdown(target)
    print(f"Fixed: {target}")
