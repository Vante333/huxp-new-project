> **放置与读取方式**：本文件位于 **`.cursor/skills/api-testcase-pack/`**，与 [`SKILL.md`](./SKILL.md) 中「Postman / Apifox 排障（Agent 先读）」互链。处理 **Postman Collection 生成器**、**Apifox 自动化运行卡顿/报错/永久 loading**、**fitness / historical ePass / Local Offer pytest-sync 集合** 时，Agent **先读本文件再改** `GeneratePostmanCollection*.py` 或让用户重新导入 JSON。

# Postman / Apifox 集合：Agent 自检与自助处理

**权威对照**：pytest + helpers 语义；Postman/Apifox 为联调与演示。变更断言后须 **改生成器 → 运行 `python …/GeneratePostmanCollection*.py` → 提醒用户 Apifox 重新导入**（勿只手改 JSON）。

**金样例生成器**：[`GeneratePostmanCollectionPapi2548.py`](../../../api-testcases/2026Q2_SP1/postman/GeneratePostmanCollectionPapi2548.py)、[`GeneratePostmanCollectionLocalOfferEpass.py`](../../../api-testcases/api_tests/postman/GeneratePostmanCollectionLocalOfferEpass.py)、[`GeneratePostmanCollectionFitnessEpass.py`](../../../api-testcases/api_tests/postman/GeneratePostmanCollectionFitnessEpass.py)。

---

## 0. 自动排查决策树（Agent 先走此表）

| 用户现象 | 优先怀疑 | 首选动作 |
|----------|----------|----------|
| 后置脚本 `ReferenceError: fpXxx / epXxx is not defined` | helpers 未注入到 **该请求的 test**；或 **ep/fp 前缀混用** | 确认 `RequestItem` 的 `MakeTestEvent` 含 `Build*JsHelpersLines()`；Apifox **不要**仅依赖集合级 pre-request 给 test 提供函数；统一前缀（fitness 用 `fp*`） |
| 某步 **永久 loading**（0ms、运行中不结束） | `pm.test(fn, done)` + `pm.sendRequest` 异步；或 **setNextRequest 回跳同一步** + `setTimeout` | 改为 **同步 test**；重试用 **线性多步 PATCH**（E02-S07 → E02-S07-R2），成功时 **向前** `setNextRequest` skip 剩余重试步；**禁止** `done()` 未调用 |
| Apifox **整体很卡**、总耗时 ≫ 接口耗时 | 每步重复整份 helpers（JSON 膨胀）；或 pre-request **busy-wait**（`while (Date.now()-start<delay)`） | helpers 只注入 test（Apifox 兼容）；**取消** script 内长等待；若业务必须等：用 Apifox 运行器「步骤间隔」或 pytest `PatchCancelOrderWithRetry`，**不要**在集合里 sync 阻塞 15s/30s |
| 同一步在列表出现 **多次**且都像「通过」 | 动态重试把「调度重跑」也记成 passed | 改用线性 R2/R3 步骤；或 test 里不要对「可重试」写 misleading pass |
| 取消返回 `Order cancellation failed. Please try again later.` | 沙箱时序；非脚本 bug | pytest：`PatchCancelOrderWithRetry` + sleep；Apifox：线性 PATCH 重试（无间隔）或用户手动重跑；**勿** sendRequest 循环 |
| schedule / 日期不对 | URL 仍用 `{{fitnessScheduleQuery}}` 等变量但 pre-request 未跑 | GET schedule 的 query 直接写 Apifox 表达式（见 §6） |
| HTTP 200 但断言失败 | Apifox「校验响应」与脚本重复；或 `pm.response.code` 缺失 | 业务成功用 `fpIsBusinessSuccess`；负向步关闭 Apifox 自带 HTTP 200 校验（见 Local Offer description） |
| 改生成器后用户仍报旧错 | 未重新导入 | 明确提示：**覆盖导入** `*.postman_collection.json` |

---

## 1. Apifox 不继承「集合级 pre-request」到后置脚本

**现象**：`后置脚本错误: fpAssertHttpBusinessOk is not defined`（或其它 `fp*` / `lo*` 函数）。

**根因**：Postman 中集合 pre-request 定义的函数，在同一次请求的 **Tests** 里通常可用；**Apifox 常隔离 pre-request 与 test 沙箱**，集合级 `event[].listen=prerequest` **不能**替代每步 test 内的 helpers。

**自助**：

1. **`RequestItem(js_helpers=Build*JsHelpersLines, …)`**，让 `MakeTestEvent` 注入完整 helpers（与 Local Offer P1 一致）。
2. **仅 WAIT 等极轻步骤**可用 `js_helpers=lambda: []`。
3. **不要**为「减小 JSON」只在集合级注入 helpers 而不改 test——Apifox 必挂。

**代码锚点**：[`collection_builder_common.py`](../../../api-testcases/api_tests/postman/collection_builder_common.py) `MakeTestEvent`；fitness 曾误用 `CollectionPreRequestEvent` 已回退。

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

**格式**：`【目的】| 步骤号 | METHOD 路径` — 使用 [`PurposeName()`](../../../api-testcases/api_tests/postman/collection_builder_common.py) 或 `StepSpec.purpose`。

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

---

## 8. 变更检查清单（生成器改完必做）

```text
- [ ] python api-testcases/api_tests/postman/GeneratePostmanCollection*.py
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
| [`GeneratePostmanCollectionFitnessEpass.py`](../../../api-testcases/api_tests/postman/GeneratePostmanCollectionFitnessEpass.py) | 生成器主维护 |
| [`Fitness-ePass-P0-e2e-core.postman_collection.json`](../../../api-testcases/api_tests/postman/Fitness-ePass-P0-e2e-core.postman_collection.json) | 导入产物 |
| [`historical_epass_service.py`](../../../api-testcases/api_tests/services/historical_epass_service.py) | `PatchCancelOrderWithRetry`、schedule 解析 |
| [`test_historical_epass_regression.py`](../../../api-testcases/api_tests/tests/regression/test_historical_epass_regression.py) | fitness 三条主链路 parametrize |

**生成命令**（仓库根）：

```powershell
python api-testcases/api_tests/postman/GeneratePostmanCollectionFitnessEpass.py
```
