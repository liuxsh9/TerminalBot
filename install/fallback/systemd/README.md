# Systemd Service Deployment

Deploy TerminalBot as a systemd user service on Linux.

## Prerequisites

- Linux with systemd
- Python 3.10+, tmux, and uv installed
- Configured `.env` file

## Installation

1. **Copy the service file**:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp install/fallback/systemd/terminalbot.service ~/.config/systemd/user/
   ```

2. **Edit the service file** to match your installation path:
   ```bash
   nano ~/.config/systemd/user/terminalbot.service
   ```

   Update `WorkingDirectory` and paths if TerminalBot is not in `~/terminal-bot`.

3. **Reload systemd**:
   ```bash
   systemctl --user daemon-reload
   ```

4. **Enable and start the service**:
   ```bash
   systemctl --user enable terminalbot
   systemctl --user start terminalbot
   ```

5. **Enable lingering** (to keep service running after logout):
   ```bash
   loginctl enable-linger $USER
   ```

## Management Commands

### Status and Control

```bash
# Check status
systemctl --user status terminalbot

# Start service
systemctl --user start terminalbot

# Stop service
systemctl --user stop terminalbot

# Restart service
systemctl --user restart terminalbot

# Disable auto-start
systemctl --user disable terminalbot
```

**Note:** The `/shutdown` command in the bot will cleanly exit without triggering an automatic restart (systemd only restarts on failures). Use `systemctl --user start terminalbot` to restart the bot after shutdown.

### Logs

```bash
# View logs (live tail)
journalctl --user -u terminalbot -f

# View last 100 lines
journalctl --user -u terminalbot -n 100

# View logs since boot
journalctl --user -u terminalbot -b
```

## Configuration

The service file includes:
- **Auto-restart**: On failure, with 5-second delay
- **Memory limit**: 500MB max
- **Logging**: Captured by systemd journal
- **Environment**: Loaded from `.env` file

To modify settings, edit `~/.config/systemd/user/terminalbot.service` and reload:
```bash
systemctl --user daemon-reload
systemctl --user restart terminalbot
```

## Troubleshooting

### Service fails to start
Check logs for errors:
```bash
journalctl --user -u terminalbot -n 50
```

Common issues:
- Incorrect `WorkingDirectory` path
- `.env` file missing or invalid
- `uv` not in PATH

### Service stops after logout
Enable lingering:
```bash
loginctl enable-linger $USER
```

### Service not starting on boot
Ensure service is enabled:
```bash
systemctl --user enable terminalbot
```

## Uninstall

```bash
# Stop and disable service
systemctl --user stop terminalbot
systemctl --user disable terminalbot

# Remove service file
rm ~/.config/systemd/user/terminalbot.service

# Reload systemd
systemctl --user daemon-reload
```
