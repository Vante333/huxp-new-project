# PAPI 看板 272（Generic API）近 3 个月新增需求

- 看板：[Generic API](https://dragonpass.atlassian.net/jira/software/c/projects/PAPI/boards/272)
- 统计区间：**2026-03-02** ~ **2026-06-02**（约 3 个月）
- JQL：`project = PAPI AND created >= "2026-03-02" ORDER BY created DESC`
- 说明：看板筛选为 `project = PAPI`；「需求」口径 = 排除缺陷、子任务、任务。

## 汇总

| 指标 | 数量 |
| --- | --- |
| 新建 Issue 总数 | 287 |
| **需求类（本表）** | **66** |
| 其中已同步到 `requirements/` | 16 |

### 全部 Issue 按类型

- 子任务：124
- 缺陷：95
- 故事：60
- 长篇故事：5
- 任务：2
- 计划：1

### 需求类按类型

- 故事：60
- 长篇故事：5
- 计划：1

### 需求类按状态

- 已完成：19
- Ready for QA Testing：15
- 待办：11
- READY FOR GO LIVE：6
- Business Requirement Collection：5
- 已取消：5
- Ready for PM Validation：4
- In QA Testing：1

## 需求清单（按创建时间倒序）

| Key | 创建日 | 类型 | 状态 | 优先级 | 标题 | 本地 MD |
| --- | --- | --- | --- | --- | --- | --- |
| [PAPI-2788](https://dragonpass.atlassian.net/browse/PAPI-2788) | 2026-05-29 | 故事 | 待办 | P2 | E-pass支持tier资源展示（仅资源） |  |
| [PAPI-2784](https://dragonpass.atlassian.net/browse/PAPI-2784) | 2026-05-29 | 故事 | Ready for QA Testing | P0 | 新增商业区域与iso国家地区code映射接口 |  |
| [PAPI-2780](https://dragonpass.atlassian.net/browse/PAPI-2780) | 2026-05-29 | 故事 | 待办 | P2 | 优化下单前的token可用性检查逻辑 |  |
| [PAPI-2771](https://dragonpass.atlassian.net/browse/PAPI-2771) | 2026-05-26 | 故事 | 待办 | P2 | 【订单流支持收银台】支付状态Callback |  |
| [PAPI-2767](https://dragonpass.atlassian.net/browse/PAPI-2767) | 2026-05-26 | 故事 | 待办 | P2 | 【订单流支持收银台】 拉起DP收银台 |  |
| [PAPI-2763](https://dragonpass.atlassian.net/browse/PAPI-2763) | 2026-05-26 | 故事 | 待办 | P2 | 【订单流支持收银台】 预览订单接口 |  |
| [PAPI-2761](https://dragonpass.atlassian.net/browse/PAPI-2761) | 2026-05-26 | 长篇故事 | Business Requirement Collection | P2 | 26'Q2 Roadmap - support h5 cashier in FT/Lounge Order flow |  |
| [PAPI-2758](https://dragonpass.atlassian.net/browse/PAPI-2758) | 2026-05-26 | 故事 | 待办 | P2 | 【订单流支持收银台】根据入参动态选择商品 |  |
| [PAPI-2750](https://dragonpass.atlassian.net/browse/PAPI-2750) | 2026-05-25 | 故事 | Ready for PM Validation | P2 | Local Offer 订单部分 |  |
| [PAPI-2739](https://dragonpass.atlassian.net/browse/PAPI-2739) | 2026-05-22 | 故事 | In QA Testing | P2 | 优化eSIM和Local offer只允许下1人次订单的提示语 |  |
| [PAPI-2735](https://dragonpass.atlassian.net/browse/PAPI-2735) | 2026-05-22 | 故事 | Ready for QA Testing | P0 | Support new language code｜新增多语种支持 |  |
| [PAPI-2730](https://dragonpass.atlassian.net/browse/PAPI-2730) | 2026-05-20 | 故事 | 待办 | P2 | token verification endpoint｜token鉴权接口 |  |
| [PAPI-2726](https://dragonpass.atlassian.net/browse/PAPI-2726) | 2026-05-20 | 故事 | 已完成 | P2 | 新增kms 私钥 |  |
| [PAPI-2722](https://dragonpass.atlassian.net/browse/PAPI-2722) | 2026-05-20 | 故事 | Ready for QA Testing | P2 | 休息室/FT预订单下单pii信息收集逻辑从nacos供应商编码改为读boss |  |
| [PAPI-2716](https://dragonpass.atlassian.net/browse/PAPI-2716) | 2026-05-14 | 故事 | 已取消 | P2 | 【Aero Blue】Fair usage Endpoint｜Fair usage 规则查询API |  |
| [PAPI-2712](https://dragonpass.atlassian.net/browse/PAPI-2712) | 2026-05-14 | 故事 | 待办 | P2 | 【Aero Blue】T&C/FAQ/Policy Endpoint｜文案与FAQ接口 |  |
| [PAPI-2707](https://dragonpass.atlassian.net/browse/PAPI-2707) | 2026-05-13 | 故事 | Ready for QA Testing | P2 | 【Revolut】FT 订单详情接口补回prebookingRequiredInfo，用户会籍列表接口补回programId |  |
| [PAPI-2700](https://dragonpass.atlassian.net/browse/PAPI-2700) | 2026-05-11 | 故事 | Ready for QA Testing | P2 | Support filtering the order list by status｜订单列表支持按状态过滤 |  |
| [PAPI-2697](https://dragonpass.atlassian.net/browse/PAPI-2697) | 2026-05-11 | 故事 | Ready for QA Testing | P2 | Support set meal/coupon redemption simulation in the Sandbox env｜simulate接口支持setmeal/coupon模拟核销 |  |
| [PAPI-2671](https://dragonpass.atlassian.net/browse/PAPI-2671) | 2026-04-24 | 故事 | Ready for PM Validation | P2 | 【Aero Blue】payment status change callback |  |
| [PAPI-2667](https://dragonpass.atlassian.net/browse/PAPI-2667) | 2026-04-24 | 故事 | Ready for PM Validation | P2 | membership preview/prebooking创单接口逻辑调整 | ✓ |
| [PAPI-2664](https://dragonpass.atlassian.net/browse/PAPI-2664) | 2026-04-22 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】收据获取接口 |  |
| [PAPI-2657](https://dragonpass.atlassian.net/browse/PAPI-2657) | 2026-04-20 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】Preview接口修改usedEntitlementDetails为非必传 | ✓ |
| [PAPI-2653](https://dragonpass.atlassian.net/browse/PAPI-2653) | 2026-04-20 | 故事 | Ready for QA Testing | P2 | SAAS 权限组支持双key切换 |  |
| [PAPI-2644](https://dragonpass.atlassian.net/browse/PAPI-2644) | 2026-04-16 | 故事 | READY FOR GO LIVE | P2 | project level 资源更新和站点更新推送 | ✓ |
| [PAPI-2640](https://dragonpass.atlassian.net/browse/PAPI-2640) | 2026-04-16 | 故事 | 已完成 | P2 | 修复epass-bundle，bundle-epass，同一clientUserId注册失败问题 | ✓ |
| [PAPI-2636](https://dragonpass.atlassian.net/browse/PAPI-2636) | 2026-04-16 | 故事 | Ready for QA Testing | P2 | Retrieve Project Resources List 和 Retrieve Project Transport Hub List，支持通过id进行资源过滤 | ✓ |
| [PAPI-2631](https://dragonpass.atlassian.net/browse/PAPI-2631) | 2026-04-16 | 故事 | 已完成 | P2 | 【BOSS】批量获取local offer资源接口 |  |
| [PAPI-2627](https://dragonpass.atlassian.net/browse/PAPI-2627) | 2026-04-15 | 故事 | 已完成 | P2 | 【运维】BTG prod 证书配置 |  |
| [PAPI-2624](https://dragonpass.atlassian.net/browse/PAPI-2624) | 2026-04-14 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】资源聚合与机场聚合逻辑调整 |  |
| [PAPI-2620](https://dragonpass.atlassian.net/browse/PAPI-2620) | 2026-04-14 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】/v2/programs/resources/batch 接口，新增program是否可预约属性 |  |
| [PAPI-2616](https://dragonpass.atlassian.net/browse/PAPI-2616) | 2026-04-14 | 故事 | READY FOR GO LIVE | P2 | 资源检索内存机制优化｜Resource retrieval mechanism optimization |  |
| [PAPI-2614](https://dragonpass.atlassian.net/browse/PAPI-2614) | 2026-04-14 | 长篇故事 | Business Requirement Collection | P2 | 26'Q2 Roadmap - Local Offer |  |
| [PAPI-2608](https://dragonpass.atlassian.net/browse/PAPI-2608) | 2026-04-14 | 故事 | READY FOR GO LIVE | P2 | Local Offer 资源查询部分 |  |
| [PAPI-2598](https://dragonpass.atlassian.net/browse/PAPI-2598) | 2026-04-11 | 故事 | READY FOR GO LIVE | P2 | 【Aero Blue】SAAS H5订单要写入ProgramId |  |
| [PAPI-2594](https://dragonpass.atlassian.net/browse/PAPI-2594) | 2026-04-11 | 故事 | 已取消 | P2 | 【Aero Blue】新增membership.updated event 待定 |  |
| [PAPI-2590](https://dragonpass.atlassian.net/browse/PAPI-2590) | 2026-04-11 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】新增prebooking.created event | ✓ |
| [PAPI-2584](https://dragonpass.atlassian.net/browse/PAPI-2584) | 2026-04-09 | 故事 | Ready for QA Testing | P2 | 【Aero Blue】多语言逻辑调整，支持es-419 |  |
| [PAPI-2576](https://dragonpass.atlassian.net/browse/PAPI-2576) | 2026-04-09 | 故事 | Ready for PM Validation | P2 | 【Aero Blue】Lounge+FT订单流支持AB5月版本 | ✓ |
| [PAPI-2572](https://dragonpass.atlassian.net/browse/PAPI-2572) | 2026-04-09 | 故事 | READY FOR GO LIVE | P1 | 【Aero Blue】下单接口内部字段新增aeroblue支持（临时支持，后续需要去除） |  |
| [PAPI-2568](https://dragonpass.atlassian.net/browse/PAPI-2568) | 2026-04-09 | 故事 | READY FOR GO LIVE | P1 | 【Aero Blue】修改注册新增字段到saas真实字段、支持clientUserId重复注册 | ✓ |
| [PAPI-2553](https://dragonpass.atlassian.net/browse/PAPI-2553) | 2026-04-07 | 故事 | Ready for QA Testing | P1 | 【Aero Blue】批量获取项目可用资源/站点数据 | ✓ |
| [PAPI-2551](https://dragonpass.atlassian.net/browse/PAPI-2551) | 2026-04-03 | 长篇故事 | Business Requirement Collection | P2 | Aero Blue - DP API |  |
| [PAPI-2548](https://dragonpass.atlassian.net/browse/PAPI-2548) | 2026-04-03 | 故事 | 待办 | P2 | 【Aero Blue】 membership注册接口，新增内部字段，用于接收项目非标信息｜Added internal field for receiving non-standard project information on membership registration and query API | ✓ |
| [PAPI-2541](https://dragonpass.atlassian.net/browse/PAPI-2541) | 2026-04-02 | 故事 | 已完成 | P2 | 语种支持新增韩语ko-KR |  |
| [PAPI-2537](https://dragonpass.atlassian.net/browse/PAPI-2537) | 2026-04-01 | 故事 | 已完成 | P2 | 【BOSS】基础 - BOSS项目配置读/写接口 |  |
| [PAPI-2534](https://dragonpass.atlassian.net/browse/PAPI-2534) | 2026-04-01 | 故事 | 已完成 | P2 | 【SAAS】SOSS项目配置读/写接口 |  |
| [PAPI-2531](https://dragonpass.atlassian.net/browse/PAPI-2531) | 2026-04-01 | 故事 | 已完成 | P2 | 【BOSS】生消 - BOSS项目配置读/写接口 |  |
| [PAPI-2528](https://dragonpass.atlassian.net/browse/PAPI-2528) | 2026-04-01 | 故事 | 已完成 | P2 | 【BOSS】机高 - BOSS项目配置读/写接口 |  |
| [PAPI-2527](https://dragonpass.atlassian.net/browse/PAPI-2527) | 2026-04-01 | 长篇故事 | Business Requirement Collection | P2 | Project Nexus 自动化上线支持 |  |
| [PAPI-2526](https://dragonpass.atlassian.net/browse/PAPI-2526) | 2026-03-30 | 长篇故事 | Business Requirement Collection | P2 | 26'Q2 Roadmap - Minor Enhancement |  |
| [PAPI-2523](https://dragonpass.atlassian.net/browse/PAPI-2523) | 2026-03-27 | 故事 | 已完成 | P2 | 【SAAS】统一域名下多服务路由扩展（支持 AI / 大数据服务接入） |  |
| [PAPI-2519](https://dragonpass.atlassian.net/browse/PAPI-2519) | 2026-03-26 | 故事 | 已完成 | P2 | 优化crossModuleEntitlement/moduleExclusiveEntitlements没数据的返回，修改回[] | ✓ |
| [PAPI-2515](https://dragonpass.atlassian.net/browse/PAPI-2515) | 2026-03-26 | 故事 | 已完成 | P2 | 优化swap品类权益在注册/查询/update接口的返回结构 | ✓ |
| [PAPI-2512](https://dragonpass.atlassian.net/browse/PAPI-2512) | 2026-03-24 | 计划 | 已完成 | P2 | 26'Q1 SP5 - 安全测试 |  |
| [PAPI-2505](https://dragonpass.atlassian.net/browse/PAPI-2505) | 2026-03-24 | 故事 | 已完成 | P2 | 优化bunlde订单判断逻辑 |  |
| [PAPI-2501](https://dragonpass.atlassian.net/browse/PAPI-2501) | 2026-03-23 | 故事 | 已完成 | P2 | 优化zh-CN和zh-HK下的港澳台机场数据冗余问题 | ✓ |
| [PAPI-2497](https://dragonpass.atlassian.net/browse/PAPI-2497) | 2026-03-23 | 故事 | 已完成 | P2 | 优化价格为空的告警逻辑 | ✓ |
| [PAPI-2488](https://dragonpass.atlassian.net/browse/PAPI-2488) | 2026-03-20 | 故事 | 待办 | P2 | 【边缘异常】walkin场景下SAAS创单成功，核销超时订单处理逻辑 |  |
| [PAPI-2475](https://dragonpass.atlassian.net/browse/PAPI-2475) | 2026-03-18 | 故事 | 已完成 | P2 | 【运维】BTG sandbox 证书配置 |  |
| [PAPI-2467](https://dragonpass.atlassian.net/browse/PAPI-2467) | 2026-03-16 | 故事 | 已完成 | P2 | 预览订单、创建订单、订单详情新增usedEntitlementBreakdown array | ✓ |
| [PAPI-2456](https://dragonpass.atlassian.net/browse/PAPI-2456) | 2026-03-13 | 故事 | 待办 | P2 | 支持在uat模拟测试预订单的pending status |  |
| [PAPI-2452](https://dragonpass.atlassian.net/browse/PAPI-2452) | 2026-03-13 | 故事 | 已取消 | P2 | 【SAAS】会籍升降级支持 |  |
| [PAPI-2448](https://dragonpass.atlassian.net/browse/PAPI-2448) | 2026-03-12 | 故事 | 已取消 | P2 | Enhance the dynamic QR code feature to support one-time-use QR codes｜优化动态二维码逻辑，支持一次性二维码 |  |
| [PAPI-2440](https://dragonpass.atlassian.net/browse/PAPI-2440) | 2026-03-10 | 故事 | 已取消 | P2 | 运营Onboarding提效 |  |
| [PAPI-2424](https://dragonpass.atlassian.net/browse/PAPI-2424) | 2026-03-06 | 故事 | 已完成 | P2 | /ePasses/details判断到MS订单给提示语【V1+V2】 | ✓ |

## 长篇故事 / Epic（5 条）

- [PAPI-2761](https://dragonpass.atlassian.net/browse/PAPI-2761) 2026-05-26 — 26'Q2 Roadmap - support h5 cashier in FT/Lounge Order flow
- [PAPI-2614](https://dragonpass.atlassian.net/browse/PAPI-2614) 2026-04-14 — 26'Q2 Roadmap - Local Offer
- [PAPI-2551](https://dragonpass.atlassian.net/browse/PAPI-2551) 2026-04-03 — Aero Blue - DP API
- [PAPI-2527](https://dragonpass.atlassian.net/browse/PAPI-2527) 2026-04-01 — Project Nexus 自动化上线支持
- [PAPI-2526](https://dragonpass.atlassian.net/browse/PAPI-2526) 2026-03-30 — 26'Q2 Roadmap - Minor Enhancement
- [PAPI-2512](https://dragonpass.atlassian.net/browse/PAPI-2512) 2026-03-24 — 26'Q1 SP5 - 安全测试
