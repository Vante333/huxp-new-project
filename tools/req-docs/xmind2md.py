"""
XMind to Markdown 转换工具

用法:
    python tools/req-docs/xmind2md.py input.xmind                    # 输出到同目录下的 .md 文件
    python tools/req-docs/xmind2md.py input.xmind -o output.md       # 指定输出文件
    python tools/req-docs/xmind2md.py input.xmind --max-heading 3    # 最多使用 h3，之后用列表
    python tools/req-docs/xmind2md.py ./my_folder/                    # 批量转换目录下所有 .xmind 文件

依赖: 无第三方依赖，仅使用 Python 标准库
"""

from __future__ import annotations

import json
import zipfile
import argparse
import sys
from pathlib import Path
from typing import Optional


def extract_xmind_content(xmind_path: str) -> list:
    """从 .xmind 文件中提取 content.json 数据"""
    with zipfile.ZipFile(xmind_path, "r") as zf:
        namelist = zf.namelist()

        # 新版 XMind (8+) 使用 content.json
        if "content.json" in namelist:
            with zf.open("content.json") as f:
                return json.loads(f.read().decode("utf-8"))

        # 旧版 XMind 使用 content.xml —— 暂不支持
        if "content.xml" in namelist:
            raise ValueError(
                "检测到旧版 XMind 格式 (content.xml)，本工具仅支持 XMind 8+ 的 JSON 格式。\n"
                "请用 XMind 软件打开后重新保存，即可转为新格式。"
            )

        raise ValueError(f"无法识别的 .xmind 文件结构，包含文件: {namelist}")


def topic_to_markdown(topic: dict, depth: int = 0, max_heading: int = 4) -> list[str]:
    """
    递归将 XMind topic 节点转换为 Markdown 行。

    - depth 0 ~ (max_heading-1): 使用 # 标题
    - depth >= max_heading: 使用缩进列表
    """
    lines = []
    title = topic.get("title", "").strip()
    if not title:
        title = "(空节点)"

    # 收集标注/标签/备注
    labels = topic.get("labels", [])
    notes_plain = ""
    if "notes" in topic:
        notes_plain = topic["notes"].get("plain", {}).get("content", "").strip()

    # 构造当前节点文本
    node_text = title
    if labels:
        node_text += "  " + " ".join(f"`{l}`" for l in labels)

    if depth < max_heading:
        # 用 Markdown 标题
        prefix = "#" * (depth + 1)
        lines.append(f"{prefix} {node_text}")
        lines.append("")
        if notes_plain:
            lines.append(notes_plain)
            lines.append("")
    else:
        # 用缩进列表
        indent = "  " * (depth - max_heading)
        lines.append(f"{indent}- {node_text}")
        if notes_plain:
            for note_line in notes_plain.split("\n"):
                lines.append(f"{indent}  {note_line}")

    # 递归处理子节点
    children = (
        topic.get("children", {}).get("attached", [])
        or topic.get("children", {}).get("topics", [])
        or []
    )
    # 兼容某些版本 children 直接是列表的情况
    if isinstance(topic.get("children"), list):
        children = topic["children"]

    for child in children:
        lines.extend(topic_to_markdown(child, depth + 1, max_heading))

    # 标题层级之间加空行
    if depth < max_heading and children:
        lines.append("")

    return lines


def convert_xmind_to_markdown(xmind_path: str, max_heading: int = 4) -> str:
    """将 .xmind 文件转换为 Markdown 字符串"""
    sheets = extract_xmind_content(xmind_path)
    all_lines = []

    for i, sheet in enumerate(sheets):
        root_topic = sheet.get("rootTopic", {})
        sheet_title = sheet.get("title", root_topic.get("title", f"Sheet {i + 1}"))

        if len(sheets) > 1:
            all_lines.append(f"---\n\n# 画布: {sheet_title}\n")

        md_lines = topic_to_markdown(root_topic, depth=0, max_heading=max_heading)
        all_lines.extend(md_lines)

    return "\n".join(all_lines).strip() + "\n"


def process_file(xmind_path: Path, output_path: Optional[Path], max_heading: int):
    """处理单个文件的转换"""
    print(f"正在转换: {xmind_path}")
    try:
        md_content = convert_xmind_to_markdown(str(xmind_path), max_heading)
    except Exception as e:
        print(f"  ❌ 转换失败: {e}")
        return False

    if output_path is None:
        output_path = xmind_path.with_suffix(".md")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(md_content, encoding="utf-8")
    print(f"  ✅ 已保存: {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="将 XMind 思维导图转换为 Markdown 文件"
    )
    parser.add_argument(
        "input",
        help="输入的 .xmind 文件路径，或包含 .xmind 文件的目录（批量转换）",
    )
    parser.add_argument(
        "-o", "--output",
        help="输出的 .md 文件路径（批量模式下不可用）",
        default=None,
    )
    parser.add_argument(
        "--max-heading",
        type=int,
        default=4,
        help="最大标题层级（默认 4，即 h1~h4 用标题，更深层级用列表）",
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if input_path.is_dir():
        xmind_files = sorted(input_path.rglob("*.xmind"))
        if not xmind_files:
            print(f"目录中未找到 .xmind 文件: {input_path}")
            sys.exit(1)
        if args.output:
            print("批量模式下不支持 -o 参数，输出文件将自动命名")
            sys.exit(1)

        success = sum(
            process_file(f, None, args.max_heading) for f in xmind_files
        )
        print(f"\n完成: {success}/{len(xmind_files)} 个文件转换成功")
    else:
        if not input_path.exists():
            print(f"文件不存在: {input_path}")
            sys.exit(1)
        output = Path(args.output) if args.output else None
        if not process_file(input_path, output, args.max_heading):
            sys.exit(1)


if __name__ == "__main__":
    main()
