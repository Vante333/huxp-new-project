# FT Membership Prebooking Payment P1 · CLI

| 项 | 值 |
|----|-----|
| 资产 key | `ft_membership_payment_p1` |
| 场景 ID | **366261** |
| 场景目录 | `membership/P1（全量用例）/prebooking`（folderId **350028**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475754** |
| 工作分支 | **`ai/apifox-cli-sync`** |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_membership_payment_p1
```

## 覆盖

- 权益支付：点数 1（不传 async）/ 3（`async=false`）；Create 后发起支付→`REDIRECT`
- 现金 `DP_COLLECT`：权益点 0（`async=true`）/ 1 / 3 正向；Create 后发起支付→`REDIRECT`
- 客户预收费 `CLIENT_COLLECT`：权益点 0 / 1 正向（显式 cashier + **只传 `cashPaymentApplied:true` 不传 cashier 默认预收费**）；点数 3 Preview+Create 报错；Create 后发起支付→`500.000.802`
- 入参冲突：`true + DP_COLLECT` → Preview+Create 报错（`500.051.023`）
- **toUseEntitlementDetail**：一致通过；guest 不匹配 `500.042.020`；sum≠count `500.042.018`
- **权益不足 / 会籍无效**：`500.042.011`；伪造 membershipId
- **支付链接全量**：缺 orderId/paymentMethod/returnUrl → 固定缺参 msg；COF、REDIRECT+validUntil、幂等、802、803；801/804 占位（`cancelUrl` 非必填，不测缺参）
- async 三种变体分散在权益/现金用例，不单开分组
- 每条成功下单：发起支付 → Cancel → 订单详情 → 订单列表（status=**3** 或 **9**）

## 单一环境定价（换场景只改 Environment）

与 BOSS「单一价结算价格配置」对齐；**一套 Environment / 一套脚本**。

**只测 5 种**（超人次价格非 0）；**不测**场景 4（超人次未配置）、场景 6（超人次=0）：

| scene | 付费方 | 预约价 | 超人次 | 预期 | 含义摘要 |
|-------|--------|--------|--------|------|----------|
| 1 | 均未配置 (`unset`) | — | — | Preview 报错 | 未配用户/客户支付 |
| 2 | 客户 (`client`) | 非 0 | 非 0 | 正向 | 客户承担预约费；用户侧 FEE=0 |
| 3 | 客户 (`client`) | 0 | 非 0 | 正向 | 客户侧预约价为 0 |
| 5 | 用户 (`user`) | 0 | 非 0 | 正向 | 用户承担但预约价为 0 |
| 7 | 用户 (`user`) | 非 0 | 非 0 | 正向（现网默认语义） | 用户付预约费 + 有超人次价 |

| 环境变量 | 现网默认 | 含义 |
|----------|----------|------|
| `paymentSceneId` | `7` | **场景号标注**（对照上表）。接口不读此字段，仅便于报告/人工核对当前测的是哪一档 BOSS 价。 |
| `prebookingFeePayer` | `user` | **预约费谁付**：`user`=用户付（计入应付 FEE）；`client`=客户付（用户侧 FEE=0）；`unset`=未配置（常配合场景 1 期望报错）。 |
| `prebookingUnitPrice` | `8.99` | **预约费单价（每人）**。仅 `payer=user` 时：`FEE = adultCount × 本值`。 |
| `overageUnitPrice` | `23.67` | **超人次/人次底价单价（每人）**。`BASE = adultCount × 本值`；权益折扣 `DISC = min(权益点, adultCount) × 本值`。本自动化范围要求非 0。 |
| `paymentSceneExpectError` | `false` | **本场景是否期望业务报错**。场景 1 改为 `true`；正向场景保持 `false`。 |
| `assert_payment_env_price` | `true` | **是否按上列单价做金额期望断言**（E-BASE/E-FEE/E-ORIG/E-DISC/E-PAY）。`false` 则只做 payment 结构断言、不算期望金额。 |
| `toUseEntitlementCount` | （可空） | **本单拟用权益点数**。Membership 会写入请求体；ePass 纯权益常不传，断言按乘客数推断。 |

金额期望：`BASE=人数×超人次`；用户承担时 `FEE=人数×预约价`，客户承担时用户侧 FEE=0；`折扣=min(权益点,人数)×超人次`；`应付=BASE+FEE-折扣`。

换测：先改 BOSS，再改 Environment 同名键后重跑，无需改生成器。
**建议**：在 Apifox Environment 里给上述变量填「描述」列，与本表一致，避免只显示「默认」。

## 跨品类

向 Lounge / Fitness 等扩展时，先读通识：  
[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md)（以本 FT Membership/E-pass 为金样例）。
