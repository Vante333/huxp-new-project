# 二期 Generic API 自动化配置补充需求

> 来源：桌面 `二期Generic API自动化配置补充需求-2.pdf`（31 页）  
> 工作区副本：`需求文档/二期Generic API自动化配置补充需求-2.pdf`  
> DEMO：https://onboarding-flow-buddy-91.lovable.app  
> Jira（群公告）：https://dragonpass.atlassian.net/browse/ECS-373

本文把 PDF 抽成可检索文本，方便对照 BOSS/SAAS 落库。截图页以 PDF 为准。

---

## 和一期的关系（人话）

一期已经能在 Form 上收集全部品类，但**自动化只真正配通 Lounge / Fast Track / SetMeal**。

二期要在现有 Form 字段上，把下面能力自动打到 BOSS + SAAS：

| 品类 | 二期要自动完成 |
|------|----------------|
| **ESIM** | BOSS 品类项目 + SAAS 权益 + 会籍 + **核销商品** |
| **Fitness** | BOSS 品类项目 + SAAS 权益 + 会籍 + **预约商品** |
| **MPV** | BOSS 品类项目 + SAAS 权益 + 会籍（补一期没配完的） |
| **Swap** | Lounge+SetMeal+MPV 或 Lounge+MPV 组合共用点数：权益模板只建 **1 份**，组合内各品类项目仍要 **分别建** |

另外两块：

1. Review 支持 **新建 / 复用协议**、**新建 / 复用租户**（交互对齐 DP APP）
2. Lounge 的 Pricing Model；Others 后增加 Upload File（对齐 DP APP）

---

## 一、BOSS Step 3：品类项目 `POST /api/project/batchAdd`

### 1.1 ESIM（`moduleType=ISC`）

**项目名称：** `【Esim】{{ProgramName}}`

| 环境 | moduleSubType | moduleName |
|------|---------------|------------|
| 生产 | `ISC00000` | 国际通用卡券eSim |
| UAT | `ISC00001` | 国际通用卡券eSim |
| Test | `ISC00270` | mai-Sim品类 |

**品类规则**

| 字段 | 规则 |
|------|------|
| 订单完成 | 固定：确认使用时完成 `finishRule=used` |
| 订单取消 | 固定：按时间 + 按状态 |
| 取消时间 | Form → Entitlement → Cancellation Rule（1天/3天/7天） |
| 取消状态 | 固定：未完成 |
| 下单间隔 | Form → Entitlement Order Limit（关了则按文档占位） |
| 网络模板 | Standard Network 取 Form 选中项；编码待产品提供 |
| 税率 | Tax Treatment：不含税=0，含税=用户输入 |
| 定价维度 | Client Code |
| 含税 | 客户/用户定价是否含税都跟 Tax Treatment |
| 交易配置 | **PAYG / COF / Ingenico**（系统默认，不跟 Form） |

JSON 要点：`businessType=equity`，`business=agreement`，`renewalFollowAgreementDate=true`，`status=1`。

### 1.2 Fitness（`moduleType=IGC`）

**项目名称：** `【Fitness】{{ProgramName}}`

| 环境 | moduleSubType | moduleName |
|------|---------------|------------|
| 生产 | `IGC00003` | BOSS2.0标准健身房服务 |
| UAT | `IGC00005` | BODDY Gym |
| Test | `IGC00013` | 樊测试BODDY服务类目合并 |

JSON 示例里的 `IGC00002` 与环境表不一致，**对照以环境表为准**。

**品类规则**

| 字段 | 规则 |
|------|------|
| 退订 | 固定：允许 |
| 取消时间 | Form Cancellation Rule：`24 hours before Service Time` 或 `One day before Service Date` |
| 取消状态 | 待确认 / 待使用 |
| 下单间隔 | Entitlement Order Limit |
| 网络模板 | 默认 `BOSS_T000727` |
| 税率 | 固定 0 |
| 币种 | Settlement Currency |
| 交易 | PAYG / COF / Ingenico；超人次 false；信用卡核销 false |

跟随协议续期：需先问 AM，不确定先选是。

### 1.3 MPV（`moduleType=NPMPV`）

**项目名称：** `【MPV】{{ProgramName}}`

| 环境 | moduleSubType | moduleName |
|------|---------------|------------|
| 生产 | `NPMPV00029` | BOSS2.0标准餐厅MPV |
| UAT | `NPMPV00028` | 新平台MVPPCS |
| Test | `NPMPV00031` | 2.0mpv品类lz |

**品类规则（Advanced Rules）**

| 字段 | Form 来源 |
|------|-----------|
| 实名 | Real Name：实名 / 校验凭证姓名 / 非实名 |
| 核销间隔 | Verification + 分钟 |
| 携伴 | Accompany + 人数 |
| 扣点 | 固定统一扣点 1 点 |
| 网络 | 同 Lounge，标准模板待提供 |
| 交易 | 支持超人次=否；信用卡核销=不支持 |

---

## 二、SAAS

### 2.1 创建权益 Step 5

接口：`POST /api/tenant/global/equity/equity/add`  
上架：`/api/tenant/equity/equity/updateStatus`（`equityStatus=2`）

补充规则：

1. Single 的 Esim / Fitness / MPV：有则建大客户权益；该品类 Topup 开了再加充值权益
2. Swap（Lounge+SetMeal+MPV 或 Lounge+MPV）：只建 **1 条** Swap 权益模板，`isCombine=true`

**权益命名**

- Single：`【品类】ProgramName-Epass/Membership-Cardhold{X}-Guest{Y}` 或 `-Share{Z}`
- Swap：`【Swap-品类1&品类2】ProgramName-...`
- Topup：`【品类 Topup】ProgramName-membership`

**Swap 选品类项目**

| Swap 组合 | 权益模板绑定的品类项目 |
|-----------|------------------------|
| Lounge+SetMeal | 只选 Lounge 一个 |
| Lounge+SetMeal+MPV | Lounge + MPV 两个 |
| Lounge+MPV | Lounge + MPV 两个 |

标签：Lounge+Setmeal（或再加 MPV）勾 Swap；有 SetMeal 勾 SetMeal；Topup 勾充值。

关键字段：`equityExpirationType=6`；Epass `isShare=true`；Membership 从 Form Entitlement Share 取值；`isInfinite` / `equityNum` 仅共享时传（**epass 不传 isInfinite**）。

### 2.2 创建会籍 Step 6

接口：`/api/tenant/member/memberShipTemplate/saveOrUpdate`

| | ePASS | Membership |
|--|-------|------------|
| 模板数量 | **每个品类 1 个** | **全单只有 1 个** |
| 绑权益 | 只绑该品类 1 个权益 | 绑全部大客户权益 + Topup 权益 |
| 名称 | `DP API-Epass-品类-ProgramName` | `DP API-Membership-ProgramName` |
| 标签 | 选 E-pass | 不选 |
| 会籍商品 Step 7 | 每品类 1 个会籍商品 | **不配会籍商品** |

其它固定：国际会籍码 DAMM；固定时长 12 个月；自动启用开；预制会籍关；删除后再注册=重发初始权益。

### 2.3 预约 / 核销商品 Step 8

- **Fitness → 预约商品**（名称 `【品类项目】ProgramName`，机场服务，支持权益兑换，价格由项目配置）
- **eSIM → 核销商品** `POST /api/tenant/qr/v2/product/add`  
  类目「卡券」；有效期自购买 0 天后生效、9999999 年；然后 `batchUpdateStatus` 上架

PDF 里预约商品接口路径写成了会籍 `saveOrUpdate`，对照时以实际商品接口为准，不要照抄错路径。

### 2.4 接口权限与凭证 Step 9

- ePASS：`/api/tenant/sys/program/saveOrUpdate`，`programConfigObj` 增加：
  - `esimsProCode` / `fitnessProCode` / `diningCouponProCode`（MPV）
- Membership：`saveOrUpdateBatch`，无变动，仍是 `membershipTemplateCodeList`
- 权限：`updateGroupConfigInfo`；publicKey=1；QPS=200；ePASS 勾对应品类产品包；Membership 勾 Membership 基准

### 2.5 Agent Portal Step 10

步骤名：Enable Agent Portal Permission  
PRD：https://dragonpass.atlassian.net/browse/SSAP20-123

---

## 三、新建 / 复用协议与租户

交互对齐 DP APP，在 Review Detail 的 Create Agreement 步骤：

| 选项 | 行为 |
|------|------|
| Create New Agreement | 按 Form 生成，运营可编辑，审核通过调 BOSS 创建协议 |
| Use Existing Agreement | 只填 Agreement Code，**不调创建协议接口**，后续用该编码 |
| Create New Tenant | 可编辑租户名称、所属区域，审核通过调 SAAS 创建 |
| Use Existing Tenant | 只填 Tenant Code，不调创建；名称/区域可自定义 |

规则：

1. New → 展示完整编辑区；Existing → 只展示编码输入和校验，无完整编辑区
2. 本步未导入或失败 → 可编辑再执行
3. 本步成功 → **锁定不可改**

---

## 四、其它交互

1. Lounge 的 Pricing Model 要支持
2. Others 后面增加 Upload File，逻辑参考 DP APP

---

## 测试时禁止串环境的品类码

| 品类 | Test | UAT | 生产 |
|------|------|-----|------|
| eSIM | ISC00270 / mai-Sim品类 | ISC00001 | ISC00000 |
| Fitness | IGC00013 | IGC00005 / BODDY Gym | IGC00003 |
| MPV | NPMPV00031 | NPMPV00028 | NPMPV00029 |

交易配置对照：BOSS 交易页 **PAYG / COF / Ingenico** 有值才算 Step 3 交易传参成功。
