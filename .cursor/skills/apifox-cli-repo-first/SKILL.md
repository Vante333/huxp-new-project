---
name: apifox-cli-repo-first
description: >-
  私有化 Apifox CLI · Repo-first：仓库生成器为真相源，经 SyncCheck/PushSteps 写入 AI 分支场景
  （customHttp + 后置 Tests）。当用户提到 Apifox CLI、Repo-first、SyncCheck、PushSteps、
  apifox-cli-sync、场景步骤同步、test-scenario update、私有化 apifox.dragonpass.com.cn、
  或按 PAPI-2548 CLI 模式新建/扩展 Apifox 自动化时使用；**扩品类预预约 payment**（Lounge/Fitness
  对齐 FT Membership/E-pass、品类扩展指南）时须先读 reference 链到的通识文档。Agent 须先读本 Skill 与 catalog.md；
  **新建/首次 Push 场景前必须先问用户挂载目录**（membership|epass|common × P0/P1 × prebooking|walk-in|others），
  再生成与同步。场景 `info.description` 须写清变量关系与金额公式（见 reference「场景 description」）。
  **按字段级用例落地时**：先确认正向 E2E 步骤序；P0 减场景不减字段断言；对照表 + 语义不清先问；未确认不做硬断言再 Push（见 reference「字段级用例 → E2E」）。
  落地完成后更新 catalog（SyncCheck 成功会自动 upsert 表格行）。
---

# Apifox CLI · Repo-first

## 必读顺序

1. 本文件（流程与硬约束）
2. [`catalog.md`](./catalog.md)（已落地资产，优先抄最近似一行）
3. [`reference.md`](./reference.md)（坑位与断言规范）
4. 对应详解（catalog「详解」列或 `suites/*.md`）
5. **扩品类预预约 payment**（Lounge 等对齐 FT）：[`Prebooking-Payment-品类扩展指南.md`](../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)

交叉：pytest/Postman 生成器总规范见 [`api-testcase-pack`](../api-testcase-pack/SKILL.md)。

**团队协作（新人必读）：**  
小白入门：[`Apifox-CLI-小白入门流程.md`](../../../api-testcases/api_tests/postman/docs/Apifox-CLI-小白入门流程.md)  
团队协作：[`Apifox-CLI-Repo-First-协作指南.md`](../../../api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-协作指南.md)（**§15 团队推广**：群公告 / 培训 checklist）

## 硬约束

1. **真相源在仓库**：改断言/步骤名只改 `postman/generators/GeneratePostmanCollection*.py`（及 helpers），再 CLI 同步；禁止只改 Apifox UI。集合在 `postman/collections/`（可审）；中间件可丢（`apifox-reports/<asset>/generated/` 或 `postman/generated/`）。
2. **唯一 AI 工作分支**：`.apifox/suites.yaml` → `working_branch`（当前 `ai/apifox-cli-sync`）。禁止按日期新建 `ai/*`。
3. **步骤类型**：`customHttp` + `postProcessors/customScript`；勿用 `type=http` + `apiDetailId=0`。
4. **命名**：`PurposeName` → `【中文目的】| 步骤ID | METHOD /path`。
5. **断言标题**：`检查点 | 期望=… | 实际=…`（Apifox 断言面板可核对）。
6. **验收命令**：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck`（生成→推送→跑→按 `suites.yaml` triage 分流→SCRIPT 类再 Generate+Push+Run 一轮→仅遗留 leftover）。禁止每需求新建 triage `.py`。
7. **映射**：`.apifox/settings.json`（projectId/apiBaseUrl 权威）+ `.apifox/suites.yaml`（资产路径/场景/环境/分支）；解析统一走 `tools/ApifoxSuitesYaml.py`。报告与临时中间件在 `apifox-reports/<asset>/`（`generated/` 放 apifox 包 / openapi，勿提交；`suites.yaml` 可省略这两路径）。
8. **数据集鉴权三列（唯一标准名）**：`ProgramID`、`clientId`、`secret`。生成器 / 请求体 / 头一律 `{{ProgramID}}` `{{clientId}}` `{{secret}}`。**禁止**新建数据集或文档使用 `programId` / `clientSecret` / `CLIENT_ID` 等别名。运行时令牌统一 `accessToken`（禁止 `dpAccessToken`）。多环境变量（`baseUrl`、`x-version`）放 Environment，用 `environment_id` / `-EnvironmentId` 切换。
9. **场景目录先问再落**：新建 / 首次 Push 场景前，**必须先问用户**放在哪一级路径（见下「场景目录树」），确认后再 `test-scenario create/update --folder-id` 或 SyncCheck。禁止默认丢到根目录或擅自猜目录。目录树与 CLI 见 [`reference.md`](./reference.md)「场景用例目录」。
10. **场景内分组按业务主轴**：一级=支付方式/订单形态等，二级=点数与关键入参；横切能力（发起支付、async、取消后查询）嵌进链路，**禁止**单独开组。细则与 Agent 决策表见 [`reference.md`](./reference.md)「场景内分组」。
11. **场景 description 必须写清变量关系**：生成器 `info.description`（经 PushSteps 写入 Apifox 场景说明）须含生成源、链路、**Environment/集合变量 → 入参/断言期望的映射与金额公式**；禁止只写一句「P0 冒烟」。模板与金样例见 [`reference.md`](./reference.md)「场景 description（变量关系）」。
12. **正向 E2E 先确认再生成**：用户给出字段级用例 / 要求按用例生成时，**先**输出正向 E2E 清单（场景名、步骤序、追溯用例、METHOD/path），**等用户确认后**再按该顺序生成 Folder 内接口；横切（Cancel/支付等）嵌进原 E2E，禁止擅自另开重复分组。细则见 [`reference.md`](./reference.md)「字段级用例 → E2E」。
13. **字段断言对照表 + 不清先问**：P0 **只减场景条数，不砍单条 rc 字段断言**。落硬断言前维护对照表（检查点→期望来源→步骤→状态）。状态仅 `已确认` / `待确认` / `砍掉(需用户书面同意)`。语义不清（如「description 为 couponName」是响应对等还是 Environment）**必须先问用户**，禁止猜测写硬断言。Push 规则见同节。

## 场景目录树（项目 346275 · AI 分支）

三级固定（名称勿自造别名）：

```text
{membership|epass|common}
  / {P0(冒烟用例)|P1（全量用例）}
    / {prebooking|walk-in|others}
```

- **P0** = 冒烟；**P1** = 全量。
- 目录写入走 `working_branch`（当前 `ai/apifox-cli-sync`）；主分支常无外部 AI 直编权限。
- 已有场景挪目录：`apifox test-scenario update <id> --folder-id <id> --branch <working_branch>`（只改 folderId，勿整文件 PUT 误清空 steps）。

## 标准流水线

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <asset_key>
```

分步：`Generate` / `PushSteps` / `Run`。工具链见 `reference.md`。

**SyncCheck 成功后**：自动执行 `tools/UpsertApifoxCliCatalog.py --asset <key>`，幂等更新 [`catalog.md`](./catalog.md) 表格行。

## Agent 义务（做完才算完成）

1. **落场景前先问目录**：一级 `membership|epass|common` × 二级 `P0(冒烟用例)|P1（全量用例）` × 三级 `prebooking|walk-in|others`；用户未指定则**停住询问**，勿开写生成器联调 / Push / create。
2. 新资产：在 `.apifox/suites.yaml` 的 `assets` 下增加 key，填齐 `test_scenario_id` / `scenario_folder` / `scenario_folder_id` / `environment_id` / `working_branch` / `generator`；`suites/<key>.md` 同步记目录。
3. 对齐 catalog 最近似资产（如 `papi_2548`）的生成器与 SyncCheck 模式。
4. SyncCheck 绿后确认 `catalog.md` 已有/已更新该行；若未自动写入则手动跑 upsert。
5. 新坑写入 `reference.md` 或 `suites/<asset_key>.md`，**不要**把 SKILL.md 写爆。
6. 缺 catalog 条目视为任务未完成。
7. 用户报 Auth 后续失败 / token 未传 / CLI 与 UI 不一致时：按 [`reference.md`](./reference.md)「症状 → 自动处置」改生成器并 SyncCheck，勿只口头解释。
8. **P1/多场景编排**：默认按 [`reference.md`](./reference.md)「场景内分组」用嵌套 `Folder`→`group`；横切步骤嵌进主链路，勿单开「发起支付/async」类分组。
9. **场景 description**：新建/大改生成器须实现 `BuildScenarioDescription()`（或等价），写入变量关系与金额公式；Push 后在 Apifox UI 能直接读懂换测改哪些变量。
10. **字段级/按用例生成**：先交 E2E 清单待确认 → 再骨架 → 再字段对照表；`待确认` 不做硬断言；带猜测硬断言的版本禁止 Push（见 reference「字段级用例 → E2E」）。

## 新建资产检查清单

- [ ] **已向用户确认**场景目录（L1/L2/L3），并写入 `suites/<asset>.md`  
- [ ] **（按用例时）已确认正向 E2E 清单**（步骤序 + 追溯）；Folder 内顺序与确认一致  
- [ ] **（按用例时）字段断言对照表**无漏项；无「已硬断言但仍待确认」  
- [ ] 生成器含 Tests + `PurposeName` + 清晰断言 helpers  
- [ ] **场景 `info.description` 含变量关系**（生成源 / 链路 / 变量→期望公式；见 reference「场景 description」）  
- [ ] `suites.yaml` 已填 ID，复用 `ai/apifox-cli-sync`  
- [ ] 场景已挂到约定 `folderId`（非根目录孤儿）  
- [ ] `SyncCheck` 通过  
- [ ] `catalog.md` 有对应行  
- [ ] （建议）`suites/<asset>.md` 记录可复用坑  
- [ ] P1 多场景：已按业务主轴二级分组；横切能力已嵌进链路（见 reference「场景内分组」）  
