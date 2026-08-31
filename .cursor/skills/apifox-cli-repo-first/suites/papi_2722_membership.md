# papi_2722_membership · CLI 落地笔记

- **场景**：369079 · `PAPI-2722 FT PII Membership · CLI sync`
- **目录**：folderId **350028** · `membership/P1（全量用例）/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475754（membership）
- **生成器**：`generators/GeneratePostmanCollectionPapi2722FastTrackPii.py`（一次写出 ePass / membership 两套）
- **姊妹资产**：`papi_2722`（ePass 轨）
- **来源**：2026-08-23 从混合场景拆出 membership 轨
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `p2722HelpersSource`；其它步（含 FastTrack 取消块）eval 同一源（须先跑 00 Auth）
- **2026-08-23 复跑修复**：取消块显式传 `helpers_source_key`；N06 成功后补 `P1-S09-OK-AVL`；资源详情前置强制 `module=2`；断言读 `prebookingPolicy.prebookingRequiredInfo`；FT 刚下单取消常 `500.051.029`/`500.041.006`，收尾警告不阻断 PII 主路径
