# PAPI-3210 Auth返回programType

## Auth

### GetAccessToken获取访问令牌 POST /v2/auth/token

操作：Body 传 clientId、secret，Header 带 X-Program-ID。成功后 data 里原有 accessToken、tokenType、validUntil，再多一个 programType。

SAAS对照｜该 Program → 项目类型

#### 返回校验

##### tc-p0: 成功时新增programType (PAPI-3210)

- code=0
- data.programType 存在且为字符串
- data.accessToken 非空
- data.tokenType 等于 Bearer
- data.validUntil 为大约一小时后的秒级时间戳

##### tc-p0: E-pass项目返回E-pass (PAPI-3210)

- 使用 SAAS 项目类型为 E-pass 的 Program
- data.programType 等于 E-pass
- 大小写和连字符与示例一致

##### tc-p0: Membership项目返回Membership (PAPI-3210)

- 使用 SAAS 项目类型为 Membership 的 Program
- data.programType 等于 Membership

##### tc-p0: Retail项目返回Retail (PAPI-3210)

- 使用 SAAS 项目类型为 Retail 的 Program
- data.programType 等于 Retail

##### tc-p0: Auth项目返回Auth (PAPI-3210)

- 使用 SAAS 项目类型为 Auth 的 Program
- data.programType 等于 Auth

##### tc-p1: 同一Program两套密钥返回相同programType (PAPI-3210)

- 鉴权1、鉴权2 分别取 Token
- 两次 data.programType 相同
- 都等于该 Program 在 SAAS 上的项目类型

#### 业务逻辑

##### tc-p0: 新Token仍可调用查询接口 (PAPI-3210)

- 用本次返回的 accessToken 调 GET /v2/resources
- 业务接口能通
- 业务接口响应里不新增 programType

##### tc-p1: programType与品类无关 (PAPI-3210)

- 同一 Membership Program 下可开休息室、快速安检等品类
- 取 Token 时 programType 仍是 Membership
- 不因开通品类变成 E-pass 或其他值

#### 错误码

##### tc-p1: secret错误不返回programType (PAPI-3210)

- secret 填错
- 返回 201.000.001
- Invalid credentials. Please check your secret and try again.
- 响应里没有 programType

##### tc-p1: AUTH_H5是否从本接口返回 (PAPI-3210)

- 待确认
- 待确认：H5 用的 AUTH_H5 Program 是否也走 POST /v2/auth/token
- 待确认：若走本接口，programType 是 Auth、AUTH_H5，还是其他字
- 工单注释只列 E-pass、Membership、Retail、Auth
