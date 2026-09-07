# SSO 免登短链（Q3-SP4）测试工作文档

> 接口：`POST /api/v2/sso/links`  
> 环境：`developer-sandbox` + `x-version: canary`  
> 执行日期：2026-09-01  
> 执行方式：本机批量脚本（非 Apifox 手工逐条）  
> 原始结果：`interface_cursor/tools/sso-links-q3-sp4/run-results/sso-batch-2026-09-01T07-56-34-492Z.json`

---

## 一、测试结论（给领导/开发一句话）

主路径 **ORDER_LIST / ORDER_DETAIL（带齐字段）可出短链**；  
**8 条用例未通过**，集中在：① 期望 `500.000.602` 但实际码不同；② `language`/`durationInSeconds` 文档称可选、canary 当必填；③ 语种 `es-419` 被拒。  
**浏览器打开短链、分页、过期、访客模式未测**，需补手工验证。

| 指标 | 结果 |
|------|------|
| 执行用例 | 59 |
| 通过 | 51（约 86%） |
| 未通过 | 8 |
| 阻塞级（主路径出链） | 否（主路径已通） |

---

## 二、本次执行环境（复现必带）

| 项 | 值 |
|----|-----|
| Base URL | `https://developer-sandbox.dragonpass.com/api` |
| Path | `/v2/sso/links` |
| Header `x-version` | `canary` |
| Header `X-Program-ID` | `1919256841868288` |
| Auth | `POST /v2/auth/token`，clientId=`OWYXJUXKHPJZHTUKIRWN`（与上 Program 同一套） |
| subject.type | `MEMBERSHIP` |
| subject.id | `8576507744260001` |
| DETAIL 用 orderId | `SL20260901BGVF836` |

说明：

- Program `1991829094323200`（clientId `DD60DF…`）可换 Token，但调 SSO 固定 `201.000.001`，**不能用那套测 SSO**。
- Apifox 全局 `X-Request-ID` 必须是 **36 位标准 UUID**（少位/多位都会 `301.000.001`）。
- 集合前置脚本会重写 Body；手工调通时建议先禁用全量前置，或保证脚本写入 `durationInSeconds`。

---

## 三、通过情况摘要

| 目录 | 通过 | 失败 | 说明 |
|------|------|------|------|
| 1.必填校验 | 2 | 4 | 602 相关未达预期 |
| 2.参数标准化 | 7 | 2 | 不传 language/duration 失败 |
| 2b.语种轮询 BOSS26 | 25 | 1 | 仅 `es-419` 失败 |
| 3.异常场景 | 9 | 1 | ERR-001 未到 602 |
| 4.边界与容错 | 2 | 0 | duration=60/7200 通过 |
| 5.联动一致性 | 3 | 0 | 同参多次均可出链（接口层） |
| 6.手工半自动 | 3 | 0 | **仅接口出链通过**，打开短链未做 |

已验证成功样例（可写进缺陷「对照成功请求」）：

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "language": "en-US",
  "durationInSeconds": 60
}
```

成功特征：`code=0`，存在 `data.entry.shortUrl`、`data.entry.validUntil`。

---

## 四、未通过清单 + 如何验证 + 提给开发的信息

### 缺陷组 A：`ORDER_DETAIL` 缺 `orderId` 未返回 `500.000.602`

| 用例 | 预期 | 实际 |
|------|------|------|
| SSO-REQ-002 缺 orderId | `500.000.602` | `500.041.004` Order 不属于当前 Program |
| SSO-REQ-005 缺 extra | `500.000.602` | `500.041.004` |
| SSO-REQ-002b `order_detall` | `500.000.602` | 先被 `302` 缺 duration 拦截 |
| SSO-REQ-003 空 orderId | `500.000.602` | 先被 `302` 缺 duration 拦截 |
| SSO-ERR-001 缺 extra | `500.000.602` | 先被 `302` 缺 duration 拦截 |

**你怎么验证（复现步骤）**

1. 用第二节环境换 Token。  
2. Body（带齐 language + duration，专门验证「缺 orderId」）：

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_DETAIL",
  "language": "en-US",
  "durationInSeconds": 60
}
```

（不要带 `extra` / 不要带 `extra.orderId`）

3. 记录：`HTTP`、`code`、`errCode`、`msg`、完整请求 Headers（可打码 Token）。

**向开发提交时附上**

- 【环境】sandbox + canary + Program-ID  
- 【预期】Jira/用例：缺 `extra.orderId` → **`500.000.602`**  
- 【实际】`500.041.004` 或先 `302` 缺 duration  
- 【问题】错误码是否改了？还是 602 未上 canary？duration 是否应先校验？  
- 【附件】请求 Body + 响应 JSON +（可选）traceId/X-Request-ID  

**建议提问**

1. `500.000.602` 是否仍是对外约定码？  
2. 缺 orderId 为何变成 `500.041.004`？  
3. `durationInSeconds` / `language` 是否已改为必填？（影响 002b/003/ERR-001 能否测到 602）

---

### 缺陷组 B：可选字段在 canary 变为必填

| 用例 | 预期 | 实际 |
|------|------|------|
| SSO-STD-004 不传 language | 成功，默认 en-US | `302.000.001` 缺 language |
| SSO-STD-007 不传 duration | 成功，默认约 600 | `302.000.001` 缺 durationInSeconds |

**你怎么验证**

不传 language：

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "durationInSeconds": 60
}
```

不传 duration：

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "language": "en-US"
}
```

**向开发提交时附上**

- 文档/Jira 原文：language 默认 en-US；duration 默认 600、范围 60～7200  
- 实际响应全文  
- 问：canary 是否未合入默认值逻辑？还是文档过期、字段已改必填？  

若开发确认「已改必填」→ 测试侧改用例预期，关闭缺陷，标「需求变更」。

---

### 缺陷组 C：语种 `es-419` 非法

| 用例 | 预期 | 实际 |
|------|------|------|
| SSO-STD-006 language=es-419 | 成功出链 | `301.000.001` language 格式非法 |

**你怎么验证**

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "language": "es-419",
  "durationInSeconds": 60
}
```

对照：同结构 `language=es-ES` 本次批量 **通过**。

**向开发提交时附上**

- BOSS-API 语种清单含 `es-419`（组内口径）  
- 实际 `301` 响应  
- 问：SSO/canary 白名单是否未包含 `es-419`？应支持还是文档剔除？  

---

## 五、未测 / 半测清单（必须补）

| 项 | 原因 | 建议验证方式 | 优先级 |
|----|------|--------------|--------|
| 打开短链是否免登进订单列表 | 批量只调接口 | 浏览器打开 `shortUrl`，确认无登录页，URL 含 `standard-public` | P0 |
| ORDER_DETAIL 打开后进详情 | 同上 | 打开 DETAIL 短链，URL 含 `standard-lfd`，订单号正确 | P0 |
| 短链过期后不可用 | 需等待 | `durationInSeconds=60` 出链，等 >60s 再打开 | P0 |
| 列表分页 / loading | 需页面操作 | 免登进列表后翻页或滚底 | P1 |
| 访客模式（不传 subject） | 预研范围待确认 | 单独发一单问开发是否本期做 | P2 |
| EPASS / CLIENT_USER | 本期不做细测 | 标 N/A | — |
| Program `1991829…` 套 SSO | 固定 201 | 另开缺陷：该 Program 在 canary SSO 鉴权失败 | P1 |
| Apifox 全量集合断言 | 前置脚本/全局 Header 干扰大 | 修好环境后再跑自动化；或以本报告批量结果为准 | P1 |
| 同参短链是否幂等（产品定义） | 接口层多次都能出链 | 对比多次 `shortUrl` 是否相同，问产品 | P2 |
| returnUrl 外域策略 | 仅记录 | 与安全/产品确认拦截还是透传 | P2 |

---

## 六、建议缺陷标题（可直接贴 Jira）

1. 【canary】SSO `/v2/sso/links` ORDER_DETAIL 缺 orderId 未返回 500.000.602，实际 500.041.004  
2. 【canary】SSO language/durationInSeconds 文档为可选，实际 302 必填  
3. 【canary】SSO language=es-419 返回 301，与 BOSS 语种清单不一致  
4. 【canary】Program 1991829094323200 换 Token 成功但 SSO 返回 201.000.001（可选，若业务要用该 Program）

每条缺陷描述模板：

```text
【环境】sandbox + x-version=canary + Program-ID=1919256841868288
【接口】POST /api/v2/sso/links
【前置】已用对应 clientId/secret 换 Token；X-Request-ID 为合法 UUID
【步骤】…
【请求 Body】…
【预期】…
【实际】errCode=… msg=…
【对照】同环境 ORDER_LIST 带 language+duration 可 code=0 出 shortUrl
【附件】响应 JSON / 截图 / 本工作文档第四节对应组
```

---

## 七、你下一步工作安排（建议顺序）

1. **今天**：按第四节把 A/B/C 三组各复现 1 次，截图 + 响应贴 Jira。  
2. **今天**：用成功 shortUrl 做 P0 手工：打开列表、打开详情、60s 过期。  
3. **明天**：问清 language/duration 是否改必填、602 是否改码；根据答复改 XMind/用例预期。  
4. **环境**：Apifox 固定 Program=`1919256841868288`，`Authorization=Bearer {{access_token}}`，`X-Request-ID` 用 36 位 UUID；调试时慎用会改写 Body 的全量前置。  

---

## 八、新人易漏点（本次踩过）

1. Token 的 Program 与 `X-Program-ID` 必须同一套，否则像业务失败其实是 `201`。  
2. `X-Request-ID` 少一位/多一位都会 301，不要手改到截断。  
3. 界面 Body 有字段 ≠ 实际发出去——**前置脚本会覆盖 Body**。  
4. 「不传字段」用例在 canary 可能先被必填校验拦住，到不了你要测的业务码（如 602）。  
5. 接口 `code=0` 只证明出链成功，**免登是否生效必须打开短链看页面**。

---

## 九、附件索引

| 文件 | 用途 |
|------|------|
| `tools/sso-links-q3-sp4/run-results/sso-batch-2026-09-01T07-56-34-492Z.json` | 全量 59 条原始结果 |
| `tools/sso-links-q3-sp4/run_sso_batch.js` | 复跑脚本 |
| `tools/sso-links-q3-sp4/PAPI-SSO免登短链-全量自动化.postman_collection.json` | Apifox 导入集合 |
| `testcases/2026Q3_SP4/SSO免登短链-接口测试用例.md` | 用例说明 |

---

*文档生成说明：基于 2026-09-01 canary 批量实测；Apifox 侧后续手工调通过程中的 Header/前置问题已写入第五、八节，不重复计入「8 条未通过」。*
