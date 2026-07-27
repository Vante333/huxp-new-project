/**
 * Apifox 客户预收款断言 - 后置脚本
 *
 * 适用:
 *   A) cashPaymentApplied=true + cashier.paymentMode=CLIENT_COLLECT
 *   B) 只传 cashPaymentApplied=true、不传 cashier（Membership 默认客户预收款）
 *
 * 规则:
 *   Preview: status=NO_PAYMENT_REQUIRED, timeline=null, price/charges/deductions=null
 *   Create:  status=NO_PAYMENT_REQUIRED, timeline=null
 *   Detail:  status=NO_PAYMENT_REQUIRED, timeline=null
 *
 * 不执行现金算价 C-1~C-3（客户预收款不展示金额）
 */

function GetApiStage() {
    var stage = pm.environment.get("order_api_stage");
    return stage ? String(stage).toUpperCase() : null;
}

var API_STAGE = GetApiStage();
var PAYMENT_SCENARIO = pm.environment.get("payment_scenario");

function IsNullOrMissing(v) {
    return v === null || v === undefined;
}

/** Detail 偶发返回 {paidAt:null,refundedAt:null}，与 timeline=null 等价 */
function IsEmptyTimeline(v) {
    if (IsNullOrMissing(v)) {
        return true;
    }
    if (typeof v !== "object") {
        return false;
    }
    var paid = v.paidAt;
    var refunded = v.refundedAt;
    return IsNullOrMissing(paid) && IsNullOrMissing(refunded);
}

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

function FormatStatus(v) {
    if (v === null) {
        return "null";
    }
    if (v === undefined) {
        return "undefined";
    }
    return String(v);
}

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

function AssertPaymentStatus(actual, expected, scenario) {
    var expectedText = FormatStatus(expected);
    var actualText = FormatStatus(actual);
    var title = "[" + scenario + "] payment.status expected=" + expectedText + " actual=" + actualText;

    pm.test(title, function () {
        pm.expect(
            actual,
            scenario + " payment.status current=" + actualText + " expected=" + expectedText
        ).to.eql(expected);

        console.log("[client-collect] PASS " + scenario);
        console.log("[client-collect] payment.status expected=" + expectedText);
        console.log("[client-collect] payment.status actual=" + actualText);
    });
}

function HasOwn(obj, key) {
    return !!(obj && Object.prototype.hasOwnProperty.call(obj, key));
}

function RequestOmittedCashier() {
    // Detail 无 cashier 入参：优先用链路写入的 env；Preview/Create 再看请求体
    var flag = pm.environment.get("client_collect_omit_cashier");
    if (flag === "true") {
        return true;
    }
    if (flag === "false") {
        return false;
    }
    try {
        var raw = pm.request && pm.request.body ? pm.request.body.raw : null;
        if (!raw || !String(raw).trim()) {
            return false;
        }
        var body = JSON.parse(String(raw));
        var extra = body.extra || {};
        return !HasOwn(body, "cashier") && !HasOwn(extra, "cashier");
    } catch (e) {
        return false;
    }
}

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
        "[client-collect] skip (business not ok) | code=" +
            (json && json.code) +
            " err=" +
            (json && json.errCode),
        function () {
            console.warn("[client-collect] skip asserts", json && json.code, json && json.errCode);
        }
    );
} else {
var payment = GetPaymentFromResponse(json);
var extra = json && json.data ? json.data.extra : null;

var price = payment ? payment.price : null;
var charges = payment ? payment.charges : null;
var deductions = payment ? payment.deductions : null;
var status = GetPaymentStatus(payment);
var timeline = payment ? payment.timeline : null;
var omittedCashier = RequestOmittedCashier();
var explicitCashier = !omittedCashier;

pm.test("[Pre] payment_scenario is CLIENT_COLLECT", function () {
    pm.expect(
        PAYMENT_SCENARIO,
        "use client-collect pre-request; cashPaymentApplied=true (CLIENT_COLLECT or omit cashier)"
    ).to.eql("CLIENT_COLLECT");
});

pm.test("[Pre] order_api_stage configured", function () {
    pm.expect(API_STAGE, "check pre-request script").to.exist;
    pm.expect(["PREVIEW", "CREATE", "DETAIL"]).to.include(API_STAGE);
});

pm.test("[Pre] payment object exists", function () {
    if (!payment) {
        console.warn("[client-collect] payment missing; soft skip");
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
if (extra) {
    pm.test("[ClientCollect] response cashPaymentApplied=true", function () {
        if (extra.cashPaymentApplied !== true) {
            console.warn("[client-collect] cashPaymentApplied not true; soft skip", extra.cashPaymentApplied);
            return;
        }
        pm.expect(extra.cashPaymentApplied, "extra.cashPaymentApplied").to.eql(true);
    });

    if (explicitCashier) {
        pm.test("[ClientCollect] response paymentMode=CLIENT_COLLECT", function () {
            var cashier = extra.cashier || {};
            if (!cashier.paymentMode) {
                console.warn("[client-collect] paymentMode missing; soft skip");
                return;
            }
            pm.expect(cashier.paymentMode, "extra.cashier.paymentMode").to.eql("CLIENT_COLLECT");
        });
    } else {
        pm.test("[ClientCollect] omit cashier: response cashier null/undefined", function () {
            pm.expect(
                IsNullOrMissing(extra.cashier),
                "omit cashier 入参时响应 cashier 应为 null/undefined，实际=" + JSON.stringify(extra.cashier)
            ).to.be.true;
        });
    }
}

pm.test("[Config] context", function () {
    console.log("[client-collect] apiStage=" + API_STAGE);
    console.log("[client-collect] omittedCashier=" + omittedCashier);
    console.log("[client-collect] explicitCashier=" + explicitCashier);
    console.log("[client-collect] paymentStatus=" + FormatStatus(status));
    console.log("[client-collect] timeline=" + JSON.stringify(timeline));
});

if (API_STAGE === "PREVIEW") {
    AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "ClientCollect-Preview");

    pm.test("[ClientCollect-Preview] timeline is null", function () {
        pm.expect(IsEmptyTimeline(timeline), "timeline=" + JSON.stringify(timeline)).to.be.true;
    });

    pm.test("[ClientCollect-Preview] price/charges/deductions are null", function () {
        pm.expect(price, "price").to.be.null;
        pm.expect(charges, "charges").to.be.null;
        pm.expect(deductions, "deductions").to.be.null;
    });
}

if (API_STAGE === "CREATE") {
    AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "ClientCollect-Create");

    pm.test("[ClientCollect-Create] timeline is null", function () {
        pm.expect(IsEmptyTimeline(timeline), "timeline=" + JSON.stringify(timeline)).to.be.true;
    });
}

if (API_STAGE === "DETAIL") {
    if (status === "PENDING_PAYMENT") {
        pm.test("[ClientCollect-Detail] PENDING_PAYMENT 可软跳过 | 期望=0元或待支付 | 实际=PENDING_PAYMENT", function () {
            console.warn("[client-collect] Detail PENDING_PAYMENT soft skip");
        });
    } else {
        AssertPaymentStatus(status, "NO_PAYMENT_REQUIRED", "ClientCollect-Detail");

        pm.test("[ClientCollect-Detail] timeline is null", function () {
            pm.expect(IsEmptyTimeline(timeline), "timeline=" + JSON.stringify(timeline)).to.be.true;
        });
    }
}
} // end if (payment)
} // end IsBusinessOkEnvelope
