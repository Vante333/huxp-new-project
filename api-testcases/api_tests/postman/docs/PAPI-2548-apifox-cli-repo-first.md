# PAPI-2548 · 全量 CLI（含后置 Tests）

目标项目：**346275** · 私有化 `https://apifox.dragonpass.com.cn`。  

- **小白入门（推荐先读）：** [`Apifox-CLI-小白入门流程.md`](./Apifox-CLI-小白入门流程.md)  
- **团队协作指南：** [`Apifox-CLI-Repo-First-协作指南.md`](./Apifox-CLI-Repo-First-协作指南.md)  
- Agent Skill：[`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)（含 `catalog.md`；SyncCheck 成功自动 upsert）

## 已跑通结果（2026-07-19）

| 项 | 值 |
|----|-----|
| 场景 ID | **365969**（`PAPI-2548 extensions · CLI sync`） |
| 步骤 | **38**（含 Search 自包含前置 S01a/S02a），每步 `postProcessors[].type=customScript` |
| 工作分支 | **唯一复用** `ai/apifox-cli-sync`（后续脚本都写这里，不要再建新 ai/*） |
| 一键命令 | `.\scripts\ApifoxRepoFirst.ps1 -Action Sync` |

## 为何不能「一条 import 完事」

| 方式 | 结果 |
|------|------|
| `import --format postman` | 私有化 `Invalid Parameter` |
| `import --format openapi` | 只有 path，**无** Tests |
| `import --format apifox` | 能建场景壳，但 `steps=[]` |
| **AI 分支 + `test-scenario update`（`customHttp`）** | **成功写入 36 步 + 后置脚本**（勿用 `type=http`+`apiDetailId=0`，会报「关联接口无法找到」） |

## 全量 CLI 流水线（零 UI 改脚本）

```powershell
# 生成 Postman → 转 Apifox 包 → import 场景壳 → AI 分支 push 36 步 Tests
.\scripts\ApifoxRepoFirst.ps1 -Action Sync
```

分步：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action Generate
.\scripts\ApifoxRepoFirst.ps1 -Action Import          # 默认 apifox 包
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps       # 写满 steps+Tests（AI 分支）
.\scripts\ApifoxRepoFirst.ps1 -Action Run             # 读 suites.yaml 的 scenario/branch
```

工具链：

| 脚本 | 作用 |
|------|------|
| `generators/GeneratePostmanCollectionPapi2548.py` | Tests 真相源 |
| `tools/ConvertPostmanToApifoxScenario.py` | Postman → 含 customScript 的 apifox 包 |
| `tools/PushApifoxScenarioSteps.py` | `test-scenario update` 写入步骤 |
| `scripts/ApifoxRepoFirst.ps1` | 编排以上步骤 |

## 日常改断言 / 改步骤名（减少人工）

1. 只改生成器 / pytest helpers（请求名用 `PurposeName` 中文目的）  
2. **生成 + 推送 + 跑 + 通用 triage（推荐）**：  
   ```powershell
   .\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck
   ```  
   - Generate → PushSteps → `apifox run` → `TriageApifoxRunFailures`  
   - 试点默认**无** `script_name_patterns` → 失败一律 leftover（改正本后再 SyncCheck）  
   - leftover 写入 `apifox-reports/leftover-failures.md` 并非 0 退出  
   - **成功后**：`UpsertApifoxCliCatalog.py` 更新 Skill [`catalog.md`](../../../.cursor/skills/apifox-cli-repo-first/catalog.md)  
   - 断言标题：`检查点 | 期望=… | 实际=…`  
3. 仅同步不跑：`PushSteps` / `Sync`（会提示加 `-CheckRun`）  
4. 仅重跑汇总：`.\scripts\ApifoxRepoFirst.ps1 -Action Run`  
5. **Apifox UI** 始终切到同一 `working_branch` 刷新；main 需客户端合并  
6. **分支策略**：只维护 `.apifox/suites.yaml` 里这一条 AI 分支；脚本默认 `branch get`，不存在时需显式 `-AllowCreateAiBranch`（禁止每次改脚本新建日期分支）  
7. 私有化通常 **没有**「外部 AI 编辑权限」菜单，合 main 用客户端合并即可

## 映射文件

- `.apifox/settings.json` → `projectId: 346275`  
- `.apifox/suites.yaml` → `test_scenario_id: 365969`、`working_branch: ai/...`

填好 `environment_id` 后即可稳定 `-Action Run`。

## 踩坑复盘 · 下次同类问题怎么自动解决

### 现象 → 根因（先对号）

| 你看到的 | 真实原因 |
|----------|----------|
| 改了生成器 / 本地 JSON，Apifox 列表仍旧名 | **只改了仓库，没有 `PushSteps`**；UI 不会读本地文件 |
| Push 成功但 UI 仍旧 | **看错分支**：步骤写在 AI 分支，main 未合并前仍是旧内容 |
| `import postman` 失败 | 私有化不支持该 format |
| import 后无 Tests / steps 空 | openapi 无脚本；apifox 包常只建壳，必须再 `test-scenario update` |
| 步骤报「关联接口无法找到」 | 勿用 `type=http`+`apiDetailId=0`；用 **`customHttp`** |
| 主分支 update 403/422 | 未开「外部 AI 编辑权限」→ 写 **唯一 AI 工作分支**（见 suites.yaml，勿新建） |
| 冒出很多 ai/日期-… 分支 | 违反复用约定；应只 push 到 `working_branch` |

### 标准动作（改名 / 改断言后）

```powershell
# 推荐：只刷新已有场景步骤 + 自动校验远程名
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps

# 或全量：Generate → Import 壳 → PushSteps（含校验）
.\scripts\ApifoxRepoFirst.ps1 -Action Sync
```

Push 后脚本会：`test-scenario get` → 校验条数、`【中文目的】| …`、与包内一致；失败非 0。  
**Agent/人工收尾**：Apifox UI 切到 `suites.yaml` 的 `working_branch` → 硬刷新。

### 命名规范（生成器）

- 格式：`【测试目的（中文）】| 步骤ID | METHOD /path`
- 实现：`PurposeName(...)`；禁止仅用 `R01 test_xxx` / 路径在前
- 细则：`.cursor/skills/api-testcase-pack/postman-purpose-first-naming.md`

### 新需求复用清单

1. 复制/对齐生成器（含 Tests + `PurposeName`）  
2. `.apifox/settings.json` + `suites.yaml` 填 `project_id` / `test_scenario_id` / `working_branch`  
3. 首次：`Sync`；日常改脚本：`PushSteps`  
4. 步骤类型固定 `customHttp` + `postProcessors/customScript`  
5. UI 核对前先确认分支；要给全员看再 merge AI→main  
6. 未填 `environment_id` 前 `-Action Run` 不完整