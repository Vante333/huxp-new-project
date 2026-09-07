# Q3-SP4 四个需求 · Pre 验收测试用例

来源：桌面《需求测试用例.xmind》（2026-09-04）  
下周二上 **pre** → pre 通过再上 **生产** → 上线后你做 **主流程回归**。  
接口自动化已按截图模板落到 Apifox：`P1（全量用例）/功能名/按XMind用例/0N分类`。

环境统一：沙箱 `https://developer-sandbox.dragonpass.com/api`，Header `x-version=canary`，**每条都要 Token + X-Request-ID（36 位 UUID）**。

| 需求 | 接口 | 用哪套 Program | 预调试结果（2026-09-04） |
|------|------|----------------|--------------------------|
| 一、SSO免登短链 | `POST /v2/sso/links` | AllCategories `1919256841868288` | **已通**：列表、详情（详情单用 FT 单，不要用休息室 SL） |
| 二、FT可用性 | `POST /v2/resources/prebookings/availability` 等 | 同上，资源 `C10826` | **已通**：过去时间 `500.020.030`；未来 `available=true`；039/040/045 也能打出 |
| 三、支付链接 | `POST /v2/orders/payments` | **会籍购买** `2032786406298624` + 待支付 **MS** 单 | 超上限 `1801` → `301.000.001` 已通。SSO 使用单会 `802/804`，不能当支付成功样例 |
| 四、Auth双密钥 | `POST /v2/auth/token` | 鉴权1/鉴权2 同一 Program | 桌面《测试数据集123》当前沙箱返回 `201.000.001 invalid secret`，要换仍有效的两套密钥 |

---

# 需求一、SSO免登短链

## 第一步 总结需求（用最通俗的话）

合作方不用自己做登录页。调我们接口，我们给一条**短时间有效的短链**。会员点开就能直接进「订单列表」或「某一张订单详情」，看起来像已经登录了。

## 第二步 列出新增功能

- 新接口：`POST /v2/sso/links`
- 场景：`ORDER_LIST`（列表）、`ORDER_DETAIL`（详情，要带 `extra.orderId`）
- 可带语种 `language`、有效期 `durationInSeconds`、回跳 `returnUrl`

## 第三步 列出修改功能

- 无旧接口改造。详情场景不支持休息室预约单（会 `500.000.603`），要用 FT 使用单。

## 第四步 列出影响范围

- 上游：Token 必须和 Program、会籍是一套
- 下游：短链打开后的 H5 页、语种展示
- 数据：会籍 `8576507744260001`；详情单 `FT20260904BG5VM58`

## 第五步 输出测试点

必填、参数标准化（含 29 语种）、异常、边界 60~7200、打开短链、过期。短链多次是否同一条：脑图已标「不用管」。

## 第六步 输出正常流程测试

1. 先 `POST /v2/auth/token` 拿到 Token。  
2. Body（列表，与脑图一致）：

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "language": "en-US",
  "durationInSeconds": 1800
}
```

3. 期望：`code=0`，有 `entry.shortUrl`、`entry.validUntil`。  
4. 详情把 `scene` 改成 `ORDER_DETAIL`，加 `"extra": { "orderId": "FT20260904BG5VM58" }`。

## 第七步 输出异常测试

- 不传 `scene` → 失败  
- 详情不传 / 空 `extra.orderId` → `500.000.602`  
- 休息室 `SL…` 详情 → `500.000.603`（不是你参数填错，是场景不支持）  
- 无 Token → 401  
- `es-419` → 现网 `301.000.001`（已知缺陷，Pre 仍按失败记，不要改预期为成功）

## 第八步 输出边界测试

- `durationInSeconds=60` 成功；`59` / `7201` 失败；`7200` 成功。

## 第九步 输出接口测试点

Header：`Authorization: Bearer <token>`、`X-Program-ID: 1919256841868288`、`x-version: canary`、`X-Request-ID`。  
Apifox：已有 `SSO免登短链 · 01~06`；P0 新增 `SSO免登短链 · 冒烟`。

## 第十步 输出需要回归的功能

订单列表/详情短链能打开、过期后不能免登。上线后主流程回归只跑：换 Token → 列表链 → 打开 → 详情链（FT 单）→ 打开。

---

# 需求二、FT可用性（含错误码迁移）

## 第一步 总结需求（用最通俗的话）

查 Fast Track 能不能预约时，如果预约时间已经**早于网点当地当前时间**，要直接拒绝，错误码 **`500.020.030`**，文案是当地时间不能早于现在。  
另外，会籍购买那串旧码 `500.020.030~035` **让路**，改成 `500.030.039~044`；查购买详情失败新增 **`500.030.045`**。  
记住：availability 的 `500.020.030` 和会籍的 `500.030.039` **不是一回事**。

## 第二步 列出新增功能

- 过去时间拦截 `500.020.030`  
- 购买详情 `500.030.045`

## 第三步 列出修改功能

| 旧码 | 新码 | 接口 |
|------|------|------|
| 500.020.030 | 500.030.039 | 会籍 Preview |
| 500.020.031 | 500.030.040 | 会籍 Create |
| 500.020.032 | 500.030.041 | Preview/Create 已有订阅 |
| 500.020.033 | 500.030.042 | 不支持自动续费 |
| 500.020.034 | 500.030.043 | 取消订阅无计划 |
| 500.020.035 | 500.030.044 | 取消失败 |

## 第四步 列出影响范围

- FT：`module=2`，资源时区  
- 会籍购买 Preview/Create/details/取消  
- 空时区网点（要后台造数）

## 第五步 输出测试点

过去/未来、跨时区、29 时区抽样、空时区、039~045、旧码不得再出现在会籍接口。

## 第六步 输出正常流程测试

Body（未来时间，脚本会改成当地+10 天 `T10:00`）：

```json
{
  "module": 2,
  "resourceId": "C10826",
  "prebookingDate": "2026-09-14T10:00",
  "adultCount": 1,
  "childCount": 0
}
```

期望：`code=0`，**不是** `500.020.030`。

## 第七步 输出异常测试

过去时间（当地 -30 分钟）期望：

- `errCode=500.020.030`
- 文案：`The prebooking time cannot be earlier than the current local time.`

会籍（同一套 SSO Token 在 AllCategories 已打通）：

- Preview `autoRenewal=true` → `500.030.039`
- Create `autoRenewal=false` → `500.030.040`
- `purchase/details` + `orderId=9999999999999999` → `500.030.045`  
  文案：`Sorry, we're unable to retrieve the order details at the moment. Please try again later.`
- 取消 `membershipId=0000000000000000` → `500.030.044`

## 第八步 输出边界测试

刚好过 1 分钟、夏令时临界、时区为空（无资源则跳过，不要用你电脑时区去猜）。

## 第九步 输出接口测试点

`POST /v2/resources/prebookings/availability`  
`POST /v2/orders/memberships/purchase/preview`  
`POST /v2/orders/memberships/purchase`  
`POST /v2/orders/memberships/purchase/details`  
`POST /v2/memberships/subscriptions/cancellation`  

Apifox：`FT可用性 · 01~04`，P0 `FT可用性 · 冒烟`。

## 第十步 输出需要回归的功能

FT 选未来时段仍可约；会籍购买失败码是新码不是旧码。上线主流程：未来可约一次 + Preview 失败仍是 039 不是 030。

---

# 需求三、支付链接

## 第一步 总结需求（用最通俗的话）

对待支付订单生成收银台链接。可以指定页面语种，也可以指定链接活多久。不传语种按 **en-US**；不传有效期按 **600 秒**；最长 **1800 秒**。

## 第二步 列出新增功能

- Body 增加 `language`、`durationInSeconds`

## 第三步 列出修改功能

- 原支付链接接口增加上述两个可选字段；超 1800 要拒绝。

## 第四步 列出影响范围

- 收银台 H5 语种、链接过期后不能再付  
- **必须用会籍待支付 MS 单**，Program=`2032786406298624`。SSO 下的 FT/Lounge 使用单会 `500.000.802`（不用付）或 `500.000.804`

## 第五步 输出测试点

12 个语种（脑图名单，含 zh-TW / en-GB / id-ID）、默认语种、60/1800/1801、过期后打开。

## 第六步 输出正常流程测试

1. 会籍 Program 换 Token。  
2. 先有待支付 `MS…` 单，写入环境 `pay_orderId`。  
3. Body（与脑图一致）：

```json
{
  "orderId": "{{pay_orderId}}",
  "returnUrl": "https://www.ly.com",
  "paymentMethod": "H5_CASHIER",
  "language": "en-US",
  "durationInSeconds": 1800
}
```

4. 期望：`code=0`，有支付 url。不传 `language` 仍成功，按 en-US。

脑图 12 语种：`zh-CN, en-US, zh-TW, zh-HK, vi-VN, pt-BR, es-ES, en-GB, id-ID, th-TH, ja-JP, ko-KR`。以前 zh-TW/en-GB/id-ID 未加白名单，开发已加，Pre 要再扫一遍。

## 第七步 输出异常测试

- `durationInSeconds=1801` → 失败。canary 实测：`301.000.001`（字段格式/范围非法），HTTP 可能 400。  
- 已支付/0 元单 → `500.000.802`  
- Token 与订单 Program 不一致 → `201.000.001`

## 第八步 输出边界测试

60 秒内能打开；过期后不能付（这条要手工打开 `pay_last_url`）。

## 第九步 输出接口测试点

`POST /v2/orders/payments`，Header 必须带 Token。  
Apifox：`支付链接 · 01语种` / `02有效期`；P0 `支付链接 · 冒烟`（1801 不依赖可支付单，可先跑通）。

## 第十步 输出需要回归的功能

会籍下单后仍能出支付链接、付完状态变化。上线主流程：造 1 笔 MS 待支付 → 出链 → 打开收银台（看语种）→ 不必真付也可，生产回归按你们支付安全规范。

---

# 需求四、Auth双密钥

## 第一步 总结需求（用最通俗的话）

一个 Program 可以配 **两把钥匙**。用钥匙 1 或钥匙 2 都能取出 Token，都能跑原来的 P0 业务。算法可以是 HS256 或 RS256，四种组合都要能用。后台还能增、改、删其中一把，剩下那把不能中断。

## 第二步 列出新增功能

- 双密钥同时有效  
- RS256 签发  
- 密钥增删改

## 第三步 列出修改功能

- 原来只有一把 secret 取 Token；现在两套 `clientId/secret`（或公私钥）都能签。

## 第四步 列出影响范围

- 所有依赖 `POST /v2/auth/token` 的业务链  
- BOSS 密钥配置页  
- 不能出现「用钥匙 1 的 Token 却去验钥匙 2」的串台

## 第五步 输出测试点

两套 Token 跑 lounge/membership P0；RS256/HS256 四种组合；增/改/删密钥。

## 第六步 输出正常流程测试

1. 环境写入 **当前有效** 的 `auth1_clientId/auth1_secret`、`auth2_*`（不要用已经 201 的旧表）。  
2. `POST /v2/auth/token` Body：`{"clientId":"...","secret":"..."}`，Header `X-Program-ID` 与密钥同一 Program。  
3. 两套都 `code=0` 且有 `accessToken`。  
4. 各带 Token 打一条 P0（可用性或会籍 Preview）。

## 第七步 输出异常测试

- 旧 secret → `201.000.001`（今天桌面数据集123就是这个，说明密钥已轮换）  
- 删掉的那把不能再签发  
- 改算法后不能再用旧算法的假 Token 过验

## 第八步 输出边界测试

只剩一把时行为与历史单密钥相同。

## 第九步 输出接口测试点

`POST /v2/auth/token`。RS256 组合和增删改以 **BOSS 手工 + 再调 token** 为主。  
Apifox：`Auth双密钥 · 02/03/04`。

## 第十步 输出需要回归的功能

上线后主流程：用生产两套密钥各取一次 Token，再跑 1 条业务冒烟。不要在生产做删密钥试验。

---

# Pre / 生产 / 上线后主流程，怎么分工

**下周二 Pre（自动化 + 少量手工）**

1. P0 冒烟：SSO 列表+详情、FT 过去/未来、支付 1801、（密钥有效时）双钥取 Token  
2. P1 按XMind：SSO 01~06（已有）、FT 01~03、支付 01~02（先有 MS 待支付单）、Auth 02  
3. 手工：打开 SSO 短链、支付链过期、BOSS 双密钥增删改 / RS256

**生产上线后（你做主流程回归，不要把 P1 全量当生产回归）**

1. SSO：列表短链打开  
2. FT：未来时段可约，不要用过去时间在生产压 030（避免脏数据；若要验证，用明确可造的测试资源）  
3. 支付：1 笔待支付出链（按生产支付规范，能出链即可）  
4. Auth：两套生产密钥各取 Token 成功

---

# 新人最容易漏测的地方

1. **Token、Program、订单不是一套**：SSO 的 Token 去打会籍支付 / 会籍 Program 去打开 SSO，常见 `201.000.001`。  
2. **忘了 `X-Request-ID`**：不是 36 位 UUID 会 `301.000.001`，看起来像参数错了。  
3. **SSO 详情用了休息室 SL 单**：会 `603`，误以为详情功能坏了。要用 FT 单。  
4. **用 availability 去验会籍 039**：030 和 039 会测串。  
5. **支付用 0 元/权益单去验语种**：一定 `802`，语种根本走不到收银台。  
6. **Apifox 点「运行」被前置脚本改 Body**：单条请点「发送」，看「实际请求」是不是脑图那个 JSON。  
7. **双密钥还用桌面旧 secret**：已经 `invalid secret`，不是接口没上。  
8. **`es-419`、支付超 1800**：分别是 Pattern 缺陷和 `301.000.001`，Pre 要带着已知问题进，不要临时改预期。
