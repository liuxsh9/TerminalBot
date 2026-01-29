# CCBot - Telegram Terminal Controller

Control your terminal/tmux sessions remotely via Telegram.

## Features

- View real-time terminal output on your phone
- Send text input to terminal from Telegram
- Connect to any tmux session/window/pane
- User authentication via whitelist
- Output buffering to prevent message flooding

## Requirements

- Python 3.10+
- tmux
- Telegram Bot Token (from @BotFather)

## Installation

1. Clone the repository:
   ```bash
   git clone <repo-url>
   cd CCBot
   ```

2. Create virtual environment and install:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

## Configuration

Edit `.env` file:

```bash
# Get from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Your Telegram user ID (get from @userinfobot)
AUTHORIZED_USERS=123456789

# Polling interval in seconds (default: 1)
POLL_INTERVAL=1
```

## Usage

1. Start a tmux session:
   ```bash
   tmux new -s mysession
   # Run your command, e.g., claude
   ```

2. Start CCBot (in another terminal):
   ```bash
   source .venv/bin/activate
   python -m src.main
   ```

3. In Telegram, message your bot:
   - `/start` - Welcome message
   - `/list` - Show available tmux panes
   - `/connect mysession:0.0` - Connect to a pane
   - Send any text - Forwards to terminal
   - `/disconnect` - Disconnect from session

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Show welcome message |
| `/help` | Show help |
| `/list` | List available tmux sessions |
| `/connect <id>` | Connect to a tmux pane |
| `/disconnect` | Disconnect from current session |

## Pane Identifier Format

Panes are identified as `session:window.pane`:
- `mysession:0.0` - Session "mysession", window 0, pane 0
- `dev:1.2` - Session "dev", window 1, pane 2

## License

MIT
