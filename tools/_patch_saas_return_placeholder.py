"""将测试分析中 2.2.1 标注「按saas返回」的 price/charges/deductions 改为占位断言。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

ROOT = Path(r"d:\interface\interface_cursor\testcases\2026Q2SP4")
MAIN = ROOT / "订单流支持真现金支付第三方权益-测试分析-001.md"
PREVIEW = ROOT / "订单流-预览订单接口-预收费权益现金-测试分析-001.md"

PREVIEW_PLACEHOLDER = (
    "  - 返回 `payment` 对象；`paymentStatus=null`；`timeline=null`；"
    "`currency` 正常返回；`price`/`charges`/`deductions` **按saas返回**"
    "（待与开发对齐取值后补充明细断言）。"
)

CREATE_PENDING = (
    "  - Create 返回完整 `payment`，`paymentStatus=PENDING_PAYMENT`，"
    "`timeline` 返回但值全部为 `null`；`price`/`charges`/`deductions` **按saas返回**；"
    "订单状态进入 `status=9`。"
)

CREATE_NO_PAYMENT = (
    "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
    "`timeline=null`；`price`/`charges`/`deductions` **按saas返回**；"
    "订单不进入 `status=9`（可为 `status=1` 或 `status=5`）。"
)

CREATE_NO_PAYMENT_SHORT = (
    "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
    "`timeline=null`；`price`/`charges`/`deductions` **按saas返回**；"
    "不进入待支付态且不应返回 `status=9`。"
)

ORDER_DETAIL_PENDING = (
    "  - Order Detail 返回完整 `payment`；`paymentStatus` 按支付状态返回；"
    "`timeline.authorizedAt/paidAt` 按支付状态返回；"
    "`price`/`charges`/`deductions` **按saas返回**。"
)

ORDER_DETAIL_REFUND = (
    "  - Order Detail：`paymentStatus`/`timeline.authorizedAt/paidAt` 按支付状态返回；"
    "退款后 `paymentStatus=REFUNDED`，`timeline` 含 `authorizedAt/paidAt/refundedAt`；"
    "`price`/`charges`/`deductions` **按saas返回**。"
)

ORDER_DETAIL_ZERO = (
    "  - Order Detail 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
    "`timeline=null`；`price`/`charges`/`deductions` **按saas返回**；"
    "0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline=null`。"
)

ORDER_DETAIL_ZERO_SHORT = (
    "  - Order Detail 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
    "`timeline=null`；`price`/`charges`/`deductions` **按saas返回**。"
)


def _ReplaceAll(text: str, pairs: List[Tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _PatchCashAssertions(text: str) -> str:
    text = re.sub(
        r"  - （1）Preview 返回完整 `payment`.*?（6）校验 `payment\.currency` 及金额关系（1）（2）（3）（4）。",
        PREVIEW_PLACEHOLDER,
        text,
    )
    text = _ReplaceAll(
        text,
        [
            (
                "  - Create 返回完整 `payment`，`paymentStatus=PENDING_PAYMENT`，"
                "`timeline` 返回但值全部为 `null`，订单状态进入 `status=9`。",
                CREATE_PENDING,
            ),
            (
                "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
                "`timeline` 返回 `null`，订单不进入 `status=9`（可为 `status=1` 或 `status=5`）。",
                CREATE_NO_PAYMENT,
            ),
            (
                "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
                "`timeline=null`，订单不进入 `status=9`。",
                CREATE_NO_PAYMENT_SHORT,
            ),
            (
                "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
                "`timeline=null`，不进入待支付态且不应返回 `status=9`。",
                CREATE_NO_PAYMENT_SHORT,
            ),
            (
                "  - Order Detail 返回完整 `payment`，未支付时保持待支付状态；"
                "支付成功后 `paymentStatus` 按支付状态返回，"
                "`timeline.authorizedAt/paidAt` 按支付状态返回。",
                ORDER_DETAIL_PENDING,
            ),
            (
                "  - （1）Order Detail 未支付时保持待支付；支付成功后 `paymentStatus` 与 "
                "`timeline.authorizedAt/paidAt` 按支付状态返回；（2）退款后 "
                "`paymentStatus=REFUNDED`，`timeline` 含 `authorizedAt/paidAt/refundedAt`。",
                ORDER_DETAIL_REFUND,
            ),
            (
                "  - Order Detail 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
                "`timeline=null`；0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline=null`。",
                ORDER_DETAIL_ZERO,
            ),
            (
                "  - Order Detail 返回完整 `payment`，`paymentStatus` 按支付状态返回；"
                "退款后 `paymentStatus=REFUNDED`，`timeline` 含 `authorizedAt/paidAt/refundedAt`。",
                ORDER_DETAIL_REFUND,
            ),
            (
                "  - 返回成功；`payment` 按 **2.2.1** 返回完整算价（`paymentStatus`/`timeline=null`）。",
                "  - 返回成功；`payment` 对象返回；`paymentStatus=null`；`timeline=null`；"
                "`price`/`charges`/`deductions` **按saas返回**（待与开发对齐取值后补充明细断言）。",
            ),
        ],
    )
    return text


def _PatchMainHeader(text: str) -> str:
    insert_rc = (
        "- rc: **2.2.1 中标注「按saas返回」的 `price`/`charges`/`deductions`**："
        "测试断言原样写 **按saas返回**，具体取值待与开发对齐后补充；"
        "下文「假定价格」「payment明细」仅作业务参考。\n"
    )
    if "按saas返回」的 `price`" not in text:
        marker = "- rc: **paymentStatus 枚举分场景**"
        if marker in text:
            text = text.replace(marker, insert_rc + marker, 1)

    text = text.replace(
        "现金（权益抵扣）Preview 返回算价且 `paymentStatus`/`timeline=null`，需支付 Create 为 `PENDING_PAYMENT`。",
        "现金（权益抵扣）`paymentStatus`/`timeline` 按 2.2.1 返回；"
        "`price`/`charges`/`deductions` 在需求标注处写 **按saas返回**（待补充明细）。",
    )
    text = text.replace(
        "| Preview（现金） | 返回完整 `payment`；`paymentStatus`/`timeline`=`null` |",
        "| Preview（现金） | 返回 `payment`；`paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** |",
    )
    text = text.replace(
        "| Create（需支付） | `paymentStatus=PENDING_PAYMENT`；`timeline` 全 `null`；`status=9` |",
        "| Create（需支付） | `paymentStatus=PENDING_PAYMENT`；`timeline` 全 `null`；`price`/`charges`/`deductions` **按saas返回**；`status=9` |",
    )
    text = text.replace(
        "| Create（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null` |",
        "| Create（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions` **按saas返回** |",
    )
    text = text.replace(
        "| Order Detail（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null` |",
        "| Order Detail（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions` **按saas返回** |",
    )
    text = text.replace(
        "> 上表仅用于 Preview 阶段字段核对；Create/Detail 的 `paymentStatus`/`timeline` 仍按文首「核对规则速查」执行。",
        "> 上表「假定价格」仅作业务参考；接口断言中 `price`/`charges`/`deductions` 按 2.2.1 写 **按saas返回**，待与开发对齐后补充明细。",
    )
    return text


def _PatchPreviewDoc(text: str) -> str:
    insert_rc = (
        "- rc: **2.2.1 标注「按saas返回」的 `price`/`charges`/`deductions`**："
        "测试断言原样写 **按saas返回**，具体取值待与开发对齐后补充；"
        "「业务计算规则」「payment明细」「假定单价」仅作参考。\n"
    )
    if "按saas返回」的 `price`" not in text:
        marker = "- rc: 已补充 **E-pass `toUseUsageCount`"
        if marker in text:
            text = text.replace(marker, insert_rc + marker, 1)

    text = text.replace(
        "现金（权益抵扣）Preview 返回完整算价，`paymentStatus`/`timeline=null`。",
        "现金（权益抵扣）Preview 返回 `payment`；`paymentStatus`/`timeline=null`；"
        "`price`/`charges`/`deductions` **按saas返回**。",
    )
    text = text.replace(
        "| 现金（权益抵扣） | `cashPaymentApplied=false`，`cashier.paymentMode=DP_COLLECT` | 返回完整 `payment` 对象 | 返回 `price`、`charges`、`deductions`；预览阶段 `paymentStatus`/`timeline` 返回 `null` |",
        "| 现金（权益抵扣） | `cashPaymentApplied=false`，`cashier.paymentMode=DP_COLLECT` | 返回 `payment` 对象 | `paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** |",
    )
    text = text.replace(
        "| 现金（权益抵扣） | 完整算价；`paymentStatus`/`timeline=null` | 需支付：`PENDING_PAYMENT` + `timeline` 全 `null` + `status=9`；0 元：`NO_PAYMENT_REQUIRED` | 按支付状态 / 0 元 `NO_PAYMENT_REQUIRED` |",
        "| 现金（权益抵扣） | `paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** | 需支付：`PENDING_PAYMENT` + `timeline` 全 `null` + `price`/`charges`/`deductions` **按saas返回** + `status=9`；0 元：`NO_PAYMENT_REQUIRED` + **按saas返回** | `paymentStatus`/`timeline` 按 2.2.1；`price`/`charges`/`deductions` **按saas返回** |",
    )

    for old in ("按 SaaS 返回算价", "按 SaaS 返回"):
        text = text.replace(old, "按saas返回")

    text = re.sub(
        r"\| `payment\.price\.originalAmount` \| 等于 `charges` 中所有正向金额汇总 \|",
        "| `payment.price.originalAmount` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.price\.deductionAmount` \| 等于权益抵扣金额汇总，抵扣对象仅限 `BASE_PRICE` \|",
        "| `payment.price.deductionAmount` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.price\.payableAmount` \| 等于 `originalAmount-deductionAmount` \|",
        "| `payment.price.payableAmount` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.charges\.type=BASE_PRICE` \| 按订单总人数返回 `CARDHOLDER`/`GUEST` 明细 \|",
        "| `payment.charges.type=BASE_PRICE` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.charges\.type=PREBOOKING_FEE` \| 客户承担 `details=\[\]`；用户承担按 3 人明细 \|",
        "| `payment.charges.type=PREBOOKING_FEE` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.deductions\.strategy=ENTITLEMENT` \| 当前只支持权益抵扣 \|",
        "| `payment.deductions.strategy=ENTITLEMENT` | **按saas返回**（待补充） |",
        text,
    )
    text = re.sub(
        r"\| `payment\.deductions\.appliedTo` \| 只能为 `BASE_PRICE` \|",
        "| `payment.deductions.appliedTo` | **按saas返回**（待补充） |",
        text,
    )

    text = re.sub(
        r"返回完整 `payment`；`paymentStatus`/`timeline=null`；按假定单价表核对 `charges`/`deductions`/`price`；[^|]+",
        "返回 `payment`；`paymentStatus`/`timeline=null`；`price`/`charges`/`deductions` **按saas返回** |",
        text,
    )
    text = re.sub(
        r"返回 `payment` 0 元口径：`payableAmount=0`；无有效 `BASE_PRICE`",
        "返回 `payment`；`paymentStatus`/`timeline=null`；`price`/`charges`/`deductions` **按saas返回**",
        text,
    )

    text = text.replace(
        "## payment明细对象预期\n\n| 对象 | type/strategy | 明细预期 |",
        "## payment明细对象预期（业务参考，待与开发对齐后补充断言）\n\n| 对象 | type/strategy | 明细预期 |",
    )

    # R3 现金用例：去掉具体金额校验，改为按saas返回
    text = re.sub(
        r"- 返回 0 元口径；若返回完整 `payment`，则 `payment\.price\.payableAmount=0`.*?`payableAmount=0`。",
        "- 返回 `payment` 对象；`paymentStatus=null`；`timeline=null`；"
        "`price`/`charges`/`deductions` **按saas返回**（待与开发对齐取值后补充明细断言）。",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"- 校验 `charges` 与 `deductions` 明细。\n  - 不应产生有效 `BASE_PRICE`、用户侧有效 `PREBOOKING_FEE` 和有效 `ENTITLEMENT` 抵扣明细。\n",
        "",
        text,
    )
    text = re.sub(
        r"- 按使用权益点数维度校验 `BASE_PRICE`、`deductions` 与 `price` 汇总。\n  - 使用权益点数为 0/1/3 时均不改变 0 元结果；超人次费用不设置，因此不返回有效 `BASE_PRICE`，`deductions` 无有效抵扣金额，`originalAmount=0`、`deductionAmount=0`、`payableAmount=0`。\n",
        "",
        text,
    )

    return _PatchCashAssertions(text)


def Main() -> None:
    main_text = MAIN.read_text(encoding="utf-8")
    main_text = _PatchCashAssertions(main_text)
    main_text = _PatchMainHeader(main_text)
    MAIN.write_text(main_text, encoding="utf-8")

    preview_text = PREVIEW.read_text(encoding="utf-8")
    preview_text = _PatchPreviewDoc(preview_text)
    PREVIEW.write_text(preview_text, encoding="utf-8")

    print(f"Patched: {MAIN.name}")
    print(f"Patched: {PREVIEW.name}")


if __name__ == "__main__":
    Main()
