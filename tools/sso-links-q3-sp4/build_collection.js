const fs = require("fs");
const path = __dirname;

const LANGUAGES = JSON.parse(fs.readFileSync(path + "/sso_languages_list.json", "utf8"));
const pre = fs.readFileSync(path + "/apifox_pre_sso_links.js", "utf8").split(/\r?\n/);
const post = fs.readFileSync(path + "/apifox_post_sso_links.js", "utf8").split(/\r?\n/);

function item(lang) {
  return {
    name: "SSO_ORDER_LIST language=" + lang,
    event: [
      {
        listen: "prerequest",
        script: {
          type: "text/javascript",
          exec: [
            "pm.variables.set('language','" + lang + "');",
            "pm.environment.set('sso_scene','ORDER_LIST');",
            "pm.environment.set('sso_expect_602','false');",
            "pm.environment.set('sso_omit_language','false');"
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
            subject: {
              type: "{{sso_subject_type}}",
              id: "{{sso_subject_id}}"
            },
            scene: "ORDER_LIST",
            language: lang,
            durationInSeconds: 60,
            returnUrl: "{{sso_returnUrl}}"
          },
          null,
          2
        ),
        options: { raw: { language: "json" } }
      },
      url: {
        raw: "{{baseUrl}}/v2/sso/links",
        host: ["{{baseUrl}}"],
        path: ["v2", "sso", "links"]
      },
      description: "SSO 免登 ORDER_LIST，language=" + lang
    }
  };
}

const collection = {
  info: {
    _postman_id: "papi-sso-links-lang-boss-api",
    name: "PAPI-SSO免登短链-语种遍历(H5SsoLanguageEnum共29)",
    description:
      "接口 POST /v2/sso/links，scene=ORDER_LIST，语种按 H5SsoLanguageEnum 29 个轮询（不含 DEFAULT）。\n" +
      "环境必填：access_token、Program-ID、sso_subject_type、sso_subject_id、baseUrl。\n" +
      "ForEach 也可直接用 sso_languages_list.json。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  variable: [
    { key: "sso_subject_type", value: "MEMBERSHIP" },
    { key: "sso_duration_default", value: "600" }
  ],
  item: [
    {
      name: "语种遍历-ORDER_LIST(29)",
      item: LANGUAGES.map(item)
    },
    {
      name: "单条样例-ORDER_DETAIL",
      item: [
        {
          name: "ORDER_DETAIL 带 orderId",
          event: [
            {
              listen: "prerequest",
              script: {
                type: "text/javascript",
                exec: [
                  "pm.environment.set('sso_scene','ORDER_DETAIL');",
                  "pm.variables.set('language','en-US');",
                  "pm.environment.set('sso_expect_602','false');"
                ].concat(pre)
              }
            },
            { listen: "test", script: { type: "text/javascript", exec: post } }
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
                  subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
                  scene: "ORDER_DETAIL",
                  language: "en-US",
                  durationInSeconds: 60,
                  extra: { orderId: "{{sso_orderId}}" }
                },
                null,
                2
              ),
              options: { raw: { language: "json" } }
            },
            url: {
              raw: "{{baseUrl}}/v2/sso/links",
              host: ["{{baseUrl}}"],
              path: ["v2", "sso", "links"]
            }
          }
        },
        {
          name: "ORDER_DETAIL 缺 orderId→500.000.602",
          event: [
            {
              listen: "prerequest",
              script: {
                type: "text/javascript",
                exec: [
                  "pm.environment.set('sso_scene','ORDER_DETAIL');",
                  "pm.environment.set('sso_orderId','');",
                  "pm.variables.set('language','en-US');",
                  "pm.environment.set('sso_expect_602','true');"
                ].concat(pre)
              }
            },
            { listen: "test", script: { type: "text/javascript", exec: post } }
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
                  subject: { type: "{{sso_subject_type}}", id: "{{sso_subject_id}}" },
                  scene: "ORDER_DETAIL",
                  language: "en-US",
                  extra: {}
                },
                null,
                2
              ),
              options: { raw: { language: "json" } }
            },
            url: {
              raw: "{{baseUrl}}/v2/sso/links",
              host: ["{{baseUrl}}"],
              path: ["v2", "sso", "links"]
            }
          }
        }
      ]
    }
  ]
};

const out = path + "/PAPI-SSO免登短链-语种遍历-BOSS-API.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
console.log("wrote", out, "langs=", LANGUAGES.length);
