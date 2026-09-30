# DragonPass Generic API 命名速查

列接口时用：`METHOD /path` — **中文名**：干什么。

本表可随需求增补；没有的条目先查 Apifox/OpenAPI，再补进本文件。

## 鉴权

| 接口 | 中文名 | 干什么 |
|------|--------|--------|
| `POST /v2/auth/token` | 获取访问令牌 | 用 clientId + secret（及 X-Program-ID）换 Bearer Token；双密钥需求测两套鉴权 |

## 资源 / 交通枢纽

| 接口 | 中文名 | 干什么 |
|------|--------|--------|
| `GET /v2/resources` | 查询资源列表 | 按 module、transportHubId 等查出 Lounge/FT/Dining 等资源列表；可含 area、routeTypes、terminal 等 |
| `GET /v2/resources/{resourceId}` | 查询资源详情 | 按 resourceId 查单个资源详情（营业时间、位置、routeTypes、权益相关展示等） |
| `GET /v2/transportHubs` | 查询交通枢纽列表 | 查机场/车站等交通枢纽列表 |
| `GET /v2/transportHubs/{transportHubId}` | 查询交通枢纽详情 | 查单个枢纽详情 |
| `GET /v2/transportHubs/iata/{iata}/resources` | 按 IATA 查枢纽下资源 | 用机场三字码拉该枢纽下资源列表；条目可含 routeTypes |
| `POST /v2/resources/prices` | 查询资源价格 | 批量/条件查资源价格 |
| `POST /v2/resources/prebookings/availability` | 查询预预约可用性 | 查资源在指定时间是否可预约（如 FT 过滤过去时间） |

## 会籍 / 权益

| 接口 | 中文名 | 干什么 |
|------|--------|--------|
| `POST /v2/memberships` | 注册会籍 | 创建/注册会员会籍 |
| 会籍 preview / details（以 Apifox 实际 PATH 为准） | 会籍预览/详情 | 下单前校验或查会籍状态；错误码 039–045 等常落在此 |

## 订单 / 支付 / SSO

| 接口 | 中文名 | 干什么 |
|------|--------|--------|
| 创建订单（以 Apifox 实际 PATH 为准） | 创建订单 | 生成订单，得到 orderId |
| 查询订单列表/详情（以 Apifox 实际 PATH 为准） | 查询订单 | 查订单状态、详情 |
| `POST /v2/orders/payments` | 创建支付链接 | 为待支付订单生成支付 H5/链接；可指定 language、durationInSeconds |
| `POST /v2/sso/links` | 创建 SSO 免登短链 | 生成订单列表/详情免登短链，用户点开无需再登 |

## 说明

- **routeTypes**：资源出发类型枚举数组。历史上 1～6 为国际/国内 出港/到港/中转；PAPI-3217 新增 **7 = 美国跨境区**。主要出现在资源列表/详情、按 IATA 查枢纽资源。
- 列影响接口时：写清「改配置 → 哪个接口的哪个返回字段变了」，不要只丢 PATH。
