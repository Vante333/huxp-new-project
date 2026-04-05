# Postman / Apifox 导入

与 [Apifox：导入 Postman](https://docs.apifox.com/doc-5174528) 一致：使用 **Postman Collection v2.1** 的 JSON；`baseUrl` 等变量在 Postman 中由集合或环境提供，导入 Apifox 后对应到项目/环境中的「服务 / 前置 URL」与变量。

## 文件

| 文件 | 用途 |
|------|------|
| [`PAPI-2548-membership-extensions.postman_collection.json`](PAPI-2548-membership-extensions.postman_collection.json) | **主文件**：Postman / Apifox → **Import** → 选择本文件。内容与 [`test_papi_2548_extensions.py`](../test_papi_2548_extensions.py) / [`papi2548_helpers.py`](../papi2548_helpers.py) 对齐（文件夹 `01 Register`～`04 E2E` 对应各类 `Test*`）。 |
| [`GeneratePostmanCollectionPapi2548.py`](GeneratePostmanCollectionPapi2548.py) | **生成器**：修改后执行 `python api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py` 重新写出上方 JSON。 |
| [`PAPI-2548-sandbox.postman_environment.json`](PAPI-2548-sandbox.postman_environment.json) | **可选**：Postman → Import → Environment；在右上角环境下拉框选中后，`baseUrl` / `programId` / `clientId` / `clientSecret` 会覆盖同名集合变量（未填的仍以集合为准）。 |

## 变量与自动化（`DP_*`）对应

| Postman（集合或环境） | 仓库 `env/.env.*` / 根目录 `.env` |
|----------------------|-----------------------------------|
| `baseUrl` | `DP_BASE_URL` |
| `programId` | `DP_PROGRAM_ID` |
| `clientId` | `DP_CLIENT_ID` |
| `clientSecret` | `DP_CLIENT_SECRET` |

`accessToken`、`membershipId` 由请求 **Tests** 脚本自动写入集合变量，一般无需手填。`fakeMembershipId` 用于「非法 membershipId」请求（默认占位长数字，可改为不存在的 id）。多步场景还会写入 **`u07aExtNorm`**、**`u03bExtNorm`**、**`e3patchNorm`**（JSON 字符串，供后续请求比对 extensions）。

## 断言（Tests）与导入 Apifox

- 集合内每个请求均带有 **Postman Tests（JavaScript）**，使用 `pm.test` / `pm.expect`，语义对齐 `papi2548_helpers` 与 `test_papi_2548_extensions`。
- **导入 Apifox** 后，这些内容通常出现在接口的 **「后置操作 / 后置脚本」** 中，**不会**自动变成 Apifox 自带的「可视化断言」卡片；若团队要求可视化断言，需在 Apifox 内按脚本逻辑手工补录。
- **权威执行**仍以本地 **pytest + Allure** 为准；Postman/Apifox 用于联调、演示与导入共享。

## JS 断言与 Python 对应（维护时同步改两处）

| JavaScript（`BuildHelpersJsLines` 内） | Python（`papi2548_helpers`） |
|----------------------------------------|------------------------------|
| `normalizeExtensionsForCompare` | `NormalizeExtensionsForCompare` |
| `extractExtensionsList` | `ExtractExtensionsList` |
| `unwrapMembershipRecord` | `UnwrapMembershipRecord` |
| `isBusinessSuccess`（根 JSON） | `IsBusinessSuccess`（信封） |
| `getInnerData` | `ParseResponseEnvelope` 得到的 `data` 对象 |
| `normalizedPairsEqual` | 元组列表 `==` 比对 |

金样例回归：[`test_p2548_normalize_parity.py`](../test_p2548_normalize_parity.py)（仅 Python 侧归一化向量；改 JS 时请人工对照）。

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

勿在取 token 请求上使用 `Authorization: undefined`；与 [`api-testcases/2026Q2_SP1/README.md`](../README.md) 中说明一致。

## 注册邮箱格式

集合内 `POST /v2/memberships` 的 `email` 统一为 **`p2548_{{$timestamp}}@yahoo.com.cn`**（时间戳较短，避免 `{{$guid}}` 过长；域名 `yahoo.com.cn`）。修改模板请编辑 `GeneratePostmanCollectionPapi2548.py` 中的 `REGISTER_EMAIL_TEMPLATE` 并重新运行生成脚本。
