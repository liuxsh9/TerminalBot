"""Telegram bot module for TerminalBot."""

import asyncio
import logging
import os
import subprocess
import sys
from functools import wraps
from typing import Optional

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.session_bridge import SessionBridge

logger = logging.getLogger(__name__)

# Bot commands for the menu
BOT_COMMANDS = [
    BotCommand("new", "Create new tmux session"),
    BotCommand("list", "List available tmux sessions"),
    BotCommand("connect", "Connect to a tmux pane"),
    BotCommand("resize", "Set terminal width"),
    BotCommand("refresh", "Refresh terminal display"),
    BotCommand("disconnect", "Disconnect from current session"),
    BotCommand("update", "Update and restart bot"),
    BotCommand("start", "Start the bot"),
    BotCommand("keys", "Show control keys panel"),
    BotCommand("help", "Show help message"),
]

# Special keys mapping for tmux
SPECIAL_KEYS = {
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "enter": "Enter",
    "backspace": "BSpace",
    "ctrl_c": "C-c",
    "ctrl_cc": "C-c",  # Double ctrl+c (handled specially)
    "tab": "Tab",
    "shift_tab": "BTab",  # Shift+Tab in tmux
    "esc": "Escape",
}

# Invisible placeholder character for empty messages with inline keyboards
# Using Hangul Filler (U+3164) because Telegram requires non-empty text
INVISIBLE_PLACEHOLDER = "\u3164"


def authorized_only(func):
    """Decorator to check user authorization before executing handler."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return
        return await func(self, update, context)
    return wrapper


def authorized_callback(func):
    """Decorator to check user authorization for callback handlers."""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            return
        return await func(self, update, context)
    return wrapper


class TelegramBot:
    """Telegram bot handler for terminal control."""

    def __init__(
        self,
        authorized_users: set[int],
        session_bridge: SessionBridge,
    ):
        self._authorized_users = authorized_users
        self._bridge = session_bridge

        # Set up callbacks
        self._bridge.set_output_callback(self._send_output)
        self._bridge.set_delete_callback(self._delete_message)
        self._bridge.set_keys_callback(self._send_keys_panel)
        self._bridge.set_disconnect_callback(self._notify_disconnect)

        self._application: Application = None

    def set_application(self, application: Application) -> None:
        """Set the application reference for sending messages."""
        self._application = application

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        return user_id in self._authorized_users

    async def _send_output(self, chat_id: int, message: str, edit_message_id: int = None) -> int:
        """Send or edit output message to a chat.

        Args:
            chat_id: Telegram chat ID
            message: Message text
            edit_message_id: If provided, edit this message instead of sending new

        Returns:
            Message ID of sent/edited message
        """
        if not self._application:
            return None

        try:
            if edit_message_id:
                # Try to edit existing message
                try:
                    msg = await self._application.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=edit_message_id,
                        text=message,
                        parse_mode="Markdown",
                    )
                    return msg.message_id
                except Exception as e:
                    # If edit fails (message too old, etc.), send new
                    pass

            # Send new message
            msg = await self._application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )
            return msg.message_id
        except Exception as e:
            # Log but don't crash
            logger.error(f"Error sending message: {e}")
            return None

    async def _delete_message(self, chat_id: int, message_id: int) -> bool:
        """Delete a message.

        Args:
            chat_id: Telegram chat ID
            message_id: Message ID to delete

        Returns:
            True if deleted successfully
        """
        if not self._application:
            return False

        try:
            await self._application.bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return False

    async def _send_keys_panel(self, chat_id: int) -> Optional[int]:
        """Send control keys panel.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Message ID of sent message
        """
        if not self._application:
            return None

        try:
            auto_enter = self._bridge.get_auto_enter(chat_id)
            msg = await self._application.bot.send_message(
                chat_id=chat_id,
                text=INVISIBLE_PLACEHOLDER,
                reply_markup=self._get_keys_keyboard(auto_enter),
            )
            return msg.message_id
        except Exception as e:
            logger.error(f"Error sending keys panel: {e}")
            return None

    async def _notify_disconnect(self, chat_id: int, reason: str) -> None:
        """Notify user of disconnection."""
        if self._application:
            await self._application.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Disconnected: {reason}",
            )

    @authorized_only
    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "Welcome to TerminalBot!\n\n"
            "Control tmux sessions from your phone.\n\n"
            "/new - Create a new session\n"
            "/connect - Connect to existing session"
        )

    @authorized_only
    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "TerminalBot Commands:\n\n"
            "/list - List available tmux panes\n"
            "/connect - Connect to a pane (shows selection)\n"
            "/disconnect - Disconnect from session\n"
            "/keys - Show control keys panel\n"
            "/help - Show this help\n\n"
            "Control Keys:\n"
            "Arrow keys, Tab, Shift+Tab, Esc, Backspace, Enter, Ctrl+C\n\n"
            "Input Modes:\n"
            "- Auto: Messages sent with Enter automatically\n"
            "- Wait: Messages sent without Enter (press Enter manually)\n\n"
            "Tip: Unknown /commands are forwarded to terminal when connected."
        )

    @authorized_only
    async def cmd_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /list command - show available sessions."""
        panes = self._bridge.list_sessions()

        if not panes:
            await update.message.reply_text(
                "No tmux sessions found.\n\n"
                "Start a tmux session first:\n"
                "`tmux new -s mysession`"
            , parse_mode="Markdown")
            return

        lines = ["Available tmux panes:\n"]
        for pane in panes:
            lines.append(f"• `{pane.identifier}` - {pane.window_name}")

        lines.append("\nUse /connect <id> to connect")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    @authorized_only
    async def cmd_connect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /connect command - connect to a tmux pane."""
        chat_id = update.effective_chat.id

        # Check if already connected
        current = self._bridge.get_connection(chat_id)
        if current:
            await update.message.reply_text(
                f"Already connected to `{current}`.\n"
                "Use /disconnect first.",
                parse_mode="Markdown"
            )
            return

        # If no argument provided, show inline keyboard with available panes
        if not context.args:
            panes = self._bridge.list_sessions()
            if not panes:
                await update.message.reply_text(
                    "No tmux sessions found.\n\n"
                    "Start a tmux session first:\n"
                    "`tmux new -s mysession`",
                    parse_mode="Markdown"
                )
                return

            # Create inline keyboard with pane options
            keyboard = []
            for pane in panes:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{pane.identifier} ({pane.window_name})",
                        callback_data=f"connect:{pane.identifier}"
                    )
                ])

            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Select a tmux pane to connect:",
                reply_markup=reply_markup
            )
            return

        pane_id = context.args[0]
        await self._do_connect(chat_id, pane_id, update.message.reply_text)

    async def _do_connect(self, chat_id: int, pane_id: str, reply_func) -> None:
        """Perform the actual connection."""
        if self._bridge.connect(chat_id, pane_id):
            await reply_func(
                f"✅ Connected to `{pane_id}`\n\n"
                "Terminal output will be streamed here.\n"
                "Send text to input to the terminal.",
                parse_mode="Markdown"
            )
        else:
            await reply_func(
                f"❌ Failed to connect to `{pane_id}`\n\n"
                "Make sure the pane exists. Use /list to see available panes.",
                parse_mode="Markdown"
            )

    @authorized_callback
    async def callback_connect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback for connect."""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id

        # Check if already connected
        current = self._bridge.get_connection(chat_id)
        if current:
            await query.edit_message_text(
                f"Already connected to `{current}`.\n"
                "Use /disconnect first.",
                parse_mode="Markdown"
            )
            return

        # Extract pane_id from callback_data (format: "connect:session:window.pane")
        pane_id = query.data.split(":", 1)[1]

        if self._bridge.connect(chat_id, pane_id):
            await query.edit_message_text(
                f"✅ Connected to `{pane_id}`\n\n"
                "Terminal output will be streamed here.\n"
                "Send text to input to the terminal.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ Failed to connect to `{pane_id}`\n\n"
                "Pane may no longer exist.",
                parse_mode="Markdown"
            )

    @authorized_only
    async def cmd_disconnect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /disconnect command."""
        chat_id = update.effective_chat.id

        current = self._bridge.get_connection(chat_id)
        if not current:
            await update.message.reply_text("Not connected to any session.")
            return

        self._bridge.disconnect(chat_id)
        await update.message.reply_text(
            f"✅ Disconnected from `{current}`",
            parse_mode="Markdown"
        )

    @authorized_only
    async def cmd_refresh(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /refresh command - force refresh terminal display."""
        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await update.message.reply_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        pane_id = self._bridge.get_connection(chat_id)

        # Check if pane still exists
        if not self._bridge.pane_exists(pane_id):
            self._bridge.disconnect(chat_id)
            await update.message.reply_text(
                f"⚠️ Session `{pane_id}` no longer exists.\n"
                "Use /connect or /new to start a new session.",
                parse_mode="Markdown"
            )
            return

        # Force refresh by invalidating message and triggering immediate poll
        self._bridge.invalidate_terminal_message(chat_id)
        await self._bridge.force_refresh(chat_id)
        await update.message.reply_text("✅ Refreshed")

    def _get_keys_keyboard(self, auto_enter: bool = True) -> InlineKeyboardMarkup:
        """Create inline keyboard for control keys."""
        mode_label = "Auto" if auto_enter else "Wait"

        keyboard = [
            [
                InlineKeyboardButton("Esc", callback_data="key:esc"),
                InlineKeyboardButton("⬆️", callback_data="key:up"),
                InlineKeyboardButton("⌫", callback_data="key:backspace"),
                InlineKeyboardButton("⏎", callback_data="key:enter"),
            ],
            [
                InlineKeyboardButton("⬅️", callback_data="key:left"),
                InlineKeyboardButton("⬇️", callback_data="key:down"),
                InlineKeyboardButton("➡️", callback_data="key:right"),
                InlineKeyboardButton("Tab", callback_data="key:tab"),
            ],
            [
                InlineKeyboardButton("^C", callback_data="key:ctrl_c"),
                InlineKeyboardButton("^C^C", callback_data="key:ctrl_cc"),
                InlineKeyboardButton("⇧Tab", callback_data="key:shift_tab"),
                InlineKeyboardButton(mode_label, callback_data="key:toggle_mode"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    @authorized_only
    async def cmd_keys(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /keys command - show control keys panel."""
        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await update.message.reply_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        # Invalidate terminal message so next update creates new one above keys
        self._bridge.invalidate_terminal_message(chat_id)

        auto_enter = self._bridge.get_auto_enter(chat_id)
        msg = await update.message.reply_text(
            INVISIBLE_PLACEHOLDER,
            reply_markup=self._get_keys_keyboard(auto_enter)
        )
        # Store keys message ID
        self._bridge.set_keys_message_id(chat_id, msg.message_id)

    @authorized_only
    async def cmd_resize(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /resize command - resize connected pane width."""
        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await update.message.reply_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        # If argument provided, use it directly
        if context.args:
            try:
                width = int(context.args[0])
                if width < 20 or width > 500:
                    await update.message.reply_text(
                        "Width must be between 20 and 500."
                    )
                    return
                await self._do_resize(chat_id, width, update.message.reply_text)
                return
            except ValueError:
                await update.message.reply_text(
                    "Invalid width. Please provide a number."
                )
                return

        # Show inline keyboard with preset options
        keyboard = [
            [
                InlineKeyboardButton("30", callback_data="resize:30"),
                InlineKeyboardButton("60", callback_data="resize:60"),
                InlineKeyboardButton("80", callback_data="resize:80"),
            ],
            [
                InlineKeyboardButton("90", callback_data="resize:90"),
                InlineKeyboardButton("120", callback_data="resize:120"),
                InlineKeyboardButton("Reset", callback_data="resize:reset"),
            ],
        ]
        await update.message.reply_text(
            "Select terminal width:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def _do_resize(self, chat_id: int, width: int, reply_func) -> None:
        """Perform the actual resize."""
        pane_id = self._bridge.get_connection(chat_id)
        if self._bridge.set_terminal_width(pane_id, width):
            await reply_func(f"✅ Terminal width set to {width} columns")
        else:
            await reply_func("❌ Failed to set terminal width.")

    @authorized_callback
    async def callback_resize(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback for resize."""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await query.edit_message_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        # Extract width from callback_data (format: "resize:60" or "resize:reset")
        value = query.data.split(":", 1)[1]

        if value == "reset":
            # Reset by getting actual terminal size
            pane_id = self._bridge.get_connection(chat_id)
            if self._bridge.reset_terminal_width(pane_id):
                await query.edit_message_text("✅ Terminal width reset")
            else:
                await query.edit_message_text("❌ Failed to reset terminal width.")
        else:
            width = int(value)
            pane_id = self._bridge.get_connection(chat_id)
            if self._bridge.set_terminal_width(pane_id, width):
                await query.edit_message_text(f"✅ Terminal width set to {width} columns")
            else:
                await query.edit_message_text("❌ Failed to set terminal width.")

    @authorized_only
    async def cmd_new(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /new command - create new tmux session."""
        chat_id = update.effective_chat.id

        # Check if already connected
        current = self._bridge.get_connection(chat_id)
        if current:
            await update.message.reply_text(
                f"Already connected to `{current}`.\n"
                "Use /disconnect first.",
                parse_mode="Markdown"
            )
            return

        # Get session name from args or generate one
        session_name = context.args[0] if context.args else None

        result = self._bridge.create_session(session_name)
        if result:
            session_name, pane_id = result
            # Auto-connect to the new session
            if self._bridge.connect(chat_id, pane_id):
                await update.message.reply_text(
                    f"✅ Created and connected to `{pane_id}`\n\n"
                    "Terminal output will be streamed here.\n"
                    "Send text to input to the terminal.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"✅ Created session `{session_name}`\n"
                    f"Use `/connect {pane_id}` to connect.",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(
                "❌ Failed to create tmux session.\n"
                "Make sure tmux is installed and running."
            )

    @authorized_only
    async def cmd_update(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /update command - update and restart the bot."""
        await update.message.reply_text("🔄 Updating TerminalBot...")

        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Run git pull
        result = subprocess.run(
            ["git", "pull"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            await update.message.reply_text(
                f"❌ Git pull failed:\n```\n{error_msg}\n```",
                parse_mode="Markdown"
            )
            return

        # Show git pull output
        output = result.stdout.strip() or "Already up to date."
        await update.message.reply_text(
            f"✅ Git pull:\n```\n{output}\n```\n\n🔄 Restarting...",
            parse_mode="Markdown"
        )

        # Give time for message to send
        await asyncio.sleep(1)

        # Save chat_id for restart notification
        import json
        restart_file = os.path.join(project_root, ".restart_notify")
        with open(restart_file, "w") as f:
            json.dump({"chat_id": update.effective_chat.id}, f)

        # Restart using os.execv
        os.execv(sys.executable, [sys.executable] + sys.argv)

    @authorized_callback
    async def callback_key(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback for special keys."""
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await query.edit_message_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        # Extract key from callback_data (format: "key:up")
        key_name = query.data.split(":", 1)[1]

        # Handle mode toggle
        if key_name == "toggle_mode":
            new_mode = self._bridge.toggle_auto_enter(chat_id)
            await query.edit_message_text(
                INVISIBLE_PLACEHOLDER,
                reply_markup=self._get_keys_keyboard(new_mode)
            )
            return

        # Handle double Ctrl+C specially
        if key_name == "ctrl_cc":
            success = (
                self._bridge.send_special_key(chat_id, "C-c") and
                self._bridge.send_special_key(chat_id, "C-c")
            )
        else:
            tmux_key = SPECIAL_KEYS.get(key_name)
            success = tmux_key and self._bridge.send_special_key(chat_id, tmux_key)

        if not success:
            await query.edit_message_text(
                "❌ Failed to send key. Session may have closed."
            )

    @authorized_only
    async def handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unknown commands - forward to connected terminal."""
        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await update.message.reply_text(
                "Unknown command. Use /help to see available commands.\n"
                "Or /connect to a session first to forward commands to terminal."
            )
            return

        # Forward the command (including the /) to the terminal
        self._bridge.invalidate_terminal_message(chat_id)

        text = update.message.text
        if not self._bridge.send_input(chat_id, text):
            await update.message.reply_text(
                "❌ Failed to send command. Session may have closed."
            )

    @authorized_only
    async def handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages - forward to connected terminal."""
        chat_id = update.effective_chat.id

        if not self._bridge.is_connected(chat_id):
            await update.message.reply_text(
                "Not connected to any session.\n"
                "Use /connect first."
            )
            return

        # Invalidate terminal message so next update creates new one below user's message
        self._bridge.invalidate_terminal_message(chat_id)

        text = update.message.text
        if not self._bridge.send_input(chat_id, text):
            await update.message.reply_text(
                "❌ Failed to send input. Session may have closed."
            )


def create_bot(
    token: str,
    authorized_users: set[int],
    session_bridge: SessionBridge,
) -> Application:
    """Create and configure the Telegram bot application.

    Args:
        token: Telegram bot token
        authorized_users: Set of authorized user IDs
        session_bridge: SessionBridge instance

    Returns:
        Configured Application instance.
    """
    bot = TelegramBot(authorized_users, session_bridge)

    application = Application.builder().token(token).build()
    bot.set_application(application)

    # Register handlers
    application.add_handler(CommandHandler("start", bot.cmd_start))
    application.add_handler(CommandHandler("help", bot.cmd_help))
    application.add_handler(CommandHandler("list", bot.cmd_list))
    application.add_handler(CommandHandler("connect", bot.cmd_connect))
    application.add_handler(CommandHandler("disconnect", bot.cmd_disconnect))
    application.add_handler(CommandHandler("keys", bot.cmd_keys))
    application.add_handler(CommandHandler("resize", bot.cmd_resize))
    application.add_handler(CommandHandler("new", bot.cmd_new))
    application.add_handler(CommandHandler("refresh", bot.cmd_refresh))
    application.add_handler(CommandHandler("update", bot.cmd_update))

    # Callback handlers for inline keyboard
    application.add_handler(
        CallbackQueryHandler(bot.callback_connect, pattern=r"^connect:")
    )
    application.add_handler(
        CallbackQueryHandler(bot.callback_key, pattern=r"^key:")
    )
    application.add_handler(
        CallbackQueryHandler(bot.callback_resize, pattern=r"^resize:")
    )

    # Text message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text)
    )

    # Unknown command handler - forward to terminal (e.g., /openspec)
    # Must be last to catch commands not handled above
    application.add_handler(
        MessageHandler(filters.COMMAND, bot.handle_unknown_command)
    )

    return application
