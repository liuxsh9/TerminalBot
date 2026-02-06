"""Retry policy with exponential backoff for network operations."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Retry configuration
BASE_DELAY = 1  # seconds
MAX_DELAY = 300  # 5 minutes
MAX_RETRIES = 10  # before logging critical error


class RetryPolicy:
    """Exponential backoff retry policy for handling transient failures."""

    def __init__(
        self,
        base_delay: float = BASE_DELAY,
        max_delay: float = MAX_DELAY,
        max_retries: int = MAX_RETRIES,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number using exponential backoff.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds, capped at max_delay
        """
        delay = self.base_delay * (2**attempt)
        return min(delay, self.max_delay)

    async def retry_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Retry an async function with exponential backoff.

        Args:
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt >= self.max_retries:
                    logger.critical(
                        f"Maximum retries ({self.max_retries}) exceeded for {func.__name__}. "
                        f"Last error: {e}"
                    )
                    raise

                delay = self.get_delay(attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries} for {func.__name__} "
                    f"after error: {e}. Retrying in {delay}s..."
                )

                await asyncio.sleep(delay)

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception


def is_transient_error(exception: Exception) -> bool:
    """Determine if an error is transient and worth retrying.

    Args:
        exception: The exception to classify

    Returns:
        True if the error is likely transient (network issues, rate limits)
    """
    # Check for standard timeout exceptions
    if isinstance(exception, TimeoutError):
        return True

    # Import telegram exceptions locally to avoid circular imports
    try:
        from telegram.error import NetworkError, RetryAfter, TimedOut

        if isinstance(exception, (NetworkError, TimedOut, RetryAfter)):
            return True
    except ImportError:
        pass

    # Check for common network-related exceptions
    error_msg = str(exception).lower()
    transient_indicators = [
        "connection",
        "timeout",
        "network",
        "temporary",
        "unavailable",
        "rate limit",
    ]

    return any(indicator in error_msg for indicator in transient_indicators)
