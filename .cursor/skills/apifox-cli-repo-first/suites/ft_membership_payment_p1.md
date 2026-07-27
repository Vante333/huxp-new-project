# ft_membership_payment_p1 · CLI 落地笔记

- **场景**：366261 · `FT Membership Prebooking Payment P1 · CLI sync`
- **目录**：folderId **350028** · `membership/P1（全量用例）/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475754
- **详解**：[`FT-Membership-Payment-P1-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/FT-Membership-Payment-P1-apifox-cli-repo-first.md)
- **跨品类通识**（Lounge 等抄作业）：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)
- **报告目录**：`apifox-reports/ft_membership_payment_p1/`
- **生成器**：`generators/GeneratePostmanCollectionFtMembershipPaymentP1.py`

## 场景内分组（对齐手工 Apifox）

一级 → 二级（`type=group`，UI 可折叠）：

- **权益支付** → 足额 3 点（不传 async / `async=false`）；Create 后发起支付期望 REDIRECT（用户预约费）
- **现金** → 点数 0（`async=true`）/ 1 / 3；Create 后发起支付期望 REDIRECT；另含 `true+DP_COLLECT` 负向
- **客户预收款** → 点数 0 / 1（显式 CLIENT_COLLECT + 只传 `cashPaymentApplied:true` 不传 cashier）/ 3（报错）；Create 后发起支付 802
- **toUseEntitlementDetail校验** → CH/G 与 count 一致/不一致（`500.042.018` / `500.042.020`）
- **权益不足与会籍无效** → 减点造数后 `042.011`/`051.011`/`051.020`（硬失败 `051.004`）；伪造 membershipId
- **支付链接入参与错误码** → 缺 orderId/paymentMethod/returnUrl → `302.000.001`；COF、REDIRECT+validUntil、幂等、802、803；801/804 占位（不测缺 cancelUrl）

不再单开「发起支付」「国内 async」分组：支付跟在每条成功下单链路后；async 三种变体分散在权益/现金用例。

## 可复用点

1. 每条支付链路前刷新 membership，避免权益耗尽；**无 01 Setup**（Auth 后链路内自包含造数）。
2. 会员现金：`cashPaymentApplied=false` + `DP_COLLECT`（`true+DP_COLLECT` → `500.051.023` + conflict msg）。
3. **可用性/预约统一 adultCount=3**；现金/预收款点数 **0 / 1 / 3** 只改 `toUseEntitlement*` 入参区分。
4. 客户预收费：点数 **0/1** 正向，点数 **3** Preview+Create 均报错（`500.051.016`）。
5. **发起支付**：`权益/现金→REDIRECT`；`客户预收费 payableAmount=0 或无该字段→必须 500.000.802`（禁止软跳过）。
6. **入参冲突**：`cashPaymentApplied=true` + `DP_COLLECT` → Preview+Create（`500.051.023` + 固定 msg）。
7. 国内 async：缺失（权益足额）/ `false`（权益足额、现金1/3）/ `true`（现金0）分散覆盖，不单开分组。
8. Preview/Create/Detail 额外一致性：`usedEntitlementDetails[key] === sum(breakdown[].entitlements[key])`；有入参时 `cashPaymentApplied`/`cashier` 与请求一致。
9. 取消：待支付 status=9 不可取消时 msg=`Order cancellation failed. Please try again later.`；取消后详情/列表 **status=3 或 9**。
10. 可用性后 **多作用域** 写入 `prebookingToken`（variables/collection/env/globals），Preview 前置强制注入，避免旧/空 token。
11. **单一环境定价**：只改 Apifox Environment（与 BOSS「单一价结算」一致），不换 Program。
    - **只测 5 种**：场景 **1 / 2 / 3 / 5 / 7**（超人次非 0）；**不测** 4（超人次未配置）、6（超人次=0）
    - 现网默认：**用户** · 预约价 **8.99** · 超人次 **23.67**（场景 7 语义，正向）
    - 键：`paymentSceneId` / `prebookingFeePayer`(`user|client|unset`) / `prebookingUnitPrice` / `overageUnitPrice` / `paymentSceneExpectError`
    - 金额断言：`apifox_payment_assert_post.js` 按环境单价算 E-BASE/E-FEE/E-ORIG/E-DISC/E-PAY（可设 `assert_payment_env_price=false` 关闭）
    - 场景 1：BOSS 均未配置后设 `paymentSceneExpectError=true`（负向止 Preview）
    - 文档样例价见生成器 `DOC_SCENE_TABLE` / `AUTOMATED_SCENE_IDS`；**运行以 Environment 为准**
12. 缺口场景实现见 `generators/ft_prebooking_payment_p1_gaps.py`。

## 排障（下次优先）

完整症状表与约束见通识文档，勿在本文件重复维护细则：

→ [`Prebooking-Payment-品类扩展指南.md` §9](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)  
→ [`Apifox-CLI-Repo-First-问题回顾.md` §11](../../../../api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-问题回顾.md)  
→ Skill [`reference.md`「症状 → 自动处置」](../reference.md)（含预预约行）

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_membership_payment_p1
```
