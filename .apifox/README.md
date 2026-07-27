# Apifox CLI · 仓库映射

本目录存放 **Repo-first** 的项目级配置（非凭据）。

| 文件 | 说明 |
|------|------|
| `settings.json` | **权威**：`projectId`、私有化 `apiBaseUrl` |
| `suites.yaml` | 资产 → 生成器 / 场景 / 环境 / 工作分支 / 可选 triage；顶层 project_id 仅对照 |
| `ai-branches.json` | 可选本机缓存（已 gitignore）；**当前脚本不读写**，勿当真相源 |
| `.gitignore` | 忽略本机私有文件与 `ai-branches.json` |

**新人小白入门（推荐先读）：**  
[`api-testcases/api_tests/postman/docs/Apifox-CLI-小白入门流程.md`](../api-testcases/api_tests/postman/docs/Apifox-CLI-小白入门流程.md)

**团队协作完整说明：**  
[`api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-协作指南.md`](../api-testcases/api_tests/postman/docs/Apifox-CLI-Repo-First-协作指南.md)  
（含 **§15 团队推广**：群公告、培训 checklist、推广节奏）

**Cursor Skill：** [`.cursor/skills/apifox-cli-repo-first/`](../.cursor/skills/apifox-cli-repo-first/SKILL.md)

**主入口：**

```powershell
.\scripts\ApifoxRepoFirst.ps1 -Action SyncCheck -Asset papi_2548
```

凭据仅放在仓库根 `.env` 的 `APIFOX_ACCESS_TOKEN`，勿提交。  
报告与流水线中间件：`apifox-reports/<asset>/`（gitignore；其中 `generated/` 放 apifox 包与 openapi 桥）。
