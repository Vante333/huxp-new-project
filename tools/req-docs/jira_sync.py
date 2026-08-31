"""
Jira 需求同步工具：从 Jira Cloud 拉取 Issue 描述并导出为 Markdown，支持图片下载与本地路径替换。

用法:
    # 同步单个 Issue，输出到指定文件
    python jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/entilement.md

    # 使用配置文件批量同步
    python jira_sync.py --config jira_sync_config.yaml

    # 仅指定输出目录（按 Issue Key 自动命名）
    python jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/

环境变量:
    JIRA_BASE_URL   Jira 站点地址，默认 https://dragonpass.atlassian.net
    JIRA_EMAIL      登录邮箱（API Token 所属账号）
    JIRA_API_TOKEN  Jira API Token（Atlassian 账户设置中创建）

依赖: pip install requests
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_JIRA_BASE = "https://dragonpass.atlassian.net"


def _load_dotenv() -> None:
    """从项目根目录的 .env 文件加载环境变量（若存在且尚未设置）"""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                if k and not os.environ.get(k):
                    os.environ[k] = v


def get_config() -> dict[str, str]:
    """从环境变量读取 Jira 配置（会先尝试加载 .env）"""
    _load_dotenv()
    return {
        "base_url": (os.environ.get("JIRA_BASE_URL") or DEFAULT_JIRA_BASE).rstrip("/"),
        "email": os.environ.get("JIRA_EMAIL", ""),
        "api_token": os.environ.get("JIRA_API_TOKEN", ""),
    }


# ---------------------------------------------------------------------------
# ADF -> Markdown 转换（仅用标准库，支持常用节点与图片占位）
# ---------------------------------------------------------------------------

def _adf_inline_to_md(node: dict) -> str:
    """将 ADF 内联内容（paragraph 内）转为 Markdown 片段"""
    if not isinstance(node, dict):
        return ""
    typ = node.get("type")
    if typ == "text":
        text = node.get("text", "")
        marks = {m.get("type"): m for m in node.get("marks", []) if isinstance(m, dict)}
        if marks.get("strong"):
            text = f"**{text}**"
        if marks.get("em"):
            text = f"*{text}*"
        if marks.get("code"):
            text = f"`{text}`"
        link = marks.get("link")
        if link and isinstance(link.get("attrs"), dict):
            href = link["attrs"].get("href", "")
            if href:
                text = f"[{text}]({href})"
        return text
    if typ == "hardBreak":
        return "\n"
    if typ == "mention":
        attrs = node.get("attrs") or {}
        return attrs.get("text") or node.get("text") or ""
    return ""


def _adf_cell_content_to_md(
    cell: dict,
    attachments: list[dict],
    images_dir: Path,
    image_downloads: list[tuple[str, Path]],
) -> str:
    """将表格单元格内容转为纯文本（用于 Markdown 表格单元格）"""
    content = cell.get("content") or []
    parts = []
    for c in content:
        typ = c.get("type")
        if typ == "paragraph":
            inline_parts = [_adf_inline_to_md(x) for x in (c.get("content") or [])]
            parts.append("".join(inline_parts).strip())
        elif typ == "text":
            parts.append(_adf_inline_to_md(c))
        elif typ == "mediaSingle":
            for mc in (c.get("content") or []):
                if mc.get("type") == "media":
                    attrs = mc.get("attrs") or {}
                    alt = (attrs.get("alt") or "image").strip()
                    media_id = attrs.get("id") or ""
                    url = None
                    for att in attachments:
                        fn = (att.get("filename") or "").strip()
                        if fn and (fn == alt or att.get("id") == media_id):
                            url = att.get("content")
                            if not alt or alt == "image":
                                alt = fn
                            break
                    ext = Path(alt).suffix or ".png"
                    safe_name = re.sub(r"[^\w\-.]", "_", Path(alt).stem)[:80] + ext
                    local_path = images_dir / safe_name
                    image_downloads.append((url or "", local_path))
                    parts.append(f"![{alt}]({images_dir.name}/{safe_name})")
        else:
            inner = c.get("content") or []
            for ic in inner:
                if ic.get("type") == "text":
                    parts.append(_adf_inline_to_md(ic))
    return " ".join(parts).replace("\n", " ").replace("|", "\\|").strip()


def _adf_table_to_md(
    table_node: dict,
    attachments: list[dict],
    images_dir: Path,
    image_downloads: list[tuple[str, Path]],
) -> str:
    """将 ADF table 节点转为 Markdown 表格"""
    rows = table_node.get("content") or []
    if not rows:
        return ""
    
    md_rows = []
    header_row_idx = -1
    
    for row_idx, row in enumerate(rows):
        if row.get("type") != "tableRow":
            continue
        cells = row.get("content") or []
        row_cells = []
        is_header_row = False
        
        for cell in cells:
            cell_type = cell.get("type")
            if cell_type in ("tableHeader", "tableCell"):
                if cell_type == "tableHeader":
                    is_header_row = True
                cell_text = _adf_cell_content_to_md(cell, attachments, images_dir, image_downloads)
                row_cells.append(cell_text)
        
        if row_cells:
            md_rows.append((is_header_row, row_cells))
            if is_header_row and header_row_idx < 0:
                header_row_idx = len(md_rows) - 1
    
    if not md_rows:
        return ""
    
    # 计算每列最大宽度（用于对齐，可选）
    col_count = max(len(r[1]) for r in md_rows)
    
    # 构建 Markdown 表格
    lines = []
    separator_added = False
    
    # 如果没有表头行，将第一行视为表头
    if header_row_idx < 0 and md_rows:
        md_rows[0] = (True, md_rows[0][1])
        header_row_idx = 0
    
    for idx, (is_header, cells) in enumerate(md_rows):
        # 补齐列数
        while len(cells) < col_count:
            cells.append("")
        line = "| " + " | ".join(cells) + " |"
        lines.append(line)
        # 在表头行后添加分隔符（只添加一次）
        if not separator_added and is_header:
            separator = "|" + "|".join(["------"] * col_count) + "|"
            lines.append(separator)
            separator_added = True
    
    return "\n".join(lines) + "\n"


def _adf_block_to_md(
    node: dict,
    attachments: list[dict],
    images_dir: Path,
    image_downloads: list[tuple[str, Path]],
    indent: int = 0,
) -> str:
    """将单个 ADF 块节点转为 Markdown（递归）。图片写入 image_downloads 供后续下载。"""
    if not isinstance(node, dict):
        return ""
    typ = node.get("type")
    content = node.get("content") or []
    prefix = "  " * indent

    if typ == "paragraph":
        parts = [_adf_inline_to_md(c) for c in content]
        return prefix + "".join(parts).strip() + "\n\n" if any(parts) else ""

    if typ == "heading":
        level = min(6, max(1, (node.get("attrs") or {}).get("level", 1)))
        parts = [_adf_inline_to_md(c) for c in content]
        return prefix + "#" * level + " " + "".join(parts).strip() + "\n\n"

    if typ == "codeBlock":
        attrs = node.get("attrs") or {}
        lang = (attrs.get("language") or "").strip() or ""
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        code = "".join(parts)
        return prefix + "```" + lang + "\n" + code + "\n```\n\n"

    if typ == "blockquote":
        inner = "".join(
            _adf_block_to_md(c, attachments, images_dir, image_downloads, indent + 1)
            for c in content
        ).strip()
        return prefix + "> " + inner.replace("\n\n", "\n> ") + "\n\n"

    if typ == "rule":
        return prefix + "---\n\n"

    if typ == "bulletList":
        lines = []
        for c in content:
            if c.get("type") == "listItem":
                item_inner = "".join(
                    _adf_block_to_md(x, attachments, images_dir, image_downloads, indent + 1)
                    for x in (c.get("content") or [])
                ).strip()
                lines.append(prefix + "- " + item_inner.replace("\n\n", "\n  ") + "\n")
        return "\n".join(lines) + "\n" if lines else ""

    if typ == "orderedList":
        attrs = node.get("attrs") or {}
        start = attrs.get("order", 1)
        lines = []
        for i, c in enumerate(content):
            if c.get("type") == "listItem":
                item_inner = "".join(
                    _adf_block_to_md(x, attachments, images_dir, image_downloads, indent + 1)
                    for x in (c.get("content") or [])
                ).strip()
                lines.append(prefix + f"{start + i}. " + item_inner.replace("\n\n", "\n   ") + "\n")
        return "\n".join(lines) + "\n" if lines else ""

    if typ == "listItem":
        return "".join(
            _adf_block_to_md(c, attachments, images_dir, image_downloads, indent)
            for c in content
        )

    if typ == "mediaSingle":
        # 内层通常为 media 节点
        for c in content:
            if c.get("type") == "media":
                attrs = c.get("attrs") or {}
                alt = (attrs.get("alt") or "image").strip()
                media_id = attrs.get("id") or ""
                # 尝试用 filename 匹配附件
                url = None
                for att in attachments:
                    fn = (att.get("filename") or "").strip()
                    if fn and (fn == alt or att.get("id") == media_id):
                        url = att.get("content")
                        if not alt or alt == "image":
                            alt = fn
                        break
                if not url and attachments and not alt:
                    att = attachments[0]
                    url = att.get("content")
                    alt = att.get("filename") or "image"
                # 安全文件名
                ext = Path(alt).suffix or ".png"
                safe_name = re.sub(r"[^\w\-.]", "_", Path(alt).stem)[:80] + ext
                local_path = images_dir / safe_name
                image_downloads.append((url or "", local_path))
                return prefix + f"![{alt}]({images_dir.name}/{safe_name})\n\n"
        return ""

    if typ == "panel":
        inner = "".join(
            _adf_block_to_md(c, attachments, images_dir, image_downloads, indent + 1)
            for c in content
        ).strip()
        return prefix + "> " + inner.replace("\n\n", "\n> ") + "\n\n"

    if typ == "table":
        return _adf_table_to_md(node, attachments, images_dir, image_downloads) + "\n"

    if typ == "doc":
        return "".join(
            _adf_block_to_md(c, attachments, images_dir, image_downloads, indent)
            for c in content
        )

    # 未识别节点：尝试递归 content
    if content:
        return "".join(
            _adf_block_to_md(c, attachments, images_dir, image_downloads, indent)
            for c in content
        )
    return ""


def adf_to_markdown(
    adf: Optional[dict],
    attachments: list[dict],
    images_dir: Path,
    image_downloads: list[tuple[str, Path]],
) -> str:
    """将 ADF 文档转为 Markdown 字符串。需下载的图片追加到 image_downloads。"""
    if not adf or not isinstance(adf, dict):
        return ""
    return _adf_block_to_md(adf, attachments, images_dir, image_downloads).strip() + "\n"


# ---------------------------------------------------------------------------
# Jira API
# ---------------------------------------------------------------------------

def fetch_issue(
    issue_key: str,
    base_url: str,
    auth: tuple[str, str],
) -> dict[str, Any]:
    """拉取单个 Issue（含 description、summary、attachment）。"""
    url = f"{base_url}/rest/api/3/issue/{issue_key}"
    params = {"fields": "summary,description,attachment"}
    r = requests.get(url, auth=auth, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def get_attachment_list(issue: dict[str, Any]) -> list[dict]:
    """从 Issue 响应中取出附件列表（含 content 下载 URL）。"""
    fields = issue.get("fields") or {}
    atts = fields.get("attachment") or []
    return [
        {
            "id": a.get("id"),
            "filename": a.get("filename"),
            "content": a.get("content"),
        }
        for a in atts
        if isinstance(a, dict) and a.get("content")
    ]


def download_image(url: str, local_path: Path, auth: tuple[str, str]) -> bool:
    """下载图片到本地。"""
    if not url:
        return False
    try:
        r = requests.get(url, auth=auth, timeout=30, stream=True)
        r.raise_for_status()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 同步逻辑
# ---------------------------------------------------------------------------

def build_markdown_document(
    issue_key: str,
    summary: str,
    body_md: str,
    base_url: str,
) -> str:
    """组装完整 Markdown 文档（标题 + Jira 链接 + 正文）。"""
    jira_link = f"{base_url}/browse/{issue_key}"
    header = f"# {summary}\n\n"
    header += f"**JIRA**: [{issue_key}]({jira_link})\n\n"
    header += "---\n\n"
    return header + body_md


def sync_issue_to_file(
    issue_key: str,
    output_path: Path,
    base_url: str,
    auth: tuple[str, str],
    images_subdir: str = "images",
) -> bool:
    """
    将指定 Jira Issue 同步到本地 Markdown 文件，并下载描述中的图片到同目录下的 images 子目录。
    """
    try:
        issue = fetch_issue(issue_key, base_url, auth)
    except requests.RequestException as e:
        print(f"拉取 Issue 失败: {e}", file=sys.stderr)
        return False

    fields = issue.get("fields") or {}
    summary = (fields.get("summary") or issue_key).strip()
    description_adf = fields.get("description")
    attachments = get_attachment_list(issue)

    output_path = Path(output_path)
    # 若输出是目录或未带 .md 后缀，则在该路径下生成 {issue_key}.md
    if output_path.suffix.lower() != ".md":
        output_path = output_path / f"{issue_key}.md"
    file_dir = output_path.parent
    images_dir = file_dir / images_subdir
    image_downloads: list[tuple[str, Path]] = []

    body_md = adf_to_markdown(description_adf, attachments, images_dir, image_downloads)
    if not body_md.strip() and not summary:
        body_md = "*（无描述内容）*\n"

    full_md = build_markdown_document(issue_key, summary, body_md, base_url)

    # 下载图片
    for url, local_path in image_downloads:
        if url:
            ok = download_image(url, local_path, auth)
            if not ok:
                print(f"  警告: 图片下载失败 {url}", file=sys.stderr)

    file_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_md, encoding="utf-8")
    print(f"已同步: {issue_key} -> {output_path}")
    return True


def load_mapping_from_yaml(path: Path) -> dict[str, str]:
    """从 YAML 文件加载 Issue Key -> 输出路径 映射。无 PyYAML 时按简单 key: path 行解析。"""
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    mapping = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            mapping[k.strip()] = v.strip()
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 Jira Cloud 拉取 Issue 并同步为 Markdown 文件（含图片下载）",
    )
    parser.add_argument(
        "issue_keys",
        nargs="*",
        help="Jira Issue Key，例如 PAPI-2199；与 --config 二选一",
    )
    parser.add_argument(
        "-o", "--output",
        required=False,
        help="输出 .md 文件路径或目录；为目录时自动生成 {issue_key}.md",
    )
    parser.add_argument(
        "--config",
        required=False,
        help="配置文件路径：每行 'ISSUE_KEY: path/to/file.md'，将批量同步",
    )
    parser.add_argument(
        "--images-dir",
        default="images",
        help="图片存放子目录名（相对于每个 MD 所在目录），默认 images",
    )
    args = parser.parse_args()

    cfg = get_config()
    if not cfg["email"] or not cfg["api_token"]:
        print(
            "请设置环境变量 JIRA_EMAIL 和 JIRA_API_TOKEN。",
            file=sys.stderr,
        )
        sys.exit(1)
    auth = (cfg["email"], cfg["api_token"])

    if args.config:
        mapping = load_mapping_from_yaml(Path(args.config))
        if not mapping:
            print("配置文件中未找到有效映射", file=sys.stderr)
            sys.exit(1)
        success = 0
        for key, out in mapping.items():
            if sync_issue_to_file(
                key,
                Path(out),
                cfg["base_url"],
                auth,
                images_subdir=args.images_dir,
            ):
                success += 1
        print(f"完成: {success}/{len(mapping)} 个 Issue 同步成功")
        sys.exit(0 if success == len(mapping) else 1)
    else:
        if not args.issue_keys:
            parser.error("请提供至少一个 issue_keys，或使用 --config 指定配置文件")
        if not args.output:
            parser.error("单 Issue 同步请指定 -o/--output 输出路径")
        out_path = Path(args.output)
        ok = sync_issue_to_file(
            args.issue_keys[0],
            out_path,
            cfg["base_url"],
            auth,
            images_subdir=args.images_dir,
        )
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
