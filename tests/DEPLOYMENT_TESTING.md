# Deployment Testing Guide

This guide helps verify all deployment methods work correctly.

## Prerequisites

- Configured `.env` file with valid `TELEGRAM_BOT_TOKEN` and `AUTHORIZED_USERS`
- All dependencies installed (`uv sync`)

## 14.2: Sleep Detection Test

**Manual Test (Required):**

1. Start the bot:
   ```bash
   uv run terminalbot
   ```

2. Watch the logs for "Bot is running"

3. Put your computer to sleep for >60 seconds

4. Wake the computer

5. Check logs for:
   ```
   System sleep detected (time jump: XXX.Xs). Triggering reconnection...
   Reconnection successful after sleep
   ```

**Expected:** Bot detects sleep and automatically reconnects to Telegram.

---

## 14.3: PM2 Deployment Test (Linux)

**Environment:** Linux with Node.js installed

```bash
# 1. Install PM2
npm install -g pm2

# 2. Deploy
pm2 start install/pm2/ecosystem.config.js

# 3. Verify running
pm2 status
# Expected: terminalbot shown as "online"

# 4. Check logs
pm2 logs terminalbot --lines 20
# Expected: "Bot is running" message

# 5. Test restart
pm2 restart terminalbot
# Expected: Restarts without errors

# 6. Test crash recovery
pm2 delete terminalbot
pm2 start install/pm2/ecosystem.config.js
kill -9 $(pm2 pid terminalbot)
sleep 6
pm2 status
# Expected: Bot auto-restarted

# 7. Cleanup
pm2 delete terminalbot
```

---

## 14.4: PM2 Deployment Test (macOS)

**Environment:** macOS with Node.js installed

Same as 14.3 above - PM2 is cross-platform.

Additional macOS test:
```bash
# Test with launchctl compatibility
pm2 startup
# Follow instructions, then:
pm2 save
# Logout and login
pm2 list
# Expected: terminalbot still running
```

---

## 14.5: Systemd Service Test (Linux)

**Environment:** Linux with systemd

```bash
# 1. Get project directory
PROJECT_DIR=$(pwd)

# 2. Install service
mkdir -p ~/.config/systemd/user
cp install/fallback/systemd/terminalbot.service ~/.config/systemd/user/
sed -i "s|%h/terminal-bot|$PROJECT_DIR|g" ~/.config/systemd/user/terminalbot.service

# 3. Enable and start
systemctl --user daemon-reload
systemctl --user enable terminalbot
systemctl --user start terminalbot

# 4. Verify running
systemctl --user status terminalbot
# Expected: "active (running)"

# 5. Check logs
journalctl --user -u terminalbot -n 20
# Expected: "Bot is running"

# 6. Test restart
systemctl --user restart terminalbot
systemctl --user status terminalbot
# Expected: Restarted successfully

# 7. Test crash recovery
systemctl --user kill -s KILL terminalbot
sleep 6
systemctl --user status terminalbot
# Expected: Auto-restarted (RestartSec=5)

# 8. Test boot startup
loginctl enable-linger $USER
# Reboot system
# After reboot:
systemctl --user status terminalbot
# Expected: Running automatically

# 9. Cleanup
systemctl --user stop terminalbot
systemctl --user disable terminalbot
rm ~/.config/systemd/user/terminalbot.service
```

---

## 14.6: Launchd Service Test (macOS)

**Environment:** macOS

```bash
# 1. Get project directory
PROJECT_DIR=$(pwd)

# 2. Install plist
cp install/fallback/launchd/com.terminalbot.plist ~/Library/LaunchAgents/
sed -i '' "s|~/terminal-bot|$PROJECT_DIR|g" ~/Library/LaunchAgents/com.terminalbot.plist

# 3. Load service
launchctl load ~/Library/LaunchAgents/com.terminalbot.plist

# 4. Verify running
launchctl list | grep terminalbot
# Expected: Process ID shown

# 5. Check logs
tail -20 logs/output.log
# Expected: "Bot is running"

# 6. Test restart
launchctl stop com.terminalbot
sleep 2
launchctl list | grep terminalbot
# Expected: Restarted automatically (KeepAlive)

# 7. Test crash recovery
kill -9 $(launchctl list | grep terminalbot | awk '{print $1}')
sleep 2
launchctl list | grep terminalbot
# Expected: Auto-restarted

# 8. Test login startup
# Logout and login
launchctl list | grep terminalbot
# Expected: Running automatically (RunAtLoad)

# 9. Cleanup
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist
rm ~/Library/LaunchAgents/com.terminalbot.plist
```

---

## 14.7: Installation Script Test

**Test environments:**

### Environment 1: Node.js + PM2 available
```bash
./install/install.sh
# Expected: Recommends PM2, offers installation
# Select PM2 method
# Verify: pm2 status shows bot running
pm2 delete terminalbot
```

### Environment 2: Node.js but no PM2
```bash
# Uninstall PM2 temporarily: npm uninstall -g pm2
./install/install.sh
# Expected: Offers to install PM2
# Select "install PM2" option
# Verify: PM2 installs and bot starts
pm2 delete terminalbot
```

### Environment 3: Linux no Node.js (systemd available)
```bash
# On Linux without Node.js
./install/install.sh
# Expected: Recommends systemd
# Select systemd
# Verify: systemctl --user status terminalbot
systemctl --user stop terminalbot
systemctl --user disable terminalbot
```

### Environment 4: macOS no Node.js
```bash
# On macOS without Node.js
./install/install.sh
# Expected: Recommends launchd
# Select launchd
# Verify: launchctl list | grep terminalbot
launchctl unload ~/Library/LaunchAgents/com.terminalbot.plist
```

### Environment 5: Fallback
```bash
./install/install.sh --fallback
# Expected: Sets up restart script
# Run: ./install/fallback/run_bot.sh
# Verify: Bot starts and logs to logs/bot.log
# Ctrl+C to stop
```

---

## 14.8: Backward Compatibility Test

✅ **PASSED** - Verified that `uv run terminalbot` works without deployment scripts.

```bash
# Quick test
uv run terminalbot &
BOT_PID=$!
sleep 3
kill $BOT_PID
# Expected: Bot starts and stops cleanly
```

---

## Quick Verification Checklist

After implementation, verify:

- [x] Retry logic works with network simulation
- [ ] Sleep detection triggers reconnection (manual test required)
- [ ] PM2 deployment works on Linux
- [ ] PM2 deployment works on macOS
- [ ] Systemd service works on Linux
- [ ] Launchd service works on macOS
- [ ] Installation script detects environment correctly
- [x] Manual `uv run terminalbot` still works

---

## Automated Test Suite

Run all automated tests:
```bash
# Retry logic tests
PYTHONPATH=$(pwd) python3 tests/test_retry.py

# Backward compatibility
python3 -c "
import subprocess, signal, time
p = subprocess.Popen(['uv', 'run', 'terminalbot'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2)
p.send_signal(signal.SIGTERM)
p.communicate(timeout=2)
print('✓ Manual start works' if p.returncode in [0, 143] else '✗ Failed')
"
```

Expected: All tests pass.
