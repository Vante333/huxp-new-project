/** Apifox customHttp 积木，对齐 SSO 免登短链模板。 */
const PROJECT_ID = 346275;

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
function customHttp(httpN, { name, method, reqPath, headers, body, pre, post }) {
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
      requestBody: body
        ? { type: "json", data: typeof body === "string" ? body : JSON.stringify(body, null, 2) }
        : { type: "none", data: "" },
      preProcessors: pre ? [proc("step" + httpN + "-pre", pre)] : [],
      postProcessors: post ? [proc("step" + httpN + "-post", post)] : [],
      auth: {},
      advancedSettings: {},
      commonParameters: {},
      projectId: PROJECT_ID,
    },
  };
}
function group(name, children) {
  return {
    id: "group-" + String(name).replace(/[^\w\u4e00-\u9fff-]+/g, "-").slice(0, 48),
    type: "group",
    disable: false,
    isOpen: true,
    parameters: { name },
    children,
  };
}

const AUTH_POST = [
  "var json = {};",
  "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
  "var token = (json.data && (json.data.accessToken || json.data.access_token)) || '';",
  "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
  "pm.test('检查点 | 期望=code=0 | 实际=' + json.code, function () { pm.expect(json.code).to.eql(0); });",
  "pm.test('检查点 | 期望=有 accessToken | 实际=' + (token ? '有' : '空'), function () { pm.expect(token).to.be.ok; });",
  "if (token) {",
  "  pm.environment.set('accessToken', token);",
  "  pm.environment.set('access_token', token);",
  "  try { pm.variables.set('accessToken', token); pm.variables.set('access_token', token); } catch (eV) {}",
  "}",
].join("\n");

function authPre(seedJs) {
  return [
    seedJs,
    "if (!pm.environment.get('x-version')) pm.environment.set('x-version', 'canary');",
    "var pid = String(pm.environment.get('ProgramID') || pm.environment.get('Program-ID') || '');",
    "if (pid) { pm.environment.set('ProgramID', pid); pm.environment.set('Program-ID', pid); }",
    RID,
  ].join("\n");
}

function authStep(n, title, seedJs) {
  return customHttp(n, {
    name: title || "【换Token】| AUTH | POST /v2/auth/token",
    method: "post",
    reqPath: "/v2/auth/token",
    headers: apiHeaders(false),
    body: { clientId: "{{clientId}}", secret: "{{secret}}" },
    pre: authPre(seedJs),
    post: AUTH_POST,
  });
}

function bizOkAssert(extraLines) {
  return [
    "var json = {};",
    "try { json = pm.response.json(); } catch (eJ) { json = {}; }",
    "var err = String(json.errCode || '');",
    "var msg = String(json.msg || '');",
    "pm.test('检查点 | 期望=HTTP 200 | 实际=' + pm.response.code, function () { pm.expect(pm.response.code).to.eql(200); });",
    extraLines || "",
  ].join("\n");
}

module.exports = {
  PROJECT_ID,
  RID,
  proc,
  hdr,
  apiHeaders,
  customHttp,
  group,
  AUTH_POST,
  authPre,
  authStep,
  bizOkAssert,
};
