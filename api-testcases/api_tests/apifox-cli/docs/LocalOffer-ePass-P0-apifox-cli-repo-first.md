# Local Offer ePass P0 · 冒烟 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

- **小白入门：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 已落地映射

| 项 | 值 |
|----|-----|
| 资产 key | `local_offer_epass_p0` |
| 场景 ID | **366256**（`Local Offer ePass P0 · CLI sync`） |
| 场景目录 | `epass/P0(冒烟用例)/prebooking`（folderId **350033**） |
| 环境 ID | **351893**（UAT/canary） |
| 数据集 ID | **3475756**（复用 PAPI-2424；列名：`ProgramID` / `clientId` / `secret`；ProgramID=`1919249349977088`） |
| 工作分支 | **`ai/apifox-cli-sync`** |
| 生成器 | `generators/GeneratePostmanCollectionLocalOfferEpass.py` → `LocalOffer-ePass-P0-e2e-core.postman_collection.json` |
| 覆盖 | Auth + E01 创建 + E02 预约 + E03 Bundle（37 HTTP 步） |

## 一键命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset local_offer_epass_p0
```

## 业务注意

1. **鉴权**：数据集三列填 **ePass** 凭据（与 PAPI-2424 相同数据集）。
2. **网点**：`resourceId` / `optionId` 从 Environment 注入（集合不预置）。
3. **改断言**：只改生成器，再 SyncCheck；UI 切 `ai/apifox-cli-sync` 硬刷新。
