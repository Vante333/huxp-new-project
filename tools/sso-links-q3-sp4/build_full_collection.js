const fs = require("fs");
const path = __dirname;

const LANGUAGES = JSON.parse(fs.readFileSync(path + "/sso_languages_list.json", "utf8"));
const pre = fs.readFileSync(path + "/apifox_pre_sso_full.js", "utf8").split(/\r?\n/);
const post = fs.readFileSync(path + "/apifox_post_sso_full.js", "utf8").split(/\r?\n/);

function setupLines(opts) {
  const lines = [];
  Object.keys(opts).forEach(function (k) {
    if (k === "_body") return;
    const v = opts[k];
    if (v === true) lines.push("pm.variables.set('" + k + "','true');");
    else if (v === false) lines.push("pm.variables.set('" + k + "','false');");
    else if (v === null || v === undefined) lines.push("pm.variables.set('" + k + "','');");
    else lines.push("pm.variables.set('" + k + "'," + JSON.stringify(String(v)) + ");");
  });
  return lines;
}

function bodyRaw(obj) {
  return JSON.stringify(obj, null, 2);
}

function baseSubject() {
  return {
    type: "{{sso_subject_type}}",
    id: "{{sso_subject_id}}"
  };
}

function makeItem(name, opts, desc, bodyObj) {
  const raw =
    bodyObj !== undefined
      ? bodyRaw(bodyObj)
      : bodyRaw({
          subject: baseSubject(),
          scene: "ORDER_LIST",
          language: "en-US"
        });

  return {
    name: name,
    event: [
      {
        listen: "prerequest",
        script: { type: "text/javascript", exec: setupLines(opts).concat(pre) }
      },
      {
        listen: "test",
        script: { type: "text/javascript", exec: post }
      }
    ],
    request: {
      method: "POST",
      header: [
        { key: "Content-Type", value: "application/json" },
        { key: "Authorization", value: "Bearer {{access_token}}" },
        { key: "X-Program-ID", value: "{{Program-ID}}" }
      ],
      body: {
        mode: "raw",
        raw: raw,
        options: { raw: { language: "json" } }
      },
      url: {
        raw: "{{baseUrl}}/v2/sso/links",
        host: ["{{baseUrl}}"],
        path: ["v2", "sso", "links"]
      },
      description: desc || name
    }
  };
}

const folder1 = {
  name: "1.必填校验",
  item: [
    makeItem(
      "SSO-REQ-001 scene必填",
      {
        case_id: "SSO-REQ-001",
        sso_omit_scene: true,
        sso_scene: "",
        language: "en-US",
        sso_expect_type: "fail_param"
      },
      "不传 scene，预期失败",
      {
        subject: baseSubject(),
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-REQ-002 ORDER_DETAIL缺orderId→602",
      {
        case_id: "SSO-REQ-002",
        sso_scene: "ORDER_DETAIL",
        sso_omit_extra: true,
        language: "en-US",
        sso_expect_type: "fail_602",
        sso_expect_errCode: "500.000.602"
      },
      "scene=ORDER_DETAIL，不传 extra.orderId，预期 500.000.602。需有效 Token，否则会先报 201/401。",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-REQ-002b order_detall缺orderId→602",
      {
        case_id: "SSO-REQ-002b",
        sso_scene: "order_detall",
        sso_omit_extra: true,
        language: "en-US",
        sso_expect_type: "fail_602",
        sso_expect_errCode: "500.000.602"
      },
      "脑图小写笔误 scene=order_detall",
      {
        subject: baseSubject(),
        scene: "order_detall",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-REQ-003 ORDER_DETAIL空orderId→602",
      {
        case_id: "SSO-REQ-003",
        sso_scene: "ORDER_DETAIL",
        sso_empty_orderId: true,
        language: "en-US",
        sso_expect_type: "fail_602",
        sso_expect_errCode: "500.000.602"
      },
      "extra.orderId 为空字符串",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        extra: { orderId: "" }
      }
    ),
    makeItem(
      "SSO-REQ-004 ORDER_LIST不强制extra→成功",
      {
        case_id: "SSO-REQ-004",
        sso_scene: "ORDER_LIST",
        sso_omit_extra: true,
        language: "en-US",
        sso_expect_type: "success",
        sso_expect_scene_echo: "ORDER_LIST"
      },
      "不传 extra，成功出短链",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-REQ-005 ORDER_DETAIL缺extra整对象→602",
      {
        case_id: "SSO-REQ-005",
        sso_scene: "ORDER_DETAIL",
        sso_omit_extra: true,
        language: "en-US",
        sso_expect_type: "fail_602",
        sso_expect_errCode: "500.000.602"
      },
      "不传 extra",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 60
      }
    )
  ]
};

const folder2 = {
  name: "2.参数标准化校验",
  item: [
    makeItem(
      "SSO-STD-001 scene=ORDER_LIST",
      {
        case_id: "SSO-STD-001",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "60",
        sso_expect_type: "success",
        sso_expect_scene_echo: "ORDER_LIST"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-STD-002 scene=ORDER_DETAIL+orderId",
      {
        case_id: "SSO-STD-002",
        sso_scene: "ORDER_DETAIL",
        language: "en-US",
        sso_durationInSeconds: "60",
        sso_expect_type: "success",
        sso_expect_scene_echo: "ORDER_DETAIL"
      },
      "需环境 sso_orderId",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 60,
        extra: { orderId: "{{sso_orderId}}" }
      }
    ),
    makeItem(
      "SSO-STD-003 scene非法值XXX",
      {
        case_id: "SSO-STD-003",
        sso_use_bad_scene: true,
        language: "en-US",
        sso_expect_type: "fail_param"
      },
      "",
      {
        subject: baseSubject(),
        scene: "XXX",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-STD-004 language不传→默认en-US",
      {
        case_id: "SSO-STD-004",
        sso_scene: "ORDER_LIST",
        sso_omit_language: true,
        sso_expect_type: "success_default_lang",
        sso_expect_language_echo: "en-US"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-STD-005 language=zh-CN",
      {
        case_id: "SSO-STD-005",
        sso_scene: "ORDER_LIST",
        language: "zh-CN",
        sso_expect_type: "success",
        sso_expect_language_echo: "zh-CN"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "zh-CN",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-STD-007 duration不传",
      {
        case_id: "SSO-STD-007",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_omit_duration: true,
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-STD-008 returnUrl不传",
      {
        case_id: "SSO-STD-008",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_omit_returnUrl: true,
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-STD-009 returnUrl合法",
      {
        case_id: "SSO-STD-009",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_returnUrl: "https://www.dragonpass.com",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60,
        returnUrl: "https://www.dragonpass.com"
      }
    ),
    makeItem(
      "SSO-STD-010 subject=MEMBERSHIP",
      {
        case_id: "SSO-STD-010",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    )
  ]
};

const folderLang = {
  name: "2b.语种轮询BOSS29(SSO-STD-006)",
  item: LANGUAGES.map(function (lang) {
    return makeItem(
      "SSO-STD-006 language=" + lang,
      {
        case_id: "SSO-STD-006_" + lang,
        sso_scene: "ORDER_LIST",
        language: lang,
        sso_durationInSeconds: "60",
        sso_expect_type: "success",
        sso_expect_language_echo: lang
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: lang,
        durationInSeconds: 60
      }
    );
  })
};

const folder3 = {
  name: "3.异常场景",
  item: [
    makeItem(
      "SSO-ERR-001 ORDER_DETAIL缺extra",
      {
        case_id: "SSO-ERR-001",
        sso_scene: "ORDER_DETAIL",
        sso_omit_extra: true,
        language: "en-US",
        sso_expect_type: "fail_602"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-ERR-002 orderId不存在",
      {
        case_id: "SSO-ERR-002",
        sso_scene: "ORDER_DETAIL",
        sso_orderId: "NOT_EXIST_ORDER_000",
        language: "en-US",
        sso_expect_type: "fail_biz"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        extra: { orderId: "NOT_EXIST_ORDER_000" }
      }
    ),
    makeItem(
      "SSO-ERR-003 orderId不属于该会籍",
      {
        case_id: "SSO-ERR-003",
        sso_scene: "ORDER_DETAIL",
        sso_use_other_order: true,
        language: "en-US",
        sso_expect_type: "fail_biz"
      },
      "需 sso_orderId_other",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        extra: { orderId: "{{sso_orderId_other}}" }
      }
    ),
    makeItem(
      "SSO-ERR-004 subject.type非法",
      {
        case_id: "SSO-ERR-004",
        sso_scene: "ORDER_LIST",
        sso_use_bad_subject_type: true,
        language: "en-US",
        sso_expect_type: "fail_param"
      },
      "",
      {
        subject: { type: "INVALID_TYPE", id: "{{sso_subject_id}}" },
        scene: "ORDER_LIST",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-ERR-005 subject.id不存在",
      {
        case_id: "SSO-ERR-005",
        sso_scene: "ORDER_LIST",
        sso_use_missing_subject_id: true,
        language: "en-US",
        sso_expect_type: "fail_biz"
      },
      "",
      {
        subject: { type: "MEMBERSHIP", id: "9999999999999999" },
        scene: "ORDER_LIST",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-ERR-006 duration=59",
      {
        case_id: "SSO-ERR-006",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "59",
        sso_expect_type: "fail_param"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 59
      }
    ),
    makeItem(
      "SSO-ERR-007 duration=7201",
      {
        case_id: "SSO-ERR-007",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "7201",
        sso_expect_type: "fail_param"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 7201
      }
    ),
    makeItem(
      "SSO-ERR-008 duration类型错误",
      {
        case_id: "SSO-ERR-008",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_duration_as_string_abc: true,
        sso_durationInSeconds: "abc",
        sso_expect_type: "fail_param"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: "abc"
      }
    ),
    makeItem(
      "SSO-ERR-009 坏Token",
      {
        case_id: "SSO-ERR-009",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_bad_auth: true,
        sso_expect_type: "fail_auth"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US"
      }
    ),
    makeItem(
      "SSO-ERR-010 returnUrl外域",
      {
        case_id: "SSO-ERR-010",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_use_bad_returnUrl: true,
        sso_expect_type: "record_only"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        returnUrl: "https://evil.example.invalid"
      }
    )
  ]
};

const folder4 = {
  name: "4.边界与容错",
  item: [
    makeItem(
      "SSO-BND-001 duration=60",
      {
        case_id: "SSO-BND-001",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "60",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-BND-002 duration=7200",
      {
        case_id: "SSO-BND-002",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "7200",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 7200
      }
    )
  ]
};

const folder5 = {
  name: "5.短链一致性(接口层)",
  item: [
    makeItem(
      "SSO-IDEMP-001a 同参第1次store",
      {
        case_id: "SSO-IDEMP-001a",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "idempotent_store"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 600
      }
    ),
    makeItem(
      "SSO-IDEMP-001b 同参第2次check",
      {
        case_id: "SSO-IDEMP-001b",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "idempotent_check"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 600
      }
    ),
    makeItem(
      "SSO-IDEMP-001c 同参第3次check",
      {
        case_id: "SSO-IDEMP-001c",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "idempotent_check"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 600
      }
    ),
    makeItem(
      "SSO-IDEMP-003a DETAIL同参store",
      {
        case_id: "SSO-IDEMP-003a",
        sso_scene: "ORDER_DETAIL",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "idempotent_store"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 600,
        extra: { orderId: "{{sso_orderId}}" }
      }
    ),
    makeItem(
      "SSO-IDEMP-003b DETAIL同参check",
      {
        case_id: "SSO-IDEMP-003b",
        sso_scene: "ORDER_DETAIL",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "idempotent_check"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 600,
        extra: { orderId: "{{sso_orderId}}" }
      }
    ),
    makeItem(
      "SSO-IDEMP-004 改scene对照",
      {
        case_id: "SSO-IDEMP-004",
        sso_scene: "ORDER_DETAIL",
        language: "en-US",
        sso_expect_type: "record_only"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        extra: { orderId: "{{sso_orderId}}" }
      }
    )
  ]
};

const folder6 = {
  name: "6.手工-打开短链/分页/过期(半自动)",
  item: [
    makeItem(
      "SSO-E2E-001 生成LIST短链",
      {
        case_id: "SSO-E2E-001",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "success"
      },
      "打开 sso_last_shortUrl 验 /standard-public/",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 600
      }
    ),
    makeItem(
      "SSO-E2E-002 生成DETAIL短链",
      {
        case_id: "SSO-E2E-002",
        sso_scene: "ORDER_DETAIL",
        language: "en-US",
        sso_durationInSeconds: "600",
        sso_expect_type: "success"
      },
      "打开短链验 /standard-lfd/",
      {
        subject: baseSubject(),
        scene: "ORDER_DETAIL",
        language: "en-US",
        durationInSeconds: 600,
        extra: { orderId: "{{sso_orderId}}" }
      }
    ),
    makeItem(
      "SSO-BND-003 生成60s短链(未过期打开)",
      {
        case_id: "SSO-BND-003",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "60",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-BND-004 生成60s短链(过期后打开)",
      {
        case_id: "SSO-BND-004",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_durationInSeconds: "60",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-E2E-004 访客模式不传subject",
      {
        case_id: "SSO-E2E-004",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_omit_subject: true,
        sso_expect_type: "record_only"
      },
      "",
      {
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 60
      }
    ),
    makeItem(
      "SSO-PAGE-001 生成LIST供分页观察",
      {
        case_id: "SSO-PAGE-001",
        sso_scene: "ORDER_LIST",
        language: "en-US",
        sso_expect_type: "success"
      },
      "",
      {
        subject: baseSubject(),
        scene: "ORDER_LIST",
        language: "en-US",
        durationInSeconds: 600
      }
    )
  ]
};

const collection = {
  info: {
    _postman_id: "papi-sso-links-full-suite-v2",
    name: "PAPI-SSO免登短链-全量自动化(按XMind用例)",
    description:
      "Body 已按每条用例写好。前置脚本仍会按 case 变量微调。\n" +
      "若返回 201.000.001，是 Token/secret 问题，不是 Body。\n" +
      "环境：baseUrl、access_token、Program-ID、sso_subject_type、sso_subject_id、sso_orderId。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  variable: [
    { key: "sso_subject_type", value: "MEMBERSHIP" },
    { key: "sso_duration_default", value: "600" }
  ],
  item: [folder1, folder2, folderLang, folder3, folder4, folder5, folder6]
};

const out = path + "/PAPI-SSO免登短链-全量自动化.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
let count = 0;
function countItems(arr) {
  arr.forEach(function (x) {
    if (x.item) countItems(x.item);
    else count++;
  });
}
countItems(collection.item);
console.log("wrote", out, "requests=", count);
