"""
根据生成器 Python/工具 JS 依赖，离线映射受影响的 Apifox 资产。

配置来自 ``.apifox/suites.yaml``；本工具只读仓库文件，不访问 Apifox。
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import ApifoxSuitesYaml


DependencyMap = Dict[Path, Set[Path]]


def RepoRootFromArg(raw: str) -> Path:
    """返回显式仓库根，未提供时按当前脚本位置推导。"""
    if raw.strip():
        root = Path(raw).resolve()
    else:
        root = Path(__file__).resolve().parents[2]
    if not (root / ".apifox" / "suites.yaml").is_file():
        raise FileNotFoundError(f"仓库缺少 .apifox/suites.yaml: {root}")
    return root


def NormalizePath(path: Path) -> Path:
    """生成适用于 Windows 大小写不敏感比较的绝对路径。"""
    return Path(str(path.resolve()).casefold())


def ResolveRepoPath(repo_root: Path, raw: str) -> Path:
    """解析仓库相对路径或绝对路径，并拒绝空路径。"""
    text = raw.strip()
    if not text:
        raise ValueError("路径不能为空")
    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def LoadAssetGenerators(repo_root: Path) -> Dict[str, Path]:
    """读取所有 ``assets.<key>.generator`` 映射。"""
    suites_text = ApifoxSuitesYaml.LoadSuitesText(repo_root)
    result: Dict[str, Path] = {}
    for asset_key in ApifoxSuitesYaml.ListAssetKeys(suites_text):
        fields = ApifoxSuitesYaml.ParseAssetFields(suites_text, asset_key)
        generator = fields.get("generator", "").strip()
        if not generator:
            raise ValueError(f"assets.{asset_key}.generator 未配置")
        generator_path = ResolveRepoPath(repo_root, generator)
        if not generator_path.is_file():
            raise FileNotFoundError(
                f"assets.{asset_key}.generator 不存在: {generator_path}"
            )
        result[asset_key] = generator_path
    return result


def ParseAssetGroups(suites_text: str) -> Dict[str, List[str]]:
    """解析顶层 ``asset_groups`` 下的简单资产列表。"""
    groups: Dict[str, List[str]] = {}
    in_groups = False
    active_group = ""
    for line_number, line in enumerate(suites_text.splitlines(), start=1):
        if line.strip() == "asset_groups:" and not line.startswith(" "):
            in_groups = True
            active_group = ""
            continue
        if not in_groups:
            continue
        if line and not line.startswith(" ") and not line.lstrip().startswith("#"):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  ") and not line.startswith("    ") and stripped.endswith(":"):
            active_group = stripped[:-1].strip()
            if not active_group:
                raise ValueError(f"asset_groups 组名为空，行 {line_number}")
            groups.setdefault(active_group, [])
            continue
        if line.startswith("    - "):
            if not active_group:
                raise ValueError(
                    f"asset_groups 列表项缺少所属组，行 {line_number}"
                )
            asset_key = ApifoxSuitesYaml.UnquoteYamlScalar(
                stripped[2:].strip()
            )
            if not asset_key:
                raise ValueError(f"asset_groups 资产 key 为空，行 {line_number}")
            groups[active_group].append(asset_key)
    return groups


def ValidateAssetGroups(
    groups: Mapping[str, Sequence[str]], known_assets: Iterable[str]
) -> None:
    """校验组内 key 存在且不重复。"""
    known = set(known_assets)
    errors: List[str] = []
    for group_name, asset_keys in groups.items():
        seen: Set[str] = set()
        for asset_key in asset_keys:
            if asset_key not in known:
                errors.append(f"asset_groups.{group_name} 包含未知资产 {asset_key}")
            if asset_key in seen:
                errors.append(f"asset_groups.{group_name} 重复资产 {asset_key}")
            seen.add(asset_key)
    if errors:
        raise ValueError("; ".join(errors))


def _ParsePython(path: Path) -> ast.AST:
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise OSError(f"读取 Python 文件失败: {path}: {exc}") from exc
    try:
        return ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SyntaxError(f"解析 Python 文件失败: {path}: {exc}") from exc


def _ResolveLocalModule(module_name: str, source_dir: Path) -> Optional[Path]:
    top_name = module_name.split(".", 1)[0].strip()
    if not top_name:
        return None
    module_path = source_dir / f"{top_name}.py"
    if module_path.is_file():
        return module_path.resolve()
    package_path = source_dir / top_name / "__init__.py"
    if package_path.is_file():
        return package_path.resolve()
    return None


def _PythonImports(tree: ast.AST, source_dir: Path) -> Set[Path]:
    dependencies: Set[Path] = set()
    for node in ast.walk(tree):
        names: List[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names = [node.module]
            elif node.level == 1 and node.module:
                names = [node.module]
        for module_name in names:
            resolved = _ResolveLocalModule(module_name, source_dir)
            if resolved is not None:
                dependencies.add(resolved)
    return dependencies


def _JsLiteralNames(tree: ast.AST) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Str):
            value = node.s
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
        else:
            continue
        normalized = str(value).strip().replace("\\", "/")
        if normalized.casefold().endswith(".js"):
            names.add(normalized)
    return names


def _ResolveJsLiteral(repo_root: Path, literal: str) -> Set[Path]:
    normalized = literal.replace("\\", "/").lstrip("./")
    candidates: List[Path] = []
    if normalized.startswith("tools/"):
        candidates.append(repo_root / normalized)
    elif "/" in normalized:
        candidates.append(repo_root / normalized)
    else:
        # 当前生成器的 LoadToolsJsLines 约定优先读取 payment-js。
        candidates.extend(
            (
                repo_root / "tools" / "payment-js" / normalized,
                repo_root / "tools" / normalized,
            )
        )
    return {candidate.resolve() for candidate in candidates if candidate.is_file()}


def BuildDependencyMap(repo_root: Path, roots: Iterable[Path]) -> DependencyMap:
    """递归分析本地 Python import 与 Python 中引用的工具 JS。"""
    graph: DependencyMap = {}
    pending: List[Path] = [path.resolve() for path in roots]
    while pending:
        source = pending.pop()
        if source in graph:
            continue
        if not source.is_file():
            raise FileNotFoundError(f"依赖文件不存在: {source}")
        dependencies: Set[Path] = set()
        if source.suffix.casefold() == ".py":
            tree = _ParsePython(source)
            dependencies.update(_PythonImports(tree, source.parent))
            for literal in _JsLiteralNames(tree):
                dependencies.update(_ResolveJsLiteral(repo_root, literal))
        graph[source] = dependencies
        for dependency in sorted(dependencies, key=lambda item: str(item).casefold()):
            if dependency.suffix.casefold() == ".py" and dependency not in graph:
                pending.append(dependency)
    return graph


def CollectTransitiveDependencies(
    root: Path, graph: Mapping[Path, Set[Path]]
) -> Set[Path]:
    """返回入口文件自身及其完整传递依赖闭包。"""
    visited: Set[Path] = set()
    pending: List[Path] = [root.resolve()]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(graph.get(current, set()))
    return visited


def FindAffectedAssets(
    repo_root: Path,
    asset_generators: Mapping[str, Path],
    affected_path: Path,
) -> List[str]:
    """按精确文件或目录匹配，返回依赖闭包命中的资产 key。"""
    graph = BuildDependencyMap(repo_root, asset_generators.values())
    target = NormalizePath(affected_path)
    target_is_directory = affected_path.is_dir()
    affected: List[str] = []
    for asset_key, generator in asset_generators.items():
        dependencies = CollectTransitiveDependencies(generator, graph)
        matched = False
        for dependency in dependencies:
            normalized_dependency = NormalizePath(dependency)
            if normalized_dependency == target:
                matched = True
                break
            if target_is_directory:
                try:
                    normalized_dependency.relative_to(target)
                    matched = True
                    break
                except ValueError:
                    pass
        if matched:
            affected.append(asset_key)
    return sorted(affected)


def BuildArgumentParser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Map generator Python/tools JS changes to Apifox asset keys"
    )
    parser.add_argument("--repo-root", default="")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--affected-by",
        default="",
        metavar="PATH",
        help="输出依赖此仓库文件或目录的资产 key",
    )
    mode.add_argument(
        "--group",
        default="",
        metavar="NAME",
        help="输出 suites.yaml asset_groups.<name> 的资产 key",
    )
    mode.add_argument(
        "--list-assets",
        action="store_true",
        help="输出 suites.yaml 中全部资产 key",
    )
    return parser


def Main(argv: Optional[Sequence[str]] = None) -> int:
    """执行离线映射命令。"""
    parser = BuildArgumentParser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        repo_root = RepoRootFromArg(str(args.repo_root))
        asset_generators = LoadAssetGenerators(repo_root)
        suites_text = ApifoxSuitesYaml.LoadSuitesText(repo_root)
        groups = ParseAssetGroups(suites_text)
        ValidateAssetGroups(groups, asset_generators.keys())
        result: List[str]
        if bool(args.list_assets):
            result = sorted(asset_generators)
        elif str(args.group).strip():
            group_name = str(args.group).strip()
            if group_name not in groups:
                known = ", ".join(sorted(groups)) or "(none)"
                raise KeyError(f"未知资产组 {group_name!r}；可选: {known}")
            result = list(groups[group_name])
        else:
            affected_path = ResolveRepoPath(repo_root, str(args.affected_by))
            if not affected_path.exists():
                raise FileNotFoundError(f"--affected-by 路径不存在: {affected_path}")
            result = FindAffectedAssets(
                repo_root, asset_generators, affected_path
            )
        for asset_key in result:
            print(asset_key)
        return 0
    except (FileNotFoundError, KeyError, OSError, SyntaxError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(Main())
