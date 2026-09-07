# FT 可用性 — 过滤过去时间（Q3-SP4）自动化说明

对应：
- 桌面《需求测试用例.xmind》→ **二、FT可用性**
- 需求：PAPI-2894 / PAPI-3098（过滤已过时段 + 错误码）
- 接口：`POST /v2/resources/prebookings/availability`（FT：`module=2`）

用例名称使用业务描述，**不加** P0/序号前缀。

---

## 一、文件清单

| 文件 | 用途 |
|------|------|
| `PAPI-FT可用性-过滤过去时间.postman_collection.json` | **导入 Apifox** |
| `apifox_pre_ft_availability.js` | 前置（已内联） |
| `apifox_post_ft_availability.js` | 后置断言（已内联） |
| `ft_timezones_sample.json` | 多时区 ForEach 数据（29 条抽样） |
| `build_collection.js` | 改脚本后执行 `node build_collection.js` 重建 |

---

## 二、环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `baseUrl` | 是 | 如 `https://developer-sandbox.dragonpass.com/api` |
| `access_token` | 是 | 有效 JWT |
| `Program-ID` | 是 | 与 Token 同一套 |
| `x-version` | 建议 | `canary` |
| `fastTrackResourceId` | 是 | FT 资源 ID |
| `membershipId` | 建议 | 会籍号 |
| `ft_tz_offset_hours` | 是* | 该资源当地相对 UTC 偏移（上海 `8`，伦敦夏令时约 `1`） |
| `ft_past_minutes` | 否 | 构造「过去」默认 30 |
| `ft_future_days` | 否 | 构造「未来」默认 10 |
| `ft_details_fail_orderId` | 测 045 时 | 能触发 purchase/details 失败的订单 |

\* 测「过去/未来当地时间」必须填对偏移，否则会误判。

Header：`Bearer {{access_token}}`、`X-Program-ID`、`x-version`、合法 `X-Request-ID`。

---

## 三、集合目录

| 文件夹 | 覆盖 |
|--------|------|
| 1.过去时间拦截 | 过去→030、时区换算、未来不报错、可约出 Token |
| 1b.多时区过去时间抽样 | 3 条示例；全量用 ForEach + `ft_timezones_sample.json` |
| 2.错误码迁移 | 030~035 → 039~044（需按原场景改 Body，`keep_body`） |
| 3.补充错误码 | `purchase/details` → `500.030.045` |
| 4.时区特殊场景 | 冬夏令时 / 空时区（部分 `record_only`） |

---

## 四、怎么跑（新人）

1. Apifox → **导入** → Postman → 选本集合 JSON  
2. 环境配好上表变量（`ft_tz_offset_hours` 与资源一致）  
3. 先跑 **「过去时间拦截」**、**「未来时间不报该错」**  
4. 成功标准：  
   - 过去：`errCode=500.020.030`，文案含 current local time / 早于当前  
   - 未来：`code=0`，且不是 030  

### 多时区 ForEach（可选）

1. 自动化加 ForEach，数组贴 `ft_timezones_sample.json`  
2. 循环里：自定义脚本 `pm.environment.set("ft_tz_offset_hours", String(当前项.offset))`（按你 ForEach 变量写法调整）  
3. 再调可用性接口（过去时间模式）  
4. 每个时区资源 ID 若不同，需在数据里加 `resourceId` 字段并写入环境  

---

## 五、重要注意

1. **码表冲突**：需求「新增过去时间 = 500.020.030」与「旧 500.020.030 迁到 500.030.039」并存，跑迁移用例前务必问开发最终码表。  
2. 前置会按 `ft_date_mode` **重写** `prebookingDate`；迁移场景用 `keep_body`，Body 按可复现场景手改。  
3. `success` 不强制 `available=true`（可能无库存）；要 Token 用 **「未来时间可约出Token」**。  
4. 空时区 / DST 切换日默认 `record_only`，确认预期后再改 `ft_expect_type`。

---

## 六、重建集合

```bash
cd d:\api\interface_cursor\tools\ft-availability-q3-sp4
node build_collection.js
```
