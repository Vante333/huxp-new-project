# PAPI-2657Preview接口toUseEntitlementDetail非必传测试用例

## 测试范围说明

- rc: 基于 `requirements/Aero Blue/PAPI-2657.md`；接口路径 `GET/POST` 以 **APIFOX** 为准：`/api/v2/orders/{modules}/memberships/prebooking/preview`。
- rc: 规则变更：**toUseEntitlementDetail** 由必传改为非必传；不传时按 **toUseEntitlementCount** 拆分：**1 点优先 CH，剩余给 Guest**（与需求原文一致；若有「最小点数单位」以产品为准）。

## v2_orders_{modules}_memberships_prebooking_preview（Preview算点）

### tc-p1: 不传toUseEntitlementDetail仅传toUseEntitlementCount为偶数点时CH与Guest点数符合优先CH规则

pc: 具备可预览的会籍与点数上下文；`toUseEntitlementCount` 取偶数且不超过可用上限

- 调用 Preview 接口不传 `toUseEntitlementDetail`，传入合法 `toUseEntitlementCount`
  - 成功；响应中 CH/Guest 分配点数之和等于 `toUseEntitlementCount`，且满足「1 点优先 CH、余量 Guest」的等价拆分（偶数时各半）

### tc-p1: 不传toUseEntitlementDetail且toUseEntitlementCount为奇数点时CH比Guest多1点

pc: 同上一致上下文；`toUseEntitlementCount` 为奇数

- 调用 Preview 接口不传明细，仅传该 count
  - 成功；CH 比 Guest 多 1 点（或等价满足「优先 CH」语义），总和等于 count

### tc-p2: 仍传toUseEntitlementDetail时行为与改造前一致按明细分配

pc: 构造合法 CH/Guest 明细与 `toUseEntitlementCount` 一致或符合 APIFOX 校验

- 调用 Preview 同时传入明细与 count
  - 成功；分配结果与明细一致（若产品与研发约定「以明细为准」；若约定 count 优先则按 APIFOX 调整预期并更新本用例）
- rc: **需与产品确认**「明细 + count 同时存在」时的优先级


### tc-p2: 不传toUseEntitlementDetail且缺少toUseEntitlementCount或点数不足时失败或提示明确

pc: 按 APIFOX 判断是否允许仅不传明细仍须 count；或点数不足场景

- 调用 Preview 不传明细且不传 count（或 count 非法）
  - 返回约定业务错误，文案可定位问题

### tc-p3: 历史客户端仍传必传形态时主流程不受影响

pc: 使用改造前典型报文（含明细）

- 调用 Preview
  - 成功且分配逻辑与现网一致

### tc-p3: modules取lounges与fastTrack时Preview规则一致

pc: 两套 modules 下均有可预览数据

- 分别调用 Preview
  - 两种 modules 下「不传明细」拆分规则一致（若存在差异以 APIFOX 为准）
