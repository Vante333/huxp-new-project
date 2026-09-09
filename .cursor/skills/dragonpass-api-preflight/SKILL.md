---
name: dragonpass-api-preflight
description: >-
  DragonPass 接口测前检查：环境域名与凭证配对、Apifox 环境变量、必带 Headers、
  先 Auth 冒烟再跑业务。Use when user mentions 变量检查、headers、201.000.001、
  invalid secret、PRE/gray、sandbox/canary、测前检查、接口能不能跑通、换 Token、
  X-Program-ID、X-Request-ID、UK-生产环境-PRE，或改 Apifox 场景前要先验证鉴权。
---

# DragonPass 接口测前检查（变量 + Headers）

改用例 / 发 curl / 跑 Apifox **之前**，必须先做本检查。不要用 PRE 密钥打沙箱，也不要 Token 与 Program 混套。

## 1. 环境配对（最易错）

| 环境 | Host（baseUrl 去掉路径后） | x-version | 凭证从哪来 |
|------|------------------------------|-----------|------------|
| **PRE** | `https://developer.dragonpass.com` | `gray` | PRE epass / PRE membership（见下表） |
| **沙箱 UAT** | `https://developer-sandbox.dragonpass.com` | `canary` | 沙箱 AllCategories 等（见数据集 skill） |

**禁止：** PRE 的 `clientId/secret` + `developer-sandbox` → 必 `201.000.001`。  
**禁止：** membership Token + epass `X-Program-ID`（或反过来）。

### 已验证可通（Auth `code=0`）

**PRE epass**

- ProgramID：`1946131279295488`
- clientId：`<本机 skill，不入库>`
- secret：`<本机 skill，不入库>`
- Host：`developer.dragonpass.com`，`x-version: gray`

**PRE membership**

- ProgramID：`1861959515628544`
- clientId：`<本机 skill，不入库>`
- secret：`<本机 skill，不入库>`
- Host：`developer.dragonpass.com`，`x-version: gray`

**沙箱 AllCategories（会籍错误码 039/044/045 冒烟用）**

- ProgramID：`1919256841868288`
- clientId：`<本机 skill，不入库>`
- secret：`<本机 skill，不入库>`
- Host：`developer-sandbox.dragonpass.com`，`x-version: canary`

更全的桌面数据集见 skill `api-test-datasets`。

## 2. Apifox 环境变量清单

跑场景前打开当前环境（如 `UK-生产环境-PRE`），确认：

| 变量 | 用途 | 注意 |
|------|------|------|
| `baseUrl` | 如 `https://developer.dragonpass.com/api` | 与 Host 一致，末尾 `/api` |
| `ProgramID` / `Program-ID` | Header | 两名都建议有，值相同 |
| `clientId` / `secret` | 仅 Auth Body | 与 Program 同套 |
| `accessToken` / `access_token` | 业务 Header | Auth 后写入；Header 别写错变量名 |
| `x-version` | Header | PRE=`gray`；沙箱=`canary` |
| `sso_epass_subject_id` | SSO `subject.id`（EPASS） | 不写死在步骤 Body，用 `{{ }}` |
| `sso_lounge_orderId` | SSO 603 用休息室 `SL…` | 真实单；假单易 601 |
| `sso_subject_id` | SSO MEMBERSHIP 主体 | |
| `err_fake_orderId` / `err_fake_membershipId` | 错误码冒烟 | 可默认假号 |
| `err_profile_email` / `err_profile_phone` | Preview profile | |

Body / Header **用 `{{变量名}}`**，不要在场景步骤里写死 Program、会籍号、订单号（脚本仅在变量为空时补默认）。

## 3. Headers 必须写好

### Auth：`POST {{baseUrl}}/v2/auth/token`

```http
X-Program-ID: {{ProgramID}}
x-version: {{x-version}}
X-Request-ID: <36位UUID，每次新>
Content-Type: application/json
Accept: */*
```

Body：

```json
{
  "clientId": "{{clientId}}",
  "secret": "{{secret}}"
}
```

成功：`code=0` 且有 `data.accessToken` → 写入 `accessToken` 与 `access_token`。

### 业务接口（SSO / 支付 / 可用性 / 会籍等）

```http
Authorization: Bearer {{accessToken}}
X-Program-ID: {{ProgramID}}
x-version: {{x-version}}
X-Request-ID: <36位UUID，每次新>
Content-Type: application/json
Accept: */*
```

缺 `X-Request-ID` → 常 `302.000.001`。  
Token 与 Program 不一致 → 常 `201.000.001`。

## 4. 测前检查流程（Agent / 人工都要做）

1. **定环境**：PRE 还是沙箱？选对 `baseUrl` + `x-version`。  
2. **定凭证套**：epass / membership / AllCategories，Program+clientId+secret 同一行。  
3. **先单独打 Auth**：只要 `201.000.001` 就停，先修变量/域名，不要跑整场景。  
4. **再打一条目标业务**（如 SSO links / preview / availability），确认不是鉴权错。  
5. **再改用例 / 跑套件**。

本机可用 node/curl 冒烟 Auth；不要假设环境变量已配对。

## 5. 常见报错对照

| errCode | 常见原因 | 处理 |
|---------|----------|------|
| `201.000.001` | 域名/凭证/Program/Token 混套 | 按第 1 节重配，重新换 Token |
| `302.000.001` | 缺必填（如 `X-Request-ID`、缺字段） | 补 Header / Body |
| `301.000.001` | 字段格式非法 | 查枚举、duration 范围等 |
| `500.000.601` | SSO 兜底 | 查单号/scene；休息室 SL 详情期望可能是 603 |
| `500.000.603` | SSO 不支持该页（如休息室详情） | `ORDER_DETAIL` + 真实 `SL…` |

## 6. PRE 会籍 / SSO 注意

- membership **Auth 可成功**，但会籍购买 `preview|details|cancellation` 以及 **membership Token 调 SSO** 仍可能 `201.000.001`。
- PRE 上 SSO / FT / 支付参数校验用 **epass 套** + `subject.type=EPASS`。不要用 membership Token 打 SSO。
- 休息室 `ORDER_DETAIL` + 真实 `SL…` 在 PRE 已返回 `500.000.603`。
- 验迁移码 `039/044/045` 用 **沙箱 canary + AllCategories**（场景「会籍错误码迁移 · 冒烟」）。

## 7. 改 Apifox 场景时

- 路径用 `{{baseUrl}}/v2/...`
- Header 用上一节模板 + `{{ }}`
- 步骤前置：空变量才 `set` 默认，**不要强制覆盖**用户环境已有值（除非用户明确要求写死）
- Push 后：先 `apifox run` 单场景验证，再让用户跑全量
