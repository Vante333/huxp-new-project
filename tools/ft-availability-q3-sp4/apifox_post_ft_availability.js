/**
 * FT 可用性过滤过去时间 — 后置断言
 *
 * ft_expect_type:
 *   success      业务成功，available 可为 true/false（不强制 true），不报 500.020.030
 *   success_slot 业务成功且 available=true，有 prebookingToken
 *   fail_past    期望 errCode=500.020.030（或 ft_expect_errCode）
 *   fail_err     期望业务失败 + 指定 errCode
 *   record_only  只记录，不强制码（迁移/空时区待确认场景）
 */
function Env(key, defVal) {
  var v = "";
  try {
    v = pm.environment.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}
function Var(key, defVal) {
  var v = "";
  try {
    v = pm.variables.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") {
    try {
      v = pm.collectionVariables.get(key);
    } catch (e2) {}
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

var caseId = Var("case_id", "FT可用性");
var expectType = Var("ft_expect_type", "success");
var expectErr = Var("ft_expect_errCode", "");
var sentDate = Var("ft_sent_prebookingDate", "");

var json = {};
try {
  json = pm.response.json();
} catch (e) {
  json = {};
}
var data = json.data !== undefined ? json.data : null;
var errCode = String(json.errCode || json.errorCode || "");
var msg = String(json.msg || "");

pm.test("[" + caseId + "] HTTP 可到达", function () {
  pm.expect(pm.response.code).to.be.oneOf([200, 400, 401, 403, 404, 422, 500]);
});

if (expectType === "success" || expectType === "success_slot") {
  pm.test("[" + caseId + "] 业务成功", function () {
    pm.expect(BizOk(json), "code=" + json.code + " err=" + errCode + " msg=" + msg).to.eql(true);
  });
  pm.test("[" + caseId + "] 不返回过去时间错误码 500.020.030", function () {
    pm.expect(errCode).to.not.eql("500.020.030");
  });
  if (expectType === "success_slot") {
    pm.test("[" + caseId + "] available=true", function () {
      pm.expect(data && data.available, "available").to.eql(true);
    });
    pm.test("[" + caseId + "] 返回 prebookingToken", function () {
      var tok = data && data.prebookingToken;
      pm.expect(tok, "prebookingToken").to.be.a("string").and.not.eql("");
    });
    try {
      if (data && data.prebookingToken) {
        pm.environment.set("prebookingToken", String(data.prebookingToken));
        pm.collectionVariables.set("prebookingToken", String(data.prebookingToken));
      }
    } catch (eTok) {}
  }
} else if (expectType === "fail_past" || expectType === "fail_err") {
  var want = expectErr || (expectType === "fail_past" ? "500.020.030" : "");
  pm.test("[" + caseId + "] 业务失败", function () {
    pm.expect(BizOk(json), "不应成功 code=" + json.code).to.eql(false);
  });
  if (want) {
    pm.test("[" + caseId + "] errCode=" + want, function () {
      pm.expect(errCode, "msg=" + msg).to.eql(want);
    });
  }
  if (want === "500.020.030" || expectType === "fail_past") {
    pm.test("[" + caseId + "] 文案含 current local time(英文口径)", function () {
      // 中英文任一命中即可；英文为需求样例
      var ok =
        /current local time/i.test(msg) ||
        /earlier than/i.test(msg) ||
        /早于当前/.test(msg) ||
        /当地时间/.test(msg);
      pm.expect(ok, "msg=" + msg).to.eql(true);
    });
  }
} else if (expectType === "record_only") {
  pm.test("[" + caseId + "] 仅记录响应(待确认预期)", function () {
    console.log(
      "[ft-avail][record]",
      caseId,
      "code=",
      json.code,
      "err=",
      errCode,
      "msg=",
      msg,
      "date=",
      sentDate
    );
    pm.expect(true).to.be.true;
  });
}

try {
  pm.environment.set("ft_last_errCode", errCode);
  pm.environment.set("ft_last_msg", msg);
  pm.environment.set("ft_last_code", String(json.code));
} catch (eSave) {}

console.log(
  "[ft-avail] done case=",
  caseId,
  "expect=",
  expectType,
  "code=",
  json.code,
  "err=",
  errCode,
  "prebookingDate=",
  sentDate
);
