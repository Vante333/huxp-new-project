# fitness_membership_p0 · CLI 落地笔记

- **场景**：369082 · `fitness Membership P0 · CLI sync`
- **目录**：folderId **350024** · `membership/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 **3475754**（membership数据集合）
- **生成器**：`generators/GeneratePostmanCollectionFitnessMembership.py`
- **姊妹资产**：`fitness_epass_p0`（ePass 轨，挂 `epass/P0/prebooking`）
- **变量供给**：A · 鉴权数据集选行；业务 `fitnessResourceId` 用手填 Environment
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **Helpers**：Auth 写入 `fmHelpersSource`；其它步 eval loader

## 主链路

`POST /v2/memberships` → `GET …/fitness/{id}/schedule` → `POST /options/prebookings/availability` → `POST /fitness/memberships/prebooking` → 详情/列表 → `PATCH /v2/orders`

`optionId` / `prebookingDate` 由 schedule 选槽写入，可用性前置强制改写 body。

**字段对照（已确认）**

| 检查点 | 期望来源 | 步骤 | 状态 |
|---|---|---|---|
| ``extra.bookingCounts`` | 可用性 ``adultCount+childCount``（默认 1+0=1；取消后不变） | E02-S04 详情 / E02-S07 取消后详情 | 已确认 |

## 跑测坑

- 列表断言必须看 ``data.orders``（不是 items/list）。
- ``push_mode=http`` 解绑后 GET schedule 常丢掉 ``startDate/endDate``，默认回到当天槽；当天已开课则 ``PATCH /orders`` 业务失败。前置 ``fmApplyScheduleQuery`` 写本机今天+5～+10，选槽跳过已过点。
