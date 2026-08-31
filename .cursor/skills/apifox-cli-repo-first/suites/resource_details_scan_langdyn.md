# resource_details_scan_langdyn · CLI 落地笔记

- **场景**：**368817** · `Resource Details Scan LangDyn · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`（与静态版同目录）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893（UAT canary；CLI 可 `-EnvironmentId 351932` 换 UAT）· 数据集 **3476397**（场景「数据 1」· ePass 行；**勿再用已 404 的 3475756**）
- **生成器**：`api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionResourceDetailsScanLangDyn.py`（**不**改静态版）
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **变量供给**：B · Environment；语种靠 `scanLanguages` JSON 数组（forEach）
- **编排**（**无语种子夹**；Apifox：「ForEach 循环 […] 中的元素」）：
  1. Auth：token + `rdlHelpersSource` + 规范化 `scanLanguages` + **清零 `scanLangIterM*`**
  2. 8 品类夹 → `FOR_EACH | scanLanguages | as=scanLanguagesM{{N}}`
  3. 语种循环内：Auth-Refresh → LIST（仅 page1）→ 资源 forEach → DETAIL
- **语种绑定**：CLI 常读不到 `$.foreach-*.element`；helpers 用 `rdlTakeNextLanguage` 按 `scanLanguages` 下标与 forEach 轮次对齐
- **换测语种**：Environment 改 `scanLanguages`（例 `["fr-FR"]` / 全量 26）；Auth 不把单语种扩成全量
- **CLI 跑**：常需 `baseUrl`；PowerShell 传 `scanLanguages` JSON 用多个 `--env-var`（勿用易截断的 plain `--variables` 对象）；跑前可带 `scanLangIterM*=0` 双保险
- **截断**：`scanMaxDetails`（`0`=不截断详情）
- **默认语种（26）**：`["en-US","ja-JP",…,"hu-HU"]`（无 `zh-CN`；与 Environment 351893/351932 对齐）。冒烟子集：`["en-US","ja-JP","fr-FR"]` + `scanMaxDetails=1`
- **Environment 洁癖**：`rdlSetMulti` **不写** Environment / globals（仅 variables + collection）。共用 **351893 / 351932** 只保留网关+鉴权+扫描配置：`baseUrl`/`x-version`/`accessToken`/`ProgramID`/`clientId`/`secret`/`scanLanguages`；勿堆 `scanResourceIdsM*` / Membership 业务键（后者用 **352446** 或数据集选行）

## 下次自动处置（本资产 · Agent 必跟）

| 症状 | 根因 | 自动处置（改生成器 → PushSteps；Run 先问用户） |
|------|------|-----------------------------------------------|
| UI/断言「仍只有 `hu-HU`」（或始终同一语种）；forEach 很多轮但 `language=` 不变 | `scanLangIterM*` 在 collectionVariables **跨次残留** + 旧 `Math.min` **钳死列表末项**；LIST 前置用残留 `scanCurrentLanguage` 改写 URL | 确认 Auth 调 `rdlEnsureScanLanguages`→`rdlResetLangIterCounters`；`rdlTakeNextLanguage` 越界重置 0（禁钳末项）；`rdlResolveLanguage` 拒未解析 `{{$.foreach-…}}`。Push 后 UI 硬刷新。复验 3 语冒烟 LIST 须含 `en-US`/`ja-JP` |
| 全量几乎只有 Auth POST、0 GET；`accessToken` 断言失败；`ProgramID=EMPTY` | `use_data_set_id` **404 / 与 UI「数据 N」漂移**（曾误用 **3475756**） | 对齐场景「数据 1」→ **3476397**；改 `.apifox/suites.yaml` + Push 保留 `options.useDataSetId`；Auth 保留凭据/空 token 日志。勿先改 `scanLanguages` |
| CLI 多语种正常、UI 仍单语种 | UI 未刷新 AI 分支 / 看的是旧终止跑次 / collection 残留未走到新 Auth | 提醒切 `ai/apifox-cli-sync` 硬刷新；看控制台是否有 `[LANG] 已重置 scanLangIterM*`；以最新 CLI 报告为准 |
| 想确认语种循环未坏 | — | 冒烟：`-e 351932 -d 3476397`，`scanLanguages=["en-US","ja-JP","fr-FR"]`，`scanMaxDetails=1`，`scanLangIterM*=0`；LIST 断言三语种都出现即可，再开全量 |

全局表见 Skill [`reference.md`](../reference.md)「症状 → 自动处置」。

一键 Push：`.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset resource_details_scan_langdyn`

## 可复用点（同类 forEach + 下标回退）

1. **开跑清零**所有模块迭代计数（variables + collection）；计数优先勿长期依赖跨次 collection。
2. **禁止** `Math.min(i, len-1)` 把坏下标钉在末项。
3. 前置改写 URL 的语种必须来自**本轮** forEach/解析结果，勿盲信上次 `scanCurrentLanguage`。
4. `use_data_set_id` 与场景 UI「数据」定期对齐；404 立刻改正本。
5. 全量前先 2～3 语冒烟，再 `scanMaxDetails=0`。
