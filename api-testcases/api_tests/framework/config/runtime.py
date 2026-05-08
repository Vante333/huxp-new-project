from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_PROFILE_SAFE = re.compile(r"^[a-zA-Z0-9_-]+$")
# 凭据别名会被拼进环境变量名（如 ``DP_EPASS_CLIENT_ID``），因此只允许安全字符。
_CREDENTIAL_ALIAS_SAFE = re.compile(r"^[a-zA-Z0-9_]+$")
_ENV_INITIALIZED = False


def RepoRoot() -> Path:
    return Path(__file__).resolve().parents[4]


def ParseDotenvLine(line: str) -> Optional[Tuple[str, str]]:
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
    return key, val


def ApplyDotenvFile(path: Path, *, overwrite: bool) -> None:
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return
    for line in raw.splitlines():
        parsed = ParseDotenvLine(line)
        if parsed is None:
            continue
        key, val = parsed
        if overwrite or key not in os.environ:
            os.environ[key] = val


def ProfileSegmentSafe(segment: str) -> bool:
    return bool(segment) and _PROFILE_SAFE.match(segment) is not None


def ApplyProfileNameFromLocalProfileFile(root: Path) -> None:
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
        segment = line.strip()
        if not segment or segment.startswith("#"):
            continue
        if ProfileSegmentSafe(segment):
            os.environ["DP_PROFILE"] = segment
        return


def ApplyCredentialAliasSelection() -> None:
    """
    将 ``DP_CREDENTIAL_ALIAS`` 指向的三件套映射到标准 ``DP_*`` 变量。

    设计目标：同一个 ``env/.env.<profile>`` 可以放多套凭据，但业务代码仍只读取
    ``DP_PROGRAM_ID`` / ``DP_CLIENT_ID`` / ``DP_CLIENT_SECRET``，避免每个接口都额外传 alias。

    例如 ``DP_CREDENTIAL_ALIAS=EPASS`` 时读取
    ``DP_EPASS_PROGRAM_ID`` / ``DP_EPASS_CLIENT_ID`` / ``DP_EPASS_CLIENT_SECRET``，
    并覆盖进程内 ``DP_PROGRAM_ID`` / ``DP_CLIENT_ID`` / ``DP_CLIENT_SECRET``。

    加载时机：根目录 ``.env`` 与 ``env/.env.<profile>`` 都加载完成后执行，因此 profile
    文件里的 ``DP_CREDENTIAL_ALIAS`` 与 ``DP_<ALIAS>_*`` 会生效。

    错误路径：只要设置了 alias，就要求对应三件套全部存在；否则立即抛出明确异常，
    避免误用旧 ``DP_*`` 凭据导致接口串环境。
    """
    raw_alias = os.environ.get("DP_CREDENTIAL_ALIAS", "").strip()
    if not raw_alias:
        return
    if _CREDENTIAL_ALIAS_SAFE.match(raw_alias) is None:
        raise RuntimeError(
            f"DP_CREDENTIAL_ALIAS 非法: {raw_alias!r}，仅允许字母、数字、下划线"
        )
    alias = raw_alias.upper()
    # field 是 alias 变量后缀；canonical_name 是现有代码统一读取的标准变量名。
    mapping = (
        ("PROGRAM_ID", "DP_PROGRAM_ID"),
        ("CLIENT_ID", "DP_CLIENT_ID"),
        ("CLIENT_SECRET", "DP_CLIENT_SECRET"),
    )
    resolved: Dict[str, str] = {}
    missing: List[str] = []
    for field, canonical_name in mapping:
        source_name = f"DP_{alias}_{field}"
        value = os.environ.get(source_name, "").strip()
        if not value:
            missing.append(source_name)
            continue
        resolved[canonical_name] = value
    if missing:
        raise RuntimeError(
            f"已设置 DP_CREDENTIAL_ALIAS={alias!r}，但缺少环境变量: {', '.join(missing)}"
        )
    # 统一写回大写 alias，便于 Allure/调试输出看到规范化后的选择值。
    os.environ["DP_CREDENTIAL_ALIAS"] = alias
    # 覆盖标准三件套后，GetAccessToken/BuildCommonHeaders 等既有代码无需感知 alias。
    for canonical_name, value in resolved.items():
        os.environ[canonical_name] = value


def InitializeRuntimeEnv() -> None:
    global _ENV_INITIALIZED
    if _ENV_INITIALIZED:
        return
    root = RepoRoot()
    ApplyDotenvFile(root / ".env", overwrite=False)
    ApplyProfileNameFromLocalProfileFile(root)
    profile = os.environ.get("DP_PROFILE", "").strip()
    if ProfileSegmentSafe(profile):
        ApplyDotenvFile(root / "env" / f".env.{profile}", overwrite=True)
    # 必须在 profile 文件之后执行：同一环境内的多套三件套通常写在 env/.env.<profile>。
    ApplyCredentialAliasSelection()
    if profile.lower() == "canary" and not os.environ.get("DP_X_VERSION", "").strip():
        os.environ["DP_X_VERSION"] = "canary"
    _ENV_INITIALIZED = True


def EnvTruthy(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class RuntimeSettings:
    profile: str
    dataset_key: str
    base_url: str
    x_version: str


def LoadRuntimeSettings() -> RuntimeSettings:
    InitializeRuntimeEnv()
    return RuntimeSettings(
        profile=os.environ.get("DP_PROFILE", "").strip(),
        dataset_key=os.environ.get("DP_TEST_DATASET", "").strip(),
        base_url=os.environ.get("DP_BASE_URL", "").strip(),
        x_version=os.environ.get("DP_X_VERSION", "").strip(),
    )
