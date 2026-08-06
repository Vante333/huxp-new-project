# 数据集 name（中文）↔ scenario_key

Apifox 全量数据 **name** 列已用中文 Group 名；`scenario_key` 为稳定英文键。

| name（中文 Group） | scenario_key | 类型 |
|---|---|---|
| 全量并集（填齐后勾选本行跑整场景） | `_FULL_SUITE` | full |
| 不传券选择默认商品B并按首月原价预览(EUR) | `pos_b_no_coupon` | positive |
| 商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，开启引导期阶段计费，activationMethod=1） | `pos_a_intro` | positive |
| 商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，未开启引导期阶段计费，activationMethod=2）-原价计算 | `pos_a_no_intro` | positive |
| 再次调用Payments获取新支付链接 | `pos_payments_retry` | positive |
| 商品A不支持订阅且autoRenewal为false时按A原价预览（传couponCode） | `neg_a_no_sub_ar_false` | negative |
| 商品A支持订阅但autoRenewal为false时按A原价预览（传couponCode） | `neg_a_sub_off_ar_false` | negative |
| 不传券选择商品B但autoRenewal为true回兜底错误 | `neg_b_ar_true` | negative |
| 商品A不支持订阅但autoRenewal为true时返回兜底错误（传couponCode） | `neg_a_no_sub_ar_true` | negative |
| 优惠券不存在Preview按原价且详情为空（传couponCode） | `neg_coupon_not_found` | negative |
| 已过期周期优惠券Preview结构符合最终约定（传couponCode） | `neg_coupon_expired` | negative |
| 非周期优惠券Preview按原价且详情为空（传couponCode） | `neg_coupon_wrong_type` | negative |
| 有效但不满足条件优惠券保留详情并按原价（传couponCode），例如优惠券未在使用有效期内 | `neg_coupon_ineligible` | negative |
| 已有生效订阅用户重复购买被拒绝 | `neg_dup_subscription` | negative |
| Preview必填Body字段缺失或null均拒绝 | `neg_preview_required_body` | negative |
| Preview字段类型与枚举错误均拒绝 | `neg_preview_type_enum` | negative |
| Preview的email必填且clientUserId选填（支持同时入参） | `pos_preview_email_required` | positive |
| Create必填字段和类型边界校验 | `neg_create_required_type` | negative |
| Details_orderId必填与类型校验 | `neg_details_order_id` | negative |
| Payments/Details 缺 orderId | `neg_payments_details` | negative |

