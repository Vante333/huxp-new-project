/**
 * FT 过去时间拦截 — 精简后置
 *
 * 只断言一件事：过去时间 → 500.020.030
 * 不要和「业务成功 / available=true / 有 token」写在一起。
 *
 * 环境/用例变量：
 *   ft_expect_type = fail_past | success_slot
 *     不填默认 fail_past（本脚本就是为过去时间准备的）
 *
 * 遇到 007 / 071.019：直接判失败并写清原因，不要再和 030 比。
 */
function pick(key, fallback) {
  var v = "";
  try {
    v = pm.variables.get(key);
  } catch (e0) {}
  if (v === null || v === undefined || v === "") {
    try {
      v = pm.collectionVariables.get(key);
    } catch (e1) {}
  }
  if (v === null || v === undefined || v === "") {
    try {
      v = pm.environment.get(key);
    } catch (e2) {}
  }
  if (v === null || v === undefined || v === "") return fallback === undefined ? "" : String(fallback);
  return String(v);
}

var expectType = pick("ft_expect_type", "fail_past");
var sentDate = pick("ft_sent_prebookingDate", "");
var sentRes = pick("ft_sent_resourceId", "");

var json = {};
try {
  json = pm.response.json();
} catch (e) {
  json = {};
}
var data = json.data;
var errCode = String(json.errCode || json.errorCode || "");
var msg = String(json.msg || "");
var code = json.code;

pm.test("HTTP 200（业务码看 Body）", function () {
  pm.expect(pm.response.code).to.eql(200);
});

if (errCode === "500.020.007") {
  pm.test("资源不在当前 Program（500.020.007）— 先换 ID，不要测 030", function () {
    pm.expect.fail(
      "resourceId=" +
        sentRes +
        " 当前 Program 用不了。去 GET /v2/resources?module=2 重拉清单。msg=" +
        msg
    );
  });
} else if (errCode === "071.019" || /not accessible|no permission|无权/i.test(msg)) {
  pm.test("ePass/权限问题 — 不是过去时间拦截", function () {
    pm.expect.fail("errCode=" + errCode + " msg=" + msg + " resourceId=" + sentRes);
  });
} else if (expectType === "success_slot") {
  pm.test("未来时间：code=0", function () {
    pm.expect(code === 0 || code === "0", "code=" + code + " err=" + errCode + " msg=" + msg).to.eql(true);
  });
  pm.test("未来时间：不是 500.020.030", function () {
    pm.expect(errCode).to.not.eql("500.020.030");
  });
  pm.test("未来时间：available=true 且有 token", function () {
    pm.expect(data && data.available, "available").to.eql(true);
    pm.expect(data && data.prebookingToken, "prebookingToken").to.be.a("string").and.not.eql("");
  });
} else {
  pm.test("过去时间：应拦截 500.020.030", function () {
    pm.expect(errCode, "实际 code=" + code + " msg=" + msg + " date=" + sentDate + " resourceId=" + sentRes).to.eql(
      "500.020.030"
    );
  });
  pm.test("过去时间：文案含当地时间", function () {
    var ok =
      /current local time/i.test(msg) ||
      /earlier than/i.test(msg) ||
      /早于当前/.test(msg) ||
      /当地时间/.test(msg);
    pm.expect(ok, "msg=" + msg).to.eql(true);
  });
}

console.log(
  "[ft-smoke] expect=",
  expectType,
  "code=",
  code,
  "err=",
  errCode,
  "date=",
  sentDate,
  "resourceId=",
  sentRes
);
