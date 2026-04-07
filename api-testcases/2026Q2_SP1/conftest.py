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


def _ApplyProfileNameFromLocalProfileFile(root: Path) -> None:
    """
    当进程与根 ``.env`` 均未设置 ``DP_PROFILE`` 时，读取 ``env/.local_profile``：
    首条非空、非 ``#`` 注释行作为 profile 名，写入 ``os.environ``（与 ``env/.env.<profile>`` 配套）。

    这样本地可只维护 ``env/.local_profile``（内容为 ``canary`` 等），无需每次在 PowerShell 里执行
    ``$env:DP_PROFILE = "canary"``。已在环境中显式设置 ``DP_PROFILE`` 时本逻辑不生效。
    """
    if os.environ.get("DP_PROFILE", "").strip():
        return
    path = root / "env" / ".local_profile"
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        seg = line.strip()
        if not seg or seg.startswith("#"):
            continue
        if _ProfileSegmentSafe(seg):
            os.environ["DP_PROFILE"] = seg
        return


def _LoadAllDotenvLayers() -> None:
    """
    分层加载环境变量：
    1. 仓库根目录 ``.env``（不覆盖已在进程环境中的键）；
    2. 若 ``DP_PROFILE`` 仍为空，尝试 ``env/.local_profile`` 首行指定 profile；
    3. 若 ``DP_PROFILE`` 合法且存在 ``env/.env.<profile>``，则加载该文件并**覆盖**同名键。
    4. 若 profile 为 ``canary``（大小写不敏感）且仍未设置 ``DP_X_VERSION``，默认 ``canary``，
       以发送 ``x-version: canary``（与 ``BuildCommonHeaders`` 一致）；显式配置或 ``omit`` 等仍优先。
    """
    root = _RepoRoot()
    _ApplyDotenvFile(root / ".env", overwrite=False)
    _ApplyProfileNameFromLocalProfileFile(root)
    profile = os.environ.get("DP_PROFILE", "").strip()
    if _ProfileSegmentSafe(profile):
        prof_path = root / "env" / f".env.{profile}"
        _ApplyDotenvFile(prof_path, overwrite=True)
    if profile.lower() == "canary" and not os.environ.get("DP_X_VERSION", "").strip():
        os.environ["DP_X_VERSION"] = "canary"


_LoadAllDotenvLayers()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "manual: 需人工/外部系统观测，默认不跑")
    config.addinivalue_line("markers", "needs_extensions_read: 依赖 search/register 返回 extensions")
    config.addinivalue_line("markers", "needs_extensions_write: 依赖 PATCH /v2/memberships/extensions 可用")
    config.addinivalue_line(
        "markers",
        "needs_cross_module_data: PAPI-2515 读侧数据依赖（含注册造数的 doc gap 等；非必等于环境变量探测）",
    )
    config.addinivalue_line(
        "markers",
        "p2515_probe_membership: 仅读探测会籍，需 DP_P2515_PROBE_MEMBERSHIP_ID；"
        "本地默认不收集，需 DP_P2515_INCLUDE_PROBE=1",
    )
    config.addinivalue_line(
        "markers",
        "needs_cross_module_write: PAPI-2515 写链路，注册+entitlements/update+按池 update，会改写沙箱权益数值",
    )
    config.addinivalue_line(
        "markers",
        "needs_p2424_usage_order_id: PAPI-2424 回归用例，依赖环境变量 DP_P2424_USAGE_ORDER_ID（非 MS 开头 usage 订单号）",
    )


def _EnvTruthy(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def pytest_collection_modifyitems(config: pytest.Config, items: list) -> None:
    """
    本地默认不收集 ``p2515_probe_membership``（避免维护 ``DP_P2515_PROBE_MEMBERSHIP_ID`` 仍出现 Skipped 条）。
    显式开启：``DP_P2515_INCLUDE_PROBE=1``（须同时配置探测会籍 ID）。
    """
    if _EnvTruthy("DP_P2515_INCLUDE_PROBE"):
        return
    items[:] = [it for it in items if it.get_closest_marker("p2515_probe_membership") is None]


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

