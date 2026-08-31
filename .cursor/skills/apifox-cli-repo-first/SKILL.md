---
name: apifox-cli-repo-first
description: >-
  私有化 Apifox CLI · Repo-first：仓库生成器为真相源，经 SyncCheck/PushSteps 写入 AI 分支场景
  （customHttp + 后置 Tests）。当用户提到 Apifox CLI、Repo-first、SyncCheck、PushSteps、
  apifox-cli-sync、场景步骤同步、test-scenario update、私有化 apifox.dragonpass.com.cn、
  或按 PAPI-2548 CLI 模式新建/扩展 Apifox 自动化时使用；**扩品类预预约 payment**（Lounge/Fitness
  对齐 FT Membership/E-pass、品类扩展指南）时须先读 reference 链到的通识文档。
  **Headers 参数值为空 / 看不到蓝色 {{变量}} / 绑定真实接口 / 解绑 / 已关联接口文档 / 手动解绑能共存 / 解绑后值又没了 / 前端改入参就报错 / UI 改参调试 / curl 头 X-Program-ID; Authorization;（无值） / 业务步 201.000.001 invalid secret / 每步脚本雷同 / helpers 内联撑包 / ftPayHelpersSource / rdHelpersSource**：
    先读 reference「场景 Headers 参数值为空」与「多步 helpers：Auth 写入 *HelpersSource」。UI 改 Body 后鉴权失败 = 空头，不是入参非法；yaml 两字段 + Push 解绑，并扫全量缺字段资产。
  **换测 / 改哪些环境变量 / Group 用哪些变量 / 填写指南 / 控制台打印变量 / 断言面板字太多**
  / **全量数据 / 数据集选行 / scenario-env / apifox-dataset**
    时：先读 reference「换测 Environment」与「变量供给：数据集选行 vs Environment」再改生成器。
  Agent 须先读本 Skill 与 catalog.md；
  **新建/首次 Push 场景前必须先问用户挂载目录**（membership|epass|common × P0/P1 × prebooking|walk-in|others），
  再生成与同步。场景 `info.description` 须写清变量关系与金额公式（见 reference「场景 description」）。
  **按字段级用例落地时**：先确认正向 E2E 步骤序；P0 减场景不减字段断言；对照表 + 语义不清先问；未确认不做硬断言再 Push（见 reference「字段级用例 → E2E」）。
  **变量供给（必问）**：新建/大改多 Group 前先问用户选 **A 数据集选行驱动** 或 **B Environment 手填**（>5 Group 推荐 A）；未选不得开写。细则见 reference「变量供给：数据集选行 vs Environment」。
  **鉴权选行 / X-Program-ID 不对 / 勾了第二套 Program 后续仍是第一套 / Bearer 头写死 ProgramID**：
  先读 reference「鉴权选行与后续步骤 ProgramID」并按症状表改生成器后 Push，勿只口头解释。
  **业务 Preview/Create body 多出 clientId/secret / 这两个参数不要传**：
  先读 reference「业务 body 误带 clientId/secret」——种子勿对任意 body 注入鉴权字段；改生成器后 Push，勿只改 UI。
  **prebookingDate 写死 / 实际请求仍是过期日期 / 感觉还是写死的 / 10天后 11天后**：
  先读 reference「预预约 prebookingDate」——每次本机今天+10 起、时刻 T10:00、每个下单 Group 依次+1；禁止沿用 Environment 旧值。
  **301.000.001 / X-Request-ID invalid / curl 头 X-Request-ID;（无值）**：
  先读 reference「空 X-Request-ID → 301.000.001」——挂 Lines_EnsureRequestIdHeader 后 Push，勿只让用户手填 UUID。
  **只见 hu-HU / 只跑一个语种 / forEach 多轮 language 不变 / scanLanguages 循环卡住**：
  先读 reference「症状 → 自动处置」语种钳死行 + [`suites/resource_details_scan_langdyn.md`](./suites/resource_details_scan_langdyn.md)；改生成器清零 `scanLangIterM*`、禁 `Math.min` 钳末项后 Push，勿只改 Environment。
  **后续步不是注册返回的 ID / 列表没有刚注册会籍 / users/memberships 多了 status:1**：
    先读 reference「注册后 runtime ID 被 Environment / OAS 样例盖掉」——捕获用响应、后续强制回填、列表不传 OAS 样例 status；改公共 helper 后 Push，勿让用户手填 Environment。
  **全是 Auth、0 个 GET / accessToken 空 / ProgramID=EMPTY / 数据集 404**：
    先对 `use_data_set_id` 与场景 UI「数据 N」是否一致（见症状表），改 `suites.yaml` 后 Push；勿先怀疑语种列表。
  落地完成后更新 catalog（SyncCheck 成功会自动 upsert 表格行）。
  **SyncCheck/Run 前必问**：是否现在跑、用哪套鉴权/业务数据集、新 CSV 是否已在 Apifox 导入勾选；未确认不得擅自 SyncCheck/Run（默认先 PushSteps）。
  **_tmp_ / tools 草稿纸 / 调试完删除无用文件 / 一次性探测脚本**：结束前自动删，勿等用户开口；先读硬约束 7a 与 reference「调试收尾」。
---

# Apifox CLI · Repo-first

## 必读顺序

1. 本文件（流程与硬约束）
2. [`catalog.md`](./catalog.md)（已落地资产，优先抄最近似一行）
3. [`reference.md`](./reference.md)（坑位与断言规范）
4. 对应详解（catalog「详解」列或 `suites/*.md`）
5. **扩品类预预约 payment**（Lounge 等对齐 FT）：[`Prebooking-Payment-品类扩展指南.md`](../../../api-testcases/api_tests/apifox-cli/docs/Prebooking-Payment-品类扩展指南.md)
6. **改公共 JS / 减 copy / 新品类入口**：[`公共逻辑收敛-落地方案.md`](../../../api-testcases/api_tests/apifox-cli/docs/公共逻辑收敛-落地方案.md)（薄入口 → 域 common → `collection_builder_common`；禁止 common 反向 import `Generate*.py`）

交叉：pytest/Postman 生成器总规范见 [`api-testcase-pack`](../api-testcase-pack/SKILL.md)。

**团队协作（新人必读）：**  
小白入门：[`Apifox-CLI-小白入门流程.md`](../../../api-testcases/api_tests/apifox-cli/docs/Apifox-CLI-小白入门流程.md)  
团队协作：[`Apifox-CLI-Repo-First-协作指南.md`](../../../api-testcases/api_tests/apifox-cli/docs/Apifox-CLI-Repo-First-协作指南.md)（**§15 团队推广**：群公告 / 培训 checklist）

## 硬约束

1. **真相源在仓库**：改断言/步骤名只改 `apifox-cli/generators/GeneratePostmanCollection*.py`（及 helpers），再 CLI 同步；禁止只改 Apifox UI。集合在 `apifox-cli/collections/`（可审）；中间件可丢（`apifox-reports/<asset>/generated/` 或 `apifox-cli/generated/`）。**单轨**：禁止新增 pytest `test_*.py` 作正式验收。
2. **唯一 AI 工作分支**：`.apifox/suites.yaml` → `working_branch`（当前 `ai/apifox-cli-sync`）。禁止按日期新建 `ai/*`。
3. **步骤类型与 Headers UI（新建必抄）**：最终 UI 形态是**解绑后的** `customHttp`（Headers 参数值可见蓝色 `{{变量}}`，可临时改 Body 调试）。到达该形态：**每个** `assets.<key>` 必须写 `push_mode: http` + `unbind_after_push: true`（复制 `papi_2548` 段时勿漏）。`ApifoxRepoFirst.ps1` 若 yaml 漏写，PushSteps **仍默认 http+unbind**，禁止再走「裸 customHttp → 参数值列空 → UI 改入参发空鉴权头」。**禁止** `type=http` + `apiDetailId=0`。解绑须对齐 UI：相对 path、header 写 `name`+`value`+`sampleValue`（禁止 Postman `key`、禁止只清 bind 留 `type=http`）。细则见 [`reference.md`](./reference.md)「场景 Headers 参数值为空」。
3b. **多步 helpers（新建/大改默认）**：禁止把完整 `ftPay*`/`rd*` helpers 内联进每一个业务步。Auth（只此一次）写入 `*HelpersSource`（四作用域），其它步前置/后置约 10 行 `eval` loader + **本步**造数/断言；payment 断言只挂 Preview/Create/Detail。金样：`ft_prebooking_payment_common.RequestItem`、Resource Details Scan 的 `rdHelpersSource`。细则见 [`reference.md`](./reference.md)「多步 helpers」。
4. **命名**：`PurposeName` → `【中文目的】| 步骤ID | METHOD /path`。
5. **断言标题**：`检查点 | 期望=… | 实际=…`（Apifox 断言面板可核对）。
6. **验收命令**：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -ConfirmRun`（生成→推送→跑→按 `suites.yaml` triage 分流→SCRIPT 类再 Generate+Push+Run 一轮→仅遗留 leftover）。禁止每需求新建 triage `.py`。
6a. **SyncCheck / Run 前必须咨询用户（硬停）**：Agent **禁止**在用户未明确同意时擅自执行 `-Action SyncCheck`、`-Action Run`、或带 `-CheckRun` 的 Push/Sync。默认只做到 **Generate + PushSteps**。开跑前须用简短清单问清并得到回复：
    1. **现在要不要跑？** → 否 / 只要 Push / 要 Run / 要 SyncCheck  
    2. **鉴权数据集**：沿用 `suites.yaml` 的 `use_data_set_id`，还是换另一套（用户给出 ID 或名称）？  
    3. **业务全量数据（选行驱动 A）**：是否已在 Apifox 场景「全量数据」**导入并勾选**本次 CSV（路径告知用户）？未导入则 **停住**，等用户说「已导入」后再跑。  
    4. **Environment**：是否沿用当前 `environment_id`，或指定 `-EnvironmentId`？  
    用户说「先导入数据集再跑」时：只 PushSteps（必要时更新 `use_data_set_id`），**等用户确认已导入/已勾选后再** Run 或 SyncCheck。
7. **映射**：`.apifox/settings.json`（projectId/apiBaseUrl 权威）+ `.apifox/suites.yaml`（资产路径/场景/环境/分支）；解析统一走 `tools/apifox-cli/ApifoxSuitesYaml.py`。报告与临时中间件在 `apifox-reports/<asset>/`（`generated/` 放 apifox 包 / openapi，勿提交；`suites.yaml` 可省略这两路径）。
7a. **少落盘 + 调试完自动清**：默认 PushSteps / 不带 Run；Run 默认 `cli,json`（`-FullReports` 才要 html）。禁止 `tools/_tmp_*` 与往 `apifox-reports` 写调试 dump。**本轮 CLI/环境排查结束后必须自动删除**本次 `_tmp_*`、无引用的一次性 `_patch_*`/`_gen_*`、仓库内 dump，再结束回复；结论写进生成器 / yaml / reference，勿把探测脚本留在 `tools/`。细则见 [`.cursor/rules/local-scratch-hygiene.mdc`](../../rules/local-scratch-hygiene.mdc) 与 [`reference.md`](./reference.md)「调试收尾」。
8. **数据集鉴权三列（唯一标准名）**：`ProgramID`、`clientId`、`secret`。生成器 / 请求体 / 头一律 `{{ProgramID}}` `{{clientId}}` `{{secret}}`。**禁止**新建数据集或文档使用 `programId` / `clientSecret` / `CLIENT_ID` 等别名。运行时令牌统一 `accessToken`（禁止 `dpAccessToken`）。多环境变量（`baseUrl`、`x-version`）放 Environment，用 `environment_id` / `-EnvironmentId` 切换。  
   **禁止**生成时把 `.env` 的 ProgramID/clientId/secret **字面量**写进 Auth body、`BearerJsonHeaders` 的 `X-Program-ID`。  
   **鉴权种子优先级**（后续步骤跟选行必抄）：`iterationData` → **Environment** → `variables` → `collection` → `globals` → 本机 `.env` 回落；选中后须写回 **四作用域**（与 `accessToken` 同）。细则与症状见 [`reference.md`](./reference.md)「鉴权选行与后续步骤 ProgramID」。
9. **场景目录先问再落**：新建 / 首次 Push 场景前，**必须先问用户**放在哪一级路径（见下「场景目录树」），确认后再 `test-scenario create/update --folder-id` 或 SyncCheck。禁止默认丢到根目录或擅自猜目录。目录树与 CLI 见 [`reference.md`](./reference.md)「场景用例目录」。
10. **场景内分组按业务主轴**：一级=支付方式/订单形态等，二级=点数与关键入参；横切能力（发起支付、async、取消后查询）嵌进链路，**禁止**单独开组。细则与 Agent 决策表见 [`reference.md`](./reference.md)「场景内分组」。
11. **场景 description 必须写清变量关系**：生成器 `info.description`（经 PushSteps 写入 Apifox 场景说明）须含生成源、链路、**Environment/集合变量 → 入参/断言期望的映射与金额公式**；禁止只写一句「P0 冒烟」。模板与金样例见 [`reference.md`](./reference.md)「场景 description（变量关系）」。
12. **正向 E2E 先确认再生成**：用户给出字段级用例 / 要求按用例生成时，**先**输出正向 E2E 清单（场景名、步骤序、追溯用例、METHOD/path），**等用户确认后**再按该顺序生成 Folder 内接口；横切（Cancel/支付等）嵌进原 E2E，禁止擅自另开重复分组。细则见 [`reference.md`](./reference.md)「字段级用例 → E2E」。
13. **字段断言对照表 + 不清先问**：P0 **只减场景条数，不砍单条 rc 字段断言**。落硬断言前维护对照表（检查点→期望来源→步骤→状态）。状态仅 `已确认` / `待确认` / `砍掉(需用户书面同意)`。语义不清（如「description 为 couponName」是响应对等还是 Environment）**必须先问用户**，禁止猜测写硬断言。Push 规则见同节。
14. **变量供给先问再生成**：新建 / 大改「多 Group / 字段级全量」场景前，**必须先问用户**选：
    - **A · 数据集选行驱动**（Apifox「全量数据」一行一场景；推荐用例 Group **>5**）
    - **B · Environment 手填**（Environment 键差分 + 控制台短提示；适合 ≤5 或单冒烟）
    用户未选则**停住询问**，禁止默认只堆 Environment。细则与产物清单见 [`reference.md`](./reference.md)「变量供给：数据集选行 vs Environment」。

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

**默认（Agent）**：Generate → PushSteps → **停下来问用户**（见硬约束 6a）→ 用户同意后再 Run / SyncCheck。

```powershell
# 先推步骤（默认停在这里）
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset <asset_key>

# 用户确认数据集已导入 / 同意验收后再：
.\scripts\ApifoxRepoFirst.ps1 -Action Run -Asset <asset_key> -ConfirmRun
# 或完整 SyncCheck（含 triage）
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <asset_key> -ConfirmRun
```

分步：`Generate` / `PushSteps` / `Run`。工具链见 `reference.md`。

**SyncCheck 成功后**：自动执行 `tools/apifox-cli/UpsertApifoxCliCatalog.py --asset <key>`，幂等更新 [`catalog.md`](./catalog.md) 表格行。

## Agent 义务（做完才算完成）

1. **落场景前先问目录**：一级 `membership|epass|common` × 二级 `P0(冒烟用例)|P1（全量用例）` × 三级 `prebooking|walk-in|others`；用户未指定则**停住询问**，勿开写生成器联调 / Push / create。
1b. **落场景前先问变量供给**：**每次**新建/大改多 Group 或字段级全量时，必须先给出二选一并**等用户确认**：
    - **A · 数据集选行驱动**（全量数据；>5 强烈推荐）
    - **B · Environment 手填**（≤5 / 单冒烟也可）
    禁止未问就只堆 Environment。仅「P0 恰好两条冒烟且用户已说只要 Environment」可跳过追问。
2. 新资产：在 `.apifox/suites.yaml` 的 `assets` 下增加 key，填齐 `test_scenario_id` / `scenario_folder` / `scenario_folder_id` / `environment_id` / `working_branch` / `generator`；`suites/<key>.md` 同步记目录。
3. 对齐 catalog 最近似资产（如 `papi_2548`）的生成器与 PushSteps 模式；**验收跑测须先问用户**（硬约束 6a）。
4. 用户同意并 SyncCheck 绿后确认 `catalog.md` 已有/已更新该行；若未自动写入则手动跑 upsert。
5. 新坑写入 `reference.md` 或 `suites/<asset_key>.md`，**不要**把 SKILL.md 写爆。
6. 缺 catalog 条目视为任务未完成。
7. 用户报 Auth 后续失败 / token 未传 / CLI 与 UI 不一致时：按 [`reference.md`](./reference.md)「症状 → 自动处置」改生成器并 **PushSteps**；是否 SyncCheck/Run **先问用户**，勿擅自跑。
8. **P1/多场景编排**：默认按 [`reference.md`](./reference.md)「场景内分组」用嵌套 `Folder`→`group`；横切步骤嵌进主链路，勿单开「发起支付/async」类分组。
9. **场景 description**：新建/大改生成器须实现 `BuildScenarioDescription()`（或等价），写入变量关系与金额公式；Push 后在 Apifox UI 能直接读懂换测改哪些变量。
10. **字段级/按用例生成**：先交 E2E 清单待确认 → 再骨架 → 再字段对照表；`待确认` 不做硬断言；带猜测硬断言的版本禁止 Push（见 reference「字段级用例 → E2E」）。
11. **用户问「这个 Group 改哪些环境变量」**：勿让用户猜 Environment 整表。按 reference「换测 Environment：Group 变量定位与控制台短提示」——先给短表（仅本 Group 差分键）；播报只打 Console、短行、默认只列差分键（`announce_only_keys`）；禁止用多条长 `assertInfo` 刷断言面板。改完 Generate + `PushSteps`（或 SyncCheck）。
12. **选了数据集选行**：生成器须导出 `apifox-dataset-business-ascii.csv` + `scenario-group-map.md`（中文 Group↔name）；种子优先读数据集行；鉴权三列仍独立（勿混进业务数据集）。
13. **「勾了数据集却不是那行」**：按 [`reference.md`](./reference.md)「变量供给 A · 实现约定第 5 条」与症状表自动改种子（`iterationData`→variables→env 非占位 + body 强制替换），禁止只口头解释；金样例 Membership Purchase P1。
14. **「勾了鉴权第二套 / 后续 X-Program-ID 仍是第一套」**：按 [`reference.md`](./reference.md)「鉴权选行与后续步骤 ProgramID」+ 症状表 **立即改生成器**（占位符头/体、种子优先级含 Environment、四作用域持久化、禁止 `_fb` 盖选行），`PushSteps`；勿只口头解释。复验：**先 Auth 再业务 Group**。
15. **「业务 body 多了 clientId/secret / 这两个参数不要传」**：按 [`reference.md`](./reference.md)「业务 body 误带 clientId/secret」**立即改生成器**（仅 Auth body 才 JSON 覆盖鉴权字段；扫全仓库同类注入），`PushSteps`；勿只改 Apifox UI。复验：业务「实际请求」无该双字段。
16. **「`301.000.001` / X-Request-ID invalid / curl 头 `X-Request-ID;`」**：按 [`reference.md`](./reference.md)「空 X-Request-ID → 301.000.001」**立即改生成器**（挂 `Lines_EnsureRequestIdHeader` / `JsExpr_FreshRequestId`；扫同类未挂载套件），`PushSteps`；勿只让用户手填 UUID。复验：实际请求头有合法 UUID。
17. **「只见 hu-HU / 只跑一个语种 / forEach 多轮 language 不变」**：按 [`reference.md`](./reference.md) 症状表（语种钳死）+ [`suites/resource_details_scan_langdyn.md`](./suites/resource_details_scan_langdyn.md)**立即改生成器**（Auth 清零 `scanLangIterM*`、禁钳末项、URL 改写用本轮语种）→ `PushSteps`；勿只改 Environment/口头解释。复验：3 语冒烟 LIST 出现 `en-US`/`ja-JP`/…。
18. **「全是 Auth、0 GET / no accessToken / 数据集 404」**：先对 `suites.yaml`↔场景 `useDataSetId`↔UI「数据 N」；失效 ID 立刻改正本并 Push；Auth 加凭据/空 token 日志。勿先改 `scanLanguages`。
19. **「prebookingDate 写死 / 实际请求过期日期 / 各 Group 同一天」**：按 [`reference.md`](./reference.md)「预预约 prebookingDate」改生成器（`PrebookingDateApifoxExpr` + `AllocatePrebookingAddDays` / `Lines_SyncPrebookingDate`）后 Push；勿只改 Body 表达式或让用户手填日期。
20. **「Headers 参数值为空 / 已关联接口文档 / 要解绑 / 手动解绑能共存 / 解绑后值又没了 / 前端改入参就报错 / 希望 UI 改参调试 / curl `X-Program-ID;` `Authorization;` / 业务步 `201.000.001 invalid secret`」**：**立即**按 [`reference.md`](./reference.md)「场景 Headers 参数值为空」补 yaml 两字段并 `PushSteps`。**同时扫** `suites.yaml` 全部资产，缺两字段的一并补+Push，勿只修当前场景。禁止当成 Body 非法或 Auth secret 填错；禁止口头说「解绑和参数值互斥」、禁止再试 Postman `key`、禁止只清 `bind` 留 `type=http`。用户已手动解绑时先 GET 对照该步。改完让用户关掉场景标签再看。UI 调试：只改 Body、勿清空 Headers、单步先跑 Auth。
21. **「每步前置/后置脚本雷同 / 断言面板字太多 / Push 422001 / helpers 撑包」**：按 [`reference.md`](./reference.md)「多步 helpers」——Auth 写入 `*HelpersSource`，业务步只 loader；**新建多步套件默认如此**，禁止再每步内联完整 helpers。改完 Generate + `PushSteps`。
22. **调试/排障结束后**：按 [`reference.md`](./reference.md)「调试收尾」**自动删除**本轮草稿纸（`_tmp_*`、无引用一次性脚本、dump）；勿等用户说「帮我删」。结论只留生成器 / yaml / Skill。
23. **「后续 search/列表不是注册返回的 membershipId/clientUserId」**：按 [`reference.md`](./reference.md)「注册后 runtime ID 被 Environment / OAS 样例盖掉」**立即改生成器**（公共 `forceCaptured`；`users/memberships` 不传 `status`），`PushSteps`；勿让用户手填 Environment。复验：实际请求 ID 与注册响应一致。

## 新建资产检查清单

- [ ] **已向用户确认**场景目录（L1/L2/L3），并写入 `suites/<asset>.md`  
- [ ] **已向用户确认**变量供给方式（A 数据集选行 / B Environment）；>5 Group 已推荐 A  
- [ ] **（按用例时）已确认正向 E2E 清单**（步骤序 + 追溯）；Folder 内顺序与确认一致  
- [ ] **（按用例时）字段断言对照表**无漏项；无「已硬断言但仍待确认」  
- [ ] 生成器含 Tests + `PurposeName` + 清晰断言 helpers  
- [ ] **场景 `info.description` 含变量关系**（生成源 / 链路 / 变量→期望公式；见 reference「场景 description」）  
- [ ] **（选 A 时）** 已导出 `apifox-dataset-business-ascii.csv` + `scenario-group-map.md`；种子优先数据集行；鉴权不进业务数据集  
- [ ] **SyncCheck/Run 前已问用户**：是否现在跑、鉴权数据集、业务 CSV 是否已导入勾选、Environment；未同意不得擅自跑  
- [ ] **鉴权**：Auth body/头与 Bearer `X-Program-ID` 均为 `{{ProgramID}}`/`{{clientId}}`/`{{secret}}`；种子含 Environment 优先于 `.env` 回落；选中值写 variables/collection/env/globals；**禁止**种子对业务 JSON body 无条件写入 `clientId`/`secret`（仅 Auth body 可覆盖）  
- [ ] **X-Request-ID**：每步前置挂 `collection_builder_common.Lines_EnsureRequestIdHeader`（自有 `RequestItem`/`EnsureAuth` 须显式拼接；勿只靠头里 `{{$guid}}`）；`pm.sendRequest` 回退头用 `JsExpr_FreshRequestId`  
- [ ] **Headers（不得省略）**：`suites.yaml` 该 key **必写** `push_mode: http` + `unbind_after_push: true`；`suites/<asset>.md` 同步写一行 Push；解绑对齐 UI（`sampleValue` + 相对 path）；Push 后关掉场景标签再验「已解绑且参数值可见」，允许用户只改 Body 调试  
- [ ] **helpers**：Auth 写入 `*HelpersSource`；业务步仅 eval loader + 本步造数/断言；payment 断言只挂 Preview/Create/Detail  
- [ ] `suites.yaml` 已填 ID，复用 `ai/apifox-cli-sync`  
- [ ] 场景已挂到约定 `folderId`（非根目录孤儿）  
- [ ] `SyncCheck` 通过  
- [ ] `catalog.md` 有对应行  
- [ ] （建议）`suites/<asset>.md` 记录可复用坑  
- [ ] P1 多场景：已按业务主轴二级分组；横切能力已嵌进链路（见 reference「场景内分组」）  
- [ ] **调试草稿已删**：无 `tools/_tmp_*`、无本轮 dump；一次性脚本未留在 `tools/`  
