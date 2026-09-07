/**
 * 生成「轻量可导入」集合：无大段内联脚本，避免 Apifox 预览空白。
 * 导入成功后，把 pre/post js 贴到集合或接口的前置/后置即可。
 */
const fs = require("fs");
const path = __dirname;

function req(name, bodyObj, caseSetup) {
  const bodyRaw = JSON.stringify(bodyObj, null, 2);
  return {
    name,
    event: [
      {
        listen: "prerequest",
        script: {
          type: "text/javascript",
          exec: caseSetup.concat([
            "// 若已在集合级粘贴完整 pre 脚本可删下面日志",
            "console.log('[pay-link] case=', pm.variables.get('case_id'));"
          ])
        }
      },
      {
        listen: "test",
        script: {
          type: "text/javascript",
          exec: [
            "const json = pm.response.json();",
            "pm.test('HTTP 200', function () { pm.response.to.have.status(200); });",
            "console.log('[pay-link] code=', json.code, 'err=', json.errCode);"
          ]
        }
      }
    ],
    request: {
      method: "POST",
      header: [
        { key: "Content-Type", value: "application/json" },
        { key: "Authorization", value: "Bearer {{accessToken}}" },
        { key: "X-Program-ID", value: "{{programId}}" }
      ],
      body: { mode: "raw", raw: bodyRaw, options: { raw: { language: "json" } } },
      url: {
        raw: "{{baseUrl}}/v2/orders/payments",
        host: ["{{baseUrl}}"],
        path: ["v2", "orders", "payments"]
      }
    }
  };
}

const base = {
  orderId: "{{pay_orderId}}",
  returnUrl: "{{pay_returnUrl}}",
  paymentMethod: "{{pay_paymentMethod}}"
};

const collection = {
  info: {
    _postman_id: "papi-3135-pay-link-lite",
    name: "PAPI-3135 支付链接-语种与有效期(轻量可导入)",
    description:
      "轻量版：保证 Apifox 预览有内容。完整断言请导入后粘贴 apifox_pre / apifox_post 两个 js。",
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
        req("LANG_DEFAULT 不传language", { ...base }, [
          "pm.variables.set('case_id','LANG_DEFAULT');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration','');"
        ]),
        req("LANG_EN 传language=en-US", { ...base, language: "en-US" }, [
          "pm.variables.set('case_id','LANG_EN');",
          "pm.variables.set('req_language','en-US');",
          "pm.variables.set('req_duration','');"
        ])
      ]
    },
    {
      name: "2.有效期durationInSeconds校验",
      item: [
        req("DUR_DEFAULT 不传duration", { ...base }, [
          "pm.variables.set('case_id','DUR_DEFAULT');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration','');"
        ]),
        req("DUR_60 duration=60", { ...base, durationInSeconds: 60 }, [
          "pm.variables.set('case_id','DUR_60');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration','60');"
        ]),
        req("DUR_MAX duration=上限", { ...base, durationInSeconds: 1800 }, [
          "pm.variables.set('case_id','DUR_MAX');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration', pm.environment.get('pay_duration_max') || '1800');"
        ]),
        req("DUR_OVER 超上限应失败", { ...base, durationInSeconds: 1801 }, [
          "pm.variables.set('case_id','DUR_OVER');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration','1801');"
        ])
      ]
    },
    {
      name: "3.手工-链接过期",
      item: [
        req("EXPIRY 建60s链接", { ...base, durationInSeconds: 60 }, [
          "pm.variables.set('case_id','EXPIRY_CREATE_60');",
          "pm.variables.set('req_language','');",
          "pm.variables.set('req_duration','60');"
        ])
      ]
    }
  ]
};

const out = path + "/PAPI-3135-支付链接-轻量可导入.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
console.log("wrote", out);
