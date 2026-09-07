/**
 * PAPI-3135 支付链接 — 语种遍历后置断言
 * 预期：各语种创建支付链接不报错（业务成功 + 有 url）
 * 页面真实语种需打开 url 人工抽查
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

function BizOk(env) {
  if (!env || typeof env !== "object") return false;
  if (!Object.prototype.hasOwnProperty.call(env, "code")) return pm.response.code === 200;
  var c = env.code;
  return c === 0 || c === "0" || c === 1 || c === "1";
}
function GetData(env) {
  return env && env.data !== undefined ? env.data : env;
}
function GetPaymentAction(data) {
  if (!data) return null;
  if (data.paymentAction) return data.paymentAction;
  if (data.payment && data.payment.paymentAction) return data.payment.paymentAction;
  return null;
}

var language = Var("pay_language_sent", Var("language", "UNKNOWN"));
var caseId = Var("pay_last_case_id", "LANG_TRAVERSE_" + language);
var json = {};
try { json = pm.response.json(); } catch (e) { json = {}; }

pm.test("[" + caseId + "] HTTP 可到达", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

pm.test("[" + caseId + "] 语种=" + language + " 业务成功(不可报错)", function () {
  pm.expect(
    BizOk(json),
    "language=" + language + " code=" + json.code + " err=" + (json.errCode || json.errorCode) + " msg=" + json.msg
  ).to.eql(true);
});

var data = GetData(json);
var action = GetPaymentAction(data);

pm.test("[" + caseId + "] 返回支付 url", function () {
  pm.expect(action, "paymentAction missing").to.be.an("object");
  pm.expect(action.url || action.redirectUrl, "url empty").to.be.a("string").and.not.eql("");
});

// 汇总到环境，方便跑完后看失败语种
try {
  var failKey = "pay_lang_fail_list";
  var okKey = "pay_lang_ok_list";
  var fails = Env(failKey, "");
  var oks = Env(okKey, "");
  if (BizOk(json) && action && (action.url || action.redirectUrl)) {
    oks = oks ? oks + "," + language : language;
    pm.environment.set(okKey, oks);
    pm.environment.set("pay_last_url", String(action.url || action.redirectUrl));
    pm.environment.set("pay_last_lang", language);
  } else {
    fails = fails ? fails + "," + language : language;
    pm.environment.set(failKey, fails);
  }
} catch (eSave) {}

console.log("[pay-lang] done language=" + language + " bizOk=" + BizOk(json) + " err=" + (json.errCode || json.errorCode));
