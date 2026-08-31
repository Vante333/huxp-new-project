# Membership Purchase P1 · Apifox CLI Repo-first

首次会籍商品购买 **P1 全量**（在 P0 冒烟上扩展字段级用例）。

## 场景目录

`common` / `P1（全量用例）` / `prebooking`（folderId **350046**；与 suites.yaml 一致）

## 已创建资源

| 项 | 值 |
|----|-----|
| 场景 | **366626** · `Membership Purchase P1 · CLI sync` |
| 分支 | `ai/apifox-cli-sync` |
| 环境 | **351893**（与 P0 共用） |
| 生成器 | `generators/GeneratePostmanCollectionMembershipPurchaseP1.py` |
| 资产 key | `membership_purchase_p1` |

## 覆盖

### 正向 E2E

`Preview → Create → 取消订阅 → Details → Payments → Details → Cancel → Details`（再次取链 / 仅 email 为子集）

| 分组 | 要点 |
|------|------|
| 默认项目配置中的首个商品-无券-原价 | P0 冒烟 |
| 商品A-传券-引导期 | P0；应付 0 → Payments 业务失败；**Create status=9**；**activationMethod=1**（dpid+激活码） |
| 商品A-引导期未开 | `productANoIntroPayableAmount`（通常=`productAPrice`）；**activationMethod=2**（兑换码） |
| 仅 email 成单 | 无 clientUserId |
| 再次取链 | Payments ×2，url/validUntil 变化 |

### 负向

| 分组 | 要点 |
|------|------|
| 无订阅 · autoRenewal=false | Preview 按 A 原价（`coupon.valid=false`、`details.currency=null`）；Create **500.020.031** |
| 订阅关 · autoRenewal=false | Preview 按 A 原价（`coupon.valid=false`、`details.currency=null`）；Create **500.020.031** |
| B/A autoRenewal=true、无效券等 | Preview/Create 券与 autoRenewal |
| Preview 字段校验 | 必填缺失/null（含 email）；类型错误；email 必填且 clientUserId 选填 |
| Create 字段校验 | 必填缺失/null（含 email）；类型错误；email 负向三组 |
| 取消订阅字段校验 | 必填缺失/null（membershipId/email）；类型/16位/邮箱格式；与 Create 注册不一致 → **500.020.035** |
| Details 字段校验 | orderId：`{}` / null / number / 空串 |
| Payments | 缺 orderId |

### 排除（本批）

callback、支付成功 activation、已支付取消退款、下游 5xx、探索边界、分级告警。

## 鉴权与环境

与 P0 相同：

```text
MP_P0_PROGRAM_ID=...
MP_P0_CLIENT_ID=...
MP_P0_SECRET=...
```

P1 业务键见生成器 `MERGED_BUSINESS_ENV` / 场景 description；**换测只改「全量数据」选行**，勿再写 Environment 业务键。  
Environment 351893 **仅保留** `baseUrl` / `x-version`（共用环境勿整表删）。

**场景×变量 / Apifox 数据集**：

`api-testcases/api_tests/apifox-cli/datasets/membership_purchase_p1/`

| 文件 | 用途 |
|------|------|
| **`apifox-dataset-business-ascii.csv`** | 导入「全量数据」，编码选 **UTF-8**（界面无 GBK 时用这个；全文 ASCII） |
| `scenario-env-matrix.csv` | Excel 对照（勿当数据集） |

导入后勾选行：`_FULL_SUITE`=全量；`pos_*`/`neg_*`=单场景数据。鉴权仍用 `MP_P0_*`。详见同目录 `README.md`。

**跑 Group 看填写指南（控制台）**：首步 Pre-request/Tests 只 `console.log` 短行（键=当前值 // 短含义）；标题为「要改的数据集列」。未开引导期默认只提示 `productANoIntroPayableAmount`（通常=`productAPrice`）。

## 命令

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionMembershipPurchaseP1.py
.\scripts\ApifoxRepoFirst.ps1 -Action PushSteps -Asset membership_purchase_p1
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset membership_purchase_p1
```

## 字段级追溯

`testcases/2026Q3_SP1/首次会籍商品购买API-字段级测试用例-001.md`（已确认 errCode 映射与 0 元 status=9）。
