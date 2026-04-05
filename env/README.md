# 环境变量目录（多 profile）

本目录用于按环境拆分**接口自动化等**所需的凭据，避免与根目录 `.env` 混在一处。

- **勿提交**真实值：`env/.env.sandbox`、`env/.env.uat` 等已在仓库 [`.gitignore`](../.gitignore) 中忽略。
- **可提交示例**：如 `env/.env.sandbox.example`、`env/.env.uat.example`（命名与团队约定一致即可），供复制为本地文件。
- **加载顺序**（运行 `api-testcases` 下 pytest 时）：先读仓库根目录 [`.env`](../.env)（不覆盖进程已有键），若设置 `DP_PROFILE`（仅 `a-zA-Z0-9_-`），再读 `env/.env.<profile>` 并**覆盖**其中出现的同名变量。详见 [api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md)「多环境」一节。
- **与 MCP 共用变量**：Apifox / MySQL MCP 等所需项见根目录 [`.env.example`](../.env.example)。
