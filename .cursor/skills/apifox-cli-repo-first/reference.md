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

## 症状 → 自动处置（Agent 必跟）

用户报「CLI/UI 跑失败」「Auth 过了后面全挂」「token 没传」时，**先对症状表再改生成器**；改完必须 `SyncCheck`，勿只改文档。

| 症状 | 根因（私有化 Apifox 常见） | Agent 自动处置 |
|------|---------------------------|----------------|
| Auth 绿，后续大量 `code:-1` / `201.000.001` / `businessSuccess=false`；头里有 Bearer 但仍像未鉴权 | ① 数据集有空列 `accessToken` 盖掉 Auth 写入；② 集合预置空 `accessToken`；③ 场景里 `collectionVariables` 不持久，只写 collection 会丢；④ UI 看的是主分支旧场景；⑤ **path/body 用了集合变量**（如 `/{{p2424V2DetailsPath}}`）在 customHttp 场景下常不解析，打到错误 URL | 生成器：`accessToken` 多作用域写入（`variables`/`env`/`globals`/`collection`）；前置清空调空列并 `upsert`/`add` Authorization；**集合勿预置空 accessToken**；数据集只留 `ProgramID`/`clientId`/`secret`。Auth 加「已写入运行时」断言。**path 与静态测试数据写死字面量**（勿把整段 path 放集合变量）。推 `ai/apifox-cli-sync` 后让用户 UI 刷新同分支重跑 |
| Auth body `invalid secret` / 取 token 失败 | 凭据在数据集不在 environment get；列名用了 `programId`/`clientSecret` 等别名 | `suites.yaml` 配 `use_data_set_id`；Push 保留 `options.useDataSetId`；列名**仅** `ProgramID`/`clientId`/`secret`；body/头用同名 `{{…}}` |
| CLI SyncCheck 绿，UI 仍 30+ 失败 | UI 未切 `working_branch` 或未刷新；或对比的是旧报告；**场景可能只在 AI 分支有 steps**（main get 常 `steps=0`） | 提醒切 `ai/apifox-cli-sync` + 硬刷新；以 `apifox-reports/<asset>/` 最新一次 SyncCheck 为准；勿在 main 验收 CLI sync 场景 |
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
