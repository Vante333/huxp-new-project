/**
 * 生成 FT 可用性 Postman/Apifox 集合
 * 用例名用业务描述，不加 P0/序号前缀
 * 运行：node build_collection.js
 */
const fs = require("fs");
const path = __dirname;

const pre = fs.readFileSync(path + "/apifox_pre_ft_availability.js", "utf8").split(/\r?\n/);
const post = fs.readFileSync(path + "/apifox_post_ft_availability.js", "utf8").split(/\r?\n/);

function setupLines(opts) {
  const lines = [];
  Object.keys(opts).forEach(function (k) {
    const v = opts[k];
    if (v === true) lines.push("pm.variables.set('" + k + "','true');");
    else if (v === false) lines.push("pm.variables.set('" + k + "','false');");
    else if (v === null || v === undefined) lines.push("pm.variables.set('" + k + "','');");
    else lines.push("pm.variables.set('" + k + "'," + JSON.stringify(String(v)) + ");");
  });
  return lines;
}

function makeItem(name, opts, desc, bodyObj) {
  const body =
    bodyObj ||
    {
      module: 2,
      resourceId: "{{fastTrackResourceId}}",
      prebookingDate: "{{ft_last_prebookingDate}}",
      adultCount: 1,
      childCount: 0,
      membershipId: "{{membershipId}}"
    };
  return {
    name: name,
    event: [
      {
        listen: "prerequest",
        script: { type: "text/javascript", exec: setupLines(opts).concat(pre) }
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
        { key: "X-Program-ID", value: "{{Program-ID}}" },
        { key: "x-version", value: "{{x-version}}" },
        { key: "X-Request-ID", value: "{{$guid}}" }
      ],
      body: {
        mode: "raw",
        raw: JSON.stringify(body, null, 2),
        options: { raw: { language: "json" } }
      },
      url: {
        raw: "{{baseUrl}}/v2/resources/prebookings/availability",
        host: ["{{baseUrl}}"],
        path: ["v2", "resources", "prebookings", "availability"]
      },
      description: desc || name
    }
  };
}

/** purchase/details 补充码 */
function makeDetailsItem(name, opts, desc) {
  const setup = setupLines(opts);
  const postDetails = [
    "const json = pm.response.json();",
    "const errCode = String(json.errCode || json.errorCode || '');",
    "const msg = String(json.msg || '');",
    "const expectErr = '" + (opts.ft_expect_errCode || "500.030.045") + "';",
    "pm.test('[" + name + "] HTTP 可到达', function () {",
    "  pm.expect(pm.response.code).to.be.oneOf([200,400,401,403,404,422,500]);",
    "});",
    "pm.test('[" + name + "] errCode=' + expectErr, function () {",
    "  pm.expect(errCode, 'msg=' + msg).to.eql(expectErr);",
    "});",
    "pm.test('[" + name + "] 文案含 order details', function () {",
    "  pm.expect(/order details|订单详情|unable to retrieve/i.test(msg), 'msg=' + msg).to.eql(true);",
    "});",
    "console.log('[ft-details]', errCode, msg);"
  ];
  return {
    name: name,
    event: [
      {
        listen: "prerequest",
        script: {
          type: "text/javascript",
          exec: setup.concat([
            "console.log('[ft-details] 请按可复现失败场景准备 orderId / 入参');"
          ])
        }
      },
      {
        listen: "test",
        script: { type: "text/javascript", exec: postDetails }
      }
    ],
    request: {
      method: "POST",
      header: [
        { key: "Content-Type", value: "application/json" },
        { key: "Authorization", value: "Bearer {{access_token}}" },
        { key: "X-Program-ID", value: "{{Program-ID}}" },
        { key: "x-version", value: "{{x-version}}" },
        { key: "X-Request-ID", value: "{{$guid}}" }
      ],
      body: {
        mode: "raw",
        raw: JSON.stringify(
          {
            orderId: "{{ft_details_fail_orderId}}"
          },
          null,
          2
        ),
        options: { raw: { language: "json" } }
      },
      url: {
        raw: "{{baseUrl}}/v2/orders/memberships/purchase/details",
        host: ["{{baseUrl}}"],
        path: ["v2", "orders", "memberships", "purchase", "details"]
      },
      description: desc || name
    }
  };
}

const folder1 = {
  name: "1.过去时间拦截",
  item: [
    makeItem(
      "过去时间拦截",
      {
        case_id: "过去时间拦截",
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "prebookingDate=资源当地过去时间 → 500.020.030"
    ),
    makeItem(
      "时区换算校验-当地已过调用方未过",
      {
        case_id: "时区换算校验",
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "环境 ft_tz_offset_hours 填「非本机」资源偏移；仍应按资源当地判过去 → 500.020.030"
    ),
    makeItem(
      "未来时间不报该错",
      {
        case_id: "未来时间不报该错",
        ft_date_mode: "future_local",
        ft_expect_type: "success"
      },
      "当地未来时间：成功且不返回 500.020.030（available 视库存可为 false）"
    ),
    makeItem(
      "未来时间可约出Token",
      {
        case_id: "未来时间可约出Token",
        ft_date_mode: "future_local",
        ft_expect_type: "success_slot"
      },
      "同资源有库存时：available=true 且有 prebookingToken"
    )
  ]
};

/** 29 时区：循环用对象数组 + 同一条模板（集合内放说明 + 示例 3 条，全量用 ForEach） */
const sampleTz = [
  { name: "Asia/Shanghai", offset: "8" },
  { name: "Europe/London", offset: "1" },
  { name: "America/New_York", offset: "-4" }
];

const folderTzLoop = {
  name: "1b.多时区过去时间抽样",
  description:
    "完整 29 时区请在 Apifox ForEach 贴 ft_timezones_sample.json；此处仅放 3 条抽样。每条改环境 ft_tz_offset_hours 或用例变量。",
  item: sampleTz.map(function (tz) {
    return makeItem(
      "过去时间-" + tz.name,
      {
        case_id: "过去时间-" + tz.name,
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "请先将环境 ft_tz_offset_hours=" +
        tz.offset +
        "，资源换为该时区网点；期望 500.020.030"
    );
  })
};

const folder2 = {
  name: "2.错误码迁移",
  description:
    "需按原业务场景触发；脚本只断言新码。旧码 500.020.030~035 的旧含义不应再出现。注意：新增「过去时间」也占用 500.020.030，与迁移表冲突，执行前与开发确认码表。",
  item: [
    ["原场景迁移为500.030.039", "500.030.039", "500.020.030"],
    ["原场景迁移为500.030.040", "500.030.040", "500.020.031"],
    ["原场景迁移为500.030.041", "500.030.041", "500.020.032"],
    ["原场景迁移为500.030.042", "500.030.042", "500.020.033"],
    ["原场景迁移为500.030.043", "500.030.043", "500.020.034"],
    ["原场景迁移为500.030.044", "500.030.044", "500.020.035"]
  ].map(function (row) {
    return makeItem(
      row[0],
      {
        case_id: row[0],
        ft_date_mode: "keep_body",
        ft_expect_type: "fail_err",
        ft_expect_errCode: row[1]
      },
      "触发原 " + row[2] + " 业务场景后，期望新码 " + row[1] + "；Body 请按可复现场景手改（keep_body）"
    );
  })
};

const folder3 = {
  name: "3.补充错误码-purchase细节",
  item: [
    makeDetailsItem(
      "memberships/purchase/details返回补充错误",
      { case_id: "purchase/details补充错误", ft_expect_errCode: "500.030.045" },
      "环境变量 ft_details_fail_orderId=可触发失败的订单；期望 500.030.045"
    )
  ]
};

const folder4 = {
  name: "4.时区特殊场景",
  description: "冬夏令时 / 空时区；部分预期待开发确认，默认 record_only 或按注释改 expect。",
  item: [
    makeItem(
      "夏令时资源按夏令时偏移判断过去时间",
      {
        case_id: "夏令时过去时间",
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "资源选 Europe/London 等 DST 区；ft_tz_offset_hours 填当前夏令时偏移"
    ),
    makeItem(
      "冬令时资源按冬令时偏移判断过去时间",
      {
        case_id: "冬令时过去时间",
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "同资源冬令时偏移填入 ft_tz_offset_hours"
    ),
    makeItem(
      "夏令时切换日春拨快边界",
      {
        case_id: "春拨快边界",
        ft_date_mode: "custom",
        ft_expect_type: "record_only"
      },
      "手工设 ft_prebookingDate 为切换日临界；先 record 再固化预期"
    ),
    makeItem(
      "冬令时切换日秋拨慢边界",
      {
        case_id: "秋拨慢边界",
        ft_date_mode: "custom",
        ft_expect_type: "record_only"
      },
      "手工设重叠小时附近时间；先记录实际码"
    ),
    makeItem(
      "无冬夏令时时区不受DST影响",
      {
        case_id: "固定时区不受DST影响",
        ft_date_mode: "past_local",
        ft_expect_type: "fail_past",
        ft_expect_errCode: "500.020.030"
      },
      "Asia/Shanghai 等；ft_tz_offset_hours=8"
    ),
    makeItem(
      "网点时区为空字符串",
      {
        case_id: "时区空串",
        ft_date_mode: "future_local",
        ft_expect_type: "record_only"
      },
      "资源时区配置为空；记录实际 errCode/是否兜底"
    ),
    makeItem(
      "网点时区为null或不返回",
      {
        case_id: "时区null",
        ft_date_mode: "future_local",
        ft_expect_type: "record_only"
      },
      "与空串区分造数；记录实际行为"
    ),
    makeItem(
      "时区为空时过去时间是否仍拦截",
      {
        case_id: "空时区过去时间",
        ft_date_mode: "past_local",
        ft_expect_type: "record_only"
      },
      "确认兜底时区后可改为 fail_past"
    ),
    makeItem(
      "时区为空时未来时间是否可约",
      {
        case_id: "空时区未来时间",
        ft_date_mode: "future_local",
        ft_expect_type: "record_only"
      },
      "确认兜底后可改为 success / success_slot"
    )
  ]
};

const collection = {
  info: {
    _postman_id: "papi-ft-availability-filter-past-q3sp4",
    name: "FT可用性-过滤过去时间(Q3-SP4)",
    description:
      "来源：桌面《需求测试用例.xmind》二、FT可用性 + 需求 PAPI-2894/PAPI-3098。\n接口：POST /v2/resources/prebookings/availability（FT module=2）。\n用例名不加自动化序号。\n环境：baseUrl、access_token、Program-ID、x-version、fastTrackResourceId、membershipId、ft_tz_offset_hours。",
    schema: "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  variable: [
    { key: "ft_module", value: "2" },
    { key: "ft_adultCount", value: "1" },
    { key: "ft_childCount", value: "0" },
    { key: "ft_future_days", value: "10" },
    { key: "ft_past_minutes", value: "30" }
  ],
  item: [folder1, folderTzLoop, folder2, folder3, folder4]
};

const out = path + "/PAPI-FT可用性-过滤过去时间.postman_collection.json";
fs.writeFileSync(out, JSON.stringify(collection, null, 2), "utf8");
console.log("written", out);
