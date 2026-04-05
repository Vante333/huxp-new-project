# 变更影响速查

改需求或实现前，按类型扫一遍下列项；每项可回到 [capability-map.md](capability-map.md)、[contracts-and-integrations.md](contracts-and-integrations.md) 或 [traceability.md](traceability.md) 补链接。

## 会籍 extensions 相关

- [ ] 注册/查询响应是否仍对非内部租户隐藏 `extensions`（或等价语义）
- [ ] 同一 membership 内 `type` 唯一、条数上限等规则是否变化
- [ ] 更新接口的 **HTTP 方法**（POST/PATCH）与网关、环境变量、Postman/自动化是否一致
- [ ] `search` 是否返回 `extensions` / `feature` 解析路径是否变化（读侧未发布时的 skip 策略）
- [ ] 错误码与响应体是否影响现有客户端与 [api-testcases/2026Q2_SP1](../api-testcases/2026Q2_SP1/) 中断言

## 响应信封与业务码

- [ ] 根级 `code` 或成功/失败判定语义是否变化
- [ ] Allure/报告中的「业务成功」判定是否与 `ParseResponseEnvelope`、Postman Tests 一致

## 鉴权与租户

- [ ] `X-Program-ID`、OAuth client 与内部租户范围是否变化
- [ ] 取 token 请求头/体是否与沙箱、文档、自动化一致

## 全局

- [ ] 是否属于 **Breaking** 对外契约：若是，需版本说明、兼容期、文档与全量回归范围
- [ ] 更新 [traceability.md](traceability.md) 对应行与 [capability-map.md](capability-map.md) 小节
