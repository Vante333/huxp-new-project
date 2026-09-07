/**
 * SSO 免登短链 — 全量用例后置断言
 * sso_expect_type:
 *   success | success_default_lang | fail_602 | fail_auth | fail_param | fail_biz | record_only | idempotent_store | idempotent_check
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
function Entry(data) {
  if (!data) return null;
  if (data.entry) return data.entry;
  return data;
}

var caseId = Var("sso_last_case_id", "SSO");
var expectType = Var("sso_expect_type", "success");
var expectErr = Var("sso_expect_errCode", "");
var language = Var("sso_language_sent", "");
var sceneSent = Var("sso_scene_sent", "");
var expectSceneEcho = Var("sso_expect_scene_echo", "");
var expectLangEcho = Var("sso_expect_language_echo", "");
var assertValidUntil = Env("sso_assert_validUntil", "false") === "true";
var expectDuration = parseInt(Var("sso_expect_duration", "600"), 10) || 600;
var sentAt = parseInt(Var("sso_sent_at_ms", String(Date.now())), 10) || Date.now();
var skewSec = parseInt(Env("sso_validUntil_skew_sec", "30"), 10) || 30;

var json = {};
try { json = pm.response.json(); } catch (e) { json = {}; }
var data = json.data !== undefined ? json.data : json;
var entry = Entry(data);
var errCode = String(json.errCode || json.errorCode || "");
var msg = String(json.msg || "");

pm.test("[" + caseId + "] HTTP 可到达", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

function assertSuccess() {
  pm.test("[" + caseId + "] 业务成功", function () {
    pm.expect(BizOk(json), "code=" + json.code + " err=" + errCode + " msg=" + msg).to.eql(true);
  });
  pm.test("[" + caseId + "] 返回 shortUrl", function () {
    var url = entry && (entry.shortUrl || entry.url);
    pm.expect(url, "shortUrl missing").to.be.a("string").and.not.eql("");
  });
  if (expectSceneEcho) {
    pm.test("[" + caseId + "] 回显 scene=" + expectSceneEcho, function () {
      pm.expect(String(data.scene || "")).to.eql(expectSceneEcho);
    });
  }
  if (expectLangEcho) {
    pm.test("[" + caseId + "] 回显 language=" + expectLangEcho, function () {
      pm.expect(String(data.language || "")).to.eql(expectLangEcho);
    });
  }
  if (assertValidUntil && entry && entry.validUntil != null) {
    pm.test("[" + caseId + "] validUntil ±" + skewSec + "s", function () {
      var vu = Number(entry.validUntil);
      if (vu < 1e12) vu = vu * 1000;
      var diff = Math.abs(vu - (sentAt + expectDuration * 1000)) / 1000;
      pm.expect(diff).to.be.at.most(skewSec);
    });
  }
  try {
    var url = entry && (entry.shortUrl || entry.url);
    if (url) {
      pm.environment.set("sso_last_shortUrl", String(url));
      pm.collectionVariables.set("sso_last_shortUrl", String(url));
    }
  } catch (e1) {}
}

function assertFail() {
  pm.test("[" + caseId + "] 业务失败", function () {
    pm.expect(BizOk(json), "不应成功").to.eql(false);
  });
  if (expectErr) {
    pm.test("[" + caseId + "] errCode=" + expectErr, function () {
      pm.expect(errCode).to.eql(expectErr);
    });
  }
}

if (expectType === "success" || expectType === "success_default_lang") {
  if (expectType === "success_default_lang") {
    expectLangEcho = expectLangEcho || "en-US";
  }
  assertSuccess();
  if (language && language !== "(omit)" && !expectLangEcho) {
    if (data && data.language) {
      pm.test("[" + caseId + "] language 回显一致", function () {
        pm.expect(String(data.language)).to.eql(String(language));
      });
    }
  }
} else if (expectType === "fail_602") {
  expectErr = expectErr || "500.000.602";
  assertFail();
  pm.test("[" + caseId + "] 602 文案含 extra/required", function () {
    var low = msg.toLowerCase();
    pm.expect(low.indexOf("extra") >= 0 || low.indexOf("required") >= 0).to.eql(true);
  });
} else if (expectType === "fail_auth") {
  assertFail();
  pm.test("[" + caseId + "] 鉴权失败(401或业务鉴权码)", function () {
    var ok = pm.response.code === 401 || pm.response.code === 403 || !BizOk(json);
    pm.expect(ok).to.eql(true);
  });
} else if (expectType === "fail_param" || expectType === "fail_biz") {
  assertFail();
  if (expectErr) {
    pm.test("[" + caseId + "] 记录/校验 errCode", function () {
      console.log("[sso-full] actual errCode=", errCode, "msg=", msg);
      if (expectErr !== "*") pm.expect(errCode).to.eql(expectErr);
      else pm.expect(true).to.be.true;
    });
  } else {
    pm.test("[" + caseId + "] 记录失败码", function () {
      console.log("[sso-full] actual errCode=", errCode, "msg=", msg);
      pm.environment.set("sso_last_errCode", errCode);
      pm.expect(true).to.be.true;
    });
  }
} else if (expectType === "idempotent_store") {
  assertSuccess();
  var url = entry && (entry.shortUrl || entry.url);
  pm.environment.set("sso_idem_shortUrl", String(url || ""));
  pm.environment.set("sso_idem_validUntil", String(entry && entry.validUntil != null ? entry.validUntil : ""));
} else if (expectType === "idempotent_check") {
  assertSuccess();
  var url2 = entry && (entry.shortUrl || entry.url);
  var prev = Env("sso_idem_shortUrl", "");
  pm.test("[" + caseId + "] shortUrl 与上次一致", function () {
    pm.expect(String(url2)).to.eql(prev);
  });
} else if (expectType === "record_only") {
  pm.test("[" + caseId + "] 仅记录响应(人工/待确认)", function () {
    console.log("[sso-full] RECORD code=", json.code, "err=", errCode, "msg=", msg, "data=", JSON.stringify(data));
    pm.expect(true).to.be.true;
  });
} else {
  pm.test("[" + caseId + "] 未知 expect_type=" + expectType, function () {
    pm.expect.fail("未知 sso_expect_type");
  });
}

console.log("[sso-full] done case=" + caseId + " expect=" + expectType + " bizOk=" + BizOk(json) + " err=" + errCode);
