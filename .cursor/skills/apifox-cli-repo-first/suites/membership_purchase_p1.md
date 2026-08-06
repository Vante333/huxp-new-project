# membership_purchase_p1 · CLI 落地笔记

- **场景**：366626 · `Membership Purchase P1 · CLI sync`
- **目录**：folderId **350048** · `common/P1（全量用例）/others`（2026-07-29 全量迁移）
- **分支**：`ai/apifox-cli-sync`
- **环境**：351893 · UAT（canary）— 与 P0 共用；鉴权 `.env` 的 `MP_P0_*`
- **详解**：[`Membership-Purchase-P1-apifox-cli-repo-first.md`](../../../../api-testcases/api_tests/postman/docs/Membership-Purchase-P1-apifox-cli-repo-first.md)
- **报告**：`apifox-reports/membership_purchase_p1/`
- **生成器**：`generators/GeneratePostmanCollectionMembershipPurchaseP1.py`

## 场景内分组

- **正向 E2E**
  - 商品B-无券-原价（P0 冒烟）+ 子组：已配置/未配置币种 E2E
  - 商品A-传券-订阅引导期（P0；Create **status=9**；0 元 Payments 失败；**activationMethod=1**）+ 币种子组
  - 商品A-引导期未开-原价（**activationMethod=2**）+ 币种子组
  - **隔离负向（嵌主链路）**：Create/`purchase/details`(DET1) 后 → `POST /v2/orders/memberships/details`（`*-MS-DET`）用同一购买 orderId；期望 `code=-1` 且 `msg/errCode` 非空（不钉精确码）
  - 再次取链（email 必填见 Preview 字段校验同组）
  - 币种键：B=`productBCurrencyConfigured|Unconfigured`；A=`productACurrencyConfigured|Unconfigured`；未配置回落 `productBCurrency`/`productACurrency`；已配置断言 `payment.currency=入参`
- **负向-Preview/Create**：无订阅/订阅关 `autoRenewal=false`（Preview `valid=false` 原价、Create **500.020.031**）；B/A autoRenewal=true、无效/过期/跨 Program/非周期/不满足条件券
- **Preview字段校验**：必填缺失/null（appId/autoRenewal/**email**）；类型错误（appId 字符串 / autoRenewal=1 / profile=[] / email=123）；**email 必填且 clientUserId 选填（同组含 Create/purchase：仅 email / 同时传 / cuid-only / 都不传 / email=null）**
- **Create字段校验**：必填缺失/null（appId/autoRenewal/email）；类型错误（appId 字符串 / autoRenewal=1 / email=123）；email 必填变体见 Preview email 同组
- **负向-Create**：033/031/702/032、email 必填负向
- **Details字段校验**：orderId `{}` / null / number / 空串
- **负向-Payments**：缺 orderId（造数 Create 同组）

## P1 业务变量（数据集选行，勿写 Environment）

**按场景选变量 / Apifox 数据集**：[`datasets/membership_purchase_p1/`](../../../../api-testcases/api_tests/postman/datasets/membership_purchase_p1/)  
- **导入全量数据**：`apifox-dataset-business-ascii.csv`，编码选 **UTF-8**  
- 对照表：`scenario-env-matrix.csv`（勿当数据集）  
- Environment **351893** 只留 `baseUrl` / `x-version`（与其它套件共用，**勿整表删**）；券码/金额等业务键请从 Environment 手动删掉，改到数据集对应行。

`CouponIntroNoRenew*`、`productANoSub*`、`productASubOff*`、`productANoIntroPayableAmount`、
`CouponExpired`、`CouponIneligible`、`CouponWrongType`、
`ExistingActiveProfileEmail/clientUserId`；不存在券用生成器默认 `CouponNotFoundCode`。

## Create 业务失败 errCode（已确认）

- **500.020.033**：autoRenewal 不支持（含：B/A autoRenewal=true）
- **500.020.031**：不存在券；无订阅/订阅关且 autoRenewal=false
- **500.000.702**：过期 / 非周期 / 有效但不满足条件

## 本批排除

callback、支付成功 activation、redemptionCode、失败单 Details、下游 5xx、探索边界、分级告警、已支付取消退款。

## 坑

1. 与 P0 相同：`purchase/preview` 可能仍 `201.000.001`（Program 未开通 purchase）。
2. 重复订阅负向依赖 `ExistingActiveProfile*` 为沙箱已有生效订阅用户。
3. 无订阅 vs 订阅关两负向共用 `CouponIntroNoRenew`，靠 `productANoSub*` / `productASubOff*` 区分 Preview 金额期望；Create 均期望 **500.020.031**。
4. **换测变量播报**（2026-07-28）：填写指南只打 **控制台短行**，勿用长 `assertInfo` 占断言面板。未开引导期 Group 仅 `announce_only_keys=["productANoIntroPayableAmount"]`（通常=`productAPrice`）。通则见 Skill reference「换测 Environment：Group 变量定位与控制台短提示」。
5. **业务变量只走全量数据选行**（2026-08）：Environment 351893 仅保留网关等非 MP 键；MP 业务键（`product*`/`Coupon*`/`returnUrl`/`orderIdProduct*`/`*_cancelOk`）已从 351893 剥离。种子见 `Lines_SeedRuntimeEnvP1`；`setRuntime` **不再写 Environment**。用户报「勾了行却是旧券码」→ 按 reference 症状表改种子，勿只改文档。
6. **errCode（已按沙箱校正）**：过期 / 非周期 / 不满足条件 Create → **500.000.702**；不存在券 → **500.020.031**。不满足条件 Preview：`details=null`（标题或仍写「保留详情」，以断言为准）。
7. **已删除 Group**：`优惠券编码边界与跨Program券按无效规则处理（传couponCode）`（及数据集 `neg_coupon_cross` / `CouponCrossProgram`）。
8. **鉴权选行 vs 后续 X-Program-ID**（2026-08）：曾出现勾 `203566…`、Preview 仍打 `203278…`（`.env` 第一套）。根因：`BearerJsonHeaders` 写死 + 种子 `_id\|\|_v\|\|_fb` 跳过 Environment 并用 upsert 盖头。已修为占位符 + `iterationData→env→variables→collection→globals→.env` + 四作用域持久化。用户再报同类 → 按 Skill reference「鉴权选行与后续步骤 ProgramID」自动改并 Push；复验须 **先 Auth 再业务**。
9. **业务 body 误带 `clientId`/`secret`**（2026-08）：种子曾对任意 JSON body 无条件写入鉴权字段，污染 Preview/Create/Details 等。已改为仅 Auth body（本就含该键）才覆盖；复验看「实际请求」body 不应再出现这两字段。
10. **Details `deductionAmount` 期望=0、实际=original−payable**（2026-08）：`Lines_DetailsPending` 曾读 `productADeduction||0`，与 Preview/Create 的 `money2(price−payable)` 不一致（例 MOP：14.37−10→期望应为 4.37）。已改 Details 与公式对齐；`productADeduction` 仅参考、不作硬期望。
11. **单步调试 `301.000.001` · X-Request-ID 非法**（2026-08）：curl 出现 `--header 'X-Request-ID;'`（无值）。根因 Apifox 常不展开头里的 `{{$guid}}`。已统一走 `collection_builder_common.Lines_EnsureRequestIdHeader`（P0/P1 EnsureAuth 挂载）；全量同类套件同修。改后须 Generate + Push。
12. **usage details 隔离**（2026-08）：正向 E2E 在 DET1 后插入 `POST /v2/orders/memberships/details`（`*-MS-DET`），用购买 orderId；断言仅 `code=-1` + `msg/errCode` 非空（HTTP 200/400 均可）。沙箱实测 `errCode=500.000.006`（暂不硬化）。**勿**在非 f-string 片段写 `}}` 收尾（曾导致 `missing ) after argument list`）。

## 未开引导期·原价（ANI）换测

| 键 | 含义 |
|----|------|
| `productANoIntroPayableAmount` | 应付期望；**填成与 `productAPrice` 相同** |

脚本写死：`autoRenewal=true` + `CouponIntroValid`。商品侧须未开引导期阶段计费。
