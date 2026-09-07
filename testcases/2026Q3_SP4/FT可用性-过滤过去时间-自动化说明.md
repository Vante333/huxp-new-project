# FT 可用性 — 过滤过去时间（接口自动化对照）

> 来源：桌面《需求测试用例.xmind》二、FT可用性  
> 自动化目录：`interface_cursor/tools/ft-availability-q3-sp4/`  
> 导入：`PAPI-FT可用性-过滤过去时间.postman_collection.json`

## 接口

`POST /v2/resources/prebookings/availability`  
FT：`module=2`，`resourceId={{fastTrackResourceId}}`，`prebookingDate=yyyy-MM-ddTHH:mm`

## 自动化已覆盖（名称无序号前缀）

### 过去时间拦截
- 过去时间拦截 → `500.020.030`
- 时区换算校验-当地已过调用方未过 → `500.020.030`
- 未来时间不报该错 → 成功且非 030
- 未来时间可约出Token → `available=true` + token

### 多时区抽样
- 过去时间-Asia/Shanghai / Europe/London / America/New_York  
- 全量 29 区见 `ft_timezones_sample.json`（ForEach）

### 错误码迁移（需手改 Body 触发原场景）
- 原场景迁移为 500.030.039 ~ 044（对应旧 030~035）

### 补充
- memberships/purchase/details → `500.030.045`

### 时区特殊
- 夏/冬令时过去时间、春拨快/秋拨慢（record）、固定时区、空时区四条（record）

## 环境要点

`ft_tz_offset_hours` 必须与资源当地 UTC 偏移一致，否则「过去/未来」构造会错。
