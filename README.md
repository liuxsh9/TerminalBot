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

### Quick Start (Manual)

```bash
uv run terminalbot
```

### Production Deployment (Recommended)

For long-running use, deploy with a process manager to ensure the bot stays running:

```bash
# Automated installation (detects environment and recommends best method)
./install/install.sh

# Or specify a method:
./install/install.sh --pm2        # PM2 (recommended, cross-platform)
./install/install.sh --systemd    # Linux with systemd
./install/install.sh --launchd    # macOS
./install/install.sh --fallback   # Simple restart script
```

See [Deployment](#deployment) section for details.

### Using the Bot

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

## Deployment

For production use, TerminalBot includes automatic restart, recovery from system sleep, and deployment configurations.

### Recommended: PM2 (Cross-platform)

PM2 provides automatic restarts, log management, and boot startup on Linux, macOS, and WSL.

**Quick Start:**
```bash
# Install Node.js and PM2
npm install -g pm2

# Deploy
pm2 start install/pm2/ecosystem.config.js
pm2 save
pm2 startup  # Enable auto-start on boot
```

**Management:**
```bash
pm2 status          # Check status
pm2 logs terminalbot # View logs
pm2 restart terminalbot # Restart
```

📖 [PM2 Deployment Guide](install/pm2/README.md)

### Alternative: System Services

#### Linux (systemd)
```bash
cp install/fallback/systemd/terminalbot.service ~/.config/systemd/user/
systemctl --user enable --now terminalbot
```

📖 [Systemd Guide](install/fallback/systemd/README.md)

#### macOS (launchd)
```bash
cp install/fallback/launchd/com.terminalbot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.terminalbot.plist
```

📖 [Launchd Guide](install/fallback/launchd/README.md)

### Fallback: Simple Restart Script

For environments without PM2 or system service managers:

```bash
# Run in foreground
./install/fallback/run_bot.sh

# Run in background
nohup ./install/fallback/run_bot.sh &
```

### Features

All deployment methods include:
- **Auto-restart on crash**: Bot restarts automatically if it fails
- **Sleep/wake recovery**: Detects system sleep and reconnects
- **Network resilience**: Automatic retry with exponential backoff
- **Memory limits**: Prevents resource exhaustion
- **Log management**: Centralized logging for troubleshooting

### Logs

| Method | Location |
|--------|----------|
| PM2 | `./logs/output.log`, `./logs/error.log` |
| systemd | `journalctl --user -u terminalbot -f` |
| launchd | `~/terminal-bot/logs/output.log` |
| Fallback script | `./logs/bot.log` |

## Troubleshooting

### Bot keeps restarting

Check logs for errors. Common issues:
- `.env` file misconfigured (missing TOKEN or USERS)
- Telegram token invalid
- Python/uv not in PATH

### Bot disconnects after system sleep

The bot automatically detects sleep and reconnects. If issues persist:
- Check logs for reconnection attempts
- Verify network connectivity after wake
- Consider using PM2 for additional recovery

### "Connection refused" or network errors

The bot includes automatic retry with exponential backoff:
- Transient errors: Retries automatically (1s, 2s, 4s, ... up to 5min)
- Check Telegram API status if persistent
- Verify internet connectivity

### Bot not starting on boot

**PM2:**
```bash
pm2 startup
pm2 save
```

**systemd:**
```bash
loginctl enable-linger $USER
systemctl --user enable terminalbot
```

**launchd:**
```bash
# Verify plist is in correct location
ls -l ~/Library/LaunchAgents/com.terminalbot.plist
```

### More Help

- Check deployment-specific README files in `install/` directory
- Review logs for detailed error messages
- Ensure all requirements are installed (Python 3.10+, tmux, uv)

## Tips

- Use `/resize 60` for comfortable mobile viewing
- Unknown `/commands` are forwarded to terminal when connected
- Use Wait mode for multi-line input or precise control

## License

MIT
