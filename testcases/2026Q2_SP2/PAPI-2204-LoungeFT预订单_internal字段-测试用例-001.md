# PAPI-2204Lounge与FT预订单_internal与订单详情回显测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2204.md`；下单：`/api/v2/orders/fastTrack/memberships/prebooking`、`/api/v2/orders/lounges/memberships/prebooking`；详情：`/api/v2/orders/memberships/details`。
- rc: `extra._internal` 含 `_amount`、`_currency`、`_exchangeRate`（下划线前缀）；**Nacos 租户白名单** 控制是否允许传入；未配置租户传入则 **统一兜底错误**；创建时不校验仅记录；**未配置租户查询不返回整个 object**；**已配置无值返回 null**。

## v2_orders_fastTrack_memberships_prebooking与v2_orders_lounges_memberships_prebooking（下单）


### tc-p1: 白名单租户传合法extra._internal时下单成功且订单可查到持久化特征

pc: Nacos（或生效配置源）已配置当前租户允许 `_internal`；构造合法 Lounge 与 FT 各一单

- 调用 Lounge 与 FT prebooking 创建接口，在 `extra` 中传入完整 `_internal` 三字段
  - 两接口均成功；后续通过订单详情可查得与 SaaS `ord.order feature` 映射一致的结构（以 APIFOX 字段为准）

### tc-p1: 非白名单租户传入extra._internal时返回统一兜底错误

pc: 当前租户未出现在允许列表

- 调用任一下单接口并传入 `_internal`
  - 失败；业务错误码与「租户未开放」类兜底一致（以 APIFOX 为准）

### tc-p2: 白名单租户不传_internal时下单成功且不强制要求该对象

pc: 白名单租户；其余必填合法

- 调用下单不传 `extra._internal`
  - 成功；不因缺失 `_internal` 被拒

### tc-p2: 白名单租户传部分_internal字段时行为符合APIFOX（不校验仅记录）

pc: 仅传 `_amount` 或缺省其它字段（若允许）

- 调用下单
  - 成功；落库或 feature 中未传字段表现为 null 或省略，与实现约定一致

### tc-p3: _internal字段类型非法或明显越界时仍成功或按全局校验失败

pc: 与需求「创建时不校验」对齐；若网关仍有类型校验以 APIFOX 为准

- 传入类型错误金额或币种
  - 行为与 APIFOX 一致并记录结论

## v2_orders_memberships_details（订单详情）


### tc-p1: 白名单租户订单在详情中返回_internal结构与下单一致

pc: 已存在带 `_internal` 的 Lounge 或 FT 预订单且租户在白名单

- 调用 memberships/details 查询该订单
  - 响应中含 `_internal` 对象，字段与下单写入及 `ord.order feature` 映射一致

### tc-p1: 非白名单租户订单详情中不出现整个_internal对象

pc: 订单创建于未开放租户（或历史数据）；当前查询身份为该项目租户

- 调用详情接口
  - 响应中 **不包含** `_internal` 顶层对象（与需求「整个 object 都不返回」一致）

### tc-p2: 白名单租户订单无_internal数据时详情返回null对象

pc: 白名单租户下创建未传 `_internal` 的成功订单

- 查询详情
  - `_internal` 存在且值为 **null**（与需求「配置了没有值就返回 null」语义对齐；字段路径以 APIFOX 为准）

### tc-p3: FT与Lounge订单详情回显规则对称

pc: 各准备一条可查询订单

- 分别查询
  - 两者 `_internal` 回显规则一致，无模块差异遗漏
