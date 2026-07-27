"""恢复 Preview 现金算价明细断言；Create/Detail 保持按saas返回。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(r"d:\interface\interface_cursor\testcases\2026Q2SP4")
MAIN = ROOT / "订单流支持真现金支付第三方权益-测试分析-001.md"
PREVIEW = ROOT / "订单流-预览订单接口-预收费权益现金-测试分析-001.md"

PREVIEW_PLACEHOLDER_RE = re.compile(
    r"  - 返回 `payment` 对象；`paymentStatus=null`；`timeline=null`；"
    r"(?:`currency` 正常返回；)?`price`/`charges`/`deductions` \*\*按saas返回\*\*"
    r"(?:（待与开发对齐取值后补充明细断言）)?。"
)

R3_PREVIEW = (
    "  - 返回 0 元口径；若返回完整 `payment`，则 `payment.price.payableAmount=0`，"
    "且不产生正向 `BASE_PRICE` 与用户承担的 `PREBOOKING_FEE`；"
    "Preview 阶段 `paymentStatus` 与 `timeline` 返回 `null`。\n"
    "- 校验 `charges` 与 `deductions` 明细。\n"
    "  - 不应产生有效 `BASE_PRICE`、用户侧有效 `PREBOOKING_FEE` 和有效 `ENTITLEMENT` 抵扣明细。\n"
    "- 按使用权益点数维度校验 `BASE_PRICE`、`deductions` 与 `price` 汇总。\n"
    "  - 使用权益点数为 0/1/3 时均不改变 0 元结果；超人次费用不设置，"
    "因此不返回有效 `BASE_PRICE`，`deductions` 无有效抵扣金额，"
    "`originalAmount=0`、`deductionAmount=0`、`payableAmount=0`。"
)


def _CustPrebookFee() -> str:
    return "（3）`PREBOOKING_FEE`：`details=[]`（客户承担预约费）；"


def _UserPrebookFee(prebook: float) -> str:
    total = prebook * 3
    return (
        f"（3）`PREBOOKING_FEE`：`CARDHOLDER.quantity=1`、`unitPrice={prebook}`、`amount={prebook}`；"
        f"`GUEST.quantity=2`、`unitPrice={prebook}`、`amount={prebook * 2}`（合计 `{total}`）；"
    )


def _ZeroPrebookFee() -> str:
    return "（3）`PREBOOKING_FEE` 不返回或 `amount=0`；"


def _DeductionsZero() -> str:
    return "（4）`deductions`：返回 `null`、`[]` 或不返回该字段；"


def _DeductionsOne(fee: float) -> str:
    neg = -fee
    return (
        f"（4）`deductions`：`strategy=ENTITLEMENT`、`appliedTo=BASE_PRICE`；"
        f"仅 `CARDHOLDER`：`quantity=1`、`unitAmount={neg}`、`amount={neg}`；"
    )


def _DeductionsThree(fee: float) -> str:
    neg = -fee
    guest_amt = neg * 2
    return (
        f"（4）`deductions`：`strategy=ENTITLEMENT`、`appliedTo=BASE_PRICE`；"
        f"`CARDHOLDER`：`quantity=1`、`unitAmount={neg}`、`amount={neg}`；"
        f"`GUEST`：`quantity=2`、`unitAmount={neg}`、`amount={guest_amt}`；"
    )


def _DeductionsThreeNoPrebook(fee: float) -> str:
    neg = -fee
    guest_amt = neg * 2
    return (
        f"（4）`deductions`：`strategy=ENTITLEMENT`、`appliedTo=BASE_PRICE`；"
        f"`CARDHOLDER`：`quantity=1`、`unitAmount={neg}`、`amount={neg}`；"
        f"`GUEST`：`quantity=2`、`unitAmount={neg}`、`amount={guest_amt}`（不抵预约费）；"
    )


def _BuildPreviewLine(
    over_fee: float,
    prebook_kind: str,
    prebook_price: float,
    points: int,
) -> str:
    guest_amt = over_fee * 2
    base_total = over_fee * 3
    if prebook_kind == "cust":
        prebook_part = _CustPrebookFee()
        original = base_total
    elif prebook_kind == "user":
        prebook_part = _UserPrebookFee(prebook_price)
        original = base_total + prebook_price * 3
    else:
        prebook_part = _ZeroPrebookFee()
        original = base_total

    if points == 0:
        ded_part = _DeductionsZero()
        deduction = 0.0
    elif points == 1:
        ded_part = _DeductionsOne(over_fee)
        deduction = over_fee
    elif prebook_kind == "user":
        ded_part = _DeductionsThreeNoPrebook(over_fee)
        deduction = over_fee * 3
    else:
        ded_part = _DeductionsThree(over_fee)
        deduction = base_total

    payable = original - deduction
    return (
        "  - （1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`；"
        f"（2）`BASE_PRICE`（按订单总人数）：`CARDHOLDER.quantity=1`、`unitPrice={over_fee}`、"
        f"`amount={over_fee}`；`GUEST.quantity=2`、`unitPrice={over_fee}`、`amount={guest_amt}`"
        f"（合计 `{base_total}`）；"
        f"{prebook_part}"
        f"{ded_part}"
        f"（5）`payment.price`：`originalAmount={original}`、`deductionAmount={deduction}`、"
        f"`payableAmount={payable}`；"
        "（6）校验 `payment.currency` 及金额关系（1）（2）（3）（4）。"
    )


RULE_CFG: Dict[str, Dict[str, object]] = {
    "R1": {"over_fee": 13.5, "prebook_kind": "cust", "prebook_price": 12.0},
    "R2": {"over_fee": 10.0, "prebook_kind": "zero", "prebook_price": 0.0},
    "R4": {"over_fee": 15.5, "prebook_kind": "user", "prebook_price": 11.0},
    "R5": {"over_fee": 8.5, "prebook_kind": "zero", "prebook_price": 0.0},
}


def _DetectRuleAndPoints(block: str) -> Optional[tuple[str, int]]:
    rule_m = re.search(r"对应 (R[1-6])", block)
    if not rule_m:
        rule_m = re.search(r"假定单价（(R[1-6])）", block)
    if not rule_m:
        return None
    rule = rule_m.group(1)
    if rule == "R3":
        return ("R3", 0)
    points_m = re.search(r"使用权益点数为 (\d+)", block)
    if not points_m:
        points_m = re.search(r"使用权益点数(\d+)", block)
    if not points_m:
        tag_m = re.search(r"使用权益点数(\d+)", block)
        if tag_m:
            return (rule, int(tag_m.group(1)))
        return None
    return (rule, int(points_m.group(1)))


def _ReplacePreviewPlaceholders(text: str) -> str:
    parts = re.split(r"(?=#### tc-p1:|### tc-p1:)", text)
    out: list[str] = []
    for part in parts:
        if "调用预览订单接口" not in part and "调用预览订单接口，" not in part:
            out.append(part)
            continue
        if "假定单价（R3）" in part or "对应 R3" in part:
            part = PREVIEW_PLACEHOLDER_RE.sub(R3_PREVIEW, part, count=1)
            out.append(part)
            continue
        detected = _DetectRuleAndPoints(part)
        if not detected:
            out.append(part)
            continue
        rule, points = detected
        if rule == "R6":
            out.append(part)
            continue
        cfg = RULE_CFG.get(rule)
        if not cfg:
            out.append(part)
            continue
        line = _BuildPreviewLine(
            over_fee=float(cfg["over_fee"]),
            prebook_kind=str(cfg["prebook_kind"]),
            prebook_price=float(cfg["prebook_price"]),
            points=points,
        )
        part = PREVIEW_PLACEHOLDER_RE.sub(line, part, count=1)
        out.append(part)
    return "".join(out)


def _PatchHeaders(text: str, *, is_preview_doc: bool) -> str:
    text = text.replace(
        "- rc: **2.2.1 标注「按saas返回」的 `price`/`charges`/`deductions`**："
        "测试断言原样写 **按saas返回**，具体取值待与开发对齐后补充；"
        "「业务计算规则」「payment明细」「假定单价」仅作参考。",
        "- rc: **2.2.1「按saas返回」适用范围**：汇总表与 **Create/Detail** 步骤对 "
        "`price`/`charges`/`deductions` 写 **按saas返回**；**Preview 现金**仍保留 R1–R6 "
        "算价明细断言（用于核对 SaaS 算价输出，待与开发对齐后可收紧）。",
    )
    text = text.replace(
        "- rc: **2.2.1 中标注「按saas返回」的 `price`/`charges`/`deductions`**："
        "测试断言原样写 **按saas返回**，具体取值待与开发对齐后补充；"
        "下文「假定价格」「payment明细」仅作业务参考。",
        "- rc: **2.2.1「按saas返回」适用范围**：汇总表与 **Create/Detail** 步骤对 "
        "`price`/`charges`/`deductions` 写 **按saas返回**；**Preview 现金**仍保留 R1–R6 "
        "算价明细断言（用于核对 SaaS 算价输出，待与开发对齐后可收紧）。",
    )
    if is_preview_doc:
        text = text.replace(
            "现金（权益抵扣）Preview 返回 `payment`；`paymentStatus`/`timeline=null`；"
            "`price`/`charges`/`deductions` **按saas返回**。",
            "现金（权益抵扣）Preview：`paymentStatus`/`timeline=null`；"
            "算价明细按 R1–R6 断言（SaaS 算价输出核对）。",
        )
        text = text.replace(
            "预约人数按附件口径取 3 人；使用权益点数覆盖 0、1、3 三种核心分支。"
            "「业务计算规则」中金额拆分仅作参考，接口 `price`/`charges`/`deductions` 断言写 **按saas返回**。",
            "预约人数按附件口径取 3 人；使用权益点数覆盖 0、1、3 三种核心分支。"
            "Preview 现金按 R1–R6 写算价明细断言；Create/Detail 的 `price`/`charges`/`deductions` 写 **按saas返回**。",
        )
        text = text.replace(
            "- rc: 现金场景按预约商品是否支持权益抵扣拆分为「现金（权益抵扣）」和「现金（不支持权益抵扣）」；明细字段待与开发对齐后补充。",
            "- rc: 现金场景按预约商品是否支持权益抵扣拆分为「现金（权益抵扣）」和「现金（不支持权益抵扣）」。",
        )
        text = text.replace(
            "| 现金（权益抵扣） | `cashPaymentApplied=false`，`cashier.paymentMode=DP_COLLECT` | 返回 `payment` 对象 | `paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** |",
            "| 现金（权益抵扣） | `cashPaymentApplied=false`，`cashier.paymentMode=DP_COLLECT` | 返回 `payment` 对象 | `paymentStatus`/`timeline`=`null`；算价明细按 R1–R6 断言 |",
        )
        text = text.replace(
            "| 现金（权益抵扣） | `paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** |",
            "| 现金（权益抵扣） | `paymentStatus`/`timeline`=`null`；算价明细按 R1–R6 断言 |",
        )
        # payment字段汇总预期 - restore cash preview column
        text = text.replace("| `payment.price.originalAmount` | **按saas返回**（待补充） | `null` |", "| `payment.price.originalAmount` | 等于 `charges` 中所有正向金额汇总 | `null` |")
        text = text.replace("| `payment.price.deductionAmount` | **按saas返回**（待补充） | `null` |", "| `payment.price.deductionAmount` | 等于权益抵扣金额汇总，抵扣对象仅限 `BASE_PRICE` | `null` |")
        text = text.replace("| `payment.price.payableAmount` | **按saas返回**（待补充） | `null` |", "| `payment.price.payableAmount` | 等于 `originalAmount-deductionAmount` | `null` |")
        text = text.replace("| `payment.charges.type=BASE_PRICE` | **按saas返回**（待补充） | `null` |", "| `payment.charges.type=BASE_PRICE` | 按订单总人数返回 `CARDHOLDER`/`GUEST` 明细 | `null` |")
        text = text.replace("| `payment.charges.type=PREBOOKING_FEE` | **按saas返回**（待补充） | `null` |", "| `payment.charges.type=PREBOOKING_FEE` | 客户承担 `details=[]`；用户承担按 3 人明细 | `null` |")
        text = text.replace("| `payment.deductions.strategy=ENTITLEMENT` | **按saas返回**（待补充） | `null` |", "| `payment.deductions.strategy=ENTITLEMENT` | 当前只支持权益抵扣 | `null` |")
        text = text.replace("| `payment.deductions.appliedTo` | **按saas返回**（待补充） | `null` |", "| `payment.deductions.appliedTo` | 只能为 `BASE_PRICE` | `null` |")
        text = text.replace("## payment明细对象预期（业务参考，待与开发对齐后补充断言）", "## payment明细对象预期")
        # R mapping cash column
        for rule in ("R1", "R2", "R4", "R5"):
            text = text.replace(
                f"| {rule} |",
                f"| {rule} |",
            )
        text = re.sub(
            r"\| (R[1245]) \|([^|]+\|){5} 返回 `payment`；`paymentStatus`/`timeline=null`；`price`/`charges`/`deductions` \*\*按saas返回\` \|",
            lambda m: m.group(0).replace(
                "返回 `payment`；`paymentStatus`/`timeline=null`；`price`/`charges`/`deductions` **按saas返回**",
                "返回完整 `payment`；`paymentStatus`/`timeline=null`；按假定单价表核对 `charges`/`deductions`/`price`",
            ),
            text,
        )
    else:
        text = text.replace(
            "- rc: 预约 3 人；下文「假定价格」中 `charges`/`deductions` 拆分规则仅作**业务参考**，接口断言写 **按saas返回**。",
            "- rc: 预约 3 人；Preview 现金保留 R1–R6 算价明细断言；Create/Detail 的 `price`/`charges`/`deductions` 写 **按saas返回**。",
        )
        text = text.replace(
            "- rc: **各 R 假定单价不同**（见下表），供 Boss 配置与业务口径核对；**非**当前接口明细断言。",
            "- rc: **各 R 假定单价不同**（见下表），供 Preview 算价明细断言与 Boss 配置核对。",
        )
        text = text.replace(
            "| Preview（现金） | 返回 `payment`；`paymentStatus`/`timeline`=`null`；`price`/`charges`/`deductions` **按saas返回** |",
            "| Preview（现金） | 返回 `payment`；`paymentStatus`/`timeline`=`null`；算价明细按 R1–R6 断言 |",
        )
        text = text.replace(
            "> 上表「假定价格」仅作业务参考；接口断言中 `price`/`charges`/`deductions` 按 2.2.1 写 **按saas返回**，待与开发对齐后补充明细。",
            "> 上表供 Preview 算价明细断言参考；Create/Detail 的 `price`/`charges`/`deductions` 按 2.2.1 写 **按saas返回**。",
        )
        text = text.replace(
            "| BASE_PRICE quantity（业务参考） | 始终按订单总人数：`CARDHOLDER=1`、`GUEST=2` |",
            "| BASE_PRICE quantity | 始终按订单总人数：`CARDHOLDER=1`、`GUEST=2` |",
        )
        text = text.replace(
            "| BASE_PRICE amount（业务参考） | 始终 `quantity*unitPrice`，**与权益使用无关** |",
            "| BASE_PRICE amount | 始终 `quantity*unitPrice`，**与权益使用无关**；权益 3 时仍为 `1*超人次+2*超人次` |",
        )
        text = text.replace(
            "| PREBOOKING_FEE（业务参考） | 客户承担 `details=[]`；用户承担按 3 人明细 |",
            "| PREBOOKING_FEE（客户承担） | `details=[]`（客户承担，不返回预约费明细行） |\n| PREBOOKING_FEE（用户承担） | `CARDHOLDER.amount=1*预约单价`、`GUEST.amount=2*预约单价`（合计 `预约单价*3`） |",
        )
        text = text.replace(
            "| deductions（业务参考） | 0→无抵扣；1→仅 CH；3→CH+G |",
            "| deductions（权益0） | `null`、`[]` 或不返回 |\n| deductions（权益1） | 仅 `CARDHOLDER`：`quantity=1`，`unitAmount`/`amount` 为具体负值 |\n| deductions（权益3） | `CARDHOLDER`+`GUEST`：`quantity=1/2`，各自 `unitAmount`/`amount` 为具体负值 |",
        )
        text = text.replace(
            "| 金额关系（业务参考，待补充断言） | charges/deductions/price 明细 **按saas返回** |",
            "| 金额关系 | （1）charges 各行 `amount=quantity*unitPrice`；（2）正向合计=`originalAmount`；（3）abs(deductions)=`deductionAmount`；（4）original-deduction=`payableAmount` |",
        )
        text = text.replace(
            "- 校验 `payment.price`/`payment.charges`/`payment.deductions`。\n  - **按saas返回**（待与开发对齐取值后补充明细断言）。",
            "- 校验 `payment.charges`。\n  - 包含 `BASE_PRICE`、`PREBOOKING_FEE`；`unitPrice` 分别取 `overNumFee`、`prebookPrice`。\n- 校验 `payment.deductions`。\n  - `strategy=ENTITLEMENT`，`appliedTo=BASE_PRICE`；抵扣金额为负数。\n- 校验金额关系（1）（2）（3）。\n  - charges 正向合计=`originalAmount`；abs(deductions)=`deductionAmount`；差值=`payableAmount`。",
        )
    return text


def Main() -> None:
    for path, is_preview in ((MAIN, False), (PREVIEW, True)):
        text = path.read_text(encoding="utf-8")
        text = _ReplacePreviewPlaceholders(text)
        text = _PatchHeaders(text, is_preview_doc=is_preview)
        path.write_text(text, encoding="utf-8")
        print(f"Restored: {path.name}")


if __name__ == "__main__":
    Main()
