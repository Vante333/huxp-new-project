"""从 MCP 已拉取的 Apifox OAS 快照落盘（由 Agent 调用 MCP 后传入 JSON 文件路径）。

用法::

    python tools/data-check/export_q2_local_offer_oas.py --main-oas <main.json> --refs <refs.json>

``--refs`` 为 ``read_project_oas_ref_resources`` 返回的 dict JSON。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

JsonDict = Dict[str, Any]

LOCAL_OFFER_KEYWORDS = (
    "localoffer",
    "local offer",
    "epass",
    "e-pass",
    "epasses",
)


def _RepoRoot() -> Path:
    return Path(__file__).resolve().parents[2]


def _LoadJson(path: Path) -> JsonDict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"无法读取 JSON 文件: {path}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON 解析失败: {path}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"期望 JSON 对象为 dict: {path}")
    return data


def _WriteJson(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _IsLocalOfferRelated(path: str, summary: str) -> bool:
    blob = f"{path} {summary}".lower()
    return any(kw in blob for kw in LOCAL_OFFER_KEYWORDS)


def _ExtractPathSummaries(main_oas: Mapping[str, Any]) -> List[Tuple[str, str, str]]:
    paths = main_oas.get("paths")
    if not isinstance(paths, dict):
        return []
    rows: List[Tuple[str, str, str]] = []
    for path, spec in paths.items():
        if not isinstance(spec, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete", "head", "options"):
            op = spec.get(method)
            if not isinstance(op, dict):
                continue
            summary = str(op.get("summary") or "").strip()
            rows.append((method.upper(), path, summary))
    return rows


def _BuildMarkdownSummary(
    main_oas: Mapping[str, Any],
    refs: Mapping[str, Any],
    *,
    download_time: str,
) -> str:
    info = main_oas.get("info")
    title = "DragonPass API"
    version = ""
    if isinstance(info, dict):
        title = str(info.get("title") or title).strip()
        version = str(info.get("version") or "").strip()

    all_rows = _ExtractPathSummaries(main_oas)
    lo_rows = [r for r in all_rows if _IsLocalOfferRelated(r[1], r[2])]

    lines: List[str] = [
        "# Q2 Local Offer — Apifox OpenAPI 快照",
        "",
        f"- **来源 MCP**：`Q2 local offer`（Apifox ProjectId `345747`，BranchId `309401`）",
        f"- **拉取时间**：{download_time}",
        f"- **OpenAPI**：{title} v{version}",
        f"- **接口总数**：{len(all_rows)}",
        f"- **Local Offer / E-pass 相关**：{len(lo_rows)}",
        "",
        "## Local Offer / E-pass 相关接口",
        "",
        "| 方法 | 路径 | 摘要 |",
        "| --- | --- | --- |",
    ]
    for method, path, summary in lo_rows:
        lines.append(f"| {method} | `{path}` | {summary} |")

    lines.extend(
        [
            "",
            "## 已落盘 $ref 明细文件",
            "",
        ]
    )
    for ref_path in sorted(refs.keys()):
        lines.append(f"- `{ref_path}`")

    lines.extend(
        [
            "",
            "## 全量接口索引",
            "",
            "| 方法 | 路径 | 摘要 |",
            "| --- | --- | --- |",
        ]
    )
    for method, path, summary in all_rows:
        lines.append(f"| {method} | `{path}` | {summary} |")

    lines.append("")
    return "\n".join(lines)


def ExportQ2LocalOfferOas(main_oas_path: Path, refs_path: Path, output_dir: Path) -> None:
    main_oas = _LoadJson(main_oas_path)
    refs = _LoadJson(refs_path)

    info = main_oas.get("info")
    download_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(info, dict) and info.get("x-download-time"):
        download_time = str(info["x-download-time"])

    _WriteJson(output_dir / "openapi.json", main_oas)

    paths_dir = output_dir / "paths"
    for ref_key, ref_body in refs.items():
        safe_name = ref_key.lstrip("/").replace("/", "__")
        _WriteJson(paths_dir / safe_name, ref_body)

    summary_md = _BuildMarkdownSummary(main_oas, refs, download_time=download_time)
    (output_dir / "README.md").write_text(summary_md, encoding="utf-8")

    print(f"已导出至: {output_dir}")
    print(f"  openapi.json + {len(refs)} 个 path 明细 + README.md")


def _ParseArgs(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="落盘 Q2 Local Offer Apifox OAS 快照")
    default_out = _RepoRoot() / "tech-docs" / "2026Q2_SP3" / "apifox-oas-q2-local-offer"
    parser.add_argument("--main-oas", type=Path, required=True, help="read_project_oas 返回的 JSON 文件")
    parser.add_argument("--refs", type=Path, required=True, help="read_project_oas_ref_resources 返回的 JSON 文件")
    parser.add_argument("--output-dir", type=Path, default=default_out, help="输出目录")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _ParseArgs(argv)
    try:
        ExportQ2LocalOfferOas(args.main_oas, args.refs, args.output_dir)
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
