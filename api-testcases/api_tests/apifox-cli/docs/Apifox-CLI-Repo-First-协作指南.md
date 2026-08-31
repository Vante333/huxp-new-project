# Apifox CLI · Repo-first 团队协作指南

本文面向测试 / 开发 / Agent 协作者，说明如何在本仓库用 **Apifox CLI** 维护接口自动化场景（含后置 Tests），并与 Git、Cursor Skill、Apifox UI 协同。

> **从没接触过？先看小白版** → [Apifox-CLI-小白入门流程.md](./Apifox-CLI-小白入门流程.md)  
> **踩坑回顾（为什么这样设计）** → [Apifox-CLI-Repo-First-问题回顾.md](./Apifox-CLI-Repo-First-问题回顾.md)  
> **公共逻辑与长期依赖规则** → [公共逻辑收敛-落地方案.md](./公共逻辑收敛-落地方案.md)

| 项 | 值 |
|----|-----|
| 目标项目 | **346275** · `API_接口自动化` |
| 私有化地址 | `https://apifox.dragonpass.com.cn` |
| 唯一 AI 工作分支 | **`ai/apifox-cli-sync`** |
| 试点资产 | `papi_2548`（会籍 extensions） |
| Cursor Skill | [`.cursor/skills/apifox-cli-repo-first/`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) |
| 资产目录表 | [catalog.md](../../../.cursor/skills/apifox-cli-repo-first/catalog.md) |

---

## 1. 为什么用 Repo-first

| 问题 | 约定 |
|------|------|
| Apifox UI 手改脚本难评审、易丢 | **Git 生成器**为唯一真相源 |
| 私有化 `import postman` 不可用 / openapi 无 Tests | 用 **Generate → 转包 → `test-scenario update`** |
| 主分支禁止外部 AI 直写 | 一律写到 **`ai/apifox-cli-sync`**，需要时再客户端合 main |
| 多人各自建 AI 分支 | **禁止**；只复用上述唯一分支 |

**一句话**：改代码 → 离线 `Generate` 门禁 → `PushSteps` → 用户确认后 `Run/SyncCheck`；不要只在 UI 里改脚本。

---

## 2. 角色与职责

| 角色 | 职责 |
|------|------|
| 用例作者 | 维护字段级用例；**确认正向 E2E 清单**与断言期望来源（env / 公式 / 写死）；评审对照表 |
| 自动化同学 + Agent | 改 `GeneratePostmanCollection*.py` / helpers；跑 `SyncCheck`；登记 catalog；按 Skill #12/#13 先问再硬断言 |
| 评审人 | 看 Git Diff（生成器 + 集合 JSON）；对照 catalog / 本指南 / E2E 清单是否一致 |
| Apifox 使用者 | UI **切到 `ai/apifox-cli-sync`** 后运行 / 看报告；勿在 main 上改 CLI 同步场景；**勿只在 UI 手改脚本** |
| Agent（Cursor） | 先读 Skill + catalog；落场景前问目录；字段级驱动先交 E2E 清单；落地后确认 catalog 有行 |
| 平台管理员 | 私有化升级、合 main 权限、环境凭据；一般同学不依赖「外部 AI 编辑权限」菜单 |

**推广时记住**：多数同学只需「提需求 → 切分支验收」；改生成器与 SyncCheck 由自动化同学 / Agent 承担。

---

## 3. 环境准备（每人一次）

### 3.1 软件

- Windows + PowerShell
- Python 3.8+
- Node.js + 全局 CLI：`npm install -g apifox-cli@latest`（当前团队约 2.2.x）
- 能访问 `https://apifox.dragonpass.com.cn`

### 3.2 凭据（勿提交）

仓库根 `.env`：

```env
APIFOX_ACCESS_TOKEN=<你的 Apifox 访问令牌>
```

业务沙箱跑接口另需 `env/.env.<profile>`（`DP_CLIENT_ID` 等），见 [`env/README.md`](../../../env/README.md) 与 `api_tests` README。

### 3.3 项目映射（仓库已配好）

| 文件 | 内容 |
|------|------|
| [`.apifox/settings.json`](../../../.apifox/settings.json) | `projectId`、`apiBaseUrl` |
| [`.apifox/suites.yaml`](../../../.apifox/suites.yaml) | 各资产的场景 ID、环境 ID、工作分支、生成器路径 |

新人只需拉仓库 + 配自己的 `APIFOX_ACCESS_TOKEN`，不必手抄 ID。

### 3.4 数据集鉴权变量（全项目统一）

场景绑定的测试数据集里，鉴权相关列名**只许**下面三个（大小写按此书写）：

| 列名 | 请求里怎么写 |
|------|----------------|
| `ProgramID` | `{{ProgramID}}`（头 `X-Program-ID`、注册体 `programId` 字段取值） |
| `clientId` | `{{clientId}}`（鉴权 body） |
| `secret` | `{{secret}}`（鉴权 body） |

禁止再用 `programId`、`clientSecret`、`CLIENT_ID` 等别名新建数据集；历史脏数据应改回上表三列。

另：canary 路由头用环境变量 **`x-version`**（常见值 `canary`），请求头为 `x-version: {{x-version}}`，对应 pytest 的 `DP_X_VERSION`。鉴权三列放数据集；`baseUrl` / `x-version` 放 **Environment**，不必进数据集。

Auth 成功后令牌统一写入运行时 **`accessToken`**，后续请求头 `Authorization: Bearer {{accessToken}}`。勿再使用 `dpAccessToken`；数据集不要放空的 `accessToken` 列（会冲掉令牌）。

### 3.5 多环境切换

每个 Apifox Environment 各自配置 `baseUrl`（及可选 `x-version` 等）。切换方式二选一：

1. 改 [`.apifox/suites.yaml`](../../../.apifox/suites.yaml) 对应资产的 `environment_id`
2. 命令行覆盖：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548 -EnvironmentId <环境ID> -ConfirmRun`

场景仍绑定同一 `use_data_set_id`（鉴权三列）；换环境只换网关地址与路由头等环境变量。

### 3.6 自检登录

```powershell
cd <仓库根>
.\scripts\ApifoxRepoFirst.ps1 -Action WhoAmI
```

---

## 4. 日常改脚本（最短路径）

```powershell
# 1. 只改生成器（或 helpers）
# 2. 离线：反模式 lint → suites lint → 生成 → Collection 校验
.\scripts\ApifoxRepoFirst.ps1 -Action Generate -Asset papi_2548
# 3. 同步场景，但不自动 Run
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset papi_2548
# 4. 确认数据集、业务 CSV、Environment 后，才执行在线验收
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548 -ConfirmRun
```

| 结果 | 你做什么 |
|------|----------|
| 退出 0 | 完成；Apifox UI 切到 `ai/apifox-cli-sync` 刷新查看；catalog 已自动更新 |
| 有 leftover | 打开 `apifox-reports/<asset>/leftover-failures.md` 与报告；属业务/环境问题则提缺陷或改预期，**不是**再盲推 |
| 脚本类失败 | 匹配 `suites.yaml` → `triage.script_name_patterns` 时会再 Generate+Push+Run **一轮**；仍失败则改正本，**不要**新建 `TriageApifox*Failures.py` |

**PushSteps 代表脚本同步完成，不代表业务验收完成**；需要业务验收时，在用户确认数据集、Environment 与 CSV 后执行 `Run/SyncCheck`。

### 4.1 常用分步命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action Generate          # 离线门禁 + 重生/校验 collection JSON
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps         # 生成+推场景；默认不 Run
.\scripts\ApifoxRepoFirst.ps1 -Action Run -ConfirmRun   # 只跑场景并汇总失败
.\scripts\ApifoxRepoFirst.ps1 -Action Status            # 项目/资产状态
```

公共 common 变更先看影响面；Batch 不提供 Run/SyncCheck：

```powershell
python tools/apifox-cli/MapGeneratorAssets.py --affected-by <common-or-js-path>
.\scripts\ApifoxRepoFirstBatch.ps1 -Action Generate -Group smoke
```

手动刷新 catalog（一般不必）：

```powershell
python tools/apifox-cli/UpsertApifoxCliCatalog.py --asset papi_2548
```

---

## 5. 分支与 UI 约定

```text
main（团队默认可读）
  └── 合并（客户端）←── ai/apifox-cli-sync  ←── SyncCheck / PushSteps 只写这里
```

1. Apifox 左上角分支选 **`ai/apifox-cli-sync`**（不要停在 main 看 CLI 场景）。
2. **禁止**为每次改脚本新建 `ai/2026xxxx-…` 分支。
3. 脚本默认只 `branch get`；若分支被删、需重建，显式加：`-AllowCreateAiBranch`（慎用）。
4. 合回 main：客户端合并场景即可；私有化通常没有「外部 AI 编辑权限」菜单，不必卡在开权限上。

---

## 6. 命名与断言规范（协作可读）

### 6.1 请求 / 步骤名（目的前置）

```text
【中文测试目的】| 步骤ID | METHOD /path简写
```

例：`【查询扩展字段与注册一致】| S01 | POST /memberships/search`

实现：生成器内 `PurposeName(...)`。细则见 Skill [`postman-purpose-first-naming.md`](../../../.cursor/skills/api-testcase-pack/postman-purpose-first-naming.md)。

### 6.2 断言结果（期望 / 实际）

Apifox「断言结果」标题统一为：

```text
检查点 | 期望=… | 实际=…
```

通过或失败都能直接核对，避免只有「extensions 归一化一致」这类看不懂的文案。

### 6.3 编排注意（抄 2548 时）

- 依赖特定会籍的步骤：**自包含前置注册**（如 S01a → S01），勿整场景共用被覆盖的 `membershipId`。
- 快照变量已是 `[[type,value]]` 时用 `coerceToNormPairs`，勿二次错误 normalize。
- 「网关备选 POST」类步骤：沙箱默认 PATCH 时可跳过，勿硬失败。

### 6.4 按字段级用例落地（E2E 先确认 + 对照表）

完整细则：[Skill reference · 字段级用例 → E2E](../../../.cursor/skills/apifox-cli-repo-first/reference.md#字段级用例--e2e防漏断言--防猜错)。

团队约定摘要：

1. **生成前**输出正向 E2E 清单（场景名、步骤序、METHOD/path、追溯 `tc-p*`），**等人确认**再生成 Folder 内接口。
2. **P0 只减场景条数**，不砍单条 rc 字段断言；Cancel/支付等横切嵌进原 E2E。
3. 落硬断言前维护对照表：`检查点 → 期望来源 → 步骤 → 已确认|待确认|砍掉`。
4. 语义不清（如「description 为 couponName」）**先问**；未确认不做硬断言。
5. **Push**：主路径已确认可推；带猜测硬断言的版本禁止 Push。

推荐口令（提给 Agent）：

> 按该 md 字段级用例；先确认 E2E；对照表；不清先问；未确认不做硬断言再 Push。场景 description 写清变量关系。

---

## 7. 新建一个 Apifox CLI 资产（新需求）

按清单做；Agent 须先读 [Skill](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) + [catalog](../../../.cursor/skills/apifox-cli-repo-first/catalog.md)。

1. **对齐最近似资产**（当前抄 `papi_2548` / 预预约抄 FT payment / 会籍购买抄 `membership_purchase_p0`）  
   - 生成器 + Tests + `PurposeName` + 清晰断言 helpers  
   - **场景 `info.description` 写清变量关系与金额公式**（Skill 硬约束 #11；见 [reference · 场景 description](../../../.cursor/skills/apifox-cli-repo-first/reference.md#场景-description变量关系)）  
   - **按字段级用例时**：先确认正向 E2E 清单 → 字段对照表 → 不清先问 → 再 Push（Skill #12/#13；[reference · 字段级用例 → E2E](../../../.cursor/skills/apifox-cli-repo-first/reference.md#字段级用例--e2e防漏断言--防猜错)）
2. **在 `.apifox/suites.yaml` 增加 `assets.<key>`**（复制 `papi_2548` 段改字段即可）  
   - 路径必填：`generator`、`collection`  
   - 跑测必填：`test_scenario_id`、`environment_id`、`working_branch: ai/apifox-cli-sync`  
   - **Headers 必填**：`push_mode: http` + `unbind_after_push: true`（否则场景里改 Body 调试会发出空鉴权头，见 [reference · 场景 Headers 参数值为空](../../../.cursor/skills/apifox-cli-repo-first/reference.md#场景-headers-参数值为空绑定展开后再按-ui-形态解绑)）  
   - 建议填：`scenario_name`、`collection_name`、`doc`、`module_id`  
   - **不必改** `ApifoxRepoFirst.ps1`（`Get-AssetPaths` 已从 yaml 读；漏写两字段时 PushSteps 仍默认 http+unbind）  
3. **首次**：Import 场景壳（如需）→ 记下场景 ID 写入 suites → `SyncCheck -Asset <key>`  
4. **成功后**：确认 `catalog.md` 已有该行；补充 `suites/<key>.md` 笔记（可复用坑）  
5. **详解文档**（建议）：`apifox-cli/docs/<需求>-apifox-cli-repo-first.md`，并链到协作指南与 Skill  

完成标准：**Git 可评审 + SyncCheck 绿 + catalog 有行 + UI 在 AI 分支可跑。**

---

## 8. 逐文件说明（大白话）

新人精简版：[小白入门 · 每个文件干什么](./Apifox-CLI-小白入门流程.md#每个文件干什么)。

### 8.1 `.apifox/`（通信录，不含密钥）

| 文件 | 干什么 |
|------|--------|
| `settings.json` | 写死：Apifox **项目 ID**（如 346275）、私有化网址。脚本先读它，知道连哪。 |
| `suites.yaml` | **资产对照表**（`ApifoxRepoFirst` 唯一驱动源）：生成器/collection/场景名/场景 ID/环境/分支等。**扩新资产只加一段 `assets.<key>`，勿改脚本写死路径。** |
| `ai-branches.json` | 可选本机缓存（已 gitignore）；**当前脚本不读写**。勿当真相；真相是 `suites.yaml` 的 `working_branch`。 |
| `README.md` | 本目录说明 + 指向协作文档。 |
| `.gitignore` | 避免把不该提交的本地杂物提交进 Git。 |

### 8.2 `scripts/`（总开关）

| 文件 | 干什么 |
|------|--------|
| `ApifoxRepoFirst.ps1` | 团队主入口。按 `-Action` 调度：Generate / PushSteps / Run / SyncCheck / WhoAmI 等。读 `.env` Token + `.apifox` 配置，再调用下面 `tools/`。**人/AI 日常基本只碰这个。** |

### 8.3 `tools/`（被总开关调用的小工）

| 文件 | 干什么 |
|------|--------|
| `ApifoxSuitesYaml.py` | **唯一** suites.yaml 解析器（PS / Upsert / Triage 共用）。 |
| `ConvertPostmanToApifoxScenario.py` | 把 Postman 集合 JSON 转成 Apifox 2.7 导入包（前后置脚本一并带上）。 |
| `PushApifoxScenarioSteps.py` | 写入场景步骤；`--scenario-name` 来自 yaml / 包，**不写死 2548**。 |
| `SummarizeApifoxRunFailures.py` | 读报告，汇总失败步骤。 |
| `TriageApifoxRunFailures.py` | 通用判卷；默认全 leftover；禁止 per-asset triage / 改生成器。 |
| `UpsertApifoxCliCatalog.py` | upsert `catalog.md`；详解读 yaml `doc`。 |

### 8.4 `api-testcases/api_tests/apifox-cli/`（按角色拆开）

长期约定：**目录按角色拆开 + 正本唯一真相 + 集合可审、中间件可丢**。

| 目录 | 干什么 |
|------|--------|
| `generators/` | **正本**：`GeneratePostmanCollection*.py`、`collection_builder_common.py` |
| `collections/` | 可审 `*.postman_collection.json`（提交；勿手改当唯一真相） |
| `envs/` | 非 CLI 资产用的 Postman Environment（如 Local Offer）；**CLI 资产不维护**，用 Apifox `environment_id` |
| `docs/` | 协作说明、`*-apifox-cli-repo-first.md` |
| `generated/` | 本地 Apifox 导入包等（gitignore） |

以试点 `papi_2548` 为例：

| 路径 | 干什么 |
|------|--------|
| `generators/GeneratePostmanCollectionPapi2548.py` | **真相源**。改用例逻辑改它（及 helpers）。 |
| `collections/PAPI-2548-membership-extensions.postman_collection.json` | 生成器打印出的集合；给转换/同步与 PR 审阅。 |
| `.apifox/suites.yaml` → `environment_id` / `use_data_set_id` | 跑测环境与鉴权数据集（无仓库内 Postman env 模板）。 |
| `docs/PAPI-2548-apifox-cli-repo-first.md` | 2548 试点专篇。 |
| `docs/Apifox-CLI-小白入门流程.md` / `Apifox-CLI-Repo-First-协作指南.md` | 新人入门 / 本文。 |

**CLI 中间件**：`*.apifox-2.7.43-import.json`、`*.openapi.json` 由 `ApifoxRepoFirst.ps1` 写到 `apifox-reports/<asset>/generated/`（gitignore）。`suites.yaml` 可省略 `apifox_package` / `openapi_bridge`。

相关（不在 postman，但 `suites.yaml` 会指到）：

| 文件 | 干什么 |
|------|--------|
| `api-testcases/.../tests/features/test_membership_extensions.py` | pytest 侧 E2E。 |
| 仓库根 `.env` | 放 `APIFOX_ACCESS_TOKEN`。**勿提交**。 |

### 8.5 `.cursor/skills/apifox-cli-repo-first/`（给 AI 的说明书）

| 文件 | 干什么 |
|------|--------|
| `SKILL.md` | Cursor 接到 Apifox CLI / SyncCheck 类任务时**先读**的总则与硬约束。 |
| `reference.md` | 私有化坑、断言写法、分支策略等细节备忘。 |
| `catalog.md` | 「已落地哪些资产」总表；SyncCheck 成功会自动 upsert。新开资产优先抄最近似一行。 |
| `suites/papi_2548.md` | 单资产笔记：可复用技巧、场景/分支/环境速查（不替代详解 md）。 |

### 8.6 `apifox-reports/`（本机草稿纸，已 gitignore）

| 典型文件 | 干什么 |
|----------|--------|
| `apifox-reports/<asset>/generated/*` | Apifox 导入包 / OpenAPI 桥（流水线现生成，勿当正本）。 |
| `apifox-reports/<asset>/<asset>-*-failures.json` | 某次 run 失败明细（按资产目录 + 前缀）。 |
| `apifox-reports/<asset>/last-failures.md` | 该资产最近失败汇总。 |
| `apifox-reports/<asset>/leftover-failures.md` | **非脚本**残留，需人看。 |

### 8.7 树形速查

```text
.apifox/
  settings.json              # 项目 ID + 私有化网址
  suites.yaml                # 资产 ↔ 生成器/场景/环境/分支
  ai-branches.json           # 本机 AI 分支缓存
  README.md
scripts/
  ApifoxRepoFirst.ps1        # 总开关
tools/
  ApifoxSuitesYaml.py                 # 共享 suites 解析
  ConvertPostmanToApifoxScenario.py   # Postman → Apifox 包
  PushApifoxScenarioSteps.py          # 推步骤（--scenario-name）
  SummarizeApifoxRunFailures.py       # 失败汇总
  TriageApifoxRunFailures.py          # 通用分流
  UpsertApifoxCliCatalog.py           # 更新 catalog（读 doc）
api-testcases/api_tests/apifox-cli/
  README.md
  generators/   # 正本 Generate*.py + collection_builder_common.py
  collections/  # 可审 *.postman_collection.json
  envs/         # 环境模板
  docs/         # 协作说明
  generated/    # 本地中间件（gitignore）
.cursor/skills/apifox-cli-repo-first/
  SKILL.md / reference.md / catalog.md / suites/papi_2548.md
apifox-reports/<asset>/              # CLI 报告 + 中间件（不进 Git）
  generated/*.apifox-*.json
  generated/*.openapi.json
  *-failures.json / leftover-failures.md
```

---

## 9. 报告与失败怎么协作

| 产物 | 说明 |
|------|------|
| `apifox-reports/<asset>/<asset>-*-failures.json` | 本次失败明细 |
| `apifox-reports/<asset>/last-failures.md` | 失败汇总 |
| `apifox-reports/<asset>/leftover-failures.md` | **非脚本**问题，需人看 |
| Apifox UI 报告 | 切 AI 分支后查看；点步骤看「期望/实际」断言 |

**分流约定**：

- 脚本问题（编排/断言写错）→ 修生成器 → 再 `SyncCheck`（自动化会尽量修一轮已知模式）。
- 业务/环境问题 → leftover 清单 + 缺陷/环境单；不要改断言「强行变绿」除非产品确认。

---

## 10. 安全与提交

| 可以提交 | 不要提交 |
|----------|----------|
| 生成器、collection JSON、suites.yaml、Skill、本指南 | `.env`、真实 Token、含密钥的报告 |
| `apifox-reports/` 已在 `.gitignore` | 截图若含 Token 需打码 |

PR 建议写明：资产 key、是否 SyncCheck 通过、是否仅 AI 分支（未合 main）。

---

## 11. 长期维护红线（避免越养越难）

| 风险 | 怎么控 |
|------|--------|
| 有人只在 UI 改、不同步 | UI 手改不算数；合 main 前必须 `SyncCheck`；正本在生成器 |
| 私有化 CLI 行为变（import/分支权限） | 坑记 `reference.md`；升级后先跑试点再扩资产 |
| 每个需求各写一套 triage/特殊脚本 | **禁止**；只用 `TriageApifoxRunFailures.py` + 可选 yaml pattern；默认不配 pattern |
| triage / 工具里「自动改生成器」 | **禁止**；bug 合进正本，不靠运行时打补丁 |
| 长期挂过期 `script_name_patterns` | 修完即删；试点默认已清空，失败进 leftover |
| 正本与 pytest 两套断言漂移 | 以生成器/helpers 为源，pytest 与 Apifox 对齐意图 |
| 把 `apifox-reports`、`ai-branches.json` 当真相 | 只是草稿纸；真相是生成器 + `suites.yaml` |

---

## 12. FAQ

**Q：UI 里步骤名/断言还是旧的？**  
A：是否切到 `ai/apifox-cli-sync`？是否重新运行？只 Push 未 SyncCheck？main 未合并前 main 仍是旧的。

**Q：为什么不能一人一个 AI 分支？**  
A：场景 ID、协作成本、分支爆炸；统一 `ai/apifox-cli-sync`，用 Git 分支管代码差异。

**Q：catalog 是干什么的？**  
A：团队/Agent 的「已 CLI 落地资产表」。SyncCheck 成功自动 upsert 一行，方便下一个需求抄作业。

**Q：和 pytest 什么关系？**  
A：**已单轨**：正式验收只走 Apifox CLI（本指南 + `apifox-cli-repo-first`）。pytest（`api_tests/tests/`）已冻结待退役，见 `api_tests/docs/pytest-retirement-map.md`；禁止再扩新 `test_*.py`。

**Q：私有化找不到「AI 功能设置」？**  
A：正常。不依赖该菜单；写 AI 分支 + 客户端合 main。

**Q：在场景里改个入参就鉴权失败 / curl 头是 `X-Program-ID;`？**  
A：Headers「参数值」列空，发出去的是空 `Authorization`/`X-Program-ID`，不是 Body 写错。yaml 必须有 `push_mode: http` + `unbind_after_push: true`，Push 后关掉场景标签再打开；临时调试只改 Body、先跑 Auth。详见 Skill reference「场景 Headers 参数值为空」。

**Q：怎么给小组推广？**  
A：见 **§15**；新人发小白入门，群公告用 §15.6 模板，跟练日用 §15.5 checklist。

---

## 13. 相关链接

| 文档 | 用途 |
|------|------|
| [Skill SKILL.md](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) | Agent 触发与硬约束 |
| [catalog.md](../../../.cursor/skills/apifox-cli-repo-first/catalog.md) | 资产一览 |
| [reference.md](../../../.cursor/skills/apifox-cli-repo-first/reference.md) | 坑位速查 |
| [PAPI-2548 试点说明](./PAPI-2548-apifox-cli-repo-first.md) | 2548 专页 |
| [问题回顾](./Apifox-CLI-Repo-First-问题回顾.md) | 长期坑、已处理结论、仍靠纪律项 |
| [api-testcase-pack](../../../.cursor/skills/api-testcase-pack/SKILL.md) | pytest / Postman 总规范 |
| [postman README](./README.md) | 集合生成与导入说明 |
| [小白入门](./Apifox-CLI-小白入门流程.md) | 验收同学三步法 |
| §15 团队推广 | 群公告、培训 checklist、推广节奏（本文） |

---

## 14. 修订

| 日期 | 说明 |
|------|------|
| 2026-07-19 | 首版：Repo-first、唯一 AI 分支、SyncCheck、Skill/catalog 协作约定 |
| 2026-07-19 | 通用 triage；删除需求级 triage/自动改生成器；清空过期 pattern；长期红线入指南 |
| 2026-07-19 | `Get-AssetPaths` 改为读 `suites.yaml`；扩资产无需改 ps1 写死路径 |
| 2026-07-19 | P0–P2：场景名/报告前缀按资产、共享 YAML 解析、catalog 读 doc、报告分目录 |
| 2026-07-27 | §6.4 字段级 E2E/对照表；§2 角色补用例作者；**§15 团队推广**（群公告 + 培训 checklist） |
| 2026-08-24 | §7 yaml 必抄 `push_mode`+`unbind`；FAQ：UI 改入参发空鉴权头 |

---

## 15. 团队推广（如何落地到小组）

### 15.1 一句话约定（贴群 / 宣贯首页）

> 接口自动化 Apifox 场景统一 **Repo-first**：**代码（生成器）是正本，Apifox 是副本**。  
> 改仓库生成器后用 `ApifoxRepoFirst.ps1` 同步到分支 **`ai/apifox-cli-sync`**。验收请切该分支。  
> 禁止只在 Apifox UI 改脚本；禁止每人新建 `ai/日期-…` 分支。  
> 新人先看《小白入门》；扩资产看本指南 + [catalog](../../../.cursor/skills/apifox-cli-repo-first/catalog.md)。

### 15.2 文档按人分发

| 对象 | 先看 |
|------|------|
| 新人 / 只验收 | [小白入门](./Apifox-CLI-小白入门流程.md) |
| 要改脚本 / 扩资产 | 本指南全文 + catalog 最近似一行 |
| Cursor Agent | [Skill](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) + [reference 字段级→E2E](../../../.cursor/skills/apifox-cli-repo-first/reference.md#字段级用例--e2e防漏断言--防猜错) |
| 想了解为何这样 | [问题回顾](./Apifox-CLI-Repo-First-问题回顾.md) |

### 15.3 日常协作流（推广时照这个演练）

```text
提需求 / 给字段级用例
  → Agent：确认目录(L1/L2/L3) + 正向 E2E 清单（等人点头）
  → 生成骨架 → 字段对照表（不清先问）
  → SyncCheck / PushSteps
  → 人：Apifox 切 ai/apifox-cli-sync 验收
  → Git PR 审生成器 Diff
  → 需要时再合主分支（勿自动 merge）
```

### 15.4 推广节奏（建议 4 步）

| 步 | 做什么 | 完成标准 |
|----|--------|----------|
| 1 宣贯 | 30～60 分钟：正本/副本、唯一 AI 分支、小白三步 | 群公告已发；文档链接已置顶 |
| 2 跟练 | 选已绿资产（如 FT payment P0 / `membership_purchase_p0`），每人提一小改 → Sync → UI 验收 | 每人至少跑通一次验收 |
| 3 新需求模板 | 用 §6.4 口令提给 Agent；目录先问 | 新资产进 catalog |
| 4 评审合入 | PR 必看生成器；UI 手改不算交付；合 main 由熟手按需 | PR 模板含资产 key + SyncCheck 结果 |

### 15.5 培训 checklist（跟练日用）

**环境（每人一次）**

- [ ] 仓库已拉；Cursor 能开  
- [ ] 根 `.env` 有自己的 `APIFOX_ACCESS_TOKEN`（未提交）  
- [ ] Python / Node / `apifox-cli` 可用  
- [ ] `.\scripts\ApifoxRepoFirst.ps1 -Action WhoAmI` 成功  
- [ ] 知悉鉴权三列：`ProgramID` / `clientId` / `secret`；`baseUrl`、`x-version` 在 Environment  

**验收（每人一次）**

- [ ] Apifox 打开项目 **346275**  
- [ ] 左上角分支切到 **`ai/apifox-cli-sync`**  
- [ ] 找到 catalog 中任一条目场景，能看到目的前置步骤名  
- [ ] 跑一步，断言面板能看到 `期望=… | 实际=…`  

**扩资产（自动化同学）**

- [ ] 抄 catalog 最近似资产  
- [ ] 确认场景目录 L1/L2/L3  
- [ ] （字段级）E2E 清单已确认 + 对照表无「硬断言仍待确认」  
- [ ] `suites.yaml` 已登记；`SyncCheck` 绿；catalog 有行  

### 15.6 群公告模板（可直接复制）

```text
【Apifox CLI · Repo-first 协作约定】
1. 正本在 Git 生成器，Apifox 只是副本；不要只在 UI 改脚本。
2. 同步目标分支一律：ai/apifox-cli-sync（验收请先切分支）。
3. 新人：小白入门 → https://...（仓库路径 api-testcases/api_tests/apifox-cli/docs/Apifox-CLI-小白入门流程.md）
4. 扩场景/改断言：协作指南 + catalog；提需求给 Cursor 时带上字段级用例，并说「先确认 E2E、对照表、不清先问」。
5. 问题先看 leftover / 期望实际截图，再丢回 Agent 或熟手。
```

（链接请换成你们 Confluence/飞书镜像地址；仓库内以 `docs/` 路径为准。）

### 15.7 硬规矩速查

| 要 | 不要 |
|----|------|
| 改生成器再 Sync | 只改 Apifox UI |
| 复用 `ai/apifox-cli-sync` | 新建 `ai/日期-…` |
| 新场景先问目录 | 丢到根目录 |
| E2E 确认后再生成 | 按字段散落拼请求 |
| 未确认不做硬断言 | 猜 `description=couponName` 一类语义 |
| PR 审生成器 | 把 `apifox-reports` 当真相 |
