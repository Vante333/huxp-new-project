# PAPI-2424_ePasses详情接口MS订单号提示测试用例

## v2_orders_ePasses_details接口（RetrieveEPassUsageOrderDetails）

### MS前缀拦截与错误码500.000.024

##### tc-P2-EPASS-001：MS前缀orderId调用接口统一返回500.000.024并提示ePassesSearch（参数化）

| orderId | 说明 |
| --- | --- |
| MS | 最短前缀边界 |
| MS00000000000001 | 典型MS订单号形态（示例，以环境真实格式为准） |

- tc-P2: pc: 已取得有效鉴权令牌、`X-Program-ID`；每次请求使用新的 `X-Request-ID`（UUID）；`Content-Type` 为 `application/json`
- tc-P2: 按上表 `orderId` 逐行调用 `POST_v2_orders_ePasses_details` 接口，请求体 JSON 仅含必填字段 `orderId` 且取值等于表中当前行
- tc-P2: HTTP 状态码为 200，响应 `code` 为 -1，`errCode` 为 `500.000.024`，`msg` 英文全文为 `The order ID you entered is not a usage order ID. If you want to query E-pass details, please use the /orders/ePasses/search API.`
- tc-P2: tag: PAPI-2424,MS前缀,500.000.024

### 回归与非MS前缀

#### usage订单号不受影响

##### tc-P1-EPASS-ORD-001：非MS前缀usage订单号查询不因本需求返回500.000.024

- tc-P1: pc: 存在已知 **usage** 订单号且不以 `MS` 开头（如 `DP` 开头），变更前调用本接口有明确预期结果
- tc-P1: 调用 `POST_v2_orders_ePasses_details` 接口，请求体 `orderId` 为该 usage 订单号，请求头满足接口契约（含 `Authorization`、`X-Program-ID`、`X-Request-ID`）
- tc-P1: HTTP 状态码为 200，响应行为与变更前一致，且不因本需求单独出现 `errCode` 为 `500.000.024`（除非该订单号在变更前即会返回该码）
- tc-P1: tag: PAPI-2424,回归,usage订单

#### 前缀语义

##### tc-P3-EPASS-001：orderId含MS子串但非MS开头不命中MS专用错误,例如SL20260129BBMSXV9

- tc-P3: pc: 构造 `orderId` 形如 `DP000MS00000001`（首字符起不为 `MS` 前缀）
- tc-P3: 调用 `POST_v2_orders_ePasses_details` 接口，请求体传入上述 `orderId`
- tc-P3: 响应 `errCode` 不为 `500.000.024`，且 `msg` 不出现针对 MS 订单引导至 `ePasses/search` 的专用文案
- tc-P3: SELECT x.* FROM `business-saas`.ord_order x WHERE order_no  not like "MS%"  and  order_no like "%MS%"  AND tenant_code='0184'
- tc-P3: SL20260129BBMSXV9
- tc-P3: rc: 防止实现误用子串包含判断
- tc-P3: tag: PAPI-2424,边界,负向

### 大小写与版本范围

#### 前缀匹配策略

##### tc-P3-EPASS-002：orderId前缀大小写

- tc-P3: pc: 与研发确认 `MS` 前缀匹配为仅大写、或大小写不敏感
- tc-P3: 分别使用 `orderId` 为 `ms00000000000001` 与 `MS00000000000001` 调用 `POST_v2_orders_ePasses_details` 接口，其余请求头与请求体规则不变
- tc-P3: 两种取值的返回是否与 `500.000.024` 命中关系与评审结论一致（仅大写敏感时小写不应返回 `500.000.024`；不敏感时均应返回 `500.000.024`）
- tc-P3: rc: 需求表述为「MS 开头」，默认主验证以 `MS` 大写前缀为准
- tc-P3: tag: PAPI-2424,边界,大小写

#### V1与V2

##### tc-P2-EPASS-002：V1与V2的ePasses_details对MS前缀orderId返回一致

- tc-P2: pc: 环境可按文档访问 V1、V2 的 `orders/ePasses/details` 路径；鉴权与 Program 有效
- tc-P2: 使用相同 `orderId`（以 `MS` 开头）分别调用 V1、V2 对应接口，请求体与头字段规则与各版本契约一致
- tc-P2: HTTP 状态码均为 200，`code` 均为 -1，`errCode` 均为 `500.000.024`，`msg` 与需求英文一致
- tc-P2: rc: 若仅 V2 上线，本用例改为仅执行 V2 或标记阻塞
- tc-P2: tag: PAPI-2424,V1V2,一致性
