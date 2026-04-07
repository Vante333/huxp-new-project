"""
PAPI-2424：``POST /v2/orders/ePasses/details``（Retrieve E-pass Usage Order Details）对 **MS 前缀** ``orderId`` 的提示与错误码。

OpenAPI（Apifox MCP · Default module）要点：必填头 ``Authorization``、``X-Program-ID``、``X-Request-ID``、``Content-Type``；
请求体必填 ``orderId``。MS 订单为 **E-pass 主单**语义，应走 ``POST /v2/orders/ePasses/search`` 查询，本 **usage details** 接口返回
``errCode=500.000.024`` 与固定英文 ``msg``（见 ``PAPI2424_MS_USAGE_ORDER_HINT_*``）。

**主链路**：本需求自动化以 **单接口多次调用** 为主（参数/版本差异），无多步注册造数编排；鉴权 ``POST /v2/auth/token`` 由用例
``Token`` fixture 调用 ``GetAccessTokenForEpass``。Allure ``S01/S02/…`` 仍由 ``AllureHttpScenarioSteps.Next`` 按请求递增。

**必填（PAPI-2424 / ePass 专用三件套）**：``DP_EPASS_PROGRAM_ID``（``X-Program-ID``，与 curl 一致）、``DP_EPASS_CLIENT_ID``、
``DP_EPASS_CLIENT_SECRET``（``POST /v2/auth/token`` 的 body）。缺任一项时 ``pytest.skip``。业务请求与取 token 的 Program 均使用该
``DP_EPASS_PROGRAM_ID``（通过 ``RequestWithAllure(..., x_program_id=...)``）。

**可选**：网关若要求取 token 时带父级 ``Authorization: Bearer``，再配置 ``DP_EPASS_TOKEN_REQUEST_BEARER`` 或 ``DP_TOKEN_REQUEST_BEARER``。

**可选**：``DP_P2424_V1_ORDERS_EPASSES_DETAILS_PATH`` 非空时，可与 V2 路径对拍（tc-P2-EPASS-002）；``DP_P2424_USAGE_ORDER_ID`` 用于
非 MS usage 回归（tc-P1-EPASS-ORD-001）；``DP_P2424_MS_PREFIX_CASE_INSENSITIVE=1`` 时，小写 ``ms…`` 前缀期望与 ``MS…`` 同为 ``500.000.024``。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Final, Optional, cast

import allure
import pytest
from requests import Response

from papi2548_helpers import JsonDict, ParseResponseEnvelope, RequestWithAllure, _RunAllureAssertionStep


def RequireP2424EpassTokenEnvOrSkip() -> None:
    """
    PAPI-2424 固定使用 ePass 专用三件套（项目 Program + clientId + secret）；缺任一项则跳过。
    """
    required = (
        "DP_EPASS_PROGRAM_ID",
        "DP_EPASS_CLIENT_ID",
        "DP_EPASS_CLIENT_SECRET",
    )
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        pytest.skip(
            "PAPI-2424 须配置 ePass 三项（当前缺失: "
            + ", ".join(missing)
            + "）：DP_EPASS_PROGRAM_ID、DP_EPASS_CLIENT_ID、DP_EPASS_CLIENT_SECRET。"
            "若取 token 仍需父级 Bearer，另设 DP_EPASS_TOKEN_REQUEST_BEARER 或 DP_TOKEN_REQUEST_BEARER。"
        )


def GetConfiguredEpassProgramId() -> str:
    """已配置场景下读取 ``DP_EPASS_PROGRAM_ID``（非空）。"""
    pid = os.getenv("DP_EPASS_PROGRAM_ID", "").strip()
    if not pid:
        raise RuntimeError("DP_EPASS_PROGRAM_ID 未设置")
    return pid

# 与 testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md 一致
PAPI2424_MS_USAGE_ORDER_HINT_ERR: Final[str] = "500.000.024"
PAPI2424_MS_USAGE_ORDER_HINT_MSG: Final[str] = (
    "The order ID you entered is not a usage order ID. If you want to query E-pass details, "
    "please use the /orders/ePasses/search API."
)

_DEFAULT_V2_PATH: Final[str] = "/v2/orders/ePasses/details"


def GetV2OrdersEPassesDetailsPath() -> str:
    """V2（及与 V2 同基的当前沙箱）details 路径；可通过 ``DP_P2424_V2_ORDERS_EPASSES_DETAILS_PATH`` 覆盖。"""
    raw = os.getenv("DP_P2424_V2_ORDERS_EPASSES_DETAILS_PATH", "").strip()
    return raw if raw.startswith("/") else _DEFAULT_V2_PATH


def ResolveV1OrdersEPassesDetailsPathOrEmpty() -> str:
    """
    V1 路径；未配置时返回空字符串，对应用例 ``pytest.skip``。

    示例：``/v1/orders/ePasses/details``（以环境网关真实前缀为准）。
    """
    raw = os.getenv("DP_P2424_V1_ORDERS_EPASSES_DETAILS_PATH", "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("/") else ("/" + raw)


def MsPrefixCaseInsensitiveFromEnv() -> bool:
    """为 ``1``/``true``/``yes``/``on`` 时，认为 MS 前缀 **大小写不敏感**（小写 ``ms`` 亦应命中 ``500.000.024``）。"""
    v = os.getenv("DP_P2424_MS_PREFIX_CASE_INSENSITIVE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def PostOrdersEPassesDetails(
    token: str,
    path: str,
    order_id: str,
    *,
    step_code: Optional[str] = None,
    step_title: Optional[str] = None,
    timeout_sec: float = 30.0,
) -> Response:
    """
    ``POST`` E-pass usage order details；``X-Program-ID`` 使用 ``DP_EPASS_PROGRAM_ID``（与 ePass curl 一致），
    每次调用新的 ``X-Request-ID``。
    """
    body: JsonDict = {"orderId": order_id}
    return RequestWithAllure(
        "POST",
        path,
        token=token,
        json_body=body,
        step_code=step_code,
        step_title=step_title,
        timeout_sec=timeout_sec,
        x_program_id=GetConfiguredEpassProgramId(),
    )


def ParseRootJsonObject(resp: Response) -> JsonDict:
    """解析响应根对象为 ``dict``；非 JSON 或非对象时抛出带上下文的 ``AssertionError``。"""
    try:
        root = resp.json()
    except ValueError as exc:
        raise AssertionError("响应体不是合法 JSON") from exc
    if not isinstance(root, dict):
        raise AssertionError(f"响应根类型异常: {type(root).__name__}")
    return cast(JsonDict, root)


def AssertHttp200MsUsageOrderHintEnvelope(resp: Response, *, context: str = "PAPI-2424") -> None:
    """HTTP 200 + 业务失败信封：``code==-1``、``errCode``、整句 ``msg`` 与需求一致。"""

    def _Do() -> str:
        assert resp.status_code == 200, f"{context}: 期望 HTTP 200，实际 {resp.status_code}"
        root = ParseRootJsonObject(resp)
        code = root.get("code")
        assert code == -1, f"{context}: 期望 code=-1，实际 {code!r}，body={root}"
        assert root.get("errCode") == PAPI2424_MS_USAGE_ORDER_HINT_ERR, (
            f"{context}: errCode 期望 {PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}，实际 {root.get('errCode')!r}"
        )
        msg = root.get("msg")
        assert msg == PAPI2424_MS_USAGE_ORDER_HINT_MSG, (
            f"{context}: msg 与需求全文不一致，实际: {msg!r}"
        )
        return (
            f"{context}: HTTP 200；code=-1；errCode={PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}；"
            "msg 与需求固定英文全文一致。"
        )

    _RunAllureAssertionStep(f"PAPI-2424: MS usage 提示信封（{context}）", _Do)


def AssertHttp200NotMsUsageOrderHint(resp: Response, *, context: str = "PAPI-2424") -> None:
    """
    用于「非 MS 前缀 / 子串边界」：不得出现 MS 专用 ``500.000.024``，且整句引导文案不得与需求全文相同。

    说明：其它业务错误仍可能返回不同 ``errCode``；本断言只排除本需求专用码与专用英文全文。
    """

    def _Do() -> str:
        assert resp.status_code == 200, f"{context}: 期望 HTTP 200，实际 {resp.status_code}"
        root = ParseRootJsonObject(resp)
        err = root.get("errCode")
        err_s = err if isinstance(err, str) else str(err)
        assert err_s != PAPI2424_MS_USAGE_ORDER_HINT_ERR, (
            f"{context}: 不应返回 MS 专用 errCode {PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}，实际 body={root}"
        )
        msg = root.get("msg")
        if isinstance(msg, str) and msg:
            assert msg != PAPI2424_MS_USAGE_ORDER_HINT_MSG, (
                f"{context}: 不应出现 MS 专用全文 msg，实际: {msg!r}"
            )
        extra = ""
        if isinstance(msg, str) and msg:
            extra = "；msg 非空且已排除与 MS 专用全文相同。"
        else:
            extra = "；msg 为空或非字符串，仅校验 errCode。"
        return f"{context}: HTTP 200；errCode 非 {PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}{extra}"

    _RunAllureAssertionStep(f"PAPI-2424: 非 MS 语义（排除专用 errCode/msg）（{context}）", _Do)


def AssertUsageOrderRegressionNotMsHint(resp: Response, *, context: str = "PAPI-2424-usage") -> None:
    """tc-P1：已知 usage 订单不因本需求单独出现 ``500.000.024``。"""

    def _Do() -> str:
        assert resp.status_code == 200, f"{context}: 期望 HTTP 200，实际 {resp.status_code}"
        root = ParseRootJsonObject(resp)
        err = root.get("errCode")
        err_s = err if isinstance(err, str) else str(err)
        assert err_s != PAPI2424_MS_USAGE_ORDER_HINT_ERR, (
            f"{context}: usage 订单不应命中 MS 专用码 {PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}，实际 body={root}"
        )
        return (
            f"{context}: HTTP 200；errCode 未命中 {PAPI2424_MS_USAGE_ORDER_HINT_ERR!r}（usage 回归）。"
        )

    _RunAllureAssertionStep(f"PAPI-2424: usage 订单回归（{context}）", _Do)


def AssertLowercaseMsPrefixBehavior(resp: Response, *, context: str = "PAPI-2424-case") -> None:
    """
    小写 ``ms…``：由 ``MsPrefixCaseInsensitiveFromEnv()`` 决定期望是否命中 ``500.000.024``。

    - **敏感（默认）**：不应返回 MS 专用码（与评审「仅大写 MS」一致）。
    - **不敏感**：应与大写一致，调用方应先断言 ``AssertHttp200MsUsageOrderHintEnvelope`` 语义；此处仅做分支入口。
    """
    insensitive = MsPrefixCaseInsensitiveFromEnv()
    branch_label = "大小写不敏感" if insensitive else "大小写敏感(默认)"

    def _Do() -> str:
        if insensitive:
            AssertHttp200MsUsageOrderHintEnvelope(resp, context=context)
            return f"{context}: 环境声明小写 ms 与 MS 等价，子步骤已校验 500.000.024 信封。"
        AssertHttp200NotMsUsageOrderHint(resp, context=context)
        return f"{context}: 环境声明仅大写 MS 命中，子步骤已校验小写未出现专用 errCode/msg。"

    _RunAllureAssertionStep(f"PAPI-2424: 小写 ms 策略（{branch_label}）（{context}）", _Do)


def AttachP2424ResponseSummary(resp: Response, *, label: str) -> None:
    """Allure 附加简要信封字段，便于 V1/V2 对拍阅读。"""
    status, root, _data = ParseResponseEnvelope(resp)
    summary: Dict[str, Any] = {
        "label": label,
        "http_status": status,
        "code": None if root is None else root.get("code"),
        "errCode": None if root is None else root.get("errCode"),
        "msg": None if root is None else root.get("msg"),
    }
    try:
        text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    except (TypeError, ValueError):
        text = str(summary) + "\n"
    allure.attach(text, name=f"p2424_envelope_{label}.json.txt", attachment_type=allure.attachment_type.TEXT)
