# 业务能力地图

按**业务域 / 能力块**组织（不按迭代）。每块尽量写清：价值、主要入口、关键概念；细节链到 `tech-docs` 与 `requirements`。

---

## 会籍与内部扩展（extensions）

- **简述**：（待补充）内部租户会籍注册/查询等路径上的扩展字段能力；与 `extensions` 数组、`feature` 等承载方式相关。
- **主要入口**：（待补充）如 `POST /v2/memberships`、`POST /v2/memberships/search`、extensions 更新路径等；以技术文档为准。
- **关键概念**：`type` / `value`、同一会籍内 `type` 唯一、条数上限、内部租户可见性等。
- **需求示例**：[PAPI-2548](../requirements/2026Q2_SP1/PAPI-2548.md)
- **自动化参考**：[api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md)

---

## 权益与 SWAP（示例占位）

- **简述**：（待补充）
- **主要入口**：（待补充）
- **需求线索**：见 [`requirements/`](../requirements/) 各迭代中带 SWAP / entitlement 的文档标题。

---

## 资源列表与告警（示例占位）

- **简述**：（待补充）
- **主要入口**：（待补充）
- **需求线索**：如 [可用资源列表逻辑优化与告警机制](../requirements/2026Q1_SP3/可用资源列表逻辑优化与告警机制.md)（若路径变更请更新本链接）。

---

## 如何新增能力块

复制上一节结构，保持**简短**；接口与规则以 `tech-docs` 与需求原文为准，此处只作**导航**。
