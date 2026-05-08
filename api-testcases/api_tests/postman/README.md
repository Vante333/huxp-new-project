# Postman / Apifox 导入

与 [Apifox：导入 Postman](https://docs.apifox.com/doc-5174528) 一致：使用 **Postman Collection v2.1** 的 JSON；`baseUrl` 等变量在 Postman 中由集合或环境提供，导入 Apifox 后对应到项目/环境中的「服务 / 前置 URL」与变量。

## 文件

| 文件 | 用途 |
|------|------|
| [`PAPI-2548-membership-extensions.postman_collection.json`](PAPI-2548-membership-extensions.postman_collection.json) | **主文件**：Postman / Apifox → **Import** → 选择本文件。内容与 [`tests/features/test_membership_extensions.py`](../tests/features/test_membership_extensions.py) / [`services/papi2548_service.py`](../services/papi2548_service.py) 对齐（文件夹 `01 Register`～`04 E2E` 对应各类 `Test*`）。 |
| [`GeneratePostmanCollectionPapi2548.py`](GeneratePostmanCollectionPapi2548.py) | **生成器**：修改后执行 `python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2548.py` 重新写出上方 JSON。 |
| [`PAPI-2548-sandbox.postman_environment.json`](PAPI-2548-sandbox.postman_environment.json) | **可选**：Postman → Import → Environment；在右上角环境下拉框选中后，`baseUrl` / `programId` / `clientId` / `clientSecret` 会覆盖同名集合变量（未填的仍以集合为准）。 |
| [`PAPI-2515-cross-module-entitlements.postman_collection.json`](PAPI-2515-cross-module-entitlements.postman_collection.json) | **PAPI-2515**：与 [`PAPI-2548-membership-extensions.postman_collection.json`](PAPI-2548-membership-extensions.postman_collection.json) 同构——多文件夹对齐 [`tests/features/test_cross_module_entitlements.py`](../tests/features/test_cross_module_entitlements.py)；公共 JS 内联于 [`GeneratePostmanCollectionPapi2515.py`](GeneratePostmanCollectionPapi2515.py) 的 `BuildP2515JsHelpersLines()`（与 2548 的 `BuildHelpersJsLines()` 同模式）。 |
| [`GeneratePostmanCollectionPapi2515.py`](GeneratePostmanCollectionPapi2515.py) | 运行后写出上方 PAPI-2515 集合 JSON。 |

## 变量与自动化（`DP_*`）对应

| Postman（集合或环境） | 仓库 `env/.env.*` / 根目录 `.env` |
|----------------------|-----------------------------------|
| `baseUrl` | `DP_BASE_URL` |
| `programId` | `DP_PROGRAM_ID` |
| `clientId` | `DP_CLIENT_ID` |
| `clientSecret` | `DP_CLIENT_SECRET` |

`accessToken`、`membershipId` 由请求 **Tests** 脚本自动写入集合变量，一般无需手填。`fakeMembershipId` 用于「非法 membershipId」请求（默认占位长数字，可改为不存在的 id）。多步场景还会写入 **`u07aExtNorm`**、**`u03bExtNorm`**、**`e3patchNorm`**（JSON 字符串，供后续请求比对 extensions）。

**PAPI-2515**：E2E 中 `p2515_pool_plan_json` 在 **[S04]** 写入；**[S05]** 主请求打 `plan[0]`，其余条在后置脚本用 **`pm.sendRequest`** 串行发出。内联请求头 **优先克隆当前步骤 `pm.request` 里已解析的头**（与 Apifox 实际发出的主请求一致）；否则用 **`pm.variables` / `replaceIn` / 集合→环境→全局`** 拼 `Authorization`、`X-Program-ID`（缓解 `201.000.001 invalid secret`）。跳转 **[S06]** 优先 **`pm.execution.setNextRequest`**。若两者皆无则内联两次 search，可取消勾选 [S06]/[S07] 以免重复。若 Apifox 有 `setNextRequest` 但不跳到 S06，可在集合/环境设 **`DP_P2515_FORCE_INLINE_TAIL=1`**（或 **`P2515_FORCE_INLINE_TAIL`**）强制内联 S06/S07，并同样取消勾选 [S06]/[S07]。仅 **[S05]** 按池串行（``plan[1..]``）的 **`pm.sendRequest`** 需要打印入参/出参时，设 **`DP_P2515_VERBOSE_SEND_IO=1`**（或 **`P2515_VERBOSE_SEND_IO`**），在运行器 **控制台** 查看；内联 S06/S07 不打印。`probeMembershipId` 对齐 `DP_P2515_PROBE_MEMBERSHIP_ID`。

## 断言（Tests）与导入 Apifox

- 集合内每个请求均带有 **Postman Tests（JavaScript）**，使用 `pm.test` / `pm.expect`，语义对齐 `services/papi2548_service.py` 与 `tests/features/test_membership_extensions.py`。
- **导入 Apifox** 后，这些内容通常出现在接口的 **「后置操作 / 后置脚本」** 中，**不会**自动变成 Apifox 自带的「可视化断言」卡片；若团队要求可视化断言，需在 Apifox 内按脚本逻辑手工补录。
- **权威执行**仍以本地 **pytest + Allure** 为准；Postman/Apifox 用于联调、演示与导入共享。

## JS 断言与 Python 对应（维护时同步改两处）

| JavaScript（`BuildHelpersJsLines` 内） | Python（`services/papi2548_service.py` / `framework`） |
|----------------------------------------|------------------------------|
| `normalizeExtensionsForCompare` | `NormalizeExtensionsForCompare` |
| `extractExtensionsList` | `ExtractExtensionsList` |
| `unwrapMembershipRecord` | `UnwrapMembershipRecord` |
| `isBusinessSuccess`（根 JSON） | `IsBusinessSuccess`（信封） |
| `getInnerData` | `ParseResponseEnvelope` 得到的 `data` 对象 |
| `normalizedPairsEqual` | 元组列表 `==` 比对 |

金样例回归：[`tests/contract/test_membership_extensions_normalize_parity.py`](../tests/contract/test_membership_extensions_normalize_parity.py)（仅 Python 侧归一化向量；改 JS 时请人工对照）。

## 使用顺序

1. 填写 `programId`、`clientId`、`clientSecret`（及按需修改 `baseUrl`）。
2. 先跑 **00 Auth → POST /v2/auth/token**（Tests 写入 `accessToken`）。
3. 按场景选择文件夹内请求：多数 **Register** 成功后会写入 `membershipId`；**03 Extensions** 中多段流程已用 `U0`/`U0b`… 标明前置注册，请按名称顺序执行。沙箱默认 **PATCH** `/v2/memberships/extensions`；仅支持 **POST** 时用 **U09** 或自建 POST 副本。

## curl 与 Postman 对照（示例，勿粘贴真实 secret）

取 token（路径与集合「1」一致，仅作对照）：

```bash
curl -sS -X POST "https://developer-sandbox.dragonpass.com/api/v2/auth/token" \
  -H "X-Program-ID: <programId>" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\":\"<clientId>\",\"secret\":\"<clientSecret>\"}"
```

勿在取 token 请求上使用 `Authorization: undefined`；与 [`api-testcases/api_tests/README.md`](../README.md) 中说明一致。

## 注册邮箱格式

集合内 `POST /v2/memberships` 的 `email` 统一为 **`p2548_{{$timestamp}}@yahoo.com.cn`**（时间戳较短，避免 `{{$guid}}` 过长；域名 `yahoo.com.cn`）。修改模板请编辑 `GeneratePostmanCollectionPapi2548.py` 中的 `REGISTER_EMAIL_TEMPLATE` 并重新运行生成脚本。
