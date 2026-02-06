# 生成 Cursor Rules 文件

根据用户的输入生成 `.mdc` 规则文件并保存到 `.cursor/rules/` 目录。

## 执行步骤

1. **获取用户输入**

   - 询问用户想要创建的规则文件名称（不含扩展名）
   - 询问用户规则的具体内容和要求

2. **生成规则文件内容**

   - 创建标准的 `.mdc` 文件格式
   - 包含 frontmatter（YAML 格式）：
     ```yaml
     ---
     description: [规则描述]
     globs: [可选的文件匹配模式，如 *.js,*.ts]
     alwaysApply: false
     ---
     ```
   - 根据用户输入生成规则内容

3. **保存文件**

   - 文件名格式：`[用户指定的名称].mdc`
   - 保存路径：`.cursor/rules/[文件名].mdc`
   - 如果文件已存在，询问用户是否覆盖

4. **确认完成**
   - 告知用户文件已生成
   - 显示文件路径

## 示例

用户输入："创建一个名为 'code-review' 的规则，用于代码审查"

生成文件：`.cursor/rules/code-review.mdc`

```yaml
---
description: 代码审查规则
globs: *.js,*.ts,*.py,*.java
alwaysApply: false
---

# 代码审查规则

[根据用户输入生成的规则内容]
```

## 注意事项

- 确保 frontmatter 格式正确（YAML）
- 文件名使用小写字母和连字符（kebab-case）
- 如果用户没有提供描述，根据规则内容自动生成描述
- 如果用户没有指定 globs，可以留空或根据规则内容推断合适的文件类型
