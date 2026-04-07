# 环境变量目录（多 profile）

本目录用于按环境拆分**接口自动化等**所需的凭据，避免与根目录 `.env` 混在一处。

- **勿提交**真实值：`env/.env.sandbox`、`env/.env.uat` 等已在仓库 [`.gitignore`](../.gitignore) 中忽略。
- **可提交示例**：如 `env/.env.sandbox.example`、`env/.env.uat.example`、`env/.env.canary.example`（开发者沙箱 + `x-version: canary`），供复制为本地文件。
- **加载顺序**（运行 `api-testcases` 下 pytest 时）：先读仓库根目录 [`.env`](../.env)（不覆盖进程已有键）；若此时 **`DP_PROFILE` 仍为空**，再读 **`env/.local_profile`** 首条非注释行作为 profile 名（可复制 [`.local_profile.example`](.local_profile.example) 为 `.local_profile`，例如写 `canary`，即可**不用每次**在 PowerShell 里执行 `$env:DP_PROFILE = "canary"`）；最后若 `DP_PROFILE` 合法（仅 `a-zA-Z0-9_-`），读 `env/.env.<profile>` 并**覆盖**其中同名变量。若 profile 为 **canary** 且未设置 `DP_X_VERSION`，套件会在加载层末尾默认 `DP_X_VERSION=canary`（请求头 `x-version: canary`）；非 canary profile 不会注入。详见 [api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md)「多环境」一节。
- **与 shell 显式变量的优先级**：已在终端或系统环境中设置 `DP_PROFILE` 时，**不会**用 `.local_profile` 覆盖；根目录 `.env` 里若已写 `DP_PROFILE=...`，同样优先生效。
- **与 MCP 共用变量**：Apifox / MySQL MCP 等所需项见根目录 [`.env.example`](../.env.example)。
