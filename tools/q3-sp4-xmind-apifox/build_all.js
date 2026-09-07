/**
 * 按 XMind 四需求生成 Apifox 场景 JSON（目录标准：P1/功能名/按XMind用例/0N）。
 * 用法: node build_all.js
 */
const fs = require("fs");
const path = require("path");
const {
  PROJECT_ID,
  RID,
  apiHeaders,
  customHttp,
  group,
  authStep,
  bizOkAssert,
} = require("./lib");

const outDir = path.join(__dirname, "generated");
fs.mkdirSync(outDir, { recursive: true });
const langs = JSON.parse(fs.readFileSync(path.join(__dirname, "pay_languages_xmind.json"), "utf8"));

const SEED_SSO = [
  "if (!String(pm.environment.get('ProgramID') || pm.environment.get('Program-ID') || '')) {",
  "  pm.environment.set('ProgramID', '1919256841868288');",
  "  pm.environment.set('Program-ID', '1919256841868288');",
  "}",
  "if (!String(pm.environment.get('clientId') || '')) pm.environment.set('clientId', String(pm.collectionVariables.get('clientId') || ''));",
  "if (!String(pm.environment.get('secret') || '')) pm.environment.set('secret', String(pm.collectionVariables.get('secret') || ''));",
  "if (!pm.environment.get('sso_subject_id')) pm.environment.set('sso_subject_id', '8576507744260001');",
  "if (!pm.environment.get('sso_orderId')) pm.environment.set('sso_orderId', 'FT20260904BG5VM58');",
  "if (!pm.environment.get('fastTrackResourceId')) pm.environment.set('fastTrackResourceId', 'C10826');",
  "if (!pm.environment.get('ft_tz_offset_hours')) pm.environment.set('ft_tz_offset_hours', '7');",
  "if (!pm.environment.get('membershipId')) pm.environment.set('membershipId', '8576507744260001');",
  "if (!pm.environment.get('pay_returnUrl')) pm.environment.set('pay_returnUrl', 'https://www.ly.com');",
  "if (!pm.environment.get('pay_paymentMethod')) pm.environment.set('pay_paymentMethod', 'H5_CASHIER');",
].join("\n");

const SEED_DUAL = [
  "if (!String(pm.environment.get('ProgramID') || '')) pm.environment.set('ProgramID', '2045264240542720');",
  "pm.environment.set('Program-ID', String(pm.environment.get('ProgramID')));",
  "var which = String(pm.variables.get('auth_which') || '1');",
  "if (which === '2') {",
  "  if (pm.environment.get('auth2_clientId')) pm.environment.set('clientId', String(pm.environment.get('auth2_clientId')));",
  "  if (pm.environment.get('auth2_secret')) pm.environment.set('secret', String(pm.environment.get('auth2_secret')));",
  "} else {",
  "  if (pm.environment.get('auth1_clientId')) pm.environment.set('clientId', String(pm.environment.get('auth1_clientId')));",
  "  if (pm.environment.get('auth1_secret')) pm.environment.set('secret', String(pm.environment.get('auth1_secret')));",
  "}",
].join("\n");

function writeScenario(file, payload) {
  fs.writeFileSync(path.join(outDir, file), JSON.stringify(payload), "utf8");
}

function ftDatePre(mode, extra) {
  return [
    extra || "",
    "function pad(n){return n<10?'0'+n:String(n);}",
    "function wall(utcMs, off){ var d=new Date(utcMs+off*3600*1000); return d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes()); }",
    "var off = parseFloat(pm.variables.get('ft_tz_offset_hours') || pm.environment.get('ft_tz_offset_hours') || '7');",
    "if (isNaN(off)) off = 7;",
    "var mode = '" + mode + "';",
    "var date = '';",
    "if (mode==='past') date = wall(Date.now()-30*60*1000, off);",
    "else { date = wall(Date.now()+10*24*3600*1000, off).replace(/T\\d{2}:\\d{2}$/, 'T10:00'); }",
    "var rid = String(pm.variables.get('ft_resourceId') || pm.environment.get('fastTrackResourceId') || 'C10826');",
    "var body = { module: 2, resourceId: rid, prebookingDate: date, adultCount: 1, childCount: 0 };",
    "var mid = String(pm.environment.get('membershipId') || '');",
    "if (mid) body.membershipId = mid;",
    "pm.request.body = { type: 'json', data: JSON.stringify(body, null, 2) };",
    "try { pm.request.body = { mode:'raw', raw: JSON.stringify(body,null,2), options:{raw:{language:'json'}} }; } catch(eB) {}",
    RID,
  ].join("\n");
}

function postExpectErr(code, msgPart) {
  return bizOkAssert(
    [
      "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
      "pm.test('检查点 | 期望=errCode=" + code + " | 实际=' + err, function () { pm.expect(err).to.eql('" + code + "'); });",
      "pm.test('检查点 | 期望=不是旧码 500.020.030 业务串味 | 实际=' + err, function () {",
      "  if ('" + code + "' !== '500.020.030') pm.expect(err).to.not.eql('500.020.030');",
      "});",
      msgPart
        ? "pm.test('检查点 | 期望=文案含指定句 | 实际=' + msg, function () { pm.expect(msg).to.include(" + JSON.stringify(msgPart) + "); });"
        : "",
    ].join("\n")
  );
}

function postSuccessNot030() {
  return bizOkAssert(
    [
      "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
      "pm.test('检查点 | 期望=不是 500.020.030 | 实际=' + err, function () { pm.expect(err).to.not.eql('500.020.030'); });",
    ].join("\n")
  );
}

function postSsoSuccess() {
  return bizOkAssert(
    [
      "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
      "var url = json.data && json.data.entry && json.data.entry.shortUrl;",
      "pm.test('检查点 | 期望=有 shortUrl | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
    ].join("\n")
  );
}

function postPay(kind) {
  return bizOkAssert(
    [
      "var caseKind = '" + kind + "';",
      "if (caseKind === 'over') {",
      "  pm.test('检查点 | 期望=超上限失败 | 实际 code=' + json.code + ' err=' + err, function () {",
      "    pm.expect(json.code).to.not.eql(0);",
      "    pm.expect(['301.000.001','302.000.001','300.000.001'].indexOf(err) >= 0 || json.code === -1).to.eql(true);",
      "  });",
      "} else if (err === '500.000.802' || err === '500.000.804') {",
      "  pm.test.skip('当前 orderId 不可支付（' + err + '）。请把环境 pay_orderId 换成会籍待支付 MS 单后再跑语种/默认有效期。');",
      "} else {",
      "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
      "  var action = json.data && (json.data.paymentAction || (json.data.payment && json.data.payment.paymentAction));",
      "  var url = action && (action.url || action.redirectUrl);",
      "  pm.test('检查点 | 期望=有支付url | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
      "  if (url) { try { pm.environment.set('pay_last_url', String(url)); } catch (eU) {} }",
      "}",
    ].join("\n")
  );
}

function payBody(obj) {
  return obj;
}

function payPre(setJs) {
  return [setJs || "", RID].join("\n");
}

let n = 0;
function next() {
  n += 1;
  return n;
}
function resetN() {
  n = 0;
}

function scenario(name, desc, tags, steps, priority) {
  return {
    name,
    description: desc,
    folderId: 0,
    priority: priority == null ? 1 : priority,
    tags,
    steps,
  };
}

const DESC_FT =
  "来源桌面《需求测试用例.xmind》二、FT可用性。先 Auth 再业务。环境：UAT canary；Program 默认 SSO AllCategories 1919256841868288；FT 资源默认 C10826（Bangkok +7）。Header 必带 Token、X-Program-ID、X-Request-ID。";
const DESC_PAY =
  "来源 XMind 三、支付链接。Body 字段与脑图一致：orderId + returnUrl + paymentMethod=H5_CASHIER，language/duration 按用例省略或填写。成功路径需要会籍待支付 MS 单（pay_orderId）；SSO 使用单常返回 802/804。超上限 1801 已在 canary 验证为 301.000.001。";
const DESC_AUTH =
  "来源 XMind 四、Auth双密钥。鉴权1/鉴权2 的 clientId/secret 放环境 auth1_* / auth2_*（桌面数据集123 当前沙箱 201.000.001 已失效，勿写死旧 secret）。RS256 组合与密钥增删改在 BOSS 配置，本场景只覆盖能接口化的取 Token。";

resetN();
const ft01 = scenario(
  "FT可用性 · 01过去时间拦截",
  DESC_FT,
  ["ft", "xmind", "q3-sp4"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 过去/未来", [
      customHttp(next(), {
        name: "【过去时间拦截】| FT-030 | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "{{fastTrackResourceId}}", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【时区换算-当地已过】| FT-030-TZ | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10899", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past", "pm.variables.set('ft_tz_offset_hours','-3'); pm.variables.set('ft_resourceId','C10899');"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【未来时间不报030】| FT-FUTURE | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "{{fastTrackResourceId}}", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("future", "pm.variables.set('ft_resourceId','C10826'); pm.variables.set('ft_tz_offset_hours','7');"),
        post: postSuccessNot030(),
      }),
    ]),
    group("02 多时区抽样", [
      ["C10826", "7", "BKK"],
      ["C10711", "8", "PEK"],
      ["C10726", "4", "DXB"],
      ["C10849", "2", "PRG"],
      ["C10899", "-3", "AEP"],
    ].map(([rid, off, iata]) =>
      customHttp(next(), {
        name: "【过去时间-" + iata + "】| FT-030-" + iata + " | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: rid, prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past", "pm.variables.set('ft_resourceId','" + rid + "'); pm.variables.set('ft_tz_offset_hours','" + off + "');"),
        post: postExpectErr("500.020.030", "current local time"),
      })
    ),
    ),
  ]
);
writeScenario("ft-01.json", ft01);

resetN();
const profile = {
  email: "2484268151@qq.COM",
  clientUserId: "{{$guid}}",
  callingCode: "86",
  phoneNumber: "15838657142",
};
const ft02 = scenario(
  "FT可用性 · 02错误码迁移039-044",
  DESC_FT + " 会籍错误码已从 500.020.030~035 迁到 500.030.039~044。不要用 availability 测 039。",
  ["ft", "err", "xmind"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 迁移码", [
      customHttp(next(), {
        name: "【原030迁039 Preview AR=true】| ERR-039 | POST /v2/orders/memberships/purchase/preview",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase/preview",
        headers: apiHeaders(true),
        body: { appId: 1, autoRenewal: true, profile },
        pre: RID,
        post: postExpectErr("500.030.039", "Unable to preview"),
      }),
      customHttp(next(), {
        name: "【原031迁040 Create AR=false】| ERR-040 | POST /v2/orders/memberships/purchase",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase",
        headers: apiHeaders(true),
        body: { appId: 1, autoRenewal: false, profile },
        pre: RID,
        post: postExpectErr("500.030.040", "unable to process your order"),
      }),
      customHttp(next(), {
        name: "【原033迁042 Create AR=true】| ERR-042 | POST /v2/orders/memberships/purchase",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase",
        headers: apiHeaders(true),
        body: { appId: 1, autoRenewal: true, profile },
        pre: RID,
        post: bizOkAssert(
          [
            "pm.test('检查点 | 期望=不是旧码 500.020.033 | 实际=' + err, function () { pm.expect(err).to.not.eql('500.020.033'); });",
            "pm.test('检查点 | 期望=039或042 | 实际=' + err, function () { pm.expect(['500.030.039','500.030.042']).to.include(err); });",
          ].join("\n")
        ),
      }),
      customHttp(next(), {
        name: "【原035迁044 会籍不存在】| ERR-044 | POST /v2/memberships/subscriptions/cancellation",
        method: "post",
        reqPath: "/v2/memberships/subscriptions/cancellation",
        headers: apiHeaders(true),
        body: { membershipId: "0000000000000000", email: "2484268151@qq.COM" },
        pre: RID,
        post: postExpectErr("500.030.044", "Failed to cancel"),
      }),
    ]),
  ]
);
writeScenario("ft-02.json", ft02);

resetN();
const ft03 = scenario(
  "FT可用性 · 03补充错误码045",
  DESC_FT,
  ["ft", "045", "xmind"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 045", [
      customHttp(next(), {
        name: "【purchase/details 不存在单】| ERR-045 | POST /v2/orders/memberships/purchase/details",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase/details",
        headers: apiHeaders(true),
        body: { orderId: "9999999999999999" },
        pre: RID,
        post: postExpectErr("500.030.045", "unable to retrieve the order details"),
      }),
    ]),
  ]
);
writeScenario("ft-03.json", ft03);

resetN();
const ft04 = scenario(
  "FT可用性 · 04时区特殊与空时区",
  DESC_FT + " 空时区资源需后台造数；无资源时本步记录实际码，不把本机时区当当地时间。",
  ["ft", "tz", "xmind"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 空时区", [
      customHttp(next(), {
        name: "【空时区资源可用性】| FT-TZ-EMPTY | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "{{ft_empty_tz_resourceId}}", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: [
          "var rid = String(pm.environment.get('ft_empty_tz_resourceId') || '');",
          "if (!rid) { pm.variables.set('ft_skip_empty_tz','true'); }",
          ftDatePre("future", "if (rid) pm.variables.set('ft_resourceId', rid);"),
        ].join("\n"),
        post: bizOkAssert(
          [
            "if (String(pm.variables.get('ft_skip_empty_tz')||'')==='true') { pm.test.skip('未配置 ft_empty_tz_resourceId，空时区手工造数后再跑'); }",
            "else { console.log('[ft-tz-empty] code='+json.code+' err='+err+' msg='+msg); pm.test('检查点 | 期望=有稳定结果 | 实际=' + err, function () { pm.expect(pm.response.code).to.eql(200); }); }",
          ].join("\n")
        ),
      }),
    ]),
  ]
);
writeScenario("ft-04.json", ft04);

function payHttp(title, id, body, kind) {
  return customHttp(next(), {
    name: title + " | " + id + " | POST /v2/orders/payments",
    method: "post",
    reqPath: "/v2/orders/payments",
    headers: apiHeaders(true),
    body,
    pre: payPre(
      [
        "var oid = String(pm.environment.get('pay_orderId') || '');",
        "if (oid) { try { var b = " + JSON.stringify(body) + "; b.orderId = oid; pm.request.body = { mode:'raw', raw: JSON.stringify(b,null,2), options:{raw:{language:'json'}} }; } catch(eP) {} }",
      ].join("\n")
    ),
    post: postPay(kind || "ok"),
  });
}

resetN();
const pay01Steps = [
  group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
  group("01 默认与 en-US", [
    payHttp("【不传language默认en-US】", "PAY-LANG-DEFAULT", {
      orderId: "{{pay_orderId}}",
      returnUrl: "https://www.ly.com",
      paymentMethod: "H5_CASHIER",
    }),
    payHttp("【language=en-US】", "PAY-LANG-EN", {
      orderId: "{{pay_orderId}}",
      returnUrl: "https://www.ly.com",
      paymentMethod: "H5_CASHIER",
      language: "en-US",
    }),
  ]),
  group(
    "02 XMind12语种",
    langs.map((lang) =>
      payHttp("【language=" + lang + "】", "PAY-LANG-" + lang, {
        orderId: "{{pay_orderId}}",
        returnUrl: "https://www.ly.com",
        paymentMethod: "H5_CASHIER",
        language: lang,
        durationInSeconds: 1800,
      })
    )
  ),
];
writeScenario(
  "pay-01.json",
  scenario("支付链接 · 01语种language校验", DESC_PAY, ["pay", "lang", "xmind"], pay01Steps)
);

resetN();
const pay02 = scenario(
  "支付链接 · 02有效期durationInSeconds校验",
  DESC_PAY,
  ["pay", "duration", "xmind"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 有效期", [
      payHttp("【不传duration默认600】", "PAY-DUR-DEFAULT", {
        orderId: "{{pay_orderId}}",
        returnUrl: "https://www.ly.com",
        paymentMethod: "H5_CASHIER",
      }),
      payHttp("【duration=60】", "PAY-DUR-60", {
        orderId: "{{pay_orderId}}",
        returnUrl: "https://www.ly.com",
        paymentMethod: "H5_CASHIER",
        durationInSeconds: 60,
      }),
      payHttp("【duration=1800上限】", "PAY-DUR-1800", {
        orderId: "{{pay_orderId}}",
        returnUrl: "https://www.ly.com",
        paymentMethod: "H5_CASHIER",
        language: "en-US",
        durationInSeconds: 1800,
      }),
      payHttp(
        "【duration=1801超上限】",
        "PAY-DUR-1801",
        {
          orderId: "{{pay_orderId}}",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          durationInSeconds: 1801,
        },
        "over"
      ),
    ]),
  ]
);
writeScenario("pay-02.json", pay02);

resetN();
const auth02 = scenario(
  "Auth双密钥 · 02两套token跑通链路",
  DESC_AUTH,
  ["auth", "dual", "xmind"],
  [
    group("00 鉴权1", [
      customHttp(next(), {
        name: "【鉴权1取Token】| AUTH-1 | POST /v2/auth/token",
        method: "post",
        reqPath: "/v2/auth/token",
        headers: apiHeaders(false),
        body: { clientId: "{{clientId}}", secret: "{{secret}}" },
        pre: "pm.variables.set('auth_which','1');\n" + SEED_DUAL + "\n" + RID,
        post: bizOkAssert(
          "pm.test('检查点 | 期望=code=0（密钥失效则为 201.000.001，需换有效鉴权1） | 实际=' + json.code + ' ' + err, function () { if (err==='201.000.001') pm.expect.fail('鉴权1 secret 无效，请更新环境 auth1_clientId/auth1_secret'); pm.expect(json.code).to.eql(0); });"
        ),
      }),
    ]),
    group("01 鉴权2", [
      customHttp(next(), {
        name: "【鉴权2取Token】| AUTH-2 | POST /v2/auth/token",
        method: "post",
        reqPath: "/v2/auth/token",
        headers: apiHeaders(false),
        body: { clientId: "{{clientId}}", secret: "{{secret}}" },
        pre: "pm.variables.set('auth_which','2');\n" + SEED_DUAL + "\n" + RID,
        post: bizOkAssert(
          "pm.test('检查点 | 期望=code=0 | 实际=' + json.code + ' ' + err, function () { if (err==='201.000.001') pm.expect.fail('鉴权2 secret 无效，请更新环境 auth2_clientId/auth2_secret'); pm.expect(json.code).to.eql(0); });"
        ),
      }),
    ]),
  ]
);
writeScenario("auth-02.json", auth02);

resetN();
const auth03 = scenario(
  "Auth双密钥 · 03RS256与HS256判定组合",
  DESC_AUTH + " 组合1~3 需 BOSS 配 RS256，接口侧只记录 JWT alg。当前沙箱数据集为 HS256 双钥（密钥有效后验 alg=HS256）。",
  ["auth", "alg", "xmind"],
  [
    group("00 HS256+HS256", [
      customHttp(next(), {
        name: "【组合4 鉴权1 HS256】| AUTH-ALG-1 | POST /v2/auth/token",
        method: "post",
        reqPath: "/v2/auth/token",
        headers: apiHeaders(false),
        body: { clientId: "{{clientId}}", secret: "{{secret}}" },
        pre: "pm.variables.set('auth_which','1');\n" + SEED_DUAL + "\n" + RID,
        post: bizOkAssert(
          [
            "if (err==='201.000.001') { pm.test.skip('密钥无效，先修鉴权1'); } else {",
            "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
            "}",
          ].join("\n")
        ),
      }),
    ]),
  ]
);
writeScenario("auth-03.json", auth03);

resetN();
const auth04 = scenario(
  "Auth双密钥 · 04密钥配置增删改",
  "BOSS 增删改密钥后，用剩余/新密钥调 POST /v2/auth/token。本场景只保留「当前环境能取到的那把钥」。增删改步骤请在 BOSS 手工做。",
  ["auth", "crud", "xmind"],
  [
    group("00 当前密钥仍可签发", [
      customHttp(next(), {
        name: "【当前config取Token】| AUTH-CRUD | POST /v2/auth/token",
        method: "post",
        reqPath: "/v2/auth/token",
        headers: apiHeaders(false),
        body: { clientId: "{{clientId}}", secret: "{{secret}}" },
        pre: "pm.variables.set('auth_which','1');\n" + SEED_DUAL + "\n" + RID,
        post: bizOkAssert(
          "if (err==='201.000.001') { pm.test.skip('请先在环境写入有效 auth1_* 再测增删改'); } else { pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); }); }"
        ),
      }),
    ]),
  ]
);
writeScenario("auth-04.json", auth04);

resetN();
const p0Ft = scenario(
  "FT可用性 · 冒烟",
  "P0：Auth + 过去时间 030 + 未来成功。",
  ["ft", "smoke"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 冒烟", [
      customHttp(next(), {
        name: "【过去时间拦截】| FT-SMOKE-PAST | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10826", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【未来时间】| FT-SMOKE-FUTURE | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10826", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("future"),
        post: postSuccessNot030(),
      }),
    ]),
  ],
  0
);
writeScenario("p0-ft.json", p0Ft);

resetN();
const p0Pay = scenario(
  "支付链接 · 冒烟",
  "P0：Auth + duration=1801 校验（不依赖可支付单）+ 若 pay_orderId 可支付则再打一条 en-US。",
  ["pay", "smoke"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 冒烟", [
      payHttp(
        "【duration=1801】",
        "PAY-SMOKE-1801",
        {
          orderId: "{{pay_orderId}}",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          durationInSeconds: 1801,
        },
        "over"
      ),
      payHttp("【language=en-US duration=1800】", "PAY-SMOKE-EN", {
        orderId: "{{pay_orderId}}",
        returnUrl: "https://www.ly.com",
        paymentMethod: "H5_CASHIER",
        language: "en-US",
        durationInSeconds: 1800,
      }),
    ]),
  ],
  0
);
writeScenario("p0-pay.json", p0Pay);

resetN();
const p0Sso = scenario(
  "SSO免登短链 · 冒烟",
  "P0：Auth + ORDER_LIST。详情用环境 sso_orderId（默认 FT20260904BG5VM58）。休息室 SL 单会 603，不要用。",
  ["sso", "smoke"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_SSO)]),
    group("01 冒烟", [
      customHttp(next(), {
        name: "【ORDER_LIST】| SSO-SMOKE-LIST | POST /v2/sso/links",
        method: "post",
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: {
          subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 1800,
        },
        pre: RID,
        post: postSsoSuccess(),
      }),
      customHttp(next(), {
        name: "【ORDER_DETAIL】| SSO-SMOKE-DETAIL | POST /v2/sso/links",
        method: "post",
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: {
          subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
          scene: "ORDER_DETAIL",
          extra: { orderId: "{{sso_orderId}}" },
          language: "en-US",
          durationInSeconds: 1800,
        },
        pre: RID,
        post: postSsoSuccess(),
      }),
    ]),
  ],
  0
);
writeScenario("p0-sso.json", p0Sso);

const manifest = {
  projectId: PROJECT_ID,
  p1Parent: 350027,
  p0Others: 350026,
  files: [
    { file: "ft-01.json", feature: "FT可用性", folder: "01 过去时间拦截" },
    { file: "ft-02.json", feature: "FT可用性", folder: "02 错误码迁移039-044" },
    { file: "ft-03.json", feature: "FT可用性", folder: "03 补充错误码045" },
    { file: "ft-04.json", feature: "FT可用性", folder: "04 时区特殊与空时区" },
    { file: "pay-01.json", feature: "支付链接", folder: "01 语种language校验" },
    { file: "pay-02.json", feature: "支付链接", folder: "02 有效期durationInSeconds校验" },
    { file: "auth-02.json", feature: "Auth双密钥", folder: "02 两套token跑通链路" },
    { file: "auth-03.json", feature: "Auth双密钥", folder: "03 RS256与HS256判定组合" },
    { file: "auth-04.json", feature: "Auth双密钥", folder: "04 密钥配置增删改" },
    { file: "p0-ft.json", feature: "P0", folder: "others", p0: true },
    { file: "p0-pay.json", feature: "P0", folder: "others", p0: true },
    { file: "p0-sso.json", feature: "P0", folder: "others", p0: true },
  ],
};
fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
console.log("generated", manifest.files.length, "->", outDir);
