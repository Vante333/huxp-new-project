# Postman / Apifox 导入

与 [Apifox：导入 Postman](https://docs.apifox.com/doc-5174528) 一致：使用 **Postman Collection v2.1** 的 JSON；`baseUrl` 等变量在 Postman 中由集合或环境提供，导入 Apifox 后对应到项目/环境中的「服务 / 前置 URL」与变量。

## 目录（按角色）

```text
postman/
  generators/   # 正本：Generate*.py、collection_builder_common.py
  collections/  # 可审：*.postman_collection.json（提交）
  envs/         # 环境模板
  docs/         # 协作说明 / 试点详解
  generated/    # 本地中间件（gitignore；可丢）
  README.md     # 本索引
```

约定：**正本唯一真相** → 只改 `generators/`；PR 审 `collections/`；CLI/本地 Apifox 包走 `apifox-reports/<asset>/generated/` 或本目录 `generated/`。

新人入门：[`docs/Apifox-CLI-小白入门流程.md`](docs/Apifox-CLI-小白入门流程.md)  
团队协作：[`docs/Apifox-CLI-Repo-First-协作指南.md`](docs/Apifox-CLI-Repo-First-协作指南.md)（**§15 团队推广**）  
Agent 规范：[Skill `apifox-cli-repo-first`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)（E2E 先确认 / 对照表 / 不清先问）

## 常用文件

| 文件 | 用途 |
|------|------|
| [`collections/PAPI-2548-membership-extensions.postman_collection.json`](collections/PAPI-2548-membership-extensions.postman_collection.json) | **主文件**：Postman / Apifox → **Import**。对齐 [`tests/features/test_membership_extensions.py`](../tests/features/test_membership_extensions.py)。 |
| [`generators/GeneratePostmanCollectionPapi2548.py`](generators/GeneratePostmanCollectionPapi2548.py) | **生成器**：`python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionPapi2548.py` |
| [`docs/Apifox-CLI-小白入门流程.md`](docs/Apifox-CLI-小白入门流程.md) | 小白入门 |
| [`docs/Apifox-CLI-Repo-First-协作指南.md`](docs/Apifox-CLI-Repo-First-协作指南.md) | Repo-first 协作 |
| [`docs/Apifox-CLI-Repo-First-问题回顾.md`](docs/Apifox-CLI-Repo-First-问题回顾.md) | 问题回顾 |
| [`docs/PAPI-2548-apifox-cli-repo-first.md`](docs/PAPI-2548-apifox-cli-repo-first.md) | 2548 CLI 试点；入口 [`scripts/ApifoxRepoFirst.ps1`](../../../scripts/ApifoxRepoFirst.ps1) |
| [Skill `apifox-cli-repo-first`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md) | Agent 硬约束 + [`catalog.md`](../../../.cursor/skills/apifox-cli-repo-first/catalog.md) |
| `apifox-reports/papi_2548/generated/*.apifox-2.7.43-import.json` | **CLI 临时包**（gitignore） |
| [`collections/PAPI-2515-cross-module-entitlements.postman_collection.json`](collections/PAPI-2515-cross-module-entitlements.postman_collection.json) | PAPI-2515 集合 |
| [`generators/GeneratePostmanCollectionPapi2515.py`](generators/GeneratePostmanCollectionPapi2515.py) | PAPI-2515 生成器 |
| [`collections/LocalOffer-ePass-P0-e2e-core.postman_collection.json`](collections/LocalOffer-ePass-P0-e2e-core.postman_collection.json) | Local Offer P0 |
| [`envs/LocalOffer-ePass-sandbox.postman_environment.json`](envs/LocalOffer-ePass-sandbox.postman_environment.json) | Local Offer 环境 |
| [`collections/LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json`](collections/LocalOffer-ePass-P1-e2e-pytest-sync.postman_collection.json) | Local Offer P1 |
| [`generators/GeneratePostmanCollectionLocalOfferEpass.py`](generators/GeneratePostmanCollectionLocalOfferEpass.py) | 写出 P1；Apifox 包装进 `generated/` |
| [`generators/GeneratePostmanCollectionLocalOfferEpassFull.py`](generators/GeneratePostmanCollectionLocalOfferEpassFull.py) | Full 集合 |
| [`docs/LocalOffer-ePass-P1-apifox-export-from-pytest.md`](docs/LocalOffer-ePass-P1-apifox-export-from-pytest.md) | P1 步骤索引 |
| [`collections/Esim-ePass-P0-e2e-core.postman_collection.json`](collections/Esim-ePass-P0-e2e-core.postman_collection.json) | eSIM P0 |
| [`generators/GeneratePostmanCollectionEsimEpass.py`](generators/GeneratePostmanCollectionEsimEpass.py) | eSIM 生成器 |

重新生成示例：

```powershell
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionPapi2548.py
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpass.py
python api-testcases/api_tests/postman/generators/GeneratePostmanCollectionLocalOfferEpassFull.py
```

Repo-first 验收：

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548
```

其余品类（fitness / lounge / fastTrack / PAPI-2722 / PAPI-2839 / Resource Details 等）生成器均在 `generators/`，集合在 `collections/`，命令形如：

```powershell
python api-testcases/api_tests/postman/generators/GeneratePostmanCollection<Name>.py
```

变量与 `DP_*` 映射、导入注意点见各集合 description 与 [`docs/`](docs/)。
