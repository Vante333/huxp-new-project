# 接口自动化主调用链说明

## 说明

本文只描述接口之间的调用依赖关系，不包含业务实现流程。

默认 `clientUserId`、`resourceId`、`module`、租户、`Program`、鉴权信息已作为前置数据准备好。

本文不包含创建用户、查询资源列表等测试数据准备接口。

后续新增或扩展接口自动化时，应先读取本文，再设计 Apifox CLI 生成器步骤序与 Tests（正式验收单轨）；冻结的 pytest 仅作历史对照。

## 一、Membership 主链路

### 1. Membership 创建验证链

```text
POST /v2/memberships
-> 入参 clientUserId
-> 取 membershipId

POST /v2/memberships/search
-> 入参 membershipId
-> 校验 membership 详情

POST /v2/users/memberships
-> 入参 clientUserId
-> 校验用户会籍列表包含 membershipId
```

字段流转：

```text
clientUserId -> /v2/memberships -> membershipId
membershipId -> /v2/memberships/search
clientUserId -> /v2/users/memberships
```

### 2. Membership Prebooking 链

```text
POST /v2/memberships
-> 入参 clientUserId
-> 取 membershipId

POST /v2/resources/prebookings/availability
-> 入参 membershipId + module + resourceId
-> 取 prebookingToken

POST /v2/orders/{module}/memberships/prebooking
-> 入参 membershipId + prebookingToken
-> 取 orderId

POST /v2/orders/memberships/details
-> 入参 orderId
-> 校验订单详情

POST /v2/orders/memberships
-> 入参 membershipId
-> 校验订单列表包含 orderId
```

字段流转：

```text
clientUserId -> /v2/memberships -> membershipId
membershipId + module + resourceId -> /v2/resources/prebookings/availability -> prebookingToken
membershipId + prebookingToken -> /v2/orders/{module}/memberships/prebooking -> orderId
orderId -> /v2/orders/memberships/details
membershipId -> /v2/orders/memberships
```

`{module}` 对应接口示例：

```text
POST /v2/orders/lounges/memberships/prebooking
POST /v2/orders/fastTrack/memberships/prebooking
POST /v2/orders/fitness/memberships/prebooking
POST /v2/orders/esims/memberships/prebooking
POST /v2/orders/localOffers/memberships/prebooking
```

### 3. Membership 订单查询链

```text
POST /v2/users/memberships
-> 入参 clientUserId
-> 取 membershipId

POST /v2/orders/memberships
-> 入参 membershipId
-> 取 orderId

POST /v2/orders/memberships/details
-> 入参 orderId
-> 校验订单详情
```

字段流转：

```text
clientUserId -> /v2/users/memberships -> membershipId
membershipId -> /v2/orders/memberships -> orderId
orderId -> /v2/orders/memberships/details
```

### 4. Membership 首次购买链（含取消订阅）

```text
POST /v2/orders/memberships/purchase/preview
-> 入参 appId + autoRenewal + profile.email
-> 校验算价

POST /v2/orders/memberships/purchase
-> 入参同 Preview
-> 取 orderId；若响应含 membershipId 则保存

POST /v2/memberships/subscriptions/cancellation
-> 入参 membershipId + email（须与 Create 注册一致）
-> 校验取消订阅或归属/无有效计划拒绝

POST /v2/orders/memberships/purchase/details
-> 入参 orderId
-> 校验购买单详情
```

字段流转：

```text
profile.email -> /v2/orders/memberships/purchase -> orderId + membershipId（支付前可能尚未发放）
membershipId + email -> /v2/memberships/subscriptions/cancellation
orderId -> /v2/orders/memberships/purchase/details
```

## 二、EPass 主链路

说明：EPass 没有单独的 `/v2/ePasses` 创建接口。EPass 通过 `/v2/orders/{module}/ePasses` 创建。创建成功后返回 `ePassId`，后续再使用 `ePassId` 查询用户 EPass 列表、订单列表或创建 prebooking。

### 1. EPass 创建验证链

```text
POST /v2/orders/{module}/ePasses
-> 入参 clientUserId + module + resourceId
-> 创建 EPass
-> 取 ePassId + orderId

POST /v2/users/ePasses
-> 入参 clientUserId
-> 校验用户 EPass 列表包含 ePassId

POST /v2/orders/ePasses
-> 入参 ePassId
-> 校验 EPass 订单列表包含 orderId

POST /v2/orders/ePasses/details
-> 入参 orderId
-> 校验订单详情
```

字段流转：

```text
clientUserId + module + resourceId -> /v2/orders/{module}/ePasses -> ePassId + orderId
clientUserId -> /v2/users/ePasses
ePassId -> /v2/orders/ePasses
orderId -> /v2/orders/ePasses/details
```

`{module}` 对应创建 EPass 接口示例：

```text
POST /v2/orders/lounges/ePasses
POST /v2/orders/fastTrack/ePasses
POST /v2/orders/setMeals/ePasses
POST /v2/orders/coupons/ePasses
POST /v2/orders/esims/ePasses
POST /v2/orders/fitness/ePasses
POST /v2/orders/multiModule/ePasses
```

### 2. EPass Prebooking 链

```text
POST /v2/orders/{module}/ePasses
-> 入参 clientUserId + module + resourceId
-> 创建 EPass
-> 取 ePassId

POST /v2/resources/prebookings/availability
-> 入参 ePassId + module + resourceId
-> 取 prebookingToken

POST /v2/orders/{module}/ePasses/prebooking
-> 入参 ePassId + prebookingToken
-> 取 orderId

POST /v2/orders/ePasses/details
-> 入参 orderId
-> 校验订单详情

POST /v2/orders/ePasses
-> 入参 ePassId
-> 校验订单列表包含 orderId
```

字段流转：

```text
clientUserId + module + resourceId -> /v2/orders/{module}/ePasses -> ePassId
ePassId + module + resourceId -> /v2/resources/prebookings/availability -> prebookingToken
ePassId + prebookingToken -> /v2/orders/{module}/ePasses/prebooking -> orderId
orderId -> /v2/orders/ePasses/details
ePassId -> /v2/orders/ePasses
```

`{module}` 对应接口示例：

```text
POST /v2/orders/lounges/ePasses/prebooking
POST /v2/orders/fastTrack/ePasses/prebooking
POST /v2/orders/fitness/ePasses/prebooking
POST /v2/orders/esims/ePasses/prebooking
```

### 3. EPass Bundle 链

说明：Bundle 链用于一次性创建 EPass 并创建预订单。

```text
POST /v2/resources/prebookings/availability
-> 入参 clientUserId + module + resourceId
-> 取 prebookingToken

POST /v2/orders/{module}/ePasses/bundle
-> 入参 clientUserId + prebookingToken
-> 创建 EPass + 创建预订单
-> 取 ePassId + orderId

POST /v2/users/ePasses
-> 入参 clientUserId
-> 校验用户 EPass 列表包含 ePassId

POST /v2/orders/ePasses/details
-> 入参 orderId
-> 校验订单详情

POST /v2/orders/ePasses
-> 入参 ePassId
-> 校验订单列表包含 orderId
```

字段流转：

```text
clientUserId + module + resourceId -> /v2/resources/prebookings/availability -> prebookingToken
clientUserId + prebookingToken -> /v2/orders/{module}/ePasses/bundle -> ePassId + orderId
clientUserId -> /v2/users/ePasses
orderId -> /v2/orders/ePasses/details
ePassId -> /v2/orders/ePasses
```

`{module}` 对应接口示例：

```text
POST /v2/orders/lounges/ePasses/bundle
POST /v2/orders/fastTrack/ePasses/bundle
POST /v2/orders/fitness/ePasses/bundle
POST /v2/orders/esims/ePasses/bundle
```

## 三、ESIM 独立链路

### 1. ESIM EPass Topup 链

```text
POST /v2/orders/esims/ePasses
-> 入参 clientUserId + module + resourceId
-> 创建 ESIM EPass
-> 取 ePassId

POST /v2/orders/esims/ePasses/prebooking
-> 入参 ePassId
-> 取 iccid / orderId

POST /v2/orders/esims/topup/availability
-> 入参 ePassId + iccid
-> 取 prebookingToken

POST /v2/orders/esims/ePasses/topup
-> 入参 ePassId + prebookingToken
-> 取 topupOrderId

POST /v2/orders/esims/packages/query
-> 入参 ePassId + iccid
-> 校验 package 信息
```

字段流转：

```text
clientUserId + module + resourceId -> /v2/orders/esims/ePasses -> ePassId
ePassId -> /v2/orders/esims/ePasses/prebooking -> iccid / orderId
ePassId + iccid -> /v2/orders/esims/topup/availability -> prebookingToken
ePassId + prebookingToken -> /v2/orders/esims/ePasses/topup -> topupOrderId
ePassId + iccid -> /v2/orders/esims/packages/query
```

### 2. ESIM Membership Topup 链

```text
POST /v2/memberships
-> 入参 clientUserId
-> 取 membershipId

POST /v2/orders/esims/memberships/prebooking
-> 入参 membershipId
-> 取 iccid / orderId

POST /v2/orders/esims/topup/availability
-> 入参 membershipId + iccid
-> 取 prebookingToken

POST /v2/orders/esims/memberships/topup
-> 入参 membershipId + prebookingToken
-> 取 topupOrderId

POST /v2/orders/esims/packages/query
-> 入参 membershipId + iccid
-> 校验 package 信息
```

字段流转：

```text
clientUserId -> /v2/memberships -> membershipId
membershipId -> /v2/orders/esims/memberships/prebooking -> iccid / orderId
membershipId + iccid -> /v2/orders/esims/topup/availability -> prebookingToken
membershipId + prebookingToken -> /v2/orders/esims/memberships/topup -> topupOrderId
membershipId + iccid -> /v2/orders/esims/packages/query
```

## 四、主链路汇总

| 链路 | 接口顺序 |
| --- | --- |
| Membership 创建验证 | `/v2/memberships` -> `/v2/memberships/search` -> `/v2/users/memberships` |
| Membership Prebooking | `/v2/memberships` -> `/v2/resources/prebookings/availability` -> `/v2/orders/{module}/memberships/prebooking` -> `/v2/orders/memberships/details` -> `/v2/orders/memberships` |
| Membership 订单查询 | `/v2/users/memberships` -> `/v2/orders/memberships` -> `/v2/orders/memberships/details` |
| EPass 创建验证 | `/v2/orders/{module}/ePasses` -> `/v2/users/ePasses` -> `/v2/orders/ePasses` -> `/v2/orders/ePasses/details` |
| EPass Prebooking | `/v2/orders/{module}/ePasses` -> `/v2/resources/prebookings/availability` -> `/v2/orders/{module}/ePasses/prebooking` -> `/v2/orders/ePasses/details` -> `/v2/orders/ePasses` |
| EPass Bundle | `/v2/resources/prebookings/availability` -> `/v2/orders/{module}/ePasses/bundle` -> `/v2/users/ePasses` -> `/v2/orders/ePasses/details` -> `/v2/orders/ePasses` |
| ESIM EPass Topup | `/v2/orders/esims/ePasses` -> `/v2/orders/esims/ePasses/prebooking` -> `/v2/orders/esims/topup/availability` -> `/v2/orders/esims/ePasses/topup` -> `/v2/orders/esims/packages/query` |
| ESIM Membership Topup | `/v2/memberships` -> `/v2/orders/esims/memberships/prebooking` -> `/v2/orders/esims/topup/availability` -> `/v2/orders/esims/memberships/topup` -> `/v2/orders/esims/packages/query` |

## 五、核心字段依赖

### `clientUserId`

来源：自动化前置测试数据。

后续使用：

```text
/v2/memberships
/v2/orders/{module}/ePasses
/v2/users/memberships
/v2/users/ePasses
```

### `membershipId`

来源：

```text
/v2/memberships
/v2/users/memberships
```

后续使用：

```text
/v2/memberships/search
/v2/resources/prebookings/availability
/v2/orders/{module}/memberships/prebooking
/v2/orders/memberships
```

### `ePassId`

来源：

```text
/v2/orders/{module}/ePasses
/v2/users/ePasses
```

后续使用：

```text
/v2/resources/prebookings/availability
/v2/orders/{module}/ePasses/prebooking
/v2/orders/ePasses
```

### `prebookingToken`

来源：

```text
/v2/resources/prebookings/availability
/v2/orders/esims/topup/availability
```

后续使用：

```text
/v2/orders/{module}/memberships/prebooking
/v2/orders/{module}/ePasses/prebooking
/v2/orders/{module}/ePasses/bundle
/v2/orders/esims/ePasses/topup
/v2/orders/esims/memberships/topup
```

### `orderId`

来源：

```text
创建订单接口
预订单接口
```

后续使用：

```text
/v2/orders/memberships/details
/v2/orders/ePasses/details
```

### `iccid`

来源：

```text
/v2/orders/esims/ePasses/prebooking
/v2/orders/esims/memberships/prebooking
```

后续使用：

```text
/v2/orders/esims/topup/availability
/v2/orders/esims/packages/query
```

## 六、Local Offers 只读查询链

### 1. Local Offers options 查询链

```text
GET /v2/resources/localOffers/{resourceId}/options
-> 入参 resourceId
-> 可选 query: duration + pageSize + pageNumber + language
-> 校验 pagination + resourceId + resourceName + optionList
```

字段流转：

```text
resourceId -> /v2/resources/localOffers/{resourceId}/options -> data.resourceId
pageSize + pageNumber -> pagination.pageSize + pagination.pageNumber
optionList[*].optionId -> 后续 /v2/resources/localOffers/{resourceId}/options/{optionId}
```

说明：该接口为只读查询，不负责创建 Local Offer 资源。canary 正向验证依赖 `DP_LOCAL_OFFER_RESOURCE_ID` 指向已有可用资源；若返回 `code=-1 / errCode=500.020.016`，自动化应 skip 正向契约校验，并继续保留鉴权、缺 Program、未知 resourceId 等负向验证。
