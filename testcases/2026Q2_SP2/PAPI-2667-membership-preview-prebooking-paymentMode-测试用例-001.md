# PAPI-2667membership预览与创单paymentMode测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2667.md`；覆盖 Membership Lounge/FT 预览与创单链路中 `extra.paymentMode` 新增字段、`cashPaymentApplied` 联动、权益抵扣、价格校验与 SaaS 计价字段写入。
- rc: 接口路径、完整请求体、错误码、订单状态名、SaaS 字段路径以 **APIFOX** 与联调环境为准；本文按需求语义记录可执行测试点。
- rc: `paymentMode` 非必填，默认 `CLIENT_COLLECT`；枚举 `CLIENT_COLLECT` 表示客户收款并记账，`DP_COLLECT` 表示 DP 收款并触发支付流程。
- rc: 需求样例以 3 人订单为主；涉及人数 N 的用例需同步校验 `toUseEntitlementCount` 与 `toUseEntitlementDetail` 的一致性。

## v2_orders_{modules}_memberships_prebooking_preview（Preview预览）

### tc-p1: 不传paymentMode时按CLIENT_COLLECT默认模式预览且历史逻辑不变

- pc: 准备 Lounge 或 FT 可预览资源；订单人数为 3；存在可用价格与会籍上下文。
- 调用 Preview 接口，不传 `extra.paymentMode`，传入 `cashPaymentApplied=true`、`toUseEntitlementCount=0`。
  - 预览成功；收费方按 `CLIENT_COLLECT` 处理，客户现金应收休息室费用与预约费用均被正确记账。
- 校验响应中的价格校验结果或等价计价节点。
  - 与显式传入 `paymentMode=CLIENT_COLLECT` 的同条件响应一致，不触发 DP 支付流程相关字段或状态。

### tc-p1: CLIENT_COLLECT且使用部分权益时按客户收款加权益抵扣计算应收

- pc: 订单人数为 3；会籍至少有 1 个可用权益；资源价格 `price` 非空。
- 调用 Preview 接口，传入 `paymentMode=CLIENT_COLLECT`、`cashPaymentApplied=true`、`toUseEntitlementCount=1`，且 `toUseEntitlementDetail` 合计为 1。
  - 预览成功；1 个权益抵扣休息室费用，剩余 2 人休息室费用与 3 人预约费用按客户收款记账。
- 校验权益与价格明细。
  - `toUseEntitlementCount`、`toUseEntitlementDetail`、可用权益扣减预估与响应计价一致，且仍校验 `price` 非空。

### tc-p1: 不传paymentMode且cashPaymentApplied为false时等同CLIENT_COLLECT并要求权益覆盖人数

- pc: 订单人数为 N；会籍可用权益不少于 N；不传 `paymentMode`。
- 调用 Preview 接口，传入 `cashPaymentApplied=false`、`toUseEntitlementCount=N`，且 `toUseEntitlementDetail` 合计为 N。
  - 预览成功；服务端按默认 `CLIENT_COLLECT` 规则处理，因权益覆盖全部人数而允许继续创单。
- 校验响应中的收款方与权益分配。
  - 不出现 DP 支付语义；权益抵扣数量与人数一致，客户现金应收为 0 或按 APIFOX 约定返回。

### tc-p1: CLIENT_COLLECT且cashPaymentApplied为false并权益覆盖人数时允许预览

- pc: 订单人数为 N；会籍可用权益不少于 N；显式传入 `paymentMode=CLIENT_COLLECT`。
- 调用 Preview 接口，传入 `cashPaymentApplied=false`、`toUseEntitlementCount=N`，且 `toUseEntitlementDetail` 合计为 N。
  - 预览成功；符合现有规则「未收现金时权益必须覆盖人数」。
- 校验权益与计价结果。
  - 所有人数均由权益覆盖，不触发现金支付或 DP 收款流程。

### tc-p2: CLIENT_COLLECT下cashPaymentApplied为false且权益数小于人数时预览失败

- pc: 订单人数为 N；会籍权益数小于 N；`cashPaymentApplied=false`。
- 调用 Preview 接口，传入 `paymentMode=CLIENT_COLLECT` 或不传 `paymentMode`，并使 `toUseEntitlementCount<N`。
  - 返回约定业务错误；提示需全额权益覆盖或现金已收，不允许进入可创单状态。

### tc-p2: toUseEntitlementCount与toUseEntitlementDetail不一致时预览失败

- pc: 会籍存在可用权益；构造 `toUseEntitlementCount` 与 `toUseEntitlementDetail.cardholder+guest` 不一致。
- 调用 Preview 接口。
  - 返回参数或业务校验错误；不得按错误明细生成计价结果。

### tc-p2: toUseEntitlementCount超过会籍可用权益时预览失败

- pc: 会籍剩余权益数为 M；请求 `toUseEntitlementCount>M`。
- 调用 Preview 接口。
  - 返回权益不足相关错误；不会把超额权益当作客户现金或 DP 现金处理。

### tc-p1: DP_COLLECT且部分权益抵扣时预览触发DP收款价格语义

- pc: 0426 Visa 或需求指定租户；订单人数为 3；会籍有 1 个可用权益；资源 `overNumPrice` 非空。
- 调用 Preview 接口，传入 `paymentMode=DP_COLLECT`、`cashPaymentApplied=false`、`toUseEntitlementCount=1`。
  - 预览成功；DP 收取 3 人预约费与 2 人休息室现金费用，1 个权益抵扣休息室费用。
- 校验响应中的支付金额、应付方或等价节点。
  - 计价以 `overNumPrice` 作为 DP 收款休息室现金价格来源，并包含后续支付流程所需金额信息。

### tc-p1: DP_COLLECT时overNumPrice为空则预览失败或不可进入支付

- pc: 构造资源价格中 `overNumPrice` 为空或缺失；请求符合 `DP_COLLECT` 其他条件。
- 调用 Preview 接口。
  - 返回明确价格缺失错误，或响应标记不可下单/不可支付；不得以 `price` 或 0 金额兜底。

### tc-p2: DP_COLLECT且cashPaymentApplied传true时预览拒绝

- pc: 资源与权益均合法；`paymentMode=DP_COLLECT`。
- 调用 Preview 接口，传入 `cashPaymentApplied=true`。
  - 返回约定业务错误；不允许 DP 收款模式同时声明客户已收款。

### tc-p3: paymentMode非法枚举或大小写错误时返回参数错误

- pc: 构造 `paymentMode=DP_collect`、`CLIENT`、空字符串或非字符串类型。
- 调用 Preview 接口。
  - 返回参数校验错误；不得静默回退为默认 `CLIENT_COLLECT`。

## v2_orders_{modules}_memberships_prebooking（Create创单）

### tc-p1: CLIENT_COLLECT不传paymentMode创单与改造前订单流一致

- pc: 已通过 Preview 获取可创单 token；订单人数为 3；`cashPaymentApplied=true`；不传 `paymentMode`。
- 调用创单接口。
  - 创单成功；订单收费方与账务记录按客户收款处理，不触发 DP 支付单。
- 校验订单详情、账务流水或 SaaS 同步结果。
  - 休息室费用与预约费用的应收记录与改造前同场景一致。

### tc-p1: CLIENT_COLLECT部分权益创单正确记录客户现金与权益抵扣

- pc: 已通过 Preview；`paymentMode=CLIENT_COLLECT`；订单人数为 3；`cashPaymentApplied=true`；`toUseEntitlementCount=1`。
- 调用创单接口。
  - 创单成功；订单包含 1 个权益抵扣与客户现金应收部分。
- 校验权益扣减、客户现金账务与 SaaS 字段。
  - 2 人休息室费用、3 人预约费用记为客户收款相关应收，权益扣减数量为 1。

### tc-p1: DP_COLLECT部分权益创单后生成待支付链路并不走客户已收款语义

- pc: 已通过 DP_COLLECT Preview；订单人数为 3；`cashPaymentApplied=false`；`toUseEntitlementCount=1`。
- 调用创单接口。
  - 创单成功并进入 DP 收款支付流程；不会标记为客户已收现金完成。
- 校验订单状态、支付单或支付参数。
  - 支付金额覆盖 DP 应收预约费与未被权益抵扣的休息室费用，权益抵扣数量为 1。

### tc-p2: 创单请求paymentMode与Preview上下文不一致时拒绝或重新校验

- pc: Preview 阶段使用 `CLIENT_COLLECT` 获取 token；创单阶段改传 `DP_COLLECT`，或反向构造。
- 调用创单接口。
  - 返回约定业务错误或按服务端重新校验后的结果处理；不得使用旧 token 绕过价格与收款方校验。

### tc-p2: DP_COLLECT创单时cashPaymentApplied为true被拒绝

- pc: 已准备合法资源、权益与价格；创单请求传 `paymentMode=DP_COLLECT`。
- 调用创单接口，传入 `cashPaymentApplied=true`。
  - 返回业务错误；不会生成客户已收款订单或支付单。

### tc-p3: Lounge与FT模块在paymentMode规则上保持一致

- pc: 分别准备 Lounge 与 FT 可下单资源；两类资源价格与权益数据均合法。
- 分别执行 Preview 与创单，覆盖 `CLIENT_COLLECT` 默认模式和 `DP_COLLECT` 模式。
  - 两个 modules 下 `paymentMode` 默认值、非法组合、权益校验和收款方语义一致；若 APIFOX 明确差异则按文档记录差异。

## DP_COLLECT_SaaS计价字段与预约费付费方

### tc-p1: DP_COLLECT且prebookingFee.chargingRule为用户支付时写入userBookPrice

- pc: BOSS 网点配置预约服务费付费方为用户支付；价格返回 `overNumPrice` 与 `userBookPrice` 均非空；订单人数为 3。
- 使用 `paymentMode=DP_COLLECT`、`cashPaymentApplied=false` 完成 Preview 与创单。
  - 创单成功并生成 DP 收款金额。
- 校验 SaaS 同步字段。
  - `baseprice` 使用 `overNumPrice`，`prebookingfee` 使用 `userBookPrice` 并写入用户预约服务费字段。

### tc-p1: DP_COLLECT且用户支付预约费时总价按overNumPrice与userBookPrice计算

- pc: 同上；记录请求人数 N、权益抵扣数量 E、`overNumPrice`、`userBookPrice`。
- 校验支付金额、订单总价或 SaaS 总价。
  - 总价与需求约定的 DP 收款公式一致；休息室现金部分、预约服务费部分和权益抵扣部分可追溯。
- rc: 若实现对权益抵扣后的休息室人数与需求样例总价公式存在差异，需以产品/研发确认口径更新本用例预期。

### tc-p2: DP_COLLECT且用户支付预约费但userBookPrice为空时失败

- pc: BOSS 配置预约服务费付费方为用户支付；`userBookPrice` 为空或缺失。
- 调用 Preview 或创单。
  - 返回明确价格缺失错误；不得生成缺少预约费的 DP 支付订单。

### tc-p1: DP_COLLECT且prebookingFee.chargingRule为客户支付时不向SaaS传prebookingfee

- pc: BOSS 网点配置预约服务费付费方为客户支付；`overNumPrice` 非空。
- 使用 `paymentMode=DP_COLLECT`、`cashPaymentApplied=false` 完成 Preview 与创单。
  - 创单成功；DP 收款休息室现金费用按 `overNumPrice` 计算。
- 校验 SaaS 同步字段。
  - `baseprice` 使用 `overNumPrice`，`prebookingfee` 不传或为空，且不写入用户预约服务费字段。

### tc-p2: DP_COLLECT且客户支付预约费时userBookPrice存在也不误写用户预约服务费

- pc: BOSS 配置预约服务费付费方为客户支付；价格数据中同时存在 `userBookPrice`。
- 执行 DP_COLLECT 创单并观察 SaaS 同步。
  - 不因 `userBookPrice` 有值而写入用户预约服务费，避免重复向用户收取预约费。

## 兼容回归与对账

### tc-p1: 历史客户端不传paymentMode的Preview与Create自动化回归通过

- pc: 使用改造前典型报文，仅包含 `cashPaymentApplied`、`toUseEntitlementCount`、`toUseEntitlementDetail` 等字段。
- 执行 Preview 与创单主链路。
  - 接口成功率、响应结构、订单状态与历史基线一致；新增字段不会破坏旧客户端。

### tc-p2: 客户收款与DP收款订单在账务报表中收款方可区分

- pc: 分别创建 `CLIENT_COLLECT` 与 `DP_COLLECT` 成功订单；具备账务或报表查询权限。
- 查询订单详情、账务流水或报表。
  - 两类订单的收款方、费用归属、权益抵扣记录可明确区分，便于对账。

### tc-p3: 并发重复创单不会重复扣权益或重复生成DP支付单

- pc: 同一个 Preview token 或等价幂等键可用于并发验证；会籍权益与价格合法。
- 并发提交多次 `DP_COLLECT` 创单请求。
  - 仅一个请求成功或按幂等规则返回同一订单；不会重复扣减权益或生成多笔有效支付单。

