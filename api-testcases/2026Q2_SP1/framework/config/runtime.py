from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

_PROFILE_SAFE = re.compile(r"^[a-zA-Z0-9_-]+$")
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
