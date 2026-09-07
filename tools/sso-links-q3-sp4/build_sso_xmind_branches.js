/**
 * 按 XMind「一、SSO免登短链」拆成 Apifox 自动化分支（E2E 模板：Auth + customHttp）。
 * 用法: node build_sso_xmind_branches.js <parentFolderId> <outDir>
 */
const fs = require("fs");
const path = require("path");

const PROJECT_ID = 346275;
const parentFolderId = Number(process.argv[2] || 0);
const outDir = process.argv[3];
if (!parentFolderId || !outDir) {
  console.error("usage: node build_sso_xmind_branches.js <parentFolderId> <outDir>");
  process.exit(1);
}

const dir = __dirname;
const collection = JSON.parse(
  fs.readFileSync(path.join(dir, "PAPI-SSO免登短链-全量自动化.postman_collection.json"), "utf8")
);
const helperPre = fs.readFileSync(path.join(dir, "apifox_pre_sso_full.js"), "utf8");
const helperPost = fs.readFileSync(path.join(dir, "apifox_post_sso_full.js"), "utf8");
const langs = JSON.parse(fs.readFileSync(path.join(dir, "sso_languages_list.json"), "utf8"));

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

function customHttp(httpN, { name, method, reqPath, headers, body, pre, post, extraAdv }) {
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
      advancedSettings: extraAdv || {},
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

function parseBody(it) {
  const raw = it.request && it.request.body && it.request.body.raw;
  if (!raw) {
    return {
      subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
      scene: "ORDER_LIST",
      language: "en-US",
      durationInSeconds: 1800,
    };
  }
  try {
    return JSON.parse(raw);
  } catch (e) {
    return raw;
  }
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
  "if (!_src) { console.log('[sso-xmind] 缺少 ssoFullPre，请先跑本场景 Auth'); }",
  "else { eval(_src); }",
].join("\n");

const LOADER_POST = [
  "var _src = '';",
  "try { _src = String(pm.environment.get('ssoFullPost') || pm.variables.get('ssoFullPost') || ''); } catch (eS) {}",
  "if (!_src) { pm.test('检查点 | 期望=已跑 Auth 写入断言脚本 | 实际=空', function () { pm.expect.fail('缺少 ssoFullPost'); }); }",
  "else { eval(_src); }",
].join("\n");

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
  "if (!pm.environment.get('sso_returnUrl_ok')) pm.environment.set('sso_returnUrl_ok', 'https://www.ly.com');",
  "if (!pm.environment.get('sso_returnUrl_bad')) pm.environment.set('sso_returnUrl_bad', 'https://evil.example.invalid');",
  "if (!pm.environment.get('sso_subject_id_missing')) pm.environment.set('sso_subject_id_missing', '0000000000000000');",
  "if (!pm.environment.get('sso_scene_bad')) pm.environment.set('sso_scene_bad', 'XXX');",
  "if (!String(pm.environment.get('clientId') || '')) pm.environment.set('clientId', String(pm.collectionVariables.get('clientId') || ''));",
  "if (!String(pm.environment.get('secret') || '')) pm.environment.set('secret', String(pm.collectionVariables.get('secret') || ''));",
  "pm.environment.set('ssoLangList', " + JSON.stringify(JSON.stringify(langs)) + ");",
  "pm.environment.set('ssoFullPre', " + JSON.stringify(helperPre) + ");",
  "pm.environment.set('ssoFullPost', " + JSON.stringify(helperPost) + ");",
  "try { pm.variables.set('ssoFullPre', pm.environment.get('ssoFullPre')); pm.variables.set('ssoFullPost', pm.environment.get('ssoFullPost')); } catch (eH) {}",
  "console.log('[sso-xmind] Auth 种子 ProgramID=' + pid + ' subject=' + pm.environment.get('sso_subject_id') + ' sso_orderId=' + (pm.environment.get('sso_orderId') || '(空)'));",
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

function authStep(n) {
  return customHttp(n, {
    name: "【换SSO Token】| SSO-N-001 | POST /v2/auth/token",
    method: "post",
    reqPath: "/v2/auth/token",
    headers: apiHeaders(false),
    body: { clientId: "{{clientId}}", secret: "{{secret}}" },
    pre: AUTH_PRE,
    post: AUTH_POST,
  });
}

function buildItems(folder, counter) {
  const children = [];
  for (const it of folder.item || []) {
    if (!it) continue;
    if (Array.isArray(it.item) && !it.request) {
      children.push(group(String(it.name || "group"), buildItems(it, counter)));
      continue;
    }
    if (!it.request) continue;
    counter.n += 1;
    const sets = extractCaseSets(eventExec(it, "prerequest"));
    children.push(
      customHttp(counter.n, {
        name: purposeName(it.name),
        method: (it.request.method || "POST").toLowerCase(),
        reqPath: "/v2/sso/links",
        headers: apiHeaders(true),
        body: parseBody(it),
        pre: [RESET_VARS, sets.join("\n"), LOADER_PRE].filter(Boolean).join("\n"),
        post: LOADER_POST,
      })
    );
  }
  return children;
}

function findFolder(pred) {
  return (collection.item || []).find((f) => f && pred(String(f.name || "")));
}

function scenarioPayload(folderId, name, tags, desc, steps) {
  return {
    name,
    description: desc,
    folderId,
    priority: 1,
    tags,
    steps,
  };
}

const DESC =
  "来源桌面《需求测试用例.xmind》→ 一、SSO免登短链。模板同一次性E2E：先 Auth 再业务。环境选 UAT（canary节点）。变量：ProgramID=1919256841868288、sso_subject_id=8576507744260001、sso_orderId=该会籍真实单号（详情/越权用）。密钥不要写在本说明。";

fs.mkdirSync(outDir, { recursive: true });

const manifest = [];

function writeScenario(key, folderName, scenarioName, tags, groupsOrFolders) {
  const counter = { n: 0 };
  counter.n += 1;
  const steps = [group("00 换 Token", [authStep(counter.n)])];
  for (const f of groupsOrFolders) {
    if (!f) continue;
    steps.push(group(String(f.name || "用例"), buildItems(f, counter)));
  }
  const file = path.join(outDir, key + ".json");
  const payload = scenarioPayload(parentFolderId, scenarioName, tags, DESC, steps);
  fs.writeFileSync(file, JSON.stringify(payload), "utf8");
  const httpCount = counter.n;
  manifest.push({ key, folderName, scenarioName, file, httpCount });
  console.log(key + " http=" + httpCount + " -> " + file);
}

writeScenario(
  "01-req",
  "01 必填校验",
  "SSO免登短链 · 01必填校验",
  ["sso", "xmind", "req"],
  [findFolder((n) => n.indexOf("1.必填") >= 0)]
);
writeScenario(
  "02-std",
  "02 参数标准化",
  "SSO免登短链 · 02参数标准化",
  ["sso", "xmind", "std"],
  [
    findFolder((n) => n.indexOf("2.参数标准化") >= 0),
    findFolder((n) => n.indexOf("2b.语种") >= 0),
  ]
);
writeScenario(
  "03-err",
  "03 异常场景",
  "SSO免登短链 · 03异常场景",
  ["sso", "xmind", "err"],
  [findFolder((n) => n.indexOf("3.异常") >= 0)]
);
writeScenario(
  "04-bnd",
  "04 边界与容错",
  "SSO免登短链 · 04边界与容错",
  ["sso", "xmind", "bnd"],
  [findFolder((n) => n.indexOf("4.边界") >= 0)]
);
writeScenario(
  "05-idemp",
  "05 短链一致性",
  "SSO免登短链 · 05短链一致性",
  ["sso", "xmind", "idemp"],
  [findFolder((n) => n.indexOf("5.短链一致性") >= 0)]
);
writeScenario(
  "06-open",
  "06 打开短链与分页",
  "SSO免登短链 · 06打开短链与分页",
  ["sso", "xmind", "page"],
  [findFolder((n) => n.indexOf("6.手工") >= 0)]
);

fs.writeFileSync(
  path.join(outDir, "manifest.json"),
  JSON.stringify({ parentFolderId, manifest }, null, 2),
  "utf8"
);

const folderCreates = [{ name: "按XMind用例", type: "test-scenario", parentId: parentFolderId, projectId: PROJECT_ID }];
for (const m of manifest) {
  folderCreates.push({ name: m.folderName, type: "test-scenario", parentId: 0, projectId: PROJECT_ID, _key: m.key });
}
fs.writeFileSync(path.join(outDir, "folder-creates.json"), JSON.stringify(folderCreates, null, 2), "utf8");
console.log("manifest=" + manifest.length);
