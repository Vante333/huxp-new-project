/**
 * Apifox payment assert - pre-request script
 * Auto set order_api_stage from URL
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
function RtSet(key, value) {
    var v = String(value);
    try { pm.variables.set(key, v); } catch (e0) {}
    try { pm.collectionVariables.set(key, v); } catch (e1) {}
}

var forceStage = RtGet("order_api_stage_force") === "true";
var manualStage = RtGet("order_api_stage");
var requestUrl = pm.request.url ? pm.request.url.toString() : "";
var detectedStage = DetectOrderApiStageFromUrl(requestUrl);
var finalStage = null;

if (forceStage && manualStage) {
    finalStage = String(manualStage).toUpperCase();
} else if (detectedStage) {
    finalStage = detectedStage;
} else if (manualStage) {
    finalStage = String(manualStage).toUpperCase();
}

if (finalStage) {
    RtSet("order_api_stage", finalStage);
    console.log("[payment-assert] order_api_stage = " + finalStage + " | URL = " + requestUrl);
} else {
    console.warn("[payment-assert] order_api_stage not detected");
}
