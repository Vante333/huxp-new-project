# Membership Purchase P0 · Apifox CLI Repo-first

首次会籍商品购买 **P0 冒烟**（从 P1 正向 E2E 抽取 3 Group）。

## 场景目录

`common` / `P0(冒烟用例)` / `prebooking`（folderId **350042**；与 suites.yaml 一致）

## 已创建资源

| 项 | 值 |
|----|-----|
| 场景 | **366587** · `Membership Purchase P0 · CLI sync` |
| 分支 | `ai/apifox-cli-sync` |
| 环境 | **351893**（UAT canary，仅 `baseUrl` / `x-version`） |
| 生成器 | `generators/GeneratePostmanCollectionMembershipPurchaseP0.py` |
| 资产 key | `membership_purchase_p0` |
| 数据集 | `datasets/membership_purchase_p0/` |

## 覆盖

三条 E2E，步骤序：

`Preview → Create → purchase/details → memberships/details(MS-DET) → Payments → Details → Cancel → Details`

| Group | scenario_key | 要点 |
|-------|--------------|------|
| 不传券选择默认项目配置中的首个商品并按首月原价预览(EUR) | `pos_b_no_coupon` | 无券 · `autoRenewal=false` |
| 【币种·已配置】商品A…开启引导期…activationMethod=1 | `pos_a_intro_currency_configured` | 传券 · AR=true · 币种入参 · Create status=9 · 0 元 Payments 可失败 |
| 【币种·已配置】商品A…未开启引导期…activationMethod=2 | `pos_a_no_intro_currency_configured` | 传券 · AR=true · `productANoIntroPayableAmount` |

## 本机鉴权（.env，勿提交）

```text
MP_P0_PROGRAM_ID=...
MP_P0_CLIENT_ID=...
MP_P0_SECRET=...
```

运行时优先勾选鉴权数据集行；未勾选回落 `.env`。业务期望走「全量数据」选行。

**数据集导入**：`apifox-dataset-business.csv`（UTF-8）；对照 `scenario-group-map.md`。详见同目录 `README.md`。

## 命令

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionMembershipPurchaseP0.py
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset membership_purchase_p0
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset membership_purchase_p0
```
