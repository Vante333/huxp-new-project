/**
 * Apifox 后置断言：响应 extra 与请求入参一致
 *
 * 规则（仅当请求体带了对应字段时校验）：
 *   1. extra.cashPaymentApplied === 请求 cashPaymentApplied
 *   2. extra.cashier 与请求 cashier 一致
 *      - 请求 cashier 为 null → 响应须为 null/undefined
 *      - 请求为对象且含 paymentMode → 响应 cashier.paymentMode 相同
 *      - 其它对象 → JSON 深等
 *
 * Detail 等无 cashPaymentApplied/cashier 入参的请求：自动跳过。
 */

function GetExtraFromResponse(json) {
    if (!json) {
        return null;
    }
    if (json.data && json.data.extra) {
        return json.data.extra;
    }
    if (json.extra) {
        return json.extra;
    }
    return null;
}

function ParseRequestBody() {
    try {
        var raw = pm.request && pm.request.body ? pm.request.body.raw : null;
        if (raw === undefined || raw === null || String(raw).trim() === "") {
            return null;
        }
        return JSON.parse(String(raw));
    } catch (e) {
        console.warn("[extra-echo] request body JSON parse failed: " + e);
        return null;
    }
}

function HasOwn(obj, key) {
    return !!(obj && Object.prototype.hasOwnProperty.call(obj, key));
}

function FormatValue(v) {
    if (v === null) {
        return "null";
    }
    if (v === undefined) {
        return "undefined";
    }
    try {
        return JSON.stringify(v);
    } catch (e) {
        return String(v);
    }
}

function ResolveRequestCashFields(body) {
    if (!body || typeof body !== "object") {
        return { hasApplied: false, hasCashier: false };
    }
    var extra = body.extra && typeof body.extra === "object" ? body.extra : null;
    var hasApplied = HasOwn(body, "cashPaymentApplied") || (extra ? HasOwn(extra, "cashPaymentApplied") : false);
    var hasCashier = HasOwn(body, "cashier") || (extra ? HasOwn(extra, "cashier") : false);
    var applied = HasOwn(body, "cashPaymentApplied")
        ? body.cashPaymentApplied
        : extra
          ? extra.cashPaymentApplied
          : undefined;
    var cashier = HasOwn(body, "cashier") ? body.cashier : extra ? extra.cashier : undefined;
    return {
        hasApplied: hasApplied,
        hasCashier: hasCashier,
        cashPaymentApplied: applied,
        cashier: cashier
    };
}

function AssertCashierMatch(reqCashier, respCashier) {
    var title =
        "extra.cashier 与入参一致 | 期望=" +
        FormatValue(reqCashier) +
        " | 实际=" +
        FormatValue(respCashier);
    pm.test(title, function () {
        if (reqCashier === null) {
            pm.expect(
                respCashier === null || respCashier === undefined,
                "入参 cashier=null，响应应为 null/undefined，实际=" + FormatValue(respCashier)
            ).to.be.true;
            return;
        }
        if (reqCashier && typeof reqCashier === "object" && HasOwn(reqCashier, "paymentMode")) {
            pm.expect(respCashier, "响应 extra.cashier 缺失").to.be.an("object");
            pm.expect(
                respCashier.paymentMode,
                "cashier.paymentMode | 期望=" +
                    FormatValue(reqCashier.paymentMode) +
                    " | 实际=" +
                    FormatValue(respCashier ? respCashier.paymentMode : undefined)
            ).to.eql(reqCashier.paymentMode);
            return;
        }
        pm.expect(respCashier, "extra.cashier").to.eql(reqCashier);
    });
}

var reqBody = ParseRequestBody();
var reqFields = ResolveRequestCashFields(reqBody);
var json = pm.response.json();
var extra = GetExtraFromResponse(json);

if (!reqFields.hasApplied && !reqFields.hasCashier) {
    console.log("[extra-echo] skip: request has no cashPaymentApplied/cashier");
} else if (!extra || typeof extra !== "object") {
    pm.test("extra 存在（校验 cashPaymentApplied/cashier 入参回显）| 期望=object | 实际=missing", function () {
        pm.expect(extra, "data.extra missing").to.be.an("object");
    });
} else {
    if (reqFields.hasApplied) {
        var titleApplied =
            "extra.cashPaymentApplied 与入参一致 | 期望=" +
            FormatValue(reqFields.cashPaymentApplied) +
            " | 实际=" +
            FormatValue(extra.cashPaymentApplied);
        pm.test(titleApplied, function () {
            pm.expect(
                extra.cashPaymentApplied,
                "cashPaymentApplied | 期望=" +
                    FormatValue(reqFields.cashPaymentApplied) +
                    " | 实际=" +
                    FormatValue(extra.cashPaymentApplied)
            ).to.eql(reqFields.cashPaymentApplied);
        });
    }
    if (reqFields.hasCashier) {
        AssertCashierMatch(reqFields.cashier, extra.cashier);
    }
}
