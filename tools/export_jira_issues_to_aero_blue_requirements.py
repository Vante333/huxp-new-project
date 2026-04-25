# -*- coding: utf-8 -*-
"""
从 Jira 工单拉取需求正文到仓库 `requirements/Aero Blue/`：
- 若描述（ADF）或字段 JSON 中含 Confluence `/pages/<id>/` 链接，则优先拉取该 Wiki 页为 Markdown 并下载图片附件；
- 否则将 Jira 描述（ADF）导出为 Markdown，并下载 Jira 图片附件。
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from fetch_confluence import (  # noqa: E402
    BASE_URL,
    _load_env_from_dotenv,
    api_get,
    get_auth_header,
    storage_html_to_markdown,
)


ISSUE_KEYS: Tuple[str, ...] = (
    "PAPI-2657",
    "PAPI-2576",
    "PAPI-2204",
    "PAPI-2644",
    "PAPI-2636",
)
AERO_BLUE_DIR = os.path.join("requirements", "Aero Blue")
IMAGES_SUBDIR = "images"


def _FmtText(node: Dict[str, Any]) -> str:
    if node.get("type") != "text":
        return ""
    s = node.get("text") or ""
    for m in node.get("marks") or []:
        mt = m.get("type")
        if mt == "strong":
            s = f"**{s}**"
        elif mt == "code":
            s = f"`{s}`"
        elif mt == "em":
            s = f"*{s}*"
    return s


def _InlineContent(nodes: Optional[List[Dict[str, Any]]]) -> str:
    if not nodes:
        return ""
    parts: List[str] = []
    for ch in nodes:
        t = ch.get("type")
        if t == "text":
            parts.append(_FmtText(ch))
        elif t == "hardBreak":
            parts.append("\n")
        else:
            parts.append(_InlineContent(ch.get("content")))
    return "".join(parts)


def _BlockToLines(node: Dict[str, Any], lines: List[str], list_prefix: str = "") -> None:
    t = node.get("type")
    if t == "heading":
        lvl = int(node.get("attrs", {}).get("level", 2))
        hashes = "#" * max(2, min(lvl + 1, 6))
        txt = _InlineContent(node.get("content"))
        lines.append(f"{hashes} {txt}".rstrip())
        lines.append("")
    elif t == "paragraph":
        txt = _InlineContent(node.get("content"))
        if txt.strip():
            lines.append(f"{list_prefix}{txt}".rstrip())
            lines.append("")
    elif t == "codeBlock":
        parts_cb: List[str] = []
        for ch in node.get("content") or []:
            if isinstance(ch, dict) and ch.get("type") == "text":
                parts_cb.append(ch.get("text") or "")
        code = "".join(parts_cb).rstrip("\n")
        lang = ((node.get("attrs") or {}).get("language") or "").strip()
        fence = lang if lang else "json"
        lines.append(f"```{fence}")
        lines.append(code)
        lines.append("```")
        lines.append("")
    elif t == "bulletList":
        for item in node.get("content") or []:
            if item.get("type") != "listItem":
                continue
            inner = item.get("content") or []
            first = True
            for blk in inner:
                prefix = "- " if first else "  "
                first = False
                _BlockToLines(blk, lines, list_prefix=prefix)
    elif t == "orderedList":
        idx = 1
        for item in node.get("content") or []:
            if item.get("type") != "listItem":
                continue
            inner = item.get("content") or []
            first = True
            for blk in inner:
                prefix = f"{idx}. " if first else "   "
                first = False
                _BlockToLines(blk, lines, list_prefix=prefix)
            idx += 1
    elif t == "table":
        lines.extend(_TableToMarkdownLines(node))
        lines.append("")
    elif t == "mediaSingle":
        lines.append("")
    else:
        inner = node.get("content")
        if isinstance(inner, list):
            for ch in inner:
                if isinstance(ch, dict):
                    _BlockToLines(ch, lines, list_prefix=list_prefix)


def _CellPlainHtml(cell: Dict[str, Any]) -> str:
    attrs = cell.get("attrs") or {}
    colspan = int(attrs.get("colspan", 1) or 1)
    rowspan = int(attrs.get("rowspan", 1) or 1)
    tag = cell.get("type", "td")
    html_tag = "th" if tag == "tableHeader" else "td"
    inner_parts: List[str] = []
    for blk in cell.get("content") or []:
        if blk.get("type") == "paragraph":
            t = _InlineContent(blk.get("content"))
            if t.strip():
                inner_parts.append(t.strip())
        else:
            sub: List[str] = []
            _BlockToLines(blk, sub, "")
            merged = " ".join(s.strip() for s in sub if s.strip())
            if merged:
                inner_parts.append(merged)
    body = "<br/>".join(inner_parts)
    cs = f' colspan="{colspan}"' if colspan > 1 else ""
    rs = f' rowspan="{rowspan}"' if rowspan > 1 else ""
    return f"<{html_tag}{cs}{rs}>{body}</{html_tag}>"


def _TableToMarkdownLines(table: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    lines.append("> 以下表格由 Jira ADF 导出为 HTML（含合并单元格）。")
    lines.append("")
    lines.append('<table border="1" style="border-collapse:collapse;">')
    for row in table.get("content") or []:
        if row.get("type") != "tableRow":
            continue
        lines.append("<tr>")
        for cell in row.get("content") or []:
            if cell.get("type") not in ("tableCell", "tableHeader"):
                continue
            lines.append(_CellPlainHtml(cell))
        lines.append("</tr>")
    lines.append("</table>")
    return lines


def _AdfDocToMarkdown(doc: Dict[str, Any]) -> str:
    lines: List[str] = []
    for block in doc.get("content") or []:
        if isinstance(block, dict):
            _BlockToLines(block, lines, "")
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def _WalkCollectWikiPageIds(node: Any, out: List[str]) -> None:
    if isinstance(node, dict):
        if node.get("type") == "inlineCard":
            u = (node.get("attrs") or {}).get("url") or ""
            for m in re.finditer(r"/pages/(\d+)", u):
                out.append(m.group(1))
        for v in node.values():
            _WalkCollectWikiPageIds(v, out)
    elif isinstance(node, list):
        for item in node:
            _WalkCollectWikiPageIds(item, out)


def _ExtractWikiPageIdsFromIssue(fields: Dict[str, Any]) -> List[str]:
    found: List[str] = []
    desc = fields.get("description")
    _WalkCollectWikiPageIds(desc, found)
    blob = json.dumps(fields, ensure_ascii=False)
    for m in re.finditer(r"/pages/(\d+)", blob):
        found.append(m.group(1))
    seen: set = set()
    ordered: List[str] = []
    for pid in found:
        if pid not in seen:
            seen.add(pid)
            ordered.append(pid)
    return ordered


def _FetchIssue(issue_key: str) -> Dict[str, Any]:
    url = (
        f"https://dragonpass.atlassian.net/rest/api/3/issue/{issue_key}"
        "?fields=summary,description,attachment"
    )
    req = Request(url, headers={**get_auth_header(), "Accept": "application/json"})
    resp = urlopen(req, timeout=90)
    return json.loads(resp.read().decode("utf-8"))


def _DownloadJiraAttachment(content_url: str, dest_path: str) -> None:
    req = Request(content_url, headers=get_auth_header())
    resp = urlopen(req, timeout=120)
    with open(dest_path, "wb") as f:
        f.write(resp.read())


def _DownloadConfluencePageImages(page_id: str, img_dir: str) -> int:
    os.makedirs(img_dir, exist_ok=True)
    data = api_get(f"/rest/api/content/{page_id}/child/attachment?limit=100")
    n = 0
    for att in data.get("results", []):
        filename = att.get("title") or ""
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        download_url = BASE_URL + att["_links"]["download"]
        req = Request(download_url, headers=get_auth_header())
        resp = urlopen(req, timeout=120)
        with open(os.path.join(img_dir, filename), "wb") as f:
            f.write(resp.read())
        n += 1
    return n


def _TryWriteConfluenceMarkdown(
    issue_key: str,
    summary: str,
    page_id: str,
    out_md: str,
) -> bool:
    try:
        data = api_get(f"/rest/api/content/{page_id}?expand=body.storage,title")
    except Exception as exc:
        print(f"  [Confluence] page {page_id} 不可用: {exc}", file=sys.stderr)
        return False
    title = data.get("title") or issue_key
    body_storage = (data.get("body") or {}).get("storage") or {}
    storage_html = body_storage.get("value") or ""
    body_md = storage_html_to_markdown(storage_html)
    webui = data.get("_links", {}).get("webui")
    wiki_url = f"{BASE_URL}{webui}" if webui else f"{BASE_URL}/pages/{page_id}"
    jira_url = f"https://dragonpass.atlassian.net/browse/{issue_key}"
    header = (
        f"# {issue_key} {title}\n\n"
        f"来源：Confluence <{wiki_url}> · Jira <{jira_url}>\n\n"
        f"> 说明：由工单关联的 Wiki 页面（pageId=`{page_id}`）通过 API 导出。\n\n"
        f"---\n\n"
    )
    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(body_md)
    return True


def _WriteJiraAdfMarkdown(
    issue_key: str,
    summary: str,
    fields: Dict[str, Any],
    out_md: str,
    img_dir: str,
) -> None:
    jira_url = f"https://dragonpass.atlassian.net/browse/{issue_key}"
    desc = fields.get("description")

    os.makedirs(img_dir, exist_ok=True)
    image_refs: List[str] = []
    for att in fields.get("attachment") or []:
        fn = att.get("filename") or ""
        if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            continue
        content_u = att.get("content")
        if not content_u:
            continue
        dest = os.path.join(img_dir, fn)
        _DownloadJiraAttachment(str(content_u), dest)
        image_refs.append(f"![]({IMAGES_SUBDIR}/{fn})")

    body_md = ""
    if isinstance(desc, dict) and desc.get("type") == "doc":
        body_md = _AdfDocToMarkdown(desc)
    elif isinstance(desc, str) and desc.strip():
        body_md = "```text\n" + desc.strip() + "\n```\n"
    elif desc is not None:
        body_md = "```json\n" + json.dumps(desc, ensure_ascii=False, indent=2) + "\n```\n"

    intro = (
        f"# {issue_key} {summary}\n\n"
        f"来源：Jira <{jira_url}>\n\n"
        f"> 说明：未发现可用 Confluence `/pages/<id>/` 链接；以下由 **Jira 描述** 导出。\n\n"
        "---\n\n"
    )
    if image_refs:
        intro += "\n\n".join(image_refs) + "\n\n---\n\n"

    os.makedirs(os.path.dirname(out_md), exist_ok=True)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(intro)
        f.write(body_md)


def ExportIssuesToAeroBlue(issue_keys: Tuple[str, ...] = ISSUE_KEYS) -> None:
    _load_env_from_dotenv()
    root = os.path.join(os.path.dirname(__file__), "..")
    os.chdir(root)

    img_dir = os.path.join(AERO_BLUE_DIR, IMAGES_SUBDIR)
    os.makedirs(img_dir, exist_ok=True)

    for key in issue_keys:
        print(f"Processing {key}...")
        data = _FetchIssue(key)
        fields = data.get("fields", {})
        summary = (fields.get("summary") or key).strip()
        out_md = os.path.join(AERO_BLUE_DIR, f"{key}.md")

        wiki_ids = _ExtractWikiPageIdsFromIssue(fields)
        done = False
        for pid in wiki_ids:
            if _TryWriteConfluenceMarkdown(key, summary, pid, out_md):
                nimg = _DownloadConfluencePageImages(pid, img_dir)
                print(f"  -> Confluence page {pid}, wrote {out_md}, images={nimg}")
                done = True
                break
        if not done:
            _WriteJiraAdfMarkdown(key, summary, fields, out_md, img_dir)
            print(f"  -> Jira ADF, wrote {out_md}")


def Main() -> None:
    keys: Tuple[str, ...] = tuple(sys.argv[1:]) if len(sys.argv) > 1 else ISSUE_KEYS
    if not keys:
        print("用法: python tools/export_jira_issues_to_aero_blue_requirements.py [PAPI-xxxx ...]", file=sys.stderr)
        sys.exit(2)
    ExportIssuesToAeroBlue(keys)


if __name__ == "__main__":
    Main()
