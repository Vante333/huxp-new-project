# PAPI-25760426租户Lounge与FT订单流cashPaymentApplied测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2576.md`；**0426** 租户专项；**cashPaymentApplied**：true 且「确有现金应付」通过校验后，create 后 API **不再**调用 `orderStatusUpdate`、`confirmOrder`，改由 **VISA** 侧通知 SaaS；false 走原流程。
- rc: 预约商品需过滤 **第三方权益/第三方现金**，仅 **权益/现金** 类可下单；纯权益/纯现金/权益+现金组合见需求表格；联调依赖 VISA/MQ/PCI 时以环境说明为准。

## 预约商品过滤（取商品阶段）

### tc-p1: 0426租户在预约商品列表或等价接口中不出现第三方权益与第三方现金类商品

pc: 0426 租户；存在混合类型商品数据

- 执行取预约商品相关能力（与实现阶段对齐）
  - 可选商品中不包含需求定义的第三方权益类、第三方现金类条目，仅保留权益/现金类

### tc-p2: 非0426租户取商品行为与现网一致不因本需求误过滤

pc: 非 0426 租户；同类商品池

- 执行取商品
  - 商品集合与改造前或对照环境一致，无异常缺失

## cashPaymentApplied为false（走原API订单流）

### tc-p1: 0426租户cashPaymentApplied为false时create后仍由API执行orderStatusUpdate与confirmOrder至待发放

pc: 0426；项目支付或等价场景；`cashPaymentApplied=false`；可观测 SaaS 调用或联调日志

- 完成 create 及后续 API 侧标准步骤
  - 与需求「不改原流程」一致：API 在 create 后继续触发 `orderStatusUpdate`、`confirmOrder` 至约定状态（待发放等）

## cashPaymentApplied为true（API在create后不再调orderStatusUpdate与confirmOrder）

以下为租户×支付形态×权益参与判定表（与需求表一致）。

| 场景编号 | 租户 | cashPaymentApplied | 支付形态 | 权益是否参与 | API在create后是否还调orderStatusUpdate_confirmOrder |
|---------|------|-------------------|----------|-------------|-----------------------------------------------------|
| A | 0426 | true | 纯现金 | 无 | 否（由VISA侧后续通知SaaS） |
| B | 0426 | true | 纯现金 | 有 | payByEquity后API不再执行业务（见需求表） |
| C | 0426 | true | 纯权益 | - | 不改原流程中与纯权益相关分支（见需求表总结行） |
| D | 非0426 | true | 任意 | - | 与改造前一致 |

### tc-p1: 0426纯现金无权益且cashPaymentApplied为true并有真实现金应付时create后API不再调orderStatusUpdate与confirmOrder

pc: 0426；可证明「确有金额要付」；`cashPaymentApplied=true`；纯现金、无权益场景；具备调用链观测

- 执行 create 成功
  - 成功创建后，在约定窗口内 **无** API 项目对 SaaS 的 `orderStatusUpdate`/`confirmOrder` 调用（与需求一致）；后续由 VISA 路径推进

### tc-p1: 0426权益加现金且cashPaymentApplied为true时在payByEquity之后API不再执行业务

pc: 0426；混合支付；`cashPaymentApplied=true`；需完成权益支付步骤

- 按需求表执行 create 与 `payByEquity`
  - `payByEquity` 成功后 API 侧不再执行后续应由 VISA 负责的阶段；状态推进依赖 VISA/MQ（以联调为准）

### tc-p2: 0426纯权益或cashPaymentApplied为false时与上表C及原流程一致无错误跳过API步骤

pc: 对照上表 C 或 false 分支

- 执行完整主路径
  - 状态与调用链符合需求表「总结」行与现网行为

### tc-p2: 非0426租户cashPaymentApplied为true时不走0426专项绕过API逻辑

pc: 非 0426 租户；`cashPaymentApplied=true`

- 执行与 0426 同类场景
  - 调用链与改造前一致，不出现错误抑制 API 更新

### tc-p2: cashPaymentApplied为true但无实际现金应付时拒绝或回退为false语义

pc: 与需求「通过检验（真的有金额要付）」对齐；构造无现金应付场景

- 调用下单并置 `cashPaymentApplied=true`
  - 业务拒绝或强制视为 false（以 APIFOX 为准），且不进入错误跳过 API 的中间态

### tc-p3: 0426租户尝试对过滤掉的第三方类商品下单被拒绝

pc: 0426；仅第三方类商品可选（若仍能构造请求）

- 尝试创建订单
  - 无法成交或返回明确业务错误

### tc-p3: VISA侧orderStatusUpdate_confirmOrder_payfinish与MQ待发放状态机联调抽样

pc: VISA/MQ/PCI 联调环境可用

- 按需求表执行纯现金或混合路径至待使用
  - 各阶段状态与需求表「VISA 预授权/确认扣款」描述一致
