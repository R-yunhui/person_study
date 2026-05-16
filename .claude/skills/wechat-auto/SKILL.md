---
name: wechat-auto
description: 通过 CLI 操控微信发送消息/文件/图片。当用户要求给微信好友或群聊发送消息、文件、图片时，使用 uv run wechat-auto 命令。项目位于 D:\ryh\personal\study\wechat-auto-server。
---

# WeChat Auto CLI

通过 `uv run wechat-auto` 命令操控微信发送消息/文件/图片。

## 前置条件

- 微信（Weixin.exe）必须正在运行
- 虚拟环境位于 `D:\ryh\personal\study\.venv`
- 工作目录：`D:\ryh\personal\study`

## 命令

### 发送文本消息

```bash
uv run wechat-auto send "联系人" "消息内容"
```

### 在群聊中 @提及 某人

```bash
uv run wechat-auto mention "群名" "王鑫" "消息内容"
# @多人用逗号分隔
uv run wechat-auto mention "群名" "王鑫,李四" "大家好"
```

注意：此命令将群聊输入到输入框、@人名选择后，再发送消息；适合群聊中提醒特定成员。

### 发送文件（显示为文件图标）

```bash
uv run wechat-auto file "联系人" "D:\path\to\file.pdf"
```

### 发送图片（显示为缩略图）

```bash
uv run wechat-auto image "联系人" "D:\path\to\photo.jpg"
```

### 启动自动回复 Agent

```bash
uv run wechat-auto agent
```

### 调试控件树

```bash
uv run wechat-auto dump -n 20
```

## 注意事项

- 联系人名称写微信里显示的名字（好友名、群名）
- 路径中的中文需用引号包裹
- 发送文件/图片前确保路径存在
- 先拿"文件传输助手"测试
