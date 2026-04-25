# PAPI-2644项目级资源与站点元数据推送及Recovery测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2644.md`；Topic 名：`project.resource.metadata.updated`、`project.transportHub.metadata.updated`；载荷与 **RetrieveProjectResourcesList** / **RetrieveProjectTransportHubList** 一致，`programId` 语义替换为 **projectId**。
- rc: 去重：同一项目下多 program 触发更新时仅推送 **1 次**；Recovery 接口需支持找回上述两类事件（具体 API 以 APIFOX 为准）。

## ProjectResourceMetadataUpdated（项目资源元数据更新）


### tc-p1: 租户内资源基础数据更新后消费者收到单次project.resource.metadata.updated且含projectId

pc: 具备事件订阅或日志/联调抓包能力；项目下挂多个 program；可触发资源元数据更新

- 触发一次覆盖多 program 的资源更新（按需求场景如 N00001 作用多 program）
  - 仅收到 **1 条**（或实现定义的幂等语义下不重复业务通知）`project.resource.metadata.updated`；payload 含 **projectId**；内容与列表接口「租户内在用 program 资源聚合去重」逻辑一致
- rc: 与 `review-reports/Aero-Blue-需求-测试分析.md` 中 PAPI-2644 节对齐

### tc-p2: 推送字段子集与RetrieveProjectResourcesList同构可比

pc: 同一时刻可拉取列表接口结果并消费事件

- 触发资源更新后比对 event 与列表接口返回的关键字段集合
  - 一致或可映射字段无矛盾（以字段清单为准）

## ProjectTransportHubMetadataUpdated（项目站点元数据更新）

### tc-p1: 租户内站点基础数据更新后消费者收到单次project.transportHub.metadata.updated且含projectId

pc: 同资源场景类比；可触发站点元数据更新且多 program 共用项目上下文

- 触发更新
  - 单次事件；payload 含 **projectId**；与 Retrieve Project Transport Hub List 聚合逻辑一致

### tc-p2: 与programId维度历史推送并存或迁移期的无重复业务语义

pc: 若现网仍存在 program 维度推送，需研发说明并存策略

- 在同一数据变更下观察新旧 Topic
  - 不出现对下游重复扣费/重复刷新等副作用，或文档明确双写期预期

## Recovery（事件找回）

### tc-p1: Recovery支持按约定条件找回上述两类Topic对应事件

pc: 已产生资源类与站点类各至少一条事件；掌握 Recovery 入参

- 调用 Recovery 接口指定时间与项目维度
  - 返回或重放中包含两类 Topic 的事件记录，字段可关联到原推送

### tc-p2: Recovery边界无记录与越权项目

pc: 时间窗口内无事件；或非法项目上下文

- 调用 Recovery
  - 空结果或统一鉴权/业务错误，符合 APIFOX

### tc-p3: 高频更新下推送与Recovery顺序与去重可观测

pc: 短时间连续触发多次更新

- 观察事件条数与内容版本或时间戳字段
  - 符合产品「去重一次」或版本递增规则，无异常风暴
