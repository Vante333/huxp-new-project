# Premium Lounges 下单部分（PAPI-2401）测试用例

> **`testcases/` 路径记法**：文中 `/v2/resources/options_prebookings_availability` 等为下划线复合段；网关/APIFOX 常见为 `/v2/resources/options/prebookings/availability`，**实际请求以 APIFOX 为准**。

## 查可用性接口

### 资源可预约性校验

#### 正向场景验证

- tc-P1-AVAIL-001：Lounge 资源在项目清单+价格清单内且支持预约，查可用性正常返回
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 返回 `available`、`prebookingToken`、`validUntil`、`price` 字段
  - tc-P1: `prebookingToken` 非空，可用于后续下单流程
  - **请求参数**:
    ```json
    {
      "membershipId": "{{membershipId}}",
      "module": 1,
      "resourceId": "{{支持预约的loungeResourceId}}",
      "prebookingDate": "2026-10-01T10:30",
      "adultCount": 1,
      "childCount": 0
    }
    ```
  - **预期响应**:
    ```json
    {
      "code": 0,
      "data": {
        "available": true,
        "prebookingToken": "{{token}}",
        "validUntil": {{timestamp}},
        "price": { "dynamicPrice": true, "currency": "USD", "adultRate": "6.00", "childRate": "6.00" }
      }
    }
    ```

- tc-P1-AVAIL-002：Fast Track 资源在项目清单+价格清单内且支持预约，查可用性正常返回
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 返回结构与 Lounge 一致，包含 `prebookingToken` 等字段
  - **请求参数**: `"module": 2, "resourceId": "{{支持预约的ftResourceId}}"`

#### 资源不支持预约校验（新增错误码 500.020.027）

- tc-P1-AVAIL-003：Lounge/Fast Track 资源在项目中不支持预定，返回错误码 500.020.027
  - tc-P1: `code` = -1
  - tc-P1: 返回错误码 `500.020.027`
  - tc-P1: 错误提示：`Prebooking is not available for this resource under the current program.`
  - **请求参数**:
    ```json
    {
      "membershipId": "{{membershipId}}",
      "module": 1,
      "resourceId": "{{不支持预约的loungeResourceId}}",
      "prebookingDate": "2026-10-01T10:30",
      "adultCount": 1,
      "childCount": 0
    }
    ```
  - **预期响应**:
    ```json
    {
      "code": -1,
      "msg": "Prebooking is not available for this resource under the current program.",
      "errCode": "500.020.027"
    }
    ```

#### 资源不在可用范围校验（错误码 500.020.007）

- tc-P1-AVAIL-004：查询的资源 ID 在该 Program 下不可用，返回错误码 500.020.007
  - tc-P1: `code` = -1
  - tc-P1: 返回错误码 `500.020.007`
  - tc-P1: 错误提示：`Sorry, this resource is not accessible with your program.`
  - **请求参数**:
    ```json
    {
      "membershipId": "{{membershipId}}",
      "module": 1,
      "resourceId": "{{不在该program范围的resourceId}}",
      "prebookingDate": "2026-10-01T10:30",
      "adultCount": 1,
      "childCount": 0
    }
    ```
  - **预期响应**:
    ```json
    {
      "code": -1,
      "msg": "Sorry, this resource is not accessible with your program.",
      "errCode": "500.020.007"
    }
    ```

### Option 级可用性校验

#### 正向场景验证

- tc-P2-AVAIL-005：通过 `/v2/resources/options_prebookings_availability` 查询 Option 级可用性，正常返回
  - tc-P2: HTTP 状态码为 200，`code` = 0
  - tc-P2: 返回 `available`、`prebookingToken`、`validUntil`、`price` 字段
  - **请求参数**:
    ```json
    {
      "membershipId": "{{membershipId}}",
      "module": 1,
      "resourceId": "{{resourceId}}",
      "optionId": "{{optionId}}",
      "prebookingDate": "2026-10-01T10:30",
      "adultCount": 1,
      "childCount": 0
    }
    ```

#### 异常场景验证

- tc-P2-AVAIL-006：Option 级查询资源不支持预定时，返回错误码 500.020.027
  - tc-P2: 返回错误码 `500.020.027`
  - tc-P2: 提示语与资源级查询一致

- tc-P2-AVAIL-007：Option 级查询资源不在 Program 可用范围时，返回错误码 500.020.007
  - tc-P2: 返回错误码 `500.020.007`
  - tc-P2: 提示语与资源级查询一致

### 接口适用范围

#### 模块范围验证

- tc-P2-AVAIL-008：仅 Lounge 和 Fast Track 模块需校验预约支持性，其他模块沿用原逻辑
  - tc-P2: module=1（Lounge）触发新增预约支持性校验逻辑
  - tc-P2: module=2（Fast Track）触发新增预约支持性校验逻辑
  - tc-P2: 其他 module 不受本次变更影响，按原逻辑处理



## 预览订单接口

### Tier 权益判断

#### 正向场景验证

- tc-P1-PREVIEW-001：分级权益（scopeType=2）场景，资源属于 Tier2，预览订单按 Tier2 权益计算扣减
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 响应 `usedEntitlementDetails` 包含 `tier` 字段，值为资源所属 Tier
  - tc-P1: `tierEntitlements` 按该 Tier 权益余额计算扣减明细
  - tc-P1: 扣减总数与 `toUseEntitlementCount` 一致
  - **请求参数**:
    ```json
    {
      "module": 1,
      "membershipId": "{{分级权益的membershipId}}",
      "extra": {
        "prebookingToken": "{{Tier2资源的token}}",
        "cashPaymentApplied": false,
        "toUseEntitlementCount": 1,
        "toUseEntitlementDetail": { "cardholder": 1, "guest": 0 }
      }
    }
    ```
  - **预期响应**（usedEntitlementDetails 部分）:
    ```json
    {
      "usedEntitlementDetails": {
        "tier": 2,
        "tierEntitlements": {
          "cardholderExclusiveEntitlements": 1,
          "guestsExclusiveEntitlements": 0,
          "sharedEntitlements": 0,
          "purchasedEntitlements": 0
        }
      }
    }
    ```

- tc-P2-PREVIEW-002：分级权益（scopeType=2）场景，资源属于 Tier1，预览订单按 Tier1 权益计算扣减
  - tc-P2: 响应 `usedEntitlementDetails.tier` = 1
  - tc-P2: `tierEntitlements` 按 Tier1 权益余额计算

#### 非分级场景兼容性验证

- tc-P1-PREVIEW-003：非分级权益（scopeType=1）场景，预览订单按默认 Tier1 权益计算
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 响应 `usedEntitlementDetails` 中 `tier` = 1（默认）
  - tc-P1: `tierEntitlements` 按全局权益余额计算扣减
  - **请求参数**:
    ```json
    {
      "module": 1,
      "membershipId": "{{非分级权益的membershipId}}",
      "extra": {
        "prebookingToken": "{{token}}",
        "cashPaymentApplied": false,
        "toUseEntitlementCount": 1,
        "toUseEntitlementDetail": { "cardholder": 1, "guest": 0 }
      }
    }
    ```

### usedEntitlementDetails 响应结构变更

#### 字段结构验证

- tc-P2-PREVIEW-004：预览订单响应中 `usedEntitlementDetails` 包含新结构 `tier` + `tierEntitlements`
  - tc-P2: `usedEntitlementDetails` 包含 `tier` 字段（整数类型）
  - tc-P2: `usedEntitlementDetails` 包含 `tierEntitlements` 对象
  - tc-P2: `tierEntitlements` 包含 `cardholderExclusiveEntitlements`、`guestsExclusiveEntitlements`、`sharedEntitlements`、`purchasedEntitlements` 四个字段
  - tc-P2: `purchasedEntitlements` 为新增字段，正确返回买点扣减数量

#### 扣减明细类型覆盖

- tc-P1-PREVIEW-005：权益扣减涉及多种类型（持卡人专属+携伴专属+共享+买点），各类型扣减数量正确

  | 场景 | 持卡人专属 | 携伴专属 | 共享 | 买点 | 说明 |
  |------|-----------|---------|------|------|------|
  | 仅持卡人入场 | 1 | 0 | 0 | 0 | 使用持卡人专属点 |
  | 持卡人+宾客入场 | 1 | 1 | 0 | 0 | 使用持卡人+携伴专属点 |
  | 专属点不足，使用共享点 | 0 | 0 | 2 | 0 | 回退到共享点 |
  | 共享点不足，使用买点 | 0 | 0 | 0 | 1 | 回退到买点 |
  | 混合扣减 | 1 | 0 | 1 | 0 | 持卡人专属+共享点 |

  - tc-P1: 各行场景下 `tierEntitlements` 中对应字段值符合上表预期
  - tc-P1: 扣减总数 = `cardholderExclusiveEntitlements` + `guestsExclusiveEntitlements` + `sharedEntitlements` + `purchasedEntitlements`

### Tier 判定规则

#### 资源跨 Tier 场景

- tc-P2-PREVIEW-006：资源同时配置在 2 个 Tier（Tier1 和 Tier3），以最小 Tier（Tier1）判断权益
  - tc-P2: 响应 `usedEntitlementDetails.tier` = 1（最小 Tier）
  - tc-P2: 按 Tier1 的权益余额计算扣减
  - tc-P2: 不使用 Tier3 的权益

#### 同 Tier 多权益场景

- tc-P2-PREVIEW-007：同一 Tier 下存在多条相同 Tier 权益（配错场景），权益相加后判断
  - tc-P2: 系统将同 Tier 多条权益的余额相加
  - tc-P2: 按相加后的总余额判断是否足够下单
  - tc-P2: `tierEntitlements` 中扣减值不超过该 Tier 权益总余额

#### 单 Tier 扣减限制

- tc-P2-PREVIEW-008：一笔订单只扣除 1 个 Tier 的权益，不跨 Tier 扣除
  - tc-P2: 预览结果中仅返回一个 `tier` 值
  - tc-P2: 不存在同时扣减多个 Tier 权益的情况
  - tc-P2: 即使当前 Tier 权益不足，也不自动借用其他 Tier 权益

### 权益充足性校验

#### 权益充足场景

- tc-P1-PREVIEW-009：当前 Tier 权益充足（持卡人专属+携伴专属+共享+买点总和 ≥ 所需人数），预览成功
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: `cashPaymentApplied` = false
  - tc-P1: 扣减明细正确反映各类型权益使用

#### 权益不足场景

- tc-P1-PREVIEW-010：当前 Tier 权益不足且 `cashPaymentApplied` = false 时，预览失败
  - tc-P1: `code` = -1
  - tc-P1: 返回权益不足的错误提示
  - **请求参数**: `"toUseEntitlementCount": 5`（超出该 Tier 权益总余额）

- tc-P2-PREVIEW-011：当前 Tier 权益不足但 `cashPaymentApplied` = true 时，预览成功
  - tc-P2: HTTP 状态码为 200，`code` = 0
  - tc-P2: `cashPaymentApplied` = true
  - tc-P2: `tierEntitlements` 扣减部分权益，剩余部分由现金支付

### 跨品类权益叠加计算（Step4）

#### 正向场景验证

- tc-P1-PREVIEW-017：单品类 Tier 权益不足，叠加跨品类权益后总量充足，预览成功
  - tc-P1: Step3 计算当前模块+Tier 的单品类权益（如 Lounge Tier2 = 0）
  - tc-P1: Step4 叠加跨品类权益后总可用点数 ≥ 所需人数
  - tc-P1: 预览成功，`code` = 0
  - tc-P1: `tierEntitlements` 中扣减明细正确反映跨品类权益的使用

- tc-P2-PREVIEW-018：单品类 Tier 权益充足，无需叠加跨品类权益，仅从单品类扣减
  - tc-P2: Step3 计算当前模块+Tier 的单品类权益已充足
  - tc-P2: 不触发 Step4 跨品类叠加
  - tc-P2: `tierEntitlements` 仅反映单品类权益的扣减

#### 权益不足场景

- tc-P1-PREVIEW-019：单品类 + 跨品类权益叠加后仍不足（`cashPaymentApplied` = false），预览失败
  - tc-P1: Step3 + Step4 叠加后总可用点数 < 所需人数
  - tc-P1: `code` = -1，返回权益不足的错误提示

- tc-P2-PREVIEW-020：单品类 + 跨品类权益叠加后不足但 `cashPaymentApplied` = true，预览成功
  - tc-P2: 叠加后仍不足的部分由现金支付
  - tc-P2: `cashPaymentApplied` = true

### allowedGuestsPerUsage 规则

#### 宾客数量限制验证

- tc-P2-PREVIEW-012：`allowedGuestsPerUsage` 为 null 时，不限制携带宾客数量
  - tc-P2: 携带多个宾客时预览成功
  - tc-P2: 系统不因宾客数量返回限制错误

- tc-P2-PREVIEW-013：`allowedGuestsPerUsage` 有值时，携带宾客数量超限，预览失败
  - tc-P2: 返回宾客数量超限的错误提示

### 边界值验证

#### Tier 权益边界

- tc-P3-PREVIEW-014：该 Tier 所有类型权益余额均为 0 时，预览失败（`cashPaymentApplied` = false）
  - tc-P3: 返回权益不足的错误提示
  - tc-P3: `tierEntitlements` 各字段均为 0

- tc-P3-PREVIEW-015：该 Tier 仅买点有余额（其他类型均为 0），预览按买点扣减
  - tc-P3: `tierEntitlements.purchasedEntitlements` > 0，其他为 0
  - tc-P3: 预览成功

- tc-P3-PREVIEW-016：`toUseEntitlementCount` = 0 时的预览行为
  - tc-P3: 系统按无需扣减权益处理或返回参数错误



## 创建订单接口

### Tier 权益扣减下单

#### 正向场景验证

- tc-P1-ORDER-001：分级权益场景，创建 Lounge 预约订单，按资源所属 Tier 扣减权益成功
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 返回 `orderId`、`status` = 1（Confirmed）
  - tc-P1: 订单创建后对应 Tier 权益余额正确减少
  - tc-P1: `usedEntitlementDetails` 结构包含 `tier` + `tierEntitlements`
  - **请求参数**:
    ```json
    {
      "module": 1,
      "membershipId": "{{分级权益的membershipId}}",
      "extra": {
        "prebookingToken": "{{token}}",
        "cashPaymentApplied": false,
        "toUseEntitlementCount": 1,
        "prebookingRequiredInfo": {
          "firstName": "Test",
          "lastName": "User",
          "email": "test@dragonpass.com",
          "phoneNumber": "1234567890",
          "callingCode": "44",
          "transportNumber": "EK0001"
        }
      }
    }
    ```
  - **预期响应**:
    ```json
    {
      "code": 0,
      "data": {
        "status": 1,
        "module": 1,
        "category": 2,
        "membershipId": "{{membershipId}}",
        "orderId": "{{orderId}}",
        "extra": {
          "usedEntitlementDetails": {
            "tier": {{tier}},
            "tierEntitlements": {
              "cardholderExclusiveEntitlements": 1,
              "guestsExclusiveEntitlements": 0,
              "sharedEntitlements": 0,
              "purchasedEntitlements": 0
            }
          }
        }
      }
    }
    ```

- tc-P2-ORDER-002：非分级权益（scopeType=1）场景，创建订单按默认 Tier1 扣减权益成功
  - tc-P2: HTTP 状态码为 200，`code` = 0
  - tc-P2: 扣减逻辑与分级场景一致，`tier` = 1

- tc-P1-ORDER-003：Fast Track 模块创建预约订单，Tier 权益扣减逻辑与 Lounge 一致
  - tc-P1: HTTP 状态码为 200，`code` = 0
  - tc-P1: 按资源所属 Tier 扣减权益
  - **请求参数**: `"module": 2`

### Tier 判定与扣减规则

#### 资源跨 Tier 场景

- tc-P2-ORDER-004：资源同时跨 2 个 Tier（配置问题），以最小 Tier 判断并扣减权益
  - tc-P2: 实际扣减的是最小 Tier 的权益
  - tc-P2: 较大 Tier 权益不受影响

#### 同 Tier 多权益场景

- tc-P2-ORDER-005：同一 Tier 下存在多条相同 Tier 权益（配错），权益相加后判断并扣减
  - tc-P2: 按相加后的总余额扣减
  - tc-P2: 扣减后各权益明细余额正确更新

#### 单 Tier 扣减限制

- tc-P2-ORDER-006：创建订单时仅扣除 1 个 Tier 的权益，不跨 Tier 扣除
  - tc-P2: 仅资源所属 Tier 的权益被扣减
  - tc-P2: 其他 Tier 权益余额不变
  - tc-P2: 调用 `/v2/entitlements/details` 验证仅目标 Tier 余额变化

### 权益不足场景

#### 异常场景验证

- tc-P1-ORDER-007：当前 Tier 权益不足且 `cashPaymentApplied` = false，创建订单失败
  - tc-P1: `code` = -1
  - tc-P1: 返回权益不足的错误提示
  - tc-P1: 权益数据未发生扣减
  - **请求参数**: `"toUseEntitlementCount": 10`（超出该 Tier 权益总余额）

- tc-P2-ORDER-008：当前 Tier 权益不足但 `cashPaymentApplied` = true，创建订单成功
  - tc-P2: `code` = 0
  - tc-P2: `cashPaymentApplied` = true
  - tc-P2: 权益部分扣减 + 现金支付部分

### SAAS 扣减执行

#### 系统集成验证

- tc-P2-ORDER-009：创建订单时权益扣减由 SAAS 执行，扣减后权益数据持久化正确
  - tc-P2: 订单创建成功后，调用 `/v2/entitlements/details` 查询目标 Tier 权益余额
  - tc-P2: 权益余额 = 原余额 - 扣减数量
  - tc-P2: 各权益类型（持卡人/携伴/共享/买点）扣减值与订单 `tierEntitlements` 一致

- tc-P2-ORDER-010：SAAS 扣减失败时，订单创建失败并回滚
  - tc-P2: `code` = -1
  - tc-P2: 权益数据未发生变化
  - tc-P2: 不出现订单已创建但权益未扣减的不一致状态

### 边界值验证

#### 特殊权益状态

- tc-P3-ORDER-011：该 Tier 仅剩 1 点权益，创建 1 人订单后余额归零
  - tc-P3: 订单创建成功
  - tc-P3: 扣减后该类型权益余额 = 0
  - tc-P3: 再次创建同 Tier 订单时失败（权益不足）

- tc-P3-ORDER-012：持卡人+多名宾客同时下单，各类型权益按优先级依次扣减

  | 持卡人专属余额 | 携伴专属余额 | 共享余额 | 买点余额 | 下单人数 | 预期扣减 |
  |--------------|------------|---------|---------|---------|---------|
  | 1 | 2 | 3 | 5 | 4 (1+3宾客) | 持卡人=1, 携伴=2, 共享=1, 买点=0 |
  | 0 | 0 | 2 | 3 | 3 (1+2宾客) | 持卡人=0, 携伴=0, 共享=2, 买点=1 |
  | 0 | 0 | 0 | 5 | 3 (1+2宾客) | 持卡人=0, 携伴=0, 共享=0, 买点=3 |

  - tc-P3: 各行场景下权益扣减符合上表预期
  - tc-P3: 扣减优先级：持卡人专属 → 携伴专属 → 共享 → 买点

### allowedGuestsPerUsage 规则（创建订单）

#### 宾客数量限制验证

- tc-P2-ORDER-013：创建订单时 `allowedGuestsPerUsage` 为 null，不限制携带宾客数量，下单成功
  - tc-P2: 携带多名宾客创建订单成功
  - tc-P2: 系统不因宾客数量返回限制错误
  - tc-P2: 权益按实际人数正确扣减

- tc-P2-ORDER-014：创建订单时 `allowedGuestsPerUsage` 有值，携带宾客数量超限，下单失败
  - tc-P2: `code` = -1，返回宾客数量超限的错误提示
  - tc-P2: 权益数据未发生扣减

#### 宾客数量判断数据来源

- tc-P2-ORDER-015：分级权益（scopeType=2）场景，宾客数量限制取 detail 级（Tier 级）`allowedGuestsPerUsage` 而非 membership 级汇总值
  - tc-P2: membership 级 `allowedGuestsPerUsage` 返回 null（分级场景下为 null）
  - tc-P2: 实际判断使用 `/v2/entitlements/details` 中对应 Tier 的 `allowedGuestsPerUsage` 值
  - tc-P2: 宾客数量未超过 Tier 级限制时下单成功

- tc-P2-ORDER-016：非分级权益（scopeType=1）场景，宾客数量限制取 membership 级 `allowedGuestsPerUsage`
  - tc-P2: membership 级 `allowedGuestsPerUsage` 有具体值
  - tc-P2: 宾客数量未超过该值时下单成功
  - tc-P2: 宾客数量超过该值时下单失败

### 订单取消 Tier 权益回退

#### 正向场景验证

- tc-P2-ORDER-017：取消 Tier 权益扣减的预约订单，对应 Tier 权益正确返还
  - tc-P2: 创建订单成功，Tier2 权益被扣减
  - tc-P2: 调用 `/v2/orders` PATCH 取消订单，`code` = 0
  - tc-P2: 取消后调用 `/v2/entitlements/details` 查询 Tier2 权益余额
  - tc-P2: Tier2 权益余额 = 取消前余额 + 订单扣减数量（完整返还）
  - tc-P2: 其他 Tier 权益余额不受影响

- tc-P2-ORDER-018：取消订单后各类型权益（持卡人/携伴/共享/买点）按原扣减明细逐项返还
  - tc-P2: 订单 `tierEntitlements` 中 `cardholderExclusiveEntitlements` = 1, `sharedEntitlements` = 1
  - tc-P2: 取消后持卡人专属余额 +1，共享余额 +1
  - tc-P2: 买点和携伴专属余额不受影响（原扣减为 0）

#### 异常场景验证

- tc-P2-ORDER-019：非分级权益（scopeType=1）场景取消订单，默认 Tier1 权益正确返还
  - tc-P2: 取消逻辑与分级场景一致
  - tc-P2: 权益返还到 Tier1（默认）



## 订单查询接口

### usedEntitlementDetails 新结构返回

#### 订单详情查询

- tc-P2-QUERY-001：通过 `/v2/orders/memberships/details` 查询已创建的 Tier 权益订单，`usedEntitlementDetails` 返回新结构
  - tc-P2: 响应 `usedEntitlementDetails` 包含 `tier` 字段
  - tc-P2: 响应 `usedEntitlementDetails` 包含 `tierEntitlements` 对象
  - tc-P2: `tierEntitlements` 四个字段值与创建订单时返回值一致
  - tc-P2: `purchasedEntitlements` 字段正确返回
  - **请求参数**:
    ```json
    {
      "membershipId": "{{membershipId}}",
      "orderId": "{{已创建的orderId}}"
    }
    ```

- tc-P2-QUERY-002：查询非分级权益（scopeType=1）场景创建的订单详情，`usedEntitlementDetails` 同样返回新结构
  - tc-P2: `tier` = 1（默认）
  - tc-P2: `tierEntitlements` 各字段正确反映扣减明细

#### 订单列表查询

- tc-P2-QUERY-003：通过 `/v2/orders/memberships` 查询订单列表，列表中订单的 `usedEntitlementDetails` 使用新结构
  - tc-P2: 列表中每条订单的 `usedEntitlementDetails` 包含 `tier` + `tierEntitlements`
  - tc-P2: 新旧订单混合场景下，新订单使用新结构，旧订单保持原结构（向后兼容）

- tc-P2-QUERY-004：取消订单后查询订单详情，`usedEntitlementDetails` 仍保留原扣减明细（记录历史）
  - tc-P2: 取消后的订单 `status` 变更为已取消
  - tc-P2: `usedEntitlementDetails` 中 `tier` 和 `tierEntitlements` 仍保留创建时的扣减值



## 预览与创建一致性

### 预览-下单数据一致性

#### 数据一致性验证

- tc-P1-CONSIST-001：预览订单与创建订单的 `usedEntitlementDetails` 结构和扣减结果一致
  - tc-P1: 使用同一 `prebookingToken` 先预览后创建
  - tc-P1: 预览返回的 `tier` 值 = 创建订单返回的 `tier` 值
  - tc-P1: 预览返回的 `tierEntitlements` 各字段值 = 创建订单返回的各字段值
  - **验证步骤**: 
    1. 调用预览接口获取 `usedEntitlementDetails`
    2. 调用创建订单接口
    3. 对比两次返回的 `usedEntitlementDetails`

- tc-P2-CONSIST-002：预览成功但创建订单前权益已被其他订单消耗完，创建失败
  - tc-P2: 预览时 `code` = 0
  - tc-P2: 在预览和创建之间，该 Tier 权益被其他操作扣减至不足
  - tc-P2: 创建订单时 `code` = -1，返回权益不足错误
  - tc-P2: 权益数据不会被错误扣减
