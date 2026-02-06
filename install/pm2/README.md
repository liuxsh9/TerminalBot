# PM2 Deployment

PM2 is the recommended deployment method for TerminalBot. It provides automatic restarts, memory management, log rotation, and boot startup across Linux, macOS, and WSL.

## Prerequisites

- Node.js (v14 or later)
- PM2 installed globally: `npm install -g pm2`

## Installation

1. **Install PM2** (if not already installed):
   ```bash
   npm install -g pm2
   ```

2. **Start the bot**:
   ```bash
   cd /path/to/terminal-bot
   pm2 start install/pm2/ecosystem.config.js
   ```

3. **Save PM2 configuration**:
   ```bash
   pm2 save
   ```

4. **Enable auto-start on boot**:
   ```bash
   pm2 startup
   # Follow the instructions printed by PM2
   ```

## Management Commands

### Status and Monitoring

```bash
# Check bot status
pm2 status

# View detailed info
pm2 info terminalbot

# Monitor in real-time
pm2 monit
```

### Logs

```bash
# View logs (live tail)
pm2 logs terminalbot

# View only errors
pm2 logs terminalbot --err

# View last 100 lines
pm2 logs terminalbot --lines 100

# Clear logs
pm2 flush
```

### Control

```bash
# Restart bot
pm2 restart terminalbot

# Stop bot
pm2 stop terminalbot

# Delete from PM2
pm2 delete terminalbot
```

**Note:** The `/shutdown` command in the bot will trigger a restart after ~5s due to PM2's auto-restart feature. To truly stop the bot, use `/new` or `/connect` to open a terminal session, then run `pm2 stop terminalbot` from within that session.

## Log Files

Logs are stored in:
- **Output**: `./logs/output.log`
- **Errors**: `./logs/error.log`

PM2 automatically rotates logs to prevent disk space issues.

## Configuration

The PM2 configuration is defined in `ecosystem.config.js`:
- **Auto-restart**: Enabled (max 10 restarts, 5s delay)
- **Memory limit**: 500MB (restart if exceeded)
- **Min uptime**: 10s (to count as successful start)

To modify these settings, edit `ecosystem.config.js` and restart with `pm2 restart terminalbot`.

## Troubleshooting

### Bot keeps restarting
Check logs for errors:
```bash
pm2 logs terminalbot --err
```

Common issues:
- `.env` file missing or misconfigured
- Telegram token invalid
- Python/uv not in PATH

### PM2 command not found
Ensure PM2 is installed globally:
```bash
npm install -g pm2
```

Add npm global bin to PATH:
```bash
export PATH="$(npm config get prefix)/bin:$PATH"
```

### Auto-start not working
Re-run PM2 startup command:
```bash
pm2 startup
pm2 save
```

## Uninstall

To remove PM2 deployment:
```bash
pm2 delete terminalbot
pm2 save
```

To remove PM2 startup:
```bash
pm2 unstartup
```
