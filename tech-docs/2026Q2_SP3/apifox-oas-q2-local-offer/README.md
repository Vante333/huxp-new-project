# Q2 Local Offer — Apifox OpenAPI 快照

- **来源 MCP**：`Q2 local offer`（Apifox ProjectId `345747`，BranchId `309401`）
- **拉取时间**：2026-05-25T03:17:27.872Z
- **OpenAPI**：DragonPass API Developer Platform v1.0.0
- **接口总数**：61
- **Local Offer / E-pass 相关**：11

## Local Offer / E-pass 相关接口

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| GET | `/v2/resources/localOffers/{resourceId}/options` | Retrieve Local Offer Resouces Options |
| GET | `/v2/resources/localOffers/{resourceId}/options/{optionId}` | Retrieve Local Offer Resource Option Details |
| POST | `/v2/users/ePasses` | Retrieve User E-passes List |
| POST | `/v2/orders/localOffers/memberships/prebooking` | Create Membership Prebooking Order - Local Offer |
| POST | `/v2/orders/{module}/ePasses` | Create E-pass Order |
| POST | `/v2/orders/ePasses/search` | Retrieve E-pass Details |
| POST | `/v2/orders/{module}/ePasses/prebooking` | Create E-pass Prebooking Order - Local Offer |
| POST | `/v2/orders/{module}/ePasses/bundle` | Create E-pass with Prebooking Order - Local Offer |
| POST | `/v2/orders/esims/ePasses/topup` | Top up eSIM data package - E-pass |
| POST | `/v2/orders/ePasses` | Retrieve E-pass Order List |
| POST | `/v2/orders/ePasses/details` | Retrieve E-pass Usage Order Details |

## 已落盘 $ref 明细文件

- `/paths/_v2_orders.json`
- `/paths/_v2_orders_%7Bmodule%7D_ePasses.json`
- `/paths/_v2_orders_%7Bmodule%7D_ePasses_bundle.json`
- `/paths/_v2_orders_%7Bmodule%7D_ePasses_prebooking.json`
- `/paths/_v2_orders_%7Bmodules%7D_memberships_prebooking_preview.json`
- `/paths/_v2_orders_ePasses.json`
- `/paths/_v2_orders_ePasses_details.json`
- `/paths/_v2_orders_ePasses_search.json`
- `/paths/_v2_orders_localOffers_memberships_prebooking.json`
- `/paths/_v2_resources_localOffers_%7BresourceId%7D_options.json`
- `/paths/_v2_resources_localOffers_%7BresourceId%7D_options_%7BoptionId%7D.json`
- `/paths/_v2_resources_options_prebookings_availability.json`
- `/paths/_v2_resources_options_prices.json`
- `/paths/_v2_resources_prebookings_availability.json`
- `/paths/_v2_resources_prices.json`
- `/paths/_v2_users_ePasses.json`

## 全量接口索引

| 方法 | 路径 | 摘要 |
| --- | --- | --- |
| POST | `/v2/auth/token` | Generate Access Token |
| POST | `/v2/search` | Aggregated Search by Keyword |
| GET | `/v2/search/modules` | Retrieve Available Modules by Location |
| GET | `/v2/transportHubs` | Retrieve Transport Hub |
| GET | `/v2/transportHubs/{transportHubId}` | Retrieve Transport Hub Details |
| GET | `/v2/resources` | Retrieve Resources List |
| GET | `/v2/resources/{resourceId}` | Retrieve Resource Details |
| POST | `/v2/resources/prebookings/availability` | Check Prebooking Resource Availability |
| POST | `/v2/resources/options/prebookings/availability` | Check Prebooking Option Availability |
| GET | `/v2/resources/fitness/{resourceId}/options/{optionId}` | Retrieve Fitness Resource Option Details |
| GET | `/v2/resources/fitness/{resourceId}/schedule` | Retrieve Fitness Resources Schedule |
| GET | `/v2/resources/esims/{resourceId}/options/{optionId}` | Retrieve eSIM Resource Option Details |
| GET | `/v2/resources/esims/{resourceId}/options` | Retrieve eSIM Resouces Options |
| GET | `/v2/resources/localOffers/{resourceId}/options` | Retrieve Local Offer Resouces Options |
| GET | `/v2/resources/localOffers/{resourceId}/options/{optionId}` | Retrieve Local Offer Resource Option Details |
| POST | `/v2/resources/prices` | Retrieve Resource Pricing Information |
| POST | `/v2/resources/options/prices` | Retrieve Prebooking Option Pricing Information |
| POST | `/v2/users` | User Creation |
| POST | `/v2/users/update` | Update User Information |
| POST | `/v2/users/delete` | Delete A User |
| POST | `/v2/users/search` | Retrieve User Information |
| POST | `/v2/users/memberships` | Retrieve User Memberships List |
| POST | `/v2/users/ePasses` | Retrieve User E-passes List |
| POST | `/v2/memberships` | Membership Registration(注册会籍) |
| POST | `/v2/memberships/update` | Update A Membership |
| POST | `/v2/memberships/search` | Retrieve Membership Information 查询会籍 |
| POST | `/v2/memberships/qrCodes` | Generate Membership Dynamic QR Codes |
| POST | `/v2/entitlements/update` | Update Membership Entitlements (权益更新) |
| POST | `/v2/entitlements/search` | Retrieve Membership Entitlement Summary(权限概览（不支持tier，不支持swap）) |
| POST | `/v2/orders/{modules}/memberships/prebooking/preview` | Preview Membership Prebooking Order |
| POST | `/v2/orders/lounges/memberships/prebooking` | Create Membership Prebooking Order - Lounge |
| POST | `/v2/orders/fastTrack/memberships/prebooking` | Create Membership Prebooking Order - Fast Track |
| POST | `/v2/orders/fitness/memberships/prebooking` | Create Membership Prebooking Order - Fitness |
| POST | `/v2/orders/esims/memberships/topup` | Top up eSIM data package - Membership |
| POST | `/v2/orders/localOffers/memberships/prebooking` | Create Membership Prebooking Order - Local Offer |
| PATCH | `/v2/orders` | Cancel an Order |
| POST | `/v2/orders/memberships` | Retrieve Membership Order List(查询membership订单列表) |
| POST | `/v2/orders/memberships/details` | Retrieve Membership Usage Order Details(查询membership订单详情) |
| POST | `/v2/orders/fitness/checkin` | Fitness Order Check-In |
| POST | `/v2/orders/esims/details` | Retrieve eSIM Order Live Extended Details |
| POST | `/v2/orders/esims/topup/availability` | Check eSIM Top-up Availability |
| POST | `/v2/orders/esims/packages/query` | Retrieve eSIM Data Packages |
| POST | `/v2/orders/{module}/ePasses` | Create E-pass Order |
| POST | `/v2/orders/ePasses/search` | Retrieve E-pass Details |
| POST | `/v2/orders/{module}/ePasses/prebooking` | Create E-pass Prebooking Order - Local Offer |
| POST | `/v2/orders/{module}/ePasses/bundle` | Create E-pass with Prebooking Order - Local Offer |
| POST | `/v2/orders/esims/ePasses/topup` | Top up eSIM data package - E-pass |
| POST | `/v2/orders/ePasses` | Retrieve E-pass Order List |
| POST | `/v2/orders/ePasses/details` | Retrieve E-pass Usage Order Details |
| GET | `/v2/event` | Push Event Recovery |
| POST | `/v2/simulations/lounges/redemptions` | Simulate Lounge Redemption - Walk in |
| POST | `/v2/simulations/lounges/prebookings/redemptions` | Simulate Lounge Redemption - Prebooking |
| POST | `/v2/simulations/lounges/cancellation` | Simulate Lounge Order Cancellation |
| POST | `/v2/simulations/setMeals/redemptions` | Simulate Set Meal Redemption - Walk in |
| POST | `/v2/simulations/setMeals/cancellation` | Simulate Set Meal Order Cancellation |
| POST | `/v2/simulations/coupons/redemptions` | Simulate Dining Coupon Redemption - Walk in |
| POST | `/v2/simulations/coupons/cancellation` | Simulate Dining Coupon Order Cancellation |
| POST | `/v2/simulations/fastTrack/prebookings/redemptions` | Simulate Fast Track Redemption - Prebooking |
| POST | `/v2/simulations/fastTrack/cancellation` | Simulate Fast Track Order Cancellation |
| POST | `/v2/entitlements/details` | Retrieve Membership Entitlement Detalis(权益明细（不支持tier，不支持swap）) |
| POST | `/v2/orders/esims/memberships/prebooking` | Create Membership Prebooking Order - lo(创建LO订单) |
