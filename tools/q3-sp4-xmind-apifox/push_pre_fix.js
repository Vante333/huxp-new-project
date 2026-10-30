/**
 * 更新 FT02/03 + 支付/SSO PRE 验收场景到 Apifox AI 分支。
 * 用法: node push_pre_fix.js
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const PROJECT = "346275";
const BRANCH = "ai/apifox-cli-sync";
const API = "https://apifox.dragonpass.com.cn";
const P0_OTHERS = 350026;
const PAY_XMIND = 350772;
const cmd = path.join(process.env.APPDATA, "npm", "apifox.cmd");
const genDir = path.join(__dirname, "generated");
const tmpDir = path.join(genDir, "_cli");
fs.mkdirSync(tmpDir, { recursive: true });

const EXISTING = {
  "ft-02.json": 370381,
  "ft-03.json": 370382,
  "p0-pay.json": 370390,
  "p0-sso.json": 370391,
};

function run(args) {
  const r = spawnSync(cmd, args.concat(["--project", PROJECT, "--branch", BRANCH, "--api-base-url", API]), {
    encoding: "utf8",
    shell: true,
    maxBuffer: 20 * 1024 * 1024,
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
    throw new Error("apifox failed " + args.join(" ") + "\n" + (out || r.stderr || "").slice(0, 2000));
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
  if (!id) throw new Error("no folder id for " + name);
  console.log("folder", id, name);
  return Number(id);
}

function updateScenario(id, metaFile) {
  const raw = JSON.parse(fs.readFileSync(path.join(genDir, metaFile), "utf8"));
  const updateFile = writeJson("sc-update-" + metaFile, raw);
  run(["test-scenario", "update", String(id), "--file", updateFile]);
  console.log("updated", id, raw.name);
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
  if (!id) throw new Error("no scenario id " + metaFile);
  raw.folderId = folderId;
  const updateFile = writeJson("sc-update-" + metaFile, raw);
  run(["test-scenario", "update", String(id), "--file", updateFile]);
  console.log("created", id, raw.name);
  return id;
}

for (const [file, id] of Object.entries(EXISTING)) {
  updateScenario(id, file);
}

const payPreFolder = createFolder("03 PRE验收", PAY_XMIND);
const ssoFeat = createFolder("sso免登录短链接", 350027);
const ssoXmind = createFolder("按XMind用例", ssoFeat);
const ssoPreFolder = createFolder("01 PRE验收", ssoXmind);

const payPreId = createScenario("pay-pre.json", payPreFolder);
const ssoPreId = createScenario("sso-pre.json", ssoPreFolder);

const idsPath = path.join(genDir, "pushed-ids.json");
const ids = JSON.parse(fs.readFileSync(idsPath, "utf8"));
ids.ids["支付链接 · PRE验收"] = payPreId;
ids.ids["SSO免登短链 · PRE验收"] = ssoPreId;
ids.folders.payPre = payPreFolder;
ids.folders.ssoPre = ssoPreFolder;
fs.writeFileSync(idsPath, JSON.stringify(ids, null, 2));
console.log("DONE", { payPreId, ssoPreId, updated: Object.values(EXISTING) });
