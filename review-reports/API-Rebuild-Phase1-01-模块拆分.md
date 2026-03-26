# 1.0 API Rebuild Phase 1 - 权益管理部分 - 模块拆分

## 拆分概览

| 模块编号 | 模块名称 | 涉及接口 | 功能点数 |
|---------|---------|---------|---------|
| M1 | 权益发放 | POST /v3_general_entitlement_issuance | 7 |
| M2 | 权益查询（单条） | POST /v3_general_entitlement_query | 3 |
| M3 | 会员权益列表 | POST /v3_general_member_entitlement_list | 4 |
| M4 | 权益状态管理 | POST /v3_general_entitlement_status_update | 4 |
| M5 | 权益编辑 | POST /v3_general_entitlement_update | 4 |
| M6 | 动态二维码（核销） | POST /v3_general_entitlement_qrcode | 4 |

## M1: 权益发放

### 涉及接口

- `POST /v3_general_entitlement_issuance`

### 核心功能点

1. 无会员发放：通过第三方用户 id（`clientUserId`）发放
2. 已有会员发放：通过 DP 会员 id（`memberId`）发放
3. 支持自定义有效期
4. 同一 `clientUserId` 下可多次发放
5. `clientOrderId` 可选；支持 `remark` 扩展字段
6. 权益数量支持小数（与 2.5 高铁休息室等场景关联）
7. 权益精细化管理：`usageAllocation`（持卡人/携伴），需 SAAS 开关与品类支持

### 业务规则

1. `clientUserId` 与 `memberId` 二选一
2. `availableUsages` 必填
3. `cardholderUsages + guestUsages = availableUsages`（当传入精细化分配时）
4. 重复 `clientOrderId` 不可再次发放（当传入该字段时）
5. `entitlementTemplateId` 须有效

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 500.031.002 | 重复 `clientOrderId` | 同一个第三方订单号不能重复发放权益 |
| 301.031.003 | 无效 `entitlementTemplateId` | 权益编码有误 |
| 500.031.005 | `usageAllocation` 与总额不一致 | 权益总额不一致 |

## M2: 权益查询（单条）

### 涉及接口

- `POST /v3_general_entitlement_query`

### 核心功能点

1. 按 `clientOrderId`（若历史有传入）查询
2. 按 `voucherCode` 查询
3. 返回：权益基本信息、剩余可使用次数、有效期

### 业务规则

1. 不支持使用 `clientUserId` 查询
2. 查询条件组合规则（二选一 / 同时支持 / 优先级）文档未明确，需在需求中补齐

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 301.031.001 | 权益券不存在等 | 权益不存在 |

## M3: 会员权益列表

### 涉及接口

- `POST /v3_general_member_entitlement_list`

### 核心功能点

1. 分页查询
2. 按状态筛选
3. 支持筛选/展示字段：`categoryType`（SL / FT / DG / LS）、`status`、`validTo`
4. 面向 App 展示某会员下剩余权益数量

### 业务规则

1. 须绑定有效会员上下文（具体入参名未在本文档定义）
2. `status` 的枚举取值与业务含义需在需求或 APIFOX 中对齐

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 301.010.002 | 会员不存在 | 会员不存在 |

## M4: 权益状态管理

### 涉及接口

- `POST /v3_general_entitlement_status_update`

### 核心功能点

1. 正常 → 冻结
2. 冻结 → 正常（解冻）
3. 非作废（正常 + 冻结）→ 作废
4. 文档另给出生命周期示意：发放 → 正常 →（使用中）→ 使用完成，以及冻结/解冻/作废分支

### 业务规则

1. 非法状态流转应拒绝（具体错误码未单独列出）
2. 「使用中」「使用完成」与状态枚举的关系未在表格中定义

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 500.031.004 | 状态更新失败 | 权益状态变更失败 |

## M5: 权益编辑

### 涉及接口

- `POST /v3_general_entitlement_update`

### 核心功能点

1. 修改用户姓名
2. 修改有效期
3. 修改权益数量
4. 修改 `usageAllocation`（受商品开关、品类是否支持精细化管理约束）

### 业务规则

1. 当不支持精细化管理时，不可编辑 `usageAllocation`
2. `usageAllocation` 与总额需一致（与发放规则同类约束）
3. 已消耗场景下如何调整数量/分配：文档未说明

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 500.031.003 | 权益更新失败 | 权益编辑失败 |
| 500.031.005 | 权益总额不一致 | 权益总额不一致 |
| 500.031.005 | 不支持编辑 `usageAllocation` | 该权益不支持编辑 `usageAllocation` |

> 说明：后两行共用同一错误码，需与研发/规范确认是否拆码或靠 message 区分。

## M6: 动态二维码（核销）

### 涉及接口

- `POST /v3_general_entitlement_qrcode`

### 核心功能点

1. 生成短时有效二维码
2. `duration` 控制有效期（默认 60 秒）
3. 适用品类：休息室（SL）、快速安检（FT）
4. 返回 `qrCode`、`validUntil`（时间戳）

### 业务规则

1. 非 SL/FT 或其他不满足条件时的拒绝规则与错误码未在本文档列出
2. 二维码与权益实例的绑定、重复使用、核销闭环未在本文档描述

### 错误码

| 错误码 | 触发条件 | 错误信息 |
|-------|---------|---------|
| 500.031.006 | 二维码生成失败 | 二维码生成失败 |
