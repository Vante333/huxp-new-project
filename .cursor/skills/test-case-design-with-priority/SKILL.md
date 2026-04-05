---
name: test-case-design-with-priority
description: >-
  按团队规范进行功能测试用例设计与优先级标注（P1/P2/P3，不使用 P0），含需求分析、测试点提取、
  Markdown 与 XMind/脑图兼容结构、用例精简合并与评审清单。在用户编写或评审 testcases、功能用例、
  测试用例设计、优先级、tc-p1、脑图导入、或引用本仓库用例规范时使用；Agent 应先读本 Skill，
  细则与示例见 reference.md。
---

# 功能测试用例设计（含优先级）

## 触发条件

用户涉及 **功能测试用例** / **testcases** / **用例优先级（P1、P2、P3）** / **XMind 或脑图导入** / **tc-p1、tc-p2、tc-p3** / **需求拆解测试点** 时，应先 **Read 本文件**，再按需 **Read [reference.md](reference.md)**（完整规范、示例与附录）。

若同时在搭建 **pytest 接口自动化** 或 **api-testcases**，另见 [api-testcase-pack](../api-testcase-pack/SKILL.md)。

## 执行顺序

1. 通读本节检查清单。
2. 输出或改写用例前打开并遵循 [reference.md](reference.md) 中对应章节（尤其「三、用例精简与合并」「四、用例文档结构」「六、用例评审与质量检查」「九、附录」）。

## 核心检查清单（简版）

- **优先级**：仅用 P1/P2/P3；前缀 `tc-p1:` / `tc-p2:` / `tc-p3:` 或 `tc:`；历史 P0 体系迁移规则见 [reference.md](reference.md) §2.1。
- **命名**：模块名与用例名 **无空格**；英文 **PascalCase**；接口路径作模块名时 **`/` → `_`**。
- **结构**：H1 根标题不导入系统；用例标题行 `tc:` 或 `tc-p{n}:`；子项顺序 `pc:` → 步骤（一级 `-`）→ 单条预期（子级 `  -`）→ 可选 `rc:`、`tag:`；**每步仅一个预期**。
- **精简**：同构场景参数化合并；忌「逻辑与 A 一致」式重复；错误码不跨章重复（见 [reference.md](reference.md) §3.3、§9.1）。
- **落盘**：`testcases/{需求名称}-测试用例-{序号}.md`（见 [reference.md](reference.md) §5.1）。

## 权威条文

完整方法论、表格、长示例、XMind 说明与常见错误见 [reference.md](reference.md)。
