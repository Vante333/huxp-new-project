# PAPI-2424 · 全量 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。

- **小白入门：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 已落地映射

| 项 | 值 |
|----|-----|
| 资产 key | `papi_2424` |
| 场景 ID | **365975**（`PAPI-2424 ePasses details MS · CLI sync`） |
| 场景目录 | `epass/P1（全量用例）/others`（folderId **350039**） |
| 环境 ID | **351893**（与 PAPI-2548 共用 UAT/canary） |
| 数据集 ID | **3475756**（`use_data_set_id`；列名：`ProgramID` / `clientId` / `secret`） |
| 工作分支 | **`ai/apifox-cli-sync`**（唯一复用，勿新建 ai/*） |
| 生成器 | `generators/GeneratePostmanCollectionPapi2424.py` |
| pytest | **已删**（2026-08-12）；正式验收仅 CLI |

## 一键命令

```powershell
# 生成 → 推 AI 分支 → 跑 UAT → triage → 成功则 upsert catalog
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2424
```

分步：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action Generate -Asset papi_2424
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset papi_2424
.\scripts\ApifoxRepoFirst.ps1 -Action Run -Asset papi_2424
```

## 日常改断言

1. 只改生成器 / `papi2424_helpers` / services（请求名用 `PurposeName`）
2. `SyncCheck -Asset papi_2424`
3. Apifox UI 切到 `ai/apifox-cli-sync` 硬刷新

## 首次落地：填数据集（必做）

CLI **无法**写入数据集行内容。场景已绑 `use_data_set_id=3475756`（「数据 1」），请在 Apifox UI：

1. 切分支 **`ai/apifox-cli-sync`**
2. 打开场景 **PAPI-2424 ePasses details MS · CLI sync** → 测试数据「数据 1」
3. 建一行三列（名称必须完全一致）：

| ProgramID | clientId | secret |
|-----------|----------|--------|
| `DP_EPASS_PROGRAM_ID` | `DP_EPASS_CLIENT_ID` | `DP_EPASS_CLIENT_SECRET` |

取值来自本地 `env/.env.canary`（**ePass** 三件套，勿填 membership）。
4. 再跑：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2424`

未填时 Auth 会因空 `clientId`/`secret` 失败，后续 MS 断言也会连锁失败。

## 业务注意（相对 2548）

1. **鉴权填 ePass 凭据**：数据集三列仍为 `ProgramID` / `clientId` / `secret`，取值对应
   `DP_EPASS_PROGRAM_ID` / `DP_EPASS_CLIENT_ID` / `DP_EPASS_CLIENT_SECRET`，
   **不要**填会籍 membership 那套 client。数据集**不要**加空列 `accessToken`。
2. **path / orderId 写死**：场景里 `{{p2424V2DetailsPath}}` 一类集合变量常不解析（Auth 绿、后续 `201.000.001`）；生成器已写死 `/v2/orders/ePasses/details` 与静态 `orderId`。
3. **usage 回归步（NM01）**：Group 02 前嵌 **fastTrack** 造数链（对齐 FT P0 E02）：
   `SETUP-S01` 创建 ePass → `SETUP-S02` 可用性 → `SETUP-S03` prebooking（写 `usageOrderId` 并同步 `p2424UsageOrderId`）→
   `NM01` details → `SETUP-S04` 取消 usage → `NM02`/`NM03`。
   须 Environment/集合填 `fastTrackResourceId`（默认 `C10826`）。若造数失败导致订单号皆空则 Tests **软跳过**。
4. **小写 ms（CS02）**：由集合变量 `DP_P2424_MS_PREFIX_CASE_INSENSITIVE` 控制是否与大写同信封。
5. **V1 对拍（VV01）**：路径 `/v1/orders/ePasses/details`；网关无 V1 时可能 leftover。

## 映射文件

- `.apifox/settings.json` → `projectId: 346275`
- `.apifox/suites.yaml` → `assets.papi_2424`
