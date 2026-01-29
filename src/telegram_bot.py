"""Telegram bot module for CCBot."""

import logging
from typing import Optional, Set

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Bot commands for the menu
BOT_COMMANDS = [
    BotCommand("start", "Start the bot"),
    BotCommand("help", "Show help message"),
    BotCommand("list", "List available tmux sessions"),
    BotCommand("connect", "Connect to a tmux pane"),
    BotCommand("disconnect", "Disconnect from current session"),
    BotCommand("keys", "Show control keys panel"),
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

from src.session_bridge import SessionBridge

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot handler for terminal control."""

    def __init__(
        self,
        authorized_users: Set[int],
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
        if not self._authorized_users:
            return True  # No whitelist = allow all
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
            import logging
            logging.getLogger(__name__).error(f"Error sending message: {e}")
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
                text="ㅤ",
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

    async def cmd_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

        await update.message.reply_text(
            "Welcome to CCBot!\n\n"
            "Control your tmux terminal sessions remotely from Telegram.\n\n"
            "Features:\n"
            "- Real-time terminal output streaming\n"
            "- Send text input to terminal\n"
            "- Control keys (arrows, Tab, Esc, Ctrl+C, etc.)\n"
            "- Auto/Wait input modes\n\n"
            "Quick Start:\n"
            "1. /list - View available tmux sessions\n"
            "2. /connect - Select a pane to connect\n"
            "3. Send messages to input to terminal\n"
            "4. /keys - Show control keys panel\n\n"
            "Use /help for detailed usage."
        )

    async def cmd_help(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /help command."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

        await update.message.reply_text(
            "CCBot Commands:\n\n"
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

    async def cmd_list(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /list command - show available sessions."""
        user_id = update.effective_user.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

        panes = self._bridge._terminal.list_sessions()

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

    async def cmd_connect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /connect command - connect to a tmux pane."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

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
            panes = self._bridge._terminal.list_sessions()
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

    async def callback_connect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback for connect."""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            return

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

    async def cmd_disconnect(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /disconnect command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

        current = self._bridge.get_connection(chat_id)
        if not current:
            await update.message.reply_text("Not connected to any session.")
            return

        self._bridge.disconnect(chat_id)
        await update.message.reply_text(
            f"✅ Disconnected from `{current}`",
            parse_mode="Markdown"
        )

    def _get_keys_keyboard(self, auto_enter: bool = True) -> InlineKeyboardMarkup:
        """Create inline keyboard for control keys."""
        mode_label = "Auto" if auto_enter else "Wait"

        keyboard = [
            [
                InlineKeyboardButton("⬅️", callback_data="key:left"),
                InlineKeyboardButton("⬆️", callback_data="key:up"),
                InlineKeyboardButton("⬇️", callback_data="key:down"),
                InlineKeyboardButton("➡️", callback_data="key:right"),
                InlineKeyboardButton("⌫", callback_data="key:backspace"),
                InlineKeyboardButton("⏎", callback_data="key:enter"),
            ],
            [
                InlineKeyboardButton("Tab", callback_data="key:tab"),
                InlineKeyboardButton("⇧Tab", callback_data="key:shift_tab"),
                InlineKeyboardButton("Esc", callback_data="key:esc"),
                InlineKeyboardButton("^C", callback_data="key:ctrl_c"),
                InlineKeyboardButton("^C^C", callback_data="key:ctrl_cc"),
                InlineKeyboardButton(mode_label, callback_data="key:toggle_mode"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def cmd_keys(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /keys command - show control keys panel."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            await update.message.reply_text("Unauthorized. Access denied.")
            return

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
            "ㅤ",
            reply_markup=self._get_keys_keyboard(auto_enter)
        )
        # Store keys message ID
        self._bridge.set_keys_message_id(chat_id, msg.message_id)

    async def callback_key(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard callback for special keys."""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            return

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
                "ㅤ",
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

    async def handle_unknown_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle unknown commands - forward to connected terminal."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            return

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

    async def handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages - forward to connected terminal."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        if not self._is_authorized(user_id):
            return  # Silently ignore unauthorized users

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
    authorized_users: Set[int],
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

    # Set up post_init to register commands menu
    async def post_init(app: Application) -> None:
        await app.bot.set_my_commands(BOT_COMMANDS)

    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )
    bot.set_application(application)

    # Register handlers
    application.add_handler(CommandHandler("start", bot.cmd_start))
    application.add_handler(CommandHandler("help", bot.cmd_help))
    application.add_handler(CommandHandler("list", bot.cmd_list))
    application.add_handler(CommandHandler("connect", bot.cmd_connect))
    application.add_handler(CommandHandler("disconnect", bot.cmd_disconnect))
    application.add_handler(CommandHandler("keys", bot.cmd_keys))

    # Callback handlers for inline keyboard
    application.add_handler(
        CallbackQueryHandler(bot.callback_connect, pattern=r"^connect:")
    )
    application.add_handler(
        CallbackQueryHandler(bot.callback_key, pattern=r"^key:")
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
