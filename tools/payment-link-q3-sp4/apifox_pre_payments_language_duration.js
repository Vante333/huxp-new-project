/**
 * PAPI-3135 支付链接 language + durationInSeconds
 * Apifox 前置脚本（贴到「测试用例 / 接口」前置操作）
 *
 * 环境变量（Environment）：
 *   baseUrl              如 https://developer-sandbox.dragonpass.com/api
 *   accessToken          已获取的 Bearer Token
 *   programId            X-Program-ID
 *   pay_orderId          可支付订单号（待支付）
 *   pay_returnUrl        合法回调 URL
 *   pay_paymentMethod    默认 H5_CASHIER（Jira 样例有 MS_CASHIER，按环境改）
 *   pay_duration_max     上限秒数：用例写 1800；Jira 图注有 12000。默认 1800
 *   pay_duration_default 默认秒数：用例/ Jira 均为 600
 *
 * 用例级变量（在单个用例里用 pm.variables.set，或用例参数）：
 *   case_id              如 LANG_DEFAULT / DUR_60 / DUR_OVER
 *   req_language         不设=不传；设了则写入 Body
 *   req_duration         不设=不传；数字则写入 Body
 */

function Env(key, defVal) {
  var v = "";
  try { v = pm.environment.get(key); } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}

function Var(key, defVal) {
  var v = "";
  try { v = pm.variables.get(key); } catch (e) {}
  if (v === null || v === undefined || v === "") {
    try { v = pm.collectionVariables.get(key); } catch (e2) {}
  }
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}

var orderId = Env("pay_orderId", "");
var returnUrl = Env("pay_returnUrl", "https://example.com/payment/return");
var paymentMethod = Env("pay_paymentMethod", "H5_CASHIER");
var caseId = Var("case_id", "MANUAL");
var reqLanguage = Var("req_language", "");
var reqDuration = Var("req_duration", "");

if (!orderId || orderId.indexOf("{{") >= 0) {
  console.warn("[pay-link] 请先在环境设置 pay_orderId=可支付订单号");
}

var body = {
  orderId: orderId,
  returnUrl: returnUrl,
  paymentMethod: paymentMethod
};

if (reqLanguage !== "") {
  body.language = reqLanguage;
}
if (reqDuration !== "") {
  var n = parseInt(reqDuration, 10);
  if (!isNaN(n)) body.durationInSeconds = n;
}

pm.request.body = {
  mode: "raw",
  raw: JSON.stringify(body, null, 2),
  options: { raw: { language: "json" } }
};

try { pm.variables.set("pay_last_case_id", caseId); } catch (e) {}
try { pm.variables.set("pay_sent_at_ms", String(Date.now())); } catch (e) {}
try {
  pm.variables.set("pay_expect_duration", reqDuration !== "" ? reqDuration : Env("pay_duration_default", "600"));
} catch (e) {}
try {
  pm.variables.set("pay_language_sent", reqLanguage !== "" ? reqLanguage : "(omit→default en-US)");
} catch (e) {}

console.log("[pay-link] case=" + caseId + " body=" + JSON.stringify(body));
