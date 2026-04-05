# PAPI-2548 会籍 extensions 接口自动化

**用例与代码对照**：pytest / `papi2548_helpers` 逐条索引见 [`testcases/2026Q2_SP1/PAPI-2548-自动化用例与pytest对应表.md`](../../testcases/2026Q2_SP1/PAPI-2548-自动化用例与pytest对应表.md)。

**Postman / Apifox 导入**：生成集合含与 helpers 对齐的 Tests（JavaScript），说明与 JS↔Python 对照表见 [`postman/README.md`](postman/README.md)。

## 环境变量

| 变量 | 说明 |
|------|------|
| `DP_BASE_URL` | 可选，默认 `https://developer-sandbox.dragonpass.com/api`（仅域名时会自动补 `/api`） |
| `DP_PROGRAM_ID` | **必填**，内部租户 `X-Program-ID`（如 UAT 0426 对应值） |
| `DP_CLIENT_ID` | **必填**，OAuth clientId |
| `DP_CLIENT_SECRET` | **必填**，OAuth secret（勿提交仓库） |
| `DP_MEMBERSHIP_EXTENSIONS_METHOD` | 可选，默认 **`PATCH`**（兼容沙箱）；需求文档为 **`POST`** ``/v2/memberships/extensions``，网关切换后可设为 `POST` |
| `DP_X_REQUEST_ID_MODE` | 可选，默认 **`uuid`**（与 Postman 一致）；若 extensions 更新接口报 301.000.001 可改为 `numeric` |
| `DP_X_REQUEST_ID` | 可选，固定每条请求的 `X-Request-ID` |
| `DP_X_VERSION` | 可选，默认**不传** `x-version`（与通了的 curl 一致）；需要 canary 路由时设为 `canary` |
| `DP_TOKEN_OMIT_PROGRAM_ID` | 可选，设为 `1` 时取 token **不**带 `X-Program-ID`（默认：已配置 `DP_PROGRAM_ID` 则带上，与 Postman 一致） |
| `DP_TOKEN_REQUEST_BEARER` | 可选，取 token 时额外带 `Authorization: Bearer …`（填 JWT 字符串即可；与 Apifox 在 token 请求上挂父级 Bearer 一致） |
| `DP_PROFILE` | 可选，profile 名（仅 `a-zA-Z0-9_-`）。若设置，则在根目录 `.env` 之后加载 `env/.env.<profile>`，**覆盖**其中出现的同名变量（用于多环境切换） |

### 多环境（方案 A：`DP_PROFILE` + `env/`）

1. **加载顺序**（在 `conftest.py` 导入时执行）：先读仓库根目录 `.env`（不覆盖已在进程里存在的键），再若设置了 `DP_PROFILE` 且合法，则读 `env/.env.<profile>` 并**覆盖**文件中列出的键。
2. **示例文件**：可提交 `env/.env.example`、`env/.env.sandbox.example`；真实凭据放在 `env/.env.sandbox` 等（已被 `.gitignore` 忽略）。
3. **PowerShell 一键指定 profile**：

```powershell
$env:DP_PROFILE = "sandbox"
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1 -m "not manual" --alluredir=reports/papi2548-allure-results
```

也可把 `DP_PROFILE=sandbox` 写在根目录 `.env` 中，再仅维护 `env/.env.sandbox`。

### 与 curl（Apifox）的对应关系

| curl / 请求 | 环境变量 |
|-------------|----------|
| `POST https://.../api/v2/auth/token` 的 host | `DP_BASE_URL`（可含 `/api` 或由代码补全） |
| 请求头 `X-Program-ID` | `DP_PROGRAM_ID` |
| 请求体 `clientId` | `DP_CLIENT_ID` |
| 请求体 `secret` | `DP_CLIENT_SECRET` |

勿使用 Apifox 导出的 `Authorization: undefined undefined`；取 token 仅在需要时配置 `DP_TOKEN_REQUEST_BEARER`。

### 权限已开放但仍 skip / 仍报 201.000.001 时

1. **更新凭据**：网关常把权限绑到 **应用/Client**，请在开发者平台确认是否下发了**新的** `clientId` / `secret`，并同步到 `DP_CLIENT_ID`、`DP_CLIENT_SECRET`（仅改网关开关有时不会自动沿用旧密钥）。
2. **Program 一致**：`X-Program-ID` 与颁发密钥的 Program 需一致（`DP_PROGRAM_ID`）。
3. **`X-Request-ID`**：默认与 Postman 一致为 **UUID**；仅当 ``POST``/``PATCH`` ``/v2/memberships/extensions`` 报 301.000.001 时再试 `DP_X_REQUEST_ID_MODE=numeric`。
4. **`x-version`**：默认不传；若你方环境必须走 canary，再设 `DP_X_VERSION=canary`。

### 强制跳过探测（仅确认接口已可用时）

若你本地调用 extensions 已成功，但会话探测仍失败（缓存、网络路径不一致等），可**临时**设置：

| 变量 | 作用 |
|------|------|
| `DP_ASSUME_EXTENSIONS_WRITE=1` | 视为 `/v2/memberships/extensions` 写路径可用，执行写类用例 |
| `DP_ASSUME_EXTENSIONS_READ=1` | 视为 register/search 可见 `extensions`，执行读一致性类用例 |

不设上述变量时，仍按**真实探测**结果决定 skip；避免在未验证环境下误报通过。

### 读侧未上线时的行为

部分环境仅开放 **extensions 更新接口**，**search 仍不返回** `extensions`：写路径用例（UPSERT/DELETE 等）可在 `post_extensions_works` 为真时执行；依赖 **search 比对前后状态** 的用例会 skip，直至读侧发布。

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

## 说明

- 非内部租户场景未实现（与计划一致）。
- `tc-p3` SaaS feature 观测类用例标记为 `@pytest.mark.manual`，默认可被 `pytest -m "not manual"` 排除。
