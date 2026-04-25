# PAPI-2636项目资源与TransportHub列表按id过滤测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2636.md`；**RetrieveProjectResourcesList**、**RetrieveProjectTransportHubList** 的完整路径、参数名（query/body）、HTTP 方法及错误码以 **APIFOX** 与联调说明为准。
- rc: 需求约束：支持 `resourceId`、`transportHubId` 过滤，**限制单个 id** 查询。

## RetrieveProjectResourcesList（按resourceId过滤）

### tc-p1: 传入合法且归属当前项目的单个resourceId时列表仅返回匹配资源

pc: 已具备项目下多资源数据；掌握某一资源的 `resourceId` 且该资源属于当前项目上下文

- 调用 Retrieve Project Resources List 接口，在约定位置传入单个 `resourceId`
  - 接口成功；返回列表仅包含该 id 对应资源条目（或等价过滤语义），条数与全量相比符合过滤预期
- 不传 `resourceId`（若与「仅单 id」不冲突且产品允许全量）
  - 行为符合 APIFOX：或为全量列表，或为与需求一致的默认行为

### tc-p2: 传入不存在或不属于当前项目的resourceId时返回空列表或约定错误

pc: 使用格式合法但不存在或跨租户的 `resourceId`

- 调用列表接口并传入该 `resourceId`
  - 返回体符合产品约定：空列表或明确业务错误码与文案（以 APIFOX 为准）

### tc-p3: 同时传入多个resourceId或重复id时接口拒绝或仅取单id

pc: 需求写明「限制单个 id」；若网关支持多参数需与产品确认

- 构造多 id 或数组形态入参调用接口
  - 返回 4xx/业务错误明确禁止多 id，或按实现仅采纳第一个且文档有说明（以最终实现为准并同步本用例）

## RetrieveProjectTransportHubList（按transportHubId过滤）

### tc-p1: 传入合法且归属当前项目的单个transportHubId时列表仅返回匹配站点

pc: 项目下存在多个 Transport Hub；掌握某一站点 `transportHubId`

- 调用 Retrieve Project Transport Hub List 接口，传入单个 `transportHubId`
  - 接口成功；返回列表仅包含该 id 对应站点条目

### tc-p2: 传入不存在或不属于当前项目的transportHubId时返回空列表或约定错误

pc: 使用合法格式但不存在或跨项目上下文的 `transportHubId`

- 调用列表接口并传入该 id
  - 行为符合 APIFOX 约定（空列表或业务错误）

### tc-p3: resourceId与transportHubId同时传入时的优先级或互斥规则

pc: 若接口允许两参数并存，需研发给出优先级；否则仅测禁止组合时的错误响应

- 按 APIFOX 允许的组合调用接口
  - 响应与字段说明一致，无静默错误过滤

## 通用与权限

### tc-p2: 未携带合法鉴权或项目上下文时列表接口拒绝访问

pc: 无效 token 或缺少项目维度上下文

- 调用上述任一列表接口并传入合法单 id
  - 返回 401/403 或网关统一未授权错误，不泄露其它租户数据

### tc-p3: 非法格式id（空串、非约定类型）时校验失败

pc: 构造空串、超长、非法字符等（以字段类型为准）

- 调用接口
  - 参数校验失败，错误码与提示与 APIFOX 一致
