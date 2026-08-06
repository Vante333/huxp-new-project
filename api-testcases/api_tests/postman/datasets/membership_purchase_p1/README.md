# Membership Purchase P1 · Apifox 全量数据导入

## 推荐导入（name = 中文 Group）

文件：`apifox-dataset-business.csv`（UTF-8 BOM）

| 列 | 含义 |
|----|------|
| **name** | 中文 Group 名（与场景目录一致，勾选用） |
| **scenario_key** | 英文稳定键（对照用） |
| 业务列 | 券码/金额等；已有真值勿乱改；新增行 `FILL_*` 在 UI 填沙箱值 |

1. 删掉旧乱码行  
2. 导入本文件，编码选 **UTF-8**  
3. 不要用 Excel 打开另存后再导  

若中文仍乱码：改用 `apifox-dataset-business-ascii.csv`（name 为英文）。

对照表：`scenario-group-map.md`。
