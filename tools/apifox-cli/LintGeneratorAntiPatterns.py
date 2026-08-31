"""扫描 apifox-cli 生成器中的已知反模式，防止公共逻辑再次 copy。

用法（仓库根目录）::

    python tools/apifox-cli/LintGeneratorAntiPatterns.py

退出码 0 = 通过；1 = 存在未登记的技术债或新增违规。
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Counter as CounterType
from typing import Dict, Final, Iterable, List, Mapping, Sequence, Tuple

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_GENERATORS_DIR: Final[Path] = (
    _REPO_ROOT / "api-testcases" / "api_tests" / "apifox-cli" / "generators"
)

# 已登记技术债：文件名 → 规则 id → 精确允许数量。
# 数量减少也会失败，提醒维护者同步收紧清单；数量增加则直接阻断新债。
_KNOWN_DEBT: Final[Mapping[str, Mapping[str, int]]] = {
    # 独立造 profile 模式，刻意保留 replaceIn。
    "GeneratePostmanCollectionMembershipPurchaseP0.py": {"replace_in_uuid": 1},
}

# 永远不应出现违规的文件（common 正本）
_STRICT_FILES: Final[frozenset[str]] = frozenset(
    {
        "collection_builder_common.py",
        "dining_discount_cli_common.py",
        "epass_cli_common.py",
        "fasttrack_prebooking_common.py",
        "ft_prebooking_payment_common.py",
        "lounge_epass_common.py",
    }
)


@dataclass(frozen=True)
class LintRule:
    RuleId: str
    Pattern: re.Pattern[str]
    Message: str


_RULES: Final[Sequence[LintRule]] = (
    LintRule(
        RuleId="replace_in_uuid",
        Pattern=re.compile(
            r"""pm\.(?:variables|collectionVariables)[^\n]{0,120}replaceIn\(\s*['"]\{\{\$string\.uuid\}\}['"]\s*\)"""
        ),
        Message="禁止 pm.*.replaceIn('{{$string.uuid}}')：CLI 常不展开，应 UnsetVar + 后置 Capture",
    ),
    LintRule(
        RuleId="legacy_client_user_id_get",
        Pattern=re.compile(r"""collectionVariables\.get\(\s*['"]clientUserId['"]\s*\)"""),
        Message="禁止 collectionVariables.get('clientUserId')：应改用 {prefix}GetVar('clientUserId')",
    ),
    LintRule(
        RuleId="inline_capture",
        Pattern=re.compile(r"function\s+\w+CaptureClientUserIdAfterSend\s*\("),
        Message="禁止在生成器内手写 CaptureClientUserIdAfterSend：应使用 collection_builder_common 工厂",
    ),
)


def _RepoRoot() -> Path:
    return _REPO_ROOT


def _GeneratorsDir() -> Path:
    return _GENERATORS_DIR


def _IterGeneratorPyFiles() -> Iterable[Path]:
    root = _GeneratorsDir()
    if not root.is_dir():
        raise FileNotFoundError(f"生成器目录不存在: {root}")
    yield from sorted(root.glob("*.py"))


def _ScanFile(path: Path) -> List[Tuple[int, str, str]]:
    text = path.read_text(encoding="utf-8")
    hits: List[Tuple[int, str, str]] = []
    for rule in _RULES:
        for match in rule.Pattern.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            hits.append((line_no, rule.RuleId, rule.Message))
    return hits


def _ExpectedDebt(file_name: str) -> Mapping[str, int]:
    if file_name in _STRICT_FILES:
        return {}
    return _KNOWN_DEBT.get(file_name, {})


def RunLint() -> int:
    violations: List[str] = []
    debt_details: Dict[str, List[str]] = {name: [] for name in _KNOWN_DEBT}
    try:
        paths = list(_IterGeneratorPyFiles())
        for path in paths:
            file_name = path.name
            hits = _ScanFile(path)
            expected = _ExpectedDebt(file_name)
            actual: CounterType[str] = Counter(rule_id for _, rule_id, _ in hits)

            for rule_id in sorted(set(expected) | set(actual)):
                expected_count = expected.get(rule_id, 0)
                actual_count = actual.get(rule_id, 0)
                if actual_count != expected_count:
                    direction = "新增技术债" if actual_count > expected_count else "债清理后清单未收紧"
                    violations.append(
                        f"{path.relative_to(_RepoRoot())} [{rule_id}] "
                        f"期望命中={expected_count}，实际命中={actual_count}（{direction}）"
                    )

            for line_no, rule_id, message in hits:
                if rule_id in expected:
                    debt_details[file_name].append(f"L{line_no}:{rule_id}")
                else:
                    violations.append(
                        f"{path.relative_to(_RepoRoot())}:{line_no} [{rule_id}] {message}"
                    )
    except (OSError, UnicodeError) as exc:
        print(f"生成器 lint 无法完成：{exc}", file=sys.stderr)
        return 1

    if violations:
        print("生成器反模式 lint 失败：", file=sys.stderr)
        for item in violations:
            print(f"  - {item}", file=sys.stderr)
        print("请优先修复反模式；若已清债，请同步降低 _KNOWN_DEBT 的精确数量。", file=sys.stderr)
        return 1

    print("生成器反模式 lint 通过：未发现超出登记数量的新命中。")
    open_debt = {k: v for k, v in debt_details.items() if v}
    if open_debt:
        print("已登记技术债（命中数量与清单完全一致，待逐项清零）：")
        for file_name, items in sorted(open_debt.items()):
            expected_summary = ", ".join(
                f"{rule_id}={count}" for rule_id, count in sorted(_KNOWN_DEBT[file_name].items())
            )
            print(f"  - {file_name}: {expected_summary}；位置 {', '.join(items)}")
    else:
        print("无已登记技术债。")
    return 0


def Main() -> None:
    raise SystemExit(RunLint())


if __name__ == "__main__":
    Main()
