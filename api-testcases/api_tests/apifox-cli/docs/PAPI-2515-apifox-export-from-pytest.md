# PAPI-2515：从 `test_papi_2515_cross_module_entitlements.py` 导出 → Apifox 后置脚本

**权威执行**仍以本地 **pytest + Allure + `papi2515_helpers`** 为准；下文 JS 用于 Apifox/Postman **联调与演示**，与 Python 语义对齐但**不保证**覆盖软断言、skip 分支与全部边界。

## 1. 公共脚本（必贴）

将 [`GeneratePostmanCollectionPapi2515.py`](../generators/GeneratePostmanCollectionPapi2515.py) 中 **`BuildP2515JsHelpersLines()`** 的 `js = r"""..."""` 段（或从已导入的 Collection 任一节点的 Tests 顶部）复制到：

- Apifox：**项目设置 → 公共脚本 → 后置操作**，或  
- 某目录/集合下**父级接口**的「后置脚本」（子请求继承执行顺序以 Apifox 版本为准），或  
- 每个相关接口脚本**最顶部**。

导入方式与 Postman 一致时，也可继续用集合 **Tests**（见 [`PAPI-2515-cross-module-entitlements.postman_collection.json`](../collections/PAPI-2515-cross-module-entitlements.postman_collection.json)）。

### 集合变量（与 `DP_*` 对齐）

| 集合变量 | 含义 |
|----------|------|
| `DP_RELAX_SUMMARY_POOL_SUM` | 设为 `1` / `true` 时放宽 summary 与 pools 四指标聚合（缺键按 0、任池 `-1` 则该指标为 `-1`；对齐 `DP_P2515_RELAX_SUMMARY_POOL_SUM`） |
| `DP_P2515_SUMMARY_GUEST_KEY_ALLOWED` | 可选，默认 `allowedGuestsPerUsage` |
| `DP_P2515_SUMMARY_GUEST_KEY_MAX` | 可选，默认 `maxGuestsNextUse` |

多步用例需自行写入中间结果，例如 `p2515_norm_cross_baseline`、`p2515_json_after_update`、`p2515_cross_before_json` 等（见各节示例）。

---

## 2. pytest 用例 ↔ Apifox 步骤 ↔ 后置脚本片段

### `TestP2515SearchCrossModuleContract.test_search_cross_module_contract_with_probe_membership`

| 步骤 | 接口 | 说明 |
|------|------|------|
| 1 | `POST /v2/auth/token` | 取 token |
| 2 | `POST /v2/entitlements/search` | body：`membershipId` = 环境探测 ID（pytest：`DP_P2515_PROBE_MEMBERSHIP_ID`） |

**`entitlements/search` 后置脚本：**

```javascript
var json = pm.response.json();
pm.test("HTTP 200", function () {
  pm.response.to.have.status(200);
});
pm.test("业务成功", function () {
  pm.expect(p2515IsBusinessSuccess(json)).to.be.true;
});
var data = json && json.data;
var ent = p2515ExtractEntitlementsFromData(data);
var cross = p2515GetCrossModule(ent);
pm.test("存在 crossModuleEntitlements", function () {
  pm.expect(cross.length).to.be.above(0);
});
p2515AssertCrossModuleContract(pm, cross, { context: "PAPI-2515-probe" });
```

---

### `TestP2515CrossModuleE2E.test_e2e_register_search_module_update_pool_updates`

对应主编排 **`RunP2515MainE2EScenario`**，HTTP 顺序与 Postman 集合 **PAPI-2515** 文件夹一致（注册 → 多次 search → update → pool update → search…）。

| 步骤 | 建议断言 |
|------|-----------|
| `POST /v2/memberships` | 见下 **S01 注册** |
| `entitlements/search`（基线） | 契约 + `pm.collectionVariables.set("p2515_norm_cross_baseline", p2515NormalizeCrossString(cross));` |
| `entitlements/update` | 业务成功；可选 `pm.collectionVariables.set("p2515_json_after_update", pm.response.text());` |
| `entitlements/search`（module 后） | `p2515NormalizeCrossString(cross)` 与 `p2515_norm_cross_baseline` 一致（对齐 S04 cross 不变） |
| `entitlements/{poolId}/update` | 业务成功 |
| 两次收尾 `search` | 至少再跑 `p2515AssertCrossModuleContract`；**summary 与预期指标**（S06/S07）逻辑较繁，建议以 pytest 为准 |

**S01 `POST /v2/memberships` 后置脚本（对齐 `RunP2515CrossModuleAndModuleExclusiveFromInner`）：**

```javascript
var json = pm.response.json();
pm.test("HTTP 200", function () {
  pm.response.to.have.status(200);
});
pm.test("业务成功", function () {
  pm.expect(p2515IsBusinessSuccess(json)).to.be.true;
});
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
var me = p2515GetModuleExclusive(ent);
if (cross.length) {
  p2515AssertCrossModuleContract(pm, cross, { context: "PAPI-2515-S01" });
}
if (me.length) {
  p2515AssertModuleExclusiveDetailsContract(pm, me, "PAPI-2515-S01");
}
var mid = json && json.data && json.data.membershipId;
if (mid) pm.collectionVariables.set("membershipId", String(mid));
```

**基线 `entitlements/search` 额外写入变量：**

```javascript
var json = pm.response.json();
pm.test("业务成功", function () {
  pm.expect(p2515IsBusinessSuccess(json)).to.be.true;
});
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
p2515AssertCrossModuleContract(pm, cross, { context: "PAPI-2515-S02" });
pm.collectionVariables.set("p2515_norm_cross_baseline", p2515NormalizeCrossString(cross));
```

**module 更新后的 `entitlements/search`：**

```javascript
var json = pm.response.json();
pm.test("业务成功", function () {
  pm.expect(p2515IsBusinessSuccess(json)).to.be.true;
});
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
var base = pm.collectionVariables.get("p2515_norm_cross_baseline");
pm.test("S04：cross 归一化与基线一致", function () {
  pm.expect(p2515NormalizeCrossString(cross)).to.eql(base);
});
p2515AssertCrossModuleContract(pm, cross, { context: "PAPI-2515-S04" });
```

> **moduleExclusive 指标增量**（Python：`AssertModuleExclusiveMetricDelta`）依赖请求体中的 module/tier/quantity，Apifox 需按实际 body 手写 `pm.expect`，或只跑 pytest。

---

### `TestP2515DocGapCoverage.test_memberships_search_cross_aligns_with_entitlements_search`（tc-P1-MBR + tc-P2-MBR-001）

| 顺序 | 接口 |
|------|------|
| 1 | `POST /v2/memberships` |
| 2 | `POST /v2/entitlements/search` |
| 3 | `POST /v2/memberships/search` |

**步骤 2 末尾增加：**

```javascript
var json = pm.response.json();
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
p2515AssertCrossModuleContract(pm, cross, { context: "gap-entitlements-search" });
pm.collectionVariables.set(
  "p2515_norm_cross_es",
  p2515NormalizeCrossString(cross)
);
```

**步骤 3 末尾：**

```javascript
var json = pm.response.json();
pm.test("业务成功", function () {
  pm.expect(p2515IsBusinessSuccess(json)).to.be.true;
});
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
p2515AssertCrossModuleContract(pm, cross, { context: "gap-memberships-search" });
var nb = p2515NormalizeCrossString(cross);
var na = pm.collectionVariables.get("p2515_norm_cross_es");
pm.test("tc-P2-MBR-001：两路 search cross 归一化一致", function () {
  pm.expect(nb).to.eql(na);
});
```

---

### `TestP2515DocGapCoverage.test_search_tc_p1_gen_005_and_fictive_purchase_zero`

单次 `POST /v2/memberships` 后 `POST /v2/entitlements/search`，在后置脚本中：

```javascript
var json = pm.response.json();
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
pm.test("存在 cross", function () {
  pm.expect(cross.length).to.be.above(0);
});
p2515AssertSummaryGuestAggregateKeys(pm, cross, "PAPI-2515-tc-P1-GEN-002");
p2515AssertSingleRowPerApplicableModules(pm, cross, "PAPI-2515-tc-P1-GEN-005");
p2515AssertFictiveZeroPurchasedPool(pm, cross, "PAPI-2515-tc-P2-GEN-005");
```

若模板无「虚构买点池」，Python 会 **skip**；JS 侧该用例会 **失败**，需换 program 或接受仅跑 pytest。

---

### `TestP2515DocGapCoverage.test_search_tc_p2_gen_004_at_least_two_cross_groups`

在 `entitlements/search` 后置：

```javascript
var json = pm.response.json();
var ent = p2515ExtractEntitlementsFromData(json.data);
var cross = p2515GetCrossModule(ent);
pm.test("存在 cross", function () {
  pm.expect(cross.length).to.be.above(0);
});
p2515AssertAtLeastTwoDistinctCrossGroups(pm, cross, "PAPI-2515-tc-P2-GEN-004");
p2515AssertCrossModuleContract(pm, cross, { context: "PAPI-2515-tc-P2-GEN-004" });
```

不足两组时 pytest **skip**；JS 会失败。

---

### `TestP2515DocGapCoverage.test_update_tc_p2_gen_001_metrics_match_followup_search`

| 顺序 | 接口 |
|------|------|
| 1 | `entitlements/search`（基线） |
| 2 | `entitlements/update` |
| 3 | `entitlements/search` |

**步骤 2 后置：**

```javascript
pm.test("HTTP 200", function () {
  pm.response.to.have.status(200);
});
pm.collectionVariables.set("p2515_json_after_update", pm.response.text());
```

**步骤 3 后置：**

```javascript
var jsonB = pm.response.json();
var parsedA = {};
try {
  parsedA = JSON.parse(pm.collectionVariables.get("p2515_json_after_update") || "{}");
} catch (e) {
  parsedA = {};
}
p2515AssertCrossMetricsEqualBetweenResponses(
  pm,
  parsedA,
  jsonB,
  "PAPI-2515-tc-P2-GEN-001"
);
```

若 update 响应无 cross 可解析，pytest 会 **skip**；Apifox 需自行判断或忽略该用例。

---

### `TestP2515DocGapCoverage.test_update_tc_p2_gen_002_purchase_pool_zero_after_pool_update`

| 顺序 | 接口 |
|------|------|
| 1 | `entitlements/search` | 选池 |
| 2 | `entitlements/{poolId}/update` | body：`{"membershipId","purchasedQuantity":0}` |
| 3 | `entitlements/search` | 校验 |

**步骤 1 后置：**

```javascript
var json = pm.response.json();
var cross = p2515GetCrossModule(
  p2515ExtractEntitlementsFromData(json.data)
);
var pid = p2515FindFirstPurchasedPoolId(cross);
pm.test("存在 purchased>0 的买点池", function () {
  pm.expect(pid).to.be.ok;
});
if (pid) pm.collectionVariables.set("entitlementPoolId", pid);
```

**步骤 3 后置：**

```javascript
var json = pm.response.json();
var cross = p2515GetCrossModule(
  p2515ExtractEntitlementsFromData(json.data)
);
pm.test("tc-P2-GEN-002：归零后仍存在 purchased=0 买点池", function () {
  pm.expect(p2515HasFictiveZeroPurchasedPool(cross)).to.be.true;
});
```

若 program **禁止按池更新**（`500.030.024`），pytest 会 skip；Apifox 需单独处理业务码。

---

### `TestP2515PoolUpdateIsolation.test_pool_update_other_applicable_modules_unchanged`（tc-P3-GEN-001）

| 顺序 | 接口 |
|------|------|
| 1 | `entitlements/search`（更新前） | 保存 `cross_before` |
| 2 | `entitlements/{poolId}/update` | 单池 |
| 3 | `entitlements/search`（更新后） | 比对 |

**步骤 1 后置：**

```javascript
var json = pm.response.json();
var cross = p2515GetCrossModule(
  p2515ExtractEntitlementsFromData(json.data)
);
p2515AssertAtLeastTwoDistinctCrossGroups(pm, cross, "PAPI-2515-tc-P3-GEN-001-prep");
pm.collectionVariables.set("p2515_cross_before_json", JSON.stringify(cross));
```

手动或通过上一步响应解析出**被更新池所属组**的 `applicableModules`，计算键字符串并写入（与 Python `item.applicable_modules_key` 一致）：

```javascript
// 示例：已知被更新组 applicableModules 为 [1,2] 时
pm.collectionVariables.set("p2515_touched_am_key", "[1,2]");
```

（键格式须为 `JSON.stringify(p2515ApplicableModulesKey(…))`，与 `p2515ApplicableModulesKeyStr` 一致。）

**步骤 3 后置：**

```javascript
var json = pm.response.json();
var crossAfter = p2515GetCrossModule(
  p2515ExtractEntitlementsFromData(json.data)
);
var crossBefore = [];
try {
  crossBefore = JSON.parse(
    pm.collectionVariables.get("p2515_cross_before_json") || "[]"
  );
} catch (e) {
  crossBefore = [];
}
var touched = pm.collectionVariables.get("p2515_touched_am_key");
p2515AssertOtherGroupsNormalizedUnchanged(
  pm,
  crossBefore,
  crossAfter,
  touched,
  "PAPI-2515-tc-P3-GEN-001"
);
```

---

## 3. 维护约定

- 修改 **`papi2515_helpers`** 中断言语义时，同步改 **`GeneratePostmanCollectionPapi2515.py`** 内 `BuildP2515JsHelpersLines()` 与本表片段。
- 更完整的接口顺序可参考生成器 [`GeneratePostmanCollectionPapi2515.py`](../generators/GeneratePostmanCollectionPapi2515.py)。
