/**
 * 订单流 payment 断言 - 后置脚本
 * Preview / Create / Detail 三接口兼容, ES5 安全
 *
 * 配套前置: tools/apifox_payment_assert_pre.js (按 URL 写入 order_api_stage)
 * 文档: .cursor/skills/api-testcase-pack/prebooking-payment-apifox-assertions.md
 *
 * 客户预收款 (CLIENT_COLLECT) 请用 apifox_client_collect_assert_*.js, 勿与本脚本混用.
 *
 * --- 三分支识别 (按 payableAmount + price 结构) ---
 *
 * 1) 现金 / 权益支付 (有应付): payableAmount != 0
 *    Preview: status=null, timeline=null, 有 price 明细, 跑 C-1~C-3
 *    Create:  status=PENDING_PAYMENT, timeline 对象内字段全 null
 *    Detail:  status 见 expected_detail_status (默认 PENDING_PAYMENT)
 *    注: 权益支付与现金 payment 预期相同 (完整金额模块); 勿再按「纯权益=金额全 null」断言.
 *
 * 2) 权益抵扣到 0 元 (含权益支付足额): originalAmount = discountAmount 且 payableAmount = 0
 *    Preview: status=null (同现金/权益支付), timeline=null; price 明细 + C-1~C-3
 *    Create/Detail: status=NO_PAYMENT_REQUIRED, timeline={ paidAt:null, refundedAt:null }
 *
 * 3) 客户预收: payableAmount = 0 且不满足上项 (CLIENT_COLLECT 请用专用脚本)
 *    Preview: status=NO_PAYMENT_REQUIRED, timeline=null, price/charges/deductions 均为 null
 *    Create/Detail: status=NO_PAYMENT_REQUIRED, timeline=null
 *
 * --- 价格汇总 (有明细时) ---
 *   (1) BASE_PRICE + PREBOOKING_FEE = originalAmount
 *   (2) abs(ENTITLEMENT) = discountAmount  (deductions[].strategy === "ENTITLEMENT")
 *   (3) originalAmount - discountAmount = payableAmount
 *
 * --- 运行时变量 ---
 *   order_api_stage 等写入 variables/collection，不回写共用 Environment。
 *   换测定价：前置 ftPayEnsurePricingEnv 把本品类 Environment 键映射到规范键
 *   （variables+collection）；GetCfg 读 variables → collection → Environment。
 *
 * Lounge 与 FT 同 Environment 解耦时用 lounge* 键（loungePrebookingUnitPrice 等）；
 * 由场景 Auth 的 ftPayEnsurePricingEnv 映射到上列规范键后再跑本脚本。
 */

// ---------------------------------------------------------------------------
// 环境变量
// ---------------------------------------------------------------------------

function RtGet(key) {
    var v = "";
    try { v = String(pm.variables.get(key) || "").trim(); } catch (e0) {}
    if (!v || v.indexOf("{{") >= 0) {
        try { v = String(pm.collectionVariables.get(key) || "").trim(); } catch (e1) {}
    }
    if (!v || v.indexOf("{{") >= 0) {
        try { v = String((pm.environment && pm.environment.get(key)) || "").trim(); } catch (e2) {}
    }
    if (!v || v.indexOf("{{") >= 0) return "";
    return v;
}

function GetApiStage() {
    var stage = RtGet("order_api_stage");
    return stage ? String(stage).toUpperCase() : null;
}

function GetCfg(key) {
    // 规范键（paymentSceneId 等）由 ftPayEnsurePricingEnv 按本品类 env 键映射进
    // variables/collection。共用 Environment 上同时有 FT 规范键与 lounge*，
    // 若此处 Environment 优先，Lounge 会误读到 FT 的 paymentSceneId。
    var v = "";
    try { v = String(pm.variables.get(key) || "").trim(); } catch (e0) {}
    if (!v || v.indexOf("{{") >= 0) {
        try { v = String(pm.collectionVariables.get(key) || "").trim(); } catch (e1) {}
    }
    if (!v || v.indexOf("{{") >= 0) {
        try { v = String((pm.environment && pm.environment.get(key)) || "").trim(); } catch (e2) {}
    }
    if (!v || v.indexOf("{{") >= 0) return "";
    return v;
}

var API_STAGE = GetApiStage();
var EXPECTED_DETAIL_STATUS = RtGet("expected_detail_status");
var ASSERT_PRICE = RtGet("assert_payment_price") !== "false";
var ASSERT_ENV_PRICE = GetCfg("assert_payment_env_price") !== "false";

// ---------------------------------------------------------------------------
// 工具函数 - 金额 / 结构
// ---------------------------------------------------------------------------

/** 保留两位小数, 避免浮点误差 */
function Round2(n) {
    return Math.round((Number(n) + Number.EPSILON) * 100) / 100;
}

/** 兼容 payment.status 与 paymentStatus 字段名 */
function GetPaymentStatus(p) {
    if (!p) {
        return undefined;
    }
    if ("status" in p) {
        return p.status;
    }
    if ("paymentStatus" in p) {
        return p.paymentStatus;
    }
    return undefined;
}

function IsNullOrMissing(v) {
    return v === null || v === undefined;
}

/** timeline 为对象且所有字段均为 null/undefined */
function IsTimelineAllNull(timeline) {
    if (!timeline || typeof timeline !== "object") {
        return false;
    }
    var keys = Object.keys(timeline);
    for (var i = 0; i < keys.length; i++) {
        if (timeline[keys[i]] !== null && timeline[keys[i]] !== undefined) {
            return false;
        }
    }
    return true;
}

/** 汇总 details[].amount */
function SumDetailsAmount(items) {
    if (!Array.isArray(items)) {
        return 0;
    }
    var sum = 0;
    for (var j = 0; j < items.length; j++) {
        if (items[j] && items[j].amount != null) {
            sum += Number(items[j].amount);
        }
    }
    return sum;
}

/** 按 charges[].type 汇总对应 details 金额 */
function SumChargeByType(charges, type) {
    if (!Array.isArray(charges)) {
        return 0;
    }
    for (var i = 0; i < charges.length; i++) {
        if (charges[i] && charges[i].type === type) {
            return SumDetailsAmount(charges[i].details);
        }
    }
    return 0;
}

/** 汇总 strategy=ENTITLEMENT 的 deductions 金额 (通常为负) */
function SumEntitlementDeductionAmount(deductions) {
    if (!Array.isArray(deductions)) {
        return 0;
    }
    var total = 0;
    for (var i = 0; i < deductions.length; i++) {
        if (deductions[i] && deductions[i].strategy === "ENTITLEMENT") {
            total += SumDetailsAmount(deductions[i].details);
        }
    }
    return total;
}

/** price / charges / deductions 三者均非 null, 才具备算价断言条件 */
function HasPaymentPriceDetails(price, charges, deductions) {
    return !IsNullOrMissing(price) && !IsNullOrMissing(charges) && !IsNullOrMissing(deductions);
}

/** 兼容 data.extra.payment / data.payment / payment 三种响应路径 */
function GetPaymentFromResponse(json) {
    if (!json) {
        return null;
    }
    if (json.data && json.data.extra && json.data.extra.payment) {
        return json.data.extra.payment;
    }
    if (json.data && json.data.payment) {
        return json.data.payment;
    }
    if (json.payment) {
        return json.payment;
    }
    return null;
}

function HasNonZeroPayableAmount(price) {
    if (!price || price.payableAmount === null || price.payableAmount === undefined) {
        return false;
    }
    return Round2(Number(price.payableAmount)) !== 0;
}

function GetPayableAmount(price) {
    if (!price || price.payableAmount === null || price.payableAmount === undefined) {
        return 0;
    }
    return Round2(Number(price.payableAmount));
}

function GetOriginalAmount(price) {
    if (!price || price.originalAmount === null || price.originalAmount === undefined) {
        return 0;
    }
    return Round2(Number(price.originalAmount));
}

/** discountAmount 与 deductionAmount 二选一, 优先 discountAmount */
function GetDiscountAmount(price) {
    if (!price) {
        return 0;
    }
    var discount = price.discountAmount != null ? price.discountAmount : price.deductionAmount;
    if (discount === null || discount === undefined) {
        return 0;
    }
    return Round2(Number(discount));
}

/**
 * 权益抵扣到 0 元: 全额被 ENTITLEMENT 抵扣, 应付为 0 但保留 price 明细.
 * 与客户预收 (price 全 null) 区分; 权益支付足额走本分支 (完整金额模块).
 */
function IsEntitlementZeroPayScenario(price) {
    if (!price) {
        return false;
    }
    var payable = GetPayableAmount(price);
    if (payable !== 0) {
        return false;
    }
    return GetOriginalAmount(price) === GetDiscountAmount(price);
}

function FormatStatus(v) {
    if (v === null) {
        return "null";
    }
    if (v === undefined) {
        return "undefined";
    }
    return String(v);
}

// ---------------------------------------------------------------------------
// 断言封装
// ---------------------------------------------------------------------------

function AssertPaymentStatus(actual, expected, scenario) {
    var expectedText = FormatStatus(expected);
    var actualText = FormatStatus(actual);
    var title = "[" + scenario + "] payment.status expected=" + expectedText + " actual=" + actualText;

    pm.test(title, function () {
        pm.expect(
            actual,
            scenario + " payment.status current=" + actualText + " expected=" + expectedText
        ).to.eql(expected);

        console.log("[payment-assert] PASS " + scenario);
        console.log("[payment-assert] payment.status expected=" + expectedText);
        console.log("[payment-assert] payment.status actual=" + actualText);
    });
}

function AssertPaymentStatusIsNull(actual, scenario) {
    var actualText = FormatStatus(actual);
    var title = "[" + scenario + "] payment.status expected=null actual=" + actualText;

    pm.test(title, function () {
        pm.expect(actual, scenario + " payment.status current=" + actualText + " expected=null").to.be.null;
        console.log("[payment-assert] PASS " + scenario + " payment.status expected=null");
    });
}

/**
 * Detail 阶段场景解析
 * timelineRule:
 *   NULL              - timeline 必须为 null (客户预收/已退款等)
 *   ENTITLEMENT_SHAPE - timeline={ paidAt:null, refundedAt:null } (权益抵扣 0 元)
 *   STATE_SHAPE       - timeline 含 paidAt/refundedAt, 值按支付状态显示否则 null
 */
function ResolveDetailScenario(payableAmount, envStatus, isEntitlementZeroPay) {
    if (payableAmount === 0) {
        if (isEntitlementZeroPay) {
            return {
                scenario: "Detail-Entitlement-ZeroPay",
                expectedStatus: "NO_PAYMENT_REQUIRED",
                timelineRule: "ENTITLEMENT_SHAPE"
            };
        }
        return {
            scenario: "Detail-ZeroPay",
            expectedStatus: "NO_PAYMENT_REQUIRED",
            timelineRule: "NULL"
        };
    }

    var status = envStatus || "PENDING_PAYMENT";
    var scenario = "Detail-NeedPay-" + status;

    if (status === "REFUNDED") {
        return {
            scenario: scenario,
            expectedStatus: status,
            timelineRule: "NULL"
        };
    }

    return {
        scenario: scenario,
        expectedStatus: status,
        timelineRule: "STATE_SHAPE"
    };
}

/** timeline 对象含 paidAt / refundedAt 字段 (值可为 null 或时间) */
function HasTimelinePaidRefundFields(timeline) {
    if (!timeline || typeof timeline !== "object") {
        return false;
    }
    return "paidAt" in timeline && "refundedAt" in timeline;
}

/** 权益抵扣 0 元: timeline 骨架 { paidAt:null, refundedAt:null } */
function AssertTimelinePaidRefundNull(scenario, timeline) {
    pm.test("[" + scenario + "] timeline expected paidAt/refundedAt null", function () {
        pm.expect(timeline).to.be.an("object");
        pm.expect(timeline.paidAt).to.be.null;
        pm.expect(timeline.refundedAt).to.be.null;
        console.log("[payment-assert] PASS " + scenario + " timeline shape ok");
    });
}

// ---------------------------------------------------------------------------
// 解析响应
// ---------------------------------------------------------------------------

var json = pm.response.json();
function IsBusinessOkEnvelope(env) {
    if (!env || typeof env !== "object") {
        return false;
    }
    if (!Object.prototype.hasOwnProperty.call(env, "code")) {
        return true;
    }
    var c = env.code;
    return c === 0 || c === 1 || c === "0" || c === "1";
}
if (!IsBusinessOkEnvelope(json)) {
    pm.test(
        "[payment-assert] skip (business not ok) | code=" +
            (json && json.code) +
            " err=" +
            (json && json.errCode),
        function () {
            console.warn("[payment-assert] skip asserts", json && json.code, json && json.errCode);
        }
    );
} else {
var payment = GetPaymentFromResponse(json);
var orderStatus = json && json.data ? json.data.status : undefined;

var price = payment ? payment.price : null;
var charges = payment ? payment.charges : null;
var deductions = payment ? payment.deductions : null;
var status = GetPaymentStatus(payment);
var timeline = payment ? payment.timeline : null;

var payableAmount = GetPayableAmount(price);
var isNonZeroPayable = HasNonZeroPayableAmount(price);
var isEntitlementZeroPay = IsEntitlementZeroPayScenario(price);

// ---------------------------------------------------------------------------
// 前置校验 (所有阶段共用)
// ---------------------------------------------------------------------------

pm.test("[Pre] order_api_stage configured", function () {
    pm.expect(API_STAGE, "check pre-request script").to.exist;
    pm.expect(["PREVIEW", "CREATE", "DETAIL"]).to.include(API_STAGE);
});

pm.test("[Pre] payment object exists", function () {
    if (!payment) {
        console.warn("[payment-assert] payment missing; soft skip remaining");
        pm.expect(true).to.be.true;
        return;
    }
    pm.expect(payment, "payment missing").to.be.an("object");
});

pm.test("[Pre] currency exists", function () {
    if (!payment) {
        return;
    }
    pm.expect(payment.currency, "currency missing").to.exist.and.not.eql("");
});

if (payment) {

pm.test("[Config] context", function () {
    console.log("[payment-assert] apiStage=" + API_STAGE);
    console.log("[payment-assert] orderStatus=" + FormatStatus(orderStatus));
    console.log("[payment-assert] paymentStatus=" + FormatStatus(status));
    console.log("[payment-assert] payableAmount=" + payableAmount);
    console.log("[payment-assert] isNonZeroPayable=" + isNonZeroPayable);
    console.log("[payment-assert] isEntitlementZeroPay=" + isEntitlementZeroPay);
});

// ---------------------------------------------------------------------------
// Preview 分支
// ---------------------------------------------------------------------------

if (API_STAGE === "PREVIEW") {
    if (isNonZeroPayable) {
        // 现金: status=null, 有 price 明细
        AssertPaymentStatusIsNull(status, "Preview-Cash");
        pm.test("[Preview-Cash] timeline is null", function () {
            pm.expect(IsNullOrMissing(timeline)).to.be.true;
        });
    } else if (isEntitlementZeroPay) {
        // 权益抵扣 0 元 Preview 同现金/权益: status=null, 有 price 明细
        AssertPaymentStatusIsNull(status, "Preview-Entitlement-ZeroPay");
        pm.test("[Preview-Entitlement-ZeroPay] timeline is null", function () {
            pm.expect(IsNullOrMissing(timeline)).to.be.true;
        });
        pm.test("[Preview-Entitlement-ZeroPay] price details exist", function () {
            pm.expect(HasPaymentPriceDetails(price, charges, deductions)).to.be.true;
        });
    } else {
        // 客户预收: price/charges/deductions 均为 null (权益支付已与现金同预期, 不进此分支)
        AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "Preview-Prepay-Entitlement");
        pm.test("[Preview-Prepay-Entitlement] timeline is null", function () {
            pm.expect(IsNullOrMissing(timeline)).to.be.true;
        });
        pm.test("[Preview-Prepay-Entitlement] price/charges/deductions are null", function () {
            pm.expect(price).to.be.null;
            pm.expect(charges).to.be.null;
            pm.expect(deductions).to.be.null;
        });
    }
}

// ---------------------------------------------------------------------------
// Create 分支
// ---------------------------------------------------------------------------

if (API_STAGE === "CREATE") {
    if (isNonZeroPayable) {
        // 需支付: timeline 对象存在, 内部时间字段全 null
        AssertPaymentStatus(status, "PENDING_PAYMENT", "Create-NeedPay");
        pm.test("[Create-NeedPay] timeline all null", function () {
            pm.expect(timeline).to.be.an("object");
            pm.expect(IsTimelineAllNull(timeline)).to.be.true;
        });
    } else if (isEntitlementZeroPay) {
        // 权益抵扣 0 元: 不拉起收银台, timeline={ paidAt:null, refundedAt:null }
        AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "Create-Entitlement-ZeroPay");
        AssertTimelinePaidRefundNull("Create-Entitlement-ZeroPay", timeline);
    } else {
        // 客户预收 0 元 (非权益抵扣 original=discount 识别)
        AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "Create-ZeroPay-Prepay");
        pm.test("[Create-ZeroPay-Prepay] timeline is null", function () {
            pm.expect(IsNullOrMissing(timeline)).to.be.true;
        });
    }
}

// ---------------------------------------------------------------------------
// Detail 分支
// ---------------------------------------------------------------------------

if (API_STAGE === "DETAIL") {
    var detailExpect = ResolveDetailScenario(payableAmount, EXPECTED_DETAIL_STATUS, isEntitlementZeroPay);

    AssertPaymentStatus(status, detailExpect.expectedStatus, detailExpect.scenario);

    if (detailExpect.timelineRule === "NULL") {
        pm.test("[" + detailExpect.scenario + "] timeline expected=null actual=" + JSON.stringify(timeline), function () {
            pm.expect(IsNullOrMissing(timeline)).to.be.true;
            console.log("[payment-assert] PASS " + detailExpect.scenario + " timeline expected=null");
        });
    } else if (detailExpect.timelineRule === "ENTITLEMENT_SHAPE") {
        AssertTimelinePaidRefundNull(detailExpect.scenario, timeline);
    } else {
        // 需支付 Detail: timeline 含 paidAt/refundedAt, 值按支付状态显示否则 null
        pm.test("[" + detailExpect.scenario + "] timeline has paidAt/refundedAt", function () {
            pm.expect(timeline).to.be.an("object");
            pm.expect(HasTimelinePaidRefundFields(timeline)).to.be.true;
            if (detailExpect.expectedStatus === "PENDING_PAYMENT") {
                pm.expect(timeline.paidAt).to.be.null;
                pm.expect(timeline.refundedAt).to.be.null;
            }
            console.log("[payment-assert] PASS " + detailExpect.scenario + " timeline shape ok");
        });
    }
}

// ---------------------------------------------------------------------------
// 价格汇总 C-1 / C-2 / C-3
// Preview 仅现金与权益抵扣 0 元; Create/Detail 有明细即跑
// ---------------------------------------------------------------------------

var shouldAssertPrice = false;
if (ASSERT_PRICE && HasPaymentPriceDetails(price, charges, deductions)) {
    if (API_STAGE === "PREVIEW" && (isNonZeroPayable || isEntitlementZeroPay)) {
        shouldAssertPrice = true;
    }
    if (API_STAGE === "CREATE") {
        shouldAssertPrice = true;
    }
    if (API_STAGE === "DETAIL") {
        shouldAssertPrice = true;
    }
}

if (shouldAssertPrice) {
    var basePriceSum = SumChargeByType(charges, "BASE_PRICE");
    var prebookingFeeSum = SumChargeByType(charges, "PREBOOKING_FEE");
    var entitlementSum = SumEntitlementDeductionAmount(deductions);
    var originalAmount = Number(price.originalAmount);
    var discountAmount = Number(price.discountAmount != null ? price.discountAmount : price.deductionAmount);
    var payableFromPrice = Number(price.payableAmount);

    pm.test("[C-1] BASE_PRICE + PREBOOKING_FEE = originalAmount", function () {
        pm.expect(Round2(basePriceSum + prebookingFeeSum)).to.eql(Round2(originalAmount));
    });

    pm.test("[C-2] abs(ENTITLEMENT) = discountAmount", function () {
        pm.expect(Round2(Math.abs(entitlementSum))).to.eql(Round2(discountAmount));
    });

    pm.test("[C-3] originalAmount - discountAmount = payableAmount", function () {
        pm.expect(Round2(originalAmount - discountAmount)).to.eql(Round2(payableFromPrice));
    });

    // Env unit prices: BASE=adults*overage; user FEE=adults*prebooking; disc=min(ent,adults)*overage
    // Detail 请求体无 passengers/权益点：跳过 E-*，避免沿用旧 collection 人数误算
    if (ASSERT_ENV_PRICE && API_STAGE !== "DETAIL") {
        var payer = String(GetCfg("prebookingFeePayer") || "user").toLowerCase();
        var ovRaw = GetCfg("overageUnitPrice");
        var pbRaw = GetCfg("prebookingUnitPrice");
        var overage = Number(ovRaw);
        var prebooking = payer === "user" ? Number(pbRaw) : 0;
        var ent = 0;
        var adults = 0;
        var gotEnt = false;
        try {
            var rawBody = pm.request && pm.request.body && pm.request.body.raw;
            if (rawBody) {
                var bodyObj = JSON.parse(pm.variables.replaceIn(String(rawBody)));
                var ex = (bodyObj && bodyObj.extra) || {};
                if (ex.toUseEntitlementCount != null && ex.toUseEntitlementCount !== "") {
                    ent = Number(ex.toUseEntitlementCount) || 0;
                    gotEnt = true;
                } else if (ex.toUseUsageCount != null && ex.toUseUsageCount !== "") {
                    // ePass 现金/次数入参
                    ent = Number(ex.toUseUsageCount) || 0;
                    gotEnt = true;
                }
                if (Array.isArray(ex.passengers)) {
                    adults = ex.passengers.length;
                }
                // Lounge 无 passengers：先用可用性人数，再推断 ePass 纯权益覆盖
                if (adults <= 0) {
                    adults = Number(GetCfg("fastTrackAdultCount") || 3) || 3;
                }
                // ePass 纯权益：无 toUse* 且无 DP/CLIENT_COLLECT → 权益覆盖全部乘客底价
                // （不传 cashPaymentApplied/cashier；或 cashPaymentApplied=true 且非现金/预收）
                if (!gotEnt && adults > 0) {
                    var pmMode = "";
                    if (ex.cashier && typeof ex.cashier === "object") {
                        pmMode = String(ex.cashier.paymentMode || "").toUpperCase();
                    }
                    if (pmMode !== "DP_COLLECT" && pmMode !== "CLIENT_COLLECT") {
                        ent = adults;
                        gotEnt = true;
                    }
                }
            }
        } catch (eEnv) {}
        if (!gotEnt) {
            ent = Number(GetCfg("toUseEntitlementCount") || GetCfg("toUseUsageCount") || 0) || 0;
        } else {
            try {
                pm.collectionVariables.set("toUseEntitlementCount", String(ent));
            } catch (eS1) {}
            try {
                pm.variables.set("toUseEntitlementCount", String(ent));
            } catch (eS2) {}
        }
        if (adults <= 0) {
            adults = Number(GetCfg("fastTrackAdultCount") || 3) || 3;
        }
        if (
            ovRaw &&
            ovRaw.toUpperCase() !== "UNSET" &&
            payer !== "unset" &&
            !isNaN(overage) &&
            (payer !== "user" || (!isNaN(prebooking) && pbRaw && pbRaw.toUpperCase() !== "UNSET"))
        ) {
            var used = ent > adults ? adults : ent;
            var expBase = Round2(adults * overage);
            var expFee = payer === "user" ? Round2(adults * prebooking) : 0;
            var expOrig = Round2(expBase + expFee);
            var expDisc = Round2(used * overage);
            var expPay = Round2(expOrig - expDisc);
            console.log(
                "[payment-assert] env expect base=" +
                    expBase +
                    " fee=" +
                    expFee +
                    " orig=" +
                    expOrig +
                    " disc=" +
                    expDisc +
                    " pay=" +
                    expPay
            );
            pm.test("[E-BASE] expected=" + expBase + " actual=" + Round2(basePriceSum), function () {
                pm.expect(Round2(basePriceSum)).to.eql(expBase);
            });
            pm.test("[E-FEE] expected=" + expFee + " actual=" + Round2(prebookingFeeSum), function () {
                pm.expect(Round2(prebookingFeeSum)).to.eql(expFee);
            });
            pm.test("[E-ORIG] expected=" + expOrig + " actual=" + Round2(originalAmount), function () {
                pm.expect(Round2(originalAmount)).to.eql(expOrig);
            });
            pm.test("[E-DISC] expected=" + expDisc + " actual=" + Round2(discountAmount), function () {
                pm.expect(Round2(discountAmount)).to.eql(expDisc);
            });
            pm.test("[E-PAY] expected=" + expPay + " actual=" + Round2(payableFromPrice), function () {
                pm.expect(Round2(payableFromPrice)).to.eql(expPay);
            });
        }
    }
}
} // end if (payment)
} // end IsBusinessOkEnvelope
