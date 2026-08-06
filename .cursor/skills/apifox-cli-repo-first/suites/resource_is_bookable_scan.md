# resource_is_bookable_scan · CLI 落地笔记

- **场景**：366666 · `Resource isBookable Scan - CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475756（鉴权三列）；业务扫描参数走 **Environment 手填**
- **生成器**：`generators/GeneratePostmanCollectionResourceIsBookableScan.py`
- **变量供给**：B · Environment 手填（`scanModule` / `scanLanguage` / `scanPageSize` / `scanMaxDetails`）
- **用途**：分页拉 `/v2/resources` → 详情轮询 → **命中 `isBookable===true` 即打印**，再继续下一条（结尾只打数量摘要）

## 换测要点

| 变量 | 说明 |
|------|------|
| `ProgramID` / `clientId` / `secret` | 鉴权（数据集或 Environment） |
| `scanModule` | 默认 `1`（lounge） |
| `scanResourceIds` | 定点 ID，如 `N00012`（**跳过列表**）；清空后才全量/抽样扫列表 |
| `scanMaxDetails` | 列表模式：`0`=全量；默认 `30`（前 N 个，**不含**未必有 N00012） |

## 命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset resource_is_bookable_scan
```
