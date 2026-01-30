"""Session bridge module - connects Telegram chats to tmux panes."""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable

from src.terminal_capture import TerminalCapture

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4000

# Default terminal window settings
DEFAULT_TERMINAL_LINES = 30


@dataclass
class Connection:
    """Represents a connection between a Telegram chat and a tmux pane."""

    chat_id: int
    pane_identifier: str
    # Single terminal window message
    terminal_message_id: Optional[int] = None
    last_content_hash: str = ""
    # Control keys message (should always be below terminal)
    keys_message_id: Optional[int] = None
    # Input mode: True = auto enter, False = manual enter (Wait)
    auto_enter: bool = True


class SessionBridge:
    """Bridge between Telegram chats and tmux terminal sessions."""

    def __init__(
        self,
        terminal_capture: TerminalCapture,
        poll_interval: float = 1.0,
        terminal_lines: int = DEFAULT_TERMINAL_LINES,
        default_work_dir: Optional[str] = None,
    ):
        self._terminal = terminal_capture
        self._poll_interval = poll_interval
        self._terminal_lines = terminal_lines
        self._default_work_dir = default_work_dir
        self._session_counter = 0  # Counter for auto-naming sessions
        self._connections: dict[int, Connection] = {}  # chat_id -> Connection
        self._polling_task: Optional[asyncio.Task] = None
        self._output_callback: Optional[Callable[[int, str, Optional[int]], Awaitable[Optional[int]]]] = None
        self._delete_callback: Optional[Callable[[int, int], Awaitable[bool]]] = None
        self._keys_callback: Optional[Callable[[int], Awaitable[Optional[int]]]] = None
        self._disconnect_callback: Optional[Callable[[int, str], Awaitable[None]]] = None

    def set_output_callback(
        self, callback: Callable[[int, str, Optional[int]], Awaitable[Optional[int]]]
    ) -> None:
        """Set callback for sending output to Telegram.

        Args:
            callback: Async function(chat_id, message, edit_message_id) -> message_id
                     If edit_message_id is provided, edit that message instead of sending new.
                     Returns the message_id of the sent/edited message.
        """
        self._output_callback = callback

    def set_delete_callback(
        self, callback: Callable[[int, int], Awaitable[bool]]
    ) -> None:
        """Set callback for deleting a message.

        Args:
            callback: Async function(chat_id, message_id) -> success
        """
        self._delete_callback = callback

    def set_keys_callback(
        self, callback: Callable[[int], Awaitable[Optional[int]]]
    ) -> None:
        """Set callback for sending control keys panel.

        Args:
            callback: Async function(chat_id) -> message_id
        """
        self._keys_callback = callback

    def set_disconnect_callback(
        self, callback: Callable[[int, str], Awaitable[None]]
    ) -> None:
        """Set callback for notifying disconnection.

        Args:
            callback: Async function(chat_id, reason) for disconnect notification.
        """
        self._disconnect_callback = callback

    def connect(self, chat_id: int, pane_identifier: str) -> bool:
        """Connect a Telegram chat to a tmux pane.

        Args:
            chat_id: Telegram chat ID
            pane_identifier: Pane identifier (session:window.pane)

        Returns:
            True if connected successfully, False otherwise.
        """
        # Verify pane exists
        if not self._terminal.pane_exists(pane_identifier):
            logger.warning(f"Pane not found: {pane_identifier}")
            return False

        # Disconnect from previous pane if any
        if chat_id in self._connections:
            self._cleanup_connection(chat_id)

        # Create new connection
        self._connections[chat_id] = Connection(
            chat_id=chat_id,
            pane_identifier=pane_identifier,
        )

        # Start polling if not already running
        if self._polling_task is None or self._polling_task.done():
            self._polling_task = asyncio.create_task(self._poll_loop())

        logger.info(f"Chat {chat_id} connected to {pane_identifier}")
        return True

    def disconnect(self, chat_id: int) -> bool:
        """Disconnect a Telegram chat from its tmux pane.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if was connected and now disconnected, False if wasn't connected.
        """
        if chat_id not in self._connections:
            return False

        self._cleanup_connection(chat_id)
        logger.info(f"Chat {chat_id} disconnected")
        return True

    def _cleanup_connection(self, chat_id: int) -> None:
        """Clean up a connection."""
        if chat_id in self._connections:
            del self._connections[chat_id]

    def get_connection(self, chat_id: int) -> Optional[str]:
        """Get the pane identifier for a connected chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Pane identifier if connected, None otherwise.
        """
        conn = self._connections.get(chat_id)
        return conn.pane_identifier if conn else None

    def is_connected(self, chat_id: int) -> bool:
        """Check if a chat is connected to a pane."""
        return chat_id in self._connections

    def list_sessions(self):
        """List available tmux sessions/panes."""
        return self._terminal.list_sessions()

    def create_session(self, name: str = None):
        """Create a new tmux session with auto-generated name if not provided."""
        if name is None:
            # Auto-generate short session name: tb0, tb1, tb2, ...
            self._session_counter += 1
            name = f"tb{self._session_counter}"
        return self._terminal.create_session(name, self._default_work_dir)

    def kill_session(self, session_name: str) -> bool:
        """Kill a tmux session."""
        return self._terminal.kill_session(session_name)

    def resize_pane(self, pane_id: str, width: int) -> bool:
        """Resize a pane to specified width."""
        return self._terminal.resize_pane(pane_id, width)

    def set_terminal_width(self, pane_id: str, width: int) -> bool:
        """Set terminal width using stty."""
        return self._terminal.set_terminal_width(pane_id, width)

    def reset_terminal_width(self, pane_id: str) -> bool:
        """Reset terminal width to actual pane size."""
        return self._terminal.reset_terminal_width(pane_id)

    def pane_exists(self, pane_id: str) -> bool:
        """Check if a pane exists."""
        return self._terminal.pane_exists(pane_id)

    def send_input(self, chat_id: int, text: str) -> bool:
        """Send text input to the connected pane.

        Args:
            chat_id: Telegram chat ID
            text: Text to send

        Returns:
            True if sent successfully, False otherwise.
        """
        conn = self._connections.get(chat_id)
        if conn is None:
            return False

        return self._terminal.send_keys(conn.pane_identifier, text, enter=conn.auto_enter)

    def toggle_auto_enter(self, chat_id: int) -> bool:
        """Toggle auto-enter mode for a connection.

        Args:
            chat_id: Telegram chat ID

        Returns:
            New auto_enter state (True = auto, False = manual)
        """
        conn = self._connections.get(chat_id)
        if conn is None:
            return False

        conn.auto_enter = not conn.auto_enter
        return conn.auto_enter

    def get_auto_enter(self, chat_id: int) -> bool:
        """Get current auto-enter mode.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Current auto_enter state
        """
        conn = self._connections.get(chat_id)
        return conn.auto_enter if conn else False

    def send_special_key(self, chat_id: int, key: str) -> bool:
        """Send a special key (like Up, Down, C-c) to the connected pane.

        Args:
            chat_id: Telegram chat ID
            key: tmux key name (e.g., "Up", "Down", "C-c", "Enter")

        Returns:
            True if sent successfully, False otherwise.
        """
        conn = self._connections.get(chat_id)
        if conn is None:
            return False

        return self._terminal.send_keys(conn.pane_identifier, key, enter=False)

    async def _poll_loop(self) -> None:
        """Main polling loop for checking pane output."""
        logger.info("Starting polling loop")

        while self._connections:
            try:
                await self._poll_all_connections()
                await asyncio.sleep(self._poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(self._poll_interval)

        logger.info("Polling loop stopped (no connections)")

    async def _poll_all_connections(self) -> None:
        """Poll all connected panes for new output."""
        disconnected = []

        for chat_id, conn in list(self._connections.items()):
            # Check if pane still exists
            if not self._terminal.pane_exists(conn.pane_identifier):
                disconnected.append((chat_id, "Pane closed or no longer exists"))
                continue

            # Get current pane content (full capture)
            content = self._terminal.capture_pane(conn.pane_identifier)
            if content is not None:
                await self._update_terminal_window(conn, content)

        # Handle disconnections
        for chat_id, reason in disconnected:
            await self._handle_disconnect(chat_id, reason)

    async def _update_terminal_window(self, conn: Connection, content: str) -> None:
        """Update the terminal window message with current content."""
        if not self._output_callback:
            return

        # Format content (last N lines)
        formatted = format_terminal_window(content, self._terminal_lines)

        # Check if content actually changed
        content_hash = hash(formatted)
        if content_hash == conn.last_content_hash:
            return  # No change, skip update

        conn.last_content_hash = content_hash

        try:
            # Check if keys panel exists and is below terminal message
            # If terminal message doesn't exist or keys is above it, we need to reorder
            need_reorder = False
            if conn.keys_message_id:
                if conn.terminal_message_id is None:
                    need_reorder = True
                elif conn.keys_message_id < conn.terminal_message_id:
                    # Keys is above terminal (shouldn't happen normally)
                    need_reorder = True

            # If we need to send a new terminal message (not edit), reorder keys panel
            if conn.terminal_message_id is None and conn.keys_message_id:
                need_reorder = True

            # Delete keys panel if we need to reorder
            if need_reorder and self._delete_callback and conn.keys_message_id:
                await self._delete_callback(conn.chat_id, conn.keys_message_id)
                conn.keys_message_id = None

            # Send/edit terminal message
            message_id = await self._output_callback(
                conn.chat_id,
                formatted,
                conn.terminal_message_id
            )

            # Store message ID for future edits
            if message_id:
                # If this is a new message (different ID), we need to resend keys panel
                if conn.terminal_message_id != message_id:
                    need_reorder = True
                conn.terminal_message_id = message_id

            # Resend keys panel below terminal if needed
            if need_reorder and self._keys_callback:
                keys_msg_id = await self._keys_callback(conn.chat_id)
                if keys_msg_id:
                    conn.keys_message_id = keys_msg_id

        except Exception as e:
            logger.error(f"Error updating terminal window for chat {conn.chat_id}: {e}")

    def set_keys_message_id(self, chat_id: int, message_id: int) -> None:
        """Store the keys panel message ID for a connection."""
        conn = self._connections.get(chat_id)
        if conn:
            conn.keys_message_id = message_id

    def invalidate_terminal_message(self, chat_id: int) -> None:
        """Invalidate terminal message so next update creates a new one."""
        conn = self._connections.get(chat_id)
        if conn:
            conn.terminal_message_id = None

    async def force_refresh(self, chat_id: int) -> bool:
        """Force refresh terminal display for a connection.

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if refreshed successfully, False otherwise.
        """
        conn = self._connections.get(chat_id)
        if conn is None:
            return False

        # Clear content hash to force update
        conn.last_content_hash = ""

        # Get current content and update
        content = self._terminal.capture_pane(conn.pane_identifier)
        if content is not None:
            await self._update_terminal_window(conn, content)
            return True
        return False

    async def _handle_disconnect(self, chat_id: int, reason: str) -> None:
        """Handle unexpected disconnection."""
        self._cleanup_connection(chat_id)

        if self._disconnect_callback:
            try:
                await self._disconnect_callback(chat_id, reason)
            except Exception as e:
                logger.error(f"Error notifying disconnect for chat {chat_id}: {e}")

    async def stop_all(self) -> None:
        """Stop all connections and polling."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass

        for chat_id in list(self._connections.keys()):
            self._cleanup_connection(chat_id)


def format_terminal_window(content: str, max_lines: int = 30) -> str:
    """Format terminal content as a fixed-height window.

    Args:
        content: Raw terminal output
        max_lines: Maximum number of lines to show

    Returns:
        Formatted output showing last N lines.
    """
    # Strip ANSI escape codes
    content = re.sub(r'\x1b\[[0-9;]*m', '', content)
    content = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', content)
    content = re.sub(r'\x1b\][^\x07]*\x07', '', content)  # OSC sequences
    content = re.sub(r'\x1b[PX^_][^\x1b]*\x1b\\', '', content)  # Other sequences

    # Remove carriage returns
    content = re.sub(r'\r+', '', content)

    # Compress long horizontal lines (─, ━, ═, -, =, etc.)
    content = re.sub(r'[─━═]{20,}', '────────────────────', content)
    content = re.sub(r'[-]{20,}', '--------------------', content)
    content = re.sub(r'[=]{20,}', '====================', content)

    # Split into lines and get last N non-empty lines
    lines = content.split('\n')

    # Remove trailing empty lines
    while lines and not lines[-1].strip():
        lines.pop()

    # Get last N lines
    if len(lines) > max_lines:
        lines = lines[-max_lines:]

    # Strip trailing whitespace from each line
    lines = [line.rstrip() for line in lines]

    # Join back
    content = '\n'.join(lines)

    # Truncate if still too long for Telegram
    if len(content) > MAX_MESSAGE_LENGTH - 50:
        content = content[-(MAX_MESSAGE_LENGTH - 50):]
        content = "[...]\n" + content

    # Wrap in code block with header
    return f"```\n{content}\n```"
