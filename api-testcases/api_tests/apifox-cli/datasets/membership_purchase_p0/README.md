# Membership Purchase P0 · Apifox 全量数据导入

## 推荐导入（name = 中文 Group）

文件：`apifox-dataset-business.csv`（UTF-8 BOM）

| 列 | 含义 |
|----|------|
| **name** | 中文 Group 名（与场景目录一致，勾选用） |
| **scenario_key** | 英文稳定键（对照用） |
| 业务列 | 券码/金额等；已有真值勿乱改；`FILL_*` 在 UI 填沙箱值 |

1. 导入本文件，编码选 **UTF-8**
2. 不要用 Excel 打开另存后再导
3. 鉴权仍用 `MP_P0_*` 或独立鉴权数据集（勿混进本业务 CSV）

若中文乱码：改用 `apifox-dataset-business-ascii.csv`（name 为英文）。

对照表：`scenario-group-map.md`。

## 场景行

| scenario_key | Group |
|---|---|
| `_FULL_SUITE` | 全量并集 |
| `pos_b_no_coupon` | 商品 B 无券原价 |
| `pos_a_intro_currency_configured` | 商品 A 引导期 · 币种已配置 |
| `pos_a_no_intro_currency_configured` | 商品 A 未开引导期 · 币种已配置 |
