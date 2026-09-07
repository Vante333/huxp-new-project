/**
 * PAPI SSO 免登短链 POST /v2/sso/links — 前置脚本
 *
 * 环境变量：
 *   sso_scene              默认 ORDER_LIST；ORDER_DETAIL 需 sso_orderId
 *   sso_subject_type       默认 MEMBERSHIP；空=不传 subject（游客）
 *   sso_subject_id         membershipId / epassId 等
 *   sso_orderId            ORDER_DETAIL 必填
 *   sso_returnUrl          可选
 *   sso_durationInSeconds  可选；空=不传（走默认）
 *   sso_omit_language      true 时不传 language（测默认 en-US）
 *
 * ForEach 当前项：
 *   language / item / value → 写入 Body.language
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

var SSO_LANGUAGES = [
  "en-US", "ja-JP", "de-DE", "es-ES", "fr-FR", "it-IT", "pl-PL", "pt-PT",
  "ru-RU", "th-TH", "uk-UA", "vi-VN", "pt-BR", "ko-KR", "zh-HK", "zh-CN",
  "es-419", "fr-CA", "ar-SA", "ro-RO", "bs-BA", "sr-SP", "sr-ME", "hr-HR",
  "nl-NL", "el-GR", "si-SI", "he-IL", "hu-HU"
];

try {
  pm.collectionVariables.set("sso_languages_json", JSON.stringify(SSO_LANGUAGES));
} catch (e0) {}

var scene = Var("sso_scene", "") || Env("sso_scene", "ORDER_LIST");
var language =
  Var("language", "") ||
  Var("item", "") ||
  Var("value", "") ||
  Env("sso_lang_current", "") ||
  "en-US";
var omitLanguage = Env("sso_omit_language", "false") === "true";
var subjectType = Env("sso_subject_type", "MEMBERSHIP");
var subjectId = Env("sso_subject_id", "") || Env("membershipId", "");
var orderId = Env("sso_orderId", "") || Env("orderId", "");
var returnUrl = Env("sso_returnUrl", "");
var duration = Var("durationInSeconds", "") || Env("sso_durationInSeconds", "");

var body = {
  scene: scene
};

if (subjectType !== "" && subjectId !== "") {
  body.subject = {
    type: subjectType,
    id: subjectId
  };
}

if (!omitLanguage) {
  body.language = language;
}

if (duration !== "") {
  var n = parseInt(duration, 10);
  if (!isNaN(n)) body.durationInSeconds = n;
}

if (returnUrl !== "") {
  body.returnUrl = returnUrl;
}

if (scene === "ORDER_DETAIL") {
  body.extra = { orderId: orderId };
  if (!orderId) {
    console.warn("[sso-link] ORDER_DETAIL 需要环境变量 sso_orderId");
  }
}

pm.request.body = {
  mode: "raw",
  raw: JSON.stringify(body, null, 2),
  options: { raw: { language: "json" } }
};

pm.variables.set("sso_last_case_id", "SSO_" + scene + "_" + (omitLanguage ? "DEFAULT_LANG" : language));
pm.variables.set("sso_language_sent", omitLanguage ? "(omit→default en-US)" : language);
pm.variables.set("sso_scene_sent", scene);
pm.variables.set("sso_sent_at_ms", String(Date.now()));
pm.variables.set("sso_expect_duration", duration !== "" ? duration : Env("sso_duration_default", "600"));

console.log("[sso-link] case=" + pm.variables.get("sso_last_case_id") + " body=" + JSON.stringify(body));
