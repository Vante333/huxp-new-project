# Resource 接口性能优化技术方案 - 方案解构

## 解构概览

| 模块编号 | 模块名称 | 涉及接口 | 关联需求 | 技术要素 |
|---------|---------|---------|---------|---------|
| T1 | 背景、目标与缓存架构 | 间接影响 `getResources` 链路的资源查询 | 待关联正式需求/JIRA | 文字说明、指标表、L1/L2/L3 层级表、缓存 key 设计 |
| T2 | Program 级二级缓存查询实现 | 内部服务方法 `getNetworkListByProgram` 等 | 待关联正式需求/JIRA | 伪代码片段、Caffeine 配置、`@DataCacheable` |
| T3 | 缓存一致性、多节点与预热 | MQ 消费、`CacheWarmUpJob` | 待关联正式需求/JIRA | 文字说明、RocketMQ 广播消费 |
| T4 | 影响范围与回归面 | `/v2/resources`、`/v2/transportHubs`、`/v2/search`、`/v2/search/modules` | 待关联正式需求/JIRA | 影响范围表 |

**技术方案落盘路径**：`tech-docs/2026_Q2SP2/Resource.md`  
**Confluence 来源**：<https://dragonpass.atlassian.net/wiki/spaces/DGSN/pages/1720418344/Resource>

---

## T1: 背景、目标与缓存架构

### 涉及接口

- 文档定位为 `getResources` 接口性能问题；对外影响见 T4 所列 v2 接口。

### 技术要素

- 问题背景：大 Map 反序列化、GC、TPS。
- 优化目标表：TPS、P95、YGC、Full GC。
- 缓存层级：Caffeine（L1）、Redis（L2）、Boss（L3）。
- 本地缓存 key、Redis key 字符串格式说明。

### 关联需求

- **本次评审未收到独立需求文档或 JIRA 编号**；建议研发补充后回填本表「关联需求」列。

### 变更范围

- 引入/强化二级缓存架构；program 级查询拆解为 project 粒度缓存（方案概述与架构章节）。

### 技术方案摘要

> 针对 getResources 接口高并发下因大对象频繁创建导致 GC 压力大、TPS 低的问题，引入 Caffeine 本地缓存 + Redis 分布式缓存 的二级缓存架构。

---

## T2: Program 级二级缓存查询实现

### 涉及接口

- 主要为内部实现：`getNetworkListByProgram`、`getNetworkListBySingleProject`、本地缓存管理类。

### 技术要素

- Caffeine：`expireAfterWrite(900s)`、`maximumSize(5000)`、`recordStats`。
- Program 维度聚合：遍历 `ProjectQueryKey`、合并 module、按资源 id 去重。
- Redis：`@DataCacheable` 与 key 表达式。

### 关联需求

- 待补充（同上）。

### 变更范围

- `NetworkResourceWithCacheService`（或等价模块）及相关调用链（依实际代码仓库为准）。

### 技术方案摘要

> 对每个组合构造本地缓存 key，先查 Caffeine；未命中则调用 getNetworkListBySingleProject（该方法已带 @DataCacheable Redis 缓存）；合并结果并按 module 去重返回。

---

## T3: 缓存一致性、多节点与预热

### 涉及接口

- 通过 T4 中间接影响对外接口；MQ 与 Job 为内部机制。

### 技术要素

- Program 配置变更触发 RocketMQ。
- 消费者：`apiProgramFacade.resetInit`、`getNetworkListByProgram` 重新加载。
- TTL 900s 兜底；`CacheWarmUpJob` 预热。
- 多节点：MQ 广播消费 `PROGRAM_PROJECT_TOPIC`。

### 关联需求

- 待补充。

### 变更范围

- MQ 消费者、定时预热任务、与 Program 配置刷新相关的 facade/service。

### 技术方案摘要

> 本地缓存与 Redis 缓存均设置 900 秒过期……当前使用 RocketMQ 广播消费……每个节点独立消费消息并执行 getNetworkListByProgram，从而刷新自己的本地缓存。

---

## T4: 影响范围与回归面

### 涉及接口

- `/v2/resources`
- `/v2/transportHubs`
- `/v2/search`
- `/v2/search/modules`

### 技术要素

- 影响范围表（序号、接口、备注）。

### 关联需求

- 待补充（用于圈定回归与验收范围）。

### 变更范围

- 凡依赖 program/project 网络资源清单聚合的读链路（方案列示四类接口）。

### 技术方案摘要

> 影响范围表列出上述四个接口及备注。
