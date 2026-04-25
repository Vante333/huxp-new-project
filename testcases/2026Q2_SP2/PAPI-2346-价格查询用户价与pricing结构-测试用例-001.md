# PAPI-2346价格查询用户价与pricing结构测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2346.md`、本目录 [PAPI-2346-价格查询用户价与pricing结构-测试分析](./PAPI-2346-价格查询用户价与pricing结构-测试分析.md)；**完整 URL、鉴权、query/body 字段名、分页与错误码** 以 **APIFOX** 与联调环境为准。
- rc: 需求约束：在 **GET** `…/fitness/{resourceId}/schedule?expand=price`、**POST** `/v2/resources/prices`、**POST** `/api/v2/resources/options_prices` 的返回中扩展 `pricing`：保留 Legacy `basePrice` / `prebookingFee`，新增 `priceDetails`；无值返回 **`null`** 不返回 **`0`**；`prebookingFee.chargingRule` 与 BOSS `bookPricePayer` 按四类枚举映射。
- rc: **`testcases/` 路径记法**：复合能力在文档中写作下划线段（如 `options_prices`）；实际调用以 **APIFOX** 网关 URL 为准。

---

## GET Fitness 排期与 expand=price

### tc-p1: 传入合法 resourceId 且带 expand=price 时排期响应含完整 pricing 与 priceDetails

pc: 已准备 Aero Blue（或需求约定）租户下某 Fitness 资源 `resourceId`；BOSS 侧对该资源有可映射的完整 `priceList`（含 `price`、`bookPrice`、`overNumPrice`、`userBookPrice`、`bookPricePayer` 等，以数据准备为准）。

- 调用 GET `/v2/resources/fitness/{resourceId}/schedule`，query 携带 `expand=price`（其余 query 按 APIFOX）。
  - HTTP 与业务码成功；排期体（或等价节点）中存在 `pricing` 对象。

- 校验 `pricing.basePrice`、`pricing.prebookingFee`。
  - 与改造前基线或对照环境同一资源一致（Legacy 不变）。

- 校验 `pricing.priceDetails.basePrice.settlement` / `selling` 与 `prebookingFee.settlement` / `selling` / `chargingRule`。
  - 与需求映射表及 BOSS 当前数据一致。

### tc-p1: 同一 resourceId 在「仅 Legacy 基线」与「含 priceDetails」环境下 expand=price 行为可对比回归

pc: 具备改造前基线抓包或对照环境；同一 `resourceId` 与租户。

- 在改造后环境调用 GET schedule 且 `expand=price`。
  - Legacy 字段数值与基线一致。

- 对比 `priceDetails` 是否存在及数值。
  - 新增节点符合需求，不因 expand 导致 Legacy 漂移。

### tc-p2: 不传 expand=price 时行为符合 APIFOX（不要求强行返回 priceDetails）

pc: 同一合法 `resourceId`。

- 调用 GET schedule，**不传** `expand=price`（或传 `expand` 不含 price，以 APIFOX 为准）。
  - 响应成功；价格相关节点出现与否与文档一致。

- 若文档约定「不传则不返回扩展价」。
  - 响应中不出现 `priceDetails`，或不出现完整计价扩展（与 APIFOX 一致），且接口不 500。

### tc-p2: resourceId 不存在、无排期或越权时返回约定错误且无副作用

pc: 非法/不存在 `resourceId`，或当前令牌无权访问该资源。

- 调用 GET schedule（分别带与不带 `expand=price`）。
  - 返回约定 HTTP/业务错误码与文案。

- 再次用合法 resourceId 调用。
  - 合法请求不受影响，无脏缓存或异常状态（若中间层有缓存需按实现验证）。

### tc-p3: expand=price 与其他 expand 组合（若 APIFOX 支持多值）

pc: APIFOX 允许多个 expand 参数或逗号分隔列表。

- 构造 `expand=price` 与其他合法 expand 组合调用。
  - 排期与价格字段均按文档返回，互不覆盖或丢失。

---

## POST_v2_resources_prices（批量资源价格）

### tc-p1: 请求体包含单个合法 resourceId 时返回 pricing 含 Legacy 与 priceDetails

pc: BOSS 对应该资源有价数据；POST body 字段名以 APIFOX 为准。

- 调用 POST `/v2/resources/prices`，传入单个资源标识。
  - 成功；`data`（或等价路径）中该资源条目存在 `pricing`。

- 断言 Legacy 与 `priceDetails`。
  - 与需求及 BOSS 映射一致，与 GET expand=price 同一资源时对拍一致（允许时间窗内价格变更则记录快照策略）。

### tc-p1: 请求体包含多个 resourceId 时每条资源独立映射且无串数据

pc: 至少 2 个资源，BOSS `priceList` 与 `bookPricePayer` 故意不同。

- 调用 POST `/v2/resources/prices`，传入多 id 列表。
  - 成功；列表长度与请求语义一致。

- 逐条校验每个 `resourceId` 对应条目的 `pricing.priceDetails`。
  - 各条目仅反映自身 BOSS 数据，不出现 A 资源价写到 B 资源。

### tc-p2: 部分 resourceId 无价或不存在时该条目的处理符合约定

pc: 混合列表：1 个有价、1 个无价或不存在。

- 调用 POST `/v2/resources/prices`。
  - 整体成功或部分成功策略以 APIFOX 为准。

- 对无价条目校验 `pricing` 或 `priceDetails` 字段。
  - 缺省为 `null` 或整段缺失与文档一致；**不得**将「无值」误写为 `0`（若文档明确 0 与 null 等价则按文档关闭用例）。

### tc-p3: 空列表、超长列表、重复 resourceId 的校验与限流

pc: 构造空数组、超网关上限条数、重复 id。

- 依次调用 POST `/v2/resources/prices`。
  - 空列表返回参数错误或空结果，与 APIFOX 一致；超长返回 4xx 或截断策略有明确文档；重复 id 去重或重复返回与文档一致。

---

## POST_api_v2_resources_options_prices（Options价格）

### tc-p1: 合法 options 请求体返回 resources 中 pricing 与 /v2/resources/prices 语义一致

pc: 与上一节相同资源集合在 options 接口支持的入参形态；BOSS 数据一致。

- 调用 POST `/api/v2/resources/options_prices`（完整前缀以网关/APIFOX 为准）。
  - 成功；资源数组路径下每条 `pricing` 与 POST `/v2/resources/prices` 对同一批 id 的结果一致（字段路径以 APIFOX 为准）。

### tc-p2: options 特有维度（日期、站点、币种等）若影响价格时 priceDetails 仍正确

pc: APIFOX 中 options 含影响计价的可选字段。

- 构造两组仅 options 维度不同的请求。
  - 返回中 `pricing` / `priceDetails` 差异符合业务规则；`chargingRule` 随 `bookPricePayer` 变化正确。

### tc-p3: 必填 options 缺失或非法枚举时返回校验错误

pc: 删除必填字段或传入非法值。

- 调用 POST `/api/v2/resources/options_prices`。
  - 返回参数校验失败；不返回半成品的 `priceDetails` 误导客户端。

---

## pricing 结构与 BOSS 字段映射

### tc-p1: SETTLEMENT 维度 settlement 取自 BOSS price 与 bookPrice

pc: BOSS `priceList` 中 `price`、`bookPrice` 为非空数值。

- 依次调用三接口中任一种能返回该资源价的入口（GET expand=price 或两 POST）。
  - `priceDetails.basePrice.settlement` 与 BOSS `price` 一致（或按产品舍入规则一致）。

- 同响应内 `priceDetails.prebookingFee.settlement`。
  - 与 BOSS `bookPrice` 一致。

### tc-p1: SELLING 维度 selling 取自 BOSS overNumPrice 与 userBookPrice

pc: BOSS 含 `overNumPrice`、`userBookPrice`。

- 拉价并校验。
  - `basePrice.selling` 对应 `overNumPrice`；`prebookingFee.selling` 对应 `userBookPrice`。

### tc-p2: prebookingFee.chargingRule 与 BOSS bookPricePayer 四类映射

pc: 分别准备 `bookPricePayer` 对应用户全付、混合、共付、客户全付（或 BOSS 原始枚举与需求映射的四种）数据。

- 对每组数据拉价。
  - `prebookingFee.chargingRule` 分别为 `USER_FULL_PAYMENT`、`MIXED_PAYMENT`、`SHARED_PAYMENT`、`CLIENT_FULL_PAYMENT` 之一，与需求文字表一致。

### tc-p3: BOSS 出现未归类 bookPricePayer 时的兜底策略

pc: 构造或等待一条 BOSS 返回未在需求表中的 payer 值（需环境配合或 mock）。

- 拉价。
  - 返回明确默认枚举、空值、或业务错误之一，**与研发确认口径一致**；不得静默写成错误类型导致对账失败。

---

## Legacy 兼容与回归

### tc-p1: 仅读取 Legacy 字段的老集成不因新增 priceDetails 失败

pc: 客户端或自动化仅断言 `pricing.basePrice` 与 `pricing.prebookingFee`。

- 调用三接口之一成功路径。
  - Legacy 两字段存在且类型与数值符合历史契约。

### tc-p1: JSON 反序列化顺序与字段增多不破坏现有解析

pc: 使用严格模式或弱类型客户端解析样例响应。

- 保存完整响应 JSON 并解析。
  - 不因新增 `priceDetails` 键导致解析异常。

### tc-p2: 与「仅查价、不下单」关联的下游冒烟

pc: 存在依赖资源价格的预览或列表页（若有）。

- 在改造后环境打开或调用依赖价格的只读接口。
  - 页面或接口不报错；若读取 Legacy 则行为与改造前一致。

---

## 空值 null 与数值 0 边界

### tc-p1: BOSS 侧缺 overNumPrice 或 userBookPrice 时 API 对应 selling 为 null 非 0

pc: 数据准备使 BOSS 条目缺失上述字段之一（或等价「无值」）。

- 拉价。
  - 对应 `basePrice.selling` 或 `prebookingFee.selling` 为 JSON `null`；不为数字 `0`（除非产品书面确认等价）。

### tc-p1: BOSS 合法数值为 0 时 API 仍可返回 0 且与 null 语义区分

pc: BOSS 明确返回金额 `0`（真实零价）。

- 拉价。
  - API 对应字段为 `0`；与「缺字段转 null」可区分，且不违反「无值不返回 0」的语义。

### tc-p2: priceDetails 整段缺失与整段为 null 两种约定

pc: 与研发确认低价资源或开关关闭场景。

- 拉价。
  - 行为与 APIFOX 一致：`priceDetails` 缺失或为 `null` 有明确文档，客户端可分支处理。

---

## Aero Blue 租户与功能开关

### tc-p1: Aero Blue 租户下抽样资源三接口拉价成功且映射正确

pc: Aero Blue 目标租户令牌；多资源抽样。

- 对同一资源依次用 GET expand=price、两 POST（以适用性为准）拉价。
  - 均成功；`chargingRule` 与 `priceDetails` 符合需求。

### tc-p2: 非 Aero Blue 租户或未打开开关时行为与产品一致

pc: 非目标租户或 Nacos/开关关闭新价模型（若存在）。

- 拉价。
  - 不返回 `priceDetails` 或返回与关闭态一致；Legacy 行为不破坏；无 500。

### tc-p3: 开关从关到开的热切换后首次请求

pc: 运维切换配置后无应用重启或需重启（按实现）。

- 切换后首次拉价。
  - 行为符合设计（立即生效或需等待），无半开半关的中间错误体。

---

## 非法入参与安全

### tc-p2: POST 价格接口鉴权失败与租户越权

pc: 无效 token、过期 token、其他租户 resourceId。

- 调用两 POST 与 GET。
  - 统一返回 401/403 或业务无权限码；不泄露其他租户价格明细。

### tc-p2: 恶意超长 body、非法 JSON、SQL 注入形态字符串

pc: 构造异常 body。

- 提交 POST。
  - 参数错误 4xx；服务不崩溃；日志无敏感信息泄露（抽检）。

---

## 三接口对拍与一致性

### tc-p1: 同一 resourceId 同一时刻 GET expand=price 与 POST prices 数值对拍

pc: 并发窗口内价格稳定；同一令牌与资源。

- 先 GET 再 POST（或并行，按实现允许）。
  - 同一语义字段在允许误差/舍入规则内一致。

### tc-p2: POST `/v2/resources/prices` 与 POST `/api/v2/resources/options_prices` 对同一批 id 结果一致

pc: options 请求可表达与 batch prices 相同的资源集合。

- 两接口各调用一次。
  - 每条资源 `pricing` 结构一致（路径差异仅字段层级，语义一致）。

---

## 性能与稳定性（可选回归）

### tc-p3: POST 大批量 resourceId 时响应时间与超时策略

pc: 接近上限的 id 列表；压测环境。

- 调用 POST `/v2/resources/prices`。
  - 在 SLA 内返回或明确超时；部分成功策略有文档；单条失败不拖垮整批（若如此设计）。

### tc-p3: 连续重复请求幂等与缓存

pc: 相同请求连续发送多次。

- 观察响应与后端监控。
  - 结果一致或可接受的缓存命中行为；无价格跳变异常（除非 BOSS 侧变更）。

---

## 关联文档与交付

- 测试分析：[PAPI-2346-价格查询用户价与pricing结构-测试分析](./PAPI-2346-价格查询用户价与pricing结构-测试分析.md)  
- 需求：[PAPI-2346.md](../../requirements/Aero%20Blue/PAPI-2346.md) · [Jira PAPI-2346](https://dragonpass.atlassian.net/browse/PAPI-2346)

执行时请将文中 **「调用 GET/POST …」** 替换为 APIFOX 中的完整路径、示例 body 与断言 JSONPath；**tc-p1** 为必测主路径，**tc-p2** 为重要边界，**tc-p3** 为补充或依赖环境条件的项。
