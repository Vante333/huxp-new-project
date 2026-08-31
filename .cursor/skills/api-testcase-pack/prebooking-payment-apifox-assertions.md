> **放置与读取方式**：本文件位于 **`.cursor/skills/api-testcase-pack/`**，与 [`SKILL.md`](./SKILL.md) 中「预预约 payment 断言（Lounge / FT）」互链。处理 **Membership 预预约 Preview / Create / Detail** 的 **Apifox 后置 payment 断言**、**预收费权益现金**、**lounge / fastTrack 算价校验** 时，Agent **先读本文件**，再改 Apifox 脚本或 `tools/payment-js/apifox_payment_assert_*.js`。  
> **扩品类场景/生成器**（非仅改断言脚本）另读：[`Prebooking-Payment-品类扩展指南.md`](../../../api-testcases/api_tests/apifox-cli/docs/Prebooking-Payment-品类扩展指南.md)。

# 预预约 payment 断言（Apifox · Lounge / FT 通用）

## 适用范围

| 模块 | Preview | Create | Detail |
|------|---------|--------|--------|
| **Lounge** | `POST /v2/orders/{modules}/memberships/prebooking/preview`（`modules=lounges`） | `POST /v2/orders/lounges/memberships/prebooking` | `POST /v2/orders/memberships/details` |
| **Fast Track** | 同上（`modules=fastTrack`） | `POST /v2/orders/fastTrack/memberships/prebooking` | 同上 |

- **响应路径**：`json.data.extra.payment`（兼容 `json.data.payment` / `json.payment`）。
- **需求来源**：[`requirements/2026Q2SP4/Confluence-1906049058.md`](../../../requirements/2026Q2SP4/Confluence-1906049058.md) §2.2.1 payment object；测试分析 [`testcases/2026Q2SP4/订单流-预览订单接口-预收费权益现金-测试分析-001.md`](../../../testcases/2026Q2SP4/订单流-预览订单接口-预收费权益现金-测试分析-001.md)。
- **脚本权威副本**（ES5 安全，Apifox 可直接粘贴）：
  - 通用前置：[`tools/payment-js/apifox_payment_assert_pre.js`](../../../tools/payment-js/apifox_payment_assert_pre.js)
  - 通用后置：[`tools/payment-js/apifox_payment_assert_post.js`](../../../tools/payment-js/apifox_payment_assert_post.js)
  - **客户预收款**前置：[`tools/payment-js/apifox_client_collect_assert_pre.js`](../../../tools/payment-js/apifox_client_collect_assert_pre.js)
  - **客户预收款**后置：[`tools/payment-js/apifox_client_collect_assert_post.js`](../../../tools/payment-js/apifox_client_collect_assert_post.js)

Lounge 与 FT **共用同一套断言逻辑**；差异仅在 URL path 中的 module 段（`lounges` / `fastTrack`）。

### 客户预收款专用（`CLIENT_COLLECT`）

**识别条件**（请求体，兼容 `extra` 嵌套）：

```json
"cashPaymentApplied": true,
"cashier": { "paymentMode": "CLIENT_COLLECT" }
```

| 阶段 | `payment.status` | `timeline` | `price/charges/deductions` |
|------|------------------|------------|----------------------------|
| Preview | `NO_PAYMENT_REQUIRED` | `null` | 均为 `null` |
| Create | `NO_PAYMENT_REQUIRED` | `null` | 不强制 null（按 SaaS） |
| Detail | `NO_PAYMENT_REQUIRED` | `null` | 不强制 null（按 SaaS） |

客户预收款用例使用 **`apifox_client_collect_assert_*.js`**，**不要**与通用 `apifox_payment_assert_post.js` 混用（避免 `payableAmount` 误分支）。

---

## Apifox 放置

1. **项目设置 → 公共脚本 → 前置操作**：粘贴 `apifox_payment_assert_pre.js` 全文。
2. **项目设置 → 公共脚本 → 后置操作**：粘贴 `apifox_payment_assert_post.js` 全文。
3. 或仅在 **预预约目录**（Preview / Create / Detail 三个接口所在文件夹）分别配置前置 + 后置。
4. **粘贴前清空旧脚本**，避免混入 `?.`、`??`、`✓`、`·` 等字符导致 `Invalid or unexpected token`。

---

## 阶段识别（前置脚本）

前置脚本 **按 URL 自动写入** `order_api_stage`（每次请求覆盖，避免 Detail 环境变量污染 Preview）：

| URL 特征 | `order_api_stage` |
|----------|-------------------|
| `/prebooking/preview` | `PREVIEW` |
| `/memberships/prebooking` 或 `/ePasses/prebooking`（不含 preview） | `CREATE` |
| `/orders/memberships/details`、`/orders/ePasses/details`、`/orders/esims/details` | `DETAIL` |

**手动覆盖**（少用）：设 `order_api_stage_force=true` 且配置 `order_api_stage`。

---

## 分支规则（后置脚本 · 按响应 `payableAmount`）

**权益抵扣到 0 元识别**（优先于「客户预收」）：`originalAmount = discountAmount` 且 `payableAmount = 0`（`Round2` 后相等）。此时 `price/charges/deductions` 按 SaaS 返回，并执行 C-1～C-3。

**权益支付与现金**：payment 返回预期相同（完整金额模块 + 按下表分支）；**勿**再把「纯权益 / 权益支付」归入 Preview 金额全 `null` 分支。仅 **客户预收**（`CLIENT_COLLECT`）走 null 金额专用脚本。

### Preview

| 条件 | 场景 | `payment.status` | `timeline` | `price/charges/deductions` | 价格汇总 C(1)(2)(3) |
|------|------|------------------|------------|----------------------------|---------------------|
| `payableAmount` 有值且 ≠ 0 | 现金 / 权益支付（有应付） | `null` | `null` | 按 SaaS 返回 | 执行 |
| `originalAmount = discountAmount` 且 `payableAmount = 0` | 权益抵扣 0 元（含权益支付足额） | `null` | `null` | 按 SaaS 返回 | 执行 |
| 否则 | 客户预收 | `NO_PAYMENT_REQUIRED` | `null` | 均为 `null` | 跳过 |

### Create

| 条件 | 场景 | `payment.status` | `timeline` |
|------|------|------------------|------------|
| `payableAmount` 有值且 ≠ 0 | 需支付 | `PENDING_PAYMENT` | 对象存在，内部字段全 `null` |
| `originalAmount = discountAmount` 且 `payableAmount = 0` | 权益抵扣 0 元 | `NO_PAYMENT_REQUIRED` | `{ paidAt: null, refundedAt: null }` |
| 否则 | 客户预收 | `NO_PAYMENT_REQUIRED` | `null` |

有明细时执行价格汇总 C(1)(2)(3)。

### Detail

| 条件 | 场景 | `payment.status` | `timeline` |
|------|------|------------------|------------|
| `originalAmount = discountAmount` 且 `payableAmount = 0` | 权益抵扣 0 元（含取消） | `NO_PAYMENT_REQUIRED` | `{ paidAt: null, refundedAt: null }` |
| `payableAmount = 0`（非上项） | 0 元 / 客户预收 | `NO_PAYMENT_REQUIRED` | `null` |
| 否则 | 需支付（默认待支付） | `PENDING_PAYMENT`（或见下） | 对象含 `paidAt`/`refundedAt`，值按支付状态显示否则 `null` |

**Detail 特殊支付态**：设环境变量 `expected_detail_status`（如 `REFUNDED`、`AUTHORIZED`）。`REFUNDED` 时 `timeline` 为 `null`；其他需支付态断言 `timeline` 含 `paidAt`/`refundedAt` 字段。

**参考日志**：后置会 `console.log` 订单级 `data.status`（如 `9`=待支付），**不断言**；只断言 `payment.status`。

---

## 价格汇总三条（C-1 / C-2 / C-3）

有 `price`、`charges`、`deductions` 且非 null 时执行（Preview：**现金 / 权益支付 / 权益抵扣 0 元** 分支）：

1. **C-1**：`sum(BASE_PRICE.details.amount) + sum(PREBOOKING_FEE.details.amount) = payment.price.originalAmount`
2. **C-2**：`abs(sum(ENTITLEMENT.details.amount)) = payment.price.discountAmount`  
   ※ 业务枚举 `ENTITLEMENT_DEDUCTION` 对应 `deductions[].strategy === "ENTITLEMENT"`
3. **C-3**：`originalAmount - discountAmount = payableAmount`  
   ※ `discountAmount` 与 `deductionAmount` 二选一（优先 `discountAmount`）

跳过价格汇总：设 `assert_payment_price=false`。

---

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `order_api_stage` | 否 | 前置按 URL 自动写入；仅 force 模式手填 |
| `order_api_stage_force` | 否 | `true` 时强制使用手填 `order_api_stage` |
| `expected_detail_status` | 否 | Detail 非默认态（`REFUNDED` 等） |
| `assert_payment_price` | 否 | 默认 `true`；设 `false` 跳过 C-1～C-3 |
| `assert_payment_env_price` | 否 | 默认 `true`；设 `false` 跳过按环境单价期望（E-BASE/E-FEE/E-ORIG/E-DISC/E-PAY） |
| `prebookingFeePayer` | 否* | `user` / `client` / `unset`；与 BOSS「预约服务费付费方」一致 |
| `prebookingUnitPrice` | 否* | 预约单价（用户承担时计入应付） |
| `overageUnitPrice` | 否* | 超人次单价；`BASE_PRICE = adults × overage` |
| `toUseEntitlementCount` | 否 | Preview/Create 从请求体写入；Detail 回读算折扣 |

\* 做「按环境单价算期望」时建议在 Apifox Environment 配置；缺 `overageUnitPrice` 或 `payer=unset` 时自动跳过 E-* 不断言失败。

**环境单价期望（E-\*）公式**（人数默认 3，或取请求 `passengers.length` / `fastTrackAdultCount`）：

- `BASE_PRICE = adults × overageUnitPrice`
- 用户承担：`PREBOOKING_FEE = adults × prebookingUnitPrice`；客户承担：面向用户 `PREBOOKING_FEE = 0`
- `discountAmount = min(toUseEntitlementCount, adults) × overageUnitPrice`
- `originalAmount = BASE_PRICE + PREBOOKING_FEE`；`payableAmount = originalAmount - discountAmount`
- **ePass 纯权益**（请求体无 `toUseUsageCount` / `toUseEntitlementCount`，且无 `DP_COLLECT`/`CLIENT_COLLECT`）：按 **`ent = adults`** 推断折扣（覆盖全部乘客底价；应付常为预约服务费）

---

## Apifox JS 约束（Agent 生成/修改时必遵）

| 禁止 | 改用 |
|------|------|
| `?.`、`??` | 逐层 `if` / `\|\|` |
| `` `模板字符串` `` | 字符串 `+` 拼接 |
| `catch (e) { /* 中文注释 */ }` 等特殊字符 | `catch (e) { body = {}; }` |
| 测试名中的 `✓`、`·`、全角标点 | ASCII：`[Preview-Cash]`、`expected=` |

报错 `Invalid or unexpected token` 或误指 `catch` 时，**优先检查是否粘贴了非 ASCII 或 ES2020 语法**。

---

## status 断言与日志

- 测试名格式：`[场景] payment.status expected=XXX actual=YYY`
- 通过时在控制台打印：
  - `[payment-assert] PASS <场景>`
  - `payment.status expected=...`
  - `payment.status actual=...`

---

## 扩展到 pytest / Postman 生成器

1. **pytest**：在 `*_helpers.py` 增加 `AssertPaymentPriceSummary`、`AssertPaymentStageStatus`，语义与本文件表格一致；可复用 `papi2548_helpers._RunAllureAssertionStep`。
2. **Postman 生成器**：在 `Build*JsHelpersLines()` 内联与本文件等价的 ES5 函数，或 `exec` 首行注释引用「与 `tools/payment-js/apifox_payment_assert_post.js` 同步」；改断言后 **运行生成脚本** 重写 JSON（见 [`postman-apifox-troubleshooting.md`](./postman-apifox-troubleshooting.md)）。
3. **新 module**（如 `fitness` 预预约）：若 URL 仍含 `/memberships/prebooking`，**无需改分支逻辑**；若 path 不同，仅扩展前置 `DetectOrderApiStageFromUrl` 中的正则。

---

## Agent 自检清单

```
- [ ] 已读 Confluence-1906049058 payment 阶段表与测试分析 R1-R7
- [ ] 前置/后置使用 tools/payment-js/apifox_payment_assert_*.js，无 ?. / ?? / 特殊 Unicode
- [ ] Preview 现金/权益支付 vs 客户预收 vs 权益抵扣0元 由 payableAmount + original/discount 分支，非 payment_product_type；权益支付与现金同预期
- [ ] Preview 权益抵扣0元 status=null（同现金/权益支付）；Create/Detail 权益抵扣0元 timeline={ paidAt:null, refundedAt:null }
- [ ] Detail 已退款/客户预收 timeline=null；需支付 timeline 含 paidAt/refundedAt
- [ ] 价格汇总 ENTITLEMENT 走 strategy=ENTITLEMENT
- [ ] lounge / fastTrack 仅 URL module 不同，断言逻辑相同
- [ ] 若同步 Postman 生成器，已运行 GeneratePostmanCollection*.py 并提醒重新导入
```
