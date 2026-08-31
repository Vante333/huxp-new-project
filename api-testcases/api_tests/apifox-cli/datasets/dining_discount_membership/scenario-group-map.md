# Dining Discount Membership · Group 对照（B Environment，无业务 CSV）

给团队看场景内分组，不是数据集选行。

| Group | 步骤 | 说明 |
|---|---|---|
| 00 Auth | Auth | membership 数据集 `3475754` 选行 |
| M01 · 注册与查询 | 注册 → 用户会籍列表 → search | 快照 module=5 四类权益 |
| M02 · 更新有效期 | 只改 expirationDate → 概览仍等于快照 | 权益不清零 |
| M03–M06 · 四类权益 | 持卡人 / 共享 / 携客（0 则 skip）/ 买点必打 | 每次更新后 search+details |
| M07 · 使用订单 | 列表空则过；详情 skip | 不造核销 |
