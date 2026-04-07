# api-testcases/2026Q2_SP1（PAPI-2548 + PAPI-2515 + PAPI-2424）

## PAPI-2548 会籍 extensions

**用例与代码对照**：pytest / `papi2548_helpers` 逐条索引见 [`testcases/2026Q2_SP1/PAPI-2548-自动化用例与pytest对应表.md`](../../testcases/2026Q2_SP1/PAPI-2548-自动化用例与pytest对应表.md)。

**Postman / Apifox 导入**：生成集合含与 helpers 对齐的 Tests（JavaScript），说明与 JS↔Python 对照表见 [`postman/README.md`](postman/README.md)。

分层配置与运行前置约定见 [`.cursor/skills/api-testcase-pack/SKILL.md`](../../.cursor/skills/api-testcase-pack/SKILL.md)、[`env/README.md`](../../env/README.md)。

**新增需求 helpers 风格**：模块 docstring 写清 **主链路**（HTTP 顺序），产品主场景提供 **`Run…MainE2EScenario`**，主 E2E 用例只调该入口；见 Skill 中「主链路与单一编排函数」与金样例 `RunPapi2548MainE2EScenario`、`RunP2515MainE2EScenario`。

## 安装依赖

```bash
pip install -r ../../tools/requirements.txt
```

## 运行测试并生成 Allure 原始数据

本目录下 **`pytest.ini`** 已配置 **`addopts = --clean-alluredir`**：只要命令行带上 **`--alluredir=...`**，每次运行会先**清空**该目录再写入，避免多次结果合并导致报告里用例数翻倍（例如出现两个 Suite、各 21 条）。

在仓库根目录或本目录下：

```bash
cd api-testcases/2026Q2_SP1
pytest . -v --alluredir=../../reports/papi2548-allure-results
```

从仓库根执行时仍需设置 `PYTHONPATH` 指向本目录，例如：

```bash
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1 -m "not manual" --alluredir=reports/papi2548-allure-results
```

## 查看 Allure 报告（含每步请求/响应 JSON 附件）

需已安装 [Allure Commandline](https://github.com/allure-framework/allure2/releases)。

**推荐（每次仅保留一份原始结果）**：单独执行 `allure serve` 不会清空 `reports/papi2548-allure-results`；若希望「打开报告前删掉旧结果 → 再跑 pytest → 再 serve」一条命令完成，在仓库根执行：

```bash
python tools/ServePapi2548Allure.py
```

若本轮已跑过 pytest、只需打开当前结果目录：

```bash
python tools/ServePapi2548Allure.py --serve-only
```

等价的手动命令（在 `api-testcases/2026Q2_SP1` 下）：

```bash
allure serve ../../reports/papi2548-allure-results
```

浏览器打开后，在每条用例的 **Steps** 与 **Attachments** 中可查看脱敏后的 headers、请求体与响应体。

**断言结果**：各 `Assert*` 在子步骤下附加 **唯一文件名** 的 `断言结果_XXX_…_结构化.json.txt`（JSON 格式化文本）与 `_可读.txt`（纯文本），类型均为 `text/plain`，避免 Allure 对 `application/json` 附件「有大小但预览空白」的问题。每条用例开始前由 conftest 复位序号。

**HTTP 步骤附件规范（与 Allure 模板一致）**：凡走 `RequestWithAllure` 的步骤，在步骤内依次为 **`request_step_meta`**（仅当传入 `step_code`/`step_title`）、**`request_meta`**、**`response_body_json`**（非 JSON 时为 **`response_body_text`**）、**`response_status`**。附件类型均为 **`text/plain`**（含 JSON 内容亦为格式化文本），避免 Allure 2.x 对 `application/json` 内嵌预览空白。`GetAccessToken` 无场景序号时不生成 `request_step_meta`。

**步骤层级（search / PATCH 与断言同屏）**：`RegisterMembershipSuccessDetail` 已在注册请求的 `after_response` 内完成成功断言。对 **search、PATCH**，用例统一通过 **`after_response`** 调用 `RunSearchResponseAssertions`、`RunPatchExtensionsAssertions`、`RunSearchSnapshotForDeleteAssertions` 等（见 `papi2548_helpers.py`），保证 **HTTP 附件之后立刻跟对应断言**，避免断言落在顶层步骤、与请求脱节。

**步骤标题与序列码**：`RequestWithAllure` 支持 `step_code`（如 `S01`）、`step_title`（如 `步骤1 · 注册会籍`），步骤名为 `[S01] 步骤1 · 注册会籍 · POST /v2/memberships`。用例中可使用 fixture **`ScenarioSteps`** 与 **`_StepKw(ScenarioSteps, "简述")`** 展开传入各 HTTP 封装。

## 精细字段断言（响应新增 key 时）

在 `papi2548_helpers.py` 中可使用：

| 函数 | 用途 |
|------|------|
| `AssertDictKeyValues(actual, {"k": v}, context="…")` | 只断言列出的键存在且与期望值 `==`（`actual` 可含其它键） |
| `AssertNestedStructureEqual(actual, expected)` | 嵌套 dict/list 递归相等，适合整段 JSON 片段 |
| `RegisterMembershipSuccessDetail` | 返回 `(membershipId, extensions, data)`，对 `data` 做键值比对 |
| `AssertRegisterCoreFields` / `AssertSearchMembershipCoreFields` | 注册 / search 单条上的 `programId`、`clientUserId`、`status` 等 |
| `AssertExtensionItemInList` | `extensions` 数组中按 `type`（及可选 `value`）定位一条 |
| `AssertExtensionsNormalizedEqual` | 与入参/另一响应的 extensions **集合完全一致**（排序归一后比对） |
| `AssertExtensionItemsKeyShape` | 每条 extension 必含 `type`/`value` 等，可选 **白名单键** |
| `AssertNoDuplicateExtensionTypesInList` | 同一会籍下 `type` 不重复 |
| `AssertAtMostOneExtensionOfType` | 某 `type` 至多一条（重复 type 注册场景） |
| `AssertRegisterSelectedFieldsEchoed` | 注册 `data` 与请求体在约定字段上回显一致 |
| `AssertBusinessFailureEnvelope` | 负面用例：不得 HTTP 200 + 业务成功 |
| `AssertRootBusinessCodeIndicatesFailure` | 根 JSON `code != 0`（非法 membershipId 等） |

`test_papi_2548_extensions.py` 中已按**每条用例的测试重点**组合上述断言，并用 `allure.step` 区分步骤。

示例：需求约定响应新增 `extensionsSchemaVersion: 1` 时，在拿到 `body_reg` 后增加：

`AssertDictKeyValues(body_reg, {"extensionsSchemaVersion": 1}, context="PAPI-2548")`

## 与 Postman（membership-extansion）断言风格对齐

桌面集合中 Apifox 导出脚本常见写法：

- **JSONPath**：`$.code` 等于 `0`；成功体上 `$.data.membershipId`、`$.data.extensions`、`$.data.extensions[0]` 等。
- **失败体**：`$.errCode`、`$.msg`（英文文案）。
- **funcChina**：响应全文不出现 CJK 汉字（`\u4e00-\u9fa5`）。

Python 侧对应函数（`papi2548_helpers.py`）：

| Postman 习惯 | 函数 |
|--------------|------|
| `$.code == 0` 及若干路径 | `AssertPostmanStyleSuccessResponse(resp, extra_json_paths={...})` |
| 单路径比对 | `AssertJsonPathEquals(root, "$.data.extensions[0]", {"type":"aa","value":"12"})` |
| `$.errCode` + `$.msg` 子串 | `AssertPostmanStyleErrorResponse(resp, expect_err_code="500.030.033", msg_contains="…")` 或 `AssertPapi2548DuplicateTypeErrorResponse` / `AssertPapi2548MaxFiveTypesErrorResponse`（整句 msg 与 `papi2548_helpers` 中常量一致） |
| 响应体无中文 | 环境变量 `DP_POSTMAN_NO_CJK_BODY=1`，或对 `AssertPostmanStyleSuccessResponse(..., strict_no_cjk_body=True)` |

### PAPI-2548 业务错误 errCode / msg（根节点）

| errCode | msg（英文全文） |
| --- | --- |
| `500.030.032` | `Duplicate extension type detected. Each type must be unique within a membership.` |
| `500.030.033` | `A maximum of 5 extension types is allowed per membership.` |
| `500.030.034` | `Failed to update membership extensions. Please try again later.` |

常量名：`PAPI2548_EXT_ERR_*`、`PAPI2548_EXT_MSG_*`（见 `papi2548_helpers.py`）。历史沙箱可能用 `500.030.033`/`500.030.034` 分别表示「重复 type」「超 5 条」，断言函数已兼容。

底层路径解析使用 `JsonPathEvaluate(root, path)`，覆盖集合里出现的 `$.data.*`、`[0]` 等形式即可；更复杂 JSONPath 可再扩展或改用专用库。

## PAPI-2515 crossModuleEntitlements

**代码**：[`papi2515_helpers.py`](papi2515_helpers.py)、[`test_papi_2515_cross_module_entitlements.py`](test_papi_2515_cross_module_entitlements.py)。**手工用例**：[PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md](../../testcases/2026Q2_SP1/PAPI-2515-crossModuleEntitlements返回结构优化-测试用例.md)。

**OpenAPI 契约（Default module）**：`POST /v2/entitlements/search`；**两个不同的 update**：`POST /v2/entitlements/update`（按 body 定位，典型 moduleExclusive）与 `POST /v2/entitlements/{entitlementPoolId}/update`（路径带池 ID，cross 单池更新）。与 MCP OAS 一致。

**summary 与 pools 加总**：默认 **严格** 断言每组 `summary` 等于各池 `details` 同类字段之和；**某池缺该键按 0 计入**。严格断言时 Allure 会附带 `p2515_summary_vs_details_*.json.txt`（四字段的 `summary`、`pools_breakdown`、`details_sum` 对照表）。若仍与网关不一致，可设 `DP_P2515_RELAX_SUMMARY_POOL_SUM=1`。

### 环境变量（摘要）

| 变量 | 说明 |
|------|------|
| `DP_CLIENT_ID` / `DP_CLIENT_SECRET` | 取 token（与 2548 相同） |
| `DP_PROGRAM_ID` 或 `DP_P2515_PROGRAM_ID` | 注册造数用 program（后者优先） |
| `DP_P2515_INCLUDE_PROBE` | 设为 `1`/`true`/`yes`/`on` 时才**收集**环境探测用例 `p2515_probe_membership`（默认不收集） |
| `DP_P2515_PROBE_MEMBERSHIP_ID` | 与上一项联用：已有会籍 ID（须含非空 crossModule） |
| `DP_P2515_REGISTER_EXTRA_JSON` | 注册 body 额外合并（JSON 对象字符串） |
| `DP_P2515_ATTACH2_*` | 单品类 update 与单池 update 数量覆盖，见根目录 `.env.example` |

### 运行

**本地默认**：不收集「环境会籍 ID 探测」用例（`p2515_probe_membership`），无需配置 `DP_P2515_PROBE_MEMBERSHIP_ID`；主链走注册造数即可。若要在 CI/排障时跑探测：设 `DP_P2515_INCLUDE_PROBE=1` 且配置 `DP_P2515_PROBE_MEMBERSHIP_ID`。

仅收集（不写沙箱权益）：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1/test_papi_2515_cross_module_entitlements.py -m "not needs_cross_module_write" -v
```

只跑注册造数主 E2E（单条，**会改写**权益）：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest "api-testcases/2026Q2_SP1/test_papi_2515_cross_module_entitlements.py::TestP2515CrossModuleE2E::test_e2e_register_search_module_update_pool_updates" -v --alluredir=reports/papi2515-allure-results
```

全链路（**会改写**新注册会籍的权益数值，同文件内全部 `needs_cross_module_write`）：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1/test_papi_2515_cross_module_entitlements.py -m needs_cross_module_write -v --alluredir=reports/papi2515-allure-results
```

**跳过条件**：模板无跨模块权益时 `crossModuleEntitlements` 为空，主场景会 `pytest.skip`；单池 `details` 均为 `-1` 时无可执行池更新亦会跳过。若按池更新返回 ``errCode=500.030.024``（program 禁止按池编辑），单池链路会以 skip 结束并提示换模板。

**注意**：直接 `pytest api-testcases/2026Q2_SP1` 会收集 PAPI-2515 写用例；若已配置有效 `DP_PROGRAM_ID` 且模板含 crossModule，将注册新会籍并改写权益。日常只跑 2548 时可加 `-m "not needs_cross_module_write"`。

**为何某步断言失败后 Allure 里看不到后续 HTTP 步骤**：pytest 中普通 `assert` 失败会抛出 `AssertionError` 并**立即结束当前用例函数**。**PAPI-2515 主 E2E**（`test_e2e_register_search_module_update_pool_updates`）已改用 ``P2515E2ESoftAssert``：业务断言失败会记入列表，**仍继续**后续 HTTP，最后用 ``pytest.fail`` 汇总；取 token / 注册 / search 等**前置 HTTP 仍硬失败即停**（无数据则无法继续）。其它用例仍为硬断言。

**注册与 entitlements/update**：若响应 `data.entitlements` 中带 `crossModuleEntitlements` / `moduleExclusiveEntitlements`，自动化会对 **cross** 使用与 search 相同的 `summary` vs `pools`（缺键按 0）及 Allure 分解附件；对 **moduleExclusive** 仅校验各条 `details` 不含携伴聚合字段（无 summary/pools 恒等式）。

### Postman

集合生成脚本见 [`postman/GeneratePostmanCollectionPapi2515.py`](postman/GeneratePostmanCollectionPapi2515.py) 与 [`postman/README.md`](postman/README.md)。

## PAPI-2424 ePasses details / MS 订单提示

**手工用例**：[PAPI-2424-ePasses-details-MS订单提示-测试用例.md](../../testcases/2026Q2_SP1/PAPI-2424-ePasses-details-MS订单提示-测试用例.md)。

**代码**：[`papi2424_helpers.py`](papi2424_helpers.py)、[`test_papi_2424_ePasses_details_ms_order_hint.py`](test_papi_2424_ePasses_details_ms_order_hint.py)。

**OpenAPI（MCP · Default module）**：`POST /v2/orders/ePasses/details`（Retrieve E-pass Usage Order Details）；MS 主单应使用 `POST /v2/orders/ePasses/search`（文档称 order ID 可以 MS 开头）。

### 环境变量（摘要）

| 变量 | 说明 |
|------|------|
| `DP_P2424_V2_ORDERS_EPASSES_DETAILS_PATH` | 可选，覆盖 V2 path，默认 `/v2/orders/ePasses/details` |
| `DP_P2424_V1_ORDERS_EPASSES_DETAILS_PATH` | 配置 V1 path 后执行 V1/V2 对拍用例；不配置则 skip |
| `DP_P2424_USAGE_ORDER_ID` | 非 MS 开头的 usage 订单号；配合 marker `needs_p2424_usage_order_id` |
| `DP_P2424_MS_PREFIX_CASE_INSENSITIVE` | `1`/`true` 等：小写 `ms` 前缀期望同大写命中 `500.000.024` |

**PAPI-2424（强制三件套）**：`DP_EPASS_PROGRAM_ID`、`DP_EPASS_CLIENT_ID`、`DP_EPASS_CLIENT_SECRET`（与 curl 中 `X-Program-ID` 与 token 请求体一致）；由 `GetAccessTokenForEpass` 取 token，`PostOrdersEPassesDetails` 等业务请求通过 `x_program_id` 发送同一 `DP_EPASS_PROGRAM_ID`。父级 Bearer 可选：`DP_EPASS_TOKEN_REQUEST_BEARER` 或 `DP_TOKEN_REQUEST_BEARER`。默认 `DP_PROGRAM_ID` 可继续给 PAPI-2548/2515 使用，不必与 ePass program 相同。

### 运行示例

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1/test_papi_2424_ePasses_details_ms_order_hint.py -v --alluredir=reports/papi2424-allure-results
```

默认不配置 `DP_P2424_USAGE_ORDER_ID` 时，tc-P1 回归条会 **skip**；可用 `-m "not needs_p2424_usage_order_id"` 只跑不依赖该 ID 的用例。

---

## 说明（PAPI-2548）

- 非内部租户场景未实现（与计划一致）。
- `tc-p3` SaaS feature 观测类用例标记为 `@pytest.mark.manual`，默认可被 `pytest -m "not manual"` 排除。
