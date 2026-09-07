---
name: ga-onboarding-e2e-test-playbook
description: GA自动化配置端到端接口测试Playbook。覆盖BOSS+SAAS冒烟、eSIM Form到BOSS对照、有问题项的查找入口与缺陷描述模板（网络模板、下单间隔、第9步商品编码0）。当用户跑GA onboarding、问对照入口在哪、Form选DP APP Default但BOSS是GA Default、怎么写缺陷、核销商品Product Code为0、或问今天测到了哪些需求要点时使用。
version: 1.5.0
---

# GA 自动化配置端到端接口测试 Playbook

## 讲解粒度（强制）

用户原话：「你这样说的太模糊了不够详细请你说的在详细一点好嘛？」

本 Playbook 面向测试新人。教任何一步时必须写清：打开哪个 Apifox 项目、环境名、前置 URI、接口树点哪、URL 栏只留哪一段、Headers 每一行（BOSS 签名 / `platform-token` / `tenant-token` 不可混）、Body 从哪抄、成功抄哪个返回字段。禁止只丢路径和 JSON。需求第 1 步逐点击见 [step1-create-agreement.md](step1-create-agreement.md)。eSIM 品类项目字段怎么在 BOSS 对照见 [step3-esim-boss-field-check.md](step3-esim-boss-field-check.md)。eSIM 有问题项的菜单入口和缺陷描述模板见 [esim-defect-entry-and-bug-template.md](esim-defect-entry-and-bug-template.md)。用户要求只报问题时：跳过已通过对项，每条写清入口+步骤+可粘贴的缺陷描述。

用户原话：「需求里面接口要求的是对内容参数需要的对应的值是不是要求的值没有错乱现象」

冒烟结束后必须按 [param-mapping-and-progress.md](param-mapping-and-progress.md) 做参数对应核对：上下游编码是否同一套、有没有把 `BZ000409`/`214` 和新建协议/`215` 写进同一条请求。禁止只说「测过了」。

## 适用场景

- 新人首次跑通 GA（Global Access）自动化配置全链路冒烟测试
- 需要从零串联 BOSS 6 步 + SAAS 5 步完整业务流程
- 验证接口连通性和基本数据流转
- 拿 eSIM 品类 JSON / 需求字段表，去 BOSS 项目页签对照 Form 填写值
- 问 eSIM 对照入口、怎么提缺陷、第 9 步商品编码为 0

本 Playbook 是"固定剧本"——所有 Body 模板、枚举值、环境地址均经过实际验证，按顺序执行即可跑通。

## 前置条件检查清单

执行前逐项确认：

1. ✅ Apifox 客户端已安装并登录
2. ✅ BOSS 项目已创建，环境已配置（见下方固定数据表）
3. ✅ SHA256 签名前置脚本已粘贴（详见技能 `apifox-api-debug-guide` 第二步）
4. ✅ Headers 已配置：appId={{appId}}、timestamp={{timestamp}}、signature={{signature}}、Content-Type=application/json
5. ✅ **VPN 已连接**（Step 6 BOSS 2.0 IL 模块必须走内网，`svc.dragon` 域名公网无法解析）
6. ✅ SAAS IAM Token 已获取（Step 7-11 需要 Bearer Token）

## 固定参考数据表

| 项目 | 值 | 备注 |
|------|------|------|
| BOSS 1.0 网关（Step 1-5） | `https://business-finance-gateway-test.dragonpass.com.cn` | 公网可达 |
| BOSS 2.0 IL 内网（Step 6） | `http://agent-salespolicy-service.restful-service.svc.dragon` | 需 VPN/内网 |
| SAAS 域名（Step 7-11） | `https://quanyi-intl-test.dragonpass.com.cn` | 公网可达 |
| IAM 登录页 | `https://iam-test.dragonpass.com.cn/#/login?system=saas-platform` | 浏览器登录取 Token |
| BOSS appId | `fanwei-test` | 测试环境固定 |
| BOSS appkey | `123456` | 测试环境固定 |
| 操作人工号 | `DP0312` | userCode/operater/creator 统一用 |
| SAAS 登录账号 | `DP001224` / `dp123456` | 用户名/密码 |
| 测试协议编码 | `BZ000409` | 已存在可复用 |
| 测试客户编码 | `DPC000547` | 已存在可复用 |
| 环境编码 | `TM001303` | 会员优惠券规则用 |
| 品类编码（Lounge） | `IL` | productInfoCode 固定值 |

## BOSS 侧 6 步

### Step 1: 获取合同编号

**Endpoint**: `POST /supplierCenter/supplier/base/contract/getContractCode`
**环境**: BOSS 1.0 网关

```json
{
    "contractType": 0,
    "companyCode": "A001"
}
```

- `contractType`: 0=新签, 1=续签（续签需 relatedCode 指向主合同）
- 返回值: `code` 字段 → 记为 `{contractCode}`，如 `A001-2026-00219`

### Step 2: 客户同步

**Endpoint**: `POST /salesCenter/saleForceAddOrUpdate`
**环境**: BOSS 1.0 网关

```json
{
    "baseInfo": {
        "sfCode": "SF-NEWBIE-TEST-001",
        "name": "新人测试客户001",
        "customerType": "1",
        "status": "1",
        "country": "CN",
        "province": "上海",
        "city": "上海",
        "address": "测试地址",
        "operater": "DP0312"
    },
    "acctInfoList": [],
    "cusInfoContactInfo": [],
    "invoiceInfo": {}
}
```

- `sfCode` 和 `name` 必须唯一，重复会报业务错误（加后缀 002/003 解决）
- 返回值: `code` 字段 → 记为 `{customerCode}`，如 `DPC000594`

### Step 3: 合同同步

**Endpoint**: `POST /salesCenter/v1/itdContractSale/saleForceAddOrUpdate`
**环境**: BOSS 1.0 网关

```json
{
    "cusCode": "{customerCode}",
    "contractCode": "{contractCode}",
    "contractName": "新人测试合同001",
    "contractType": "0",
    "startDate": "2026-08-17",
    "endDate": "2027-08-16",
    "status": "1",
    "operater": "DP0312"
}
```

- `cusCode` 填 Step 2 返回的 customerCode
- 返回值: `code` 字段 → 记为 `{contractSaleCode}`，如 `A014-XS-2026-000467`

### Step 4: 创建 Agreement

> 需求文档「调用接口」第 1 步 = 本步。逐点击说明（打开哪个项目、点哪个标签、Headers 每一行）见 [step1-create-agreement.md](step1-create-agreement.md)。禁止只丢路径和 JSON。

**Endpoint**: `POST /salesCenter/api/v1/agreement/add`
**环境**: BOSS 1.0 网关

```json
{
    "customerCode": "{customerCode}",
    "contractCode": "{contractSaleCode}",
    "agreementName": "测试协议001",
    "agreementType": "standard",
    "beginDate": "2026-08-17",
    "endDate": "2027-08-16",
    "expender": "DP0312",
    "profitCode": "DP086",
    "autoRenewal": "Y",
    "agreementCompany": "A014",
    "status": "0",
    "businessOwner": "international",
    "businessMode": "b2b",
    "salesType": "b2b",
    "remark": "test",
    "operater": "DP0312"
}
```

**⚠️ 已知枚举陷阱：**

| 字段 | 错误写法 | 正确写法 | 报错信息 |
|------|----------|----------|----------|
| profitCode | `A014`（公司编码） | `DP086`（部门ID） | "利润中心需为龙腾在用部门" |
| businessOwner | `DP0312`（工号） | `international` 或 `domestic` | Err000019「业务归属字段为非法字段,请使用可用枚举」 |
| businessMode | `domestic` / `international` | `b2b` | 不要把业务归属的枚举填到这一列 |

- `agreementType` 枚举：`standard` / `framework` / `generic`
- 返回值: `agreementCode` → 记为 `{agreementCode}`，如 `BZ000410`
- **冒烟可跳过此步**：直接复用已存在的 `BZ000409`

### Step 5: 创建会员优惠券规则

**Endpoint**: `POST /salesCenter/api/v1/memberCouponRule/add`（路径以实际文档为准）
**环境**: BOSS 1.0 网关

依赖数据：
- agreementCode: `BZ000409`（或 Step 4 返回值）
- customerCode: `DPC000547`（或 Step 2 返回值）
- 环境编码: `TM001303`

具体 Body 需参照接口文档填充，核心是上述三个固定编码正确即可跑通。

### Step 6: BOSS 2.0 IL 项目配置（6 个子接口）

**⚠️ 网络前置**：此步全部走 K8s 内网，必须确认 VPN 已连接，`nslookup agent-salespolicy-service.restful-service.svc.dragon` 能解析出 IP。

**环境**: `http://agent-salespolicy-service.restful-service.svc.dragon`
**认证**: 与 BOSS 1.0 相同的 SHA256 签名（appId=fanwei-test, appkey=123456）

#### 6.1 项目基本信息保存

`POST /api/IL/project/create-project-info` → 返回 `projectId` + `projectCode`

```json
{
    "reqId": "TEST-NEWBIE-PRJ-001",
    "userCode": "DP0312",
    "agreementCode": "BZ000409",
    "projectName": "新人测试Lounge项目001",
    "startDate": "2026-08-17",
    "endDate": "2027-08-16",
    "businessType": "equity",
    "businessWay": "agreement",
    "productInfoCode": "IL",
    "isFollowAgreementRenewal": "N",
    "monitorSupplierFlag": "N",
    "projectStatus": "1",
    "remark": "newbie test"
}
```

- `reqId`: 幂等控制，每次请求需唯一
- `isFollowAgreementRenewal`: 必填，Y/N
- 返回的 `projectId` 后续 5 步全部要用，**务必记录**

#### 6.2 品类规则保存

`POST /api/IL/project/save-rule-config` → 返回 `ruleConfigId`

```json
{
    "userCode": "DP0312",
    "projectId": "{6.1返回的projectId}",
    "reserveRule": "N",
    "realNameRule": "1",
    "writeOffGapType": "CustomInterval",
    "writeOffGapMinutes": 30,
    "carryRuleInfoList": [
        {
            "loungeType": "IL",
            "carryRuleType": "NoLimit",
            "number": "0"
        }
    ]
}
```

#### 6.3 网络范围保存

`POST /api/IL/project/save-network-range` → 返回 `networkRangeId`

```json
{
    "userCode": "DP0312",
    "projectId": "{6.1返回的projectId}",
    "networkTemplateCode": "{需从网络模板列表接口获取}"
}
```

- `networkTemplateCode` 需先调网络模板查询接口获取，或使用项目组提供的已有模板编码

#### 6.4 结算配置保存

`POST /api/IL/project/save-settlement-config` → 返回 `settlementConfigId`

```json
{
    "userCode": "DP0312",
    "projectId": "{6.1返回的projectId}",
    "priceTemplateCode": "{需从价格模板列表接口获取}",
    "erpSettlementCode": "",
    "taxRate": "0",
    "settlementTimeType": "monthly",
    "customerPriceContainTax": "N",
    "userPriceContainTax": "N",
    "priceDimensionConfig": "DPC000547"
}
```

- `priceTemplateCode` 需先调价格模板查询接口获取

#### 6.5 交易配置保存

`POST /api/IL/project/trade-config` → 返回 `tradeConfigId`

```json
{
    "userCode": "DP0312",
    "projectId": "{6.1返回的projectId}",
    "supportOverPeople": "N",
    "supportCreditCardWriteOff": "N",
    "transactionMode": "online"
}
```

- `supportCreditCardWriteOff`: 必填

#### 6.6 项目详情查询（验证）

`POST /api/IL/project/detail`

```json
{
    "projectCode": "{6.1返回的projectCode}"
}
```

- 用于验证 6.1-6.5 数据是否全部落库成功

## SAAS 侧 5 步

**认证方式**：Bearer Token（非 SHA256 签名）
**环境**: `https://quanyi-intl-test.dragonpass.com.cn`
**Headers**: `Authorization: Bearer {token}`, `Content-Type: application/json`

Token 获取方式：浏览器访问 `https://iam-test.dragonpass.com.cn/#/login?system=saas-platform`，用 `DP001224/dp123456` 登录后 F12 → Network 提取 token。

### Step 7: SAAS 租户协议关联

通常由 BOSS→SAAS 后台自动同步。手动验证方式：在 SAAS 后台「协议管理」页面确认 `BZ000409` 是否已同步。若未同步，需调用协议关联接口手动触发。

### Step 8: SAAS 创建权益

**主接口**: `api-3486610`（租户-权益管理 [新增--]）

辅助下拉接口（新增前调用获取有效选项）：
- `api-3487999` — 结算方下拉V2
- `api-3487997` — 分组下拉
- `api-3488002` — 最高覆盖等级下拉
- `api-3498958` — 根据项目ID获取可用车型（礼宾车权益时使用）

备选路径：若从模板复制 → 使用 `api-3500501`（租户-国际权益管理 [复制模板]）

### Step 9: SAAS 创建会员模板

**主接口**: `api-3492129`（会员会籍管理(国际) [创建会员会籍]）

备选：`api-3492299`（预制会籍-新增预制会籍）

辅助下拉：
- `api-3500522` — 会籍模板码下拉
- `api-3483096` — 会籍状态下拉

### Step 10: SAAS 创建产品

根据商品类型选择接口：

| 类型 | 接口 |
|------|------|
| 核销类商品（休息室、礼宾车等） | `api-3502967`（租户-商品管理 [新增商品-]） |
| v2 核销商品 | `api-3482738`（v2核销-商品管理 [新增商品-]） |
| 会籍类商品 | 会籍商品-商品管理下的新增接口 |

辅助接口：
- `api-3502978` — 本规格-是品类的规格
- `api-3502980` — 网络分组下拉
- `api-3502979` — 获取boss的规格详情
- `api-3482558` — 品类项目分页
- `api-3511030` — 品类项目详情

### Step 11: SAAS 创建续期计划并启用

**两步操作**：

1. 新增计划：`api-3482673`（权益任务计划接口 [新增V2]）
2. 启用计划：`api-3500514`（权益任务计划接口 [启用]）

辅助下拉（新增前必调）：
- `api-3500518` — 权益模板编码下拉
- `api-3500519` — 操作类型下拉
- `api-3500520` — job类型下拉（值：`once`/`day` 等）
- `api-3500521` — 执行周期下拉
- `api-3500523` — 计划类型
- `api-3500524` — 时区下拉
- `api-3483418` — 权益状态下拉

验证：`api-3491396`（执行单个任务）— 手动触发验证是否生效

## 已知踩坑总结

1. **businessOwner vs businessMode**：`businessOwner` 只能 `international`/`domestic`。填工号 `DP0312` 报 Err000019「业务归属字段为非法字段」。`businessMode` 才是 `b2b`。
2. **profitCode**：必须部门 ID（如 `DP086`），不能填公司编码 `A014`。
3. **创建协议路径**：`POST /salesCenter/api/v1/agreement/add`。手册旧路径 `/supplierCenter/supplier/base/agreement/add` 在 TEST 是 Spring 404。
4. **operater**：少一个 a，不要写成 `operator`。
5. **BOSS 2.0 IL 与 FAQ bind 需 VPN**：`svc.dragon` 公网无法解析。FAQ 为 `POST /api/project/contentPackage/bind`，host `products-service.restful-service.svc.dragon`。
6. **SAAS 两个 Token**：`/api/platform/...` 用 `platform-token`（停在租户选择页）；`/api/tenant/...` 用 `tenant-token`（进 1276 后）。只写 `Authorization: Bearer` 会报对应 token cannot be empty。
7. **绑租户 edit 整表覆盖**：必须带齐 get 返回的全部 `tenantApplicationAgReqList` 再追加。只传 `{id:27}` 或只传新协议会冲掉已有协议。
8. **会籍前权益必须已上架**：否则 `membership-template-equity-not-available-state`。
9. **预约商品**：TEST 上 `getSkuInfo` 两条路径均 404。从同项目已有商品 `getDetail` 抄 `entryId`。add 需 `productType=8`、`exchangeType=3`（权益）、`entryIdList` 非空，否则可能只返回「系统繁忙」。
10. **第 8 步 ≠ 第 9 步**：预约商品已测不算 Topup 权益商品已测。
11. **URL 前缀不要重复**；**reqId 必须唯一**；Agreement 日期字段是 `beginDate`/`endDate`。
12. **eSIM 品类对照点错行**：JSON 的 `moduleType=ISC` 必须打开 `【Esim】` 项目，禁止用 Lounge（`IL`）页对取消规则/结算。Test 品类码是 `ISC00270` / `mai-Sim品类`，不是生产 `ISC00000`。Cancellation Rule、Entitlement Order Limit、Tax Treatment、**网络模板编码** 的对照步骤见 [step3-esim-boss-field-check.md](step3-esim-boss-field-check.md)。
13. **网络模板不要对显示名**：Form `DP APP Default Esim` 与 BOSS `GA Default` 短名不同时，入口是项目 **网络范围配置 → 查看模板基础信息**，对 `templateCode`。编码相同才通过；编码不同才报缺陷；没点弹窗不算对照完成。入口逐步与缺陷原文见 [esim-defect-entry-and-bug-template.md](esim-defect-entry-and-bug-template.md)。

参数对应与 2026-08-19 进度见 [param-mapping-and-progress.md](param-mapping-and-progress.md)。

## 字典兜底方案

遇到「非法字段/非法枚举」类报错时的排查路径：

1. **查字典接口**：SAAS 有 `api-3486617`（租户字典管理 [查询-]），传 `dictGroup=目标字段名`，获取当前有效枚举列表
2. **查已成功样例**：Apifox 同接口的「运行记录」标签页，找团队中其他人成功的请求体对比
3. **查数据库枚举表**：如有 DB 权限，查 `sys_dict_data` 表获取枚举值
4. **询问后端开发**：以上均无果时，直接找接口负责人确认

## 验证与清理

**验证**：每步完成后调用对应的查询/详情接口确认数据已落库：
- Step 6 → `/api/IL/project/detail`
- Step 8 → 权益详情查询
- Step 10 → 商品分页查询 `api-3502967`
- Step 11 → 执行单个任务 `api-3491396` 验证计划生效

**清理**：测试完成后，若需清理测试数据避免污染环境：
- 找对应的 delete/disable 接口
- 或联系开发提供 SQL 清理脚本
- 重要：生产环境绝不执行清理操作
