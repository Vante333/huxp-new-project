# PAPI-2548 自动化用例与 `papi2548_helpers` / pytest 对应表

> **说明**：业务用例与需求对照见 [`PAPI-2548-会籍extensions非标字段-测试用例.md`](PAPI-2548-会籍extensions非标字段-测试用例.md)。  
> **代码位置**：HTTP 封装、断言与探测逻辑在 [`api-testcases/2026Q2_SP1/papi2548_helpers.py`](../../api-testcases/2026Q2_SP1/papi2548_helpers.py)；**pytest 用例类**在 [`api-testcases/2026Q2_SP1/test_papi_2548_extensions.py`](../../api-testcases/2026Q2_SP1/test_papi_2548_extensions.py)。

## 环境与执行

| 项 | 说明 |
| --- | --- |
| 必填 | `DP_PROGRAM_ID`、`DP_CLIENT_ID`、`DP_CLIENT_SECRET` |
| 可选 | `DP_BASE_URL`、`DP_MEMBERSHIP_EXTENSIONS_METHOD`（默认 `PATCH`）、`DP_ASSUME_EXTENSIONS_WRITE` / `DP_ASSUME_EXTENSIONS_READ` 等，详见 [`api-testcases/2026Q2_SP1/README.md`](../../api-testcases/2026Q2_SP1/README.md) |
| 默认跑自动化（排除手工标记） | `pytest api-testcases/2026Q2_SP1/test_papi_2548_extensions.py -m "not manual" -v` |

**探测结果** `Papi2548SandboxFlags`（`ProbeExtensionCapabilities` / `BuildSandboxFlags`）：`search_shows_extensions`、`post_extensions_works` 为假时，部分用例会 **skip**，避免假通过。

---

## 一、`v2_memberships` 注册（`TestMembershipsRegisterExtensions`）

| pytest 节点 ID（节选） | Allure 标题 | 行为摘要 | 主要 helper / 入口 |
| --- | --- | --- | --- |
| `.../test_register_with_extensions_echo` | 内部租户注册携带合法 extensions 回显一致 | 注册含 `ailasId`/`cardId`；校验注册响应或 fallback 到 search 与入参一致 | `BuildMinimalMembershipPayload`、`RegisterMembershipSuccessDetail`、`PostMembershipsSearch`、`RunSearchResponseAssertions` |
| `.../test_register_duplicate_type_fails` | 同一请求 extensions 重复 type 应失败 | 两条 `cardId`：期望失败语义或 search 侧持久化断言 | `PostMemberships`、`RunSearchDuplicateTypeCardIdPersistenceAssertions` |
| `.../test_register_omit_extensions_success` | 注册不传 extensions 键应成功 | 请求体无 `extensions` 键；响应不应带非空 extensions | `BuildMinimalMembershipPayload(extensions=None)`、`RegisterMembershipSuccessDetail` |
| `.../test_register_empty_extensions_success` | 注册 extensions 为空数组应成功 | `extensions: []` | 同上 |
| `.../test_register_five_distinct_types_success` | 恰好 5 个不同 type 的 extensions 注册成功 | `t0`…`t4` | `RegisterMembershipSuccessDetail`、`RunSearchResponseAssertions` |
| `.../test_register_six_types_fails` | 6 个不同 type 的 extensions 注册应失败 | 期望业务失败；若仍为成功则 skip | `CallMembershipsExpectFailure`、`AssertPapi2548MaxFiveTypesErrorResponse`（errCode 命中时） |
| `.../test_register_type_value_length_boundary[A_128_1]` | type/value 长度边界参数化 | 128/1 成功 | `StrOfLength`、`PostMemberships` |
| `.../test_register_type_value_length_boundary[B_1_128]` | 同上 | 1/128 成功 | 同上 |
| `.../test_register_type_value_length_boundary[C_129_1]` | 同上 | 129/1 期望失败（未收紧则 skip） | 同上 |
| `.../test_register_type_value_length_boundary[D_1_129]` | 同上 | 1/129 期望失败（未收紧则 skip） | 同上 |

**完整节点 ID 前缀**：`api-testcases/2026Q2_SP1/test_papi_2548_extensions.py::TestMembershipsRegisterExtensions::`

---

## 二、`v2_memberships/search`（`TestMembershipsSearchExtensions`）

| pytest 节点 ID（节选） | Allure 标题 | 行为摘要 | 主要 helper |
| --- | --- | --- | --- |
| `.../test_search_extensions_match_register` | search 返回的 extensions 与注册一致 | 需 `search_shows_extensions` | `RegisterMembershipSuccess`、`PostMembershipsSearch`、`RunSearchResponseAssertions` |
| `.../test_search_membership_without_extensions_semantics` | 未传 extensions 注册的会籍 search 时 extensions 为空或省略 | — | `RunSearchOmitExtensionsSemanticsAssertions` |

**完整节点 ID 前缀**：`...::TestMembershipsSearchExtensions::`

---

## 三、`v2_memberships/extensions` 更新（`TestMembershipsExtensionsUpdate`）

| pytest 节点 ID（节选） | Allure 标题 | 前置 | 行为摘要 | 主要 helper |
| --- | --- | --- | --- | --- |
| `.../test_extensions_upsert_add_new_type` | UPSERT 新增 type 成功且返回完整 extensions | `post_extensions_works` | 注册一条后 UPSERT 新 type | `PatchMembershipsExtensions`、`RunPatchExtensionsAssertions` |
| `.../test_extensions_upsert_update_value` | UPSERT 已存在 type 更新 value | 同上 | 更新 `k1` 的 value | 同上 |
| `.../test_extensions_delete_existing_type` | DELETE 移除已有 type | 同上 | DELETE `a1`，保留 `b2` | 同上 |
| `.../test_extensions_delete_nonexistent_type_idempotent` | DELETE 不存在的 type 仍成功且数据不变 | 写成功 + `search_shows_extensions` | search 快照前后比对 | `RunSearchSnapshotForDeleteAssertions`、`RunPatchExtensionsAssertions` |
| `.../test_extensions_mixed_operations` | 同一请求混合 UPSERT 与 DELETE | `post_extensions_works` | DELETE+UPSERT 组合 | `RunPatchExtensionsAssertions` |
| `.../test_extensions_invalid_membership_id_fails` | membershipId 不存在时应失败 | — | 随机不存在的 id | `RunPatchInvalidMembershipIdAssertions` |
| `.../test_extensions_invalid_operation_fails` | 非法 operation 不得改变已持久化的 extensions | `search_shows_extensions` | `UPDATE` 非法；前后 search 一致 | `RunPatchInvalidOperationGatewayAssertions` |
| `.../test_extensions_upsert_missing_value_documented` | UPSERT 缺少 value：按契约记录行为 | — | 文档化实际成功/失败 | `RunUpsertMissingValueDocumentedAssertions` |

HTTP 方法由 `GetMembershipsExtensionsHttpMethod()` / `DP_MEMBERSHIP_EXTENSIONS_METHOD` 决定；标签见 `MembershipsExtensionsHttpContextLabel()`。

**完整节点 ID 前缀**：`...::TestMembershipsExtensionsUpdate::`

---

## 四、E2E（`TestMembershipsExtensionsE2E`）

| pytest 节点 ID | Allure 标题 | 前置 | 行为摘要 |
| --- | --- | --- | --- |
| `.../test_e2e_register_search_extensions_search` | 注册→search→extensions→search 闭环一致 | `post_extensions_works` 且 `search_shows_extensions` | 注册 → search#1 → PATCH → search#2，最终集合与 PATCH 一致 |

---

## 五、手工 / 占位（`@pytest.mark.manual`）

| pytest 节点 ID | Allure 标题 | 说明 |
| --- | --- | --- |
| `...::TestManualObservation::test_placeholder_saas_feature_not_automated` | SaaS feature 存放（需人工/DB/管理端） | 默认 skip；见需求侧手工 tc-p3 |

---

## `papi2548_helpers.py` 按职责速查（节选）

| 类别 | 代表函数 |
| --- | --- |
| 环境与鉴权 | `GetBaseUrl`、`GetProgramId`、`GetClientId`、`GetClientSecret`、`GetAccessToken`、`BuildCommonHeaders` |
| 注册 / 查询 | `BuildMinimalMembershipPayload`、`PostMemberships`、`RegisterMembershipSuccess`、`RegisterMembershipSuccessDetail`、`PostMembershipsSearch` |
| extensions 写 | `PatchMembershipsExtensions`、`GetMembershipsExtensionsHttpMethod` |
| 规范化与抽取 | `ExtractExtensionsList`、`ExtractMembershipId`、`NormalizeExtensionsForCompare` |
| 沙箱探测 | `ProbeExtensionCapabilities`、`BuildSandboxFlags` |
| 断言与场景步骤 | `RunSearchResponseAssertions`、`RunPatchExtensionsAssertions`、`AssertRegisterCoreFields`、`AssertPapi2548DuplicateTypeErrorResponse` 等 |

---

*本文档由仓库内 `test_papi_2548_extensions.py` 与 `papi2548_helpers.py` 结构整理生成；若代码增删用例，请同步更新本表。*
