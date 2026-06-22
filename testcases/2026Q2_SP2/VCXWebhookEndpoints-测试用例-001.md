# VCXWebhookEndpoints测试用例

## 测试范围说明

- rc: 源脑图：`d:\fenxi\清结算\2026_Q2\评审前\Q2_SP2\VCX Webhook endpoints.xmind`；文档结构与导入约定见 `.cursor/skills/test-case-design-with-priority/reference.md` 第四节及仓库 `testcases` Markdown 约定。
- rc: 覆盖 **vcx_callback** 内各 `receive*Event` 对应 **Visa VCX** 对外回调路径（Program/Project 库存、核销、订单、支付）；**Aero Blue 支付状态** 分支为 **SaasMq → 内部订单状态 →（条件性）ApiCallback → VCX** 链路，字段与状态枚举以 **Apifox / 清结算与订单域文档** 为准。
- rc: 脑图样例中出现的 `sandbox.api.visa.co` 与 `sandbox.api.visa.com`、路径大小写等以 **当前环境网关与 Visa 侧配置** 为准；用例中 URL 仅作定位关键字，执行前请核对现网基址。
- rc: 历史 `tc-p0` 若出现在其他材料中已映射为 `tc-p1`；本需求未使用 P0。
- rc: 下列用例在「可合并的同构场景」上已做适度合并；仍保留较多条以便按模块分工执行与缺陷定位。

## vcx_v1_events_inventory_program（Program级库存与资源元数据）

### tc-p1: API_RESOURCE_METADATA_CHANGED_GROUP_CALL_BACK消费后向VCX推送Program库存事件成功

- pc: MQ 主题 `API_RESOURCE_METADATA_CHANGED_GROUP_CALL_BACK` 可消费；样例 `groupId`、`programId`、`tenantCode`、`payload`（含 `eventType`、`batchId`、`sequence`、`module`、`resources`）与联调数据一致；VCX 回调 URL 已配置且鉴权有效
- 触发资源元数据/可用性变更，使业务向该 Topic 投递与脑图一致的 JSON 结构
  - 消费者处理成功；下游请求 `…/vcx/v1/events/inventory/program`（或环境等价路径）返回成功；VCX 或网关日志可关联 `groupId`/`programId`
- 校验 `payload` 内 `eventType`（如 `resource.metadata.updated`）与 `resources` 列表与变更事实一致
  - 字段语义与 Apifox 一致，无静默丢字段（除约定脱敏字段外）

### tc-p2: 回调VCX时缺少X-PAY-TOKEN等鉴权头导致失败可观测

- pc: 故意缺失或配置错误 `X-PAY-TOKEN`（或与该环境等效的鉴权头）；其余报文合法
- 执行回调处理器（如 `ResourceEventCallbackProcessor`）向 VCX 发起 HTTP
  - 请求失败；业务日志出现可检索的失败原因（脑图样例含「未携带X-pay-token」类描述）；不将失败误判为成功；重试策略符合设计（若有 `retryTimes` 则按约定递增或进入死信，以实现为准）

### tc-p2: tenantCode与programId归属或VCX侧Program配置不一致时不误报成功

- pc: 构造 `tenantCode` 与 `programId` 在内部主数据不存在或不匹配的组合；或 VCX 侧该 Program 未开通回调
- 消费并尝试回调
  - 返回明确失败或按规则跳过；监控与日志可区分「鉴权失败 / 资源不存在 / 租户不匹配」；不产生「已成功同步」的误报状态

### tc-p2: VCX返回401/403时停止无效重试或切换凭据策略符合设计

- pc: VCX 或网关稳定返回 401/403（可用联调桩）
- 触发回调并观察重试与告警
  - 不出现无限重试；达到阈值后有告警或人工可介入标识；凭据轮换后同报文可恢复成功（若产品支持）

### tc-p3: sequence与totalSequence分批场景下最后一包行为正确

- pc: 同一 `batchId` 下 `totalSequence`>1 的多条消息
- 按顺序投递直至 `sequence` 等于 `totalSequence`
  - 每包回调可被 VCX 接受或按幂等规则处理；最后一包后无重复全量错误回调（以产品与研发约定为准）

### tc-p3: 重复投递同一batchId与sequence消息时幂等不导致重复全量副作用

- pc: 与已成功消费的一条消息字节级相同，再次投递
- 观察 VCX 调用次数与内部落库/游标
  - 符合幂等：不重复产生对端重复资源变更或内部重复写；日志可标记重复投递

### tc-p3: payload内嵌JSON字符串转义非法或结构缺失时解析失败可定位

- pc: 破坏 `payload` 字符串内转义或删除必填内层字段
- 消费该消息
  - 解析失败有明确异常与 `traceId`；不发起半残缺 HTTP；不阻塞同 Topic 其他合法消息（以实现为准）

### tc-p3: resources列表为空或含不存在resourceId时的契约行为

- pc: `resources:[]` 或包含主数据中不存在的编码
- 回调或按规则短路
  - 行为与 Apifox/产品一致：要么合法空增量，要么拒绝并记录原因，且不造成 Program 侧脏数据

### tc-p3: VCX返回429或503时退避重试与上限符合配置

- pc: 桩或沙箱返回 429（带 Retry-After 若存在）或 503
- 触发回调
  - 退避间隔与最大重试次数符合配置；超过上限进入死信或可人工重放；无 tight loop

## vcx_v1_events_inventory_project（Project级库存与TransportHub）

### tc-p1: PROJECT_RESOURCE_METADATA_CALLBACK_TOPIC投递后Project与TransportHub元数据回调成功

- pc: Topic `PROJECT_RESOURCE_METADATA_CALLBACK_TOPIC`；`payload` 分别覆盖 `project.transportHub.metadata.updated` 与 `project.resource.metadata.updated`（脑图两类样例）
- 触发对应变更并消费消息
  - 回调 `…/vcx/v1/events/inventory/project`（或环境等价）成功；`projectId`、`transportHubs` 或 `module`+`resources` 与事实一致
- 检索应用日志关键字 `vcx/v1/events/inventory/project` 与业务文案（如「租户级别资源变更消息准备开始回调客户」类）及 `batchId`
  - 可唯一定位一次完整回调链路

### tc-p2: 回调请求体与Apifox文档字段对齐且敏感字段脱敏策略一致

- pc: 使用 Apifox 中该 Webhook 的请求体定义
- 比对实际 HTTP Body 与文档（含嵌套 JSON 字符串中的 `payload`）
  - 字段名、类型、必填/可选一致；`dpId` 等敏感标识脱敏规则与现网一致

### tc-p2: Apifox与对外文档字段不一致时的口径与回归清单（脑图备注）

- pc: 已识别差异字段列表（由研发/测试维护 checklist）
- 以对外文档为验收口径执行一次完整回调比对
  - 差异项在发布前已修复或已登记为已知限制并在监控中豁免误报

### tc-p2: projectId与tenantCode组合非法时不发起回调或失败可观测

- pc: `tenantCode` 无权限访问该 `projectId`
- 消费消息
  - 不静默成功；日志含拒绝原因；必要时进入死信队列

### tc-p3: updatedAt乱序（晚于已处理包的更早时间戳）时不覆盖较新状态

- pc: 连续两条消息 `updatedAt` 逆序
- 按到达顺序处理（若实现为「以时间戳为准」则按规则取较新）
  - VCX 最终可见状态与「较新事实」一致；无回滚为旧元数据

### tc-p3: transportHubs与resources两类事件短时间交错到达时最终一致

- pc: 同一 `projectId` 上交替投递两类 `eventType`
- 全部消费完成
  - Project 维度的 Hub 与资源元数据均与主数据一致；无互斥写丢失

## vcx_v1_events_redemption（Walk-in核销）

### tc-p1: API_TRANSPORT_HUB_METADATA_GROUP_CALL_BACK_TOPIC驱动walkin.redemption回调成功

- pc: Topic `API_TRANSPORT_HUB_METADATA_GROUP_CALL_BACK_TOPIC`；`verifyOrderCallbackDTO.eventType` 为 `walkin.redemption`；`orderId`、`programId`、`module`、`status`、`usageDate` 等与可核销订单一致
- 消费消息并回调 `…/vcx/v1/events/redemption`
  - HTTP 成功；`orderId` 与 `resourceId`/`transportHubId` 与订单域数据一致
- 核对 `passengers.cardholder`/`guests` 与下单人数一致
  - 数值与业务规则一致

### tc-p2: INTERNATIONAL_DEVELOPER_API_CALLBACK_VERIFY路径与核销校验一致

- pc: 存在需走 `INTERNATIONAL_DEVELOPER_API_CALLBACK_VERIFY` 的配置或租户
- 触发与脑图「明细用例」等价的核销完成事件
  - 校验 Topic 与回调体与 Apifox 一致；VCX 返回与订单状态联动正确

### tc-p2: guests大于0时passengers与资源点/人数业务规则一致

- pc: 订单含携客且 `guests`>0
- 发送核销完成回调
  - Body 中 `passengers` 与订单域一致；VCX 无拒识（以文档为准）

### tc-p2: retryTimes大于0时失败重试后成功或进入死信符合规则

- pc: 首次回调桩返回失败，`retryTimes` 已递增样例或配置允许重试
- 观察后续消费
  - 重试间隔与次数符合规则；最终成功或死信可人工补偿

### tc-p3: 回调体缺少category字段时的兼容或明确失败

- pc: 脑图备注「缺少 category 字段」的裁剪版 Body
- 向 VCX 发送该 Body
  - 行为符合约定：要么 VCX 容忍缺省，要么返回明确业务/校验错误且不造成内部状态不一致（以 Apifox 与 Visa 文档为准，若文档要求必填则预期失败）

### tc-p3: orderCancelledDate非空或status表示已取消时是否仍回调与规则一致

- pc: 订单已取消但 MQ 仍到达核销完成类消息（或边界样例）
- 消费并尝试回调
  - 与产品规则一致：要么不发外向回调，要么发带取消语义且 VCX 可处理；无订单状态倒挂

### tc-p3: eventType非walkin.redemption误入该Topic时被拒或进入隔离处理

- pc: 构造错误 `eventType` 字段
- 消费
  - 不误当作核销成功；错误可观测且不污染其他订单

## vcx_v1_events_orders（预订单创建与状态变更）

### tc-p1: BUSINESS_ORDER_PREBOOKING_CREATED_CALLBACK投递prebooking.created且带合法鉴权头

- pc: Topic `BUSINESS_ORDER_PREBOOKING_CREATED_CALLBACK`；`preBookingCreatedCallBackDto.eventType`=`prebooking.created`；租户 `0184`/`0426` 等样例中 `module`（lounge/fastTrack）与订单号有效
- 消费并调用 VCX `…/vcx/v1/events/orders`（可带 `apikey` 等查询参数，以环境为准）
  - 请求头包含 `Content-Type`、`Accept` 及有效 `X-PAY-TOKEN`（脑图日志样例）；HTTP 成功
- 校验 Body 中 `orderId`、`programId`、`status`、`createdDate`、`source`、`remarks` 与源订单一致
  - 字段值一致；可检索日志中 `url` 与脱敏后 `dpId`

### tc-p1: module=2（FastTrack）预订单prebooking.created回调成功

- pc: 租户 `0426`、订单号 `FT…`、module=2 等脑图样例数据可造数或取自联调环境
- 消费 `BUSINESS_ORDER_PREBOOKING_CREATED_CALLBACK` 并回调 VCX
  - HTTP 成功；`module` 与 `orderId` 与订单域一致；与 lounge（module=1）样例相比字段集合符合 Apifox

### tc-p2: BUSINESS_ORDER_STATUS_CHANGE投递prebooking.statusChanged且previousStatus与currentStatus正确

- pc: Topic `BUSINESS_ORDER_STATUS_CHANGE`；`orderStatusCallBackDto` 含 `previousStatus`、`currentStatus`、`statusChangedDate`
- 订单从上一状态流转到当前状态后消费消息
  - 回调成功；VCX 收到的状态迁移与订单域「前一状态/当前状态」一致
- `retryTimes`>0 时（脑图样例为 2）验证重试计数或日志
  - 重试行为符合 MQ 与消费者配置，无无限重试

### tc-p2: remarks为null与为非空字符串两种序列化均合法且VCX可解析

- pc: 两笔订单分别 `remarks:null` 与 `remarks` 有值
- 分别触发 `prebooking.created`
  - 均无非法 JSON；VCX 侧解析成功

### tc-p2: 同一orderId短时间重复prebooking.created时幂等或二次语义明确

- pc: 字节级相同或仅 `retryTimes` 不同的重复消息
- 连续消费
  - 不产生重复下单副作用；若第二次为补偿则日志可区分

### tc-p2: prebooking.statusChanged中previousStatus与currentStatus与订单流不一致时被拦截

- pc: 构造与订单主库当前状态不匹配的状态对
- 消费
  - 不向外误报；日志含拒绝原因；订单主状态不被错误覆盖

### tc-p3: MQ消息JSON非法时反序列化失败且不污染正常消费进度

- pc: 构造非法 JSON（脑图样例：`remarks` 后 `::` 双冒号等导致 `convert failed`）
- 投递并由监听器解析
  - 解析失败有明确错误日志与 `traceId`；该条不当作成功回调；不阻塞同组合法消息的最终处理（具体是否跳过/重试以框架配置为准，需在日志中可区分）

### tc-p3: 日志可通过groupId或orderNo关联多次orders回调

- pc: 日志中存在同一 `groupId` 或 `orderNo` 的多次 `…/vcx/v1/events/orders` 记录（脑图多条 message 样例）
- 按时间序拉取相关日志
  - 每次回调可对应到明确订单状态节点，无交叉写错订单

### tc-p3: 环境仅允许单一生效域名时未出现visa.co与visa.com双发（若曾误配）

- pc: 配置中仅保留一个基址；另一基址 DNS 或桩不可达
- 全链路回归一次订单回调
  - 仅命中生效域名；无因回退列表导致的双写

## vcx_v1_events_payments（支付状态更新）

### tc-p1: BUSINESS_ORDER_PAYMENT_STATUS_CALLBACK投递payment.status.updated且金额与状态迁移正确

- pc: Topic `BUSINESS_ORDER_PAYMENT_STATUS_CALLBACK`；`paymentStatusCallBackDto.eventType`=`payment.status.updated`；`payment.previousStatus`=`AUTHORIZED`、`currentStatus`=`CAPTURED`；`action.type`=`CAPTURE`；`amount` 与币种与支付单一致
- 消费后回调 `…/vcx/v1/events/payments`
  - HTTP 成功；Body 中 `orderId`、`programId`、`paymentId`、`provider` 等与支付域一致
- 检索日志关键字订单号（脑图样例 `SL20260502BGNMN8G`）
  - 可关联到一次成功回调

### tc-p1: payment回调外层groupId与type为null时仍可成功投递（脑图样例）

- pc: MQ 体 `groupId`、`type` 为 `null`，`paymentStatusCallBackDto` 合法
- 消费并回调 VCX
  - HTTP 成功；不因外层 null 误拒解析

### tc-p2: result.success为false或provider名称脱敏时仍符合对外契约

- pc: 构造 `result.success`=false 或 provider 名称脱敏（脑图 `C***kOut` 类）
- 发送回调
  - VCX 或对接方按契约解析；内部监控不误判为「未发送」

### tc-p2: 同一paymentId重复CAPTURE成功回调时幂等

- pc: 两条内容一致的 `CAPTURED` 回调
- 连续处理
  - 订单/支付域无重复记账；VCX 不重复计费等副作用（以规则为准）

### tc-p2: payment.amount中original、captured、refunded组合与币种小数位正确

- pc: 多币种及最小货币单位边界数据（以产品支持为准）
- 发送回调并核对页面与对账文件
  - 金额精度与币种代码一致；无静默截断

### tc-p3: occurredAt跨日界线与时区格式校验

- pc: `occurredAt` 取 UTC 与带偏移样例
- 回调
  - VCX 与内部展示时间一致且无解析异常

### tc-p3: action为REFUND且currentStatus为REFUNDED时与订单取消链路一致（若Apifox已定义）

- pc: 满足退款完成主数据
- 发送 `payment.status.updated` 退款完成样例
  - 支付单与订单状态与脑图「REFUND」类场景一致

## AeroBlue订单支付状态（SaasMq与VCX侧订单状态联动）

### tc-p1: 订单orderStatus从wait_hand变为processing时触发SaasMq且下游一致

- pc: `memberCode`、`orderNo`、`tenantCode` 与样例一致；`before.orderStatus`=`wait_hand`，`after.orderStatus`=`processing`；`payStatus` 等联动字段符合「支付处理中」语义
- 触发订单状态变更并观察 SaasMq 消息体 `before`/`after` JSON
  - 消息结构与脑图样例一致；消费方或后续 VCX 回调与订单展示一致

### tc-p2: wait_hand到processing阶段对VCX的ApiCallback按规则不发送时可验证

- pc: 脑图标注该阶段「api callback 不发送」的租户/渠道/开关组合已明确（需与研发确认开关名）
- 完成该状态迁移并抓取出站 HTTP
  - 无对 VCX/Webhook 的误发；SaasMq 仍按预期到达

### tc-p2: 订单从processing进入wait_provide时链路可闭环

- pc: `after.orderStatus`=`wait_provide`（脑图：待发放；以订单域字典为准）
- 完成该状态迁移
  - SaasMq 与 API callback（若存在）与订单详情页状态一致；无重复仅状态抖动一次

### tc-p1: 订单从wait_provide进入wait_use且支付AUTHORIZED到CAPTURED与action=CAPTURE时全链路一致

- pc: 脑图路径「wait_provide→wait_use」；支付 `previousStatus`=`AUTHORIZED`，`currentStatus`=`CAPTURED`，`action.type`=`CAPTURE`
- 触发 SaasMq 与对外 `payment.status.updated` 回调（若分步）
  - 订单 `orderStatus` 与支付状态、回调 Body 与 `webhook.site`/VCX 桩收到的内容一致

### tc-p1: 订单从wait_use进入cancel且支付CAPTURED到REFUNDED与action=REFUND时全链路一致

- pc: 脑图路径「wait_use→cancel」；支付 `previousStatus`=`CAPTURED`，`currentStatus`=`REFUNDED`，`action.type`=`REFUND`
- 触发变更
  - SaasMq `before`/`after` 与对外回调 JSON 与订单取消原因一致；无中间态悬挂

### tc-p3: 支付状态previousStatus为INITIATED、currentStatus为AUTHORIZED且action为AUTH时与订单支付字段一致

- pc: 与脑图「INITIATED→AUTHORIZED」「action.type=AUTH」类场景一致的数据
- 触发对应变更
  - 订单 `payStatus` 与时间戳变更与规则一致；若存在对 VCX 的二次回调，Body 中状态与内部一致

### tc-p2: 订单从wait_hand进入disabled（订单关闭）时无错误悬挂回调

- pc: 脑图「wait_hand→disabled」类关闭路径
- 执行关闭
  - 内部状态为终态；对 VCX 的后续自动回调符合规则（不发/发关闭语义二选一，以实现为准）；无持续重试风暴

### tc-p3: payment.status.updated在result.success=false且前后状态码相同、action=AUTH时的可观测性与产品缺口

- pc: 脑图样例：`result.success`=false，`previousStatus` 与 `currentStatus` 均为内部码 `1`，`action.type`=`AUTH`
- 触发并记录 SaasMq 与 ApiCallback
  - 行为与现网一致；`rc` 记录已知缺口：「暂无退款失败/确认扣款失败类独立推送」若仍成立则仅做观测项不判失败，否则按新需求更新预期

### tc-p3: 同一订单在「支付中/履约中」仅出现一次关键状态广播（防重复）

- pc: 脑图备注「核对订单状态只有一次」类约束
- 在短时间内重复触发相同状态迁移或重复消息
  - 对外仅一次有效状态通知或幂等合并；日志可证明去重逻辑生效

### tc-p3: business-saas库ord_order实付金额币种与payment_id与回调及页面一致

- pc: 具备 `business-saas`.ord_order 查询权限；样例订单号如脑图 SQL（`SL20260428BKS621E`）
- 执行 `SELECT x.actual_pay_amount,x.currency,x.payment_id FROM ord_order x WHERE order_no=…` 与页面、回调 JSON 比对
  - 三者一致或在允许舍入规则内一致

### tc-p3: 使用webhook.site等公网收件箱仅允许在测试环境且不得携带生产密钥

- pc: 回调 URL 指向 `webhook.site` 类联调地址（脑图 Inbox 样例）
- 在隔离环境执行一笔回调
  - 请求成功且可验 Body；生产配置中不存在该类 URL；日志不含完整密钥

## VCX回调横切观测与安全

### tc-p2: traceId自MQ消费贯穿至HTTP出站日志可检索

- pc: 任一 `receive*Event` 主路径
- 从 MQ 日志到 `PreBookingCreatedCallBackProcessor`/`ResourceEventCallbackProcessor` 等再到 HTTP client 日志按 `traceId` 串联
  - 单次业务可在一条追踪链上还原

### tc-p3: 日志与附件中不得出现完整apikey或完整X-PAY-TOKEN明文

- pc: 开启全量调试日志级别（若允许）
- 执行一次成功回调
  - 扫描日志输出：密钥为脱敏或省略；满足安全基线

### tc-p3: TLS证书校验失败或主机名不匹配时错误可读且不无限重试

- pc: 将 VCX 基址指向证书错误桩
- 触发回调
  - 明确 SSL/TLS 错误；重试策略受控

### tc-p3: 回调HTTP耗时与Payload大小在约定阈值内可监控

- pc: 正常与偏大（仍合法）的 inventory 列表
- 压测或单次计量
  - 超时率与 P99 在 SLA 内或有监控阈值告警
