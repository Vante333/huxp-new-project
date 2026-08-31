# ft_epass_payment_p0 · CLI 落地笔记

- **场景**：366262 · `FT E-pass Prebooking Payment P0 · CLI sync`
- **目录**：folderId **350033** · `epass/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475756（复用 papi_2424；ePass 凭据）
- **详解**：[`FT-Epass-Payment-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/apifox-cli/docs/FT-Epass-Payment-P0-apifox-cli-repo-first.md)
- **跨品类通识**：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/apifox-cli/docs/Prebooking-Payment-品类扩展指南.md)
- **报告目录**：`apifox-reports/ft_epass_payment_p0/`
- **生成器**：`generators/GeneratePostmanCollectionFtEpassPaymentP0.py` → 共享 `ft_prebooking_payment_common.py`

## 场景内分组（对齐 Membership P0）

- **权益支付** → 点数 3 冒烟（发起支付 REDIRECT）
- **现金** → 点数 0 冒烟（仅 `DP_COLLECT`、不传 `cashPaymentApplied` → REDIRECT）
- **客户预收款** → 点数 1 冒烟（显式 `CLIENT_COLLECT` → conflict msg；ePass 无预收款能力）
- **Bundle** → 纯权益冒烟（Create 后查详情/列表再取消）

Preview 全量 / Bundle 现金与预收款 / 支付链接 / 点数矩阵 → 仅 P1。

## 可复用点

1. 与 Membership P0 同构分组；现金入参语义不同（见详解「刻意差异」）。
2. 每条链路前刷新 ePass（`availableUsages` 预留足额）。
3. payment 断言与 Membership 共用脚本族。
4. E-pass 现金链路须带 `toUseUsageCount`（点数映射）；纯权益不传；客户预收款仅作 conflict 冒烟。

## 鉴权选行与请求头（2026-08）

- 场景「数据 1」勾选鉴权行（列名 **ProgramID / clientId / secret**）。前置从 `iterationData` 取 `ProgramID` 写入 **Environment**。
- 后续步骤 Headers 使用 `{{ProgramID}}`、`{{x-version}}`、`Bearer {{accessToken}}`、`{{$string.uuid}}`，**不要**在前置脚本 `headers.upsert`。
- **helpers 加载**：`00 Auth` 后置写入 `ftPayHelpersSource`；其它步骤前置/后置只 `eval` 该变量（约 10 行 loader）。单独跑业务步前须先跑 Auth。全局规范见 Skill [`reference.md`](../reference.md)「多步 helpers」。
- 复验：先跑 `00 Auth` 再跑业务 Group；控制台应有 `[ft-pay][auth-seed] ProgramID=… source=iterationData` 与 `[ft-pay][auth] ftPayHelpersSource 已写入`。

## 绑定真实接口再按 UI 解绑（2026-08）

- `suites.yaml` → `push_mode: http` + `unbind_after_push: true`。
- 金样 header：`name` + `value` + **`sampleValue`** + `enable`；path 相对 `/v2/...`。实现 `UiUnbindHeaderRows`。
- **禁止再试**：Postman `key`、path 带 `{{baseUrl}}`、只清 bind 留 `type=http`、口头「互斥」。
- AI 分支没有接口文档时按 METHOD+path **按需创建**，禁止 `apiDetailId=0`。
- 看 Headers：关掉整条场景标签再打开。步骤上不应再显示「已关联接口文档」，参数值列应有蓝色变量。
- 全局规范：Skill [`reference.md`](../reference.md)「场景 Headers 参数值为空」。
