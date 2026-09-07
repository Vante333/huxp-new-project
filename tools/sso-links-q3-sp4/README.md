# SSO 免登短链 — 全量自动化说明

对应：
- XMind：`需求测试用例.xmind` → 一、SSO免登短链
- 用例文档：`interface_cursor/testcases/2026Q3_SP4/SSO免登短链-接口测试用例.md`
- 接口：`POST /v2/sso/links`

## 一、文件清单

| 文件 | 用途 |
|------|------|
| **`PAPI-SSO免登短链-全量自动化.postman_collection.json`** | **导入这个（全量）** |
| `apifox_pre_sso_full.js` / `apifox_post_sso_full.js` | 全量前置/后置（已内联进集合） |
| `sso_languages_list.json` | ForEach 语种列表（29，不含 DEFAULT） |
| `PAPI-SSO免登短链-语种遍历-BOSS-API.postman_collection.json` | 仅语种遍历（旧包，可忽略） |
| `apifox_pre_sso_links.js` / `apifox_post_sso_links.js` | 语种专用脚本 |
| `build_full_collection.js` | 改脚本后执行 `node build_full_collection.js` 重建 |

## 二、导入与环境

1. Apifox → **导入数据** → **Postman** → 选  
   `PAPI-SSO免登短链-全量自动化.postman_collection.json`
2. 环境变量：

| 变量 | 必填 | 说明 |
|------|------|------|
| `baseUrl` | 是 | 如 `https://developer-sandbox.dragonpass.com/api` |
| `access_token` | 是 | 有效 JWT |
| `Program-ID` | 是 | 与 Token / 会籍同一套 |
| `sso_subject_type` | 是 | `MEMBERSHIP` |
| `sso_subject_id` | 是 | 合法会籍号 |
| `sso_orderId` | DETAIL 用 | 该会籍下真实订单 |
| `sso_orderId_other` | 越权用 | 其他会籍订单 |
| `sso_subject_id_missing` | 可选 | 默认脚本有占位 |
| `sso_returnUrl_ok` | 可选 | 合法回调 |
| `sso_returnUrl_bad` | 可选 | 外域探测 |

3. Header 与支付一样：`Bearer {{access_token}}`、`X-Program-ID: {{Program-ID}}`

## 三、集合目录（全量）

| 文件夹 | 覆盖用例 |
|--------|----------|
| 1.必填校验 | SSO-REQ-001～005（含 602） |
| 2.参数标准化 | SSO-STD-001～005、007～010 |
| 2b.语种轮询BOSS29 | SSO-STD-006 × 29 |
| 3.异常场景 | SSO-ERR-001～010 |
| 4.边界 | SSO-BND-001～002 |
| 5.短链一致性 | SSO-IDEMP 同参多次 |
| 6.手工半自动 | 打开短链 / 过期 / 分页 / 访客 |

## 四、ForEach 语种列表（也可单独挂）

```json
[
  "en-US","ja-JP","de-DE","es-ES","fr-FR","it-IT","pl-PL","pt-PT",
  "ru-RU","th-TH","uk-UA","vi-VN","pt-BR","ko-KR","zh-HK","zh-CN",
  "es-419","fr-CA","ar-SA","ro-RO","bs-BA","sr-SP","sr-ME","hr-HR",
  "nl-NL","el-GR","si-SI","he-IL","hu-HU"
]
```

## 五、怎么跑

- **接口管理**：导入后逐条发送，或整夹运行  
- **自动化测试**：添加步骤 → 导入接口 → 勾选本集合文件夹 → 运行  
- 跑完看：`sso_last_shortUrl`、`sso_idem_shortUrl`、控制台 `[sso-full]` 日志  

## 六、注意

1. 前置脚本会**重写 Body**，以 case 变量为准（不要只改界面 JSON 却不设 `pay_orderId` 那种空变量问题；这里用 `sso_subject_id` / `sso_orderId`）。  
2. 打开短链、分页、过期必须**手工**点 `sso_last_shortUrl`。  
3. `SSO-STD-005 language=zh-CN`：若 Program 不支持可改为失败后改 expect 或跳过。  
4. 短链一致性：若产品定义为「每次新链」，把 IDEMP 的 `idempotent_check` 预期改掉。  
