"""Test retry logic and error handling."""

import pytest

from src.retry_policy import RetryPolicy, is_transient_error


class NetworkError(Exception):
    """Simulated network error."""


class FatalError(Exception):
    """Simulated fatal error."""


class TestRetryPolicy:
    """Test RetryPolicy class."""

    @pytest.mark.asyncio
    async def test_retry_with_success(self):
        """Test that retry succeeds after transient failures."""
        attempts = {"count": 0}

        async def simulate_network_failure():
            attempts["count"] += 1
            if attempts["count"] <= 3:
                raise NetworkError(f"Connection failed (attempt {attempts['count']})")
            return "Success"

        retry_policy = RetryPolicy(base_delay=0.01, max_delay=1.0)
        result = await retry_policy.retry_async(simulate_network_failure)

        assert result == "Success"
        assert attempts["count"] == 4  # 3 failures + 1 success

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that retry gives up after max retries."""
        attempts = {"count": 0}

        async def always_fail():
            attempts["count"] += 1
            raise NetworkError(f"Connection failed (attempt {attempts['count']})")

        retry_policy = RetryPolicy(base_delay=0.01, max_delay=1.0, max_retries=2)

        with pytest.raises(NetworkError):
            await retry_policy.retry_async(always_fail)

        assert attempts["count"] == 3  # Initial + 2 retries

    def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        retry_policy = RetryPolicy(base_delay=1.0, max_delay=300.0)

        delays = [retry_policy.get_delay(i) for i in range(10)]

        assert delays == [1, 2, 4, 8, 16, 32, 64, 128, 256, 300]

    def test_exponential_backoff_no_cap(self):
        """Test exponential backoff without reaching cap."""
        retry_policy = RetryPolicy(base_delay=1.0, max_delay=1000.0)

        delays = [retry_policy.get_delay(i) for i in range(5)]

        assert delays == [1, 2, 4, 8, 16]


class TestTransientErrorDetection:
    """Test error classification."""

    def test_network_error_is_transient(self):
        """Test that generic network errors are transient."""
        error = NetworkError("Connection timeout")
        assert is_transient_error(error) is True

    def test_network_message_is_transient(self):
        """Test that errors with 'network' in message are transient."""
        test_cases = [
            Exception("network unavailable"),
            Exception("Network timeout"),
            Exception("NETWORK ERROR"),
        ]
        for error in test_cases:
            assert is_transient_error(error) is True

    def test_rate_limit_is_transient(self):
        """Test that rate limit errors are transient."""
        error = Exception("rate limit exceeded")
        assert is_transient_error(error) is True

    def test_timeout_is_transient(self):
        """Test that timeout errors are transient."""
        test_cases = [
            Exception("connection timeout"),
            Exception("timeout occurred"),
            TimeoutError("Operation timed out"),
        ]
        for error in test_cases:
            assert is_transient_error(error) is True

    def test_fatal_error_not_transient(self):
        """Test that fatal errors are not transient."""
        error = FatalError("Invalid token")
        assert is_transient_error(error) is False

    def test_value_error_not_transient(self):
        """Test that value errors are not transient."""
        error = ValueError("Invalid input")
        assert is_transient_error(error) is False

    def test_generic_exception_not_transient(self):
        """Test that generic exceptions without network keywords are not transient."""
        error = Exception("Something went wrong")
        assert is_transient_error(error) is False
