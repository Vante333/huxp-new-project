"""PAPI-2548 测试配置与会话级能力探测。"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Tuple

import pytest

_PROFILE_SAFE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _RepoRoot() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _ParseDotenvLine(line: str) -> Optional[Tuple[str, str]]:
    s = line.strip()
    if not s or s.startswith("#") or "=" not in s:
        return None
    key, _, val = s.partition("=")
    key = key.strip()
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    if not key:
        return None
    return (key, val)


def _ApplyDotenvFile(path: Path, *, overwrite: bool) -> None:
    """
    解析 ``.env`` 风格文件并写入 ``os.environ``。
    ``overwrite=False``：仅当键尚不存在时写入（根 ``.env``）。
    ``overwrite=True``：文件中出现的键一律覆盖（profile 层）。
    """
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        tup = _ParseDotenvLine(line)
        if tup is None:
            continue
        key, val = tup
        if overwrite or key not in os.environ:
            os.environ[key] = val


def _ProfileSegmentSafe(segment: str) -> bool:
    """防止路径穿越：profile 名仅允许字母数字、下划线、连字符。"""
    return bool(segment) and _PROFILE_SAFE.match(segment) is not None


def _LoadAllDotenvLayers() -> None:
    """
    分层加载环境变量：
    1. 仓库根目录 ``.env``（不覆盖已在进程环境中的键）；
    2. 若 ``DP_PROFILE`` 合法且存在 ``env/.env.<profile>``，则加载该文件并**覆盖**同名键。
    """
    root = _RepoRoot()
    _ApplyDotenvFile(root / ".env", overwrite=False)
    profile = os.environ.get("DP_PROFILE", "").strip()
    if not _ProfileSegmentSafe(profile):
        return
    prof_path = root / "env" / f".env.{profile}"
    _ApplyDotenvFile(prof_path, overwrite=True)


_LoadAllDotenvLayers()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "manual: 需人工/外部系统观测，默认不跑")
    config.addinivalue_line("markers", "needs_extensions_read: 依赖 search/register 返回 extensions")
    config.addinivalue_line("markers", "needs_extensions_write: 依赖 PATCH /v2/memberships/extensions 可用")


@pytest.fixture(autouse=True)
def _ResetAllureAssertionAttachmentCounterPerTest() -> None:
    """避免 Allure 中断言附件同名覆盖：每条用例从序号 1 重新计数。"""
    from papi2548_helpers import ResetAllureAssertionAttachmentCounter

    ResetAllureAssertionAttachmentCounter()
    yield


@pytest.fixture
def ScenarioSteps():
    """用例内 HTTP 步骤序号：步骤1/2… 与序列码 S01/S02…，见 ``AllureHttpScenarioSteps``。"""
    from papi2548_helpers import AllureHttpScenarioSteps

    return AllureHttpScenarioSteps()


@pytest.fixture(scope="session")
def papi2548_sandbox_flags():
    from papi2548_helpers import BuildSandboxFlags, GetAccessToken, Papi2548SandboxFlags

    try:
        token = GetAccessToken()
    except Exception as exc:
        pytest.skip(f"无法获取 token，跳过会话探测: {exc}")
    flags: Papi2548SandboxFlags = BuildSandboxFlags(token)
    return flags

