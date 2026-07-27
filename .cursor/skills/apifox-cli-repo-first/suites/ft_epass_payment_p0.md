# ft_epass_payment_p0 · CLI 落地笔记

- **场景**：366262 · `FT E-pass Prebooking Payment P0 · CLI sync`
- **目录**：folderId **350033** · `epass/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475756（复用 papi_2424；ePass 凭据）
- **详解**：[`FT-Epass-Payment-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/FT-Epass-Payment-P0-apifox-cli-repo-first.md)
- **跨品类通识**：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)
- **报告目录**：`apifox-reports/ft_epass_payment_p0/`
- **生成器**：`generators/GeneratePostmanCollectionFtEpassPaymentP0.py` → 共享 `ft_prebooking_payment_common.py`

## 场景内分组（对齐 Membership P0）

- **权益支付** → 点数 3 冒烟（发起支付 REDIRECT）
- **现金** → 点数 0 冒烟（仅 `DP_COLLECT`、不传 `cashPaymentApplied` → REDIRECT）
- **客户预收款** → 点数 1 冒烟（显式 `CLIENT_COLLECT` → conflict msg；ePass 无预收款能力）

Bundle / Preview 全量 / 支付链接 / 点数矩阵 → 仅 P1。

## 可复用点

1. 与 Membership P0 同构分组；现金入参语义不同（见详解「刻意差异」）。
2. 每条链路前刷新 ePass（`availableUsages` 预留足额）。
3. payment 断言与 Membership 共用脚本族。
4. E-pass 现金链路须带 `toUseUsageCount`（点数映射）；纯权益不传；客户预收款仅作 conflict 冒烟。
