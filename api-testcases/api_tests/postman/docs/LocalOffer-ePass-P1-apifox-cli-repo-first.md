# Local Offer ePass P1 Full · 全量 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

- **小白入门：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 已落地映射

| 项 | 值 |
|----|-----|
| 资产 key | `local_offer_epass_p1` |
| 场景 ID | **366257**（`Local Offer ePass P1 Full · CLI sync`） |
| 场景目录 | `epass/P1（全量用例）/prebooking`（folderId **350037**） |
| 环境 ID | **351893**（UAT/canary） |
| 数据集 ID | **3475756**（复用 PAPI-2424；列名：`ProgramID` / `clientId` / `secret`；ProgramID=`1919249349977088`） |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionLocalOfferEpassFull.py` → `LocalOffer-ePass-P1-full.postman_collection.json` |
| 覆盖 | E2E 三链路 + 分模块（约 132 HTTP 步） |

## 一键命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset local_offer_epass_p1
```

## 业务注意

1. **鉴权 / 数据集**：与 P0、PAPI-2424 共用 `3475756`。
2. **负向步**：可能 HTTP 4xx；以「断言结果」后置脚本为准；可关平台「校验响应 HTTP 200」。
3. **esim 负向造数**：集合预置 `esimResourceId`/`esimOptionId`（非 LO 默认网点）。
