---
name: apifox-automation-folder-standard
description: >-
  DragonPass Apifox 接口自动化目录与命名标准（P0 冒烟 / P1 全量 / 功能名 / 按XMind用例 / 0N 分类场景）。
  Use when designing Apifox 自动化、接口自动化用例、按XMind用例、P0 冒烟、P1 全量、
  test-scenario 目录、场景命名、或用户要求按模板建自动化用例。
---

# Apifox 接口自动化目录标准

以后设计接口自动化用例，**默认按本标准**，不要再把新场景散落在功能根目录或挂到别人的功能夹里。

## 目录树（必须）

```
<模块 membership | epass | common>/
  P0(冒烟用例)/
    <功能名>/                          # 可选；没有功能夹时放到 others
      <功能名> · 冒烟                  # priority = P0
  P1（全量用例）/
    <功能名>/                          # 与需求名一致，如 sso免登录短链接、支付链接、FT可用性、Auth双密钥
      按XMind用例/                     # 需求脑图拆出来的全量用例，只放这里
        01 <XMind第1类>/
          <功能简称> · 01<类别>
        02 <XMind第2类>/
          <功能简称> · 02<类别>
        …
      一次性E2E/                       # 一条主链路冒烟/联调，可 P0
      测试用例/                        # 禁止把 XMind 全量塞这里（历史杂项）
      auth双密钥/                      # 仅 Auth 需求本身；其它功能不要往 SSO 夹里塞
```

对照金样（已落地）：`membership/sso免登录短链接/按XMind用例/` 下的

- `SSO免登短链 · 01必填校验`
- `SSO免登短链 · 02参数标准化`
- `SSO免登短链 · 03异常场景`
- `SSO免登短链 · 04边界与容错`
- `SSO免登短链 · 05短链一致性`
- `SSO免登短链 · 06打开短链与分页`

编号跟 XMind 章节走（01、02、03…），缺章就跳号，不要为了连续而改需求分类名。

## 场景命名与优先级

| 项 | 规则 |
|----|------|
| 场景名 | `<功能简称> · 0N<类别>`，中间是中文间隔号 `·` |
| 按XMind用例 | **P1** |
| 冒烟 / 一次性E2E 主链路 | **P0** |
| 步骤名 | `【中文目的】\| 用例ID \| METHOD /path` |
| 断言标题 | `检查点 \| 期望=… \| 实际=…` |

禁止：`支付链接`、`FT可用性`、`11` 这种无分类名的占位场景当正式全量（历史占位不要删，也不要往里面继续堆）。

## 步骤与 Body（必须）

1. **每个场景第一步换 Token**：`POST /v2/auth/token`，写出 `accessToken` / `access_token`。
2. **业务步 Header 必带**：`Authorization: Bearer {{accessToken}}`、`X-Program-ID: {{ProgramID}}`、`x-version: {{x-version}}`（默认 canary）、`X-Request-ID`（36 位 UUID，前置脚本生成）、`Content-Type: application/json`。
3. **Body 与 XMind/需求用例一致**：字段名、是否省略、枚举值以需求脑图为准，不要用另一套接口的样例单号。
4. **Program / Token / 数据三件套不混用**。会籍购买、SSO 免登、Lounge+FT、双密钥鉴权1/鉴权2 各用各的。
5. 场景内用 `type=group` 按 XMind 小类分组；叶步骤用解绑 `customHttp`。
6. 前置脚本若会重写 Body，界面 JSON 只作对照；真正入参以脚本/`pm.variables` 为准。
7. 密钥写在 Auth 前置种子或数据集，**不要**写进场景说明、回复、git。

## 新建时落点

- 新功能：建在 **`membership/P1（全量用例）/<功能名>/按XMind用例`**（epass/common 同理）。
- 历史 SSO 夹在 `membership/sso免登录短链接`（与 P0/P1 平级），**不要挪**，也不要把支付/FT/Auth 新用例继续堆进这个夹。
- 占位场景 `11`、旧 `支付链接`、旧 `FT可用性`：**禁止删除**，新标准用例另建。
- 默认只 Push 场景，不擅自 SyncCheck/Run。预调试用本机脚本或单条「发送」。

## 分类怎么从 XMind 映射

把需求根节点下的「1.xxx / 2.xxx」变成 `01 xxx` 文件夹 + 一条 P1 场景。同一章里的前置/步骤/预期变成该场景的 HTTP 步骤，不要每个叶子再拆一个场景。
