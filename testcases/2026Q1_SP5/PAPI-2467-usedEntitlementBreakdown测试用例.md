# usedEntitlementBreakdown 扣点明细测试用例

## 预览订单接口（Preview Membership Prebooking Order）

### /v2/orders/{modules}/memberships/prebooking/preview 返回 usedEntitlementBreakdown

#### 正向场景验证

##### tc-P1-PREVIEW-UEB-001：仅使用单品类权益下单预览，usedEntitlementBreakdown 返回 sourceType=module_exclusive 且结构完整

- tc-P1: HTTP 状态码为 200
- tc-P1: 响应中包含 `usedEntitlementBreakdown` 数组
- tc-P1: 数组中存在 `sourceType` 为 `module_exclusive` 的对象
- tc-P1: 该对象包含 `tier` 字段（Lounge/FT 场景）
- tc-P1: 该对象 `entitlements` 包含 `cardholderExclusiveEntitlements`、`guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 四个字段
- tc-P1: 各字段数值与实际扣除的权益点数一致

##### tc-P1-PREVIEW-UEB-002：仅使用跨品类（swap）权益下单预览，usedEntitlementBreakdown 返回 sourceType=cross_module 且结构完整

- tc-P1: 响应中 `usedEntitlementBreakdown` 数组存在 `sourceType` 为 `cross_module` 的对象
- tc-P1: 该对象不包含 `tier` 字段
- tc-P1: `entitlements` 中各字段数值与实际扣除的跨品类权益点数一致

##### tc-P1-PREVIEW-UEB-003：同时扣除单品类 + 跨品类权益时，usedEntitlementBreakdown 返回两种 sourceType 的对象

- tc-P1: `usedEntitlementBreakdown` 数组中同时存在 `module_exclusive` 和 `cross_module` 两种 sourceType 的对象
- tc-P1: 各对象的 `entitlements` 数值分别反映单品类和跨品类权益的实际扣除量
- tc-P1: 总扣除量 = module_exclusive 的 entitlements + cross_module 的 entitlements

#### tier 字段规则验证

##### tc-P2-PREVIEW-UEB-004：Lounge 场景下 module_exclusive 对象包含 tier 字段，值与实际使用的 tier 一致

- tc-P2: modules 为 `lounges` 时，`sourceType=module_exclusive` 对象的 `tier` 字段存在
- tc-P2: `tier` 值与会员实际使用的权益 tier 等级一致（如 tier=1 或 tier=2）

##### tc-P2-PREVIEW-UEB-005：FT 场景下 module_exclusive 对象包含 tier 字段

- tc-P2: modules 为 `fastTrack` 时，`sourceType=module_exclusive` 对象的 `tier` 字段存在
- tc-P2: `tier` 值与会员实际使用的权益 tier 等级一致

##### tc-P2-PREVIEW-UEB-006：cross_module 类型的对象不返回 tier 字段

- tc-P2: `sourceType=cross_module` 的对象中不包含 `tier` 字段
- tc-P2: 无论 Lounge 还是 FT 场景，cross_module 均无 tier

##### tc-P2-PREVIEW-UEB-007：未使用 tier 权益时，module_exclusive 对象不返回 tier 字段

- tc-P2: 当该品类未配置分级权益或未使用 tier 权益时
- tc-P2: `sourceType=module_exclusive` 的对象中不包含 `tier` 字段

#### entitlements 字段验证

##### tc-P2-PREVIEW-UEB-008：仅扣除持卡人专属点时，entitlements 中仅 cardholderExclusiveEntitlements 有值，其余为 0

- tc-P2: `cardholderExclusiveEntitlements` 值为实际扣除的点数
- tc-P2: `guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 均为 0

##### tc-P2-PREVIEW-UEB-009：同时扣除多种类型权益点时，entitlements 各字段分别反映实际扣除量

- tc-P2: 持卡人下单并携伴，同时使用共享点和买点
- tc-P2: `cardholderExclusiveEntitlements`、`guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 各字段分别返回对应的扣除量
- tc-P2: 所有字段之和等于本次实际使用的总权益点数

#### sourceType 判断规则

##### tc-P2-PREVIEW-UEB-010：使用单品类权益扣点时 sourceType 为 module_exclusive，使用跨品类权益时为 cross_module

| 权益来源 | 预期 sourceType | 是否有 tier |
|---------|----------------|------------|
| 单品类权益（如仅 lounge 品类） | module_exclusive | Lounge/FT 有 |
| 跨品类权益（swap） | cross_module | 无 |

- tc-P2: 各场景下 `sourceType` 与上表一致
- tc-P2: sourceType 严格根据权益的实际来源类型判断

#### 合并规则验证

##### tc-P1-PREVIEW-UEB-011：同品类同 tier 的不同权益类型（持卡人点+共享点+买点）合并到同一个 module_exclusive 对象

- tc-P1: 同时扣除 lounge T1 的持卡人专属点、共享点和买点
- tc-P1: `usedEntitlementBreakdown` 中仅返回 1 个 `sourceType=module_exclusive` 且 `tier=1` 的对象
- tc-P1: 该对象 `entitlements` 中 `cardholderExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 分别有值
- tc-P1: 不会拆分为 3 条独立记录

##### tc-P2-PREVIEW-UEB-012：同品类但不同 tier 的权益分别展示为独立对象

- tc-P2: 会员配置了 lounge T1 和 T2 两级权益，下单时扣除了两个 tier 的权益
- tc-P2: `usedEntitlementBreakdown` 中返回 2 个 `sourceType=module_exclusive` 对象，分别带有 `tier=1` 和 `tier=2`
- tc-P2: 各对象 `entitlements` 分别反映对应 tier 的扣除量

##### tc-P2-PREVIEW-UEB-013：项目配置了多种跨品类权益但扣了多个时，合并为最多 1 个 cross_module 对象

- tc-P2: 项目配置了多种跨品类权益（如 134+13 组合），且下单时扣了 2 个跨品类权益
- tc-P2: `usedEntitlementBreakdown` 中最多只有 1 个 `sourceType=cross_module` 的对象
- tc-P2: 该对象的 `entitlements` 汇总了所有跨品类权益的扣除量

#### 不展示规则

##### tc-P2-PREVIEW-UEB-014：未扣除 swap 权益时，不返回 cross_module 类型的对象

- tc-P2: 仅使用单品类权益完成预览
- tc-P2: `usedEntitlementBreakdown` 数组中无 `sourceType=cross_module` 的对象

##### tc-P2-PREVIEW-UEB-015：未扣除单品类权益时，不返回 module_exclusive 类型的对象

- tc-P2: 仅使用 swap 权益完成预览
- tc-P2: `usedEntitlementBreakdown` 数组中无 `sourceType=module_exclusive` 的对象

#### 接口模块适用范围

##### tc-P1-PREVIEW-UEB-016：Preview 接口仅支持 Lounge 和 FT 两个 module，均返回 usedEntitlementBreakdown

| modules 参数 | 预期行为 |
|-------------|---------|
| lounges | 返回 usedEntitlementBreakdown |
| fastTrack | 返回 usedEntitlementBreakdown |

- tc-P1: Lounge 和 FT 的预览接口均正确返回 `usedEntitlementBreakdown` 字段
- tc-P1: 字段结构与业务逻辑在两个 module 下保持一致

## 创建订单接口（Create Membership Prebooking Order）

### 创建订单返回 usedEntitlementBreakdown（通用逻辑）

#### 正向场景验证

##### tc-P1-CREATE-UEB-001：各品类创建 Membership 订单成功后，响应中返回 usedEntitlementBreakdown 且结构正确

| 接口路径 | 适用品类 |
|---------|---------|
| `/v2/orders/lounges/memberships/prebooking` | Lounge |
| `/v2/orders/fastTrack/memberships/prebooking` | Fast Track |
| `/v2/orders/fitness/memberships/prebooking` | Fitness |
| `/v2/orders/esims/memberships/prebooking` | eSIM |
| `/v2/orders/esims/memberships/topup` | eSIM Topup |

- tc-P1: 以上各接口创建订单成功后，响应中均包含 `usedEntitlementBreakdown` 数组
- tc-P1: 数组结构包含 `sourceType`、`entitlements` 字段
- tc-P1: `entitlements` 包含 `cardholderExclusiveEntitlements`、`guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements`

##### tc-P1-CREATE-UEB-002：创建 Lounge 订单仅使用单品类权益，返回 module_exclusive 含 tier 且数值正确

- tc-P1: Lounge 创建订单成功
- tc-P1: `usedEntitlementBreakdown` 中存在 `sourceType=module_exclusive` 对象
- tc-P1: 该对象包含 `tier` 字段，与实际使用的 tier 等级一致
- tc-P1: `entitlements` 各字段值与实际扣除量一致

##### tc-P1-CREATE-UEB-003：创建 FT 订单仅使用单品类权益，返回 module_exclusive 含 tier 且数值正确

- tc-P1: FT 创建订单成功
- tc-P1: `usedEntitlementBreakdown` 中 `sourceType=module_exclusive` 对象包含 `tier` 字段
- tc-P1: `entitlements` 各字段值与实际扣除量一致

#### tier 字段适用范围验证

##### tc-P2-CREATE-UEB-004：Lounge/FT 的 module_exclusive 有 tier，Fitness/eSIM 的 module_exclusive 无 tier

| 品类 | module_exclusive 是否有 tier |
|------|---------------------------|
| Lounge | 有（若使用了 tier 权益） |
| Fast Track | 有（若使用了 tier 权益） |
| Fitness | 无 |
| eSIM | 无 |

- tc-P2: Lounge 和 FT 的 `module_exclusive` 对象在使用 tier 权益时返回 `tier` 字段
- tc-P2: Fitness 和 eSIM 的 `module_exclusive` 对象不返回 `tier` 字段
- tc-P2: cross_module 对象在所有品类下均不返回 `tier` 字段

#### sourceType 逻辑验证

##### tc-P2-CREATE-UEB-005：创建订单时 sourceType 根据实际使用的权益类型判断

- tc-P2: 仅扣除单品类权益 → 仅返回 `module_exclusive`
- tc-P2: 仅扣除 swap 权益 → 仅返回 `cross_module`
- tc-P2: 同时扣除两种权益 → 同时返回 `module_exclusive` 和 `cross_module`

#### 合并规则验证

##### tc-P1-CREATE-UEB-006：创建订单时同品类同 tier 不同权益类型合并为 1 个 module_exclusive 对象

- tc-P1: 扣除 Lounge T1 的持卡人点 + 共享点 + 买点
- tc-P1: `usedEntitlementBreakdown` 中仅 1 个 `sourceType=module_exclusive, tier=1` 对象
- tc-P1: 该对象 `entitlements` 中 `cardholderExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 分别反映各自扣除量

##### tc-P2-CREATE-UEB-007：创建订单时多个跨品类权益扣点合并为最多 1 个 cross_module 对象

- tc-P2: 项目配置了多种跨品类权益，下单时扣了多个
- tc-P2: `usedEntitlementBreakdown` 中 `cross_module` 对象最多 1 个
- tc-P2: 该对象 `entitlements` 为所有跨品类权益的合计

#### eSIM Topup 场景

##### tc-P2-CREATE-UEB-008：eSIM topup 接口（/v2/orders/esims/memberships/topup）创建成功后返回 usedEntitlementBreakdown

- tc-P2: eSIM topup 创建成功
- tc-P2: 响应中包含 `usedEntitlementBreakdown` 数组
- tc-P2: `sourceType` 根据实际使用的权益类型正确返回
- tc-P2: eSIM 场景的 `module_exclusive` 对象不包含 `tier` 字段

## 订单详情接口（Retrieve Membership Usage Order Details）

### /v2/orders/memberships/details 返回 usedEntitlementBreakdown

#### 正向场景验证

##### tc-P1-DETAIL-UEB-001：各品类的 Membership 订单详情均返回 usedEntitlementBreakdown 且与创建时一致

| 适用品类 | 是否支持 tier |
|---------|-------------|
| Lounge | 是 |
| Fast Track | 是 |
| Dining | 否 |
| Setmeal | 是 |
| eSIM | 否 |
| Fitness | 否 |

- tc-P1: 查询以上各品类的 Membership 订单详情，响应中均包含 `usedEntitlementBreakdown` 数组
- tc-P1: 数组内容与创建订单时返回的 `usedEntitlementBreakdown` 一致
- tc-P1: `sourceType`、`tier`（如适用）、`entitlements` 各字段值正确

##### tc-P1-DETAIL-UEB-002：仅使用单品类权益的订单，详情中 usedEntitlementBreakdown 仅含 module_exclusive

- tc-P1: 订单仅扣除了单品类权益
- tc-P1: `usedEntitlementBreakdown` 仅包含 `sourceType=module_exclusive` 的对象
- tc-P1: 不包含 `cross_module` 类型的对象

##### tc-P1-DETAIL-UEB-003：仅使用 swap 权益的订单，详情中 usedEntitlementBreakdown 仅含 cross_module

- tc-P1: 订单仅扣除了跨品类权益
- tc-P1: `usedEntitlementBreakdown` 仅包含 `sourceType=cross_module` 的对象
- tc-P1: 不包含 `module_exclusive` 类型的对象

##### tc-P1-DETAIL-UEB-004：同时扣除单品类 + swap 权益的订单，详情中两种 sourceType 均存在

- tc-P1: 订单同时扣除了单品类和跨品类权益
- tc-P1: `usedEntitlementBreakdown` 数组中同时包含 `module_exclusive` 和 `cross_module` 对象
- tc-P1: 各对象 `entitlements` 数值与实际扣除一致

#### tier 字段品类差异验证

##### tc-P2-DETAIL-UEB-005：Lounge/FT/Setmeal 订单详情中 module_exclusive 含 tier，Dining/eSIM/Fitness 无 tier

| 品类 | module_exclusive 是否有 tier |
|------|---------------------------|
| Lounge | 有（若使用了 tier 权益） |
| Fast Track | 有（若使用了 tier 权益） |
| Setmeal | 有（若使用了 tier 权益） |
| Dining | 无 |
| eSIM | 无 |
| Fitness | 无 |

- tc-P2: Lounge、FT、Setmeal 的订单详情中 `module_exclusive` 对象在使用 tier 权益时返回 `tier` 字段
- tc-P2: Dining、eSIM、Fitness 的订单详情中 `module_exclusive` 对象不返回 `tier` 字段
- tc-P2: 所有品类的 `cross_module` 对象均不返回 `tier` 字段

#### 合并规则验证

##### tc-P2-DETAIL-UEB-006：订单详情中同品类同 tier 不同权益类型合并为 1 个对象展示

- tc-P2: 订单扣除了同品类同 tier 的持卡人点 + 共享点 + 买点
- tc-P2: 详情中 `usedEntitlementBreakdown` 该品类 + tier 仅 1 个 `module_exclusive` 对象
- tc-P2: `entitlements` 内各字段分别反映对应的扣除量

##### tc-P2-DETAIL-UEB-007：订单详情中跨品类权益合并为最多 1 个 cross_module 对象展示

- tc-P2: 即使项目配置了多种跨品类权益且均有扣除
- tc-P2: 详情中 `cross_module` 对象最多 1 个
- tc-P2: `entitlements` 为所有跨品类权益扣除量的合计

#### 数据一致性验证

##### tc-P1-DETAIL-UEB-008：创建订单与查询订单详情返回的 usedEntitlementBreakdown 数据完全一致

- tc-P1: 创建订单后立即查询该订单详情
- tc-P1: 两个接口返回的 `usedEntitlementBreakdown` 数组长度一致
- tc-P1: 每个对象的 `sourceType`、`tier`（如适用）、`entitlements` 各字段值完全匹配

## 预览与创建一致性

### Preview 与 Create 返回的 usedEntitlementBreakdown 对比

#### 数据一致性

##### tc-P1-CONSISTENCY-001：同一笔订单的 Preview 和 Create 返回的 usedEntitlementBreakdown 一致

- tc-P1: 使用相同参数先调用 Preview 再调用 Create 接口
- tc-P1: 两次返回的 `usedEntitlementBreakdown` 数组长度一致
- tc-P1: 每个对象的 `sourceType`、`tier`（如适用）、`entitlements` 各字段值完全匹配
- tc-P1: 实际创建的扣点明细与预览时展示的一致

## 边界与异常场景

### usedEntitlementBreakdown 边界场景

#### 边界值验证

##### tc-P3-EDGE-UEB-001：所有权益点均为 0 时（无实际扣点），usedEntitlementBreakdown 返回行为验证

- tc-P3: 当订单不需要扣除任何权益点（如全部使用买点为 0 且其他权益也为 0）
- tc-P3: 验证 `usedEntitlementBreakdown` 是否返回空数组或不返回

##### tc-P3-EDGE-UEB-002：仅扣除 purchasedEntitlements（买点）时，usedEntitlementBreakdown 正确展示

- tc-P3: 会员仅有买点可用，下单仅扣除买点
- tc-P3: `usedEntitlementBreakdown` 中对应对象的 `purchasedEntitlements` 有值
- tc-P3: 其余三个权益字段（cardholderExclusiveEntitlements、guestsExclusiveEntitlements、sharedEntitlements）均为 0

##### tc-P3-EDGE-UEB-003：携伴人数较多，同时扣除多种权益类型时，entitlements 各字段累加正确

- tc-P3: 会员带多名携伴下单，涉及持卡人点、携伴点、共享点、买点多种扣除
- tc-P3: `entitlements` 中各字段数值与实际扣除量匹配
- tc-P3: 所有字段之和等于本次使用的总权益点数

#### 异常配置场景

##### tc-P3-EDGE-UEB-004：单品类配错导致扣除 2 个 tier 的权益时，展示 2 条 module_exclusive 对象

- tc-P3: 权益配置异常导致同时扣除了 T1 和 T2 两个 tier 的单品类权益
- tc-P3: `usedEntitlementBreakdown` 中展示 2 个 `module_exclusive` 对象
- tc-P3: 分别对应 `tier=1` 和 `tier=2`，各自 `entitlements` 反映对应 tier 的扣除量
