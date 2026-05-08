# API 测试用例目录

与 `testcases`（功能测试用例）平级，用于存放 API 自动化测试用例。

## 长期主线

[`api_tests/`](api_tests/) 是后续长期维护的业务接口自动化主线。新增接口能力、新需求扩展、公共断言、回归分层和 Postman 导出默认进入该目录，以接口能力为长期资产维护，不再按迭代复制整套自动化。

[`2026Q2_SP1/`](2026Q2_SP1/) 保留为历史金样例与迁移参考，原则上不再作为新需求默认开发目录；确需修复历史样例时，应同步评估是否也需要更新 `api_tests/`。

## 协作入口

- 主线 README：[`api_tests/README.md`](api_tests/README.md)
- 自动化覆盖索引：[`docs/automation-coverage-index.md`](docs/automation-coverage-index.md)
- 主调用链：[`docs/api-main-call-chains.md`](docs/api-main-call-chains.md)
- 跨迭代追溯：[`../knowledge/traceability.md`](../knowledge/traceability.md)

涉及 **接口自动化**，或在讨论本目录 API/pytest/Allure/Postman 时提到 **自动化**，请让 Cursor Agent 先读并遵循：[`../.cursor/skills/api-testcase-pack/SKILL.md`](../.cursor/skills/api-testcase-pack/SKILL.md)。
