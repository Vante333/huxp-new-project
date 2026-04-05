# Apifox MCP Server 配置指南

本文档记录了在 Cursor IDE 中配置 Apifox MCP Server 的完整步骤，以及实际遇到的问题和解决方案。

---

## 一、前置条件

- **Node.js** >= 18（推荐最新 LTS 版本）
- **Cursor IDE**（或其他支持 MCP 的 IDE）
- **Apifox 账号**，并拥有目标项目的编辑者及以上权限
- 已获取以下信息：
  - **API 访问令牌**：Apifox → 头像 → 账号设置 → API 访问令牌 → 新建令牌
  - **项目 ID**：Apifox → 进入项目 → 项目设置 → 基本设置 → 项目 ID
  - **私有化部署地址**（如适用）：公司 Apifox 服务器 URL

---

## 二、Mac 配置步骤

### 1. 创建 MCP 配置文件

在项目根目录下创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "API 文档": {
      "command": "npx",
      "args": [
        "-y",
        "apifox-mcp-server@latest",
        "--project-id=<项目ID>"
      ],
      "env": {
        "APIFOX_ACCESS_TOKEN": "<你的API访问令牌>"
      }
    }
  }
}
```

**私有化部署版本**需在 args 中增加：

```json
{
  "mcpServers": {
    "API 文档": {
      "command": "npx",
      "args": [
        "-y",
        "apifox-mcp-server@latest",
        "--project-id=<项目ID>",
        "--apifox-api-base-url=<私有化部署服务器地址>"
      ],
      "env": {
        "APIFOX_ACCESS_TOKEN": "<你的API访问令牌>"
      }
    }
  }
}
```

### 2. 重启 MCP 服务

`Cmd + Shift + P` → 输入 `Reload Window` → 回车

---

## 三、Windows 配置步骤

Windows 系统需要额外处理 Node.js 路径问题，推荐使用 `.cmd` 脚本方式。

### 方式一：标准方式（Node.js 已加入系统 PATH）

创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "API 文档": {
      "command": "cmd",
      "args": [
        "/c",
        "npx",
        "-y",
        "apifox-mcp-server@latest",
        "--project-id=<项目ID>"
      ],
      "env": {
        "APIFOX_ACCESS_TOKEN": "<你的API访问令牌>"
      }
    }
  }
}
```

**私有化部署版本**需在 args 中增加 `"--apifox-api-base-url=<私有化部署服务器地址>"`。

### 方式二：通过 .cmd 脚本方式（Node.js 未加入系统 PATH）

如果 Cursor 无法找到 `npx` 命令，需要创建一个 `.cmd` 启动脚本来手动设置 PATH。

**步骤 1**：创建 `.cursor/run-apifox-mcp.cmd`：

```batch
@echo off
set PATH=C:\Program Files\nodejs;%PATH%
npx -y apifox-mcp-server@latest --project-id=<项目ID> --apifox-api-base-url=<私有化部署服务器地址>
```

> 注意：`C:\Program Files\nodejs` 替换为你实际的 Node.js 安装路径。

**步骤 2**：创建 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "API 文档": {
      "command": "cmd",
      "args": ["/c", "<.cmd脚本的绝对路径>"],
      "env": {
        "APIFOX_ACCESS_TOKEN": "<你的API访问令牌>"
      }
    }
  }
}
```

### 方式三：使用 `.env` 管理令牌（推荐，避免提交密钥）

将 `APIFOX_ACCESS_TOKEN` 写在**项目根目录**的 `.env` 中（确保 `.gitignore` 已忽略 `.env`），由 PowerShell 启动脚本读取后再启动 MCP。本仓库提供 **`.cursor/run-apifox-mcp.ps1`** 与 **`.env.example`**。

**若你已有 `.env`（含 `JIRA_EMAIL`、`JIRA_API_TOKEN` 等）**：**不要改动或删除原有行**，仅在文件**末尾**追加「Apifox MCP」段（见 `.env.example` 底部），增加一行 `APIFOX_ACCESS_TOKEN=` 即可。

**`.cursor/mcp.json` 示例**（不要在 JSON 里写令牌）：

```json
{
  "mcpServers": {
    "API 文档": {
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "<仓库绝对路径>\\.cursor\\run-apifox-mcp.ps1",
        "-ProjectId",
        "<项目ID>",
        "-BranchId",
        "<分支ID>"
      ]
    }
  }
}
```

**步骤**：若无 `.env`，可复制 `.env.example` 为 `.env` 并逐项填写；若已有 `.env`，仅在保留原配置的前提下**追加** `APIFOX_ACCESS_TOKEN=`（见 `.env.example` 中「Apifox MCP」段）。

### 3. 重启 MCP 服务

`Ctrl + Shift + P` → 输入 `Reload Window` → 回车

---

## 四、配置参数说明

| 参数 | 说明 | 必填 |
|---|---|---|
| `--project-id` | Apifox 项目 ID | 是 |
| `--apifox-api-base-url` | 私有化部署 Apifox 服务器地址 | 私有化部署时必填 |
| `--site-id` | 公开文档站 ID（与 project-id 二选一） | 否 |
| `--branch-id` | 迭代分支 ID | 否 |
| `--oas` | 直接使用 OpenAPI/Swagger 文件 URL 或路径 | 否 |
| `APIFOX_ACCESS_TOKEN` | API 访问令牌（环境变量） | 使用 project-id 时必填 |

---

## 五、遇到的问题与解决方案

### 问题 1：`"No server info found"` / MCP 服务器无法启动

**现象**：MCP 日志持续显示 `[error] No server info found` 和 `Server not yet created, returning empty offerings`。

**根本原因**：Cursor 启动 MCP 进程时，系统 PATH 中不包含 Node.js 路径，导致 `npx` 命令找不到 `node`。

**报错信息**：
```
'"node"' 不是内部或外部命令，也不是可运行的程序或批处理文件。
```

**解决方案**：
- 使用 `.cmd` 脚本方式，在脚本中显式设置 `set PATH=C:\Program Files\nodejs;%PATH%`
- 或将 Node.js 安装目录添加到系统环境变量 PATH 中

---

### 问题 2：`401 - "The token is invalid"`

**现象**：MCP 服务器能启动，但调用 API 时返回 `{"success":false,"errorCode":"401005","errorMessage":"The token is invalid"}`。

**可能原因及排查**：

| 原因 | 排查方式 |
|---|---|
| Token 已过期或无效 | 重新在 Apifox 生成新令牌 |
| Token 复制不完整 | 重新复制完整令牌 |
| **使用了私有化部署版本** | 见下方「问题 3」 |
| 环境变量名错误 | 确认使用 `APIFOX_ACCESS_TOKEN`（不是 `APIDOG_ACCESS_TOKEN`） |

---

### 问题 3：私有化部署导致认证失败（本次核心问题）

**现象**：Token 确认有效、权限确认充足，但 MCP 始终返回 401。

**根本原因**：公司使用 Apifox **私有化部署版本**（如 `https://apifox.yourcompany.com`），但 MCP 服务器默认连接的是**公网** `https://api.apifox.com`，Token 在公网自然无法通过认证。

**解决方案**：在启动参数中添加 `--apifox-api-base-url=<私有化部署服务器地址>`。

**如何判断是否为私有化部署**：
- 你访问 Apifox 时使用的是公司内部域名（如 `apifox.xxx.com`），而不是 `app.apifox.com`
- 文档帮助页面指向公司内部地址

---

### 问题 4：`403 - "No project maintainer privilege"`

**现象**：Token 被识别但返回权限不足。

**解决方案**：
- 确认你的账号在项目中至少拥有**编辑者**及以上权限
- 在 Apifox 项目设置 → 成员管理中检查你的角色
- 联系项目管理员提升权限

---

### 问题 5：使用了错误的 npm 包

**现象**：配置正确但 API 返回异常。

**说明**：Apifox（中文版）和 Apidog（国际版）是两个不同的产品，对应不同的 npm 包：

| 产品 | npm 包名 | 环境变量 |
|---|---|---|
| Apifox（中文版） | `apifox-mcp-server` | `APIFOX_ACCESS_TOKEN` |
| Apidog（国际版） | `apidog-mcp-server` | `APIDOG_ACCESS_TOKEN` |

请根据你使用的产品选择正确的包和环境变量名。

---

### 问题 6：`ParameterBindingException` + `WriteErrorCommand`（Windows + PowerShell 启动脚本）

**现象**：Cursor MCP 日志中出现 `ParameterBindingException`，`FullyQualifiedErrorId` 为 `PositionalParameterNotFound,Microsoft.PowerShell.Commands.WriteErrorCommand`，随后 `Client closed` / `initializing -> error`。

**根本原因**：MCP 由 Cursor 以**非交互子进程**拉起 PowerShell。部分环境下对 `Write-Error` 的位置参数绑定不稳定，错误被“绑定异常”盖住，难以看到真实原因。

**解决方案（本仓库已落实）**：`.cursor/run-apifox-mcp.ps1` 在启动阶段**不再使用 `Write-Error`**，改为将致命信息写入 **stderr** 后 `exit 1`（见脚本内 `Write-McpLaunchErr`）。

---

### 问题 7：stderr 中文乱码、日志里出现 `undefined` 或像“脚本碎片”的内容；误判未配置 `APIFOX_ACCESS_TOKEN`

**现象**：

- 日志里中文末尾变成 `?`，后面还跟一大段像 PowerShell 源码的乱码，并可能出现 `undefined`。
- 或提示 `APIFOX_ACCESS_TOKEN` 未设置，但编辑器里明明已在 `.env` 中填写。

**可能原因**：

| 原因 | 说明 |
|------|------|
| **stderr 编码** | Windows 控制台默认代码页与 Cursor 按 **UTF-8** 解读日志不一致时，多字节字符（如中文句号）易断码，后续字节被误显示成“代码碎片”。 |
| **`.env` 未保存** | MCP 读的是**磁盘上的文件**；若仅编辑未保存，进程内仍看不到令牌。 |
| **路径不一致** | 确认 `mcp.json` 里 `-File` 指向的仓库根目录下，确实存在正在维护的那份 `.env`。 |

**解决方案（本仓库已落实）**：

1. **`Write-McpLaunchErr`**：用 **UTF-8 字节**写入 stderr，减轻 Cursor 侧断码与误解析。
2. **解析仓库根目录**：用 **`$PSScriptRoot`** 推导项目根（相对 `$MyInvocation.MyCommand.Path` 在少数宿主下更稳）。
3. **令牌校验**：使用 **`[string]::IsNullOrWhiteSpace($env:APIFOX_ACCESS_TOKEN)`**，避免仅空格被当成已配置。
4. **可读的英文错误行**：前缀 **`[apifox-mcp]`**，并输出**已尝试加载的 `.env` 绝对路径**（不含令牌），便于对照是否读错文件。

**自助排查**：修改 `.env` 后**保存文件** → `Reload Window` 或重启 Cursor → 若仍失败，将日志中带 **`[apifox-mcp]`** 的整行复制出来核对路径与提示。

---

## 六、验证 MCP 是否工作正常

配置完成并 Reload Window 后，在 Cursor 对话中输入：

> "通过 MCP 获取 API 文档，并告诉我项目中有几个接口"

AI 应该能正常返回项目中的接口信息。

---

## 七、常用提示词

| 用途 | 提示词示例 |
|---|---|
| 获取文档 | "通过 MCP 获取 API 文档，列出所有接口" |
| 生成代码 | "根据 API 文档，生成 /v2/users 相关的 MVC 代码" |
| 添加注释 | "根据 API 文档给 User 类的每个字段加上注释" |
| 刷新缓存 | "刷新 API 文档数据"（Apifox 文档更新后使用） |

---

## 八、本项目最终配置

令牌放在**项目根目录** **`.env`** 的 `APIFOX_ACCESS_TOKEN`（已在 `.gitignore`，勿提交）。**与 `JIRA_EMAIL`、`JIRA_API_TOKEN` 等原有项并存**：已有 `.env` 时只在末尾追加 Apifox 段，勿删改原配置；新环境可参考 **`.env.example`** 完整结构。

**`.cursor/mcp.json`**（不在此文件存放令牌；以下为当前双项目示例）：

```json
{
  "mcpServers": {
    "API 文档 346181": {
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "d:\\interface\\interface_cursor\\.cursor\\run-apifox-mcp.ps1",
        "-ProjectId",
        "346181",
        "-BranchId",
        "309372"
      ]
    },
    "API 文档 345747": {
      "command": "powershell",
      "args": [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "d:\\interface\\interface_cursor\\.cursor\\run-apifox-mcp.ps1",
        "-ProjectId",
        "345747",
        "-BranchId",
        "309343"
      ]
    }
  }
}
```

**`.cursor/run-apifox-mcp.ps1`**：由 **`$PSScriptRoot`** 推导仓库根目录并读取其中 **`.env`**，再执行 `npx apifox-mcp-server@latest`（含 `--apifox-api-base-url`、分支 ID 等，见脚本内参数默认值）。启动失败时通过 **`Write-McpLaunchErr`** 以 **UTF-8** 写 stderr，避免 Cursor 日志断码；校验 **`APIFOX_ACCESS_TOKEN`** 使用 **`IsNullOrWhiteSpace`**；错误信息带 **`[apifox-mcp]`** 前缀与 **`.env` 绝对路径**，便于与「问题 6」「问题 7」对照排查。手动调试时在仓库根执行：`powershell -NoProfile -ExecutionPolicy Bypass -File .\.cursor\run-apifox-mcp.ps1 -ProjectId <项目ID> -BranchId <分支ID>`（参数与 `.cursor/mcp.json` 保持一致）；本仓库不再附带 `.cmd` 快捷方式，需要时可按上文「方式二」自行新建。

若本机找不到 `npx`，可在自建 `.cmd` 中于调用 PowerShell 前增加 `set PATH=C:\Program Files\nodejs;%PATH%`（参见上文「问题 1」）。
