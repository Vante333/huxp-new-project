"""并发调用 POST /v2/orders/payments，断言多次响应字段一致。

默认要求 **全部字段**（含 validUntil）一致；设 ``DP_PAYMENTS_IGNORE_VALID_UNTIL=1`` 时忽略 validUntil / vaildUntil。

用法（仓库根目录）::

    python tools/run_orders_payments_concurrent_assert.py

可通过环境变量覆盖默认请求参数。
"""
from __future__ import annotations

import copy
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

_DEFAULT_URL = "https://developer-sandbox.dragonpass.com/api/v2/orders/payments"
_DEFAULT_TOKEN = (
    "eyJraWQiOiJrZXlfMjAyMzAxMDFfMjA5OTAxMDFfYSIsInR5cCI6IkpXVCIsImFsZyI6IkhTMjU2In0."
    "eyJpc3MiOiJPV1lYSlVYS0hQSlpIVFVLSVJXTiIsImV4cCI6MTc4MzkxNTQzMH0."
    "gquf_mbzrc_urCAeUSJZCwCn-O8IDJRliyNX-L5XBR8"
)
_DEFAULT_PROGRAM_ID = "1919256841868288"
_DEFAULT_BODY: Dict[str, str] = {
    "orderId": "SL20260713BD2KAIC",
    "paymentMethod": "H5_CASHIER",
    "returnUrl": "https://quanyi-aws.dragonpass.com.cn/#/system/tenantApiMgmt",
}
_VALID_UNTIL_KEYS: Set[str] = {"validUntil", "vaildUntil"}
_CONCURRENCY = 20


def _EnvBool(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"环境变量 {name} 须为布尔值，当前值: {raw!r}")


def _EnvInt(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"环境变量 {name} 须为整数，当前值: {raw!r}") from exc


def _StripValidUntil(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _StripValidUntil(inner)
            for key, inner in value.items()
            if key not in _VALID_UNTIL_KEYS
        }
    if isinstance(value, list):
        return [_StripValidUntil(item) for item in value]
    return value


def _PostPaymentOnce(
    *,
    url: str,
    token: str,
    program_id: str,
    body: Dict[str, str],
    index: int,
    timeout_sec: float,
) -> Tuple[int, int, Optional[Dict[str, Any]], Optional[str]]:
    headers = {
        "x-version": os.getenv("DP_X_VERSION", "canary").strip() or "canary",
        "X-Program-ID": program_id,
        "X-Request-ID": str(uuid.uuid4()),
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "*/*",
    }
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout_sec)
    except requests.RequestException as exc:
        return index, 0, None, f"请求异常: {exc}"

    try:
        payload = resp.json()
    except ValueError:
        return index, resp.status_code, None, f"响应非 JSON: {resp.text[:500]}"

    if not isinstance(payload, dict):
        return index, resp.status_code, None, f"响应根节点非对象: {type(payload).__name__}"

    return index, resp.status_code, payload, None


def _CollectValidUntilPaths(value: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    found: List[Tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, inner in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if key in _VALID_UNTIL_KEYS:
                found.append((path, inner))
            found.extend(_CollectValidUntilPaths(inner, path))
    elif isinstance(value, list):
        for idx, item in enumerate(value):
            found.extend(_CollectValidUntilPaths(item, f"{prefix}[{idx}]"))
    return found


def RunConcurrentPaymentsAssert() -> int:
    url = os.getenv("DP_PAYMENTS_URL", _DEFAULT_URL).strip() or _DEFAULT_URL
    token = os.getenv("DP_ACCESS_TOKEN", _DEFAULT_TOKEN).strip() or _DEFAULT_TOKEN
    program_id = os.getenv("DP_PROGRAM_ID", _DEFAULT_PROGRAM_ID).strip() or _DEFAULT_PROGRAM_ID
    concurrency = _EnvInt("DP_PAYMENTS_CONCURRENCY", _CONCURRENCY)
    timeout_sec = float(os.getenv("DP_HTTP_TIMEOUT_SEC", "30").strip() or "30")

    body = copy.deepcopy(_DEFAULT_BODY)
    body["orderId"] = os.getenv("DP_PAYMENTS_ORDER_ID", body["orderId"]).strip() or body["orderId"]
    body["paymentMethod"] = os.getenv("DP_PAYMENTS_METHOD", body["paymentMethod"]).strip() or body["paymentMethod"]
    body["returnUrl"] = os.getenv("DP_PAYMENTS_RETURN_URL", body["returnUrl"]).strip() or body["returnUrl"]

    print(f"目标: {url}")
    print(f"并发数: {concurrency}")
    print(f"请求体: {json.dumps(body, ensure_ascii=False)}")
    print("-" * 72)

    results: List[Tuple[int, int, Optional[Dict[str, Any]], Optional[str]]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                _PostPaymentOnce,
                url=url,
                token=token,
                program_id=program_id,
                body=body,
                index=idx,
                timeout_sec=timeout_sec,
            )
            for idx in range(1, concurrency + 1)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item[0])

    errors: List[str] = []
    payloads: List[Dict[str, Any]] = []
    for index, status_code, payload, error in results:
        if error:
            errors.append(f"#{index}: {error}")
            continue
        if status_code != 200:
            errors.append(f"#{index}: HTTP {status_code}, body={json.dumps(payload, ensure_ascii=False)}")
            continue
        payloads.append(payload)
        valid_until_paths = _CollectValidUntilPaths(payload)
        valid_until_text = ", ".join(f"{path}={value}" for path, value in valid_until_paths) or "(无 validUntil 字段)"
        print(f"#{index:02d} HTTP 200 | {valid_until_text}")

    if errors:
        print("\n请求失败:")
        for line in errors:
            print(f"  - {line}")
        return 1

    if len(payloads) != concurrency:
        print(f"\n有效响应数 {len(payloads)} != 并发数 {concurrency}")
        return 1

    ignore_valid_until = _EnvBool("DP_PAYMENTS_IGNORE_VALID_UNTIL", default=False)
    comparable = [_StripValidUntil(item) if ignore_valid_until else item for item in payloads]
    baseline = comparable[0]
    mismatch_details: List[str] = []
    for idx, candidate in enumerate(comparable[1:], start=2):
        if candidate != baseline:
            mismatch_details.append(
                f"#{idx} 与 #1 不一致:\n"
                f"  baseline={json.dumps(baseline, ensure_ascii=False, sort_keys=True)}\n"
                f"  actual  ={json.dumps(candidate, ensure_ascii=False, sort_keys=True)}"
            )

    print("-" * 72)
    if mismatch_details:
        scope = "除 validUntil 外" if ignore_valid_until else "全部"
        print(f"断言失败：{scope}存在字段差异")
        for line in mismatch_details:
            print(line)
        return 1

    if ignore_valid_until:
        all_valid_until = [_CollectValidUntilPaths(item) for item in payloads]
        print(f"断言通过：{concurrency} 次响应除 validUntil 外完全一致")
        print("各次 validUntil 取值:")
        for idx, paths in enumerate(all_valid_until, start=1):
            text = ", ".join(f"{path}={value}" for path, value in paths) or "(无)"
            print(f"  #{idx:02d}: {text}")
    else:
        print(f"断言通过：{concurrency} 次响应全部字段完全一致")
        print("基准响应:")
        print(json.dumps(payloads[0], ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    sys.exit(RunConcurrentPaymentsAssert())


if __name__ == "__main__":
    main()
