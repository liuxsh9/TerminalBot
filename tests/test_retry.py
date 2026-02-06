#!/usr/bin/env python3
"""Test retry logic and error handling."""

import asyncio
import logging
from src.retry_policy import RetryPolicy, is_transient_error

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class NetworkError(Exception):
    """Simulated network error."""
    pass


class FatalError(Exception):
    """Simulated fatal error."""
    pass


async def simulate_network_failure(fail_count=3):
    """Simulate a function that fails a few times then succeeds."""
    if not hasattr(simulate_network_failure, 'attempts'):
        simulate_network_failure.attempts = 0

    simulate_network_failure.attempts += 1

    if simulate_network_failure.attempts <= fail_count:
        logger.info(f"Simulating failure (attempt {simulate_network_failure.attempts})")
        raise NetworkError(f"Connection failed (attempt {simulate_network_failure.attempts})")

    logger.info("Success!")
    return "Success"


async def test_retry_with_success():
    """Test that retry succeeds after transient failures."""
    print("\n=== Test 1: Retry with eventual success ===")

    simulate_network_failure.attempts = 0
    retry_policy = RetryPolicy(base_delay=0.1, max_delay=1.0)

    try:
        result = await retry_policy.retry_async(simulate_network_failure, fail_count=3)
        print(f"✓ Result: {result}")
        print(f"✓ Succeeded after {simulate_network_failure.attempts} attempts")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


async def test_max_retries_exceeded():
    """Test that retry gives up after max retries."""
    print("\n=== Test 2: Max retries exceeded ===")

    simulate_network_failure.attempts = 0
    retry_policy = RetryPolicy(base_delay=0.1, max_delay=1.0, max_retries=2)

    try:
        result = await retry_policy.retry_async(simulate_network_failure, fail_count=10)
        print(f"✗ Should have failed but got: {result}")
        return False
    except NetworkError as e:
        print(f"✓ Correctly gave up after max retries")
        print(f"✓ Total attempts: {simulate_network_failure.attempts}")
        return True


async def test_exponential_backoff():
    """Test that delays increase exponentially."""
    print("\n=== Test 3: Exponential backoff ===")

    retry_policy = RetryPolicy(base_delay=1.0, max_delay=300.0)

    delays = [retry_policy.get_delay(i) for i in range(10)]
    print(f"Delays for first 10 attempts: {delays}")

    # Check exponential growth
    if delays == [1, 2, 4, 8, 16, 32, 64, 128, 256, 300]:
        print("✓ Exponential backoff working correctly (capped at 300s)")
        return True
    else:
        print("✗ Exponential backoff incorrect")
        return False


def test_transient_error_detection():
    """Test error classification."""
    print("\n=== Test 4: Transient error detection ===")

    # Create mock telegram exceptions
    class MockNetworkError(Exception):
        pass

    class MockTimedOut(Exception):
        pass

    test_cases = [
        (NetworkError("Connection timeout"), True, "Generic network error"),
        (Exception("network unavailable"), True, "Network in message"),
        (Exception("rate limit exceeded"), True, "Rate limit in message"),
        (FatalError("Invalid token"), False, "Fatal error"),
        (ValueError("Invalid input"), False, "Non-network error"),
    ]

    passed = 0
    for error, expected, description in test_cases:
        result = is_transient_error(error)
        status = "✓" if result == expected else "✗"
        print(f"{status} {description}: {result} (expected {expected})")
        if result == expected:
            passed += 1

    print(f"\n{passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Retry Logic and Error Handling")
    print("=" * 60)

    results = []

    # Async tests
    results.append(await test_retry_with_success())
    results.append(await test_max_retries_exceeded())
    results.append(await test_exponential_backoff())

    # Sync test
    results.append(test_transient_error_detection())

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    return all(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
