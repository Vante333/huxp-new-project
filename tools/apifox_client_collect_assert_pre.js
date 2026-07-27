/**
 * Apifox 客户预收款断言 - 前置脚本
 *
 * 识别条件（请求体，兼容 extra 嵌套）:
 *   A) cashPaymentApplied === true 且 cashier.paymentMode === "CLIENT_COLLECT"
 *   B) Membership 默认：cashPaymentApplied === true 且不传 cashier（默认客户预收款）
 *
 * 写入环境变量:
 *   order_api_stage       PREVIEW | CREATE | DETAIL（按 URL）
 *   payment_scenario      CLIENT_COLLECT
 */

function DetectOrderApiStageFromUrl(url) {
    var path = String(url || "").toLowerCase();

    if (/\/prebooking\/preview\b/.test(path)) {
        return "PREVIEW";
    }
    if (
        /\/orders\/memberships\/details\b/.test(path) ||
        /\/orders\/epasses\/details\b/.test(path) ||
        /\/orders\/esims\/details\b/.test(path)
    ) {
        return "DETAIL";
    }
    if (
        /\/memberships\/prebooking\b/.test(path) ||
        /\/epasses\/prebooking\b/.test(path)
    ) {
        return "CREATE";
    }
    return null;
}

function ParseRequestBody() {
    if (!pm.request.body || !pm.request.body.raw) {
        return {};
    }
    try {
        return JSON.parse(pm.request.body.raw);
    } catch (e) {
        return {};
    }
}

function HasOwn(obj, key) {
    return !!(obj && Object.prototype.hasOwnProperty.call(obj, key));
}

function IsClientCollectRequest(body) {
    var extra = body.extra || {};
    var cashApplied = body.cashPaymentApplied !== undefined
        ? body.cashPaymentApplied
        : extra.cashPaymentApplied;
    if (cashApplied !== true) {
        return false;
    }
    var hasCashier = HasOwn(body, "cashier") || HasOwn(extra, "cashier");
    if (!hasCashier) {
        // 只传 cashPaymentApplied=true → Membership 默认客户预收款
        return true;
    }
    var cashier = body.cashier !== undefined ? body.cashier : extra.cashier;
    if (cashier === null || cashier === undefined) {
        return true;
    }
    var paymentMode = cashier.paymentMode;
    return paymentMode === "CLIENT_COLLECT";
}

var requestUrl = pm.request.url ? pm.request.url.toString() : "";
var stage = DetectOrderApiStageFromUrl(requestUrl);
var body = ParseRequestBody();
var isClientCollect = IsClientCollectRequest(body);

if (stage) {
    pm.environment.set("order_api_stage", stage);
    console.log("[client-collect] order_api_stage = " + stage);
} else {
    console.warn("[client-collect] order_api_stage not detected");
}

if (isClientCollect) {
    pm.environment.set("payment_scenario", "CLIENT_COLLECT");
    var extra = body.extra || {};
    var omitCashier = !HasOwn(body, "cashier") && !HasOwn(extra, "cashier");
    pm.environment.set("client_collect_omit_cashier", omitCashier ? "true" : "false");
    console.log("[client-collect] payment_scenario = CLIENT_COLLECT");
    console.log("[client-collect] omit_cashier=" + omitCashier);
} else {
    pm.environment.unset("payment_scenario");
    pm.environment.unset("client_collect_omit_cashier");
    console.warn("[client-collect] request is NOT client collect, check body fields");
}
