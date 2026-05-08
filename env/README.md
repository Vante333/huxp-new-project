# 环境变量目录（多 profile）

本目录用于按环境拆分**接口自动化等**所需的凭据，避免与根目录 `.env` 混在一处。

- **勿提交**真实值：`env/.env.sandbox`、`env/.env.uat` 等已在仓库 [`.gitignore`](../.gitignore) 中忽略。
- **可提交示例**：如 `env/.env.sandbox.example`、`env/.env.uat.example`、`env/.env.canary.example`（开发者沙箱 + `x-version: canary`），供复制为本地文件。
- **加载顺序**（运行 `api-testcases` 下 pytest 时）：先读仓库根目录 [`.env`](../.env)（不覆盖进程已有键）；若此时 **`DP_PROFILE` 仍为空**，再读 **`env/.local_profile`** 首条非注释行作为 profile 名（可复制 [`.local_profile.example`](.local_profile.example) 为 `.local_profile`，例如写 `canary`，即可**不用每次**在 PowerShell 里执行 `$env:DP_PROFILE = "canary"`）；最后若 `DP_PROFILE` 合法（仅 `a-zA-Z0-9_-`），读 `env/.env.<profile>` 并**覆盖**其中同名变量。若 profile 为 **canary** 且未设置 `DP_X_VERSION`，套件会在加载层末尾默认 `DP_X_VERSION=canary`（请求头 `x-version: canary`）；非 canary profile 不会注入。详见 [api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md)「多环境」一节。
- **与 shell 显式变量的优先级**：已在终端或系统环境中设置 `DP_PROFILE` 时，**不会**用 `.local_profile` 覆盖；根目录 `.env` 里若已写 `DP_PROFILE=...`，同样优先生效。
- **与 MCP 共用变量**：Apifox / MySQL MCP 等所需项见根目录 [`.env.example`](../.env.example)。

## 环境与 CSV 测试数据

从 `api-testcases/2026Q2_SP1` 开始，环境与业务测试数据拆成两层：

- `DP_PROFILE`：选择环境凭据与 baseUrl / client / secret。
- `DP_TEST_DATASET`：选择该环境目录下的一条 **CSV 测试数据**。

同一个 `env/.env.<profile>` 里需要维护多套 `PROGRAM_ID` / `CLIENT_ID` / `CLIENT_SECRET` 时，可用
`DP_CREDENTIAL_ALIAS` 做运行级选择。例如：

```dotenv
DP_CREDENTIAL_ALIAS=EPASS

DP_CORE_PROGRAM_ID=...
DP_CORE_CLIENT_ID=...
DP_CORE_CLIENT_SECRET=...

DP_EPASS_PROGRAM_ID=...
DP_EPASS_CLIENT_ID=...
DP_EPASS_CLIENT_SECRET=...
```

加载 profile 后，框架会把当前 alias 对应的三件套映射为标准
`DP_PROGRAM_ID` / `DP_CLIENT_ID` / `DP_CLIENT_SECRET`。不设置 `DP_CREDENTIAL_ALIAS` 时保持旧行为，继续直接读取标准 `DP_*` 三件套。

目录约定：

- `api-testcases/2026Q2_SP1/testdata/<profile>/membership_register.csv`
- `api-testcases/2026Q2_SP1/testdata/<profile>/p2515_dataset.csv`
- `api-testcases/2026Q2_SP1/testdata/<profile>/p2424_dataset.csv`

兼容规则：

- **未设置** `DP_TEST_DATASET`：优先读取各 CSV 的 `datasetKey=default` 行；若不存在则回退旧的 `DP_*` 变量和代码默认值。
- **已设置** `DP_TEST_DATASET`：优先读取同名行；若该 CSV 没有该行，则回退到该 CSV 的 `default` 行；若两者都不存在则抛出明确错误。

PowerShell 示例：

```powershell
$env:DP_PROFILE = "canary"
$env:DP_TEST_DATASET = "p2515-cross-write-a"
```
