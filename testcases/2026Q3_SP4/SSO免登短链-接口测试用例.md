# SSO 免登短链 — 接口测试用例

> 来源：`c:\Users\dragonpass\Desktop\需求测试用例.xmind` → **一、SSO免登短链**  
> 接口：`POST /api/v2/sso/links`（Apifox 环境 `baseUrl` 已含 `/api` 时写 `/v2/sso/links`）  
> 语种轮询口径：H5SsoLanguageEnum（不含 DEFAULT，共 **29**）  
> 生成日期：2026-09-04

---

## 一、需求摘要（通俗）

调用接口生成**短时免登 H5 链接**：打开后无需再登录，直接进入「订单列表」或「订单详情」。可指定身份（会籍等）、语种、链接有效期、回跳地址。

---

## 二、接口说明

| 项 | 内容 |
|----|------|
| Method | `POST` |
| Path | `/api/v2/sso/links` |
| Header | `Authorization: Bearer {{access_token}}`、`X-Program-ID: {{Program-ID}}`、`Content-Type: application/json` |
| 鉴权 | 有效 Token + Program 与数据归属一致 |

### Body 字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `scene` | 是 | `ORDER_LIST` / `ORDER_DETAIL`（脑图亦写 order_list / order_detall，以实返标准化大写为准） |
| `subject.type` / `subject.id` | 否 | MEMBERSHIP / EPASS / CLIENT_USER；不传=游客 |
| `language` | 否 | 默认 `en-US` |
| `durationInSeconds` | 否 | 合法范围 **60～7200**；默认脑图写 600（若开发确认 60 以实为准） |
| `returnUrl` | 否 | 默认空 |
| `extra.orderId` | 条件 | **仅 `ORDER_DETAIL` 必填** |

### 成功关键返回

- `entry.shortUrl`
- `entry.validUntil`
- 回显 `scene` / `language` / `subject`（有入参时）

### 关键错误

| errCode | 场景 |
|---------|------|
| `500.000.602` | ORDER_DETAIL 缺 `extra.orderId`（或缺 extra）；文案：`The extra.{fieldName} field is required when scene is {scene}.` |
| 401 等 | Token 无效/缺失 |

---

## 三、语种轮询列表（ForEach 条件）

严格用于「语种遍历 / language 合法值轮询」自动化，数据源贴此数组：

```json
[
  "en-US",
  "ja-JP",
  "de-DE",
  "es-ES",
  "fr-FR",
  "it-IT",
  "pl-PL",
  "pt-PT",
  "ru-RU",
  "th-TH",
  "uk-UA",
  "vi-VN",
  "pt-BR",
  "ko-KR",
  "zh-HK",
  "zh-CN",
  "es-419",
  "fr-CA",
  "ar-SA",
  "ro-RO",
  "bs-BA",
  "sr-SP",
  "sr-ME",
  "hr-HR",
  "nl-NL",
  "el-GR",
  "si-SI",
  "he-IL",
  "hu-HU"
]
```

- 建议 scene 固定：`ORDER_LIST`（不强制 extra）  
- Body：`"language": "{{item}}"`（或 ForEach 当前项变量名）  
- 预期：每条成功；回显 language 与请求一致；返回 `shortUrl`  
- 脚本目录：`D:\api\interface_cursor\tools\sso-links-q3-sp4\`

---

## 四、接口测试用例（严格按脑图）

### 4.1 必填校验

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-REQ-001 | scene必填 | 有效 Token | 不传 `scene`，其余合法 | 失败；提示 scene 必填 | P0 |
| SSO-REQ-002 | ORDER_DETAIL缺orderId（小写笔误场景） | 有效 Token | `scene=order_detall`，不传 `extra.orderId` | 失败；`errCode=500.000.602`；文案含 extra.orderId 与 scene；完整提示=`The extra.{fieldName} field is required when scene is {scene}.` | P0 |
| SSO-REQ-003 | ORDER_DETAIL空orderId | 有效 Token | `scene=order_detall`，`extra.orderId=""` | 失败；`500.000.602`；同上提示语 | P0 |
| SSO-REQ-004 | ORDER_LIST不强制extra | 有效 Token；合法 membership | `scene=order_list`，不传 extra | 成功；返回 `entry.shortUrl`、`entry.validUntil` | P0 |
| SSO-REQ-005 | ORDER_DETAIL缺extra.orderId（标准大写） | 有效 Token | `scene=ORDER_DETAIL`，不传 extra.orderId（或缺 extra） | 失败；`500.000.602`；提示语=`The extra.{fieldName} field is required when scene is {scene}.`（fieldName=orderId，scene=ORDER_DETAIL） | P0 |

### 4.2 参数标准化校验

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-STD-001 | scene=order_list | Token；subject.type=membership+合法id | 合法请求 | 成功；回显 scene=`ORDER_LIST`；有 shortUrl、validUntil | P0 |
| SSO-STD-002 | scene=order_detall | Token；该会籍下合法 orderId | 传合法 extra.orderId | 成功；回显 scene=`ORDER_DETAIL`；有 shortUrl、validUntil | P0 |
| SSO-STD-003 | scene非法值 | Token | scene=`XXX` | 失败；记录实际 errCode（与开发对齐） | P1 |
| SSO-STD-004 | language不传 | Token | 不传 language | 成功；返回 `language=en-US` | P0 |
| SSO-STD-005 | language传非英文合法值 | Token；环境支持目标语种 | 传 `language=zh-CN`（或以实支持为准） | 成功；回显一致；打开短链页语种一致（若前端支持） | P1 |
| SSO-STD-006 | **language 29语种轮询** | Token；`ORDER_LIST`；合法 subject | ForEach 上表 29 语种，逐个请求 | **每条成功**；回显 language=入参；有 shortUrl；记录失败语种到 `sso_lang_fail_list` | P0 |
| SSO-STD-007 | durationInSeconds不传 | Token | 不传 durationInSeconds | 成功；用 validUntil 核对默认有效期（文档默认 600s，开发确认默认 60 则回写） | P0 |
| SSO-STD-008 | returnUrl不传 | Token | 不传 returnUrl | 成功；按空默认仍可生成短链 | P1 |
| SSO-STD-009 | returnUrl传合法地址 | Token | 传业务允许域名 | 成功；按约定携带 | P1 |
| SSO-STD-010 | subject传membership | 合法会籍 | subject.type=membership+合法id | 成功；subject 回显正确 | P0 |

### 4.3 异常场景

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-ERR-001 | ORDER_DETAIL缺extra整对象 | Token | scene=ORDER_DETAIL，不传 extra | `500.000.602`；标准提示语 | P0 |
| SSO-ERR-002 | orderId不存在 | Token | ORDER_DETAIL + 不存在的 orderId | 失败；记录实际 errCode | P1 |
| SSO-ERR-003 | orderId不属于该会籍 | 会籍A + 会籍B真实订单 | subject=A，extra.orderId=B的订单 | 失败或无权查看 | P0 |
| SSO-ERR-004 | subject.type非法 | Token | type=非法值 | 失败；记录 errCode | P1 |
| SSO-ERR-005 | subject.id不存在 | Token | MEMBERSHIP + 不存在 id | 会籍校验失败 | P1 |
| SSO-ERR-006 | durationInSeconds=59 | Token | 59 | 失败或拒绝（范围 60～7200） | P0 |
| SSO-ERR-007 | durationInSeconds=7201 | Token | 7201 | 失败或拒绝 | P0 |
| SSO-ERR-008 | durationInSeconds类型错误 | Token | `"abc"` | 失败（类型校验） | P1 |
| SSO-ERR-009 | 无Token或Token错误 | 无/坏 Authorization | 调用接口 | 鉴权失败（如 401） | P0 |
| SSO-ERR-010 | returnUrl非法或外域 | Token | evil.com 或非 URL | 按规则拦截/失败；若仍成功可跳外域记缺陷/风险 | P2 |

### 4.4 边界与容错

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-BND-001 | durationInSeconds=60 | Token | 60 | 成功；validUntil≈now+60s（误差与开发确认） | P0 |
| SSO-BND-002 | durationInSeconds=7200 | Token | 7200 | 成功；validUntil≈now+7200s | P0 |
| SSO-BND-003 | 链接未过期可进入 | 已生成未过期短链 | 有效期内打开 shortUrl | 免登进入；不出现登录页 | P0 |
| SSO-BND-004 | 链接已过期不可进入 | duration=60 生成后等到过期 | 过期后打开 shortUrl | 不可免登；记录实际过期页/提示 | P0 |

### 4.5 全链路业务场景

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-E2E-001 | 订单列表全链路 | Token；合法 membership | 1）ORDER_LIST 生成短链 2）打开 shortUrl 3）看 path | 免登进列表；URL 含 `/standard-public/`；不登录页；身份对应该会籍 | P0 |
| SSO-E2E-002 | 订单详情全链路 | 该会籍真实订单 | 1）ORDER_DETAIL+orderId 2）打开 3）看 path 与订单号 | 免登进详情；URL 含 `/standard-lfd/`；订单号一致；不登录页 | P0 |
| SSO-E2E-003 | 会员身份全链路 | 合法会员 | subject=MEMBERSHIP 生成并打开 | 以该会员身份进入；数据归属正确 | P0 |
| SSO-E2E-004 | 访客模式（不传subject） | Token | 不传 subject | 按产品：subject type/id 为 null 的回显是否如下（脑图待确认）；记录实际展示 | P1 |

访客模式脑图期望回显参考：

```json
{
  "subject": {
    "type": null,
    "id": null
  }
}
```

### 4.6 ORDER_LIST 分页 / loading 逐步加载

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-PAGE-001 | 先判定形态 | MEMBERSHIP；订单≥2页量 | 生成 ORDER_LIST 短链并打开；观察分页控件或滚底 loading | 明确记录「分页」或「loading逐步加载」；截图 | P0 |
| SSO-PAGE-002 | 分页-翻页成功 | 已确认分页 | 第1页→第2页→回第1页 | 条数符合配置；数据变化不错乱；带 page/pageSize；无长时间白屏 | P1 |
| SSO-PAGE-003 | 分页-末页与超出 | 已知总页 | 末页；再下一页/超页码 | 末页剩余条数；超出不崩溃（空列表/提示） | P1 |
| SSO-PAGE-004 | loading-滚底加载 | 已确认逐步加载 | 滚到底→loading→下一段 | loading 出现后追加不覆盖；不异常重复；loading 结束 | P1 |
| SSO-PAGE-005 | loading-已无更多 | 已到最后一段 | 再滚底 | 无更多/不再请求；不一直转圈；不重复追加 | P1 |
| SSO-PAGE-006 | 筛选+分页/加载 | 若列表有筛选 | 加条件再翻页/加载；改条件重查 | 改条件从第1页/第1段重载；结果符合筛选 | P2 |
| SSO-PAGE-007 | 免登下分页全链路 | MEMBERSHIP；订单足够多 | 生成短链→打开→翻页或滚加载≥1次 | 免登；URL 含 `/standard-public/`；过程不回登录页 | P0 |

### 4.7 多次请求短链一致性

| 用例ID | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 |
|--------|----------|----------|------|----------|--------|
| SSO-IDEMP-001 | 相同入参连续多次 shortUrl一致 | 固定同一套合法入参 | 相同 Body 连续 ≥3 次，记录 shortUrl、validUntil | **shortUrl 一致**；validUntil 按约定；默认按「一致」验收（若产品定义为每次新链则改预期） | P0 |
| SSO-IDEMP-002 | ORDER_LIST 相同入参≥2次 | scene=ORDER_LIST 固定 | 相同 Body ≥2 次 | shortUrl 一致 | P0 |
| SSO-IDEMP-003 | ORDER_DETAIL 相同orderId≥2次 | 同一 orderId 固定 | 相同 Body ≥2 次 | shortUrl 一致 | P0 |
| SSO-IDEMP-004 | 入参变化后链接可变（对照） | Token | 固定得链A；仅改 orderId 或 scene 得链B | A 与 B 可以不同 | P1 |

---

## 五、正常 / 异常 / 边界（汇总对照脑图）

### 正常流程（最小闭环）

1. 换 Token → 设 `Program-ID`  
2. `scene=ORDER_LIST` + `subject` → 得 `shortUrl`  
3. 浏览器打开 → 免登进列表  
4. `scene=ORDER_DETAIL` + `extra.orderId` → 得短链 → 打开进详情  

### 异常（必测）

- 缺 scene / ORDER_DETAIL 缺 orderId → 602  
- 越权 orderId、非法 subject、鉴权失败  
- duration 59 / 7201 / 类型错误  

### 边界

- duration 60 / 7200  
- 短链过期前后  
- 29 语种轮询  

---

## 六、Apifox 自动化挂载（语种轮询）

1. 场景加 **ForEach**，数据源贴第三节 JSON 数组  
2. 循环内：`POST {{baseUrl}}/v2/sso/links`  
3. 前置：`tools/sso-links-q3-sp4/apifox_pre_sso_links.js`  
4. 后置：`tools/sso-links-q3-sp4/apifox_post_sso_links.js`  
5. 环境：`sso_scene=ORDER_LIST`，`sso_subject_type`，`sso_subject_id`，`access_token`，`Program-ID`  
6. 或导入：`PAPI-SSO免登短链-语种遍历-BOSS-API.postman_collection.json`

样例 Body：

```json
{
  "subject": {
    "type": "MEMBERSHIP",
    "id": "{{sso_subject_id}}"
  },
  "scene": "ORDER_LIST",
  "language": "{{item}}",
  "durationInSeconds": 60
}
```

---

## 七、回归范围

- SSO 建链（LIST/DETAIL）  
- 短链打开免登（列表/详情 URL path）  
- 602 文案  
- 语种默认 en-US + 29 语种轮询  
- duration 边界与过期  
- 短链多次请求一致性  
- ORDER_LIST 分页/loading（若本期前端有）  

---

## 八、新人最容易漏测

1. **ORDER_DETAIL 只测有 orderId，漏测缺/空 orderId 的 `500.000.602` 完整文案**  
2. **只调接口成功，不打开 shortUrl 验免登与 URL path**（`/standard-public/` vs `/standard-lfd/`）  
3. **会籍 A 打开会籍 B 的订单详情（越权）**  
4. **duration 只测中间值，漏 59/7201/60/7200 与过期后打开**  
5. **语种只测 en-US，漏 29 语种轮询（尤其新增 pt-BR / zh-HK / zh-CN）**  
6. **相同入参多次请求 shortUrl 是否一致未记**  
7. **ORDER_LIST 有多页数据时，未区分分页 vs loading 逐步加载**  
8. **Token/Program 与 subject 会籍不是同一套，误判接口失败**  

---

## 九、待与开发确认（脑图已标）

1. scene 入参大小写（order_list / ORDER_LIST）最终标准化规则  
2. `durationInSeconds` 默认是 **600** 还是 **60**  
3. 相同入参多次请求 shortUrl **必须一致** 还是允许每次新链  
4. 访客模式 subject 回显是否必须为 null  
5. returnUrl 外域是否强制拦截  
