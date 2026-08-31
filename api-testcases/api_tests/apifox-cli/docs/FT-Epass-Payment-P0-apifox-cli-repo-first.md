# FT E-pass Prebooking Payment P0 · CLI

| 项 | 值 |
|----|-----|
| 资产 key | `ft_epass_payment_p0` |
| 场景 ID | **366262** |
| 场景目录 | `epass/P0(冒烟用例)/prebooking`（folderId **350033**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475756**（ePass 凭据） |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionFtEpassPaymentP0.py` |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_epass_payment_p0
```

## 相对 P1 的冒烟裁剪（对齐 Membership P0）

与 Membership P0 **同构**：一级支付方式 → 二级一条冒烟；链路含发起支付与取消后详情/列表。

| P0 保留 | 对应 P1 | 发起支付 |
|---------|---------|----------|
| 权益支付 · 点数 3 | 权益足额 | REDIRECT |
| 现金 · 点数 0（仅 `DP_COLLECT`，不传 `cashPaymentApplied`） | 现金 0 点 | REDIRECT |
| 客户预收款 · 点数 1（显式 `CLIENT_COLLECT`） | 无预收款能力（点 1 代表） | Preview/Create conflict msg |
| Bundle · 纯权益 | P1 Bundle纯权益支付-成功 | Create 后详情/列表再取消 |

**刻意差异（相对 Membership）**

- E-pass **不支持客户预收款**：`CLIENT_COLLECT` 一律 conflict（`500.051.023`/`500.042.023`），勿当正向 0 元造单
- E-pass 现金**不传** `cashPaymentApplied`；靠 `cashier.DP_COLLECT` + `toUseUsageCount`；顶层带 `clientUserId`
- Membership 现金为 `cashPaymentApplied=false` + `DP_COLLECT` + `toUseEntitlement*`；0 元 802 靠客户预收款

**鉴权 / 请求头**

- 场景「数据 1」勾选鉴权行（列名 `ProgramID` / `clientId` / `secret`）。前置把 `ProgramID` 写入 Environment。
- Headers：`X-Program-ID={{ProgramID}}`、`x-version={{x-version}}`、`X-Request-ID={{$string.uuid}}`、`Authorization=Bearer {{accessToken}}`。禁止前置脚本 upsert 头。

**P0 不测（留 P1）**：点数矩阵、async 分散、Bundle 现金/预收款、Preview 全量、支付链接全量、次数不足等缺口。

定价变量与 Membership 共用 Environment，见  
[`FT-Membership-Payment-P1-apifox-cli-repo-first.md`](./FT-Membership-Payment-P1-apifox-cli-repo-first.md)。

## 跨品类

[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md)。
