# Postman / Apifox：测试目的前置命名

配合主 Skill [SKILL.md](./SKILL.md) 中 **Postman** 小节使用。Local Offer 已落地；**新建或扩展任意** `GeneratePostmanCollection*.py` 时默认遵循本规范。

## 原则

Apifox/Postman 列表里 **先让人看懂「这一步在验证什么」**，再看到步骤号与 HTTP。  
**禁止** 仅用 `S02 POST prebooking（无效 token）` 这类「动作在前、目的在后」的命名。

## 展示名格式（唯一标准）

```text
【测试目的（中文）】| 步骤ID | METHOD /path简写
```

| 字段 | 规则 |
|------|------|
| 测试目的 | 一句话业务语义；正向/负向写清；与 pytest / 用例表意图一致 |
| 步骤ID | E2E：`E01-S01`；分模块：`S01`；鉴权：`Auth` |
| path 简写 | 关键路径段即可，如 `/localOffers/ePasses`、`/ePasses/prebooking` |

### 示例

| 避免 | 推荐 |
|------|------|
| `S02 POST prebooking（无效 token）` | `【负向：无效 prebookingToken 预约】\| S02 \| POST /ePasses/prebooking` |
| `E02-S03 POST /v2/orders/.../prebooking` | `【预约下单成功（usage 单）】\| E02-S03 \| POST /ePasses/prebooking` |
| `S01 POST create（31 个 resourceIds）` | `【负向：resourceIds 超过 30 条】\| S01 \| POST /localOffers/ePasses` |

### 目的文案模板

- 正向：`创建 ePass`、`可用性取 token`、`预约下单成功`、`取消 MS 购买单`
- 负向：`负向：无效 prebookingToken 预约`、`负向：复用已消费 token`
- 说明：`说明：请用 pytest 跑完整场景`、`说明：SaaS 人工核对权益`

## 生成器实现（Agent 必做）

### 1. 公共函数 `PurposeName`

在需求生成器（或共享模块）中定义，**Local Offer 参考**：

[`GeneratePostmanCollectionLocalOfferEpass.py`](../../../api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpass.py)：

```python
def PurposeName(purpose: str, step_id: str, method: str, path_hint: str = "") -> str:
    hint = (path_hint or "").strip()
    if hint:
        return f"【{purpose}】| {step_id} | {method} {hint}"
    return f"【{purpose}】| {step_id} | {method}"
```

### 2. 写入 `RequestItem.name`

P1 / 单文件 E2E 形态：

```python
lo.RequestItem(
    name=PurposeName("创建 Local Offer ePass（MS 购买单）", "E01-S01", "POST", "/localOffers/ePasses"),
    ...
)
```

### 3. Full / 多模块形态：`StepSpec` + `purpose`

[`GeneratePostmanCollectionLocalOfferEpassFull.py`](../../../api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpassFull.py)：

```python
@dataclass
class StepSpec:
    purpose: str      # 必填
    step_id: str
    method: str
    url_path: str
    path_hint: str = ""
    ...

def _DisplayName(spec: StepSpec) -> str:
    return lo.PurposeName(spec.purpose, spec.step_id, spec.method, spec.path_hint or ...)
```

封装步骤 **必须** 带 `purpose=`：

```python
_CreateEpassStep("S01", purpose="创建 ePass", payload=...)
_AvailabilityStep("S02", purpose="可用性取 token", with_epass=True)
_PrebookStep("S03", purpose="负向：零权益不可预约", expect_success=False)
```

内联步骤：

```python
StepSpec(
    purpose="负向：不存在 orderId search",
    step_id="S01",
    method="POST",
    url_path="/v2/orders/ePasses/search",
    path_hint="/ePasses/search",
    ...
)
```

### 4. 禁止占位步误用鉴权 URL

说明类 /「仅 pytest」步骤：**不要** `GET /v2/auth/token` 当占位（易 405）。用合法 `GET /v2/resources?module=…` + `loManualPytestOnly`，或合并到上一步后置脚本。

## 导出命令（仓库根，PowerShell）

```powershell
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpass.py
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpassFull.py
```

其他需求：`python api-testcases/api_tests/postman/generators/GeneratePostmanCollection<需求>.py`

改生成器后 **必须** 运行脚本重写 `*.postman_collection.json`，再让使用者 **重新导入** Apifox（勿沿用旧集合缓存）。

## Local Offer 集合分层（勿混）

| 集合 | 维护方式 |
|------|----------|
| P0 E2E 核心 | **手工** Apifox/Postman，生成器 **不写入** |
| P1 (pytest-sync) | `GeneratePostmanCollectionLocalOfferEpass.py` |
| Full (pytest-sync) | `GeneratePostmanCollectionLocalOfferEpassFull.py` |

## Agent 自检清单

```
- [ ] 每个请求的 name 均以 【目的】 开头（非 Sxx POST … 旧格式）
- [ ] 新增/改步骤已补 purpose= 或 PurposeName(...)
- [ ] 负向步骤目的含「负向：」
- [ ] 已运行 GeneratePostmanCollection*.py 并提交更新后的 JSON
- [ ] postman/README.md 与 pytest 用例表仍可对齐
- [ ] 权威执行仍为 pytest + Allure；Postman 仅联调/共享
```

## 延伸阅读

- [`api-testcases/api_tests/postman/README.md`](../../../api-testcases/api_tests/postman/README.md) — 变量、导入、目的前置导出小节
- [`LocalOffer订单相关-epass-自动化用例与pytest对应表.md`](../../../testcases/2026Q2_SP3/LocalOffer订单相关-epass-自动化用例与pytest对应表.md) — 步骤语义对照
