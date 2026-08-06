> **放置与读取方式**：本文件位于 **`.cursor/skills/api-testcase-pack/`**，与 [`SKILL.md`](./SKILL.md) 中「Postman / Apifox 排障（Agent 先读）」互链。处理 **Postman Collection 生成器**、**Apifox 自动化运行卡顿/报错/永久 loading**、**fitness / historical ePass / Local Offer pytest-sync 集合** 时，Agent **先读本文件再改** `GeneratePostmanCollection*.py` 或让用户重新导入 JSON。

# Postman / Apifox 集合：Agent 自检与自助处理

**权威对照**：pytest + helpers 语义；Postman/Apifox 为联调与演示。变更断言后须 **改生成器 → 运行 `python …/GeneratePostmanCollection*.py` → 提醒用户 Apifox 重新导入**（勿只手改 JSON）。

**金样例生成器**：[`GeneratePostmanCollectionPapi2548.py`](../../../api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py)、[`GeneratePostmanCollectionLocalOfferEpass.py`](../../../api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpass.py)、[`GeneratePostmanCollectionFitnessEpass.py`](../../../api-testcases/api_tests/postman/generators/GeneratePostmanCollectionFitnessEpass.py)。

---

## 0. 自动排查决策树（Agent 先走此表）

| 用户现象 | 优先怀疑 | 首选动作 |
|----------|----------|----------|
| 后置脚本 `ReferenceError: fpXxx / epXxx is not defined` | helpers 未注入到 **该请求的 test**；或 **ep/fp 前缀混用** | 确认 `RequestItem` 的 `MakeTestEvent` 含 `Build*JsHelpersLines()`；Apifox **不要**仅依赖集合级 pre-request 给 test 提供函数；统一前缀（fitness 用 `fp*`） |
| 某步 **永久 loading**（0ms、运行中不结束） | `pm.test(fn, done)` + `pm.sendRequest` 异步；或 **setNextRequest 回跳同一步** + `setTimeout` | 改为 **同步 test**；重试用 **线性多步 PATCH**（E02-S07 → E02-S07-R2），成功时 **向前** `setNextRequest` skip 剩余重试步；**禁止** `done()` 未调用 |
| Apifox **整体很卡**、总耗时 ≫ 接口耗时 | 每步重复整份 helpers（JSON 膨胀）；或 pre-request **busy-wait**（`while (Date.now()-start<delay)`） | helpers 只注入 test（Apifox 兼容）；**取消** script 内长等待；若业务必须等：用 Apifox 运行器「步骤间隔」或 pytest `PatchCancelOrderWithRetry`，**不要**在集合里 sync 阻塞 15s/30s |
| 打开项目「自动化测试」长期 **骨架屏**；多人同项目复现，其他项目正常 | 项目初始化全量接口慢、重复加载，或 Electron 已取到数据但未重绘；**不等于场景脚本卡住** | 先走 §0.1：CLI 只读验证场景树 → 查客户端版本/内存 → 经用户同意干净重启 → 运行时测真实请求体与 pending → DOM 已完成但画面旧则强制重绘 |
| 切 main / AI 分支后越来越卡或客户端退出 | 旧分支请求未取消、重复加载、JS Heap 持续上涨 | 一次只切一个分支并等待稳定；记录 Heap；出现持续增长或崩溃立即停止连切，恢复 `working_branch`，按 §0.1 升级/上报客户端问题 |
| 同一步在列表出现 **多次**且都像「通过」 | 动态重试把「调度重跑」也记成 passed | 改用线性 R2/R3 步骤；或 test 里不要对「可重试」写 misleading pass |
| 取消返回 `Order cancellation failed. Please try again later.` | 沙箱时序；非脚本 bug | pytest：`PatchCancelOrderWithRetry` + sleep；Apifox：线性 PATCH 重试（无间隔）或用户手动重跑；**勿** sendRequest 循环 |
| schedule / 日期不对 | URL 仍用 `{{fitnessScheduleQuery}}` 等变量但 pre-request 未跑 | GET schedule 的 query 直接写 Apifox 表达式（见 §6） |
| HTTP 200 但断言失败 | Apifox「校验响应」与脚本重复；或 `pm.response.code` 缺失 | 业务成功用 `fpIsBusinessSuccess`；负向步关闭 Apifox 自带 HTTP 200 校验（见 Local Offer description） |
| 改生成器后用户仍报旧错 | 未重新导入 | 明确提示：**覆盖导入** `*.postman_collection.json` |
| Preview 误跑 Detail 断言 / `Invalid or unexpected token` | 环境 `order_api_stage` 未随 URL 更新；或脚本含 `?.`/`??`/特殊 Unicode | 用 [`prebooking-payment-apifox-assertions.md`](./prebooking-payment-apifox-assertions.md) 与 `tools/apifox_payment_assert_*.js`；前置按 URL 写 stage |
| `301.000.001` · X-Request-ID invalid / curl 头为 `X-Request-ID;` | Apifox 不展开 `{{$guid}}`，头值为空 | 用 `collection_builder_common.Lines_EnsureRequestIdHeader` / `JsExpr_FreshRequestId`；重跑生成器并重新导入或 CLI Push |

---

## 0.1 项目级骨架屏：自动诊断与恢复（不是步骤运行 loading）

### 先分类，禁止凭文件大小猜根因

同时满足以下条件时，按**项目级 UI loading**处理：

- 多人打开同一项目都卡，其他项目正常；
- main 与 AI 分支均可能卡；
- 左侧目录是骨架屏，而不是某个 HTTP 步骤显示「运行中」。

Agent **不得**把仓库 `*.postman_collection.json` 总大小直接当成 Apifox UI 响应体。必须测桌面端实际请求；本次实测中，本地集合总量很大，但 `test-scenario/tree-list` 只有约 32KB，真正慢的是约 6.6MB 的 `/api-details`。

### 自动处置顺序

1. **CLI 只读确认服务端资源可读**（不改场景）：

   ```powershell
   apifox branch list --project <projectId> --type all
   apifox test-scenario list --project <projectId>
   apifox test-scenario list --project <projectId> --branch <workingBranch>
   apifox folder list --project <projectId> --type test-scenario
   apifox folder list --project <projectId> --type test-scenario --branch <workingBranch>
   ```

   再抽样 `test-scenario get`，记录实际响应耗时、字节数、步骤数、重复 ID 与 folder 引用。列表/详情正常时，勿再泛称「服务端场景接口挂了」。

2. **检查客户端版本与内存**：

   ```powershell
   $p = Get-Process | Where-Object { $_.ProcessName -match 'Apifox' }
   [pscustomobject]@{
     Processes = $p.Count
     WorkingSetGB = [math]::Round((($p | Measure-Object WorkingSet64 -Sum).Sum) / 1GB, 2)
   }
   ```

   多 Renderer、总内存数 GB 且持续上涨时，优先怀疑 Electron 状态泄漏。**强制结束客户端会丢失 UI 未保存修改，必须先征得用户同意**；不得自动杀进程。

3. **用户同意后干净重启**：结束所有客户端/Agent 进程再启动，勿只关窗口。升级版本后要重新核对实际进程 `FileVersion`，不能只相信安装器提示。

4. **仍卡时抓桌面端真实网络证据**：经用户同意，用临时 `--remote-debugging-port=<port>` 启动，监听项目 Renderer 的 CDP `Network.*` / `Runtime.*`：
   - 记录每个请求的 TTFB、完成耗时、编码后大小、失败与真正 pending；
   - 单独观察 `/test-scenario/tree-list` 与 `/api-details`；
   - pending 集合必须在 `loadingFinished` / `loadingFailed` 时删除，禁止把「已完成但未从 Map 删除」误报为 pending；
   - 调试端口仅临时使用；完全退出客户端后即结束。

5. **区分数据加载与窗口重绘**：
   - `tree-list` 已 200、DOM 中 `skeletons=0`、目录文本已存在，但用户仍看到骨架屏 → Electron 合成/重绘问题；
   - 可置前窗口，并触发一次 `resize` 或轻微 zoom 后恢复；
   - 若 DOM 自身仍有 skeleton → 继续等真实 pending 请求，勿先重绘掩盖问题。

6. **分支切换只做受控复现**：
   - main → AI → main 最多一轮，逐次等 skeleton=0；
   - 记录 JS Heap；持续上涨即停止；
   - 连续切换导致客户端崩溃时，不再暴力重试；干净重启并最终恢复 `.apifox/suites.yaml` 的 `working_branch`。

### 本次基线（项目 346275，2026-07-28）

- 客户端 2.7.43 与升级后的 2.8.33 均复现；
- `test-scenario/tree-list`：HTTP 200、约 32KB，目录结构有效；
- `/api-details`：编码后约 6.6MB，约 13～20 秒，切分支可出现第二轮全量请求；
- 自动化场景仅 16 个，分支仅 3 个；「分支/场景数量过多」不是已证实根因；
- 连续切分支时 JS Heap 约 199MB → 322MB，随后客户端退出；
- 干净重启、等待请求完成并强制重绘后可恢复。

### 根治项（交给 Apifox 私有化客户端/服务端）

- 自动化页面先独立渲染 `test-scenario/tree-list`，不要等待 API / Schema / Mock 全量资源；
- `/api-details` 按项目/分支/模块过滤，只返回列表字段，支持分页、懒加载与 ETag；
- 切分支时 `AbortController` 取消旧请求，并按 `projectId + branchId` 去重缓存；
- `customHttp` 步骤无需预载全量 API；仅打开关联 `apiDetailId` 的步骤时按 ID 加载；
- 验收：`tree-list` 返回后 1 秒内显示目录；`api-details` pending/失败不阻塞；连续切 5 次分支不崩溃且 Heap 不持续上涨。

### 安全红线

- **不得**仅因骨架屏就删除/归档场景、移动目录或拆分生成器；
- 发现 orphan folder 也先证明与 UI 失败相关；目录修复后无改善应立即撤销「它是根因」的判断；
- 修改共享 Apifox 项目、强制重启客户端、清缓存前都要向用户确认；
- CLI/UI 诊断完成后，把客户端留在资产配置的 `working_branch`。

---

## 1. Apifox 不继承「集合级 pre-request」到后置脚本

**现象**：`后置脚本错误: fpAssertHttpBusinessOk is not defined`（或其它 `fp*` / `lo*` 函数）。

**根因**：Postman 中集合 pre-request 定义的函数，在同一次请求的 **Tests** 里通常可用；**Apifox 常隔离 pre-request 与 test 沙箱**，集合级 `event[].listen=prerequest` **不能**替代每步 test 内的 helpers。

**自助**：

1. **`RequestItem(js_helpers=Build*JsHelpersLines, …)`**，让 `MakeTestEvent` 注入完整 helpers（与 Local Offer P1 一致）。
2. **仅 WAIT 等极轻步骤**可用 `js_helpers=lambda: []`。
3. **不要**为「减小 JSON」只在集合级注入 helpers 而不改 test——Apifox 必挂。

**代码锚点**：[`collection_builder_common.py`](../../../api-testcases/api_tests/postman/generators/collection_builder_common.py) `MakeTestEvent`；fitness 曾误用 `CollectionPreRequestEvent` 已回退。

---

## 2. 取消订单重试：禁止 async sendRequest + done（永久 loading）

**现象**：`【取消 usage 预订单】| E02-S07 | PATCH` 一直 loading；总耗时很长但「接口请求耗时」很短。

**根因**：

- `pm.test('…', function (done) { pm.sendRequest(..., function () { …; done(); }); })` 在 Apifox 中 **`done()` 未正确结束** 或 HTTP 200 断言与业务失败冲突 → 步骤永不完成。
- `setTimeout` + `setNextRequest` **回跳同名请求** → UI 显示同一步重复、状态混乱。

**推荐形态（fitness 现行）**：

```text
E02-S07      PATCH 取消（第 1 次）  → fpCancelOrderAttempt(..., 1, 3, skipToNextStepName)
E02-S07-R2   PATCH 取消（第 2 次）
E02-S07-R3   PATCH 取消（第 3 次）
```

- **`fpCancelOrderAttempt`**：成功则 `fpMarkCancelDone` + 断言；可重试且非末次 → test 记「可重试」**继续下一步**（非回跳）。
- **首次成功**：`fpSetNextRequestByName(skipToNextStepName)` **向前 skip** 剩余 R2/R3（仅 skip 向前，不回跳）。
- **对齐 pytest**：`PatchCancelOrderWithRetry`、可重试 msg 含 `Order cancellation failed`、errCode `500.041.006` / `500.071.016`。

**禁止**：`pm.sendRequest` 做取消重试；`pm.test(..., done)` 包 HTTP 重试；回跳 `setNextRequest(当前步名)`。

---

## 3. 脚本内 busy-wait 导致 Apifox 卡死

**现象**：WAIT 步骤或取消 pre-request 显示 **0ms** 长时间「运行中」；CPU 占满。

**根因**：在 **含数百行 helpers 的 pre-request** 或独立 WAIT 里 `while (Date.now() - start < 30000) {}`。

**自助**：

1. **默认不在集合内做 15s/30s 同步等待**（fitness 已移除 `fitnessCancelBeforeMs` / `fitnessCancelRetryIntervalMs` WAIT 步）。
2. 若产品强制「下单后 N 秒再取消」：**pytest 侧 sleep**；Apifox 侧用运行器 **步骤间隔** 或文档说明手动 pause。
3. 若必须 WAIT 步：脚本 **仅数行**、无 helpers 复制（仍可能卡，优先避免）。

---

## 4. JS helpers 前缀与 Auth 变量

**现象**：`epGetInnerData is not defined`（fitness 集合）。

**根因**：从 eSIM 派生时 Auth/断言仍调 `ep*`，helpers 已改为 `fp*`。

**自助**：全集合统一 **`BuildFitnessJsHelpersLines`** 前缀；Auth test 用 `fpGetInnerData`；生成器内勿留 eSIM 死代码块。

---

## 5. 请求命名：测试目的前置

**现象**：Apifox 列表只有 `E02-S07 PATCH /orders`，看不出验证意图。

**格式**：`【目的】| 步骤号 | METHOD 路径` — 使用 [`PurposeName()`](../../../api-testcases/api_tests/postman/generators/collection_builder_common.py) 或 `StepSpec.purpose`。

**细则**：[`postman-purpose-first-naming.md`](./postman-purpose-first-naming.md)。

---

## 6. fitness schedule URL：Apifox 动态日期写在 query 上

**现象**：`GET …/schedule` 无 query 或日期不对；依赖 `fitnessScheduleQuery` 变量但 URL 未带上。

**推荐 URL**（生成器常量 `FITNESS_SCHEDULE_URL_PATH`）：

```text
/v2/resources/fitness/{{fitnessResourceId}}/schedule
  ?startDate={{$date.now|addDays(5)|format('yyyy-MM-dd')}}
  &endDate={{$date.now|addDays(10)|format('yyyy-MM-dd')}}
  &fallbackAllowed=true
```

- **不要**再用 pre-request `fpPrerequestScheduleQuery()` 拼 `fitnessScheduleQuery`（Apifox 表达式在 URL 上更可靠）。
- **`fpParseFitnessSchedule`** 仍从响应写 `fitnessOptionId`、`prebookingDate`。
- 删除废弃集合变量：`fitnessScheduleQuery`、`fitnessScheduleStartOffsetDays`、`fitnessScheduleEndOffsetDays`。

---

## 7. 性能与 JSON 体积

| 策略 | Postman | Apifox |
|------|---------|--------|
| helpers 仅在 **集合 pre-request** 注入一次 | 可接受 | **test 找不到函数** ❌ |
| helpers 在 **每步 test** 注入 | JSON 大、略慢 | ✅ 可用 |
| 线性重试 + 向前 skip | 步数略增 | 比回跳 loading 稳定 |
| 无 busy-wait | — | 显著减负 |

**Agent 默认**：Apifox 可跑 **优先**；体积优化不能牺牲 test 内 helpers。

**注意**：本节解决的是集合/步骤脚本体积与运行性能；项目打开时的骨架屏须按 §0.1 测桌面端真实网络请求。仓库 JSON 大，不代表 UI 的 `test-scenario/tree-list` 大。

---

## 8. 变更检查清单（生成器改完必做）

```text
- [ ] python api-testcases/api_tests/postman/generators/GeneratePostmanCollection*.py
- [ ] JSON 中 schedule 请求含 startDate/endDate Apifox 表达式（若适用）
- [ ] 取消步骤无 sendRequest/done、无 WAIT busy-wait
- [ ] 抽样打开 1 个请求的 test script：含 function fpAssertHttpBusinessOk（或 lo*）
- [ ] 提醒用户 Apifox **重新导入** 覆盖旧集合
- [ ] 断言语义与 pytest helpers 仍对齐
```

---

## 9. 案例索引：fitness ePass P0（2026Q2）

| 文件 | 说明 |
|------|------|
| [`GeneratePostmanCollectionFitnessEpass.py`](../../../api-testcases/api_tests/postman/generators/GeneratePostmanCollectionFitnessEpass.py) | 生成器主维护 |
| [`Fitness-ePass-P0-e2e-core.postman_collection.json`](../../../api-testcases/api_tests/postman/collections/Fitness-ePass-P0-e2e-core.postman_collection.json) | 导入产物 |
| [`historical_epass_service.py`](../../../api-testcases/api_tests/services/historical_epass_service.py) | `PatchCancelOrderWithRetry`、schedule 解析 |
| [`test_historical_epass_regression.py`](../../../api-testcases/api_tests/tests/regression/test_historical_epass_regression.py) | fitness 三条主链路 parametrize |

**生成命令**（仓库根）：

```powershell
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionFitnessEpass.py
```
