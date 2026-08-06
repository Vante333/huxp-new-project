# membership_purchase_p0 · CLI 落地笔记

- **场景**：366587 · `Membership Purchase P0 · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`（2026-07-29 全量迁移）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）— 需可用 `baseUrl` 变量（新建空环境会导致 `{{baseUrl}}` 不解析）
- **详解**：[`Membership-Purchase-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/Membership-Purchase-P0-apifox-cli-repo-first.md)
- **报告**：`apifox-reports/membership_purchase_p0/`
- **生成器**：`generators/GeneratePostmanCollectionMembershipPurchaseP0.py`

## 场景内分组

- **商品B-无券-原价EUR** → Preview→Create→Details→Payments→Details→**Cancel→Details**
- **商品A-传券-订阅引导期USD** → 同上；应付 0 时 Payments 期望业务失败；其后仍 Cancel→Details；`deductionAmount=originalAmount-payableAmount`
- Preview/Create 断言 `charges[0].details[0]`：`paxType/quantity/unitPrice/amount`
- 已去掉独立「商品B-取链后取消」分组（Cancel 嵌进原 E2E）

## 场景 description（变量关系）

由 `BuildScenarioDescription()` 写入（Skill 硬约束 #11 / reference「场景 description」金样例）。含：生成源、链路、商品 A/B 变量与 `deductionAmount=original−payable`、运行时 orderId。换测改 Environment / `.env` 的 `MP_P0_*`。

## 坑

1. Push 会把 path 写成 `{{baseUrl}}+相对路径`，Environment 必须有可解析的 `baseUrl`（用 351893）。
2. 私有化 Environment CLI update 常写不进变量；鉴权用 `.env` 的 `MP_P0_*` 在生成时注入。
3. **2026-07-27**：token 有效且 search 可过鉴权，但 `purchase/preview` 仍 `201.000.001 invalid secret` → 接口侧权限/发布问题。
4. `product*ProgramId` 暂用 Retail ProgramID 占位，断言失败可能是预期。
