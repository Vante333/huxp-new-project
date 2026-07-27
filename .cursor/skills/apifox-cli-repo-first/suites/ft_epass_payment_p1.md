# ft_epass_payment_p1 · CLI 落地笔记



- **场景**：366263 · `FT E-pass Prebooking Payment P1 · CLI sync`

- **目录**：folderId **350037** · `epass/P1（全量用例）/prebooking`

- **分支**：`ai/apifox-cli-sync`

- **环境**：351893 · UAT（canary）

- **数据集**：3475756

- **详解**：[`FT-Epass-Payment-P1-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/FT-Epass-Payment-P1-apifox-cli-repo-first.md)

- **跨品类通识**（Lounge 等抄作业）：[`Prebooking-Payment-品类扩展指南.md`](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)

- **报告目录**：`apifox-reports/ft_epass_payment_p1/`

- **生成器**：`generators/GeneratePostmanCollectionFtEpassPaymentP1.py` + `ft_prebooking_payment_p1_gaps.py`



## 场景内分组（对齐 membership P1）



一级 → 二级（`type=group`，UI 可折叠）：



- **权益支付** → 点数 3（不传 async / `async=false`）；Create 后发起支付期望 REDIRECT

- **现金** → 点数 0（`async=true`）/ 1 / 3；**仅** `cashier.DP_COLLECT` + `toUseUsageCount`（**不传** `cashPaymentApplied`）；可用性/预约 **adultCount=3**

- **客户预收款** → ePass **无此能力**：`CLIENT_COLLECT` 一律期望 conflict msg（`500.051.023`/`500.042.023`）

- **Bundle** → 纯权益成功（Create 后取消 usage，status=9 断言取消失败文案）；现金入参忽略不报错；预收款报错（不传 `cashPaymentApplied`，钉 conflict msg）

- **Preview全量校验** → module / ePassId / token / 次数不足 / 现金 usage+cashier / 出参（不抽样）

- **支付链接入参与错误码** → 缺 orderId/paymentMethod/returnUrl → 固定缺参 msg；COF、REDIRECT+validUntil、幂等、802、803；801/804 占位（不测缺 cancelUrl）



## 可复用点



1. 每条支付链路前刷新 ePass（`availableUsages≥5`）。

2. ePass 现金：不传 `cashPaymentApplied`；仅 `cashier.DP_COLLECT` + `toUseUsageCount`。

3. ePass **无客户预收款**：`CLIENT_COLLECT` → msg=`The specified collection method conflicts with the cash payment parameter. Please verify the request parameters.`

4. Bundle：现金忽略不报错；预收款 conflict；成功单取消用 `ftPayAssertCancelUsageResponse`。

5. Preview / 支付链接缺口：`generators/ft_prebooking_payment_p1_gaps.py`。

6. 缺/空必填：**只断言固定 msg**（+ `code=-1`），不验 errCode

7. `epassModule`：集合变量，存品类 module 枚举（FT=2）；断言 `data.module` 与之相等。

8. Create/Bundle `status`：允许 **1/5/9**（9=待支付）；取消失败文案见上。

9. Preview「token 由 membership 可用性」：注册 membership（复用 clientUserId）→ 会籍可用性 → ePass Preview。

10. **P1 包体过大 → Push `422001`**：勿内联整包 FastTrack helpers；用精简 `ft*` + `CompactJsLines`。

11. **次数不足 errCode 族**：Preview/Create 接受 `500.042.005` / `500.051.005` / `500.051.010` / `500.051.020`（沙箱 Preview 常 051.020、Create 常 051.005）。

12. **双缺 `toUseUsageCount`+`paymentMode`**：合法纯权益，断言 `code=0`（勿当缺参负向）。

13. **纯权益 E-DISC/E-PAY**：无 toUse* 且无 DP/CLIENT_COLLECT 时按 `ent=adults` 推断（折扣=底价合计，应付≈预约费）。

## Agent 下次自动处置（本资产）

用户报本场景 / ePass Preview·Bundle·缺参类失败时：

1. 先读 [品类扩展指南 §9.1 #10–#15](../../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md) 与 [问题回顾 §12](../../../../api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-问题回顾.md)。  
2. 改 `ft_prebooking_payment_common.py` / `ft_prebooking_payment_p1_gaps.py`（勿只改 Apifox UI）。  
3. `PushSteps -Asset ft_epass_payment_p1`；若动缺参助手则同步 `ft_membership_payment_p1`、`lounge_epass_payment_p1`、`lounge_membership_payment_p1`。  
4. 提醒：`ai/apifox-cli-sync` + 硬刷新。


