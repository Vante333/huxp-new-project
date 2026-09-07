# SSO 免登短链 — 接口测试用例（设计执行版）

> 来源：桌面《需求测试用例.xmind》→ **一、SSO免登短链**  
> 对照：`SSO免登短链-接口测试用例.md`（脑图原表）  
> 接口：`POST /api/v2/sso/links`  
> 环境：`developer-sandbox` + Header `x-version: canary`  
> 生成日期：2026-09-03  
> 说明：脑图预期保持不变；canary 与文档不一致的，记在「实测备注」，按缺陷提，不要擅自改预期。

---

## 固定测试数据（先抄到本子上）

| 项 | 值 | 说明 |
|----|-----|------|
| Apifox 环境 | **UAT (canary节点)** 或 **developer-sandbox** | 右上角选这个 |
| Base URL | `https://developer-sandbox.dragonpass.com/api` | 环境里 `baseUrl` 已含 `/api` 时，接口路径只写 `/v2/sso/links` |
| 完整 URL | `https://developer-sandbox.dragonpass.com/api/v2/sso/links` | **不要**写成 `/api/api/v2/...` |
| X-Program-ID | `1919256841868288` | **只测 SSO 用这一套** |
| subject.type | `MEMBERSHIP` | 本期细测会籍 |
| subject.id | `8576507744260001` | 已验证能出 ORDER_LIST 短链 |
| language | `en-US` | canary 实际当必填，调试一律带上 |
| durationInSeconds | 浏览器打开用 **1800**；测过期用 **60** | 60 秒链几乎立刻过期，不适合打开页面 |
| X-Request-ID | Apifox 动态值 `{{$string.uuid}}` | 必须 36 位 UUID，少一位会 `301.000.001` |
| ORDER_DETAIL 的 orderId | 从列表页 **Past / Cancelled** 抄真实单号 | 不要用 `123`；假单会 `500.000.601` |

**禁止混用的 Program（会 201.000.001）：**

| 不要用 | 用途 |
|--------|------|
| `2032786406298624` | 会籍购买 / 支付 |
| `1919249349977088` | ePass / FT 可用性 |

Token 必须和 `X-Program-ID` **同一套**。测 SSO 前先发：`POST /v2/auth/token`，数据集勾 Program=`1919256841868288`。

---

## 第一步 总结需求（用最通俗的话）

合作方调一个接口，系统吐出一条**短时免登 H5 链接**。  
用户点开后**不用再登录**，直接进：

- **订单列表**（`ORDER_LIST`）
- **某一张订单的详情**（`ORDER_DETAIL`，必须带这张单的 `extra.orderId`）

可以指定：是哪个会籍、页面什么语种、链接活多久、付完/看完回跳哪里。

一句话：**出链是接口的事；免登进没进对页面，必须用浏览器打开 shortUrl 才算测完。**

---

## 第二步 列出新增功能

- 新增对外接口 `POST /v2/sso/links`，生成免登短链。
- 支持场景：`ORDER_LIST` / `ORDER_DETAIL`（入参大小写可能被标准化成大写）。
- 返回 `entry.shortUrl`、`entry.validUntil`（Unix 秒，UTC）。
- 短链打开后免登进入对应 H5（列表 path 含 `/standard-public/`，详情 path 含 `/standard-lfd/`）。
- 语种按 BOSS-API 清单轮询（组1+组2，**26** 个）。
- 链接有效期：合法范围 **60～7200** 秒。
- `ORDER_DETAIL` 缺 `extra.orderId` 应返回 **`500.000.602`**。

---

## 第三步 列出修改功能

本期是新能力，不是改老接口字段。测试时注意和旧码表隔离：

| 容易混的码 | 实际属于 |
|------------|----------|
| `500.020.030` | FT 可用性「当地已过」，**不是** SSO |
| `500.030.039～045` | 会籍购买错误码迁移，**不是** SSO |
| `500.000.601` | SSO **生成失败兜底**（假订单号、下游失败） |
| `500.000.602` | SSO **ORDER_DETAIL 缺 extra.orderId**（文档约定） |

---

## 第四步 列出影响范围

| 类型 | 范围 |
|------|------|
| 上游 | `POST /v2/auth/token`；Program 与会籍归属必须一致 |
| 下游 | H5 短链服务、订单列表/详情页、语种包 |
| 接口依赖 | Auth Token → SSO 出链 →（可选）浏览器打开；DETAIL 依赖真实 `orderId` |
| 配置 | canary 上 `language`、`durationInSeconds` 实际当必填（文档写可选） |
| 数据 | 会籍 `8576507744260001`；DETAIL 必须该会籍下真实订单 |
| 多语言 | 26 语种轮询；`es-419` canary 曾被拒 |
| 权限 | 错 Program、错 Token、会籍 A 看会籍 B 的订单 |
| 前端 | 免登、过期页、分页/loading、不回登录页 |

---

## 第五步 输出测试点

### 功能

- 出列表链、出详情链、打开免登、过期失效、访客模式、分页/滚加载

### 参数

- `scene` 必填 / 大小写标准化 / 非法值
- `extra.orderId` 条件必填（仅 DETAIL）
- `language` 不传 / 合法 / 非法 / 26 轮询
- `durationInSeconds` 不传 / 59 / 60 / 7200 / 7201 / 类型错误
- `returnUrl` 不传 / 合法 / 外域
- `subject` 不传 / MEMBERSHIP / 非法 type / 不存在 id

### 权限

- 无 Token、坏 Token、Program 与 Token 不一致、跨会籍 orderId

### Header

- 缺 `X-Request-ID`、UUID 位数不对、缺 `X-Program-ID`、URL 写成 `/api/api/v2`

### 一致性

- 相同 Body 多次 `shortUrl` 是否一致；改 scene/orderId 后链可变

---

## 第六步 输出正常流程测试

调用链（必须按这个顺序，不要跳）：

```
1. POST /v2/auth/token     （SSO Program 1919256841868288）
        ↓
2. POST /v2/sso/links      scene=ORDER_LIST，带 language + duration
        ↓
3. 浏览器打开 shortUrl      免登进列表（Bookings & Usage）
        ↓
4. 列表里 Past/Cancelled 抄真实 orderId
        ↓
5. POST /v2/sso/links      scene=ORDER_DETAIL + extra.orderId
        ↓
6. 浏览器打开详情 shortUrl  订单号一致、不回登录页
```

对应用例：SSO-N-001～004、SSO-E2E-001～003（见下方表格）。

---

## 第七步 输出异常测试

- 不传 scene
- ORDER_DETAIL 不传 extra / 不传 orderId / 空 orderId → 期望 `500.000.602`
- 假 orderId / 不存在 → 记录实际码（canary 常见 `500.000.601`）
- 会籍 A + 会籍 B 的订单
- duration 59 / 7201 / `"abc"`
- 无 Token、错 Program
- scene=`XXX`、subject.type 非法、subject.id 不存在

---

## 第八步 输出边界测试

- duration=60 / 7200
- 未过期打开 / 过期后再打开
- 26 语种
- 相同入参连打 3 次短链

---

## 第九步 输出接口测试点

| 项 | 要点 |
|----|------|
| Method | 只测 POST；GET 应失败 |
| URL | `/v2/sso/links`，不要双写 `/api` |
| Header | Bearer Token、X-Program-ID、Content-Type、X-Request-ID、x-version=canary |
| Body | JSON；自动化「运行」可能被前置脚本改写 Body，调试请点「发送」 |
| 成功 | `code=0`，有 `data.entry.shortUrl`、`data.entry.validUntil` |
| validUntil | Unix **秒**（如 `1788439473`），不要按东八区去减 |
| 602 | 缺 orderId 的约定码 |
| 601 | 生成失败兜底，不是 602 |
| 302.000.001 | canary 缺 language 或 duration |
| 301.000.001 | UUID 非法或 language 格式非法（如 es-419） |
| 201.000.001 | Program 和 Token 不是一套 |

---

## 第十步 输出需要回归的功能

- Auth 换 Token 后 SSO 仍能出链
- ORDER_LIST / ORDER_DETAIL 出链 + 打开免登
- 602 文案（若开发改码，回归预期）
- 语种默认 en-US + 26 轮询
- duration 边界与过期
- 短链多次一致性
- 错 Program 仍应 201，不能误伤 SSO 主路径

---

## 怎么在 Apifox 里点（新人逐步）

### A. 换 Token（每条 SSO 前先做，Token 过期也重做）

1. 打开 **Apifox**。
2. 右上角环境选 **UAT (canary节点)** 或 **developer-sandbox**。
3. 左侧点 **`POST /v2/auth/token`**（SSO 那套，不要点会籍 3475754）。
4. 确认 Body/数据集里 **ProgramID = `1919256841868288`**。
5. 点 **发送**（不要点自动化「运行」）。
6. 看响应：`code` 必须是 **0**，复制 `data.access_token`（或确认环境变量 `access_token` 已更新）。

失败：`201.000.001` → Program 勾错了。

### B. 调 SSO（调试用「发送」，不要用集合「运行」）

1. 左侧点 **`POST /v2/sso/links`**。  
   URL 栏最终应是：`https://developer-sandbox.dragonpass.com/api/v2/sso/links`。
2. **Params** 不要乱加。
3. **Headers** 勾选并填写：

| 是否勾选 | 键 | 值 |
|----------|-----|-----|
| 勾 | Authorization | `Bearer {{access_token}}` |
| 勾 | X-Program-ID | `1919256841868288` |
| 勾 | Content-Type | `application/json` |
| 勾 | x-version | `canary` |
| 勾 | X-Request-ID | `{{$string.uuid}}` |

4. **Body** 选 JSON，按下面各用例粘贴。
5. 点 **发送**。
6. 成功：`code=0`，复制 `data.entry.shortUrl`。
7. 浏览器打开该 URL（测打开/过期时 `durationInSeconds` 用 1800，不要用 60）。

集合「运行」常会跑前置脚本 **改写 Body**，导致你界面上改的 JSON 没发出去。

---

## 接口测试用例（按脑图设计）

表头按公司规范。**预期结果 = 脑图/文档约定。** canary 不一致单独写在「canary 备注」。

### 6.1 正常流程（P0 先跑这 4 条）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-N-001 | 正常 | 换 Token 成功 | SSO 数据集 | 按上面 A 发 `/v2/auth/token` | `code=0`，有 access_token | P0 |
| SSO-N-002 | 正常 | ORDER_LIST 出链 | Token 有效；会籍 8576507744260001 | 点发送，Body 用下方「列表成功包」 | `code=0`；回显 scene=`ORDER_LIST`；有 shortUrl、validUntil | P0 |
| SSO-N-003 | 正常 | 打开列表短链免登 | 已有未过期 shortUrl（duration=1800） | 浏览器打开 shortUrl | 不出现登录页；进入订单列表；URL 含 `/standard-public/`；身份是该会籍。Upcoming 为空也算过 | P0 |
| SSO-N-004 | 正常 | ORDER_DETAIL 出链并打开 | 已从列表 Past/Cancelled 抄到真实 orderId | Body 用「详情成功包」发送；再打开新 shortUrl | `code=0`；回显 `ORDER_DETAIL`；打开后 URL 含 `/standard-lfd/`；订单号一致；不回登录页 | P0 |

**列表成功包（SSO-N-002 / SSO-REQ-004 / SSO-STD-001）：**

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_LIST",
  "language": "en-US",
  "durationInSeconds": 1800
}
```

**详情成功包（SSO-N-004 / SSO-STD-002）：** 把 `真实订单号` 换成你抄的。

```json
{
  "subject": { "type": "MEMBERSHIP", "id": "8576507744260001" },
  "scene": "ORDER_DETAIL",
  "language": "en-US",
  "durationInSeconds": 1800,
  "extra": { "orderId": "真实订单号" }
}
```

---

### 6.2 必填校验（脑图 1）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-REQ-001 | 必填 | scene 必填 | 有效 Token | Body 不传 scene，其余同列表成功包 | 失败；提示 scene 必填 | P0 |
| SSO-REQ-002 | 必填 | order_detall 缺 orderId | 有效 Token | `"scene":"order_detall"`，不传 extra.orderId，**仍带** language+duration | `code=-1`；`errCode=500.000.602`；文案=`The extra.{fieldName} field is required when scene is {scene}.` | P0 |
| SSO-REQ-003 | 必填 | order_detall 空 orderId | 有效 Token | scene=`order_detall`，`extra.orderId=""` | 同上 602 | P0 |
| SSO-REQ-004 | 必填 | order_list 不强制 extra | 合法会籍 | scene=`order_list` 或不传 extra | 成功；有 shortUrl、validUntil | P0 |
| SSO-REQ-005 | 必填 | ORDER_DETAIL 缺 extra.orderId | 有效 Token | scene=`ORDER_DETAIL`，不传 extra（或只缺 orderId） | 602；fieldName=orderId，scene=ORDER_DETAIL | P0 |

canary 备注：REQ-002/005 曾出 `500.041.004` 或先被 `302` 缺 duration 拦住，**仍按 602 提缺陷**，不要改预期。

---

### 6.3 参数标准化（脑图 2）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-STD-001 | 标准化 | scene=order_list | 会籍合法 | scene 小写 order_list | 成功；回显 `ORDER_LIST` | P0 |
| SSO-STD-002 | 标准化 | scene=order_detall | 有真实 orderId | 小写 scene + 合法 extra.orderId | 成功；回显 `ORDER_DETAIL` | P0 |
| SSO-STD-003 | 标准化 | scene 非法值 | Token 有效 | scene=`XXX` | 失败；记录实际 errCode | P1 |
| SSO-STD-004 | 标准化 | 不传 language | Token 有效 | 列表包去掉 language | 成功；返回 language=`en-US` | P0 |
| SSO-STD-005 | 标准化 | language=zh-CN | 环境支持该语种 | 传 zh-CN，打开短链看页面语种 | 成功；回显一致；页语种一致（前端支持时） | P1 |
| SSO-STD-006 | 标准化 | H5SsoLanguageEnum 29 语种轮询 | ORDER_LIST；ForEach | 见下方 29 语种数组，逐个请求 | **每条成功**；回显 language=入参；有 shortUrl；失败语种记 `sso_lang_fail_list` | P0 |
| SSO-STD-007 | 标准化 | 不传 durationInSeconds | Token 有效 | 去掉 duration 字段 | 成功；用 validUntil 核对默认（文档 600s，开发确认 60 则回写） | P0 |
| SSO-STD-008 | 标准化 | 不传 returnUrl | Token 有效 | 不传 returnUrl | 成功仍出链 | P1 |
| SSO-STD-009 | 标准化 | returnUrl 合法 | Token 有效 | `"returnUrl":"https://www.ly.com"` | 成功；按约定携带 | P1 |
| SSO-STD-010 | 标准化 | subject=membership | 合法会籍 | type 小写或标准 MEMBERSHIP + 合法 id | 成功；subject 回显正确 | P0 |

canary 备注：STD-004/007 实际 `302.000.001`（当必填）；STD-006 中 `es-419` 曾 `301.000.001`。文档预期不变，提缺陷。新增 `pt-BR` / `zh-HK` / `zh-CN` 必须出链。

**29 语种（SSO-STD-006 ForEach 数据源，不含 DEFAULT）：**

```json
["en-US","ja-JP","de-DE","es-ES","fr-FR","it-IT","pl-PL","pt-PT","ru-RU","th-TH","uk-UA","vi-VN","pt-BR","ko-KR","zh-HK","zh-CN","es-419","fr-CA","ar-SA","ro-RO","bs-BA","sr-SP","sr-ME","hr-HR","nl-NL","el-GR","si-SI","he-IL","hu-HU"]
```

---

### 6.4 异常场景（脑图 3）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-ERR-001 | 异常 | ORDER_DETAIL 缺 extra 整对象 | Token 有效 | scene=ORDER_DETAIL，不传 extra | `500.000.602` + 标准提示语 | P0 |
| SSO-ERR-002 | 异常 | orderId 不存在 | Token 有效 | extra.orderId=`9999999999999999` 或明确不存在的单号 | 失败；**记录实际 errCode**（不要用 `123` 当唯一样本） | P1 |
| SSO-ERR-003 | 异常 | orderId 不属于该会籍 | 会籍 A + 会籍 B 真实订单 | subject=A，extra.orderId=B 的单 | 失败或无权查看 | P0 |
| SSO-ERR-004 | 异常 | subject.type 非法 | Token 有效 | type=`FOO` | 失败；记录 errCode | P1 |
| SSO-ERR-005 | 异常 | subject.id 不存在 | Token 有效 | MEMBERSHIP + `0000000000000000` | 会籍校验失败 | P1 |
| SSO-ERR-006 | 异常 | duration=59 | Token 有效 | durationInSeconds=59 | 失败或拒绝（范围 60～7200） | P0 |
| SSO-ERR-007 | 异常 | duration=7201 | Token 有效 | 7201 | 失败或拒绝 | P0 |
| SSO-ERR-008 | 异常 | duration 类型错误 | Token 有效 | `"durationInSeconds":"abc"` | 失败（类型校验） | P1 |
| SSO-ERR-009 | 异常 | 无 Token / Token 错误 | 去掉 Authorization 或改坏 | 发 SSO | 鉴权失败（如 401） | P0 |
| SSO-ERR-010 | 异常 | returnUrl 外域 | Token 有效 | returnUrl=`https://evil.com` | 按规则拦截；若仍成功可跳外域，记风险/缺陷 | P2 |
| SSO-ERR-011 | 异常 | Program 与 Token 不一致 | SSO Token + 会籍 Program | Header X-Program-ID 改成 `2032786406298624` | `201.000.001` | P0 |
| SSO-ERR-012 | 异常 | 缺 X-Request-ID | 去掉该 Header | 发 SSO | `301.000.001` 或 `302.000.001` | P1 |
| SSO-ERR-013 | 异常 | URL 写成 /api/api/v2 | 路径重复 | 观察 404 | 失败；路径错误 | P1 |

假 orderId 补充（与 ERR-002 区分）：canary 上 `SL20260901BGVF836` 一类无效/不可映射单曾返回 **`500.000.601`**（生成失败兜底），**不是 602**。602 只用于「DETAIL 且缺 orderId」。

---

### 6.5 边界与容错（脑图 4）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-BND-001 | 边界 | duration=60 | Token 有效 | durationInSeconds=60 | 成功；validUntil≈现在+60s（问开发允许误差） | P0 |
| SSO-BND-002 | 边界 | duration=7200 | Token 有效 | 7200 | 成功；validUntil≈现在+7200s | P0 |
| SSO-BND-003 | 边界 | 未过期可进入 | duration=1800 已出链 | 立刻打开 shortUrl | 免登进入；无登录页 | P0 |
| SSO-BND-004 | 边界 | 已过期不可进入 | duration=60 出链后等 >60 秒 | 再打开同一 shortUrl | 不可免登；记录过期页/提示 | P0 |

---

### 6.6 全链路（脑图 5）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-E2E-001 | 全链路 | 订单列表全链路 | 合法 membership | 出链 → 打开 → 看 path | 免登列表；`/standard-public/`；不登录；身份对 | P0 |
| SSO-E2E-002 | 全链路 | 订单详情全链路 | 该会籍真实订单 | 出链 → 打开 → 对订单号 | 免登详情；`/standard-lfd/`；单号一致 | P0 |
| SSO-E2E-003 | 全链路 | 会员身份全链路 | 合法会员 | subject=MEMBERSHIP 出链并打开 | 以该会员身份进页；数据归属正确 | P0 |
| SSO-E2E-004 | 全链路 | 访客模式不传 subject | Token 有效 | 去掉整个 subject | 按产品记录回显；脑图参考 type/id 为 null | P1 |

---

### 6.7 ORDER_LIST 分页 / loading（脑图 6）

当前会籍 Upcoming 可能为空，**先用有历史单的 Past**，或换订单更多的会籍。没数据不要判失败，标「阻塞：数据不足」。

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-PAGE-001 | 分页 | 先判定形态 | 订单建议 ≥2 页 | 打开列表，看有无页码或滚底 loading | 记录「分页」或「loading」；截图 | P0 |
| SSO-PAGE-002 | 分页 | 翻页成功 | 已确认是分页 | 1 页→2 页→回 1 页 | 条数对；数据不错乱；无长时间白屏 | P1 |
| SSO-PAGE-003 | 分页 | 末页与超出 | 已知总页 | 末页再下一页 | 不崩溃；空列表或提示 | P1 |
| SSO-PAGE-004 | loading | 滚底加载 | 已确认逐步加载 | 滚到底等下一段 | 追加不覆盖；不异常重复 | P1 |
| SSO-PAGE-005 | loading | 已无更多 | 已到最后一段 | 再滚底 | 不一直转圈；不重复追加 | P1 |
| SSO-PAGE-006 | 分页 | 筛选+分页 | 列表有筛选时 | 加条件再翻页；改条件重查 | 从第 1 页/段重载 | P2 |
| SSO-PAGE-007 | 分页 | 免登下翻页全链路 | 订单足够多 | 出链→打开→翻页或滚加载 ≥1 次 | 全程免登；不回登录页 | P0 |

---

### 6.8 短链一致性（脑图 7）

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-IDEMP-001 | 一致性 | 相同入参 ≥3 次 | 固定同一套 Body | 连续发送 3 次，记下 shortUrl、validUntil | **shortUrl 一致**（产品若定义为每次新链则改预期） | P0 |
| SSO-IDEMP-002 | 一致性 | ORDER_LIST 相同入参 ≥2 次 | scene=ORDER_LIST 固定 | 连发 2 次 | shortUrl 一致 | P0 |
| SSO-IDEMP-003 | 一致性 | ORDER_DETAIL 相同 orderId ≥2 次 | 同一真实 orderId | 连发 2 次 | shortUrl 一致 | P0 |
| SSO-IDEMP-004 | 一致性 | 入参变化后链接可变 | Token 有效 | 链 A 后只改 scene 或 orderId 得链 B | A 与 B 可以不同 | P1 |

---

## Header / 方法补充用例

| 用例编号 | 模块 | 测试标题 | 前置条件 | 测试步骤 | 预期结果 | 优先级 |
|----------|------|----------|----------|----------|----------|--------|
| SSO-HDR-001 | Header | Content-Type 不是 JSON | Token 有效 | 改成 text/plain | 失败 | P2 |
| SSO-MTH-001 | 方法 | GET 调 SSO | Token 有效 | 方法改 GET | 失败（405 或框架错误） | P2 |

---

## 测试范围

- 接口：`POST /v2/sso/links`（含 Header、Body、错误码）
- 浏览器：列表免登、详情免登、过期、分页/loading（有数据时）
- 不含：EPASS / CLIENT_USER 细测（脑图本期不做）；会籍购买 039～045；FT 030

## 测试风险

1. canary 把 language/duration 当必填，负向用例到不了 602。
2. DETAIL 没有真实 orderId 会误报 601，当成接口坏了。
3. 集合「运行」改写 Body。
4. 混 Program 导致 201，误判 SSO 挂了。
5. duration=60 出的链来不及打开页面。
6. 列表空 ≠ 出链失败。

## 回归建议

发版后必回归：N-001～004、REQ-001/004/005、ERR-006/007/009、BND-001～004、E2E-001/002、STD-006 抽样 en-US + 1 个非英文。

## 自动化建议

| 适合自动化 | 建议人工 |
|------------|----------|
| 出链成功/失败码、26 语种、duration 59/60/7200/7201、缺 scene、缺 Token、错 Program | 打开短链免登、过期页、分页/loading、页面语种、越权看到的页面内容 |

导入集合：`interface_cursor/tools/sso-links-q3-sp4/PAPI-SSO免登短链-全量自动化.postman_collection.json`  
**调试单条请用接口「发送」，不要用自动化「运行」。**

## 执行顺序

1. SSO-N-001 Token  
2. SSO-N-002 / REQ-004 列表出链  
3. SSO-N-003 / E2E-001 打开列表（**今天优先补这条**）  
4. 抄真实 orderId → N-004 / E2E-002 详情  
5. REQ-001、ERR-006/007、BND-001/002  
6. REQ-002/005（记 602 vs 实际码）  
7. STD-004/007（记可选变必填）  
8. STD-006 语种  
9. BND-004 过期  
10. 分页（有数据再测）  
11. 其余 P1/P2  

---

## XMind 结构（可复制）

```
一、SSO免登短链
├── 接口 POST /v2/sso/links
├── 1.必填
│   ├── scene必填
│   ├── DETAIL缺/空orderId → 500.000.602
│   └── LIST不强制extra
├── 2.标准化
│   ├── scene大小写
│   ├── language默认/26语种
│   ├── duration默认
│   └── returnUrl / subject
├── 3.异常
│   ├── 602 / 601 / 假单号
│   ├── 越权orderId
│   ├── duration越界
│   └── Token / Program
├── 4.边界
│   ├── 60 / 7200
│   └── 过期前后打开
├── 5.全链路
│   ├── 列表免登
│   ├── 详情免登
│   └── 访客模式
├── 6.分页/loading
└── 7.短链一致性
```

---

## 待开发/产品确认（不要自己改预期）

1. `language` / `durationInSeconds` 文档可选，canary 是否已改必填？  
2. 缺 `extra.orderId` 最终码是 `500.000.602` 还是 `500.041.004`？  
3. `es-419` 是否在 SSO 白名单？  
4. 相同入参 `shortUrl` 必须一致还是每次新链？  
5. duration 默认 600 还是 60？  
6. 访客模式 subject 是否必须回显 null？  
7. returnUrl 外域是否强制拦截？  

---

## 新人最容易漏测的地方

1. **只看到接口 `code=0` 就打勾，不打开 shortUrl** —— 免登、path、登录页才是 P0。  
2. **ORDER_DETAIL 用假单号 `123`** —— 会出 `500.000.601`，测不到 602，也测不到详情页。  
3. **把 601 当成 602** —— 601=生成失败；602=DETAIL 缺 orderId。  
4. **duration 填 60 再去打开页面** —— 链已过期，误判免登失败；打开页面用 1800。  
5. **自动化点「运行」** —— 前置脚本改 Body，界面 JSON 没发出去。  
6. **Token 和 Program 不是 SSO 那套** —— `201.000.001`，不是短链逻辑坏了。  
7. **URL 写成 `/api/api/v2/sso/links`**。  
8. **X-Request-ID 手改截断** —— `301.000.001`。  
9. **语种只测 en-US**，漏 26 轮询和 `es-419`。  
10. **duration 只测中间值**，漏 59/7201/60/7200 和过期后再打开。  
11. **会籍 A 打开会籍 B 的详情（越权）没测**。  
12. **列表 Upcoming 为空就报接口失败** —— 空列表可以是正常。  
13. **相同入参多次 shortUrl 是否一致没记**。  
14. **canary 与文档不一致时改用例预期** —— 应提缺陷，脑图预期先保留。
