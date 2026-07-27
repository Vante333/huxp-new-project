# Apifox CLI · Repo-first 问题回顾（便于后续对照）

> 记录试点落地与长期化改造中遇到的问题、危害与处理结论。  
> 日常用法见：[小白入门](./Apifox-CLI-小白入门流程.md) · [协作指南](./Apifox-CLI-Repo-First-协作指南.md)（含 **§15 团队推广**）  
> 日期：2026-07-19 起；**2026-07-27** 追加 §13（字段级用例 → E2E / 断言防漏）

---

## 1. 目标与背景

要把 **Apifox CLI · Repo-first** 做成可长期用的模式：

仓库生成器为正本 → 同步到私有化 Apifox AI 分支 → 跑测分流 → catalog 登记。

| 项 | 值 |
|----|-----|
| 试点资产 | `papi_2548`（会籍 extensions） |
| 工作分支 | `ai/apifox-cli-sync`（唯一复用，禁止 `ai/日期-*`） |
| 项目 | 346275 · 私有化 `https://apifox.dragonpass.com.cn` |
| 主命令 | `.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <key>` |

---

## 2. 协作 / 认知类问题

| 问题 | 表现 | 处理 |
|------|------|------|
| 文档偏术语、不好懂 | 新人看不懂「真相源 / SyncCheck」 | 写大白话版[小白入门](./Apifox-CLI-小白入门流程.md)：你提需求 → AI 改正本并同步 → 你去 Apifox 验收 |
| 目录只列路径不够 | 不知道每个文件干啥 | 协作指南 + 小白文档补**逐文件**说明 |
| 误以为人手改代码/敲命令 | 实际第 1、2 步是 AI 做 | 文档改成「解释 AI 在干啥」，人只验收 |

---

## 3. 不利于长期维护（核心坑）

### 3.1 每需求一套 triage / 自动改生成器

- **问题**：曾有 `TriageApifoxPapi2548Failures.py`，混了「读报告 / 按步骤名猜脚本问题 / **自动给生成器打补丁**」。
- **危害**：扩资产会复制脚本；运行时改正本，难评审、难追溯。
- **处理**：
  - 通用 `tools/TriageApifoxRunFailures.py`
  - 规则可选：`suites.yaml` → `triage.script_name_patterns`
  - **禁止** triage 改生成器；过期 pattern **清空**（默认失败全进 leftover）
  - 删除需求级 triage 文件

### 3.2 路径 / ID 写死在 `ApifoxRepoFirst.ps1`

- **问题**：`Get-AssetPaths` 一度只认 `papi_2548`，扩资产还要改脚本。
- **处理**：从 `.apifox/suites.yaml` → `assets.<key>` 驱动；共享解析 `tools/ApifoxSuitesYaml.py`。

### 3.3 「多资产未就绪」的残留硬编码

| 问题 | 危害 | 处理 |
|------|------|------|
| Push 场景名写死 2548 | 新资产推上去名字错 | `--scenario-name` + 包内名称 |
| Run 报告前缀固定 `papi2548-` | 多资产报告混在一起 | `<asset>-时间戳`，目录 `apifox-reports/<asset>/` |
| Sync / PushSteps 不校验 ScenarioId=0 | 可能对无效 ID 调 CLI | 全链路 `Assert-ScenarioIdConfigured` |
| Catalog 详解特判 `papi_2548`，不读 yaml `doc` | 新资产 upsert 链接不全 | Upsert 读 `doc` |
| 三套手写 YAML 解析 | 行为不一致 | 统一 `ApifoxSuitesYaml.py` |
| `last/leftover-failures.md` 全局同名 | 多资产互踩 | 按资产分目录 |
| 文档写 ai-branches「脚本维护」 | 实际无读写 | 标明「不读写 / 非真相」 |
| Skill reference 堆 2548 业务细节 | 易被当成全局规范 | 业务坑下沉 `suites/papi_2548.md` |

### 3.4 中间文件过多、与正本平铺混放

- **问题**：每次 SyncCheck / Generate 会产出多种文件，原先全堆在 `postman/` 根下：
  - 正本 `Generate*.py`
  - 可审集合 `*.postman_collection.json`
  - 流水线中间件 `*.apifox-2.7.43-import.json`、`*.openapi.json`
  - 环境模板、协作 md、报告碎片混在一起
- **危害**：
  - Explorer / PR 噪音大，难一眼分清「该改什么 / 别碰什么」
  - 新人易手改 JSON「打印件」，下次 Generate / SyncCheck 被盖掉
  - 中间件进 Git 体积大（单包可达数百 KB～数 MB），审 diff 价值低
- **处理（长期维护选型）**：
  1. **目录按角色拆开**（`postman/`）  
     `generators/`（正本）· `collections/`（可审）· `envs/` · `docs/` · `generated/`（本地中间件，gitignore）
  2. **正本唯一真相** · 只改 `generators/Generate*.py`（及 helpers）
  3. **集合可审** · `collections/*.postman_collection.json` 仍提交，便于 PR 看步骤/断言变化
  4. **中间件可丢**  
     - CLI：`suites.yaml` 省略 `apifox_package` / `openapi_bridge` → 默认写到 `apifox-reports/<asset>/generated/`（已 gitignore）  
     - Local Offer 等本地 Apifox 包 → `postman/generated/`（gitignore）  
     - PushSteps / SyncCheck **现生成**，勿当正本、勿手改
  5. 生成器统一经 `collection_builder_common.CollectionPath` / `EnvPath` / `GeneratedArtifactPath` 写出，避免再写回平铺路径
- **文档同步注意**：搬目录后须改 `suites.yaml`、Skill/catalog、协作指南/小白入门，以及 `docs/` 内相对链接（`../generators/`、`../collections/`）；历史金样例 `2026Q2_SP1/postman/` 可保留旧布局作对照。

---

## 4. 私有化 Apifox 环境约束（一直要记住）

- `import postman` 常失败；openapi 无 Tests；apifox 导入场景常 `steps=[]`
- 可靠写法：AI 分支 + `test-scenario update`（`customHttp` + 后置脚本）
- 主分支常不可外部 AI 直写 → 统一写 `ai/apifox-cli-sync`，合 main 用客户端
- **禁止**每人一条 `ai/日期-*` 分支

---

## 5. 当前约定（回顾时对照）

1. **正本** = `postman/generators/GeneratePostmanCollection*.py`（及 helpers），不是 Apifox UI  
2. **可审集合** = `postman/collections/*.postman_collection.json`（提交；勿手改当唯一真相）  
3. **中间件可丢** = CLI 用 `apifox-reports/<asset>/generated/`；本地 Apifox 包用 `postman/generated/`（均 gitignore）  
4. **验收** = `SyncCheck`；UI 手改不算数  
5. **分支** = yaml 里 `working_branch`（缺了要报错，不静默回落）  
6. **失败** = 默认 leftover → 人/AI 改正本 → 再 SyncCheck；不靠运行时打补丁  
7. **扩资产** = 只加 `suites.yaml` 一段 + SyncCheck，不新建 `TriageApifoxXxx.py`  
8. **报告** = `apifox-reports/<asset>/`（gitignore）  
9. **解析** = `tools/ApifoxSuitesYaml.py` 一处共用  
10. **项目 ID / Base URL** = .apifox/settings.json 权威；suites 顶层同名字段仅对照  
11. **字段级驱动** = 先确认正向 E2E → 对照表 → 不清先问 → 再硬断言/Push（Skill #12/#13；见 §13）  
12. **场景 description** = 写清变量关系与金额公式（Skill #11）  

---

## 6. 仍需靠纪律、工具拦不住的

- UI 只改不同步  
- 生成器与 pytest 断言漂移  
- 私有化 CLI 升级后行为变化  
- 漏传 -Asset 时默认落到 papi_2548（可选再加强制显式）  
- cli_import_format 与命令行 -ImportFormat 优先级：当前 yaml 有值时优先生效  
- 新生成器若仍写 Path(__file__).parent / OUT_NAME（未用 CollectionPath），会把 JSON 又写回 generators/，破坏按角色落盘  
- 搬目录后文档/链接漏改 → 新人按旧路径找不到文件（改完目录应用 grep 扫一遍旧路径）  
- **按用例生成时跳过 E2E 确认 / 猜断言语义** → 漏字段、假绿假红（纪律见 §13；Skill 已硬约束，仍靠人确认清单）  

---

## 7. 快捷入口

| 路径 | 用途 |
|------|------|
| [Apifox-CLI-小白入门流程.md](./Apifox-CLI-小白入门流程.md) | 大白话流程 + 文件说明 |
| [Apifox-CLI-Repo-First-协作指南.md](./Apifox-CLI-Repo-First-协作指南.md) | 规范、红线、§6.4 字段级、**§15 团队推广** |
| [PAPI-2548-apifox-cli-repo-first.md](./PAPI-2548-apifox-cli-repo-first.md) | 2548 试点专页 |
| .cursor/skills/apifox-cli-repo-first/ | Agent：SKILL / reference（含「字段级用例 → E2E」）/ catalog / suites |
| .apifox/suites.yaml + settings.json | 资产映射与项目连接 |
| scripts/ApifoxRepoFirst.ps1 | 团队主入口 |
| 本文 **§13** | 字段级 E2E / 断言防漏 / Push 规则（membership_purchase_p0） |

`powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548
`

---

## 8. 一句话

**早期最大坑是「每需求特判 + 运行时改生成器 + 写死 2548」；已改成 yaml 驱动 + 通用工具 + leftover 改正本。**  
**第二类坑是「中间文件与正本平铺混放」；已按角色拆目录 + 集合可审、中间件可丢。**  
**第三类坑是「按字段级用例生成时：未先确认 E2E、P0 擅自砍字段、语义猜测硬断言」；已写入 Skill #12/#13 + 协作指南 §6.4/§15，见本文 §13。**  
后续维护成本取决于是否坚持：**generators/ 正本 + SyncCheck + 唯一 AI 分支 + 不手改打印件 + E2E/对照表先确认**。

---

## 9. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-07-19 | 首版：汇总协作文档、triage 抽取、多资产硬编码清理与长期红线 |
| 2026-07-19 | 追加 §3.4：中间文件过多 / 平铺混放；落地按角色目录 + CLI 中间件进 pifox-reports/<asset>/generated/；更新 §5/§6/§8 约定 |
| 2026-07-19 | 追加 §10：鉴权三列 / accessToken 传递 / 多环境 / canary DELETE；Agent 自动处置见 Skill 
eference.md「症状→自动处置」 |
| 2026-07-21 | 追加 §11：预预约 Payment（人数统一 / token / 802 / 取消文案 / 去 Setup / 冲突 msg）；通识见品类扩展指南 §9 |
| 2026-07-21 | 追加 §12：ePass P1（无预收款 / status=9 标题 / Bundle 取消 / ePassId 占位覆盖 / membership token / 缺参只验 msg） |
| 2026-07-27 | 追加 **§13**：字段级用例 → E2E / 断言防漏 / 不清先问 / Push 规则；同步 §5/§6/§7/§8；试点 membership_purchase_p0 |
## 10. 本轮联调坑（鉴权 · 令牌 · 多环境 · canary）

便于下次 Agent **对症状表自动改生成器 + SyncCheck**，不必再口头排查一轮。

| # | 问题 | 表现 | 处理结论 |
|---|------|------|----------|
| 1 | 鉴权列名不统一 | `programId` / `clientSecret` / 空 `ProgramID` → Auth 或后续 `201.000.001` | 数据集**仅** `ProgramID`、`clientId`、`secret`；凭据放 `use_data_set_id`，勿依赖 environment get |
| 2 | 令牌「看起来传了」实际未用上 | Auth 200；R01 起大量失败；头有 Bearer 但 `code:-1` | 空 `accessToken`（数据集列或集合变量）盖掉 Auth；场景下 collection 不持久。须多作用域写入 + 前置强制 Authorization；**禁止** `dpAccessToken` 旁路名 |
| 3 | CLI 绿、UI 红 | 同一场景名两边结果不一致 | UI 必须 `ai/apifox-cli-sync` 并刷新；以最新 SyncCheck 报告为准 |
| 4 | 多环境 | 换环境 baseUrl/x-version 不对 | 环境变量放 Environment；集合留空；`environment_id` / `-EnvironmentId` |
| 5 | canary DELETE | U03/U05/E3 期望删净、实际仍在 | `allowCanaryDeleteNoop` 软跳过，勿改业务预期硬对齐 canary |

**Agent 入口**：[`.cursor/skills/apifox-cli-repo-first/reference.md`](../../../../.cursor/skills/apifox-cli-repo-first/reference.md) →「症状 → 自动处置」。

---

## 11. 预预约 Payment 联调坑（人数 · token · 802 · 取消 · Setup）

| 项 | 值 |
|----|-----|
| 日期 | 2026-07-21 |
| 首发资产 | `ft_membership_payment_p1`（场景 366261） |
| 正本 | `generators/ft_prebooking_payment_common.py`、`ft_prebooking_payment_p1_gaps.py` |
| 通识（下次优先） | [`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md) **§9 排障速查** |
| 资产笔记 | [`suites/ft_membership_payment_p1.md`](../../../../.cursor/skills/apifox-cli-repo-first/suites/ft_membership_payment_p1.md) |

| # | 问题 | 表现 | 处理结论 |
|---|------|------|----------|
| 1 | 取消失败文案 | status=9 不可取消时未钉死英文 msg | 断言 `Order cancellation failed. Please try again later.`；无 `usageOrderId` 时勿硬套 |
| 2 | 预约人数不统一 | 现金点 1 → `adultCount=1`、乘客仅 1 人 | **可用性/预约统一 3 人**；点数只改 `toUseEntitlement*`；纯权益勿「1 点约 3 人」（`500.051.011`） |
| 3 | 冲突断言偏软 | 只验 `code=-1` | `500.051.023` + conflict 固定 msg |
| 4 | 802 可跳过 | 断言标题含「或跳过」、`code=0` soft pass | `payableAmount=0`/无字段 → **必须** `500.000.802` |
| 5 | 多余 Setup | 顶层 `01 Setup` 与链路内注册重复 | 去掉 Setup；Auth + 链路内 refresh |
| 6 | Preview 无 token | 可用性有 `prebookingToken`，后续仍空/`{{prebookingToken}}` | **根因加深**：空集合变量 + body 占位符被 `replaceIn` 洗空；`SetVar(GetVar)` 可能冲空。处置：去掉空 CollectionVariable；body 预置 `""`；`ftSavePrebookingToken`（test 外写入）；`Prerequest_InjectPrebookingToken` 硬注入 |
| 7 | 权益不足假绿 | Preview/Create 得 `500.051.004` Invalid prebookingToken，断言软跳过仍绿 | **不是**单纯 token 传递问题：`avail+1` 超姓名池 → AVL 跳过无 token 仍打 Preview。造数：`POST /v2/entitlements/update`（`quantity` 负、`usageRestriction` 1持卡/2guest/3共享）减到可测；链路 `MS→DEC→AVL→PRE→CRT`；断言接受 `500.042.011`/`500.051.011`/`500.051.020`，**硬失败** `500.051.004`；无法造数才 `skipRequest` |
| 8 | Push `ECONNRESET` / `422001` | 大包更新偶发断连；helpers 膨胀易 422；**单步 post ≳62KB** 亦 422 | 重试 `PushSteps`；helpers 增量须极小；Preview 不挂 PaymentExtraConsistency（Create/Detail 才挂） |
| 9 | Run 全绿脚本仍 exit 1 | `apifox run` 非 0 污染 `$LASTEXITCODE`；或 Merge 抬高脏 `failed` | 以 `*-failures.json` 空列表 + CLI 断言表为准；`SummarizeApifoxRunFailures` / `ApifoxRepoFirst` 已修：分离 failures 为空则 `failed=0`，显式捕获 python exit |

**验收**：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_membership_payment_p1`（共用 common 的品类资产按需同步）。

---

## 12. ePass Prebooking Payment P1 联调坑（无预收款 · status=9 · 占位覆盖 · 缺参 msg）

| 项 | 值 |
|----|-----|
| 日期 | 2026-07-21 |
| 首发资产 | `ft_epass_payment_p1`（场景 366263）；同步 Push：`ft_membership_payment_p1`、`lounge_*_payment_p1` |
| 正本 | 同 §11（`ft_prebooking_payment_common.py`、`ft_prebooking_payment_p1_gaps.py`） |
| 通识（下次优先） | [`Prebooking-Payment-品类扩展指南.md`](./Prebooking-Payment-品类扩展指南.md) **§9.1 #10–#15**、**§9.3** |
| Agent 入口 | Skill [`reference.md`](../../../../.cursor/skills/apifox-cli-repo-first/reference.md)「症状 → 自动处置」ePass 行 |
| 资产笔记 | [`suites/ft_epass_payment_p1.md`](../../../../.cursor/skills/apifox-cli-repo-first/suites/ft_epass_payment_p1.md) |

| # | 问题 | 表现 | 处理结论 |
|---|------|------|----------|
| 1 | ePass 无客户预收款 | `CLIENT_COLLECT` / Bundle 预收款当正向；body 含 `cashPaymentApplied:true`；**支付链接 0 元 802 Preview 误用 CLIENT_COLLECT → 051.023** | **一律 conflict msg**；勿传 `cashPaymentApplied`；现金仅 `DP_COLLECT`+`toUseUsageCount`；**PAYLNK 802** 改纯权益足额（payable=0→802 / 有费→REDIRECT） |
| 2 | status 断言撒谎 | 标题「1 或 5」，实际 `status=9` 仍绿 | 允许 `[1,5,9]`；禁止 `st===9` 静默 return |
| 3 | Bundle 取消无文案 | 取消步只「可解析」；status=9 看不到取消失败 msg | `ftPayAssertCancelUsageResponse` |
| 4 | ePassId 负向假造数 | 「空」「不一致」请求体被换成真 ID | placeholders **仅占位符**才注入 ePassId |
| 5 | membership token 用例假造数 | 写死假 token 字符串 | `MS(复用 clientUserId)→membership AVL→ePass Preview` |
| 6 | 缺/空必填 errCode 红 | `302.000.001` vs `302.051.001` | **只验固定 msg** + `code=-1`；改 common 后 Push 全套 P1 |

**验收**：`.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset ft_epass_payment_p1`（缺参助手变更时一并 Push Membership/Lounge P1）。

---

## 13. 字段级用例 → E2E / 断言防漏（2026-07-27）

| 项 | 值 |
|----|-----|
| 日期 | 2026-07-27 |
| 触发试点 | `membership_purchase_p0`（场景 366587 · 首次会籍购买） |
| 正本 | `generators/GeneratePostmanCollectionMembershipPurchaseP0.py` |
| Agent 规范 | Skill 硬约束 **#11–#13**；[`reference.md`「字段级用例 → E2E」](../../../../.cursor/skills/apifox-cli-repo-first/reference.md#字段级用例--e2e防漏断言--防猜错) |
| 协作文档 | [协作指南 §6.4](./Apifox-CLI-Repo-First-协作指南.md) · [§15 团队推广](./Apifox-CLI-Repo-First-协作指南.md#15-团队推广如何落地到小组) |
| 资产笔记 | [`suites/membership_purchase_p0.md`](../../../../.cursor/skills/apifox-cli-repo-first/suites/membership_purchase_p0.md) |

### 13.1 遇到的问题（危害）

| # | 问题 | 表现 | 危害 |
|---|------|------|------|
| 1 | 未先确认正向 E2E | 直接按「冒烟」拼步骤；Cancel 另开「商品B-取链后取消」与原 E2E 重复 | 步骤序与用例意图不一致；分组膨胀 |
| 2 | P0 擅自砍字段断言 | Create 只有 orderId/status/价格；缺 `orderCreatedDate` / `orderCancelledDate` / `extra.appId` / `profile` 等 | 字段级用例覆盖不足；靠截图事后补洞 |
| 3 | 断言语义猜测 | 「description 为 couponName」写成响应对等，或误断言 description=null | 假绿/假红；多轮 Push 返工 |
| 4 | 金额期望来源摇摆 | `deductionAmount` 一度写死 0，后又改公式 `original−payable` | 与用例公式不一致 |
| 5 | 场景说明过简 | description 只有「P0 冒烟」一句 | 换测不知道改哪个 Environment 变量 |
| 6 | Environment / baseUrl | Push 强制 `{{baseUrl}}+path`；空 Environment 不解析 | 整链失败（需可用环境如 351893） |
| 7 | 鉴权注入 | 私有化 Environment CLI 写变量常不生效 | 改用 `.env` 的 `MP_P0_*` 生成时注入 |

### 13.2 处理结论（以后按此自动执行）

**生成前**

1. 从字段级用例抽出**正向 E2E 清单**（场景名、步骤序、METHOD/path、追溯 `tc-p*`）。  
2. **等用户确认后再**按该顺序生成 Folder 内接口。  
3. P0 **只减场景条数**，不打乱已确认步骤序；Cancel/支付等横切**嵌进原 E2E**，禁止擅自另开重复「仅取消」分组（除非用户明确要求）。

**断言**

4. P0 **不砍**单条用例里的 rc 字段断言。  
5. 落硬断言前维护对照表：`检查点 → 期望来源 → 步骤 → 已确认|待确认|砍掉(需同意)`。  
6. 语义不清（env？响应对等？写死？公式？）**先问用户**；未确认不做硬断言（可省略或 `assertInfo`）。  
7. 金额类优先写**公式**（例：`deductionAmount = originalAmount − payableAmount`）；名称类用 Environment（例：`CouponIntroValidName` → `details.description` / `couponName`）。

**Push**

8. 主路径已确认、歧义字段未硬断言 → **允许 Push**，交付列出待确认项。  
9. 含**猜测硬断言**的版本 → **禁止 Push**。  
10. 仅当主路径本身也不清 → 整包阻塞。

**场景说明**

11. `info.description` 须含生成源、链路、变量→期望映射与金额公式（对齐 FT payment 风格）。

### 13.3 推荐口令（提给 Agent）

> 先列正向 E2E 清单等我确认；再按确认顺序生成接口。按字段级用例补齐断言，P0 不砍字段；先出对照表；不清先问；未确认不做硬断言再 Push。场景 description 写清变量关系。

### 13.4 试点已落地要点（membership_purchase_p0）

| 项 | 结论 |
|----|------|
| E2E | 商品 B / 商品 A 均为 `Preview→Create→Details→Payments→Details→Cancel→Details` |
| `deductionAmount`（商品 A） | `productAPrice − productAPayableAmount` |
| coupon 四字段 | `couponType=4`；`description`/`couponName` ← `CouponIntroValidName`；`currency`/`discount` = null |
| Create 元数据 | `orderCreatedDate` UTC+0；`orderCancelledDate=null`；`extra.appId/profile` 回显 |
| 目录 | `membership/P0(冒烟用例)/others`（folderId 350026） |

**验收**：`.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset membership_purchase_p0`（Environment 须可解析 `baseUrl`；券名填 `CouponIntroValidName`）。
