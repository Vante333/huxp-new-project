/**
 * PAPI-3135 支付链接 — 语种 ForEach 完整后置断言
 *
 * 粘贴位置：
 *   自动化 → ForEach 内的 POST /v2/orders/payments
 *   →「后置操作」→「自定义脚本」
 *
 * Body 里 language 请用循环变量，例如：
 *   "language": "{{item}}"
 * 若 ForEach 变量名不是 item，改成界面上的名字（如 forEachItem）
 */
function pickLanguage() {
  var keys = ["item", "forEachItem", "$item", "language", "pay_language_sent"];
  var i, v;

  for (i = 0; i < keys.length; i++) {
    try {
      v = pm.variables.get(keys[i]);
      if (v !== null && v !== undefined && String(v) !== "") return String(v);
    } catch (e1) {}
    try {
      v = pm.environment.get(keys[i]);
      if (v !== null && v !== undefined && String(v) !== "") return String(v);
    } catch (e2) {}
    try {
      if (typeof pm.iterationData !== "undefined" && pm.iterationData.get) {
        v = pm.iterationData.get(keys[i]);
        if (v !== null && v !== undefined && String(v) !== "") return String(v);
      }
    } catch (e3) {}
  }

  // 从本次实际请求 Body 反查
  try {
    var raw = pm.request.body && pm.request.body.raw ? pm.request.body.raw : "";
    if (raw) {
      var bodyObj = JSON.parse(raw);
      if (bodyObj && bodyObj.language) return String(bodyObj.language);
    }
  } catch (e4) {}

  return "UNKNOWN";
}

function bizOk(env) {
  if (!env || typeof env !== "object") return false;
  var c = env.code;
  return c === 0 || c === "0" || c === 1 || c === "1";
}

function paymentUrl(env) {
  var d = env && env.data !== undefined ? env.data : env;
  if (!d) return "";
  if (d.paymentAction) {
    return d.paymentAction.url || d.paymentAction.redirectUrl || "";
  }
  if (d.payment && d.payment.paymentAction) {
    return d.payment.paymentAction.url || d.payment.paymentAction.redirectUrl || "";
  }
  return d.url || "";
}

function validUntil(env) {
  var d = env && env.data !== undefined ? env.data : env;
  if (!d) return null;
  if (d.paymentAction && d.paymentAction.validUntil != null) return d.paymentAction.validUntil;
  if (d.validUntil != null) return d.validUntil;
  return null;
}

var language = pickLanguage();
var json = {};
try {
  json = pm.response.json();
} catch (e) {
  json = {};
}

var errCode = json.errCode || json.errorCode || "";
var url = paymentUrl(json);
var vu = validUntil(json);

pm.test("[语种=" + language + "] HTTP 有响应", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

pm.test("[语种=" + language + "] 业务成功 code=0", function () {
  pm.expect(
    bizOk(json),
    "language=" +
      language +
      " code=" +
      json.code +
      " err=" +
      errCode +
      " msg=" +
      (json.msg || "")
  ).to.eql(true);
});

pm.test("[语种=" + language + "] 返回支付 url", function () {
  pm.expect(url, "没有 paymentAction.url，err=" + errCode + " msg=" + (json.msg || "")).to.be
    .a("string")
    .and.not.eql("");
});

pm.test("[语种=" + language + "] 循环变量已解析(非UNKNOWN/非模板)", function () {
  pm.expect(language, "ForEach 变量未取到，请检查 Body 的 language={{item}}").to.not.eql(
    "UNKNOWN"
  );
  pm.expect(language.indexOf("{{"), "language 仍是未解析模板").to.eql(-1);
});

// 可选：有 validUntil 再记一条（没有也不判失败）
if (vu != null) {
  pm.test("[语种=" + language + "] 记录 validUntil", function () {
    console.log("[pay-lang] validUntil=", vu);
    pm.expect(true).to.be.true;
  });
}

// 汇总成功/失败语种，跑完看环境变量
try {
  if (bizOk(json) && url) {
    var ok = pm.environment.get("pay_lang_ok_list") || "";
    pm.environment.set("pay_lang_ok_list", ok ? ok + "," + language : language);
    pm.environment.set("pay_last_url", url);
    pm.environment.set("pay_last_lang", language);
    if (vu != null) pm.environment.set("pay_last_validUntil", String(vu));
  } else {
    var bad = pm.environment.get("pay_lang_fail_list") || "";
    var one = language + "(" + (errCode || json.code || "?") + ")";
    pm.environment.set("pay_lang_fail_list", bad ? bad + "," + one : one);
  }
} catch (eSave) {}

console.log(
  "[pay-lang] language=",
  language,
  "code=",
  json.code,
  "err=",
  errCode,
  "url=",
  url,
  "body=",
  pm.request.body ? pm.request.body.raw : ""
);
