/**
 * SSO 免登短链 — 语种列表（ForEach 轮询用）
 * 口径：H5SsoLanguageEnum 最新枚举（不含 DEFAULT），共 29
 *
 * Apifox：自动化 → 添加步骤 → ForEach 循环 → 数据源贴 SSO_LANGUAGES / 本文件 JSON
 */

var SSO_LANGUAGES = [
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
  "pt-BR",
  "ko-KR",
  "zh-HK",
  "zh-CN",
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
  pm.collectionVariables.set("sso_languages_json", JSON.stringify(SSO_LANGUAGES));
  pm.environment.set("sso_languages_json", JSON.stringify(SSO_LANGUAGES));
  pm.collectionVariables.set("sso_languages_count", String(SSO_LANGUAGES.length));
} catch (e) {}

console.log("[sso-link] languages size=" + SSO_LANGUAGES.length);

var idx = parseInt(pm.environment.get("sso_lang_index") || "0", 10);
if (isNaN(idx) || idx < 0) idx = 0;
if (idx >= SSO_LANGUAGES.length) idx = 0;
var current = SSO_LANGUAGES[idx];
pm.variables.set("language", current);
pm.environment.set("sso_lang_current", current);
console.log("[sso-link] index=" + idx + " language=" + current);
