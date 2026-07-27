# Local Offers options · 全量 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

- **小白入门：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 已落地映射

| 项 | 值 |
|----|-----|
| 资产 key | `local_offers_options` |
| 场景 ID | **365976**（`Local Offers options · CLI sync`） |
| 场景目录 | `common/P1（全量用例）/others`（folderId **350048**） |
| 环境 ID | **351893**（与 PAPI-2548 共用 UAT/canary） |
| 数据集 ID | **3475754**（与 2548 共用；列名：`ProgramID` / `clientId` / `secret`） |
| 工作分支 | **`ai/apifox-cli-sync`**（唯一复用，勿新建 ai/*） |
| 生成器 | `generators/GeneratePostmanCollectionLocalOffersOptions.py` |
| pytest | `tests/features/test_local_offers_options.py`、`tests/smoke/test_local_offers_options_smoke.py` |
| 用例表 | `testcases/2026Q2_SP2/LocalOffersOptions-接口测试用例-001.md` |

## 一键命令

```powershell
# 生成 → 推 AI 分支 → 跑 UAT → triage → 成功则 upsert catalog
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset local_offers_options
```

分步：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action Generate -Asset local_offers_options
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset local_offers_options
.\scripts\ApifoxRepoFirst.ps1 -Action Run -Asset local_offers_options
```

## 日常改断言

1. 只改生成器 / `local_offers_options_service`（请求名用 `PurposeName`）
2. `SyncCheck -Asset local_offers_options`
3. Apifox UI 切到 `ai/apifox-cli-sync` 硬刷新

## 业务注意

1. **鉴权**：数据集三列 `ProgramID` / `clientId` / `secret` 对应 `DP_PROGRAM_ID` / `DP_CLIENT_ID` / `DP_CLIENT_SECRET`（与会籍套件相同，非 ePass 那套）。
2. **正向资源**：path 用 **`{{resourceId}}` / `{{optionId}}`**，值只从 Environment 取；集合不预置。前置脚本注入并改写未解析占位符。P03 为 option 详情。**业务失败（code!=0）硬失败，不可跳过。**
3. **负向 HTTP 4xx**：以「断言结果」后置脚本为准；可按项目设置关闭平台「校验响应 HTTP 200」。
4. **duration 缺口**：N05c/N05d 对齐 pytest xfail——服务端未拒绝时软通过。
5. **不含**纯本地 OpenAPI 契约用例（`test_local_offers_options_contract.py`，不访问网关）。

## 映射文件

- `.apifox/settings.json` → `projectId: 346275`
- `.apifox/suites.yaml` → `assets.local_offers_options`
