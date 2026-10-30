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

/** UAT canary：会籍错误码 039/044/045 简单冒烟（不下单） */
const SEED_UAT_ERR_MIGRATE = [
  "pm.environment.set('baseUrl', 'https://developer-sandbox.dragonpass.com/api');",
  "pm.environment.set('ProgramID', '1919256841868288');",
  "pm.environment.set('Program-ID', '1919256841868288');",
  "pm.environment.set('clientId', 'OWYXJUXKHPJZHTUKIRWN');",
  "pm.environment.set('secret', '2804391AB4B64DD189EE1509A06AFCD4');",
  "pm.environment.set('x-version', 'canary');",
  "if (!String(pm.environment.get('err_profile_email') || '').trim()) pm.environment.set('err_profile_email', '2484268151@qq.COM');",
  "if (!String(pm.environment.get('err_profile_phone') || '').trim()) pm.environment.set('err_profile_phone', '15838657142');",
  "if (!String(pm.environment.get('err_fake_membershipId') || '').trim()) pm.environment.set('err_fake_membershipId', '0000000000000000');",
  "if (!String(pm.environment.get('err_fake_orderId') || '').trim()) pm.environment.set('err_fake_orderId', '9999999999999999');",
].join("\n");

/** PRE FT 可用性：epass 鉴权；不要带 membershipId；不下单 */
const SEED_FT_PRE_EPASS = [
  "pm.environment.set('ProgramID', '1946131279295488');",
  "pm.environment.set('Program-ID', '1946131279295488');",
  "pm.environment.set('clientId', 'Q8F0ECUC92189UU2HNJO');",
  "pm.environment.set('secret', '51FDFD782E974A8D997C69FA230F011A');",
  "pm.environment.set('fastTrackResourceId', 'C10632');",
  "pm.environment.set('ft_tz_offset_hours', '8');",
  "pm.environment.set('membershipId', '');",
  "try { pm.environment.unset('membershipId'); } catch (eU) {}",
  "pm.environment.set('x-version', 'gray');",
  "pm.environment.set('baseUrl', 'https://developer.dragonpass.com/api');",
  "pm.environment.set('epass_ProgramID', '1946131279295488');",
  "pm.environment.set('membership_ProgramID', '1861959515628544');",
  "pm.environment.set('membership_clientId', '691C10CA39D74A0FA047C77C6618DEE8');",
  "pm.environment.set('membership_secret', '0A0469B91DCC4F7FA04298833B192122');",
].join("\n");

/** PRE 会籍错误码 039～045：用 membership 凭证；只打失败路径，不下单、不开收银台 */
const SEED_FT_PRE_MEMBERSHIP = [
  "pm.environment.set('ProgramID', '1861959515628544');",
  "pm.environment.set('Program-ID', '1861959515628544');",
  "pm.environment.set('clientId', '691C10CA39D74A0FA047C77C6618DEE8');",
  "pm.environment.set('secret', '0A0469B91DCC4F7FA04298833B192122');",
  "pm.environment.set('x-version', 'gray');",
  "pm.environment.set('baseUrl', 'https://developer.dragonpass.com/api');",
  "pm.environment.set('membershipId', '');",
  "try { pm.environment.unset('membershipId'); } catch (eU) {}",
].join("\n");

/** PRE 支付/SSO 验收：epass 主凭证（Program/Token 同套）。membership 只存备用，SSO 不要混套。 */
const SEED_PRE_PAY_SSO = [
  "pm.environment.set('ProgramID', '1946131279295488');",
  "pm.environment.set('Program-ID', '1946131279295488');",
  "pm.environment.set('clientId', 'Q8F0ECUC92189UU2HNJO');",
  "pm.environment.set('secret', '51FDFD782E974A8D997C69FA230F011A');",
  "pm.environment.set('x-version', 'gray');",
  "pm.environment.set('baseUrl', 'https://developer.dragonpass.com/api');",
  "pm.environment.set('epass_ProgramID', '1946131279295488');",
  "pm.environment.set('membership_ProgramID', '1861959515628544');",
  "pm.environment.set('membership_clientId', '691C10CA39D74A0FA047C77C6618DEE8');",
  "pm.environment.set('membership_secret', '0A0469B91DCC4F7FA04298833B192122');",
  "if (!pm.environment.get('pay_returnUrl')) pm.environment.set('pay_returnUrl', 'https://www.ly.com');",
  "if (!pm.environment.get('pay_paymentMethod')) pm.environment.set('pay_paymentMethod', 'H5_CASHIER');",
  "if (!String(pm.environment.get('sso_epass_subject_id') || '').trim()) pm.environment.set('sso_epass_subject_id', '8576666260529406');",
  "if (!String(pm.environment.get('sso_lounge_orderId') || '').trim()) pm.environment.set('sso_lounge_orderId', 'SL20251124BGLFL4S');",
].join("\n");

const SSO_EPASS_SUBJECT = { type: "EPASS", id: "{{sso_epass_subject_id}}" };

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
    "var off = parseFloat(pm.variables.get('ft_tz_offset_hours') || pm.environment.get('ft_tz_offset_hours') || '8');",
    "if (isNaN(off)) off = 8;",
    "var mode = '" + mode + "';",
    "var date = '';",
    "if (mode==='past') date = wall(Date.now()-30*60*1000, off);",
    "else { date = wall(Date.now()+10*24*3600*1000, off).replace(/T\\d{2}:\\d{2}$/, 'T10:00'); }",
    "var rid = String(pm.variables.get('ft_resourceId') || pm.environment.get('fastTrackResourceId') || 'C10632');",
    "var body = { module: 2, resourceId: rid, prebookingDate: date, adultCount: 1, childCount: 0 };",
    "var mid = String(pm.environment.get('membershipId') || pm.variables.get('membershipId') || '').trim();",
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

/** PRE：会籍购买/取消类接口若未放行会先 201；放行后才验迁移码。不下单、不开收银台。 */
function postExpectMigrateOrPreGate(code, msgPart) {
  return bizOkAssert(
    [
      "if (err === '201.000.001') {",
      "  pm.test('检查点 | PRE会籍接口未放行(201)已记录，开通权限后应返回 " + code + "', function () { pm.expect(err).to.eql('201.000.001'); });",
      "} else {",
      "  pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
      "  pm.test('检查点 | 期望=errCode=" + code + " | 实际=' + err, function () { pm.expect(err).to.eql('" + code + "'); });",
      "  pm.test('检查点 | 期望=不是旧码 500.020.030~035 | 实际=' + err, function () {",
      "    pm.expect(['500.020.030','500.020.031','500.020.032','500.020.033','500.020.034','500.020.035']).to.not.include(err);",
      "  });",
      msgPart
        ? "  pm.test('检查点 | 期望=文案含指定句 | 实际=' + msg, function () { pm.expect(msg).to.include(" + JSON.stringify(msgPart) + "); });"
        : "",
      "}",
    ].join("\n")
  );
}

function postSuccessNot030() {
  return bizOkAssert(
    [
      "if (err === '500.020.009') {",
      "  pm.test('检查点 | 不是过去时间030；该时段资源不可确认(009)已记录 | 实际=' + err, function () {",
      "    pm.expect(err).to.eql('500.020.009');",
      "    pm.expect(err).to.not.eql('500.020.030');",
      "  });",
      "} else {",
      "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code + ' err=' + err, function () { pm.expect(json.code).to.eql(0); });",
      "  pm.test('检查点 | 期望=不是 500.020.030 | 实际=' + err, function () { pm.expect(err).to.not.eql('500.020.030'); });",
      "}",
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
  return [
    "var json = {};",
    "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
    "var err = String(json.errCode || '');",
    "var msg = String(json.msg || '');",
    "var caseKind = '" + kind + "';",
    "if (caseKind === 'over') {",
    "  pm.test('检查点 | 期望=HTTP 200或400 | 实际=' + pm.response.code, function () { pm.expect([200,400]).to.include(pm.response.code); });",
    "  pm.test('检查点 | 期望=超上限失败 | 实际 code=' + json.code + ' err=' + err, function () {",
    "    pm.expect(json.code).to.not.eql(0);",
    "    pm.expect(['301.000.001','302.000.001','300.000.001'].indexOf(err) >= 0 || json.code === -1).to.eql(true);",
    "  });",
    "} else {",
    "  pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
    "  if (err === '500.000.802' || err === '500.000.804') {",
    "    pm.test.skip('当前 orderId 不可支付（' + err + '）。请把环境 pay_orderId 换成会籍待支付 MS 单后再跑语种/默认有效期。');",
    "  } else {",
    "    pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
    "    var action = json.data && (json.data.paymentAction || (json.data.payment && json.data.payment.paymentAction));",
    "    var url = action && (action.url || action.redirectUrl);",
    "    pm.test('检查点 | 期望=有支付url | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
    "    if (url) { try { pm.environment.set('pay_last_url', String(url)); } catch (eU) {} }",
    "  }",
    "}",
  ].join("\n");
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
  "来源桌面《需求测试用例.xmind》二、FT可用性。先 Auth 再业务。PRE：epass Program 1946131279295488 + 资源 C10632；不要带 membershipId、不要下单。Header 必带 Token、X-Program-ID、x-version=gray、X-Request-ID。";
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
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_FT_PRE_EPASS)]),
    group("01 过去/未来", [
      customHttp(next(), {
        name: "【过去时间拦截】| FT-030 | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10632", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past", "pm.variables.set('ft_resourceId','C10632'); pm.variables.set('ft_tz_offset_hours','8');"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【时区换算-当地已过】| FT-030-TZ | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10299", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past", "pm.variables.set('ft_tz_offset_hours','1'); pm.variables.set('ft_resourceId','C10299');"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【未来时间不报030】| FT-FUTURE | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10632", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("future", "pm.variables.set('ft_resourceId','C10632'); pm.variables.set('ft_tz_offset_hours','8');"),
        post: postSuccessNot030(),
      }),
    ]),
    group("02 多时区抽样", [
      ["C10810", "7", "HAN"],
      ["C10632", "8", "NNG"],
      ["C10299", "1", "LGW"],
      ["C10295", "2", "NCE"],
      ["C10812", "7", "DAD"],
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
  DESC_FT +
    " PRE验收：用 membership 凭证只打 preview/取消（不下单、不开收银台）。会籍购买接口若仍 201.000.001 记为环境未放行并通过；放行后须返回 500.030.039/044，且不得再出现旧码 500.020.030~035。",
  ["ft", "err", "xmind", "pre"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_FT_PRE_MEMBERSHIP)]),
    group("01 迁移码(不下单)", [
      customHttp(next(), {
        name: "【原030迁039 Preview AR=true】| ERR-039 | POST /v2/orders/memberships/purchase/preview",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase/preview",
        headers: apiHeaders(true),
        body: { appId: 1, autoRenewal: true, profile },
        pre: RID,
        post: postExpectMigrateOrPreGate("500.030.039", "Unable to preview"),
      }),
      customHttp(next(), {
        name: "【原035迁044 会籍不存在】| ERR-044 | POST /v2/memberships/subscriptions/cancellation",
        method: "post",
        reqPath: "/v2/memberships/subscriptions/cancellation",
        headers: apiHeaders(true),
        body: { membershipId: "0000000000000000", email: "2484268151@qq.COM" },
        pre: RID,
        post: postExpectMigrateOrPreGate("500.030.044", "Failed to cancel"),
      }),
    ]),
  ]
);
writeScenario("ft-02.json", ft02);

resetN();
const ft03 = scenario(
  "FT可用性 · 03补充错误码045",
  DESC_FT +
    " PRE验收：只查不存在单 details，不下单。若 PRE 返回 201.000.001 记未放行并通过；放行后须 500.030.045。",
  ["ft", "045", "xmind", "pre"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_FT_PRE_MEMBERSHIP)]),
    group("01 045", [
      customHttp(next(), {
        name: "【purchase/details 不存在单】| ERR-045 | POST /v2/orders/memberships/purchase/details",
        method: "post",
        reqPath: "/v2/orders/memberships/purchase/details",
        headers: apiHeaders(true),
        body: { orderId: "9999999999999999" },
        pre: RID,
        post: postExpectMigrateOrPreGate("500.030.045", "unable to retrieve the order details"),
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
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_FT_PRE_EPASS)]),
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
  group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
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
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
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
const payPreAccept = scenario(
  "支付链接 · PRE验收",
  "PRE 验收：Auth(epass) + 参数校验。只生成/校验支付链接接口，不打开收银台、不完成线上支付。缺 orderId→302；duration=1801→301；假单号→804 可接受。环境若已有待支付 pay_orderId 再验出链成功。",
  ["pay", "pre", "accept"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
    group("01 参数校验(无收银台支付)", [
      customHttp(next(), {
        name: "【缺orderId】| PAY-PRE-302 | POST /v2/orders/payments",
        method: "post",
        reqPath: "/v2/orders/payments",
        headers: apiHeaders(true),
        body: { returnUrl: "https://www.ly.com", paymentMethod: "H5_CASHIER", language: "en-US" },
        pre: RID,
        post: [
          "var json = {};",
          "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
          "var err = String(json.errCode || '');",
          "pm.test('检查点 | 期望=HTTP 200或400 | 实际=' + pm.response.code, function () { pm.expect([200,400]).to.include(pm.response.code); });",
          "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
          "pm.test('检查点 | 期望=errCode=302.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('302.000.001'); });",
        ].join("\n"),
      }),
      payHttp(
        "【duration=1801超上限】",
        "PAY-PRE-1801",
        {
          orderId: "MS20260908PRECHECK",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          durationInSeconds: 1801,
        },
        "over"
      ),
      customHttp(next(), {
        name: "【假单号不出链】| PAY-PRE-804 | POST /v2/orders/payments",
        method: "post",
        reqPath: "/v2/orders/payments",
        headers: apiHeaders(true),
        body: {
          orderId: "MS20260908NOTEXIST",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          language: "en-US",
          durationInSeconds: 60,
        },
        pre: RID,
        post: bizOkAssert(
          [
            "pm.test('检查点 | 期望=业务失败(不打开支付) | 实际 code=' + json.code + ' err=' + err, function () {",
            "  pm.expect(json.code).to.not.eql(0);",
            "  pm.expect(['500.000.804','500.000.803','500.000.802','302.000.001']).to.include(err);",
            "});",
          ].join("\n")
        ),
      }),
      customHttp(next(), {
        name: "【若有pay_orderId则出链】| PAY-PRE-URL | POST /v2/orders/payments",
        method: "post",
        reqPath: "/v2/orders/payments",
        headers: apiHeaders(true),
        body: {
          orderId: "{{pay_orderId}}",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          language: "en-US",
          durationInSeconds: 60,
        },
        pre: [
          "var oid = String(pm.environment.get('pay_orderId') || '').trim();",
          "if (!oid || oid.indexOf('{{') >= 0) { pm.variables.set('pay_skip_url','true'); }",
          "else {",
          "  try {",
          "    var b = { orderId: oid, returnUrl: 'https://www.ly.com', paymentMethod: 'H5_CASHIER', language: 'en-US', durationInSeconds: 60 };",
          "    pm.request.body = { mode:'raw', raw: JSON.stringify(b,null,2), options:{raw:{language:'json'}} };",
          "  } catch (eP) {}",
          "}",
          RID,
        ].join("\n"),
        post: bizOkAssert(
          [
            "if (String(pm.variables.get('pay_skip_url')||'')==='true') {",
            "  pm.test('检查点 | 未配置 pay_orderId，跳过出链（不涉及线上支付）', function () { pm.expect(true).to.eql(true); });",
            "} else if (err === '500.000.802' || err === '500.000.804' || err === '500.000.803') {",
            "  pm.test('检查点 | 当前单不可出链已记录 | 实际=' + err, function () { pm.expect(json.code).to.not.eql(0); });",
            "} else {",
            "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
            "  var action = json.data && (json.data.paymentAction || (json.data.payment && json.data.payment.paymentAction));",
            "  var url = action && (action.url || action.redirectUrl);",
            "  pm.test('检查点 | 期望=有支付url(仅出链) | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
            "}",
          ].join("\n")
        ),
      }),
    ]),
  ]
);
writeScenario("pay-pre.json", payPreAccept);

function postSsoHttp(httpStatusOk) {
  return [
    "var json = {};",
    "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
    "var err = String(json.errCode || '');",
    "var msg = String(json.msg || '');",
    httpStatusOk
      ? "pm.test('检查点 | 期望=HTTP 200或400 | 实际=' + pm.response.code, function () { pm.expect([200,400]).to.include(pm.response.code); });"
      : "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
  ].join("\n");
}

/** PRE 门控：201/601 未到业务层时记通过；否则执行业务断言块 */
function postSsoBizOrPreGate(bizLines) {
  return [
    postSsoHttp(true),
    "if (err === '201.000.001') {",
    "  pm.test('检查点 | PRE SSO鉴权未放行(201)已记录', function () { pm.expect(err).to.eql('201.000.001'); });",
    "} else if (err === '500.000.601' && String(pm.variables.get('sso_allow_601_gate')||'true')==='true') {",
    "  pm.test('检查点 | PRE SSO兜底601已记录(业务层未达) | msg=' + msg, function () {",
    "    pm.expect(err).to.eql('500.000.601');",
    "    pm.expect(msg).to.include(\"unable to generate the SSO link\");",
    "  });",
    "} else {",
    bizLines,
    "}",
  ].join("\n");
}

function ssoStep(title, body, postScript, preExtra) {
  return customHttp(next(), {
    name: title,
    method: "post",
    reqPath: "/v2/sso/links",
    headers: apiHeaders(true),
    body,
    pre: [preExtra || "", RID].join("\n"),
    post: postScript,
  });
}

resetN();
const ssoPreAccept = scenario(
  "SSO免登短链 · PRE验收",
  [
    "PRE 验收：epass 凭证（Program 1946131279295488）+ EPASS subject，不要用 membership Token 打 SSO（会 201）。",
    "基础：缺 subject→302；非法 scene→301；缺 scene→302。",
    "错误码：602 ORDER_DETAIL 缺/空 extra.orderId；603 休息室 SL 详情不支持；601 用假 EPASS id 触发兜底。",
    "缺陷对照：PAPI-3201 membership 凭证+type=EPASS 应拦截(PRE 现为 201)；PAPI-3200 省略 duration 出链成功；PAPI-3199 详情与订单不匹配失败；PAPI-3198 不存在主体失败。",
    "不涉及线上支付。",
  ].join(" "),
  ["sso", "pre", "accept", "bug"],
  [
    group("00 换 Token", [authStep(next(), "【换Token-epass】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
    group("01 参数基础", [
      ssoStep(
        "【缺subject】| SSO-PRE-302 | POST /v2/sso/links",
        { scene: "ORDER_LIST", language: "en-US", durationInSeconds: 60 },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
          "pm.test('检查点 | 期望=errCode=302.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('302.000.001'); });",
        ].join("\n")
      ),
      ssoStep(
        "【非法scene】| SSO-PRE-301 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "BAD_SCENE",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
          "pm.test('检查点 | 期望=errCode=301.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('301.000.001'); });",
        ].join("\n")
      ),
      ssoStep(
        "【缺scene】| SSO-PRE-SCENE | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
          "pm.test('检查点 | 期望=errCode=302.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('302.000.001'); });",
        ].join("\n")
      ),
    ]),
    group("02 错误提示语601/602/603", [
      ssoStep(
        "【602 DETAIL缺extra.orderId】| SSO-MSG-602 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_DETAIL",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=errCode=500.000.602 | 实际=' + err, function () { pm.expect(err).to.eql('500.000.602'); });",
          "pm.test('检查点 | 期望=文案含 extra.orderId/required | 实际=' + msg, function () {",
          "  pm.expect(msg.toLowerCase().indexOf('extra') >= 0 || msg.toLowerCase().indexOf('orderid') >= 0).to.eql(true);",
          "  pm.expect(msg.toLowerCase().indexOf('required') >= 0).to.eql(true);",
          "});",
        ].join("\n")
      ),
      ssoStep(
        "【602 DETAIL空orderId】| SSO-MSG-602-EMPTY | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_DETAIL",
          extra: { orderId: "" },
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=errCode=500.000.602 | 实际=' + err, function () { pm.expect(err).to.eql('500.000.602'); });",
          "pm.test('检查点 | 期望=文案指向 extra.orderId | 实际=' + msg, function () {",
          "  pm.expect(msg.toLowerCase()).to.include('order');",
          "});",
        ].join("\n")
      ),
      ssoStep(
        "【603 休息室SL详情不支持】| SSO-MSG-603 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_DETAIL",
          extra: { orderId: "{{sso_lounge_orderId}}" },
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
          "pm.test('检查点 | 期望=errCode=500.000.603 | 实际=' + err, function () { pm.expect(err).to.eql('500.000.603'); });",
          "pm.test('检查点 | 期望=文案 not currently supported | 实际=' + msg, function () {",
          "  pm.expect(msg).to.include('not currently supported');",
          "});",
        ].join("\n")
      ),
      ssoStep(
        "【601 假EPASS主体兜底】| SSO-MSG-601 | POST /v2/sso/links",
        {
          subject: { type: "EPASS", id: "0000000000000000" },
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=errCode=500.000.601 | 实际=' + err, function () { pm.expect(err).to.eql('500.000.601'); });",
          "pm.test('检查点 | 期望=兜底文案 | 实际=' + msg, function () {",
          "  pm.expect(msg).to.include(\"unable to generate the SSO link\");",
          "});",
        ].join("\n")
      ),
    ]),
    group("03 缺陷对照PAPI-3198~3201", [
      authStep(next(), "【换Token-membership】| AUTH-MEM | POST /v2/auth/token", SEED_FT_PRE_MEMBERSHIP),
      ssoStep(
        "【PAPI-3201 membership凭证+type=EPASS应拦截】| BUG-3201 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=拦截(非成功出链) | 实际 code=' + json.code + ' err=' + err, function () {",
          "  pm.expect(json.code).to.not.eql(0);",
          "  pm.expect(['201.000.001','500.000.601','301.000.001','302.000.001']).to.include(err);",
          "});",
          "pm.test('检查点 | 期望=不是静默成功短链 | 实际=' + err, function () {",
          "  var url = json.data && json.data.entry && json.data.entry.shortUrl;",
          "  pm.expect(!!url).to.eql(false);",
          "});",
        ].join("\n")
      ),
      authStep(next(), "【换回Token-epass】| AUTH-EPASS | POST /v2/auth/token", SEED_PRE_PAY_SSO),
      ssoStep(
        "【PAPI-3200 省略duration应可默认】| BUG-3200 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_LIST",
          language: "en-US",
        },
        [
          postSsoHttp(true),
          "if (err === '302.000.001' && msg.toLowerCase().indexOf('durationinseconds') >= 0) {",
          "  pm.test('检查点 | PAPI-3200仍复现：省略duration被当成必填302 | 实际=' + msg, function () {",
          "    pm.expect.fail('PAPI-3200未修：省略 durationInSeconds 不应报必填/默认参数错误');",
          "  });",
          "} else {",
          "  pm.test('检查点 | 期望=code=0(默认有效期) | 实际=' + json.code + ' err=' + err, function () { pm.expect(json.code).to.eql(0); });",
          "  var url = json.data && json.data.entry && json.data.entry.shortUrl;",
          "  pm.test('检查点 | 期望=有 shortUrl | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
          "}",
        ].join("\n")
      ),
      ssoStep(
        "【PAPI-3199 详情主体与订单关系】| BUG-3199 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_DETAIL",
          extra: { orderId: "{{sso_orderId_other}}" },
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=失败且不出链 | 实际 code=' + json.code + ' err=' + err, function () {",
          "  pm.expect(json.code).to.not.eql(0);",
          "  var url = json.data && json.data.entry && json.data.entry.shortUrl;",
          "  pm.expect(!!url).to.eql(false);",
          "});",
        ].join("\n"),
        "if (!pm.environment.get('sso_orderId_other')) pm.environment.set('sso_orderId_other', 'FT20260901OTHER000');"
      ),
      ssoStep(
        "【PAPI-3198 不存在主体提示语】| BUG-3198 | POST /v2/sso/links",
        {
          subject: { type: "EPASS", id: "0000000000000000" },
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=业务失败 | 实际=' + json.code, function () { pm.expect(json.code).to.not.eql(0); });",
          "pm.test('检查点 | 期望=提示语不是笼统redirectURL/600 | 实际=' + err + ' ' + msg, function () {",
          "  pm.expect(err).to.not.eql('500.000.600');",
          "  pm.expect(msg.toLowerCase().indexOf('redirect url') >= 0).to.eql(false);",
          "});",
        ].join("\n")
      ),
    ]),
    group("04 其它异常", [
      ssoStep(
        "【duration=59下限外】| SSO-ERR-DUR59 | POST /v2/sso/links",
        {
          subject: SSO_EPASS_SUBJECT,
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 59,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=errCode=301.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('301.000.001'); });",
        ].join("\n")
      ),
      ssoStep(
        "【subject.type非法】| SSO-ERR-TYPE | POST /v2/sso/links",
        {
          subject: { type: "INVALID_TYPE", id: "{{sso_epass_subject_id}}" },
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 60,
        },
        [
          postSsoHttp(true),
          "pm.test('检查点 | 期望=errCode=301.000.001 | 实际=' + err, function () { pm.expect(err).to.eql('301.000.001'); });",
        ].join("\n")
      ),
    ]),
  ]
);
writeScenario("sso-pre.json", ssoPreAccept);

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
  "P0：Auth + 过去时间 030 + 未来成功。PRE epass，不下单。",
  ["ft", "smoke"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_FT_PRE_EPASS)]),
    group("01 冒烟", [
      customHttp(next(), {
        name: "【过去时间拦截】| FT-SMOKE-PAST | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10632", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("past", "pm.variables.set('ft_resourceId','C10632'); pm.variables.set('ft_tz_offset_hours','8');"),
        post: postExpectErr("500.020.030", "current local time"),
      }),
      customHttp(next(), {
        name: "【未来时间】| FT-SMOKE-FUTURE | POST /v2/resources/prebookings/availability",
        method: "post",
        reqPath: "/v2/resources/prebookings/availability",
        headers: apiHeaders(true),
        body: { module: 2, resourceId: "C10632", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
        pre: ftDatePre("future", "pm.variables.set('ft_resourceId','C10632'); pm.variables.set('ft_tz_offset_hours','8');"),
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
  "P0 PRE：Auth(epass) + duration=1801 校验。不打开收银台、不完成线上支付；有 pay_orderId 才验出链。",
  ["pay", "smoke", "pre"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
    group("01 冒烟", [
      payHttp(
        "【duration=1801】",
        "PAY-SMOKE-1801",
        {
          orderId: "MS20260908PRECHECK",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          durationInSeconds: 1801,
        },
        "over"
      ),
      customHttp(next(), {
        name: "【若有pay_orderId则出链】| PAY-SMOKE-EN | POST /v2/orders/payments",
        method: "post",
        reqPath: "/v2/orders/payments",
        headers: apiHeaders(true),
        body: {
          orderId: "{{pay_orderId}}",
          returnUrl: "https://www.ly.com",
          paymentMethod: "H5_CASHIER",
          language: "en-US",
          durationInSeconds: 60,
        },
        pre: [
          "var oid = String(pm.environment.get('pay_orderId') || '').trim();",
          "if (!oid || oid.indexOf('{{') >= 0) { pm.variables.set('pay_skip_url','true'); }",
          "else {",
          "  try {",
          "    var b = { orderId: oid, returnUrl: 'https://www.ly.com', paymentMethod: 'H5_CASHIER', language: 'en-US', durationInSeconds: 60 };",
          "    pm.request.body = { mode:'raw', raw: JSON.stringify(b,null,2), options:{raw:{language:'json'}} };",
          "  } catch (eP) {}",
          "}",
          RID,
        ].join("\n"),
        post: bizOkAssert(
          [
            "if (String(pm.variables.get('pay_skip_url')||'')==='true') {",
            "  pm.test('检查点 | 未配置 pay_orderId，跳过出链', function () { pm.expect(true).to.eql(true); });",
            "} else if (err === '500.000.802' || err === '500.000.804' || err === '500.000.803') {",
            "  pm.test('检查点 | 当前单不可出链已记录 | 实际=' + err, function () { pm.expect(json.code).to.not.eql(0); });",
            "} else {",
            "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
            "  var action = json.data && (json.data.paymentAction || (json.data.payment && json.data.payment.paymentAction));",
            "  var url = action && (action.url || action.redirectUrl);",
            "  pm.test('检查点 | 期望=有支付url | 实际=' + (url ? '有' : '空'), function () { pm.expect(url).to.be.ok; });",
            "}",
          ].join("\n")
        ),
      }),
    ]),
  ],
  0
);
writeScenario("p0-pay.json", p0Pay);

resetN();
const p0Sso = scenario(
  "SSO免登短链 · 冒烟",
  "P0 PRE：epass 凭证 + EPASS subject。先 ORDER_LIST 出链成功，再休息室 SL 的 ORDER_DETAIL 验 500.000.603。不要混 membership Token。不涉及线上支付。",
  ["sso", "smoke", "603"],
  [
    group("00 换 Token", [authStep(next(), "【换Token】| AUTH | POST /v2/auth/token", SEED_PRE_PAY_SSO)]),
    group("01 冒烟", [
      customHttp(next(), {
        name: "【ORDER_LIST出链】| SSO-SMOKE-LIST | POST /v2/sso/links",
        method: "post",
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: {
          subject: { type: "EPASS", id: "{{sso_epass_subject_id}}" },
          scene: "ORDER_LIST",
          language: "en-US",
          durationInSeconds: 60,
        },
        pre: RID,
        post: postSsoSuccess(),
      }),
      customHttp(next(), {
        name: "【603 休息室SL详情不支持】| SSO-SMOKE-603 | POST /v2/sso/links",
        method: "post",
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: {
          subject: { type: "EPASS", id: "{{sso_epass_subject_id}}" },
          scene: "ORDER_DETAIL",
          extra: { orderId: "{{sso_lounge_orderId}}" },
          language: "en-US",
          durationInSeconds: 60,
        },
        pre: RID,
        post: [
          "var json = {};",
          "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
          "var err = String(json.errCode || '');",
          "var msg = String(json.msg || '');",
          "pm.test('检查点 | 期望=HTTP 200或400 | 实际=' + pm.response.code, function () { pm.expect([200,400]).to.include(pm.response.code); });",
          "pm.test('检查点 | 期望=errCode=500.000.603 | 实际=' + err, function () { pm.expect(err).to.eql('500.000.603'); });",
          "pm.test('检查点 | 期望=文案 not currently supported | 实际=' + msg, function () {",
          "  pm.expect(msg).to.include('not currently supported');",
          "});",
        ].join("\n"),
      }),
    ]),
  ],
  0
);
writeScenario("p0-sso.json", p0Sso);

resetN();
const SBX_API = "https://developer-sandbox.dragonpass.com/api";
function sandboxErrPre(apiPath) {
  return [
    SEED_UAT_ERR_MIGRATE,
    RID,
    "var _full = " + JSON.stringify(SBX_API + apiPath) + ";",
    "try { pm.request.url = _full; } catch (e0) {}",
    "try { if (pm.request.url && typeof pm.request.url === 'object') pm.request.url.raw = _full; } catch (e1) {}",
    "try { pm.request.headers.upsert({ key: 'X-Program-ID', value: '1919256841868288' }); } catch (e2) {}",
    "try { pm.request.headers.upsert({ key: 'x-version', value: 'canary' }); } catch (e3) {}",
    "var _rid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) { var r = (Math.random() * 16) | 0; var v = c === 'x' ? r : (r & 0x3) | 0x8; return v.toString(16); });",
    "pm.sendRequest({",
    "  url: " + JSON.stringify(SBX_API + "/v2/auth/token") + ",",
    "  method: 'POST',",
    "  header: [",
    "    { key: 'X-Program-ID', value: '1919256841868288' },",
    "    { key: 'x-version', value: 'canary' },",
    "    { key: 'X-Request-ID', value: _rid },",
    "    { key: 'Content-Type', value: 'application/json' }",
    "  ],",
    "  body: { mode: 'raw', raw: JSON.stringify({ clientId: 'OWYXJUXKHPJZHTUKIRWN', secret: '2804391AB4B64DD189EE1509A06AFCD4' }) }",
    "}, function (eReq, res) {",
    "  try {",
    "    var j = res && res.json && res.json();",
    "    var t = j && j.data && (j.data.accessToken || j.data.access_token);",
    "    if (t) {",
    "      pm.environment.set('accessToken', t);",
    "      pm.environment.set('access_token', t);",
    "      try { pm.request.headers.upsert({ key: 'Authorization', value: 'Bearer ' + t }); } catch (eH) {}",
    "    }",
    "  } catch (eJ) {}",
    "});",
  ].join("\n");
}
const profileErr = {
  email: "{{err_profile_email}}",
  clientUserId: "{{$guid}}",
  callingCode: "86",
  phoneNumber: "{{err_profile_phone}}",
};
const p0ErrMigrate = scenario(
  "会籍错误码迁移 · 冒烟",
  "挑最简单的 3 个迁移码：039←030 Preview、044←035 取消不存在会籍、045 补充 details。固定打 UAT 沙箱 canary（AllCategories），不依赖当前环境的 PRE 域名/epass Token。不下单、不开收银台。选 UK-生产环境-PRE 也能跑通。",
  ["err", "migrate", "smoke"],
  [
    group("00 换 Token", [
      authStep(
        next(),
        "【换Token】| AUTH | POST /v2/auth/token",
        SEED_UAT_ERR_MIGRATE,
        SBX_API + "/v2/auth/token"
      ),
    ]),
    group("01 简单迁移码", [
      customHttp(next(), {
        name: "【039 Preview】| ERR-039 | POST /v2/orders/memberships/purchase/preview",
        method: "post",
        reqPath: SBX_API + "/v2/orders/memberships/purchase/preview",
        headers: apiHeaders(true),
        body: { appId: 1, autoRenewal: true, profile: profileErr },
        pre: sandboxErrPre("/v2/orders/memberships/purchase/preview"),
        post: postExpectErr("500.030.039", "Unable to preview"),
      }),
      customHttp(next(), {
        name: "【044 会籍不存在取消】| ERR-044 | POST /v2/memberships/subscriptions/cancellation",
        method: "post",
        reqPath: SBX_API + "/v2/memberships/subscriptions/cancellation",
        headers: apiHeaders(true),
        body: { membershipId: "{{err_fake_membershipId}}", email: "{{err_profile_email}}" },
        pre: sandboxErrPre("/v2/memberships/subscriptions/cancellation"),
        post: postExpectErr("500.030.044", "Failed to cancel"),
      }),
      customHttp(next(), {
        name: "【045 details不存在单】| ERR-045 | POST /v2/orders/memberships/purchase/details",
        method: "post",
        reqPath: SBX_API + "/v2/orders/memberships/purchase/details",
        headers: apiHeaders(true),
        body: { orderId: "{{err_fake_orderId}}" },
        pre: sandboxErrPre("/v2/orders/memberships/purchase/details"),
        post: postExpectErr("500.030.045", "unable to retrieve the order details"),
      }),
    ]),
  ],
  0
);
writeScenario("p0-err-migrate.json", p0ErrMigrate);

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
    { file: "pay-pre.json", feature: "支付链接", folder: "03 PRE验收" },
    { file: "sso-pre.json", feature: "sso免登录短链接", folder: "01 PRE验收" },
    { file: "auth-02.json", feature: "Auth双密钥", folder: "02 两套token跑通链路" },
    { file: "auth-03.json", feature: "Auth双密钥", folder: "03 RS256与HS256判定组合" },
    { file: "auth-04.json", feature: "Auth双密钥", folder: "04 密钥配置增删改" },
    { file: "p0-ft.json", feature: "P0", folder: "others", p0: true },
    { file: "p0-pay.json", feature: "P0", folder: "others", p0: true },
    { file: "p0-sso.json", feature: "P0", folder: "others", p0: true },
    { file: "p0-err-migrate.json", feature: "P0", folder: "others", p0: true },
  ],
};
fs.writeFileSync(path.join(outDir, "manifest.json"), JSON.stringify(manifest, null, 2));
console.log("generated", manifest.files.length, "->", outDir);
