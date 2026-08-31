# Apifox CLI · Repo-first（脚本正本）

接口自动化**单轨真相源**：改断言/步骤只改本目录 `generators/`，经 `.\scripts\ApifoxRepoFirst.ps1` 同步到 Apifox AI 分支场景（`customHttp` + 后置 Tests）。  
Collection 仍使用 **Postman Collection v2.1** JSON 作为中间格式（故生成器文件名保留 `GeneratePostmanCollection*`）。

**禁止**再以新增 pytest `test_*.py` 作为正式验收；pytest 冻结说明见 [`../docs/pytest-retirement-map.md`](../docs/pytest-retirement-map.md)。

## 目录（按角色）

```text
apifox-cli/
  generators/   # 正本：Generate*.py、*_common.py（域公共层，禁止反向 import 入口）
  collections/  # 可审：*.postman_collection.json（提交）
  envs/         # 环境模板
  datasets/     # 数据集选行 CSV / scenario-group-map
  docs/         # 协作说明 / 资产详解
  generated/    # 本地中间件（gitignore；可丢）
  README.md     # 本索引
```

约定：**正本唯一真相** → 只改 `generators/`；PR 审 `collections/`；CLI 临时包走 `apifox-reports/<asset>/generated/`（gitignore）。

新人入门：[`docs/Apifox-CLI-小白入门流程.md`](docs/Apifox-CLI-小白入门流程.md)  
团队协作：[`docs/Apifox-CLI-Repo-First-协作指南.md`](docs/Apifox-CLI-Repo-First-协作指南.md)（**§15 团队推广**）  
公共逻辑收敛（减 copy）：[`docs/公共逻辑收敛-落地方案.md`](docs/公共逻辑收敛-落地方案.md)  
Agent 规范：[Skill `apifox-cli-repo-first`](../../../.cursor/skills/apifox-cli-repo-first/SKILL.md)  
已落地资产：[catalog.md](../../../.cursor/skills/apifox-cli-repo-first/catalog.md)

## 验收（唯一主路径）

```powershell
# 可单独跑；正常 Generate 会自动执行
python tools/apifox-cli/LintGeneratorAntiPatterns.py
python tools/apifox-cli/LintSuitesYaml.py

# 离线生成 + Collection 校验（不访问 Apifox）
.\scripts\ApifoxRepoFirst.ps1 -Action Generate -Asset papi_2548

# 用户确认数据集 / Environment / CSV 后，才执行在线验收
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548 -ConfirmRun
```

分步：`Generate` / `PushSteps` / `Run`。映射见 [`.apifox/suites.yaml`](../../../.apifox/suites.yaml)。

公共模块变更先查影响范围；批量入口不提供 Run/SyncCheck：

```powershell
python tools/apifox-cli/MapGeneratorAssets.py --affected-by `
  api-testcases/api_tests/apifox-cli/generators/ft_prebooking_payment_common.py
.\scripts\ApifoxRepoFirstBatch.ps1 -Action Generate -Group payment
.\scripts\ApifoxRepoFirstBatch.ps1 -Action PushSteps -Group payment -DryRun
```

## 常用文件

| 文件 | 用途 |
|------|------|
| [`generators/collection_builder_common.py`](generators/collection_builder_common.py) | 全品类基础设施（PurposeName / GetVar / Capture） |
| [`generators/epass_cli_common.py`](generators/epass_cli_common.py) | E-pass 品类配置、创建 payload、主链 RequestSpec |
| [`generators/fasttrack_prebooking_common.py`](generators/fasttrack_prebooking_common.py) | FT 预约 / Payment / PAPI 共用 |
| [`generators/lounge_epass_common.py`](generators/lounge_epass_common.py) | Lounge P0 与 PAPI-2839 Lounge 共用 |
| [`generators/ft_prebooking_payment_common.py`](generators/ft_prebooking_payment_common.py) | 预预约 payment 8 套 |
| [`generators/GeneratePostmanCollectionPapi2548.py`](generators/GeneratePostmanCollectionPapi2548.py) | 金样例生成器 |
| [`collections/PAPI-2548-membership-extensions.postman_collection.json`](collections/PAPI-2548-membership-extensions.postman_collection.json) | 可审集合 |
| [`docs/PAPI-2548-apifox-cli-repo-first.md`](docs/PAPI-2548-apifox-cli-repo-first.md) | 2548 详解 |
| [`docs/Apifox-CLI-小白入门流程.md`](docs/Apifox-CLI-小白入门流程.md) | 小白入门 |
| [`docs/Apifox-CLI-Repo-First-协作指南.md`](docs/Apifox-CLI-Repo-First-协作指南.md) | 协作全流程 |

重新生成示例：

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollectionPapi2548.py
```

其余品类生成器均在 `generators/`，命令形如：

```powershell
python api-testcases/api_tests/apifox-cli/generators/GeneratePostmanCollection<Name>.py
```
