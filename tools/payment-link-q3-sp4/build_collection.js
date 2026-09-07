const fs = require("fs");
const path = __dirname;
const pre = fs.readFileSync(path + "/apifox_pre_payments_language_duration.js", "utf8").split(/\r?\n/);
const post = fs.readFileSync(path + "/apifox_post_payments_language_duration.js", "utf8").split(/\r?\n/);

function event(caseSetupLines, extraPostLines) {
  return [
    { listen: "prerequest", script: { type: "text/javascript", exec: caseSetupLines.concat(pre) } },
    { listen: "test", script: { type: "text/javascript", exec: post.concat(extraPostLines || []) } }
  ];
}

function req(bodyRaw, desc) {
  return {
    method: "POST",
    header: [
      { key: "Content-Type", value: "application/json" },
      { key: "Authorization", value: "Bearer {{accessToken}}" },
      { key: "X-Program-ID", value: "{{programId}}" }
    ],
    body: { mode: "raw", raw: bodyRaw, options: { raw: { language: "json" } } },
    // Apifox 对字符串 url 偶发解析为空，改用 v2.1 对象格式
    url: {
      raw: "{{baseUrl}}/v2/orders/payments",
      host: ["{{baseUrl}}"],
      path: ["v2", "orders", "payments"]
    },
    description: desc || ""
  };
}

const baseBody =
  '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}"\n}';

const collection = {
  info: {
    _postman_id: "papi-3135-pay-link-q3-sp4",
    name: "PAPI-3135 支付链接-语种与有效期(Q3-SP4)",
    description:
      "来源：Desktop《需求测试用例》三、支付链接 + Jira PAPI-2834/PAPI-3135 + Q3-SP4。\n接口 POST /v2/orders/payments。\n脚本已内联，导入后只需配环境变量即可跑。\n上限默认按用例 1800；若按 Jira 图注 12000，改环境变量 pay_duration_max。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  variable: [
    { key: "pay_duration_max", value: "1800" },
    { key: "pay_duration_default", value: "600" }
  ],
  item: [
    {
      name: "1.语种language校验",
      item: [
        {
          name: "LANG_DEFAULT 不传language→默认en-US",
          event: event([
            "pm.variables.set('case_id','LANG_DEFAULT');",
            "pm.variables.set('req_language','');",
            "pm.variables.set('req_duration','');"
          ]),
          request: req(baseBody, "不传 language。预期成功并按默认 en-US。")
        },
        {
          name: "LANG_EN 传language=en-US",
          event: event([
            "pm.variables.set('case_id','LANG_EN');",
            "pm.variables.set('req_language','en-US');",
            "pm.variables.set('req_duration','');"
          ]),
          request: req(
            '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}",\n  "language": "en-US"\n}',
            "传 language=en-US"
          )
        }
      ]
    },
    {
      name: "2.有效期durationInSeconds校验",
      item: [
        {
          name: "DUR_DEFAULT 不传duration→默认600",
          event: event([
            "pm.variables.set('case_id','DUR_DEFAULT');",
            "pm.variables.set('req_language','');",
            "pm.variables.set('req_duration','');"
          ]),
          request: req(baseBody, "不传 duration，期望 validUntil≈now+600s")
        },
        {
          name: "DUR_60 durationInSeconds=60",
          event: event([
            "pm.variables.set('case_id','DUR_60');",
            "pm.variables.set('req_language','');",
            "pm.variables.set('req_duration','60');"
          ]),
          request: req(
            '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}",\n  "durationInSeconds": 60\n}'
          )
        },
        {
          name: "DUR_MAX durationInSeconds=上限(默认1800)",
          event: event([
            "var max = pm.environment.get('pay_duration_max') || pm.collectionVariables.get('pay_duration_max') || '1800';",
            "pm.variables.set('case_id','DUR_MAX');",
            "pm.variables.set('req_language','');",
            "pm.variables.set('req_duration', String(max));"
          ]),
          request: req(
            '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}",\n  "durationInSeconds": {{pay_duration_max}}\n}'
          )
        },
        {
          name: "DUR_OVER 超上限(默认1801)应失败",
          event: event([
            "var max = parseInt(pm.environment.get('pay_duration_max') || pm.collectionVariables.get('pay_duration_max') || '1800', 10);",
            "pm.variables.set('case_id','DUR_OVER');",
            "pm.variables.set('req_language','');",
            "pm.variables.set('req_duration', String(max + 1));"
          ]),
          request: req(
            '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}",\n  "durationInSeconds": 1801\n}',
            "用例预期失败。若上限12000，改 pay_duration_max=12000（前置会自动用 max+1）。"
          )
        }
      ]
    },
    {
      name: "3.手工-链接过期不可支付",
      item: [
        {
          name: "EXPIRY 先建60s链接(再手工等过期打开)",
          event: event(
            [
              "pm.variables.set('case_id','EXPIRY_CREATE_60');",
              "pm.variables.set('req_language','');",
              "pm.variables.set('req_duration','60');"
            ],
            [
              "pm.test('[EXPIRY] 已写入 pay_last_url，请60s后浏览器打开验证不可支付', function () {",
              "  var u = pm.environment.get('pay_last_url') || pm.collectionVariables.get('pay_last_url');",
              "  pm.expect(u).to.be.ok;",
              "  console.log('[pay-link] open later:', u);",
              "});"
            ]
          ),
          request: req(
            '{\n  "orderId": "{{pay_orderId}}",\n  "returnUrl": "{{pay_returnUrl}}",\n  "paymentMethod": "{{pay_paymentMethod}}",\n  "durationInSeconds": 60\n}'
          )
        }
      ]
    }
  ]
};

const out = path + "/PAPI-3135-支付链接-语种有效期.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
console.log("wrote", out, "preLines=", pre.length, "postLines=", post.length);
