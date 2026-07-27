"""
SyncCheck 成功后：从 ``.apifox/suites.yaml`` 读取资产，幂等写入 Skill ``catalog.md`` 表格行。

用法::

    python tools/UpsertApifoxCliCatalog.py --asset papi_2548
    python tools/UpsertApifoxCliCatalog.py --asset papi_2548 --repo-root .
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from ApifoxSuitesYaml import (  # noqa: E402
    BuildCatalogDocCell,
    LoadSuitesText,
    ParseAssetFields,
    RepoRootFromArg,
    SuitesYamlPath,
)


def CatalogPath(repo: Path) -> Path:
    return repo / ".cursor" / "skills" / "apifox-cli-repo-first" / "catalog.md"


def EnsureCatalogSkeleton(path: Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Apifox CLI · 已落地资产目录",
                "",
                "由 `tools/UpsertApifoxCliCatalog.py` 在 SyncCheck 成功后自动维护；Agent 落地新资产后也应核对本表。",
                "",
                "| 资产 key | 标题 | 场景 ID | 场景目录 | 环境 ID | 工作分支 | 生成器 | 详解 | 上次 SyncCheck |",
                "|----------|------|---------|----------|---------|----------|--------|------|----------------|",
                "",
                "> **落新场景前先问目录**：`{membership|epass|common}/{P0(冒烟用例)|P1（全量用例）}/{prebooking|walk-in|others}`。见 Skill 硬约束 §9。",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def BuildScenarioFolderCell(fields: Dict[str, str]) -> str:
    folder = (fields.get("scenario_folder") or "").strip()
    folder_id = (fields.get("scenario_folder_id") or "").strip()
    if folder and folder_id:
        return f"`{folder}`（{folder_id}）"
    if folder:
        return f"`{folder}`"
    if folder_id:
        return folder_id
    return ""


def BuildRow(fields: Dict[str, str], *, when: str, note_doc: str) -> str:
    asset = fields.get("asset_key", "")
    title = fields.get("title", asset)
    scenario = fields.get("test_scenario_id", "")
    folder_cell = BuildScenarioFolderCell(fields)
    env_id = fields.get("environment_id", "")
    branch = fields.get("working_branch", "")
    generator = fields.get("generator", "")
    gen_cell = f"`{generator}`" if generator else ""
    doc_cell = note_doc if note_doc else ""
    return (
        f"| `{asset}` | {title} | {scenario} | {folder_cell} | {env_id} | `{branch}` | {gen_cell} | {doc_cell} | {when} |"
    )


def UpsertRow(catalog_text: str, asset_key: str, new_row: str) -> Tuple[str, str]:
    """返回 (新文本, inserted|updated)。"""
    lines = catalog_text.splitlines()
    pattern = re.compile(rf"^\|\s*`{re.escape(asset_key)}`\s*\|")
    out: List[str] = []
    replaced = False
    for line in lines:
        if pattern.match(line):
            out.append(new_row)
            replaced = True
        else:
            out.append(line)
    if replaced:
        text = "\n".join(out)
        if not text.endswith("\n"):
            text += "\n"
        return text, "updated"
    header_idx = -1
    for i, line in enumerate(out):
        if line.startswith("| 资产 key"):
            header_idx = i
            break
    if header_idx < 0:
        out.extend(["", new_row, ""])
        return "\n".join(out) + "\n", "inserted"
    insert_at = header_idx + 2
    while insert_at < len(out) and out[insert_at].startswith("|"):
        insert_at += 1
    out.insert(insert_at, new_row)
    return "\n".join(out) + "\n", "inserted"


def Main() -> int:
    parser = argparse.ArgumentParser(description="Upsert Apifox CLI skill catalog row")
    parser.add_argument("--asset", required=True, help="suites.yaml assets 下的 key，如 papi_2548")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--doc", default="", help="详解列 Markdown 链接；默认读 suites.yaml 的 doc")
    parser.add_argument("--suites", default="", help="覆盖 suites.yaml 路径")
    args = parser.parse_args()

    repo = RepoRootFromArg(args.repo_root)
    suites_path = SuitesYamlPath(repo, args.suites)
    if not suites_path.is_file():
        raise SystemExit(f"missing {suites_path}")

    fields = ParseAssetFields(LoadSuitesText(repo, args.suites), args.asset)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    doc = args.doc.strip() or BuildCatalogDocCell(repo, fields, args.asset)
    row = BuildRow(fields, when=when, note_doc=doc)

    catalog = CatalogPath(repo)
    EnsureCatalogSkeleton(catalog)
    old = catalog.read_text(encoding="utf-8")
    new_text, action = UpsertRow(old, args.asset, row)
    catalog.write_text(new_text, encoding="utf-8")
    print(f"catalog {action}: asset={args.asset} -> {catalog}")
    print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
