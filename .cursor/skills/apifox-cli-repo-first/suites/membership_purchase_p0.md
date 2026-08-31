# membership_purchase_p0 · CLI 落地笔记

- **场景**：366587 · `Membership Purchase P0 · CLI sync`
- **目录**：folderId **350042** · `common/P0(冒烟用例)/prebooking`（2026-08-23 按用户指定挪目录）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）— 仅 `baseUrl` / `x-version`
- **详解**：[`Membership-Purchase-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/apifox-cli/docs/Membership-Purchase-P0-apifox-cli-repo-first.md)
- **报告**：`apifox-reports/membership_purchase_p0/`
- **生成器**：`generators/GeneratePostmanCollectionMembershipPurchaseP0.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **数据集**：[`datasets/membership_purchase_p0/`](../../../../api-testcases/api_tests/apifox-cli/datasets/membership_purchase_p0/)

## 场景内分组（从 P1 正向抽取）

每条：`Preview→Create→purchase/details→memberships/details(MS-DET)→Payments→Details→Cancel→Details`

1. **不传券选择默认项目配置中的首个商品并按首月原价预览(EUR)** · `pos_b_no_coupon`
2. **【币种·已配置】商品A…开启引导期…activationMethod=1** · `pos_a_intro_currency_configured`
3. **【币种·已配置】商品A…未开启引导期…activationMethod=2** · `pos_a_no_intro_currency_configured`

不抽：币种·未配置、商品 A 主场景（无币种前缀）、再次取链、负向/字段校验（仍在 P1）。

## 变量供给

- **A · 数据集选行**：导入 `apifox-dataset-business-ascii.csv`（或 UTF-8 中文版），勾选 `_FULL_SUITE` / `pos_*` 行。
- 鉴权：`MP_P0_*` 或独立鉴权数据集；**勿**把 ProgramID/clientId/secret 写进业务 CSV。
- Environment 351893 勿堆业务键（券码/金额），避免盖掉数据集。

## 场景 description（变量关系）

由 `BuildScenarioDescription()` 写入。含三条链路、币种/activationMethod、`deduction=original−payable`、MS-DET 隔离说明。

## 坑

1. Push 会把 path 写成 `{{baseUrl}}+相对路径`，Environment 必须有可解析的 `baseUrl`（用 351893）。
2. 鉴权选行须先跑 Auth；种子优先级含 Environment，避免后续步骤 X-Program-ID 回落 `.env` 第一套。
3. 业务 body 禁止注入 `clientId`/`secret`（仅 Auth body 覆盖）。
4. `product*ProgramId` 暂用 Retail ProgramID 占位，断言失败可能是预期。
