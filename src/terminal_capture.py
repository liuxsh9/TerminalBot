"""Terminal capture module for interacting with tmux sessions."""

import logging
from dataclasses import dataclass
from typing import Optional

import libtmux

logger = logging.getLogger(__name__)


@dataclass
class PaneInfo:
    """Information about a tmux pane."""

    session_name: str
    window_index: int
    window_name: str
    pane_index: int
    pane_id: str

    @property
    def identifier(self) -> str:
        """Return a human-readable identifier for this pane."""
        return f"{self.session_name}:{self.window_index}.{self.pane_index}"

    def __str__(self) -> str:
        return f"{self.identifier} ({self.window_name})"


class TerminalCapture:
    """Capture and interact with tmux terminal sessions."""

    def __init__(self):
        self._server: Optional[libtmux.Server] = None
        self._last_content: dict[str, str] = {}

    def _get_server(self) -> Optional[libtmux.Server]:
        """Get or create tmux server connection."""
        try:
            if self._server is None:
                self._server = libtmux.Server()
            # Test connection by listing sessions
            self._server.sessions
            return self._server
        except libtmux.exc.LibTmuxException:
            self._server = None
            return None

    def list_sessions(self) -> list[PaneInfo]:
        """List all available tmux sessions, windows, and panes.

        Returns:
            List of PaneInfo objects for each pane.
        """
        server = self._get_server()
        if server is None:
            logger.warning("tmux server not running")
            return []

        panes = []
        try:
            for session in server.sessions:
                for window in session.windows:
                    for pane in window.panes:
                        panes.append(
                            PaneInfo(
                                session_name=session.name,
                                window_index=int(window.index),
                                window_name=window.name,
                                pane_index=int(pane.index),
                                pane_id=pane.id,
                            )
                        )
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error listing sessions: {e}")
            return []

        return panes

    def get_pane(self, identifier: str) -> Optional[libtmux.Pane]:
        """Get a pane by its identifier (session:window.pane).

        Args:
            identifier: Pane identifier in format "session:window.pane"

        Returns:
            The libtmux Pane object, or None if not found.
        """
        server = self._get_server()
        if server is None:
            return None

        try:
            # Parse identifier: session:window.pane
            session_part, pane_part = identifier.split(":")
            window_index, pane_index = pane_part.split(".")

            session = server.sessions.get(session_name=session_part)
            if session is None:
                return None

            window = session.windows.get(window_index=window_index)
            if window is None:
                return None

            for pane in window.panes:
                if pane.index == pane_index:
                    return pane

            return None
        except (ValueError, libtmux.exc.LibTmuxException) as e:
            logger.error(f"Error getting pane {identifier}: {e}")
            return None

    def capture_pane(self, identifier: str) -> Optional[str]:
        """Capture the visible content of a tmux pane.

        Args:
            identifier: Pane identifier in format "session:window.pane"

        Returns:
            The pane content as a string, or None if pane not found.
        """
        pane = self.get_pane(identifier)
        if pane is None:
            return None

        try:
            # Capture visible pane content
            content_lines = pane.capture_pane()
            return "\n".join(content_lines)
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error capturing pane {identifier}: {e}")
            return None

    def get_new_content(self, identifier: str) -> Optional[str]:
        """Get new content since last capture (change detection).

        Args:
            identifier: Pane identifier in format "session:window.pane"

        Returns:
            New content if changed, empty string if unchanged, None if error.
        """
        current_content = self.capture_pane(identifier)
        if current_content is None:
            return None

        last_content = self._last_content.get(identifier, "")
        self._last_content[identifier] = current_content

        if current_content == last_content:
            return ""

        # Find new content by comparing from the end
        # This handles scrolling better than simple diff
        if last_content and current_content.endswith(last_content[-500:]):
            # Content scrolled, return only new part
            overlap_start = current_content.rfind(last_content[-200:])
            if overlap_start > 0:
                return current_content[:overlap_start].strip()

        # If we can't find overlap, return full content on first capture
        # or just the new content
        if not last_content:
            return current_content

        # Return the difference - simple approach: new lines at the end
        last_lines = set(last_content.split("\n"))
        new_lines = []
        for line in current_content.split("\n"):
            if line not in last_lines:
                new_lines.append(line)

        return "\n".join(new_lines) if new_lines else ""

    def send_keys(self, identifier: str, text: str, enter: bool = True) -> bool:
        """Send text input to a tmux pane.

        Args:
            identifier: Pane identifier in format "session:window.pane"
            text: Text to send
            enter: Whether to press Enter after the text

        Returns:
            True if successful, False otherwise.
        """
        pane = self.get_pane(identifier)
        if pane is None:
            logger.error(f"Pane not found: {identifier}")
            return False

        try:
            pane.send_keys(text, enter=enter)
            return True
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error sending keys to {identifier}: {e}")
            return False

    def clear_history(self, identifier: str) -> None:
        """Clear the stored content history for a pane."""
        if identifier in self._last_content:
            del self._last_content[identifier]

    def pane_exists(self, identifier: str) -> bool:
        """Check if a pane still exists."""
        return self.get_pane(identifier) is not None

    def resize_pane(self, identifier: str, width: int) -> bool:
        """Resize a pane to specified width.

        Args:
            identifier: Pane identifier in format "session:window.pane"
            width: Target width in columns

        Returns:
            True if successful, False otherwise.
        """
        pane = self.get_pane(identifier)
        if pane is None:
            logger.error(f"Pane not found: {identifier}")
            return False

        try:
            pane.resize(width=width)
            return True
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error resizing pane {identifier}: {e}")
            return False

    def set_terminal_width(self, identifier: str, width: int) -> bool:
        """Set terminal width using stty (works for running programs).

        This sends a stty command to change the terminal's column setting,
        which triggers SIGWINCH and makes programs like Claude Code
        re-detect the terminal width.

        Args:
            identifier: Pane identifier in format "session:window.pane"
            width: Target width in columns

        Returns:
            True if successful, False otherwise.
        """
        pane = self.get_pane(identifier)
        if pane is None:
            logger.error(f"Pane not found: {identifier}")
            return False

        try:
            # Send stty command to set columns
            pane.send_keys(f"stty columns {width}", enter=True)
            return True
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error setting terminal width for {identifier}: {e}")
            return False

    def reset_terminal_width(self, identifier: str) -> bool:
        """Reset terminal width to match actual pane size.

        Args:
            identifier: Pane identifier in format "session:window.pane"

        Returns:
            True if successful, False otherwise.
        """
        pane = self.get_pane(identifier)
        if pane is None:
            logger.error(f"Pane not found: {identifier}")
            return False

        try:
            # Use resize command to reset stty to actual pane size
            pane.send_keys("eval $(resize)", enter=True)
            return True
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error resetting terminal width for {identifier}: {e}")
            return False

    def create_session(self, name: Optional[str] = None) -> Optional[tuple[str, str]]:
        """Create a new tmux session.

        Args:
            name: Optional session name. If not provided, tmux will auto-generate.

        Returns:
            Tuple of (session_name, pane_identifier) if successful, None otherwise.
        """
        server = self._get_server()
        if server is None:
            # Try to start a new server
            try:
                server = libtmux.Server()
                self._server = server
            except libtmux.exc.LibTmuxException as e:
                logger.error(f"Error creating tmux server: {e}")
                return None

        try:
            session = server.new_session(session_name=name)
            window = session.active_window
            pane = window.active_pane
            pane_id = f"{session.name}:{window.index}.{pane.index}"
            return (session.name, pane_id)
        except libtmux.exc.LibTmuxException as e:
            logger.error(f"Error creating session: {e}")
            return None
