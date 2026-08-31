# dining_discount_membership · CLI 落地笔记

- **场景**：370240 · `Dining Discount Membership · CLI sync`
- **目录**：folderId **350025** · `membership/P0(冒烟用例)/walk-in`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475754**（membership）
- **生成器**：`generators/GeneratePostmanCollectionDiningDiscountMembership.py`
- **姊妹资产**：`dining_discount_epass`
- **变量供给**：B · Environment 手填（**不建业务 CSV**）
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `ddMbrHelpersSource`；其它步 eval loader
- `clientUserId` / `membershipId`：取 M01-S01 **响应**，后续步强制回填（覆盖 Environment 旧值）
- `POST /users/memberships` **不传** `status`（OAS example `status=1` 会把刚注册会籍滤掉）
- 通识：Skill [`reference.md`](../reference.md)「注册后 runtime ID 被 Environment / OAS 样例盖掉」

## 主链路

Auth → `POST /v2/memberships` → `POST /v2/users/memberships` → `POST /v2/memberships/search` →
`POST /v2/memberships/qrCodes` 展码（`durationInSeconds=60`）→
`POST /v2/memberships/update` 只改 `expirationDate` → 权益概览仍等于注册快照 →
按快照依次更新：持卡人 `usageRestriction=1`、共享 `=3`、携客 `guestsExclusiveEntitlements` `=2`（为 0 skip）、
**无论 purchased 是否为 0 再打一次买点** → 每次更新后 search + details → 使用订单列表（空则过）

**不做**：核销 / 取消 / 业务 CSV

## 字段对照（已确认）

| 检查点 | 期望来源 | 步骤 | 状态 |
|---|---|---|---|
| 四类权益字段 | 持卡人 / 携客=guestsExclusive / 共享 / 买点 | 注册快照 + 更新后 | 已确认 |
| 改期不清零 | 四类余额=注册快照 | M02-S02 | 已确认 |
| 大客户为 0 skip | `ddSnap_* === 0` | M03–M05 | 已确认 |
| 买点必打 | `purchasedQuantity=1` 不论是否为 0 | M06 | 已确认 |
| 未核销不返回 usedEntitlementDetails | 详情 extra | M07-S02 | 已确认 |
| qrCode 非空 | 响应 | M01-S04 | 已确认 |
| validUntil Unix ≈ 请求时刻+duration | `durationInSeconds=60`，容差 30s | M01-S04 | 已确认 |

## 2026-08-27 Run（沿用 3475754 / 351893）

20 步里 18 步通过。剩余：

- M04 共享、M06 买点：`500.030.025` Different types of entitlements must be updated separately
  （OAS required 同时传 `quantity`+`purchasedQuantity`；产品按 PAPI-2182 要求两类分开传）

用户确认（4A）：大客户只传 `quantity`，买点只传 `purchasedQuantity`。

2026-08-27 复跑（192426）：19/20，M04 共享已绿。M06 买点仍 `500.030.025`：body 还带了 `usageRestriction=1`（买点不受 restriction 控制）。已改为买点不传 restriction。

## 跑测前必问

现在要不要跑、鉴权数据集是否仍用 `3475754`、Environment 是否仍用 `351893`。无业务 CSV 可导入。
