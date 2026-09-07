/**
 * 按模板在 P1 下建功能夹/按XMind用例，并 Push 场景步骤。
 * 用法: node push_all.js
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const PROJECT = "346275";
const BRANCH = "ai/apifox-cli-sync";
const API = "https://apifox.dragonpass.com.cn";
const P1 = 350027;
const P0_OTHERS = 350026;
const cmd = path.join(process.env.APPDATA, "npm", "apifox.cmd");
const genDir = path.join(__dirname, "generated");
const tmpDir = path.join(__dirname, "generated", "_cli");
fs.mkdirSync(tmpDir, { recursive: true });

function run(args) {
  const r = spawnSync(cmd, args.concat(["--project", PROJECT, "--branch", BRANCH, "--api-base-url", API]), {
    encoding: "utf8",
    shell: true,
  });
  const out = r.stdout || "";
  let json = {};
  try {
    json = JSON.parse(out);
  } catch (e) {
    const i = out.indexOf("{");
    if (i >= 0) json = JSON.parse(out.slice(i));
  }
  if (r.status !== 0 || json.success === false) {
    throw new Error("apifox failed " + args.join(" ") + "\n" + (out || r.stderr || "").slice(0, 1500));
  }
  return json;
}

function writeJson(name, obj) {
  const p = path.join(tmpDir, name);
  fs.writeFileSync(p, JSON.stringify(obj), "utf8");
  return p;
}

function createFolder(name, parentId) {
  const file = writeJson("folder-" + name.replace(/[^\w\u4e00-\u9fff]+/g, "-") + "-" + parentId + ".json", {
    name,
    type: "test-scenario",
    parentId,
    projectId: Number(PROJECT),
  });
  const j = run(["folder", "create", "--type", "test-scenario", "--file", file]);
  const id = j.data && (j.data.id || j.data.folderId);
  if (!id) throw new Error("no folder id for " + name + " " + JSON.stringify(j).slice(0, 400));
  console.log("folder", id, name, "parent", parentId);
  return Number(id);
}

function createScenario(metaFile, folderId) {
  const raw = JSON.parse(fs.readFileSync(path.join(genDir, metaFile), "utf8"));
  const createFile = writeJson("sc-create-" + metaFile, {
    name: raw.name,
    description: raw.description,
    folderId,
    priority: raw.priority,
    tags: raw.tags,
  });
  const j = run(["test-scenario", "create", "--file", createFile]);
  const id = j.data && j.data.id;
  if (!id) throw new Error("no scenario id " + metaFile + " " + JSON.stringify(j).slice(0, 400));
  raw.folderId = folderId;
  const updateFile = writeJson("sc-update-" + metaFile, raw);
  run(["test-scenario", "update", String(id), "--file", updateFile]);
  console.log("scenario", id, raw.name, "folder", folderId);
  return id;
}

function ensureFeature(parentId, featureName) {
  const feat = createFolder(featureName, parentId);
  const xmind = createFolder("按XMind用例", feat);
  return { feat, xmind };
}

const map = {};
map.ft = ensureFeature(P1, "FT可用性");
map.pay = ensureFeature(P1, "支付链接");
map.auth = ensureFeature(P1, "Auth双密钥");

const ft01 = createFolder("01 过去时间拦截", map.ft.xmind);
const ft02 = createFolder("02 错误码迁移039-044", map.ft.xmind);
const ft03 = createFolder("03 补充错误码045", map.ft.xmind);
const ft04 = createFolder("04 时区特殊与空时区", map.ft.xmind);
const pay01 = createFolder("01 语种language校验", map.pay.xmind);
const pay02 = createFolder("02 有效期durationInSeconds校验", map.pay.xmind);
const auth02 = createFolder("02 两套token跑通链路", map.auth.xmind);
const auth03 = createFolder("03 RS256与HS256判定组合", map.auth.xmind);
const auth04 = createFolder("04 密钥配置增删改", map.auth.xmind);

const ids = {
  "ft-01.json": createScenario("ft-01.json", ft01),
  "ft-02.json": createScenario("ft-02.json", ft02),
  "ft-03.json": createScenario("ft-03.json", ft03),
  "ft-04.json": createScenario("ft-04.json", ft04),
  "pay-01.json": createScenario("pay-01.json", pay01),
  "pay-02.json": createScenario("pay-02.json", pay02),
  "auth-02.json": createScenario("auth-02.json", auth02),
  "auth-03.json": createScenario("auth-03.json", auth03),
  "auth-04.json": createScenario("auth-04.json", auth04),
  "p0-ft.json": createScenario("p0-ft.json", P0_OTHERS),
  "p0-pay.json": createScenario("p0-pay.json", P0_OTHERS),
  "p0-sso.json": createScenario("p0-sso.json", P0_OTHERS),
};

fs.writeFileSync(path.join(genDir, "pushed-ids.json"), JSON.stringify({ map, folders: { ft01, ft02, ft03, ft04, pay01, pay02, auth02, auth03, auth04 }, ids }, null, 2));
console.log("DONE", JSON.stringify(ids, null, 2));
