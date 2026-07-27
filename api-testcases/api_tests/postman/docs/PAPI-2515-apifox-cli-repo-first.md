# PAPI-2515 · 全量 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

- **小白入门：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 已落地映射

| 项 | 值 |
|----|-----|
| 资产 key | `papi_2515` |
| 场景 ID | **365972**（`PAPI-2515 crossModule · CLI sync`） |
| 场景目录 | `MEMBERSHIP` → `PAPI-2515 crossModule entitlements`（folderId **350020**） |
| 环境 ID | **351893**（与 PAPI-2548 共用 UAT/canary） |
| 数据集 ID | **3475755**（`use_data_set_id`；列名：`ProgramID` / `clientId` / `secret`） |
| 工作分支 | **`ai/apifox-cli-sync`**（唯一复用，勿新建 ai/*） |
| 生成器 | `generators/GeneratePostmanCollectionPapi2515.py` |
| 编排 | `RunP2515MainE2EScenario` |

## 一键命令

```powershell
# 生成 → 推 AI 分支 → 跑 UAT → triage → 成功则 upsert catalog
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2515
```

分步：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action Generate -Asset papi_2515
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset papi_2515
.\scripts\ApifoxRepoFirst.ps1 -Action Run -Asset papi_2515
```

## 日常改断言

1. 只改生成器 / `papi2515_helpers` / services（请求名用 `PurposeName`）
2. `SyncCheck -Asset papi_2515`
3. Apifox UI 切到 `ai/apifox-cli-sync` 硬刷新

## 业务注意（相对 2548）

1. **鉴权凭据来自数据集**（非 environment get 可见变量）：场景 `options.useDataSetId=3475755`；PushSteps 会从 `suites.yaml` → `use_data_set_id` 写回 options。
2. **数据集鉴权三列（团队统一，勿改别名）**：`ProgramID`、`clientId`、`secret` → 请求里 `{{ProgramID}}` / `{{clientId}}` / `{{secret}}`。
3. **按池多步**：E2E S05 用 `pm.sendRequest` 串行 `plan[1..]`；`setNextRequest` 在 Apifox 常无效 → 可设 `DP_P2515_FORCE_INLINE_TAIL=1`。
4. **探测 / Doc gap / 无 cross**：生成器内 `p2515SkipOk` 对齐 pytest skip（当前数据集 Program 未必产出 cross）；完整业务绿需 P2515 专用 program + `probeMembershipId`。
5. 软断言 / moduleExclusive 增量仍以 **pytest** 为准。

## 映射文件

- `.apifox/settings.json` → `projectId: 346275`
- `.apifox/suites.yaml` → `assets.papi_2515`
