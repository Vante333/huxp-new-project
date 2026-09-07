/**
 * PAPI-3135 支付链接 — 语种遍历
 * 实际口径：BOSS-API 转换关系（组1共14 + 组2共12 = 26）
 *
 * 语种来源优先级：
 * 1) 测试数据 / 用例变量 language（自动化「测试数据」CSV / ForEach 当前项）
 * 2) 环境变量 pay_lang_current
 * 3) 默认 en-US
 *
 * 环境变量：
 *   pay_orderId / pay_returnUrl / pay_paymentMethod
 *   access_token 或 accessToken；Program-ID 或 programId
 *   pay_lang_duration   可选，遍历时附带有效期秒数；空=不传 duration
 */
function Env(key, defVal) {
  var v = "";
  try { v = pm.environment.get(key); } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}
function Var(key, defVal) {
  var v = "";
  try { v = pm.variables.get(key); } catch (e) {}
  if (v === null || v === undefined || v === "") {
    try { v = pm.collectionVariables.get(key); } catch (e2) {}
  }
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}

// BOSS-API 转换关系语种（组1+组2，共26）— ForEach / 轮询用列表
var PAY_LANGUAGES = [
  "en-US",
  "ja-JP",
  "de-DE",
  "es-ES",
  "fr-FR",
  "it-IT",
  "pl-PL",
  "pt-PT",
  "ru-RU",
  "th-TH",
  "uk-UA",
  "vi-VN",
  "ko-KR",
  "es-419",
  "fr-CA",
  "ar-SA",
  "ro-RO",
  "bs-BA",
  "sr-SP",
  "sr-ME",
  "hr-HR",
  "nl-NL",
  "el-GR",
  "si-SI",
  "he-IL",
  "hu-HU"
];

try {
  pm.collectionVariables.set("pay_languages_json", JSON.stringify(PAY_LANGUAGES));
  pm.environment.set("pay_languages_json", JSON.stringify(PAY_LANGUAGES));
} catch (eLang) {}

// ForEach 循环项可能叫 item / language / value，按常见字段兼容
var language =
  Var("language", "") ||
  Var("item", "") ||
  Var("value", "") ||
  Env("pay_lang_current", "") ||
  "en-US";

// 若循环直接把字符串当当前项，Apifox 有时只给 item
if (language && language.charAt(0) === "[") {
  // 误拿到整表 JSON 时回退
  language = Env("pay_lang_current", "en-US");
}
var orderId = Env("pay_orderId", "") || Env("orderId", "");
var returnUrl = Env("pay_returnUrl", "https://example.com/payment/return");
var paymentMethod = Env("pay_paymentMethod", "H5_CASHIER");
var duration = Var("durationInSeconds", "") || Env("pay_lang_duration", "");

if (!orderId) {
  console.warn("[pay-lang] 请设置环境变量 pay_orderId=待支付订单号");
}

var body = {
  orderId: orderId,
  returnUrl: returnUrl,
  paymentMethod: paymentMethod,
  language: language
};
if (duration !== "") {
  var n = parseInt(duration, 10);
  if (!isNaN(n)) body.durationInSeconds = n;
}

pm.request.body = {
  mode: "raw",
  raw: JSON.stringify(body, null, 2),
  options: { raw: { language: "json" } }
};

pm.variables.set("case_id", "LANG_TRAVERSE_" + language);
pm.variables.set("pay_last_case_id", "LANG_TRAVERSE_" + language);
pm.variables.set("pay_language_sent", language);
pm.variables.set("pay_sent_at_ms", String(Date.now()));
pm.variables.set("pay_h5_lang_count", String(PAY_LANGUAGES.length));

console.log("[pay-lang] language=" + language + " body=" + JSON.stringify(body));
