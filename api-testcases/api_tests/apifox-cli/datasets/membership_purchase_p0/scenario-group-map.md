# 数据集 name（中文）↔ scenario_key

Apifox 全量数据 **name** 列已用中文 Group 名；`scenario_key` 为稳定英文键。

| name（中文 Group） | scenario_key | 类型 |
|---|---|---|
| 全量并集（填齐后勾选本行跑整场景） | `_FULL_SUITE` | full |
| 不传券选择默认项目配置中的首个商品并按首月原价预览(EUR) | `pos_b_no_coupon` | positive |
| 【币种·已配置】商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，开启引导期阶段计费，activationMethod=1） | `pos_a_intro_currency_configured` | positive |
| 【币种·已配置】商品A支持订阅时autoRenewal为true使用阶段价（传couponCode，未开启引导期阶段计费，activationMethod=2）-原价计算 | `pos_a_no_intro_currency_configured` | positive |

