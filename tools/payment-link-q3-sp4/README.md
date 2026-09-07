# PAPI-3135 支付链接（语种 + 有效期）Apifox 自动化说明

对应：
- Jira：PAPI-2834 / PAPI-3135（Q3-SP4）
- 用例：桌面《需求测试用例.xmind》→ **三、支付链接**
- 接口：`POST /v2/orders/payments`
- 代码仓：`business-international-developer-api`（`OrderV2Controller#payments`）

> **重要**：当前本地 `master` 的 `SaasPaymentUrlReqDto` **尚未包含** `language` / `durationInSeconds`。  
> 请在**已发布该需求的测试环境**跑本脚本；若仍忽略新字段，找开发确认分支/发版。

---

## 一、文件清单

目录：`D:\api\interface_cursor\tools\payment-link-q3-sp4\`

| 文件 | 用途 |
|------|------|
| `apifox_pre_payments_language_duration.js` | 前置：组装 Body（按用例决定是否带 language/duration） |
| `apifox_post_payments_language_duration.js` | 后置：成功断言 url + validUntil；超上限断言失败 |
| `PAPI-3135-支付链接-语种有效期.postman_collection.json` | 可导入 Apifox 的用例目录骨架 |
| `PAPI-3135-支付链接-轻量可导入.postman_collection.json` | 轻量导入版（易预览成功） |
| `PAPI-3135-支付链接-19语种遍历.postman_collection.json` | （旧）H5Sso 19 语种，可忽略 |
| `PAPI-3135-支付链接-语种遍历-BOSS-API.postman_collection.json` | **实际口径** BOSS-API 26 语种遍历 |
| `pay_languages_boss_api.csv` | 自动化「测试数据」CSV（26） |
| `pay_languages_list.json` / `pay_languages_list.js` | ForEach 轮询列表（26） |
| `本 README` | 操作步骤 |

---

## 二、Apifox 导入与配置（逐步）

### 1. 导入集合
1. 打开 Apifox → 你的项目（如 FT/可用性/免登 同环境）
2. **导入** → 选 Postman → 选择  
   `PAPI-3135-支付链接-语种有效期.postman_collection.json`
3. 导入后左侧出现文件夹「PAPI-3135 支付链接-语种与有效期(Q3-SP4)」

### 2. 环境变量（Environment）必填
| 变量名 | 示例 | 说明 |
|--------|------|------|
| `baseUrl` | `https://developer-sandbox.dragonpass.com/api` | 不要末尾多余斜杠或按你们习惯统一 |
| `accessToken` | 先调 `/v2/auth/token` 拿到 | Bearer，不要带 Bearer 前缀就写在变量里，Header 里加 |
| `programId` | 你的 Program | Header `X-Program-ID` |
| `pay_orderId` | 如 `MS20260831BDVZ9ZQ` | **待支付、可生成支付链接**的订单 |
| `pay_returnUrl` | `https://example.com/payment/return` | 合法 URL |
| `pay_paymentMethod` | `H5_CASHIER` 或 `MS_CASHIER` | 以你们环境枚举为准（Jira 样例 MS_CASHIER，旧代码多 H5_CASHIER） |
| `pay_duration_default` | `600` | 与用例一致 |
| `pay_duration_max` | `1800` | **用例上限**；若按 Jira 图注改为 `12000` |
| `pay_assert_validUntil` | `true` | 是否校验 validUntil 时间窗 |
| `pay_validUntil_skew_sec` | `15` | 允许误差秒数 |

### 3. 脚本说明
集合 JSON **已内联**前置/后置脚本，导入后一般不用再粘贴。  
若你想单独维护脚本：用 `apifox_pre_*.js` / `apifox_post_*.js`，或改完后执行  
`node build_collection.js` 重新生成集合。

### 4. 怎么跑
- 单条：打开用例 → **发送**
- 整夹：选文件夹 → **运行**（自动化）

---

## 三-附、语种遍历（以 BOSS-API 为准，共 26）

### ForEach 直接贴这个数组

```json
[
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
]
```

- 组1（14）：en-US ~ es-419  
- 组2（12）：fr-CA ~ hu-HU  

导入集合用：`PAPI-3135-支付链接-语种遍历-BOSS-API.postman_collection.json`  
CSV：`pay_languages_boss_api.csv`

循环体内：`"language": "{{item}}"`（或你 ForEach 当前项变量名）。

> 同一待支付单多次生成链接一般可以；若从第 2 个语种开始失败，换新待支付单或问开发。  
> 页面是否真切换语种：打开返回的 url 人工抽查即可。

---

## 三、用例 ↔ 脚本 case_id（备份节，见上表）

| XMind 用例 | case_id | Body 要点 | 断言 |
|------------|---------|-----------|------|
| language默认en-US | `LANG_DEFAULT` | 不传 language | 成功 + 有 url |
| language指定en-US | `LANG_EN` | language=en-US | 成功 + 有 url（语种需打开支付页人工看） |
| duration默认600 | `DUR_DEFAULT` | 不传 duration | 成功；validUntil≈now+600s |
| duration=60 | `DUR_60` | 60 | 成功；validUntil≈now+60s |
| duration上限1800 | `DUR_MAX` | =pay_duration_max | 成功 |
| duration超上限1801 | `DUR_OVER` | max+1 | **业务失败** |
| 链接过期不可支付 | `EXPIRY_CREATE_60` | 60 | 成功出链后 **手工** 等过期打开 |
| 覆盖语种遍历 | BOSS-API 26 | 逐个 `language=` | 不报错 + 有 url |

---

## 三-附旧说明（已废弃）

~~19 语种 H5Sso~~ 已改为 BOSS-API 26，见上节。

### 方式 A：导入集合（推荐）
1. 导入 `PAPI-3135-支付链接-语种遍历-BOSS-API.postman_collection.json`（选 **Postman**）
2. 环境配好：`pay_orderId`、`pay_returnUrl`、`pay_paymentMethod`、`access_token`、`Program-ID`、`baseUrl`
3. 跑文件夹「1.BOSS组1」+「2.BOSS组2」
4. 跑完看环境变量：`pay_lang_ok_list` / `pay_lang_fail_list`

### 方式 B：自动化场景 + CSV
1. 场景里加一步 `POST /v2/orders/payments`
2. 前置/后置分别贴 `apifox_pre_payments_lang_traverse.js`、`apifox_post_payments_lang_traverse.js`
3. 「测试数据」导入 `pay_languages_boss_api.csv`（列名 `language`）
4. 运行（会按行循环）

### 方式 C：ForEach 列表轮询（推荐你这种用法）
见本节上方数组。

或导入文件：`pay_languages_list.json` / 脚本 `pay_languages_list.js`。

循环体内支付接口 Body：`"language": "{{item}}"` 或 `"language": "{{language}}"`（以你 ForEach 当前项变量名为准）。

> 同一待支付单多次生成链接一般可以；若从第 2 个语种开始失败，换新待支付单或问开发。  
> 页面是否真切换语种：打开返回的 url 人工抽查即可。

---

## 四、与代码/文档差异（测前知晓）

1. **master 代码**尚未接 `language`→`lg`、`durationInSeconds`→`expireIn`；环境未发版时自动化会「成功但 validUntil 不随入参变」。  
2. XMind 上限 **1800**；Jira 图注有 **默认600、最长12000**——以联调确认后改 `pay_duration_max`。  
3. `paymentMethod`：代码侧常见 `H5_CASHIER`；Jira 样例 `MS_CASHIER`——以沙箱能通的为准。

---

## 五、手工样例 Body（对照）

```json
{
  "orderId": "{{pay_orderId}}",
  "returnUrl": "https://example.com/payment/return",
  "paymentMethod": "H5_CASHIER",
  "language": "en-US",
  "durationInSeconds": 60
}
```

映射（需求）：`language` 不转换直接作 SaaS `lg`；`durationInSeconds` → `expireIn`。
