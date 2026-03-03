# 脚本工具说明

## 1. XMind 转 Markdown（xmind2md.py）

将 XMind 思维导图转为 Markdown，仅用 Python 标准库。

```bash
python xmind2md.py input.xmind -o output.md
python xmind2md.py ./my_folder/   # 批量转换目录下所有 .xmind
```

## 2. Jira 需求同步（jira_sync.py）

从 Jira Cloud 拉取 Issue 描述并导出为 Markdown，支持**描述中的图片**下载到本地并替换为相对路径，便于「手动点击」同步更新需求文档。

### 依赖

```bash
pip install requests
```

或使用项目根目录下的依赖（若有）：

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
python jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/entilement.md
```

**输出到目录（自动生成 `{IssueKey}.md`）：**

```bash
python jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/
```

**使用配置文件批量同步：**

1. 复制 `jira_sync_config.example.txt` 为 `jira_sync_config.txt`（或任意文件名）。
2. 每行写：`ISSUE_KEY: path/to/output.md`。
3. 执行：

```bash
python jira_sync.py --config jira_sync_config.txt
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
2. 可配置 Task：在 `.vscode/tasks.json` 中添加一项，例如：
   - 任务名：`Jira 同步 PAPI-2199`
   - 命令：`python tools/jira_sync.py PAPI-2199 -o requirements/2026Q1_SP3/entilement.md`
   - 配置好 `JIRA_EMAIL` 与 `JIRA_API_TOKEN`（本机环境变量或 `.env` 后在 task 中加载）。
3. 需要同步时运行该 Task（或绑定快捷键），即可从 Jira 拉取最新内容并更新本地 MD 与图片。
