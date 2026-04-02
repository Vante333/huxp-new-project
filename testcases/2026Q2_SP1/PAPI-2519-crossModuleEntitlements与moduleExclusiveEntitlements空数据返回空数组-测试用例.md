# PAPI-2519空权益字段无数据返回空数组测试用例

**JIRA**: [PAPI-2519](https://dragonpass.atlassian.net/browse/PAPI-2519)

## 会籍权益四接口cross与module空数组返回（V2EntitlementsEndpoints）

### 参数化数据态矩阵

#### 四接口共性验证

| 接口标识 | 路径 |
| --- | --- |
| SearchEntitlements | /v2/entitlements/search |
| RetrieveMemberships | /v2/memberships |
| UpdateEntitlements | /v2/entitlements/update |
| UpdateEntitlementByPoolId | /v2/entitlements/{entitlementPoolId}/update |

##### tc-p1: 双空数据态下四接口entitlements中crossModuleEntitlements与moduleExclusiveEntitlements均为空数组非null

- pc: 已为表中每一行准备可稳定复现「无跨品类权益明细且无单品类权益明细」的会籍数据；已具备合法鉴权及请求头X-Program-ID、X-Request-ID；各接口请求方法、请求体、路径参数及查询参数以OpenAPI为准且可成功返回含entitlements的响应
- 按上表自上而下逐行调用对应路径接口直至获得业务成功响应
  - 每一行成功响应在约定entitlements节点下crossModuleEntitlements与moduleExclusiveEntitlements均存在且为JSON数组、长度为0、取值不为null
- rc: UpdateEntitlements与UpdateEntitlementByPoolId需构造合法更新入参使成功响应携带最新entitlements；路径中entitlementPoolId替换为环境合法权益池ID；需求标题crossModuleEntitlement与字段名crossModuleEntitlements不一致时以OpenAPI为准；entitlements在响应中的嵌套路径以Apifox当前版本为准
- tag: PAPI-2519,P1,参数化,双空

##### tc-p2: 仅crossModuleEntitlements无数据时四接口该字段为空数组非null且moduleExclusiveEntitlements为非空数组

| 接口标识 | 路径 |
| --- | --- |
| SearchEntitlements | /v2/entitlements/search |
| RetrieveMemberships | /v2/memberships |
| UpdateEntitlements | /v2/entitlements/update |
| UpdateEntitlementByPoolId | /v2/entitlements/{entitlementPoolId}/update |

- pc: 已准备仅有单品类权益明细、无跨品类权益明细的会籍；表中各接口调用前置均已满足且可成功返回
- 按上表逐行调用对应路径接口直至获得业务成功响应
  - 每一行成功响应中crossModuleEntitlements为JSON空数组且不为null，moduleExclusiveEntitlements为元素个数大于0的JSON数组且不为null
- rc: 若环境无法构造仅cross空场景则记录阻塞原因与替代账号或Program后执行
- tag: PAPI-2519,P2,参数化,单侧空

##### tc-p2: 仅moduleExclusiveEntitlements无数据时四接口该字段为空数组非null且crossModuleEntitlements为非空数组

| 接口标识 | 路径 |
| --- | --- |
| SearchEntitlements | /v2/entitlements/search |
| RetrieveMemberships | /v2/memberships |
| UpdateEntitlements | /v2/entitlements/update |
| UpdateEntitlementByPoolId | /v2/entitlements/{entitlementPoolId}/update |

- pc: 已准备存在swap跨品类权益明细、单品类侧无权益明细的会籍；表中各接口调用前置均已满足且可成功返回
- 按上表逐行调用对应路径接口直至获得业务成功响应
  - 每一行成功响应中moduleExclusiveEntitlements为JSON空数组且不为null，crossModuleEntitlements为元素个数大于0的JSON数组且不为null
- rc: 若环境无法构造仅module空场景则记录阻塞原因与替代数据后执行
- tag: PAPI-2519,P2,参数化,单侧空

##### tc-p2: 双侧有数据时四接口两字段均为非空数组非null且元素结构符合契约

| 接口标识 | 路径 |
| --- | --- |
| SearchEntitlements | /v2/entitlements/search |
| RetrieveMemberships | /v2/memberships |
| UpdateEntitlements | /v2/entitlements/update |
| UpdateEntitlementByPoolId | /v2/entitlements/{entitlementPoolId}/update |

- pc: 已准备同时存在跨品类与单品类权益明细的会籍；表中各接口调用前置均已满足且可成功返回
- 按上表逐行调用对应路径接口直至获得业务成功响应
  - 每一行成功响应中crossModuleEntitlements与moduleExclusiveEntitlements均为元素个数大于0的JSON数组且不为null，数组元素字段与OpenAPI或现行契约定一致
- rc: 本用例用于回归有数据路径不因空改数组而破坏结构
- tag: PAPI-2519,P2,参数化,回归

## 会籍查询接口列表补充（RetrieveMemberships）

### 多条记录entitlements结构

#### 列表逐条校验

##### tc-p2: memberships列表含双空与非空会籍交错时各条entitlements两字段均为数组类型非null

- pc: 单次/v2/memberships列表响应可稳定包含至少一条权益双空会籍与至少一条权益非空会籍；鉴权与Program上下文合法
- 调用/v2/memberships接口获取列表并得到业务成功响应
  - HTTP状态码与业务成功约定一致
- 遍历响应体会籍列表每一项定位entitlements节点并读取crossModuleEntitlements与moduleExclusiveEntitlements
  - 对权益双空记录两字段均为JSON空数组且不为null，对权益非空记录两字段均为元素个数大于0的JSON数组且不为null
- tag: PAPI-2519,P2,列表,Memberships

## 跨接口一致性（SearchVsMemberships）

### 同一会籍权益快照

#### 查询类一致性

##### tc-p2: 同一会籍在Search与Memberships下等价数据态时两字段空非空形态一致且空为数组非null

- pc: 固定可定位的会籍标识（如membershipId或等价条件）与Program；数据态至少覆盖「双空」一种，若可构造则增加「仅cross空」或「仅module空」之一
- 调用/v2/entitlements/search查询该会籍权益并得到业务成功响应
  - 记录entitlements中crossModuleEntitlements与moduleExclusiveEntitlements各自为空数组或非空数组的判定结果且确认均不为null
- 调用/v2/memberships定位同一会籍并得到业务成功响应
  - 同一会籍entitlements中上述两字段与Search一步的空非空形态一致，且凡为空时均为JSON空数组不为null
- tag: PAPI-2519,P2,一致性

## 权益更新接口补充（UpdateEntitlements）

### 失败响应结构

#### 异常路径

##### tc-p3: update业务失败响应若仍含entitlements则空列表场景下两字段不得为null

- pc: 已构造可稳定触发/v2/entitlements/update业务失败的请求；若实现从不返回entitlements结构则本用例标记不适用并跳过
- 调用/v2/entitlements/update接口
  - 响应符合业务失败约定
- 当失败响应体包含entitlements且包含crossModuleEntitlements与moduleExclusiveEntitlements键时读取两字段并按业务语义判断是否应为无数据列表
  - 凡应表达无数据列表的一侧其字段为JSON空数组且不为null；若响应不含上述结构则跳过本断言
- tag: PAPI-2519,P3,异常,UpdateEntitlements

## 按权益池更新接口补充（UpdateEntitlementByPoolId）

### 连续更新与查询对照

#### 顺序更新

##### tc-p3: 同一会籍连续两次按池更新成功后每次无数据侧字段均为空数组非null且search结果与最终态一致

- pc: 同一会籍下存在两个可顺序成功执行的entitlementPoolId；两次更新请求均合法
- 使用第一个entitlementPoolId调用/v2/entitlements/{entitlementPoolId}/update直至业务成功
  - 成功响应entitlements中crossModuleEntitlements与moduleExclusiveEntitlements均为JSON数组且不为null，无数据侧长度为0、有数据侧长度大于0
- 使用第二个entitlementPoolId重复上一步调用直至业务成功
  - 成功响应entitlements中crossModuleEntitlements与moduleExclusiveEntitlements均为JSON数组且不为null，无数据侧长度为0、有数据侧长度大于0
- 调用/v2/entitlements/search查询同一会籍
  - entitlements中两字段与最后一次更新后的业务预期一致且凡为空时均为JSON空数组不为null
- rc: 第二次更新须在第一笔成功之后执行
- tag: PAPI-2519,P3,顺序更新,按池更新
