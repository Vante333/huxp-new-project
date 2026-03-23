# usedEntitlementBreakdown字段测试用例

## 预览订单接口（PreviewMembershipPrebookingOrder）

### v2_orders_{modules}_memberships_prebooking_preview

#### 正向场景验证

##### tc-p1: FT/Lounge预览订单使用单品类权益返回usedEntitlementBreakdown含tier字段

- pc: 用户有FT或Lounge单品类权益，预览订单会扣除单品类权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口预览订单
  - HTTP状态码为200，响应包含usedEntitlementBreakdown数组，存在sourceType为module_exclusive的对象，该对象包含tier字段（值为对应tier等级），entitlements展示实际扣除的权益明细

##### tc-p1: 预览订单使用跨品类权益返回usedEntitlementBreakdown含cross_module

- pc: 用户配置了跨品类权益（如134+13），预览订单会扣除跨品类权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口预览订单
  - HTTP状态码为200，响应包含usedEntitlementBreakdown数组，存在sourceType为cross_module的对象，该对象不包含tier字段，entitlements展示实际扣除的跨品类权益明细

##### tc-p2: 预览订单同时使用单品类和跨品类权益返回多个breakdown对象

- pc: 用户同时有单品类和跨品类权益，预览订单同时扣除两种权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口预览订单
  - HTTP状态码为200，usedEntitlementBreakdown数组包含多个对象，包含module_exclusive对象（含tier字段）和cross_module对象（不含tier字段），各对象的entitlements明细与实际扣除一致

#### 权益明细展示规则

##### tc-p1: 仅扣除持卡人权益时entitlements只展示cardholderExclusiveEntitlements

- pc: 预览订单仅扣除持卡人专属权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口预览订单
  - entitlements中cardholderExclusiveEntitlements>0，guestsExclusiveEntitlements、sharedEntitlements、purchasedEntitlements值为0或不展示

##### tc-p2: 扣除多种权益类型时entitlements展示所有扣除项

| 扣除权益组合 | cardholderExclusiveEntitlements | guestsExclusiveEntitlements | sharedEntitlements | purchasedEntitlements |
|------------|--------------------------------|----------------------------|-------------------|----------------------|
| 持卡人+共享 | >0 | 0 | >0 | 0 |
| 持卡人+买点 | >0 | 0 | 0 | >0 |
| 携伴+共享 | 0 | >0 | >0 | 0 |
| 持卡人+携伴+共享+买点 | >0 | >0 | >0 | >0 |

- 按上表数据组合执行预览订单
  - 每种组合下entitlements中各字段值符合上表预期，未扣除的权益类型字段值为0

##### tc-p2: 未扣除某类权益时该字段值为0

- pc: 预览订单未使用swap/跨品类权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口预览订单
  - usedEntitlementBreakdown中不包含sourceType为cross_module的对象（或cross_module对象不存在）

#### tier字段规则

##### tc-p1: FT/Lounge预览订单扣除tier1权益返回tier=1

- pc: 用户有tier1等级的FT或Lounge权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口（modules=ft或lounge）
  - usedEntitlementBreakdown中module_exclusive对象的tier字段值为1

##### tc-p2: FT/Lounge预览订单扣除不同tier权益返回多个breakdown对象

- pc: 用户同时有tier1和tier2的权益，预览订单同时扣除两个tier的权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口
  - usedEntitlementBreakdown数组包含2个module_exclusive对象，一个tier=1另一个tier=2，各对象的entitlements分别展示对应tier的扣除明细
- rc: 一般情况下单品类不会扣除2个tier的权益，除非配置错误

##### tc-p2: 未使用tier权益时不返回tier字段

- pc: 用户仅使用跨品类权益，未使用单品类tier权益
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口
  - usedEntitlementBreakdown中cross_module对象不包含tier字段

#### 合并规则验证

##### tc-p1: 同品类同tier扣除多种权益类型合并到一个object

- pc: 用户休息室tier1同时有持卡人点、共享点、买点，预览订单同时扣除这3种权益
- 调用POST_v2_orders_lounge_memberships_prebooking_preview接口
  - usedEntitlementBreakdown中只有1个tier=1的module_exclusive对象，该对象的entitlements包含cardholderExclusiveEntitlements、sharedEntitlements、purchasedEntitlements，3种权益明细合并在同一个entitlements对象中

##### tc-p2: 配置多种跨品类权益（如134+13）扣除时合并为1个cross_module

- pc: 项目配置了134和13两种跨品类权益，预览订单同时扣除2个跨品类权益点
- 调用POST_v2_orders_{modules}_memberships_prebooking_preview接口
  - usedEntitlementBreakdown中最多只有1个sourceType为cross_module的对象，该对象的entitlements合并展示所有跨品类权益扣除明细

---

## 创建订单接口（CreateMembershipPrebookingOrder）

### v2_orders_{modules}_memberships_prebooking

#### 正向场景验证

##### tc-p1: Lounge/FT创建订单成功返回usedEntitlementBreakdown含tier字段

- pc: 用户有Lounge或FT单品类权益
- 调用POST_v2_orders_{modules}_memberships_prebooking接口创建订单（modules=lounge或ft）
  - HTTP状态码为200/201，响应包含usedEntitlementBreakdown数组，module_exclusive对象包含tier字段，entitlements展示实际扣除的权益明细

##### tc-p1: eSIM/Fitness创建订单成功返回usedEntitlementBreakdown不含tier字段

- pc: 用户有eSIM或Fitness权益
- 调用POST_v2_orders_esims_memberships_topup或POST_v2_orders_fitness_memberships_prebooking接口
  - HTTP状态码为200/201，响应包含usedEntitlementBreakdown数组，对象不包含tier字段，entitlements展示实际扣除的权益明细

##### tc-p2: 创建订单使用跨品类权益返回cross_module对象

- pc: 用户配置了跨品类权益，创建订单扣除跨品类权益
- 调用POST_v2_orders_{modules}_memberships_prebooking接口创建订单
  - usedEntitlementBreakdown中存在sourceType为cross_module的对象，该对象不包含tier字段，entitlements展示跨品类权益扣除明细

#### 各模块sourceType验证

##### tc-p1: 各模块创建订单sourceType按权益类型正确返回

| 模块 | 权益类型 | 期望sourceType | 是否有tier |
|-----|---------|---------------|----------|
| Lounge | 单品类 | module_exclusive | 是 |
| FT | 单品类 | module_exclusive | 是 |
| eSIM | 单品类 | module_exclusive | 否 |
| Fitness | 单品类 | module_exclusive | 否 |
| 任意模块 | 跨品类 | cross_module | 否 |

- 按上表数据组合执行创建订单
  - 每种组合下sourceType和tier字段存在性符合上表预期

### v2_orders_esims_memberships_topup

##### tc-p1: eSIM充值订单返回usedEntitlementBreakdown

- pc: 用户有eSIM权益
- 调用POST_v2_orders_esims_memberships_topup接口创建充值订单
  - HTTP状态码为200/201，响应包含usedEntitlementBreakdown数组，sourceType为module_exclusive，不包含tier字段，entitlements展示实际扣除的权益明细

---

## 订单详情接口（RetrieveMembershipUsageOrderDetails）

### v2_orders_memberships_details

#### 正向场景验证

##### tc-p1: Lounge/FT/Setmeal订单详情返回usedEntitlementBreakdown含tier字段

- pc: 已创建Lounge、FT或Setmeal订单
- 调用GET_v2_orders_memberships_details接口查询订单详情
  - HTTP状态码为200，响应包含usedEntitlementBreakdown数组，module_exclusive对象包含tier字段，entitlements展示该订单实际扣除的权益明细

##### tc-p1: Dining/eSIM/Fitness订单详情返回usedEntitlementBreakdown不含tier字段

- pc: 已创建Dining、eSIM或Fitness订单
- 调用GET_v2_orders_memberships_details接口查询订单详情
  - HTTP状态码为200，响应包含usedEntitlementBreakdown数组，对象不包含tier字段，entitlements展示该订单实际扣除的权益明细

##### tc-p2: 订单详情usedEntitlementBreakdown与创建订单时一致

- pc: 已创建订单并记录创建时的usedEntitlementBreakdown
- 调用GET_v2_orders_memberships_details接口查询订单详情
  - usedEntitlementBreakdown数组内容与创建订单时返回的一致，sourceType、tier、entitlements各字段值完全匹配

#### 各模块tier字段验证

##### tc-p1: 各模块订单详情tier字段返回规则

| 模块 | 是否返回tier字段 |
|-----|----------------|
| Lounge | 是 |
| FT | 是 |
| Setmeal | 是 |
| Dining | 否 |
| eSIM | 否 |
| Fitness | 否 |

- 按上表各模块查询订单详情
  - 每个模块的tier字段存在性符合上表预期

---

## 边界场景验证

### 空值和特殊场景

##### tc-p2: 订单未扣除任何权益时usedEntitlementBreakdown为空数组

- pc: 订单场景不扣除任何权益（如免费订单）
- 调用相关接口
  - usedEntitlementBreakdown字段存在且为空数组[]

##### tc-p3: entitlements中所有字段值均为0的场景

- pc: 特殊配置场景导致扣除0点权益
- 调用相关接口
  - usedEntitlementBreakdown正常返回，entitlements对象中各字段值为0

### 数据一致性验证

##### tc-p1: 预览订单与创建订单的usedEntitlementBreakdown一致

- pc: 使用相同参数先预览后创建订单
- 调用preview接口获取usedEntitlementBreakdown
  - 记录预览返回的usedEntitlementBreakdown
- 调用创建订单接口
  - 创建订单返回的usedEntitlementBreakdown与预览时一致，sourceType、tier、entitlements各字段值完全匹配

##### tc-p2: 创建订单与订单详情的usedEntitlementBreakdown一致

- pc: 已创建订单
- 调用GET_v2_orders_memberships_details接口查询订单详情
  - 订单详情中的usedEntitlementBreakdown与创建订单时返回的一致，数据持久化正确

---

## 字段格式验证

### entitlements对象字段

##### tc-p2: entitlements对象包含正确的字段结构

- pc: 订单扣除了权益
- 调用相关接口
  - entitlements对象包含cardholderExclusiveEntitlements、guestsExclusiveEntitlements、sharedEntitlements、purchasedEntitlements字段（均为整数类型且>=0）

##### tc-p3: usedEntitlementBreakdown数组元素顺序验证

- pc: 订单同时扣除单品类和跨品类权益
- 调用相关接口
  - usedEntitlementBreakdown数组正确返回多个元素，各元素结构完整包含sourceType和entitlements
- rc: 验证数组元素顺序是否有特定规则
