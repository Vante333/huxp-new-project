# SWAP entitlement - phase 1

来源：<https://dragonpass.atlassian.net/wiki/spaces/DGSN/pages/1000898583/SWAP+entitlement+-+phase+1>

---

## 一、E-pass 与 swap entitlement 概述

目前在 E-pass 上只支持 lounge / setmeal / coupon（1，3，4）的 swap entitlement，暂不支持其他品类的 swap。

![](images/image-20251112-060333.png)

### 1.1 /v2/orders/{module}/ePasses

将 `{module}` 设为 `multiModule` 代表多品类可用：

`/v2/orders/multiModule/ePasses`

用 `"module": 0` 代表多品类 ePass，实际使用 `modules` 数组来控制品类，这个数组只有在 `module = 0` 的时候生效。如果判断为 swap，则 `module` 只允许输入 0。


```json
{
    "module": 0,//新增枚举
    "clientUserId": "3EF5D065-76F8-4D3E-801A-B329D15F461A",
    "extra": {
        "firstName": "DragonPass",
        "lastName": "DragonPass",
        "activationDate": "2028-10-31T23:59:59+00:00",
        "expirationDate": "2028-12-31T23:59:59+00:00",
        "availableUsages": 1,
        "allowedResources": {
            "resourceIds": []
        }
    }
}
```
swap的Epass，支持指定跨品类的resoureIds

swap 和单品类权益需要分为 2 个不同的 program 组，swap 的 program 组仅支持发放 swap，不兼容单品类。

在 SAAS 配置中，swap 的 program 需要额外配置一个新的会籍商品-会籍模板组，会籍模版下最多只会有 2 条权益明细：

![](images/image-20251023-063117.png)

休息室权益 + MPV，已经覆盖了 4 种场景：

![](images/image-20251117-025715.png)

**组合配置说明：**

| 组合                     | 管理项目                                   | ResourceIds              | Remark                                                                                      |
| ------------------------ | ------------------------------------------ | ------------------------ | ------------------------------------------------------------------------------------------- |
| 休息室 + Setmeal         | 一条【国际休息室】品类项目                | 可以指定 N + Rcode      | 权益模板关联【国际休息室】品类项目，勾选 SWAP + Setmeal 标签；【BOSS】网络范围配 Setmeal+休息室 |
| Setmeal + Coupon         | 一条【国际休息室】品类项目 + 一条【MPV】品类项目 | 可以指定 Rcode          | 权益模板关联【国际休息室】品类项目，勾选 Set Meal 标签，不勾选 SWAP 标签；【BOSS】网络范围只配 Setmeal |
| 休息室 + Coupon          | 一条【国际休息室】品类项目 + 一条【MPV】品类项目 | 可以指定 N + Rcode      | 权益模板关联【国际休息室】品类项目，无需勾选标签；【BOSS】网络范围只配休息室                      |
| 休息室 + Setmeal + Coupon | 一条【国际休息室】品类项目 + 一条【MPV】品类项目 | 可以指定 N + Rcode      | 权益模板关联【国际休息室】品类项目，勾选 SWAP + Setmeal 标签；【BOSS】网络范围配 Setmeal+休息室      |

如果只有 Setmeal 的权益，现在是给【国际休息室】品类的权益打一个 Set Meal 的标。

![](images/image-20251023-063204.png)

后面如果是休息室 + Setmeal SWAP 这种场景，一个项目支持 2 个品类，计划是打一个 SWAP 的标，告诉 API 这个条权益是休息室和 setmeal 共享的，相应地，在查询资源、展示订单时，都要根据实际使用的网点，来展示 module 和 Ncode/Rcode。

![](images/image-20251023-063155.png)

返回示例：


```json
{
  "code": 0,
  "data": {
    "status": 2,
    "module": 0,
    "category": 1,
    "clientUserId": "3EF5D065-76F8-4D3E-801A-B329D15F461A",
    "orderId": "DP00000000000001",
    "orderCreatedDate": "2024-12-31T00:00:00+00:00",
    "orderCancelledDate": null,
    "extra": {
      "ePassId": "1788000066668888",
      "ePassStatus": 0,
      "firstName": "DragonPass",
      "lastName": "DragonPass",
      "activationDate": "2028-10-31T23:59:59+00:00",
      "expirationDate": "2028-12-31T23:59:59+00:00",
      "availableUsages": 1,
      "usedUsages": 0,
      "allowedModules": [
            1,
            3
        ],//展示可用的module，只有在module=0时会返回
      "allowedResources": {
        "resourceIds": []
      }
    }
  }
}
```
category： 如果swap中有lounge则为3、如果没有lounge，则为1，单品类保持历史逻辑

moudle：判断为swap只能输入0，判断为单品类只允许输入对应品类得moudle值

### 1.2 /v2/orders/ePasses/search
```json
{
  "code": 0,
  "data": {
    "status": 2,
    "module": 0, //新增枚举
    "category": 1,
    "clientUserId": "3EF5D065-76F8-4D3E-801A-B329D15F461A",
    "orderId": "DP00000000000001",
    "orderCreatedDate": "2024-12-31T00:00:00+00:00",
    "orderCancelledDate": null,
    "extra": {
      "ePassId": "1788000066668888",
      "ePassStatus": 1,
      "firstName": "DragonPass",
      "lastName": "DragonPass",
      "activationDate": "2028-10-31T23:59:59+00:00",
      "expirationDate": "2028-12-31T23:59:59+00:00",
      "availableUsages": 0,
      "usedUsages": 1,
      "allowedModules": [
            1,
            3
        ],//展示可用的module，只有在module=0时会返回
      "allowedResources": {
        "resourceIds": [
          "N00001"
        ]
      }
    }
  }
}
```
### 1.3 /v2/orders/ePasses

展示逻辑不变，核销什么网点，就对应展示什么 module 和 Ncode/Rcode。

### 1.4 /v2/orders/ePasses/details

展示逻辑不变，核销什么网点，就对应展示什么 module 和 Ncode/Rcode。

### 1.5 资源相关接口

对于 swap entitlement 到会籍模板（program），同时支持对应品类的资源检索，包括：

- `/v2/resources`
- `/v2/resources/{resourceId}`
- `/v2/resources/updates`（回去跑一下日志，如果最近 30 天无人用，就下架）
- `/v2/transportHubs`
- `/v2/transportHubs/{transportHubId}`
- `/v2/search/modules`
- `/v2/search`

### 1.6 预订单创建与取消、下单前权益计算

目前saas没有接口计算某个品类现在一共还有多少权益，需要根据权益明细来计算

统计会籍下可用权益（初始/剩余）时，应该只统计待使用和已用完2个状态，不统计已作废/冻结/已过期的

订单取消：取消的话权益直接回退到对应明细，SaaS 负责，我们不用管。

### 1.7 错误提示语

| 错误码      | 场景说明                                                                 | 提示语（英文）                                                                                                                                        |
| ----------- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| 500.000.020 | 只有单品类权益，但是去下了跨品类的权益。不支持 swap entitlement          | Sorry, we’re unable to process your order at the moment. Please try again later or contact DragonPass support team.                                  |
| 500.xxx.010 | 跨品类会籍商品，在单品类 ePass 接口尝试创建单品类权益（如 `/lounges/ePasses`、`/fastTrack/ePasses` 等） | Sorry, we’re unable to process your order at the moment. Please try again later or contact DragonPass support team.                                  |
| 500.000.020 | 单品类会籍商品，在 `/crossModule/ePasses` 尝试创建跨品类权益             | Sorry, we’re unable to process your order at the moment. Please try again later or contact DragonPass support team.                                  |
| 500.xxx.010 | 只要是跨品类，在对应品类的 bundle 接口不能下对应品类的 bundle 单（`/v2/orders/{module}/ePasses/bundle`） | Sorry, we’re unable to process your order at the moment. Please try again later or contact DragonPass support team.                                  |
| 500.000.013 | 尝试下单该 ePass 不可用的网点                                            | Sorry, this resource is not accessible with your program.                                                                                             |
| 500.000.014 | `clientUserId` 重复                                                      | Sorry, this clientUserId already exists.                                                                                                              |
| 500.000.015 | ePass 过期时间早于激活时间                                               | Sorry, the expiration date cannot be earlier than the activation date.                                                                               |
| 500.000.016 | ePass 激活时间早于会籍模板生效时间                                       | Sorry, the activation date is earlier than the allowed start date.                                                                                   |
| 500.000.017 | `resourceId` 中传了非该接口对应品类的资源，例如创建 lounge ePass 时传了 Ccode | The 'resourceId' array contains resources that are not associated with the expected module. Please verify and ensure the resource IDs match the correct module. |
| 500.000.018 | `resourceId` 中传了超过 30 个资源 code                                   | The 'resourceId' array exceeds the maximum limit of 30 resource IDs. Please reduce the number of resource IDs and try again.                         |

## 二、Membership 接口

先不看 2.1 `/v2/entitlements/search`。

顶级结构：


```json
{
  "code": 0,
  "data": {
    "entitlements": {
      "moduleExclusiveEntitlements": [], //单品类权益列表
      "crossModuleEntitlements": [], //跨品类权益列表，只有存在swap的话才会出现这个object
      "enabledTypes": [1,2] //启用的权益类型
    }
  }
}
```

```json
"crossModuleEntitlements": [
  {
    "applicableModules": [1, 2, 3], // 跨休息室、快速安检、Set Meal
    "entitlementPoolId": "aaaa1234" //权益明细编码
    "details": {
      "cardholderExclusiveEntitlements": 2,
      "guestsExclusiveEntitlements": 1,
      "sharedEntitlements": 3
    }
  }
]
```
enabledTypes：

| 枚举 | 名称            | 说明           |
| ---- | --------------- | -------------- |
| 1    | moduleExclusive | 存在单品类权益 |
| 2    | crossModule     | 存在 swap 权益 |

2.2 /v2/entitlements/update

原来的入参，还是保留只更新moduleExclusiveEntitlements，返回也不变。


```json
{
  "membershipId": "8888000066668888",
  "quantity": 1,
  "module": 1,
  "usageRestriction": 1
}
```
如果要操作swap权益，则需要指定权益明细编码才能编辑


```json
{
  "membershipId": "8888000066668888",
  "quantity": 1,
  "module": 0,
  "entitlementPoolId": "aaaa1234", //需要指定权益明细编码才能编辑
  "usageRestriction": 1
}
```

```json
{
    "code": 0,
    "data": {
        "membershipId": "8888000066668888",
        "entitlements": {
            "moduleExclusiveEntitlements": [...],
            "crossModuleEntitlements": [], //跨品类权益列表，只有存在swap的话才会出现这个object
            "enabledTypes": [1,2] //启用的权益类型  
        }
    }
}
```
