# Lounge Membership Prebooking Payment P0 · CLI

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

| 项 | 值 |
|----|-----|
| 资产 key | `lounge_membership_payment_p0` |
| 场景 ID | **366310** |
| 场景目录 | `membership/P0(冒烟用例)/prebooking`（folderId **350024**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475754** |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionLoungeMembershipPaymentP0.py` |
| 品类 | Lounge · path=`lounges` · `loungeResourceId` · module=`1` |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset lounge_membership_payment_p0
```

## 相对 P1 的冒烟裁剪（对齐 FT Membership P0）

与 `ft_membership_payment_p0` **同构**（一级支付方式 → 二级一条冒烟），链路含：Preview→Create→Detail→**发起支付**→Cancel→取消后详情/列表。

| P0 保留 | 对应 P1 | 发起支付 |
|---------|---------|----------|
| 权益支付 · 点数 3 | 权益足额 | REDIRECT |
| 现金 · 点数 0（`false+DP_COLLECT`） | 现金 0 点 | REDIRECT |
| 客户预收款 · 点数 0（**非显示**：只传 `cashPaymentApplied:true`、不传 cashier） | 默认预收费 0 点 | `500.000.802` |

**P0 不测（留 P1）**：权益点 1、现金点 1/3、显式 `CLIENT_COLLECT`、预收费点 1/3 报错、`true+DP_COLLECT` 冲突、async 三种分散、Detail/权益不足/支付链接全量。

## 相对 FT 的差异

- path / `loungeResourceId` / module=`1`（见品类扩展指南）
- **定价 Environment 键与 FT 解耦**（同环境换名并存）：

| Lounge 键 | 默认（场景 3） |
|-----------|----------------|
| `loungePaymentSceneId` | `3` |
| `loungePrebookingFeePayer` | `client` |
| `loungePrebookingUnitPrice` | `0` |
| `loungeOverageUnitPrice` | `17.00` |
| `loungeAssertPaymentEnvPrice` | `true` |

Environment 另须配置 **`loungeResourceId`**（集合默认 `N00012`）。BOSS 改价只改 `lounge*` 键，勿改 FT 的 `prebookingUnitPrice` 等。