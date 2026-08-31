from __future__ import annotations

"""XMind（tc-p* / tc: 节点）→ testcases 可导入 Markdown。

用法（仓库根目录）：
  python tools/req-docs/xmind_to_testcases_md.py \\
    --xmind path/to/file.xmind \\
    --out testcases/2026Q2SP4/PAPI-xxxx-测试用例-001.md \\
    --requirement requirements/2026Q2SP4/PAPI-xxxx.md

仅导出脑图中 tc 用例节点；判定表等未挂 tc 子树的内容不会写入输出。
模块路径按脑图原始嵌套输出为 H2/H3/…（不再用 ``-`` 拼成单层 H2）。
详见 tools/README.md 与 .cursor/skills/test-case-design-with-priority/reference.md §8.4。
"""

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Callable, List


def _LoadRootFromXmind(xmind: Path) -> dict[str, Any]:
    with zipfile.ZipFile(xmind, "r") as zf:
        with zf.open("content.json") as fp:
            data = json.loads(fp.read().decode("utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("content.json: 期望非空数组")
    sheet0 = data[0]
    if not isinstance(sheet0, dict) or "rootTopic" not in sheet0:
        raise ValueError("content.json: 缺少 rootTopic")
    root = sheet0["rootTopic"]
    if not isinstance(root, dict):
        raise ValueError("rootTopic 格式错误")
    return root


def _NormalizeCaseTitle(title: str) -> str:
    t = (title or "").strip().replace("\n", " ")
    t = re.sub(r"^tc-p0:", "tc-p1:", t, flags=re.IGNORECASE)
    m = re.match(r"^(tc(?:-p\d+)?:)(\S)", t, flags=re.IGNORECASE)
    if m:
        t = m.group(1) + " " + t[m.end(2) - 1 :]
    return t


def _IsTcTitle(title: str) -> bool:
    s = (title or "").strip()
    return bool(re.match(r"^tc(?:-p\d+)?:", s, flags=re.IGNORECASE))


def _ShouldSkipTopic(title: str) -> bool:
    t = (title or "").strip()
    if not t:
        return True
    if t in ("是", "否", "不适用"):
        return True
    if re.match(r"^细分主题\s*\d+$", t):
        return True
    return False


def _TopicAttached(node: dict[str, Any]) -> List[dict[str, Any]]:
    ch = node.get("children") or {}
    return list(ch.get("attached") or [])


def _OnlyMeaningfulTcChildren(attached: List[dict[str, Any]]) -> bool:
    meaningful: List[dict[str, Any]] = []
    for x in attached:
        t = (x.get("title") or "").strip()
        if _ShouldSkipTopic(t):
            continue
        meaningful.append(x)
    return bool(meaningful) and all(_IsTcTitle((x.get("title") or "").strip()) for x in meaningful)


def _IsPassThroughFolder(title: str, attached: List[dict[str, Any]]) -> bool:
    if not _OnlyMeaningfulTcChildren(attached):
        return False
    t = title.strip()
    if t in ("单品类", "非swap", "共享权益/充值权益"):
        return True
    tl = t.lower()
    # 仅穿透「swap」子文件夹，不把「SWAP映射」等章节误穿透
    if tl == "swap" or tl.startswith("swap （") or tl.startswith("swap（"):
        return True
    return False


def _MergeExpecteds(children: List[str]) -> str:
    parts = [c.strip() for c in children if c.strip()]
    if not parts:
        return "（待补充可验证预期）"
    s = parts[0] if len(parts) == 1 else "；".join(parts)
    return s.replace("。；", "；")


def _IsDataTopic(title: str) -> bool:
    t = (title or "").strip()
    return t == "数据" or t.startswith("数据")


_DEFAULT_DATA_LINES = (
    "apifox链接 ——（待补充）",
    "boss配置 ——（待补充）",
    "saas截图 ——（待补充）",
    "saas价格返回 ——（待补充）",
)


def _NormalizeDataLine(title: str) -> str:
    t = title.strip().replace("\n", " ")
    if not t:
        return ""
    if "——" in t or "—" in t or "--" in t:
        return t
    return f"{t} ——（待补充）"


def _EmitDataSection(data_node: dict[str, Any], lines: List[str]) -> None:
    """按脑图平级子主题导出：``- 数据`` + 缩进子项。"""
    lines.append("- 数据")
    subs = _TopicAttached(data_node)
    if not subs:
        for item in _DEFAULT_DATA_LINES:
            lines.append(f"  - {item}")
        return
    for sub in subs:
        text = _NormalizeDataLine(str(sub.get("title") or ""))
        if text:
            lines.append(f"  - {text}")


def _EmitCaseBody(
    attached: List[dict[str, Any]],
    lines: List[str],
) -> None:
    for ch in attached:
        if _ShouldSkipTopic(str(ch.get("title") or "")):
            continue
        title = (ch.get("title") or "").strip().replace("\n", " ")
        sub = (ch.get("children") or {}).get("attached") or []
        sub_titles = [(x.get("title") or "").strip().replace("\n", " ") for x in sub]
        sub_titles = [x for x in sub_titles if x and not _ShouldSkipTopic(x)]

        low = title.lower()
        if low.startswith("pc:"):
            lines.append(f"- {title}")
            continue
        if low.startswith("rc:") or low.startswith("tag:"):
            lines.append(f"- {title}")
            continue

        if _IsTcTitle(title):
            lines.append(f"- rc: 源脑图子节点误挂为步骤内用例标题，执行时请按独立用例看待：{_NormalizeCaseTitle(title)}")
            if sub_titles:
                lines.append(f"  - {_MergeExpecteds(sub_titles)}")
            continue

        if not sub_titles:
            lines.append(f"- {title}")
            continue

        lines.append(f"- {title}")
        lines.append(f"  - {_MergeExpecteds(sub_titles)}")


def _SanitizeModuleSegment(s: str) -> str:
    s = s.strip().replace("\n", " ")
    s = re.sub(r"\s+", "", s)
    return s


def ConvertToTestcasesMarkdown(
    root: dict[str, Any],
    xmind_path: str,
    requirement_doc: str | None = None,
) -> str:
    out: List[str] = []
    root_title = (root.get("title") or "").strip().replace("\n", " ") or "测试用例"
    out.append(f"# {_SanitizeModuleSegment(root_title)}")
    out.append("")
    out.append("## 测试范围说明")
    out.append("")
    if requirement_doc:
        out.append(
            f"- rc: 基于 `{requirement_doc}`；源脑图：`{xmind_path}`。"
        )
    else:
        out.append(
            f"- rc: 源脑图：`{xmind_path}`；结构与导入约定见 "
            f"`.cursor/skills/test-case-design-with-priority/reference.md` 第四节及仓库 "
            f"`testcases` Markdown 约定。"
        )
    out.append(
        "- rc: 若涉及接口，接口结构以 **Apifox/MCP 契约**为准；业务预期与错误码以需求及已确认规则为准；"
        "当前联调响应仅作验证证据，不得反向覆盖预期。"
    )
    out.append(
        "- rc: 历史 `tc-p0` 已按规范映射为 `tc-p1`；判定表碎片节点（是/否/不适用等）未写入本文件。"
    )
    out.append("")

    # 保留脑图模块嵌套：path[0]→H2、path[1]→H3…；用例标题紧随其后一层。
    # Markdown 实用上限 H6；更深模块仍写入但截断为 H6，用例同层继续用 H6。
    _MAX_HEADING = 6
    last_module_parts: List[str] = []

    def _HeadingPrefix(level: int) -> str:
        return "#" * max(1, min(level, _MAX_HEADING))

    def flush_module_path(parts: List[str]) -> None:
        nonlocal last_module_parts
        if not parts:
            parts = ["默认模块"]
        common = 0
        while (
            common < len(parts)
            and common < len(last_module_parts)
            and parts[common] == last_module_parts[common]
        ):
            common += 1
        for idx in range(common, len(parts)):
            # H1 为根标题，模块从 H2 起
            level = idx + 2
            out.append(f"{_HeadingPrefix(level)} {parts[idx]}")
            out.append("")
        last_module_parts = list(parts)

    def walk(node: dict[str, Any], path: List[str]) -> None:
        title_raw = (node.get("title") or "").strip().replace("\n", " ")
        if not title_raw or _ShouldSkipTopic(title_raw):
            for c in _TopicAttached(node):
                walk(c, path)
            return

        attached = _TopicAttached(node)

        if _IsTcTitle(title_raw):
            parts = [_SanitizeModuleSegment(p) for p in path if p.strip()]
            flush_module_path(parts)
            case_title = _NormalizeCaseTitle(title_raw)
            case_level = (len(parts) if parts else 1) + 2
            out.append(f"{_HeadingPrefix(case_level)} {case_title}")
            out.append("")
            data_nodes = [c for c in attached if _IsDataTopic(str(c.get("title") or ""))]
            body_nodes = [c for c in attached if not _IsDataTopic(str(c.get("title") or ""))]
            _EmitCaseBody(body_nodes, out)
            if data_nodes:
                _EmitDataSection(data_nodes[0], out)
            out.append("")
            return

        if _IsPassThroughFolder(title_raw, attached):
            for c in attached:
                walk(c, path)
            return

        for c in attached:
            walk(c, path + [title_raw])

    for c in _TopicAttached(root):
        walk(c, [])

    text = "\n".join(out).rstrip() + "\n"
    text = text.replace("目标ProgramSWAP", "目标Program的SWAP")
    text = text.replace("ProgramSWAP", "Program的SWAP")
    return text


def Main() -> None:
    parser = argparse.ArgumentParser(
        description="XMind Zen → testcases 可导入 Markdown（仅导出 tc-p* / tc: 用例节点）"
    )
    parser.add_argument(
        "--xmind",
        type=Path,
        required=True,
        help="输入 .xmind 文件路径",
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="输出 Markdown 路径（如 testcases/2026Q2SP4/PAPI-xxxx-测试用例-001.md）",
    )
    parser.add_argument(
        "--requirement",
        type=str,
        default=None,
        help="需求文档仓库内路径，写入测试范围说明（如 requirements/2026Q2SP4/PAPI-xxxx.md）",
    )
    args = parser.parse_args()
    if not args.xmind.is_file():
        raise FileNotFoundError(f"未找到 XMind 文件：{args.xmind}")
    root = _LoadRootFromXmind(args.xmind)
    md = ConvertToTestcasesMarkdown(
        root,
        str(args.xmind.resolve()),
        requirement_doc=args.requirement,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(md, encoding="utf-8")
    print("written", args.out, "chars", len(md))


if __name__ == "__main__":
    Main()
