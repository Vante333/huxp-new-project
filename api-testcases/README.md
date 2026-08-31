# API 测试用例目录

与 `testcases`（功能测试用例）平级，用于存放接口自动化。

## 长期主线（单轨）

[`api_tests/`](api_tests/) 为长期主线；**正式执行与验收 = Apifox CLI · Repo-first**：

- 正本目录：[`api_tests/apifox-cli/`](api_tests/apifox-cli/)
- 入口：`.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset <key>`
- 资产表：[`.cursor/skills/apifox-cli-repo-first/catalog.md`](../.cursor/skills/apifox-cli-repo-first/catalog.md)

[`2026Q2_SP1/`](2026Q2_SP1/) 保留为历史金样例，不再作为新需求默认开发目录。

pytest（`api_tests/tests/` 等）已**冻结**，不得再扩新用例作第二套真相；退役对照见 [`api_tests/docs/pytest-retirement-map.md`](api_tests/docs/pytest-retirement-map.md)。

## 协作入口

- 主线 README：[`api_tests/README.md`](api_tests/README.md)
- 框架演进：[`api_tests/docs/framework-evolution.md`](api_tests/docs/framework-evolution.md)
- Apifox CLI 协作：[`api_tests/apifox-cli/docs/Apifox-CLI-Repo-First-协作指南.md`](api_tests/apifox-cli/docs/Apifox-CLI-Repo-First-协作指南.md)
- 主调用链：[`docs/api-main-call-chains.md`](docs/api-main-call-chains.md)
- 覆盖索引（历史）：[`docs/automation-coverage-index.md`](docs/automation-coverage-index.md)

涉及接口自动化 / Apifox CLI / SyncCheck，请让 Agent 先读：  
[`.cursor/skills/apifox-cli-repo-first/SKILL.md`](../.cursor/skills/apifox-cli-repo-first/SKILL.md)  
（pytest 历史约定仍见 [`api-testcase-pack`](../.cursor/skills/api-testcase-pack/SKILL.md)，但**新需求不得走双轨**。）
