from __future__ import annotations

"""XMind（tc-p* / tc: 节点）→ testcases 可导入 Markdown。

用法（仓库根目录）：
  python tools/xmind_to_testcases_md.py \\
    --xmind path/to/file.xmind \\
    --out testcases/2026Q2SP4/PAPI-xxxx-测试用例-001.md \\
    --requirement requirements/2026Q2SP4/PAPI-xxxx.md

仅导出脑图中 tc 用例节点；判定表等未挂 tc 子树的内容不会写入输出。
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
        "- rc: 接口路径、错误码、主数据以 **Apifox/MCP** 与当前联调环境为准。"
    )
    out.append(
        "- rc: 历史 `tc-p0` 已按规范映射为 `tc-p1`；判定表碎片节点（是/否/不适用等）未写入本文件。"
    )
    out.append("")

    last_h2: str | None = None

    def flush_h2(name: str) -> None:
        nonlocal last_h2
        if name == last_h2:
            return
        out.append(f"## {name}")
        out.append("")
        last_h2 = name

    def walk(node: dict[str, Any], path: List[str]) -> None:
        title_raw = (node.get("title") or "").strip().replace("\n", " ")
        if not title_raw or _ShouldSkipTopic(title_raw):
            for c in _TopicAttached(node):
                walk(c, path)
            return

        attached = _TopicAttached(node)

        if _IsTcTitle(title_raw):
            parts = [_SanitizeModuleSegment(p) for p in path if p.strip()]
            h2 = "-".join(parts) if parts else "默认模块"
            flush_h2(h2)
            case_title = _NormalizeCaseTitle(title_raw)
            out.append(f"### {case_title}")
            out.append("")
            _EmitCaseBody(attached, out)
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
