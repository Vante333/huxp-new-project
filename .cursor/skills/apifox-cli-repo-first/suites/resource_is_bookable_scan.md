# resource_is_bookable_scan · CLI 落地笔记

- **场景**：366666 · `Resource isBookable Scan - CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 鉴权数据集 3475756；**业务扫描参数走数据集选行（A）**
- **生成器**：`generators/GeneratePostmanCollectionResourceIsBookableScan.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **变量供给**：A · 数据集选行  
  - `postman/datasets/resource_is_bookable_scan/apifox-dataset-business-ascii.csv`  
  - 中文对照：`scenario-group-map.md`
- **编排（2026-08-09 · 对齐 Details Scan forEach）**：
  1. Auth：token + `rbHelpersSource` + 清空 `scanLastBookableIds`
  2. module ∈ {1,2,7,8,11} × 语种 **en-US** 静态分组
  3. 组内：LIST-SEED → 列表页 forEach → 资源 forEach → DETAIL  
     （`fallbackAllowed=false`；命中 `isBookable===true` 追加 `scanLastBookableIds`）

## 换测要点

| 来源 | 变量 | 说明 |
|------|------|------|
| 鉴权数据集 / Environment | `ProgramID` / `clientId` / `secret` | 鉴权三列（勿进业务数据集） |
| Environment | `baseUrl` / `x-version` | 网关 |
| 业务数据集行 | `scanPageSize` | 默认 `100` |
| 业务数据集行 | `scanMaxDetails` | `0`=全量；默认行 `30`（抽样） |
| 业务数据集行 | `scanResourceIds` | 定点 ID（非空则跳过列表） |

## 产出

- 控制台 / 断言面板：`[命中 #N] module=… | resourceId | name`
- 集合变量：`scanLastBookableIds`（JSON 数组）、`scanLastBookableHits`、`scanLastSummary`

## 命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset resource_is_bookable_scan
```
