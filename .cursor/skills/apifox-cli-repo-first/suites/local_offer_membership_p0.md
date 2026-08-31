# local_offer_membership_p0 · CLI 落地笔记

- **场景**：369083 · `Local Offer Membership P0 · CLI sync`
- **目录**：folderId **350024** · `membership/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475754**（membership数据集合）
- **生成器**：`generators/GeneratePostmanCollectionLocalOfferMembership.py`
- **姊妹资产**：`local_offer_epass_p0`（ePass 轨，挂 `epass/P0/prebooking`）
- **变量供给**：A · 鉴权数据集选行；业务 `resourceId`/`optionId` 用手填 Environment（与 ePass 同键）
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `lomHelpersSource`；其它步 eval loader
- **2026-08-23 复跑**：membership 数据集 `3475754` · Environment `351893` · 8 HTTP / 21 断言全绿。下单响应无 `bookingCounts`，详情才断言。

## 主链路

`POST /v2/memberships` → `POST /v2/resources/options/prebookings/availability`（含 membershipId）→ `POST /localOffers/memberships/prebooking` → 详情/列表 → `PATCH /v2/orders`

**字段对照（已确认）**

| 检查点 | 期望来源 | 步骤 | 状态 |
|---|---|---|---|
| `extra.bookingCounts` | 可用性 `adultCount+childCount`（默认 1+0=1；取消后不变） | E02A-S03 详情 / E02A-S06 取消后详情（下单响应无此字段，不硬断言） | 已确认 |
