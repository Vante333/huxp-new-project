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

var forceStage = pm.environment.get("order_api_stage_force") === "true";
var manualStage = pm.environment.get("order_api_stage");
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
    pm.environment.set("order_api_stage", finalStage);
    console.log("[payment-assert] order_api_stage = " + finalStage + " | URL = " + requestUrl);
} else {
    console.warn("[payment-assert] order_api_stage not detected");
}
