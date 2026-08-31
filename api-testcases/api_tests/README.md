# api-testcases/api_tests

长期维护的接口自动化框架目录。**执行与验收单轨为 Apifox CLI · Repo-first**（见 [`apifox-cli/`](apifox-cli/) 与 [framework-evolution.md](docs/framework-evolution.md)）。

`api-testcases/2026Q2_SP1` 仅作历史金样例参考。新需求只改 `apifox-cli/generators/` + `.apifox/suites.yaml`，**禁止**新增 `tests/**/test_*.py` 作为正式验收。

## 目录分层

| 目录 | 作用 |
|------|------|
| **`apifox-cli/`** | **正本**：生成器 / 可审 Collection / envs / datasets / docs |
| `docs/` | 框架演进、pytest 退役对照 |
| `framework/` / `clients/` / `services/` / `scenarios/` | 历史 pytest 分层（**冻结**，待按对照表退役） |
| `tests/` | 历史 pytest 用例（**冻结**，见 [`docs/pytest-retirement-map.md`](docs/pytest-retirement-map.md)） |
| `testdata/` / `config/` / `datasets/` | 历史/辅助数据（换测优先 Apifox Environment / 数据集选行） |

## 验收入口（唯一主路径）

资产列表：[`.cursor/skills/apifox-cli-repo-first/catalog.md`](../../.cursor/skills/apifox-cli-repo-first/catalog.md)

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548
```

映射配置：[`.apifox/suites.yaml`](../../.apifox/suites.yaml)。其中 `pytest_e2e` / `scenario_orchestrator` **仅历史备注**，不作执行依赖。

## 新增接口能力约定（单轨）

1. 抄 catalog 最近似资产，新增或扩展 `apifox-cli/generators/GeneratePostmanCollection*.py`。
2. 在 `.apifox/suites.yaml` 增加 `assets.<key>`（场景目录先问用户：membership|epass|common × P0/P1 × prebooking|walk-in|others）。
3. 变量供给先问：A 数据集选行 / B Environment。
4. `SyncCheck` 绿；确认 `catalog.md` 有对应行。
5. **不要**新增 pytest E2E；不要只改 Apifox UI。

协作文档：[`apifox-cli/docs/Apifox-CLI-Repo-First-协作指南.md`](apifox-cli/docs/Apifox-CLI-Repo-First-协作指南.md)  
Agent Skill：[apifox-cli-repo-first](../../.cursor/skills/apifox-cli-repo-first/SKILL.md)

## 历史 pytest（冻结，非主路径）

仅排障或退役对照时使用。示例（不推荐作日常验收）：

```powershell
$env:PYTHONPATH = (Resolve-Path "api-testcases\api_tests").Path
$env:DP_PROFILE = "canary"
pytest api-testcases/api_tests/tests -m "contract or smoke" -v --alluredir=reports/api-tests-allure-results
```

退役进度与可删条件见 [`docs/pytest-retirement-map.md`](docs/pytest-retirement-map.md)。
