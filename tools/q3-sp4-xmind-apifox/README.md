# Q3-SP4 按 XMind 模板的 Apifox 场景

对应：桌面《需求测试用例.xmind》四需求。  
目录标准 skill：`~/.cursor/skills/apifox-automation-folder-standard/SKILL.md`

## Apifox 落点（项目 346275 · 分支 ai/apifox-cli-sync）

```
membership/P1（全量用例）/
  FT可用性/按XMind用例/01~04
  支付链接/按XMind用例/01~02
  Auth双密钥/按XMind用例/02~04
membership/P0(冒烟用例)/others/
  SSO免登短链 · 冒烟
  FT可用性 · 冒烟
  支付链接 · 冒烟
```

SSO 全量仍在历史夹 `membership/sso免登录短链接/按XMind用例`（01~06），不要往那个夹继续堆支付/FT。

重建（会新建夹，勿重复执行）：`node build_all.js` 然后 `node push_all.js`

预调试：`node smoke_pre.js`（SSO/FT/039/045）；支付成功需会籍待支付 MS 单。

## Postman 文件（可导入 Postman 或 Apifox）

| 文件 | 用途 |
|------|------|
| `Q3-SP4-四需求-验收.postman_collection.json` | 集合（P0 冒烟 + P1 按XMind，约 100 条） |
| `Q3-SP4-四需求-验收.postman_environment.json` | 沙箱 canary 环境变量 |

重建：`node build_postman.js`
