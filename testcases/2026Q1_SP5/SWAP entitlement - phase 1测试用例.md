# SWAP entitlement - phase 1 测试用例

## E-pass 创建接口

### /v2/orders/multiModule/ePasses 创建 swap E-pass

#### 正向场景验证

##### tc-P1-EPASS-CREATE-001：使用 module=0 创建 swap E-pass 成功，返回完整结构

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应中 `module` 值为 `0`
- tc-P1: 响应中 `extra.allowedModules` 返回该 swap 权益可用的品类数组（如 `[1, 3]` 表示休息室 + Setmeal）
- tc-P1: `extra.ePassId` 成功生成
- tc-P1: `extra.ePassStatus` 为初始状态 `0`
- tc-P1: `extra.availableUsages` 与请求入参一致
- tc-P1: `extra.usedUsages` 为 `0`

##### tc-P1-EPASS-CREATE-002：swap E-pass 支持指定跨品类的 resourceIds，创建成功且 allowedResources 正确返回

- tc-P1: 入参 `allowedResources.resourceIds` 包含不同品类的资源 code（Ncode + Rcode）
- tc-P1: 创建成功，响应中 `allowedResources.resourceIds` 与入参一致
- tc-P1: resourceIds 中的资源可来自不同品类（如 lounge 的 Ncode + setmeal 的 Rcode）

##### tc-P1-EPASS-CREATE-003：swap E-pass 不指定 resourceIds（空数组）时创建成功，表示不限制网点

- tc-P1: 入参 `allowedResources.resourceIds` 为空数组 `[]`
- tc-P1: 创建成功，返回 `allowedResources.resourceIds` 为空数组
- tc-P1: 该 ePass 可用于 swap 配置范围内的所有网点

#### category 字段规则验证

##### tc-P2-EPASS-CREATE-004：swap 中包含 lounge 品类时，category 返回 3

| swap 品类组合 | 是否包含 lounge | 预期 category |
|--------------|----------------|--------------|
| 休息室 + Setmeal | 是 | 3 |
| 休息室 + Coupon | 是 | 3 |
| 休息室 + Setmeal + Coupon | 是 | 3 |
| Setmeal + Coupon | 否 | 1 |

- tc-P2: 每种 swap 品类组合下 `category` 值符合上表预期
- tc-P2: 单品类场景保持历史逻辑不变

#### module 字段规则验证

##### tc-P1-EPASS-CREATE-005：swap 场景下 module 只允许输入 0，单品类场景只允许输入对应品类的 module 值

- tc-P1: swap program 下创建 ePass 时 `module` 传 `0`，创建成功
- tc-P1: 单品类 program 下创建 ePass 时 `module` 传对应品类值（如 `1` 表示 lounge），创建成功
- tc-P1: swap program 下 `module` 传非 `0` 值（如 `1`），返回错误
- tc-P1: 单品类 program 下 `module` 传 `0`，返回错误

#### program 组隔离规则

##### tc-P1-EPASS-CREATE-006：swap program 组仅支持发放 swap E-pass，不兼容单品类

- tc-P1: 在 swap program 组下尝试通过单品类接口（如 `/v2/orders/lounges/ePasses`）创建 ePass，返回错误码 `500.xxx.010`
- tc-P1: 错误提示为"Sorry, we're unable to process your order at the moment. Please try again later or contact DragonPass support team."
- tc-P1: 在 swap program 组下通过 `/v2/orders/multiModule/ePasses`（module=0）创建成功

##### tc-P1-EPASS-CREATE-007：单品类 program 组不支持发放 swap E-pass

- tc-P1: 在单品类 program 组下尝试通过 `/v2/orders/multiModule/ePasses` 创建跨品类 ePass，返回错误码 `500.000.020`
- tc-P1: 错误提示为"Sorry, we're unable to process your order at the moment. Please try again later or contact DragonPass support team."

#### 异常场景验证

##### tc-P2-EPASS-CREATE-008：clientUserId 重复时返回错误码 500.000.014

- tc-P2: 使用已存在的 `clientUserId` 创建 swap ePass
- tc-P2: 返回错误码 `500.000.014`
- tc-P2: 错误提示为"Sorry, this clientUserId already exists."

##### tc-P2-EPASS-CREATE-009：ePass 过期时间早于激活时间时返回错误码 500.000.015

- tc-P2: 入参 `expirationDate` 早于 `activationDate`
- tc-P2: 返回错误码 `500.000.015`
- tc-P2: 错误提示为"Sorry, the expiration date cannot be earlier than the activation date."

##### tc-P2-EPASS-CREATE-010：ePass 激活时间早于会籍模板生效时间时返回错误码 500.000.016

- tc-P2: 入参 `activationDate` 早于 swap program 会籍模板的生效时间
- tc-P2: 返回错误码 `500.000.016`
- tc-P2: 错误提示为"Sorry, the activation date is earlier than the allowed start date."

##### tc-P2-EPASS-CREATE-011：resourceId 中传了非该 swap 对应品类的资源时返回错误码 500.000.017

- tc-P2: swap 配置为休息室 + Setmeal，但 `resourceIds` 中传入了 Coupon 品类的 Ccode
- tc-P2: 返回错误码 `500.000.017`
- tc-P2: 错误提示为"The 'resourceId' array contains resources that are not associated with the expected module. Please verify and ensure the resource IDs match the correct module."

##### tc-P3-EPASS-CREATE-012：resourceId 中传入超过 30 个资源 code 时返回错误码 500.000.018

- tc-P3: `resourceIds` 数组包含 31 个资源 code
- tc-P3: 返回错误码 `500.000.018`
- tc-P3: 错误提示为"The 'resourceId' array exceeds the maximum limit of 30 resource IDs. Please reduce the number of resource IDs and try again."

##### tc-P2-EPASS-CREATE-013：尝试下单该 ePass 不可用的网点时返回错误码 500.000.013

- tc-P2: swap ePass 指定了 resourceIds，但下单时使用不在 resourceIds 范围内的网点
- tc-P2: 返回错误码 `500.000.013`
- tc-P2: 错误提示为"Sorry, this resource is not accessible with your program."

##### tc-P2-EPASS-CREATE-014：跨品类会籍在 bundle 接口创建单品类 bundle 单时返回错误码 500.xxx.010

- tc-P2: 在 swap program 下调用 `/v2/orders/{module}/ePasses/bundle` 创建对应品类的 bundle 单
- tc-P2: 返回错误码 `500.xxx.010`
- tc-P2: 错误提示为"Sorry, we're unable to process your order at the moment. Please try again later or contact DragonPass support team."

## E-pass 查询接口

### /v2/orders/ePasses/search 查询 swap E-pass

#### 正向场景验证

##### tc-P1-EPASS-SEARCH-001：查询 swap E-pass 返回正确的跨品类结构

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应中 `module` 值为 `0`
- tc-P1: 响应中 `extra.allowedModules` 返回该 swap 权益的可用品类数组
- tc-P1: `extra.ePassStatus` 反映当前实际状态
- tc-P1: `extra.availableUsages` 与 `extra.usedUsages` 反映实际使用情况
- tc-P1: `allowedResources.resourceIds` 与创建时一致

##### tc-P2-EPASS-SEARCH-002：已使用的 swap E-pass 查询后 usedUsages 正确递增，allowedResources 反映使用记录

- tc-P2: swap ePass 被核销使用后，`extra.usedUsages` 正确递增
- tc-P2: `extra.availableUsages` 相应递减
- tc-P2: `allowedResources.resourceIds` 展示实际使用的网点资源

#### allowedModules 字段规则

##### tc-P2-EPASS-SEARCH-003：仅当 module=0 时返回 allowedModules 字段，单品类 ePass 不返回

- tc-P2: 查询 swap ePass（module=0），响应中包含 `extra.allowedModules` 字段
- tc-P2: 查询单品类 ePass（module=1/3/4），响应中不包含 `extra.allowedModules` 字段

## E-pass 展示接口

### /v2/orders/ePasses 与 /v2/orders/ePasses/details 展示逻辑

#### 核销后展示规则

##### tc-P1-EPASS-DISP-001：swap E-pass 核销后，根据实际核销网点展示对应的 module 和 Ncode/Rcode

- tc-P1: swap ePass 在休息室网点核销后，展示接口返回的 module 为休息室对应值，资源为 Ncode
- tc-P1: swap ePass 在 Setmeal 网点核销后，展示接口返回的 module 为 Setmeal 对应值，资源为 Rcode
- tc-P1: swap ePass 在 Coupon 网点核销后，展示接口返回的 module 为 Coupon 对应值，资源为对应 code

##### tc-P2-EPASS-DISP-002：未核销的 swap E-pass 展示 module=0 与完整 allowedModules

- tc-P2: 未使用的 swap ePass 在列表和详情接口中 `module` 保持为 `0`
- tc-P2: `allowedModules` 展示 swap 配置的所有可用品类

## 资源接口

### swap entitlement 多品类资源检索

#### 正向场景验证

##### tc-P1-RESOURCE-001：swap entitlement 的 program 支持检索对应品类的资源

| 资源接口 | 验证点 |
|---------|--------|
| `/v2/resources` | 可检索 swap 配置中所有品类的资源列表 |
| `/v2/resources/{resourceId}` | 可查询 swap 配置范围内的单个资源详情 |
| `/v2/transportHubs` | 可检索 swap 配置品类对应的交通枢纽列表 |
| `/v2/transportHubs/{transportHubId}` | 可查询对应交通枢纽详情 |
| `/v2/search/modules` | 返回 swap 配置的多品类 module 列表 |
| `/v2/search` | 跨品类搜索返回 swap 配置范围内的资源 |

- tc-P1: 以上各接口在 swap program 下均可正确检索到多品类资源
- tc-P1: 检索范围与 swap 会籍模板中配置的品类保持一致

##### tc-P2-RESOURCE-002：资源更新接口（/v2/resources/updates）在 swap 场景下行为正常

- tc-P2: 在 swap program 下调用 `/v2/resources/updates` 接口
- tc-P2: 资源更新与上下架逻辑与单品类场景保持一致
- tc-P2: 不因 swap 配置而影响现有资源更新逻辑

## 预订单与权益计算

### 下单前权益计算

#### 权益状态过滤规则

##### tc-P1-ORDER-CALC-001：统计会籍下可用权益时，仅统计待使用和已用完两种状态的权益

- tc-P1: 为会员配置多种状态的权益明细（待使用/已用完/已作废/冻结/已过期）
- tc-P1: 权益统计仅计入"待使用"和"已用完"状态的明细
- tc-P1: "已作废"、"冻结"、"已过期"状态的权益不参与统计
- tc-P1: 初始权益和剩余权益均遵循此过滤规则

#### 组合配置场景

##### tc-P2-ORDER-CALC-002：四种 swap 组合配置下的权益计算与资源范围验证

| 组合 | 管理项目 | ResourceIds | 网络范围 |
|------|---------|-------------|---------|
| 休息室 + Setmeal | 一条国际休息室品类项目 | 可指定 N + Rcode | Setmeal + 休息室 |
| Setmeal + Coupon | 国际休息室 + MPV 项目 | 可指定 Rcode | 仅 Setmeal |
| 休息室 + Coupon | 国际休息室 + MPV 项目 | 可指定 N + Rcode | 仅休息室 |
| 休息室 + Setmeal + Coupon | 国际休息室 + MPV 项目 | 可指定 N + Rcode | Setmeal + 休息室 |

- tc-P2: 每种组合下的权益计算范围与上表配置一致
- tc-P2: 下单时的网点可用范围与 BOSS 配置的网络范围匹配

### 订单取消

#### 权益回退机制

##### tc-P2-ORDER-CANCEL-001：swap ePass 订单取消后，权益由 SaaS 负责回退，PAPI 不重复处理

- tc-P2: 使用 swap 权益下单成功后取消订单
- tc-P2: 权益由 SaaS 回退到对应的权益明细
- tc-P2: PAPI 不对同一订单执行二次权益回退
- tc-P2: 取消后查询权益余额与回退后的实际值一致

## Membership 接口

### 权益查询结构（/v2/entitlements/search 与 /v2/memberships）

#### 顶级结构验证

##### tc-P1-ENT-QUERY-001：存在 swap 权益时，返回 crossModuleEntitlements 与 enabledTypes 包含 2

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应中 `entitlements.crossModuleEntitlements` 不为空，返回跨品类权益列表
- tc-P1: `entitlements.enabledTypes` 包含值 `2`（crossModule）
- tc-P1: `crossModuleEntitlements` 每条权益包含 `applicableModules`、`entitlementPoolId`、`details`

##### tc-P1-ENT-QUERY-002：仅存在单品类权益时，不返回 crossModuleEntitlements 或返回为空

- tc-P1: 响应中 `entitlements.moduleExclusiveEntitlements` 正常返回
- tc-P1: `entitlements.crossModuleEntitlements` 不返回或为空数组
- tc-P1: `entitlements.enabledTypes` 仅包含值 `1`（moduleExclusive）

##### tc-P1-ENT-QUERY-003：同时存在单品类 + swap 权益时，两类权益均正确返回且 enabledTypes=[1,2]

- tc-P1: 响应中同时包含 `moduleExclusiveEntitlements` 与 `crossModuleEntitlements`
- tc-P1: `entitlements.enabledTypes` 同时包含 `1` 和 `2`
- tc-P1: 两类权益数据与 SaaS 会籍配置保持一致

#### crossModuleEntitlements 字段验证

##### tc-P2-ENT-QUERY-004：crossModuleEntitlements 中 applicableModules 与 SaaS 配置一致

- tc-P2: `applicableModules` 数组包含 swap 会籍模板中配置的品类 module 枚举
- tc-P2: 当配置为休息室 + Setmeal 时，`applicableModules` 包含 lounge 和 setmeal 的 module 值
- tc-P2: 当配置为三品类组合时，`applicableModules` 包含所有三个品类的 module 值

##### tc-P2-ENT-QUERY-005：crossModuleEntitlements 中 details 返回三类权益点数

- tc-P2: `details.cardholderExclusiveEntitlements` 返回持卡人专属权益剩余点数
- tc-P2: `details.guestsExclusiveEntitlements` 返回携伴专属权益剩余点数
- tc-P2: `details.sharedEntitlements` 返回共享权益剩余点数
- tc-P2: 各类权益点数与会籍下实际权益状态一致

##### tc-P2-ENT-QUERY-006：crossModuleEntitlements 中 entitlementPoolId 唯一标识权益明细

- tc-P2: 每条跨品类权益的 `entitlementPoolId` 与 SaaS 中的权益明细编码一一对应
- tc-P2: `entitlementPoolId` 可用于后续权益编辑接口的定位

#### enabledTypes 枚举验证

##### tc-P2-ENT-QUERY-007：enabledTypes 枚举值正确反映权益类型存在情况

| 权益存在情况 | 预期 enabledTypes |
|-------------|-------------------|
| 仅单品类权益 | [1] |
| 仅 swap 权益 | [2] |
| 单品类 + swap | [1, 2] |

- tc-P2: 各场景下 `enabledTypes` 与上表预期一致
- tc-P2: 枚举值 `1` 代表 moduleExclusive，`2` 代表 crossModule

### 权益编辑（/v2/entitlements/update）

#### 单品类权益更新（兼容历史逻辑）

##### tc-P1-ENT-UPDATE-001：沿用原有入参更新单品类权益成功，返回结构与历史一致

- tc-P1: 入参仅包含 `membershipId`、`quantity`、`module`（非 0）、`usageRestriction`
- tc-P1: 更新成功，`moduleExclusiveEntitlements` 中对应品类的权益值正确更新
- tc-P1: 返回结构保持与 phase 1 前的历史定义一致

##### tc-P2-ENT-UPDATE-002：单品类更新不影响 crossModuleEntitlements

- tc-P2: 在同时拥有单品类和 swap 权益的会员上，仅更新单品类权益
- tc-P2: `crossModuleEntitlements` 不受影响，数值不变
- tc-P2: `enabledTypes` 保持不变

#### swap 权益更新（crossModuleEntitlements）

##### tc-P1-ENT-UPDATE-003：指定 entitlementPoolId 且 module=0 成功更新 swap 权益

- tc-P1: 入参包含 `membershipId`、`module=0`、`entitlementPoolId`（合法值）、`quantity`、`usageRestriction`
- tc-P1: 对应 `crossModuleEntitlements` 中匹配 `entitlementPoolId` 的权益被正确更新
- tc-P1: 返回体中 `entitlements` 结构完整，包含更新后的 `crossModuleEntitlements` 和 `enabledTypes`

##### tc-P2-ENT-UPDATE-004：更新 swap 权益时不传 entitlementPoolId，返回错误

- tc-P2: 入参 `module=0` 但未提供 `entitlementPoolId`
- tc-P2: 接口返回参数校验错误，无法定位到具体的 swap 权益 pool
- tc-P2: 权益数据未发生变化

##### tc-P2-ENT-UPDATE-005：使用不存在或不属于当前会员的 entitlementPoolId 时返回错误

- tc-P2: `entitlementPoolId` 不存在或不属于当前 `membershipId`
- tc-P2: 接口返回明确错误码与提示信息
- tc-P2: 不会更新任何权益

#### 返回结构验证

##### tc-P1-ENT-UPDATE-006：无论更新单品类或 swap 权益，返回体都包含最新完整权益状态

- tc-P1: 成功更新后，返回体 `data.entitlements` 同时包含最新的 `moduleExclusiveEntitlements` 与 `crossModuleEntitlements`
- tc-P1: 当会员存在 swap 权益时，返回中包含 `enabledTypes` 字段且内容正确
- tc-P1: 当会员不存在 swap 权益时，`enabledTypes` 中不包含 `2`

## SaaS 配置规则

### swap program 会籍模板配置

#### 组合配置验证

##### tc-P2-SAAS-CONFIG-001：swap 会籍模板下最多 2 条权益明细，覆盖 4 种场景

| 权益明细配置 | 覆盖场景 | 标签要求 |
|-------------|---------|---------|
| 国际休息室（勾选 SWAP + Setmeal 标签） | 休息室 + Setmeal | SWAP 标签 + Setmeal 标签 |
| 国际休息室（勾选 Setmeal 标签，不勾选 SWAP） + MPV | Setmeal + Coupon | 仅 Setmeal 标签 |
| 国际休息室（无标签） + MPV | 休息室 + Coupon | 无需勾选标签 |
| 国际休息室（勾选 SWAP + Setmeal 标签） + MPV | 休息室 + Setmeal + Coupon | SWAP 标签 + Setmeal 标签 |

- tc-P2: 各组合配置下的标签与权益明细数量符合上表约束
- tc-P2: SWAP 标签告知 API 该权益为休息室和 Setmeal 共享
- tc-P2: 仅 Setmeal 场景使用国际休息室品类项目 + Setmeal 标签（不勾选 SWAP）

#### 资源展示规则

##### tc-P2-SAAS-CONFIG-002：查询资源和展示订单时，根据实际使用网点展示对应 module 和 Ncode/Rcode

- tc-P2: 使用休息室网点时展示 lounge module + Ncode
- tc-P2: 使用 Setmeal 网点时展示 Setmeal module + Rcode
- tc-P2: 使用 Coupon 网点时展示 Coupon module + 对应 code
- tc-P2: 展示内容与实际核销的网点品类一致
