/**
 * FT 可用性 — ForEach 时区绑定（不依赖 item / forEachItem）
 *
 * 用法（Apifox）：
 * 1) 加 ForEach，循环次数 = 下面 TZ_LIST 长度（或先只测前 3 条：改 FT_FOREACH_LIMIT）
 * 2) ForEach 虚线框内顺序：
 *    a. 本脚本（前置）
 *    b. apifox_pre_ft_availability.js（前置）
 *    c. POST /v2/resources/prebookings/availability
 *    d. apifox_post_ft_availability.js（后置）
 * 3) ForEach 数据可随便填相同次数的占位数组，例如：
 *    [{"i":0},{"i":1},{"i":2}]  — 真正时区从本脚本 TZ_LIST 按计数取
 *
 * 环境：
 *   ft_foreach_idx   自动维护，从 0 递增；重跑前可手动清掉
 *   FT_FOREACH_LIMIT 可选，限制只跑前 N 条（默认跑满 TZ_LIST）
 */
function Env(key, defVal) {
  var v = "";
  try {
    v = pm.environment.get(key);
  } catch (e) {}
  if (v === null || v === undefined || v === "") return defVal === undefined ? "" : defVal;
  return String(v);
}

var TZ_LIST = [
  { tz: "Asia/Shanghai", offset: "8" },
  { tz: "Europe/London", offset: "1" },
  { tz: "America/New_York", offset: "-4" },
  { tz: "Pacific/Midway", offset: "-11" },
  { tz: "Pacific/Honolulu", offset: "-10" },
  { tz: "America/Anchorage", offset: "-8" },
  { tz: "America/Los_Angeles", offset: "-7" },
  { tz: "America/Denver", offset: "-6" },
  { tz: "America/Chicago", offset: "-5" },
  { tz: "America/Halifax", offset: "-3" },
  { tz: "America/Sao_Paulo", offset: "-3" },
  { tz: "UTC", offset: "0" },
  { tz: "Europe/Paris", offset: "2" },
  { tz: "Europe/Moscow", offset: "3" },
  { tz: "Asia/Dubai", offset: "4" },
  { tz: "Asia/Bangkok", offset: "7" },
  { tz: "Asia/Tokyo", offset: "9" },
  { tz: "Australia/Sydney", offset: "10" },
  { tz: "Pacific/Auckland", offset: "12" }
];

var limit = parseInt(Env("FT_FOREACH_LIMIT", String(TZ_LIST.length)), 10);
if (isNaN(limit) || limit < 1) limit = TZ_LIST.length;
if (limit > TZ_LIST.length) limit = TZ_LIST.length;

var idx = parseInt(Env("ft_foreach_idx", "0"), 10);
if (isNaN(idx) || idx < 0) idx = 0;
if (idx >= limit) idx = 0;

var row = TZ_LIST[idx];
pm.environment.set("ft_tz_offset_hours", String(row.offset));
pm.environment.set("ft_tz_name", row.tz);
pm.environment.set("ft_date_mode", "past_local");
pm.environment.set("ft_expect_type", "fail_past");
pm.environment.set("ft_expect_errCode", "500.020.030");
pm.variables.set("case_id", "过去时间-" + row.tz);

pm.environment.set("ft_foreach_idx", String(idx + 1));

console.log(
  "[ft-foreach] idx=",
  idx,
  "tz=",
  row.tz,
  "offset=",
  row.offset,
  "nextIdx=",
  idx + 1
);
