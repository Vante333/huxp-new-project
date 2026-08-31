# FT E-pass Prebooking Payment P1 · CLI

| 项 | 值 |
|----|-----|
| 资产 key | `ft_epass_payment_p1` |
| 场景 ID | **366263** |
| 场景目录 | `epass/P1（全量用例）/prebooking`（folderId **350037**） |
| 环境 ID | **351893** |
| 数据集 ID | **3475756** |
| 工作分支 | **`ai/apifox-cli-sync`** |

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_epass_payment_p1
```

## 覆盖（对齐 membership P1 + Bundle/附件1）

- 权益支付：点数 1（不传 async）/ 3（`async=false`）；Create 后发起支付→`REDIRECT`
- 现金 `DP_COLLECT`：`cashPaymentApplied=true`；权益点 0（`async=true`）/ 1 / 3 正向；Create 后发起支付→`REDIRECT`
- 客户预收费 `CLIENT_COLLECT`：ePass **无此能力** · 仅保留点数 1 代表 → Preview/Create conflict msg（`500.051.023`/`500.042.023`）
- Bundle：纯权益成功；**现金 / 客户预收款入参均忽略不报错**；Create 后查详情+列表
- **Preview 全量**：module / ePassId / token / 次数不足 / 现金 usage+cashier / 出参（不抽样）
- **支付链接全量**：缺 orderId/paymentMethod/returnUrl → 固定缺参 msg；COF、REDIRECT+validUntil、幂等、803；**0 元 802** 用纯权益足额（**勿** `CLIENT_COLLECT`）；801/804 占位（`cancelUrl` 非必填，不测缺参）
- async 三种变体分散在权益/现金用例，不单开分组
- 每条成功下单：发起支付 → Cancel → 订单详情 → 订单列表（status=**3** 或 **9**）

## 单一环境定价变量（与 Membership 共用 Environment）

场景号 `(1,2,3,5,7)` 与变量含义见  
[`FT-Membership-Payment-P1-apifox-cli-repo-first.md`](./FT-Membership-Payment-P1-apifox-cli-repo-first.md)「单一环境定价」一节。  
Apifox 场景 description 在 PushSteps 后会写入完整中文说明；Environment 建议同步填「描述」列。

重新生成：

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionFtEpassPaymentP1.py
```

## 跨品类

向其它品类扩展时，先读通识：  
[`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md)。
