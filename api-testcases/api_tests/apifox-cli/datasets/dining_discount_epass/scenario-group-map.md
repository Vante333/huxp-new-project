# Dining Discount ePass · Group 对照（B Environment，无业务 CSV）

给团队看场景内分组，不是数据集选行。

| Group | 步骤 | 说明 |
|---|---|---|
| 00 Auth | Auth | ePass 数据集 `3475756` 选行 |
| E00 · 动态取资源 | E00-S01 LIST module=5；E00-S02 LIST coupon module=4 | 写入 `diningResourceId` / 混品类 ID |
| E01 · P0 全网络发放 | 发放（不传 resourceIds）→ search → users → 使用列表 → 详情 skip | 同一 `clientUserId` |
| E02 · P0 指定资源发放 | 发放 `[diningResourceId]` → 同样查询链 | 第二个 ePass |
| E03 · P1 负向 | 混品类 `500.063.001`；31 个 `500.063.002` | 条件不足则 skip |
