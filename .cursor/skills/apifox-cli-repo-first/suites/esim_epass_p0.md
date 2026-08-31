# esim_epass_p0 · CLI 落地笔记

- **场景**：366655 · `eSIM ePass P0 · CLI sync`
- **目录**：folderId **350033** · `epass/P0(冒烟用例)/prebooking`（2026-08-23 从 common/P1/others 迁入）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475756（ePass）
- **生成器**：`generators/GeneratePostmanCollectionEsimEpass.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **来源**：main 旧场景「eSIM ePass · P0 E2E 核心」全量迁移（2026-07-29）
- **注意**：生成器已加 `RewritePurposeFirstNames`，满足 PushSteps 目的前置命名硬约束
