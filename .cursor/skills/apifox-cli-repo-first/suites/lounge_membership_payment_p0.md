# lounge_membership_payment_p0 · CLI 落地笔记

- **场景**：366310 · `Lounge Membership Prebooking Payment P0 · CLI sync`
- **目录**：folderId **350024** · `membership/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475754（ProgramID/clientId/secret）
- **详解**：[`Lounge-Membership-Payment-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/Lounge-Membership-Payment-P0-apifox-cli-repo-first.md)
- **跨品类通识**：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)
- **报告目录**：`apifox-reports/lounge_membership_payment_p0/`
- **生成器**：`GeneratePostmanCollectionLoungeMembershipPaymentP0.py` → `ft_prebooking_payment_common.py`（`category=lounge`）

## 场景内分组（对齐 FT Membership P0）

- **权益支付** → 点数 3 冒烟（发起支付 REDIRECT）
- **现金** → 点数 0 冒烟（`false+DP_COLLECT` → REDIRECT）
- **客户预收款** → 点数 0 冒烟（**非显示**：只传 `cashPaymentApplied:true`、不传 cashier → 发起支付 802）

点数矩阵 / async 分散 / 显式 CLIENT_COLLECT / 入参冲突 / 预收费点 3 报错 / Detail·不足·支付链接 → 仅 P1。

## 品类参数

| 项 | 值 |
|----|-----|
| path | `/v2/orders/lounges/...` |
| 资源变量 | `loungeResourceId`（默认 N00012） |
| module | `1` |
| 权益不足池 | `moduleExclusiveEntitlements` 中 `module=1` |
| 定价 Environment | `loungePaymentSceneId` 等（与 FT 换名解耦；默认 scene=3） |
