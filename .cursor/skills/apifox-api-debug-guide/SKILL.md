---
name: apifox-api-debug-guide
description: Apifox接口测试完整新手指南。涵盖BOSS系统SHA256签名认证调试、SAAS IAM登录获取Token、环境配置、签名前置脚本编写、接口克隆导入、多接口依赖数据追踪、常见401/404/业务错误排查、接口文档字段预提取与枚举差异排查。当用户提到Apifox调试、BOSS API签名、SHA256签名认证、SAAS登录获取token、接口401/404报错、签名前置脚本、接口克隆导入、Gateway接口测试、接口字段枚举错误时使用。
version: 1.2.0
---

# Apifox 接口测试新手引导（BOSS + SAAS）

## 讲解粒度（强制）

用户原话：「你这样说的太模糊了不够详细请你说的在详细一点好嘛？」

对测试新人讲解任何一步时，禁止只给接口路径+一段 JSON。必须细到：

1. 打开哪个软件（Apifox / 浏览器 / BOSS 后台）
2. 点左侧哪个菜单、哪个接口名
3. 右上角环境选哪一个（完整环境名 + 前置 URI 全文）
4. URL 栏逐字该留下什么、不该留下什么
5. Headers 每一行：勾选状态、参数名、参数值（是否加 Bearer）
6. Body 是整段可复制的 JSON，并逐字段说明从哪抄
7. 点「发送」还是「运行场景」；禁止默认走自动化测试
8. 成功时长什么样（该抄哪个返回字段）
9. 失败时按 HTTP 码 / msg 给出下一步点哪里改

不要用「切到 BOSS 项目」「配好签名」这类一句话带过。

## 适用场景

本技能面向刚接触 BOSS 对外 API 的新人，帮助在 Apifox 中从零完成第一个接口调试。典型场景包括：配置测试环境、编写 SHA256 签名前置脚本、克隆或导入共享接口文档、按业务流程逐步调通接口链路，以及排查 401/404/业务错误。

## 第零步：接口文档字段预提取（强制）

> **⚠️ 铁律：调试任何新接口之前，必须先完整提取该接口的全部必填字段。严禁「发一次请求→报错→加一个字段→再发→再报错」的逐字段试错方式。**

### 0.1 为什么必须先读文档

逐字段试错的危害：每多一次无效请求就多浪费用户几分钟等待，5 次以上会严重消耗耐心。正确做法是在发送第一个请求之前，就把所有必填字段、枚举值、格式要求全部搞清楚。

### 0.2 提取方法

**方式一：PDF 文档提取（推荐）**

```bash
# 将 PDF 转为纯文本
pdftotext -layout "BOSS系统对外API 文档.pdf" boss-api.txt

# 搜索目标接口的字段定义
grep -A 50 "agreement/add" boss-api.txt
```

提取后，整理为如下格式备用：

```
接口：POST /xxx/agreement/add
必填字段：
  - customerCode (string) — 客户编码，如 DPC000550
  - contractCode (string) — 合同编码，如 A001-XS-2026-000221
  - agreementName (string) — 协议名称
  - agreementType (string) — 枚举：standard / framework / generic
  - beginDate (date) — 格式 yyyy-MM-dd
  - endDate (date) — 格式 yyyy-MM-dd
  - profitCode (string) — 龙腾在用部门ID，如 DP086
  - businessMode (string) — 枚举：b2b
  - ...（列出全部字段）
```

**方式二：OpenAPI/Swagger 文档**

如果有 JSON/YAML 格式的 OpenAPI 文件，直接搜索 endpoint path，查看 `requestBody.content.application/json.schema.required` 数组获取必填字段列表。

**方式三：Apifox 已导入的接口定义**

在 Apifox 中打开接口详情 → Body 标签页 → 查看参数表中标有「必填」的字段。

### 0.3 执行检查清单

在发送第一个请求之前，确认以下全部完成：

1. ✅ 已提取目标接口的完整字段列表（必填 + 选填）
2. ✅ 每个枚举类型字段已确认有效枚举值（优先参考已成功的请求样例，而非仅看文档描述）
3. ✅ 每个编码类字段（xxxCode）已确认填入的是前序接口实际返回的值
4. ✅ 日期格式、数值精度等格式要求已确认
5. ✅ 构造的请求体包含全部必填字段，无遗漏

---

## 第一步：环境配置

### 1.1 新建项目

打开 Apifox 客户端，点击左上角「+ 新建项目」，项目名称填 `BOSS接口测试`，项目类型选 `HTTP`，点击「创建」。

### 1.2 创建测试环境

1. 点击左上角项目名旁边的「环境」下拉框
2. 点击「环境设置」
3. 点击「+ 新建环境」
4. 环境名称填：`TEST测试环境`
5. URL 前缀填入：

```
https://business-finance-gateway-test.dragonpass.com.cn
```

> 注意：如果测试的是 SAAS 相关接口，URL 前缀应改为 `https://quanyi-intl-test.dragonpass.com.cn`

### 1.3 配置环境变量

在环境设置页面的「环境变量」区域，添加以下变量：

| 变量名    | 变量值         | 说明           |
|-----------|----------------|----------------|
| appId     | fanwei-test    | 测试环境应用ID |
| appkey    | 123456         | 测试环境密钥   |

> 正式环境的 appId 和 appkey 需要从项目负责人处获取，切勿混用。

### 1.4 关键注意事项

**URL 前缀与接口路径不要重复。** 配置了 URL 前缀后，接口 URL 栏只需填写路径部分（如 `/supplierCenter/supplier/base/contract/getContractCode`），不要再写完整域名或 `{{baseUrl}}`，否则会拼出错误地址导致 404。

## 第二步：签名前置脚本

所有 BOSS 对外接口都需要在请求头中携带签名，通过 Apifox 的「前置操作」脚本自动计算。

### 2.1 签名原理

签名流程如下：

1. 收集请求的 method（小写）、url（路径部分）、timestamp（秒级时间戳）、appId、appkey
2. 将 Body 中的顶层参数按 key 的 ASCII 字母序排序，拼接为 `key1=value1&key2=value2` 格式（嵌套对象用 JSON.stringify）
3. 将上述所有部分拼接为签名原文：`method=xxx&url=xxx&timestamp=xxx&appId=xxx&key=xxx&排序后的Body参数`
4. 对签名原文做 SHA256 哈希，转为大写字符串
5. 将结果写入请求头 `signature`，同时写入 `timestamp` 和 `appId`

### 2.2 完整脚本代码

将以下脚本完整粘贴到 Apifox 接口的「前置操作」标签页中：

```javascript
// ===== 配置区 =====
var appId = pm.environment.get("appId");
var appkey = pm.environment.get("appkey");

// ===== 获取当前时间戳（秒级） =====
var timestamp = Math.floor(Date.now() / 1000).toString();
pm.environment.set("timestamp", timestamp);

// ===== 获取请求信息 =====
var method = pm.request.method.toLowerCase();
var url = pm.request.url.getPath();

// ===== 解析 Body 参数并按 ASCII 排序 =====
var bodyStr = pm.request.body ? pm.request.body.raw : "";
var sortedParams = "";

try {
    var bodyObj = JSON.parse(bodyStr);
    var keys = Object.keys(bodyObj).sort();
    var parts = [];
    for (var i = 0; i < keys.length; i++) {
        var key = keys[i];
        var value = bodyObj[key];
        if (typeof value === 'object' && value !== null) {
            parts.push(key + "=" + JSON.stringify(value));
        } else {
            parts.push(key + "=" + String(value));
        }
    }
    sortedParams = parts.join("&");
} catch (e) {
    sortedParams = "";
}

// ===== 拼接签名原文 =====
var signStr = "method=" + method
    + "&url=" + url
    + "&timestamp=" + timestamp
    + "&appId=" + appId
    + "&key=" + appkey;

if (sortedParams) {
    signStr = signStr + "&" + sortedParams;
}

console.log("签名原文:", signStr);

// ===== SHA256 计算 =====
var signature = CryptoJS.SHA256(signStr).toString().toUpperCase();
pm.environment.set("signature", signature);

console.log("signature:", signature);
```

### 2.3 配置 Headers

每个接口需要在「Headers」标签页添加以下 4 个请求头：

| Header名    | Header值        |
|-------------|-----------------|
| appId       | {{appId}}       |
| timestamp   | {{timestamp}}   |
| signature   | {{signature}}   |
| Content-Type| application/json|

### 2.4 脚本关键逻辑说明

**参数排序**：`Object.keys(bodyObj).sort()` 按字母序排列 Body 的顶层 key，与 Java 服务端 TreeMap 的行为一致。排序错误是最常见的 401 原因之一。

**时间戳精度**：使用 `Math.floor(Date.now() / 1000)` 生成秒级（10位）时间戳。如果误用毫秒级（13位），签名会不匹配。

**嵌套对象处理**：Body 中的嵌套对象（如 `baseInfo`）使用 `JSON.stringify()` 转为字符串拼接，不要展开为子参数。

## 第三步：接口克隆与导入

### 3.1 从共享文档克隆

如果团队提供了 Apifox 在线共享文档链接：

1. 在浏览器中打开共享文档链接
2. 滚动到页面底部，找到「克隆」按钮
3. 点击克隆，选择目标项目（你的「BOSS接口测试」项目）
4. 在 Apifox 客户端的导入预览页中，**关闭**「将 OpenAPI/Swagger 里的 Servers 导入为环境」开关（避免环境冲突）
5. 点击「确定导入」

> 克隆过来的接口 URL 前缀可能不是你测试环境的地址，需要手动修改每个接口的 URL 前缀。

### 3.2 通过 OpenAPI/Swagger 文件导入

如果拿到的是 YAML/JSON 格式的接口文档文件：

1. 在 Apifox 客户端，点「项目设置」→「导入数据」
2. 数据源格式选「OpenAPI/Swagger」
3. 选「上传文件」标签页，选择文件
4. 同样**关闭**「将 Servers 导入为环境」
5. 点击「确定导入」

### 3.3 手动创建接口

当无法克隆或导入时，手动创建接口只需 6 步：

1. 左侧接口列表右键 →「新建接口」
2. 填写接口名称和请求方式（POST/GET）
3. URL 栏填写路径部分（不含域名前缀）
4. Headers 标签页添加 appId/timestamp/signature/Content-Type
5. 前置操作标签页粘贴签名脚本
6. Body 标签页选 JSON，填入请求参数

## 第四步：业务接口调试流程

### 4.1 接口调用链路

BOSS 对外接口存在严格的先后依赖关系，必须按顺序调用：

```
① 获取合同编号  →  返回 contractCode
      ↓
② 客户同步      →  返回 customerCode (DPC000xxx)
      ↓
③ 合同同步      →  需要 customerCode + contractCode，返回合同编号
      ↓
④ 创建Agreement →  需要 customerCode + contractCode
      ↓
⑤ 创建会员优惠券规则 →  需要 agreementCode + customerCode
      ↓
⑥ BOSS项目配置（Lounge/FT/eSIM等）
      ↓
⑦ SAAS 租户协议关联
      ↓
⑧ SAAS 创建权益
      ↓
⑨ SAAS 创建会员模板
      ↓
⑩ SAAS 创建产品
      ↓
⑪ SAAS 创建续期计划并启用
```

### 4.2 接口间数据传递

每一步接口返回的 `code` 或 `id` 都是下一步的入参。建议将关键返回值记录在笔记中：

- 第①步返回的 `code`（合同编号，如 A001-2026-00213）
- 第②步返回的 `code`（客户编码，如 DPC000324）
- 第③步返回的 `code`（合同销售编号，如 A014-XS-2026-000010）
- 第④步返回的 `agreementCode`

### 4.3 各接口关键参数

**获取合同编号** `POST /supplierCenter/supplier/base/contract/getContractCode`

```json
{
    "contractType": 0,
    "companyCode": "A001"
}
```

contractType 为 0 表示新签合同，为 1 表示续签（需要 relatedCode 指向已存在的主合同）。

**客户同步** `POST /salesCenter/saleForceAddOrUpdate`

Body 包含 baseInfo（客户基本信息）、acctInfoList（账户列表）、cusInfoContactInfo（联系人列表）、invoiceInfo（发票信息）。其中 baseInfo 的 sfCode 和 name 必须唯一，重复会报业务错误。

**合同同步** `POST /salesCenter/v1/itdContractSale/saleForceAddOrUpdate`

需要用到第②步返回的 customerCode 填入 cusCode 字段。

**创建Agreement** `POST /salesCenter/api/v1/agreement/add`

这是最容易出错的接口，必须一次性提供全部必填字段。完整字段清单如下：

```json
{
    "customerCode": "DPC000594",
    "contractCode": "A014-XS-2026-000467",
    "agreementName": "测试协议001",
    "agreementType": "standard",
    "beginDate": "2026-01-09",
    "endDate": "2027-01-09",
    "expender": "DP0312",
    "profitCode": "DP086",
    "autoRenewal": "Y",
    "agreementCompany": "A014",
    "status": "0",
    "businessOwner": "international",
    "businessMode": "b2b",
    "salesType": "b2b",
    "remark": "test",
    "operater": "DP0312"
}
```

**各字段说明与已知陷阱：**

| 字段 | 说明 | 注意事项 |
|------|------|----------|
| customerCode | 客户编码 | 必须是第②步实际返回的值（如 DPC000594） |
| contractCode | 合同编码 | 必须是第③步实际返回的值 |
| agreementType | 协议类型 | 枚举：standard / framework / generic |
| profitCode | 利润中心 | **⚠️ 必须填龙腾在用部门ID**（如 DP086、DP0312），不能填公司编码（如 A014），否则报"利润中心需为龙腾在用部门" |
| businessMode | 业务模式 | 有效值为 `b2b`。`domestic`/`international` 是 **businessOwner** 的枚举，不要填到这里 |
| businessOwner | 业务归属 | **只能填 `international` 或 `domestic`**。填工号 `DP0312` 会报 Err000019「业务归属字段为非法字段」 |
| expender | 支出方 | 填部门ID（如 DP0312） |
| autoRenewal | 自动续期 | Y 或 N |
| status | 状态 | 0=草稿 / 1=生效 / 2=终止 |
| agreementCompany | 协议公司 | 公司编码（如 A014） |
| operater | 操作人 | 填部门ID（如 DP0312） |

## 第五步：SAAS IAM登录获取Token

### 5.1 SAAS 与 BOSS 的认证区别

- **BOSS 接口：** SHA256 签名（Header：`appId`、`timestamp`、`signature`）
- **SAAS 平台接口**（路径以 `/api/platform/` 开头）：Header 名必须是 **`platform-token`**，值为登录后停在租户选择页拿到的 UUID，**不要**加 `Bearer`
- **SAAS 租户接口**（路径以 `/api/tenant/` 开头）：Header 名必须是 **`tenant-token`**，值为**点进某个租户（如 1276）之后**的 UUID，**不要**加 `Bearer`

只写 `Authorization: Bearer …` 不够。平台接口会报 `platform-token cannot be empty`，租户接口会报 `tenant-token cannot be empty`。两种 Token 不能混用，进租户后旧的 platform-token 立刻失效。

SAAS 系统走的是 IAM 统一登录，没有直接的 API 接口可以调用获取 token，需要通过浏览器登录后提取。

### 5.2 浏览器登录提取 Token

**操作步骤：**

1. 打开浏览器，访问 SAAS 登录页：
   ```
   https://iam-test.dragonpass.com.cn/#/login?system=saas-platform
   ```

2. 使用测试账号登录：
   - 用户名：`DP001224`
   - 密码：`dp123456`

3. 登录成功后，按 **F12** 打开浏览器开发者工具

4. 点击 **「Network」（网络）** 标签

5. 在页面上随便点击一下，触发网络请求

6. 在网络请求列表中找到包含 `token` 的请求，复制 token 值

7. 将 token 添加到 Apifox 环境变量中，变量名设为 `token`

### 5.3 使用 Cookie 方式（备选）

如果提取 token 困难，可以使用 Cookie：

1. 登录 SAAS 后，在 F12 → **Application（应用）** → **Cookies** 中找到 SAAS 域名的 cookie
2. 将 cookie 复制到 Apifox 接口的 **Cookies** 标签页
3. 后续请求会自动带上 cookie

### 5.4 SAAS 接口 Header 配置

| 接口类型 | 必须勾上的 Header | 值 |
|----------|-------------------|-----|
| `/api/platform/...` | `platform-token` | 原始 UUID，无 Bearer |
| `/api/tenant/...` | `tenant-token` | 原始 UUID，无 Bearer |
| 两类都要 | `Content-Type` | `application/json` |

不要带 BOSS 的 `appId`/`timestamp`/`signature`。租户接口不要勾 `platform-token`（没勾=不发送；勾了但空着也会乱）。

F12 → Network → 点开一条发往 `quanyi-intl-test` 的请求 → **Request Headers** 里复制同名那一行的值。

### 5.5 SAAS 测试环境地址

SAAS 接口的 URL 前缀与 BOSS 不同：

```
https://quanyi-intl-test.dragonpass.com.cn
```

在 Apifox 环境设置中，如果测试 SAAS 接口，需要创建单独的环境或将 URL 前缀改为上述地址。

## 第六步：常见错误排查

### 6.1 HTTP 401 — 签名错误 / 无权访问该资源 / 应用凭证已失效

网关在进业务逻辑之前就把请求挡了。典型特征：几十毫秒返回、响应只有一行 `error`、体积约几十字节。这时不要先改 Body 业务字段。

**新人新建接口最常见原因**：只贴了 URL 和 Body，没有把「前置操作脚本 + 4 个签名 Header」从已调通的 BOSS 接口抄过来。操作手册里 `appId+timestamp+appkey`、毫秒时间戳那份脚本是错的，会 401。

排查顺序（必须细到点哪个标签）：

1. 点响应上方 **「实际请求」** → 看 Headers 里有没有 `appId`、`timestamp`、`signature`，且 `appId` 是 `fanwei-test`。缺任意一个 = 没发出去。
2. 点接口的 **「前置操作」**：必须有 SHA256 脚本（method+url+秒级 timestamp+appId+key+排序 Body，结果转大写）。可从已调通的会籍券码接口整段复制。
3. 点 **「Headers」**：四行都勾上：`appId={{appId}}`、`timestamp={{timestamp}}`、`signature={{signature}}`、`Content-Type=application/json`。去掉 `platform-token` / `Authorization`。
4. 点 **「Auth / 认证」**：选无需认证。不要带 SAAS Bearer。
5. 发完点下方 **「控制台」**：必须出现 `签名原文:` 和 `signature:`。没有输出 = 脚本没跑。
6. `timestamp` 必须是 10 位秒，不是 13 位毫秒。环境变量 `appId=fanwei-test`、`appkey=123456`。

**检查参数排序**：Body 的顶层 key 必须按 ASCII 字母序排列。例如 `acctInfoList` 在 `baseInfo` 前面（a 在 b 前面）。可以用控制台输出的签名原文对比服务端期望的原文。

**检查 URL 路径**：签名脚本中 `pm.request.url.getPath()` 获取的路径必须与实际请求路径完全一致。

### 6.2 HTTP 404 — 路径错误

**URL 重复前缀**：最常见的 404 原因。如果已配置 URL 前缀，接口 URL 栏不要再写完整域名或 `{{baseUrl}}`，只写路径部分。

**创建协议用了手册旧路径**：`/supplierCenter/supplier/base/agreement/add` 在 TEST 网关会 Spring 404。正确路径是 `/salesCenter/api/v1/agreement/add`（和已调通的 `membershipCouponRule/add` 同一前缀）。

**环境地址错误**：确认当前选择的环境是否正确（应选 TEST测试环境），不同环境的域名不同。

**路径拼写错误**：注意大小写、斜杠方向、是否有多余的 `/` 或缺少 `/`。

### 6.3 业务错误（HTTP 200 但 errorCode 非 ok）

**客户名称已存在**：测试环境中已有同名客户。修改 Body 中的 `sfCode` 和 `name` 为唯一值（如加后缀 002、003）。

**主合同不存在**：`contractType` 设为 1（续签）时需要关联已存在的主合同。新人测试应设为 0（新签）。

**依赖数据未就绪**：接口间有严格顺序，如果上一步没成功就跳到最后，会因缺少依赖数据而失败。

**编码格式问题**：确保 Body 中的 JSON 格式正确，没有多余逗号、引号不匹配等语法错误。

### 6.4 枚举值与文档不一致

BOSS 系统存在文档描述与服务端实际接受值不一致的情况，这是已知的常见问题。

**已知差异案例：**

| 字段 | 文档描述 | 实际有效值 | 错误提示 |
|------|----------|-----------|----------|
| profitCode | 可能误以为填公司编码（A014） | 必须填龙腾在用部门ID（DP086、DP0312） | "利润中心需为龙腾在用部门" |
| businessMode | 文档写 domestic / international | 实际有效值为 `b2b` | "业务归属字段为非法字段，请使用可用枚举" |

**排查方法论（当遇到"非法字段/非法枚举"错误时）：**

1. **查已成功请求样例**：找团队中其他人已调通的请求体，对比自己的值。这是最快的方式。
2. **查数据库枚举表**：如果有数据库访问权限，查对应的枚举配置表（如 `sys_dict_data`）获取实际有效值列表。
3. **对比 Apifox 已有用例**：在团队共享的 Apifox 项目中，查看同一接口的历史成功用例（「运行记录」标签页）。
4. **询问后端开发**：当以上方式都无法确认时，直接询问接口负责人确认枚举值。
5. **不要盲目猜测**：枚举值不匹配时，不要靠逐个尝试不同值来碰运气，应通过上述渠道确认。

## 踩坑总结

以下是实际调试中容易踩的坑，按优先级排列：

1. **自动化测试模式下前置脚本不执行**：必须在「接口管理」的调试模式下发送请求，而不是在「自动化测试」模块中运行。自动化测试模式的前置脚本行为不同，可能导致签名未计算。

2. **URL 重复前缀导致 404**：配置了环境 URL 前缀后，接口 URL 栏只写路径，不要同时写域名和 `{{baseUrl}}`。

3. **签名字段必须按 ASCII 排序**：`Object.keys(bodyObj).sort()` 的行为要和 Java 服务端 TreeMap 一致，否则签名算出来不同。

4. **时间戳精度**：秒级（10位），不是毫秒级（13位）。

5. **嵌套 JSON 不要展开**：签名拼接时，嵌套对象（如 baseInfo 的值）应该用 `JSON.stringify()` 整体作为字符串，不要拆成子字段。

6. **克隆接口后记得改环境**：从共享文档克隆的接口可能带有原始环境配置，需要切换到自己的测试环境。

7. **共享文档可能需要授权**：如果导入 Apifox 共享链接报错「抓取 URL 数据报错」，需要联系文档负责人授权。

8. **严禁逐字段试错**：调试新接口前必须先用 pdftotext 或阅读 OpenAPI 文档提取全部必填字段，一次性构造完整请求体。逐字段添加→发送→报错→再加的方式极其低效，会浪费大量时间。

9. **文档枚举值与服务端不一致是常态**：BOSS 系统的 PDF 文档中的枚举描述可能与服务端实际接受值不同（如 businessMode 文档写 domestic 实际要 b2b，profitCode 需要部门ID而非公司编码）。遇到枚举错误时不要盲目猜测，应参考已成功的请求样例或直接询问开发确认。

10. **Generic API 测试数据集**：鉴权1/鉴权2、UAT Program 凭证、支付链接 Body 已入库。工作区 `d:/api/testdata/`，skill `api-test-datasets`。测 `POST /v2/auth/token` 或支付链接时先读 `catalog.md`，不要从桌面复制。
