# 会籍权益系统API需求文档

## 二、权益查询接口 (Entitlement Query)
**接口路径**: `/v2/entitlements/search`

### 2.1 新增买点字段规则
- 如果充值过才会有买点返回（充值过才会有充值的权益明细）
- 没充值过，没有明细，不返回`purchasedEntitlements`
- 买点都是共享点，因此在计算`maxGuestsNextUse`时需要加上买点作为共享点来计算

### 2.2 响应示例
```json
{
  "entitlements": {
    "moduleExclusiveEntitlements": [
      {
        "module": 1,
        "details": {
          "cardholderExclusiveEntitlements": 1,
          "guestsExclusiveEntitlements": 1,
          "sharedEntitlements": 0,
          "purchasedEntitlements": 0, // 新增买点字段
          "allowedGuestsPerUsage": 1,
          "maxGuestsNextUse": 1
        }
      }
    ]
  }
}
```

---

## 三、编辑权益接口 (Entitlement Update)
**接口路径**: `/v2/entitlements/update`

### 3.1 请求参数
- 新增`purchasedQuantity`字段，选填，代表买点

```json
{
  "membershipId": "8888000066668888",
  "module": 1,
  "usageRestriction": 1,
  "quantity": 1,
  "purchasedQuantity": 2 // 新增，修改买点
}
```

### 3.2 业务规则 (Business Rules)

#### 3.2.1 买点特性
- **Purchase entitlements are always shared and not controlled by usageRestriction field.**
  - 买点永远是共享的，不受`usageRestriction`控制

#### 3.2.2 充值模板校验
- **If there is no recharge template configured, purchase entitlements cannot be edited, and an error code must be provided.**
  - 没配充值模板（充值商品）不能编辑买点，需要给错误码
- **If there is no recharge template configured, it means purchase entitlements are not supported, and purchasedEntitlements will not be returned.**
  - 没配充值模板就是不支持买点，不返回`purchasedEntitlements`

#### 3.2.3 更新规则
- **Purchase entitlements and agent entitlement can only be updated separately, not simultaneously; simultaneous updates must provide an error code.**
  - 买点和权益点只能分开更新，不能同时更新，同时更新要给错误码

#### 3.2.4 计算规则
- **Purchase entitlements are all shared points, so when calculating maxGuestsNextUse, purchase points need to be added as shared points for the calculation.**
  - 买点都是共享点，因此在计算`maxGuestsNextUse`时需要加上买点作为共享点来计算

#### 3.2.5 数值限制
- **Purchase entitlements can also be increased or decreased, with an upper limit of 999 (invalid characters), and cannot be decreased to a negative number (500.030.012).**
  - 买点也可以加减，加上限限制为999（非法字符），减不能减到负数（500.030.012）

### 3.3 响应示例
```json
{
  "entitlements": {
    "moduleExclusiveEntitlements": [
      {
        "module": 1,
        "details": {
          "cardholderExclusiveEntitlements": 1,
          "guestsExclusiveEntitlements": 1,
          "sharedEntitlements": 0,
          "purchasedEntitlements": 0, // 新增买点字段
          "allowedGuestsPerUsage": 1,
          "maxGuestsNextUse": 1
        }
      }
    ]
  }
}
```

### 3.4 错误码定义

| 错误码 | 中文描述 | 英文描述 |
|--------|----------|----------|
| 500.030.024 | 没有权益明细（不支持买点） | Operation not allowed. Editing this type of entitlement is not supported based on the program settings. |
| 500.030.025 | 买点和权益点只能分开更新，不能同时更新 | Operation not allowed. Different types of entitlements must be updated separately. |
| 500.030.012 | 更新的权益不足 | Insufficient entitlement balance. The requested deduction exceeds the available entitlement. |
| 500.030.005 | 无法更新权益（兜底） | Sorry, we're unable to update the entitlements at the moment. Please try again later. |

---

## 四、升降级接口 (Change Membership Program)
**接口路径**: `/v2/memberships/programChange`

> **注意：这个部分先不做，等saas做完再做**

### 4.1 业务规则
- **Whether it's Strategy 1 or Strategy 2, if there is a purchased entitlement, it will be directly update to the new tier.**
  - 不管是权益策略1还是权益策略2，如果有买点，那都是直接带到新等级，没有重发这一说
- **If there is a purchased entitlement, the target level must also have a recharge template configured; otherwise, migration is not allowed.**
  - 如果有买点，目标等级也需要有买点模板，否则禁止迁移

### 4.2 当前限制
- 当前重发权益接口不支持买点，这个部分先不做，等saas做完再做

---

## 五、迁移新增的内部订单列表接口

### 5.1 接口列表
1. **内部订单列表接口**: `/v2/internal/orders/memberships`
2. **现有会籍使用订单详情接口**: `/v2/orders/memberships/details`

### 5.2 相关链接
- **JIRA任务**: https://dragonpass.atlassian.net/browse/PAPI-2199
- **参考文档**: 打开 "image-20260107-034016.png"

---

## 六、充值流程 (Recharge Process)

### 6.1 充值规则
- 充值需要通过充值商品实现，配合权益订单流
- 支付方式【项目支付】，实付金额可以先写0

### 6.2 参考文档
- 打开 "img_v3_02tv_78342617-a6d9-4e1c-9090-91271edd80dg-20260115-092608.jpg"

---

## 七、下单相关流程 (Order Process)

### 7.1 点数计算规则
- 检查可用性和下单时，当前逻辑会判断点数是否足够
- 新增充值点后，充值点当作权益共享点计算即可

### 7.2 影响接口列表

#### 下单接口：
1. `/v2/orders/***/memberships/prebooking` * 4
2. `/v2/orders/esims/memberships/topup`

#### 检查可用性接口：
- **文档链接**: https://apifox.dragonpass.com/apidoc/docs-site/6000000/3507440e0
- **接口路径**: `/v2/resources/options/prebookings/availability`

---

## 八、下单预览接口 (Order Preview)

### 8.1 接口列表
1. `/v2/orders/lounges/memberships/prebooking/preview`
2. `/v2/orders/fastTrack/memberships/prebooking/preview`

### 8.2 接口逻辑
- 入参逻辑不变，根据入参的点数信息，saas进行扣点判断
- 基于saas返回将结果填入`usedEntitlementDetails`中
- 新增`purchasedEntitlements`字段

### 8.3 响应示例
```json
{
  "code": 0,
  "data": {
    "module": 1,
    "category": 2,
    "membershipId": "8888000066668888",
    "extra": {
      "prebookingDate": "2025-10-01T10:30",
      "usedEntitlementDetails": {
        "cardholderExclusiveEntitlements": 1,
        "guestsExclusiveEntitlements": 0,
        "sharedEntitlements": 0,
        "purchasedEntitlements": 0 // 新增买点字段
      },
      "cashPaymentApplied": false,
      "resourceId": "N00001",
      "resourceName": "DragonPass Lounge"
    }
  }
}
```

---

## 总结

### 核心变更点
1. **新增买点字段**: `purchasedEntitlements`（仅在充值后返回）
2. **编辑接口扩展**: 支持买点的单独编辑
3. **计算规则调整**: 买点作为共享点参与`maxGuestsNextUse`计算
4. **业务限制**: 必须配置充值模板才能支持买点功能

### 实施阶段
1. **第一阶段**: 会籍注册、权益查询、编辑权益接口（立即实施）
2. **第二阶段**: 升降级接口（等待saas完成）
3. **第三阶段**: 订单相关接口和充值流程（配合整体系统升级）

### 注意事项
1. 所有买点操作都需要先检查充值模板配置
2. 买点和权益点必须分开更新
3. 买点数值有上限限制（999）和负数保护
4. 当前重发权益接口暂不支持买点功能