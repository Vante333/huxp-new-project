# 脚本工具说明

仓库根目录执行下列命令（Windows / macOS / Linux 均需已配置好对应依赖与 PATH）。

## 目录

| 目录 | 对应分类 | 内容 |
|------|----------|------|
| `apifox-cli/` | Apifox CLI 流水线 | `ApifoxRepoFirst.ps1` 调用的转换 / Push / 失败分流 |
| `payment-js/` | Payment 断言 JS | 生成器 `LoadToolsJsLines` 读取；**勿删** |
| `req-docs/` | 需求 / 用例文档 | Confluence / Jira / XMind ↔ Markdown |
| `data-check/` | 接口清单 / 数据核对 | 接口用例 Excel、OAS 落盘、Redis 对拍 |
| （根） | 其它 | `ServePapi2548Allure.py`、探测/并发脚本、本 README、`requirements.txt` |

依赖：`pip install -r tools/requirements.txt`。调试草稿勿落本目录；结束后自动删 `_tmp_*`（见 `.cursor/rules/local-scratch-hygiene.mdc`）。

配置文件（非脚本）：`req-docs/jira_sync_config.example.txt` → 复制为 `jira_sync_config.txt` 供 Jira 批量同步。

---

## Apifox CLI（`apifox-cli/`）

日常请走 `.\scripts\ApifoxRepoFirst.ps1`，不要手搓下面脚本。解析 suites 可单独：

```powershell
python tools/apifox-cli/ApifoxSuitesYaml.py --list-keys
```

---

## XMind → testcases Markdown（`req-docs/xmind_to_testcases_md.py`）

将带 **`tc-p*`** 优先级语义的 XMind 转为 [`testcases/`](../testcases/) 风格 Markdown。**用户要求用 XMind 替换 testcases 下 md 时优先用本脚本**，勿临时写转换代码。

```powershell
python tools/req-docs/xmind_to_testcases_md.py `
  --xmind path/to/file.xmind `
  --out testcases/2026Q2SP4/PAPI-xxxx-测试用例-001.md `
  --requirement requirements/2026Q2SP4/PAPI-xxxx.md
```

- **仅导出**脑图中 `tc-p*` / `tc:` 节点。
- 备用：`xmind_to_markdown_v2.py`（另一套 tc 格式）、`xmind2md.py`（通用大纲）、`xmind_workbook_to_testcase_md.py`（带表格工作簿）。
- Markdown 表 → 列表（便于导回 XMind）：`python tools/req-docs/md_tables_to_xmind_lists.py input.md -o output-xmind.md`

---

## Jira 需求同步（`req-docs/jira_sync.py`）

```powershell
python tools/req-docs/jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/entilement.md
python tools/req-docs/jira_sync.py --config tools/req-docs/jira_sync_config.txt
```

环境变量：`JIRA_BASE_URL`（默认 `https://dragonpass.atlassian.net`）、`JIRA_EMAIL`、`JIRA_API_TOKEN`。VS Code Task 见 [`.vscode/tasks.json`](../.vscode/tasks.json)。

---

## Confluence 拉取（`req-docs/fetch_confluence.py`）

```powershell
python tools/req-docs/fetch_confluence.py markdown <PAGE_ID> path/to/output.md
```

排查见 [`.cursor/skills/fetch-confluence-troubleshooting/SKILL.md`](../.cursor/skills/fetch-confluence-troubleshooting/SKILL.md)。

---

## 接口清单 / 对拍（`data-check/`）

```powershell
python tools/data-check/export_api_main_testcase_xlsx.py
python tools/data-check/CompareRedisExcelResourcesPipeline.py --help
```

---

## PAPI-2548 Allure（根目录，冻结 pytest）

```powershell
python tools/ServePapi2548Allure.py
python tools/ServePapi2548Allure.py --serve-only
```

详见 [api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md) 中 Allure 章节。
