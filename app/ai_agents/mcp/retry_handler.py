"""
MCP Retry Handler

This module provides comprehensive retry logic for MCP operations, including:
- Exponential backoff with jitter (1s, 2s, 4s, 8s)
- Retry decorator for automatic retries (maximum 3 attempts)
- Configurable retry strategies
- Integration with error handling system

Following PRD: Task 2.2 and 2.3 - Implementar función de backoff exponencial y decorador retry
"""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from datetime import datetime, timedelta

from .error_handler import (
    BaseMCPError,
    MCPErrorCategory,
    MCPErrorHandler,
    get_error_handler,
)
from app.core.config import get_mcp_config

logger = logging.getLogger(__name__)


class RetryStrategy:
    """
    Configuration for retry behavior.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        jitter_range: tuple = (0.1, 0.3),
        retryable_errors: Optional[List[MCPErrorCategory]] = None,
        non_retryable_errors: Optional[List[MCPErrorCategory]] = None,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.jitter_range = jitter_range

        # Default retryable errors (temporary failures)
        self.retryable_errors = retryable_errors or [
            MCPErrorCategory.CONNECTION,
            MCPErrorCategory.TIMEOUT,
            MCPErrorCategory.RATE_LIMIT,
            MCPErrorCategory.SERVICE_UNAVAILABLE,
            MCPErrorCategory.NETWORK,
            MCPErrorCategory.OPERATION_FAILED,
        ]

        # Default non-retryable errors (permanent failures)
        self.non_retryable_errors = non_retryable_errors or [
            MCPErrorCategory.AUTHENTICATION,
            MCPErrorCategory.AUTHORIZATION,
            MCPErrorCategory.VALIDATION,
            MCPErrorCategory.CONFIGURATION,
        ]

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number using exponential backoff with jitter.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            float: Delay in seconds
        """
        # Exponential backoff: base_delay * (backoff_factor ^ attempt)
        delay = self.base_delay * (self.backoff_factor**attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_min, jitter_max = self.jitter_range
            jitter_amount = random.uniform(jitter_min, jitter_max) * delay
            delay += jitter_amount

        return delay

    def should_retry(self, error: BaseMCPError, attempt: int) -> bool:
        """
        Determine if an error should be retried.

        Args:
            error: The MCP error that occurred
            attempt: Current attempt number (1-based)

        Returns:
            bool: Whether to retry the operation
        """
        # Check attempt limit
        if attempt >= self.max_attempts:
            return False

        # Check if error category is retryable
        if error.category in self.non_retryable_errors:
            return False

        if error.category in self.retryable_errors:
            return True

        # Default: don't retry unknown categories
        return False

    def get_retry_after_seconds(self, error: BaseMCPError) -> Optional[float]:
        """
        Get retry-after seconds from error context (e.g., from rate limit headers).

        Args:
            error: The MCP error

        Returns:
            Optional[float]: Seconds to wait before retry, if specified
        """
        if error.category == MCPErrorCategory.RATE_LIMIT:
            return error.context.get("retry_after_seconds")
        return None


def exponential_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    jitter_range: tuple = (0.1, 0.3),
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    This is the core function implementing the backoff algorithm as specified:
    1s, 2s, 4s, 8s with jitter to prevent thundering herd.

    Args:
        attempt: Current attempt number (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential growth
        jitter: Whether to add random jitter
        jitter_range: Range for jitter as (min_factor, max_factor)

    Returns:
        float: Delay in seconds
    """
    # Calculate exponential delay
    delay = base_delay * (backoff_factor**attempt)

    # Cap at maximum
    delay = min(delay, max_delay)

    # Add jitter if requested
    if jitter:
        jitter_min, jitter_max = jitter_range
        jitter_factor = random.uniform(jitter_min, jitter_max)
        jitter_amount = delay * jitter_factor
        delay += jitter_amount

    return delay


def create_retry_strategy_from_config(
    service_name: str = "",
    custom_config: Optional[Dict[str, Any]] = None,
) -> RetryStrategy:
    """
    Create retry strategy from MCP configuration.

    Args:
        service_name: Name of the service for service-specific config
        custom_config: Custom configuration overrides

    Returns:
        RetryStrategy: Configured retry strategy
    """
    mcp_config = get_mcp_config()

    # Get base configuration
    config = {
        "max_attempts": mcp_config.mcp_max_retries,
        "base_delay": 1.0,  # Start with 1 second as specified
        "max_delay": mcp_config.mcp_retry_max_delay,
        "backoff_factor": mcp_config.mcp_retry_backoff_factor,
        "jitter": mcp_config.mcp_retry_jitter,
    }

    # Apply service-specific overrides if available
    if service_name:
        service_config = mcp_config.get_service_config(service_name)
        config.update(
            {
                "max_attempts": service_config.get(
                    "max_retries", config["max_attempts"]
                ),
                "max_delay": service_config.get("max_delay", config["max_delay"]),
                "backoff_factor": service_config.get(
                    "backoff_factor", config["backoff_factor"]
                ),
            }
        )

    # Apply custom overrides
    if custom_config:
        config.update(custom_config)

    return RetryStrategy(**config)


class RetryContext:
    """
    Context object to track retry state and provide debugging information.
    """

    def __init__(self, operation_name: str, service_name: str = ""):
        self.operation_name = operation_name
        self.service_name = service_name
        self.attempt_count = 0
        self.start_time = time.time()
        self.attempts: List[Dict[str, Any]] = []
        self.last_error: Optional[BaseMCPError] = None
        self.total_delay = 0.0

    def record_attempt(
        self,
        error: Optional[BaseMCPError] = None,
        delay: float = 0.0,
        success: bool = False,
    ) -> None:
        """Record an attempt with its result"""
        self.attempt_count += 1
        self.total_delay += delay

        attempt_record = {
            "attempt": self.attempt_count,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "delay": delay,
            "error": error.to_dict() if error else None,
        }

        self.attempts.append(attempt_record)

        if error:
            self.last_error = error

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of retry attempts"""
        total_time = time.time() - self.start_time

        return {
            "operation": self.operation_name,
            "service": self.service_name,
            "total_attempts": self.attempt_count,
            "total_time_seconds": total_time,
            "total_delay_seconds": self.total_delay,
            "success": self.last_error is None,
            "last_error": self.last_error.to_dict() if self.last_error else None,
            "attempts": self.attempts,
        }


def retry_mcp_operation(
    max_attempts: int = 3,
    strategy: Optional[RetryStrategy] = None,
    service_name: str = "",
    operation_name: str = "",
    error_handler: Optional[MCPErrorHandler] = None,
    log_attempts: bool = True,
):
    """
    Decorator for automatic retry of MCP operations with exponential backoff.

    This decorator implements the retry logic as specified in the PRD:
    - Maximum 3 attempts by default
    - Exponential backoff: 1s, 2s, 4s, 8s
    - Smart error classification and retry decisions
    - Comprehensive logging and debugging

    Args:
        max_attempts: Maximum number of retry attempts
        strategy: Custom retry strategy (auto-created if not provided)
        service_name: Name of the MCP service
        operation_name: Name of the operation (auto-detected if not provided)
        error_handler: Error handler instance (uses global if not provided)
        log_attempts: Whether to log retry attempts

    Usage:
        @retry_mcp_operation(max_attempts=3, service_name="sendgrid")
        async def send_email(recipient, subject, body):
            # Operation that might fail
            pass

        @retry_mcp_operation(strategy=custom_strategy)
        def sync_operation():
            # Synchronous operation
            pass
    """

    def decorator(func: Callable) -> Callable:
        # Determine if function is async
        is_async = asyncio.iscoroutinefunction(func)

        # Create retry strategy if not provided
        retry_strategy = strategy or create_retry_strategy_from_config(
            service_name=service_name,
            custom_config={"max_attempts": max_attempts} if max_attempts != 3 else None,
        )

        # Get error handler
        handler = error_handler or get_error_handler()

        # Determine operation name
        op_name = operation_name or func.__name__

        if is_async:

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = RetryContext(op_name, service_name)

                for attempt in range(retry_strategy.max_attempts):
                    try:
                        if log_attempts and attempt > 0:
                            logger.info(
                                f"🔄 Retrying {op_name} on {service_name} "
                                f"(attempt {attempt + 1}/{retry_strategy.max_attempts})"
                            )

                        # Execute the operation
                        result = await func(*args, **kwargs)

                        # Success - record and return
                        context.record_attempt(success=True)

                        if log_attempts and attempt > 0:
                            logger.info(
                                f"✅ {op_name} succeeded on attempt {attempt + 1} "
                                f"after {context.total_delay:.1f}s total delay"
                            )

                        return result

                    except Exception as raw_error:
                        # Classify and handle the error
                        if isinstance(raw_error, BaseMCPError):
                            mcp_error = raw_error
                        else:
                            mcp_error = handler.classify_error(
                                raw_error, service_name, op_name
                            )

                        # Check if we should retry
                        should_retry = retry_strategy.should_retry(
                            mcp_error, attempt + 1
                        )

                        # Calculate delay for next attempt
                        if should_retry and attempt + 1 < retry_strategy.max_attempts:
                            # Check for rate limit retry-after
                            rate_limit_delay = retry_strategy.get_retry_after_seconds(
                                mcp_error
                            )
                            if rate_limit_delay:
                                delay = rate_limit_delay
                                logger.info(
                                    f"⏱️ Rate limited, waiting {delay}s as requested"
                                )
                            else:
                                delay = retry_strategy.calculate_delay(attempt)

                            # Record attempt and wait
                            context.record_attempt(mcp_error, delay)

                            if log_attempts:
                                logger.warning(
                                    f"❌ {op_name} failed on attempt {attempt + 1}: "
                                    f"{mcp_error.get_user_friendly_message()[:50]}... "
                                    f"Retrying in {delay:.1f}s"
                                )

                            await asyncio.sleep(delay)
                        else:
                            # No more retries - record final failure
                            context.record_attempt(mcp_error)

                            if log_attempts:
                                if attempt + 1 >= retry_strategy.max_attempts:
                                    logger.error(
                                        f"💥 {op_name} failed after {retry_strategy.max_attempts} attempts. "
                                        f"Total time: {time.time() - context.start_time:.1f}s"
                                    )
                                else:
                                    logger.error(
                                        f"🛑 {op_name} failed with non-retryable error: "
                                        f"{mcp_error.category.value}"
                                    )

                            # Log retry summary for debugging
                            if log_attempts:
                                summary = context.get_summary()
                                logger.debug(f"Retry summary for {op_name}: {summary}")

                            # Re-raise the last error
                            raise mcp_error

                # This should never be reached
                raise RuntimeError("Retry loop completed without result")

            return async_wrapper

        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                context = RetryContext(op_name, service_name)

                for attempt in range(retry_strategy.max_attempts):
                    try:
                        if log_attempts and attempt > 0:
                            logger.info(
                                f"🔄 Retrying {op_name} on {service_name} "
                                f"(attempt {attempt + 1}/{retry_strategy.max_attempts})"
                            )

                        # Execute the operation
                        result = func(*args, **kwargs)

                        # Success - record and return
                        context.record_attempt(success=True)

                        if log_attempts and attempt > 0:
                            logger.info(
                                f"✅ {op_name} succeeded on attempt {attempt + 1} "
                                f"after {context.total_delay:.1f}s total delay"
                            )

                        return result

                    except Exception as raw_error:
                        # Classify and handle the error
                        if isinstance(raw_error, BaseMCPError):
                            mcp_error = raw_error
                        else:
                            mcp_error = handler.classify_error(
                                raw_error, service_name, op_name
                            )

                        # Check if we should retry
                        should_retry = retry_strategy.should_retry(
                            mcp_error, attempt + 1
                        )

                        # Calculate delay for next attempt
                        if should_retry and attempt + 1 < retry_strategy.max_attempts:
                            # Check for rate limit retry-after
                            rate_limit_delay = retry_strategy.get_retry_after_seconds(
                                mcp_error
                            )
                            if rate_limit_delay:
                                delay = rate_limit_delay
                                logger.info(
                                    f"⏱️ Rate limited, waiting {delay}s as requested"
                                )
                            else:
                                delay = retry_strategy.calculate_delay(attempt)

                            # Record attempt and wait
                            context.record_attempt(mcp_error, delay)

                            if log_attempts:
                                logger.warning(
                                    f"❌ {op_name} failed on attempt {attempt + 1}: "
                                    f"{mcp_error.get_user_friendly_message()[:50]}... "
                                    f"Retrying in {delay:.1f}s"
                                )

                            time.sleep(delay)
                        else:
                            # No more retries - record final failure
                            context.record_attempt(mcp_error)

                            if log_attempts:
                                if attempt + 1 >= retry_strategy.max_attempts:
                                    logger.error(
                                        f"💥 {op_name} failed after {retry_strategy.max_attempts} attempts. "
                                        f"Total time: {time.time() - context.start_time:.1f}s"
                                    )
                                else:
                                    logger.error(
                                        f"🛑 {op_name} failed with non-retryable error: "
                                        f"{mcp_error.category.value}"
                                    )

                            # Log retry summary for debugging
                            if log_attempts:
                                summary = context.get_summary()
                                logger.debug(f"Retry summary for {op_name}: {summary}")

                            # Re-raise the last error
                            raise mcp_error

                # This should never be reached
                raise RuntimeError("Retry loop completed without result")

            return sync_wrapper

    return decorator


# Convenience functions for common retry patterns
def retry_connection_operation(max_attempts: int = 3, service_name: str = ""):
    """Retry decorator optimized for connection operations"""
    strategy = RetryStrategy(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=30.0,  # Shorter max delay for connections
        retryable_errors=[MCPErrorCategory.CONNECTION, MCPErrorCategory.NETWORK],
    )
    return retry_mcp_operation(strategy=strategy, service_name=service_name)


def retry_rate_limited_operation(max_attempts: int = 5, service_name: str = ""):
    """Retry decorator optimized for rate-limited operations"""
    strategy = RetryStrategy(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=300.0,  # Longer max delay for rate limits
        retryable_errors=[
            MCPErrorCategory.RATE_LIMIT,
            MCPErrorCategory.SERVICE_UNAVAILABLE,
        ],
    )
    return retry_mcp_operation(strategy=strategy, service_name=service_name)


def retry_timeout_operation(max_attempts: int = 2, service_name: str = ""):
    """Retry decorator optimized for timeout operations"""
    strategy = RetryStrategy(
        max_attempts=max_attempts,
        base_delay=2.0,  # Start with longer delay
        max_delay=60.0,
        retryable_errors=[MCPErrorCategory.TIMEOUT],
    )
    return retry_mcp_operation(strategy=strategy, service_name=service_name)


# Global functions for manual retry logic
async def retry_async_operation(
    operation: Callable,
    strategy: Optional[RetryStrategy] = None,
    service_name: str = "",
    operation_name: str = "",
    *args,
    **kwargs,
):
    """
    Manually retry an async operation with the specified strategy.

    Args:
        operation: Async function to retry
        strategy: Retry strategy (uses default if not provided)
        service_name: Name of the service
        operation_name: Name of the operation
        *args, **kwargs: Arguments to pass to the operation

    Returns:
        Result of the successful operation

    Raises:
        BaseMCPError: If all retry attempts fail
    """
    retry_strategy = strategy or create_retry_strategy_from_config(service_name)
    handler = get_error_handler()
    op_name = operation_name or getattr(operation, "__name__", "unknown_operation")
    context = RetryContext(op_name, service_name)

    for attempt in range(retry_strategy.max_attempts):
        try:
            result = await operation(*args, **kwargs)
            context.record_attempt(success=True)
            return result

        except Exception as raw_error:
            if isinstance(raw_error, BaseMCPError):
                mcp_error = raw_error
            else:
                mcp_error = handler.classify_error(raw_error, service_name, op_name)

            should_retry = retry_strategy.should_retry(mcp_error, attempt + 1)

            if should_retry and attempt + 1 < retry_strategy.max_attempts:
                delay = retry_strategy.calculate_delay(attempt)
                context.record_attempt(mcp_error, delay)
                await asyncio.sleep(delay)
            else:
                context.record_attempt(mcp_error)
                raise mcp_error


def retry_sync_operation(
    operation: Callable,
    strategy: Optional[RetryStrategy] = None,
    service_name: str = "",
    operation_name: str = "",
    *args,
    **kwargs,
):
    """
    Manually retry a sync operation with the specified strategy.

    Similar to retry_async_operation but for synchronous functions.
    """
    retry_strategy = strategy or create_retry_strategy_from_config(service_name)
    handler = get_error_handler()
    op_name = operation_name or getattr(operation, "__name__", "unknown_operation")
    context = RetryContext(op_name, service_name)

    for attempt in range(retry_strategy.max_attempts):
        try:
            result = operation(*args, **kwargs)
            context.record_attempt(success=True)
            return result

        except Exception as raw_error:
            if isinstance(raw_error, BaseMCPError):
                mcp_error = raw_error
            else:
                mcp_error = handler.classify_error(raw_error, service_name, op_name)

            should_retry = retry_strategy.should_retry(mcp_error, attempt + 1)

            if should_retry and attempt + 1 < retry_strategy.max_attempts:
                delay = retry_strategy.calculate_delay(attempt)
                context.record_attempt(mcp_error, delay)
                time.sleep(delay)
            else:
                context.record_attempt(mcp_error)
                raise mcp_error
