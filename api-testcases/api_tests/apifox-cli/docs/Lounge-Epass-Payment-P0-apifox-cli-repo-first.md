# Lounge E-pass Prebooking Payment P0 · CLI

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

| 项 | 值 |
|----|-----|
| 资产 key | `lounge_epass_payment_p0` |
| 场景 ID | **366312** |
| 场景目录 | `epass/P0(冒烟用例)/prebooking`（folderId **350033**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475756** |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionLoungeEpassPaymentP0.py` |
| 品类 | Lounge · path=`lounges` · `loungeResourceId` · module=`1` |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset lounge_epass_payment_p0
```

## 相对 P1 的冒烟裁剪（对齐 FT E-pass P0）

与 `ft_epass_payment_p0` **同构**；与 Lounge Membership P0 同分组形态。

| P0 保留 | 对应 P1 | 发起支付 |
|---------|---------|----------|
| 权益支付 · 点数 3 | 权益足额 | REDIRECT |
| 现金 · 点数 0（仅 `DP_COLLECT`，不传 `cashPaymentApplied`） | 现金 0 点 | REDIRECT |
| 客户预收款 · 点数 1（显式 `CLIENT_COLLECT`） | 无预收款能力（点 1 代表） | Preview/Create conflict msg |

**刻意差异（相对 Membership）**

- E-pass **不支持客户预收款**：`CLIENT_COLLECT` 一律 conflict（`500.051.023`/`500.042.023`），勿当正向 0 元造单
- E-pass 现金**不传** `cashPaymentApplied`；靠 `cashier.DP_COLLECT` + `toUseUsageCount`
- Membership 0 元 802 靠**非显示**客户预收款

**P0 不测（留 P1）**：点数矩阵、async 分散、Bundle、Preview 全量、支付链接全量。

## 定价解耦（Environment 换名）

与 FT 同环境并存：`loungePaymentSceneId` / `loungePrebookingFeePayer` / `loungePrebookingUnitPrice` / `loungeOverageUnitPrice` / `loungeAssertPaymentEnvPrice`（默认 scene=3 · client / 0 / 17.00）。另配 **`loungeResourceId`**。通识见  
[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md)。
