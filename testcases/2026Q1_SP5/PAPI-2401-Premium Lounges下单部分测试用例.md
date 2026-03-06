# Premium Lounges 预定链路测试用例（PAPI-2401，关联 PAPI-2214）

## 资源预定可用性接口 `/v2/resources/prebookings/availability` & `/v2/resources/options/prebookings/availability`

### 正向场景验证

#### 正常可预定资源

##### tc-P1-RES-AVAIL-001：项目清单+价格清单内且支持预定的 lounge 资源可正常返回可预定结果
- tc-P1: HTTP 状态码为 200
- tc-P1: 响应返回查询的 lounge 资源，包含资源名称、资源 ID、可预定时间段等关键字段
- tc-P1: 不进行任何权益/点数判断，仅基于资源是否在项目+价格清单+支持预定范围内返回结果
- tc-P1: 与改造前同配置下行为一致（回归验证）

##### tc-P1-RES-AVAIL-002：项目清单+价格清单内且支持预定的 lounge ft 资源可正常返回可预定结果
- tc-P1: HTTP 状态码为 200
- tc-P1: 响应返回对应 lounge ft 资源，结构与普通 lounge 一致
- tc-P1: 资源类型字段或标签标识正确（区分 lounge / lounge ft）
- tc-P1: 查询多资源时，所有支持预定的资源均出现在结果中

#### 规则与错误码验证

##### tc-P1-RES-AVAIL-003：资源在项目中不支持预定时返回错误码 500.020.027
- tc-P1: 选取在项目清单+价格清单内但关闭预定功能的 lounge 资源进行查询
- tc-P1: HTTP 状态码为 4xx/5xx（按系统现有约定），业务错误码为 `500.020.027`
- tc-P1: 中文错误提示为 `该资源在当前program下未启用预约功能`
- tc-P1: 英文错误提示为 `Precooking is not available for this resource under the current program.`
- tc-P1: 不返回该资源的可预定时段数据

##### tc-P1-RES-AVAIL-004：资源不在当前 program 可用范围时返回错误码 500.020.007
- tc-P1: 选取不在当前 program 可用范围内的 lounge 资源 ID 进行查询
- tc-P1: HTTP 状态码为 4xx/5xx（按系统现有约定），业务错误码为 `500.020.007`
- tc-P1: 中文错误提示为 `查询的资源id该program不可用`
- tc-P1: 英文错误提示为 `Sorry, this resource is not accessible with your program.`
- tc-P1: 不返回该资源的任何可用性信息

##### tc-P2-RES-AVAIL-005：资源在多个 tier 分组下时，仍按项目可用性规则正确返回
- tc-P2: 选取在 BOSS 中同时属于多个 tier 网络分组的 lounge 资源进行查询（关联 PAPI-2214 告警场景）
- tc-P2: 如果该资源在项目中支持预定，则可用性查询仍返回可预定结果
- tc-P2: 不因资源存在多个 tier 而误返回 `500.020.007` 或 `500.020.027`
- tc-P2: 内部可触发相应告警，但对接口返回无影响（仅监控层）

### 边界值与异常场景验证

##### tc-P2-RES-AVAIL-006：缺失必填参数（如 program/project）时的参数校验
- tc-P2: 不传 programId 或 projectId 调用接口
- tc-P2: 返回参数错误码/HTTP 400，提示必填参数缺失
- tc-P2: 不进入资源可用性业务逻辑

##### tc-P2-RES-AVAIL-007：传入不存在的 resourceId 时的处理
- tc-P2: 传入格式合法但不存在的 resourceId
- tc-P2: 返回资源不可用相关错误码（可为 `500.020.007` 或约定的资源不存在错误）
- tc-P2: 错误提示信息不与“未启用预约功能”混淆

##### tc-P3-RES-AVAIL-008：批量查询大量资源时分页与性能表现
- tc-P3: 使用大数量资源 ID（接近或达到分页上限）进行查询
- tc-P3: 每页返回数量符合分页约定（如 pageSize）
- tc-P3: 响应时间在可接受范围内，无明显性能退化

---

## 订单预览接口 `/v2/orders/{modules}/memberships/prebooking/preview`

### 正向场景验证（分级权益 + Premium Lounges）

##### tc-P1-ORDER-PREVIEW-001：scopeType=2 且目标 tier 权益充足时预览成功并按 tier 返回 usedEntitlementDetails
- tc-P1: 会籍 module=1（lounge）配置为 scopeType=2，至少存在一个 tier 对应的 lounge 权益（关联 PAPI-2214）
- tc-P1: 选择该 tier 下的 lounge 资源，持卡人/携伴人数在可用点数范围内
- tc-P1: 调用预览接口，HTTP 状态码为 200，业务 code=0
- tc-P1: `extra.usedEntitlementDetails.tier` 等于资源的 tier
- tc-P1: `tierEntitlements.cardholderExclusiveEntitlements` 等字段扣减值与人数、权益规则匹配
- tc-P1: 预览不跨 tier 汇总扣减，仅在一个 tier 上扣减

##### tc-P1-ORDER-PREVIEW-002：资源仅属于单一 tier 时，预览计算仅使用该 tier 权益
- tc-P1: BOSS 中将 lounge 资源只配置在 tier=2 分组
- tc-P1: 会籍在 tier=2 下有足够 lounge 权益
- tc-P1: 预览时 `usedEntitlementDetails.tier=2`
- tc-P1: 调用 `/v2/entitlements/details` 时，扣减的 tier=2 明细与预览中展示的扣减值保持一致（关联 PAPI-2214）

### 多 tier 与多明细规则验证

##### tc-P1-ORDER-PREVIEW-003：资源跨多个 tier 分组时以最小 tier 进行判断与扣减
- tc-P1: BOSS 中同一 lounge 资源同时存在于 tier=1 和 tier=2 分组
- tc-P1: 会籍在 tier=1 和 tier=2 下均有可用权益
- tc-P1: 预览返回 `usedEntitlementDetails.tier=1`（最小 tier）
- tc-P1: 扣减只发生在 tier=1 对应的权益明细上，不混用 tier=2
- tc-P1: 如配置了告警，则仅在监控侧出现“资源多分组告警”，接口正常返回（关联 PAPI-2214 告警机制）

##### tc-P2-ORDER-PREVIEW-004：同一 tier 下存在多条权益明细时，先聚合后再判断与扣减
- tc-P2: 会籍在 tier=2 下存在多条 lounge 权益明细（例如来自不同模板迁移），总和足够
- tc-P2: 预览时内部先对 tier=2 下同类字段（持卡人专属/携伴专属/共享）求和后再判断
- tc-P2: `tierEntitlements` 中的扣减值基于聚合后的可用额度
- tc-P2: 扣减后再通过 `/v2/entitlements/details` 查询，对应 tier=2 的所有明细变动总和与预览扣减一致

##### tc-P2-ORDER-PREVIEW-005：一笔订单仅扣减一个 tier，不支持跨 tier 扣减
- tc-P2: 会籍在 tier=1 和 tier=2 下都有 lounge 权益，任意单个 tier 的权益不足、两者合计足够
- tc-P2: 预览结果为“权益不足”而非自动跨 tier 聚合
- tc-P2: 不会出现部分在 tier=1、部分在 tier=2 扣减的情况
- tc-P2: 通过 `/v2/entitlements/details` 验证，各 tier 权益余额均保持原值

### 边界值与异常场景验证

##### tc-P2-ORDER-PREVIEW-006：可用权益刚好等于所需点数时预览成功
- tc-P2: 目标 tier 下的可用 lounge 权益点数刚好满足本次预定所需
- tc-P2: 预览成功，`tierEntitlements` 中扣减值等于可用点数
- tc-P2: 再次预览同一订单（不创建）不改变后端实际余额

##### tc-P1-ORDER-PREVIEW-007：权益不足导致预览失败时的错误码与提示
- tc-P1: 目标 tier 下可用 lounge 权益少于本次预定所需
- tc-P1: 预览返回业务错误，明确表达“权益不足”，不使用资源不可用错误码 `500.020.007/027`
- tc-P1: 不返回 `usedEntitlementDetails` 或仅返回空/0 值
- tc-P1: `/v2/entitlements/details` 中权益余额保持不变

##### tc-P2-ORDER-PREVIEW-008：会员无分级权益但资源存在 tier 时的行为（scopeType=1）
- tc-P2: module=1 为 scopeType=1（GLOBAL），但资源在 BOSS 中配置 tier
- tc-P2: 确认预期业务规则（例如：是否允许按非分级逻辑预定或直接拒绝），并验证实现与设计一致
- tc-P2: 如果拒绝下单，应有清晰错误码与提示，区分于资源不可用与权益不足
- tc-P2: 如允许预定，应明确使用 GLOBAL 权益进行扣减，不依赖 tier 逻辑（关联 PAPI-2214）

---

## 订单创建接口（Premium Lounges 预定下单）

### 正向场景验证

##### tc-P1-ORDER-SUBMIT-001：在预览成功且权益充足的前提下创建订单成功
- tc-P1: 先调用预览接口，确认权益充足并记录 `usedEntitlementDetails.tier` 与扣减值
- tc-P1: 使用相同参数调用下单接口，订单创建成功（HTTP 200，业务 code=0）
- tc-P1: 返回订单号、订单状态等信息正确
- tc-P1: 通过 `/v2/entitlements/details` 查询，目标 tier 下权益余额已按预览的扣减值减少（由 SaaS 扣减）

##### tc-P1-ORDER-SUBMIT-002：订单创建时再次检测权益充足，防止预览后被占用
- tc-P1: 预览阶段显示权益充足，但在下单前通过其他操作消耗了目标 tier 的部分权益
- tc-P1: 一段时间后发起下单请求
- tc-P1: 若权益已不足，下单失败，并返回权益不足相关错误码，而非资源不可用错误
- tc-P1: `/v2/entitlements.details` 中权益余额与失败前状态一致（无扣减）

### 资源与配置变化场景

##### tc-P2-ORDER-SUBMIT-003：预览后资源被关闭预定或移出项目时的下单行为
- tc-P2: 预览成功后，在 BOSS 中将该资源关闭预定或从项目清单/价格清单中移除
- tc-P2: 再次尝试下单
- tc-P2: 下单失败，返回资源不可用相关错误（可为 `500.020.007/027` 或单独下单错误码），提示重点为“资源不可用/未启用预约”
- tc-P2: 不进行权益扣减

##### tc-P2-ORDER-SUBMIT-004：订单创建成功后，权益扣减与预览一致且仅扣减一个 tier
- tc-P2: 选择同时在 tier=1、tier=2 有权益的会籍，按资源 tier=2 预定成功
- tc-P2: 下单后 `/v2/entitlements/details` 中仅 tier=2 的 lounge 明细被扣减
- tc-P2: tier=1 明细保持原值
- tc-P2: 扣减金额与预览中的 `tierEntitlements` 值一致

### 异常与回滚验证

##### tc-P2-ORDER-SUBMIT-005：SaaS 扣减失败时订单回滚与权益一致性
- tc-P2: 模拟 SaaS 扣减失败（如超时、内部错误）
- tc-P2: PAPI 不将订单标记为成功状态（可为失败或待确认状态，视设计）
- tc-P2: `/v2/entitlements.details` 中对应 tier 的权益余额未发生变化
- tc-P2: 不出现订单成功但权益未扣减或订单失败但权益已扣减的情况

---

## 分级权益基础接口联合验证（关联需求：PAPI-2214）

### `/v2/memberships` 与 `/v2/entitlements/search`/`/v2/entitlements/details` 一致性

##### tc-P1-ENT-TIER-001：Premium Lounges 所在 module scopeType=2 时，预览/下单使用的权益来源与 details 明细一致
- tc-P1: module=1（lounge）在 memberships/search 中 `scopeType=2`
- tc-P1: `/v2/entitlements/details` 对该 module 返回按 tier 分组的明细
- tc-P1: Premium Lounges 预览/下单仅在资源对应 tier 的明细上进行额度计算
- tc-P1: 下单后，再次调用 details 验证对应 tier 的明细变化与扣减值一致

##### tc-P2-ENT-TIER-002：update 接口更新某个 tier 后，Premium Lounges 预览/下单使用最新数据
- tc-P2: 先记录某会员在 tier=2 下 lounge 权益的明细值
- tc-P2: 使用 `/v2/entitlements/update` 更新 tier=2 lounge 权益
- tc-P2: 再次预览/下单时，使用更新后的额度进行判断与扣减
- tc-P2: 下单后的 details 数据等于“更新后初始值 - 本次预订单扣减值”

### 错误码与非支持场景验证

##### tc-P2-ENT-TIER-003：Premium Lounges 不使用 SWAP（crossModuleEntitlements）中的权益进行预定判断
- tc-P2: 会籍同时存在单品类 lounge 权益与跨品类 SWAP 权益（lounge+setmeal+coupon）
- tc-P2: Premium Lounges 预览/下单时，仅使用 moduleExclusive（按 tier 的 lounge 权益）进行计算
- tc-P2: 不把 crossModuleEntitlements 中的共享权益作为 lounge 预定可用额度
- tc-P2: 当单品类 lounge 权益不足但 SWAP 权益充足时，仍返回“权益不足”

##### tc-P3-ENT-TIER-004：仅有 SWAP 权益无单品类 lounge 权益时，Premium Lounges 下单策略
- tc-P3: 会籍仅配置跨品类 SWAP 权益，不配置 module=1 的单品类 lounge 权益
- tc-P3: 调用 Premium Lounges 预览/下单接口
- tc-P3: 确认实际设计预期（例如不允许依赖 SWAP 权益预定 Premium Lounges），并验证返回错误码与提示
- tc-P3: `/v2/entitlements.details` 仅对 moduleExclusive 生效，对 SWAP 不提供 tier 明细（回归 SWAP phase 2 行为）

---

## 业务场景与端到端流程验证

### scopeType=2 分级下 Premium Lounges 主流程

##### tc-P1-INTEG-PL-001：scopeType=2 端到端主流程：查可用性 → 查权益明细 → 预览订单 → 创建订单
- tc-P1: 资源在项目+价格清单内且支持预定，可用性查询成功（不涉及权益判断）
- tc-P1: `/v2/entitlements.details` 按 tier 返回 lounge 权益明细，scopeType=2
- tc-P1: 预览订单根据资源 tier 与明细正确计算扣减并返回 `usedEntitlementDetails`
- tc-P1: 创建订单成功，SaaS 正确扣减对应 tier 的 lounge 权益
- tc-P1: 再次调用 details，确认扣减后的余额与预览/下单一致

##### tc-P2-INTEG-PL-002：资源跨多个 tier 分组 + 会籍多 tier 权益时端到端行为
- tc-P2: 资源在 tier=1 与 tier=2 分组，会籍在两个 tier 下均有 lounge 权益
- tc-P2: 可用性查询成功返回可预定结果
- tc-P2: 预览/下单均以最小 tier=1 进行判断与扣减
- tc-P2: details 中仅 tier=1 的权益明细变化，tier=2 保持不变
- tc-P2: 如存在资源多分组告警，仅在监控侧体现，不影响主流程

