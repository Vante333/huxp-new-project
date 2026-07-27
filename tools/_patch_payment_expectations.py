"""按脑图底稿全文校正 payment 字段预期，保持用例步骤换行结构。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

TARGET = Path(
    r"d:\interface\interface_cursor\testcases\2026Q2SP4"
    r"\订单流支持真现金支付第三方权益-测试分析-001.md"
)
PREVIEW_TARGET = Path(
    r"d:\interface\interface_cursor\testcases\2026Q2SP4"
    r"\订单流-预览订单接口-预收费权益现金-测试分析-001.md"
)

HEADER_PREFIX = """# 订单流支持真现金支付第三方权益测试分析

## 测试范围说明

- rc: **本文以脑图 `D:\\fenxi\\API\\2026_Q2\\评审后\\Q2_SP4\\订单流支持真现金支付第三方权益测试分析.xmind` 为权威底稿**；由 `tools/build_cash_payment_test_analysis_from_xmind.py` 导出并叠加需求校正；**请勿手工改结构**，改脑图后重跑构建脚本。
- rc: 需求依据 `requirements/2026Q2SP4/Confluence-1906049058.md` **2.2.1**；判定组合见 `requirements/2026Q2SP4/订单流-判定组合表-预收费权益现金.xlsx`（R1-R7）。
- rc: **订单详情 payment 以 2.2.1 为准**；需求 2.5 旧表作废。
- rc: 预约 3 人；Preview 现金保留 R1–R6 算价明细断言；Create/Detail 的 `price`/`charges`/`deductions` 写 **按saas返回**。
- rc: **各 R 假定单价不同**（见下表），供 Preview 算价明细断言与 Boss 配置核对。
- rc: **超人次费用已配置但价格为 0 不允许**（R6）；现金 Preview/Create 应返回兜底错误 `500.042.019`。
- rc: **全文 `payment` 字段预期以需求 2.2.1 为准**（2.5 作废）；客户预收费/权益支付各阶段均为 `NO_PAYMENT_REQUIRED` + 子项 `null`；现金（权益抵扣）`paymentStatus`/`timeline` 按 2.2.1 返回；`price`/`charges`/`deductions` 在需求标注处写 **按saas返回**（待补充明细）。
- rc: Membership 现金（DP 收款）**入参**以 2.2.2 为准：`cashPaymentApplied=false` + `cashier.paymentMode=DP_COLLECT`；E-pass 点数不足用 **`500.042.005`**。
- rc: **Preview 阶段 SaaS 不校验会籍/权益，API 侧须保留校验**（2.2）；已补充客户预收费/现金/E-pass 入参成对及 `500.042.024`/`500.042.025` 用例。
- rc: **2.2.1「按saas返回」适用范围**：汇总表与 **Create/Detail** 步骤对 `price`/`charges`/`deductions` 写 **按saas返回**；**Preview 现金**仍保留 R1–R6 算价明细断言。
- rc: **paymentStatus 枚举分场景**：订单对象 `payment.paymentStatus` 用 **2.2.1**；`POST /v2/orders/payments` 响应顶层 `paymentStatus` 用 **2.3.3** 示例值 `PendingPayment`。
- rc: **E-pass bundle 只支持纯权益下单**；不支持现金 DP 收款与客户预收款；脑图 bundle 下「现金」章节执行时改负向/跳过。
- rc: **国内网点**（Lounge PB 等）prebooking/bundle 的 `"async": true` 与 `false` **无同步异步行为差异**。
- rc: 每个用例在**原有步骤之后**追加 **「数据」** 节点（`apifox链接` / `boss配置` / `saas截图` / `saas价格返回`），便于保存执行记录；脑图已挂「数据」子节点时优先导出脑图内容。

## 核对规则速查

| 规则项 | 口径 |
| --- | --- |
| Preview（现金） | 返回 `payment`；`paymentStatus`/`timeline`=`null`；算价明细按 R1–R6 断言 |
| BASE_PRICE quantity | 始终按订单总人数：`CARDHOLDER=1`、`GUEST=2` |
| BASE_PRICE amount | 始终 `quantity*unitPrice`，**与权益使用无关**；权益 3 时仍为 `1*超人次+2*超人次` |
| PREBOOKING_FEE（客户承担） | `details=[]`（客户承担，不返回预约费明细行） |
| PREBOOKING_FEE（用户承担） | `CARDHOLDER.amount=1*预约单价`、`GUEST.amount=2*预约单价`（合计 `预约单价*3`） |
| deductions（权益0） | `null`、`[]` 或不返回 |
| deductions（权益1） | 仅 `CARDHOLDER`：`quantity=1`，`unitAmount`/`amount` 为具体负值 |
| deductions（权益3） | `CARDHOLDER`+`GUEST`：`quantity=1/2`，各自 `unitAmount`/`amount` 为具体负值 |
| Create（需支付） | `paymentStatus=PENDING_PAYMENT`；`timeline` 全 `null`；`price`/`charges`/`deductions` **按saas返回**；`status=9` |
| Create（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions` **按saas返回** |
| Order Detail（0元） | `paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions` **按saas返回** |
| 客户预收费/权益支付（Preview） | 返回 `payment`；`paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions=null` |
| 客户预收费/权益支付（Create/Detail） | 返回 `payment`；`paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；`price`/`charges`/`deductions=null` |
| 超人次价格为 0（已配置） | **不允许**；Preview/Create 返回兜底错误 `500.042.019`，不产生可履约订单 |
| 金额关系 | （1）charges 各行 `amount=quantity*unitPrice`；（2）正向合计=`originalAmount`；（3）abs(deductions)=`deductionAmount`；（4）original-deduction=`payableAmount` |
| E-pass bundle 支付 | **仅纯权益**；禁止 `toUseUsageCount`+`DP_COLLECT`、禁止 `cashPaymentApplied=true` / `CLIENT_COLLECT` |
| 国内网点 async | `async=true` 与 `false` 行为一致，无同步/异步之分 |

## 假定价格与 Preview 预期值（核对用）

各 **R 使用不同单价**，便于改配置后按对应用例核对。预约人数均为 **3**。

| 判定 | overNumFee | prebookPrice | 说明 |
| --- | --- | --- | --- |
| **R1** | **13.5** | 12（客户承担） | 仅收超人次；`PREBOOKING_FEE.details=[]` |
| **R2** | **10** | 0 | 仅收超人次；预约费为 0 |
| **R4** | **15.5** | **11** | 超人次 + 用户预约费 |
| **R5** | **8.5** | 0 | 仅收超人次；用户预约费价格为 0 |
| **R6** | **0** | **14** | 非法：超人次价 0 → 兜底错误 |

"""

HEADER_SUFFIX = """
> 上表供 Preview 算价明细断言参考；Create/Detail 的 `price`/`charges`/`deductions` 按 2.2.1 写 **按saas返回**。

"""

RULE_CFG: Dict[str, Dict[str, object]] = {
    "R1": {
        "cust_prebook": True,
        "user_prebook": False,
        "over_price": True,
        "prebook_zero": False,
        "refund": False,
        "over_num_fee": 13.5,
        "prebook_price": 12.0,
    },
    "R2": {
        "cust_prebook": True,
        "user_prebook": False,
        "over_price": True,
        "prebook_zero": True,
        "refund": False,
        "over_num_fee": 10.0,
        "prebook_price": 0.0,
    },
    "R4": {
        "cust_prebook": False,
        "user_prebook": True,
        "over_price": True,
        "prebook_zero": False,
        "refund": True,
        "over_num_fee": 15.5,
        "prebook_price": 11.0,
    },
    "R5": {
        "cust_prebook": False,
        "user_prebook": False,
        "over_price": True,
        "prebook_zero": True,
        "refund": False,
        "over_num_fee": 8.5,
        "prebook_price": 0.0,
    },
    "R6": {
        "cust_prebook": False,
        "user_prebook": True,
        "over_price": False,
        "prebook_zero": False,
        "refund": False,
        "over_num_fee": 0.0,
        "prebook_price": 14.0,
    },
}


def _OverNumFee(cfg: Dict[str, object]) -> float:
    return float(cfg["over_num_fee"])


def _PrebookPrice(cfg: Dict[str, object]) -> float:
    return float(cfg["prebook_price"])


def _BaseCh(cfg: Dict[str, object]) -> float:
    return _OverNumFee(cfg)


def _BaseG(cfg: Dict[str, object]) -> float:
    return _OverNumFee(cfg) * 2


def _BaseTotal(cfg: Dict[str, object]) -> float:
    return _OverNumFee(cfg) * 3


def _PrebookCh(cfg: Dict[str, object]) -> float:
    return _PrebookPrice(cfg)


def _PrebookG(cfg: Dict[str, object]) -> float:
    return _PrebookPrice(cfg) * 2


def _PrebookTotalAmount(cfg: Dict[str, object]) -> float:
    if cfg.get("cust_prebook") and not cfg.get("prebook_zero"):
        return 0.0
    if cfg.get("user_prebook"):
        return _PrebookPrice(cfg) * 3
    return 0.0


def _FmtAmount(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return str(value)


def _PrebookTotal(cfg: Dict[str, object]) -> float:
    return _PrebookTotalAmount(cfg)


def _ComputePrice(
    usage: int, cfg: Dict[str, object], *, no_deduct: bool
) -> Tuple[float, float, float]:
    base_total = _BaseTotal(cfg) if cfg.get("over_price") else 0.0
    original = base_total + _PrebookTotal(cfg)
    if no_deduct or usage == 0 or not cfg.get("over_price"):
        deduction = 0.0
    elif usage == 1:
        deduction = _OverNumFee(cfg)
    else:
        deduction = _BaseTotal(cfg)
    payable = original - deduction
    return original, deduction, payable


def _BasePriceExpect(cfg: Dict[str, object]) -> str:
    if not cfg.get("over_price"):
        return (
            "（2）`BASE_PRICE`（按订单总人数）：`CARDHOLDER.quantity=1`、"
            f"`GUEST.quantity=2`、`unitPrice=0`、`amount=0`"
        )
    return (
        "（2）`BASE_PRICE`（按订单总人数）：`CARDHOLDER.quantity=1`、"
        f"`unitPrice={_FmtAmount(_OverNumFee(cfg))}`、"
        f"`amount={_FmtAmount(_BaseCh(cfg))}`；"
        f"`GUEST.quantity=2`、`unitPrice={_FmtAmount(_OverNumFee(cfg))}`、"
        f"`amount={_FmtAmount(_BaseG(cfg))}`（合计 "
        f"`{_FmtAmount(_BaseTotal(cfg))}`）"
    )


def _PrebookExpect(cfg: Dict[str, object]) -> str:
    if cfg.get("cust_prebook") and not cfg.get("prebook_zero"):
        return "（3）`PREBOOKING_FEE`：`details=[]`（客户承担预约费）"
    if cfg.get("user_prebook"):
        return (
            "（3）`PREBOOKING_FEE`：`CARDHOLDER.quantity=1`、"
            f"`unitPrice={_FmtAmount(_PrebookPrice(cfg))}`、"
            f"`amount={_FmtAmount(_PrebookCh(cfg))}`；"
            f"`GUEST.quantity=2`、`unitPrice={_FmtAmount(_PrebookPrice(cfg))}`、"
            f"`amount={_FmtAmount(_PrebookG(cfg))}`（合计 "
            f"`{_FmtAmount(_PrebookTotalAmount(cfg))}`）"
        )
    return "（3）`PREBOOKING_FEE` 不返回或 `amount=0`"


def _DeductionsExpect(
    usage: int, cfg: Dict[str, object], *, no_deduct: bool
) -> str:
    if no_deduct or usage == 0 or not cfg.get("over_price"):
        return "（4）`deductions`：返回 `null`、`[]` 或不返回该字段"
    if usage == 1:
        return (
            "（4）`deductions`：`strategy=ENTITLEMENT`、`appliedTo=BASE_PRICE`；"
            "仅 `CARDHOLDER`："
            f"`quantity=1`、`unitAmount=-{_FmtAmount(_OverNumFee(cfg))}`、"
            f"`amount=-{_FmtAmount(_OverNumFee(cfg))}`"
        )
    ded = (
        "（4）`deductions`：`strategy=ENTITLEMENT`、`appliedTo=BASE_PRICE`；"
        f"`CARDHOLDER`：`quantity=1`、`unitAmount=-{_FmtAmount(_OverNumFee(cfg))}`、"
        f"`amount=-{_FmtAmount(_OverNumFee(cfg))}`；"
        f"`GUEST`：`quantity=2`、`unitAmount=-{_FmtAmount(_OverNumFee(cfg))}`、"
        f"`amount=-{_FmtAmount(_BaseG(cfg))}`"
    )
    if cfg.get("user_prebook"):
        ded += "（不抵预约费）"
    return ded + ""


def _PriceExpect(
    usage: int, cfg: Dict[str, object], *, no_deduct: bool
) -> str:
    original, deduction, payable = _ComputePrice(usage, cfg, no_deduct=no_deduct)
    return (
        "（5）`payment.price`："
        f"`originalAmount={_FmtAmount(original)}`、"
        f"`deductionAmount={_FmtAmount(deduction)}`、"
        f"`payableAmount={_FmtAmount(payable)}`"
    )


def _PriceHint(rule: str, cfg: Dict[str, object]) -> str:
    if rule == "R6":
        return (
            f"- 假定单价（{rule}）：`overNumFee=0`、`prebookPrice="
            f"{_FmtAmount(_PrebookPrice(cfg))}`（超人次价 0 为非法配置）。\n"
        )
    if cfg.get("cust_prebook") and not cfg.get("prebook_zero"):
        return (
            f"- 假定单价（{rule}）：`overNumFee={_FmtAmount(_OverNumFee(cfg))}`、"
            f"`prebookPrice={_FmtAmount(_PrebookPrice(cfg))}`（客户承担，charges 不展示预约费）。\n"
        )
    if cfg.get("prebook_zero"):
        return (
            f"- 假定单价（{rule}）：`overNumFee={_FmtAmount(_OverNumFee(cfg))}`、"
            "`prebookPrice=0`。\n"
        )
    return (
        f"- 假定单价（{rule}）：`overNumFee={_FmtAmount(_OverNumFee(cfg))}`、"
        f"`prebookPrice={_FmtAmount(_PrebookPrice(cfg))}`。\n"
    )


def _RuleSummaryRows(rule: str) -> str:
    cfg = RULE_CFG[rule]
    if rule == "R6":
        return (
            "| 0/1/3 | Preview/Create 均返回 `code=-1`、`errCode=500.042.019`；"
            "不产生可履约订单 |\n"
        )
    rows: List[str] = []
    for usage in (0, 1, 3):
        bp = (
            f"`{_FmtAmount(_BaseCh(cfg))}` / `{_FmtAmount(_BaseG(cfg))}`，"
            f"合计 **{_FmtAmount(_BaseTotal(cfg))}**"
        )
        if cfg.get("cust_prebook") and not cfg.get("prebook_zero"):
            pb = "`details=[]`"
        elif cfg.get("user_prebook"):
            pb = (
                f"`{_FmtAmount(_PrebookCh(cfg))}` / `{_FmtAmount(_PrebookG(cfg))}`，"
                f"合计 **{_FmtAmount(_PrebookTotalAmount(cfg))}**"
            )
        else:
            pb = "不返回或 `amount=0`"
        if usage == 0:
            ded = "`null` 或 `[]`"
        elif usage == 1:
            ded = (
                f"仅 CH：`unitAmount=-{_FmtAmount(_OverNumFee(cfg))}`、"
                f"`amount=-{_FmtAmount(_OverNumFee(cfg))}`"
            )
        else:
            ded = (
                f"CH `-{_FmtAmount(_OverNumFee(cfg))}`；G `-{_FmtAmount(_BaseG(cfg))}`"
            )
            if cfg.get("user_prebook"):
                ded += "（不抵预约费）"
        orig, ded_amt, pay = _ComputePrice(usage, cfg, no_deduct=False)
        rows.append(
            f"| {usage} | {bp} | {pb} | {ded} | "
            f"`original={_FmtAmount(orig)}`，`deduction={_FmtAmount(ded_amt)}`，"
            f"`payable={_FmtAmount(pay)}` |\n"
        )
    return "".join(rows)


def _BuildHeader() -> str:
    titles = {
        "R1": "R1：客户承担预约费 + 超人次有价",
        "R2": "R2：客户承担预约费 + 预约费为 0 + 超人次有价",
        "R4": "R4：用户承担预约费 + 超人次有价",
        "R5": "R5：用户预约费为 0 + 超人次有价",
        "R6": "R6：超人次已配置但价格为 0（非法配置）",
    }
    parts = [HEADER_PREFIX]
    for rule in ("R1", "R2", "R4", "R5", "R6"):
        parts.append(f"### {titles[rule]}\n\n")
        if rule == "R6":
            parts.append("| 权益点数 | 预期 |\n| --- | --- |\n")
        else:
            parts.append(
                "| 权益点数 | BASE_PRICE（CH/G） | PREBOOKING_FEE | deductions | "
                "payment.price |\n| --- | --- | --- | --- | --- |\n"
            )
        parts.append(_RuleSummaryRows(rule))
        parts.append("\n")
    parts.append(HEADER_SUFFIX)
    return "".join(parts)


def _Usage(pc: str) -> Optional[int]:
    m = re.search(r"使用权益点数为\s*(\d+)", pc)
    if m:
        return int(m.group(1))
    m = re.search(r"使用权益点数(\d+)", pc)
    return int(m.group(1)) if m else None


def _Rule(pc: str) -> Optional[str]:
    m = re.search(r"对应\s*(R[1-7])", pc)
    return m.group(1) if m else None


def _Payable(rule: str, usage: int, cfg: Dict[str, object]) -> str:
    _, _, payable = _ComputePrice(usage, cfg, no_deduct=False)
    return _FmtAmount(payable)


def _PreviewExpect(
    rule: str, usage: int, cfg: Dict[str, object], *, no_deduct: bool
) -> str:
    parts = [
        "（1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`",
        _BasePriceExpect(cfg),
        _PrebookExpect(cfg),
        _DeductionsExpect(usage, cfg, no_deduct=no_deduct),
        _PriceExpect(usage, cfg, no_deduct=no_deduct),
        "（6）校验 `payment.currency` 及金额关系（1）（2）（3）（4）",
    ]
    return "；".join(parts) + "。"


def _RewriteCashEquityBlock(
    title: str,
    body: List[str],
    section: str,
    *,
    is_epass: bool,
    no_deduct: bool,
) -> List[str]:
    pc = next((ln[5:].strip() for ln in body if ln.startswith("- pc:")), "")
    rule = _Rule(pc)
    usage = _Usage(pc)
    if not rule or usage is None or rule not in RULE_CFG:
        return [f"### {title}\n", *body]
    cfg = RULE_CFG[rule]
    ent = "toUseUsageCount" if is_epass else "toUseEntitlementCount"
    payable_zero = _ComputePrice(usage, cfg, no_deduct=no_deduct)[2] == 0
    tag = next((ln for ln in body if ln.startswith("- tag:")), None)

    out: List[str] = [f"### {title}\n", "\n"]
    out.append(f"- pc: {pc}\n")
    out.append(_PriceHint(rule, cfg))
    out.append(
        f"- 调用预览订单接口，传入 `cashPaymentApplied=false`、"
        f"`cashier.paymentMode=DP_COLLECT`、`{ent}={usage}`。\n"
    )
    out.append(f"  - {_PreviewExpect(rule, usage, cfg, no_deduct=no_deduct)}\n")
    out.append("- 调用创建订单接口。\n")
    if payable_zero:
        out.append(
            "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
            "`timeline` 返回 `null`，订单不进入 `status=9`（可为 `status=1` 或 `status=5`）。\n"
        )
    else:
        out.append(
            "  - Create 返回完整 `payment`，`paymentStatus=PENDING_PAYMENT`，"
            "`timeline` 返回但值全部为 `null`，订单状态进入 `status=9`。\n"
        )
    out.append("- 查询订单详情接口。\n")
    if payable_zero:
        out.append(
            "  - Order Detail 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
            "`timeline=null`；0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline=null`。\n"
        )
    elif cfg.get("refund"):
        out.append(
            "  - （1）Order Detail 未支付时保持待支付；支付成功后 `paymentStatus` 与 "
            "`timeline.authorizedAt/paidAt` 按支付状态返回；"
            "（2）退款后 `paymentStatus=REFUNDED`，`timeline` 含 "
            "`authorizedAt/paidAt/refundedAt`。\n"
        )
    else:
        out.append(
            "  - Order Detail 返回完整 `payment`，未支付时保持待支付状态；"
            "支付成功后 `paymentStatus` 按支付状态返回，"
            "`timeline.authorizedAt/paidAt` 按支付状态返回。\n"
        )
    out.append("- 调用 `POST /v2/orders/payments`。\n")
    if payable_zero:
        out.append(
            "  - 返回 `errCode=500.000.802`，"
            "`msg=Payment is not required for the specified order.`。\n"
        )
    else:
        out.append(
            "  - 返回可拉起收银台的支付动作，`paymentAction.type=REDIRECT` "
            "且返回有效收银台链接。\n"
        )
    if tag:
        out.append(f"{tag}\n")
    out.append("")
    return out


def _RewriteNoDeductError(title: str, body: List[str]) -> List[str]:
    return [
        f"### {title}\n",
        "",
        "- 弹出合理提示\n",
        "  - 返回 `code=-1`，`errCode=500.042.010`，"
        "`msg=Sorry, we're unable to process your order at the moment. "
        "Please try again later or contact DragonPass support team.`。\n",
        "",
    ]


def _RewriteOverNumZeroError(
    title: str, body: List[str], *, is_epass: bool
) -> List[str]:
    pc = next((ln[5:].strip() for ln in body if ln.startswith("- pc:")), "")
    usage = _Usage(pc)
    tag = next((ln for ln in body if ln.startswith("- tag:")), None)
    ent = "toUseUsageCount" if is_epass else "toUseEntitlementCount"
    usage_val = usage if usage is not None else 0
    out: List[str] = [f"### {title}\n", "\n"]
    if pc:
        out.append(f"- pc: {pc}\n")
    out.append(_PriceHint("R6", RULE_CFG["R6"]))
    out.append(
        f"- 调用预览订单接口，传入 `cashPaymentApplied=false`、"
        f"`cashier.paymentMode=DP_COLLECT`、`{ent}={usage_val}`。\n"
    )
    out.append(
        "  - 超人次费用已配置但价格为 0，不允许算价；返回 `code=-1`、"
        "`errCode=500.042.019`，"
        "`msg=Temporarily unable to preview the order. Please try again later.`。\n"
    )
    out.append("- 调用创建订单接口。\n")
    out.append(
        "  - 与 Preview 一致返回兜底错误 `500.042.019`，不产生可履约订单。\n"
    )
    if tag:
        out.append(f"{tag}\n")
    out.append("")
    return out


def _ClientEntitlementPaymentExpect() -> str:
    return (
        "返回 `payment` 对象，`paymentStatus=NO_PAYMENT_REQUIRED`，`timeline=null`，"
        "`currency` 正常返回；`price`、`charges`、`deductions` 均为 `null`"
    )


def _RewriteClientPrecharge(title: str, body: List[str]) -> List[str]:
    pc = next((ln[5:].strip() for ln in body if ln.startswith("- pc:")), "")
    tag = next((ln for ln in body if ln.startswith("- tag:")), None)
    # 保留脑图原始入参描述行
    preview_param = next(
        (
            ln.strip()
            for ln in body
            if "调用 Membership Preview" in ln or "Membership Preview" in ln
        ),
        None,
    )
    create_param = next(
        (ln.strip() for ln in body if "Membership Create" in ln and "Preview" in ln),
        None,
    )
    is_error = any("报错" in ln for ln in body)
    out: List[str] = [f"### {title}\n", "\n"]
    if pc:
        out.append(f"- pc: {pc}\n")
    if is_error:
        out.append("- 调用预览订单接口。\n")
        out.append("  - 返回 `code=-1`，`errCode=500.042.010` 或权益/参数相关业务错误。\n")
        out.append("- 调用创建订单接口。\n")
        out.append("  - 与 Preview 一致报错，不产生可履约订单。\n")
    else:
        out.append("- 调用预览订单接口。\n")
        if preview_param and preview_param.startswith("- "):
            out.append(f"  {preview_param[2:]}\n")
        out.append(
            f"  - Preview 成功并选择客户预收费商品；{_ClientEntitlementPaymentExpect()}。\n"
        )
        out.append("- 调用创建订单接口。\n")
        if create_param and create_param.startswith("- "):
            out.append(f"  {create_param[2:]}\n")
        out.append(
            f"  - Create 成功；{_ClientEntitlementPaymentExpect()}；"
            "不进入 `status=9`；权益扣减正确。\n"
        )
        out.append("- 查询订单详情接口。\n")
        out.append(
            f"  - Order Detail 订单状态正确；{_ClientEntitlementPaymentExpect()}。\n"
        )
        out.append("- 调用 `POST /v2/orders/payments`。\n")
        out.append(
            "  - 返回 `errCode=500.000.802`，"
            "`msg=Payment is not required for the specified order.`。\n"
        )
    if tag:
        out.append(f"{tag}\n")
    out.append("")
    return out


def _RewriteEntitlementPreview(title: str, body: List[str]) -> List[str]:
    if "Preview" not in title and not any("Preview" in ln for ln in body):
        return [f"### {title}\n", *body]
    out: List[str] = [f"### {title}\n", "\n"]
    for ln in body:
        if ln.strip() == "- 调用 Membership Preview。":
            out.append(ln)
            out.append(
                f"  - Preview 成功并选择权益支付商品；{_ClientEntitlementPaymentExpect()}；"
                "API 仍校验会籍状态与权益点数。\n"
            )
        elif ln.strip().startswith("- 查询订单详情"):
            out.append(ln)
        elif ln.strip().startswith("  -") and "订单状态" in ln:
            out.append(
                f"  - Create/Order Detail 均 {_ClientEntitlementPaymentExpect()}；"
                "订单状态与权益扣减正确。\n"
            )
        else:
            out.append(ln)
    if not out[-1].endswith("\n\n"):
        out.append("")
    return out


def _FixGenericPaymentCheck(text: str) -> str:
    old = (
        "- 校验 `payment.charges`\n"
        "  - (1)包含 `BASE_PRICE`、`PREBOOKING_FEE`、`ENTITLEMENT_DEDUCTION`；(2)`BASE_PRICE.unitPrice` 取 `overNumFee`，`PREBOOKING_FEE.  unitPrice` 取  (3)`paxType=CARDHOLDER/GUEST` 返回 `quantity`、`unitPrice`、`amount`。\n"
        "- 校验权益抵扣明细。\n"
        "  - DP 权益和第三方权益抵扣金额均按负数计入，持卡人抵扣金额对应`ownerDeductionAmount`，随行人抵扣金额对应`followDeductionAmount`，且 `appliedTo=[\"BASE_PRICE\"]` 且`strategy=[\"ENTITLEMENT\"]` 。\n"
        "- 校验 `payment.charges` 与 `payment.price` 金额关系。\n"
        "  - （1）`sum(BASE_PRICE.details.amount)+sum(PREBOOKING_FEE.details.amount)=payment.price.originalAmount`， （2）`abs(sum(ENTITLEMENT_DEDUCTION.details.amount))=payment.price.discountAmount`， （3）`originalAmount-discountAmount=payableAmount`"
    )
    new = (
        "- 校验 `payment.price`。\n"
        "  - `originalAmount`、`deductionAmount`、`payableAmount`、`currency` 与同用例 "
        "`假定单价（R*）` 及 Preview 预期一致。\n"
        "- 校验 `payment.charges`。\n"
        "  - 包含 `BASE_PRICE`、`PREBOOKING_FEE`；`unitPrice` 与对应用例 R 的假定单价一致。\n"
        "- 校验 `payment.deductions`。\n"
        "  - `strategy=ENTITLEMENT`，`appliedTo=BASE_PRICE`；抵扣金额为负数。\n"
        "- 校验金额关系（1）（2）（3）（4）。\n"
        "  - charges 各行 `amount=quantity*unitPrice`；正向合计=`originalAmount`；"
        "abs(deductions)=`deductionAmount`；差值=`payableAmount`。"
    )
    text = text.replace(old, new)
    old_epass = (
        "- 校验 `payment.charges`/`payment.deductions`\n"
        "  - (1)包含 `BASE_PRICE`、`PREBOOKING_FEE`、`ENTITLEMENT_DEDUCTION`"
    )
    if old_epass.split("\n")[0] in text:
        text = text.replace(
            "- 校验 `payment.charges`/`payment.deductions`\n"
            "  - (1)包含 `BASE_PRICE`、`PREBOOKING_FEE`、`ENTITLEMENT_DEDUCTION`；(2)`BASE_PRICE.unitPrice` 取 `overNumFee`，`PREBOOKING_FEE.  unitPrice` 取  (3)`paxType=CARDHOLDER/GUEST` 返回 `quantity`、`unitPrice`、`amount`。\n"
            "- 校验权益抵扣明细。\n"
            "  - DP 权益和第三方权益抵扣金额均按负数计入，持卡人抵扣金额对应`ownerDeductionAmount`，随行人抵扣金额对应`followDeductionAmount`，且 `appliedTo=[\"BASE_PRICE\"]`。\n"
            "- 校验 `payment.charges`/`payment.deductions` 与 `payment.price` 金额关系。\n"
            "  - （1）`sum(BASE_PRICE.details.amount)+sum(PREBOOKING_FEE.details.amount)=payment.price.originalAmount`， （2）`abs(sum(ENTITLEMENT_DEDUCTION.details.amount))=payment.price.deductionAmount`， （3）`originalAmount-deductionAmount=payableAmount`",
            new,
        )
    text = re.sub(
        r"- 校验 `payment\.price`。\n"
        r"  - `originalAmount`、`deductionAmount`、`payableAmount`、`currency` 与 SaaS 算价结果一致[^\n]+\n"
        r"- 校验 `payment\.price`。\n",
        "- 校验 `payment.price`。\n",
        text,
    )
    text = text.replace("`payment.breakdown`", "`payment.charges`/`payment.deductions`")
    text = text.replace("discountAmount", "deductionAmount")
    text = text.replace(
        "`paymentStatus` 与 `timeline` 字段不返回",
        "`paymentStatus` 与 `timeline` 返回 `null`",
    )
    return text


def _NormalizePaymentStageText(text: str) -> str:
    """对齐需求 2.2.1 标红变更：0 元 Detail timeline=null；客户预收费非 payment={}。"""
    text = text.replace(
        "`timeline={}`；0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline={}`",
        "`timeline=null`；0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline=null`",
    )
    text = text.replace(
        "`paymentStatus=NO_PAYMENT_REQUIRED`，`timeline={}`",
        "`paymentStatus=NO_PAYMENT_REQUIRED`，`timeline=null`",
    )
    text = text.replace(
        "Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，`timeline={}`",
        "Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，`timeline=null`",
    )
    return text


def _PatchSymbolicPreviewLines(text: str) -> str:
    """将脑图遗留的符号化 Preview 预期替换为假定单价数值。"""
    r1_u0 = (
        f"（1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`；"
        f"{_BasePriceExpect(RULE_CFG['R1'])[3:]}；"
        f"{_PrebookExpect(RULE_CFG['R1'])[3:]}；"
        f"{_DeductionsExpect(0, RULE_CFG['R1'], no_deduct=True)[3:]}；"
        f"{_PriceExpect(0, RULE_CFG['R1'], no_deduct=True)[3:]}"
    )
    r4_u0 = (
        f"（1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`；"
        f"{_BasePriceExpect(RULE_CFG['R4'])[3:]}；"
        f"{_PrebookExpect(RULE_CFG['R4'])[3:]}；"
        f"{_DeductionsExpect(0, RULE_CFG['R4'], no_deduct=True)[3:]}；"
        f"{_PriceExpect(0, RULE_CFG['R4'], no_deduct=True)[3:]}"
    )
    r6_u0 = (
        "（1）Preview 返回 `code=-1`、`errCode=500.042.019`，"
        "`msg=Temporarily unable to preview the order. Please try again later.`"
    )
    legacy = [
        (
            r"\(1\)Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`；"
            r"\(2\)`BASE_PRICE` 明细为 `CARDHOLDER\.quantity=1`、`GUEST\.quantity=2`、"
            r"`amount=3\*超人次价格`；\(3\)不返回有效 `PREBOOKING_FEE`；"
            r"\(4\)`deductions` 无有效 `ENTITLEMENT` 抵扣；\(5\)`payableAmount=3\*超人次价格`。",
            r1_u0 + "。",
        ),
        (
            r"（1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`； "
            r"（2）`BASE_PRICE` 明细为 `CARDHOLDER\.quantity=1`、`GUEST\.quantity=2`、"
            r"`amount=3\*超人次价格`；（3）`PREBOOKING_FEE` 明细为 `CARDHOLDER\.quantity=1`、"
            r"`GUEST\.quantity=2`、`amount=预约单价\*3`； （4）`deductions` 无有效抵扣； "
            r"（5）`payableAmount=预约单价\*3\+3\*超人次价格`。",
            r4_u0 + "。",
        ),
        (
            r"（1）Preview 返回完整 `payment`，`paymentStatus` 与 `timeline` 返回 `null`； "
            r"（2）`BASE_PRICE` 金额为 0； （3）`PREBOOKING_FEE` 明细为 `CARDHOLDER\.quantity=1`、"
            r"`GUEST\.quantity=2`、`amount=预约单价\*3`； （4）`deductions` 无有效抵扣； "
            r"（5）`payableAmount=预约单价\*3`。",
            r6_u0 + "。",
        ),
    ]
    for pattern, repl in legacy:
        text = re.sub(pattern, repl, text)
    return text


def _FixResidualPaymentObject(text: str) -> str:
    """主 E2E 文档遗留的 payment object:{} / 为空对象 / payment 返回 {}。"""
    expect = _ClientEntitlementPaymentExpect()
    entitlement_preview = (
        f"Preview 成功并选择权益支付商品；{expect}；API 仍校验会籍状态与权益点数"
    )
    text = text.replace("payment object:{}", expect)
    text = text.replace(
        "Preview 成功并选择权益支付商品，`payment` 为空对象",
        entitlement_preview,
    )
    text = text.replace(
        "Preview 成功并选择权益支付商品；`payment` 返回 `{}`，不展示现金金额；API 仍校验会籍状态与权益点数。",
        entitlement_preview + "。",
    )
    text = text.replace(
        "创单成功并选择权益支付商品 payment object:{}， 且",
        f"创单成功并选择权益支付商品；{expect}；且",
    )
    text = text.replace(
        "创单成功并选择权益支付商品\n",
        f"创单成功并选择权益支付商品；{expect}；\n",
    )
    text = text.replace(
        "订单状态=待使用、权益扣减正确；payment object:{}",
        f"订单状态=待使用、权益扣减正确；{expect}",
    )
    text = text.replace(
        "订单状态、权益扣减正确；payment object:{}",
        f"订单状态、权益扣减正确；{expect}",
    )
    text = text.replace(
        "订单状态、权益扣减正确；\n",
        f"订单状态、权益扣减正确；{expect}。\n",
    )
    epass_pure = (
        "纯权益支付：`extra.payment` 返回 `payment` 对象，`paymentStatus=NO_PAYMENT_REQUIRED`，"
        "`timeline=null`，`currency` 正常返回；`price`/`charges`/`deductions=null`；"
        "不传 `cashier`（**2.2.1**）"
    )
    text = text.replace("- ，payment和cashier返回{}", f"- {epass_pure}")
    text = text.replace(
        "- 纯权益支付，payment和cashier返回{}",
        f"- {epass_pure}",
    )
    text = text.replace("payment.status", "`paymentStatus`")
    text = text.replace("H5_CASHIE", "H5_CASHIER")
    text = text.replace(
        "  - Preview 成功并选择权益支付商品，\n",
        "",
    )
    return text


def _PreviewDocBusinessRules() -> str:
    return """## 业务计算规则

| 规则项 | 计算口径 | 说明 |
| --- | --- | --- |
| 应付价格 | `应付价格=超人次费用+预约费用` | 附件 R1-R6 的统一计算口径 |
| 预约费用-客户承担 | `预约费用=0` | prebooking fee 付费方式为客户时，用户侧应付价格不包含预约费用 |
| 预约费用-用户承担且单价非0 | `预约费用=预约单价*3` | 预约 3 人，每人收取预约费用 |
| 预约费用-用户承担且单价为0 | `预约费用=0` | 预约单价为 0 时不产生预约费用 |
| 超人次费用-使用权益点数0 | `超人次费用=3*超人次价格` | 预约 3 人均未使用权益点数抵扣超人次费用 |
| 超人次费用-使用权益点数1 | `超人次费用=2*超人次价格` | 抵扣 1 人后，应付超人次费用剩余 2 人份 |
| 超人次费用-使用权益点数3 | `超人次费用=0` | 预约 3 人均使用权益点数，应付超人次费用为 0 |
| BASE_PRICE 明细 | 始终按订单总人数：`CARDHOLDER=1`、`GUEST=2` | `amount=quantity*unitPrice`，**与权益使用无关**；抵扣在 `deductions` |
| 收银台后续判断 | 应付价格非0时，后续创建/支付链路应可拉取收银台 | 预览阶段 `paymentStatus`/`timeline` 返回 `null` |

"""


def _PreviewDocPaymentDetail() -> str:
    return """## payment明细对象预期

| 对象 | type/strategy | 明细预期 |
| --- | --- | --- |
| `charges` | `BASE_PRICE` | 按订单总人数：`CARDHOLDER.quantity=1`、`GUEST.quantity=2`；`amount=quantity*unitPrice`（权益 3 时仍展示正向金额） |
| `charges` | `PREBOOKING_FEE` | 客户承担：`details=[]`；用户承担：`CARDHOLDER.quantity=1`、`GUEST.quantity=2`，`amount=quantity*预约单价` |
| `deductions` | `strategy=ENTITLEMENT` | 当前只支持权益抵扣；`appliedTo=BASE_PRICE`，只抵扣超人次费用，不抵扣预约费用 |
| `deductions.details` | `CARDHOLDER` | 使用 1 点权益时：`quantity=1`，`unitAmount`/`amount` 为负值 |
| `deductions.details` | `GUEST` | 使用 3 点权益时：`quantity=2`，`unitAmount`/`amount` 为负值 |
| 未使用权益 | — | `deductions` 返回 `null`、`[]` 或不返回该字段 |

"""


def _PreviewDocFieldSummary() -> str:
    return """## payment字段汇总预期

| 字段 | 现金（权益抵扣）预览预期 | 客户预收费/权益支付预览预期 |
| --- | --- | --- |
| `payment.price.originalAmount` | 等于 `charges` 中所有正向金额汇总 | `null` |
| `payment.price.deductionAmount` | 等于权益抵扣金额汇总，抵扣对象仅限 `BASE_PRICE` | `null` |
| `payment.price.payableAmount` | 等于 `originalAmount-deductionAmount` | `null` |
| `payment.charges.type=BASE_PRICE` | 按订单总人数返回 `CARDHOLDER`/`GUEST` 明细 | `null` |
| `payment.charges.type=PREBOOKING_FEE` | 客户承担 `details=[]`；用户承担按 3 人明细 | `null` |
| `payment.deductions.strategy=ENTITLEMENT` | 当前只支持权益抵扣 | `null` |
| `payment.deductions.appliedTo` | 只能为 `BASE_PRICE` | `null` |
| `paymentStatus` | 返回 `null` | `NO_PAYMENT_REQUIRED` |
| `timeline` | 返回 `null` | `null` |

"""


def _PreviewDocRMapping() -> str:
    r1_pay = (
        f"`original={_FmtAmount(_ComputePrice(0, RULE_CFG['R1'], no_deduct=False)[0])}`/"
        f"`{_FmtAmount(_ComputePrice(1, RULE_CFG['R1'], no_deduct=False)[2])}`/"
        f"`{_FmtAmount(_ComputePrice(3, RULE_CFG['R1'], no_deduct=False)[2])}`"
    )
    r2_pay = (
        f"`original={_FmtAmount(_ComputePrice(0, RULE_CFG['R2'], no_deduct=False)[0])}`/"
        f"`{_FmtAmount(_ComputePrice(1, RULE_CFG['R2'], no_deduct=False)[2])}`/"
        f"`{_FmtAmount(_ComputePrice(3, RULE_CFG['R2'], no_deduct=False)[2])}`"
    )
    r4_pay = (
        f"`original={_FmtAmount(_ComputePrice(0, RULE_CFG['R4'], no_deduct=False)[0])}`/"
        f"`{_FmtAmount(_ComputePrice(1, RULE_CFG['R4'], no_deduct=False)[2])}`/"
        f"`{_FmtAmount(_ComputePrice(3, RULE_CFG['R4'], no_deduct=False)[2])}`"
    )
    r5_pay = (
        f"`original={_FmtAmount(_ComputePrice(0, RULE_CFG['R5'], no_deduct=False)[0])}`/"
        f"`{_FmtAmount(_ComputePrice(1, RULE_CFG['R5'], no_deduct=False)[2])}`/"
        f"`{_FmtAmount(_ComputePrice(3, RULE_CFG['R5'], no_deduct=False)[2])}`"
    )
    null_api = (
        "`paymentStatus=NO_PAYMENT_REQUIRED`；`timeline=null`；"
        "`price`/`charges`/`deductions=null`"
    )
    cash_preview = (
        "返回完整 `payment`；`paymentStatus`/`timeline=null`；"
        "按假定单价表核对 `charges`/`deductions`/`price`"
    )
    return f"""## R1-R7组合预览预期映射

| 规则 | prebooking fee 付费方式 | prebooking fee 价格 | 超人次费用 | 超人次费用价格 | 客户预收费预览预期 | 权益支付预览预期 | 现金（权益抵扣）预览预期 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 | 客户 | 非0 | 设置 | 非0 | 业务口径：预约费用=0；应付价格 0/1/3 点分别为 {r1_pay}。接口：{null_api} | {null_api}；权益足够成功，不足返回权益不足 | {cash_preview}；`PREBOOKING_FEE.details=[]`；假定单价 `overNumFee=13.5`、`prebookPrice=12` |
| R2 | 客户 | 0 | 设置 | 非0 | 业务口径同 R1；预约费用=0。接口：{null_api} | {null_api} | {cash_preview}；假定单价 `overNumFee=10`、`prebookPrice=0` |
| R3 | 客户 | 非0 | 不设置 | - | 业务口径：预约费用=0，超人次费用=0，应付价格=0。接口：{null_api} | {null_api} | 返回 `payment` 0 元口径：`payableAmount=0`；无有效 `BASE_PRICE` |
| R4 | 用户 | 非0 | 设置 | 非0 | 业务口径：预约费用=33；应付价格 0/1/3 点分别为 {r4_pay}。接口：{null_api} | {null_api}；R4/R6 权益+现金待确认 | {cash_preview}；含 `PREBOOKING_FEE`；假定单价 `overNumFee=15.5`、`prebookPrice=11` |
| R5 | 用户 | 0 | 设置 | 非0 | 业务口径：预约费用=0；应付价格 0/1/3 点分别为 {r5_pay}。接口：{null_api} | {null_api} | {cash_preview}；假定单价 `overNumFee=8.5`、`prebookPrice=0` |
| R6 | 用户 | 非0 | 设置 | 0 | 业务口径：非法配置。接口：{null_api} | {null_api} | **Preview/Create 均返回 `errCode=500.042.019`**，不产生可履约订单 |
| R7 | 未配置 | - | 未配置 | - | 返回 `errCode=500.042.010` | 返回 `errCode=500.042.010` | 返回 `errCode=500.042.010` |

"""


def _RewritePreviewCashBlock(title: str, body: List[str]) -> List[str]:
    pc = next((ln[5:].strip() for ln in body if ln.startswith("- pc:")), "")
    rule = _Rule(pc)
    usage = _Usage(pc) or _Usage(title)
    tag = next((ln for ln in body if ln.startswith("- tag:")), None)
    if rule == "R6":
        usage_val = usage if usage is not None else 0
        out: List[str] = [f"#### {title}\n", "\n"]
        if pc:
            out.append(f"- pc: {pc}\n")
        out.append(_PriceHint("R6", RULE_CFG["R6"]))
        out.append("- 调用预览订单接口。\n")
        out.append(
            "  - 超人次费用已配置但价格为 0，不允许算价；返回 `code=-1`、"
            "`errCode=500.042.019`，"
            "`msg=Temporarily unable to preview the order. Please try again later.`。\n"
        )
        out.append("- 调用创建订单接口。\n")
        out.append(
            "  - 与 Preview 一致返回兜底错误 `500.042.019`，不产生可履约订单。\n"
        )
        if tag:
            out.append(f"{tag}\n")
        out.append("")
        return out
    if not rule or usage is None or rule not in RULE_CFG:
        return [f"#### {title}\n", *body]
    cfg = RULE_CFG[rule]
    payable_zero = _ComputePrice(usage, cfg, no_deduct=False)[2] == 0
    out = [f"#### {title}\n", "\n"]
    if pc:
        out.append(f"- pc: {pc}\n")
    out.append(_PriceHint(rule, cfg))
    out.append("- 调用预览订单接口。\n")
    out.append(f"  - {_PreviewExpect(rule, usage, cfg, no_deduct=False)}\n")
    out.append("- 调用创建订单接口。\n")
    if payable_zero:
        out.append(
            "  - Create 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
            "`timeline=null`，订单不进入 `status=9`。\n"
        )
    else:
        out.append(
            "  - Create 返回完整 `payment`，`paymentStatus=PENDING_PAYMENT`，"
            "`timeline` 返回但值全部为 `null`，订单状态进入 `status=9`。\n"
        )
    out.append("- 查询订单详情接口。\n")
    if payable_zero:
        out.append(
            "  - Order Detail 返回完整 `payment`，`paymentStatus=NO_PAYMENT_REQUIRED`，"
            "`timeline=null`；0 元订单取消后仍保持 `NO_PAYMENT_REQUIRED` 与 `timeline=null`。\n"
        )
    elif cfg.get("refund"):
        out.append(
            "  - Order Detail 返回完整 `payment`，`paymentStatus` 按支付状态返回；"
            "退款后 `paymentStatus=REFUNDED`，`timeline` 含 "
            "`authorizedAt/paidAt/refundedAt`。\n"
        )
    else:
        out.append(
            "  - Order Detail 返回完整 `payment`，未支付时保持待支付状态；"
            "支付成功后 `paymentStatus` 按支付状态返回，"
            "`timeline.authorizedAt/paidAt` 按支付状态返回。\n"
        )
    out.append("- 调用 `POST /v2/orders/payments`。\n")
    if payable_zero:
        out.append(
            "  - 返回 `errCode=500.000.802`，"
            "`msg=Payment is not required for the specified order.`。\n"
        )
    else:
        out.append(
            "  - 返回可拉起收银台的支付动作，`paymentAction.type=REDIRECT` "
            "且返回有效收银台链接。\n"
        )
    if tag:
        out.append(f"{tag}\n")
    out.append("")
    return out


def _RewritePreviewClientEntitlement(title: str, body: List[str], *, is_entitlement: bool) -> List[str]:
    pc = next((ln[5:].strip() for ln in body if ln.startswith("- pc:")), "")
    tag = next((ln for ln in body if ln.startswith("- tag:")), None)
    rc = next((ln for ln in body if ln.startswith("- rc:")), None)
    expect = _ClientEntitlementPaymentExpect()
    out: List[str] = [f"#### {title}\n", "\n"]
    if pc:
        out.append(f"- pc: {pc}\n")
    out.append(
        "- 按 R1/R2/R3 中客户预收费组合调用 "
        "`/v2/orders/{modules}/memberships/prebooking/preview`。\n"
        if not is_entitlement
        else "- 使用权益足够的账号调用 "
        "`/v2/orders/{modules}/memberships/prebooking/preview`。\n"
    )
    out.append(f"  - 接口返回成功；{expect}。\n")
    if is_entitlement:
        out.append("- 使用权益不足的账号或权益点数不足的数据调用预览订单接口。\n")
        out.append(
            "  - 接口返回权益不足错误，不因 SAAS 预览不校验权益点数而绕过 API 侧会籍和权益校验。\n"
        )
    out.append("- 使用同一业务数据继续调用创建订单接口和订单详情接口。\n")
    out.append(
        f"  - Create 与 Order Detail 阶段均 {expect}。\n"
    )
    if not is_entitlement:
        out.append("- 校验业务计算口径。\n")
        out.append(
            "  - R1/R2 中预约费用为 0，超人次应付按使用权益点数 0/1/3 分别为 "
            "3/2/0 人份超人次价格；R3 中预约费用和超人次费用均为 0。\n"
        )
    if rc:
        out.append(f"{rc}\n")
    if tag:
        out.append(f"{tag}\n")
    out.append("")
    return out


def PatchPreviewDoc() -> None:
    raw = PREVIEW_TARGET.read_text(encoding="utf-8")
    raw = _FixGenericPaymentCheck(raw)
    raw = _NormalizePaymentStageText(raw)

    # 替换汇总章节
    raw = re.sub(
        r"## 业务计算规则\n.*?(?=## payment阶段返回预期)",
        _PreviewDocBusinessRules(),
        raw,
        count=1,
        flags=re.S,
    )
    raw = re.sub(
        r"## payment明细对象预期\n.*?(?=## R1-R7组合预览预期映射)",
        _PreviewDocPaymentDetail(),
        raw,
        count=1,
        flags=re.S,
    )
    raw = re.sub(
        r"## R1-R7组合预览预期映射\n.*?(?=## payment字段汇总预期)",
        _PreviewDocRMapping(),
        raw,
        count=1,
        flags=re.S,
    )
    raw = re.sub(
        r"## payment字段汇总预期\n.*?(?=## 预览订单接口)",
        _PreviewDocFieldSummary(),
        raw,
        count=1,
        flags=re.S,
    )

    # R3 0元用例
    raw = raw.replace(
        "Preview 阶段 `paymentStatus` 与 `timeline` 字段不返回。",
        "Preview 阶段 `paymentStatus` 与 `timeline` 返回 `null`。",
    )

    lines = raw.splitlines(keepends=True)
    out: List[str] = []
    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            current_section = line.strip()
            out.append(line)
            i += 1
            continue
        if line.startswith("### "):
            current_section = line.strip()
            out.append(line)
            i += 1
            continue
        if line.startswith("#### tc-"):
            title = line.strip()[5:]
            i += 1
            block: List[str] = []
            while (
                i < len(lines)
                and not lines[i].startswith("#### tc-")
                and not lines[i].startswith("## ")
                and not lines[i].startswith("### ")
            ):
                block.append(lines[i])
                i += 1
            pc = next((b for b in block if b.startswith("- pc:")), "")
            usage = _Usage(pc or "") or _Usage(title)
            if (
                "现金（权益抵扣）" in current_section
                and _Rule(pc or "")
                and (usage is not None or _Rule(pc or "") == "R6")
            ):
                out.extend(_RewritePreviewCashBlock(title, block))
            elif "客户预收费" in current_section and "权益支付" not in current_section:
                out.extend(_RewritePreviewClientEntitlement(title, block, is_entitlement=False))
            elif current_section.endswith("### 权益支付") or (
                "权益支付" in current_section and "现金" not in current_section
            ):
                if "客户预收费" not in title:
                    out.extend(_RewritePreviewClientEntitlement(title, block, is_entitlement=True))
                else:
                    out.append(f"#### {title}\n")
                    out.extend(block)
            else:
                out.append(f"#### {title}\n")
                out.extend(block)
            continue
        out.append(line)
        i += 1

    text = "".join(out)
    text = text.replace(
        "预览阶段不返回 `paymentStatus` 和 `timeline` 字段",
        "预览阶段 `paymentStatus` 和 `timeline` 返回 `null`",
    )
    PREVIEW_TARGET.write_text(text, encoding="utf-8")
    print(f"rewrote {PREVIEW_TARGET}")


def Main() -> None:
    raw = TARGET.read_text(encoding="utf-8")
    raw = _FixGenericPaymentCheck(raw)
    # 去掉原 H1/测试范围，保留正文
    m = re.search(r"(## 商品初始化.*)", raw, re.S)
    body = m.group(1) if m else raw

    lines = body.splitlines(keepends=True)
    out: List[str] = [_BuildHeader()]
    current_section = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            current_section = line.strip()
            out.append(line if line.endswith("\n") else line + "\n")
            i += 1
            continue
        if line.startswith("### tc-"):
            title = line.strip()[4:]
            i += 1
            block: List[str] = []
            while i < len(lines) and not lines[i].startswith("### tc-") and not lines[i].startswith("## "):
                block.append(lines[i])
                i += 1
            pc = next((b for b in block if b.startswith("- pc:")), "")
            is_cash_eq = (
                ("现金（权益抵扣）" in current_section or "不支持权益抵扣" in current_section)
                and "客户预收费" not in current_section
            )
            is_no_deduct = "不支持权益抵扣" in current_section
            is_client = "客户预收费（权益抵扣）" in current_section or (
                "客户预收费" in current_section
                and "不使用权益" in current_section
            )
            is_epass = "E-pass" in current_section or "Epass" in current_section
            is_ent_preview = (
                "权益支付" in current_section
                and ("Preview" in title or any("Membership Preview" in b for b in block))
            )

            if is_cash_eq and _Rule(pc or "") and _Usage(pc or "") is not None:
                rule = _Rule(pc or "")
                if rule == "R6":
                    out.extend(
                        _RewriteOverNumZeroError(title, block, is_epass=is_epass)
                    )
                elif is_no_deduct and _Usage(pc or "") != 0:
                    out.extend(_RewriteNoDeductError(title, block))
                else:
                    out.extend(
                        _RewriteCashEquityBlock(
                            title,
                            block,
                            current_section,
                            is_epass=is_epass,
                            no_deduct=is_no_deduct,
                        )
                    )
            elif is_client:
                out.extend(_RewriteClientPrecharge(title, block))
            elif is_ent_preview and "Membership权益支付Preview" in title:
                out.extend(_RewriteEntitlementPreview(title, block))
            else:
                out.append(f"### {title}\n")
                out.extend(block)
            continue
        out.append(line)
        i += 1

    TARGET.write_text(
        _FixResidualPaymentObject(
            _NormalizePaymentStageText(_PatchSymbolicPreviewLines("".join(out)))
        ),
        encoding="utf-8",
    )
    print(f"rewrote {TARGET}")


if __name__ == "__main__":
    Main()
    PatchPreviewDoc()
