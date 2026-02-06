"""Health monitoring for TerminalBot."""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Bot connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DEGRADED = "degraded"


@dataclass
class HealthStatus:
    """Current health status of the bot."""
    state: ConnectionState
    last_poll_time: Optional[float]
    last_message_time: Optional[float]
    uptime_seconds: float

    def is_healthy(self) -> bool:
        """Check if the bot is in a healthy state."""
        return self.state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING)

    def is_degraded(self) -> bool:
        """Check if the bot is degraded but still running."""
        return self.state == ConnectionState.DEGRADED


class HealthMonitor:
    """Monitor bot health and trigger recovery actions."""

    def __init__(self, check_interval: float = 300.0):
        """Initialize health monitor.

        Args:
            check_interval: How often to run health checks (seconds)
        """
        self.check_interval = check_interval
        self.state = ConnectionState.DISCONNECTED
        self.last_poll_time: Optional[float] = None
        self.last_message_time: Optional[float] = None
        self.start_time = time.time()
        self._monitoring_task: Optional[asyncio.Task] = None
        self._reconnect_callback = None

    def set_reconnect_callback(self, callback):
        """Set callback to trigger reconnection.

        Args:
            callback: Async function to call when reconnection is needed
        """
        self._reconnect_callback = callback

    def update_state(self, state: ConnectionState):
        """Update connection state.

        Args:
            state: New connection state
        """
        if self.state != state:
            logger.info(f"Health state transition: {self.state.value} -> {state.value}")
            self.state = state

    def record_successful_poll(self):
        """Record that a successful Telegram poll occurred."""
        self.last_poll_time = time.time()
        if self.state == ConnectionState.DEGRADED:
            logger.info("Bot recovered from degraded state")
            self.state = ConnectionState.CONNECTED

    def record_message_sent(self):
        """Record that a message was successfully sent."""
        self.last_message_time = time.time()

    def get_status(self) -> HealthStatus:
        """Get current health status.

        Returns:
            Current HealthStatus
        """
        uptime = time.time() - self.start_time
        return HealthStatus(
            state=self.state,
            last_poll_time=self.last_poll_time,
            last_message_time=self.last_message_time,
            uptime_seconds=uptime
        )

    def log_status(self):
        """Log current health status."""
        status = self.get_status()

        last_poll_str = "never"
        if status.last_poll_time:
            elapsed = time.time() - status.last_poll_time
            last_poll_str = f"{elapsed:.1f}s ago"

        logger.info(
            f"Health Status: state={status.state.value}, "
            f"last_poll={last_poll_str}, "
            f"uptime={status.uptime_seconds/60:.1f}min"
        )

    async def check_health(self) -> bool:
        """Run health check and return whether bot is healthy.

        Returns:
            True if healthy, False if degraded
        """
        status = self.get_status()

        # If we haven't had a successful poll in 5 minutes, mark as degraded
        if status.last_poll_time:
            time_since_poll = time.time() - status.last_poll_time
            if time_since_poll > 300:  # 5 minutes
                logger.warning(
                    f"Bot degraded: no successful poll for {time_since_poll/60:.1f} minutes"
                )
                self.update_state(ConnectionState.DEGRADED)

                # Trigger reconnection if callback is set
                if self._reconnect_callback:
                    logger.info("Triggering health-based reconnection")
                    try:
                        await self._reconnect_callback()
                    except Exception as e:
                        logger.error(f"Reconnection failed: {e}")

                return False

        return status.is_healthy()

    async def start_monitoring(self):
        """Start the health monitoring loop."""
        logger.info(f"Starting health monitor (check interval: {self.check_interval}s)")

        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self.check_health()
                self.log_status()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

    def start(self):
        """Start health monitoring in the background."""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self.start_monitoring())

    async def stop(self):
        """Stop health monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
