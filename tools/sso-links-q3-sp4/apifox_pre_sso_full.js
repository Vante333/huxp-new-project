/**
 * SSO 免登短链 — 全量用例前置脚本
 * 通过用例级变量 case_id / sso_* 控制 Body
 *
 * 环境变量（必填）：
 *   access_token / Program-ID / baseUrl
 *   sso_subject_type=MEMBERSHIP
 *   sso_subject_id=合法会籍
 *   sso_orderId=该会籍下真实订单（DETAIL 用）
 *   sso_orderId_other=其他会籍订单（越权用，可选）
 *   sso_subject_id_other=不存在或非法 id（可选）
 *   sso_returnUrl_ok / sso_returnUrl_bad
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
function Flag(key) {
  return Var(key, "") === "true" || Env(key, "") === "true";
}

var caseId = Var("case_id", "MANUAL");
var scene = Var("sso_scene", Env("sso_scene", "ORDER_LIST"));
var language = Var("language", "") || Var("item", "") || Env("sso_lang_current", "en-US");
var omitScene = Flag("sso_omit_scene");
var omitLanguage = Flag("sso_omit_language");
var omitDuration = Flag("sso_omit_duration");
var omitReturnUrl = Flag("sso_omit_returnUrl");
var omitSubject = Flag("sso_omit_subject");
var omitExtra = Flag("sso_omit_extra");
var emptyOrderId = Flag("sso_empty_orderId");
var noAuth = Flag("sso_no_auth");
var badAuth = Flag("sso_bad_auth");

var subjectType = Var("sso_subject_type", Env("sso_subject_type", "MEMBERSHIP"));
var subjectId = Var("sso_subject_id", Env("sso_subject_id", Env("membershipId", "")));
var orderId = Var("sso_orderId", Env("sso_orderId", ""));
var durationRaw = Var("sso_durationInSeconds", Env("sso_durationInSeconds", ""));
var returnUrl = Var("sso_returnUrl", Env("sso_returnUrl", Env("sso_returnUrl_ok", "")));

if (Flag("sso_use_other_order")) {
  orderId = Env("sso_orderId_other", "OTHER_ORDER_NOT_OWNED");
}
if (Flag("sso_use_missing_subject_id")) {
  subjectId = Env("sso_subject_id_missing", "9999999999999999");
}
if (Flag("sso_use_bad_subject_type")) {
  subjectType = Env("sso_subject_type_bad", "INVALID_TYPE");
}
if (Flag("sso_use_bad_returnUrl")) {
  returnUrl = Env("sso_returnUrl_bad", "https://evil.example.invalid");
}
if (Flag("sso_use_bad_scene")) {
  scene = Env("sso_scene_bad", "XXX");
}

var body = {};

if (!omitScene && scene !== "") {
  body.scene = scene;
}

if (!omitSubject && subjectType !== "" && subjectId !== "") {
  body.subject = { type: subjectType, id: subjectId };
}

if (!omitLanguage) {
  body.language = language;
}

if (!omitDuration && durationRaw === "") {
  durationRaw = Env("sso_duration_default", "1800");
}
if (!omitDuration && durationRaw !== "") {
  if (Flag("sso_duration_as_string_abc")) {
    body.durationInSeconds = "abc";
  } else {
    var n = parseInt(durationRaw, 10);
    if (!isNaN(n)) body.durationInSeconds = n;
    else body.durationInSeconds = durationRaw;
  }
}

if (!omitReturnUrl && returnUrl !== "") {
  body.returnUrl = returnUrl;
}

var sceneUpper = String(scene).toUpperCase().replace("ORDER_DETALL", "ORDER_DETAIL");
var needDetail =
  sceneUpper.indexOf("ORDER_DETAIL") >= 0 ||
  String(scene).toLowerCase().indexOf("order_detall") >= 0 ||
  String(scene).toLowerCase().indexOf("order_detail") >= 0;

if (needDetail && !omitExtra) {
  if (emptyOrderId) {
    body.extra = { orderId: "" };
  } else if (orderId !== "") {
    body.extra = { orderId: orderId };
  } else {
    body.extra = {};
  }
}

pm.request.body = {
  mode: "raw",
  raw: JSON.stringify(body, null, 2),
  options: { raw: { language: "json" } }
};

if (noAuth) {
  try {
    pm.request.headers.remove("Authorization");
  } catch (eH) {
    pm.request.headers.upsert({ key: "Authorization", value: "" });
  }
}
if (badAuth) {
  pm.request.headers.upsert({ key: "Authorization", value: "Bearer INVALID_TOKEN_FOR_TEST" });
}

pm.variables.set("sso_last_case_id", caseId);
pm.variables.set("sso_language_sent", omitLanguage ? "(omit)" : language);
pm.variables.set("sso_scene_sent", omitScene ? "(omit)" : scene);
pm.variables.set("sso_sent_at_ms", String(Date.now()));
pm.variables.set("sso_expect_duration", durationRaw !== "" ? durationRaw : Env("sso_duration_default", "600"));
pm.variables.set("sso_expect_type", Var("sso_expect_type", Env("sso_expect_type", "success")));
pm.variables.set("sso_expect_errCode", Var("sso_expect_errCode", Env("sso_expect_errCode", "")));
pm.variables.set("sso_expect_scene_echo", Var("sso_expect_scene_echo", ""));
pm.variables.set("sso_expect_language_echo", Var("sso_expect_language_echo", ""));

console.log("[sso-full] case=" + caseId + " expect=" + pm.variables.get("sso_expect_type") + " body=" + JSON.stringify(body));
