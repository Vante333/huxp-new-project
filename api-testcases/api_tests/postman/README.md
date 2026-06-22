# Postman / Apifox 导入

与 [Apifox：导入 Postman](https://docs.apifox.com/doc-5174528) 一致：使用 **Postman Collection v2.1** 的 JSON；`baseUrl` 等变量在 Postman 中由集合或环境提供，导入 Apifox 后对应到项目/环境中的「服务 / 前置 URL」与变量。

## 文件

| 文件 | 用途 |
|------|------|
| [`PAPI-2548-membership-extensions.postman_collection.json`](PAPI-2548-membership-extensions.postman_collection.json) | **主文件**：Postman / Apifox → **Import** → 选择本文件。内容与 [`tests/features/test_membership_extensions.py`](../tests/features/test_membership_extensions.py) / [`services/papi2548_service.py`](../services/papi2548_service.py) 对齐（文件夹 `01 Register`～`04 E2E` 对应各类 `Test*`）。 |
| [`GeneratePostmanCollectionPapi2548.py`](GeneratePostmanCollectionPapi2548.py) | **生成器**：修改后执行 `python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2548.py` 重新写出上方 JSON。 |
| [`PAPI-2548-sandbox.postman_environment.json`](PAPI-2548-sandbox.postman_environment.json) | **推荐**：Postman / Apifox → Import → Environment；选中后提供 ``ProgramID``、``clientId``、``secret``（及可选 ``baseUrl``），对齐 ``DP_PROGRAM_ID`` / ``DP_CLIENT_ID`` / ``DP_CLIENT_SECRET`` |
| [`PAPI-2515-cross-module-entitlements.postman_collection.json`](PAPI-2515-cross-module-entitlements.postman_collection.json) | **PAPI-2515**：与 [`PAPI-2548-membership-extensions.postman_collection.json`](PAPI-2548-membership-extensions.postman_collection.json) 同构——多文件夹对齐 [`tests/features/test_cross_module_entitlements.py`](../tests/features/test_cross_module_entitlements.py)；公共 JS 内联于 [`GeneratePostmanCollectionPapi2515.py`](GeneratePostmanCollectionPapi2515.py) 的 `BuildP2515JsHelpersLines()`（与 2548 的 `BuildHelpersJsLines()` 同模式）。 |
| [`GeneratePostmanCollectionPapi2515.py`](GeneratePostmanCollectionPapi2515.py) | 运行后写出上方 PAPI-2515 集合 JSON。 |
| [`LocalOffer-ePass-P0-e2e-core.postman_collection.json`](LocalOffer-ePass-P0-e2e-core.postman_collection.json) | **P0 E2E 核心** · ``resourceId``/``optionId`` 从 **Environment** 读取（见下方环境 JSON） |
| [`LocalOffer-ePass-sandbox.postman_environment.json`](LocalOffer-ePass-sandbox.postman_environment.json) | **推荐** · Local Offer ePass 环境变量（``ProgramID``、``clientId``、``secret``、``resourceId``、``optionId``） |
| [`LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json`](LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json) | **生成** · 「P1 E2E (pytest-sync)」— 仅三条主链路 E2E |
| [`LocalOffer-ePass-P1-e2e-pytest-sync.apifox-2.7.43-import.json`](LocalOffer-ePass-P1-e2e-pytest-sync.apifox-2.7.43-import.json) | **可选** · P1 的 Apifox **导入 → Apifox** |
| [`LocalOffer-ePass-full-pytest-sync.postman_collection.json`](LocalOffer-ePass-full-pytest-sync.postman_collection.json) | **生成** · Full — E2E + 分模块**可运行** HTTP 步骤（非全部 pytest 用例） |
| [`LocalOffer-ePass-full-pytest-sync.apifox-2.7.43-import.json`](LocalOffer-ePass-full-pytest-sync.apifox-2.7.43-import.json) | **可选** · Full 的 Apifox 导入 |
| [`GeneratePostmanCollectionLocalOfferEpass.py`](GeneratePostmanCollectionLocalOfferEpass.py) | 写出 P1 两个 JSON；**不修改** P0 |
| [`GeneratePostmanCollectionLocalOfferEpassFull.py`](GeneratePostmanCollectionLocalOfferEpassFull.py) | 写出 Full 两个 JSON；**不修改** P0 |
| [`LocalOffer-ePass-P1-apifox-export-from-pytest.md`](LocalOffer-ePass-P1-apifox-export-from-pytest.md) | P1 步骤 ↔ pytest ↔ 后置脚本索引（``E01-S*`` / ``E02-S*`` / ``E03-S*``） |
| [`Esim-ePass-P0-e2e-core.postman_collection.json`](Esim-ePass-P0-e2e-core.postman_collection.json) | **主文件（Postman v2.1）** · eSIM P0 E2E；对齐 [`test_historical_epass_esim.py`](../tests/features/test_historical_epass_esim.py) 三条 `RunHistoricalEpass*MainE2EScenario(catalog_label='esim')` |
| [`GeneratePostmanCollectionEsimEpass.py`](GeneratePostmanCollectionEsimEpass.py) | 运行后写出上方 `Esim-ePass-P0-e2e-core.postman_collection.json`（仅一个 JSON） |
| [`Fitness-ePass-P0-e2e-core.postman_collection.json`](Fitness-ePass-P0-e2e-core.postman_collection.json) | **主文件（Postman v2.1）** · fitness P0 E2E；对齐 ``test_historical_epass_regression.py`` fitness 的 ``RunHistoricalEpass*MainE2EScenario(catalog_label='fitness')`` |
| [`GeneratePostmanCollectionFitnessEpass.py`](GeneratePostmanCollectionFitnessEpass.py) | 运行后写出上方 `Fitness-ePass-P0-e2e-core.postman_collection.json` |
| [`Lounge-ePass-P0-e2e-core.postman_collection.json`](Lounge-ePass-P0-e2e-core.postman_collection.json) | **主文件（Postman v2.1）** · lounge P0 E2E；对齐 ``test_historical_epass_regression.py`` lounge 的 ``RunHistoricalEpass*MainE2EScenario(catalog_label='lounge')`` |
| [`GeneratePostmanCollectionLoungeEpass.py`](GeneratePostmanCollectionLoungeEpass.py) | 运行后写出上方 `Lounge-ePass-P0-e2e-core.postman_collection.json` |
| [`FastTrack-ePass-P0-e2e-core.postman_collection.json`](FastTrack-ePass-P0-e2e-core.postman_collection.json) | **主文件（Postman v2.1）** · fastTrack P0 E2E；对齐 [`test_historical_epass_fasttrack.py`](../tests/features/test_historical_epass_fasttrack.py) 三条 `RunHistoricalEpass*MainE2EScenario(catalog_label='fastTrack')` |
| [`GeneratePostmanCollectionFastTrackEpass.py`](GeneratePostmanCollectionFastTrackEpass.py) | 运行后写出上方 `FastTrack-ePass-P0-e2e-core.postman_collection.json`；可由 [`_build_fasttrack_from_lounge.py`](_build_fasttrack_from_lounge.py) 从 lounge 生成器派生 |
| [`PAPI-2722-FastTrack-PII-P1.postman_collection.json`](PAPI-2722-FastTrack-PII-P1.postman_collection.json) | **PAPI-2722** · FT BOSS PII（全部使用人·无航班号）：资源详情 + 三接口各 6 负向 + 3 正向 |
| [`GeneratePostmanCollectionPapi2722FastTrackPii.py`](GeneratePostmanCollectionPapi2722FastTrackPii.py) | 运行后写出上方 PAPI-2722 FT PII 集合 JSON |
| [`PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json`](PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json) | **PAPI-2839** · FT ``prebookingRequiredInfo`` + ``passengers[]`` 姓名正则 ``^[A-Za-z ]+$``：三接口各 7+5 步 |
| [`GeneratePostmanCollectionPapi2839.py`](GeneratePostmanCollectionPapi2839.py) | 运行后写出上方 PAPI-2839 FT 姓名正则集合 JSON |
| [`PAPI-2839-Lounge-NameRegex-Regression-P1.postman_collection.json`](PAPI-2839-Lounge-NameRegex-Regression-P1.postman_collection.json) | **PAPI-2839 回归** · Lounge 三接口各 1 条正向下单（FT 非法样本 · Lounge 正则 ``^[A-Za-z -]+$`` 仍应成功） |
| [`GeneratePostmanCollectionPapi2839LoungeRegression.py`](GeneratePostmanCollectionPapi2839LoungeRegression.py) | 运行后写出上方 PAPI-2839 Lounge 品类隔离回归集合 JSON |
| [`Lounge-ePass-P0-e2e-core-v1.postman_collection.json`](Lounge-ePass-P0-e2e-core-v1.postman_collection.json) | **主文件（Postman v2.1）** · lounge P0 E2E · **API v1 路径**（``/v1/orders/...`` 等） |
| [`GeneratePostmanCollectionLoungeEpassV1.py`](GeneratePostmanCollectionLoungeEpassV1.py) | 运行后写出上方 v1 路径集合 JSON |
| [`Resource-Details-Scan.postman_collection.json`](Resource-Details-Scan.postman_collection.json) | **Resource 全量扫描**：module=1 断言 ``prebookingPolicy.prebookingRequiredInfo=[1,2]``（en-US / 26 语种）；module 2/3/4/6/7/8/11 详情 ``code=0``（en-US）；后置脚本 ``pm.sendRequest`` 分页扫描 |
| [`Resource-Details-Scan-sandbox.postman_environment.json`](Resource-Details-Scan-sandbox.postman_environment.json) | 对齐 ``DP_MEMBERSHIP_*``（Program ``1919256841868288``）；填写 ``ProgramID`` / ``clientId`` / ``secret`` |
| [`GeneratePostmanCollectionResourceDetailsScan.py`](GeneratePostmanCollectionResourceDetailsScan.py) | 运行后写出上方 Resource Details Scan 集合与环境 JSON |

## 变量与自动化（`DP_*`）对应

| Postman（集合或环境） | 仓库 `env/.env.*` / 根目录 `.env` |
|----------------------|-----------------------------------|
| `baseUrl` | `DP_BASE_URL` |
| `ProgramID` | `DP_PROGRAM_ID` |
| `clientId` | `DP_CLIENT_ID` |
| `secret` | `DP_CLIENT_SECRET` |

**PAPI-2548**：凭据三项 **`ProgramID` / `clientId` / `secret` 仅放在 Environment**（见 ``PAPI-2548-sandbox.postman_environment.json``），集合内不再定义；请求头 `X-Program-ID: {{ProgramID}}`，鉴权 body `secret: {{secret}}`。其余 **`accessToken`**、**`membershipId`** 等仍为集合变量。`fakeMembershipId` 用于「非法 membershipId」请求（默认占位长数字，可改为不存在的 id）。多步场景还会写入 **`u07aExtNorm`**、**`u03bExtNorm`**、**`e3patchNorm`**（JSON 字符串，供后续请求比对 extensions）。

**Local Offer ePass**：**Environment** 填 `ProgramID`/`clientId`/`secret`/`resourceId`/`optionId`（对齐 `DP_EPASS_*` 与 `DP_LO_EPASS_RESOURCE_ID`/`DP_LO_EPASS_OPTION_ID`，见 `env/.env.local-offer.example` 与 ``LocalOffer-ePass-sandbox.postman_environment.json``）；断言用 `pm.variables.get` 读环境值，**不会**从响应回写 `resourceId`/`optionId` 到集合变量。可选 `x-version`（canary）。**P0 核心**运行生成器时会同步 patch 内嵌 JS（``PatchP0CollectionResourceIdOptionIdEnv``）。**P1 / Full (pytest-sync)** 请求名统一为 **目的前置**：`【目的】| 步骤ID | METHOD /path`（由 `PurposeName()` / `StepSpec.purpose` 生成，便于 Apifox 列表扫读断言意图）。`POST /v2/orders/ePasses/search` **不要**传 `module`。

**eSIM ePass（tc-P0）**：鉴权同上；集合变量 `epassModule=8`、`otherModule=11`；**eSIM 专用** `esimResourceId`/`esimOptionId`（对齐 `DP_HIST_EPASS_ESIM_RESOURCE_ID` / `DP_HIST_EPASS_ESIM_OPTION_ID`，默认 `GR0005901` / `SKU-GS0010955`，见 `env/.env.historical-epass.example`）。与 Local Offer 的 `resourceId`/`optionId` 分离，可同时维护两套网点。E02/E03 使用 `POST /v2/resources/options/prebookings/availability`（body `module=8`）。路径为 `/v2/orders/esims/ePasses`（及 `/prebooking`、`/bundle`）。

**fitness ePass（tc-P0）**：鉴权同上；`epassModule=7`、`otherModule=11`；**fitness 专用** `fitnessResourceId`（对齐 `DP_HIST_EPASS_FITNESS_RESOURCE_ID`，默认 `GR0000308`）。E02/E03 先 `GET /v2/resources/fitness/{resourceId}/schedule` 写入 `fitnessOptionId` 与 `prebookingDate`，再 `POST /v2/resources/options/prebookings/availability`（`module=7`），预约/bundle 的 `extra` 含 `prebookingRequiredInfo` + `optionId`。路径为 `/v2/orders/fitness/ePasses`（及 `/prebooking`、`/bundle`）。请求名格式 **`【目的】| 步骤号 | METHOD 路径`**（`PurposeName()`，与 Local Offer P1 pytest-sync 一致）。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionFitnessEpass.py`。

**lounge ePass（tc-P0）**：鉴权同上；`epassModule=1`、`otherModule=11`；**lounge 专用** `loungeResourceId`（对齐 `DP_HIST_EPASS_LOUNGE_RESOURCE_ID`，默认 `N00012`）。E02/E03 使用 **经典可用性** `POST /v2/resources/prebookings/availability`（**无 optionId**）；`prebookingDate` 由可用性步骤 Apifox 表达式 `{{$date.now|addDays(10)|format('yyyy-MM-dd')}}T10:30` 同步。预约/bundle 的 `extra` 含 `prebookingRequiredInfo` + `prebookingToken`（无 `optionId`）。路径为 `/v2/orders/lounges/ePasses`（及 `/prebooking`、`/bundle`）。**v1 网关**：另导入 `Lounge-ePass-P0-e2e-core-v1.postman_collection.json`（路径前缀 `/v1/`；**不含** `extra.ePassStatus` 断言，因 v1 响应无该字段）；重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionLoungeEpassV1.py`。v2 重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionLoungeEpass.py`。

**fastTrack ePass（tc-P0）**：鉴权同上；`epassModule=2`、`otherModule=11`；**fastTrack 专用** `fastTrackResourceId`（对齐 `DP_HIST_EPASS_FASTTRACK_RESOURCE_ID`，默认 `C10826`）。响应 **`category`**：MS 创建/search 与 usage 预约单均为 **2**（lounge MS 为 3）。E02/E03 使用 **经典可用性** `POST /v2/resources/prebookings/availability`（与 lounge 同模式，**无 optionId**）；可用性 Tests 写入 `fastTrackAdultCount`/`fastTrackChildCount`（默认 2/0）。**E02-S03 / E03-S02** Pre-request 调 `ftSyncPrebookingPassengersBody()` 按人数生成 `passengers`（默认 **Auto Smith** lead + **Alex Jones**），Tests 含 `ftAssertPrebookingPassengersShape`；**`usedUsages` 断言仍为 1**（≠ 乘客人数）。预约/bundle 的 `extra` 在 lounge 基础上增加 **`prebookingRequiredInfo`**（须与 lead passenger 姓名一致，见 `500.051.017`）与 **`passengers`**（`passengersType` + `leadPassenger`，姓名 `^[A-Za-z ]+$`）；**PAPI-2722 无航班号场景不传 `transportNumber`**。路径为 `/v2/orders/fastTrack/ePasses`（及 `/prebooking`、`/bundle`）。细则见 `.cursor/rules/fasttrack-epass-prebooking-patterns.mdc`。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionFastTrackEpass.py`。

**PAPI-2722 · FT PII（tc-p1）**：集合 `PAPI-2722-FastTrack-PII-P1.postman_collection.json`；`fastTrackResourceId=C10826`（BOSS：邮箱/姓名/电话、全部使用人、无航班号）。`P1-S01`：`GET /v2/resources/{resourceId}?module=2` 断言 `prebookingRequiredInfo=[1,2,3,4,5]` 不含 `6`。`passengers` 与 FastTrack P0 同构；`P1-S04`/`P1-S06`/`P1-S09` 各 6 步负向 + 1 步正向；**正向下单后 ``PATCH /v2/orders`` 取消**（Bundle 另取消 MS 购买单，含 N06 成功步）。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2722FastTrackPii.py`。

**PAPI-2839 · FT 姓名正则（tc-p1）**：集合 `PAPI-2839-FastTrack-NameRegex-P1.postman_collection.json`；**仅 FastTrack**（``^[A-Za-z ]+$``）。遵循 ``fasttrack-epass-prebooking-patterns``（可用性 → 下单 ``p39SyncPrebookingPassengersOnly`` + ``p39ApplyNameOverrides``）。**正向下单后 ``PATCH /v2/orders`` 取消**（Bundle 另取消 MS 购买单）。凭据放 **Environment**（``PAPI-2548-sandbox.postman_environment.json``）。`fastTrackResourceId=C10826`。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2839.py`。

**PAPI-2839 · Lounge 品类隔离回归（tc-p2）**：集合 `PAPI-2839-Lounge-NameRegex-Regression-P1.postman_collection.json`；三条正向下单验证 Lounge 不受 FT 正则影响：`lounges/ePasses/prebooking`（``Jean-Pierre``）、`lounges/ePasses/bundle`（``Mary-Jane``）、`lounges/memberships/prebooking`（``Anne-Marie``）；下单后 ``PATCH /v2/orders`` 取消（Bundle 另取消 MS 购买单）。Lounge 正则 ``^[A-Za-z -]+$``；`loungeResourceId` 默认 `N00012`。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionPapi2839LoungeRegression.py`。

**Resource Details · 全量扫描**：集合 `Resource-Details-Scan.postman_collection.json`；环境 `Resource-Details-Scan-sandbox.postman_environment.json`（``DP_MEMBERSHIP_PROGRAM_ID`` / ``DP_MEMBERSHIP_CLIENT_ID`` / ``DP_MEMBERSHIP_CLIENT_SECRET``）。先 **Auth**，再跑 ``SCAN-M1-EN`` / ``SCAN-M1-I18N`` 或各 module 的 ``SCAN-M*``。全量扫描耗时较长；集合变量 ``scanMaxDetails=10`` 可抽样。重新生成：`python api-testcases/api_tests/postman/GeneratePostmanCollectionResourceDetailsScan.py`。

**PAPI-2515**：E2E 中 `p2515_pool_plan_json` 在 **[S04]** 写入；**[S05]** 主请求打 `plan[0]`，其余条在后置脚本用 **`pm.sendRequest`** 串行发出。内联请求头 **优先克隆当前步骤 `pm.request` 里已解析的头**（与 Apifox 实际发出的主请求一致）；否则用 **`pm.variables` / `replaceIn` / 集合→环境→全局`** 拼 `Authorization`、`X-Program-ID`（缓解 `201.000.001 invalid secret`）。跳转 **[S06]** 优先 **`pm.execution.setNextRequest`**。若两者皆无则内联两次 search，可取消勾选 [S06]/[S07] 以免重复。若 Apifox 有 `setNextRequest` 但不跳到 S06，可在集合/环境设 **`DP_P2515_FORCE_INLINE_TAIL=1`**（或 **`P2515_FORCE_INLINE_TAIL`**）强制内联 S06/S07，并同样取消勾选 [S06]/[S07]。仅 **[S05]** 按池串行（``plan[1..]``）的 **`pm.sendRequest`** 需要打印入参/出参时，设 **`DP_P2515_VERBOSE_SEND_IO=1`**（或 **`P2515_VERBOSE_SEND_IO`**），在运行器 **控制台** 查看；内联 S06/S07 不打印。`probeMembershipId` 对齐 `DP_P2515_PROBE_MEMBERSHIP_ID`。

## 导出 Postman：测试目的前置命名（Local Offer 等 pytest-sync 集合）

**原则**：请求在 Apifox/Postman 列表里先让人看懂「这一步在验证什么」，再看到步骤号与 HTTP 信息。不要再用 `S02 POST prebooking（无效 token）` 这类「动作在前、目的在后」的写法。

### 展示名格式

```
【测试目的（中文）】| 步骤ID | METHOD /path简写
```

示例：

| 旧写法（避免） | 新写法（推荐） |
|----------------|----------------|
| `S02 POST prebooking（无效 token）` | `【负向：无效 prebookingToken 预约】\| S02 \| POST /ePasses/prebooking` |
| `E02-S03 POST /v2/orders/.../prebooking` | `【预约下单成功（usage 单）】\| E02-S03 \| POST /ePasses/prebooking` |

- **测试目的**：一句话业务语义（正向/负向、关键对象），与 pytest 用例意图一致，可对照 `testcases/.../自动化用例与pytest对应表.md`。
- **步骤ID**：E2E 用 `E01-S01`；分模块用 `S01`；鉴权用 `Auth`。
- **path 简写**：只保留路径末段或关键段（如 `/localOffers/ePasses`），不必写完整 `https://...`。

### 生成器里怎么写

| 集合 | 生成器 | 写法 |
|------|--------|------|
| P1 E2E | `GeneratePostmanCollectionLocalOfferEpass.py` | `RequestItem(..., name=PurposeName("创建 Local Offer ePass（MS 购买单）", "E01-S01", "POST", "/localOffers/ePasses"))` |
| Full 分模块 | `GeneratePostmanCollectionLocalOfferEpassFull.py` | 辅助函数必填 `purpose=`，如 `_CreateEpassStep("S01", purpose="创建 ePass", ...)`；内联步骤用 `StepSpec(purpose="...", step_id="S02", method="POST", url_path="...", path_hint="...")` |

`PurposeName()` 定义在 `GeneratePostmanCollectionLocalOfferEpass.py`；Full 通过 `StepSpec` + `_DisplayName()` 复用。

### 导出命令（仓库根目录，PowerShell）

```powershell
python api-testcases/api_tests/postman/GeneratePostmanCollectionLocalOfferEpass.py
python api-testcases/api_tests/postman/GeneratePostmanCollectionLocalOfferEpassFull.py
```

产出：`LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json`、`LocalOffer-ePass-full-pytest-sync.postman_collection.json`（及同名 `.apifox-2.7.43-import.json`）。**勿**用生成器覆盖手工 **P0 E2E 核心**。

### 导入注意

- Apifox：**重新导入**最新 JSON，避免沿用旧集合缓存。
- 改断言或步骤后：先改生成器里的 `purpose` / `test_lines`，再跑上述命令重写 JSON；权威执行仍以 **pytest + Allure** 为准。

### Agent Skill（自动遵循）

Cursor 在 Postman 导出、集合命名、断言步骤难读等场景会读取 **`.cursor/skills/api-testcase-pack/postman-purpose-first-naming.md`**（主 Skill 内链）；新建 `GeneratePostmanCollection*.py` 时默认按本节格式实现。

## Full 集合范围（未导出的 pytest 用例）

**Full 集合只包含能稳定用 HTTP 步骤表达的用例**；不再输出「说明」占位请求或空文件夹。

完整 pytest 清单与状态（✅/⏭/👤/📝）见：

[`testcases/2026Q2_SP3/LocalOffer订单相关-epass-自动化用例与pytest对应表.md`](../../../testcases/2026Q2_SP3/LocalOffer订单相关-epass-自动化用例与pytest对应表.md)

### 整模块不导出

| 模块 | 原因 |
|------|------|
| **M04** `test_prebooking_restrictions.py` | 双模式 availability + 限制造数，仅 pytest |
| **M11** `test_sandbox_redemption_url_outlets.py` | 需沙箱专用 `DP_LO_EPASS_SANDBOX_*`，完整链仅 pytest |

### 部分用例不导出（同模块其余步骤仍在 Full）

| pytest（节选） | 原因 |
|----------------|------|
| `test_prebooking_token.py::…_TokenResourceMismatch_Rejected` | 限制 resourceIds + 另一网点 token |
| `test_prebooking_token.py::…_MembershipIdToken_Rejected` | memberships 注册与权益链 |
| `test_prebooking_entitlements.py::…_GuestCountVsAvailableUsages` 等 | 参数化 / 矩阵 / 专用 ePass ID |
| `test_retrieve.py::…_ExtendedFields` / `…_Module8_*` | 依赖 E2E 链或扩展字段断言 |
| `test_bundle.py::…_CompensationAfterPrebookingFailure_Manual` | `@pytest.mark.manual` |
| `test_bundle_token.py::…_MembershipIdToken_Rejected` | memberships 场景 |
| `test_saas_manual_checkpoint.py`（除 Create 无限制一条外） | 预约/Bundle SaaS 参数化 |
| `test_availability.py::…_AbnormalMembershipOrEpass_Manual` | manual |

跑全量自动化请用 pytest（见对应表「运行」一节），不要指望 Full Postman 覆盖上表。

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

1. 导入并选中 **`PAPI-2548-sandbox.postman_environment.json`**，填写 **`ProgramID`**、**`clientId`**、**`secret`**（及按需修改 **`baseUrl`**）。
2. 先跑 **00 Auth → POST /v2/auth/token**（Tests 写入 `accessToken`）。
3. 按场景选择文件夹内请求：多数 **Register** 成功后会写入 `membershipId`；**03 Extensions** 中多段流程已用 `U0`/`U0b`… 标明前置注册，请按名称顺序执行。沙箱默认 **PATCH** `/v2/memberships/extensions`；仅支持 **POST** 时用 **U09** 或自建 POST 副本。

## curl 与 Postman 对照（示例，勿粘贴真实 secret）

取 token（路径与集合「1」一致，仅作对照）：

```bash
curl -sS -X POST "https://developer-sandbox.dragonpass.com/api/v2/auth/token" \
  -H "X-Program-ID: <ProgramID>" \
  -H "Content-Type: application/json" \
  -d "{\"clientId\":\"<clientId>\",\"secret\":\"<secret>\"}"
```

勿在取 token 请求上使用 `Authorization: undefined`；与 [`api-testcases/api_tests/README.md`](../README.md) 中说明一致。

## 注册邮箱格式

集合内 `POST /v2/memberships` 的 `email` 统一为 **`p2548_{{$timestamp}}@yahoo.com.cn`**（时间戳较短，避免 `{{$guid}}` 过长；域名 `yahoo.com.cn`）。修改模板请编辑 `GeneratePostmanCollectionPapi2548.py` 中的 `REGISTER_EMAIL_TEMPLATE` 并重新运行生成脚本。
