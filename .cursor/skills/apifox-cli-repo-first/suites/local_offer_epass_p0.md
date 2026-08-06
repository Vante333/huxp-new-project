# local_offer_epass_p0 · CLI 落地笔记

- **场景**：366256 · `Local Offer ePass P0 · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`（2026-07-29 全量迁移自 epass/P0/prebooking）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475756（复用 papi_2424；ProgramID=`1919249349977088`）
- **详解**：[`LocalOffer-ePass-P0-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/LocalOffer-ePass-P0-apifox-cli-repo-first.md)
- **报告目录**：`apifox-reports/local_offer_epass_p0/`
- **生成器**：`generators/GeneratePostmanCollectionLocalOfferEpass.py`

## 可复用点

1. ePass 鉴权三列数据集与 2424 共用。
2. Auth 多作用域写 `accessToken` + 每步 `Lines_EnsureAuthPrerequest`。
3. 网点 `resourceId`/`optionId` 只从 Environment 取。
