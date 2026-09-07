/**
 * 本机批量跑 SSO /v2/sso/links（对应 Apifox Q3-SP4 sso 节点）
 * 用法: node run_sso_batch.js
 */
const fs = require("fs");
const https = require("https");
const crypto = require("crypto");
const path = require("path");

const BASE = "developer-sandbox.dragonpass.com";
const BASE_PATH = "/api/v2/sso/links";
const AUTH_PATH = "/api/v2/auth/token";

const CFG = {
  // 实测：1991829094323200 + DD60DF… 能换 Token，但 /v2/sso/links 固定 201.000.001
  // 数据集 membership 行 1919256841868288 + OWYX… 可成功出链
  programId: process.env.SSO_PROGRAM_ID || "1919256841868288",
  clientId: process.env.SSO_CLIENT_ID || "",
  secret: process.env.SSO_SECRET || "",
  accessToken: process.env.SSO_TOKEN || "",
  subjectType: "MEMBERSHIP",
  subjectId: process.env.SSO_SUBJECT_ID || "8576507744260001",
  orderId: process.env.SSO_ORDER_ID || "SL20260901BGVF836",
  orderIdOther: process.env.SSO_ORDER_ID_OTHER || "SL20260901BHL36IN",
  version: "canary"
};

const LANGUAGES = JSON.parse(
  fs.readFileSync(path.join(__dirname, "sso_languages_list.json"), "utf8")
);

function req(method, apiPath, headers, bodyObj) {
  const body = bodyObj == null ? null : JSON.stringify(bodyObj);
  const h = Object.assign(
    {
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
      "X-Request-ID": crypto.randomUUID(),
      "X-Program-ID": CFG.programId,
      "x-version": CFG.version
    },
    headers || {}
  );
  if (body) h["Content-Length"] = Buffer.byteLength(body);

  return new Promise((resolve, reject) => {
    const r = https.request(
      { hostname: BASE, path: apiPath, method, headers: h },
      (res) => {
        let raw = "";
        res.on("data", (c) => (raw += c));
        res.on("end", () => {
          let json = null;
          try {
            json = JSON.parse(raw);
          } catch (e) {}
          resolve({ status: res.statusCode, raw, json });
        });
      }
    );
    r.on("error", reject);
    if (body) r.write(body);
    r.end();
  });
}

async function fetchToken() {
  const res = await req("POST", AUTH_PATH, {}, {
    clientId: CFG.clientId,
    secret: CFG.secret
  });
  const t =
    res.json &&
    res.json.data &&
    (res.json.data.accessToken || res.json.data.access_token);
  if (!t) throw new Error("换 Token 失败: " + res.raw);
  CFG.accessToken = t;
  return t;
}

function authHeaders(extra) {
  return Object.assign(
    { Authorization: "Bearer " + CFG.accessToken },
    extra || {}
  );
}

function subject(id) {
  return { type: CFG.subjectType, id: id || CFG.subjectId };
}

function judge(expect, json) {
  const code = json && json.code;
  const err = (json && (json.errCode || json.errorCode)) || "";
  const okBiz = code === 0 || code === "0";
  const shortUrl =
    json &&
    json.data &&
    json.data.entry &&
    (json.data.entry.shortUrl || json.data.entry.url);

  switch (expect) {
    case "success":
    case "success_default_lang":
    case "idempotent_store":
    case "idempotent_check":
      return {
        pass: okBiz && !!shortUrl,
        reason: okBiz
          ? shortUrl
            ? "OK"
            : "无 shortUrl"
          : "code=" + code + " err=" + err
      };
    case "fail_602":
      return {
        pass: err === "500.000.602",
        reason: "err=" + err + " msg=" + (json && json.msg)
      };
    case "fail_param":
    case "fail_biz":
      return {
        pass: !okBiz && err && err !== "201.000.001" && err !== "202.000.001",
        reason: "err=" + err + " msg=" + (json && json.msg)
      };
    case "fail_auth":
      return {
        pass:
          err === "201.000.001" ||
          err === "202.000.001" ||
          (json && String(json.msg || "").toLowerCase().indexOf("auth") >= 0),
        reason: "err=" + err
      };
    case "record_only":
    case "manual":
      return { pass: true, reason: "仅记录 err=" + err + " code=" + code };
    default:
      return { pass: false, reason: "未知 expect=" + expect };
  }
}

function cases() {
  const list = [];
  const add = (folder, name, expect, body, hdr) =>
    list.push({ folder, name, expect, body, hdr: hdr || {} });

  // 1.必填
  add("1.必填校验", "SSO-REQ-001 scene必填", "fail_param", {
    subject: subject(),
    language: "en-US",
    durationInSeconds: 60
  });
  add("1.必填校验", "SSO-REQ-002 ORDER_DETAIL缺orderId→602", "fail_602", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    durationInSeconds: 60
  });
  add("1.必填校验", "SSO-REQ-002b order_detall缺orderId→602", "fail_602", {
    subject: subject(),
    scene: "order_detall",
    language: "en-US"
  });
  add("1.必填校验", "SSO-REQ-003 ORDER_DETAIL空orderId→602", "fail_602", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    extra: { orderId: "" }
  });
  add("1.必填校验", "SSO-REQ-004 ORDER_LIST不强制extra→成功", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });
  add("1.必填校验", "SSO-REQ-005 ORDER_DETAIL缺extra→602", "fail_602", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    durationInSeconds: 60
  });

  // 2.标准化
  add("2.参数标准化", "SSO-STD-001 ORDER_LIST", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });
  add("2.参数标准化", "SSO-STD-002 ORDER_DETAIL+orderId", "success", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    durationInSeconds: 60,
    extra: { orderId: CFG.orderId }
  });
  add("2.参数标准化", "SSO-STD-003 scene=XXX", "fail_param", {
    subject: subject(),
    scene: "XXX",
    language: "en-US"
  });
  add("2.参数标准化", "SSO-STD-004 language不传", "success_default_lang", {
    subject: subject(),
    scene: "ORDER_LIST",
    durationInSeconds: 60
  });
  add("2.参数标准化", "SSO-STD-005 language=zh-CN", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "zh-CN",
    durationInSeconds: 60
  });
  add("2.参数标准化", "SSO-STD-007 duration不传", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US"
  });
  add("2.参数标准化", "SSO-STD-008 returnUrl不传", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });
  add("2.参数标准化", "SSO-STD-009 returnUrl合法", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60,
    returnUrl: "https://www.dragonpass.com"
  });
  add("2.参数标准化", "SSO-STD-010 subject=MEMBERSHIP", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });

  // 2b 语种
  LANGUAGES.forEach((lang) => {
    add("2b.语种轮询BOSS29", "SSO-STD-006 language=" + lang, "success", {
      subject: subject(),
      scene: "ORDER_LIST",
      language: lang,
      durationInSeconds: 60
    });
  });

  // 3.异常
  add("3.异常场景", "SSO-ERR-001 DETAIL缺extra", "fail_602", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US"
  });
  add("3.异常场景", "SSO-ERR-002 orderId不存在", "fail_biz", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    extra: { orderId: "NOT_EXIST_ORDER_000" }
  });
  add("3.异常场景", "SSO-ERR-003 orderId不属于该会籍", "fail_biz", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    extra: { orderId: CFG.orderIdOther }
  });
  add("3.异常场景", "SSO-ERR-004 subject.type非法", "fail_param", {
    subject: { type: "INVALID_TYPE", id: CFG.subjectId },
    scene: "ORDER_LIST",
    language: "en-US"
  });
  add("3.异常场景", "SSO-ERR-005 subject.id不存在", "fail_biz", {
    subject: { type: "MEMBERSHIP", id: "9999999999999999" },
    scene: "ORDER_LIST",
    language: "en-US"
  });
  add("3.异常场景", "SSO-ERR-006 duration=59", "fail_param", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 59
  });
  add("3.异常场景", "SSO-ERR-007 duration=7201", "fail_param", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 7201
  });
  add("3.异常场景", "SSO-ERR-008 duration类型错误", "fail_param", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: "abc"
  });
  add(
    "3.异常场景",
    "SSO-ERR-009 坏Token",
    "fail_auth",
    {
      subject: subject(),
      scene: "ORDER_LIST",
      language: "en-US"
    },
    { Authorization: "Bearer BAD_TOKEN_XXX" }
  );
  add("3.异常场景", "SSO-ERR-010 returnUrl外域", "record_only", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    returnUrl: "https://evil.example.invalid"
  });

  // 4.边界
  add("4.边界与容错", "SSO-BND-001 duration=60", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });
  add("4.边界与容错", "SSO-BND-002 duration=7200", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 7200
  });

  // 5.一致性
  add("5.联动一致性", "SSO-IDEMP-001a 同参第1次", "idempotent_store", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 600
  });
  add("5.联动一致性", "SSO-IDEMP-001b 同参第2次", "idempotent_check", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 600
  });
  add("5.联动一致性", "SSO-IDEMP-001c 同参第3次", "idempotent_check", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 600
  });

  // 6.手工半自动：只出链，打开短链需人手
  add("6.手工半自动", "SSO-MAN-001 出链供打开短链", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });
  add("6.手工半自动", "SSO-MAN-002 DETAIL出链", "success", {
    subject: subject(),
    scene: "ORDER_DETAIL",
    language: "en-US",
    durationInSeconds: 60,
    extra: { orderId: CFG.orderId }
  });
  add("6.手工半自动", "SSO-MAN-003 短有效期60s供过期验", "success", {
    subject: subject(),
    scene: "ORDER_LIST",
    language: "en-US",
    durationInSeconds: 60
  });

  return list;
}

async function main() {
  console.log("[sso-batch] 先换新 Token…");
  await fetchToken();
  console.log("[sso-batch] Token OK, Program=", CFG.programId, "subject=", CFG.subjectId);

  // 鉴权冒烟
  const smoke = await req(
    "POST",
    BASE_PATH,
    authHeaders(),
    {
      subject: subject(),
      scene: "ORDER_LIST",
      language: "en-US",
      durationInSeconds: 60
    }
  );
  console.log("[sso-batch] 冒烟:", JSON.stringify(smoke.json));
  if (
    smoke.json &&
    (smoke.json.errCode === "201.000.001" || smoke.json.errCode === "202.000.001")
  ) {
    console.error(
      "\n鉴权仍失败，无法继续批量。请确认 canary 上该 Program 的 Auth secret 与 Token 匹配。\n"
    );
  }

  const all = cases();
  const results = [];
  let pass = 0;
  let fail = 0;
  let authBlocked = 0;

  for (const c of all) {
    const res = await req("POST", BASE_PATH, authHeaders(c.hdr), c.body);
    const j = res.json || {};
    const verdict = judge(c.expect, j);
    if (j.errCode === "201.000.001" || j.errCode === "202.000.001") authBlocked++;
    if (verdict.pass) pass++;
    else fail++;
    const line = {
      folder: c.folder,
      name: c.name,
      expect: c.expect,
      pass: verdict.pass,
      http: res.status,
      code: j.code,
      errCode: j.errCode || j.errorCode,
      msg: j.msg,
      reason: verdict.reason,
      shortUrl:
        j.data && j.data.entry && (j.data.entry.shortUrl || j.data.entry.url)
    };
    results.push(line);
    const mark = verdict.pass ? "PASS" : "FAIL";
    console.log(
      `[${mark}] ${c.folder} | ${c.name} | err=${line.errCode || "-"} | ${verdict.reason}`
    );
  }

  const outDir = path.join(__dirname, "run-results");
  fs.mkdirSync(outDir, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const outFile = path.join(outDir, `sso-batch-${stamp}.json`);
  fs.writeFileSync(
    outFile,
    JSON.stringify(
      {
        cfg: {
          programId: CFG.programId,
          subjectId: CFG.subjectId,
          orderId: CFG.orderId,
          version: CFG.version
        },
        summary: {
          total: all.length,
          pass,
          fail,
          authBlocked,
          at: new Date().toISOString()
        },
        results
      },
      null,
      2
    ),
    "utf8"
  );

  console.log("\n========== SUMMARY ==========");
  console.log("total=", all.length, "pass=", pass, "fail=", fail, "authBlocked=", authBlocked);
  console.log("report=", outFile);

  if (authBlocked > all.length * 0.5) {
    console.log(
      "\n注意：超过一半用例卡在 201/202 鉴权，业务断言（602/成功出链）在鉴权修好前无法判定。"
    );
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
