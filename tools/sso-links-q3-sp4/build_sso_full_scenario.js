/**
 * SSO 全量自动化：Auth + XMind 全量步骤（compact helpers）
 * 场景说明不写密钥。参数走环境变量 / --env-var。
 */
const fs = require("fs");
const path = require("path");

const PROJECT_ID = 346275;
const folderId = Number(process.argv[2] || 0);
const outPath = process.argv[3];
if (!folderId || !outPath) {
  console.error("usage: node build_sso_full_scenario.js <folderId> <out.json>");
  process.exit(1);
}

const dir = __dirname;
const collection = JSON.parse(
  fs.readFileSync(path.join(dir, "PAPI-SSO免登短链-全量自动化.postman_collection.json"), "utf8")
);
const helperPre = fs.readFileSync(path.join(dir, "apifox_pre_sso_full.js"), "utf8");
const helperPost = fs.readFileSync(path.join(dir, "apifox_post_sso_full.js"), "utf8");

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
function customHttp({ name, method, reqPath, headers, body, pre, post }) {
  httpN += 1;
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
    id: "group-" + String(name).replace(/[^\w\u4e00-\u9fff-]+/g, "-").slice(0, 40),
    type: "group",
    disable: false,
    isOpen: true,
    parameters: { name },
    children,
  };
}

function purposeName(raw) {
  const name = String(raw || "SSO");
  const m = name.match(/^(SSO-[A-Z0-9-]+)\s+(.*)$/);
  if (m) return "【" + m[2] + "】| " + m[1] + " | POST /v2/sso/links";
  return "【" + name + "】| SSO | POST /v2/sso/links";
}

function extractCaseSets(execLines) {
  const out = [];
  for (const line of execLines || []) {
    const s = String(line);
    if (s.trim().startsWith("/**") || s.trim().startsWith("function Env")) break;
    if (s.indexOf("pm.variables.set(") >= 0) out.push(s.replace(/;\s*$/, "") + ";");
  }
  return out;
}

function eventExec(item, listen) {
  for (const ev of item.event || []) {
    if (!ev || ev.listen !== listen) continue;
    const exec = (ev.script && ev.script.exec) || [];
    return Array.isArray(exec) ? exec.map(String) : String(exec).split(/\r?\n/);
  }
  return [];
}

const RESET_VARS = [
  "pm.variables.set('sso_omit_scene','false');",
  "pm.variables.set('sso_omit_language','false');",
  "pm.variables.set('sso_omit_duration','false');",
  "pm.variables.set('sso_omit_returnUrl','true');",
  "pm.variables.set('sso_omit_subject','false');",
  "pm.variables.set('sso_omit_extra','false');",
  "pm.variables.set('sso_empty_orderId','false');",
  "pm.variables.set('sso_no_auth','false');",
  "pm.variables.set('sso_bad_auth','false');",
  "pm.variables.set('sso_use_other_order','false');",
  "pm.variables.set('sso_use_missing_subject_id','false');",
  "pm.variables.set('sso_use_bad_subject_type','false');",
  "pm.variables.set('sso_use_bad_returnUrl','false');",
  "pm.variables.set('sso_use_bad_scene','false');",
  "pm.variables.set('sso_duration_as_string_abc','false');",
  "pm.variables.set('sso_scene','ORDER_LIST');",
  "pm.variables.set('sso_expect_type','success');",
  "pm.variables.set('sso_expect_errCode','');",
  "pm.variables.set('sso_expect_scene_echo','');",
  "pm.variables.set('sso_expect_language_echo','');",
  "pm.variables.set('sso_durationInSeconds','1800');",
  "pm.variables.set('sso_returnUrl','');",
].join("\n");

const LOADER_PRE = [
  RID,
  "if (!pm.environment.get('ProgramID') && pm.environment.get('Program-ID')) pm.environment.set('ProgramID', String(pm.environment.get('Program-ID')));",
  "var _src = '';",
  "try { _src = String(pm.environment.get('ssoFullPre') || pm.variables.get('ssoFullPre') || ''); } catch (eS) {}",
  "if (!_src) { console.log('[sso-full] 缺少 ssoFullPre，请先跑 Auth'); }",
  "else { eval(_src); }",
].join("\n");

const LOADER_POST = [
  "var _src = '';",
  "try { _src = String(pm.environment.get('ssoFullPost') || pm.variables.get('ssoFullPost') || ''); } catch (eS) {}",
  "if (!_src) { pm.test('检查点 | 期望=已跑 Auth 写入断言脚本 | 实际=空', function () { pm.expect.fail('缺少 ssoFullPost'); }); }",
  "else { eval(_src); }",
].join("\n");

function buildFolder(folder) {
  const children = [];
  for (const it of folder.item || []) {
    if (!it) continue;
    if (Array.isArray(it.item) && !it.request) {
      children.push(buildFolder(it));
      continue;
    }
    if (!it.request) continue;
    const sets = extractCaseSets(eventExec(it, "prerequest"));
    children.push(
      customHttp({
        name: purposeName(it.name),
        method: (it.request.method || "POST").toLowerCase(),
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: { scene: "ORDER_LIST", language: "en-US", durationInSeconds: 1800 },
        pre: [RESET_VARS, sets.join("\n"), LOADER_PRE].filter(Boolean).join("\n"),
        post: LOADER_POST,
      })
    );
  }
  return group(String(folder.name || "group"), children);
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
  "if (!pm.environment.get('sso_duration_default')) pm.environment.set('sso_duration_default', '1800');",
  "pm.environment.set('ssoFullPre', " + JSON.stringify(helperPre) + ");",
  "pm.environment.set('ssoFullPost', " + JSON.stringify(helperPost) + ");",
  "try { pm.variables.set('ssoFullPre', pm.environment.get('ssoFullPre')); pm.variables.set('ssoFullPost', pm.environment.get('ssoFullPost')); } catch (eH) {}",
  "console.log('[sso-full] Auth 种子 ProgramID=' + pid);",
  RID,
].join("\n");

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

const steps = [
  group("00 换 Token", [
    customHttp({
      name: "【换SSO Token】| SSO-N-001 | POST /v2/auth/token",
      method: "post",
      reqPath: "/v2/auth/token",
      headers: apiHeaders(false),
      body: { clientId: "{{clientId}}", secret: "{{secret}}" },
      pre: AUTH_PRE,
      post: AUTH_POST,
    }),
  ]),
];

for (const folder of collection.item || []) {
  if (folder && Array.isArray(folder.item)) steps.push(buildFolder(folder));
}

const payload = {
  name: "SSO免登短链 · 全量自动化",
  description: "按 XMind 全量接口用例。先 Auth 再逐条 POST /v2/sso/links。参数请填「环境」变量，不要写在本说明里。",
  folderId,
  priority: 1,
  tags: ["sso", "full", "q3-sp4"],
  steps,
};

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, JSON.stringify(payload), "utf8");
console.log("http=" + httpN + " groups=" + steps.length + " bytes=" + fs.statSync(outPath).size);
