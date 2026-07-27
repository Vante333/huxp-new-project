/**
 * Apifox 后置断言：usedEntitlementDetails 与 usedEntitlementBreakdown 权益数量一致
 *
 * 规则：
 *   1. usedEntitlementDetails 存在，且含 4 个权益 key
 *   2. usedEntitlementBreakdown 为数组（允许 []：未扣任何权益）
 *   3. breakdown 非空时：每项 entitlements 含相同 4 个 key
 *   4. 对每个 key：sum(breakdown[i].entitlements[key]) === usedEntitlementDetails[key]
 *      - breakdown=[] 时 sum=0，即 details 各 key 均为 0
 *      - 单条 breakdown 时等价于与 details 逐 key 相等
 *
 * 响应路径：data.extra（兼容 data / 根级）
 */

var ENTITLEMENT_KEYS = [
    "cardholderExclusiveEntitlements",
    "guestsExclusiveEntitlements",
    "sharedEntitlements",
    "purchasedEntitlements"
];

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
    if (json.data) {
        return json.data;
    }
    return json;
}

function ToNumberOrNaN(v) {
    if (v === null || v === undefined) {
        return NaN;
    }
    var n = Number(v);
    return n;
}

function FormatValue(v) {
    if (v === null) {
        return "null";
    }
    if (v === undefined) {
        return "undefined";
    }
    return String(v);
}

var json = pm.response.json();
var extra = GetExtraFromResponse(json);
var details = extra ? extra.usedEntitlementDetails : null;
var breakdown = extra ? extra.usedEntitlementBreakdown : null;

pm.test("[Entitlement] usedEntitlementDetails exists", function () {
    pm.expect(details, "usedEntitlementDetails missing").to.be.an("object");
});

pm.test("[Entitlement] usedEntitlementBreakdown is array (empty [] allowed)", function () {
    pm.expect(breakdown, "usedEntitlementBreakdown missing").to.be.an("array");
});

if (!details || !Array.isArray(breakdown)) {
    console.log("[entitlement] SKIP compare: details or breakdown missing");
} else {
    pm.test("[Entitlement] usedEntitlementDetails has 4 keys", function () {
        for (var i = 0; i < ENTITLEMENT_KEYS.length; i++) {
            var key = ENTITLEMENT_KEYS[i];
            pm.expect(details, "details missing key=" + key).to.have.property(key);
            pm.expect(isNaN(ToNumberOrNaN(details[key])), "details." + key + " not number, actual=" + FormatValue(details[key])).to.be.false;
        }
    });

    if (breakdown.length === 0) {
        // 未扣权益：breakdown=[]，details 各 key 应为 0
        pm.test("[Entitlement] breakdown=[] (no entitlement used), details all keys = 0", function () {
            for (var i = 0; i < ENTITLEMENT_KEYS.length; i++) {
                var key = ENTITLEMENT_KEYS[i];
                pm.expect(
                    ToNumberOrNaN(details[key]),
                    "breakdown=[] but details." + key + "=" + FormatValue(details[key]) + " expected=0"
                ).to.eql(0);
            }
        });
        console.log("[entitlement] breakdown=[] OK; details=" + JSON.stringify(details));
    } else {
        pm.test("[Entitlement] each breakdown[].entitlements has same 4 keys", function () {
            for (var bi = 0; bi < breakdown.length; bi++) {
                var item = breakdown[bi];
                pm.expect(item, "breakdown[" + bi + "] missing").to.be.an("object");
                var entitlements = item.entitlements;
                pm.expect(entitlements, "breakdown[" + bi + "].entitlements missing").to.be.an("object");
                for (var ki = 0; ki < ENTITLEMENT_KEYS.length; ki++) {
                    var key = ENTITLEMENT_KEYS[ki];
                    pm.expect(entitlements, "breakdown[" + bi + "].entitlements missing key=" + key).to.have.property(key);
                    pm.expect(
                        isNaN(ToNumberOrNaN(entitlements[key])),
                        "breakdown[" + bi + "].entitlements." + key + " not number, actual=" + FormatValue(entitlements[key])
                    ).to.be.false;
                }
            }
        });

        // 多条 breakdown 时 details = 各条 entitlements 按 key 求和；单条时即逐 key 相等
        for (var ki2 = 0; ki2 < ENTITLEMENT_KEYS.length; ki2++) {
            (function (key) {
                var detailVal = ToNumberOrNaN(details[key]);
                var sumVal = 0;
                var parts = [];
                for (var bi2 = 0; bi2 < breakdown.length; bi2++) {
                    var itemEnt = breakdown[bi2] && breakdown[bi2].entitlements ? breakdown[bi2].entitlements : null;
                    var part = itemEnt ? ToNumberOrNaN(itemEnt[key]) : NaN;
                    parts.push("[" + bi2 + "]=" + FormatValue(itemEnt ? itemEnt[key] : undefined));
                    if (!isNaN(part)) {
                        sumVal += part;
                    }
                }
                var title =
                    "[Entitlement] " +
                    key +
                    " details=" +
                    FormatValue(details[key]) +
                    " sum(breakdown)=" +
                    sumVal +
                    " parts=" +
                    parts.join(",");

                pm.test(title, function () {
                    pm.expect(isNaN(detailVal), "details." + key + " invalid").to.be.false;
                    pm.expect(
                        sumVal,
                        key + " mismatch: details=" + FormatValue(details[key]) + " sum(breakdown)=" + sumVal
                    ).to.eql(detailVal);
                });
            })(ENTITLEMENT_KEYS[ki2]);
        }

        console.log("[entitlement] details=" + JSON.stringify(details));
        console.log("[entitlement] breakdown.length=" + breakdown.length);
    }
}
