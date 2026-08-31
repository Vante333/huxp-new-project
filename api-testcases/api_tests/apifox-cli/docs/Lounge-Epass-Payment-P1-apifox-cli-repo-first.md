# Lounge E-pass Prebooking Payment P1 · CLI

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

| 项 | 值 |
|----|-----|
| 资产 key | `lounge_epass_payment_p1` |
| 场景 ID | **366313** |
| 场景目录 | `epass/P1（全量用例）/prebooking`（folderId **350037**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475756** |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionLoungeEpassPaymentP1.py` |
| 品类 | Lounge · path=`lounges` · `loungeResourceId` · module=`1` |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset lounge_epass_payment_p1
```

## 覆盖（对齐 FT E-pass P1）

- 权益支付：点数 1（不传 async）/ 3（`async=false`）；Create 后发起支付→`REDIRECT`
- 现金 `DP_COLLECT`：仅 `cashier.DP_COLLECT` + `toUseUsageCount`（**不传** `cashPaymentApplied`）；权益点 0 / 1 / 3 正向；Create 后发起支付→`REDIRECT`
- 客户预收费 `CLIENT_COLLECT`：ePass **无此能力** · 仅保留点数 1 代表 → Preview/Create conflict msg（`500.051.023`/`500.042.023`）
- Bundle：纯权益成功；**现金 / 客户预收款入参均忽略不报错**；Create 后查详情+列表
- **Preview 全量**：module / ePassId / token / 次数不足 / 现金 usage+cashier / 出参（不抽样）
- **支付链接全量**：缺 orderId/paymentMethod/returnUrl → 固定缺参 msg；COF、REDIRECT+validUntil、幂等、803；**0 元 802** 用纯权益足额（**勿** `CLIENT_COLLECT`）；801/804 占位（`cancelUrl` 非必填，不测缺参）
- async 三种变体分散在权益/现金用例，不单开分组
- 每条成功下单：发起支付 → Cancel → 订单详情 → 订单列表（status=**3** 或 **9**）

定价键与 FT 解耦（`lounge*`）；默认 scene=3。通识见  
[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md) ·  
[`FT-Epass-Payment-P1-apifox-cli-repo-first.md`](./FT-Epass-Payment-P1-apifox-cli-repo-first.md)。
