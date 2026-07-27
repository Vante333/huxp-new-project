# Membership Purchase P0 · Apifox CLI Repo-first

首次会籍商品购买 **P0 冒烟**（开发冒烟）。

## 场景目录

`membership` / `P0(冒烟用例)` / `others`（folderId **350026**）

## 已创建资源

| 项 | 值 |
|----|-----|
| 场景 | **366587** · `Membership Purchase P0 · CLI sync` |
| 分支 | `ai/apifox-cli-sync` |
| 环境 | **351893**（UAT canary，含可用 `baseUrl`） |
| 生成器 | `generators/GeneratePostmanCollectionMembershipPurchaseP0.py` |

## 覆盖

两条 E2E，步骤序：

`Preview → Create → Details → Payments → Details`

| 一级分组 | 要点 |
|----------|------|
| 商品B-无券-原价EUR | `autoRenewal=false`，默认商品 B，15 EUR |
| 商品A-传券-订阅引导期USD | `CouponIntroValid` + `autoRenewal=true`，应付 0；Payments 期望业务失败 |

## 本机鉴权（.env，勿提交）

```text
MP_P0_PROGRAM_ID=...
MP_P0_CLIENT_ID=...
MP_P0_SECRET=...
```

生成时注入 Auth body / `X-Program-ID`；业务期望见生成器 `DEFAULT_BUSINESS_ENV`。

## 命令

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset membership_purchase_p0
```

## 当前阻塞（2026-07-27）

curl 实测：同 Program 换 token **成功**；`POST /v2/memberships/search` 能过鉴权；但

`POST /v2/orders/memberships/purchase/preview` 固定返回：

`code=-1` · `errCode=201.000.001` · `Authentication failed: invalid secret provided.`

→ 属 **网关/Program 对首次会籍购买接口的授权或发布** 问题，不是脚本未取 token。需业务侧确认 Retail Program `2032786406298624` 是否已开通 purchase 能力、路由是否打到正确环境。
