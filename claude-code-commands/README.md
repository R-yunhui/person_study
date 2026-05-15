# Claude Code 命令大全

> 版本：2026年5月版 | 基于 [官方文档](https://code.claude.com/docs/en/commands) + 社区实践整理
>
> 来源：https://code.claude.com/docs/en/commands、https://code.claude.com/docs/en/cli-reference、https://github.com/luongnv89/claude-howto

---

## 目录

1. [CLI 启动命令](#一cli-启动命令)
2. [会话内斜杠命令（完整 60+ 个）](#二会话内斜杠命令)
3. [捆绑技能](#三捆绑-skill-5-个)
4. [MCP 提示词命令](#四mcp-提示词命令)
5. [键盘快捷键](#五键盘快捷键)
6. [输入超能力](#六输入超能力)
7. [按使用场景速查](#七按使用场景速查)
8. [自定义命令（Skills）](#八自定义-command-skills)
9. [版本变更历史](#九cli-版本变更历史)

---

## 一、CLI 启动命令

在终端中使用，非会话内命令。

### 基本启动

| 命令 | 说明 | 场景 |
|------|------|------|
| `claude` | 启动交互式 REPL 会话 | 日常开发 |
| `claude "描述任务"` | 带初始提示启动 | 开局就交代任务，省一轮 |
| `claude -p "查询"` | **打印模式**：单次查询后立即退出 | 脚本/CI 集成 |
| `claude -c` | 继续最近一次会话 | 中断后回来接着干 |
| `claude -r "会话名"` | 按名称恢复指定会话 | 多任务上下文切换 |
| `claude -w "指令"` | 在隔离的 git worktree 中启动 | 安全实验，不污染主分支 |
| `claude update` | 更新到最新版本 | 定期升级 |

### 高级启动标志

| 标志 | 说明 | 场景 |
|------|------|------|
| `--model <模型ID>` | 指定模型启动 | `claude --model claude-opus-4` |
| `--max-turns N` | 限制最大交互轮数 | CI 中的安全断路器 |
| `--allowedTools "Read" "Write"` | 允许特定工具，跳过确认 | 自动化场景 |
| `--disallowedTools "Bash(rm *)"` | 禁止特定工具 | 安全限制 |
| `--add-dir <路径>` | 添加额外工作目录 | 跨项目工作 |
| `--output-format <text\|json\|stream-json>` | 设置输出格式 | 脚本解析输出 |
| `--input-format <text\|stream-json>` | 设置输入格式 | 管道输入处理 |
| `--fork-session` | 分叉会话，保留完整上下文 | 并行探索方案 |
| `--from-pr <编号>` | 从 GitHub PR 恢复 | CI 代码审查 |
| `--resume <会话ID>` | 恢复指定会话 | 精确恢复 |
| `--verbose` | 启用详细日志 | 调试自身问题 |
| `--dangerously-skip-permissions` | 跳过所有权限确认 | **完全信任的自动化用（慎用！）** |

### 管道与组合

```bash
# 分析日志
tail -200 app.log | claude -p "分析这些错误"

# 批量代码审查
git diff main --name-only | claude -p "审查这些文件的安全问题"

# 自动化翻译
claude -p "将新字符串翻译成法语并提 PR"
```

---

## 二、会话内斜杠命令

### 新手必学（最常用）

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/help`** | 显示所有可用命令（含自定义） | **第一个要记住的命令** |
| **`/clear [名称]`** | 清空对话，全新开始 | **切换任务时必用**。旧上下文会拖累新任务。别名 `/reset` `/new` |
| **`/compact [指令]`** | 压缩对话历史释放上下文 | **上下文快满时用**。可加指令：`/compact 保留数据库 schema` |
| **`/model [模型]`** | 切换模型 | **省钱核心**：Sonnet 日常、Opus 复杂问题 |
| **`/diff`** | 交互式 diff 查看器 | **提交前必看改动**。左右切换 git diff/逐轮 diff，上下翻文件 |
| **`/plan [描述]`** | 进入计划模式（只读，先出方案再执行） | 关键操作前先看方案 |
| **`/status`** | 显示版本/模型/账号/连接状态 | 排查问题时了解环境 |
| **`/cost`** | 查看 Token 用量/费用（别名，指向 `/usage`） | 定期检查了解消耗 |

### 日常效率（高频）

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/memory`** | 编辑 CLAUDE.md 记忆文件 | 增删项目规则、查看自动记忆 |
| **`/init`** | 初始化 CLAUDE.md 项目指引 | **每个新项目第一步** |
| **`/rename [名称]`** | 重命名会话 | 不加参数自动生成。有意义的名字方便恢复 |
| **`/resume [会话]`** | 恢复之前会话 | 日常上下文切换。别名 `/continue` |
| **`/context [all]`** | 可视化上下文使用（彩色网格+优化建议） | 感觉"健忘"时先查这个 |
| **`/btw [问题]`** | 侧边提问，不污染主对话 | 调试中突然想查概念，问完继续干活 |
| **`/voice [hold\|tap\|off]`** | 语音输入（按住空格说话） | 不想打字时，支持 20+ 语言 |
| **`/fast [on\|off]`** | 切换快速模式 | Opus 用户做简单编辑时开启 |
| **`/effort [级别\|auto]`** | 设置思考深度 | `low`→简单格式化 `medium`→`high`→`xhigh`→`max`(Opus 4.7)。`auto` 恢复默认 |

### 高级效率（高手向）

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/goal [条件\|clear]`** | 设目标：Claude 持续工作直到条件满足 | 让 Claude 自动循环直到条件达成 |
| **`/branch [名称]`** | 创建对话分支/分叉 | 想探索不同方案不丢原路。别名 `/fork` |
| **`/rewind`** | 回退对话和/或代码到之前状态 | 走错路了选择性回退。别名 `/checkpoint` `/undo` |
| **`/export [文件名]`** | 导出对话为纯文本 | 写复盘文档、分享输出给队友 |
| **`/copy [N]`** | 复制上次回复到剪贴板 | 按 `w` 改写入文件而非剪贴板（SSH 时有用） |
| **`/recap`** | 生成当前会话的一行摘要 | 离开回来后快速了解上下文 |
| **`/focus`** | 切换聚焦视图（只看最近提示+工具摘要+回复） | 长会话中减少信息噪音 |
| **`/tui [default\|fullscreen]`** | 切换全屏无闪烁渲染模式 | 追求沉浸式体验 |
| **`/color [颜色\|default]`** | 设置提示栏颜色 | 多会话用颜色区分。不加参数随机颜色 |
| **`/statusline [描述]`** | 配置底部状态栏 | 显示你想要的信息 |

### 代码审查与质量

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/review [PR]`** | 本地 PR 审查 | 审查当前分支变更 |
| **`/security-review`** | 安全漏洞专项审查 | **涉及认证/数据/外部集成时必用** |
| **`/ultrareview [PR]`** | 云端多 Agent 深度代码审查 | 需要深度审查时（Pro/Max 有 3 次免费） |

### 项目配置

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/config`** | 设置界面（主题/模型/输出风格等） | 别名 `/settings` |
| **`/permissions`** | 管理工具权限 | 安全敏感环境限制爆破半径。别名 `/allowed-tools` |
| **`/hooks`** | 查看钩子配置 | 自动化触发器的管理 |
| **`/mcp`** | 管理 MCP 服务器连接 | 接入数据库/API/文件系统等外部工具 |
| **`/agents`** | 管理子代理配置 | 创建专用 Agent（代码审查员、调试员） |
| **`/skills`** | 列出可用技能 | 按 `t` 按 token 排序，按 `Space` 隐藏不用的 |
| **`/plugin`** | 管理插件 | 安装、卸载、浏览 |
| **`/reload-plugins`** | 重新加载所有插件 | 修改插件配置后无需重启 |
| **`/keybindings`** | 打开快捷键配置 | 自定义快捷键 |
| **`/theme`** | 更换颜色主题 | 含亮/暗/色盲友好/ANSI/自定义主题 |
| **`/terminal-setup`** | 配置终端快捷键 | Shift+Enter 换行不好用时先跑 |
| **`/sandbox`** | 切换沙箱模式 | 安全隔离环境 |
| **`/add-dir <路径>`** | 添加额外工作目录 | 需要访问其他目录的文件 |

### 代理与自动化

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/background [提示]`** | 当前会话转后台 Agent，释放终端 | 别名 `/bg` |
| **`/tasks`** | 列出管理后台任务 | 别名 `/bashes` |
| **`/schedule [描述]`** | 创建定时任务（云端基础设施运行） | 定期执行重复工作。别名 `/routines` |
| **`/autofix-pr [提示]`** | 云端会话自动修复 PR 的 CI 失败 | 合 PR 前让 Claude 盯着，CI 失败自动修 |
| **`/stop`** | 停止当前后台会话 | 只停止不删除 |

### 跨设备与远程

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/remote-control`** | 从 claude.ai 远程控制本机会话 | 离开电脑也能继续。别名 `/rc` |
| **`/teleport`** | 把 Web 会话拉到本机终端 | 从网页版/手机端切回命令行。别名 `/tp` |
| **`/desktop`** | 切换到桌面版 | 需要图形化 diff 审查。别名 `/app` |
| **`/mobile`** | 显示手机端二维码 | 出门在外继续。别名 `/ios` `/android` |
| **`/chrome`** | 配置 Chrome 浏览器集成 | 调试 Web 应用 |
| **`/ide`** | 管理 IDE 集成状态 | 查看 VS Code/JetBrains 连接状态 |
| **`/remote-env`** | 配置 Web 会话的默认远程环境 | 设置云端环境 |

### 集成

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/install-github-app`** | 安装 GitHub Actions App | CI 自动化 |
| **`/install-slack-app`** | 安装 Slack App | 团队协作 |
| **`/web-setup`** | 用本地 gh CLI 连接 GitHub 账号 | Web 版 Claude Code 的设置 |

### 用量与账户

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/usage`** | 综合用量面板（限额/费用/统计三合一） | `/cost` 和 `/stats` 是其别名 |
| **`/extra-usage`** | 配置超额使用 | 不想被限流中断 |
| **`/insights`** | 生成使用分析 HTML 报告 | 每月一次，了解自己的工作模式 |
| **`/privacy-settings`** | 隐私设置 | Pro/Max 用户调整数据偏好 |
| **`/login`** | 登录 | 切换账号 |
| **`/logout`** | 登出 | 共享机器时 |
| **`/upgrade`** | 打开升级页面 | 当前计划不够用 |
| **`/passes`** | 分享免费周（限有资格用户） | 邀请朋友 |
| **`/stickers`** | 订购 Claude Code 贴纸 | 真好玩 |

### 诊断与支持

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/doctor`** | 诊断安装和配置 | **出问题先跑这个**。按 `f` 自动修复 |
| **`/debug [描述]`** | 启用调试日志并分析 | 排查难复现的 bug |
| **`/feedback [报告]`** | 提交反馈 | 遇到 bug。别名 `/bug` |
| **`/release-notes`** | 查看更新日志 | 了解新功能 |
| **`/heapdump`** | 写 JS 堆快照到桌面 | 诊断高内存使用 |
| **`/powerup`** | 交互式新功能学习（含动画演示） | 探索不熟悉的功能 |
| **`/team-onboarding`** | 生成队友上手指南 | 新成员快速了解项目设置 |
| **`/setup-bedrock`** | 配置 Amazon Bedrock | 需 `CLAUDE_CODE_USE_BEDROCK=1` |
| **`/setup-vertex`** | 配置 Google Vertex AI | 需 `CLAUDE_CODE_USE_VERTEX=1` |

### 趣味

| 命令 | 说明 |
|------|------|
| **`/radio`** | 在浏览器中打开 Claude FM 轻音乐电台（Bedrock/Vertex 不可用） |

### 已移除/废弃

| 命令 | 状态 | 替代 |
|------|------|------|
| `/review` | 废弃 | `code-review` 插件 |
| `/pr-comments` | v2.1.91 移除 | 直接问 Claude |
| `/vim` | v2.1.92 移除 | `/config` → Editor mode |
| `/output-style` | v2.1.73 废弃 | `/config` |
| `/fork` | 已重命名 | `/branch`（别名仍可用） |

---

## 三、捆绑 Skill（5 个）

这些是预装在 Claude Code 中的高级工作流：

| 命令 | 说明 | 场景 |
|------|------|------|
| **`/batch <指令>`** | 将大规模变更分解为 5-30 个独立单元，每个在隔离 worktree 中并行执行并提 PR | 跨代码库大规模重构。例：`/batch 将 src/ 从 Solid 迁移到 React` |
| **`/simplify [焦点]`** | 三方并行审查（架构/质量/效率）→ 汇总 → 自动修复 | **每个功能完成后的质量门**。`/simplify 关注内存效率` |
| **`/debug [描述]`** | 启用调试日志并分析会话日志 | 排查难复现的 bug |
| **`/loop [间隔] [提示]`** | 重复执行提示。无间隔则自定节奏 | 轮询部署/监控 PR。`/loop 5m 检查部署完成了吗`。别名 `/proactive` |
| **`/claude-api [migrate\|managed-agents-onboard]`** | 加载 Claude API/Agent SDK 参考 | 开发 Claude API 时自动提供参考。`migrate` 可升级代码到新模型 |
| **`/fewer-permission-prompts`** | 扫描日志 → 自动添加到允许列表 | 减少权限提示弹窗 |

---

## 四、MCP 提示词命令

MCP 服务器暴露的提示词以命令形式出现：

```
/mcp__<服务器名>__<提示词名>
```

示例：`/mcp__github__list_prs`、`/mcp__jira__create_issue`

---

## 五、键盘快捷键

| 快捷键 | 功能 | 场景 |
|--------|------|------|
| **`!` + 命令** | 直接执行 Shell 命令，不经过 Claude | `!git status` 省 token |
| **`@` + 路径** | 智能文件路径补全 | `@src/components/Header.tsx` 直接引用 |
| **`Shift+Tab` / `Alt+M`** | 切换 Normal / Auto-Accept / Plan 模式 | 频繁切换模式时 |
| **`Esc` + `Esc`** | 打开回退菜单（可选回退代码/对话） | 比 `/rewind` 更快 |
| **`Alt+P`** | 切换模型（保留已输入内容） | 写到一半发现需要更强模型 |
| **`Alt+T`** | 切换扩展思考模式 | 下一轮需要深度推理时 |
| **`Ctrl+O`** | 切换 Verbose 模式，看 Claude 思考过程 | 想看推理步骤时 |

---

## 六、输入超能力

| 语法 | 说明 | 示例 |
|------|------|------|
| `@<文件路径>` | 引用文件 | `审查 @./src/auth.ts` |
| `@<目录路径>/` | 引用整个目录（递归） | `审查 @./src/api/` |
| `@<glob>` | glob 模式匹配文件 | `审查 @./src/**/*.test.ts` |
| `!<Shell命令>` | 执行 Shell 命令 | `!npm test` |
| `!`（单独一行） | 进入/退出 Shell 模式 | `!` → 执行多条命令 → `!` |
| 管道输入 | 从 stdin 传入内容 | `cat log \| claude -p "分析"` |

---

## 七、按使用场景速查

### 新手上路

```
/help         → 看所有命令
/init         → 初始化项目指引
/status       → 确认版本和连接
/doctor       → 如果出问题先诊断
```

### 日常开发流程

```
1. claude "实现XX功能"     → 启动或直接提需求
2. @引用文件                → 精确指定操作文件
3. !npm test                → 测试（省 token）
4. /diff                    → 检查改动
5. /simplify                → 质量检查+自动优化
6. /security-review         → 安全审查（敏感代码）
```

### 长会话管理

```
/context       → 看还剩多少上下文
/compact 保留X  → 压缩对话释放空间
/btw           → 侧边提问不占上下文
/clear         → 彻底清空开始新任务
```

### 省钱策略

```
/model sonnet  → 日常用 Sonnet
/model opus   → 复杂问题切 Opus
/compact      → 压缩上下文节省 token
/cost         → 监控消耗
/effort low   → 简单 task 降低思考深度
```

### 代码质量门禁（提交前）

```
/diff              → 看改了啥
/simplify          → 自动优化
/security-review   → 安全检查
/review            → 代码审查
/ultrareview       → 云端深度审查
```

### 大规模重构

```
/batch "将 X 迁移到 Y"   → 自动分解并行执行
```

### 远程/跨设备

```
/remote-control    → 让手机控制本机
/teleport          → 网页版拉到终端
/desktop           → 切到桌面版
/mobile            → 手机二维码
```

### 自动化

```
/schedule          → 定时任务（云端）
/loop 5m "检查"   → 轮询（本机会话内）
/autofix-pr        → PR 自动修复 CI 失败
/background        → 当前任务转后台
```

### 调试排查

```
/doctor            → 诊断工具自身
/debug "描述问题" → 深度调试
/feedback          → 报告 bug
/heapdump          → 内存问题诊断
```

### 团队协作

```
/team-onboarding   → 生成队友上手指南
/hooks             → 查看自动化钩子
/init (加环境变量)  → 交互式初始化含技能/钩子/记忆
```

---

## 八、自定义 Command（Skills）

> 自定义斜杠命令已被 Skills 取代。`.claude/commands/` 仍可用，但 `.claude/skills/` 是推荐方式。

### 创建步骤

创建 `.claude/skills/<name>/SKILL.md`：

```markdown
---
name: my-command
description: 什么时候用这个命令
argument-hint: [参数说明]
allowed-tools: Read, Bash(git *)
model: sonnet
disable-model-invocation: true   # 只允许用户手动调用
---

# 我的命令

## 动态上下文
- 当前分支：!`git branch --show-current`
- 相关文件：@package.json

## 指令
1. 第一步
2. 使用参数：$ARGUMENTS
3. 结束
```

### Frontmatter 字段完整参考

| 字段 | 用途 | 默认值 |
|------|------|--------|
| `name` | 命令名（变成 `/name`） | 目录名 |
| `description` | 描述，Claude 判断是否自动调用 | 第一段 |
| `argument-hint` | 参数提示 | 无 |
| `allowed-tools` | 允许的工具 | 继承 |
| `model` | 指定模型 | 继承 |
| `disable-model-invocation` | `true` 则仅用户可调用 | `false` |
| `user-invocable` | `false` 则从 `/` 菜单隐藏 | `true` |
| `context` | `fork` 则在独立子代理中运行 | 无 |
| `agent` | `context: fork` 时的代理类型 | `general-purpose` |
| `hooks` | 技能级钩子 | 无 |

### 参数使用

```markdown
# 所有参数：$ARGUMENTS
修复 issue #$ARGUMENTS

# 单个参数：$1, $2, $3...
审查 PR #$1，优先级 $2
```

### 动态上下文（Shell 命令）

在 frontmatter 之外用 `` !`command` `` 语法嵌入 Shell 输出：

```markdown
---
name: commit
description: 带上下文的 Git 提交
allowed-tools: Bash(git *)
---

## 上下文
- Git 状态：!`git status`
- 当前 diff：!`git diff HEAD`
- 当前分支：!`git branch --show-current`
- 最近提交：!`git log --oneline -5`

## 任务
根据以上变更创建提交。
```

---

## 九、CLI 版本变更历史

| 版本 | 变化 |
|------|------|
| v2.1.73 | `/output-style` 废弃 |
| v2.1.77 | `/fork` 重命名为 `/branch` |
| v2.1.91 | `/pr-comments` 移除 |
| v2.1.92 | `/vim` 移除，用 `/config` → Editor mode |
| v2.1.101 | `/team-onboarding` 新增 |
| v2.1.105 | `/proactive` 作为 `/loop` 别名 |
| v2.1.108 | `/recap`、`/undo` 新增 |
| v2.1.110 | `/focus`、`/tui` 新增 |
| v2.1.111 | `/ultrareview`、`/less-permission-prompts` 新增；`/effort` 增加 `xhigh` |
| v2.1.118 | `/usage` 统一面板；`/cost` 和 `/stats` 改为别名 |
| v2.1.128 | `/color` 不加参数随机颜色 |

---

> **最准的命令列表永远在你的终端里：**
> 会话内输入 `/` 即可看到所有可用命令（含自定义），输入 `/help` 看完整说明。
