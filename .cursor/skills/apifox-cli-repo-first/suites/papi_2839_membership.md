# papi_2839_membership · CLI 落地笔记

- **场景**：369080 · `PAPI-2839 FT NameRegex Membership · CLI sync`
- **目录**：folderId **350028** · `membership/P1（全量用例）/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475754（membership）
- **生成器**：`generators/GeneratePostmanCollectionPapi2839.py`（一次写出 ePass / membership 两套）
- **姊妹资产**：`papi_2839`（ePass 轨）
- **来源**：2026-08-23 从混合场景拆出 membership 轨
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `p2839HelpersSource`；其它步（含 FastTrack 取消块）eval 同一源（须先跑 00 Auth）
- **2026-08-23 复跑**：`passengers` 组前再注册 `SETUP-MS-S02`，避免同一 membership 权益耗尽；FT 刚下单取消 `500.051.029`/`500.041.006` 收尾警告不阻断
