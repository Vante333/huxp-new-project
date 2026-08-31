"""离线检查 ``.apifox/suites.yaml`` 中可 Push 资产的配置完整性。

本工具复用 ``ApifoxSuitesYaml.py`` 的共享解析逻辑，不访问网络。缺少场景 ID 的草稿资产、
允许为空的 Environment 等以 warning 呈现；会导致 Generate/Push 不可用的问题以 error 阻断。
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional, Sequence, Tuple

from ApifoxSuitesYaml import ListAssetKeys, LoadSuitesText, ParseAssetFields, RepoRootFromArg


@dataclass(frozen=True)
class LintFinding:
    Level: str
    AssetKey: str
    Field: str
    Message: str


_ALLOWED_PUSH_MODES: Tuple[str, ...] = ("http", "customHttp", "raw")
_TRUE_VALUES: Tuple[str, ...] = ("true", "1", "yes")
_FALSE_VALUES: Tuple[str, ...] = ("false", "0", "no")


def _ParsePositiveInt(raw: str) -> Optional[int]:
    text = raw.strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        return None
    return value if value > 0 else None


def _ResolveRepoPath(repo_root: Path, raw: str) -> Optional[Path]:
    text = raw.strip()
    if not text:
        return None
    candidate = Path(text)
    resolved = candidate.resolve() if candidate.is_absolute() else (repo_root / candidate).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    return resolved


def _Add(
    findings: List[LintFinding],
    level: str,
    asset_key: str,
    field: str,
    message: str,
) -> None:
    findings.append(
        LintFinding(Level=level, AssetKey=asset_key, Field=field, Message=message)
    )


def LintAsset(
    repo_root: Path,
    asset_key: str,
    fields: Mapping[str, str],
) -> List[LintFinding]:
    """检查单个资产并返回稳定排序前的发现列表。"""
    findings: List[LintFinding] = []

    for field, suffix in (("generator", ".py"), ("collection", ".json")):
        raw = fields.get(field, "")
        resolved = _ResolveRepoPath(repo_root, raw)
        if not raw.strip():
            _Add(findings, "error", asset_key, field, "必填路径为空")
        elif resolved is None:
            _Add(findings, "error", asset_key, field, "路径必须位于仓库内")
        elif resolved.suffix.lower() != suffix:
            _Add(findings, "error", asset_key, field, f"文件扩展名必须为 {suffix}")
        elif not resolved.is_file():
            _Add(findings, "error", asset_key, field, f"文件不存在：{resolved}")

    scenario_raw = fields.get("test_scenario_id", "")
    scenario_id = _ParsePositiveInt(scenario_raw)
    if scenario_raw.strip() and scenario_id is None:
        _Add(findings, "error", asset_key, "test_scenario_id", "必须为正整数或合法 null")
    if scenario_id is None:
        _Add(
            findings,
            "warning",
            asset_key,
            "test_scenario_id",
            "未配置场景 ID：视为仅 Generate 的草稿资产，不可 Push",
        )
        return findings

    working_branch = fields.get("working_branch", "").strip()
    if not working_branch:
        _Add(findings, "error", asset_key, "working_branch", "可 Push 资产必须配置工作分支")
    elif not working_branch.startswith("ai/"):
        _Add(
            findings,
            "warning",
            asset_key,
            "working_branch",
            f"工作分支不是约定的 ai/*：{working_branch}",
        )

    push_mode = fields.get("push_mode", "").strip()
    if not push_mode:
        _Add(
            findings,
            "error",
            asset_key,
            "push_mode",
            "可 Push 资产必须显式配置 push_mode，禁止依赖脚本默认值",
        )
    elif push_mode not in _ALLOWED_PUSH_MODES:
        _Add(
            findings,
            "error",
            asset_key,
            "push_mode",
            f"仅允许 {', '.join(_ALLOWED_PUSH_MODES)}，实际为 {push_mode}",
        )

    unbind_raw = fields.get("unbind_after_push", "").strip().lower()
    if not unbind_raw:
        _Add(
            findings,
            "error",
            asset_key,
            "unbind_after_push",
            "可 Push 资产必须显式配置 true/false",
        )
    elif unbind_raw not in _TRUE_VALUES + _FALSE_VALUES:
        _Add(findings, "error", asset_key, "unbind_after_push", "仅允许 true/false")
    elif push_mode == "http" and unbind_raw not in _TRUE_VALUES:
        _Add(
            findings,
            "error",
            asset_key,
            "unbind_after_push",
            "http 模式必须为 true，确保 UI 参数值可见且可调试",
        )
    elif push_mode != "http" and unbind_raw in _TRUE_VALUES:
        _Add(
            findings,
            "error",
            asset_key,
            "unbind_after_push",
            "只有 http 模式支持解绑",
        )

    environment_raw = fields.get("environment_id", "")
    if environment_raw.strip() and _ParsePositiveInt(environment_raw) is None:
        _Add(findings, "error", asset_key, "environment_id", "必须为正整数或合法 null")
    elif not environment_raw.strip():
        _Add(
            findings,
            "warning",
            asset_key,
            "environment_id",
            "未配置环境 ID：允许 Push，但不能直接 Run",
        )

    return findings


def RunLint(
    repo_root: Path,
    suites_override: str = "",
    asset_filter: str = "",
) -> int:
    """检查 suites 配置；有 error 返回 1，仅 warning 返回 0。"""
    try:
        text = LoadSuitesText(repo_root, suites_override)
        keys = ListAssetKeys(text)
        if not keys:
            print("suites.yaml lint 失败：assets 下没有任何资产。", file=sys.stderr)
            return 1
        if len(keys) != len(set(keys)):
            print("suites.yaml lint 失败：存在重复资产 key。", file=sys.stderr)
            return 1
        if asset_filter:
            if asset_filter not in keys:
                print(f"suites.yaml lint 失败：未知资产 {asset_filter}。", file=sys.stderr)
                return 1
            keys = [asset_filter]

        findings: List[LintFinding] = []
        for key in keys:
            findings.extend(LintAsset(repo_root, key, ParseAssetFields(text, key)))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"suites.yaml lint 无法完成：{exc}", file=sys.stderr)
        return 1

    errors = sorted(
        (item for item in findings if item.Level == "error"),
        key=lambda item: (item.AssetKey, item.Field, item.Message),
    )
    warnings = sorted(
        (item for item in findings if item.Level == "warning"),
        key=lambda item: (item.AssetKey, item.Field, item.Message),
    )
    if errors:
        print(f"suites.yaml lint 失败：{len(errors)} 个错误。", file=sys.stderr)
        for item in errors:
            print(
                f"  - [错误] assets.{item.AssetKey}.{item.Field}: {item.Message}",
                file=sys.stderr,
            )
    else:
        print(f"suites.yaml lint 通过：已检查 {len(keys)} 个资产。")
    for item in warnings:
        print(f"  - [警告] assets.{item.AssetKey}.{item.Field}: {item.Message}")
    return 1 if errors else 0


def Main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="离线检查 .apifox/suites.yaml")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--suites", default="", help="覆盖 suites.yaml 路径")
    parser.add_argument("--asset", default="", help="只检查一个资产")
    args = parser.parse_args(list(argv) if argv is not None else None)
    return RunLint(
        RepoRootFromArg(str(args.repo_root)),
        str(args.suites),
        str(args.asset).strip(),
    )


if __name__ == "__main__":
    raise SystemExit(Main())
