# 需求第 1 步：BOSS 创建协议（逐点击）

用户原话：「你这样说的太模糊了不够详细请你说的在详细一点好嘛？」

本文件教测试新人在 Apifox 调 `agreement/add`。教的人必须按下面粒度写，禁止「打开 BOSS 项目发一下」。

## 这一步在干什么（人话）

需求「五、调用接口」第 1 步：在**已经存在的客户 + 合同**下面，新建一份协议。

- 不是 SAAS，不要 Token，不要 VPN
- 不是改已有协议 `BZ000409`。`add` 是新建，会再出一份新的 `BZxxxxxx`
- 编号别混：需求第 1 步 = Playbook 的「创建 Agreement」；Playbook 的 Step 1 是「获取合同编号」

## 开始前先确认你人在哪

1. 关掉浏览器里刚才的 SAAS 页面也没关系，本步不用浏览器。
2. 打开电脑上的 **Apifox 桌面客户端**（不是浏览器里的 Apifox 在线文档）。
3. 看 Apifox **最左上角当前项目名**。
   - 必须是 **`GA-BOSS`**
   - 如果写着 `GA-SAAS`：点项目名 → 在列表里点 `GA-BOSS` 切过去
   - 不要在 SAAS 项目里新建这个接口，Headers 会混

## A. 选环境和前置 URI（发请求前必做）

1. 看窗口 **右上角** 环境下拉框（接口名旁边，一般显示「环境: xxx」）。
2. 点开，选你之前调会籍券码规则时用的那个测试环境（常见名字：`TEST测试环境` / `测试环境`）。
3. 点同一个下拉框旁边的 **「环境管理」或齿轮**，点进刚选的那个环境。
4. 找到 **「前置 URL」**（有的版本叫「服务」或「Base URL」）。
5. 必须整段是下面这一行，一个字母都不能少，结尾不要斜杠：

```text
https://business-finance-gateway-test.dragonpass.com.cn
```

6. 对照检查，发现下面任何一种就改掉：
   - 写成了 `https://iam-test.dragonpass.com.cn` → 错，那是登录页
   - 写成了 `https://quanyi-intl-test.dragonpass.com.cn` → 错，那是 SAAS 接口
   - 写成了 `http://agent-salespolicy-service...svc.dragon` → 错，那是第 3 步内网
7. 同一页确认环境变量（没有就点「添加」）：

| 变量名 | 当前值必须是 |
|--------|----------------|
| appId | `fanwei-test` |
| appkey | `123456` |

8. 点 **「保存」**，关掉环境窗口。

## B. 找到或新建接口（二选一）

### 情况 1：左边已经有这条接口

1. 确认你在 **「接口管理」** 页签（窗口顶部或左侧，不要点「自动化测试 / 测试场景 / 测试用例」）。
2. 左侧接口树上方有搜索框，点一下，输入：

```text
agreement/add
```

3. 点搜索结果里路径完全是下面这一行的接口：

```text
POST /salesCenter/api/v1/agreement/add
```

4. 如果搜到的是 `membershipCouponRule/add`，点错了，回到搜索再选 `agreement/add`。

### 情况 2：搜不到，要手建

1. 仍在 **「接口管理」**。
2. 左侧接口树空白处 **右键** → **「新建接口」**。
3. 顶部中间，请求方法下拉框点开，选 **POST**（默认可能是 GET，不改会 405 或网关报错）。
4. 方法右边的 **URL 栏**，整段删掉后，只粘贴下面这一行（不要域名、不要 `{{baseUrl}}`）：

```text
/salesCenter/api/v1/agreement/add
```

5. 接口名称可改成：`创建协议-agreement/add`。
6. 点 **保存**（Ctrl+S）。

## C. 改 URL 栏（很多人 404 出在这里）

打开接口后，看中间 URL 栏，只能是：

```text
/salesCenter/api/v1/agreement/add
```

如果栏里出现下面任何一段，用鼠标全选删掉，只留上面那一行：

- `https://...`
- `{{baseUrl}}`
- `/api/auth/login`
- `/api/platform/...`

完整地址由「前置 URL + 这一行路径」自动拼。拼完应是：

```text
https://business-finance-gateway-test.dragonpass.com.cn/salesCenter/api/v1/agreement/add
```

## D. Headers（一行一行勾）

1. 点接口中间的 **「请求」** 区域里的 **「Params」旁边的「Headers」** 标签（不是「实际请求」里的只读 Headers）。
2. 先把 **`platform-token`、`Authorization`** 两行前面的勾 **全部去掉**（本步是 BOSS，不是 SAAS）。
3. 按表格新增或改已有行。每一行左边小方块必须是 **勾上**（没勾 = 不发出去）：

| 勾选 | 参数名（Header 名） | 参数值 |
|------|---------------------|--------|
| 勾上 | `appId` | `{{appId}}` |
| 勾上 | `timestamp` | `{{timestamp}}` |
| 勾上 | `signature` | `{{signature}}` |
| 勾上 | `Content-Type` | `application/json` |

4. `{{appId}}` 不要改成手打的别的词；环境变量里已经是 `fanwei-test`。
5. 不要写 `Bearer`。不要把 SAAS 的 UUID token 贴到这里。

## E. 前置脚本（签名）

1. 点 **「前置操作」** 标签（有的版本在「前置脚本」）。
2. 如果这里是空的：回到你已经调通的 **会籍券码规则** 那个接口 → 同样打开「前置操作」→ 全选脚本 → 复制 → 回到 `agreement/add` → 粘贴。
3. 如果没有券码接口：把技能 `apifox-api-debug-guide` 里「第二步：签名前置脚本」整段 JavaScript 粘进来。
4. 脚本里签名原文必须是：`method` + `url`（路径）+ `timestamp`（秒，10 位）+ `appId` + `key`（appkey）+ **Body 顶层字段按字母排序**。
5. 不要用操作手册里错误的 `appId+timestamp+appkey` 三段拼接（会 401）。
6. 点保存。

## F. Body（整段覆盖粘贴）

1. 点 **「Body」** 标签。
2. 左侧类型选 **「json」**（不要 form-data、不要 x-www-form-urlencoded）。
3. 右边编辑框里如果有旧内容，**全选删除**。
4. 把下面整段复制进去（一个字段都不要删）。`agreementName` 如果今天已经用过同名，把 `08219` 改成当天日期再发：

```json
{
  "customerCode": "DPC000547",
  "contractCode": "A004-XS-2026-000233",
  "agreementName": "新人测试协议-08219",
  "agreementType": "standard",
  "beginDate": "2026-08-19",
  "endDate": "2027-08-18",
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

5. 字段从哪来、不能改成什么：

| 字段 | 你要填的值 | 说明 |
|------|------------|------|
| customerCode | `DPC000547` | 客户编码，页面上客户名前面括号里那个。不要填 `DP001224` |
| contractCode | `A004-XS-2026-000233` | 合同编号。不要填协议号 `BZ000409` |
| agreementName | 新名字 | 新建协议的名称，不要用已有的 `DP API -SunnyTestClient` |
| agreementType | `standard` | 小写英文 |
| beginDate / endDate | `yyyy-MM-dd` | 结束日必须晚于开始日 |
| profitCode | `DP086` | 部门 ID。填 `A014` 会报「利润中心需为龙腾在用部门」 |
| businessOwner | `international` | 业务归属枚举，只能是 `international` 或 `domestic`。填工号 `DP0312` 会报 Err000019「业务归属字段为非法字段」 |
| businessMode | `b2b` | 不要填 international / domestic（那是 businessOwner 的值） |
| operater | `DP0312` | 拼写是 **operater**，少一个 a。不要写成 operator |
| agreementCompany | `A014` | 公司编码，和 profitCode 不是同一个 |

6. 不要对已有协议 `BZ000409` 调 add。add 没有「协议编码」入参，成功会返回**新的** BZ 号。

## G. 发送（不要走自动化）

1. 确认还在 **接口管理** 里打开的这一条接口，不是「测试场景」。
2. 右上角环境仍是 BOSS 测试环境。
3. 点窗口右侧或下部的 **「发送」** 按钮（绿色，有的版本写 Send）。
4. 等下方「响应」出现。不要连续点两次，避免建出两份协议。

## H. 成功时长什么样、抄什么

HTTP 一般是 **200**。响应 JSON 里：

- `code` 为成功码（常见 `"0"` 或 `"200"`，以实际为准，同时看 `msg` 是成功而不是报错句）
- 找到 **`agreementCode`** 或返回体里的新协议编码（形如 `BZ000xxx`）

立刻写到笔记：

| 记什么 | 值 |
|--------|----|
| 新协议编码 | 本次返回的 `BZxxxxxx`（不是旧的 `BZ000409`） |
| 客户 | 仍是 `DPC000547` |
| 合同 | 仍是 `A004-XS-2026-000233` |

可选：打开 BOSS 后台 `https://dpboss-test.dragonpass.com.cn/#login`，用 `DP001224` / `!4yOcoZk` 登录，按协议编码搜索，状态应能搜到刚建的那份。

## I. 失败时按这个表改（改完再发，不要盲试）

先点响应上方 **「实际请求」**，确认发出去的 URL、Headers 和 Body 跟上面一致。

| 你看到的 | 原因 | 你现在改哪 |
|----------|------|------------|
| HTTP 404，响应是 Spring 的 `Not Found`，path 里带 `supplierCenter/supplier/base/agreement/add` | 手册旧路径不存在。真实接口和券码规则同属 salesCenter | URL 栏改成 `/salesCenter/api/v1/agreement/add`（与 `membershipCouponRule/add` 同一前缀）。前置脚本不用改，改完路径再发一次让签名按新 url 重算 |
| HTTP 404，URL 里出现 `/api/auth/login` 或 IAM 域名 | 前置 URI 用成了登录地址，或路径叠了两段 | 环境前置 URI 改成 BOSS 网关；URL 栏只留 `/salesCenter/api/v1/agreement/add` |
| HTTP 404，主机是 `quanyi-intl-test` | 人还在 GA-SAAS 项目 | 左上角切回 `GA-BOSS` |
| HTTP 401，响应 `无权访问该资源` / `应用凭证已失效`（几十毫秒、只有一行 error） | 新建接口没抄签名：Headers 缺 appId/timestamp/signature，或前置脚本没跑/用了手册里错误的 appId+timestamp+appkey | **先别改 Body 业务字段。** 点「实际请求」看这 3 个 Header 有没有发出去；从已调通的券码接口复制「前置操作」整段脚本 + 4 个 Header 并勾上；Auth 选无需认证；控制台必须打出 `签名原文:`。脚本必须是 method+url+秒级 timestamp+appId+key+排序 Body，SHA256 转大写 |
| `platform-token cannot be empty` | 误用了 SAAS 校验 | 去掉 platform-token；确认项目是 GA-BOSS |
| msg 含「利润中心」 | profitCode 填成了公司码 | 改成 `DP086` |
| HTTP 200 但 `state`=`0`，`Err000019`，msg 含「业务归属字段为非法字段」 | `businessOwner` 填成了工号 | 改成 `international`（GA 国际用这个）或 `domestic`。不要填 `DP0312` |
| msg 含「合同下已有协议」或类似 | 这份合同已经绑过协议 | **停**。不要反复 add。先调获取合同编号接口拿一个**新合同号**，再对新合同 add。旧协议继续用 `BZ000409` 即可 |
| msg 含 operat / 操作人 | 字段名写了 operator | 改成 `operater` |
| 响应 `data` 是 null，Apifox 提示 schema 失败 | 多半是业务失败，不是「校验脚本坏了」 | 先看 JSON 里的 `code` 和 `msg` |

## J. 做完这一步不要做什么

- 不要立刻改 SAAS 租户绑定（需求第 5 步）。新协议要绑租户必须走完整 Body，只传 `{id:27}` 会把已有协议列表清空。
- 不要把新 BZ 号和旧的 `BZ000409` 混着填到券码规则里，除非你明确要给**新协议**再配规则。
- 第 3 步品类项目仍要 VPN，本步不需要。
