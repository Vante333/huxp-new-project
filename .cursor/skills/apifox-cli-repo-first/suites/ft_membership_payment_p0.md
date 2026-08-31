# ft_membership_payment_p0 · CLI 落地笔记

- **场景**：366258 · `FT Membership Prebooking Payment P0 · CLI sync`
- **目录**：folderId **350024** · `membership/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475754（复用 papi_2548；ProgramID/clientId/secret）
- **详解**：[`FT-Membership-Payment-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/apifox-cli/docs/FT-Membership-Payment-P0-apifox-cli-repo-first.md)
- **跨品类通识**：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/apifox-cli/docs/Prebooking-Payment-品类扩展指南.md)
- **报告目录**：`apifox-reports/ft_membership_payment_p0/`
- **生成器**：`generators/GeneratePostmanCollectionFtMembershipPaymentP0.py` → 共享 `ft_prebooking_payment_common.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`。金样 header：`name`+`value`+**`sampleValue`**，相对 path。**禁止** Postman `key`、path 带 `{{baseUrl}}`、只清 bind 留 `type=http`。
- **Helpers**：Auth 写入 `ftPayHelpersSource`；其它步 eval loader；payment 断言只挂 Preview/Create/Detail
- **Headers 验收**：关掉整条场景标签再打开；应无「已关联接口文档」，参数值列有蓝色 `{{变量}}`。

## 场景内分组（相对 P1 冒烟裁剪）

- **权益支付** → 点数 3 冒烟（发起支付 REDIRECT）
- **现金** → 点数 0 冒烟（`false+DP_COLLECT` → REDIRECT）
- **客户预收款** → 点数 0 冒烟（**非显示**：只传 `cashPaymentApplied:true`、不传 cashier → 发起支付 802）

点数矩阵 / async 分散 / 显式 CLIENT_COLLECT / 入参冲突 / 预收费点 3 报错 / Detail·不足·支付链接 → 仅 P1。

## 可复用点

1. payment 断言内联 `tools/payment-js/apifox_payment_assert_*.js` + `apifox_extra_consistency_assert_post.js`。
2. Auth 多作用域写 `accessToken` + `Lines_EnsureAuthPrerequest`。
3. 网点 `fastTrackResourceId` 优先 Environment。
4. 与 P1 同链路横切：发起支付、取消后详情/列表。
5. P0 与 E-pass P0 **同构**（账户轴差异见品类扩展指南）。
