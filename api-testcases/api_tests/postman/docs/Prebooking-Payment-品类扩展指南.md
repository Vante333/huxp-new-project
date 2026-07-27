# 预预约 Payment · 品类扩展指南

> **定位**：把 **FT Membership / E-pass** Prebooking Payment（P0/P1）的编写经验抽成跨品类通识，供后续 **Lounge / Fitness / …** 对齐抄作业。  
> **不是**：金额公式全文（见实现参考）、单资产 ID 表（见 `suites/ft_*.md`）、payment 断言脚本细则（见断言 Skill 附文）。

## 读谁（按任务）

| 任务 | 先读 |
|------|------|
| 新建/扩展某品类的 Apifox 场景 + 生成器 | **本文** → catalog 最近似 FT 行 → 对应 `suites/<asset>.md` |
| Repo-first / SyncCheck / Push | [`apifox-cli-repo-first`](../../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) + [`reference.md`](../../../../.cursor/skills/apifox-cli-repo-first/reference.md) |
| Preview/Create/Detail **payment 断言** | [`prebooking-payment-apifox-assertions.md`](../../../../.cursor/skills/api-testcase-pack/prebooking-payment-apifox-assertions.md) |
| 业务规则（七场景、金额、Bundle） | [`订单流支持真现金支付第三方权益-自动化实现参考.md`](../../../../testcases/2026Q2SP4/订单流支持真现金支付第三方权益-自动化实现参考.md) |
| FT 实例覆盖与环境变量 | [`FT-Membership-Payment-P1-apifox-cli-repo-first.md`](./FT-Membership-Payment-P1-apifox-cli-repo-first.md)、[`FT-Epass-Payment-P1-apifox-cli-repo-first.md`](./FT-Epass-Payment-P1-apifox-cli-repo-first.md) |
| **排障**（人数/token/802/取消/Setup/冲突） | **本文 §9** → [`问题回顾 §11`](./Apifox-CLI-Repo-First-问题回顾.md) → Skill [`reference.md` 症状表](../../../../.cursor/skills/apifox-cli-repo-first/reference.md) |

**金样例资产（优先抄）**

| 资产 key | 账户轴 | 品类轴 | 生成器入口 |
|----------|--------|--------|------------|
| `ft_membership_payment_p0` / `_p1` | Membership | Fast Track | `GeneratePostmanCollectionFtMembershipPaymentP*.py` |
| `ft_epass_payment_p0` / `_p1` | E-pass | Fast Track | `GeneratePostmanCollectionFtEpassPaymentP*.py` |
| `lounge_membership_payment_p0` / `_p1` | Membership | Lounge | `GeneratePostmanCollectionLoungeMembershipPaymentP*.py` |
| `lounge_epass_payment_p0` / `_p1` | E-pass | Lounge | `GeneratePostmanCollectionLoungeEpassPaymentP*.py` |

公共实现：`generators/ft_prebooking_payment_common.py`、`prebooking_payment_category.py`、缺口 `ft_prebooking_payment_p1_gaps.py`。  
Lounge = `Generate(..., category="lounge")`（path=`lounges`、`loungeResourceId`、module=`1`）。

---

## 1. 两轴模型（先定轴，再换品类）

```text
账户轴：Membership  |  E-pass
品类轴：fastTrack   |  lounges  |  fitness  |  …
```

- **换品类**（如 FT → Lounge）：多数只改 URL path 中的 module 段、资源 ID 变量、乘客/姓名池；**支付方式矩阵与分组结构可复用**。
- **换账户轴**：造数与 ID 字段不同（`membershipId` vs `ePassId` / `availableUsages`），缺口场景也不同；应对齐同账户轴的 FT 金样例，而不是混抄。

Lounge 与 FT 的 **payment 断言逻辑相同**（差异仅 path）；见断言附文「适用范围」。

---

## 2. 生成器怎么拆（抄 FT 结构）

| 层 | FT 做法 | 新品类建议 |
|----|---------|------------|
| 公共构建 | `ft_prebooking_payment_common.py`（路径、payload、链路、精简 JS helpers） | 抽「品类参数」：`PreviewPath`/`CreatePath`、resource 变量名、默认 module 枚举、乘客名池 |
| P0 | `BuildP0PaymentFolders`：各支付方式各 1 条冒烟（MS/EP **同构**） | 同构；少负向 |
| P1 | `BuildP1PaymentFolders` + `*_p1_gaps.py` | 主轴矩阵 + Detail/不足/Preview 入参/支付链接 |
| 入口脚本 | `GeneratePostmanCollectionFt*PaymentP0/P1.py` | 新 `Generate…Lounge…` 或参数化同一 common |
| 集合产出 | `postman/collections/*.postman_collection.json` | 同上；**真相源在生成器** |

**硬约束（跨品类）**

1. 每步内联 helpers 必须精简（`_BuildFtPaymentCoreJsHelpersLines` + `CompactJsLines`），否则 Push `422001`。
2. 步骤名 `PurposeName`：`【目的】| 步骤ID | METHOD /path`。
3. 断言标题：`检查点 | 期望=… | 实际=…`。
4. payment 断言内联 `tools/apifox_payment_assert_*.js`；客户预收款用 `apifox_client_collect_assert_*.js`，**勿混用**。

---

## 3. Apifox 目录与场景内分组

### 目录（先问再 Push）

```text
{membership|epass|common} / {P0(冒烟用例)|P1（全量用例）} / {prebooking|walk-in|others}
```

新品类仍挂在 **membership 或 epass** 域下的 `prebooking`（品类体现在 path/资源，不必新造 L1 名）。

### 分组（禁止按技术步骤开夹）

| 一级（主轴） | 二级（变体） | 叶步骤 |
|--------------|--------------|--------|
| 权益支付 / 现金 / 客户预收款（+ Bundle 若 ePass） | 点数、async、正负向 | Preview→Create→…→支付→取消→详情/列表 |

横切能力（发起支付、async、取消后查询）**嵌进链路**，不单开「发起支付」「async」组。细则见 `apifox-cli-repo-first/reference.md`「场景内分组」。

---

## 4. Membership 账户轴（可迁移点）

| 主题 | FT 经验 | 扩品类注意 |
|------|---------|------------|
| 现金 | `cashPaymentApplied=false` + `DP_COLLECT`；`true+DP_COLLECT` → `500.051.023` + conflict msg；**可用性/预约统一 adultCount=3** | 同规则 |
| 预收款 | 显式 `CLIENT_COLLECT`；「只传 cashPaymentApplied」可作默认预收费变体 | 点数过大常业务拒 |
| Detail | `toUseEntitlementDetail` 与 count 一致/不一致 → `500.042.018` / `500.042.020` | 同 |
| 权益不足 | 注册后按需 ``POST /entitlements/update`` 减点（`usageRestriction` 1持卡/2guest/3共享）；再可用性 `avail+1` → 期望 `500.042.011`（沙箱亦见 `500.051.011` / `500.051.020` / Lounge `500.042.019`） | **Lounge 的 module 枚举≠2**；单池减不完且 `avail+1` 超姓名池则软跳过 |
| 冲突 true+DP_COLLECT | FT：`500.051.023`；Lounge：常 `500.042.023`（同 conflict msg） | 断言 `reject_err_codes` 两者皆可 |
| 会籍无效 | 伪造 `membershipId` | 同 |
| 刷新 | 每条支付链路前刷新 membership | 避免权益耗尽 |

路径示例（Membership）：`/v2/orders/{module}/memberships/prebooking[/preview]`。

---

## 5. E-pass 账户轴（可迁移点）

| 主题 | FT 经验 | 扩品类注意 |
|------|---------|------------|
| 现金 | 不传 `cashPaymentApplied`；`cashier.DP_COLLECT` + `toUseUsageCount`；**可用性/预约统一 adultCount=3** | 与 membership 的 false+DP_COLLECT 不同 |
| 造数 | `availableUsages`；不足 `500.042.005`（可配软跳过） | 同 |
| 客户预收款 | **ePass 无此能力**：`CLIENT_COLLECT` → conflict msg（`500.051.023`/`500.042.023`）；**勿传** `cashPaymentApplied` | Bundle 同 |
| Bundle | 纯权益成功（Create 后取消；status=9 断言取消失败文案）；**现金入参忽略成功**；预收款 conflict | 有 Bundle 的品类才加 |
| Preview 全量 | module / ePassId / token / 现金 usage+cashier / 出参；缺/空必填钉 **msg**；membership token 错配须先注册会籍再可用性 | 缺必填见 §6 |
| Program 能力 | 未开现金常 `500.051.010` → `env_reject_ok_codes` | 沙箱必查 |

路径示例：`/v2/orders/{module}/ePasses/prebooking[/preview]`。

---

## 6. 两边共用（后续品类直接抄）

### 缺必填字段

统一期望（**只断言 msg + code=-1**；errCode 可不一致）：

```json
{
  "code": -1,
  "msg": "The required parameter '{{字段名}}' is missing. Please provide a valid value."
}
```

助手：`ftPayAssertMissingRequiredParam(label, fieldName)`。

### 支付链接 `POST /v2/orders/payments`

| 覆盖 | 说明 |
|------|------|
| 缺 `orderId` / `paymentMethod` / `returnUrl` | → 固定缺参 msg（不验 errCode） |
| **不测**缺 `cancelUrl` | 非必填 |
| REDIRECT + `validUntil`、同单幂等、0 元 `802`、取消后 `803` | Membership 0 元用 `CLIENT_COLLECT`；**ePass 无预收款**，0 元用纯权益足额（payable=0→802，有预约费→REDIRECT） |
| `801`/`804` | 需 SaaS 故障注入，占位即可 |

### 定价 Environment（换场景不换脚本；品类换变量名解耦）

只测场景 **1 / 2 / 3 / 5 / 7**。同一 Apifox Environment 可同时配置 FT 与 Lounge 键：

| 语义 | FT 键名 | Lounge 键名（解耦） |
|------|---------|---------------------|
| 场景号 | `paymentSceneId` | `loungePaymentSceneId` |
| 预约费承担方 | `prebookingFeePayer` | `loungePrebookingFeePayer` |
| 预约单价 | `prebookingUnitPrice` | `loungePrebookingUnitPrice` |
| 超人次单价 | `overageUnitPrice` | `loungeOverageUnitPrice` |
| 期望报错 | `paymentSceneExpectError` | `loungePaymentSceneExpectError` |
| 金额断言开关 | `assert_payment_env_price` | `loungeAssertPaymentEnvPrice` |

- FT 默认常 scene=7（user / 8.99 / 23.67）；Lounge 默认常 scene=3（client / 0 / 17.00）。
- Auth 步将本品类键映射到规范键后再跑 E-* 断言；BOSS 改价只改对应品类键。
- 键与含义见 Membership P1 文档「单一环境定价」；品类键表见 `prebooking_payment_category.py`。

### 取消后状态

详情/列表允许 **status=3（已取消）** 或 **status=9（待支付不可取消）**。

### 可用性 token

可用性成功后在 **`pm.test` 外**立刻多作用域写入 `prebookingToken`；Preview/Create body 预置空串，由 `Prerequest_InjectPrebookingToken`（Auth 序）硬写 `extra.prebookingToken`（勿依赖 `{{prebookingToken}}` + `replaceIn`）。

### 取消失败文案（status=9）

待支付不可取消时断言 msg=`Order cancellation failed. Please try again later.`（成功取消则 `code=0`）。

### 0 元发起支付

`payableAmount=0` 或无该字段时，发起支付**必须** `errCode=500.000.802`，禁止软跳过。

### 场景结构

不再挂 `01 Setup`；Auth 后各支付链路内 `refresh_membership` / `refresh_epass` 自包含造数。

---

## 7. 新品类落地检查清单

- [ ] 已确认 Apifox 目录 L1/L2/L3，写入 `suites.yaml` + `suites/<asset>.md`
- [ ] 抄最近似 FT 资产（同账户轴优先）：生成器结构、分组、gaps
- [ ] path / `resourceId` 变量 / 乘客名池已换品类
- [ ] Membership：`moduleExclusiveEntitlements` 的 **module 枚举**已按品类改对
- [ ] E-pass：现金入参语义、Bundle 是否适用、沙箱 Program 能力（010/020 软拒）
- [ ] 缺参断言固定 msg（不验 errCode）；支付链接不测缺 `cancelUrl`
- [ ] helpers 精简，Push 无 `422001`
- [ ] `SyncCheck` 绿；`catalog.md` 有行
- [ ] 详解文档链到本文 + 实现参考 + 断言附文（勿三份抄金额公式）

### 建议命令

```powershell
# 生成 → 推送 → 跑 → triage（资产 key 自定）
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <your_asset_key>
```

---

## 8. Lounge 相对 FT 的典型 diff（示例）

| 项 | Fast Track（金样例） | Lounge（预期改动） |
|----|----------------------|--------------------|
| path module | `fastTrack` | `lounges` |
| 资源变量 | `fastTrackResourceId` 等 | `loungeResourceId` |
| `extra.passengers` | **有**（按 adult/child 同步） | **无**（仅 `prebookingRequiredInfo`） |
| Membership 权益池 `module` | `2` | `1`（Lounge） |
| payment 断言 | 共用 `apifox_payment_assert_*.js` | **通常无需改逻辑**（Lounge 默认可关 env 金额断言） |
| 场景分组 / 支付矩阵 | 见 FT P1 | **结构照抄**，改 purpose/path |

Fitness 等同理：先定账户轴金样例，再换 path 与资源，最后补品类特有负向。

---

## 9. 排障速查（下次优先对表）

> 首发于 `ft_membership_payment_p1`（2026-07-21）；**ePass 轴补强**于 `ft_epass_payment_p1`（同日晚）。  
> 改 **`generators/ft_prebooking_payment_common.py`**（及 `ft_prebooking_payment_p1_gaps.py`）后 PushSteps/SyncCheck，勿只改 Apifox UI。  
> 联调实录见 [`Apifox-CLI-Repo-First-问题回顾.md`](./Apifox-CLI-Repo-First-问题回顾.md) §11–§12。

### 9.1 症状 → 处置

| # | 症状 | 根因 | 处置（生成器） |
|---|------|------|----------------|
| 1 | status=9 取消失败文案不对 / 未断言 | 取消步只「可解析」或沿用旧文案 | `ftPayAssertCancelUsageResponse`：成功 `code=0`；失败 msg=`Order cancellation failed. Please try again later.`；无有效 `usageOrderId` 时勿硬套该文案 |
| 2 | 现金点 1 变成 1 人预约；乘客数组只有 1 人 | `AdultCountForEntitlementPoints` 按点数缩减 `adultCount` | **可用性/预约统一 `adultCount=3`**；点数只改 `toUseEntitlementCount` / `toUseEntitlementDetail`；detail 正向组命名「预约3人-…」 |
| 3 | 冲突场景只验 `code=-1`，未钉死文案 | 负向未传 `reject_err_code` / `reject_msg` | `true+DP_COLLECT` → `500.051.023`（Lounge 常 `500.042.023`）+ msg=`The specified collection method conflicts with the cash payment parameter. Please verify the request parameters.` |
| 4 | 0 元发起支付「期望=802或跳过」绿但未真验 802 | `ftPayAssertPaymentNotRequired` 在 `code=0` 时 soft skip | `payableAmount=0` **或无该字段** → 必须 `500.000.802`；缺字段按 0 记入；**禁止**软跳过 |
| 5 | 顶层仍有 `01 Setup`，与链路内注册重复 | `BuildCollection` 挂了 `BuildSetupFolder` | 只留 `00 Auth`；靠链路内 `refresh_membership` / `refresh_epass` |
| 6 | 可用性已返回 `prebookingToken`，Preview/Create 仍旧/空/`{{prebookingToken}}` | ① 集合预置空 `prebookingToken` 盖住写入；② body 写 `{{prebookingToken}}` 时 `replaceIn`/乘客同步先洗成空串；③ 只写 collection 步间丢失；④ 可用性后 `SetVar(GetVar)` 在 `pm.test` 未执行前冲空 | **禁止**集合预置空 token；body 预置 `""`；可用性 **`ftSavePrebookingToken` 在 `pm.test` 外立刻多作用域写入**；Preview/Create 末尾 `Prerequest_InjectPrebookingToken`（Auth 序读并硬写 `extra.prebookingToken`）；乘客同步勿对整包 `replaceIn`；helpers 增量须极小（防 Push `422001`） |
| 7 | 权益不足 Preview/Create 得到 `500.051.004` Invalid prebookingToken（假绿） | `avail+1` 超姓名池 → AVL 跳过无 token 仍打 Preview；断言软跳过 | 注册后 ``POST /v2/entitlements/update`` 减点（`quantity` 负；`usageRestriction` 1/2/3）；链路 `MS→DEC→AVL→PRE→CRT`；断言接受 `500.042.011`/`500.051.011`/`500.051.020`，**硬失败** `500.051.004`；无法造数才 `skipRequest` |
| 8 | `PushSteps` `ECONNRESET` 或 `422001` | 网络断连 / 每步 helpers 过大 | 重试 Push；helpers 增量极小（金样例包体约 21.2–21.4MB，勿再往每步塞大段逻辑） |
| 9 | CLI 断言表 0 失败但脚本 exit 1 | `$LASTEXITCODE` 被 `apifox run` 污染，或汇总误抬 `failed` | 以 `*-failures.json` + Apifox 断言表为准；勿仅凭脚本 exit code 判红 |
| 10 | **ePass** 客户预收款 / Bundle 预收款当正向；或带 `cashPaymentApplied:true`；**支付链接 0 元 802 误用 CLIENT_COLLECT** | ePass **无**客户预收款能力；误抄 Membership | `CLIENT_COLLECT`（含 Bundle）一律 **conflict msg**（`500.051.023`/`500.042.023`）；**勿传** `cashPaymentApplied`；现金仅 `cashier.DP_COLLECT`+`toUseUsageCount`；**PAYLNK 802** 用纯权益足额（payable=0→802，有预约费→REDIRECT） |
| 11 | Create/Bundle 断言标题「status=1 或 5」却在 `status=9` 时绿 | 脚本对 `st===9` 静默 `return`，标题撒谎 | 允许集改为 **`[1,5,9]`**，标题写清「待支付」；**禁止**静默软过 |
| 12 | Bundle 成功下单后取消无失败文案 | Bundle 取消步只「响应可解析」 | 与主链路同：`ftPayAssertCancelUsageResponse`；status=9 钉死取消失败英文 msg |
| 13 | 「ePassId 空 / 与 token 不一致」请求体仍是真 ID；负向变正向 | `ftPayResolveBodyPlaceholders` 凡见 `ePassId` 字段就用集合变量覆盖 | **仅当**当前值含 `{{` 才注入；显式 `""` / 伪造 ID **保留** |
| 14 | 「token 由 membership 可用性」用假 token 字符串 | 未真实走会籍可用性 | `MS 注册（复用 clientUserId）→ membership AVL → ePass Preview`；勿 `NewClientUserId` 冲掉 ePass 归属 |
| 15 | 缺/空必填因 `errCode`（`302.000.001` vs `302.051.001`）红 | 沙箱缺参码不统一 | `ftPayAssertMissingRequiredParam`：**只验** `code=-1` + 固定 msg；**不验** errCode。改 common 后须 Push **FT/Lounge × MS/EP P1** 全套 |

### 9.2 业务约束（勿踩）

| 约束 | 说明 |
|------|------|
| 纯权益不可「1 点约 3 人」 | 会 `500.051.011`。权益组用**足额 3 点**，用 async 有无（缺失 / `false`）区分；**点 1 放现金/预收款矩阵** |
| 权益不足链路 | `adultCount=avail+1` 可动态改写，属负向特例，不与「统一 3 人」冲突 |
| 取消级联失败 | Create 失败导致无 `usageOrderId` 时，取消步不要误报「文案不匹配」 |
| ePass ≠ Membership 预收款 | Membership 可 `CLIENT_COLLECT` / 只传 `cashPaymentApplied`；**ePass 一律 conflict** |
| `epassModule` | 集合变量=品类 module 枚举（FT=`2`，Lounge=`1`）；断言 `data.module` 与之相等，不是业务文案 |

### 9.3 Agent 自动处置清单（ePass / 缺参）

用户报 ePass Preview/Bundle/缺参类失败时，**按序执行**（勿只改 UI）：

1. 对表 **§9.1 #10–#15** 与 §5 E-pass 轴。  
2. 改 `ft_prebooking_payment_common.py` / `ft_prebooking_payment_p1_gaps.py`。  
3. 重生成并 Push（至少）：`ft_epass_payment_p1`；若动缺参助手则同步 `ft_membership_payment_p1`、`lounge_*_payment_p1`。  
4. 提醒 UI：`ai/apifox-cli-sync` + 硬刷新。

### 9.4 验收命令

```powershell
# 金样例（Membership P1）
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_membership_payment_p1

# ePass P1（本轮补强）
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset ft_epass_payment_p1

# 共用 common：FT/Lounge × Membership/E-pass × P0/P1 按需 PushSteps/SyncCheck
```

UI：分支 `ai/apifox-cli-sync`，硬刷新后验收；以 `apifox-reports/<asset>/` 最新 SyncCheck 为准。
