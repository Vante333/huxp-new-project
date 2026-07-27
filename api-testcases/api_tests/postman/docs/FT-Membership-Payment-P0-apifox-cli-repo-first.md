# FT Membership Prebooking Payment P0 · CLI

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

| 项 | 值 |
|----|-----|
| 资产 key | `ft_membership_payment_p0` |
| 场景 ID | **366258** |
| 场景目录 | `membership/P0(冒烟用例)/prebooking`（folderId **350024**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475754** |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionFtMembershipPaymentP0.py` |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_membership_payment_p0
```

## 相对 P1 的冒烟裁剪

与 P1 同分组形态（一级支付方式 → 二级一条冒烟），链路含：Preview→Create→Detail→**发起支付**→Cancel→取消后详情/列表。

| P0 保留 | 对应 P1 | 发起支付 |
|---------|---------|----------|
| 权益支付 · 点数 3 | 权益足额 | REDIRECT |
| 现金 · 点数 0（`false+DP_COLLECT`） | 现金 0 点 | REDIRECT |
| 客户预收款 · 点数 0（**非显示**：只传 `cashPaymentApplied:true`、不传 cashier） | 默认预收费 0 点 | `500.000.802` |

**P0 不测（留 P1）**：权益点 1、现金点 1/3、显式 `CLIENT_COLLECT`、预收费点 1/3 报错、`true+DP_COLLECT` 冲突、async 三种分散、Detail/权益不足/支付链接全量。

定价 Environment 与 P1 共用（场景 1/2/3/5/7）；见  
[`FT-Membership-Payment-P1-apifox-cli-repo-first.md`](./FT-Membership-Payment-P1-apifox-cli-repo-first.md)。

## 跨品类

扩 Lounge 等冒烟时先读：  
[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md)。
