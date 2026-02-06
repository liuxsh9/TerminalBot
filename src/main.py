#!/usr/bin/env python3
"""TerminalBot - Telegram bot for controlling terminal/tmux sessions remotely."""

import asyncio
import logging
import os
import sys
import time

from dotenv import load_dotenv
from src.retry_policy import RetryPolicy, is_transient_error

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        sys.exit(1)

    authorized_users_str = os.getenv("AUTHORIZED_USERS", "")
    authorized_users = set()
    if authorized_users_str:
        for user_id in authorized_users_str.split(","):
            user_id = user_id.strip()
            if user_id:
                authorized_users.add(int(user_id))

    if not authorized_users:
        logger.error("AUTHORIZED_USERS not set - refusing to start for security reasons")
        sys.exit(1)

    poll_interval = float(os.getenv("POLL_INTERVAL", "1"))
    terminal_lines = int(os.getenv("TERMINAL_LINES", "30"))
    default_work_dir = os.getenv("DEFAULT_WORK_DIR", "~")
    # Expand ~ to actual home directory
    default_work_dir = os.path.expanduser(default_work_dir)

    return {
        "token": token,
        "authorized_users": authorized_users,
        "poll_interval": poll_interval,
        "terminal_lines": terminal_lines,
        "default_work_dir": default_work_dir,
    }


async def run_bot(config: dict) -> None:
    """Run the Telegram bot with retry logic and sleep detection."""
    # Import here to avoid issues if dependencies not installed
    from src.telegram_bot import create_bot, BOT_COMMANDS
    from src.session_bridge import SessionBridge
    from src.terminal_capture import TerminalCapture

    terminal_capture = TerminalCapture()
    session_bridge = SessionBridge(
        terminal_capture=terminal_capture,
        poll_interval=config["poll_interval"],
        terminal_lines=config["terminal_lines"],
        default_work_dir=config["default_work_dir"],
    )
    application = create_bot(
        token=config["token"],
        authorized_users=config["authorized_users"],
        session_bridge=session_bridge,
    )

    retry_policy = RetryPolicy()

    async def start_polling_with_retry():
        """Start polling with automatic retry on failure."""
        while True:
            try:
                logger.info("Starting TerminalBot...")
                await application.initialize()

                # Register bot commands menu
                await application.bot.set_my_commands(BOT_COMMANDS)
                logger.info("Bot commands menu registered")

                await application.start()
                await application.updater.start_polling()

                # Check for restart notification
                import json
                restart_file = os.path.join(os.path.dirname(__file__), "..", ".restart_notify")
                restart_file = os.path.abspath(restart_file)
                if os.path.exists(restart_file):
                    try:
                        with open(restart_file) as f:
                            data = json.load(f)
                        os.remove(restart_file)
                        await application.bot.send_message(
                            chat_id=data["chat_id"],
                            text="✅ TerminalBot restarted successfully!"
                        )
                        logger.info(f"Sent restart notification to chat {data['chat_id']}")
                    except Exception as e:
                        logger.error(f"Failed to send restart notification: {e}")

                logger.info("Bot is running")
                return  # Successfully started

            except Exception as e:
                if is_transient_error(e):
                    logger.warning(f"Transient error during bot start: {e}")
                    # Retry with backoff
                    await asyncio.sleep(retry_policy.base_delay)
                else:
                    logger.error(f"Fatal error during bot start: {e}")
                    raise

    async def sleep_detection_loop():
        """Monitor for system sleep and trigger reconnection."""
        last_time = time.time()
        SLEEP_THRESHOLD = 60  # seconds

        while True:
            await asyncio.sleep(10)  # Check every 10 seconds

            current_time = time.time()
            elapsed = current_time - last_time

            if elapsed > SLEEP_THRESHOLD:
                logger.warning(
                    f"System sleep detected (time jump: {elapsed:.1f}s). "
                    "Triggering reconnection..."
                )
                # Stop and restart polling to refresh connections
                try:
                    await application.updater.stop()
                    await application.updater.start_polling()
                    logger.info("Reconnection successful after sleep")
                except Exception as e:
                    logger.error(f"Failed to reconnect after sleep: {e}")

            last_time = current_time

    sleep_task = None
    try:
        # Start bot with retry logic
        await start_polling_with_retry()

        # Start sleep detection in background
        sleep_task = asyncio.create_task(sleep_detection_loop())

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down TerminalBot...")

        # Cancel sleep detection task
        if sleep_task and not sleep_task.done():
            sleep_task.cancel()
            try:
                await sleep_task
            except asyncio.CancelledError:
                pass

        await session_bridge.stop_all()
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main() -> None:
    """Main entry point."""
    config = load_config()
    logger.info(f"Authorized users: {config['authorized_users']}")

    try:
        asyncio.run(run_bot(config))
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, exiting...")


if __name__ == "__main__":
    main()
