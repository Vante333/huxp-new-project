# requirements 需求文档总览

本目录按**迭代**（或主题版本）存放从 Jira / Confluence 同步或整理后的需求 Markdown。单条需求多为 `PAPI-xxxx.md` 或描述性文件名；**逐文件详情以原文为准**，本页与各迭代下的 README 仅提供**导航与索引**。

## 文档分层（建议）

1. **总索引**：本文件中的「迭代一览」表，链向各子目录 README。
2. **迭代摘要**：各 `requirements/<迭代>/README.md` 中的需求列表表，并可补充迭代目标、跨需求依赖、相关测试/方案链接。
3. **主题纵览**（可选）：跨迭代同一业务能力可另写短文，用链接聚合多条 `PAPI-*`，避免复制大段正文导致双份维护。

## 与评审、测试的衔接

- 需求结构化评审流程与产出格式见 [`.cursor/skills/requirement-review/SKILL.md`](../.cursor/skills/requirement-review/SKILL.md)；评审报告默认落在 [`review-reports/`](../review-reports/)。
- 功能用例见 [`testcases/`](../testcases/)，接口自动化见 [`api-testcases/`](../api-testcases/)，技术方案见 [`tech-docs/`](../tech-docs/)。

## 迭代一览

以下表格由脚本根据当前目录结构自动生成；**勿手写修改表体**，应运行生成器刷新。

<!-- REQ_GLOBAL_INDEX_START -->

| 迭代 | 文档数 | 索引 |
| --- | --- | --- |
| `2025Q4_SP4` | 1 | [README](./2025Q4_SP4/README.md) |
| `2026Q1_SP3` | 7 | [README](./2026Q1_SP3/README.md) |
| `2026Q1_SP4` | 7 | [README](./2026Q1_SP4/README.md) |
| `2026Q1_SP5` | 7 | [README](./2026Q1_SP5/README.md) |
| `2026Q2_SP1` | 6 | [README](./2026Q2_SP1/README.md) |
| `API 1.0` | 1 | [README](./API%201.0/README.md) |

<!-- REQ_GLOBAL_INDEX_END -->

## 维护说明

在仓库根目录执行：

```bash
python tools/GenerateRequirementsIndex.py
```

将刷新**本页「迭代一览」**以及**各迭代 README 中「需求文档索引」表**（位于 `<!-- REQ_INDEX_START -->` 与 `<!-- REQ_INDEX_END -->` 之间）。迭代目标、跨需求依赖等手写段落不会被覆盖。

## 跨迭代业务能力总览

按能力域整理的导航与影响评估入口见 [`knowledge/README.md`](../knowledge/README.md)（与按迭代罗列的需求索引互补）。
