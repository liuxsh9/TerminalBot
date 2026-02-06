"""Test health monitoring functionality."""

import asyncio
import time

import pytest

from src.health_monitor import ConnectionState, HealthMonitor


class TestHealthMonitor:
    """Test HealthMonitor class."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Test that monitor starts in disconnected state."""
        monitor = HealthMonitor(check_interval=1.0)
        assert monitor.get_status().state == ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_state_transitions(self):
        """Test state transitions."""
        monitor = HealthMonitor(check_interval=1.0)

        # DISCONNECTED -> CONNECTING
        monitor.update_state(ConnectionState.CONNECTING)
        assert monitor.get_status().state == ConnectionState.CONNECTING

        # CONNECTING -> CONNECTED
        monitor.update_state(ConnectionState.CONNECTED)
        assert monitor.get_status().state == ConnectionState.CONNECTED

        # CONNECTED -> DEGRADED
        monitor.update_state(ConnectionState.DEGRADED)
        assert monitor.get_status().state == ConnectionState.DEGRADED

        # DEGRADED -> CONNECTED
        monitor.update_state(ConnectionState.CONNECTED)
        assert monitor.get_status().state == ConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_record_successful_poll(self):
        """Test recording successful polls."""
        monitor = HealthMonitor(check_interval=1.0)
        monitor.update_state(ConnectionState.CONNECTED)

        # Record poll
        monitor.record_successful_poll()

        # Should still be connected
        assert monitor.get_status().state == ConnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_health_check_triggers_callback(self):
        """Test that health check triggers callback when degraded."""
        monitor = HealthMonitor(check_interval=0.1)
        callback_called = {"value": False}

        async def mock_callback():
            callback_called["value"] = True

        monitor.set_reconnect_callback(mock_callback)
        monitor.update_state(ConnectionState.CONNECTED)

        # Record a poll in the past (more than 300s ago)
        monitor.last_poll_time = time.time() - 301

        # Start monitoring
        monitor.start()

        try:
            # Wait for health check to detect degradation
            await asyncio.sleep(0.3)

            # Callback should have been called
            assert callback_called["value"] is True
        finally:
            await monitor.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_health_check(self):
        """Test that stop cancels the health check task."""
        monitor = HealthMonitor(check_interval=0.1)
        monitor.update_state(ConnectionState.CONNECTED)

        monitor.start()
        await asyncio.sleep(0.05)  # Let it start

        await monitor.stop()

        # Task should be cancelled
        # If we wait, no health checks should run
        await asyncio.sleep(0.2)
        # Test passes if no errors occur

    @pytest.mark.asyncio
    async def test_multiple_start_calls(self):
        """Test that multiple start calls don't create duplicate tasks."""
        monitor = HealthMonitor(check_interval=0.1)
        monitor.update_state(ConnectionState.CONNECTED)

        monitor.start()
        monitor.start()  # Second call should be ignored

        await asyncio.sleep(0.05)
        await monitor.stop()

    @pytest.mark.asyncio
    async def test_callback_exception_handling(self):
        """Test that callback exceptions don't crash the monitor."""
        monitor = HealthMonitor(check_interval=0.1)

        async def failing_callback():
            raise Exception("Callback failed")

        monitor.set_reconnect_callback(failing_callback)
        monitor.update_state(ConnectionState.CONNECTED)

        # Record a poll in the past (more than 300s ago)
        monitor.last_poll_time = time.time() - 301

        monitor.start()

        try:
            # Wait for health check
            await asyncio.sleep(0.3)
            # Should not crash, should be degraded
            assert monitor.get_status().state == ConnectionState.DEGRADED
        finally:
            await monitor.stop()


class TestConnectionState:
    """Test ConnectionState enum."""

    def test_connection_state_values(self):
        """Test that connection states have expected values."""
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.DEGRADED.value == "degraded"

    def test_connection_state_comparison(self):
        """Test that connection states can be compared."""
        assert ConnectionState.DISCONNECTED == ConnectionState.DISCONNECTED
        assert ConnectionState.CONNECTED != ConnectionState.DEGRADED
