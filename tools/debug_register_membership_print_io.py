"""
一次性调试：调用 POST /v2/memberships，在标准输出打印请求入参与响应出参。

环境加载与套件一致：将 ``api-testcases/2026Q2_SP1`` 加入 ``sys.path`` 后导入 ``conftest``（会执行分层 ``.env``）。

**为何没有 ``x-version``**：仅当 ``DP_X_VERSION`` 非空且非 ``omit/none/off`` 时才会加该头。
``DP_X_VERSION`` 来自根目录 ``.env``、或 **加载** ``env/.env.<profile>``（例如 canary 文件里的配置）、
或在 ``DP_PROFILE`` 为 ``canary`` 时由 ``conftest`` 默认补 ``canary``。
若未设置 ``DP_PROFILE``（且根 ``.env`` 也未写 ``DP_X_VERSION``），**不会**读取 ``env/.env.canary``，
也就没有 ``x-version``。

**``.local_profile`` 何时生效**：仅当加载根 ``.env`` 之后 ``DP_PROFILE`` **仍为空** 时，才会读 ``env/.local_profile``。
若根 ``.env``、终端或系统环境里已有 ``DP_PROFILE=uat`` 等，**会完全忽略** ``.local_profile``。
此时要么删掉/改掉根 ``.env`` 里的 ``DP_PROFILE``，要么显式改为 ``DP_PROFILE=canary``，
或直接在根 ``.env`` 写 ``DP_X_VERSION=canary``。

用法（仓库根目录，PowerShell）::

    python tools/debug_register_membership_print_io.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


def _ReadLocalProfileFirstSegment(root: Path) -> Optional[str]:
    """与 conftest 一致：首条非空、非 ``#`` 行；不存在或读失败则 ``None``。"""
    path = root / "env" / ".local_profile"
    if not path.is_file():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in raw.splitlines():
        seg = line.strip()
        if not seg or seg.startswith("#"):
            continue
        return seg
    return None


def _EnsureSuitePathAndLoadEnv() -> None:
    root = Path(__file__).resolve().parent.parent
    suite = root / "api-testcases" / "2026Q2_SP1"
    if not suite.is_dir():
        raise RuntimeError(f"未找到套件目录: {suite}")
    sys.path.insert(0, str(suite))
    import conftest  # noqa: F401  pylint: disable=unused-import  # 触发 _LoadAllDotenvLayers


def DebugPrintRegisterMembershipIo() -> None:
    _EnsureSuitePathAndLoadEnv()

    import requests

    from papi2515_helpers import BuildP2515RegisterPayload
    from papi2548_helpers import (
        BuildCommonHeaders,
        GetAccessToken,
        GetBaseUrl,
        MaskHeadersForLog,
    )

    print("=== conftest 加载后的关键变量（核对为何无 x-version）===")
    effective = os.environ.get("DP_PROFILE", "").strip()
    print("DP_PROFILE:", repr(effective))
    print("DP_X_VERSION:", repr(os.environ.get("DP_X_VERSION", "")))
    repo_root = Path(__file__).resolve().parent.parent
    local_seg = _ReadLocalProfileFirstSegment(repo_root)
    if local_seg and local_seg != effective:
        print()
        print(
            f"提示: env/.local_profile 首条 profile 为 {local_seg!r}，但当前 DP_PROFILE={effective!r}。"
        )
        print(
            "      根目录 .env 或终端/系统环境已设置 DP_PROFILE 时，不会读取 .local_profile（见 conftest）。"
        )
        print("      处理: 编辑根 .env 去掉或改为 DP_PROFILE=canary，或关闭终端里的 $env:DP_PROFILE。")
    print()

    token = GetAccessToken()
    payload = BuildP2515RegisterPayload()
    base = GetBaseUrl().rstrip("/")
    url = f"{base}/v2/memberships"
    headers = BuildCommonHeaders(token)

    print("=== POST /v2/memberships 调试（与 P2515 自动造数注册体一致）===\n")
    print("URL:", url)
    print("Headers（Authorization 已脱敏）:")
    print(json.dumps(MaskHeadersForLog(headers), ensure_ascii=False, indent=2))
    print("\nRequest JSON body:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60.0)
    except requests.RequestException as exc:
        print("\n=== 请求异常 ===")
        print(f"{type(exc).__name__}: {exc}")
        raise SystemExit(2) from exc

    print("\n=== Response ===")
    print("HTTP status:", resp.status_code)
    ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    print("Content-Type:", ct or "(none)")
    text = resp.text
    try:
        parsed: Any = resp.json()
        print("Body (JSON):")
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    except ValueError:
        print("Body (raw text, 前 8000 字符):")
        print(text[:8000] if text else "(empty)")


def main() -> None:
    DebugPrintRegisterMembershipIo()


if __name__ == "__main__":
    main()
