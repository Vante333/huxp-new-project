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


_URL_ONLY_RE = re.compile(
    r'^[\"\u201c\u201d\'\']?\s*(/v2/\S+?)\s*[\"\u201c\u201d\'\']?\s*$'
)


def _IsUrlOnlySegment(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if s.startswith("/v2/"):
        return True
    if _URL_ONLY_RE.match(s):
        return True
    return False


def _TopicDisplayTitle(title: str) -> str:
    """取首行非 URL 文本作为模块/列表显示名（去掉脑图第二行单独路径）。"""
    raw = title.replace("\r\n", "\n").strip()
    if not raw:
        return raw
    parts = [p.strip() for p in raw.split("\n") if p.strip()]
    if not parts:
        return raw
    for part in parts:
        if not _IsUrlOnlySegment(part):
            return part
    return parts[0]


def _TopicBodyLines(title: str) -> List[str]:
    """多行标题中除显示名外、且非单独 URL 的续行。"""
    raw = title.replace("\r\n", "\n").strip()
    parts = [p.rstrip() for p in raw.split("\n")]
    if len(parts) <= 1:
        return []
    display = _TopicDisplayTitle(title)
    rest: List[str] = []
    seen_display = False
    for part in parts:
        s = part.strip()
        if not s or _IsUrlOnlySegment(s):
            continue
        if not seen_display and s == display.strip():
            seen_display = True
            continue
        rest.append(part.rstrip())
    return rest


def _NormalizeTcPrefix(text: str) -> str:
    text = re.sub(r"(?i)\btc-p0:", "tc-p1:", text)
    text = re.sub(r"(?i)\btc-p1:", "tc-p1:", text)
    text = re.sub(r"(?i)\btc-p2:", "tc-p2:", text)
    text = re.sub(r"(?i)\btc-p3:", "tc-p3:", text)
    text = re.sub(r"(?i)\btc-p([123]):(?! )", r"tc-p\1: ", text)
    return text


def _EnsureLineTcPrefixSpacing(line: str) -> str:
    def _Sp(m: re.Match[str]) -> str:
        pri = m.group(2).lower()
        return f"{m.group(1)}tc-p{pri}: {m.group(3)}"

    line = re.sub(r"^(\s*- )tc-p([123]):(?!\s)(.*)$", _Sp, line, flags=re.IGNORECASE)
    line = re.sub(r"^(#{3,6} )tc-p([123]):(?!\s)(.*)$", _Sp, line, flags=re.IGNORECASE)
    return line


def _DefaultExpectedForTcTitle(title: str) -> str:
    t = re.sub(r"(?i)^tc-p[123]:\s*", "", title).strip()
    if not t:
        return "结果与 Apifox 及脑图描述一致"
    if "null" in t.lower() or t.endswith(" null"):
        return "为 null"
    if "orderId" in t or "订单id" in t:
        return "非空且为系统生成的有效订单标识"
    if "orderCreatedDate" in t or "创建日期" in t or "创建时间" in t:
        return "为订单创建时间，格式与 Apifox 一致"
    if t.startswith("clientUserId") or "传入的字段" in t:
        return "与入参传入值一致"
    if re.match(r"^(ePassId|ePassStatus|firstName|lastName|activationDate|expirationDate|availableUsages)$", t, re.I):
        return "字段存在且取值与 Apifox/数据结构定义一致"
    return "结果与 Apifox 及脑图描述一致"


_V2_API_PATH_RE = re.compile(r"/v2/[\w./{}-]+")
_V2_API_PATH_NO_LEAD_RE = re.compile(r"(?<![\w/.-])v2/[\w./{}-]+")


def _ApiPathToUnderscoreSlug(path: str) -> str:
    slug = path.lstrip("/").replace("/", "_")
    return re.sub(r"[{}]", "", slug)


def _ReplaceV2PathSlashes(line: str) -> str:
    """将正文/步骤中的 ``/v2/...`` 或 ``v2/...`` 转为 ``v2_...``（规范 §4.2）。"""
    line = _V2_API_PATH_RE.sub(lambda m: _ApiPathToUnderscoreSlug(m.group(0)), line)
    return _V2_API_PATH_NO_LEAD_RE.sub(lambda m: _ApiPathToUnderscoreSlug(m.group(0)), line)


_TC_TITLE_RE = re.compile(r"^tc-p[123]:", re.I)
_ERROR_CODE_RE = re.compile(r"^\d{3}\.\d{3}\.\d{3}\b")
_ERROR_CODE_FIND_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}\b")
_LIST_ITEM_RE = re.compile(r"^(\s*)- (.+)$")
_EXPECTED_OUTCOME_RE = re.compile(
    r"^(返回|弹出合理提示|不可通过|可以通过|下单成功|不生成订单|返回错误码|状态为)"
)

_GROUP_SECTION_HEADERS = frozenset(
    {
        "错误码",
        "入参校验",
        "参数校验",
        "返回校验",
        "返回响应",
        "业务逻辑",
        "出参特殊校验",
        "预约人数",
        "extra",
        "Path",
        "body",
        "async",
        "allowedResources",
        "resourceIds",
        "countryOrRegion",
        "iata",
        "ePassStatus",
        "其他字段",
        "与数据结构一致",
        "预约成功",
        "data",
        "pagination",
        "orders",
        "status",
        "localOfferOptions",
        "Cancel an Order",
    }
)


def _ListItemParts(line: str) -> Optional[tuple[int, str, str]]:
    m = _LIST_ITEM_RE.match(line)
    if not m:
        return None
    return len(m.group(1)), m.group(1), m.group(2).strip()


def _HasTcPrefix(title: str) -> bool:
    return bool(_TC_TITLE_RE.match(title.strip()))


def _FirstChildBody(lines: List[str], index: int, parent_indent: int) -> Optional[str]:
    j = index + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return None
    parts = _ListItemParts(lines[j])
    if not parts or parts[0] != parent_indent + 2:
        return None
    return parts[2]


def _LooksLikeExpectedOutcome(text: str) -> bool:
    t = text.strip()
    if _ERROR_CODE_RE.match(t):
        return True
    if _HasTcPrefix(t) and _ERROR_CODE_FIND_RE.search(t):
        return True
    return bool(_EXPECTED_OUTCOME_RE.match(t)) or "500." in t


def _CopyDescendantLines(
    lines: List[str], start: int, parent_indent: int, skip_first: int
) -> tuple[List[str], int]:
    """从 ``start+skip_first`` 起复制更深缩进子行，返回 (子行, 下一未处理索引)。"""
    copied: List[str] = []
    j = start + skip_first
    while j < len(lines):
        nxt = lines[j]
        if not nxt.strip():
            copied.append(nxt)
            j += 1
            continue
        nxt_parts = _ListItemParts(nxt)
        if not nxt_parts or nxt_parts[0] <= parent_indent:
            break
        copied.append(nxt)
        j += 1
    return copied, j


def _AutoTagMissingTcPrefix(lines: List[str]) -> List[str]:
    """为 ``错误码`` 节及同类叶节点场景补 ``tc-p1:`` 标识（与脑图已有用例写法对齐）。"""
    out: List[str] = []
    section: Optional[str] = None
    section_indent = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        if line.startswith("###"):
            section = None
            out.append(line)
            i += 1
            continue

        parts = _ListItemParts(line)
        if not parts:
            out.append(line)
            i += 1
            continue

        indent_len, indent, body = parts

        if body in _GROUP_SECTION_HEADERS and body in ("错误码", "入参校验", "参数校验"):
            section = body
            section_indent = indent_len
            out.append(line)
            i += 1
            continue

        if section and indent_len <= section_indent and body not in ("错误码", "入参校验", "参数校验"):
            section = None

        if _HasTcPrefix(body):
            out.append(line)
            i += 1
            continue

        if body in _GROUP_SECTION_HEADERS:
            out.append(line)
            i += 1
            continue

        child = _FirstChildBody(lines, i, indent_len)

        if child and _HasTcPrefix(child) and _ERROR_CODE_FIND_RE.search(child):
            code = _ERROR_CODE_FIND_RE.search(child)
            code_text = code.group(0) if code else child
            out.append(f"{indent}- tc-p1: {body}")
            out.append(f"{' ' * (indent_len + 2)}- {code_text}")
            descendants, i = _CopyDescendantLines(lines, i, indent_len, skip_first=1)
            for d in descendants:
                d_parts = _ListItemParts(d)
                if d_parts and d_parts[0] == indent_len + 2 and _HasTcPrefix(d_parts[2]):
                    continue
                out.append(d)
            continue

        should_tag = False
        if section == "错误码" and indent_len == section_indent + 2:
            should_tag = child is not None and (
                _ERROR_CODE_RE.match(child) or _LooksLikeExpectedOutcome(child)
            )
        elif section in ("入参校验", "参数校验") and indent_len == section_indent + 2:
            should_tag = child is not None and _LooksLikeExpectedOutcome(child)

        if should_tag:
            out.append(f"{indent}- tc-p1: {body}")
        else:
            out.append(line)
        i += 1

    return out


def FormatMarkdownTreeCompliance(text: str) -> str:
    """在不改变树形层级的前提下，对齐 test-case-design-with-priority 导入格式。"""
    lines = _AutoTagMissingTcPrefix(text.splitlines())
    pass1: List[str] = []
    i = 0
    while i < len(lines):
        line = _EnsureLineTcPrefixSpacing(lines[i])
        m_tag = re.match(r"^(\s+)tag:(.*)$", line)
        if m_tag and "- tag:" not in line.strip():
            line = f"{m_tag.group(1)}- tag:{m_tag.group(2)}"
        m_tc = re.match(r"^(\s*)- tc-p[123]:", line, re.I)
        if m_tc and i + 1 < len(lines):
            ind = len(m_tc.group(1))
            nxt = lines[i + 1]
            m_child = re.match(r"^(\s*)- tc-p[123]:\s*(.*)$", nxt, re.I)
            if m_child and len(m_child.group(1)) == ind + 2:
                pass1.append(line)
                pass1.append(f"{' ' * (ind + 2)}- {m_child.group(2).strip()}")
                i += 2
                continue
        pass1.append(line)
        i += 1

    out: List[str] = []
    for idx, line in enumerate(pass1):
        out.append(line)
        m = re.match(r"^(\s*)- tc-p[123]:", line, re.I)
        if not m:
            continue
        ind = len(m.group(1))
        has_child = False
        for j in range(idx + 1, len(pass1)):
            if not pass1[j].strip():
                continue
            ni = len(pass1[j]) - len(pass1[j].lstrip())
            if ni <= ind:
                break
            if ni == ind + 2 and pass1[j].lstrip().startswith("- "):
                has_child = True
                break
        if not has_child:
            m_title = re.search(r"tc-p[123]:\s*(.*)$", line, re.IGNORECASE)
            exp = _DefaultExpectedForTcTitle(m_title.group(1) if m_title else line)
            out.append(f"{' ' * (ind + 2)}- {exp}")

    final = [_ReplaceV2PathSlashes(line) for line in out]
    result = "\n".join(final)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.rstrip() + "\n"


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
            lines.append(_NormalizeTcPrefix(t if t[:3].lower() == "pc:" else f"pc: {t}"))
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
            _AppendListItemLines(lines, 0, t)
            continue
        kind = _LastNonEmptyLineKind(lines)
        if kind in ("expect", "lone", "table"):
            lines.append("")
        if len(sub) == 1:
            exp = GetTopicTitle(sub[0])
            _AppendListItemLines(lines, 0, t)
            _AppendListItemLines(lines, 1, exp)
        else:
            _AppendListItemLines(lines, 0, t)
            for s in sub:
                st = GetTopicTitle(s)
                if st.strip():
                    _AppendListItemLines(lines, 1, st)
    lines.append("")


def _AppendListItemLines(lines: List[str], indent: int, text: str) -> None:
    """将主题标题写入 Markdown 列表；多行标题保持为同一列表项的续行（跳过单独 URL 行）。"""
    display = _TopicDisplayTitle(text)
    if not display:
        return
    parts = [_NormalizeTcPrefix(display)] + [_NormalizeTcPrefix(p) for p in _TopicBodyLines(text)]
    bullet = "  " * indent + "- "
    cont = "  " * indent + "  "
    lines.append(f"{bullet}{parts[0]}")
    for part in parts[1:]:
        if part.strip():
            lines.append(f"{cont}{part.rstrip()}")
        else:
            lines.append("")


def _SanitizeModuleDisplayName(title: str) -> str:
    """模块显示名：去掉引号内/内联 ``/v2/`` 路径；纯路径转为 ``v2_...`` 模块名（规范 §4.2）。"""
    raw = _TopicDisplayTitle(title).replace("\r\n", " ").strip()
    if not raw:
        return raw
    m = re.match(
        r'^(.+?)\s*["\u201c\u201d\']((?:/v2/)[^"\u201c\u201d\']+)["\u201c\u201d\']?\s*$',
        raw,
    )
    if m:
        return m.group(1).strip()
    m2 = re.search(r"/v2/", raw)
    if m2:
        head = raw[: m2.start()].rstrip(" -/\t").strip()
        if head:
            return head
    path_like = raw.strip("\"'\u201c\u201d ")
    if path_like.startswith("/v2/"):
        return _ApiPathToUnderscoreSlug(path_like)
    return raw


def _EmitModuleChildren(lines: List[str], topic: Dict[str, Any], indent: int) -> None:
    """展开模块子节点，不再重复输出与 ``###`` 同名的根列表项。"""
    for child in (topic.get("children") or {}).get("attached") or []:
        _EmitFreeformTopic(lines, child, indent)


def _EmitFreeformTopic(lines: List[str], topic: Dict[str, Any], indent: int) -> None:
    t = GetTopicTitle(topic)
    children = (topic.get("children") or {}).get("attached") or []
    if not t.strip():
        for c in children:
            _EmitFreeformTopic(lines, c, indent)
        return
    _AppendListItemLines(lines, indent, t)
    for c in children:
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
            raw_nt = GetTopicTitle(node)
            nt = _SanitizeModuleDisplayName(raw_nt)
            if not IsTcHeader(nt):
                lines.append(f"### {_NormalizeTcPrefix(nt)}")
                lines.append("")
                _EmitModuleChildren(lines, node, indent=0)
                continue
            lines.append(f"### {_NormalizeTcPrefix(nt)}")
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
    md = FormatMarkdownTreeCompliance(md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md.replace("\r\n", "\n"), encoding="utf-8")


if __name__ == "__main__":
    Main()
