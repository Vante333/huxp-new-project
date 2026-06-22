# PAPI-2653SAAS权限组支持双key切换测试分析

## 测试范围说明

- rc: 基于 `requirements/2026Q2SP4/PAPI-2653.md`；覆盖 Auth Token 从单 Key 扩展为双 Key 配置、独立有效期、启用禁用状态、`kid` 路由验签、HS256/RS256 算法兼容、存量 Token 迁移默认值和有效期告警。
- rc: 重点验证 JWT 带 `kid` 与不带 `kid` 两条鉴权路径、双 Key 同时生效时权限组操作权限、UTC+0 有效期判定、临期小于 1 个月告警，以及存量数据自动生成 `keyId` 后不影响历史调用方。
- rc: 补充覆盖 SAAS 配置增删改、Auth 生成 Token、客户侧 RS256 Token 验签、配置缓存刷新、全量新增单/双鉴权方式、Base64/PEM Key 格式和回滚方案验证。
- rc: 需求未明确后台配置入口、Key 保存与发布方式、错误码、告警渠道、缓存刷新策略、`kid` 中两个有效期字段的精确含义；执行前需以 Auth/BOSS/Admin 最终设计或 Apifox 文档为准。
- rc: 本文以接口和服务端行为分析为主，不覆盖前端配置页面的布局、交互文案和权限菜单细节。

## 需求语义归纳

| 能力 | 需求语义 | 主要风险 |
| --- | --- | --- |
| 双Key配置 | 一个 SAAS 权限组支持同时配置两个 Key，每个 Key 可独立启用、禁用和配置有效期 | Key 切换期间新旧调用方鉴权失败，或禁用 Key 仍可通过 |
| 算法支持 | 同一权限组支持 HS256 与 RS256 算法 | 选错验签算法、密钥类型混用、RS256 公私钥处理错误 |
| kid路由 | JWT Header 新增 `kid` 时按 `kid` 找匹配 Secret/Key；无 `kid` 时按 `issuer` 匹配 | `kid` 与 `issuer` 不一致时被绕过，历史无 `kid` Token 不兼容 |
| 有效期 | 每个 Key 独立有效期，按 UTC+0 判断；存量默认 2023-01-01 至 2099-01-01 | 时区边界误判，过期或未开始 Key 仍可验签 |
| 数据迁移 | 存量 Token 默认启用，并自动生成 `keyId` | 历史权限组不可用、重复 `kid`、生成格式不符合约定 |
| 临期告警 | 鉴权发现有效期小于 1 个月时触发告警 | 告警未触发、重复刷屏、跨时区导致提前或延后告警 |

## Key状态判定表

| JWT条件 | Key匹配条件 | Key状态 | 有效期状态 | 预期鉴权结果 |
| --- | --- | --- | --- | --- |
| 带合法 `kid` | 命中 Key A | 启用 | 当前 UTC+0 在有效期内 | 验签成功并允许访问权限组资源 |
| 带合法 `kid` | 命中 Key B | 启用 | 当前 UTC+0 在有效期内 | 验签成功并允许访问权限组资源 |
| 带合法 `kid` | 命中 Key A 或 B | 禁用 | 当前 UTC+0 在有效期内 | 鉴权失败，不能访问权限组资源 |
| 带合法 `kid` | 命中 Key A 或 B | 启用 | 未到开始时间 | 鉴权失败 |
| 带合法 `kid` | 命中 Key A 或 B | 启用 | 已超过结束时间 | 鉴权失败 |
| 带未知 `kid` | 无匹配 Key | 任意 | 任意 | 鉴权失败，不应回退使用同 `issuer` 其他 Key 兜底通过 |
| 不带 `kid` | `issuer` 命中权限组 | 至少一个 Key 可用 | 当前 UTC+0 在有效期内 | 按兼容策略验签，历史 Token 可继续使用 |
| 不带 `kid` | `issuer` 命中权限组 | 所有 Key 禁用或过期 | 不在有效期内 | 鉴权失败 |
| 带 `kid` 且 `issuer` 不匹配 | `kid` 命中其他权限组 | 启用 | 当前 UTC+0 在有效期内 | 按产品安全策略拒绝或绑定校验失败，不允许越权 |

## 检查清单映射

| 检查项 | 覆盖章节 | 是否需重点补充 |
| --- | --- | --- |
| SAAS配置过期Key、待启用、启用、禁用 | `Key状态判定表`、`KeyValidity`、`DualKeyConfiguration` | 已覆盖，补充配置查询与缓存生效验证 |
| 存量迁移对不对 | `LegacyTokenMigration` | 已覆盖，补充迁移后 Auth 生成 Token 和旧 Token 继续可用 |
| 删除或修改 `issuer+secret` | `SaasConfigurationCrudAndCache` | 需补充 |
| 新增 HS256 或 RS256 Key | `FullNewAuthGroupFlow`、`AlgorithmCompatibility` | 需补充全链路 |
| 改、删、新增一键后的缓存变化 | `SaasConfigurationCrudAndCache` | 需补充 |
| 全量新增单鉴权/双鉴权方式 | `FullNewAuthGroupFlow` | 需补充 |
| HS256 由系统生成 Token，RS256 客户生成 Token 后验签 | `TokenIssueAndVerifyFlow` | 需补充 |
| Base64无换行和PEM标准格式 | `AlgorithmCompatibility` | 需补充 |
| 回滚方案 | `RollbackPlanVerification` | 需补充 |

## 存量数据迁移与默认值（LegacyTokenMigration）

### tc-p1: 存量Token迁移后默认启用且有效期覆盖历史调用

- pc: 测试环境存在迁移前创建的 SAAS 权限组 Token，历史调用方使用该 Token 可正常访问授权接口。
- 执行双 Key 版本数据迁移或部署升级。
  - 存量 Token 对应 Key 默认为启用状态，默认有效期为 `2023-01-01T00:00:00Z` 至 `2099-01-01T00:00:00Z`。
- 使用迁移前的历史 JWT 或按历史方式签发的 JWT 调用受保护接口。
  - 鉴权成功，历史调用方不因缺少新配置而失败。

### tc-p1: 存量迁移后可继续通过Auth生成Token

- pc: 存量 SAAS 权限组迁移完成，默认 Key 启用且有效期覆盖当前 UTC+0 时间。
- 调用 Auth 生成 Token 接口，使用迁移后的权限组、`issuer` 和 Secret/Key 配置生成 JWT。
  - Token 生成成功，Header 或响应中按约定包含可用于验签的 `kid`。
- 使用生成的 Token 调用受保护接口。
  - 鉴权成功，说明迁移后的配置同时支持生成和验签链路。

### tc-p1: 存量旧Token迁移后仍可继续验签

- pc: 迁移前已保存一个未过期旧 Token，且旧 Token Header 不包含 `kid` 或仍使用历史 Header 结构。
- 完成迁移后直接使用旧 Token 调用受保护接口。
  - 服务端按 `issuer` 兼容匹配并鉴权成功。
- 等待配置缓存刷新后再次使用同一个旧 Token 调用。
  - 鉴权结果保持成功，不因缓存切换导致历史 Token 失效。

### tc-p1: 存量Token自动生成keyId且格式符合约定

- pc: 存量 SAAS 权限组包含租户 ID、有效期和单 Key 配置；迁移任务已执行完成。
- 查询或导出权限组 Key 配置。
  - 每个存量 Key 均生成唯一 `keyId`，格式符合 `key_{租户id}_{有效期}_{有效期}_a/b` 约定。
- 对同一租户多权限组或多 Token 迁移结果进行重复性检查。
  - 不出现重复 `keyId`，且 `keyId` 可稳定定位到原权限组 Key。

### tc-p2: 迁移失败或历史数据缺关键字段时有明确处理

- pc: 构造缺租户 ID、缺历史 Secret/Key 或历史数据格式异常的存量记录。
- 执行迁移任务或服务启动迁移逻辑。
  - 异常记录被明确记录并阻断发布或进入待处理状态，不静默生成不可用 Key。

### tc-p3: 重复执行迁移保持幂等

- pc: 同一批存量权限组数据已经完成一次迁移并生成 `keyId`。
- 再次执行迁移任务。
  - 已迁移 Key 不重复生成新 `keyId`，启用状态和有效期不被意外覆盖。

## SAAS配置增删改与缓存（SaasConfigurationCrudAndCache）

### tc-p1: 新增HS256Key后Auth生成Token并完成验签

- pc: 新建或选择一个 SAAS 权限组，新增一个 HS256 Key，配置合法 `issuer`、Secret、有效期和启用状态。
- 保存配置并等待或触发缓存刷新。
  - 查询配置返回新增 HS256 Key，缓存生效后 Auth 可读取到最新配置。
- 调用 Auth 生成 Token 接口。
  - Token 生成成功，并可使用该 Token 调用受保护接口完成验签。

### tc-p1: 新增RS256Key后客户生成Token并由Auth验签

- pc: 新建或选择一个 SAAS 权限组，新增一个 RS256 Key，服务端保存 `issuer`、`kid` 和 PublicKey，客户侧持有 PrivateKey。
- 客户侧使用 PrivateKey 生成带 `kid` 和 `issuer` 的 JWT。
  - JWT 可提交到 Auth 鉴权流程。
- 使用该 JWT 调用受保护接口。
  - Auth 按 `issuer+publicKey` 或 `kid+publicKey` 验签成功。

### tc-p1: 修改issuer和secret后新旧Token按缓存策略切换

- pc: 权限组存在启用 HS256 Key，旧 `issuer+secret` 已可生成并验签 Token。
- 修改该 Key 的 `issuer` 或 Secret 并保存发布。
  - 配置查询返回新值，旧值不再作为当前配置展示。
- 在缓存刷新完成后分别使用旧 Token 和新配置生成的新 Token 调用接口。
  - 旧 Token 按产品策略失效或仅在缓存窗口内短暂可用，新 Token 鉴权成功。

### tc-p2: 删除或禁用Key后缓存刷新完成即不可继续使用

- pc: 权限组存在启用 Key，且该 Key 生成的 Token 当前可正常鉴权。
- 删除该 Key 或将该 Key 状态改为禁用。
  - 配置保存成功，查询结果不再返回该 Key 或返回禁用状态。
- 缓存刷新完成后使用原 Token 调用受保护接口。
  - 鉴权失败，不继续命中过期缓存中的 Key。

### tc-p2: 删除后重新新增Key不应导致旧Token复活

- pc: 权限组存在 Key A，使用 Key A 生成的旧 Token 当前可正常鉴权。
- 删除 Key A，等待缓存刷新完成后使用旧 Token 调用接口。
  - 鉴权失败。
- 重新新增同位置或同后缀的新 Key，使用新的 Secret/PublicKey 和有效期。
  - 新 Key 生效后旧 Token 仍不可鉴权，除非产品明确允许复用相同 KeyMaterial。

### tc-p2: 新增一键配置后缓存可被Auth生成和验签同时读取

- pc: 通过后台“一键新增”或批量新增入口创建 Key，配置合法算法、`issuer`、KeyMaterial、有效期和启用状态。
- 保存后立即查询配置并触发 Auth 生成 Token 或客户侧生成 Token。
  - 在约定缓存生效时间内，生成和验签链路均读取同一份新配置。
- 多实例环境下重复调用生成和验签接口。
  - 缓存刷新完成后各实例结果一致。

### tc-p3: 配置编辑失败不污染缓存

- pc: 权限组已有一份可用 Key 配置。
- 提交非法 Secret、非法 PublicKey、开始时间晚于结束时间或重复 `kid` 的编辑请求。
  - 配置保存失败。
- 使用编辑前合法 Token 调用受保护接口。
  - 鉴权结果仍按编辑前配置执行，失败配置未进入缓存。

### tc-p2: kid和issuer唯一性冲突时配置保存失败

- pc: 系统中已存在权限组 A，配置了 `issuerA` 和 `kidA`。
- 在权限组 B 中新增相同 `kidA` 或不允许复用的 `issuerA`。
  - 配置保存失败，避免鉴权时跨权限组误匹配。
- 在同一权限组内新增两个相同 `kid` 的 Key。
  - 配置保存失败，不允许同一 `kid` 指向多个 Key。

### tc-p2: 配置查询接口不返回敏感KeyMaterial明文

- pc: 权限组已配置 HS256 Secret 或 RS256 PublicKey，配置查询接口可访问。
- 调用配置查询或导出接口。
  - 响应中 Secret、私钥、完整敏感 KeyMaterial 按约定脱敏或不返回。
- 使用脱敏后的查询结果尝试生成或伪造 Token。
  - 无法凭查询结果绕过鉴权。

### tc-p2: 非授权用户不可新增修改删除Key配置

- pc: 准备无 SAAS 权限组配置权限的后台用户或接口 Token。
- 调用新增、修改、删除、启用、禁用 Key 配置接口。
  - 请求被拒绝，配置和缓存均不发生变化。
- 使用原有合法 Token 调用受保护接口。
  - 鉴权结果不受未授权配置请求影响。

## 双Key配置与状态管理（DualKeyConfiguration）

### tc-p1: 同一权限组配置两个启用Key均可鉴权成功

- pc: 同一 SAAS 权限组配置 Key A 与 Key B，两个 Key 均启用且当前 UTC+0 在有效期内。
- 使用 Key A 签发带 `kid=KeyA` 的 JWT 调用受保护接口。
  - 鉴权成功，调用方具备该权限组对应操作权限。
- 使用 Key B 签发带 `kid=KeyB` 的 JWT 调用同一接口。
  - 鉴权成功，双 Key 同时生效。

### tc-p1: 禁用其中一个Key后仅另一个Key可继续鉴权

- pc: 同一权限组 Key A 与 Key B 均已配置，Key A 启用，Key B 禁用。
- 使用 Key A 签发 JWT 调用受保护接口。
  - 鉴权成功。
- 使用 Key B 签发 JWT 调用同一接口。
  - 鉴权失败，并返回约定鉴权错误。

### tc-p2: 权限组最多仅允许两个Key配置

- pc: 权限组已配置 Key A 与 Key B。
- 继续新增第三个 Key C。
  - 配置保存失败或返回约定校验错误，不允许超过双 Key 上限。

### tc-p2: Key有效期和启用状态可独立配置互不影响

- pc: 权限组已配置 Key A 与 Key B。
- 修改 Key A 的有效期或启用状态，不修改 Key B。
  - Key A 按新配置生效，Key B 的有效期和状态保持不变。

### tc-p2: a和b槽位编辑后KeyId与KeyMaterial不发生错位

- pc: 权限组已配置 `key_..._a` 和 `key_..._b` 两个 Key，两个 Key 使用不同 Secret/PublicKey。
- 仅编辑 a 槽位的有效期、状态或 KeyMaterial。
  - a 槽位配置按新值生效，b 槽位的 `keyId`、KeyMaterial、状态和有效期保持不变。
- 分别使用 a、b 两个槽位对应 Token 调用受保护接口。
  - 鉴权结果与各自槽位配置一致，不出现 a/b 配置错位。

### tc-p3: KeyId格式非法时配置保存失败

- pc: 通过配置接口或后台准备新增 Key。
- 分别提交缺租户 ID、缺有效期片段、后缀非 `a/b`、包含空格或特殊字符的 `keyId`。
  - 配置保存失败，并返回明确字段校验错误。

## 全量新增鉴权组链路（FullNewAuthGroupFlow）

### tc-p1: 全量新增单鉴权方式HS256主链路成功

- pc: 从零新增 SAAS 权限组，仅配置一个 HS256 Key，状态启用且当前 UTC+0 在有效期内。
- 使用 Auth 生成 Token 接口生成 JWT。
  - Token 生成成功，Header 和 Payload 符合约定。
- 使用该 Token 调用受保护接口。
  - 鉴权成功，权限组可操作对应 Token 组。

### tc-p1: 全量新增单鉴权方式RS256主链路成功

- pc: 从零新增 SAAS 权限组，仅配置一个 RS256 Key，状态启用且当前 UTC+0 在有效期内。
- 客户侧使用 PrivateKey 生成 JWT，并传入约定 `issuer`、`kid` 和过期时间。
  - JWT 生成成功。
- 使用该 JWT 调用受保护接口。
  - Auth 使用配置的 PublicKey 验签成功。

### tc-p1: 全量新增双鉴权方式启用组合覆盖主链路

- pc: 从零新增 SAAS 权限组，配置 Key A 与 Key B，两个 Key 可分别为 HS256 或 RS256，均启用且在有效期内。
- 分别生成 Key A 与 Key B 对应 Token，并调用同一受保护接口。
  - 两个 Token 均鉴权成功，两个鉴权组均可按权限范围操作同一 Token 组。

### tc-p2: 双鉴权方式状态和算法组合判定表全链路覆盖

- pc: 权限组配置 Key A 与 Key B，组合覆盖 HS256+HS256、RS256+RS256、HS256+RS256、RS256+HS256。
- 对每种算法组合分别设置 Key A 启用、Key B 启用，生成对应 Token 调用接口。
  - 两个 Key 在启用且有效时均可通过全链路鉴权。
- 对每种算法组合分别将其中一个 Key 禁用或设置过期。
  - 禁用或过期 Key 生成或提交的 Token 不可用，另一个启用有效 Key 不受影响。

### tc-p2: 过期Key生成Token不可用于鉴权

- pc: HS256 Key 或 RS256 Key 已过期；HS256 通过 Auth 生成 Token，RS256 由客户侧按入参指定过期时间生成 Token。
- 使用过期 HS256 Key 请求 Auth 生成 Token 或使用生成结果调用接口。
  - 生成被拒绝或生成后的 Token 鉴权失败。
- 使用过期 RS256 Key 对应 PrivateKey 生成 JWT 后调用接口。
  - Auth 鉴权失败，过期 Key 不可用于验签。

### tc-p3: Token自身过期后即使Key有效也不可继续使用

- pc: Key 处于启用且有效期内，生成一个 JWT 自身 `exp` 已过期或很快过期的 Token。
- 在 Token 自身过期后调用受保护接口。
  - 鉴权失败，不因 Key 仍有效而放行过期 Token。

## JWT验签路由与权限控制（JwtVerificationRouting）

### tc-p1: 带kid的JWT按kid匹配Key完成验签

- pc: 权限组配置 Key A 与 Key B，两个 Key 使用不同 Secret/KeyMaterial，均启用且在有效期内。
- 使用 Key A 签发 JWT，Header 中传 `kid=KeyA`，Payload 中传合法 `issuer`。
  - 服务端按 `kid` 找到 Key A 并验签成功。
- 将同一 JWT Header 改为 `kid=KeyB` 但签名仍来自 Key A。
  - 验签失败，说明未错误使用其他 Key 兜底。

### tc-p1: 不带kid的历史JWT按issuer兼容验签

- pc: 权限组存在历史 Token 或兼容 Key，JWT Header 不包含 `kid`，Payload 中包含合法 `issuer`。
- 使用历史签发方式生成 JWT 调用受保护接口。
  - 服务端按 `issuer` 匹配 Secret/Key 并鉴权成功。

### tc-p1: kid命中但issuer不属于该权限组时拒绝越权

- pc: 准备权限组 A 与权限组 B，两个权限组分别有独立租户和 Key。
- 使用权限组 A 的 Key 签发 JWT，但 Payload 中写入权限组 B 的 `issuer` 或租户信息。
  - 鉴权失败，不允许通过 `kid` 绕过 `issuer` 与租户归属校验。

### tc-p2: 未知kid不回退到issuer兜底通过

- pc: JWT Header 传入不存在的 `kid`，Payload 中 `issuer` 为真实权限组。
- 调用受保护接口。
  - 鉴权失败，避免攻击者通过伪造 `kid` 触发不确定兜底逻辑。

### tc-p2: JWT缺issuer时鉴权失败

- pc: JWT Header 带合法 `kid`，签名可被对应 Key 验证，但 Payload 缺少 `issuer`。
- 调用受保护接口。
  - 鉴权失败或返回约定缺字段错误，不建立无发行方的权限上下文。

### tc-p2: 无kid且同issuer存在双Key时按兼容策略验签

- pc: 同一权限组存在 Key A 与 Key B，两个 Key 均启用且有效，JWT Header 不包含 `kid`，Payload 包含合法 `issuer`。
- 使用 Key A 签发无 `kid` JWT 调用受保护接口。
  - 按最终兼容策略验签成功或失败，结果应稳定且可解释。
- 使用 Key B 签发无 `kid` JWT 调用同一接口。
  - 结果符合相同兼容策略，不出现随机命中不同 Key 的不确定行为。

### tc-p2: JWTHeader中kid为空字符串或大小写不一致时拒绝或按约定处理

- pc: 权限组存在合法 `kid=key_xxx_a`。
- 构造 Header 中 `kid` 为空字符串、全空格、大小写变化或前后带空格的 JWT。
  - 请求按约定拒绝或规范化处理，不能误匹配到其他 Key。

### tc-p2: kid包含注入字符或路径字符时不可影响Key查询

- pc: 权限组存在合法 `kid`，鉴权服务按 `kid` 查询 Key 配置。
- 构造 Header 中 `kid` 包含 SQL 特殊字符、JSON 控制字符、路径穿越字符、超长字符串或 Unicode 混淆字符的 JWT。
  - 鉴权失败，并返回统一鉴权错误。
- 检查服务日志和配置数据。
  - 不出现 SQL 注入、路径读取、异常栈泄漏或配置数据被污染。

### tc-p2: JWTHeader外部密钥引用字段不被信任

- pc: 权限组配置合法 HS256 或 RS256 Key。
- 构造 Header 中包含 `jku`、`x5u`、`jwk` 等外部密钥引用字段的 JWT。
  - 服务端仅使用本地 SAAS 权限组配置的 Key 验签，不从 Header 指定地址或内嵌 JWK 动态取 Key。
- 使用攻击者自建 Key 签发同类 JWT 调用接口。
  - 鉴权失败。

### tc-p3: JWT结构异常或签名篡改时返回统一鉴权错误

- pc: 准备结构损坏、Base64 非法、Header 缺 `alg`、Payload 被篡改、签名为空等 JWT。
- 分别调用受保护接口。
  - 请求均被拒绝，响应不泄露 Secret、公钥、私钥或内部异常栈。

## Token生成与验签分工（TokenIssueAndVerifyFlow）

### tc-p1: HS256由Auth生成Token并完成验签

- pc: 权限组配置 HS256 Key，`issuer+secret` 合法，Key 启用且在有效期内。
- 调用 Auth 生成 Token 接口。
  - Auth 使用当前 HS256 Secret 生成 JWT，返回 Token 不包含明文 Secret。
- 使用返回 Token 调用受保护接口。
  - Auth 使用同一配置完成验签并放行。

### tc-p1: RS256由客户生成Token并由Auth验签

- pc: 权限组配置 RS256 Key，Auth 侧保存 PublicKey，客户侧持有 PrivateKey。
- 客户侧使用 PrivateKey 生成 JWT，Header 指定 `alg=RS256` 和合法 `kid`，Payload 指定合法 `issuer`。
  - JWT 可被提交到受保护接口。
- Auth 收到 JWT 后根据 `kid` 或 `issuer` 定位 PublicKey。
  - 验签成功并放行，不要求 Auth 持有 PrivateKey。

### tc-p2: HS256客户自行伪造Token不可绕过Auth生成规则

- pc: 权限组配置 HS256 Key，客户不知道当前 Secret 或使用旧 Secret。
- 客户自行构造 HS256 JWT 并调用受保护接口。
  - 鉴权失败，不能绕过 Auth 生成 Token 或当前 Secret 校验。

### tc-p2: Auth生成Token接口不允许指定禁用或未生效Key

- pc: 同一权限组存在启用 Key、禁用 Key 和待启用 Key。
- 调用 Auth 生成 Token 接口时显式指定禁用 Key 或待启用 Key 的 `kid`。
  - Token 生成失败或生成后不可鉴权，不能绕过 Key 状态控制。

### tc-p2: 双HS256启用时Auth生成Token的默认Key选择稳定

- pc: 同一权限组存在两个启用且有效的 HS256 Key，均允许 Auth 生成 Token。
- 不指定 `kid` 调用 Auth 生成 Token 接口。
  - Token 生成成功，Header 中返回的 `kid` 与产品约定默认 Key 一致。
- 连续多次生成 Token 并分别验签。
  - 默认 Key 选择稳定，不在 a/b Key 之间随机切换。
- 显式指定另一个启用 Key 的 `kid` 调用 Auth 生成 Token 接口。
  - Token Header 中 `kid` 与指定 Key 一致，并可按指定 Key 验签成功。

### tc-p2: Auth生成Token参数租户和权限组不一致时拒绝

- pc: 准备租户 A 和租户 B，各自拥有独立权限组和 Key。
- 使用租户 A 的调用凭证请求为租户 B 的权限组生成 Token。
  - Token 生成失败，不允许跨租户生成。
- 使用权限组 A 的 `issuer` 搭配权限组 B 的 `kid` 请求生成 Token。
  - Token 生成失败，生成链路同样校验 `issuer`、`kid`、租户和权限组归属关系。

## 算法兼容与密钥类型（AlgorithmCompatibility）

### tc-p1: HS256Key可完成签名和验签

- pc: 权限组 Key A 配置为 HS256，Secret 合法，Key A 启用且在有效期内。
- 使用 HS256 和 Key A Secret 签发 JWT 并调用受保护接口。
  - 鉴权成功。

### tc-p1: RS256Key可完成签名和验签

- pc: 权限组 Key B 配置为 RS256，私钥用于签发，公钥或证书用于服务端验签，Key B 启用且在有效期内。
- 使用 RS256 和 Key B 私钥签发 JWT 并调用受保护接口。
  - 鉴权成功。

### tc-p2: JWT声明算法与Key配置算法不一致时拒绝

- pc: 权限组 Key A 配置为 HS256，Key B 配置为 RS256。
- 使用 HS256 签发 JWT 但 Header `kid` 指向 RS256 Key。
  - 鉴权失败。
- 使用 RS256 签发 JWT 但 Header `kid` 指向 HS256 Key。
  - 鉴权失败。

### tc-p2: 禁止none算法或非白名单算法

- pc: 构造 Header `alg=none`、`HS384`、`RS512` 或其他未声明支持算法的 JWT。
- 调用受保护接口。
  - 鉴权失败，服务端只接受权限组配置允许的 HS256 或 RS256。

### tc-p1: 防止HS256与RS256算法混淆攻击

- pc: 权限组配置 RS256 Key，服务端保存 PublicKey，攻击者可获取 PublicKey。
- 使用 RS256 PublicKey 作为 HMAC Secret 伪造 `alg=HS256` 的 JWT，并将 `kid` 指向 RS256 Key。
  - 鉴权失败，服务端不将 RS256 PublicKey 当作 HS256 Secret 使用。
- 权限组配置 HS256 Key 时构造 `alg=RS256` 且 `kid` 指向 HS256 Key 的 JWT。
  - 鉴权失败，服务端严格按 Key 配置算法验签。

### tc-p3: RS256公钥格式错误时配置或鉴权失败

- pc: 准备格式错误、公私钥不匹配、过短或过期证书形式的 RS256 KeyMaterial。
- 保存配置或使用该 Key 签发 JWT 调用接口。
  - 配置保存失败或鉴权失败，并返回明确错误，不降级为 HS256 验签。

### tc-p2: Base64无换行Key格式可正常保存和验签

- pc: RS256 PublicKey 或证书内容按 Base64 无换行格式提交，内容本身可解析为合法公钥。
- 保存 RS256 Key 配置。
  - 配置保存成功，系统可正确解析无换行 Base64。
- 客户侧使用匹配 PrivateKey 生成 JWT 调用接口。
  - Auth 验签成功。

### tc-p2: PEM标准格式Key可正常保存和验签

- pc: RS256 PublicKey 以标准 PEM 格式提交，包含 `BEGIN PUBLIC KEY` 和 `END PUBLIC KEY` 头尾及换行。
- 保存 RS256 Key 配置。
  - 配置保存成功，系统可正确解析 PEM 标准格式。
- 客户侧使用匹配 PrivateKey 生成 JWT 调用接口。
  - Auth 验签成功。

### tc-p3: Base64换行异常或PEM头尾缺失时保存失败

- pc: 准备 Base64 内容中夹杂非法换行、空格、不可见字符，或 PEM 缺少头尾标记的 PublicKey。
- 保存 RS256 Key 配置。
  - 配置保存失败并返回明确格式错误，不写入可用配置或缓存。

### tc-p2: RS256配置误传PrivateKey时不应明文存储

- pc: 新增 RS256 Key 时误将 PrivateKey 提交到服务端配置接口。
- 保存配置。
  - 系统拒绝保存或按安全策略只接受 PublicKey，不在配置查询、日志和缓存中明文保存 PrivateKey。

### tc-p3: HS256Secret为空或强度过低时保存失败

- pc: 新增或编辑 HS256 Key。
- 提交空 Secret、过短 Secret、全空格 Secret 或明显弱 Secret。
  - 配置保存失败，并返回明确字段校验错误。

## 有效期与UTC+0边界（KeyValidity）

### tc-p1: 当前时间在Key有效期内时鉴权成功

- pc: Key 已启用，开始时间早于当前 UTC+0，结束时间晚于当前 UTC+0。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 鉴权成功。

### tc-p1: 当前时间早于Key开始时间时鉴权失败

- pc: Key 已启用，开始时间晚于当前 UTC+0。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 鉴权失败，未生效 Key 不允许提前使用。

### tc-p1: 当前时间晚于Key结束时间时鉴权失败

- pc: Key 已启用，结束时间早于当前 UTC+0。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 鉴权失败，过期 Key 不允许继续访问。

### tc-p2: 有效期开始和结束边界按UTC+0判断

- pc: Key 开始时间或结束时间设置在 UTC+0 日期边界，测试执行环境本地时区为 UTC+8。
- 分别在边界前、边界时刻、边界后构造鉴权请求。
  - 鉴权结果以 UTC+0 时间为准，不受服务器本地时区或客户端时区影响。

### tc-p2: 有效期配置非法时保存失败

- pc: 准备新增或编辑 Key。
- 提交开始时间晚于结束时间、时间格式非法、缺开始时间或缺结束时间的配置。
  - 配置保存失败，并返回明确字段校验错误。

### tc-p3: JWT自身exp与Key有效期同时存在时按更严格规则拒绝

- pc: JWT Payload 包含 `exp`，Key 也配置独立有效期。
- 构造 JWT 未过期但 Key 已过期的请求。
  - 鉴权失败。
- 构造 Key 未过期但 JWT 自身 `exp` 已过期的请求。
  - 鉴权失败。

### tc-p2: JWT的nbf和iat时间声明按UTC+0校验

- pc: Key 已启用且在有效期内，JWT Payload 包含 `nbf` 或 `iat`。
- 构造 `nbf` 晚于当前 UTC+0 的 JWT 调用受保护接口。
  - 鉴权失败或按约定时钟容忍窗口拒绝。
- 构造 `iat` 明显晚于当前 UTC+0 或早于允许范围的 JWT 调用受保护接口。
  - 鉴权失败或按约定策略处理，不因 Key 有效而放行异常时间 Token。

### tc-p3: 服务端时间轻微偏差时鉴权结果符合容忍策略

- pc: 多个 Auth 实例存在轻微时钟偏差，Key 和 JWT 接近有效期边界。
- 分别请求不同实例。
  - 鉴权结果符合统一的时钟容忍策略，不出现边界时间大范围随机失败。

## 临期告警与可观测性（ExpiryAlert）

### tc-p1: 鉴权时发现Key有效期小于1个月触发告警

- pc: Key 已启用且可验签，结束时间距离当前 UTC+0 小于 1 个月；告警渠道可观测。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 接口鉴权成功，同时触发 Key 临期告警。

### tc-p2: Key有效期等于或大于1个月不触发临期告警

- pc: Key 已启用，结束时间距离当前 UTC+0 等于或大于 1 个月。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 接口鉴权成功，不触发临期告警。

### tc-p2: 临期告警具备权限组和keyId定位信息

- pc: Key 有效期小于 1 个月，告警平台可查看告警详情。
- 触发一次成功鉴权。
  - 告警内容包含租户、权限组、`keyId`、有效期结束时间和环境信息，不包含 Secret 或私钥明文。

### tc-p3: 高频鉴权不会造成临期告警风暴

- pc: 临期 Key 被高频调用，告警去重或限流策略已配置。
- 在短时间内连续发起多次鉴权请求。
  - 告警按约定聚合、限流或去重，不因每次鉴权生成大量重复告警。

### tc-p2: 告警通道异常不影响正常鉴权结果

- pc: Key 已启用且可验签，结束时间距离当前 UTC+0 小于 1 个月；模拟告警服务超时、不可用或返回失败。
- 使用该 Key 签发 JWT 调用受保护接口。
  - 鉴权结果仍按 Key 和 Token 有效性判断，不因告警发送失败误拒绝合法请求。
- 检查日志或补偿任务。
  - 告警失败有可追踪记录或重试机制。

## 回归与安全（RegressionAndSecurity）

### tc-p1: 双Key切换期间新旧调用方均可访问授权接口

- pc: Key A 为旧调用方使用，Key B 为新调用方使用，两个 Key 同时启用且在有效期内。
- 旧调用方继续使用 Key A 签发 JWT。
  - 鉴权成功。
- 新调用方切换为 Key B 签发 JWT。
  - 鉴权成功，切换期间业务不中断。

### tc-p1: 双Key同时生效时两个鉴权组均有权操作同一Token组

- pc: 同一 Token 组绑定双 Key，两个鉴权组均处于启用且有效状态。
- 分别使用两个 Key 对应鉴权组调用同一 Token 组的授权操作接口。
  - 两个鉴权组均可按权限范围操作该 Token 组。

### tc-p1: 不同租户或权限组不可跨Token组操作

- pc: 准备租户 A 和租户 B，各自拥有独立权限组、Key 和 Token 组。
- 使用租户 A 的合法 Token 操作租户 B 的 Token 组。
  - 请求被拒绝，不允许跨租户或跨权限组越权。
- 使用租户 B 的合法 Token 操作租户 A 的 Token 组。
  - 请求被拒绝，权限边界保持双向隔离。

### tc-p2: 关闭旧Key后新Key链路不受影响

- pc: 调用方已完成从 Key A 到 Key B 的切换。
- 将 Key A 禁用，保留 Key B 启用。
  - Key A 请求失败，Key B 请求继续成功。

### tc-p2: 鉴权失败响应不泄露敏感KeyMaterial

- pc: 构造签名错误、算法错误、未知 `kid`、过期 Key 等失败请求。
- 调用受保护接口并检查响应、日志和可观测附件。
  - 不回显 Secret、私钥、公钥完整内容、签名原文或内部堆栈。

### tc-p3: Authorization请求头异常格式统一拒绝

- pc: 准备一个可正常鉴权的合法 Token。
- 分别使用缺少 `Bearer` 前缀、重复 `Bearer` 前缀、多个 Token 拼接、Token 前后带不可见字符或换行的 Authorization Header 调用接口。
  - 请求被统一拒绝或按约定规范化处理，不因 Header 解析差异误放行。
- 使用标准 `Authorization: Bearer {token}` 再次调用。
  - 鉴权成功，说明异常格式处理不影响正常请求。

### tc-p3: 配置缓存刷新后多实例鉴权结果一致

- pc: Auth 服务存在多个实例，权限组 Key 状态或有效期发生变更。
- 在缓存刷新窗口内连续请求不同实例。
  - 刷新完成后所有实例对同一 JWT 的鉴权结果一致。

### tc-p3: 并发鉴权期间更新Key配置不产生随机通过

- pc: 持续使用同一 Key 发起并发鉴权，同时将该 Key 从启用改为禁用或调整为过期。
- 观察配置变更前后鉴权结果。
  - 结果符合配置生效时点和缓存策略，不出现同一实例随机通过或随机失败。

### tc-p2: 审计日志记录Key配置变更但不泄露敏感值

- pc: 对同一权限组执行新增、修改、禁用、启用、删除 Key 操作。
- 查询审计日志或操作记录。
  - 日志包含操作人、时间、权限组、`keyId`、操作类型和结果。
- 检查审计日志中的 KeyMaterial 字段。
  - Secret、私钥和签名材料不明文展示。

## 回滚方案验证（RollbackPlanVerification）

### tc-p1: 双Key版本回滚后存量单Key鉴权仍可用

- pc: 双 Key 版本已上线并完成存量迁移，准备回滚到上一版本或关闭双 Key 开关的方案。
- 执行回滚或关闭双 Key 能力。
  - 服务恢复到单 Key 鉴权模式，存量单 Key 配置仍可被读取。
- 使用回滚前已可用的历史 Token 调用受保护接口。
  - 鉴权成功，核心业务不中断。

### tc-p1: 回滚后Auth生成Token链路仍可用

- pc: 回滚后保留一份有效单 Key 权限组配置。
- 调用 Auth 生成 Token 接口。
  - Token 生成成功。
- 使用生成 Token 调用受保护接口。
  - 鉴权成功。

### tc-p2: 回滚前新增的双Key配置有明确兼容或清理策略

- pc: 双 Key 版本中新建过 Key A 和 Key B，且两个 Key 可能包含 HS256 或 RS256。
- 执行回滚流程并查询权限组配置。
  - 系统明确保留默认 Key、禁用新增 Key 或阻断回滚，并给出可执行处理结果。
- 使用被保留 Key 和被禁用或清理 Key 分别调用接口。
  - 鉴权结果符合回滚策略，不出现两个版本之间状态不一致。

### tc-p2: 回滚后缓存不保留已删除或禁用Key

- pc: 双 Key 版本中曾删除或禁用某 Key，随后执行回滚。
- 回滚后等待缓存刷新完成。
  - 已删除或禁用 Key 不因旧缓存恢复可用。
- 使用该 Key 对应 Token 调用受保护接口。
  - 鉴权失败。

## 评审待确认项

- rc: 双 Key 的配置入口、保存接口、查询接口、发布流程和权限控制是否已有 Apifox 或后台设计。
- rc: `key_{租户id}_{有效期}_{有效期}_a/b` 中两个“有效期”分别代表开始时间、结束时间，还是其他业务字段；时间格式是否包含时分秒和时区。
- rc: 无 `kid` 的 JWT 按 `issuer` 匹配时，如果同一 `issuer` 下存在两个启用 Key，应按顺序尝试、指定默认 Key，还是只兼容迁移前单 Key。
- rc: `kid` 命中 Key 但 Payload `issuer` 与 Key 所属权限组不一致时，最终错误码和安全策略需要明确。
- rc: HS256 与 RS256 是否允许同一权限组同时存在，还是单个权限组可选择其中一种算法；RS256 KeyMaterial 保存公钥、证书还是 JWKS。
- rc: “有效期小于 1 个月”按自然月、30 天、31 天还是日历月计算；是否以 UTC+0 当前时间精确到秒判断。
- rc: 临期告警触发渠道、告警内容、去重频率、严重级别和恢复规则需要明确。
- rc: Key 禁用、过期、未知 `kid`、算法不匹配、签名失败、迁移异常等错误码和响应结构需要补充。
- rc: 配置缓存 TTL、刷新机制和多实例一致性策略需要明确，便于设计稳定自动化回归。
- rc: Auth 生成 Token 接口对 HS256、RS256 的职责边界需要明确：HS256 是否只允许 Auth 生成，RS256 是否完全由客户侧生成并由 Auth 仅验签。
- rc: RS256 PublicKey 支持 Base64 无换行、PEM 标准格式或 JWKS 的最终格式约束需要明确。
- rc: 回滚方案是版本回滚、功能开关关闭、配置降级还是数据回滚；双 Key 新增数据在回滚后的保留和清理策略需要明确。
- rc: `kid` 和 `issuer` 的唯一性范围需要明确：全局唯一、租户内唯一、权限组内唯一，还是允许同 `issuer` 绑定多个 Key。
- rc: 无 `kid` 且同一 `issuer` 下存在两个启用 Key 时，验签顺序、默认 Key 或兼容策略需要明确。
- rc: 配置查询、审计日志和缓存观测中 Secret、PrivateKey、PublicKey 是否需要脱敏，以及脱敏规则需要明确。
- rc: JWT Header 中 `jku`、`x5u`、`jwk` 等外部密钥引用字段是否统一忽略或直接拒绝需要明确。
- rc: JWT `nbf`、`iat`、`exp` 的时钟容忍窗口、最大 Token 生命周期和多实例时间同步策略需要明确。
- rc: Key 删除后是否允许复用相同 `kid` 或相同 a/b 槽位，以及复用时旧 Token 是否必须失效需要明确。
- rc: Auth 生成 Token 接口的调用凭证、租户、权限组、`issuer`、`kid` 之间的归属校验规则需要明确。
- rc: 双 HS256 Key 同时启用时，Auth 生成 Token 默认选择 a 槽位、b 槽位、最近启用 Key，还是必须由调用方显式指定 `kid` 需要明确。
