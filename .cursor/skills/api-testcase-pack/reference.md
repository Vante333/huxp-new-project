# 接口自动化套件：附录（模板与命令）

## 建议目录结构（新需求/迭代）

将 `{TICKET}` 换为如 `PAPI-2548`，`{SPRINT}` 换为如 `2026Q2_SP1`：

```
api-testcases/{SPRINT}/
  README.md
  pytest.ini
  conftest.py
  {ticket}_helpers.py          # 或小写前缀，与套件内 import 一致
  test_{ticket}_*.py
  postman/
    README.md
    GeneratePostmanCollection{TICKET}.py
    {TICKET}-*.postman_collection.json
    {TICKET}-*.postman_environment.json   # 可选
testcases/{SPRINT}/
  {TICKET}-自动化用例与pytest对应表.md    # 可选但推荐
```

## 环境：分层加载（与金样例一致）

1. 仓库根目录 `.env`：不覆盖已在进程环境中的键。
2. 若设置 `DP_PROFILE`（仅 `a-zA-Z0-9_-`），加载 `env/.env.<profile>` 并**覆盖**同名键。

PowerShell 示例（在仓库根执行）：

```powershell
$env:DP_PROFILE = "sandbox"
$env:PYTHONPATH = (Resolve-Path "api-testcases\2026Q2_SP1").Path
pytest api-testcases/2026Q2_SP1 -m "not manual" --alluredir=reports/papi2548-allure-results
```

将路径中的 `2026Q2_SP1`、`papi2548` 换成当前套件对应目录与报告名。

## pytest + Allure

在本套件目录内：

```powershell
cd api-testcases\2026Q2_SP1
pytest . -v --alluredir=..\..\reports\papi2548-allure-results
```

安装 Allure CLI 后查看报告：

```powershell
allure serve ..\..\reports\papi2548-allure-results
```

`pytest.ini` 中应包含 `addopts = --clean-alluredir`，以便每次带 `--alluredir` 运行时先清空目录，避免多次运行合并导致用例数翻倍。

## Postman 生成器（2548/2515 金样例形态）

- **Schema**：`https://schema.getpostman.com/json/collection/v2.1.0/collection.json`
- **脚本单一来源（与 2548 一致）**：公共 JavaScript 写在 **`apifox-cli/generators/GeneratePostmanCollection<需求>.py`** 的 **`Build<需求>JsHelpersLines()`** 内（`js = r"""..."""`，再 `splitlines()` 写入 `event`），**不要**单独维护与生成器并行的仓库根 `*.js` 作为唯一规范（除非团队明确要求）。集合写出到 **`apifox-cli/collections/`**。
- **结构**：**多文件夹**（如 `00 Auth`、按 `Test*` 区分的 E2E / Doc gap）；**主链路 HTTP 顺序**对齐对应 `Run…MainE2EScenario` 与 helpers **主链路**表（例：2515 含多次 `entitlements/search`、按池 update 与集合变量 `p2515_pool_update_body_raw` 等）。

### 测试目的前置命名（默认，非可选）

**完整细则**：[`postman-purpose-first-naming.md`](./postman-purpose-first-naming.md)

- **展示名**：`【测试目的】| 步骤ID | METHOD /path简写`（禁止 `S02 POST prebooking（…）` 旧式）。
- **实现**：`PurposeName()` + `RequestItem(name=...)`；多模块用 `StepSpec(purpose=..., step_id=...)`，封装函数带 **`purpose=`** 关键字参数。
- **金样例对照**：`api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionLocalOfferEpass.py`（P1）、`GeneratePostmanCollectionLocalOfferEpassFull.py`（Full）。
- **2548/2515 新建集合**：在对应 `GeneratePostmanCollection*.py` 中**同样引入** `PurposeName`，逐步把 `name=` 从步骤描述改为目的前置（与 pytest 断言意图一致）。
- **事件**：每个请求的 `event` 中 `listen: "test"`，`script.exec` 为字符串数组：先整段 helpers，再 `save_token` / `save_mid` / 场景专属 `Lines_*`（见 `MakeTestEvent` / `MakeP2515TestEvent` 模式）。
- **变量**：集合（及可选环境 JSON）中定义 `baseUrl`、`programId`、`clientId`、`clientSecret` 等，与 `apifox-cli/README.md` 中 `DP_*` 对照表一致。
- **注册体**：`firstName` / `lastName` 等若网关要求**仅拉丁字母**，模板中勿填中文或数字；标识可用 `email` 前缀等。
- **生成命令**（仓库根）：`python api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py` 或 `…Papi2515.py`。
- **导入**：Postman / Apifox **Import** 写出的 `*.postman_collection.json`；Apifox 中脚本在「后置操作」。团队流程见 [`apifox-cli/README.md`](../../../api-testcases/2026Q2_SP1/postman/README.md)。
- **Apifox 排障（Agent 必读）**：[`postman-apifox-troubleshooting.md`](./postman-apifox-troubleshooting.md) — 后置 `fp*` 未定义、永久 loading、取消重试、schedule 动态日期、busy-wait 卡顿；**§0 决策树**。
- **预预约 payment 断言（Lounge / FT）**：[`prebooking-payment-apifox-assertions.md`](./prebooking-payment-apifox-assertions.md) — Preview/Create/Detail 三接口、`payableAmount` 分支、C-1～C-3 算价；脚本 [`tools/payment-js/apifox_payment_assert_pre.js`](../../../tools/payment-js/apifox_payment_assert_pre.js)、[`tools/payment-js/apifox_payment_assert_post.js`](../../../tools/payment-js/apifox_payment_assert_post.js)。
- **pytest ↔ 片段索引（可选）**：2515 示例 [`PAPI-2515-apifox-export-from-pytest.md`](../../../api-testcases/2026Q2_SP1/postman/PAPI-2515-apifox-export-from-pytest.md)。

## 依赖

金样例依赖见仓库 [`tools/requirements.txt`](../../../tools/requirements.txt)（在套件 README 中引用 `pip install -r ...`）。

## 自动造数与 Apifox 链路对照

本附录配合主文档 [SKILL.md](SKILL.md) 中 **「自动造数（优先于手工 ID）」** 使用。

### 映射原则

1. **以 Apifox / 用例附件中的请求顺序为权威**，在 `*_helpers.py` 中实现同序调用（或拆成可复用函数再在 session 造数函数中组合）。
2. 每一步对应 **一次** `RequestWithAllure`（或封装它的 `Post*`/`Get*` 函数）；需要报告可读性时，用 `allure.step("…")` 包裹一整段子链，并在用例里用 `ScenarioSteps` + `_StepKw` 生成 `step_code` / `step_title`。
3. **可复用业务断言**：在 `*_helpers.py` 中实现 **`Assert*`** 时，与金样例一致使用 **`from papi2548_helpers import _RunAllureAssertionStep`**，在 **`def _Do() -> str`** 内写 `assert`，成功则 `return` 摘要，外层 **`_RunAllureAssertionStep("PAPI-xxxx: …", _Do)`**。这样会生成 **Allure 子步骤** 与 **`断言结果_*`** 附件；不要只写裸 `assert`。若断言必须出现在某一 HTTP 步骤**内部**，在该请求的 **`after_response`** 回调里调用该 `Assert*`。
4. **会话造数**（`conftest.py` 中 `scope="session"`）适合「整条套件共用的主体数据」；若单测必须隔离数据，可改为 function scope 或每条用例内注册（注意耗时与沙箱配额）。

### 典型步骤与金样例对应关系（示例）

| Apifox 步骤（示例） | pytest / helpers 落点 |
|---------------------|------------------------|
| 取 Token | `GetAccessToken()`（`papi2548_helpers`） |
| 注册会籍 | `RegisterMembershipSuccessDetail` + `BuildMinimalMembershipPayload`（可合并 `extra` JSON） |
| 注册后 search 权益 | `PostEntitlementsSearch`（`papi2515_helpers`） |
| 单品类 update → 再 search | `PostEntitlementsUpdate` 后接 `PostEntitlementsSearch`（见 `RunP2515Attach2Scenario`） |
| 按 pool 更新 | `PostEntitlementsUpdateByPoolId`；`poolId` 常由上一包 search 响应解析 |
| details | `PostEntitlementsDetails`；请求体字段以 OpenAPI 为准 |

### 健壮性建议

- **Program 策略拒绝**（如某 `module` 不可编辑）时：可对「候选请求体」**循环尝试**（见 `ListP2515ModuleExclusiveUpdateBodies` 一类写法），仍失败则 **不写**入可复用上下文，后续变更类用例 **skip** 并说明原因。
- **手工覆盖**：环境变量指向的 JSON 文件应 **优先于** 自动生成的体，便于本地复现与 CI 稳定账号。

### 参考实现文件

- [`api-testcases/2026Q2_SP1/papi2515_helpers.py`](../../../api-testcases/2026Q2_SP1/papi2515_helpers.py)：`BuildP2515SandboxContext`、`RunP2515Attach2Scenario`
- [`api-testcases/2026Q2_SP1/conftest.py`](../../../api-testcases/2026Q2_SP1/conftest.py)：`P2515Sandbox` 及相关 fixture
