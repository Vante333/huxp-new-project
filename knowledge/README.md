# 业务知识库（knowledge）

本目录存放**跨迭代、按业务能力组织**的总结性文档，用于：快速了解「系统能力长什么样」、评估需求/改动的**影响范围**、对齐需求—方案—测试的**追溯关系**。

需求原文仍以 [`requirements/`](../requirements/) 为准；本库**不复制**长文，只保留结构化索引与链到各目录的入口。

## 读者与阅读顺序

| 读者 | 建议顺序 |
|------|----------|
| 产品 / 业务 | [capability-map.md](capability-map.md) → [contracts-and-integrations.md](contracts-and-integrations.md) |
| 研发 | [contracts-and-integrations.md](contracts-and-integrations.md) → [capability-map.md](capability-map.md) → [change-impact-checklist.md](change-impact-checklist.md) |
| 测试 | [traceability.md](traceability.md) → [change-impact-checklist.md](change-impact-checklist.md) |

## 子文档索引

| 文档 | 用途 |
|------|------|
| [capability-map.md](capability-map.md) | 业务能力地图（按域，不按迭代） |
| [contracts-and-integrations.md](contracts-and-integrations.md) | 对外契约、错误码/信封习惯、集成边界 |
| [traceability.md](traceability.md) | 能力 ↔ 需求 ↔ 方案 ↔ 用例 ↔ 自动化 |
| [change-impact-checklist.md](change-impact-checklist.md) | 按修改类型的影响速查清单 |

## 与仓库其他目录的关系

| 类型 | 位置 |
|------|------|
| 需求列表与自动生成索引 | [`requirements/README.md`](../requirements/README.md)（刷新：`python tools/GenerateRequirementsIndex.py`） |
| 技术方案 / 接口设计 | [`tech-docs/`](../tech-docs/) |
| 功能测试用例 | [`testcases/`](../testcases/) |
| 接口自动化 | [`api-testcases/`](../api-testcases/) |
| 多环境与凭据 | [`env/README.md`](../env/README.md) |
| 需求评审流程与产出 | [`.cursor/skills/requirement-review/SKILL.md`](../.cursor/skills/requirement-review/SKILL.md)、[`review-reports/`](../review-reports/) |

## 维护约定

- **何时更新**：重大能力上线或需求定稿时，更新 [capability-map.md](capability-map.md) 对应小节与 [traceability.md](traceability.md) 相关行；若涉及对外行为，同步 [contracts-and-integrations.md](contracts-and-integrations.md)。
- **写什么**：短句 + **链接**；细节一律指向 `requirements` / `tech-docs` / 用例与自动化 README。
- **不做什么**：不把整份需求粘贴进本目录；不替代 Jira/Confluence 权威版本。
