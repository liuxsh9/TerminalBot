"""Telegram bot module for CCBot."""

import logging
from typing import Set

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
    "ctrl_c": "C-c",
    "ctrl_d": "C-d",
    "ctrl_z": "C-z",
    "tab": "Tab",
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

    async def _send_output(self, chat_id: int, message: str) -> None:
        """Send output message to a chat."""
        if self._application:
            await self._application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
            )

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
            "Welcome to CCBot! 🖥️\n\n"
            "Control your terminal sessions from Telegram.\n\n"
            "Commands:\n"
            "/list - Show available tmux sessions\n"
            "/connect <session:window.pane> - Connect to a pane\n"
            "/disconnect - Disconnect from current session\n"
            "/help - Show this help message\n\n"
            "Once connected, send any text to forward it to the terminal."
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
            "/list - List all available tmux sessions and panes\n"
            "/connect <id> - Connect to a tmux pane\n"
            "  Example: /connect main:0.0\n"
            "/disconnect - Disconnect from current session\n"
            "/help - Show this help\n\n"
            "Usage:\n"
            "1. Use /list to see available sessions\n"
            "2. Use /connect to attach to a pane\n"
            "3. Send text messages to input to the terminal\n"
            "4. Receive terminal output automatically"
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

    def _get_keys_keyboard(self) -> InlineKeyboardMarkup:
        """Create inline keyboard for control keys."""
        keyboard = [
            [
                InlineKeyboardButton("⬆️", callback_data="key:up"),
            ],
            [
                InlineKeyboardButton("⬅️", callback_data="key:left"),
                InlineKeyboardButton("⏎", callback_data="key:enter"),
                InlineKeyboardButton("➡️", callback_data="key:right"),
            ],
            [
                InlineKeyboardButton("⬇️", callback_data="key:down"),
            ],
            [
                InlineKeyboardButton("Tab", callback_data="key:tab"),
                InlineKeyboardButton("Esc", callback_data="key:esc"),
            ],
            [
                InlineKeyboardButton("Ctrl+C", callback_data="key:ctrl_c"),
                InlineKeyboardButton("Ctrl+D", callback_data="key:ctrl_d"),
                InlineKeyboardButton("Ctrl+Z", callback_data="key:ctrl_z"),
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

        await update.message.reply_text(
            "Control Keys:",
            reply_markup=self._get_keys_keyboard()
        )

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
        tmux_key = SPECIAL_KEYS.get(key_name)

        if tmux_key and self._bridge.send_special_key(chat_id, tmux_key):
            # Keep the keyboard visible, just acknowledge
            pass
        else:
            await query.edit_message_text(
                "❌ Failed to send key. Session may have closed."
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

        text = update.message.text
        if self._bridge.send_input(chat_id, text):
            # Optionally confirm input was sent
            # await update.message.reply_text(f"→ {text}")
            pass
        else:
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

    # Text message handler (must be last)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text)
    )

    return application
