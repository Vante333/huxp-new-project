/**
 * PAPI SSO 免登短链 — 后置断言
 * 成功：code 成功 + entry.shortUrl + 可选 validUntil
 * 缺 extra.orderId（ORDER_DETAIL）：errCode 500.000.602
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

var caseId = Var("sso_last_case_id", "SSO");
var language = Var("sso_language_sent", "");
var scene = Var("sso_scene_sent", "");
var expect602 = Env("sso_expect_602", "false") === "true";
var assertValidUntil = Env("sso_assert_validUntil", "true") !== "false";
var expectDuration = parseInt(Var("sso_expect_duration", "600"), 10) || 600;
var sentAt = parseInt(Var("sso_sent_at_ms", String(Date.now())), 10) || Date.now();
var skewSec = parseInt(Env("sso_validUntil_skew_sec", "30"), 10) || 30;

var json = {};
try { json = pm.response.json(); } catch (e) { json = {}; }

pm.test("[" + caseId + "] HTTP 可到达", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

if (expect602) {
  pm.test("[" + caseId + "] 缺 extra 应失败 500.000.602", function () {
    pm.expect(BizOk(json)).to.eql(false);
    pm.expect(String(json.errCode || json.errorCode)).to.eql("500.000.602");
  });
  pm.test("[" + caseId + "] 602 文案含 extra", function () {
    var msg = String(json.msg || "");
    pm.expect(msg.toLowerCase().indexOf("extra") >= 0 || msg.indexOf("required") >= 0).to.eql(true);
  });
} else {
  pm.test("[" + caseId + "] 语种=" + language + " 业务成功", function () {
    pm.expect(
      BizOk(json),
      "code=" + json.code + " err=" + (json.errCode || json.errorCode) + " msg=" + json.msg
    ).to.eql(true);
  });

  var data = json.data !== undefined ? json.data : json;
  var entry = data && data.entry ? data.entry : data;

  pm.test("[" + caseId + "] 返回 shortUrl", function () {
    var url = entry && (entry.shortUrl || entry.url);
    pm.expect(url, "shortUrl missing").to.be.a("string").and.not.eql("");
  });

  if (data && data.language && !String(language).startsWith("(omit")) {
    pm.test("[" + caseId + "] 回显 language 与请求一致", function () {
      pm.expect(String(data.language)).to.eql(String(language));
    });
  }

  if (assertValidUntil && entry && (entry.validUntil != null)) {
    pm.test("[" + caseId + "] validUntil 接近 now+duration(±" + skewSec + "s)", function () {
      var vu = Number(entry.validUntil);
      if (vu < 1e12) vu = vu * 1000;
      var expectMs = sentAt + expectDuration * 1000;
      var diff = Math.abs(vu - expectMs) / 1000;
      console.log("[sso-link] validUntilDiffSec=", diff, "expectDuration=", expectDuration);
      pm.expect(diff).to.be.at.most(skewSec);
    });
  }

  try {
    var url = entry && (entry.shortUrl || entry.url);
    if (url) {
      pm.environment.set("sso_last_shortUrl", String(url));
      pm.collectionVariables.set("sso_last_shortUrl", String(url));
    }
    var oks = Env("sso_lang_ok_list", "");
    var fails = Env("sso_lang_fail_list", "");
    if (BizOk(json) && url) {
      oks = oks ? oks + "," + language : language;
      pm.environment.set("sso_lang_ok_list", oks);
    } else {
      fails = fails ? fails + "," + language : language;
      pm.environment.set("sso_lang_fail_list", fails);
    }
  } catch (eSave) {}
}

console.log("[sso-link] done case=" + caseId + " bizOk=" + BizOk(json) + " err=" + (json.errCode || json.errorCode));
