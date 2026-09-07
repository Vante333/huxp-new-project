---
name: api-test-datasets
description: >-
  DragonPass 沙箱/UAT 接口测试数据集（鉴权1/鉴权2、ProgramID+clientId+secret、支付链接 Body）。
  Use when the user mentions 测试数据集、测试数据集123、测试数据集222、测试数据集.json 2222、
  鉴权1、鉴权2、取 Token、POST /v2/auth/token、支付链接、H5_CASHIER、orderId SL20260901BH9PWO6、
  ProgramID 2045264240542720 / 1919256841868288 / 1991829094323200, or asks which clientId/secret/Program to use.
---

# API 测试数据集

调 Generic API / Apifox 时，**先读本 skill 的数据集**，不要让用户再从桌面复制。

工作区副本：请用本机 `d:/api/testdata/`（不要提交密钥）。Skill 里的 `datasets/` 仅本机使用，Git 已忽略。

## 三份数据集怎么用

| 来源 | 文件 | 场景 |
|------|------|------|
| 桌面 `测试数据集123` | [datasets/测试数据集123.csv](datasets/测试数据集123.csv) | **双 Key HS256**：同一 Program 下鉴权1 / 鉴权2 分别取 Token |
| 桌面 `测试数据集.json 2222` | [datasets/测试数据集-2222.csv](datasets/测试数据集-2222.csv) | UAT 业务 Program：会籍全品类 / Lounge+FT |
| 桌面 `测试数据集222` | [datasets/测试数据集222.jsonc](datasets/测试数据集222.jsonc) | `POST /v2/orders/payments` 支付链接 Body（含注释，发请求用无注释 JSON） |

## 强制规则

1. 取 Token：`POST /v2/auth/token`，Body 只用表里的 `clientId` + `secret`；Header `X-Program-ID` 必须与该行 `ProgramID` 同一套。
2. 鉴权1、鉴权2 **不要混用** secret；ProgramID 都是 `2045264240542720`。
3. `测试数据集-2222.csv` 前两行数据相同，用一行即可；第三行是另一套 Lounge+FT Program。
4. 支付链接 Body 桌面原文件带 `//` 注释，**不能直接当 JSON 发送**。发请求用：

```json
{
  "orderId": "SL20260901BH9PWO6",
  "returnUrl": "https://example.com/payment/return",
  "paymentMethod": "H5_CASHIER",
  "language": "en-US",
  "durationInSeconds": 60
}
```

5. 这些是测试凭证。不要提交到 git、不要写进公开回复的大段重复粘贴；回答里用「鉴权1 / AllCategories 那一行」指代即可，需要调试时再读文件。

## Git 仓库访问权限（务必遵守，勿越权推送）

| 仓库 | 远端 | 我的权限 | 说明 |
|------|------|----------|------|
| `interface_cursor`（本人测试主仓库） | `http://192.168.1.165:62000/huxp/my-project.git` | ✅ 读 + 写 | 本人账号 `huxp`，PAT 已存凭据管理器，可 `git push` |
| `interface_cursor`（同事刘冬霞的仓库） | `http://192.168.1.165:62000/liudx/interface_cursor.git` | 🔒 只读拉取 | **不是本人账号，只有访问/拉取权限，不得更改或推送内容** |

**硬性规则：**
- **永远不要**对 `liudx/interface_cursor` 执行 `git push`、`git config`、改远端、force-push、删分支等写操作。
- 本地 `interface_cursor` 默认远端 `origin` 指向 `liudx/interface_cursor.git`（历史遗留），**仅用于拉取最新代码参考**；要保存本人工作请推到 `myproject`（`huxp/my-project`）。
- 如需把本人新增内容入库，用 `git push myproject main`，不要用 `git push origin`。
- `business-international-developer-api` / `basedata` / `api-auth` 是其它业务代码仓库，同样**只读**，不要把测试产物塞进去，也不要改它们的远端。

## Git 提交身份（务必用本人，勿用领导账号）

- **本人提交身份（固定，勿改）：**
  - `user.name` = `胡鑫朋`（注意是「朋」，不是「明」）
  - `user.email` = `huxp@dragonpass.com.cn`
- **刘冬霞（liudx@dragonpass.com.cn）是本人领导**，**严禁**用她的名字/邮箱作为提交作者。历史提交里出现「刘冬霞」的，只可能是她本人在 `liudx/interface_cursor` 的原始提交，**不要改写那些原始提交的作者**；本人新增的提交若误用了她的身份，必须改回 `胡鑫朋 <huxp@dragonpass.com.cn>`。
- 本仓库已设 **local** `user.name/user.email` = 胡鑫朋 / huxp@dragonpass.com.cn；新机器或新 clone 后记得重设。
- 推送目标：`huxp/my-project`（本人有写权限，PAT 已存凭据管理器）。`huxp/my-project` 的 `main` 是受保护分支，平时普通推即可；只在改写历史时才需临时解除保护并强推（已做过一次，恢复保护后勿再强推）。

## Git / GitLab 基础概念（新人别混）

三层东西，完全不同：

| 名字 | 是什么 | 官网 | 收费 |
|------|--------|------|------|
| **Git** | 版本控制**工具**本身（命令行那个 `git`） | https://git-scm.com | 永久免费、开源 |
| **GitLab** | 基于 Git 的**代码托管/协作平台**（网页、MR、CI） | https://gitlab.com | 有免费版也有付费版 |
| **GitHub** | 另一家代码托管平台（和 GitLab 是竞品） | https://github.com | 有免费版也有付费版 |

- **GitLab 自己**分：**CE（Community Edition，免费开源）** 和 **EE（Enterprise Edition，付费企业版，功能更多）**。
- **本公司用的是自己搭的私有 GitLab**：`http://192.168.1.165:62000`，只有公司内网能访问。CE 还是 EE 看不出，但对使用无影响。
- 一句话：**Git 是工具，GitLab 是平台，本公司搭的是私有 GitLab。** 不需要去 git-scm.com 注册账号。

## 本地工作区 `d:\api` 的仓库布局

`d:\api` 下有 **4 个独立 git 仓库**（每个都有自己的 `.git`）：

| 仓库目录 | 是什么 | 我的权限 |
|----------|--------|----------|
| `interface_cursor` | 测试主仓库（日常用这个） | 见下表（连两个远端） |
| `business-international-developer-api` | 业务代码仓库 | 🔒 只读 |
| `business-international-developer-basedata` | 基础数据仓库 | 🔒 只读 |
| `business-international-api-auth` | 鉴权代码仓库 | 🔒 只读 |

后三个是研发同事的代码仓库，只 clone 下来参考接口实现，**不要往里推、不要改**。

## `interface_cursor` 的两个远端（重点）

一个本地仓库可以连多个远端。`d:\api\interface_cursor` 同时连着 2 个：

| 远端名 | GitLab 项目 | 我的权限 | 用途 |
|--------|-------------|----------|------|
| `myproject` | `huxp/my-project`（**本人**） | ✅ 读 + 写 | **保存本人工作**，`git push myproject main` |
| `origin` | `liudx/interface_cursor`（**领导刘冬霞**） | 🔒 只读 | 拉取领导维护的用例/框架作参考，`git fetch origin` / `git pull origin` |

**日常三句话：**
1. 保存自己工作 → `git push myproject main`
2. 看领导最新加了什么 → `git fetch origin` 后 `git log origin/main`（只看）；要合并 `git pull origin`
3. **永远不要** `git push origin`（领导仓库，推了 403，且不该推）

**真正属于本人的仓库只有 1 个：`huxp/my-project`。** 领导的 `liudx/interface_cursor` 只是看。

## 新人怎么填 Apifox

1. 打开 Apifox，选对应环境，URL 前缀用沙箱：`https://developer-sandbox.dragonpass.com/api`
2. 取 Token：`POST /v2/auth/token`，Header 勾 `X-Program-ID` = 表中 ProgramID，`Content-Type=application/json`
3. Body 填该行 `clientId`、`secret`，点「发送」（不要走自动化）
4. 成功后抄 `accessToken`，后续业务接口 Header：`Authorization: Bearer <token>`，`X-Program-ID` 仍用同一 Program
5. 测支付链接：把上面 JSON 贴到 `POST /v2/orders/payments`；`orderId` 过期则先用当前 Program 重新下单再替换
