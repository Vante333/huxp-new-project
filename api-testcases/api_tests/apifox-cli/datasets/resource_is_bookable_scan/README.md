# Resource isBookable Scan · Apifox 全量数据导入

## 推荐导入（name = 中文 Group）

文件：`apifox-dataset-business.csv`（UTF-8 BOM）

| 列 | 含义 |
|----|------|
| **name** | 中文 Group 名（与场景目录一致，勾选用） |
| **scenario_key** | 英文稳定键 |
| 业务列 | `scanPageSize` / `scanMaxDetails` / `scanResourceIds` / `scanLanguage` |

1. 导入本文件，编码选 **UTF-8**
2. 勾选对应 `name` 行再跑场景 Group（选行只换变量，不会自动只跑某一 Group）
3. 鉴权仍勾「自动化-鉴权」数据集三列；先跑 `00 Auth`

若中文乱码：改用 `apifox-dataset-business-ascii.csv`。

对照表：`scenario-group-map.md`。
