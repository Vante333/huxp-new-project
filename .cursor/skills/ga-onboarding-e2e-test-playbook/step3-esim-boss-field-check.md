# 需求第 3 步：eSIM 品类项目 Form → BOSS 对照

用户问「这些字段和规则怎么去平台对照」时，必须按本文教：对照地点是 **BOSS 协议 → 项目配置 →【Esim】那一条的页签**，不是 SAAS，不是 Onboarding Form 本身。

Form 只提供红字来源；BOSS 才是落库结果。先抄 Form/审核详情实际值，再打开同一环境、同一协议下的 eSIM 项目逐页对。只看、不要点保存。

## 这段 JSON 是什么

自动化第 3 步「创建品类项目」里 **eSIM（`moduleType=ISC`）** 写入 BOSS 的内容，五块对应五个页签。

BOSS 项目列表里看到 `[Lounge]` / `[Fast Track]` / `[MPV]` / `[Discount]` / `[Esim]` 多行，也是第 3 步产物。Form 上不是叫「第 3 步」，而是 Membership 下 **+ Add Entitlement**（及 Discount 模块）勾选；审核通过后才在 BOSS 落地。

| Form 勾选 | BOSS 列表常见名称 | 不要拿去对 eSIM JSON |
|-----------|-------------------|----------------------|
| Lounge | `【Lounge】…` / `BPN` | 对，那是 IL |
| Fast Track | `【Fast Track】…` | 对，那是 FT |
| MPV | `[MPV] …` / `APN` | 对，那是 MPV |
| Discount | `[Discount] …` | 对，Discount 模块 |
| **eSIM** | **`【Esim】{{ProgramName}}`** | **只对这一行** |

没有 Lounge-Topup 项目 = Form 里 Topup=No，正常。

## 进 BOSS 怎么点

1. 打开 **和 Form 同一环境** 的 BOSS（Test 对 Test，禁止用 UAT 对 Test）。
2. 搜这份协议 `agreementCode`。
3. 协议页 → **项目配置**。
4. 点名称 `【Esim】` + Form Program Name 的那一行（编辑/详情）。
5. 按页签对照，不要打开 Lounge 行去对下面的 JSON。

| JSON 段 | BOSS 页签 |
|---------|-----------|
| `basicInformation` | **基本信息** |
| `moduleRules` | **品类规则** |
| `networkPriceTemplateConfiguration` | **网络配置 / 网络范围** |
| `settlementConfiguration` | **结算配置**（可能另有价格/跟随模板） |
| `transactionConfiguration` | **交易配置** |

## 环境品类码（禁止抄生产到 Test）

| 环境 | `moduleSubType` | `moduleName` |
|------|-----------------|--------------|
| Test | `ISC00270` | `mai-Sim品类` |
| UAT | `ISC00001` | `国际通用卡券eSim` |
| 生产 | `ISC00000` | `国际通用卡券eSim` |

## 写入 Body 模板（对照用，注释勿发给接口）

```json
{
  "basicInformation": {
    "agreementCode": "{{agreementCode}}",
    "projectName": "【Esim】{{ProgramName}}",
    "startDate": "{{StartDate}}",
    "endDate": "{{EndDate}}",
    "businessType": "equity",
    "business": "agreement",
    "moduleType": "ISC",
    "moduleSubType": "{{见环境表}}",
    "moduleName": "{{见环境表}}",
    "renewalFollowAgreementDate": true,
    "status": "1",
    "note": ""
  },
  "moduleRules": {
    "finishRule": "used",
    "cancelLimitType": ["time", "status"],
    "cancelLimitTimeUnit": "{{Cancellation Rule 单位 hour/day}}",
    "cancelLimitTime": "{{Cancellation Rule 数字}}",
    "cancelStatusLimit": ["unfinished"],
    "cancelDependsSupplier": 1,
    "equityOrderInterval": "{{EntitlementOrderLimit.enabled ? value : 空或默认}}",
    "equityOrderIntervalUnit": "{{EntitlementOrderLimit.enabled ? unit : 空或默认}}"
  },
  "networkPriceTemplateConfiguration": {
    "templateCode": "{{NetworkType == Standard Network ? StandardNetwork : 待产品提供}}"
  },
  "settlementConfiguration": {
    "erpSettlementCode": "",
    "taxRate": "{{TaxTreatment：不含税=0，含税=用户输入}}",
    "settlementTime": "ServiceTime",
    "pricingDimension": "{{ClientCode}}",
    "customerPriceTaxInclusive": "{{TaxTreatment.isInclusive}}",
    "userPriceTaxInclusive": "{{TaxTreatment.isInclusive}}"
  },
  "transactionConfiguration": {
    "paymentMode": "PAYG",
    "paymentMethod": "COF",
    "paymentGateway": "Ingenico"
  }
}
```

## 基本信息

| JSON | BOSS | 判对 |
|------|------|------|
| `projectName` | 项目名称 | `【Esim】` + Form Program Name |
| `startDate` / `endDate` | 开始/结束 | Form StartDate / EndDate |
| `businessType=equity` | 业务类型 | 权益 |
| `moduleType=ISC` | 品类/模块 | eSIM |
| `moduleSubType` / `moduleName` | 品类编码、名称 | 按上表环境，Test 必须 `ISC00270` / `mai-Sim品类` |
| `renewalFollowAgreementDate=true` | 跟随协议续期 | 是 |
| `status=1` | 状态 | 在用 |

## 品类规则（eSIM 重点，不是 Lounge 预约抽查）

先从 Form **Entitlement（eSIM 那条）** 抄 Cancellation Rule、Entitlement Order Limit。

| JSON / 需求表 | 写入规则 | Form | BOSS 品类规则 |
|---------------|----------|------|----------------|
| 订单完成规则 `finishRule=used` | 系统默认 | — | **确认使用时完成** |
| 订单取消规则 | 系统默认 | — | **按时间限制 + 按状态限制** |
| `cancelLimitTime` + Unit | 取 Form | **Entitlement → Cancellation Rule**（24h / 48h / 7days） | **取消时间限制** 数字+单位一致。`24 hour` ≠ `24 天` |
| `cancelStatusLimit=unfinished` | 系统默认 | — | **未完成** |
| `equityOrderInterval` + Unit | 取 Form | **Entitlement → Entitlement Order Limit** | 开关开了：值和单位与 Form 一致；没开：不应乱填 XX |
| 提示规则 / 下单资料表单 | `-` | — | 空或默认即可，不当必填 |

## 网络配置

| JSON | 规则 | BOSS |
|------|------|------|
| `templateCode` | Network Type = Standard Network | 绑的模板编码 = Form 选中那条的编码 |
| Custom / 非标 | 待产品提供 | 有值记下给产品；没有不当 Standard 用例失败 |

不要把 Lounge 的 `BOSS_T000718` 直接当成 eSIM 已对上。以 **本条 eSIM 项目页** 实际模板为准。

### Form 显示名 vs BOSS 显示名（禁止只看中文名）

实测常见：Form 下拉是 **`【Esim】DP APP Default Esim`**，BOSS 网络/结算页显示成 **`【Esim】GA Default…`**（带 `T0007…` 一类编码）。**显示名不同不能直接报缺陷，也不能直接算通过。** 对照的是 `templateCode`，不是下拉文案。

**对照入口（必须走到这一步）：**

1. BOSS 打开本条 eSIM 项目（项目查询用执行页的 `APN…`，不要打开别的协议下的 `[Esim]`）。
2. 点 **查看** 或 **编辑**（不要点价格计划、权益购买配置）。
3. 页签点 **网络范围配置**（结算页若也绑了价格模板，同样处理）。
4. 确认配置模式是 **关联网络模板**（对应 Form Standard Network）。
5. 点模板右侧蓝色 **「查看模板基础信息」**。
6. 弹窗里抄 **模板编码** + **模板全称**。不要只抄项目页下拉那一行短名。
7. 回 Form / 审核详情，对照当时选中的那条网络（编码若 Form 上看不到，以下拉全称+编码两边都记）。

**判定：**

| 条件 | 结论 | 怎么写 |
|------|------|--------|
| 模板编码相同（全称可视为同一条） | **通过** | Form 显示 `DP APP Default Esim`、BOSS 显示 `GA Default` 只是别名/截断，不算错 |
| 模板编码不同，或全称明显不是 Form 选中那条 | **缺陷** | 标题：eSIM Standard Network 未按 Form 选中模板写入 BOSS。步骤：Form 选 A，BOSS 项目 `APN…` → 网络范围 → 查看模板基础信息得到编码 B。期望：B=A。实际：B≠A。 |
| 未点「查看模板基础信息」，只看了下拉短名 | **对照未完成** | 禁止下结论、禁止报缺陷 |

结算页价格模板同样：不要用「GA Default」短名结案，点 **查看模板基础信息** 对编码。本页结算类型/时间为空时，先看价格模板内容，不要在项目页手填后保存。

「请尽快维护并完善」是模板适用范围提示，不是 Form 填错，对照时只记模板编码。

## 结算配置

先抄 Form **Client Info**：Tax Treatment、Settlement Currency、Client Code；再抄该 eSIM **Entitlement → Pricing Model**。

| JSON / 需求表 | Form | BOSS 结算页 |
|---------------|------|-------------|
| ERP 结算编号 | 空 / null | 空 |
| `taxRate` | Tax Treatment | **不含税 → 0**；**含税 → 用户输入的税率** |
| 结算类型 | 默认 / 跟随模板 | **使用即结算** |
| 结算时间 `ServiceTime` | 默认 | **服务时间** |
| 交易币种 | Settlement Currency | 与 Form 币种一致 |
| 定价模式 | 默认 | **标准模式** |
| 使用模板 | Pricing Model | Standard Price → **是**；Custom Price → **否** |
| 选择模板 | Standard Price 选中的价格模板 | 显示 Form 选中那套（「发卡行」是一种类型，以实际名为准） |
| 定价维度 | Client Code | 等于客户编码 |
| 客户/用户定价是否含税 | Tax Treatment | 两者必须相同，且与 Form 含税/不含税一致 |

「跟随模板」页：税率、含税仍跟 Tax Treatment；币种等可跟价格模板。**以本条 eSIM 结算页为准**，不要和 Lounge 结算混看。

## 交易配置（不跟 Form，写死）

| JSON | BOSS 必须是 |
|------|-------------|
| `paymentMode=PAYG` | 付费模式 PAYG |
| `paymentMethod=COF` | 支付方式 COF |
| `paymentGateway=Ingenico` | 支付网关 Ingenico |

任一不符即缺陷，与 Form 无关。

## 建议对照顺序

1. Form/审核详情抄：Program Name、日期、Cancellation Rule、Order Limit、Tax Treatment、**选中的网络模板全称**。
2. BOSS 用执行页 `APN…` 打开本条 `【Esim】` 项目，不要打开其它协议的 eSIM。
3. 基本信息（名称 + 环境品类码）→ 品类规则（取消时限、下单间隔）→ **网络：点「查看模板基础信息」对编码** → 结算（税率、含税、币种、价格模板编码）→ 交易（PAYG/COF/Ingenico）。

## 正常 / 异常 / 边界

- 正常：勾 eSIM + Standard Network + 不含税 + 取消规则有值 → 第 3 步成功后五页签全对，状态在用。
- 异常：没勾 eSIM 却出现 `【Esim】`；Cancellation 空却乱填；Custom Network 当接口失败；Test 写成 `ISC00000`。
- 边界：24h / 48h / 7days 单位；Order Limit 关 vs 开；不含税税率必须是 0，不能残留上次 6%/13%。

## 接口侧（可选）

页面核对即可。有 VPN 时查项目详情，对同一批字段；不要用 SAAS 权益接口对这五块。eSIM 权益/核销商品必须绑本条项目，禁止绑旧 Lounge `BPN`。

## 新人易漏

1. 拿 Lounge 项目页对 eSIM JSON。
2. 用生产/UAT 品类名对 Test（Test = `ISC00270` / `mai-Sim品类`）。
3. 只看项目建出来，不对 Cancellation Rule 的数字和单位。
4. 不含税时 BOSS 税率不是 0。
5. Order Limit 未开，BOSS 却有随意间隔。
6. 在结算页点了保存，改掉自动化结果。
7. 网络「待产品提供」当成接口失败。
8. 把 BOSS 项目列表当成 Form 某一页；列表是自动化第 3 步，Form 上是勾品类。
9. Form 是 `DP APP Default Esim`、BOSS 是 `GA Default` 就直接报缺陷或直接通过。必须进 **查看模板基础信息** 对 `templateCode`。
