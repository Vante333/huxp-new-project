/**
 * PAPI-3135 支付链接 language + durationInSeconds
 * Apifox 后置断言脚本（贴到「后置操作 / 测试脚本」）
 *
 * 成功包络：code===0（或贵司实际成功码），data.paymentAction.url / validUntil
 * 失败：校验 errCode（超上限等）
 *
 * 依赖前置写入的变量：
 *   pay_last_case_id / pay_sent_at_ms / pay_expect_duration / pay_language_sent
 * 环境：
 *   pay_duration_max（默认 1800，可改 12000）
 *   pay_duration_default（默认 600）
 *   pay_assert_validUntil（true/false，默认 true）
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

var caseId = Var("pay_last_case_id", "UNKNOWN");
var durationMax = parseInt(Env("pay_duration_max", "1800"), 10) || 1800;
var durationDefault = parseInt(Env("pay_duration_default", "600"), 10) || 600;
var expectDuration = parseInt(Var("pay_expect_duration", String(durationDefault)), 10) || durationDefault;
var assertValidUntil = Env("pay_assert_validUntil", "true") !== "false";
var sentAt = parseInt(Var("pay_sent_at_ms", String(Date.now())), 10) || Date.now();
var skewSec = parseInt(Env("pay_validUntil_skew_sec", "15"), 10) || 15;

var json = {};
try { json = pm.response.json(); } catch (e) { json = {}; }

function BizOk(env) {
  if (!env || typeof env !== "object") return false;
  if (!Object.prototype.hasOwnProperty.call(env, "code")) return pm.response.code === 200;
  var c = env.code;
  return c === 0 || c === "0" || c === 1 || c === "1";
}

function GetData(env) {
  if (!env) return null;
  return env.data !== undefined ? env.data : env;
}

function GetPaymentAction(data) {
  if (!data) return null;
  if (data.paymentAction) return data.paymentAction;
  if (data.payment && data.payment.paymentAction) return data.payment.paymentAction;
  return null;
}

pm.test("[" + caseId + "] HTTP 可到达(非网络失败)", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

// ---------- 按用例分支 ----------
var isOverLimit = caseId.indexOf("DUR_OVER") >= 0 || caseId.indexOf("超上限") >= 0;
var isSuccessCase = !isOverLimit && caseId.indexOf("FAIL") < 0;

if (isOverLimit) {
  pm.test("[" + caseId + "] 超上限应业务失败", function () {
    pm.expect(BizOk(json), "超上限不应成功 code=" + json.code + " err=" + json.errCode).to.eql(false);
  });
  pm.test("[" + caseId + "] 记录失败码(便于回填)", function () {
    console.log("[pay-link] OVER_LIMIT errCode=", json.errCode, "msg=", json.msg);
    pm.expect(true).to.be.true;
  });
} else if (isSuccessCase) {
  pm.test("[" + caseId + "] 业务成功 code", function () {
    pm.expect(BizOk(json), "code=" + json.code + " err=" + json.errCode + " msg=" + json.msg).to.eql(true);
  });

  var data = GetData(json);
  var action = GetPaymentAction(data);

  pm.test("[" + caseId + "] 返回支付跳转 url", function () {
    pm.expect(action, "paymentAction missing").to.be.an("object");
    pm.expect(action.url || action.redirectUrl, "url empty").to.be.a("string").and.not.eql("");
  });

  if (assertValidUntil) {
    pm.test("[" + caseId + "] validUntil 接近 发送时刻+期望秒数(±" + skewSec + "s)", function () {
      pm.expect(action, "paymentAction").to.be.an("object");
      var vu = action.validUntil != null ? action.validUntil : action.vaildUntil;
      pm.expect(vu, "validUntil missing").to.exist;
      var vuMs = Number(vu);
      // 兼容秒/毫秒时间戳
      if (vuMs < 1e12) vuMs = vuMs * 1000;
      var expectMs = sentAt + expectDuration * 1000;
      var diff = Math.abs(vuMs - expectMs) / 1000;
      console.log("[pay-link] validUntilDiffSec=", diff, "expectDuration=", expectDuration, "language=", Var("pay_language_sent", ""));
      pm.expect(diff, "validUntil 偏差过大 diffSec=" + diff).to.be.at.most(skewSec);
    });
  }

  // 保存链接供手工打开验语种/过期
  try {
    if (action && action.url) {
      pm.collectionVariables.set("pay_last_url", String(action.url));
      pm.environment.set("pay_last_url", String(action.url));
    }
    if (action && (action.validUntil != null || action.vaildUntil != null)) {
      var v = action.validUntil != null ? action.validUntil : action.vaildUntil;
      pm.collectionVariables.set("pay_last_validUntil", String(v));
    }
  } catch (eSave) {}
}

console.log("[pay-link] done case=" + caseId + " bizOk=" + BizOk(json));
