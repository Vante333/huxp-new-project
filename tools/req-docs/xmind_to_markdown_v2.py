"""
XMind（content.json / .xmind）→ Markdown 测试用例。

默认（无参数）：读取同目录下 xmind_content.json，输出仓库根目录 testcases/2026Q1_SP3-测试用例.md。

指定输入输出示例：
  python tools/req-docs/xmind_to_markdown_v2.py -i path/to/file.xmind -o testcases/2026Q2_SP1/out.md
  python tools/req-docs/xmind_to_markdown_v2.py -i path/to/content.json -o testcases/out.md
"""

from __future__ import annotations

import argparse
import html
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

JsonData = List[Dict[str, Any]]


def GetRepoRoot() -> Path:
    return Path(__file__).resolve().parents[2]


def LoadMindData(input_path: Path) -> JsonData:
    """从 .xmind（ZIP）或 content.json 加载 XMind 数据。"""
    if not input_path.is_file():
        raise FileNotFoundError(f"输入文件不存在: {input_path}")
    suffix = input_path.suffix.lower()
    if suffix == ".xmind":
        with zipfile.ZipFile(input_path, "r") as zf:
            names = zf.namelist()
            if "content.json" not in names:
                raise FileNotFoundError(f"{input_path} 内缺少 content.json，当前条目: {names[:15]}")
            raw = zf.read("content.json").decode("utf-8")
        return json.loads(raw)
    if suffix == ".json":
        text = input_path.read_text(encoding="utf-8")
        return json.loads(text)
    raise ValueError(f"不支持的输入类型: {suffix}（请使用 .xmind 或 .json）")


def get_children(topic: Dict[str, Any]) -> List[Dict[str, Any]]:
    return topic.get("children", {}).get("attached", [])


def clean_title(title: str) -> str:
    return title.replace("\n", " ").strip()


def get_topic_title(topic: Dict[str, Any]) -> str:
    """兼容 XMind attributedTitle 与普通 title。"""
    if "attributedTitle" in topic:
        raw = "".join(str(s.get("text", "")) for s in topic["attributedTitle"])
    else:
        raw = str(topic.get("title", ""))
    return clean_title(raw)


def GetTopicNotesPlain(topic: Dict[str, Any]) -> str:
    """读取主题笔记（plain），去掉简易 HTML。"""
    notes = topic.get("notes") or {}
    plain = (notes.get("plain") or {}).get("content") or ""
    if not plain:
        return ""
    s = str(plain).replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.DOTALL)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()


def is_url(text: str) -> bool:
    return text.strip().startswith("http")


def extract_priority(title: str) -> Optional[int]:
    match = re.search(r"(?i)tc-p(\d)", title)
    if match:
        return int(match.group(1))
    return None


def is_result_marker(title: str) -> bool:
    t = title.strip()
    return bool(re.match(r"(?i)tc-p\d[:：]\s*预期结果", t)) or t == "预期结果" or t.startswith(
        "预期结果"
    )


def is_tc_node(title: str) -> bool:
    return bool(re.search(r"(?i)tc-p\d", title)) and not is_result_marker(title)


def IsProbablyMarkdownTable(block: str) -> bool:
    lines = [x.strip() for x in block.strip().split("\n") if x.strip()]
    return len(lines) >= 2 and "|" in lines[0] and "---" in lines[1]


def strip_tc_prefix(text: str) -> str:
    return re.sub(r"(?i)^tc-p\d[:：]\s*", "", text).strip()


def PreorderResultLines(topic: Dict[str, Any]) -> List[str]:
    """前序展开子主题标题，保留多层步骤（如 SQL、示例订单号）。"""
    t = get_topic_title(topic)
    if is_url(t):
        return []
    line = strip_tc_prefix(t) if t else ""
    if not line:
        return []
    children = get_children(topic)
    if not children:
        return [line]
    parts: List[str] = [line]
    for c in children:
        parts.extend(PreorderResultLines(c))
    return [p for p in parts if p and not is_url(p)]


def collect_all_results(topic: Dict[str, Any]) -> List[str]:
    """收集用例节点下所有步骤行（前序遍历，兼容表格笔记 + 深层子节点）。"""
    out: List[str] = []
    for child in get_children(topic):
        out.extend(PreorderResultLines(child))
    return [r for r in out if r and not is_url(r)]


def derive_module_abbr(title: str) -> str:
    t = title.lower()
    if "membership" in t or "充点" in t or "权益支持" in title:
        return "MBR"
    elif "搜索" in title and "聚合" in title:
        return "SEARCH"
    elif "premium" in t or "等级打标" in title:
        return "TIER"
    elif "e-pass" in t or "epass" in t:
        return "EPASS"
    elif "migration" in t or "order list" in t:
        return "ORDER"
    elif "可用资源" in title:
        return "RES"
    return "GEN"


def derive_sub_abbr(title: str, parent_abbr: str) -> Optional[str]:
    t = title.lower()
    mappings = [
        ("lounge", "LNG"),
        ("esim", "ESIM"),
        ("setmeal", "SET"),
        ("套餐", "SET"),
        ("coupon", "CPN"),
        ("fitness", "FIT"),
        ("编辑权益", "UPD"),
        ("entitlements/update", "UPD"),
        ("权益查询", "QRY"),
        ("entitlements/search", "QRY"),
        ("充值流程", "RCH"),
        ("充值", "RCH"),
        ("会籍模板", "TPL"),
        ("会籍注册", "REG"),
        ("registration", "REG"),
        ("订单", "ORD"),
        ("order", "ORD"),
        ("预览", "PRV"),
        ("preview", "PRV"),
        ("预订", "PBK"),
        ("prebooking", "PBK"),
        ("可用性", "AVL"),
        ("availability", "AVL"),
        ("价格", "PRC"),
        ("price", "PRC"),
        ("告警", "ALT"),
        ("缓存", "CACHE"),
        ("搜索", "SCH"),
        ("资源", "RES"),
        ("模板", "TPL"),
        ("参数", "PARAM"),
        ("数值", "VAL"),
        ("共享", "SHARE"),
        ("状态", "STS"),
        ("删除", "DEL"),
        ("修改", "MOD"),
    ]

    for keyword, abbr in mappings:
        if keyword in t:
            return abbr

    if "ft" == t.strip():
        return "FT"

    return None


class TestCase:
    def __init__(
        self,
        priority: Optional[int],
        scenario: str,
        results: List[str],
        context_path: List[str],
    ) -> None:
        self.priority: Optional[int] = priority
        self.scenario: str = scenario
        self.results: List[str] = results
        self.context_path: List[str] = context_path


class MarkdownGeneratorV2:
    def __init__(self) -> None:
        self.lines: List[str] = []
        self.all_test_cases: List[TestCase] = []

    def collect_test_cases(self, topic: Dict[str, Any], path: List[str]) -> None:
        """Recursively collect all test cases with their context paths."""
        title = get_topic_title(topic)
        children = get_children(topic)

        if not title or title == "子主题 1":
            return

        if title.startswith("子主题") and title not in ("子主题 1",) and not children:
            return

        if is_tc_node(title):
            priority = extract_priority(title)
            scenario = strip_tc_prefix(title)
            if not scenario:
                scenario = title
            results = collect_all_results(topic)
            notes = GetTopicNotesPlain(topic)
            if notes:
                results = [notes] + results
            self.all_test_cases.append(TestCase(priority, scenario, results, list(path)))
            return

        has_result_child = any(is_result_marker(get_topic_title(c)) for c in children)
        if has_result_child:
            priority = extract_priority(title)
            result_child = next(
                c for c in children if is_result_marker(get_topic_title(c))
            )
            if priority is None:
                priority = extract_priority(get_topic_title(result_child))
            if priority is None:
                priority = 1
            scenario = strip_tc_prefix(title)
            if not scenario:
                scenario = title

            results: List[str] = []
            for child in children:
                ct = get_topic_title(child)
                if is_url(ct):
                    continue
                if is_result_marker(ct):
                    for sub in get_children(child):
                        st = get_topic_title(sub)
                        if not is_url(st):
                            results.append(strip_tc_prefix(st))
                            for ssub in get_children(sub):
                                sst = get_topic_title(ssub)
                                if not is_url(sst):
                                    results.append(strip_tc_prefix(sst))
                else:
                    results.append(strip_tc_prefix(ct))

            results = [r for r in results if r and not is_url(r)]
            notes = GetTopicNotesPlain(topic)
            if notes:
                results = [notes] + results
            self.all_test_cases.append(TestCase(priority, scenario, results, list(path)))
            return

        new_path = path + [title]
        for child in children:
            self.collect_test_cases(child, new_path)

    def generate(self, data: JsonData) -> str:
        root = data[0]["rootTopic"]
        root_title = get_topic_title(root)

        d1_children = get_children(root)

        for d1 in d1_children:
            d1_title = get_topic_title(d1)
            if not d1_title or d1_title == "子主题 1":
                continue

            module_abbr = derive_module_abbr(d1_title)
            self.all_test_cases = []
            self.collect_test_cases(d1, [d1_title])

            if not self.all_test_cases:
                continue

            grouped = self.group_test_cases(d1_title)
            self.emit_section(root_title, d1_title, module_abbr, grouped)

        return "\n".join(self.lines)

    def group_test_cases(self, h2_title: str) -> Dict[str, Dict[str, List[TestCase]]]:
        groups: Dict[str, Dict[str, List[TestCase]]] = {}
        for tc in self.all_test_cases:
            path = tc.context_path

            effective_path = [p for p in path if p != h2_title]
            if not effective_path:
                effective_path = ["通用验证"]

            if len(effective_path) >= 2:
                h3_key = effective_path[0]
                h4_key = effective_path[1]
            elif len(effective_path) == 1:
                h3_key = effective_path[0]
                h4_key = ""
            else:
                h3_key = "通用验证"
                h4_key = ""

            if h3_key not in groups:
                groups[h3_key] = {}
            if h4_key not in groups[h3_key]:
                groups[h3_key][h4_key] = []
            groups[h3_key][h4_key].append(tc)

        return groups

    def emit_section(
        self, root_title: str, h2_title: str, module_abbr: str, grouped: Dict[str, Any]
    ) -> None:
        if not self.lines:
            h1 = root_title.rstrip()
            if not h1.endswith("测试用例"):
                h1 = f"{h1} 测试用例"
            self.lines.append(f"# {h1}")
            self.lines.append("")

        self.lines.append(f"## {h2_title}")
        self.lines.append("")

        tc_counter: Dict[str, int] = {}

        for h3_title, h4_groups in grouped.items():
            h3_display = strip_tc_prefix(h3_title)
            if not h3_display or is_url(h3_display):
                continue

            self.lines.append(f"### {h3_display}")
            self.lines.append("")

            sub_abbr = derive_sub_abbr(h3_title, module_abbr)
            h3_abbr = f"{module_abbr}-{sub_abbr}" if sub_abbr else module_abbr

            for h4_title, test_cases in h4_groups.items():
                if h4_title:
                    h4_display = strip_tc_prefix(h4_title)
                    if h4_display and not is_url(h4_display):
                        self.lines.append(f"#### {h4_display}")
                        self.lines.append("")
                        h4_sub = derive_sub_abbr(h4_title, h3_abbr)
                        tc_abbr = (
                            f"{h3_abbr}-{h4_sub}"
                            if h4_sub and h4_sub != sub_abbr
                            else h3_abbr
                        )
                    else:
                        tc_abbr = h3_abbr
                else:
                    tc_abbr = h3_abbr

                parts = tc_abbr.split("-")
                if len(parts) > 3:
                    seen: List[str] = []
                    for p in parts:
                        if p not in seen:
                            seen.append(p)
                    tc_abbr = "-".join(seen[:3])

                for tc in test_cases:
                    p = tc.priority if tc.priority is not None else 1
                    counter_key = f"P{p}-{tc_abbr}"
                    if counter_key not in tc_counter:
                        tc_counter[counter_key] = 0
                    tc_counter[counter_key] += 1
                    tc_id = f"tc-P{p}-{tc_abbr}-{tc_counter[counter_key]:03d}"

                    self.lines.append(f"##### {tc_id}：{tc.scenario}")
                    self.lines.append("")

                    if tc.results:
                        for r in tc.results:
                            if not r or is_url(r):
                                continue
                            if IsProbablyMarkdownTable(r):
                                for tbl_line in r.strip().split("\n"):
                                    tl = tbl_line.strip()
                                    if tl:
                                        self.lines.append(tl)
                                self.lines.append("")
                            else:
                                self.lines.append(f"- tc-P{p}: {r}")

                    self.lines.append("")


def ParseArgs() -> argparse.Namespace:
    repo = GetRepoRoot()
    default_in = Path(__file__).resolve().parent / "xmind_content.json"
    default_out = repo / "testcases" / "2026Q1_SP3-测试用例.md"
    parser = argparse.ArgumentParser(
        description="将 XMind（.xmind 或 content.json）转为 Markdown 测试用例"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=default_in,
        help=f"输入文件（默认: {default_in})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=default_out,
        help=f"输出 .md 路径（默认: {default_out})",
    )
    return parser.parse_args()


def Main() -> None:
    args = ParseArgs()
    input_path: Path = args.input.expanduser().resolve()
    output_path: Path = args.output.expanduser()
    if not output_path.is_absolute():
        output_path = (GetRepoRoot() / output_path).resolve()
    else:
        output_path = output_path.resolve()

    data = LoadMindData(input_path)

    gen = MarkdownGeneratorV2()
    output = gen.generate(data)

    output = re.sub(r"\n{3,}", "\n\n", output)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"Total lines: {len(output.splitlines())}")

    tc_count = len(re.findall(r"^##### tc-", output, re.MULTILINE))
    p0_count = len(re.findall(r"^##### tc-P0", output, re.MULTILINE))
    p1_count = len(re.findall(r"^##### tc-P1", output, re.MULTILINE))
    p2_count = len(re.findall(r"^##### tc-P2", output, re.MULTILINE))
    p3_count = len(re.findall(r"^##### tc-P3", output, re.MULTILINE))
    total = p0_count + p1_count + p2_count + p3_count
    print(f"\nTotal test cases: {tc_count}")
    if total > 0:
        print(f"  P0: {p0_count} ({p0_count / total * 100:.1f}%)")
        print(f"  P1: {p1_count} ({p1_count / total * 100:.1f}%)")
        print(f"  P2: {p2_count} ({p2_count / total * 100:.1f}%)")
        print(f"  P3: {p3_count} ({p3_count / total * 100:.1f}%)")

    long_ids = re.findall(r"##### (tc-[^\s：]+)", output)
    max_len = max(len(x) for x in long_ids) if long_ids else 0
    long_ones = [x for x in long_ids if len(x) > 30]
    if long_ones:
        print(f"\nWarning: {len(long_ones)} IDs longer than 30 chars (max: {max_len})")
        for x in long_ones[:5]:
            print(f"  {x}")


if __name__ == "__main__":
    Main()
