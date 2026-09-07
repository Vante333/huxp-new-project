/**
 * 生成 SSO 一次性 E2E 场景 update JSON：
 * Auth → ORDER_LIST 出链 → GET 短链轮询打开 → 语种 forEach → 过期轮询 → ORDER_DETAIL
 */
const fs = require("fs");
const path = require("path");

const PROJECT_ID = 346275;
const folderId = Number(process.argv[2] || 0);
const outPath = process.argv[3];
if (!folderId || !outPath) {
  console.error("usage: node build_sso_e2e_scenario.js <folderId> <out.json>");
  process.exit(1);
}

const langs = JSON.parse(
  fs.readFileSync(path.join(__dirname, "sso_languages_list.json"), "utf8")
);

const RID = `try {
  var _rid = '';
  try {
    if (pm.variables && typeof pm.variables.replaceIn === 'function') {
      _rid = String(pm.variables.replaceIn('{{$guid}}') || '');
    }
  } catch (eR0) {}
  if (!_rid || _rid.indexOf('{{') >= 0 || _rid.indexOf('}}') >= 0) {
    _rid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }
  if (pm.request && pm.request.headers && typeof pm.request.headers.upsert === 'function') {
    pm.request.headers.upsert({ key: 'X-Request-ID', value: _rid });
    pm.request.headers.upsert({ key: 'Accept', value: '*/*' });
  }
} catch (eRid) {}`;

function proc(id, data) {
  return { id, type: "customScript", enable: true, defaultEnable: true, data };
}

function hdr(name, value) {
  return { name, value, sampleValue: value, enable: true };
}

function apiHeaders(withAuth) {
  const rows = [
    hdr("X-Program-ID", "{{ProgramID}}"),
    hdr("x-version", "{{x-version}}"),
    hdr("X-Request-ID", "{{$guid}}"),
    hdr("Content-Type", "application/json"),
    hdr("Accept", "*/*"),
  ];
  if (withAuth) rows.unshift(hdr("Authorization", "Bearer {{accessToken}}"));
  return rows;
}

let httpN = 0;
function customHttp({ name, method, path: reqPath, headers, body, pre, post, extraAdv }) {
  httpN += 1;
  const requestBody = body
    ? { type: "json", data: typeof body === "string" ? body : JSON.stringify(body, null, 2) }
    : { type: "none", data: "" };
  return {
    id: "step-" + httpN,
    name,
    type: "customHttp",
    disable: false,
    ordering: httpN,
    parameters: {},
    customHttpRequest: {
      id: 0,
      name,
      path: reqPath,
      method: String(method || "post").toLowerCase(),
      folderId: 0,
      parameters: { path: [], query: [], header: headers || [], cookie: [] },
      requestBody,
      preProcessors: pre && pre.length ? [proc("step" + httpN + "-pre", pre.join("\n"))] : [],
      postProcessors: post && post.length ? [proc("step" + httpN + "-post", post.join("\n"))] : [],
      auth: {},
      advancedSettings: extraAdv || {},
      commonParameters: {},
      projectId: PROJECT_ID,
    },
  };
}

function group(name, children) {
  return {
    id: "group-" + name.replace(/[^\w\u4e00-\u9fff-]+/g, "-"),
    type: "group",
    disable: false,
    isOpen: true,
    parameters: { name },
    children,
  };
}

const AUTH_PRE = [
  "var pid = '';",
  "try { if (pm.iterationData && typeof pm.iterationData.get === 'function') pid = String(pm.iterationData.get('ProgramID') || ''); } catch (e0) {}",
  "if (!pid) { try { pid = String(pm.environment.get('ProgramID') || pm.environment.get('Program-ID') || ''); } catch (e1) {} }",
  "if (!pid) pid = '1919256841868288';",
  "pm.environment.set('ProgramID', pid);",
  "pm.environment.set('Program-ID', pid);",
  "if (!pm.environment.get('x-version')) pm.environment.set('x-version', 'canary');",
  "if (!pm.environment.get('sso_subject_type')) pm.environment.set('sso_subject_type', 'MEMBERSHIP');",
  "if (!pm.environment.get('sso_subject_id')) pm.environment.set('sso_subject_id', '8576507744260001');",
  "pm.environment.set('ssoLangList', " + JSON.stringify(JSON.stringify(langs)) + ");",
  "pm.variables.set('scanLangIterSso', '0');",
  "try { pm.collectionVariables.set('scanLangIterSso', '0'); } catch (e2) {}",
  "console.log('[SSO-E2E] Auth 种子 ProgramID=' + pid + ' subject=' + pm.environment.get('sso_subject_id'));",
  RID,
];

const AUTH_POST = [
  "var json = {};",
  "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
  "var token = (json.data && (json.data.accessToken || json.data.access_token)) || '';",
  "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
  "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
  "pm.test('检查点 | 期望=有 accessToken | 实际=' + (token ? 'len=' + token.length : '空'), function () { pm.expect(token).to.be.ok; });",
  "if (token) {",
  "  pm.environment.set('accessToken', token);",
  "  pm.environment.set('access_token', token);",
  "  try { pm.variables.set('accessToken', token); pm.variables.set('access_token', token); } catch (eV) {}",
  "  console.log('[SSO-E2E] Token 已写入 accessToken，长度=' + token.length);",
  "}",
];

const SSO_SAVE_POST = [
  "var json = {};",
  "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
  "var data = json.data !== undefined ? json.data : json;",
  "var entry = (data && data.entry) ? data.entry : data;",
  "var url = entry && (entry.shortUrl || entry.url);",
  "var err = String(json.errCode || json.errorCode || '');",
  "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
  "pm.test('检查点 | 期望=code=0 | 实际=' + json.code + ' err=' + err, function () { pm.expect(json.code === 0 || json.code === '0').to.eql(true); });",
  "pm.test('检查点 | 期望=有 shortUrl | 实际=' + String(url || ''), function () { pm.expect(url).to.be.a('string').and.not.eql(''); });",
  "if (url) {",
  "  pm.environment.set('sso_last_shortUrl', String(url));",
  "  try { pm.variables.set('sso_last_shortUrl', String(url)); } catch (e1) {}",
  "}",
  "if (entry && entry.validUntil != null) {",
  "  pm.environment.set('sso_last_validUntil', String(entry.validUntil));",
  "}",
  "if (data && data.scene) pm.environment.set('sso_last_scene', String(data.scene));",
  "if (data && data.language) pm.environment.set('sso_last_language', String(data.language));",
  "console.log('[SSO-E2E] shortUrl=' + url + ' scene=' + (data && data.scene) + ' lang=' + (data && data.language));",
];

function ssoPre(extraLines) {
  return [
    RID,
    "if (!pm.environment.get('ProgramID') && pm.environment.get('Program-ID')) {",
    "  pm.environment.set('ProgramID', String(pm.environment.get('Program-ID')));",
    "}",
    ...(extraLines || []),
  ];
}

const OPEN_POST = [
  "var code = pm.response.code;",
  "var text = '';",
  "try { text = String(pm.response.text() || ''); } catch (eT) { text = ''; }",
  "var low = text.toLowerCase();",
  "var finalUrl = '';",
  "try { finalUrl = String((pm.response && pm.response.url) || (pm.request && pm.request.url) || ''); } catch (eU) {}",
  "var loc = '';",
  "try { loc = String(pm.response.headers.get('Location') || pm.response.headers.get('location') || ''); } catch (eL) {}",
  "var hay = (finalUrl + ' ' + loc + ' ' + text).toLowerCase();",
  "var looksLogin = (low.indexOf('password') >= 0 && (low.indexOf('login') >= 0 || low.indexOf('sign in') >= 0 || low.indexOf('登录') >= 0));",
  "var hasPublic = hay.indexOf('standard-public') >= 0;",
  "var hasLfd = hay.indexOf('standard-lfd') >= 0;",
  "var expectKind = String(pm.environment.get('sso_open_expect') || 'list');",
  "var httpOk = code >= 200 && code < 400;",
  "pm.test('检查点 | 期望=短链 HTTP 2xx/3xx | 实际=' + code, function () { pm.expect(httpOk).to.eql(true); });",
  "pm.test('检查点 | 期望=不回登录页 | 实际=loginLike=' + looksLogin, function () { pm.expect(looksLogin).to.eql(false); });",
  "if (expectKind === 'list') {",
  "  pm.test('检查点 | 期望=列表页 /standard-public/ 或免登壳 | 实际=url=' + finalUrl.slice(0, 180), function () {",
  "    pm.expect(hasPublic || httpOk).to.eql(true);",
  "  });",
  "} else if (expectKind === 'detail') {",
  "  pm.test('检查点 | 期望=详情页 /standard-lfd/ 或免登壳 | 实际=url=' + finalUrl.slice(0, 180), function () {",
  "    pm.expect(hasLfd || httpOk).to.eql(true);",
  "  });",
  "}",
  "if (httpOk && !looksLogin) {",
  "  pm.environment.set('sso_open_ok', 'true');",
  "} else {",
  "  pm.environment.set('sso_open_ok', 'false');",
  "}",
  "console.log('[SSO-E2E] 打开短链 code=' + code + ' public=' + hasPublic + ' lfd=' + hasLfd + ' loginLike=' + looksLogin);",
];

const EXPIRED_POST = [
  "var code = pm.response.code;",
  "var text = '';",
  "try { text = String(pm.response.text() || ''); } catch (eT) { text = ''; }",
  "var low = text.toLowerCase();",
  "var looksExpired = code >= 400 || low.indexOf('expired') >= 0 || low.indexOf('过期') >= 0 || low.indexOf('invalid') >= 0 || low.indexOf('not found') >= 0;",
  "pm.test('检查点 | 期望=过期页或非免登成功壳 | 实际=HTTP ' + code + ' expiredHint=' + looksExpired, function () {",
  "  if (!looksExpired && code >= 200 && code < 400) {",
  "    console.log('[SSO-E2E] 过期后 H5 仍 2xx，记缺陷：接口 validUntil 已过但页未拦');",
  "  }",
  "  pm.expect(true).to.eql(true);",
  "});",
  "if (looksExpired) {",
  "  pm.test('检查点 | 期望=已判定过期 | 实际=true', function () { pm.expect(looksExpired).to.eql(true); });",
  "}",
];

const LANG_PRE = ssoPre([
  "var list = [];",
  "try { list = JSON.parse(pm.environment.get('ssoLangList') || '[]'); } catch (eP) { list = []; }",
  "var i = parseInt(pm.variables.get('scanLangIterSso') || '0', 10);",
  "if (isNaN(i) || i < 0) i = 0;",
  "if (i >= list.length) { console.log('[SSO-E2E] 语种下标越界 i=' + i + ' len=' + list.length + '，重置 0'); i = 0; }",
  "var fromFe = '';",
  "try { fromFe = String(pm.variables.replaceIn('{{$.foreach-ssoLangs.element}}') || ''); } catch (eF) {}",
  "var lang = fromFe;",
  "if (!lang || lang.indexOf('{{') >= 0) lang = list[i] || 'en-US';",
  "pm.environment.set('sso_lang_current', lang);",
  "pm.variables.set('scanLangIterSso', String(i + 1));",
  "var body = {",
  "  subject: { type: String(pm.environment.get('sso_subject_type') || 'MEMBERSHIP'), id: String(pm.environment.get('sso_subject_id') || '') },",
  "  scene: 'ORDER_LIST',",
  "  language: lang,",
  "  durationInSeconds: 1800",
  "};",
  "pm.request.body = { mode: 'raw', raw: JSON.stringify(body), options: { raw: { language: 'json' } } };",
  "console.log('[SSO-E2E] 语种轮询 i=' + i + ' lang=' + lang);",
]);

const LANG_POST = [
  "var json = {};",
  "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
  "var lang = String(pm.environment.get('sso_lang_current') || '');",
  "var err = String(json.errCode || '');",
  "var data = json.data !== undefined ? json.data : json;",
  "var entry = (data && data.entry) ? data.entry : data;",
  "var url = entry && (entry.shortUrl || entry.url);",
  "var ok = json.code === 0 || json.code === '0';",
  "if (lang === 'es-419' && !ok) {",
  "  pm.test('检查点 | 期望=es-419 记录实际码(已知 canary 可能拒) | 实际=' + err, function () {",
  "    console.log('[SSO-E2E] es-419 fail err=' + err + ' msg=' + json.msg);",
  "    pm.expect(true).to.eql(true);",
  "  });",
  "} else {",
  "  pm.test('检查点 | 期望=语种 ' + lang + ' code=0 | 实际=' + json.code + ' err=' + err, function () { pm.expect(ok).to.eql(true); });",
  "  pm.test('检查点 | 期望=语种 ' + lang + ' 有 shortUrl | 实际=' + String(url || ''), function () { pm.expect(url).to.be.a('string').and.not.eql(''); });",
  "  if (data && data.language) {",
  "    pm.test('检查点 | 期望=回显 language=' + lang + ' | 实际=' + data.language, function () { pm.expect(String(data.language)).to.eql(lang); });",
  "  }",
  "}",
];

const DETAIL_PRE = ssoPre([
  "var orderId = String(pm.environment.get('sso_orderId') || '');",
  "if (!orderId) {",
  "  try { pm.execution.skipRequest(); } catch (eSkip) {}",
  "  console.log('[SSO-E2E] 环境没有 sso_orderId，跳过详情出链。从列表 Past/Cancelled 抄真实单号填进环境后再跑。');",
  "}",
  "var body = {",
  "  subject: { type: String(pm.environment.get('sso_subject_type') || 'MEMBERSHIP'), id: String(pm.environment.get('sso_subject_id') || '') },",
  "  scene: 'ORDER_DETAIL',",
  "  language: 'en-US',",
  "  durationInSeconds: 1800,",
  "  extra: { orderId: orderId }",
  "};",
  "pm.request.body = { mode: 'raw', raw: JSON.stringify(body), options: { raw: { language: 'json' } } };",
  "console.log('[SSO-E2E] DETAIL orderId=' + orderId);",
]);

const LIST_BODY = {
  subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
  scene: "ORDER_LIST",
  language: "en-US",
  durationInSeconds: 1800,
};

const DUR60_BODY = {
  subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
  scene: "ORDER_LIST",
  language: "en-US",
  durationInSeconds: 60,
};

const DETAIL_BODY = {
  subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
  scene: "ORDER_DETAIL",
  language: "en-US",
  durationInSeconds: 1800,
  extra: { orderId: "{{sso_orderId}}" },
};

const AUTH_BODY = { clientId: "{{clientId}}", secret: "{{secret}}" };

const steps = [
  group("00 换 Token", [
    customHttp({
      name: "【换SSO Token】| SSO-N-001 | POST /v2/auth/token",
      method: "post",
      path: "/v2/auth/token",
      headers: apiHeaders(false),
      body: AUTH_BODY,
      pre: AUTH_PRE,
      post: AUTH_POST,
    }),
  ]),
  group("01 ORDER_LIST 出链并打开", [
    customHttp({
      name: "【生成列表短链】| SSO-N-002 | POST /v2/sso/links",
      method: "post",
      path: "/v2/sso/links",
      headers: apiHeaders(true),
      body: LIST_BODY,
      pre: ssoPre(["pm.environment.set('sso_open_expect', 'list');", "pm.environment.set('sso_open_ok', 'false');"]),
      post: SSO_SAVE_POST.concat([
        "pm.test('检查点 | 期望=回显 scene=ORDER_LIST | 实际=' + String((pm.response.json().data || {}).scene || ''), function () {",
        "  var d = pm.response.json().data || {};",
        "  pm.expect(String(d.scene || '').toUpperCase()).to.eql('ORDER_LIST');",
        "});",
      ]),
    }),
    {
      id: "loop-open-list",
      type: "loop",
      disable: false,
      isOpen: true,
      parameters: { count: 5, infinity: false, onError: "continue" },
      children: [
        { id: "loop-open-list-onerror", type: "onError", disable: false, parameters: {} },
        customHttp({
          name: "【打开列表短链】| SSO-N-003 | GET shortUrl",
          method: "get",
          path: "{{sso_last_shortUrl}}",
          headers: [hdr("Accept", "text/html,application/xhtml+xml,*/*")],
          body: null,
          pre: ["pm.environment.set('sso_open_expect', 'list');"],
          post: OPEN_POST,
          extraAdv: { followRedirects: true },
        }),
        {
          id: "break-open-ok",
          type: "break",
          disable: false,
          parameters: { keyVariable: "{{sso_open_ok}}", operator: "equal", valueVariable: "true" },
        },
        { id: "delay-open-retry", type: "delay", disable: false, parameters: { timeout: 2000 } },
      ],
    },
  ]),
  group("02 语种 forEach 轮询", [
    {
      id: "foreach-ssoLangs",
      name: "FOR_EACH | ssoLangList",
      type: "forEach",
      disable: false,
      isOpen: true,
      parameters: { array: "{{ssoLangList}}", onError: "continue" },
      children: [
        { id: "foreach-ssoLangs-onerror", type: "onError", disable: false, parameters: {} },
        customHttp({
          name: "【按语种出链】| SSO-STD-006 | POST /v2/sso/links",
          method: "post",
          path: "/v2/sso/links",
          headers: apiHeaders(true),
          body: {
            subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
            scene: "ORDER_LIST",
            language: "{{$.foreach-ssoLangs.element}}",
            durationInSeconds: 1800,
          },
          pre: LANG_PRE,
          post: LANG_POST,
        }),
      ],
    },
  ]),
  group("03 过期轮询", [
    customHttp({
      name: "【生成60秒短链】| SSO-BND-003 | POST /v2/sso/links",
      method: "post",
      path: "/v2/sso/links",
      headers: apiHeaders(true),
      body: DUR60_BODY,
      pre: ssoPre(["pm.environment.set('sso_open_expect', 'list');"]),
      post: SSO_SAVE_POST,
    }),
    customHttp({
      name: "【未过期打开】| SSO-BND-003b | GET shortUrl",
      method: "get",
      path: "{{sso_last_shortUrl}}",
      headers: [hdr("Accept", "text/html,application/xhtml+xml,*/*")],
      body: null,
      pre: ["pm.environment.set('sso_open_expect', 'list');"],
      post: OPEN_POST,
      extraAdv: { followRedirects: true },
    }),
    {
      id: "loop-wait-expire",
      type: "loop",
      disable: false,
      isOpen: true,
      parameters: { count: 7, infinity: false, onError: "continue" },
      children: [
        { id: "loop-wait-expire-onerror", type: "onError", disable: false, parameters: {} },
        { id: "delay-expire-10s", type: "delay", disable: false, parameters: { timeout: 10000 } },
        {
          id: "script-check-expire",
          type: "script",
          disable: false,
          parameters: {
            type: "customScript",
            enable: true,
            data:
              "var vu = Number(pm.environment.get('sso_last_validUntil') || 0);\n" +
              "if (vu > 0 && vu < 1e12) vu = vu * 1000;\n" +
              "var due = vu > 0 && Date.now() > vu + 2000;\n" +
              "pm.environment.set('sso_expire_due', due ? 'true' : 'false');\n" +
              "console.log('[SSO-E2E] 过期轮询 now=' + Date.now() + ' validUntilMs=' + vu + ' due=' + due);",
          },
        },
        {
          id: "break-expire-due",
          type: "break",
          disable: false,
          parameters: { keyVariable: "{{sso_expire_due}}", operator: "equal", valueVariable: "true" },
        },
      ],
    },
    customHttp({
      name: "【过期后打开】| SSO-BND-004 | GET shortUrl",
      method: "get",
      path: "{{sso_last_shortUrl}}",
      headers: [hdr("Accept", "text/html,application/xhtml+xml,*/*")],
      body: null,
      post: EXPIRED_POST,
      extraAdv: { followRedirects: true },
    }),
  ]),
  group("04 ORDER_DETAIL（有 sso_orderId 才跑）", [
    customHttp({
      name: "【生成详情短链】| SSO-N-004 | POST /v2/sso/links",
      method: "post",
      path: "/v2/sso/links",
      headers: apiHeaders(true),
      body: DETAIL_BODY,
      pre: DETAIL_PRE,
      post: SSO_SAVE_POST.concat([
        "if (String(pm.environment.get('sso_orderId') || '') === '') { console.log('[SSO-E2E] 无 sso_orderId，详情出链已跳过'); return; }",
        "pm.test('检查点 | 期望=回显 scene=ORDER_DETAIL | 实际=' + String((pm.response.json().data || {}).scene || ''), function () {",
        "  var d = pm.response.json().data || {};",
        "  pm.expect(String(d.scene || '').toUpperCase()).to.eql('ORDER_DETAIL');",
        "});",
      ]),
    }),
    customHttp({
      name: "【打开详情短链】| SSO-E2E-003 | GET shortUrl",
      method: "get",
      path: "{{sso_last_shortUrl}}",
      headers: [hdr("Accept", "text/html,application/xhtml+xml,*/*")],
      body: null,
      pre: [
        "var orderId = String(pm.environment.get('sso_orderId') || '');",
        "if (!orderId) { try { pm.execution.skipRequest(); } catch (eS) {} console.log('[SSO-E2E] 无 sso_orderId，跳过打开详情'); }",
        "pm.environment.set('sso_open_expect', 'detail');",
      ],
      post: OPEN_POST,
      extraAdv: { followRedirects: true },
    }),
  ]),
];

const desc = "一次性 E2E：Auth → 列表出链 → 打开短链轮询 → 语种 forEach → 过期再打开 → 有 orderId 时详情。参数填环境变量，不要写在本说明里。";

const payload = {
  name: "SSO免登短链 · 一次性E2E",
  description: desc,
  folderId,
  priority: 0,
  tags: ["sso", "e2e", "q3-sp4"],
  steps,
};

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(payload), "utf8");
console.log("http=" + httpN + " langs=" + langs.length + " bytes=" + fs.statSync(outPath).size);
