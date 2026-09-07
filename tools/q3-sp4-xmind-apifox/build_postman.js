/**
 * 生成 Q3-SP4 四需求 Postman Collection v2.1（也可直接导入 Apifox）。
 * 用法: node build_postman.js
 */
const fs = require("fs");
const path = require("path");

const payLangs = JSON.parse(fs.readFileSync(path.join(__dirname, "pay_languages_xmind.json"), "utf8"));
const ssoLangs = JSON.parse(
  fs.readFileSync(path.join(__dirname, "../sso-links-q3-sp4/sso_languages_list.json"), "utf8")
);

const RID = [
  "try {",
  "  var _rid = (typeof pm !== 'undefined' && pm.variables && pm.variables.replaceIn) ? String(pm.variables.replaceIn('{{$guid}}')||'') : '';",
  "  if (!_rid || _rid.indexOf('{{')>=0) {",
  "    _rid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c){ var r=(Math.random()*16)|0; return (c==='x'?r:(r&0x3)|0x8).toString(16); });",
  "  }",
  "  if (pm.request && pm.request.headers && pm.request.headers.upsert) {",
  "    pm.request.headers.upsert({ key: 'X-Request-ID', value: _rid });",
  "    pm.request.headers.upsert({ key: 'Accept', value: '*/*' });",
  "  }",
  "} catch (eRid) {}",
].join("\n");

const SEED_SSO = [
  "if (!String(pm.environment.get('ProgramID') || pm.environment.get('Program-ID') || pm.collectionVariables.get('ProgramID') || '')) {",
  "  pm.environment.set('ProgramID', '1919256841868288');",
  "}",
  "pm.environment.set('Program-ID', String(pm.environment.get('ProgramID') || '1919256841868288'));",
  "if (!pm.environment.get('x-version')) pm.environment.set('x-version', 'canary');",
  "if (!String(pm.environment.get('clientId') || pm.collectionVariables.get('clientId') || '')) {",
  "  pm.environment.set('clientId', pm.collectionVariables.get('clientId') || '');",
  "}",
  "if (!pm.environment.get('sso_subject_id')) pm.environment.set('sso_subject_id', '8576507744260001');",
  "if (!pm.environment.get('sso_orderId')) pm.environment.set('sso_orderId', 'FT20260904BG5VM58');",
  "if (!pm.environment.get('fastTrackResourceId')) pm.environment.set('fastTrackResourceId', 'C10826');",
  "if (!pm.environment.get('ft_tz_offset_hours')) pm.environment.set('ft_tz_offset_hours', '7');",
  "if (!pm.environment.get('membershipId')) pm.environment.set('membershipId', '8576507744260001');",
  "if (!pm.environment.get('pay_returnUrl')) pm.environment.set('pay_returnUrl', 'https://www.ly.com');",
  "if (!pm.environment.get('pay_paymentMethod')) pm.environment.set('pay_paymentMethod', 'H5_CASHIER');",
].join("\n");

function ev(listen, lines) {
  return {
    listen,
    script: { type: "text/javascript", exec: String(lines).split(/\n/) },
  };
}

function hdrs(withAuth) {
  const h = [
    { key: "X-Program-ID", value: "{{ProgramID}}" },
    { key: "x-version", value: "{{x-version}}" },
    { key: "X-Request-ID", value: "{{$guid}}" },
    { key: "Content-Type", value: "application/json" },
    { key: "Accept", value: "*/*" },
  ];
  if (withAuth) h.unshift({ key: "Authorization", value: "Bearer {{accessToken}}" });
  return h;
}

function url(p) {
  const segs = String(p).replace(/^\//, "").split("/");
  return {
    raw: "{{baseUrl}}" + (p.indexOf("/") === 0 ? p : "/" + p),
    host: ["{{baseUrl}}"],
    path: segs,
  };
}

function item(name, { reqPath, body, withAuth, pre, post, extraPre }) {
  const events = [];
  const preLines = [extraPre || "", pre || "", RID].filter(Boolean).join("\n");
  events.push(ev("prerequest", preLines));
  events.push(ev("test", post || defaultPost()));
  return {
    name,
    event: events,
    request: {
      method: "POST",
      header: hdrs(withAuth !== false),
      body: {
        mode: "raw",
        raw: typeof body === "string" ? body : JSON.stringify(body, null, 2),
        options: { raw: { language: "json" } },
      },
      url: url(reqPath),
    },
  };
}

function defaultPost() {
  return [
    "var json = {};",
    "try { json = pm.response.json(); } catch (e) { json = {}; }",
    "var err = String(json.errCode || '');",
    "pm.test('检查点 | 期望=HTTP可达 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.be.oneOf([200,400,401,403]); });",
    "console.log('[case] code=' + json.code + ' err=' + err + ' msg=' + json.msg);",
  ].join("\n");
}

function postOk() {
  return [
    "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
    "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
    "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
  ].join("\n");
}

function postErr(code, msgPart) {
  return [
    "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
    "var err = String(json.errCode || '');",
    "var msg = String(json.msg || '');",
    "pm.test('检查点 | 期望=code=-1 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(-1); });",
    "pm.test('检查点 | 期望=errCode=" + code + " | 实际=' + err, function () { pm.expect(err).to.eql('" + code + "'); });",
    msgPart
      ? "pm.test('检查点 | 期望=文案含指定句 | 实际=' + msg, function () { pm.expect(msg).to.include(" + JSON.stringify(msgPart) + "); });"
      : "",
  ].join("\n");
}

function postAuth() {
  return [
    "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
    "var token = (json.data && (json.data.accessToken || json.data.access_token)) || '';",
    "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
    "pm.test('检查点 | 期望=有 accessToken | 实际=' + (token?'有':'空'), function () { pm.expect(token).to.be.ok; });",
    "if (token) { pm.environment.set('accessToken', token); pm.environment.set('access_token', token); pm.collectionVariables.set('accessToken', token); }",
  ].join("\n");
}

function postSso() {
  return [
    postOk(),
    "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
    "var url = json.data && json.data.entry && json.data.entry.shortUrl;",
    "pm.test('检查点 | 期望=有 shortUrl | 实际=' + (url?'有':'空'), function () { pm.expect(url).to.be.ok; });",
    "if (url) pm.environment.set('sso_last_shortUrl', String(url));",
  ].join("\n");
}

function postPay(kind) {
  return [
    "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
    "var err = String(json.errCode || '');",
    "var kind = '" + (kind || "ok") + "';",
    "if (kind === 'over') {",
    "  pm.test('检查点 | 期望=超上限失败 | 实际=' + json.code + ' ' + err, function () { pm.expect(json.code).to.not.eql(0); });",
    "} else if (err === '500.000.802' || err === '500.000.804') {",
    "  pm.test.skip('当前 pay_orderId 不可支付（' + err + '）。请换成会籍待支付 MS 单');",
    "} else {",
    "  pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
    "  var action = json.data && (json.data.paymentAction || (json.data.payment && json.data.payment.paymentAction));",
    "  var u = action && (action.url || action.redirectUrl);",
    "  pm.test('检查点 | 期望=有支付url | 实际=' + (u?'有':'空'), function () { pm.expect(u).to.be.ok; });",
    "  if (u) pm.environment.set('pay_last_url', String(u));",
    "}",
  ].join("\n");
}

function ftPre(mode, extra) {
  return [
    extra || "",
    "function pad(n){return n<10?'0'+n:String(n);}",
    "function wall(ms,off){ var d=new Date(ms+off*3600*1000); return d.getUTCFullYear()+'-'+pad(d.getUTCMonth()+1)+'-'+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+':'+pad(d.getUTCMinutes()); }",
    "var off = parseFloat(pm.variables.get('ft_tz_offset_hours') || pm.environment.get('ft_tz_offset_hours') || '7');",
    "if (isNaN(off)) off = 7;",
    "var date = '" + mode + "'==='past' ? wall(Date.now()-30*60*1000, off) : wall(Date.now()+10*24*3600*1000, off).replace(/T\\d{2}:\\d{2}$/, 'T10:00');",
    "var rid = String(pm.variables.get('ft_resourceId') || pm.environment.get('fastTrackResourceId') || 'C10826');",
    "var body = { module: 2, resourceId: rid, prebookingDate: date, adultCount: 1, childCount: 0 };",
    "var mid = String(pm.environment.get('membershipId') || '');",
    "if (mid) body.membershipId = mid;",
    "pm.request.body = { mode: 'raw', raw: JSON.stringify(body, null, 2), options: { raw: { language: 'json' } } };",
  ].join("\n");
}

function authItem(title, extraPre) {
  return item(title, {
    reqPath: "/v2/auth/token",
    withAuth: false,
    body: { clientId: "{{clientId}}", secret: "{{secret}}" },
    extraPre: [SEED_SSO, extraPre || ""].join("\n"),
    post: postAuth(),
  });
}

function folder(name, items) {
  return { name, item: items };
}

const profile = {
  email: "2484268151@qq.COM",
  clientUserId: "{{$guid}}",
  callingCode: "86",
  phoneNumber: "15838657142",
};

const ssoListBody = {
  subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
  scene: "ORDER_LIST",
  language: "en-US",
  durationInSeconds: 1800,
};
const ssoDetailBody = {
  subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
  scene: "ORDER_DETAIL",
  extra: { orderId: "{{sso_orderId}}" },
  language: "en-US",
  durationInSeconds: 1800,
};

const collection = {
  info: {
    _postman_id: "q3-sp4-xmind-accept-20260904",
    name: "Q3-SP4 四需求验收（按XMind）",
    description:
      "来源桌面《需求测试用例.xmind》。目录：P0 冒烟 / P1 全量 / 功能名 / 按XMind用例。\n" +
      "导入后选环境「Q3-SP4 四需求验收」。每条场景先跑 00换Token。\n" +
      "SSO/FT 用 AllCategories Program；支付成功需会籍待支付 MS 单写入 pay_orderId；双密钥填 auth1_*/auth2_*。\n" +
      "Header 必带 Token、X-Program-ID、x-version=canary、X-Request-ID。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
  },
  variable: [
    { key: "baseUrl", value: "https://developer-sandbox.dragonpass.com/api" },
    { key: "x-version", value: "canary" },
    { key: "ProgramID", value: "1919256841868288" },
    { key: "clientId", value: "" },
    { key: "secret", value: "" },
    { key: "sso_subject_id", value: "8576507744260001" },
    { key: "sso_orderId", value: "FT20260904BG5VM58" },
    { key: "fastTrackResourceId", value: "C10826" },
    { key: "membershipId", value: "8576507744260001" },
    { key: "pay_orderId", value: "" },
    { key: "pay_returnUrl", value: "https://www.ly.com" },
    { key: "pay_paymentMethod", value: "H5_CASHIER" },
  ],
  item: [
    folder("P0 (冒烟用例)", [
      folder("SSO免登短链 · 冒烟", [
        authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
        item("【ORDER_LIST】| SSO-SMOKE-LIST | POST /v2/sso/links", {
          reqPath: "/v2/sso/links",
          body: ssoListBody,
          post: postSso(),
        }),
        item("【ORDER_DETAIL】| SSO-SMOKE-DETAIL | POST /v2/sso/links", {
          reqPath: "/v2/sso/links",
          body: ssoDetailBody,
          post: postSso(),
        }),
      ]),
      folder("FT可用性 · 冒烟", [
        authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
        item("【过去时间拦截】| FT-SMOKE-PAST | POST /v2/resources/prebookings/availability", {
          reqPath: "/v2/resources/prebookings/availability",
          body: { module: 2, resourceId: "{{fastTrackResourceId}}", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
          extraPre: ftPre("past"),
          post: postErr("500.020.030", "current local time"),
        }),
        item("【未来时间】| FT-SMOKE-FUTURE | POST /v2/resources/prebookings/availability", {
          reqPath: "/v2/resources/prebookings/availability",
          body: { module: 2, resourceId: "{{fastTrackResourceId}}", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
          extraPre: ftPre("future"),
          post: [
            postOk(),
            "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
            "pm.test('检查点 | 期望=不是 500.020.030 | 实际=' + json.errCode, function () { pm.expect(String(json.errCode||'')).to.not.eql('500.020.030'); });",
          ].join("\n"),
        }),
      ]),
      folder("支付链接 · 冒烟", [
        authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
        item("【duration=1801超上限】| PAY-SMOKE-1801 | POST /v2/orders/payments", {
          reqPath: "/v2/orders/payments",
          body: {
            orderId: "{{pay_orderId}}",
            returnUrl: "https://www.ly.com",
            paymentMethod: "H5_CASHIER",
            durationInSeconds: 1801,
          },
          extraPre:
            "if (!String(pm.environment.get('pay_orderId')||pm.collectionVariables.get('pay_orderId')||'')) { pm.collectionVariables.set('pay_orderId','MS_PLACEHOLDER'); }",
          post: postPay("over"),
        }),
        item("【language=en-US duration=1800】| PAY-SMOKE-EN | POST /v2/orders/payments", {
          reqPath: "/v2/orders/payments",
          body: {
            orderId: "{{pay_orderId}}",
            returnUrl: "https://www.ly.com",
            paymentMethod: "H5_CASHIER",
            language: "en-US",
            durationInSeconds: 1800,
          },
          post: postPay("ok"),
        }),
      ]),
      folder("Auth双密钥 · 冒烟", [
        item("【鉴权1取Token】| AUTH-1 | POST /v2/auth/token", {
          reqPath: "/v2/auth/token",
          withAuth: false,
          body: { clientId: "{{auth1_clientId}}", secret: "{{auth1_secret}}" },
          extraPre: [
            "if (pm.environment.get('auth1_clientId')) pm.environment.set('clientId', String(pm.environment.get('auth1_clientId')));",
            "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID') || '2045264240542720'));",
            "pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
          ].join("\n"),
          post: [
            "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
            "if (String(json.errCode)==='201.000.001') { pm.test.skip('鉴权1 secret 无效，请在环境填 auth1_clientId/auth1_secret'); }",
            "else { " + postAuth() + " }",
          ].join("\n"),
        }),
        item("【鉴权2取Token】| AUTH-2 | POST /v2/auth/token", {
          reqPath: "/v2/auth/token",
          withAuth: false,
          body: { clientId: "{{auth2_clientId}}", secret: "{{auth2_secret}}" },
          extraPre: [
            "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID') || '2045264240542720'));",
            "pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
          ].join("\n"),
          post: [
            "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
            "if (String(json.errCode)==='201.000.001') { pm.test.skip('鉴权2 secret 无效，请在环境填 auth2_clientId/auth2_secret'); }",
            "else { pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); }); }",
          ].join("\n"),
        }),
      ]),
    ]),
    folder("P1 (全量用例)", [
      folder("sso免登录短链接", [
        folder("按XMind用例", [
          folder("SSO免登短链 · 01必填校验", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【不传scene】| SSO-REQ-001 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: {
                subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "pm.test('检查点 | 期望=失败 | 实际=' + json.code, function () { pm.expect(json.code).to.not.eql(0); });",
              ].join("\n"),
            }),
            item("【ORDER_DETAIL缺extra.orderId】| SSO-REQ-602 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: {
                subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
                scene: "ORDER_DETAIL",
                extra: {},
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: postErr("500.000.602"),
            }),
            item("【ORDER_DETAIL空orderId】| SSO-REQ-602-EMPTY | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: {
                subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
                scene: "ORDER_DETAIL",
                extra: { orderId: "" },
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: postErr("500.000.602"),
            }),
            item("【order_list不传extra】| SSO-REQ-LIST | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: {
                subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
                scene: "ORDER_LIST",
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: postSso(),
            }),
          ]),
          folder("SSO免登短链 · 02参数标准化", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【scene=order_list】| SSO-STD-LIST | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: ssoListBody,
              post: postSso(),
            }),
            item("【scene=ORDER_DETAIL】| SSO-STD-DETAIL | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: ssoDetailBody,
              post: postSso(),
            }),
            item("【language=zh-CN】| SSO-STD-ZH | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { language: "zh-CN" }),
              post: postSso(),
            }),
            item("【es-419已知301】| SSO-STD-ES419 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { language: "es-419" }),
              post: postErr("301.000.001"),
            }),
            folder(
              "语种轮询BOSS29",
              ssoLangs.map((lang) =>
                item("【language=" + lang + "】| SSO-LANG | POST /v2/sso/links", {
                  reqPath: "/v2/sso/links",
                  body: Object.assign({}, ssoListBody, { language: lang }),
                  post:
                    lang === "es-419"
                      ? postErr("301.000.001")
                      : postSso(),
                })
              )
            ),
          ]),
          folder("SSO免登短链 · 03异常场景", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【orderId不存在】| SSO-ERR-MISS | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: {
                subject: { type: "MEMBERSHIP", id: "{{sso_subject_id}}" },
                scene: "ORDER_DETAIL",
                extra: { orderId: "FT999999999999999" },
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "pm.test('检查点 | 期望=失败 | 实际=' + json.code + ' ' + json.errCode, function () { pm.expect(json.code).to.not.eql(0); });",
              ].join("\n"),
            }),
            item("【duration=59】| SSO-ERR-59 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { durationInSeconds: 59 }),
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "pm.test('检查点 | 期望=失败 | 实际=' + json.code, function () { pm.expect(json.code).to.not.eql(0); });",
              ].join("\n"),
            }),
            item("【duration=7201】| SSO-ERR-7201 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { durationInSeconds: 7201 }),
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "pm.test('检查点 | 期望=失败 | 实际=' + json.code, function () { pm.expect(json.code).to.not.eql(0); });",
              ].join("\n"),
            }),
            item("【无Token】| SSO-ERR-401 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              withAuth: false,
              body: ssoListBody,
              post: [
                "pm.test('检查点 | 期望=鉴权失败 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.be.oneOf([401,403,200]); });",
              ].join("\n"),
            }),
          ]),
          folder("SSO免登短链 · 04边界与容错", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【duration=60】| SSO-BND-60 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { durationInSeconds: 60 }),
              post: postSso(),
            }),
            item("【duration=7200】| SSO-BND-7200 | POST /v2/sso/links", {
              reqPath: "/v2/sso/links",
              body: Object.assign({}, ssoListBody, { durationInSeconds: 7200 }),
              post: postSso(),
            }),
          ]),
        ]),
      ]),
      folder("FT可用性", [
        folder("按XMind用例", [
          folder("FT可用性 · 01过去时间拦截", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【过去时间拦截】| FT-030 | POST /v2/resources/prebookings/availability", {
              reqPath: "/v2/resources/prebookings/availability",
              body: { module: 2, resourceId: "C10826", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
              extraPre: ftPre("past"),
              post: postErr("500.020.030", "current local time"),
            }),
            item("【时区换算-AEP当地已过】| FT-030-TZ | POST /v2/resources/prebookings/availability", {
              reqPath: "/v2/resources/prebookings/availability",
              body: { module: 2, resourceId: "C10899", prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
              extraPre: ftPre("past", "pm.variables.set('ft_tz_offset_hours','-3'); pm.variables.set('ft_resourceId','C10899');"),
              post: postErr("500.020.030", "current local time"),
            }),
            item("【未来时间不报030】| FT-FUTURE | POST /v2/resources/prebookings/availability", {
              reqPath: "/v2/resources/prebookings/availability",
              body: { module: 2, resourceId: "C10826", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
              extraPre: ftPre("future", "pm.variables.set('ft_resourceId','C10826'); pm.variables.set('ft_tz_offset_hours','7');"),
              post: [
                postOk(),
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "pm.test('检查点 | 期望=不是 500.020.030 | 实际=' + json.errCode, function () { pm.expect(String(json.errCode||'')).to.not.eql('500.020.030'); });",
              ].join("\n"),
            }),
            folder("多时区抽样", [
              ["C10826", "7", "BKK"],
              ["C10711", "8", "PEK"],
              ["C10726", "4", "DXB"],
              ["C10849", "2", "PRG"],
              ["C10899", "-3", "AEP"],
            ].map(([rid, off, iata]) =>
              item("【过去时间-" + iata + "】| FT-030-" + iata + " | POST /v2/resources/prebookings/availability", {
                reqPath: "/v2/resources/prebookings/availability",
                body: { module: 2, resourceId: rid, prebookingDate: "2020-01-01T10:00", adultCount: 1, childCount: 0 },
                extraPre: ftPre("past", "pm.variables.set('ft_resourceId','" + rid + "'); pm.variables.set('ft_tz_offset_hours','" + off + "');"),
                post: postErr("500.020.030", "current local time"),
              })
            )),
          ]),
          folder("FT可用性 · 02错误码迁移039-044", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【原030迁039 Preview AR=true】| ERR-039 | POST /v2/orders/memberships/purchase/preview", {
              reqPath: "/v2/orders/memberships/purchase/preview",
              body: { appId: 1, autoRenewal: true, profile },
              post: postErr("500.030.039", "Unable to preview"),
            }),
            item("【原031迁040 Create AR=false】| ERR-040 | POST /v2/orders/memberships/purchase", {
              reqPath: "/v2/orders/memberships/purchase",
              body: { appId: 1, autoRenewal: false, profile },
              post: postErr("500.030.040", "unable to process your order"),
            }),
            item("【原033迁042 Create AR=true】| ERR-042 | POST /v2/orders/memberships/purchase", {
              reqPath: "/v2/orders/memberships/purchase",
              body: { appId: 1, autoRenewal: true, profile },
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "var err = String(json.errCode||'');",
                "pm.test('检查点 | 期望=不是旧码 500.020.033 | 实际=' + err, function () { pm.expect(err).to.not.eql('500.020.033'); });",
                "pm.test('检查点 | 期望=039或042 | 实际=' + err, function () { pm.expect(['500.030.039','500.030.042']).to.include(err); });",
              ].join("\n"),
            }),
            item("【原035迁044 会籍不存在】| ERR-044 | POST /v2/memberships/subscriptions/cancellation", {
              reqPath: "/v2/memberships/subscriptions/cancellation",
              body: { membershipId: "0000000000000000", email: "2484268151@qq.COM" },
              post: postErr("500.030.044", "Failed to cancel"),
            }),
          ]),
          folder("FT可用性 · 03补充错误码045", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【purchase/details 不存在单】| ERR-045 | POST /v2/orders/memberships/purchase/details", {
              reqPath: "/v2/orders/memberships/purchase/details",
              body: { orderId: "9999999999999999" },
              post: postErr("500.030.045", "unable to retrieve the order details"),
            }),
          ]),
          folder("FT可用性 · 04时区特殊与空时区", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【空时区资源】| FT-TZ-EMPTY | POST /v2/resources/prebookings/availability", {
              reqPath: "/v2/resources/prebookings/availability",
              body: { module: 2, resourceId: "{{ft_empty_tz_resourceId}}", prebookingDate: "2099-01-01T10:00", adultCount: 1, childCount: 0 },
              extraPre: [
                "var rid = String(pm.environment.get('ft_empty_tz_resourceId')||'');",
                "if (!rid) { pm.variables.set('ft_skip','1'); }",
                ftPre("future"),
              ].join("\n"),
              post: [
                "if (String(pm.variables.get('ft_skip')||'')==='1') { pm.test.skip('未配置 ft_empty_tz_resourceId'); }",
                "else { " + defaultPost() + " }",
              ].join("\n"),
            }),
          ]),
        ]),
      ]),
      folder("支付链接", [
        folder("按XMind用例", [
          folder("支付链接 · 01语种language校验", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【不传language默认en-US】| PAY-LANG-DEFAULT | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: { orderId: "{{pay_orderId}}", returnUrl: "https://www.ly.com", paymentMethod: "H5_CASHIER" },
              post: postPay("ok"),
            }),
            item("【language=en-US】| PAY-LANG-EN | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: {
                orderId: "{{pay_orderId}}",
                returnUrl: "https://www.ly.com",
                paymentMethod: "H5_CASHIER",
                language: "en-US",
              },
              post: postPay("ok"),
            }),
            folder(
              "XMind12语种遍历",
              payLangs.map((lang) =>
                item("【language=" + lang + "】| PAY-LANG-" + lang + " | POST /v2/orders/payments", {
                  reqPath: "/v2/orders/payments",
                  body: {
                    orderId: "{{pay_orderId}}",
                    returnUrl: "https://www.ly.com",
                    paymentMethod: "H5_CASHIER",
                    language: lang,
                    durationInSeconds: 1800,
                  },
                  post: postPay("ok"),
                })
              )
            ),
          ]),
          folder("支付链接 · 02有效期durationInSeconds校验", [
            authItem("00 【换Token】| AUTH | POST /v2/auth/token"),
            item("【不传duration默认600】| PAY-DUR-DEFAULT | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: { orderId: "{{pay_orderId}}", returnUrl: "https://www.ly.com", paymentMethod: "H5_CASHIER" },
              post: postPay("ok"),
            }),
            item("【duration=60】| PAY-DUR-60 | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: {
                orderId: "{{pay_orderId}}",
                returnUrl: "https://www.ly.com",
                paymentMethod: "H5_CASHIER",
                durationInSeconds: 60,
              },
              post: postPay("ok"),
            }),
            item("【duration=1800上限】| PAY-DUR-1800 | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: {
                orderId: "{{pay_orderId}}",
                returnUrl: "https://www.ly.com",
                paymentMethod: "H5_CASHIER",
                language: "en-US",
                durationInSeconds: 1800,
              },
              post: postPay("ok"),
            }),
            item("【duration=1801超上限】| PAY-DUR-1801 | POST /v2/orders/payments", {
              reqPath: "/v2/orders/payments",
              body: {
                orderId: "{{pay_orderId}}",
                returnUrl: "https://www.ly.com",
                paymentMethod: "H5_CASHIER",
                durationInSeconds: 1801,
              },
              extraPre:
                "if (!String(pm.environment.get('pay_orderId')||pm.collectionVariables.get('pay_orderId')||'')) { pm.collectionVariables.set('pay_orderId','MS_PLACEHOLDER'); }",
              post: postPay("over"),
            }),
          ]),
        ]),
      ]),
      folder("Auth双密钥", [
        folder("按XMind用例", [
          folder("Auth双密钥 · 02两套token跑通链路", [
            item("【鉴权1取Token】| AUTH-1 | POST /v2/auth/token", {
              reqPath: "/v2/auth/token",
              withAuth: false,
              body: { clientId: "{{auth1_clientId}}", secret: "{{auth1_secret}}" },
              extraPre:
                "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID')||'2045264240542720')); pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "if (String(json.errCode)==='201.000.001') pm.test.skip('请更新 auth1_clientId/secret');",
                "else { " + postAuth() + " }",
              ].join("\n"),
            }),
            item("【鉴权2取Token】| AUTH-2 | POST /v2/auth/token", {
              reqPath: "/v2/auth/token",
              withAuth: false,
              body: { clientId: "{{auth2_clientId}}", secret: "{{auth2_secret}}" },
              extraPre:
                "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID')||'2045264240542720')); pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "if (String(json.errCode)==='201.000.001') pm.test.skip('请更新 auth2_clientId/secret');",
                "else { pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); }); }",
              ].join("\n"),
            }),
          ]),
          folder("Auth双密钥 · 03RS256与HS256判定组合", [
            item("【组合4 HS256+HS256 鉴权1】| AUTH-ALG | POST /v2/auth/token", {
              reqPath: "/v2/auth/token",
              withAuth: false,
              body: { clientId: "{{auth1_clientId}}", secret: "{{auth1_secret}}" },
              extraPre:
                "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID')||'2045264240542720')); pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "if (String(json.errCode)==='201.000.001') pm.test.skip('密钥无效，RS256组合需 BOSS 配置后手工测');",
                "else { pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); }); }",
              ].join("\n"),
            }),
          ]),
          folder("Auth双密钥 · 04密钥配置增删改", [
            item("【当前config取Token】| AUTH-CRUD | POST /v2/auth/token", {
              reqPath: "/v2/auth/token",
              withAuth: false,
              body: { clientId: "{{auth1_clientId}}", secret: "{{auth1_secret}}" },
              extraPre:
                "pm.environment.set('ProgramID', String(pm.environment.get('dual_ProgramID')||'2045264240542720')); pm.environment.set('Program-ID', pm.environment.get('ProgramID'));",
              post: [
                "var json = {}; try { json = pm.response.json(); } catch (e) { json = {}; }",
                "if (String(json.errCode)==='201.000.001') pm.test.skip('增删改请在 BOSS 手工做完后，用剩余密钥再跑本条');",
                "else { pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); }); }",
              ].join("\n"),
            }),
          ]),
        ]),
      ]),
    ]),
  ],
};

const env = {
  id: "q3-sp4-xmind-accept-env",
  name: "Q3-SP4 四需求验收（canary沙箱）",
  values: [
    { key: "baseUrl", value: "https://developer-sandbox.dragonpass.com/api", enabled: true },
    { key: "x-version", value: "canary", enabled: true },
    { key: "ProgramID", value: "1919256841868288", enabled: true },
    { key: "Program-ID", value: "1919256841868288", enabled: true },
    { key: "clientId", value: "", enabled: true },
    { key: "secret", value: "", enabled: true },
    { key: "accessToken", value: "", enabled: true },
    { key: "sso_subject_id", value: "8576507744260001", enabled: true },
    { key: "sso_orderId", value: "FT20260904BG5VM58", enabled: true },
    { key: "fastTrackResourceId", value: "C10826", enabled: true },
    { key: "ft_tz_offset_hours", value: "7", enabled: true },
    { key: "membershipId", value: "8576507744260001", enabled: true },
    { key: "pay_orderId", value: "", enabled: true },
    { key: "pay_returnUrl", value: "https://www.ly.com", enabled: true },
    { key: "pay_paymentMethod", value: "H5_CASHIER", enabled: true },
    { key: "dual_ProgramID", value: "2045264240542720", enabled: true },
    { key: "auth1_clientId", value: "", enabled: true },
    { key: "auth1_secret", value: "", enabled: true },
    { key: "auth2_clientId", value: "", enabled: true },
    { key: "auth2_secret", value: "", enabled: true },
    { key: "ft_empty_tz_resourceId", value: "", enabled: true },
  ],
  _postman_variable_scope: "environment",
};

const outCol = path.join(__dirname, "Q3-SP4-四需求-验收.postman_collection.json");
const outEnv = path.join(__dirname, "Q3-SP4-四需求-验收.postman_environment.json");
fs.writeFileSync(outCol, JSON.stringify(collection, null, 2), "utf8");
fs.writeFileSync(outEnv, JSON.stringify(env, null, 2), "utf8");
console.log("collection", outCol);
console.log("environment", outEnv);
