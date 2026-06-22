# PAPI-2833休息室resourceDetails-nearestGate取值修正测试分析

## 测试范围说明

- rc: 基于 `requirements/2026Q2SP4/PAPI-2833.md`；覆盖 **休息室（Lounge）品类** `GET /v2/resources/{resourceId}` 响应中 `extra.loungeInfo.nearestGate` 的取值逻辑修正。
- rc: 取值优先级调整为：优先取 BOSS `nearestBoardingGate`；若为 `null` 则回退取 `boardingGateNearby`；两者均为 `null` 时对外返回 `null`。
- rc: 历史逻辑仅取 `boardingGateNearby`；本次修正后，BOSS 同时存在 `nearestBoardingGate` 与 `boardingGateNearby` 时，对外 `nearestGate` 应以 `nearestBoardingGate` 为准。
- rc: 本文聚焦资源详情字段映射与回退规则，不覆盖 `locationGuidance`、`terminal`、`amenities` 等其他 `loungeInfo` 字段，也不覆盖搜索列表、下单、预订单等业务链路。
- rc: 需求未明确 BOSS 字段所在节点路径、空字符串与 `null` 是否等价、以及非 Lounge 品类是否返回 `nearestGate`；执行前需以 BOSS 实际报文、Apifox 定义与研发最终实现为准。
- rc: 需求截图示例为 Perth 网点，BOSS `locationInfo` 中 `nearestBoardingGate` 为 `"53"`；测试样本宜覆盖「双字段均有值」「仅回退字段有值」「双字段均为空」三类数据。

## 需求语义归纳

| 能力 | 需求语义 | 主要风险 |
| --- | --- | --- |
| 主取值字段切换 | `nearestGate` 主来源由 `boardingGateNearby` 改为 `nearestBoardingGate` | 仍只读旧字段，导致新维护的最近登机口不展示 |
| 回退兼容 | `nearestBoardingGate` 为 `null` 时回退 `boardingGateNearby` | 回退逻辑缺失，历史仅有 `boardingGateNearby` 的网点展示为空 |
| 双空处理 | 两字段均为 `null` 时 `nearestGate` 返回 `null` | 误返回空字符串、默认值或旧缓存值 |
| 品类隔离 | 仅休息室品类 resource details 受影响 | FT、Setmeal 等资源详情被误改或 Lounge 以外品类出现 `nearestGate` 异常 |
| 字段稳定性 | 除 `nearestGate` 外其余 `loungeInfo` 字段保持既有语义 | 修正映射时连带破坏 `terminal`、`area`、`tier` 等字段 |

## nearestGate取值判定表

| BOSS `nearestBoardingGate` | BOSS `boardingGateNearby` | 对外 `extra.loungeInfo.nearestGate` | 场景归类 |
| --- | --- | --- | --- |
| `"53"` | `"54"` | `"53"` | 主字段优先 |
| `"A1"` | `null` | `"A1"` | 仅主字段有值 |
| `null` | `"B12"` | `"B12"` | 回退兼容 |
| `null` | `null` | `null` | 双空 |
| `""`（空字符串，若 BOSS 存在） | `"C3"` | 待研发确认；建议按 `null` 处理并回退 `"C3"` | 空串边界 |
| `"D5"` | `""`（空字符串，若 BOSS 存在） | `"D5"` | 主字段有值时忽略回退空串 |

## 资源详情nearestGate映射（LoungeResourceDetailsNearestGate）

### tc-p1: nearestBoardingGate有值时nearestGate取主字段

- pc: 准备 Lounge 资源 `resourceId`，BOSS 侧 `nearestBoardingGate` 与 `boardingGateNearby` 均有非空值且取值不同；测试环境可调用 `GET /v2/resources/{resourceId}?module=1`。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功，响应存在 `extra.loungeInfo.nearestGate`。
- 对比 BOSS 源数据与接口响应。
  - `nearestGate` 等于 `nearestBoardingGate`，不等于 `boardingGateNearby`。

### tc-p1: nearestBoardingGate为null时回退boardingGateNearby

- pc: 准备 Lounge 资源，BOSS 侧 `nearestBoardingGate` 为 `null`，`boardingGateNearby` 为非空值（如 `"B12"`）。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功。
- 校验 `extra.loungeInfo.nearestGate`。
  - 等于 `boardingGateNearby`，不因主字段为空而返回 `null`。

### tc-p1: 双字段均为null时nearestGate返回null

- pc: 准备 Lounge 资源，BOSS 侧 `nearestBoardingGate` 与 `boardingGateNearby` 均为 `null`。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功，不因映射为空触发 500 或业务错误。
- 校验 `extra.loungeInfo.nearestGate`。
  - 字段值为 `null` 或按 Apifox 约定缺失；不得静默回填 `"53"` 等默认值。

### tc-p1: 仅nearestBoardingGate有值时正常返回

- pc: 准备 Lounge 资源，BOSS 侧 `nearestBoardingGate` 为非空值，`boardingGateNearby` 为 `null`。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功。
- 校验 `extra.loungeInfo.nearestGate`。
  - 等于 `nearestBoardingGate`。

### tc-p2: 空字符串与null的边界处理符合产品约定

- pc: 与研发确认 BOSS 返回空字符串 `""` 时是否视为 `null`；准备覆盖「主字段空串 + 回退有值」「主字段有值 + 回退空串」「双空串」样本（若 BOSS 存在此类数据）。
- 分别调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口行为与研发确认口径一致，不出现主字段空串却未触发回退的异常。
- 对比判定表预期列。
  - 空串场景结果稳定，不与 `null` 场景混用错误取值。

### tc-p2: 修正后loungeInfo其他字段不受影响

- pc: 选取修正前后均可访问的同一 Lounge `resourceId`；记录 `terminal`、`area`、`routeTypes`、`tier`、`amenities` 等字段基线。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 除 `nearestGate` 按新规则变化外，其余 `extra.loungeInfo` 字段与基线一致。
- 校验 `prebookingPolicy`、资源名称、位置信息等同级节点。
  - 不因 `nearestGate` 映射调整出现非预期缺失或类型变化。

### tc-p2: 历史仅维护boardingGateNearby的网点仍可展示

- pc: 准备 BOSS 长期只维护 `boardingGateNearby`、未维护 `nearestBoardingGate` 的 Lounge 样本；记录修正前线上或沙箱 `nearestGate` 展示值。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功。
- 校验 `extra.loungeInfo.nearestGate`。
  - 与修正前展示一致，等于 `boardingGateNearby`，不出现回归为空。

### tc-p2: 多语言请求下nearestGate映射口径一致

- pc: 同一 Lounge `resourceId` 可分别以默认语言与至少一种其他 `language` 查询（若接口支持 `language` query）。
- 使用相同 `resourceId` 重复调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 各语言响应中 `nearestGate` 取值一致，均遵循主字段优先、回退次之规则。
- 对比 BOSS 源数据。
  - 不因语言参数切换误读不同 BOSS 字段。

## 品类隔离与回归（LoungeNearestGateRegression）

### tc-p2: 非Lounge品类resourceDetails不受本次修正影响

- pc: 准备 FT（`module=2`）、Setmeal 或其他非 Lounge 品类可访问 `resourceId`。
- 分别调用 `GET /v2/resources/{resourceId}`，传入对应 `module`。
  - 接口返回成功，响应结构符合各品类既有定义。
- 检查响应是否含 `extra.loungeInfo.nearestGate` 或等价字段。
  - 非 Lounge 品类不因本次 Lounge 映射修正出现异常新增、误赋值或 500。

### tc-p2: Lounge资源列表与详情nearestGate口径一致

- pc: `GET /v2/resources?module=1` 可返回含 `nearestGate` 或等价展示字段的列表项（若列表接口暴露该字段）；准备列表与详情均可核对的 `resourceId`。
- 先调用 `GET /v2/resources?module=1` 定位目标资源，再调用 `GET /v2/resources/{resourceId}?module=1`。
  - 列表与详情均可正常返回。
- 对比同一 `resourceId` 在列表与详情中的最近登机口展示值（若列表暴露）。
  - 两处取值一致，均符合 `nearestBoardingGate` 优先、`boardingGateNearby` 回退规则。

### tc-p3: 特殊字符与长登机口编号可原样返回

- pc: 若 BOSS 存在含字母数字混合、多位编号或带前缀的登机口值（如 `"53"`、`"A1"`、`"Gate 53"`），准备对应 Lounge 样本。
- 调用 `GET /v2/resources/{resourceId}`，`module=1`。
  - 接口返回成功。
- 校验 `extra.loungeInfo.nearestGate`。
  - 按新规则原样映射 BOSS 字符串，不被截断、转义或拼接两个源字段。

### tc-p3: BOSS字段更新后resourceDetails可反映最新nearestGate

- pc: 测试环境允许调整 BOSS `nearestBoardingGate` 或 `boardingGateNearby`；同一 `resourceId` 可完成「主字段有值 → 主字段清空仅留回退 → 双空」至少一次变更。
- BOSS 更新后重新调用 `GET /v2/resources/{resourceId}`，`module=1`（必要时避开过长的资源缓存周期）。
  - 每次变更后 `nearestGate` 与判定表一致。
- 记录变更前后响应。
  - 不出现长期滞留旧 `boardingGateNearby` 值、未读取新 `nearestBoardingGate` 的缓存问题。
