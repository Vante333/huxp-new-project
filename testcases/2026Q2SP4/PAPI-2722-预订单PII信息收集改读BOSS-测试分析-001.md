# PAPI-2722预订单PII信息收集改读BOSS测试分析

## 测试范围说明

- rc: 基于 `requirements/2026Q2SP4/PAPI-2722.md`；源脑图：`D:\fenxi\API\2026_Q2\评审前\Q2_SP4\PAPI-2722预订单PII信息收集改读BOSS测试分析.xmind`。
- rc: 接口路径、错误码、主数据以 **Apifox/MCP** 与当前联调环境为准。
- rc: 历史 `tc-p0` 已按规范映射为 `tc-p1`；判定表碎片节点（是/否/不适用等）未写入本文件。

## Lounge三步骤主场景（LoungePrebookingE2E）

### tc-p1: Lounge场景-仅姓名Nacos无额外PII

- pc: Nacos `lounge` 供应商编码不配置 email/phone/transportNumber 等额外 PII；准备可预约 Lounge 资源、会员或 ePass 权益及有效 `prebookingToken`。
- 【步骤1·后台配置】确认 Nacos `lounge` 对该资源供应商无额外 PII 必填项；姓名写死必传，不读 BOSS。
  - 与判定表「无额外字段」行一致。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=1`）。
  - `prebookingRequiredInfo` 为 `[1, 2]`。
- 【步骤3·下单校验】按枚举传入 `firstName`、`lastName` 调用 Lounge 预订单下单。
  - 下单成功。
- 【步骤3·下单校验】移除 `firstName` 或 `lastName` 后再次下单。
  - 返回约定参数或业务错误，不创建预订单。

## FT三步骤主场景（FtPrebookingE2E）

### tc-p1: FT场景-邮箱姓名电话    不需要航班号

- pc: BOSS 收集内容为邮箱、姓名、电话；是否收集乘客信息=全部使用人；是否需要航班号=否；准备含下单人与同行使用人的 FT 资源与权益。
- 【步骤1·后台配置】确认 BOSS 配置与判定表「邮箱、姓名、电话 / 全部使用人 / 否」行一致。
  - 配置记录完成。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 为 `[1, 2, 3, 4, 5]`，不含 `6`。
- 【步骤3·下单校验】每位使用人均传邮箱、姓名、电话，不传 `transportNumber` 后下单。
  - 下单成功。
- 【步骤3·下单校验】仅移除同行使用人的一个必填 PII 字段后下单。
  - 返回约定参数或业务错误，不创建预订单。

### tc-p1: FT场景-邮箱姓名电话    不需要航班号

- pc: BOSS 收集内容为邮箱、姓名、电话；是否收集乘客信息=下单人；是否需要航班号=否；准备含同行使用人的 FT 资源与权益。
- 【步骤1·后台配置】确认 BOSS 配置与判定表「邮箱、姓名、电话 / 下单人 / 否」行一致。
  - 配置记录完成。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 为 `[1, 2, 3, 4, 5]`。
- 【步骤3·下单校验】仅下单人传邮箱、姓名、电话，同行使用人不传 PII 后下单。
  - 下单成功。
- 【步骤3·下单校验】移除下单人的一个必填 PII 字段后下单。
  - 返回约定参数或业务错误，不创建预订单。

### tc-p1: FT场景-邮箱姓名电话  需要航班号

- pc: BOSS 收集内容为邮箱、姓名、电话；是否收集乘客信息=全部使用人；是否需要航班号=是；准备含同行使用人的 FT 资源与权益。
- 【步骤1·后台配置】确认 BOSS 配置与判定表「全部使用人 / 是」行一致。
  - 配置记录完成。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 为 `[1, 2, 3, 4, 5, 6]`。
- 【步骤3·下单校验】每位使用人均传 PII 及 `transportNumber` 后下单。
  - 下单成功。
- 【步骤3·下单校验】PII 完整但不传 `transportNumber` 后下单。
  - 返回约定参数或业务错误，不创建预订单。

### tc-p1: FT场景-邮箱姓名电话 需要航班号

- pc: BOSS 收集内容为邮箱、姓名、电话；是否收集乘客信息=下单人；是否需要航班号=是；准备含同行使用人的 FT 资源与权益。
- 【步骤1·后台配置】确认 BOSS 配置与判定表「下单人 / 是」行一致。
  - 配置记录完成。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 为 `[1, 2, 3, 4, 5, 6]`。
- 【步骤3·下单校验】仅下单人传 PII 及 `transportNumber` 后下单。
  - 下单成功。
- 【步骤3·下单校验】下单人 PII 完整但不传 `transportNumber` 后下单。
  - 返回约定参数或业务错误，不创建预订单。

### tc-p1: FT场景-收集内容为空且无需收集乘客信息

- pc: BOSS 收集内容为空；是否收集乘客信息=无需；是否需要航班号=否；历史 Nacos `cip` 曾要求邮箱/电话/护照号。
- 【步骤1·后台配置】确认 BOSS 配置与判定表「无或空 / 无需 / 否」行一致；Nacos `cip` 与 BOSS 配置刻意不一致。
  - 配置记录完成。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 为 `[]` 或按产品约定为空集。
- 【步骤3·下单校验】不传 `prebookingRequiredInfo` 或传空对象后下单。
  - 下单成功，不因旧 Nacos `cip` 强制要求 PII。

### tc-p2: FT场景-收集内容减少某字段全部使用人

- pc: BOSS 收集内容从「邮箱+姓名+电话」调整为仅「姓名+电话」等减少字段组合；是否收集乘客信息=全部使用人；不需要航班号。
- 【步骤1·后台配置】确认 BOSS 已移除邮箱（或电话）收集项。
  - 与判定表「收集内容减少某字段 / 全部使用人」行一致。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 仅含当前 BOSS 收集内容对应枚举，不含被移除字段枚举。
- 【步骤3·下单校验】按新枚举完整传字段、不传被移除字段后下单。
  - 下单成功。
- 【步骤3·下单校验】移除新枚举中任一仍必填字段后下单。
  - 返回约定参数或业务错误，不创建预订单。

### tc-p2: FT场景-收集内容增加某字段下单人

- pc: BOSS 收集内容增加某字段；是否收集乘客信息=下单人；不需要航班号；准备含同行使用人的 FT 预订单。
- 【步骤1·后台配置】确认 BOSS 已移除被测字段收集项。
  - 与判定表「收集内容增加某字段 / 下单人」行一致。
- 【步骤2·资源详情】调用 GET `/v2/resources/{resourceId}`（`module=2`）。
  - `prebookingRequiredInfo` 仅含当前 BOSS 收集内容对应枚举。
- 【步骤3·下单校验】仅下单人按新枚举传字段后下单。
  - 下单成功；不再要求被移除字段。
- 【步骤3·下单校验】下单人缺少新枚举中任一必填字段后下单。
  - 返回约定参数或业务错误，不创建预订单。
