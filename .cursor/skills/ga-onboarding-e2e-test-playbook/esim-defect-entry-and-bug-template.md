# eSIM 对照：有问题项的入口、步骤、缺陷描述

用户要「只报有问题的、入口说清楚、提 bug 把描述写好」时用本文。已通过对项（48 小时、税率 0、PAYG/COF/Ingenico、第 8/10 步跳过）禁止再展开。对照未完成禁止报缺陷。

教的人必须写清：**打开哪个系统、哪个菜单、点哪一颗按钮**。禁止只说「去 Form / 去 BOSS 对一下」。

---

## 先抄执行页（三个问题共用）

入口：Onboarding **Review Detail**（已审核通过的那份，不要打开空白新建 Form）。

1. 打开 `https://onboarding-form-test.dragonpass.com.cn` → 进该单 Review（例：`OBT-20260821-003`）。
2. 滚到 **Operations to Execute after Approval**。
3. 抄：协议 `BZ…`、权益 `E…`、项目 `APN…`、会籍 `MST…`、第 9 步 Product Code、Program Name。

网络模板 **不在** Client Info 第一页。Form 侧入口见问题 1。

---

## 问题 1：Standard Network 写入的不是 Form 选中模板

**现象：** Form 选 `【Esim】DP APP Default Esim`，BOSS 模板基本信息是 `Esim | GA Default Esim Network`。显示名不同先对全称/编码；全称明显不是一条（APP Default vs GA Default）则报缺陷。

### Form 入口（取期望值）

网络下拉 **不在** Client Info（客户名称、渠道那一页）。

1. 打开 **该单 Review Detail**（已提交），不要新建一张空表。
2. 滚到 **Entitlement** → Module = **ESIM** 那张卡。
3. 再滚到 **Network & Price**。
4. 看 **Network Type = Standard Network** 下面已选中的模板全称。截图。

新建/编辑未提交的表：Client Info 填完 → **+ Add Entitlement** → 勾 **ESIM** → Entitlement 卡 → **Network & Price** → Standard Network 下拉。

BOSS「查看模板基础信息」在 Form **没有**，不要在 Form 找这个按钮。

### BOSS 入口（取实际值）

1. BOSS 销售中心 → 左侧 **项目查询**（不要先打开别的协议的项目配置）。
2. 项目编码填执行页 **`APN…`**（例 `APN00000736`）→ 搜索。
3. 点中 `【Esim】` + Program Name 那一行 → **查看** 或 **编辑**。不要点价格计划、权益购买配置。
4. 页签 **网络范围配置**。
5. 点模板旁 **「查看模板基础信息」**。
6. 抄 **模板名称**（+ 能看到的模板编码）。截图。不要点保存。

### 缺陷描述（可粘贴）

```text
【标题】eSIM Standard Network 未按 Form 选中模板写入 BOSS

【环境】TEST / Onboarding 单号：OBT-xxxxxxxx / 协议：BZxxxxxx / 项目：APNxxxxxx

【步骤】
1. Client Onboarding Form 的 eSIM Entitlement → Network & Price，Standard Network 选择「【Esim】DP APP Default Esim」并审核通过。
2. BOSS → 项目查询 → 项目编码 APNxxxxxx → 查看 → 网络范围配置 → 查看模板基础信息。

【期望】模板名称/编码与 Form 选中的「【Esim】DP APP Default Esim」为同一条。

【实际】模板名称为「Esim | GA Default Esim Network」（GA Default，不是 DP APP Default）。

【附件】Review 上 eSIM Network 已选项；BOSS 模板基本信息页。
```

编码相同、仅短名不同：不报本条。未点「查看模板基础信息」：不报本条。

---

## 问题 2：Entitlement Order Limit 关闭后 BOSS 仍有下单间隔

**现象：** Form 开关 **关**，BOSS 品类规则「权益下单间隔限制」为 **1 天**。

先问产品：关闭是否系统默认 1 天。产品说默认 → 记需求缺口，不报缺陷。产品说关闭应无限制 → 报缺陷。

### Form 入口

1. 该单 **Review Detail**（不要新建）。
2. Entitlement → **ESIM**。
3. **Entitlement Order Limit** 开关位置（在 Cancellation Rule 下面）。截图：关着、没有数字。

### BOSS 入口

1. 同问题 1：项目查询 `APN…` → 查看/编辑。
2. 页签 **品类规则**（不要网络、不要结算）。
3. 找 **使用规则 → 权益下单间隔限制**。截图。不要保存。

### 缺陷描述（产品确认应无限制后再贴）

```text
【标题】eSIM Entitlement Order Limit 关闭时 BOSS 仍写入下单间隔 1 天

【环境】TEST / 单号：OBT-xxxxxxxx / 项目：APNxxxxxx

【步骤】
1. Form eSIM Entitlement Order Limit = Off（未填间隔）。
2. BOSS 项目查询 APNxxxxxx → 查看 → 品类规则 → 使用规则。

【期望】Order Limit 关闭时，权益下单间隔限制为空或不限制。

【实际】权益下单间隔限制 = 1 天。

【附件】Review 上 Order Limit 关闭；BOSS 品类规则间隔截图。
```

不要和问题 1 合成一条缺陷。

---

## 问题 3：第 9 步核销商品 Product Code 为 0

**现象：** 执行页 Create Booking / Verification Product 绿勾，eSIM 行 Product Code = **`0`**。

### 执行页入口（取回显）

1. 该单 Review → 滚到 **第 9 步 Create Booking / Verification Product**。
2. 看 Module = **ESIM** 那一行的 Product Code、Related Category（`APN…`）。截图。

### SAAS 入口（取是否落库）

1. 登录 SAAS，租户必须能搜到本单会籍 `MST…`（例 `MST1015000027`）。编码是 `E1015…`/`MST1015…` 就进 1015 这一系，**不要进旧租户 1276**。
2. 左侧 **商品** → **核销商品**（不要预约商品、不要权益商品）。
3. 搜 Program Name（例 `ESIM-0821-A`）或项目编码 **`APN…`**。
4. 看：有没有行、商品编号、是否上架、关联项目是不是本单 `APN…`。截图。

### 判定与缺陷描述

- SAAS 有真实 `ISC…`（或非 0 编号）且已上架、项目是本单 `APN…`：本条过；执行页 `0` 可另开「回显为 0」轻缺陷或备注。
- SAAS 没有，或编号就是 `0`：报缺陷。

```text
【标题】eSIM 第 9 步核销商品执行成功但 Product Code 为 0 / SAAS 未落库

【环境】TEST / 单号：OBT-xxxxxxxx / 项目：APNxxxxxx / 会籍：MSTxxxxxx

【步骤】
1. Onboarding 审核通过，第 9 步 Create Booking/Verification Product 显示 Completed，ESIM 行 Related Category=APNxxxxxx，Product Code=0。
2. SAAS（能搜到 MSTxxxxxx 的租户）→ 商品 → 核销商品，按 APNxxxxxx 或 Program Name 查询。

【期望】生成核销商品，编号非 0，已上架，关联品类项目=APNxxxxxx。

【实际】执行页 Product Code=0；（无商品 / 编号为 0，以查询结果填写）。

【附件】第 9 步回显；SAAS 核销商品查询结果。
```

---

## 提缺陷时强制格式

每条必须有：标题、环境+单号+`APN`、步骤（含入口菜单）、期望、实际、附件。禁止只写「网络不对」「商品是 0」。问题 1、2、3 分开提。对照时不要在 BOSS/SAAS 点保存。
