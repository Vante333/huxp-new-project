---
name: fetch-confluence-troubleshooting
description: >-
  指导从 Confluence 通过 API 拉取需求/技术文档为本地 Markdown、下载图片附件、拉取后 Markdown
  格式自检与修复，以及网络/认证/Windows 文件名等常见问题。在用户给出 Confluence URL、要求拉取
  Confluence、使用 tools/req-docs/fetch_confluence.py、PAGE_ID、requirements 或 tech-docs 目录落盘、
  或 Confluence 拉取失败排查时使用；Agent 应先读本 Skill 再执行命令与修复。
---

# Confluence 页面拉取指南

当用户提供 Confluence URL 并要求拉取内容时，**自动执行以下完整流程**，无需额外确认。

## 自动执行流程

### 步骤 1：解析 URL 并确定输出路径

从 URL 中提取信息：

- **PAGE_ID**：从 `/pages/<PAGE_ID>/` 提取
- **页面标题**：从 URL 末尾或 `/<TITLE>` 部分推断

根据内容类型确定输出目录：

| 内容类型 | 输出目录 | 示例 |
|---------|---------|------|
| 需求文档 | `requirements/<迭代>/` | `requirements/2026Q1_SP5/V3.17.0.md` |
| 技术方案 | `tech-docs/<迭代>/` | `tech-docs/2026Q1_SP5/tech-design.md` |

### 步骤 2：拉取 Markdown 内容

**必须使用 `full_network` 权限**执行：

```bash
python tools/req-docs/fetch_confluence.py markdown <PAGE_ID> <输出路径>
```

示例：

```bash
python tools/req-docs/fetch_confluence.py markdown 1577484335 requirements/2026Q1_SP5/V3.17.0.md
```

### 步骤 3：下载图片附件

**必须使用 `full_network` 权限**，通过内联 Python 脚本下载到对应 `images/` 目录：

```python
python -c "
import os, sys
sys.path.insert(0, 'tools')
from fetch_confluence import api_get, get_auth_header, BASE_URL
from urllib.request import Request, urlopen

page_id = '<PAGE_ID>'
img_dir = '<输出目录>/images'
os.makedirs(img_dir, exist_ok=True)

data = api_get(f'/rest/api/content/{page_id}/child/attachment?limit=100')
for att in data.get('results', []):
    filename = att['title']
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
        continue
    download_url = BASE_URL + att['_links']['download']
    req = Request(download_url, headers=get_auth_header())
    resp = urlopen(req, timeout=120)
    with open(os.path.join(img_dir, filename), 'wb') as f:
        f.write(resp.read())
    print(f'Saved: {filename}')
"
```

**注意**：图片较多时下载耗时较长（可能 2-4 分钟），设置 `block_until_ms: 120000` 或更长。

### 步骤 4：输出结果摘要

完成后向用户报告：

1. 生成的文件路径
2. 下载的图片数量
3. 文档主要内容概要（标题、功能模块等）
4. 提示表格格式可能需要手动整理

### 步骤 5：自动检查并修复 Markdown 格式（必做）

拉取完成后，**必须自动执行以下格式检查和修复**，不需要用户额外确认：

#### 5.1 检查清单

逐项检查以下常见问题：

| 检查项 | 问题特征 | 修复方法 |
|--------|----------|----------|
| 标题粘连 | `...png)2. 核心概念` 图片/内容后直接接标题 | 在标题前插入空行，确保 `#` 独占一行 |
| 章节编号未成为标题 | `1. 产品背景在 DragonPass...` 编号和正文挤在一起 | 拆分为 `## 1. 产品背景` + 换行 + 正文 |
| 子章节格式不规范 | `### 2.1 权益定义内容...` 标题和内容同行 | 标题独占行，内容另起一行 |
| 列表空行过多 | 列表项之间有 2-3 个空行 | 压缩为标准格式（列表项之间无空行） |
| 表格断裂 | 错误码显示为 `500.031.002\n\n \| 说明\n\n \|` | 重建为标准表格 `\| 场景 \| 错误码 \| 说明 \|` |
| HTML 实体未转义 | `&ldquo;` `&rdquo;` `&rarr;` `&nbsp;` | 替换为 `"` `"` `->` ` ` |
| 代码块类型不当 | 接口路径用 `json` 包裹 | 改为 `text` 代码块 |

#### 5.2 修复执行顺序

按以下顺序修复，避免遗漏：

1. **拆分章节标题**
   - 识别 `1./2./3.` 等主章节，确保前面有 `## ` 且独占一行
   - 识别 `2.1/2.2/3.1` 等子章节，确保前面有 `### ` 且独占一行

2. **修复列表格式**
   - 删除列表项之间的多余空行
   - 确保嵌套列表缩进正确（2 空格）

3. **重建表格**
   - 识别"错误码 + 说明"片段，统一改成：

     ```markdown
     | 场景 | 错误码 | 说明 |
     | --- | --- | --- |
     | 重复 clientOrderId | 500.031.002 | 同一个第三方订单号不能重复发放权益 |
     ```

4. **替换 HTML 实体**
   - `&ldquo;` `&rdquo;` → `"` `"`
   - `&rarr;` → `->`
   - `&nbsp;` → 空格
   - `&ndash;` → `–`

5. **统一代码块**
   - 接口路径（如 `POST /v3_xxx`）使用 `text` 代码块
   - JSON 示例使用 `json` 代码块

6. **最终检查**
   - 预览确认标题层级、表格、列表显示正常
   - 确保只修格式，不改业务内容（字段名、错误码、接口路径保持原样）

#### 5.3 修复原则

- **只修格式，不改语义**：字段名、错误码、接口路径、业务描述保持原文
- **保留图片引用**：`![](images/xxx.png)` 不变
- **保持一致性**：同类内容用同样格式（如所有异常表格结构统一）

---

## 常见问题与解决方案

### 问题 1：网络请求被沙箱拦截

**现象**：`ConnectionRefusedError` 或 `URLError: <urlopen error [WinError 10061]>`

**解决**：Shell 命令必须添加 `required_permissions: ["full_network"]`

### 问题 2：WebFetch 无法访问 Confluence

**现象**：WebFetch 返回 Atlassian 登录页面。

**解决**：不要用 WebFetch，使用 `tools/req-docs/fetch_confluence.py`，它通过 `.env` 中的 `JIRA_EMAIL` / `JIRA_API_TOKEN` 进行 API 认证。

### 问题 3：Windows 下中文文件名导致 OSError

**现象**：`OSError: [Errno 22] Invalid argument`

**解决**：输出文件名使用英文命名（如 `V3.17.0.md`），避免中文字符。

### 问题 4：download_images 目录硬编码

**现象**：`fetch_confluence.py` 的 `download_images` 模式目录写死。

**解决**：使用步骤 3 的内联 Python 脚本，可自定义目标目录。

### 问题 5：HTML 转 Markdown 格式混乱

**现象**：

- 表格结构破损，显示为 `内容\n\n |\n说明\n\n |` 碎片
- HTML 实体未转义（`&ldquo;` `&rarr;` 等）
- 标题和正文挤在一行（如 `...png)2. 核心概念定义2.1 权益...`）
- 列表项之间空行过多

**解决**：拉取完成后**自动执行步骤 5 的格式修复流程**，按检查清单逐项修复：

1. 拆分粘连的章节标题
2. 重建断裂的表格
3. 替换 HTML 实体
4. 压缩多余空行
5. 统一代码块类型

详见上方「步骤 5：自动检查并修复 Markdown 格式」。

---

## 快速参考

```bash
# 1. 拉取 Markdown（需要 full_network 权限）
python tools/req-docs/fetch_confluence.py markdown <PAGE_ID> <输出路径>

# 2. 列出附件
python tools/req-docs/fetch_confluence.py attachments <PAGE_ID>

# 3. 下载图片（使用内联脚本，需要 full_network 权限）
# 见步骤 3 的完整脚本
```
