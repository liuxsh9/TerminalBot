"""Session bridge module - connects Telegram chats to tmux panes."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable

from src.terminal_capture import TerminalCapture

logger = logging.getLogger(__name__)

# Telegram message limit
MAX_MESSAGE_LENGTH = 4000

# Buffer settings
BUFFER_DELAY = 0.5  # seconds to wait before sending buffered output
MIN_BURST_INTERVAL = 2.0  # seconds - outputs faster than this get buffered


@dataclass
class Connection:
    """Represents a connection between a Telegram chat and a tmux pane."""

    chat_id: int
    pane_identifier: str
    last_output_time: float = 0
    output_buffer: list[str] = field(default_factory=list)
    buffer_task: Optional[asyncio.Task] = None


class SessionBridge:
    """Bridge between Telegram chats and tmux terminal sessions."""

    def __init__(
        self,
        terminal_capture: TerminalCapture,
        poll_interval: float = 1.0,
    ):
        self._terminal = terminal_capture
        self._poll_interval = poll_interval
        self._connections: dict[int, Connection] = {}  # chat_id -> Connection
        self._polling_task: Optional[asyncio.Task] = None
        self._output_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
        self._disconnect_callback: Optional[Callable[[int, str], Awaitable[None]]] = None

    def set_output_callback(
        self, callback: Callable[[int, str], Awaitable[None]]
    ) -> None:
        """Set callback for sending output to Telegram.

        Args:
            callback: Async function(chat_id, message) to send output.
        """
        self._output_callback = callback

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

        # Clear content history to get fresh start
        self._terminal.clear_history(pane_identifier)

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
            conn = self._connections[chat_id]
            if conn.buffer_task and not conn.buffer_task.done():
                conn.buffer_task.cancel()
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

        return self._terminal.send_keys(conn.pane_identifier, text, enter=True)

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

            # Get new content
            new_content = self._terminal.get_new_content(conn.pane_identifier)
            if new_content:
                await self._handle_output(conn, new_content)

        # Handle disconnections
        for chat_id, reason in disconnected:
            await self._handle_disconnect(chat_id, reason)

    async def _handle_output(self, conn: Connection, content: str) -> None:
        """Handle new output from a pane with buffering."""
        now = time.time()
        time_since_last = now - conn.last_output_time

        if time_since_last < MIN_BURST_INTERVAL:
            # Buffer rapid output
            conn.output_buffer.append(content)

            # Schedule flush if not already scheduled
            if conn.buffer_task is None or conn.buffer_task.done():
                conn.buffer_task = asyncio.create_task(
                    self._flush_buffer_delayed(conn)
                )
        else:
            # Send immediately
            conn.last_output_time = now
            await self._send_output(conn.chat_id, content)

    async def _flush_buffer_delayed(self, conn: Connection) -> None:
        """Flush output buffer after a delay."""
        await asyncio.sleep(BUFFER_DELAY)

        if conn.output_buffer:
            combined = "\n".join(conn.output_buffer)
            conn.output_buffer.clear()
            conn.last_output_time = time.time()
            await self._send_output(conn.chat_id, combined)

    async def _send_output(self, chat_id: int, content: str) -> None:
        """Send output to Telegram with formatting and truncation."""
        if not self._output_callback:
            return

        # Format as monospace
        formatted = format_output(content)

        try:
            await self._output_callback(chat_id, formatted)
        except Exception as e:
            logger.error(f"Error sending output to chat {chat_id}: {e}")
            # Retry logic could be added here

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


def format_output(content: str) -> str:
    """Format terminal output for Telegram.

    Args:
        content: Raw terminal output

    Returns:
        Formatted output with monospace and truncation.
    """
    # Strip ANSI escape codes (basic)
    import re
    content = re.sub(r'\x1b\[[0-9;]*m', '', content)
    content = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', content)

    # Truncate if too long
    if len(content) > MAX_MESSAGE_LENGTH - 20:
        content = content[: MAX_MESSAGE_LENGTH - 20] + "\n[truncated]"

    # Wrap in code block
    return f"```\n{content}\n```"
