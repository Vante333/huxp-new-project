# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import json
import os
import re
import sys
from urllib.request import Request, urlopen

try:
    import html2text  # type: ignore
except ImportError:
    html2text = None

BASE_URL = "https://dragonpass.atlassian.net/wiki"
PAGE_ID = "1492779221"


def _load_env_from_dotenv() -> None:
    """
    尝试从项目根目录的 .env 文件加载环境变量（仅在当前进程内生效）。
    支持的格式：
        KEY=VALUE
    以 # 开头的行会被忽略。
    """
    root_dir = os.path.join(os.path.dirname(__file__), "..")
    env_path = os.path.join(root_dir, ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # 不覆盖已存在的环境变量
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # 加载失败时静默忽略，保持原有行为（只读系统环境变量）
        pass


def get_auth_header() -> dict:
    # 优先尝试从 .env 加载（若存在）
    _load_env_from_dotenv()

    email = os.getenv("JIRA_EMAIL")
    token = os.getenv("JIRA_API_TOKEN")
    if not email or not token:
        raise RuntimeError(
            "Confluence 认证信息缺失，请在环境变量或 .env 中配置 JIRA_EMAIL / JIRA_API_TOKEN"
        )
    creds = base64.b64encode(f"{email}:{token}".encode("ascii")).decode("ascii")
    return {"Authorization": f"Basic {creds}", "Accept": "application/json"}


def api_get(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    req = Request(url, headers=get_auth_header())
    resp = urlopen(req, timeout=120)
    return json.loads(resp.read().decode("utf-8"))


def _replace_code_macros(html: str) -> str:
    """
    将 Confluence 的 <ac:structured-macro ac:name="code"> 转成 Markdown fenced code block。
    """

    pattern = (
        r'<ac:structured-macro[^>]*ac:name="code"[^>]*>.*?'
        r"<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>"
        r".*?</ac:structured-macro>"
    )

    def _repl(match: re.Match) -> str:
        code = match.group(1).strip("\n")
        # 这里不强行判断语言，默认用 json，更符合当前接口文档的主要场景
        return f"\n```json\n{code}\n```\n"

    return re.sub(pattern, _repl, html, flags=re.DOTALL)


def _replace_html_entities(text: str) -> str:
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
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _strip_inline_html(html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "- ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = _replace_html_entities(text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text.strip()


def _replace_tables(html: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}
    counter = 0

    def _table_repl(match: re.Match) -> str:
        nonlocal counter
        table_html = match.group(0)
        row_html_list = re.findall(
            r"<tr[^>]*>(.*?)</tr>", table_html, flags=re.DOTALL | re.IGNORECASE
        )
        md_rows: list[list[str]] = []
        has_header_row = False
        for row_html in row_html_list:
            if re.search(r"<th[^>]*>", row_html, flags=re.IGNORECASE):
                has_header_row = True
                break
        for row_html in row_html_list:
            cell_html_list = re.findall(
                r"<t[hd][^>]*>(.*?)</t[hd]>",
                row_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
            md_rows.append(
                [
                    _strip_inline_html(cell_html).replace("\n", "<br>")
                    for cell_html in cell_html_list
                ]
            )
        if not md_rows:
            return ""
        if not has_header_row:
            col_count = max(len(row) for row in md_rows)
            if col_count == 3 and re.match(r"^\d+\.\d+\.\d+", md_rows[0][0]):
                md_rows.insert(0, ["错误码", "说明", "英文提示"])
            elif col_count == 2:
                md_rows.insert(0, ["项", "说明"])
            elif col_count >= 3:
                md_rows.insert(0, [f"列{i + 1}" for i in range(col_count)])
        col_count = max(len(row) for row in md_rows)
        normalized = [row + [""] * (col_count - len(row)) for row in md_rows]
        lines = [
            "| " + " | ".join(normalized[0]) + " |",
            "| " + " | ".join(["---"] * col_count) + " |",
        ]
        for row in normalized[1:]:
            lines.append("| " + " | ".join(row) + " |")
        key = f"__CONFLUENCE_TABLE_{counter}__"
        counter += 1
        placeholders[key] = "\n\n" + "\n".join(lines) + "\n\n"
        return f"\n\n{key}\n\n"

    html = re.sub(
        r"<table[^>]*>.*?</table>",
        _table_repl,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html, placeholders


def _replace_headings(html: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    for level in range(6, 0, -1):
        tag = f"h{level}"
        counter = 0

        def _heading_repl(match: re.Match, heading_level: int = level) -> str:
            nonlocal counter
            content = _strip_inline_html(match.group(1))
            hashes = "#" * heading_level
            key = f"__CONFLUENCE_H{heading_level}_{counter}__"
            counter += 1
            placeholders[key] = f"\n\n{hashes} {content}\n\n"
            return f"\n\n{key}\n\n"

        html = re.sub(
            rf"<{tag}[^>]*>(.*?)</{tag}>",
            _heading_repl,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return html, placeholders


def _restore_placeholders(text: str, placeholders: dict[str, str]) -> str:
    for key, value in placeholders.items():
        text = text.replace(key, value)
    return text


def _replace_images(html: str) -> str:
    """
    将 <ac:image><ri:attachment ri:filename="xxx" /></ac:image>
    转成 Markdown 图片引用，默认指向 images/ 目录，便于后续配合 download_images 使用。
    """

    pattern = (
        r'<ac:image[^>]*>.*?<ri:attachment[^>]*ri:filename="([^"]+)"[^>]*/?>.*?</ac:image>'
    )

    def _repl(match: re.Match) -> str:
        filename = match.group(1)
        # 这里固定用正斜杠，避免在 Windows 上生成反斜杠路径
        return f"![](images/{filename})"

    return re.sub(pattern, _repl, html, flags=re.DOTALL)


def storage_html_to_markdown(html: str) -> str:
    """
    将 Confluence storage format HTML 粗清洗并转换为 Markdown。
    """
    # 先把常见的 Confluence 宏替换掉
    cleaned = _replace_code_macros(html)
    cleaned = _replace_images(cleaned)
    cleaned, heading_placeholders = _replace_headings(cleaned)
    cleaned, table_placeholders = _replace_tables(cleaned)
    placeholders = {**heading_placeholders, **table_placeholders}

    # 优先使用 html2text，如果不可用，则退化为简单的标签清理
    if html2text is not None:
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.body_width = 0  # 不自动折行，保留原文结构
        markdown = h.handle(cleaned)
    else:
        # 简单兜底：尽量保留换行和列表结构
        text = cleaned
        # 段落和换行
        text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        # 列表
        text = re.sub(r"<li[^>]*>", "- ", text, flags=re.IGNORECASE)
        text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
        # 表格换行稍微保留一下
        text = re.sub(r"</tr\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</th\s*>", " | ", text, flags=re.IGNORECASE)
        text = re.sub(r"</td\s*>", " | ", text, flags=re.IGNORECASE)
        # 去掉剩余所有标签
        text = re.sub(r"<[^>]+>", "", text)
        markdown = text

    # 通用 Markdown 后处理
    markdown = _restore_placeholders(markdown, placeholders)
    markdown = _post_process_markdown(markdown)
    markdown = _replace_html_entities(markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip() + "\n"


def _post_process_markdown(md: str) -> str:
    """
    对生成的 Markdown 做一些风格化处理：
    - 图片路径统一为 images/xxx.png（防止出现反斜杠）
    - 将类似“一、xxx”提升为二级标题
    - 将类似“1.1 xxx”提升为三级标题
    """
    # 1）修正图片路径中的反斜杠
    md = re.sub(r"!\[]\((images)\\([^)\r\n]+)\)", r"![](\1/\2)", md)

    # 2）标题提升
    lines = md.splitlines()
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        # 已经是 Markdown 标题的行不处理
        if stripped.startswith("#"):
            continue

        # “一、二、三、...” 这种章节标题 → 二级标题
        if re.match(r"^[一二三四五六七八九十]+、", stripped):
            lines[i] = f"## {stripped}"
            continue

        # “1. / 1.1 / 1.2.3 ...” 这种小节标题 → 三级标题
        if re.match(r"^\d+(\.\d+)+\s", stripped):
            lines[i] = f"### {stripped}"
            continue

    return "\n".join(lines)


def main():
    """
    用法示例：

    1）导出原始 storage HTML 到 json（原有行为）：
        python fetch_confluence.py content <PAGE_ID>

    2）列出附件：
        python fetch_confluence.py attachments <PAGE_ID>

    3）下载图片到固定目录：
        python fetch_confluence.py download_images <PAGE_ID>

    4）一条命令生成干净 Markdown：
        python fetch_confluence.py markdown <PAGE_ID> <OUTPUT_MD_PATH>
    """

    mode = sys.argv[1] if len(sys.argv) > 1 else "content"
    # 优先使用命令行中的 page_id，其次是环境变量，最后是默认 PAGE_ID
    page_id = (
        sys.argv[2]
        if len(sys.argv) > 2 and mode != "markdown"
        else os.getenv("CONFLUENCE_PAGE_ID", PAGE_ID)
    )

    if mode == "content":
        data = api_get(f"/rest/api/content/{page_id}?expand=body.storage,title")
        output = {
            "title": data["title"],
            "body": data["body"]["storage"]["value"],
        }
        out_path = os.path.join(
            os.path.dirname(__file__), "..", "tech-docs", "page_content.json"
        )
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Page content saved to {out_path}")
        print(f"Title: {data['title']}")

    elif mode == "attachments":
        data = api_get(f"/rest/api/content/{page_id}/child/attachment?limit=50")
        for att in data.get("results", []):
            print(f"FILE: {att['title']} | DOWNLOAD: {att['_links']['download']}")

    elif mode == "download_images":
        img_dir = os.path.join(
            os.path.dirname(__file__), "..", "tech-docs", "2026Q1_SP4", "images"
        )
        os.makedirs(img_dir, exist_ok=True)
        data = api_get(f"/rest/api/content/{page_id}/child/attachment?limit=50")
        for att in data.get("results", []):
            filename = att["title"]
            if not filename.lower().endswith(
                (".png", ".jpg", ".jpeg", ".gif", ".svg")
            ):
                continue
            download_url = BASE_URL + att["_links"]["download"]
            print(f"Downloading: {filename}")
            req = Request(download_url, headers=get_auth_header())
            resp = urlopen(req, timeout=120)
            filepath = os.path.join(img_dir, filename)
            with open(filepath, "wb") as f:
                f.write(resp.read())
            print(f"  Saved: {filepath}")
        print("All images downloaded.")

    elif mode == "markdown":
        if len(sys.argv) < 4:
            print(
                "用法：python fetch_confluence.py markdown <PAGE_ID> <OUTPUT_MD_PATH>",
                file=sys.stderr,
            )
            sys.exit(1)

        page_id = sys.argv[2]
        output_md_path = sys.argv[3]

        data = api_get(f"/rest/api/content/{page_id}?expand=body.storage,title")
        title = data["title"]
        storage_html = data["body"]["storage"]["value"]

        body_md = storage_html_to_markdown(storage_html)

        # 使用 Confluence 返回的 webui 链接作为来源链接，避免手抄 URL
        webui = data.get("_links", {}).get("webui")
        source_url = f"{BASE_URL}{webui}" if webui else f"{BASE_URL}/pages/{page_id}"

        full_md = f"# {title}\n\n来源：<{source_url}>\n\n---\n\n{body_md}"

        os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as f:
            f.write(full_md)

        print(f"Markdown saved to {output_md_path}")
        print(f"Title: {title}")

    else:
        print(f"未知模式: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
