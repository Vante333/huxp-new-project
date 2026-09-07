# 需求参数对应核对 + 冒烟进度（禁止错乱）

用户原话：「需求里面接口要求的是对内容参数需要的对应的值是不是要求的值没有错乱现象」

核对时必须回答两件事：① 需求要的是字段上下游对应，不是照抄 Demo 示例码；② 本次实测值有没有把两套协议数据写进同一条成功请求。

讲解仍须细到点哪个接口、抄哪个返回字段。禁止只说「对得上」。

---

## 需求要的对应关系（不是照抄 BZ000409）

文档/截图里的 `BZ000409`、`BPN003606`、`E1276000001` 是 Demo 样例。TEST 环境才有死值：规则 `TM001303`、平台应用 `id=27`、认券 TEST 用 `TM001303`（不要用 UAT 的 `TM001216/1217`）。

| 需求步骤 | 必须对上的 | 对上才算没乱 |
|----------|------------|--------------|
| 1 创建协议 | 客户 + 合同 → 产出协议号 | `customerCode`、`contractCode` 同一客户 |
| 2 会籍券码 | 协议 + 客户 + 规则 → `projectSign` | `agreementCode` = 第 1 步刚建的 |
| 3 品类项目 | 协议 → 新建 Lounge/FT/eSIM 等 | `agreementCode` = 第 1 步；产出 `projectCode`/`projectId`；eSIM 还须 Form→BOSS 页签字段对上（见 [step3-esim-boss-field-check.md](step3-esim-boss-field-check.md)） |
| 5 绑租户 | 协议+客户一对挂到平台应用 | 一对匹配；`id=27` 不是租户卡片 1276，也不是 `tenantCode=1015` |
| 6 创建权益 | 客户 + 第 3 步项目 | `categoryProjectCode` 与 `projectId` 是同一条 Lounge（`IL`） |
| 7 会籍模板 | 协议 + 客户 + 第 2 步规则 + 第 6 步权益 | `projectMark`=`projectSign`；`equityIds`=第 6 步权益 |
| 8 权益商品 | 仅 Topup=Yes | 关联第 6 步权益编码 |
| 9 预约商品 | 协议 + Lounge 项目 | `agreementCode`、`projectId`、`BPN` 同一套；规格 `entryId` 属于该项目 |
| 10 续期 | 仅 Auto Renew | 关联第 7 步 `templateCode` |
| 11 Agent Portal | 租户 + 协议 + 渠道 | 与第 5 步租户、第 1 步协议一致 |

三个号不要混：租户卡片 **1276**（进 SAAS 页面）、平台应用 **id=27**（get/edit）、`tenantCode=1015`。

两套数据禁止混用：

| 套 | 协议 | projectSign | 预约商品示例 |
|----|------|-------------|--------------|
| 旧（Demo/已有） | `BZ000409` | `214` | `9460` |
| 新（本次新建） | `BZ000579` | `215` | `9468` |

---

## 2026-08-19 实测：有没有问题、测没测到需求要点

### 结论

- **已测步骤（1、2、5、6、7、9）主数据对齐**：客户全程 `DPC000547`；成功请求里用的是新协议 `BZ000579` 和 `projectSign=215`，没有把 `BZ000409`/`214` 写进这些成功 Body。
- **测到了需求要点里的「公网主链路」**：创建协议、配券码、绑租户（整表追加）、建权益并上架、建会籍（规则=券码标识、权益=上架后的 ID）、建预约商品并上架。
- **没测到的需求要点**：第 3 步「给本协议新建品类项目」、第 4 步 Standard FAQ&T&C、第 8 步 Topup 权益商品、第 10 步续期、第 11 步 Agent Portal、第 0 步 SF/客户合同同步接口。
- **最大缺口（和需求不完全一致，不是字段填反）**：第 3 步未测，第 6、9 步借用旧 Lounge `BPN003608`（该项目属于旧协议那套品类）。项目编码和 `projectId` 彼此是对的，但不是「`BZ000579` 自己新建的品类」。

### 已测步骤实际值（新套）

| 字段 | 实际值 | 有没有乱 |
|------|--------|----------|
| `customerCode` | `DPC000547` | 全程同一客户 |
| 第 1 步协议 | `BZ000579` | 对，不应照抄示例 `BZ000409` |
| 第 2 步 `agreementCode` / `ruleCode` / `projectSign` | `BZ000579` / `TM001303` / **`215`** | 对 |
| 第 5 步 `id` + 追加对 | `27`；`BZ000579`+`DPC000547` | 对；edit 带齐旧 3 条，未冲掉 |
| 第 6 步项目 | `BPN003608` + `pvhjgy7rr4pkye9pj7`，`IL`，`equityType=agent` | 这一对自身对；项目是借用的 |
| 第 6 步权益 | ID `12426`，编码 `E1276000010`，已上架 | 对 |
| 第 7 步 | 协议 `BZ000579`，`projectMark=215`，`uqiKey=TM001303+215`，`equityIds=["12426"]`，模板 `MST1276000007` | 对 |
| 第 9 步 | 协议 `BZ000579`，项目同上，`entryId=1485`，`exchangeType=3`，商品 `9468` 已上架 | 字段对上；项目仍是借用 |

### 测的过程中曾经乱过、已纠正（不要写成当前数据仍错）

| 曾经 | 正确 |
|------|------|
| `businessOwner=DP0312` | `international`（业务归属枚举；`businessMode` 才是 `b2b`） |
| 字段名 `operator` | `operater` |
| 创建协议 `/supplierCenter/supplier/base/agreement/add` | `/salesCenter/api/v1/agreement/add` |
| 租户接口用 `platform-token` 或只写 `Authorization: Bearer` | `/api/tenant/...` 必须 Header 名 **`tenant-token`**（进租户 1276 后的 UUID，无 Bearer） |
| `/api/platform/...` | Header 名 **`platform-token`**（停在租户选择页） |
| 会籍在权益未上架时发 | 先上架再绑；未上架报「选择权益不是上架状态」 |

### 进度对照（需求 0～11）

```
0  客户+合同          没测接口（复用）
1  创建协议            ✅
2  会籍券码            ✅
3  品类项目            ❌ VPN，复用 BPN003608
4  FAQ & T&C           ❌ VPN
5  绑租户              ✅
6  创建权益            ✅（含上架）
7  会籍模板            ✅
8  Topup 权益商品      ❌ 条件跳过（Topup=No）；接口没测
9  预约商品            ✅（含上架）
10 续期计划            ❌ 条件跳过
11 Agent Portal        ❌ 未测
```

第 8 步 ≠ 第 9 步。第 9 步已测不算 Topup 权益商品已测。

### TEST 环境注意（不要记成业务失败）

- `GET /api/tenant/reservation/product/getSkuInfo` 与 `GET /api/tenant/product/getSkuInfo` 在 TEST 均 404（未部署）。规格从已有预约商品 `getDetail` 抄（同项目 `BPN003608` 的 `entryId`）。
- 预约商品 add 缺 `entryId` / `productType=8` / `exchangeType=3` 时，可能返回「系统繁忙」而不是明确校验句。

### 报告里要对需求坦白的三句

1. 公网主链路（协议→券码→绑租户→权益→会籍→预约商品）已按新协议跑通，参数对应无 409/579 串套。  
2. 品类项目不是新协议创建的，FAQ/T&C 未测。  
3. Topup 权益商品、续期、Agent Portal、客户合同同步接口未测。
