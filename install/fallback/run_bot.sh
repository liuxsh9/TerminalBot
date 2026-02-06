#!/bin/bash
# Simple restart wrapper for TerminalBot
# Automatically restarts the bot if it crashes

cd "$(dirname "$0")/../.."
PROJECT_DIR="$(pwd)"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/bot.log"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "[$(date)] Starting TerminalBot restart wrapper..." | tee -a "$LOG_FILE"

while true; do
    echo "[$(date)] Starting TerminalBot..." | tee -a "$LOG_FILE"

    # Run the bot and capture exit code
    uv run terminalbot 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=$?

    echo "[$(date)] Bot exited with code $EXIT_CODE" | tee -a "$LOG_FILE"

    # If clean exit (code 0), don't restart
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date)] Clean exit detected, not restarting" | tee -a "$LOG_FILE"
        break
    fi

    # Otherwise, wait and restart
    echo "[$(date)] Restarting in 5 seconds..." | tee -a "$LOG_FILE"
    sleep 5
done

echo "[$(date)] TerminalBot restart wrapper stopped" | tee -a "$LOG_FILE"
