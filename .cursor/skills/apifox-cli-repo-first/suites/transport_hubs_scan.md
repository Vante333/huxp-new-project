# transport_hubs_scan · CLI 落地笔记

- **场景**：366797 · `Transport Hubs Scan · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475756**（A · 鉴权选行，与 resource_details_scan 共用）
- **生成器**：`generators/GeneratePostmanCollectionTransportHubsScan.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **编排**：
  1. Auth（token；helpers 内嵌各步，勿写含 `{{` 的 collection 变量）
  2. 26 语种**静态分组**（步骤名含语种字面量）
  3. `LIST-SEED` `GET /v2/transportHubs`（**不传 type**）→ 列表页 forEach → 站点 forEach
  4. DETAIL `GET /v2/transportHubs/{transportHubId}?fallbackAllowed=false`，断言 `code=0`
- **变量**：`scanPageSize`（≤100）、`scanMaxDetails`（0=全量）
- **规模**：1 + 26×3 ≈ 79 叶子步骤
