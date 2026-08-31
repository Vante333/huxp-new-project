# Transport Hubs Scan · Group ↔ 数据集

| Apifox 场景 Group | 说明 | 鉴权数据集 |
|---|---|---|
| 00 Auth | `POST /auth/token` | **3475756**（ProgramID / clientId / secret 选行） |
| P1 · Transport Hubs 站点扫描 | 26 语种静态分组：列表→详情 | 沿用 Auth 写入的 `accessToken` / `ProgramID` |

业务无额外数据集列（纯扫描）；换 Program 只改鉴权数据集选行。
