# SWAP entitlement - phase 2 测试用例

## Membership 接口

### /v2/entitlements/search 与 /v2/memberships

#### 正向场景验证

##### tc-P1-ENT-QUERY-001：会员仅存在单品类权益时，返回 moduleExclusiveEntitlements 且 enabledTypes=[1]

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应体中 `entitlements.moduleExclusiveEntitlements` 返回该会员所有单品类权益明细
- tc-P1: 响应体中不返回或返回空数组 `entitlements.crossModuleEntitlements`
- tc-P1: `entitlements.enabledTypes` 仅包含值 `1`

##### tc-P1-ENT-QUERY-002：会员仅存在跨品类 swap 权益时，返回 crossModuleEntitlements 且 enabledTypes=[2]

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应体中 `entitlements.crossModuleEntitlements` 返回所有跨品类 swap 权益明细
- tc-P1: `entitlements.crossModuleEntitlements[*].entitlementPoolId` 与会籍下实际的权益明细编码一一对应
- tc-P1: `entitlements.enabledTypes` 仅包含值 `2`
- tc-P1: `entitlements.moduleExclusiveEntitlements` 不返回或为空数组

##### tc-P1-ENT-QUERY-003：会员同时存在单品类 + 跨品类 swap 权益时，两类权益均正确返回且 enabledTypes=[1,2]

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应体中同时包含 `moduleExclusiveEntitlements` 与 `crossModuleEntitlements`
- tc-P1: `entitlements.enabledTypes` 同时包含 `1` 和 `2`
- tc-P1: 单品类、跨品类权益数量及明细与 SaaS 会籍配置保持一致

#### 结构与字段规则验证

##### tc-P2-ENT-QUERY-004：验证 crossModuleEntitlements.details 中三类权益数的返回规则

- tc-P2: `details.cardholderExclusiveEntitlements` 返回持卡人专属权益剩余点数
- tc-P2: `details.guestsExclusiveEntitlements` 返回携伴专属权益剩余点数
- tc-P2: `details.sharedEntitlements` 返回共享权益剩余点数
- tc-P2: 对于为 0 的权益类型，可按实现约定返回 0 或不返回字段，但接口行为与需求/设计一致

##### tc-P2-ENT-QUERY-005：验证 crossModuleEntitlements.applicableModules 支持的跨品类组合

- tc-P2: 当配置为“休息室+Setmeal”时，`applicableModules` 仅包含 lounge 与 setmeal 对应的 module 枚举
- tc-P2: 当配置为“Setmeal+Coupon”或“休息室+Coupon”或“三者皆有”时，`applicableModules` 返回与配置一致的 module 集合
- tc-P2: 返回的 module 枚举值与 phase 1 中 E-pass 的多品类配置保持一致

### /v2/entitlements/update

#### 双定位模式（entitlementPoolId 与 module+tier）

##### tc-P1-ENT-UPDATE-001：仅传 module+tier 更新单品类权益成功（双定位模式）

- tc-P1: 入参仅包含 `membershipId`、`module`、`tier` 以及数值字段（如 `usageRestriction`、`quantity`、`purchasedQuantity`）
- tc-P1: 系统能根据 `membershipId+module+tier` 唯一解析出对应 `entitlementPoolId`
- tc-P1: 对应单品类权益 pool 数值被正确更新
- tc-P1: 返回体中 `entitlements` 结构完整，包含更新后的 `moduleExclusiveEntitlements`

##### tc-P1-ENT-UPDATE-002：仅传 entitlementPoolId 更新单品类或跨品类权益成功

- tc-P1: 入参包含合法的 `entitlementPoolId` 和待更新的数值字段，不传 `module`/`tier`
- tc-P1: 系统根据 `entitlementPoolId` 精确定位到对应 pool（可为单品类或 swap）
- tc-P1: 对应权益 pool 数值被正确更新
- tc-P1: 返回体中 `entitlements` 结构完整，包含最新的单品类与跨品类权益

##### tc-P1-ENT-UPDATE-003：同时传 entitlementPoolId 与 module/tier 时返回参数冲突错误

- tc-P1: 入参同时包含 `entitlementPoolId` 与 `module`、`tier`
- tc-P1: 接口返回 4xx 或业务错误码，表示双定位参数冲突
- tc-P1: 任何权益 pool 均未被修改

#### 原有入参与兼容性

##### tc-P2-ENT-UPDATE-004：沿用原有入参仅更新 moduleExclusiveEntitlements，返回结构与历史保持一致

- tc-P2: 入参仅包含 `membershipId`、`module`、可选 `tier` 以及 `usageRestriction`、`quantity`、`purchasedQuantity`
- tc-P2: 在仅有单品类权益的会员上更新成功，返回与 phase 1 定义一致的 `entitlements` 结构
- tc-P2: 在既有单品类又有 swap 的会员上，仅单品类权益被更新，`crossModuleEntitlements` 不受影响

#### swap 权益更新（crossModuleEntitlements）

##### tc-P1-ENT-UPDATE-005：指定 entitlementPoolId 成功更新跨品类 swap 权益

- tc-P1: 入参 `entitlementPoolId` 对应一个合法的 swap 权益 pool
- tc-P1: 更新 `usageRestriction`、`quantity` 或 `purchasedQuantity` 后，`crossModuleEntitlements` 中对应 pool 的值正确变化
- tc-P1: 返回体中的 `enabledTypes` 包含 `2`，并与会员实际存在的跨品类权益保持一致

##### tc-P2-ENT-UPDATE-006：使用不存在或不属于当前会员的 entitlementPoolId 时返回错误

- tc-P2: 入参 `entitlementPoolId` 不存在或不属于当前 `membershipId`
- tc-P2: 接口返回明确错误码与提示信息，不会更新任何权益

##### tc-P2-ENT-UPDATE-007：更新 swap 权益时数值非法（负数或超上限）返回参数错误

- tc-P2: 当传入 `quantity`、`purchasedQuantity` 为负数或超过系统上限时，接口返回参数校验错误
- tc-P2: 对应权益 pool 的数值保持不变

#### 返回结构完整性

##### tc-P1-ENT-UPDATE-008：无论更新单品类或跨品类权益，返回体都包含最新完整权益状态

- tc-P1: 成功更新后，返回体 `data.entitlements` 中同时包含最新的 `moduleExclusiveEntitlements` 与 `crossModuleEntitlements`
- tc-P1: 当会员存在 swap 权益时，返回中包含 `enabledTypes` 字段且内容正确
- tc-P1: 当会员不存在 swap 权益时，`enabledTypes` 中不包含 `2`

### /v2/entitlements/details

#### 不支持 cross module entitlement 的限制

##### tc-P1-ENT-DETAILS-001：会员仅有跨品类 swap 权益时，调用 details 接口返回 500.030.030

- tc-P1: 为仅配置 swap 权益的会员，调用 `/v2/entitlements/details`，`module` 传任一 swap 所覆盖的 module
- tc-P1: 接口返回错误码 `500.030.030`
- tc-P1: 错误消息为“This API does not support querying cross-module entitlements.” 或与文档描述一致
- tc-P1: 不返回任何 swap 权益 details

##### tc-P1-ENT-DETAILS-002：会员同时拥有单品类 + swap 权益时，details 仅返回单品类权益

- tc-P1: 为同时拥有单品类与 swap 的会员，调用 `/v2/entitlements/details`，`module` 传单品类对应的 module
- tc-P1: 接口仅返回单品类权益的 details，且与 membership 中的 moduleExclusiveEntitlements 对应
- tc-P1: 接口不返回 cross module entitlement 相关明细

##### tc-P2-ENT-DETAILS-003：当会员无任何权益或传入无效 module 时的异常处理

- tc-P2: 对无任何权益的会员调用 details 接口，返回空结果或设计约定的业务错误
- tc-P2: 传入与会员权益无关的 module 时，返回参数错误或资源不存在错误，且不使用 500.030.030

## 资源接口

### 复用 E-pass 相关资源配置逻辑

#### 资源检索与可用范围

##### tc-P2-ENT-RESOURCE-001：跨品类 swap 权益在资源检索接口中可正确检索到多品类资源

- tc-P2: 使用配置有 swap 的会籍模板，调用 `/v2/resources`、`/v2/search` 等资源相关接口
- tc-P2: 可根据 swap 配置的 `applicableModules` 检索到对应品类（lounge/setmeal/coupon）的资源
- tc-P2: 资源可用性与 phase 1 的多品类 E-pass 行为保持一致

##### tc-P3-ENT-RESOURCE-002：swap 场景下资源更新与下架逻辑回归

- tc-P3: 在存在 swap 配置的 program 下，调用 `/v2/resources/updates` 接口
- tc-P3: 资源上下架与更新结果与 phase 1 行为一致，本次改动不会影响更新逻辑

## 下单与权益统计

### preview 与下单前权益计算

#### 单品类 + 跨品类合并统计

##### tc-P1-ORDER-CALC-001：仅有单品类权益时，预览与下单前权益统计仅包含单品类权益

- tc-P1: 在仅配置单品类权益的会员上发起预览与下单请求
- tc-P1: 权益统计结果仅基于 `moduleExclusiveEntitlements` 的明细进行计算
- tc-P1: 统计结果与历史实现保持一致

##### tc-P1-ORDER-CALC-002：仅有跨品类 swap 权益时，预览与下单前权益统计仅包含跨品类权益

- tc-P1: 在仅配置 swap 权益的会员上发起预览与下单请求
- tc-P1: 权益统计结果基于 `crossModuleEntitlements` 的明细进行计算
- tc-P1: 可用权益数量与 swap 权益明细中的剩余权利数一致

##### tc-P1-ORDER-CALC-003：同时存在单品类 + 跨品类权益时，统计总数为二者之和

- tc-P1: 在同时拥有单品类和 swap 权益的会员上发起预览与下单请求
- tc-P1: 权益统计总数=单品类权益可用数量 + 跨品类权益可用数量
- tc-P1: 单品类与跨品类权益均可作为本次订单可用权益参与计算

#### 权益状态过滤规则

##### tc-P2-ORDER-CALC-004：仅统计待使用与已用完状态的权益，不统计已作废/冻结/已过期

- tc-P2: 为会员配置多种状态的权益明细（待使用/已用完/已作废/冻结/已过期）
- tc-P2: 预览与下单前的权益统计仅计入“待使用”和“已用完”两类明细
- tc-P2: 已作废、冻结、已过期的权益不计入初始/剩余统计

##### tc-P2-ORDER-CALC-005：跨品类权益状态过滤规则与单品类一致

- tc-P2: 为 swap 权益分别配置不同状态的明细记录
- tc-P2: 统计可用权益时，对 swap 权益应用与单品类相同的状态过滤规则
- tc-P2: 统计结果仍为“单品类+跨品类”中状态为待使用/已用完的明细之和

### 订单取消

#### SaaS 回退与 PAPI 行为

##### tc-P2-ORDER-CANCEL-001：取消订单后权益由 SaaS 回退，PAPI 不重复回退

- tc-P2: 会员使用单品类或跨品类权益下单成功后取消订单
- tc-P2: 由 SaaS 将权益回退到对应的权益明细，PAPI 不对同一订单执行二次回退
- tc-P2: 取消后再次查询 membership，权益余额与回退后的实际值一致

##### tc-P3-ORDER-CANCEL-002：多次重复取消同一订单时，权益余额保持幂等

- tc-P3: 对同一订单执行重复取消或重放取消请求
- tc-P3: PAPI 不因重复取消请求导致权益被多次回退
- tc-P3: 会员最终权益余额与首次取消后的结果保持一致

