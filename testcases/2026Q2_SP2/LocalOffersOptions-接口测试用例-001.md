# LocalOffersOptions接口测试用例

## 测试范围说明

- rc: MCP OpenAPI `project-0-interface_cursor-Q2 local offer`：`GET /v2/resources/localOffers/{resourceId}/options`
- rc: 自动化入口 [`api-testcases/api_tests/tests/features/test_local_offers_options.py`](../../api-testcases/api_tests/tests/features/test_local_offers_options.py)
- rc: 契约入口 [`api-testcases/api_tests/tests/contract/test_local_offers_options_contract.py`](../../api-testcases/api_tests/tests/contract/test_local_offers_options_contract.py)
- 环境：优先 `DP_PROFILE=canary`；正向用例依赖 `DP_LOCAL_OFFER_RESOURCE_ID` 指向 canary 中存在且可返回 options 的 Local Offer 资源。
- 接口口径：只读查询接口，必填 path `resourceId`，必填 headers `Authorization`、`X-Program-ID`、`X-Request-ID`、`Content-Type`，可选 query `duration`、`pageSize`、`pageNumber`、`language`。

## v2_resources_localOffers_{resourceId}_options（RetrieveLocalOfferResourcesOptions）

### tc-p1: 最小必填查询返回LocalOffersOptions列表

- pc: 已配置 canary 凭据 `DP_CLIENT_ID`、`DP_CLIENT_SECRET`、`DP_PROGRAM_ID`。
- pc: `DP_LOCAL_OFFER_RESOURCE_ID` 指向存在的 Local Offer 资源。
- 使用合法 token、`X-Program-ID`、`X-Request-ID`、`Content-Type` 请求 `GET /v2/resources/localOffers/{resourceId}/options?pageSize=10&pageNumber=1`。
  - 预期 HTTP 状态为 200。
- 检查响应根节点 `code`。
  - 预期 `code=0` 时返回业务成功；若 canary 数据暂不可用返回 `code=-1/500.020.016`，自动化记录为 skip 而非假失败。
- 检查成功响应 `data.pagination`、`data.resourceId`、`data.resourceName`、`data.optionList`。
  - 预期字段存在且类型符合 OpenAPI 契约。
- rc: pytest `test_LocalOffersOptions_MinimalRequired_Smoke`
- tag: smoke,local_offers,contract

### tc-p1: 查询参数组合不破坏响应契约

- pc: 已满足 `tc-p1: 最小必填查询返回LocalOffersOptions列表` 的前置条件。
- 使用合法 token 请求 `GET /v2/resources/localOffers/{resourceId}/options?pageSize=5&pageNumber=1&language=en-US&duration=7`。
  - 预期 HTTP 状态为 200。
- 检查成功响应中的 `pagination.pageSize` 与 `pagination.pageNumber`。
  - 预期分别回显为 5 和 1。
- 检查 `optionList` 中每个 option 的 `optionId`、`optionName`、`marketingTag`、`validity`。
  - 预期必填字段存在，`marketingTag` 仅允许 `"1"`、`"2"`、`"3"`、`"4"` 或 canary 当前返回的整数 `1`、`2`、`3`、`4`，`validity.type` 仅允许 1、2、3。
- rc: pytest `test_LocalOffersOptions_QueryParameters_ShouldEchoPaginationAndKeepContract`
- tag: feature,local_offers

### tc-p2: 不存在的resourceId不应业务成功

- pc: 已获取合法 token，并配置 canary `DP_PROGRAM_ID`。
- 使用不存在的 `resourceId=LO_NOT_EXIST_000000` 请求 options。
  - 预期接口返回资源不存在相关失败，或 HTTP 200 但业务 `code` 不为 0。
- 检查失败响应。
  - 预期不得出现业务成功。
- rc: pytest `test_LocalOffersOptions_UnknownResourceId_ShouldFail`
- tag: feature,negative

### tc-p2: 必填path参数resourceId为空不应业务成功

- pc: 已获取合法 token，并配置 canary `DP_PROGRAM_ID`。
- 使用空 `resourceId` 请求 options。
  - 预期接口返回路由/参数失败，或 HTTP 200 但业务 `code` 不为 0。
- 检查失败响应。
  - 预期不得出现业务成功。
- rc: pytest `test_LocalOffersOptions_EmptyResourceId_ShouldFail`
- tag: feature,negative,required

### tc-p2: resourceId非法格式不应业务成功

- pc: 已获取合法 token，并配置 canary `DP_PROGRAM_ID`。
- 参数化使用特殊字符、路径穿透样式、超长 resourceId 请求 options。
  - 预期接口返回路由/参数失败，或 HTTP 200 但业务 `code` 不为 0。
- 检查失败响应。
  - 预期不得出现业务成功。
- rc: pytest `test_LocalOffersOptions_InvalidResourceIdFormat_ShouldFail`
- tag: feature,negative,length

### tc-p2: 分页参数越界或类型错误不应业务成功

- pc: 已获取合法 token，并配置 canary `DP_LOCAL_OFFER_RESOURCE_ID`。
- 参数化请求 `pageSize=0`、`pageSize=101`、`pageNumber=0`、`pageNumber=101`、`pageSize=-1`、`pageSize=abc`。
  - 预期接口返回参数失败，或 HTTP 200 但业务 `code` 不为 0。
- 检查失败响应。
  - 预期不得出现业务成功。
- rc: pytest `test_LocalOffersOptions_InvalidPagination_ShouldFail`
- tag: feature,negative,boundary

### tc-p2: 可选查询参数非法不应业务成功

- pc: 已获取合法 token，并配置 canary `DP_LOCAL_OFFER_RESOURCE_ID`。
- 参数化请求 `duration=-1`、`duration=seven`、`language=invalid-lang`、超长 `language`。
  - 预期接口返回参数失败，或 HTTP 200 但业务 `code` 不为 0。
- 记录 canary 当前行为。
  - 预期 `duration=-1`、`duration=seven` 暂以严格 xfail 观察；若后续服务端改为拒绝，pytest 会提示 XPASS，需要同步调整预期。
- 检查失败响应。
  - 预期不得出现业务成功。
- rc: pytest `test_LocalOffersOptions_InvalidOptionalQuery_ShouldFail`
- tag: feature,negative,boundary

### tc-p2: OpenAPI成功响应契约本地校验

- pc: 使用 MCP OpenAPI 示例构造本地响应样例，不访问外部环境。
- 构造包含 `validity.type=1` 固定日期、`type=2` 相对时长、`type=3` 动态有效期的成功响应。
  - 预期契约断言通过。
- 构造 `marketingTag` 越界或 `validity.unit` 越界的响应。
  - 预期契约断言失败并能定位字段。
- 构造 `marketingTag` 为整数枚举 `1`、`2`、`3`、`4` 的响应。
  - 预期契约断言通过，并记录 MCP 文档与 canary 实际类型差异。
- 构造缺少 `code`、`data`、`pagination`、`optionId`、`validity.type` 等必填字段的响应。
  - 预期契约断言失败并能定位字段。
- 构造 `pageSize/pageNumber` 越界、`totalNumber` 为负数、必填字符串为空、`optionList` 非数组的响应。
  - 预期契约断言失败并能定位字段。
- 构造 `validity.type` 越界、`unit` 非法、固定日期缺少 `startTime/endTime` 的响应。
  - 预期契约断言失败并能定位字段。
- rc: pytest `test_local_offers_options_contract.py`
- tag: contract,local_offers

### tc-p3: canary正向数据未准备时的跳过策略

- pc: canary 未配置 `DP_LOCAL_OFFER_RESOURCE_ID`，或默认 `LO00001` 在 canary 返回 `500.020.016`。
- 运行正向 smoke / feature 用例。
  - 预期用例以 skip 结束，并在原因中提示资源可能不存在或数据暂不可用。
- 检查负向用例执行结果。
  - 预期不存在资源、空 resourceId、非法 resourceId、非法分页等负向用例仍可独立验证。
- tag: canary,maintainability
