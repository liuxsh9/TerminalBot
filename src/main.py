#!/usr/bin/env python3
"""TerminalBot - Telegram bot for controlling terminal/tmux sessions remotely."""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

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
    """Run the Telegram bot."""
    # Import here to avoid issues if dependencies not installed
    from src.telegram_bot import create_bot
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

    logger.info("Starting TerminalBot...")
    await application.initialize()

    await application.start()
    await application.updater.start_polling()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down TerminalBot...")
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
