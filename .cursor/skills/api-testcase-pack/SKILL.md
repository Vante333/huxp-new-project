---
name: api-testcase-pack
description: >-
  按本仓库金样例搭建 pytest 接口自动化套件：分层环境变量、Allure 报告、Postman Collection v2.1
  生成器与可导入 JSON、团队协作文档；**优先会话级自动造数**（再用手工 ID/JSON 覆盖）。当用户消息出现
  「接口自动化」「API 自动化」「自动化」（且与 API、pytest、Allure、Postman、api-testcases
  或本仓库接口测试相关）、「api-testcases」「Allure」「Postman」「接口测试自动化」、**显式「Postman 导出」
  「生成 collection」「导出 Postman」「Postman 集合 JSON」** 或按
  PAPI-2548/PAPI-2515/2026Q2_SP1 模式新建/扩展套件、与 testcases 用例表对齐时使用；Agent 应先读取本
  Skill 再产出目录结构与命令，与 api-testcases/api_tests 主线一致。
---

# 接口自动化套件（api-testcase-pack）

## 当前主线

`api-testcases/api_tests/` 是接口自动化长期主线目录；后续新增需求、大改、公共断言、回归分层和 Postman 生成器默认维护在该目录。`api-testcases/2026Q2_SP1/` 保留为历史金样例与迁移参考，修复历史样例时应判断是否需要同步回 `api_tests/`，避免同一接口能力出现两份真相源。

## 触发条件

用户只要提到 **接口自动化**，或在与 API/pytest/Allure/Postman/`api-testcases`/本仓库接口测试相关的语境下提到 **自动化**，或上列 description 中的其它触发词，即应 **先读取并遵循本 Skill**，再生成或修改代码与文档，使结构与长期主线 `api-testcases/api_tests/` 对齐。

以下表述**显式触发** Postman/集合相关流程（含 2548/2515 形态、`GeneratePostmanCollection*.py`）：**「Postman 导出」**、**「生成 collection」**、**「导出 Postman」**、**「Postman 集合 JSON」**、**「生成 Postman」**。

## 主线样例（必读）

先阅读并对齐长期主线目录 [`api-testcases/api_tests/`](../../../api-testcases/api_tests/)；必要时再对照历史样例 [`api-testcases/2026Q2_SP1/`](../../../api-testcases/2026Q2_SP1/)：

| 文件/目录 | 作用 |
|-----------|------|
| [`README.md`](../../../api-testcases/api_tests/README.md) | 环境变量表、运行命令、回归分层、长期主线约定 |
| [`conftest.py`](../../../api-testcases/api_tests/conftest.py) | 分层 `.env`、`DP_PROFILE`、`pytest` markers、Allure fixture |
| [`pytest.ini`](../../../api-testcases/api_tests/pytest.ini) | `addopts = --clean-alluredir`（与 `--alluredir` 配合防结果翻倍） |
| [`services/`](../../../api-testcases/api_tests/services/) | 业务语义、断言、payload 构造与结果处理 |
| [`scenarios/`](../../../api-testcases/api_tests/scenarios/) | 主链路编排入口，主 E2E 只调用 `Run...MainE2EScenario` |
| [`tests/`](../../../api-testcases/api_tests/tests/) | `contract` / `features` / `regression` / `smoke` 分层用例 |
| [`postman/`](../../../api-testcases/api_tests/postman/) | 生成脚本、`.postman_collection.json`、环境 JSON、`README.md` |
| [`api-main-call-chains.md`](../../../api-testcases/docs/api-main-call-chains.md) | Membership / EPass / ESIM 主调用链、字段流转、`{module}` 变体；新增或扩展接口自动化主链路前必读 |

更细的命令与模板见同目录 [`reference.md`](reference.md)（含 **Apifox 链路与 pytest 步骤对照**）。

## 主链路与单一编排函数（新建/扩展套件必选风格）

**后续凡新增或扩展**需求专属 `*_helpers.py`，与金样例 **PAPI-2548 / PAPI-2515** 保持一致，便于人与 Agent 快速掌握接口顺序、且避免重复维护。

1. **模块 docstring（简体中文）**：在契约、环境变量之外，增加 **主链路** 小节——按 **真实 HTTP 先后顺序** 列出关键步骤（方法 + path 或统一描述）；注明 **鉴权**（如 `POST /v2/auth/token`）是否由用例 **`Token` fixture** 提供而不在编排队列内；注明 **Allure `S01/S02/…`** 由 **`AllureHttpScenarioSteps.Next`** 按每次请求递增，分支或可变步数时序列码会平移、勿死记固定 `Sxx`；若有「只读探测 / 单步用例」与「写侧 E2E」之分，在 docstring 中分开说明。
2. **单一编排入口**：为产品 **附件链或主场景 E2E** 提供 **`Run<需求缩写>MainE2EScenario`**（PascalCase），参数至少包含 **`token`**、**`steps: AllureHttpScenarioSteps`**，按需增加 **`flags`**、沙箱上下文等；**对应主 E2E 的 `test_*` 函数体内仅调用该编排函数**，不在测试文件再展开一长串 HTTP。
3. **辅助约定**：多处复用的 **`pytest.skip`** 条件封装为 **`Require…OrSkip`** 并放在 helpers；与 `RequestWithAllure` 配套的 **`step_code` / `step_title`** 可在 helpers 内用 **`_HttpStepKw(steps, brief)`**（与现有一致）。
4. **对照实现**：[`RunPapi2548MainE2EScenario`](../../../api-testcases/api_tests/scenarios/papi2548_scenarios.py)、[`RunP2515MainE2EScenario`](../../../api-testcases/api_tests/scenarios/papi2515_scenarios.py)；测试侧见 [`test_membership_extensions.py`](../../../api-testcases/api_tests/tests/features/test_membership_extensions.py)、[`test_cross_module_entitlements.py`](../../../api-testcases/api_tests/tests/features/test_cross_module_entitlements.py) 中 E2E 用例。

**边界**：负向、边界、单接口用例仍可 **直接** 调用原子级 `Post*` / `Assert*`；不必为每条用例各写一个编排函数，**仅主链路/附件链**强制单一入口。

## 跨迭代维护与历史回归

同一接口在**不同迭代 / 不同 Jira 需求**下重复演进时，默认目标不是“按迭代复制一套自动化”，而是以**接口能力**为长期资产持续扩展：复用既有 HTTP 封装、公共断言、主链路编排与用例映射，在其上**增量补测试**并**保留历史回归**。

1. **优先复用同一 `*_helpers.py`**：同一接口跨迭代新增能力时，优先在既有 helpers 中补 **`Post*` / `Assert*` / `Run…MainE2EScenario`** 或新增独立编排函数；**不要**仅因迭代变化就平移复制一份 `*_helpers_v2.py` / `*_helpers_<迭代>.py`。若目录仍按 `api-testcases/<迭代>/` 组织，逻辑上也应优先复用同一接口能力设计，避免双份真相源。
2. **区分“新增需求验证”与“历史最小回归”**：新需求接入时，除新增对应用例外，至少保留该接口的最小回归集合，建议按语义分层维护：**`contract`**（结构/字段/核心语义）、**`smoke`**（老主流程/关键成功链路）、**`regression`**（历史缺陷与关键业务回归点）。新增需求不应替代这三类旧验证。
3. **兼容非破坏性新增字段**：若接口只是**新增字段 / 新增节点 / 放宽返回结构**，历史用例应优先断言其原始需求关心的**核心字段、核心结构与关键语义**，避免一味做“全量响应完全相等”导致兼容新增误报失败；新增字段、分支或新语义由**新需求用例**单独覆盖。
4. **新增需求优先补公共能力与独立回归点**：当需求影响同一接口时，优先判断应补在哪一层：公共断言、主链路编排、独立 doc gap / 对拍 / 边界回归用例。**不要**为了让新需求通过而直接改写旧用例语义；旧用例继续守护旧需求，新用例负责验证新行为。

**对照主线样例**：

- [`scenarios/papi2515_scenarios.py`](../../../api-testcases/api_tests/scenarios/papi2515_scenarios.py) 中 **`RunP2515MainE2EScenario`** 体现“主链路单一入口，后续需求在 services/scenarios 中持续演进”的模式。
- [`tests/features/test_cross_module_entitlements.py`](../../../api-testcases/api_tests/tests/features/test_cross_module_entitlements.py) 中主 E2E、doc gap、隔离回归分层组织，体现“新增需求验证”与“历史/补缺回归”并存，而非互相覆盖。

## PAPI-2515 排障（Agent 先读）

处理 **`summary` vs `pools` 四指标聚合（缺键按 0、任池 `-1` 则该指标为 `-1`）**、**两个 `entitlements/update` 混淆**、**断言失败后链路中断**、**Allure 断言与 HTTP 步骤同屏**、**脑图用例数 vs pytest 覆盖**、**`allure serve` 端口占用**、**与用户约定是否加环境开关**、**探测用例 Skipped / `DP_P2515_PROBE_MEMBERSHIP_ID` / `DP_P2515_INCLUDE_PROBE`、误以为 memberships+entitlements search 可无 ID 枚举会籍** 时，必须先读本 Skill 附属文档 **[`papi2515-crossmodule-troubleshooting.md`](./papi2515-crossmodule-troubleshooting.md)**（含 §0～§7），再改 `papi2515_helpers` / `papi2548_helpers` / E2E 或环境变量。

## 自动造数（优先于手工 ID）

新建或扩展套件时，**默认应能通过接口自动准备测试数据**，而不是把「固定会籍 ID」当作唯一入口。手工环境变量（如 `DP_*_MEMBERSHIP_ID`）或 JSON 文件路径用于 **覆盖 / 兜底 / 多环境复现**，须在套件 `README.md` 中说明开关与 **副作用**（例如是否会改写沙箱权益）。

### 顺序可变、能力同类

不同 Jira 需求的 **HTTP 调用顺序** 可以不同（以 Apifox 集合、用例附件或 OpenAPI 为准），但前置造数往往复用同一类 **基础接口族**（按需求裁剪，不必每条链路全用）：

| 能力 | 常见路径（示例） | 说明 |
|------|------------------|------|
| 鉴权 | `POST /v2/auth/token` | 与 `GetAccessToken`、分层 `DP_*` 一致 |
| 会籍创建 / 定位 | `POST /v2/memberships`、`POST /v2/memberships/search` | 注册新会籍或解析已有会籍 |
| 权益探测 | `POST /v2/entitlements/search` | 解析 `entitlements`、判断是否具备某类数据（如 crossModule） |
| 权益变更链（按需） | `POST /v2/entitlements/update`、`POST /v2/entitlements/{poolId}/update`、`POST /v2/entitlements/details` | **是否调用及先后顺序以需求为准**；用于把沙箱推到可断言状态 |

将 Apifox 中的多步顺序映射到 pytest 的写法见 [`reference.md`](reference.md) 中 **「自动造数与 Apifox 链路对照」**。

### pytest 落地形态（与金样例一致）

- 在 [`conftest.py`](../../../api-testcases/2026Q2_SP1/conftest.py) 使用 **session（或合适 scope）fixture** 执行造数链，返回 **不可变上下文**（如 `dataclass`：`P2515SandboxContext`）；用例通过 **细粒度 fixture**（如 `P2515CrossMembershipId`、`ResolveXxxOrSkip`）注入 `membershipId` 或请求体。
- 造数条件不满足时 **`pytest.skip`**，并写清依赖（Program 模板、权限、网关错误码等），避免假通过。
- 若需把「后续用例可复用的 update / pool 请求体」写入上下文，**仅在对应请求 HTTP 与业务均成功时** 再写入；失败时不得把失败请求体当作有效造数结果（参见金样例 `papi2515_helpers` 中附件链实现）。
- 提供 **显式关闭** 的环境变量（如 `DP_*_DISABLE_AUTOGEN`、`DP_*_SKIP_*_SCENARIO`），与「凭据不进仓库」同属协作约定，并在 README 列表中维护。

### 金样例：造数模式速查

| 模式 | 位置 | 说明 |
|------|------|------|
| 注册 + search **探测**读/写 | [`papi2548_helpers.py`](../../../api-testcases/2026Q2_SP1/papi2548_helpers.py)：`BuildSandboxFlags`、`ProbeExtensionCapabilities` | 会话级能力标志，供 skip/执行分支 |
| 注册 + search + **多步权益链** | [`papi2515_helpers.py`](../../../api-testcases/2026Q2_SP1/papi2515_helpers.py)：`BuildP2515SandboxContext`、`RunP2515Attach2Scenario` | 顺序可对齐 Apifox「附件」链路；步骤集合因需求而异 |
| fixture 挂载 | [`conftest.py`](../../../api-testcases/2026Q2_SP1/conftest.py)：`P2515Sandbox`、`P2515CrossMembershipId`、`P2515ProbeMembershipId` 等 | 会话造数与用例注入分离 |

## 权威与双轨

- **自动化与报告**：以 **pytest + Allure** 为权威；Postman/Apifox 用于联调、演示与导入共享。
- Postman Tests（JS）与 Python helpers **语义需对齐**；变更时同步修改两处，必要时用归一化/parity 小测校验（参见金样例中 `test_p2548_normalize_parity.py` 一类做法）。

## 工作流清单

复制并逐项勾选：

```
- [ ] 确定 Jira/需求编号，在 api-testcases/<迭代或前缀>/ 建套件目录
- [ ] pytest.ini：含 --clean-alluredir（与命令行 --alluredir 同用）
- [ ] conftest.py：仓库根 .env + env/.env.<profile>（DP_PROFILE），markers，Allure 相关 fixture
- [ ] *_helpers.py：HTTP 封装、RequestWithAllure、共享断言/归一化；错误路径处理完整；**模块 docstring 主链路** + **`Run…MainE2EScenario`**（主 E2E 仅调编排入口）；**可复用 `Assert*` 一律用 `papi2548_helpers._RunAllureAssertionStep` 包装**（见下节「Allure」）
- [ ] test_*.py：@allure.feature/story、ScenarioSteps、按需 skip/沙箱探测
- [ ] 套件 README.md：DP_* 表、PYTHONPATH（Windows）、pytest/allure 命令
- [ ] postman/Generate*.py → v2.1 Collection JSON（**2548/2515 形态**：多文件夹、`Build*JsHelpersLines` 内联于 .py、主链路对齐 `Run…MainE2EScenario`）；可选 *.postman_environment.json；postman/README.md（变量与 DP_* 映射、JS↔Python）；改毕运行 `python …/GeneratePostmanCollection*.py` 更新 JSON
- [ ] testcases/ 下维护「用例 ↔ pytest」对照表，并从套件 README 链到该表
- [ ] 同一接口新增需求时：确认**历史最小回归集**（至少 contract / smoke / regression）仍保留、仍可收集，并纳入本轮回归运行
- [ ] 造数：session/fixture 优先自动完成前置接口链；手工 DP_*_ID / JSON 文件为可选覆盖；README 写明开关与副作用（是否改沙箱数据）
```

## 硬性约定（与金样例一致）

### Allure

- 运行：`pytest ... --alluredir=<目录>`；查看：`allure serve <目录>`（需本机安装 Allure CLI）。
- 与 JSON 相关的附件优先用 **`text/plain`** 承载格式化内容，避免 Allure 2.x 对 `application/json` 预览空白。
- HTTP 步骤附件顺序以金样例 README 与 **`RequestWithAllure`** 为准。
- **可复用断言（Agent 生成 helpers 时默认执行）**：在 `papi*_helpers.py` 中新增或扩展 **对外 `Assert*`** 时，从 **`papi2548_helpers`** 导入 **`_RunAllureAssertionStep`**，按金样例模式编写：
  - **`def _Do() -> str`**：内放原断言逻辑；通过后 **`return`** 一两句中文摘要（写入 **`断言结果_*`** 可读附件）。
  - **`_RunAllureAssertionStep("步骤标题", _Do)`**：步骤标题建议带需求号前缀（如 `PAPI-xxxx: …`）。
  - **不要**在业务 helpers 里直接调用 **`_RecordAllureAssertionResult`**（由 `_RunAllureAssertionStep` 内部统一调用）；**不要**仅写裸 `assert` 而不包步骤——否则 Allure 报告中看不到断言痕迹。
  - 断言附件序号依赖套件 **`conftest.py`** 已具备的 **`ResetAllureAssertionAttachmentCounter`**（每用例复位）；与规则 **[`.cursor/rules/api-testcases-pytest-allure.mdc`](../../rules/api-testcases-pytest-allure.mdc)** 一致。
- **断言嵌在某一 HTTP 步骤内**：在该次请求的 **`after_response`** 里调用 `Assert*`（见 `RequestWithAllure` 与 PAPI-2515 排障规则 §4）；否则断言步骤常与 `[Sxx]` 请求步骤**平级**，仍可见但层级不同。

### Postman（集合导出：与 PAPI-2548 / PAPI-2515 金样例对齐）

- 使用 **Collection v2.1**（`schema.getpostman.com/json/collection/v2.1.0/collection.json`）。
- 集合变量与仓库 `DP_*` / `env/.env.*` 对照写在 `postman/README.md`。

#### 复盘：常见诉求与易错点

| 现象 | 建议 |
|------|------|
| 只要「能导入的 JSON」却只做极少请求 | 金样例是**多文件夹**集合，**请求名对齐** `test_*.py` / 场景（如 2515 的 Probe、E2E、Doc gap），不是单条最小链。 |
| 需要 Apifox 可跑的断言 | 每个请求 **Tests** 内联 JS；导入 Apifox 后在「后置脚本」。可选：同目录 `*-apifox-export-from-pytest.md` 做用例与片段索引（见 `PAPI-2515-apifox-export-from-pytest.md`）。 |
| 公共 JS 单独建 `*.js` 再由生成器读取 | 与 **2548 不一致**；**唯一真相在生成器**内 **`Build*JsHelpersLines()`**（`js = r"""..."""` + `splitlines()`），与 [`GeneratePostmanCollectionPapi2548.py`](../../../api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py) 的 `BuildHelpersJsLines` **同构**。 |
| Postman 步骤少于 `Run…MainE2EScenario` | 按 helpers **模块 docstring 主链路**补全步骤（如 2515：**update 后再 search**、收尾多次 search）；多步用**集合变量**衔接。 |
| 注册 `firstName` / `lastName` 校验失败 | 部分网关**仅允许拉丁字母**（`A–Z`/`a–z`）；勿中文/数字/符号；标识放 `email` 等字段。 |
| 改 Python 断言后 Postman 未更新 | 同步改生成器内 JS 与各 `Lines_*`，再 **运行** `python postman/GeneratePostmanCollection*.py` 重写 JSON。 |

#### Agent 新建/更新 Postman 时的执行顺序

1. **对照模板**：[`GeneratePostmanCollectionPapi2548.py`](../../../api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py)（extensions）、[`GeneratePostmanCollectionPapi2515.py`](../../../api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2515.py)（crossModule）— 复用 **`Folder` / `RequestItem` / 头 / `Make*TestEvent`** 模式。
2. **内联 Helpers JS**：在 `GeneratePostmanCollection<需求>.py` 中实现 **`Build<需求>JsHelpersLines()`**，不要把仓库级 `*.js` 当作与 2548 并列的规范源（除非团队明文要求双轨）。
3. **顺序与命名**：文件夹与请求顺序对齐 **`Run…MainE2EScenario`** 与 **`test_*`**；`info.description` / `postman/README.md` 写明变量与 `DP_*`。
4. **产出物**：生成 `*.postman_collection.json`；可选环境 JSON；改完**务必执行生成脚本**提交更新后的 collection。

更细的字段级说明见 [`reference.md`](reference.md) 中 **Postman 生成器（2548/2515 形态）**。

### 协作与安全

- 凭据 **不提交**：真实值放 `env/.env.<profile>`（已 gitignore）；仓库只保留 `.env.example`、`env/.env.*.example`。
- 报告目录建议：`reports/<feature>-allure-results`（或团队统一路径），勿把含敏感信息的原始结果提交到公开分支。

## 代码风格

新增 Python 与**当前套件内文件、金样例**保持一致；pytest 钩子、`pytest_*` 函数名遵循 pytest 惯例。若项目另有 `.cursor/rules` 约定，与之对齐。
