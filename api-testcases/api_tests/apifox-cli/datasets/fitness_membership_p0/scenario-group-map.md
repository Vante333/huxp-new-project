# fitness Membership P0 · Group 对照

鉴权用场景数据集 **membership数据集合**（`use_data_set_id=3475754`，列 `ProgramID` / `clientId` / `secret`）。  
本套 P0 只有 **1 条预约链**，不另做业务 CSV；网点 `fitnessResourceId` 填 Environment。

| Apifox Group | 步骤 | 说明 |
|---|---|---|
| 00 Auth | Auth | 数据集选 membership 行 |
| P0 · membership 预约 / 00 前置 | SETUP-MS-S01 | `POST /v2/memberships` |
| P0 · membership 预约 / prebooking | E02-S01～S07 | schedule 选槽 → 可用性 → 下单 → 详情/列表 → 取消 |
