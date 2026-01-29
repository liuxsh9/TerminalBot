## Why

用户在使用 Claude Code 等终端应用时，经常需要离开电脑但仍想监控执行进度或补充需求。目前没有便捷的方式在手机上查看终端输出并与之交互，导致用户必须守在电脑前或错过重要的交互时机。

## What Changes

- 新增 Telegram Bot 服务，可连接到本地运行的终端/tmux 会话
- 实现终端输出的实时捕获和推送到 Telegram
- 支持通过 Telegram 发送文本输入到终端
- 提供会话管理功能（列出、选择、断开连接）

## Capabilities

### New Capabilities

- `telegram-bot`: Telegram Bot 核心服务，处理消息收发和用户认证
- `terminal-capture`: 终端/tmux 会话的输出捕获和输入注入
- `session-bridge`: 连接 Telegram 用户与终端会话的桥接层

### Modified Capabilities

(无现有 capabilities 需要修改)

## Impact

- **新增依赖**: python-telegram-bot 或类似库、libtmux/pty 相关库
- **系统要求**: 需要 tmux 或 pty 支持
- **网络**: 需要能访问 Telegram API（可能需要代理）
- **安全**: 需要 Bot Token 配置，建议限制授权用户
