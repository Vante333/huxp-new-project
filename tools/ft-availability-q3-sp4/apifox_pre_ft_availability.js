/**
 * FT 可用性过滤过去时间 — 前置脚本
 * 接口：POST /v2/resources/prebookings/availability
 *
 * 环境变量（必填）：
 *   access_token / Program-ID / baseUrl
 *   fastTrackResourceId   FT 资源 ID（module=2）
 *   membershipId          可选，有则写入 Body
 *
 * 环境变量（时间控制，可选）：
 *   ft_tz_offset_hours    资源当地相对 UTC 的小时偏移，如上海 8、伦敦夏令时 1
 *                         用于构造「当地已过 / 当地未过」的 prebookingDate
 *   ft_past_minutes       过去多少分钟，默认 30
 *   ft_future_days        未来多少天，默认 10
 *   ft_adultCount         默认 1
 *   ft_childCount         默认 0
 *
 * 用例级变量（pm.variables）：
 *   case_id               用例名（日志用）
 *   ft_date_mode          past_local | future_local | custom | keep_body
 *   ft_prebookingDate     custom 时使用（yyyy-MM-ddTHH:mm）
 *   ft_expect_type        fail_past | success | fail_err | record_only
 *   ft_expect_errCode     期望错误码，如 500.020.030
 *   ft_module             默认 2
 *   ft_resourceId         覆盖环境资源
 */
function Env(key, defVal) {
  var v = "";
  try {
    v = pm.environment.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}
function Var(key, defVal) {
  var v = "";
  try {
    v = pm.variables.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") {
    try {
      v = pm.collectionVariables.get(key);
    } catch (e2) {}
  }
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}
function pad(n) {
  return n < 10 ? "0" + n : String(n);
}
/** 按「资源当地墙钟」格式化 yyyy-MM-ddTHH:mm */
function formatLocalWall(utcMs, offsetHours) {
  var local = new Date(utcMs + offsetHours * 3600 * 1000);
  return (
    local.getUTCFullYear() +
    "-" +
    pad(local.getUTCMonth() + 1) +
    "-" +
    pad(local.getUTCDate()) +
    "T" +
    pad(local.getUTCHours()) +
    ":" +
    pad(local.getUTCMinutes())
  );
}

var caseId = Var("case_id", "FT可用性");
var dateMode = Var("ft_date_mode", Env("ft_date_mode", "future_local"));
var offsetHours = parseFloat(Env("ft_tz_offset_hours", "8"));
if (isNaN(offsetHours)) offsetHours = 8;
var pastMinutes = parseInt(Env("ft_past_minutes", "30"), 10) || 30;
var futureDays = parseInt(Env("ft_future_days", "10"), 10) || 10;
var now = Date.now();

var prebookingDate = Var("ft_prebookingDate", "");
if (dateMode === "past_local") {
  prebookingDate = formatLocalWall(now - pastMinutes * 60 * 1000, offsetHours);
} else if (dateMode === "future_local") {
  prebookingDate = formatLocalWall(now + futureDays * 24 * 3600 * 1000, offsetHours);
  // 固定落到整点，减少库存/时段边界噪音
  prebookingDate = prebookingDate.replace(/T\d{2}:\d{2}$/, "T10:00");
} else if (dateMode === "custom") {
  if (!prebookingDate) prebookingDate = Env("ft_prebookingDate", "");
} else if (dateMode === "keep_body") {
  try {
    var rawKeep = pm.request.body && pm.request.body.raw ? pm.request.body.raw : "";
    if (rawKeep) {
      var keepObj = JSON.parse(rawKeep);
      if (keepObj.prebookingDate) prebookingDate = String(keepObj.prebookingDate);
    }
  } catch (eKeep) {}
}

var moduleNum = parseInt(Var("ft_module", Env("ft_module", "2")), 10) || 2;
var resourceId = Var("ft_resourceId", Env("ft_resourceId", Env("fastTrackResourceId", "")));
var membershipId = Var("ft_membershipId", Env("membershipId", ""));
var adultCount = parseInt(Var("ft_adultCount", Env("ft_adultCount", "1")), 10);
if (isNaN(adultCount)) adultCount = 1;
var childCount = parseInt(Var("ft_childCount", Env("ft_childCount", "0")), 10);
if (isNaN(childCount)) childCount = 0;

var body = {
  module: moduleNum,
  resourceId: resourceId,
  prebookingDate: prebookingDate,
  adultCount: adultCount,
  childCount: childCount
};
if (membershipId) body.membershipId = membershipId;

if (dateMode !== "keep_body" || !pm.request.body || !pm.request.body.raw) {
  pm.request.body = {
    mode: "raw",
    raw: JSON.stringify(body, null, 2),
    options: { raw: { language: "json" } }
  };
} else {
  // keep_body：仅补齐缺失字段
  try {
    var cur = JSON.parse(pm.request.body.raw);
    if (!cur.module) cur.module = moduleNum;
    if (!cur.resourceId) cur.resourceId = resourceId;
    if (!cur.prebookingDate && prebookingDate) cur.prebookingDate = prebookingDate;
    if (cur.adultCount === undefined) cur.adultCount = adultCount;
    if (cur.childCount === undefined) cur.childCount = childCount;
    if (membershipId && !cur.membershipId) cur.membershipId = membershipId;
    pm.request.body.raw = JSON.stringify(cur, null, 2);
    prebookingDate = cur.prebookingDate || prebookingDate;
  } catch (e2) {
    pm.request.body = {
      mode: "raw",
      raw: JSON.stringify(body, null, 2),
      options: { raw: { language: "json" } }
    };
  }
}

pm.variables.set("case_id", caseId);
pm.variables.set("ft_sent_prebookingDate", prebookingDate);
pm.variables.set("ft_sent_at_ms", String(now));
pm.variables.set("ft_expect_type", Var("ft_expect_type", "success"));
pm.variables.set("ft_expect_errCode", Var("ft_expect_errCode", ""));
pm.environment.set("ft_last_prebookingDate", prebookingDate);

console.log(
  "[ft-avail] case=",
  caseId,
  "mode=",
  dateMode,
  "tzOffset=",
  offsetHours,
  "prebookingDate=",
  prebookingDate,
  "resourceId=",
  resourceId
);
