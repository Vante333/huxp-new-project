# PAPI-2548会籍extensions非标字段测试用例

> 需求同步：`requirements/2026Q2_SP1/PAPI-2548.md`（自 Jira 拉取并整理）。要点：内部租户 UAT **0426**；非内部租户注册/查询**不返回** `extensions` 数组；无数据时展示 **`[]`**。

## 错误码与msg（业务失败体）

失败时响应根节点含 **`errCode`**、**`msg`**（英文）。约定如下（与需求文档一致；历史沙箱可能使用相邻 errCode，但 `msg` 句式应与下表一致）：

| errCode | 场景 | msg（英文全文） |
| --- | --- | --- |
| 500.030.032 | 同一会籍下 extensions 重复 type | Duplicate extension type detected. Each type must be unique within a membership. |
| 500.030.033 | 超过「最多 5 个 type」上限 | A maximum of 5 extension types is allowed per membership. |
| 500.030.034 | POST/PATCH /v2/memberships/extensions 更新失败（兜底） | Failed to update membership extensions. Please try again later. |

## v2_memberships（会籍注册）

### 租户权限与extensions主流程

#### tc-p1: 内部租户UAT0426注册携带合法extensions成功且HTTP200响应回显与请求一致的extensions

- pc: 使用内部租户ProgramId=0426及合法鉴权；其余注册必填项满足OpenAPI
- 调用POST_v2_memberships，请求体含extensions数组（至少1条，每条含type与value字符串）
  - HTTP状态码为200（或业务成功码，以契约为准），响应体含extensions且与请求中各条type/value一致，会籍创建成功
- tag: PAPI-2548,P1,注册,extensions

#### tc-p1: 非内部租户调用POST_v2_memberships携带extensions被拒绝或业务失败且响应不暴露extensions数组

- pc: 使用非0426租户及有效鉴权；注册其他条件合法
- 调用POST_v2_memberships并传入非空extensions
  - 返回业务失败或HTTP与契约约定的拒绝语义；成功路径下响应亦**不得**返回可读的 `extensions` 非标数组（与需求「其他租户接口不返回该 array」一致，具体以OpenAPI为准）
- rc: 具体HTTP状态码与错误码以OpenAPI/实现为准，本用例验证「仅限内部租户」约束生效
- tag: PAPI-2548,P1,权限,租户隔离

#### tc-p1: 同一注册请求中extensions存在重复type（如两条cardId）注册失败且不创建半成会籍

- pc: 内部租户0426；除extensions外注册参数合法
- 调用POST_v2_memberships，extensions内含两条及以上相同type字段值
  - 注册失败，数据库/后续查询中不存在因本请求产生的新会籍；若返回业务错误码，优先 **500.030.032**，`msg` 为 `Duplicate extension type detected. Each type must be unique within a membership.`（历史环境可能为相邻 errCode，以实际为准）
- tag: PAPI-2548,P1,唯一性,type

#### tc-p2: 注册不传extensions字段成功且会籍其他字段与原有行为一致

- pc: 内部租户0426；注册参数不含extensions键
- 调用POST_v2_memberships
  - 注册成功，响应与查询中extensions为空数组、字段省略或null的行为与OpenAPI一致且不破坏原有会籍字段
- tag: PAPI-2548,P2,兼容,可选字段

#### tc-p2: 注册传入extensions为空数组成功

- pc: 内部租户0426
- 调用POST_v2_memberships，extensions为[]
  - 注册成功，响应/查询中extensions表现为空集合语义（空数组或契约等价表示）
- tag: PAPI-2548,P2,边界,空数组

#### tc-p2: 注册传入恰好5个不同type的extensions成功

- pc: 内部租户0426；准备5组互不重复type
- 调用POST_v2_memberships，extensions含5条
  - 注册成功，响应与查询中extensions条数为5且type互不重复
- tag: PAPI-2548,P2,上限,条数

#### tc-p2: 注册传入6个不同type的extensions失败

- pc: 内部租户0426；准备6组互不重复type
- 调用POST_v2_memberships，extensions含6条
  - 注册失败，错误信息或码符合「最多5个type」规则（优先 **500.030.033**），`msg` 为 `A maximum of 5 extension types is allowed per membership.`，会籍未错误创建
- tag: PAPI-2548,P2,上限,校验

### type与value长度边界

#### tc-p3: type与value长度为128注册成功129失败（参数化）

| 场景 | type长度 | value长度 | 预期 |
| --- | --- | --- | --- |
| A | 128 | 1 | 成功 |
| B | 1 | 128 | 成功 |
| C | 129 | 1 | 失败 |
| D | 1 | 129 | 失败 |

- pc: 内部租户0426；按上表构造字符串长度（可用单字节字符计数，若产品按Unicode码点计需与实现一致）
- 按上表逐行调用POST_v2_memberships（其余参数合法）
  - 成功行注册成功且extensions回显正确；失败行注册失败且不突破128长度规则
- rc: 若实现另有「最小长度」约束以OpenAPI为准并调整表内短字符串
- tag: PAPI-2548,P3,边界,长度

## v2_memberships_search（会籍查询）

### extensions回显与一致性

#### tc-p1: 通过POST_v2_memberships_search查询已带extensions注册的会籍返回与库内一致的extensions

- pc: 已通过内部租户0426注册成功且extensions含多条type/value；掌握可唯一定位该会籍的查询条件（如membershipId、外部单号等，以环境为准）
- 调用POST_v2_memberships_search获取该会籍
  - HTTP成功，响应中extensions与注册/最近一次更新后的全集一致，各元素含type，value存在性与DELETE后形态符合下文更新接口约定；非0426租户不返回该数组（见需求）
- tag: PAPI-2548,P1,查询,一致性

#### tc-p2: 从未写入extensions的会籍查询时extensions语义符合契约（空数组或省略）

- pc: 存在未携带extensions创建的历史会籍或同租户下无extensions成员
- 调用POST_v2_memberships_search定位该会籍
  - 成功响应中extensions表现为空数组、省略或null之一，且与OpenAPI及历史兼容策略一致
- tag: PAPI-2548,P2,兼容,默认态

## v2_memberships_extensions（extensions专用更新）

> 接口方法：需求为 **POST** ``/v2/memberships/extensions``；个别网关仍注册 **PATCH** 同路径，联调以 OpenAPI/环境为准。

### UPSERT与DELETE与混合

#### tc-p1: POST_v2_memberships_extensions对已有membershipId执行UPSERT新增type成功且响应返回更新后完整extensions

- pc: 已存在合法membershipId且当前extensions不含待新增type；内部租户0426
- 调用POST_v2_memberships_extensions（或网关等价的PATCH同路径），body含membershipId与一条operation为UPSERT的项（含type与value）
  - HTTP成功，响应含membershipId与extensions全集，新增type已出现且value正确，其余已有项未被误删
- tag: PAPI-2548,P1,UPSERT,新增

#### tc-p1: POST_v2_memberships_extensions对已有type执行UPSERT更新value成功且响应返回完整extensions

- pc: membershipId下已存在某type
- 调用POST_v2_memberships_extensions，对该type执行UPSERT并传入新value
  - 成功，响应extensions中该type的value已更新，其他type不变
- tag: PAPI-2548,P1,UPSERT,更新

#### tc-p1: POST_v2_memberships_extensions对已有type执行DELETE成功且响应中该type按契约移除或value按示例省略

- pc: membershipId下已存在待删type
- 调用POST_v2_memberships_extensions，对该type执行DELETE（不传value）
  - 成功，响应extensions为删除后的全集，被删type不再出现或符合需求示例（如仅保留type无value等以契约为准）
- tag: PAPI-2548,P1,DELETE

#### tc-p2: DELETE请求中type在库中不存在时接口仍成功且不改变当前extensions

- pc: membershipId有效；指定一条当前extensions中不存在的type
- 调用POST_v2_memberships_extensions，对该type执行DELETE
  - HTTP成功，响应extensions与删除前完全一致（无报错）
- tag: PAPI-2548,P2,DELETE,幂等

#### tc-p2: 同一请求内包含多条UPSERT与DELETE混合操作后响应extensions为最终全集

- pc: membershipId有效；准备至少一条待UPSERT、一条待DELETE的type
- 调用POST_v2_memberships_extensions，extensions数组内同时包含UPSERT与DELETE多条
  - 成功，响应extensions顺序与字段形态符合契约，且与按操作语义演算后的全集一致
- tag: PAPI-2548,P2,组合,批处理

### membershipId与operation校验

#### tc-p2: membershipId不存在时POST_v2_memberships_extensions失败且不产生副作用

- pc: 使用不存在或他租户的membershipId；鉴权为0426内部租户
- 调用POST_v2_memberships_extensions传入合法结构的extensions操作列表
  - 返回失败（HTTP/业务错误码以契约为准），任意现存会籍的extensions未被修改
- tag: PAPI-2548,P2,异常,membershipId

#### tc-p2: operation取值非UPSERT且非DELETE时请求失败且不修改数据

- pc: 合法membershipId；operation为非法字符串（如UPDATE、REMOVE自定义值）
- 调用POST_v2_memberships_extensions
  - 失败，原extensions不变（若网关对非法operation返回200且忽略，则以OpenAPI/实现为准并记录结论）
- tag: PAPI-2548,P2,校验,operation

#### tc-p3: UPSERT项缺少value时行为符合契约（拒绝或按默认值）

- pc: 合法membershipId；一条UPSERT未带value字段或value为null
- 调用POST_v2_memberships_extensions
  - 行为与OpenAPI一致（若文档要求必填则应失败）；若不定义则以实现为准并记录结论
- rc: 需求仅明确DELETE可不传value，UPSERT建议以OpenAPI为单一事实来源
- tag: PAPI-2548,P3,边界,UPSERT

## 端到端与数据存放

### 注册查询更新闭环

#### tc-p2: 内部租户0426完成注册带extensions后经search核对再经extensions接口变更后search再次核对一致

- pc: 全流程使用0426租户
- 调用POST_v2_memberships注册并记录返回的membershipId与extensions
  - 注册成功且extensions正确
- 调用POST_v2_memberships_search核对
  - 与注册一致
- 调用POST_v2_memberships_extensions执行至少一次UPSERT与一次DELETE
  - 响应extensions为中间态全集正确
- 再次调用POST_v2_memberships_search
  - 与上一响应extensions一致，且SaaS会籍feature侧存储可据技术方案抽样核对（若有权限）
- tag: PAPI-2548,P2,E2E,一致性

#### tc-p3: extensions数据存放于SaaS会籍feature字段且不影响非extensions会籍字段读写

- pc: 具备会籍详情或配置侧的观测手段（日志、DB、管理端其一）
- 完成一次带extensions的注册或更新
  - extensions可从feature（或当前实现等价位置）读到，且其他标准会籍字段读写行为与改造前一致
- rc: 需求说明「以后可能改为saas真实字段」，本用例关注当前迭代的实际落库/映射位置与回归
- tag: PAPI-2548,P3,存放,回归
