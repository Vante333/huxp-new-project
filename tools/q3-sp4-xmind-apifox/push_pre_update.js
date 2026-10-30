/**
 * 只更新已有 PRE 相关场景，不新建目录。
 * 用法: node push_pre_update.js
 */
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const PROJECT = "346275";
const BRANCH = "ai/apifox-cli-sync";
const API = "https://apifox.dragonpass.com.cn";
const cmd = path.join(process.env.APPDATA, "npm", "apifox.cmd");
const genDir = path.join(__dirname, "generated");
const tmpDir = path.join(genDir, "_cli");
fs.mkdirSync(tmpDir, { recursive: true });

const EXISTING = {
  "ft-01.json": 370380,
  "ft-02.json": 370381,
  "ft-03.json": 370382,
  "ft-04.json": 370383,
  "pay-01.json": 370384,
  "pay-02.json": 370385,
  "p0-ft.json": 370389,
  "p0-pay.json": 370390,
  "p0-sso.json": 370391,
  "pay-pre.json": 370480,
  "sso-pre.json": 370481,
};

function run(args, withProject) {
  const extra = withProject === false ? [] : ["--project", PROJECT, "--branch", BRANCH, "--api-base-url", API];
  const r = spawnSync(cmd, args.concat(extra), {
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

for (const [file, id] of Object.entries(EXISTING)) {
  const raw = JSON.parse(fs.readFileSync(path.join(genDir, file), "utf8"));
  const updateFile = path.join(tmpDir, "sc-update-" + file);
  fs.writeFileSync(updateFile, JSON.stringify(raw), "utf8");
  try {
    run(["cli-schema", "validate", "test-scenario-update", "--file", updateFile], false);
    run(["test-scenario", "update", String(id), "--file", updateFile]);
    console.log("updated", id, raw.name);
  } catch (e) {
    const msg = String(e.message || e);
    if (msg.indexOf("404000") >= 0 || msg.indexOf("Not found") >= 0) {
      console.log("SKIP missing", id, raw.name);
      continue;
    }
    throw e;
  }
}

console.log("DONE", Object.keys(EXISTING).length);
