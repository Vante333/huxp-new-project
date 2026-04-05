# 脚本工具说明

仓库根目录执行下列命令（Windows / macOS / Linux 均需已配置好对应依赖与 PATH）。

## 工具总览

| 脚本 | 一句话用途 |
|------|------------|
| `xmind_to_markdown_v2.py` | XMind（`tc-p*` 结构）→ 团队规范的功能测试用例 Markdown |
| `xmind2md.py` | 通用脑图 → 标题 + 列表式 Markdown（无 tc-p* 专用结构） |
| `md_tables_to_xmind_lists.py` | Markdown 管道表格 → 无序列表，便于 XMind「从 Markdown 导入」 |
| `jira_sync.py` | 从 Jira 拉取 Issue 为 Markdown，可批量、可下图 |
| `fetch_confluence.py` | Confluence 页面导出 HTML/JSON/Markdown 或下载附件图片 |
| `ServePapi2548Allure.py` | 清空 Allure 结果目录 → 跑 PAPI-2548 pytest → `allure serve` |
| `GenerateRequirementsIndex.py` | 扫描 `requirements/` 各迭代，刷新总览与各迭代 README 中的索引表 |

配置文件（非脚本）：`jira_sync_config.example.txt` → 复制为 `jira_sync_config.txt` 供 Jira 批量同步使用（见 Jira 一节）。

---

## 2. 需求文档索引（GenerateRequirementsIndex.py）

根据 [`requirements/`](../requirements/) 下各一级子目录中的 `.md` 文件（不含各目录下的 `README.md`），自动更新 [`requirements/README.md`](../requirements/README.md) 中的「迭代一览」表，以及各迭代目录 `README.md` 中 `<!-- REQ_INDEX_START -->` … `<!-- REQ_INDEX_END -->` 之间的**需求文档索引**表。手写段落（如迭代目标、跨需求依赖）不会被覆盖。

```bash
python tools/GenerateRequirementsIndex.py
```

依赖：Python 标准库（无第三方包）。

---

## 3. XMind 测试用例脑图 → Markdown（xmind_to_markdown_v2.py）

将带 **`tc-p*`** 优先级语义的 XMind（或导出的 `content.json`）转为 [`testcases/`](../testcases/) 风格的用例 Markdown。

```bash
python tools/xmind_to_markdown_v2.py -i path/to/file.xmind -o testcases/2026Q2_SP1/out.md
python tools/xmind_to_markdown_v2.py -i path/to/content.json -o testcases/out.md
```

无参数时脚本内另有默认输入/输出路径（见文件头注释）；建议显式传入 `-i` / `-o`。

---

## 4. XMind 通用大纲 → Markdown（xmind2md.py）

将 XMind 8+（`content.json`）按树结构转为普通 Markdown 大纲（`#` 标题 + 缩进列表），**不**解析 `tc-p*` 用例模板。仅依赖 Python 标准库。

```bash
python tools/xmind2md.py path/to/file.xmind -o output.md
python tools/xmind2md.py path/to/folder/   # 批量转换目录下所有 .xmind
```

---

## 5. Markdown 表格 → 列表（md_tables_to_xmind_lists.py）

将 Markdown 中的管道表格转为无序列表，便于 XMind「从 Markdown 导入」时展开子主题。

```bash
python tools/md_tables_to_xmind_lists.py input.md -o output-xmind.md
# 默认输出：同目录下 input-xmind.md
```

---

## 6. Jira 需求同步（jira_sync.py）

从 Jira Cloud 拉取 Issue 描述并导出为 Markdown，支持**描述中的图片**下载到本地并替换为相对路径，便于「手动点击」同步更新需求文档。

### 依赖

```bash
pip install requests
```

或：

```bash
pip install -r tools/requirements.txt
```

### 环境变量

| 变量 | 说明 | 默认 |
|------|------|------|
| `JIRA_BASE_URL` | Jira 站点地址 | `https://dragonpass.atlassian.net` |
| `JIRA_EMAIL` | 登录邮箱（API Token 所属账号） | 必填 |
| `JIRA_API_TOKEN` | [Atlassian API Token](https://id.atlassian.com/manage-profile/security/api-tokens) | 必填 |

### 用法

**同步单个 Issue，输出到指定文件：**

```bash
python tools/jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/entilement.md
```

**输出到目录（自动生成 `{IssueKey}.md`）：**

```bash
python tools/jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/
```

**使用配置文件批量同步：**

1. 复制 `jira_sync_config.example.txt` 为 `jira_sync_config.txt`（或任意文件名）。
2. 每行写：`ISSUE_KEY: path/to/output.md`。
3. 执行：

```bash
python tools/jira_sync.py --config tools/jira_sync_config.txt
```

**可选参数：**

- `--images-dir images`：图片存放子目录名（相对每个 MD 所在目录），默认 `images`。图片会保存到 `{输出目录}/{images-dir}/`。

### 行为说明

- 使用 Jira REST API v3 获取 Issue 的 `summary`、`description`（ADF）、`attachment`。
- 将 ADF 描述转为 Markdown（标题、列表、代码块、引用、段落、加粗/斜体/链接等）。
- 描述中的**图片**（ADF `mediaSingle`/`media`）通过附件列表按文件名匹配，下载到本地 `images/`（或 `--images-dir`），并在 Markdown 中替换为 `![](images/xxx.png)`。
- 生成的 MD 顶部会包含标题和 Jira 链接，便于追溯。

### 在 Cursor / VS Code 中「一键同步」

1. 在项目根目录下执行上述命令即可。
2. 已预置 Task：见 [`.vscode/tasks.json`](../.vscode/tasks.json)（如「Jira 同步: 使用配置文件」）。
3. 配置好 `JIRA_EMAIL` 与 `JIRA_API_TOKEN`（本机环境变量或根目录 `.env`）。

---

## 7. Confluence 拉取（fetch_confluence.py）

通过 Confluence REST API 导出页面或附件（需在脚本/环境中配置认证，可读根目录 `.env`）。常用子命令示例：

```bash
python tools/fetch_confluence.py content <PAGE_ID>
python tools/fetch_confluence.py attachments <PAGE_ID>
python tools/fetch_confluence.py download_images <PAGE_ID>
python tools/fetch_confluence.py markdown <PAGE_ID> path/to/output.md
```

排查认证、路径、Windows 文件名等问题时可让 Cursor Agent 先读 [`.cursor/skills/fetch-confluence-troubleshooting/SKILL.md`](../.cursor/skills/fetch-confluence-troubleshooting/SKILL.md)。

---

## 8. PAPI-2548 Allure 一键清空+pytest+serve（ServePapi2548Allure.py）

默认：删除 `reports/papi2548-allure-results` 与 `reports/papi2548-allure-report`（若存在）→ 运行 PAPI-2548 pytest → `allure serve`。需本机已安装 Allure Commandline。

```bash
python tools/ServePapi2548Allure.py
python tools/ServePapi2548Allure.py --serve-only   # 仅打开当前结果，不删、不跑测试
```

详见 [api-testcases/2026Q2_SP1/README.md](../api-testcases/2026Q2_SP1/README.md) 中 Allure 章节。
