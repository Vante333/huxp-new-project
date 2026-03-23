# SWAPEntitlementPhase2测试用例

## Membership接口

### v2_entitlements_search与v2_memberships

#### 正向场景验证

##### tc-p1: 会员仅存在单品类权益时返回ModuleExclusiveEntitlements且EnabledTypes仅为1

- pc: 会员仅配置单品类权益且无跨品类swap权益
- 调用GET_v2_entitlements_search查询该会员权益
  - HTTP状态码为200且响应体仅返回`moduleExclusiveEntitlements`并且`enabledTypes`仅包含`1`
- 对比响应中的单品类权益明细与SaaS会籍配置
  - 响应中的单品类权益数量和字段值与配置保持一致

##### tc-p1: 会员仅存在跨品类Swap权益时返回CrossModuleEntitlements且EnabledTypes仅为2

- pc: 会员仅配置跨品类swap权益且无单品类权益
- 调用GET_v2_entitlements_search查询该会员权益
  - HTTP状态码为200且响应体仅返回`crossModuleEntitlements`并且`enabledTypes`仅包含`2`
- 校验`crossModuleEntitlements[*].entitlementPoolId`与会籍配置映射关系
  - 每个`entitlementPoolId`均与实际权益明细编码一一对应

##### tc-p1: 会员同时存在单品类与跨品类Swap权益时两类权益均返回且EnabledTypes为1和2

- pc: 会员同时配置单品类权益和跨品类swap权益
- 调用GET_v2_entitlements_search查询该会员权益
  - HTTP状态码为200且响应体同时包含`moduleExclusiveEntitlements`和`crossModuleEntitlements`
- 校验`enabledTypes`及两类权益明细
  - `enabledTypes`同时包含`1`和`2`且权益明细与SaaS会籍配置一致

#### 结构与字段规则验证

##### tc-p2: 验证CrossModuleEntitlementsDetails中三类权益字段返回规则

- pc: 会员存在跨品类swap权益且详情中包含持卡人专属携伴专属和共享权益
- 调用GET_v2_entitlements_search查询该会员权益
  - 响应中的`details.cardholderExclusiveEntitlements`、`details.guestsExclusiveEntitlements`、`details.sharedEntitlements`字段返回行为与设计一致
- 针对值为0的权益字段执行校验
  - 值为0时返回0或不返回字段均可但必须与约定保持一致且行为稳定

##### tc-p2: 验证CrossModuleEntitlementsApplicableModules返回跨品类组合与配置一致

- pc: 分别准备休息室+Setmeal、Setmeal+Coupon、休息室+Coupon和三者皆有四种配置数据
- 调用GET_v2_entitlements_search查询各配置下会员权益
  - `applicableModules`返回的module枚举集合与各自配置完全一致
- 对比phase1中E-pass多品类模块枚举
  - 本次返回的module枚举与phase1行为一致

### v2_entitlements_update

#### 双定位模式验证

##### tc-p1: 仅传ModuleTier定位可成功更新单品类权益

- pc: 会员存在可更新的单品类权益且`membershipId+module+tier`可唯一定位权益池
- 调用PUT_v2_entitlements_update仅传`membershipId`、`module`、`tier`和待更新数值字段
  - 接口更新成功并正确定位对应`entitlementPoolId`且该单品类权益池数值被正确更新
- 校验返回体结构
  - 返回体`entitlements`结构完整且包含更新后的`moduleExclusiveEntitlements`

##### tc-p1: 仅传EntitlementPoolId可成功更新单品类或跨品类权益

- pc: 准备合法且归属于当前会员的`entitlementPoolId`
- 调用PUT_v2_entitlements_update仅传`entitlementPoolId`和待更新数值字段
  - 接口可精确定位对应权益池并成功更新目标字段
- 校验返回体中两类权益状态
  - 返回体`entitlements`反映最新权益结果并与更新后的数据库状态一致

##### tc-p1: 同时传EntitlementPoolId与ModuleTier时返回参数冲突且不更新

- pc: 会员存在可更新权益池
- 调用PUT_v2_entitlements_update同时传`entitlementPoolId`与`module`、`tier`
  - 接口返回4xx或业务参数冲突错误码
- 查询更新前后权益池数据
  - 任一权益池数值均未发生变化

#### 原有入参与兼容性

##### tc-p2: 沿用历史入参仅更新单品类权益时返回结构与历史版本一致

- pc: 准备仅单品类权益会员和单品类+swap混合权益会员各一组
- 调用PUT_v2_entitlements_update仅传历史兼容参数更新单品类权益
  - 单品类权益更新成功且返回结构与phase1定义保持一致
- 校验混合权益会员中的跨品类权益是否被影响
  - `crossModuleEntitlements`保持不变

#### Swap权益更新验证

##### tc-p1: 指定合法EntitlementPoolId可成功更新跨品类Swap权益

- pc: 入参`entitlementPoolId`对应合法swap权益池
- 调用PUT_v2_entitlements_update更新`usageRestriction`或`quantity`或`purchasedQuantity`
  - `crossModuleEntitlements`中对应权益池字段值按请求正确变化
- 校验返回中的启用类型
  - 返回体`enabledTypes`包含`2`且与会员实际跨品类权益状态一致

##### tc-p2: 使用不存在或不属于当前会员的EntitlementPoolId返回错误且不更新

- pc: 准备不存在的`entitlementPoolId`和属于其他会员的`entitlementPoolId`
- 调用PUT_v2_entitlements_update发起更新请求
  - 接口返回明确错误码和提示信息
- 查询会员权益池数据
  - 当前会员任一权益池均未被更新

##### tc-p2: 更新Swap权益传入负数或超上限时返回参数错误且数据不变

- pc: 会员存在可更新swap权益池且已知系统数值上限
- 调用PUT_v2_entitlements_update分别传入负数和超上限值
  - 接口返回参数校验错误
- 对比更新前后权益池数值
  - 对应权益池数值保持不变

#### 返回结构完整性

##### tc-p1: 更新单品类或跨品类权益后返回体均包含最新完整权益状态

- pc: 准备单品类权益会员和混合权益会员各一组
- 调用PUT_v2_entitlements_update分别更新单品类和跨品类权益
  - 成功响应中的`data.entitlements`均返回最新完整权益状态
- 校验`enabledTypes`字段返回逻辑
  - 会员存在swap权益时包含`2`不存在swap权益时不包含`2`

### v2_entitlements_details

#### CrossModuleEntitlement限制验证

##### tc-p1: 会员仅有跨品类Swap权益时调用Details接口返回500030030

- pc: 会员仅配置swap权益且无单品类权益
- 调用GET_v2_entitlements_details并传入swap覆盖范围内任一module
  - 接口返回错误码`500.030.030`
- 校验错误信息和返回内容
  - 错误信息与文档一致且不返回任何swap权益details

##### tc-p1: 会员同时拥有单品类与Swap权益时Details仅返回单品类明细

- pc: 会员同时拥有单品类权益和swap权益
- 调用GET_v2_entitlements_details并传入单品类对应module
  - 接口仅返回单品类权益details
- 校验是否出现跨品类明细
  - 响应中不返回任何cross module entitlement相关明细

##### tc-p2: 会员无权益或传入无效Module时按约定返回错误且不命中500030030

- pc: 准备无任何权益会员以及传入与会员权益无关module两类数据
- 调用GET_v2_entitlements_details分别发起请求
  - 接口返回空结果或约定业务错误且无效module场景不返回`500.030.030`

## 资源接口

### 复用Epass资源配置逻辑

#### 资源检索与可用范围

##### tc-p2: 跨品类Swap权益在资源检索接口可检索到对应多品类资源

- pc: 会籍模板已配置swap权益并覆盖多个module
- 调用GET_v2_resources和GET_v2_search等资源相关接口
  - 可按`applicableModules`检索到对应的lounge或setmeal或coupon资源
- 对比phase1多品类E-pass行为
  - 资源可用性行为与phase1保持一致

##### tc-p3: Swap场景下资源更新与下架逻辑保持历史行为一致

- pc: program下存在swap配置并已准备可上下架资源
- 调用GET_v2_resources_updates验证资源更新与下架行为
  - 资源上下架与更新结果与phase1保持一致且本次改动未引入回归

## 下单与权益统计

### Preview与下单前权益计算

#### 单品类与跨品类合并统计

##### tc-p1: 仅有单品类权益时预览与下单前统计仅包含单品类权益

- pc: 会员仅配置单品类权益且无swap权益
- 发起预览与下单前权益计算请求
  - 统计结果仅基于`moduleExclusiveEntitlements`明细计算
- 对比历史实现基线结果
  - 统计值与历史实现一致

##### tc-p1: 仅有跨品类Swap权益时预览与下单前统计仅包含跨品类权益

- pc: 会员仅配置swap权益且无单品类权益
- 发起预览与下单前权益计算请求
  - 统计结果仅基于`crossModuleEntitlements`明细计算
- 对比可用权益数量与权益明细
  - 统计值与swap权益明细中的剩余权利数一致

##### tc-p1: 同时存在单品类与跨品类权益时统计总数为两者之和

- pc: 会员同时拥有单品类权益和swap权益
- 发起预览与下单前权益计算请求
  - 统计总数等于单品类可用数量与跨品类可用数量之和
- 校验订单可用权益来源
  - 单品类和跨品类权益均可参与订单计算

#### 权益状态过滤规则

##### tc-p2: 仅统计待使用和已用完状态权益不统计已作废冻结已过期

- pc: 会员权益明细同时包含待使用已用完已作废冻结已过期状态
- 发起预览与下单前权益计算请求
  - 统计结果仅计入待使用和已用完状态明细
- 校验非计入状态
  - 已作废冻结和已过期状态均不计入初始或剩余统计

##### tc-p2: 跨品类Swap权益状态过滤规则与单品类规则一致

- pc: swap权益下准备多状态明细数据
- 发起预览与下单前权益计算请求
  - swap权益应用与单品类相同的状态过滤规则
- 校验合并统计结果
  - 最终统计结果为单品类和跨品类中待使用与已用完明细之和

### 订单取消

#### SaaS回退与PAPI行为

##### tc-p2: 取消订单后权益由SaaS回退且PAPI不执行重复回退

- pc: 会员使用单品类或跨品类权益完成下单
- 取消订单后查询权益回退来源与动作日志
  - 权益由SaaS回退且PAPI未对同一订单执行二次回退
- 取消后再次查询会员权益
  - 会员权益余额与回退后的实际值一致

##### tc-p3: 重复取消同一订单时权益余额保持幂等

- pc: 存在已取消订单并可重复触发取消请求
- 对同一订单执行重复取消或重放取消请求
  - PAPI不会因重复请求导致权益多次回退
- 查询会员最终权益余额
  - 最终权益余额与首次取消后的结果一致

