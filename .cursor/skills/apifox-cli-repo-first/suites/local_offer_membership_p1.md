# local_offer_membership_p1 · CLI 落地笔记

- **场景**：369084 · `Local Offer Membership P1 · CLI sync`
- **目录**：folderId **350028** · `membership/P1（全量用例）/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475754**（membership数据集合）
- **生成器**：`generators/GeneratePostmanCollectionLocalOfferMembership.py`（一次写出 P0 / P1）
- **姊妹资产**：`local_offer_epass_p1`（ePass 轨，挂 `epass/P1/prebooking`）
- **变量供给**：A · 鉴权数据集选行；业务 `resourceId`/`optionId` 用手填 Environment
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `lomHelpersSource`；其它步 eval loader
- **2026-08-23 复跑**：membership 数据集 `3475754` · Environment `351893` · 15 HTTP / 39 断言全绿（路径 A 含 membershipId + 路径 B 不含）。

## 主链路

P0 路径 A（可用性含 `membershipId`）+ 路径 B（可用性不含 `membershipId`，下单仍绑会籍）。每条链前重注册会籍，避免权益耗尽。路径 B 的 `prebookingDate` 为今天+11 天 T10:00。
