# resource_details_scan · CLI 落地笔记

- **场景**：366662 · `Resource Details Scan · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475756
- **生成器**：`generators/GeneratePostmanCollectionResourceDetailsScan.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **编排（2026-08-11 · 回退：品类 → 语种子夹）**：
  1. Auth：token + `rdHelpersSource`
  2. 顶层 **8 品类夹** → 语种子夹（名=`en-US` 等）
  3. 语种内：Auth-Refresh（默认）→ LIST（page1 + `pm.sendRequest` 余页）→ 资源 forEach → DETAIL
- **变量**：`scanPageSize`、`scanMaxDetails`（0=全量）；改语种改生成器常量后 Generate+Push
- **Auth 续期**：`RD_AUTH_REFRESH_SCOPE`=`language`（默认）| `module` | `none`
- **规模**：≈649 叶子 HTTP（8×27×(Auth-Refresh+LIST+DETAIL)+顶层 Auth）
- **冒烟**：`RD_SCAN_SMOKE=1` → PushSteps → Run（建议 `scanMaxDetails=5`）→ 去掉变量再 PushSteps 恢复全量；勿另写 `_tmp` 落盘脚本
