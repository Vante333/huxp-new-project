# 网络清单取值改造（NetworkLanguage）测试用例

## 测试范围说明

- rc: 对比分支：`master...feat-hzhan-20260618-network-language`（当前分支 `feat-hzhan-20260618-network-language`）。
- rc: 依据材料：网络调用链风险分析、语言缓存风险审查、QA 场景分析报告（本会话汇总稿）。
- rc: **改造核心**：清单取值切 `NetworkEndpointFace.getModuleNetwork`；单资源授权切 `verifyAvailability`；tier 切 `NetworkGroupEndpointFace.getGroupTier`；Lounge/FastTrack 新增 L1 Caffeine；详情缓存 key / 坐标 / prebooking 字段映射有变更。
- rc: 接口路径、错误码、主数据以 **Apifox/MCP** 与联调环境为准；文中错误码来自代码/历史约定，联调不一致时以环境为准并回写本文。
- rc: **在范围**：资源详情/列表授权、预约可用性双检、品类子接口入口授权、TransportHub 授权、tier、缓存刷新一致性、Dining module=6、Feign 失败表现、语言传递。
- rc: **弱影响/对照**：`GET /v2/projects/{projectId}/resources`（清单仍走旧 BaseData，`needFilter=false`）。
- rc: **不在范围**：`NetworkResoucesEndpointFace` 死代码、BaseDataFeignTest 编译问题、订单流其他改动、ES 搜索索引层（diff 未覆盖）。
- rc: 历史材料中的 P0 映射为本文 `tc-p1`；P1→`tc-p2`；P2→`tc-p3`。

## 共性数据准备（TestData）

### Program与资源

| 代号 | 说明 |
|------|------|
| P1 | 当前鉴权 token 对应 program；清单内含 lounge(`N*`)、cip(`C*`)、dining、fitness(`RES_*`)、esim、localOffer 各≥1 |
| P2 | 同环境另一 program 下资源，或本 program 清单外的跨 program 资源（如 `N99999`） |
| P3 | lounge/cip 各 1 个，tier 分组明确且与默认 1 不同（用于 tier 对拍） |
| DINE-IN | 餐饮聚合资源，客户端可传 `module=6`；底层对应 SET_MEAL(3)/COUPON(4) 清单语义（待确认下游是否识别 6） |

### 语言

| 代号 | language | 说明 |
|------|----------|------|
| L1 | `en-US` | 默认 |
| L2 | `zh-CN` / `ja-JP` | 走 `LanguageUtils.getBossLanguage` |
| L3 | 目标语种无 Boss 翻译 | 验证 fallbackAllowed 行为 |

### 鉴权

- 使用 P1 的合法 Bearer token，确保 `RequestContext.programId` 会传入 Feign。
- 涉及 Job/MQ/缓存刷新时：确认执行线程已 `requestService.init(programId)`（或等价初始化）。

---

## 资源详情授权门禁（NeedFilterTrue）

### GET_v1_resources_{resourceId}

#### tc-p1: Lounge在清单内详情成功且nearestGate优先nearestBoardingGate

- pc: P1 下 lounge 在清单内（如 `N01336`）；同时存在 `nearestBoardingGate` 与 `boardingGateNearby`；`language=en-US`；`fallbackAllowed=false`。
- 调用 `GET /v1/resources/{resourceId}?language=en-US&fallbackAllowed=false`。
  - HTTP 200；返回该资源详情；`locationInfo.nearestGate` 优先取 `nearestBoardingGate`（与分支映射一致）。

#### tc-p1: 资源不在ProgramNetwork清单时详情返回业务错误

| resourceId | module暗示 | 预期错误码（以环境为准） |
|------------|-----------|------------------------|
| 清单外 lounge | — | `500_020_007`（或当前环境等价业务码） |
| 清单外 cip | — | 同上 |

- pc: 使用 P1 token；resourceId 确认为清单外。
- 调用 `GET /v1/resources/{resourceId}?language=en-US`。
  - 返回约定业务错误，不返回完整详情体。

#### tc-p2: Lounge无目标语种翻译时按fallbackAllowed分支

| language | fallbackAllowed | 预期 |
|----------|-----------------|------|
| zh-CN（无翻译） | false | `500_020_015`（或环境等价） |
| zh-CN（无翻译） | true | 200；language 回退 en-US（或产品约定回退语种） |

- pc: 资源在清单内；Boss 仅有英文数据。
- 按表调用 `GET /v1/resources/{resourceId}`。
  - 响应与上表预期一致。

#### tc-p1: CIP详情prebookingRequiredInfo取自Boss字段而非旧Nacos

- pc: CIP 资源 `collectPassengerDetail` 含 `email,name,tel` 且 `flightNo=1`；另备「旧 Nacos 必填但 Boss 未收集」反向资源（若有）。
- 调用 `GET /v1/resources/{cipResourceId}?language=en-US`。
  - `prebookingRequiredInfo` 中 email/phone/callingCode/firstName/lastName/transportNumber 与 Boss 字段一致；不再强制对齐 master 的 Nacos `CipPrebookingConfig`。

#### tc-p2: Lounge详情prebookingRequiredInfo固定姓名必填其余false

- pc: Lounge 资源在清单内。
- 调用 `GET /v1/resources/{loungeResourceId}?language=en-US`。
  - `prebookingRequiredInfo` 中 firstName/lastName 为 true，其余为 false（不再读 Nacos `LoungePrebookingConfig`）。

### GET_v2_resources_{resourceId}

#### tc-p1: 多品类资源在清单内详情成功

| module | 典型resourceId | 额外关注字段 |
|--------|----------------|-------------|
| 1 | lounge `N*` | `extra.loungeInfo.tier`、nearestGate、prebookingRequiredInfo |
| 2 | cip `C*` | `extra.fastTrackInfo.tier`、prebookingRequiredInfo |
| 7 | fitness `RES_*` | 无 tier；仅授权门禁 |
| 8 | esim | 授权门禁 |
| 11 | localOffer | `countryOrRegion`（regionInfo.type=country 时写 iso） |

- pc: P1 清单内各品类资源可用；Bearer 为 P1。
- 调用 `GET /v2/resources/{resourceId}?module={module}&language=en-US`。
  - HTTP 200；返回对应品类详情；上表关注字段存在且符合分支映射。

#### tc-p1: 多品类资源不在清单时详情失败

- pc: 各 module 各备 1 个清单外 resourceId。
- 调用 `GET /v2/resources/{resourceId}?module={module}&language=en-US`。
  - 返回业务错误（常见 `500_020_007` / 详情 null 触发码，以环境为准），不返回完整授权后详情。

#### tc-p2: Lounge或CIP的tier来自ProgramNetworkGroup且空则默认1

- pc: P3 资源有明确非 1 的 tier；另备无分组资源。
- 分别调用 `GET /v2/resources/{id}?module=1|2&language=en-US`；必要时与 master 同资源对拍。
  - 有分组：`extra.*.tier` 等于 ProgramNetworkGroup 配置；无分组或 tier 空：默认 `1`；与 master 对拍时记录差异（数据源已切换属预期，值需业务确认）。

#### tc-p1: Dining传module等于6时可用性校验不被误判无权限

- pc: 餐饮资源在 SET_MEAL(3) 或 COUPON(4) 清单内；客户端传 `module=6`（或 module 空由 DiningProcessor 默认 6）；`needFilter=true` 路径。
- 调用 `GET /v2/resources/{diningId}?module=6&language=en-US`（及列表侧等价入口若可复现）。
  - 合法餐饮资源应 200 返回详情；**不得**因下游不识别 `moduleType=6` 被误判无权限（若失败记缺陷：DINING 双模块逻辑丢失）。
- rc: 旧逻辑分别查 3/4；新逻辑直接传 `moduleType=6`。若产品确认下游已支持 6，则本用例预期改为「与基于ata 契约一致」。
- tag: Dining,module=6,回归风险

---

## 预约可用性（PrebookingAvailability）

### POST_v1_resources_prebookings_availability

#### tc-p1: Lounge预约可用性清单与verifyAvailability双检矩阵

| resourceId | getModuleNetwork清单 | verifyAvailability | 预期 |
|------------|---------------------|-------------------|------|
| 在清单可预约 | 包含 | available=true | 200；available 为可预约语义 |
| 不在清单 | 不包含 | — | 业务错误（常见 `500_020_007`，步骤2拦截） |
| 清单含但verify=false | 包含 | false | 步骤2通过后步骤3失败，业务错误 `500_020_007`（或等价） |

- pc: 项目开启 reservation；网点 bookable；有效 membershipId（status=USED，sourceCode=当前 programId）；另测无 membershipId（跳过权益校验仍做清单校验）。
- 调用 `POST /v1/resources/prebookings/availability`，body 含 resourceId、membershipId、prebookingDate(UTC+2h)、adultCount=1、childCount=0。
  - 结果与上表一致。
- rc: 清单语言硬编码 `DEFAULT_LANGUAGE_EN`，与用户 language 无关——需额外确认 ProgramNetwork 是否语种敏感。

#### tc-p2: 预约可用性Feign失败时表现为系统错误而非业务码

- pc: 可模拟 `ProgramNetworkFeign.verifyAvailability` 或 `getModuleNetwork` 超时/5xx（联调桩或基于ata 临时故障窗口）。
- 调用同一 availability 接口，资源本应在清单内。
  - 接口返回系统错误/500（`RuntimeException` 路径），而非稳定业务码 `500_020_007`；记录实际 HTTP 与错误体以便产品确认是否接受。
- tag: Feign失败,降级缺失

### POST_v2_resources_options_prebookings_availability

#### tc-p1: fitness_esim_localOffer预约可用性入口授权

| module | 典型resource | 特殊前置 |
|--------|-------------|---------|
| 7 | fitness RES_* | adultCount=1；schedule 状态=1 |
| 8 | esim | adultCount=1；prebookingDate UTC+1h |
| 11 | localOffer | prebookingDate > now(UTC) |

- pc: 各 module 准备「在清单」与「不在清单」资源；optionId 有效。
- 对在清单资源调用 `POST /v2/resources/options/prebookings/availability`。
  - HTTP 200（或业务 available 成功语义）；后续 option/库存校验按原逻辑。
- 对不在清单资源调用同一接口。
  - 返回 `500_020_007`（或环境等价），在入口 `getResourceDetailCache(needFilter=true)` 被拦截。

---

## 品类子接口入口授权（SubResourceGate）

### GET_v2_resources_fitness_{resourceId}_schedule

#### tc-p1: Fitness排班接口按清单授权门禁

- pc: fitness 在/不在 P1 清单各 1 个；`startDate` 合法。
- 调用在清单资源：`GET /v2/resources/fitness/{resourceId}/schedule?startDate=...`。
  - HTTP 200；返回 schedules；schedule 内容本身不受清单改造影响。
- 调用不在清单资源。
  - 业务错误（常见 `500_020_010`，detail null）。

### GET_v2_resources_fitness_{resourceId}_options_{optionId}

#### tc-p2: Fitness选项详情授权与语言fallback

| resourceId | optionId | language | fallback | 预期 |
|------------|----------|----------|----------|------|
| 在清单 | 有效 | en-US | — | 200 |
| 在清单 | 有效 | zh-CN 无翻译 | false | `500_020_015` |
| 不在清单 | — | — | — | `500_020_010` |

- pc: 同上表数据。
- 按表调用接口。
  - 响应与预期一致。

### GET_v2_resources_esims_{resourceId}_options

#### tc-p1: eSIM选项列表与详情授权门禁

| 接口 | 在清单 | 不在清单预期 |
|------|--------|-------------|
| `GET .../esims/{id}/options` | 200 + options | `500_020_016`（或环境等价） |
| `GET .../esims/{id}/options/{optionId}` | 200 + option | `500_020_007`（或环境等价） |

- pc: esim 在清单且有 options；另备清单外 esim。
- 分别调用列表与详情。
  - 在清单：option 内容与 master/Boss 一致；不在清单：错误码符合上表。

### GET_v2_resources_localOffers_{resourceId}_options

#### tc-p2: LocalOffer选项接口授权与countryOrRegion映射

- pc: localOffer 在/不在清单各 1；详情层存在 `regionInfo.type=country` 数据。
- 调用 options / optionDetail。
  - 不在清单：入口授权失败；在清单：options 可用，详情 `countryOrRegion` 按分支映射写入 iso（若适用）。

### POST_v2_orders_esims_topup_availability

#### tc-p1: eSIM充值可用性入口资源授权

- pc: 有效 membership/ePass + iccid 归属正确；option 兼容；esim 在/不在清单各 1。
- 调用 `POST /v2/orders/esims/topup/availability`（resourceId/optionId/iccid/membershipId/prebookingDate/adultCount）。
  - 不在清单：`500_020_007`（或步骤4等价业务码）；在清单且后续校验通过：200 + prebookingToken。

---

## TransportHub授权（TransportHubAvailability）

### GET_v2_transportHubs_{transportHubId}

#### tc-p1: 机场详情授权在清单内成功不在清单失败

- pc: P1 下授权机场与未授权机场各 1；`language` 任意合法值。
- 调用授权机场 `GET /v2/transportHubs/{transportHubId}`。
  - HTTP 200；返回机场详情。
- 调用未授权机场。
  - 业务错误（常见 `TRANSPORT_HUB_ERROR_500_020_003` 或环境等价）。

#### tc-p2: verifyAvailability返回available为null时不崩溃

- pc: 可构造 basedata 成功但 `available` 字段缺失/null 的响应（联调桩）。
- 调用机场详情或资源详情权限过滤路径。
  - 应有明确业务失败或安全默认（false），**不得**因 Boolean 拆箱 NPE 变成未处理 500；若现状为 NPE/500 则记缺陷。
- tag: BooleanNull,NPE风险

---

## 资源列表与聚合（ResourceListAndHub）

### GET_v2_resources与机场资源聚合

#### tc-p1: 资源列表与机场聚合仅返回ProgramNetwork清单内资源

- pc: P1 下多品类清单内/外资源并存；机场下挂多资源。
- 调用 `GET /v2/resources?...`（按 module 分品类）及 `GET /v2/transportHubs/{id}/resources`。
  - 返回的 resourceId 集合 ⊆ `getModuleNetwork` 清单；清单外资源不出现。

#### tc-p2: Dining列表module等于6时清单范围正确

- pc: 同一机场/program 下存在套餐与券类餐饮资源。
- 调用 `GET /v2/resources?module=6&...`。
  - 返回范围与产品对「聚合餐饮」的定义一致（应覆盖原 3+4 语义）；若只返回空或全拒，记缺陷。

#### tc-p3: 列表语言参数经bossLanguage传递后与master语义一致

- pc: 同一清单在 en-US 与 zh-CN 下资源集合应一致（若 ProgramNetwork 非语种敏感）；或按契约差异记录。
- 分别用 L1/L2 调用列表接口。
  - 资源集合符合契约；无因 `lg`/`bossLanguage` 双轨导致的意外缩集/扩集。

---

## Tier填充（NetworkGroupTier）

### GET_v2_resources列表与详情tier

#### tc-p2: 远端getOne失败时接口行为（降级vs500）

- pc: 可模拟 `ProgramNetworkGroupFeign.getOne` 超时/非 success；资源本身在清单内。
- 调用会填充 tier 的列表或详情（lounge/cip）。
  - **现状风险**：抛 `RuntimeException` 导致整体 500，而非 master 静默 `tier=1`；记录实际表现；若产品要求降级，提缺陷。
- rc: master `getOneOrDefault` 失败→null→tier=1。

#### tc-p3: NetworkGroup缓存命中后tier稳定

- pc: 同一 programId+resourceId 连续两次详情；存在 `API:NetworkGroup:{programId}:{resourceId}` 缓存（约 300s）。
- 连续调用两次详情。
  - `extra.*.tier` 两次一致；缓存期内 basedata 变更不立即反映（记录滞后窗口）。

---

## 缓存一致性（CacheConsistency）

### FastTrackL1Key

#### tc-p1: FastTrack刷新后详情不应继续命中旧L1

- pc: 先成功读取某 CIP 详情写入 L1；修改 Boss/可观测字段（或替换坐标源数据）；触发 `FastTrackCache.refreshDetail`（XXL Job `ResourceRefreshCacheJob` / 缓存清理 Job）。
- 再次调用 `GET /v2/resources/{ftId}?module=2`（或 v1 等价）。
  - 应返回刷新后数据；**不得**因 L1 key `API:FasTrackDetail` vs `API:FastTrackDetail` 拼写不一致仍命中旧 L1（最长约 55min/TTL 3300s）。
- tag: L1KeyTypo,FastTrack

### LocalOffer与Dining的L2Key

#### tc-p1: LocalOffer刷新后Redis层详情应更新

- pc: 先 `detail` 命中旧 L2 key `LocalOfferDetail:...`；执行 `refreshDetail`（写入 `API:LocalOfferDetail:...`）；强制 L1 miss（或等 L1 失效）后再读。
- 调用 LocalOffer 资源详情。
  - 应读到刷新后数据；若仍命中旧 `LocalOfferDetail:` 则记缺陷（L2 读写前缀不一致）。

#### tc-p1: Dining刷新后Redis层详情应更新

- pc: 先读详情（`RDetailV2:`）；执行 `DiningCache.refreshDetail`（`RDetail:`）；再读详情。
- 调用 Dining 资源详情。
  - 应更新为刷新后数据；若仍读旧 `RDetailV2:` 记缺陷。

### Lounge与FastTrack坐标module

#### tc-p1: 刷新后Lounge与CIP的coordinates模块类型正确

| 品类 | refreshDetail误用 | detail正确module |
|------|------------------|------------------|
| Lounge | OFFER | LOUNGE |
| FastTrack | OFFER | CIP |

- pc: 资源有正确坐标数据；触发对应 `refreshDetail` 后立即读详情（优先 L1 hit）。
- 调用详情接口检查 `coordinates`。
  - 坐标与正确 module 数据一致，不为空/错模块；若刷新路径写入 OFFER 脏数据记缺陷。

### LoungeL1Enrichment

#### tc-p2: Lounge刷新写入L1后prebookingOnly仍完整

- pc: 触发 `LoungeCache.refreshDetail` 后，用户请求详情且 L1 命中。
- 调用 Lounge 详情。
  - `serviceTerms.prebookingOnly`（及读路径 enrichment 字段）与未刷新前读路径一致，不因 refresh 跳过 enrichment 而缺失。

### 清单变更与缓存滞后

#### tc-p2: 清单移除资源后缓存清前可能仍成功清后应失败

- pc: 资源在清单内且详情已缓存（L1/L2）。
- 步骤1：`GET /v2/resources/{id}?module=1` 成功。
  - HTTP 200。
- 步骤2：在 Basedata 从 program 清单移除该资源后立即再调。
  - 可能仍 200（缓存滞后，属已知风险）。
- 步骤3：手动 evict L1 + 清理 Redis `API:LoungeDetail:*`（或等待 >55min）后再调。
  - 返回业务错误（常见 `500_020_007`）。

---

## 弱影响对照（AeroBlueProjectResources）

### GET_v2_projects_{projectId}_resources

#### tc-p2: 项目资源列表仍走旧BaseData且详情needFilter为false

- pc: project 列表含某 resourceId，但该 id **不在** 当前 token program 的 ProgramNetwork 中。
- 调用 `GET /v2/projects/{projectId}/resources`（module=1）。
  - 列表仍返回该 resourceId（旧 BaseData 源）。
- 在同上下文取详情（AeroBlue/`needFilter=false` 路径）。
  - 详情可返回（不做 verifyAvailability）。
- 对比调用 `GET /v2/resources/{id}?module=1`（needFilter=true）。
  - 常规详情应授权失败；两接口授权策略不一致——标注为跨接口风险（非本次新引入但需知悉）。

---

## 上下文与Job链路（RequestContext）

#### tc-p1: HTTP主链路资源列表与详情不因RequestContext缺失NPE

- pc: 正常 HTTP 请求经拦截器初始化上下文。
- 调用资源列表、详情、机场详情、预约可用性主路径。
  - 全部可达业务结果或业务错误，无 NPE（`requestContext.getProgramId()`）。

#### tc-p2: 订单校验与限额链路在有上下文时可用

- pc: 走会触发 `OrderServiceImpl(V2).checkResources`、`ResourceLimitHandler`、`MultiOrderHandler` 餐饮/休息室校验的下单/预检路径；上下文已 init。
- 执行对应下单或预检。
  - 清单/授权校验生效；无 ThreadLocal NPE。

#### tc-p2: 缓存刷新Job在init后可安全调用getAvailableCodes

- pc: `ResourceRefreshCacheJob` / `CacheCleanJobService` 已按代码手动 init programId。
- 执行 Job 刷新各品类详情。
  - Job 成功完成；无因 RequestContext 为空导致的 NPE；刷新结果可被后续详情观察到（结合缓存用例）。

#### tc-p3: 未init的异步或内部调用访问清单时失败可定位

- pc: 若存在未 init 的内部调用路径（联调可造）。
- 触发该路径访问 `getAvailableCodes` / `checkResourcesAvailable`。
  - 当前实现可能 NPE/500；记录堆栈与入口；缺陷级别按是否生产可达判定。
- tag: RequestContext,NPE

---

## Health与兼容（ApiCompatibility）

#### tc-p3: 已删除Health调试端点返回404

| 已删除端点 |
|-----------|
| `GET /queryNetworkListByModule?lg=&filter=` |
| `GET /queryNetworkListByModuleAndHub?transportHubId=&lg=` |

- pc: 环境部署 feat 分支。
- 分别请求上表端点。
  - HTTP 404（或网关不可达）；依赖旧脚本需改走新排查方式。

#### tc-p3: 保留Health端点仍走旧lg语义

- pc: `/queryNetWorkList`、`/getNetWorkList` 仍存在。
- 调用保留端点。
  - 仍可用且走旧 BaseDataFeign + `lg`；与新 `bossLanguage` 路径并存——仅作排障对照，不作主验收。

---

## Feign失败与空指针防护（Resilience）

#### tc-p2: getModuleNetwork失败时资源列表表现为系统错误

- pc: 模拟 `ProgramNetworkFeign.getModuleNetwork` 失败/空 data。
- 调用依赖 `getAvailableCodes` 的资源列表或机场聚合。
  - 返回系统错误/500（`NetworkEndpointFaceImpl` 抛 RuntimeException），而非空列表静默；记录是否可接受。

#### tc-p2: TransportHub_verifyAvailability失败时机场详情系统错误

- pc: 模拟 `ProgramTransportHubFeign.verifyAvailability` 失败。
- 调用 `GET /v2/transportHubs/{id}`。
  - 系统错误/500；与「不在授权集合返回 false + 业务码」路径区分记录。

#### tc-p3: NetworkResoucesEndpointFace无运行时调用无功能回归

- pc: 全链路回归资源详情坐标（Lounge 仍可走 `baseDataFacade.getNetWorkDetailByModule` 旧路径）。
- 执行 Lounge/相关详情主路径。
  - 功能不受 `NetworkResoucesEndpointFace` 死代码影响；坐标读取路径符合当前实现。

---

## CountryRegion映射（ContractualRegionMappings）

### POST_v2_projects_reference_contractualRegionMappings

#### tc-p2: Nacos区域映射缺失时接口失败可复现

- pc: Nacos `wise-region-mapping.yaml` 未加载或缺少硬编码 region key（EUROPE/APAC 等）；或 mapping 为空。
- 调用 `POST /v2/projects/reference/contractualRegionMappings`（body 含 module 等，即使传非 lounge）。
  - 返回业务错误 `COUNTRY_REGION_500_000_026`（或 500）；`req.getModule()` 被忽略、`applicableModules` 硬编码 lounge——记录与产品预期差异。
- rc: 与网络清单主改造弱相关，但同分支有证据；按需纳入回归。

#### tc-p3: 配置齐全时区域映射返回成功

- pc: Nacos 映射配置完整且含约定 region key。
- 调用同一接口。
  - HTTP 200；items 非空；字段符合契约。

---

## 跨版本对拍（MasterVsFeat）

#### tc-p2: 同资源在master与feat的授权边界对拍

- pc: 准备边界资源（清单边缘、刚纳入/刚移出、Dining 聚合）；两环境数据尽量对齐。
- 对同一组 resourceId 分别调 master 与 feat 的详情/availability。
  - 记录 200 vs 业务错误差异表；非「数据源切换导致的预期差异」应提缺陷。

#### tc-p2: 同Lounge或CIP的tier值对拍

- pc: P3 资源在两环境均存在。
- 对比 `extra.loungeInfo.tier` / `extra.fastTrackInfo.tier`。
  - 记录差异；无分组两侧均应为 1；有分组差异需业务确认 ProgramNetworkGroup 迁移正确性。

#### tc-p3: prebookingRequiredInfo与master差异已文档化可接受

- pc: Lounge/CIP 各 1 个在两侧可查。
- 对比 `prebookingRequiredInfo`。
  - 差异符合「改读 Boss / Lounge 固定姓名」的改造说明；若出现未说明字段差异记缺陷。

---

## 建议执行顺序（ExecutionOrder）

1. **P1 授权门禁**：NeedFilterTrue 详情 + PrebookingAvailability + 子接口门禁 + eSIM topup + TransportHub + 列表清单范围 + Dining module=6。
2. **P1 缓存缺陷验证**：FastTrack L1 key、LocalOffer/Dining L2 key、Lounge/FT coordinates module。
3. **P1/P2 字段与对拍**：prebookingRequiredInfo、tier、master/feat 边界对拍。
4. **P2 韧性与上下文**：Feign 失败、Boolean null、RequestContext/Job、清单变更缓存滞后、AeroBlue 弱影响。
5. **P3 兼容与边缘**：Health 删除、CountryRegion、死代码无影响、语言双轨对照。
