# pytest 退役对照表（单轨 Apifox CLI）

> 约定：catalog 中已登记且曾 SyncCheck 的资产为**正式执行入口**。  
> `tests/` 仅在本表「可删」列确认后删除；**本轮不盲删**。

| 能力 / pytest 入口 | Apifox 资产 key | catalog 状态 | 建议 |
|--------------------|-----------------|--------------|------|
| ~~`tests/features/test_membership_extensions.py`~~ | `papi_2548` | 已落地 | **已删**（2026-08-12） |
| ~~`tests/contract/test_membership_extensions_normalize_parity.py`~~ | `papi_2548` | 已落地 | **已删**（2026-08-12）；parity 以生成器 JS 为准 |
| ~~`tests/features/test_cross_module_entitlements.py`~~ | `papi_2515` | 已落地 | **已删**（2026-08-12，用户确认 CLI 跑通）；**后续待调整**见下节 |
| ~~`tests/regression/test_epass_orders_ms_hint.py`~~ | `papi_2424` | 已落地 | **已删**（2026-08-12） |
| ~~`tests/features|smoke|contract/test_local_offers_options*.py`~~ | `local_offers_options` | 已落地 | **已删**（2026-08-12） |
| `tests/features/local_offer_epass/` + smoke | `local_offer_epass_p0` / `local_offer_epass_p1` | 已落地 | 冻结；P1 边界需对照 Full 集合后再删 |
| `tests/features/test_historical_epass_*` / regression | `fitness_epass_p0` / `esim_epass_p0`（lounge/fastTrack 历史 P0 场景已于 2026-08-22 从 Apifox 删除，改走 `lounge_*_payment_*` / `ft_epass_payment_*`） | 部分落地 | 冻结；按品类逐个确认后删 |
| （无独立 pytest）Payment P0/P1 | `ft_*_payment_*` / `lounge_*_payment_*` | 已落地 | 仅 CLI |
| （无独立 pytest）Membership Purchase | `membership_purchase_p0` / `p1` | 已落地 | 仅 CLI |
| （无独立 pytest）Resource / Transport scan | `resource_details_scan*` / `resource_is_bookable_scan` / `transport_hubs_scan` | 已落地 | 仅 CLI |
| （无独立 pytest）PAPI-2839 / 2722 | `papi_2839*` / `papi_2722*` | 已落地（2026-08-23 ePass / membership 分场景） | 仅 CLI |

## 待办（单轨后继续改）

| 资产 | 状态 | 说明 |
|------|------|------|
| `papi_2515` | **待调整** | pytest 已删；用户将再改生成器/场景（软断言、doc gap、探测 skip 等与 CLI 对齐）。改完后 Generate + PushSteps；Run/SyncCheck 须先问用户。 |

## 删除前检查清单

1. catalog 行存在且路径指向 `apifox-cli/generators/`。
2. 本机或 CI 曾对该 `asset_key` 跑通 `SyncCheck`（或至少 Generate + PushSteps）。
3. 无仅存在于 pytest、未写入生成器 Tests 的硬断言（尤其 2515 软断言 / doc gap）。
4. 更新本表状态为「已删」并去掉 `suites.yaml` 中对应 `pytest_e2e` 备注（可选）。

## 禁止

- 新增 `tests/**/test_*.py` 作为主验收路径。
- 为对齐 pytest 再维护一套与生成器冲突的断言。
