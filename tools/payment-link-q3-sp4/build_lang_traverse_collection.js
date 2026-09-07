const fs = require("fs");
const path = __dirname;

// BOSS-API 转换关系（实际口径）
const GROUP1 = [
  ["en-US", "BOSS组1"],
  ["ja-JP", "BOSS组1"],
  ["de-DE", "BOSS组1"],
  ["es-ES", "BOSS组1"],
  ["fr-FR", "BOSS组1"],
  ["it-IT", "BOSS组1"],
  ["pl-PL", "BOSS组1"],
  ["pt-PT", "BOSS组1"],
  ["ru-RU", "BOSS组1"],
  ["th-TH", "BOSS组1"],
  ["uk-UA", "BOSS组1"],
  ["vi-VN", "BOSS组1"],
  ["ko-KR", "BOSS组1"],
  ["es-419", "BOSS组1-拉丁美洲西语"]
];

const GROUP2 = [
  ["fr-CA", "BOSS组2"],
  ["ar-SA", "BOSS组2"],
  ["ro-RO", "BOSS组2"],
  ["bs-BA", "BOSS组2"],
  ["sr-SP", "BOSS组2"],
  ["sr-ME", "BOSS组2"],
  ["hr-HR", "BOSS组2"],
  ["nl-NL", "BOSS组2"],
  ["el-GR", "BOSS组2"],
  ["si-SI", "BOSS组2"],
  ["he-IL", "BOSS组2"],
  ["hu-HU", "BOSS组2"]
];

const LANGUAGES = GROUP1.concat(GROUP2);

const pre = fs.readFileSync(path + "/apifox_pre_payments_lang_traverse.js", "utf8").split(/\r?\n/);
const post = fs.readFileSync(path + "/apifox_post_payments_lang_traverse.js", "utf8").split(/\r?\n/);

function item(lang, desc) {
  return {
    name: "LANG_" + lang + " " + desc,
    event: [
      {
        listen: "prerequest",
        script: {
          type: "text/javascript",
          exec: [
            "pm.variables.set('language','" + lang + "');",
            "pm.variables.set('case_id','LANG_TRAVERSE_" + lang + "');"
          ].concat(pre)
        }
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
        raw: JSON.stringify(
          {
            orderId: "{{pay_orderId}}",
            returnUrl: "{{pay_returnUrl}}",
            paymentMethod: "{{pay_paymentMethod}}",
            language: lang
          },
          null,
          2
        ),
        options: { raw: { language: "json" } }
      },
      url: {
        raw: "{{baseUrl}}/v2/orders/payments",
        host: ["{{baseUrl}}"],
        path: ["v2", "orders", "payments"]
      },
      description: "BOSS-API 语种: " + lang + " / " + desc
    }
  };
}

const collection = {
  info: {
    _postman_id: "papi-3135-pay-lang-boss-api",
    name: "PAPI-3135 支付链接-语种遍历(BOSS-API共26)",
    description:
      "语种以 BOSS-API 转换关系为准：组1共14 + 组2共12 = 26。\n" +
      "组1: en-US,ja-JP,de-DE,es-ES,fr-FR,it-IT,pl-PL,pt-PT,ru-RU,th-TH,uk-UA,vi-VN,ko-KR,es-419\n" +
      "组2: fr-CA,ar-SA,ro-RO,bs-BA,sr-SP,sr-ME,hr-HR,nl-NL,el-GR,si-SI,he-IL,hu-HU\n" +
      "Header: access_token / Program-ID。跑前必填 pay_orderId 等。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  variable: [{ key: "pay_duration_default", value: "600" }],
  item: [
    {
      name: "1.BOSS组1(14)",
      item: GROUP1.map(function (row) {
        return item(row[0], row[1]);
      })
    },
    {
      name: "2.BOSS组2(12)",
      item: GROUP2.map(function (row) {
        return item(row[0], row[1]);
      })
    }
  ]
};

const out = path + "/PAPI-3135-支付链接-语种遍历-BOSS-API.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
console.log("wrote", out, "count=", LANGUAGES.length);
