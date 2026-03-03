# 【Migration】New order list endpoint for Oversea/Revolut 【V2】

**JIRA**: [PAPI-2199](https://dragonpass.atlassian.net/browse/PAPI-2199)

---

当前Revolut订单列表返回如下，会存在订单权益明细、使用时间、tier等信息。而我们目前的`/v2/orders/memberships`是没这些字段。

此外，Oversea的Ecert订单列表接口还缺少了`visitTime`字段。

因此需要新增2个单独接口，给迁移项目使用

```
{
    "state": "1",
    "msg": null,
    "errorCode": null,
    "result": {
        "customerId": "04570730910080612840", //项目处理
        "totalRecords": 1, //总页数
        "usageHistory": [
            {
                "dpid": "1720404662662451", //membershipId
                "airportCode": "A10052", //transportHubId
                "airportName": "Hong Kong International Airport", //transportHubName
                "iso2": "HK", //countryOrRegion
                "benefitTypeName": "Lounge", //module
                "memberType": "C", //项目处理
                "benefitTypeId": "1", //module+网络分组判断，缺少
                "code": "N02661", //resourceId
                "name": "Plaza Premium First", //resourceName
                "dateTimeUsed": "2025-12-10T19:02:35.000+08:00", //缺少
                "qtyUsed": 1, //passengerCounts
                "usageType": "R", //category
                "status": 0, //status
                "usageChargeDetail": {
                    "agentPoint": 1,
                    "buyPoint": 0
                }, //缺少
                "orderNo": "72512109794970" //orderId
            }
        ]
    }
}
```

## 新接口一，内部membership订单列表接口

`/v2/internal/orders/memberships`

在原来的接口上新增tier、usageDate、usedEntitlementDetails

```
{
    "code": 0,
    "data": {
        "Pagination": {
            "pageSize": 10,
            "pageNumber": 1,
            "totalNumber": 3
        },
        "orders": [
            {
                "orderId": "DP00000000000001",
                "status": 1,
                "module": 1,
                "category": 1,
                "passengerCounts": {
                    "cardholder": 1,
                    "guests": 1
                },
                "usedEntitlementDetails": {
                    "cardholderExclusiveEntitlements": 1,
                    "guestsExclusiveEntitlements": 1,
                    "sharedEntitlements": 0,
                    "purchasedEntitlements": 0
                }, //新增object字段，也是详情里来的
                "orderCreatedDate": "2024-12-01T00:00:00+00:00",
                "usageDate": "2024-12-31T00:00:00+00:00", //新增使用时间字段，当地，与details一致
                "resourceId": "N00001",
                "resourceName": "DragonPass Lounge",
                "image": "https://image.dragonpass.com/uploadFile/images/cover.png",
                "extra": {
                    "optionId": null,
                    "optionName": null,
                    "transportHubId": "A00001",
                    "transportHubName": "Manchester Airport",
                    "city": "Manchester",
                    "countryOrRegion": "GB",
                    "tier": 1 //新增tier字段，对应资源等级，目前写死1，后续再处理这个逻辑
                }
            }
        ]
    }
}
```

## 新接口而，内部Epass订单列表接口

`/v2/internal/orders/ePasses`

只新增usageDatedate字段

```
{
    "code": 0,
    "data": {
        "Pagination": {
            "pageSize": 10,
            "pageNumber": 1,
            "totalNumber": 3
        },
        "orders": [
            {
                "orderId": "DP00000000000001",
                "status": 1,
                "usedUsages": 1,
                "module": 1,
                "category": 1,
                "orderCreatedDate": "2024-12-01T00:00:00+00:00",
                "usageDate": "2024-12-31T00:00:00+00:00", //新增使用时间字段，与details一样
                "resourceId": "N00001",
                "resourceName": "DragonPass Lounge",
                "image": "https://image.dragonpass.com/uploadFile/images/cover.png",
                "extra": {
                    "optionId": null,
                    "optionName": null,
                    "transportHubName": "Manchester Airport",
                    "transportHubId": "A00001",
                    "city": "Manchester",
                    "countryOrRegion": "GB"
                }
            }
        ]
    }
}
```

**以下忽视**

备注：返回字段多于Generic API原订单列表，因此需要新增一个订单列表接口给迁移项目使用，目前缺少：

**Revolut**

**API**

**Remark**

dateTimeUsed

usageDate

缺时区，api处理或saas拼接

usageChargeDetail

待新增

权益使用明细，saas接口已有字段，但数据库没细分，需要确认

接口：`page/orderInfoMq`

benefitTypeId

tier

做完premium lounge后会有，需要saas 提供
