# Local Offer ePass · Postman / Apifox 2.7.43 导入说明

客户端 **2.7.43** / 服务端 **2.7.59**（与 PAPI-2548 金样例同团队环境）。

## 主文件：Postman Collection v2.1（推荐）

**请使用 Postman 格式 JSON**（与 PAPI-2548 金样例相同）：

| 文件（均在 `postman/collections/`） | 说明 |
|------|------|
| **`LocalOffer-ePass-P1-e2e-core.postman_collection.json`** | 主文件（E01/E02/E03；E01 在 S05 后、取消 MS 前后各跑 module 隔离；35 个请求均带 Tests） |
| `LocalOffer-ePass-tc-P1-mainflow.postman_collection.json` | 与上相同（兼容旧名） |

### Apifox 2.7.43

**项目设置 → 导入数据 → Postman** → 选择 `*.postman_collection.json`（勿选 `*.apifox-2.7.43-import.json`）。

导入后在 **接口管理** 查看各接口 **后置操作**（`pm.test` 脚本）。要跑 **自动化测试场景** 时：新建场景 → **从接口测试用例导入** → **复制** → 断言选 **「成功」**（同 PAPI-2548）。

### Postman 桌面端

**Import** → 选择同一 `*.postman_collection.json` → Collection Runner 按文件夹顺序执行。

## 可选：Apifox 原生场景包（非 Postman 格式）

| 文件（`postman/generated/`，gitignore，需先跑生成器） | 导入入口 | 结果 |
|------|----------|------|
| `LocalOffer-ePass-P1-e2e-core.apifox-2.7.43-import.json` | **项目设置 → 导入 → Apifox** | 直接生成 **自动化测试场景**（无需手工搭场景） |

用 **Postman 入口** 导入 `*.apifox-2.7.43-import.json` 会报 **「数据格式不正确」**。

## 重新生成

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionLocalOfferEpass.py
```

## 环境变量（Postman / Apifox 通用）

`baseUrl`、`ProgramID`、`clientId`、`secret`、`x-version`、`resourceId`、`optionId`；`prebookingDate` 可留空（Auth 前置脚本 UTC+10 天 10:30）。E02 用 card_secret 网点；E03 Bundle 前改 `REDEMPTION_CODE_*` 对应 `resourceId`/`optionId`。

## 可选 A：Apifox 原生场景（非 Postman 格式）

1. **项目设置 → 导入 → Apifox** → `LocalOffer-ePass-P1-e2e-core.apifox-2.7.43-import.json`
2. **自动化测试** → 场景 `P1 E2E 核心` → 每步后置含 `pm.test`

## 链路

`00 Auth` → `E01 创建（含 module=8/11 列表隔离）` → `E02 预约` → `E03 Bundle`（与 `test_local_offer_epass.py` 三条 E2E 一致；隔离断言对齐 `test_retrieve.py` 中 `AssertLocalOfferNotReturnedWithEsimModuleFilter` / `AssertEsimNotReturnedWithLocalOfferModuleFilter`）。

对照：[`LocalOffer-ePass-P1-apifox-export-from-pytest.md`](LocalOffer-ePass-P1-apifox-export-from-pytest.md)
