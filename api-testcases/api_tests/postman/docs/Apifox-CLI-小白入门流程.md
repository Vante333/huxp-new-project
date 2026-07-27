# 这套东西到底怎么用（大白话版）

别被 CLI、分支这些词吓到。日常分工很简单：

1. **你跟 AI 说要改啥**（加步骤、改检查、修失败……）  
2. **AI 去改代码、同步到 Apifox、顺带跑一遍**  
3. **你打开 Apifox 看结果**（注意选对那个粉色分支）

你不用自己翻 Python、也不用记命令。知道「背后在干啥、你去哪验收」就够了。  
正式规范另有文档：[协作指南](./Apifox-CLI-Repo-First-协作指南.md)。

---

## 先搞懂一件事

我们写自动化，其实是在告诉电脑：  
「先调这个接口，再调那个，回来的结果要对不对。」

以前有人直接在 Apifox 里改脚本——改完自己清楚，别人难审，也容易丢。  
所以现在约定：**以仓库里的代码为准**。  
Apifox 只是用来「点一点、看一看、跑一跑」的界面。

你可以记成：

> **代码是正本，Apifox 是副本。**  
> AI 改正本并同步；你别只在副本里手改。

---

## 实际怎么走（你 + AI）

### 第 1 步：AI 改代码（你只提需求）

你在 Cursor 里说清楚要啥就行，例如：  
「给 2548 加一步某某检查」「某条断言太松了，改严一点」。

AI 会去改仓库里的**正本**（生成脚本、相关 helpers 等）。  
这一步在干啥：**把用例步骤、请求、检查规则写进代码**，以后可评审、可追溯，不会只活在网页上。

你一般不用自己打开那个 `.py` 文件。

### 第 2 步：AI 同步并试跑（你等结果）

改完后，AI 会跑一套自动流程（内部叫 `SyncCheck`），大致是：

- 按代码重新生成整套接口步骤  
- 推到 Apifox 的专用分支 `ai/apifox-cli-sync`  
- 自动跑一遍，看看通不通  
- 若是脚本写错了，尽量先修再推再跑  
- 成功了还会登记一下，方便后人抄

这一步在干啥：**把正本印成副本，并试考一遍**。  
你不用自己敲命令；若 AI 说还有 leftover 失败，把说明丢给熟手或继续让 AI 修。

### 第 3 步：你去 Apifox 验收（这步主要是人做）

打开公司 Apifox，进对应项目。

**特别重要：左上角把分支切成 `ai/apifox-cli-sync`。**  
若还停在 main，你可能看到的是旧的，会以为「AI 白干了」。

然后进自动化测试，找到类似 `PAPI-2548 … CLI sync` 的场景，点开步骤。  
名字一般是中文开头的，比如「【鉴权获取访问令牌】…」。  
点运行，再点某一步的断言，能看到「期望是啥、实际是啥」——不用读代码也能核对。

---

## 第一次上手：环境准备（通常装一次就行）

这些多半是熟手 / AI 帮你弄好；你知道有这么回事即可：

1. 仓库在本机，Cursor 能打开。  
2. 装好 Python、Node、`apifox-cli`。  
3. 仓库根目录 `.env` 里有 `APIFOX_ACCESS_TOKEN`（私人钥匙，**不要提交到 Git**）。  
4. 登录能通（`WhoAmI` 一类检查，一般也是 AI/熟手确认）。

你日常只要会：**跟 AI 提需求 → 去 Apifox 切分支看结果**。

数据集里鉴权相关列名团队已统一，以后只认这三个：`ProgramID`、`clientId`、`secret`（别写成 programId / clientSecret）。

---

## 就记这些就够了

| 谁 | 干啥 |
|----|------|
| 你 | 说清楚要改/要验什么；去 Apifox 验收 |
| AI | 改正本代码；同步到 Apifox；试跑；能修的先修 |
| Apifox | 给人看步骤、看「期望 / 实际」、再点一次跑 |

---

## 每个文件干什么（先别背表）

日常你只需要知道下面 4 件事；其它文件由 AI 使用，不必记。

| 你要知道的 | 在哪 | 做什么 |
|------------|------|--------|
| **正本** | `postman/generators/Generate*.py` | 步骤和断言写在这里；改自动化改这里（一般让 AI 改） |
| **验收界面** | Apifox → 分支 `ai/apifox-cli-sync` | 点运行、看断言「期望 / 实际」 |
| **资产对照** | `.apifox/suites.yaml` | 某套用例对应哪个场景 ID、环境、生成器（扩新需求时熟手/AI 改） |
| **登录凭据** | 仓库根 `.env` 的 `APIFOX_ACCESS_TOKEN` | 让本机 CLI 能登录公司 Apifox；**勿提交 Git** |

主命令（一般由 AI 执行）：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <资产名>
```

### 其它路径（需要时再查）

#### `scripts/ApifoxRepoFirst.ps1`

仓库根下 PowerShell 入口。常用 `-Action`：

| Action | 做什么 |
|--------|--------|
| `WhoAmI` | 检查能否登录私有化 Apifox |
| `Generate` | 只跑生成器，写出 `collections/` 里的 JSON |
| `PushSteps` | 生成 → 转包 → 把步骤+Tests 推到 Apifox 场景 |
| `Run` | 在指定环境跑场景，写出失败报告 |
| `SyncCheck` | Generate + Push + Run + 失败分流；成功则更新 catalog |

资产名用 `-Asset`（如 `membership_purchase_p0`），从 `.apifox/suites.yaml` 读路径与场景 ID。

#### `tools/`（被 `ApifoxRepoFirst.ps1` 调用；一般不用手跑）

| 文件 | 做什么 |
|------|--------|
| `ApifoxSuitesYaml.py` | 解析 `.apifox/suites.yaml`（场景 ID、生成器路径、环境等） |
| `ConvertPostmanToApifoxScenario.py` | 把 Postman 集合转成带 Tests 的 Apifox 场景包 |
| `PushApifoxScenarioSteps.py` | 调用 CLI，把包写入指定场景（`customHttp` + 后置脚本） |
| `SummarizeApifoxRunFailures.py` | 从本次 run 报告抽出失败步骤与原因 |
| `TriageApifoxRunFailures.py` | 按规则把失败分成「像脚本问题」/「留给人」；**不改生成器** |
| `UpsertApifoxCliCatalog.py` | SyncCheck 成功后，更新 Skill 里的 `catalog.md` 一行 |
| `apifox_payment_assert_*.js` 等 | 预预约 payment 等业务断言片段，由生成器内联进 Tests；新人可忽略 |

#### `postman/`（集合与文档）

| 路径 | 做什么 |
|------|--------|
| `generators/Generate*.py` | **正本**：步骤顺序、请求体、断言脚本都在这 |
| `generators/collection_builder_common.py` 等 | 生成器公共工具（路径、命名）；跟具体业务生成器一起改 |
| `collections/*.postman_collection.json` | 生成器输出的集合 JSON，方便 Git/PR 对比；**不要只改 JSON 当真相** |
| `envs/` | 少量环境模板（多数跑测用 Apifox Environment，见 suites 的 `environment_id`） |
| `docs/Apifox-CLI-小白入门流程.md` | 本文 |
| `docs/Apifox-CLI-Repo-First-协作指南.md` | 团队完整规范（含推广 §15） |
| `docs/Apifox-CLI-Repo-First-问题回顾.md` | 历史坑与结论 |
| `docs/*-apifox-cli-repo-first.md` | 单个资产的详解页 |
| `generated/` | 本地临时 Apifox 包（gitignore），可删 |

#### `apifox-reports/<资产名>/`（本机，gitignore）

| 路径 | 做什么 |
|------|--------|
| `generated/*.apifox-2.7.43-import.json` | Push 用的临时场景包，现生成现用 |
| `generated/*.openapi.json` | 偶发用的 OpenAPI 桥接文件 |
| `<资产>-*-failures.json` | 某次 Run 的失败明细 |
| `last-failures.md` | 最近一次失败汇总 |
| `leftover-failures.md` | 分流后仍需人看的残留失败 |

跑挂了：优先看这里或 Apifox UI 断言面板，把截图丢回 AI。

#### `.apifox/`（项目映射，无密钥）

| 文件 | 做什么 |
|------|--------|
| `settings.json` | Apifox 项目 ID、私有化网址 |
| `suites.yaml` | 资产 key → 生成器 / collection / 场景 ID / 环境 / 工作分支 |
| `README.md` | 本目录说明 |
| `ai-branches.json` | 可选本机缓存（已忽略）；**不要当配置真相** |

#### `.cursor/skills/apifox-cli-repo-first/`（给 Cursor Agent）

| 文件 | 做什么 |
|------|--------|
| `SKILL.md` | Agent 硬约束（目录先问、E2E 先确认、对照表、Push 规则等） |
| `reference.md` | 坑位、字段级→E2E、场景 description、症状处置 |
| `catalog.md` | 已落地资产总表（场景 ID、目录、生成器链接） |
| `suites/<资产>.md` | 单资产短笔记（可复用坑） |

更细的熟手说明 → [协作指南 §8](./Apifox-CLI-Repo-First-协作指南.md#8-逐文件说明大白话)。

---

## 实例：首次会籍购买 P0（`membership_purchase_p0`）

用最近落地的一套说明「改一处 → 同步 → 验收」时各文件分别干什么。

### 这套在 Apifox 里是什么

| 项 | 值 |
|----|-----|
| 资产 key | `membership_purchase_p0` |
| 场景 | **366587** · `Membership Purchase P0 · CLI sync` |
| 目录 | `membership/P0(冒烟用例)/others` |
| 分支 | `ai/apifox-cli-sync` |
| 环境 | **351893**（须有可用 `baseUrl`） |
| 链路 | 商品 B / 商品 A：Preview→Create→Details→Payments→Details→Cancel→Details |

### 文件对照（按一次改断言/同步的路径）

| 文件 | 在这套里做什么 |
|------|----------------|
| `.env`（仓库根，勿提交） | 放 `APIFOX_ACCESS_TOKEN`；本套鉴权另用 `MP_P0_PROGRAM_ID` / `MP_P0_CLIENT_ID` / `MP_P0_SECRET`，生成时注入请求 |
| `.apifox/settings.json` | 固定项目 346275、私有化网址 |
| `.apifox/suites.yaml` → `membership_purchase_p0` | 登记：生成器路径、collection、场景 ID **366587**、环境 **351893**、分支、目录 folderId |
| `postman/generators/GeneratePostmanCollectionMembershipPurchaseP0.py` | **正本**：商品 A/B 步骤、断言、`BuildScenarioDescription()`、默认业务变量 |
| `postman/collections/Membership-Purchase-P0.postman_collection.json` | 跑生成器后写出的集合；PR 可看 diff；不要只改它 |
| `scripts/ApifoxRepoFirst.ps1` | 例如：` -Action PushSteps -Asset membership_purchase_p0` |
| `tools/ApifoxSuitesYaml.py` | 读出上面 yaml 里本资产的路径与 ID |
| `tools/ConvertPostmanToApifoxScenario.py` | 把 collection 转成带 Tests 的 Apifox 包 |
| `tools/PushApifoxScenarioSteps.py` | 把包推到场景 366587（分支 `ai/apifox-cli-sync`） |
| `apifox-reports/membership_purchase_p0/generated/…apifox-….json` | 本次 Push 的临时包（可删） |
| `apifox-reports/membership_purchase_p0/*-failures.json` 等 | 若跑 `SyncCheck`/`Run`，失败明细写这里 |
| `tools/SummarizeApifoxRunFailures.py` / `TriageApifoxRunFailures.py` | 汇总失败、分流 leftover（SyncCheck 时自动调） |
| `tools/UpsertApifoxCliCatalog.py` | SyncCheck 成功后更新 catalog 本行 |
| `.cursor/skills/apifox-cli-repo-first/catalog.md` | 总表里有本资产一行（场景/目录/生成器链接） |
| `.cursor/skills/apifox-cli-repo-first/suites/membership_purchase_p0.md` | 本资产短笔记（坑、分组、环境） |
| `postman/docs/Membership-Purchase-P0-apifox-cli-repo-first.md` | 本资产详解（给人读） |
| Apifox UI 场景 366587 | **你验收**：切 `ai/apifox-cli-sync`，看步骤与断言 |

### 你改一句需求时实际发生什么

例：「商品 A 的 `deductionAmount` 按 `original−payable` 断言」

1. AI 改 **`GeneratePostmanCollectionMembershipPurchaseP0.py`**（正本）  
2. 执行 `ApifoxRepoFirst.ps1 -Action PushSteps -Asset membership_purchase_p0`  
3. 脚本调用 tools：读 yaml → 生成 collection → Convert → Push 到 **366587**  
4. 你打开 Apifox，分支 **`ai/apifox-cli-sync`**，跑商品 A Create，看断言是否变绿  

中间产生的 `apifox-reports/membership_purchase_p0/generated/` 不用手改、不用提交。

常用命令：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset membership_purchase_p0
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset membership_purchase_p0
```

---

## 最容易踩的坑（人话）

**「我在 Apifox 里改好了，过两天又没了。」**  
因为又从代码同步了一遍，网页手改会被盖掉。下次让 AI 改正本再同步。

**「AI 说同步成功了，网页还是旧的。」**  
多半是分支没切对。切到 `ai/apifox-cli-sync` 再看。

**「断言绿了，但我不知道它查了啥。」**  
点开看「期望=…、实际=…」，那就是白话结果。

**「我不会写代码。」**  
不用会。你会提需求、会切分支看结果就行。

**「跑挂了怎么办。」**  
把失败步骤截个图（带上期望/实际），丢回 Cursor 让 AI 继续修，或拉熟手一起看。

---

## 团队一起用时你要知道的

完整推广说明见协作指南 **[§15 团队推广](./Apifox-CLI-Repo-First-协作指南.md#15-团队推广如何落地到小组)**。你只要记住：

| 你 | 别人 / AI |
|----|-----------|
| 提清需求；Apifox 切 `ai/apifox-cli-sync` 验收 | 改正本、同步、试跑 |
| 字段级用例交给 Agent 时，要求「先确认 E2E」 | 按 Skill 出清单给你点头再写脚本 |
| 发现只在网页改过脚本 | 提醒：改了也会被下次同步盖掉，应改正本 |

---

## 一句话收尾

> 你提需求 → AI 改正本并同步试跑 → 你在 Apifox（分支 `ai/apifox-cli-sync`）看结果。  

会这三步，就算会用了。要推广给小组，把协作指南 §15 的群公告发出去即可。
