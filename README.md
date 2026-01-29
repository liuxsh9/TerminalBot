# TerminalBot

Control your tmux terminal sessions remotely via Telegram. Perfect for monitoring long-running tasks, managing servers, or using CLI tools like Claude Code from your phone.

## Features

- **Real-time Output** - Stream terminal output to Telegram
- **Text Input** - Send commands and text to terminal
- **Control Keys** - Arrow keys, Tab, Esc, Ctrl+C, Backspace, Enter
- **Input Modes** - Auto (with Enter) or Wait (manual Enter)
- **Mobile Friendly** - Resize terminal width for phone screens
- **Session Management** - Create new sessions or connect to existing ones
- **User Authentication** - Whitelist-based access control

## Requirements

- Python 3.10+
- tmux
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Installation

```bash
git clone https://github.com/liuxsh9/TerminalBot.git
cd TerminalBot

# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Configure
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Edit `.env`:

```bash
# Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Your Telegram user ID (get from @userinfobot)
# Multiple users: comma-separated (123,456,789)
AUTHORIZED_USERS=123456789

# Terminal polling interval in seconds (default: 1)
POLL_INTERVAL=1

# Number of terminal lines to display (default: 30)
TERMINAL_LINES=30

# Default working directory for new sessions (default: ~)
DEFAULT_WORK_DIR=~
```

## Usage

```bash
uv run terminalbot
```

Then in Telegram:

1. `/new` - Create a new tmux session
2. `/connect` - Or connect to an existing session
3. Send text to input to terminal
4. `/keys` - Show control keys panel
5. `/resize 60` - Optimize width for mobile

## Bot Commands

| Command | Description |
|---------|-------------|
| `/new [name]` | Create new tmux session and connect |
| `/list` | List available tmux panes |
| `/connect` | Connect to a pane (interactive) |
| `/resize <width>` | Set terminal width (e.g., `/resize 60`) |
| `/refresh` | Refresh terminal display |
| `/disconnect` | Disconnect from session |
| `/start` | Welcome message |
| `/keys` | Show control keys panel |
| `/help` | Show detailed help |

## Control Keys

The `/keys` command shows an inline keyboard:

```
[Esc] [⬆️] [⌫]  [⏎]
[⬅️]  [⬇️] [➡️] [Tab]
[^C] [^C^C] [⇧Tab] [Auto]
```

## Resize Options

The `/resize` command shows preset width options:

```
[30] [60] [80]
[90] [120] [Reset]
```

Or use directly: `/resize 70`

## Input Modes

- **Auto** (default): Messages sent with Enter automatically
- **Wait**: Messages sent without Enter - press ⏎ manually

Toggle using the Auto/Wait button in the control keys panel.

## Tips

- Use `/resize 60` for comfortable mobile viewing
- Unknown `/commands` are forwarded to terminal when connected
- Use Wait mode for multi-line input or precise control

## License

MIT
