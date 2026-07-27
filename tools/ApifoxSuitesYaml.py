"""
共享解析 ``.apifox/suites.yaml``（不依赖 PyYAML）。

供 ``ApifoxRepoFirst.ps1``、Upsert、Triage 等共用，避免多套手写解析分叉。

用法::

    python tools/ApifoxSuitesYaml.py --list-keys
    python tools/ApifoxSuitesYaml.py --asset papi_2548 --format json
    python tools/ApifoxSuitesYaml.py --asset papi_2548 --triage-patterns
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence


def RepoRootFromArg(raw: str) -> Path:
    if raw.strip():
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[1]


def SuitesYamlPath(repo_root: Path, override: str = "") -> Path:
    if override.strip():
        return Path(override).resolve()
    return repo_root / ".apifox" / "suites.yaml"


def StripYamlInlineComment(val: str) -> str:
    if "#" not in val:
        return val.strip()
    in_single = False
    in_double = False
    for i, ch in enumerate(val):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return val[:i].strip()
    return val.strip()


def UnquoteYamlScalar(val: str) -> str:
    text = StripYamlInlineComment(val)
    if len(text) >= 2 and (
        (text.startswith('"') and text.endswith('"'))
        or (text.startswith("'") and text.endswith("'"))
    ):
        return text[1:-1]
    return text


def ListAssetKeys(suites_text: str) -> List[str]:
    keys: List[str] = []
    in_assets = False
    for line in suites_text.splitlines():
        if re.match(r"^assets:\s*$", line):
            in_assets = True
            continue
        if not in_assets:
            continue
        if re.match(r"^[A-Za-z_]", line) and not line.startswith(" "):
            break
        m_key = re.match(r"^(\s{2})([A-Za-z0-9_]+):\s*$", line)
        if m_key:
            keys.append(m_key.group(2))
    return keys


def ParseAssetFields(suites_text: str, asset_key: str) -> Dict[str, str]:
    """
    解析 ``assets.<key>`` 下 indent=4 的标量字段。

    空值块（如 ``triage:``）及其更深缩进子项会被跳过，不写入 fields。
    """
    lines = suites_text.splitlines()
    in_assets = False
    in_target = False
    skip_deeper = False
    fields: Dict[str, str] = {"asset_key": asset_key}

    for line in lines:
        if re.match(r"^assets:\s*$", line):
            in_assets = True
            in_target = False
            skip_deeper = False
            continue
        if not in_assets:
            continue
        if re.match(r"^[A-Za-z_]", line) and not line.startswith(" "):
            break
        m_key = re.match(r"^(\s{2})([A-Za-z0-9_]+):\s*$", line)
        if m_key:
            in_target = m_key.group(2) == asset_key
            skip_deeper = False
            continue
        if not in_target:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent >= 6:
            continue
        m_field = re.match(r"^(\s{4})([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m_field:
            continue
        key = m_field.group(2)
        val = UnquoteYamlScalar(m_field.group(3))
        if val == "" or val in ("|", ">"):
            skip_deeper = True
            continue
        skip_deeper = False
        if val in ("null", "~"):
            val = ""
        fields[key] = val

    if "title" not in fields and "generator" not in fields:
        known = ", ".join(ListAssetKeys(suites_text)) or "(none)"
        raise SystemExit(f"asset '{asset_key}' not found under assets:. Known: {known}")
    return fields


def ParseTriageScriptPatterns(suites_text: str, asset_key: str) -> List[str]:
    """解析 ``assets.<key>.triage.script_name_patterns``；未配置则 ``[]``。"""
    lines = suites_text.splitlines()
    in_assets = False
    in_target = False
    in_triage = False
    in_patterns = False
    patterns: List[str] = []

    for line in lines:
        if re.match(r"^assets:\s*$", line):
            in_assets = True
            in_target = False
            in_triage = False
            in_patterns = False
            continue
        if not in_assets:
            continue
        if re.match(r"^[A-Za-z_]", line) and not line.startswith(" "):
            break

        m_key = re.match(r"^(\s{2})([A-Za-z0-9_]+):\s*$", line)
        if m_key:
            in_target = m_key.group(2) == asset_key
            in_triage = False
            in_patterns = False
            continue
        if not in_target:
            continue

        indent = len(line) - len(line.lstrip(" "))
        if indent < 4 and line.strip():
            in_target = False
            in_triage = False
            in_patterns = False
            continue

        stripped = line.strip()
        if indent == 4 and re.match(r"^triage:\s*$", stripped):
            in_triage = True
            in_patterns = False
            continue
        if indent == 4 and stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            if not stripped.startswith("triage:"):
                in_triage = False
                in_patterns = False
            continue
        if not in_triage:
            continue

        if indent == 6 and re.match(r"^script_name_patterns:\s*$", stripped):
            in_patterns = True
            continue
        if indent == 6 and stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            in_patterns = False
            continue
        if not in_patterns:
            continue

        m_item = re.match(r"^-\s+(.*)$", stripped)
        if m_item and indent >= 6:
            pat = UnquoteYamlScalar(m_item.group(1))
            if pat:
                patterns.append(pat)
    return patterns


def LoadSuitesText(repo_root: Path, suites_override: str = "") -> str:
    path = SuitesYamlPath(repo_root, suites_override)
    if not path.is_file():
        raise FileNotFoundError(f"suites.yaml not found: {path}")
    return path.read_text(encoding="utf-8")


def BuildCatalogDocCell(repo_root: Path, fields: Dict[str, str], asset_key: str) -> str:
    """
    catalog「详解」列：优先 ``doc``（相对仓库根的 md），再加 ``suites/<key>.md`` 笔记链。
    """
    suite_note = f"[笔记](./suites/{asset_key}.md)"
    doc_rel = (fields.get("doc") or "").strip().replace("\\", "/")
    if not doc_rel:
        return suite_note
    doc_path = (repo_root / doc_rel).resolve()
    catalog_dir = (repo_root / ".cursor" / "skills" / "apifox-cli-repo-first").resolve()
    try:
        rel = Path(os_path_rel(doc_path, catalog_dir)).as_posix()
    except ValueError:
        rel = f"../../../{doc_rel}"
    if not rel.startswith("."):
        rel = "./" + rel
    return f"[详解]({rel}) / {suite_note}"


def os_path_rel(target: Path, start: Path) -> str:
    import os

    return os.path.relpath(str(target), str(start))


def Main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Parse .apifox/suites.yaml (shared)")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--suites", default="", help="override suites.yaml path")
    parser.add_argument("--list-keys", action="store_true")
    parser.add_argument("--asset", default="")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument(
        "--triage-patterns",
        action="store_true",
        help="print script_name_patterns for --asset (one per line)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    repo = RepoRootFromArg(args.repo_root)
    text = LoadSuitesText(repo, args.suites)

    if args.list_keys:
        for key in ListAssetKeys(text):
            print(key)
        return 0

    if not args.asset.strip():
        raise SystemExit("--asset is required unless --list-keys")

    if args.triage_patterns:
        for pat in ParseTriageScriptPatterns(text, args.asset.strip()):
            print(pat)
        return 0

    fields = ParseAssetFields(text, args.asset.strip())
    if args.format == "json":
        print(json.dumps(fields, ensure_ascii=False))
    else:
        for k, v in sorted(fields.items()):
            print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(Main())
