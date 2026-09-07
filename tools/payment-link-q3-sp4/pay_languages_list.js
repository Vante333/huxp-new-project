/**
 * PAPI-3135 支付链接 — 语种列表（轮询用）
 * 实际口径：BOSS-API 转换关系（用户提供）
 *
 * 第一组（14）：
 *   en-US, ja-JP, de-DE, es-ES, fr-FR, it-IT, pl-PL, pt-PT,
 *   ru-RU, th-TH, uk-UA, vi-VN, ko-KR, es-419
 * 第二组（12，PAPI-2735 等新增）：
 *   fr-CA, ar-SA, ro-RO, bs-BA, sr-SP, sr-ME, hr-HR, nl-NL,
 *   el-GR, si-SI, he-IL, hu-HU
 * 合计 26，去重后仍 26（两组无重复）
 *
 * Apifox：ForEach 数据源直接用 PAY_LANGUAGES / pay_languages_list.json
 */

var PAY_LANGUAGES_BOSS_GROUP1 = [
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
  "es-419"
];

var PAY_LANGUAGES_BOSS_GROUP2 = [
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

var PAY_LANGUAGES = PAY_LANGUAGES_BOSS_GROUP1.concat(PAY_LANGUAGES_BOSS_GROUP2);

try {
  pm.collectionVariables.set("pay_languages_json", JSON.stringify(PAY_LANGUAGES));
  pm.environment.set("pay_languages_json", JSON.stringify(PAY_LANGUAGES));
  pm.collectionVariables.set("pay_languages_count", String(PAY_LANGUAGES.length));
  pm.collectionVariables.set("pay_languages_group1_json", JSON.stringify(PAY_LANGUAGES_BOSS_GROUP1));
  pm.collectionVariables.set("pay_languages_group2_json", JSON.stringify(PAY_LANGUAGES_BOSS_GROUP2));
} catch (e) {}

console.log("[pay-lang] boss-api list size=" + PAY_LANGUAGES.length + " => " + JSON.stringify(PAY_LANGUAGES));

var idx = parseInt(pm.environment.get("pay_lang_index") || "0", 10);
if (isNaN(idx) || idx < 0) idx = 0;
if (idx >= PAY_LANGUAGES.length) idx = 0;
var current = PAY_LANGUAGES[idx];
pm.variables.set("language", current);
pm.environment.set("pay_lang_current", current);
console.log("[pay-lang] index=" + idx + " language=" + current);
