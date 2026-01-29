# CCBot

Control your tmux terminal sessions remotely via Telegram.

## Features

- **Real-time Output** - Stream terminal output to your phone
- **Text Input** - Send commands and text to terminal
- **Control Keys** - Arrow keys, Tab, Esc, Ctrl+C, Backspace, Enter
- **Input Modes** - Auto (with Enter) or Wait (manual Enter)
- **Session Selection** - Interactive pane picker via inline keyboard
- **User Authentication** - Whitelist-based access control

## Requirements

- Python 3.10+
- tmux
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

## Installation

```bash
git clone https://github.com/user/CCBot.git
cd CCBot

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

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
```

## Usage

1. **Start a tmux session:**
   ```bash
   tmux new -s dev
   ```

2. **Run CCBot:**
   ```bash
   source .venv/bin/activate
   python -m src.main
   ```

3. **In Telegram, message your bot:**
   - `/start` - Welcome and quick start guide
   - `/list` - Show available tmux panes
   - `/connect` - Select a pane to connect
   - `/keys` - Show control keys panel
   - `/disconnect` - Disconnect from session

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and quick start |
| `/help` | Show detailed help |
| `/list` | List available tmux panes |
| `/connect` | Connect to a pane (interactive) |
| `/disconnect` | Disconnect from session |
| `/keys` | Show control keys panel |

## Control Keys

The `/keys` command shows an inline keyboard with:

| Key | Function |
|-----|----------|
| ⬅️⬆️⬇️➡️ | Arrow keys |
| ⌫ | Backspace |
| ⏎ | Enter |
| Tab | Tab |
| ⇧Tab | Shift+Tab |
| Esc | Escape |
| ^C | Ctrl+C |
| ^C^C | Double Ctrl+C |
| Auto/Wait | Toggle input mode |

## Input Modes

- **Auto** (default): Messages are sent with Enter automatically
- **Wait**: Messages are sent without Enter - press ⏎ manually

Toggle between modes using the Auto/Wait button in the control keys panel.

## Pane Identifier Format

Panes are identified as `session:window.pane`:
- `dev:0.0` - Session "dev", window 0, pane 0
- `main:1.2` - Session "main", window 1, pane 2

## Tips

- Unknown `/commands` are forwarded to terminal when connected (e.g., `/help` in CLI apps)
- Use Wait mode for multi-line input or when you need precise control
- The terminal window shows the last 30 lines of output

## License

MIT
