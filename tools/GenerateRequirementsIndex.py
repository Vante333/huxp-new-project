"""
扫描 requirements/ 下各迭代子目录，解析需求 Markdown 的首个一级标题与 JIRA 键，
并写回各 README 中 HTML 注释标记块内的表格（幂等、可重复运行）。

用法（仓库根目录）::

    python tools/GenerateRequirementsIndex.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import quote

_REPO_ROOT: Path = Path(__file__).resolve().parent.parent
_REQUIREMENTS_ROOT: Path = _REPO_ROOT / "requirements"

_MARK_GLOBAL_START: str = "<!-- REQ_GLOBAL_INDEX_START -->"
_MARK_GLOBAL_END: str = "<!-- REQ_GLOBAL_INDEX_END -->"
_MARK_SPRINT_START: str = "<!-- REQ_INDEX_START -->"
_MARK_SPRINT_END: str = "<!-- REQ_INDEX_END -->"

_READ_CHUNK: int = 96 * 1024
_JIRA_BASE: str = "https://dragonpass.atlassian.net/browse/"
_H1_PATTERN: re.Pattern[str] = re.compile(r"^#\s+(.+?)\s*$")
_JIRA_KEY_PATTERN: re.Pattern[str] = re.compile(r"\b(PAPI-\d+)\b", re.IGNORECASE)


def RepoRoot() -> Path:
    return _REPO_ROOT


def RequirementsRoot() -> Path:
    return _REQUIREMENTS_ROOT


def UrlEncodeRelativeSegment(segment: str) -> str:
    """将路径段编码为可用于 Markdown 相对链接的形式（如空格 -> %20）。"""
    return quote(segment, safe="")


def ReadMarkdownPreview(path: Path) -> Tuple[Optional[str], str]:
    """
    读取文件前若干字节为 UTF-8 文本。

    返回 (None, "") 表示跳过（编码错误或读失败）；第二个元素为成功时的正文预览。
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        print(f"[WARN] 无法读取 {path}: {exc}", file=sys.stderr)
        return None, ""
    chunk = raw[:_READ_CHUNK]
    try:
        text = chunk.decode("utf-8")
    except UnicodeDecodeError:
        print(
            f"[WARN] 跳过非 UTF-8 或含非法序列的文件: {path}",
            file=sys.stderr,
        )
        return None, ""
    return "ok", text


def ExtractFirstH1FromText(text: str, fallback_stem: str) -> str:
    for line in text.splitlines():
        m = _H1_PATTERN.match(line)
        if m:
            return m.group(1).strip()
    return fallback_stem


def ExtractJiraKey(text: str) -> Optional[str]:
    m = _JIRA_KEY_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(1)
    upper = raw.upper()
    if upper.startswith("PAPI-"):
        return upper
    return raw


def EscapeTableCell(value: str) -> str:
    s = " ".join(value.split())
    return s.replace("|", "\\|")


def ListSprintDirectories(requirements_root: Path) -> List[Path]:
    if not requirements_root.is_dir():
        raise FileNotFoundError(f"requirements 目录不存在: {requirements_root}")
    out: List[Path] = []
    for p in sorted(requirements_root.iterdir(), key=lambda x: x.name.lower()):
        if p.is_dir() and not p.name.startswith("."):
            out.append(p)
    return out


def ListRequirementMarkdownFiles(sprint_dir: Path) -> List[Path]:
    files = [p for p in sprint_dir.iterdir() if p.suffix.lower() == ".md" and p.is_file()]
    files = [p for p in files if p.name.lower() != "readme.md"]
    return sorted(files, key=lambda x: x.name.lower())


def BuildJiraColumn(jira_key: Optional[str]) -> str:
    if not jira_key:
        return "-"
    url = f"{_JIRA_BASE}{jira_key}"
    return f"[{jira_key}]({url})"


def BuildSprintIndexTableBody(rows: List[Tuple[str, str, str]]) -> str:
    lines = [
        "| 文档 | 标题 | JIRA |",
        "| --- | --- | --- |",
    ]
    for doc_link, title, jira_col in rows:
        lines.append(f"| {doc_link} | {title} | {jira_col} |")
    return "\n".join(lines)


def BuildGlobalIndexTableBody(sprint_stats: List[Tuple[str, int, str]]) -> str:
    lines = [
        "| 迭代 | 文档数 | 索引 |",
        "| --- | --- | --- |",
    ]
    for name, count, readme_link in sprint_stats:
        lines.append(f"| `{name}` | {count} | {readme_link} |")
    return "\n".join(lines)


def ReplaceMarkedSection(
    full_text: str,
    start_marker: str,
    end_marker: str,
    new_body: str,
) -> str:
    i_start = full_text.find(start_marker)
    i_end = full_text.find(end_marker)
    if i_start < 0 or i_end < 0 or i_end <= i_start:
        raise ValueError(
            f"未找到成对标记或顺序错误: {start_marker!r} … {end_marker!r}"
        )
    before_inclusive = full_text[: i_start + len(start_marker)]
    after_inclusive = full_text[i_end:]
    body = new_body.strip()
    return f"{before_inclusive}\n\n{body}\n\n{after_inclusive}"


def ScanSprintDirectory(sprint_dir: Path) -> List[Tuple[str, str, str]]:
    """返回表格行：(文档链接 Markdown, 转义后的标题, JIRA 列 Markdown)。"""
    rows: List[Tuple[str, str, str]] = []
    for md_path in ListRequirementMarkdownFiles(sprint_dir):
        status, preview = ReadMarkdownPreview(md_path)
        if status is None:
            continue
        title = ExtractFirstH1FromText(preview, md_path.stem)
        jira_key = ExtractJiraKey(preview)
        enc_name = UrlEncodeRelativeSegment(md_path.name)
        doc_link = f"[{md_path.name}](./{enc_name})"
        rows.append(
            (
                doc_link,
                EscapeTableCell(title) if title else EscapeTableCell(md_path.stem),
                BuildJiraColumn(jira_key),
            )
        )
    return rows


def SprintReadmePath(sprint_dir: Path) -> Path:
    return sprint_dir / "README.md"


def ProcessSprintReadme(sprint_dir: Path) -> Tuple[str, int]:
    readme_path = SprintReadmePath(sprint_dir)
    if not readme_path.is_file():
        raise FileNotFoundError(f"缺少迭代 README（请先创建）: {readme_path}")
    text = readme_path.read_text(encoding="utf-8")
    rows = ScanSprintDirectory(sprint_dir)
    body = BuildSprintIndexTableBody(rows)
    new_text = ReplaceMarkedSection(text, _MARK_SPRINT_START, _MARK_SPRINT_END, body)
    readme_path.write_text(new_text.replace("\r\n", "\n"), encoding="utf-8")
    return sprint_dir.name, len(rows)


def ProcessRootReadme(
    requirements_root: Path,
    sprint_stats: List[Tuple[str, int, str]],
) -> None:
    root_readme = requirements_root / "README.md"
    if not root_readme.is_file():
        raise FileNotFoundError(f"缺少 requirements/README.md: {root_readme}")
    text = root_readme.read_text(encoding="utf-8")
    body = BuildGlobalIndexTableBody(sprint_stats)
    new_text = ReplaceMarkedSection(text, _MARK_GLOBAL_START, _MARK_GLOBAL_END, body)
    root_readme.write_text(new_text.replace("\r\n", "\n"), encoding="utf-8")


def Main() -> None:
    req_root = RequirementsRoot()
    sprints = ListSprintDirectories(req_root)
    sprint_stats: List[Tuple[str, int, str]] = []
    for sprint_dir in sprints:
        name, count = ProcessSprintReadme(sprint_dir)
        enc = UrlEncodeRelativeSegment(sprint_dir.name)
        readme_link = f"[README](./{enc}/README.md)"
        sprint_stats.append((name, count, readme_link))
    ProcessRootReadme(req_root, sprint_stats)
    print(
        f"已更新 {len(sprint_stats)} 个迭代 README 与 requirements/README.md 中的索引表。",
        file=sys.stderr,
    )


if __name__ == "__main__":
    try:
        Main()
    except (OSError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
