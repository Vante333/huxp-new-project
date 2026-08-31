# 数据集 name（中文）↔ scenario_key

场景：`Resource isBookable Scan - CLI sync` · 资产 `resource_is_bookable_scan`

Apifox 全量数据 **name** 列用中文 Group 名；`scenario_key` 为稳定英文键。

| name（中文 Group） | scenario_key | module |
|---|---|---|
| 全量并集（填齐后勾选本行跑整场景） | `_FULL_SUITE` | all |
| P1 · module=1 Lounge · en-US isBookable | `M1_en_US` | 1 |
| P1 · module=2 FastTrack · en-US isBookable | `M2_en_US` | 2 |
| P1 · module=7 eSIM · en-US isBookable | `M7_en_US` | 7 |
| P1 · module=8 Fitness/eSIM 变体 · en-US isBookable | `M8_en_US` | 8 |
| P1 · module=11 Local Offer · en-US isBookable | `M11_en_US` | 11 |

## 业务列

| 列 | 说明 |
|----|------|
| `scanPageSize` | 列表分页（默认 100） |
| `scanMaxDetails` | 0=全量；>0=前 N 个（SyncCheck 建议 30） |
| `scanResourceIds` | 定点 ID，逗号分隔；非空则跳过列表 |
| `scanLanguage` | 固定 en-US |

鉴权三列 **不要** 放进本业务数据集。
