/**
 * FT 可用性 — 单条冒烟（不依赖 ForEach）
 * 贴在 POST /v2/resources/prebookings/availability 的「前置操作」里，
 * 或先跑本脚本再跑 apifox_pre_ft_availability.js（二选一：本脚本已含组 Body）。
 *
 * 测过去：环境 ft_smoke_mode = past
 * 测未来：环境 ft_smoke_mode = future（默认）
 */
function Env(key, defVal) {
  var v = "";
  try {
    v = pm.environment.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}
function pad(n) {
  return n < 10 ? "0" + n : String(n);
}
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

var mode = Env("ft_smoke_mode", "future"); // past | future
var offsetHours = parseFloat(Env("ft_tz_offset_hours", "8"));
if (isNaN(offsetHours)) offsetHours = 8;
var pastMinutes = parseInt(Env("ft_past_minutes", "30"), 10) || 30;
var futureDays = parseInt(Env("ft_future_days", "10"), 10) || 10;
var now = Date.now();

var prebookingDate;
if (mode === "past") {
  prebookingDate = formatLocalWall(now - pastMinutes * 60 * 1000, offsetHours);
  pm.environment.set("ft_expect_type", "fail_past");
  pm.environment.set("ft_expect_errCode", "500.020.030");
  pm.variables.set("case_id", "冒烟-过去时间拦截");
} else {
  prebookingDate = formatLocalWall(now + futureDays * 24 * 3600 * 1000, offsetHours);
  prebookingDate = prebookingDate.replace(/T\d{2}:\d{2}$/, "T10:00");
  pm.environment.set("ft_expect_type", "success");
  pm.environment.set("ft_expect_errCode", "");
  pm.variables.set("case_id", "冒烟-未来时间");
}

var resourceId = Env("fastTrackResourceId", Env("ft_resourceId", ""));
var membershipId = Env("membershipId", "");
var body = {
  module: 2,
  resourceId: resourceId,
  prebookingDate: prebookingDate,
  adultCount: 1,
  childCount: 0
};
if (membershipId) body.membershipId = membershipId;

pm.request.body = {
  mode: "raw",
  raw: JSON.stringify(body, null, 2),
  options: { raw: { language: "json" } }
};

pm.variables.set("ft_sent_prebookingDate", prebookingDate);
pm.environment.set("ft_last_prebookingDate", prebookingDate);

console.log("[ft-smoke] mode=", mode, "prebookingDate=", prebookingDate, "resourceId=", resourceId);

if (!resourceId) {
  console.warn("[ft-smoke] 警告：fastTrackResourceId 为空，接口会失败");
}
