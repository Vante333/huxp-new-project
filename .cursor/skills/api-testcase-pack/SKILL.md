---
name: api-testcase-pack
description: >-
  按本仓库金样例搭建 pytest 接口自动化套件：分层环境变量、Allure 报告、Postman Collection v2.1
  生成器与可导入 JSON、团队协作文档。当用户消息出现「接口自动化」「API 自动化」「自动化」
  （且与 API、pytest、Allure、Postman、api-testcases 或本仓库接口测试相关）、「api-testcases」
  「Allure」「Postman」「接口测试自动化」或按 PAPI-2548/2026Q2_SP1 模式新建/扩展套件、与 testcases
  用例表对齐时使用；Agent 应先读取本 Skill 再产出目录结构与命令，与 api-testcases/2026Q2_SP1 一致。
---

# 接口自动化套件（api-testcase-pack）

## 触发条件

用户只要提到 **接口自动化**，或在与 API/pytest/Allure/Postman/`api-testcases`/本仓库接口测试相关的语境下提到 **自动化**，或上列 description 中的其它触发词，即应 **先读取并遵循本 Skill**，再生成或修改代码与文档，使结构与金样例 `api-testcases/2026Q2_SP1/` 对齐。

## 金样例（必读）

先阅读并对齐目录 [`api-testcases/2026Q2_SP1/`](../../../api-testcases/2026Q2_SP1/)：

| 文件/目录 | 作用 |
|-----------|------|
| [`README.md`](../../../api-testcases/2026Q2_SP1/README.md) | 环境变量表、运行命令、Allure/断言约定、与 curl 对照 |
| [`conftest.py`](../../../api-testcases/2026Q2_SP1/conftest.py) | 分层 `.env`、`DP_PROFILE`、`pytest` markers、Allure fixture |
| [`pytest.ini`](../../../api-testcases/2026Q2_SP1/pytest.ini) | `addopts = --clean-alluredir`（与 `--alluredir` 配合防结果翻倍） |
| [`papi2548_helpers.py`](../../../api-testcases/2026Q2_SP1/papi2548_helpers.py) | HTTP + Allure 步骤、断言、与 Postman 共享语义 |
| [`test_papi_2548_extensions.py`](../../../api-testcases/2026Q2_SP1/test_papi_2548_extensions.py) | `@allure`、`ScenarioSteps`、用例组织方式 |
| [`postman/`](../../../api-testcases/2026Q2_SP1/postman/) | 生成脚本、`.postman_collection.json`、环境 JSON、`README.md` |

更细的命令与模板见同目录 [`reference.md`](reference.md)。

## 权威与双轨

- **自动化与报告**：以 **pytest + Allure** 为权威；Postman/Apifox 用于联调、演示与导入共享。
- Postman Tests（JS）与 Python helpers **语义需对齐**；变更时同步修改两处，必要时用归一化/parity 小测校验（参见金样例中 `test_p2548_normalize_parity.py` 一类做法）。

## 工作流清单

复制并逐项勾选：

```
- [ ] 确定 Jira/需求编号，在 api-testcases/<迭代或前缀>/ 建套件目录
- [ ] pytest.ini：含 --clean-alluredir（与命令行 --alluredir 同用）
- [ ] conftest.py：仓库根 .env + env/.env.<profile>（DP_PROFILE），markers，Allure 相关 fixture
- [ ] *_helpers.py：HTTP 封装、RequestWithAllure、共享断言/归一化；错误路径处理完整
- [ ] test_*.py：@allure.feature/story、ScenarioSteps、按需 skip/沙箱探测
- [ ] 套件 README.md：DP_* 表、PYTHONPATH（Windows）、pytest/allure 命令
- [ ] postman/Generate*.py → v2.1 Collection JSON；可选 *.postman_environment.json；postman/README.md（变量与 DP_* 映射、JS↔Python）
- [ ] testcases/ 下维护「用例 ↔ pytest」对照表，并从套件 README 链到该表
```

## 硬性约定（与金样例一致）

### Allure

- 运行：`pytest ... --alluredir=<目录>`；查看：`allure serve <目录>`（需本机安装 Allure CLI）。
- 与 JSON 相关的附件优先用 **`text/plain`** 承载格式化内容，避免 Allure 2.x 对 `application/json` 预览空白。
- HTTP 步骤附件顺序、断言与步骤同级等规则以金样例 README 与 `RequestWithAllure` 用法为准。

### Postman

- 使用 **Collection v2.1**（`schema.getpostman.com/json/collection/v2.1.0/collection.json`）。
- 集合变量与仓库 `DP_*` / `env/.env.*` 对照写在 `postman/README.md`。

### 协作与安全

- 凭据 **不提交**：真实值放 `env/.env.<profile>`（已 gitignore）；仓库只保留 `.env.example`、`env/.env.*.example`。
- 报告目录建议：`reports/<feature>-allure-results`（或团队统一路径），勿把含敏感信息的原始结果提交到公开分支。

## 代码风格

新增 Python 与**当前套件内文件、金样例**保持一致；pytest 钩子、`pytest_*` 函数名遵循 pytest 惯例。若项目另有 `.cursor/rules` 约定，与之对齐。
