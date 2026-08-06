# Apifox CLI · 参考与坑位

团队完整说明见：[`Apifox-CLI-Repo-First-协作指南.md`](../../../api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-协作指南.md)。

## 品类扩展（预预约 Payment）

以 **FT Membership / E-pass** 为金样例，向 Lounge / Fitness 等扩品类时：

→ **[`Prebooking-Payment-品类扩展指南.md`](../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md)**（两轴模型、生成器拆分、缺参 `302.000.001`、支付链接不测缺 cancelUrl、检查清单）

资产级 ID / 覆盖表仍看 `suites/ft_*_payment_*.md` 与 catalog；金额规则看实现参考文档。

## 工具链

| 脚本 | 作用 |
|------|------|
| `scripts/ApifoxRepoFirst.ps1` | 编排 Generate / PushSteps / SyncCheck / Run（路径来自 suites.yaml） |
| `tools/ApifoxSuitesYaml.py` | **唯一** suites.yaml 解析（PS / Upsert / Triage 共用） |
| `tools/ConvertPostmanToApifoxScenario.py` | Postman → 含 customScript 的 apifox 包 |
| `tools/PushApifoxScenarioSteps.py` | `test-scenario update`（customHttp）+ `--scenario-name` |
| `tools/SummarizeApifoxRunFailures.py` | 解析本次报告失败 |
| `tools/TriageApifoxRunFailures.py` | 通用分流；无 pattern → 全 leftover；不改生成器 |
| `tools/UpsertApifoxCliCatalog.py` | SyncCheck 成功后 upsert `catalog.md`（详解读 yaml `doc`） |

## 私有化限制

| 方式 | 结果 |
|------|------|
| `import --format postman` | 常 `Invalid Parameter` |
| `import --format openapi` | 仅接口壳，无 Tests |
| `import --format apifox` | 场景壳常 `steps=[]` |
| `test-scenario update` 422001 | ① 总包过大；② **单步 postProcessors 脚本 ≳62KB**（epass 曾踩坑） | helpers 精简 + `CompactJsLines`；**仅 Detail 挂 `PaymentExtraConsistency`**（Preview/Create 不挂）；Push 紧凑 JSON |
| AI 分支 + `test-scenario update`（customHttp） | 可写满步骤 + 后置脚本 |

项目通常 **无**「外部 AI 编辑权限」菜单；合 main 用客户端合并。

## 分支策略

- **唯一复用**：各资产 `working_branch`（当前共享 `ai/apifox-cli-sync`）
- 缺 `working_branch` **直接报错**（无静默回落）
- `ApifoxRepoFirst` 默认只 `branch get`；新建需 `-AllowCreateAiBranch`
- 禁止每次改脚本新建 `ai/日期-…`

## 通用断言约定

- 断言标题：`检查点 | 期望=… | 实际=…`
- 目的前置步骤名：`【中文目的】| 步骤ID | METHOD /path`
- 业务编排细节（自包含注册、快照 normalize 等）见各资产 `suites/<key>.md`，勿当成全局硬编码

## 字段级用例 → E2E（防漏断言 / 防猜错）

**触发**：用户给出 `testcases/**` 字段级用例、要求「按用例生成 / 补齐断言 / P0 冒烟」，或截图圈选 rc 检查点。

**顺序（不得跳步）**：

```text
确认目录(L1/L2/L3)
  → 输出正向 E2E 清单（等用户确认）
  → 按确认顺序生成 Folder/步骤骨架
  → 字段断言对照表（已确认项写硬断言；待确认先问）
  → Push（遵守下方规则）
  → 场景 description 含变量关系
```

### 正向 E2E 清单（生成前必交）

每条至少含：

| 列 | 说明 |
|----|------|
| 场景名 | 如「商品A-传券-引导期」 |
| 步骤序 | `Preview→Create→Details→Payments→Details→Cancel→Details` |
| METHOD/path | 每步接口 |
| 追溯 | 字段级 `tc-p*` / 章节 |
| P0? | 是否纳入冒烟 |

规则：

- **用户未确认 E2E 清单前**：禁止写生成器联调 / Generate+Push 当完成态。
- **P0 只减场景条数**，不打乱已确认步骤序；Cancel/支付等横切**嵌进原 E2E**，禁止擅自再开一条重复「仅取消」分组（除非用户明确要求独立场景）。
- 正向用例按 E2E 顺序生成接口，不要按字段散落拼请求。

### 字段断言对照表

| 列 | 说明 |
|----|------|
| 用例检查点 | 如 `$.data.coupon.details.description` |
| 期望来源 | Environment 键 / 公式（`original−payable`）/ 写死 / 响应对等 |
| 步骤 | A-PRE / B-CRT / … |
| 状态 | `已确认` / `待确认` / `砍掉(需同意)` |

- P0 **不砍**单条用例里的 rc 字段断言（减的是场景条数，不是字段覆盖）。
- 对照表有、脚本无 = **未完成**。
- **禁止**把 `待确认` 写成硬 `assertCheck` 后 Push。

### 语义不清 → 先问（典型）

| 用例措辞 | 先问什么 |
|----------|----------|
| 「description 为 couponName」 | 响应对等，还是 Environment（如 `CouponIntroValidName`）？键名？ |
| 金额「引导期 / 阶段价」 | payable/deduction 期望值或公式？ |
| Create 0 元 | `status` 是否仍强制 9？ |
| Preview 有、Create 无的字段 | Create 是否也要断言？ |

未答复前：该字段不写硬断言（可省略或 `assertInfo` 记实际值），并在回复列出待确认项。

### Push 规则

| 情况 | 是否 Push |
|------|-----------|
| 主路径已确认；歧义字段未硬断言或仅 info；交付列出待确认项 | **允许** |
| 版本内含**猜测**硬断言（未确认期望来源） | **禁止** |
| 主路径本身步骤序/接口也不清 | **整包阻塞**，先问清 |

金样例踩坑：`membership_purchase_p0` — 勿再把 `description=couponName` 猜成响应对等；应以 Environment `CouponIntroValidName`（或用户指定键）断言。

## 场景 description（变量关系）

**硬要求**：凡 Repo-first 新建 / 大改生成器，`collection["info"]["description"]` 必须写清「变量怎么用」，经 `ConvertPostmanToApifoxScenario` → `PushApifoxScenarioSteps` 落到 Apifox 场景说明。目标：打开场景页即可换测，不必翻生成器源码。

### 必备段落（顺序建议）

1. **生成源**：`由 <GeneratorModule> 生成 · <品类/域> · <P0|P1>`
2. **鉴权 / 环境**：哪些键来自 `.env` / Environment；换测改什么、不改什么（如「只改 Environment / BOSS，不换 Program」）
3. **链路摘要**：各文件夹或主路径（Preview→Create→…）
4. **变量关系（核心）**：Environment/集合变量 → 请求入参 / 断言期望；**金额用公式**，勿只列孤立默认值
5. **运行时变量**：Create 写出的 `orderId*`、动态 profile 等（注明勿预置空集合变量）

### 写法模板

```text
由 <GenerateXxx.py 或 common 模块> 生成 · <域> · <优先级>
鉴权：… → ProgramID/clientId/secret
环境：baseUrl / x-version …（换测只改 …）

【链路】
1 …
2 …

【变量关系】
· <envKeyA> → <入参或断言字段>（默认 …）
· <envKeyB> → …
· <金额字段> 期望 = <公式，如 original − payable>

【金额 / 断言块】（若有）
payment.currency / originalAmount / payableAmount / deductionAmount；…
charges[0].details[0]：…

【运行时变量】
· orderId* → Create 写出，Details/Payments 读入
```

### 金样例（抄结构，勿照抄业务键）

| 资产 | 实现 | 说明风格 |
|------|------|----------|
| `ft_*_payment_*` | `ft_prebooking_payment_common.CollectionMeta` + `BuildEnvPricingScenarioDescription()` | 单一环境定价表、Environment 键映射、`应付≈BASE+FEE−DISC` |
| `membership_purchase_p0` | `GeneratePostmanCollectionMembershipPurchaseP0.BuildScenarioDescription()` | 商品 A/B 变量；`deductionAmount=originalAmount−payableAmount` |

### Agent 自检

- [ ] description 非空、非单行口号
- [ ] 至少一条「期望 = 公式」或「键 ← Environment ``xxx``」
- [ ] Push 后 Apifox 场景页可见（与 FT Membership Payment P0 圈选区同级信息密度）

## 变量供给：数据集选行 vs Environment

**触发**：新建 / 大改多 Group 场景、字段级 P1、用户提「数据集 / 选行 / 全量数据 / 环境变量太多」。

**硬规则**：生成器落盘前 **先问用户二选一**，未答不得开写业务数据集或大改 Environment 方案。

### 询问话术（照抄）

```text
本场景预计有 N 个 Group（>5 建议选 A）。变量供给请选一种：
A. 数据集选行驱动（Apifox「全量数据」一行一场景；勾 name 行换测；全量勾 _FULL_SUITE）
B. Environment 手填（差分键 + 控制台短提示；适合 ≤5 / 单冒烟）
```

| 条件 | Agent 默认倾向 | 仍须 |
|------|----------------|------|
| Group / 可独立换测场景 **>5** | **推荐 A** | 等用户确认 |
| ≤5 或纯 P0 冒烟 | 可倾向 B | 仍问一句 |
| 用户明确点名 A 或 B | 按用户 | — |

### A · 数据集选行驱动（金样例：Membership Purchase P1）

**产物目录**：`api-testcases/api_tests/postman/datasets/<asset_key>/`

| 文件 | 用途 |
|------|------|
| `apifox-dataset-business-ascii.csv` | **导入 Apifox 全量数据**；编码选 **UTF-8**（界面常无 GBK；单元格用 ASCII/`FILL_*` 防乱码） |
| `scenario-group-map.md` | **中文 Group 名 ↔ 数据集 `name`**（给人看，勿导入） |
| `scenario-env-matrix.csv` / `scenario-env-keys.csv` | Excel 对照（可选） |
| `README.md` | 导入步骤 |

**实现约定**（抄 Membership Purchase P1 生成器）：

1. `BuildScenarioEnvCatalog()`：一场景一行差分键；`scenario_key` = 数据集 `name`（ASCII）。
2. `WriteApifoxBusinessDatasetCsvs()`：列 = `name,title,polarity,notes` + **业务键**（与 `{{键}}` / `getEnv` 同名）；含 `_FULL_SUITE` 并集行。
3. **禁止**把 `ProgramID` / `clientId` / `secret` / `accessToken` 放进业务数据集（鉴权仍 `.env` 或独立鉴权数据集三列）。
4. `baseUrl` / `x-version` 留 Environment（共用 Environment **勿整表删**业务无关键以外的网关项）。
5. **业务键种子（必抄，否则「勾了数据集却不是那行」）**：
   - 解析优先级：`pm.iterationData.get(键)`（Apifox「单独配置」勾选行）→ `pm.variables` 非占位 → `pm.environment` 非占位 → 生成器 `PLACEHOLDER_*`/`FILL_*` 占位。
   - 占位判定：空串，或以 `PLACEHOLDER` / `FILL_` 开头。
   - 解析后 **写入 `pm.variables`**，并对 body 内 `{{业务键}}` **强制字符串替换**（防止 Apifox 先用旧 Environment 解析 `{{}}`）。
   - `getEnv`：**业务键不要读 Environment**（只 `variables` → `collection`）；`baseUrl`/`x-version`/`accessToken`/鉴权三列才可读 Environment。
   - **禁止**种子把业务真值回写 Environment（污染共用 351893）；也禁止「只读 variables、完全忽略 iterationData/选行注入到 env」——会表现为勾了 `AWLB…` 却打出旧券 `8KTH…`。
6. 用户用中文认 Group：必须有 `scenario-group-map.md`；回答「这个中文 Group 的 name 是多少」时查该表。
7. Console 播报标题用「要改的数据集列」，勿再引导用户改 Environment 业务键。

**用户侧**：导入 ascii CSV → UTF-8 → 改 `FILL_*`/`PLACEHOLDER_*` 为沙箱真值 → 跑场景勾选对应 `name`（或 `_FULL_SUITE`）。选行只切换变量，**不会**自动只跑某一 Group；单测时 UI 勾该 Group。Environment 里同名业务键（`Coupon*`/`product*` 等）应删掉或留空，避免与选行混淆。

### 鉴权选行与后续步骤 ProgramID（2026-08 金样例踩坑 · Agent 必跟）

**触发**（任一即按本节改生成器，禁止只口头解释）：

- 勾了「自动化-鉴权」第二套，Auth 可能对、**后续** Preview/Create 实际请求 `X-Program-ID` 仍是第一套
- 算价空 / `currency=""` / `charges=false` / 金额 `undefined`，同时头里 Program 与勾选不一致
- 用户说「后续没有读取到选择的鉴权 programid」

**根因（常叠加）**：

1. **生成时写死**：`BearerJsonHeaders()` / Auth body 用 `AuthCredentials()` 把 `.env` 的 `MP_P0_*` 字面量打进 JSON → 运行时永远第一套。
2. **种子回落盖选行**：鉴权只做 `_id || _v || _fb(.env)`，**不读 Environment/collection/globals**；Apifox 勾选行常进 Environment，且步骤间 `pm.variables` 易清空 → 后续步用 `_fb` upsert 把头盖成第一套。
3. **作用域不持久**：只写 `variables`/`collection`，与 `accessToken` 同类问题；后续 Group 丢 ProgramID。
4. **只跑业务 Group**：未先跑 Auth，又无 Environment 注入时，只能吃到生成器 `.env` 回落。

**生成器硬约定**（抄 `GeneratePostmanCollectionMembershipPurchaseP1.Lines_SeedRuntimeEnvP1` + P0 `BearerJsonHeaders` / `Lines_EnsureAuthPrerequest`）：

| 项 | 正确做法 |
|----|----------|
| Auth body / `X-Program-ID` / Bearer 头 | 一律 `{{ProgramID}}` `{{clientId}}` `{{secret}}`，**禁止** `AuthCredentials().get(...)` 写入请求字面量 |
| 鉴权三列解析优先级 | `iterationData` → **Environment** → `variables` → `collection` → `globals` → 本机 `.env` 生成回落（`_fb` 必须最后） |
| 选中后写入 | 与 token 同：`variables` + `collectionVariables` + **environment** + **globals**，再 `headers.upsert('X-Program-ID')` |
| 业务数据集 | **禁止**混入鉴权三列；业务 `iterationData` 无 ProgramID 时靠 Auth/Environment 持久化值 |
| `getEnv('ProgramID')` | 允许读 Environment（infra）；业务键仍禁止读 Environment |

**Agent 自动处置顺序**：

1. Grep 生成器：`AuthCredentials().get`、`BearerJsonHeaders`、`"X-Program-ID"` 是否仍有字面量 ProgramID。
2. 改头/体为占位符；改鉴权种子优先级 + 四作用域；EnsureAuth 与种子一致。
3. `PushSteps`（或 SyncCheck）→ 提醒用户刷新 `ai/apifox-cli-sync`。
4. 复验话术：**只勾第二套鉴权一行 → 先跑 `00 Auth` → 再跑业务 Group**；核对 Preview「实际请求」头 = 勾选 ProgramID。

### 业务 body 误带 clientId/secret（2026-08 金样例踩坑 · Agent 必跟）

**触发**（任一即按本节改生成器，禁止只口头解释 / 只改 UI）：

- 用户圈选 Preview/Create「实际请求」body 里多了 `clientId` / `secret`
- 整组 E2E（Preview→Cancel）业务步连环失败，且实际请求 body 末尾带鉴权双字段
- 用户说「这两个参数不要传」「业务接口不该带 secret」

**根因**：

种子 Pre-request（如 `Lines_SeedRuntimeEnvP1`）在替换 `{{clientId}}`/`{{secret}}` 后，对 **任意** `JSON.parse(body)` 无条件执行 `_bj.clientId = _cid; _bj.secret = _sec`。Auth 需要覆盖死值，但业务 Preview/Create/Details/Payments/Cancel 也有 JSON body → 被污染。静态 Collection body / `BodyPreviewCreate` 往往本身正确，**运行时注入**才是问题；同场景所有挂该种子的步骤都会中招，不是单条用例写错。

**生成器硬约定**：

| 项 | 正确做法 |
|----|----------|
| `{{clientId}}` / `{{secret}}` 字符串替换 | 可保留（业务 body 无此类占位则无副作用） |
| `JSON.parse` 后写字段 | **仅当** body 本就 `hasOwnProperty('clientId'|'secret')`（Auth）才覆盖 |
| 禁止 | 任意 body 无条件 `_bj.clientId = …` / `_bj.secret = …` |
| ProgramID | 只走请求头 `X-Program-ID` upsert，**勿**塞进业务 body |

**Agent 自动处置顺序**：

1. Grep 生成器：`_bj.clientId`、`_bj.secret`、`JSON.parse(_raw)` 后无条件赋值。
2. 改为「仅 Auth body 才覆盖」（抄 Membership Purchase P1 `Lines_SeedRuntimeEnvP1` 已修逻辑）。
3. 扫同仓库其它 `GeneratePostmanCollection*.py`：若有同类无条件注入一并修；P0 仅字符串替换则通常无此坑。
4. `Generate` → `PushSteps`（或 SyncCheck）→ 提醒刷新 `ai/apifox-cli-sync`。
5. 复验：业务步「实际请求」body **无** `clientId`/`secret`；Auth 步仍有且值=勾选鉴权行。

### B · Environment 手填

沿用下文「换测 Environment：Group 变量定位与控制台短提示」：`announce_only_keys` + Console 短行；键名按场景拆开（如 `productANoSub*`），避免共用一个值来回改。

### 反模式

| 反模式 | 正确 |
|--------|------|
| 未问用户就只堆 Environment | 先问 A/B |
| 把对照 matrix 当全量数据导入且含大量中文 | 用 `apifox-dataset-business-ascii.csv` + UTF-8 |
| 业务数据集混鉴权三列 / 空 `accessToken` 列 | 鉴权独立 |
| 只有英文 name、无中文对照表 | 必出 `scenario-group-map.md` |
| 选 A 后种子只读 `pm.variables`、忽略 `iterationData`/选行注入 | 按第 5 条优先级 + body 强制替换 |
| `BearerJsonHeaders` / Auth body 生成时写死 `.env` ProgramID | 一律 `{{ProgramID}}`/`{{clientId}}`/`{{secret}}` |
| 鉴权种子 `_id \|\| _v \|\| _fb(.env)`，跳过 Environment/collection | 见「鉴权选行与后续步骤 ProgramID」；四作用域持久化 |
| 种子对任意 JSON body 无条件 `_bj.clientId/_bj.secret` | 见「业务 body 误带 clientId/secret」；仅 Auth body 覆盖 |
| 为「清 Environment」在脚本里 environment.set(业务键,'') 持久清空共用环境 | 只改读优先级；网关保留；剥离业务键用 CLI export+environment update；setRuntime 勿再写 env |
| 断言期望与沙箱实测 errCode 不一致仍硬撑旧码 | 以实测为准改生成器（如过期 Create：`500.000.702` 非 `500.020.031`）再 Push |

## 换测 Environment：Group 变量定位与控制台短提示

**触发**：用户问「这个场景/Group 改哪些环境变量」「不知道填啥」「填写指南」「控制台没有 / 字太多 / 挪到控制台」「只保留某一个键」。

**目标**：换测时 10 秒知道改哪几个键；跑 Group 首步打开 **控制台** 能对上当前值；**断言面板不被填写说明刷屏**。

### Agent 处置顺序（自动做）

1. **先答短表**（本 Group 差分键 + 一句话含义 + 与谁对齐），勿甩全集 Environment。
2. **定位键从哪来**（按优先级）：
   - 生成器该 Folder 的 `coupon_env=` / `price_env=` / `payable_env=` / `program_*_env=` / `announce_only_keys=`
   - `BuildScenarioDescription()` / Group `description`
   - `suites/<asset>.md` 增量键说明
3. **播报实现约定**（Membership Purchase 金样例，可抄到其它多 Group 资产）：
   - 入口：`Lines_AnnounceGroupEnv`（P0 生成器）+ 各 Folder 传入键列表
   - **只打 `console.log`**（Pre-request + Tests 各一遍，因 Apifox 有时只在一侧可见）
   - **禁止**用多条长文 `assertInfo` / 恒通过 `pm.test` 当填写指南（用户会抱怨断言面板字太多）
   - 行格式短：`键 = 当前值  // 短含义`；完整词典可留在 `ENV_KEY_FILL_GUIDE`（供文档），控制台用 `ENV_KEY_FILL_SHORT`
   - **默认只播差分键**：用 `announce_only_keys=[...]`；共用键（券/program/原价）已配好时不要重复刷屏
4. **改完必 Push**：`Generate` → `PushSteps`（或 `SyncCheck`）；口头说「看控制台」但未 Push = 未完成。
5. **金额失败先对 Environment**：断言 `期望≠实际` 时，先核对播报的应付/原价键是否与接口一致（常见：未开引导期应付未改成=原价）。

### 用户侧怎么看

| 位置 | 期望 |
|------|------|
| **控制台** | 本 Group 要改的键 + 当前值（主入口） |
| **断言结果** | 只留业务断言；无长篇「填写指南」绿勾 |
| **场景/Group description** | 静态变量关系（不跑也能查） |

说明：Apifox 部分运行视图控制台可能为空；若用户说「控制台没有」，先确认已 Push 最新脚本，并看 **后置脚本执行后的控制台**（Tests 侧也会打一遍）。

### Membership Purchase 差分键速查（换测）

| Group（关键词） | 控制台优先只提示 | 对齐规则 |
|-----------------|------------------|----------|
| 商品B 无券原价 | `productBPrice` / `productBCurrency`（按需） | 无券，应付≈原价 |
| 商品A 引导期 | `productAPayableAmount`（常 0） | `deduction=price−payable`；0 元 Create status=9 |
| 商品A 无订阅 | `productANoSub*` | Preview 原价 OK、Create 033；与引导期 `productA*` 勿混用 |
| 商品A 订阅关 | `productASubOff*` | 同上；共用 `CouponIntroNoRenew`，靠 program 区分 |
| **商品A 未开引导期·原价** | **仅 `productANoIntroPayableAmount`** | **必须 = `productAPrice`**（否则金额红） |
| 负向券 | 对应 `CouponExpired` 等单键 | 见 suites 笔记 errCode |

**场景×变量 CSV（选行换测 / 填齐跑全量）**：  
`api-testcases/api_tests/postman/datasets/membership_purchase_p1/`  
- 导入全量数据：`apifox-dataset-business-ascii.csv`（UTF-8）  
- 中文 Group↔name：`scenario-group-map.md`  
- 详见上文「变量供给：数据集选行 vs Environment」

金样例代码：

- `GeneratePostmanCollectionMembershipPurchaseP0.Lines_AnnounceGroupEnv` / `ENV_KEY_FILL_SHORT`
- `GeneratePostmanCollectionMembershipPurchaseP1.BuildStandardPendingE2E(..., announce_only_keys=...)`
- 未开引导期：`announce_only_keys=["productANoIntroPayableAmount"]`

### 反模式（已踩坑，勿重复）

| 反模式 | 后果 | 正确做法 |
|--------|------|----------|
| 长文 `assertInfo` 刷断言面板 | 用户觉得「字太多」、找不到业务失败点 | 只 Console 短行 |
| 每个 Group 打印全部 `productA*`+券+固定说明 | 控制台刷屏 | `announce_only_keys` 只留差分 |
| 只改生成器不 Push | UI 仍是旧脚本 | PushSteps / SyncCheck |
| 未开引导期应付仍填引导期价/旧默认 `10` | `payable`/`unitPrice` 断言失败 | 应付=原价 |

### Agent 自检

- [ ] 已用短表回答「改哪几个键」
- [ ] 播报不占断言面板
- [ ] 差分 Group 使用 `announce_only_keys`（或等价）
- [ ] 已 Push；用户可在控制台看到短行

## 场景用例目录（项目 346275）

**Agent：生成脚本 / 首次 Push / create 场景之前，必须先问用户放在哪条路径；未确认不得继续。**

### 约定树

```text
membership|epass|common
└── P0(冒烟用例) | P1（全量用例）
    └── prebooking | walk-in | others
```

| 级 | 取值 | 含义 |
|----|------|------|
| L1 | `membership` / `epass` / `common` | 业务域 |
| L2 | `P0(冒烟用例)` / `P1（全量用例）` | 冒烟 vs 全量 |
| L3 | `prebooking` / `walk-in` / `others` | 预约 / 现场 / 其他 |

主分支上历史目录名（如 `EPASS`、`P0核心场景`）与 AI 分支新树并存；**新资产只落 AI 分支新树**，勿再往根目录或旧 `PAPI-*` 壳目录堆场景。

### 当前已挂载（`ai/apifox-cli-sync`）

| 资产 | 场景 ID | 目录 | folderId |
|------|---------|------|----------|
| `papi_2548` | 365969 | `membership/P1（全量用例）/others` | **350030** |
| `papi_2515` | 365972 | `membership/P1（全量用例）/others` | **350030** |
| `papi_2424` | 365975 | `epass/P1（全量用例）/others` | **350039** |
| `local_offers_options` | 365976 | `common/P1（全量用例）/others` | **350048** |
| `local_offer_epass_p0` | 366256 | `epass/P0(冒烟用例)/prebooking` | **350033** |
| `local_offer_epass_p1` | 366257 | `epass/P1（全量用例）/prebooking` | **350037** |
| `ft_membership_payment_p0` | 366258 | `membership/P0(冒烟用例)/prebooking` | **350024** |
| `ft_membership_payment_p1` | 366261 | `membership/P1（全量用例）/prebooking` | **350028** |
| `ft_epass_payment_p0` | 366262 | `epass/P0(冒烟用例)/prebooking` | **350033** |
| `ft_epass_payment_p1` | 366263 | `epass/P1（全量用例）/prebooking` | **350037** |

查目录：`apifox folder list --project 346275 --type test-scenario --branch ai/apifox-cli-sync`  
挪场景（只改目录，勿整包 PUT）：

```powershell
apifox test-scenario update <scenarioId> --project 346275 --folder-id <folderId> --branch ai/apifox-cli-sync
```

建空目录：`apifox folder create --project 346275 --type test-scenario --file <folder-create.json> --branch ai/apifox-cli-sync`（JSON 用 UTF-8；`--name` 与 `--file` 同传时 CLI 参数会盖掉文件，中文名易乱码——**优先只传 `--file`**）。

### 写入权限

- 目录 / 场景元数据写入需 AI 分支（或项目开启外部 AI 直编）；默认用 `working_branch`。
- AI 分支改完后**不要自动 merge**；需用户确认再合主分支。

## 场景内分组（Agent 默认按此编排）

金样例：`ft_membership_payment_p1`（`ft_prebooking_payment_common.BuildP1PaymentFolders`）。  
工具链已支持：Postman `Folder` 嵌套 → Convert 出 `type=group` → Push 保留可折叠分组（勿再拍平）。

### 分组原则（按业务场景，不是按技术步骤）

| 层级 | 怎么分 | 示例 |
|------|--------|------|
| **一级** | 主业务维度（支付方式 / 订单形态 / 模块差异） | `权益支付` / `现金` / `客户预收款` |
| **二级** | 该维度下的用例变体（点数、关键入参、正负向） | `现金使用权益点数0点-async:true` |
| **叶步骤** | 一条用例的完整链路（Preview→Create→…） | 目的前置 HTTP 步 |

**禁止**为「发起支付」「async」「取消后详情」等**横切能力**单独开一级/二级分组。这类能力应**嵌进**主场景链路：

- 成功 Create 后需要验支付 → 同链路追加 `POST /orders/payments`（期望随场景：待支付 `REDIRECT` / 0 元 `500.000.802`）。
- `async` 缺失 / `false` / `true` → **分散**挂到已有权益/现金（或同类主场景）子夹，名称或 purpose 标明变体；三种至少各覆盖一次即可，勿再复制三套全链路。
- 取消后详情/列表 → 成功下单链路尾部固定带上，勿另开「取消验证」夹。

### Agent 落盘时自动决策

1. 从需求/参考文档抽出**主场景轴**（如 `payment_mode` × `entitlement_count`），作为一级/二级文件夹名（中文、可读，对齐手工 Apifox 习惯）。
2. 列出横切能力（发起支付、async、取消后查询…）→ 映射进主轴链路参数（如 `initiate_payment` / `include_async_key`），**不**新增顶层夹。
3. 生成器：`Folder("一级", [Folder("二级", BuildXxxChain(...))])`；Convert/Push 勿改回扁平。
4. 负向只到 Preview/Create 的用例：二级名写清「报错」，且**不要**跟发起支付。
5. SyncCheck 后在 `suites/<asset>.md` 用「一级 → 二级」表记一笔，方便下次抄。

### 实现要点（勿回退）

- Convert：`BuildApifoxStepsFromPostmanItems` 保留文件夹为 `group`（`parameters.name` + `children`）。
- Push：`ToCliScenarioSteps` 递归 group；目的前置校验只扫 **HTTP 叶节点**（`FlattenHttpStepNames`）。
- 权益足额 ≠ 一定 0 元：用户承担预约费时发起支付常仍为 `REDIRECT`；`CLIENT_COLLECT` 0 元才是 `802`。以沙箱实测为准，勿臆测。

## 扩新资产

0. **先问用户**：场景挂到 `L1/L2/L3` 哪条；确认后填 `suites.yaml` 的 `scenario_folder` / `scenario_folder_id`，并写入 `suites/<key>.md`
1. 复制 `.apifox/suites.yaml` → `assets.<key>`，填 `generator` / `collection` / `scenario_name` / `test_scenario_id` / `scenario_folder` / `scenario_folder_id` / `environment_id` / `working_branch` / `doc`
2. **鉴权凭据**：若环境 get 看不到变量，须填 `use_data_set_id`；PushSteps 写入场景 `options`。数据集列名**仅允许**三列标准名：`ProgramID`、`clientId`、`secret`（与请求 `{{…}}` 一致）。勿用 `programId` / `clientSecret`；勿放空的 `accessToken` 列。运行时令牌统一写 `accessToken`（`Bearer {{accessToken}}`），**禁止**另造 `dpAccessToken`
3. **多环境**：`baseUrl`、`x-version` 等放在各 Apifox Environment；集合变量留空以免盖住环境注入。切换：改 `assets.<key>.environment_id`，或 `.\scripts\ApifoxRepoFirst.ps1 … -EnvironmentId <id>`
4. **路由头 `x-version`**：环境变量名 `x-version`（对应 pytest `DP_X_VERSION`，canary 常为 `canary`）。生成器请求头须带 `x-version: {{x-version}}`；环境未配则头值为空
5. **不必**改 `ApifoxRepoFirst.ps1` 写死路径；Push 场景名与报告前缀已按资产透传
6. `.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <key>`
7. 确认 `catalog.md` 有行；可选 `suites/<key>.md`

报告落在 `apifox-reports/<asset>/`（含 `last-failures.md` / `leftover-failures.md`）。

## 空 X-Request-ID → 301.000.001（2026-08 金样例踩坑 · Agent 必跟）

**症状（任一即触发自动处置）**

- 业务响应：`errCode=301.000.001`，msg 含 `X-Request-ID` / `invalid characters or format`
- 导出 curl：`--header 'X-Request-ID;'` 或 `Accept;`（头名后无值）
- 用户说：单步调试发送失败 / Membership Purchase 等 CLI sync 场景点「发送」报 301

**根因**

- 集合头写 `X-Request-ID: {{$guid}}`（Postman 动态变量）
- 私有化 Apifox **单步调试 / customHttp** 常不展开 `{{$guid}}` → 空头 → 网关校验失败
- 仅改 Apifox UI 会在下次 Push 被仓库覆盖

**标准修复（勿另起一套）**

1. 公共源：`api-testcases/api_tests/postman/generators/collection_builder_common.py`
   - `Lines_EnsureRequestIdHeader()`：前置自生成 UUID + `headers.upsert('X-Request-ID')`（兼补 `Accept: */*`）
   - `JsExpr_FreshRequestId()`：给 `pm.sendRequest` 回退头用（禁止裸 `replaceIn('{{$guid}}')`）
2. 公共 `RequestItem` 已默认前置挂载；**自有** `Lines_EnsureAuth*` / `RequestItem` 的套件须 `*Lines_EnsureRequestIdHeader()` 拼到前置末尾。
3. 扫仓库：头仍只写 `{{$guid}}` 且前置未 upsert 的生成器一并修。
4. `Generate` + `PushSteps`（用户场景相关资产；用户说「全部」则按 `suites.yaml` 全量 Push）。
5. 复验：实际请求 / curl 中 `X-Request-ID` 为合法 UUID；临时手填 UUID 仅作应急，不算完成。

**禁止**

- 只口头解释「填个 UUID 再试」而不改生成器
- 新建套件只靠头里 `{{$guid}}`、不挂 `Lines_EnsureRequestIdHeader`

---

## 症状 → 自动处置（Agent 必跟）

用户报「CLI/UI 跑失败」「Auth 过了后面全挂」「token 没传」「勾了鉴权第二套后续 ProgramID 不对」「301.000.001 / X-Request-ID」或「项目自动化页面骨架屏」时，**先对症状表再改生成器**；改完必须 `SyncCheck`/`PushSteps`，勿只改文档。项目级 loading 另须先读 [`postman-apifox-troubleshooting.md`](../api-testcase-pack/postman-apifox-troubleshooting.md) §0.1。

| 症状 | 根因（私有化 Apifox 常见） | Agent 自动处置 |
|------|---------------------------|----------------|
| Auth 绿，后续大量 `code:-1` / `201.000.001` / `businessSuccess=false`；头里有 Bearer 但仍像未鉴权 | ① 数据集有空列 `accessToken` 盖掉 Auth 写入；② 集合预置空 `accessToken`；③ 场景里 `collectionVariables` 不持久，只写 collection 会丢；④ UI 看的是主分支旧场景；⑤ **path/body 用了集合变量**（如 `/{{p2424V2DetailsPath}}`）在 customHttp 场景下常不解析，打到错误 URL | 生成器：`accessToken` 多作用域写入（`variables`/`env`/`globals`/`collection`）；前置清空调空列并 `upsert`/`add` Authorization；**集合勿预置空 accessToken**；数据集只留 `ProgramID`/`clientId`/`secret`。Auth 加「已写入运行时」断言。**path 与静态测试数据写死字面量**（勿把整段 path 放集合变量）。推 `ai/apifox-cli-sync` 后让用户 UI 刷新同分支重跑 |
| 单步调试 / curl 出现 `X-Request-ID;`（无值）；业务 `301.000.001` *invalid characters or format* | Apifox 常不展开头里的 `{{$guid}}`，发出空 `X-Request-ID`（`Accept` 有时也空） | 见下节「空 X-Request-ID → 301.000.001」；**立即**挂公共前置并 Push，勿只口头让用户手填 |
| Auth body `invalid secret` / 取 token 失败 | 凭据在数据集不在 environment get；列名用了 `programId`/`clientSecret` 等别名 | `suites.yaml` 配 `use_data_set_id`；Push 保留 `options.useDataSetId`；列名**仅** `ProgramID`/`clientId`/`secret`；body/头用同名 `{{…}}` |
| CLI SyncCheck 绿，UI 仍 30+ 失败 | UI 未切 `working_branch` 或未刷新；或对比的是旧报告；**场景可能只在 AI 分支有 steps**（main get 常 `steps=0`） | 提醒切 `ai/apifox-cli-sync` + 硬刷新；以 `apifox-reports/<asset>/` 最新一次 SyncCheck 为准；勿在 main 验收 CLI sync 场景 |
| 打开「自动化测试」长期骨架屏；多人同项目、main/AI 都可能复现 | 可能是项目初始化全量 `/api-details` / Schema / Mock 慢或重复加载，也可能数据已到但 Electron 未重绘；**不是看到本地 collection 大就能下结论** | 按 troubleshooting §0.1：CLI 只读验证场景树 → 测客户端版本/内存 → 用户同意后干净重启 → CDP 测真实大小/pending → DOM 完成但画面旧才强制重绘；连续切分支 Heap 上涨即停，最终恢复 `working_branch`；不得先删场景/挪目录 |
| 实际请求 URL 含 `%7B%7BresourceId%7D%7D` / 字面 `{{var}}`；正向 `500.020.016` | ① path 用了 Environment **没有**的变量名（如 `localOfferResourceId`，环境只有 `resourceId`）；② customHttp 未替换 path 占位符；③ 集合预置空/旧值盖住环境 | **path 用环境已有变量名**（Local Offer：`resourceId`/`optionId`）；集合**不预置**业务 ID；前置：`pm.environment.get` 优先 → 改写 `url.raw`/`url.path` 未解析占位符。**禁止**为「好跑」把网点 ID 写死进生成器（用户明确要环境变量时） |
| GET 有 query 的步：分页不回显 / 非法 query 却业务成功 | Convert 把 `parameters.query` 置空；或 Push 后 customHttp **不带** query | `ConvertPostmanToApifoxScenario.ExtractPostmanQueryRows` 透传 `url.query`；`PushApifoxScenarioSteps` **把启用中的 query 拼进 `customHttp.path`**（`?a=1&b=2`） |
| 空 path 段负向（如 `/localOffers//options`）打到错误路径 | ResolvePath 用 truthy 过滤掉空 path 段 | Convert `ResolvePath` **保留空 path 段** |
| 正向 `code=-1` 却断言「可跳过」绿 | 生成器把业务失败当 pytest.skip 软通过 | **正向业务失败硬失败**（`code=0`）；禁止 `assertInfo(…可跳过)`。用户要求「业务失败不可跳过」时立刻改 |
| 非法 pageSize/language 等只断言「非成功」太弱 | 网关有固定非法入参文案 | 断言 `code=-1` + msg=`The field '<field>' contains invalid characters or format is incorrect.` + errCode（分页 `301.020.001` / language `300.020.001`）；见 `loAssertInvalidFieldRejected` |
| U03/U05/E3：DELETE 后 extensions 仍含被删 type（期望为实际子集） | canary（`x-version=canary`）下 DELETE 常不落库 | `assertExtNormEqual(…, { allowCanaryDeleteNoop: true })`；勿为过 canary 改业务预期 |
| 换环境后 baseUrl 仍指向旧网关 | 集合写死了 sandbox URL，或空集合变量盖住 Environment | 集合 `baseUrl`/`x-version` 留空；前置优先 `pm.environment.get`；用 `environment_id` / `-EnvironmentId` 切换 |
| CLI 绿但本地报告里仍有旧失败文件 | 看了历史 `*-failures.json` / 陈旧 `leftover-failures.md` | 按文件时间戳取最新；`failures: []` + junit failures=0 才算绿；Triage 无失败时**清空** `leftover-failures.md` |
| 预预约：现金点 1 变成 1 人预约 / 乘客数=1 | `AdultCountForEntitlementPoints` 按点数缩减人数 | **可用性/预约统一 adultCount=3**；点数只改 `toUseEntitlement*`；纯权益勿 1 点约 3 人（`500.051.011`）。通识：[品类扩展指南 §9](../../../api-testcases/api_tests/postman/docs/Prebooking-Payment-品类扩展指南.md) |
| 预预约：可用性有 `prebookingToken`，Preview/Create 仍旧/空/`{{…}}` | 集合预置空串 + body `{{prebookingToken}}` 被 `replaceIn` 洗空；customHttp 只写 collection 易丢；可用性后 `SetVar(GetVar)` 可能冲空 | **勿** `CollectionVariable("prebookingToken","")`；body 预置 `""`；`ftSavePrebookingToken`（`pm.test` 外写入）；`Prerequest_InjectPrebookingToken` Auth 序硬写（`ft_prebooking_payment_common`） |
| 预预约：权益不足得 `500.051.004` / 假绿 | `avail+1` 超姓名池 → AVL 无 token 仍 Preview；只认 `042.011` 会红 | ``POST /v2/entitlements/update`` 减点造数（`usageRestriction` 1/2/3）；`MS→DEC→AVL→PRE→CRT`；接受 `042.011`/`051.011`/`051.020`，**硬失败** `051.004`；见品类扩展指南 §9.7 |
| 预预约：0 元发起支付「802或跳过」 | `ftPayAssertPaymentNotRequired` soft skip | `payableAmount=0`/无字段 → **硬断言** `500.000.802`，禁止跳过 |
| 预预约：status=9 取消文案不对 | 取消步未钉死 msg | `Order cancellation failed. Please try again later.`（`ftPayAssertCancelUsageResponse`） |
| 预预约：`true+DP_COLLECT` 只验 code=-1 | 缺 errCode/msg | `500.051.023` + conflict 固定英文 msg |
| 预预约：顶层仍有 `01 Setup` | `BuildCollection` 挂了 Setup | 去掉；链路内 `refresh_membership`/`refresh_epass` |
| **ePass**：客户预收款/Bundle 预收款当正向；body 有 `cashPaymentApplied` | 误抄 Membership；ePass 无预收款 | `CLIENT_COLLECT`→conflict msg；**勿传** `cashPaymentApplied`；见品类扩展指南 §5/§9.1#10 |
| **ePass**：断言「status=1或5」在 status=9 时绿 | `st===9` 静默 return | 允许 `[1,5,9]`，标题写清待支付；禁止静默软过 |
| **ePass**：Bundle 取消无失败文案 | 取消步只「可解析」 | 同主链路 `ftPayAssertCancelUsageResponse` |
| Preview「ePassId 空/不一致」却带真 ID | placeholders 无脑覆盖 ePassId | 仅 `{{` 占位符才注入；空串/伪造 ID 保留 |
| Preview「membership token」假绿/假红 | 用假 token 字符串；或 MS 注册冲掉 clientUserId | `MS(复用 cuid)→membership AVL→ePass Preview` |
| 缺/空必填因 errCode `302.000.001`≠`302.051.001` 红 | 沙箱缺参码不统一 | **只验固定 msg**+`code=-1`；改 common 后 Push FT/Lounge×MS/EP P1 |
| Push `ECONNRESET` / `422001` | 大包网络断 / helpers 膨胀 / **单步 post ≳62KB** | 重试 `PushSteps`；精简 helpers；Preview 不挂 PaymentExtraConsistency |
| Run 断言表 0 失败但脚本 exit 1 | `$LASTEXITCODE` 污染或汇总脏计数 | 以 `*-failures.json`（空=绿）+ CLI 断言表为准；已修 summarizer / `ApifoxRepoFirst` |
| **勾了全量数据/单独配置某行，请求体券码/金额却不是该行**（UI 行=`AWLB…`，实际=`8KTH…`/PLACEHOLDER/旧 Environment） | ① 种子只读 `pm.variables`，Apifox 选行在 `iterationData` 或 env；② body `{{键}}` 被旧 Environment 先解析，强制替换又因 variables 空而跳过；③ 选行只换变量、未勾对应 Group；④ CLI SyncCheck **不会**带 UI 勾的业务行 | **立即改生成器种子**（见上文「变量供给 A · 第 5 条」）：`iterationData`→variables 非占位→env 非占位→占位；写入 variables + **body 强制替换**；`getEnv` 业务键不读 env。金样例：`GeneratePostmanCollectionMembershipPurchaseP1.Lines_SeedRuntimeEnvP1`。改完 `PushSteps`（或 SyncCheck）。提醒：Environment 删业务键；单测再勾 Group；CLI 验收不代表 UI 选行 |
| **勾了鉴权第二套 ProgramID，后续 Preview/Create 实际请求 `X-Program-ID` 仍是第一套**（算价空/币种空/`charges=false`） | ① `BearerJsonHeaders`/`Auth` 生成时把 `.env` 写死进头/体；② 鉴权种子 `_id\|\|_v\|\|_fb`，**跳过 Environment**，步骤间 variables 清空后回落 `.env` 并用 upsert **盖掉**正确头；③ 只跑业务 Group 未先跑 Auth；④ 业务数据集无鉴权列却被当成唯一 iterationData | 见上文「鉴权选行与后续步骤 ProgramID」：**立即改**生成器（占位符 + 含 Environment 的优先级 + 四作用域）→ `PushSteps`；复验先 Auth 再业务；金样例 Membership Purchase P1 |
| **业务 Preview/Create「实际请求」body 多出 `clientId`/`secret`**（鉴权字段误进订单体） | 种子脚本 `JSON.parse` 后对**任意** body 无条件 `_bj.clientId=_cid` | 仅当 body **本就含** `clientId`/`secret`（Auth）才覆盖；`{{clientId}}` 字符串替换可保留；金样例 `Lines_SeedRuntimeEnvP1` |
| Membership Purchase：过期/不适用券 Create 期望 `500.020.031` 实际 `500.000.702` + `not applicable` | 旧用例映射过期→031，沙箱对「券不适用」统一 702 | Create 步改 `Lines_AssertBizFail(..., "500.000.702", "not applicable")`；同步用例 md / 场景 description errCode 表；**过期 / 非周期 / 不满足条件**→702；**不存在 / 跨 Program / 无订阅·订阅关 autoRenewal=false**→031（以实测为准）。Push 后让用户重跑 |
| Membership Purchase：不满足条件券 Preview 期望「details 保留」实际 `details=null` | 用例旧文案与沙箱不一致 | 按用户/实测改断言为 `details=null`（可对齐 `Lines_PreviewInvalidCoupon`）；同步字段级用例 md；标题「保留详情」可随后改文案。Push |

### 令牌传递标准实现（生成器模板）

1. **Auth 后置**：从响应 `data.accessToken` 取出后写入 `pm.variables` / `collectionVariables` / `environment` / `globals`（均 try/catch）；并 `pm.test` 断言至少一处非空。  
2. **业务步前置**：若 `variables.accessToken` 为空串则 `unset`；再按 collection → globals → env → variables 取非空 token；回写各作用域；`headers.upsert`（否则 `remove`+`add`）`Authorization: Bearer <tok>`。  
3. **禁止**：另造 `dpAccessToken`；集合/数据集预置空 `accessToken`；Auth 只 `assert` 不 `set`。  
4. **多环境**：`baseUrl`、`x-version` 只放 Environment；鉴权三列只放数据集。

金样例：`generators/GeneratePostmanCollectionPapi2548.py` 的 `SaveTokenLines` / `Lines_EnsureAuthPrerequest`（2515 同构）。

## Triage（禁止每需求一份）

```powershell
python tools/TriageApifoxRunFailures.py --report-dir apifox-reports/papi_2548 --asset papi_2548 --repo-root .
```

- 默认不配 `script_name_patterns` → 失败全 leftover
- exit `0` / `1` leftover / `10` 仅 SCRIPT（再 Generate+Push+Run 一轮，**不改生成器**）

## Catalog upsert

```powershell
python tools/UpsertApifoxCliCatalog.py --asset papi_2548
```

详解列优先 `suites.yaml` → `doc`，并附 `suites/<key>.md` 笔记链。
