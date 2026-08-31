# local_offer_epass_p1 · CLI 落地笔记

- **场景**：366257 · `Local Offer ePass P1 Full · CLI sync`
- **目录**：folderId **350037** · `epass/P1（全量用例）/prebooking`（2026-08-23 从 common/P1/others 迁回）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475756（复用 papi_2424；ProgramID=`1919249349977088`）
- **详解**：[`LocalOffer-ePass-P1-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/apifox-cli/docs/LocalOffer-ePass-P1-apifox-cli-repo-first.md)
- **报告目录**：`apifox-reports/local_offer_epass_p1/`
- **生成器**：`generators/GeneratePostmanCollectionLocalOfferEpassFull.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`

## 可复用点

1. Full 生成器复用 P0/P1 E2E 的 `RequestItem` / EnsureAuth。
2. 负向步以脚本断言为准（平台 HTTP 200 校验可关）。
3. SyncCheck 耗时较长（100+ 步）。
