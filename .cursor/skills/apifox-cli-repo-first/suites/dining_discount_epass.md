# dining_discount_epass · CLI 落地笔记

- **场景**：370239 · `Dining Discount ePass · CLI sync`
- **目录**：folderId **350034** · `epass/P0(冒烟用例)/walk-in`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475756**（ePass）
- **生成器**：`generators/GeneratePostmanCollectionDiningDiscountEpass.py`
- **变量供给**：B · Environment 手填（**不建业务 CSV**）；资源 ID **禁止手填**，LIST 动态取
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `ddEpassHelpersSource`；其它步 eval loader

## 主链路

Auth → `GET /v2/resources?module=5` → `GET /v2/resources?module=4`（coupon）→
`POST /v2/orders/discounts/ePasses` 全网络（不传 `resourceIds`）→ search / users / 使用列表（空则过，详情 skip）→
再发放 `resourceIds=[diningResourceId]` → 同样查询链 →
P1 混品类 `500.063.001`、超 30（31 个）`500.063.002`（Dining 不足 31 skip，禁止用 coupon 凑数）

**不做**：核销 / Callback / 取消 / 二维码 / 业务 CSV

## 字段对照（已确认）

| 检查点 | 期望来源 | 步骤 | 状态 |
|---|---|---|---|
| 全网络不传 `resourceIds` | 入参省略该键（不是 `[]`） | E01-S01 | 已确认 |
| `module=5` `category=1` | 发放/search/列表 | E01/E02 | 已确认 |
| 未核销不返回 `usedUsages` | 使用列表/详情 | E01-S04/S05 | 已确认 |
| 混品类 | coupon `module=4` ID → `500.063.001` | E03-S01 | 已确认 |
| 超 30 | 31 个 Dining ID → `500.063.002` | E03-S02 | 已确认 |

- LIST `GET /v2/resources`：解绑后 **query 会丢**（第一次跑 `module=5` 没带上，列表空）。前置 `ddApplyResourcesListQuery` 强制写回。

- 发放 **不传** `activationDate`（可选）：传过去的日期早于当前会 `500.060.016`。

## 2026-08-27 Run（沿用 3475756 / 351893）

发放 + search 已通。用户确认下列 **当产品问题，测试期望不改**：

- `users/ePasses` 空列表；`orders/ePasses` 列表 `500.060.020`（search 同一 ePassId 成功）
- 混品类实际 `500.000.017` Invalid scope（期望仍为 `500.063.001`）
- 超 30 实际 HTTP 400 / `301.063.001` 格式非法（期望仍为 `500.063.002`；已组 31 个 Dining ID）

## 跑测前必问

现在要不要跑、鉴权数据集是否仍用 `3475756`、Environment 是否仍用 `351893`。无业务 CSV 可导入。
