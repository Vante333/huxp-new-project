# local_offers_options · CLI 落地笔记

- **场景**：365976 · `Local Offers options · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）
- **数据集**：3475754（与 papi_2548 共用会籍鉴权三列）
- **详解**：[`LocalOffers-Options-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/apifox-cli/docs/LocalOffers-Options-apifox-cli-repo-first.md)
- **报告目录**：`apifox-reports/local_offers_options/`
- **生成器**：`generators/GeneratePostmanCollectionLocalOffersOptions.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **pytest**：已删 features/smoke/contract 三文件（2026-08-12）

## 下次自动处置（本资产 + 同类只读 GET）

| 症状 | 自动处置 |
|------|----------|
| URL 出现 `%7B%7B…%7D%7D` / `500.020.016` | path 改用 Environment 已有名：`resourceId`/`optionId`（勿自造 `localOfferResourceId`）；集合不预置；前置 env 优先 + 改写 path |
| 用户说「不要固化、取环境变量」 | path 保持 `{{resourceId}}`/`{{optionId}}`；**禁止**写死 GR0006115；默认值只放 Environment |
| 用户说「业务失败不可跳过」 | 删掉正向 `code=-1` 的 `assertInfo` 软跳过；硬断言 `code=0` |
| 分页不回显 / 非法 query 却成功 | 查 Convert query 是否透传 + Push 是否把 query 拼进 path；修工具链后 SyncCheck |
| 非法 pageSize/language | `loAssertInvalidFieldRejected(label, field, errCode)`：固定 msg 模板 + `301.020.001`/`300.020.001` |
| CLI 绿、UI 红 | 先确认 UI 在 `ai/apifox-cli-sync`（本场景 main 常无 steps）+ 环境 351893 + 硬刷新 |
| 后置脚本 `Cannot read properties of undefined (reading 'length')`（断言面板前几条绿） | `fmtJsonBrief`：`JSON.stringify(undefined)` 非字符串；对齐 MembershipPurchaseP0 兜底；`validity`/`pagination` 排除 `null`；改生成器后 PushSteps |
| `validity.type` 实际=undefined / 部分 SKU `validity:{}` | BOSS 未配有效期；`loAssertValidity` 对空 type 软通过（`assertInfo`），有 type 仍硬断言 1\|2\|3；改生成器后 PushSteps |

一键：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset local_offers_options`

## 可复用点

1. 只读 GET：`/v2/resources/localOffers/{resourceId}/options`（+ P03 详情 `…/options/{optionId}`）。
2. 鉴权三列数据集；业务 ID 只在 Environment。
3. Convert：透传 `url.query`、保留空 path 段；Push：query 拼进 `customHttp.path`。
4. Triage 成功清空陈旧 `leftover-failures.md`。
5. 全局症状表见 Skill [`reference.md`](../reference.md)「症状 → 自动处置」。
