# Launchd Service Deployment

Deploy TerminalBot as a launchd user agent on macOS.

## Prerequisites

- macOS
- Python 3.10+, tmux, and uv installed
- Configured `.env` file

## Installation

1. **Edit the plist file** to match your installation path:
   ```bash
   nano install/fallback/launchd/com.terminalbot.plist
   ```

   Update paths if TerminalBot is not in `~/terminal-bot`.

2. **Copy the plist file**:
   ```bash
   cp install/fallback/launchd/com.terminalbot.plist ~/Library/LaunchAgents/
   ```

3. **Load the service**:
   ```bash
   launchctl load ~/Library/LaunchAgents/com.terminalbot.plist
   ```

The bot will start automatically and restart if it crashes.

## Management Commands

### Status and Control

```bash
# Check if service is loaded
launchctl list | grep terminalbot

# Start service
launchctl start com.terminalbot

# Stop service
launchctl stop com.terminalbot

# Unload service (disable)
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist

# Reload service (after editing plist)
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist
launchctl load ~/Library/LaunchAgents/com.terminalbot.plist
```

### Logs

```bash
# View output logs
tail -f ~/terminal-bot/logs/output.log

# View error logs
tail -f ~/terminal-bot/logs/error.log

# View system logs
log stream --predicate 'processImagePath contains "terminalbot"'
```

## Configuration

The plist file includes:
- **KeepAlive**: Service restarts automatically if it crashes
- **RunAtLoad**: Service starts at login
- **Logging**: Captured to `logs/output.log` and `logs/error.log`

To modify settings, edit `~/Library/LaunchAgents/com.terminalbot.plist` and reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist
launchctl load ~/Library/LaunchAgents/com.terminalbot.plist
```

## Troubleshooting

### Service fails to start
Check error logs:
```bash
cat ~/terminal-bot/logs/error.log
```

Common issues:
- Incorrect paths in plist file
- `.env` file missing or invalid
- `uv` not in PATH (add to EnvironmentVariables in plist)

### Service not starting at login
Ensure plist is in correct location:
```bash
ls -l ~/Library/LaunchAgents/com.terminalbot.plist
```

Verify it's loaded:
```bash
launchctl list | grep terminalbot
```

### Find uv path for plist
If `uv` is not in standard PATH, find it:
```bash
which uv
```

Add its directory to PATH in the plist EnvironmentVariables.

## Uninstall

```bash
# Unload service
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist

# Remove plist file
rm ~/Library/LaunchAgents/com.terminalbot.plist
```
