"""
PAPI-2548：查看 Allure 报告前清空 ``reports/papi2548-allure-results``，再跑 pytest 写入新结果，最后 ``allure serve``。

单独执行 ``allure serve`` 不会触发 pytest 的 ``--clean-alluredir``；本脚本把「只保留一次运行的原始结果」与「打开报告」绑成一条命令。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def GetRepoRoot() -> Path:
    """本文件位于 ``tools/``，仓库根为其父目录。"""
    return Path(__file__).resolve().parent.parent


def RemoveTreeIfExists(path: Path) -> None:
    """删除目录树；不存在则忽略。"""
    if not path.exists():
        return
    if not path.is_dir():
        raise NotADirectoryError(f"期望为目录以便删除: {path}")
    try:
        shutil.rmtree(path)
    except OSError as exc:
        raise RuntimeError(f"无法删除目录（可能被占用或权限不足）: {path}") from exc


def RunPytestPapi2548(*, repo: Path, results_dir: Path) -> int:
    """在仓库根执行 PAPI-2548 pytest，写入 ``results_dir``。"""
    pkg = repo / "api-testcases" / "2026Q2_SP1"
    if not pkg.is_dir():
        raise FileNotFoundError(f"未找到测试包目录: {pkg}")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(pkg.resolve())

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(pkg),
        "-m",
        "not manual",
        f"--alluredir={results_dir.resolve()}",
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(repo.resolve()),
            env=env,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "无法启动 Python/pytest，请确认当前解释器可用。"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"执行 pytest 时发生系统错误: {exc}") from exc
    return int(completed.returncode)


def RunAllureServe(*, results_dir: Path, repo: Path) -> int:
    """调用系统 ``allure serve``。"""
    if not results_dir.is_dir():
        raise FileNotFoundError(f"Allure 结果目录不存在: {results_dir}")
    try:
        next(results_dir.iterdir())
    except StopIteration:
        raise FileNotFoundError(
            f"Allure 结果目录为空，无法 serve: {results_dir}"
        ) from None

    cmd = ["allure", "serve", str(results_dir.resolve())]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(repo.resolve()),
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "未找到 allure 命令。请安装 Allure Commandline 并加入 PATH："
            " https://github.com/allure-framework/allure2/releases"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"执行 allure 时发生系统错误: {exc}") from exc
    return int(completed.returncode)


def ParseArgs(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "默认：删除 reports/papi2548-allure-results 与可选静态报告目录后，"
            "运行 pytest 再 allure serve（每次仅保留本轮结果）。"
        )
    )
    parser.add_argument(
        "--serve-only",
        action="store_true",
        help="不删除、不跑 pytest，仅对当前结果目录执行 allure serve。",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="与默认流程联用时跳过删除结果目录（仍跑 pytest；依赖 pytest --clean-alluredir 清空）。",
    )
    return parser.parse_args(argv)


def Fail(message: str, *, code: int = 1) -> NoReturn:
    print(message, file=sys.stderr)
    sys.exit(code)


def Main(argv: list[str] | None = None) -> int:
    args = ParseArgs(argv)
    repo = GetRepoRoot()
    results_dir = repo / "reports" / "papi2548-allure-results"
    static_report_dir = repo / "reports" / "papi2548-allure-report"

    try:
        if args.serve_only:
            if not results_dir.is_dir():
                Fail(f"结果目录不存在: {results_dir}", code=2)
            code = RunAllureServe(results_dir=results_dir, repo=repo)
            return code

        if not args.no_clean:
            RemoveTreeIfExists(results_dir)
        RemoveTreeIfExists(static_report_dir)

        results_dir.mkdir(parents=True, exist_ok=True)

        pytest_code = RunPytestPapi2548(repo=repo, results_dir=results_dir)
        if pytest_code != 0:
            Fail(f"pytest 退出码 {pytest_code}，已跳过 allure serve。", code=pytest_code)

        return RunAllureServe(results_dir=results_dir, repo=repo)
    except (FileNotFoundError, NotADirectoryError, RuntimeError) as exc:
        Fail(str(exc), code=2)


if __name__ == "__main__":
    raise SystemExit(Main())
