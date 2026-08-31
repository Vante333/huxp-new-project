# fitness_epass_p0 · CLI 落地笔记

- **场景**：366654 · `fitness ePass P0 · CLI sync`
- **目录**：folderId **350033** · `epass/P0(冒烟用例)/prebooking`
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · 数据集 3475756（ePass）
- **生成器**：`generators/GeneratePostmanCollectionFitnessEpass.py`
- **Push**：`push_mode: http` + `unbind_after_push: true`
- **来源**：main 旧场景「fitness ePass · P0 E2E 核心」全量迁移（2026-07-29）

## schedule → 可用性 / 下单

- `prebookingDate` **不套**「今天+10 天 T10:00」：由 GET schedule 选槽（`date` + `startTime`）写入。
- Apifox 场景里 `collectionVariables` 跨步不持久。`fpParseFitnessSchedule` 用 `fpSetVar` 写 **variables + collection**，并 `unset` 共用 Environment 上的旧 `fitnessOptionId` / `prebookingDate`。
- E02-S02 / E02-S03 / E03-S01 / E03-S02 前置调用 `fpApplyScheduleToRequestBody()`，把槽位字面量写进 body（含 `extra.optionId`）。
- 复验：可用性「实际请求」的 `optionId` / `prebookingDate` 须等于 schedule 后置控制台 `schedule 选槽 …` 那一行。
- ``extra.bookingCounts``：仅详情接口断言，等于可用性 ``adultCount+childCount``（默认 1+0=1；取消后不变）。
- **clientUserId**：创建 body 用 ``{{$string.uuid}}`` 发出；后置从响应提取 ``fpSetVar`` 再断言回显为 UUID。禁止前置 ``replaceIn``（CLI 常不展开，会拿模板去比响应 UUID）。后续步靠 ``fpApplyRuntimeIdsToRequestBody`` 写入 body。
